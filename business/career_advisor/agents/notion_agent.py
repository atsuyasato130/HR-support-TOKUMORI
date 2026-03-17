#!/usr/bin/env python3
"""
Notionエージェント

機能:
  - 企業紹介文生成（Notion企業DB → LINE送信用）
  - 企業DB検索・情報取得
  - 社外/社内MTG 議事録作成（Notion議事録ページ配下に子ページ作成）

使い方:
  python3 notion_agent.py
  from agents.notion_agent import run, create_meeting_minutes
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import date
import anthropic
import httpx
import requests
from dotenv import load_dotenv

BASE = os.path.dirname(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE, "../config/.env"))

ANTHROPIC_API_KEY     = os.environ["ANTHROPIC_API_KEY"]
NOTION_API_KEY        = os.environ["NOTION_API_KEY"]
NOTION_DB_ID          = "5cdbd39197f94db7b7e275d317166bfd"
NOTION_MINUTES_PAGE   = "2bc48452bd2581c2bd93f36b7d2acbd8"  # 議事録ルートページ

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

# ──────────────────────────────────────────────
# Notion プロパティ名マッピング
# ──────────────────────────────────────────────

FIELD_CANDIDATES: dict[str, list[str]] = {
    "企業名":     ["会社名", "企業名", "Name", "名前", "name"],
    "HP":         ["ウェブサイト", "HP", "ホームページ", "URL", "url", "Website", "website", "サイト"],
    "事業概要":   ["事業内容", "事業概要", "概要", "会社概要", "business"],
    "選考フロー": ["選考フロー", "選考", "選考ステップ", "採用フロー", "フロー"],
    "説明会日程": ["説明会日程", "説明会", "選考案内", "日程", "イベント", "説明会・選考", "選考日程"],
}


def _match_property(prop_name: str, candidates: list[str]) -> bool:
    name_norm = prop_name.lower().replace(" ", "").replace("　", "")
    for c in candidates:
        c_norm = c.lower().replace(" ", "").replace("　", "")
        if c_norm in name_norm or name_norm in c_norm:
            return True
    return False


def get_db_properties() -> dict[str, str]:
    """DBスキーマを取得し、内部キー → 実際のNotion列名 のマッピングを返す"""
    url = f"https://api.notion.so/v1/databases/{NOTION_DB_ID}"
    r = requests.get(url, headers=NOTION_HEADERS, timeout=15)
    r.raise_for_status()
    props = r.json().get("properties", {})

    mapping: dict[str, str] = {}
    for field_key, candidates in FIELD_CANDIDATES.items():
        for prop_name in props:
            if _match_property(prop_name, candidates):
                mapping[field_key] = prop_name
                break

    missing = [k for k in FIELD_CANDIDATES if k not in mapping]
    if missing:
        print(f"\n⚠️  以下のフィールドがNotionで見つかりませんでした: {', '.join(missing)}")
        print(f"   利用可能なプロパティ: {', '.join(props.keys())}\n")

    return mapping


def extract_text(prop: dict) -> str:
    """Notionプロパティから文字列を抽出"""
    t = prop.get("type", "")
    if t == "title":
        return "".join(b.get("plain_text", "") for b in prop.get("title", []))
    if t == "rich_text":
        return "".join(b.get("plain_text", "") for b in prop.get("rich_text", []))
    if t == "url":
        return prop.get("url") or ""
    if t == "select":
        s = prop.get("select")
        return s.get("name", "") if s else ""
    if t == "multi_select":
        return "、".join(o.get("name", "") for o in prop.get("multi_select", []))
    if t == "date":
        d = prop.get("date")
        if d:
            start = d.get("start", "")
            end   = d.get("end", "")
            return f"{start}〜{end}" if end else start
        return ""
    if t == "email":
        return prop.get("email") or ""
    if t == "phone_number":
        return prop.get("phone_number") or ""
    return ""


def search_companies(company_names: list[str], prop_mapping: dict[str, str]) -> list[dict[str, str]]:
    """企業名リストでNotionDBを検索し、各フィールドの値を返す"""
    results = []
    title_prop = prop_mapping.get("企業名", "名前")

    for name in company_names:
        name = name.strip()
        if not name:
            continue

        payload = {
            "filter": {
                "property": title_prop,
                "title": {"contains": name},
            }
        }
        url = f"https://api.notion.so/v1/databases/{NOTION_DB_ID}/query"
        r = requests.post(url, headers=NOTION_HEADERS, json=payload, timeout=15)
        r.raise_for_status()
        pages = r.json().get("results", [])

        if not pages:
            print(f"  ⚠️  [{name}] はNotionで見つかりませんでした。スキップします。")
            continue

        page  = pages[0]
        props = page.get("properties", {})

        row: dict[str, str] = {}
        for field_key, notion_key in prop_mapping.items():
            row[field_key] = extract_text(props[notion_key]) if notion_key in props else ""

        if not row.get("企業名"):
            row["企業名"] = name

        results.append(row)

    return results


# ──────────────────────────────────────────────
# おすすめポイント AI 生成
# ──────────────────────────────────────────────

_RECOMMEND_SYSTEM = """あなたはキャリアアドバイザーのアシスタントです。
以下のルールで「おすすめポイント」を生成してください。

