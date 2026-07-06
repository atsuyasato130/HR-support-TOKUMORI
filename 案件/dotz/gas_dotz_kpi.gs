/**
 * DOTZ 28卒 ★KPIサマリー 自動生成（GAS / コンテナバインドスクリプト版）
 *
 * ■ 使い方（初回だけ）
 *   1. DOTZ採用シートで [拡張機能] → [Apps Script] を開く
 *   2. このファイルの中身を全部貼り付けて保存
 *   3. 関数選択で installTriggers を選び ▶実行（初回は権限承認ダイアログでOK）
 *      → 平日(月〜金)の 9時台 と 18時台 に refreshDotzKpi が自動実行される
 *   4. 手動で今すぐ更新したい時は refreshDotzKpi を ▶実行
 *
 * ■ 安全設計：書き込みは「★KPIサマリー」タブのみ。既存タブには一切触れない。
 *   ★KPIサマリーが在ればクリアして再描画、無ければ新規作成。
 */

// ───────── 設定 ─────────
var TAB = '★KPIサマリー';
var SRC_PROG = '003_000_03採用進捗管理';
var SRC_MASTER = 'エントリーマスター';
var SRC_FLOWS = {
  '代表面談': 'エントリー（スカウト：代表面談）',
  '説明会兼一次': 'エントリー（スカウト：説明会兼一次面接）',
  '説明会': 'エントリー（スカウト：説明会）',
  'エージェント': 'エントリー（エージェント）'
};
var FLOWS = ['代表面談', '説明会兼一次', '説明会', 'エージェント'];
var N_COLS = 18, N_ROWS = 190;
var TZ = 'Asia/Tokyo';

// ブランドカラー（Tokumori方式：深い赤＋黒）
var RED = '#af322c', RED_DK = '#7e1c18', INK = '#292929', WHITE = '#ffffff';
var PAPER = '#fcfbfa', ZEBRA = '#f6f4f2', HEAD_BG = '#2e2b29', PALE_RED = '#f6eae9';
var SIG_GREEN = '#d9efe1', SIG_AMBER = '#fedeca', SIG_RED = '#fbd8d5';
var BORDER = '#59544f', GRID = '#d9d7d4';
var FONT = 'Arial';

// DOTZ ファネル段階（001_04 GOALノード整合）
var NODES = ['エントリー', '説明選考会参加', '説明選考会合格', '1次面接', '1次合格',
  'カジュアル面談', '2次面接', '最終(役員)面接', 'オファー面談', '内定出し', '内定承諾', '入社'];
var GOAL = {
  'エントリー': 555, '説明選考会参加': 411, '説明選考会合格': 129, '1次面接': 115,
  '1次合格': 43, 'カジュアル面談': 39, '2次面接': null, '最終(役員)面接': 19,
  'オファー面談': null, '内定出し': 6, '内定承諾': 5, '入社': 5
};
// 接頭辞 → [到達ノードindex, active]
var STATUS_MAP = {
  'a': [1, false], 'b': [1, true], 'c': [1, false], 'd': [2, true], 'e': [2, true],
  'f': [3, true], 'g': [3, false], 'k': [4, true], 'l': [4, true], 'm': [5, true],
  'n': [5, true], 'o': [6, true], 'p': [6, false], 'q': [6, true], 'r': [6, true],
  's': [7, true], 't': [7, false], 'u': [7, true], 'v': [7, true], 'w': [8, true],
  'x': [9, true], 'y': [10, true], 'z': [10, true], 'α': [11, true], 'β': [1, true],
  'γ': [1, false]
};
var FAIL = ['a', 'c', 'g', 'p', 't', 'γ'];
// 全12段階（node0=エントリー除く 1..11）を表示する
var KEY = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11];
var KEY_H = ['説明', '合格', '1次', '1次合', 'ｶｼﾞｭ', '2次', '最終', 'ｵﾌｧ', '内定', '承諾', '入社'];
var RYUU_M = [];
var RYUU_P = [];

// ───────── トリガー設定（初回1回） ─────────
function installTriggers() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'refreshDotzKpi') ScriptApp.deleteTrigger(t);
  });
  var days = [ScriptApp.WeekDay.MONDAY, ScriptApp.WeekDay.TUESDAY,
    ScriptApp.WeekDay.WEDNESDAY, ScriptApp.WeekDay.THURSDAY, ScriptApp.WeekDay.FRIDAY];
  [9, 18].forEach(function (h) {
    days.forEach(function (d) {
      ScriptApp.newTrigger('refreshDotzKpi').timeBased()
        .onWeekDay(d).atHour(h).nearMinute(0).create();
    });
  });
  refreshDotzKpi();  // 設定直後に1回生成
  SpreadsheetApp.getActive().toast('平日9時台/18時台の自動更新を設定しました', 'KPIサマリー', 5);
}

