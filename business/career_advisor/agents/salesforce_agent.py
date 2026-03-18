#!/usr/bin/env python3
"""
Salesforce記載エージェント

機能:
  tldv議事録テキストから以下を自動抽出 → Salesforceに直接書き込み
  【新規学生（初回面談）】
    - Account（新卒RecordType）を作成: 固定項目 + 学生情報 + 送客情報
    - Task（活動記録）を作成
    - 不足情報はLステップ情報から補完
  【既存学生（2回目以降）】
    - 選考進捗・就活状況を更新
    - Task（活動記録）を追加

使い方:
  python3 salesforce_agent.py
"""

from __future__ import annotations

import os
import sys
import json
import re
import anthropic
from datetime import date
from dotenv import load_dotenv

BASE = os.path.dirname(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE, "config/.env"))

# utils/ をパスに追加
sys.path.insert(0, os.path.join(BASE, "utils"))
from tldv_client import fetch_all, TldvApiKeyError, TldvApiError  # type: ignore

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
TLDV_API_KEY = os.environ.get("TLDV_API_KEY", "")

# ──────────────────────────────────────────────
# Salesforce 定数
# ──────────────────────────────────────────────

SF_RECORDTYPE_SHINSOTSU = "0122w000001Ry2hAAC"   # 新卒

# Google Sheets（Lステップ情報入力フォーム）
SPREADSHEET_ID = "1xSF3m1MyeZT60VBnECNyi8qqHZPqAX5mZlniPF2Eodc"

# SFフィールドAPI名 → student dict キー の逆引きマッピング
_SF_TO_STUDENT_KEY: dict[str, str] = {
    "PersonEmail": "email",
    "PersonMobilePhone": "phone",
    "KanaLastName__pc": "kana_last_name",
    "KanaFirstName__pc": "kana_first_name",
    "seinengappi__c": "birth_date",
    "koukomei__pc": "high_school",
    "GraduationYears__pc": "graduation_year",
    "PersonGenderIdentity": "gender",
    "Field17__c": "faculty",
    "gakka__c": "department",
    "Field12__c": "career_axis",
    "Field13__c": "gauchika",
    "LastName": "last_name",
    "FirstName": "first_name",
}

# 志望業界の有効値（Field1__c）
INDUSTRY_OPTIONS = [
    "金融", "メーカー", "商社", "IT・通信", "流通・小売", "広告・マスコミ",
    "人材・教育", "インフラ・交通", "コンサル", "デベロッパー", "不動産・建設",
    "旅行・観光", "ブライダル・美容・くらし", "医療・福祉", "小売・流通",
    "公務員・団体職員", "官公庁", "その他",
]

# 希望業界の有効値（HopeIndustry__pc） ※Field1__cとは別フィールド
HOPE_INDUSTRY_OPTIONS = [
    "コンサル・シンクタンク", "金融", "メーカー", "商社", "IT・通信",
    "広告・マスコミ", "人材・教育", "インフラ・交通", "不動産・建設",
    "旅行・観光", "ブライダル・美容・くらし", "医療・福祉", "小売・流通",
    "公務員・団体職員", "電気", "M&A",
]
# Field1__c → HopeIndustry__pc の表記揺れ対応
_INDUSTRY_TO_HOPE: dict[str, str] = {
    "コンサル": "コンサル・シンクタンク",
}

# 希望の会社規模感の有効値（DesiredCompanyScale__pc）
COMPANY_SCALE_OPTIONS = ["大手", "中小", "メガベンチャー", "ベンチャー", "スタートアップ"]

# 希望職種の有効値
OCCUPATION_OPTIONS = [
    "営業", "事務", "コンサルタント", "経理・法務", "人事",
    "為替ディーラー・トレーダー", "証券アナリスト・資産運用", "ファイナンシャル・アドバイザー",
    "企画", "マーケティング", "宣伝・広報", "システムエンジニア・プログラマ",
    "ネットワークエンジニア", "Webデザイナー", "デザイナー", "福祉士・介護士・ホームヘルパー",
    "講師・インストラクター", "建築土木設計・施工管理", "製造・開発・研究",
    "店舗運営・販売・接客", "薬剤師", "公務員", "保育士", "教員", "その他", "未定、決まっていない",
]

# 学科区分の有効値
DEPT_TYPE_OPTIONS = ["文系", "機電", "化生", "建築", "情報", "その他"]

# 卒業年度の有効値
GRAD_YEAR_OPTIONS = ["23卒", "24卒", "25卒", "26卒", "27卒", "28卒", "29卒", "30卒"]

# ガクチカレベルの有効値
GAUCHIKA_LEVEL_OPTIONS = [
    "S：起業",
    "A：長期IS・部活動(体育会系大学)",
    "B：留学・立ち上げ(サークル・ボランティア)",
    "C：リーダー(バイト・サークル・ボランティア)",
    "D：メンバー(バイト・サークル・ボランティア)",
]

# 紹介者の有効 picklist 値（主要なもの）
REPORTER_OPTIONS = [
    "【エ】熊谷穂澄", "【エ】宮内 佑一郎", "【エ】浅葉美緒", "【エ】渡邉りんご", "【エ】木村七菜",
    "000_対象外", "25卒卒業エナジスト", "26卒卒業エナジスト", "27卒卒業エナジスト", "28卒卒業エナジスト",
    "E00_不明", "E001_石川 昂祐",
    "partner063_レッドキャリア", "partner006_バリカツ", "partner009_ナイモノ（ジョーカツ）",
    "partner017_なっつ_理系就活", "partner018_ワンキャリア_スカウト",
    "【社】佐藤篤也", "【社】袴田颯斗", "【社】佐原紗耶", "【社】斎藤 宏太", "【社】松本 麻優",
    "【社】森脇 新大", "【社】大輪 敦", "【社】滝口 加奈子", "【社】中尾 佳澄", "【社】田村 光輝",
    "【社】田中 史織", "【社】渡邊真衣", "【社】二宮大星",
    "【エ】山口 扇世", "【エ】安宅紗英", "【エ】安田 琴美", "【エ】伊神 和希",
    "【エ】伊吹 夢香", "【エ】伊豆田菜々", "【エ】石垣 知紗", "【エ】石川 杏音",
]


# ──────────────────────────────────────────────
# Salesforce 接続
# ──────────────────────────────────────────────

def get_sf():
    from simple_salesforce import Salesforce  # type: ignore
    return Salesforce(
        username=os.environ["SF_USERNAME"],
        password=os.environ["SF_PASSWORD"],
        security_token=os.environ["SF_SECURITY_TOKEN"],
        domain=os.environ.get("SF_DOMAIN", "login"),
    )


def find_university_id(sf, name: str) -> str | None:
    """大学名から CustomObject1__c の ID を検索して返す（部分一致）"""
    if not name:
        return None
    escaped = name.replace("'", "\\'")
    # 完全一致優先
    res = sf.query(f"SELECT Id, Name FROM CustomObject1__c WHERE Name = '{escaped}' LIMIT 1")
    if res.get("records"):
        return res["records"][0]["Id"]
    # 部分一致フォールバック
    res2 = sf.query(f"SELECT Id, Name FROM CustomObject1__c WHERE Name LIKE '%{escaped}%' LIMIT 1")
    if res2.get("records"):
        return res2["records"][0]["Id"]
    return None


