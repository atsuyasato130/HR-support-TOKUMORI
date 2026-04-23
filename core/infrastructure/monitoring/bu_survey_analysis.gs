// =================================================================
// BU Survey 自動集計・分析エンジン
// 「現場の理想と現実」を抉り出すアンケート分析ロジック
// =================================================================

// ── 設定 ────────────────────────────────────────────────────────
const SURVEY_CONFIG = {
  RESPONSE_SHEET: "survey_responses",  // フォーム回答シート名
  ANALYSIS_SHEET: "Survey Analysis",
  FORM_ID: "",  // Google Form IDを設定
};

// アンケート設問定義（型: scale=1-5点, text=自由記述, choice=選択）
const QUESTIONS = [
  { id: "Q1", text: "現在の業務で最も時間を奪われているタスクは？",      type: "text",   category: "pain_point" },
  { id: "Q2", text: "1日あたり何時間をルーチン作業に費やしていますか？", type: "scale",  category: "time_loss" },
  { id: "Q3", text: "AI自動化への期待度（1-5）",                          type: "scale",  category: "expectation" },
  { id: "Q4", text: "今すぐ自動化したいタスクTOP3",                       type: "text",   category: "automation_wish" },
  { id: "Q5", text: "AIへの不安・懸念事項",                               type: "text",   category: "concern" },
  { id: "Q6", text: "所属BU",                                             type: "choice", category: "meta" },
  { id: "Q7", text: "業務の属人化度（1-5）",                              type: "scale",  category: "risk" },
];

// =================================================================
// ENTRY POINT: 全分析を実行してAnalysisシートに出力
// =================================================================
function runSurveyAnalysis() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const responses = _loadResponses(ss);

  if (responses.length === 0) {
    Logger.log("回答データなし");
    return;
  }

  const analysisSheet = _getOrCreateSheet(ss, SURVEY_CONFIG.ANALYSIS_SHEET);
  analysisSheet.clear();

  let currentRow = 1;
  currentRow = _renderHeader(analysisSheet, responses, currentRow);
  currentRow = _renderKPISummary(analysisSheet, responses, currentRow);
  currentRow = _renderBUBreakdown(analysisSheet, responses, currentRow);
  currentRow = _renderPainPointClusters(analysisSheet, responses, currentRow);
  currentRow = _renderPriorityMatrix(analysisSheet, responses, currentRow);
  currentRow = _renderAutoWishList(analysisSheet, responses, currentRow);

  _applyAnalysisStyle(analysisSheet, currentRow);
  SpreadsheetApp.flush();
  Logger.log("Survey Analysis complete. Rows written: " + currentRow);
}

// =================================================================
// Section 1: ヘッダー
// =================================================================
function _renderHeader(sheet, responses, row) {
  _writeRow(sheet, row, ["⬛  BU SURVEY ANALYSIS — 現場の理想と現実"], {
    bg: "#0d0d0d", fg: "#ffffff", bold: true, fontSize: 16, mergeEnd: 6,
  });
  _writeRow(sheet, row + 1, [
    `分析日時: ${new Date().toLocaleString("ja-JP")}`,
    "", "", "",
    `回答数: ${responses.length}件`,
  ], { bg: "#0d0d0d", fg: "#888888", fontSize: 9 });
  return row + 3;
}

