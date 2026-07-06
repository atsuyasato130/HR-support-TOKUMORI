/************************************************************
 * DOTZ 選考リマインド＋面接調整モジュール（自己完結・追加のみ）
 * - 既存シート/コードは一切変更しない。新規タブを作る／進捗管理は右端に1列追加のみ。
 * - 採用マスタ(自社採用 gas_saiyo_v1.js)のリマインド基盤を移植＋面接調整コックピット。
 * - 名前衝突回避のため全て dz / DZ プレフィクス。
 *
 * 構成:
 *   面接スケジュール（日時の正本・正規化表）  ← dzBuildScheduleTab_
 *   リマインド設定（段別テンプレ＋確定/変更通知）← dzBuildReminderSettingsTab_
 *   面接調整（人事主導コックピット）          ← dzBuildCoordTab_
 *   進捗管理(003_000_03) 右端に「学生ID」採番   ← dzAssignStudentIds_
 *   進捗管理 → 面接スケジュール 取込（読むだけ） ← dzImportSchedule_
 *   面接調整 → 確定/変更通知＋スケジュール反映  ← dzConfirmInterviews_
 *   面接スケジュール → リマインド送信          ← dzSendRemindersAuto_
 *
 * メニューは既存 onOpen に dzMenu_(ui) を1行足して呼ぶ（onOpenは新規定義しない）。
 ************************************************************/

var DZ = {
  PROG: '003_000_03採用進捗管理',   // 進捗管理（読む＋右端にID列追加のみ）
  PROG_HEADER_ROW: 10,             // ヘッダ行
  SCHED: '面接スケジュール',          // 日時の正本
  SETTINGS: 'リマインド設定',         // 段別テンプレ＋通知テンプレ
  COORD: '面接調整',                // 人事主導コックピット
  // 進捗管理の列（0始まり）: I=8姓 / J=9名 / Q=16メール
  COL_LAST: 8, COL_FIRST: 9, COL_EMAIL: 16,
  SID_HEADER: '学生ID',            // 進捗管理に新設するヘッダ名（位置はヘッダ名で特定）
  SID_PREFIX: 'DOTZ28-',
  // 段→確定日程列（0始まり）。全段とも「日時+Zoom URL混在」形式（dzParseEventDate_で抽出）。
  STAGES: [
    { stage: '1次面接',      col: 59 },                 // BH 確定時間/URL
    { stage: 'カジュアル面談', col: 74 },                 // BW 確定日程
    { stage: '1dayインターン', col: 84 },                 // CG 確定日程
    { stage: '2次面接',      col: 98 },                 // CU 確定日程
    { stage: '最終面接',      col: 112, timeCol: 113 },   // DI 確定日程(+DJ 確定時間)
  ],
  STAGE_NAMES: ['1次面接', 'カジュアル面談', '1dayインターン', '2次面接', '最終面接'],
  PROPS_KEY: 'dotzRemindLog',
  // 🔒 送信マスタースイッチ。false の間は新システム(選考リマインド/確定・変更通知)を
  //    一切送信しない（dzMailSend_で物理ブロック）。本稼働時に true へ変更して再デプロイ。
  //    ※既存の説明会リマインド(sendMultiReminders)はこのフラグの対象外。
  SEND_ENABLED: false,
  // 送信元アドレス。saiyo_2固定。※GmailApp.sendEmailの from は「実行アカウントの
  //   送信エイリアスとして承認済み」の場合のみ有効。一致しなければ送信せず中止(誤アドレス送信防止)。
  //   最も確実なのは「saiyo_2@dotz.co.jp のアカウントでトリガーを設置」すること。
  FROM_ADDR: 'saiyo_2@dotz.co.jp',
  CC_DEFAULT: 'myoshino@dotz.co.jp,saiyo_2@dotz.co.jp',
  FROM_NAME_DEFAULT: 'DOTZ株式会社 人事担当',
  LEAD_DEFAULT: '7,3,1',
};

// 面接スケジュール列（学生IDは末尾＝既存データの並びを壊さない）
var DZ_SCHED_COLS = ['キー', 'ステージ', '氏名', 'メール', '予定日時', 'URL/詳細', '面接官', 'ステータス', '取込元', '学生ID'];
// 面接調整(コックピット)列
var DZ_COORD_COLS = ['学生ID', '氏名', '段', '確定日時', '面接官', '形式', 'URL・場所', 'ステータス', '通知', '通知日時'];

// 選考リマインド（5段共通）の既定テンプレ
var DZ_DEF_REMIND_SUBJ = '【DOTZ株式会社】{ステージ}のご案内（{日時}）';
var DZ_DEF_REMIND_BODY = '{氏名} 様\n\n' +
  'お世話になっております。DOTZ株式会社 人事担当です。\n' +
  '{ステージ}の日時が近づいてまいりましたので、改めてご案内いたします。\n\n' +
  '■ 日時：{日時}\n■ 会場／接続先：\n{URL}\n\n' +
  '当日はお時間に余裕をもってご参加ください。\n' +
  'お手数ですが、本メールをご確認のうえ「確認しました」とご返信ください。\n' +
  '万一、ご都合がつかず参加が難しくなった場合も、その旨を本メールへご返信ください。\n' +
  '※恐れ入りますが、ご返信の際は【全員返信】にてお願いいたします。\n\n' +
  '当日お会いできることを楽しみにしております。\n' +
  '────────────────────\nDOTZ株式会社 人事担当';

// 確定/変更 通知の既定テンプレ（リマインド設定が空のときのフォールバック）
var DZ_DEF_CONFIRM_SUBJ = '【DOTZ株式会社】{ステージ}の日程が確定しました（{日時}）';
var DZ_DEF_CONFIRM_BODY = '{氏名} 様\n\n' +
  'お世話になっております。DOTZ株式会社 人事担当です。\n' +
  '{ステージ}の日程が下記の通り確定いたしましたので、ご案内いたします。\n\n' +
  '■ 日時：{日時}\n■ 担当：{面接官}\n■ 会場／接続先：\n{URL}\n\n' +
  'お手数ですが、日程をご確認のうえ本メールへ「確認しました」とご返信ください。\n' +
  '万一ご都合がつかない場合も、その旨を本メールへご返信ください。\n' +
  '※恐れ入りますが、ご返信の際は【全員返信】にてお願いいたします。\n\n' +
  '当日が近づきましたら、改めてリマインドをお送りいたします。\n' +
  '────────────────────\nDOTZ株式会社 人事担当';
