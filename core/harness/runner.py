#!/usr/bin/env python3
"""
harness/runner.py — HarnessRunner（エージェントハーネス本体）

【役割】
  Initializer → Planner → Generator → Evaluator のループを管理する。
  スコアが閾値未満の場合、最大 max_iterations 回まで再計画・再実行する。
  Progress File で状態を外部化し、コンテキストリセット後も再開可能。

【アーキテクチャ（Phase 4 更新）】
                        ┌──────────────────────┐
  タスク記述 ──▶ Init   │ 要件リスト展開        │  ← Phase 4 追加
                        └──────────────────────┘
                                  ↓ (progress.json 作成)
                        ┌──────────────────────┐
                        │ Planner  計画生成     │
                        └──────────────────────┘
                                  ↓
                        ┌──────────────────────┐
                        │ Generator ループ      │  ← 既存エージェントを呼び出す
                        └──────────────────────┘
                                  ↓
                        ┌──────────────────────┐
              ┌── No ── │ Evaluator 品質判定    │ ── Yes ──▶ DONE
              │         └──────────────────────┘
              ▼
          再計画ループ（max_iterations 回まで）

【使い方】
  runner = HarnessRunner(dispatcher=my_dispatch_fn)
  result = runner.run("SF-Schemaにフィールドを追加して")

  # Initializer を無効化（後方互換）
  runner = HarnessRunner(use_initializer=False, dispatcher=my_dispatch_fn)
"""

from __future__ import annotations

import logging
import sys
import uuid
from pathlib import Path
from typing import Callable, Dict, Optional

_EMPIRE_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_EMPIRE_ROOT))

from .evaluator import Evaluator
from .initializer import Initializer
from .memory import MemoryStore
from .progress_file import ProgressFile
from .quality_evaluator import QualityEvaluator
from .models import (
    HarnessResult,
    HarnessStatus,
    HarnessPlan,
    StepResult,
)
from .planner import Planner

logger = logging.getLogger("harness.runner")

# dispatcher の型ヒント: タグ名とタスク辞書を受け取り、成功/失敗と出力を返す
DispatchFn = Callable[[str, dict], tuple[bool, str]]


