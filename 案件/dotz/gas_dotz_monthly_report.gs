/**
 * DOTZ 28卒 採用 月次レポート（Google ドキュメント）生成 — 本番bound用
 *
 * ■ 役割：production シートの生データを集計し、経営報告粒度の月次レポートを
 *   Google ドキュメントとして生成する（毎月新規Doc・生成のみ・手動共有）。
 * ■ 依存：同じプロジェクト内の gas_dotz_kpi.gs（aggregate_ / NODES / GOAL /
 *   SRC_PROG / SRC_MASTER / SRC_FLOWS / FLOWS / TZ / colIdx_ / prefixOf_ /
 *   normRank_ / STATUS_MAP）を流用する。
 * ■ Gemini非依存（ルールベース所感）。グラフは QuickChart 画像。
 * ■ メニュー：onOpen に「📝 月間レポートDoc(前月)/(月指定)」を追加して実行。
 */

var MR_TITLE_PREFIX = 'DOTZ 28卒 採用 月次レポート ';
// 経営ファネル表示段階（中間の薄い段は圧縮）
var MR_FUNNEL = ['エントリー', '説明選考会参加', '1次面接', 'カジュアル面談',
  '2次面接', '最終(役員)面接', '内定出し', '内定承諾'];
var MR_RED = '#af322c', MR_INK = '#292929', MR_GRAY = '#8a8a8a';
var MR_PALETTE = ['#af322c', '#404040', '#9b9b9b', '#c98b87', '#5e5e5e', '#d8c2c0'];

// ───────── メニューエントリ ─────────
function generateMonthlyDocPrevMonth() {
  var d = new Date();
  var prev = new Date(d.getFullYear(), d.getMonth() - 1, 1);
  buildMonthlyDoc_(Utilities.formatDate(prev, TZ, 'yyyy/MM'));
}

function generateMonthlyDocForMonth() {
  var ui = SpreadsheetApp.getUi();
  var res = ui.prompt('月間レポート生成',
    '対象月を yyyy/MM で入力（例 2026/06）', ui.ButtonSet.OK_CANCEL);
  if (res.getSelectedButton() !== ui.Button.OK) return;
  var period = res.getResponseText().trim();
  if (!/^\d{4}\/\d{2}$/.test(period)) { ui.alert('形式が不正です（yyyy/MM）'); return; }
  buildMonthlyDoc_(period);
}

// ───────── データ取得（refreshDotzKpi と同じ読み込み） ─────────
function mrLoadAggregate_() {
  var ss = SpreadsheetApp.getActive();
  var today = new Date();
  var prog = ss.getSheetByName(SRC_PROG).getDataRange().getValues();
  var progHead = prog[9] || [];
  var progRows = prog.slice(10);
  var master = ss.getSheetByName(SRC_MASTER).getDataRange().getValues().slice(1);
  var flowData = {};
  FLOWS.forEach(function (f) {
    var sh = ss.getSheetByName(SRC_FLOWS[f]);
    flowData[f] = sh ? sh.getDataRange().getValues().slice(1) : [];
  });
  var A = aggregate_(progRows, progHead, master, flowData, today);
  A.seekerRanks = mrSeekerRanks_(progRows, progHead);
  A.today = today;
  return A;
}

// 求職者評価ランク別の到達分布（aggregate_ の ranks は企業評価。求職者評価を補完）
function mrSeekerRanks_(progRows, progHead) {
  var ciStatus = colIdx_(progHead, ['ステータス']);
  var ciSeeker = colIdx_(progHead, ['求職者評価']);
  var sr = {}; ['S', 'A', 'B', 'C', 'D'].forEach(function (x) {
    sr[x] = []; for (var i = 0; i < NODES.length; i++) sr[x].push(0);
  });
  progRows.forEach(function (r) {
    var status = (ciStatus >= 0 && ciStatus < r.length) ? String(r[ciStatus] || '') : '';
    var sm = STATUS_MAP[prefixOf_(status)];
    if (!sm || sm[0] == null) return;
    var reached = sm[0];
    var sk = normRank_((ciSeeker >= 0 && ciSeeker < r.length) ? r[ciSeeker] : '');
    if (sr[sk]) for (var n = 1; n <= reached; n++) sr[sk][n]++;
  });
  return sr;
}

