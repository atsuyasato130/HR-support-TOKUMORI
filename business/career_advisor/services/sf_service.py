"""
sf_service.py — Salesforce 操作サービスレイヤー

mcp_salesforce_notion.py / salesforce_agent.py に散らばっていた SF 操作ロジックを
単一の SFService クラスに集約する。

FastAPI エンドポイント・MCP サーバー・エージェント CLI の
いずれからも同じインターフェースで呼び出せる「信頼できる唯一の SF 窓口」。

使い方:
    from career_advisor.services.sf_service import SFService

    svc = SFService()
    account = svc.search_by_name("山田花子")
    svc.update_account(account["Id"], {"Phase__pc": "一次面接"})
    svc.log_meeting(account["Id"], student_name="山田花子", ...)
"""

from __future__ import annotations

import os
import sys
import datetime
import logging
from typing import Any, Dict, List, Optional, Tuple

# プロジェクトルート
_SVC_DIR = os.path.dirname(os.path.abspath(__file__))            # career_advisor/services/
_CA_DIR  = os.path.dirname(_SVC_DIR)                             # career_advisor/
_ROOT    = os.path.dirname(_CA_DIR)                              # project root

from dotenv import load_dotenv
load_dotenv(os.path.join(_ROOT, "config", ".env"))

logger = logging.getLogger("sf_service")

# ──────────────────────────────────────────────
# 定数（salesforce_agent.py と共通管理）
# ──────────────────────────="──────────────────

SF_RECORDTYPE_SHINSOTSU   = "0122w000001Ry2hAAC"   # 新卒
SF_RECORDTYPE_CHUTO       = "0122w000001Ry2cAAC"   # 中途
SF_RECORDTYPE_CLIENT      = "0122w000001RweZAAS"   # クライアント

# 支援ステータス有効値
SUPPORT_STATUS_ACTIVE = "支援中"

# フェーズ有効値（重み付け用）
PHASE_WEIGHTS: Dict[str, int] = {
    "最終面接"   : 100,
    "二次面接"   : 85,
    "一次面接"   : 75,
    "書類選考"   : 60,
    "ES選考"     : 55,
    "エントリー" : 40,
    "送客済"     : 30,
    "初回面談済" : 20,
}


# ──────────────────────────────────────────────
# SFService — メインクラス
# ──────────────────────────────────────────────

