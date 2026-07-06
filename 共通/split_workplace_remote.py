"""
勤務地設問とリモートワーク有無をMECEに分離する使い捨てスクリプト。

1. 既存の「勤務地（複数選択可）」設問からリモート2選択肢を除去（updateItem）
2. リモートワーク有無の設問（CHECKBOX/4択）を勤務地の直後に追加（createItem）

既存の他設問は改変しない。
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

WORKPLACE_ANCHOR = "勤務地を教えてください"
LOCATION_OPTIONS = [
    "東京",
    "大阪",
    "名古屋",
    "福岡",
    "札幌",
    "仙台",
    "広島",
    "その他（下の備考欄にご記入ください）",
]
REMOTE_OPTIONS = [
    "フルリモート可",
    "ハイブリッド（一部リモート）可",
    "リモートなし（フル出社）",
    "職種・条件による",
]


def get_service():
    creds = Credentials.from_authorized_user_file(TOKEN_PATH)
    return build("forms", "v1", credentials=creds)


def find_workplace(form):
    for i, item in enumerate(form.get("items", [])):
        if WORKPLACE_ANCHOR in (item.get("title", "") or ""):
            return i, item
    raise ValueError("勤務地設問が見つかりません")


def main():
    forms = get_service()
    form = forms.forms().get(formId=FORM_ID).execute()
    wp_index, wp_item = find_workplace(form)
    logging.info("勤務地設問: index=%d itemId=%s", wp_index, wp_item.get("itemId"))

    # 1) 勤務地の選択肢をロケーションのみに更新（リモート2項目を除去）
    update_request = {
        "updateItem": {
            "item": {
                "itemId": wp_item["itemId"],
                "title": wp_item.get("title"),
                "questionItem": {
                    "question": {
                        "required": True,
                        "choiceQuestion": {
                            "type": "CHECKBOX",
                            "options": [{"value": v} for v in LOCATION_OPTIONS],
                        },
                    }
                },
            },
            "location": {"index": wp_index},
            "updateMask": "questionItem.question.choiceQuestion.options",
        }
    }

    # 2) リモートワーク有無を勤務地の直後に追加
    create_request = {
        "createItem": {
            "item": {
                "title": "【28卒】リモートワークの有無を教えてください。（複数選択可）",
                "questionItem": {
                    "question": {
                        "required": False,
                        "choiceQuestion": {
                            "type": "CHECKBOX",
                            "options": [{"value": v} for v in REMOTE_OPTIONS],
                        },
                    }
                },
            },
            "location": {"index": wp_index + 1},
        }
    }

    forms.forms().batchUpdate(
        formId=FORM_ID,
        body={"requests": [update_request, create_request]},
    ).execute()
    logging.info("勤務地の選択肢を更新し、リモート設問を index=%d に追加", wp_index + 1)

    # 検証出力
    form = forms.forms().get(formId=FORM_ID).execute()
    items = form.get("items", [])
    logging.info("最終item数: %d", len(items))
    for i, it in enumerate(items):
        if wp_index <= i <= wp_index + 2:
            q = it.get("questionItem", {}).get("question", {})
            opts = [o.get("value") for o in q.get("choiceQuestion", {}).get("options", [])]
            logging.info("idx=%d title=%s opts=%s", i, (it.get("title") or "")[:40], opts)


if __name__ == "__main__":
    main()
