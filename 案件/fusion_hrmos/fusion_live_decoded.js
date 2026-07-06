// ============================================================
// HRMOS 歩留まり分析 GAS v2
// スプレッドシート: 1zNv4az6PLaoO2ltdKudvZW3SM7XFzkkrD8E50vhMULU
//
// 機能:
//   - raw_data タブ（HRMOSエクスポート）から直近6ヶ月の歩留まりを集計
//   - 期間: 実行日の5ヶ月前の月初〜実行日（例: 5/26実行 → 2025/12/01〜2026/05/26）
//   - 選考フロー: カジュアル面談 → 1次 → 2次 → 最終 → 会食 → 内定 → 承諾
//   - A〜I列: カテゴリ別歩留まり（既存）
//   - K列以降: 媒体別 / エージェント×カテゴリ別
//   - 業務委託（求人ID 99始まり or 求人名に「業務委託」を含む）は除外
// ============================================================

const RAW_SHEET    = "raw_data";
const OUTPUT_SHEET = "歩留まり分析";

// 選考フロー（HRMOSのN次ステップを順にマッピング）
//   1次ステップ実施日 = カジュアル面談実施
//   2次ステップ実施日 = 1次面接実施
//   3次ステップ実施日 = 2次面接実施
//   4次ステップ実施日 = 最終面接実施
//   5次ステップ実施日 = 会食実施
const STEP_LABELS = ["カジュアル面談", "1次", "2次", "最終", "会食"];
const MAX_STEPS = STEP_LABELS.length;

// 分析対象カテゴリ（求人IDで紐付け。複数IDは配列で）
const POSITION_CATEGORIES = [
  { key: "営業ダイレクト",                  jobIds: ["122301_bp_drmgr"] },
  { key: "ブランド(Brand) メンバー",        jobIds: ["122302_bp_br"] },
  { key: "ブランド(Alliance) メンバー",     jobIds: ["122304_bp_al"] },
  { key: "ブランド マネージャー",           jobIds: ["122303_bp_almgr"] },
  { key: "ダイレクトクリエイティブプランナー", jobIds: ["122305_dc_pl"] },
  { key: "キャスティングD",                 jobIds: ["122310_pd_cas"] },
  { key: "経営企画",                        jobIds: ["122313_co_cp"] },
  { key: "メディアコンサルタント メンバー",  jobIds: ["122308_mc"] },
  { key: "メディアコンサルタント マネージャー", jobIds: ["122307_mc_mgr"] },
];

const COLOR = {
  bgDark:   "#37474F",
  fgWhite:  "#FFFFFF",
  totalBg:  "#ECEFF1",
  bgRow:    "#FFFFFF",
  bgRowAlt: "#F5F5F5",
  good:     "#C8E6C9",
  warn:     "#FFF59D",
  bad:      "#FFCDD2",
};

// 出力レイアウト
const COL_A = 1;         // メインテーブル開始列
const COL_K = 11;        // 媒体別/エージェント別テーブル開始列
const STEP_COLS = MAX_STEPS + 2; // ステップ列 + 内定 + 承諾

// ─────────────────────────────────────────
// メニュー
// ─────────────────────────────────────────

function onOpen() {
  SpreadsheetApp.getUi().createMenu("歩留まり分析")
    .addItem("再集計（直近6ヶ月）", "rebuildFunnelAnalysis")
    .addItem("📄 Geminiレポート生成（Docs）", "generateGeminiReport")
    .addToUi();
}

// ─────────────────────────────────────────
// Gemini レポート生成（Google Docs に出力）
// ─────────────────────────────────────────

const GEMINI_MODEL = "gemini-2.5-flash";
const GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models";

