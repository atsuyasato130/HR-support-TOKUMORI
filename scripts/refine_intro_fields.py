#!/usr/bin/env python3
"""LINE文の質向上：Notionの人が書いた良質テキストをそのまま反映。
  推しポイント : 学生へ伝える魅力ポイント（無ければ強み/訴求）→ GfaSelectionPoint__c
  事業概要     : 事業内容の「一言で言うと」要約 → GfaAccountBusinessContent__c
※学生向け前提。採用要件・学歴制限・評価基準は対象外（魅力ポイントは学生開示OKの内容）。
  python3 scripts/refine_intro_fields.py            # dry-run
  python3 scripts/refine_intro_fields.py --execute   # 反映
"""
import argparse
import difflib
import os
import re
from pathlib import Path

import httpx

_ROOT = Path(__file__).resolve().parents[1] / "agents" / "hr_support"
for _l in (_ROOT / "config" / ".env").read_text().splitlines():
    _l = _l.strip()
    if _l and not _l.startswith("#") and "=" in _l:
        _k, _, _v = _l.partition("=")
        os.environ.setdefault(_k.strip(), _v.strip())

from simple_salesforce import Salesforce

NOTION_KEY = os.environ["NOTION_API_KEY"]
DB = "5cdbd39197f94db7b7e275d317166bfd"
_SUF = re.compile(r"(株式会社|有限会社|合同会社|一般社団法人|公益社団法人|医療法人|社会福祉法人|Inc\.|LLC|Ltd\.)", re.I)
_ALIAS = {"匠ローレン": "匠lauren"}


def norm(name):
    n = re.sub(r"[\s　・\-_]", "", _SUF.sub("", name or "")).lower().strip()
    return _ALIAS.get(n, n)


def ptext(p):
    t = p.get("type", "")
    if t == "title":
        return "".join(r.get("plain_text", "") for r in p.get("title", []))
    if t == "rich_text":
        return "".join(r.get("plain_text", "") for r in p.get("rich_text", []))
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
                    "miryoku": ptext(pr.get("学生へ伝える魅力ポイント", {})).strip(),
                    "tsuyomi": ptext(pr.get("強み / 訴求ポイント", {})).strip(),
                    "jigyo": ptext(pr.get("事業内容", {})).strip(),
                })
            if not d.get("has_more"):
                break
            cur = d["next_cursor"]
    return rows


def clean_oshi(miryoku, tsuyomi):
    """魅力ポイントを推しポイントとして整形（学生向け・見出し記号を統一）"""
    src = miryoku or tsuyomi
    if not src:
        return ""
    s = re.sub(r"【[^】]*】", "", src)            # 【見出し】除去
    s = re.sub(r"https?://\S+", "", s)            # URL除去
    s = re.sub(r"[ \t]+", " ", s)
    out = []
    for raw in re.split(r"\n", s):
        line = raw.strip()
        line = re.sub(r"^[■◆●○・※\-①-⑳①②③④⑤⑥⑦⑧⑨⑩\d\.\)]+\s*", "", line)
        line = line.strip(" 　:：")
        if len(line) >= 6:
            out.append("▶ " + line)
    return "\n".join(out[:5]).strip()


def biz_summary(jigyo):
    """事業内容から「一言で言うと」要約を抽出（無ければ先頭1文）"""
    if not jigyo:
        return ""
    s = jigyo.replace("\r", "")
    m = re.search(r"一言(?:で|でこの会社を)?(?:言うと|表すと|表現すると)[？\?\s「]*\n?(.+)", s)
    if m:
        seg = m.group(1)
        seg = re.split(r"\n|📌|💼|🏢|🔧|事業内容", seg)[0]
        seg = seg.strip(" 　「」！!。\n🎯✨🚀🌟")
        if len(seg) >= 6:
            return (seg + "。").replace("。。", "。")
    # fallback: 記号/見出しを除いた先頭1文
    body = re.sub(r"[🎯📌💼🏢🔧✨🚀🌟]", "", s)
    body = re.sub(r"一言で言うと|事業内容|詳細", "", body)
    body = re.sub(r"\s+", " ", body).strip()
    first = body.split("。")[0].strip()
    return (first + "。") if len(first) >= 6 else ""


def main(execute):
    sf = Salesforce(username=os.environ["SF_USERNAME"], password=os.environ["SF_PASSWORD"],
                    security_token=os.environ["SF_SECURITY_TOKEN"], domain=os.environ.get("SF_DOMAIN", "login"))
    comp = {}
    for r in sf.query_all("SELECT Id, Company__c, Company__r.Name FROM JobOfferSlip__c WHERE Company__c != null")["records"]:
        c = comp.setdefault(norm((r.get("Company__r") or {}).get("Name") or ""), {"acct": r["Company__c"], "slips": []})
        c["slips"].append(r["Id"])

    notion = fetch_notion()
    print(f"Notion {len(notion)}社（{'実行' if execute else 'DRY-RUN'}）")
    matched = up_slip = up_acct = 0
    samples = 0
    for n in notion:
        oshi = clean_oshi(n["miryoku"], n["tsuyomi"])
        biz = biz_summary(n["jigyo"])
        if not (oshi or biz):
            continue
        tgt = comp.get(norm(n["name"]))
        if not tgt:
            continue
        matched += 1
        if samples < 3:
            print(f"\n■ {n['name']}\n  事業概要: {biz}\n  推しポイント:\n{oshi}")
            samples += 1
        if execute:
            for sid in tgt["slips"]:
                if oshi:
                    try:
                        sf.JobOfferSlip__c.update(sid, {"GfaSelectionPoint__c": oshi[:32000]})
                        up_slip += 1
                    except Exception as e:  # noqa: BLE001
                        print(f"  ✗slip {n['name']}: {str(e)[:70]}")
            if biz:
                try:
                    sf.Account.update(tgt["acct"], {"GfaAccountBusinessContent__c": biz[:1000]})
                    up_acct += 1
                except Exception as e:  # noqa: BLE001
                    print(f"  ✗acct {n['name']}: {str(e)[:70]}")
    print(f"\nマッチ:{matched}社 / 推し更新:{up_slip}件 / 事業概要更新:{up_acct}社")


if __name__ == "__main__":
    import sys
    main("--execute" in sys.argv)
