/**
 * Tokumori新卒研修 管理ダッシュボード — バインドGAS
 * 管理スプレッドシート(build_admin_sheet.pyで生成)の Extensions > Apps Script に貼り付ける。
 * 機能: Googleフォーム(確認テスト)の回答を自動取得→点数・合否を集計→受講者ごとの進捗率/平均点を更新。
 *
 * 初回手順:
 *  1) 貼り付けて保存。リロードするとメニュー「研修管理」が出る。
 *  2)「研修管理 > フォームのメール収集をON」を実行(初回に承認)。
 *  3)「研修管理 > テスト結果を取得・集計」で集計。
 *  4)「研修管理 > 毎朝の自動更新を設定」で日次トリガー化(任意)。
 *  ※受講者はGoogleログイン状態でフォーム回答(メールで本人照合)。合格点/満点は「設定」タブで変更可。
 */

var MANAGERS = ['atsuya_sato@tokumori.co.jp', 'shun_watanabe@tokumori.co.jp']; // 管理者（個別シートに常に編集権限を付与）

function onOpen() {
  SpreadsheetApp.getUi().createMenu('研修管理')
    .addItem('① 自動作成をON（名簿に入力→自動で生成）', 'enableAutoGenerate')
    .addItem('受講者シートを今すぐ一括生成', 'generateTraineeSheets')
    .addSeparator()
    .addItem('テスト結果を取得・集計', 'collectResults')
    .addItem('フォームのメール収集をON', 'ensureEmailCollection')
    .addItem('毎朝の自動更新を設定', 'installTrigger')
    .addToUi();
}

/** 受講者名簿の入力を検知して自動生成するトリガーを設置（初回のみ実行・要承認） */
function enableAutoGenerate() {
  ScriptApp.getProjectTriggers().forEach(function (t) { if (t.getHandlerFunction() === 'onRosterEdit') ScriptApp.deleteTrigger(t); });
  ScriptApp.newTrigger('onRosterEdit').forSpreadsheet(SpreadsheetApp.getActive()).onEdit().create();
  SpreadsheetApp.getUi().alert('自動作成をONにしました。\n受講者名簿に「氏名」と「メール」を入力すると、その場で研修シートが作成され、管理者＋本人に権限が付与されURLが記入されます。');
}

/** 名簿(氏名/メール)の編集を検知 → 当該行の研修シートを自動生成 */
function onRosterEdit(e) {
  try {
    var sh = e.range.getSheet();
    if (sh.getName() !== '受講者名簿') return;
    var srcId = SpreadsheetApp.getActive().getSheetByName('設定').getRange('I1').getValue();
    if (!srcId) return;
    var r0 = e.range.getRow(), nr = e.range.getNumRows();
    for (var r = Math.max(2, r0); r < r0 + nr; r++) {
      var row = sh.getRange(r, 1, 1, 7).getValues()[0];
      var name = row[1], email = String(row[2]).trim(), url = row[5];
      if (!email || url) continue; // 未入力 or 既に生成済み
      if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) continue; // メール形式
      var u = makeTraineeSheet_(srcId, sh, r, name, email);
      SpreadsheetApp.getActive().toast((name || email) + ' さんの研修シートを作成し、管理者＋本人に権限を付与しました。', '自動生成 完了', 6);
    }
  } catch (err) { /* 失敗は無視（手動の一括生成で再実行可） */ }
}

/** 1名分：配布元SSを複製し「管理者＋本人のみ」に権限設定→URLを名簿へ記入 */
function makeTraineeSheet_(srcId, sh, rowIndex, name, email) {
  // 命名規則：【新卒研修】氏名（誰のシートか一目で分かる／Driveで並びやすい）
  var copy = DriveApp.getFileById(srcId).makeCopy('【新卒研修】' + (name || email.split('@')[0]));
  try { copy.setSharing(DriveApp.Access.PRIVATE, DriveApp.Permission.NONE); } catch (e) {} // ドメイン公開を解除
  copy.addEditor(email); // 本人
  MANAGERS.forEach(function (m) { try { copy.addEditor(m); } catch (e) {} }); // 管理者2名
  sh.getRange(rowIndex, 6).setValue(copy.getUrl());
  var st = sh.getRange(rowIndex, 7).getValue();
  if (!st || st === '未開始') sh.getRange(rowIndex, 7).setValue('受講中');
  return copy.getUrl();
}