var DZ_DEF_CHANGE_SUBJ = '【DOTZ株式会社】{ステージ}の日程変更のお知らせ（{日時}）';
var DZ_DEF_CHANGE_BODY = '{氏名} 様\n\n' +
  'お世話になっております。DOTZ株式会社 人事担当です。\n' +
  '{ステージ}につきまして、日程を下記の通り変更させていただきましたのでお知らせいたします。\n\n' +
  '■ 新しい日時：{日時}\n■ 担当：{面接官}\n■ 会場／接続先：\n{URL}\n\n' +
  'ご不便をおかけし申し訳ございません。お手数ですが、新しい日程をご確認のうえ本メールへ「確認しました」とご返信ください。\n' +
  '万一ご都合がつかない場合も、その旨を本メールへご返信ください。\n' +
  '※恐れ入りますが、ご返信の際は【全員返信】にてお願いいたします。\n\n' +
  '引き続きどうぞよろしくお願いいたします。\n' +
  '────────────────────\nDOTZ株式会社 人事担当';

/* ====== 共通ヘルパ ====== */

function dzSheet_(name) { return SpreadsheetApp.getActiveSpreadsheet().getSheetByName(name); }
function dzEnsureSheet_(name) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName(name);
  if (!sh) sh = ss.insertSheet(name);
  return sh;
}
function dzColLetter_(n0) { var n = n0 + 1, s = ''; while (n) { var r = (n - 1) % 26; s = String.fromCharCode(65 + r) + s; n = (n - r - 1) / 26; } return s; }
function dzHeaderIndex_(headerArr, name) { for (var i = 0; i < headerArr.length; i++) { if (String(headerArr[i]).trim() === name) return i; } return -1; }

/* ====== 学生ID採番（進捗管理・右端に1列） ====== */

// 進捗管理の「学生ID」列インデックス(0始まり)を返す。無ければ右端に作成。
function dzGetOrCreateSidCol_(prog) {
  var hdr = prog.getRange(DZ.PROG_HEADER_ROW, 1, 1, prog.getMaxColumns()).getValues()[0];
  var idx = dzHeaderIndex_(hdr, DZ.SID_HEADER);
  if (idx >= 0) return idx;
  // 右端(=row10の最後の非空ヘッダの次)に作成。列挿入はせず既存列を一切ずらさない。
  var last = 0;
  for (var i = 0; i < hdr.length; i++) if (String(hdr[i]).trim() !== '') last = i;
  var target = last + 1; // 0始まり
  if (target + 1 > prog.getMaxColumns()) prog.insertColumnsAfter(prog.getMaxColumns(), (target + 1) - prog.getMaxColumns());
  prog.getRange(DZ.PROG_HEADER_ROW, target + 1).setValue(DZ.SID_HEADER)
    .setFontWeight('bold').setFontColor('#FFFFFF').setBackground('#404040');
  return target;
}

function dzAssignStudentIds_(opts) {
  opts = opts || {};
  var prog = dzSheet_(DZ.PROG);
  if (!prog) { dzToast_('進捗管理タブが見つかりません: ' + DZ.PROG); return 0; }
  var sidCol = dzGetOrCreateSidCol_(prog);
  var startRow = DZ.PROG_HEADER_ROW + 1;
  var n = prog.getLastRow() - DZ.PROG_HEADER_ROW;
  if (n <= 0) { if (opts.manual) dzToast_('対象行がありません'); return 0; }

  var ids = prog.getRange(startRow, sidCol + 1, n, 1).getValues();
  var names = prog.getRange(startRow, DZ.COL_LAST + 1, n, 2).getValues(); // 姓・名
  // 既存IDの最大連番
  var maxSeq = 0;
  for (var i = 0; i < ids.length; i++) {
    var m = String(ids[i][0] || '').match(/(\d+)\s*$/);
    if (m) maxSeq = Math.max(maxSeq, parseInt(m[1], 10));
  }
  var assigned = 0;
  for (var r = 0; r < ids.length; r++) {
    if (String(ids[r][0] || '').trim() !== '') continue;          // 既存ID保全
    var name = (String(names[r][0] || '').trim() + String(names[r][1] || '').trim());
    if (!name) continue;                                          // 氏名空はスキップ
    maxSeq++;
    var pad = ('0000' + maxSeq).slice(-4);
    ids[r][0] = DZ.SID_PREFIX + pad;
    assigned++;
  }
  if (assigned) prog.getRange(startRow, sidCol + 1, n, 1).setValues(ids);
  var msg = '学生ID採番: 新規' + assigned + '件（既存IDは保全）';
  Logger.log(msg);
  if (opts.manual) dzToast_(msg);
  return assigned;
}

// 学生ID → {name,email} のマップ（進捗管理）
function dzStudentLookup_() {
  var prog = dzSheet_(DZ.PROG);
  var map = {};
  if (!prog) return map;
  var hdr = prog.getRange(DZ.PROG_HEADER_ROW, 1, 1, prog.getMaxColumns()).getValues()[0];
  var sidCol = dzHeaderIndex_(hdr, DZ.SID_HEADER);
  if (sidCol < 0) return map;
  var startRow = DZ.PROG_HEADER_ROW + 1;
  var n = prog.getLastRow() - DZ.PROG_HEADER_ROW;
  if (n <= 0) return map;
  var data = prog.getRange(startRow, 1, n, Math.max(sidCol + 1, DZ.COL_EMAIL + 1)).getValues();
  for (var i = 0; i < data.length; i++) {
    var sid = String(data[i][sidCol] || '').trim();
    if (!sid) continue;
    var name = (String(data[i][DZ.COL_LAST] || '').trim() + ' ' + String(data[i][DZ.COL_FIRST] || '').trim()).trim();
    map[sid] = { name: name, email: String(data[i][DZ.COL_EMAIL] || '').trim() };
  }
  return map;
}