# ──────────────────────────────────────────────
# システムプロンプト（拡張版）
# ──────────────────────────────────────────────

EXTRACT_SYSTEM_PROMPT = """あなたはキャリアアドバイザー向けの情報抽出アシスタントです。
面談議事録のテキストから、Salesforceに登録するための情報を抽出してください。

【出力ルール】
- 必ずJSON形式のみを出力する（説明・前置き不要）
- 情報が議事録に記載されていない場合は空文字列 "" を設定する（配列は [] ）
- 日付はYYYY-MM-DD形式で出力する
- 氏名は姓と名を分けて抽出する。分けられない場合はfirst_nameを空にしてlast_nameに全名を入れる
- 次のアクションは箇条書きの配列で出力する
- summaryは面談の重要ポイントを200字程度でまとめる

【志望業界の選択肢】（desired_industryはこのリストから選択・複数可）
金融 / メーカー / 商社 / IT・通信 / 流通・小売 / 広告・マスコミ /
人材・教育 / インフラ・交通 / コンサル / デベロッパー / 不動産・建設 /
旅行・観光 / ブライダル・美容・くらし / 医療・福祉 / 小売・流通 /
公務員・団体職員 / 官公庁 / その他

【希望職種の選択肢】（desired_occupationはこのリストから選択・複数可）
営業 / 事務 / コンサルタント / 経理・法務 / 人事 / 企画 / マーケティング /
宣伝・広報 / システムエンジニア・プログラマ / ネットワークエンジニア /
製造・開発・研究 / 店舗運営・販売・接客 / その他 / 未定、決まっていない

【学科区分の選択肢】（department_typeはこのリストから1つ選択）
文系 / 機電 / 化生 / 建築 / 情報 / その他

【ガクチカレベルの選択肢】（gauchika_levelはこのリストから1つ選択）
S：起業 /
A：長期IS・部活動(体育会系大学) /
B：留学・立ち上げ(サークル・ボランティア) /
C：リーダー(バイト・サークル・ボランティア) /
D：メンバー(バイト・サークル・ボランティア)

【卒業年度の選択肢】（graduation_yearはこのリストから1つ選択）
23卒 / 24卒 / 25卒 / 26卒 / 27卒 / 28卒 / 29卒 / 30卒
- 明確に述べられていない場合は "27卒" を出力する

【希望の会社規模感の選択肢】（desired_company_scaleは複数選択可）
大手 / 中小 / メガベンチャー / ベンチャー / スタートアップ
- 会話の中で規模感・企業タイプに触れていれば推測して出力する

【referrer_guessの出力ルール】
紹介者 = 学生をこのサービスに紹介・送客した人物や媒体。面談を担当したCAとは別の人物。
ミーティングタイトルやカレンダー名・議事録から推測してください。
- タイトルが「【面談】〇〇経由」形式の場合: 〇〇を紹介者として出力
  - 例: "【面談】山口扇世経由" → 紹介者は「山口扇世」
  - 例: "【面談】レッドキャリア経由" → 紹介者は「レッドキャリア」
- 例: "矢部遥花 x 佐藤篤也: 山口扇世_レッドキャリア様" → 紹介者は「レッドキャリア」
- TikTok / Instagram / YouTube / Twitter / X / SNSなど、CAの個人SNSアカウント経由で学生が来た場合 → 面談担当CA名を出力
  - 例: "tiktokがインスタ経由でその面談" → 面談担当CA名（例:「佐藤篤也」）を出力
  - 例: "インスタで見つけた" "TikTokで知った" → 面談担当CA名を出力
- 就活サービス・エージェント媒体（マイナビ・リクナビ・キャリアパーク等）経由の場合 → その媒体名を出力
- 媒体名・パートナー名があれば媒体名を優先して出力
- 面談担当のCAしか登場せず、紹介元が不明な場合は "" を出力（面談CAを紹介者にしない）

【direct_referral_memoの出力ルール】
直紹介判断に使う重要なメモ欄。以下の内容を漏れなく具体的に記載する:
- 学生の強み・人柄・第一印象
- 就活の軸・大事にしたい条件（「大事にしたいこと」「譲れない条件」「軸」として語られた内容）
- 行きたい企業・気になる会社（選考中・参加予定含む）
- ガクチカの概要・経験の質
- 就活の現状・進捗（何社受けているか、内定有無、選考フェーズなど）
- CAからの推薦理由・総評

【career_axisの出力ルール（Field12__c = 就活の軸）】
「大事にしたい条件」「譲れない条件」「就活の軸」として語られた内容を career_axis に記載。
例: 「若いうちに稼ぎたい・キャリアアップ・活気のある社風」など

【current_companiesの出力ルール（Field15__c = 現状の選考企業）】
「行きたい企業」「気になる企業」「受けている企業」「選考中の企業」を current_companies に記載。
選考フェーズも分かれば付記する。

【各フィールドの抽出ルール】
- first_interview_consult: 初回面談で学生が「相談したいこと」「気になること」として最初に話した内容
- desired_company_scale: 希望する会社規模感（複数可）。「大手」「ベンチャー」「安定した会社」等の発言から推測
- company_scale_reason: 規模感を希望する理由
- interest_industry: 興味を持っている業界（自由記述。「気になっている」「興味がある」という発言ベース）
- wanted_companies: 行きたい・気になる会社名3つ程度（選考中含む）
- job_search_axis_three: 就活の軸を3つ列挙（career_axisと同内容を3つに絞って記載）
- job_hunting_end_time: 就活を終わらせたい時期（「夏までに」「〇月に内定を」等）
- past_job_hunting_status: 受けている企業名と選考フェーズの一覧
- job_hunting_agents_media: 現在利用している就活エージェント・サービス・媒体名
- future_dream_mission: 将来の夢や人生のミッション（「将来はこうなりたい」「〇〇したい」等）
- future_dream_background: ミッションの背景・理由（なぜそう思うようになったか）
- gauchika_1: ガクチカのメインエピソード（役割・行動・成果を含む）
- gauchika_2: ガクチカのサブエピソード（別の活動・経験があれば）
- gender: 性別（「男性」「女性」。議事録から明確に判断できる場合のみ、不明なら ""）

【出力JSON形式】
{
  "student": {
    "last_name": "矢部",
    "first_name": "春香",
    "kana_last_name": "ヤベ",
    "kana_first_name": "ハルカ",
    "university": "上智大学",
    "faculty": "理工学部",
    "department": "物質生命理工学科",
    "department_type": "化生",
    "graduation_year": "27卒",
    "email": "",
    "phone": "",
    "circle_club": "管弦楽部（バイオリン）、候補責任者1年",
    "part_time_job": "居酒屋ホール（週3）",
    "career_axis": "バリバリ働く・市場価値向上・20代で稼ぐ",
    "job_search_axis_three": "①若いうちに高収入 ②キャリアアップできる環境 ③活気のある社風",
    "gauchika": "管弦楽部でバイオリン演奏。候補責任者としてSNS運用・広告協賛の新規開拓を担当",
    "gauchika_1": "管弦楽部の候補責任者として広告協賛の新規開拓を実施。SNS運用も担当",
    "gauchika_2": "",
    "gauchika_level": "C：リーダー(バイト・サークル・ボランティア)",
    "job_search_status": "キーエンス2次面接・武田薬品結果待ち",
    "current_companies": "キーエンス(2次)、武田薬品(結果待ち)、ノバルティス(GD終了)",
    "past_job_hunting_status": "キーエンス2次面接、武田薬品結果待ち、M&Aセンター最終落ち",
    "desired_industry": ["金融", "メーカー"],
    "interest_industry": "金融・メーカー・コンサル。特に市場価値を高められる業界に関心",
    "desired_occupation": ["営業"],
    "desired_industry_reason": "市場価値が高く20代で稼げる業界を希望",
    "desired_occupation_reason": "裁量が大きく成長できる営業職を志望",
    "desired_company_scale": ["大手"],
    "company_scale_reason": "安定性とブランド力を重視",
    "first_interview_consult": "面接が苦手で克服したい。業界の絞り方を相談したい",
    "job_hunting_end_time": "夏休み前（7月）までに内定を取りたい",
    "job_hunting_agents_media": "マイナビ、リクナビ",
    "future_dream_mission": "30代で独立・起業したい",
    "future_dream_background": "父親が経営者であり、幼い頃から影響を受けた",
    "referrer_guess": "レッドキャリア",
    "direct_referral_memo": "管弦楽部候補責任者として新規開拓を経験。積極性と実行力あり。",
    "wanted_companies": "三菱商事、キーエンス、野村証券",
    "gender": "男性"
  },
  "activity": {
    "date": "2026-03-02",
    "duration": "60分",
    "advisor_name": "佐藤篤也",
    "summary": "面談内容の要約（200字程度）",
    "next_actions": ["議事録を送付", "次回面談日程URLを送付"],
    "meeting_title": "矢部遥花 x 佐藤篤也: 山口扇世_レッドキャリア様"
  }
}"""


