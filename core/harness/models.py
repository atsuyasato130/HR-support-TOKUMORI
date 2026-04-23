#!/usr/bin/env python3
"""
harness/models.py — エージェントハーネスのデータモデル

Planner・Generator・Evaluator 間で受け渡すデータクラスを定義する。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class HarnessStatus(str, Enum):
    PENDING    = "pending"
    PLANNING   = "planning"
    RUNNING    = "running"
    EVALUATING = "evaluating"
    DONE       = "done"
    FAILED     = "failed"
    REPLANNING = "replanning"


@dataclass
class ExecutionStep:
    """Planner が生成する単一実行ステップ"""
    step_no: int
    description: str
    agent_tag: Optional[str] = None    # 対応エージェントタグ（例: "SF-Schema"）
    context: Dict[str, Any] = field(default_factory=dict)
    expected_output: str = ""


@dataclass
class HarnessPlan:
    """Planner の出力: タスクを分解した実行計画"""
    task_id: str
    original_description: str
    goal: str
    steps: List[ExecutionStep] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "original_description": self.original_description,
            "goal": self.goal,
            "steps": [
                {
                    "step_no": s.step_no,
                    "description": s.description,
                    "agent_tag": s.agent_tag,
                    "context": s.context,
                    "expected_output": s.expected_output,
                }
                for s in self.steps
            ],
            "created_at": self.created_at,
        }


@dataclass
class StepResult:
    """各ステップの実行結果"""
    step_no: int
    agent_tag: Optional[str]
    raw_output: str
    success: bool
    error_msg: str = ""
    executed_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class EvaluationReport:
    """Evaluator の出力: 全ステップ結果の品質評価"""
    task_id: str
    score: float           # 0.0〜1.0
    passed: bool           # score >= threshold で True
    summary: str           # 評価サマリー
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    evaluated_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class HarnessResult:
    """HarnessRunner の最終出力"""
    task_id: str
    status: HarnessStatus
    plan: Optional[HarnessPlan]
    step_results: List[StepResult] = field(default_factory=list)
    evaluation: Optional[EvaluationReport] = None
    iterations: int = 1
    final_output: str = ""
    completed_at: str = field(default_factory=lambda: datetime.now().isoformat())