// ───────── 補助 ─────────
function mrIdx_(reach, name) { return reach[NODES.indexOf(name)]; }
function mrPct_(n, d) { return d ? (n / d) : null; }
function mrPctStr_(n, d) { var r = mrPct_(n, d); return r == null ? '—' : Math.round(r * 100) + '%'; }
function mrLanding_(n, el) { return (el && el > 0) ? Math.round(n / el) : null; }

function mrRuleInsight_(A) {
  var reach = A.reach, el = A.elapsed, lines = [];
  var gEntry = GOAL['エントリー'] || 0, gAcc = GOAL['内定承諾'] || 0;
  // ボトルネック（母数3以上の隣接遷移で最低通過率）
  var worst = null;
  for (var i = 1; i < MR_FUNNEL.length; i++) {
    var cur = mrIdx_(reach, MR_FUNNEL[i]), prev = mrIdx_(reach, MR_FUNNEL[i - 1]);
    if (prev < 3) continue;
    var rate = cur / prev;
    if (!worst || rate < worst[2]) worst = [MR_FUNNEL[i - 1], MR_FUNNEL[i], rate];
  }
  if (worst) lines.push('・最大のボトルネックは「' + worst[0] + '→' + worst[1] +
    '」通過率 ' + Math.round(worst[2] * 100) + '%。次の打ち手の優先度トップ。');
  if (gAcc && el > 0) {
    var fc = mrLanding_(A.accept, el);
    var v = fc >= gAcc ? '目標到達ペース' : '目標未達ペース';
    lines.push('・現ペースの年度末着地（線形・参考）：内定承諾 約' + fc +
      '名 ／ 目標 ' + gAcc + '名＝' + v + '。');
  }
  var mk = Object.keys(A.media)[0];
  if (mk) lines.push('・流入は「' + mk + '」が最多（' + A.media[mk] + '件 / 全' +
    A.mTotal + '件）。費用対効果の観点で配分継続の妥当性を確認。');
  if (!lines.length) lines.push('・データ蓄積中。次月以降に通過率・着地の傾向を評価する。');
  return lines;
}

// ───────── QuickChart ─────────
function mrChartImg_(config, w, h) {
  try {
    var payload = JSON.stringify({
      chart: config, width: w, height: h,
      backgroundColor: 'white', devicePixelRatio: 2
    });
    var res = UrlFetchApp.fetch('https://quickchart.io/chart/create', {
      method: 'post', contentType: 'application/json',
      payload: payload, muteHttpExceptions: true
    });
    var j = JSON.parse(res.getContentText());
    if (j && j.success && j.url) {
      return UrlFetchApp.fetch(j.url, { muteHttpExceptions: true }).getBlob();
    }
    Logger.log('QuickChart 応答に url 無し: ' + res.getContentText());
  } catch (e) { Logger.log('QuickChart 失敗: ' + e); }
  return null;
}