LSTEP_SYSTEM_PROMPT = """Lステップ（LINE公式アカウント管理ツール）の取得情報テキストから、
学生の個人情報を抽出してください。

【出力JSON形式】
{
  "email": "",
  "phone": "",
  "kana_last_name": "",
  "kana_first_name": "",
  "birth_date": ""
}
情報がなければ空文字列 "" を設定。日付はYYYY-MM-DD形式。"""


# ──────────────────────────────────────────────
# 紹介者マッチング
# ──────────────────────────────────────────────

def match_referrer(guess: str) -> str | None:
    """referrer_guess から picklist 値に部分一致マッチング"""
    if not guess:
        return None
    # スペース・特殊文字を除去した形で比較
    guess_clean = re.sub(r"[\s　]", "", guess).lower()

    for option in REPORTER_OPTIONS:
        clean = re.sub(r"[【】\[\]（）]", "", option)
        clean = re.sub(r"partner\d+_", "", clean)
        clean_nospace = re.sub(r"[\s　]", "", clean).lower()
        if guess_clean in clean_nospace or clean_nospace in guess_clean:
            return option

    # 単語単位の部分一致（スペース除去後）
    for option in REPORTER_OPTIONS:
        opt_nospace = re.sub(r"[\s　]", "", option).lower()
        for word in re.split(r"[_\s・]", guess):
            word_clean = re.sub(r"[\s　]", "", word).lower()
            if len(word_clean) >= 2 and word_clean in opt_nospace:
                return option
    return None


# ──────────────────────────────────────────────
# multipicklist ヘルパー
# ──────────────────────────────────────────────

def _normalize_picklist_value(v: str) -> str:
    """半角記号を全角に正規化（SF picklist 値との一致用）"""
    return v.replace("&", "＆")


def join_picklist(values: list, valid_options: list) -> str | None:
    """リストから有効値のみをフィルタして ';' 区切りで結合"""
    normalized = [_normalize_picklist_value(v) for v in values]
    filtered = [v for v in normalized if v in valid_options]
    return ";".join(filtered) if filtered else None


# ──────────────────────────────────────────────
# 議事録入力（3択）
# ──────────────────────────────────────────────

def _paste_text() -> str:
    today = date.today().strftime("%Y/%m/%d")
    print(f"\n議事録テキストを貼り付けてください（空行2回で確定、本日: {today}）:")
    lines = []
    blank_count = 0
    while True:
        line = input()
        if line == "":
            blank_count += 1
            if blank_count >= 2:
                break
            lines.append(line)
        else:
            blank_count = 0
            lines.append(line)
    return "\n".join(lines).strip()


def get_transcript_input() -> str:
    """議事録テキストを取得（tldv URL / ファイル / 貼り付けの3択）"""
    api_status = "（APIキー設定済み）" if TLDV_API_KEY else "（※Businessプランのみ）"
    print("\n【議事録の入力方法を選択】\n")
    print(f"  [1] tldv URL から自動取得 {api_status}")
    print("  [2] エクスポートファイル（.txt）を指定")
    print("  [3] テキストを貼り付け")

    while True:
        choice = input("\n番号を入力 > ").strip()

        if choice == "1":
            url = input("tldv URL > ").strip()
            if not url:
                print("URLを入力してください。")
                continue
            if not TLDV_API_KEY:
                print("\n[注意] TLDV_API_KEY が未設定です（Businessプランが必要）。")
                print("  [2] ファイル指定 または [3] テキスト貼り付けをご利用ください。")
                continue
            try:
                print("\ntldv APIからデータを取得中...")
                data = fetch_all(url, TLDV_API_KEY)
                transcript = data.get("transcript_text", "")
                if not transcript:
                    print("[警告] トランスクリプトが空でした。ハイライトで代替します。")
                    transcript = data.get("highlights_text", "")
                meeting = data.get("meeting", {})
                title = meeting.get("name", "")
                happened_at = meeting.get("happenedAt", "")
                prefix = ""
                if title:
                    prefix += f"【ミーティングタイトル】{title}\n"
                if happened_at:
                    prefix += f"【録画日時】{happened_at}\n"
                return f"{prefix}\n{transcript}" if prefix else transcript
            except TldvApiKeyError as e:
                print(f"\n[APIキーエラー] {e}")
                continue
            except TldvApiError as e:
                print(f"\n[APIエラー] {e}")
                continue

        if choice == "2":
            filepath = input("ファイルパス > ").strip().strip("'\"")
            if not os.path.exists(filepath):
                print(f"ファイルが見つかりません: {filepath}")
                continue
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read().strip()

        if choice == "3":
            return _paste_text()

        print("1・2・3 のいずれかを入力してください。")


# ──────────────────────────────────────────────
# Claude による情報抽出
# ──────────────────────────────────────────────

def _repair_json_strings(raw: str) -> str:
    """JSON文字列値内の未エスケープ改行・制御文字を修正する"""
    result = []
    in_string = False
    escape_next = False
    for ch in raw:
        if escape_next:
            result.append(ch)
            escape_next = False
            continue
        if ch == "\\":
            escape_next = True
            result.append(ch)
            continue
        if ch == '"':
            in_string = not in_string
            result.append(ch)
            continue
        if in_string and ch == "\n":
            result.append("\\n")
            continue
        if in_string and ch == "\r":
            result.append("\\r")
            continue
        result.append(ch)
    return "".join(result)