// ───────── ユーティリティ ─────────
function colIdx_(head, needles) {
  for (var i = 0; i < head.length; i++) {
    var s = String(head[i]); var ok = true;
    for (var j = 0; j < needles.length; j++) if (s.indexOf(needles[j]) < 0) ok = false;
    if (ok) return i;
  }
  return -1;
}
function prefixOf_(status) {
  var s = String(status || '').trim();
  var p = s.indexOf('.');
  return p < 0 ? '' : s.substring(0, p).trim();
}
function normRank_(v) {
  if (!v) return '';
  var t = String(v).trim();
  var m = { 'Ｓ': 'S', 'Ａ': 'A', 'Ｂ': 'B', 'Ｃ': 'C', 'Ｄ': 'D' };
  return m[t] || t.toUpperCase();
}
function toDate_(v) {
  if (v instanceof Date) return v;
  if (!v) return null;
  var s = String(v).trim().replace(/-/g, '/');
  var m = s.match(/(\d{4})\/(\d{1,2})\/(\d{1,2})(?:\s+(\d{1,2}):(\d{1,2})(?::(\d{1,2}))?)?/);
  if (!m) return null;
  return new Date(+m[1], +m[2] - 1, +m[3], +(m[4] || 0), +(m[5] || 0), +(m[6] || 0));
}
function ym_(d) { return Utilities.formatDate(d, TZ, 'yyyy/MM'); }
function monday_(d) {
  var x = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  var wd = (x.getDay() + 6) % 7;  // Mon=0
  x.setDate(x.getDate() - wd);
  return x;
}
function md_(d) { return Utilities.formatDate(d, TZ, 'MM/dd'); }
function days_(a, b) { return Math.round((a.getTime() - b.getTime()) / 86400000); }
function pct_(n, d) { return d ? n / d : null; }
function pctstr_(v) { return v == null ? '—' : Math.round(v * 100) + '%'; }
function getCell_(r, i) { return (i >= 0 && i < r.length && r[i] != null) ? String(r[i]).trim() : ''; }

