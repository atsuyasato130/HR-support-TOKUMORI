#!/usr/bin/env python3
"""
notion_to_sf_sync.py — Notion企業DB → Salesforce + Supabase 統合移管スクリプト

機能:
  1. Notion企業DBの全レコードを取得
  2. SF既存Accountと名前マッチング（株式会社等を除去した正規化マッチ）
  3. マッチした企業: SF & Supabase を更新
  4. 未マッチ企業: SF に新規Account作成 → Supabase に挿入
  5. --watch モード: 定期ポーリングで Notion 新規追加を検知 → SF 自動生成

使い方:
  # 全件同期（dry-runで確認）
  python3 tools/notion_to_sf_sync.py --dry-run

  # 実行
  python3 tools/notion_to_sf_sync.py

  # 特定1社のみ
  python3 tools/notion_to_sf_sync.py --company "サイバーエージェント"

SFフィールドマッピング（クライアントAccount）:
  Notion "企業名"        → Account.Name
  Notion "HP"           → Account.Website
  Notion "事業概要"      → Account.Description（先頭500文字）
  Notion "業界"         → Account.Field1__c（multipicklist）
  Notion "従業員数"      → Account.NumberOfEmployees
  Notion "選考フロー"    → Supabase companies.session_dates（+ SF Description の後半）

Supabaseフィールドマッピング:
  SF Account.Id         → companies.sf_account_id
  Notion page id        → companies.notion_id
  事業概要              → companies.overview
  おすすめポイント      → companies.recommend_points[]
  選考フロー            → companies.selection_flow （※ 017マイグレ後）
  USP                   → companies.recommend_points に追加
  説明会日程            → companies.session_dates
  難易度                → companies.difficulty_score（手動設定）
"""

from __future__ import annotations

import os
import sys
import re
import json
import time
import logging
import argparse
import datetime
import difflib
from typing import Any, Dict, List, Optional, Tuple

# Claude API（web enrichment用）
try:
    import anthropic as _anthropic_module  # type: ignore
    _ANTHROPIC_AVAILABLE = True
except ImportError:
    _ANTHROPIC_AVAILABLE = False

# ── プロジェクトルート
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(_ROOT, "config", ".env"))

