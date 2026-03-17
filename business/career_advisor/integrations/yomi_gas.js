/**
 * ヨミ管理システム v3.1 — Google Apps Script
 *
 * 【設定方法】
 * 1. スプレッドシートを開く → 拡張機能 → Apps Script
 * 2. このコードを全て貼り付けて保存（Ctrl+S）
 * 3. CONFIG の SLACK_WEBHOOK_URL を変更
 * 4. 「実行」→ onOpen を実行してメニューを有効化
 * 5. 初回のみ: 「企業名ドロップダウンを更新」を実行
 *
 * 【主な変更点 v3.1】
 * - DATA_START_ROW: 4 → 5（説明行追加のため）
 * - チェックシートのonEdit対応（チェックボックス変更時に最終更新日を自動セット）
 * - J/L/P列をinputColsから削除（チェックシート参照の数式列に変更）
 * - CHECK_SHEET 追加
 */

// ============================================================
// 設定
// ============================================================
const CONFIG = {
  SLACK_WEBHOOK_URL: 'YOUR_SLACK_WEBHOOK_URL',  // 変更してください
  YOMI_SHEET:    'ヨミ台帳',
  FCST_SHEET:    'Fcst集計',
  DB_SHEET:      '企業金額',
  DASH_SHEET:    'ダッシュボード',
  CA_SHEET:      'CA別分析',
  MEMBER_SHEET:  'メンバー設定',
  CHECK_SHEET:   'チェックシート',   // ← v3.1追加
  MEMBER_DATA_ROW: 5,
  MAX_MEMBERS:   20,
  DATA_START_ROW: 5,   // ← v3.1修正: 説明行(row4)追加により5に変更
  DATA_END_ROW:  104,  // データ終了行
  DB_DATA_START:  3,
  // 列インデックス (1-indexed) ※ヨミ台帳
  COL: {
    CANDIDATE:   2,   // B: 候補者名
    COMPANY:     3,   // C: 企業名
    CA:          4,   // D: 担当CA
    FEE:         5,   // E: 単価（VLOOKUP）
    COUNT:       6,   // F: 人数
    MONTH:       7,   // G: 読み月
    STAGE:       8,   // H: 選考ステージ
    ACCEPT_YES:  10,  // J: Accept Yes数（チェックシート参照）
    MANDATORY:   12,  // L: 必須項目埋まり数（チェックシート参照）
    LAST_UPDATE: 13,  // M: 最終更新日
    CONFLICT:    14,  // N: Conflictフラグ数
    REFUND_YES:  16,  // P: Refund安全Yes数（チェックシート参照）
    REFUND_FAC:  18,  // R: RefundFactor（VLOOKUP）
    YOMI:        20,  // T: 承諾ヨミ
    YOMI_GRADE:  21,  // U: 承諾グレード
    GROSS:       24,  // X: Gross
    EXP_REFUND:  25,  // Y: Expected Refund
    NET:         26,  // Z: Net
  },
  // チェックシート 列インデックス (1-indexed)
  CHECK_COL: {
    ACCEPT_START:    5,   // E: Accept Q1
    ACCEPT_END:      14,  // N: Accept Q10
    REFUND_START:    17,  // Q: Refund R1
    REFUND_END:      21,  // U: Refund R5
    MANDATORY_START: 24,  // X: 必須 M1
    MANDATORY_END:   43,  // AQ: 必須 M20
  }
};

// ============================================================
// カスタムメニュー
// ============================================================
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('ヨミ管理')
    .addItem('企業名ドロップダウンを更新', 'updateCompanyDropdown')
    .addItem('Fcst集計を更新（日時スタンプ）', 'refreshFcstTimestamp')
    .addSeparator()
    .addItem('Slackにレポートを送る', 'sendSlackReport')
    .addSeparator()
    .addItem('計算列を保護（警告モード）', 'protectCalculatedColumns')
    .addItem('行の色を初期化', 'resetAllRowColors')
    .addSeparator()
    .addItem('メンバー変更を全シートに反映', 'applyMemberChanges')
    .addToUi();
}

