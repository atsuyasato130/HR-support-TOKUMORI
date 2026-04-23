"""
dashboard/db.py — empire.db の初期化・接続ユーティリティ
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "empire.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """全テーブルを作成する（IF NOT EXISTS）"""
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS agents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            canonical_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            layer TEXT,
            status TEXT DEFAULT '設計中',
            level TEXT DEFAULT 'Level 1',
            apis TEXT,
            description TEXT,
            impl_method TEXT,
            launched_at TEXT,
            last_run_at TEXT,
            run_count_total INTEGER DEFAULT 0,
            run_count_month INTEGER DEFAULT 0,
            time_saved_month REAL DEFAULT 0,
            priority TEXT DEFAULT 'Medium'
        );

        CREATE TABLE IF NOT EXISTS intel_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            executed_at TEXT NOT NULL,
            agent_name TEXT NOT NULL,
            canonical_id TEXT,
            bu TEXT,
            operator TEXT,
            time_saved REAL DEFAULT 0,
            result TEXT DEFAULT 'SUCCESS',
            task_summary TEXT,
            input_summary TEXT,
            output_summary TEXT,
            duration_sec REAL DEFAULT 0,
            error_message TEXT
        );

        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            logged_at TEXT NOT NULL,
            icon TEXT,
            summary TEXT NOT NULL,
            targets TEXT,
            details TEXT,
            status TEXT DEFAULT '✅ 完了'
        );

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
            integrations TEXT,
            phase INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS security_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            canonical_id TEXT UNIQUE NOT NULL,
            pii_types TEXT,
            external_writes TEXT,
            human_in_loop TEXT DEFAULT 'なし',
            risk_level TEXT DEFAULT '低',
            current_security_level INTEGER DEFAULT 0
        );

        -- セキュリティレベル定義（0〜4）
        CREATE TABLE IF NOT EXISTS security_level_defs (
            level INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            summary TEXT,
            auth TEXT,
            logging TEXT,
            encryption TEXT,
            pii TEXT,
            audit TEXT,
            badge_color TEXT DEFAULT '#475569'
        );

        -- ユースケース別必要セキュリティレベル
        CREATE TABLE IF NOT EXISTS usecase_requirements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usecase TEXT UNIQUE NOT NULL,
            required_level INTEGER NOT NULL,
            icon TEXT,
            description TEXT,
            sort_order INTEGER DEFAULT 99
        );

        -- エージェント間の呼び出し・データ連携関係
        CREATE TABLE IF NOT EXISTS agent_edges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_id TEXT NOT NULL,   -- 呼び出し元 canonical_id
            to_id TEXT NOT NULL,     -- 呼び出し先 canonical_id
            edge_type TEXT DEFAULT 'triggers',  -- triggers/reads/writes/orchestrates
            label TEXT,              -- 矢印ラベル（例: "議事録取得"）
            is_parallel INTEGER DEFAULT 0,      -- 並列実行フラグ
            parallel_group INTEGER,             -- 同グループは並列
            UNIQUE(from_id, to_id)
        );

        -- ビジネスユニット × ツール接続定義（将来のビジネスマップ用）
        CREATE TABLE IF NOT EXISTS tool_connections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bu TEXT NOT NULL,        -- HRsupport/RPO/経営管理/バックオフィス/Strategy
            tool TEXT NOT NULL,      -- Salesforce/Notion/LINE/Slack/tldv/Gmail/GDrive/GSheets/GitHub
            direction TEXT DEFAULT 'both',  -- read/write/both
            agent_ids TEXT,          -- 使用エージェントのcanonical_id（カンマ区切り）
            note TEXT,
            UNIQUE(bu, tool)
        );
    """)
    conn.commit()
    conn.close()
    print(f"✅ empire.db 初期化完了: {DB_PATH}")


if __name__ == "__main__":
    init_db()
