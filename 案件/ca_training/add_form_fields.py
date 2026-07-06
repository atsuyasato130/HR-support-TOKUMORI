"""
【TOKUMORI】28卒 採用要件ヒアリングシート_最新 に3設問を追加する使い捨てスクリプト。

- 年間休日（短文）/ 転勤の有無（ラジオ）→ 「想定初任給・年収レンジ」の直後
- 見送り(NG)学生像（段落）→ 「採用ペルソナ想定」の直後

既存項目の削除・改変はせず、createItem による追加のみ行う。
インデックスずれを避けるため、設問ごとに get → アンカー検索 → 挿入を順番に実行する。
"""

import logging

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

TOKEN_PATH = (
    "/Users/atsuyasato130/Claude AI/tokumori/agents/"
    "hr_support/config/token_sheets.json"
)
FORM_ID = "10Ev7OrgVIp3WQ3Tuc3RqePcCfONqydOfMEpY5udu8DU"


def get_service():
    creds = Credentials.from_authorized_user_file(TOKEN_PATH)
    return build("forms", "v1", credentials=creds)


def find_index_after(form, anchor_substring):
    """anchor_substring を含むタイトルのitemの「次の」indexを返す。"""
    items = form.get("items", [])
    for i, item in enumerate(items):
        title = item.get("title", "") or ""
        if anchor_substring in title:
            return i + 1
    raise ValueError(f"アンカーが見つかりません: {anchor_substring}")


def insert_item(forms, item_body, anchor_substring):
    form = forms.forms().get(formId=FORM_ID).execute()
    index = find_index_after(form, anchor_substring)
    request = {
        "requests": [
            {
                "createItem": {
                    "item": item_body,
                    "location": {"index": index},
                }
            }
        ]
    }
    forms.forms().batchUpdate(formId=FORM_ID, body=request).execute()
    logging.info("追加: '%s' を index=%d に挿入", item_body["title"], index)


def main():
    forms = get_service()

    nenkan_kyujitsu = {
        "title": "【28卒】年間休日数を教えてください。（例：121日）",
        "questionItem": {
            "question": {
                "required": False,
                "textQuestion": {"paragraph": False},
            }
        },
    }
    tenkin = {
        "title": "【28卒】転勤の有無を教えてください。",
        "questionItem": {
            "question": {
                "required": False,
                "choiceQuestion": {
                    "type": "RADIO",
                    "options": [
                        {"value": "あり"},
                        {"value": "なし"},
                        {"value": "一部あり（職種・エリアによる）"},
                    ],
                },
            }
        },
    }
    ng_student = {
        "title": "【28卒】見送り（NG）となる学生像があれば教えてください。",
        "description": (
            "「こういう学生は紹介を控えてほしい」という基準があればご記入ください"
            "（例：転勤を避けたい/特定の志向 など）。"
        ),
        "questionItem": {
            "question": {
                "required": False,
                "textQuestion": {"paragraph": True},
            }
        },
    }

    # 1) 年間休日 を「想定初任給・年収レンジ」の直後へ
    insert_item(forms, nenkan_kyujitsu, "想定初任給・年収レンジ")
    # 2) 転勤の有無 を「年間休日数」（今追加した設問）の直後へ
    insert_item(forms, tenkin, "年間休日数を教えてください")
    # 3) 見送り(NG)学生像 を「採用ペルソナ想定」の直後へ
    insert_item(forms, ng_student, "採用ペルソナ想定")

    # 検証用に最終状態を出力
    form = forms.forms().get(formId=FORM_ID).execute()
    items = form.get("items", [])
    logging.info("最終item数: %d", len(items))


if __name__ == "__main__":
    main()