/* ====== タブ作成 ====== */

// 面接スケジュール（正規化表）。ヘッダは常にDZ_SCHED_COLSへ整合（学生ID列を後付けで足せる）。初回のみ装飾。
function dzBuildScheduleTab_() {
  var sh = dzEnsureSheet_(DZ.SCHED);
  var w = DZ_SCHED_COLS.length;
  var first = sh.getRange(1, 1, 1, w).getValues()[0];
  var firstBuild = String(first[1] || '') !== 'ステージ';
  // ヘッダ整合（既存データ行は不変・末尾の学生ID列を後付け可能に）
  sh.getRange(1, 1, 1, w).setValues([DZ_SCHED_COLS]);
  if (firstBuild) {
    sh.getRange(1, 1, 1, w).setFontWeight('bold').setFontColor('#FFFFFF').setBackground('#404040')
      .setVerticalAlignment('middle');
    sh.setFrozenRows(1);
    var widths = [60, 130, 130, 220, 150, 320, 110, 90, 70, 110];
    for (var c = 0; c < w; c++) sh.setColumnWidth(c + 1, widths[c]);
    sh.getRange(2, 5, sh.getMaxRows() - 1, 1).setNumberFormat('yyyy-mm-dd hh:mm');
    var rule = SpreadsheetApp.newDataValidation().requireValueInList(['予定', '完了', 'キャンセル'], true).build();
    sh.getRange(2, 8, sh.getMaxRows() - 1, 1).setDataValidation(rule);
    sh.getRange(1, 1, 1, w).setNote(
      '日時の正本。［選考リマインド→スケジュール取込］で進捗管理の確定日程を自動取込。' +
      '面接調整タブで確定した分は 取込元=調整 で入り、取込で上書きされません。');
  } else {
    sh.getRange(1, 1, 1, w).setFontWeight('bold').setFontColor('#FFFFFF').setBackground('#404040');
    sh.setColumnWidth(w, 110); // 学生ID列幅
  }
  return sh;
}

// 面接調整（人事主導コックピット）。build-if-empty。
function dzBuildCoordTab_() {
  var sh = dzEnsureSheet_(DZ.COORD);
  var w = DZ_COORD_COLS.length;
  var first = sh.getRange(1, 1, 1, w).getValues()[0];
  if (String(first[0] || '') === '学生ID') return sh; // 既設なら保全
  sh.clear();
  sh.getRange(1, 1, 1, w).setValues([DZ_COORD_COLS])
    .setFontWeight('bold').setFontColor('#FFFFFF').setBackground('#AF322C').setVerticalAlignment('middle');
  sh.setFrozenRows(1);
  var widths = [110, 130, 130, 150, 110, 90, 320, 90, 80, 140];
  for (var c = 0; c < w; c++) sh.setColumnWidth(c + 1, widths[c]);
  var maxR = sh.getMaxRows() - 1;
  // 確定日時 書式
  sh.getRange(2, 4, maxR, 1).setNumberFormat('yyyy-mm-dd hh:mm');
  // プルダウン
  function dv(list) { return SpreadsheetApp.newDataValidation().requireValueInList(list, true).build(); }
  sh.getRange(2, 3, maxR, 1).setDataValidation(dv(DZ.STAGE_NAMES));                  // 段
  sh.getRange(2, 6, maxR, 1).setDataValidation(dv(['オンライン', '対面']));            // 形式
  sh.getRange(2, 8, maxR, 1).setDataValidation(dv(['調整中', '確定', '変更', 'キャンセル'])); // ステータス
  sh.getRange(2, 9, maxR, 1).setDataValidation(dv(['未送信', '送信済']));              // 通知
  // 学生IDプルダウン（進捗管理のID列を参照・あれば）
  try {
    var prog = dzSheet_(DZ.PROG);
    if (prog) {
      var hdr = prog.getRange(DZ.PROG_HEADER_ROW, 1, 1, prog.getMaxColumns()).getValues()[0];
      var sidCol = dzHeaderIndex_(hdr, DZ.SID_HEADER);
      if (sidCol >= 0) {
        var rng = prog.getRange(DZ.PROG_HEADER_ROW + 1, sidCol + 1, Math.max(prog.getLastRow() - DZ.PROG_HEADER_ROW, 1), 1);
        sh.getRange(2, 1, maxR, 1).setDataValidation(
          SpreadsheetApp.newDataValidation().requireValueInRange(rng, true).build());
      }
    }
  } catch (e) { Logger.log('学生IDプルダウン設定スキップ: ' + e); }
  sh.getRange(1, 1, 1, w).setNote(
    '人事が 学生ID／段／確定日時／面接官 を入力し、ステータス=確定(または変更)→メニュー［面接を確定＆通知］。' +
    '氏名は確定時に自動補完。URL・場所が空ならリマインド設定の段別URLを使用。');
  return sh;
}

