#!/usr/bin/env python3
"""
lighten_yomi_report.py — ヨミレポート軽量化（Aプラン）

「担当CA別 ヨミグレード分布（S/A/B/C）」(ID 00OfP00000Fz78qUAB) の
紹介日 standardDateFilter を「全期間(CUSTOM/空)」→「直近6ヶ月」に変更し、
pipeline__c 全件スキャン(5,433件)を約1,468件に絞って軽量化する。

過去パターン(phase1_batch_update_27.py)準拠:
  - DRY-RUN 既定。実行は `--execute`。
  - メタデータ変更のため connect_sf(SfTaskType.SCHEMA)=渡邊アカウント。

Analytics REST API:
  GET   /analytics/reports/{id}/describe → reportMetadata
  PATCH /analytics/reports/{id}          → {"reportMetadata": {...}}
"""

import copy
import json
import logging
import sys
from datetime import date
from pathlib import Path

# hr_support を import パスに追加
_HR = Path("/Users/atsuyasato130/Claude AI/tokumori/agents/hr_support")
sys.path.insert(0, str(_HR))

from simple_salesforce.exceptions import SalesforceError  # noqa: E402

from utils.sf_credentials import connect_sf, SfTaskType  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("lighten_yomi_report")

REPORT_ID = "00OfP00000Fz78qUAB"
DATE_COLUMN = "pipeline__c.GfaIntroductionDate__c"
RELATIVE_DURATION = "LAST_N_MONTHS:6"  # 第一候補（相対・自動ロール）


def _months_ago(base: date, months: int) -> date:
    """base から months ヶ月前の日付（月跨ぎを安全に処理）。"""
    month_index = (base.year * 12 + (base.month - 1)) - months
    year, month = divmod(month_index, 12)
    month += 1
    # 月末日の差異を吸収（例: 8/31 の6ヶ月前 → 2/28）
    day = min(base.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
                         else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
    return date(year, month, day)


def _custom_range_filter() -> dict:
    """フォールバック用: 直近6ヶ月の固定日付レンジ。"""
    today = date.today()
    return {
        "column": DATE_COLUMN,
        "durationValue": "CUSTOM",
        "startDate": _months_ago(today, 6).isoformat(),
        "endDate": today.isoformat(),
    }


def _relative_filter() -> dict:
    return {
        "column": DATE_COLUMN,
        "durationValue": RELATIVE_DURATION,
        "startDate": None,
        "endDate": None,
    }


def _patch(sf, report_metadata: dict) -> None:
    sf.restful(
        f"analytics/reports/{REPORT_ID}",
        method="PATCH",
        json={"reportMetadata": report_metadata},
    )


def main(dry_run: bool = True, use_admin: bool = False) -> None:
    # 既定は佐藤(DATA)＝hr-support MCPと同じ接続基盤。
    # Analytics PATCH はレポート編集権限だけで通るため、まず佐藤で試行する。
    # 権限不足なら --admin で渡邊(SCHEMA/ModifyMetadata)に切替（要 .env の ADMIN 認証）。
    task = SfTaskType.SCHEMA if use_admin else SfTaskType.DATA
    sf = connect_sf(task)
    logger.info("接続アカウント: %s", "渡邊(admin)" if use_admin else "佐藤(default)")

    desc = sf.restful(f"analytics/reports/{REPORT_ID}/describe")
    rm = desc.get("reportMetadata", {})

    before = rm.get("standardDateFilter", {})
    logger.info("対象レポート: %s", rm.get("name"))
    logger.info("変更前 standardDateFilter:\n%s", json.dumps(before, ensure_ascii=False, indent=2))

    new_rm = copy.deepcopy(rm)
    new_rm["standardDateFilter"] = _relative_filter()

    logger.info("変更後 standardDateFilter（第一候補）:\n%s",
                json.dumps(new_rm["standardDateFilter"], ensure_ascii=False, indent=2))

    if dry_run:
        logger.info("[DRY-RUN] PATCH は送信していません。実行するには --execute を付けてください。")
        return

    # 第一候補（相対リテラル）→ 失敗時は CUSTOM 日付レンジにフォールバック
    try:
        _patch(sf, new_rm)
        logger.info("✅ PATCH 完了（%s）", RELATIVE_DURATION)
    except SalesforceError as e:
        logger.warning("相対リテラルが拒否されました（%s）。CUSTOM日付レンジにフォールバックします。", e)
        new_rm["standardDateFilter"] = _custom_range_filter()
        logger.info("フォールバック standardDateFilter:\n%s",
                    json.dumps(new_rm["standardDateFilter"], ensure_ascii=False, indent=2))
        _patch(sf, new_rm)
        logger.info("✅ PATCH 完了（CUSTOM 日付レンジ）")

    # 反映確認
    after = sf.restful(f"analytics/reports/{REPORT_ID}/describe") \
        .get("reportMetadata", {}).get("standardDateFilter", {})
    logger.info("反映後 standardDateFilter:\n%s", json.dumps(after, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main(dry_run="--execute" not in sys.argv, use_admin="--admin" in sys.argv)
