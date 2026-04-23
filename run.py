#!/usr/bin/env python3
"""
Tokumori — シンプルエントリーポイント

使い方:
    python run.py --harness "SF面談を登録して企業紹介文も作って"
    python run.py --harness "タスク" --dry-run
    python run.py status
    python run.py dispatch "タスク"
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

AI_EMPIRE = Path(__file__).resolve().parent
sys.path.insert(0, str(AI_EMPIRE))

from dotenv import load_dotenv
load_dotenv(AI_EMPIRE / "config" / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("run")


def _make_dispatcher(dry_run: bool = False):
    """
    HarnessRunner 用ディスパッチャーを生成する。
    Planner が返す部門タグ（hr_support / sales / …）または
    ツールタグ（SF-Register / Slack / …）を empire_os._dispatch_to_dept に橋渡しする。
    """
    from core.infrastructure.empire_os import _dispatch_to_dept, DEPARTMENTS

    # ツールタグ → 部門キーのマッピング（ツール粒度タスクを部門に集約）
    _TAG_TO_DEPT = {
        "SF-Schema":   "hr_support",
        "SF-UI":       "hr_support",
        "SF-Data":     "hr_support",
        "SF-Patrol":   "hr_support",
        "SF-Register": "hr_support",
        "Slack":       "hr_support",
        "Email":       "hr_support",
        "Line":        "hr_support",
        "Doc":         "hr_support",
        "Slide":       "hr_support",
        "Schedule":    "hr_support",
        "TLDV":        "hr_support",
        "Notion":      "hr_support",
        "Log":         "hr_support",
    }

    def dispatcher(tag: str, task: dict) -> tuple[bool, str]:
        description = task.get("description", "")
        dept_key = _TAG_TO_DEPT.get(tag, tag if tag in DEPARTMENTS else "hr_support")

        if dry_run:
            logger.info("[dry-run] tag=%s dept=%s desc=%s", tag, dept_key, description[:50])
            return True, f"[dry-run] {tag} → {dept_key}: {description[:60]}"

        try:
            output = _dispatch_to_dept(dept_key=dept_key, task=description)
            return True, output
        except Exception as exc:
            logger.error("dispatch失敗: tag=%s dept=%s error=%s", tag, dept_key, exc)
            return False, str(exc)

    return dispatcher


def cmd_harness(task: str, dry_run: bool = False) -> None:
    """HarnessRunner 経由でタスクを実行する。"""
    from core.harness.runner import HarnessRunner

    logger.info("Harness起動: %s", task[:80])
    runner = HarnessRunner(
        dispatcher=_make_dispatcher(dry_run=dry_run),
        max_iterations=2,
    )
    result = runner.run(task)
    print("\n" + "=" * 60)
    print(result.final_output)
    print("=" * 60)


def cmd_status() -> None:
    """empire_os status に委譲する。"""
    from core.infrastructure import empire_os
    empire_os.cmd_status()


def cmd_dispatch(task: str) -> None:
    """empire_os dispatch に委譲する。"""
    from core.infrastructure import empire_os
    empire_os.cmd_dispatch(task)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Tokumori ルートエントリーポイント",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
例:
  python run.py --harness "SF面談を登録して企業紹介文を作って"
  python run.py --harness "Slackで進捗を報告して" --dry-run
  python run.py status
  python run.py dispatch "学生のES添削をお願い"
""",
    )

    subparsers = parser.add_subparsers(dest="command")

    # --harness はトップレベルフラグとしても使えるようにする
    parser.add_argument("--harness", metavar="TASK", help="HarnessRunner でタスクを実行")
    parser.add_argument("--dry-run", action="store_true", help="実際のエージェントを呼ばずに計画だけ表示")

    # サブコマンド: status
    subparsers.add_parser("status", help="全部門の状態確認")

    # サブコマンド: dispatch
    dp = subparsers.add_parser("dispatch", help="自然言語タスクを部門自動判定して実行")
    dp.add_argument("task", help="実行するタスクの説明")

    args = parser.parse_args()

    if args.harness:
        cmd_harness(args.harness, dry_run=args.dry_run)
    elif args.command == "status":
        cmd_status()
    elif args.command == "dispatch":
        cmd_dispatch(args.task)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
