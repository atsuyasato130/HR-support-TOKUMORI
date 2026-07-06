// ============================================================
// RPO 新卒ダッシュボード — 211_全体KPI / 212_月別KPI（2タブ再構成）
// ------------------------------------------------------------
// gas_rpo_v2.js と同じ Apps Script プロジェクトに追加する想定。
// COLOR / FONT / 各 aggregate* / loadTargets* / _getOrCreateSheet /
// _clearSheet / _bannerTitle / _sectionHeader / _tableHeader /
// _tableData / rateToColor / monthKey / formatDatetime / buildMonthList /
// getConfig / loadRawRecords / aggregateLanding 等は gas_rpo_v2.js 側を流用。
// ============================================================

const OVERVIEW_ALL_SHEET = "211_全体KPI";
const MONTHLY_SHEET      = "212_月別KPI";

// ── 共通ヘルパ ─────────────────────────────

// ファネル列（main + pass + reserved。exit / interview は除外）
function _funnelPhasesAll(phases) {
  return phases.filter(p => p.group === "main" || p.group === "pass" || p.group === "reserved");
}

// サマリー/ハイライト 共通指標セット（各フェーズ「合格」中心の8指標）
const SUMMARY_LABELS = [
  "エントリー", "説明選考会【合格】", "一次面接【合格】",
  "1dayインターン【合格】", "2daysインターン【合格】", "二次面接【合格】",
  "内定", "内定承諾",
];
function _kpiKeysFromLabels(phases, labels) {
  return labels.map(lbl => {
    const p = phases.find(x => x.label === lbl);
    return { key: p ? p.key : null, label: lbl };
  });
}

// ハイライト用 主要KPI（8指標・合格中心）
function _heroKpiKeys(phases) {
  return _kpiKeysFromLabels(phases, SUMMARY_LABELS);
}

// 全体/当月サマリー用 主要KPI（8指標・合格中心）
function _summaryKpiKeys(phases) {
  return _kpiKeysFromLabels(phases, SUMMARY_LABELS);
}

const _fmtNum = n => (n === null || n === undefined) ? "-" : String(Math.round(Number(n) * 10) / 10);
const _fmtPct = r => (r === null || r === undefined || isNaN(r)) ? "-" : Math.round(r * 100) + "%";
const _fmtDiff = d => (d === null || isNaN(d)) ? "-" : (d > 0 ? "+" + (Math.round(d * 10) / 10) : String(Math.round(d * 10) / 10));

