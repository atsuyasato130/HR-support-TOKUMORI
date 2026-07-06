#!/usr/bin/env python3
"""ATS（利用ATS=AtsTool__c）を企業名マッチで一括割当。
使い方:
  python3 scripts/assign_ats.py kanrikun           # dry-run（マッチ確認）
  python3 scripts/assign_ats.py kanrikun --execute  # 実更新
対象は company_name__c の部分一致。全卒年の求人票に設定。
"""
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1] / "agents" / "hr_support"
_ENV = _ROOT / "config" / ".env"
if _ENV.exists():
    for line in _ENV.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

from simple_salesforce import Salesforce

sf = Salesforce(
    username=os.environ["SF_USERNAME"],
    password=os.environ["SF_PASSWORD"],
    security_token=os.environ["SF_SECURITY_TOKEN"],
    domain=os.environ.get("SF_DOMAIN", "login"),
)

# (表示名, 検索キーワード)。キーワードは company_name__c LIKE '%kw%'
GROUPS = {
    "kanrikun": ("採用一括かんりくん", [
        ("いえらぶ", "いえらぶ"), ("ボードルア", "ボードルア"), ("揚羽", "揚羽"),
        ("アットキャド", "アットキャド"), ("ピアラ", "ピアラ"),
        ("日本マニュファクチャリング", "マニュファクチャリング"), ("ホームテック", "ホームテック"),
        ("データX", "データＸ"), ("ポート株式会社", "ポート株式会社"), ("不動産SHOPナカジツ", "ナカジツ"),
        ("リヴトラスト", "リヴトラスト"), ("ウイルテック", "ウイルテック"), ("ウィルオブ", "ウィルオブ"),
        ("グローバル・パートナーズ", "グローバル・パートナーズ"), ("プラン・ドゥ", "プラン・ドゥ"),
        ("プレシャスパートナーズ", "プレシャスパートナーズ"), ("田中商事", "田中商事"),
        ("イングリウッド", "イングリウッド"), ("プレアデス", "プレアデス"), ("サイバー・バズ", "サイバー・バズ"),
        ("匠Lauren", "匠Lauren"), ("ギブリー", "ギブリー"), ("ネクサスエージェント", "ネクサスエージェント"),
        ("エス・エム・エス", "エス・エム・エス"), ("HATARABA", "HATARABA"), ("HR team", "HR team"),
        ("L&E Group", "L&E"), ("3WELL", "3WELL"), ("AViC", "AViC"),
        ("ヒューマントラスト", "ヒューマントラスト"), ("マイクロアド", "マイクロアド"),
        ("ロットネスト", "ロットネスト"), ("オーリーズ", "オーリーズ"),
    ]),
    "hrmos1": ("HRMOS①", [
        ("アーキテックス", "アーキテックス"), ("クラシル", "クラシル"), ("トレンダーズ", "トレンダーズ"),
        ("ファインディ", "ファインディ"), ("PLAN-B", "PLAN-B"), ("Photosynth", "Photosynth"),
        ("TWOSTONE&Sons", "TWOSTONE"), ("ZEALS", "ZEALS"), ("株式会社エージェント", "株式会社エージェント"),
        ("オロ", "株式会社オロ"), ("キュービック", "キュービック"), ("ナハト", "ナハト"),
        ("ビザスク", "ビザスク"), ("ブイキューブ", "ブイキューブ"), ("ログラス", "ログラス"),
    ]),
    "hrmos2": ("HRMOS②", [
        ("INCLUSIVE Holdings", "INCLUSIVE"), ("CINC", "CINC"), ("ウイングアーク1st", "ウイングアーク"),
        ("カオナビ", "カオナビ"), ("ネクストビート", "ネクストビート"), ("クオンツ総研", "クオンツ"),
        ("i-plug", "i-plug"), ("リーディングマーク", "リーディングマーク"), ("エイジレス", "エイジレス"),
        ("ノースサンド", "ノースサンド"), ("オルビス", "オルビス"), ("バトンズ", "バトンズ"),
    ]),
    "sonar": ("sonar", [
        ("Sansan", "Sansan"), ("エヌエス・テック", "エヌエス・テック"), ("エムスリーキャリア", "エムスリーキャリア"),
        ("セーフィー", "セーフィー"), ("ヒューマングループ", "ヒューマングループ"), ("CARTA HOLDINGS", "CARTA"),
        ("DYM", "DYM"), ("FCE", "FCE"), ("IDOM", "IDOM"), ("RERISE", "RERISE"), ("S-FIT", "S-FIT"),
        ("Speee", "Speee"), ("TAPP", "TAPP"), ("kubell", "kubell"), ("クイック", "クイック"),
        ("ピーアンドアイ", "ピーアンドアイ"), ("ファミリーコーポレーション", "ファミリーコーポレーション"),
        ("マイスターエンジニアリング", "マイスターエンジニアリング"), ("マネーフォワード", "マネーフォワード"),
        ("リブ・コンサルティング", "リブ・コンサルティング"), ("ワールドインテック", "ワールドインテック"),
    ]),
}


def main(group_key, execute):
    ats_value, items = GROUPS[group_key]
    print(f"=== {ats_value} 割当 ({'実行' if execute else 'DRY-RUN'}) ===")
    total_updated = 0
    not_matched = []
    for label, kw in items:
        kw_esc = kw.replace("'", "\\'")
        # 取引先名(Company__r.Name)で照合（company_name__c手入力欄は空の場合があるため）
        res = sf.query(
            f"SELECT Id, Company__r.Name FROM JobOfferSlip__c "
            f"WHERE Company__r.Name LIKE '%{kw_esc}%'"
        )
        recs = res.get("records", [])
        # AViC は NAVICUS を誤検出するため除外
        if label == "AViC":
            recs = [r for r in recs if "NAVICUS" not in ((r.get("Company__r") or {}).get("Name") or "")]
        if not recs:
            not_matched.append(label)
            print(f"  ✗ 未マッチ: {label}（kw={kw}）")
            continue
        names = sorted({(r.get("Company__r") or {}).get("Name") for r in recs})
        print(f"  ✓ {label}: {len(recs)}件 → {', '.join(names)}")
        if execute:
            for r in recs:
                try:
                    sf.JobOfferSlip__c.update(r["Id"], {"AtsTool__c": ats_value})
                    total_updated += 1
                except Exception as e:
                    print(f"     更新失敗 {r['Id']}: {e}")
    print("=" * 60)
    if execute:
        print(f"更新: {total_updated}件")
    print(f"未マッチ: {len(not_matched)}件 {not_matched if not_matched else ''}")


if __name__ == "__main__":
    key = sys.argv[1] if len(sys.argv) > 1 else "kanrikun"
    main(key, "--execute" in sys.argv)
