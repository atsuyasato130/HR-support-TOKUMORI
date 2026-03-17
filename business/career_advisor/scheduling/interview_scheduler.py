#!/usr/bin/env python3
"""
面談調整エージェント

Slack「team_delivery_leadgen_pass」の面談希望メッセージを監視し、
Google Calendar と照合して自動で予定を設定する常駐エージェント。

【制約】
- 面談時間: 10:00〜20:00（30分枠）
- 週最大: 14件
- 休日・祝日は設定しない
- カレンダー名: 【面談】〇〇経由（〇〇はスレッド主の名字）
- Google Meet URL を自動生成してスレッドに返信

【起動方法】
  pip install -r requirements.txt
  python3 agent.py
"""

import os
import json
import time
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
CONFIG_DIR = BASE_DIR.parent / "config"
load_dotenv(CONFIG_DIR / ".env")

import anthropic
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import jpholiday

# ── 設定 ──────────────────────────────────────────────────────────────────────

ANTHROPIC_API_KEY  = os.getenv("ANTHROPIC_API_KEY")
SLACK_BOT_TOKEN    = os.getenv("SLACK_BOT_TOKEN")
SLACK_USER_TOKEN   = os.getenv("SLACK_USER_TOKEN")

TARGET_CHANNEL     = "team_delivery_leadgen_pass"
TARGET_CHANNEL_ID  = "C0A8E5JTWTW"   # チャンネルID（直接指定）
MAX_WEEKLY         = 14          # 週の面談上限
MEET_START_H       = 10         # 面談開始時刻（時）
MEET_END_H         = 20         # 面談終了時刻（時）
DURATION_MIN       = 30         # 面談時間（分）
POLL_SEC           = 60         # ポーリング間隔（秒）

STATE_FILE         = BASE_DIR / "state.json"
LOG_FILE           = BASE_DIR / "agent.log"
CREDENTIALS_FILE   = CONFIG_DIR / "credentials.json"
TOKEN_FILE         = CONFIG_DIR / "token.json"
CALENDAR_SCOPES    = ["https://www.googleapis.com/auth/calendar"]

JST = timezone(timedelta(hours=9))

WEEKDAY_JP = ["月", "火", "水", "木", "金", "土", "日"]

# ── ログ ──────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)

# ── 状態管理 ──────────────────────────────────────────────────────────────────

def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"processed": [], "last_poll_ts": None}


def save_state(state: dict):
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )

# ── Google Calendar ────────────────────────────────────────────────────────────

def get_calendar_service():
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), CALENDAR_SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), CALENDAR_SCOPES
            )
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    return build("calendar", "v3", credentials=creds)


def get_weekly_meeting_count(cal, year: int, week: int) -> int:
    """指定週の【面談】予定件数を返す"""
    monday = datetime.fromisocalendar(year, week, 1).replace(
        hour=0, minute=0, second=0, microsecond=0, tzinfo=JST
    )
    sunday = monday + timedelta(days=7)
    events = cal.events().list(
        calendarId="primary",
        timeMin=monday.isoformat(),
        timeMax=sunday.isoformat(),
        q="【面談】",
        singleEvents=True,
    ).execute()
    return len(events.get("items", []))


def is_slot_free(cal, start: datetime, end: datetime) -> bool:
    """指定時間帯が空きか確認"""
    result = cal.freebusy().query(body={
        "timeMin": start.isoformat(),
        "timeMax": end.isoformat(),
        "items": [{"id": "primary"}],
    }).execute()
    return len(result["calendars"]["primary"]["busy"]) == 0


def create_event(cal, start: datetime, end: datetime, last_name: str) -> dict:
    """Google カレンダーに面談予定を作成（Google Meet 付き）"""
    event = {
        "summary": f"【面談】{last_name}経由",
        "start": {"dateTime": start.isoformat(), "timeZone": "Asia/Tokyo"},
        "end":   {"dateTime": end.isoformat(),   "timeZone": "Asia/Tokyo"},
        "conferenceData": {
            "createRequest": {
                "requestId": f"interview-{int(start.timestamp())}",
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        },
    }
    return cal.events().insert(
        calendarId="primary",
        body=event,
        conferenceDataVersion=1,
    ).execute()

# ── Claude ─────────────────────────────────────────────────────────────────────

def is_meeting_request(claude: anthropic.Anthropic, text: str) -> bool:
    """面談・MTG希望メッセージかどうかを判定"""
    msg = claude.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=5,
        messages=[{
            "role": "user",
            "content": (
                "次のメッセージは面談・打ち合わせ・MTGを希望していますか？"
                "「はい」か「いいえ」のみ答えてください。\n\n" + text
            ),
        }],
    )
    return "はい" in msg.content[0].text


