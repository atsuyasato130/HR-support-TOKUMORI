#!/usr/bin/env python3
"""
template_agent.py — JSON設定1つで動作する汎用エージェントエンジン

【使い方】
    # JSON設定ファイルから起動
    agent = TemplateAgent.from_config_file("agent_configs/my_agent.json")
    agent.execute()

    # main.py からは自動起動（agent_configs/*.json を自動スキャン）

【interaction_mode 一覧】
    "chat"              → 対話ループ（coaching_agentパターン）
    "one_shot"          → 1入力→1出力
    "form_then_generate"→ フォーム収集→生成（line_agent/report_agentパターン）
    "menu"              → サブモード選択メニュー（デフォルト）
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import datetime
from typing import Any, Dict, List, Optional

from base_agent import BaseAgent

# ──────────────────────────────────────────────
# テンプレート変数の解決
# ──────────────────────────────────────────────

def _render_template(template: str, variables: Dict[str, str]) -> str:
    """{{変数名}} 形式のプレースホルダーを variables で置換する"""
    for key, value in variables.items():
        template = template.replace("{{" + key + "}}", str(value))
    return template


# ──────────────────────────────────────────────
# TemplateAgent 本体
# ──────────────────────────────────────────────

class TemplateAgent(BaseAgent):
    """
    JSON設定ファイルを読み込んで動作する汎用エージェントエンジン。

    新しいエージェントを追加するには agent_configs/{key}.json を置くだけ。
    Pythonコードの追記は一切不要。

    後方互換性: 既存11エージェント（coaching_agent.py等）は一切変更なし。
    """

    agent_key: str = "template"
    agent_name: str = "テンプレートエージェント"
    agent_desc: str = "JSON設定で動作する汎用エージェント"

    def __init__(self, config: Dict[str, Any], dry_run: bool = False) -> None:
        super().__init__(dry_run=dry_run)
        self._config = config

        # クラス変数をインスタンスで上書き
        self.agent_key = config.get("agent_key", "template")
        self.agent_name = config.get("agent_name", "エージェント")
        self.agent_desc = config.get("description", "")

        # domain_config 読み込み（業界転用）
        domain_path = config.get("domain_config_path", "config/domain_hr.json")
        full_domain_path = self._resolve_path(domain_path)
        try:
            with open(full_domain_path, "r", encoding="utf-8") as fh:
                self._domain: Dict[str, Any] = json.load(fh)
        except Exception:
            self._domain = {}

    # ──────────────────────────────────────────────
    # ファクトリーメソッド
    # ──────────────────────────────────────────────

    @classmethod
    def from_config_file(cls, path: str, dry_run: bool = False) -> "TemplateAgent":
        """JSONファイルからTemplateAgentを生成する"""
        with open(path, "r", encoding="utf-8") as fh:
            config = json.load(fh)
        return cls(config, dry_run=dry_run)

    # ──────────────────────────────────────────────
    # エントリポイント（BaseAgent抽象メソッドの実装）
    # ──────────────────────────────────────────────

    def run(self) -> Optional[str]:
        """interaction_mode に応じてモードを分岐する"""
        mode = self._config.get("interaction_mode", "menu")

        if mode == "chat":
            return self._run_chat_mode()
        elif mode == "one_shot":
            return self._run_one_shot_mode()
        elif mode == "form_then_generate":
            return self._run_form_mode()
        elif mode == "menu":
            return self._run_menu_mode()
        else:
            print(f"  [WARN] 不明なinteraction_mode: '{mode}' → chatモードで起動します")
            return self._run_chat_mode()

    # ──────────────────────────────────────────────
    # モード実装
    # ──────────────────────────────────────────────

    def _run_chat_mode(
        self,
        system_override: Optional[str] = None,
        opening_override: Optional[str] = None,
        config_override: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        対話ループモード。coaching_agentパターンを汎用化。
        q/quit/終了 で終了、出力テキストをまとめて返す。
        """
        cfg = config_override or self._config
        system = system_override or self._resolve_system_prompt(cfg)
        opening = opening_override or cfg.get("opening_message", "何でも聞いてください。")
        title = cfg.get("agent_name", self.agent_name)
        model = cfg.get("model", "claude-sonnet-4-6")
        max_tokens = cfg.get("max_tokens", 2048)
        use_stream = cfg.get("stream", True)

        messages: List[Dict[str, str]] = [{"role": "assistant", "content": opening}]
        print(f"\n{'=' * 55}")
        print(f"  {title}")
        print(f"{'=' * 55}")
        print(f"\nAI > {opening}\n")

        outputs: List[str] = []

        while True:
            try:
                user_input = input("あなた > ").strip()
            except (KeyboardInterrupt, EOFError):
                break

            if not user_input:
                continue
            if user_input.lower() in ("q", "quit", "exit", "終了"):
                break

            messages.append({"role": "user", "content": user_input})

            if use_stream:
                response_text = self._call_stream(system, messages, model, max_tokens)
            else:
                response_text = self._call_sync(system, messages, model, max_tokens)

            messages.append({"role": "assistant", "content": response_text})
            outputs.append(f"Q: {user_input}\nA: {response_text}")

        return "\n\n".join(outputs) if outputs else None

    def _run_one_shot_mode(
        self,
        config_override: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        単発入力→単発出力モード。
        1行入力 or 複数行入力（multiline_input: true）に対応。
        """
        cfg = config_override or self._config
        system = self._resolve_system_prompt(cfg)
        model = cfg.get("model", "claude-sonnet-4-6")
        max_tokens = cfg.get("max_tokens", 2048)
        title = cfg.get("agent_name", self.agent_name)
        input_prompt = cfg.get("input_prompt", "入力 > ")
        multiline = cfg.get("multiline_input", False)

        print(f"\n{'=' * 55}")
        print(f"  {title}")
        print(f"{'=' * 55}\n")

        if multiline:
            print(f"{input_prompt}")
            print("（空行2回で確定）\n")
            user_input = self._read_multiline()
        else:
            user_input = input(input_prompt).strip()

        if not user_input:
            print("  入力がありません。")
            return None

        print("\n生成中...\n")
        result = self._call_sync(
            system,
            [{"role": "user", "content": user_input}],
            model,
            max_tokens,
        )
        print(result)
        self._handle_output(result, cfg)
        return result

    def _run_form_mode(
        self,
        config_override: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        フォーム収集→生成モード。
        form_fields を順番に入力させ、generation_prompt_template に埋め込んで生成する。
        line_agent / report_agent パターンを汎用化。
        """
        cfg = config_override or self._config
        fields = cfg.get("form_fields", [])
        gen_template = cfg.get("generation_prompt_template", "")
        system = self._resolve_system_prompt(cfg)
        model = cfg.get("model", "claude-sonnet-4-6")
        max_tokens = cfg.get("max_tokens", 2048)
        title = cfg.get("agent_name", self.agent_name)

        print(f"\n{'=' * 55}")
        print(f"  {title}")
        print(f"{'=' * 55}\n")

        collected: Dict[str, str] = {}

        for field in fields:
            key = field["key"]
            prompt_text = field.get("prompt", f"{key} > ")
            required = field.get("required", False)
            default = field.get("default")
            is_multiline = field.get("multiline", False)

            if is_multiline:
                print(f"\n{prompt_text}")
                print("（空行2回で確定）\n")
                value = self._read_multiline()
            else:
                value = input(prompt_text).strip()

            if not value:
                if default is not None:
                    value = str(default)
                elif required:
                    print(f"  [{field.get('label', key)}] は必須です。中断します。")
                    return None

            collected[key] = value

        # テンプレート変数を解決
        prompt = _render_template(gen_template, collected)

        print("\n生成中...\n")
        result = self._call_sync(
            system,
            [{"role": "user", "content": prompt}],
            model,
            max_tokens,
        )

        print(f"\n{'─' * 55}")
        print(result)
        print(f"{'─' * 55}")
        self._handle_output(result, cfg)
        return result

    def _run_menu_mode(self) -> Optional[str]:
        """
        サブモード選択メニュー。
        config["menu"]["items"] に従ってメニューを表示し、選択されたモードを実行する。
        """
        menu_cfg = self._config.get("menu", {})
        items = menu_cfg.get("items", [])
        title = menu_cfg.get("title", self.agent_name)

        if not items:
            # メニュー設定なし → chatモードにフォールバック
            return self._run_chat_mode()

        print(f"\n{'=' * 55}")
        print(f"  {title}")
        print(f"{'=' * 55}")
        for item in items:
            print(f"    {item['key']}. {item['label']}")
        print("\n  q. 終了")
        print(f"{'=' * 55}")

        outputs: List[str] = []

        while True:
            try:
                choice = input("\n選択 > ").strip().lower()
            except (KeyboardInterrupt, EOFError):
                break

            if choice in ("q", "quit", "終了"):
                break

            selected = next((i for i in items if i["key"] == choice), None)
            if not selected:
                print(f"  '{choice}' は無効な選択です。")
                continue

            mode = selected.get("mode", "chat")
            # メニューアイテム個別の設定をマージ
            item_config = {**self._config, **selected}

            if mode == "chat":
                result = self._run_chat_mode(config_override=item_config)
            elif mode == "form_then_generate":
                result = self._run_form_mode(config_override=item_config)
            elif mode == "one_shot":
                result = self._run_one_shot_mode(config_override=item_config)
            else:
                result = self._run_chat_mode(config_override=item_config)

            if result:
                outputs.append(result)

            # メニューに戻るか確認
            try:
                again = input("\n  続けますか？ (y/n) > ").strip().lower()
                if again not in ("y", "yes", "はい"):
                    break
            except (KeyboardInterrupt, EOFError):
                break

        return "\n\n".join(outputs) if outputs else None

    # ──────────────────────────────────────────────
    # システムプロンプト解決
    # ──────────────────────────────────────────────

    def _resolve_system_prompt(
        self,
        config_override: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        config["system_prompt"] の {{変数名}} テンプレートを解決する。

        解決優先順位:
          1. config["system_prompt"]["variables"] （静的定義）
          2. domain_hr.json の entity 情報（自動注入）
          3. エージェント自身のメタ情報
        """
        cfg = config_override or self._config
        sp_config = cfg.get("system_prompt", {})

        if isinstance(sp_config, str):
            # 文字列直指定（後方互換）
            return sp_config

        template = sp_config.get("template", "あなたは有能なAIアシスタントです。")
        variables: Dict[str, str] = dict(sp_config.get("variables", {}))

        # domain_hr.json から自動注入
        if self._domain:
            entity = self._domain.get("entity", {})
            variables.setdefault("entity_label", entity.get("label", "ユーザー"))
            variables.setdefault("counterpart_label", entity.get("counterpart_label", "相手"))
            variables.setdefault("session_label", entity.get("session_label", "セッション"))
            variables.setdefault("advisor_label", entity.get("advisor_label", "担当者"))

        # エージェント自身のメタ情報
        variables.setdefault("agent_name", cfg.get("agent_name", self.agent_name))
        variables.setdefault("agent_key", cfg.get("agent_key", self.agent_key))

        return _render_template(template, variables)

    # ──────────────────────────────────────────────
    # Claude API 呼び出し
    # ──────────────────────────────────────────────

    def _call_sync(
        self,
        system: str,
        messages: List[Dict[str, str]],
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 2048,
    ) -> str:
        """同期呼び出し（一括取得）"""
        response = self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
        )
        return response.content[0].text

    def _call_stream(
        self,
        system: str,
        messages: List[Dict[str, str]],
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 2048,
    ) -> str:
        """ストリーミング呼び出し（文字を逐次表示）"""
        print("\nAI > ", end="", flush=True)
        full_text = ""
        with self._client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                print(text, end="", flush=True)
                full_text += text
        print("\n")
        return full_text

    # ──────────────────────────────────────────────
    # ユーティリティ
    # ──────────────────────────────────────────────

    def _read_multiline(self) -> str:
        """空行2回で確定する複数行入力"""
        lines: List[str] = []
        empty_count = 0
        while empty_count < 2:
            try:
                line = input()
            except (KeyboardInterrupt, EOFError):
                break
            if line == "":
                empty_count += 1
            else:
                empty_count = 0
                lines.append(line)
        return "\n".join(lines).strip()

    def _handle_output(self, result: str, cfg: Dict[str, Any]) -> None:
        """出力後処理（クリップボードコピー・ファイル保存）"""
        output_cfg = cfg.get("output", {})

        if output_cfg.get("clipboard_copy"):
            try:
                subprocess.run(
                    ["pbcopy"],
                    input=result.encode("utf-8"),
                    check=True,
                )
                print("\n  ✅ クリップボードにコピーしました")
            except Exception:
                pass  # macOS以外や失敗時は無視

        if output_cfg.get("save_to_file"):
            self._save_to_file(result, cfg)

    def _save_to_file(self, result: str, cfg: Dict[str, Any]) -> None:
        """reports/ 配下にファイル保存する"""
        reports_dir = self._resolve_path(
            self._profile.get("reports_dir", "reports")
        )
        os.makedirs(reports_dir, exist_ok=True)

        pattern = cfg.get("output", {}).get(
            "file_pattern", "{date}_{agent_key}_output.txt"
        )
        now = datetime.datetime.now()
        filename = pattern.format(
            date=now.strftime("%Y%m%d"),
            agent_key=self.agent_key,
            datetime=now.strftime("%Y%m%d_%H%M%S"),
        )
        filepath = os.path.join(reports_dir, filename)

        with open(filepath, "w", encoding="utf-8") as fh:
            fh.write(result)
        print(f"\n  ✅ ファイル保存: {filepath}")


# ──────────────────────────────────────────────
# スタンドアロン実行（テスト用）
# ──────────────────────────────────────────────

def run():
    """main.py からの呼び出しエントリポイント（このファイルは直接呼ばれない）"""
    # このモジュール自体は直接 run() されない。
    # _run_agent() が TemplateAgent.from_config_file() を呼ぶ。
    print("  [INFO] template_agent.run() は直接呼び出し不可です。agent_configs/*.json を介して起動してください。")
