"""02_マスターの生データ(533行)をYOUTRUSTタブの正式フォーマットへ変換する。
ローカルでのドライラン専用。スプレッドシートへの書き込みは一切行わない。
"""
import json
import os
import re
from collections import Counter

SRC = os.path.expanduser("~/Claude AI/scratch_zeals/raw_master_LATEST.json")
OUT = os.path.expanduser("~/Claude AI/scratch_zeals/transformed_youtrust_rows.json")
FLAGGED_OUT = os.path.expanduser("~/Claude AI/scratch_zeals/flagged_for_review.json")

with open(SRC, encoding="utf-8") as f:
    data = json.load(f)

header = data["header"]
raw_rows = data["rows"]
idx = {name: i for i, name in enumerate(header)}


def get(row, col):
    i = idx[col]
    return row[i] if i < len(row) else ""


REMINDER_TAG = "「高評価」リマインド送付2回目　対象者"

SUFFIX_PATTERNS = [
    re.compile(r"^(AP|FS|IS|AI|AIコンサル|AIコンサルタント)　?TOKUMORI作成（(該当企業外?)）$"),
    re.compile(r"^(AP|FS|IS|AI|AIコンサル|AIコンサルタント)　?TOKUMIRI選定（(該当企業外?)）$"),
    re.compile(r"^(AP|FS|IS|AI|AIコンサル|AIコンサルタント)　?TOKUMORI選定（(該当企業外?)）$"),
]
NO_TAG_SUFFIX_PATTERN = re.compile(r"^(AP|FS|IS|AI|AIコンサル|AIコンサルタント)　?TOKUMORI選定$")

CODE_NORMALIZE = {
    "AP": "AP",
    "FS": "FS",
    "IS": "IS",
    "AI": "AIコンサル",
    "AIコンサル": "AIコンサル",
    "AIコンサルタント": "AIコンサル",
}


def parse_shoku(raw_value):
    """職種セルの生値 -> (正規化職種コード or None, 選定タグ注記 or None, 要確認フラグ)"""
    v = (raw_value or "").strip()
    if v in ("", "null"):
        return None, None, False
    if v == "りりこ":
        return None, f"要確認(元職種欄:{v})", True
    if v == REMINDER_TAG:
        return None, "「高評価」リマインド送付2回目対象", False  # 別行でマージされるので単独出現時のみ経由
    for pat in SUFFIX_PATTERNS:
        m = pat.match(v)
        if m:
            code, tag = m.group(1), m.group(2)
            return CODE_NORMALIZE.get(code, code), f"TOKUMIRI選定:{tag}", False
    m = NO_TAG_SUFFIX_PATTERN.match(v)
    if m:
        code = m.group(1)
        return CODE_NORMALIZE.get(code, code), "TOKUMORI選定", False
    if v in CODE_NORMALIZE:
        return CODE_NORMALIZE[v], None, False
    # 未知の自由記述(例: Omakase SMBセールス)
    return v, None, True


# ── Step A: 同一(担当者, 候補者名)の「高評価リマインド」重複行を統合 ──
groups = {}
order = []
for r in raw_rows:
    key = (get(r, "担当者"), get(r, "候補者名"), get(r, "送付日"))
    groups.setdefault(key, []).append(r)
    if key not in order:
        order.append(key)

merged_rows = []
dropped_tag_rows = 0
multi_job_flagged = []

for key in order:
    group = groups[key]
    if len(group) == 1:
        merged_rows.append((group[0], None))
        continue
    # 複数行: 「高評価」リマインドタグ行と実職種行に分離
    tag_rows = [r for r in group if get(r, "職種") == REMINDER_TAG]
    real_rows = [r for r in group if get(r, "職種") != REMINDER_TAG]
    if len(tag_rows) >= 1 and len(real_rows) == 1:
        # タグ行を実職種行にマージ(タグ行は破棄・メモへ注記)
        merged_rows.append((real_rows[0], "高評価リマインド送付2回目対象"))
        dropped_tag_rows += len(tag_rows)
    else:
        # 想定外パターン(実職種が複数など) → 全行残しつつ要確認
        for r in group:
            merged_rows.append((r, None))
        multi_job_flagged.append({"key": key, "職種一覧": [get(r, "職種") for r in group]})

