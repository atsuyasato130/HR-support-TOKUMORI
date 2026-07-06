#!/usr/bin/env python3
"""Notion企業DB → SF求人票「構造化項目」一括充実（Phase1: テキスト系）。

マッピング（Notion優先・非空のみ上書き）:
  事業内容                         → Account.Description
  選考フロー(無ければ紹介フロー本選考) → JobOfferSlip__c.GfaSelectionFlow__c
  強み/訴求ポイント＋学生へ伝える魅力  → JobOfferSlip__c.GfaSelectionPoint__c
  採用要件                         → JobOfferSlip__c.FitStudentType__c
  ウェブサイト                     → Account.Website
  （職務内容 GfaDutyDetail__c はNotion無し→ --duty でWeb補完：別実装）

使い方:
  python3 scripts/enrich_joboffer_from_notion.py            # dry-run（全社マッピング確認）
  python3 scripts/enrich_joboffer_from_notion.py --execute  # 実反映
  python3 scripts/enrich_joboffer_from_notion.py --limit 5  # 先頭5社だけ
"""
import argparse
import difflib
import os
import re
import sys
from pathlib import Path

import httpx

_ROOT = Path(__file__).resolve().parents[1] / "agents" / "hr_support"
_ENV = _ROOT / "config" / ".env"
if _ENV.exists():
    for _line in _ENV.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

from simple_salesforce import Salesforce

NOTION_API_KEY = os.environ.get("NOTION_API_KEY", "")
NOTION_DB_ID = os.environ.get("NOTION_COMPANY_DB_ID", "5cdbd39197f94db7b7e275d317166bfd")
NOTION_VERSION = "2022-06-28"

_CORP_SUFFIXES = re.compile(
    r"(株式会社|有限会社|合同会社|一般社団法人|公益社団法人|医療法人|社会福祉法人"
    r"|Inc\.|LLC|Ltd\.|Co\.,?\s*Ltd\.?)",
    re.IGNORECASE,
)


# Notion(カタカナ等) → SF表記 の手動別名（自動マッチで取りこぼす表記差）
_ALIAS = {
    "匠ローレン": "匠lauren",
}


def normalize_company_name(name: str) -> str:
    name = _CORP_SUFFIXES.sub("", name or "")
    name = re.sub(r"[\s　・\-_]", "", name)
    n = name.lower().strip()
    return _ALIAS.get(n, n)


# ──────────────────────────────────────────────
# Notion 取得
# ──────────────────────────────────────────────
def _prop_text(prop: dict) -> str:
    t = prop.get("type", "")
    if t == "title":
        return "".join(r.get("plain_text", "") for r in prop.get("title", []))
    if t == "rich_text":
        return "".join(r.get("plain_text", "") for r in prop.get("rich_text", []))
    if t == "url":
        return prop.get("url") or ""
    if t == "select":
        s = prop.get("select")
        return s["name"] if s else ""
    if t == "multi_select":
        return ";".join(s["name"] for s in prop.get("multi_select", []))
    return ""


def fetch_notion_companies() -> list:
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    out, cursor = [], None
    with httpx.Client(timeout=30) as client:
        while True:
            body = {"page_size": 100}
            if cursor:
                body["start_cursor"] = cursor
            r = client.post(
                f"https://api.notion.com/v1/databases/{NOTION_DB_ID}/query",
                headers=headers, json=body,
            )
            r.raise_for_status()
            data = r.json()
            for pg in data.get("results", []):
                props = pg.get("properties", {})
                name = ""
                for _k, p in props.items():
                    if p.get("type") == "title":
                        name = _prop_text(p)
                        break
                if not name:
                    continue

                def g(key: str) -> str:
                    return _prop_text(props.get(key, {})).strip()

                usp_parts = [x for x in [g("強み / 訴求ポイント"), g("学生へ伝える魅力ポイント")] if x]
                out.append({
                    "name": name,
                    "overview": g("事業内容"),
                    "selection_flow": g("選考フロー") or g("紹介フロー (本選考）"),
                    "selection_point": "\n\n".join(usp_parts),
                    "requirement": g("採用要件"),
                    "website": g("ウェブサイト"),
                })
            if not data.get("has_more"):
                break
            cursor = data.get("next_cursor")
    return out


# ──────────────────────────────────────────────
# SF
# ──────────────────────────────────────────────
def sf_login() -> Salesforce:
    return Salesforce(
        username=os.environ["SF_USERNAME"],
        password=os.environ["SF_PASSWORD"],
        security_token=os.environ["SF_SECURITY_TOKEN"],
        domain=os.environ.get("SF_DOMAIN", "login"),
    )


