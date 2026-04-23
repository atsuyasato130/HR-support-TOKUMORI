// =================================================================
// AI推進室 統合管理ダッシュボード v2.0
// 対象SS: 1g8PzcuPuUTTdO-kcSh4niuwfLw6d8zN8JQMZCrmyuH8
//
// 実行手順:
//   1. Apps Script エディタで このファイルを貼り付け
//   2. setupAll() を実行
//   3. 既存の Update_Log は互換フォーマットで自動引き継ぎ
// =================================================================

// ── カラーパレット ────────────────────────────────────────────────
const C = {
  BG:       "#ffffff",   // 白背景
  CARD:     "#f8f9fa",   // 薄いグレーカード
  HEADER:   "#e8eaed",   // ヘッダー行
  BORDER:   "#dadce0",
  WHITE:    "#202124",   // メインテキスト（黒）
  GRAY:     "#5f6368",   // サブテキスト
  LGRAY:    "#80868b",   // 補足テキスト
  ACCENT:   "#3c4043",   // ヘッダー文字
  GREEN:    "#1e8e3e",
  YELLOW:   "#f29900",
  RED:      "#d93025",
  BLUE:     "#1a73e8",
  PURPLE:   "#9334e6",
};

// ── タブ定義 ─────────────────────────────────────────────────────
const TABS = {
  HOME:     { name: "🏠 HOME",           color: "#ffffff" },
  DASH:     { name: "📊 Dashboard",      color: "#4caf50" },
  ROADMAP:  { name: "🗺️ Roadmap",        color: "#64b5f6" },
  BOARD:    { name: "📋 Project Board",  color: "#ffc107" },
  BACKLOG:  { name: "🏢 BU Backlog",     color: "#f44336" },
  LOG:      { name: "📝 Update_Log",     color: "#888888" },
  REGISTRY: { name: "🤖 Agent Registry", color: "#ce93d8" },
  INTEL:    { name: "💡 Intel Log",      color: "#333333" },
};

// ── エージェント定義 ─────────────────────────────────────────────
const AGENTS = [
  { id:1,  name:"面談後フルサポート",   domain:"RPO",       owner:"佐藤",   status:"稼働中", desc:"tldv→SF→LINE→レポート（ワンストップ）" },
  { id:2,  name:"面接マスター",         domain:"RPO",       owner:"佐藤",   status:"稼働中", desc:"志望動機・ガクチカ・逆質問 全シーン対策" },
  { id:3,  name:"Salesforce",          domain:"共通",       owner:"佐藤",   status:"稼働中", desc:"tldv議事録→SF自動登録・更新" },
  { id:4,  name:"Notion",             domain:"共通",        owner:"佐藤",   status:"稼働中", desc:"企業DB・企業紹介文生成" },
  { id:5,  name:"LINE",               domain:"HRsupport",  owner:"佐藤",   status:"稼働中", desc:"Lステップ文章生成（6シーン）" },
  { id:6,  name:"Slack",              domain:"共通",        owner:"佐藤",   status:"稼働中", desc:"選考進捗Slack自動共有" },
  { id:7,  name:"学生コーチング",       domain:"RPO",       owner:"佐藤",   status:"稼働中", desc:"ES・面接対策 / 就活軸深掘り" },
  { id:8,  name:"レポート",            domain:"RPO",        owner:"佐藤",   status:"稼働中", desc:"学生所感レポート自動生成" },
  { id:9,  name:"tldv",               domain:"共通",        owner:"佐藤",   status:"稼働中", desc:"議事録取得・Claude分析" },
  { id:10, name:"Google",             domain:"共通",        owner:"佐藤",   status:"稼働中", desc:"Gmail・Sheets・Docs連携" },
  { id:11, name:"サポーター",          domain:"共通",        owner:"佐藤",   status:"稼働中", desc:"使い方・システムガイド" },
  { id:12, name:"Orchestrator",       domain:"全体",        owner:"未定",   status:"開発中", desc:"マルチエージェント自律分業（Phase 3）" },
];

// =================================================================
// ENTRY POINT
// =================================================================
function setupAll() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  Logger.log("=== AI推進室 統合管理ダッシュボード v2.0 セットアップ開始 ===");

  _ensureTabs(ss);
  _setupHome(ss);
  _setupDashboard(ss);
  _setupRoadmap(ss);
  _setupProjectBoard(ss);
  _setupBUBacklog(ss);
  _migrateUpdateLog(ss);      // 既存互換
  _setupAgentRegistry(ss);
  _setupIntelLog(ss);
  _reorderTabs(ss);

  SpreadsheetApp.flush();
  Logger.log("=== セットアップ完了 ===");
}

