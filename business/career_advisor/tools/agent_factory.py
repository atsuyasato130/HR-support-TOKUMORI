#!/usr/bin/env python3
"""
AgentFactory — BaseAgent 継承エージェントを自動生成するツール

使い方:
  # 引数渡し
  python3 tools/agent_factory.py --key interview_prep --name "面接準備" --role "学生の面接準備をサポートする"

  # 対話モード
  python3 tools/agent_factory.py

生成物（3点セット）:
  1. career_advisor/agents/<key>_agent.py     （BaseAgent 継承の子クラス）
  2. career_advisor/main.py                   （AGENT_REGISTRY に自動追記）
  3. career_advisor/agents/supporter_agent.py （SYSTEM_KNOWLEDGE に自動追記）
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
import textwrap
from typing import List, Optional

# ──────────────────────────────────────────────
# パス定義
# ──────────────────────────────────────────────

_TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_TOOLS_DIR)

_AGENTS_DIR = os.path.join(_PROJECT_ROOT, "career_advisor", "agents")
_MAIN_PY = os.path.join(_PROJECT_ROOT, "career_advisor", "main.py")
_SUPPORTER_PY = os.path.join(_PROJECT_ROOT, "career_advisor", "agents", "supporter_agent.py")
_MANIFEST_PATH = os.path.join(_PROJECT_ROOT, "docs", "AGENT_MANIFEST.json")

# ──────────────────────────────────────────────
# エージェントファイル テンプレート
# ──────────────────────────────────────────────

_AGENT_TEMPLATE = '''\
#!/usr/bin/env python3
"""
{agent_name}エージェント

役割:
  {role}

使い方:
  python3 career_advisor/agents/{filename}
  from agents.{module_name} import run
"""

from __future__ import annotations

import os
import sys
from typing import Optional

# BaseAgent のあるディレクトリを sys.path に追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import anthropic
from dotenv import load_dotenv
from agents.base_agent import BaseAgent

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_BASE, "../config/.env"))

_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# ──────────────────────────────────────────────
# {agent_name} システムプロンプト
# ──────────────────────────────────────────────

_SYSTEM_PROMPT = """\\
■ 役割
{role}

■ 対象ユーザー
キャリアアドバイザー（CA）

■ 応答方針
- 具体的・実践的なアドバイスを提供する
- 必要に応じて追加情報を質問する
- 最終的には明確なアウトプット（テキスト・リスト・手順）を返す
"""


# ──────────────────────────────────────────────
# {agent_name} クラス
# ──────────────────────────────────────────────

class {class_name}(BaseAgent):
    """
    {agent_name}

    役割: {role}

    TODO: run() に具体的なロジックを実装してください。
    """

    agent_key = "{agent_key}"
    agent_name = "{agent_name}"
    agent_desc = "{role}"

    def run(self) -> Optional[str]:
        """
        {agent_name}のメインループ。

        戻り値として出力文字列を返すと BaseAgent がノウハウを自動アーカイブします。
        対話ループのみの場合は None を返してください。

        TODO: このメソッドに業務ロジックを実装してください。
        """
        sep = "=" * 50
        print("\\n" + sep)
        print(f"  {self.agent_name}")
        print(f"  {self.agent_desc}")
        print(sep)

        outputs: list = []

        while True:
            try:
                user_input = input("\\nあなた > ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\\n終了します")
                break

            if user_input.lower() in ("q", "quit", "exit", "終了"):
                break
            if not user_input:
                continue

            response = _client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2048,
                system=_SYSTEM_PROMPT,
                messages=[{{"role": "user", "content": user_input}}],
            )
            reply = response.content[0].text
            print(f"\\nAI > {{reply}}")
            outputs.append(f"Q: {{user_input}}\\nA: {{reply}}")

        return "\\n\\n".join(outputs) if outputs else None


# ──────────────────────────────────────────────
# エントリポイント
# ──────────────────────────────────────────────

def run() -> None:
    """main.py のオーケストレーターから呼び出されるエントリポイント"""
    {class_name}().execute()


if __name__ == "__main__":
    run()
'''

# ──────────────────────────────────────────────
# AGENT_REGISTRY エントリ テンプレート
# ──────────────────────────────────────────────

_REGISTRY_ENTRY = '''\
    "{agent_key}": {{
        "name": "{agent_name}",
        "desc": "{role}",
        "module": "{module_name}",
        "keywords": {keywords_json},
    }},
'''

# ──────────────────────────────────────────────
# SYSTEM_KNOWLEDGE エントリ テンプレート
# ──────────────────────────────────────────────

_KNOWLEDGE_ENTRY = """\