function generateGeminiReport() {
  let ui = null;
  try { ui = SpreadsheetApp.getUi(); } catch (e) { /* editor context */ }
  const notify = (msg) => { if (ui) ui.alert(msg); else Logger.log(msg); };

  const apiKey = PropertiesService.getScriptProperties().getProperty("GEMINI_API_KEY");
  if (!apiKey) { notify("Gemini API キー未設定（スクリプトプロパティ GEMINI_API_KEY）"); return; }

  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(OUTPUT_SHEET);
  if (!sheet) { notify(`「${OUTPUT_SHEET}」タブなし。先に再集計を実行してください`); return; }

  const data = sheet.getDataRange().getValues();
  const tsv = data.map(r => r.map(c => (c == null) ? "" : String(c)).join("\t")).join("\n");
  const today = new Date();
  const periodStart = new Date(today.getFullYear(), today.getMonth() - 5, 1);

  // ─── プロンプト（過去レポートスタイル準拠・◆見出し記号・Topics Good/More 形式）───
  const systemInstruction =
`あなたは採用RPOコンサルタント。クライアントの月次レポートを過去のフォーマットに準拠して書く。

【絶対ルール】
- 文章は簡潔。曖昧表現禁止（「頑張ろう」「改善が必要」は禁止）。動詞で始める具体策で書く
- 見出しは \`◆\` 記号を使う（例: ◆応募サマリ ◆Topics ◆応募経路 ◆改善アクション）
- 数値は箇条書きで明確に。前月比・前期比などの相対値も併記
- Good/More の構造で「やったこと→結果」を明示。施策と成果がペアで紐づくよう書く
- 業務委託（求人ID 99始まり）は異常値として除外し、その旨を明示
- 表は markdown 形式 \`| ヘッダ | ヘッダ |\` で区切り行 \`|---|---|\` を必ず入れる
- 直近6ヶ月の集計データを「期の総括」として書く。月次レポートではなく半期レポート`;

  const userPrompt =
`■ 企業: 株式会社FUSION（広告・キャスティング業界）
■ 期間: ${formatDate(periodStart)} 〜 ${formatDate(today)}（直近6ヶ月）
■ フロー: カジュアル面談→1次→2次→最終→会食→内定→承諾

■ データ（TSV / 歩留まり分析タブ全内容）
\`\`\`
${tsv}
\`\`\`

■ 出力構成（順番厳守・黒字シンプル）

# ◆6ヶ月の半期サマリ
箇条書き4〜5行で要点。テンプレ:
- 応募総数: XX名　※業務委託YY名を除外
- 期間中の最終選考フェーズ進出: ZZ名
- 期間中の内定獲得: AA名
- 全体応募の最大ポジション: 「XX」（YY%）
- 内定率（エントリー比）: ZZ%

# ◆Topics

:::good:Good
やったこと→結果を3行（各1行）。例:
ワークポート集中投資で人事中途のカジュアル面談を5名獲得
:::end

:::more:More
課題3行。例:
ワークポート経由62名から内定0、解約検討要
事業サイド責任者クラスの応募が0名で停滞
1次→2次の歩留まりが大幅に低下
:::end

# ◆媒体別コメント
3〜5行。「効率の良い媒体」「死に体の媒体」を具体名で。投資シフトの方向性を1行で結論

# ◆エージェント別コメント
4〜6行。ワークポート62名→内定0、Digital Arrow 1名→内定1 のような対比を含め、各エージェントに対する継続/見直し/解約の判断を明示

# ◆ポジション別コメント
3〜5行。最大エントリーのポジションと内定獲得済みポジションを比較。歩留まりが弱いポジションを指摘

# ◆来期の改善アクション
具体施策を3〜5個、各2行:
- 施策: [動詞で始まる具体策]
- 期待効果: [数値や状態で示す]`;

  // ─── Gemini 呼び出し ───
  const endpoint = `${GEMINI_ENDPOINT}/${GEMINI_MODEL}:generateContent?key=${apiKey}`;
  const payload = {
    systemInstruction: { parts: [{ text: systemInstruction }] },
    contents: [{ role: "user", parts: [{ text: userPrompt }] }],
    tools: [{ googleSearch: {} }],
    generationConfig: { temperature: 0.35, maxOutputTokens: 8192 },
  };

  let resJson;
  try {
    const res = UrlFetchApp.fetch(endpoint, {
      method: "post", contentType: "application/json",
      payload: JSON.stringify(payload), muteHttpExceptions: true,
    });
    resJson = JSON.parse(res.getContentText());
  } catch (e) { notify(`Gemini呼び出しエラー: ${e.message}`); return; }
  if (resJson.error) { notify(`Geminiエラー: ${JSON.stringify(resJson.error)}`); return; }
  const candidate = resJson.candidates?.[0];
  if (!candidate) { notify(`空応答: ${JSON.stringify(resJson)}`); return; }
  const reportText = candidate.content?.parts?.map(p => p.text).filter(Boolean).join("\n") || "(出力なし)";

  Logger.log("[step] reportText length: " + reportText.length);

  // ─── KPI 集計 ───
  let kpis = { totalEntry: 0, casualReached: 0, offerCount: 0, offerRate: "0.0" };
  try { kpis = _computeOverallKPIs(sheet); Logger.log("[step] kpis: " + JSON.stringify(kpis)); }
  catch (e) { Logger.log("kpi error: " + e.message); }

  // ─── Doc 作成 ───
  const docName = `FUSION 採用半期レポート_${formatDate(today)}`;
  const doc = DocumentApp.create(docName);
  const body = doc.getBody();
  Logger.log("[step] doc created: " + doc.getUrl());
  try { body.setMarginTop(40).setMarginBottom(40).setMarginLeft(50).setMarginRight(50); } catch (e) { Logger.log("margin skip: " + e.message); }

  // タイトル
  try {
    body.appendParagraph(docName).setHeading(DocumentApp.ParagraphHeading.TITLE);
  } catch (e) { Logger.log("title error: " + e.message); body.appendParagraph(docName); }

  // サブタイトル
  try {
    const sub = body.appendParagraph(`対象期間: ${formatDate(periodStart)} 〜 ${formatDate(today)}（直近6ヶ月）`);
    sub.setItalic(true);
  } catch (e) { Logger.log("subtitle error: " + e.message); }

  // KPI ブロック
  try {
    body.appendParagraph(" ");
    _appendHeroBlock(body, [
      { value: kpis.totalEntry,      label: "総応募数" },
      { value: kpis.casualReached,   label: "カジュアル面談" },
      { value: kpis.offerCount,      label: "内定獲得" },
      { value: kpis.offerRate + "%", label: "内定率" },
    ]);
    body.appendParagraph(" ");
    Logger.log("[step] hero block done");
  } catch (e) { Logger.log("hero error: " + e.message + " stack: " + (e.stack||"").substring(0,200)); }

  // ─── Markdown 本文 ───
  try {
    _renderMarkdownToDoc(body, reportText);
    Logger.log("[step] markdown done");
  } catch (e) {
    Logger.log("markdown error: " + e.message + " stack: " + (e.stack || "").substring(0, 400));
    body.appendParagraph("[本文描画エラー: " + e.message + "]").editAsText().setForegroundColor("#c00");
    body.appendParagraph(reportText.substring(0, 5000));
  }

  // ★ 中間保存
  try { doc.saveAndClose(); Logger.log("[step] intermediate save done"); }
  catch (e) { Logger.log("intermediate save error: " + e.message); }

  // ─── doc を再オープンしてシート表＋チャートを追加 ───
  let doc2, body2;
  try {
    doc2 = DocumentApp.openById(doc.getId());
    body2 = doc2.getBody();
  } catch (e) { Logger.log("reopen error: " + e.message); }

  if (body2) {
    // === 媒体別セクション ===
    try {
      body2.appendParagraph(" ");
      body2.appendParagraph("◆ 媒体別 歩留まり").setHeading(DocumentApp.ParagraphHeading.HEADING1);
      _appendSheetSection(body2, sheet, "■ 媒体別 歩留まり（応募経路ベース）");
      const pieBlob = _buildChannelPieChartBlob(sheet);
      if (pieBlob) { body2.appendParagraph(" "); body2.appendImage(pieBlob).setWidth(520).setHeight(340); }
    } catch (e) { Logger.log("media section: " + e.message); }

    // === エージェント別セクション ===
    try {
      body2.appendParagraph(" ");
      body2.appendParagraph("◆ エージェント別 歩留まり").setHeading(DocumentApp.ParagraphHeading.HEADING1);
      _appendSheetSection(body2, sheet, "■ エージェント × カテゴリ別 歩留まり");
    } catch (e) { Logger.log("agent section: " + e.message); }

    // === ポジション別セクション ===
    try {
      body2.appendParagraph(" ");
      body2.appendParagraph("◆ ポジション別 歩留まり").setHeading(DocumentApp.ParagraphHeading.HEADING1);
      _appendSheetSection(body2, sheet, "■ 実績数");
      const barBlob = _buildPositionBarChartBlob(sheet);
      if (barBlob) { body2.appendParagraph(" "); body2.appendImage(barBlob).setWidth(520).setHeight(340); }
      const donutBlob = _buildPositionDonutChartBlob(sheet);
      if (donutBlob) { body2.appendParagraph(" "); body2.appendImage(donutBlob).setWidth(520).setHeight(340); }
    } catch (e) { Logger.log("position section: " + e.message); }

    // === 選考フローファネル ===
    try {
      body2.appendParagraph(" ");
      body2.appendParagraph("◆ 選考フロー全体推移").setHeading(DocumentApp.ParagraphHeading.HEADING1);
      const funnelBlob = _buildFunnelChartBlob(sheet);
      if (funnelBlob) body2.appendImage(funnelBlob).setWidth(520).setHeight(260);
    } catch (e) { Logger.log("funnel section: " + e.message); }
  }

  // ─── 引用元 ───
  const groundingMeta = candidate.groundingMetadata;
  if (body2 && groundingMeta?.groundingChunks?.length) {
    try {
      body2.appendHorizontalRule();
      body2.appendParagraph("引用元（業界ベンチマーク）").setHeading(DocumentApp.ParagraphHeading.HEADING2);
      groundingMeta.groundingChunks.forEach(chunk => {
        const web = chunk.web; if (!web) return;
        const item = body2.appendListItem(web.title || "(no title)");
        item.editAsText().appendText(`\n${web.uri || ""}`).setForegroundColor("#1A73E8");
      });
    } catch (e) { Logger.log("grounding error: " + e.message); }
  }
  if (body2) {
    try {
      body2.appendHorizontalRule();
      const footer = body2.appendParagraph(`Generated by Gemini ${GEMINI_MODEL}`);
      footer.setItalic(true);
    } catch (e) { Logger.log("footer error: " + e.message); }
  }

  // ★ 最終保存
  try {
    if (doc2) doc2.saveAndClose();
    Logger.log("[step] final saveAndClose done");
  } catch (e) { Logger.log("final save error: " + e.message); }

  const url = doc.getUrl();
  notify(`✅ レポート生成完了\n\n${url}`);
  Logger.log(`[GeminiReport] ${url}`);
}