def extract_candidates(claude: anthropic.Anthropic, text: str, today: datetime) -> list[dict]:
    """
    Claude でメッセージから面談希望日時を抽出する。
    返り値: [{"date": "YYYY-MM-DD", "time_start": "HH:MM" or null}, ...]
    """
    prompt = f"""今日は {today.strftime('%Y年%m月%d日（') + WEEKDAY_JP[today.weekday()] + '）'} です。
以下のメッセージに含まれる面談・MTGの希望日時を抽出してください。

メッセージ:
{text}

条件:
- 面談は30分単位です
- 時刻が記載されていない場合は time_start を null にしてください
- 「来週」「今週中」など曖昧な表現は、来週または今週の平日を複数日返してください
- 面談希望が含まれていない場合は [] を返してください

JSONのみ返してください（説明不要）:
[
  {{"date": "YYYY-MM-DD", "time_start": "HH:MM または null"}},
  ...
]"""

    msg = claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = msg.content[0].text.strip()

    # コードブロックを除去
    if "```" in raw:
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else raw
        if raw.startswith("json"):
            raw = raw[4:]

    try:
        data = json.loads(raw)
        # time_start が文字列 "null" の場合も None に統一
        for item in data:
            if item.get("time_start") in ("null", ""):
                item["time_start"] = None
        return data
    except json.JSONDecodeError:
        log.warning(f"JSON 解析失敗: {raw}")
        return []

# ── ユーティリティ ─────────────────────────────────────────────────────────────

def get_last_name(display_name: str) -> str:
    """表示名から名字を取得"""
    if not display_name:
        return "不明"
    # 全角スペース・半角スペースで分割して先頭を取得
    name = display_name.replace("\u3000", " ").strip()
    parts = name.split()
    return parts[0] if parts else name[:3]


def find_available_slot(
    cal,
    candidates: list[dict],
    today: datetime,
) -> tuple[datetime, datetime] | None:
    """候補日程から最初の空き30分枠を返す。なければ None。"""

    for c in candidates:
        date_str = c.get("date", "")
        try:
            date = datetime.strptime(date_str, "%Y-%m-%D").replace(tzinfo=JST)
        except ValueError:
            try:
                date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=JST)
            except ValueError:
                log.warning(f"日付フォーマット不正: {date_str}")
                continue

        # 過去日スキップ
        if date.date() < today.date():
            continue
        # 週末スキップ
        if date.weekday() >= 5:
            continue
        # 祝日スキップ
        if jpholiday.is_holiday(date.date()):
            continue

        # 週の上限チェック
        iso = date.isocalendar()
        weekly_count = get_weekly_meeting_count(cal, iso[0], iso[1])
        if weekly_count >= MAX_WEEKLY:
            log.info(f"{iso[0]}年 第{iso[1]}週 は上限（{MAX_WEEKLY}件）に達しています")
            continue

        time_start = c.get("time_start")
        if time_start:
            # 指定時刻でチェック
            try:
                h, m = map(int, time_start.split(":"))
                start = date.replace(hour=h, minute=m, second=0, microsecond=0)
                end = start + timedelta(minutes=DURATION_MIN)
                if start.hour < MEET_START_H:
                    continue
                if end.hour > MEET_END_H or (end.hour == MEET_END_H and end.minute > 0):
                    continue
                if is_slot_free(cal, start, end):
                    return start, end
            except Exception as e:
                log.warning(f"時刻解析エラー: {time_start} - {e}")
        else:
            # 時刻未指定: 10:00〜19:30 の30分枠を順に探す
            for hour in range(MEET_START_H, MEET_END_H):
                for minute in [0, 30]:
                    start = date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    end = start + timedelta(minutes=DURATION_MIN)
                    if end.hour > MEET_END_H or (end.hour == MEET_END_H and end.minute > 0):
                        break
                    if is_slot_free(cal, start, end):
                        return start, end

    return None

# ── Slack ─────────────────────────────────────────────────────────────────────

def get_channel_id(bot: WebClient, name: str) -> str | None:
    cursor = None
    while True:
        resp = bot.conversations_list(
            types="public_channel,private_channel",
            limit=200,
            cursor=cursor,
        )
        for ch in resp.get("channels", []):
            if ch["name"] == name:
                return ch["id"]
        cursor = resp.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            return None


def get_display_name(bot: WebClient, user_id: str) -> str:
    try:
        info = bot.users_info(user=user_id)
        profile = info["user"]["profile"]
        return profile.get("display_name") or profile.get("real_name", "")
    except SlackApiError:
        return ""


def reply_in_thread(user: WebClient, channel_id: str, thread_ts: str, text: str):
    user.chat_postMessage(
        channel=channel_id,
        thread_ts=thread_ts,
        text=text,
    )

# ── メイン処理 ────────────────────────────────────────────────────────────────