【ルール】
- 今の就活生のトレンド（成長環境・裁量・安定性・福利厚生・社風・リモート・若手活躍など）を踏まえる
- 提供された企業情報から具体的に読み取れる魅力を記述する（抽象的なコピーはNG）
- 3〜5点を箇条書き。各ポイントは1〜2文で完結
- 絵文字は使わない
- 出力はポイントのみ（見出し・説明は不要）
"""


def generate_recommend_points(company_data: dict[str, str]) -> str:
    """おすすめポイントをAIで生成（▶ 箇条書き形式）"""
    prompt = f"""
以下の企業情報をもとに、就活生向けのおすすめポイントを生成してください。

企業名：{company_data.get('企業名', '')}
事業概要：{company_data.get('事業概要', '')}
選考フロー：{company_data.get('選考フロー', '')}
HP：{company_data.get('HP', '')}

各ポイントは「▶ 」で始めてください。
"""
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        system=_RECOMMEND_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


# ──────────────────────────────────────────────
# フォーマット組み立て
# ──────────────────────────────────────────────

def _filter_schedule(raw: str, max_count: int = 7) -> str:
    """説明会日程テキストから未来の日程を最大 max_count 件抽出して返す"""
    today = date.today()
    date_pattern = re.compile(r"(\d{1,2})[/／](\d{1,2})")
    lines = raw.splitlines()
    future_lines: list[tuple] = []
    url_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("http") or stripped.startswith("https"):
            url_lines.append(stripped)
            continue
        m = date_pattern.search(stripped)
        if m:
            try:
                month, day = int(m.group(1)), int(m.group(2))
                year = today.year
                d = date(year, month, day)
                if d < today:
                    d = date(year + 1, month, day)
                future_lines.append((d, stripped))
            except ValueError:
                pass

    future_lines.sort(key=lambda x: x[0])
    result_lines = [l for _, l in future_lines[:max_count]]

    if url_lines:
        result_lines.append("\nその他日程はこちら👇")
        result_lines.extend(url_lines)

    return "\n".join(result_lines) if result_lines else raw


def format_introduction(company_data: dict[str, str], recommend_points: str) -> str:
    """LINE送信用企業紹介文を生成"""
    name     = company_data.get("企業名", "")
    hp       = company_data.get("HP", "") or "ー"
    overview = company_data.get("事業概要", "") or "ー"
    flow     = company_data.get("選考フロー", "") or "ー"
    raw_schedule = company_data.get("説明会日程", "") or ""
    schedule = _filter_schedule(raw_schedule) if raw_schedule else "ー"

    lines = [
        "━━━━━━━━━━━━━━━━━━",
        f"🏢 {name}",
        "━━━━━━━━━━━━━━━━━━",
        "",
        "🌐 HP",
        hp,
        "",
        "📋 事業概要",
        overview,
        "",
        "🔄 選考フロー",
        flow,
        "",
        "✨ おすすめポイント",
        recommend_points,
        "",
        "📅 説明会・選考案内",
        schedule,
    ]
    return "\n".join(lines)


def copy_to_clipboard(text: str) -> bool:
    try:
        subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
        return True
    except Exception as e:
        print(f"\n[ERROR] クリップボードコピー失敗: {e}")
        return False


def parse_company_names(lines: list[str]) -> list[str]:
    """改行・カンマ・読点で区切って企業名リストを返す（重複除去）"""
    raw: list[str] = []
    for line in lines:
        raw.extend(n.strip() for n in re.split(r"[,、]", line) if n.strip())

    seen: set[str] = set()
    result: list[str] = []
    for n in raw:
        if n not in seen:
            seen.add(n)
            result.append(n)
    return result


# ──────────────────────────────────────────────
# 議事録作成（Notion DB レコード）
# DB: 議事録(Int / Ext)  ID: 2bc48452bd258007838cc3c707c953c1
# テンプレート構成: 目的 / アジェンダ / 議事録 / 決定事項・ネクストアクション / AI議事録
# ──────────────────────────────────────────────

NOTION_MINUTES_DB = "2bc48452bd258007838cc3c707c953c1"  # 議事録(Int / Ext) DB

# プロジェクト有効値: コンサルティング/RPO/中途紹介/新卒紹介/Sales/Ops/Corporate/Recruitment/Fcst/strategy
_MINUTES_SYSTEM = """あなたは優秀なビジネスアシスタントです。
以下のルールで会議の議事録を Notion ブロック JSON 形式で生成してください。