// リマインド設定（段別テンプレ＋通知テンプレ）。build-if-empty＋通知テンプレ後付け保証。
function dzBuildReminderSettingsTab_() {
  var sh = dzEnsureSheet_(DZ.SETTINGS);
  var marker = String(sh.getRange(1, 1).getValue() || '');
  if (marker.indexOf('リマインド設定') >= 0) { dzEnsureNotifyTemplates_(sh); return sh; }

  sh.clear();
  sh.getRange(1, 1, 1, 5).merge().setValue('■ 選考リマインド設定（DOTZ）')
    .setFontWeight('bold').setFontColor('#FFFFFF').setBackground('#AF322C').setFontSize(12)
    .setVerticalAlignment('middle');
  sh.setRowHeight(1, 28);

  function kv(row, label, val, note) {
    sh.getRange(row, 1).setValue(label).setFontWeight('bold').setBackground('#F2F2F2');
    sh.getRange(row, 2, 1, 4).merge().setValue(val);
    if (note) sh.getRange(row, 1).setNote(note);
  }
  kv(3, '送信タイミング（日数・カンマ区切り）', DZ.LEAD_DEFAULT, '面接の何日前に送るか。例: 7,3,1');
  kv(4, '自動送信', 'ON', 'ON=毎朝の自動送信を有効。OFFにすると手動メニューのみ。');
  kv(5, 'CC', DZ.CC_DEFAULT, 'カンマ区切りで複数指定可');
  kv(6, '差出人表示名', DZ.FROM_NAME_DEFAULT, '');

  var hr = 8;
  sh.getRange(hr, 1, 1, 5)
    .setValues([['ステージ', '有効', '件名（差込可）', '本文（差込可）', 'URL/詳細']])
    .setFontWeight('bold').setFontColor('#FFFFFF').setBackground('#404040');
  var defBody = DZ_DEF_REMIND_BODY;
  var defSubj = DZ_DEF_REMIND_SUBJ;
  var rows = [
    ['1次面接', 'ON', defSubj, defBody, 'Zoom: https://us06web.zoom.us/j/8174717383?pwd=MofbGk7LzXWeF8W2rS7gvbOaP4nlHa.1\nID: 817 471 7383 / パスコード: h7hrjy'],
    ['カジュアル面談', 'ON', defSubj, defBody, 'Zoom: https://us06web.zoom.us/j/86890662095?pwd=Fm8ME3IQ2SAyA7wW5zop4a3LWv7Zza.1\nID: 868 9066 2095 / パスコード: 824711'],
    ['1dayインターン', 'ON', defSubj, defBody, '（URL・詳細をここに記入してください）'],
    ['2次面接', 'ON', defSubj, defBody, 'Zoom: https://us06web.zoom.us/j/89302830356?pwd=GoyyEwRvBsezrTj6DS0RoId4apODwT.1\nID: 893 0283 0356'],
    ['最終面接', 'ON', defSubj, defBody, '（URL・詳細をここに記入してください）'],
    ['確定通知', 'ON', DZ_DEF_CONFIRM_SUBJ, DZ_DEF_CONFIRM_BODY, ''],
    ['変更通知', 'ON', DZ_DEF_CHANGE_SUBJ, DZ_DEF_CHANGE_BODY, ''],
  ];
  sh.getRange(hr + 1, 1, rows.length, 5).setValues(rows).setVerticalAlignment('top').setWrap(true);
  var enRule = SpreadsheetApp.newDataValidation().requireValueInList(['ON', 'OFF'], true).build();
  sh.getRange(hr + 1, 2, rows.length, 1).setDataValidation(enRule);

  sh.setColumnWidth(1, 120); sh.setColumnWidth(2, 60);
  sh.setColumnWidth(3, 280); sh.setColumnWidth(4, 360); sh.setColumnWidth(5, 320);

  var nr = hr + rows.length + 2;
  sh.getRange(nr, 1, 1, 5).merge()
    .setValue('差込タグ: {氏名} {ステージ} {日時} {URL} {面接官}　／　段の行=リマインド用、確定通知/変更通知=面接調整の確定時に使用。{URL}は各行のURL欄（段は面接調整で空なら段別Zoom）。')
    .setFontColor('#777777').setWrap(true);
  return sh;
}

// 既存のリマインド設定タブに 確定通知/変更通知 行が無ければ追記（既存編集を保全）。
function dzEnsureNotifyTemplates_(sh) {
  var data = sh.getDataRange().getValues();
  var hr = -1;
  for (var i = 0; i < data.length; i++) {
    if (String(data[i][0]).trim() === 'ステージ' && String(data[i][2]).indexOf('件名') >= 0) { hr = i; break; }
  }
  if (hr < 0) return;
  // 既存ステージ行の範囲＋既に通知行があるか
  var have = {};
  var lastRow = hr; // 1始まりに直すとhr+1
  for (var r = hr + 1; r < data.length; r++) {
    var st = String(data[r][0] || '').trim();
    if (!st) break;
    have[st] = true; lastRow = r;
  }
  var add = [];
  if (!have['確定通知']) add.push(['確定通知', 'ON', DZ_DEF_CONFIRM_SUBJ, DZ_DEF_CONFIRM_BODY, '']);
  if (!have['変更通知']) add.push(['変更通知', 'ON', DZ_DEF_CHANGE_SUBJ, DZ_DEF_CHANGE_BODY, '']);
  if (!add.length) return;
  var at = lastRow + 2; // 1始まり行番号（lastRowは0始まりindex）
  sh.getRange(at, 1, add.length, 5).setValues(add).setVerticalAlignment('top').setWrap(true);
  var enRule = SpreadsheetApp.newDataValidation().requireValueInList(['ON', 'OFF'], true).build();
  sh.getRange(at, 2, add.length, 1).setDataValidation(enRule);
}

// テンプレ文面を最新の既定に更新（有効/URLは保持）＋CC統一。文面の作り込みを反映する保守用。
function dzResetTemplates_(opts) {
  opts = opts || {};
  var sh = dzBuildReminderSettingsTab_();   // 無ければ作成・確定/変更行も保証
  dzEnsureNotifyTemplates_(sh);             // 確定通知/変更通知 行の存在を保証
  var data = sh.getDataRange().getValues();
  var hr = -1;
  for (var i = 0; i < data.length; i++) {
    if (String(data[i][0]).trim() === 'ステージ' && String(data[i][2]).indexOf('件名') >= 0) { hr = i; break; }
  }
  if (hr < 0) { if (opts.manual) dzToast_('テンプレ表が見つかりません'); return 0; }
  var updated = 0;
  for (var r = hr + 1; r < data.length; r++) {
    var name = String(data[r][0] || '').trim();
    if (!name) break;
    var subj = '', body = '';
    if (DZ.STAGE_NAMES.indexOf(name) >= 0) { subj = DZ_DEF_REMIND_SUBJ; body = DZ_DEF_REMIND_BODY; }
    else if (name === '確定通知') { subj = DZ_DEF_CONFIRM_SUBJ; body = DZ_DEF_CONFIRM_BODY; }
    else if (name === '変更通知') { subj = DZ_DEF_CHANGE_SUBJ; body = DZ_DEF_CHANGE_BODY; }
    else continue;
    // 件名(C)/本文(D) のみ更新。有効(B)・URL/詳細(E) は保持。
    sh.getRange(r + 1, 3).setValue(subj);
    sh.getRange(r + 1, 4).setValue(body).setWrap(true).setVerticalAlignment('top');
    updated++;
  }
  // CC統一（共通設定 行5）
  sh.getRange(5, 2).setValue(DZ.CC_DEFAULT);
  if (opts.manual) dzToast_('テンプレ文面を最新に更新しました（' + updated + '件・有効/URLは保持・CC統一）');
  return updated;
}