// QuickChart.io でファネル形状の棒グラフを生成（合計行から直接読む）
function _buildFunnelChartBlob(sheet) {
  const values = sheet.getDataRange().getValues();
  // 合計（分析対象9カテゴリ計）行を探す
  let totalRow = null;
  for (let r = 0; r < values.length; r++) {
    const label = String(values[r][0] || "").trim();
    if (label.startsWith("合計") && label.includes("9カテゴリ")) { totalRow = values[r]; break; }
  }
  if (!totalRow) return null;
  // 列: B=エントリー, C=カジュアル面談, D=1次, E=2次, F=最終, G=会食, H=内定, I=承諾
  const stages = ["エントリー", "カジュアル面談", "1次", "2次", "最終", "会食", "内定", "承諾"];
  const counts = [];
  for (let i = 0; i < stages.length; i++) {
    const v = Number(totalRow[i + 1]);
    counts.push(isNaN(v) ? 0 : v);
  }
  if (counts.every(c => c === 0)) return null;
  const config = {
    type: "bar",
    data: {
      labels: stages,
      datasets: [{
        label: "人数",
        data: counts,
        backgroundColor: ["#1f77b4","#2ca085","#41a85f","#75c95a","#b1d850","#e6c130","#e85d75","#cc4477"],
      }],
    },
    options: {
      indexAxis: "y",
      plugins: {
        title: { display: true, text: "選考フロー人数推移（直近6ヶ月）", font: { size: 16 } },
        legend: { display: false },
        datalabels: { anchor: "end", align: "right", color: "#333", font: { weight: "bold" } },
      },
      scales: { x: { beginAtZero: true } },
    },
  };
  const url = "https://quickchart.io/chart?width=700&height=350&format=png&c=" + encodeURIComponent(JSON.stringify(config));
  const res = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
  if (res.getResponseCode() !== 200) return null;
  return res.getBlob().setName("funnel_chart.png");
}

// 応募経路 円グラフ（過去レポートスタイル: 色分け・ラベル付き）
function _buildChannelPieChartBlob(sheet) {
  const data = _extractKAreaTable(sheet, "■ 媒体別 歩留まり");
  if (!data || data.labels.length === 0) return null;
  const total = data.entries.reduce((a, b) => a + b, 0) || 1;
  const labelsWithCount = data.labels.map((l, i) => `${l}\n${data.entries[i]}名 (${(data.entries[i]/total*100).toFixed(1)}%)`);
  const config = {
    type: "pie",
    data: {
      labels: labelsWithCount,
      datasets: [{
        data: data.entries,
        backgroundColor: ["#E53935","#4285F4","#FFB300","#43A047","#F4511E","#8E24AA","#00ACC1","#FB8C00"],
      }],
    },
    options: {
      plugins: {
        title: { display: true, text: "応募経路まとめ", font: { size: 20, weight: "bold" }, align: "start" },
        legend: { position: "right", labels: { font: { size: 12 } } },
        datalabels: { color: "#fff", font: { weight: "bold", size: 13 }, formatter: (v) => v >= 3 ? v + "名" : "" },
      },
    },
  };
  return _fetchChart(config, 800, 500, "channel_pie.png");
}

// ポジション別 応募数 棒グラフ（青系・数値ラベル付き）
function _buildPositionBarChartBlob(sheet) {
  const data = _extractPositionData(sheet);
  if (!data || data.labels.length === 0) return null;
  // ソート: エントリー数の降順
  const idx = data.labels.map((_, i) => i).sort((a, b) => data.entries[b] - data.entries[a]);
  const labels = idx.map(i => data.labels[i]);
  const entries = idx.map(i => data.entries[i]);
  const total = entries.reduce((a, b) => a + b, 0);
  const config = {
    type: "bar",
    data: {
      labels: labels,
      datasets: [{
        label: "応募数",
        data: entries,
        backgroundColor: "#4285F4",
        borderRadius: 4,
      }],
    },
    options: {
      plugins: {
        title: { display: true, text: `応募総数 ${total}名　／　ポジション別`, font: { size: 20, weight: "bold" }, align: "start" },
        legend: { display: false },
        datalabels: { anchor: "end", align: "top", color: "#4285F4", font: { weight: "bold", size: 14 }, formatter: (v) => v + "名" },
      },
      scales: {
        y: { beginAtZero: true, title: { display: true, text: "応募数" } },
        x: { ticks: { font: { size: 11 } } },
      },
    },
  };
  return _fetchChart(config, 900, 500, "position_bar.png");
}

// ポジション別 応募数 ドーナツチャート
function _buildPositionDonutChartBlob(sheet) {
  const data = _extractPositionData(sheet);
  if (!data || data.labels.length === 0) return null;
  const idx = data.labels.map((_, i) => i).sort((a, b) => data.entries[b] - data.entries[a]);
  const labels = idx.map(i => data.labels[i]);
  const entries = idx.map(i => data.entries[i]);
  const total = entries.reduce((a, b) => a + b, 0) || 1;
  const labelsWithPct = labels.map((l, i) => `${l}　${(entries[i]/total*100).toFixed(1)}%`);
  const config = {
    type: "doughnut",
    data: {
      labels: labelsWithPct,
      datasets: [{
        data: entries,
        backgroundColor: ["#43A047","#FF6F00","#26A69A","#AB47BC","#FBC02D","#5C6BC0","#EC407A","#7E57C2","#26C6DA","#FF7043"],
      }],
    },
    options: {
      plugins: {
        title: { display: true, text: "ポジション別 応募数割合", font: { size: 20, weight: "bold" }, align: "start" },
        legend: { position: "right", labels: { font: { size: 11 } } },
      },
      cutout: "55%",
    },
  };
  return _fetchChart(config, 900, 500, "position_donut.png");
}

