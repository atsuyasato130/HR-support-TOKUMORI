// ============================================================
// RPO 採用ダッシュボード GAS v1.0
// SpreadsheetID: 1Jst9O1xcgDOgpRylhUIslnbLzgPZMk9zKy9W0NFyFtM
// 設計: /Users/atsuyasato130/.claude/plans/zany-conjuring-squid.md
//
// 構成:
//   §1  定数・設定
//   §2  設定管理
//   §3  ローデータ読込
//   §4  集計エンジン
//   §5  目標比較
//   §6  描画エンジン
//   §7  Slack 週次レポート
//   §8  メニュー & トリガー
//   §9  ユーティリティ
// ============================================================

// ─────────────────────────────────────────
// §1  定数・設定
// ─────────────────────────────────────────

const CONFIG_SHEET = "200_設定";

// テーマカラー（既存タブの配色に揃える: 003_01_採用サマリー / LG/CA案件と同系統）
const COLOR = {
  bgDark:    "#37474F", // ヘッダ濃グレー（既存と同色）
  bgPanel:   "#546E7A", // セクション帯（やや明るいグレー）
  bgRow:     "#FFFFFF", // データ行は白
  bgRowAlt:  "#F5F5F5", // ストライプ用
  bgHeader:  "#37474F",
  fgWhite:   "#FFFFFF",
  accent:    "#C8E6C9", // 達成（薄緑・既存サマリーと同系）
  alert:     "#FFCDD2", // 未達（薄赤）
  warn:      "#FFF59D", // 注意（薄黄）
  ok:        "#C8E6C9",
  textDim:   "#757575",
  textMain:  "#212121",
  totalBg:   "#ECEFF1", // 合計行の淡グレー
};

// フォントは既存タブと揃えるためデフォルト(Arial)を使う
const FONT_HEAD = "Arial";
const FONT_MONO = "Arial";

// フェーズ定義（ATS到達日列名 → 内部キー / 表示ラベル / グループ）
// 003_01_採用サマリー の列順に合わせる
const PHASE_DEFS = [
  { key: "entry",         arrival: "エントリー・到達日",         label: "エントリー",   group: "main" },
  { key: "info_joined",   arrival: "説明選考会【参加】・到達日", label: "説明選考会",   group: "main" },
  { key: "info_passed",   arrival: "一次面接【予約】・到達日",   label: "合格",         group: "pass",  derivedFrom: "info_joined" },
  { key: "first_joined",  arrival: "一次面接【参加】・到達日",   label: "1次面接",      group: "main" },
  { key: "first_passed",  arrival: "一次面接【合格】・到達日",   label: "合格",         group: "pass" },
  { key: "oneday_joined", arrival: "1dayインターン【参加】・到達日", label: "1day",      group: "main" },
  { key: "oneday_passed", arrival: "1dayインターン【合格】・到達日", label: "合格",      group: "pass" },
  { key: "twoday_joined", arrival: "2daysインターン【参加】・到達日", label: "2day",     group: "main" },
  { key: "twoday_passed", arrival: "2daysインターン【合格】・到達日", label: "合格",     group: "pass" },
  { key: "second_joined", arrival: "二次面接【参加】・到達日",   label: "役員面接",     group: "main" },
  { key: "second_passed", arrival: "二次面接【合格】・到達日",   label: "合格",         group: "pass" },
  { key: "final_joined",  arrival: "最終選考【参加】・到達日",   label: "最終面接",     group: "main" },
  { key: "offer",         arrival: "内定・到達日",               label: "内定",         group: "main" },
  { key: "accepted",      arrival: "内定承諾・到達日",           label: "内定承諾",     group: "main" },
];

// 「現在の選考段階」値 → アクティブ管理タブの表示順
const ACTIVE_STAGES = [
  "エントリー", "説明選考会【予約】", "説明選考会【参加】",
  "一次面接【予約】", "一次面接【参加】", "一次面接【合格】",
  "1dayインターン【予約】", "1dayインターン【参加】", "1dayインターン【合格】",
  "2daysインターン【予約】", "2daysインターン【参加】", "2daysインターン【合格】",
  "二次面接【予約】", "二次面接【参加】", "二次面接【合格】",
  "最終選考【予約】", "最終選考【参加】",
  "内定", "内定承諾",
];

// 現在の選考段階 → 次の選考イベント＆その予約日のATSヘッダ
const NEXT_STAGE_MAP = {
  "エントリー":             { name: "説明選考会",  arrivalHeader: "説明選考会【予約】・到達日" },
  "説明選考会【予約】":     { name: "説明選考会",  arrivalHeader: "説明選考会【参加】・到達日" },
  "説明選考会【参加】":     { name: "1次面接",     arrivalHeader: "一次面接【予約】・到達日" },
  "一次面接【予約】":       { name: "1次面接",     arrivalHeader: "一次面接【参加】・到達日" },
  "一次面接【参加】":       { name: "1次面接合格", arrivalHeader: "一次面接【合格】・到達日" },
  "一次面接【合格】":       { name: "1day",        arrivalHeader: "1dayインターン【予約】・到達日" },
  "1dayインターン【予約】": { name: "1day",        arrivalHeader: "1dayインターン【参加】・到達日" },
  "1dayインターン【参加】": { name: "1day合格",    arrivalHeader: "1dayインターン【合格】・到達日" },
  "1dayインターン【合格】": { name: "2day",        arrivalHeader: "2daysインターン【予約】・到達日" },
  "2daysインターン【予約】":{ name: "2day",        arrivalHeader: "2daysインターン【参加】・到達日" },
  "2daysインターン【参加】":{ name: "2day合格",    arrivalHeader: "2daysインターン【合格】・到達日" },
  "2daysインターン【合格】":{ name: "役員面接",    arrivalHeader: "二次面接【予約】・到達日" },
  "二次面接【予約】":       { name: "役員面接",    arrivalHeader: "二次面接【参加】・到達日" },
  "二次面接【参加】":       { name: "役員面接合格",arrivalHeader: "二次面接【合格】・到達日" },
  "二次面接【合格】":       { name: "最終面接",    arrivalHeader: "最終選考【予約】・到達日" },
  "最終選考【予約】":       { name: "最終面接",    arrivalHeader: "最終選考【参加】・到達日" },
  "最終選考【参加】":       { name: "内定",        arrivalHeader: "内定・到達日" },
  "内定":                   { name: "内定承諾",    arrivalHeader: "内定承諾・到達日" },
  "内定承諾":               { name: "（完了）",    arrivalHeader: null },
};

const RANKS = ["S", "A", "B", "C", "D"];

// ─────────────────────────────────────────
// §2  設定管理
// ─────────────────────────────────────────

function getConfig() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(CONFIG_SHEET);
  if (!sheet) throw new Error(`設定タブ「${CONFIG_SHEET}」が見つかりません`);
  const data = sheet.getDataRange().getValues();
  const cfg = {};
  for (const row of data) {
    const key = String(row[0] || "").trim();
    if (!key || key.startsWith("■") || key === "設定キー") continue;
    cfg[key] = row[1];
  }
  return cfg;
}

function getChannelMapping() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(CONFIG_SHEET);
  if (!sheet) return {};
  const data = sheet.getDataRange().getValues();
  const map = {};
  let inSection = false;
  for (const row of data) {
    const a = String(row[0] || "").trim();
    const b = String(row[1] || "").trim();
    if (a.includes("チャネル名マッピング")) { inSection = true; continue; }
    if (!inSection) continue;
    if (a === "ATS表記" || !a || a.startsWith("（")) continue;
    if (b) map[a] = b;
  }
  return map;
}

function getInputSheetNames() {
  const cfg = getConfig();
  return {
    raw:        cfg["ATSローデータタブ名"]      || "向編集中",
    targetFun:  cfg["目標タブ名（ファネル）"]    || "001_採用目標",
    targetCh:   cfg["目標タブ名（チャネル）"]    || "003_ver1.1_エントリー目標/実績管理",
  };
}

function getOutputSheetNames() {
  const cfg = getConfig();
  return {
    dashboard: cfg["ダッシュボードタブ"] || "210_ダッシュボード",
    detail:    cfg["詳細分析タブ"]       || "220_詳細分析",
    byname:    cfg["バイネーム管理タブ"] || "230_バイネーム管理",
    log:       cfg["ログタブ"]           || "299_ログ",
  };
}

// 旧タブの名前（クリーンアップ用）
const LEGACY_OUTPUT_TABS = [
  "220_月次ファネル_自動",
  "230_チャネル別実績_自動",
  "230_チャネル別実績",
  "240_アクティブ_自動",
  "240_ステータス",
  "250_目標差分",
  "260_リードタイム_自動",
  "270_辞退・離脱_自動",
  "220_月次ファネル+目標差分",
];

function cleanupLegacyTabs() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  LEGACY_OUTPUT_TABS.forEach(name => {
    const sheet = ss.getSheetByName(name);
    if (sheet) {
      ss.deleteSheet(sheet);
      Logger.log(`[cleanup] 削除: ${name}`);
    }
  });
}

function getSlackSettings() {
  const cfg = getConfig();
  return {
    token:   String(cfg["Slack Bot Token"] || "").trim(),
    channel: String(cfg["Slack 週次レポートチャンネルID"] || "").trim(),
    weekday: String(cfg["週次レポート曜日"] || "月曜").trim(),
    hour:    parseInt(cfg["週次レポート時刻"] || "9", 10),
  };
}

// ─────────────────────────────────────────
// §3  ローデータ読込
// ─────────────────────────────────────────

// 戻り値: [{ id, lastName, firstName, school, currentStage, status, channel(プライマリ),
//          arrivals: {phaseKey → Date|null}, evals: {phaseKey → "S"|"A"... } }, ...]
function loadRawRecords() {
  const { raw } = getInputSheetNames();
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(raw);
  if (!sheet) throw new Error(`ローデータタブ「${raw}」が見つかりません`);

  const data = sheet.getDataRange().getValues();
  if (data.length < 2) return [];

  // ヘッダ行は2行目 (1行目は職種ラベル)
  const headerRow = data[1];
  const colIdx = {};
  headerRow.forEach((h, i) => {
    const key = String(h || "").trim();
    if (!key) return;
    // 重複ヘッダ(総合評価/自由記述)は最初に出てきたインデックスのみ保持しない
    if (!(key in colIdx)) colIdx[key] = i;
  });

  // 「総合評価」は各フェーズ後に登場する重複ヘッダ。直近の主要フェーズに紐付けるためインデックス配列も取得
  const evalIndices = [];
  headerRow.forEach((h, i) => { if (String(h).trim() === "総合評価") evalIndices.push(i); });

  // 主要評価ポイント（参加列の直後に評価列がある想定）
  // 評価インデックス順: 説明選考会, 一次面接, 1day, 2day, 二次面接, 最終選考
  const evalPhaseKeys = ["info_joined", "first_joined", "oneday_joined", "twoday_joined", "second_joined", "final_joined"];

  const records = [];
  for (let r = 2; r < data.length; r++) {
    const row = data[r];
    const id = String(row[colIdx["ID"]] || "").trim();
    if (!id) continue;

    const rec = {
      id,
      lastName:     String(row[colIdx["姓"]] || "").trim(),
      firstName:    String(row[colIdx["名"]] || "").trim(),
      school:       String(row[colIdx["学校名"]] || "").trim(),
      currentStage: String(row[colIdx["現在の選考段階"]] || "").trim(),
      status:       String(row[colIdx["選考状況"]] || "").trim(),
      channel:      _normalizeChannel(String(row[colIdx["エントリー経路"]] || "").trim()),
      arrivals:     {},
      evals:        {},
    };

    PHASE_DEFS.forEach(def => {
      if (!(def.arrival in colIdx)) { rec.arrivals[def.key] = null; return; }
      const v = row[colIdx[def.arrival]];
      rec.arrivals[def.key] = parseDate(v);
    });

    // 各「○○・到達日」列を全部 rawArrivals に格納（バイネーム用）
    rec.rawArrivals = {};
    Object.keys(colIdx).forEach(header => {
      if (header.endsWith("・到達日")) {
        rec.rawArrivals[header] = parseDate(row[colIdx[header]]);
      }
    });

    evalIndices.forEach((idx, i) => {
      if (i >= evalPhaseKeys.length) return;
      const v = String(row[idx] || "").trim().toUpperCase();
      if (RANKS.includes(v)) rec.evals[evalPhaseKeys[i]] = v;
    });

    records.push(rec);
  }
  return records;
}

