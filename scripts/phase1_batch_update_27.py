#!/usr/bin/env python3
"""
Phase 1: 27卒求人票 不足フィールド一括補完スクリプト
対象: GfaRecruitingStatus__c IN ('募集中','契約済') AND student_year__c INCLUDES ('27卒')
更新フィールド: Req_Gakuchika__c, Req_Thinking__c, Req_Character__c, Req_Execution__c,
              Req_Interpersonal__c, Req_JobHunting__c, RecommendedScale__c,
              TargetHireCount__c, EstimatedSalary__c
"""

import os
import sys
import json

# .env を読み込む
_ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../agents/hr_support/config/.env")
if os.path.exists(_ENV_FILE):
    with open(_ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

from simple_salesforce import Salesforce  # type: ignore

sf = Salesforce(
    username=os.environ["SF_USERNAME"],
    password=os.environ["SF_PASSWORD"],
    security_token=os.environ["SF_SECURITY_TOKEN"],
    domain=os.environ.get("SF_DOMAIN", "login"),
)


# ─── マッピング関数 ───────────────────────────────────────────────────────────

def map_gakuchika(gakuchikapower: str) -> str:
    """gakuchikapower_c__c (例: '起業;留学;インターンシップ・部活動') → Req_Gakuchika__c (S/A/B/C/D)

    採用ランク:
    S: 起業経験
    A: 留学
    B: インターンシップ・部活動（長期/立ち上げ系）
    C: リーダー経験、2_リーダー経験
    D: メンバー経験

    複数ある場合は最も高いランクを採用
    """
    val = str(gakuchikapower or "").strip()
    if not val:
        return "C"
    items = [v.strip() for v in val.split(";")]
    rank_order = ["S", "A", "B", "C", "D"]
    best = "D"
    for item in items:
        if "起業" in item:
            best = _better_rank(best, "S", rank_order)
        elif "留学" in item:
            best = _better_rank(best, "A", rank_order)
        elif "インターンシップ" in item or "部活動" in item:
            best = _better_rank(best, "B", rank_order)
        elif "リーダー" in item or "2_" in item:
            best = _better_rank(best, "C", rank_order)
    return best


def _better_rank(current: str, candidate: str, order: list) -> str:
    """より上位のランクを返す"""
    if order.index(candidate) < order.index(current):
        return candidate
    return current


def map_rank_req(rank_field: str) -> str:
    """GfaJobOfferRank__c (例: 'S;A;B') → 最低要件ランク（リスト中の最低ランク）

    GfaJobOfferRank__c は許容する学歴ランクの範囲を表す（複数選択）
    → 最も低いランク（最後の値）が最低要件
    """
    rank_order = ["S", "A", "B", "C", "D"]
    ranks_raw = str(rank_field or "").strip()
    if not ranks_raw:
        return "C"
    ranks = [r.strip() for r in ranks_raw.split(";") if r.strip() in rank_order]
    if not ranks:
        return "C"
    # 最も低い（=index最大）ランクを最低要件とする
    return max(ranks, key=lambda r: rank_order.index(r))


def map_scale(segment: str) -> str:
    """segment__c → RecommendedScale__c（複数選択可のセミコロン区切り）"""
    segment = str(segment or "").strip()
    mapping = {
        "大手": "大企業（1,001名以上）",
        "中堅": "中企業（101〜1,000名）",
        "中小": "中企業（101〜1,000名）;小企業（〜100名）",
        "ベンチャー": "小企業（〜100名）",
        "スタートアップ": "小企業（〜100名）",
    }
    # セミコロン区切りで複数あれば最初のものを使用
    first_seg = segment.split(";")[0].strip() if ";" in segment else segment
    for key, val in mapping.items():
        if key in first_seg:
            return val
    return ""


def map_salary(annual_income_width: str):
    """GfaAnnualIncomeWidth__c (例: '300〜500万') → EstimatedSalary__c (万円単位の中央値)"""
    import re
    if not annual_income_width:
        return None
    # 数値を全て抽出
    nums = re.findall(r"\d+", str(annual_income_width))
    if len(nums) >= 2:
        low, high = int(nums[0]), int(nums[1])
        return (low + high) / 2
    elif len(nums) == 1:
        return float(nums[0])
    return None


# ─── メイン処理 ──────────────────────────────────────────────────────────────

def main(dry_run: bool = True):
    # 27卒の募集中・契約済求人票を取得
    soql = """
        SELECT Id, Name, company_name__c,
               gakuchikapower_c__c, GfaJobOfferRank__c, segment__c,
               GfaRecruitmentCount__c, GfaAnnualIncomeWidth__c,
               Req_Gakuchika__c, Req_Thinking__c, Req_Character__c,
               Req_Execution__c, Req_Interpersonal__c, Req_JobHunting__c,
               RecommendedScale__c, TargetHireCount__c, EstimatedSalary__c
        FROM JobOfferSlip__c
        WHERE GfaRecruitingStatus__c IN ('稼働中', '契約中')
        AND student_year__c INCLUDES ('27卒')
        ORDER BY company_name__c
    """
    result = sf.query_all(soql)
    records = result.get("records", [])
    print(f"対象求人票: {len(records)} 件")
    print("=" * 80)

    update_count = 0
    skip_count = 0

    for rec in records:
        rec_id = rec["Id"]
        company = rec.get("company_name__c") or rec.get("Name", "")

        # 新しい値を計算
        new_gakuchika = map_gakuchika(rec.get("gakuchikapower_c__c", ""))
        rank_val = map_rank_req(rec.get("GfaJobOfferRank__c", ""))
        new_scale = map_scale(rec.get("segment__c", ""))
        new_salary = map_salary(rec.get("GfaAnnualIncomeWidth__c", ""))

        # 更新が必要なフィールドのみ抽出（既に値があればスキップ）
        updates = {}

        if not rec.get("Req_Gakuchika__c"):
            updates["Req_Gakuchika__c"] = new_gakuchika
        if not rec.get("Req_Thinking__c"):
            updates["Req_Thinking__c"] = rank_val
        if not rec.get("Req_Character__c"):
            updates["Req_Character__c"] = rank_val
        if not rec.get("Req_Execution__c"):
            updates["Req_Execution__c"] = rank_val
        if not rec.get("Req_Interpersonal__c"):
            updates["Req_Interpersonal__c"] = rank_val
        if not rec.get("Req_JobHunting__c"):
            updates["Req_JobHunting__c"] = "C"  # 固定デフォルト

        if not rec.get("RecommendedScale__c") and new_scale:
            updates["RecommendedScale__c"] = new_scale

        recruit_count = rec.get("GfaRecruitmentCount__c")
        if not rec.get("TargetHireCount__c") and recruit_count:
            updates["TargetHireCount__c"] = int(recruit_count)

        if not rec.get("EstimatedSalary__c") and new_salary is not None:
            updates["EstimatedSalary__c"] = new_salary

        if not updates:
            skip_count += 1
            continue

        print(f"[{'DRY' if dry_run else 'UPDATE'}] {company} ({rec_id})")
        for k, v in updates.items():
            print(f"  {k}: {v}")

        if not dry_run:
            try:
                getattr(sf, "JobOfferSlip__c").update(rec_id, updates)
                print(f"  -> 更新完了")
                update_count += 1
            except Exception as e:
                print(f"  -> エラー: {e}")
        else:
            update_count += 1

    print("=" * 80)
    print(f"{'[DRY RUN] ' if dry_run else ''}更新対象: {update_count} 件 / スキップ: {skip_count} 件")
    if dry_run:
        print("実際に更新するには: python3 phase1_batch_update_27.py --execute")


if __name__ == "__main__":
    dry_run = "--execute" not in sys.argv
    main(dry_run=dry_run)