// 朱の濃淡（ファネル段別）
var MR_SHADES = ['#8f231e', '#af322c', '#c24a40', '#d06e64', '#dd9189', '#e8b4ae', '#f1d5d1'];
function mrShades_(n) { var o = []; for (var i = 0; i < n; i++) o.push(MR_SHADES[Math.min(i, MR_SHADES.length - 1)]); return o; }
// 横棒/縦棒 共通の磨いたoptions（v2・データラベル/罫線なし/黒×朱）
function mrBarOpts_(horizontal) {
  var valAxis = { gridLines: { display: false, drawBorder: false }, ticks: { display: false, beginAtZero: true } };
  var catAxis = { gridLines: { display: false, drawBorder: false }, ticks: { fontColor: MR_INK, fontSize: 11 } };
  return {
    legend: { display: false },
    plugins: { datalabels: { anchor: 'end', align: horizontal ? 'right' : 'top', color: MR_INK, font: { weight: 'bold', size: 11 } } },
    scales: horizontal ? { xAxes: [valAxis], yAxes: [catAxis] } : { xAxes: [catAxis], yAxes: [valAxis] },
    layout: { padding: { right: horizontal ? 30 : 8, top: horizontal ? 4 : 18 } }
  };
}
function mrFunnelChart_(reach) {
  var labels = MR_FUNNEL.slice(), data = labels.map(function (n) { return mrIdx_(reach, n); });
  return {
    type: 'horizontalBar',
    data: { labels: labels, datasets: [{ data: data, backgroundColor: mrShades_(labels.length) }] },
    options: mrBarOpts_(true)
  };
}
function mrTrendChart_(monthEntry) {
  var keys = Object.keys(monthEntry).sort();
  return {
    type: 'bar',
    data: { labels: keys, datasets: [{ data: keys.map(function (k) { return monthEntry[k]; }), backgroundColor: MR_RED }] },
    options: mrBarOpts_(false)
  };
}
function mrDoughnutChart_(media) {
  var keys = Object.keys(media).slice(0, 6);
  return {
    type: 'doughnut',
    data: { labels: keys, datasets: [{ data: keys.map(function (k) { return media[k]; }), backgroundColor: MR_PALETTE, borderColor: '#ffffff', borderWidth: 2 }] },
    options: {
      cutoutPercentage: 58,
      legend: { position: 'right', labels: { fontColor: MR_INK, fontSize: 11 } },
      plugins: { datalabels: { color: '#ffffff', font: { weight: 'bold', size: 12 } } }
    }
  };
}
function mrUnivChart_(univReach) {
  var keys = Object.keys(univReach).slice(0, 6);
  return {
    type: 'horizontalBar',
    data: { labels: keys, datasets: [{ data: keys.map(function (k) { return univReach[k][1]; }), backgroundColor: MR_RED }] },
    options: mrBarOpts_(true)
  };
}
function mrValuesChart_(topVals) {
  var items = topVals.slice(0, 8);
  return {
    type: 'horizontalBar',
    data: { labels: items.map(function (x) { return x[0]; }), datasets: [{ data: items.map(function (x) { return x[1]; }), backgroundColor: MR_RED }] },
    options: mrBarOpts_(true)
  };
}

