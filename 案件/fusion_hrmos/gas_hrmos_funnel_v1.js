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
  { key: "営業ダイレクト",                     jobIds: ["122301_bp_drmgr"] },
  { key: "ブランド(Brand) メンバー",           jobIds: ["122302_bp_br"] },
  { key: "ブランド(Alliance) メンバー",        jobIds: ["122304_bp_al"] },
  { key: "ブランド マネージャー",              jobIds: ["122303_bp_almgr"] },
  { key: "ダイレクトクリエイティブプランナー", jobIds: ["122305_dc_pl"] },
  { key: "キャスティングD",                    jobIds: ["122310_pd_cas"] },
  { key: "経営企画",                           jobIds: ["122313_co_cp"] },
  { key: "メディアコンサルタント メンバー",     jobIds: ["122308_mc"] },
  { key: "メディアコンサルタント マネージャー", jobIds: ["122307_mc_mgr", "0000005"] },
  { key: "プロデューサー",                     jobIds: ["122305_pd_p"] },
  { key: "エディター",                         jobIds: ["122306_dc_edit"] },
  { key: "メディアオペレーション",             jobIds: ["122309_mc_ope"] },
  { key: "リクルーター（新卒）",               jobIds: ["122311_co_nr"] },
  { key: "リクルーター（中途）",               jobIds: ["122312_co_ta"] },
  { key: "オープンポジション",                 jobIds: ["122314_op"] },
  { key: "BP局長候補",                         jobIds: ["0000206"] },
  { key: "セールス",                           jobIds: ["0000208"] },
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
  var ui = SpreadsheetApp.getUi();
  ui.createMenu("採用レポート更新")
    .addItem("ダッシュボードを更新", "buildDashboardV2")
    .addItem("月次レポートDoc（前月）", "generateMonthlyDocEditablePrevMonth")
    .addItem("月次レポートDoc（月を指定）", "generateMonthlyDocEditableForMonth")
    .addToUi();
}

// グローバル期間オーバーライド（月次レポート時に設定）
var _PERIOD_OVERRIDE = null;

