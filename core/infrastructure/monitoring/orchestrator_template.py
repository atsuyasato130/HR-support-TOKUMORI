"""
Orchestrator — マルチエージェント・ワークフロー雛形
タスク分解AI → 実行AI群 → 検証AI の3層プロンプトチェーン
"""
import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any

import anthropic

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CLIENT = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
MODEL = "claude-opus-4-6"


# =================================================================
# データ構造
# =================================================================
@dataclass
class SubTask:
    id: str
    agent_name: str
    description: str
    input_data: dict
    dependencies: list[str] = field(default_factory=list)


@dataclass
class ExecutionResult:
    sub_task_id: str
    agent_name: str
    output: Any
    success: bool
    error: str = ""
    hours_saved: float = 0.0


@dataclass
class OrchestratorResult:
    original_request: str
    sub_tasks: list[SubTask]
    results: list[ExecutionResult]
    verification_passed: bool
    final_output: str
    total_hours_saved: float


# =================================================================
# Layer 1: タスク分解AI
# =================================================================
def decompose_task(user_request: str, available_agents: list[str]) -> list[SubTask]:
    """
    単一の依頼を複数のサブタスクに分解する。
    どのエージェントに何を依頼するかを決定する。
    """
    system_prompt = """あなたはタスク分解の専門AIです。
ユーザーの依頼を分析し、利用可能なエージェントへの具体的なサブタスクに分解してください。

## 出力形式（必ずJSONで返す）
{
  "analysis": "依頼の意図と複雑度の分析",
  "sub_tasks": [
    {
      "id": "task_001",
      "agent_name": "エージェント名",
      "description": "このエージェントへの具体的な指示",
      "input_data": {"key": "value"},
      "dependencies": []
    }
  ],
  "estimated_hours_saved": 数値
}

## 分解ルール
1. 独立して実行できるタスクは並列に配置する（dependenciesを空に）
2. 前のタスクの出力を必要とするタスクはdependenciesにIDを記載
3. 各タスクは単一のエージェントが担当できる粒度にする
4. 削減時間は現状の手動作業と比較して算出する"""

    user_prompt = f"""
## 依頼内容
{user_request}

## 利用可能なエージェント
{json.dumps(available_agents, ensure_ascii=False)}

上記の依頼をサブタスクに分解してください。
"""

    response = CLIENT.messages.create(
        model=MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": user_prompt}],
        system=system_prompt,
    )

    raw = response.content[0].text
    # JSON部分を抽出
    start = raw.find("{")
    end = raw.rfind("}") + 1
    data = json.loads(raw[start:end])

    logger.info(f"[Decomposer] 分析: {data['analysis']}")
    logger.info(f"[Decomposer] サブタスク数: {len(data['sub_tasks'])}")

    return [
        SubTask(
            id=t["id"],
            agent_name=t["agent_name"],
            description=t["description"],
            input_data=t.get("input_data", {}),
            dependencies=t.get("dependencies", []),
        )
        for t in data["sub_tasks"]
    ]


# =================================================================
# Layer 2: 実行AI（エージェントルーター）
# =================================================================
def execute_sub_task(sub_task: SubTask, context: dict) -> ExecutionResult:
    """
    サブタスクを担当エージェントに委譲して実行する。
    contextには前のタスクの出力が入る。
    """
    system_prompt = f"""あなたは「{sub_task.agent_name}」として動作するAIです。
与えられたタスクを正確に実行し、構造化された結果を返してください。

## 出力形式（必ずJSONで返す）
{{
  "success": true/false,
  "output": {{実行結果}},
  "summary": "何を実行したかの日本語サマリー",
  "hours_saved": 削減した時間（数値）,
  "error": "エラーがある場合のみ"
}}"""

    user_prompt = f"""
## タスク
{sub_task.description}

## 入力データ
{json.dumps(sub_task.input_data, ensure_ascii=False, indent=2)}

## 前タスクの結果（コンテキスト）
{json.dumps(context, ensure_ascii=False, indent=2) if context else "なし"}

タスクを実行してください。
"""

    try:
        response = CLIENT.messages.create(
            model=MODEL,
            max_tokens=3000,
            messages=[{"role": "user", "content": user_prompt}],
            system=system_prompt,
        )
        raw = response.content[0].text
        start = raw.find("{")
        end = raw.rfind("}") + 1
        data = json.loads(raw[start:end])

        logger.info(f"[Executor:{sub_task.agent_name}] {data.get('summary', '')}")
        return ExecutionResult(
            sub_task_id=sub_task.id,
            agent_name=sub_task.agent_name,
            output=data.get("output", {}),
            success=data.get("success", False),
            error=data.get("error", ""),
            hours_saved=float(data.get("hours_saved", 0)),
        )

    except Exception as e:
        logger.error(f"[Executor:{sub_task.agent_name}] エラー: {e}")
        return ExecutionResult(
            sub_task_id=sub_task.id,
            agent_name=sub_task.agent_name,
            output=None,
            success=False,
            error=str(e),
        )


