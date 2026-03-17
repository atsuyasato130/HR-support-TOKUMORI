#!/usr/bin/env python3
"""
notion_company_watcher.py — Notion企業DB 監視 → SF自動生成

Notionに新規企業ページが追加されると自動的に:
  1. SF クライアントAccount を作成（または既存を更新）
  2. Supabase companies を upsert
  3. Slack に完了通知を投稿

起動方法:
  # 常駐監視（デフォルト: 30分ごとにポーリング）
  python3 integrations/notion_company_watcher.py

  # ポーリング間隔を変更（例: 60分）
  python3 integrations/notion_company_watcher.py --interval 60

  # 1回だけ実行してすぐ終了
  python3 integrations/notion_company_watcher.py --once

  # dry-run
  python3 integrations/notion_company_watcher.py --once --dry-run

状態管理:
  logs/notion_watcher_state.json に「最終確認日時」を保存。
  このファイルを消すと全件再チェックになる。

Slack通知先:
  SLACK_BOT_TOKEN + SLACK_ALERT_CHANNEL_ID 環境変数を使用。
  未設定の場合は通知スキップ。
"""

from __future__ import annotations

import os
import sys
import json
import time
import logging
import argparse
import datetime
from typing import Any, Dict, List, Optional

# ── プロジェクトルート
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(_ROOT, "config", ".env"))

# ── sync モジュールを再利用
from tools.notion_to_sf_sync import (  # type: ignore
    NotionCompanyDB,
    SFCompanyClient,
    SupabaseCompanyClient,
    WebEnricher,
    match_company_name,
    NOTION_COMPANY_DB_ID,
    NOTION_API_KEY,
)

