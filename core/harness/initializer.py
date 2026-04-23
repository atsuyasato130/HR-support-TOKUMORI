#!/usr/bin/env python3
"""
harness/initializer.py — Initializer エージェント（Phase 4）

【役割】
  Plannerの前段に置き、1〜4文の曖昧な指示を構造化された要件リストに展開する。
  Anthropicの研究で最も効果が大きかったコンポーネント。

  「Salesforceに内定承諾日フィールドを追加して」（1文）
      ↓ Initializer
  - [ ] pipeline__c オブジェクトに InternalAcceptDate__c (Date型) フィールドを追加
  - [ ] フィールドラベルは「内定承諾日」
  - [ ] 求職者ページのレイアウトに追加
  - [ ] FlexiPageに表示列として追加
  - [ ] 完了後にSlackで完了通知
  ↓ Planner へ

【設計原則（Anthropic論文より）】
  - すべての要件を最初は "failing" 状態でマーク
  - Generatorが1つずつ done に更新
  - Evaluatorはfailing残数でスコアを補正できる
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

import anthropic

logger = logging.getLogger("harness.initializer")


@dataclass
class Requirement:
    """単一の要件定義。failing → done へ状態遷移する。"""
    req_id: str
    description: str
    status: str = "failing"      # "failing" | "done" | "skipped"
    agent_hint: Optional[str] = None  # 対応エージェントタグのヒント
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def mark_done(self) -> None:
        self.status = "done"
        self.updated_at = datetime.now().isoformat()

    def mark_skipped(self) -> None:
        self.status = "skipped"
        self.updated_at = datetime.now().isoformat()

    @property
    def is_failing(self) -> bool:
        return self.status == "failing"


@dataclass
class InitializerOutput:
    """Initializer の出力：要件リストとタスク目標。"""
    task_id: str
    original_prompt: str
    goal: str
    requirements: List[Requirement] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def failing_count(self) -> int:
        return sum(1 for r in self.requirements if r.is_failing)

    @property
    def done_count(self) -> int:
        return sum(1 for r in self.requirements if r.status == "done")

    @property
    def completion_rate(self) -> float:
        total = len(self.requirements)
        return self.done_count / total if total else 0.0

    def to_markdown(self) -> str:
        """Plannerへ渡すMarkdown形式の要件リスト。"""
        lines = [
            f"# タスク要件リスト",
            f"**目標:** {self.goal}",
            f"**要件数:** {len(self.requirements)} ({self.failing_count} failing / {self.done_count} done)",
            "",
            "## 要件",
        ]
        for r in self.requirements:
            icon = "[ ]" if r.is_failing else ("[x]" if r.status == "done" else "[-]")
            hint = f" `{r.agent_hint}`" if r.agent_hint else ""
            lines.append(f"- {icon} {r.description}{hint}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "original_prompt": self.original_prompt,
            "goal": self.goal,
            "requirements": [
                {"req_id": r.req_id, "description": r.description,
                 "status": r.status, "agent_hint": r.agent_hint}
                for r in self.requirements
            ],
            "created_at": self.created_at,
        }


_SYSTEM_PROMPT = """あなたはTokumoriのタスク初期化エージェントです。
与えられた曖昧なタスク指示を、実行可能な具体的要件リストに展開します。

ルール:
1. 1〜4文の指示を5〜15個の具体的要件に分解する
2. 各要件は「何を・どのオブジェクト/ファイル/ツールに・どう変更するか」を明記
3. 要件間の依存関係を考慮して順序付けする
4. 各要件に最適なエージェントタグをヒントとして付与する

利用可能なエージェントタグ:
SF-Schema, SF-UI, SF-Data, SF-Patrol, SF-Register,
Slack, Email, Line, Slide, Schedule, TLDV, Notion, Doc, Log

出力形式（JSONのみ、前置き不要）:
{
  "goal": "このタスクの達成目標（1文）",
  "requirements": [
    {
      "description": "具体的な要件の説明",
      "agent_hint": "SF-Schema"
    }
  ]
}

要件は具体的かつ独立したアクションとして記述すること。
「〇〇の準備をする」のような曖昧な要件は禁止。"""


class Initializer:
    """
    曖昧な指示を構造化された要件リストに展開するエージェント。

    Usage:
        init = Initializer()
        output = init.initialize("内定承諾日フィールドをSFに追加して")
        print(output.to_markdown())  # Plannerに渡す
    """

    def __init__(self, model: str = "claude-haiku-4-5-20251001") -> None:
        self._client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        self._model = model

    def initialize(
        self,
        prompt: str,
        task_id: Optional[str] = None,
    ) -> InitializerOutput:
        """
        曖昧な指示を要件リストに展開する。

        Args:
            prompt:  ユーザーの自然言語指示
            task_id: タスクID（省略時は自動生成）

        Returns:
            InitializerOutput（要件リスト付き）
        """
        task_id = task_id or str(uuid.uuid4())[:8]
        logger.info("Initializer: 要件展開開始 [%s] %s", task_id, prompt[:60])

        try:
            resp = self._client.messages.create(
                model=self._model,
                max_tokens=1200,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = resp.content[0].text.strip()
            start, end = raw.find("{"), raw.rfind("}") + 1
            data = json.loads(raw[start:end]) if start >= 0 and end > start else {}
        except Exception as exc:
            logger.warning("Initializer: LLM失敗 → 1要件フォールバック: %s", exc)
            data = {}

        goal = data.get("goal") or prompt[:80]
        raw_reqs = data.get("requirements") or [{"description": prompt, "agent_hint": None}]

        requirements = [
            Requirement(
                req_id=f"{task_id}-{i+1:02d}",
                description=r.get("description", ""),
                agent_hint=r.get("agent_hint"),
            )
            for i, r in enumerate(raw_reqs)
        ]

        output = InitializerOutput(
            task_id=task_id,
            original_prompt=prompt,
            goal=goal,
            requirements=requirements,
        )
        logger.info(
            "Initializer: 要件展開完了 [%s] %d要件 goal=%s",
            task_id, len(requirements), goal[:40],
        )
        return output
