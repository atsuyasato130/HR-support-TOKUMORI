#!/usr/bin/env python3
"""【自動・増分】新規企業の求人票を統一スタイルで自動充填。
launchd等で定期実行。空欄(=未処理/新規)かつNotionに情報がある企業だけをClaudeで生成し、
空欄のみ埋める（既存の整え済みコンテンツは上書きしない＝コスト最小・安全）。
対象項目: 事業概要(GfaAccountBusinessContent__c) / 推しポイント(GfaSelectionPoint__c) /
          職務内容(GfaDutyDetail__c) / 選考フロー(GfaSelectionFlow__c)
  python3 scripts/auto_fill_joboffer_unified.py            # dry-run（対象と生成を表示）
  python3 scripts/auto_fill_joboffer_unified.py --execute   # 反映
"""
import argparse
import datetime
import json
import os
import re
import time
from pathlib import Path

import httpx

_ROOT = Path(__file__).resolve().parents[1] / "agents" / "hr_support"
for _l in (_ROOT / "config" / ".env").read_text().splitlines():
    _l = _l.strip()
    if _l and not _l.startswith("#") and "=" in _l:
        _k, _, _v = _l.partition("=")
        os.environ.setdefault(_k.strip(), _v.strip())

import anthropic
from simple_salesforce import Salesforce

NOTION_KEY = os.environ["NOTION_API_KEY"]
DB = "5cdbd39197f94db7b7e275d317166bfd"
MODEL = "claude-sonnet-4-6"
LOG = _ROOT / "logs" / "auto_fill_joboffer.log"
_SUF = re.compile(r"(株式会社|有限会社|合同会社|一般社団法人|公益社団法人|医療法人|社会福祉法人|Inc\.|LLC|Ltd\.)", re.I)
_ALIAS = {"匠ローレン": "匠lauren"}

SYSTEM = (
    "あなたは新卒採用支援会社のエディターです。与えられた企業情報をもとに、学生に共有する求人票の"
    "4項目を統一スタイルで作成します。\n"
    "【厳守スタイル】敬体（です・ます）。煽り・俗語禁止。事実ベースで簡潔。絵文字/①②/■/★禁止、箇条書きは▶のみ。"
    "学歴制限・社内評価基準・通過率など学生に開示すべきでない情報は書かない。\n"
    "【各項目】\n"
    "・jigyo_gaiyo: 何をする会社かを1〜2文。\n"
    "・oshi: 学生メリットを▶で3〜4点（各40〜70字）。\n"
    "・shokumu: 新卒が担う業務を1〜3文で具体的に。\n"
    "・senko_flow: 選考の流れを『【選考ステップ】A → B → 内定』形式の1行で（情報が無ければ空文字）。\n"
    "出力は次のJSONのみ:\n"
    '{"jigyo_gaiyo":"...","oshi":"▶ ...\\n▶ ...","shokumu":"...","senko_flow":"【選考ステップ】..."}'
)


def log(msg):
    LOG.parent.mkdir(exist_ok=True)
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} {msg}"
    print(line)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def norm(name):
    n = re.sub(r"[\s　・\-_]", "", _SUF.sub("", name or "")).lower().strip()
    return _ALIAS.get(n, n)


def ptext(p):
    t = p.get("type", "")
    if t == "title":
        return "".join(r.get("plain_text", "") for r in p.get("title", []))
    if t == "rich_text":
        return "".join(r.get("plain_text", "") for r in p.get("rich_text", []))
    if t == "multi_select":
        return "/".join(s["name"] for s in p.get("multi_select", []))
    return ""


def fetch_notion():
    rows, cur = [], None
    with httpx.Client(timeout=30) as c:
        while True:
            b = {"page_size": 100}
            if cur:
                b["start_cursor"] = cur
            d = c.post(f"https://api.notion.com/v1/databases/{DB}/query",
                       headers={"Authorization": f"Bearer {NOTION_KEY}", "Notion-Version": "2022-06-28",
                                "Content-Type": "application/json"}, json=b).json()
            for pg in d["results"]:
                pr = pg["properties"]
                name = ""
                for _k, p in pr.items():
                    if p.get("type") == "title":
                        name = ptext(p)
                rows.append({
                    "name": name,
                    "jigyo": ptext(pr.get("事業内容", {})).strip(),
                    "miryoku": ptext(pr.get("学生へ伝える魅力ポイント", {})).strip(),
                    "tsuyomi": ptext(pr.get("強み / 訴求ポイント", {})).strip(),
                    "shoku": ptext(pr.get("職種", {})).strip(),
                    "flow": (ptext(pr.get("選考フロー", {})) or ptext(pr.get("紹介フロー (本選考）", {}))).strip(),
                })
            if not d.get("has_more"):
                break
            cur = d["next_cursor"]
    return {norm(r["name"]): r for r in rows if r["name"]}


