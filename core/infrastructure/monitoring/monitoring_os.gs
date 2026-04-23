// =================================================================
// Monitoring OS — Google Apps Script
// AI帝国建国ロードマップ 管理基盤
// =================================================================

// ── 定数 ──────────────────────────────────────────────────────────
const SHEET_NAMES = {
  DASHBOARD: "Dashboard",
  ROADMAP: "Agent Roadmap",
  BACKLOG: "BU Backlog",
  INTEL_LOG: "Intelligence Log",
};

const AGENTS = [
  { id: 1,  name: "Career Advisor",            domain: "RPO",       status: "稼働中" },
  { id: 2,  name: "Interview Master",           domain: "RPO",       status: "稼働中" },
  { id: 3,  name: "Post Interview Support",     domain: "RPO",       status: "稼働中" },
  { id: 4,  name: "Notion Agent",               domain: "共通",      status: "稼働中" },
  { id: 5,  name: "Salesforce Agent",           domain: "共通",      status: "稼働中" },
  { id: 6,  name: "LINE Agent",                 domain: "HRsupport", status: "稼働中" },
  { id: 7,  name: "Slack Agent",                domain: "HRsupport", status: "稼働中" },
  { id: 8,  name: "Google Agent",               domain: "共通",      status: "稼働中" },
  { id: 9,  name: "Report Agent",               domain: "共通",      status: "稼働中" },
  { id: 10, name: "Coaching Agent",             domain: "HRsupport", status: "稼働中" },
  { id: 11, name: "TLDV Agent",                 domain: "RPO",       status: "稼働中" },
  { id: 12, name: "Orchestrator (予定)",         domain: "全体",      status: "開発中" },
];

const COLORS = {
  BG_DARK:     "#0d0d0d",
  BG_CARD:     "#1a1a1a",
  BG_HEADER:   "#111111",
  TEXT_WHITE:  "#ffffff",
  TEXT_GRAY:   "#888888",
  ACCENT:      "#e0e0e0",
  GREEN:       "#4caf50",
  YELLOW:      "#ffc107",
  RED:         "#f44336",
  BLUE:        "#2196f3",
  BORDER:      "#333333",
};

// =================================================================
// ENTRY POINT: スプレッドシート全体を初期化
// =================================================================
function initializeMonitoringOS() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  ss.setSpreadsheetTheme(null); // デフォルトテーマリセット

  _ensureSheets(ss);
  _setupDashboard(ss);
  _setupAgentRoadmap(ss);
  _setupBUBacklog(ss);
  _setupIntelligenceLog(ss);

  // シート順序を整理
  const order = Object.values(SHEET_NAMES);
  order.forEach((name, i) => {
    const sheet = ss.getSheetByName(name);
    ss.setActiveSheet(sheet);
    ss.moveActiveSheet(i + 1);
  });

  SpreadsheetApp.flush();
  Logger.log("Monitoring OS initialized.");
}

