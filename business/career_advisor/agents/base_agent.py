#!/usr/bin/env python3
"""
BaseAgent — すべてのエージェントの親クラス

機能:
  - PII_DETECTOR : 日本語HR文脈における個人情報パターン定義
  - @secure_output : execute() 完了時に出力を自動PII洗浄するデコレータ
  - archive_intelligence() : ノウハウをタグ付きMarkdownで自動保存

使い方（子クラス実装例）:
  class MyAgent(BaseAgent):
      agent_key  = "my_agent"
      agent_name = "マイエージェント"
      agent_desc = "〇〇を実行する"

      def run(self) -> Optional[str]:
          ...
          return "セッション出力テキスト"

  MyAgent().execute()  # PII洗浄 + ノウハウ保存を自動実行
"""

from __future__ import annotations

import os
import re
import json
import functools
import datetime
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional

import anthropic
from dotenv import load_dotenv

# プロジェクトルート: career_advisor/agents/ → career_advisor/ → project root
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(_BASE_DIR, "config", ".env"))

# ──────────────────────────────────────────────
# PII検出パターン（日本語HR文脈）
# ──────────────────────────────────────────────

PII_DETECTOR: Dict[str, re.Pattern] = {
    # メールアドレス
    "email": re.compile(
        r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
        re.IGNORECASE,
    ),
    # 日本の電話番号（携帯・固定・フリーダイヤル）
    "phone_jp": re.compile(
        r"(?<!\d)0(?:\d{1,4}[\-\s]?\d{1,4}[\-\s]?\d{3,4}|\d{9,10})(?!\d)",
    ),
    # 郵便番号
    "postal_code": re.compile(
        r"〒?\s*\d{3}[\-\s]\d{4}",
    ),
    # 生年月日（YYYY年MM月DD日 / YYYY-MM-DD / YYYY/MM/DD）
    "birthdate": re.compile(
        r"\d{4}[年\-/]\d{1,2}[月\-/]\d{1,2}[日]?",
    ),
    # 氏名ラベル付き（「氏名: 山田太郎」「学生名：鈴木花子」等）
    "name_label": re.compile(
        r"(?:氏名|学生名|名前|お名前)[：:]\s*\S+(?:[\s　]\S+)?",
    ),
    # LINE ID
    "line_id": re.compile(
        r"LINE\s*ID[：:\s]+\S+",
        re.IGNORECASE,
    ),
    # マイナンバー（12桁数字）
    "my_number": re.compile(
        r"(?<!\d)\d{4}[\s\-]?\d{4}[\s\-]?\d{4}(?!\d)",
    ),
}


def _mask_pii(text: str) -> str:
    """テキスト内の個人情報を [LABEL_MASKED] 形式でマスクする"""
    masked = text
    for label, pattern in PII_DETECTOR.items():
        masked = pattern.sub(f"[{label.upper()}_MASKED]", masked)
    return masked


# ──────────────────────────────────────────────
# @secure_output デコレータ
# ──────────────────────────────────────────────

def secure_output(func: Callable) -> Callable:
    """
    execute() に付与するデコレータ。
    子クラスの run() 完了後、戻り値の文字列から個人情報を自動洗浄する。

    - str が返された場合 → PII マスキング後に返す
    - None が返された場合 → 空文字列を返す
    """
    @functools.wraps(func)
    def wrapper(self: "BaseAgent", *args: Any, **kwargs: Any) -> str:
        raw_result = func(self, *args, **kwargs)
        if isinstance(raw_result, str):
            return _mask_pii(raw_result)
        if raw_result is None:
            return ""
        return _mask_pii(str(raw_result))
    return wrapper


# ──────────────────────────────────────────────
# BaseAgent 親クラス
# ──────────────────────────────────────────────