【ルール】
- MTGに参加していない第三者が読んでも内容の詳細を把握できるレベルに詳しく書く
- 事実と発言内容を正確に反映する（意見の主語を明示する）
- テンプレート構成に従う（下記参照）
- 出力は Notion ブロックの JSON 配列のみ（```json などのコードフェンスは不要）
- 使用できるブロックタイプ: heading_1, paragraph, bulleted_list_item, to_do, divider
- to_do は「決定事項 / ネクストアクション」セクションで使用し、checked は false にする

【テンプレート構成】
1. heading_1「目的」→ bullet で目的を2〜3点
2. divider
3. heading_1「アジェンダ」→ bullet で議題を箇条書き
4. divider
5. heading_1「議事録」→ 会議情報（日時・参加者・tldv URL）を bullet で記載後、各議題ごとに heading_1 + bullet で詳細を記述
6. divider
7. heading_1「決定事項 / ネクストアクション」→ to_do ブロックで全アクションを列挙（担当者を先頭に記載）
8. divider
9. heading_1「AI 議事録」→ bullet で「本議事録はtldv議事録テキストをAIが構造化」+ tldv URL
"""

def _nb_h1(text: str) -> dict:
    return {"object": "block", "type": "heading_1",
            "heading_1": {"rich_text": [{"type": "text", "text": {"content": text}}]}}

def _nb_h2(text: str) -> dict:
    return {"object": "block", "type": "heading_2",
            "heading_2": {"rich_text": [{"type": "text", "text": {"content": text}}]}}

def _nb_bullet(text: str) -> dict:
    return {"object": "block", "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": text}}]}}

def _nb_todo(text: str) -> dict:
    return {"object": "block", "type": "to_do",
            "to_do": {"rich_text": [{"type": "text", "text": {"content": text}}], "checked": False}}

def _nb_divider() -> dict:
    return {"object": "block", "type": "divider", "divider": {}}

def _nb_p(text: str) -> dict:
    return {"object": "block", "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": text}}]}}


# ──────────────────────────────────────────────
# 企業DBブラッシュアップ（議事録 → 企業DB自動更新）
# ──────────────────────────────────────────────

_COMPANY_UPDATE_SYSTEM = """あなたはキャリアアドバイザーのアシスタントです。
会議議事録テキストから、指定企業の採用情報として更新すべき内容を抽出してください。

【抽出対象フィールド】
- 選考フロー: 面接の段階・内容・評価基準（具体的に）
- 採用要件: 学歴・スキル・資質の条件
- 学生へ伝える魅力ポイント: 就活生向けの訴求点
- 強み / 訴求ポイント: 企業の強み（CA向け）
- 競合他社・バッティング企業: 競合として言及された企業名

【出力形式】
JSON オブジェクト。更新すべき情報がないフィールドは含めない。
例: {"選考フロー": "一次: コミュ力確認\n二次: 行動量・思考力\n最終: 就活軸の論理性", "採用要件": "面接レベル次第で学歴不問"}

コードフェンス不要。JSON のみ出力。
"""


def search_company_in_db(company_name: str) -> tuple[str, str] | tuple[None, None]:
    """
    企業名で直紹介リスト DB を検索し (page_id, current_flow) を返す。
    見つからない場合は (None, None)。
    """
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    payload = {
        "filter": {"property": "会社名", "title": {"contains": company_name}},
        "page_size": 1,
    }
    resp = httpx.post(
        f"https://api.notion.com/v1/databases/{NOTION_DB_ID}/query",
        headers=headers, json=payload, timeout=15,
    )
    resp.raise_for_status()
    results = resp.json().get("results", [])
    if not results:
        return None, None
    page = results[0]
    page_id = page["id"]
    # 現在の選考フローを取得
    current_flow = "".join(
        b.get("plain_text", "")
        for b in page.get("properties", {}).get("選考フロー", {}).get("rich_text", [])
    )
    return page_id, current_flow


def extract_company_updates(company_name: str, tldv_text: str, current_flow: str) -> dict:
    """Claude で議事録から企業DB更新情報を抽出する"""
    prompt = f"""
対象企業: {company_name}

【現在の選考フロー（既存値）】
{current_flow or "（未設定）"}

【会議議事録】
{tldv_text}

上記議事録から {company_name} に関する採用情報を抽出してください。
既存値がある場合は、新情報をマージして上書きする内容を返してください。
"""
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=_COMPANY_UPDATE_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
    return json.loads(raw)


def update_company_db(page_id: str, updates: dict) -> None:
    """企業DBのページを更新する（rich_text フィールドのみ対応）"""
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    props: dict = {}
    for field, value in updates.items():
        if isinstance(value, str) and value.strip():
            props[field] = {"rich_text": [{"text": {"content": value[:2000]}}]}
    if not props:
        return
    httpx.patch(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers=headers,
        json={"properties": props},
        timeout=15,
    )


def brushup_company_db_from_minutes(company_name: str, tldv_text: str) -> str:
    """
    会議議事録から企業情報を抽出し、企業DB を自動更新する。
    Returns: 処理結果メッセージ
    """
    # 企業名の揺れに対応（エムスリーキャリア → M3キャリア等も検索）
    aliases = [company_name]
    # 一般的な略称マッピング
    alias_map = {
        "エムスリーキャリア": ["エムスリーキャリア", "M3キャリア", "m3career"],
    }
    for key, vals in alias_map.items():
        if key in company_name:
            aliases = vals
            break

    page_id, current_flow = None, None
    for alias in aliases:
        page_id, current_flow = search_company_in_db(alias)
        if page_id:
            break

    if not page_id:
        return f"⚠️ 企業DB に「{company_name}」が見つかりませんでした。手動で確認してください。"

    print(f"  [企業DB] {company_name} を検索中... 発見 (ID: {page_id[:8]}...)")
    updates = extract_company_updates(company_name, tldv_text, current_flow or "")

    if not updates:
        return f"ℹ️ 「{company_name}」に関する更新情報が見つかりませんでした。"

    update_company_db(page_id, updates)
    updated_fields = list(updates.keys())
    return f"✅ 企業DB「{company_name}」を更新しました。更新フィールド: {', '.join(updated_fields)}"


def generate_minutes_blocks(
    meeting_type: str,
    company: str,
    date_str: str,
    participants: str,
    tldv_url: str,
    tldv_text: str,
) -> list:
    """Claude に議事録ブロック JSON を生成させる"""
    prompt = f"""
以下の会議情報と tldv 議事録テキストをもとに、Notion ブロック JSON 配列を生成してください。

【会議情報】
- 種別: {meeting_type}
- 相手企業/会議名: {company}
- 日時: {date_str}
- 参加者: {participants}
- tldv URL: {tldv_url}

【tldv 議事録テキスト】
{tldv_text}

出力は Notion ブロックの JSON 配列のみ。コードフェンス不要。
"""
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8000,
        system=_MINUTES_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip()
    # コードフェンスが付いていた場合の除去
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
    return json.loads(raw)


def _notion_append_blocks(page_id: str, blocks: list) -> None:
    """Notion ページにブロックを追加（100件ずつ分割）"""
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    for i in range(0, len(blocks), 100):
        batch = blocks[i:i + 100]
        httpx.patch(
            f"https://api.notion.com/v1/blocks/{page_id}/children",
            headers=headers,
            json={"children": batch},
            timeout=30,
        )


def create_notion_child_page(parent_page_id: str, title: str, blocks: list) -> str:
    """通常ページ配下に子ページを作成し URL を返す（後方互換用）"""
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    body = {
        "parent": {"page_id": parent_page_id},
        "properties": {"title": {"title": [{"text": {"content": title}}]}},
        "children": blocks[:100],
    }
    resp = httpx.post("https://api.notion.com/v1/pages", headers=headers, json=body, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    page_id = data["id"]
    url = data.get("url", "")
    if len(blocks) > 100:
        _notion_append_blocks(page_id, blocks[100:])
    return url


def create_minutes_db_record(
    title: str,
    date_str: str,
    blocks: list,
    project: str = "",
) -> str:
    """
    議事録 DB にレコードを作成し URL を返す。
    date_str は "YYYY-MM-DD" 形式。
    project は DB の multi_select 有効値 (省略可)。
    """
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    props: dict = {
        "会議名": {"title": [{"text": {"content": title}}]},
        "日付": {"date": {"start": date_str}},
    }
    if project:
        props["プロジェクト"] = {"multi_select": [{"name": project}]}

    body = {
        "parent": {"database_id": NOTION_MINUTES_DB},
        "properties": props,
        "children": blocks[:100],
    }
    resp = httpx.post("https://api.notion.com/v1/pages", headers=headers, json=body, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    page_id = data["id"]
    url = data.get("url", "")
    if len(blocks) > 100:
        _notion_append_blocks(page_id, blocks[100:])
    return url


def create_meeting_minutes(
    company: str,
    date_str: str,
    participants: str,
    tldv_text: str,
    tldv_url: str = "",
    meeting_type: str = "社外MTG",
    project: str = "",
    brushup_company: bool = True,
) -> str:
    """
    議事録を生成して Notion DB に保存する。
    社外MTG かつ企業DB に対象企業が存在する場合、選考フロー等を自動更新する。

    Parameters
    ----------
    company        : 相手企業名または会議名
    date_str       : 日付文字列 (例: "2026-03-16" または "2026/03/16")
    participants   : 参加者 (例: "梅村京平（エムスリーキャリア）、佐藤篤也")
    tldv_text      : tldv の議事録テキスト全文
    tldv_url       : tldv の URL (省略可)
    meeting_type   : "社外MTG" | "社内MTG" | "採用MTG" など
    project        : Notion プロジェクト (新卒紹介/RPO/Sales/Ops/Recruitment 等、省略可)
    brushup_company: True のとき、社外MTG であれば企業DB を自動更新する

    Returns
    -------
    作成されたページの URL
    """
    # 日付を YYYY-MM-DD に正規化
    date_normalized = date_str.replace("/", "-")
    title = f"【{meeting_type}】{company}｜{date_str}"

    print(f"\n[議事録生成] Claude で構造化中...")
    blocks = generate_minutes_blocks(
        meeting_type, company, date_str, participants, tldv_url, tldv_text
    )
    print(f"  → {len(blocks)} ブロック生成完了")

    print("[Notion] DB レコードを作成中...")
    url = create_minutes_db_record(title, date_normalized, blocks, project)
    print(f"  → 議事録作成完了: {url}")

    # 社外MTG の場合、企業DB を自動ブラッシュアップ
    if brushup_company and meeting_type in ("社外MTG", "採用MTG", "クライアントMTG"):
        print(f"\n[企業DB] 「{company}」の情報を議事録からブラッシュアップ中...")
        result = brushup_company_db_from_minutes(company, tldv_text)
        print(f"  → {result}")

    return url


def _run_meeting_minutes():
    """対話形式で議事録を作成するモード"""
    print("\n" + "─" * 55)
    print("📝 議事録作成モード")
    print("─" * 55)

    meeting_type = input("会議種別 (社外MTG/社内MTG etc.) [社外MTG] > ").strip() or "社外MTG"
    company = input("相手企業名・会議名 > ").strip()
    date_str = input(f"日付 (例: {date.today().strftime('%Y/%m/%d')}) > ").strip() or date.today().strftime("%Y/%m/%d")
    participants = input("参加者 > ").strip()
    tldv_url = input("tldv URL (省略可) > ").strip()
    print("プロジェクト: コンサルティング/RPO/中途紹介/新卒紹介/Sales/Ops/Corporate/Recruitment/Fcst/strategy")
    project = input("プロジェクト (省略可) > ").strip()
    brushup_input = input("企業DB を自動ブラッシュアップしますか? [Y/n] > ").strip().lower()
    brushup_company = brushup_input != "n"

    print("\ntldv議事録テキストを貼り付けてください（空行2行で確定）:\n")
    lines = []
    empty_count = 0
    while True:
        line = input()
        if line == "":
            empty_count += 1
            if empty_count >= 2:
                break
        else:
            empty_count = 0
        lines.append(line)
    tldv_text = "\n".join(lines).strip()

    if not tldv_text:
        print("議事録テキストが空です。中断します。")
        return

    try:
        url = create_meeting_minutes(
            company=company,
            date_str=date_str,
            participants=participants,
            tldv_text=tldv_text,
            tldv_url=tldv_url,
            meeting_type=meeting_type,
            project=project,
            brushup_company=brushup_company,
        )
        print(f"\n✅ 議事録を作成しました。\nNotion URL: {url}")
    except Exception as e:
        print(f"\n[ERROR] 議事録作成に失敗しました: {e}")


# ──────────────────────────────────────────────
# 企業紹介文生成メイン処理
# ──────────────────────────────────────────────

def _run_company_intro():
    """企業紹介文生成モード"""
    print("\nNotion データベースに接続中...")
    try:
        prop_mapping = get_db_properties()
    except Exception as e:
        print(f"\n[ERROR] Notion接続に失敗しました: {e}")
        return

    print(f"✅ 接続OK  取得フィールド: {', '.join(prop_mapping.keys())}\n")

    while True:
        print("─" * 55)
        print("企業名を入力してください。")
        print("複数企業はカンマ区切り または 1行ずつ入力（空行で確定）\n")

        lines: list[str] = []
        while True:
            line = input("> ").strip()
            if line == "":
                break
            lines.append(line)

        if not lines:
            print("終了します。")
            break

        company_names = parse_company_names(lines)
        print(f"\n対象企業: {', '.join(company_names)}")
        print("Notionから情報を取得中...\n")

        try:
            companies = search_companies(company_names, prop_mapping)
        except Exception as e:
            print(f"[ERROR] Notion検索に失敗しました: {e}")
            continue

        if not companies:
            print("対象企業が見つかりませんでした。")
            continue

        print(f"{len(companies)}社分を生成中...\n" + "─" * 55)

        introductions: list[str] = []
        for i, company in enumerate(companies, 1):
            name = company.get("企業名", "")
            print(f"[{i}/{len(companies)}] {name} ...")
            points = generate_recommend_points(company)
            text   = format_introduction(company, points)
            introductions.append(text)
            print("完了")

        all_text = ("\n\n" + "─" * 30 + "\n\n").join(introductions)

        print("\n" + "═" * 55)
        print(all_text)
        print("═" * 55)

        while True:
            print("\n  [c] クリップボードにコピー")
            if len(companies) > 1:
                for idx, c in enumerate(companies, 1):
                    print(f"  [{idx}] {c.get('企業名', '')} だけコピー")
            print("  [r] 再生成")
            print("  [n] 別の企業を入力")
            print("  [q] 終了\n")

            action = input("> ").strip().lower()

            if action == "c":
                if copy_to_clipboard(all_text):
                    print("\n✅ クリップボードにコピーしました。")
                    print("Lステップのトーク画面に貼り付けてください。")
                break

            elif action.isdigit() and 1 <= int(action) <= len(introductions):
                idx = int(action) - 1
                if copy_to_clipboard(introductions[idx]):
                    print(f"\n✅ {companies[idx].get('企業名', '')} をコピーしました。")
                break

            elif action == "r":
                print("\n再生成中...\n" + "─" * 55)
                introductions = []
                for i, company in enumerate(companies, 1):
                    name = company.get("企業名", "")
                    print(f"[{i}/{len(companies)}] {name} ...")
                    points = generate_recommend_points(company)
                    text   = format_introduction(company, points)
                    introductions.append(text)
                    print("完了")
                all_text = ("\n\n" + "─" * 30 + "\n\n").join(introductions)
                print("\n" + "═" * 55)
                print(all_text)
                print("═" * 55)

            elif action == "n":
                break

            elif action == "q":
                print("終了します。")
                return

            else:
                print("入力が正しくありません。")


# ──────────────────────────────────────────────
# エントリポイント
# ──────────────────────────────────────────────

def run(mode: str | None = None, **kwargs):
    """
    オーケストレーターから呼ばれるエントリポイント。
    mode:
      'intro'   → 企業紹介文生成
      'minutes' → 議事録作成（kwargs: company, date_str, participants, tldv_text, tldv_url, meeting_type）
      None      → メニュー表示
    """
    if mode == "intro":
        _run_company_intro()
        return

    if mode == "minutes":
        # プログラムから直接呼ぶ場合（引数あり）
        if kwargs.get("tldv_text"):
            url = create_meeting_minutes(**kwargs)
            print(f"\n✅ 議事録URL: {url}")
        else:
            _run_meeting_minutes()
        return

    print("\n" + "=" * 55)
    print("  Notionエージェント")
    print("=" * 55)
    print("\n【メニュー】\n")
    print("  1. 企業紹介文生成（Notion → LINE用）")
    print("  2. 議事録作成（tldv → Notion）")
    print("  q. 終了\n")

    while True:
        choice = input("番号を入力 > ").strip().lower()
        if choice == "1":
            _run_company_intro()
            break
        elif choice == "2":
            _run_meeting_minutes()
            break
        elif choice == "q":
            break
        else:
            print("1 / 2 / q を入力してください。")


def main():
    run()


if __name__ == "__main__":
    main()
