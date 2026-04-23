#!/usr/bin/env python3
"""
Patrol Agent — 業務 launchd ジョブ監視エージェント
canonical_id: quality_patrol
layer: Quality
level: Level 1（自動監視）

責務:
  登録された launchd ジョブのログを走査し、エラー・停止・異常を検知する。
  異常があれば Repair Agent と連携して自動修復を試みる。

監視対象（外部JSONで定義）:
  - 業務ターゲット: agents/quality/patrol/targets.business.json（常時ロード）
  - 拡張ターゲット: 環境変数 PATROL_PRIVATE_TARGETS_JSON で指定された
                    JSONファイル（存在すれば追加ロード）

使い方:
  python3 agents/quality/patrol/agent.py          # 全ジョブをパトロール
  python3 agents/quality/patrol/agent.py --quick  # ログのみ（Claude解析なし）
"""
from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv
load_dotenv(_ROOT / "config" / ".env")

import anthropic

logger = logging.getLogger(__name__)

PATROL_LOG = _ROOT / "logs" / "patrol"

# ─── 監視ジョブ定義（外部JSONからロード） ─────────────────────────────────────
#
# 業務ターゲット: patrol/targets.business.json（常にロード）
# private ターゲット: 環境変数 PATROL_PRIVATE_TARGETS_JSON で指定されたパスに
#   JSONファイルがあれば追加でロードする（大将環境のみ）。
#
# JSON内の {root} プレースホルダは ai-empire ルート絶対パスに置換される。

_PATROL_DIR = Path(__file__).resolve().parent
_BUSINESS_TARGETS_PATH = _PATROL_DIR / "targets.business.json"
_PRIVATE_TARGETS_ENV = "PATROL_PRIVATE_TARGETS_JSON"


def _substitute_root(job: dict) -> dict:
    """JSON内の {root} プレースホルダを ai-empire ルートに置換。"""
    for key in ("stderr", "stdout"):
        val = job.get(key)
        if isinstance(val, str) and "{root}" in val:
            job[key] = val.replace("{root}", str(_ROOT))
    return job


