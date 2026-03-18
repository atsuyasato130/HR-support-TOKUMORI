"""
Google Sheets クライアント

【セットアップ手順】
1. Google Cloud Console でサービスアカウントを作成
   https://console.cloud.google.com/
   → IAM & Admin → Service Accounts → Create
   → JSON キーをダウンロード

2. Google Sheets API を有効化
   → APIs & Services → Enable APIs → "Google Sheets API" を検索・有効化

3. ダウンロードした JSON キーのパスを .env に設定
   GOOGLE_SERVICE_ACCOUNT_JSON=/path/to/service-account.json

4. スプレッドシートをサービスアカウントのメールアドレスと共有（閲覧権限でOK）
   - サービスアカウントのメールアドレスは JSON ファイルの "client_email" フィールド
"""

from __future__ import annotations
import os
import json


def get_sheets_client():
    """gspread クライアントを初期化して返す。

    認証の優先順位:
      1. config/token.json（既存のOAuth2トークン）
      2. GOOGLE_SERVICE_ACCOUNT_JSON 環境変数（サービスアカウント）
    """
    import gspread
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    # ── 1. OAuth2 token.json（既存の認証情報を流用）
    token_path = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "../config/token.json")
    )
    if os.path.exists(token_path):
        with open(token_path) as f:
            token_data = json.load(f)
        creds = Credentials(
            token=token_data.get("token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri=token_data.get("token_uri"),
            client_id=token_data.get("client_id"),
            client_secret=token_data.get("client_secret"),
            scopes=token_data.get("scopes"),
        )
        # 期限切れなら自動更新
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            token_data["token"] = creds.token
            if creds.expiry:
                token_data["expiry"] = creds.expiry.isoformat()
            with open(token_path, "w") as f:
                json.dump(token_data, f, ensure_ascii=False, indent=2)
        return gspread.authorize(creds)

    # ── 2. サービスアカウント JSON（フォールバック）
    from google.oauth2.service_account import Credentials as SACredentials
    creds_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    if not creds_path:
        raise EnvironmentError(
            "Google認証情報が見つかりません。\n"
            "config/token.json が存在するか、.env に GOOGLE_SERVICE_ACCOUNT_JSON を設定してください。"
        )
    if not os.path.exists(creds_path):
        raise FileNotFoundError(f"サービスアカウントJSONが見つかりません: {creds_path}")

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    creds = SACredentials.from_service_account_file(creds_path, scopes=scopes)
    return gspread.authorize(creds)


def fetch_sheet_as_records(spreadsheet_id: str, sheet_index: int = 0) -> list[dict]:
    """
    スプレッドシートを辞書のリストとして取得する。
    1行目をヘッダーとして扱う。

    Returns:
        [{"氏名": "田中太郎", "メール": "...", ...}, ...]
    """
    gc = get_sheets_client()
    sh = gc.open_by_key(spreadsheet_id)
    ws = sh.get_worksheet(sheet_index)
    return ws.get_all_records()


def fetch_sheet_headers(spreadsheet_id: str, sheet_index: int = 0) -> list[str]:
    """スプレッドシートのヘッダー行（1行目）を返す"""
    gc = get_sheets_client()
    sh = gc.open_by_key(spreadsheet_id)
    ws = sh.get_worksheet(sheet_index)
    all_values = ws.get_all_values()
    return all_values[0] if all_values else []


def search_student_in_sheet(
    spreadsheet_id: str,
    name: str,
    name_col_candidates: list[str] | None = None,
    sheet_index: int = 0,
    meeting_date: str | None = None,
) -> dict | None:
    """
    氏名でシートを検索し、ヒットした行を返す。
    複数ヒット時は meeting_date（面談日）に最も近い「回答日時」の行を優先する。

    Args:
        spreadsheet_id: スプレッドシートID
        name: 検索する氏名（スペース除去して部分一致）
        name_col_candidates: 氏名が入っている可能性のある列名リスト
        sheet_index: シートのインデックス（0始まり）
        meeting_date: 面談日（YYYY-MM-DD形式）。複数ヒット時の絞り込みに使用

    Returns:
        ヒットした行の辞書 or None
    """
    from datetime import datetime

    if name_col_candidates is None:
        name_col_candidates = [
            "お名前を教えてください",         # 実際のシートの列名
            "氏名", "名前", "お名前", "フルネーム", "姓名",
            "last_name", "名前（フルネーム）", "学生氏名",
        ]

    records = fetch_sheet_as_records(spreadsheet_id, sheet_index)
    if not records:
        return None

    # 使用する名前列を特定
    headers = list(records[0].keys())
    name_col = None
    for candidate in name_col_candidates:
        if candidate in headers:
            name_col = candidate
            break

    if name_col is None:
        # ヘッダーに「名」が含まれる列を探す
        for h in headers:
            if "名" in h or "name" in h.lower():
                name_col = h
                break

    if name_col is None:
        return None

    name_clean = name.replace(" ", "").replace("　", "").lower()

    matched = []
    for row in records:
        row_name = str(row.get(name_col, "")).replace(" ", "").replace("　", "").lower()
        if name_clean in row_name or row_name in name_clean:
            matched.append(row)

    if not matched:
        return None
    if len(matched) == 1:
        return matched[0]

    # 複数ヒット時: meeting_date に最も近い「回答日時」の行を返す
    if meeting_date:
        try:
            target = datetime.strptime(meeting_date[:10], "%Y-%m-%d")

            def date_diff(row: dict) -> int:
                raw = str(row.get("回答日時", ""))
                try:
                    d = datetime.strptime(raw[:10], "%Y-%m-%d")
                    return abs((d - target).days)
                except ValueError:
                    return 99999

            return min(matched, key=date_diff)
        except Exception:
            pass

    return matched[0]


# ──────────────────────────────────────────────
# Salesforce フィールドへのマッピング
# ──────────────────────────────────────────────

# シートの列名 → Salesforce フィールドAPI名 のマッピング辞書
SHEET_TO_SF_MAPPING = {
    # ── 実際のシートの列名（Lステップ フォーム）
    "お名前を教えてください": None,            # 姓・名に分割するため別処理
    "フリガナを教えてください": None,           # 姓カナ・名カナに分割する別処理
    "生年月日を教えてください": "seinengappi__c",
    "大学名を教えてください": None,             # 参照型のため別処理
    "学部を教えてください": "Field17__c",
    "学科を教えてください": "gakka__c",
    "高校名を教えてください": "koukomei__pc",   # 高校名
    "卒業年度を教えてください": None,           # GraduationYears__pc（別処理）
    "電話番号": "PersonMobilePhone",
    "メールアドレス": "PersonEmail",
    "在住エリアを教えてください": None,              # 制限ピックリストのためスキップ
    "志望する業界を教えて下さい（※複数選択可）": None,  # multipicklist（別処理）
    "性別を教えてください": None,               # SFに対応フィールドなし

    # ── 汎用列名（他シート対応用）
    "氏名": None,
    "姓": "LastName",
    "名": "FirstName",
    "姓（カナ）": "KanaLastName__pc",
    "名（カナ）": "KanaFirstName__pc",
    "氏名（カナ）": None,
    "フリガナ": None,
    "メール": "PersonEmail",
    "携帯番号": "PersonMobilePhone",
    "携帯": "PersonMobilePhone",
    "生年月日": "seinengappi__c",
    "誕生日": "seinengappi__c",
    "高校名": "koukomei__pc",
    "出身高校": "koukomei__pc",
    "大学名": None,
    "大学": None,
    "学部": "Field17__c",
    "学部名": "Field17__c",
    "学科": "gakka__c",
    "学科名": "gakka__c",
    "学年": None,
    "都道府県": None,   # 制限ピックリストのためスキップ
    "市区町村": None,   # 制限ピックリストのためスキップ
    "志望業界": None,
    "希望業界": None,
    "就活の軸": "Field12__c",
    "就活軸": "Field12__c",
    "ガクチカ": "Field13__c",
    "学チカ": "Field13__c",
}


def map_sheet_row_to_sf_fields(row: dict) -> dict:
    """
    シートの1行（辞書）をSalesforceフィールド辞書に変換する。
    空文字・None は除外する。
    """
    sf_fields = {}

    for col_name, value in row.items():
        if not value:
            continue
        value = str(value).strip()
        if not value:
            continue

        sf_field = SHEET_TO_SF_MAPPING.get(col_name)

        if sf_field:
            sf_fields[sf_field] = value

        # ── 氏名の分割処理
        elif col_name in ("氏名", "名前", "お名前", "フルネーム"):
            parts = value.replace("　", " ").split()
            if len(parts) >= 2:
                sf_fields["LastName"] = parts[0]
                sf_fields["FirstName"] = parts[1]
            else:
                sf_fields["LastName"] = value

        # ── カナ氏名の分割処理
        elif col_name in ("氏名（カナ）", "フリガナ", "カナ氏名", "フリガナを教えてください"):
            parts = value.replace("　", " ").split()
            if len(parts) >= 2:
                sf_fields["KanaLastName__pc"] = parts[0]
                sf_fields["KanaFirstName__pc"] = parts[1]
            else:
                sf_fields["KanaLastName__pc"] = value

        # ── 卒業年度の変換
        elif col_name in ("学年", "卒業年度", "卒業年次", "卒業年度を教えてください"):
            # 例: "3年" → "27卒"（現在27卒ベースで計算）
            # 既に "27卒" 形式ならそのまま使用
            if "卒" in value:
                sf_fields["GraduationYears__pc"] = value
            # 学年から計算は複雑なためそのまま記録しない

        # ── 性別の変換（PersonGenderIdentity: 男/女）
        elif col_name in ("性別", "性別を教えてください"):
            gender_map = {"男性": "男", "女性": "女", "男": "男", "女": "女"}
            gender_val = gender_map.get(value, "")
            if gender_val:
                sf_fields["PersonGenderIdentity"] = gender_val

    return sf_fields


def get_spreadsheet_id_from_url(url: str) -> Optional[str]:
    """Google スプレッドシートのURLからIDを抽出"""
    import re
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", url)
    return match.group(1) if match else None


# ──────────────────────────────────────────────
# ロギング設定
# ──────────────────────────────────────────────

import logging
import logging.handlers
from typing import Optional, List, Dict, Tuple

_PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "../../"))
_LOG_PATH = os.path.join(_PROJECT_ROOT, "logs", "sync_activity.log")
os.makedirs(os.path.dirname(_LOG_PATH), exist_ok=True)