// データ抽出: ポジション別
function _extractPositionData(sheet) {
  const values = sheet.getDataRange().getValues();
  // A列ヘッダから「ポジション別」セクションを探す
  // フォールバック: 200_設定 のポジション定義 + raw_data からカウント
  const labels = [], entries = [];
  // 「合計」を含まない行で、A列にポジション名がある行を拾う（B列にエントリー数想定）
  for (let r = 1; r < values.length; r++) {
    const label = String(values[r][0] || "").trim();
    if (!label) continue;
    if (label.includes("合計") || label.includes("総計") || label === "ステップ") continue;
    // ポジション名は POSITION_CATEGORIES のキーと一致
    const matched = POSITION_CATEGORIES.find(p => label === p.key || label.includes(p.key));
    if (!matched) continue;
    const v = Number(values[r][1]);
    if (!isNaN(v) && v > 0) {
      labels.push(label.substring(0, 16));
      entries.push(v);
    }
  }
  return { labels, entries };
}

// KPI ヒーローブロック: スプシと同じ色 (ネイビー header)
function _appendHeroBlock(body, kpis) {
  const numbers = kpis.map(k => String(k.value));
  const labels = kpis.map(k => k.label);
  const table = body.appendTable([labels, numbers]);
  // ラベル行: ネイビー背景 + 白文字
  try {
    const lblRow = table.getRow(0);
    for (let c = 0; c < lblRow.getNumCells(); c++) {
      try {
        const cell = lblRow.getCell(c);
        cell.setBackgroundColor("#37474F");
        const para = cell.getChild(0).asParagraph();
        para.editAsText().setForegroundColor("#FFFFFF").setBold(true);
        para.setAlignment(DocumentApp.HorizontalAlignment.CENTER);
      } catch (e) { Logger.log("hero lbl cell " + c + ": " + e.message); }
    }
  } catch (e) {}
  // 数値行: 薄グレー背景 + 黒太字
  try {
    const numRow = table.getRow(1);
    for (let c = 0; c < numRow.getNumCells(); c++) {
      try {
        const cell = numRow.getCell(c);
        cell.setBackgroundColor("#ECEFF1");
        const para = cell.getChild(0).asParagraph();
        para.editAsText().setBold(true);
        para.setAlignment(DocumentApp.HorizontalAlignment.CENTER);
      } catch (e) { Logger.log("hero num cell " + c + ": " + e.message); }
    }
  } catch (e) {}
  return table;
}

// コールアウトボックス（Good=緑系 / More=黄系）— スプシの good/warn 色を流用
function _appendCalloutBox(body, type, title, lines) {
  const bg  = type === "good" ? "#C8E6C9" : type === "more" ? "#FFF59D" : "#ECEFF1";
  const text = `${title}\n` + lines.map(l => `・${l}`).join("\n");
  const table = body.appendTable([[text]]);
  const cell = table.getCell(0, 0);
  cell.setBackgroundColor(bg);
  const para = cell.getChild(0);
  if (para && para.editAsText) {
    const t = para.editAsText();
    const txt = t.getText();
    const nl = txt.indexOf("\n");
    if (nl > 0) {
      t.setBold(0, nl - 1, true);
    }
  }
  return table;
}

// シートの特定セクション（例: "■ 媒体別 歩留まり"）を見つけて、表として Doc に挿入
function _appendSheetSection(body, sheet, sectionLabel, opts) {
  opts = opts || {};
  const values = sheet.getDataRange().getValues();
  let startRow = -1, startCol = -1;
  // ラベルを含むセルを探す
  for (let r = 0; r < values.length; r++) {
    for (let c = 0; c < values[r].length; c++) {
      const cell = String(values[r][c] || "").trim();
      if (cell.includes(sectionLabel)) { startRow = r; startCol = c; break; }
    }
    if (startRow >= 0) break;
  }
  if (startRow < 0) return false;
  // ヘッダ行 = startRow + 1, データ行 = startRow + 2 〜 空行まで
  const headerRow = startRow + 1;
  const rows = [];
  // ヘッダ
  const header = [];
  let endCol = startCol;
  for (let c = startCol; c < values[headerRow].length; c++) {
    const v = String(values[headerRow][c] || "").trim();
    if (!v && c > startCol) break;
    header.push(v);
    endCol = c;
  }
  if (!header.length) return false;
  rows.push(header);
  // データ（長いラベルは短縮）
  for (let r = headerRow + 1; r < Math.min(values.length, headerRow + 50); r++) {
    const first = String(values[r][startCol] || "").trim();
    const second = String(values[r][startCol + 1] || "").trim();
    if (!first && !second) break;
    const dataRow = [];
    for (let c = startCol; c <= endCol; c++) {
      let v = String(values[r][c] || "");
      if (c <= startCol + 1) v = _shortenLabel(v);
      dataRow.push(v);
    }
    rows.push(dataRow);
  }
  _appendStyledTable(body, rows);
  return true;
}

// 長いカテゴリ名を短縮して表が改ページで分断されないようにする
function _shortenLabel(s) {
  return String(s)
    .replace(/合計（分析対象9カテゴリ計）/, "合計")
    .replace(/ブランド\(Brand\) メンバー/, "ブランド(B)M")
    .replace(/ブランド\(Alliance\) メンバー/, "ブランド(A)M")
    .replace(/ブランド マネージャー/, "ブランドMgr")
    .replace(/ダイレクトクリエイティブプランナー/, "DCプランナー")
    .replace(/メディアコンサルタント メンバー/, "メディアコンサM")
    .replace(/メディアコンサルタント マネージャー/, "メディアコンサMgr")
    .replace(/株式会社ワークポート/, "ワークポート")
    .replace(/株式会社インディードリクルートパートナーズ/, "インディード")
    .replace(/Ｈｙｐｅ Ａｇｅｎｃｙ株式会社/, "Hype Agency")
    .replace(/株式会社Ｄｉｇｉｔａｌ Ａｒｒｏｗ Ｐａｒｔｎｅｒｓ/, "Digital Arrow")
    .replace(/株式会社マスメディアン/, "マスメディアン")
    .replace(/ダイレクトソーシング/, "DR")
    .replace(/HRMOS求人ページ/, "HRMOS");
}