function _normalizeChannel(raw) {
  if (!raw) return "";
  // 複数チャネル併記の場合は最初をプライマリ
  return raw.split(/[,、|｜]/)[0].trim();
}

// ─────────────────────────────────────────
// §4  集計エンジン
// ─────────────────────────────────────────

// 月次ファネル: { phaseKey: { "YYYY-MM": count, "TOTAL": count } }
function aggregateFunnelMonthly(records) {
  const result = {};
  PHASE_DEFS.forEach(def => { result[def.key] = { TOTAL: 0 }; });

  records.forEach(rec => {
    PHASE_DEFS.forEach(def => {
      const dt = rec.arrivals[def.key];
      if (!dt) return;
      const mk = monthKey(dt);
      result[def.key][mk] = (result[def.key][mk] || 0) + 1;
      result[def.key].TOTAL += 1;
    });
  });
  return result;
}

// チャネル別: { channel: { "YYYY-MM": count, "TOTAL": count } }
function aggregateChannelMonthly(records) {
  const mapping = getChannelMapping();
  const result = {};
  records.forEach(rec => {
    const dt = rec.arrivals.entry;
    if (!dt) return;
    const ch = mapping[rec.channel] || rec.channel || "(未分類)";
    if (!result[ch]) result[ch] = { TOTAL: 0 };
    const mk = monthKey(dt);
    result[ch][mk] = (result[ch][mk] || 0) + 1;
    result[ch].TOTAL += 1;
  });
  return result;
}

// アクティブ: { stage: count }
function aggregateActive(records) {
  const result = {};
  ACTIVE_STAGES.forEach(s => { result[s] = 0; });
  records.forEach(rec => {
    if (rec.status !== "選考中") return;
    if (!(rec.currentStage in result)) result[rec.currentStage] = 0;
    result[rec.currentStage] += 1;
  });
  return result;
}

// リードタイム: { transitionKey: { samples:[日数...], avg, median, p90 } }
// transitions: 主要フェーズ間遷移を計算
const LEADTIME_TRANSITIONS = [
  { key: "entry_to_info",     from: "entry",        to: "info_joined",   label: "エントリー → 説明選考会参加" },
  { key: "info_to_first",     from: "info_joined",  to: "first_joined",  label: "説明選考会参加 → 1次面接参加" },
  { key: "first_to_pass",     from: "first_joined", to: "first_passed",  label: "1次面接参加 → 1次面接合格" },
  { key: "pass_to_oneday",    from: "first_passed", to: "oneday_joined", label: "1次合格 → 1day参加" },
  { key: "oneday_to_pass",    from: "oneday_joined",to: "oneday_passed", label: "1day参加 → 1day合格" },
  { key: "oneday_to_twoday",  from: "oneday_passed",to: "twoday_joined", label: "1day合格 → 2day参加" },
  { key: "twoday_to_second",  from: "twoday_passed",to: "second_joined", label: "2day合格 → 役員面接参加" },
  { key: "second_to_final",   from: "second_joined",to: "final_joined",  label: "役員面接 → 最終面接" },
  { key: "final_to_offer",    from: "final_joined", to: "offer",         label: "最終面接 → 内定" },
  { key: "offer_to_accept",   from: "offer",        to: "accepted",      label: "内定 → 内定承諾" },
];

function aggregateLeadtime(records) {
  const result = {};
  LEADTIME_TRANSITIONS.forEach(t => { result[t.key] = { samples: [] }; });

  records.forEach(rec => {
    LEADTIME_TRANSITIONS.forEach(t => {
      const a = rec.arrivals[t.from];
      const b = rec.arrivals[t.to];
      if (!a || !b) return;
      const diffDays = (b - a) / (24 * 60 * 60 * 1000);
      if (diffDays < 0 || diffDays > 365) return; // 異常値除外
      result[t.key].samples.push(diffDays);
    });
  });

  Object.values(result).forEach(r => {
    const arr = r.samples.slice().sort((a, b) => a - b);
    r.count  = arr.length;
    r.avg    = arr.length ? arr.reduce((s, n) => s + n, 0) / arr.length : null;
    r.median = arr.length ? arr[Math.floor(arr.length / 2)] : null;
    r.p90    = arr.length ? arr[Math.floor(arr.length * 0.9)] : null;
    r.min    = arr.length ? arr[0] : null;
    r.max    = arr.length ? arr[arr.length - 1] : null;
  });

  return result;
}

// 辞退・離脱: 選考状況 != "選考中" の候補者を最終到達フェーズ別に集計
// + 各フェーズ通過者数を用いた離脱率
function aggregateAttrition(records) {
  // フェーズごとの「到達者数」と「離脱者数（そのフェーズで止まった人）」を計算
  const phaseKeys = PHASE_DEFS.map(d => d.key);
  const reached = {}; phaseKeys.forEach(k => { reached[k] = 0; });
  const declinedAt = {}; phaseKeys.forEach(k => { declinedAt[k] = 0; });

  let totalActive = 0, totalDeclined = 0, totalAccepted = 0, totalOffered = 0;

  records.forEach(rec => {
    // 到達フェーズ集計（順序通り）
    let lastReachedKey = null;
    PHASE_DEFS.forEach(def => {
      if (rec.arrivals[def.key]) {
        reached[def.key]++;
        lastReachedKey = def.key;
      }
    });

    const isActive = rec.status === "選考中";
    if (isActive) {
      totalActive++;
    } else {
      // 選考中でない=離脱(辞退/不合格/内定承諾済み)
      // 内定承諾済みは離脱扱いしない（=ゴール）
      if (rec.arrivals.accepted) {
        totalAccepted++;
      } else {
        totalDeclined++;
        if (lastReachedKey) declinedAt[lastReachedKey]++;
      }
    }
    if (rec.arrivals.offer) totalOffered++;
  });

  const rates = {};
  phaseKeys.forEach(k => {
    rates[k] = reached[k] ? declinedAt[k] / reached[k] : null;
  });

  return {
    reached,
    declinedAt,
    rates,
    summary: {
      total: records.length,
      active: totalActive,
      declined: totalDeclined,
      accepted: totalAccepted,
      offered: totalOffered,
      acceptRate: totalOffered ? totalAccepted / totalOffered : null,
    },
  };
}

// 評価ランク: { phaseKey: { S, A, B, C, D, TOTAL } }
const RANK_PHASE_KEYS = ["info_joined", "first_joined", "oneday_joined", "twoday_joined", "second_joined", "final_joined"];
const RANK_PHASE_LABELS = {
  info_joined:   "説明選考会",
  first_joined:  "1次面接",
  oneday_joined: "1day",
  twoday_joined: "2day",
  second_joined: "役員面接",
  final_joined:  "最終面接",
};

function aggregateRanking(records) {
  const result = {};
  RANK_PHASE_KEYS.forEach(k => {
    result[k] = { S: 0, A: 0, B: 0, C: 0, D: 0, TOTAL: 0 };
  });
  records.forEach(rec => {
    Object.entries(rec.evals).forEach(([phase, rank]) => {
      if (!result[phase]) return;
      result[phase][rank] = (result[phase][rank] || 0) + 1;
      result[phase].TOTAL += 1;
    });
  });
  return result;
}

// ランク月別: { phaseKey: { "YYYY-MM": { S, A, B, C, D, TOTAL } } }
function aggregateRankingByMonth(records) {
  const result = {};
  RANK_PHASE_KEYS.forEach(k => { result[k] = {}; });

  // 評価キー → 対応する到達日フェーズキー（同じフェーズの参加日を使う）
  const phaseArrivalMap = {
    info_joined:   "info_joined",
    first_joined:  "first_joined",
    oneday_joined: "oneday_joined",
    twoday_joined: "twoday_joined",
    second_joined: "second_joined",
    final_joined:  "final_joined",
  };

  records.forEach(rec => {
    Object.entries(rec.evals).forEach(([phase, rank]) => {
      if (!result[phase]) return;
      const arrivalKey = phaseArrivalMap[phase];
      const dt = arrivalKey ? rec.arrivals[arrivalKey] : null;
      if (!dt) return;
      const mk = monthKey(dt);
      if (!result[phase][mk]) result[phase][mk] = { S: 0, A: 0, B: 0, C: 0, D: 0, TOTAL: 0 };
      result[phase][mk][rank] = (result[phase][mk][rank] || 0) + 1;
      result[phase][mk].TOTAL += 1;
    });
  });
  return result;
}

// 採用着地予想: 各フェーズのアクティブ人数 × 残りの累積通過率 = 内定到達期待値
//   通過率は 001_採用目標 タブのフェーズ間転換率（targets[next] / targets[prev]）から取得
function aggregateLanding(records, targetsFun) {
  const aStats = aggregateActive(records);
  const fStats = aggregateFunnelMonthly(records);

  // 累計目標値からフェーズ間平均通過率を計算
  const cumTargets = {};
  PHASE_DEFS.forEach(def => {
    cumTargets[def.key] = Object.values(targetsFun[def.key] || {}).reduce((s, n) => s + n, 0);
  });

  // 各フェーズの「次フェーズへの通過率」
  const passRates = {};
  PHASE_DEFS.forEach((def, i) => {
    const next = PHASE_DEFS[i + 1];
    if (!next) { passRates[def.key] = null; return; }
    const t1 = cumTargets[def.key];
    const t2 = cumTargets[next.key];
    passRates[def.key] = t1 ? t2 / t1 : null;
  });

  // フェーズ → そのフェーズに「現在いる」人数のマッピング
  // 現在の選考段階の値とPHASE_DEFSのキーを対応づける
  const stageToPhase = {
    "エントリー":              "entry",
    "説明選考会【予約】":      "entry",  // 説明選考会への移行待ち = entry段階
    "説明選考会【参加】":      "info_joined",
    "一次面接【予約】":        "info_joined",
    "一次面接【参加】":        "first_joined",
    "一次面接【合格】":        "first_passed",
    "1dayインターン【予約】":  "first_passed",
    "1dayインターン【参加】":  "oneday_joined",
    "1dayインターン【合格】":  "oneday_passed",
    "2daysインターン【予約】": "oneday_passed",
    "2daysインターン【参加】": "twoday_joined",
    "2daysインターン【合格】": "twoday_passed",
    "二次面接【予約】":        "twoday_passed",
    "二次面接【参加】":        "second_joined",
    "二次面接【合格】":        "second_passed",
    "最終選考【予約】":        "second_passed",
    "最終選考【参加】":        "final_joined",
    "内定":                    "offer",
    "内定承諾":                "accepted",
  };

  // 各フェーズの「現在地」アクティブ数
  const currentAt = {};
  PHASE_DEFS.forEach(d => { currentAt[d.key] = 0; });
  Object.entries(aStats).forEach(([stage, n]) => {
    const p = stageToPhase[stage];
    if (p) currentAt[p] = (currentAt[p] || 0) + n;
  });

  // 各フェーズから内定承諾までの累積通過率を計算
  const acceptedIdx = PHASE_DEFS.findIndex(d => d.key === "accepted");
  const result = [];
  PHASE_DEFS.forEach((def, i) => {
    let cumProb = 1;
    for (let j = i; j < acceptedIdx; j++) {
      const r = passRates[PHASE_DEFS[j].key];
      if (r === null) { cumProb = null; break; }
      cumProb *= r;
    }
    const expected = (cumProb === null) ? null : currentAt[def.key] * cumProb;
    result.push({
      key: def.key,
      label: def.label + (def.group === "pass" ? "（合格）" : ""),
      active: currentAt[def.key] || 0,
      passRate: cumProb,
      expectedAccept: expected,
    });
  });

  const totalExpected = result.reduce((s, r) => s + (r.expectedAccept || 0), 0);
  // すでに内定承諾済みの実績も足す
  const alreadyAccepted = fStats.accepted?.TOTAL || 0;

  return { rows: result, totalExpected, alreadyAccepted, grandTotal: totalExpected + alreadyAccepted };
}