_sync_logger = logging.getLogger("sync_activity")
if not _sync_logger.handlers:
    _handler = logging.handlers.RotatingFileHandler(
        _LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    _handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    )
    _sync_logger.addHandler(_handler)
    _sync_logger.setLevel(logging.DEBUG)


# ──────────────────────────────────────────────
# StatusAutoUpdater
# ──────────────────────────────────────────────

class StatusAutoUpdater:
    """
    選考進捗管理スプレッドシートの該当セルを自動書き換えする。

    スプレッドシートの列構成（例）:
      A: 学生名  B: SFレコードID  C: 企業名  D: ステータス  E: 更新日時

    検索優先順:
      1. sf_record_id が渡された場合 → SFレコードID列で完全一致検索
      2. 渡されない場合 → 「学生名 + 企業名」の組み合わせで検索

    Args:
        spreadsheet_id : 進捗管理スプレッドシートのID
        sheet_index    : シートのインデックス（0始まり）
        student_col    : 学生名が入る列名（デフォルト: "学生名"）
        company_col    : 企業名が入る列名（デフォルト: "企業名"）
        status_col     : ステータスが入る列名（デフォルト: "ステータス"）
        sf_id_col      : SFレコードIDが入る列名（デフォルト: "SFレコードID"）
        updated_at_col : 更新日時を書き込む列名（デフォルト: "更新日時"、Noneでスキップ）
    """

    def __init__(
        self,
        spreadsheet_id: str,
        sheet_index: int = 0,
        student_col: str = "学生名",
        company_col: str = "企業名",
        status_col: str = "ステータス",
        sf_id_col: str = "SFレコードID",
        updated_at_col: Optional[str] = "更新日時",
    ) -> None:
        self.spreadsheet_id = spreadsheet_id
        self.sheet_index = sheet_index
        self.student_col = student_col
        self.company_col = company_col
        self.status_col = status_col
        self.sf_id_col = sf_id_col
        self.updated_at_col = updated_at_col

    def update_status(
        self,
        new_status: str,
        student_name: Optional[str] = None,
        company_name: Optional[str] = None,
        sf_record_id: Optional[str] = None,
    ) -> bool:
        """
        該当行のステータスセルのみを書き換える。既存フォーマットは保持する。

        Args:
            new_status    : 書き込む新しいステータス文字列
            student_name  : 学生名（sf_record_id がない場合は必須）
            company_name  : 企業名（sf_record_id がない場合は必須）
            sf_record_id  : Salesforce レコードID（優先検索キー）

        Returns:
            True: 更新成功 / False: 該当行なし or エラー
        """
        import datetime

        if not sf_record_id and not (student_name and company_name):
            _sync_logger.error("[StatusAutoUpdater] sf_record_id または 学生名+企業名 のいずれかが必要です")
            return False

        try:
            gc = get_sheets_client()
            sh = gc.open_by_key(self.spreadsheet_id)
            ws = sh.get_worksheet(self.sheet_index)

            all_values = ws.get_all_values()
            if not all_values:
                _sync_logger.warning("[StatusAutoUpdater] シートが空です: %s", self.spreadsheet_id)
                return False

            headers = all_values[0]

            # 列インデックスを解決
            def col_idx(name: str) -> Optional[int]:
                try:
                    return headers.index(name)
                except ValueError:
                    return None

            status_idx = col_idx(self.status_col)
            if status_idx is None:
                _sync_logger.error(
                    "[StatusAutoUpdater] ステータス列 '%s' が見つかりません。headers=%s",
                    self.status_col, headers
                )
                return False

            # 検索: sf_record_id 優先 → 学生名+企業名
            target_row_num: Optional[int] = None  # 1始まり（gspread形式）

            if sf_record_id:
                sf_id_idx = col_idx(self.sf_id_col)
                if sf_id_idx is not None:
                    for i, row in enumerate(all_values[1:], start=2):
                        if len(row) > sf_id_idx and row[sf_id_idx] == sf_record_id:
                            target_row_num = i
                            break

            if target_row_num is None and student_name and company_name:
                stu_idx = col_idx(self.student_col)
                com_idx = col_idx(self.company_col)
                if stu_idx is not None and com_idx is not None:
                    name_clean = student_name.replace(" ", "").replace("　", "").lower()
                    for i, row in enumerate(all_values[1:], start=2):
                        row_name = ""
                        if len(row) > stu_idx:
                            row_name = row[stu_idx].replace(" ", "").replace("　", "").lower()
                        row_company = row[com_idx] if len(row) > com_idx else ""
                        if name_clean in row_name and company_name in row_company:
                            target_row_num = i
                            break

            if target_row_num is None:
                _sync_logger.warning(
                    "[StatusAutoUpdater] 該当行なし: student=%s, company=%s, sf_id=%s",
                    student_name, company_name, sf_record_id
                )
                return False

            # ステータスセルだけ更新（フォーマット保持のため最小範囲で操作）
            ws.update_cell(target_row_num, status_idx + 1, new_status)

            # 更新日時列があれば書き込む
            if self.updated_at_col:
                upd_idx = col_idx(self.updated_at_col)
                if upd_idx is not None:
                    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ws.update_cell(target_row_num, upd_idx + 1, now_str)

            _sync_logger.info(
                "[StatusAutoUpdater] 更新成功: row=%d, student=%s, company=%s, status=%s",
                target_row_num, student_name, company_name, new_status
            )
            return True

        except Exception as exc:
            _sync_logger.error("[StatusAutoUpdater] 更新エラー: %s", exc, exc_info=True)
            return False

    def bulk_update(self, updates: List[Dict[str, str]]) -> Tuple[int, int]:
        """
        複数行を一括更新する。

        Args:
            updates: [
                {"student_name": "...", "company_name": "...", "new_status": "...", "sf_record_id": "...（任意）"},
                ...
            ]

        Returns:
            (成功件数, 失敗件数)
        """
        success = 0
        fail = 0
        for item in updates:
            ok = self.update_status(
                new_status=item.get("new_status", ""),
                student_name=item.get("student_name"),
                company_name=item.get("company_name"),
                sf_record_id=item.get("sf_record_id"),
            )
            if ok:
                success += 1
            else:
                fail += 1
        _sync_logger.info("[StatusAutoUpdater] bulk_update 完了: success=%d, fail=%d", success, fail)
        return success, fail


