"""
Code Reviewer Agent — ai-empire 品質管理層

全エージェント(.py)を静的解析 + Claude セマンティックレビューで審査し、
スコア(0-100)とグレードを付ける。

機能:
  1. 静的解析 (AST)          — APIコストゼロ・即時
  2. Claude セマンティックレビュー — 論理・統合・改善提案
  3. スコアリング (0-100)     — security/error_handling/code_quality/integration
  4. dashboard_logger 連携    — 結果を Update_Log に自動記録

使い方:
  python3 agents/quality/code_reviewer/agent.py                    # 全エージェント
  python3 agents/quality/code_reviewer/agent.py agents/hr_support/ # 特定ディレクトリ
  python3 agents/quality/code_reviewer/agent.py --fix              # 自動修正付き

BU: Quality / Layer: Review
canonical_id: quality_code_reviewer
"""

from __future__ import annotations

import ast
import json
import logging
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

import anthropic
from dotenv import load_dotenv

# ─── パス設定（ai-empire構造に合わせる） ─────────────────────────────────────
AI_EMPIRE = Path(__file__).parent.parent.parent.parent  # ai-empire/
load_dotenv(AI_EMPIRE / "config" / ".env")

sys.path.insert(0, str(AI_EMPIRE))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("CodeReviewer")

AGENTS_DIR = AI_EMPIRE / "agents"
REVIEW_OUT = AI_EMPIRE / "logs" / "code_reviews"

# ─── データクラス ──────────────────────────────────────────────────────────────

@dataclass
class Issue:
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]
    category: str
    message: str
    line: int = 0
    fix: str = ""


@dataclass
class ReviewScore:
    security: int = 25
    error_handling: int = 25
    code_quality: int = 25
    integration: int = 25

    @property
    def total(self) -> int:
        return self.security + self.error_handling + self.code_quality + self.integration

    @property
    def grade(self) -> str:
        t = self.total
        if t >= 90: return "A"
        if t >= 75: return "B"
        if t >= 60: return "C"
        return "D"


@dataclass
class ReviewResult:
    filepath: str
    score: ReviewScore
    issues: list[Issue]
    ai_feedback: str = ""
    fixed: bool = False
    duration_sec: float = 0.0


# ─── 静的解析 ─────────────────────────────────────────────────────────────────

# 自己適用除外（このファイル自身と改善エージェントは対象外）
SELF_EXCLUDE = {
    "agent.py",  # 全 quality/ エージェント自身
}


class StaticAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.issues: list[Issue] = []

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.type is None:
            self.issues.append(Issue(
                "HIGH", "error_handling",
                "裸の `except:` — 必ず `except SpecificError as e:` で捕捉",
                node.lineno,
                "except Exception as e:",
            ))
        elif node.name is None and node.type is not None:
            exc_name = ast.unparse(node.type) if hasattr(ast, "unparse") else str(node.type)
            self.issues.append(Issue(
                "MEDIUM", "error_handling",
                f"`except {exc_name}:` に `as e` がない — ログ出力でエラー内容が取れない",
                node.lineno,
                f"except {exc_name} as e:",
            ))
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        lines = (node.end_lineno or node.lineno) - node.lineno
        if lines > 60:
            self.issues.append(Issue(
                "MEDIUM", "code_quality",
                f"`{node.name}()` が {lines}行 — 50行超えたら分割を検討",
                node.lineno,
                "責務ごとにサブ関数に分割",
            ))
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        # timeout未設定のAPIコール検出
        func_str = ast.unparse(node) if hasattr(ast, "unparse") else ""
        if any(kw in func_str for kw in ["requests.get", "requests.post", "httpx."]):
            has_timeout = any(
                (isinstance(k, ast.keyword) and k.arg == "timeout")
                for k in node.keywords
            )
            if not has_timeout:
                self.issues.append(Issue(
                    "MEDIUM", "error_handling",
                    "外部HTTP呼び出しに `timeout` がない — ハングアップリスク",
                    node.lineno,
                    "timeout=30 を追加",
                ))
        self.generic_visit(node)


def _check_open_statements(source: str, issues: list[Issue]) -> None:
    for i, line in enumerate(source.splitlines(), 1):
        if "open(" in line and "encoding" not in line and not line.strip().startswith("#"):
            # f-string内のopen(は除外
            if 'f"' not in line and "f'" not in line:
                issues.append(Issue(
                    "LOW", "code_quality",
                    f"行{i}: `open()` に `encoding='utf-8'` がない",
                    i, "encoding='utf-8' を追加",
                ))


