"""
Catalog Updater Agent — ai-empire 品質管理層

agents/ ディレクトリをスキャンして AGENT_MANIFEST.json を自動更新する。

機能:
  1. エージェント自動検出      — agents/**/*.py を走査
  2. メタデータ抽出            — docstring から canonical_id/bu/layer/desc を解析
  3. AGENT_MANIFEST.json 更新  — 新規エージェントの追加・既存の同期
  4. Markdown カタログ生成     — knowledge/ に要約 MD を出力
  5. dashboard_logger 連携     — 更新結果を Update_Log に自動記録

使い方:
  python3 agents/quality/catalog_updater/agent.py         # 全エージェント同期
  python3 agents/quality/catalog_updater/agent.py --dry-run  # 差分確認のみ
  python3 agents/quality/catalog_updater/agent.py --gen-md   # MD生成も実行

BU: Quality / Layer: Catalog
canonical_id: quality_catalog_updater
"""

from __future__ import annotations

import ast
import json
import logging
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# ─── パス設定 ─────────────────────────────────────────────────────────────────
AI_EMPIRE = Path(__file__).parent.parent.parent.parent  # ai-empire/
load_dotenv(AI_EMPIRE / "config" / ".env")

sys.path.insert(0, str(AI_EMPIRE))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("CatalogUpdater")

MANIFEST_PATH = AI_EMPIRE / "knowledge" / "hr_support" / "AGENT_MANIFEST.json"
CATALOG_MD_PATH = AI_EMPIRE / "knowledge" / "hr_support" / "AGENT_CATALOG.md"

# ─── エージェント検出除外 ─────────────────────────────────────────────────────
EXCLUDE_FILES = {"__init__.py", "setup.py", "conftest.py"}
EXCLUDE_DIRS = {"__pycache__", ".venv", "venv", "node_modules", ".git"}


# ─── データクラス ─────────────────────────────────────────────────────────────

@dataclass
class AgentMeta:
    canonical_id: str
    name: str
    bu: str
    layer: str
    desc: str
    apis: list[str] = field(default_factory=list)
    status: str = "active"
    filepath: str = ""

    def to_manifest_entry(self) -> dict:
        return {
            "canonical_id": self.canonical_id,
            "name": self.name,
            "bu": self.bu,
            "layer": self.layer,
            "desc": self.desc,
            "apis": self.apis,
            "status": self.status,
        }


# ─── メタデータ抽出 ───────────────────────────────────────────────────────────

def _extract_from_docstring(docstring: str, filepath: Path) -> dict[str, str]:
    """docstring のメタコメントを解析"""
    meta: dict[str, str] = {}
    lines = docstring.splitlines()

    for line in lines:
        line = line.strip()
        # "BU: Quality / Layer: Review" 形式
        bu_match = re.search(r"BU:\s*([^/\n]+?)(?:\s*/|$)", line)
        if bu_match:
            meta["bu"] = bu_match.group(1).strip()
        layer_match = re.search(r"Layer:\s*(\S+)", line)
        if layer_match:
            meta["layer"] = layer_match.group(1).strip()
        id_match = re.search(r"canonical_id:\s*(\S+)", line)
        if id_match:
            meta["canonical_id"] = id_match.group(1).strip()

    return meta


def _infer_from_path(filepath: Path) -> dict[str, str]:
    """ファイルパスからメタデータを推定"""
    parts = filepath.parts
    meta: dict[str, str] = {}

    # bu を推定 (agents/<bu>/)
    if "agents" in parts:
        idx = list(parts).index("agents")
        if idx + 1 < len(parts):
            bu_dir = parts[idx + 1]
            bu_map = {
                "hr_support": "HRsupport",
                "rpo": "RPO",
                "quality": "品質管理",
                "sales": "Sales",
                "management": "経営管理",
                "strategy": "経営戦略",
            }
            meta["bu"] = bu_map.get(bu_dir, bu_dir)

    # layer を推定 (agents/<bu>/<layer>/<name>/agent.py)
    if "quality" in parts:
        idx = list(parts).index("quality")
        if idx + 1 < len(parts):
            meta["layer"] = parts[idx + 1].replace("_", " ").title()

    return meta


