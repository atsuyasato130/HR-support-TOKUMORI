# Tokumori Web Dashboard — 実装指示書

> **目的**: スプレッドシート管理（6タブ）をFastAPI製WebダッシュボードにX移行する  
> **参考設計**: FastAPI + Jinja2 + SQLite のシンプルな単一アプリ構成  
> **URL**: http://localhost:8889

---

## 0. 前提・コンテキスト

### 現在のスプレッドシート構成（移行対象）
スプレッドシートID: `1g8PzcuPuUTTdO-kcSh4niuwfLw6d8zN8JQMZCrmyuH8`

| タブ名 | 移行先タブ | 内容 |
|-------|-----------|------|
| 📊 Dashboard | Overview | KPIスナップ・Agent Status Map・ROI |
| 🗺️ Roadmap | Roadmap | 全25体の開発フェーズ管理 |
| 🤖 Agent Registry | Agents | 25体の仕様・canonical_id・API・ステータス |
| Update_Log | Activity | 変更履歴62件（自動記録連携） |
| 💡 Intel Log | Intel | 実行ログ・成功/失敗・削減時間 |
| Security_Governance | Security | PII・リスクレベル・承認フロー |

### プロジェクト構成（ai-empire）
```
ai-empire/
├── agents/business/hr_support/    ← HRsupportエージェント本体（11体稼働）
├── core/monitoring_os/            ← GAS監視OS（monitoring_os.gs）
├── integrations/                  ← MCP連携
├── utils/dashboard_logger.py      ← Update_Log自動記録ツール
└── dashboard/                     ← ★ ここに新規作成する
    ├── app.py                     ← FastAPIメインアプリ
    ├── db.py                      ← SQLite初期化
    ├── routes/                    ← APIルーター（タブ別）
    │   ├── overview_routes.py
    │   ├── agent_routes.py
    │   ├── roadmap_routes.py
    │   ├── activity_routes.py
    │   ├── intel_routes.py
    │   └── security_routes.py
    └── templates/
        └── index.html             ← SPA（タブ切替）
```

---

## 1. データベース設計（dashboard/db.py）

SQLiteファイル: `ai-empire/dashboard/empire.db`

### テーブル一覧

```sql
-- エージェント基本情報（Agent Registry から移行）
CREATE TABLE IF NOT EXISTS agents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    layer TEXT,                    -- HRsupport/経営戦略/組織管理/品質管理/全体
    status TEXT DEFAULT '設計中',  -- 稼働中/開発中/設計中
    level TEXT DEFAULT 'Level 1',  -- Level 1/Level 2/Level 3
    apis TEXT,                     -- 使用API（カンマ区切り）
    description TEXT,              -- 主な責務
    impl_method TEXT,              -- Python/JSON/GAS
    launched_at TEXT,
    last_run_at TEXT,
    run_count_total INTEGER DEFAULT 0,
    run_count_month INTEGER DEFAULT 0,
    time_saved_month REAL DEFAULT 0,
    priority TEXT DEFAULT 'Medium'  -- High/Medium/Low
);

-- 実行ログ（Intel Log から移行・今後は自動記録）
CREATE TABLE IF NOT EXISTS intel_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    executed_at TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    canonical_id TEXT,
    bu TEXT,                       -- RPO/HRsupport/共通/経営戦略
    operator TEXT,
    time_saved REAL DEFAULT 0,
    result TEXT DEFAULT 'SUCCESS', -- SUCCESS/ERROR/SKIP
    task_summary TEXT,
    input_summary TEXT,
    output_summary TEXT,
    duration_sec REAL DEFAULT 0,
    error_message TEXT
);

-- 変更履歴（Update_Log から移行・dashboard_logger.py と連携）
CREATE TABLE IF NOT EXISTS activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    logged_at TEXT NOT NULL,
    icon TEXT,
    summary TEXT NOT NULL,
    targets TEXT,
    details TEXT,
    status TEXT DEFAULT '✅ 完了'
);

-- KPI手動入力（Dashboard KPI から移行）
CREATE TABLE IF NOT EXISTS kpi_manual (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recorded_at TEXT NOT NULL,
    bu TEXT,
    operator TEXT,
    task_name TEXT,
    time_before REAL,
    time_after REAL,
    time_saved REAL,
    reduction_rate REAL,
    note TEXT
);

-- ロードマップ（Roadmap から移行）
CREATE TABLE IF NOT EXISTS roadmap (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_no INTEGER,
    canonical_id TEXT,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT,
    layer TEXT,
    operator TEXT,
    start_date TEXT,
    launch_date TEXT,
    priority TEXT,
    integrations TEXT,             -- 連携先
    phase INTEGER DEFAULT 1        -- 1/2/3
);
```

---

## 2. データ初期投入（スプレッドシートからの移行）

`dashboard/migrate.py` を作成して以下を実行:

