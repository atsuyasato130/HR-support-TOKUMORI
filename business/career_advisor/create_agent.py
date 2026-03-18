#!/usr/bin/env python3
"""
create_agent.py — JSONエージェント生成CLI

使い方:
    python3 create_agent.py

対話形式で agent_configs/{agent_key}.json を生成し、
エージェントをシステムに即座に追加する。
"""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Any, Dict, List, Optional

_CAREER_DIR = os.path.dirname(os.path.abspath(__file__))
_AGENT_CONFIGS_DIR = os.path.join(_CAREER_DIR, "agent_configs")
_MANIFEST_PATH = os.path.join(_CAREER_DIR, "knowledge", "AGENT_MANIFEST.json")

# ──────────────────────────────────────────────
# プリセットテンプレート
# ──────────────────────────────────────────────

PRESETS: Dict[str, Dict[str, Any]] = {
    "chat": {
        "label": "対話型コーチング（coaching_agentパターン）",
        "interaction_mode": "chat",
        "stream": True,
        "max_tokens": 2048,
        "system_prompt": {
            "template": (
                "あなたは{{agent_name}}として、{{entity_label}}の{{session_label}}をサポートします。\n\n"
                "■ 方針\n"
                "- 具体的・実践的なアドバイスを提供する\n"
                "- 「なぜそう思うのか」を深掘りする質問をする\n"
                "- {{entity_label}}が自分の言葉で考えを整理できるよう促す"
            ),
            "variables": {},
        },
        "opening_message": "よろしくお願いします。今日はどんなことについて話しますか？",
        "output": {"clipboard_copy": False, "save_to_file": False},
    },
    "form": {
        "label": "フォーム収集→文章生成（line_agent/report_agentパターン）",
        "interaction_mode": "form_then_generate",
        "stream": False,
        "max_tokens": 2000,
        "system_prompt": {
            "template": (
                "あなたは{{agent_name}}として、{{advisor_label}}の業務をサポートします。\n"
                "与えられた情報をもとに、高品質な出力を生成してください。"
            ),
            "variables": {},
        },
        "form_fields": [
            {
                "key": "student_name",
                "label": "学生名",
                "prompt": "学生名 > ",
                "required": True,
                "default": None,
            },
            {
                "key": "memo",
                "label": "メモ・詳細",
                "prompt": "メモを入力してください（空行2回で確定）",
                "required": False,
                "default": "（未入力）",
                "multiline": True,
            },
        ],
        "generation_prompt_template": (
            "学生名: {{student_name}}\n"
            "メモ: {{memo}}\n\n"
            "上記の情報をもとに出力を生成してください。"
        ),
        "output": {"clipboard_copy": True, "save_to_file": False},
    },
    "one_shot": {
        "label": "単発入力→出力（テキスト解析・変換）",
        "interaction_mode": "one_shot",
        "stream": False,
        "max_tokens": 2048,
        "system_prompt": {
            "template": (
                "あなたは{{agent_name}}です。\n"
                "入力されたテキストを分析し、指定された形式で出力してください。"
            ),
            "variables": {},
        },
        "input_prompt": "テキストを貼り付けてください\n（空行2回で確定）\n\n",
        "multiline_input": True,
        "output": {"clipboard_copy": True, "save_to_file": False},
    },
    "menu": {
        "label": "サブモード選択メニュー（複数機能を1エージェントに集約）",
        "interaction_mode": "menu",
        "stream": True,
        "max_tokens": 2048,
        "menu": {
            "title": "メニュー",
            "items": [
                {
                    "key": "1",
                    "label": "機能A",
                    "mode": "chat",
                    "opening_message": "機能Aを開始します。",
                },
                {
                    "key": "2",
                    "label": "機能B",
                    "mode": "form_then_generate",
                    "form_fields": [
                        {"key": "input", "label": "入力", "prompt": "入力 > ", "required": True},
                    ],
                    "generation_prompt_template": "{{input}} をもとに生成してください。",
                    "system_prompt": {
                        "template": "あなたは有能なアシスタントです。",
                        "variables": {},
                    },
                },
            ],
        },
        "output": {"clipboard_copy": False, "save_to_file": False},
    },
}

# ──────────────────────────────────────────────
# バリデーション
# ──────────────────────────────────────────────

def _validate_key(key: str) -> Optional[str]:
    """エラーメッセージを返す。問題なければ None。"""
    if not key:
        return "agent_key は必須です"
    if not re.match(r"^[a-z][a-z0-9_]*$", key):
        return "agent_key は小文字英字で始まる英数字・アンダースコアのみ"
    config_path = os.path.join(_AGENT_CONFIGS_DIR, f"{key}.json")
    if os.path.exists(config_path):
        return f"agent_configs/{key}.json が既に存在します"
    return None


def _load_existing_keys() -> List[str]:
    """既存の agent_key 一覧を返す"""
    keys = []
    if not os.path.isdir(_AGENT_CONFIGS_DIR):
        return keys
    for f in os.listdir(_AGENT_CONFIGS_DIR):
        if f.endswith(".json") and not f.startswith("_"):
            try:
                with open(os.path.join(_AGENT_CONFIGS_DIR, f)) as fh:
                    data = json.load(fh)
                keys.append(data.get("agent_key", ""))
            except Exception:
                pass
    return keys


