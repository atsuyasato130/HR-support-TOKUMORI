/**
 * DOTZ 28卒 採用進捗管理 自動化 — Phase 1
 * 取込（説明会テキストワーク → ②選考進捗管理）＋ 管理ID自動採番 ＋ 002_15突合（経路・選考フロー・フリガナ）
 *
 * 設計方針:
 *  - 列はすべて「ヘッダー名」で解決（列の移動・追加に強い）
 *  - メールアドレスをキーに重複取込を防止
 *  - 経路＝002_15「流入元キッカケ」／選考フロー＝002_15「経路」カテゴリから導出
 *  - 未知のキッカケはプルダウン整理V列（経路マスター）へ自動追記
 *  - 求職者評価は行3の数式テンプレを新規行へコピー（相性%→S〜D 変換）
 *  - 既存GASは壊さない（このファイルは onOpen メニュー追加のみ）
 *
 * Phase 2（動的ステータスPD）・Phase 3（②→③ヨミ自動追記）は別途追加予定。
 */

const DOTZ = {
  SS_ID:   '1T_YJOYhR2leqz9atAV4RN2oiwL61IwJBb72rmn7ZaxI',
  SRC:     '説明会テキストワーク',     // ②取込元
  DEST:    '003_02_採用進捗管理',        // ②選考進捗管理
  MASTER:  '002_15_エントリーマスター', // 経路突合元
  PD:      'プルダウン整理',            // プルダウンマスター
  YOMI:    '003_04_ヨミ管理（2次通過〜）', // ③ヨミ管理
  PD_KIKKAKE_COL: 22,                  // V列（1始まり）= キッカケマスター
  PD_KIKKAKE_START: 5,                 // V5 から値
  // 選考フロー → プルダウン整理の該当フロー列（1始まり）。値は行5から。
  FLOW_PD_COL: { '①社長面談': 10, '②説明会兼一次面接': 12, '③説明会': 14 }, // J/L/N
  FLOW_PD_START: 5,
  FLOW_PD_LEN: 30,
  YOMI_HEADER_ROW: 2,   // ③ヘッダー行
  YOMI_TEMPLATE_ROW: 3, // ③数式テンプレ行（=最初のデータ行）
  YOMI_FORMULA_COLS: [2, 14], // B〜N（1始まり）に共有列の数式
  ID_PREFIX: '28-',
  ID_PAD: 3,
  HEADER_ROW: 2,    // ②のヘッダー行
  DATA_ROW: 3,      // ②のデータ開始行（行3に数式テンプレ）
};

// ②側ヘッダー名 : 取込元（テキストワーク）側ヘッダー名（名称が異なる場合のみ）
const SRC_ALIAS = {
  '卒業高校': '出身高校',
};

/** スプレッドシートを開いた時にメニューを追加（既存onOpenがある場合は手動で統合してください） */
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('DOTZ自動化')
    .addItem('① 説明会テキストワークから取込・採番・突合', 'importFromTextwork')
    .addToUi();
}

/**
 * 編集トリガー（Phase2/3）。既存の onEdit があれば、この中の2つの呼び出しを統合してください。
 *  - Phase2: 選考フロー変更 → ステータスのプルダウンを経路別フローに切替
 *  - Phase3: ステータス=「2次面接_実施済」→ ③ヨミ管理へ管理IDを自動追記
 */
function onEdit(e) {
  if (!e || !e.range) return;
  try { handleFlowChange_(e); } catch (err) { Logger.log('flow: ' + err); }
  try { handleStatusToYomi_(e); } catch (err) { Logger.log('yomi: ' + err); }
}

/** Phase2: 選考フロー変更時にステータスのプルダウンを切替 */
function handleFlowChange_(e) {
  const sh = e.range.getSheet();
  if (sh.getName() !== DOTZ.DEST) return;
  const idx = headerIndex_(sh.getRange(DOTZ.HEADER_ROW, 1, 1, sh.getLastColumn()).getValues()[0]);
  const flowCol = idx['選考フロー'], statusCol = idx['ステータス'];
  if (flowCol === undefined || statusCol === undefined) return;
  if (e.range.getColumn() !== flowCol + 1 || e.range.getRow() < DOTZ.DATA_ROW) return;

  const flow = String(e.range.getValue()).trim();
  const pdCol = DOTZ.FLOW_PD_COL[flow];
  const statusCell = sh.getRange(e.range.getRow(), statusCol + 1);
  if (!pdCol) { statusCell.clearDataValidations(); return; }

  const pd = e.source.getSheetByName(DOTZ.PD);
  const listRange = pd.getRange(DOTZ.FLOW_PD_START, pdCol, DOTZ.FLOW_PD_LEN, 1);
  const rule = SpreadsheetApp.newDataValidation()
    .requireValueInRange(listRange, true).setAllowInvalid(false).build();
  statusCell.setDataValidation(rule);
}

