#!/usr/bin/env python3
"""
harness/evaluator.py — Evaluator エージェント

全ステップの実行結果を受け取り、品質スコアと改善提案を返す。
スコアが閾値未満の場合、HarnessRunner は再計画ループに入る。
"""

from __future__ import annotations

import json
import logging
import os
from typing import List

import anthropic

from .models import EvaluationReport, HarnessPlan, StepResult

logger = logging.getLogger("harness.evaluator")

_PASS_THRESHOLD = 0.7  # 0.0〜1.0: これ以上で「合格」

_SYSTEM_PROMPT = """あなたはTokumoriのタスク評価エージェントです。
与えられたタスク目標と実行結果を比較し、達成度を評価します。

評価基準:
- 目標の達成度（最重要）
- エラーの有無と深刻度
- 出力の品質と完全性

出力形式（JSONのみ、前置き不要）:
{
  "score": 0.85,
  "summary": "評価の一言サマリー（1文）",
  "issues": ["問題点1", "問題点2"],
  "suggestions": ["改善提案1", "改善提案2"]
}

score は 0.0〜1.0 の数値。問題なく完了なら 0.9〜1.0。
部分的に達成なら 0.5〜0.8。大きな失敗があれば 0.0〜0.4。"""


class Evaluator:
    """
    ステップ実行結果を評価し、EvaluationReport を返す。

    Usage:
        evaluator = Evaluator()
        report = evaluator.evaluate(plan, step_results)
        if not report.passed:
            # 再計画ループへ
    """

    def __init__(
        self,
        model: str = "claude-haiku-4-5-20251001",
        pass_threshold: float = _PASS_THRESHOLD,
    ) -> None:
        self._client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        self._model = model
        self._threshold = pass_threshold

    def evaluate(
        self,
        plan: HarnessPlan,
        step_results: List[StepResult],
    ) -> EvaluationReport:
        """
        計画と実行結果を比較して品質評価する。

        Args:
            plan:         実行計画（goal・steps）
            step_results: 各ステップの実行結果

        Returns:
            EvaluationReport
        """
        logger.info("Evaluator: 評価開始 [%s]", plan.task_id)

        # 評価用プロンプトを構築
        results_text = "\n".join(
            f"ステップ{r.step_no}: {'✅ 成功' if r.success else '❌ 失敗'}\n"
            f"  出力: {r.raw_output[:300]}\n"
            + (f"  エラー: {r.error_msg}\n" if r.error_msg else "")
            for r in step_results
        )

        prompt = (
            f"タスク目標: {plan.goal}\n\n"
            f"実行結果:\n{results_text}"
        )

        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=600,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()
            start = raw.find("{")
            end = raw.rfind("}") + 1
            data = json.loads(raw[start:end]) if start >= 0 and end > start else {}
        except Exception as exc:
            logger.warning("Evaluator: LLM呼び出し失敗 → ルールベース評価にフォールバック: %s", exc)
            data = {}

        # LLMが失敗した場合はルールベースでスコア計算
        if not data:
            success_count = sum(1 for r in step_results if r.success)
            total = len(step_results) or 1
            score = success_count / total
            data = {
                "score": score,
                "summary": f"{total}ステップ中{success_count}ステップ成功",
                "issues": [r.error_msg for r in step_results if r.error_msg],
                "suggestions": [],
            }

        score = float(data.get("score", 0.0))
        passed = score >= self._threshold

        report = EvaluationReport(
            task_id=plan.task_id,
            score=score,
            passed=passed,
            summary=data.get("summary", ""),
            issues=data.get("issues", []),
            suggestions=data.get("suggestions", []),
        )

        logger.info(
            "Evaluator: 評価完了 [%s] score=%.2f passed=%s",
            plan.task_id, score, passed,
        )
        return report
