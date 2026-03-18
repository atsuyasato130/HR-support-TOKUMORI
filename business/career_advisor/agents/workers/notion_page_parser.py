#!/usr/bin/env python3
"""
NotionPageParser — PARSER ロール

## 役割（選別兵）
watcher_queue から notion_page_id を読み込み、Notion ページを取得して
必要最小限のフィールドのみを抽出する。不要なメタデータは完全に削ぎ落とす。
LLMを使わない。次工程（PROCESSOR）に渡すのは整形済みのコンパクトJSONのみ。

## 入力（state/watcher_queue.json）
[{"notion_page_id": "...", "name": "...", "last_edited_time": "..."}]

## 出力（state/parser_queue.json）
[
  {
    "notion_page_id": "xxx",
    "name": "会社名",
    "extracted": {
      "selection_flow"          : "選考フロー本文",
      "description"             : "採用要件本文",
      "strength_offer_point"    : "強み・訴求ポイント",
      "url_for_introduction"    : "https://...",
      "introduction_method"     : "URL" | "ATS" | "グーグルフォーム" | "",
      "gakuchika_requirement"   : "A",
      "feelings_requirement"    : "B",
      "intelligence_criteria"   : "S",
      "hot_requirement"         : "A",
      "batting_company"         : "レバレジーズ;リクルート",
      "recruitment_channel"     : "...",
      "phase"                   : "契約完了" | "契約進行" | "中止" | "クローズ",
      "hp_url"                  : "https://...",
      "overview"                : "事業概要"
    }
  },
  ...
]

## 使い方
  python3 agents/workers/notion_page_parser.py
  python3 agents/workers/notion_page_parser.py --dry-run
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import Any, Dict, List, Optional

_AGENTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BASE_DIR   = os.path.dirname(_AGENTS_DIR)
sys.path.insert(0, _BASE_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(_BASE_DIR, "config", ".env"))

import httpx

from agents.base_worker import BaseWorker, WorkerResult, WorkerRole
from state.state_manager import StateManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(
            os.path.join(_BASE_DIR, "logs", "notion_page_parser.log"),
            encoding="utf-8",
        ),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("worker.parser.notion")

NOTION_API_KEY = os.environ.get("NOTION_API_KEY", "")
NOTION_VERSION = "2022-06-28"

# 取得対象の Notion プロパティ名（表記ゆれを考慮した候補リスト）
_FIELD_CANDIDATES: Dict[str, List[str]] = {
    "selection_flow"        : ["選考フロー", "選考", "採用フロー", "SelectionFlow"],
    "description"           : ["採用要件", "要件", "Description", "採用条件"],
    "strength_offer_point"  : ["強み", "訴求ポイント", "強み/訴求ポイント", "USP", "おすすめポイント", "StrengthOfferPoint"],
    "url_for_introduction"  : ["HP", "URL", "ホームページ", "hp", "HP URL", "企業URL"],
    "introduction_method"   : ["紹介方法", "IntroductionMethod", "紹介方式"],
    "gakuchika_requirement" : ["学チカレベル", "Gakuchika", "学チカ", "GakuchikaRequirement"],
    "feelings_requirement"  : ["気持ちよさ", "FeelingsRequirement", "気持ちよさレベル"],
    "intelligence_criteria" : ["賢さ", "IntelligenceCriteria", "賢さレベル"],
    "hot_requirement"       : ["熱さ", "HotRequirement", "熱さレベル"],
    "batting_company"       : ["バッティング企業", "BattingCompany", "競合企業"],
    "recruitment_channel"   : ["採用チャネル", "RecruitmentChannel", "チャネル"],
    "phase"                 : ["フェーズ", "Phase", "ステータス", "契約状況"],
    "overview"              : ["事業概要", "概要", "会社概要", "Overview"],
}

# ピックリスト許容値（これ以外は空文字に補正）
_VALID_INTRODUCTION_METHOD = {"URL", "ATS", "グーグルフォーム"}
_VALID_GRADE               = {"S", "A", "B", "C", "D"}
_VALID_PHASE               = {"契約完了", "契約進行", "中止", "クローズ"}


class NotionPageParser(BaseWorker):
    """
    PARSER: watcher_queue のIDリストを読み込み、Notion全文を取得して
    最小限フィールドのみを抽出する。生のAPIレスポンスは保存しない。
    """

    role        = WorkerRole.PARSER
    worker_name = "notion_page_parser"

    def __init__(self, dry_run: bool = False) -> None:
        super().__init__(dry_run=dry_run)
        self._state = StateManager(self.state_path(""))

    def execute(self) -> WorkerResult:
        """
        watcher_queue を読み込み、各ページを取得して parser_queue に書き込む。
        """
        queue = self._state.read_queue("watcher_queue")
        if not queue:
            logger.info("[Parser] watcher_queue が空です。スキップ。")
            return WorkerResult(processed=0)

        logger.info("[Parser] %d件のページを解析開始", len(queue))

        parsed_records: List[Dict[str, Any]] = []
        errors = 0

        with httpx.Client(timeout=30) as client:
            for item in queue:
                notion_page_id = item.get("notion_page_id", "")
                name           = item.get("name", "unknown")

                if not notion_page_id:
                    logger.warning("[Parser] notion_page_id なし: %s", item)
                    errors += 1
                    continue

                try:
                    page_props = self._fetch_page_properties(client, notion_page_id)
                    extracted  = self._extract_fields(page_props)
                    parsed_records.append({
                        "notion_page_id": notion_page_id,
                        "name"          : name,
                        "extracted"     : extracted,
                    })
                    logger.info("[Parser] 解析完了: %s", name)
                except Exception as exc:
                    logger.error("[Parser] エラー: %s → %s", name, exc)
                    errors += 1

        if not self.dry_run:
            self._state.write_queue("parser_queue", parsed_records)
            # 処理済みの watcher_queue をクリア
            self._state.clear_queue("watcher_queue")
            logger.info("[Parser] parser_queue.json に %d件 書き込み完了", len(parsed_records))
        else:
            logger.info("[Parser] [DRY-RUN] 書き込みスキップ。解析結果:")
            for r in parsed_records:
                logger.info("  %s: %s", r["name"], list(r["extracted"].keys()))

        return WorkerResult(processed=len(parsed_records), errors=errors)

    # ── 内部メソッド ──────────────────────────

    def _fetch_page_properties(
        self,
        client: httpx.Client,
        page_id: str,
    ) -> Dict[str, Any]:
        """Notion ページのプロパティを取得する"""
        resp = client.get(
            f"https://api.notion.com/v1/pages/{page_id}",
            headers={
                "Authorization" : f"Bearer {NOTION_API_KEY}",
                "Notion-Version": NOTION_VERSION,
            },
        )
        resp.raise_for_status()
        return resp.json().get("properties", {})

    def _extract_fields(self, props: Dict[str, Any]) -> Dict[str, Any]:
        """
        Notion プロパティから必要フィールドのみ抽出する。
        不要なメタデータ（Notion内部ID、型情報等）は完全に除去する。
        """
        extracted: Dict[str, Any] = {}

        for field_key, candidates in _FIELD_CANDIDATES.items():
            value = ""
            for candidate in candidates:
                raw = props.get(candidate)
                if raw:
                    value = self._prop_to_str(raw)
                    if value:
                        break

            # ピックリスト値のバリデーション
            value = self._validate_picklist(field_key, value)
            extracted[field_key] = value

        return extracted

    @staticmethod
    def _prop_to_str(prop: Dict[str, Any]) -> str:
        """Notion プロパティオブジェクトを文字列に変換する"""
        pt = prop.get("type", "")

        if pt == "title":
            return "".join(r.get("plain_text", "") for r in prop.get("title", []))
        if pt == "rich_text":
            return "".join(r.get("plain_text", "") for r in prop.get("rich_text", []))
        if pt == "url":
            return prop.get("url") or ""
        if pt == "select":
            sel = prop.get("select")
            return sel["name"] if sel else ""
        if pt == "multi_select":
            return ";".join(s["name"] for s in prop.get("multi_select", []))
        if pt == "number":
            v = prop.get("number")
            return str(v) if v is not None else ""
        if pt == "date":
            d = prop.get("date")
            return d["start"] if d else ""
        if pt == "checkbox":
            return "true" if prop.get("checkbox") else "false"

        return ""

    @staticmethod
    def _validate_picklist(field_key: str, value: str) -> str:
        """ピックリスト値が許容範囲内か検証し、不正値は空文字に補正する"""
        if field_key == "introduction_method" and value:
            return value if value in _VALID_INTRODUCTION_METHOD else ""
        if field_key in {"gakuchika_requirement", "feelings_requirement",
                         "intelligence_criteria", "hot_requirement"} and value:
            # セミコロン区切りの複数値に対応
            parts = [v.strip() for v in value.split(";")]
            valid_parts = [p for p in parts if p in _VALID_GRADE]
            return ";".join(valid_parts)
        if field_key == "phase" and value:
            return value if value in _VALID_PHASE else ""
        return value


# ──────────────────────────────────────────────
# CLI エントリポイント
# ──────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Notionページ最小フィールド抽出（PARSER）")
    parser.add_argument("--dry-run", action="store_true", help="書き込みスキップ（確認用）")
    args = parser.parse_args()

    worker = NotionPageParser(dry_run=args.dry_run)
    result = worker.execute()
    print(f"\n{'[DRY-RUN] ' if args.dry_run else ''}パース結果: {result}")


if __name__ == "__main__":
    main()