// =================================================================
// Tab 1: 🏠 HOME — 全員が最初に見るAI化現在地
// =================================================================
function _setupHome(ss) {
  const sh = ss.getSheetByName(TABS.HOME.name);
  sh.clear();
  sh.setColumnWidths(1, 10, 120);
  sh.setColumnWidth(1, 30);
  sh.setColumnWidth(10, 30);

  // ── タイトルブロック ──────────────────────────────────────────
  _mc(sh, 1, 2, 1, 8, "AI推進室 統合管理ダッシュボード", {
    bg: C.BG, fg: C.WHITE, bold: true, size: 22, align: "center", vAlign: "middle", h: 52,
  });
  _mc(sh, 2, 2, 1, 8, "すべての部署が、会社のAI化の「今」をリアルタイムで把握するための司令塔", {
    bg: C.BG, fg: C.GRAY, size: 10, align: "center",
  });

  // ── ナビゲーションカード ──────────────────────────────────────
  _mc(sh, 4, 2, 1, 8, "▸  NAVIGATION — 各タブの使い方", {
    bg: C.HEADER, fg: C.GRAY, bold: true, size: 9,
  });

  const navItems = [
    ["📊 Dashboard",     "削減時間・ROI・エージェント稼働状況をリアルタイムで確認",         "全員"],
    ["🗺️ Roadmap",       "①〜⑫エージェントの開発進捗と担当者を確認・更新する",             "PM/開発者"],
    ["📋 Project Board", "進行中プロジェクトのタスク管理。誰でも追記・ステータス更新OK",     "全員"],
    ["🏢 BU Backlog",    "RPO/HRsupportの現場課題を起票。解決優先度を全体で共有する",       "全員"],
    ["📝 Update_Log",    "AIシステムへの変更履歴が自動記録される（書き込みはシステム側）",   "参照のみ"],
    ["🤖 Agent Registry","稼働中エージェントの仕様・API・担当者一覧",                        "開発者/PM"],
    ["💡 Intel Log",     "エージェントの成功/失敗ログ蓄積。外販時の実績アセットになる",      "開発者"],
  ];

  navItems.forEach(([tab, desc, who], i) => {
    const row = 5 + i;
    const bg = i % 2 === 0 ? C.CARD : C.BG;
    _cell(sh, row, 2, tab,  { bg, fg: C.WHITE, bold: true, size: 10 });
    _cell(sh, row, 4, desc, { bg, fg: C.LGRAY, size: 9 });
    sh.getRange(row, 4, 1, 5).merge().setBackground(bg).setFontColor(C.LGRAY).setFontSize(9).setVerticalAlignment("middle");
    _cell(sh, row, 9, who,  { bg, fg: C.GRAY, size: 9, align: "center" });
    sh.setRowHeight(row, 30);
  });

  // ── KPIスナップショット（数式で他タブから引用） ───────────────
  _mc(sh, 13, 2, 1, 8, "▸  KPI SNAPSHOT", {
    bg: C.HEADER, fg: C.GRAY, bold: true, size: 9,
  });

  const kpiCards = [
    { label: "稼働エージェント",  formula: `COUNTIF('🤖 Agent Registry'!D:D,"稼働中")`,  unit: "体" },
    { label: "累計削減時間",      formula: `IFERROR(SUM('💡 Intel Log'!E:E),0)`,          unit: "h" },
    { label: "未解決バックログ",  formula: `COUNTIF('🏢 BU Backlog'!F:F,"未対応")`,       unit: "件" },
    { label: "進行中プロジェクト",formula: `COUNTIF('📋 Project Board'!D:D,"進行中")`,    unit: "件" },
  ];

  kpiCards.forEach((k, i) => {
    const col = 2 + i * 2;
    _mc(sh, 14, col, 1, 2, k.label, { bg: C.CARD, fg: C.GRAY, size: 9, align: "center" });
    const valRange = sh.getRange(15, col, 1, 2).merge();
    valRange.setFormula(`=${k.formula}&" ${k.unit}"`)
      .setBackground(C.CARD).setFontColor(C.WHITE)
      .setFontSize(20).setFontWeight("bold").setHorizontalAlignment("center")
      .setVerticalAlignment("middle").setFontFamily("Roboto Mono");
    sh.setRowHeight(15, 48);
  });

  // ── 更新ルール説明 ────────────────────────────────────────────
  _mc(sh, 17, 2, 1, 8, "▸  このダッシュボードのルール", {
    bg: C.HEADER, fg: C.GRAY, bold: true, size: 9,
  });

  const rules = [
    "① Project Board と BU Backlog は全員が自由に書き込めます",
    "② Roadmap の担当者欄・ステータスは PM/開発者が更新してください",
    "③ Update_Log はシステムが自動書き込みします（手動編集不要）",
    "④ Intel Log に蓄積されたデータは外部販売時の実績証明になります。できる限り詳細に",
    "⑤ 数字を動かしたい場合は Dashboard タブへ（KPIの手動入力欄あり）",
  ];
  rules.forEach((rule, i) => {
    const row = 18 + i;
    _mc(sh, row, 2, 1, 8, rule, { bg: i % 2 === 0 ? C.CARD : C.BG, fg: C.LGRAY, size: 9 });
    sh.setRowHeight(row, 26);
  });

  _applyDarkBg(sh, 25, 10);
  sh.setFrozenRows(0);
}