// =================================================================
// Tab 1: DASHBOARD
// =================================================================
function _setupDashboard(ss) {
  const sheet = ss.getSheetByName(SHEET_NAMES.DASHBOARD);
  sheet.clear();
  sheet.setTabColor(COLORS.ACCENT);

  // ── ヘッダー ─────────────────────────────────────────────────
  _setCell(sheet, 1, 1, "⬛  MONITORING OS — DASHBOARD", {
    bg: COLORS.BG_DARK, fg: COLORS.TEXT_WHITE, bold: true, fontSize: 16,
    mergeEnd: 8,
  });
  _setCell(sheet, 2, 1, "AI帝国建国ロードマップ / リアルタイム経営指標", {
    bg: COLORS.BG_DARK, fg: COLORS.TEXT_GRAY, fontSize: 10, mergeEnd: 8,
  });

  // ── KPIカード行 ──────────────────────────────────────────────
  const kpis = [
    { label: "累計削減時間 (h)",   formula: "=IFERROR(SUM('Intelligence Log'!D:D),0)" },
    { label: "月間ROI (%)",         formula: "=IFERROR(ROUND(SUM('Intelligence Log'!D:D)*5000/500000*100,1),0)" },
    { label: "稼働エージェント数",  formula: `=COUNTIF('Agent Roadmap'!C:C,"稼働中")` },
    { label: "未解決バックログ",    formula: `=COUNTIF('BU Backlog'!E:E,"未対応")` },
  ];

  _setCell(sheet, 4, 1, "KEY METRICS", {
    bg: COLORS.BG_DARK, fg: COLORS.TEXT_GRAY, bold: true, fontSize: 9, mergeEnd: 8,
  });

  kpis.forEach((kpi, i) => {
    const col = i * 2 + 1;
    _setCell(sheet, 5, col, kpi.label, {
      bg: COLORS.BG_CARD, fg: COLORS.TEXT_GRAY, fontSize: 9, mergeEnd: col + 1,
    });
    sheet.getRange(6, col, 1, 2).merge()
      .setValue(kpi.formula)
      .setBackground(COLORS.BG_CARD)
      .setFontColor(COLORS.TEXT_WHITE)
      .setFontSize(24)
      .setFontWeight("bold")
      .setHorizontalAlignment("center");
  });

  // ── エージェント稼働ステータス一覧 ───────────────────────────
  _setCell(sheet, 8, 1, "AGENT STATUS", {
    bg: COLORS.BG_DARK, fg: COLORS.TEXT_GRAY, bold: true, fontSize: 9, mergeEnd: 8,
  });

  const agentHeaders = ["#", "Agent Name", "Domain", "Status", "本日ログ数", "直近エラー"];
  agentHeaders.forEach((h, i) => {
    _setCell(sheet, 9, i + 1, h, {
      bg: COLORS.BG_HEADER, fg: COLORS.ACCENT, bold: true, fontSize: 9,
    });
  });

  AGENTS.forEach((a, i) => {
    const row = 10 + i;
    const rowBg = i % 2 === 0 ? COLORS.BG_CARD : COLORS.BG_DARK;
    [a.id, a.name, a.domain, a.status].forEach((v, j) => {
      _setCell(sheet, row, j + 1, v, { bg: rowBg, fg: COLORS.TEXT_WHITE, fontSize: 9 });
    });
    // ログ数（Intelligence LogからCOUNTIF）
    sheet.getRange(row, 5)
      .setFormula(`=COUNTIF('Intelligence Log'!B:B,"${a.name}")`)
      .setBackground(rowBg).setFontColor(COLORS.TEXT_WHITE).setFontSize(9);
    // 直近エラー（IFERROR + MAXIFS）
    sheet.getRange(row, 6)
      .setFormula(`=IFERROR(MAXIFS('Intelligence Log'!A:A,'Intelligence Log'!B:B,"${a.name}",'Intelligence Log'!F:F,"ERROR"),"—")`)
      .setBackground(rowBg).setFontColor(COLORS.TEXT_GRAY).setFontSize(9);
  });

  _applySheetStyle(sheet, 22, 8);
}

