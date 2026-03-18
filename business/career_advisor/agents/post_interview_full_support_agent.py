#!/usr/bin/env python3
"""
面談後フルサポートエージェント — v3 (マルチチャンネル並列配信版)

アーキテクチャ:
  Transcript
      │
      ▼
  [PRE] KV Entity Extraction  ← トークン節約型・要約プロトコル
      │  [STU][EXP][MOT][ACT][COM][STA][ADV][IND]
      │
      ├── enrich_from_sheet (sequential / KV → Sheet補完)
      │
      ▼
  [PARALLEL ThreadPoolExecutor × 4]
  ┌──────────────┬───────────────┬──────────────┬──────────────┐
  │ SF Write     │ Notion Fill   │ LINE Draft   │  Slack       │
  │ (Account+   │ (企業DB欠損  │ (KV→下書き  │  (SF完了後   │
  │  Task)      │  自動補完)    │  +CB copy)   │   通知)      │
  └──────────────┴───────────────┴──────────────┴──────────────┘
      │
      ▼
  Summary → execute() → @secure_output (PII洗浄) → archive_intelligence()

ポータビリティ:
  config/domain_hr.json でドメイン設定を外部化。
  別業界への転用は DOMAIN_CONFIG_PATH の差し替えのみ。

使い方:
  python3 career_advisor/agents/post_interview_full_support_agent.py
  python3 career_advisor/agents/post_interview_full_support_agent.py --dry-run
  または main.py で「面談後フルサポート」と入力
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field as dc_field
from datetime import date
from typing import Dict, List, Optional, Tuple

# ──────────────────────────────────────────────
# パス解決
# ──────────────────────────────────────────────

_AGENTS_DIR = os.path.dirname(os.path.abspath(__file__))
_CAREER_DIR = os.path.dirname(_AGENTS_DIR)
_PROJECT_ROOT = _CAREER_DIR

sys.path.insert(0, _CAREER_DIR)
sys.path.insert(0, _AGENTS_DIR)
sys.path.insert(0, os.path.join(_CAREER_DIR, "utils"))

import anthropic
import requests as _requests
from dotenv import load_dotenv

load_dotenv(os.path.join(_PROJECT_ROOT, "config", ".env"))

from agents.base_agent import BaseAgent

_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

NOTION_API_KEY = os.environ.get("NOTION_API_KEY", "")
NOTION_DB_ID   = "5cdbd39197f94db7b7e275d317166bfd"
_NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

DOMAIN_CONFIG_PATH = os.path.join(_PROJECT_ROOT, "config", "domain_hr.json")


def _load_domain() -> dict:
    with open(DOMAIN_CONFIG_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


# ──────────────────────────────────────────────
# ステップ実行結果
# ──────────────────────────────────────────────

@dataclass
class StepResult:
    label: str
    success: bool
    message: str
    output: str = ""

    def __str__(self) -> str:
        mark = "✓" if self.success else "✗"
        return f"  [{mark}] {self.label}: {self.message}"


# ──────────────────────────────────────────────
# 依存モジュール
# ──────────────────────────────────────────────

from salesforce_agent import (  # type: ignore
    extract_sf_data,
    enrich_from_sheet,
    search_account,
    write_account,
    write_task,
    get_sf,
)
from report_agent import (  # type: ignore
    generate_report,
    _save_to_file as _save_report_file,
)


# ══════════════════════════════════════════════
# § 1  KV Entity Extraction  (トークン節約型・要約プロトコル)
# ══════════════════════════════════════════════

KV_SCHEMA = {
    "STU": "姓|名|大学名|学部|卒業年度|学科区分",
    "EXP": "ガクチカ1|ガクチカ2|…（パイプ区切り・最大3件）",
    "MOT": "就活軸1|就活軸2|…（パイプ区切り・最大3件）",
    "ACT": "次のアクション1|…（パイプ区切り）",
    "COM": "企業名1|企業名2|…（議事録中に登場した企業・パイプ区切り）",
    "STA": "初回/2回目|Phase（初回面談済/送客済等）",
    "ADV": "CA名|面談日YYYY-MM-DD|面談時間",
    "IND": "志望業界1|志望業界2|…（パイプ区切り）",
}

_KV_SYSTEM = (
    "あなたは議事録の最小情報抽出アシスタントです。\n"
    "指定された固定フォーマット（KV形式）のみを出力してください。\n"
    "情報がない場合は「-」を使用。説明・前置き不要。\n\n"
    "出力フォーマット:\n"
    + "\n".join(f"[{tag}] {hint}" for tag, hint in KV_SCHEMA.items())
)


def kv_extract(transcript: str) -> dict:
    """
    議事録からKV形式でビジネスエンティティを抽出する（トークン節約型）。

    フルテキストを各チャンネルに送信する代わりにKVを使用することで、
    下流処理のトークン消費を最大70〜90%削減する。

    Returns:
        {"STU": [...], "EXP": [...], "MOT": [...], "ACT": [...],
         "COM": [...], "STA": [...], "ADV": [...], "IND": [...]}
    """
    print("  [KV] ビジネスエンティティを抽出中...")
    response = _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        system=_KV_SYSTEM,
        messages=[{"role": "user", "content": f"議事録:\n{transcript[:6000]}"}],
    )
    raw = response.content[0].text.strip()
    return _parse_kv(raw)


def _parse_kv(raw: str) -> dict:
    """KVテキストをタグ→リスト の辞書に変換する"""
    result: Dict[str, List[str]] = {}
    for line in raw.splitlines():
        m = re.match(r"\[([A-Z]+)\]\s*(.*)", line.strip())
        if not m:
            continue
        tag, value = m.group(1), m.group(2).strip()
        items = [v.strip() for v in value.split("|") if v.strip() and v.strip() != "-"]
        result[tag] = items
    return result


def kv_to_str(kv: dict) -> str:
    """KV辞書を読みやすい文字列に変換する"""
    lines = []
    for tag, items in kv.items():
        lines.append(f"[{tag}] {' | '.join(items) if items else '-'}")
    return "\n".join(lines)


# ══════════════════════════════════════════════
# § 2  Notion 自動補完エンジン
# ══════════════════════════════════════════════

# 自動補完対象フィールドと出力指示
_NOTION_FILL_TARGETS: Dict[str, str] = {
    "事業概要":   "事業内容・ビジネスモデルを3〜5文で説明。不明な場合は「要確認」と記載。",
    "選考フロー": "選考ステップを「ES → 一次面接 → …」形式で記述。不明な場合は「要確認」と記載。",
    "USP":        "この企業の独自の強み・差別化ポイントを3点箇条書き。",
    "ペルソナ":   "この企業が求める学生像を2〜3文で記述（スキル・マインド・志向性）。",
}

_NOTION_FILL_SYSTEM = (
    "あなたはHR支援エージェントのNotion企業情報補完アシスタントです。\n"
    "企業情報の空欄フィールドを推測・生成します。\n"
    "Claude の知識と提供コンテキストを活用し、具体的・正確に記述してください。\n"
    "500文字以内、日本語、内容のみ出力（見出し・前置き不要）。"
)


def _notion_search_page(
    company_name: str,
) -> Optional[Tuple[str, dict, dict]]:
    """
    Notion DBで企業を検索し (page_id, page_props, db_schema) を返す。
    見つからない場合は None。
    """
    try:
        # DB スキーマ取得（プロパティ型を確認するため）
        db_resp = _requests.get(
            f"https://api.notion.so/v1/databases/{NOTION_DB_ID}",
            headers=_NOTION_HEADERS, timeout=15,
        )
        db_resp.raise_for_status()
        db_schema: dict = db_resp.json().get("properties", {})

        # タイトルプロパティを特定
        title_prop = next(
            (k for k, v in db_schema.items() if v.get("type") == "title"),
            "名前",
        )

        # DB Query
        payload = {
            "filter": {
                "property": title_prop,
                "title": {"contains": company_name},
            }
        }
        q_resp = _requests.post(
            f"https://api.notion.so/v1/databases/{NOTION_DB_ID}/query",
            headers=_NOTION_HEADERS, json=payload, timeout=15,
        )
        q_resp.raise_for_status()
        pages = q_resp.json().get("results", [])
        if not pages:
            return None

        page = pages[0]
        return (page["id"], page.get("properties", {}), db_schema)

    except Exception as exc:
        print(f"    [Notion] 検索エラー ({company_name}): {exc}")
        return None


def _notion_fill_page(
    page_id: str,
    page_props: dict,
    db_schema: dict,
    company_name: str,
    kv: dict,
    dry_run: bool,
) -> List[str]:
    """
    1企業ページの欠損フィールドをClaudeで補完してNotionを更新する。

    Returns:
        更新したフィールド名のリスト
    """
    context = (
        f"企業名: {company_name}\n"
        f"議事録から抽出した就活軸・業界情報:\n"
        f"[MOT] {' | '.join(kv.get('MOT', []))}\n"
        f"[IND] {' | '.join(kv.get('IND', []))}\n"
        f"[EXP] {' | '.join(kv.get('EXP', []))}"
    )

    updates: Dict[str, dict] = {}
    filled_fields: List[str] = []

    for field_name, instruction in _NOTION_FILL_TARGETS.items():
        # Notion上の実際のプロパティ名を探す（柔軟マッチング）
        notion_key = _find_notion_key(db_schema, field_name)
        if not notion_key:
            continue  # このDBにはそのフィールドが存在しない

        # 現在値の確認
        current_prop = page_props.get(notion_key, {})
        current_val = _extract_rich_text(current_prop)
        if current_val.strip():
            continue  # 既に値あり → スキップ

        # Claude で生成
        prompt = (
            f"企業「{company_name}」の「{field_name}」を記述してください。\n\n"
            f"【コンテキスト】\n{context}\n\n"
            f"【指示】{instruction}"
        )
        resp = _client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            system=_NOTION_FILL_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        generated = resp.content[0].text.strip()

        # プロパティの型に応じた更新ペイロードを構築
        prop_type = db_schema.get(notion_key, {}).get("type", "rich_text")
        if prop_type == "rich_text":
            updates[notion_key] = {
                "rich_text": [{"type": "text", "text": {"content": generated[:1990]}}]
            }
            filled_fields.append(field_name)
        # title / select 等は今回はスキップ

    if not updates:
        return []

    if dry_run:
        print(f"    [Notion][DRY-RUN] {company_name}: {filled_fields} を補完予定")
        return filled_fields

    # PATCH リクエスト
    patch_resp = _requests.patch(
        f"https://api.notion.so/v1/pages/{page_id}",
        headers=_NOTION_HEADERS,
        json={"properties": updates},
        timeout=30,
    )
    patch_resp.raise_for_status()
    print(f"    [Notion] {company_name}: {filled_fields} を更新しました")
    return filled_fields


def _find_notion_key(db_schema: dict, target: str) -> Optional[str]:
    """DBスキーマからターゲットフィールド名に近いキーを返す"""
    target_norm = target.lower().replace(" ", "")
    for key in db_schema:
        key_norm = key.lower().replace(" ", "").replace("　", "")
        if target_norm in key_norm or key_norm in target_norm:
            return key
    return None


def _extract_rich_text(prop: dict) -> str:
    """Notionプロパティから文字列を抽出する"""
    for key in ("rich_text", "title"):
        items = prop.get(key, [])
        if items:
            return "".join(t.get("plain_text", "") for t in items)
    return ""


def _step_notion_autofill(kv: dict, dry_run: bool) -> StepResult:
    """
    [COM] に含まれる企業のNotionページを自動補完するパイプラインステップ。
    """
    companies = kv.get("COM", [])
    if not companies:
        return StepResult("Notion自動補完", True, "対象企業なし（[COM]が空）")

    updated_summary: List[str] = []
    skipped: List[str] = []

    for company in companies:
        found = _notion_search_page(company)
        if not found:
            skipped.append(company)
            continue

        page_id, page_props, db_schema = found
        filled = _notion_fill_page(
            page_id, page_props, db_schema, company, kv, dry_run
        )
        if filled:
            updated_summary.append(f"{company}({', '.join(filled)})")
        else:
            updated_summary.append(f"{company}(欠損なし)")

    msg_parts = []
    if updated_summary:
        msg_parts.append("更新: " + " / ".join(updated_summary))
    if skipped:
        msg_parts.append("DB未登録: " + ", ".join(skipped))

    return StepResult(
        "Notion自動補完",
        True,
        " | ".join(msg_parts) if msg_parts else "処理完了",
    )


# ══════════════════════════════════════════════
# § 3  並列配信パイプライン — 各ステップ関数
# ══════════════════════════════════════════════

def _copy_to_clipboard(text: str) -> bool:
    try:
        subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
        return True
    except Exception:
        return False


def _step_sf_write(
    data: dict, domain: dict, dry_run: bool
) -> Tuple[StepResult, Optional[str]]:
    """SF PersonAccount + Task の作成・更新ステップ"""
    if dry_run:
        return StepResult("SF登録", True, "[DRY-RUN] スキップ"), None

    try:
        sf = get_sf()
        s = data.get("student", {})
        full_name = (
            f"{s.get('last_name', '')} {s.get('first_name', '')}".strip()
            or "（不明）"
        )
        existing = search_account(sf, full_name)
        is_existing = existing is not None
        existing_id = existing.get("Id") if existing else None

        account_id = write_account(sf, data, existing_id=existing_id)
        task_id = write_task(sf, data, account_id=account_id, is_existing=is_existing)

        mode = "更新" if is_existing else "新規作成"
        return (
            StepResult("SF登録", True,
                       f"{mode} / Account={account_id} / Task={task_id}",
                       output=account_id),
            account_id,
        )
    except Exception as exc:
        return StepResult("SF登録", False, str(exc)), None


def _step_line_draft(kv: dict, domain: dict) -> Tuple[StepResult, str]:
    """KV情報からLINEフォロー下書きを生成してクリップボードにコピーするステップ"""
    try:
        comm = domain.get("communication", {})
        channel = comm.get("channel", "LINE")
        hints = "\n".join(
            f"- {h}" for h in comm.get("post_meeting_template_hints", [])
        )

        mot_str = " / ".join(kv.get("MOT", [])) or "未記録"
        act_str = "\n".join(f"・{a}" for a in kv.get("ACT", [])) or "特になし"
        student_parts = kv.get("STU", [])
        student_name = (
            f"{student_parts[0]} {student_parts[1]}".strip()
            if len(student_parts) >= 2 else "（学生名）"
        )

        system_prompt = (
            f"あなたはキャリアアドバイザーの{channel}文章作成アシスタントです。\n"
            f"絵文字: {'使わない' if comm.get('no_emoji') else '適宜使う'}\n"
            f"プレースホルダー: {comm.get('placeholder_format', '[  ]')}\n\n"
            f"【文章ガイドライン】\n{hints}\n出力は文章のみ。"
        )
        prompt = (
            f"【学生名】{student_name}\n"
            f"【就活軸・モチベーション】{mot_str}\n"
            f"【次のアクション】\n{act_str}\n\n"
            "面談後フォローメッセージを作成してください。"
        )

        resp = _client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}],
        )
        draft = resp.content[0].text.strip()
        copied = _copy_to_clipboard(draft)
        cb = "クリップボード済み ✓" if copied else "(CB コピー失敗)"

        return (
            StepResult(f"{channel}下書き", True, f"生成完了 / {cb}", output=draft),
            draft,
        )
    except Exception as exc:
        return StepResult("LINE下書き", False, str(exc)), ""


def _step_report(
    kv: dict, data: dict, domain: dict
) -> Tuple[StepResult, str, str]:
    """所感レポートを生成・保存してターミナルに表示するステップ"""
    try:
        s = data.get("student", {})
        a = data.get("activity", {})

        student_parts = kv.get("STU", [])
        full_name = (
            f"{student_parts[0]} {student_parts[1]}".strip()
            if len(student_parts) >= 2 else
            f"{s.get('last_name', '')} {s.get('first_name', '')}".strip() or "不明"
        )
        university = (
            student_parts[2] if len(student_parts) >= 3
            else s.get("university", "不明")
        )
        faculty = (
            student_parts[3] if len(student_parts) >= 4
            else s.get("faculty", "")
        )
        adv_parts = kv.get("ADV", [])
        meeting_date = adv_parts[1] if len(adv_parts) >= 2 else date.today().isoformat()
        advisor_name = adv_parts[0] if adv_parts else a.get("advisor_name", "未記録")

        report_data = {
            "student_name": full_name,
            "university": f"{university} {faculty}".strip() or "不明",
            "date": meeting_date,
            "duration": adv_parts[2] if len(adv_parts) >= 3 else a.get("duration", "未記録"),
            "advisor_name": advisor_name,
            "meeting_type": a.get("meeting_type", "未記録"),
            "memo": (
                a.get("summary", "") + "\n"
                + "\n".join(f"・{x}" for x in kv.get("ACT", []))
            ).strip(),
        }

        report_text = generate_report(report_data)
        report_path = _save_report_file(report_text, full_name, meeting_date)

        return (
            StepResult("所感レポート", True, report_path, output=report_text),
            report_path,
            report_text,
        )
    except Exception as exc:
        return StepResult("所感レポート", False, str(exc)), "", ""


def _step_slack_notify(
    kv: dict,
    domain: dict,
    account_id: Optional[str],
    dry_run: bool,
) -> StepResult:
    """Slack学生スレッドに面談サマリーを投稿するステップ"""
    notify = domain.get("notification", {})
    if not notify.get("enabled"):
        return StepResult("Slack通知", True, "無効（domain設定）")

    student_parts = kv.get("STU", [])
    student_name = (
        f"{student_parts[0]} {student_parts[1]}".strip()
        if len(student_parts) >= 2 else "不明"
    )
    adv_parts = kv.get("ADV", [])
    meeting_date = adv_parts[1] if len(adv_parts) >= 2 else date.today().isoformat()
    advisor_name = adv_parts[0] if adv_parts else "未記録"
    act_text = "\n".join(f"  ・{a}" for a in kv.get("ACT", [])) or "  なし"
    mot_text = " / ".join(kv.get("MOT", [])) or "-"

    message = (
        f"*面談完了 {meeting_date}*\n"
        f"担当: {advisor_name}  SF: {account_id or '未登録'}\n\n"
        f"*就活軸:* {mot_text}\n\n"
        f"*次のアクション:*\n{act_text}"
    )

    # スレッド検索
    thread: Optional[dict] = None
    try:
        from slack_sdk import WebClient
        user_token = os.environ.get("SLACK_USER_TOKEN", "")
        if user_token:
            slack_user = WebClient(token=user_token)
            channels = notify.get("search_channels", [])
            marker = notify.get("thread_marker", "📍")
            for ch in channels:
                try:
                    resp = slack_user.search_messages(
                        query=f"{marker}{student_name} in:<#{ch}>", count=5
                    )
                    matches = resp.get("messages", {}).get("matches", [])
                    if matches:
                        m = matches[0]
                        thread = {
                            "channel": m.get("channel", {}).get("id", ch),
                            "thread_ts": m.get("ts"),
                        }
                        break
                except Exception:
                    pass
    except ImportError:
        pass

    if not thread:
        return StepResult("Slack通知", False, "スレッド未発見（手動投稿が必要）")

    if dry_run or notify.get("post_on_dry_run") is False and dry_run:
        return StepResult("Slack通知", True, f"[DRY-RUN] ch={thread['channel']} スキップ")

    try:
        from slack_sdk import WebClient
        from slack_sdk.errors import SlackApiError
        bot_token = os.environ.get("SLACK_BOT_TOKEN", "")
        if not bot_token:
            return StepResult("Slack通知", False, "SLACK_BOT_TOKEN 未設定")
        slack_bot = WebClient(token=bot_token)
        slack_bot.chat_postMessage(
            channel=thread["channel"],
            thread_ts=thread.get("thread_ts"),
            text=message,
        )
        return StepResult("Slack通知", True,
                          f"投稿完了 ch={thread['channel']}")
    except Exception as exc:
        return StepResult("Slack通知", False, str(exc))


# ══════════════════════════════════════════════
# § 4  PostInterviewFullSupportAgent
# ══════════════════════════════════════════════

class PostInterviewFullSupportAgent(BaseAgent):
    """
    面談後フルサポートエージェント — v3 マルチチャンネル並列配信版

    KVプロトコルによるトークン節約 + ThreadPoolExecutorによる並列実行で、
    議事録貼り付けから全チャンネル配信完了まで最速で処理する。
    """

    agent_key = "post_interview_full_support"
    agent_name = "面談後フルサポート"
    agent_desc = (
        "tldv議事録 → [KV抽出] → "
        "[SF|Notion自動補完|LINE|Slack] 並列配信 → PII洗浄 → ノウハウ蓄積"
    )

    def __init__(self, dry_run: bool = False) -> None:
        super().__init__(dry_run=dry_run)
        self._domain = _load_domain()

    def run(self) -> Optional[str]:
        sep = "=" * 62
        print(f"\n{sep}")
        print("  面談後フルサポートエージェント v3 — マルチチャンネル並列配信")
        if self.dry_run:
            print("  [DRY-RUN] SF/Slackへの書き込みはスキップします")
        print(sep)

        transcript = self._receive_transcript()
        if not transcript:
            print("議事録が入力されませんでした。終了します。")
            return None

        return self.run_workflow(transcript)

    def run_workflow(self, transcript: str) -> str:
        """
        コアワークフロー。外部からも直接呼び出し可能。

        返り値は execute() → @secure_output → archive_intelligence() へ渡り、
        PII洗浄 + ノウハウ蓄積が自動実行される。
        """
        today = date.today().isoformat()
        all_results: List[StepResult] = []

        # ──────────────────────────────────────
        # PRE: KV Entity Extraction（トークン節約）
        # ──────────────────────────────────────
        self._header("PRE", "KV エンティティ抽出（トークン節約型プロトコル）")
        try:
            kv = kv_extract(transcript)
            print(f"\n{kv_to_str(kv)}\n")
            all_results.append(
                StepResult("KV抽出", True,
                           f"抽出完了（{len(kv)}タグ）")
            )
        except Exception as exc:
            print(f"  [ERROR] KV抽出失敗: {exc}")
            all_results.append(StepResult("KV抽出", False, str(exc)))
            kv = {}

        # ──────────────────────────────────────
        # STEP 1: SF用フル抽出（精度優先・フルテキスト使用）
        # ──────────────────────────────────────
        self._header(1, "SF用フルデータ抽出（精度優先）")
        sf_data: Optional[dict] = None
        try:
            sf_data = extract_sf_data(transcript)
            all_results.append(StepResult("SF用抽出", True, "完了"))
        except Exception as exc:
            print(f"  [WARN] SF用抽出失敗（SF登録はスキップ）: {exc}")
            all_results.append(StepResult("SF用抽出", False, str(exc)))

        # ──────────────────────────────────────
        # STEP 2: Sheets補完（sequential）
        # ──────────────────────────────────────
        self._header(2, "Google Sheets で個人情報を補完中...")
        adv_parts = kv.get("ADV", [])
        meeting_date = adv_parts[1] if len(adv_parts) >= 2 else today
        if sf_data:
            try:
                sf_data = enrich_from_sheet(sf_data, meeting_date=meeting_date)
                all_results.append(StepResult("Sheets補完", True, "完了"))
            except Exception as exc:
                all_results.append(StepResult("Sheets補完", False, str(exc)))
        else:
            all_results.append(StepResult("Sheets補完", True, "SF抽出なしのためスキップ"))

        # ──────────────────────────────────────
        # STEP 3+: 並列配信パイプライン
        # ──────────────────────────────────────
        self._header("PARALLEL", "多重配信パイプライン（SF / Notion / LINE / レポート）起動")

        domain = self._domain
        dry_run = self.dry_run

        sf_result: Optional[StepResult] = None
        sf_account_id: Optional[str] = None
        line_draft = ""
        report_path = ""
        report_text = ""

        with ThreadPoolExecutor(max_workers=4) as executor:
            # SF, Notion, LINE, レポートを並列実行
            f_sf: Future = executor.submit(
                _step_sf_write, sf_data or {}, domain, dry_run
            )
            f_notion: Future = executor.submit(
                _step_notion_autofill, kv, dry_run
            )
            f_line: Future = executor.submit(
                _step_line_draft, kv, domain
            )
            f_report: Future = executor.submit(
                _step_report, kv, sf_data or {}, domain
            )

            # SF完了を待ってSlackを起動（Account IDが必要なため）
            sf_step_result, sf_account_id = f_sf.result()
            sf_result = sf_step_result
            print(f"  [SF]     {sf_result}")

            f_slack: Future = executor.submit(
                _step_slack_notify, kv, domain, sf_account_id, dry_run
            )

            # 残りのfutureを回収
            notion_result: StepResult = f_notion.result()
            line_step_result, line_draft = f_line.result()
            report_step_result, report_path, report_text = f_report.result()
            slack_result: StepResult = f_slack.result()

        # 並列実行結果をまとめて表示
        for r in [sf_result, notion_result, line_step_result,
                  report_step_result, slack_result]:
            print(str(r))
            all_results.append(r)

        # LINE下書きを枠付き表示（クリップボードコピー済み）
        if line_draft:
            print(f"\n  ── LINEフォロー下書き（クリップボード済み ✓）──")
            print(line_draft)
            print("  " + "─" * 52)

        # 所感レポートを全文表示
        if report_text:
            print(f"\n  ── 所感レポート ({report_path}) ──")
            print(report_text)
            print("  " + "─" * 52)

        # ──────────────────────────────────────
        # STEP 4: レポートはSTEP3で並列生成済み
        # Slack通知も並列完了済み
        # 完了サマリーを構築して返す
        # ──────────────────────────────────────
        final_summary = self._build_summary(
            kv, sf_account_id, report_path, line_draft, all_results,
        )
        print("\n" + "=" * 62)
        print(final_summary)
        print("=" * 62)

        # execute() → @secure_output → archive_intelligence() へ渡る
        return final_summary

    # ──────────────────────────────────────────
    # ユーティリティ
    # ──────────────────────────────────────────

    @staticmethod
    def _header(step, label: str) -> None:
        print(f"\n{'─' * 62}")
        label_str = f"STEP {step}" if isinstance(step, int) else f"[{step}]"
        print(f"{label_str}  {label}")
        print("─" * 62)

    def _receive_transcript(self) -> str:
        session_label = self._domain.get("entity", {}).get("session_label", "面談")
        print(f"\n{session_label}議事録を貼り付けてください（空行2回で確定）")
        print("─" * 62)
        lines: list = []
        blank_count = 0
        try:
            while True:
                line = input()
                if line == "":
                    blank_count += 1
                    if blank_count >= 2:
                        break
                    lines.append(line)
                else:
                    blank_count = 0
                    lines.append(line)
        except (KeyboardInterrupt, EOFError):
            pass
        return "\n".join(lines).strip()

    def _build_summary(
        self,
        kv: dict,
        sf_account_id: Optional[str],
        report_path: str,
        line_draft: str,
        all_results: List[StepResult],
    ) -> str:
        domain_name = self._domain.get("domain_name", "")
        mode = "[DRY-RUN] " if self.dry_run else ""
        stu = kv.get("STU", [])
        adv = kv.get("ADV", [])

        student_name = (
            f"{stu[0]} {stu[1]}".strip() if len(stu) >= 2 else "不明"
        )
        meeting_date = adv[1] if len(adv) >= 2 else date.today().isoformat()
        advisor_name = adv[0] if adv else "未記録"

        lines = [
            f"  {mode}完了サマリー ({domain_name})",
            f"  {'─' * 54}",
            f"  学生名    : {student_name}",
            f"  面談日    : {meeting_date}",
            f"  担当      : {advisor_name}",
            f"  SF Account: {sf_account_id or '未登録'}",
            f"  レポート  : {report_path or '未保存'}",
            f"  KV タグ   : {list(kv.keys())}",
            f"  {'─' * 54}",
            "  ステップ実行結果:",
        ]
        for r in all_results:
            lines.append(str(r))

        if line_draft:
            lines += ["", "  ── LINE下書き（クリップボード済み）──", line_draft]

        return "\n".join(lines)


# ──────────────────────────────────────────────
# エントリポイント
# ──────────────────────────────────────────────

def run(dry_run: bool = False) -> None:
    PostInterviewFullSupportAgent(dry_run=dry_run).execute()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="面談後フルサポートエージェント v3",
        epilog=(
            "例:\n"
            "  python3 post_interview_full_support_agent.py\n"
            "  python3 post_interview_full_support_agent.py --dry-run"
        ),
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="SF/Slackへの書き込みをスキップしてテスト実行",
    )
    args = parser.parse_args()
    run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