// =================================================================
// Tab 2: 📊 Dashboard — KPI / ROI / 稼働状況
// =================================================================
function _setupDashboard(ss) {
  const sh = ss.getSheetByName(TABS.DASH.name);
  sh.clear();

  // ヘッダー
  _mc(sh, 1, 1, 1, 9, "📊  DASHBOARD — AI推進室 経営指標", {
    bg: C.BG, fg: C.WHITE, bold: true, size: 16, h: 44,
  });
  _mc(sh, 2, 1, 1, 9, "削減時間・ROI・エージェント稼働状況のリアルタイム集計", {
    bg: C.BG, fg: C.GRAY, size: 9,
  });

  // ── KPIカード（行4-6） ────────────────────────────────────────
  _mc(sh, 4, 1, 1, 9, "KEY METRICS", { bg: C.HEADER, fg: C.GRAY, bold: true, size: 9 });

  const kpis = [
    { label: "累計削減時間 (h)",   col: 1, formula: `=IFERROR(SUM('💡 Intel Log'!E:E),0)` },
    { label: "月間推計ROI",        col: 3, formula: `=IFERROR("¥"&TEXT(SUM('💡 Intel Log'!E:E)*5000,"#,##0"),"—")` },
    { label: "稼働エージェント",   col: 5, formula: `=COUNTIF('🤖 Agent Registry'!D:D,"稼働中")&" / 12体"` },
    { label: "未解決バックログ",   col: 7, formula: `=COUNTIF('🏢 BU Backlog'!F:F,"未対応")&"件"` },
  ];

  kpis.forEach((k) => {
    _mc(sh, 5, k.col, 1, 2, k.label, { bg: C.CARD, fg: C.GRAY, size: 9, align: "center" });
    sh.getRange(6, k.col, 1, 2).merge()
      .setFormula(k.formula)
      .setBackground(C.CARD).setFontColor(C.WHITE)
      .setFontSize(22).setFontWeight("bold")
      .setHorizontalAlignment("center").setVerticalAlignment("middle")
      .setFontFamily("Roboto Mono");
    sh.setRowHeight(6, 52);
  });

  // ── 手動入力KPI（チーム全員で記録） ──────────────────────────
  _mc(sh, 8, 1, 1, 9, "MANUAL KPI — 部署別実績入力（月次）", {
    bg: C.HEADER, fg: C.GRAY, bold: true, size: 9,
  });

  const manualHeaders = ["部署", "担当者", "対象業務", "従来所要時間(h)", "AI後所要時間(h)", "削減時間(h)", "削減率(%)", "記録日", "備考"];
  manualHeaders.forEach((h, i) => {
    _cell(sh, 9, i + 1, h, { bg: C.HEADER, fg: C.ACCENT, bold: true, size: 9 });
  });

  const manualSamples = [
    ["RPO",       "佐藤", "面談後SF登録",       2.0, 0.1, "", "", "2026-03-27", "Salesforce Agent導入後"],
    ["RPO",       "佐藤", "学生所感レポート作成", 1.5, 0.2, "", "", "2026-03-27", "Report Agent"],
    ["HRsupport", "—",   "週次レポート作成",     3.0, 0.2, "", "", "2026-03-27", "Report Agent"],
    ["HRsupport", "—",   "LINE返信",            0.5, 0.05,"", "", "2026-03-27", "LINE Agent"],
  ];
  manualSamples.forEach((row, i) => {
    const bg = i % 2 === 0 ? C.CARD : C.BG;
    row.forEach((v, j) => {
      _cell(sh, 10 + i, j + 1, v, { bg, fg: C.WHITE, size: 9 });
    });
    // F列（削減時間）= D - E の数式
    sh.getRange(10 + i, 6).setFormula(`=IF(D${10+i}<>"",D${10+i}-E${10+i},"")`).setBackground(bg).setFontColor(C.GREEN).setFontSize(9);
    // G列（削減率）= (D-E)/D の数式
    sh.getRange(10 + i, 7).setFormula(`=IF(D${10+i}>0,ROUND((D${10+i}-E${10+i})/D${10+i}*100,0)&"%","")`).setBackground(bg).setFontColor(C.GREEN).setFontSize(9);
  });

  // ── エージェント稼働マップ ────────────────────────────────────
  _mc(sh, 16, 1, 1, 9, "AGENT STATUS MAP", { bg: C.HEADER, fg: C.GRAY, bold: true, size: 9 });
  const agHeaders = ["#", "Agent Name", "Domain", "Status", "担当者", "今月ログ数", "今月削減h", "最終稼働", "メモ"];
  agHeaders.forEach((h, i) => {
    _cell(sh, 17, i + 1, h, { bg: C.HEADER, fg: C.ACCENT, bold: true, size: 9 });
  });

  AGENTS.forEach((a, i) => {
    const row = 18 + i;
    const bg = i % 2 === 0 ? C.CARD : C.BG;
    const sc = a.status === "稼働中" ? C.GREEN : a.status === "開発中" ? C.YELLOW : C.RED;
    [a.id, a.name, a.domain, a.status, a.owner].forEach((v, j) => {
      const cell = sh.getRange(row, j + 1).setValue(v).setBackground(bg).setFontColor(C.WHITE).setFontSize(9);
      if (j === 3) cell.setFontColor(sc).setFontWeight("bold");
    });
    // 今月ログ数
    sh.getRange(row, 6).setFormula(`=COUNTIFS('💡 Intel Log'!B:B,"${a.name}",'💡 Intel Log'!A:A,">="&DATE(YEAR(TODAY()),MONTH(TODAY()),1))`).setBackground(bg).setFontColor(C.BLUE).setFontSize(9);
    // 今月削減h
    sh.getRange(row, 7).setFormula(`=IFERROR(SUMIFS('💡 Intel Log'!E:E,'💡 Intel Log'!B:B,"${a.name}",'💡 Intel Log'!A:A,">="&DATE(YEAR(TODAY()),MONTH(TODAY()),1)),0)`).setBackground(bg).setFontColor(C.GREEN).setFontSize(9);
    // 最終稼働
    sh.getRange(row, 8).setFormula(`=IFERROR(IF(MAXIFS('💡 Intel Log'!A:A,'💡 Intel Log'!B:B,"${a.name}")>0,TEXT(MAXIFS('💡 Intel Log'!A:A,'💡 Intel Log'!B:B,"${a.name}"),"yyyy/mm/dd"),"—"),"—")`).setBackground(bg).setFontColor(C.GRAY).setFontSize(9);
    _cell(sh, row, 9, "", { bg, fg: C.GRAY, size: 9 });
  });

  _applyDarkBg(sh, 35, 9);
  sh.setColumnWidths(1, 9, 130);
  sh.setColumnWidth(1, 30);
  sh.setFrozenRows(4);
}