/**
 * 受講者名簿の各メンバーに“研修シート”を配布元SS（既定=研修ハブ本体）から複製し、
 * 権限を「管理者（実行者＋指定マネージャー）＋本人のみ」に設定してURLを名簿へ記入する。
 * 配布元SSのIDは 設定!I1 から取得（研修ハブ＝丸ごと1人1コピー／軽量テンプレに差し替えも可）。
 */
function generateTraineeSheets() {
  var ss = SpreadsheetApp.getActive();
  var tplId = ss.getSheetByName('設定').getRange('I1').getValue();
  if (!tplId) { SpreadsheetApp.getUi().alert('配布元SSのIDが未設定です（設定!I1）。研修ハブまたはテンプレのIDを入れてください。'); return; }
  var sh = ss.getSheetByName('受講者名簿');
  var v = sh.getDataRange().getValues();
  var made = 0, skip = 0, fail = 0;
  for (var i = 1; i < v.length; i++) {
    var name = v[i][1], email = String(v[i][2]).trim(), url = v[i][5];
    if (!email) continue;
    if (url) { skip++; continue; } // 既に生成済みはスキップ
    try { makeTraineeSheet_(tplId, sh, i + 1, name, email); made++; }
    catch (e) { fail++; }
  }
  SpreadsheetApp.getUi().alert('受講者シート生成：新規 ' + made + ' 件 / 既存スキップ ' + skip + ' 件 / 失敗 ' + fail + ' 件\n権限は「管理者2名＋本人」のみ。社内ドメインには非公開です。');
}

function cfg_() {
  var sh = SpreadsheetApp.getActive().getSheetByName('設定');
  var v = sh.getDataRange().getValues();
  var out = [];
  for (var i = 1; i < v.length; i++) {
    if (v[i][4]) out.push({ mid: String(v[i][0]), name: String(v[i][1]), full: Number(v[i][2]) || 100, pass: Number(v[i][3]) || 90, formId: String(v[i][4]) });
  }
  return out;
}

function roster_() {
  var sh = SpreadsheetApp.getActive().getSheetByName('受講者名簿');
  var v = sh.getDataRange().getValues();
  var map = {};
  for (var i = 1; i < v.length; i++) {
    var em = String(v[i][2]).trim().toLowerCase();
    if (em) map[em] = v[i][1];
  }
  return map;
}

function ensureEmailCollection() {
  var c = cfg_(), ok = 0, ng = 0;
  c.forEach(function (m) {
    try {
      var f = FormApp.openById(m.formId);
      try { f.setEmailCollectionType(FormApp.EmailCollectionType.VERIFIED); }
      catch (e) { f.setCollectEmail(true); }
      ok++;
    } catch (e) { ng++; }
  });
  SpreadsheetApp.getUi().alert('メール収集ON: 成功 ' + ok + ' / 失敗 ' + ng + '\n(失敗はフォームの所有権をご確認ください)');
}

function collectResults() {
  var ss = SpreadsheetApp.getActive();
  var c = cfg_(), rmap = roster_();
  var passOf = {}; c.forEach(function (m) { passOf[m.mid] = m.pass; });
  var logs = [];
  c.forEach(function (m) {
    var f;
    try { f = FormApp.openById(m.formId); } catch (e) { return; }
    var res;
    try { res = f.getResponses(); } catch (e) { return; }
    res.forEach(function (r) {
      var email = '';
      try { email = r.getRespondentEmail(); } catch (e) {}
      email = String(email || '').trim().toLowerCase();
      var sc = 0;
      var items = r.getGradableItemResponses();
      items.forEach(function (it) { var s = it.getScore(); if (typeof s === 'number') sc += s; });
      var ts = r.getTimestamp();
      var pass = (sc >= m.pass) ? '合格' : '不合格';
      logs.push([ts, email, rmap[email] || '', m.mid, m.name, sc, m.full, pass]);
    });
  });
  var lsh = ss.getSheetByName('結果ログ');
  if (lsh.getMaxRows() > 1) lsh.getRange(2, 1, lsh.getMaxRows() - 1, 8).clearContent();
  if (logs.length) lsh.getRange(2, 1, logs.length, 8).setValues(logs);
  refreshProgress_(c, rmap, logs, passOf);
  refreshModuleAgg_(c, logs);
  SpreadsheetApp.getUi().alert('集計完了: 回答 ' + logs.length + ' 件を取り込みました。');
}