def fetch_sf_companies(sf: Salesforce) -> dict:
    """Company__c単位に求人票をまとめる。 {company_id: {name, account_id, slips:[ids]}}"""
    res = sf.query_all(
        "SELECT Id, Company__c, Company__r.Name FROM JobOfferSlip__c WHERE Company__c != null"
    )
    companies = {}
    for r in res["records"]:
        cid = r["Company__c"]
        name = (r.get("Company__r") or {}).get("Name") or ""
        c = companies.setdefault(cid, {"name": name, "account_id": cid, "slips": []})
        c["slips"].append(r["Id"])
    return companies


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true", help="実反映（既定はdry-run）")
    ap.add_argument("--limit", type=int, default=0, help="先頭N社だけ処理")
    ap.add_argument("--threshold", type=float, default=0.84, help="社名マッチ閾値")
    args = ap.parse_args()

    print(f"=== Notion → 求人票 充実 ({'実行' if args.execute else 'DRY-RUN'}) ===")
    sf = sf_login()
    notion = fetch_notion_companies()
    sf_companies = fetch_sf_companies(sf)
    print(f"Notion企業: {len(notion)}件 / SF求人票のある企業: {len(sf_companies)}社")

    # SF企業の正規化名インデックス
    sf_index = {}
    for cid, c in sf_companies.items():
        sf_index.setdefault(normalize_company_name(c["name"]), c)
    sf_norm_list = list(sf_index.items())

    matched = updated_slips = updated_accts = 0
    not_matched = []
    processed = 0

    for n in notion:
        if not any([n["overview"], n["selection_flow"], n["selection_point"], n["requirement"], n["website"]]):
            continue  # Notion側が空の企業はスキップ
        if args.limit and processed >= args.limit:
            break

        nn = normalize_company_name(n["name"])
        target = sf_index.get(nn)
        if not target:
            best, best_score = None, 0.0
            for sf_norm, c in sf_norm_list:
                score = difflib.SequenceMatcher(None, nn, sf_norm).ratio()
                if score > best_score:
                    best, best_score = c, score
            target = best if best_score >= args.threshold else None
        if not target:
            not_matched.append(n["name"])
            continue

        processed += 1
        matched += 1

        # 求人票項目（項目ごとに独立更新：1項目の失敗が他を巻き込まない）
        slip_fields, acct_fields = {}, {}
        if n["selection_point"]:
            slip_fields["GfaSelectionPoint__c"] = n["selection_point"][:32000]
        # 選考フローは現状255制限。長文は項目拡張(LongText)後に入るのでそのまま投入し、失敗は個別ログ
        if n["selection_flow"]:
            slip_fields["GfaSelectionFlow__c"] = n["selection_flow"][:32000]
        if n["overview"]:
            acct_fields["Description"] = n["overview"][:32000]
        if n["website"]:
            acct_fields["Website"] = n["website"][:255]

        cols = list(slip_fields.keys()) + [f"Account.{k}" for k in acct_fields]
        print(f"  ✓ {n['name']} → {target['name']}（求人票{len(target['slips'])}件）: {', '.join(cols)}")

        if args.execute:
            for sid in target["slips"]:
                for fkey, fval in slip_fields.items():
                    try:
                        sf.JobOfferSlip__c.update(sid, {fkey: fval})
                        updated_slips += 1
                    except Exception as e:  # noqa: BLE001
                        msg = str(e)
                        if "STRING_TOO_LONG" in msg:
                            print(f"     スキップ(長文/{fkey}) {target['name']}")
                        else:
                            print(f"     求人票更新失敗 {sid}/{fkey}: {msg[:120]}")
            if acct_fields:
                try:
                    sf.Account.update(target["account_id"], acct_fields)
                    updated_accts += 1
                except Exception as e:  # noqa: BLE001
                    print(f"     取引先更新失敗 {target['account_id']}: {str(e)[:120]}")

    print("=" * 64)
    print(f"マッチ: {matched}社")
    if args.execute:
        print(f"更新: 求人票{updated_slips}件 / 取引先{updated_accts}社")
    print(f"未マッチ(Notionに情報あるがSF求人票無し等): {len(not_matched)}社")
    if not_matched:
        print("  " + ", ".join(not_matched[:40]))


if __name__ == "__main__":
    main()