def extract_sf_data(transcript: str) -> dict:
    print("\n情報を抽出中...")
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=EXTRACT_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"以下の議事録から情報を抽出してください:\n\n{transcript}"}],
    )
    raw = response.content[0].text.strip()
    json_match = re.search(r"\{[\s\S]+\}", raw)
    if not json_match:
        raise ValueError(f"JSON抽出に失敗しました。\n出力:\n{raw}")
    json_str = json_match.group()
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        # 文字列内の未エスケープ改行を修正して再試行
        return json.loads(_repair_json_strings(json_str))


# ──────────────────────────────────────────────
# Google Sheets からの自動補完
# ──────────────────────────────────────────────

def enrich_from_sheet(data: dict, meeting_date: str | None = None) -> dict:
    """Google Sheetsで学生を検索し、個人情報（メール・電話・生年月日・高校名・大学名）を自動補完する"""
    try:
        from sheets_client import search_student_in_sheet, map_sheet_row_to_sf_fields  # type: ignore
    except ImportError:
        return data  # gspread 未インストール or sheets_client 未配置

    s = data["student"]
    full_name = f"{s.get('last_name', '')} {s.get('first_name', '')}".strip()
    if not full_name:
        return data

    try:
        date_hint = f"（面談日: {meeting_date}）" if meeting_date else ""
        print(f"\n  Google Sheetsで「{full_name}」を検索中{date_hint}...")
        row = search_student_in_sheet(
            SPREADSHEET_ID, full_name, meeting_date=meeting_date
        )

        # ── カナ名でフォールバック検索（漢字が違う場合に対応）
        found_by_kana = False
        if not row:
            kana = f"{s.get('kana_last_name', '')} {s.get('kana_first_name', '')}".strip()
            if kana:
                print(f"  → 漢字で見つからず、カナ「{kana}」で再検索中...")
                row = search_student_in_sheet(
                    SPREADSHEET_ID, kana,
                    name_col_candidates=["フリガナを教えてください", "フリガナ", "氏名（カナ）", "カナ氏名"],
                    meeting_date=meeting_date,
                )
                if row:
                    found_by_kana = True

        if not row:
            print("  → シートに該当なし")
            return data

        # ── カナで見つかった場合、シートの正式氏名で学生名を上書き
        if found_by_kana:
            sheet_name = row.get("お名前を教えてください", "").replace("　", " ").strip()
            if sheet_name:
                parts = sheet_name.split()
                if len(parts) >= 2:
                    s["last_name"] = parts[0]
                    s["first_name"] = parts[1]
                elif parts:
                    s["last_name"] = parts[0]
                print(f"  → 氏名をシートから修正: {sheet_name}")

        # ── 大学名をシートから設定（参照型のため map_sheet_row_to_sf_fields では処理されない・必須のため常に上書き）
        sheet_university = row.get("大学名を教えてください", "").strip()
        if sheet_university:
            s["university"] = sheet_university

        sf_fields = map_sheet_row_to_sf_fields(row)
        # シートで常に上書きするフィールド（フォームデータの方が正確）
        _ALWAYS_PREFER_SHEET = {"kana_last_name", "kana_first_name", "graduation_year", "gender"}
        filled = []
        for sf_field, student_key in _SF_TO_STUDENT_KEY.items():
            if sf_fields.get(sf_field):
                if student_key in _ALWAYS_PREFER_SHEET or not s.get(student_key):
                    s[student_key] = sf_fields[sf_field]
                    filled.append(student_key)

        if sheet_university:
            filled.append("university")
        if filled:
            print(f"  → シートから補完: {', '.join(filled)}")
        else:
            print("  → シートにデータあり（追加補完なし）")
    except EnvironmentError:
        pass  # GOOGLE_SERVICE_ACCOUNT_JSON 未設定の場合は静かにスキップ
    except Exception as e:
        print(f"  [警告] Google Sheets検索エラー: {e}")

    return data


# ──────────────────────────────────────────────
# Lステップ情報補完
# ──────────────────────────────────────────────

def infer_kana_if_missing(data: dict) -> dict:
    """カナ名が未設定の場合、Claude APIで漢字から推測して補完する"""
    s = data["student"]
    if s.get("kana_last_name") and s.get("kana_first_name"):
        return data  # 既に設定済み

    last = s.get("last_name", "")
    first = s.get("first_name", "")
    if not last:
        return data

    full_kanji = f"{last} {first}".strip()
    print(f"  カナ名が未設定のため「{full_kanji}」からフリガナを推測中...")

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=100,
            messages=[{
                "role": "user",
                "content": (
                    f"次の日本人名のフリガナをカタカナで出力してください。\n"
                    f"名前: {full_kanji}\n\n"
                    f"JSONのみ出力（説明不要）:\n"
                    f'{{\"kana_last\": \"コバヤシ\", \"kana_first\": \"ハヤト\"}}'
                ),
            }],
        )
        raw = response.content[0].text.strip()
        json_match = re.search(r"\{[\s\S]+?\}", raw)
        if json_match:
            result = json.loads(json_match.group())
            if not s.get("kana_last_name") and result.get("kana_last"):
                s["kana_last_name"] = result["kana_last"]
            if not s.get("kana_first_name") and result.get("kana_first"):
                s["kana_first_name"] = result["kana_first"]
            kana_full = f"{s.get('kana_last_name', '')} {s.get('kana_first_name', '')}".strip()
            print(f"  → フリガナ推測: {kana_full}")
    except Exception as e:
        print(f"  [警告] フリガナ推測エラー: {e}")

    return data


def prompt_lstep_info(data: dict) -> dict:
    """不足情報をLステップから補完するよう促し、入力があればClaudeで解析"""
    s = data.get("student", {})
    missing = []
    if not s.get("email"):
        missing.append("□ メールアドレス")
    if not s.get("phone"):
        missing.append("□ 携帯番号")
    if not s.get("kana_last_name") and not s.get("kana_first_name"):
        missing.append("□ 氏名（カナ）")
    if not s.get("birth_date"):
        missing.append("□ 生年月日")

    if not missing:
        return data

    print("\n" + "─" * 55)
    print("📋 以下の情報がLステップから取得できます:")
    for m in missing:
        print(f"  {m}")
    print("\nLステップの取得情報をテキストで貼り付けてください")
    print("（スキップする場合はそのままEnterを2回押してください）:")
    lines = []
    blank_count = 0
    while True:
        line = input()
        if line == "":
            blank_count += 1
            if blank_count >= 2:
                break
            lines.append(line)
        else:
            blank_count = 0
            lines.append(line)
    lstep_text = "\n".join(lines).strip()

    if not lstep_text:
        print("  → Lステップ情報をスキップしました。")
        return data

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            system=LSTEP_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": lstep_text}],
        )
        raw = response.content[0].text.strip()
        json_match = re.search(r"\{[\s\S]+\}", raw)
        if json_match:
            lstep_data = json.loads(json_match.group())
            s = data["student"]
            for key in ("email", "phone", "kana_last_name", "kana_first_name"):
                if not s.get(key) and lstep_data.get(key):
                    s[key] = lstep_data[key]
            if not s.get("birth_date") and lstep_data.get("birth_date"):
                s["birth_date"] = lstep_data["birth_date"]
            print("  → Lステップ情報を補完しました。")
    except Exception as e:
        print(f"  [警告] Lステップ情報の解析に失敗しました: {e}")

    return data