// =================================================================
// Tab 2: AGENT ROADMAP
// =================================================================
function _setupAgentRoadmap(ss) {
  const sheet = ss.getSheetByName(SHEET_NAMES.ROADMAP);
  sheet.clear();
  sheet.setTabColor("#555555");

  _setCell(sheet, 1, 1, "⬛  AGENT ROADMAP — ①〜⑫ 開発ステータス", {
    bg: COLORS.BG_DARK, fg: COLORS.TEXT_WHITE, bold: true, fontSize: 14, mergeEnd: 9,
  });

  const headers = ["#", "Agent Name", "Status", "Domain", "開発開始", "稼働開始", "担当", "優先度", "備考"];
  headers.forEach((h, i) => {
    _setCell(sheet, 3, i + 1, h, {
      bg: COLORS.BG_HEADER, fg: COLORS.ACCENT, bold: true, fontSize: 9,
    });
  });

  AGENTS.forEach((a, i) => {
    const row = 4 + i;
    const rowBg = i % 2 === 0 ? COLORS.BG_CARD : COLORS.BG_DARK;
    const statusColor = a.status === "稼働中" ? COLORS.GREEN
                      : a.status === "開発中"  ? COLORS.YELLOW
                      : COLORS.RED;
    [a.id, a.name, a.status, a.domain, "", "", "佐藤", "High", ""].forEach((v, j) => {
      const cell = sheet.getRange(row, j + 1);
      cell.setValue(v).setBackground(rowBg).setFontColor(COLORS.TEXT_WHITE).setFontSize(9);
      if (j === 2) cell.setFontColor(statusColor).setFontWeight("bold");
    });
  });

  // 条件付き書式: Status列
  const statusRange = sheet.getRange(4, 3, AGENTS.length, 1);
  const rules = sheet.getConditionalFormatRules();
  rules.push(
    SpreadsheetApp.newConditionalFormatRule()
      .whenTextEqualTo("稼働中").setFontColor(COLORS.GREEN).setRanges([statusRange]).build(),
    SpreadsheetApp.newConditionalFormatRule()
      .whenTextEqualTo("開発中").setFontColor(COLORS.YELLOW).setRanges([statusRange]).build(),
    SpreadsheetApp.newConditionalFormatRule()
      .whenTextEqualTo("停止中").setFontColor(COLORS.RED).setRanges([statusRange]).build(),
  );
  sheet.setConditionalFormatRules(rules);

  _applySheetStyle(sheet, 20, 9);
}

// =================================================================
// Tab 3: BU BACKLOG
// =================================================================
function _setupBUBacklog(ss) {
  const sheet = ss.getSheetByName(SHEET_NAMES.BACKLOG);
  sheet.clear();
  sheet.setTabColor("#444444");

  _setCell(sheet, 1, 1, "⬛  BU BACKLOG — 現場の悲鳴と解決優先度", {
    bg: COLORS.BG_DARK, fg: COLORS.TEXT_WHITE, bold: true, fontSize: 14, mergeEnd: 8,
  });

  // サマリーカード
  const summaries = [
    { label: "総課題数",   formula: `=COUNTA(A4:A1000)-1` },
    { label: "未対応",     formula: `=COUNTIF(E4:E1000,"未対応")` },
    { label: "対応中",     formula: `=COUNTIF(E4:E1000,"対応中")` },
    { label: "完了",       formula: `=COUNTIF(E4:E1000,"完了")` },
  ];
  summaries.forEach((s, i) => {
    _setCell(sheet, 2, i * 2 + 1, s.label, {
      bg: COLORS.BG_CARD, fg: COLORS.TEXT_GRAY, fontSize: 9, mergeEnd: i * 2 + 2,
    });
    sheet.getRange(3, i * 2 + 1, 1, 2).merge()
      .setFormula(s.formula)
      .setBackground(COLORS.BG_CARD)
      .setFontColor(COLORS.TEXT_WHITE)
      .setFontSize(18).setFontWeight("bold").setHorizontalAlignment("center");
  });

  const headers = ["起票日", "BU", "課題タイトル", "詳細（悲鳴）", "対応状況", "優先度", "担当エージェント", "解決予定日"];
  headers.forEach((h, i) => {
    _setCell(sheet, 5, i + 1, h, {
      bg: COLORS.BG_HEADER, fg: COLORS.ACCENT, bold: true, fontSize: 9,
    });
  });

  // サンプルデータ
  const samples = [
    ["2026-03-26", "RPO",       "面接後フォローのメール送付が遅延",       "候補者から「連絡が遅い」クレーム多発",          "未対応", "🔴 Critical", "Post Interview Support", "2026-03-28"],
    ["2026-03-26", "HRsupport", "LINE返信の品質がバラバラ",               "担当者によって返信内容・速度に差がある",         "対応中", "🟡 High",     "LINE Agent",             "2026-04-01"],
    ["2026-03-25", "RPO",       "面談ログのSF入力漏れ",                   "手入力が面倒で後回しになる",                     "未対応", "🟡 High",     "Salesforce Agent",       "2026-03-30"],
    ["2026-03-24", "共通",      "週次レポートの作成に3時間かかる",         "毎週月曜の朝が潰れる",                           "完了",   "🔵 Medium",   "Report Agent",           "2026-03-24"],
    ["2026-03-23", "HRsupport", "議事録のNotionへの転記が属人化している", "担当者が休むと議事録が消滅する",                 "対応中", "🟡 High",     "Notion Agent",           "2026-04-05"],
  ];
  samples.forEach((row, i) => {
    const rowBg = i % 2 === 0 ? COLORS.BG_CARD : COLORS.BG_DARK;
    row.forEach((val, j) => {
      _setCell(sheet, 6 + i, j + 1, val, { bg: rowBg, fg: COLORS.TEXT_WHITE, fontSize: 9 });
    });
  });

  _applySheetStyle(sheet, 100, 8);

  // データ検証: 対応状況列
  const statusValidation = SpreadsheetApp.newDataValidation()
    .requireValueInList(["未対応", "対応中", "完了", "却下"])
    .setAllowInvalid(false).build();
  sheet.getRange(6, 5, 95, 1).setDataValidation(statusValidation);
}