// =================================================================
// Tab 3: 🗺️ Roadmap — ①〜⑫ 開発進捗 + 担当者
// =================================================================
function _setupRoadmap(ss) {
  const sh = ss.getSheetByName(TABS.ROADMAP.name);
  sh.clear();

  _mc(sh, 1, 1, 1, 10, "🗺️  AGENT ROADMAP — ①〜⑫ 開発ステータス管理", {
    bg: C.BG, fg: C.WHITE, bold: true, size: 16, h: 44,
  });
  _mc(sh, 2, 1, 1, 10, "担当者・ステータスは PM / 開発者が随時更新してください", {
    bg: C.BG, fg: C.GRAY, size: 9,
  });

  // 進捗サマリー
  _mc(sh, 4, 1, 1, 10, "PROGRESS OVERVIEW", { bg: C.HEADER, fg: C.GRAY, bold: true, size: 9 });
  const progCells = [
    { label: "稼働中", formula: `=COUNTIF(D8:D19,"稼働中")`, color: C.GREEN },
    { label: "開発中", formula: `=COUNTIF(D8:D19,"開発中")`, color: C.YELLOW },
    { label: "未着手", formula: `=COUNTIF(D8:D19,"未着手")`, color: C.GRAY },
    { label: "完了率", formula: `=ROUND(COUNTIF(D8:D19,"稼働中")/12*100,0)&"%"`, color: C.WHITE },
  ];
  progCells.forEach((p, i) => {
    const col = i * 2 + 1;
    _mc(sh, 5, col, 1, 2, p.label, { bg: C.CARD, fg: C.GRAY, size: 9, align: "center" });
    sh.getRange(6, col, 1, 2).merge()
      .setFormula(p.formula)
      .setBackground(C.CARD).setFontColor(p.color)
      .setFontSize(22).setFontWeight("bold").setHorizontalAlignment("center").setVerticalAlignment("middle")
      .setFontFamily("Roboto Mono");
    sh.setRowHeight(6, 44);
  });

  // テーブルヘッダー
  const headers = ["#", "エージェント名", "概要", "Status", "Domain", "担当者", "開始日", "稼働日", "優先度", "連携先"];
  headers.forEach((h, i) => {
    _cell(sh, 7, i + 1, h, { bg: C.HEADER, fg: C.ACCENT, bold: true, size: 9 });
  });

  // データ行
  AGENTS.forEach((a, i) => {
    const row = 8 + i;
    const bg = i % 2 === 0 ? C.CARD : C.BG;
    const sc = a.status === "稼働中" ? C.GREEN : a.status === "開発中" ? C.YELLOW : C.GRAY;
    const values = [a.id, a.name, a.desc, a.status, a.domain, a.owner, "2026-03-01", a.status === "稼働中" ? "2026-03-18" : "—", "High", "—"];
    values.forEach((v, j) => {
      const cell = sh.getRange(row, j + 1).setValue(v).setBackground(bg).setFontColor(C.WHITE).setFontSize(9);
      if (j === 3) cell.setFontColor(sc).setFontWeight("bold");
    });
    sh.setRowHeight(row, 28);
  });

  // 条件付き書式
  const statusRange = sh.getRange(8, 4, 12, 1);
  const cfRules = [
    SpreadsheetApp.newConditionalFormatRule().whenTextEqualTo("稼働中").setFontColor(C.GREEN).setRanges([statusRange]).build(),
    SpreadsheetApp.newConditionalFormatRule().whenTextEqualTo("開発中").setFontColor(C.YELLOW).setRanges([statusRange]).build(),
    SpreadsheetApp.newConditionalFormatRule().whenTextEqualTo("未着手").setFontColor(C.GRAY).setRanges([statusRange]).build(),
    SpreadsheetApp.newConditionalFormatRule().whenTextEqualTo("停止中").setFontColor(C.RED).setRanges([statusRange]).build(),
  ];
  sh.setConditionalFormatRules(cfRules);

  // データ検証
  const statusVal = SpreadsheetApp.newDataValidation()
    .requireValueInList(["稼働中", "開発中", "未着手", "停止中", "完了"]).build();
  sh.getRange(8, 4, 12, 1).setDataValidation(statusVal);

  const priorityVal = SpreadsheetApp.newDataValidation()
    .requireValueInList(["Critical", "High", "Medium", "Low"]).build();
  sh.getRange(8, 9, 12, 1).setDataValidation(priorityVal);

  _applyDarkBg(sh, 25, 10);
  sh.setColumnWidths(1, 10, 130);
  sh.setColumnWidth(1, 30);
  sh.setColumnWidth(3, 240);
  sh.setFrozenRows(7);
}