// =================================================================
// Section 2: KPIサマリー
// =================================================================
function _renderKPISummary(sheet, responses, row) {
  _writeRow(sheet, row, ["KPI SUMMARY"], { bg: "#111111", fg: "#888888", bold: true, fontSize: 9, mergeEnd: 6 });
  row++;

  const avgTimeLoss   = _avgScale(responses, "Q2");
  const avgExpectation = _avgScale(responses, "Q3");
  const avgRisk       = _avgScale(responses, "Q7");
  const totalTimeLoss  = avgTimeLoss * responses.length;  // 推計/日

  const kpis = [
    ["平均ルーチン業務時間/日", `${avgTimeLoss.toFixed(1)}h`],
    ["AI期待度平均",            `${avgExpectation.toFixed(1)} / 5`],
    ["属人化リスク平均",        `${avgRisk.toFixed(1)} / 5`],
    ["推計全体損失時間/日",     `${totalTimeLoss.toFixed(0)}h`],
    ["自動化ROI試算（月）",     `¥${Math.round(totalTimeLoss * 22 * 5000).toLocaleString()}`],
  ];

  kpis.forEach(([label, value]) => {
    sheet.getRange(row, 1).setValue(label).setBackground("#1a1a1a").setFontColor("#888888").setFontSize(9);
    sheet.getRange(row, 2).setValue(value).setBackground("#1a1a1a").setFontColor("#ffffff").setFontSize(14).setFontWeight("bold");
    row++;
  });

  return row + 2;
}

// =================================================================
// Section 3: BU別ブレイクダウン
// =================================================================
function _renderBUBreakdown(sheet, responses, row) {
  _writeRow(sheet, row, ["BU BREAKDOWN"], { bg: "#111111", fg: "#888888", bold: true, fontSize: 9, mergeEnd: 6 });
  row++;

  const headers = ["BU", "回答数", "平均損失h/日", "AI期待度", "属人化度", "緊急度スコア"];
  _writeHeaderRow(sheet, row, headers);
  row++;

  const buGroups = _groupByBU(responses);
  Object.entries(buGroups).forEach(([bu, items], i) => {
    const avgTime = _avgScale(items, "Q2");
    const avgExp  = _avgScale(items, "Q3");
    const avgRisk = _avgScale(items, "Q7");
    const urgency = ((avgTime / 5 * 0.4) + (avgRisk / 5 * 0.4) + ((5 - avgExp) / 5 * 0.2)) * 100;

    const rowBg = i % 2 === 0 ? "#1a1a1a" : "#0d0d0d";
    const urgencyColor = urgency > 60 ? "#f44336" : urgency > 40 ? "#ffc107" : "#4caf50";

    [bu, items.length, avgTime.toFixed(1), avgExp.toFixed(1), avgRisk.toFixed(1)].forEach((v, j) => {
      sheet.getRange(row, j + 1).setValue(v).setBackground(rowBg).setFontColor("#ffffff").setFontSize(9);
    });
    sheet.getRange(row, 6).setValue(Math.round(urgency)).setBackground(rowBg).setFontColor(urgencyColor).setFontWeight("bold").setFontSize(9);
    row++;
  });

  return row + 2;
}

// =================================================================
// Section 4: ペインポイント クラスタリング（キーワード頻度）
// =================================================================
function _renderPainPointClusters(sheet, responses, row) {
  _writeRow(sheet, row, ["PAIN POINT CLUSTERS — キーワード頻度分析"], { bg: "#111111", fg: "#888888", bold: true, fontSize: 9, mergeEnd: 6 });
  row++;

  const keywords = _extractKeywords(responses, "Q1");
  const top10 = keywords.slice(0, 10);

  _writeHeaderRow(sheet, row, ["キーワード", "出現回数", "割合(%)", "カテゴリ推定"]);
  row++;

  top10.forEach(([word, count], i) => {
    const rowBg = i % 2 === 0 ? "#1a1a1a" : "#0d0d0d";
    const pct = ((count / responses.length) * 100).toFixed(0);
    const category = _guessCategory(word);
    [word, count, pct + "%", category].forEach((v, j) => {
      sheet.getRange(row, j + 1).setValue(v).setBackground(rowBg).setFontColor("#ffffff").setFontSize(9);
    });
    row++;
  });

  return row + 2;
}

