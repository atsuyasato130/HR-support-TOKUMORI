#!/usr/bin/env python3
"""Notion情報を入力に、求人票の事業概要・推しポイント・職務内容を統一スタイルでAIリライト。
スタイル: 敬体／絵文字・①②■なし(箇条書きは▶)／学歴制限・採用基準・通過率は書かない(学生向け)。
  python3 scripts/rewrite_intro_unified.py --limit 3       # dry-run（生成内容を表示）
  python3 scripts/rewrite_intro_unified.py --execute        # 全社反映
"""
import argparse
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
_SUF = re.compile(r"(株式会社|有限会社|合同会社|一般社団法人|公益社団法人|医療法人|社会福祉法人|Inc\.|LLC|Ltd\.)", re.I)
_ALIAS = {"匠ローレン": "匠lauren"}

SYSTEM = (
    "あなたは新卒採用支援会社のエディターです。与えられた企業情報をもとに、学生に共有する求人票の"
    "3項目を統一スタイルで作成します。\n"
    "【厳守スタイル】\n"
    "・敬体（です・ます）。主観的な煽り・俗語（例:えぐい）は使わない。事実ベースで簡潔に。\n"
    "・絵文字、①②③、■、★ は使わない。箇条書きは ▶ のみ。\n"
    "・学歴制限/学歴フィルタ/社内の評価基準/通過率/合格率など、学生に開示すべきでない情報は一切書かない。\n"
    "【各項目】\n"
    "・jigyo_gaiyo（事業概要）: その会社が何をしているかを1〜2文で。\n"
    "・oshi（推しポイント）: 学生にとっての魅力・メリットを ▶ で3〜4点。各1行・各40〜70字程度。\n"
    "・shokumu（職務内容）: 新卒が入社後に担う業務を1〜3文で具体的に。\n"
    "出力は次のJSONのみ（前後に文章やコードブロックを付けない）:\n"
    '{"jigyo_gaiyo":"...","oshi":"▶ ...\\n▶ ...\\n▶ ...","shokumu":"..."}'
)


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
                })
            if not d.get("has_more"):
                break
            cur = d["next_cursor"]
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    sf = Salesforce(username=os.environ["SF_USERNAME"], password=os.environ["SF_PASSWORD"],
                    security_token=os.environ["SF_SECURITY_TOKEN"], domain=os.environ.get("SF_DOMAIN", "login"))
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    comp = {}
    for r in sf.query_all("SELECT Id, Company__c, Company__r.Name FROM JobOfferSlip__c WHERE Company__c != null")["records"]:
        c = comp.setdefault(norm((r.get("Company__r") or {}).get("Name") or ""), {"acct": r["Company__c"], "slips": []})
        c["slips"].append(r["Id"])

    notion = fetch_notion()
    print(f"Notion {len(notion)}社 / {'実行' if args.execute else 'DRY-RUN'}")
    _OUT = {}
    done = up_slip = up_acct = 0
    for n in notion:
        if not (n["jigyo"] or n["miryoku"] or n["tsuyomi"]):
            continue
        tgt = comp.get(norm(n["name"]))
        if not tgt:
            continue
        if args.limit and done >= args.limit:
            break
        material = (f"企業名: {n['name']}\n職種: {n['shoku']}\n"
                    f"事業内容: {n['jigyo']}\n学生へ伝える魅力ポイント: {n['miryoku']}\n強み・訴求ポイント: {n['tsuyomi']}")
        try:
            resp = client.messages.create(model=MODEL, max_tokens=900, system=SYSTEM,
                                          messages=[{"role": "user", "content": material}])
            raw = resp.content[0].text.strip()
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            data = json.loads(m.group()) if m else {}
        except Exception as e:  # noqa: BLE001
            print(f"  ✗ {n['name']}: {str(e)[:90]}")
            continue
        jg, oshi, shoku = data.get("jigyo_gaiyo", ""), data.get("oshi", ""), data.get("shokumu", "")
        if not (jg or oshi or shoku):
            continue
        done += 1
        if not args.execute or done <= 3:
            print(f"\n■ {n['name']}\n 事業概要: {jg}\n 推し:\n{oshi}\n 職務内容: {shoku}")
        _OUT[n["name"]] = {"jigyo_gaiyo": jg, "oshi": oshi, "shokumu": shoku}
        if args.execute:
            for sid in tgt["slips"]:
                fields = {}
                if oshi:
                    fields["GfaSelectionPoint__c"] = oshi[:32000]
                if shoku:
                    fields["GfaDutyDetail__c"] = shoku[:32000]
                if jg:
                    fields["GfaAccountBusinessContent__c"] = jg[:32000]  # 求人票側の事業概要
                if fields:
                    try:
                        sf.JobOfferSlip__c.update(sid, fields)
                        up_slip += 1
                    except Exception as e:  # noqa: BLE001
                        print(f"  ✗slip {n['name']}: {str(e)[:70]}")
            if jg:
                up_acct += 1
        time.sleep(0.5)
    Path("/tmp/rewrite_out.json").write_text(json.dumps(_OUT, ensure_ascii=False, indent=1))
    print(f"\n生成:{done}社 / 推し・職務更新:{up_slip}件 / 事業概要更新:{up_acct}社")


if __name__ == "__main__":
    main()
