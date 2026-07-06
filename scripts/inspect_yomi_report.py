#!/usr/bin/env python3
"""
inspect_yomi_report.py — 読み取り専用。ヨミレポートの現在定義を取得して表示する。
変更は一切行わない（Analytics describe API の GET のみ）。
"""

import json
import os
import sys
from pathlib import Path

# hr_support を import パスに追加
_HR = Path("/Users/atsuyasato130/Claude AI/tokumori/agents/hr_support")
sys.path.insert(0, str(_HR))

from utils.sf_credentials import connect_sf, SfTaskType  # noqa: E402

REPORT_ID = "00OfP00000Fz78qUAB"  # 担当CA別 ヨミグレード分布（S/A/B/C）


def main():
    # メタデータ変更用の渡邊(admin)アカウントで接続検証も兼ねる
    sf = connect_sf(SfTaskType.SCHEMA)
    desc = sf.restful(f"analytics/reports/{REPORT_ID}/describe")
    rm = desc.get("reportMetadata", {})

    print("=== 基本 ===")
    print("name:", rm.get("name"))
    print("reportType:", (rm.get("reportType") or {}).get("type"),
          "|", (rm.get("reportType") or {}).get("label"))
    print("reportFormat:", rm.get("reportFormat"))
    print("folderId:", rm.get("folderId"))

    print("\n=== 既存 reportFilters ===")
    print(json.dumps(rm.get("reportFilters", []), ensure_ascii=False, indent=2))

    print("\n=== standardDateFilter ===")
    print(json.dumps(rm.get("standardDateFilter", {}), ensure_ascii=False, indent=2))

    print("\n=== グルーピング(down/across) ===")
    print("down:", json.dumps(rm.get("groupingsDown", []), ensure_ascii=False))
    print("across:", json.dumps(rm.get("groupingsAcross", []), ensure_ascii=False))

    # 紹介日 / 卒年 のカラムAPI名を、利用可能カラム一覧から特定
    ext = desc.get("reportExtendedMetadata", {})
    cols = ext.get("detailColumnInfo", {}) or {}
    print("\n=== 紹介日/卒年 を含むカラム候補 ===")
    for api, meta in cols.items():
        label = meta.get("label", "")
        if any(k in (api + label) for k in ["Introduction", "紹介日", "Graduation", "卒"]):
            print(f"  {api}  |  {label}  |  {meta.get('dataType')}")


if __name__ == "__main__":
    main()
