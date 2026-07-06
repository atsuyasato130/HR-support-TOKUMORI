#!/usr/bin/env python3
"""
MCP Server — Lステップ (L Message) REST API

Claude Code から Lステップの友だち・タグ・友だち情報・トーク履歴などを
直接操作できるようにする MCP サーバー。
Python 3.9 対応 (mcp ライブラリ不要・JSON-RPC over stdio を手実装)。

公式リファレンス: https://docs.lineml.jp/
本番ベースURL:    https://api.lineml.jp/v2/api
認証:             Authorization: Bearer {LSTEP_ACCESS_TOKEN}

起動方法 (Claude Code が自動実行):
  "lstep": {"type": "stdio", "command": "/usr/bin/python3",
            "args": ["/path/to/mcp_lstep.py"], "env": {}}
"""

import json
import logging
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] lstep-mcp: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("lstep-mcp")

# ─── 設定 ───────────────────────────────────────────────────────────────────

API_BASE = "https://api.lineml.jp/v2/api"
REQUEST_TIMEOUT = 30

# .env を手動で読み込む（dotenv を使わずに）
_ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config/.env")
if os.path.exists(_ENV_FILE):
    with open(_ENV_FILE, encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                # クォート付き値（KEY="value"）にも対応
                _v = _v.strip().strip('"').strip("'")
                os.environ.setdefault(_k.strip(), _v)


def _get_token() -> str:
    token = os.environ.get("LSTEP_ACCESS_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "LSTEP_ACCESS_TOKEN が未設定です。config/.env に設定してください。"
        )
    return token


def _get_line_token() -> str:
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "LINE_CHANNEL_ACCESS_TOKEN が未設定です。config/.env に設定してください。"
        )
    return token


# ─── HTTP ヘルパ ──────────────────────────────────────────────────────────────