def _check_security(source: str, issues: list[Issue]) -> None:
    # ハードコードAPIキーパターン
    patterns = [
        (r'sk-ant-[a-zA-Z0-9\-_]{20,}', "CRITICAL", "Anthropic APIキーがハードコード"),
        (r'sk-[a-zA-Z0-9]{32,}', "CRITICAL", "OpenAI APIキーがハードコード"),
        (r'AKIA[0-9A-Z]{16}', "CRITICAL", "AWS Access Keyがハードコード"),
        (r'ghp_[a-zA-Z0-9]{36}', "HIGH", "GitHub tokenがハードコード"),
    ]
    for pattern, severity, msg in patterns:
        if re.search(pattern, source):
            issues.append(Issue(severity, "security", msg, 0, "os.environ.get() に変更"))

    # environ直接アクセス
    if re.search(r'os\.environ\[', source):
        issues.append(Issue(
            "LOW", "security",
            "os.environ[] 直接アクセス — KeyError リスク。os.environ.get() を使う",
            0, "os.environ.get('KEY', default)",
        ))


def _check_integration(source: str, filepath: Path, issues: list[Issue]) -> None:
    if "run(" not in source and "execute(" not in source and "main(" not in source:
        issues.append(Issue(
            "LOW", "integration",
            "パブリックAPI (run/execute/main) が見当たらない",
            0, "def run() パブリックAPIを実装",
        ))
    if "ANTHROPIC_API_KEY" in source and "load_dotenv" not in source:
        issues.append(Issue(
            "MEDIUM", "integration",
            "ANTHROPIC_API_KEY を使うが load_dotenv() がない",
            0, "from dotenv import load_dotenv; load_dotenv()",
        ))


def run_static_analysis(filepath: Path) -> list[Issue]:
    issues: list[Issue] = []
    try:
        source = filepath.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        logger.warning(f"読み込み失敗: {filepath}: {e}")
        return issues

    try:
        tree = ast.parse(source, filename=str(filepath))
        analyzer = StaticAnalyzer()
        analyzer.visit(tree)
        issues.extend(analyzer.issues)
    except SyntaxError as e:
        issues.append(Issue("HIGH", "code_quality", f"構文エラー: {e}", 0))

    _check_open_statements(source, issues)
    _check_security(source, issues)
    _check_integration(source, filepath, issues)
    return issues


# ─── スコアリング ─────────────────────────────────────────────────────────────

def calculate_score(issues: list[Issue]) -> ReviewScore:
    score = ReviewScore()
    deductions = {"security": 0, "error_handling": 0, "code_quality": 0, "integration": 0}
    weights = {"CRITICAL": 15, "HIGH": 8, "MEDIUM": 4, "LOW": 2, "INFO": 0}

    for issue in issues:
        cat = issue.category if issue.category in deductions else "code_quality"
        deductions[cat] += weights.get(issue.severity, 0)

    score.security = max(0, 25 - deductions["security"])
    score.error_handling = max(0, 25 - deductions["error_handling"])
    score.code_quality = max(0, 25 - deductions["code_quality"])
    score.integration = max(0, 25 - deductions["integration"])
    return score


# ─── 自動修正 ─────────────────────────────────────────────────────────────────