// 着地予想（フェーズ別）— 現パイプライン・カスケード方式
//   ラダー = main+pass+reserved（予約も位置決めに含む）。内定承諾は着地対象外（着地は内定まで）。
//   実績通過率 = 各フェーズ累計実績の隣接比。
//   モデル: 現在「選考中」の学生だけを実績通過率で各段階へ進めた期待到達数（単調非増加）。
//   ※ 旧 if(idx<0)idx=0 の「未マップを全部エントリーへ加算」を撤去（305 過大化バグ修正）。
//      「一次後面談（人事/現場）」は「一次面接【合格】」段階へ寄せる。
function _landingByPhase(records, phases, targets) {
  const ladder = phases.filter(p => p.group === "main" || p.group === "pass" || p.group === "reserved");
  const acceptKey = phases.find(p => p.label === "内定承諾")?.key;
  const fp = ladder.filter(p => p.key !== acceptKey);  // 内定承諾は着地対象外

  const fStats = aggregateFunnelMonthly(records, phases);
  const cum = {};
  fp.forEach(p => { cum[p.key] = fStats[p.key]?.TOTAL || 0; });

  // 実績通過率 i → i+1（累計実績の隣接比）
  const passRate = {};
  for (let i = 0; i < fp.length - 1; i++) {
    const a = cum[fp[i].key], b = cum[fp[i + 1].key];
    passRate[fp[i].key] = a > 0 ? b / a : 0;
  }

  // 現在アクティブ（選考中）を fp 上の段階へマップ。未マップは加算しない。
  const aStats = aggregateActive(records);
  const activeAt = new Array(fp.length).fill(0);
  Object.entries(aStats).forEach(([stage, n]) => {
    let s = String(stage);
    if (/一次後面談/.test(s)) s = "一次面接【合格】";   // 後面談 → 一次合格 段階へ寄せる
    const base = s.replace(/【.+?】/g, "").trim();
    const idx = fp.findIndex(p => {
      const pb = p.label.replace(/【.+?】/g, "").trim();
      return pb && (base === pb || base.indexOf(pb) >= 0 || pb.indexOf(base) >= 0);
    });
    if (idx < 0) return;                               // 未マップは捨てる（エントリーへ寄せない）
    activeAt[idx] += n;
  });

  // カスケード: 段階 i にいる活動者を実績通過率で下流へ。landing[j] へ加算。
  const landing = new Array(fp.length).fill(0);
  for (let i = 0; i < fp.length; i++) {
    let carry = activeAt[i];
    if (!carry) continue;
    landing[i] += carry;
    for (let j = i + 1; j < fp.length; j++) {
      carry *= (passRate[fp[j - 1].key] || 0);
      landing[j] += carry;
    }
  }
  // 単調非増加を保証
  for (let i = 1; i < fp.length; i++) {
    if (landing[i] > landing[i - 1]) landing[i] = landing[i - 1];
  }

  const rows = fp.map((p, i) => {
    const tgt = Object.values(targets[p.key] || {}).reduce((s, n) => s + n, 0);
    return {
      key: p.key, label: p.label,
      group: p.group,
      cumActual: cum[p.key],
      active: activeAt[i],
      landing: landing[i],
      target: tgt,
      ratio: tgt ? landing[i] / tgt : null,
    };
  });
  return { fp, rows };
}

// 指定月の「フェーズ到達数」をキー（大学/チャネル）別に集計
function _byKeyPhaseForMonth(records, phases, ym, keyFn) {
  const res = {};
  records.forEach(rec => {
    const k = keyFn(rec) || "（未記入）";
    phases.forEach(p => {
      const dt = rec.arrivals[p.key];
      if (dt && monthKey(dt) === ym) {
        if (!res[k]) { res[k] = {}; phases.forEach(q => { res[k][q.key] = 0; }); }
        res[k][p.key]++;
      }
    });
  });
  return res;
}