class SFService:
    """
    Salesforce 操作を担うサービスクラス。

    インスタンスはスレッドセーフではないため、リクエストごとに生成するか
    依存性注入（FastAPI Depends）を使うこと。
    """

    def __init__(self) -> None:
        self._sf = None  # 遅延初期化

    # ──────── 接続 ────────

    def get_client(self):
        """simple_salesforce クライアントを返す（遅延初期化・再利用）"""
        if self._sf is None:
            from simple_salesforce import Salesforce  # type: ignore
            self._sf = Salesforce(
                username=os.environ["SF_USERNAME"],
                password=os.environ["SF_PASSWORD"],
                security_token=os.environ["SF_SECURITY_TOKEN"],
                domain=os.environ.get("SF_DOMAIN", "login"),
            )
        return self._sf

    # ──────── 検索 ────────

    def search_by_name(self, full_name: str) -> Optional[Dict[str, Any]]:
        """
        氏名（スペース区切り）で PersonAccount を検索する。
        複数ヒット時は最初の1件を返す。

        Args:
            full_name: "山田花子" または "山田 花子"

        Returns:
            SF Account レコード辞書 or None
        """
        parts = full_name.replace("　", " ").strip().split()
        last_name  = parts[0] if parts else full_name
        first_name = parts[1] if len(parts) > 1 else ""

        try:
            sf = self.get_client()
            if first_name:
                soql = (
                    "SELECT Id, Name, LastName, FirstName, Phase__pc, Status__pc, "
                    "InterviewDate__pc, InterviewExpectedDate__pc, ReportPerson__c, "
                    "LastModifiedDate "
                    f"FROM Account "
                    f"WHERE LastName = '{last_name}' AND FirstName = '{first_name}' "
                    f"AND RecordTypeId = '{SF_RECORDTYPE_SHINSOTSU}' LIMIT 5"
                )
            else:
                soql = (
                    "SELECT Id, Name, LastName, FirstName, Phase__pc, Status__pc, "
                    "InterviewDate__pc, InterviewExpectedDate__pc, ReportPerson__c, "
                    "LastModifiedDate "
                    f"FROM Account "
                    f"WHERE LastName = '{last_name}' "
                    f"AND RecordTypeId = '{SF_RECORDTYPE_SHINSOTSU}' LIMIT 5"
                )
            result = sf.query(soql)
            records = result.get("records", [])
            if not records:
                return None
            if len(records) > 1:
                logger.warning("[SFService] search_by_name: %d件ヒット, 最初を使用: %s", len(records), full_name)
            return records[0]
        except Exception as exc:
            logger.error("[SFService] search_by_name エラー: %s", exc, exc_info=True)
            return None

    def search_by_id(self, account_id: str) -> Optional[Dict[str, Any]]:
        """SF Account ID でレコードを1件取得する"""
        try:
            sf = self.get_client()
            result = sf.Account.get(account_id)
            return dict(result) if result else None
        except Exception as exc:
            logger.error("[SFService] search_by_id エラー: id=%s, %s", account_id, exc, exc_info=True)
            return None

    def soql_query(self, soql: str) -> List[Dict[str, Any]]:
        """汎用 SOQL クエリを実行し、レコードリストを返す"""
        try:
            sf = self.get_client()
            result = sf.query(soql)
            return result.get("records", [])
        except Exception as exc:
            logger.error("[SFService] soql_query エラー: %s", exc, exc_info=True)
            return []

    def find_university_id(self, name: str) -> Optional[str]:
        """
        大学名から CustomObject1__c の ID を検索する（完全一致 → 部分一致の順）

        Returns:
            SF レコード ID or None
        """
        if not name:
            return None
        try:
            sf = self.get_client()
            escaped = name.replace("'", "\\'")
            res = sf.query(f"SELECT Id FROM CustomObject1__c WHERE Name = '{escaped}' LIMIT 1")
            if res.get("records"):
                return res["records"][0]["Id"]
            res2 = sf.query(f"SELECT Id FROM CustomObject1__c WHERE Name LIKE '%{escaped}%' LIMIT 1")
            if res2.get("records"):
                return res2["records"][0]["Id"]
            return None
        except Exception as exc:
            logger.error("[SFService] find_university_id エラー: %s", exc, exc_info=True)
            return None

    # ──────── 書き込み ────────

    def create_account(self, fields: Dict[str, Any]) -> Optional[str]:
        """
        PersonAccount を新規作成する。

        Args:
            fields: Account フィールド辞書

        Returns:
            作成された Account ID or None
        """
        try:
            sf = self.get_client()
            result = sf.Account.create(fields)
            account_id = result.get("id")
            logger.info("[SFService] Account 作成: id=%s, name=%s", account_id, fields.get("LastName"))
            return account_id
        except Exception as exc:
            logger.error("[SFService] create_account エラー: %s", exc, exc_info=True)
            return None

    def update_account(self, account_id: str, fields: Dict[str, Any]) -> bool:
        """
        既存 Account を更新する。

        Args:
            account_id : SF Account ID
            fields     : 更新フィールド辞書（差分のみ渡す）

        Returns:
            True: 成功 / False: 失敗
        """
        try:
            sf = self.get_client()
            sf.Account.update(account_id, fields)
            logger.info("[SFService] Account 更新: id=%s, fields=%s", account_id, list(fields.keys()))
            return True
        except Exception as exc:
            logger.error("[SFService] update_account エラー: id=%s, %s", account_id, exc, exc_info=True)
            return False

    def update_selection_phase(self, account_id: str, new_phase: str) -> bool:
        """
        選考フェーズ（Phase__pc）を更新する便利メソッド。
        有効な Phase 値かどうかをチェックしてから更新する。

        Args:
            account_id : SF Account ID
            new_phase  : 新しい Phase__pc 値

        Returns:
            True: 成功 / False: 無効フェーズ or API エラー
        """
        valid_phases = list(PHASE_WEIGHTS.keys()) + [
            "内定", "内定承諾済", "辞退", "不採用", "支援終了",
        ]
        if new_phase not in valid_phases:
            logger.warning("[SFService] 無効な Phase 値: %s", new_phase)
            # 無効でも試みる（SF 側でバリデーション）
        return self.update_account(account_id, {"Phase__pc": new_phase})

    def log_meeting(
        self,
        account_id: str,
        student_name: str,
        meeting_date: str,
        summary: str,
        next_actions: str = "",
        duration: str = "",
        advisor_name: str = "",
        is_second_or_later: bool = False,
    ) -> Optional[str]:
        """
        面談活動記録（Task）を作成する。

        Args:
            account_id         : SF Account ID
            student_name       : 学生名（件名に使用）
            meeting_date       : 面談日（YYYY-MM-DD）
            summary            : 面談サマリー
            next_actions       : 次のアクション（複数行可）
            duration           : 面談時間（例: "60分"）
            advisor_name       : 担当CA名
            is_second_or_later : 2回目以降の面談かどうか

        Returns:
            作成された Task ID or None
        """
        try:
            sf = self.get_client()
            prefix = "2回目以降面談" if is_second_or_later else "面談"
            subject = f"{prefix} - {student_name} ({meeting_date})"

            desc_parts: List[str] = []
            if is_second_or_later:
                desc_parts.append("【2回目以降の面談】")
            if summary:
                desc_parts.append(f"【面談内容】\n{summary}")
            if next_actions:
                desc_parts.append(f"【次のアクション】\n{next_actions}")
            if duration:
                desc_parts.append(f"【面談時間】{duration}")
            if advisor_name:
                desc_parts.append(f"【担当CA】{advisor_name}")

            task_fields = {
                "Subject"      : subject,
                "Description"  : "\n\n".join(desc_parts),
                "ActivityDate" : meeting_date,
                "Status"       : "Completed",
                "WhatId"       : account_id,
            }
            result = sf.Task.create(task_fields)
            task_id = result.get("id")
            logger.info("[SFService] Task 作成: id=%s, subject=%s", task_id, subject)
            return task_id
        except Exception as exc:
            logger.error("[SFService] log_meeting エラー: account=%s, %s", account_id, exc, exc_info=True)
            return None

    def get_student_pipelines(self, account_id: str) -> List[Dict[str, Any]]:
        """
        指定 Account に紐づく Pipeline__c（選考パイプライン）を取得する。
        存在しない場合は空リストを返す。
        """
        try:
            sf = self.get_client()
            soql = (
                "SELECT Id, Company__c, Status__c, Phase__c, InterviewDate__c "
                f"FROM Pipeline__c WHERE Account__c = '{account_id}' LIMIT 100"
            )
            result = sf.query(soql)
            return result.get("records", [])
        except Exception as exc:
            logger.debug("[SFService] get_student_pipelines: %s (Pipeline__c が存在しないかも)", exc)
            return []

    # ──────── 優先度クエリ ────────

    def get_priority_students(self) -> List[Dict[str, Any]]:
        """
        優先アクションが必要な学生をSFから一括取得する。
        PriorityEngine.score() に渡す raw データを返す。

        取得条件:
          - Status__pc = '支援中'
          - RecordTypeId = 新卒
          - 以下のいずれかに該当:
            a) InterviewExpectedDate__pc が今日以前（面接結果確認待ち）
            b) Phase__pc が ['最終面接', '二次面接', '一次面接', '書類選考'] で LastModifiedDate が3日以上前
            c) Phase__pc = '初回面談済' で LastModifiedDate が7日以上前（打診未送付）

        Returns:
            SF Account レコードのリスト
        """
        today      = datetime.date.today().isoformat()
        three_days = (datetime.date.today() - datetime.timedelta(days=3)).isoformat()
        seven_days = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()

        base = (
            "SELECT Id, Name, LastName, FirstName, Phase__pc, Status__pc, "
            "InterviewExpectedDate__pc, InterviewDate__pc, "
            "ReportPerson__c, LastModifiedDate, Field12__c, OfficialLineRegistration__pc "
            "FROM Account "
            f"WHERE RecordTypeId = '{SF_RECORDTYPE_SHINSOTSU}' "
            f"AND Status__pc = '{SUPPORT_STATUS_ACTIVE}' "
        )

        queries = [
            # a) 面接結果確認待ち
            base + (
                f"AND InterviewExpectedDate__pc <= {today} "
                "AND Phase__pc IN ('最終面接', '二次面接', '一次面接') "
                "ORDER BY InterviewExpectedDate__pc ASC LIMIT 100"
            ),
            # b) 選考フェーズ中だが 3日以上アクションなし
            base + (
                "AND Phase__pc IN ('最終面接', '二次面接', '一次面接', '書類選考') "
                f"AND LastModifiedDate <= {three_days}T00:00:00Z "
                "ORDER BY LastModifiedDate ASC LIMIT 100"
            ),
            # c) 初回面談済 + 7日以上打診なし
            base + (
                "AND Phase__pc = '初回面談済' "
                f"AND LastModifiedDate <= {seven_days}T00:00:00Z "
                "ORDER BY LastModifiedDate ASC LIMIT 100"
            ),
        ]

        seen: set = set()
        all_records: List[Dict[str, Any]] = []

        for soql in queries:
            for rec in self.soql_query(soql):
                rid = rec.get("Id", "")
                if rid not in seen:
                    seen.add(rid)
                    all_records.append(rec)

        logger.info("[SFService] get_priority_students: %d件取得", len(all_records))
        return all_records

    def get_count(self, object_type: str, conditions: str = "") -> int:
        """COUNT クエリで件数を返す"""
        where = f" WHERE {conditions}" if conditions else ""
        try:
            sf = self.get_client()
            result = sf.query(f"SELECT COUNT(Id) cnt FROM {object_type}{where}")
            return result["records"][0]["cnt"]
        except Exception as exc:
            logger.error("[SFService] get_count エラー: %s", exc, exc_info=True)
            return -1