// 設定タブを読む（段別＋確定/変更テンプレを tpl[名称] で返す）
function dzSettings_() {
  var sh = dzSheet_(DZ.SETTINGS);
  if (!sh) return null;
  function g(row) { return String(sh.getRange(row, 2).getValue() || ''); }
  var lead = g(3).split(/[,、\s]+/).map(function (x) { return parseInt(x, 10); })
    .filter(function (n) { return !isNaN(n) && n >= 0; });
  var tpl = {};
  var data = sh.getDataRange().getValues();
  var hr = -1;
  for (var i = 0; i < data.length; i++) {
    if (String(data[i][0]).trim() === 'ステージ' && String(data[i][2]).indexOf('件名') >= 0) { hr = i; break; }
  }
  if (hr >= 0) {
    for (var r = hr + 1; r < data.length; r++) {
      var st = String(data[r][0] || '').trim();
      if (!st) break;
      tpl[st] = {
        enabled: String(data[r][1]).toUpperCase() !== 'OFF',
        subj: String(data[r][2] || ''),
        body: String(data[r][3] || ''),
        url: String(data[r][4] || ''),
      };
    }
  }
  return {
    leadDays: lead.length ? lead : [7, 3, 1],
    autoOn: /^(on|はい|有効|true|1)$/i.test(g(4).trim()),
    cc: g(5).trim() || DZ.CC_DEFAULT,
    fromName: g(6).trim() || DZ.FROM_NAME_DEFAULT,
    tpl: tpl,
  };
}

/* ====== 日付パース・補助（既存説明会リマインド準拠） ====== */

function dzParseEventDate_(input, timeExtra) {
  if (!input && !timeExtra) return null;
  var s = String(input || '');
  if (timeExtra) s = s + ' ' + String(timeExtra);
  var withoutEnd = s.split(/[～〜]/)[0];
  var cleaned = withoutEnd
    .replace(/\(.*?\)/g, '').replace(/（.*?）/g, '')
    .replace(/⋅/g, ' ').replace(/[\r\n]+/g, ' ')
    .replace(/\s+/g, ' ').trim();
  var re = /(\d{1,2})月\s*(\d{1,2})日\s*(午[前後])?\s*(\d{1,2})(?::(\d{2}))?/;
  var m = cleaned.match(re);
  if (!m) return null;
  var year = (new Date()).getFullYear();
  var month = parseInt(m[1], 10) - 1, day = parseInt(m[2], 10);
  var hour = m[4] ? parseInt(m[4], 10) : 0, min = m[5] ? parseInt(m[5], 10) : 0;
  var ampm = m[3] || '';
  if (ampm === '午後' && hour !== 12) hour += 12;
  if (ampm === '午前' && hour === 12) hour = 0;
  return new Date(year, month, day, hour, min, 0, 0);
}
function dzExtractUrl_(input) { var m = String(input || '').match(/https?:\/\/\S+/); return m ? m[0] : ''; }
function dzTz_() { return Session.getScriptTimeZone() || 'Asia/Tokyo'; }
function dzFmtDT_(d) { return (d instanceof Date) ? Utilities.formatDate(d, dzTz_(), 'M月d日（E） HH:mm') : ''; }
function dzMidnight_(d) { var x = new Date(d); x.setHours(0, 0, 0, 0); return x; }
function dzDaysFromToday_(d) {
  var today = dzMidnight_(new Date()), ev = dzMidnight_(d);
  return Math.round((ev.getTime() - today.getTime()) / 86400000);
}
function dzValidEmail_(s) { return /.+@.+\..+/.test(String(s || '').trim()); }
function dzFillTemplate_(tmpl, ctx) {
  return String(tmpl || '').replace(/\{([^}]+)\}/g, function (m, k) {
    k = k.trim(); return (ctx[k] != null) ? String(ctx[k]) : m;
  });
}
function dzMailSend_(to, subject, body, cfg, ccOverride) {
  if (!DZ.SEND_ENABLED) { Logger.log('🔒送信ロック中(SEND_ENABLED=false): ' + to + ' / ' + subject); return false; }
  if (!to || !subject) return false;
  var opt = { name: cfg.fromName, htmlBody: String(body || '').replace(/\n/g, '<br>') };
  var cc = (ccOverride != null) ? ccOverride : cfg.cc;
  if (cc) opt.cc = cc;
  if (DZ.FROM_ADDR) opt.from = DZ.FROM_ADDR; // 送信元を saiyo_2 に固定（実行アカウントのエイリアス要承認）
  try { GmailApp.sendEmail(to, subject, String(body || ''), opt); return true; }
  catch (e) {
    // from が承認エイリアスでない等で失敗 → 誤アドレス送信を避けるため送信中止（実行者アドレスでは送らない）
    Logger.log('dzMailSend error(送信元=' + DZ.FROM_ADDR + 'で送れず中止・実行者アドレスでは送りません): ' + e);
    return false;
  }
}
function dzSameTime_(a, b) {
  if (!(a instanceof Date) || !(b instanceof Date)) return false;
  return a.getTime() === b.getTime();
}