// KPI 集計: 「合計（分析対象9カテゴリ計）」行から直接読み取り
// 列構造: A=カテゴリ, B=エントリー, C=カジュアル面談, D=1次, E=2次, F=最終, G=会食, H=内定, I=承諾
function _computeOverallKPIs(sheet) {
  const values = sheet.getDataRange().getValues();
  for (let r = 0; r < values.length; r++) {
    const label = String(values[r][0] || "").trim();
    if (label.startsWith("合計") && label.includes("9カテゴリ")) {
      const entry  = Number(values[r][1]) || 0;
      const casual = Number(values[r][2]) || 0;
      const offer  = Number(values[r][7]) || 0;  // 内定列
      const rate   = entry > 0 ? ((offer / entry) * 100).toFixed(1) : "0.0";
      return { totalEntry: entry, casualReached: casual, offerCount: offer, offerRate: rate };
    }
  }
  return { totalEntry: 0, casualReached: 0, offerCount: 0, offerRate: "0.0" };
}

// 汎用 fetch helper
function _fetchChart(config, w, h, name) {
  const url = `https://quickchart.io/chart?width=${w}&height=${h}&format=png&c=` + encodeURIComponent(JSON.stringify(config));
  const res = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
  if (res.getResponseCode() !== 200) {
    Logger.log(`QuickChart error ${res.getResponseCode()}: ${res.getContentText().substring(0, 200)}`);
    return null;
  }
  return res.getBlob().setName(name);
}

// 歩留まり分析タブのK列以降から「媒体別」「エージェント別」の表を抽出
function _extractKAreaTable(sheet, sectionLabel) {
  const values = sheet.getDataRange().getValues();
  const cols = values[0]?.length || 0;
  // セクションのヘッダ行を探す（K列以降）
  let headerRow = -1, startCol = -1;
  for (let r = 0; r < values.length; r++) {
    for (let c = 10; c < cols; c++) {
      const cell = String(values[r][c] || "").trim();
      if (cell.includes(sectionLabel)) { headerRow = r; startCol = c; break; }
    }
    if (headerRow >= 0) break;
  }
  if (headerRow < 0) return null;
  // セクション内の行を読む（最大20行）。1列目=ラベル、2列目=エントリー、最終列付近=内定
  const labels = [], entries = [], offers = [];
  for (let r = headerRow + 2; r < Math.min(values.length, headerRow + 22); r++) {
    const label = String(values[r][startCol] || "").trim();
    if (!label || label.includes("合計") || label.includes("総計")) break;
    const ent = Number(values[r][startCol + 1]);
    // 内定列を末尾から探す（NaNでない数値）
    let off = 0;
    for (let c = startCol + 5; c >= startCol + 2; c--) {
      const v = Number(values[r][c]);
      if (!isNaN(v)) { off = v; break; }
    }
    if (isNaN(ent) || ent === 0) continue;
    labels.push(label.substring(0, 14));
    entries.push(ent);
    offers.push(off);
  }
  return { labels, entries, offers };
}

// 汎用バーチャート（エントリーvs内定の対比）
function _quickBarChart(opts) {
  const config = {
    type: "bar",
    data: {
      labels: opts.labels,
      datasets: [
        { label: "エントリー", data: opts.entries, backgroundColor: "#4285F4" },
        { label: "内定",       data: opts.offers,  backgroundColor: "#34A853" },
      ],
    },
    options: {
      plugins: {
        title: { display: true, text: opts.title, font: { size: 16 } },
        legend: { position: "top" },
        datalabels: { color: "#222", font: { weight: "bold", size: 11 } },
      },
      scales: { y: { beginAtZero: true } },
    },
  };
  const url = "https://quickchart.io/chart?width=700&height=400&format=png&c=" + encodeURIComponent(JSON.stringify(config));
  const res = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
  if (res.getResponseCode() !== 200) return null;
  return res.getBlob().setName(opts.name);
}

// Markdown を Docs に変換（表 `| ... |` 対応）
function _renderMarkdownToDoc(body, text) {
  const lines = text.split("\n");
  let inCodeBlock = false;
  let i = 0;
  while (i < lines.length) {
    const raw = lines[i];
    const line = raw.trim();
    if (line.startsWith("```")) { inCodeBlock = !inCodeBlock; i++; continue; }
    if (inCodeBlock) { i++; continue; }

    // コールアウトブロック: :::good:タイトル / :::more:タイトル / :::end
    const calloutMatch = line.match(/^:::(good|more|info):(.*)$/);
    if (calloutMatch) {
      const type = calloutMatch[1];
      const title = calloutMatch[2].trim();
      const calloutLines = [];
      i++;
      while (i < lines.length) {
        const l = lines[i].trim();
        if (l === ":::end") { i++; break; }
        if (l) calloutLines.push(_cleanMarkdownInline(l.replace(/^[-・*]\s*/, "")));
        i++;
      }
      _appendCalloutBox(body, type, title, calloutLines);
      continue;
    }

    // Markdown 表検出: `| col | col |` で始まり、次行が `|---|---|`
    if (line.startsWith("|") && line.endsWith("|") && i + 1 < lines.length && /^\|[\s\-:|]+\|$/.test(lines[i+1].trim())) {
      const tableRows = [];
      // ヘッダ行
      tableRows.push(_splitTableRow(line));
      i += 2; // 区切り行スキップ
      while (i < lines.length) {
        const l = lines[i].trim();
        if (!l.startsWith("|") || !l.endsWith("|")) break;
        tableRows.push(_splitTableRow(l));
        i++;
      }
      _appendStyledTable(body, tableRows);
      continue;
    }

    if (!line) { body.appendParagraph(""); i++; continue; }
    if (line.startsWith("### ")) {
      body.appendParagraph(line.substring(4)).setHeading(DocumentApp.ParagraphHeading.HEADING3);
    } else if (line.startsWith("## ")) {
      body.appendParagraph(line.substring(3)).setHeading(DocumentApp.ParagraphHeading.HEADING2);
    } else if (line.startsWith("# ")) {
      body.appendParagraph(line.substring(2)).setHeading(DocumentApp.ParagraphHeading.HEADING1);
    }
    else if (line.startsWith("- ") || line.startsWith("* ")) body.appendListItem(_cleanMarkdownInline(line.substring(2)));
    else if (/^\d+\.\s/.test(line)) body.appendListItem(_cleanMarkdownInline(line.replace(/^\d+\.\s/, ""))).setGlyphType(DocumentApp.GlyphType.NUMBER);
    else body.appendParagraph(_cleanMarkdownInline(line));
    i++;
  }
}

function _splitTableRow(line) {
  return line.replace(/^\||\|$/g, "").split("|").map(c => _cleanMarkdownInline(c.trim()));
}