// ============================================================
// メンバー設定シートからCA名を取得（動的）
// ============================================================
function getActiveMembers() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(CONFIG.MEMBER_SHEET);
  if (!sheet) return [];

  const data = sheet.getRange(
    CONFIG.MEMBER_DATA_ROW, 1,
    CONFIG.MAX_MEMBERS, 4  // A:CA名, B:目標, C:入社日, D:ステータス
  ).getValues();

  return data
    .filter(r => r[0] && String(r[0]).trim() !== '' && r[3] !== '退職')
    .map(r => ({
      name:   String(r[0]).trim(),
      target: r[1] || 0,
      status: r[3] || '在籍中',
    }));
}

// ============================================================
// メンバー変更を全シートに反映（ドロップダウン更新）
// ============================================================
function applyMemberChanges() {
  updateCompanyDropdown();

  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const yomiSheet = ss.getSheetByName(CONFIG.YOMI_SHEET);
  const members = getActiveMembers();

  if (members.length === 0) {
    SpreadsheetApp.getUi().alert('メンバー設定シートにCA名が入力されていません。');
    return;
  }

  const caNames = members.map(m => m.name);
  const rule = SpreadsheetApp.newDataValidation()
    .requireValueInList(caNames, true)
    .setAllowInvalid(true)
    .build();

  const dataRows = CONFIG.DATA_END_ROW - CONFIG.DATA_START_ROW + 1;
  yomiSheet.getRange(
    CONFIG.DATA_START_ROW, CONFIG.COL.CA,
    dataRows, 1
  ).setDataValidation(rule);

  SpreadsheetApp.getUi().alert(
    `メンバー変更を反映しました！\n` +
    `在籍メンバー: ${caNames.join(' / ')}\n\n` +
    `CA別分析・ダッシュボード・Fcst集計は自動で更新されます。`
  );
}

// ============================================================
// 企業名ドロップダウンを企業金額DBから動的生成
// ============================================================
function updateCompanyDropdown() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const dbSheet   = ss.getSheetByName(CONFIG.DB_SHEET);
  const yomiSheet = ss.getSheetByName(CONFIG.YOMI_SHEET);

  const dbData = dbSheet.getRange(
    CONFIG.DB_DATA_START, 1,
    dbSheet.getLastRow() - CONFIG.DB_DATA_START + 1, 1
  ).getValues();
  const companies = dbData.map(r => r[0]).filter(v => v && String(v).trim() !== '');

  if (companies.length === 0) {
    SpreadsheetApp.getUi().alert('企業金額DBに企業データがありません。');
    return;
  }

  const dataRows = CONFIG.DATA_END_ROW - CONFIG.DATA_START_ROW + 1;
  const rule = SpreadsheetApp.newDataValidation()
    .requireValueInList(companies, true)
    .setAllowInvalid(true)
    .build();

  yomiSheet.getRange(CONFIG.DATA_START_ROW, CONFIG.COL.COMPANY, dataRows, 1)
           .setDataValidation(rule);

  SpreadsheetApp.getUi().alert(`企業名ドロップダウンを更新しました！（${companies.length}社）`);
}

// ============================================================
// 編集時トリガー — ヨミ台帳 & チェックシート 両方に対応
// ============================================================
function onEdit(e) {
  const sheet     = e.range.getSheet();
  const sheetName = sheet.getName();

  if (sheetName === CONFIG.YOMI_SHEET) {
    _handleYomiEdit(e, sheet);
  } else if (sheetName === CONFIG.CHECK_SHEET) {
    _handleCheckEdit(e, sheet);  // ← v3.1追加
  }
}