// 累積歩留まり: 「そのフェーズ以降のいずれかに到達した人数」で計算
//   → 内定承諾に近づくほど数値が単調減少する
// { phaseKey: { cumActual, cumRate(対エントリー比), monthlyRates: { ym: rate } } }
function aggregateYield(records) {
  const totalEntry = records.filter(r => r.arrivals.entry).length;
  const months = buildMonthList();

  // フェーズインデックスでスライス: そのフェーズ以降のどれかに到達 = カウント対象
  const result = {};
  PHASE_DEFS.forEach((def, idx) => {
    const futurePhases = PHASE_DEFS.slice(idx);
    const reachedRecords = records.filter(rec =>
      futurePhases.some(d => rec.arrivals[d.key])
    );
    const cumActual = reachedRecords.length;

    const monthlyRates = {};
    months.forEach(m => {
      // 月別: エントリーがその月の人 + そのフェーズ以降に到達した人
      const monthEntries = records.filter(r =>
        r.arrivals.entry && monthKey(r.arrivals.entry) === m.ym
      );
      const denom = monthEntries.length;
      const monthReached = monthEntries.filter(rec =>
        futurePhases.some(d => rec.arrivals[d.key])
      ).length;
      monthlyRates[m.ym] = denom ? monthReached / denom : null;
    });

    result[def.key] = {
      cumActual,
      cumRate: totalEntry ? cumActual / totalEntry : null,
      monthlyRates,
    };
  });
  return result;
}

// ─────────────────────────────────────────
// §5  目標比較
// ─────────────────────────────────────────

// 001_採用目標 → { phaseKey: { "YYYY-MM": target } }
// 003_01のラベルと001の行ラベルを対応させる
const TARGET_PHASE_ROW_LABELS = {
  entry:         ["エントリー数"],
  info_joined:   ["GD選考"],
  info_passed:   ["GD選考_合格者数"],
  first_joined:  ["1次面接"],
  first_passed:  ["1次選考_合格者数", "1次面接_合格者数"],
  oneday_joined: ["1dayインターンシップ"],
  oneday_passed: ["1dayインターン_合格者数"],
  twoday_joined: ["2daysインターンシップ"],
  twoday_passed: ["2daysインターン_合格者数"],
  second_joined: ["役員面接"],
  second_passed: ["役員面接_合格者数"],
  final_joined:  ["最終面接"],
  offer:         ["内定者数"],
  accepted:      ["内定承諾数"],
};

function loadTargetsFunnel() {
  const { targetFun } = getInputSheetNames();
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(targetFun);
  if (!sheet) return {};
  const data = sheet.getDataRange().getValues();

  // 月ヘッダ行を見つける (「対象月」のある行)
  let monthRowIdx = -1, yearRowIdx = -1;
  for (let i = 0; i < data.length; i++) {
    const cellA = String(data[i][1] || "").trim();
    if (cellA === "対象月") { monthRowIdx = i; break; }
  }
  if (monthRowIdx < 0) return {};
  yearRowIdx = monthRowIdx - 1;

  // 列ごとに {year, month} を構築
  const yearRow  = data[yearRowIdx];
  const monthRow = data[monthRowIdx];
  let currentYear = null;
  const colToYM = {};
  for (let c = 0; c < monthRow.length; c++) {
    const yv = String(yearRow[c] || "").trim();
    const mv = String(monthRow[c] || "").trim();
    if (/^\d{4}$/.test(yv)) currentYear = parseInt(yv, 10);
    if (currentYear && /^\d{1,2}$/.test(mv)) {
      colToYM[c] = `${currentYear}-${String(mv).padStart(2, "0")}`;
    }
  }

  // 各フェーズの行を探して値を抽出
  const result = {};
  Object.entries(TARGET_PHASE_ROW_LABELS).forEach(([phaseKey, labels]) => {
    result[phaseKey] = {};
    for (let i = 0; i < data.length; i++) {
      const rowLabel = String(data[i][1] || "").trim();
      if (!labels.some(l => rowLabel === l)) continue;
      Object.entries(colToYM).forEach(([col, ym]) => {
        const raw = data[i][parseInt(col, 10)];
        const n = _parseTargetCell(raw);
        if (n !== null) result[phaseKey][ym] = n;
      });
      break;
    }
  });
  return result;
}

function _parseTargetCell(v) {
  if (v === null || v === undefined || v === "" || v === "-") return null;
  const s = String(v).replace(/[名回%]/g, "").trim();
  if (s === "") return null;
  const n = Number(s);
  if (isNaN(n)) return null;
  // 計算式由来の小数値は四捨五入して整数化
  return Math.round(n);
}

// 003_ver1.1 → { channelName: { "YYYY-MM": target } }
function loadTargetsChannel() {
  const { targetCh } = getInputSheetNames();
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(targetCh);
  if (!sheet) return {};
  const data = sheet.getDataRange().getValues();

  // 月行を探す: 4月, 5月... が並ぶ行
  let monthRowIdx = -1;
  for (let i = 0; i < data.length; i++) {
    const labels = data[i].map(c => String(c || "").trim());
    if (labels.includes("4月") && labels.includes("5月")) { monthRowIdx = i; break; }
  }
  if (monthRowIdx < 0) return {};

  // 月ヘッダ列の位置をマップ。各月は「目標/実績/差分」3列のうち先頭が目標
  // → 月ラベルの次の3列目（「目標」ラベル列）が目標カラム
  const subHeaderRowIdx = monthRowIdx + 3; // 「目標 / 実績 / 差分」が並ぶ行
  if (subHeaderRowIdx >= data.length) return {};
  const subHeader = data[subHeaderRowIdx];

  // 月ラベル → 目標列インデックス
  const monthRow = data[monthRowIdx];
  const monthToTargetCol = {};
  for (let c = 0; c < monthRow.length; c++) {
    const m = String(monthRow[c] || "").trim();
    const mm = m.match(/^(\d{1,2})月$/);
    if (!mm) continue;
    // c〜c+5 範囲で「目標」サブヘッダを探す
    for (let cc = c; cc < Math.min(c + 5, subHeader.length); cc++) {
      if (String(subHeader[cc] || "").trim() === "目標") {
        monthToTargetCol[mm[1]] = cc;
        break;
      }
    }
  }
  if (Object.keys(monthToTargetCol).length === 0) return {};

  // 年度開始月から年を割り当てる（例: 開始4月 → 4-12月=2025年扱い、1-3月=翌年扱い）
  // ※今期年度はcfg「対象年度開始月/終了月」から判定。シンプルに：開始月以降は同年、それより前は翌年
  const cfg = getConfig();
  const baseYear = new Date().getFullYear();
  const startMonth = parseInt(cfg["対象年度開始月"] || "4", 10);

  // 見出し風の文字列を弾くフィルタ
  const isHeaderLike = s => {
    const lower = s.toLowerCase();
    return s.includes("社名") || s.includes("サービス名") ||
           s === "カテゴリ" || s === "合計" || lower === "total";
  };

  const result = {};
  // チャネル名はC列（index 2）
  for (let i = subHeaderRowIdx + 1; i < data.length; i++) {
    const ch = String(data[i][2] || "").trim();
    if (!ch || ch === "-" || isHeaderLike(ch)) continue;
    if (!result[ch]) result[ch] = {};
    Object.entries(monthToTargetCol).forEach(([m, col]) => {
      const n = _parseTargetCell(data[i][col]);
      if (n === null) return;
      const month = parseInt(m, 10);
      const year = month >= startMonth ? baseYear : baseYear + 1;
      const ym = `${year}-${String(month).padStart(2, "0")}`;
      result[ch][ym] = n;
    });
  }
  return result;
}

// 達成率 → カラー
function rateToColor(rate) {
  if (rate === null || isNaN(rate)) return COLOR.bgRow;
  if (rate >= 1.0) return COLOR.ok;
  if (rate >= 0.7) return COLOR.warn;
  return COLOR.alert;
}

// ─────────────────────────────────────────
// §6  描画エンジン
// ─────────────────────────────────────────

// 月リスト生成: 開始月から12ヶ月分
function buildMonthList() {
  const cfg = getConfig();
  const startMonth = parseInt(cfg["対象年度開始月"] || "4", 10);
  const baseYear = new Date().getFullYear();
  const result = [];
  for (let i = 0; i < 13; i++) {
    const mIdx = (startMonth - 1 + i) % 12;
    const month = mIdx + 1;
    const year = i < (12 - startMonth + 1) ? baseYear : baseYear + 1;
    result.push({
      ym: `${year}-${String(month).padStart(2, "0")}`,
      label: `${month}月`,
      year, month,
    });
  }
  return result;
}

function _getOrCreateSheet(name) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(name);
  if (!sheet) sheet = ss.insertSheet(name);
  return sheet;
}

function _clearSheet(sheet) {
  sheet.getRange(1, 1, sheet.getMaxRows(), sheet.getMaxColumns()).breakApart();
  sheet.setFrozenRows(0);
  sheet.setFrozenColumns(0);
  sheet.clearContents();
  sheet.clearFormats();
  // デフォルトのグリッド線は非表示。ユーザーが手動で必要な線を引く方針
  sheet.setHiddenGridlines(true);
}

// セクション見出し（■ XXX）をマージしてバー表示
function _renderSectionHeader(sheet, row, totalCols, text) {
  sheet.getRange(row, 1, 1, totalCols).merge().setValue(text)
    .setBackground(COLOR.totalBg).setFontColor(COLOR.textMain)
    .setFontWeight("bold").setFontSize(11).setFontFamily(FONT_HEAD)
    .setHorizontalAlignment("left").setVerticalAlignment("middle")
    .setBorder(true, true, true, true, false, false, COLOR.bgDark, SpreadsheetApp.BorderStyle.SOLID);
  sheet.setRowHeight(row, 28);
}

// タイトル行をマージしてバナー化する。固定列に配慮して分割マージできる
//   sheet:   対象シート
//   row:     行番号
//   totalCols: 全列数
//   frozenCols: 固定列数（0/1/2）
//   title:   左側に表示するメインタイトル
//   subtitle: 右側に表示するサブ情報（タイムスタンプなど）
function _renderTitleBar(sheet, row, totalCols, frozenCols, title, subtitle) {
  const fullText = subtitle ? `${title}  ／  ${subtitle}` : title;
  if (frozenCols === 0 || frozenCols >= totalCols) {
    sheet.getRange(row, 1, 1, totalCols).merge().setValue(fullText);
  } else if (frozenCols === 1) {
    // A列はタイトル、B列以降はサブ情報
    sheet.getRange(row, 1).setValue(title);
    if (totalCols > 1) {
      sheet.getRange(row, 2, 1, totalCols - 1).merge();
      if (subtitle) sheet.getRange(row, 2).setValue(subtitle);
    }
  } else {
    // frozenCols === 2 想定: A1:B1 と C1:end をそれぞれマージ
    sheet.getRange(row, 1, 1, 2).merge().setValue(title);
    if (totalCols > 2) {
      sheet.getRange(row, 3, 1, totalCols - 2).merge();
      if (subtitle) sheet.getRange(row, 3).setValue(subtitle);
    }
  }
  _applyTitleStyle(sheet.getRange(row, 1, 1, totalCols));
}

