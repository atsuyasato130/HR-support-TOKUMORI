#!/usr/bin/env python3
"""
Repair Agent — Tokumori 自動修復エージェント
canonical_id: quality_repair
layer: Quality
level: Level 1（自動修復）

責務:
  Patrol Agent からエラー情報を受け取り、
  原因を分析して実行可能な修復アクションを選択・実行する。

修復アクション一覧:
  - restart_job       : launchd ジョブを unload → load で再起動
  - reload_env        : .env ファイルを再読み込み（env-bootstrap 再実行）
  - clear_log         : 肥大化したログをローテート
  - notify_manual     : 自動修復不可 → 手動対応が必要な旨をログに記録

使い方:
  from agents.quality.repair.agent import RepairAgent
  repair = RepairAgent()
  results = repair.run(patrol_report)
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv
load_dotenv(_ROOT / "config" / ".env")

import anthropic

logger = logging.getLogger(__name__)

REPAIR_LOG = _ROOT / "logs" / "repair"
LAUNCH_AGENTS = Path("/Users/atsuyasato/Library/LaunchAgents")


# ─── データ構造 ───────────────────────────────────────────────────────────────

@dataclass
class RepairAction:
    job_label: str
    job_name: str
    action: str          # "restart_job" | "reload_env" | "clear_log" | "notify_manual"
    reason: str
    success: bool = False
    message: str = ""


@dataclass
class RepairReport:
    repair_id: str
    started_at: str
    finished_at: str = ""
    actions: list[RepairAction] = field(default_factory=list)

    @property
    def repaired_count(self) -> int:
        return sum(1 for a in self.actions if a.success)

    @property
    def manual_needed(self) -> list[RepairAction]:
        return [a for a in self.actions if a.action == "notify_manual"]


# ─── 修復アクション実装 ───────────────────────────────────────────────────────

def _restart_job(label: str) -> tuple[bool, str]:
    """
    launchd ジョブを再起動する（unload → load）。
    plist が LaunchAgents に存在する場合のみ実行。
    """
    plist = LAUNCH_AGENTS / f"{label}.plist"
    if not plist.exists():
        return False, f"plistが見つかりません: {plist.name}"

    try:
        subprocess.run(["launchctl", "unload", str(plist)], check=False, timeout=10)
        result = subprocess.run(
            ["launchctl", "load", str(plist)],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            return True, f"{label} を再起動しました"
        else:
            return False, f"load 失敗: {result.stderr.strip()}"
    except Exception as e:
        return False, f"再起動エラー: {e}"


def _reload_env(label: str) -> tuple[bool, str]:
    """env-bootstrap ジョブを再実行して環境変数を再読み込みする。"""
    plist = LAUNCH_AGENTS / "com.atsuyasato.env-bootstrap.plist"
    if not plist.exists():
        return False, "env-bootstrap plist が見つかりません"
    try:
        subprocess.run(["launchctl", "start", "com.atsuyasato.env-bootstrap"],
                       check=False, timeout=30)
        return True, "env-bootstrap を再実行しました"
    except Exception as e:
        return False, f"env-bootstrap 失敗: {e}"


def _clear_log(stderr_path: str | None) -> tuple[bool, str]:
    """エラーログを末尾100行にトリミングしてサイズを削減する。"""
    if not stderr_path:
        return False, "ログパスが未定義"
    path = Path(stderr_path)
    if not path.exists():
        return False, f"ログファイルが存在しない: {path.name}"
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        if len(lines) > 500:
            trimmed = "\n".join(lines[-100:]) + "\n"
            path.write_text(trimmed, encoding="utf-8")
            return True, f"{path.name} を末尾100行にトリミングしました（{len(lines)}行→100行）"
        return True, f"{path.name} はサイズ正常（{len(lines)}行）"
    except Exception as e:
        return False, f"ログクリア失敗: {e}"


# ─── Claude による修復戦略判定 ────────────────────────────────────────────────

def _decide_repair_action(job_data: dict) -> str:
    """
    エラー内容から最適な修復アクションを Claude で判定する。

    Returns:
        action: "restart_job" | "reload_env" | "clear_log" | "notify_manual"
    """
    error_text = "\n".join(job_data.get("error_lines", [])[-5:])
    diagnosis = job_data.get("diagnosis", "")
    status = job_data.get("status", "error")

    # ルールベースで判定できるケースは API を使わない
    if status == "stale":
        return "restart_job"

    for line in job_data.get("error_lines", []):
        if "ModuleNotFoundError" in line or "ImportError" in line:
            return "notify_manual"  # 依存ライブラリ欠損は手動対応
        if "PermissionError" in line:
            return "notify_manual"
        if "nodename nor servname" in line or "Connection refused" in line:
            return "restart_job"   # ネットワークエラーは再起動で回復する場合が多い
        if "JSONDecodeError" in line:
            return "clear_log"     # ログ破損 → クリア後再起動
        if "RateLimitError" in line or "429" in line:
            return "notify_manual"  # API制限は手動確認

    # Claude に判断を委ねる
    try:
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        res = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=30,
            system=(
                "Tokumoriのジョブエラーに対して最適な修復アクションを1つ選んでください。\n"
                "選択肢: restart_job / reload_env / clear_log / notify_manual\n"
                "出力: action=<選択肢> のみ"
            ),
            messages=[{"role": "user", "content": (
                f"エラー概要: {diagnosis}\n"
                f"ステータス: {status}\n"
                f"エラーログ:\n{error_text}"
            )}],
        )
        text = res.content[0].text.strip()
        for action in ("restart_job", "reload_env", "clear_log", "notify_manual"):
            if action in text:
                return action
    except Exception:
        pass

    return "restart_job"  # デフォルト


# ─── 修復実行 ─────────────────────────────────────────────────────────────────

class RepairAgent:
    """Patrol Agentと連携してエラージョブを自動修復する。"""

    agent_key  = "quality_repair"
    agent_name = "Repair Agent"
    agent_desc = "エラージョブの原因分析と自動修復"

    def run(self, patrol_data: dict | None = None) -> RepairReport:
        """
        パトロールレポートを受け取り、要修復ジョブを自動修復する。

        Args:
            patrol_data: PatrolAgent が返した dict（Noneの場合は最新レポートを使用）
        """
        repair_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        report = RepairReport(repair_id=repair_id, started_at=datetime.now().isoformat())

        # パトロールレポートを取得
        if patrol_data is None:
            from agents.quality.patrol.agent import load_latest_report
            patrol_data = load_latest_report()

        if patrol_data is None:
            logger.warning("パトロールレポートが見つかりません")
            return report

        # 修復が必要なジョブのみ対象
        jobs_to_repair = [
            j for j in patrol_data.get("jobs", [])
            if j.get("repair_needed") and j.get("status") in ("error", "stale", "unknown")
        ]

        if not jobs_to_repair:
            logger.info("修復が必要なジョブはありません")
            return report

        logger.info(f"=== 修復開始: {len(jobs_to_repair)}ジョブ ===")

        # WATCH_JOBS から stderr パスを逆引き
        from agents.quality.patrol.agent import WATCH_JOBS
        stderr_map = {j["label"]: j.get("stderr") for j in WATCH_JOBS}

        for job_data in jobs_to_repair:
            label = job_data["label"]
            name = job_data["name"]
            logger.info(f"  修復対象: {name} [{label}]")

            # アクション決定
            action = _decide_repair_action(job_data)
            reason = job_data.get("diagnosis", job_data.get("status", "エラー"))
            repair_action = RepairAction(
                job_label=label, job_name=name, action=action, reason=reason
            )

            # アクション実行
            if action == "restart_job":
                success, msg = _restart_job(label)
            elif action == "reload_env":
                success, msg = _reload_env(label)
                if success:
                    import time
                    time.sleep(5)
                    s2, m2 = _restart_job(label)
                    msg += f" → {m2}"
                    success = success and s2
            elif action == "clear_log":
                success, msg = _clear_log(stderr_map.get(label))
                if success:
                    s2, m2 = _restart_job(label)
                    msg += f" → {m2}"
            else:  # notify_manual
                success = True  # 手動対応通知は「実行成功」扱い
                msg = f"手動対応が必要: {reason}"

            repair_action.success = success
            repair_action.message = msg
            report.actions.append(repair_action)

            icon = "✓" if success else "✗"
            logger.info(f"    {icon} [{action}] {msg}")

        report.finished_at = datetime.now().isoformat()
        self._save_report(report)
        self._log_to_dashboard(report)

        return report

    def _save_report(self, report: RepairReport) -> None:
        REPAIR_LOG.mkdir(parents=True, exist_ok=True)
        out = REPAIR_LOG / f"repair_{report.repair_id}.json"
        data = {
            "repair_id": report.repair_id,
            "started_at": report.started_at,
            "finished_at": report.finished_at,
            "repaired_count": report.repaired_count,
            "manual_needed_count": len(report.manual_needed),
            "actions": [
                {
                    "job_label": a.job_label,
                    "job_name": a.job_name,
                    "action": a.action,
                    "reason": a.reason,
                    "success": a.success,
                    "message": a.message,
                }
                for a in report.actions
            ],
        }
        out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _log_to_dashboard(self, report: RepairReport) -> None:
        try:
            from utils.dashboard_logger import log_update
            manual_names = ", ".join(a.job_name for a in report.manual_needed[:2])
            log_update(
                icon="🔧 修復",
                summary=f"自動修復: {report.repaired_count}/{len(report.actions)}件成功",
                targets="エラージョブ",
                details=(
                    f"①修復完了: {report.repaired_count}件 "
                    f"②手動対応: {len(report.manual_needed)}件"
                    + (f" ({manual_names})" if manual_names else "")
                    + f" ③repair_id: {report.repair_id}"
                ),
            )
        except Exception as e:
            logger.debug(f"dashboard_logger スキップ: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    agent = RepairAgent()
    report = agent.run()

    print(f"\n{'='*50}")
    print(f"  修復完了: {report.repaired_count}/{len(report.actions)}件")
    for a in report.actions:
        icon = "✓" if a.success else "✗"
        print(f"  {icon} [{a.action}] {a.job_name}: {a.message[:80]}")
    if report.manual_needed:
        print(f"\n  ⚠️ 手動対応が必要なジョブ:")
        for a in report.manual_needed:
            print(f"    - {a.job_name}: {a.reason}")
    print(f"{'='*50}\n")