function refreshModuleAgg_(c, logs) {
  var CATN = { A: '自社・マインド', B: 'ビジネス基礎', C: 'PC・ツール', D: '思考・分析', E: '自己・対人', F: 'CA職種特化', G: 'リスク・コンプラ' };
  var byMod = {};
  logs.forEach(function (L) {
    var mid = L[3], email = L[1], sc = L[5];
    if (!email) return;
    if (!byMod[mid]) byMod[mid] = {};
    if (byMod[mid][email] === undefined || sc > byMod[mid][email]) byMod[mid][email] = sc;
  });
  var rows = [];
  c.forEach(function (m) {
    var bm = byMod[m.mid] || {};
    var emails = Object.keys(bm);
    var taken = emails.length, passed = 0, sum = 0;
    emails.forEach(function (e) { sum += bm[e]; if (bm[e] >= m.pass) passed++; });
    rows.push([m.mid, m.name, CATN[m.mid.charAt(0)] || '', taken, passed, taken ? passed / taken : 0, taken ? Math.round(sum / taken * 10) / 10 : 0]);
  });
  var sh = SpreadsheetApp.getActive().getSheetByName('モジュール別集計');
  if (sh.getMaxRows() > 1) sh.getRange(2, 1, sh.getMaxRows() - 1, 7).clearContent();
  if (rows.length) sh.getRange(2, 1, rows.length, 7).setValues(rows);
}

function refreshProgress_(c, rmap, logs, passOf) {
  var total = c.length;
  var byEmail = {};
  logs.forEach(function (L) {
    var email = L[1]; if (!email) return;
    if (!byEmail[email]) byEmail[email] = { best: {}, last: 0 };
    var mid = L[3], sc = L[5], ts = new Date(L[0]).getTime();
    if (byEmail[email].best[mid] === undefined || sc > byEmail[email].best[mid]) byEmail[email].best[mid] = sc;
    if (ts > byEmail[email].last) byEmail[email].last = ts;
  });
  // 名簿のメールも対象に（未受験者も0%で表示）
  var emails = {};
  Object.keys(byEmail).forEach(function (e) { emails[e] = 1; });
  var rv = SpreadsheetApp.getActive().getSheetByName('受講者名簿').getDataRange().getValues();
  for (var i = 1; i < rv.length; i++) { var em = String(rv[i][2]).trim().toLowerCase(); if (em) emails[em] = 1; }
  var rows = [];
  Object.keys(emails).forEach(function (email) {
    var b = byEmail[email] || { best: {}, last: 0 };
    var attempted = Object.keys(b.best).length;
    var passed = 0, sum = 0, cnt = 0, notPassed = [];
    c.forEach(function (m) {
      if (b.best[m.mid] !== undefined) {
        cnt++; sum += b.best[m.mid];
        if (b.best[m.mid] >= m.pass) passed++; else notPassed.push(m.name);
      } else notPassed.push(m.name);
    });
    var rate = total ? passed / total : 0;
    var avg = cnt ? Math.round(sum / cnt * 10) / 10 : 0;
    var last = b.last ? Utilities.formatDate(new Date(b.last), Session.getScriptTimeZone(), 'yyyy/MM/dd') : '';
    rows.push([rmap[email] || '', email, rate, attempted, passed, avg, last, notPassed.slice(0, 12).join('・')]);
  });
  rows.sort(function (a, b) { return b[2] - a[2]; });
  var psh = SpreadsheetApp.getActive().getSheetByName('進捗・成績');
  if (psh.getMaxRows() > 1) psh.getRange(2, 1, psh.getMaxRows() - 1, 8).clearContent();
  if (rows.length) psh.getRange(2, 1, rows.length, 8).setValues(rows);
}

function installTrigger() {
  ScriptApp.getProjectTriggers().forEach(function (t) { if (t.getHandlerFunction() === 'collectResults') ScriptApp.deleteTrigger(t); });
  ScriptApp.newTrigger('collectResults').timeBased().everyDays(1).atHour(7).create();
  SpreadsheetApp.getUi().alert('毎朝7時の自動集計を設定しました。');
}
