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

### Update_Logへの記録方法（必ずこの方法を使うこと）

スプレッドシートID: `1g8PzcuPuUTTdO-kcSh4niuwfLw6d8zN8JQMZCrmyuH8`

**⚠️ `append_row` は禁止。必ず `dashboard_logger.py` を使うこと。**
（append_rowは末尾追加のため順番が崩れる。insert_rowsで Row5 に挿入する設計）

```python
# 正しい記録方法（セッション内のPythonコードから呼ぶ）
import sys
sys.path.insert(0, "utils")
from dashboard_logger import log_update

log_update(
    icon="🔧 修正",           # 🆕新規作成/➕機能追加/🔧修正/🎨UI変更/🔄更新/📋設定変更
    summary="依頼内容の1〜2行要約",
    targets="変更したファイル/タブ名",
    details="①変更点A ②変更点B ③変更点C",
    # status はデフォルト "✅ 完了"
)
```

`dashboard_logger.py` が自動で行う処理:
1. 連番（前の最大値+1）を計算
2. 日時（YYYY/MM/DD HH:MM）を自動付与
3. **Row5 に insert_rows**（最新エントリが常に先頭に来る）
4. **Row2 統計バー**（総更新回数・最終更新日時）を自動更新

### 対象外（ログ不要）
- 情報検索・質問応答のみ（ファイル・外部サービスへの変更を伴わない）
- Salesforceへの個別学生情報登録・更新（日常業務系）
- 企業紹介文の生成（日常業務系）

---

## knowledge/ 動的同期義務（2026-03-17 追加）

`business/career_advisor/knowledge/` はシステムの「生きた設計書」である。
**コード・設定・エージェント・スプレッドシートへの変更のたびに、必ず対応するknowledgeファイルを更新せよ。**

### 更新トリガー早見表

| 変更内容 | 更新対象 |
|----------|---------|
| エージェント追加・変更 | `knowledge/architecture_master.md` §1・§8 + `knowledge/AGENT_MANIFEST.json` |
| SFフィールド追加・変更 | `knowledge/architecture_master.md` §2 |
| MCPツール追加 | `knowledge/architecture_master.md` §6 + `settings.local.json` |
| アーキテクチャ変更 | `knowledge/architecture_master.md` 該当セクション |
| ディレクトリ構造変更 | `CLAUDE.md` + `STATUS_REPORT.md` + `memory/project_directory_structure.md` |

### knowledge/ ファイル一覧

| ファイル | 内容 |
|---------|------|
| `architecture_master.md` | **最上位行動指針**・全秘伝仕様・SF独自フィールド・並列処理設計 |
| `AGENT_MANIFEST.json` | エージェント正規登録台帳（11体） |
| `system_diagram.md` | システムダイアグラム・処理フロー |
| `gems_student_interview.md` | 就活対策AI秘伝システムプロンプト（3モード×3レベル） |
| `slack_post_draft.md` | Slack向けシステム説明ドキュメント |

---

## 情報の絶対隔離ルール（最重要・例外なし）

### ディレクトリ構造と隔離原則（2026-03-17 更新）

```
/Users/atsuyasato/Claude AI/
├── private/                    ← プライベート領域（リポジトリ外・同階層に物理分離）
│   └── life_supporter/         ← 個人用エージェント（business/との接触禁止）
└── AI agent（HRsupport事業）/   ← ビジネス専用リポジトリ（private/は存在しない）
    ├── business/
    │   ├── career_advisor/ ← エージェント本体
    │   └── tokumo/         ← Webアプリ
    ├── STATUS_REPORT.md
    └── CLAUDE.md
```

**`private/` はリポジトリ外（`/Users/atsuyasato/Claude AI/private/`）に物理分離済み。**
このリポジトリ内に `private/` フォルダは存在しない。

### 1. ダッシュボードへの反映禁止
以下の情報は、いかなる場合も統合管理ダッシュボード（Googleスプレッドシート）に反映させてはならない:
- `/Users/atsuyasato/Claude AI/private/` 配下での活動・作業内容
- `life_supporter` エージェントの実行ログ
- ライフサポーターとの対話内容

Update_Log・Main_Map・Agent_Registry 等すべてのタブが対象。

### 2. ログの物理的隔離
- `private/` 配下エージェントのログは `/Users/atsuyasato/Claude AI/private/logs/` 内のローカルファイルにのみ保存
- `business/` 側の Supabase ログテーブルや共通ログファイルへの出力を禁止

### 3. RAG・コンテキストの非干渉
- `business/` 側エージェントは `/Users/atsuyasato/private/` の内容をコンテキストとして読み取ってはならない
- ファイル読み込み時に `private/` ディレクトリがスコープに入らないよう厳格に制限する

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

### ディレクトリ（完全最新版・2026-03-17）
- **エージェント本体**: `business/career_advisor/`（11体稼働）
- **Webアプリ**: `business/tokumo/`（Next.js + Supabase）
- **プライベート**: `/Users/atsuyasato/Claude AI/private/`（リポジトリの外・同階層・非接触）
- **ダッシュボード**: [統合管理スプレッドシート](https://docs.google.com/spreadsheets/d/1g8PzcuPuUTTdO-kcSh4niuwfLw6d8zN8JQMZCrmyuH8/edit)

### 注意事項
- `Claude AI/web/` は `.next/` ビルドキャッシュのみで実体なし → 削除推奨
- エージェント起動: `cd business/career_advisor && python3 main.py`

詳細はメモリファイル（`~/.claude/projects/-Users-atsuyasato-Claude-AI/memory/`）を参照:
- `MEMORY.md` — 全体インデックス
- `project_tokumo.md` — TOKUMOアプリ詳細
- `feedback_dashboard_update.md` — ダッシュボード更新ルール
- `feedback_reporting_style.md` — 戦略AI報告スタイル
