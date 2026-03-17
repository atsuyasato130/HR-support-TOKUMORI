# Claude Code 全体指示

## Update_Log 自動記録（最重要）

**このプロジェクトでのすべての作業完了後に、必ずUpdate_Logタブを更新すること。**

対象: このChatに限らず、すべてのClaude Codeセッション・依頼すべて。

### 対象となる作業の種類
- スプレッドシートの変更・タブ追加
- コード実装・ファイル変更（エージェント追加、バグ修正、機能拡張）
- Salesforceレコード登録・更新（個別対応を除く、仕組み・フロー変更）
- Notion / Slack / Gmail 連携設定の変更
- メモリファイル（.claude/memory/）の作成・更新
- その他、システム構成に影響する変更全般

### Update_Logへの記録方法

スプレッドシートID: `1g8PzcuPuUTTdO-kcSh4niuwfLw6d8zN8JQMZCrmyuH8`

`update_google_spreadsheet` で Update_Log タブに1行追記する:

| 列 | 内容 |
|---|---|
| A | 連番（前の最終行+1） |
| B | 日時（例: 2026-03-17 14:30） |
| C | 種別アイコン（🆕新規作成 / ➕機能追加 / 🔧修正 / 🎨UI変更 / 🔄更新 / 📋設定変更） |
| D | 依頼内容（ユーザーの依頼を1〜2行で要約） |
| E | 変更タブ/ファイル（例: Main_Map / salesforce_agent.py） |
| F | 主な変更内容（箇条書き3〜5点） |
| G | ステータス（✅完了 / 🔧実装中 / 📋予定） |

記録後に **統計バー（Row 2）の「総更新回数」と「最終更新日時」も更新**すること。

### 対象外（ログ不要）
- 情報検索・質問応答のみ（ファイル・外部サービスへの変更を伴わない）
- Salesforceへの個別学生情報登録・更新（日常業務系）
- 企業紹介文の生成（日常業務系）

---

## 情報の絶対隔離ルール（最重要・例外なし）

### 1. ダッシュボードへの反映禁止
以下の情報は、いかなる場合も統合管理ダッシュボード（Googleスプレッドシート）に反映させてはならない:
- `private/` フォルダ配下での活動・作業内容
- `private/` 配下エージェントの実行ログ
- ライフサポーターとの対話内容

Update_Log・Main_Map・Agent_Registry 等すべてのタブが対象。

### 2. ログの物理的隔離
- `private/` 配下エージェントのログは `private/logs/` 内のローカルファイルにのみ保存
- `business/` 側の Supabase ログテーブルや共通ログファイルへの出力を禁止
- 保存する場合は暗号化または秘匿された状態で行う

### 3. RAG・コンテキストの非干渉
- `business/` 側エージェントは `private/` フォルダの内容をコンテキストとして読み取ってはならない
- 検索・RAG・ファイル読み込み時に `private/` ディレクトリがスコープに入らないよう厳格に制限する

---

## ダッシュボード自動更新ルール

機能追加・エージェント変更・ステータス変化のたびに以下を更新:
- Main_Map → ロジックツリーを更新
- Agent_Registry → エージェント行を更新
- Integration_Matrix → 外部API追加・削除時
- Security_Governance → セキュリティリスク変化時

ダッシュボード: `https://docs.google.com/spreadsheets/d/1g8PzcuPuUTTdO-kcSh4niuwfLw6d8zN8JQMZCrmyuH8/edit`

---

## 作業スタイル
- 作業中の確認は不要。自律的に進めてよい
- **変更を反映する直前**に最終確認を取ること
- 削除操作（rm等）は絶対に自動実行しない
- 各会話・作業セッションの終わりに戦略AIへ報告できる形式でサマリーを出力すること（→ memory/feedback_reporting_style.md 参照）

---

## プロジェクト固有情報

詳細はメモリファイル（`~/.claude/projects/-Users-atsuyasato-AI-agent-HRsupport---/memory/`）を参照:
- `MEMORY.md` — 全体インデックス
- `project_tokumo.md` — TOKUMOアプリ詳細
- `feedback_dashboard_update.md` — ダッシュボード更新ルール
- `feedback_reporting_style.md` — 戦略AI報告スタイル
