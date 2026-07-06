/**
 * 目標管理シート 雛形／本人版 — AI（Gemini）バインドGAS
 * 対象スプレッドシートに「拡張機能 > Apps Script」でバインドし、本ファイルを貼り付けて使う。
 * 前提：スクリプトプロパティ GEMINI_API_KEY に Gemini APIキーを設定。
 *
 * 機能（メニュー「AI（Gemini）」）：
 *  A. 月次まとめ … 「月次振り返り」のKPI推移＋振り返りログを Gemini が上期/下期/Q/通期で要約 → D31-D37
 *  B. 評価コメント下書き … 評価タブ（通期/上半期/下半期）の点数＋役職＋月次ログから、上長評価コメントを下書き
 *
 * 年度：6月始まり（上期=6-11 / 下期=12-5、Q1=6-8 Q2=9-11 Q3=12-2 Q4=3-5）。
 * 採点思想：達成=100点基準、定量はOTE公式 支給率テーブル準拠、定性/バリュー=◎120/◯100/△80。
 *
 * ── シート上の固定参照位置（build_template_v1.py と一致。レイアウト変更時はここも更新）──
 *  月次振り返り：KPI B6:B13=項目 / C6:N13=12か月(C=6月…N=5月)、個人売上=12行 チーム売上=13行
 *                ログ 行17-28（B=月, C=できたこと, I=課題, N=来月のアクション, R=上長コメント）
 *                AIサマリー書込先：上半期D31 下半期D32 Q1D33 Q2D34 Q3D35 Q4D36 通期D37
 *  評価タブ（通期/上半期/下半期）：
 *                ブロック先頭行 定量[6,11,16] 定性[25,28,31] バリュー[38,41,44]
 *                C=目標項目, D=目標(SMART), M=自己点, P=上長点, Q=採点方式
 *                カード：D=自己 E=上長、総合点 行51 / 定量53 定性54 バリュー55（配点 定量60/定性20/バリュー20）
 *  ダッシュボード：C5=役職, C6=区分(OTE/MBO), F6=Base:Variable
 */

var MONTHLY_SHEET = "月次振り返り";
var DASH_SHEET = "ダッシュボード";
var EVAL_SHEETS = ["通期", "上半期", "下半期"];
var MONTHS = ["6月", "7月", "8月", "9月", "10月", "11月", "12月", "1月", "2月", "3月", "4月", "5月"];
var GEMINI_MODEL = "gemini-2.0-flash";   // 必要に応じて変更可（gemini-2.5-flash 等）

var RANGE_MAP = {  // [開始月index, 終了月index(排他)]
  "上半期": [0, 6], "下半期": [6, 12],
  "Q1": [0, 3], "Q2": [3, 6], "Q3": [6, 9], "Q4": [9, 12], "通期": [0, 12]
};
var TARGET_CELL = {
  "上半期": "D31", "下半期": "D32", "Q1": "D33", "Q2": "D34", "Q3": "D35", "Q4": "D36", "通期": "D37"
};

// 評価タブのブロック先頭行（自己点=M, 上長点=P）
var BLOCKS = {
  "定量": [6, 11, 16], "定性": [25, 28, 31], "バリュー": [38, 41, 44]
};
// カード（自己=D列 / 上長=E列）
var CARD = { total: 51, quant: 53, qual: 54, value: 55 };


function onOpen() {
  var ui = SpreadsheetApp.getUi();
  ui.createMenu("AI（Gemini）")
    .addSubMenu(ui.createMenu("月次まとめ")
      .addItem("上半期サマリー（6-11月）", "summarizeFirstHalf")
      .addItem("下半期サマリー（12-5月）", "summarizeSecondHalf")
      .addSeparator()
      .addItem("Q1（6-8月）", "summarizeQ1").addItem("Q2（9-11月）", "summarizeQ2")
      .addItem("Q3（12-2月）", "summarizeQ3").addItem("Q4（3-5月）", "summarizeQ4")
      .addSeparator()
      .addItem("通期サマリー", "summarizeAnnual"))
    .addSubMenu(ui.createMenu("評価コメント下書き")
      .addItem("通期", "draftAnnual")
      .addItem("上半期", "draftFirstHalf")
      .addItem("下半期", "draftSecondHalf"))
    .addSeparator()
    .addItem("APIキー設定状況を確認", "checkApiKey")
    .addToUi();
}

// ── A. 月次まとめ ─────────────────────────────────────────────
function summarizeFirstHalf() { summarizePeriod_("上半期"); }
function summarizeSecondHalf() { summarizePeriod_("下半期"); }
function summarizeQ1() { summarizePeriod_("Q1"); }
function summarizeQ2() { summarizePeriod_("Q2"); }
function summarizeQ3() { summarizePeriod_("Q3"); }
function summarizeQ4() { summarizePeriod_("Q4"); }
function summarizeAnnual() { summarizePeriod_("通期"); }