# ──────────────────────────────────────────────
# プレビュー表示
# ──────────────────────────────────────────────

def confirm_referrer(data: dict) -> dict:
    """紹介者を確認・選択する。自動マッチした場合は確認、なければ一覧から選択"""
    s = data["student"]
    guess = s.get("referrer_guess", "")
    auto_matched = match_referrer(guess)

    print("\n" + "─" * 55)
    if auto_matched:
        print(f"📌 紹介者（自動マッチ）: {auto_matched}")
        yn = input("  この紹介者でOKですか？ [y/n] > ").strip().lower()
        if yn == "y":
            s["_referrer_exact"] = auto_matched
            return data
    else:
        if guess:
            print(f"  紹介者候補「{guess}」がリストに見つかりませんでした。")
        else:
            print("  議事録から紹介者を特定できませんでした。")

    print("\n紹介者を選択してください（番号入力 / 0=スキップ）:")
    for i, opt in enumerate(REPORTER_OPTIONS, 1):
        print(f"  [{i:2d}] {opt}")
    while True:
        sel = input("\n番号 > ").strip()
        if sel == "0" or sel == "":
            print("  → 紹介者をスキップします。")
            break
        if sel.isdigit() and 1 <= int(sel) <= len(REPORTER_OPTIONS):
            s["_referrer_exact"] = REPORTER_OPTIONS[int(sel) - 1]
            print(f"  → 紹介者: {s['_referrer_exact']}")
            break
        print("  有効な番号を入力してください。")

    return data


def preview_data(data: dict, is_new: bool = True):
    s = data.get("student", {})
    a = data.get("activity", {})
    full_name = f"{s.get('last_name', '')} {s.get('first_name', '')}".strip()
    kana = f"{s.get('kana_last_name', '')} {s.get('kana_first_name', '')}".strip()
    meeting_date = a.get("date") or date.today().isoformat()
    confirmed = s.get("_referrer_exact") or ""
    referrer = confirmed or match_referrer(s.get("referrer_guess", "")) or "（未設定・要確認）"
    fac = " ".join(filter(None, [s.get("faculty"), s.get("department")])) or ""

    W = 62  # 表の幅

    def row(label: str, value: str, w_label: int = 18):
        if not value:
            return
        max_val = W - w_label - 5
        lines = []
        # 長い値を折り返し
        while len(value) > max_val:
            lines.append(value[:max_val])
            value = value[max_val:]
        lines.append(value)
        print(f"  {label:<{w_label}}  {lines[0]}")
        for ln in lines[1:]:
            print(f"  {' ' * w_label}  {ln}")

    mode_label = "新規登録" if is_new else "既存レコード更新"
    print("\n" + "=" * W)
    print(f"  Salesforce 書き込み内容確認  【{mode_label}】")
    print("=" * W)

    # ── 基本情報
    print("\n  ■ 基本情報")
    print("  " + "─" * (W - 2))
    row("氏名", full_name or "（取得できず）")
    row("氏名カナ", kana)
    row("性別", s.get("gender", ""))
    row("大学", s.get("university", ""))
    row("学部・学科", fac)
    row("学科区分", s.get("department_type", ""))
    row("卒業年度", s.get("graduation_year") or "27卒（デフォルト）")
    row("高校名", s.get("high_school", ""))

    # ── 連絡先
    print("\n  ■ 連絡先")
    print("  " + "─" * (W - 2))
    row("Email", s.get("email") or "─（シート要確認）")
    row("電話番号", s.get("phone") or "─（シート要確認）")
    row("生年月日", s.get("birth_date", ""))

    # ── 就活情報
    print("\n  ■ 就活情報")
    print("  " + "─" * (W - 2))
    row("希望業界", ", ".join(s.get("desired_industry", [])))
    row("希望職種", ", ".join(s.get("desired_occupation", [])))
    row("希望の会社規模", ", ".join(s.get("desired_company_scale", [])))
    row("規模感の理由", s.get("company_scale_reason", ""))
    row("就活の軸", s.get("career_axis", ""))
    row("就活の軸（3つ）", s.get("job_search_axis_three", ""))
    row("ガクチカレベル", s.get("gauchika_level", ""))
    row("ガクチカ①", s.get("gauchika_1", ""))
    row("ガクチカ②", s.get("gauchika_2", ""))
    row("サークル・団体", s.get("circle_club", ""))
    row("アルバイト", s.get("part_time_job", ""))

    # ── 直紹介情報
    print("\n  ■ 直紹介情報")
    print("  " + "─" * (W - 2))
    row("相談したいこと", s.get("first_interview_consult", ""))
    row("行きたい会社（3つ）", s.get("wanted_companies", ""))
    row("興味のある業界", s.get("interest_industry", ""))
    row("選考中の企業", s.get("current_companies", ""))
    row("受け企業／フェーズ", s.get("past_job_hunting_status", ""))
    row("就活終わらせたい時期", s.get("job_hunting_end_time", ""))
    row("利用エージェント媒体", s.get("job_hunting_agents_media", ""))
    row("将来の夢・ミッション", s.get("future_dream_mission", ""))
    row("ミッションの背景", s.get("future_dream_background", ""))

    # ── 送客情報
    print("\n  ■ 送客情報")
    print("  " + "─" * (W - 2))
    row("紹介者", referrer)
    row("FS面談日", meeting_date)
    row("FS面談予定日", meeting_date)
    if is_new:
        row("ステータス", "支援中")
        row("状況", "初回面談済")
        row("CS経由", "なし ／ 対象外理由: 直紹介対象")
        row("公式LINE登録", "TRUE")

    # ── 活動記録
    print("\n  ■ 活動記録（Task）")
    print("  " + "─" * (W - 2))
    row("面談日", a.get("date") or date.today().isoformat())
    row("所要時間", a.get("duration", ""))
    row("担当CA", a.get("advisor_name", ""))
    row("要約", a.get("summary", ""))
    if a.get("next_actions"):
        row("次のアクション", " ／ ".join(a["next_actions"]))
    print()


# ──────────────────────────────────────────────
# Salesforce 検索
# ──────────────────────────────────────────────

def search_account(sf, full_name: str) -> dict | None:
    """氏名でAccount（PersonAccount: 新卒）を検索。

    スペース有無どちらの形式でもヒットさせるため、姓と名を % でつなぐ。
    例: "平井愛香" → LIKE '%平井%愛香%' → "平井愛香" も "平井 愛香" も一致。
    """
    if not full_name:
        return None
    # 全角/半角スペースで分割し、各パートを % でつなぐ
    parts = re.split(r"[\s　]+", full_name.strip())
    name_keyword = "%".join(p for p in parts if p)
    try:
        soql = (
            f"SELECT Id, Name, PersonEmail, PersonMobilePhone, Status__pc, Phase__pc "
            f"FROM Account WHERE Name LIKE '%{name_keyword}%' "
            f"AND RecordTypeId = '{SF_RECORDTYPE_SHINSOTSU}' LIMIT 3"
        )
        result = sf.query(soql)
        records = result.get("records", [])
        if not records:
            return None
        if len(records) == 1:
            r = records[0]
        else:
            print(f"\n  {len(records)}件のレコードが見つかりました:")
            for i, r in enumerate(records, 1):
                print(f"  [{i}] {r['Name']} | {r.get('PersonEmail', '─')} | 状況:{r.get('Phase__pc', '─')}")
            while True:
                sel = input("  番号を選択（0=新規作成）> ").strip()
                if sel == "0":
                    return None
                if sel.isdigit() and 1 <= int(sel) <= len(records):
                    r = records[int(sel) - 1]
                    break
                print("  有効な番号を入力してください。")
        return {
            "id": r["Id"], "name": r["Name"],
            "email": r.get("PersonEmail", ""), "phone": r.get("PersonMobilePhone", ""),
            "status": r.get("Status__pc", ""), "phase": r.get("Phase__pc", ""),
        }
    except Exception as e:
        print(f"  [検索エラー] {e}")
        return None