# ──────────────────────────────────────────────
# AGENT_MANIFEST.json 更新
# ──────────────────────────────────────────────

def _update_manifest(config: Dict[str, Any]) -> None:
    """knowledge/AGENT_MANIFEST.json に新エージェントを追記する"""
    try:
        with open(_MANIFEST_PATH, "r", encoding="utf-8") as fh:
            manifest = json.load(fh)
    except Exception:
        manifest = {"agents": []}

    agents = manifest.get("agents", [])
    # 既存エントリ確認（上書き防止）
    if any(a.get("agent_key") == config["agent_key"] for a in agents):
        return

    agents.append(
        {
            "agent_key": config["agent_key"],
            "agent_name": config["agent_name"],
            "description": config.get("description", ""),
            "interaction_mode": config.get("interaction_mode"),
            "status": config.get("status", "active"),
            "created": config.get("created", ""),
            "source": "json_template",
        }
    )
    manifest["agents"] = agents
    with open(_MANIFEST_PATH, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
    print(f"  ✅ AGENT_MANIFEST.json を更新しました")


# ──────────────────────────────────────────────
# メイン対話フロー
# ──────────────────────────────────────────────

def main() -> None:
    import datetime

    print("\n" + "=" * 60)
    print("  create_agent.py — JSONエージェント生成ツール")
    print("=" * 60)
    print("\n  このツールで agent_configs/*.json を生成し、")
    print("  新しいエージェントをシステムに即座に追加できます。\n")

    # ── プリセット選択 ──
    print("  プリセットを選択してください:\n")
    preset_keys = list(PRESETS.keys())
    for i, key in enumerate(preset_keys, 1):
        print(f"    {i}. {PRESETS[key]['label']}")
    print("    q. 終了\n")

    while True:
        choice = input("  選択 > ").strip().lower()
        if choice == "q":
            print("  終了します。")
            sys.exit(0)
        if choice.isdigit() and 1 <= int(choice) <= len(preset_keys):
            preset_key = preset_keys[int(choice) - 1]
            break
        print("  無効な選択です。")

    preset = dict(PRESETS[preset_key])
    print(f"\n  [{PRESETS[preset_key]['label']}] を選択しました\n")

    # ── 基本情報入力 ──
    print("  基本情報を入力してください:\n")

    # agent_key
    while True:
        key = input("  agent_key（英小文字・数字・_） > ").strip()
        err = _validate_key(key)
        if err:
            print(f"  ⚠️  {err}")
        else:
            break

    # agent_name
    name = input("  agent_name（表示名・日本語可） > ").strip()
    if not name:
        name = key

    # description
    desc = input("  description（1行説明・省略可） > ").strip()

    # keywords
    kw_input = input("  ルーティングキーワード（カンマ区切り） > ").strip()
    keywords = [kw.strip() for kw in kw_input.split(",") if kw.strip()] or [key]

    # system_prompt カスタマイズ
    print(f"\n  デフォルトのsystem_prompt:\n")
    sp = preset.get("system_prompt", {})
    default_template = sp.get("template", "") if isinstance(sp, dict) else sp
    print(f"  ---\n{default_template}\n  ---\n")
    customize = input("  カスタマイズしますか？ (y/N) > ").strip().lower()
    if customize in ("y", "yes"):
        print("  新しいsystem_promptを入力してください（空行2回で確定）:")
        lines: List[str] = []
        empty_count = 0
        while empty_count < 2:
            line = input()
            if line == "":
                empty_count += 1
            else:
                empty_count = 0
                lines.append(line)
        new_template = "\n".join(lines).strip()
        if new_template:
            if isinstance(preset.get("system_prompt"), dict):
                preset["system_prompt"]["template"] = new_template
            else:
                preset["system_prompt"] = new_template

    # ── 設定オブジェクト構築 ──
    import datetime
    now = datetime.datetime.now().strftime("%Y-%m-%d")

    config: Dict[str, Any] = {
        "agent_key": key,
        "agent_name": name,
        "description": desc,
        **preset,
        "routing": {
            "keywords": keywords,
            "priority": 5,
        },
        "domain_config_path": "config/domain_hr.json",
        "version": "1.0",
        "created": now,
        "author": "create_agent.py",
        "tags": [key],
        "status": "active",
    }

    # ── プレビュー ──
    print("\n  ── 生成される設定 ──────────────────────────────")
    print(json.dumps(config, ensure_ascii=False, indent=2))
    print("  ────────────────────────────────────────────────\n")

    confirm = input("  この設定で保存しますか？ (y/N) > ").strip().lower()
    if confirm not in ("y", "yes"):
        print("  キャンセルしました。")
        sys.exit(0)

    # ── 保存 ──
    os.makedirs(_AGENT_CONFIGS_DIR, exist_ok=True)
    config_path = os.path.join(_AGENT_CONFIGS_DIR, f"{key}.json")
    with open(config_path, "w", encoding="utf-8") as fh:
        json.dump(config, fh, ensure_ascii=False, indent=2)

    print(f"\n  ✅ agent_configs/{key}.json を作成しました")
    _update_manifest(config)

    print(f"\n  🎉 エージェント [{name}] の追加完了！")
    print(f"  python3 main.py を起動して /{key} で呼び出せます。\n")


if __name__ == "__main__":
    main()