class BaseAgent(ABC):
    """
    すべてのエージェントの親クラス。

    子クラスで定義するクラス変数:
        agent_key  (str): AGENT_REGISTRY キー（例: "coaching"）
        agent_name (str): 表示名（例: "学生コーチング"）
        agent_desc (str): 一行説明

    子クラスで実装するメソッド:
        run() -> Optional[str]:
            エージェントのメインロジック。
            出力テキストを返すとノウハウとして自動アーカイブされる。
            対話ループのみの場合は None を返してよい。
    """

    agent_key: str = ""
    agent_name: str = ""
    agent_desc: str = ""

    def __init__(self, dry_run: bool = False) -> None:
        """
        Args:
            dry_run: True の場合、archive_intelligence() は実行するが
                     外部API（SF/Slack等）への書き込みは子クラスが制御する。
                     テスト・デモ実行時に使用する。
        """
        settings_path = os.path.join(_BASE_DIR, "config", "factory_settings.json")
        with open(settings_path, "r", encoding="utf-8") as fh:
            self._settings: dict = json.load(fh)

        profile_name = self._settings.get("active_profile", "company")
        self._profile: dict = self._settings.get("profiles", {}).get(profile_name, {})
        self._client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        self.dry_run: bool = dry_run

    @abstractmethod
    def run(self) -> Optional[str]:
        """
        エージェントのメインロジック（子クラスで必ず実装）。

        Returns:
            出力テキスト（ノウハウ保存の入力になる）。
            対話ループのみで出力テキストがない場合は None を返す。
        """
        ...

    @secure_output
    def execute(self) -> str:
        """
        run() を呼び出し、出力を PII 洗浄して返す。
        洗浄後に内容があれば archive_intelligence() でノウハウを自動保存する。

        Returns:
            PII マスキング済みの出力テキスト（出力なしの場合は空文字列）
        """
        result = self.run()
        # @secure_output がマスキングを行うため、ここでは生の result を返す
        # （デコレータが wrapper 内で _mask_pii を適用する）
        cleaned = _mask_pii(result) if isinstance(result, str) else ""
        if cleaned.strip():
            self.archive_intelligence(cleaned)
        return result  # デコレータ側でマスクされる

    # ──────────────────────────────────────────────
    # ノウハウ保存
    # ──────────────────────────────────────────────

    def archive_intelligence(
        self,
        content: str,
        tags: Optional[List[str]] = None,
    ) -> str:
        """
        セッション出力からノウハウを抽出し、タグ付き Markdown で保存する。

        Args:
            content : PII 洗浄済みのセッション出力テキスト
            tags    : 追加タグ（省略時は agent_key を自動付与）

        Returns:
            保存したファイルのパス
        """
        knowledge_dir = self._resolve_path(
            self._profile.get("knowledge_dir", "knowledge/company")
        )
        os.makedirs(knowledge_dir, exist_ok=True)

        insights = self._extract_insights(content)

        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{ts}_{self.agent_key or 'unknown'}.md"
        filepath = os.path.join(knowledge_dir, filename)

        effective_tags: List[str] = list(tags or [])
        if self.agent_key and self.agent_key not in effective_tags:
            effective_tags.insert(0, self.agent_key)

        md = self._render_markdown(insights, effective_tags, ts)
        with open(filepath, "w", encoding="utf-8") as fh:
            fh.write(md)

        print(f"\n[BaseAgent] ノウハウを保存しました: {filepath}")
        return filepath

    def _extract_insights(self, content: str) -> dict:
        """Claude を使ってセッション出力からノウハウを抽出する"""
        max_chars = 3000
        excerpt = content[:max_chars]

        prompt = (
            "以下はHR支援AIエージェントのセッション出力です（個人情報はマスク済み）。\n"
            "このセッションから学べる『ノウハウ・知見・再現可能なパターン』を抽出してください。\n\n"
            "出力形式（JSONのみ、前置き不要）:\n"
            "{\n"
            '  "title": "ノウハウのタイトル（15字以内）",\n'
            '  "summary": "このセッションの概要（2文以内）",\n'
            '  "insights": ["インサイト1", "インサイト2", "インサイト3"],\n'
            '  "applicable_tags": ["タグ1", "タグ2"]\n'
            "}\n\n"
            f"セッション出力:\n{excerpt}"
        )

        try:
            response = self._client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=600,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(raw[start:end])
        except Exception as exc:
            print(f"[BaseAgent] ノウハウ抽出に失敗しました: {exc}")

        # フォールバック
        return {
            "title": f"{self.agent_name}セッション",
            "summary": "セッション概要の自動抽出に失敗しました。",
            "insights": [content[:300]],
            "applicable_tags": [],
        }

    def _render_markdown(self, insights: dict, tags: List[str], ts: str) -> str:
        """抽出インサイトを Markdown 文字列に変換する"""
        extra_tags = [t for t in insights.get("applicable_tags", []) if t not in tags]
        all_tags = tags + extra_tags
        tag_str = ", ".join(f'"{t}"' for t in all_tags)

        date_str = ts[:8]  # YYYYMMDD

        lines = [
            "---",
            f'date: "{date_str}"',
            f'agent: "{self.agent_key}"',
            f"tags: [{tag_str}]",
            "---",
            "",
            f"# {insights.get('title', 'ノウハウ')}",
            "",
            "## 概要",
            "",
            insights.get("summary", ""),
            "",
            "## 抽出されたインサイト",
            "",
        ]
        for i, item in enumerate(insights.get("insights", []), 1):
            lines.append(f"{i}. {item}")

        lines += [
            "",
            "---",
            f"*生成エージェント: {self.agent_name} (`{self.agent_key}`) / {ts}*",
        ]
        return "\n".join(lines) + "\n"

    def _resolve_path(self, path: str) -> str:
        """相対パスをプロジェクトルート基準の絶対パスに変換する"""
        if os.path.isabs(path):
            return path
        return os.path.join(_BASE_DIR, path)
