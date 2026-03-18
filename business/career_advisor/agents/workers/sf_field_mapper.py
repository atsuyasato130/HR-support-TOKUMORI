#!/usr/bin/env python3
"""
SFFieldMapper — PROCESSOR ロール

## 役割（策士兵）
parser_queue から抽出済みNotionデータを読み込み、
SFフィールド名にマッピングして実行命令を processor_queue に書き込む。

このワーカーの責務:
  1. Notion フィールド名 → SF API フィールド名 への変換
  2. SF Account ID の名前マッチング（既存SFレコードから企業名で検索）
  3. 空フィールドのスキップ（None/""はSFに送らない）
  4. 必須フィールド不足のチェックとフラグ立て

LLMは基本不使用（マッピングは静的定義）。
ただし将来的に曖昧なフィールドマッピングが必要になった場合はここに集中させる。

## 入力（state/parser_queue.json）
[{"notion_page_id": "...", "name": "...", "extracted": {...}}]

## 出力（state/processor_queue.json）
[
  {
    "sf_account_id" : "001xx...",
    "sf_name"       : "会社名",
    "notion_page_id": "xxx",
    "update_fields" : {
      "SelectionFlow__c"        : "...",
      "Description__c"          : "...",
      "StrengthOfferPoint__c"   : "...",
      ...
    },
    "requires_manual": false,    # true の場合は EXECUTOR でスキップして警告
    "skip_reason"    : ""
  },
  ...
]

## 使い方
  python3 agents/workers/sf_field_mapper.py
  python3 agents/workers/sf_field_mapper.py --dry-run
"""

from __future__ import annotations

import argparse
import difflib
import logging
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

_AGENTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BASE_DIR   = os.path.dirname(_AGENTS_DIR)
sys.path.insert(0, _BASE_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(_BASE_DIR, "config", ".env"))

from agents.base_worker import BaseWorker, WorkerResult, WorkerRole
from state.state_manager import StateManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(
            os.path.join(_BASE_DIR, "logs", "sf_field_mapper.log"),
            encoding="utf-8",
        ),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("worker.processor.sf_mapper")

# ── Notion → SF フィールドマッピング定義
# キー: Notion抽出フィールド名（notion_page_parser.pyの_FIELD_CANDIDATESに対応）
# 値: SF API フィールド名
NOTION_TO_SF: Dict[str, str] = {
    "selection_flow"        : "SelectionFlow__c",
    "description"           : "Description__c",
    "strength_offer_point"  : "StrengthOfferPoint__c",
    "url_for_introduction"  : "URLForIntroduction__c",
    "introduction_method"   : "IntroductionMethod__c",
    "gakuchika_requirement" : "GakuchikaRequirement__c",
    "feelings_requirement"  : "FeelingsRequirement__c",
    "intelligence_criteria" : "IntelligenceCriteria__c",
    "hot_requirement"       : "HotRequirement__c",
    "batting_company"       : "BattingCompany__c",
    "recruitment_channel"   : "RecruitmentChannel__c",
    "phase"                 : "Phase__c",
    # overview は SF の Description にも使うが、Description__c が優先
}

# 企業名正規化（株式会社等を除去したマッチング用）
_CORP_SUFFIXES = re.compile(
    r"(株式会社|有限会社|合同会社|一般社団法人|公益社団法人|医療法人"
    r"|Inc\.|LLC|Ltd\.|Co\.,?\s*Ltd\.?)",
    re.IGNORECASE,
)

# SF クライアントAccount レコードタイプ ID
SF_CLIENT_RECORDTYPE = os.environ.get("SF_CLIENT_RECORDTYPE", "0122w000001RweZAAS")