# ──────────────────────────────────────────────
# PriorityEngine — スコアリングロジック
# ──────────────────────────────────────────────

class PriorityEngine:
    """
    SF レコードから「優先度スコア」を計算し、
    CA が今日対応すべき順にソートされたリストを返す。

    スコア基準:
      100 : 24時間以内に面接予定
      90  : 最終面接フェーズ + 3日以上アクションなし
      80  : 二次/一次面接フェーズ + 3日以上アクションなし
      70  : 面接予定日が過去で結果未更新
      60  : 初回面談済 + LINE 未登録（打診未送付の疑い）
      50  : 初回面談済 + 7日以上アクションなし
      30  : 支援終了フラグ or 長期（30日以上）未連絡
    """

    def score(self, record: Dict[str, Any]) -> Tuple[str, str, int]:
        """
        1件の SF Account レコードを評価してスコアを返す。

        Returns:
            (priority: str, reason: str, score: int)
            priority は "high" / "medium" / "low" のいずれか
        """
        now   = datetime.datetime.now()
        today = datetime.date.today()

        phase         = record.get("Phase__pc", "") or ""
        last_modified = record.get("LastModifiedDate", "") or ""
        interview_exp = record.get("InterviewExpectedDate__pc", "") or ""
        line_reg      = record.get("OfficialLineRegistration__pc", True)

        # ── 最終更新からの日数を計算
        days_since_action = 999
        if last_modified:
            try:
                mod_dt = datetime.datetime.strptime(last_modified[:10], "%Y-%m-%d").date()
                days_since_action = (today - mod_dt).days
            except ValueError:
                pass

        # ── 面接予定日の評価
        hours_to_interview: Optional[float] = None
        interview_is_past = False
        if interview_exp:
            try:
                exp_date = datetime.datetime.strptime(interview_exp[:10], "%Y-%m-%d")
                delta    = exp_date - now
                hours_to_interview = delta.total_seconds() / 3600
                interview_is_past  = exp_date.date() < today
            except ValueError:
                pass

        # ── スコアリング（条件は上位から評価し、最初にマッチしたものを採用）

        # HIGH: 24時間以内に面接
        if hours_to_interview is not None and 0 <= hours_to_interview <= 24:
            return ("high", f"面接予定まで{int(hours_to_interview)}時間以内 ({interview_exp})", 100)

        # HIGH: 最終面接フェーズ + 3日以上アクションなし
        if phase == "最終面接" and days_since_action >= 3:
            return ("high", f"最終面接フェーズで{days_since_action}日間アクションなし", 90)

        # HIGH: 面接予定日が過去で結果未更新（面接フェーズのまま）
        if interview_is_past and phase in ("最終面接", "二次面接", "一次面接"):
            return ("high", f"面接予定日({interview_exp})が過去なのに結果未更新", 70)

        # MEDIUM: 二次/一次面接フェーズ + 3日以上アクションなし
        if phase in ("二次面接", "一次面接") and days_since_action >= 3:
            return ("medium", f"{phase}フェーズで{days_since_action}日間アクションなし", 80)

        # MEDIUM: 初回面談済 + LINE 未登録（打診未送付の疑い）
        if phase == "初回面談済" and not line_reg:
            return ("medium", "初回面談済・LINE未登録（打診未送付の可能性）", 60)

        # MEDIUM: 初回面談済 + 7日以上アクションなし
        if phase == "初回面談済" and days_since_action >= 7:
            return ("medium", f"初回面談済から{days_since_action}日間アクションなし（打診未送付）", 50)

        # LOW: 30日以上アクションなし
        if days_since_action >= 30:
            return ("low", f"{days_since_action}日間アクションなし（長期未連絡）", 30)

        # その他（支援中だが特段の緊急度なし）
        return ("low", f"通常フォロー（{phase}）", 10)

    def build_priority_list(
        self,
        records: List[Dict[str, Any]],
        advisor_filter: Optional[str] = None,
        priority_filter: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        SF レコードリストをスコアリングして優先度順に返す。

        Args:
            records          : SFService.get_priority_students() の返り値
            advisor_filter   : 担当CA名でフィルタ（省略時は全員）
            priority_filter  : "high" / "medium" / "low" でフィルタ
            limit            : 最大返却件数

        Returns:
            [{
                "sf_id", "student_name", "advisor_name",
                "phase", "priority", "score", "reason",
                "interview_expected_date", "days_since_action",
                "last_modified_date",
            }, ...]  スコア降順
        """
        scored: List[Tuple[int, Dict[str, Any]]] = []

        for rec in records:
            advisor = rec.get("ReportPerson__c", "") or ""
            if advisor_filter and advisor != advisor_filter:
                continue

            priority, reason, score = self.score(rec)
            if priority_filter and priority != priority_filter:
                continue

            # 最終更新からの日数を再計算（表示用）
            last_mod = rec.get("LastModifiedDate", "") or ""
            days_action = 0
            if last_mod:
                try:
                    mod_date   = datetime.datetime.strptime(last_mod[:10], "%Y-%m-%d").date()
                    days_action = (datetime.date.today() - mod_date).days
                except ValueError:
                    pass

            item = {
                "sf_id"                  : rec.get("Id", ""),
                "student_name"           : rec.get("Name", ""),
                "advisor_name"           : advisor,
                "phase"                  : rec.get("Phase__pc", ""),
                "priority"               : priority,
                "score"                  : score,
                "reason"                 : reason,
                "interview_expected_date": rec.get("InterviewExpectedDate__pc"),
                "days_since_action"      : days_action,
                "last_modified_date"     : last_mod[:10] if last_mod else None,
            }
            scored.append((score, item))

        # スコア降順でソート
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:limit]]