// =================================================================
// Tab 4: 📋 Project Board — チーム全員が書けるKanban
// =================================================================
function _setupProjectBoard(ss) {
  const sh = ss.getSheetByName(TABS.BOARD.name);
  sh.clear();

  _mc(sh, 1, 1, 1, 9, "📋  PROJECT BOARD — AI推進室 プロジェクト管理", {
    bg: C.BG, fg: C.WHITE, bold: true, size: 16, h: 44,
  });
  _mc(sh, 2, 1, 1, 9, "誰でも追記・ステータス更新OK。新しいプロジェクトは最下行に追加してください", {
    bg: C.BG, fg: C.GRAY, size: 9,
  });

  // ステータス別カウント
  const statuses = ["アイデア", "承認待ち", "進行中", "レビュー中", "完了", "保留"];
  const statColors = [C.GRAY, C.YELLOW, C.BLUE, C.PURPLE, C.GREEN, C.RED];
  _mc(sh, 4, 1, 1, 9, "STATUS OVERVIEW", { bg: C.HEADER, fg: C.GRAY, bold: true, size: 9 });

  statuses.forEach((s, i) => {
    const col = i + 1;
    _cell(sh, 5, col, s, { bg: C.CARD, fg: statColors[i], bold: true, size: 9, align: "center" });
    sh.getRange(6, col)
      .setFormula(`=COUNTIF(D10:D200,"${s}")`)
      .setBackground(C.CARD).setFontColor(statColors[i])
      .setFontSize(18).setFontWeight("bold").setHorizontalAlignment("center")
      .setFontFamily("Roboto Mono");
    sh.setRowHeight(6, 36);
  });
  _cell(sh, 5, 8, "合計", { bg: C.CARD, fg: C.GRAY, bold: true, size: 9, align: "center" });
  sh.getRange(6, 8).setFormula(`=COUNTA(D10:D200)`).setBackground(C.CARD).setFontColor(C.WHITE).setFontSize(18).setFontWeight("bold").setHorizontalAlignment("center");

  // テーブル
  _mc(sh, 8, 1, 1, 9, "PROJECT LIST — 新規追加は最下行へ", { bg: C.HEADER, fg: C.GRAY, bold: true, size: 9 });
  const pHeaders = ["#", "プロジェクト名", "概要・目的", "Status", "担当BU", "担当者", "期限", "優先度", "備考"];
  pHeaders.forEach((h, i) => {
    _cell(sh, 9, i + 1, h, { bg: C.HEADER, fg: C.ACCENT, bold: true, size: 9 });
  });

  // サンプルプロジェクト
  const projects = [
    [1, "Monitoring OS構築",           "AI推進室全体の統合管理ダッシュボード整備",            "進行中",   "全体",       "佐藤",  "2026-03-31", "Critical", "このシート自体"],
    [2, "BU Surveyアンケート設計",      "各部署の課題・AI自動化ニーズを定量把握",              "進行中",   "全体",       "佐藤",  "2026-04-05", "High",     "GAS分析ロジック実装済み"],
    [3, "Orchestrator(⑫)開発",         "マルチエージェント自律分業ワークフロー",               "開発中",   "全体",       "佐藤",  "2026-04-30", "High",     "雛形コード作成済み"],
    [4, "GitHubリポジトリ整備",         "Internal/Personal 2系統の分離管理",                  "アイデア", "全体",       "佐藤",  "2026-04-15", "Medium",   ""],
    [5, "HRsupport LINE自動化拡張",     "LINE返信エージェントの対応シーン追加",                "アイデア", "HRsupport",  "—",    "2026-05-01", "Medium",   "担当者未定"],
    [6, "外販パッケージ化 Phase1",      "Monitoring OSの業務情報除去・テンプレ化",             "保留",     "全体",       "佐藤",  "2026-06-01", "Medium",   "内部完成後着手"],
  ];
  projects.forEach((p, i) => {
    const bg = i % 2 === 0 ? C.CARD : C.BG;
    p.forEach((v, j) => {
      const cell = sh.getRange(10 + i, j + 1).setValue(v).setBackground(bg).setFontColor(C.WHITE).setFontSize(9);
      if (j === 3) {
        const sc = { "進行中": C.BLUE, "開発中": C.YELLOW, "完了": C.GREEN, "保留": C.RED, "アイデア": C.GRAY, "承認待ち": C.YELLOW, "レビュー中": C.PURPLE }[v] || C.WHITE;
        cell.setFontColor(sc).setFontWeight("bold");
      }
    });
    sh.setRowHeight(10 + i, 30);
  });

  // データ検証
  sh.getRange(10, 4, 100, 1).setDataValidation(
    SpreadsheetApp.newDataValidation().requireValueInList(statuses).build()
  );
  sh.getRange(10, 5, 100, 1).setDataValidation(
    SpreadsheetApp.newDataValidation().requireValueInList(["全体", "RPO", "HRsupport"]).build()
  );
  sh.getRange(10, 8, 100, 1).setDataValidation(
    SpreadsheetApp.newDataValidation().requireValueInList(["Critical", "High", "Medium", "Low"]).build()
  );

  // 条件付き書式
  const statusRange2 = sh.getRange(10, 4, 100, 1);
  sh.setConditionalFormatRules([
    SpreadsheetApp.newConditionalFormatRule().whenTextEqualTo("進行中").setFontColor(C.BLUE).setRanges([statusRange2]).build(),
    SpreadsheetApp.newConditionalFormatRule().whenTextEqualTo("完了").setFontColor(C.GREEN).setRanges([statusRange2]).build(),
    SpreadsheetApp.newConditionalFormatRule().whenTextEqualTo("保留").setFontColor(C.RED).setRanges([statusRange2]).build(),
    SpreadsheetApp.newConditionalFormatRule().whenTextEqualTo("アイデア").setFontColor(C.GRAY).setRanges([statusRange2]).build(),
    SpreadsheetApp.newConditionalFormatRule().whenTextEqualTo("承認待ち").setFontColor(C.YELLOW).setRanges([statusRange2]).build(),
  ]);

  _applyDarkBg(sh, 200, 9);
  sh.setColumnWidths(1, 9, 140);
  sh.setColumnWidth(1, 30);
  sh.setColumnWidth(3, 260);
  sh.setFrozenRows(9);
}

