#!/usr/bin/env python3
"""
harness/planner.py — Planner エージェント

タスク記述を受け取り、実行計画（HarnessPlan）に分解する。
Claude を使って自然言語タスクを構造化ステップに変換する。
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Optional

import anthropic

from .models import ExecutionStep, HarnessPlan

logger = logging.getLogger("harness.planner")

# ── ツールレベルタグ（orchestrator.py の _TAG_TO_AGENT と対応） ──────────────
_TOOL_TAGS = [
    "SF-Schema",    # Salesforce フィールド・スキーマ変更
    "SF-UI",        # Salesforce FlexiPage・レイアウト変更
    "SF-Data",      # Salesforce CRUD・一括処理
    "SF-Patrol",    # Salesforce 巡回・データ品質チェック
    "SF-Register",  # Salesforce 面談登録（auto_sf_register）
    "Slack",        # Slack 通知・投稿
    "Email",        # Gmail 送受信・パイプライン
    "Line",         # LINE 送信
    "Doc",          # Notion / Google Docs / Sheets（MCP経由）
    "Slide",        # Google Slides 生成
    "Schedule",     # 面談日程調整・スケジュール登録
    "TLDV",         # tl;dv 文字起こし解析
    "Notion",       # Notion ページ解析
    "Log",          # Update_Log 記録
]

# ── 部門レベルタグ（empire_os.py の DEPARTMENTS と対応） ─────────────────────
_DEPT_TAGS = [
    "hr_support",   # HRサポート: 学生対応・面接・SF登録・LINE通知
    "sales",        # Sales: リード育成・提案書・商談管理
    "rpo",          # RPO: 採用KPI報告・定例報告
    "hr_dept",      # 人事部門: 自社採用・求人票管理
    "management",   # 経営管理: 経理・請求書・法務
    "quality",      # 品質管理: コードレビュー・自動改善
]

# Planner が参照するタグ一覧（ツール + 部門）
_KNOWN_TAGS = _TOOL_TAGS + _DEPT_TAGS

_SYSTEM_PROMPT = """あなたはTokumoriのタスクプランナーです。
与えられたタスクを実行可能なステップに分解し、各ステップに最適なタグを割り当てます。

【ツールレベルタグ（具体的な操作）】
- SF-Schema   : Salesforceフィールド・スキーマ追加・変更
- SF-UI       : SalesforceレイアウトFlexiPage変更
- SF-Data     : Salesforce CRUD・一括処理
- SF-Patrol   : Salesforce巡回・データ品質チェック
- SF-Register : Salesforce面談登録（auto_sf）
- Slack       : Slack通知・投稿
- Email       : Gmail送受信・パイプライン
- Line        : LINE送信
- Slide       : Google Slides生成
- Schedule    : 面談日程調整・スケジュール登録
- TLDV        : tl;dv文字起こし解析
- Notion      : Notionページ解析・議事録
- Doc         : Google Docs・Sheets操作
- Log         : Update_Log記録

【部門レベルタグ（複合業務）】
- hr_support  : HRサポート全般（学生対応・面接・SF登録・LINE通知）
- sales       : Sales業務（リード育成・提案書・商談管理）
- rpo         : RPO業務（採用KPI報告・定例報告）
- hr_dept     : 人事部門（自社採用・求人票）
- management  : 経営管理（経理・請求書・法務）
- quality     : 品質管理（コードレビュー・自動改善）

出力形式（JSONのみ、前置き不要）:
{
  "goal": "このタスクの達成目標（1文）",
  "steps": [
    {
      "step_no": 1,
      "description": "ステップの説明",
      "agent_tag": "SF-Schema",
      "expected_output": "期待される出力"
    }
  ]
}

ステップは最大5つまで。シンプルなタスクは1〜2ステップで十分。
単一の複合業務なら部門タグを使い1ステップにまとめてよい。
タグが不明な場合は agent_tag を null にしてください。"""


class Planner:
    """
    タスク記述を HarnessPlan に変換するプランナー。

    Usage:
        planner = Planner()
        plan = planner.plan("pipeline__c に内定承諾日フィールドを追加して")
    """

    def __init__(self, model: str = "claude-haiku-4-5-20251001") -> None:
        self._client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        self._model = model  # Plannerは軽量モデルで十分

    def plan(
        self,
        description: str,
        task_id: Optional[str] = None,
    ) -> HarnessPlan:
        """
        タスク記述を実行計画に変換する。

        Args:
            description: タスクの自然言語記述
            task_id:     タスクID（省略時は自動生成）

        Returns:
            HarnessPlan
        """
        task_id = task_id or str(uuid.uuid4())[:8]
        logger.info("Planner: タスク計画開始 [%s] %s", task_id, description[:60])

        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=800,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": description}],
            )
            raw = response.content[0].text.strip()
            start = raw.find("{")
            end = raw.rfind("}") + 1
            data = json.loads(raw[start:end]) if start >= 0 and end > start else {}
        except Exception as exc:
            logger.warning("Planner: LLM呼び出し失敗 → フォールバック計画を生成: %s", exc)
            data = {}

        goal = data.get("goal") or description[:80]
        raw_steps = data.get("steps") or [{"step_no": 1, "description": description, "agent_tag": None, "expected_output": ""}]

        steps = [
            ExecutionStep(
                step_no=s.get("step_no", i + 1),
                description=s.get("description", ""),
                agent_tag=s.get("agent_tag"),
                expected_output=s.get("expected_output", ""),
            )
            for i, s in enumerate(raw_steps)
        ]

        plan = HarnessPlan(
            task_id=task_id,
            original_description=description,
            goal=goal,
            steps=steps,
        )
        logger.info(
            "Planner: 計画完了 [%s] goal=%s steps=%d",
            task_id, goal[:40], len(steps),
        )
        return plan