# ──────────────────────────────────────────────
# ConsistencyChecker
# ──────────────────────────────────────────────

class ConsistencyChecker:
    """
    Salesforce のステータスとスプレッドシートのステータスを突合し、
    不一致があれば Slack の指定チャンネルに不一致レポートを投稿する。

    使い方:
        checker = ConsistencyChecker(
            spreadsheet_id="...",
            slack_channel_id="C0A2YSANGKS",
        )
        report = checker.run_check(sf_records)
        # sf_records = [{"sf_id": "...", "student_name": "...", "company_name": "...", "sf_status": "..."}, ...]

    SF側のステータスリストは salesforce_agent 等から事前に取得して渡す。
    """

    def __init__(
        self,
        spreadsheet_id: str,
        slack_channel_id: str,
        sheet_index: int = 0,
        student_col: str = "学生名",
        company_col: str = "企業名",
        status_col: str = "ステータス",
        sf_id_col: str = "SFレコードID",
        slack_token_env: str = "SLACK_BOT_TOKEN",
    ) -> None:
        self.spreadsheet_id = spreadsheet_id
        self.slack_channel_id = slack_channel_id
        self.sheet_index = sheet_index
        self.student_col = student_col
        self.company_col = company_col
        self.status_col = status_col
        self.sf_id_col = sf_id_col
        self.slack_token_env = slack_token_env

    def run_check(
        self,
        sf_records: List[Dict[str, str]],
        post_to_slack: bool = True,
    ) -> List[Dict[str, str]]:
        """
        SF レコードリストとスプレッドシートを突合して不一致を検出する。

        Args:
            sf_records: SFから取得したレコードのリスト。各要素:
                {
                    "sf_id"        : "001...",
                    "student_name" : "山田花子",
                    "company_name" : "リクルート",
                    "sf_status"    : "書類選考中",
                }
            post_to_slack: True の場合、不一致があれば Slack に投稿する

        Returns:
            不一致レコードのリスト（一致した場合は空リスト）
        """
        import datetime

        _sync_logger.info("[ConsistencyChecker] 突合チェック開始: SF件数=%d", len(sf_records))

        # スプレッドシートを辞書化（sf_id → sheet_status）
        sheet_map = self._build_sheet_map()

        mismatches: List[Dict[str, str]] = []

        for rec in sf_records:
            sf_id = rec.get("sf_id", "")
            sf_status = rec.get("sf_status", "")
            student_name = rec.get("student_name", "")
            company_name = rec.get("company_name", "")

            sheet_status = sheet_map.get(sf_id, {}).get("status")

            if sheet_status is None:
                # シートに存在しない（新規 or 未登録）
                _sync_logger.debug(
                    "[ConsistencyChecker] シート未登録: sf_id=%s, student=%s", sf_id, student_name
                )
                continue

            if sheet_status != sf_status:
                mismatch = {
                    "sf_id"        : sf_id,
                    "student_name" : student_name,
                    "company_name" : company_name,
                    "sf_status"    : sf_status,
                    "sheet_status" : sheet_status,
                }
                mismatches.append(mismatch)
                _sync_logger.warning(
                    "[ConsistencyChecker] 不一致: student=%s, company=%s, SF=%s, Sheet=%s",
                    student_name, company_name, sf_status, sheet_status
                )

        _sync_logger.info(
            "[ConsistencyChecker] 突合完了: 不一致=%d件", len(mismatches)
        )

        if mismatches and post_to_slack:
            self._post_slack_report(mismatches)

        return mismatches

    def _build_sheet_map(self) -> Dict[str, Dict[str, str]]:
        """スプレッドシートを {sf_id: {status, student_name, company_name}} に変換"""
        try:
            gc = get_sheets_client()
            sh = gc.open_by_key(self.spreadsheet_id)
            ws = sh.get_worksheet(self.sheet_index)
            all_values = ws.get_all_values()
        except Exception as exc:
            _sync_logger.error("[ConsistencyChecker] シート取得エラー: %s", exc, exc_info=True)
            return {}

        if not all_values:
            return {}

        headers = all_values[0]

        def col_idx(name: str) -> Optional[int]:
            try:
                return headers.index(name)
            except ValueError:
                return None

        sf_id_idx = col_idx(self.sf_id_col)
        status_idx = col_idx(self.status_col)
        stu_idx = col_idx(self.student_col)
        com_idx = col_idx(self.company_col)

        result: Dict[str, Dict[str, str]] = {}
        for row in all_values[1:]:
            if sf_id_idx is None or len(row) <= sf_id_idx:
                continue
            sf_id = row[sf_id_idx].strip()
            if not sf_id:
                continue
            result[sf_id] = {
                "status"       : row[status_idx].strip() if status_idx is not None and len(row) > status_idx else "",
                "student_name" : row[stu_idx].strip() if stu_idx is not None and len(row) > stu_idx else "",
                "company_name" : row[com_idx].strip() if com_idx is not None and len(row) > com_idx else "",
            }

        return result

    def _post_slack_report(self, mismatches: List[Dict[str, str]]) -> None:
        """不一致レポートを Slack に投稿する"""
        import datetime
        try:
            from slack_sdk import WebClient
        except ImportError:
            _sync_logger.error("[ConsistencyChecker] slack_sdk が未インストールです: pip install slack-sdk")
            return

        token = os.environ.get(self.slack_token_env, "")
        if not token:
            _sync_logger.error(
                "[ConsistencyChecker] %s が未設定です", self.slack_token_env
            )
            return

        today = datetime.date.today().strftime("%Y-%m-%d")
        lines = [
            f"*【ステータス不一致レポート】{today}*",
            f"_SF とスプレッドシートで {len(mismatches)} 件の不一致が検出されました。_",
            "",
        ]
        for m in mismatches:
            lines.append(
                f"• {m['student_name']} / {m['company_name']}"
                f"  SF=`{m['sf_status']}`  Sheet=`{m['sheet_status']}`"
                f"  (ID: {m['sf_id']})"
            )

        message = "\n".join(lines)

        try:
            client = WebClient(token=token)
            client.chat_postMessage(channel=self.slack_channel_id, text=message)
            _sync_logger.info(
                "[ConsistencyChecker] Slack 投稿完了: channel=%s, 不一致=%d件",
                self.slack_channel_id, len(mismatches)
            )
        except Exception as exc:
            _sync_logger.error("[ConsistencyChecker] Slack 投稿エラー: %s", exc, exc_info=True)