def _request(method, path, params=None, body=None, base_url=None):
    """Lステップ API を呼び出し、レスポンス dict を返す。

    method: "GET" / "POST" / "DELETE"
    path:   "/friends" などのパス (base_url 指定時は無視)
    params: クエリパラメータ dict (None 不可値は除外)
    body:   リクエストボディ dict
    base_url: フルURL を直接指定する場合 (カスタムエンドポイント用)
    """
    url = base_url if base_url else (API_BASE + path)

    if params:
        # None / 空文字を除外し、リストは複数キーで展開
        clean = {}
        for key, value in params.items():
            if value is None or value == "":
                continue
            clean[key] = value
        if clean:
            url = url + "?" + urllib.parse.urlencode(clean, doseq=True)

    data = None
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")

    headers = {
        "Authorization": "Bearer " + _get_token(),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8")
        except (UnicodeDecodeError, OSError) as read_exc:
            detail = "(レスポンス本文の読取に失敗: {})".format(read_exc)
        # ログにはクエリ文字列を除いたパスのみ・本文は切り詰めて出す
        logger.error("HTTP %s %s -> %s", method, url.split("?")[0], exc.code)
        logger.debug("response body (truncated): %s", detail[:200])
        hint = ""
        if exc.code == 401:
            hint = " (アクセストークンを確認してください)"
        elif exc.code == 429:
            hint = " (レート制限: 10req/秒 または月間上限に到達)"
        raise RuntimeError(
            "APIエラー HTTP {}{}: {}".format(exc.code, hint, detail[:500])
        ) from exc
    except urllib.error.URLError as exc:
        logger.error("接続エラー %s %s -> %s", method, url.split("?")[0], exc.reason)
        raise RuntimeError("接続エラー: {}".format(exc.reason)) from exc
    except json.JSONDecodeError as exc:
        logger.error("JSONデコード失敗 %s %s -> %s", method, url, exc)
        raise RuntimeError("レスポンスのJSON解析に失敗しました") from exc


# ─── LINE Messaging API ヘルパ ───────────────────────────────────────────────

_LINE_API_BASE = "https://api.line.me"
_LINE_DATA_BASE = "https://api-data.line.me"


def _line_request(method, path, body=None):
    """LINE Messaging API を呼び出し、レスポンス dict を返す。"""
    url = _LINE_API_BASE + path
    data = None
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = {
        "Authorization": "Bearer " + _get_line_token(),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {"message": "OK"}
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8")
        except (UnicodeDecodeError, OSError) as read_exc:
            detail = "(レスポンス本文の読取に失敗: {})".format(read_exc)
        logger.error("LINE HTTP %s %s -> %s", method, url.split("?")[0], exc.code)
        logger.debug("LINE response body (truncated): %s", detail[:200])
        hint = ""
        if exc.code == 401:
            hint = " (LINE_CHANNEL_ACCESS_TOKEN を確認してください)"
        elif exc.code == 429:
            hint = " (LINEのレート制限/配信枠超過)"
        raise RuntimeError(
            "LINE APIエラー HTTP {}{}: {}".format(exc.code, hint, detail[:500])
        ) from exc
    except urllib.error.URLError as exc:
        logger.error("LINE 接続エラー %s %s -> %s", method, url.split("?")[0], exc.reason)
        raise RuntimeError("LINE 接続エラー: {}".format(exc.reason)) from exc
    except json.JSONDecodeError as exc:
        logger.error("LINE JSONデコード失敗 %s %s -> %s", method, url, exc)
        raise RuntimeError("LINEレスポンスのJSON解析に失敗しました") from exc


def _line_upload_image(rich_menu_id, image_path):
    """ローカル画像をリッチメニューに紐づけてアップロードする (api-data)。"""
    if not os.path.isfile(image_path):
        raise RuntimeError("画像ファイルが見つかりません: {}".format(image_path))
    lower = image_path.lower()
    if lower.endswith(".png"):
        content_type = "image/png"
    elif lower.endswith(".jpg") or lower.endswith(".jpeg"):
        content_type = "image/jpeg"
    else:
        raise RuntimeError("画像は .png / .jpg / .jpeg のみ対応です")
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    url = "{}/v2/bot/richmenu/{}/content".format(_LINE_DATA_BASE, rich_menu_id)
    headers = {
        "Authorization": "Bearer " + _get_line_token(),
        "Content-Type": content_type,
    }
    req = urllib.request.Request(url, data=image_bytes, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            resp.read()
            return {"message": "画像をアップロードしました"}
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8")
        except (UnicodeDecodeError, OSError):
            detail = ""
        logger.error("LINE image upload -> %s", exc.code)
        raise RuntimeError(
            "LINE 画像アップロードエラー HTTP {}: {}".format(exc.code, detail[:500])
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError("LINE 接続エラー: {}".format(exc.reason)) from exc


def _parse_json_arg(value, default):
    """`*_json` 文字列引数を安全にパースする。"""
    if value is None or value == "":
        return default
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise RuntimeError("JSON引数の解析に失敗しました: {}".format(exc)) from exc


def _to_int(value, field):
    """引数を整数へ変換。失敗時は分かりやすいエラーを投げる。"""
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            "{} は整数値で指定してください: {!r}".format(field, value)
        ) from exc


# 任意URLへPOSTする lstep_custom_action のSSRF対策。
# Lステップのインフラ (lineml.jp) 配下・https のみ許可し、
# file:// やローカル/メタデータエンドポイントへの到達を防ぐ。
_ALLOWED_HOST_SUFFIX = ".lineml.jp"


def _validate_endpoint_url(url):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https":
        raise RuntimeError("endpoint_url は https:// で始まる必要があります")
    host = (parsed.hostname or "").lower()
    if not (host == "lineml.jp" or host.endswith(_ALLOWED_HOST_SUFFIX)):
        raise RuntimeError(
            "許可されていないホストです: {} (lineml.jp 配下のみ許可)".format(host)
        )


def _format(result):
    """API レスポンス dict を人間可読テキストへ整形する。"""
    if not isinstance(result, dict):
        return json.dumps(result, ensure_ascii=False, indent=2)

    lines = []
    if "data" in result:
        data = result["data"]
        if isinstance(data, list):
            lines.append("{} 件取得".format(len(data)))
        lines.append(json.dumps(data, ensure_ascii=False, indent=2))
    if "message" in result:
        lines.append(str(result["message"]))
    if result.get("next_cursor"):
        lines.append("next_cursor: {}".format(result["next_cursor"]))
    if not lines:
        lines.append(json.dumps(result, ensure_ascii=False, indent=2))
    return "\n".join(lines)


# ─── 友だち ─────────────────────────────────────────────────────────────────

def _friends_list(args):
    params = {
        "cursor": args.get("cursor"),
        "limit": args.get("limit"),
        "name": args.get("name"),
        "full_name": args.get("full_name"),
        "system_name": args.get("system_name"),
        "is_blocked": args.get("is_blocked"),
        "created_at_from": args.get("created_at_from"),
        "created_at_to": args.get("created_at_to"),
        "sort_by": args.get("sort_by"),
        "sort_order": args.get("sort_order"),
        "taiou_mark_id": _parse_json_arg(args.get("taiou_mark_id_json"), None),
        "display_status": _parse_json_arg(args.get("display_status_json"), None),
        "include_tags": _parse_json_arg(args.get("include_tags_json"), None),
        "include_friend_infos": _parse_json_arg(
            args.get("include_friend_infos_json"), None
        ),
    }
    return _format(_request("GET", "/friends", params=params))


def _friends_add_tags(args):
    body = {"tag_ids": _parse_json_arg(args["tag_ids_json"], [])}
    path = "/friends/{}/tags".format(args["id"])
    return _format(_request("POST", path, body=body))


def _friends_remove_tags(args):
    body = {"tag_ids": _parse_json_arg(args["tag_ids_json"], [])}
    path = "/friends/{}/tags".format(args["id"])
    return _format(_request("DELETE", path, body=body))


def _friends_set_taiou_mark(args):
    body = {"taiou_mark_id": _to_int(args["taiou_mark_id"], "taiou_mark_id")}
    path = "/friends/{}/taiou-mark".format(args["id"])
    return _format(_request("POST", path, body=body))


# ─── 友だち情報 ───────────────────────────────────────────────────────────────

def _friend_info_create_folder(args):
    body = {"name": args["name"]}
    return _format(_request("POST", "/friend-info-folders", body=body))


def _friend_info_create(args):
    body = {"name": args["name"], "type": args["type"]}
    if args.get("folder_id") not in (None, ""):
        body["folder_id"] = _to_int(args["folder_id"], "folder_id")
    options = _parse_json_arg(args.get("options_json"), None)
    if options is not None:
        body["options"] = options
    return _format(_request("POST", "/friend-infos", body=body))


# ─── タグ ───────────────────────────────────────────────────────────────────

def _tag_folders_list(args):
    return _format(_request("GET", "/tag-folders"))


def _tag_folder_create(args):
    return _format(_request("POST", "/tag-folders", body={"name": args["name"]}))


def _tags_list(args):
    params = {
        "cursor": args.get("cursor"),
        "limit": args.get("limit"),
        "folder_id": args.get("folder_id"),
    }
    return _format(_request("GET", "/tags", params=params))


def _tag_create(args):
    body = {"name": args["name"]}
    if args.get("folder_id") not in (None, ""):
        body["folder_id"] = _to_int(args["folder_id"], "folder_id")
    return _format(_request("POST", "/tags", body=body))


def _tag_update(args):
    body = {}
    if args.get("name"):
        body["name"] = args["name"]
    if "folder_id" in args and args.get("folder_id") != "":
        fid = args.get("folder_id")
        body["folder_id"] = None if fid is None else _to_int(fid, "folder_id")
    path = "/tags/{}".format(_to_int(args["id"], "id"))
    return _format(_request("POST", path, body=body))


def _tag_list_friends(args):
    params = {"cursor": args.get("cursor"), "limit": args.get("limit")}
    path = "/tags/{}/friends".format(_to_int(args["id"], "id"))
    return _format(_request("GET", path, params=params))


def _tag_add_friends(args):
    body = {"friend_ids": _parse_json_arg(args["friend_ids_json"], [])}
    path = "/tags/{}/friends".format(_to_int(args["id"], "id"))
    return _format(_request("POST", path, body=body))


def _tag_remove_friends(args):
    body = {"friend_ids": _parse_json_arg(args["friend_ids_json"], [])}
    path = "/tags/{}/friends".format(_to_int(args["id"], "id"))
    return _format(_request("DELETE", path, body=body))


# ─── 対応マーク ───────────────────────────────────────────────────────────────

def _taiou_marks_list(args):
    params = {"cursor": args.get("cursor"), "limit": args.get("limit")}
    return _format(_request("GET", "/taiou-marks", params=params))


# ─── トーク履歴 ───────────────────────────────────────────────────────────────

def _messages_list(args):
    params = {
        "cursor": args.get("cursor"),
        "limit": args.get("limit"),
        "friend_id": args.get("friend_id"),
        "direction": args.get("direction"),
        "is_unconfirmed": args.get("is_unconfirmed"),
        "staff_id": args.get("staff_id"),
        "has_staff": args.get("has_staff"),
        "sent_at_from": args.get("sent_at_from"),
        "sent_at_to": args.get("sent_at_to"),
        "sort_order": args.get("sort_order"),
    }
    return _format(_request("GET", "/messages", params=params))


# ─── 共通情報 ─────────────────────────────────────────────────────────────────

def _common_info_folders_list(args):
    return _format(_request("GET", "/common-info-folders"))


def _common_infos_list(args):
    params = {
        "cursor": args.get("cursor"),
        "limit": args.get("limit"),
        "folder_id": args.get("folder_id"),
    }
    return _format(_request("GET", "/common-infos", params=params))


def _common_info_update(args):
    body = {}
    if args.get("name"):
        body["name"] = args["name"]
    if args.get("value") is not None:
        body["value"] = args["value"]
    if "folder_id" in args and args.get("folder_id") != "":
        fid = args.get("folder_id")
        body["folder_id"] = None if fid is None else _to_int(fid, "folder_id")
    path = "/common-infos/{}".format(_to_int(args["id"], "id"))
    return _format(_request("POST", path, body=body))


# ─── カスタムAPI（送信系・シナリオ開始など） ───────────────────────────────────

def _custom_action(args):
    """管理画面で作成した受信用エンドポイントURLへ任意ペイロードをPOSTする。

    メッセージ送信・シナリオ配信開始・リマインド設定などはREST APIではなく、
    Lステップ管理画面の「カスタムAPI設定」で発行したエンドポイントURLへの
    POSTで実行する。URLとJSONペイロードを引数で受け取る。
    """
    _validate_endpoint_url(args["endpoint_url"])
    payload = _parse_json_arg(args["payload_json"], {})
    return _format(_request("POST", "", body=payload, base_url=args["endpoint_url"]))


# ─── LINE Messaging API: 配信 ──────────────────────────────────────────────────

def _line_push(args):
    body = {
        "to": args["to"],
        "messages": _parse_json_arg(args["messages_json"], []),
    }
    return _format(_line_request("POST", "/v2/bot/message/push", body=body))


def _line_multicast(args):
    body = {
        "to": _parse_json_arg(args["to_json"], []),
        "messages": _parse_json_arg(args["messages_json"], []),
    }
    return _format(_line_request("POST", "/v2/bot/message/multicast", body=body))


def _line_broadcast(args):
    body = {"messages": _parse_json_arg(args["messages_json"], [])}
    return _format(_line_request("POST", "/v2/bot/message/broadcast", body=body))


def _line_message_quota(args):
    return _format(_line_request("GET", "/v2/bot/message/quota"))


def _line_quota_consumption(args):
    return _format(_line_request("GET", "/v2/bot/message/quota/consumption"))


# ─── LINE Messaging API: リッチメニュー ─────────────────────────────────────────

def _line_richmenu_list(args):
    return _format(_line_request("GET", "/v2/bot/richmenu/list"))


def _line_richmenu_get(args):
    path = "/v2/bot/richmenu/{}".format(args["rich_menu_id"])
    return _format(_line_request("GET", path))


def _line_richmenu_create(args):
    body = _parse_json_arg(args["rich_menu_json"], {})
    return _format(_line_request("POST", "/v2/bot/richmenu", body=body))


def _line_richmenu_upload_image(args):
    return _format(_line_upload_image(args["rich_menu_id"], args["image_path"]))


def _line_richmenu_delete(args):
    path = "/v2/bot/richmenu/{}".format(args["rich_menu_id"])
    return _format(_line_request("DELETE", path))


def _line_richmenu_set_default(args):
    path = "/v2/bot/user/all/richmenu/{}".format(args["rich_menu_id"])
    return _format(_line_request("POST", path))


def _line_richmenu_cancel_default(args):
    return _format(_line_request("DELETE", "/v2/bot/user/all/richmenu"))


def _line_richmenu_link_user(args):
    path = "/v2/bot/user/{}/richmenu/{}".format(args["user_id"], args["rich_menu_id"])
    return _format(_line_request("POST", path))


def _line_richmenu_unlink_user(args):
    path = "/v2/bot/user/{}/richmenu".format(args["user_id"])
    return _format(_line_request("DELETE", path))


def _line_richmenu_alias_list(args):
    return _format(_line_request("GET", "/v2/bot/richmenu/alias/list"))


def _line_richmenu_alias_create(args):
    body = {
        "richMenuAliasId": args["rich_menu_alias_id"],
        "richMenuId": args["rich_menu_id"],
    }
    return _format(_line_request("POST", "/v2/bot/richmenu/alias", body=body))


def _line_richmenu_alias_update(args):
    body = {"richMenuId": args["rich_menu_id"]}
    path = "/v2/bot/richmenu/alias/{}".format(args["rich_menu_alias_id"])
    return _format(_line_request("POST", path, body=body))


def _line_richmenu_alias_delete(args):
    path = "/v2/bot/richmenu/alias/{}".format(args["rich_menu_alias_id"])
    return _format(_line_request("DELETE", path))


# ─── ツールスキーマ ─────────────────────────────────────────────────────────────

_LIMIT = {"type": "integer", "description": "取得件数 (default 50)"}
_CURSOR = {"type": "string", "description": "ページングカーソル"}

TOOLS = [
    {
        "name": "lstep_list_friends",
        "description": "Lステップの友だち一覧を取得。タグ情報・友だち情報・対応マークを含む。名前/本名/作成日時/対応マーク/表示ステータス/タグ等でフィルタ可能。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "cursor": _CURSOR,
                "limit": _LIMIT,
                "name": {"type": "string", "description": "友だち名で部分一致検索"},
                "full_name": {"type": "string", "description": "本名で部分一致検索"},
                "system_name": {"type": "string", "description": "システム表示名で部分一致検索"},
                "is_blocked": {"type": "boolean", "description": "ブロック状態でフィルタ"},
                "created_at_from": {"type": "string", "description": "作成日時の開始 (ISO8601)"},
                "created_at_to": {"type": "string", "description": "作成日時の終了 (ISO8601)"},
                "sort_by": {"type": "string", "enum": ["created_at", "taiou_mark_updated_at"]},
                "sort_order": {"type": "string", "enum": ["asc", "desc"]},
                "taiou_mark_id_json": {"type": "string", "description": "対応マークID配列のJSON文字列 例:[1,2]"},
                "display_status_json": {"type": "string", "description": "表示ステータス配列のJSON文字列 例:[\"normal\",\"block\"]"},
                "include_tags_json": {"type": "string", "description": "含めるタグID配列のJSON文字列 (最大100)"},
                "include_friend_infos_json": {"type": "string", "description": "含める友だち情報ID配列のJSON文字列 (最大100)"},
            },
        },
    },
    {
        "name": "lstep_add_friend_tags",
        "description": "指定した友だちにタグを追加する。タグ追加時アクション・人数制限・システムメッセージは発生しない。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "友だちID (数値ID または UID)"},
                "tag_ids_json": {"type": "string", "description": "追加するタグID配列のJSON文字列 例:[1,2,3]"},
            },
            "required": ["id", "tag_ids_json"],
        },
    },
    {
        "name": "lstep_remove_friend_tags",
        "description": "指定した友だちのタグを解除する。システムメッセージは作成されない。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "友だちID (数値ID または UID)"},
                "tag_ids_json": {"type": "string", "description": "削除するタグID配列のJSON文字列 例:[2]"},
            },
            "required": ["id", "tag_ids_json"],
        },
    },
    {
        "name": "lstep_set_friend_taiou_mark",
        "description": "指定した友だちの対応マークを設定する。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "友だちID (数値ID または UID)"},
                "taiou_mark_id": {"type": "integer", "description": "対応マークID"},
            },
            "required": ["id", "taiou_mark_id"],
        },
    },
    {
        "name": "lstep_create_friend_info_folder",
        "description": "友だち情報フォルダを新規作成する。",
        "inputSchema": {
            "type": "object",
            "properties": {"name": {"type": "string", "description": "フォルダ名"}},
            "required": ["name"],
        },
    },
    {
        "name": "lstep_create_friend_info",
        "description": "友だち情報(項目)を新規作成する。type が select の場合は options_json が必須。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "項目名"},
                "type": {"type": "string", "description": "select / string / number / date 等"},
                "folder_id": {"type": "integer", "description": "友だち情報フォルダID (任意)"},
                "options_json": {"type": "string", "description": "selectの選択肢配列のJSON文字列 例:[{\"value\":\"赤\",\"color\":\"#FF0000\"}]"},
            },
            "required": ["name", "type"],
        },
    },
    {
        "name": "lstep_list_tag_folders",
        "description": "タグフォルダ一覧を取得する。",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "lstep_create_tag_folder",
        "description": "タグフォルダを新規作成する。",
        "inputSchema": {
            "type": "object",
            "properties": {"name": {"type": "string", "description": "フォルダ名"}},
            "required": ["name"],
        },
    },
    {
        "name": "lstep_list_tags",
        "description": "タグ一覧を取得する。folder_id でフォルダ絞り込み可能。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "cursor": _CURSOR,
                "limit": _LIMIT,
                "folder_id": {"type": "integer", "description": "フォルダID (任意)"},
            },
        },
    },
    {
        "name": "lstep_create_tag",
        "description": "タグを新規作成する。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "タグ名"},
                "folder_id": {"type": "integer", "description": "タグフォルダID (任意)"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "lstep_update_tag",
        "description": "タグを更新する (名前・所属フォルダ)。folder_id を null にすると未分類へ移動。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "description": "タグID"},
                "name": {"type": "string", "description": "新しいタグ名 (任意)"},
                "folder_id": {"type": "integer", "description": "移動先フォルダID (任意 / null可)"},
            },
            "required": ["id"],
        },
    },
    {
        "name": "lstep_list_tag_friends",
        "description": "指定したタグが付与されている友だち一覧を取得する。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "description": "タグID"},
                "cursor": _CURSOR,
                "limit": _LIMIT,
            },
            "required": ["id"],
        },
    },
    {
        "name": "lstep_add_friends_to_tag",
        "description": "指定したタグを複数の友だちに一括付与する (最大100件)。システムメッセージは作成されない。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "description": "タグID"},
                "friend_ids_json": {"type": "string", "description": "友だちID配列のJSON文字列 (数値IDまたはUID, 最大100) 例:[\"12345\",\"Uabcd\"]"},
            },
            "required": ["id", "friend_ids_json"],
        },
    },
    {
        "name": "lstep_remove_friends_from_tag",
        "description": "指定したタグを複数の友だちから一括解除する (最大100件)。システムメッセージは作成されない。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "description": "タグID"},
                "friend_ids_json": {"type": "string", "description": "友だちID配列のJSON文字列 (数値IDまたはUID, 最大100)"},
            },
            "required": ["id", "friend_ids_json"],
        },
    },
    {
        "name": "lstep_list_taiou_marks",
        "description": "対応マーク一覧を取得する。",
        "inputSchema": {
            "type": "object",
            "properties": {"cursor": _CURSOR, "limit": _LIMIT},
        },
    },
    {
        "name": "lstep_list_messages",
        "description": "トーク履歴を取得する。友だち・方向(inbound/outbound/system)・未読・スタッフ・送信日時でフィルタ可能。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "cursor": _CURSOR,
                "limit": _LIMIT,
                "friend_id": {"type": "string", "description": "送信者の友だちID (数値IDまたはUID)"},
                "direction": {"type": "string", "enum": ["inbound", "outbound", "system"]},
                "is_unconfirmed": {"type": "boolean", "description": "true:未読のみ / false:既読のみ"},
                "staff_id": {"type": "integer", "description": "送信操作スタッフID"},
                "has_staff": {"type": "boolean", "description": "true:手動送信のみ"},
                "sent_at_from": {"type": "string", "description": "送信日時の開始 (ISO8601)"},
                "sent_at_to": {"type": "string", "description": "送信日時の終了 (ISO8601)"},
                "sort_order": {"type": "string", "enum": ["asc", "desc"]},
            },
        },
    },
    {
        "name": "lstep_list_common_info_folders",
        "description": "共通情報フォルダ一覧を取得する。",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "lstep_list_common_infos",
        "description": "共通情報一覧を取得する。folder_id で絞り込み可能。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "cursor": _CURSOR,
                "limit": _LIMIT,
                "folder_id": {"type": "integer", "description": "フォルダID (任意)"},
            },
        },
    },
    {
        "name": "lstep_update_common_info",
        "description": "共通情報を更新する (名前・値・所属フォルダ)。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "description": "共通情報ID"},
                "name": {"type": "string", "description": "共通情報名 (任意)"},
                "value": {"type": "string", "description": "値 (任意)"},
                "folder_id": {"type": "integer", "description": "フォルダID (任意 / null可)"},
            },
            "required": ["id"],
        },
    },
    {
        "name": "lstep_custom_action",
        "description": "メッセージ送信・シナリオ配信開始・リマインド設定など、REST APIに無い操作を実行する。Lステップ管理画面の『カスタムAPI設定』で発行した受信用エンドポイントURLへ任意のJSONペイロードをPOSTする。endpoint_url と payload_json を指定する。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "endpoint_url": {"type": "string", "description": "管理画面で発行したカスタムエンドポイントの完全なURL"},
                "payload_json": {"type": "string", "description": "送信するJSONペイロードの文字列 (UID等のパラメータを含む)"},
            },
            "required": ["endpoint_url", "payload_json"],
        },
    },
    # ─── LINE Messaging API（直接操作・Lステップ履歴/分析には載らない点に注意） ───
    {
        "name": "line_push_message",
        "description": "LINE Messaging APIで特定ユーザー(UID)にプッシュ配信する。注意: この配信はLステップの配信履歴/分析には記録されない。messages_json はLINEのmessageオブジェクト配列(最大5件)。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "送信先のLINEユーザーID(UID)"},
                "messages_json": {"type": "string", "description": "messageオブジェクト配列のJSON文字列 例:[{\"type\":\"text\",\"text\":\"こんにちは\"}]"},
            },
            "required": ["to", "messages_json"],
        },
    },
    {
        "name": "line_multicast",
        "description": "LINE Messaging APIで複数ユーザー(最大500)に同一メッセージを配信する。注意: Lステップ履歴/分析には載らない。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "to_json": {"type": "string", "description": "UID配列のJSON文字列 (最大500) 例:[\"U1\",\"U2\"]"},
                "messages_json": {"type": "string", "description": "messageオブジェクト配列のJSON文字列 (最大5件)"},
            },
            "required": ["to_json", "messages_json"],
        },
    },
    {
        "name": "line_broadcast",
        "description": "LINE Messaging APIで全友だちに一斉配信する。注意: Lステップ履歴/分析には載らない。大量配信時は枠消費に注意。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "messages_json": {"type": "string", "description": "messageオブジェクト配列のJSON文字列 (最大5件)"},
            },
            "required": ["messages_json"],
        },
    },
    {
        "name": "line_get_message_quota",
        "description": "当月のメッセージ配信上限(無料枠等)を取得する。副作用なし。",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "line_get_quota_consumption",
        "description": "当月これまでに消費したメッセージ配信数を取得する。副作用なし。",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "line_list_rich_menus",
        "description": "作成済みリッチメニューの一覧を取得する。副作用なし。",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "line_get_rich_menu",
        "description": "指定リッチメニューの定義を取得する。",
        "inputSchema": {
            "type": "object",
            "properties": {"rich_menu_id": {"type": "string", "description": "リッチメニューID"}},
            "required": ["rich_menu_id"],
        },
    },
    {
        "name": "line_create_rich_menu",
        "description": "リッチメニューを新規作成する(定義のみ。画像は別途 line_upload_rich_menu_image)。rich_menu_json はsize/selected/name/chatBarText/areasを含むLINE仕様のオブジェクト。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "rich_menu_json": {"type": "string", "description": "リッチメニュー定義のJSON文字列 (size, selected, name, chatBarText, areas)"},
            },
            "required": ["rich_menu_json"],
        },
    },
    {
        "name": "line_upload_rich_menu_image",
        "description": "リッチメニューに画像をアップロードする。image_path はローカルの .png/.jpg ファイルパス (2500x1686 等のLINE規定サイズ)。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "rich_menu_id": {"type": "string", "description": "リッチメニューID"},
                "image_path": {"type": "string", "description": "ローカル画像ファイルの絶対パス (.png/.jpg)"},
            },
            "required": ["rich_menu_id", "image_path"],
        },
    },
    {
        "name": "line_delete_rich_menu",
        "description": "指定リッチメニューを削除する。",
        "inputSchema": {
            "type": "object",
            "properties": {"rich_menu_id": {"type": "string", "description": "リッチメニューID"}},
            "required": ["rich_menu_id"],
        },
    },
    {
        "name": "line_set_default_rich_menu",
        "description": "指定リッチメニューを全友だちのデフォルトに設定する。注意: Lステップ側のリッチメニュー設定と競合し得る(後勝ち)。",
        "inputSchema": {
            "type": "object",
            "properties": {"rich_menu_id": {"type": "string", "description": "リッチメニューID"}},
            "required": ["rich_menu_id"],
        },
    },
    {
        "name": "line_cancel_default_rich_menu",
        "description": "デフォルトリッチメニューの設定を解除する。",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "line_link_rich_menu_to_user",
        "description": "特定ユーザー(UID)に個別のリッチメニューを紐づける。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "LINEユーザーID(UID)"},
                "rich_menu_id": {"type": "string", "description": "リッチメニューID"},
            },
            "required": ["user_id", "rich_menu_id"],
        },
    },
    {
        "name": "line_unlink_rich_menu_from_user",
        "description": "特定ユーザー(UID)の個別リッチメニュー紐づけを解除する。",
        "inputSchema": {
            "type": "object",
            "properties": {"user_id": {"type": "string", "description": "LINEユーザーID(UID)"}},
            "required": ["user_id"],
        },
    },
    {
        "name": "line_list_rich_menu_aliases",
        "description": "リッチメニューエイリアス一覧を取得する(タブ切替メニュー用)。",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "line_create_rich_menu_alias",
        "description": "リッチメニューエイリアスを作成する(タブ切替メニューでrichmenuswitchアクションから参照する別名)。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "rich_menu_alias_id": {"type": "string", "description": "エイリアスID (任意の識別子)"},
                "rich_menu_id": {"type": "string", "description": "紐づけるリッチメニューID"},
            },
            "required": ["rich_menu_alias_id", "rich_menu_id"],
        },
    },
    {
        "name": "line_update_rich_menu_alias",
        "description": "リッチメニューエイリアスの紐づけ先を更新する。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "rich_menu_alias_id": {"type": "string", "description": "エイリアスID"},
                "rich_menu_id": {"type": "string", "description": "新しいリッチメニューID"},
            },
            "required": ["rich_menu_alias_id", "rich_menu_id"],
        },
    },
    {
        "name": "line_delete_rich_menu_alias",
        "description": "リッチメニューエイリアスを削除する。",
        "inputSchema": {
            "type": "object",
            "properties": {"rich_menu_alias_id": {"type": "string", "description": "エイリアスID"}},
            "required": ["rich_menu_alias_id"],
        },
    },
]


