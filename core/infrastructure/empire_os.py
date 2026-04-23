#!/usr/bin/env python3
"""
Tokumori OS — 統合オペレーティングシステム（Phase 3: フル統合）

全部門オーケストレーターと進化サイクルを単一エントリポイントから統括する。

アーキテクチャ:
    empire_os.py
    ├── dispatch  → 自然言語タスクを部門自動判定して委譲 [Phase 3 新機能]
    ├── catchup   → user_requests.md の未処理依頼を自動消化 [Phase 3 新機能]
    ├── HRSupport → agents/hr_support/main.py
    ├── Sales     → agents/sales/orchestrator.py
    ├── RPO       → agents/_experimental/rpo/orchestrator.py       [experimental]
    ├── HRDept    → agents/_experimental/hr_dept/orchestrator.py    [experimental]
    ├── Management→ agents/_experimental/management/orchestrator.py [experimental]
    └── Evolution → scripts/evolution_cycle.py（週次自律進化）

使い方:
    python3 core/infrastructure/empire_os.py status              # 全部門の状態確認
    python3 core/infrastructure/empire_os.py dispatch "タスク"   # 自然言語で部門自動判定
    python3 core/infrastructure/empire_os.py catchup             # user_requests.md を処理
    python3 core/infrastructure/empire_os.py evolve              # 進化サイクル実行
    python3 core/infrastructure/empire_os.py run hr_support      # 部門ポータル起動
    python3 core/infrastructure/empire_os.py list                # 部門一覧
"""
from __future__ import annotations

import importlib.util
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# ─── パス設定 ─────────────────────────────────────────────────────────────────
AI_EMPIRE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(AI_EMPIRE))