// =================================================================
// Tab 5: 🏢 BU Backlog — 部署横断の課題管理
// =================================================================
function _setupBUBacklog(ss) {
  const sh = ss.getSheetByName(TABS.BACKLOG.name);
  sh.clear();

  _mc(sh, 1, 1, 1, 9, "🏢  BU BACKLOG — 現場の課題・AIへの要望", {
    bg: C.BG, fg: C.WHITE, bold: true, size: 16, h: 44,
  });
  _mc(sh, 2, 1, 1, 9, "どの部署の人でも起票OK。「困ってること」をどんどん書いてください", {
    bg: C.BG, fg: C.GRAY, size: 9,
  });

  // サマリー
  _mc(sh, 4, 1, 1, 9, "SUMMARY", { bg: C.HEADER, fg: C.GRAY, bold: true, size: 9 });
  const sumCols = [
    { l: "総課題数",  f: `=COUNTA(B9:B500)`,            c: C.WHITE },
    { l: "未対応",    f: `=COUNTIF(F9:F500,"未対応")`,   c: C.RED },
    { l: "対応中",    f: `=COUNTIF(F9:F500,"対応中")`,   c: C.YELLOW },
    { l: "完了",      f: `=COUNTIF(F9:F500,"完了")`,     c: C.GREEN },
    { l: "RPO",       f: `=COUNTIF(C9:C500,"RPO")`,      c: C.BLUE },
    { l: "HRsupport", f: `=COUNTIF(C9:C500,"HRsupport")`,c: C.PURPLE },
  ];
  sumCols.forEach((s, i) => {
    _cell(sh, 5, i + 1, s.l, { bg: C.CARD, fg: C.GRAY, size: 9, align: "center" });
    sh.getRange(6, i + 1).setFormula(s.f)
      .setBackground(C.CARD).setFontColor(s.c)
      .setFontSize(18).setFontWeight("bold").setHorizontalAlignment("center")
      .setFontFamily("Roboto Mono");
    sh.setRowHeight(6, 36);
  });

  // テーブルヘッダー
  _mc(sh, 8, 1, 1, 9, "BACKLOG LIST — 新規起票は最下行に追加してください", { bg: C.HEADER, fg: C.GRAY, bold: true, size: 9 });
  const bHeaders = ["起票日", "課題タイトル", "BU", "詳細（現場の声）", "推定削減h", "対応状況", "優先度", "担当エージェント", "解決日"];
  bHeaders.forEach((h, i) => {
    _cell(sh, 9, i + 1, h, { bg: C.HEADER, fg: C.ACCENT, bold: true, size: 9 });
  });

  // サンプルデータ（現場のリアルな声）
  const backlog = [
    ["2026-03-27", "面接後のメール送付・SF登録が二度手間",       "RPO",       "面接が終わるたびに手動でSFを開いて入力。次の面接の時間が迫っていて毎回ヒヤヒヤ",         2.0, "対応中", "Critical", "面談後フルサポート",  "—"],
    ["2026-03-27", "LINEの返信文章がバラバラで品質管理できない",  "HRsupport", "担当者によって返信の速度・内容・丁寧さがバラバラ。クレームになる前に統一したい",         0.5, "対応中", "High",     "LINE Agent",          "—"],
    ["2026-03-26", "週次レポートの作成に毎週3時間かかる",          "共通",      "毎週月曜の朝をレポート作成で潰している。自動化できるなら最優先でやってほしい",           3.0, "完了",   "Critical", "Report Agent",        "2026-03-24"],
    ["2026-03-26", "面談の議事録がNotion未登録のまま放置される",   "HRsupport", "担当者が忙しいと議事録をNotionに上げるのを忘れる。ナレッジが消える",                     1.0, "未対応", "High",     "Notion Agent",        "—"],
    ["2026-03-25", "企業紹介文の作成に1社あたり15分かかる",        "RPO",       "学生に送る企業紹介文を毎回ゼロから書いている。月に50社分。それだけで12.5h消える",       12.5,"完了",   "High",     "Notion/LINE Agent",   "2026-03-20"],
    ["2026-03-25", "Slack進捗共有のフォーマットがまちまち",         "共通",      "誰がどの学生をどのフェーズで担当してるか、Slackを全部読まないとわからない",             1.5, "未対応", "Medium",   "Slack Agent",         "—"],
  ];
  backlog.forEach((row, i) => {
    const bg = i % 2 === 0 ? C.CARD : C.BG;
    row.forEach((v, j) => {
      const cell = sh.getRange(10 + i, j + 1).setValue(v).setBackground(bg).setFontColor(C.WHITE).setFontSize(9);
      if (j === 5) {
        const sc = { "未対応": C.RED, "対応中": C.YELLOW, "完了": C.GREEN, "却下": C.GRAY }[v] || C.WHITE;
        cell.setFontColor(sc).setFontWeight("bold");
      }
    });
    sh.setRowHeight(10 + i, 30);
  });

  // データ検証
  sh.getRange(10, 3, 100, 1).setDataValidation(
    SpreadsheetApp.newDataValidation().requireValueInList(["RPO", "HRsupport", "共通", "全体"]).build()
  );
  sh.getRange(10, 6, 100, 1).setDataValidation(
    SpreadsheetApp.newDataValidation().requireValueInList(["未対応", "対応中", "完了", "却下"]).build()
  );
  sh.getRange(10, 7, 100, 1).setDataValidation(
    SpreadsheetApp.newDataValidation().requireValueInList(["Critical", "High", "Medium", "Low"]).build()
  );

  // 条件付き書式
  const stRange = sh.getRange(10, 6, 100, 1);
  sh.setConditionalFormatRules([
    SpreadsheetApp.newConditionalFormatRule().whenTextEqualTo("未対応").setFontColor(C.RED).setBackground("#fce8e6").setRanges([stRange]).build(),
    SpreadsheetApp.newConditionalFormatRule().whenTextEqualTo("対応中").setFontColor(C.YELLOW).setRanges([stRange]).build(),
    SpreadsheetApp.newConditionalFormatRule().whenTextEqualTo("完了").setFontColor(C.GREEN).setRanges([stRange]).build(),
  ]);

  _applyDarkBg(sh, 500, 9);
  sh.setColumnWidths(1, 9, 130);
  sh.setColumnWidth(4, 280);
  sh.setFrozenRows(9);
}