# ─── ディスパッチ ─────────────────────────────────────────────────────────────

_HANDLERS = {
    "lstep_list_friends": _friends_list,
    "lstep_add_friend_tags": _friends_add_tags,
    "lstep_remove_friend_tags": _friends_remove_tags,
    "lstep_set_friend_taiou_mark": _friends_set_taiou_mark,
    "lstep_create_friend_info_folder": _friend_info_create_folder,
    "lstep_create_friend_info": _friend_info_create,
    "lstep_list_tag_folders": _tag_folders_list,
    "lstep_create_tag_folder": _tag_folder_create,
    "lstep_list_tags": _tags_list,
    "lstep_create_tag": _tag_create,
    "lstep_update_tag": _tag_update,
    "lstep_list_tag_friends": _tag_list_friends,
    "lstep_add_friends_to_tag": _tag_add_friends,
    "lstep_remove_friends_from_tag": _tag_remove_friends,
    "lstep_list_taiou_marks": _taiou_marks_list,
    "lstep_list_messages": _messages_list,
    "lstep_list_common_info_folders": _common_info_folders_list,
    "lstep_list_common_infos": _common_infos_list,
    "lstep_update_common_info": _common_info_update,
    "lstep_custom_action": _custom_action,
    # LINE Messaging API
    "line_push_message": _line_push,
    "line_multicast": _line_multicast,
    "line_broadcast": _line_broadcast,
    "line_get_message_quota": _line_message_quota,
    "line_get_quota_consumption": _line_quota_consumption,
    "line_list_rich_menus": _line_richmenu_list,
    "line_get_rich_menu": _line_richmenu_get,
    "line_create_rich_menu": _line_richmenu_create,
    "line_upload_rich_menu_image": _line_richmenu_upload_image,
    "line_delete_rich_menu": _line_richmenu_delete,
    "line_set_default_rich_menu": _line_richmenu_set_default,
    "line_cancel_default_rich_menu": _line_richmenu_cancel_default,
    "line_link_rich_menu_to_user": _line_richmenu_link_user,
    "line_unlink_rich_menu_from_user": _line_richmenu_unlink_user,
    "line_list_rich_menu_aliases": _line_richmenu_alias_list,
    "line_create_rich_menu_alias": _line_richmenu_alias_create,
    "line_update_rich_menu_alias": _line_richmenu_alias_update,
    "line_delete_rich_menu_alias": _line_richmenu_alias_delete,
}


