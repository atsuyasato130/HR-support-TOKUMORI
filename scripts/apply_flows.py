#!/usr/bin/env python3
"""/tmp/flows_formatted.json ({企業名: 整形選考フロー}) を企業名マッチで一括反映。
  python3 scripts/apply_flows.py            # dry-run
  python3 scripts/apply_flows.py --execute   # 反映
"""
import json
import os
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1] / "agents" / "hr_support"
_ENV = _ROOT / "config" / ".env"
if _ENV.exists():
    for _l in _ENV.read_text().splitlines():
        _l = _l.strip()
        if _l and not _l.startswith("#") and "=" in _l:
            _k, _, _v = _l.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

from simple_salesforce import Salesforce

_SUF = re.compile(r"(株式会社|有限会社|合同会社|一般社団法人|公益社団法人|医療法人|社会福祉法人|Inc\.|LLC|Ltd\.)", re.I)
_ALIAS = {"匠ローレン": "匠lauren"}


def norm(name):
    n = _SUF.sub("", name or "")
    n = re.sub(r"[\s　・\-_]", "", n).lower().strip()
    return _ALIAS.get(n, n)


def main(execute):
    flows = json.loads(Path("/tmp/flows_formatted.json").read_text())
    sf = Salesforce(
        username=os.environ["SF_USERNAME"], password=os.environ["SF_PASSWORD"],
        security_token=os.environ["SF_SECURITY_TOKEN"], domain=os.environ.get("SF_DOMAIN", "login"),
    )
    comp = {}
    for r in sf.query_all("SELECT Id, Company__c, Company__r.Name FROM JobOfferSlip__c WHERE Company__c != null")["records"]:
        comp.setdefault(norm((r.get("Company__r") or {}).get("Name") or ""), []).append(r["Id"])

    over = {k: len(v) for k, v in flows.items() if len(v) > 255}
    if over:
        print("⚠️255超(切り詰めます):", over)
    matched = updated = 0
    nomatch = []
    for name, text in flows.items():
        ids = comp.get(norm(name))
        if not ids:
            nomatch.append(name)
            continue
        matched += 1
        if execute:
            for i in ids:
                try:
                    sf.JobOfferSlip__c.update(i, {"GfaSelectionFlow__c": text[:255]})
                    updated += 1
                except Exception as e:  # noqa: BLE001
                    print(f"  ✗ {name}: {str(e)[:80]}")
    print(f"対象:{len(flows)} / マッチ:{matched}社 / 更新:{updated}件 / 未マッチ:{len(nomatch)}")
    if nomatch:
        print("  未マッチ(求人票なし等):", ", ".join(nomatch))


if __name__ == "__main__":
    main("--execute" in sys.argv)