# ── ログ
_LOG_DIR    = os.path.join(_ROOT, "logs")
_STATE_FILE = os.path.join(_LOG_DIR, "notion_watcher_state.json")
os.makedirs(_LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(_LOG_DIR, "notion_watcher.log"), encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("notion_watcher")

# ── 環境変数
SLACK_TOKEN   = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_CHANNEL = os.environ.get("SLACK_ALERT_CHANNEL_ID", "C0A2YSANGKS")


# ──────────────────────────────────────────────
# 状態管理（最終確認日時を永続化）
# ──────────────────────────────────────────────

def load_state() -> Dict[str, Any]:
    """logs/notion_watcher_state.json から状態を読み込む"""
    if os.path.exists(_STATE_FILE):
        with open(_STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(state: Dict[str, Any]) -> None:
    """状態を保存する"""
    with open(_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# ──────────────────────────────────────────────
# Slack 通知
# ──────────────────────────────────────────────

def notify_slack(message: str) -> None:
    """Slack に通知を投稿する（トークン未設定時はスキップ）"""
    if not SLACK_TOKEN:
        return
    try:
        from slack_sdk import WebClient  # type: ignore
        client = WebClient(token=SLACK_TOKEN)
        client.chat_postMessage(channel=SLACK_CHANNEL, text=message)
        logger.debug("[Slack] 投稿完了: %s", SLACK_CHANNEL)
    except ImportError:
        logger.warning("[Slack] slack_sdk 未インストール。通知をスキップします")
    except Exception as exc:
        logger.error("[Slack] 投稿エラー: %s", exc)


# ──────────────────────────────────────────────
# メイン監視ループ
# ──────────────────────────────────────────────

class NotionCompanyWatcher:
    """
    Notion企業DBを定期ポーリングし、新規企業を SF & Supabase に自動登録する。
    """

    def __init__(self, dry_run: bool = False, enrich: bool = False) -> None:
        self.dry_run = dry_run
        self.notion  = NotionCompanyDB(NOTION_API_KEY, NOTION_COMPANY_DB_ID)
        self.sf      = SFCompanyClient()
        try:
            self.supabase = SupabaseCompanyClient()
            self._supabase_ok = True
        except EnvironmentError:
            self.supabase = None  # type: ignore
            self._supabase_ok = False
            logger.warning("[Supabase] 接続情報未設定 → Supabase同期をスキップします")

        # Web エンリッチメント
        self._enricher: Optional[WebEnricher] = None
        if enrich:
            try:
                self._enricher = WebEnricher()
                logger.info("[Enrich] Webエンリッチメント: 有効")
            except (ImportError, EnvironmentError) as exc:
                logger.warning("[Enrich] 無効化: %s", exc)

    def check_once(self) -> List[Dict[str, Any]]:
        """
        1回のポーリングを実行する。

        Returns:
            処理した新規企業のリスト（各要素: {name, action, sf_id}）
        """
        state    = load_state()
        last_run = state.get("last_run")
        processed: List[Dict[str, Any]] = []

        if last_run:
            since = datetime.datetime.fromisoformat(last_run)
            logger.info("[Watcher] 前回実行: %s 以降の新規ページを確認", since.strftime("%Y-%m-%d %H:%M"))
        else:
            # 初回: 直近7日分を対象
            since = datetime.datetime.utcnow() - datetime.timedelta(days=7)
            logger.info("[Watcher] 初回実行: 直近7日分を確認")

        # Notion から新規ページ取得
        new_companies = self.notion.fetch_new_since(since)
        logger.info("[Watcher] 新規ページ: %d件", len(new_companies))

        if not new_companies:
            logger.info("[Watcher] 新規企業なし → スキップ")
            state["last_run"] = datetime.datetime.utcnow().isoformat()
            save_state(state)
            return []

        # SF既存リストを取得（マッチング用）
        sf_accounts = self.sf.fetch_all()

        for company in new_companies:
            name = company["name"]
            # Web エンリッチメント（有効時）
            if self._enricher:
                company = self._enricher.enrich(
                    company_name=name,
                    url=company.get("hp_url"),
                    existing=company,
                )
            result = self._process_company(company, sf_accounts)
            processed.append(result)

            # 新規作成した SF Account を次の企業のマッチングに反映
            if result["action"] == "created" and result["sf_id"]:
                sf_accounts.append({"Id": result["sf_id"], "Name": name})

        # Slack 通知
        if processed:
            self._send_summary_slack(processed)

        # 状態保存
        state["last_run"] = datetime.datetime.utcnow().isoformat()
        save_state(state)
        return processed

    def _process_company(
        self,
        company: Dict[str, Any],
        sf_accounts: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        1社の Notion企業データを処理して SF & Supabase に反映する。

        Returns:
            {name, action: "created"|"updated"|"error", sf_id, detail}
        """
        name       = company["name"]
        sf_fields  = self.sf.build_fields(company)
        matched_sf = match_company_name(name, sf_accounts, threshold=0.85)

        if matched_sf:
            account_id = matched_sf["Id"]
            action = "updated"
            logger.info("[Watcher] 既存SF更新: %s → %s", name, account_id)
            if not self.dry_run:
                ok = self.sf.update(account_id, sf_fields)
                if not ok:
                    return {"name": name, "action": "error", "sf_id": account_id, "detail": "SF更新失敗"}
        else:
            action = "created"
            logger.info("[Watcher] SF新規作成: %s", name)
            if not self.dry_run:
                account_id = self.sf.create(sf_fields)
                if not account_id:
                    return {"name": name, "action": "error", "sf_id": None, "detail": "SF作成失敗"}
            else:
                account_id = f"DRY_{name}"

        # Supabase upsert
        if self._supabase_ok and not self.dry_run:
            import datetime as dt
            sb_record = {
                "sf_account_id"  : account_id,
                "notion_id"      : company.get("notion_page_id"),
                "name"           : name,
                "industry"       : company.get("industry") or None,
                "overview"       : company.get("overview") or None,
                "recommend_points": [company["usp"]] if company.get("usp") else None,
                "website_url"    : company.get("hp_url") or None,
                "session_dates"  : company.get("session_dates") or None,
                "is_published"   : True,
                "updated_at"     : dt.datetime.utcnow().isoformat() + "Z",
            }
            self.supabase.upsert(sb_record)  # type: ignore

        logger.info("[Watcher] 完了: %s → action=%s, sf_id=%s", name, action, account_id)
        return {"name": name, "action": action, "sf_id": account_id, "detail": ""}

    def _send_summary_slack(self, processed: List[Dict[str, Any]]) -> None:
        """処理結果のサマリーを Slack に投稿する"""
        today = datetime.date.today().strftime("%Y-%m-%d")
        created = [p for p in processed if p["action"] == "created"]
        updated = [p for p in processed if p["action"] == "updated"]
        errors  = [p for p in processed if p["action"] == "error"]

        lines = [f"*【企業DB同期】{today}*"]

        if created:
            lines.append(f"\n*新規登録 {len(created)}社:*")
            for p in created:
                lines.append(f"  • {p['name']}  (SF: `{p['sf_id']}`)")

        if updated:
            lines.append(f"\n*更新 {len(updated)}社:*")
            for p in updated[:5]:  # 多すぎる場合は先頭5件のみ
                lines.append(f"  • {p['name']}")
            if len(updated) > 5:
                lines.append(f"  ... 他{len(updated)-5}社")

        if errors:
            lines.append(f"\n*エラー {len(errors)}社:*")
            for p in errors:
                lines.append(f"  ✗ {p['name']}: {p.get('detail', '')}")

        notify_slack("\n".join(lines))

    def run_loop(self, interval_minutes: int = 30) -> None:
        """
        常駐監視ループ。Ctrl+C で停止。

        Args:
            interval_minutes: ポーリング間隔（分）
        """
        logger.info("[Watcher] 常駐監視開始: %d分間隔", interval_minutes)
        notify_slack(
            f"*[Notion Watcher] 起動しました。*\n"
            f"監視DB: `{NOTION_COMPANY_DB_ID}`\n"
            f"ポーリング間隔: {interval_minutes}分"
        )

        while True:
            try:
                self.check_once()
            except KeyboardInterrupt:
                logger.info("[Watcher] 停止シグナルを受信。終了します")
                notify_slack("*[Notion Watcher] 停止しました。*")
                break
            except Exception as exc:
                logger.error("[Watcher] 予期しないエラー: %s", exc, exc_info=True)
                notify_slack(f"*[Notion Watcher] エラー:* `{exc}`")

            logger.info("[Watcher] 次回実行まで %d分 待機...", interval_minutes)
            time.sleep(interval_minutes * 60)


# ──────────────────────────────────────────────
# CLI エントリポイント
# ──────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Notion企業DB監視 → SF自動生成")
    parser.add_argument("--interval", type=int, default=30, help="ポーリング間隔（分、デフォルト:30）")
    parser.add_argument("--once",     action="store_true", help="1回だけ実行してすぐ終了")
    parser.add_argument("--dry-run",  action="store_true", help="書き込みをスキップして確認のみ")
    parser.add_argument("--reset",    action="store_true", help="状態ファイルをリセットして全件再チェック")
    parser.add_argument(
        "--enrich",
        action="store_true",
        help="WebエンリッチメントON: 企業HPをHTTP取得 → Claude APIで空フィールドを自動補完",
    )
    args = parser.parse_args()

    if args.reset and os.path.exists(_STATE_FILE):
        os.remove(_STATE_FILE)
        logger.info("[Watcher] 状態ファイルをリセットしました")

    watcher = NotionCompanyWatcher(dry_run=args.dry_run, enrich=args.enrich)

    if args.once:
        processed = watcher.check_once()
        print(f"\n{'[DRY-RUN] ' if args.dry_run else ''}処理結果: {len(processed)}件")
        for p in processed:
            mark = "✓" if p["action"] != "error" else "✗"
            print(f"  {mark} {p['name']} [{p['action']}] sf_id={p['sf_id']}")
    else:
        watcher.run_loop(interval_minutes=args.interval)


if __name__ == "__main__":
    main()
