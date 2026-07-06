/**
 * DOTZ 28卒 採用進捗管理 — Slack 週次レポート
 *
 * ■ セットアップ手順（初回のみ）
 *   1. このファイルの内容を Apps Script エディタに貼り付ける（既存コードとは別ファイル推奨）
 *   2. Script Properties に SLACK_BOT_TOKEN を追加
 *      → Apps Script エディタ > プロジェクトの設定 > スクリプト プロパティ > 追加
 *      → プロパティ: SLACK_BOT_TOKEN / 値: .env の SLACK_BOT_TOKEN 値
 *   3. メニュー「DOTZ自動化 > ⑦ Slack週次トリガー設定」を実行（毎週金曜9:00 JSTに自動実行される）
 *
 * ■ 手動テスト
 *   Apps Script エディタで sendWeeklyReportToSlack を選択して「実行」
 */

const REPORT_SS_ID    = '1T_YJOYhR2leqz9atAV4RN2oiwL61IwJBb72rmn7ZaxI';
const REPORT_CHANNEL  = 'C0A52K66PQV';  // 000_01設定 > レポート配信先（Slack）
const REPORT_SS_URL   = 'https://docs.google.com/spreadsheets/d/1T_YJOYhR2leqz9atAV4RN2oiwL61IwJBb72rmn7ZaxI/edit';

/**
 * Slack週次レポート送信（毎週金曜9:00JSTに自動実行）
 */
function sendWeeklyReportToSlack() {
  var token = PropertiesService.getScriptProperties().getProperty('SLACK_BOT_TOKEN');
  if (!token) {
    Logger.log('ERROR: SLACK_BOT_TOKEN が Script Properties に未設定です');
    return;
  }

  var ss = SpreadsheetApp.openById(REPORT_SS_ID);
  var message = buildSlackReport_(ss);

  var options = {
    method: 'post',
    contentType: 'application/json; charset=UTF-8',
    headers: { Authorization: 'Bearer ' + token },
    payload: JSON.stringify({
      channel: REPORT_CHANNEL,
      text: message,
      unfurl_links: false,
      unfurl_media: false,
    }),
    muteHttpExceptions: true,
  };

  var res = UrlFetchApp.fetch('https://slack.com/api/chat.postMessage', options);
  var json = JSON.parse(res.getContentText());
  if (!json.ok) {
    Logger.log('Slack送信エラー: ' + json.error);
  } else {
    Logger.log('Slack送信完了: ts=' + json.ts);
  }
}

/**
 * レポート本文を組み立てる
 */
function buildSlackReport_(ss) {
  var today  = new Date();
  var dateStr = Utilities.formatDate(today, 'Asia/Tokyo', 'M月d日(E)');

  // 003_03 KPI行（B5:J5）
  var s03  = ss.getSheetByName('003_03_分析サマリー');
  var kpi  = s03 ? s03.getRange('B5:J5').getValues()[0] : [];
  var totalEntry = kpi[0] || 0;
  var weekEntry  = kpi[2] || 0;
  var setsuEntry = kpi[3] || 0;
  var active     = kpi[5] || 0;
  var承諾        = kpi[6] || 0;

  // 003_01 ファネル合計行（B6:R6）
  var s01     = ss.getSheetByName('003_01_採用サマリー（経路別ファネル・月次/週次）');
  var funnel  = s01 ? s01.getRange('B6:R6').getValues()[0] : [];
  // B=エントリー, C=%, D=説明会, E=%, F=1次, ..., L=2次, ..., N=最終, ..., R=承諸
  var f0 = funnel[0]  || 0;  // エントリー
  var f2 = funnel[2]  || 0;  // 説明会
  var f4 = funnel[4]  || 0;  // 1次
  var f10= funnel[10] || 0;  // 2次
  var f12= funnel[12] || 0;  // 最終
  var f16= funnel[16] || 0;  // 承諸

  // 今週エントリー（週次行先頭）
  var weekRow = s01 ? s01.getRange('B59:J59').getValues()[0] : [];
  var weekLabel = weekRow[0] || '';
  var weekNew   = weekRow[1] || 0;

  // エージェント / スカウト内訳
  var agEntry = s01 ? s01.getRange('B52').getValue() : 0;
  var scEntry = s01 ? s01.getRange('B29').getValue() : 0;

  var lines = [
    '*📊 DOTZ 28卒 採用週次レポート* (' + dateStr + ')',
    '',
    '*■ KPI（全期間合計）*',
    'エントリー: *' + f0 + '件*（エージェント: ' + agEntry + '件 / スカウト: ' + scEntry + '件）',
    '説明会参加: ' + f2 + '件  アクティブ: ' + active + '件  内定承諸: ' + 承諸 + '件',
    '',
    '*■ 選考ファネル*',
    'Entry *' + f0 + '* → 説明会 ' + f2 + ' → 1次 ' + f4 + ' → 2次 ' + f10 + ' → 最終 ' + f12 + ' → 承諸 ' + f16,
    '',
    '*■ 今週（' + weekLabel + '～）*',
    'エントリー: ' + weekNew + '件',
    '',
    '※詳細は以下シートを確認ください',
    '<' + REPORT_SS_URL + '|📄 採用管理シート>',
  ];

  return lines.join('\n');
}

/**
 * 毎週金曜 9:00 JST トリガーを設定（一度だけ実行）
 * 既存の同名トリガーは削除して再作成
 */
function setupFridayTrigger() {
  ScriptApp.getProjectTriggers().forEach(function(t) {
    if (t.getHandlerFunction() === 'sendWeeklyReportToSlack') {
      ScriptApp.deleteTrigger(t);
    }
  });
  ScriptApp.newTrigger('sendWeeklyReportToSlack')
    .timeBased()
    .onWeekDay(ScriptApp.WeekDay.FRIDAY)
    .atHour(9)
    .nearMinute(0)
    .inTimezone('Asia/Tokyo')
    .create();
  var msg = '毎週金曜 9:00 JSTのトリガーを設定しました';
  Logger.log(msg);
  SpreadsheetApp.getActive().toast(msg, 'DOTZ自動化', 5);
}