/* ====== 取込: 進捗管理 → 面接スケジュール（読むだけ） ====== */

function dzImportSchedule_(opts) {
  opts = opts || {};
  var prog = dzSheet_(DZ.PROG);
  if (!prog) { dzToast_('進捗管理タブが見つかりません: ' + DZ.PROG); return 0; }
  var sched = dzBuildScheduleTab_();
  var hdr = prog.getRange(DZ.PROG_HEADER_ROW, 1, 1, prog.getMaxColumns()).getValues()[0];
  var sidCol = dzHeaderIndex_(hdr, DZ.SID_HEADER); // 無ければ-1

  var pv = prog.getDataRange().getValues();
  var sv = sched.getDataRange().getValues();
  var sH = {}; for (var c = 0; c < DZ_SCHED_COLS.length; c++) sH[DZ_SCHED_COLS[c]] = c;
  // 既存（キー→{row}）＋ 旧氏名キーでも引けるよう両対応
  var existing = {};
  for (var r = 1; r < sv.length; r++) {
    var k = String(sv[r][sH['キー']] || '').trim();
    if (k) existing[k] = { row: r + 1, src: String(sv[r][sH['取込元']] || '') };
  }

  var appended = [], updated = 0, parseFail = 0;
  for (var i = DZ.PROG_HEADER_ROW; i < pv.length; i++) {
    var row = pv[i];
    var ln = String(row[DZ.COL_LAST] || '').trim(), fn = String(row[DZ.COL_FIRST] || '').trim();
    var name = (ln + ' ' + fn).trim();
    var email = String(row[DZ.COL_EMAIL] || '').trim();
    var sid = sidCol >= 0 ? String(row[sidCol] || '').trim() : '';
    if (!name) continue;
    for (var s = 0; s < DZ.STAGES.length; s++) {
      var st = DZ.STAGES[s];
      var raw = row[st.col];
      if (!raw || !String(raw).trim()) continue;
      var dt = dzParseEventDate_(raw, st.timeCol != null ? row[st.timeCol] : null);
      if (!(dt instanceof Date) || isNaN(dt.getTime())) { parseFail++; continue; }
      var sidKey = sid ? (sid + '|' + st.stage) : '';
      var nameKey = name + '|' + st.stage;
      var legacyKey = st.stage + '|' + name; // v1の旧キー形式（段|氏名）
      var key = sidKey || nameKey;
      var url = dzExtractUrl_(raw);
      // 既存を sidKey→nameKey→legacyKey の順で探す（氏名キー/旧キー→IDキー移行に対応＝重複防止）
      var ex = (sidKey && existing[sidKey]) ? existing[sidKey] : (existing[nameKey] || existing[legacyKey]);
      if (ex) {
        if (ex.src === '手動' || ex.src === '調整') continue; // コックピット/手動を保全
        sched.getRange(ex.row, sH['キー'] + 1).setValue(key);
        sched.getRange(ex.row, sH['予定日時'] + 1).setValue(dt);
        if (email) sched.getRange(ex.row, sH['メール'] + 1).setValue(email);
        if (url) sched.getRange(ex.row, sH['URL/詳細'] + 1).setValue(url);
        if (sid) sched.getRange(ex.row, sH['学生ID'] + 1).setValue(sid);
        updated++;
      } else {
        // DZ_SCHED_COLS順: キー,ステージ,氏名,メール,予定日時,URL,面接官,ステータス,取込元,学生ID
        appended.push([key, st.stage, name, email, dt, url, '', '予定', '取込', sid]);
        existing[key] = { row: -1, src: '取込' };
      }
    }
  }
  if (appended.length) sched.getRange(sched.getLastRow() + 1, 1, appended.length, DZ_SCHED_COLS.length).setValues(appended);
  var msg = '取込: 新規' + appended.length + '件 / 更新' + updated + '件' + (parseFail ? ' / 日付パース失敗' + parseFail + '件(手動補完してください)' : '');
  Logger.log(msg);
  if (opts.manual) dzToast_(msg);
  return appended.length + updated;
}

/* ====== 確定/変更: 面接調整 → 通知＋面接スケジュール反映 ====== */