# ──────────────────────────────────────────────
# Salesforce 書き込み
# ──────────────────────────────────────────────

def build_account_fields(data: dict, is_new: bool, sf=None) -> dict:
    """Accountのフィールド辞書を構築"""
    s = data["student"]
    a = data["activity"]
    fields = {}

    # ── 氏名
    if s.get("last_name"):
        fields["LastName"] = s["last_name"]
    if s.get("first_name"):
        fields["FirstName"] = s["first_name"]
    if s.get("kana_last_name"):
        fields["KanaLastName__pc"] = s["kana_last_name"]
    if s.get("kana_first_name"):
        fields["KanaFirstName__pc"] = s["kana_first_name"]

    # ── 連絡先
    if s.get("email"):
        fields["PersonEmail"] = s["email"]
    if s.get("phone"):
        fields["PersonMobilePhone"] = s["phone"]
    if s.get("birth_date"):
        fields["seinengappi__c"] = s["birth_date"]
    if s.get("high_school"):
        fields["koukomei__pc"] = s["high_school"]

    # ── 学校情報
    if s.get("faculty"):
        fields["Field17__c"] = s["faculty"]
    elif is_new:
        fields["Field17__c"] = "未記載"  # SFの必須項目のためデフォルト値
    if s.get("department"):
        fields["gakka__c"] = s["department"][:10]  # max length=10
    # 大学名（自由記述・必須 → UniversityName__pc）
    if s.get("university"):
        fields["UniversityName__pc"] = s["university"]
    # 大学名（CustomObject1__c ルックアップ → Field26__c）
    if sf and s.get("university"):
        uid = find_university_id(sf, s["university"])
        if uid:
            fields["Field26__c"] = uid
        else:
            print(f"  [情報] 大学「{s['university']}」はSFマスタに未登録のためスキップ")
    dept_type = s.get("department_type") or ""
    if dept_type in DEPT_TYPE_OPTIONS:
        fields["Field19__c"] = dept_type
    elif is_new:
        fields["Field19__c"] = "その他"

    grad_year = s.get("graduation_year") or ""
    if grad_year in GRAD_YEAR_OPTIONS:
        fields["GraduationYears__pc"] = grad_year
    elif is_new:
        fields["GraduationYears__pc"] = "27卒"

    # ── 性別（PersonGenderIdentity: 男/女）
    gender_raw = s.get("gender", "")
    gender_map = {"男性": "男", "女性": "女", "男": "男", "女": "女"}
    gender_val = gender_map.get(gender_raw, "")
    if gender_val:
        fields["PersonGenderIdentity"] = gender_val

    # ── 課外活動
    if s.get("circle_club"):
        fields["Field22__c"] = s["circle_club"]
    if s.get("part_time_job"):
        fields["Field23__c"] = s["part_time_job"]

    # ── 就活情報
    if s.get("career_axis"):
        fields["Field12__c"] = s["career_axis"]
    if s.get("job_search_axis_three"):
        fields["JobSearchAxisThree__pc"] = s["job_search_axis_three"]
    if s.get("gauchika"):
        fields["Field13__c"] = s["gauchika"]
    if s.get("gauchika_1"):
        fields["GakuchikaTheme1__pc"] = s["gauchika_1"]
    if s.get("gauchika_2"):
        fields["GakuchikaTheme2__pc"] = s["gauchika_2"]
    gauchika_level = s.get("gauchika_level") or ""
    if gauchika_level in GAUCHIKA_LEVEL_OPTIONS:
        fields["Field31__c"] = gauchika_level
    elif is_new:
        fields["Field31__c"] = "D：メンバー(バイト・サークル・ボランティア)"
    if s.get("current_companies"):
        fields["Field15__c"] = s["current_companies"]
    if s.get("past_job_hunting_status"):
        fields["PastJobHuntingStatus__pc"] = s["past_job_hunting_status"]
    if s.get("job_hunting_end_time"):
        fields["JobHuntingEndDesiredTime__pc"] = s["job_hunting_end_time"]
    if s.get("job_hunting_agents_media"):
        fields["CurrentUsingJobHuntingAgentAndMedia__pc"] = s["job_hunting_agents_media"]
    if s.get("first_interview_consult"):
        fields["FirstInterviewCounselingDetail__pc"] = s["first_interview_consult"]
    if s.get("wanted_companies"):
        fields["WantedThreeCompanies__pc"] = s["wanted_companies"]
    if s.get("future_dream_mission"):
        fields["FutureDreamAndLifeMission__pc"] = s["future_dream_mission"]
    if s.get("future_dream_background"):
        fields["FutureDreamAndLifeMissionBackground__pc"] = s["future_dream_background"]

    # ── 希望業界・職種
    industry = join_picklist(s.get("desired_industry", []), INDUSTRY_OPTIONS)
    if industry:
        fields["Field1__c"] = industry
    # HopeIndustry__pc: Field1__cと同内容をHopeIndustry__pc形式にマッピング
    hope_values = []
    for ind in s.get("desired_industry", []):
        mapped = _INDUSTRY_TO_HOPE.get(ind, ind)
        if mapped in HOPE_INDUSTRY_OPTIONS:
            hope_values.append(mapped)
    if hope_values:
        fields["HopeIndustry__pc"] = ";".join(hope_values)
    if s.get("interest_industry"):
        fields["InterestIndustry__pc"] = s["interest_industry"]
    occupation = join_picklist(s.get("desired_occupation", []), OCCUPATION_OPTIONS)
    if occupation:
        fields["DesiredOccupation__pc"] = occupation
    if s.get("desired_industry_reason"):
        fields["Field28__c"] = s["desired_industry_reason"]
    if s.get("desired_occupation_reason"):
        fields["Field29__c"] = s["desired_occupation_reason"]
    # 希望の会社規模感
    company_scale = join_picklist(s.get("desired_company_scale", []), COMPANY_SCALE_OPTIONS)
    if company_scale:
        fields["DesiredCompanyScale__pc"] = company_scale
    if s.get("company_scale_reason"):
        fields["Field30__c"] = s["company_scale_reason"]

    # ── 直紹介メモ
    if s.get("direct_referral_memo"):
        fields["Field21__c"] = s["direct_referral_memo"]

    # ── 紹介者（confirm_referrer()で確定した値を優先）
    referrer = s.get("_referrer_exact") or match_referrer(s.get("referrer_guess", ""))
    if referrer:
        fields["ReportPerson__c"] = referrer

    # ── FS面談日時（録画日 = 面談日）
    meeting_date = a.get("date") or date.today().isoformat()
    fields["InterviewDate__pc"] = meeting_date
    fields["InterviewExpectedDate__pc"] = meeting_date

    # ── 新規のみセットする固定項目
    if is_new:
        fields["RecordTypeId"] = SF_RECORDTYPE_SHINSOTSU
        fields["Status__pc"] = "支援中"
        fields["Phase__pc"] = "初回面談済"
        fields["CS_keiyu__c"] = "なし"
        fields["Field27__c"] = "直紹介対象"
        fields["OfficialLineRegistration__pc"] = True

    # 空文字列・None を除去（boolean は除外しない）
    return {k: v for k, v in fields.items() if v is True or v is False or v}