// ───────── 集計 ─────────
function aggregate_(progRows, progHead, masterRows, flowData, today) {
  var ci = {
    status: colIdx_(progHead, ['ステータス']), ts: colIdx_(progHead, ['タイムスタンプ']),
    seeker: colIdx_(progHead, ['求職者評価']), company: colIdx_(progHead, ['企業評価']),
    route: colIdx_(progHead, ['経路']), univ: colIdx_(progHead, ['大学群']),
    uniname: colIdx_(progHead, ['大学名']), rank: colIdx_(progHead, ['学生ランク']),
    email: colIdx_(progHead, ['メールアドレス']),
    sei: colIdx_(progHead, ['氏名（姓）']), mei: colIdx_(progHead, ['氏名（名）'])
  };
  var valCols = [];
  for (var i = 0; i < progHead.length; i++) {
    var h = String(progHead[i]);
    if (h.indexOf('価値観') >= 0 && h.indexOf('位') >= 0) valCols.push(i);
  }

  // フロー結合マップ（email/氏名）
  var email2flow = {}, name2flow = {}, flowEntry = {};
  FLOWS.forEach(function (f) {
    flowEntry[f] = 0;
    (flowData[f] || []).forEach(function (rw) {
      if (!rw || !String(rw[0] || '').trim()) return;
      flowEntry[f]++;
      var em = getCell_(rw, 10).toLowerCase();
      var nm = (getCell_(rw, 3) + getCell_(rw, 4)).replace(/[\s　]/g, '');
      if (em && !(em in email2flow)) email2flow[em] = f;
      if (nm && !(nm in name2flow)) name2flow[nm] = f;
    });
  });

  // people
  var people = [];
  progRows.forEach(function (r) {
    var status = getCell_(r, ci.status);
    var pf = prefixOf_(status);
    if (!pf && !getCell_(r, ci.ts)) return;
    var sm = STATUS_MAP[pf] || [null, true];
    var reached = sm[0], active = sm[1] && FAIL.indexOf(pf) < 0;
    var em = getCell_(r, ci.email).toLowerCase();
    var nm = (getCell_(r, ci.sei) + getCell_(r, ci.mei)).replace(/[\s　]/g, '');
    var vals = [];
    valCols.forEach(function (i) { var x = getCell_(r, i); if (x) vals.push(x); });
    people.push({
      prefix: pf, reached: reached, active: active,
      ts: toDate_(ci.ts >= 0 ? r[ci.ts] : null),
      seeker: normRank_(getCell_(r, ci.seeker)), company: normRank_(getCell_(r, ci.company)),
      route: getCell_(r, ci.route) || '(未設定)', univ: getCell_(r, ci.univ) || '(未設定)',
      uniname: getCell_(r, ci.uniname) || '(不明)', rank: getCell_(r, ci.rank) || '通常',
      flow: email2flow[em] || name2flow[nm] || '(不明)', values: vals
    });
  });
  var sel = people.filter(function (p) { return p.reached != null; });

  // master：母数・月次/週次/媒体/大学名
  var mTotal = 0, mMonth = 0, mWeek = 0;
  var media = {}, monthEntry = {}, weekEntry = {}, uniEntry = {};
  var wkStart = monday_(today);
  var curYM = ym_(today);
  masterRows.forEach(function (r) {
    var ts = toDate_(r[0]);
    if (!ts) return;
    mTotal++;
    if (ym_(ts) === curYM) mMonth++;
    if (ts.getTime() >= wkStart.getTime()) mWeek++;
    var k = (r[1] != null && String(r[1]).trim()) ? String(r[1]).trim() : '(不明)';
    media[k] = (media[k] || 0) + 1;
    var mk = ym_(ts); monthEntry[mk] = (monthEntry[mk] || 0) + 1;
    var wk = md_(monday_(ts)); weekEntry[wk] = (weekEntry[wk] || 0) + 1;
    var u = (r[8] != null && String(r[8]).trim()) ? String(r[8]).trim() : '(不明)';
    uniEntry[u] = (uniEntry[u] || 0) + 1;
  });

  function zeros() { var a = []; for (var i = 0; i < NODES.length; i++) a.push(0); return a; }
  function addReach(arr, reached) { for (var n = 1; n <= reached; n++) arr[n]++; }

  // 全体ファネル
  var reach = zeros(); reach[0] = mTotal;
  sel.forEach(function (p) { addReach(reach, p.reached); });

  // アクティブ
  var activePeople = sel.filter(function (p) { return p.active; });
  var activeTotal = activePeople.length;
  var activeDist = {};
  activePeople.forEach(function (p) {
    var node = p.reached ? NODES[p.reached] : '—';
    activeDist[node] = (activeDist[node] || 0) + 1;
  });

  // 平均選考日数
  var lts = sel.filter(function (p) { return p.ts; }).map(function (p) { return days_(today, p.ts); });
  var avgLt = lts.length ? Math.round(lts.reduce(function (a, b) { return a + b; }, 0) / lts.length * 10) / 10 : null;

  var offer = reach[NODES.indexOf('内定出し')];
  var accept = reach[NODES.indexOf('内定承諾')];

  // 経路別
  var routes = {};
  sel.forEach(function (p) {
    if (!routes[p.route]) routes[p.route] = zeros();
    addReach(routes[p.route], p.reached);
  });
  routes = sortObjByArr_(routes, 1);

  // 大学名別（個別）
  var uniReach = {};
  sel.forEach(function (p) { if (!uniReach[p.uniname]) uniReach[p.uniname] = zeros(); addReach(uniReach[p.uniname], p.reached); });
  var uniDetail = {};
  Object.keys(uniEntry).forEach(function (u) { var a = (uniReach[u] || zeros()).slice(); a[0] = uniEntry[u]; uniDetail[u] = a; });
  Object.keys(uniReach).forEach(function (u) { if (!(u in uniDetail)) uniDetail[u] = uniReach[u].slice(); });
  uniDetail = sliceObj_(sortObjByArr_(uniDetail, 0), 15);

  // 大学群別
  var univReach = {};
  sel.forEach(function (p) { if (!univReach[p.univ]) univReach[p.univ] = zeros(); addReach(univReach[p.univ], p.reached); });
  univReach = sortObjByArr_(univReach, 1);

  // 企業評価ランク別
  var ranks = {}; ['S', 'A', 'B', 'C', 'D'].forEach(function (x) { ranks[x] = zeros(); });
  sel.forEach(function (p) { if (ranks[p.company]) addReach(ranks[p.company], p.reached); });

  // 価値観
  var vTop3 = {}, vAll = {}, v1 = {}, v2 = {}, vOff = {};
  sel.forEach(function (p) {
    uniq_(p.values.slice(0, 3)).forEach(function (v) { vTop3[v] = (vTop3[v] || 0) + 1; });
    uniq_(p.values).forEach(function (v) {
      vAll[v] = (vAll[v] || 0) + 1;
      if (p.reached >= 3) v1[v] = (v1[v] || 0) + 1;
      if (p.reached >= 6) v2[v] = (v2[v] || 0) + 1;
      if (p.reached >= 9) vOff[v] = (vOff[v] || 0) + 1;
    });
  });
  var topVals = Object.keys(vTop3).map(function (k) { return [k, vTop3[k]]; })
    .sort(function (a, b) { return b[1] - a[1]; }).slice(0, 10);

  // 経路カテゴリ（Ag/スカウト）＆選考フロー
  var catReach = { 'エージェント': zeros(), 'スカウト': zeros() };
  var flowReach = {}; FLOWS.forEach(function (f) { flowReach[f] = zeros(); });
  sel.forEach(function (p) {
    var cat = p.flow === 'エージェント' ? 'エージェント' : 'スカウト';
    addReach(catReach[cat], p.reached);
    if (flowReach[p.flow]) addReach(flowReach[p.flow], p.reached);
  });
  var agentE = flowEntry['エージェント'] || 0, scoutE = 0;
  FLOWS.forEach(function (f) { if (f !== 'エージェント') scoutE += flowEntry[f] || 0; });
  catReach['エージェント'][0] = agentE; catReach['スカウト'][0] = scoutE;
  FLOWS.forEach(function (f) { flowReach[f][0] = flowEntry[f] || 0; });

  // 平均到達日数（各段階到達者の応募→現在）
  var avgDays = zeros().map(function () { return null; });
  for (var n = 1; n < NODES.length; n++) {
    var ds = sel.filter(function (p) { return p.ts && p.reached >= n; }).map(function (p) { return days_(today, p.ts); });
    avgDays[n] = ds.length ? Math.round(ds.reduce(function (a, b) { return a + b; }, 0) / ds.length * 10) / 10 : null;
  }

  // 月次/週次コホート（進捗ベース）
  var months = {};
  sel.forEach(function (p) { if (!p.ts) return; var k = ym_(p.ts); if (!months[k]) months[k] = zeros(); addReach(months[k], p.reached); });
  var weeks = {};
  for (var w = 0; w < 12; w++) { var wk = new Date(wkStart.getTime() - w * 7 * 86400000); weeks[md_(wk)] = zeros(); }
  sel.forEach(function (p) { if (!p.ts) return; var k = md_(monday_(p.ts)); if (weeks[k]) addReach(weeks[k], p.reached); });

  // ヨミ確度
  var yomi = { 'S 確実': 0, 'A 有力': 0, 'B 可能性': 0, 'C 様子見': 0 };
  activePeople.forEach(function (p) {
    var c = p.company;
    if (p.reached >= 9) yomi['S 確実']++;
    else if ((c === 'S' || c === 'A') && p.reached >= 5) yomi['A 有力']++;
    else if (c === 'A' || c === 'B') yomi['B 可能性']++;
    else yomi['C 様子見']++;
  });

  // 見送り/辞退
  var decline = {}; var lbl = { 'a': '辞退', 'c': '説明会_不合格', 'g': '1次_不合格', 'p': '2次_不合格', 't': '最終_不合格', 'γ': '1day_不合格' };
  sel.forEach(function (p) { if (FAIL.indexOf(p.prefix) >= 0) { var L = lbl[p.prefix] || 'その他'; decline[L] = (decline[L] || 0) + 1; } });
  decline = sortObjByVal_(decline);

  return {
    reach: reach, mTotal: mTotal, mMonth: mMonth, mWeek: mWeek,
    media: sortObjByVal_(media), activeTotal: activeTotal, activeDist: activeDist,
    avgLt: avgLt, offer: offer, accept: accept,
    routes: routes, uniDetail: uniDetail, univReach: univReach, ranks: ranks,
    vAll: vAll, vTop3: vTop3, v1: v1, v2: v2, vOff: vOff, topVals: topVals,
    catReach: catReach, flowReach: flowReach, flowEntry: flowEntry, avgDays: avgDays,
    months: months, weeks: weeks, monthEntry: monthEntry, weekEntry: weekEntry,
    yomi: yomi, decline: decline, elapsed: elapsed_(today)
  };
}