// ───────── Doc 組み立て ─────────
function buildMonthlyDoc_(period) {
  var A = mrLoadAggregate_();
  var reach = A.reach, el = A.elapsed, today = A.today;
  var y = parseInt(period.substring(0, 4), 10), m = parseInt(period.substring(5, 7), 10);
  var curEntry = A.monthEntry[period] || 0;
  var prevD = new Date(y, m - 2, 1); // 前月
  var prevKey = Utilities.formatDate(prevD, TZ, 'yyyy/MM');
  var prevEntry = A.monthEntry[prevKey] || 0;
  var delta = curEntry - prevEntry;

  var title = MR_TITLE_PREFIX + period;
  var doc = DocumentApp.create(title);
  var body = doc.getBody();
  body.appendParagraph(title).setHeading(DocumentApp.ParagraphHeading.TITLE);
  body.appendParagraph('作成日: ' + Utilities.formatDate(today, TZ, 'yyyy/MM/dd') +
    '　／　対象: ' + period + '（応募月ベース）')
    .editAsText().setForegroundColor(MR_GRAY).setFontSize(9);

  // 0) エグゼクティブサマリー
  body.appendParagraph('エグゼクティブサマリー').setHeading(DocumentApp.ParagraphHeading.HEADING2);
  var gEntry = GOAL['エントリー'] || 0, gAcc = GOAL['内定承諾'] || 0;
  var entAch = gEntry ? Math.round(reach[0] / gEntry * 100) + '%' : '—';
  body.appendParagraph('・当月（' + period + '）エントリー ' + curEntry + '件（前月比 ' +
    (delta >= 0 ? '+' : '') + delta + '）。累計 ' + reach[0] + '件 ／ 目標 ' + gEntry +
    '（達成率 ' + entAch + '）。').setFontSize(10.5);
  body.appendParagraph('・選考進捗：説明会参加 ' + mrIdx_(reach, '説明選考会参加') +
    ' → 1次 ' + mrIdx_(reach, '1次面接') + ' → 2次 ' + mrIdx_(reach, '2次面接') +
    ' → 内定 ' + A.offer + ' → 承諾 ' + A.accept + '（選考中アクティブ ' +
    A.activeTotal + '名 ／ 平均選考日数 ' + (A.avgLt != null ? A.avgLt : '—') + '日）。').setFontSize(10.5);
  mrRuleInsight_(A).forEach(function (line) { body.appendParagraph(line).setFontSize(10.5); });

  // 0b) 対目標サマリー（全段階）
  body.appendParagraph('対目標サマリー（全選考段階・着地予測）').setHeading(DocumentApp.ParagraphHeading.HEADING2);
  var stages = ['エントリー', '説明選考会参加', '説明選考会合格', '1次面接', '1次合格',
    'カジュアル面談', '2次面接', '最終(役員)面接', '内定出し', '内定承諾'];
  var t1 = [['選考段階', '実績', '前段比', '目標', '達成率', '着地予測*']];
  stages.forEach(function (name) {
    var i = NODES.indexOf(name), n = reach[i];
    var prev = i > 0 ? reach[i - 1] : null;
    var step = prev ? Math.round(n / prev * 100) + '%' : '—';
    var goal = GOAL[name];
    var ach = goal ? Math.round(n / goal * 100) + '%' : '—';
    var fc = mrLanding_(n, el);
    t1.push([name, String(n), step, goal != null ? String(goal) : '—', ach, fc != null ? String(fc) : '—']);
  });
  mrTable_(body, t1);
  body.appendParagraph('*着地予測＝実績 ÷ 年度経過率（線形仮定）。採用の季節性は考慮しない参考値。')
    .editAsText().setForegroundColor(MR_GRAY).setFontSize(8.5);

  // 1) KPIサマリー
  body.appendParagraph('KPI サマリー').setHeading(DocumentApp.ParagraphHeading.HEADING2);
  var setsu = mrIdx_(reach, '説明選考会参加');
  var accRate = mrPct_(A.accept, reach[0]);
  mrTable_(body, [
    ['指標', '値', '補足'],
    [period + ' エントリー', curEntry + ' 件', '前月比 ' + (delta >= 0 ? '+' : '') + delta],
    ['累計エントリー（母数）', reach[0] + ' 件', ''],
    ['説明選考会 参加', setsu + ' 件', reach[0] ? '参加率 ' + Math.round(setsu / reach[0] * 100) + '%' : ''],
    ['1次面接 到達', mrIdx_(reach, '1次面接') + ' 件', ''],
    ['2次面接 到達', mrIdx_(reach, '2次面接') + ' 件', ''],
    ['内定出し', A.offer + ' 件', '目標 ' + GOAL['内定出し']],
    ['内定承諾', A.accept + ' 件', '目標 ' + GOAL['内定承諾']],
    ['承諾率', accRate != null ? (Math.round(accRate * 1000) / 10) + '%' : '—', '対累計エントリー'],
    ['アクティブ（選考中）', A.activeTotal + ' 名', ''],
    ['平均選考日数', (A.avgLt != null ? A.avgLt : '—') + ' 日', '']
  ]);

  // 2) 担当者コメント（編集可）
  body.appendParagraph('担当者コメント（編集してください）').setHeading(DocumentApp.ParagraphHeading.HEADING2);
  mrRuleInsight_(A).forEach(function (line) { body.appendParagraph(line).setFontSize(10.5); });
  body.appendParagraph('◇ 総評：').editAsText().setBold(true);
  body.appendParagraph('（ここに今月の総評・次月の打ち手を記入）')
    .editAsText().setForegroundColor(MR_GRAY);

  // 3) 選考ファネル
  body.appendParagraph('選考ファネル（累計到達・対目標）').setHeading(DocumentApp.ParagraphHeading.HEADING2);
  mrAppendImg_(body, mrFunnelChart_(reach), 520, 320, 380, 234);
  var t2 = [['段階', '到達', '前段比', '累計比', '目標', '達成率', 'ペース']];
  for (var i2 = 0; i2 < MR_FUNNEL.length; i2++) {
    var nm = MR_FUNNEL[i2], idx = NODES.indexOf(nm), cur = reach[idx];
    var prev = i2 > 0 ? mrIdx_(reach, MR_FUNNEL[i2 - 1]) : null;
    var step = prev ? Math.round(cur / prev * 100) + '%' : '—';
    var cum = reach[0] ? Math.round(cur / reach[0] * 100) + '%' : '—';
    var goal = GOAL[nm], ach = goal ? Math.round(cur / goal * 100) + '%' : '—', pace = '—';
    if (goal && el > 0) { var p = (cur / goal) / el; pace = (p >= 0.9 ? '順調' : p >= 0.6 ? '注意' : '遅れ') + ' ' + (Math.round(p * 100) / 100); }
    t2.push([nm, String(cur), step, cum, goal != null ? String(goal) : '—', ach, pace]);
  }
  mrTable_(body, t2);

  // 3b) 経路別の質
  body.appendParagraph('経路別の質（通過率）').setHeading(DocumentApp.ParagraphHeading.HEADING2);
  var t3 = [['経路', '説明会', '1次', '2次', '承諾', '説明会→1次']];
  var rk = Object.keys(A.routes).slice(0, 6);
  rk.forEach(function (route) {
    var arr = A.routes[route];
    var s = arr[NODES.indexOf('説明選考会参加')], f1 = arr[NODES.indexOf('1次面接')];
    t3.push([route, String(s), String(f1), String(arr[NODES.indexOf('2次面接')]),
      String(arr[NODES.indexOf('内定承諾')]), mrPctStr_(f1, s)]);
  });
  mrTable_(body, t3);

  // 3c) 選考評価の分布
  body.appendParagraph('選考評価の分布（評価ランク別の人数と到達段階）').setHeading(DocumentApp.ParagraphHeading.HEADING2);
  body.appendParagraph('企業評価（当社が応募者をどう評価したか）').editAsText().setBold(true).setFontSize(10);
  mrTable_(body, mrEvalTable_(A.ranks, '企業評価'));
  body.appendParagraph('求職者評価（応募者の当社への評価＝相性）').editAsText().setBold(true).setFontSize(10);
  mrTable_(body, mrEvalTable_(A.seekerRanks, '求職者評価'));

  // 4) 月次トレンド（実数）
  body.appendParagraph('月次トレンド（月別エントリー実数）').setHeading(DocumentApp.ParagraphHeading.HEADING2);
  mrAppendImg_(body, mrTrendChart_(A.monthEntry), 520, 250, 380, 183);
  body.appendParagraph('※応募日ベースの月別実数。説明会以降の段階別 月末累計は、本番運用で'
    + '毎月スナップショットを蓄積し翌月以降に推移表示します（到達日列が無いため）。')
    .editAsText().setForegroundColor(MR_GRAY).setFontSize(8.5);

  // 5) 媒体別
  body.appendParagraph('媒体別 エントリー').setHeading(DocumentApp.ParagraphHeading.HEADING2);
  mrAppendImg_(body, mrDoughnutChart_(A.media), 440, 300, 320, 218);
  var t4 = [['媒体', 'エントリー']];
  Object.keys(A.media).slice(0, 8).forEach(function (k) { t4.push([k, String(A.media[k])]); });
  mrTable_(body, t4);

  // 6) 大学群別
  body.appendParagraph('大学群別').setHeading(DocumentApp.ParagraphHeading.HEADING2);
  mrAppendImg_(body, mrUnivChart_(A.univReach), 520, 300, 380, 219);
  var t5 = [['大学群', '説明会', '1次', '2次', '承諾']];
  Object.keys(A.univReach).slice(0, 8).forEach(function (k) {
    var a = A.univReach[k];
    t5.push([k, String(a[NODES.indexOf('説明選考会参加')]), String(a[NODES.indexOf('1次面接')]),
      String(a[NODES.indexOf('2次面接')]), String(a[NODES.indexOf('内定承諾')])]);
  });
  mrTable_(body, t5);

  // 7) 経路カテゴリ別
  body.appendParagraph('経路カテゴリ別 ファネル').setHeading(DocumentApp.ParagraphHeading.HEADING2);
  var t6 = [['カテゴリ', 'エントリー', '説明会', '1次', '2次', '承諾']];
  ['エージェント', 'スカウト'].forEach(function (cat) {
    var a = A.catReach[cat] || [];
    t6.push([cat, String(a[0] || 0), String(a[NODES.indexOf('説明選考会参加')] || 0),
      String(a[NODES.indexOf('1次面接')] || 0), String(a[NODES.indexOf('2次面接')] || 0),
      String(a[NODES.indexOf('内定承諾')] || 0)]);
  });
  mrTable_(body, t6);

  // 8) 価値観TOP
  body.appendParagraph('重視価値観 TOP（応募者の上位3位集計）').setHeading(DocumentApp.ParagraphHeading.HEADING2);
  if (A.topVals && A.topVals.length) mrAppendImg_(body, mrValuesChart_(A.topVals), 520, 300, 380, 219);
  else body.appendParagraph('価値観データなし。').editAsText().setForegroundColor(MR_GRAY);

  body.appendParagraph('');
  body.appendParagraph('※本レポートは本番データ（応募月ベース）から自動集計。担当者コメント欄は編集可。')
    .editAsText().setForegroundColor(MR_GRAY).setFontSize(9);

  doc.saveAndClose();
  // 社内リンク共有（編集可）
  try {
    DriveApp.getFileById(doc.getId())
      .setSharing(DriveApp.Access.DOMAIN_WITH_LINK, DriveApp.Permission.EDIT);
  } catch (e) { Logger.log('共有設定失敗: ' + e); }

  var url = doc.getUrl();
  SpreadsheetApp.getActive().toast('月次レポートDocを生成しました: ' + url, 'DOTZ自動化', 8);
  Logger.log('生成: ' + title + ' ' + url);
  return url;
}