// 220_詳細分析（ファネル+目標差分+歩留まり+チャネル+ステータス を1タブに統合）
function renderDetailed(records, targetsFun, targetsCh) {
  const { detail } = getOutputSheetNames();
  const sheet = _getOrCreateSheet(detail);
  _clearSheet(sheet);

  const months = buildMonthList();
  const stats = aggregateFunnelMonthly(records);

  // ─── セクション1: 月次ファネル進捗 ───
  const phaseCols = [];
  PHASE_DEFS.forEach((d, i) => {
    phaseCols.push({ key: d.key, label: d.label });
    if (i < PHASE_DEFS.length - 1) phaseCols.push({ key: `__rate_${d.key}`, label: "→" });
  });
  const funnelCols = 2 + phaseCols.length;

  _renderTitleBar(sheet, 1, funnelCols, 2, "月次ファネル進捗", `自動更新: ${formatDatetime(new Date())}`);

  const header = ["登録日", "月"].concat(phaseCols.map(c => c.label));
  sheet.getRange(2, 1, 1, funnelCols).setValues([header]);
  _applyHeaderStyle(sheet.getRange(2, 1, 1, funnelCols));

  const totalRow = ["", "合計"].concat(phaseCols.map(c => {
    if (c.key.startsWith("__rate_")) return "";
    return stats[c.key]?.TOTAL || 0;
  }));
  sheet.getRange(3, 1, 1, funnelCols).setValues([totalRow]);
  _applyTotalRowStyle(sheet.getRange(3, 1, 1, funnelCols));

  const fRows = [];
  months.forEach(m => {
    const r = ["", m.label];
    phaseCols.forEach((c) => {
      if (c.key.startsWith("__rate_")) {
        const prevKey = c.key.replace("__rate_", "");
        const phaseIdx = PHASE_DEFS.findIndex(d => d.key === prevKey);
        const nextDef  = PHASE_DEFS[phaseIdx + 1];
        if (!nextDef) { r.push(""); return; }
        const prev = stats[prevKey]?.[m.ym] || 0;
        const next = stats[nextDef.key]?.[m.ym] || 0;
        r.push(prev ? `${Math.round(next / prev * 100)}%` : "0%");
      } else {
        r.push(stats[c.key]?.[m.ym] || 0);
      }
    });
    fRows.push(r);
  });
  if (fRows.length) {
    sheet.getRange(4, 1, fRows.length, funnelCols).setValues(fRows);
    _applyDataStyle(sheet.getRange(4, 1, fRows.length, funnelCols));
  }

  // ─── セクション2: 目標差分ヒートマップ ───
  let r2 = 4 + fRows.length + 2;
  const diffCols = 2 + months.length + 1;

  _renderTitleBar(sheet, r2, diffCols, 2, "目標差分ヒートマップ");
  r2++;

  const dHeader = ["フェーズ", "累計達成率"].concat(months.map(m => m.label)).concat(["凡例"]);
  sheet.getRange(r2, 1, 1, diffCols).setValues([dHeader]);
  _applyHeaderStyle(sheet.getRange(r2, 1, 1, diffCols));
  r2++;

  const dRows = [];
  const dColors = [];
  PHASE_DEFS.filter(d => d.group === "main" || d.key === "accepted" || d.key === "offer").forEach(def => {
    const row = [def.label, ""];
    const rowColors = [COLOR.bgRow, COLOR.bgRow];
    let totalTgt = 0, totalAct = 0;
    months.forEach(m => {
      const tgt = targetsFun[def.key]?.[m.ym] ?? 0;
      const act = stats[def.key]?.[m.ym] ?? 0;
      totalTgt += tgt;
      totalAct += act;
      const rate = tgt ? act / tgt : null;
      row.push(tgt ? `${act}/${tgt}` : (act || ""));
      rowColors.push(rateToColor(rate));
    });
    const totalRate = totalTgt ? totalAct / totalTgt : null;
    row[1] = totalTgt ? `${Math.round(totalRate * 100)}%` : "-";
    rowColors[1] = rateToColor(totalRate);
    row.push("");
    rowColors.push(COLOR.bgRow);
    dRows.push(row);
    dColors.push(rowColors);
  });
  if (dRows.length) {
    sheet.getRange(r2, 1, dRows.length, diffCols).setValues(dRows);
    sheet.getRange(r2, 1, dRows.length, diffCols).setBackgrounds(dColors);
    _applyDataStyle(sheet.getRange(r2, 1, dRows.length, diffCols), { keepBg: true });
  }

  // 凡例
  const legendRow = r2 + dRows.length + 1;
  sheet.getRange(legendRow, 1).setValue("凡例:");
  sheet.getRange(legendRow, 2).setValue("≥100%").setBackground(COLOR.ok);
  sheet.getRange(legendRow, 3).setValue("70-99%").setBackground(COLOR.warn);
  sheet.getRange(legendRow, 4).setValue("<70%").setBackground(COLOR.alert);

  // ─── セクション3: 累積歩留まり（エントリー比） ───
  let r3 = legendRow + 2;
  const yieldCols = 2 + months.length;

  _renderTitleBar(sheet, r3, yieldCols, 2, "累積歩留まり（エントリーを100%として各フェーズの通過率）");
  r3++;

  const yHeader = ["フェーズ", "累計実績／率"].concat(months.map(m => m.label));
  sheet.getRange(r3, 1, 1, yieldCols).setValues([yHeader]);
  _applyHeaderStyle(sheet.getRange(r3, 1, 1, yieldCols));
  r3++;

  const yStats = aggregateYield(records);
  const yRows = [];
  const yColors = [];
  PHASE_DEFS.forEach(def => {
    const y = yStats[def.key];
    const row = [def.label + (def.group === "pass" ? "（合格）" : ""),
      y.cumRate === null ? `${y.cumActual}` : `${y.cumActual} (${(y.cumRate * 100).toFixed(1)}%)`];
    const rowColors = [COLOR.bgRow, COLOR.bgRow];
    months.forEach(m => {
      const rate = y.monthlyRates[m.ym];
      row.push(rate === null ? "-" : `${(rate * 100).toFixed(0)}%`);
      // 通過率を色で可視化
      let bg = COLOR.bgRow;
      if (rate !== null) {
        if (rate >= 0.5) bg = COLOR.ok;
        else if (rate >= 0.2) bg = COLOR.warn;
        else if (rate > 0)    bg = COLOR.alert;
      }
      rowColors.push(bg);
    });
    yRows.push(row);
    yColors.push(rowColors);
  });
  sheet.getRange(r3, 1, yRows.length, yieldCols).setValues(yRows);
  sheet.getRange(r3, 1, yRows.length, yieldCols).setBackgrounds(yColors);
  _applyDataStyle(sheet.getRange(r3, 1, yRows.length, yieldCols), { keepBg: true });
  r3 += yRows.length + 1;

  sheet.getRange(r3, 1)
    .setValue("※ 月別セルは各月のエントリー数に対するそのフェーズへの到達率。色: 緑=50%以上 / 黄=20-49% / 赤=20%未満。")
    .setFontColor(COLOR.textDim).setFontSize(9).setFontFamily(FONT_HEAD)
    .setWrap(true);
  sheet.setRowHeight(r3, 32);

  // ===========================================================
  // ─── セクション4: チャネル別実績 ───
  // ===========================================================
  let r4 = r3 + 2;
  const chStats = aggregateChannelMonthly(records);
  const allChannels = new Set([...Object.keys(targetsCh), ...Object.keys(chStats)]);
  const channels = [...allChannels].sort();
  const chCols = 4 + months.length * 3;

  _renderSectionHeader(sheet, r4, chCols, "■ チャネル別実績");
  r4++;

  const ch1 = ["チャネル", "累計目標", "累計実績", "累計差分"];
  const ch2 = ["", "", "", ""];
  months.forEach(m => {
    ch1.push(m.label, "", "");
    ch2.push("目標", "実績", "差分");
  });
  sheet.getRange(r4, 1, 1, chCols).setValues([ch1]);
  sheet.getRange(r4 + 1, 1, 1, chCols).setValues([ch2]);
  months.forEach((m, i) => {
    sheet.getRange(r4, 5 + i * 3, 1, 3).merge();
  });
  _applyHeaderStyle(sheet.getRange(r4, 1, 2, chCols));
  r4 += 2;

  const chRows = [];
  const chRowColors = [];
  channels.forEach(ch => {
    let totalTgt = 0, totalAct = 0;
    const row = [ch, "", "", ""];
    const rowColors = [COLOR.bgRow, COLOR.bgRow, COLOR.bgRow, COLOR.bgRow];
    months.forEach(m => {
      const tgt = targetsCh[ch]?.[m.ym] ?? 0;
      const act = chStats[ch]?.[m.ym] ?? 0;
      const diff = act - tgt;
      totalTgt += tgt;
      totalAct += act;
      row.push(tgt || "", act || "", diff || "");
      const rate = tgt ? act / tgt : null;
      rowColors.push(COLOR.bgRow, rateToColor(rate), diff >= 0 ? COLOR.bgRow : "#FEE2E2");
    });
    row[1] = totalTgt || "";
    row[2] = totalAct || "";
    row[3] = (totalAct - totalTgt) || "";
    rowColors[2] = rateToColor(totalTgt ? totalAct / totalTgt : null);
    rowColors[3] = (totalAct - totalTgt) >= 0 ? COLOR.bgRow : "#FEE2E2";
    chRows.push(row);
    chRowColors.push(rowColors);
  });
  if (chRows.length) {
    sheet.getRange(r4, 1, chRows.length, chCols).setValues(chRows);
    sheet.getRange(r4, 1, chRows.length, chCols).setBackgrounds(chRowColors);
    _applyDataStyle(sheet.getRange(r4, 1, chRows.length, chCols), { keepBg: true });
    r4 += chRows.length;
  }

  // ===========================================================
  // ─── セクション5: アクティブ管理（選考中） ───
  // ===========================================================
  let r = r4 + 2;
  const aStats  = aggregateActive(records);
  const atStats = aggregateAttrition(records);
  const ltStats = aggregateLeadtime(records);

  _renderSectionHeader(sheet, r, 8, "■ アクティブ学生（選考中）");
  r++;

  sheet.getRange(r, 1, 1, 3).setValues([["#", "現在の選考段階", "人数"]]);
  _applyHeaderStyle(sheet.getRange(r, 1, 1, 3));
  r++;

  // ゼロ行を省略してコンパクト化
  const stages = Object.keys(aStats).filter(s => aStats[s] > 0);
  const aRows = stages.map((s, i) => [i + 1, s, aStats[s]]);
  const totalA = stages.reduce((sum, s) => sum + aStats[s], 0);
  aRows.push(["", "合計", totalA]);
  sheet.getRange(r, 1, aRows.length, 3).setValues(aRows);
  _applyDataStyle(sheet.getRange(r, 1, aRows.length, 3));
  _applyTotalRowStyle(sheet.getRange(r + aRows.length - 1, 1, 1, 3));
  r += aRows.length + 2;

  // ─── セクション2: 辞退・離脱 ───
  _renderSectionHeader(sheet, r, 8, "■ 辞退・離脱サマリー");
  r++;

  const sR = atStats.summary;
  const sumRows = [
    ["総候補者数", sR.total, "", "", "", "", ""],
    ["選考中（アクティブ）", sR.active, "", "", "", "", ""],
    ["離脱者（辞退・不合格）", sR.declined, sR.total ? `${Math.round(sR.declined / sR.total * 100)}%` : "-", "", "", "", ""],
    ["内定獲得", sR.offered, "", "", "", "", ""],
    ["内定承諾", sR.accepted, sR.offered ? `${Math.round(sR.acceptRate * 100)}%` : "-", "← 承諾率", "", "", ""],
  ];
  sheet.getRange(r, 1, sumRows.length, 7).setValues(sumRows);
  _applyDataStyle(sheet.getRange(r, 1, sumRows.length, 7));
  r += sumRows.length + 1;

  sheet.getRange(r, 1, 1, 5).setValues([["フェーズ", "到達者数", "離脱者数", "離脱率", "次フェーズへの通過率"]]);
  _applyHeaderStyle(sheet.getRange(r, 1, 1, 5));
  r++;

  const atRows = [];
  const atColors = [];
  // 到達者0のフェーズは省略
  PHASE_DEFS.forEach((def, i) => {
    const reached = atStats.reached[def.key] || 0;
    if (reached === 0) return;
    const declined = atStats.declinedAt[def.key] || 0;
    const declineRate = atStats.rates[def.key];
    const nextDef = PHASE_DEFS[i + 1];
    const passRate = (reached && nextDef) ? (atStats.reached[nextDef.key] || 0) / reached : null;

    atRows.push([
      def.label + (def.group === "pass" ? "（合格）" : ""),
      reached,
      declined,
      declineRate === null ? "-" : `${Math.round(declineRate * 100)}%`,
      passRate === null ? "-" : `${Math.round(passRate * 100)}%`,
    ]);
    const bg = declineRate === null ? COLOR.bgRow :
               declineRate >= 0.3 ? COLOR.alert :
               declineRate >= 0.15 ? COLOR.warn : COLOR.bgRow;
    atColors.push([COLOR.bgRow, COLOR.bgRow, COLOR.bgRow, bg, COLOR.bgRow]);
  });
  if (atRows.length) {
    sheet.getRange(r, 1, atRows.length, 5).setValues(atRows);
    sheet.getRange(r, 1, atRows.length, 5).setBackgrounds(atColors);
    _applyDataStyle(sheet.getRange(r, 1, atRows.length, 5), { keepBg: true });
    r += atRows.length;
  }
  r += 2;

  // ─── セクション3: リードタイム ───
  _renderSectionHeader(sheet, r, 8, "■ リードタイム（フェーズ間日数）");
  r++;

  sheet.getRange(r, 1, 1, 7).setValues([["遷移", "サンプル数", "平均(日)", "中央値(日)", "P90(日)", "最短", "最長"]]);
  _applyHeaderStyle(sheet.getRange(r, 1, 1, 7));
  r++;

  // サンプル0の遷移は省略
  const ltRows = LEADTIME_TRANSITIONS
    .filter(t => ltStats[t.key].count > 0)
    .map(t => {
      const s = ltStats[t.key];
      const fmt = v => v === null ? "-" : v.toFixed(1);
      return [t.label, s.count || 0, fmt(s.avg), fmt(s.median), fmt(s.p90), fmt(s.min), fmt(s.max)];
    });
  if (ltRows.length) {
    sheet.getRange(r, 1, ltRows.length, 7).setValues(ltRows);
    _applyDataStyle(sheet.getRange(r, 1, ltRows.length, 7));
    r += ltRows.length;
  } else {
    sheet.getRange(r, 1).setValue("(データなし)").setFontColor(COLOR.textDim).setFontFamily(FONT_HEAD);
    r++;
  }
  r += 1;

  sheet.getRange(r, 1)
    .setValue("※ 「平均」は外れ値の影響を受けやすいため、運用判断には中央値とP90を併用してください。0日以下や365日超のサンプルは異常値として除外しています。")
    .setFontColor(COLOR.textDim).setFontSize(9).setFontFamily(FONT_HEAD)
    .setWrap(true).setHorizontalAlignment("left");
  sheet.setRowHeight(r, 32);
  r += 2;

  // ─── セクション4: 選考官評価ランク集計（合計） ───
  _renderSectionHeader(sheet, r, 8, "■ 選考官評価ランク（フェーズ別 S/A/B/C/D・合計）");
  r++;

  const rankStats = aggregateRanking(records);

  sheet.getRange(r, 1, 1, 8).setValues([["フェーズ", "S", "A", "B", "C", "D", "合計", "S+A率"]]);
  _applyHeaderStyle(sheet.getRange(r, 1, 1, 8));
  r++;

  const rkRows = [];
  const rkColors = [];
  RANK_PHASE_KEYS.forEach(pk => {
    const s = rankStats[pk];
    const sa = s.S + s.A;
    const saRate = s.TOTAL ? sa / s.TOTAL : null;
    rkRows.push([
      RANK_PHASE_LABELS[pk],
      s.S, s.A, s.B, s.C, s.D,
      s.TOTAL,
      saRate === null ? "-" : `${Math.round(saRate * 100)}%`,
    ]);
    const saColor = saRate === null ? COLOR.bgRow :
                    saRate >= 0.5 ? COLOR.ok :
                    saRate >= 0.3 ? COLOR.warn : COLOR.alert;
    rkColors.push([COLOR.bgRow, COLOR.bgRow, COLOR.bgRow, COLOR.bgRow, COLOR.bgRow, COLOR.bgRow, COLOR.bgRow, saColor]);
  });
  sheet.getRange(r, 1, rkRows.length, 8).setValues(rkRows);
  sheet.getRange(r, 1, rkRows.length, 8).setBackgrounds(rkColors);
  _applyDataStyle(sheet.getRange(r, 1, rkRows.length, 8), { keepBg: true });
  r += rkRows.length + 1;

  // 構成比行
  _renderSectionHeader(sheet, r, 8, "構成比");
  r++;

  sheet.getRange(r, 1, 1, 8).setValues([["フェーズ", "S%", "A%", "B%", "C%", "D%", "", ""]]);
  _applyHeaderStyle(sheet.getRange(r, 1, 1, 8));
  r++;

  const pctRows = RANK_PHASE_KEYS.map(pk => {
    const s = rankStats[pk];
    const pct = rk => s.TOTAL ? `${Math.round(s[rk] / s.TOTAL * 100)}%` : "-";
    return [RANK_PHASE_LABELS[pk], pct("S"), pct("A"), pct("B"), pct("C"), pct("D"), "", ""];
  });
  sheet.getRange(r, 1, pctRows.length, 8).setValues(pctRows);
  _applyDataStyle(sheet.getRange(r, 1, pctRows.length, 8));
  r += pctRows.length + 2;

  // ─── セクション5: 選考官評価ランク 月別（1つのコンパクトマトリクスに統合） ───
  _renderSectionHeader(sheet, r, 8, "■ 選考官評価ランク 月別（フェーズ × ランク × 月）");
  r++;

  const rankByMonth = aggregateRankingByMonth(records);
  const rmCols = 2 + months.length + 1; // フェーズ + ランク + 月別 + 合計

  const rmHeader = ["フェーズ", "ランク"].concat(months.map(m => m.label)).concat(["合計"]);
  sheet.getRange(r, 1, 1, rmCols).setValues([rmHeader]);
  _applyHeaderStyle(sheet.getRange(r, 1, 1, rmCols));
  r++;

  // 全フェーズ × ランクをひとつのテーブルに集約
  // データがあるフェーズだけ表示（全0は省略）
  const rankSumAll = aggregateRanking(records);
  const phaseLabelStart = r; // フェーズラベルマージ開始位置

  RANK_PHASE_KEYS.forEach(pk => {
    if ((rankSumAll[pk]?.TOTAL || 0) === 0) return; // データなしフェーズは省略

    const phaseStartRow = r;
    RANKS.forEach((rk, i) => {
      const row = [i === 0 ? RANK_PHASE_LABELS[pk] : "", rk];
      let totalForRank = 0;
      months.forEach(m => {
        const c = rankByMonth[pk]?.[m.ym]?.[rk] || 0;
        row.push(c || "");
        totalForRank += c;
      });
      row.push(totalForRank || "");
      sheet.getRange(r, 1, 1, rmCols).setValues([row]);
      _applyDataStyle(sheet.getRange(r, 1, 1, rmCols));
      r++;
    });
    // フェーズラベルセル(A列)を5行マージ
    sheet.getRange(phaseStartRow, 1, RANKS.length, 1).merge()
      .setVerticalAlignment("middle").setHorizontalAlignment("left")
      .setFontWeight("bold").setBackground(COLOR.bgRowAlt);
  });

  // データなしの場合のフォールバック
  if (r === phaseLabelStart) {
    sheet.getRange(r, 1).setValue("(評価データなし)").setFontColor(COLOR.textDim).setFontFamily(FONT_HEAD);
    r++;
  }
  r += 1;

  // ─── セクション6: 採用着地予想 ───
  _renderSectionHeader(sheet, r, 8, "■ 採用着地予想（アクティブ × 標準通過率）");
  r++;

  const landing = aggregateLanding(records, targetsFun);

  sheet.getRange(r, 1, 1, 4).setValues([["フェーズ", "現在のアクティブ", "内定承諾までの累積通過率", "内定承諾期待値"]]);
  _applyHeaderStyle(sheet.getRange(r, 1, 1, 4));
  r++;

  // アクティブ0のフェーズは省略
  const ldRows = landing.rows
    .filter(row => row.active > 0)
    .map(row => [
      row.label,
      row.active,
      row.passRate === null ? "-" : `${(row.passRate * 100).toFixed(1)}%`,
      row.expectedAccept === null ? "-" : row.expectedAccept.toFixed(1),
    ]);
  if (ldRows.length) {
    sheet.getRange(r, 1, ldRows.length, 4).setValues(ldRows);
    _applyDataStyle(sheet.getRange(r, 1, ldRows.length, 4));
    r += ldRows.length;
  }

  // 合計行
  sheet.getRange(r, 1, 1, 4).setValues([[
    "アクティブからの期待値合計",
    "",
    "",
    landing.totalExpected.toFixed(1),
  ]]);
  _applyTotalRowStyle(sheet.getRange(r, 1, 1, 4));
  r++;
  sheet.getRange(r, 1, 1, 4).setValues([[
    "既に内定承諾済み",
    "",
    "",
    landing.alreadyAccepted,
  ]]);
  _applyDataStyle(sheet.getRange(r, 1, 1, 4));
  r++;
  sheet.getRange(r, 1, 1, 4).setValues([[
    "最終着地予想（合計）",
    "",
    "",
    landing.grandTotal.toFixed(1),
  ]]);
  _applyTotalRowStyle(sheet.getRange(r, 1, 1, 4));
  sheet.getRange(r, 1, 1, 4).setFontSize(12);
  r++;

  sheet.getRange(r, 1)
    .setValue("※ 通過率は001_採用目標の累計値から「次フェーズ目標 ÷ 現フェーズ目標」で算出。実績のブレや評価ランク補正は未反映のシンプル版です。")
    .setFontColor(COLOR.textDim).setFontSize(9).setFontFamily(FONT_HEAD)
    .setWrap(true);
  sheet.setRowHeight(r, 32);

  // ===========================================================
  // 列幅・固定行（全セクション共通の最終設定）
  // ===========================================================
  const totalMaxCols = Math.max(funnelCols, diffCols, yieldCols, chCols);
  sheet.setColumnWidth(1, 200);
  sheet.setColumnWidth(2, 130);
  for (let c = 3; c <= totalMaxCols; c++) sheet.setColumnWidth(c, 76);
  sheet.setFrozenRows(2);
}