function elapsed_(today) {
  var s = new Date(2026, 3, 1), e = new Date(2027, 2, 31);
  var tot = days_(e, s), done = Math.max(0, days_(today, s));
  return tot ? Math.min(1, done / tot) : 0;
}
function paceSignal_(rate, el) {
  if (el <= 0) return ['—', null];
  var p = rate / el, t = Math.round(p * 100) / 100;
  if (p >= 0.9) return ['順調 ' + t, SIG_GREEN];
  if (p >= 0.6) return ['注意 ' + t, SIG_AMBER];
  return ['遅れ ' + t, SIG_RED];
}
function uniq_(a) { var s = {}, o = []; a.forEach(function (x) { if (!(x in s)) { s[x] = 1; o.push(x); } }); return o; }
function sortObjByVal_(o) { var k = Object.keys(o).sort(function (a, b) { return o[b] - o[a]; }); var r = {}; k.forEach(function (x) { r[x] = o[x]; }); return r; }
function sortObjByArr_(o, idx) { var k = Object.keys(o).sort(function (a, b) { return o[b][idx] - o[a][idx]; }); var r = {}; k.forEach(function (x) { r[x] = o[x]; }); return r; }
function sliceObj_(o, n) { var r = {}, k = Object.keys(o).slice(0, n); k.forEach(function (x) { r[x] = o[x]; }); return r; }

