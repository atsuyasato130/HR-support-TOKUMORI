/**
 * DOTZ 28卒 採用 週次レポート（Slack・経営報告粒度）— 本番bound用
 *
 * ■ 役割：production の生データを集計し、Slack に週次レポートを送信する。
 *   各段階の「今週の増加」は Script Properties のスナップショット差分で算出
 *   （到達日列が無いため。送信ごとに基準を更新＝翌週から増加が乗る）。
 * ■ 依存：gas_dotz_kpi.gs（aggregate_/NODES/GOAL/TZ/monday_/md_ 等）と
 *   gas_dotz_monthly_report.gs（mrLoadAggregate_/mrIdx_/mrPctStr_）。
 * ■ 送信先：000_01設定「レポート配信先（Slack）」のチャンネル。
 *   トークンは Script Properties の SLACK_BOT_TOKEN。
 */

var WR_CHANNEL = 'C0A52K66PQV';
var WR_SNAP_KEY = 'DOTZ_WEEKLY_SNAP';

// ───────── メニューエントリ ─────────
function sendWeeklyReportToSlack() {
  var token = PropertiesService.getScriptProperties().getProperty('SLACK_BOT_TOKEN');
  if (!token) { Logger.log('SLACK_BOT_TOKEN 未設定'); return; }
  var A = mrLoadAggregate_();
  var prev = wrLoadSnap_();
  var text = wrBuildText_(A, A.today, prev);
  wrSaveSnap_(A.reach);  // 送信時のみ基準更新
  var options = {
    method: 'post', contentType: 'application/json; charset=UTF-8',
    headers: { Authorization: 'Bearer ' + token },
    payload: JSON.stringify({ channel: WR_CHANNEL, text: text, unfurl_links: false, unfurl_media: false }),
    muteHttpExceptions: true
  };
  var res = UrlFetchApp.fetch('https://slack.com/api/chat.postMessage', options);
  var j = JSON.parse(res.getContentText());
  if (!j.ok) Logger.log('Slack送信エラー: ' + j.error);
  else Logger.log('Slack送信完了 ts=' + j.ts);
}

function previewWeeklyReport() {
  var A = mrLoadAggregate_();
  var text = wrBuildText_(A, A.today, wrLoadSnap_());  // プレビューは基準を消費しない
  Logger.log(text);
  SpreadsheetApp.getActive().toast('週次プレビューを実行ログに出力しました', 'DOTZ自動化', 6);
  return text;
}

function setupWeeklyTrigger() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'sendWeeklyReportToSlack') ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('sendWeeklyReportToSlack').timeBased()
    .onWeekDay(ScriptApp.WeekDay.FRIDAY).atHour(9).nearMinute(0)
    .inTimezone(TZ).create();
  SpreadsheetApp.getActive().toast('毎週金曜9時の週次Slack送信を設定しました', 'DOTZ自動化', 5);
}

// ───────── スナップショット（各段階累計） ─────────
function wrLoadSnap_() {
  var raw = PropertiesService.getScriptProperties().getProperty(WR_SNAP_KEY);
  if (!raw) return null;
  try { return JSON.parse(raw).reach; } catch (e) { return null; }
}
function wrSaveSnap_(reach) {
  PropertiesService.getScriptProperties().setProperty(
    WR_SNAP_KEY, JSON.stringify({ reach: reach }));
}