class HarnessRunner:
    """
    Planner → Generator → Evaluator ループを管理するハーネス本体。

    Args:
        dispatcher:     タグとタスク辞書からエージェントを起動する関数
                        シグネチャ: (tag: str, task: dict) -> (success: bool, output: str)
        max_iterations: 最大再計画回数（デフォルト: 3）
        planner_model:  Planner が使う LLM モデル
        evaluator_model: Evaluator が使う LLM モデル
    """

    def __init__(
        self,
        dispatcher: Optional[DispatchFn] = None,
        max_iterations: int = 3,
        planner_model: str = "claude-haiku-4-5-20251001",
        evaluator_model: str = "claude-haiku-4-5-20251001",
        use_quality_evaluator: bool = True,
        use_initializer: bool = True,
        use_progress_file: bool = True,
    ) -> None:
        self._dispatcher = dispatcher or self._noop_dispatcher
        self._max_iterations = max_iterations
        self._planner = Planner(model=planner_model)
        self._use_initializer = use_initializer
        self._use_progress_file = use_progress_file
        # Phase 4: Initializer
        self._initializer = Initializer(model=planner_model) if use_initializer else None
        # Phase 6: MUSE Memory
        self._memory = MemoryStore.get_instance()
        # Phase 3: コードレビュー統合Evaluatorを標準で使用
        if use_quality_evaluator:
            self._evaluator = QualityEvaluator(model=evaluator_model)
        else:
            self._evaluator = Evaluator(model=evaluator_model)

    # ── パブリックAPI ──────────────────────────────────────────

    def run(
        self,
        description: str,
        task_id: Optional[str] = None,
        context: Optional[Dict] = None,
    ) -> HarnessResult:
        """
        タスク記述を受け取り、Planner→Generator→Evaluator ループを実行する。

        Args:
            description: タスクの自然言語記述
            task_id:     タスクID（省略時は自動生成）
            context:     エージェントに渡す追加コンテキスト

        Returns:
            HarnessResult（status・plan・step_results・evaluation を含む）
        """
        task_id = task_id or str(uuid.uuid4())[:8]
        context = context or {}
        logger.info("HarnessRunner: 開始 [%s] %s", task_id, description[:80])

        plan: Optional[HarnessPlan] = None
        step_results = []
        evaluation = None
        status = HarnessStatus.PENDING

        # ── Phase 4: Progress File 作成 ────────────────────────
        pf: Optional[ProgressFile] = None
        if self._use_progress_file:
            pf = ProgressFile.create(task_id=task_id, description=description)

        # ── Phase 4: Initializer ───────────────────────────────
        enriched_description = description
        if self._initializer:
            init_output = self._initializer.initialize(description, task_id=task_id)
            # Phase 6: 記憶からコンテキストを取得してInitializer出力に付加
            memory_ctx = self._memory.get_context_for_task(description)
            enriched_description = init_output.to_markdown()
            if memory_ctx:
                enriched_description += f"\n\n{memory_ctx}"
            if pf:
                pf.set_goal(init_output.goal)
                pf.set_requirements([
                    {"req_id": r.req_id, "description": r.description,
                     "status": r.status, "agent_hint": r.agent_hint}
                    for r in init_output.requirements
                ])
            logger.info(
                "HarnessRunner: Initializer完了 [%s] %d要件",
                task_id, len(init_output.requirements),
            )

        for iteration in range(1, self._max_iterations + 1):
            logger.info("HarnessRunner: イテレーション %d/%d", iteration, self._max_iterations)

            # ── Planner ───────────────────────────────────────
            status = HarnessStatus.PLANNING
            if pf:
                pf.set_phase("planning")
            if iteration == 1:
                plan = self._planner.plan(enriched_description, task_id=task_id)
            else:
                # 再計画: 評価結果を反映した新しい計画
                feedback = ""
                if evaluation:
                    feedback = f"\n\n前回の問題点:\n" + "\n".join(f"- {i}" for i in evaluation.issues)
                    feedback += f"\n改善提案:\n" + "\n".join(f"- {s}" for s in evaluation.suggestions)
                plan = self._planner.plan(description + feedback, task_id=task_id)
                logger.info("HarnessRunner: 再計画完了 [%s]", task_id)

            # ── Generator（既存エージェント実行） ─────────────
            status = HarnessStatus.RUNNING
            if pf:
                pf.set_phase("running")
            step_results = []
            for step in plan.steps:
                tag = step.agent_tag
                task_dict = {
                    "tag": tag,
                    "description": step.description,
                    "context": {**context, **step.context},
                    "expected_output": step.expected_output,
                }
                logger.info(
                    "HarnessRunner: ステップ%d実行 [%s] tag=%s desc=%s",
                    step.step_no, task_id, tag, step.description[:50],
                )

                if tag:
                    # harness_context を task_dict に埋め込む（BaseAgent.run_from_harness で受信）
                    task_dict["harness_context"] = {
                        "goal": plan.goal,
                        "step_no": step.step_no,
                        "step_desc": step.description,
                        "expected_output": step.expected_output,
                        "iteration": iteration,
                        "task_id": task_id,
                    }
                    success, output = self._dispatcher(tag, task_dict)
                else:
                    logger.warning(
                        "HarnessRunner: ステップ%dにエージェントタグなし — スキップ", step.step_no
                    )
                    success, output = False, "エージェントタグが未割り当てのためスキップ"

                sr = StepResult(
                    step_no=step.step_no,
                    agent_tag=tag,
                    raw_output=output,
                    success=success,
                    error_msg="" if success else output,
                )
                step_results.append(sr)
                if pf:
                    pf.add_step_result(
                        step_no=step.step_no,
                        success=success,
                        output=output,
                        agent_tag=tag,
                    )

            # ── Evaluator ─────────────────────────────────────
            status = HarnessStatus.EVALUATING
            if pf:
                pf.set_phase("evaluating")
            evaluation = self._evaluator.evaluate(plan, step_results)
            if pf:
                pf.set_evaluation(
                    score=evaluation.score,
                    summary=evaluation.summary,
                    passed=evaluation.passed,
                )

            if evaluation.passed:
                logger.info(
                    "HarnessRunner: 評価合格 [%s] score=%.2f iteration=%d",
                    task_id, evaluation.score, iteration,
                )
                status = HarnessStatus.DONE
                break

            logger.info(
                "HarnessRunner: 評価不合格 [%s] score=%.2f → 再計画",
                task_id, evaluation.score,
            )
            status = HarnessStatus.REPLANNING

        else:
            # max_iterations を超えた
            logger.error("HarnessRunner: 最大イテレーション超過 [%s]", task_id)
            status = HarnessStatus.FAILED

        # 最終出力サマリーを組み立て
        final_output = self._build_final_output(plan, step_results, evaluation, status)

        # Progress File を最終更新
        if pf:
            if status == HarnessStatus.DONE:
                pf.complete(final_output)
            else:
                pf.fail(reason=f"status={status.value}")

        # Phase 6: Reflect-Memorize（実行結果から記憶を自動更新）
        harness_result_tmp = HarnessResult(
            task_id=task_id, status=status, plan=plan,
            step_results=step_results, evaluation=evaluation,
            iterations=iteration if status != HarnessStatus.FAILED else self._max_iterations,
            final_output=final_output,
        )
        self._memory.reflect_from_harness_result(harness_result_tmp)

        return HarnessResult(
            task_id=task_id,
            status=status,
            plan=plan,
            step_results=step_results,
            evaluation=evaluation,
            iterations=iteration if status != HarnessStatus.FAILED else self._max_iterations,
            final_output=final_output,
        )

    # ── プライベートヘルパー ───────────────────────────────────

    @staticmethod
    def _noop_dispatcher(tag: str, task: dict) -> tuple[bool, str]:
        """ディスパッチャー未設定時のフォールバック（ドライラン用）"""
        logger.info("noop_dispatcher: tag=%s desc=%s", tag, task.get("description", "")[:50])
        return True, f"[noop] {tag}: {task.get('description', '')}"

    @staticmethod
    def _build_final_output(plan, step_results, evaluation, status) -> str:
        lines = []
        if plan:
            lines.append(f"目標: {plan.goal}")
            lines.append(f"ステップ数: {len(plan.steps)}")
        lines.append(f"ステータス: {status.value}")
        if evaluation:
            lines.append(f"評価スコア: {evaluation.score:.2f}")
            lines.append(f"評価: {evaluation.summary}")
            if evaluation.issues:
                lines.append("問題点: " + ", ".join(evaluation.issues[:2]))
        success_count = sum(1 for r in step_results if r.success)
        lines.append(f"完了ステップ: {success_count}/{len(step_results)}")
        return "\n".join(lines)