// ───────── レイアウト用 Grid ─────────
function mat_(R, C, v) { var m = []; for (var i = 0; i < R; i++) { var row = []; for (var j = 0; j < C; j++) row.push(v); m.push(row); } return m; }
function Grid_(R, C) {
  this.R = R; this.C = C;
  this.v = mat_(R, C, ''); this.bg = mat_(R, C, PAPER); this.fc = mat_(R, C, INK);
  this.fw = mat_(R, C, 'normal'); this.ha = mat_(R, C, 'left'); this.fs = mat_(R, C, 9);
  this.wr = mat_(R, C, false); this.merges = []; this.borders = [];
}
Grid_.prototype.put = function (r, c, v) { if (r < this.R && c < this.C) this.v[r][c] = (v == null ? '' : v); };
Grid_.prototype.row = function (r, c, items) { for (var i = 0; i < items.length; i++) this.put(r, c + i, items[i]); };
Grid_.prototype.fmt = function (r0, c0, r1, c1, o) {
  o = o || {};
  for (var r = r0; r < r1; r++) for (var c = c0; c < c1; c++) {
    if (r >= this.R || c >= this.C) continue;
    if (o.bg) this.bg[r][c] = o.bg;
    if (o.fc) this.fc[r][c] = o.fc;
    if (o.bold != null) this.fw[r][c] = o.bold ? 'bold' : 'normal';
    if (o.ha) this.ha[r][c] = o.ha;
    if (o.fs) this.fs[r][c] = o.fs;
    if (o.wrap) this.wr[r][c] = true;
  }
};
Grid_.prototype.merge = function (r0, c0, r1, c1) { this.merges.push([r0, c0, r1 - r0, c1 - c0]); };
Grid_.prototype.border = function (r0, c0, r1, c1, inner, color) { this.borders.push([r0, c0, r1 - r0, c1 - c0, !!inner, color || BORDER]); };

// ───────── メイン ─────────
function refreshDotzKpi() {
  var ss = SpreadsheetApp.getActive();
  var today = new Date();

  var prog = ss.getSheetByName(SRC_PROG).getDataRange().getValues();
  var progHead = prog[9] || [];          // ヘッダ=10行目
  var progRows = prog.slice(10);
  var master = ss.getSheetByName(SRC_MASTER).getDataRange().getValues().slice(1);
  var flowData = {};
  FLOWS.forEach(function (f) {
    var sh = ss.getSheetByName(SRC_FLOWS[f]);
    flowData[f] = sh ? sh.getDataRange().getValues().slice(1) : [];
  });

  var A = aggregate_(progRows, progHead, master, flowData, today);
  var g = buildLayout_(A, today);
  writeSheet_(ss, g);
}