def write_account(sf, data: dict, existing_id: str | None = None) -> str:
    """Account の新規作成 or 更新"""
    is_new = existing_id is None
    fields = build_account_fields(data, is_new, sf=sf)

    if is_new:
        if "LastName" not in fields:
            fields["LastName"] = "（不明）"
        result = sf.Account.create(fields)
        return result["id"]
    else:
        sf.Account.update(existing_id, fields)
        return existing_id


def build_task_description(a: dict, is_existing: bool = False) -> str:
    parts = []
    if is_existing:
        parts.append("【2回目以降の面談】")
    if a.get("summary"):
        parts.append(f"【面談内容】\n{a['summary']}")
    if a.get("next_actions"):
        actions = "\n".join(f"・{x}" for x in a["next_actions"])
        parts.append(f"【次のアクション】\n{actions}")
    if a.get("duration"):
        parts.append(f"【面談時間】{a['duration']}")
    if a.get("advisor_name"):
        parts.append(f"【担当CA】{a['advisor_name']}")
    return "\n\n".join(parts)


def write_task(sf, data: dict, account_id: str | None = None, is_existing: bool = False) -> str:
    """Task（活動記録）を作成"""
    s = data["student"]
    a = data["activity"]
    full_name = f"{s.get('last_name', '')} {s.get('first_name', '')}".strip() or "（不明）"
    activity_date = a.get("date") or date.today().isoformat()
    prefix = "2回目面談" if is_existing else "面談"
    subject = f"{prefix} - {full_name} ({activity_date})"

    fields = {
        "Subject": subject,
        "Description": build_task_description(a, is_existing),
        "ActivityDate": activity_date,
        "Status": "Completed",
    }
    if account_id:
        fields["WhatId"] = account_id

    result = sf.Task.create(fields)
    return result["id"]


# ──────────────────────────────────────────────
# 選考進捗（pipeline）更新
# ──────────────────────────────────────────────

PIPELINE_SYSTEM_PROMPT = """あなたはキャリアアドバイザー向けの情報抽出アシスタントです。
面談議事録から、弊社経由で推薦した企業の選考進捗情報を抽出してください。

【出力ルール】
- 必ずJSON配列形式のみを出力する（説明・前置き不要）
- 選考に関する話題が出た企業のみ対象（雑談・関係ない話題は除外）
- 日付が不明な場合は null を出力する
- attended_setsumeikai: 一次面接以降の話が出た場合（一次面接参加予定含む）は true

【Status選択基準】
- 説明会参加予定/申し込み中 → 002.説明会参加予定
- 説明会に参加した/参加済み → 003.説明会参加済み
- 説明会後辞退 → 004.説明会参加後辞退
- 書類選考・適性検査中 → 005.書類選考・適性検査
- 書類選考・適性検査NG → 006.書類選考・適性検査ＮＧ
- 書類選考後辞退 → 007.書類選考・適性検査後辞退
- 一次面接参加予定 → 008.一次面接参加予定
- 一次面接通過 → 009.一次面接通過
- 一次面接NG/落ちた/流れた → 010.一次面接NG
- 一次面接辞退 → 011.一次面接後辞退
- 二次面接参加予定 → 012.二次面接参加予定
- 二次面接通過 → 013.二次面接通過
- 二次面接NG → 014.二次面接NG
- 二次面接辞退 → 015.二次面接後辞退
- 三次面接参加予定 → 016.三次面接参加予定
- 三次面接通過 → 017.三次面接通過
- 三次面接NG → 018.三次面接NG
- 三次面接辞退 → 019.三次面接後辞退
- 最終面接参加予定 → 020.最終面接参加予定
- 最終面接通過 → 021.最終面接通過
- 最終面接NG → 022.最終面接NG
- 最終面接辞退 → 023.最終面接後辞退
- 内定 → 024.内定
- 内定承諾 → 025.内定承諾
- 内定後辞退 → 026.内定後辞退
- 内定承諾後辞退 → 027.内定承諾後辞退

【出力JSON形式】
[
  {
    "company_name": "企業名（議事録に登場した名前のまま）",
    "status": "020.最終面接参加予定",
    "attended_setsumeikai": true,
    "first_interview_date": null,
    "second_interview_date": null,
    "third_interview_date": null,
    "last_interview_date": "2026-03-04"
  }
]
選考の話題がない場合は空配列 [] を返してください。"""


def extract_pipeline_updates(transcript: str) -> list:
    """議事録から選考進捗の更新情報を抽出"""
    print("  選考進捗情報を抽出中...")
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=PIPELINE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"以下の議事録から選考進捗情報を抽出してください（本日: {date.today().isoformat()}）:\n\n{transcript}"}],
    )
    raw = response.content[0].text.strip()
    json_match = re.search(r"\[[\s\S]*\]", raw)
    if not json_match:
        return []
    return json.loads(json_match.group())


def fetch_student_pipelines(sf, account_id: str) -> list:
    """学生のpipeline__cレコードを取得"""
    soql = (
        f"SELECT Id, Name, Status__c, Company__c, Company__r.Name, "
        f"Sanka_Check__c, First__c, Second__c, Third__c, Last__c "
        f"FROM pipeline__c WHERE JobApplicant__c = '{account_id}'"
    )
    result = sf.query(soql)
    return result.get("records", [])


def match_pipeline_by_name(pipelines: list, company_name: str) -> dict | None:
    """企業名の部分一致でpipelineレコードをマッチング"""
    def normalize(s: str) -> str:
        return re.sub(r"[\s　株式会社（）()・]", "", s).lower()

    name_clean = normalize(company_name)
    for p in pipelines:
        company = p.get("Company__r") or {}
        sf_name = company.get("Name", "")
        sf_clean = normalize(sf_name)
        if name_clean in sf_clean or sf_clean in name_clean:
            return p
        # 4文字以上の単語でマッチ
        for word in re.split(r"[_\s・　]", company_name):
            w = normalize(word)
            if len(w) >= 4 and w in sf_clean:
                return p
    return None


def preview_pipeline_updates(pipelines: list, updates: list):
    """pipeline更新内容のプレビュー"""
    if not updates:
        print("\n▼ 選考進捗（pipeline）: 更新対象なし")
        return
    print("\n▼ 選考進捗（pipeline）更新予定")
    for u in updates:
        matched = match_pipeline_by_name(pipelines, u.get("company_name", ""))
        if matched:
            company_sf = (matched.get("Company__r") or {}).get("Name", "─")
            current = matched.get("Status__c", "─")
            print(f"  [{u.get('company_name')} → {company_sf}]")
            print(f"    Status: {current} → {u.get('status', '─')}")
        else:
            print(f"  [{u.get('company_name')}] → （SFにマッチなし・スキップ）")
            continue
        if u.get("attended_setsumeikai"):
            print(f"    説明会参加チェック: → TRUE")
        for field, label in [
            ("first_interview_date", "一次面接日"),
            ("second_interview_date", "二次面接日"),
            ("third_interview_date", "三次面接日"),
            ("last_interview_date", "最終面接日"),
        ]:
            if u.get(field):
                print(f"    {label}: {u[field]}")
    print()