// =================================================================
// Tab 4: INTELLIGENCE LOG
// =================================================================
function _setupIntelligenceLog(ss) {
  const sheet = ss.getSheetByName(SHEET_NAMES.INTEL_LOG);
  sheet.clear();
  sheet.setTabColor("#333333");

  _setCell(sheet, 1, 1, "⬛  INTELLIGENCE LOG — エージェント成功/失敗ログ（外販アセット）", {
    bg: COLORS.BG_DARK, fg: COLORS.TEXT_WHITE, bold: true, fontSize: 14, mergeEnd: 9,
  });

  const headers = [
    "Timestamp", "Agent Name", "Domain", "削減時間(h)", "タスク概要",
    "結果", "入力サマリ", "出力サマリ", "エラー詳細", "学習メモ",
  ];
  headers.forEach((h, i) => {
    _setCell(sheet, 3, i + 1, h, {
      bg: COLORS.BG_HEADER, fg: COLORS.ACCENT, bold: true, fontSize: 9,
    });
  });

  // サンプルログ
  const logs = [
    ["2026-03-26 09:12", "Career Advisor",        "RPO",       1.5, "求人票作成 × 3件",          "SUCCESS", "JD要件3件",        "求人票3件生成",      "",                      "テンプレ改善余地あり"],
    ["2026-03-26 10:30", "Interview Master",       "RPO",       0.5, "面接評価シート自動入力",     "SUCCESS", "面接メモ音声",     "SF入力完了",         "",                      "精度95%以上"],
    ["2026-03-26 11:45", "LINE Agent",             "HRsupport", 0.3, "LINE返信 × 12通",           "SUCCESS", "受信メッセージ",   "返信送信完了",       "",                      "平均7分短縮"],
    ["2026-03-26 13:00", "Notion Agent",           "共通",      1.0, "議事録Notion登録",           "ERROR",   "議事録テキスト",   "",                   "APIタイムアウト60s",    "リトライ実装要"],
    ["2026-03-26 14:20", "Post Interview Support", "RPO",       0.8, "面後フォローメール × 5件",  "SUCCESS", "候補者情報5名",    "メール送信完了",     "",                      "開封率89%"],
    ["2026-03-26 15:10", "Report Agent",           "共通",      3.0, "週次レポート自動生成",       "SUCCESS", "各種KPIデータ",   "Googleドキュメント", "",                      "3h→15分に短縮"],
  ];
  logs.forEach((row, i) => {
    const rowBg = i % 2 === 0 ? COLORS.BG_CARD : COLORS.BG_DARK;
    row.forEach((val, j) => {
      const cell = sheet.getRange(4 + i, j + 1);
      cell.setValue(val).setBackground(rowBg).setFontColor(COLORS.TEXT_WHITE).setFontSize(9);
      if (j === 5) {
        cell.setFontColor(val === "SUCCESS" ? COLORS.GREEN : COLORS.RED).setFontWeight("bold");
      }
    });
  });

  _applySheetStyle(sheet, 1000, 10);
}