def extract_agent_meta(filepath: Path) -> AgentMeta | None:
    """Python ファイルからエージェントメタデータを抽出"""
    if filepath.name in EXCLUDE_FILES:
        return None
    if any(ex in filepath.parts for ex in EXCLUDE_DIRS):
        return None

    try:
        source = filepath.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        logger.debug(f"読み込み失敗: {filepath}: {e}")
        return None

    # run() パブリックAPIが無ければエージェントではないと判断
    if "def run(" not in source and "def execute(" not in source and "def main(" not in source:
        return None

    # docstring 解析
    module_docstring = ""
    try:
        tree = ast.parse(source)
        if (tree.body and isinstance(tree.body[0], ast.Expr)
                and isinstance(tree.body[0].value, ast.Constant)):
            module_docstring = str(tree.body[0].value.value)
    except SyntaxError:
        pass

    meta_from_doc = _extract_from_docstring(module_docstring, filepath)
    meta_from_path = _infer_from_path(filepath)

    # docstring の最初の行を description として使う
    desc_line = ""
    for line in module_docstring.splitlines():
        line = line.strip()
        if line and not line.startswith(("BU:", "Layer:", "canonical_id:", "機能:", "使い方:")):
            desc_line = line[:80]
            break

    # canonical_id を決定（docstring > ファイル名ベース）
    canonical_id = meta_from_doc.get("canonical_id") or _path_to_canonical(filepath)
    name = _path_to_name(filepath)
    bu = meta_from_doc.get("bu") or meta_from_path.get("bu", "Unknown")
    layer = meta_from_doc.get("layer") or meta_from_path.get("layer", "Executor")

    return AgentMeta(
        canonical_id=canonical_id,
        name=name,
        bu=bu,
        layer=layer,
        desc=desc_line or f"{name} エージェント",
        apis=_detect_apis(source),
        status="active",
        filepath=str(filepath),
    )


def _path_to_canonical(filepath: Path) -> str:
    """ファイルパスから canonical_id を生成"""
    parts = list(filepath.parts)
    if "agents" in parts:
        idx = parts.index("agents")
        sub = parts[idx + 1:]
        # agent.py を除く
        sub = [p.replace(".py", "") for p in sub if p not in ("agent.py",)]
        return "_".join(sub[:3])
    return filepath.stem


def _path_to_name(filepath: Path) -> str:
    """ファイルパスから表示名を生成"""
    if filepath.name == "agent.py":
        return filepath.parent.name.replace("_", " ").title()
    return filepath.stem.replace("_", " ").title()


def _detect_apis(source: str) -> list[str]:
    """ソースコードから使用APIを検出"""
    apis = []
    api_patterns = {
        "Claude": r"anthropic|claude",
        "SF": r"salesforce|simple_salesforce",
        "Notion": r"notion",
        "Slack": r"slack",
        "GSheets": r"gspread|google.sheets",
        "Gmail": r"gmail|google.auth",
        "GitHub": r"PyGithub|github",
        "OpenAI": r"openai",
    }
    source_lower = source.lower()
    for api_name, pattern in api_patterns.items():
        if re.search(pattern, source_lower):
            apis.append(api_name)
    return apis or ["—"]


# ─── AGENT_MANIFEST.json 更新 ─────────────────────────────────────────────────

def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {
        "version": "1.0",
        "updated": datetime.now().strftime("%Y-%m-%d"),
        "description": "Tokumori — 全エージェントカタログ",
        "agents": [],
    }


def sync_manifest(
    discovered: list[AgentMeta],
    dry_run: bool = False,
) -> tuple[list[str], list[str]]:
    """
    AGENT_MANIFEST.json に新規エージェントを追加・既存エントリのステータスを同期。

    Returns:
        (added_ids, updated_ids)
    """
    manifest = load_manifest()
    existing = {a["canonical_id"]: a for a in manifest["agents"]}

    added_ids: list[str] = []
    updated_ids: list[str] = []

    for agent in discovered:
        if agent.canonical_id not in existing:
            entry = agent.to_manifest_entry()
            if not dry_run:
                manifest["agents"].append(entry)
            added_ids.append(agent.canonical_id)
            logger.info(f"  ➕ 追加: {agent.canonical_id} ({agent.bu}/{agent.layer})")
        else:
            # status が design/planned → active に更新
            current = existing[agent.canonical_id]
            if current.get("status") in ("design", "planned", "inactive"):
                if not dry_run:
                    current["status"] = "active"
                    current["desc"] = agent.desc
                    current["apis"] = agent.apis
                updated_ids.append(agent.canonical_id)
                logger.info(f"  🔄 更新: {agent.canonical_id} → active")

    if not dry_run and (added_ids or updated_ids):
        manifest["updated"] = datetime.now().strftime("%Y-%m-%d")
        manifest["description"] = (
            f"Tokumori — 全エージェントカタログ（{len(manifest['agents'])}体・BU別構成）"
        )
        MANIFEST_PATH.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info(f"AGENT_MANIFEST.json 更新: {MANIFEST_PATH}")

    return added_ids, updated_ids