def _empty(v):
    return not (v or "").strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true")
    args = ap.parse_args()

    sf = Salesforce(username=os.environ["SF_USERNAME"], password=os.environ["SF_PASSWORD"],
                    security_token=os.environ["SF_SECURITY_TOKEN"], domain=os.environ.get("SF_DOMAIN", "login"))
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    notion = fetch_notion()

    # Company単位に集約（空欄判定は「その企業のいずれかの求人票が空」）
    rows = sf.query_all(
        "SELECT Id, Company__c, Company__r.Name, GfaAccountBusinessContent__c, GfaSelectionPoint__c, "
        "GfaDutyDetail__c, GfaSelectionFlow__c FROM JobOfferSlip__c WHERE Company__c != null"
    )["records"]
    comp = {}
    for r in rows:
        key = norm((r.get("Company__r") or {}).get("Name") or "")
        c = comp.setdefault(key, {"name": (r.get("Company__r") or {}).get("Name"), "slips": []})
        c["slips"].append(r)

    # 対象＝いずれかの項目が空 かつ Notionに情報あり
    targets = []
    for key, c in comp.items():
        need = any(_empty(s.get("GfaSelectionPoint__c")) or _empty(s.get("GfaAccountBusinessContent__c"))
                   or _empty(s.get("GfaDutyDetail__c")) or _empty(s.get("GfaSelectionFlow__c")) for s in c["slips"])
        n = notion.get(key)
        if need and n and (n["jigyo"] or n["miryoku"] or n["tsuyomi"]):
            targets.append((c, n))

    log(f"[auto_fill] 新規/未充填の対象: {len(targets)}社 ({'実行' if args.execute else 'DRY-RUN'})")
    if not args.execute:
        # dry-runはAIを呼ばず対象一覧のみ（コストゼロ）
        for c, _n in targets:
            empt = sorted({fk for s in c["slips"] for fk in
                           ("GfaAccountBusinessContent__c", "GfaSelectionPoint__c", "GfaDutyDetail__c", "GfaSelectionFlow__c")
                           if _empty(s.get(fk))})
            log(f"  - {c['name']}（空欄: {', '.join(empt)}）")
        log("[auto_fill] DRY-RUN: --execute で生成・反映します")
        return
    done = upd = 0
    for c, n in targets:
        material = (f"企業名: {n['name']}\n職種: {n['shoku']}\n事業内容: {n['jigyo']}\n"
                    f"学生へ伝える魅力ポイント: {n['miryoku']}\n強み・訴求ポイント: {n['tsuyomi']}\n選考フロー(生): {n['flow']}")
        try:
            resp = client.messages.create(model=MODEL, max_tokens=900, system=SYSTEM,
                                          messages=[{"role": "user", "content": material}])
            m = re.search(r"\{.*\}", resp.content[0].text.strip(), re.DOTALL)
            data = json.loads(m.group()) if m else {}
        except Exception as e:  # noqa: BLE001
            log(f"  NG {n['name']}: {str(e)[:80]}")
            continue
        gen = {
            "GfaAccountBusinessContent__c": data.get("jigyo_gaiyo", ""),
            "GfaSelectionPoint__c": data.get("oshi", ""),
            "GfaDutyDetail__c": data.get("shokumu", ""),
            "GfaSelectionFlow__c": data.get("senko_flow", ""),
        }
        done += 1
        log(f"  OK {n['name']}")
        if args.execute:
            for s in c["slips"]:
                fields = {}
                for fk, val in gen.items():
                    if val and _empty(s.get(fk)):       # 空欄のみ充填（既存は保持）
                        fields[fk] = val[:32000]
                if fields:
                    try:
                        sf.JobOfferSlip__c.update(s["Id"], fields)
                        upd += 1
                    except Exception as e:  # noqa: BLE001
                        log(f"    更新NG {s['Id']}: {str(e)[:70]}")
        time.sleep(0.5)
    log(f"[auto_fill] 生成:{done}社 / 更新:{upd}件 完了")


if __name__ == "__main__":
    main()