// 230_バイネーム管理（候補者個別リスト）
//   各学生1行で、現在の状況・経過日数・直近活動・最終評価・リスクフラグを一覧表示
function renderByName(records) {
  const { byname } = getOutputSheetNames();
  const sheet = _getOrCreateSheet(byname);
  _clearSheet(sheet);

  const now = new Date();
  const channelMap = getChannelMapping();

  // ヘッダ定義
  const headers = [
    "#", "ID", "姓", "名", "学校名",
    "経路", "現在の選考段階", "選考状況",
    "エントリー日", "経過日数",
    "次回選考種別", "次回予約日",
    "直近の評価", "直近フェーズ",
    "直近活動日", "停滞日数",
    "リスク",
  ];
  const cols = headers.length;

  _renderTitleBar(sheet, 1, cols, 2, "バイネーム管理", `自動更新: ${formatDatetime(now)}　|　${records.length}名`);

  sheet.getRange(2, 1, 1, cols).setValues([headers]);
  _applyHeaderStyle(sheet.getRange(2, 1, 1, cols));

  // 最終的に到達したフェーズと評価を抽出
  const enrichedRows = records.map((rec, i) => {
    const entryDt = rec.arrivals.entry;
    const entryDays = entryDt ? Math.floor((now - entryDt) / (24 * 60 * 60 * 1000)) : null;

    // 直近活動日（全フェーズの最大到達日）
    let lastActivity = null, lastPhaseLabel = "";
    PHASE_DEFS.forEach(def => {
      const d = rec.arrivals[def.key];
      if (d && (!lastActivity || d > lastActivity)) {
        lastActivity = d;
        lastPhaseLabel = def.label;
      }
    });
    const stagnantDays = lastActivity ? Math.floor((now - lastActivity) / (24 * 60 * 60 * 1000)) : null;

    // 直近の評価（最後のフェーズ評価を採用）
    let latestEval = "", latestEvalPhase = "";
    const evalOrder = ["final_joined", "second_joined", "twoday_joined", "oneday_joined", "first_joined", "info_joined"];
    for (const ek of evalOrder) {
      if (rec.evals[ek]) {
        latestEval = rec.evals[ek];
        latestEvalPhase = RANK_PHASE_LABELS[ek] || ek;
        break;
      }
    }

    // 次回選考種別と予約日
    let nextStageName = "", nextReserveDate = "", nextStatus = "";
    if (rec.status === "選考中") {
      const nextDef = NEXT_STAGE_MAP[rec.currentStage];
      if (nextDef && nextDef.arrivalHeader) {
        nextStageName = nextDef.name;
        const reserveDt = rec.rawArrivals?.[nextDef.arrivalHeader];
        if (reserveDt) {
          nextReserveDate = formatDate(reserveDt);
          nextStatus = "予約済";
        } else {
          nextReserveDate = "未予約";
          nextStatus = "未予約";
        }
      } else if (nextDef) {
        nextStageName = nextDef.name;
        nextReserveDate = "-";
      }
    }

    // リスクフラグ
    const flags = [];
    if (rec.status === "選考中") {
      if (nextStatus === "未予約" && stagnantDays !== null && stagnantDays > 7) {
        flags.push("未予約+停滞");
      } else if (nextStatus === "未予約") {
        flags.push("未予約");
      } else if (stagnantDays !== null && stagnantDays > 14) {
        flags.push("停滞14日超");
      } else if (stagnantDays !== null && stagnantDays > 7) {
        flags.push("停滞7日超");
      }
    } else if (rec.arrivals.accepted) {
      flags.push("承諾");
    } else {
      flags.push("離脱");
    }
    if (latestEval === "S") flags.push("S評価");
    if (latestEval === "D") flags.push("D評価");

    return {
      row: [
        i + 1, rec.id, rec.lastName, rec.firstName,
        rec.school,
        channelMap[rec.channel] || rec.channel,
        rec.currentStage, rec.status,
        entryDt ? formatDate(entryDt) : "",
        entryDays === null ? "" : entryDays,
        nextStageName || "-",
        nextReserveDate || "-",
        latestEval || "-",
        latestEvalPhase || "-",
        lastActivity ? formatDate(lastActivity) : "",
        stagnantDays === null ? "" : stagnantDays,
        flags.join(" / "),
      ],
      stagnantDays,
      isActive: rec.status === "選考中",
      latestEval,
      nextStatus,
    };
  });

  // 並び替え: 選考中 → 停滞日数降順
  enrichedRows.sort((a, b) => {
    if (a.isActive !== b.isActive) return a.isActive ? -1 : 1;
    return (b.stagnantDays || 0) - (a.stagnantDays || 0);
  });

  const dataRows = enrichedRows.map((e, i) => {
    e.row[0] = i + 1; // 連番振り直し
    return e.row;
  });

  // 行ごとの背景色（リスクに応じて）
  const dataColors = enrichedRows.map(e => {
    const bg = !e.isActive ? COLOR.bgRowAlt :
               (e.stagnantDays !== null && e.stagnantDays > 14) ? COLOR.alert :
               (e.stagnantDays !== null && e.stagnantDays > 7) ? COLOR.warn :
               COLOR.bgRow;
    return new Array(cols).fill(bg);
  });

  if (dataRows.length) {
    sheet.getRange(3, 1, dataRows.length, cols).setValues(dataRows);
    sheet.getRange(3, 1, dataRows.length, cols).setBackgrounds(dataColors);
    _applyDataStyle(sheet.getRange(3, 1, dataRows.length, cols), { keepBg: true });
  }

  // 列幅
  const widths = [40, 70, 60, 60, 200, 110, 160, 80, 100, 80, 110, 100, 80, 110, 100, 80, 200];
  widths.forEach((w, i) => sheet.setColumnWidth(i + 1, w));
  sheet.setFrozenRows(2);
  sheet.setFrozenColumns(2);
}

