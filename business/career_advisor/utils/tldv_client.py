#!/usr/bin/env python3
"""
tldv API 共通クライアント

使い方:
  from utils.tldv_client import fetch_all, TldvApiKeyError

対応エンドポイント:
  GET /v1alpha1/meetings/{meetingId}           - ミーティング情報
  GET /v1alpha1/meetings/{meetingId}/transcript - 文字起こし
  GET /v1alpha1/meetings/{meetingId}/highlights - ハイライト・要約

⚠️  tldv API は Businessプラン以上が必要:
  https://tldv.io/app/settings/personal-settings/api-keys
  APIキー未設定の場合は TldvApiKeyError が送出される。
"""

import re
import requests

TLDV_API_BASE = "https://pasta.tldv.io"
TLDV_API_VERSION = "v1alpha1"


class TldvApiKeyError(Exception):
    """APIキーが未設定またはBusinessプランでない場合"""


class TldvApiError(Exception):
    """APIリクエストが失敗した場合"""


# ──────────────────────────────────────────────
# ミーティングID抽出
# ──────────────────────────────────────────────

def extract_meeting_id(url_or_id: str) -> str:
    """
    tldv URLまたはIDからミーティングIDを返す。
    例: "https://app.tldv.io/meetings/abc123xyz" → "abc123xyz"
    """
    url_or_id = url_or_id.strip()
    match = re.search(r'/meetings/([a-zA-Z0-9_-]+)', url_or_id)
    if match:
        return match.group(1)
    # URLでなければそのままIDとみなす
    if re.match(r'^[a-zA-Z0-9_-]+$', url_or_id):
        return url_or_id
    raise ValueError(f"ミーティングIDを抽出できませんでした: {url_or_id}")


# ──────────────────────────────────────────────
# API リクエスト共通
# ──────────────────────────────────────────────

def _request(path: str, api_key: str) -> dict:
    if not api_key:
        raise TldvApiKeyError(
            "TLDV_API_KEY が未設定です。\n"
            "tldv BusinessプランのAPIキーを config/.env に設定してください。\n"
            "取得先: https://tldv.io/app/settings/personal-settings/api-keys"
        )

    url = f"{TLDV_API_BASE}/{TLDV_API_VERSION}{path}"
    headers = {"x-api-key": api_key}

    try:
        resp = requests.get(url, headers=headers, timeout=15)
    except requests.exceptions.Timeout:
        raise TldvApiError("リクエストがタイムアウトしました（15秒）")
    except requests.exceptions.RequestException as e:
        raise TldvApiError(f"通信エラー: {e}")

    if resp.status_code == 401:
        raise TldvApiKeyError("APIキーが無効です。tldv設定ページで確認してください。")
    if resp.status_code == 403:
        raise TldvApiKeyError(
            "このミーティングへのアクセス権限がありません。\n"
            "Businessプランかどうか確認してください。"
        )
    if resp.status_code == 404:
        raise TldvApiError("ミーティングが見つかりません。IDを確認してください。")
    if not resp.ok:
        raise TldvApiError(f"APIエラー (HTTP {resp.status_code}): {resp.text[:200]}")

    return resp.json()


# ──────────────────────────────────────────────
# 各エンドポイント
# ──────────────────────────────────────────────

def get_meeting(meeting_id: str, api_key: str) -> dict:
    """ミーティングのメタデータを取得（タイトル・日時・参加者など）"""
    return _request(f"/meetings/{meeting_id}", api_key)


def get_transcript(meeting_id: str, api_key: str) -> list:
    """
    文字起こしデータを取得。
    Returns: [{speaker, text, startTime, endTime}, ...]
    """
    data = _request(f"/meetings/{meeting_id}/transcript", api_key)
    return data.get("data", [])


def get_highlights(meeting_id: str, api_key: str) -> list:
    """
    AIハイライト・ノートを取得。
    Returns: [{text, startTime, topic: {title, summary}}, ...]
    """
    data = _request(f"/meetings/{meeting_id}/highlights", api_key)
    return data.get("data", [])


# ──────────────────────────────────────────────
# テキスト整形
# ──────────────────────────────────────────────

def _seconds_to_mmss(seconds) -> str:
    """秒数を MM:SS 形式に変換"""
    try:
        sec = int(float(seconds))
        return f"{sec // 60:02d}:{sec % 60:02d}"
    except (TypeError, ValueError):
        return "00:00"


def format_transcript_text(transcript_data: list) -> str:
    """
    トランスクリプトデータをClaudeに渡しやすいテキスト形式に変換。
    例: "[01:23] 田中CA: こんにちは、本日はよろしくお願いします。"
    """
    lines = []
    for item in transcript_data:
        speaker = item.get("speaker") or "（話者不明）"
        text = item.get("text", "").strip()
        start = _seconds_to_mmss(item.get("startTime", 0))
        if text:
            lines.append(f"[{start}] {speaker}: {text}")
    return "\n".join(lines)


def format_highlights_text(highlights_data: list) -> str:
    """ハイライトデータを整形して返す"""
    if not highlights_data:
        return "（ハイライトなし）"

    sections = []
    current_topic = None

    for item in highlights_data:
        topic = item.get("topic") or {}
        title = topic.get("title", "")
        summary = topic.get("summary", "")
        text = item.get("text", "").strip()
        start = _seconds_to_mmss(item.get("startTime", 0))

        if title and title != current_topic:
            current_topic = title
            sections.append(f"\n▼ {title}")
            if summary:
                sections.append(f"  {summary}")

        if text:
            sections.append(f"  [{start}] {text}")

    return "\n".join(sections)


# ──────────────────────────────────────────────
# まとめて取得
# ──────────────────────────────────────────────

def fetch_all(url_or_id: str, api_key: str) -> dict:
    """
    ミーティングの全データ（メタデータ・トランスクリプト・ハイライト）を取得。

    Returns:
        {
            "meeting": {...},          # メタデータ
            "transcript": [...],       # 生データ
            "highlights": [...],       # 生データ
            "transcript_text": "...",  # Claudeに渡せるテキスト形式
            "highlights_text": "...",  # 整形済みハイライト
            "meeting_id": "...",
        }
    """
    meeting_id = extract_meeting_id(url_or_id)

    meeting = get_meeting(meeting_id, api_key)
    transcript = get_transcript(meeting_id, api_key)
    highlights = get_highlights(meeting_id, api_key)

    return {
        "meeting_id": meeting_id,
        "meeting": meeting,
        "transcript": transcript,
        "highlights": highlights,
        "transcript_text": format_transcript_text(transcript),
        "highlights_text": format_highlights_text(highlights),
    }