// 月次レポート: 期間を月単位で指定して再集計＋レポート生成
function generateMonthlyReport() {
  const ui = SpreadsheetApp.getUi();
  const resp = ui.prompt(
    "月次レポート生成",
    "対象月を YYYY-MM 形式で入力してください\n（例: 2026-04）",
    ui.ButtonSet.OK_CANCEL
  );
  if (resp.getSelectedButton() !== ui.Button.OK) return;
  const text = resp.getResponseText().trim();
  const m = text.match(/^(\d{4})-(\d{1,2})$/);
  if (!m) { ui.alert("形式エラー: YYYY-MM で入力してください（例: 2026-04）"); return; }
  const year = parseInt(m[1]);
  const month = parseInt(m[2]);
  if (month < 1 || month > 12) { ui.alert("月が不正です"); return; }
  const start = new Date(year, month - 1, 1);
  const end = new Date(year, month, 0); // 月末
  const label = `${year}年${month}月`;
  _PERIOD_OVERRIDE = { start, end, label };
  try {
    rebuildFunnelAnalysis();
    generateGeminiReport();
  } finally {
    _PERIOD_OVERRIDE = null;
  }
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
  // 期間オーバーライド（月次レポート時）または直近6ヶ月
  const periodStart = (typeof _PERIOD_OVERRIDE !== "undefined" && _PERIOD_OVERRIDE)
    ? _PERIOD_OVERRIDE.start
    : new Date(today.getFullYear(), today.getMonth() - 5, 1);
  const periodEnd = (typeof _PERIOD_OVERRIDE !== "undefined" && _PERIOD_OVERRIDE)
    ? _PERIOD_OVERRIDE.end
    : today;
  const periodLabel = (typeof _PERIOD_OVERRIDE !== "undefined" && _PERIOD_OVERRIDE)
    ? _PERIOD_OVERRIDE.label
    : "直近6ヶ月";

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
■ 期間: ${formatDate(periodStart)} 〜 ${formatDate(periodEnd)}（${periodLabel}）
■ フロー: カジュアル面談→1次→2次→最終→会食→内定→承諾

■ データ（TSV / 歩留まり分析タブ全内容）
\`\`\`
${tsv}
\`\`\`

■ 出力構成（順番厳守・黒字シンプル）

# ◆${periodLabel}サマリ
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
  const docName = `FUSION 採用レポート（${periodLabel}）_${formatDate(today)}`;
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
    const sub = body.appendParagraph(`対象期間: ${formatDate(periodStart)} 〜 ${formatDate(periodEnd)}（${periodLabel}）`);
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

  // ★ tokumori.co.jp ドメイン編集権限を付与
  try {
    const file = DriveApp.getFileById(doc.getId());
    file.setSharing(DriveApp.Access.DOMAIN_WITH_LINK, DriveApp.Permission.EDIT);
    Logger.log("[step] domain sharing set to DOMAIN_WITH_LINK/EDIT");
  } catch (e) { Logger.log("share error: " + e.message); }

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
    const usable = 520; // ポイント
    const firstColW = numCols >= 8 ? 100 : (numCols >= 6 ? 110 : 130);
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
          cell.editAsText().setFontSize(10);
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

// 集計コア（純粋関数）: raw_data を指定期間で走査し、カテゴリ別/媒体別/エージェント別の
// stat を返す。歩留まり分析タブ・レポート出力タブの双方から呼ぶ（タブは書き換えない）。
// 戻り値: { stats, channelStats, agentStats, totalExcluded, totalOutOfPeriod, idx, header, data }
function computeFunnel_(periodStart, periodEnd) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const raw = ss.getSheetByName(RAW_SHEET);
  if (!raw) throw new Error(`${RAW_SHEET} タブが見つかりません`);

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

  // ─── 雇用区分別（社員 / 業務委託）＋ 業務委託の職種内訳 ───
  const koyouStats = { "正社員": _initStat(), "業務委託": _initStat() };
  const gyoStats = {};       // 業務委託の職種ラベル → stat

  // レコード走査
  let totalExcluded = 0;
  let totalOutOfPeriod = 0;
  for (let r = 1; r < data.length; r++) {
    const row = data[r];
    const jobId = String(row[idx["求人ID"]] || "").trim();
    const jobName = String(row[idx["求人名"]] || "").trim();
    if (!jobId) continue;

    // テスト求人は雇用区分いずれにも含めない
    if (jobId === "0000207" || jobName === "テスト") continue;

    // 業務委託（求人IDが99始まり or 求人名に「業務委託」を含む）
    if (jobId.startsWith("99") || jobName.includes("業務委託")) {
      totalExcluded++;   // 既存の「除外件数」表示は後方互換で維持
      // ただし雇用区分別として別途集計（期間フィルタは社員と同条件）
      const gAppDate = parseHRMOSDate(row[idx["応募日"]]);
      if (!gAppDate || gAppDate < periodStart || gAppDate > periodEnd) continue;
      _accumulate(koyouStats["業務委託"], row, idx);
      const gLabel = _gyoLabel_(jobName);
      if (!gyoStats[gLabel]) gyoStats[gLabel] = _initStat();
      _accumulate(gyoStats[gLabel], row, idx);
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
    _accumulate(koyouStats["正社員"], row, idx);   // 正社員区分

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

  return { stats, channelStats, agentStats, koyouStats, gyoStats, totalExcluded, totalOutOfPeriod, idx, header, data };
}

// 業務委託の求人名 → 職種ラベル（「｜業務委託」「（業務委託）」等の付記を除去）
function _gyoLabel_(jobName) {
  let s = String(jobName || "").trim();
  s = s.replace(/[｜\|]\s*業務委託.*$/, "").replace(/[（(]\s*業務委託\s*[）)]/, "").replace(/業務委託/, "").trim();
  return s || "業務委託（職種不明）";
}

function rebuildFunnelAnalysis() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const raw = ss.getSheetByName(RAW_SHEET);
  if (!raw) throw new Error(`${RAW_SHEET} タブが見つかりません`);

  // 対象期間: _PERIOD_OVERRIDE があれば月次、なければ直近6ヶ月
  const today = new Date();
  const periodStart = (typeof _PERIOD_OVERRIDE !== "undefined" && _PERIOD_OVERRIDE)
    ? _PERIOD_OVERRIDE.start
    : new Date(today.getFullYear(), today.getMonth() - 5, 1);
  const periodEnd = (typeof _PERIOD_OVERRIDE !== "undefined" && _PERIOD_OVERRIDE)
    ? _PERIOD_OVERRIDE.end
    : today;

  // 集計コア（computeFunnel_ に集約。レポート出力タブ等と共用）
  const F = computeFunnel_(periodStart, periodEnd);
  const stats = F.stats;
  const channelStats = F.channelStats;
  const agentStats = F.agentStats;
  const totalExcluded = F.totalExcluded;
  const totalOutOfPeriod = F.totalOutOfPeriod;

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


// ============================================================
// §  レポート出力タブ（月次=経営向け + 週次=担当者向け）
//    シート内完結の構造化レポート。歩留まり分析タブは書き換えない。
//    他クライアントシートへは冒頭定数(POSITION_CATEGORIES / STEP_LABELS / RAW_SHEET)
//    と REPORT_COMPANY の差し替えのみで移植可能（次元はハードコードせず動的描画）。
// ============================================================

const REPORT_SHEET   = "レポート出力";
const REPORT_COMPANY = "株式会社FUSION";
const STALL_DAYS     = 14;             // 要対応: 最終アクションからの停滞日数しきい値
const REPORT_COLS    = MAX_STEPS + 4;  // レイアウト幅(=9): カテゴリ+エントリー+steps+内定+承諾

// 表示用フロー段ラベル（エントリー → 各ステップ → 内定 → 承諾）
function _flowLabels_() {
  return ["エントリー"].concat(STEP_LABELS).concat(["内定", "承諾"]);
}
function _statCounts_(s) { return [s.entry].concat(s.steps).concat([s.offer, s.accept]); }

// 月の period オブジェクト
function _monthPeriod_(year, month) {
  return {
    start: new Date(year, month - 1, 1),
    end:   new Date(year, month, 0),
    label: `${year}年${month}月`,
    ym:    `${year}-${String(month).padStart(2, "0")}`,
  };
}
function _prevMonthPeriod_() {
  const n = new Date();
  const d = new Date(n.getFullYear(), n.getMonth() - 1, 1);
  return _monthPeriod_(d.getFullYear(), d.getMonth() + 1);
}
function _curMonthPeriod_() {
  const n = new Date();
  return _monthPeriod_(n.getFullYear(), n.getMonth() + 1);
}

// ── メイン: レポート出力タブを生成（月次 period 指定） ──
function buildReportTab_(period) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const asOf = new Date();

  // 月次集計（歩留まり分析と同じ computeFunnel_ を期間指定で／タブは書き換えない）
  const F = computeFunnel_(period.start, period.end);
  // 全レコードスキャン（週次・進行中・停滞用。期間非依存）
  const recs = _reportScanRecords_();

  let sheet = ss.getSheetByName(REPORT_SHEET);
  if (!sheet) sheet = ss.insertSheet(REPORT_SHEET);
  _reportCleanup_(sheet);             // クリーンアップ先行（罫線/塗り/結合リセット）
  sheet.setHiddenGridlines(true);

  let r = 1;
  r = _reportTitle_(sheet, r, asOf);
  r = _reportMonthlySection_(sheet, r, F, period, asOf);
  r += 1;
  r = _reportWeeklySection_(sheet, r, recs, asOf);

  // 列幅
  sheet.setColumnWidth(1, 220);
  sheet.setColumnWidth(2, 120);
  for (let c = 3; c <= REPORT_COLS; c++) sheet.setColumnWidth(c, 96);
  return sheet;
}

// 出力タブのクリーンアップ（背景白/基準フォント/全罫線NONE/結合解除）
function _reportCleanup_(sheet) {
  const maxR = sheet.getMaxRows(), maxC = sheet.getMaxColumns();
  if (maxR > 0 && maxC > 0) {
    const rng = sheet.getRange(1, 1, maxR, maxC);
    rng.breakApart();
    rng.clear();
    rng.setBackground("#FFFFFF").setFontColor("#000000").setFontSize(10).setFontWeight("normal");
    rng.setBorder(false, false, false, false, false, false);
  }
  sheet.setFrozenRows(0);
  sheet.setFrozenColumns(0);
}

// raw_data 全レコードを分析対象カテゴリで抽出（業務委託除外・期間非依存）
function _reportScanRecords_() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const raw = ss.getSheetByName(RAW_SHEET);
  if (!raw) throw new Error(`${RAW_SHEET} タブが見つかりません`);
  const data = raw.getDataRange().getValues();
  const idx = {};
  data[0].forEach((h, i) => { idx[String(h).trim()] = i; });
  const out = [];
  for (let r = 1; r < data.length; r++) {
    const row = data[r];
    const jobId = String(row[idx["求人ID"]] || "").trim();
    const jobName = String(row[idx["求人名"]] || "").trim();
    if (!jobId) continue;
    if (jobId.startsWith("99") || jobName.includes("業務委託")) continue;
    const cat = POSITION_CATEGORIES.find(p => p.jobIds.includes(jobId));
    if (!cat) continue;
    const stepDates = [];
    for (let s = 1; s <= MAX_STEPS; s++) stepDates.push(parseHRMOSDate(row[idx[`${s}次ステップ実施日`]]));
    out.push({
      cat: cat.key,
      channel: String(row[idx["応募経路"]] || "").trim() || "（未記入）",
      agent: String(row[idx["エージェント企業名"]] || "").trim(),
      name: String(row[idx["氏名"]] || "").trim(),
      position: String(row[idx["選考ポジション名"]] || row[idx["求人名"]] || "").trim(),
      appDate: parseHRMOSDate(row[idx["応募日"]]),
      stepDates: stepDates,
      offerDate: parseHRMOSDate(row[idx["内定日"]]),
      acceptDate: parseHRMOSDate(row[idx["内定承諾日"]]),
      joinDate: parseHRMOSDate(row[idx["入社日"]]),
      declineDate: parseHRMOSDate(row[idx["辞退日"]]),
      failDate: parseHRMOSDate(row[idx["不合格・重複終了日"]]),
    });
  }
  return out;
}

// 候補者の状態判定（日付駆動。ステータス文字列に依存しない）
function _isClosed_(x) { return !!(x.acceptDate || x.joinDate || x.declineDate || x.failDate); }
function _currentStage_(x) {
  if (x.offerDate) return "内定";
  for (let s = MAX_STEPS; s >= 1; s--) { if (x.stepDates[s - 1]) return STEP_LABELS[s - 1]; }
  return "エントリー";
}
function _lastActivity_(x) {
  let last = null;
  const cand = [x.appDate].concat(x.stepDates).concat([x.offerDate]);
  cand.forEach(d => { if (d && (!last || d > last)) last = d; });
  return last;
}

// ── タイトル ──
function _reportTitle_(sheet, r, asOf) {
  sheet.getRange(r, 1, 1, REPORT_COLS).merge()
    .setValue(`■ ${REPORT_COMPANY} 採用レポート　（基準日: ${formatDate(asOf)}　/　生成: ${formatDatetime(asOf)}）`)
    .setBackground(COLOR.bgDark).setFontColor(COLOR.fgWhite)
    .setFontWeight("bold").setFontSize(13).setVerticalAlignment("middle");
  sheet.setRowHeight(r, 38);
  return r + 2;
}

// ── 見出しバー / サブ見出し / KV表 / 注記 ──
function _bandTitle_(sheet, r, text) {
  sheet.getRange(r, 1, 1, REPORT_COLS).merge()
    .setValue(text).setBackground("#263238").setFontColor(COLOR.fgWhite)
    .setFontWeight("bold").setFontSize(12).setVerticalAlignment("middle");
  sheet.setRowHeight(r, 30);
  return r + 2;
}
function _reportSub_(sheet, r, text) {
  sheet.getRange(r, 1, 1, REPORT_COLS).merge()
    .setValue(text).setFontWeight("bold").setFontColor("#263238").setFontSize(11)
    .setBackground("#ECEFF1").setVerticalAlignment("middle");
  sheet.setRowHeight(r, 24);
  return r + 1;
}
function _writeKV_(sheet, r, rows) {
  const n = rows.length;
  sheet.getRange(r, 1, n, 4).setValues(rows).setVerticalAlignment("middle")
    .setBorder(true, true, true, true, true, true, "#B0BEC5", SpreadsheetApp.BorderStyle.SOLID);
  sheet.getRange(r, 1, n, 1).setFontWeight("bold").setBackground(COLOR.bgRowAlt);
  sheet.getRange(r, 3, n, 1).setFontWeight("bold").setBackground(COLOR.bgRowAlt);
  return r + n;
}
function _writeNote_(sheet, r, text) {
  const lines = String(text).split("\n");
  const n = Math.max(1, lines.length);
  for (let i = 0; i < n; i++) {
    sheet.getRange(r + i, 1, 1, REPORT_COLS).merge();
    sheet.getRange(r + i, 1).setValue(lines[i] || "").setWrap(true).setVerticalAlignment("top");
  }
  sheet.getRange(r, 1, n, REPORT_COLS)
    .setBorder(true, true, true, true, false, false, "#B0BEC5", SpreadsheetApp.BorderStyle.SOLID);
  return r + n;
}

// ── 月次セクション（経営向け） ──
function _reportMonthlySection_(sheet, r, F, period, asOf) {
  r = _bandTitle_(sheet, r, `■ 月次レポート（経営向け）　${period.label}`);
  const total = F.stats["合計（分析対象9カテゴリ計）"];

  // ▎当月サマリ
  r = _reportSub_(sheet, r, "▎当月サマリ");
  let topCat = "-", topN = -1;
  POSITION_CATEGORIES.forEach(p => { const s = F.stats[p.key]; if (s && s.entry > topN) { topN = s.entry; topCat = p.key; } });
  const offerRate = total.entry ? Math.round(total.offer / total.entry * 1000) / 10 + "%" : "-";
  r = _writeKV_(sheet, r, [
    ["応募総数", total.entry, "業務委託除外", F.totalExcluded + "件"],
    ["最終選考進出", total.steps[3], "会食進出", total.steps[4]],
    ["内定", total.offer, "承諾", total.accept],
    ["最大応募ポジション", `${topCat}（${topN < 0 ? 0 : topN}件）`, "内定率(エントリー比)", offerRate],
  ]);
  r += 1;

  // ▎ファネル歩留まり（全カテゴリ合計）
  r = _reportSub_(sheet, r, "▎ファネル歩留まり（全カテゴリ合計）");
  const flow = _flowLabels_();
  const counts = _statCounts_(total);
  const funRows = [];
  for (let i = 0; i < flow.length; i++) {
    const prevPct = i === 0 ? "—" : _pct(counts[i], counts[i - 1]);
    const cumPct  = _pct(counts[i], counts[0]);
    const drop    = i === 0 ? 0 : Math.max(0, counts[i - 1] - counts[i]);
    funRows.push([flow[i], counts[i], prevPct, cumPct, drop]);
  }
  r = _writeTable(sheet, r, 1, ["ステージ", "到達数", "前段通過率", "累積通過率", "離脱数"], funRows, { colorize: true });
  r += 1;

  // ▎カテゴリ別 実績
  r = _reportSub_(sheet, r, "▎カテゴリ別 実績");
  const catHeaders = ["カテゴリ", "エントリー"].concat(STEP_LABELS).concat(["内定", "承諾"]);
  const catRows = [["合計"].concat(_statCounts_(total))];
  POSITION_CATEGORIES.forEach(p => { const s = F.stats[p.key]; if (s) catRows.push([p.key].concat(_statCounts_(s))); });
  r = _writeTable(sheet, r, 1, catHeaders, catRows, {});
  r += 1;

  // ▎媒体別 CVR / 必要エントリー数
  r = _reportSub_(sheet, r, "▎媒体別 CVR / 必要エントリー数");
  const needHeaders = ["媒体", "エントリー", "内定", "承諾", "内定率", "内定1名/必要", "承諾1名/必要"];
  const chRows = Object.keys(F.channelStats)
    .sort((a, b) => F.channelStats[b].entry - F.channelStats[a].entry)
    .map(k => _needRow(k, F.channelStats[k]));
  r = _writeTable(sheet, r, 1, needHeaders, chRows.length ? chRows : [["（データなし）", "", "", "", "", "", ""]], {});
  r += 1;

  // ▎エージェント別 成果
  r = _reportSub_(sheet, r, "▎エージェント別 成果");
  const agHeaders = ["エージェント", "エントリー"].concat(STEP_LABELS).concat(["内定", "承諾"]);
  const agRows = Object.keys(F.agentStats)
    .sort((a, b) => F.agentStats[b]._total.entry - F.agentStats[a]._total.entry)
    .map(k => [k].concat(_statCounts_(F.agentStats[k]._total)));
  r = _writeTable(sheet, r, 1, agHeaders, agRows.length ? agRows : [["（エージェント経由なし）"].concat(new Array(agHeaders.length - 1).fill(""))], {});
  r += 1;

  // ▎所感（Gemini転記 → 失敗時ルールベース）
  r = _reportSub_(sheet, r, "▎所感");
  r = _writeNote_(sheet, r, _reportInsight_(F, period));
  r += 1;
  return r;
}

// ── 週次セクション（担当者向け） ──
function _reportWeeklySection_(sheet, r, recs, asOf) {
  r = _bandTitle_(sheet, r, `■ 週次レポート（担当者向け）　〜${formatDate(asOf)} 基準（直近7日）`);
  const from = new Date(asOf.getFullYear(), asOf.getMonth(), asOf.getDate() - 7);
  const inWin = (d) => d && d >= from && d <= asOf;

  // ▎今週の動き
  r = _reportSub_(sheet, r, "▎今週の動き（直近7日）");
  let newApp = 0, offerW = 0, acceptW = 0;
  const stepW = new Array(MAX_STEPS).fill(0);
  recs.forEach(x => {
    if (inWin(x.appDate)) newApp++;
    x.stepDates.forEach((d, i) => { if (inWin(d)) stepW[i]++; });
    if (inWin(x.offerDate)) offerW++;
    if (inWin(x.acceptDate)) acceptW++;
  });
  r = _writeTable(sheet, r, 1,
    ["新規応募"].concat(STEP_LABELS).concat(["内定", "承諾"]),
    [[newApp].concat(stepW).concat([offerW, acceptW])], {});
  r += 1;

  // ▎媒体・エージェント別 新規応募（直近7日）
  r = _reportSub_(sheet, r, "▎媒体・エージェント別 新規応募（直近7日）");
  const byCh = {}, byAg = {};
  recs.forEach(x => {
    if (inWin(x.appDate)) {
      byCh[x.channel] = (byCh[x.channel] || 0) + 1;
      if (x.agent) byAg[x.agent] = (byAg[x.agent] || 0) + 1;
    }
  });
  const chList = Object.keys(byCh).sort((a, b) => byCh[b] - byCh[a]).map(k => [k, byCh[k]]);
  const agList = Object.keys(byAg).sort((a, b) => byAg[b] - byAg[a]).map(k => [k, byAg[k]]);
  r = _writeTable(sheet, r, 1, ["媒体", "新規応募"], chList.length ? chList : [["（なし）", 0]], {});
  r += 1;
  r = _writeTable(sheet, r, 1, ["エージェント", "新規応募"], agList.length ? agList : [["（なし）", 0]], {});
  r += 1;

  // ▎選考中（進行中）の現況
  r = _reportSub_(sheet, r, "▎選考中（進行中）の現況");
  const flow = _flowLabels_().slice(0, -1); // エントリー..内定（承諾は確定扱い）
  const stageCount = {};
  flow.forEach(l => stageCount[l] = 0);
  const inProg = recs.filter(x => !_isClosed_(x));
  inProg.forEach(x => { const st = _currentStage_(x); stageCount[st] = (stageCount[st] || 0) + 1; });
  r = _writeTable(sheet, r, 1, ["ステージ", "進行中人数"], flow.map(l => [l, stageCount[l] || 0]), {});
  r += 1;

  // ▎要対応（停滞 N日以上）
  r = _reportSub_(sheet, r, `▎要対応（最終アクションから${STALL_DAYS}日以上停滞）`);
  const stalled = inProg.map(x => ({ x: x, last: _lastActivity_(x) }))
    .filter(o => o.last && (asOf - o.last) >= STALL_DAYS * 86400000)
    .sort((a, b) => a.last - b.last)
    .map(o => [formatDate(o.last), o.x.name || "(無名)", o.x.cat, _currentStage_(o.x), Math.floor((asOf - o.last) / 86400000) + "日"]);
  r = _writeTable(sheet, r, 1, ["最終アクション", "候補者", "カテゴリ", "現ステージ", "停滞"],
    stalled.length ? stalled : [["—", "", "", "", ""]], {});
  r += 1;
  return r;
}

// ── 所感: Gemini転記（失敗時はルールベース） ──
function _reportInsight_(F, period) {
  try {
    const t = _geminiInsightText_(F, period);
    if (t && t.trim()) return t.trim();
  } catch (e) {
    Logger.log("[insight] Gemini失敗→ルールベースに切替: " + e.message);
  }
  return _ruleInsight_(F);
}

function _geminiInsightText_(F, period) {
  const apiKey = PropertiesService.getScriptProperties().getProperty("GEMINI_API_KEY");
  if (!apiKey) throw new Error("GEMINI_API_KEY未設定");
  const total = F.stats["合計（分析対象9カテゴリ計）"];
  const catLines = POSITION_CATEGORIES.map(p => {
    const s = F.stats[p.key];
    return s ? `${p.key}: 応募${s.entry} 最終${s.steps[3]} 内定${s.offer} 承諾${s.accept}` : "";
  }).filter(Boolean);
  const chLines = Object.keys(F.channelStats).sort((a, b) => F.channelStats[b].entry - F.channelStats[a].entry).slice(0, 8)
    .map(k => { const s = F.channelStats[k]; return `${k}: 応募${s.entry} 内定${s.offer}`; });
  const agLines = Object.keys(F.agentStats).sort((a, b) => F.agentStats[b]._total.entry - F.agentStats[a]._total.entry).slice(0, 8)
    .map(k => { const s = F.agentStats[k]._total; return `${k}: 応募${s.entry} 内定${s.offer} 承諾${s.accept}`; });
  const sys = "あなたは採用RPOコンサルタント。与えた当月実績から経営向けの所感を簡潔に書く。曖昧表現禁止、動詞で始まる具体策。出力はプレーンテキストのみ。";
  const prompt =
`■ 企業: ${REPORT_COMPANY} ／ 対象: ${period.label}
■ フロー: エントリー→カジュアル面談→1次→2次→最終→会食→内定→承諾
■ 全体: 応募${total.entry} 最終${total.steps[3]} 内定${total.offer} 承諾${total.accept}（業務委託除外${F.totalExcluded}件）
■ カテゴリ別:
${catLines.join("\n")}
■ 媒体別:
${chLines.join("\n")}
■ エージェント別:
${agLines.join("\n")}

次の3見出しで各2〜3行、合計8行以内のプレーンテキストで出力（行頭記号は「・」のみ）:
【Good】やったこと→結果
【課題】具体的なボトルネック
【来月アクション】動詞で始まる具体策`;
  const endpoint = `${GEMINI_ENDPOINT}/${GEMINI_MODEL}:generateContent?key=${apiKey}`;
  const payload = {
    systemInstruction: { parts: [{ text: sys }] },
    contents: [{ role: "user", parts: [{ text: prompt }] }],
    generationConfig: { temperature: 0.3, maxOutputTokens: 1024 },
  };
  const resp = UrlFetchApp.fetch(endpoint, {
    method: "post", contentType: "application/json",
    payload: JSON.stringify(payload), muteHttpExceptions: true,
  });
  if (resp.getResponseCode() !== 200) throw new Error("Gemini HTTP " + resp.getResponseCode() + ": " + resp.getContentText().slice(0, 200));
  const json = JSON.parse(resp.getContentText());
  const cand = json && json.candidates && json.candidates[0];
  const text = (cand && cand.content && cand.content.parts) ? cand.content.parts.map(p => p.text || "").join("") : "";
  if (!text) throw new Error("Gemini空応答");
  return text;
}

// ルールベース所感（API不要・常に成功）
function _ruleInsight_(F) {
  const total = F.stats["合計（分析対象9カテゴリ計）"];
  const lines = [];
  let bestCh = null, bestChN = 0;
  Object.keys(F.channelStats).forEach(k => { if (F.channelStats[k].offer > bestChN) { bestChN = F.channelStats[k].offer; bestCh = k; } });
  if (bestCh && bestChN > 0) lines.push(`【Good】・${bestCh}が内定${bestChN}名を創出。当月の主力チャネル`);
  else lines.push("【Good】・当月の内定創出は限定的。母集団形成フェーズと位置づける");

  const counts = [total.entry].concat(total.steps).concat([total.offer]);
  const flow = ["エントリー"].concat(STEP_LABELS).concat(["内定"]);
  let worstPass = 2, worstIdx = -1;
  for (let i = 1; i < counts.length; i++) {
    if (counts[i - 1] > 0) {
      const pass = counts[i] / counts[i - 1];
      if (pass < worstPass) { worstPass = pass; worstIdx = i; }
    }
  }
  if (worstIdx > 0) lines.push(`【課題】・${flow[worstIdx - 1]}→${flow[worstIdx]}の通過率が最低（${Math.round(worstPass * 100)}%）。最大のボトルネック`);
  const offerRate = total.entry ? Math.round(total.offer / total.entry * 1000) / 10 : 0;
  lines.push(`【課題】・エントリー→内定の内定率${offerRate}%。${offerRate < 3 ? "母集団・歩留まり両面の改善が必要" : "歩留まりは一定水準"}`);

  if (bestCh && bestChN > 0) lines.push(`【来月アクション】・${bestCh}への投資を継続し応募数を積み増す`);
  if (worstIdx > 0) lines.push(`【来月アクション】・${flow[worstIdx - 1]}→${flow[worstIdx]}の選考設計を見直す（評価基準・面接官アサインの最適化）`);
  if (lines.filter(l => l.indexOf("【来月アクション】") === 0).length === 0) lines.push("【来月アクション】・母集団形成チャネルを2系統以上に増やす");
  return lines.join("\n");
}

// ── 公開エントリーポイント（メニュー / トリガー） ──
function generateReportTabPrevMonth() {
  const p = _prevMonthPeriod_();
  const sheet = buildReportTab_(p);
  _toastReport_(sheet, p.label);
}
function generateReportTabForMonth() {
  const ui = SpreadsheetApp.getUi();
  const resp = ui.prompt("レポート出力タブ 生成", "対象月を YYYY-MM 形式で入力（例: 2026-04）", ui.ButtonSet.OK_CANCEL);
  if (resp.getSelectedButton() !== ui.Button.OK) return;
  const m = resp.getResponseText().trim().match(/^(\d{4})-(\d{1,2})$/);
  if (!m) { ui.alert("形式エラー: YYYY-MM で入力してください（例: 2026-04）"); return; }
  const month = parseInt(m[2], 10);
  if (month < 1 || month > 12) { ui.alert("月が不正です"); return; }
  const p = _monthPeriod_(parseInt(m[1], 10), month);
  const sheet = buildReportTab_(p);
  _toastReport_(sheet, p.label);
}
// 2026-06-25: レポート出力タブは Python(build_hrmos_report.py / hrmos_automation) へ移行。
// 既存トリガーが発火してもレポート出力を上書きしないよう no-op 化（トリガー削除不要）。
function buildReportTabAuto()    { return; /* moved to Python (weekly/monthly run) */ }
function refreshWeeklyReportTab() { return; /* moved to Python (weekly_run.py / 水10:30) */ }

function _toastReport_(sheet, label) {
  try { sheet.activate(); SpreadsheetApp.getUi().alert(`レポート出力タブを生成しました（月次: ${label}）`); }
  catch (e) { Logger.log("レポート生成完了: " + label); }
}

function setReportMonthlyTrigger() {
  _deleteTriggersByFn_("buildReportTabAuto");
  ScriptApp.newTrigger("buildReportTabAuto").timeBased().onMonthDay(1).atHour(0).create();
  try { SpreadsheetApp.getUi().alert("月次トリガー設定: 毎月1日0時に前月分レポートを自動生成"); } catch (e) {}
}
function setReportWeeklyTrigger() {
  _deleteTriggersByFn_("refreshWeeklyReportTab");
  ScriptApp.newTrigger("refreshWeeklyReportTab").timeBased().onWeekDay(ScriptApp.WeekDay.MONDAY).atHour(9).create();
  try { SpreadsheetApp.getUi().alert("週次トリガー設定: 毎週月曜9時にレポート(週次)を自動更新"); } catch (e) {}
}
function _deleteTriggersByFn_(fnName) {
  ScriptApp.getProjectTriggers().forEach(t => { if (t.getHandlerFunction() === fnName) ScriptApp.deleteTrigger(t); });
}


// ============================================================
// §  月間レポートDoc（編集可能コメント＋QuickChartグラフ・Gemini非依存）
//    担当者がコメントを編集できる。毎月新規Docなので編集は永続。
// ============================================================

// QuickChart 画像取得（共通）
function _qcImg_(config, w, h, name) {
  w = w || 700; h = h || 360;
  const url = "https://quickchart.io/chart?width=" + w + "&height=" + h + "&format=png&v=4&c=" + encodeURIComponent(JSON.stringify(config));
  try {
    const res = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
    if (res.getResponseCode() !== 200) { Logger.log("QuickChart " + res.getResponseCode()); return null; }
    return res.getBlob().setName((name || "chart") + ".png");
  } catch (e) { Logger.log("QuickChart err: " + e.message); return null; }
}
// ── スマートDocデザイン（黒×朱で統一） ──
var DOC_INK = "#1A1A1A", DOC_ACCENT = "#AF322C", DOC_MUTED = "#9AA0A6", DOC_GRID = "#EEEEEE";
function _redShades_(n) {
  const base = ["#8F231E", "#AF322C", "#C24A40", "#D06E64", "#DD9189", "#E8B4AE", "#F1D5D1"];
  const out = []; for (let i = 0; i < n; i++) out.push(base[Math.min(i, base.length - 1)]); return out;
}
// 横棒ランキング（データラベル付き・罫線なし・角丸・朱）
function _qcBarH_(labels, values, title, opts) {
  opts = opts || {};
  const colors = opts.shade ? _redShades_(values.length) : DOC_ACCENT;
  return _qcImg_({
    type: "bar",
    data: { labels: labels, datasets: [{ data: values, backgroundColor: colors, borderRadius: 6, borderSkipped: false, barPercentage: 0.78 }] },
    options: {
      indexAxis: "y",
      plugins: {
        title: { display: true, text: title, color: DOC_INK, font: { size: 13, weight: "bold" }, align: "start", padding: { bottom: 10 } },
        legend: { display: false },
        datalabels: { anchor: "end", align: "right", color: DOC_INK, font: { weight: "bold", size: 11 }, formatter: function (v) { return v; } },
      },
      layout: { padding: { right: 30, left: 4 } },
      scales: { x: { display: false, grid: { display: false }, beginAtZero: true }, y: { grid: { display: false }, border: { display: false }, ticks: { color: DOC_INK, font: { size: 11 } } } },
    },
  }, opts.w || 700, opts.h || (64 + labels.length * 34), "barh");
}
// 折れ線（朱=主 / グレー=副・薄塗り・点付き・罫線最小）
function _qcLineSmart_(labels, series, title) {
  // 2系列までは朱+グレー、3系列以上はパレットで色分け（全フェーズ推移用）
  var PAL = [DOC_ACCENT, "#37474F", "#1E88E5", "#43A047", "#FB8C00", "#8E24AA", "#00897B"];
  var multi = series.length > 2;
  return _qcImg_({
    type: "line",
    data: { labels: labels, datasets: series.map(function (s, i) { var col = multi ? PAL[i % PAL.length] : (i === 0 ? DOC_ACCENT : DOC_MUTED); return { label: s.label, data: s.data, borderColor: col, backgroundColor: (!multi && i === 0) ? "rgba(175,50,44,0.08)" : "transparent", fill: !multi && i === 0, tension: 0.4, borderWidth: 2.5, pointRadius: multi ? 2 : 3, pointBackgroundColor: col }; }) },
    options: {
      plugins: {
        title: { display: true, text: title, color: DOC_INK, font: { size: 13, weight: "bold" }, align: "start", padding: { bottom: 10 } },
        legend: { position: "top", align: "end", labels: { color: DOC_INK, usePointStyle: true, boxWidth: 8, font: { size: 11 } } },
        datalabels: { display: false },
      },
      scales: { x: { grid: { display: false }, border: { display: false }, ticks: { color: DOC_MUTED, font: { size: 11 } } }, y: { beginAtZero: true, grid: { color: DOC_GRID }, border: { display: false }, ticks: { color: DOC_MUTED, font: { size: 11 } } } },
    },
  }, 700, 300, "line");
}
// 黒帯タイトル（白文字・控えめサイズ）＋サブ
function _docTitleBand_(body, title, sub) {
  const t = body.appendTable([[title]]);
  try {
    const cell = t.getCell(0, 0); cell.setBackgroundColor(DOC_INK); cell.setPaddingTop(8).setPaddingBottom(8).setPaddingLeft(12);
    const p = cell.getChild(0).asParagraph(); p.editAsText().setForegroundColor("#FFFFFF").setBold(true).setFontSize(16);
  } catch (e) {}
  if (sub) { const s = body.appendParagraph(sub); s.editAsText().setForegroundColor(DOC_MUTED).setItalic(true).setFontSize(9.5); }
  return t;
}
// 統一セクション見出し「▎ X」: ▎=朱 / 文字=ink太字・13pt（HEADING2でアウトライン保持）
function _docH_(body, text) {
  const p = body.appendParagraph("▎ " + text);
  p.setHeading(DocumentApp.ParagraphHeading.HEADING2);
  try { const tx = p.editAsText(); tx.setForegroundColor(DOC_INK).setBold(true).setFontSize(13); tx.setForegroundColor(0, 0, DOC_ACCENT); } catch (e) {}
  return p;
}

// 月次推移（raw_data 単一パスで月バケット）。全フェーズの月別到達数を集計。
//   各フェーズの基準日: 応募=応募日 / 各選考ステップ=該当ステップ実施日 / 内定=内定日 / 承諾=内定承諾日
//   戻り値: { labels, entries, offers(後方互換), series:[{label,data[]}] }（series=全フェーズ）
function _hrmosMonthlyTrend_(monthsBack) {
  monthsBack = monthsBack || 6;
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const raw = ss.getSheetByName(RAW_SHEET);
  const data = raw.getDataRange().getValues();
  const idx = {}; data[0].forEach((h, i) => { idx[String(h).trim()] = i; });
  const today = new Date();
  const months = [];
  for (let i = monthsBack - 1; i >= 0; i--) { const d = new Date(today.getFullYear(), today.getMonth() - i, 1); months.push({ ym: `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`, label: `${d.getMonth() + 1}月` }); }
  // 全フェーズ系列を初期化（応募 + 各選考ステップ + 内定 + 承諾）
  const flow = ["応募"].concat(STEP_LABELS).concat(["内定", "承諾"]);
  const buckets = flow.map(() => { const o = {}; months.forEach(m => { o[m.ym] = 0; }); return o; });
  const ymOf = (v) => { const dt = parseHRMOSDate(v); return dt ? `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, "0")}` : null; };
  const bump = (seriesIdx, v) => { const ym = ymOf(v); if (ym && buckets[seriesIdx][ym] !== undefined) buckets[seriesIdx][ym]++; };
  for (let r = 1; r < data.length; r++) {
    const row = data[r];
    const jobId = String(row[idx["求人ID"]] || "").trim(); const jobName = String(row[idx["求人名"]] || "").trim();
    if (!jobId || jobId.startsWith("99") || jobName.includes("業務委託")) continue;
    if (!POSITION_CATEGORIES.find(p => p.jobIds.includes(jobId))) continue;
    bump(0, row[idx["応募日"]]);                                    // 応募
    for (let s = 1; s <= STEP_LABELS.length; s++) {                 // 各選考ステップ実施日（_accumulate と同じ列基準）
      const col = idx[`${s}次ステップ実施日`];
      if (col !== undefined) bump(s, row[col]);
    }
    bump(1 + STEP_LABELS.length, row[idx["内定日"]]);                // 内定
    bump(2 + STEP_LABELS.length, row[idx["内定承諾日"]]);            // 承諾
  }
  const series = flow.map((label, i) => ({ label, data: months.map(m => buckets[i][m.ym]) }));
  return {
    labels: months.map(m => m.label),
    entries: series[0].data,
    offers: series[1 + STEP_LABELS.length].data,
    series,
  };
}

// Doc 表（ヘッダ=ink・10pt）
function _hrmosDocTable_(body, headers, rows) {
  const t = body.appendTable([headers].concat(rows.length ? rows : [headers.map(() => "-")]));
  try {
    const hr = t.getRow(0);
    for (let c = 0; c < hr.getNumCells(); c++) {
      const cell = hr.getCell(c); cell.setBackgroundColor(DOC_INK); cell.setPaddingTop(2).setPaddingBottom(2).setPaddingLeft(5).setPaddingRight(5);
      const p = cell.getChild(0).asParagraph(); p.editAsText().setForegroundColor("#FFFFFF").setBold(true).setFontSize(10); p.setAlignment(DocumentApp.HorizontalAlignment.CENTER);
    }
    for (let r = 1; r < t.getNumRows(); r++) { for (let c = 0; c < t.getRow(r).getNumCells(); c++) { try { const cc = t.getRow(r).getCell(c); cc.setPaddingTop(2).setPaddingBottom(2).setPaddingLeft(5).setPaddingRight(5); cc.getChild(0).asParagraph().editAsText().setFontSize(10); } catch (e) {} } }
  } catch (e) {}
  return t;
}

// 最大の歩留まり低下段を返す（ハイライト用）
function _hrmosFunnelHighlight_(total) {
  const labels = ["エントリー", "カジュアル面談", "1次", "2次", "最終", "会食", "内定", "承諾"];
  const counts = [total.entry].concat(total.steps).concat([total.offer, total.accept]);
  let worst = 2, idx = -1;
  for (let i = 1; i < counts.length; i++) { if (counts[i - 1] >= 3) { const pass = counts[i] / counts[i - 1]; if (pass < worst) { worst = pass; idx = i; } } }
  if (idx < 0) return "";
  return `${labels[idx - 1]}→${labels[idx]}（通過率 ${Math.round(worst * 100)}%）`;
}

// メイン: 編集可能・グラフ入り月間Docを生成し URL を返す
function buildMonthlyDocEditable_(period) {
  const F = computeFunnel_(period.start, period.end);
  const total = F.stats["合計（分析対象9カテゴリ計）"];  // 社員のみ（＝職種別と整合）
  // 雇用区分別 & 合計（社員＋業務委託）
  const emp = F.koyouStats["正社員"], gyo = F.koyouStats["業務委託"];
  const _addStat = (a, b) => ({ entry: a.entry + b.entry, steps: a.steps.map((v, i) => v + b.steps[i]), offer: a.offer + b.offer, accept: a.accept + b.accept, decline: 0, fail: 0 });
  const comb = _addStat(emp, gyo);   // 全体（見出し・ファネルはこれを主役に）
  const pd = new Date(period.start.getFullYear(), period.start.getMonth() - 1, 1);
  const pe = new Date(period.start.getFullYear(), period.start.getMonth(), 0);
  let prevTotal = null, prevComb = null;
  try { const pf = computeFunnel_(pd, pe); prevTotal = pf.stats["合計（分析対象9カテゴリ計）"]; prevComb = _addStat(pf.koyouStats["正社員"], pf.koyouStats["業務委託"]); } catch (e) {}
  const diff = (c, p) => (p == null) ? "" : (c - p === 0 ? " (±0)" : (c - p > 0 ? ` (+${c - p})` : ` (${c - p})`));

  const now = new Date();
  const docName = `株式会社FUSION 月次採用レポート(中途)_${period.label}_${formatDate(now)}`;
  const doc = DocumentApp.create(docName);
  const body = doc.getBody();

  _docTitleBand_(body, `株式会社FUSION 月次採用レポート（中途）`, `${period.label} ／ 生成日 ${formatDate(now)}`);
  body.appendParagraph("");

  // 今月のハイライト（1行）
  let hl = "";
  try {
    const fr = _hrmosFunnelHighlight_(comb);
    const offerRate = comb.entry ? Math.round(comb.offer / comb.entry * 1000) / 10 + "%" : "-";
    hl = `応募 ${comb.entry}名（正社員 ${emp.entry}／業務委託 ${gyo.entry}）／内定 ${comb.offer}名（内定率 ${offerRate}）${fr ? "・最大の歩留まり低下は " + fr : ""}`;
  } catch (e) {}
  if (hl) { const p = body.appendParagraph("今月のハイライト： " + hl); p.editAsText().setForegroundColor(DOC_INK).setFontSize(11).setBold(true); }
  body.appendParagraph("");

  // KPIサマリ（全体＝社員＋業務委託・前月比）
  const hero = _appendHeroBlock(body, [
    { label: "応募",     value: comb.entry + diff(comb.entry, prevComb && prevComb.entry) },
    { label: "最終選考", value: comb.steps[3] },
    { label: "内定",     value: comb.offer + diff(comb.offer, prevComb && prevComb.offer) },
    { label: "承諾",     value: comb.accept },
  ]);
  try { for (let c = 0; c < hero.getRow(1).getNumCells(); c++) hero.getRow(1).getCell(c).getChild(0).asParagraph().editAsText().setFontSize(13); } catch (e) {}
  body.appendParagraph("");

  // 全フェーズ サマリー（雇用区分別 社員/業務委託/合計＋合計前月比）— 業務委託を最上部で可視化
  {
    const flowLabels = ["エントリー"].concat(STEP_LABELS).concat(["内定", "承諾"]);
    const cnt = s => [s.entry].concat(s.steps).concat([s.offer, s.accept]);
    const combC = cnt(comb);
    const preC = prevComb ? cnt(prevComb) : null;
    const dlt = (v, i) => preC ? (v - preC[i] === 0 ? "±0" : (v - preC[i] > 0 ? `+${v - preC[i]}` : `${v - preC[i]}`)) : "-";
    _hrmosDocTable_(body, ["雇用区分"].concat(flowLabels), [
      [`正社員（${emp.entry}名）`].concat(cnt(emp).map(String)),
      [`業務委託（${gyo.entry}名）`].concat(cnt(gyo).map(String)),
      ["合計"].concat(combC.map(String)),
      ["前月比(合計)"].concat(combC.map(dlt)),
    ]);
    body.appendParagraph("");
  }

  // 担当者コメント（編集可能・ルールベース下書き）
  _docH_(body, "担当者コメント（編集してください）");
  body.appendParagraph("下記は数値から自動生成した下書きです。担当者が自由に編集・追記してください。").editAsText().setForegroundColor(DOC_MUTED).setItalic(true).setFontSize(9.5);
  try {
    _ruleInsight_(F).split("\n").forEach(line => { if (line.trim()) body.appendParagraph(line).editAsText().setFontSize(10.5); });
  } catch (e) { body.appendParagraph("（下書き生成に失敗しました。手動で記入してください）"); }
  body.appendParagraph("◇ 総評： ").editAsText().setFontSize(10.5);
  body.appendParagraph("");

  // 選考ファネル（歩留まり・全体＝社員＋業務委託）
  _docH_(body, "選考ファネル（歩留まり・全体）");
  const fLabels = ["エントリー", "カジュアル面談", "1次", "2次", "最終", "会食", "内定", "承諾"];
  const fCounts = [comb.entry].concat(comb.steps).concat([comb.offer, comb.accept]);
  const fb = _qcBarH_(fLabels, fCounts, `選考ファネル 全体（${period.label}）`, { shade: true });
  if (fb) body.appendImage(fb).setWidth(500).setHeight(280);
  const fRows = [];
  for (let i = 0; i < fLabels.length; i++) {
    const prev = i === 0 ? null : fCounts[i - 1];
    const drop = i === 0 ? "—" : String(Math.max(0, fCounts[i - 1] - fCounts[i]));
    fRows.push([fLabels[i], String(fCounts[i]), i === 0 ? "—" : _pct(fCounts[i], prev), _pct(fCounts[i], fCounts[0]), drop]);
  }
  _hrmosDocTable_(body, ["ステージ", "到達数", "前段通過率", "累積通過率", "離脱"], fRows);
  body.appendParagraph("");

  // 業務委託の職種内訳（応募数降順）— 区分別サマリーは冒頭「全フェーズサマリー」に集約
  {
    const gyoKeys = Object.keys(F.gyoStats).sort((a, b) => F.gyoStats[b].entry - F.gyoStats[a].entry);
    if (gyoKeys.length) {
      _docH_(body, "業務委託の職種内訳");
      _hrmosDocTable_(body, ["職種（業務委託）", "応募"].concat(STEP_LABELS).concat(["内定", "承諾"]),
        gyoKeys.map(k => { const s = F.gyoStats[k]; return [k, String(s.entry)].concat(s.steps.map(String)).concat([String(s.offer), String(s.accept)]); }));
      body.appendParagraph("");
    }
  }

  // 職種ごとのエントリー（全職種一覧・社員＋業務委託を統合）
  _docH_(body, "職種ごとのエントリー（全職種）");
  {
    const entryRows = [];
    POSITION_CATEGORIES.forEach(p => { const s = F.stats[p.key]; if (s && s.entry > 0) entryRows.push({ key: p.key, koyou: "正社員", n: s.entry }); });
    Object.keys(F.gyoStats).forEach(k => { const s = F.gyoStats[k]; if (s.entry > 0) entryRows.push({ key: k, koyou: "業務委託", n: s.entry }); });
    entryRows.sort((a, b) => b.n - a.n);
    if (entryRows.length) {
      const eb = _qcBarH_(entryRows.map(x => x.key + (x.koyou === "業務委託" ? "（委託）" : "")), entryRows.map(x => x.n), "職種別 応募（エントリー）数");
      if (eb) body.appendImage(eb).setWidth(540).setHeight(64 + entryRows.length * 26);
      _hrmosDocTable_(body, ["職種", "雇用区分", "応募（エントリー）"], entryRows.map(x => [x.key, x.koyou, String(x.n)]));
    } else {
      body.appendParagraph("（当月の職種別データなし）").editAsText().setForegroundColor(DOC_MUTED).setFontSize(9.5);
    }
    body.appendParagraph("");
  }

  // 職種別ファネル（職種ごとの累積通過率＝歩留まりを横並びで比較）
  _docH_(body, "職種別ファネル（累積通過率）");
  {
    const jfCats = POSITION_CATEGORIES.map(p => ({ key: p.key, s: F.stats[p.key] })).filter(x => x.s && x.s.entry > 0);
    if (jfCats.length) {
      const jfHeader = ["職種", "エントリー"].concat(STEP_LABELS).concat(["内定", "承諾"]);
      _hrmosDocTable_(body, jfHeader, jfCats.map(x => _cumRow(x.key, x.s)));
    } else {
      body.appendParagraph("（当月の職種別データなし）").editAsText().setForegroundColor(DOC_MUTED).setFontSize(9.5);
    }
    body.appendParagraph("");
  }

  // 月次推移（全フェーズ）
  _docH_(body, "月次推移（直近6ヶ月）");
  const tr = _hrmosMonthlyTrend_(6);
  const tb = _qcLineSmart_(tr.labels, tr.series, "全フェーズの月次推移");
  if (tb) body.appendImage(tb).setWidth(500).setHeight(230);
  body.appendParagraph("");

  // 媒体別
  _docH_(body, "媒体別（応募構成・内定率）");
  const chKeys = Object.keys(F.channelStats).sort((a, b) => F.channelStats[b].entry - F.channelStats[a].entry);
  if (chKeys.length) {
    const cb = _qcBarH_(chKeys, chKeys.map(k => F.channelStats[k].entry), "媒体別 応募数");
    if (cb) body.appendImage(cb).setWidth(500).setHeight(64 + chKeys.length * 28);
    _hrmosDocTable_(body, ["媒体", "応募", "カジュ面談", "最終", "内定", "内定率"], chKeys.map(k => { const s = F.channelStats[k]; return [k, String(s.entry), _pct(s.steps[0], s.entry), _pct(s.steps[3], s.entry), String(s.offer), s.entry ? Math.round(s.offer / s.entry * 1000) / 10 + "%" : "-"]; }));
  }
  body.appendParagraph("");

  // エージェント別（「エージェント」を会社名ごとに細分化＝どのエージェント経由か）
  const agKeys = Object.keys(F.agentStats || {}).sort((a, b) => F.agentStats[b]._total.entry - F.agentStats[a]._total.entry);
  if (agKeys.length) {
    _docH_(body, "エージェント別（会社名別 応募・内定）");
    const ab = _qcBarH_(agKeys, agKeys.map(k => F.agentStats[k]._total.entry), "エージェント別 応募数");
    if (ab) body.appendImage(ab).setWidth(500).setHeight(64 + agKeys.length * 28);
    _hrmosDocTable_(body, ["エージェント", "応募", "カジュ面談", "最終", "内定", "内定率"], agKeys.map(k => { const s = F.agentStats[k]._total; return [k, String(s.entry), _pct(s.steps[0], s.entry), _pct(s.steps[3], s.entry), String(s.offer), s.entry ? Math.round(s.offer / s.entry * 1000) / 10 + "%" : "-"]; }));
    body.appendParagraph("");
  }

  // ポジション（カテゴリ）別
  _docH_(body, "ポジション別 実績");
  const catRows = POSITION_CATEGORIES.map(p => ({ key: p.key, s: F.stats[p.key] })).filter(x => x.s);
  if (catRows.length) {
    const pcb = _qcBarH_(catRows.map(x => x.key), catRows.map(x => x.s.entry), "ポジション別 応募数");
    if (pcb) body.appendImage(pcb).setWidth(540).setHeight(64 + catRows.length * 30);
    _hrmosDocTable_(body, ["ポジション", "応募"].concat(STEP_LABELS).concat(["内定", "承諾", "内定率"]),
      catRows.map(x => [x.key, String(x.s.entry)].concat(x.s.steps.map(String)).concat([String(x.s.offer), String(x.s.accept), _pct(x.s.offer, x.s.entry)])));
  }
  body.appendParagraph("");

  body.appendParagraph(`生成: ${formatDatetime(now)} ／ データ: raw_data（業務委託 ${F.totalExcluded}件は「雇用区分別」セクションに区分表示・テスト求人は除外）`).editAsText().setForegroundColor(DOC_MUTED).setFontSize(8.5);

  doc.saveAndClose();
  try { DriveApp.getFileById(doc.getId()).setSharing(DriveApp.Access.DOMAIN_WITH_LINK, DriveApp.Permission.EDIT); } catch (e) { Logger.log("share err: " + e.message); }
  return doc.getUrl();
}

function generateMonthlyDocEditablePrevMonth() {
  const p = _prevMonthPeriod_();
  const url = buildMonthlyDocEditable_(p);
  try { SpreadsheetApp.getUi().alert(`月間レポートDocを生成しました（${p.label}）\n${url}`); } catch (e) { Logger.log("月間Doc: " + url); }
}
function generateMonthlyDocEditableForMonth() {
  const ui = SpreadsheetApp.getUi();
  const resp = ui.prompt("月間レポートDoc 生成", "対象月を YYYY-MM 形式で入力（例: 2026-04）", ui.ButtonSet.OK_CANCEL);
  if (resp.getSelectedButton() !== ui.Button.OK) return;
  const m = resp.getResponseText().trim().match(/^(\d{4})-(\d{1,2})$/);
  if (!m) { ui.alert("形式エラー: YYYY-MM"); return; }
  const url = buildMonthlyDocEditable_(_monthPeriod_(parseInt(m[1], 10), parseInt(m[2], 10)));
  ui.alert(`月間レポートDocを生成しました\n${url}`);
}
