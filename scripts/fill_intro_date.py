#!/usr/bin/env python3
"""【自動】紹介日(GfaIntroductionDate__c)が空のpipelineに、紹介日を自動代入。
ルール: 求人紹介以降(status有・JobOfferSlip紐付き)で紹介日が空のレコードを対象に、
        説明会参加日/初回面談/一次〜最終面接日 のうち「今日以前で最も早い日」を紹介日に。
        該当が無ければ 作成日(CreatedDate) を代入。
※ダッシュボードは紹介日で年度集計するため、紹介日が無いと集計対象外になるのを防ぐ。
  python3 scripts/fill_intro_date.py            # dry-run（件数と数件のサンプル）
  python3 scripts/fill_intro_date.py --execute   # 反映
"""
import argparse
import datetime
import os
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1] / "agents" / "hr_support"
for _l in (_ROOT / "config" / ".env").read_text().splitlines():
    _l = _l.strip()
    if _l and not _l.startswith("#") and "=" in _l:
        _k, _, _v = _l.partition("=")
        os.environ.setdefault(_k.strip(), _v.strip())

from simple_salesforce import Salesforce

LOG = _ROOT / "logs" / "fill_intro_date.log"
CONTACT_FIELDS = ["Field5__c", "Setsumeikai__c", "First__c", "Second__c", "Third__c", "Last__c"]


def log(msg):
    LOG.parent.mkdir(exist_ok=True)
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} {msg}"
    print(line)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true")
    args = ap.parse_args()
    sf = Salesforce(username=os.environ["SF_USERNAME"], password=os.environ["SF_PASSWORD"],
                    security_token=os.environ["SF_SECURITY_TOKEN"], domain=os.environ.get("SF_DOMAIN", "login"))
    today = datetime.date.today()
    flds = ", ".join(CONTACT_FIELDS)
    recs = sf.query_all(
        f"SELECT Id, CreatedDate, {flds} FROM pipeline__c "
        f"WHERE JobOfferSlip__c != null AND status__c != null AND GfaIntroductionDate__c = null"
    )["records"]
    log(f"[fill_intro_date] 対象(紹介日が空): {len(recs)}件 ({'実行' if args.execute else 'DRY-RUN'})")

    upd = fail = 0
    samples = 0
    for r in recs:
        cand = []
        for f in CONTACT_FIELDS:
            v = r.get(f)
            if v:
                try:
                    d = datetime.date.fromisoformat(v[:10])
                    if d <= today:
                        cand.append(d)
                except ValueError:
                    pass
        intro = min(cand) if cand else datetime.date.fromisoformat(r["CreatedDate"][:10])
        if intro > today:
            intro = today
        iso = intro.isoformat()
        if samples < 5:
            src = "接点日" if cand else "作成日"
            log(f"  例: {r['Id']} → {iso} ({src})")
            samples += 1
        if args.execute:
            try:
                sf.pipeline__c.update(r["Id"], {"GfaIntroductionDate__c": iso})
                upd += 1
            except Exception as e:  # noqa: BLE001
                fail += 1
                if fail <= 3:
                    log(f"  更新NG {r['Id']}: {str(e)[:90]}")
    log(f"[fill_intro_date] 更新:{upd} 失敗:{fail}（失敗は卒年↔求人票不整合の検証ルール等）完了")


if __name__ == "__main__":
    main()
