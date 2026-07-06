#!/usr/bin/env python3
"""求人票の職務内容(GfaDutyDetail__c)を、企業HP＋SF既存情報からClaudeで生成して補完。

材料: 企業HP本文(取得できれば) ＋ 事業内容(Account.Description) ＋ 職種(syokusyu__c) ＋ 選考ポイント
対象: GfaDutyDetail__c が空 or 30文字未満の稼働中求人票
使い方:
  python3 scripts/fill_dutydetail_from_web.py            # dry-run（生成結果を表示）
  python3 scripts/fill_dutydetail_from_web.py --execute   # 実反映
  python3 scripts/fill_dutydetail_from_web.py --limit 3    # 先頭3件だけ
"""
import argparse
import os
import re
import time
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

import anthropic
from simple_salesforce import Salesforce

MODEL = "claude-haiku-4-5-20251001"
MAX_HTML = 10000
DELAY = 1.0

SYSTEM = (
    "あなたは新卒採用支援会社のリサーチャーです。与えられた企業情報（HP本文・事業内容・職種）から、"
    "その企業で新卒が担う『職務内容』を、学生にそのまま共有できる日本語で簡潔にまとめてください。"
    "条件: 150〜300文字／箇条書きや前置きは不要で説明文のみ／推測の誇張はせず材料に基づく／"
    "『〜と思われます』等の曖昧表現は避け、事実ベースで。出力は職務内容の本文のみ。"
)


def sf_login():
    return Salesforce(
        username=os.environ["SF_USERNAME"], password=os.environ["SF_PASSWORD"],
        security_token=os.environ["SF_SECURITY_TOKEN"], domain=os.environ.get("SF_DOMAIN", "login"),
    )


def fetch_html(url):
    if not url:
        return ""
    if not url.startswith("http"):
        url = "https://" + url
    try:
        r = httpx.get(url, follow_redirects=True, timeout=10,
                      headers={"User-Agent": "Mozilla/5.0 (compatible; HRSupportBot/1.0)"})
        r.raise_for_status()
        t = re.sub(r"<script[^>]*>.*?</script>", " ", r.text, flags=re.DOTALL | re.I)
        t = re.sub(r"<style[^>]*>.*?</style>", " ", t, flags=re.DOTALL | re.I)
        t = re.sub(r"<[^>]+>", " ", t)
        return re.sub(r"\s+", " ", t).strip()[:MAX_HTML]
    except Exception:
        return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    sf = sf_login()
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    rows = sf.query_all(
        "SELECT Id, Company__r.Name, Company__r.Description, Company__r.Website, "
        "syokusyu__c, GfaSelectionPoint__c, GfaDutyDetail__c "
        "FROM JobOfferSlip__c WHERE Company__c != null AND GfaRecruitingStatus__c IN ('稼働中','契約中')"
    )["records"]

    # 職務内容が空/短いものだけ
    targets = [r for r in rows if len((r.get("GfaDutyDetail__c") or "").strip()) < 30]
    print(f"対象: {len(targets)}件（{'実行' if args.execute else 'DRY-RUN'}）")

    done = 0
    for r in targets:
        if args.limit and done >= args.limit:
            break
        comp = (r.get("Company__r") or {})
        name = comp.get("Name") or ""
        desc = comp.get("Description") or ""
        site = fetch_html(comp.get("Website"))
        if not (desc or site):
            continue  # 材料なし
        material = (
            f"企業名: {name}\n"
            f"事業内容: {desc}\n"
            f"職種: {r.get('syokusyu__c') or ''}\n"
            f"選考ポイント: {(r.get('GfaSelectionPoint__c') or '')[:500]}\n"
            f"HP本文(抜粋): {site[:6000]}"
        )
        try:
            resp = client.messages.create(
                model=MODEL, max_tokens=500, system=SYSTEM,
                messages=[{"role": "user", "content": material}],
            )
            duty = resp.content[0].text.strip()
        except Exception as e:  # noqa: BLE001
            print(f"  ✗ 生成失敗 {name}: {str(e)[:80]}")
            continue
        if not duty:
            continue
        done += 1
        print(f"\n■ {name}\n{duty[:200]}{'…' if len(duty) > 200 else ''}")
        if args.execute:
            try:
                sf.JobOfferSlip__c.update(r["Id"], {"GfaDutyDetail__c": duty[:32000]})
            except Exception as e:  # noqa: BLE001
                print(f"  ✗ 更新失敗 {name}: {str(e)[:80]}")
        time.sleep(DELAY)

    print(f"\n=== {'更新' if args.execute else '生成'}: {done}件 ===")


if __name__ == "__main__":
    main()
