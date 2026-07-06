#!/usr/bin/env python3
"""整形済み選考フロー(B形式:ステップ＋評価ポイント・255字以内)を企業名マッチで一括反映。
  python3 scripts/update_selectionflow.py            # dry-run
  python3 scripts/update_selectionflow.py --execute   # 反映
FLOWS に {企業名: 整形テキスト} を追記して実行（複数バッチ対応）。
"""
import os
import re
import sys
import difflib
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
_ALIAS = {"匠ローレン": "匠lauren", "エヌエステック": "エヌエステック"}


def norm(name):
    n = _SUF.sub("", name or "")
    n = re.sub(r"[\s　・\-_]", "", n).lower().strip()
    return _ALIAS.get(n, n)


FLOWS = {
    "株式会社エンパワー": "【選考ステップ】説明会 → 一次面接 → 最終面接 → 内定",
    "エー・アール・システム株式会社": "【選考ステップ】書類選考 → 一次面接(オンライン/人事・各部署長) → 適性検査(SPI) → 最終面接(社長)",
    "シューワ株式会社": "【選考ステップ】説明会 → 質疑応答面接 → 部門長面接(希望事業部責任者) → 最終選考(代表)",
    "株式会社アイスタイル": "【選考ステップ】説明会 → ES → 一次 → 二次 → 三次面接(人事/現場) → 最終面接(執行役員・人事)",
    "株式会社ネクサスエージェント": "【選考ステップ】別途共有（ATS：SONAR経由でご紹介）",
    "株式会社AsucrePartners": "【選考ステップ】会社説明会(人事) → 書類選考 → 二次選考/個別面接(現場役職者) → 最終選考(現場責任者)",
    "株式会社はなまる": "【選考ステップ】説明会 → 一次面接 → 二次面接(課長以上) → 店舗見学 → 最終面接(社長)",
    "SALESCORE株式会社": "【選考ステップ】説明選考会 → 一次面接 → 二次面接(採用責任者) → 最終面接(事業部責任者)",
    "株式会社ウイルテック": "【選考ステップ】Web説明会 → 一次面接(Web) → 二次面接(Web/対面)　※職種により異なる",
    "株式会社エーピーコミュニケーションズ": "【選考ステップ】説明会(人事) → 一次面接(人事M) → 二次面接(採用責任者) → 最終面接(役員・人事部長)",
    "ヒューマントラスト": "【選考ステップ】説明会 → 一次面接 → 二次面接(研修担当) → 人事面談 → 最終面接(対面)",
    "株式会社サンテック": "【選考ステップ】説明会 → WEB一次面接(人事) → [希望地以外:事業所での対面面接] → 最終面接(本社役員2〜3名)",
    "ライズ": "【選考ステップ】オファー面談 → WEB会社説明会 → 面接(新卒採用責任者) → 内定",
    "OKAN": "【選考ステップ】カジュアル面談 → 一次面接 → 二次面接 → テスト → 最終面接 → 内定",
    "パワーエッジ": "【選考ステップ】説明会(動画) → 一次面接＋適性検査 → 二次面接 → 最終面接(対面/本社・支社)\n【ポイント】一次=コミュ力・成功体験／二次=逆質問は複数用意",
    "株式会社MSK": "【選考ステップ】説明会 → 面接 → 内定",
    "チュチュアンナ": "【選考ステップ】ES → 適性検査 → 一次面接(人事課長) → 二次面接(人事部長) → 最終面接(社長・副社長)　※二次〜最終間に面談あり",
    "ユナイテッドエンジニアリング株式会社": "【選考ステップ】説明会(WEB) → 一次面接(WEB) → 最終面接(原則対面・WEB相談可)",
    "ラネット": "【選考ステップ】説明会 → SPI → SPIフィードバック面談 → 一次面接(オンライン) → 準備面談 → 最終面接(対面)",
    "株式会社ピーアンドアイ": "【選考ステップ】説明会 → 一次面接 → 二次面接 → 最終面接",
    "エヌエステック株式会社": "【選考ステップ】説明会 → 一次面接 → 最終面接(対面)",
    "株式会社DYM": "【選考ステップ】説明選考会 → 1次(人事) → 2次(現場若手) → 3次(現場中間) → 4次(課長・部長) → 役員面接 → 最終面接",
    "Sansan株式会社": "【選考ステップ】説明会 → ES → AI面接 → 一次面接(現場MGR) → 二次面接(部長/副部長) → 最終面接(役員)",
    "株式会社オーリーズ": "【選考ステップ】カジュアル面談 → インターンシップ → ES → 面接(複数回) → 内定",
    "マイスターエンジニアリング株式会社": "【選考ステップ】説明会 → 適性検査＋一次面接 → 最終面接",
    "株式会社ナハトエース": "【選考ステップ】動画説明会 → 面接誘致(候補日提示) → 二次面接 → 最終面接",
    "カルタホールディングス": "【選考ステップ】説明会 → ES → GD面接 → SPI/適性 → 4次 → 5次 → 6次 → 最終面接　※グローバル選考はプレゼンあり(語学・外国籍可)",
    "ウイングアークNEX株式会社": "【選考ステップ】説明会 → 一次面接 → 二次面接 → 最終面接",
    "エムスリーキャリア株式会社": "【選考ステップ】会社説明会(若手座談会含む) → 一次面接 → 二次面接 → 最終面接\n【ポイント】一次=簡潔さ・印象／二次=行動量or思考力・カルチャーフィット／最終=志望理由の一貫性・活躍可能性",
    "株式会社オロ": "【選考ステップ】会社説明会/セミナー → ES選考 → 一次選考(採用担当/現場) → 二次選考(マネージャー) → 最終選考(役員)",
    "株式会社プレシャスパートナーズ": "【選考ステップ】説明会 → 1次 → 2次 → 3次面接(対面) → 最終面接(対面)",
    "ラクサスマネジメント株式会社": "【選考ステップ】会社説明会 → 一次面接 → 最終面接(副社長)　｜ATS:リクナビHRTech／採用10名程度",
    "株式会社ロットネスト": "【選考ステップ】説明会 → 一次面接 → 最終選考",
    "株式会社マイベスト": "【選考ステップ】説明選考会・ES → 1次(人事) → 2次(MGR) → 3次(部長) → 4次(CHRO) → 最終面接(CEO)　｜ATS:Talentio",
    "株式会社3WELL": "【選考ステップ】説明選考会 → 書類選考 →(動画選考)→ 1次面接 → 2次面接(役員/人事) → 適性検査 → 最終面接(代表)",
    "オルビス株式会社": "【選考ステップ】一次面接 → 二次面接(部長) → 三次面接(HR本部長＋マーケ部長) → 最終面接(社長)　｜マーケ職6名・商品企画2名",
    "SEVENRICH GROUP": "【選考ステップ】1day選考会(最短即日内定)　｜採用45名／ターゲット松竹梅(松=MARCH以上・経営志向ほか)",
    "株式会社リーディングマーク": "【選考ステップ】(本選考)説明会 → 面接(マネージャー) → 面接(事業責任者) → 面接(役員)\n(インターン)性格検査 → インターン → 各面接",
    "株式会社エイジレス": "【選考ステップ】説明会(45分)＋WEB適性検査 → 一次面接 → 二次面接 → 三次面接 → 最終面接",
}


def main(execute):
    sf = Salesforce(
        username=os.environ["SF_USERNAME"], password=os.environ["SF_PASSWORD"],
        security_token=os.environ["SF_SECURITY_TOKEN"], domain=os.environ.get("SF_DOMAIN", "login"),
    )
    comp = {}
    for r in sf.query_all("SELECT Id, Company__c, Company__r.Name FROM JobOfferSlip__c WHERE Company__c != null")["records"]:
        comp.setdefault(norm((r.get("Company__r") or {}).get("Name") or ""), []).append(r["Id"])

    print(f"整形選考フロー: {len(FLOWS)}社（{'実行' if execute else 'DRY-RUN'}）")
    over = [(k, len(v)) for k, v in FLOWS.items() if len(v) > 255]
    if over:
        print("⚠️255超:", over)
    matched = updated = 0
    nomatch = []
    for name, text in FLOWS.items():
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
    print(f"マッチ:{matched}社 / 更新:{updated}件 / 未マッチ:{len(nomatch)} {nomatch}")


if __name__ == "__main__":
    main("--execute" in sys.argv)