# ─── Markdown カタログ生成 ────────────────────────────────────────────────────

def generate_markdown_catalog(manifest: dict) -> str:
    agents = manifest.get("agents", [])
    updated = manifest.get("updated", datetime.now().strftime("%Y-%m-%d"))
    total = len(agents)

    # BU別グループ化
    by_bu: dict[str, list[dict]] = {}
    for a in agents:
        by_bu.setdefault(a["bu"], []).append(a)

    lines = [
        f"# Tokumori エージェントカタログ",
        f"",
        f"> 自動生成: {updated} / 総エージェント数: {total}体",
        f"",
    ]

    status_icons = {
        "active": "✅",
        "design": "🔷",
        "planned": "📋",
        "inactive": "⬛",
        "beta": "🔶",
    }

    for bu, bu_agents in sorted(by_bu.items()):
        lines.append(f"## {bu} ({len(bu_agents)}体)")
        lines.append("")
        lines.append("| エージェント | Layer | 説明 | API | Status |")
        lines.append("|---|---|---|---|---|")
        for a in bu_agents:
            icon = status_icons.get(a.get("status", "design"), "❓")
            apis = ", ".join(a.get("apis", ["—"]))
            lines.append(
                f"| {a['name']} | {a['layer']} | {a['desc']} | {apis} | {icon} {a['status']} |"
            )
        lines.append("")

    return "\n".join(lines)


# ─── dashboard_logger 連携 ────────────────────────────────────────────────────

def _log_to_dashboard(added: list[str], updated: list[str]) -> None:
    try:
        from utils.dashboard_logger import log_update
        log_update(
            icon="🔄 更新",
            summary=f"AGENT_MANIFEST.json 同期: 追加{len(added)}件 / 更新{len(updated)}件",
            targets="knowledge/hr_support/AGENT_MANIFEST.json",
            details=(
                f"①新規追加: {', '.join(added) or 'なし'} "
                f"②ステータス更新: {', '.join(updated) or 'なし'}"
            ),
        )
    except Exception as e:
        logger.debug(f"dashboard_logger 記録スキップ: {e}")


# ─── パブリックAPI ────────────────────────────────────────────────────────────

def run(
    dry_run: bool = False,
    gen_md: bool = False,
    log_dashboard: bool = True,
) -> dict:
    """
    パブリックAPI

    Args:
        dry_run: Trueなら差分表示のみ（ファイル変更なし）
        gen_md: MarkdownカタログをCATALOG_MD_PATHに出力するか
        log_dashboard: Update_Logに記録するか
    """
    logger.info(f"カタログ更新開始 (dry_run={dry_run})")

    # エージェント検出
    discovered: list[AgentMeta] = []
    for py_file in sorted((AI_EMPIRE / "agents").rglob("*.py")):
        if any(ex in py_file.parts for ex in EXCLUDE_DIRS):
            continue
        meta = extract_agent_meta(py_file)
        if meta:
            discovered.append(meta)

    logger.info(f"エージェント検出: {len(discovered)}体")

    # マニフェスト同期
    added, updated = sync_manifest(discovered, dry_run=dry_run)

    # Markdown 生成
    if gen_md and not dry_run:
        manifest = load_manifest()
        md_content = generate_markdown_catalog(manifest)
        CATALOG_MD_PATH.write_text(md_content, encoding="utf-8")
        logger.info(f"Markdownカタログ出力: {CATALOG_MD_PATH}")

    # 結果表示
    print(f"\n{'='*60}")
    print(f"  カタログ更新{'[DRY-RUN] ' if dry_run else ''}結果")
    print(f"{'='*60}")
    print(f"  検出エージェント: {len(discovered)}体")
    print(f"  新規追加: {len(added)}件 {added}")
    print(f"  ステータス更新: {len(updated)}件 {updated}")
    print(f"{'='*60}\n")

    if log_dashboard and not dry_run and (added or updated):
        _log_to_dashboard(added, updated)

    return {
        "discovered": len(discovered),
        "added": len(added),
        "updated": len(updated),
        "dry_run": dry_run,
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="ai-empire エージェントカタログ更新")
    parser.add_argument("--dry-run", action="store_true", help="差分確認のみ（変更なし）")
    parser.add_argument("--gen-md", action="store_true", help="Markdownカタログも生成")
    parser.add_argument("--no-log", action="store_true", help="Update_Log への記録をスキップ")
    args = parser.parse_args()

    result = run(dry_run=args.dry_run, gen_md=args.gen_md, log_dashboard=not args.no_log)
    print(f"完了: {result['discovered']}体検出 / "
          f"追加{result['added']}件 / 更新{result['updated']}件")