// 210_ダッシュボード（経営層向け1枚KPI）
function renderDashboard(records, targetsFun, targetsCh) {
  const { dashboard } = getOutputSheetNames();
  const sheet = _getOrCreateSheet(dashboard);
  _clearSheet(sheet);

  const cfg = getConfig();
  const company = String(cfg["企業名"] || "").trim();
  const now = new Date();
  const currentYM = monthKey(now);

  const fStats = aggregateFunnelMonthly(records);
  const aStats = aggregateActive(records);

  // タイトル（16列横断）
  sheet.getRange(1, 1, 1, 16).merge().setValue(`${company}   ／   RPO ダッシュボード`)
    .setBackground(COLOR.bgDark).setFontColor(COLOR.fgWhite)
    .setFontSize(14).setFontFamily(FONT_HEAD).setFontWeight("bold")
    .setHorizontalAlignment("left").setVerticalAlignment("middle");
  sheet.setRowHeight(1, 40);

  sheet.getRange(2, 1, 1, 16).merge().setValue(`自動更新: ${formatDatetime(now)}　|　対象月: ${currentYM}`)
    .setBackground(COLOR.totalBg).setFontColor(COLOR.textDim)
    .setFontSize(10).setFontFamily(FONT_HEAD)
    .setHorizontalAlignment("left").setVerticalAlignment("middle");
  sheet.setRowHeight(2, 24);

  // 主要KPIサマリー: エントリー / 説明選考会参加 / 1次面接合格 / 内定承諾
  let r = 4;
  _renderSectionHeader(sheet, r, 9, "■ 主要KPI サマリー");
  r++;

  // 前月キー
  const nowDt = now;
  const prevDt = new Date(nowDt.getFullYear(), nowDt.getMonth() - 1, 1);
  const prevYM = monthKey(prevDt);

  const cards = [
    { key: "entry",        label: "エントリー" },
    { key: "info_joined",  label: "説明選考会参加" },
    { key: "first_passed", label: "1次面接合格" },
    { key: "accepted",     label: "内定承諾" },
  ];

  sheet.getRange(r, 1, 1, 9).setValues([
    ["指標"].concat(cards.flatMap(c => [c.label, ""])).slice(0, 9),
  ]);
  // ヘッダの2セル毎をマージしてラベルを横方向に
  cards.forEach((c, i) => {
    sheet.getRange(r, 2 + i * 2, 1, 2).merge();
  });
  _applyHeaderStyle(sheet.getRange(r, 1, 1, 9));
  r++;

  const cardActuals = cards.map(c => fStats[c.key]?.[currentYM] || 0);
  const cardPrev    = cards.map(c => fStats[c.key]?.[prevYM] || 0);
  const cardCum     = cards.map(c => fStats[c.key]?.TOTAL || 0);
  const cardTargets = cards.map(c => targetsFun[c.key]?.[currentYM] || 0);
  const cardRates   = cardTargets.map((t, i) => t ? cardActuals[i] / t : null);

  // 当月実績行（大きい数字）
  const actRow = ["当月実績"].concat(cards.flatMap((c, i) => [cardActuals[i], ""])).slice(0, 9);
  sheet.getRange(r, 1, 1, 9).setValues([actRow]);
  cards.forEach((c, i) => sheet.getRange(r, 2 + i * 2, 1, 2).merge());
  _applyDataStyle(sheet.getRange(r, 1, 1, 9));
  sheet.getRange(r, 2, 1, 8).setFontSize(18).setFontWeight("bold");
  sheet.setRowHeight(r, 40);
  r++;

  // 当月目標 / 達成率
  const tgtRow = ["当月目標"].concat(cards.flatMap((c, i) => [cardTargets[i] || "-", ""])).slice(0, 9);
  sheet.getRange(r, 1, 1, 9).setValues([tgtRow]);
  cards.forEach((c, i) => sheet.getRange(r, 2 + i * 2, 1, 2).merge());
  _applyDataStyle(sheet.getRange(r, 1, 1, 9));
  r++;

  const rateRow = ["達成率"].concat(cards.flatMap((c, i) => [
    cardRates[i] === null ? "-" : `${Math.round(cardRates[i] * 100)}%`, "",
  ])).slice(0, 9);
  sheet.getRange(r, 1, 1, 9).setValues([rateRow]);
  cards.forEach((c, i) => sheet.getRange(r, 2 + i * 2, 1, 2).merge());
  cards.forEach((c, i) => {
    const color = rateToColor(cardRates[i]);
    sheet.getRange(r, 2 + i * 2, 1, 2).setBackground(color);
  });
  _applyDataStyle(sheet.getRange(r, 1, 1, 9), { keepBg: true });
  sheet.getRange(r, 2, 1, 8).setFontWeight("bold").setFontSize(12);
  r++;

  // 前月 / 前月比
  const prevRow = ["前月実績"].concat(cards.flatMap((c, i) => [cardPrev[i], ""])).slice(0, 9);
  sheet.getRange(r, 1, 1, 9).setValues([prevRow]);
  cards.forEach((c, i) => sheet.getRange(r, 2 + i * 2, 1, 2).merge());
  _applyDataStyle(sheet.getRange(r, 1, 1, 9));
  r++;

  const diffRow = ["前月差"].concat(cards.flatMap((c, i) => {
    const d = cardActuals[i] - cardPrev[i];
    return [d > 0 ? `+${d}` : `${d}`, ""];
  })).slice(0, 9);
  sheet.getRange(r, 1, 1, 9).setValues([diffRow]);
  cards.forEach((c, i) => sheet.getRange(r, 2 + i * 2, 1, 2).merge());
  _applyDataStyle(sheet.getRange(r, 1, 1, 9));
  r++;

  // 累計
  const cumRow = ["年度累計"].concat(cards.flatMap((c, i) => [cardCum[i], ""])).slice(0, 9);
  sheet.getRange(r, 1, 1, 9).setValues([cumRow]);
  cards.forEach((c, i) => sheet.getRange(r, 2 + i * 2, 1, 2).merge());
  _applyDataStyle(sheet.getRange(r, 1, 1, 9));
  r += 2;

  // ===========================================================
  // ワイドレイアウト: 左パネル(A-H) + 右パネル(J-P)
  // ===========================================================
  const leftEnd = 8;   // 左パネル最終列(H)
  const rightStart = 10; // 右パネル開始列(J)
  const rightEnd = 16; // 右パネル最終列(P)

  const sectionStartRow = r; // 左右パネルの開始行を揃える

  // ── 左パネル: 主要KPI（当月 vs 目標）
  let lr = sectionStartRow;
  _renderSectionHeader(sheet, lr, leftEnd, "■ 主要KPI（当月 vs 目標）");
  lr++;

  sheet.getRange(lr, 1, 1, 8).setValues([["フェーズ", "当月実績", "当月目標", "達成率", "累計実績", "累計目標", "累計達成率", "ステータス"]]);
  _applyHeaderStyle(sheet.getRange(lr, 1, 1, 8));
  lr++;

  const kpiRows = [];
  const kpiColors = [];
  PHASE_DEFS.filter(d => d.group === "main").forEach(def => {
    const actM = fStats[def.key]?.[currentYM] || 0;
    const tgtM = targetsFun[def.key]?.[currentYM] || 0;
    const rateM = tgtM ? actM / tgtM : null;
    const actT = fStats[def.key]?.TOTAL || 0;
    const tgtT = Object.values(targetsFun[def.key] || {}).reduce((s, n) => s + n, 0);
    const rateT = tgtT ? actT / tgtT : null;

    const status = rateT === null ? "-" : rateT >= 1 ? "達成" : rateT >= 0.7 ? "注意" : "警戒";
    kpiRows.push([
      def.label,
      actM,
      tgtM || "-",
      rateM === null ? "-" : `${Math.round(rateM * 100)}%`,
      actT,
      tgtT || "-",
      rateT === null ? "-" : `${Math.round(rateT * 100)}%`,
      status,
    ]);
    kpiColors.push([
      COLOR.bgRow, COLOR.bgRow, COLOR.bgRow,
      rateToColor(rateM),
      COLOR.bgRow, COLOR.bgRow,
      rateToColor(rateT),
      COLOR.bgRow,
    ]);
  });
  sheet.getRange(lr, 1, kpiRows.length, 8).setValues(kpiRows);
  sheet.getRange(lr, 1, kpiRows.length, 8).setBackgrounds(kpiColors);
  _applyDataStyle(sheet.getRange(lr, 1, kpiRows.length, 8), { keepBg: true });
  lr += kpiRows.length + 1;

  // 左パネル: リードタイム上位
  _renderSectionHeader(sheet, lr, leftEnd, "■ リードタイム（中央値・上位5遷移）");
  lr++;

  sheet.getRange(lr, 1, 1, 4).setValues([["遷移", "サンプル数", "中央値(日)", "P90(日)"]]);
  _applyHeaderStyle(sheet.getRange(lr, 1, 1, 4));
  lr++;

  const lt = aggregateLeadtime(records);
  const ltRows = LEADTIME_TRANSITIONS
    .map(t => ({ t, s: lt[t.key] }))
    .filter(x => x.s.count > 0)
    .sort((a, b) => b.s.count - a.s.count)
    .slice(0, 5)
    .map(x => [x.t.label, x.s.count, x.s.median?.toFixed(1) || "-", x.s.p90?.toFixed(1) || "-"]);
  if (ltRows.length) {
    sheet.getRange(lr, 1, ltRows.length, 4).setValues(ltRows);
    _applyDataStyle(sheet.getRange(lr, 1, ltRows.length, 4));
    lr += ltRows.length;
  } else {
    sheet.getRange(lr, 1).setValue("（データ未蓄積）").setFontColor(COLOR.textDim).setFontFamily(FONT_HEAD);
    lr++;
  }

  // ── 右パネル: アクティブ学生
  let rr = sectionStartRow;
  const rightCols = rightEnd - rightStart + 1; // 7 columns J-P
  _renderSectionHeader(sheet, rr, rightCols, "■ アクティブ学生（選考中）");
  // Note: _renderSectionHeader uses cols 1〜N. Override for right panel:
  sheet.getRange(rr, rightStart, 1, rightCols).merge().setValue("■ アクティブ学生（選考中）")
    .setBackground(COLOR.totalBg).setFontColor(COLOR.textMain)
    .setFontWeight("bold").setFontSize(11).setFontFamily(FONT_HEAD)
    .setHorizontalAlignment("left").setVerticalAlignment("middle")
    .setBorder(true, true, true, true, false, false, COLOR.bgDark, SpreadsheetApp.BorderStyle.SOLID);
  // 左側に書かれた値を消す
  sheet.getRange(rr, 1, 1, leftEnd).clearContent();
  sheet.setRowHeight(rr, 28);
  rr++;

  sheet.getRange(rr, rightStart, 1, 2).setValues([["選考段階", "人数"]]);
  _applyHeaderStyle(sheet.getRange(rr, rightStart, 1, 2));
  rr++;

  const activeRows = [];
  Object.entries(aStats).forEach(([stage, count]) => {
    if (count > 0) activeRows.push([stage, count]);
  });
  const totalActive = activeRows.reduce((s, row) => s + row[1], 0);
  activeRows.push(["合計（選考中）", totalActive]);

  sheet.getRange(rr, rightStart, activeRows.length, 2).setValues(activeRows);
  _applyDataStyle(sheet.getRange(rr, rightStart, activeRows.length, 2));
  _applyTotalRowStyle(sheet.getRange(rr + activeRows.length - 1, rightStart, 1, 2));
  rr += activeRows.length + 1;

  // 右パネル: 離脱・承諾
  sheet.getRange(rr, rightStart, 1, rightCols).merge().setValue("■ 離脱・承諾サマリー")
    .setBackground(COLOR.totalBg).setFontColor(COLOR.textMain)
    .setFontWeight("bold").setFontSize(11).setFontFamily(FONT_HEAD)
    .setHorizontalAlignment("left").setVerticalAlignment("middle")
    .setBorder(true, true, true, true, false, false, COLOR.bgDark, SpreadsheetApp.BorderStyle.SOLID);
  sheet.setRowHeight(rr, 28);
  rr++;

  const atr = aggregateAttrition(records);
  const sR = atr.summary;
  const atrRows = [
    ["総候補者数", sR.total],
    ["選考中", sR.active],
    ["離脱者", `${sR.declined} (${sR.total ? Math.round(sR.declined / sR.total * 100) + "%" : "-"})`],
    ["内定獲得", sR.offered],
    ["内定承諾", `${sR.accepted} (${sR.offered ? Math.round(sR.acceptRate * 100) + "%" : "-"})`],
  ];
  sheet.getRange(rr, rightStart, atrRows.length, 2).setValues(atrRows);
  _applyDataStyle(sheet.getRange(rr, rightStart, atrRows.length, 2));
  rr += atrRows.length + 1;

  // ===========================================================
  // チャート: 主要KPI 当月実績 vs 目標 (columnチャート)
  // ===========================================================
  const chartDataStart = Math.max(lr, rr) + 1;
  // チャート用データを書き出し（隠し用に右端）
  sheet.getRange(chartDataStart, 1, 1, 3).setValues([["フェーズ", "当月実績", "当月目標"]]);
  const chartLabels = ["エントリー", "説明選考会", "1次面接", "1day", "役員面接", "最終面接", "内定承諾"];
  const chartKeys =   ["entry",     "info_joined", "first_joined", "oneday_joined", "second_joined", "final_joined", "accepted"];
  const chartRows = chartKeys.map((k, i) => [
    chartLabels[i],
    fStats[k]?.[currentYM] || 0,
    targetsFun[k]?.[currentYM] || 0,
  ]);
  sheet.getRange(chartDataStart + 1, 1, chartRows.length, 3).setValues(chartRows);
  _applyHeaderStyle(sheet.getRange(chartDataStart, 1, 1, 3));
  _applyDataStyle(sheet.getRange(chartDataStart + 1, 1, chartRows.length, 3));

  // 既存チャートを削除してから再作成
  sheet.getCharts().forEach(c => sheet.removeChart(c));
  const chart = sheet.newChart()
    .setChartType(Charts.ChartType.COLUMN)
    .addRange(sheet.getRange(chartDataStart, 1, chartRows.length + 1, 3))
    .setPosition(chartDataStart, rightStart, 0, 0)
    .setOption("title", `当月実績 vs 目標（${currentYM}）`)
    .setOption("legend", { position: "top" })
    .setOption("colors", ["#1f77b4", "#ff7f0e"])
    .setOption("height", 320)
    .setOption("width", 520)
    .build();
  sheet.insertChart(chart);

  // 列幅
  sheet.setColumnWidth(1, 140);
  for (let c = 2; c <= leftEnd; c++) sheet.setColumnWidth(c, 105);
  sheet.setColumnWidth(rightStart - 1, 16); // 左右パネル間の薄い区切り
  sheet.setColumnWidth(rightStart, 160);
  for (let c = rightStart + 1; c <= rightEnd; c++) sheet.setColumnWidth(c, 110);

  sheet.getRange(1, 1, sheet.getMaxRows(), sheet.getMaxColumns()).setVerticalAlignment("middle");
}

