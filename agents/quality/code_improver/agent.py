"""
Code Improver Agent — ai-empire 品質管理層

code_reviewer の出力（review_*.json）を読み込み、
低スコアファイルを Claude で自動改善提案 → パッチ適用。

機能:
  1. ReviewResult 読み込み        — 最新 review_*.json を自動取得
  2. 改善候補フィルタリング       — スコア75点未満 or CRITICAL/HIGH Issue持ち
  3. Claude による改善提案生成    — 差分ベースのパッチを生成
  4. パッチ適用 + バックアップ    — 適用前 .bak 保存、失敗時ロールバック
  5. dashboard_logger 連携        — 改善結果を Update_Log に自動記録

使い方:
  python3 agents/quality/code_improver/agent.py           # 全改善候補を処理
  python3 agents/quality/code_improver/agent.py --dry-run # 差分表示のみ（適用しない）
  python3 agents/quality/code_improver/agent.py --target agents/hr_support/main.py

BU: Quality / Layer: Improve
canonical_id: quality_code_improver
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import anthropic
from dotenv import load_dotenv

# ─── パス設定 ─────────────────────────────────────────────────────────────────
AI_EMPIRE = Path(__file__).parent.parent.parent.parent  # ai-empire/
load_dotenv(AI_EMPIRE / "config" / ".env")

sys.path.insert(0, str(AI_EMPIRE))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("CodeImprover")

REVIEW_OUT = AI_EMPIRE / "logs" / "code_reviews"
IMPROVE_OUT = AI_EMPIRE / "logs" / "code_improvements"
BACKUP_DIR = AI_EMPIRE / "logs" / "backups"

# quality/ 自身は改善対象外
SELF_EXCLUDE_DIRS = {"code_reviewer", "code_improver", "security_scanner", "catalog_updater"}


# ─── データクラス ─────────────────────────────────────────────────────────────

@dataclass
class ImprovementResult:
    filepath: str
    original_score: int
    patches: list[str] = field(default_factory=list)
    applied: bool = False
    error: str = ""
    ai_suggestion: str = ""


# ─── レビュー結果の読み込み ───────────────────────────────────────────────────

def load_latest_review() -> list[dict[str, Any]]:
    """最新の review_*.json を読み込む"""
    if not REVIEW_OUT.exists():
        logger.warning(f"レビューディレクトリが見つかりません: {REVIEW_OUT}")
        return []

    review_files = sorted(REVIEW_OUT.glob("review_*.json"), reverse=True)
    if not review_files:
        logger.warning("レビュー結果ファイルが見つかりません。先にコードレビューを実行してください。")
        return []

    latest = review_files[0]
    logger.info(f"レビュー結果読み込み: {latest.name}")
    try:
        return json.loads(latest.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        logger.error(f"レビュー結果の解析に失敗: {e}")
        return []


def filter_improvement_targets(
    review_data: list[dict[str, Any]],
    score_threshold: int = 75,
) -> list[dict[str, Any]]:
    """改善対象のファイルを抽出（スコア閾値未満 or CRITICAL/HIGH 問題あり）"""
    targets = []
    for entry in review_data:
        score = entry.get("score", {}).get("total", 100)
        critical = entry.get("critical_count", 0)
        filepath = entry.get("filepath", "")

        # quality/ 自身は除外
        p = Path(filepath)
        if p.parent.name in SELF_EXCLUDE_DIRS:
            continue

        if score < score_threshold or critical > 0:
            targets.append(entry)

    targets.sort(key=lambda e: e.get("score", {}).get("total", 100))
    return targets


# ─── Claude による改善提案 ────────────────────────────────────────────────────

def _build_improve_prompt(filepath: Path, source: str, review_entry: dict[str, Any]) -> str:
    score = review_entry.get("score", {})
    ai_feedback = review_entry.get("ai_feedback", "")
    issues_count = review_entry.get("issues_count", 0)
    critical_count = review_entry.get("critical_count", 0)

    return (
        f"以下の Python ファイルを改善してください。\n\n"
        f"ファイル: `{filepath.name}`\n"
        f"現スコア: {score.get('total', '?')}pt "
        f"(security:{score.get('security','?')} / "
        f"error_handling:{score.get('error_handling','?')} / "
        f"code_quality:{score.get('code_quality','?')} / "
        f"integration:{score.get('integration','?')})\n"
        f"課題数: {issues_count} / CRITICAL: {critical_count}\n"
        f"AIレビュー: {ai_feedback or '(なし)'}\n\n"
        f"ソースコード:\n```python\n{source[:2000]}\n```\n\n"
        "以下の形式で改善提案を出力してください（JSON）:\n"
        "```json\n"
        "{\n"
        '  "patches": [\n'
        '    {"description": "変更内容の説明", "old": "元のコード", "new": "修正後コード"}\n'
        "  ],\n"
        '  "summary": "全体的な改善の要約（日本語100字以内）"\n'
        "}\n"
        "```\n\n"
        "注意:\n"
        "- old/new は完全に一致する文字列（行単位）を指定してください\n"
        "- 機能を変えずに品質だけ改善してください\n"
        "- 改善が不要なら patches を空リストにしてください"
    )


def generate_improvements(
    filepath: Path,
    review_entry: dict[str, Any],
) -> tuple[list[dict[str, str]], str]:
    """Claude で改善パッチを生成する。(patches, summary) を返す"""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY が未設定 — AI改善をスキップ")
        return [], ""

    try:
        source = filepath.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        logger.error(f"ファイル読み込み失敗: {filepath}: {e}")
        return [], ""

    prompt = _build_improve_prompt(filepath, source, review_entry)

    try:
        client = anthropic.Anthropic(api_key=api_key, timeout=120.0)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        response_text = msg.content[0].text
    except Exception as e:
        logger.warning(f"Claude API呼び出し失敗: {e}")
        return [], ""

    # JSON抽出
    json_match = re.search(r"```json\s*(.*?)\s*```", response_text, re.DOTALL)
    if not json_match:
        # コードブロックなしで直接JSONの場合
        json_match = re.search(r"\{.*\}", response_text, re.DOTALL)

    if not json_match:
        logger.warning(f"Claude からの JSON 抽出失敗: {filepath.name}")
        return [], response_text[:200]

    try:
        data = json.loads(json_match.group(1) if json_match.lastindex else json_match.group(0))
        patches = data.get("patches", [])
        summary = data.get("summary", "")
        return patches, summary
    except json.JSONDecodeError as e:
        logger.warning(f"JSON解析失敗 ({filepath.name}): {e}")
        return [], ""


# ─── パッチ適用 ───────────────────────────────────────────────────────────────

def _backup(filepath: Path) -> Path:
    """適用前バックアップを作成"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"{filepath.name}.{ts}.bak"
    shutil.copy2(filepath, backup_path)
    return backup_path


