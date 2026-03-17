#!/usr/bin/env python3
"""
かんりくん → Salesforce 同期スクリプト

機能:
  かんりくんで選考ステータスが変わった学生を検出し、
  Salesforce の Account（Status__pc / Phase__pc）を自動更新する。

  ・差分検知: integrations/kanrikun_cache.json でステータスをキャッシュ
  ・SF検索順: メール → 電話番号 → 氏名（部分一致）
  ・DRY RUN: --dry-run フラグで更新せずにプレビューのみ

使い方:
  python3 kanrikun_sync.py             # 通常同期
  python3 kanrikun_sync.py --dry-run  # プレビューのみ
  python3 kanrikun_sync.py --status 3 4 5  # 指定ステータスのみ

環境変数（config/.env に設定）:
  KANRIKUN_CLIENT_ID
  KANRIKUN_CLIENT_SECRET
"""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv  # type: ignore

# .env 読み込み
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_BASE, "config/.env"))

# integrations/ を sys.path に追加（kanrikun_client をインポートするため）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kanrikun_cache.json")

SF_RECORDTYPE_SHINSOTSU = "0122w000001Ry2hAAC"

# ──────────────────────────────────────────────
# ステータスマッピング
# ──────────────────────────────────────────────

STATUS_LABELS: Dict[int, str] = {
    1: "書類選考",
    2: "選考中",
    3: "内定",
    4: "内定承諾",
    5: "選考辞退",
    6: "承諾辞退",
    7: "内定辞退",
    8: "不採用",
}

# かんりくん status → SF Account.Status__pc
# ※ SF の picklist 値に合わせて調整してください
KANRIKUN_TO_SF_STATUS: Dict[int, str] = {
    1: "支援中",    # 書類選考
    2: "支援中",    # 選考中
    3: "支援中",    # 内定（承諾前は支援継続）
    4: "支援終了",  # 内定承諾
    5: "支援終了",  # 選考辞退
    6: "支援終了",  # 承諾辞退
    7: "支援終了",  # 内定辞退
    8: "支援終了",  # 不採用
}

# かんりくん status → SF Account.Phase__pc
# ※ SF の Phase__pc picklist に存在する値に合わせてください
# ※ 存在しない値を設定するとエラーになります
KANRIKUN_TO_SF_PHASE: Dict[int, Optional[str]] = {
    1: "送客済",    # 書類選考 → 送客済のまま
    2: "送客済",    # 選考中   → 送客済のまま（より詳細はpipelineで管理）
    3: None,        # 内定     → Phase は手動管理（Noneでスキップ）
    4: None,        # 内定承諾 → 手動管理
    5: None,        # 辞退系   → 手動管理
    6: None,
    7: None,
    8: None,
}


# ──────────────────────────────────────────────
# キャッシュ管理
# ──────────────────────────────────────────────

def load_cache() -> Dict[str, int]:
    """前回同期時の学生ステータスキャッシュを読み込む"""
    if not os.path.exists(CACHE_FILE):
        return {}
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_cache(cache: Dict[str, int]) -> None:
    """学生ステータスキャッシュを保存"""
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


# ──────────────────────────────────────────────
# Salesforce 接続・検索
# ──────────────────────────────────────────────

def get_sf():
    from simple_salesforce import Salesforce  # type: ignore
    return Salesforce(
        username=os.environ["SF_USERNAME"],
        password=os.environ["SF_PASSWORD"],
        security_token=os.environ["SF_SECURITY_TOKEN"],
        domain=os.environ.get("SF_DOMAIN", "login"),
    )


def find_sf_account(sf, email: str, phone: str, name: str) -> Optional[Dict[str, Any]]:
    """SF Account を メール → 電話番号 → 氏名 の順で検索"""

    def _query(where: str) -> Optional[Dict[str, Any]]:
        soql = (
            f"SELECT Id, Name, Status__pc, Phase__pc "
            f"FROM Account WHERE {where} "
            f"AND RecordTypeId = '{SF_RECORDTYPE_SHINSOTSU}' LIMIT 1"
        )
        result = sf.query(soql)
        records = result.get("records", [])
        if not records:
            return None
        r = records[0]
        return {
            "id": r["Id"],
            "name": r["Name"],
            "status": r.get("Status__pc"),
            "phase": r.get("Phase__pc"),
        }

    if email:
        found = _query(f"PersonEmail = '{email}'")
        if found:
            return found

    if phone:
        found = _query(f"PersonMobilePhone = '{phone}'")
        if found:
            return found

    if name:
        parts = re.split(r"[\s　]+", name.strip())
        name_kw = "%".join(p for p in parts if p)
        found = _query(f"Name LIKE '%{name_kw}%'")
        if found:
            return found

    return None


# ──────────────────────────────────────────────
# 同期ロジック
# ──────────────────────────────────────────────