function _appendStyledTable(body, rows) {
  if (!rows.length) return;
  const table = body.appendTable(rows);
  const numCols = rows[0].length;

  // 列幅設定: 1列目はラベル広め、それ以外は均等に狭く
  try {
    const usable = 480; // ポイント
    const firstColW = numCols >= 6 ? 90 : 120;
    const restW = Math.floor((usable - firstColW) / Math.max(1, numCols - 1));
    table.setColumnWidth(0, firstColW);
    for (let c = 1; c < numCols; c++) table.setColumnWidth(c, restW);
  } catch (e) {}

  // 全セルのスタイル: 小フォント・縦padding削減
  for (let r = 0; r < table.getNumRows(); r++) {
    try {
      const row = table.getRow(r);
      for (let c = 0; c < row.getNumCells(); c++) {
        const cell = row.getCell(c);
        try {
          cell.setPaddingTop(2).setPaddingBottom(2).setPaddingLeft(6).setPaddingRight(6);
        } catch (e) {}
        try {
          cell.editAsText().setFontSize(9);
        } catch (e) {}
      }
    } catch (e) {}
  }

  // ヘッダ行: ネイビー + 白文字
  try {
    const headerRow = table.getRow(0);
    for (let c = 0; c < headerRow.getNumCells(); c++) {
      const cell = headerRow.getCell(c);
      cell.setBackgroundColor("#37474F");
      const t = cell.editAsText();
      t.setForegroundColor("#FFFFFF").setBold(true);
    }
  } catch (e) {}

  // データ行: 交互背景 + 判定列ハイライト
  for (let r = 1; r < table.getNumRows(); r++) {
    try {
      const row = table.getRow(r);
      const bg = (r % 2 === 0) ? "#F5F5F5" : "#FFFFFF";
      for (let c = 0; c < row.getNumCells(); c++) {
        const cell = row.getCell(c);
        cell.setBackgroundColor(bg);
        const v = cell.getText().trim();
        if (v === "◎" || v === "継続") cell.setBackgroundColor("#C8E6C9");
        else if (v === "△" || v === "見直し") cell.setBackgroundColor("#FFF59D");
        else if (v === "×" || v === "解約") cell.setBackgroundColor("#FFCDD2");
      }
    } catch (e) {}
  }
}

function _cleanMarkdownInline(s) {
  return String(s)
    .replace(/\*\*(.+?)\*\*/g, "$1")
    .replace(/\*(.+?)\*/g, "$1")
    .replace(/`(.+?)`/g, "$1");
}

// ─────────────────────────────────────────
// メイン: 歩留まり分析タブを再生成
// ─────────────────────────────────────────