def _handle_tool(name, args):
    handler = _HANDLERS.get(name)
    if handler is None:
        return "Unknown tool: {}".format(name)
    return handler(args)


# ─── MCP JSON-RPC ループ ────────────────────────────────────────────────────────

def _send(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def main() -> None:
    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            req = json.loads(raw)
        except json.JSONDecodeError:
            continue

        method = req.get("method", "")
        req_id = req.get("id")
        params = req.get("params", {})

        # Notification（id なし）は返答不要
        if req_id is None:
            continue

        if method == "initialize":
            _send({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "lstep-mcp", "version": "1.0.0"},
                },
            })

        elif method == "tools/list":
            _send({"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}})

        elif method == "tools/call":
            tool_name = params.get("name", "")
            tool_args = params.get("arguments", {})
            try:
                result_text = _handle_tool(tool_name, tool_args)
            except Exception as exc:  # ツール単位の失敗はエラーテキストで返す
                logger.error("tool %s failed: %s", tool_name, exc)
                result_text = "エラー: {}".format(exc)
            _send({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": result_text}]},
            })

        elif method == "ping":
            _send({"jsonrpc": "2.0", "id": req_id, "result": {}})

        else:
            _send({
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": "Method not found: {}".format(method)},
            })


if __name__ == "__main__":
    main()