// ───────── 本文組み立て ─────────
function wrBuildText_(A, today, prevReach) {
  var reach = A.reach, el = A.elapsed;
  var wkStart = monday_(today);
  var thisKey = md_(wkStart);
  var lastKey = md_(new Date(wkStart.getTime() - 7 * 86400000));
  var thisNew = A.weekEntry[thisKey] || 0;
  var lastNew = A.weekEntry[lastKey] || 0;
  var dw = thisNew - lastNew;
  var gEntry = GOAL['エントリー'] || 0, gAcc = GOAL['内定承諾'] || 0;
  var wd = ['日', '月', '火', '水', '木', '金', '土'][today.getDay()];

  var chain = ['エントリー', '説明選考会参加', '1次面接', '2次面接', '最終(役員)面接', '内定承諾'];
  var worst = null;
  for (var i = 1; i < chain.length; i++) {
    var cur = mrIdx_(reach, chain[i]), prev = mrIdx_(reach, chain[i - 1]);
    if (prev < 3) continue;
    var r = cur / prev;
    if (!worst || r < worst[2]) worst = [chain[i - 1], chain[i], r];
  }

  var L = [];
  L.push('*DOTZ 28卒 採用週次レポート* (' + Utilities.formatDate(today, TZ, 'M月d日') + '(' + wd + '))');
  L.push('');

  // TL;DR
  var accFc = el > 0 ? Math.round(A.accept / el) : 0;
  var bn = worst ? (worst[0] + '→' + worst[1] + ' ' + Math.round(worst[2] * 100) + '%') : '—';
  L.push('*＜今週サマリー＞* 新規 ' + thisNew + '件 ／ 累計 ' + reach[0] + '/' + gEntry +
    '（' + mrPctStr_(reach[0], gEntry) + '）／ 承諾着地 約' + accFc + '名(目標' + gAcc + ') ／ 最大BN ' + bn);
  L.push('');

  // 今週のサマリー
  L.push('*■ 今週のサマリー*');
  L.push('新規エントリー: *' + thisNew + '件*（前週比 ' + (dw >= 0 ? '+' : '') + dw + '件）  /  今月累計: ' + A.mMonth + '件');
  L.push('累計エントリー: ' + reach[0] + '件 / 目標 ' + gEntry + '（達成率 ' + mrPctStr_(reach[0], gEntry) + '）');
  L.push('');

  // 今週のファネル増加（スナップ差分）
  L.push('*■ 今週のファネル増加（前回比）*');
  var incStages = ['説明選考会参加', '1次面接', 'カジュアル面談', '2次面接', '最終(役員)面接', '内定出し', '内定承諾'];
  var lbl = { '説明選考会参加': '説明会', '1次面接': '1次', 'カジュアル面談': 'ｶｼﾞｭ', '2次面接': '2次', '最終(役員)面接': '最終', '内定出し': '内定', '内定承諾': '承諾' };
  if (prevReach) {
    var parts = incStages.map(function (name) {
      var idx = NODES.indexOf(name);
      var d = reach[idx] - (idx < prevReach.length ? prevReach[idx] : 0);
      return lbl[name] + ' ' + (d >= 0 ? '+' : '') + d;
    });
    L.push(parts.join(' / '));
  } else {
    L.push('（初回のため基準値を記録。次回レポートから各段階の増加を表示します）');
  }
  L.push('');

  // 選考ファネル＆通過率
  L.push('*■ 選考ファネル＆通過率*');
  var e0 = reach[0], s = mrIdx_(reach, '説明選考会参加'), f1 = mrIdx_(reach, '1次面接');
  var f2 = mrIdx_(reach, '2次面接'), fin = mrIdx_(reach, '最終(役員)面接'), acc = A.accept;
  L.push('Entry *' + e0 + '* → 説明会 ' + s + ' → 1次 ' + f1 + ' → 2次 ' + f2 + ' → 最終 ' + fin + ' → 承諾 ' + acc);
  L.push('通過率: 説明会 ' + mrPctStr_(s, e0) + '  /  説明会→1次 ' + mrPctStr_(f1, s) + '  /  1次→2次 ' + mrPctStr_(f2, f1));
  if (worst) L.push('[要注意] 最大ボトルネック: ' + worst[0] + '→' + worst[1] + ' 通過率 ' + Math.round(worst[2] * 100) + '%');
  L.push('');

  // 着地予想
  L.push('*■ 着地予想（年度末・線形参考）*');
  if (el > 0) {
    var shortName = { '説明選考会参加': '説明会参加', '1次面接': '1次', '2次面接': '2次', '内定出し': '内定', '内定承諾': '承諾' };
    ['説明選考会参加', '1次面接', '2次面接', '内定出し', '内定承諾'].forEach(function (name) {
      var n = mrIdx_(reach, name), fcn = Math.round(n / el), g = GOAL[name];
      var gtxt = g ? (' / 目標 ' + g + '（' + mrPctStr_(fcn, g) + '）') : '';
      L.push(shortName[name] + ': 現 ' + n + ' → 予測 約' + fcn + gtxt);
    });
  }
  L.push('');

  // 経路別の質
  L.push('*■ 経路別の質（説明会→1次 通過率）*');
  var cnt = 0;
  Object.keys(A.routes).forEach(function (route) {
    if (cnt >= 4) return;
    var arr = A.routes[route];
    var rs = arr[NODES.indexOf('説明選考会参加')], r1 = arr[NODES.indexOf('1次面接')];
    if (rs <= 0) return;
    L.push('・' + route + ': 説明会 ' + rs + ' → 1次 ' + r1 + '（' + mrPctStr_(r1, rs) + '）');
    cnt++;
  });
  if (cnt === 0) L.push('・（説明会到達データ蓄積中）');
  L.push('');

  // 選考中の現況
  L.push('*■ 選考中の現況（アクティブ）*');
  var order = ['説明選考会参加', '説明選考会合格', '1次面接', '1次合格', 'カジュアル面談', '2次面接', '最終(役員)面接', '内定出し'];
  var dparts = [];
  order.forEach(function (n) { if (A.activeDist[n]) dparts.push(n + ' ' + A.activeDist[n]); });
  L.push('アクティブ計: *' + A.activeTotal + '名*' + (dparts.length ? '（' + dparts.join(' / ') + '）' : ''));
  L.push('平均選考日数: ' + (A.avgLt != null ? A.avgLt : '—') + '日');
  L.push('');

  // 要対応
  L.push('*■ 今週の要対応*');
  var todos = [];
  if (worst) todos.push(worst[0] + '→' + worst[1] + ' の通過率改善（面談調整・歩留り対策）');
  if (A.activeTotal > 0) todos.push('選考中 ' + A.activeTotal + '名の次アクション設定（停滞防止）');
  if (!todos.length) todos.push('特記事項なし');
  todos.forEach(function (t) { L.push('・' + t); });
  L.push('');
  L.push('※詳細は採用管理シートを確認ください');

  return L.join('\n');
}