function dzConfirmInterviews_(opts) {
  opts = opts || {};
  var cfg = dzSettings_();
  if (!cfg) { if (opts.manual) dzToast_('リマインド設定がありません。先に［初期セットアップ］を実行'); return 0; }
  if (!DZ.SEND_ENABLED && !opts.dry) { opts.dry = true; dzToast_('🔒送信ロック中：送信せずドライラン表示にしました'); }
  var coord = dzSheet_(DZ.COORD);
  if (!coord) { if (opts.manual) dzToast_('面接調整タブがありません。先に［初期セットアップ］を実行'); return 0; }
  var cv = coord.getDataRange().getValues();
  if (cv.length < 2) { if (opts.manual) dzToast_('面接調整に行がありません'); return 0; }
  var cH = {}; for (var c = 0; c < DZ_COORD_COLS.length; c++) cH[DZ_COORD_COLS[c]] = c;

  var sched = dzBuildScheduleTab_();
  var sv = sched.getDataRange().getValues();
  var sH = {}; for (var c2 = 0; c2 < DZ_SCHED_COLS.length; c2++) sH[DZ_SCHED_COLS[c2]] = c2;
  var schedByKey = {};
  for (var r0 = 1; r0 < sv.length; r0++) {
    var kk = String(sv[r0][sH['キー']] || '').trim();
    if (kk) schedByKey[kk] = { row: r0 + 1, dt: sv[r0][sH['予定日時']] };
  }

  var lookup = dzStudentLookup_();
  var props = PropertiesService.getDocumentProperties();
  var log = {}; try { log = JSON.parse(props.getProperty(DZ.PROPS_KEY) || '{}'); } catch (e) { log = {}; }

  var sent = 0, dryLines = [], logChanged = false;
  for (var i = 1; i < cv.length; i++) {
    var row = cv[i];
    var status = String(row[cH['ステータス']] || '').trim();
    if (status !== '確定' && status !== '変更') continue;
    if (String(row[cH['通知']] || '').trim() === '送信済') continue;

    var sid = String(row[cH['学生ID']] || '').trim();
    var stage = String(row[cH['段']] || '').trim();
    var dt = row[cH['確定日時']];
    if (!stage || !(dt instanceof Date)) continue;

    var info = lookup[sid] || {};
    var name = String(row[cH['氏名']] || '').trim() || info.name || '';
    var email = info.email || '';
    var interviewer = String(row[cH['面接官']] || '').trim();
    var url = String(row[cH['URL・場所']] || '').trim() || (cfg.tpl[stage] ? cfg.tpl[stage].url : '');

    var key = (sid ? sid : name) + '|' + stage;
    var isChange = (status === '変更');
    var tplKey = isChange ? '変更通知' : '確定通知';
    var t = cfg.tpl[tplKey] || {
      enabled: true,
      subj: isChange ? DZ_DEF_CHANGE_SUBJ : DZ_DEF_CONFIRM_SUBJ,
      body: isChange ? DZ_DEF_CHANGE_BODY : DZ_DEF_CONFIRM_BODY,
    };
    var ctx = { 氏名: name, ステージ: stage, 日時: dzFmtDT_(dt), URL: url, 面接官: interviewer };
    var subj = dzFillTemplate_(t.subj, ctx), body = dzFillTemplate_(t.body, ctx);

    if (opts.dry) {
      dryLines.push('[' + status + '] ' + stage + ' / ' + name + ' <' + email + '> 件名: ' + subj +
        (dzValidEmail_(email) ? '' : '  ← メール不正/空でスキップ'));
      continue;
    }
    if (!dzValidEmail_(email)) { Logger.log('確定スキップ(メール不正): ' + name + '/' + stage); continue; }
    if (!t.enabled) continue;
    if (!dzMailSend_(email, subj, body, cfg)) continue;

    // 面接スケジュール upsert（取込元=調整）
    var prev = schedByKey[key];
    var dtChanged = prev ? !dzSameTime_(prev.dt, dt) : true;
    var rowVals = [key, stage, name, email, dt, url, interviewer, '予定', '調整', sid];
    if (prev) {
      sched.getRange(prev.row, 1, 1, DZ_SCHED_COLS.length).setValues([rowVals]);
    } else {
      var ar = sched.getLastRow() + 1;
      sched.getRange(ar, 1, 1, DZ_SCHED_COLS.length).setValues([rowVals]);
      schedByKey[key] = { row: ar, dt: dt };
    }
    // 日時変更ならリマインドログをリセット（新日程で7/3/1前が再送される）
    if (dtChanged && log[key]) { delete log[key]; logChanged = true; }

    // コックピットに反映: 氏名補完・通知済・通知日時
    if (!String(row[cH['氏名']] || '').trim() && name) coord.getRange(i + 1, cH['氏名'] + 1).setValue(name);
    coord.getRange(i + 1, cH['通知'] + 1).setValue('送信済');
    coord.getRange(i + 1, cH['通知日時'] + 1).setValue(new Date()).setNumberFormat('yyyy-mm-dd hh:mm');
    sent++;
  }

  if (opts.dry) {
    Logger.log('=== 確定ドライラン（送信なし）対象 ' + dryLines.length + '件 ===');
    dryLines.forEach(function (l) { Logger.log(l); });
    if (opts.manual) dzToast_('確定ドライラン: 対象' + dryLines.length + '件（詳細はログ）');
    return dryLines.length;
  }
  if (logChanged) { try { props.setProperty(DZ.PROPS_KEY, JSON.stringify(log)); } catch (e) { Logger.log('log保存失敗: ' + e); } }
  if (opts.manual) dzToast_('確定/変更通知を' + sent + '件送信し、面接スケジュールに反映しました');
  return sent;
}

/* ====== 送信: 面接スケジュール → リマインド ====== */

function dzSendRemindersAuto_(opts) {
  opts = opts || {};
  var cfg = dzSettings_();
  if (!cfg) { if (opts.manual) dzToast_('リマインド設定タブがありません。先に［初期セットアップ］を実行してください'); return 0; }
  if (!opts.manual && !opts.dry && !cfg.autoOn) return 0;
  if (!DZ.SEND_ENABLED && !opts.dry) { opts.dry = true; if (opts.manual) dzToast_('🔒送信ロック中：送信せずドライラン表示にしました'); }

  var sched = dzSheet_(DZ.SCHED);
  if (!sched) { if (opts.manual) dzToast_('面接スケジュールタブがありません'); return 0; }
  var sv = sched.getDataRange().getValues();
  if (sv.length < 2) { if (opts.manual) dzToast_('面接スケジュールが空です'); return 0; }
  var sH = {}; for (var c = 0; c < DZ_SCHED_COLS.length; c++) sH[DZ_SCHED_COLS[c]] = c;

  var props = PropertiesService.getDocumentProperties();
  var log = {}; try { log = JSON.parse(props.getProperty(DZ.PROPS_KEY) || '{}'); } catch (e) { log = {}; }

  var sent = 0, dryLines = [];
  for (var i = 1; i < sv.length; i++) {
    var r = sv[i];
    var stage = String(r[sH['ステージ']] || '').trim(); if (!stage) continue;
    var status = String(r[sH['ステータス']] || '');
    if (status === 'キャンセル' || status === '完了') continue;
    var dt = r[sH['予定日時']]; if (!(dt instanceof Date)) continue;
    var du = dzDaysFromToday_(dt); if (du < 0) continue;
    if (cfg.leadDays.indexOf(du) < 0) continue;

    var t = cfg.tpl[stage];
    if (!t || !t.enabled || !t.subj || !t.body) continue;

    var key = String(r[sH['キー']] || (stage + '|' + r[sH['氏名']]));
    var done = log[key] || [];
    if (done.indexOf(du) >= 0) continue;

    var to = String(r[sH['メール']] || '').trim();
    // URL: スケジュール行のURLが空なら段別テンプレのURL
    var rowUrl = String(r[sH['URL/詳細']] || '').trim() || t.url;
    var ctx = { 氏名: r[sH['氏名']], ステージ: stage, 日時: dzFmtDT_(dt), URL: rowUrl, 面接官: r[sH['面接官']] };
    var subj = dzFillTemplate_(t.subj, ctx), body = dzFillTemplate_(t.body, ctx);

    if (opts.dry) {
      dryLines.push('[' + du + '日前] ' + stage + ' / ' + r[sH['氏名']] + ' <' + to + '> 件名: ' + subj +
        (dzValidEmail_(to) ? '' : '  ← メール不正/空でスキップ'));
      continue;
    }
    if (!dzValidEmail_(to)) continue;
    if (dzMailSend_(to, subj, body, cfg)) { done.push(du); log[key] = done; sent++; }
  }

  if (opts.dry) {
    Logger.log('=== ドライラン（送信なし）対象 ' + dryLines.length + '件 ===');
    dryLines.forEach(function (l) { Logger.log(l); });
    if (opts.manual) dzToast_('ドライラン: 対象' + dryLines.length + '件（詳細はログ）');
    return dryLines.length;
  }
  try { props.setProperty(DZ.PROPS_KEY, JSON.stringify(log)); }
  catch (e) { Logger.log('dotzRemindLog 保存失敗(次回重複送信の恐れ): ' + e); }
  if (opts.manual) dzToast_('リマインドを' + sent + '件送信しました');
  return sent;
}