def apply_patches(
    filepath: Path,
    patches: list[dict[str, str]],
    dry_run: bool = False,
) -> tuple[bool, list[str]]:
    """
    パッチを適用する。

    Returns:
        (success, applied_descriptions)
    """
    if not patches:
        return False, []

    try:
        source = filepath.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        logger.error(f"ファイル読み込み失敗: {filepath}: {e}")
        return False, []

    applied_descriptions = []
    modified_source = source

    for patch in patches:
        old_code = patch.get("old", "")
        new_code = patch.get("new", "")
        desc = patch.get("description", "パッチ適用")

        if not old_code or not new_code or old_code == new_code:
            continue

        if old_code not in modified_source:
            logger.debug(f"  スキップ (対象コードが見つからない): {desc}")
            continue

        modified_source = modified_source.replace(old_code, new_code, 1)
        applied_descriptions.append(desc)
        logger.info(f"  ✓ {desc}")

    if not applied_descriptions:
        return False, []

    if dry_run:
        logger.info(f"  [DRY-RUN] {len(applied_descriptions)}件のパッチを適用予定")
        return True, applied_descriptions

    backup = _backup(filepath)
    logger.debug(f"  バックアップ: {backup}")

    try:
        filepath.write_text(modified_source, encoding="utf-8")
        return True, applied_descriptions
    except OSError as e:
        logger.error(f"ファイル書き込み失敗 — ロールバック: {e}")
        shutil.copy2(backup, filepath)
        return False, []


# ─── 改善実行 ─────────────────────────────────────────────────────────────────

def improve_file(
    filepath: Path,
    review_entry: dict[str, Any],
    dry_run: bool = False,
) -> ImprovementResult:
    logger.info(f"改善処理: {filepath.name}")
    result = ImprovementResult(
        filepath=str(filepath),
        original_score=review_entry.get("score", {}).get("total", 0),
    )

    patches, summary = generate_improvements(filepath, review_entry)

    if not patches:
        result.ai_suggestion = summary or "改善不要"
        return result

    result.ai_suggestion = summary
    success, applied = apply_patches(filepath, patches, dry_run=dry_run)
    result.patches = applied
    result.applied = success
    return result


def improve_all(
    review_data: list[dict[str, Any]],
    target_file: Path | None = None,
    score_threshold: int = 75,
    dry_run: bool = False,
    max_files: int = 10,
) -> list[ImprovementResult]:
    if target_file:
        # 単一ファイルモード
        entry = next(
            (e for e in review_data if Path(e.get("filepath", "")).name == target_file.name),
            {"filepath": str(target_file), "score": {"total": 0}},
        )
        return [improve_file(target_file, entry, dry_run=dry_run)]

    targets = filter_improvement_targets(review_data, score_threshold)[:max_files]
    logger.info(f"改善対象: {len(targets)}ファイル")

    results = []
    for entry in targets:
        fp = Path(entry["filepath"])
        if not fp.exists():
            logger.warning(f"ファイルが見つかりません: {fp}")
            continue
        results.append(improve_file(fp, entry, dry_run=dry_run))

    return results