function buildLayout_(A, today) {
  var g = new Grid_(N_ROWS, N_COLS);
  var NS = NODES.slice(1), RC = 7, full = NODES.slice();

  function sec(rr, title, c0, c1) { g.put(rr, c0 || 0, title); g.fmt(rr, c0 || 0, rr + 1, c1 || N_COLS, { fc: RED_DK, bold: true, fs: 10 }); }
  function ryuu(counts) { var o = []; for (var i = 1; i < counts.length; i++) o.push(pctstr_(pct_(counts[i], counts[i - 1]))); return o; }

  // table: header + rows。sigCol/sigMap でペース色。戻り=次行
  function table(rr, c0, header, rows, sigCol, sigMap) {
    var nc = header.length;
    g.row(rr, c0, header);
    g.fmt(rr, c0, rr + 1, c0 + nc, { bg: HEAD_BG, fc: WHITE, bold: true, fs: 8, ha: 'center', wrap: true });
    for (var ri = 0; ri < rows.length; ri++) {
      var R = rr + 1 + ri; g.row(R, c0, rows[ri]);
      var bg = (ri % 2) ? ZEBRA : PAPER;
      for (var ci = 0; ci < nc; ci++) {
        var cb = bg;
        if (sigCol != null && ci === sigCol && sigMap && sigMap[ri]) cb = sigMap[ri];
        g.fmt(R, c0 + ci, R + 1, c0 + ci + 1, { bg: cb, ha: ci === 0 ? 'left' : 'center', fs: 8, bold: (ci === 0 || ci === 1) });
      }
    }
    g.border(rr, c0, rr + 1 + rows.length, c0 + nc, true);
    return rr + 1 + rows.length;
  }

  // ===== タイトル =====
  g.put(0, 0, '■ DOTZ 28卒 採用KPIサマリー');
  g.put(0, 9, '更新 ' + Utilities.formatDate(today, TZ, 'yyyy-MM-dd HH:mm'));
  g.merge(0, 0, 1, 9); g.merge(0, 9, 1, N_COLS);
  g.fmt(0, 0, 1, 9, { bg: HEAD_BG, fc: WHITE, bold: true, fs: 13, ha: 'left' });
  g.fmt(0, 9, 1, N_COLS, { bg: HEAD_BG, fc: '#ccc7c2', fs: 9, ha: 'right' });

  // ===== KPI 9指標ストリップ ＋ 内定/承諾ハイライト箱 =====
  var r = 2, base = A.reach[0];
  var kpi = [['総エントリー', '' + base], ['今月応募', '' + A.mMonth], ['今週応募', '' + A.mWeek],
    ['説明会参加', '' + A.reach[1]], ['参加率', pctstr_(pct_(A.reach[1], base))],
    ['アクティブ', '' + A.activeTotal], ['内定承諾', '' + A.accept],
    ['承諾率', pctstr_(pct_(A.accept, A.offer))], ['平均LT日', A.avgLt == null ? '—' : '' + A.avgLt]];
  for (var i = 0; i < 9; i++) { g.put(r, i, kpi[i][0]); g.put(r + 1, i, kpi[i][1]); }
  g.fmt(r, 0, r + 1, 9, { bg: HEAD_BG, fc: WHITE, bold: true, fs: 8, ha: 'center', wrap: true });
  g.fmt(r + 1, 0, r + 3, 9, { bg: PALE_RED, fc: RED_DK, bold: true, fs: 13, ha: 'center' });
  g.merge(r + 1, 0, r + 3, 1);
  for (var i2 = 1; i2 < 9; i2++) g.merge(r + 1, i2, r + 3, i2 + 1);
  g.border(r, 0, r + 3, 9, true, RED);
  var hb = [['内定', A.offer, GOAL['内定出し']], ['承諾', A.accept, GOAL['内定承諾']]];
  for (var j = 0; j < 2; j++) {
    var c0 = 9 + j * 3;
    g.merge(r, c0, r + 1, c0 + 3); g.merge(r + 1, c0, r + 3, c0 + 3);
    g.put(r, c0, hb[j][0] + '（目標' + hb[j][2] + '）'); g.put(r + 1, c0, hb[j][1] + ' / ' + hb[j][2]);
    g.fmt(r, c0, r + 1, c0 + 3, { bg: RED, fc: WHITE, bold: true, fs: 8, ha: 'center' });
    g.fmt(r + 1, c0, r + 3, c0 + 3, { bg: PALE_RED, fc: RED_DK, bold: true, fs: 17, ha: 'center' });
    g.border(r, c0, r + 3, c0 + 3, false, RED);
  }

  // ===== 統合ファネル × 目標進捗 =====
  r = 6; sec(r, '▎選考ファネル × 目標進捗（到達/通過率/目標/達成率/ペース/着地）'); r += 1;
  var el = A.elapsed;
  var hdr = ['ステージ', '到達', '前段%', '累積%', '目標', '達成%', 'ペース', '着地'];
  var rows = [], sigMap = {};
  for (var fi = 0; fi < full.length; fi++) {
    var name = full[fi], cnt = A.reach[fi], prev = fi > 0 ? A.reach[fi - 1] : null, goal = GOAL[name];
    var g4;
    if (goal) {
      var rate = pct_(cnt, goal) || 0, ps = paceSignal_(rate, el), land = el > 0 ? Math.round(cnt / el) : cnt;
      sigMap[fi] = ps[1]; g4 = [goal, pctstr_(rate), ps[0], land];
    } else g4 = ['—', '—', '—', '—'];
    rows.push([name, cnt, prev ? pctstr_(pct_(cnt, prev)) : '—', fi > 0 ? pctstr_(pct_(cnt, base)) : '100%'].concat(g4));
  }
  r = table(r, 0, hdr, rows, 6, sigMap);
  g.put(r, 0, '※経過率' + Math.round(el * 100) + '%（〜27/3末）・ペース=達成率÷経過率・着地=実績÷経過率');
  g.fmt(r, 0, r + 1, N_COLS, { fc: INK, fs: 8 }); r += 2;

  // ===== 詳細 =====
  g.put(r, 0, '■ 詳細分析'); g.fmt(r, 0, r + 1, N_COLS, { bg: HEAD_BG, fc: WHITE, bold: true, fs: 10, ha: 'left' }); r += 2;

  function twoUp(lt, lf, rt, rf) { sec(r, lt, 0, RC - 1); sec(r, rt, RC, N_COLS); return Math.max(lf(r + 1), rf(r + 1)); }
  function funnelMaster(rr, labelH, items) {
    var rs = items.map(function (it) {
      var counts = [it[2]]; KEY.forEach(function (k) { counts.push(it[1] ? it[1][k] : 0); });
      return [it[0]].concat(counts);
    });
    if (!rs.length) rs = [['(なし)'].concat(blank_(KEY.length + 1))];
    return table(rr, 0, [labelH, '母数'].concat(KEY_H), rs);
  }
  function funnelProg(rr, labelH, items) {
    var rs = items.map(function (it) {
      var counts = KEY.map(function (k) { return it[1][k]; });
      return [it[0]].concat(counts);
    });
    if (!rs.length) rs = [['(なし)'].concat(blank_(KEY.length))];
    return table(rr, 0, [labelH].concat(KEY_H), rs);
  }

  // ⑤ 媒体別 ｜ ⑨ ヨミ
  r = twoUp('⑤ 媒体別エントリー(母数=ｴﾝﾄﾘｰﾏｽﾀｰ)', function (rr) {
    var tot = A.mTotal || 1, rs = Object.keys(A.media).map(function (m) { return [m, A.media[m], pctstr_(A.media[m] / tot)]; });
    return table(rr, 0, ['媒体', '応募', '構成比'], rs);
  }, '⑨ ヨミ確度別(企業評価×ステータス)', function (rr) {
    var rs = Object.keys(A.yomi).map(function (k) { return [k, A.yomi[k]]; });
    return table(rr, RC, ['ヨミ確度', '人数'], rs);
  }) + 1;

  // ⑩ 見送り ｜ ⑪ アクティブ現在地
  r = twoUp('⑩ 見送り・辞退 内訳', function (rr) {
    var td = 0; Object.keys(A.decline).forEach(function (k) { td += A.decline[k]; }); td = td || 1;
    var rs = Object.keys(A.decline).map(function (k) { return [k, A.decline[k], pctstr_(A.decline[k] / td)]; });
    if (!rs.length) rs = [['(なし)', '', '']];
    return table(rr, 0, ['見送り/辞退', '件数', '比'], rs);
  }, '⑪ アクティブ現在地分布', function (rr) {
    var ks = Object.keys(A.activeDist).sort(function (a, b) { return (NODES.indexOf(a) < 0 ? 99 : NODES.indexOf(a)) - (NODES.indexOf(b) < 0 ? 99 : NODES.indexOf(b)); });
    var rs = ks.map(function (k) { return [k, A.activeDist[k]]; });
    if (!rs.length) rs = [['(なし)', '']];
    return table(rr, RC, ['現フェーズ', 'ｱｸﾃｨﾌﾞ数'], rs);
  }) + 1;

  // ⑧ 価値観
  sec(r, '⑧ 価値観 × 到達段階（全10順位・段階別保有＋寄与率）');
  rows = A.topVals.map(function (t) {
    var v = t[0], allc = A.vAll[v] || 0, off = A.vOff[v] || 0;
    return [v, allc, t[1], A.v1[v] || 0, A.v2[v] || 0, off, pctstr_(pct_(off, allc))];
  });
  if (!rows.length) rows = [['(なし)'].concat(blank_(6))];
  r = table(r + 1, 0, ['価値観', '全体保有', '重視(上位3)', '1次到達', '2次到達', '内定者', '寄与率'], rows) + 1;

  // ④ 経路別
  sec(r, '④ 経路別 ファネル＆歩留（進捗管理の経路／母数=説明会参加）');
  r = funnelProg(r + 1, '経路', Object.keys(A.routes).map(function (k) { return [k, A.routes[k]]; })) + 1;

  // ④b 経路カテゴリ別 ＋平均到達日
  sec(r, '④b 経路カテゴリ別 選考ファネル（総/エージェント/スカウト・平均到達日）');
  var cat = A.catReach, agE = cat['エージェント'][0] || 1, scE = cat['スカウト'][0] || 1;
  var totE = (cat['エージェント'][0] + cat['スカウト'][0]) || 1;
  rows = [];
  for (var ci2 = 0; ci2 < full.length; ci2++) {
    var tot = cat['エージェント'][ci2] + cat['スカウト'][ci2], ad = ci2 > 0 ? A.avgDays[ci2] : 0;
    rows.push([full[ci2], tot, pctstr_(pct_(tot, totE)), ad == null ? '—' : ad,
      cat['エージェント'][ci2], pctstr_(pct_(cat['エージェント'][ci2], agE)),
      cat['スカウト'][ci2], pctstr_(pct_(cat['スカウト'][ci2], scE))]);
  }
  r = table(r + 1, 0, ['ステージ', '総数', '総歩留', '平均到達日', 'Ag数', 'Ag歩留', 'ｽｶｳﾄ数', 'ｽｶｳﾄ歩留'], rows) + 1;

  // ④c 選考フロー別
  sec(r, '④c 選考フロー別 ファネル＆歩留（エントリー元フォーム別／母数=各フォーム）');
  r = funnelMaster(r + 1, '選考フロー', FLOWS.map(function (f) { return [f, A.flowReach[f], A.flowEntry[f] || 0]; })) + 1;

  // ⑥ 大学群別
  sec(r, '⑥ 大学群別 ファネル＆歩留（進捗管理／母数=説明会参加）');
  r = funnelProg(r + 1, '大学群', Object.keys(A.univReach).map(function (k) { return [k, A.univReach[k]]; })) + 1;

  // ⑦ 企業評価ランク別
  sec(r, '⑦ 企業評価ランク別 ファネル＆歩留（進捗管理／母数=説明会参加）');
  r = funnelProg(r + 1, '評価', ['S', 'A', 'B', 'C', 'D'].map(function (k) { return [k, A.ranks[k]]; })) + 1;

  // ② 月次
  sec(r, '② 月次KPI推移（母数=ｴﾝﾄﾘｰﾏｽﾀｰ／説明会以降=進捗管理・応募月別）');
  var mks = uniq_(Object.keys(A.months).concat(Object.keys(A.monthEntry))).sort();
  r = funnelMaster(r + 1, '応募月', mks.map(function (mk) { return [mk, A.months[mk], A.monthEntry[mk] || 0]; })) + 1;

  // ③ 週次
  sec(r, '③ 週次KPI推移（直近12週・月曜起算／母数=ｴﾝﾄﾘｰﾏｽﾀｰ）');
  r = funnelMaster(r + 1, '週(月)', Object.keys(A.weeks).map(function (wk) { return [wk, A.weeks[wk], A.weekEntry[wk] || 0]; })) + 1;

  // ⑫ 大学別個別
  sec(r, '⑫ 大学別 ファネル＆歩留（個別大学名・エントリー降順／母数=ｴﾝﾄﾘｰﾏｽﾀｰ）');
  r = funnelMaster(r + 1, '大学名', Object.keys(A.uniDetail).map(function (u) { return [u, A.uniDetail[u], A.uniDetail[u][0]]; })) + 1;

  return g;
}

