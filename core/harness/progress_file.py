#!/usr/bin/env python3
"""
harness/progress_file.py — Progress File（外部化メモリ）（Phase 4）

【役割】
  コンテキストリセット後も継続できるよう、タスクの進捗状態を
  JSON ファイルとして外部化して永続化する。

  新しいエージェントインスタンスはこのファイルを読み込むだけで
  前回の続きから再開できる。

【保存先】
  ai-empire/queue/progress/{task_id}.json

【ライフサイクル】
  created → planning → running → evaluating → done | failed
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("harness.progress_file")

_EMPIRE_ROOT = Path(__file__).resolve().parents[2]
_PROGRESS_DIR = _EMPIRE_ROOT / "queue" / "progress"


def _ensure_dir() -> None:
    _PROGRESS_DIR.mkdir(parents=True, exist_ok=True)


class ProgressFile:
    """
    タスクの進捗状態を JSON ファイルで管理するクラス。

    Usage:
        pf = ProgressFile.create(task_id="abc12345", description="SF-Schemaにフィールド追加")
        pf.set_phase("running")
        pf.add_step_result(step_no=1, success=True, output="フィールド追加完了")
        pf.set_phase("done")

        # 再開時
        pf = ProgressFile.load("abc12345")
        print(pf.phase, pf.step_results)
    """

    def __init__(self, data: Dict[str, Any], path: Path) -> None:
        self._data = data
        self._path = path

    # ── ファクトリ ───────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        task_id: str,
        description: str,
        goal: str = "",
        requirements: Optional[List[dict]] = None,
    ) -> "ProgressFile":
        """新しい Progress File を作成する。"""
        _ensure_dir()
        data: Dict[str, Any] = {
            "task_id": task_id,
            "description": description,
            "goal": goal,
            "requirements": requirements or [],
            "phase": "created",
            "step_results": [],
            "evaluation": None,
            "iterations": 0,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        path = _PROGRESS_DIR / f"{task_id}.json"
        pf = cls(data, path)
        pf._save()
        logger.info("ProgressFile 作成: %s", task_id)
        return pf

    @classmethod
    def load(cls, task_id: str) -> Optional["ProgressFile"]:
        """既存の Progress File をロードする。存在しない場合は None。"""
        _ensure_dir()
        path = _PROGRESS_DIR / f"{task_id}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            logger.info("ProgressFile ロード: %s (phase=%s)", task_id, data.get("phase"))
            return cls(data, path)
        except Exception as exc:
            logger.error("ProgressFile ロード失敗: %s — %s", task_id, exc)
            return None

    @classmethod
    def list_incomplete(cls) -> List["ProgressFile"]:
        """完了していない（done/failed 以外の）タスクを一覧返す。"""
        _ensure_dir()
        result = []
        for p in sorted(_PROGRESS_DIR.glob("*.json")):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if data.get("phase") not in ("done", "failed"):
                    result.append(cls(data, p))
            except Exception:
                pass
        return result

    # ── プロパティ ───────────────────────────────────────────────

    @property
    def task_id(self) -> str:
        return self._data["task_id"]

    @property
    def phase(self) -> str:
        return self._data.get("phase", "created")

    @property
    def goal(self) -> str:
        return self._data.get("goal", "")

    @property
    def description(self) -> str:
        return self._data.get("description", "")

    @property
    def step_results(self) -> List[dict]:
        return self._data.get("step_results", [])

    @property
    def requirements(self) -> List[dict]:
        return self._data.get("requirements", [])

    @property
    def iterations(self) -> int:
        return self._data.get("iterations", 0)

    @property
    def is_resumable(self) -> bool:
        """コンテキストリセット後に再開可能かどうか。"""
        return self.phase not in ("done", "failed", "created")

    # ── 状態更新 ─────────────────────────────────────────────────

    def set_phase(self, phase: str) -> None:
        """フェーズを更新して保存する。"""
        self._data["phase"] = phase
        if phase in ("running",):
            self._data["iterations"] = self._data.get("iterations", 0) + 1
        self._save()
        logger.info("ProgressFile フェーズ更新: %s → %s", self.task_id, phase)

    def set_goal(self, goal: str) -> None:
        self._data["goal"] = goal
        self._save()

    def set_requirements(self, requirements: List[dict]) -> None:
        self._data["requirements"] = requirements
        self._save()

    def add_step_result(
        self,
        step_no: int,
        success: bool,
        output: str,
        agent_tag: Optional[str] = None,
    ) -> None:
        """ステップ実行結果を追記する。"""
        self._data.setdefault("step_results", []).append({
            "step_no": step_no,
            "success": success,
            "output": output[:500],
            "agent_tag": agent_tag,
            "executed_at": datetime.now().isoformat(),
        })
        self._save()

    def mark_requirement_done(self, req_id: str) -> None:
        """要件を完了状態にマークする。"""
        for r in self._data.get("requirements", []):
            if r.get("req_id") == req_id:
                r["status"] = "done"
                r["updated_at"] = datetime.now().isoformat()
        self._save()

    def set_evaluation(self, score: float, summary: str, passed: bool) -> None:
        """評価結果を保存する。"""
        self._data["evaluation"] = {
            "score": score,
            "summary": summary,
            "passed": passed,
            "evaluated_at": datetime.now().isoformat(),
        }
        self._save()

    def complete(self, final_output: str = "") -> None:
        """タスク完了としてファイルを最終更新する。"""
        self._data["phase"] = "done"
        self._data["final_output"] = final_output[:1000]
        self._data["completed_at"] = datetime.now().isoformat()
        self._save()
        logger.info("ProgressFile 完了: %s", self.task_id)

    def fail(self, reason: str = "") -> None:
        """タスク失敗として記録する。"""
        self._data["phase"] = "failed"
        self._data["failure_reason"] = reason
        self._data["failed_at"] = datetime.now().isoformat()
        self._save()
        logger.info("ProgressFile 失敗: %s — %s", self.task_id, reason)

    def to_summary(self) -> str:
        """再開時にエージェントに渡す状態サマリー文字列。"""
        reqs_done = sum(1 for r in self.requirements if r.get("status") == "done")
        reqs_total = len(self.requirements)
        lines = [
            f"[再開タスク] task_id={self.task_id}",
            f"目標: {self.goal}",
            f"現在フェーズ: {self.phase}",
            f"要件進捗: {reqs_done}/{reqs_total}",
            f"実行済みステップ: {len(self.step_results)}件",
            f"イテレーション: {self.iterations}回目",
        ]
        if self._data.get("evaluation"):
            ev = self._data["evaluation"]
            lines.append(f"前回評価: score={ev['score']:.2f} {'✅合格' if ev['passed'] else '❌不合格'}")
        return "\n".join(lines)

    # ── 内部 ─────────────────────────────────────────────────────

    def _save(self) -> None:
        self._data["updated_at"] = datetime.now().isoformat()
        self._path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
