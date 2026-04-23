# エージェント操作ルール（agents/ 配下）

## MCP使用優先順位

1. **hr-support MCP**（Salesforce / Notion / Gmail / Calendar / Slack）→ 必ず使う
2. **salesforce-dx MCP** → SOQL / Metadata API 操作時のみ

## Salesforce 操作時の必須確認

- SNS/リファラル経由の学生登録: `SheetNumber__pc` フィールドを必ず使う
- 説明会日程: **「説明会日程」フィールド**を参照（「日程」フィールドは別物）
- 社名表記に「学生協賛」がある場合: **「ガクセイ協賛」（カタカナ）** に修正する

## Notion 操作時の必須確認

- 議事録DB: `database_id = 2bc48452-bd25-8007-838c-c3c707c953c1`
- 日付フィールド: 録画日を必ず入力（空白禁止）

## context7 MCP の活用

Salesforce / Notion / Slack / Gmail の API仕様・フィールド定義・エラーコードを調べるときは **context7 MCP** を使う。

```
例: "Salesforce SOQL WHERE句の書き方を確認して"
例: "Notion database propertiesのAPIリファレンスを見て"
```

トレーニングデータに古い情報が含まれている場合があるため、API仕様は必ずcontext7で最新情報を取得すること。

## 新規エージェント追加時の必須作業

1. `knowledge/hr_support/AGENT_MANIFEST.json` に追加
2. `knowledge/hr_support/architecture_master.md` §1・§8 を更新
3. `knowledge/hr_support/settings.local.json` の allowedMcp に追加（MCP関数使用時）
