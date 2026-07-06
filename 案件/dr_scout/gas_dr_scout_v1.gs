/**
 * DR/スカウト管理シート（テンプレ v1）コンテナバインドGAS
 *
 * 役割（数式駆動の補助層。これが無くても日常利用は可能）:
 *   - メニュー「DRスカウト管理」
 *   - 媒体を追加（_媒体テンプレ複製 → 設定マスタ登録 → マスター結合式を再生成）
 *   - マスター再集計（媒体タブの増減に合わせて結合式を作り直す）
 *   - onEdit：媒体タブの編集行に最終更新日(W列)を自動記入
 *
 * 正本: ~/Claude AI/gas_dr_scout_v1.gs
 * ファネル: ListUp → 送付 → 返信 → 面談 → 採用
 */

var SET_TAB = '03_設定マスタ';
var MST_TAB = '02_マスター';
var SUM_TAB = '01_サマリー';
var README_TAB = '00_使い方';
var TEMPLATE_TAB = '_媒体テンプレ';
var DAILY_TAB = '04_日次入力';
var SYSTEM_TABS = [SET_TAB, MST_TAB, SUM_TAB, README_TAB, TEMPLATE_TAB, DAILY_TAB];

// 設定マスタ座標（build_dr_scout_v1.py と一致させること）
var MEDIA_LIST_FIRST = 5;   // 媒体リスト データ先頭行
var MEDIA_LIST_SLOTS = 12;
var GOAL_FIRST = 45;        // 月次目標 データ先頭行
var DATA_START = 3;         // 媒体タブ データ開始行
var COL_NAME = 4;           // 媒体タブ 候補者名(D)列
var COL_UPD = 23;           // 媒体タブ 最終更新日(W)列

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('DRスカウト管理')
    .addItem('媒体を追加', 'addMediaTab')
    .addItem('マスター再集計', 'rebuildMaster')
    .addSeparator()
    .addItem('（参考）使い方を開く', 'showReadme')
    .addToUi();
}

function showReadme() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  ss.getSheetByName(README_TAB).activate();
}

/** 設定マスタの媒体リストにある媒体名（空でないもの）を返す。 */
function getMediaNames_() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var set = ss.getSheetByName(SET_TAB);
  var vals = set.getRange(MEDIA_LIST_FIRST, 1, MEDIA_LIST_SLOTS, 1).getValues();
  var names = [];
  for (var i = 0; i < vals.length; i++) {
    var v = String(vals[i][0]).trim();
    if (v) names.push(v);
  }
  return names;
}

/** マスターの結合式を、現在の媒体リストから作り直す。 */
function rebuildMaster() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var names = getMediaNames_();
  if (names.length === 0) {
    SpreadsheetApp.getUi().alert('媒体リストが空です。設定マスタに媒体を登録してください。');
    return;
  }
  var blocks = [];
  for (var i = 0; i < names.length; i++) {
    var qn = "'" + names[i].replace(/'/g, "''") + "'";
    blocks.push(
      'ARRAYFORMULA(IF(' + qn + '!$A$' + DATA_START + ':$A<>"","' + names[i] + '","")),' +
      qn + '!$A$' + DATA_START + ':$W'
    );
  }
  var formula = '={' + blocks.join('; ') + '}';

  var mst = ss.getSheetByName(MST_TAB);
  // 行数が足りなければ拡張（媒体数 × タブ行数 を確保）
  var perTab = ss.getSheetByName(names[0]).getMaxRows();
  var need = perTab * names.length + 50;
  if (mst.getMaxRows() < need) {
    mst.insertRowsAfter(mst.getMaxRows(), need - mst.getMaxRows());
  }
  mst.getRange('A' + DATA_START).setFormula(formula);
  SpreadsheetApp.flush();
}

/** 媒体を追加：テンプレ複製→設定マスタ登録→マスター再集計。 */
function addMediaTab() {
  var ui = SpreadsheetApp.getUi();
  var ss = SpreadsheetApp.getActiveSpreadsheet();

  var res = ui.prompt('媒体を追加', '媒体名を入力（例: Wantedly）', ui.ButtonSet.OK_CANCEL);
  if (res.getSelectedButton() !== ui.Button.OK) return;
  var name = res.getResponse().trim();
  if (!name) { ui.alert('媒体名が空です。'); return; }
  if (ss.getSheetByName(name)) { ui.alert('同名のタブが既に存在します。'); return; }
  if (SYSTEM_TABS.indexOf(name) !== -1) { ui.alert('その名前はシステム用に予約されています。'); return; }

  var res2 = ui.prompt('媒体を追加', '略号を入力（候補者IDの接頭辞・例: WT）', ui.ButtonSet.OK_CANCEL);
  if (res2.getSelectedButton() !== ui.Button.OK) return;
  var abbr = res2.getResponse().trim() || name.substring(0, 2).toUpperCase();

  // テンプレ複製
  var tpl = ss.getSheetByName(TEMPLATE_TAB);
  var ns = tpl.copyTo(ss);
  ns.setName(name);
  ns.showSheet();
  // バナー & 候補者ID式を媒体に合わせて書き換え
  ns.getRange('A1').setValue('媒体：' + name);
  ns.getRange('A' + DATA_START).setFormula(
    '=ARRAYFORMULA(IF($D$' + DATA_START + ':$D="","","' + abbr +
    '-"&TEXT(ROW($D$' + DATA_START + ':$D)-' + (DATA_START - 1) + ',"000")))'
  );
  // 媒体タブをテンプレの直前に移動（末尾の手前）
  ss.setActiveSheet(ns);
  ss.moveActiveSheet(tpl.getIndex());  // テンプレの位置へ＝テンプレを後ろに押し出す

  // 設定マスタ登録（媒体リストの最初の空き行 / 月次目標も同様）
  var set = ss.getSheetByName(SET_TAB);
  // 媒体名/略号/主チャネル/状態/集計方式(既定=個別)/アカウント/URL/memo
  registerToSlot_(set, MEDIA_LIST_FIRST, MEDIA_LIST_SLOTS, [name, abbr, '', '利用中', '個別', '', '', '']);

  rebuildMaster();
  ui.alert('「' + name + '」を追加しました。入力はそのタブで、進捗は ' + SUM_TAB + ' で確認できます。');
}

/** 指定列ブロックの最初の空き行に値を書く（媒体リスト/目標の媒体名列=A基準）。 */
function registerToSlot_(sheet, firstRow, slots, rowValues) {
  for (var i = 0; i < slots; i++) {
    var r = firstRow + i;
    if (String(sheet.getRange(r, 1).getValue()).trim() === '') {
      // 月次目標行は媒体名が数式参照のため、媒体リストのみ実値で登録
      sheet.getRange(r, 1, 1, rowValues.length).setValues([rowValues]);
      return;
    }
  }
}

/** 媒体タブの編集時、その行の最終更新日(W)を今日に。 */
function onEdit(e) {
  try {
    var sh = e.range.getSheet();
    var name = sh.getName();
    if (SYSTEM_TABS.indexOf(name) !== -1) return;
    var row = e.range.getRow();
    if (row < DATA_START) return;
    // 候補者名が無い行は触らない
    if (String(sh.getRange(row, COL_NAME).getValue()).trim() === '') return;
    // 最終更新日列自身の編集は無視
    if (e.range.getColumn() === COL_UPD) return;
    sh.getRange(row, COL_UPD).setValue(new Date());
  } catch (err) {
    // onEdit内のエラーは無視（運用を止めない）
  }
}