// =================================================================
// Tab 6: 📝 Update_Log — 既存互換フォーマット維持
// =================================================================
function _migrateUpdateLog(ss) {
  const sh = ss.getSheetByName(TABS.LOG.name);
  // 既存データがあれば保持。タイトルとヘッダーのスタイルだけ更新する。
  const allData = sh.getDataRange().getValues();
  const hasData = allData.length >= 5;

  // Row1: タイトル（スタイル更新のみ）
  sh.getRange(1, 1, 1, 7).merge()
    .setValue("📝  UPDATE_LOG — AIシステム変更履歴（自動記録）")
    .setBackground(C.BG).setFontColor(C.WHITE).setFontWeight("bold").setFontSize(14)
    .setFontFamily("Roboto Mono");
  sh.setRowHeight(1, 40);

  // Row2: 統計バー（既存データがある場合は維持）
  if (!hasData) {
    sh.getRange(2, 1, 1, 7).setValues([[
      "📊 総更新回数: 0回", "最終更新: —", "", "", "", "", "",
    ]]);
  }
  sh.getRange(2, 1, 1, 7).setBackground(C.CARD).setFontColor(C.GRAY).setFontSize(9).setFontFamily("Roboto Mono");

  // Row3: 空行
  sh.getRange(3, 1, 1, 7).setBackground(C.BG);

  // Row4: ヘッダー（dashboard_logger.py互換）
  const logHeaders = ["#", "日時", "種別", "概要", "対象", "詳細", "Status"];
  logHeaders.forEach((h, i) => {
    sh.getRange(4, i + 1).setValue(h)
      .setBackground(C.HEADER).setFontColor(C.ACCENT).setFontWeight("bold").setFontSize(9)
      .setFontFamily("Roboto Mono");
  });
  sh.setRowHeight(4, 28);

  // Row5〜: 既存データがなければサンプル1行
  if (!hasData) {
    sh.getRange(5, 1, 1, 7).setValues([[
      "0", "2026-03-27 00:00", "🆕 新規作成", "Monitoring OS v2.0 セットアップ", "統合管理SS全タブ", "①HOME ②Dashboard ③Roadmap ④Project Board ⑤BU Backlog ⑥Update_Log ⑦Agent Registry ⑧Intel Log", "✅ 完了",
    ]]).setBackground(C.CARD).setFontColor(C.WHITE).setFontSize(9).setFontFamily("Roboto Mono");
  }

  _applyDarkBg(sh, 500, 7);
  sh.setColumnWidths(1, 7, 130);
  sh.setColumnWidth(1, 40);
  sh.setColumnWidth(2, 130);
  sh.setColumnWidth(6, 320);
  sh.setFrozenRows(4);

  _mc(sh, 1, 8, 1, 1, "⚠️ このタブへの手動書き込み不要。dashboard_logger.pyが自動記録します", {
    bg: "#fef9e7", fg: C.YELLOW, size: 8,
  });
}

// =================================================================
// Tab 7: 🤖 Agent Registry — エージェント台帳
// =================================================================
function _setupAgentRegistry(ss) {
  const sh = ss.getSheetByName(TABS.REGISTRY.name);
  sh.clear();

  _mc(sh, 1, 1, 1, 9, "🤖  AGENT REGISTRY — 稼働エージェント正規台帳", {
    bg: C.BG, fg: C.WHITE, bold: true, size: 16, h: 44,
  });
  _mc(sh, 2, 1, 1, 9, "エージェントの追加・変更時は AGENT_MANIFEST.json と合わせてここも更新", {
    bg: C.BG, fg: C.GRAY, size: 9,
  });

  const rHeaders = ["#", "名前", "canonical_id", "Status", "Domain", "担当者", "主要API", "主な責務", "module"];
  rHeaders.forEach((h, i) => {
    _cell(sh, 4, i + 1, h, { bg: C.HEADER, fg: C.ACCENT, bold: true, size: 9 });
  });

  const registry = [
    [1,  "面談後フルサポート",   "hr_orchestrator_post_interview", "稼働中", "RPO",       "佐藤", "Claude/SF/GSheets",     "tldv→SF登録→LINE下書き→レポート（並列）", "post_interview_full_support_agent"],
    [2,  "面接マスター",         "hr_processor_interview",         "稼働中", "RPO",       "佐藤", "Claude",                 "志望動機/ガクチカ/逆質問 全シーン対策",    "interview_master_agent"],
    [3,  "Salesforce",           "hr_executor_salesforce",         "稼働中", "共通",      "佐藤", "Claude/SF/GSheets",     "tldv議事録→SF PersonAccount登録",         "salesforce_agent"],
    [4,  "Notion",               "hr_parser_notion",               "稼働中", "共通",      "佐藤", "Claude/Notion",          "企業DB取得・企業紹介文生成",               "notion_agent"],
    [5,  "LINE",                 "hr_executor_line",               "稼働中", "HRsupport", "佐藤", "Claude/Notion",          "Lステップ文章生成（6シーン）",             "line_agent"],
    [6,  "Slack",                "hr_executor_slack",              "稼働中", "共通",      "佐藤", "SF/Slack",               "選考進捗をSlackスレッドへ自動共有",        "slack_agent"],
    [7,  "学生コーチング",       "hr_processor_coaching",          "稼働中", "RPO",       "佐藤", "Claude",                 "ES・面接対策/就活軸深掘り",               "coaching_agent"],
    [8,  "レポート",             "hr_processor_report",            "稼働中", "RPO",       "佐藤", "Claude",                 "学生所感レポート自動生成・保存",           "report_agent"],
    [9,  "tldv",                 "hr_watcher_tldv",                "稼働中", "共通",      "佐藤", "Claude/tldv",            "議事録取得・Claude自由質問分析",           "tldv_agent"],
    [10, "Google",               "hr_executor_google",             "稼働中", "共通",      "佐藤", "Claude/Gmail/GDrive",   "Gmail返信/Sheets読書/Docs操作",            "google_agent"],
    [11, "サポーター",           "hr_processor_supporter",         "稼働中", "共通",      "佐藤", "Claude",                 "全エージェント使い方ガイド",               "supporter_agent"],
    [12, "Orchestrator",         "hr_orchestrator_main",           "開発中", "全体",      "未定", "Claude",                 "タスク分解→実行→検証の自律分業",          "orchestrator（予定）"],
  ];

  registry.forEach((row, i) => {
    const bg = i % 2 === 0 ? C.CARD : C.BG;
    row.forEach((v, j) => {
      const cell = sh.getRange(5 + i, j + 1).setValue(v).setBackground(bg).setFontColor(C.WHITE).setFontSize(9).setFontFamily("Roboto Mono");
      if (j === 3) cell.setFontColor(v === "稼働中" ? C.GREEN : C.YELLOW).setFontWeight("bold");
    });
    sh.setRowHeight(5 + i, 30);
  });

  _applyDarkBg(sh, 20, 9);
  sh.setColumnWidths(1, 9, 130);
  sh.setColumnWidth(3, 200);
  sh.setColumnWidth(8, 260);
  sh.setColumnWidth(9, 200);
  sh.setFrozenRows(4);
}