// ── ヨミ台帳 編集ハンドラー ──
function _handleYomiEdit(e, sheet) {
  const row = e.range.getRow();
  const col = e.range.getColumn();
  if (row < CONFIG.DATA_START_ROW) return;

  // 行ハイライト（編集中の行を薄黄色に）
  const props   = PropertiesService.getScriptProperties();
  const lastRow = parseInt(props.getProperty('lastHighlightRow') || '0');
  if (lastRow >= CONFIG.DATA_START_ROW) _resetRowColor(sheet, lastRow);
  sheet.getRange(row, 1, 1, 27).setBackground('#fffde7');
  props.setProperty('lastHighlightRow', String(row));

  // 最終更新日を自動セット
  // ※ J/L/P は数式列のため直接入力されないが N/AA 等の入力時に更新
  const autoUpdateCols = [
    CONFIG.COL.CONFLICT,  // N: Conflictフラグ数（直接入力）
    14,                   // N（念のため）
    27,                   // AA: メモ
    8,                    // H: 選考ステージ
    6,                    // F: 人数
    7,                    // G: 読み月
  ];
  if (autoUpdateCols.includes(col)) {
    const updateCell = sheet.getRange(row, CONFIG.COL.LAST_UPDATE);
    if (!updateCell.getValue()) {
      updateCell.setValue(new Date());
    }
  }
}

// ── チェックシート 編集ハンドラー（v3.1追加）──
// チェックボックスをクリックしたとき、ヨミ台帳の最終更新日を自動セット
function _handleCheckEdit(e, sheet) {
  const row = e.range.getRow();
  const col = e.range.getColumn();

  // データ行のみ（ヘッダー行 1〜4 は除外）
  if (row < CONFIG.DATA_START_ROW) return;

  const cc = CONFIG.CHECK_COL;
  const isAccept    = (col >= cc.ACCEPT_START    && col <= cc.ACCEPT_END);
  const isRefund    = (col >= cc.REFUND_START    && col <= cc.REFUND_END);
  const isMandatory = (col >= cc.MANDATORY_START && col <= cc.MANDATORY_END);

  if (!isAccept && !isRefund && !isMandatory) return;

  // 対応するヨミ台帳の行（行番号は同じ）の最終更新日を更新
  const yomiSheet = sheet.getParent().getSheetByName(CONFIG.YOMI_SHEET);
  const updateCell = yomiSheet.getRange(row, CONFIG.COL.LAST_UPDATE);
  updateCell.setValue(new Date());

  // ステータスバーに更新確認を表示
  const kind = isAccept ? 'Accept' : isRefund ? 'Refund' : '必須項目';
  SpreadsheetApp.getActive().toast(
    `Row${row} の最終更新日を更新しました（${kind}）`,
    'ヨミ台帳 連携', 3
  );
}

// ============================================================
// 行色リセット（モノトーン）
// ============================================================
function _resetRowColor(sheet, row) {
  // J=10, L=12, P=16 はチェックシート参照の数式列 → inputColsから除外
  const inputCols   = new Set([2,3,4,6,7,8,13,14,27]);   // 直接入力列（白）
  const vlookupCols = new Set([5, 18]);                   // E: 単価, R: RefundFactor（薄緑）
  const checkCols   = new Set([10, 12, 16]);              // J, L, P: チェックシート参照（薄青）
  const grossCols   = new Set([24, 26]);                  // X, Z（薄グレー）
  const refundCols  = new Set([25]);                      // Y（やや濃いグレー）
  const gradeCols   = new Set([21, 23]);                  // U, W（グレード色）

  for (let col = 1; col <= 27; col++) {
    const cell = sheet.getRange(row, col);
    if (gradeCols.has(col)) {
      cell.setBackground(_gradeColor(cell.getValue()));
    } else if (checkCols.has(col)) {
      cell.setBackground('#e3f2fd');  // 薄青：チェックシートから自動反映
    } else if (vlookupCols.has(col)) {
      cell.setBackground('#e8f5e9');  // 薄緑：DBから自動反映
    } else if (grossCols.has(col)) {
      cell.setBackground('#e8e8e8');
    } else if (refundCols.has(col)) {
      cell.setBackground('#e1e1e1');
    } else if (inputCols.has(col)) {
      cell.setBackground('#ffffff');  // 白：直接入力
    } else {
      cell.setBackground('#f0f0f0');  // 薄グレー：自動計算
    }
  }
}