function blank_(n) { var a = []; for (var i = 0; i < n; i++) a.push(''); return a; }

// ───────── 書き込み（★KPIサマリーのみ） ─────────
function writeSheet_(ss, g) {
  var sh = ss.getSheetByName(TAB);
  if (!sh) {
    sh = ss.insertSheet(TAB, 0);
  } else {
    sh.clear();
    var mg = sh.getRange(1, 1, sh.getMaxRows(), sh.getMaxColumns()).getMergedRanges();
    mg.forEach(function (m) { m.breakApart(); });
  }
  if (sh.getMaxColumns() < N_COLS) sh.insertColumnsAfter(sh.getMaxColumns(), N_COLS - sh.getMaxColumns());
  if (sh.getMaxRows() < N_ROWS) sh.insertRowsAfter(sh.getMaxRows(), N_ROWS - sh.getMaxRows());
  sh.setHiddenGridlines(true);

  var rng = sh.getRange(1, 1, N_ROWS, N_COLS);
  rng.setValues(g.v).setBackgrounds(g.bg).setFontColors(g.fc).setFontWeights(g.fw)
    .setHorizontalAlignments(g.ha).setFontSizes(g.fs).setWraps(g.wr)
    .setFontFamily(FONT).setVerticalAlignment('middle');

  g.merges.forEach(function (m) { sh.getRange(m[0] + 1, m[1] + 1, m[2], m[3]).merge(); });
  g.borders.forEach(function (b) {
    var R = sh.getRange(b[0] + 1, b[1] + 1, b[2], b[3]);
    R.setBorder(true, true, true, true, false, false, b[5], SpreadsheetApp.BorderStyle.SOLID);
    if (b[4]) R.setBorder(null, null, null, null, true, true, GRID, SpreadsheetApp.BorderStyle.SOLID);
  });

  // 列幅
  for (var c = 1; c <= N_COLS; c++) sh.setColumnWidth(c, (c === 1 || c === 8) ? 100 : 46);

  // 先頭へ移動
  ss.setActiveSheet(sh); ss.moveActiveSheet(1);
}