function summarizePeriod_(key) {
  var ui = SpreadsheetApp.getUi();
  var sh = SpreadsheetApp.getActive().getSheetByName(MONTHLY_SHEET);
  if (!sh) { ui.alert("「" + MONTHLY_SHEET + "」タブが見つかりません"); return; }

  var record = buildMonthlyText_(sh, key);
  if (!record.hasData &&
      ui.alert(key + "の入力がまだ無いようです。それでも生成しますか？", ui.ButtonSet.YES_NO) != ui.Button.YES) return;

  var prompt =
    "あなたは人材紹介会社のマネージャーです。メンバーの" + key + "の月次記録（KPIと振り返り）を読み、" +
    "上長が評価コメントの下書きに使えるよう簡潔に整理してください。\n" +
    "次の4見出しで、各2〜4行の箇条書き（過度な装飾や絵文字は不要、端的に）:\n" +
    "1) KPIの傾向（伸び・停滞・季節性など数字の動き）\n2) できたこと（成果・前進）\n" +
    "3) 課題（つまずき・未達の要因）\n4) 次への学び・打ち手\n\n" +
    "=== " + key + " の月次記録 ===\n" + record.text;

  var out;
  try { out = callGemini_(prompt); }
  catch (e) { ui.alert("生成に失敗しました：\n" + e.message); return; }
  sh.getRange(TARGET_CELL[key]).setValue(out + "\n\n（AI生成 " + stamp_() + "）");
  SpreadsheetApp.getActive().toast(key + "サマリーを生成しました", "月次まとめ", 4);
}

function buildMonthlyText_(sh, key) {
  var rng = RANGE_MAP[key], s = rng[0], e = rng[1];
  var labels = sh.getRange("B6:B13").getValues().map(function (r) { return r[0]; });
  var kpi = sh.getRange(6, 3, 8, 12).getValues();    // 8項目 × 12か月（C..N）
  var log = sh.getRange(17, 2, 12, 20).getValues();  // 12か月 × B..U
  var text = "", hasData = false;
  for (var m = s; m < e; m++) {
    text += "【" + MONTHS[m] + "】\n";
    for (var i = 0; i < labels.length; i++) {
      var v = kpi[i][m];
      if (v !== "" && v !== null) hasData = true;
      text += "  ・" + labels[i] + ": " + (v === "" ? "—" : v) + "\n";
    }
    var row = log[m];  // idx: 1=できたこと(C) 7=課題(I) 12=来月(N) 16=上長(R)
    if (row[1] || row[7] || row[12] || row[16]) hasData = true;
    text += "  ＜できたこと＞" + (row[1] || "—") + "\n  ＜課題＞" + (row[7] || "—") +
            "\n  ＜来月のアクション＞" + (row[12] || "—") + "\n  ＜上長コメント＞" + (row[16] || "—") + "\n\n";
  }
  return { text: text, hasData: hasData };
}

// ── B. 評価コメント下書き ─────────────────────────────────────
function draftAnnual() { draftEvalComment_("通期"); }
function draftFirstHalf() { draftEvalComment_("上半期"); }
function draftSecondHalf() { draftEvalComment_("下半期"); }

function draftEvalComment_(period) {
  var ui = SpreadsheetApp.getUi();
  var ss = SpreadsheetApp.getActive();
  var ev = ss.getSheetByName(period);
  if (!ev) { ui.alert("「" + period + "」タブが見つかりません"); return; }

  var ctx = buildEvalContext_(ss, ev, period);
  if (!ctx.scored &&
      ui.alert(period + "の点数がまだ「未評価」のようです。それでも下書きしますか？", ui.ButtonSet.YES_NO) != ui.Button.YES) return;

  var prompt =
    "あなたは人材紹介会社の評価者（上長）です。以下のメンバーの" + period + "の評価データをもとに、" +
    "本人に渡す評価フィードバックコメントの下書きを作成してください。\n" +
    "条件：\n" +
    "・前向きかつ率直に。良かった点と改善点を具体的に（数字・行動に触れる）。\n" +
    "・達成=100点が基準。100超は超過達成、100未満は未達。OTE職種は達成率で報酬が変わる前提を踏まえる。\n" +
    "・最後に次期に向けた期待・打ち手を2〜3点。\n" +
    "・400〜600字程度、絵文字や過度な装飾は不要、敬体で。\n\n" +
    "=== 評価データ（" + period + "）===\n" + ctx.text;

  var out;
  try { out = callGemini_(prompt); }
  catch (e) { ui.alert("生成に失敗しました：\n" + e.message); return; }

  var html = HtmlService.createHtmlOutput(
    '<div style="font-family:sans-serif;padding:8px">' +
    '<div style="font-size:12px;color:#888;margin-bottom:6px">' + period +
    ' 評価コメント下書き（AI生成 ' + stamp_() + '）— 内容を確認・調整のうえHRブレイン等へ貼り付けてください</div>' +
    '<textarea style="width:100%;height:300px;font-size:13px;line-height:1.6" onclick="this.select()">' +
    out.replace(/</g, "&lt;") + '</textarea></div>')
    .setWidth(560).setHeight(380);
  ui.showModalDialog(html, period + " 評価コメント下書き");
}

