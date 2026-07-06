---
name: tldv-autoreg
description: tldv URLから会議内容を取得し、面談/商談を自動分類。面談はSF登録、商談はNotion議事録DBに自動登録。「tldv URLを登録」「この面談を登録」「{URL} を処理」で発火。引数: tldv URL
---

tldv会議を分類して適切なルートで自動登録する。

## 1. URL受取
引数から tldv URL または meeting_id を取得する。

## 2. meeting_router 実行（情報抽出）
```bash
cd "/Users/atsuyasato/Claude AI/ai-empire"
python3 -m agents.hr_support.meeting_router "<tldv_url>" --advisor "佐藤篤也"
```

この実行で以下のJSONが返る:
- `classification.category`: `mendan` / `shodan` / `unknown`
- `classification.confidence`: 0.0〜1.0
- `requires_review`: true の場合は人手確認が必要
- `route`: `sf_register` / `notion_minutes` / `review`
- `sf_payload` (面談の場合): create_fields, update_fields, task, Field21メモ
- `notion_payload` (商談の場合): title, body_markdown, properties, recording_date

## 3. 分岐処理

### category = "mendan" (面談 → SF登録)

**Step A: 重複チェック**
```
hr-support MCP: search_salesforce
SOQL: SELECT Id, Name, PersonMobilePhone, PersonEmail FROM Account
      WHERE Name LIKE '%<姓>%<名>%'
      OR PersonMobilePhone = '<phone>'
      OR PersonEmail = '<email>'
```

重複あり:
- 同一人物確認 (電話番号 or メール一致) → 既存IDにupdateする (is_second_or_later=true で log_sf_meeting)
- 別人 → 新規作成

**Step B: 新規作成 or 既存更新**
- 新規: `create_salesforce_record` with `sf_payload.create_fields`
- 既存: スキップ

**Step C: Account全フィールド更新**
```
hr-support MCP: update_salesforce_record
object_type: Account
record_id: <新規 or 既存ID>
fields_json: sf_payload.update_fields (Field21__cメモ含む)
```

**Step D: 面談ログ作成**
```
hr-support MCP: log_sf_meeting
account_id: <ID>
student_name: sf_payload.task.student_name
meeting_date: sf_payload.task.meeting_date
summary: sf_payload.task.summary
next_actions: sf_payload.task.next_actions
advisor_name: sf_payload.task.advisor_name
duration: sf_payload.task.duration
is_second_or_later: 既存なら true, 新規なら false
```

### category = "shodan" (商談 → Notion議事録)

**Step A: Notion子ページ作成**
```
hr-support MCP: create_notion_child_page
database_id: notion_payload.database_id (2bc48452-bd25-8007-838c-c3c707c953c1)
title: notion_payload.title
properties: notion_payload.properties (録画日を必ず含める)
content: notion_payload.body_markdown
```

### category = "unknown" (要レビュー)

**Step A: Slack通知**
```
hr-support MCP: send_slack_message
channel: #hr-support
message: "⚠️ tldv会議の分類判定不能\nURL: <url>\nタイトル: <name>\n理由: <reason>\n手動確認お願いします"
```

## 4. 完了報告
実行結果をサマリーで表示:
- 分類結果 (category / confidence)
- 実行したルート
- Account ID / Task ID / Notion URL
- Field21__c メモのサマリー (面談の場合)

## 5. requires_review = true の場合の扱い
confidence < 0.8 の場合は、自動実行前にユーザーに確認を求める:
- "分類confidence=X.XX ({reason}) です。{category}として処理してよいですか？"

## 注意事項
- 紹介元 (ReportPerson__c) の自動判定はタイトルから行う（partner022_ガクセイ協賛 / partner040_スマートキャンパス / 【エ】永長敏江 等）
- 既存学生の場合、既存の紹介元は上書きせず追記メモで補足
- 社名表記に「学生協賛」がある場合は「ガクセイ協賛」（カタカナ）に修正する
- Field17__c (学部) が picklist の場合は抽出データから該当値を選択、不明は「その他」

## 失敗時の対処

| エラー | 対処 |
|---|---|
| `meeting_router` 実行失敗 | Python環境確認 (`cd ai-empire && python3 -c "import agents.hr_support.meeting_router"`)。モジュール欠損なら `pip install -r requirements.txt` |
| tldv URL取得失敗 | URL形式確認（`https://tldv.io/app/meetings/<id>` 形式）。APIキー失効なら `.env` の `TLDV_API_KEY` 確認 |
| 重複チェックで複数ヒット（別人か同一人物判定不能） | ユーザーに電話番号・メール提示して手動判定を求める |
| SF Account作成失敗（REQUIRED_FIELD_MISSING） | sf_payload.create_fields の必須項目漏れ確認。`/sf-register` の Step 5 参照 |
| Notion作成失敗（validation_error） | 録画日プロパティ名の確認（「録画日」フィールドを使う） |
| Slack通知失敗（unknown ルート） | チャンネル `#hr-support` 未参加なら Bot招待を案内 |
| confidence < 0.8 でユーザーが "no" 回答 | 自動実行せず手動登録に切り替え、`/sf-register` または `/notion-minutes` を提案 |