# ── Step B: 各行をYOUTRUSTタブ用フォーマットへ変換 ──
MEDIA_HEADERS = [
    "候補者ID", "流入チャネル", "担当者", "候補者名", "プロフィールURL",
    "職種", "雇用形態希望", "意欲ステータス", "接点ステータス",
    "ListUp日", "送付日", "返信日", "面談調整日", "面談実施日", "採用日",
    "有効返信", "御礼連絡", "前日リマインド", "NG理由",
    "次アクション", "次アクション期日", "memo", "最終更新日", "スカウト種別",
]

out_rows = []
flagged = []

for i, (r, extra_note) in enumerate(merged_rows, start=1):
    shoku_raw = get(r, "職種")
    shoku_code, shoku_note, need_review = parse_shoku(shoku_raw)

    memo_parts = []
    if shoku_note:
        memo_parts.append(shoku_note)
    if extra_note:
        memo_parts.append(extra_note)
    memo = " / ".join(memo_parts)

    listup = get(r, "ListUp日")
    if listup == "ー":
        listup = ""

    row_out = {
        "候補者ID": f"YT-{i:03d}",
        "流入チャネル": get(r, "スカウト種別") and (
            "有料スカウト" if get(r, "スカウト種別") == "有料" else "無料スカウト"
        ),
        "担当者": get(r, "担当者"),
        "候補者名": get(r, "候補者名"),
        "プロフィールURL": get(r, "プロフィールURL"),
        "職種": shoku_code or "",
        "雇用形態希望": get(r, "雇用形態希望"),
        "意欲ステータス": get(r, "意欲ステータス"),
        "接点ステータス": get(r, "接点ステータス"),
        "ListUp日": listup,
        "送付日": get(r, "送付日"),
        "返信日": (get(r, "返信日") if get(r, "返信日") != "null" else ""),
        "面談調整日": get(r, "面談調整日"),
        "面談実施日": get(r, "面談実施日"),
        "採用日": get(r, "採用日"),
        "有効返信": get(r, "有効返信"),
        "御礼連絡": get(r, "御礼連絡"),
        "前日リマインド": get(r, "前日リマインド"),
        "NG理由": get(r, "NG理由"),
        "次アクション": get(r, "次アクション"),
        "次アクション期日": get(r, "次アクション期日"),
        "memo": memo,
        "最終更新日": "",
        "スカウト種別": get(r, "スカウト種別"),
    }
    out_rows.append(row_out)
    if need_review:
        flagged.append({"候補者ID": i, "担当者": row_out["担当者"], "候補者名": row_out["候補者名"], "元職種欄": shoku_raw})

for item in multi_job_flagged:
    flagged.append({"候補者ID": None, "type": "同一候補者に複数職種タグ", **item})

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out_rows, f, ensure_ascii=False, indent=1)

with open(FLAGGED_OUT, "w", encoding="utf-8") as f:
    json.dump(flagged, f, ensure_ascii=False, indent=1)

print(f"生データ行数: {len(raw_rows)}")
print(f"「高評価」リマインドタグとして統合・破棄した行数: {dropped_tag_rows}")
print(f"変換後の行数(YOUTRUSTタブへ書き込む件数): {len(out_rows)}")
print(f"要確認フラグ件数: {len(flagged)}")

print("\n■ 変換後の職種コード分布")
for k, v in Counter(r["職種"] for r in out_rows).most_common():
    print(f"  {v:4d}件: {k!r}")

print("\n■ 送付/ListUp/返信/面談/採用 の件数(変換後)")
for col in ["ListUp日", "送付日", "返信日", "面談調整日", "面談実施日", "採用日"]:
    n = sum(1 for r in out_rows if r[col] not in ("", "null"))
    print(f"  {col}: {n}")