// =================================================================
// Section 5: 優先度マトリクス（インパクト × 実現容易性）
// =================================================================
function _renderPriorityMatrix(sheet, responses, row) {
  _writeRow(sheet, row, ["PRIORITY MATRIX — 自動化優先度スコア"], { bg: "#111111", fg: "#888888", bold: true, fontSize: 9, mergeEnd: 6 });
  row++;

  // 自動化したいタスクをQ4から抽出・スコアリング
  const wishKeywords = _extractKeywords(responses, "Q4");
  const top8 = wishKeywords.slice(0, 8);

  _writeHeaderRow(sheet, row, ["タスク", "要望数", "インパクト推定", "実現容易性", "優先スコア", "推奨エージェント"]);
  row++;

  top8.forEach(([task, count], i) => {
    const impact      = Math.min(5, Math.ceil(count / responses.length * 10));
    const feasibility = _estimateFeasibility(task);
    const score       = (impact * 0.6 + feasibility * 0.4) * 20;
    const agent       = _recommendAgent(task);
    const scoreColor  = score > 70 ? "#f44336" : score > 50 ? "#ffc107" : "#4caf50";
    const rowBg = i % 2 === 0 ? "#1a1a1a" : "#0d0d0d";

    [task, count, `★${impact}`, `★${feasibility}`, Math.round(score)].forEach((v, j) => {
      sheet.getRange(row, j + 1).setValue(v).setBackground(rowBg).setFontColor("#ffffff").setFontSize(9);
    });
    sheet.getRange(row, 5).setFontColor(scoreColor).setFontWeight("bold");
    sheet.getRange(row, 6).setValue(agent).setBackground(rowBg).setFontColor("#888888").setFontSize(9);
    row++;
  });

  return row + 2;
}

// =================================================================
// Section 6: 自動化ウィッシュリスト（そのままBacklogへ転記）
// =================================================================
function _renderAutoWishList(sheet, responses, row) {
  _writeRow(sheet, row, ["AUTO WISH LIST → BU Backlogへの自動転記候補"], { bg: "#111111", fg: "#888888", bold: true, fontSize: 9, mergeEnd: 6 });
  row++;

  _writeHeaderRow(sheet, row, ["原文（現場の声）", "BU", "推定削減h", "優先度", "推奨エージェント"]);
  row++;

  responses.slice(0, 20).forEach((r, i) => {
    const wish   = r["Q4"] || "";
    const bu     = r["Q6"] || "不明";
    const hours  = parseFloat(r["Q2"]) || 1;
    const prio   = hours >= 3 ? "🔴 Critical" : hours >= 2 ? "🟡 High" : "🔵 Medium";
    const agent  = _recommendAgent(wish);
    const rowBg  = i % 2 === 0 ? "#1a1a1a" : "#0d0d0d";

    [wish.substring(0, 60), bu, hours + "h", prio, agent].forEach((v, j) => {
      sheet.getRange(row, j + 1).setValue(v).setBackground(rowBg).setFontColor("#ffffff").setFontSize(9);
    });
    row++;
  });

  return row + 2;
}

// =================================================================
// HELPERS
// =================================================================
function _loadResponses(ss) {
  const sheet = ss.getSheetByName(SURVEY_CONFIG.RESPONSE_SHEET);
  if (!sheet) return _generateSampleData(); // シートがなければサンプルデータ
  const data = sheet.getDataRange().getValues();
  const headers = data[0];
  return data.slice(1).map((row) => {
    const obj = {};
    headers.forEach((h, i) => { obj[h] = row[i]; });
    return obj;
  });
}

function _generateSampleData() {
  // デモ用サンプルデータ（10件）
  return Array.from({ length: 10 }, (_, i) => ({
    Q1: ["メール返信", "議事録作成", "データ入力", "レポート作成", "面接調整"][i % 5],
    Q2: [2, 3, 1.5, 4, 2.5, 3, 2, 1, 3.5, 2][i],
    Q3: [4, 5, 3, 4, 5, 4, 3, 5, 4, 4][i],
    Q4: ["メール自動返信", "議事録自動化", "SF自動入力", "週次レポート", "面接日程調整"][i % 5],
    Q5: ["誤送信が怖い", "品質が心配", "なし", "使い方が不明", "なし"][i % 5],
    Q6: ["RPO", "HRsupport", "RPO", "HRsupport", "RPO", "HRsupport", "RPO", "HRsupport", "RPO", "HRsupport"][i],
    Q7: [3, 4, 2, 5, 3, 4, 3, 2, 4, 3][i],
  }));
}