/** Phase3: ステータス=「2次面接_実施済」で③ヨミ管理へ自動追記 */
function handleStatusToYomi_(e) {
  const sh = e.range.getSheet();
  if (sh.getName() !== DOTZ.DEST) return;
  const idx = headerIndex_(sh.getRange(DOTZ.HEADER_ROW, 1, 1, sh.getLastColumn()).getValues()[0]);
  const statusCol = idx['ステータス'], idCol = idx['管理ID'];
  if (statusCol === undefined || idCol === undefined) return;
  if (e.range.getColumn() !== statusCol + 1 || e.range.getRow() < DOTZ.DATA_ROW) return;
  if (String(e.range.getValue()).trim() !== '2次面接_実施済') return;

  const id = String(sh.getRange(e.range.getRow(), idCol + 1).getValue()).trim();
  if (id) appendToYomi_(e.source, id);
}

/** ③ヨミ管理に管理IDを追記（共有列の数式はテンプレ行からコピー） */
function appendToYomi_(ss, id) {
  const yo = ss.getSheetByName(DOTZ.YOMI);
  if (!yo) return;
  const tRow = DOTZ.YOMI_TEMPLATE_ROW;
  const last = yo.getLastRow();

  // 既存チェック（A列=管理ID、テンプレ行以降）
  const ids = last >= tRow
    ? yo.getRange(tRow, 1, last - tRow + 1, 1).getValues().map(function (r) { return String(r[0]).trim(); })
    : [];
  if (ids.indexOf(id) >= 0) return;

  // 書き込み先：テンプレ行のA列が空ならそこ、なければ最終行+1
  let target;
  if (!String(yo.getRange(tRow, 1).getValue()).trim()) {
    target = tRow;
  } else {
    target = Math.max(last + 1, tRow + 1);
    // 共有列の数式をテンプレ行からコピー（$A3 等の行参照が自動調整される）
    const c0 = DOTZ.YOMI_FORMULA_COLS[0], c1 = DOTZ.YOMI_FORMULA_COLS[1];
    yo.getRange(tRow, c0, 1, c1 - c0 + 1)
      .copyTo(yo.getRange(target, c0, 1, c1 - c0 + 1), { contentsOnly: false });
  }
  yo.getRange(target, 1).setValue(id); // A列=管理ID（これをキーに数式が②から引く）
}