# =================================================================
# Layer 3: 検証AI
# =================================================================
def verify_results(
    original_request: str,
    sub_tasks: list[SubTask],
    results: list[ExecutionResult],
) -> tuple[bool, str]:
    """
    全実行結果を検証し、品質チェックと最終サマリーを生成する。
    """
    system_prompt = """あなたは品質検証AIです。
各エージェントの実行結果を評価し、以下を判断してください:
1. 元の依頼が完全に満たされているか
2. 各結果に矛盾や抜け漏れがないか
3. ユーザーに提示すべき最終サマリーの作成

## 出力形式（必ずJSONで返す）
{
  "passed": true/false,
  "issues": ["問題点があれば列挙"],
  "final_summary": "ユーザー向けの最終回答（日本語）",
  "quality_score": 0-100
}"""

    results_summary = [
        {
            "agent": r.agent_name,
            "success": r.success,
            "output_summary": str(r.output)[:200] if r.output else None,
            "error": r.error,
        }
        for r in results
    ]

    user_prompt = f"""
## 元の依頼
{original_request}

## 実行されたサブタスク
{json.dumps([{"id": t.id, "agent": t.agent_name, "task": t.description} for t in sub_tasks], ensure_ascii=False, indent=2)}

## 実行結果
{json.dumps(results_summary, ensure_ascii=False, indent=2)}

検証してください。
"""

    response = CLIENT.messages.create(
        model=MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": user_prompt}],
        system=system_prompt,
    )
    raw = response.content[0].text
    start = raw.find("{")
    end = raw.rfind("}") + 1
    data = json.loads(raw[start:end])

    logger.info(f"[Verifier] 品質スコア: {data.get('quality_score')}")
    if data.get("issues"):
        logger.warning(f"[Verifier] 問題点: {data['issues']}")

    return data.get("passed", False), data.get("final_summary", "")


# =================================================================
# MAIN: オーケストレーター本体
# =================================================================
def run_orchestrator(user_request: str, available_agents: list[str] | None = None) -> OrchestratorResult:
    """
    エントリーポイント: 依頼を受けてフルパイプラインを実行する。
    """
    if available_agents is None:
        available_agents = [
            "Career Advisor", "Interview Master", "Post Interview Support",
            "Notion Agent", "Salesforce Agent", "LINE Agent", "Slack Agent",
            "Google Agent", "Report Agent", "Coaching Agent", "TLDV Agent",
        ]

    logger.info(f"[Orchestrator] 開始: {user_request[:80]}")

    # ── Layer 1: 分解 ─────────────────────────────────────────
    sub_tasks = decompose_task(user_request, available_agents)

    # ── Layer 2: 実行（依存関係を考慮して順次/並列） ──────────
    results: list[ExecutionResult] = []
    context: dict = {}  # 完了タスクの出力を蓄積

    # 依存なしタスクと依存ありタスクを分離
    independent = [t for t in sub_tasks if not t.dependencies]
    dependent   = [t for t in sub_tasks if t.dependencies]

    # 独立タスクを実行（実際の並列化はthreadpoolで実装可）
    for task in independent:
        result = execute_sub_task(task, context)
        results.append(result)
        if result.success:
            context[task.id] = result.output

    # 依存タスクを順次実行
    for task in dependent:
        dep_context = {dep_id: context.get(dep_id) for dep_id in task.dependencies}
        result = execute_sub_task(task, dep_context)
        results.append(result)
        if result.success:
            context[task.id] = result.output

    # ── Layer 3: 検証 ─────────────────────────────────────────
    passed, final_output = verify_results(user_request, sub_tasks, results)

    total_hours = sum(r.hours_saved for r in results)
    logger.info(f"[Orchestrator] 完了 | 検証: {'PASS' if passed else 'FAIL'} | 削減時間: {total_hours:.1f}h")

    return OrchestratorResult(
        original_request=user_request,
        sub_tasks=sub_tasks,
        results=results,
        verification_passed=passed,
        final_output=final_output,
        total_hours_saved=total_hours,
    )


# =================================================================
# CLI テスト実行
# =================================================================
if __name__ == "__main__":
    test_request = """
    今日の面接（山田太郎さん、エンジニア職）が終わりました。
    TLDVの議事録から評価シートをSFに登録して、
    候補者にお礼メール（LINE）を送り、
    Notionの議事録DBにも記録してください。
    """

    result = run_orchestrator(test_request)

    print("\n" + "=" * 60)
    print("ORCHESTRATOR RESULT")
    print("=" * 60)
    print(f"検証: {'PASS ✓' if result.verification_passed else 'FAIL ✗'}")
    print(f"削減時間: {result.total_hours_saved:.1f}h")
    print(f"\n最終回答:\n{result.final_output}")