function _avgScale(responses, questionId) {
  const vals = responses.map((r) => parseFloat(r[questionId])).filter((v) => !isNaN(v));
  return vals.length > 0 ? vals.reduce((a, b) => a + b, 0) / vals.length : 0;
}

function _groupByBU(responses) {
  return responses.reduce((acc, r) => {
    const bu = r["Q6"] || "不明";
    if (!acc[bu]) acc[bu] = [];
    acc[bu].push(r);
    return acc;
  }, {});
}

function _extractKeywords(responses, questionId) {
  const freq = {};
  responses.forEach((r) => {
    const text = (r[questionId] || "").replace(/[、。，．]/g, " ");
    text.split(/\s+/).forEach((word) => {
      if (word.length >= 3) freq[word] = (freq[word] || 0) + 1;
    });
  });
  return Object.entries(freq).sort((a, b) => b[1] - a[1]);
}

function _guessCategory(word) {
  const map = {
    "メール": "コミュニケーション", "返信": "コミュニケーション",
    "議事録": "ドキュメント", "レポート": "ドキュメント",
    "入力": "データ処理", "転記": "データ処理", "集計": "データ処理",
    "面接": "採用業務", "候補者": "採用業務", "調整": "採用業務",
  };
  for (const [key, cat] of Object.entries(map)) {
    if (word.includes(key)) return cat;
  }
  return "その他";
}

function _estimateFeasibility(task) {
  const highFeasibility = ["メール", "入力", "転記", "集計", "レポート"];
  const medFeasibility  = ["議事録", "調整", "確認", "通知"];
  if (highFeasibility.some((w) => task.includes(w))) return 5;
  if (medFeasibility.some((w) => task.includes(w))) return 3;
  return 2;
}

function _recommendAgent(task) {
  const map = {
    "メール": "LINE Agent / Gmail",
    "Slack": "Slack Agent",
    "議事録": "Notion Agent",
    "SF": "Salesforce Agent",
    "レポート": "Report Agent",
    "面接": "Interview Master Agent",
    "候補者": "Career Advisor",
    "コーチ": "Coaching Agent",
  };
  for (const [key, agent] of Object.entries(map)) {
    if (task.includes(key)) return agent;
  }
  return "汎用エージェント";
}

function _getOrCreateSheet(ss, name) {
  return ss.getSheetByName(name) || ss.insertSheet(name);
}

function _writeRow(sheet, row, values, opts = {}) {
  values.forEach((v, i) => {
    const cell = sheet.getRange(row, i + 1);
    cell.setValue(v).setBackground(opts.bg || "#0d0d0d").setFontColor(opts.fg || "#ffffff");
    if (opts.bold)     cell.setFontWeight("bold");
    if (opts.fontSize) cell.setFontSize(opts.fontSize);
  });
  if (opts.mergeEnd) sheet.getRange(row, 1, 1, opts.mergeEnd).merge();
}

function _writeHeaderRow(sheet, row, headers) {
  headers.forEach((h, i) => {
    sheet.getRange(row, i + 1).setValue(h)
      .setBackground("#111111").setFontColor("#e0e0e0")
      .setFontWeight("bold").setFontSize(9);
  });
}

function _applyAnalysisStyle(sheet, numRows) {
  sheet.setColumnWidths(1, 6, 160);
  sheet.getRange(1, 1, numRows, 6)
    .setFontFamily("Roboto Mono").setVerticalAlignment("middle");
}