```python
"""
スプレッドシートから empire.db に初期データを移行する
実行: python3 dashboard/migrate.py
"""
import sqlite3
import sys
sys.path.insert(0, '.')

# 以下の25体をagentsテーブルに INSERT
AGENTS_SEED = [
    # canonical_id, name, layer, status, level, apis, description, impl_method, launched_at
    ("hr_orchestrator_post_interview", "面談後フルサポート", "HRsupport", "稼働中", "Level 1",
     "Claude/SF/GSheets", "tldv→SF→LINE→レポート 並列実行", "Python", "2025-12"),
    ("hr_executor_salesforce", "Salesforce", "HRsupport", "稼働中", "Level 1",
     "Claude/SF/GSheets", "tldv議事録→SF PersonAccount登録（最重要）", "Python", "2025-12"),
    ("hr_parser_notion", "Notion", "HRsupport", "稼働中", "Level 1",
     "Claude/Notion", "企業DB取得・企業紹介文生成（複数一括対応）", "Python", "2025-12"),
    ("hr_executor_line", "LINE", "HRsupport", "稼働中", "Level 1",
     "Claude/Notion", "Lステップ文章生成（6シーン・複数パターン）", "Python", "2025-12"),
    ("hr_executor_slack", "Slack", "HRsupport", "稼働中", "Level 1",
     "SF/Slack", "選考進捗Slackスレッドへ自動共有", "Python", "2025-12"),
    ("hr_watcher_tldv", "tldv", "HRsupport", "稼働中", "Level 1",
     "Claude/tldv", "議事録取得・Claude自由質問分析", "Python", "2025-12"),
    ("hr_executor_google", "Google", "HRsupport", "稼働中", "Level 1",
     "Claude/Gmail/GDrive", "Gmail返信/Sheets読書/Docs操作", "Python", "2025-12"),
    ("hr_processor_coaching", "学生コーチング", "HRsupport", "稼働中", "Level 1",
     "Claude", "ES・面接対策/就活軸深掘り（5W1H×MECE）", "Python", "2025-12"),
    ("hr_processor_interview", "面接マスター", "HRsupport", "稼働中", "Level 1",
     "Claude", "5W1H×MECE・新卒/中途自動判別・GDocs出力", "Python", "2025-12"),
    ("hr_processor_report", "レポート", "HRsupport", "稼働中", "Level 1",
     "Claude", "学生所感レポート自動生成・保存（6セクション）", "Python", "2025-12"),
    ("hr_processor_supporter", "サポーター", "HRsupport", "稼働中", "Level 1",
     "Claude", "全エージェント使い方ガイド・機能提案", "Python", "2025-12"),
    ("hr_orchestrator_main", "Orchestrator", "全体", "開発中", "Level 2-3",
     "Claude", "タスク分解→エージェント割振り→実行→検証の自律分業", "Python", "2026-03"),
    ("exec_strategy", "戦略立案", "経営戦略", "稼働中", "Level 1",
     "Claude", "戦略ブリーフ・OKR設計・意思決定支援", "JSON/Template", "2026-03-31"),
    ("exec_ai_trend", "AI動向監視", "経営戦略", "稼働中", "Level 1",
     "Claude", "最新AIモデル・競合インテリジェンス・週次ブリーフ", "JSON/Template", "2026-03-31"),
    ("exec_pl", "P&L管理", "経営戦略", "稼働中", "Level 1",
     "Claude", "売上・工数・利益率の分析・改善提案", "JSON/Template", "2026-03-31"),
    ("exec_team_health", "チーム健全性", "経営戦略", "稼働中", "Level 1",
     "Claude", "Health Score計算・離職リスク検出・週次レポート", "JSON/Template", "2026-03-31"),
    ("exec_approval", "承認", "経営戦略", "設計中", "Level 1",
     "Slack", "稟議・承認ワークフロー自動化", "JSON/Template", None),
    ("org_pulse", "チームパルス", "組織管理", "設計中", "Level 1",
     "Slack", "週次モチベーション・問題検知", "JSON/Template", None),
    ("org_recruiting", "リクルーティング", "組織管理", "設計中", "Level 1",
     "SF/GSheets", "採用KPI・パイプライン管理", "JSON/Template", None),
    ("org_onboarding", "オンボーディング", "組織管理", "設計中", "Level 1",
     "Notion", "新メンバー研修・チェックリスト自動化", "JSON/Template", None),
    ("org_kpi", "KPI管理", "組織管理", "設計中", "Level 1",
     "GSheets", "部署別KPI追跡・ダッシュボード自動更新", "JSON/Template", None),
    ("qa_review", "レビュー", "品質管理", "設計中", "Level 1",
     "GitHub", "コード・ドキュメント品質チェック", "JSON/Template", None),
    ("qa_design", "デザイン", "品質管理", "設計中", "Level 1",
     "—", "UI/UXガイドライン遵守チェック", "JSON/Template", None),
    ("qa_creative", "クリエイティブ", "品質管理", "設計中", "Level 1",
     "—", "コンテンツ品質・ブランド整合性チェック", "JSON/Template", None),
    ("qa_brand_mgr", "ブランドMGR", "品質管理", "設計中", "Level 1",
     "—", "ブランドガイドライン管理・配布", "JSON/Template", None),
]
```