class SFFieldMapper(BaseWorker):
    """
    PROCESSOR: Notion抽出データをSFフィールド名にマッピングし、
    SF Account ID を解決して実行命令を生成する。
    """

    role        = WorkerRole.PROCESSOR
    worker_name = "sf_field_mapper"

    def __init__(self, dry_run: bool = False) -> None:
        super().__init__(dry_run=dry_run)
        self._state = StateManager(self.state_path(""))

    def execute(self) -> WorkerResult:
        """
        parser_queue を読み込み、SFフィールドマッピングと Account ID解決を行い、
        processor_queue に書き込む。
        """
        queue = self._state.read_queue("parser_queue")
        if not queue:
            logger.info("[Mapper] parser_queue が空です。スキップ。")
            return WorkerResult(processed=0)

        logger.info("[Mapper] %d件のマッピング開始", len(queue))

        # SF全Account取得（名前マッチング用）
        sf_accounts = self._fetch_sf_accounts()
        logger.info("[Mapper] SF Account取得: %d件", len(sf_accounts))

        processor_records: List[Dict[str, Any]] = []
        errors = 0
        skipped = 0

        for item in queue:
            name           = item.get("name", "unknown")
            notion_page_id = item.get("notion_page_id", "")
            extracted      = item.get("extracted", {})

            try:
                sf_account_id, matched_name = self._resolve_sf_account(name, sf_accounts)

                update_fields = self._build_sf_fields(extracted)

                requires_manual = False
                skip_reason     = ""

                if not sf_account_id:
                    requires_manual = True
                    skip_reason     = f"SFにマッチする企業が見つかりません: '{name}'"
                    logger.warning("[Mapper] SF未マッチ: %s", name)
                elif not update_fields:
                    skipped += 1
                    logger.info("[Mapper] 更新フィールドなし（スキップ）: %s", name)
                    continue

                record = {
                    "sf_account_id"  : sf_account_id or "",
                    "sf_name"        : matched_name or name,
                    "notion_page_id" : notion_page_id,
                    "update_fields"  : update_fields,
                    "requires_manual": requires_manual,
                    "skip_reason"    : skip_reason,
                }
                processor_records.append(record)
                logger.info(
                    "[Mapper] マッピング完了: %s → SF:%s (%d fields)",
                    name, sf_account_id or "未マッチ", len(update_fields),
                )

            except Exception as exc:
                logger.error("[Mapper] エラー: %s → %s", name, exc)
                errors += 1

        if not self.dry_run:
            self._state.write_queue("processor_queue", processor_records)
            self._state.clear_queue("parser_queue")
            logger.info("[Mapper] processor_queue.json に %d件 書き込み完了", len(processor_records))
        else:
            logger.info("[Mapper] [DRY-RUN] 書き込みスキップ。マッピング結果:")
            for r in processor_records:
                flag = "⚠️ manual" if r["requires_manual"] else "✓"
                logger.info(
                    "  %s %s → %s | fields: %s",
                    flag, r["sf_name"], r["sf_account_id"],
                    list(r["update_fields"].keys()),
                )

        return WorkerResult(
            processed=len(processor_records),
            errors=errors,
            skipped=skipped,
        )

    # ── 内部メソッド ──────────────────────────

    def _fetch_sf_accounts(self) -> List[Dict[str, Any]]:
        """SFの全クライアントAccountを取得する（名前マッチング用）"""
        try:
            from simple_salesforce import Salesforce  # type: ignore
            sf = Salesforce(
                username=os.environ["SF_USERNAME"],
                password=os.environ["SF_PASSWORD"],
                security_token=os.environ["SF_SECURITY_TOKEN"],
                domain=os.environ.get("SF_DOMAIN", "login"),
            )
            soql = (
                f"SELECT Id, Name FROM Account "
                f"WHERE RecordTypeId = '{SF_CLIENT_RECORDTYPE}' "
                f"ORDER BY Name LIMIT 2000"
            )
            result = sf.query(soql)
            return result.get("records", [])
        except Exception as exc:
            logger.error("[Mapper] SF Account取得エラー: %s", exc)
            return []

    def _resolve_sf_account(
        self,
        notion_name: str,
        sf_accounts: List[Dict[str, Any]],
        threshold: float = 0.80,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Notion企業名からSF Account IDを解決する。

        Returns:
            (sf_account_id, matched_sf_name) or (None, None)
        """
        n_norm = self._normalize(notion_name)
        best_score   = 0.0
        best_account = None

        for acct in sf_accounts:
            sf_norm = self._normalize(acct.get("Name", ""))
            if n_norm == sf_norm:
                return acct["Id"], acct["Name"]
            score = difflib.SequenceMatcher(None, n_norm, sf_norm).ratio()
            if score > best_score:
                best_score   = score
                best_account = acct

        if best_score >= threshold and best_account:
            logger.debug(
                "[Mapper] 名前マッチ: '%s' ≈ '%s' (%.2f)",
                notion_name, best_account["Name"], best_score,
            )
            return best_account["Id"], best_account["Name"]

        return None, None

    def _build_sf_fields(self, extracted: Dict[str, Any]) -> Dict[str, Any]:
        """
        Notion抽出データをSFフィールド辞書に変換する。
        空値（""、None）はスキップして送らない。
        """
        sf_fields: Dict[str, Any] = {}

        for notion_key, sf_key in NOTION_TO_SF.items():
            value = extracted.get(notion_key, "")
            if value:  # 空文字・Noneはスキップ
                sf_fields[sf_key] = value

        # overview が description より補完的に使える場合
        if not sf_fields.get("Description__c") and extracted.get("overview"):
            sf_fields["Description__c"] = extracted["overview"]

        return sf_fields

    @staticmethod
    def _normalize(name: str) -> str:
        """企業名を正規化してマッチング精度を上げる"""
        name = _CORP_SUFFIXES.sub("", name)
        name = re.sub(r"[\s　・\-_]", "", name)
        return name.lower().strip()


# ──────────────────────────────────────────────
# CLI エントリポイント
# ──────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="NotionデータのSFフィールドマッピング（PROCESSOR）")
    parser.add_argument("--dry-run", action="store_true", help="書き込みスキップ（確認用）")
    args = parser.parse_args()

    worker = SFFieldMapper(dry_run=args.dry_run)
    result = worker.execute()
    print(f"\n{'[DRY-RUN] ' if args.dry_run else ''}マッピング結果: {result}")


if __name__ == "__main__":
    main()