def auto_fix(filepath: Path, source: str, issues: list[Issue]) -> tuple[str, list[str]]:
    """quality/ 配下のエージェント自身は除外"""
    if filepath.parent.name in ("code_reviewer", "code_improver", "security_scanner", "catalog_updater"):
        return source, []

    applied: list[str] = []

    # logging import 追加
    if "import logging" not in source:
        source = "import logging\n" + source
        applied.append("import logging を追加")
    if "logger = logging.getLogger" not in source:
        lines = source.splitlines()
        for i, line in enumerate(lines):
            if line.startswith("logger") or "logging.basicConfig" in line:
                break
        else:
            import_end = next(
                (i for i, l in enumerate(lines) if l and not l.startswith(("import", "from", "#", '"""', "'''"))),
                3,
            )
            lines.insert(import_end, 'logger = logging.getLogger(__name__)')
            source = "\n".join(lines)
            applied.append("logger を追加")

    # except ExcType: → except ExcType as e:
    def fix_except(m: re.Match) -> str:
        exc_type = m.group(1)
        if re.search(r'\bas\s+\w+', exc_type):
            return m.group(0)
        return f"except {exc_type} as e:"

    new_source = re.sub(r"except\s+([\w\.,\s\[\]]+?)\s*:", fix_except, source)
    if new_source != source:
        source = new_source
        applied.append("except に as e を追加")

    # open() に encoding="utf-8" を追加
    def fix_open(m: re.Match) -> str:
        if "encoding" in m.group(0):
            return m.group(0)
        return m.group(0).rstrip(")") + ', encoding="utf-8")'

    new_source = re.sub(r'open\([^)]+\)', fix_open, source)
    if new_source != source:
        source = new_source
        applied.append("open() に encoding='utf-8' を追加")

    # load_dotenv 追加
    if "ANTHROPIC_API_KEY" in source and "load_dotenv" not in source:
        source = "from dotenv import load_dotenv\nload_dotenv()\n" + source
        applied.append("load_dotenv() を追加")

    if applied and source != filepath.read_text(encoding="utf-8", errors="replace"):
        filepath.write_text(source, encoding="utf-8")

    return source, applied


# ─── Claudeセマンティックレビュー ────────────────────────────────────────────

def run_ai_review(filepath: Path, source: str, static_issues: list[Issue]) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return ""
    try:
        client = anthropic.Anthropic(api_key=api_key, timeout=120.0)
        issues_summary = "\n".join(
            f"- [{i.severity}] {i.category}: {i.message}"
            for i in static_issues[:10]
        )
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=600,
            messages=[{
                "role": "user",
                "content": (
                    f"ai-empireエージェント `{filepath.name}` の品質レビューをしてください。\n\n"
                    f"静的解析の指摘:\n{issues_summary or '(なし)'}\n\n"
                    f"ソース冒頭(300文字):\n```python\n{source[:300]}\n```\n\n"
                    "①主要な改善点(2点以内) ②良い点(1点) を簡潔に（日本語200字以内）"
                ),
            }],
        )
        return msg.content[0].text
    except Exception as e:
        logger.warning(f"AIレビュー失敗: {e}")
        return ""


# ─── レビュー実行 ─────────────────────────────────────────────────────────────

def review_file(filepath: Path, fix: bool = False, ai_review: bool = False) -> ReviewResult:
    import time
    start = time.time()
    source = filepath.read_text(encoding="utf-8", errors="replace")
    issues = run_static_analysis(filepath)
    score = calculate_score(issues)
    ai_fb = run_ai_review(filepath, source, issues) if ai_review else ""

    fixed = False
    if fix:
        _, applied = auto_fix(filepath, source, issues)
        fixed = bool(applied)

    return ReviewResult(
        filepath=str(filepath),
        score=score,
        issues=issues,
        ai_feedback=ai_fb,
        fixed=fixed,
        duration_sec=round(time.time() - start, 2),
    )


def review_all(
    target_dir: Path | None = None,
    fix: bool = False,
    ai_review: bool = False,
    max_files: int = 50,
) -> list[ReviewResult]:
    target = target_dir or AGENTS_DIR
    files = sorted(target.rglob("*.py"))[:max_files]
    # quality/ 自身は除外
    files = [f for f in files if "quality" not in f.parts[-3:] or f.name not in SELF_EXCLUDE]

    results = []
    for f in files:
        result = review_file(f, fix=fix, ai_review=ai_review)
        results.append(result)
        grade_icon = {"A": "✓", "B": "○", "C": "△", "D": "✗"}.get(result.score.grade, "?")
        logger.info(f"  {grade_icon} {f.name}: {result.score.total}pt ({result.score.grade})")

    return results


# ─── レポート保存・表示 ───────────────────────────────────────────────────────