def process_message(
    bot: WebClient,
    user: WebClient,
    claude: anthropic.Anthropic,
    cal,
    channel_id: str,
    msg: dict,
    state: dict,
):
    ts       = msg.get("ts", "")
    text     = msg.get("text", "")
    user_id  = msg.get("user", "")
    thread_ts = msg.get("thread_ts", ts)  # スレッド返信の場合は親 ts

    # サブタイプ（ボット投稿など）はスキップ
    if msg.get("subtype") or msg.get("bot_id"):
        state["processed"].append(ts)
        return

    if not text or not user_id:
        state["processed"].append(ts)
        return

    log.info(f"メッセージ確認: ts={ts} user={user_id} text={text[:50]!r}")

    # 面談希望か判定
    if not is_meeting_request(claude, text):
        log.info("面談希望ではないためスキップ")
        state["processed"].append(ts)
        return

    log.info("面談希望メッセージを検出")

    # スレッド主の情報取得（スレッド返信の場合は親メッセージのユーザー）
    target_user_id = user_id
    if thread_ts != ts:
        try:
            parent = bot.conversations_history(
                channel=channel_id,
                latest=thread_ts,
                oldest=str(float(thread_ts) - 1),
                limit=1,
                inclusive=True,
            )
            msgs = parent.get("messages", [])
            if msgs:
                target_user_id = msgs[0].get("user", user_id)
        except SlackApiError:
            pass

    display_name = get_display_name(bot, target_user_id)
    last_name = get_last_name(display_name)
    log.info(f"スレッド主: {display_name} → 名字: {last_name}")

    # 日程候補を抽出
    today = datetime.now(JST)
    candidates = extract_candidates(claude, text, today)
    if not candidates:
        log.info("日程候補を抽出できませんでした")
        reply_in_thread(
            user, channel_id, ts,
            f"<@{user_id}> 面談のご希望ありがとうございます。"
            "ご都合の良い日程をもう少し具体的にお教えいただけますでしょうか？",
        )
        state["processed"].append(ts)
        return

    log.info(f"候補日程: {candidates}")

    # 空き枠を探す
    slot = find_available_slot(cal, candidates, today)

    if slot is None:
        log.info("空き枠なし → 代替日程を依頼")
        reply_in_thread(
            user, channel_id, ts,
            f"<@{user_id}> ご希望の日程を確認しましたが、現在ご提示いただいた日程での調整が難しい状況です。"
            "別の日程をご提案いただけますでしょうか。",
        )
        state["processed"].append(ts)
        return

    start_dt, end_dt = slot

    # カレンダーに予定を作成
    event = create_event(cal, start_dt, end_dt, last_name)
    meet_url = (
        event.get("conferenceData", {})
             .get("entryPoints", [{}])[0]
             .get("uri", "")
    )

    # Slack スレッドに返信
    date_jp = (
        start_dt.strftime("%Y年%m月%d日（")
        + WEEKDAY_JP[start_dt.weekday()]
        + "）"
    )
    time_jp = f"{start_dt.strftime('%H:%M')}〜{end_dt.strftime('%H:%M')}"

    reply_text = (
        f"<@{user_id}> 面談の日程が確定しました！\n\n"
        f"📅 日時: {date_jp} {time_jp}\n"
        f"🔗 Google Meet: {meet_url}\n\n"
        "当日はこちらの URL よりご参加ください。よろしくお願いいたします。"
    )
    reply_in_thread(user, channel_id, ts, reply_text)

    log.info(f"面談設定完了: {start_dt.isoformat()} 【面談】{last_name}経由")
    state["processed"].append(ts)


def run():
    # クライアント初期化
    bot   = WebClient(token=SLACK_BOT_TOKEN)
    user  = WebClient(token=SLACK_USER_TOKEN)
    claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    cal   = get_calendar_service()

    log.info("=== 面談調整エージェント 起動 ===")

    # チャンネル ID（直接指定）
    channel_id = TARGET_CHANNEL_ID
    log.info(f"監視チャンネル: #{TARGET_CHANNEL} ({channel_id})")

    state = load_state()

    # 初回起動時は直近1時間だけ対象（過去メッセージを遡らない）
    if not state.get("last_poll_ts"):
        state["last_poll_ts"] = str(time.time() - 3600)

    while True:
        try:
            oldest = state["last_poll_ts"]
            # Bot トークンで取得を試み、スコープ不足なら User トークンで再試行
            try:
                resp = bot.conversations_history(
                    channel=channel_id,
                    oldest=oldest,
                    limit=50,
                )
            except SlackApiError as e:
                if e.response.get("error") == "missing_scope":
                    log.info("Bot スコープ不足 → User トークンで再試行")
                    resp = user.conversations_history(
                        channel=channel_id,
                        oldest=oldest,
                        limit=50,
                    )
                else:
                    raise
            messages = list(reversed(resp.get("messages", [])))  # 古い順に処理

            for msg in messages:
                ts = msg.get("ts", "")
                if ts in state["processed"]:
                    continue
                # スレッド返信はスキップ（トップレベルメッセージのみ処理）
                if msg.get("thread_ts") and msg.get("thread_ts") != ts:
                    state["processed"].append(ts)
                    continue
                process_message(bot, user, claude, cal, channel_id, msg, state)

            state["last_poll_ts"] = str(time.time())
            save_state(state)

        except SlackApiError as e:
            log.error(f"Slack API エラー: {e.response['error']}")
        except Exception as e:
            log.error(f"予期しないエラー: {e}", exc_info=True)

        log.info(f"{POLL_SEC}秒後に次のポーリング...")
        time.sleep(POLL_SEC)


if __name__ == "__main__":
    run()