# ── ログ
_LOG_DIR  = os.path.join(_ROOT, "logs")
os.makedirs(_LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(_LOG_DIR, "notion_sf_sync.log"), encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("notion_sf_sync")

# ── 定数
SF_CLIENT_RECORDTYPE = "0122w000001RweZAAS"
NOTION_COMPANY_DB_ID = os.environ.get("NOTION_COMPANY_DB_ID", "5cdbd39197f94db7b7e275d317166bfd")
NOTION_API_KEY       = os.environ.get("NOTION_API_KEY", "")
SUPABASE_URL         = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")


# ──────────────────────────────────────────────
# 企業名正規化（マッチング用）
# ──────────────────────────────────────────────

_CORP_SUFFIXES = re.compile(
    r"(株式会社|有限会社|合同会社|一般社団法人|公益社団法人|医療法人|社会福祉法人"
    r"|Inc\.|LLC|Ltd\.|Co\.,?\s*Ltd\.?)",
    re.IGNORECASE,
)

def normalize_company_name(name: str) -> str:
    """
    企業名を正規化してマッチング精度を上げる。
    「株式会社〇〇」と「〇〇」を同一視できるようにする。
    """
    name = _CORP_SUFFIXES.sub("", name)
    name = re.sub(r"[\s　・\-_]", "", name)
    return name.lower().strip()


def match_company_name(
    notion_name: str,
    sf_accounts: List[Dict[str, Any]],
    threshold: float = 0.80,
) -> Optional[Dict[str, Any]]:
    """
    Notion企業名とSF Accountリストを照合し、最も近いものを返す。

    Args:
        notion_name  : Notion上の企業名
        sf_accounts  : SF Account レコードのリスト
        threshold    : 一致率の閾値（0〜1、デフォルト0.80）

    Returns:
        最もマッチしたSF Account or None
    """
    n_norm = normalize_company_name(notion_name)
    best_score = 0.0
    best_account = None

    for acct in sf_accounts:
        sf_norm = normalize_company_name(acct.get("Name", ""))
        # 完全一致優先
        if n_norm == sf_norm:
            return acct
        score = difflib.SequenceMatcher(None, n_norm, sf_norm).ratio()
        if score > best_score:
            best_score = score
            best_account = acct

    if best_score >= threshold:
        logger.debug("マッチ: '%s' ≈ '%s' (%.2f)", notion_name, best_account["Name"], best_score)
        return best_account

    return None


# ──────────────────────────────────────────────
# Notionクライアント
# ──────────────────────────────────────────────

class NotionCompanyDB:
    """Notion企業DBの読み取りクライアント"""

    BASE_URL = "https://api.notion.com/v1"
    VERSION  = "2022-06-28"

    def __init__(self, api_key: str, db_id: str) -> None:
        self.api_key = api_key
        self.db_id   = db_id

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization"  : f"Bearer {self.api_key}",
            "Notion-Version" : self.VERSION,
            "Content-Type"   : "application/json",
        }

    def fetch_all_companies(self) -> List[Dict[str, Any]]:
        """全企業ページを取得して正規化した辞書リストを返す"""
        import httpx
        results = []
        has_more = True
        cursor   = None

        while has_more:
            payload: Dict[str, Any] = {"page_size": 100}
            if cursor:
                payload["start_cursor"] = cursor

            resp = httpx.post(
                f"{self.BASE_URL}/databases/{self.db_id}/query",
                headers=self._headers(),
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            data     = resp.json()
            has_more = data.get("has_more", False)
            cursor   = data.get("next_cursor")

            for page in data.get("results", []):
                parsed = self._parse_page(page)
                if parsed:
                    results.append(parsed)

        logger.info("[Notion] 取得完了: %d社", len(results))
        return results

    def fetch_new_since(self, since: datetime.datetime) -> List[Dict[str, Any]]:
        """指定日時以降に追加・更新されたページを取得"""
        import httpx
        results = []
        has_more = True
        cursor   = None
        since_str = since.strftime("%Y-%m-%dT%H:%M:%S.000Z")

        while has_more:
            payload: Dict[str, Any] = {
                "page_size": 100,
                "filter": {
                    "timestamp": "created_time",
                    "created_time": {"after": since_str},
                },
                "sorts": [{"timestamp": "created_time", "direction": "descending"}],
            }
            if cursor:
                payload["start_cursor"] = cursor

            resp = httpx.post(
                f"{self.BASE_URL}/databases/{self.db_id}/query",
                headers=self._headers(),
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            data     = resp.json()
            has_more = data.get("has_more", False)
            cursor   = data.get("next_cursor")

            for page in data.get("results", []):
                parsed = self._parse_page(page)
                if parsed:
                    results.append(parsed)

        return results

    def _parse_page(self, page: dict) -> Optional[Dict[str, Any]]:
        """NotionページのプロパティをフラットなDictに変換"""
        props = page.get("properties", {})

        def text(key: str) -> str:
            p = props.get(key, {})
            pt = p.get("type", "")
            if pt == "title":
                return "".join(r.get("plain_text", "") for r in p.get("title", []))
            if pt == "rich_text":
                return "".join(r.get("plain_text", "") for r in p.get("rich_text", []))
            if pt == "url":
                return p.get("url") or ""
            if pt == "select":
                s = p.get("select")
                return s["name"] if s else ""
            if pt == "multi_select":
                return ";".join(s["name"] for s in p.get("multi_select", []))
            if pt == "number":
                v = p.get("number")
                return str(v) if v is not None else ""
            if pt == "date":
                d = p.get("date")
                return d["start"] if d else ""
            return ""

        # 企業名（title フィールドを自動検出）
        company_name = ""
        for key, prop in props.items():
            if prop.get("type") == "title":
                company_name = "".join(
                    r.get("plain_text", "") for r in prop.get("title", [])
                )
                break

        if not company_name:
            return None

        # 各フィールドを柔軟に取得（プロパティ名の表記ゆれに対応）
        def get_any(*keys: str) -> str:
            for k in keys:
                v = text(k)
                if v:
                    return v
            return ""

        result: Dict[str, Any] = {
            "notion_page_id"  : page["id"],
            "notion_url"      : page.get("url", ""),
            "created_at"      : page.get("created_time", ""),
            "name"            : company_name,
            "hp_url"          : get_any("HP", "ホームページ", "URL", "Website", "hp", "HP URL"),
            "overview"        : get_any("事業概要", "概要", "会社概要", "Overview"),
            "selection_flow"  : get_any("選考フロー", "選考", "採用フロー", "SelectionFlow"),
            "usp"             : get_any("USP", "強み", "おすすめポイント", "推薦ポイント"),
            "persona"         : get_any("ペルソナ", "求める人物像", "ターゲット", "Persona"),
            "industry"        : get_any("業界", "Industry", "分野"),
            "employee_count"  : get_any("従業員数", "社員数", "人数"),
            "session_dates"   : get_any("説明会日程", "説明会", "イベント日程"),
            "grad_years"      : get_any("対象卒業年度", "卒業年度", "対象年度"),
            "hiring_count"    : get_any("採用人数", "採用数", "募集人数"),
        }
        return result


# ──────────────────────────────────────────────
# Web エンリッチメント（Claude API + httpx）
# ──────────────────────────────────────────────

# 業界ピックリスト（SFの Field1__c で使用可能な値）
_SF_INDUSTRIES = [
    "IT・通信", "メーカー", "商社", "金融", "コンサルティング",
    "不動産・建設", "医療・製薬", "流通・小売", "広告・メディア",
    "教育", "エネルギー", "物流・運輸", "官公庁・非営利",
    "サービス・インフラ", "その他",
]

_ENRICH_SYSTEM = """あなたは日本語のビジネス情報抽出AIです。
企業のWebページHTMLが与えられます。以下のJSON形式で企業情報を抽出してください。
値が不明な場合は null にしてください。必ずJSONのみを返してください。

{
  "overview": "事業概要（300文字以内、日本語）",
  "industry": "業界カテゴリ（次のいずれか: """ + "、".join(_SF_INDUSTRIES) + """）",
  "employee_count": 従業員数（整数）または null,
  "usp": "強み・特徴（200文字以内、日本語）",
  "persona": "求める人物像（150文字以内）または null"
}"""


class WebEnricher:
    """
    企業WebサイトをHTTP取得 → Claude API で構造化情報を抽出。
    Notionデータで空のフィールドを補完するために使用する。
    """

    _MAX_HTML_CHARS = 12_000   # Claudeに渡すHTMLの最大文字数
    _CLAUDE_MODEL   = "claude-haiku-4-5-20251001"  # コスト優先
    _REQUEST_DELAY  = 1.5      # サイトへの連続アクセス間隔（秒）

    def __init__(self) -> None:
        if not _ANTHROPIC_AVAILABLE:
            raise ImportError(
                "anthropic パッケージが未インストールです。"
                "`pip install anthropic` を実行してください。"
            )
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY が未設定です（config/.env）")
        self._client = _anthropic_module.Anthropic(api_key=api_key)

    # ── 公開API ────────────────────────────────

    def enrich(
        self,
        company_name: str,
        url: Optional[str] = None,
        existing: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        企業名・URL を受け取り、空フィールドをWebから補完した辞書を返す。

        Args:
            company_name : 企業名（ログ・プロンプト用）
            url          : 企業HPのURL（Notionから取得済み）
            existing     : 既にNotionから取得済みのフィールド辞書

        Returns:
            既存データ + web補完データ のマージ結果
        """
        existing = existing or {}
        result = dict(existing)

        if not url:
            logger.debug("[Enrich] URL未設定のためスキップ: %s", company_name)
            return result

        # 既にすべての主要フィールドが埋まっていればスキップ
        needs_enrich = not all([
            existing.get("overview"),
            existing.get("industry"),
            existing.get("employee_count"),
        ])
        if not needs_enrich:
            logger.debug("[Enrich] 補完不要: %s", company_name)
            return result

        try:
            html_text = self._fetch_page(url)
            if not html_text:
                return result
            web_data = self._extract_with_claude(company_name, html_text)
            result = self._merge(existing, web_data)
            logger.info("[Enrich] 補完完了: %s", company_name)
        except Exception as exc:
            logger.warning("[Enrich] エラー（スキップ）: %s → %s", company_name, exc)

        time.sleep(self._REQUEST_DELAY)
        return result

    # ── 内部メソッド ────────────────────────────

    def _fetch_page(self, url: str) -> Optional[str]:
        """URLからHTMLを取得してテキスト化する"""
        import httpx
        try:
            resp = httpx.get(
                url,
                follow_redirects=True,
                timeout=10,
                headers={"User-Agent": "Mozilla/5.0 (compatible; HRSupportBot/1.0)"},
            )
            resp.raise_for_status()
            # HTMLタグを除去してテキストのみ抽出
            raw = resp.text
            clean = re.sub(r"<script[^>]*>.*?</script>", " ", raw, flags=re.DOTALL | re.IGNORECASE)
            clean = re.sub(r"<style[^>]*>.*?</style>",  " ", clean, flags=re.DOTALL | re.IGNORECASE)
            clean = re.sub(r"<[^>]+>", " ", clean)
            clean = re.sub(r"\s+", " ", clean).strip()
            return clean[:self._MAX_HTML_CHARS]
        except Exception as exc:
            logger.debug("[Enrich] fetch失敗 (%s): %s", url, exc)
            return None

    def _extract_with_claude(self, company_name: str, html_text: str) -> Dict[str, Any]:
        """ClaudeにHTML文字列を渡して構造化データを抽出する"""
        user_msg = (
            f"企業名: {company_name}\n\n"
            f"Webページ内容:\n{html_text}"
        )
        response = self._client.messages.create(
            model=self._CLAUDE_MODEL,
            max_tokens=512,
            system=_ENRICH_SYSTEM,
            messages=[{"role": "user", "content": user_msg}],
        )
        raw_text = response.content[0].text.strip()

        # JSONブロック抽出（```json ... ``` 対応）
        json_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if not json_match:
            logger.warning("[Enrich] JSON抽出失敗: %s", raw_text[:200])
            return {}

        data = json.loads(json_match.group())
        # 型・値を検証
        validated: Dict[str, Any] = {}
        if data.get("overview"):
            validated["overview"] = str(data["overview"])[:800]
        if data.get("industry") and data["industry"] in _SF_INDUSTRIES:
            validated["industry"] = data["industry"]
        if data.get("employee_count") and isinstance(data["employee_count"], (int, float)):
            validated["employee_count"] = str(int(data["employee_count"]))
        if data.get("usp"):
            validated["usp"] = str(data["usp"])[:300]
        if data.get("persona"):
            validated["persona"] = str(data["persona"])[:300]
        return validated

    @staticmethod
    def _merge(existing: Dict[str, Any], web_data: Dict[str, Any]) -> Dict[str, Any]:
        """Notion既存データを優先し、空のフィールドのみWebデータで補完する"""
        result = dict(existing)
        for key, value in web_data.items():
            if not result.get(key) and value:
                result[key] = value
                logger.debug("  [Web補完] %s = %s", key, str(value)[:60])
        return result


# ──────────────────────────────────────────────
# SFクライアント（クライアントAccount専用）
# ──────────────────────────────────────────────

class SFCompanyClient:
    """クライアントAccount の CRUD ラッパー"""

    RECORDTYPE = SF_CLIENT_RECORDTYPE

    def __init__(self) -> None:
        from simple_salesforce import Salesforce  # type: ignore
        self.sf = Salesforce(
            username=os.environ["SF_USERNAME"],
            password=os.environ["SF_PASSWORD"],
            security_token=os.environ["SF_SECURITY_TOKEN"],
            domain=os.environ.get("SF_DOMAIN", "login"),
        )

    def fetch_all(self) -> List[Dict[str, Any]]:
        """全クライアントAccountを取得"""
        soql = (
            "SELECT Id, Name, Website, Description, NumberOfEmployees, "
            "Field1__c, Field3__c "
            f"FROM Account WHERE RecordTypeId = '{self.RECORDTYPE}' "
            "ORDER BY Name LIMIT 2000"
        )
        result = self.sf.query(soql)
        records = result.get("records", [])
        logger.info("[SF] クライアントAccount取得: %d社", len(records))
        return records

    def update(self, account_id: str, fields: Dict[str, Any]) -> bool:
        """Account を更新する（Noneフィールドはスキップ）"""
        clean = {k: v for k, v in fields.items() if v is not None and v != ""}
        if not clean:
            return True
        try:
            self.sf.Account.update(account_id, clean)
            return True
        except Exception as exc:
            logger.error("[SF] 更新エラー: id=%s, %s", account_id, exc)
            return False

    def create(self, fields: Dict[str, Any]) -> Optional[str]:
        """新規クライアントAccountを作成して ID を返す"""
        fields["RecordTypeId"] = self.RECORDTYPE
        clean = {k: v for k, v in fields.items() if v is not None and v != ""}
        try:
            result = self.sf.Account.create(clean)
            account_id = result.get("id")
            logger.info("[SF] 新規Account作成: %s → %s", fields.get("Name"), account_id)
            return account_id
        except Exception as exc:
            logger.error("[SF] 作成エラー: name=%s, %s", fields.get("Name"), exc)
            return None

    def build_fields(self, company: Dict[str, Any]) -> Dict[str, Any]:
        """
        Notionデータ辞書をSF Accountフィールド辞書に変換する。

        SFフィールドマッピング:
          Name             ← company["name"]
          Website          ← company["hp_url"]
          Description      ← 【事業概要】\n{overview}\n\n【選考フロー】\n{selection_flow}
                             （既存の所在地情報は上書き）
          NumberOfEmployees← company["employee_count"]（整数変換）
          Field1__c        ← company["industry"]（multipicklist）
        """
        overview      = company.get("overview", "") or ""
        selection     = company.get("selection_flow", "") or ""
        usp           = company.get("usp", "") or ""
        persona       = company.get("persona", "") or ""

        desc_parts = []
        if overview:
            desc_parts.append(f"【事業概要】\n{overview[:800]}")
        if selection:
            desc_parts.append(f"【選考フロー】\n{selection[:400]}")
        if usp:
            desc_parts.append(f"【USP・強み】\n{usp[:300]}")
        if persona:
            desc_parts.append(f"【求める人物像】\n{persona[:300]}")

        description = "\n\n".join(desc_parts) if desc_parts else None

        # 従業員数を整数変換
        emp_raw = company.get("employee_count", "") or ""
        employee_count: Optional[int] = None
        if emp_raw:
            digits = re.sub(r"[^\d]", "", emp_raw)
            if digits:
                employee_count = int(digits)

        return {
            "Name"            : company["name"],
            "Website"         : company.get("hp_url") or None,
            "Description"     : description,
            "NumberOfEmployees": employee_count,
            "Field1__c"       : company.get("industry") or None,
        }


# ──────────────────────────────────────────────
# Supabaseクライアント
# ──────────────────────────────────────────────

class SupabaseCompanyClient:
    """Supabase companies テーブルの upsert ラッパー"""

    def __init__(self) -> None:
        url = SUPABASE_URL
        key = SUPABASE_SERVICE_KEY
        if not url or not key:
            raise EnvironmentError(
                "SUPABASE_URL / SUPABASE_SERVICE_KEY が未設定です。config/.env を確認してください。"
            )
        import httpx
        self._client = httpx.Client(
            base_url=f"{url}/rest/v1",
            headers={
                "apikey"       : key,
                "Authorization": f"Bearer {key}",
                "Content-Type" : "application/json",
                "Prefer"       : "resolution=merge-duplicates,return=representation",
            },
            timeout=30,
        )

    def upsert(self, record: Dict[str, Any]) -> bool:
        """
        sf_account_id をキーに upsert する。
        sf_account_id がない場合は notion_id をキーに upsert する。
        """
        try:
            resp = self._client.post("/companies", json=record)
            resp.raise_for_status()
            return True
        except Exception as exc:
            logger.error("[Supabase] upsert エラー: %s", exc)
            return False

    def build_record(
        self,
        company: Dict[str, Any],
        sf_account_id: str,
    ) -> Dict[str, Any]:
        """Notionデータ + SF ID を Supabase companies レコードに変換"""
        recommend_points = []
        if company.get("usp"):
            recommend_points.append(company["usp"])
        if company.get("persona"):
            recommend_points.append(f"【求める人物像】{company['persona']}")

        grad_years_raw = company.get("grad_years", "") or ""
        grad_years = [g.strip() for g in grad_years_raw.split(",") if g.strip()] or None

        return {
            "sf_account_id"   : sf_account_id,
            "notion_id"       : company.get("notion_page_id"),
            "name"            : company["name"],
            "industry"        : company.get("industry") or None,
            "overview"        : company.get("overview") or None,
            "recommend_points": recommend_points or None,
            "website_url"     : company.get("hp_url") or None,
            "session_dates"   : company.get("session_dates") or None,
            "hiring_count"    : company.get("hiring_count") or None,
            "grad_years"      : grad_years,
            "is_published"    : True,
            "updated_at"      : datetime.datetime.utcnow().isoformat() + "Z",
        }


# ──────────────────────────────────────────────
# メイン同期ロジック
# ──────────────────────────────────────────────

class NotionToSFSync:
    """
    Notion企業DB → SF（クライアントAccount）+ Supabase の同期オーケストレーター
    """

    def __init__(self, dry_run: bool = False, enrich: bool = False) -> None:
        self.dry_run = dry_run
        self.notion  = NotionCompanyDB(NOTION_API_KEY, NOTION_COMPANY_DB_ID)
        self.sf      = SFCompanyClient()
        try:
            self.supabase = SupabaseCompanyClient()
            self._supabase_ok = True
        except EnvironmentError:
            logger.warning("[Supabase] 接続情報未設定 → Supabase同期をスキップします")
            self.supabase = None  # type: ignore
            self._supabase_ok = False

        # Web エンリッチメント
        self._enricher: Optional[WebEnricher] = None
        if enrich:
            try:
                self._enricher = WebEnricher()
                logger.info("[Enrich] Webエンリッチメント: 有効")
            except (ImportError, EnvironmentError) as exc:
                logger.warning("[Enrich] 無効化: %s", exc)

    def run(
        self,
        company_filter: Optional[str] = None,
        since: Optional[datetime.datetime] = None,
    ) -> Dict[str, int]:
        """
        フル同期を実行する。

        Args:
            company_filter : 特定企業名でフィルタ（部分一致）
            since          : この日時以降の新規Notionページのみ対象

        Returns:
            {"updated": N, "created": N, "skipped": N, "error": N}
        """
        stats = {"updated": 0, "created": 0, "skipped": 0, "error": 0}

        # 1. データ取得
        logger.info("=== Notion→SF同期 開始 (dry_run=%s) ===", self.dry_run)
        if since:
            notion_companies = self.notion.fetch_new_since(since)
            logger.info("[Notion] 新規取得: %d社（%s以降）", len(notion_companies), since.date())
        else:
            notion_companies = self.notion.fetch_all_companies()

        sf_accounts = self.sf.fetch_all()

        # 2. フィルタ
        if company_filter:
            notion_companies = [
                c for c in notion_companies
                if company_filter.lower() in c["name"].lower()
            ]
            logger.info("[Filter] 対象: %d社", len(notion_companies))

        # 3. 各Notion企業を処理
        for company in notion_companies:
            name = company["name"]
            try:
                # Web エンリッチメント（有効時: 空フィールドをWebで補完）
                if self._enricher:
                    company = self._enricher.enrich(
                        company_name=name,
                        url=company.get("hp_url"),
                        existing=company,
                    )

                matched_sf = match_company_name(name, sf_accounts)
                sf_fields  = self.sf.build_fields(company)

                if matched_sf:
                    # ── 既存SFレコードを更新
                    account_id = matched_sf["Id"]
                    logger.info("[MATCH] %s → SF:%s", name, account_id)
                    if not self.dry_run:
                        ok = self.sf.update(account_id, sf_fields)
                        if ok:
                            stats["updated"] += 1
                        else:
                            stats["error"] += 1
                            continue
                    else:
                        logger.info("  [DRY] SF更新スキップ: %s", sf_fields)
                        stats["updated"] += 1

                else:
                    # ── 新規SFレコードを作成
                    logger.info("[NEW] %s → SF新規作成", name)
                    if not self.dry_run:
                        account_id = self.sf.create(sf_fields)
                        if not account_id:
                            stats["error"] += 1
                            continue
                        # SF Accountsリストに追加（後続のマッチ精度向上）
                        sf_accounts.append({"Id": account_id, "Name": name})
                        stats["created"] += 1
                    else:
                        logger.info("  [DRY] SF作成スキップ: %s", sf_fields)
                        account_id = f"DRY_RUN_{name}"
                        stats["created"] += 1

                # ── Supabase upsert
                if self._supabase_ok and not self.dry_run:
                    sb_record = self.supabase.build_record(company, account_id)  # type: ignore
                    self.supabase.upsert(sb_record)  # type: ignore
                elif self.dry_run:
                    logger.info("  [DRY] Supabase upsertスキップ: %s", name)

            except Exception as exc:
                logger.error("[ERROR] %s: %s", name, exc, exc_info=True)
                stats["error"] += 1

        # 4. サマリー
        logger.info(
            "=== 同期完了 === 更新:%d 新規:%d スキップ:%d エラー:%d",
            stats["updated"], stats["created"], stats["skipped"], stats["error"]
        )
        return stats

    def run_single(self, company_name: str) -> bool:
        """1社のみ同期する（デバッグ・手動補完用）"""
        stats = self.run(company_filter=company_name)
        return stats["error"] == 0


# ──────────────────────────────────────────────
# CLI エントリポイント
# ──────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Notion企業DB → SF + Supabase 同期")
    parser.add_argument("--dry-run",  action="store_true", help="書き込みをスキップして確認のみ")
    parser.add_argument("--company",  type=str, default=None, help="特定企業名でフィルタ（部分一致）")
    parser.add_argument("--since",    type=str, default=None, help="この日付以降の新規Notionページのみ対象 (YYYY-MM-DD)")
    parser.add_argument(
        "--enrich",
        action="store_true",
        help=(
            "WebエンリッチメントON: 企業HPをHTTP取得 → Claude APIで空フィールドを自動補完。"
            "ANTHROPIC_API_KEY が必要。"
        ),
    )
    args = parser.parse_args()

    since = None
    if args.since:
        since = datetime.datetime.strptime(args.since, "%Y-%m-%d")

    syncer = NotionToSFSync(dry_run=args.dry_run, enrich=args.enrich)
    stats  = syncer.run(company_filter=args.company, since=since)

    print(f"\n{'[DRY-RUN] ' if args.dry_run else ''}同期結果:")
    print(f"  更新: {stats['updated']}社")
    print(f"  新規: {stats['created']}社")
    print(f"  エラー: {stats['error']}社")


if __name__ == "__main__":
    main()