// ─────────────────────────────────────────
// 描画ヘルパー
// ─────────────────────────────────────────

function _applyTitleStyle(range) {
  range.setBackground(COLOR.bgDark)
    .setFontColor(COLOR.fgWhite)
    .setFontWeight("bold").setFontSize(12).setFontFamily(FONT_HEAD)
    .setHorizontalAlignment("left").setVerticalAlignment("middle");
  range.getSheet().setRowHeight(range.getRow(), 36);
  // タイトル行全体に外枠
  range.setBorder(true, true, true, true, false, false, COLOR.bgDark, SpreadsheetApp.BorderStyle.SOLID);
}

function _applyHeaderStyle(range) {
  range.setBackground(COLOR.bgDark)
    .setFontColor(COLOR.fgWhite)
    .setFontWeight("bold").setFontSize(10).setFontFamily(FONT_HEAD)
    .setHorizontalAlignment("center").setVerticalAlignment("middle");
  for (let r = range.getRow(); r < range.getRow() + range.getNumRows(); r++) {
    range.getSheet().setRowHeight(r, 28);
  }
  // ヘッダ全体の外枠
  range.setBorder(true, true, true, true, false, false, COLOR.bgDark, SpreadsheetApp.BorderStyle.SOLID);
}

function _applyDataStyle(range, opts) {
  if (!opts?.keepBg) range.setBackground(COLOR.bgRow);
  range.setFontColor(COLOR.textMain)
    .setFontSize(10).setFontFamily(FONT_MONO)
    .setHorizontalAlignment("center").setVerticalAlignment("middle");
  // 1列目は左寄せ
  const sheet = range.getSheet();
  sheet.getRange(range.getRow(), 1, range.getNumRows(), 1)
    .setHorizontalAlignment("left").setFontFamily(FONT_HEAD);
  for (let r = range.getRow(); r < range.getRow() + range.getNumRows(); r++) {
    sheet.setRowHeight(r, 24);
  }
  // データ範囲の外枠 + セル間の薄い境界線
  range.setBorder(
    true, true, true, true,
    true, true,
    COLOR.bgDark,
    SpreadsheetApp.BorderStyle.SOLID
  );
}

function _applyTotalRowStyle(range) {
  range.setBackground(COLOR.totalBg)
    .setFontColor(COLOR.textMain)
    .setFontWeight("bold").setFontSize(10);
  range.getSheet().setRowHeight(range.getRow(), 26);
  range.setBorder(true, true, true, true, false, false, COLOR.bgDark, SpreadsheetApp.BorderStyle.SOLID);
}