// =================================================================
// UTILITIES
// =================================================================
function _ensureSheets(ss) {
  Object.values(SHEET_NAMES).forEach((name) => {
    if (!ss.getSheetByName(name)) {
      ss.insertSheet(name);
    }
  });
  // 不要なデフォルトシートを削除
  const defaultSheet = ss.getSheetByName("シート1") || ss.getSheetByName("Sheet1");
  if (defaultSheet && ss.getSheets().length > Object.keys(SHEET_NAMES).length) {
    ss.deleteSheet(defaultSheet);
  }
}

function _setCell(sheet, row, col, value, opts = {}) {
  const range = opts.mergeEnd
    ? sheet.getRange(row, col, 1, opts.mergeEnd - col + 1).merge()
    : sheet.getRange(row, col);

  range.setValue(value);
  if (opts.bg)       range.setBackground(opts.bg);
  if (opts.fg)       range.setFontColor(opts.fg);
  if (opts.bold)     range.setFontWeight("bold");
  if (opts.fontSize) range.setFontSize(opts.fontSize);
  return range;
}

function _applySheetStyle(sheet, numRows, numCols) {
  sheet.setColumnWidths(1, numCols, 140);
  sheet.setColumnWidth(1, 40);
  sheet.getRange(1, 1, numRows, numCols)
    .setFontFamily("Roboto Mono")
    .setVerticalAlignment("middle");
  sheet.setFrozenRows(3);
  sheet.setRowHeight(1, 40);
  sheet.setRowHeight(2, 28);

  // 背景を全体にDARKで塗りつぶす
  sheet.getRange(1, 1, numRows, numCols).setBackground(COLORS.BG_DARK);
}

// =================================================================
// API: Intelligence Logへの書き込みエンドポイント（Python側から呼ぶ）
// =================================================================
function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);
    _appendIntelLog(data);
    return ContentService.createTextOutput(JSON.stringify({ status: "ok" }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ status: "error", message: err.message }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function _appendIntelLog(data) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(SHEET_NAMES.INTEL_LOG);
  const lastRow = Math.max(sheet.getLastRow(), 3);
  const i = lastRow - 3; // 行インデックス（背景交互用）

  const row = [
    data.timestamp || new Date().toISOString(),
    data.agent_name || "",
    data.domain     || "",
    data.hours_saved || 0,
    data.task_summary || "",
    data.result      || "SUCCESS",
    data.input_summary  || "",
    data.output_summary || "",
    data.error_detail   || "",
    data.learning_note  || "",
  ];

  const range = sheet.getRange(lastRow + 1, 1, 1, row.length);
  range.setValues([row]);
  range.setBackground(i % 2 === 0 ? COLORS.BG_CARD : COLORS.BG_DARK);
  range.setFontColor(COLORS.TEXT_WHITE).setFontSize(9).setFontFamily("Roboto Mono");

  // 結果列の色分け
  const resultCell = sheet.getRange(lastRow + 1, 6);
  resultCell.setFontColor(row[5] === "SUCCESS" ? COLORS.GREEN : COLORS.RED).setFontWeight("bold");
}

// =================================================================
// TRIGGER: 毎時ダッシュボード更新
// =================================================================
function setupHourlyTrigger() {
  ScriptApp.newTrigger("refreshDashboard")
    .timeBased().everyHours(1).create();
}

function refreshDashboard() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const dashboard = ss.getSheetByName(SHEET_NAMES.DASHBOARD);
  // 時刻スタンプ更新
  dashboard.getRange(2, 7).setValue("最終更新: " + new Date().toLocaleString("ja-JP"));
  SpreadsheetApp.flush();
}