\u25a0 {module_name}\uff08{agent_name}\uff09
  \u30d5\u30a1\u30a4\u30eb: career_advisor/agents/{filename}
  \u6a5f\u80fd:
    - {role}
  \u4f7f\u3046\u30bf\u30a4\u30df\u30f3\u30b0:
    - \u300c{agent_name}\u3092\u4f7f\u3044\u305f\u3044\u300d\u307e\u305f\u306f \u300c/{agent_key}\u300d \u3067\u76f4\u63a5\u8d77\u52d5
  \u751f\u6210\u65e5: {date}
"""

# ──────────────────────────────────────────────
# ヘルパー関数
# ──────────────────────────────────────────────


def _to_class_name(key: str) -> str:
    """snake_case → PascalCaseAgent に変換する"""
    return "".join(part.capitalize() for part in key.split("_")) + "Agent"


def _generate_keywords(agent_key: str, agent_name: str, role: str) -> List[str]:
    """エージェントキー・名前・役割からキーワード候補を自動生成する"""
    seen = set()
    kws: List[str] = []

    def _add(w: str) -> None:
        w = w.strip()
        if w and w not in seen:
            seen.add(w)
            kws.append(w)

    _add(agent_key.replace("_", ""))
    _add(agent_key)
    _add(agent_name)
    # 役割文から2文字以上の単語を抽出
    for token in re.split(r"[\s・、。,]+", role):
        if len(token) >= 2:
            _add(token)

    return kws[:8]  # 最大8個


# ──────────────────────────────────────────────
# ファイル生成・更新関数
# ──────────────────────────────────────────────


def _generate_agent_file(
    agent_key: str,
    agent_name: str,
    role: str,
    agents_dir: str,
) -> str:
    """
    BaseAgent 継承のエージェントファイルを生成する。

    Returns:
        生成したファイルの絶対パス

    Raises:
        FileExistsError: 同名ファイルが既に存在する場合
    """
    module_name = f"{agent_key}_agent"
    filename = f"{module_name}.py"
    filepath = os.path.join(agents_dir, filename)

    if os.path.exists(filepath):
        raise FileExistsError(
            f"エージェントファイルが既に存在します: {filepath}\n"
            "上書きする場合は先にファイルを削除してください。"
        )

    content = _AGENT_TEMPLATE.format(
        agent_key=agent_key,
        agent_name=agent_name,
        role=role,
        class_name=_to_class_name(agent_key),
        module_name=module_name,
        filename=filename,
    )

    with open(filepath, "w", encoding="utf-8") as fh:
        fh.write(content)

    return filepath


def _update_agent_registry(
    main_py: str,
    agent_key: str,
    agent_name: str,
    role: str,
) -> None:
    """
    main.py の AGENT_REGISTRY に新エントリを追記する。

    挿入位置:
        "Claude によるルーティング" コメントブロック直前の
        AGENT_REGISTRY 閉じ括弧 `}` の手前。
    """
    with open(main_py, "r", encoding="utf-8") as fh:
        source = fh.read()

    # 既存チェック
    if f'"{agent_key}"' in source:
        print(f"  [skip] AGENT_REGISTRY に '{agent_key}' は既に存在します")
        return

    module_name = f"{agent_key}_agent"
    keywords = _generate_keywords(agent_key, agent_name, role)
    entry = _REGISTRY_ENTRY.format(
        agent_key=agent_key,
        agent_name=agent_name,
        role=role,
        module_name=module_name,
        keywords_json=json.dumps(keywords, ensure_ascii=False),
    )

    # AGENT_REGISTRY の末尾を特定する。
    # main.py では AGENT_REGISTRY の直後に "Claude によるルーティング" コメントがある。
    routing_marker = "# Claude によるルーティング"
    idx = source.find(routing_marker)
    if idx == -1:
        raise ValueError(
            "main.py に '# Claude によるルーティング' コメントが見つかりません。\n"
            "main.py の構造が想定と異なります。手動で追記してください。"
        )

    # routing_marker より前の部分で最後の `}` を探す（= AGENT_REGISTRY の閉じ括弧）
    before_routing = source[:idx]
    registry_close_pos = before_routing.rfind("}")
    if registry_close_pos == -1:
        raise ValueError("AGENT_REGISTRY の閉じ括弧 `}` が見つかりません。")

    # 閉じ括弧の手前に新エントリを差し込む
    new_source = (
        source[:registry_close_pos]
        + entry
        + source[registry_close_pos:]
    )

    with open(main_py, "w", encoding="utf-8") as fh:
        fh.write(new_source)


def _update_supporter_knowledge(
    supporter_py: str,
    agent_key: str,
    agent_name: str,
    role: str,
) -> None:
    """
    supporter_agent.py の SYSTEM_KNOWLEDGE に新エージェントの説明を追記する。

    挿入位置:
        「新機能を追加したいとき」セクション手前の `---` 区切りの直前。
        見つからない場合は SYSTEM_KNOWLEDGE 末尾（`=====...=====` 行）の直前。
    """
    with open(supporter_py, "r", encoding="utf-8") as fh:
        source = fh.read()

    # 既存チェック（エージェントキーが既に含まれている場合はスキップ）
    if f"/{agent_key}" in source or f"{agent_key}_agent" in source:
        print(f"  [skip] SYSTEM_KNOWLEDGE に '{agent_key}' は既に存在します")
        return

    module_name = f"{agent_key}_agent"
    filename = f"{module_name}.py"
    entry = _KNOWLEDGE_ENTRY.format(
        module_name=module_name,
        agent_name=agent_name,
        filename=filename,
        agent_key=agent_key,
        role=role,
        date=datetime.date.today().isoformat(),
    )

    # 優先: 「新機能を追加したいとき」セクション直前の `---\n\n` の前に挿入
    new_feature_marker = "【新機能を追加したいとき】"
    idx = source.find(new_feature_marker)
    if idx != -1:
        # marker 直前の `---\n\n` を探す
        before = source[:idx]
        sep_idx = before.rfind("---\n\n")
        if sep_idx != -1:
            insert_at = sep_idx  # `---\n\n` の直前に差し込む
            new_source = source[:insert_at] + entry + "\n" + source[insert_at:]
        else:
            # `---\n\n` が見つからない場合は marker の直前に差し込む
            new_source = source[:idx] + entry + "\n" + source[idx:]
    else:
        # フォールバック: SYSTEM_KNOWLEDGE の末尾区切り線の直前
        end_marker = "=" * 49 + "\n\"\"\""
        idx2 = source.rfind(end_marker)
        if idx2 == -1:
            print("  [skip] supporter_agent.py の挿入位置が見つかりません。手動で追記してください。")
            return
        new_source = source[:idx2] + entry + "\n" + source[idx2:]

    with open(supporter_py, "w", encoding="utf-8") as fh:
        fh.write(new_source)


# ──────────────────────────────────────────────
# マニフェスト連携
# ──────────────────────────────────────────────


def _load_manifest(manifest_path: str) -> dict:
    """AGENT_MANIFEST.json を読み込む。ファイルが存在しない場合は空カタログを返す。"""
    if not os.path.exists(manifest_path):
        return {"version": "1.0", "updated": "", "agents": []}
    with open(manifest_path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _check_manifest_duplicate(manifest: dict, agent_key: str) -> None:
    """
    マニフェスト内に同じ agent_key が存在する場合は DuplicateAgentError を送出する。

    Raises:
        ValueError: 重複が検出された場合
    """
    existing_keys = [a.get("key") for a in manifest.get("agents", [])]
    if agent_key in existing_keys:
        raise ValueError(
            f"エージェントキー '{agent_key}' は既に AGENT_MANIFEST.json に登録されています。\n"
            "別のキーを使用するか、既存エントリを確認してください。"
        )


def _update_manifest(
    manifest_path: str,
    agent_key: str,
    agent_name: str,
    role: str,
    apis: Optional[List[str]] = None,
) -> None:
    """
    AGENT_MANIFEST.json に新エージェントのエントリを追記して保存する。

    Args:
        apis: 使用するAPI名のリスト（省略時は ["anthropic"] のみ）
    """
    manifest = _load_manifest(manifest_path)

    new_entry = {
        "key": agent_key,
        "name": agent_name,
        "module": f"{agent_key}_agent",
        "desc": role,
        "responsibilities": [role],
        "apis": apis or ["anthropic"],
        "inherits_base": True,
        "status": "active",
        "created": datetime.date.today().isoformat(),
    }

    manifest["agents"].append(new_entry)
    manifest["updated"] = datetime.date.today().isoformat()

    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)


# ──────────────────────────────────────────────
# メイン API
# ──────────────────────────────────────────────


def create_agent(
    agent_key: str,
    agent_name: str,
    role: str,
    agents_dir: Optional[str] = None,
    main_py: Optional[str] = None,
    supporter_py: Optional[str] = None,
    manifest_path: Optional[str] = None,
    apis: Optional[List[str]] = None,
) -> dict:
    """
    エージェントを生成して関連ファイルを更新する。

    Args:
        agent_key    : 英数字・アンダースコアのキー（例: "interview_prep"）
        agent_name   : 日本語の表示名（例: "面接準備"）
        role         : 役割・説明文
        agents_dir   : 省略時は career_advisor/agents/
        main_py      : 省略時は career_advisor/main.py
        supporter_py : 省略時は career_advisor/agents/supporter_agent.py
        manifest_path: 省略時は docs/AGENT_MANIFEST.json
        apis         : 使用するAPI名リスト（マニフェストに記録）

    Returns:
        {"agent_file": str, "status": "success"}

    Raises:
        ValueError      : agent_key の形式が不正 / マニフェスト重複
        FileExistsError : 同名エージェントファイルが既に存在する
    """
    if not re.match(r"^[a-z][a-z0-9_]*$", agent_key):
        raise ValueError(
            f"agent_key '{agent_key}' は小文字英字で始まり、"
            "小文字英数字・アンダースコアのみ使用できます。"
        )

    agents_dir = agents_dir or _AGENTS_DIR
    main_py = main_py or _MAIN_PY
    supporter_py = supporter_py or _SUPPORTER_PY
    manifest_path = manifest_path or _MANIFEST_PATH

    sep = "=" * 52
    print(f"\n{sep}")
    print(f"  エージェント・ファクトリー")
    print(f"  key: {agent_key}  /  name: {agent_name}")
    print(sep)

    # 【事前チェック】マニフェストで重複確認（ファイル生成前に弾く）
    print("\n[0/4] マニフェストで重複チェック中...")
    manifest = _load_manifest(manifest_path)
    _check_manifest_duplicate(manifest, agent_key)
    print(f"  OK: '{agent_key}' は未登録です")

    # ① エージェントファイルを生成
    print("\n[1/4] エージェントファイルを生成中...")
    agent_file = _generate_agent_file(agent_key, agent_name, role, agents_dir)
    print(f"  完了: {agent_file}")

    # ② AGENT_REGISTRY を更新
    print("\n[2/4] AGENT_REGISTRY を更新中 (main.py)...")
    _update_agent_registry(main_py, agent_key, agent_name, role)
    print(f"  完了: '{agent_key}' を AGENT_REGISTRY に追記しました")

    # ③ SYSTEM_KNOWLEDGE を更新
    print("\n[3/4] SYSTEM_KNOWLEDGE を更新中 (supporter_agent.py)...")
    _update_supporter_knowledge(supporter_py, agent_key, agent_name, role)
    print(f"  完了: '{agent_name}' の説明を SYSTEM_KNOWLEDGE に追記しました")

    # ④ マニフェストを更新
    print("\n[4/4] AGENT_MANIFEST.json を更新中...")
    _update_manifest(manifest_path, agent_key, agent_name, role, apis)
    print(f"  完了: '{agent_key}' を AGENT_MANIFEST.json に登録しました")

    print(f"\n{'='*52}")
    print(f"  エージェント '{agent_name}' の生成が完了しました！")
    print(f"  起動コマンド: python3 career_advisor/agents/{agent_key}_agent.py")
    print(f"  または main.py で「{agent_key}」と入力")
    print("=" * 52 + "\n")

    return {"agent_file": agent_file, "status": "success"}


# ──────────────────────────────────────────────
# 対話モード
# ──────────────────────────────────────────────


def _interactive_mode() -> None:
    """引数なし起動時の対話モード"""
    sep = "=" * 52
    print(f"\n{sep}")
    print("  エージェント・ファクトリー（対話モード）")
    print(sep)
    print("\n新しいエージェントを生成します。")
    print("（中断: Ctrl+C）\n")

    try:
        agent_key = input("エージェントキー（英数字・アンダースコア）: ").strip().lower()
        if not re.match(r"^[a-z][a-z0-9_]*$", agent_key):
            print("エラー: キーは小文字英字で始まり、英数字・アンダースコアのみ使用できます")
            sys.exit(1)

        agent_name = input("エージェント名（日本語可）: ").strip()
        if not agent_name:
            print("エラー: エージェント名を入力してください")
            sys.exit(1)

        role = input("役割・説明（どんな業務を担当するか）: ").strip()
        if not role:
            print("エラー: 役割を入力してください")
            sys.exit(1)

        print(f"\n--- 生成内容 ---")
        print(f"  キー  : {agent_key}")
        print(f"  名前  : {agent_name}")
        print(f"  役割  : {role}")
        print(f"  ファイル: career_advisor/agents/{agent_key}_agent.py")
        confirm = input("\n実行しますか？ [y/N]: ").strip().lower()
        if confirm != "y":
            print("キャンセルしました")
            sys.exit(0)

        create_agent(agent_key, agent_name, role)

    except KeyboardInterrupt:
        print("\nキャンセルしました")
        sys.exit(0)


# ──────────────────────────────────────────────
# CLI エントリポイント
# ──────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AgentFactory — BaseAgent 継承エージェントを自動生成する",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """\
            使用例:
              # 引数で直接指定
              python3 tools/agent_factory.py \\
                --key interview_prep \\
                --name "面接準備" \\
                --role "学生の面接準備を対話形式でサポートする"

              # 対話モード（引数省略）
              python3 tools/agent_factory.py
            """
        ),
    )
    parser.add_argument("--key", help="エージェントキー（例: interview_prep）")
    parser.add_argument("--name", help="エージェント名（例: 面接準備）")
    parser.add_argument("--role", help="役割説明（例: 学生の面接準備をサポートする）")
    args = parser.parse_args()

    if args.key and args.name and args.role:
        try:
            create_agent(args.key, args.name, args.role)
        except (ValueError, FileExistsError) as exc:
            print(f"エラー: {exc}")
            sys.exit(1)
    else:
        _interactive_mode()


if __name__ == "__main__":
    main()