/* ====== メニュー・トリガー（onOpenは新規定義しない・既存onOpenから dzMenu_(ui) を呼ぶ） ====== */

function dzToast_(msg) { try { SpreadsheetApp.getActiveSpreadsheet().toast(msg, '選考リマインド', 8); } catch (e) { Logger.log(msg); } }

function dzSetup() {
  dzBuildScheduleTab_(); dzBuildReminderSettingsTab_(); dzBuildCoordTab_();
  dzToast_('面接スケジュール／リマインド設定／面接調整 を用意しました' +
    (DZ.SEND_ENABLED ? '' : '（🔒現在メール送信はロック中＝送信されません）'));
}
function dzImportNow() { dzImportSchedule_({ manual: true }); }
// 取込行(取込元=取込)を一旦クリアして再取込（手動/調整は保全）。キー形式の重複が出たとき等の保守用。
function dzRebuildScheduleFromProg() {
  var sched = dzBuildScheduleTab_();
  var sv = sched.getDataRange().getValues();
  var sH = {}; for (var c = 0; c < DZ_SCHED_COLS.length; c++) sH[DZ_SCHED_COLS[c]] = c;
  var keep = [];
  for (var r = 1; r < sv.length; r++) {
    var src = String(sv[r][sH['取込元']] || '');
    if (src === '手動' || src === '調整') keep.push(sv[r]);
  }
  var last = sched.getLastRow();
  if (last >= 2) sched.getRange(2, 1, last - 1, DZ_SCHED_COLS.length).clearContent();
  if (keep.length) sched.getRange(2, 1, keep.length, DZ_SCHED_COLS.length).setValues(keep);
  dzImportSchedule_({});
  dzToast_('面接スケジュールを再構築しました（取込行クリア→再取込・手動/調整は保全）');
}
function dzRemindNow() { dzSendRemindersAuto_({ manual: true }); }
function dzDryRun() { dzSendRemindersAuto_({ manual: true, dry: true }); }
function dzOpenSettings() { var sh = dzBuildReminderSettingsTab_(); SpreadsheetApp.getActiveSpreadsheet().setActiveSheet(sh); }
function dzResetTemplatesNow() { dzResetTemplates_({ manual: true }); }
function dzAssignIdsNow() { dzAssignStudentIds_({ manual: true }); }
function dzOpenCoord() { var sh = dzBuildCoordTab_(); SpreadsheetApp.getActiveSpreadsheet().setActiveSheet(sh); }
function dzConfirmNow() { dzConfirmInterviews_({ manual: true }); }
function dzConfirmDryRun() { dzConfirmInterviews_({ manual: true, dry: true }); }

function dzDailyAuto() {
  try { dzImportSchedule_({}); } catch (e) { Logger.log('dzImportSchedule_ error: ' + e); }
  try { dzSendRemindersAuto_({}); } catch (e) { Logger.log('dzSendRemindersAuto_ error: ' + e); }
}
function dzInstallTrigger() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'dzDailyAuto') ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('dzDailyAuto').timeBased().everyDays(1).atHour(8).create();
  dzToast_('毎朝8時の自動取込＋リマインドを設定しました');
}

// 既存 onOpen にこの1行を足す: dzMenu_(SpreadsheetApp.getUi());
function dzMenu_(ui) {
  ui.createMenu('選考リマインド')
    .addItem('① 初期セットアップ（タブ作成）', 'dzSetup')
    .addItem('② スケジュール取込（進捗管理→面接スケジュール）', 'dzImportNow')
    .addItem('②\' 面接スケジュールを再構築（取込クリア→再取込）', 'dzRebuildScheduleFromProg')
    .addItem('③ ドライラン（送らず対象確認）', 'dzDryRun')
    .addItem('④ リマインドを今すぐ送信', 'dzRemindNow')
    .addSeparator()
    .addItem('学生IDを採番（進捗管理）', 'dzAssignIdsNow')
    .addItem('面接調整タブを開く', 'dzOpenCoord')
    .addItem('面接を確定＆通知', 'dzConfirmNow')
    .addItem('確定ドライラン（送らず確認）', 'dzConfirmDryRun')
    .addSeparator()
    .addItem('リマインド設定タブを開く', 'dzOpenSettings')
    .addItem('テンプレ文面を最新に更新（有効/URLは保持）', 'dzResetTemplatesNow')
    .addItem('毎朝8時の自動化を設定', 'dzInstallTrigger')
    .addToUi();
}
