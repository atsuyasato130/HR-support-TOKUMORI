"""バックアップした533行の中身を分析する。書き込みは一切行わない。"""
import json
import os
from collections import Counter, defaultdict

PATH = os.path.expanduser("~/Claude AI/scratch_zeals/raw_master_backup_20260703.json")

with open(PATH, encoding="utf-8") as f:
    data = json.load(f)

header = data["header"]
rows = data["rows"]
idx = {name: i for i, name in enumerate(header)}


def get(row, col):
    i = idx[col]
    return row[i] if i < len(row) else ""


print(f"総行数: {len(rows)}")

# 担当者別件数
tanto_counter = Counter(get(r, "担当者") for r in rows)
print("\n■ 担当者別件数")
for k, v in tanto_counter.most_common():
    print(f"  {k}: {v}")

# 候補者名の重複(同一担当者内で同じ名前が複数行)
print("\n■ 候補者名の重複（同一担当者×同一候補者名が複数行）")
name_groups = defaultdict(list)
for r in rows:
    key = (get(r, "担当者"), get(r, "候補者名"))
    name_groups[key].append(r)

dup_count = 0
dup_candidates = 0
for key, group in name_groups.items():
    if len(group) > 1:
        dup_candidates += 1
        dup_count += len(group)
        tanto, name = key
        shoku_list = [get(r, "職種") for r in group]
        print(f"  [{tanto}] {name} × {len(group)}行  職種列: {shoku_list}")

print(f"\n重複候補者数(ユニーク): {dup_candidates}")
print(f"重複による総行数: {dup_count}")
print(f"ユニーク候補者数(推定): {len(name_groups)}")

# 職種列の値の分布
print("\n■ 職種列の値の分布（頻度順）")
shoku_counter = Counter(get(r, "職種") for r in rows)
for k, v in shoku_counter.most_common():
    print(f"  {v:4d}件: {k!r}")

# プロフィールURL列の分布
print("\n■ プロフィールURL列の値の分布")
url_counter = Counter(get(r, "プロフィールURL") for r in rows)
for k, v in url_counter.most_common():
    print(f"  {v:4d}件: {k!r}")

# スカウト種別
print("\n■ スカウト種別の分布")
type_counter = Counter(get(r, "スカウト種別") for r in rows)
for k, v in type_counter.most_common():
    print(f"  {v:4d}件: {k!r}")

# 送付日が入っている件数、ListUp日が入っている件数
sofu_filled = sum(1 for r in rows if get(r, "送付日") not in ("", "null"))
listup_filled = sum(1 for r in rows if get(r, "ListUp日") not in ("", "null", "ー"))
henshin_filled = sum(1 for r in rows if get(r, "返信日") not in ("", "null"))
print(f"\n送付日あり: {sofu_filled} / ListUp日あり(実日付): {listup_filled} / 返信日あり: {henshin_filled}")