function rebuildFunnelAnalysis() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const raw = ss.getSheetByName(RAW_SHEET);
  if (!raw) throw new Error(`${RAW_SHEET} タブが見つかりません`);

  // 対象期間: 実行月から5ヶ月前の月初 〜 実行日
  const today = new Date();
  const periodStart = new Date(today.getFullYear(), today.getMonth() - 5, 1);
  const periodEnd = today;

  // データ読み込み
  const data = raw.getDataRange().getValues();
  if (data.length < 2) throw new Error("raw_dataにデータがありません");
  const header = data[0];
  const idx = {};
  header.forEach((h, i) => { idx[String(h).trim()] = i; });

  // ─── カテゴリ別統計を初期化 ───
  const stats = {};
  POSITION_CATEGORIES.forEach(p => { stats[p.key] = _initStat(); });
  stats["合計（分析対象9カテゴリ計）"] = _initStat();

  // ─── 媒体別 / エージェント×カテゴリ別 ───
  const channelStats = {};   // 応募経路 → stat
  const agentStats = {};     // エージェント名 → { _total: stat, [catKey]: stat }

  // レコード走査
  let totalExcluded = 0;
  let totalOutOfPeriod = 0;
  for (let r = 1; r < data.length; r++) {
    const row = data[r];
    const jobId = String(row[idx["求人ID"]] || "").trim();
    const jobName = String(row[idx["求人名"]] || "").trim();
    if (!jobId) continue;

    // 業務委託除外
    if (jobId.startsWith("99") || jobName.includes("業務委託")) {
      totalExcluded++;
      continue;
    }

    // 対象カテゴリか判定
    const cat = POSITION_CATEGORIES.find(p => p.jobIds.includes(jobId));
    if (!cat) continue;

    // 応募日が期間内か判定
    const appDate = parseHRMOSDate(row[idx["応募日"]]);
    if (!appDate) continue;
    if (appDate < periodStart || appDate > periodEnd) {
      totalOutOfPeriod++;
      continue;
    }

    // 集計実行
    _accumulate(stats[cat.key], row, idx);
    _accumulate(stats["合計（分析対象9カテゴリ計）"], row, idx);

    // 媒体別集計
    const channel = String(row[idx["応募経路"]] || "").trim() || "（未記入）";
    if (!channelStats[channel]) channelStats[channel] = _initStat();
    _accumulate(channelStats[channel], row, idx);

    // エージェント別集計（エージェント企業名が入っているもののみ）
    const agentName = String(row[idx["エージェント企業名"]] || "").trim();
    if (agentName) {
      if (!agentStats[agentName]) agentStats[agentName] = { _total: _initStat() };
      if (!agentStats[agentName][cat.key]) agentStats[agentName][cat.key] = _initStat();
      _accumulate(agentStats[agentName][cat.key], row, idx);
      _accumulate(agentStats[agentName]._total, row, idx);
    }
  }

  // 出力タブを取得/作成・クリア
  let sheet = ss.getSheetByName(OUTPUT_SHEET);
  if (!sheet) sheet = ss.insertSheet(OUTPUT_SHEET);
  else {
    sheet.clear();
    if (sheet.getMaxRows() > 0 && sheet.getMaxColumns() > 0) {
      sheet.getRange(1, 1, sheet.getMaxRows(), sheet.getMaxColumns()).breakApart();
    }
    sheet.setFrozenRows(0);
    sheet.setFrozenColumns(0);
  }
  sheet.setHiddenGridlines(true);

  // ===================================
  //   A列〜: カテゴリ別 歩留まり（メイン）
  // ===================================

  const baseHeaders = ["カテゴリ", "エントリー"].concat(STEP_LABELS).concat(["内定", "承諾"]);
  const totalCols = baseHeaders.length; // = 9

  let r = 1;

  // タイトル
  sheet.getRange(r, 1, 1, totalCols).merge()
    .setValue(`HRMOS 歩留まり分析　／　対象期間: ${formatDate(periodStart)} 〜 ${formatDate(periodEnd)}　／　生成: ${formatDatetime(new Date())}`)
    .setBackground(COLOR.bgDark).setFontColor(COLOR.fgWhite)
    .setFontWeight("bold").setFontSize(13)
    .setHorizontalAlignment("left").setVerticalAlignment("middle");
  sheet.setRowHeight(r, 38);
  r++;

  // 説明文
  sheet.getRange(r, 1, 1, totalCols).merge()
    .setValue(`業務委託除外: 求人IDが99始まり または 求人名に「業務委託」を含むレコード（除外 ${totalExcluded} 件）　／　期間外: ${totalOutOfPeriod} 件`)
    .setBackground(COLOR.bgRowAlt).setFontColor("#546E7A").setFontSize(10)
    .setHorizontalAlignment("left");
  r++;
  r++;

  const allRows = [{ key: "合計（分析対象9カテゴリ計）" }].concat(POSITION_CATEGORIES);

  // ─ テーブル1: 実績数 ─
  r = _renderTitle(sheet, r, COL_A, totalCols, "■ 実績数（カテゴリ × 選考ステップ）");
  const rowsActual = allRows.map(p => {
    const s = stats[p.key];
    return [p.key, s.entry].concat(s.steps).concat([s.offer, s.accept]);
  });
  r = _writeTable(sheet, r, COL_A, baseHeaders, rowsActual) + 2;

  // ─ テーブル2: 累積通過率 ─
  r = _renderTitle(sheet, r, COL_A, totalCols, "■ 累積通過率（エントリー基準・%）");
  const rowsCum = allRows.map(p => _cumRow(p.key, stats[p.key]));
  r = _writeTable(sheet, r, COL_A, baseHeaders, rowsCum, { colorize: true }) + 2;

  // ─ テーブル3: ステップ間通過率 ─
  r = _renderTitle(sheet, r, COL_A, totalCols, "■ ステップ間通過率（前ステップ基準・%）");
  const rowsStep = allRows.map(p => _stepRow(p.key, stats[p.key]));
  r = _writeTable(sheet, r, COL_A, baseHeaders, rowsStep, { colorize: true }) + 2;

  // ─ テーブル4: 必要エントリー数 ─
  r = _renderTitle(sheet, r, COL_A, totalCols, "■ 必要エントリー数（内定1名あたり）");
  const needHeaders = ["カテゴリ", "エントリー", "内定", "承諾", "内定率", "内定1名あたり", "承諾1名あたり"];
  const needRows = allRows.map(p => _needRow(p.key, stats[p.key]));
  r = _writeTable(sheet, r, COL_A, needHeaders, needRows) + 2;

  // ─ テーブル5: 離脱内訳 ─
  r = _renderTitle(sheet, r, COL_A, totalCols, "■ 離脱内訳（参考）");
  const declHeaders = ["カテゴリ", "エントリー", "辞退", "不合格", "辞退率", "不合格率"];
  const declRows = allRows.map(p => _declRow(p.key, stats[p.key]));
  r = _writeTable(sheet, r, COL_A, declHeaders, declRows) + 2;

  // ===================================
  //   K列〜: 媒体別・エージェント別
  // ===================================

  let kr = 1;

  // タイトル
  sheet.getRange(kr, COL_K, 1, totalCols).merge()
    .setValue("媒体別 / エージェント×カテゴリ別 歩留まり")
    .setBackground(COLOR.bgDark).setFontColor(COLOR.fgWhite)
    .setFontWeight("bold").setFontSize(13)
    .setHorizontalAlignment("left").setVerticalAlignment("middle");
  sheet.setRowHeight(kr, 38);
  kr++;
  kr++;
  kr++;

  // ─ 媒体別 ─
  kr = _renderTitle(sheet, kr, COL_K, totalCols, "■ 媒体別 歩留まり（応募経路ベース）");
  const channelKeys = Object.keys(channelStats).sort((a, b) => channelStats[b].entry - channelStats[a].entry);
  const channelHeaders = ["媒体", "エントリー"].concat(STEP_LABELS).concat(["内定", "承諾"]);
  const channelRows = channelKeys.map(ch => {
    const s = channelStats[ch];
    return [ch, s.entry].concat(s.steps).concat([s.offer, s.accept]);
  });
  kr = _writeTable(sheet, kr, COL_K, channelHeaders, channelRows) + 2;

  // ─ 媒体別 累積通過率 ─
  kr = _renderTitle(sheet, kr, COL_K, totalCols, "■ 媒体別 累積通過率（エントリー基準・%）");
  const channelCumRows = channelKeys.map(ch => _cumRow(ch, channelStats[ch]));
  kr = _writeTable(sheet, kr, COL_K, channelHeaders, channelCumRows, { colorize: true }) + 2;

  // ─ 媒体別 必要エントリー数 ─
  kr = _renderTitle(sheet, kr, COL_K, totalCols, "■ 媒体別 必要エントリー数（内定1名あたり）");
  const channelNeedRows = channelKeys.map(ch => _needRow(ch, channelStats[ch]));
  kr = _writeTable(sheet, kr, COL_K, needHeaders, channelNeedRows) + 2;

  // ─ エージェント × カテゴリ クロス ─
  const agentCrossCols = totalCols + 1; // エージェント名 + カテゴリ + ...
  kr = _renderTitle(sheet, kr, COL_K, agentCrossCols, "■ エージェント × カテゴリ別 歩留まり");
  const agentHeaders = ["エージェント", "カテゴリ", "エントリー"].concat(STEP_LABELS).concat(["内定", "承諾"]);
  const agentRows = [];
  const agentKeys = Object.keys(agentStats).sort((a, b) => agentStats[b]._total.entry - agentStats[a]._total.entry);
  agentKeys.forEach(agent => {
    const t = agentStats[agent]._total;
    // 合計行
    agentRows.push([agent, "(合計)", t.entry].concat(t.steps).concat([t.offer, t.accept]));
    // カテゴリ別
    POSITION_CATEGORIES.forEach(p => {
      const s = agentStats[agent][p.key];
      if (!s || s.entry === 0) return;
      agentRows.push(["", p.key, s.entry].concat(s.steps).concat([s.offer, s.accept]));
    });
  });
  kr = _writeTable(sheet, kr, COL_K, agentHeaders, agentRows, { groupRows: true }) + 2;

  // ─ エージェント別 累積通過率 ─
  kr = _renderTitle(sheet, kr, COL_K, agentCrossCols, "■ エージェント別 累積通過率（合計・%）");
  const agentCumHeaders = ["エージェント", "", "エントリー"].concat(STEP_LABELS).concat(["内定", "承諾"]);
  const agentCumRows = agentKeys.map(agent => {
    const s = agentStats[agent]._total;
    const base = s.entry || 0;
    return [agent, "", base ? "100%" : "-"]
      .concat(s.steps.map(v => _pct(v, base)))
      .concat([_pct(s.offer, base), _pct(s.accept, base)]);
  });
  kr = _writeTable(sheet, kr, COL_K, agentCumHeaders, agentCumRows, { colorize: true }) + 2;

  // 列幅
  sheet.setColumnWidth(1, 240);
  for (let c = 2; c <= totalCols; c++) sheet.setColumnWidth(c, 90);
  sheet.setColumnWidth(COL_K, 200);          // 媒体/エージェント
  sheet.setColumnWidth(COL_K + 1, 200);       // カテゴリ
  for (let c = COL_K + 2; c <= COL_K + agentCrossCols; c++) sheet.setColumnWidth(c, 90);

  // 固定行（タイトル全列マージのため列固定は不可）
  sheet.setFrozenRows(3);

  SpreadsheetApp.getUi().alert(`歩留まり分析を更新しました\n対象期間: ${formatDate(periodStart)} 〜 ${formatDate(periodEnd)}\n業務委託除外: ${totalExcluded} 件\n媒体数: ${channelKeys.length} / エージェント数: ${agentKeys.length}`);
}