# ─── レポート保存・表示 ───────────────────────────────────────────────────────

def save_report(results: list[ImprovementResult]) -> Path:
    IMPROVE_OUT.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = IMPROVE_OUT / f"improvement_{ts}.json"

    data = [
        {
            "filepath": r.filepath,
            "original_score": r.original_score,
            "patches_count": len(r.patches),
            "applied": r.applied,
            "patches": r.patches,
            "ai_suggestion": r.ai_suggestion,
            "error": r.error,
        }
        for r in results
    ]
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def print_summary(results: list[ImprovementResult], dry_run: bool = False) -> None:
    if not results:
        print("改善対象なし")
        return
    mode = "[DRY-RUN] " if dry_run else ""
    applied = [r for r in results if r.applied]
    print(f"\n{'='*60}")
    print(f"  {mode}コード改善結果  — {len(results)}ファイル処理")
    print(f"{'='*60}")
    print(f"  改善適用: {len(applied)} / {len(results)}ファイル")
    for r in results:
        status = "✓" if r.applied else "−"
        patches_str = f" ({len(r.patches)}件)" if r.patches else ""
        print(f"  {status} {Path(r.filepath).name}{patches_str}"
              + (f" — {r.ai_suggestion[:40]}" if r.ai_suggestion else ""))
    print(f"{'='*60}\n")


# ─── dashboard_logger 連携 ────────────────────────────────────────────────────

def _log_to_dashboard(results: list[ImprovementResult], dry_run: bool = False) -> None:
    try:
        from utils.dashboard_logger import log_update
        applied = [r for r in results if r.applied]
        total_patches = sum(len(r.patches) for r in applied)
        mode_str = "(DRY-RUN)" if dry_run else ""
        log_update(
            icon="➕ 機能追加",
            summary=f"コード改善実行{mode_str}: {len(results)}ファイル / {len(applied)}件適用",
            targets="agents/ 改善対象",
            details=(
                f"①改善適用: {len(applied)}ファイル "
                f"②パッチ数: {total_patches}件 "
                f"③バックアップ: {BACKUP_DIR}"
            ),
        )
    except Exception as e:
        logger.debug(f"dashboard_logger 記録スキップ: {e}")


# ─── パブリックAPI ────────────────────────────────────────────────────────────

def run(
    target: str | None = None,
    score_threshold: int = 75,
    dry_run: bool = False,
    log_dashboard: bool = True,
    max_files: int = 10,
) -> dict:
    """
    パブリックAPI

    Args:
        target: 対象ファイルパス（Noneなら全改善候補）
        score_threshold: 改善対象スコア閾値（デフォルト75）
        dry_run: Trueなら差分表示のみ（ファイル変更なし）
        log_dashboard: Update_Logに記録するか
        max_files: 一度に処理する最大ファイル数
    """
    logger.info(f"コード改善開始: {target or '全改善候補'} (dry_run={dry_run})")

    review_data = load_latest_review()
    if not review_data:
        return {"improved": 0, "patches_total": 0, "error": "レビュー結果なし"}

    target_path = Path(target) if target else None
    results = improve_all(
        review_data,
        target_file=target_path,
        score_threshold=score_threshold,
        dry_run=dry_run,
        max_files=max_files,
    )

    print_summary(results, dry_run=dry_run)

    if results:
        report_path = save_report(results)
        logger.info(f"改善レポート保存: {report_path}")
        if log_dashboard and not dry_run:
            _log_to_dashboard(results, dry_run=dry_run)

    applied = [r for r in results if r.applied]
    return {
        "processed": len(results),
        "improved": len(applied),
        "patches_total": sum(len(r.patches) for r in applied),
        "dry_run": dry_run,
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="ai-empire コード改善エージェント")
    parser.add_argument("--target", help="対象ファイルパス")
    parser.add_argument("--dry-run", action="store_true", help="差分表示のみ（適用しない）")
    parser.add_argument("--threshold", type=int, default=75, help="改善対象スコア閾値 (default: 75)")
    parser.add_argument("--max", type=int, default=10, help="最大処理ファイル数 (default: 10)")
    parser.add_argument("--no-log", action="store_true", help="Update_Log への記録をスキップ")
    args = parser.parse_args()

    result = run(
        target=args.target,
        score_threshold=args.threshold,
        dry_run=args.dry_run,
        log_dashboard=not args.no_log,
        max_files=args.max,
    )
    print(f"完了: {result['processed']}ファイル処理 / {result['improved']}件改善適用 / "
          f"パッチ{result['patches_total']}件")