// 評価分布の表（ランク別 人数/1次/2次/内定/承諾）
function mrEvalTable_(ranks, label) {
  var rows = [[label, '人数', '1次到達', '2次到達', '内定', '承諾']];
  ['S', 'A', 'B', 'C', 'D'].forEach(function (rk) {
    var arr = ranks[rk] || [];
    rows.push([rk, String(arr[NODES.indexOf('説明選考会参加')] || 0),
      String(arr[NODES.indexOf('1次面接')] || 0), String(arr[NODES.indexOf('2次面接')] || 0),
      String(arr[NODES.indexOf('内定出し')] || 0), String(arr[NODES.indexOf('内定承諾')] || 0)]);
  });
  return rows;
}

// 2D配列から表を追加（1行目=ヘッダ・赤背景白文字）
function mrTable_(body, rows) {
  var table = body.appendTable(rows);
  var head = table.getRow(0);
  for (var c = 0; c < head.getNumCells(); c++) {
    var cell = head.getCell(c);
    cell.setBackgroundColor(MR_RED);
    cell.editAsText().setForegroundColor('#ffffff').setBold(true);
  }
  table.setBorderColor('#cfcfcf');
  return table;
}

// QuickChart画像を追加（失敗時はテキスト代替）
function mrAppendImg_(body, config, genW, genH, dispW, dispH) {
  var blob = mrChartImg_(config, genW, genH);
  if (blob) {
    var img = body.appendImage(blob);
    img.setWidth(dispW).setHeight(dispH);
  } else {
    body.appendParagraph('（グラフ生成に失敗しました）')
      .editAsText().setForegroundColor(MR_GRAY);
  }
}