function buildEvalContext_(ss, ev, period) {
  var dash = ss.getSheetByName(DASH_SHEET);
  var role = dash ? (dash.getRange("C5").getValue() || "（役職未選択）") : "";
  var kubun = dash ? dash.getRange("C6").getValue() : "";
  var bv = dash ? dash.getRange("F6").getValue() : "";

  // カード（自己=D / 上長=E）
  function card(r) { return ev.getRange("D" + r).getValue() + " / " + ev.getRange("E" + r).getValue(); }
  var scored = ev.getRange("E" + CARD.total).getValue() !== "未評価" &&
               ev.getRange("E" + CARD.total).getValue() !== "";

  var text = "役職: " + role + "（区分 " + kubun + " / Base:Variable " + bv + "）\n" +
    "総合点(自己/上長): " + card(CARD.total) + "\n" +
    "  定量(60%): " + card(CARD.quant) + " ／ 定性(20%): " + card(CARD.qual) +
    " ／ バリュー(20%): " + card(CARD.value) + "\n\n■ 目標別\n";

  Object.keys(BLOCKS).forEach(function (cat) {
    BLOCKS[cat].forEach(function (r) {
      var item = ev.getRange("C" + r).getValue();
      if (!item) return;
      var smart = ev.getRange("D" + r).getValue();
      var self = ev.getRange("M" + r).getValue();
      var boss = ev.getRange("P" + r).getValue();
      text += "・[" + cat + "] " + item + "（自己" + self + "/上長" + boss + "）" +
              (smart ? " — " + String(smart).slice(0, 60) : "") + "\n";
    });
  });

  // 月次の振り返り（あれば文脈として添える）
  var msh = ss.getSheetByName(MONTHLY_SHEET);
  if (msh) {
    var key = (period === "通期") ? "通期" : period;
    var rec = buildMonthlyText_(msh, RANGE_MAP[key] ? key : "通期");
    if (rec.hasData) text += "\n■ 月次振り返り（抜粋）\n" + rec.text.slice(0, 1500);
  }
  return { text: text, scored: scored };
}

// ── 共通 ─────────────────────────────────────────────────────
function checkApiKey() {
  var k = PropertiesService.getScriptProperties().getProperty("GEMINI_API_KEY");
  SpreadsheetApp.getUi().alert(k ? "GEMINI_API_KEY は設定済みです（先頭: " + k.slice(0, 6) + "…）" :
    "GEMINI_API_KEY が未設定です。\nプロジェクトの設定 > スクリプトプロパティ で登録してください。");
}

function stamp_() {
  return Utilities.formatDate(new Date(), Session.getScriptTimeZone(), "yyyy/MM/dd HH:mm");
}

function callGemini_(prompt) {
  var apiKey = PropertiesService.getScriptProperties().getProperty("GEMINI_API_KEY");
  if (!apiKey) throw new Error("スクリプトプロパティ GEMINI_API_KEY が未設定です。プロジェクトの設定 > スクリプトプロパティ で登録してください。");
  var url = "https://generativelanguage.googleapis.com/v1beta/models/" + GEMINI_MODEL + ":generateContent?key=" + apiKey;
  var payload = { "contents": [{ "parts": [{ "text": prompt }] }],
                  "generationConfig": { "temperature": 0.4, "maxOutputTokens": 1200 } };
  var res = UrlFetchApp.fetch(url, { "method": "post", "contentType": "application/json",
                                     "payload": JSON.stringify(payload), "muteHttpExceptions": true });
  var code = res.getResponseCode(), body = res.getContentText();
  if (code !== 200) throw new Error("Gemini API エラー (" + code + "): " + body.slice(0, 300));
  var j = JSON.parse(body);
  if (!j.candidates || !j.candidates[0]) throw new Error("Geminiから応答が空でした: " + body.slice(0, 300));
  return j.candidates[0].content.parts[0].text.trim();
}