// ============================================================
// 211_全体KPI（累計・全期間）
// ============================================================
function renderOverviewAll(records, phases, targets, targetsCh) {
  const sheet = _getOrCreateSheet(OVERVIEW_ALL_SHEET);
  _clearSheet(sheet);

  const cfg = getConfig();
  const company = String(cfg["企業名"] || "（記入してください）").trim();
  const now = new Date();

  const fp = _funnelPhasesAll(phases);          // 表示用フェーズ列（最大幅）
  const FCOLS = fp.length;
  const WIDE = 4 + FCOLS;                        // 経路別テーブルの最大列数

  const fStats   = aggregateFunnelMonthly(records, phases);
  const cohort   = aggregateFunnelByEntryMonth(records, phases);
  const aStats   = aggregateActive(records);
  const schools  = aggregateBySchool(records, phases);
  const channels = aggregateByChannel(records, phases);
  const landing  = aggregateLanding(records, phases, targets);
  const landP    = _landingByPhase(records, phases, targets);

  let r = 1;

  // ── バナー ──
  _bannerTitle(sheet, r++, WIDE, `${company}　／　RPO 採用ダッシュボード（全体KPI）`);
  sheet.getRange(r, 1, 1, WIDE).merge()
    .setValue(`自動更新: ${formatDatetime(now)}　｜　対象: 全期間累計`)
    .setBackground(COLOR.bgRowAlt).setFontColor(COLOR.textDim).setFontSize(10)
    .setFontFamily(FONT).setHorizontalAlignment("left");
  r += 2;

  // ── ① ハイライトサマリー（累計） ──
  const heroKeys = _heroKpiKeys(phases);
  const HN = heroKeys.length;
  _sectionHeader(sheet, r++, HN, "■ サマリー（全体ハイライト・累計）");
  sheet.getRange(r, 1, 1, HN).setValues([heroKeys.map(k => k.label)]);
  _tableHeader(sheet, r, 1, HN); r++;
  const heroVals = heroKeys.map(k => k.key ? (fStats[k.key]?.TOTAL || 0) : 0);
  sheet.getRange(r, 1, 1, HN).setValues([heroVals]);
  _tableData(sheet, r, 1, 1, HN);
  sheet.getRange(r, 1, 1, HN).setFontSize(18).setFontWeight("bold").setHorizontalAlignment("center");
  sheet.setRowHeight(r, 46);
  r += 2;

  // ── ② 全体サマリー（累計KPI） ──
  const sumKeys = _summaryKpiKeys(phases);
  _sectionHeader(sheet, r++, 1 + sumKeys.length, "■ 全体サマリー（累計）");
  sheet.getRange(r, 1, 1, 1 + sumKeys.length).setValues([["指標"].concat(sumKeys.map(k => k.label))]);
  _tableHeader(sheet, r, 1, 1 + sumKeys.length); r++;
  const cumAct = sumKeys.map(k => k.key ? (fStats[k.key]?.TOTAL || 0) : 0);
  const cumTgt = sumKeys.map(k => Object.values(targets[k.key] || {}).reduce((s, n) => s + n, 0));
  const cumRate = cumAct.map((a, i) => cumTgt[i] ? a / cumTgt[i] : null);
  const sumRows = [
    ["累計実績"].concat(cumAct),
    ["累計目標"].concat(cumTgt.map(t => t || "-")),
    ["達成率"].concat(cumRate.map(_fmtPct)),
    ["進捗"].concat(cumRate.map(x => x === null ? "-" : x >= 1 ? "達成" : x >= 0.7 ? "注意" : "警戒")),
  ];
  sheet.getRange(r, 1, sumRows.length, 1 + sumKeys.length).setValues(sumRows);
  _tableData(sheet, r, 1, sumRows.length, 1 + sumKeys.length);
  cumRate.forEach((rate, i) => sheet.getRange(r + 2, 2 + i).setBackground(rateToColor(rate)));
  r += sumRows.length + 2;

  // ── ③ 月次ファネル（実績／目標／達成率 統合） ──
  const months = buildMonthList();
  const activeMonths = months.filter(m =>
    (cohort[m.ym]?.TOTAL || 0) > 0 || fp.some(k => (targets[k.key]?.[m.ym] || 0) > 0));
  if (activeMonths.length === 0) activeMonths.push(months[0]);

  _sectionHeader(sheet, r++, 2 + FCOLS, "■ 月次ファネル（実績／目標／達成率 統合）");
  sheet.getRange(r, 1, 1, 2 + FCOLS).setValues([["月", "区分"].concat(fp.map(p => p.label))]);
  _tableHeader(sheet, r, 1, 2 + FCOLS); r++;

  const mfRows = [];
  const totAct = fp.map(p => cohort.TOTAL?.[p.key] || 0);
  const totTgt = fp.map(p => Object.values(targets[p.key] || {}).reduce((s, n) => s + n, 0));
  activeMonths.forEach(m => {
    const act = fp.map(p => cohort[m.ym]?.[p.key] || 0);
    const tgt = fp.map(p => targets[p.key]?.[m.ym] || 0);
    mfRows.push([m.label, "実績"].concat(act));
    mfRows.push(["", "目標"].concat(tgt.map(t => t || "-")));
    mfRows.push(["", "達成率"].concat(act.map((a, i) => tgt[i] ? _fmtPct(a / tgt[i]) : "-")));
  });
  mfRows.push(["合計", "実績"].concat(totAct));
  mfRows.push(["", "目標"].concat(totTgt.map(t => t || "-")));
  mfRows.push(["", "達成率"].concat(totAct.map((a, i) => totTgt[i] ? _fmtPct(a / totTgt[i]) : "-")));
  sheet.getRange(r, 1, mfRows.length, 2 + FCOLS).setValues(mfRows);
  _tableData(sheet, r, 1, mfRows.length, 2 + FCOLS);
  // 達成率行に色付け（3行周期の3行目）：達成率に応じて緑/黄/赤
  for (let i = 2; i < mfRows.length; i += 3) {
    for (let c = 0; c < FCOLS; c++) {
      const v = mfRows[i][2 + c];
      const rate = (typeof v === "string" && v.endsWith("%")) ? parseFloat(v) / 100 : null;
      sheet.getRange(r + i, 3 + c).setBackground(rate === null ? COLOR.bgRow : rateToColor(rate));
    }
  }
  r += mfRows.length + 2;

  // ── ④ 着地予想（過去実績ベース・フェーズ別） ──
  _sectionHeader(sheet, r++, 6, "■ 着地予想（過去実績ベース）");
  sheet.getRange(r, 1, 1, 6).setValues([["フェーズ", "累計実績", "選考中", "着地予想", "期間目標", "着地予想/目標"]]);
  _tableHeader(sheet, r, 1, 6); r++;
  const lpRows = landP.rows.map(x => [x.label, x.cumActual, x.active, _fmtNum(x.landing), x.target || "-", _fmtPct(x.ratio)]);
  if (lpRows.length) {
    sheet.getRange(r, 1, lpRows.length, 6).setValues(lpRows);
    _tableData(sheet, r, 1, lpRows.length, 6);
    landP.rows.forEach((x, i) => sheet.getRange(r + i, 6).setBackground(rateToColor(x.ratio)));
    r += lpRows.length;
  }
  r += 2;

  // ── ⑤ アクティブ学生（選考中） ──
  _sectionHeader(sheet, r++, 2, "■ アクティブ学生（選考中）");
  sheet.getRange(r, 1, 1, 2).setValues([["選考段階", "人数"]]); _tableHeader(sheet, r, 1, 2); r++;
  const actRows = Object.entries(aStats).filter(([, n]) => n > 0).sort((a, b) => b[1] - a[1]);
  const totActive = actRows.reduce((s, x) => s + x[1], 0);
  const aRows = actRows.map(x => [x[0], x[1]]).concat([["合計（選考中）", totActive]]);
  sheet.getRange(r, 1, aRows.length, 2).setValues(aRows);
  _tableData(sheet, r, 1, aRows.length, 2);
  sheet.getRange(r + aRows.length - 1, 1, 1, 2).setBackground(COLOR.bgRowAlt).setFontWeight("bold");
  r += aRows.length + 2;

  // ── ⑥ 大学別 累計ファネル ──
  _sectionHeader(sheet, r++, 1 + FCOLS, "■ 大学別 累計ファネル");
  sheet.getRange(r, 1, 1, 1 + FCOLS).setValues([["大学名"].concat(fp.map(p => p.label))]);
  _tableHeader(sheet, r, 1, 1 + FCOLS); r++;
  const schRows = Object.entries(schools)
    .filter(([, s]) => s.entry > 0)
    .sort((a, b) => b[1].entry - a[1].entry)
    .map(([sch, s]) => [sch].concat(fp.map(p => s.byPhase[p.key] || 0)));
  if (schRows.length) {
    sheet.getRange(r, 1, schRows.length, 1 + FCOLS).setValues(schRows);
    _tableData(sheet, r, 1, schRows.length, 1 + FCOLS);
    r += schRows.length;
  }
  r += 2;

  // ── ⑦ エントリー経路別 累計 ──
  _sectionHeader(sheet, r++, WIDE, "■ エントリー経路別 累計");
  sheet.getRange(r, 1, 1, WIDE)
    .setValues([["チャネル", "累計目標", "累計実績", "累計差分"].concat(fp.map(p => p.label))]);
  _tableHeader(sheet, r, 1, WIDE); r++;
  const chRows = Object.entries(channels)
    .filter(([, s]) => s.entry > 0)
    .sort((a, b) => b[1].entry - a[1].entry)
    .map(([ch, s]) => {
      const tgt = Object.values(targetsCh[ch] || {}).reduce((sum, n) => sum + n, 0);
      const act = s.entry;
      return [ch, tgt || "-", act, _fmtDiff(act - tgt)].concat(fp.map(p => s.byPhase[p.key] || 0));
    });
  if (chRows.length) {
    sheet.getRange(r, 1, chRows.length, WIDE).setValues(chRows);
    _tableData(sheet, r, 1, chRows.length, WIDE);
    r += chRows.length;
  }

  // 列幅
  sheet.setColumnWidth(1, 180);
  for (let c = 2; c <= WIDE; c++) sheet.setColumnWidth(c, 92);
  sheet.setFrozenRows(2);
  sheet.setHiddenGridlines(true);
}

