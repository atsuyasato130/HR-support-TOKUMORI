"""
dashboard/migrate.py — empire.db にシードデータを投入する
実行: python3 dashboard/migrate.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dashboard.db import init_db, get_conn

# 25体エージェントシードデータ
# (canonical_id, name, layer, status, level, apis, description, impl_method, launched_at)
AGENTS_SEED = [
    # ── HRsupport事業 ──
    ("hr_orchestrator_post_interview", "HRsupportオーケストレーター", "HRsupport", "稼働中", "Level 1",
     "Claude/SF/GSheets/Notion/LINE/Slack/tldv",
     "【Orchestrator】面談後フルサポート。tldv→SF登録→LINE送信→レポート生成を並列オーケストレーション", "Python", "2025-12"),
    ("hr_executor_salesforce", "Salesforce", "HRsupport", "稼働中", "Level 1",
     "Claude/SF/GSheets", "tldv議事録→SF PersonAccount登録（最重要）", "Python", "2025-12"),
    ("hr_parser_notion", "Notion", "HRsupport", "稼働中", "Level 1",
     "Claude/Notion", "企業DB取得・企業紹介文生成（複数一括対応）", "Python", "2025-12"),
    # hr_executor_line は Messaging グループに統合（削除対象）
    ("hr_executor_slack", "Messaging", "HRsupport", "稼働中", "Level 1",
     "LINE/Slack", "【Group】LINE（学生向け配信）・Slack（社内共有）をまとめるグループノード", "Python", "2025-12"),
    ("hr_watcher_tldv", "tldv", "HRsupport", "稼働中", "Level 1",
     "Claude/tldv", "議事録取得・Claude自由質問分析", "Python", "2025-12"),
    ("hr_executor_google", "Google Suite", "HRsupport", "稼働中", "Level 1",
     "Gmail/GDrive/GSheets/GDocs", "【Group】Google系ツール（Gmail/GDrive/GDocs/GSheets）をまとめるグループノード", "Python", "2025-12"),
    ("hr_google_gmail", "Gmail", "HRsupport", "稼働中", "Level 1",
     "Gmail", "学生・企業へのメール返信・受信・テンプレート送信", "Python", "2025-12"),
    ("hr_google_gdrive", "GDrive / GDocs", "HRsupport", "稼働中", "Level 1",
     "GDrive/GDocs", "レポート・面接Q&A・議事録をGDocs/GDriveへ保存・管理", "Python", "2025-12"),
    ("hr_google_gsheets", "GSheets", "HRsupport", "稼働中", "Level 1",
     "GSheets", "スプレッドシート読書き・KPI集計・データ更新", "Python", "2025-12"),
    ("hr_messaging_line", "LINE", "HRsupport", "稼働中", "Level 1",
     "LINE/Lステップ", "学生向けLステップ文章生成・配信（6シーン・複数パターン）", "Python", "2025-12"),
    ("hr_messaging_slack", "Slack", "HRsupport", "稼働中", "Level 1",
     "Slack/SF", "社内選考進捗のSlackスレッドへ自動共有", "Python", "2025-12"),
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

    # ── RPO事業 ──
    ("rpo_orchestrator", "RPOオーケストレーター", "RPO", "設計中", "Level 1",
     "Claude/SF/GSheets",
     "【Orchestrator】RPO事業全体の指揮。採用KPI管理・候補者パイプライン・クライアント報告を統括", "Python", None),

    # ── Sales事業（事業部なし・フラット）──
    ("sales_orchestrator", "Salesオーケストレーター", "Sales", "設計中", "Level 1",
     "Claude/SF/Slack",
     "【Orchestrator】Sales事業を統括。リード管理・商談進捗・クロージング支援を一元制御", "Python", None),

    # ── 人事部門 ──
    ("hr_dept_orchestrator", "人事オーケストレーター", "人事", "設計中", "Level 1",
     "Claude/Notion/Slack",
     "【Orchestrator】人事部門全体を統括。社員採用・業務委託採用・インターン採用の3系統を指揮", "Python", None),
    ("hr_dept_employee_hiring", "社員採用", "人事", "設計中", "Level 1",
     "Claude/SF/Notion",
     "正社員採用プロセス全体（JD作成→スクリーニング→面接→オファー）を管理", "Python", None),
    ("hr_dept_contractor_hiring", "業務委託採用", "人事", "設計中", "Level 1",
     "Claude/Notion",
     "業務委託・フリーランス採用プロセスと契約管理を担当", "Python", None),
    ("hr_dept_intern_hiring", "インターン生採用", "人事", "設計中", "Level 1",
     "Claude/Notion/Slack",
     "インターン採用・研修プログラム・日次フォローを管理", "Python", None),

    # ── 経営管理 ──
    ("mgmt_orchestrator", "経営管理オーケストレーター", "経営管理", "設計中", "Level 1",
     "Claude/GSheets/Slack",
     "【Orchestrator】経営管理部門全体を統括。戦略・経理・法務の3機能を調整・指揮", "Python", None),
    ("mgmt_accounting", "経理", "経営管理", "設計中", "Level 1",
     "Claude/GSheets",
     "月次P&L集計・経費申請処理・請求書管理・税務対応を自動化", "Python", None),
    ("mgmt_legal", "法務", "経営管理", "設計中", "Level 1",
     "Claude/Notion",
     "契約書レビュー・法令遵守チェック・規約管理・リスク評価を担当", "Python", None),

    # ── HRsupport — 中途/新卒 サブオーケストレーター ──
    ("hrsup_chuto", "中途支援", "HRsupport", "設計中", "Level 1",
     "Claude/SF/Notion",
     "【Sub-Orch】中途採用支援。CA/RA担当へタスク委譲し選考プロセスを管理", "Python", None),
    ("hrsup_shinsotsu", "新卒支援", "HRsupport", "設計中", "Level 1",
     "Claude/SF/Notion",
     "【Sub-Orch】新卒採用支援。CA/LG担当へタスク委譲し内定〜入社フォローを管理", "Python", None),
    # ── HRsupport — 職種エージェント（社員/業委/インターン生は権限グループで分離） ──
    ("hrsup_ca", "CA", "HRsupport", "設計中", "Level 1",
     "Claude/SF/GSheets",
     "キャリアアドバイザー業務全般（面談・選考管理・コーチング）。社員/業務委託でセキュリティレベル・アクセス権を分離", "Python", None),
    ("hrsup_ra", "RA", "HRsupport", "設計中", "Level 1",
     "Claude/SF/GSheets/Slack",
     "リクルーティングアドバイザー業務（企業折衝・求人票作成・クライアント報告・Slack共有）", "Python", None),
    ("hrsup_lg", "LG", "HRsupport", "設計中", "Level 1",
     "Claude/Notion/Slack",
     "リードジェネレーション補助。インターン生が担当する業務をNotion/Slackで自動補助", "Python", None),

    # ── RPO — CS職種エージェント（社員/業委は権限グループで分離） ──
    ("rpo_cs", "CS", "RPO", "設計中", "Level 1",
     "Claude/SF/GSheets",
     "RPOカスタマーサクセス（クライアント報告・採用KPI管理・定例対応）。社員/業務委託でセキュリティレベルを分離", "Python", None),

    # ── Sales — FS/IS職種エージェント（社員/業委は権限グループで分離） ──
    ("sales_fs", "FS", "Sales", "設計中", "Level 1",
     "Claude/SF/Slack",
     "フィールドセールス（商談管理・提案書生成・契約フォロー）。社員/業務委託でセキュリティレベルを分離", "Python", None),
    ("sales_is", "IS", "Sales", "設計中", "Level 1",
     "Claude/SF/Slack",
     "インサイドセールス（リード育成・アポイント管理・商談ログ記録）。社員/業務委託でセキュリティレベルを分離", "Python", None),
]

# ロードマップシードデータ (agent_no, canonical_id, name, description, status, layer, operator,
#                             start_date, launch_date, priority, integrations, phase)
ROADMAP_SEED = [
    (1, "hr_orchestrator_post_interview", "面談後フルサポート", "tldv→SF→LINE→レポート 並列実行",
     "稼働中", "HRsupport", "佐藤", "2025-11", "2025-12", "High", "Claude/SF/GSheets/LINE", 1),
    (2, "hr_executor_salesforce", "Salesforce", "tldv議事録→SF PersonAccount登録",
     "稼働中", "HRsupport", "佐藤", "2025-11", "2025-12", "High", "Claude/SF/GSheets", 1),
    (3, "hr_parser_notion", "Notion", "企業DB取得・企業紹介文生成",
     "稼働中", "HRsupport", "佐藤", "2025-11", "2025-12", "High", "Claude/Notion", 1),
    (4, "hr_executor_line", "LINE", "Lステップ文章生成",
     "稼働中", "HRsupport", "佐藤", "2025-11", "2025-12", "High", "Claude/Notion", 1),
    (5, "hr_executor_slack", "Slack", "選考進捗Slackスレッドへ自動共有",
     "稼働中", "HRsupport", "佐藤", "2025-11", "2025-12", "Medium", "SF/Slack", 1),
    (6, "hr_watcher_tldv", "tldv", "議事録取得・Claude自由質問分析",
     "稼働中", "HRsupport", "佐藤", "2025-11", "2025-12", "High", "Claude/tldv", 1),
    (7, "hr_executor_google", "Google", "Gmail返信/Sheets読書/Docs操作",
     "稼働中", "HRsupport", "佐藤", "2025-11", "2025-12", "Medium", "Claude/Gmail/GDrive", 1),
    (8, "hr_processor_coaching", "学生コーチング", "ES・面接対策/就活軸深掘り",
     "稼働中", "HRsupport", "佐藤", "2025-11", "2025-12", "High", "Claude", 1),
    (9, "hr_processor_interview", "面接マスター", "5W1H×MECE・新卒/中途自動判別",
     "稼働中", "HRsupport", "佐藤", "2025-11", "2025-12", "High", "Claude", 1),
    (10, "hr_processor_report", "レポート", "学生所感レポート自動生成・保存",
     "稼働中", "HRsupport", "佐藤", "2025-11", "2025-12", "Medium", "Claude", 1),
    (11, "hr_processor_supporter", "サポーター", "全エージェント使い方ガイド・機能提案",
     "稼働中", "HRsupport", "佐藤", "2025-11", "2025-12", "Low", "Claude", 1),
    (12, "exec_strategy", "戦略立案", "戦略ブリーフ・OKR設計・意思決定支援",
     "稼働中", "経営戦略", "佐藤", "2026-03", "2026-03-31", "High", "Claude", 2),
    (13, "exec_ai_trend", "AI動向監視", "最新AIモデル・競合インテリジェンス・週次ブリーフ",
     "稼働中", "経営戦略", "佐藤", "2026-03", "2026-03-31", "High", "Claude", 2),
    (14, "exec_pl", "P&L管理", "売上・工数・利益率の分析・改善提案",
     "稼働中", "経営戦略", "佐藤", "2026-03", "2026-03-31", "High", "Claude", 2),
    (15, "exec_team_health", "チーム健全性", "Health Score計算・離職リスク検出・週次レポート",
     "稼働中", "経営戦略", "佐藤", "2026-03", "2026-03-31", "Medium", "Claude", 2),
    (16, "exec_approval", "承認", "稟議・承認ワークフロー自動化",
     "設計中", "経営戦略", "—", "2026-04", "2026-06", "Medium", "Slack", 2),
    (17, "hr_orchestrator_main", "Orchestrator", "タスク分解→エージェント割振り→実行→検証の自律分業",
     "開発中", "全体", "佐藤", "2026-03", "2026-06", "High", "Claude", 2),
    (18, "org_pulse", "チームパルス", "週次モチベーション・問題検知",
     "設計中", "組織管理", "—", "2026-05", "2026-07", "Medium", "Slack", 3),
    (19, "org_recruiting", "リクルーティング", "採用KPI・パイプライン管理",
     "設計中", "組織管理", "—", "2026-05", "2026-07", "Medium", "SF/GSheets", 3),
    (20, "org_onboarding", "オンボーディング", "新メンバー研修・チェックリスト自動化",
     "設計中", "組織管理", "—", "2026-06", "2026-08", "Low", "Notion", 3),
    (21, "org_kpi", "KPI管理", "部署別KPI追跡・ダッシュボード自動更新",
     "設計中", "組織管理", "—", "2026-06", "2026-08", "Medium", "GSheets", 3),
    (22, "qa_review", "レビュー", "コード・ドキュメント品質チェック",
     "設計中", "品質管理", "—", "2026-07", "2026-09", "Low", "GitHub", 3),
    (23, "qa_design", "デザイン", "UI/UXガイドライン遵守チェック",
     "設計中", "品質管理", "—", "2026-07", "2026-09", "Low", "—", 3),
    (24, "qa_creative", "クリエイティブ", "コンテンツ品質・ブランド整合性チェック",
     "設計中", "品質管理", "—", "2026-07", "2026-09", "Low", "—", 3),
    (25, "qa_brand_mgr", "ブランドMGR", "ブランドガイドライン管理・配布",
     "設計中", "品質管理", "—", "2026-08", "2026-10", "Low", "—", 3),
    # RPO
    (26, "rpo_orchestrator", "RPOオーケストレーター", "RPO事業全体統括",
     "設計中", "RPO", "佐藤", "2026-05", "2026-07", "High", "Claude/SF/GSheets", 2),
    # Sales
    (27, "sales_orchestrator", "Salesオーケストレーター", "Sales事業統括",
     "設計中", "Sales", "佐藤", "2026-05", "2026-07", "High", "Claude/SF/Slack", 2),
    # 人事
    (28, "hr_dept_orchestrator",    "人事オーケストレーター", "人事部門全体統括",
     "設計中", "人事", "—", "2026-06", "2026-08", "High", "Claude/Notion/Slack", 3),
    (29, "hr_dept_employee_hiring",  "社員採用",         "正社員採用プロセス管理",
     "設計中", "人事", "—", "2026-06", "2026-09", "Medium", "Claude/SF/Notion", 3),
    (30, "hr_dept_contractor_hiring","業務委託採用",      "業務委託・契約管理",
     "設計中", "人事", "—", "2026-07", "2026-09", "Medium", "Claude/Notion", 3),
    (31, "hr_dept_intern_hiring",    "インターン生採用",  "インターン採用・研修",
     "設計中", "人事", "—", "2026-07", "2026-10", "Low", "Claude/Notion/Slack", 3),
    # 経営管理追加
    (32, "mgmt_orchestrator", "経営管理オーケストレーター", "経営管理部門全体統括",
     "設計中", "経営管理", "—", "2026-05", "2026-07", "High", "Claude/GSheets/Slack", 2),
    (33, "mgmt_accounting",   "経理", "月次P&L・経費・請求書管理",
     "設計中", "経営管理", "—", "2026-06", "2026-08", "Medium", "Claude/GSheets", 3),
    (34, "mgmt_legal",        "法務", "契約書レビュー・法令遵守・リスク評価",
     "設計中", "経営管理", "—", "2026-07", "2026-09", "Medium", "Claude/Notion", 3),
    # HRsupport 中途/新卒 + 職種
    (35, "hrsup_chuto",    "中途支援", "中途採用CA/RA担当へのタスク委譲・進捗管理",
     "設計中", "HRsupport", "佐藤", "2026-05", "2026-07", "High", "Claude/SF/Notion", 2),
    (36, "hrsup_shinsotsu","新卒支援", "新卒採用CA/LG担当へのタスク委譲・内定フォロー",
     "設計中", "HRsupport", "佐藤", "2026-05", "2026-07", "High", "Claude/SF/Notion", 2),
    (37, "hrsup_ca",       "CA", "面談・選考管理・コーチング自動化（社員/業委は権限グループで分離）",
     "設計中", "HRsupport", "佐藤", "2026-06", "2026-08", "High", "Claude/SF/GSheets", 2),
    (38, "hrsup_ra",       "RA", "企業折衝・求人票作成・クライアント報告",
     "設計中", "HRsupport", "佐藤", "2026-06", "2026-08", "High", "Claude/SF/GSheets/Slack", 2),
    (39, "hrsup_lg",       "LG", "リードジェネレーション補助・Notion/Slack連動（インターン生は権限グループで分離）",
     "設計中", "HRsupport", "—", "2026-07", "2026-09", "Low", "Claude/Notion/Slack", 2),
    # RPO CS
    (40, "rpo_cs",         "CS", "クライアント報告・KPI管理（社員/業委は権限グループで分離）",
     "設計中", "RPO", "佐藤", "2026-06", "2026-08", "High", "Claude/SF/GSheets", 2),
    # Sales FS/IS
    (41, "sales_fs",       "FS", "商談管理・提案書生成・契約フォロー（社員/業委は権限グループで分離）",
     "設計中", "Sales", "佐藤", "2026-06", "2026-08", "High", "Claude/SF/Slack", 2),
    (42, "sales_is",       "IS", "リード育成・アポイント管理・商談ログ（社員/業委は権限グループで分離）",
     "設計中", "Sales", "佐藤", "2026-06", "2026-08", "High", "Claude/SF/Slack", 2),

    # ── Phase 4: 全社AIエージェント化 展開ロードマップ（〜2026-04-30） ────────────────
    # 【Week 1: 4/7-4/10】AI推進室 基盤整備
    (43, "w1_ai_dept_setup",
     "【W1】AI推進室 環境構築",
     "AI推進室全員のClaude Code（Team Premium）セットアップ完了。"
     "ai-empire/ リポジトリ共有・MCPサーバー設定・CLAUDE.md統一。"
     "完了基準: 推進室全員がClaude Codeでai-empireを操作・エージェント追加できる状態",
     "未着手", "AI推進室", "佐藤", "2026-04-07", "2026-04-10", "High",
     "Claude Code / Team Premium / GitHub", 4),

    (44, "w1_team_plan_contract",
     "【W1】全社 Claude Team プラン契約",
     "Anthropic Team プランを全社契約。"
     "AI推進室: Team Premium（Claude Code付き）/ 社員: Team Standard（Cowork・Projects利用）。"
     "業務委託・インターン: 本週中に方針決定（案: 担当BU成果物の閲覧のみ）。"
     "完了基準: 全メンバーのアカウントにシートが割り当てられた状態",
     "未着手", "AI推進室", "佐藤", "2026-04-07", "2026-04-10", "High",
     "Claude Team Premium / Team Standard", 4),

    (45, "w1_workflow_audit",
     "【W1】全BU 業務フロー棚卸し",
     "各BU担当者と30分ミーティングを実施し、AI化対象業務を洗い出す。"
     "アウトプット: BUごとの『現状フロー → AI化後フロー』マッピング表。"
     "優先基準: ①繰り返し頻度が高い ②Claude/既存エージェントで対応可能 ③効果が数値化できる",
     "未着手", "AI推進室", "佐藤", "2026-04-07", "2026-04-10", "High",
     "—", 4),

    # 【Week 2: 4/11-4/17】社員へのClaude配布・基礎研修
    (46, "w2_claude_onboarding_all",
     "【W2】全社員 Claude 基礎研修（1時間×BU別）",
     "AI推進室が各BU向けに1時間の研修を実施。"
     "内容: ①Claudeとは / ②Projects・Coworkの使い方 / ③自部署での活用シーン体験。"
     "研修後ゴール: 社員全員がClaudeに自分の業務を相談できる状態になる",
     "未着手", "全社", "佐藤", "2026-04-11", "2026-04-17", "High",
     "Claude.ai / Claude Cowork", 4),

    (47, "w2_projects_bu_setup",
     "【W2】BU別 Claude Projects 構築",
     "Claude.ai のProjects機能でBU別共有プロジェクトを5つ作成。"
     "各プロジェクトに: ①業務ナレッジ（会社概要・用語集・SF設計書等）②プロンプトテンプレート ③過去成果物サンプルを格納。"
     "社員が『このプロジェクトを開けばすぐ仕事できる』状態に。",
     "未着手", "AI推進室", "佐藤", "2026-04-11", "2026-04-17", "High",
     "Claude.ai Projects", 4),

    (48, "w2_prompt_library",
     "【W2】業務シーン別 Promptテンプレート整備",
     "BU × 業務シーン別のプロンプトテンプレートを作成しProjectsに格納。"
     "HRsupport: 面談メモ整理・企業紹介文・LINEメッセージ・SF登録指示文"
     "RPO: クライアント週次報告・KPI集計依頼・課題提案"
     "Sales: 提案書ドラフト・商談後フォローメール・失注分析"
     "社員がゼロからプロンプトを書かず業務を回せる状態を目指す",
     "未着手", "AI推進室", "佐藤", "2026-04-11", "2026-04-17", "High",
     "Claude.ai Projects / Notion", 4),

    # 【Week 3: 4/18-4/24】BU別 業務フロー移行
    (49, "w3_hrsupport_ai_workflow",
     "【W3】HRsupport 業務フロー完全AI化",
     "HRsupportの主要業務フローをClaude主体で完結させる。"
     "① 面談後フロー: tldv → SF登録 → LINE下書き → Slack共有 → レポート（既存エージェント活用）"
     "② 企業紹介文: Notion検索 → Claude生成 → LINE配信（CA/LGが手を動かさない状態）"
     "③ 面接対策: 学生情報入力 → Claude提案（RAがRA業務に集中できる状態）"
     "完了基準: CA・RA・LGが1日の業務の50%以上をClaudeで処理できる",
     "未着手", "HRsupport", "佐藤", "2026-04-18", "2026-04-24", "High",
     "既存エージェント全体 / Claude Cowork", 4),

    (50, "w3_rpo_ai_workflow",
     "【W3】RPO 業務フロー AI化",
     "RPO（CS）の定型業務をClaude主体で自動化する。"
     "① クライアント週次報告書: SF KPIデータ → Claude → 報告書ドラフト（30分→5分）"
     "② 採用パイプライン更新連絡: 変化点 → Claudeで要約 → クライアントSlack/メール"
     "③ 課題抽出・改善提案: KPIデータ → Claude分析 → 提案スライド"
     "完了基準: CS1名が担当クライアント数を1.5倍こなせる状態",
     "未着手", "RPO", "佐藤", "2026-04-18", "2026-04-24", "High",
     "Claude.ai / GSheets / Slack", 4),

    (51, "w3_sales_ai_workflow",
     "【W3】Sales 業務フロー AI化",
     "Sales（FS・IS）の商談周辺業務をClaude主体で自動化する。"
     "① 提案書ドラフト: クライアント情報入力 → Claude → 提案書（2時間→20分）"
     "② 商談後フォローメール: 面談メモ → Claude → カスタマイズメール即時送信"
     "③ 失注分析・次手提案: 商談ログ → Claude分析 → 再アプローチ戦略"
     "完了基準: FS・ISが提案準備・フォロー工数を50%削減",
     "未着手", "Sales", "佐藤", "2026-04-18", "2026-04-24", "High",
     "Claude.ai / SF / Slack", 4),

    (52, "w3_mgmt_ai_workflow",
     "【W3】経営管理・人事 業務フロー AI化",
     "経営管理・人事の定型業務をClaude主体で処理する。"
     "経営管理: 月次P&L集計→Claude分析コメント / 契約書レビュー依頼→Claude要点抽出"
     "人事: 採用要件整理→JDドラフト / オンボーディングチェックリスト自動生成"
     "完了基準: 月次定型作業の事務工数30%削減",
     "未着手", "経営管理/人事", "佐藤", "2026-04-18", "2026-04-24", "Medium",
     "Claude.ai / GSheets / Notion", 4),

    # 【Week 4: 4/25-4/30】全社稼働確認・権限設計確定
    (53, "w4_security_permission",
     "【W4】権限グループ設計確定・実装",
     "雇用形態別のClaudeアクセス権限を確定し実装する。"
     "社員（正社員）: Team Standard全機能 + 自BUのProjectsアクセス"
     "業務委託: Claude.ai Proアカウント（個人払い）+ 担当BUのProjectsを閲覧のみ共有"
     "インターン生（LG）: Claude.ai Free or Pro（個別判断）+ LG業務テンプレートのみ提供"
     "完了基準: 全メンバーのアクセス権限が役割に沿って設定完了",
     "未着手", "AI推進室", "佐藤", "2026-04-25", "2026-04-30", "High",
     "Cloudflare Access / Claude Team Admin", 4),

    (54, "w4_kpi_measurement",
     "【W4】AI活用KPI計測・ダッシュボード反映",
     "全BUのAI活用状況をダッシュボードのKPIタブに記録開始。"
     "計測指標: ①業務別削減時間（分/件）②Claudeへの依頼回数 ③エージェント実行回数"
     "週次でKPIを記録し改善PDCAを回す体制を確立する。"
     "完了基準: ダッシュボードKPIタブに各BUの週次実績が入力されている状態",
     "未着手", "AI推進室", "佐藤", "2026-04-25", "2026-04-30", "High",
     "ダッシュボード KPIタブ / GSheets", 4),

    (55, "w4_full_launch_review",
     "【W4】全社AIエージェント化 完成確認・改善",
     "4月末時点での全社AI化状況をレビューし未達項目を洗い出す。"
     "確認項目: ①全社員がClaudeを業務で使えているか ②各BUのAI化フローが機能しているか"
     "③エラー・使いにくい点のフィードバック収集 ④5月以降の改善タスク整理"
     "完了基準: 全BUから『Claudeなしでは戻れない業務』が最低1つ以上挙がっている",
     "未着手", "AI推進室", "佐藤", "2026-04-28", "2026-04-30", "High",
     "—", 4),

    # ── Phase 5: 外販・SaaS化（〜2026-06-30） ──────────────────────────────────
    (53, "saas_package_design",
     "AIエージェントSaaSパッケージ設計",
     "ai-empireのエージェント群を外部企業向けにパッケージ化する設計。"
     "対象: HR事業社（採用支援・CA/RA業務）をファーストターゲットに。"
     "提供形態: ①SaaS（月額）/ ②導入支援コンサル / ③ホワイトラベル",
     "未着手", "外販", "佐藤", "2026-05", "2026-05-15", "High",
     "—", 5),

    (54, "saas_dashboard_whitlabel",
     "外部向けダッシュボード（ホワイトラベル）",
     "ai-empireダッシュボードをクライアント企業向けにカスタマイズ可能な構成に改修。"
     "・ロゴ・カラー・BU名を差替え可能に"
     "・クライアント専用サブドメイン（例: client.empire.ai）"
     "・閲覧専用ビュー（編集権限なし）",
     "未着手", "外販", "佐藤", "2026-05", "2026-05-31", "High",
     "Cloudflare / FastAPI", 5),

    (55, "saas_pricing_contract",
     "料金体系・契約モデル設計",
     "外販向け料金体系を設計。"
     "案: ①スターター（月3万〜: 基本エージェント5体+ダッシュボード）"
     "   ②スタンダード（月10万〜: 全BUエージェント+カスタマイズ）"
     "   ③エンタープライズ（月30万〜: 専任AI推進室サポート付き）",
     "未着手", "外販", "佐藤", "2026-05", "2026-05-20", "High",
     "—", 5),

    (56, "saas_lp_sales_material",
     "外販LP・営業資料作成",
     "外部顧客向けLPと営業資料（提案書・事例集）を作成。"
     "・LP: AI帝国の実績・ROI・デモ動画を掲載"
     "・提案書テンプレート: HRsupport特化版をファーストバージョン"
     "・事例: 自社導入実績をケーススタディ化",
     "未着手", "外販", "佐藤", "2026-05", "2026-05-31", "High",
     "Claude / Notion / Webサイト", 5),

    (57, "saas_pilot_client",
     "初期顧客獲得・パイロット導入",
     "外販ファースト顧客を1〜3社獲得しパイロット導入を実施。"
     "・ターゲット: 中規模HR事業社（10〜50名）"
     "・提供: 3ヶ月無償トライアル → 有償移行"
     "・目標: 6月末までに有償1社契約",
     "未着手", "外販", "佐藤", "2026-06", "2026-06-30", "High",
     "—", 5),

    (58, "saas_support_system",
     "外販サポート体制構築",
     "外部顧客向けサポートフロー整備。"
     "・オンボーディング手順書（Claude使い方・エージェント操作）"
     "・Slackサポートチャンネル設置"
     "・月次レビュー・KPI報告テンプレート",
     "未着手", "外販", "佐藤", "2026-06", "2026-06-30", "Medium",
     "Slack / Notion / Claude", 5),
]

# セキュリティ情報シードデータ (canonical_id, pii_types, external_writes, human_in_loop, risk_level)
SECURITY_SEED = [
    ("hr_orchestrator_post_interview", "氏名・面談内容・評価", "SF/GSheets/LINE/GDrive", "要確認ステップあり", "高"),
    ("hr_executor_salesforce", "氏名・連絡先・面談記録", "Salesforce", "なし", "高"),
    ("hr_parser_notion", "企業情報", "なし", "なし", "低"),
    ("hr_executor_line", "氏名・就活情報", "LINE（Lステップ）", "なし", "中"),
    ("hr_executor_slack", "なし", "なし", "なし", "低"),  # Messaging グループノード
    ("hr_watcher_tldv", "面談録画・音声", "なし（読取のみ）", "なし", "中"),
    ("hr_executor_google", "なし", "なし", "なし", "低"),  # Google Suite グループノード
    ("hr_google_gmail",   "メール本文・添付・個人情報", "Gmail", "なし", "高"),
    ("hr_google_gdrive",  "レポート・面接Q&A・議事録", "GDrive/GDocs", "なし", "中"),
    ("hr_google_gsheets", "KPI・選考データ", "GSheets", "なし", "中"),
    ("hr_messaging_line", "氏名・就活情報", "LINE（Lステップ）", "なし", "中"),
    ("hr_messaging_slack","氏名・選考情報", "Slack", "なし", "中"),
    ("hr_processor_coaching", "就活軸・自己分析情報", "なし", "なし", "低"),
    ("hr_processor_interview", "面接想定Q&A", "GDocs", "なし", "低"),
    ("hr_processor_report", "学生所感・評価", "GDrive", "なし", "中"),
    ("hr_processor_supporter", "なし", "なし", "なし", "低"),
    ("hr_orchestrator_main", "全エージェント情報", "複数外部サービス", "要設計", "高"),
    ("exec_strategy", "経営情報・戦略", "なし", "なし", "中"),
    ("exec_ai_trend", "なし", "なし", "なし", "低"),
    ("exec_pl", "財務情報", "なし", "なし", "中"),
    ("exec_team_health", "従業員情報", "なし", "なし", "中"),
    ("exec_approval", "稟議情報", "Slack", "承認者確認必須", "高"),
    ("org_pulse", "従業員情報", "Slack", "なし", "中"),
    ("org_recruiting", "採用候補者情報", "SF/GSheets", "なし", "高"),
    ("org_onboarding", "新メンバー情報", "Notion", "なし", "中"),
    ("org_kpi", "部署KPI", "GSheets", "なし", "低"),
    ("qa_review", "コード情報", "なし", "なし", "低"),
    ("qa_design", "デザイン情報", "なし", "なし", "低"),
    ("qa_creative", "コンテンツ情報", "なし", "なし", "低"),
    ("qa_brand_mgr", "ブランド情報", "なし", "なし", "低"),
    # HRsupport 中途/新卒 + 職種
    ("hrsup_chuto",    "なし", "なし", "なし", "低"),
    ("hrsup_shinsotsu","なし", "なし", "なし", "低"),
    ("hrsup_ca",       "氏名・面談内容・選考評価", "SF/GSheets", "なし", "高"),
    ("hrsup_ra",       "企業情報・選考情報", "SF/GSheets/Slack", "なし", "中"),
    ("hrsup_lg",       "リード候補者情報", "Notion/Slack", "なし", "低"),
    # RPO CS
    ("rpo_cs",         "クライアント採用情報・KPI", "SF/GSheets", "なし", "高"),
    # Sales FS/IS
    ("sales_fs",       "リード・商談情報", "SF/Slack", "なし", "中"),
    ("sales_is",       "リード情報", "SF/Slack", "なし", "中"),
]


# エージェント間エッジ (from_id, to_id, edge_type, label, is_parallel, parallel_group)
AGENT_EDGES_SEED = [
    # ── Orchestrator main → 全HRsupportエージェント（orchestrates）
    ("hr_orchestrator_main", "hr_orchestrator_post_interview", "orchestrates", "委譲", 0, None),
    ("hr_orchestrator_main", "hr_executor_salesforce",         "orchestrates", "委譲", 0, None),
    ("hr_orchestrator_main", "hr_parser_notion",               "orchestrates", "委譲", 0, None),
    ("hr_orchestrator_main", "hr_executor_line",               "orchestrates", "委譲", 0, None),
    ("hr_orchestrator_main", "hr_executor_slack",              "orchestrates", "委譲", 0, None),
    ("hr_orchestrator_main", "hr_watcher_tldv",                "orchestrates", "委譲", 0, None),
    ("hr_orchestrator_main", "hr_executor_google",             "orchestrates", "委譲", 0, None),
    ("hr_orchestrator_main", "hr_processor_coaching",          "orchestrates", "委譲", 0, None),
    ("hr_orchestrator_main", "hr_processor_interview",         "orchestrates", "委譲", 0, None),
    ("hr_orchestrator_main", "hr_processor_report",            "orchestrates", "委譲", 0, None),
    ("hr_orchestrator_main", "hr_processor_supporter",         "orchestrates", "委譲", 0, None),
    # ── 面談後フルサポート（起点: tldv取得 → 並列3本）
    ("hr_orchestrator_post_interview", "hr_watcher_tldv",      "reads",     "議事録取得", 0, None),
    ("hr_orchestrator_post_interview", "hr_executor_salesforce","triggers",  "SF登録",    1, 1),
    ("hr_orchestrator_post_interview", "hr_executor_slack",     "triggers",  "Msg送信",   1, 1),
    ("hr_orchestrator_post_interview", "hr_processor_report",   "triggers",  "レポート生成", 1, 1),
    # ── Salesforce ← tldv（議事録を読んでSFに書く）
    ("hr_executor_salesforce", "hr_watcher_tldv",              "reads",     "議事録参照", 0, None),
    # ── Notion（企業DB）→ Messaging（紹介文に使う）
    ("hr_parser_notion",       "hr_executor_slack",            "writes",    "企業紹介文", 0, None),
    # ── Google Suite → 子エージェント
    ("hr_executor_google", "hr_google_gmail",   "orchestrates", "Gmail",   0, None),
    ("hr_executor_google", "hr_google_gdrive",  "orchestrates", "GDrive",  0, None),
    ("hr_executor_google", "hr_google_gsheets", "orchestrates", "GSheets", 0, None),
    # ── Messaging → 子エージェント
    ("hr_executor_slack",  "hr_messaging_line",  "orchestrates", "LINE",   0, None),
    ("hr_executor_slack",  "hr_messaging_slack", "orchestrates", "Slack",  0, None),
    # ── レポート → Google Suite（GDocs保存）
    ("hr_processor_report",    "hr_executor_google", "triggers", "GDocs保存", 0, None),
    # ── 面接マスター → Google Suite（GDocs出力）
    ("hr_processor_interview", "hr_executor_google", "triggers", "GDocs出力", 0, None),
    # ── Salesforce → Messaging（進捗共有）
    ("hr_executor_salesforce", "hr_executor_slack",  "writes",   "進捗共有",  0, None),
    # ── 新規オーケストレーター階層
    ("hr_orchestrator_main", "rpo_orchestrator",      "orchestrates", "委譲", 0, None),
    ("hr_orchestrator_main", "sales_orchestrator",    "orchestrates", "委譲", 0, None),
    ("hr_orchestrator_main", "hr_dept_orchestrator",  "orchestrates", "委譲", 0, None),
    ("hr_orchestrator_main", "mgmt_orchestrator",     "orchestrates", "委譲", 0, None),
    # 人事部門 → サブ採用
    ("hr_dept_orchestrator", "hr_dept_employee_hiring",   "orchestrates", "委譲", 0, None),
    ("hr_dept_orchestrator", "hr_dept_contractor_hiring", "orchestrates", "委譲", 0, None),
    ("hr_dept_orchestrator", "hr_dept_intern_hiring",     "orchestrates", "委譲", 0, None),
    # 経営管理 → サブ機能
    ("mgmt_orchestrator", "mgmt_accounting", "orchestrates", "委譲", 0, None),
    ("mgmt_orchestrator", "mgmt_legal",      "orchestrates", "委譲", 0, None),
    ("mgmt_orchestrator", "exec_strategy",   "orchestrates", "委譲", 0, None),
    # RPO → SF連携
    ("rpo_orchestrator", "org_recruiting", "orchestrates", "委譲", 0, None),
    # ── HRsupport 中途/新卒 サブ構造
    ("hr_orchestrator_post_interview", "hrsup_chuto",     "orchestrates", "中途委譲", 0, None),
    ("hr_orchestrator_post_interview", "hrsup_shinsotsu", "orchestrates", "新卒委譲", 0, None),
    ("hrsup_chuto",    "hrsup_ca", "orchestrates", "CA",  0, None),
    ("hrsup_chuto",    "hrsup_ra", "orchestrates", "RA",  0, None),
    ("hrsup_shinsotsu","hrsup_ca", "orchestrates", "CA",  0, None),
    ("hrsup_shinsotsu","hrsup_lg", "orchestrates", "LG",  0, None),
    # ── RPO CS
    ("rpo_orchestrator",   "rpo_cs",   "orchestrates", "CS", 0, None),
    # ── Sales FS/IS
    ("sales_orchestrator", "sales_fs", "orchestrates", "FS", 0, None),
    ("sales_orchestrator", "sales_is", "orchestrates", "IS", 0, None),
    # ── 経営戦略層（exec）同士の将来連携（設計中）
    ("exec_strategy",  "exec_pl",          "reads",     "P&L参照",   0, None),
    ("exec_strategy",  "exec_team_health", "reads",     "健全性参照", 0, None),
    ("exec_strategy",  "exec_approval",    "triggers",  "承認フロー", 0, None),
    # ── 組織管理層
    ("org_recruiting", "hr_executor_salesforce", "writes", "候補者登録", 0, None),
    ("org_onboarding", "org_kpi",                "reads",  "KPI参照",   0, None),
]

# ビジネスユニット×ツール接続 (bu, tool, direction, agent_ids, note)
TOOL_CONNECTIONS_SEED = [
    # HRsupport
    ("HRsupport", "Salesforce", "write",
     "hr_executor_salesforce,hr_executor_slack,org_recruiting",
     "面談記録・PersonAccount登録・選考進捗"),
    ("HRsupport", "Notion",     "read",
     "hr_parser_notion,org_onboarding",
     "企業DB取得・研修資料参照"),
    ("HRsupport", "LINE",       "write",
     "hr_executor_line",
     "Lステップ文章配信（6シーン）"),
    ("HRsupport", "Slack",      "write",
     "hr_executor_slack,exec_approval,org_pulse",
     "選考進捗共有・承認フロー・パルスサーベイ"),
    ("HRsupport", "tldv",       "read",
     "hr_watcher_tldv,hr_orchestrator_post_interview",
     "面談録画・議事録取得"),
    ("HRsupport", "Gmail",      "both",
     "hr_executor_google",
     "学生・企業へのメール返信・受信"),
    ("HRsupport", "GDrive",     "write",
     "hr_executor_google,hr_processor_report,hr_processor_interview",
     "レポート・面接Q&A GDocsへ保存"),
    ("HRsupport", "GSheets",    "both",
     "hr_executor_google,hr_executor_salesforce",
     "データ読書き・KPI更新"),
    ("HRsupport", "Claude",     "both",
     "hr_orchestrator_post_interview,hr_orchestrator_main,hr_processor_coaching,hr_processor_interview,hr_processor_report,hr_processor_supporter,hr_parser_notion,hr_executor_google,hr_watcher_tldv",
     "推論・文章生成・分析"),
    # RPO
    ("RPO",       "Salesforce", "both",
     "org_recruiting",
     "採用KPI・パイプライン管理"),
    ("RPO",       "GSheets",    "both",
     "org_kpi",
     "採用KPI集計・レポート"),
    ("RPO",       "Claude",     "both",
     "exec_strategy,exec_ai_trend",
     "戦略分析・AI動向調査"),
    # 経営管理
    ("経営管理",  "Claude",     "both",
     "exec_strategy,exec_pl,exec_team_health,exec_ai_trend",
     "戦略・P&L・チーム健全性"),
    ("経営管理",  "Slack",      "write",
     "exec_approval",
     "承認ワークフロー"),
    ("経営管理",  "GSheets",    "both",
     "exec_pl,org_kpi",
     "財務・KPI管理"),
    # バックオフィス（将来）
    ("バックオフィス", "Claude",     "both", "", "（将来実装）"),
    ("バックオフィス", "GSheets",    "both", "", "経費・契約管理（将来実装）"),
    # Strategy
    ("Strategy",  "Claude",     "both",
     "exec_strategy,exec_ai_trend",
     "OKR設計・競合インテリジェンス"),
    ("Strategy",  "GSheets",    "write",
     "exec_pl",
     "P&Lダッシュボード"),
]


# ── セキュリティレベル定義シード ─────────────────────────────
# (level, name, summary, auth, logging, encryption, pii, audit, badge_color)
SECURITY_LEVEL_DEFS_SEED = [
    (0, "未対応", "開発・テスト専用。本番運用不可",
     "なし", "なし", "なし", "無保護", "なし", "#ef4444"),
    (1, "基本", "社内少数チーム向け最低限の対策",
     "個人APIキー（.env管理）", "実行ログ（ローカル）", "TLS転送のみ",
     "必要フィールドのみ取得", "手動レビュー", "#f59e0b"),
    (2, "標準", "社内全体展開に必要な標準対策",
     "RBAC（役割ベースアクセス制御）", "操作・アクセスログ",
     "TLS + 静止暗号化", "匿名化・マスキング", "定期自動レビュー", "#3b82f6"),
    (3, "強化", "外部パートナー・業務委託展開に必要",
     "MFA + RBAC", "完全監査ログ（改ざん防止）",
     "E2E暗号化", "同意管理・削除権対応", "リアルタイム監視", "#8b5cf6"),
    (4, "エンタープライズ", "外販SaaS・大企業向け最高水準",
     "ゼロトラスト・SSO", "SOC2準拠ログ",
     "KMS鍵管理", "GDPR/個人情報保護法完全対応", "第三者認証・ペネトレーションテスト", "#10b981"),
]

# ── ユースケース別必要セキュリティレベル ────────────────────
# (usecase, required_level, icon, description, sort_order)
USECASE_REQUIREMENTS_SEED = [
    ("社内少数チーム（現在）", 1, "👤",
     "創業メンバー・信頼済みの少数チームのみが利用。APIキー管理と基本ログで対応可能",  1),
    ("社内全体展開",          2, "🏢",
     "全社員が利用。役割ごとのアクセス制御と操作ログが必要",                           2),
    ("業務委託・インターン",  3, "🤝",
     "社外の業務委託・インターン生に展開。MFA・完全監査ログ・PII削除権対応が必要",      3),
    ("RPO事業（外部クライアント）", 3, "📋",
     "外部クライアントの個人情報を扱う。強化レベルのPII管理と監査が必須",               4),
    ("経営管理（機密情報）",  2, "📊",
     "財務・経営情報を扱う。静止暗号化と役割ベースアクセス制御が必要",                  5),
    ("外販 SaaS",            4, "🌐",
     "一般顧客向け販売。GDPR対応・SOC2・ゼロトラスト・ペネトレーションテストが必要",    6),
]

# ── エージェント別現在セキュリティレベル ───────────────────
# canonical_id → current_security_level
AGENT_SECURITY_LEVELS = {
    "hr_orchestrator_post_interview": 1,
    "hr_executor_salesforce":         1,
    "hr_parser_notion":               1,
    "hr_executor_line":               1,
    "hr_executor_slack":              1,
    "hr_watcher_tldv":                1,
    "hr_executor_google":             0,  # Google Suite グループノード
    "hr_google_gmail":                1,
    "hr_google_gdrive":               1,
    "hr_google_gsheets":              1,
    "hr_executor_slack":              0,  # Messaging グループノード
    "hr_messaging_line":              1,
    "hr_messaging_slack":             1,
    "hr_processor_coaching":          0,
    "hr_processor_interview":         0,
    "hr_processor_report":            1,
    "hr_processor_supporter":         0,
    "hr_orchestrator_main":           0,
    "exec_strategy":                  1,
    "exec_ai_trend":                  0,
    "exec_pl":                        1,
    "exec_team_health":               1,
    "exec_approval":                  0,
    "org_pulse":                      0,
    "org_recruiting":                 0,
    "org_onboarding":                 0,
    "org_kpi":                        0,
    "qa_review":                      0,
    "qa_design":                      0,
    "qa_creative":                    0,
    "qa_brand_mgr":                   0,
    # 新規エージェント
    "rpo_orchestrator":               0,
    "sales_orchestrator":             0,
    "hr_dept_orchestrator":           0,
    "hr_dept_employee_hiring":        0,
    "hr_dept_contractor_hiring":      0,
    "hr_dept_intern_hiring":          0,
    "mgmt_orchestrator":              0,
    "mgmt_accounting":  0,
    "mgmt_legal":       0,
    # HRsupport 中途/新卒 + 職種
    "hrsup_chuto":    0,
    "hrsup_shinsotsu":0,
    "hrsup_ca":       0,
    "hrsup_ra":       0,
    "hrsup_lg":       0,
    # RPO CS
    "rpo_cs":         0,
    # Sales FS/IS
    "sales_fs":       0,
    "sales_is":       0,
}


def migrate() -> None:
    init_db()
    conn = get_conn()

    # ── 名称・定義変更（既存レコードの上書き更新） ────────────
    _name_updates = [
        ("HRsupportオーケストレーター", "hr_orchestrator_post_interview"),
        ("Google Suite",  "hr_executor_google"),
        ("Messaging",     "hr_executor_slack"),
    ]
    for name, cid in _name_updates:
        conn.execute("UPDATE agents SET name = ? WHERE canonical_id = ?", (name, cid))
        conn.execute("UPDATE roadmap SET name = ? WHERE canonical_id = ?", (name, cid))

    # ── 旧エージェント（社員/業委スプリット版）を削除 ──────────
    # 社員/業務委託/インターン生はAIエージェントではなく権限グループで管理するため整理
    _obsolete_ids = [
        "hrsup_ca_seishain", "hrsup_ca_gyomu",
        "rpo_cs_seishain",   "rpo_cs_gyomu",
        "sales_fs_seishain", "sales_fs_gyomu",
        "sales_is_seishain", "sales_is_gyomu",
        "hr_executor_line",  # Messaging グループ(hr_executor_slack)＋hr_messaging_lineに統合
    ]
    placeholders = ",".join("?" * len(_obsolete_ids))
    conn.execute(f"DELETE FROM agents       WHERE canonical_id IN ({placeholders})", _obsolete_ids)
    conn.execute(f"DELETE FROM roadmap      WHERE canonical_id IN ({placeholders})", _obsolete_ids)
    conn.execute(f"DELETE FROM security_info WHERE canonical_id IN ({placeholders})", _obsolete_ids)
    conn.execute(
        f"DELETE FROM agent_edges WHERE from_id IN ({placeholders}) OR to_id IN ({placeholders})",
        _obsolete_ids + _obsolete_ids,
    )

    # agents テーブル投入
    conn.executemany(
        """
        INSERT OR IGNORE INTO agents
            (canonical_id, name, layer, status, level, apis, description, impl_method, launched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        AGENTS_SEED,
    )

    # roadmap テーブル投入（シードで管理するエントリのみ一旦削除して入れ直す）
    seed_nos = [row[0] for row in ROADMAP_SEED]
    if seed_nos:
        placeholders_rm = ",".join("?" * len(seed_nos))
        conn.execute(f"DELETE FROM roadmap WHERE agent_no IN ({placeholders_rm})", seed_nos)
    conn.executemany(
        """
        INSERT INTO roadmap
            (agent_no, canonical_id, name, description, status, layer, operator,
             start_date, launch_date, priority, integrations, phase)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ROADMAP_SEED,
    )

    # security_info テーブル投入
    conn.executemany(
        """
        INSERT OR IGNORE INTO security_info
            (canonical_id, pii_types, external_writes, human_in_loop, risk_level)
        VALUES (?, ?, ?, ?, ?)
        """,
        SECURITY_SEED,
    )

    # agent_edges テーブル投入
    conn.executemany(
        """
        INSERT OR IGNORE INTO agent_edges
            (from_id, to_id, edge_type, label, is_parallel, parallel_group)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        AGENT_EDGES_SEED,
    )

    # tool_connections テーブル投入
    conn.executemany(
        """
        INSERT OR IGNORE INTO tool_connections
            (bu, tool, direction, agent_ids, note)
        VALUES (?, ?, ?, ?, ?)
        """,
        TOOL_CONNECTIONS_SEED,
    )

    # security_level_defs 投入
    conn.executemany(
        """
        INSERT OR IGNORE INTO security_level_defs
            (level, name, summary, auth, logging, encryption, pii, audit, badge_color)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        SECURITY_LEVEL_DEFS_SEED,
    )

    # usecase_requirements 投入
    conn.executemany(
        """
        INSERT OR IGNORE INTO usecase_requirements
            (usecase, required_level, icon, description, sort_order)
        VALUES (?, ?, ?, ?, ?)
        """,
        USECASE_REQUIREMENTS_SEED,
    )

    # security_info に列が存在しない場合は追加（既存DB対応）
    try:
        conn.execute("ALTER TABLE security_info ADD COLUMN current_security_level INTEGER DEFAULT 0")
        conn.commit()
    except Exception:
        pass  # 既に存在する場合はスキップ

    # エージェント別セキュリティレベル更新
    for cid, lvl in AGENT_SECURITY_LEVELS.items():
        conn.execute(
            "UPDATE security_info SET current_security_level = ? WHERE canonical_id = ?",
            (lvl, cid),
        )

    conn.commit()
    conn.close()
    print(
        f"✅ マイグレーション完了: {len(AGENTS_SEED)}体 / {len(AGENT_EDGES_SEED)}エッジ / "
        f"{len(TOOL_CONNECTIONS_SEED)}ツール接続 / セキュリティLv定義{len(SECURITY_LEVEL_DEFS_SEED)}件"
    )


if __name__ == "__main__":
    migrate()