/** メイン：テキストワーク→②取込＋採番＋002_15突合 */
function importFromTextwork() {
  const ss = SpreadsheetApp.openById(DOTZ.SS_ID);
  const src = ss.getSheetByName(DOTZ.SRC);
  const dest = ss.getSheetByName(DOTZ.DEST);
  const master = ss.getSheetByName(DOTZ.MASTER);
  if (!src || !dest || !master) throw new Error('必要なタブが見つかりません');

  const srcVals = src.getDataRange().getValues();
  if (srcVals.length < 2) { toast_('取込元にデータがありません'); return; }
  const srcIdx = headerIndex_(srcVals[0]);

  const destHead = dest.getRange(DOTZ.HEADER_ROW, 1, 1, dest.getLastColumn()).getValues()[0];
  const destIdx = headerIndex_(destHead);

  const mVals = master.getDataRange().getValues();
  const mIdx = headerIndex_(mVals[0]);

  // 必須列の存在チェック
  ['管理ID', 'タイムスタンプ', 'メールアドレス', '経路', '選考フロー', 'ステータス'].forEach(function (k) {
    if (destIdx[k] === undefined) throw new Error('②に列が見つかりません: ' + k);
  });

  // 既存②メール集合（重複防止）＋ 採番の現在最大
  const lastRow = dest.getLastRow();
  const destData = lastRow >= DOTZ.DATA_ROW
    ? dest.getRange(DOTZ.DATA_ROW, 1, lastRow - DOTZ.DATA_ROW + 1, dest.getLastColumn()).getValues()
    : [];
  const emailCol = destIdx['メールアドレス'];
  const existing = new Set();
  destData.forEach(function (r) {
    const e = normEmail_(r[emailCol]);
    if (e) existing.add(e);
  });
  let maxId = currentMaxId_(destData, destIdx['管理ID']);

  // 002_15 メール→行マップ
  const mEmail = mIdx['メールアドレス'];
  const mMap = {};
  for (let i = 1; i < mVals.length; i++) {
    const e = normEmail_(mVals[i][mEmail]);
    if (e) mMap[e] = mVals[i];
  }

  // 取込
  const newRows = [];
  let unmatched = 0;
  for (let i = 1; i < srcVals.length; i++) {
    const sr = srcVals[i];
    const email = normEmail_(sr[srcIdx['メールアドレス']]);
    if (!email || existing.has(email)) continue;
    existing.add(email);
    maxId++;

    const row = new Array(destHead.length).fill('');
    row[destIdx['管理ID']] = DOTZ.ID_PREFIX + String(maxId).padStart(DOTZ.ID_PAD, '0');
    row[destIdx['タイムスタンプ']] = sr[srcIdx['タイムスタンプ']] || '';

    // テキストワーク→②（同名 + alias、未設定セルのみ）
    for (const destName in destIdx) {
      const srcName = SRC_ALIAS[destName] || destName;
      if (srcIdx[srcName] !== undefined && row[destIdx[destName]] === '') {
        row[destIdx[destName]] = sr[srcIdx[srcName]];
      }
    }

    // 002_15突合（経路＝キッカケ／選考フロー／フリガナ）
    const m = mMap[email];
    if (m) {
      const kikkake = m[mIdx['流入元キッカケ']] || '';
      row[destIdx['経路']] = kikkake;
      row[destIdx['選考フロー']] = flowFromRoute_(m[mIdx['経路']]);
      if (destIdx['フリガナ（姓）'] !== undefined || destIdx['フリガナ（名）'] !== undefined) {
        const furi = String(m[mIdx['フリガナ']] || '').trim().split(/\s+/);
        if (destIdx['フリガナ（姓）'] !== undefined) row[destIdx['フリガナ（姓）']] = furi[0] || '';
        if (destIdx['フリガナ（名）'] !== undefined) row[destIdx['フリガナ（名）']] = furi[1] || '';
      }
      ensureKikkakeMaster_(ss, kikkake);
    } else {
      unmatched++;
      // 突合不可：経路・選考フローは空のまま（手動確認用）
    }

    row[destIdx['ステータス']] = 'エントリー';
    newRows.push(row);
  }

  if (!newRows.length) { toast_('新規取込なし（全件取込済み）'); return; }

  const startRow = Math.max(dest.getLastRow() + 1, DOTZ.DATA_ROW);
  dest.getRange(startRow, 1, newRows.length, destHead.length).setValues(newRows);

  // 求職者評価：行3の数式テンプレを新規行へコピー（相性列を相対参照）
  const yqCol = findColBySubstr_(destIdx, '求職者評価');
  if (yqCol !== null) {
    dest.getRange(DOTZ.DATA_ROW, yqCol + 1)
      .copyTo(dest.getRange(startRow, yqCol + 1, newRows.length, 1), { contentsOnly: false });
  }

  toast_(newRows.length + '件 取込・採番完了' + (unmatched ? '（うち' + unmatched + '件は002_15突合なし＝経路要確認）' : ''));
}

/* ───────── helpers ───────── */

function headerIndex_(head) {
  const m = {};
  head.forEach(function (h, i) { const k = String(h).trim(); if (k && m[k] === undefined) m[k] = i; });
  return m;
}

function findColBySubstr_(idx, sub) {
  for (const k in idx) if (k.indexOf(sub) >= 0) return idx[k];
  return null;
}

function normEmail_(v) { return String(v == null ? '' : v).trim().toLowerCase(); }

function currentMaxId_(data, idCol) {
  let mx = 0;
  data.forEach(function (r) {
    const mt = String(r[idCol] || '').match(/^28-(\d+)$/);
    if (mt) mx = Math.max(mx, parseInt(mt[1], 10));
  });
  return mx;
}

/** 002_15の経路カテゴリ → 選考フロー（①②③） */
function flowFromRoute_(route) {
  const r = String(route || '');
  if (r.indexOf('S層') >= 0 || r.indexOf('代表面談') >= 0) return '①社長面談';
  if (r.indexOf('A層') >= 0 || r.indexOf('兼一次') >= 0) return '②説明会兼一次面接';
  return '③説明会'; // エージェント・B層・その他はすべて③
}

/** 未知キッカケをプルダウン整理V列（経路マスター）へ追記 */
function ensureKikkakeMaster_(ss, kikkake) {
  const v = String(kikkake || '').trim();
  if (!v) return;
  const pd = ss.getSheetByName(DOTZ.PD);
  if (!pd) return;
  const last = pd.getLastRow();
  const start = DOTZ.PD_KIKKAKE_START;
  const existing = last >= start
    ? pd.getRange(start, DOTZ.PD_KIKKAKE_COL, last - start + 1, 1).getValues().map(function (r) { return String(r[0]).trim(); })
    : [];
  if (existing.indexOf(v) >= 0) return;
  const writeRow = start + existing.filter(function (x) { return x; }).length;
  pd.getRange(writeRow, DOTZ.PD_KIKKAKE_COL).setValue(v);
}

function toast_(msg) {
  try { SpreadsheetApp.getActive().toast(msg, 'DOTZ自動化', 6); } catch (e) { Logger.log(msg); }
}
