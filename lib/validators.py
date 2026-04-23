#!/usr/bin/env python3
"""
validators.py — フィールド値バリデーション共通ライブラリ

SalesforceピックリストやNotionフィールドの値を一元的に検証する。
各 Worker の if/else 分岐をこのモジュールに集約し、重複定義を排除する。

## 使い方
  from business.lib.validators import validate_picklist, sanitize_sf_text

  ok, fixed = validate_picklist("GakuchikaRequirement__c", "A")
  # → (True, "A")

  ok, fixed = validate_picklist("IntroductionMethod__c", "URL形式")
  # → (False, "")  ← 不正値は空文字を返す
"""

from __future__ import annotations

from typing import Optional

# ── Salesforce ピックリスト定義 ────────────────────────────────────────
# 追加・変更時はここだけ修正すること

SF_PICKLISTS: dict[str, list[str]] = {
    # 紹介方法
    "IntroductionMethod__c": ["URL", "ATS", "グーグルフォーム"],

    # 学チカ / ガクチカ・スクリーニングレベル
    "GakuchikaRequirement__c": ["S", "A", "B", "C", "D"],
    "FeelingsRequirement__c":  ["S", "A", "B", "C", "D"],
    "IntelligenceCriteria__c": ["S", "A", "B", "C", "D"],
    "HotRequirement__c":       ["S", "A", "B", "C", "D"],

    # 契約フェーズ
    "Phase__c": ["契約完了", "契約進行", "中止", "クローズ"],
}

# Notion側のラベル → SF ピックリスト値 マッピング
_NOTION_TO_SF_LEVEL: dict[str, str] = {
    # GakuchikaRequirement
    "S": "S",
    "S.起業":                               "S",
    "A": "A",
    "A.長期IS・部活(大学)":                  "A",
    "A：長期IS・部活動":                     "A",
    "B": "B",
    "B.留学・立ち上げ(サークル)":             "B",
    "B：留学・立ち上げ":                     "B",
    "C": "C",
    "C.リーダー(バイト・サークル・ボランティア)": "C",
    "D": "D",
    "D.メンバー(バイト・サークル)":           "D",
}

_NOTION_TO_SF_INTRO_METHOD: dict[str, str] = {
    "URL":          "URL",
    "ATS":          "ATS",
    "グーグルフォーム": "グーグルフォーム",
    "Google Form":  "グーグルフォーム",
    "google_form":  "グーグルフォーム",
    "form":         "グーグルフォーム",
}

_NOTION_TO_SF_PHASE: dict[str, str] = {
    "エントリー受付中":   "契約完了",
    "契約（紹介可能）":  "契約完了",
    "契約完了":          "契約完了",
    "契約進行":          "契約進行",
    "中止":              "中止",
    "クローズ":          "クローズ",
}


# ── 検証・変換関数 ─────────────────────────────────────────────────────

def validate_picklist(field_name: str, value: str) -> tuple[bool, str]:
    """
    SF ピックリスト値を検証する。

    Args:
        field_name: SF フィールド名（例: "Phase__c"）
        value: 検証する値

    Returns:
        (is_valid, canonical_value)
        is_valid=False の場合、canonical_value は空文字
    """
    allowed = SF_PICKLISTS.get(field_name)
    if allowed is None:
        # ピックリストとして定義されていないフィールドは通過
        return True, value

    if value in allowed:
        return True, value

    return False, ""


def normalize_level(raw: str) -> Optional[str]:
    """
    Notionの学チカ表記（"A.長期IS・部活(大学)"等）をSFの1文字コード（"A"）に変換する。

    Returns:
        正規化後の値（"S"/"A"/"B"/"C"/"D"）、不明な場合は None
    """
    if not raw:
        return None
    raw = raw.strip()
    # 先頭1文字がS/A/B/C/Dならそのまま
    if raw in ("S", "A", "B", "C", "D"):
        return raw
    # マッピング辞書を参照
    if raw in _NOTION_TO_SF_LEVEL:
        return _NOTION_TO_SF_LEVEL[raw]
    # "A：〜" "A.〜" など先頭文字で判定
    if raw[0] in ("S", "A", "B", "C", "D") and len(raw) > 1 and raw[1] in (".", "：", ":", " "):
        return raw[0]
    return None


def normalize_intro_method(raw: str) -> Optional[str]:
    """
    NotionのIntroductionMethod表記をSFの正規ピックリスト値に変換する。

    Returns:
        "URL" / "ATS" / "グーグルフォーム"、不明な場合は None
    """
    if not raw:
        return None
    raw = raw.strip()
    return _NOTION_TO_SF_INTRO_METHOD.get(raw)


def normalize_phase(raw: str) -> Optional[str]:
    """
    Notionの契約ステータス表記をSFのPhase__cピックリスト値に変換する。

    Returns:
        "契約完了" / "契約進行" / "中止" / "クローズ"、不明な場合は None
    """
    if not raw:
        return None
    raw = raw.strip()
    return _NOTION_TO_SF_PHASE.get(raw)


def sanitize_sf_text(text: str, max_length: int = 32_000) -> str:
    """
    SF テキストフィールドに書き込む前の共通サニタイズ。

    - 前後ホワイトスペース除去
    - 最大長トリム（SF Long Text 上限対策）
    """
    if not text:
        return ""
    text = text.strip()
    if len(text) > max_length:
        text = text[:max_length - 3] + "..."
    return text
