#!/usr/bin/env python3
"""
harness/quality_evaluator.py — QualityEvaluator（Phase 3）

quality/review/agent.py のコードレビューロジックを Evaluator のバックエンドとして統合。
コード変更を伴うタスクでは、LLM評価スコアとコードレビュースコアを合算して品質判定する。

使い方:
    from core.harness.quality_evaluator import QualityEvaluator
    evaluator = QualityEvaluator()
    report = evaluator.evaluate(plan, step_results)
"""

from __future__ import annotations

import logging
import re
import sys
from pathlib import Path
from typing import List, Optional

_EMPIRE_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_EMPIRE_ROOT))

from .evaluator import Evaluator
from .models import EvaluationReport, HarnessPlan, StepResult

logger = logging.getLogger("harness.quality_evaluator")

# コードレビュースコアの重み（LLMスコア 70% + コードレビュー 30%）
_CODE_REVIEW_WEIGHT = 0.3
_LLM_WEIGHT = 0.7

# コードレビューが必要なタグ
_CODE_TAGS = {"SF-Schema", "SF-UI", "SF-Data", "SF-Register", "Slide"}

# 総合評価グレード → スコア変換
_GRADE_TO_SCORE = {"A": 1.0, "B": 0.8, "C": 0.55, "D": 0.3}


def _parse_review_grade(review_text: str) -> Optional[float]:
    """
    review_agent の出力テキストから「総合評価: A/B/C/D」を抽出してスコアに変換する。

    例: "総合評価: B — 全体的に良好" → 0.8
    """
    m = re.search(r"総合評価[：:]\s*([ABCD])", review_text)
    if m:
        grade = m.group(1).upper()
        return _GRADE_TO_SCORE.get(grade)
    # 「合計: XX/100」形式にも対応
    m2 = re.search(r"合計[：:]\s*(\d+)/100", review_text)
    if m2:
        return int(m2.group(1)) / 100.0
    return None


class QualityEvaluator(Evaluator):
    """
    コードレビューを組み込んだ拡張 Evaluator。

    コード変更タグ（SF-Schema, SF-UI 等）のステップ結果がある場合に
    quality/review/agent.py のレビュー関数を呼び出してスコアを補正する。
    コード変更がないタスクは基底 Evaluator と同じ動作をする。
    """

    def __init__(
        self,
        model: str = "claude-haiku-4-5-20251001",
        pass_threshold: float = 0.7,
        enable_code_review: bool = True,
    ) -> None:
        super().__init__(model=model, pass_threshold=pass_threshold)
        self._enable_code_review = enable_code_review
        self._review_fn = None  # 遅延インポート

    def _load_review_fn(self):
        """quality/review/agent.py の review_file 関数を遅延ロードする。"""
        if self._review_fn is not None:
            return self._review_fn
        try:
            review_path = _EMPIRE_ROOT / "agents" / "quality" / "review" / "agent.py"
            import importlib.util
            spec = importlib.util.spec_from_file_location("quality_review", str(review_path))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            self._review_fn = mod.review_file
            logger.info("quality/review/agent.py をロードしました")
            return self._review_fn
        except Exception as exc:
            logger.warning("quality/review/agent.py のロード失敗（コードレビューをスキップ）: %s", exc)
            return None

    def _extract_modified_files(self, step_results: List[StepResult]) -> List[str]:
        """
        ステップ出力から変更されたファイルパスを抽出する。
        出力テキスト内の「.py」パスパターンを検索する。
        """
        files = []
        for r in step_results:
            if r.agent_tag not in _CODE_TAGS:
                continue
            found = re.findall(
                r"[\w/\.\-]+\.py",
                r.raw_output or "",
            )
            for f in found:
                candidate = Path(f) if Path(f).is_absolute() else _EMPIRE_ROOT / f
                if candidate.exists():
                    files.append(str(candidate))
        return list(set(files))

    def evaluate(
        self,
        plan: HarnessPlan,
        step_results: List[StepResult],
    ) -> EvaluationReport:
        """
        LLM評価 + コードレビュー（コード変更ありの場合）の合算スコアで品質判定する。
        """
        # ① 基底 Evaluator による LLM評価
        base_report = super().evaluate(plan, step_results)

        if not self._enable_code_review:
            return base_report

        # ② コード変更ステップがあるか確認
        code_steps = [r for r in step_results if r.agent_tag in _CODE_TAGS and r.success]
        if not code_steps:
            logger.debug("QualityEvaluator: コード変更ステップなし → LLM評価のみ")
            return base_report

        # ③ 変更ファイルを抽出してコードレビュー実行
        review_fn = self._load_review_fn()
        if review_fn is None:
            return base_report

        modified_files = self._extract_modified_files(code_steps)
        if not modified_files:
            logger.debug("QualityEvaluator: 変更ファイルを特定できず → LLM評価のみ")
            return base_report

        logger.info("QualityEvaluator: コードレビュー実行 (%d ファイル)", len(modified_files))

        review_scores = []
        review_issues = []
        for filepath in modified_files[:3]:  # 最大3ファイルまで
            try:
                review_result = review_fn(filepath)
                if review_result and review_result.get("review_text"):
                    grade_score = _parse_review_grade(review_result["review_text"])
                    if grade_score is not None:
                        review_scores.append(grade_score)
                        logger.info(
                            "コードレビュースコア: %s → %.2f", Path(filepath).name, grade_score
                        )
                    # Criticalな問題を issues に追加
                    critical = re.findall(
                        r"🔴[^\n]*\n((?:- .+\n?)*)", review_result["review_text"]
                    )
                    if critical:
                        review_issues.extend(
                            [f"[コードレビュー] {line.strip()}" for line in critical[0].splitlines() if line.strip().startswith("-")][:2]
                        )
            except Exception as exc:
                logger.warning("コードレビュー実行エラー (%s): %s", filepath, exc)

        if not review_scores:
            return base_report

        # ④ LLMスコアとコードレビュースコアの加重平均
        avg_review_score = sum(review_scores) / len(review_scores)
        combined_score = (_LLM_WEIGHT * base_report.score) + (_CODE_REVIEW_WEIGHT * avg_review_score)
        combined_passed = combined_score >= self._threshold

        combined_issues = base_report.issues + review_issues
        summary = (
            f"{base_report.summary} / コードレビュー: {avg_review_score:.2f} → 合算: {combined_score:.2f}"
        )

        logger.info(
            "QualityEvaluator: LLM=%.2f CodeReview=%.2f Combined=%.2f passed=%s",
            base_report.score, avg_review_score, combined_score, combined_passed,
        )

        return EvaluationReport(
            task_id=base_report.task_id,
            score=combined_score,
            passed=combined_passed,
            summary=summary,
            issues=combined_issues,
            suggestions=base_report.suggestions + (
                ["コードレビューで指摘された問題を修正してください"] if review_issues else []
            ),
        )
