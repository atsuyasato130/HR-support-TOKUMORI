# Claude Code 全体指示 — Tokumori（2026-03-30 更新）

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

### Update_Logへの記録方法（必ずこの方法を使うこと）

**⚠️ `append_row` は禁止。必ず `dashboard_logger.py` を使うこと。**

```bash
# ai-empire/ ルートから実行（アイコン・summary・targets・details の順）
python3 utils/dashboard_logger.py "🔧 修正" "依頼内容の1〜2行要約" "変更ファイル/タブ名" "①変更点A ②変更点B"

# アイコン: 🆕新規作成 ➕機能追加 🔧修正 🎨UI変更 🔄更新 📋設定変更
# status を変えたい場合: --status "⚠️ 確認中"
```

### 対象外（ログ不要）
- 情報検索・質問応答のみ（ファイル・外部サービスへの変更を伴わない）
- Salesforceへの個別学生情報登録・更新（日常業務系）
- 企業紹介文の生成（日常業務系）

---

## knowledge/ 動的同期義務

`knowledge/` はシステムの「生きた設計書」。コード・設定・エージェント変更時に更新する。
詳細ルール → `agents/CLAUDE.md` を参照。

---

## 情報の絶対隔離ルール（最重要・例外なし）

### ディレクトリ構造と隔離原則（2026-03-30 更新）

詳細構造は `~/.claude/projects/-Users-atsuyasato-Claude-AI/memory/project_directory_structure.md` を参照。

**絶対原則:**
- `private/`（`/Users/atsuyasato/Claude AI/private/`）は **ai-empire/ と完全分離**（リポジトリ外）
- `life_supporter` エージェントと ai-empire/ の接触禁止

**`private/` はリポジトリ外（`/Users/atsuyasato/Claude AI/private/`）に物理分離済み。**

### ダッシュボードへの反映禁止
以下の情報は、いかなる場合もダッシュボードに反映させてはならない:
- `/Users/atsuyasato/Claude AI/private/` 配下での活動・作業内容
- `life_supporter` エージェントの実行ログ・対話内容

### ログの物理的隔離
- `private/` 配下エージェントのログは `/Users/atsuyasato/Claude AI/private/logs/` にのみ保存
- `ai-empire/` 側の共通ログファイルへの出力を禁止

---

## Tokumori アーキテクチャ（2026-03-30）

### 3層レベル
| Level | 状態 | 特徴 |
|-------|------|------|
| Level 1（対話型） | 運用中 | 会話中のみ動作・毎回指示が必要 |
| Level 2（自律型） | 運用中 | 定期実行・24時間稼働（PC常時ON） |
| Level 3（常駐型） | 開発中 | VPS常駐・Webhook即時反応・PC電源不要 |

### 開発ドメイン
現在開発中の機能はデフォルトで **HRsupport** 向け。RPO側は明示指定時のみ。

---

## ダッシュボード自動更新ルール

機能追加・エージェント変更・ステータス変化のたびに以下を更新:
- Roadmap → フェーズ進捗を更新
- Agent Registry → エージェント行を更新
- Project Board → タスクステータスを更新

ダッシュボード: `https://docs.google.com/spreadsheets/d/1g8PzcuPuUTTdO-kcSh4niuwfLw6d8zN8JQMZCrmyuH8/edit`

---

## 作業スタイル
- 作業中の確認は不要。自律的に進めてよい
- **変更を反映する直前**に最終確認を取ること
- 削除操作（rm等）は絶対に自動実行しない
- 各会話・作業セッションの終わりに戦略AIへ報告できる形式でサマリーを出力すること（→ memory/feedback_reporting_style.md 参照）

---

## 主要コマンド

```bash
# HRsupportエージェント起動
cd agents/hr_support && python3 main.py

# Update_Log記録（ai-empire/ ルートで実行）
python3 utils/dashboard_logger.py "ICON" "SUMMARY" "TARGETS" "DETAILS"
```

詳細はメモリファイル（`~/.claude/projects/-Users-atsuyasato-Claude-AI/memory/`）を参照:
- `MEMORY.md` — 全体インデックス
- `project_directory_structure.md` — ディレクトリ構造
- `feedback_reporting_style.md` — 戦略AI報告スタイル
