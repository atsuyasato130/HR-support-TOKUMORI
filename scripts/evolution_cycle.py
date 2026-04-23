"""
Evolution Cycle — ai-empire 自律進化ループ

品質管理層の 4エージェントを週次で順番に実行し、
ai-empire 全体を常に高品質・最新状態に保つ自律サイクル。

ステップ:
  1. Security Scan   — セキュリティリスクを先に検出
  2. Code Review     — 全エージェントをスコアリング
  3. Code Improve    — 低スコアを自動改善
  4. Catalog Update  — AGENT_MANIFEST.json を同期

実行方法:
  python3 scripts/evolution_cycle.py          # 全ステップ実行
  python3 scripts/evolution_cycle.py --dry-run # ドライラン（ファイル変更なし）
  python3 scripts/evolution_cycle.py --step review  # 特定ステップのみ

launchd (週次自動実行):
  com.<USER>.ai-empire-evolution-weekly
  Schedule: 毎週日曜 03:00
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# ─── パス設定 ─────────────────────────────────────────────────────────────────
AI_EMPIRE = Path(__file__).parent.parent  # ai-empire/
load_dotenv(AI_EMPIRE / "config" / ".env")

sys.path.insert(0, str(AI_EMPIRE))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("EvolutionCycle")

CYCLE_LOG = AI_EMPIRE / "logs" / "evolution_cycles"


# ─── データクラス ─────────────────────────────────────────────────────────────

@dataclass
class StepResult:
    step: str
    success: bool
    duration_sec: float
    result: dict[str, Any] = field(default_factory=dict)
    error: str = ""


@dataclass
class CycleReport:
    cycle_id: str
    started_at: str
    finished_at: str = ""
    steps: list[StepResult] = field(default_factory=list)
    dry_run: bool = False

    @property
    def is_success(self) -> bool:
        return all(s.success for s in self.steps)

    @property
    def total_duration(self) -> float:
        return sum(s.duration_sec for s in self.steps)


# ─── ステップ実行ヘルパー ─────────────────────────────────────────────────────

def _run_step(name: str, fn, **kwargs) -> StepResult:
    logger.info(f"\n{'─'*50}")
    logger.info(f"▶ ステップ: {name}")
    logger.info(f"{'─'*50}")
    start = time.time()
    try:
        result = fn(**kwargs)
        duration = round(time.time() - start, 2)
        logger.info(f"✓ {name} 完了 ({duration}s)")
        return StepResult(step=name, success=True, duration_sec=duration, result=result or {})
    except Exception as e:
        duration = round(time.time() - start, 2)
        logger.error(f"✗ {name} 失敗: {e}")
        return StepResult(step=name, success=False, duration_sec=duration, error=str(e))


# ─── 各ステップの実行関数 ─────────────────────────────────────────────────────

def _load_quality_agent(subdir: str):
    """quality/ 配下のエージェントを動的ロードして返す"""
    agent_path = AI_EMPIRE / "agents" / "quality" / subdir / "agent.py"
    if not agent_path.exists():
        raise FileNotFoundError(f"エージェントが見つかりません: {agent_path}")

    import importlib.util
    mod_name = f"quality_{subdir}"
    # sys.modules に事前登録（dataclass解決のため必須）
    import types
    mod = types.ModuleType(mod_name)
    mod.__file__ = str(agent_path)
    sys.modules[mod_name] = mod

    spec = importlib.util.spec_from_file_location(mod_name, agent_path)
    spec.loader.exec_module(mod)
    return mod


def step_security_scan(dry_run: bool = False) -> dict:
    """Step 1: セキュリティスキャン"""
    agent = _load_quality_agent("security_scanner")
    return agent.run(log_dashboard=not dry_run)


def step_code_review(dry_run: bool = False) -> dict:
    """Step 2: コードレビュー"""
    agent = _load_quality_agent("code_reviewer")
    return agent.run(fix=not dry_run, ai_review=False, log_dashboard=not dry_run)


def step_code_improve(dry_run: bool = False) -> dict:
    """Step 3: コード改善（スコア75未満を対象）"""
    agent = _load_quality_agent("code_improver")
    return agent.run(dry_run=dry_run, log_dashboard=not dry_run, max_files=5)


def step_catalog_update(dry_run: bool = False) -> dict:
    """Step 4: カタログ更新"""
    agent = _load_quality_agent("catalog_updater")
    return agent.run(dry_run=dry_run, gen_md=True, log_dashboard=not dry_run)


# ─── サイクル実行 ─────────────────────────────────────────────────────────────

STEPS = {
    "security": ("セキュリティスキャン", step_security_scan),
    "review": ("コードレビュー", step_code_review),
    "improve": ("コード改善", step_code_improve),
    "catalog": ("カタログ更新", step_catalog_update),
}


def run_cycle(
    steps: list[str] | None = None,
    dry_run: bool = False,
    stop_on_critical: bool = True,
) -> CycleReport:
    """
    進化サイクルを実行する。

    Args:
        steps: 実行ステップ名リスト（Noneなら全ステップ）
        dry_run: ファイル変更なしで実行
        stop_on_critical: CRITICALセキュリティ問題があれば改善ステップを中断
    """
    cycle_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    report = CycleReport(
        cycle_id=cycle_id,
        started_at=datetime.now().isoformat(),
        dry_run=dry_run,
    )

    target_steps = steps or list(STEPS.keys())

    logger.info(f"\n{'='*60}")
    logger.info(f"  Tokumori 自律進化ループ 開始")
    logger.info(f"  cycle_id: {cycle_id}")
    logger.info(f"  dry_run: {dry_run}")
    logger.info(f"  ステップ: {', '.join(target_steps)}")
    logger.info(f"{'='*60}")

    for step_key in target_steps:
        if step_key not in STEPS:
            logger.warning(f"未知のステップ: {step_key} — スキップ")
            continue

        step_name, step_fn = STEPS[step_key]
        step_result = _run_step(step_name, step_fn, dry_run=dry_run)
        report.steps.append(step_result)

        # セキュリティスキャンで CRITICAL があれば後続ステップを安全モードで実行
        if step_key == "security" and stop_on_critical:
            critical = step_result.result.get("critical", 0)
            if critical > 0:
                logger.warning(
                    f"⚠️  CRITICAL問題 {critical}件 — 改善ステップはDRY-RUNで実行します"
                )
                dry_run = True  # 以降ドライランに切り替え

    report.finished_at = datetime.now().isoformat()
    return report


# ─── レポート保存 ─────────────────────────────────────────────────────────────

def save_report(report: CycleReport) -> Path:
    CYCLE_LOG.mkdir(parents=True, exist_ok=True)
    out = CYCLE_LOG / f"cycle_{report.cycle_id}.json"

    data = {
        "cycle_id": report.cycle_id,
        "started_at": report.started_at,
        "finished_at": report.finished_at,
        "dry_run": report.dry_run,
        "is_success": report.is_success,
        "total_duration_sec": report.total_duration,
        "steps": [
            {
                "step": s.step,
                "success": s.success,
                "duration_sec": s.duration_sec,
                "result": s.result,
                "error": s.error,
            }
            for s in report.steps
        ],
    }
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def print_summary(report: CycleReport) -> None:
    status_icon = "✅" if report.is_success else "⚠️ "
    print(f"\n{'='*60}")
    print(f"  {status_icon} 自律進化ループ完了  — {report.cycle_id}")
    print(f"{'='*60}")
    print(f"  総実行時間: {report.total_duration:.1f}秒")
    for s in report.steps:
        icon = "✓" if s.success else "✗"
        print(f"  {icon} {s.step}: {s.duration_sec:.1f}s"
              + (f" — ⚠️ {s.error[:50]}" if s.error else ""))
    print(f"{'='*60}\n")


# ─── dashboard_logger 連携 ────────────────────────────────────────────────────

def _log_to_dashboard(report: CycleReport) -> None:
    if report.dry_run:
        return
    try:
        from utils.dashboard_logger import log_update
        success_steps = sum(1 for s in report.steps if s.success)
        log_update(
            icon="🔄 更新",
            summary=(
                f"自律進化ループ完了: {success_steps}/{len(report.steps)}ステップ成功 "
                f"({report.total_duration:.0f}秒)"
            ),
            targets="agents/ quality/ 全体",
            details=(
                f"①cycle_id: {report.cycle_id} "
                f"②ステップ: {', '.join(s.step for s in report.steps)} "
                f"③結果: {'✅ 正常' if report.is_success else '⚠️ 一部失敗'}"
            ),
        )
    except Exception as e:
        logger.debug(f"dashboard_logger 記録スキップ: {e}")


# ─── パブリックAPI ────────────────────────────────────────────────────────────

def run(
    steps: list[str] | None = None,
    dry_run: bool = False,
    log_dashboard: bool = True,
) -> dict:
    """
    パブリックAPI（evolution_cycle の run）

    Args:
        steps: 実行ステップリスト（Noneなら全ステップ）
        dry_run: ファイル変更なしで実行
        log_dashboard: Update_Logに記録するか
    """
    report = run_cycle(steps=steps, dry_run=dry_run)
    print_summary(report)

    report_path = save_report(report)
    logger.info(f"サイクルレポート保存: {report_path}")

    if log_dashboard:
        _log_to_dashboard(report)

    return {
        "cycle_id": report.cycle_id,
        "steps_run": len(report.steps),
        "success": report.is_success,
        "duration_sec": report.total_duration,
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Tokumori 自律進化ループ")
    parser.add_argument("--step", nargs="+",
                        choices=list(STEPS.keys()),
                        help="実行するステップ（デフォルト: 全ステップ）")
    parser.add_argument("--dry-run", action="store_true",
                        help="ファイル変更なしで実行（テスト用）")
    parser.add_argument("--no-log", action="store_true",
                        help="Update_Log への記録をスキップ")
    args = parser.parse_args()

    result = run(
        steps=args.step,
        dry_run=args.dry_run,
        log_dashboard=not args.no_log,
    )
    status = "✅ 成功" if result["success"] else "⚠️  一部失敗"
    print(f"完了: {status} / {result['steps_run']}ステップ / {result['duration_sec']:.1f}秒")