from dotenv import load_dotenv
load_dotenv(AI_EMPIRE / "config" / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("EmpireOS")

OS_LOG = AI_EMPIRE / "logs" / "empire_os"
USER_REQUESTS_FILE = AI_EMPIRE / "user_requests.md"
DISPATCH_LOG = AI_EMPIRE / "logs" / "dispatch_log.jsonl"


# ─── データ構造 ───────────────────────────────────────────────────────────────

@dataclass
class DeptStatus:
    key: str
    name: str
    status: str          # "active" | "dev" | "error"
    agent_count: int = 0
    last_run: str = ""
    error: str = ""
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class OSReport:
    generated_at: str
    departments: list[DeptStatus]
    evolution: dict[str, Any] = field(default_factory=dict)


@dataclass
class DispatchResult:
    task: str
    dept_key: str
    dept_name: str
    result: str
    success: bool
    duration_sec: float
    routed_by: str = "claude"     # "claude" | "keyword" | "fallback"


# ─── 部門定義 ─────────────────────────────────────────────────────────────────

DEPARTMENTS = {
    "hr_support": {
        "name": "HRサポート",
        "emoji": "👥",
        "entry": AI_EMPIRE / "agents" / "hr_support" / "main.py",
        "orchestrator": None,
        "status": "active",
        "description": "学生対応・面接対策・ES添削・SF登録・Notion記録・LINE通知などHR業務全般",
        "keywords": ["学生", "面接", "es", "sf登録", "notion", "line", "tldv", "議事録",
                     "コーチング", "就活", "採用支援", "候補者", "選考"],
    },
    "sales": {
        "name": "Sales",
        "emoji": "💼",
        "entry": AI_EMPIRE / "agents" / "sales" / "orchestrator.py",
        "orchestrator": "SalesOrchestrator",
        "status": "dev",
        "description": "リード育成・アポイント・提案書・商談・契約フォローなどSales業務",
        "keywords": ["リード", "アポ", "提案書", "商談", "契約", "営業", "案件", "クロージング"],
    },
    "rpo": {
        "name": "RPO",
        "emoji": "🔍",
        "entry": AI_EMPIRE / "agents" / "_experimental" / "rpo" / "orchestrator.py",
        "orchestrator": "RpoOrchestrator",
        "status": "experimental",
        "description": "RPOクライアントへの採用KPI報告・定例報告・課題提案など",
        "keywords": ["rpo", "クライアント", "採用kpi", "定例", "報告書", "採用支援業務"],
    },
    "hr_dept": {
        "name": "人事部門",
        "emoji": "🏢",
        "entry": AI_EMPIRE / "agents" / "_experimental" / "hr_dept" / "orchestrator.py",
        "orchestrator": "HrDeptOrchestrator",
        "status": "experimental",
        "description": "自社の正社員・業務委託・インターン採用プロセス管理",
        "keywords": ["社員採用", "求人票", "業務委託", "フリーランス", "インターン", "自社採用", "内定"],
    },
    "management": {
        "name": "経営管理",
        "emoji": "📊",
        "entry": AI_EMPIRE / "agents" / "_experimental" / "management" / "orchestrator.py",
        "orchestrator": "MgmtOrchestrator",
        "status": "experimental",
        "description": "経理・P&L・請求書・法務・契約書・経営戦略・KPI管理",
        "keywords": ["請求書", "経理", "pl", "p&l", "法務", "契約書", "経営", "kpi", "戦略", "月次"],
    },
    "quality": {
        "name": "品質管理",
        "emoji": "🔬",
        "entry": AI_EMPIRE / "scripts" / "evolution_cycle.py",
        "orchestrator": None,
        "status": "active",
        "description": "コードレビュー・自動改善・セキュリティスキャン・カタログ更新",
        "keywords": ["コードレビュー", "品質", "セキュリティ", "改善", "進化サイクル"],
    },
}


# ─── ユーティリティ ───────────────────────────────────────────────────────────

def _load_module(path: Path, mod_name: str):
    """指定パスのPythonファイルを動的ロードして返す。"""
    spec = importlib.util.spec_from_file_location(mod_name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


def _get_claude_client():
    """Anthropic クライアントを返す（遅延初期化）。"""
    import anthropic
    return anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


def _read_registry() -> list[dict]:
    registry_path = AI_EMPIRE / "agents" / "_registry" / "registry.json"
    try:
        with open(registry_path, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("agents", [])
    except Exception as e:
        logger.warning(f"レジストリ読み込み失敗: {e}")
        return []


def _read_evolution_log() -> dict:
    log_dir = AI_EMPIRE / "logs" / "evolution_cycles"
    if not log_dir.exists():
        return {}
    logs = sorted(log_dir.glob("cycle_*.json"), reverse=True)
    if not logs:
        return {}
    try:
        with open(logs[0], encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _log_dispatch(result: DispatchResult) -> None:
    """ディスパッチ結果を JSONL ログに追記する。"""
    DISPATCH_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now().isoformat(),
        "task": result.task[:100],
        "dept_key": result.dept_key,
        "dept_name": result.dept_name,
        "success": result.success,
        "duration_sec": result.duration_sec,
        "routed_by": result.routed_by,
    }
    with open(DISPATCH_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _log_to_dashboard(summary: str, targets: str, details: str) -> None:
    """dashboard_logger に作業ログを記録する。"""
    try:
        from utils.dashboard_logger import log_update
        log_update(icon="🤖 自動", summary=summary, targets=targets, details=details)
    except Exception as e:
        logger.debug(f"dashboard_logger スキップ: {e}")


# ─── 部門自動判定（Phase 3 コア） ─────────────────────────────────────────────

def _route_by_keyword(task: str) -> str | None:
    """
    キーワードマッチで部門を高速判定する（APIコストゼロ）。
    明確にマッチした場合のみ返し、曖昧な場合は None を返す。
    """
    task_lower = task.lower()
    scores: dict[str, int] = {}
    for key, conf in DEPARTMENTS.items():
        count = sum(1 for kw in conf.get("keywords", []) if kw in task_lower)
        if count > 0:
            scores[key] = count
    if not scores:
        return None
    best_key = max(scores, key=lambda k: scores[k])
    # スコアが1以上かつ次点と差があれば採用
    sorted_scores = sorted(scores.values(), reverse=True)
    if len(sorted_scores) == 1 or sorted_scores[0] > sorted_scores[1]:
        return best_key
    return None


def _route_by_claude(task: str) -> str:
    """
    Claude で部門を判定する（キーワード判定が曖昧な場合）。
    """
    dept_list = "\n".join(
        f"- {key}: {conf['description']}"
        for key, conf in DEPARTMENTS.items()
    )
    res = _get_claude_client().messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=20,
        system=(
            f"以下のタスクを最も適切な部門に振り分けてください。\n"
            f"部門一覧:\n{dept_list}\n\n"
            f"出力: dept=<部門キー> のみ（例: dept=hr_support）"
        ),
        messages=[{"role": "user", "content": task}],
    )
    text = res.content[0].text.strip()
    for key in DEPARTMENTS:
        if f"dept={key}" in text:
            return key
    return "hr_support"  # fallback


def _dispatch_to_dept(
    dept_key: str,
    task: str,
    client_id: str | None = None,
    parallel: bool = False,
    max_workers: int = 4,
) -> str:
    """
    部門オーケストレーターにタスクを渡して実行する。

    Phase 7/8 追加パラメータ:
        client_id:   マルチテナント用クライアントID（hr_support のみ有効）
        parallel:    True の場合 Orchestrator を並列モードで起動
        max_workers: 並列ワーカー数
    """
    conf = DEPARTMENTS[dept_key]
    entry: Path = conf["entry"]
    cls_name = conf.get("orchestrator")

    if not entry.exists():
        return f"❌ エントリファイルが見つかりません: {entry.name}"

    if dept_key == "hr_support":
        # hr_support はタグ付きタスクを Orchestrator に渡す
        # client_id / parallel が指定されている場合は Orchestrator 経由で処理
        if client_id or parallel:
            try:
                orch_path = AI_EMPIRE / "agents" / "hr_support" / "agents" / "orchestrator.py"
                orch_mod = _load_module(orch_path, "hr_support_orchestrator")
                orch = orch_mod.Orchestrator(
                    client_id=client_id,
                    parallel=parallel,
                    max_workers=max_workers,
                )
                result = orch.run_once()
                return (
                    f"Orchestrator完了: {result.get('processed', 0)}件処理 "
                    f"(succeeded={result.get('succeeded', 0)} failed={result.get('failed', 0)})"
                )
            except Exception as exc:
                logger.warning(f"Orchestrator経由失敗 → Claude fallback: {exc}")

        # フォールバック: Claude でタスクを処理
        res = _get_claude_client().messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            system=(
                "あなたはHRサポート担当AIです。"
                "学生対応・面接対策・SF登録・Notion記録など採用支援業務を担当します。"
                "タスクを受け取り、何をすべきかを具体的に回答してください。"
            ),
            messages=[{"role": "user", "content": task}],
        )
        return res.content[0].text

    if dept_key == "quality":
        # quality は evolution_cycle — evolve コマンドに委譲
        result = cmd_evolve(dry_run=False)
        return f"進化サイクル完了: {'成功' if result.get('success') else '失敗'} ({result.get('steps_run', 0)}ステップ)"

    if cls_name:
        mod = _load_module(entry, f"dept_{dept_key}_dispatch")
        cls = getattr(mod, cls_name)
        orch = cls()
        return orch.run(task)

    return f"❌ {conf['name']} にオーケストレーターが定義されていません"


# ─── user_requests.md 処理（Phase 3 コア） ────────────────────────────────────

def _read_pending_requests() -> list[str]:
    """
    user_requests.md から未処理（- [ ]）の依頼を読み取る。
    ファイルが存在しない場合は空リストを返す。
    """
    if not USER_REQUESTS_FILE.exists():
        return []
    content = USER_REQUESTS_FILE.read_text(encoding="utf-8")
    pending = re.findall(r"^- \[ \] (.+)$", content, re.MULTILINE)
    return [p.strip() for p in pending]


def _mark_request_done(task: str) -> None:
    """user_requests.md の対象タスクを処理済み（- [x] ✅）にマークする。"""
    if not USER_REQUESTS_FILE.exists():
        return
    content = USER_REQUESTS_FILE.read_text(encoding="utf-8")
    # 完全一致で置換
    updated = content.replace(
        f"- [ ] {task}",
        f"- [x] \u2705 {task}",
    )
    USER_REQUESTS_FILE.write_text(updated, encoding="utf-8")


def _ensure_user_requests_file() -> None:
    """user_requests.md がなければテンプレートを作成する。"""
    if USER_REQUESTS_FILE.exists():
        return
    USER_REQUESTS_FILE.write_text(
        "# Tokumori — ユーザー依頼リスト\n\n"
        "<!-- [ ] のタスクが catchup コマンドで自動処理されます -->\n\n"
        "<!-- 記述例:\n"
        "- [ ] Notionの議事録をSlackに自動サマリーするエージェントが欲しい\n"
        "- [ ] 内定承諾率を上げるフォロー自動化エージェント\n"
        "-->\n",
        encoding="utf-8",
    )
    logger.info(f"user_requests.md を作成しました: {USER_REQUESTS_FILE}")


# ─── ハーネス統合ヘルパー ─────────────────────────────────────────────────────

def _get_harness_runner(client_id: str | None = None, parallel: bool = False, max_workers: int = 4):
    """
    HarnessRunner を生成して返す。
    dispatcher は dept_key OR ツールタグを解釈できる統合ディスパッチャー。

    Phase 7/8 追加:
        client_id:   ディスパッチャー内で ClientManager.context() に渡す
        parallel:    hr_support Orchestrator を並列モードで起動
        max_workers: 並列ワーカー数
    """
    try:
        from core.harness import HarnessRunner

        def _dispatcher(tag: str, task_dict: dict) -> tuple[bool, str]:
            """
            部門タグ（hr_support等）またはツールタグ（SF-Schema等）を受け取り実行する。
            Phase 7: client_id が指定されていれば ClientManager.context() でラップ。
            """
            description = task_dict.get("description", "")

            def _run():
                # 部門タグ → _dispatch_to_dept
                if tag in DEPARTMENTS:
                    try:
                        text = _dispatch_to_dept(
                            tag, description,
                            client_id=client_id,
                            parallel=parallel,
                            max_workers=max_workers,
                        )
                        return True, text
                    except Exception as exc:
                        return False, str(exc)

                # ツールタグ → subprocess 実行
                import subprocess as _sp
                import json as _json
                import tempfile
                workers_dir = AI_EMPIRE / "agents" / "hr_support" / "agents" / "workers"
                comm_dir    = AI_EMPIRE / "agents" / "hr_support" / "communication"
                messaging_dir = AI_EMPIRE / "agents" / "hr_support" / "agents" / "messaging"
                tools_dir   = AI_EMPIRE / "agents" / "hr_support" / "tools"
                scheduling_dir = AI_EMPIRE / "agents" / "hr_support" / "scheduling"
                tag_map: dict[str, Path | None] = {
                    "SF-Schema":    workers_dir / "sf_schema_agent.py",
                    "SF-UI":        workers_dir / "sf_ui_agent.py",
                    "SF-Data":      workers_dir / "sf_bulk_executor.py",
                    "SF-Patrol":    workers_dir / "sf_patrol_agent.py",
                    "Slack":        comm_dir / "slack_agent.py",
                    "Email":        comm_dir / "email_pipeline.py",
                    "Line":         messaging_dir / "line.py",
                    "Slide":        tools_dir / "slide_orchestrator.py",
                    "Schedule":     scheduling_dir / "interview_scheduler.py",
                    "SF-Register":  scheduling_dir / "auto_sf_register.py",
                    "TLDV":         workers_dir / "tldv_parser.py",
                    "Notion":       workers_dir / "notion_page_parser.py",
                }
                agent_path = tag_map.get(tag)
                if not agent_path or not agent_path.exists():
                    return False, f"ツールエージェント未実装: {tag}"

                tmp = Path(tempfile.mktemp(suffix=".json"))
                tmp.write_text(_json.dumps(task_dict, ensure_ascii=False), encoding="utf-8")
                try:
                    proc = _sp.run(
                        [sys.executable, str(agent_path), "--task", str(tmp)],
                        capture_output=True, text=True, timeout=300,
                    )
                    return proc.returncode == 0, (proc.stdout or proc.stderr or "")[:500]
                except Exception as exc:
                    return False, str(exc)

            # Phase 7: client_id があれば ClientManager.context() でラップ
            if client_id:
                try:
                    client_manager_path = (
                        AI_EMPIRE / "agents" / "hr_support" / "config" / "client_manager.py"
                    )
                    cm_mod = _load_module(client_manager_path, "client_manager")
                    with cm_mod.ClientManager.context(client_id):
                        return _run()
                except Exception as exc:
                    logger.warning(f"ClientManager contextラップ失敗: {exc} — 通常実行にフォールバック")

            return _run()

        return HarnessRunner(dispatcher=_dispatcher, max_iterations=3)
    except ImportError as exc:
        logger.warning(f"HarnessRunner import 失敗: {exc}")
        return None


# ─── コマンド実装 ─────────────────────────────────────────────────────────────

def cmd_dispatch(
    task: str,
    harness: bool = False,
    client_id: str | None = None,
    parallel: bool = False,
    max_workers: int = 4,
) -> DispatchResult:
    """
    自然言語タスクを受け取り、部門を自動判定して実行する（Phase 3 コア）。

    harness=True の場合、Planner→Generator→Evaluator ループ経由で実行する。
    client_id が指定された場合、クライアント別資格情報でオーバーレイして実行（Phase 7）。
    parallel=True の場合、複数タスクを ThreadPoolExecutor で同時実行（Phase 8）。

    1. キーワードマッチで高速判定（APIコストゼロ）
    2. 曖昧な場合は Claude で判定
    3. 対応オーケストレーターに委譲して実行（ハーネス有無で分岐）
    4. 結果をログに記録
    """
    flags = []
    if harness:
        flags.append("harness")
    if client_id:
        flags.append(f"client={client_id}")
    if parallel:
        flags.append(f"parallel(workers={max_workers})")
    flag_str = f"[{','.join(flags)}]" if flags else ""
    logger.info(f"=== dispatch{flag_str}: {task[:60]} ===")
    start = time.time()

    # ① キーワード判定
    dept_key = _route_by_keyword(task)
    routed_by = "keyword"

    # ② Claude 判定（キーワードで決まらない場合）
    if dept_key is None:
        dept_key = _route_by_claude(task)
        routed_by = "claude"

    conf = DEPARTMENTS[dept_key]
    logger.info(f"→ {conf['name']} [{dept_key}] (by {routed_by})")

    # ③ 実行
    if harness:
        runner = _get_harness_runner(
            client_id=client_id,
            parallel=parallel,
            max_workers=max_workers,
        )
        if runner:
            harness_result = runner.run(task, context={"dept_key": dept_key})
            result_text = harness_result.final_output
            success = harness_result.status.value == "done"
            routed_by = f"{routed_by}+harness"
            logger.info(
                f"ハーネス完了: status={harness_result.status.value} "
                f"score={harness_result.evaluation.score:.2f if harness_result.evaluation else '-'} "
                f"iterations={harness_result.iterations}"
            )
        else:
            # ハーネス初期化失敗 → 通常モードにフォールバック
            logger.warning("ハーネス初期化失敗 → 通常モードで実行")
            harness = False

    if not harness:
        try:
            result_text = _dispatch_to_dept(
                dept_key, task,
                client_id=client_id,
                parallel=parallel,
                max_workers=max_workers,
            )
            success = True
        except Exception as e:
            result_text = f"❌ 実行エラー: {e}"
            success = False
            logger.error(f"dispatch 実行エラー: {e}")

    duration = round(time.time() - start, 2)

    result = DispatchResult(
        task=task,
        dept_key=dept_key,
        dept_name=conf["name"],
        result=result_text,
        success=success,
        duration_sec=duration,
        routed_by=routed_by,
    )

    # ④ ログ記録
    _log_dispatch(result)

    return result


def cmd_catchup(
    harness: bool = False,
    client_id: str | None = None,
    parallel: bool = False,
    max_workers: int = 4,
) -> list[DispatchResult]:
    """
    user_requests.md の未処理依頼を全て自動ディスパッチする（Phase 3 コア）。

    harness=True の場合、各タスクをハーネスモードで処理する。
    client_id が指定された場合、クライアント別資格情報で実行（Phase 7）。
    parallel=True の場合、各タスクを並列ディスパッチ（Phase 8）。
    - [ ] 形式のタスクを読み取り → dispatch → - [x] ✅ に更新
    """
    _ensure_user_requests_file()
    pending = _read_pending_requests()

    if not pending:
        logger.info("catchup: 未処理の依頼はありません")
        print("✅ 未処理の依頼はありません。")
        print(f"   依頼追加: {USER_REQUESTS_FILE}")
        return []

    flags = []
    if harness:
        flags.append("harness")
    if client_id:
        flags.append(f"client={client_id}")
    if parallel:
        flags.append(f"parallel(workers={max_workers})")
    mode_label = f"[{','.join(flags)}]" if flags else ""
    logger.info(f"catchup{mode_label}: {len(pending)}件の依頼を処理します")
    print(f"\n{len(pending)}件の依頼を処理します{(' ' + mode_label) if mode_label else ''}...\n")

    results = []
    for i, task in enumerate(pending, 1):
        print(f"[{i}/{len(pending)}] {task[:60]}")
        result = cmd_dispatch(
            task,
            harness=harness,
            client_id=client_id,
            parallel=parallel,
            max_workers=max_workers,
        )
        results.append(result)
        _mark_request_done(task)

        status = "✅" if result.success else "❌"
        print(f"  {status} → {result.dept_name} ({result.duration_sec:.1f}s)")
        print(f"  {result.result[:120]}\n")

    # dashboard_logger に記録
    _log_to_dashboard(
        summary=f"user_requests catchup{mode_label}: {len(results)}件処理",
        targets="user_requests.md",
        details=" ".join(f"①{r.task[:30]}" for r in results[:3]),
    )

    return results


def cmd_status() -> OSReport:
    """全部門のステータスを収集してレポートを返す。"""
    logger.info("=== Tokumori OS — ステータス確認 ===")
    departments = []
    for key, conf in DEPARTMENTS.items():
        dept = _get_dept_status(key, conf)
        departments.append(dept)

    evolution = _read_evolution_log()

    # 未処理依頼数も取得
    _ensure_user_requests_file()
    pending_count = len(_read_pending_requests())

    report = OSReport(
        generated_at=datetime.now().isoformat(),
        departments=departments,
        evolution=evolution,
    )
    report.evolution["pending_requests"] = pending_count
    return report


def cmd_evolve(dry_run: bool = False, steps: list[str] | None = None) -> dict:
    """進化サイクル（evolution_cycle.py）を呼び出す。"""
    logger.info("=== Tokumori OS — 進化サイクル起動 ===")
    entry = DEPARTMENTS["quality"]["entry"]
    try:
        mod = _load_module(entry, "empire_evolution_cycle")
        result = mod.run(steps=steps, dry_run=dry_run, log_dashboard=not dry_run)
        logger.info(f"進化サイクル完了: {result}")
        return result
    except Exception as e:
        logger.error(f"進化サイクル失敗: {e}")
        return {"success": False, "error": str(e)}


def cmd_run(dept_key: str, task: str = "") -> Any:
    """指定部門のエントリポイントを起動する。"""
    if dept_key not in DEPARTMENTS:
        print(f"❌ 不明な部門: {dept_key}")
        print(f"   利用可能: {', '.join(DEPARTMENTS.keys())}")
        return

    conf = DEPARTMENTS[dept_key]
    entry: Path = conf["entry"]

    if not entry.exists():
        print(f"❌ エントリファイルが見つかりません: {entry}")
        return

    if dept_key == "hr_support":
        import subprocess
        subprocess.run([sys.executable, str(entry)], cwd=str(AI_EMPIRE))
        return

    cls_name = conf.get("orchestrator")
    if cls_name:
        try:
            mod = _load_module(entry, f"dept_{dept_key}_orch")
            cls = getattr(mod, cls_name)
            orch = cls()
            if task:
                result = orch.run(task)
                print(result)
            else:
                print(f"⚠️  {conf['name']} — task を指定してください")
                print(f"   例: empire_os.py run {dept_key} \"タスク内容\"")
        except NotImplementedError:
            print(f"⚠️  {conf['name']} は現在開発中です")
        except Exception as e:
            print(f"❌ {conf['name']} 起動失敗: {e}")
    else:
        print(f"⚠️  {conf['name']} はオーケストレーター未定義です")


def cmd_patrol(quick: bool = False, repair: bool = True) -> dict:
    """
    全ジョブをパトロールし、エラーがあれば自動修復する。
    """
    logger.info("=== Tokumori OS — パトロール起動 ===")
    from agents.quality.patrol.agent import run as patrol_run
    patrol_report = patrol_run(quick=quick, log_dashboard=True)

    repair_result = {}
    if repair and (patrol_report.error_jobs or patrol_report.stale_jobs):
        logger.info(f"エラー検知: {len(patrol_report.error_jobs)}件 → Repair Agent 起動")
        from agents.quality.repair.agent import RepairAgent
        patrol_dict = {
            "jobs": [
                {
                    "label": j.label, "name": j.name, "system": j.system,
                    "critical": j.critical, "status": j.status,
                    "error_lines": j.error_lines, "diagnosis": j.diagnosis,
                    "repair_needed": j.repair_needed,
                }
                for j in patrol_report.jobs
            ]
        }
        rr = RepairAgent().run(patrol_dict)
        repair_result = {
            "repaired": rr.repaired_count,
            "manual_needed": len(rr.manual_needed),
        }

    return {
        "overall_status": patrol_report.overall_status,
        "ok": len(patrol_report.ok_jobs),
        "warning": len(patrol_report.warning_jobs),
        "error": len(patrol_report.error_jobs),
        "stale": len(patrol_report.stale_jobs),
        **repair_result,
    }


def cmd_list() -> None:
    """部門一覧と簡易ステータスを表示する。"""
    _ensure_user_requests_file()
    pending = len(_read_pending_requests())
    print("\n Tokumori OS — 部門一覧")
    print("=" * 60)
    for key, conf in DEPARTMENTS.items():
        emoji = conf["emoji"]
        name = conf["name"]
        status_icon = "✅" if conf["status"] == "active" else "🔧"
        print(f"  {status_icon} {emoji} {name:<12} [{key}]")
        print(f"      {conf['description'][:55]}")
    print("=" * 60)
    print(f"\n  未処理の依頼: {pending}件  →  empire_os.py catchup で一括処理")
    print("\n使い方:")
    print('  empire_os.py dispatch "タスク内容"  # 自然言語で自動振り分け')
    print("  empire_os.py catchup               # user_requests.md を処理")
    print("  empire_os.py evolve                # 進化サイクル実行")
    print("  empire_os.py status                # 全部門ステータス")


# ─── ステータス表示 ───────────────────────────────────────────────────────────

def _get_dept_status(key: str, conf: dict) -> DeptStatus:
    entry: Path = conf["entry"]
    status = conf["status"]
    error = ""
    meta = {}

    if not entry.exists():
        return DeptStatus(key, conf["name"], "error",
                          error=f"エントリファイルが存在しない: {entry.name}")

    if key == "hr_support":
        try:
            mod = _load_module(entry, f"dept_{key}_main")
            agent_count = len(getattr(mod, "AGENT_REGISTRY", {}))
            meta["registry_agents"] = agent_count
        except Exception as e:
            error = str(e)
            agent_count = 0
    elif key == "quality":
        last_log = _read_evolution_log()
        agent_count = len(last_log.get("steps", []))
        if last_log:
            meta["last_cycle"] = last_log.get("cycle_id", "")
            meta["last_success"] = last_log.get("is_success", False)
    else:
        try:
            cls_name = conf.get("orchestrator")
            if cls_name:
                mod = _load_module(entry, f"dept_{key}_orch_status")
                cls = getattr(mod, cls_name)
                orch = cls()
                sub = getattr(orch, "sub_agents", [])
                agent_count = len(sub)
                meta["sub_agents"] = sub
        except Exception as e:
            agent_count = 0
            meta["note"] = f"開発中: {str(e)[:40]}"

    registry = _read_registry()
    domain_map = {"hr_support": "hr", "sales": "sales", "rpo": "rpo"}
    domain = domain_map.get(key)
    if domain:
        registered = [a for a in registry if a.get("domain") == domain]
        meta["registered_agents"] = len(registered)
        if not agent_count:
            agent_count = len(registered)

    return DeptStatus(
        key=key,
        name=conf["name"],
        status=status if not error else "error",
        agent_count=agent_count,
        error=error,
        meta=meta,
    )


def print_status_report(report: OSReport) -> None:
    pending = report.evolution.get("pending_requests", 0)
    print(f"\n{'='*60}")
    print(f"  Tokumori OS — ステータスレポート")
    print(f"  生成: {report.generated_at[:16]}")
    if pending > 0:
        print(f"  未処理依頼: {pending}件 → empire_os.py catchup")
    print(f"{'='*60}")

    for dept in report.departments:
        icon = "✅" if dept.status == "active" else ("🔧" if dept.status == "dev" else "❌")
        conf = DEPARTMENTS.get(dept.key, {})
        emoji = conf.get("emoji", "")
        print(f"\n  {icon} {emoji} {dept.name} [{dept.key}]")
        if dept.agent_count:
            print(f"    エージェント数: {dept.agent_count}")
        if dept.meta.get("last_cycle"):
            s = "✓" if dept.meta.get("last_success") else "✗"
            print(f"    最終サイクル: {dept.meta['last_cycle']} [{s}]")
        if dept.error:
            print(f"    ⚠️  {dept.error}")

    if report.evolution.get("cycle_id"):
        print(f"\n  📈 最新進化サイクル: {report.evolution.get('cycle_id', '-')}")
        for s in report.evolution.get("steps", []):
            icon = "✓" if s.get("success") else "✗"
            print(f"    {icon} {s['step']} ({s['duration_sec']:.1f}s)")

    print(f"\n{'='*60}\n")


def save_os_report(report: OSReport) -> Path:
    OS_LOG.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = OS_LOG / f"status_{ts}.json"
    data = {
        "generated_at": report.generated_at,
        "departments": [
            {"key": d.key, "name": d.name, "status": d.status,
             "agent_count": d.agent_count, "error": d.error, "meta": d.meta}
            for d in report.departments
        ],
        "evolution": report.evolution,
    }
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


# ─── パブリックAPI ────────────────────────────────────────────────────────────

def run(command: str = "status", **kwargs) -> dict:
    """
    他スクリプトから呼べるパブリックAPI。

    Args:
        command: "status" | "evolve" | "list" | "dispatch" | "catchup" | "clients"
        **kwargs:
            dispatch:  task=str, harness=bool, client_id=str, parallel=bool, max_workers=int
            catchup:   harness=bool, client_id=str, parallel=bool, max_workers=int
            evolve:    dry_run=bool, steps=list
            patrol:    quick=bool, repair=bool
    """
    if command == "status":
        report = cmd_status()
        print_status_report(report)
        return {"departments": len(report.departments), "generated_at": report.generated_at}

    elif command == "dispatch":
        task = kwargs.get("task", "")
        if not task:
            return {"error": "task が指定されていません"}
        result = cmd_dispatch(
            task,
            harness=kwargs.get("harness", False),
            client_id=kwargs.get("client_id"),
            parallel=kwargs.get("parallel", False),
            max_workers=kwargs.get("max_workers", 4),
        )
        return {
            "dept": result.dept_key,
            "success": result.success,
            "result": result.result,
            "duration_sec": result.duration_sec,
        }

    elif command == "catchup":
        results = cmd_catchup(
            harness=kwargs.get("harness", False),
            client_id=kwargs.get("client_id"),
            parallel=kwargs.get("parallel", False),
            max_workers=kwargs.get("max_workers", 4),
        )
        return {"processed": len(results), "success": sum(1 for r in results if r.success)}

    elif command == "clients":
        try:
            client_manager_path = (
                AI_EMPIRE / "agents" / "hr_support" / "config" / "client_manager.py"
            )
            cm_mod = _load_module(client_manager_path, "client_manager_api")
            clients = cm_mod.ClientManager.list_clients(active_only=kwargs.get("active_only", False))
            return {"clients": [c.to_dict() for c in clients]}
        except Exception as exc:
            return {"error": str(exc)}

    elif command == "patrol":
        return cmd_patrol(
            quick=kwargs.get("quick", False),
            repair=kwargs.get("repair", True),
        )

    elif command == "evolve":
        return cmd_evolve(
            dry_run=kwargs.get("dry_run", False),
            steps=kwargs.get("steps"),
        )

    elif command == "list":
        cmd_list()
        return {}

    else:
        logger.error(f"不明なコマンド: {command}")
        return {"error": f"不明なコマンド: {command}"}


# ─── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Tokumori OS — 統合オペレーティングシステム"
    )
    subparsers = parser.add_subparsers(dest="command")

    # status
    subparsers.add_parser("status", help="全部門のステータスを確認")

    # list
    subparsers.add_parser("list", help="部門一覧を表示")

    # dispatch（Phase 3 新機能）
    p_dispatch = subparsers.add_parser("dispatch", help="自然言語タスクを部門自動判定して実行")
    p_dispatch.add_argument("task", help="実行するタスク（自然言語）")
    p_dispatch.add_argument(
        "--harness", action="store_true",
        help="ハーネスモード: Planner→Generator→Evaluator ループで品質保証しながら実行",
    )
    p_dispatch.add_argument(
        "--managed", action="store_true",
        help="Managed Agentsモード: Anthropicインフラ上で実行（$0.08/h、PC電源不要）",
    )
    p_dispatch.add_argument(
        "--client", type=str, default=None,
        help="Phase 7: クライアントID（例: client_abc）。クライアント別資格情報で実行",
    )
    p_dispatch.add_argument(
        "--parallel", action="store_true",
        help="Phase 8: 並列実行モード（複数タスクを ThreadPoolExecutor で同時処理）",
    )
    p_dispatch.add_argument(
        "--max-workers", type=int, default=4,
        help="Phase 8: 並列ワーカー数（デフォルト: 4）",
    )

    # catchup（Phase 3 新機能）
    p_catchup = subparsers.add_parser("catchup", help="user_requests.md の未処理依頼を自動処理")
    p_catchup.add_argument(
        "--harness", action="store_true",
        help="ハーネスモード: 各依頼を Planner→Evaluator ループで処理",
    )
    p_catchup.add_argument(
        "--client", type=str, default=None,
        help="Phase 7: クライアントID。クライアント別資格情報で実行",
    )
    p_catchup.add_argument(
        "--parallel", action="store_true",
        help="Phase 8: 各依頼を並列ディスパッチ",
    )
    p_catchup.add_argument(
        "--max-workers", type=int, default=4,
        help="Phase 8: 並列ワーカー数（デフォルト: 4）",
    )

    # clients（Phase 7 新機能）
    subparsers.add_parser("clients", help="Phase 7: 登録クライアント一覧を表示")

    # patrol（パトロール）
    p_patrol = subparsers.add_parser("patrol", help="全ジョブを監視・エラーを自動修復")
    p_patrol.add_argument("--quick", action="store_true", help="Claude診断をスキップ")
    p_patrol.add_argument("--no-repair", action="store_true", help="自動修復をスキップ")

    # evolve
    p_evolve = subparsers.add_parser("evolve", help="進化サイクルを実行")
    p_evolve.add_argument("--dry-run", action="store_true", help="ファイル変更なしで実行")
    p_evolve.add_argument(
        "--step", nargs="+",
        choices=["security", "review", "improve", "catalog"],
        help="実行するステップを指定（デフォルト: 全ステップ）",
    )

    # run
    p_run = subparsers.add_parser("run", help="部門ポータルを起動")
    p_run.add_argument("dept", choices=list(DEPARTMENTS.keys()), help="部門キー")
    p_run.add_argument("task", nargs="?", default="", help="タスク（オーケストレーター向け）")

    args = parser.parse_args()

    if args.command == "status" or args.command is None:
        report = cmd_status()
        print_status_report(report)
        save_os_report(report)

    elif args.command == "list":
        cmd_list()

    elif args.command == "dispatch":
        if getattr(args, "managed", False):
            # Phase 5: Managed Agents モード
            from core.infrastructure.managed_agent_runner import ManagedAgentRunner
            mgr = ManagedAgentRunner()
            result = mgr.run(args.task)
            mode = " [managed]" if mgr.is_managed_available else " [managed→fallback]"
            print(f"\n{mode} 実行完了")
            print(f"  時間: {result.duration_sec:.1f}s")
            if result.estimated_cost_usd > 0:
                print(f"  コスト: ${result.estimated_cost_usd:.4f}")
            print(f"\n{result.output}")
        else:
            r = cmd_dispatch(
                args.task,
                harness=getattr(args, "harness", False),
                client_id=getattr(args, "client", None),
                parallel=getattr(args, "parallel", False),
                max_workers=getattr(args, "max_workers", 4),
            )
            flags = []
            if getattr(args, "harness", False):
                flags.append("harness")
            if getattr(args, "client", None):
                flags.append(f"client={args.client}")
            if getattr(args, "parallel", False):
                flags.append("parallel")
            mode = f" [{','.join(flags)}]" if flags else ""
            print(f"\n  部門: {r.dept_name} [{r.dept_key}] (by {r.routed_by}){mode}")
            print(f"  時間: {r.duration_sec:.1f}s\n")
            print(r.result)

    elif args.command == "catchup":
        cmd_catchup(
            harness=getattr(args, "harness", False),
            client_id=getattr(args, "client", None),
            parallel=getattr(args, "parallel", False),
            max_workers=getattr(args, "max_workers", 4),
        )

    elif args.command == "clients":
        # Phase 7: 登録クライアント一覧
        try:
            client_manager_path = (
                AI_EMPIRE / "agents" / "hr_support" / "config" / "client_manager.py"
            )
            cm_mod = _load_module(client_manager_path, "client_manager_cli")
            clients = cm_mod.ClientManager.list_clients(active_only=False)
            if clients:
                print(f"\n登録クライアント一覧 ({len(clients)}件):")
                for c in clients:
                    status = "✅ 有効" if c.active else "🔧 設定中"
                    print(f"  {status} [{c.client_id}] {c.name} ({c.tier}) ¥{c.monthly_fee_jpy:,}/月")
            else:
                print("登録クライアントなし")
                print(f"  作成: python3 {client_manager_path} create {{client_id}} {{会社名}}")
        except Exception as e:
            print(f"❌ ClientManager 読み込み失敗: {e}")

    elif args.command == "evolve":
        result = cmd_evolve(dry_run=args.dry_run, steps=args.step)
        status = "✅ 成功" if result.get("success") else "⚠️  一部失敗"
        print(f"\n進化サイクル: {status}")

    elif args.command == "patrol":
        result = cmd_patrol(
            quick=getattr(args, "quick", False),
            repair=not getattr(args, "no_repair", False),
        )
        icons = {"OK": "✅", "WARNING": "⚠️", "ERROR": "❌", "CRITICAL": "🚨"}
        icon = icons.get(result["overall_status"], "❓")
        print(f"\n{icon} {result['overall_status']}")
        print(f"  正常: {result['ok']} / 警告: {result['warning']} / エラー: {result['error']} / 停止疑い: {result['stale']}")
        if result.get("repaired"):
            print(f"  自動修復: {result['repaired']}件")
        if result.get("manual_needed"):
            print(f"  ⚠️  手動対応: {result['manual_needed']}件")

    elif args.command == "run":
        cmd_run(args.dept, getattr(args, "task", ""))
