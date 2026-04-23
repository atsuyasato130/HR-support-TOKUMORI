"""
core/harness — Tokumori エージェントハーネス

Planner → Generator → Evaluator ループで既存エージェントを包み込み、
自律的な再計画・品質保証を実現する。

使い方:
    from core.harness import HarnessRunner

    def my_dispatcher(tag: str, task: dict) -> tuple[bool, str]:
        # 既存の dispatch_task() を呼び出す
        ...

    runner = HarnessRunner(dispatcher=my_dispatcher)
    result = runner.run("pipeline__c に内定承諾日フィールドを追加して")

    print(result.status)       # HarnessStatus.DONE
    print(result.evaluation.score)  # 0.92
"""

from .evaluator import Evaluator
from .initializer import Initializer, InitializerOutput
from .memory import MemoryStore
from .progress_file import ProgressFile
from .quality_evaluator import QualityEvaluator
from .models import (
    EvaluationReport,
    ExecutionStep,
    HarnessPlan,
    HarnessResult,
    HarnessStatus,
    StepResult,
)
from .planner import Planner
from .runner import HarnessRunner

__all__ = [
    "HarnessRunner",
    "Planner",
    "Evaluator",
    "QualityEvaluator",
    "Initializer",
    "InitializerOutput",
    "MemoryStore",
    "ProgressFile",
    "HarnessPlan",
    "HarnessResult",
    "HarnessStatus",
    "EvaluationReport",
    "ExecutionStep",
    "StepResult",
]