// ============================================================
// 212_月別KPI（月切替：ドロップダウン→再描画）
// ============================================================
function renderMonthly(records, phases, targets, targetsCh, targetYM) {
  const sheet = _getOrCreateSheet(MONTHLY_SHEET);
  _clearSheet(sheet);

  const cfg = getConfig();
  const company = String(cfg["企業名"] || "（記入してください）").trim();
  const months = buildMonthList();

  // 対象月の決定（未指定なら当月、なければ最初の月）
  const fStats = aggregateFunnelMonthly(records, phases);
  let target = months.find(m => m.ym === targetYM);
  if (!target) {
    const cur = monthKey(new Date());
    target = months.find(m => m.ym === cur) || months[0];
  }
  const ym = target.ym, prevYM = (() => {
    const idx = months.findIndex(m => m.ym === ym);
    return idx > 0 ? months[idx - 1].ym : null;
  })();

  const fp = _funnelPhasesAll(phases);
  const FCOLS = fp.length;
  const WIDE = 1 + FCOLS;

  const landing = aggregateLanding(records, phases, targets);
  const landP   = _landingByPhase(records, phases, targets);
  const schM    = _byKeyPhaseForMonth(records, phases, ym, rec => rec.school);
  const chM     = _byKeyPhaseForMonth(records, phases, ym, rec => rec.channel);

  let r = 1;

  // ── バナー ＋ 月ドロップダウン ──
  _bannerTitle(sheet, r++, WIDE, `${company}　／　RPO 採用ダッシュボード（月別KPI）`);
  sheet.getRange(r, 1).setValue("対象月 →").setFontWeight("bold").setFontFamily(FONT);
  const rule = SpreadsheetApp.newDataValidation()
    .requireValueInList(months.map(m => m.label), true).setAllowInvalid(false).build();
  sheet.getRange(r, 2).setDataValidation(rule).setValue(target.label)
    .setBackground("#FFF2B3").setFontWeight("bold").setHorizontalAlignment("center");
  const dropRow = r;
  r++;
  sheet.getRange(r, 1, 1, WIDE).merge()
    .setValue("※ B2の月を切替えると自動で再描画されます")
    .setBackground(COLOR.bgRowAlt).setFontColor(COLOR.textDim).setFontSize(10)
    .setFontFamily(FONT).setHorizontalAlignment("left");
  r += 2;

  // ── ① ハイライトサマリー（選択月） ── 共通の合格中心8指標
  const heroKeys = _heroKpiKeys(phases);
  const HN = heroKeys.length;
  _sectionHeader(sheet, r++, HN, `■ サマリー（${target.label}のハイライト）`);
  sheet.getRange(r, 1, 1, HN).setValues([heroKeys.map(k => k.label)]);
  _tableHeader(sheet, r, 1, HN); r++;
  const heroVals = heroKeys.map(k => k.key ? (fStats[k.key]?.[ym] || 0) : 0);
  sheet.getRange(r, 1, 1, HN).setValues([heroVals]);
  _tableData(sheet, r, 1, 1, HN);
  sheet.getRange(r, 1, 1, HN).setFontSize(18).setFontWeight("bold").setHorizontalAlignment("center");
  sheet.setRowHeight(r, 46);
  r += 2;

  // ── ② 当月サマリー（選択月） ──
  const sumKeys = _summaryKpiKeys(phases);
  _sectionHeader(sheet, r++, 1 + sumKeys.length, `■ 当月サマリー（${target.label}：実績／目標／達成率／前月差）`);
  sheet.getRange(r, 1, 1, 1 + sumKeys.length).setValues([["指標"].concat(sumKeys.map(k => k.label))]);
  _tableHeader(sheet, r, 1, 1 + sumKeys.length); r++;
  const mAct  = sumKeys.map(k => k.key ? (fStats[k.key]?.[ym] || 0) : 0);
  const mPrev = sumKeys.map(k => k.key && prevYM ? (fStats[k.key]?.[prevYM] || 0) : 0);
  const mTgt  = sumKeys.map(k => targets[k.key]?.[ym] || 0);
  const mRate = mAct.map((a, i) => mTgt[i] ? a / mTgt[i] : null);
  const mRows = [
    ["実績"].concat(mAct),
    ["目標"].concat(mTgt.map(t => t || "-")),
    ["達成率"].concat(mRate.map(_fmtPct)),
    ["前月差"].concat(mAct.map((a, i) => _fmtDiff(a - mPrev[i]))),
  ];
  sheet.getRange(r, 1, mRows.length, 1 + sumKeys.length).setValues(mRows);
  _tableData(sheet, r, 1, mRows.length, 1 + sumKeys.length);
  mRate.forEach((rate, i) => sheet.getRange(r + 2, 2 + i).setBackground(rateToColor(rate)));
  r += mRows.length + 2;

  // ── ④ フェーズ別（選択月）：実績 × 目標 × 差分 × 着地予想 ──
  _sectionHeader(sheet, r++, 7, `■ フェーズ別（${target.label}）：実績 × 目標 × 差分 × 着地予想`);
  sheet.getRange(r, 1, 1, 7).setValues([["フェーズ", "実績", "目標", "達成率", "差分", "着地予想", "着地予想/目標"]]);
  _tableHeader(sheet, r, 1, 7); r++;
  const landMap = {};
  landP.rows.forEach(x => { landMap[x.key] = x; });
  const entKey = fp[0]?.key;
  const acceptKeyM = phases.find(p => p.label === "内定承諾")?.key;
  // エントリー着地予想 = 日割りペース（当月のみ）: 当月実績 ÷ 経過日数 × 当月日数
  const nowM = new Date();
  const isCurMonth = (ym === monthKey(nowM));
  const elapsed = nowM.getDate();
  const daysInMonth = new Date(nowM.getFullYear(), nowM.getMonth() + 1, 0).getDate();
  // 各フェーズの着地予想値を算出（数値 or null）
  const landingOf = (p) => {
    if (p.group === "reserved") return null;            // 予約フェーズは対象外
    if (p.key === acceptKeyM) return null;              // 内定承諾は対象外
    if (p.key === entKey) {                              // エントリーは日割りペース（当月のみ）
      if (!isCurMonth || !elapsed) return null;
      const a = fStats[p.key]?.[ym] || 0;
      return a / elapsed * daysInMonth;
    }
    return landMap[p.key] ? landMap[p.key].landing : null;  // 他フェーズはカスケード着地
  };
  const phRows = fp.map(p => {
    const act = fStats[p.key]?.[ym] || 0;
    const tgt = targets[p.key]?.[ym] || 0;               // 当月目標
    const rate = tgt ? act / tgt : null;
    const land = landingOf(p);
    const landRatio = (land !== null && tgt) ? land / tgt : null;  // 着地予想 ÷ 当月目標
    return [
      p.label, act, tgt || "-", _fmtPct(rate), _fmtDiff(act - tgt),
      land === null ? "-" : _fmtNum(land), landRatio === null ? "-" : _fmtPct(landRatio),
    ];
  });
  sheet.getRange(r, 1, phRows.length, 7).setValues(phRows);
  _tableData(sheet, r, 1, phRows.length, 7);
  fp.forEach((p, i) => {
    const tgt = targets[p.key]?.[ym] || 0;
    const act = fStats[p.key]?.[ym] || 0;
    sheet.getRange(r + i, 4).setBackground(rateToColor(tgt ? act / tgt : null));
    const land = landingOf(p);
    const landRatio = (land !== null && tgt) ? land / tgt : null;
    if (landRatio !== null) sheet.getRange(r + i, 7).setBackground(rateToColor(landRatio));
  });
  r += phRows.length + 2;

  // ── ⑤ 大学別（選択月の実績） ──
  _sectionHeader(sheet, r++, 1 + FCOLS, `■ 大学別（${target.label}の実績）`);
  sheet.getRange(r, 1, 1, 1 + FCOLS).setValues([["大学名"].concat(fp.map(p => p.label))]);
  _tableHeader(sheet, r, 1, 1 + FCOLS); r++;
  const entryKey = fp[0]?.key;
  const schRows = Object.entries(schM)
    .sort((a, b) => (b[1][entryKey] || 0) - (a[1][entryKey] || 0))
    .filter(([, s]) => fp.some(p => (s[p.key] || 0) > 0))
    .map(([sch, s]) => [sch].concat(fp.map(p => s[p.key] || 0)));
  if (schRows.length) {
    sheet.getRange(r, 1, schRows.length, 1 + FCOLS).setValues(schRows);
    _tableData(sheet, r, 1, schRows.length, 1 + FCOLS);
    r += schRows.length;
  } else {
    sheet.getRange(r, 1, 1, 1 + FCOLS).setValues([["（該当月の実績なし）"].concat(fp.map(() => ""))]);
    _tableData(sheet, r, 1, 1, 1 + FCOLS); r++;
  }
  r += 2;

  // ── ⑥ エントリー経路別（選択月の実績） ──
  _sectionHeader(sheet, r++, 1 + FCOLS, `■ エントリー経路別（${target.label}の実績）`);
  sheet.getRange(r, 1, 1, 1 + FCOLS).setValues([["チャネル"].concat(fp.map(p => p.label))]);
  _tableHeader(sheet, r, 1, 1 + FCOLS); r++;
  const chRows = Object.entries(chM)
    .sort((a, b) => (b[1][entryKey] || 0) - (a[1][entryKey] || 0))
    .filter(([, s]) => fp.some(p => (s[p.key] || 0) > 0))
    .map(([ch, s]) => [ch].concat(fp.map(p => s[p.key] || 0)));
  if (chRows.length) {
    sheet.getRange(r, 1, chRows.length, 1 + FCOLS).setValues(chRows);
    _tableData(sheet, r, 1, chRows.length, 1 + FCOLS);
    r += chRows.length;
  } else {
    sheet.getRange(r, 1, 1, 1 + FCOLS).setValues([["（該当月の実績なし）"].concat(fp.map(() => ""))]);
    _tableData(sheet, r, 1, 1, 1 + FCOLS); r++;
  }

  // 列幅
  sheet.setColumnWidth(1, 180);
  for (let c = 2; c <= WIDE; c++) sheet.setColumnWidth(c, 92);
  sheet.setFrozenRows(dropRow);
  sheet.setHiddenGridlines(true);
}

// ── 月ドロップダウン変更で 212 を再描画（簡易トリガー） ──
function onEdit(e) {
  try {
    if (!e || !e.range) return;
    const sh = e.range.getSheet();
    if (sh.getName() !== MONTHLY_SHEET) return;
    if (e.range.getRow() !== 2 || e.range.getColumn() !== 2) return;
    const label = String(e.value || "").trim();
    const m = buildMonthList().find(x => x.label === label);
    if (!m) return;
    const { records, phases } = loadRawRecords();
    renderMonthly(records, phases, loadTargetsFunnel(phases), loadTargetsChannel(), m.ym);
  } catch (err) {
    try { _writeLog("WARN", "onEdit(212): " + err.message); } catch (e2) {}
  }
}

// ── 単体再生成 ──
function rebuildOverviewAllOnly() {
  const { records, phases } = loadRawRecords();
  renderOverviewAll(records, phases, loadTargetsFunnel(phases), loadTargetsChannel());
}
function rebuildMonthlyOnly() {
  const { records, phases } = loadRawRecords();
  renderMonthly(records, phases, loadTargetsFunnel(phases), loadTargetsChannel(), null);
}