function _gradeColor(grade) {
  const map = { S: '#1e1e1e', A: '#464646', B: '#828282', C: '#b9b9b9', D: '#e1e1e1' };
  return map[grade] || '#ffffff';
}

function resetAllRowColors() {
  const ss    = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(CONFIG.YOMI_SHEET);
  const lastRow = sheet.getLastRow();
  for (let row = CONFIG.DATA_START_ROW; row <= lastRow; row++) {
    if (sheet.getRange(row, 2).getValue() !== '') {
      _resetRowColor(sheet, row);
    }
  }
  SpreadsheetApp.getUi().alert('行の色をリセットしました！');
}

// ============================================================
// Fcst集計タイムスタンプ更新
// ============================================================
function refreshFcstTimestamp() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  ss.getSheetByName(CONFIG.FCST_SHEET).getRange('B2').setValue(new Date());
  SpreadsheetApp.getUi().alert('集計日時を更新しました！');
}

// ============================================================
// Slack レポート送信
// ============================================================
function sendSlackReport() {
  if (CONFIG.SLACK_WEBHOOK_URL === 'YOUR_SLACK_WEBHOOK_URL') {
    SpreadsheetApp.getUi().alert(
      'SLACK_WEBHOOK_URL を設定してください。\n' +
      'スクリプト冒頭の CONFIG.SLACK_WEBHOOK_URL を編集してください。'
    );
    return;
  }

  const ss      = SpreadsheetApp.getActiveSpreadsheet();
  const fcst    = ss.getSheetByName(CONFIG.FCST_SHEET);
  const members = getActiveMembers();

  const grades    = ['S','A','B','C','D'];
  const START_ROW = 6;
  let gradeLines  = '';
  for (let i = 0; i < grades.length; i++) {
    const cnt   = fcst.getRange(START_ROW + i, 2).getValue();
    const gross = fcst.getRange(START_ROW + i, 3).getValue();
    const net   = fcst.getRange(START_ROW + i, 5).getValue();
    if (cnt > 0) {
      gradeLines += `  ${grades[i]}: ${cnt}件 / Gross ¥${_fmt(gross)} / Net ¥${_fmt(net)}\n`;
    }
  }

  // CA別（動的にメンバー設定から取得）
  const yomi    = ss.getSheetByName(CONFIG.YOMI_SHEET);
  const dataRows = CONFIG.DATA_END_ROW - CONFIG.DATA_START_ROW + 1;
  const caCol   = yomi.getRange(CONFIG.DATA_START_ROW, CONFIG.COL.CA, dataRows, 1).getValues().flat();
  const grossCol = yomi.getRange(CONFIG.DATA_START_ROW, CONFIG.COL.GROSS, dataRows, 1).getValues().flat();

  let caLines = '';
  for (const member of members) {
    let caGross = 0;
    for (let i = 0; i < caCol.length; i++) {
      if (caCol[i] === member.name && typeof grossCol[i] === 'number') caGross += grossCol[i];
    }
    if (caGross > 0) caLines += `  ${member.name}: Gross ¥${_fmt(caGross)}\n`;
  }

  const commitGross = (fcst.getRange(START_ROW, 3).getValue() || 0) + (fcst.getRange(START_ROW+1, 3).getValue() || 0);
  const commitNet   = (fcst.getRange(START_ROW, 5).getValue() || 0) + (fcst.getRange(START_ROW+1, 5).getValue() || 0);
  const totalGross  = fcst.getRange('C12').getValue() || 0;
  const totalNet    = fcst.getRange('E12').getValue() || 0;

  const dateStr = Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyy/MM/dd(E)');

  const text =
    `*週次ヨミレポート（${dateStr}）*\n` +
    `━━━━━━━━━━━━━━━━━\n` +
    `*コミット（S+A）*\n` +
    `  Gross: ¥${_fmt(commitGross)}\n` +
    `  Net:   ¥${_fmt(commitNet)}\n` +
    `━━━━━━━━━━━━━━━━━\n` +
    `*グレード別内訳*\n` + gradeLines +
    (caLines ? `━━━━━━━━━━━━━━━━━\n*CA別 Gross*\n` + caLines : '') +
    `━━━━━━━━━━━━━━━━━\n` +
    `*全体合計*\n` +
    `  Gross: ¥${_fmt(totalGross)}\n` +
    `  Net:   ¥${_fmt(totalNet)}\n` +
    `\n詳細 → ${ss.getUrl()}`;

  UrlFetchApp.fetch(CONFIG.SLACK_WEBHOOK_URL, {
    method: 'post',
    contentType: 'application/json',
    payload: JSON.stringify({ text })
  });

  SpreadsheetApp.getUi().alert('Slackにレポートを送信しました！');
}