---

## 3. FastAPI アプリ（dashboard/app.py）

以下の構造で作る。

```python
"""
Tokumori Web Dashboard
起動: uvicorn dashboard.app:app --port 8889 --reload
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pathlib import Path
import sqlite3

app = FastAPI(title="Tokumori Dashboard", version="1.0")

# ルーター登録
from dashboard.routes.overview_routes import router as overview_router
from dashboard.routes.agent_routes import router as agent_router
from dashboard.routes.roadmap_routes import router as roadmap_router
from dashboard.routes.activity_routes import router as activity_router
from dashboard.routes.intel_routes import router as intel_router
from dashboard.routes.security_routes import router as security_router

app.include_router(overview_router, prefix="/api")
app.include_router(agent_router,    prefix="/api")
app.include_router(roadmap_router,  prefix="/api")
app.include_router(activity_router, prefix="/api")
app.include_router(intel_router,    prefix="/api")
app.include_router(security_router, prefix="/api")

@app.get("/", response_class=HTMLResponse)
async def index():
    return Path("dashboard/templates/index.html").read_text(encoding="utf-8")
```

---

## 4. APIエンドポイント設計

### Overview（KPIダッシュボード）
```
GET /api/overview/kpi          — 稼働エージェント数/累計削減時間/ROI/ログ数
GET /api/overview/agent_map    — 全25体のステータスマップ
GET /api/overview/kpi_manual   — 部署別手動KPI一覧
POST /api/overview/kpi_manual  — KPI手動入力
```

### Agents（エージェント管理）
```
GET /api/agents                         — 全25体一覧（ステータス/Layer別フィルタ）
GET /api/agents/{canonical_id}          — 個別詳細
PUT /api/agents/{canonical_id}/status   — ステータス更新（稼働中/開発中/設計中）
GET /api/agents/{canonical_id}/logs     — 個別実行ログ
POST /api/agents/{canonical_id}/run_log — 実行ログ手動記録
```

### Roadmap（開発進捗）
```
GET /api/roadmap               — 全フェーズのロードマップ
GET /api/roadmap/progress      — フェーズ別完了率
PUT /api/roadmap/{id}/status   — ステータス更新
```

### Activity（更新ログ）
```
GET /api/activity              — 変更履歴一覧（最新50件）
POST /api/activity             — 新規記録（dashboard_logger.py と同期）
```

### Intel（実行ログ）
```
GET /api/intel                 — 実行ログ一覧（フィルタ: BU/期間/結果）
GET /api/intel/summary         — 成功率・平均削減時間・総削減時間
GET /api/intel/by_agent        — エージェント別実績集計
POST /api/intel                — ログ記録（エージェントから自動記録）
```

### Security（セキュリティ管理）
```
GET /api/security              — 全エージェントのリスク情報
GET /api/security/{canonical_id} — 個別リスク詳細
```

---

## 5. フロントエンド（dashboard/templates/index.html）

タブ切替UIで以下のタブ構成で作る。

### カラーパレット
```css
/* Tokumori テーマ（ダークテック × エンパイア感）*/
--bg-primary:    #0d0d14;   /* 深夜ネイビー */
--bg-card:       #1a1a2e;   /* カード背景 */
--accent:        #7c3aed;   /* パープル（エンパイア色）*/
--accent-light:  #a855f7;
--success:       #10b981;   /* 稼働中 */
--warning:       #f59e0b;   /* 開発中 */
--danger:        #ef4444;   /* エラー/設計中 */
--text-primary:  #e2e8f0;
--text-muted:    #64748b;
```

### タブ構成（6タブ）

```
[🏠 Overview] [🤖 Agents] [🗺️ Roadmap] [📋 Activity] [💡 Intel] [🔒 Security]
```

#### タブ1: Overview（KPIダッシュボード）
- **KPIカード（4枚）**:
  - 🤖 稼働エージェント: N/25体
  - ⏱️ 今月削減時間: X.X h
  - 💰 ROI換算: ¥XXX,XXX
  - 📋 累計ログ: N件
- **Agent Status Map**: 全25体をLayerごとにカード表示（🟢稼働中/🟡開発中/⚪設計中）
- **部署別KPI表**: RPO/HRsupportの削減時間・削減率を入力できるフォーム付き
- **月次グラフ**: 削減時間の累積推移（Chart.js）