def sync_to_salesforce(
    dry_run: bool = False,
    target_statuses: Optional[List[int]] = None,
) -> None:
    """かんりくん学生ステータスを Salesforce に同期する

    Args:
        dry_run: True の場合は SF への書き込みをせずにプレビューのみ
        target_statuses: 対象とするかんりくんステータスコード（デフォルト: 2〜8 = 書類選考以降）
    """
    from kanrikun_client import KanrikunClient, KanrikunAuthError, KanrikunApiError  # type: ignore

    client_id = os.environ.get("KANRIKUN_CLIENT_ID", "")
    client_secret = os.environ.get("KANRIKUN_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        print("[ERROR] KANRIKUN_CLIENT_ID / KANRIKUN_CLIENT_SECRET が未設定です")
        print("  config/.env に設定してください（かんりくん管理画面 > API連携 で発行）")
        return

    statuses = target_statuses or [2, 3, 4, 5, 6, 7, 8]
    status_labels = [STATUS_LABELS.get(s, str(s)) for s in statuses]

    print("\n" + "=" * 60)
    print(f"  かんりくん → Salesforce 同期{'（DRY RUN）' if dry_run else ''}")
    print("=" * 60)
    print(f"  対象ステータス: {', '.join(status_labels)}")
    print()

    # ── かんりくん接続
    try:
        kk = KanrikunClient(client_id, client_secret)
    except Exception as e:
        print(f"[ERROR] かんりくん初期化エラー: {e}")
        return

    # ── キャッシュ読み込み
    cache = load_cache()
    new_cache = dict(cache)

    # ── ステータスごとに学生取得（APIが単一ステータスのフィルターのため）
    all_students: List[Dict[str, Any]] = []
    for status_code in statuses:
        try:
            students = kk.get_all_students(search={"status": status_code})
            all_students.extend(students)
            print(f"  {STATUS_LABELS.get(status_code, status_code)}: {len(students)}件取得")
        except KanrikunAuthError as e:
            print(f"  [ERROR] 認証エラー: {e}")
            return
        except KanrikunApiError as e:
            print(f"  [警告] status={status_code} 取得エラー: {e}")

    print(f"\n  合計 {len(all_students)}件。差分チェック中...\n")

    if not all_students:
        print("  取得対象の学生がいませんでした。")
        return

    # ── SF接続
    sf = None
    if not dry_run:
        try:
            sf = get_sf()
        except Exception as e:
            print(f"[ERROR] Salesforce接続エラー: {e}")
            return

    # ── 差分チェック・更新
    updated_count = 0
    skipped_count = 0
    not_found_count = 0

    for student in all_students:
        stu_id = str(student.get("id", ""))
        kk_status = int(student.get("status", 0))
        full_name = f"{student.get('sei_kanji', '')}{student.get('mei_kanji', '')}".strip()
        email = student.get("pc_email") or student.get("mobile_email") or ""
        phone = student.get("mobile_number") or ""

        # ── ステータス変更チェック
        cached_status = cache.get(stu_id)
        if cached_status == kk_status:
            skipped_count += 1
            continue

        old_label = STATUS_LABELS.get(cached_status, "（初回）") if cached_status is not None else "（初回）"
        new_label = STATUS_LABELS.get(kk_status, str(kk_status))

        # ── SF Account 検索
        sf_account = None
        if not dry_run and sf:
            try:
                sf_account = find_sf_account(sf, email=email, phone=phone, name=full_name)
            except Exception as e:
                print(f"  [{full_name}] SF検索エラー: {e}")
                continue

        if not dry_run and sf_account is None:
            print(f"  [{full_name}] SFに見つかりません → スキップ（{old_label} → {new_label}）")
            not_found_count += 1
            new_cache[stu_id] = kk_status  # 見つからなくてもキャッシュ更新
            continue

        # ── 更新フィールドを決定
        sf_status_val = KANRIKUN_TO_SF_STATUS.get(kk_status)
        sf_phase_val = KANRIKUN_TO_SF_PHASE.get(kk_status)

        update_fields: Dict[str, Any] = {}
        if sf_status_val:
            update_fields["Status__pc"] = sf_status_val
        if sf_phase_val:
            update_fields["Phase__pc"] = sf_phase_val

        # ── 表示
        display_name = sf_account["name"] if sf_account else full_name
        changes = []
        if sf_status_val:
            current_status = sf_account.get("status") if sf_account else "─"
            changes.append(f"Status: {current_status} → {sf_status_val}")
        if sf_phase_val:
            current_phase = sf_account.get("phase") if sf_account else "─"
            changes.append(f"Phase: {current_phase} → {sf_phase_val}")

        change_str = " / ".join(changes) if changes else "（更新フィールドなし）"
        print(f"  [{display_name}] {old_label} → {new_label}")
        print(f"    {change_str}")

        # ── SF 書き込み
        if not dry_run and sf and sf_account and update_fields:
            try:
                sf.Account.update(sf_account["id"], update_fields)
            except Exception as e:
                print(f"    [ERROR] SF更新エラー: {e}")
                continue

        new_cache[stu_id] = kk_status
        updated_count += 1

    # ── キャッシュ保存
    if not dry_run:
        save_cache(new_cache)

    print()
    print("=" * 60)
    print(f"  完了: 更新={updated_count}件 / 変更なし={skipped_count}件 / SF未マッチ={not_found_count}件")
    if dry_run:
        print("  ※ DRY RUN のため実際の更新は行われていません")
    print("=" * 60)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="かんりくん → Salesforce 同期",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
例:
  python3 kanrikun_sync.py                      # 通常同期（全差分を更新）
  python3 kanrikun_sync.py --dry-run            # プレビューのみ（SF更新なし）
  python3 kanrikun_sync.py --status 3 4         # 内定・内定承諾のみ同期
  python3 kanrikun_sync.py --reset-cache        # キャッシュをリセットして全件チェック
        """,
    )
    parser.add_argument("--dry-run", action="store_true", help="実際の更新をせずにプレビューのみ")
    parser.add_argument(
        "--status", type=int, nargs="+",
        help="対象ステータス番号（例: --status 3 4 5）デフォルト: 2 3 4 5 6 7 8",
    )
    parser.add_argument("--reset-cache", action="store_true", help="差分キャッシュをリセット")
    args = parser.parse_args()

    if args.reset_cache:
        if os.path.exists(CACHE_FILE):
            os.remove(CACHE_FILE)
            print(f"キャッシュをリセットしました: {CACHE_FILE}")
        else:
            print("キャッシュファイルが存在しません。")

    sync_to_salesforce(dry_run=args.dry_run, target_statuses=args.status)


if __name__ == "__main__":
    main()