def _load_jobs_from(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    except Exception as e:
        logger.warning(f"監視ターゲットJSON読込失敗: {path} — {e}")
        return []
    return [_substitute_root(j) for j in raw if isinstance(j, dict)]


def _load_watch_jobs() -> list[dict]:
    jobs: list[dict] = _load_jobs_from(_BUSINESS_TARGETS_PATH)

    private_path_str = os.environ.get(_PRIVATE_TARGETS_ENV)
    if private_path_str:
        jobs.extend(_load_jobs_from(Path(private_path_str)))

    return jobs


WATCH_JOBS: list[dict] = _load_watch_jobs()

# エラーと判断するキーワード
ERROR_PATTERNS = [
    r"ERROR",
    r"CRITICAL",
    r"Traceback \(most recent call last\)",
    r"Exception:",
    r"Error:",
    r"failed",
    r"Failed",
    r"exit code [^0]",
    r"HTTPSConnectionPool.*Max retries exceeded",
    r"Connection refused",
    r"ModuleNotFoundError",
    r"ImportError",
    r"FileNotFoundError",
    r"PermissionError",
    r"JSONDecodeError",
    r"APIError",
    r"RateLimitError",
    r"TimeoutError",
]

WARNING_PATTERNS = [
    r"WARNING",
    r"WARN",
    r"rate limit",
    r"retry",
    r"429",
    r"timeout",
]

_ERROR_RE = re.compile("|".join(ERROR_PATTERNS), re.IGNORECASE)
_WARN_RE = re.compile("|".join(WARNING_PATTERNS), re.IGNORECASE)


# ─── データ構造 ───────────────────────────────────────────────────────────────

@dataclass
class JobHealth:
    label: str
    name: str
    system: str
    critical: bool
    status: str              # "ok" | "warning" | "error" | "stale" | "unknown"
    last_activity: str = ""  # 最後の活動時刻
    error_lines: list[str] = field(default_factory=list)
    warning_lines: list[str] = field(default_factory=list)
    log_age_hours: float = 0.0
    diagnosis: str = ""      # Claude による診断
    repair_needed: bool = False


@dataclass
class PatrolReport:
    patrol_id: str
    started_at: str
    finished_at: str = ""
    jobs: list[JobHealth] = field(default_factory=list)

    @property
    def error_jobs(self) -> list[JobHealth]:
        return [j for j in self.jobs if j.status == "error"]

    @property
    def warning_jobs(self) -> list[JobHealth]:
        return [j for j in self.jobs if j.status == "warning"]

    @property
    def stale_jobs(self) -> list[JobHealth]:
        return [j for j in self.jobs if j.status == "stale"]

    @property
    def ok_jobs(self) -> list[JobHealth]:
        return [j for j in self.jobs if j.status == "ok"]

    @property
    def overall_status(self) -> str:
        if any(j.status == "error" and j.critical for j in self.jobs):
            return "CRITICAL"
        if any(j.status == "error" for j in self.jobs):
            return "ERROR"
        if any(j.status in ("warning", "stale") for j in self.jobs):
            return "WARNING"
        return "OK"


# ─── ログ解析 ─────────────────────────────────────────────────────────────────

def _read_recent_log(log_path: str | None, hours: int = 24) -> tuple[list[str], list[str], float]:
    """
    ログファイルを読み込み、直近 hours 時間のエラー行・警告行を返す。

    Returns:
        (error_lines, warning_lines, log_age_hours)
        log_age_hours: ファイルの最終更新からの経過時間（存在しない場合は 9999）
    """
    if not log_path:
        return [], [], 9999.0

    path = Path(log_path)
    if not path.exists():
        return [], [], 9999.0

    # ファイル更新時刻から経過時間を計算
    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    age_hours = (datetime.now() - mtime).total_seconds() / 3600

    # 直近 N 時間分のみ読む（末尾500行）
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return [], [], age_hours

    recent_lines = lines[-500:]  # 末尾500行
    cutoff = datetime.now() - timedelta(hours=hours)

    error_lines = []
    warning_lines = []

    for line in recent_lines:
        if _ERROR_RE.search(line):
            error_lines.append(line.strip()[:200])
        elif _WARN_RE.search(line):
            warning_lines.append(line.strip()[:200])

    return error_lines[-20:], warning_lines[-10:], age_hours


def _check_launchctl_status(label: str) -> str:
    """
    launchctl でジョブの実行状態を確認する。
    Returns: "running" | "stopped" | "error:<code>" | "unknown"
    """
    try:
        result = subprocess.run(
            ["launchctl", "list", label],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return "stopped"
        output = result.stdout
        # PID があれば実行中
        pid_match = re.search(r'"PID"\s*=\s*(\d+)', output)
        exit_match = re.search(r'"LastExitStatus"\s*=\s*(\d+)', output)
        if pid_match:
            return "running"
        if exit_match:
            code = exit_match.group(1)
            return "ok" if code == "0" else f"error:{code}"
        return "unknown"
    except Exception:
        return "unknown"


# ─── ジョブヘルスチェック ─────────────────────────────────────────────────────

def check_job(job: dict) -> JobHealth:
    """1ジョブのヘルスを確認する。"""
    health = JobHealth(
        label=job["label"],
        name=job["name"],
        system=job["system"],
        critical=job.get("critical", False),
        status="unknown",
    )

    # ログ解析
    error_lines, warning_lines, age_hours = _read_recent_log(
        job.get("stderr"), hours=24
    )
    health.error_lines = error_lines
    health.warning_lines = warning_lines
    health.log_age_hours = age_hours

    # 最終活動時刻
    if age_hours < 9999:
        health.last_activity = (
            datetime.now() - timedelta(hours=age_hours)
        ).strftime("%Y-%m-%d %H:%M")
    else:
        health.last_activity = "不明（ログなし）"

    # ステータス判定
    expect_hours = job.get("expect_interval_hours", 25)
    is_stale = age_hours > expect_hours and age_hours < 9999

    if error_lines:
        health.status = "error"
        health.repair_needed = True
    elif is_stale:
        health.status = "stale"
        health.repair_needed = job.get("critical", False)
    elif warning_lines:
        health.status = "warning"
    elif age_hours >= 9999:
        health.status = "unknown"
    else:
        health.status = "ok"

    return health


# ─── Claude 診断 ──────────────────────────────────────────────────────────────

def diagnose_errors(jobs: list[JobHealth], quick: bool = False) -> None:
    """
    エラー・異常ジョブを Claude で診断し、diagnosis フィールドを埋める。
    quick=True の場合はスキップ。
    """
    abnormal = [j for j in jobs if j.status in ("error", "stale", "unknown")]
    if not abnormal or quick:
        for j in abnormal:
            j.diagnosis = "（診断スキップ）"
        return

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    for job in abnormal:
        errors_text = "\n".join(job.error_lines[-5:]) if job.error_lines else "ログなし"
        prompt = (
            f"以下のジョブで問題が発生しています。原因と推奨対処を50文字以内で答えてください。\n\n"
            f"ジョブ名: {job.name}\n"
            f"ステータス: {job.status}\n"
            f"ログ経過時間: {job.log_age_hours:.1f}時間\n"
            f"エラーログ（末尾5行）:\n{errors_text}"
        )
        try:
            res = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=100,
                messages=[{"role": "user", "content": prompt}],
            )
            job.diagnosis = res.content[0].text.strip()
        except Exception as e:
            job.diagnosis = f"診断失敗: {e}"


# ─── パトロール実行 ───────────────────────────────────────────────────────────

def run(quick: bool = False, log_dashboard: bool = True) -> PatrolReport:
    """
    全ジョブをパトロールしてレポートを返す。

    Args:
        quick: True の場合 Claude 診断をスキップ
        log_dashboard: True の場合 dashboard_logger に記録
    """
    patrol_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    report = PatrolReport(patrol_id=patrol_id, started_at=datetime.now().isoformat())

    logger.info(f"=== パトロール開始 [{patrol_id}] ===")

    for job in WATCH_JOBS:
        health = check_job(job)
        report.jobs.append(health)
        status_icon = {"ok": "✓", "warning": "⚠", "error": "✗", "stale": "?", "unknown": "?"}.get(
            health.status, "?"
        )
        logger.info(f"  {status_icon} {health.name} [{health.status}] age={health.log_age_hours:.1f}h")

    # エラー・異常ジョブを Claude で診断
    diagnose_errors(report.jobs, quick=quick)

    report.finished_at = datetime.now().isoformat()

    # 保存
    PATROL_LOG.mkdir(parents=True, exist_ok=True)
    out = PATROL_LOG / f"patrol_{patrol_id}.json"
    _save_report(report, out)

    # dashboard_logger
    if log_dashboard:
        _log_to_dashboard(report)

    logger.info(
        f"=== パトロール完了 [{report.overall_status}] "
        f"ok={len(report.ok_jobs)} warn={len(report.warning_jobs)} "
        f"err={len(report.error_jobs)} stale={len(report.stale_jobs)} ==="
    )
    return report


def _save_report(report: PatrolReport, path: Path) -> None:
    data = {
        "patrol_id": report.patrol_id,
        "started_at": report.started_at,
        "finished_at": report.finished_at,
        "overall_status": report.overall_status,
        "summary": {
            "ok": len(report.ok_jobs),
            "warning": len(report.warning_jobs),
            "error": len(report.error_jobs),
            "stale": len(report.stale_jobs),
        },
        "jobs": [
            {
                "label": j.label,
                "name": j.name,
                "system": j.system,
                "critical": j.critical,
                "status": j.status,
                "last_activity": j.last_activity,
                "log_age_hours": round(j.log_age_hours, 1),
                "error_count": len(j.error_lines),
                "warning_count": len(j.warning_lines),
                "error_lines": j.error_lines[-5:],
                "diagnosis": j.diagnosis,
                "repair_needed": j.repair_needed,
            }
            for j in report.jobs
        ],
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _log_to_dashboard(report: PatrolReport) -> None:
    try:
        from utils.dashboard_logger import log_update
        status_icon = {"OK": "✅", "WARNING": "⚠️", "ERROR": "❌", "CRITICAL": "🚨"}.get(
            report.overall_status, "❓"
        )
        error_names = ", ".join(j.name for j in report.error_jobs[:3])
        log_update(
            icon=f"{status_icon} パトロール",
            summary=(
                f"全体: {report.overall_status} / "
                f"正常{len(report.ok_jobs)} 警告{len(report.warning_jobs)} "
                f"エラー{len(report.error_jobs)}"
            ),
            targets="全ジョブ監視",
            details=(
                f"①合計{len(report.jobs)}ジョブ確認 "
                f"②エラー: {error_names or 'なし'} "
                f"③patrol_id: {report.patrol_id}"
            ),
        )
    except Exception as e:
        logger.debug(f"dashboard_logger スキップ: {e}")


def load_latest_report() -> dict | None:
    """最新のパトロールレポートを返す（dashboard 用）。"""
    if not PATROL_LOG.exists():
        return None
    files = sorted(PATROL_LOG.glob("patrol_*.json"), reverse=True)
    if not files:
        return None
    try:
        with open(files[0], encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    parser = argparse.ArgumentParser(description="Tokumori パトロールエージェント")
    parser.add_argument("--quick", action="store_true", help="Claude診断をスキップして高速実行")
    parser.add_argument("--no-log", action="store_true", help="dashboard_loggerへの記録をスキップ")
    args = parser.parse_args()

    report = run(quick=args.quick, log_dashboard=not args.no_log)

    print(f"\n{'='*55}")
    print(f"  パトロール結果: {report.overall_status}")
    print(f"{'='*55}")
    print(f"  ✓ 正常: {len(report.ok_jobs)}件")
    print(f"  ⚠ 警告: {len(report.warning_jobs)}件")
    print(f"  ✗ エラー: {len(report.error_jobs)}件")
    print(f"  ? 停止疑い: {len(report.stale_jobs)}件")

    if report.error_jobs or report.stale_jobs:
        print(f"\n  要対応:")
        for j in report.error_jobs + report.stale_jobs:
            critical_mark = " [重要]" if j.critical else ""
            print(f"  {'✗' if j.status=='error' else '?'} {j.name}{critical_mark}")
            if j.diagnosis:
                print(f"    → {j.diagnosis}")
    print(f"{'='*55}\n")