// ─────────────────────────────────────────
// §7  Slack 週次レポート
// ─────────────────────────────────────────

function sendSlackMessage(channel, text, blocks, threadTs) {
  const { token } = getSlackSettings();
  if (!token) { Logger.log("[Slack] Bot Token 未設定"); return null; }

  const payload = { channel, text: text || " " };
  if (blocks && blocks.length > 0) payload.blocks = blocks;
  if (threadTs) payload.thread_ts = threadTs;

  const res = UrlFetchApp.fetch("https://slack.com/api/chat.postMessage", {
    method: "post", contentType: "application/json",
    headers: { Authorization: "Bearer " + token },
    payload: JSON.stringify(payload), muteHttpExceptions: true,
  });
  const result = JSON.parse(res.getContentText());
  if (!result.ok) Logger.log("[Slack Error] " + result.error);
  return result;
}

function composeWeeklyBlocks() {
  const cfg = getConfig();
  const company = String(cfg["企業名"] || "").trim() || "RPO";

  const records = loadRawRecords();
  const targetsFun = loadTargetsFunnel();
  const targetsCh  = loadTargetsChannel();

  const fStats = aggregateFunnelMonthly(records);
  const cStats = aggregateChannelMonthly(records);
  const aStats = aggregateActive(records);

  const now = new Date();
  const ym = monthKey(now);
  const weekStart = _startOfWeek(now);

  const blocks = [];
  blocks.push({
    type: "header",
    text: { type: "plain_text", text: `${company} RPO 週次サマリー  ／  ${formatDate(weekStart)}週` },
  });

  // KPI Section
  const kpiLines = [];
  PHASE_DEFS.filter(d => ["entry", "info_joined", "first_joined", "first_passed", "offer", "accepted"].includes(d.key))
    .forEach(def => {
      const act = fStats[def.key]?.[ym] || 0;
      const tgt = targetsFun[def.key]?.[ym] || 0;
      const rate = tgt ? Math.round(act / tgt * 100) : null;
      const emoji = rate === null ? "▫️" : rate >= 100 ? "🟢" : rate >= 70 ? "🟡" : "🔴";
      kpiLines.push(`${emoji} *${def.label}*: ${act}${tgt ? ` / ${tgt} (${rate}%)` : ""}`);
    });
  blocks.push({
    type: "section",
    text: { type: "mrkdwn", text: `*■ 当月KPI（${ym}）*\n${kpiLines.join("\n")}` },
  });

  // チャネル別Top5
  const chRows = Object.entries(cStats)
    .map(([ch, s]) => ({
      ch,
      act: s[ym] || 0,
      tgt: targetsCh[ch]?.[ym] || 0,
    }))
    .sort((a, b) => b.act - a.act)
    .slice(0, 5);
  const chLines = chRows.map(r => {
    const rate = r.tgt ? Math.round(r.act / r.tgt * 100) : null;
    const emoji = rate === null ? "▫️" : rate >= 100 ? "🟢" : rate >= 70 ? "🟡" : "🔴";
    return `${emoji} ${r.ch}: ${r.act}${r.tgt ? ` / ${r.tgt} (${rate}%)` : ""}`;
  });
  blocks.push({
    type: "section",
    text: { type: "mrkdwn", text: `*■ チャネル別Top5（当月）*\n${chLines.join("\n") || "(データなし)"}` },
  });

  // 注意点（達成率<70%）
  const alerts = [];
  PHASE_DEFS.filter(d => d.group === "main").forEach(def => {
    const act = fStats[def.key]?.[ym] || 0;
    const tgt = targetsFun[def.key]?.[ym] || 0;
    if (!tgt) return;
    const rate = act / tgt;
    if (rate < 0.7) alerts.push(`🔴 ${def.label}: ${act}/${tgt} (${Math.round(rate * 100)}%)`);
  });
  if (alerts.length) {
    blocks.push({
      type: "section",
      text: { type: "mrkdwn", text: `*■ 警戒フェーズ（達成率70%未満）*\n${alerts.join("\n")}` },
    });
  }

  // 離脱・承諾サマリー
  const atr = aggregateAttrition(records);
  const sR = atr.summary;
  const atrLines = [
    `候補者: ${sR.total}名（選考中 ${sR.active} / 離脱 ${sR.declined} / 内定獲得 ${sR.offered} / 承諾 ${sR.accepted}）`,
    sR.total ? `離脱率: ${Math.round(sR.declined / sR.total * 100)}%` : "",
    sR.offered ? `承諾率: ${Math.round(sR.acceptRate * 100)}%` : "",
  ].filter(Boolean);
  blocks.push({
    type: "section",
    text: { type: "mrkdwn", text: `*■ 離脱・承諾*\n${atrLines.join("\n")}` },
  });

  // アクティブ
  const activeLines = Object.entries(aStats)
    .filter(([, n]) => n > 0)
    .map(([s, n]) => `• ${s}: ${n}名`);
  const totalActive = Object.values(aStats).reduce((s, n) => s + n, 0);
  blocks.push({
    type: "section",
    text: { type: "mrkdwn", text: `*■ アクティブ学生（合計 ${totalActive}名）*\n${activeLines.join("\n") || "(なし)"}` },
  });

  // フッター
  const ssUrl = SpreadsheetApp.getActiveSpreadsheet().getUrl();
  blocks.push({ type: "divider" });
  blocks.push({
    type: "context",
    elements: [{ type: "mrkdwn", text: `🔗 <${ssUrl}|詳細はスプレッドシートへ>　|　自動生成: ${formatDatetime(now)}` }],
  });

  return blocks;
}

function sendWeeklyReport() {
  const { channel } = getSlackSettings();
  if (!channel) { Logger.log("[WeeklyReport] チャンネルID未設定"); return; }
  const blocks = composeWeeklyBlocks();
  const text = `RPO 週次サマリー (${formatDate(new Date())})`;
  return sendSlackMessage(channel, text, blocks);
}

function previewWeeklyReport() {
  const blocks = composeWeeklyBlocks();
  Logger.log("=== Weekly Report Preview ===");
  Logger.log(JSON.stringify(blocks, null, 2));
  SpreadsheetApp.getUi().alert("プレビューは「表示 > ログ」(Cmd+Enter) で確認できます。\n問題なければ メニュー > 週次レポート送信 を実行してください。");
}

// ─────────────────────────────────────────
// §8  メニュー & トリガー
// ─────────────────────────────────────────

function onOpen() {
  SpreadsheetApp.getUi().createMenu("RPO")
    .addItem("全体再集計", "rebuildAll")
    .addSeparator()
    .addItem("ダッシュボード再生成", "rebuildDashboardOnly")
    .addItem("詳細分析 再生成", "rebuildDetailedOnly")
    .addItem("バイネーム管理 再生成", "rebuildByNameOnly")
    .addSeparator()
    .addItem("週次レポート プレビュー", "previewWeeklyReport")
    .addItem("週次レポート 送信", "sendWeeklyReport")
    .addSeparator()
    .addItem("旧タブのクリーンアップ", "cleanupLegacyTabs")
    .addItem("トリガー設定", "setAllTriggers")
    .addToUi();
}

function rebuildAll() {
  const start = Date.now();
  try {
    cleanupLegacyTabs();
    const records   = loadRawRecords();
    const targetsFun = loadTargetsFunnel();
    const targetsCh  = loadTargetsChannel();

    renderDetailed(records, targetsFun, targetsCh);
    renderByName(records);
    renderDashboard(records, targetsFun, targetsCh);

    _writeLog("OK", `件数=${records.length} / 経過=${(Date.now() - start) / 1000}s`);
  } catch (e) {
    _writeLog("ERR", String(e) + "\n" + e.stack);
    throw e;
  }
}

function rebuildDashboardOnly() {
  const records = loadRawRecords();
  renderDashboard(records, loadTargetsFunnel(), loadTargetsChannel());
}
function rebuildDetailedOnly() {
  renderDetailed(loadRawRecords(), loadTargetsFunnel(), loadTargetsChannel());
}
function rebuildByNameOnly() {
  renderByName(loadRawRecords());
}

function setAllTriggers() {
  const cfg = getConfig();
  ScriptApp.getProjectTriggers().forEach(t => {
    const name = t.getHandlerFunction();
    if (["rebuildAll", "sendWeeklyReport"].includes(name)) ScriptApp.deleteTrigger(t);
  });

  const dailyHour = parseInt(cfg["再集計トリガー時刻"] || "9", 10);
  ScriptApp.newTrigger("rebuildAll").timeBased().atHour(dailyHour).everyDays(1).create();

  const wday = String(cfg["週次レポート曜日"] || "月曜").trim();
  const weekHour = parseInt(cfg["週次レポート時刻"] || "9", 10);
  const wdMap = {
    "月曜": ScriptApp.WeekDay.MONDAY,
    "火曜": ScriptApp.WeekDay.TUESDAY,
    "水曜": ScriptApp.WeekDay.WEDNESDAY,
    "木曜": ScriptApp.WeekDay.THURSDAY,
    "金曜": ScriptApp.WeekDay.FRIDAY,
    "土曜": ScriptApp.WeekDay.SATURDAY,
    "日曜": ScriptApp.WeekDay.SUNDAY,
  };
  ScriptApp.newTrigger("sendWeeklyReport").timeBased()
    .onWeekDay(wdMap[wday] || ScriptApp.WeekDay.MONDAY)
    .atHour(weekHour).create();

  SpreadsheetApp.getUi().alert(`トリガー設定完了:\n- 毎日 ${dailyHour}時 → 全体再集計\n- 毎週${wday} ${weekHour}時 → 週次レポート送信`);
}

// ─────────────────────────────────────────
// §9  ユーティリティ
// ─────────────────────────────────────────

function parseDate(v) {
  if (!v && v !== 0) return null;
  if (v instanceof Date && !isNaN(v.getTime())) return v;
  const s = String(v).trim();
  if (!s) return null;
  const norm = s.replace(/\//g, "-").replace(/\./g, "-");
  // YYYY-M-D
  const m = norm.match(/^(\d{4})-(\d{1,2})-(\d{1,2})/);
  if (m) {
    const d = new Date(parseInt(m[1], 10), parseInt(m[2], 10) - 1, parseInt(m[3], 10));
    return isNaN(d.getTime()) ? null : d;
  }
  const d = new Date(s);
  return isNaN(d.getTime()) ? null : d;
}

function monthKey(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

function _startOfWeek(d) {
  const c = new Date(d);
  const day = c.getDay();
  const diff = (day === 0 ? -6 : 1 - day); // 月曜始まり
  c.setDate(c.getDate() + diff);
  c.setHours(0, 0, 0, 0);
  return c;
}

function formatDate(d) {
  if (!(d instanceof Date) || isNaN(d.getTime())) return "";
  return `${d.getFullYear()}/${String(d.getMonth() + 1).padStart(2, "0")}/${String(d.getDate()).padStart(2, "0")}`;
}

function formatTime(d) {
  if (!(d instanceof Date) || isNaN(d.getTime())) return "";
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

function formatDatetime(d) {
  return `${formatDate(d)} ${formatTime(d)}`;
}

function _writeLog(status, msg) {
  const { log } = getOutputSheetNames();
  const sheet = _getOrCreateSheet(log);
  sheet.setHiddenGridlines(true);
  if (sheet.getLastRow() === 0) {
    sheet.getRange(1, 1, 1, 3).setValues([["日時", "結果", "詳細"]]);
    _applyHeaderStyle(sheet.getRange(1, 1, 1, 3));
    sheet.setColumnWidth(1, 160);
    sheet.setColumnWidth(2, 80);
    sheet.setColumnWidth(3, 600);
    sheet.setFrozenRows(1);
  }
  sheet.appendRow([formatDatetime(new Date()), status, msg]);
}