// =================================================================
// Tab 8: 💡 Intel Log — エージェントパフォーマンスログ
// =================================================================
function _setupIntelLog(ss) {
  const sh = ss.getSheetByName(TABS.INTEL.name);
  sh.clear();

  _mc(sh, 1, 1, 1, 10, "💡  INTEL LOG — エージェント成功/失敗ログ（外販実績アセット）", {
    bg: C.BG, fg: C.WHITE, bold: true, size: 14, h: 40,
  });
  _mc(sh, 2, 1, 1, 10, "ここに蓄積されたデータが「魔法の証拠」になる。詳細に記録してください", {
    bg: C.BG, fg: C.GRAY, size: 9,
  });

  const iHeaders = ["実行日時", "Agent名", "BU", "担当者", "削減時間(h)", "結果", "タスク概要", "入力サマリ", "出力サマリ", "学習メモ"];
  iHeaders.forEach((h, i) => {
    _cell(sh, 4, i + 1, h, { bg: C.HEADER, fg: C.ACCENT, bold: true, size: 9 });
  });

  const logs = [
    ["2026-03-27 09:00", "面談後フルサポート", "RPO",       "佐藤", 2.5, "SUCCESS", "山田太郎 面談後処理",         "tldv URL",        "SF登録+LINE下書き+レポート完了", "並列実行で3タスクを同時処理"],
    ["2026-03-27 10:15", "Notion/LINE",        "RPO",       "佐藤", 0.5, "SUCCESS", "企業紹介文5社分 LINE送付用",  "企業名5社",       "紹介文5件生成",                  "1社平均6秒"],
    ["2026-03-26 14:30", "Slack Agent",        "共通",      "佐藤", 0.3, "SUCCESS", "選考進捗 週次Slack共有",      "SF進捗データ",    "Slackスレッド投稿完了",          ""],
    ["2026-03-26 11:00", "Report Agent",       "RPO",       "佐藤", 1.5, "SUCCESS", "学生所感レポート3件",          "面談メモ3件",     "レポート3件生成・保存",          "従来45分→3分"],
    ["2026-03-25 16:00", "Notion Agent",       "HRsupport", "佐藤", 0.0, "ERROR",   "企業DB取得",                  "DB ID",           "",                               "API Timeout。リトライ実装要"],
  ];
  logs.forEach((row, i) => {
    const bg = i % 2 === 0 ? C.CARD : C.BG;
    row.forEach((v, j) => {
      const cell = sh.getRange(5 + i, j + 1).setValue(v).setBackground(bg).setFontColor(C.WHITE).setFontSize(9).setFontFamily("Roboto Mono");
      if (j === 5) cell.setFontColor(v === "SUCCESS" ? C.GREEN : C.RED).setFontWeight("bold");
    });
    sh.setRowHeight(5 + i, 28);
  });

  _applyDarkBg(sh, 1000, 10);
  sh.setColumnWidths(1, 10, 130);
  sh.setColumnWidth(1, 130);
  sh.setColumnWidth(7, 200);
  sh.setColumnWidth(9, 200);
  sh.setFrozenRows(4);

  // データ検証: 結果列
  sh.getRange(5, 6, 995, 1).setDataValidation(
    SpreadsheetApp.newDataValidation().requireValueInList(["SUCCESS", "ERROR", "WARNING", "SKIP"]).build()
  );
}

// =================================================================
// UTILITIES
// =================================================================
function _ensureTabs(ss) {
  Object.values(TABS).forEach(({ name, color }) => {
    let sh = ss.getSheetByName(name);
    if (!sh) sh = ss.insertSheet(name);
    sh.setTabColor(color);
  });
}

function _reorderTabs(ss) {
  const order = Object.values(TABS).map((t) => t.name);
  order.forEach((name, i) => {
    const sh = ss.getSheetByName(name);
    if (sh) { ss.setActiveSheet(sh); ss.moveActiveSheet(i + 1); }
  });
}

function _mc(sh, row, col, numRows, numCols, value, opts = {}) {
  const range = sh.getRange(row, col, numRows, numCols).merge();
  range.setValue(value);
  if (opts.bg)     range.setBackground(opts.bg);
  if (opts.fg)     range.setFontColor(opts.fg);
  if (opts.bold)   range.setFontWeight("bold");
  if (opts.size)   range.setFontSize(opts.size);
  if (opts.align)  range.setHorizontalAlignment(opts.align);
  if (opts.vAlign) range.setVerticalAlignment(opts.vAlign);
  range.setFontFamily("Roboto Mono").setVerticalAlignment(opts.vAlign || "middle");
  if (opts.h) sh.setRowHeight(row, opts.h);
  return range;
}

function _cell(sh, row, col, value, opts = {}) {
  const range = sh.getRange(row, col).setValue(value);
  if (opts.bg)     range.setBackground(opts.bg);
  if (opts.fg)     range.setFontColor(opts.fg);
  if (opts.bold)   range.setFontWeight("bold");
  if (opts.size)   range.setFontSize(opts.size);
  if (opts.align)  range.setHorizontalAlignment(opts.align);
  range.setFontFamily("Roboto Mono").setVerticalAlignment("middle");
  return range;
}

function _applyDarkBg(sh, numRows, numCols) {
  sh.getRange(1, 1, numRows, numCols).setBackground(C.BG);
  sh.setColumnWidth(numCols + 1, 30);
}

// =================================================================
// TRIGGER: 毎時ダッシュボード最終更新時刻を更新
// =================================================================
function setupHourlyRefresh() {
  // 既存トリガー削除
  ScriptApp.getProjectTriggers().forEach((t) => {
    if (t.getHandlerFunction() === "refreshTimestamp") ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger("refreshTimestamp").timeBased().everyHours(1).create();
}

function refreshTimestamp() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sh = ss.getSheetByName(TABS.HOME.name);
  sh.getRange(2, 9).setValue("最終更新: " + new Date().toLocaleString("ja-JP"))
    .setBackground(C.BG).setFontColor(C.GRAY).setFontSize(8);
}
