"""
core/harness/memory — MUSE Memory システム（Phase 6）

Plan-Execute-Reflect-Memorize ループの記憶層。
3種類の記憶を分離管理し、エージェントの自己改善を支援する。

使い方:
    from core.harness.memory import MemoryStore

    mem = MemoryStore()
    # 記憶を追加
    mem.strategic.add("SF-Schema タスクは必ず dry-run を先に実行する")
    mem.procedural.add("SF-UI", "FlexiPageの変更前にバックアップJSONを保存する")
    mem.tool_usage.add("SF-Schema", success=True, duration_sec=45.2)

    # 記憶を検索（Plannerへのコンテキスト注入用）
    context = mem.get_context_for_task("Salesforceにフィールドを追加する")
"""

from .store import MemoryStore
from .strategic import StrategicMemory
from .procedural import ProceduralMemory
from .tool_usage import ToolUsageMemory

__all__ = ["MemoryStore", "StrategicMemory", "ProceduralMemory", "ToolUsageMemory"]