// ─────────────────────────────────────────
// 集計ヘルパー
// ─────────────────────────────────────────

function _initStat() {
  return {
    entry: 0,
    steps: new Array(MAX_STEPS).fill(0),
    offer: 0,
    accept: 0,
    decline: 0,
    fail: 0,
  };
}

function _accumulate(stat, row, idx) {
  stat.entry++;
  for (let s = 1; s <= MAX_STEPS; s++) {
    if (row[idx[`${s}次ステップ実施日`]]) stat.steps[s - 1]++;
  }
  if (row[idx["内定日"]])             stat.offer++;
  if (row[idx["内定承諾日"]])         stat.accept++;
  if (row[idx["辞退日"]])             stat.decline++;
  if (row[idx["不合格・重複終了日"]]) stat.fail++;
}

function _cumRow(label, s) {
  const base = s.entry || 0;
  const row = [label, base ? "100%" : "-"];
  s.steps.forEach(v => row.push(_pct(v, base)));
  row.push(_pct(s.offer, base));
  row.push(_pct(s.accept, base));
  return row;
}

function _stepRow(label, s) {
  const row = [label, "-"];
  let prev = s.entry;
  for (let i = 0; i < MAX_STEPS; i++) {
    const curr = s.steps[i];
    row.push(_pct(curr, prev));
    prev = curr;
  }
  row.push(_pct(s.offer, prev));
  row.push(_pct(s.accept, s.offer));
  return row;
}

function _needRow(label, s) {
  const rate = s.entry ? s.offer / s.entry : null;
  const needOffer = s.offer ? Math.ceil(s.entry / s.offer) : "-";
  const needAccept = s.accept ? Math.ceil(s.entry / s.accept) : "-";
  return [
    label, s.entry, s.offer, s.accept,
    rate === null ? "-" : Math.round(rate * 1000) / 10 + "%",
    needOffer, needAccept,
  ];
}

function _declRow(label, s) {
  return [
    label, s.entry, s.decline, s.fail,
    _pct(s.decline, s.entry),
    _pct(s.fail, s.entry),
  ];
}

// ─────────────────────────────────────────
// ヘルパー
// ─────────────────────────────────────────

function parseHRMOSDate(v) {
  if (!v) return null;
  if (v instanceof Date) return v;
  const s = String(v).trim();
  const m = s.match(/(\d{4})\D+(\d{1,2})\D+(\d{1,2})/);
  if (!m) return null;
  return new Date(parseInt(m[1], 10), parseInt(m[2], 10) - 1, parseInt(m[3], 10));
}

function _pct(num, den) {
  if (!den || den <= 0) return "-";
  return Math.round((num / den) * 1000) / 10 + "%";
}

function _renderTitle(sheet, r, c, cols, text) {
  sheet.getRange(r, c, 1, cols).merge()
    .setValue(text)
    .setBackground(COLOR.totalBg).setFontWeight("bold").setFontSize(11)
    .setHorizontalAlignment("left")
    .setBorder(true, true, true, true, false, false, COLOR.bgDark, SpreadsheetApp.BorderStyle.SOLID);
  sheet.setRowHeight(r, 26);
  return r + 1;
}

function _writeTable(sheet, r, c, headers, rows, opts) {
  const cols = headers.length;
  sheet.getRange(r, c, 1, cols).setValues([headers]);
  _styleHeader(sheet, r, c, cols);
  r++;
  if (rows.length > 0) {
    sheet.getRange(r, c, rows.length, cols).setValues(rows);
    _styleData(sheet, r, c, rows.length, cols);
    // 合計行（最初の行が「合計」ラベルなら強調）
    const firstVal = String(rows[0][0] || "");
    if (firstVal.startsWith("合計") || firstVal.startsWith("Total")) {
      sheet.getRange(r, c, 1, cols).setBackground(COLOR.bgRowAlt).setFontWeight("bold");
    }
    if (opts && opts.colorize) _colorizePctCells(sheet, r, c, rows);
    if (opts && opts.groupRows) _styleGroupRows(sheet, r, c, rows, cols);
  }
  return r + rows.length;
}

function _styleHeader(sheet, r, c, cols) {
  sheet.getRange(r, c, 1, cols)
    .setBackground(COLOR.bgDark).setFontColor(COLOR.fgWhite)
    .setFontWeight("bold").setHorizontalAlignment("center")
    .setBorder(true, true, true, true, true, true, "#000000", SpreadsheetApp.BorderStyle.SOLID);
}

function _styleData(sheet, r, c, rows, cols) {
  sheet.getRange(r, c, rows, cols)
    .setHorizontalAlignment("center")
    .setBorder(true, true, true, true, true, true, "#CFD8DC", SpreadsheetApp.BorderStyle.SOLID);
  // 1列目は左寄せ
  sheet.getRange(r, c, rows, 1).setHorizontalAlignment("left");
}

function _colorizePctCells(sheet, startR, startC, rows) {
  const bgs = rows.map(row => row.map((v, i) => {
    if (i === 0) return null;
    if (typeof v !== "string" || !v.endsWith("%")) return null;
    const n = parseFloat(v);
    if (isNaN(n)) return null;
    if (n >= 50) return COLOR.good;
    if (n >= 20) return COLOR.warn;
    if (n > 0)   return COLOR.bad;
    return null;
  }));
  for (let i = 0; i < bgs.length; i++) {
    for (let j = 0; j < bgs[i].length; j++) {
      if (bgs[i][j]) sheet.getRange(startR + i, startC + j).setBackground(bgs[i][j]);
    }
  }
}

// エージェント別クロス表で、「(合計)」行を強調
function _styleGroupRows(sheet, r, c, rows, cols) {
  for (let i = 0; i < rows.length; i++) {
    if (String(rows[i][1] || "").includes("合計")) {
      sheet.getRange(r + i, c, 1, cols).setBackground(COLOR.bgRowAlt).setFontWeight("bold");
    }
  }
}

// 日付フォーマット
function formatDate(dt)     { return (dt instanceof Date && !isNaN(dt)) ? `${dt.getFullYear()}/${String(dt.getMonth()+1).padStart(2,"0")}/${String(dt.getDate()).padStart(2,"0")}` : ""; }
function formatDatetime(dt) { return (dt instanceof Date && !isNaN(dt)) ? `${formatDate(dt)} ${String(dt.getHours()).padStart(2,"0")}:${String(dt.getMinutes()).padStart(2,"0")}` : ""; }