#### タブ2: Agents（エージェント管理）
- **フィルターバー**: Layer別（HRsupport/経営戦略/組織管理/品質管理）、Status別
- **エージェントカード一覧**: 各カードに
  - canonical_id（コピーボタン付き）
  - ステータスバッジ（🟢稼働中/🟡開発中/⚪設計中）
  - 今月ログ数・削減時間
  - 使用API・Level
  - 「詳細」ボタン → サイドパネルで実行ログ表示

#### タブ3: Roadmap（開発ロードマップ）
- **フェーズ進捗バー**: Phase1完了✅ / Phase2進行中🚀 / Phase3計画中
- **Layer別展開リスト**:
  - HRsupport（11体稼働）
  - 経営戦略層（5体）
  - 組織管理層（4体）
  - 品質管理層（4体）
- 各行: ステータス/優先度/担当者/開始日/稼働日/連携先
- ステータスを直接変更できるドロップダウン付き

#### タブ4: Activity（更新ログ）
- **サマリー**: 総更新N回 / 今月X回 / 種別内訳
- **更新ログテーブル**:
  - #番号 / 日時 / アイコン / 概要 / 変更ターゲット / 詳細 / ステータス
  - 検索フィルター（キーワード/種別/期間）
- **手動追加フォーム**: icon/summary/targets/details を入力して記録
- dashboard_logger.py と連携: `python3 utils/dashboard_logger.py` 実行でDBに自動記録

#### タブ5: Intel（実行ログ）
- **サマリーカード（3枚）**: 成功率 / 平均削減時間 / 総削減時間
- **エージェント別実績バー**: 横棒グラフで削減時間の多い順
- **実行ログテーブル**:
  - 日時 / エージェント名 / BU / 結果（SUCCESS/ERROR）/ 削減時間 / タスク概要
  - フィルター: BU別/期間別/結果別
- **エラーログハイライト**: result=ERRORは赤色でハイライト

#### タブ6: Security（セキュリティ管理）
- **リスクサマリー**: 🔴高=N体 / 🟡中=N体 / 🟢低=N体
- **エージェント別リスクテーブル**:
  - エージェント名 / PII種別 / 外部書込先 / Human-in-the-loop / リスクレベル
- **PIIポリシーセクション**: システム全体のPII定義・セキュリティポリシー表示

---

## 6. dashboard_logger.py との統合

`utils/dashboard_logger.py` の末尾に以下を追加して、
スプレッドシート書込と同時にDBにも記録するようにする:

```python
# utils/dashboard_logger.py の _write_to_sheet() の後に追加
def _write_to_db(icon, summary, targets, details, status="✅ 完了"):
    """empire.db の activity_log にも同時記録"""
    try:
        import sqlite3
        from pathlib import Path
        db = Path(__file__).parent.parent / "dashboard" / "empire.db"
        if db.exists():
            conn = sqlite3.connect(db)
            conn.execute("""
                INSERT INTO activity_log (logged_at, icon, summary, targets, details, status)
                VALUES (datetime('now', 'localtime'), ?, ?, ?, ?, ?)
            """, (icon, summary, targets, details, status))
            conn.commit()
            conn.close()
    except Exception:
        pass  # DBが未初期化の場合はスキップ
```

---

## 7. 起動スクリプト

`ai-empire/start_dashboard.sh`:
```bash
#!/bin/bash
cd "/Users/atsuyasato/Claude AI/ai-empire"
echo "Tokumori Dashboard 起動中..."
python3 -m uvicorn dashboard.app:app --port 8889 --reload --host 0.0.0.0
```

`ai-empire/dashboard/setup.py`（初回セットアップ）:
```bash
# 実行手順:
# 1. python3 dashboard/setup.py     ← DB初期化 + シードデータ投入
# 2. bash start_dashboard.sh        ← ダッシュボード起動
# 3. open http://localhost:8889     ← ブラウザで確認
```

---

## 8. 実装優先順位

1. **まず動かす（コア）**: DB初期化 + migrate.py + app.py + Overview タブ
2. **最重要タブ**: Agents（25体一覧）+ Activity（更新ログ）
3. **実務で使う**: Intel（実行ログ）+ Roadmap
4. **仕上げ**: Security + dashboard_logger.py 統合 + Chart.js グラフ

---

## 9. 参考スタック構成

| コンポーネント | ai-empire での用途 |
|-----------------|------------------|
| `dashboard/app.py` | FastAPI構造のベース |
| `dashboard/templates/index.html` | タブUI・CSSデザイン |
| `data/information_hub.py` の DB初期化パターン | `dashboard/db.py` |
| `dashboard/ir_routes.py` の APIRouter構造 | 各 routes/*.py |

---

## 10. 追加依存パッケージ

```bash
pip install fastapi uvicorn jinja2 aiofiles
```

（FastAPI標準スタック）