def update_pipeline_records(sf, pipelines: list, updates: list):
    """pipeline__cのStatus・日付・説明会チェックを更新"""
    if not updates:
        return
    DATE_FIELD_MAP = {
        "first_interview_date": "First__c",
        "second_interview_date": "Second__c",
        "third_interview_date": "Third__c",
        "last_interview_date": "Last__c",
    }
    updated = 0
    for u in updates:
        pipeline = match_pipeline_by_name(pipelines, u.get("company_name", ""))
        if not pipeline:
            print(f"  [スキップ] '{u.get('company_name')}' のpipelineレコードが見つかりません")
            continue
        fields: dict = {}
        if u.get("status"):
            fields["Status__c"] = u["status"]
        if u.get("attended_setsumeikai"):
            fields["Sanka_Check__c"] = True
        for key, sf_field in DATE_FIELD_MAP.items():
            if u.get(key):
                fields[sf_field] = u[key]
        if not fields:
            continue
        company_name = (pipeline.get("Company__r") or {}).get("Name", pipeline["Id"])
        sf.pipeline__c.update(pipeline["Id"], fields)
        print(f"  pipeline更新: {company_name} → {u.get('status', '─')}")
        updated += 1
    if updated:
        print(f"  選考進捗を{updated}件更新しました。")


# ──────────────────────────────────────────────
# メイン
# ──────────────────────────────────────────────

def main():
    print("\n" + "=" * 60)
    print("  Salesforce記載エージェント")
    print("  tldv議事録 → 学生情報・活動記録を自動登録")
    print("=" * 60)

    while True:
        # ① 議事録入力
        transcript = get_transcript_input()
        if not transcript:
            print("議事録が入力されていません。")
            continue

        # ② Claude で情報抽出
        try:
            data = extract_sf_data(transcript)
        except Exception as e:
            print(f"\n[ERROR] 情報抽出に失敗しました: {e}")
            retry = input("再試行しますか？ [y/n] > ").strip().lower()
            if retry == "y":
                continue
            break

        # ②-b 選考進捗抽出
        try:
            pipeline_updates = extract_pipeline_updates(transcript)
        except Exception as e:
            print(f"  [警告] 選考進捗の抽出に失敗しました: {e}")
            pipeline_updates = []

        # ③ スプレッドシートから個人情報を自動補完（サイレント）
        meeting_date = data.get("activity", {}).get("date") or ""
        data = enrich_from_sheet(data, meeting_date=meeting_date or None)

        # ③-b カナ名が未設定の場合は Claude で推測補完
        data = infer_kana_if_missing(data)

        # ④ Salesforce 既存チェック
        s = data.get("student", {})
        full_name = f"{s.get('last_name', '')} {s.get('first_name', '')}".strip()
        sf_conn = None
        existing = None

        try:
            print(f"\nSalesforce で「{full_name}」を確認中...")
            sf_conn = get_sf()
            if full_name:
                existing = search_account(sf_conn, full_name)
        except Exception as e:
            print(f"[ERROR] Salesforce接続エラー: {e}")
            print("環境変数（SF_USERNAME/SF_PASSWORD/SF_SECURITY_TOKEN）を確認してください。")
            break

        # ── 新規か既存かをユーザーが選択
        if existing:
            print(f"\n  既存レコードが見つかりました:")
            print(f"    {existing['name']} / 状況: {existing.get('phase', '─')} / Email: {existing.get('email') or '─'}")
            while True:
                sel = input("  [1] 既存レコードを更新  [2] 新規作成 > ").strip()
                if sel == "1":
                    is_new = False
                    break
                elif sel == "2":
                    is_new = True
                    existing = None
                    break
                print("  1 または 2 を入力してください。")
        else:
            print("  既存レコードなし → 新規作成")
            is_new = True

        # ④-b 選考進捗レコード取得（既存学生のみ）
        student_pipelines = []
        if not is_new:
            try:
                student_pipelines = fetch_student_pipelines(sf_conn, existing["id"])
                if student_pipelines:
                    print(f"  選考進捗: {len(student_pipelines)}件取得")
            except Exception as e:
                print(f"  [警告] pipeline取得エラー: {e}")

        # ⑤ 紹介者確認（自動マッチしない場合のみ質問）
        data = confirm_referrer(data)

        # ⑥ 【書き込み内容確認】表形式プレビュー
        preview_data(data, is_new)
        if not is_new:
            preview_pipeline_updates(student_pipelines, pipeline_updates)

        action = input("実行しますか？ [y=実行 / r=やり直す / q=キャンセル] > ").strip().lower()

        if action == "q":
            print("キャンセルしました。")
            break

        if action == "r":
            try:
                data = extract_sf_data(transcript)
                meeting_date = data.get("activity", {}).get("date") or ""
                data = enrich_from_sheet(data, meeting_date=meeting_date or None)
            except Exception as e:
                print(f"\n[ERROR] 再抽出に失敗しました: {e}")
            continue

        if action != "y":
            print("y / r / q のいずれかを入力してください。")
            continue

        # ⑦ Salesforce 書き込み（Account + Task + pipeline 全件）
        try:
            account_id = existing["id"] if existing else None
            account_id = write_account(sf_conn, data, existing_id=account_id)
            task_id = write_task(sf_conn, data, account_id=account_id, is_existing=not is_new)

            updated_pipelines = 0
            if student_pipelines and pipeline_updates:
                update_pipeline_records(sf_conn, student_pipelines, pipeline_updates)
                updated_pipelines = len([
                    u for u in pipeline_updates
                    if match_pipeline_by_name(student_pipelines, u.get("company_name", ""))
                ])

        except Exception as e:
            print(f"\n[ERROR] Salesforce書き込みエラー: {e}")
            cont = input("\n別の議事録を処理しますか？ [y/n] > ").strip().lower()
            if cont != "y":
                print("終了します。")
            break

        # ⑧ 完了サマリー
        W = 62
        action_label = "新規作成" if is_new else "更新"
        print("\n" + "=" * W)
        print("  ✅ Salesforce への書き込みが完了しました")
        print("=" * W)
        print(f"  操作        : {action_label}")
        print(f"  氏名        : {full_name or '(不明)'}")
        print(f"  Account ID  : {account_id}")
        print(f"  Task ID     : {task_id}")
        if updated_pipelines:
            print(f"  選考進捗    : {updated_pipelines}件更新")
        print()

        cont = input("別の議事録を処理しますか？ [y/n] > ").strip().lower()
        if cont != "y":
            print("終了します。")
            break


def run(mode: str | None = None):
    """
    オーケストレーターから呼ばれるエントリポイント。
    mode: 'register' | None（メニュー表示）

    将来追加予定:
      - 'search': 学生検索・情報確認
      - 'update': 選考進捗の一括更新
      - 'pipeline': pipeline__c の登録・更新
    """
    main()


if __name__ == "__main__":
    main()