def save_report(results: list[ReviewResult]) -> Path:
    REVIEW_OUT.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = REVIEW_OUT / f"review_{ts}.json"

    data = []
    for r in results:
        data.append({
            "filepath": r.filepath,
            "score": {
                "total": r.score.total,
                "grade": r.score.grade,
                "security": r.score.security,
                "error_handling": r.score.error_handling,
                "code_quality": r.score.code_quality,
                "integration": r.score.integration,
            },
            "issues_count": len(r.issues),
            "critical_count": sum(1 for i in r.issues if i.severity == "CRITICAL"),
            "ai_feedback": r.ai_feedback,
        })

    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def print_summary(results: list[ReviewResult]) -> None:
    if not results:
        print("レビュー対象なし")
        return
    scores = [r.score.total for r in results]
    avg = sum(scores) / len(scores)
    grade_counts = {}
    for r in results:
        grade_counts[r.score.grade] = grade_counts.get(r.score.grade, 0) + 1

    print(f"\n{'='*60}")
    print(f"  コードレビュー結果  — {len(results)}ファイル")
    print(f"{'='*60}")
    print(f"  平均スコア: {avg:.1f}pt")
    for g in ["A", "B", "C", "D"]:
        c = grade_counts.get(g, 0)
        bar = "█" * c
        print(f"  {g}評価: {bar} ({c}件)")
    print()

    # 下位5件を表示
    worst = sorted(results, key=lambda r: r.score.total)[:5]
    if any(r.score.total < 75 for r in worst):
        print("  【改善優先ファイル】")
        for r in worst:
            if r.score.total < 75:
                name = Path(r.filepath).name
                crits = sum(1 for i in r.issues if i.severity == "CRITICAL")
                print(f"    {r.score.total}pt({r.score.grade}) {name}"
                      + (f" ⚠ CRITICAL:{crits}" if crits else ""))
    print(f"{'='*60}\n")


# ─── dashboard_logger 連携 ────────────────────────────────────────────────────

def _log_to_dashboard(results: list[ReviewResult]) -> None:
    """レビュー結果を ai-empire の Update_Log に記録する"""
    try:
        from utils.dashboard_logger import log_update
        scores = [r.score.total for r in results]
        avg = sum(scores) / len(scores) if scores else 0
        grade_counts = {}
        for r in results:
            grade_counts[r.score.grade] = grade_counts.get(r.score.grade, 0) + 1
        gc_str = " / ".join(f"{g}:{c}" for g, c in sorted(grade_counts.items()))
        log_update(
            icon="🔧 修正",
            summary=f"コードレビュー実行: {len(results)}ファイル / 平均{avg:.1f}pt",
            targets="agents/ 全体",
            details=f"①グレード分布: {gc_str} ②平均スコア: {avg:.1f}pt",
        )
    except Exception as e:
        logger.debug(f"dashboard_logger 記録スキップ: {e}")


# ─── メイン ──────────────────────────────────────────────────────────────────

def run(
    target: str | None = None,
    fix: bool = False,
    ai_review: bool = False,
    log_dashboard: bool = True,
) -> dict:
    """
    パブリックAPI

    Args:
        target: レビュー対象パス（Noneなら全agents/）
        fix: 自動修正を適用するか
        ai_review: Claude AIレビューを実行するか
        log_dashboard: Update_Logに記録するか
    """
    target_path = Path(target) if target else None
    logger.info(f"コードレビュー開始: {target or 'agents/ 全体'}")

    results = review_all(target_path, fix=fix, ai_review=ai_review)
    print_summary(results)

    if results:
        report_path = save_report(results)
        logger.info(f"レポート保存: {report_path}")
        if log_dashboard:
            _log_to_dashboard(results)

    scores = [r.score.total for r in results]
    avg = sum(scores) / len(scores) if scores else 0
    return {
        "reviewed": len(results),
        "avg_score": round(avg, 1),
        "grade_counts": {
            g: sum(1 for r in results if r.score.grade == g)
            for g in ["A", "B", "C", "D"]
        },
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="ai-empire コードレビューエージェント")
    parser.add_argument("target", nargs="?", help="レビュー対象ディレクトリ/ファイル")
    parser.add_argument("--fix", action="store_true", help="自動修正を適用")
    parser.add_argument("--ai", action="store_true", help="Claude AIレビューを有効化")
    parser.add_argument("--no-log", action="store_true", help="Update_Log への記録をスキップ")
    args = parser.parse_args()

    result = run(
        target=args.target,
        fix=args.fix,
        ai_review=args.ai,
        log_dashboard=not args.no_log,
    )
    print(f"完了: {result['reviewed']}ファイル / 平均 {result['avg_score']}pt")
