#!/usr/bin/env python3
"""
name_validator.py — Agent命名規則バリデーター

## 命名規則
  [Domain]_[Role]_[Target]
  例: hr_executor_sf_bulk / hr_watcher_notion_company / hr_processor_coaching

## 使い方（新エージェント追加時に実行）
  python3 business/agents/name_validator.py --check hr_executor_new_agent
  python3 business/agents/name_validator.py --check-all      # registry.json 全件検証
  python3 business/agents/name_validator.py --suggest "SF一括書き込み担当"
"""

import json
import re
import sys
import argparse
from pathlib import Path

# ── 定数 ──────────────────────────────────────────────────────────────
REGISTRY_PATH = Path(__file__).parent / "registry.json"

VALID_DOMAINS = {"hr"}

VALID_ROLES = {"watcher", "parser", "processor", "executor", "orchestrator"}

# canonical_name の正規表現: [domain]_[role]_[target]
# target は英小文字・数字・アンダースコアの組み合わせ（最低1セグメント）
NAME_PATTERN = re.compile(r"^([a-z]+)_([a-z]+)_([a-z0-9_]+)$")

# ── バリデーション関数 ─────────────────────────────────────────────────

def validate_name(name: str) -> tuple[bool, str]:
    """
    エージェント名を検証する。

    Returns:
        (is_valid, error_message)
    """
    m = NAME_PATTERN.match(name)
    if not m:
        return False, (
            f"形式エラー: '{name}' は [Domain]_[Role]_[Target] 形式に適合しません。\n"
            f"  正しい例: hr_executor_sf_bulk"
        )

    domain, role, target = m.group(1), m.group(2), m.group(3)

    if domain not in VALID_DOMAINS:
        return False, (
            f"ドメインエラー: '{domain}' は未登録ドメインです。\n"
            f"  有効なドメイン: {sorted(VALID_DOMAINS)}"
        )

    if role not in VALID_ROLES:
        return False, (
            f"ロールエラー: '{role}' は無効なロールです。\n"
            f"  有効なロール: {sorted(VALID_ROLES)}"
        )

    if len(target) < 2:
        return False, f"ターゲット名が短すぎます: '{target}' (最低2文字)"

    return True, "OK"


def check_duplicate(name: str, registry: dict) -> tuple[bool, str]:
    """
    レジストリ内に同一IDが存在しないか検証する。

    Returns:
        (is_duplicate, existing_agent_description)
    """
    for agent in registry.get("agents", []):
        if agent["id"] == name:
            return True, (
                f"重複エラー: '{name}' は既に登録済みです。\n"
                f"  既存: {agent['description']}\n"
                f"  既存モジュール: {agent['legacy_module']}\n"
                f"  → 新規作成ではなく「拡張」または「統合」を検討してください。"
            )
    return False, ""


def find_similar(name: str, registry: dict) -> list[dict]:
    """
    名前・ターゲットが類似するエージェントを検索する（衝突候補の提示）。
    """
    m = NAME_PATTERN.match(name)
    if not m:
        return []

    _, role, target = m.group(1), m.group(2), m.group(3)
    target_words = set(target.split("_"))

    similar = []
    for agent in registry.get("agents", []):
        existing_target = agent["id"].split("_", 2)[-1] if "_" in agent["id"] else ""
        existing_words = set(existing_target.split("_"))
        if target_words & existing_words:  # 共通単語あり
            similar.append(agent)

    return similar


# ── エントリポイント ───────────────────────────────────────────────────

def load_registry() -> dict:
    if not REGISTRY_PATH.exists():
        print(f"⚠️  registry.json が見つかりません: {REGISTRY_PATH}", file=sys.stderr)
        sys.exit(1)
    with open(REGISTRY_PATH, encoding="utf-8") as f:
        return json.load(f)


def cmd_check(name: str) -> None:
    """単一エージェント名を検証"""
    registry = load_registry()

    valid, msg = validate_name(name)
    if not valid:
        print(f"❌ {msg}")
        sys.exit(1)

    dup, dup_msg = check_duplicate(name, registry)
    if dup:
        print(f"❌ {dup_msg}")
        sys.exit(1)

    similar = find_similar(name, registry)
    if similar:
        print(f"⚠️  類似エージェントが存在します（統合を検討してください）:")
        for a in similar:
            print(f"   - {a['id']}: {a['description']}")
        print()

    print(f"✅ '{name}' — 命名規則OK・重複なし。registry.json に追加できます。")


def cmd_check_all() -> None:
    """registry.json の全エージェントを検証"""
    registry = load_registry()
    agents = registry.get("agents", [])
    errors = []
    seen_ids: set[str] = set()

    for agent in agents:
        name = agent.get("id", "")
        valid, msg = validate_name(name)
        if not valid:
            errors.append(f"  [{name}] {msg}")
        if name in seen_ids:
            errors.append(f"  [{name}] 重複IDが存在します")
        seen_ids.add(name)

    if errors:
        print(f"❌ {len(errors)} 件の問題が見つかりました:")
        for e in errors:
            print(e)
        sys.exit(1)
    else:
        print(f"✅ 全 {len(agents)} エージェントの命名規則・重複チェック通過。")


def cmd_suggest(description: str) -> None:
    """日本語の説明文から命名候補を提示"""
    # キーワードマッピング（簡易版）
    role_hints = {
        "watcher":      ["監視", "ポーリング", "検知", "watch"],
        "parser":       ["抽出", "解析", "パース", "parse", "読み込み"],
        "processor":    ["推論", "マッピング", "生成", "変換", "処理"],
        "executor":     ["書き込み", "送信", "実行", "登録", "更新", "executor"],
        "orchestrator": ["束ねる", "ワンストップ", "フル", "一括制御"],
    }
    domain_hints = {"hr": ["HR", "就活", "学生", "企業", "SF", "Notion", "Slack"]}

    detected_role = "processor"
    for role, hints in role_hints.items():
        if any(h in description for h in hints):
            detected_role = role
            break

    print(f"📝 説明: '{description}'")
    print(f"   推定ロール: {detected_role}")
    print(f"   命名候補例:")
    print(f"     hr_{detected_role}_<target>  ← <target> を英語スネークケースで命名")
    print(f"   検証コマンド: python3 business/agents/name_validator.py --check hr_{detected_role}_<target>")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Agent命名規則バリデーター",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check",     metavar="NAME", help="単一エージェント名を検証")
    group.add_argument("--check-all", action="store_true", help="registry.json 全件検証")
    group.add_argument("--suggest",   metavar="DESCRIPTION", help="説明文から命名候補を提示")

    args = parser.parse_args()

    if args.check:
        cmd_check(args.check)
    elif args.check_all:
        cmd_check_all()
    elif args.suggest:
        cmd_suggest(args.suggest)


if __name__ == "__main__":
    main()