function _fmt(n) {
  return Math.round(n || 0).toLocaleString('ja-JP');
}

// ============================================================
// 計算列の保護（警告モード）
// ============================================================
function protectCalculatedColumns() {
  const ss    = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(CONFIG.YOMI_SHEET);

  // 自動計算列 (1-indexed): A=1,E=5,I=9,J=10,K=11,L=12,O=15,P=16,Q=17,R=18,S=19,T=20,U=21,V=22,W=23,X=24,Y=25,Z=26
  const calcCols = [1, 5, 9, 10, 11, 12, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26];
  const maxRow   = sheet.getMaxRows();

  calcCols.forEach(col => {
    const range = sheet.getRange(CONFIG.DATA_START_ROW, col, maxRow - CONFIG.DATA_START_ROW + 1, 1);
    const prot  = range.protect();
    prot.setDescription(`自動計算列（${String.fromCharCode(64 + col)}列）`);
    prot.setWarningOnly(true);
  });

  SpreadsheetApp.getUi().alert('計算列に警告保護を設定しました！\n誤って編集しようとすると確認ダイアログが表示されます。');
}

// ============================================================
// 週次自動レポート（時間トリガー設定方法）
// Apps Script > トリガー > 新しいトリガー
//   関数: weeklyAutoReport
//   イベントのソース: 時間ベースのタイマー
//   時間ベースのトリガーのタイプ: 週タイマー
//   曜日と時刻: 毎週月曜日 / 午前9時〜10時
// ============================================================
function weeklyAutoReport() {
  sendSlackReport();
}

// ============================================================
// ユーティリティ: 要対応案件リストを表示
// ============================================================
function getActionItems() {
  const ss    = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(CONFIG.YOMI_SHEET);
  const lastRow = sheet.getLastRow();
  const ui    = SpreadsheetApp.getUi();

  const items = [];
  for (let row = CONFIG.DATA_START_ROW; row <= lastRow; row++) {
    const candidate = sheet.getRange(row, CONFIG.COL.CANDIDATE).getValue();
    if (!candidate) continue;

    const grade      = sheet.getRange(row, CONFIG.COL.YOMI_GRADE).getValue();
    const updateDate = sheet.getRange(row, CONFIG.COL.LAST_UPDATE).getValue();
    const conflict   = sheet.getRange(row, CONFIG.COL.CONFLICT).getValue() || 0;

    const daysSince = updateDate ? Math.floor((new Date() - new Date(updateDate)) / 86400000) : 99;
    if ((grade === 'B' && conflict >= 1) || daysSince >= 21) {
      const company = sheet.getRange(row, CONFIG.COL.COMPANY).getValue();
      items.push(`Row${row}: ${candidate} / ${company} / グレード${grade} / 更新${daysSince}日前 / Conflict${conflict}件`);
    }
  }

  if (items.length === 0) {
    ui.alert('要対応案件はありません！');
  } else {
    ui.alert(`【要対応案件 ${items.length}件】\n\n` + items.join('\n'));
  }
}
