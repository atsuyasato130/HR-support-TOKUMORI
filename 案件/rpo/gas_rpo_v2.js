// ============================================================
// RPO 採用ダッシュボード GAS v2.0
// SpreadsheetID: 1Jst9O1xcgDOgpRylhUIslnbLzgPZMk9zKy9W0NFyFtM
//
// 主な変更点 (v1.x → v2.0):
//   - データソースを「学生情報一覧raw」に変更（かんりくんCSV）
//   - 選考フェーズを学生情報一覧raw のヘッダから自動検出（動的）
//   - タブ構成: 110/120/130/200/210/220/230/240/299
//   - 大学・チャネルも動的に増減対応
//   - シートからコンサル示唆を撤去し、Slack/Docsレポートに集約
//   - ルールベース示唆生成
//   - 日次スナップショット + 月次 Docs レポート 新規追加
//   - 行/列固定を全廃止
// ============================================================

// ─────────────────────────────────────────
// §1  定数・テーマ
// ─────────────────────────────────────────

const CONFIG_SHEET = "200_設定";

const COLOR = {
  bgDark:    "#37474F",
  bgPanel:   "#546E7A",
  bgRow:     "#FFFFFF",
  bgRowAlt:  "#F5F5F5",
  totalBg:   "#ECEFF1",
  bgInsight: "#FCF5D9",
  fgWhite:   "#FFFFFF",
  textMain:  "#212121",
  textDim:   "#757575",
  ok:        "#C8E6C9", // 達成 / 緑
  warn:      "#FFF59D", // 注意 / 黄
  alert:     "#FFCDD2", // 警戒 / 赤
  okBorder:  "#22C55E",
  warnBorder:"#EAB308",
  alertBorder:"#EF4444",
  borderGray:"#D9D9D9",
};

const FONT = "Arial";

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

function getInputSheetNames() {
  const cfg = getConfig();
  return {
    raw:       cfg["ATSローデータタブ名"]      || "学生情報一覧raw",
    targetFun: cfg["目標タブ名（ファネル）"]   || "120_採用目標",
    targetCh:  cfg["目標タブ名（チャネル）"]   || "130_エントリー目標管理",
  };
}

function getOutputSheetNames() {
  const cfg = getConfig();
  return {
    overview:   cfg["全体サマリータブ"]         || "210_全体サマリー",
    bySchool:   cfg["大学別タブ"]               || "220_大学別歩留まり実績",
    byChannel:  cfg["エントリー経路別タブ"]     || "230_エントリー経路別実績",
    byName:     cfg["バイネーム進捗タブ"]       || "240_バイネーム進捗管理シート",
    log:        cfg["ログタブ"]                 || "299_ログ",
  };
}

function getSlackSettings() {
  const cfg = getConfig();
  return {
    token:           String(cfg["Slack Bot Token"] || "").trim(),
    weeklyChannel:   String(cfg["Slack 週次レポートチャンネルID"] || "").trim(),
    dailyChannel:    String(cfg["Slack 日次レポートチャンネルID"] || cfg["Slack 週次レポートチャンネルID"] || "").trim(),
    monthlyChannel:  String(cfg["Slack 月次レポートチャンネルID"] || cfg["Slack 週次レポートチャンネルID"] || "").trim(),
    weeklyEnabled:   _toBool(cfg["週次レポート有効"], true),
    dailyEnabled:    _toBool(cfg["日次レポート有効"], false),
    monthlyEnabled:  _toBool(cfg["月次レポート有効"], false),
    weeklyWday:      String(cfg["週次レポート曜日"] || "月曜").trim(),
    weeklyHour:      parseInt(cfg["週次レポート時刻"] || "9", 10),
    dailyHour:       parseInt(cfg["日次レポート時刻"] || "9", 10),
  };
}

function getDocsSettings() {
  const cfg = getConfig();
  return {
    templateId: String(cfg["月次レポートテンプレDocsID"] || "").trim(),
    folderId:   String(cfg["月次レポート保存先フォルダID"] || "").trim(),
  };
}

function _toBool(v, def) {
  const s = String(v || "").trim().toUpperCase();
  if (s === "TRUE" || s === "ON" || s === "1") return true;
  if (s === "FALSE" || s === "OFF" || s === "0") return false;
  return def;
}

// ─────────────────────────────────────────
// §3  ローデータ読込 + 動的フェーズ検出
// ─────────────────────────────────────────

// 学生情報一覧raw の列ヘッダから「○○・到達日」列を全て検出して PHASE_DEFS を構築
function detectPhaseDefs() {
  const { raw } = getInputSheetNames();
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(raw);
  if (!sheet) throw new Error(`ローデータタブ「${raw}」が見つかりません`);

  // ヘッダ行は2行目（1行目は職種ラベル）
  const headerRow = sheet.getRange(2, 1, 1, sheet.getLastColumn()).getValues()[0];
  const defs = [];
  headerRow.forEach((h, i) => {
    const header = String(h || "").trim();
    if (!header.endsWith("・到達日")) return;
    let label = header.replace("・到達日", "");
    // 表記揺れ正規化: 全角数字を半角に統一（例: "２daysインターン" → "2daysインターン"）
    label = label.replace(/[０-９]/g, c => String.fromCharCode(c.charCodeAt(0) - 0xFEE0));
    // フェーズキーは英数字化（社内呼称はそのままlabelに保持）
    const key = `p_${defs.length}`;
    defs.push({
      key,
      arrival: header,
      label,
      colIdx: i,
      // グルーピング判定
      //  exit      : 【不合格】【不参加】【辞退】 / 内定辞退 = 離脱集計のみ、ファネル順序からは除外
      //  interview : 〇〇後面談 = main 集計から除外
      //  pass      : 【合格】/ 内定 / 内定承諾
      //  reserved  : 【予約】= 予約消化率を見るため月次ファネルには表示
      //  main      : エントリー / 〇〇【参加】等 = ファネル主軸
      group: /[【]不合格[】]|[【]不参加[】]|[【]辞退[】]|^内定辞退$/.test(label) ? "exit" :
             /後面談/.test(label) ? "interview" :
             /[【]合格[】]|内定承諾|^内定$/.test(label) ? "pass" :
             /[【]予約[】]/.test(label) ? "reserved" : "main",
    });
  });
  return defs;
}

// rawレコード読込: 動的に検出したPHASE_DEFSを使って到達日を収集
function loadRawRecords() {
  const { raw } = getInputSheetNames();
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(raw);
  if (!sheet) throw new Error(`ローデータタブ「${raw}」が見つかりません`);
  const data = sheet.getDataRange().getValues();
  if (data.length < 3) return { phases: [], records: [] };

  const headerRow = data[1];
  const colIdx = {};
  headerRow.forEach((h, i) => {
    const key = String(h || "").trim();
    if (!key) return;
    if (!(key in colIdx)) colIdx[key] = i;
  });

  const phases = detectPhaseDefs();

  // 総合評価列のインデックス配列（フェーズ後に登場する評価列）
  const evalIndices = [];
  headerRow.forEach((h, i) => {
    if (String(h).trim() === "総合評価") evalIndices.push(i);
  });

  const records = [];
  for (let r = 2; r < data.length; r++) {
    const row = data[r];
    const id = String(row[colIdx["ID"]] || "").trim();
    if (!id) continue;
    const rec = {
      id,
      lastName:     String(row[colIdx["姓"]] || "").trim(),
      firstName:    String(row[colIdx["名"]] || "").trim(),
      lastKana:     String(row[colIdx["セイ"]] || "").trim(),
      firstKana:    String(row[colIdx["メイ"]] || "").trim(),
      school:       String(row[colIdx["学校名"]] || "").trim() || "（未記入）",
      currentStage: String(row[colIdx["現在の選考段階"]] || "").trim(),
      status:       String(row[colIdx["選考状況"]] || "").trim(),
      channel:      _normalizeChannel(String(row[colIdx["エントリー経路"]] || "").trim()),
      channels:     String(row[colIdx["エントリー経路"]] || "").split(/[,、|｜\/]/).map(s => s.trim()).filter(Boolean),
      arrivals:     {},  // 〇〇・到達日 の値（フェーズに到達した日）
      scheduled:    {},  // 〇〇 列の素の値（予約フェーズなら予約された実施予定日）
      evals:        {},
    };
    phases.forEach(p => {
      rec.arrivals[p.key] = parseDate(row[p.colIdx]);
      // 〇〇・到達日 の1つ左の列が 〇〇（素の予約日が入る列）
      const mainColIdx = p.colIdx - 1;
      if (mainColIdx >= 0) rec.scheduled[p.key] = parseDate(row[mainColIdx]);
    });
    // 評価ランクをフェーズに紐付け（評価列の直前のフェーズに対応）
    evalIndices.forEach(idx => {
      const v = String(row[idx] || "").trim().toUpperCase();
      if (!RANKS.includes(v)) return;
      // 評価列の左にある一番近いフェーズキーを探す
      const owner = phases.slice().reverse().find(p => p.colIdx < idx);
      if (owner) rec.evals[owner.key] = v;
    });
    records.push(rec);
  }
  return { phases, records };
}

function _normalizeChannel(raw) {
  if (!raw) return "";
  return raw.split(/[,、|｜]/)[0].trim();
}

// ─────────────────────────────────────────
// §4  集計エンジン
// ─────────────────────────────────────────

function aggregateFunnelMonthly(records, phases) {
  const result = {};
  phases.forEach(p => { result[p.key] = { TOTAL: 0 }; });
  records.forEach(rec => {
    phases.forEach(p => {
      const dt = rec.arrivals[p.key];
      if (!dt) return;
      const mk = monthKey(dt);
      result[p.key][mk] = (result[p.key][mk] || 0) + 1;
      result[p.key].TOTAL += 1;
    });
  });
  return result;
}

// 月次ファネル（コホート版）: その月にエントリーした人が、各フェーズに到達した数を集計
// → 行内で単調減少する正しいファネル形になる
function aggregateFunnelByEntryMonth(records, phases) {
  const result = {};
  const entryKey = phases[0]?.key;
  if (!entryKey) return result;
  records.forEach(rec => {
    const entryDt = rec.arrivals[entryKey];
    if (!entryDt) return;
    const mk = monthKey(entryDt);
    if (!result[mk]) {
      result[mk] = { TOTAL: 0 };
      phases.forEach(p => { result[mk][p.key] = 0; });
    }
    phases.forEach(p => {
      if (rec.arrivals[p.key]) result[mk][p.key]++;
    });
    result[mk].TOTAL++;
  });
  // 全体合計
  const overall = { TOTAL: 0 };
  phases.forEach(p => { overall[p.key] = 0; });
  Object.values(result).forEach(m => {
    phases.forEach(p => { overall[p.key] += m[p.key] || 0; });
    overall.TOTAL += m.TOTAL || 0;
  });
  result.TOTAL = overall;
  return result;
}

function aggregateChannelMonthly(records) {
  const result = {};
  records.forEach(rec => {
    // エントリー扱いの最初フェーズの到達日を基準（簡易: 最初に到達した日付）
    const firstDt = _firstArrival(rec);
    if (!firstDt) return;
    const ch = rec.channel || "(未分類)";
    if (!result[ch]) result[ch] = { TOTAL: 0 };
    const mk = monthKey(firstDt);
    result[ch][mk] = (result[ch][mk] || 0) + 1;
    result[ch].TOTAL += 1;
  });
  return result;
}

function _firstArrival(rec) {
  let min = null;
  Object.values(rec.arrivals).forEach(d => {
    if (d && (!min || d < min)) min = d;
  });
  return min;
}

// アクティブ判定: 「選考中」かつ「不参加/不合格/辞退」ステージでない
// かんりくん側で 不参加/辞退 ステージになっても「選考状況」が「選考中」のまま残ることがあるため、
// currentStage の文字列もチェックする
function _isActiveRecord(rec) {
  if (rec.status !== "選考中") return false;
  const stage = String(rec.currentStage || "");
  if (/[【]不合格[】]|[【]不参加[】]|[【]辞退[】]/.test(stage)) return false;
  if (stage === "内定辞退") return false;
  return true;
}

function aggregateActive(records) {
  const result = {};
  records.forEach(rec => {
    if (!_isActiveRecord(rec)) return;
    const st = rec.currentStage || "(不明)";
    result[st] = (result[st] || 0) + 1;
  });
  return result;
}

function aggregateAttrition(records, phases) {
  const reached = {};
  const declinedAt = {};
  const failedAt = {};            // 【不合格】到達日ベース：フェーズキー → 件数
  const noShowAt = {};            // 【不参加】到達日ベース：フェーズキー → 件数
  const declinedAtVoluntary = {}; // 【辞退】/ 内定辞退 到達日ベース：フェーズキー → 件数
  phases.forEach(p => {
    reached[p.key] = 0;
    declinedAt[p.key] = 0;
    failedAt[p.key] = 0;
    noShowAt[p.key] = 0;
    declinedAtVoluntary[p.key] = 0;
  });

  let totalActive = 0, totalDeclined = 0, totalAccepted = 0, totalOffered = 0;
  let totalFailed = 0, totalNoShow = 0, totalVoluntary = 0;
  const acceptedKey = phases.find(p => p.label === "内定承諾")?.key;
  const offerKey    = phases.find(p => p.label === "内定")?.key;

  // 「〇〇【不合格】/【不参加】/【辞退】/ 内定辞退」のexitフェーズ集合
  const exitPhases = phases.filter(p => p.group === "exit");

  records.forEach(rec => {
    let lastReached = null;
    phases.forEach(p => {
      if (rec.arrivals[p.key]) {
        // exit フェーズは「到達した」とは扱わない（離脱なので）
        if (p.group !== "exit") {
          reached[p.key]++;
          lastReached = p.key;
        }
      }
    });

    // exit フェーズに到達日があれば、種別ごとに記録
    let recExited = false;
    exitPhases.forEach(p => {
      if (!rec.arrivals[p.key]) return;
      recExited = true;
      if (/[【]不合格[】]/.test(p.label)) {
        failedAt[p.key]++;
        totalFailed++;
      } else if (/[【]不参加[】]/.test(p.label)) {
        noShowAt[p.key]++;
        totalNoShow++;
      } else if (/[【]辞退[】]|^内定辞退$/.test(p.label)) {
        declinedAtVoluntary[p.key]++;
        totalVoluntary++;
      }
    });

    const isActive = _isActiveRecord(rec);
    if (isActive) {
      totalActive++;
    } else if (acceptedKey && rec.arrivals[acceptedKey]) {
      totalAccepted++;
    } else {
      totalDeclined++;
      // exit 列に何も入っていない場合は「最終到達フェーズで離脱」として既存ロジック互換で集計
      if (!recExited && lastReached) declinedAt[lastReached]++;
    }
    if (offerKey && rec.arrivals[offerKey]) totalOffered++;
  });

  // 既存の declinedAt は後方互換のため、3種類の合計と「未分類離脱」の合算にする
  phases.forEach(p => {
    declinedAt[p.key] = declinedAt[p.key] + failedAt[p.key] + noShowAt[p.key] + declinedAtVoluntary[p.key];
  });

  const rates = {};
  phases.forEach(p => {
    rates[p.key] = reached[p.key] ? declinedAt[p.key] / reached[p.key] : null;
  });

  return {
    reached, declinedAt, rates,
    failedAt, noShowAt, declinedAtVoluntary,
    summary: {
      total: records.length,
      active: totalActive,
      declined: totalDeclined,
      accepted: totalAccepted,
      offered: totalOffered,
      failed: totalFailed,
      noShow: totalNoShow,
      voluntary: totalVoluntary,
      acceptRate: totalOffered ? totalAccepted / totalOffered : null,
    },
  };
}

// リードタイム: 連続するメインフェーズ間の日数
function aggregateLeadtime(records, phases) {
  const mainPhases = phases.filter(p => p.group === "main");
  const result = {};
  for (let i = 0; i < mainPhases.length - 1; i++) {
    const from = mainPhases[i], to = mainPhases[i + 1];
    const key = `${from.key}__${to.key}`;
    result[key] = {
      label: `${from.label} → ${to.label}`,
      samples: [],
    };
    records.forEach(rec => {
      const a = rec.arrivals[from.key], b = rec.arrivals[to.key];
      if (!a || !b) return;
      const d = (b - a) / (24 * 60 * 60 * 1000);
      if (d < 0 || d > 365) return;
      result[key].samples.push(d);
    });
  }
  Object.values(result).forEach(r => {
    const arr = r.samples.slice().sort((a, b) => a - b);
    r.count = arr.length;
    r.avg = arr.length ? arr.reduce((s, n) => s + n, 0) / arr.length : null;
    r.median = arr.length ? arr[Math.floor(arr.length / 2)] : null;
    r.p90 = arr.length ? arr[Math.floor(arr.length * 0.9)] : null;
    r.min = arr.length ? arr[0] : null;
    r.max = arr.length ? arr[arr.length - 1] : null;
  });
  return result;
}

function aggregateRanking(records, phases) {
  const targetPhases = phases.filter(p => p.group === "main");
  const result = {};
  targetPhases.forEach(p => {
    result[p.key] = { S: 0, A: 0, B: 0, C: 0, D: 0, TOTAL: 0, label: p.label };
  });
  records.forEach(rec => {
    Object.entries(rec.evals).forEach(([phaseKey, rank]) => {
      if (!result[phaseKey]) return;
      result[phaseKey][rank] = (result[phaseKey][rank] || 0) + 1;
      result[phaseKey].TOTAL += 1;
    });
  });
  return result;
}

// 累積歩留まり（monotonic）: そのフェーズ以降のいずれかに到達した人数
function aggregateYield(records, phases) {
  // 累積歩留まりは「前進したかどうか」を見るので exit/interview は除外
  const fp = phases.filter(p => p.group === "main" || p.group === "pass" || p.group === "reserved");
  const totalEntry = fp[0] ? records.filter(r => r.arrivals[fp[0].key]).length : 0;
  const result = {};
  fp.forEach((p, idx) => {
    const futurePhases = fp.slice(idx);
    const cumActual = records.filter(rec =>
      futurePhases.some(q => rec.arrivals[q.key])
    ).length;
    result[p.key] = {
      cumActual,
      cumRate: totalEntry ? cumActual / totalEntry : null,
    };
  });
  return result;
}

// 大学別 × フェーズ累計
function aggregateBySchool(records, phases) {
  const result = {};
  records.forEach(rec => {
    const sch = rec.school || "（未記入）";
    if (!result[sch]) {
      result[sch] = { entry: 0, byPhase: {} };
      phases.forEach(p => { result[sch].byPhase[p.key] = 0; });
    }
    phases.forEach(p => {
      if (rec.arrivals[p.key]) result[sch].byPhase[p.key]++;
    });
    // 最初フェーズへの到達がエントリー扱い
    if (phases[0] && rec.arrivals[phases[0].key]) result[sch].entry++;
  });
  return result;
}

// 媒体（エントリー経路）別 × フェーズ累計（aggregateBySchool と同型）
function aggregateByChannel(records, phases) {
  const result = {};
  records.forEach(rec => {
    const ch = rec.channel || "(未分類)";
    if (!result[ch]) {
      result[ch] = { entry: 0, byPhase: {} };
      phases.forEach(p => { result[ch].byPhase[p.key] = 0; });
    }
    phases.forEach(p => {
      if (rec.arrivals[p.key]) result[ch].byPhase[p.key]++;
    });
    if (phases[0] && rec.arrivals[phases[0].key]) result[ch].entry++;
  });
  return result;
}

// 大学 × 月別 × エントリー数
function aggregateBySchoolMonthly(records, phases) {
  const result = {};
  records.forEach(rec => {
    const sch = rec.school || "（未記入）";
    if (!result[sch]) result[sch] = {};
    phases.forEach(p => {
      const dt = rec.arrivals[p.key];
      if (!dt) return;
      const mk = monthKey(dt);
      if (!result[sch][p.key]) result[sch][p.key] = {};
      result[sch][p.key][mk] = (result[sch][p.key][mk] || 0) + 1;
    });
  });
  return result;
}

// 大学 × チャネル クロス
function aggregateSchoolByChannel(records) {
  const result = {};
  const channels = new Set();
  records.forEach(rec => {
    const sch = rec.school || "（未記入）";
    const ch = rec.channel || "(未分類)";
    channels.add(ch);
    if (!result[sch]) result[sch] = {};
    result[sch][ch] = (result[sch][ch] || 0) + 1;
  });
  return { result, channels: [...channels].sort() };
}

// 採用着地予想（簡易: アクティブ × 各フェーズ累積目標通過率）
function aggregateLanding(records, phases, targetsFun) {
  const aStats = aggregateActive(records);
  // 採用着地予想はメインファネル（main + pass）順序で計算
  // exit/interview/reserved は除外（exit は離脱・interview は補助・reserved は予約待ちのため通過率の対象外）
  const fp = phases.filter(p => p.group === "main" || p.group === "pass");
  // 累計目標を計算
  const cumTargets = {};
  fp.forEach(p => {
    cumTargets[p.key] = Object.values(targetsFun[p.key] || {}).reduce((s, n) => s + n, 0);
  });
  const passRates = {};
  fp.forEach((p, i) => {
    const next = fp[i + 1];
    if (!next) { passRates[p.key] = null; return; }
    const a = cumTargets[p.key], b = cumTargets[next.key];
    passRates[p.key] = a ? b / a : null;
  });
  // 「現在の選考段階」→ メインファネル fp 上のフェーズへマッピング
  const stageToPhase = {};
  Object.keys(aStats).forEach(stage => {
    const p = fp.find(p => stage.includes(p.label.replace(/【.+?】/, "")));
    if (p) stageToPhase[stage] = p.key;
  });
  const currentAt = {};
  fp.forEach(p => { currentAt[p.key] = 0; });
  Object.entries(aStats).forEach(([stage, n]) => {
    const k = stageToPhase[stage];
    if (k) currentAt[k] = (currentAt[k] || 0) + n;
  });

  const acceptedIdx = fp.findIndex(p => p.label === "内定承諾");
  const acceptedKey = fp[acceptedIdx]?.key;

  const rows = [];
  let totalExpected = 0;
  fp.forEach((p, i) => {
    if (i >= acceptedIdx) return;
    let cumProb = 1;
    for (let j = i; j < acceptedIdx; j++) {
      const r = passRates[fp[j].key];
      if (r === null) { cumProb = null; break; }
      cumProb *= r;
    }
    const expected = (cumProb === null || !currentAt[p.key]) ? null : currentAt[p.key] * cumProb;
    if (expected !== null) totalExpected += expected;
    if (currentAt[p.key] > 0) {
      rows.push({
        label: p.label,
        active: currentAt[p.key],
        passRate: cumProb,
        expected,
      });
    }
  });
  const alreadyAccepted = acceptedKey ? (aggregateFunnelMonthly(records, phases)[acceptedKey]?.TOTAL || 0) : 0;
  return { rows, totalExpected, alreadyAccepted, grandTotal: totalExpected + alreadyAccepted };
}

// ─────────────────────────────────────────
// §5  目標読込
// ─────────────────────────────────────────

// 200_設定 の「■ フェーズ目標マッピング」セクションを読み込み
// 戻り値: { rawPhaseLabel: target120RowLabel } の逆引きマップ
// 「+」で複数列がある場合は分割して全て同じ120行ラベルへマップ
function loadPhaseMapping() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(CONFIG_SHEET);
  if (!sheet) return {};
  const data = sheet.getDataRange().getValues();
  const map = {};
  let inSection = false;
  for (let i = 0; i < data.length; i++) {
    const a = String(data[i][0] || "").trim();
    const b = String(data[i][1] || "").trim();
    if (a.indexOf("フェーズ目標マッピング") >= 0) { inSection = true; continue; }
    if (!inSection) continue;
    if (a.startsWith("■")) break;
    if (!a || !b || a === "120の行名") continue;
    // b 例: "一次後面談（人事）+一次後面談（現場）" → 分割
    b.split(/[+＋]/).map(s => s.trim()).filter(Boolean).forEach(rawLabel => {
      map[rawLabel] = a; // rawフェーズ → 120行名
    });
  }
  return map;
}

// 120_採用目標から月別ファネル目標を読み込み（マッピング表経由）
// 行: 120行ラベル / 列: 月別
// 200_設定 のマッピング表で raw フェーズ → 120行 を解決
function loadTargetsFunnel(phases) {
  const { targetFun } = getInputSheetNames();
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(targetFun);
  if (!sheet) return {};
  const data = sheet.getDataRange().getValues();
  const mapping = loadPhaseMapping(); // rawPhaseLabel → 120rowLabel

  // 月ヘッダ行を探す: 4月, 5月... を含む行
  let monthRow = -1;
  let monthMap = {}; // colIdx -> "YYYY-MM"
  const cfg = getConfig();
  const startMonth = parseInt(cfg["対象年度開始月"] || "4", 10);
  const baseYear = new Date().getFullYear();

  for (let i = 0; i < data.length; i++) {
    const labels = data[i].map(c => String(c || "").trim());
    if (labels.filter(l => /^\d{1,2}月$/.test(l)).length >= 6) {
      monthRow = i;
      let firstAprSeen = false;
      labels.forEach((l, c) => {
        const m = l.match(/^(\d{1,2})月$/);
        if (m) {
          const mm = parseInt(m[1], 10);
          // 4月は2回出る（早期=baseYear/4 と 本選翌年=baseYear+1/4）
          // 最初の4月以降の早期月 → baseYear、本選合計より後の4月以降 → baseYear+1
          let yr;
          if (mm === 4 && firstAprSeen) yr = baseYear + 1;
          else if (mm >= startMonth) { yr = baseYear; if (mm === 4) firstAprSeen = true; }
          else yr = baseYear + 1;
          monthMap[c] = `${yr}-${String(mm).padStart(2, "0")}`;
        }
      });
      break;
    }
  }
  if (monthRow < 0) return {};

  // 120行ラベル → 月別目標値 をまず構築
  const targetByRow = {}; // "エントリー数" → { "2026-04": 36, ... }
  for (let i = monthRow + 1; i < data.length; i++) {
    const rowLabel = String(data[i][0] || "").trim();
    if (!rowLabel || rowLabel.startsWith("↓") || rowLabel.startsWith("■")) continue;
    if (!targetByRow[rowLabel]) targetByRow[rowLabel] = {};
    Object.entries(monthMap).forEach(([c, ym]) => {
      const n = _parseNum(data[i][parseInt(c, 10)]);
      if (n !== null) targetByRow[rowLabel][ym] = n;
    });
  }

  // 各 phase に対し、マッピングで対応する120行の目標を割り当てる
  const result = {};
  phases.forEach(p => {
    result[p.key] = {};
    const rowLabel = mapping[p.label];
    if (!rowLabel) return;
    const monthly = targetByRow[rowLabel];
    if (!monthly) return;
    result[p.key] = Object.assign({}, monthly);
  });
  return result;
}

// 130_エントリー目標管理からチャネル別月別目標を読み込み
function loadTargetsChannel() {
  const { targetCh } = getInputSheetNames();
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(targetCh);
  if (!sheet) return {};
  const data = sheet.getDataRange().getValues();

  const cfg = getConfig();
  const startMonth = parseInt(cfg["対象年度開始月"] || "4", 10);
  const baseYear = new Date().getFullYear();

  // 月_目標 列を探す（例: "4月_目標"）
  let monthHeaderRow = -1;
  let monthColMap = {}; // colIdx -> "YYYY-MM"
  for (let i = 0; i < data.length; i++) {
    let found = 0;
    data[i].forEach((c, ci) => {
      const s = String(c || "").trim();
      const m = s.match(/^(\d{1,2})月_目標$/);
      if (m) {
        const mm = parseInt(m[1], 10);
        const yr = mm >= startMonth ? baseYear : baseYear + 1;
        monthColMap[ci] = `${yr}-${String(mm).padStart(2, "0")}`;
        found++;
      }
    });
    if (found >= 3) { monthHeaderRow = i; break; }
    monthColMap = {};
  }
  if (monthHeaderRow < 0) return {};

  // チャネル名列を見つける（B列想定）
  const result = {};
  for (let i = monthHeaderRow + 1; i < data.length; i++) {
    const ch = String(data[i][1] || "").trim();
    if (!ch || ch === "—" || ch === "合計" || ch === "—") continue;
    if (!result[ch]) result[ch] = {};
    Object.entries(monthColMap).forEach(([c, ym]) => {
      const n = _parseNum(data[i][parseInt(c, 10)]);
      if (n !== null) result[ch][ym] = n;
    });
  }
  return result;
}

function _parseNum(v) {
  if (v === null || v === undefined || v === "" || v === "—" || v === "-") return null;
  const s = String(v).replace(/[名回%+,]/g, "").trim();
  if (!s) return null;
  const n = Number(s);
  return isNaN(n) ? null : Math.round(n);
}

function rateToColor(rate) {
  if (rate === null || isNaN(rate)) return COLOR.bgRow;
  if (rate >= 1.0) return COLOR.ok;
  if (rate >= 0.7) return COLOR.warn;
  return COLOR.alert;
}

function buildMonthList() {
  const cfg = getConfig();
  const startMonth = parseInt(cfg["対象年度開始月"] || "4", 10);
  const baseYear = new Date().getFullYear();
  const result = [];
  for (let i = 0; i < 13; i++) {
    const mIdx = (startMonth - 1 + i) % 12;
    const month = mIdx + 1;
    const year = (startMonth - 1 + i) < 12 ? baseYear : baseYear + 1;
    result.push({
      ym: `${year}-${String(month).padStart(2, "0")}`,
      label: `${month}月`,
      year, month,
    });
  }
  return result;
}

// ─────────────────────────────────────────
// §6  描画エンジン
// ─────────────────────────────────────────

function _getOrCreateSheet(name) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(name);
  if (!sheet) sheet = ss.insertSheet(name);
  return sheet;
}

function _clearSheet(sheet) {
  // 既存のマージ・固定・罫線・書式を全てリセット
  const all = sheet.getRange(1, 1, sheet.getMaxRows(), sheet.getMaxColumns());
  all.breakApart();
  sheet.setFrozenRows(0);
  sheet.setFrozenColumns(0);
  sheet.clearContents();
  sheet.clearFormats();
  // clearFormats() は数値書式（％・小数）を残すことがあるため明示的に既定へ戻す
  all.setNumberFormat("General");
  sheet.setHiddenGridlines(true);
}

// バナータイトル行
function _bannerTitle(sheet, row, cols, title, subtitle) {
  const text = subtitle ? `${title}　／　${subtitle}` : title;
  sheet.getRange(row, 1, 1, cols).merge().setValue(text)
    .setBackground(COLOR.bgDark).setFontColor(COLOR.fgWhite)
    .setFontWeight("bold").setFontSize(13).setFontFamily(FONT)
    .setHorizontalAlignment("left").setVerticalAlignment("middle")
    .setBorder(true, true, true, true, false, false, COLOR.bgDark, SpreadsheetApp.BorderStyle.SOLID);
  sheet.setRowHeight(row, 40);
}

// セクション見出し
function _sectionHeader(sheet, row, cols, text, opts) {
  const bg = opts?.insight ? COLOR.bgInsight : COLOR.totalBg;
  sheet.getRange(row, 1, 1, cols).merge().setValue(text)
    .setBackground(bg).setFontColor(COLOR.textMain)
    .setFontWeight("bold").setFontSize(11).setFontFamily(FONT)
    .setHorizontalAlignment("left").setVerticalAlignment("middle")
    .setBorder(true, true, true, true, false, false, COLOR.bgDark, SpreadsheetApp.BorderStyle.SOLID);
  sheet.setRowHeight(row, 28);
}

// テーブルヘッダ行
function _tableHeader(sheet, row, startCol, cols) {
  const range = sheet.getRange(row, startCol, 1, cols);
  range.setBackground(COLOR.bgDark).setFontColor(COLOR.fgWhite)
    .setFontWeight("bold").setFontSize(10).setFontFamily(FONT)
    .setHorizontalAlignment("center").setVerticalAlignment("middle")
    .setWrapStrategy(SpreadsheetApp.WrapStrategy.WRAP);
  sheet.setRowHeight(row, 32);
}

// データセル: 外枠 + 内部薄罫線 + 白背景
function _tableData(sheet, row, startCol, rows, cols, opts) {
  const range = sheet.getRange(row, startCol, rows, cols);
  if (!opts?.keepBg) range.setBackground(COLOR.bgRow);
  range.setFontColor(COLOR.textMain).setFontSize(10).setFontFamily(FONT)
    .setHorizontalAlignment("center").setVerticalAlignment("middle");
  // 先頭列は左寄せ
  sheet.getRange(row, startCol, rows, 1)
    .setHorizontalAlignment("left").setFontWeight("bold");
  range.setBorder(true, true, true, true, true, true, COLOR.borderGray, SpreadsheetApp.BorderStyle.SOLID);
}

// =============================================
// 210_全体サマリー
// =============================================
function renderOverview(records, phases, targets, targetsCh) {
  const { overview } = getOutputSheetNames();
  const sheet = _getOrCreateSheet(overview);
  _clearSheet(sheet);

  const cfg = getConfig();
  const company = String(cfg["企業名"] || "（記入してください）").trim();
  const now = new Date();
  const currentYM = monthKey(now);
  const prevYM = monthKey(new Date(now.getFullYear(), now.getMonth() - 1, 1));

  const fStats = aggregateFunnelMonthly(records, phases);
  const aStats = aggregateActive(records);
  const atr = aggregateAttrition(records, phases);
  const lt = aggregateLeadtime(records, phases);
  const landing = aggregateLanding(records, phases, targets);
  // フェーズラベル → 着地見込み数（expected）の引き当てマップ。フェーズ別KPI表・月次着地見込みで共用
  const landingExpectedByLabel = {};
  landing.rows.forEach(lr => { landingExpectedByLabel[lr.label] = lr.expected; });
  const fmtLanding = label => {
    const e = landingExpectedByLabel[label];
    return (e === null || e === undefined) ? "-" : Math.round(e);
  };

  // 主要4KPI: entry/info_joined相当/first_passed相当/accepted
  const kpiKeys = _pickMainKpiKeys(phases);

  // タイトル + サブタイトル
  _bannerTitle(sheet, 1, 14, `${company}　／　RPO 採用ダッシュボード`);
  sheet.getRange(2, 1, 1, 14).merge()
    .setValue(`自動更新: ${formatDatetime(now)}　|　対象月: ${currentYM}`)
    .setBackground(COLOR.bgRowAlt).setFontColor(COLOR.textDim)
    .setFontSize(10).setFontFamily(FONT)
    .setHorizontalAlignment("left").setVerticalAlignment("middle");
  sheet.setRowHeight(2, 24);

  // ===== セクション1: 当月サマリー / 全月サマリー =====
  // 左パネル: cols 1-5（指標+4KPI）、右パネル: cols 10-14（指標+4KPI）
  let r = 4;
  // 左セクション（全セクションのバーを統一: 1-7列分）
  sheet.getRange(r, 1, 1, 7).merge().setValue("■ 当月サマリー（" + currentYM + "）")
    .setBackground(COLOR.totalBg).setFontWeight("bold").setFontSize(11)
    .setHorizontalAlignment("left").setFontFamily(FONT)
    .setBorder(true, true, true, true, false, false, COLOR.bgDark, SpreadsheetApp.BorderStyle.SOLID);
  // 右セクション
  sheet.getRange(r, 9, 1, 5).merge().setValue("■ 全月サマリー（累計）")
    .setBackground(COLOR.totalBg).setFontWeight("bold").setFontSize(11)
    .setHorizontalAlignment("left").setFontFamily(FONT)
    .setBorder(true, true, true, true, false, false, COLOR.bgDark, SpreadsheetApp.BorderStyle.SOLID);
  sheet.setRowHeight(r, 28);
  r++;

  // ヘッダ行
  const leftHeader = ["指標"].concat(kpiKeys.map(k => k.label));
  const rightHeader = ["指標"].concat(kpiKeys.map(k => k.label));
  sheet.getRange(r, 1, 1, leftHeader.length).setValues([leftHeader]);
  sheet.getRange(r, 9, 1, rightHeader.length).setValues([rightHeader]);
  _tableHeader(sheet, r, 1, leftHeader.length);
  _tableHeader(sheet, r, 9, rightHeader.length);
  r++;

  // 当月実績/目標/達成率/前月差 — 全月実績/目標/達成率
  const cardActuals = kpiKeys.map(k => fStats[k.key]?.[currentYM] || 0);
  const cardPrev    = kpiKeys.map(k => fStats[k.key]?.[prevYM] || 0);
  const cardCum     = kpiKeys.map(k => fStats[k.key]?.TOTAL || 0);
  const cardTgtM    = kpiKeys.map(k => targets[k.key]?.[currentYM] || 0);
  const cardTgtT    = kpiKeys.map(k => Object.values(targets[k.key] || {}).reduce((s, n) => s + n, 0));
  const cardRateM   = cardTgtM.map((t, i) => t ? cardActuals[i] / t : null);
  const cardRateT   = cardTgtT.map((t, i) => t ? cardCum[i] / t : null);

  const fmtNum = n => (n === null || n === undefined) ? "-" : String(n);
  const fmtPct = r => (r === null || isNaN(r)) ? "-" : Math.round(r * 100) + "%";
  const fmtDiff = (a, p) => { const d = a - p; return d > 0 ? "+" + d : String(d); };

  // 左テーブル: 当月 4行
  const leftRows = [
    ["実績"].concat(cardActuals),
    ["目標"].concat(cardTgtM.map(t => t || "-")),
    ["達成率"].concat(cardRateM.map(fmtPct)),
    ["前月差"].concat(cardActuals.map((a, i) => fmtDiff(a, cardPrev[i]))),
  ];
  sheet.getRange(r, 1, leftRows.length, leftHeader.length).setValues(leftRows);
  _tableData(sheet, r, 1, leftRows.length, leftHeader.length);
  // 実績行は大きいフォント
  sheet.getRange(r, 2, 1, kpiKeys.length).setFontSize(18).setFontWeight("bold");
  sheet.setRowHeight(r, 44);
  // 達成率行に色付け
  cardRateM.forEach((rate, i) => {
    sheet.getRange(r + 2, 2 + i).setBackground(rateToColor(rate));
  });

  // 右テーブル: 全月 4行
  const rightRows = [
    ["累計実績"].concat(cardCum),
    ["累計目標"].concat(cardTgtT.map(t => t || "-")),
    ["累計達成率"].concat(cardRateT.map(fmtPct)),
    ["進捗"].concat(cardRateT.map(r => r === null ? "-" : r >= 1 ? "達成" : r >= 0.7 ? "注意" : "警戒")),
  ];
  sheet.getRange(r, 9, rightRows.length, rightHeader.length).setValues(rightRows);
  _tableData(sheet, r, 9, rightRows.length, rightHeader.length);
  sheet.getRange(r, 10, 1, kpiKeys.length).setFontSize(18).setFontWeight("bold");
  cardRateT.forEach((rate, i) => {
    sheet.getRange(r + 2, 10 + i).setBackground(rateToColor(rate));
  });
  r += 5;

  // ===== セクション2: フェーズ別 主要KPI / アクティブ =====
  sheet.getRange(r, 1, 1, 8).merge().setValue("■ フェーズ別 主要KPI")
    .setBackground(COLOR.totalBg).setFontWeight("bold").setFontSize(11)
    .setHorizontalAlignment("left").setFontFamily(FONT)
    .setBorder(true, true, true, true, false, false, COLOR.bgDark, SpreadsheetApp.BorderStyle.SOLID);
  sheet.getRange(r, 9, 1, 5).merge().setValue("■ アクティブ学生（選考中）")
    .setBackground(COLOR.totalBg).setFontWeight("bold").setFontSize(11)
    .setHorizontalAlignment("left").setFontFamily(FONT)
    .setBorder(true, true, true, true, false, false, COLOR.bgDark, SpreadsheetApp.BorderStyle.SOLID);
  sheet.setRowHeight(r, 28);
  r++;

  // フェーズ別KPI表（8列・ステータス列は累計達成率セルの色で表現するため削除）
  const kpiHeader = ["フェーズ", "当月実績", "当月目標", "達成率", "累計実績", "累計目標", "累計達成率", "着地見込"];
  sheet.getRange(r, 1, 1, 8).setValues([kpiHeader]);
  _tableHeader(sheet, r, 1, 8);

  // アクティブ表
  const activeHeader = ["選考段階", "人数"];
  sheet.getRange(r, 9, 1, 2).setValues([activeHeader]);
  _tableHeader(sheet, r, 9, 2);
  r++;

  // フェーズ別データ（参加+合格+内定+承諾、予約・後面談は除外）
  const mainPhases = phases.filter(p => p.group === "main" || p.group === "pass" || p.group === "reserved");
  const kpiRows = [];
  const kpiColors = [];
  mainPhases.forEach(p => {
    const actM = fStats[p.key]?.[currentYM] || 0;
    const tgtM = targets[p.key]?.[currentYM] || 0;
    const rateM = tgtM ? actM / tgtM : null;
    const actT = fStats[p.key]?.TOTAL || 0;
    const tgtT = Object.values(targets[p.key] || {}).reduce((s, n) => s + n, 0);
    const rateT = tgtT ? actT / tgtT : null;
    kpiRows.push([p.label, actM, tgtM || "-", fmtPct(rateM), actT, tgtT || "-", fmtPct(rateT), fmtLanding(p.label)]);
    kpiColors.push([COLOR.bgRow, COLOR.bgRow, COLOR.bgRow, rateToColor(rateM), COLOR.bgRow, COLOR.bgRow, rateToColor(rateT), COLOR.bgRow]);
  });
  if (kpiRows.length) {
    const rng = sheet.getRange(r, 1, kpiRows.length, 8);
    rng.setValues(kpiRows);
    rng.setBackgrounds(kpiColors);
    _tableData(sheet, r, 1, kpiRows.length, 8, { keepBg: true });
  }

  // アクティブデータ
  const activeRows = Object.entries(aStats).filter(([, n]) => n > 0).map(([s, n]) => [s, n]);
  const totalActive = activeRows.reduce((s, row) => s + row[1], 0);
  activeRows.push(["合計（選考中）", totalActive]);
  if (activeRows.length) {
    sheet.getRange(r, 9, activeRows.length, 2).setValues(activeRows);
    _tableData(sheet, r, 9, activeRows.length, 2);
    sheet.getRange(r + activeRows.length - 1, 10, 1, 2)
      .setBackground(COLOR.totalBg).setFontWeight("bold");
  }
  r += Math.max(kpiRows.length, activeRows.length) + 2;

  // ===== セクション3: 月次ファネル（実績／目標／差分 を3表に分割） =====
  const funnelPhases = phases.filter(p => p.group === "main" || p.group === "pass" || p.group === "reserved");
  const months = buildMonthList();
  const cohortFunnel = aggregateFunnelByEntryMonth(records, phases);
  const activeMonths = months.filter(m => (cohortFunnel[m.ym]?.TOTAL || 0) > 0 || funnelPhases.some(k => (targets[k.key]?.[m.ym] || 0) > 0));
  if (activeMonths.length === 0) activeMonths.push(months[0]);

  // 各月の値を事前計算
  const totalActsArr = funnelPhases.map(k => cohortFunnel.TOTAL?.[k.key] || 0);
  const totalTgtsArr = funnelPhases.map(k => Object.values(targets[k.key] || {}).reduce((s, n) => s + n, 0));

  // フェーズ別ファネル表 汎用描画ヘルパー（月次・大学別・媒体別で共用）
  // dimHeader: 行見出しラベル（"月"/"大学"/"媒体" 等）
  // dataRows:  [{ label, values: [funnelPhases順の数値] }]
  // totalValues: 合計行の値配列（funnelPhases順）。null の場合は合計行を出さない
  // diffColoring=true で差分テーブル用にセル色付け（+緑/-赤）
  const renderFunnelTable = (title, dimHeader, dataRows, totalValues, formatter, diffColoring) => {
    const cols = 1 + funnelPhases.length;
    sheet.getRange(r, 1, 1, cols).merge().setValue(title)
      .setBackground(COLOR.totalBg).setFontWeight("bold").setFontSize(11)
      .setHorizontalAlignment("left").setFontFamily(FONT)
      .setBorder(true, true, true, true, false, false, COLOR.bgDark, SpreadsheetApp.BorderStyle.SOLID);
    sheet.setRowHeight(r, 28);
    r++;

    const hdr = [dimHeader].concat(funnelPhases.map(k => k.label));
    sheet.getRange(r, 1, 1, hdr.length).setValues([hdr]);
    _tableHeader(sheet, r, 1, hdr.length);
    r++;

    const fmt = formatter || (v => v);
    const rawValues = dataRows.map(d => d.values);
    const rows = dataRows.map(d => [d.label].concat(d.values.map(fmt)));
    const hasTotal = totalValues != null;
    if (hasTotal) rows.push(["合計"].concat(totalValues.map(fmt)));

    sheet.getRange(r, 1, rows.length, hdr.length).setValues(rows);
    _tableData(sheet, r, 1, rows.length, hdr.length);

    // 差分テーブルのみセル色付け（達成=緑、未達=赤）
    if (diffColoring) {
      const bgs = [];
      rawValues.forEach(vals => {
        const rowBg = ["#FFFFFF"]; // 行ラベル列
        vals.forEach(v => {
          if (v > 0) rowBg.push("#C8E6C9");        // 緑（達成超過）
          else if (v === 0) rowBg.push("#F5F5F5"); // グレー（同等）
          else rowBg.push("#FFCDD2");              // 赤（未達）
        });
        bgs.push(rowBg);
      });
      if (hasTotal) {
        const totalBg = ["#FFFFFF"];
        totalValues.forEach(v => {
          if (v > 0) totalBg.push("#A5D6A7");
          else if (v === 0) totalBg.push("#E0E0E0");
          else totalBg.push("#EF9A9A");
        });
        bgs.push(totalBg);
      }
      sheet.getRange(r, 1, rows.length, hdr.length).setBackgrounds(bgs);
    }

    // 合計行を強調
    if (hasTotal && !diffColoring) {
      sheet.getRange(r + rows.length - 1, 1, 1, hdr.length)
        .setBackground(COLOR.bgRowAlt);
    }
    if (hasTotal) {
      sheet.getRange(r + rows.length - 1, 1, 1, hdr.length).setFontWeight("bold");
    }
    r += rows.length + 2;
  };

  // 3-A: 実績テーブル（コホート）
  renderFunnelTable(
    "■ 月次ファネル 実績（コホート: その月にエントリーした人の到達数）",
    "月",
    activeMonths.map(m => ({ label: m.label, values: funnelPhases.map(k => cohortFunnel[m.ym]?.[k.key] || 0) })),
    totalActsArr,
  );

  // 3-B: 目標テーブル
  renderFunnelTable(
    "■ 月次ファネル 目標",
    "月",
    activeMonths.map(m => ({ label: m.label, values: funnelPhases.map(k => targets[k.key]?.[m.ym] || 0) })),
    totalTgtsArr,
    v => v || "-",
  );

  // 3-C: 差分テーブル（実績 - 目標。プラスは「+5」表記、達成=緑/未達=赤）
  renderFunnelTable(
    "■ 月次ファネル 差分（実績 − 目標）",
    "月",
    activeMonths.map(m => ({ label: m.label, values: funnelPhases.map(k => (cohortFunnel[m.ym]?.[k.key] || 0) - (targets[k.key]?.[m.ym] || 0)) })),
    totalActsArr.map((a, i) => a - totalTgtsArr[i]),
    d => d > 0 ? "+" + d : String(d),
    true,  // diffColoring 有効
  );

  // 3-D: フェーズ別 着地見込み（アクティブ × 累積目標通過率）
  // funnelPhases 順に landingExpectedByLabel から expected を並べる（共通マップを再利用）
  const landingValues = funnelPhases.map(k => fmtLanding(k.label));
  renderFunnelTable(
    `■ フェーズ別 着地見込み（最終着地予想 ${landing.grandTotal.toFixed(1)}名 = 既承諾 ${landing.alreadyAccepted} + アクティブ予測 ${landing.totalExpected.toFixed(1)}）`,
    "見込み",
    [{ label: "着地見込", values: landingValues }],
    null,  // 合計行なし
  );

  // 次元別 累計ファネルの共通描画（大学別・媒体別）
  // statsByDim: { dimName: { entry, byPhase:{key:count} } } を funnelPhases 順の行に変換
  // topN を指定した場合は entry 上位N件＋「その他」集約。合計行は全件のフェーズ別累計。
  const renderDimFunnel = (title, dimHeader, statsByDim, topN) => {
    let entries = Object.entries(statsByDim)
      .filter(([, s]) => s.entry > 0)
      .sort((a, b) => b[1].entry - a[1].entry);
    if (entries.length === 0) {
      sheet.getRange(r, 1, 1, 1 + funnelPhases.length).merge().setValue(title)
        .setBackground(COLOR.totalBg).setFontWeight("bold").setFontSize(11)
        .setHorizontalAlignment("left").setFontFamily(FONT);
      r++;
      sheet.getRange(r, 1, 1, 1 + funnelPhases.length).setValue("（データなし）");
      r += 2;
      return;
    }
    // 合計（全件のフェーズ別累計）
    const totalValues = funnelPhases.map(k =>
      entries.reduce((sum, [, s]) => sum + (s.byPhase[k.key] || 0), 0));

    let dataRows;
    if (topN && entries.length > topN) {
      const head = entries.slice(0, topN);
      const rest = entries.slice(topN);
      dataRows = head.map(([name, s]) => ({
        label: name, values: funnelPhases.map(k => s.byPhase[k.key] || 0),
      }));
      const otherValues = funnelPhases.map(k =>
        rest.reduce((sum, [, s]) => sum + (s.byPhase[k.key] || 0), 0));
      dataRows.push({ label: `その他（${rest.length}件）`, values: otherValues });
    } else {
      dataRows = entries.map(([name, s]) => ({
        label: name, values: funnelPhases.map(k => s.byPhase[k.key] || 0),
      }));
    }
    renderFunnelTable(title, dimHeader, dataRows, totalValues);
  };

  // 3-E: 大学別 累計ファネル（エントリー上位10校＋その他）
  renderDimFunnel(
    "■ 大学別 累計ファネル（各フェーズ到達数・エントリー上位10校）",
    "大学",
    aggregateBySchool(records, phases),
    10,
  );

  // 3-F: 媒体別 累計ファネル（エントリー経路別・全件）
  renderDimFunnel(
    "■ 媒体別 累計ファネル（各フェーズ到達数）",
    "媒体",
    aggregateByChannel(records, phases),
  );

  // ===== セクション4: チャネル/大学Top5 + リードタイム + ランク =====
  sheet.getRange(r, 1, 1, 7).merge().setValue("■ チャネル別Top5（当月エントリー）")
    .setBackground(COLOR.totalBg).setFontWeight("bold").setFontSize(11)
    .setHorizontalAlignment("left").setFontFamily(FONT)
    .setBorder(true, true, true, true, false, false, COLOR.bgDark, SpreadsheetApp.BorderStyle.SOLID);
  sheet.getRange(r, 9, 1, 5).merge().setValue("■ 大学別Top5（採用効率順）")
    .setBackground(COLOR.totalBg).setFontWeight("bold").setFontSize(11)
    .setHorizontalAlignment("left").setFontFamily(FONT)
    .setBorder(true, true, true, true, false, false, COLOR.bgDark, SpreadsheetApp.BorderStyle.SOLID);
  sheet.setRowHeight(r, 28);
  r++;

  // チャネル別Top5（当月実績ベース）
  const cStats = aggregateChannelMonthly(records);
  const chTop = Object.entries(cStats)
    .map(([ch, s]) => ({ ch, act: s[currentYM] || 0, tgt: targetsCh[ch]?.[currentYM] || 0 }))
    .sort((a, b) => b.act - a.act).slice(0, 5);
  sheet.getRange(r, 1, 1, 5).setValues([["チャネル", "実績", "目標", "達成率", "差分"]]);
  _tableHeader(sheet, r, 1, 5);
  const chRows = chTop.map(c => [
    c.ch, c.act, c.tgt || "-",
    fmtPct(c.tgt ? c.act / c.tgt : null),
    c.tgt ? (c.act - c.tgt > 0 ? "+" + (c.act - c.tgt) : String(c.act - c.tgt)) : "-",
  ]);

  // 大学別Top5（採用効率順）
  const schoolStats = aggregateBySchool(records, phases);
  const acceptedKey = phases.find(p => p.label === "内定承諾")?.key;
  // 1次合格 = 一次面接【合格】 (raw は漢字「一次」のみ。"1次"表記には未対応)
  const firstPassedKey = phases.find(p => p.label === "一次面接【合格】" || p.label === "1次面接【合格】")?.key;
  const schoolTop = Object.entries(schoolStats)
    .map(([sch, s]) => ({
      sch, entry: s.entry,
      firstPass: firstPassedKey ? s.byPhase[firstPassedKey] || 0 : 0,
      accepted:  acceptedKey ? s.byPhase[acceptedKey] || 0 : 0,
      efficiency: s.entry ? (acceptedKey ? (s.byPhase[acceptedKey] || 0) / s.entry : 0) : 0,
    }))
    .filter(s => s.entry > 0)
    .sort((a, b) => b.efficiency - a.efficiency || b.entry - a.entry)
    .slice(0, 5);
  sheet.getRange(r, 9, 1, 5).setValues([["大学", "エントリー", "1次合格", "内定承諾", "効率%"]]);
  _tableHeader(sheet, r, 9, 5);
  const schoolRows = schoolTop.map(s => [
    s.sch, s.entry, s.firstPass, s.accepted, fmtPct(s.efficiency),
  ]);
  r++;
  if (chRows.length) {
    sheet.getRange(r, 1, chRows.length, 5).setValues(chRows);
    _tableData(sheet, r, 1, chRows.length, 5);
  }
  if (schoolRows.length) {
    sheet.getRange(r, 9, schoolRows.length, 5).setValues(schoolRows);
    _tableData(sheet, r, 9, schoolRows.length, 5);
  }
  r += Math.max(chRows.length, schoolRows.length) + 2;

  // セクション5: 評価ランク / リードタイム
  sheet.getRange(r, 1, 1, 7).merge().setValue("■ 評価ランク分布（合計）")
    .setBackground(COLOR.totalBg).setFontWeight("bold").setFontSize(11)
    .setHorizontalAlignment("left").setFontFamily(FONT)
    .setBorder(true, true, true, true, false, false, COLOR.bgDark, SpreadsheetApp.BorderStyle.SOLID);
  sheet.getRange(r, 9, 1, 5).merge().setValue("■ リードタイム（中央値）")
    .setBackground(COLOR.totalBg).setFontWeight("bold").setFontSize(11)
    .setHorizontalAlignment("left").setFontFamily(FONT)
    .setBorder(true, true, true, true, false, false, COLOR.bgDark, SpreadsheetApp.BorderStyle.SOLID);
  sheet.setRowHeight(r, 28);
  r++;
  // 7列に統一（合計列は削除、S+A率を色付きで強調）
  sheet.getRange(r, 1, 1, 7).setValues([["フェーズ", "S", "A", "B", "C", "D", "S+A率"]]);
  _tableHeader(sheet, r, 1, 7);
  sheet.getRange(r, 9, 1, 4).setValues([["遷移", "サンプル", "中央値(日)", "P90(日)"]]);
  _tableHeader(sheet, r, 9, 4);
  r++;

  const rank = aggregateRanking(records, phases);
  const rankEntries = Object.entries(rank).filter(([, s]) => s.TOTAL > 0);
  const rankRows = rankEntries.map(([, s]) => {
    const sa = s.S + s.A;
    return [s.label, s.S, s.A, s.B, s.C, s.D, fmtPct(s.TOTAL ? sa / s.TOTAL : null)];
  });
  const rankColors = rankEntries.map(([, s]) => {
    const sa = s.S + s.A;
    const rate = s.TOTAL ? sa / s.TOTAL : null;
    return [COLOR.bgRow, COLOR.bgRow, COLOR.bgRow, COLOR.bgRow, COLOR.bgRow, COLOR.bgRow, rateToColor(rate)];
  });
  if (rankRows.length) {
    sheet.getRange(r, 1, rankRows.length, 7).setValues(rankRows);
    sheet.getRange(r, 1, rankRows.length, 7).setBackgrounds(rankColors);
    _tableData(sheet, r, 1, rankRows.length, 7, { keepBg: true });
  } else {
    sheet.getRange(r, 1, 1, 7).setValues([["（評価データなし）", "", "", "", "", "", ""]]);
    _tableData(sheet, r, 1, 1, 7);
  }

  const ltRows = Object.values(lt)
    .filter(t => t.count > 0)
    .sort((a, b) => b.count - a.count)
    .slice(0, 5)
    .map(t => [t.label, t.count, t.median?.toFixed(1) || "-", t.p90?.toFixed(1) || "-"]);
  if (ltRows.length) {
    sheet.getRange(r, 9, ltRows.length, 4).setValues(ltRows);
    _tableData(sheet, r, 9, ltRows.length, 4);
  } else {
    sheet.getRange(r, 9, 1, 4).setValues([["（データ未蓄積）", "", "", ""]]);
    _tableData(sheet, r, 9, 1, 4);
  }

  // 列幅: 左パネル A-G (7列・データはA-E使用、フェーズ別主要KPIはA-G使用), col H はギャップ, 右パネル I-M (5列)
  // 列幅: A列はフェーズラベルが見切れない幅、B列以降は100pxで統一
  sheet.setColumnWidth(1, 170);
  for (let c = 2; c <= 16; c++) sheet.setColumnWidth(c, 100);

  sheet.setHiddenGridlines(true);
}

// 主要4KPIキーを動的に選ぶ
function _pickMainKpiKeys(phases) {
  const wanted = ["エントリー", "説明選考会", "1次面接", "1次合格", "内定承諾"];
  const picked = [];
  // ラベルに「エントリー」を含む最初
  const entry = phases.find(p => p.label.includes("エントリー"));
  if (entry) picked.push(entry);
  // 説明選考会参加（mainグループ）
  const info = phases.find(p => p.label.includes("説明選考会") && p.group === "main");
  if (info) picked.push(info);
  // 1次合格
  const firstPass = phases.find(p => p.label.includes("一次面接【合格】") || p.label.includes("1次面接【合格】"));
  if (firstPass) picked.push(firstPass);
  // 内定承諾
  const accepted = phases.find(p => p.label.includes("内定承諾"));
  if (accepted) picked.push(accepted);
  // フォールバック: 足りなければmain上位を補充
  if (picked.length < 4) {
    phases.filter(p => p.group === "main").forEach(p => {
      if (!picked.includes(p) && picked.length < 4) picked.push(p);
    });
  }
  return picked.slice(0, 4);
}

// =============================================
// 220_大学別歩留まり実績
// =============================================
function renderBySchool(records, phases) {
  const { bySchool } = getOutputSheetNames();
  const sheet = _getOrCreateSheet(bySchool);
  _clearSheet(sheet);

  const schoolStats = aggregateBySchool(records, phases);
  const cross = aggregateSchoolByChannel(records);

  // 主要フェーズ: 参加・合格・内定・承諾を全て含める（予約と後面談は除く）
  const mainPhases = phases.filter(p => p.group === "main" || p.group === "pass" || p.group === "reserved");
  // 累計フェーズ列とその通過率列
  const phaseCount = mainPhases.length;
  const tableCols = 1 + phaseCount + (phaseCount - 1) + 1; // 大学 + フェーズ件数 + 通過率(1次-1)+ 効率%

  const now = new Date();
  _bannerTitle(sheet, 1, Math.max(tableCols, 20),
    `大学別 歩留まり実績　／　自動更新: ${formatDatetime(now)}　／　累計エントリー: ${records.length}名`);

  // ターゲットセクション
  let r = 3;
  sheet.getRange(r, 1, 1, 4).merge().setValue("■ 全体ターゲット vs 進捗")
    .setBackground(COLOR.totalBg).setFontWeight("bold").setFontSize(11)
    .setHorizontalAlignment("left").setFontFamily(FONT)
    .setBorder(true, true, true, true, false, false, COLOR.bgDark, SpreadsheetApp.BorderStyle.SOLID);
  r++;
  sheet.getRange(r, 1, 1, 4).setValues([["", "目標", "進捗", "乖離"]]);
  _tableHeader(sheet, r, 1, 4);
  r++;
  const fStats = aggregateFunnelMonthly(records, phases);
  const targetsFun = loadTargetsFunnel(phases);
  const offerKey = phases.find(p => p.label === "内定")?.key;
  const acceptKey = phases.find(p => p.label === "内定承諾")?.key;
  const offerTgt = offerKey ? Object.values(targetsFun[offerKey] || {}).reduce((s, n) => s + n, 0) : 0;
  const offerAct = offerKey ? (fStats[offerKey]?.TOTAL || 0) : 0;
  const acceptTgt = acceptKey ? Object.values(targetsFun[acceptKey] || {}).reduce((s, n) => s + n, 0) : 0;
  const acceptAct = acceptKey ? (fStats[acceptKey]?.TOTAL || 0) : 0;
  sheet.getRange(r, 1, 2, 4).setValues([
    ["内定", offerTgt || "-", offerAct, offerAct - offerTgt],
    ["内定承諾", acceptTgt || "-", acceptAct, acceptAct - acceptTgt],
  ]);
  _tableData(sheet, r, 1, 2, 4);
  r += 3;

  // 大学別ファネル + 通過率
  sheet.getRange(r, 1, 1, tableCols).merge().setValue("■ 大学別 累計ファネル + フェーズ別通過率")
    .setBackground(COLOR.totalBg).setFontWeight("bold").setFontSize(11)
    .setHorizontalAlignment("left").setFontFamily(FONT)
    .setBorder(true, true, true, true, false, false, COLOR.bgDark, SpreadsheetApp.BorderStyle.SOLID);
  r++;

  const countHeader = ["大学名"].concat(mainPhases.map(p => p.label));
  const rateHeader = mainPhases.slice(1).map((p, i) => `${mainPhases[i].label}→${p.label}`);
  const fullHeader = countHeader.concat(rateHeader).concat(["エントリー→承諾"]);
  sheet.getRange(r, 1, 1, fullHeader.length).setValues([fullHeader]);
  _tableHeader(sheet, r, 1, fullHeader.length);
  // 件数部と率部で色分け
  sheet.getRange(r, 1, 1, 1 + phaseCount).setBackground(COLOR.bgDark);
  sheet.getRange(r, 2 + phaseCount, 1, phaseCount).setBackground(COLOR.bgPanel);
  r++;

  // ソート: 採用効率（承諾/エントリー）降順
  const sorted = Object.entries(schoolStats)
    .filter(([, s]) => s.entry > 0)
    .map(([sch, s]) => {
      const counts = mainPhases.map(p => s.byPhase[p.key] || 0);
      const rates = [];
      for (let i = 0; i < mainPhases.length - 1; i++) {
        rates.push(counts[i] ? counts[i + 1] / counts[i] : null);
      }
      const eff = counts[0] && acceptKey ? (s.byPhase[acceptKey] || 0) / counts[0] : 0;
      return { sch, counts, rates, eff, entry: s.entry };
    })
    .sort((a, b) => b.eff - a.eff || b.entry - a.entry);

  const schoolRows = sorted.map(x => {
    return [x.sch].concat(x.counts).concat(
      x.rates.map(r => r === null ? "—" : Math.round(r * 100) + "%")
    ).concat([Math.round(x.eff * 100) + "%"]);
  });

  // 合計行
  const totalCounts = mainPhases.map(p => fStats[p.key]?.TOTAL || 0);
  const totalRates = [];
  for (let i = 0; i < mainPhases.length - 1; i++) {
    totalRates.push(totalCounts[i] ? totalCounts[i + 1] / totalCounts[i] : null);
  }
  const totalEff = totalCounts[0] && acceptKey ? (fStats[acceptKey]?.TOTAL || 0) / totalCounts[0] : 0;
  schoolRows.push(["合計"].concat(totalCounts).concat(
    totalRates.map(r => r === null ? "—" : Math.round(r * 100) + "%")
  ).concat([Math.round(totalEff * 100) + "%"]));

  if (schoolRows.length) {
    sheet.getRange(r, 1, schoolRows.length, fullHeader.length).setValues(schoolRows);
    _tableData(sheet, r, 1, schoolRows.length, fullHeader.length);
    // 合計行を強調
    sheet.getRange(r + schoolRows.length - 1, 1, 1, fullHeader.length)
      .setBackground(COLOR.totalBg).setFontWeight("bold");
  }
  r += schoolRows.length + 2;

  // 大学×経路 クロス集計
  const channels = cross.channels;
  sheet.getRange(r, 1, 1, channels.length + 2).merge().setValue("■ 大学×経路 クロス集計")
    .setBackground(COLOR.totalBg).setFontWeight("bold").setFontSize(11)
    .setHorizontalAlignment("left").setFontFamily(FONT)
    .setBorder(true, true, true, true, false, false, COLOR.bgDark, SpreadsheetApp.BorderStyle.SOLID);
  r++;
  const crossHdr = ["大学"].concat(channels).concat(["合計"]);
  sheet.getRange(r, 1, 1, crossHdr.length).setValues([crossHdr]);
  _tableHeader(sheet, r, 1, crossHdr.length);
  r++;
  const crossRows = sorted.slice(0, 10).map(x => {
    const row = [x.sch];
    let sum = 0;
    channels.forEach(ch => {
      const v = cross.result[x.sch]?.[ch] || 0;
      row.push(v);
      sum += v;
    });
    row.push(sum);
    return row;
  });
  if (crossRows.length) {
    sheet.getRange(r, 1, crossRows.length, crossHdr.length).setValues(crossRows);
    _tableData(sheet, r, 1, crossRows.length, crossHdr.length);
  }

  // 列幅
  sheet.setColumnWidth(1, 200);
  for (let c = 2; c <= 25; c++) sheet.setColumnWidth(c, 88);
  sheet.setHiddenGridlines(true);
}

// =============================================
// 230_エントリー経路別実績
// =============================================
function renderEntryChannel(records, phases, targetsCh) {
  const { byChannel } = getOutputSheetNames();
  const sheet = _getOrCreateSheet(byChannel);
  _clearSheet(sheet);

  const months = buildMonthList();
  const cStats = aggregateChannelMonthly(records);
  const now = new Date();

  // チャネル一覧（目標+実績）
  const allChannels = new Set([...Object.keys(targetsCh), ...Object.keys(cStats)]);
  const channels = [...allChannels].sort();

  const totalCols = 4 + months.length * 3;
  _bannerTitle(sheet, 1, totalCols, `エントリー経路別 実績　／　自動更新: ${formatDatetime(now)}　／　累計エントリー: ${records.length}名`);

  // セクション1: 月別 目標/実績/差分
  let r = 3;
  sheet.getRange(r, 1, 1, totalCols).merge().setValue("■ チャネル × 月別  目標 / 実績 / 差分")
    .setBackground(COLOR.totalBg).setFontWeight("bold").setFontSize(11)
    .setHorizontalAlignment("left").setFontFamily(FONT)
    .setBorder(true, true, true, true, false, false, COLOR.bgDark, SpreadsheetApp.BorderStyle.SOLID);
  r++;

  // ヘッダ2段
  const hdr1 = ["チャネル", "累計目標", "累計実績", "累計差分"];
  const hdr2 = ["", "", "", ""];
  months.forEach(m => {
    hdr1.push(m.label, "", "");
    hdr2.push("目標", "実績", "差分");
  });
  sheet.getRange(r, 1, 1, totalCols).setValues([hdr1]);
  sheet.getRange(r + 1, 1, 1, totalCols).setValues([hdr2]);
  months.forEach((m, i) => { sheet.getRange(r, 5 + i * 3, 1, 3).merge(); });
  _tableHeader(sheet, r, 1, totalCols);
  _tableHeader(sheet, r + 1, 1, totalCols);
  r += 2;

  // データ
  const rows = [];
  const colors = [];
  channels.forEach(ch => {
    let totalTgt = 0, totalAct = 0;
    const row = [ch, 0, 0, 0];
    const rowColors = [COLOR.bgRow, COLOR.bgRow, COLOR.bgRow, COLOR.bgRow];
    months.forEach(m => {
      const tgt = targetsCh[ch]?.[m.ym] || 0;
      const act = cStats[ch]?.[m.ym] || 0;
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
    rows.push(row);
    colors.push(rowColors);
  });
  // 合計行
  if (rows.length) {
    const totalRow = ["合計"].concat(Array(totalCols - 1).fill(""));
    // 合計列の合算
    let gTgt = 0, gAct = 0;
    rows.forEach(rw => { gTgt += rw[1] || 0; gAct += rw[2] || 0; });
    totalRow[1] = gTgt;
    totalRow[2] = gAct;
    totalRow[3] = gAct - gTgt;
    rows.push(totalRow);
    colors.push(Array(totalCols).fill(COLOR.totalBg));

    sheet.getRange(r, 1, rows.length, totalCols).setValues(rows);
    sheet.getRange(r, 1, rows.length, totalCols).setBackgrounds(colors);
    _tableData(sheet, r, 1, rows.length, totalCols, { keepBg: true });
    sheet.getRange(r + rows.length - 1, 1, 1, totalCols)
      .setFontWeight("bold").setBackground(COLOR.totalBg);
  }
  r += rows.length + 2;

  // セクション2: チャネル別累計ファネル + 歩留まり
  sheet.getRange(r, 1, 1, 8).merge().setValue("■ チャネル別 累計ファネル（品質比較）")
    .setBackground(COLOR.totalBg).setFontWeight("bold").setFontSize(11)
    .setHorizontalAlignment("left").setFontFamily(FONT)
    .setBorder(true, true, true, true, false, false, COLOR.bgDark, SpreadsheetApp.BorderStyle.SOLID);
  r++;
  const mainPhases = phases.filter(p => p.group === "main" || p.group === "pass" || p.group === "reserved");
  const ffHdr = ["チャネル"].concat(mainPhases.map(p => p.label)).concat(["エントリー→承諾率"]);
  sheet.getRange(r, 1, 1, ffHdr.length).setValues([ffHdr]);
  _tableHeader(sheet, r, 1, ffHdr.length);
  r++;

  // チャネル別の各フェーズ累計
  const channelFunnel = {};
  records.forEach(rec => {
    const ch = rec.channel || "(未分類)";
    if (!channelFunnel[ch]) {
      channelFunnel[ch] = {};
      mainPhases.forEach(p => { channelFunnel[ch][p.key] = 0; });
    }
    mainPhases.forEach(p => {
      if (rec.arrivals[p.key]) channelFunnel[ch][p.key]++;
    });
  });
  const acceptKey = phases.find(p => p.label === "内定承諾")?.key;
  const cfRows = Object.entries(channelFunnel)
    .filter(([, m]) => Object.values(m).reduce((s, n) => s + n, 0) > 0)
    .sort((a, b) => (b[1][mainPhases[0].key] || 0) - (a[1][mainPhases[0].key] || 0))
    .map(([ch, m]) => {
      const counts = mainPhases.map(p => m[p.key] || 0);
      const eff = counts[0] && acceptKey ? (m[acceptKey] || 0) / counts[0] : 0;
      return [ch].concat(counts).concat([Math.round(eff * 100) + "%"]);
    });
  if (cfRows.length) {
    sheet.getRange(r, 1, cfRows.length, ffHdr.length).setValues(cfRows);
    _tableData(sheet, r, 1, cfRows.length, ffHdr.length);
  }

  // 列幅
  sheet.setColumnWidth(1, 220);
  for (let c = 2; c <= totalCols; c++) sheet.setColumnWidth(c, 75);
  sheet.setHiddenGridlines(true);
}

// =============================================
// 240_バイネーム進捗管理シート
// =============================================
function renderByName(records, phases) {
  const { byName } = getOutputSheetNames();
  const sheet = _getOrCreateSheet(byName);
  _clearSheet(sheet);

  const now = new Date();
  // exit フェーズが定義されていれば離脱種別/フェーズ/日 列を末尾に追加
  const exitPhases = phases.filter(p => p.group === "exit");
  const hasExit = exitPhases.length > 0;
  const headers = [
    "#", "ID", "姓", "名", "セイ", "メイ",
    "学校名",
    "経路", "現在の選考段階", "選考状況",
    "エントリー日", "経過日数",
    "次回選考種別", "次回予約日",
    "直近の評価", "直近フェーズ",
    "直近活動日", "停滞日数",
    "リスク",
  ].concat(hasExit ? ["離脱種別", "離脱フェーズ", "離脱日"] : []);
  const cols = headers.length;

  // タイトル: 固定列との衝突回避のため merge せず、背景色だけ全列に
  sheet.getRange(1, 1).setValue(`バイネーム進捗管理　／　自動更新: ${formatDatetime(now)}　／　${records.length}名`);
  sheet.getRange(1, 1, 1, cols)
    .setBackground(COLOR.bgDark).setFontColor(COLOR.fgWhite)
    .setFontWeight("bold").setFontSize(13).setFontFamily(FONT)
    .setHorizontalAlignment("left").setVerticalAlignment("middle")
    .setBorder(true, true, true, true, false, false, COLOR.bgDark, SpreadsheetApp.BorderStyle.SOLID);
  sheet.setRowHeight(1, 40);
  sheet.getRange(2, 1, 1, cols).setValues([headers]);
  _tableHeader(sheet, 2, 1, cols);

  // フェーズ順序から次回選考を判定するマップ
  const phaseByLabel = {};
  phases.forEach(p => { phaseByLabel[p.label] = p; });

  const enriched = records.map((rec, i) => {
    const entryPhase = phases[0];
    const entryDt = entryPhase ? rec.arrivals[entryPhase.key] : null;
    const entryDays = entryDt ? Math.floor((now - entryDt) / (24 * 60 * 60 * 1000)) : null;

    let lastActivity = null, lastPhaseLabel = "";
    phases.forEach(p => {
      const d = rec.arrivals[p.key];
      if (d && (!lastActivity || d > lastActivity)) {
        lastActivity = d;
        lastPhaseLabel = p.label;
      }
    });
    const stagnant = lastActivity ? Math.floor((now - lastActivity) / (24 * 60 * 60 * 1000)) : null;

    // 直近の評価
    let latestEval = "", latestEvalPhase = "";
    const evalOrder = phases.filter(p => p.group === "main").reverse();
    for (const p of evalOrder) {
      if (rec.evals[p.key]) {
        latestEval = rec.evals[p.key];
        latestEvalPhase = p.label;
        break;
      }
    }

    // 次回選考種別と予約日
    // ロジック:
    //   1. 候補者が現在いる位置以降で「次に到来する予約フェーズ（reserved）」を探す
    //      - 現在ステージ自体が【予約】なら、そのフェーズの予約日を見る
    //      - そうでなければ、次の reserved フェーズへ
    //   2. 予約日は raw 〇〇【予約】列の素の値 = rec.scheduled[p.key] を使う
    //   3. 表示ラベルは「〇〇」とし、【予約】サフィックスは除去
    let nextStageName = "", nextReserveDate = "", nextStatus = "";
    if (_isActiveRecord(rec)) {
      const idx = phases.findIndex(p => p.label === rec.currentStage);
      // idx 以降で reserved グループの予約フェーズを探す（現在ステージ自体が予約ならそれを使う）
      let bookingPhase = null;
      const startIdx = idx >= 0 ? idx : 0;
      for (let j = startIdx; j < phases.length; j++) {
        if (phases[j].group === "reserved") { bookingPhase = phases[j]; break; }
      }
      if (bookingPhase) {
        nextStageName = bookingPhase.label.replace(/[【]予約[】]/, "");
        // 予約された実施予定日 = raw 〇〇【予約】列の素の値
        const scheduledDt = rec.scheduled[bookingPhase.key];
        if (scheduledDt) {
          nextReserveDate = formatDate(scheduledDt);
          nextStatus = "予約済";
        } else {
          nextReserveDate = "未予約";
          nextStatus = "未予約";
        }
      } else {
        // 予約フェーズが見つからない（最終選考以降など）→ 次の main/pass を表示
        for (let j = startIdx + 1; j < phases.length; j++) {
          const g = phases[j].group;
          if (g === "main" || g === "pass") {
            nextStageName = phases[j].label;
            const d = rec.arrivals[phases[j].key];
            if (d) { nextReserveDate = formatDate(d); nextStatus = "予約済"; }
            else { nextReserveDate = "未予約"; nextStatus = "未予約"; }
            break;
          }
        }
      }
    }

    const flags = [];
    if (_isActiveRecord(rec)) {
      // 次回予約済の学生は停滞扱いしない（予約日まで待っているだけのため）
      if (nextStatus === "未予約" && stagnant !== null && stagnant > 7) flags.push("未予約+停滞");
      else if (nextStatus === "未予約") flags.push("未予約");
      else if (nextStatus !== "予約済" && stagnant !== null && stagnant > 14) flags.push("停滞14日超");
      else if (nextStatus !== "予約済" && stagnant !== null && stagnant > 7) flags.push("停滞7日超");
    } else {
      const accKey = phases.find(p => p.label === "内定承諾")?.key;
      if (accKey && rec.arrivals[accKey]) flags.push("承諾");
      else flags.push("離脱");
    }
    if (latestEval === "S") flags.push("S評価");
    if (latestEval === "D") flags.push("D評価");

    // 離脱種別 / 離脱フェーズ / 離脱日
    // アクティブ学生（選考中で且つcurrentStageがexitでない）には表示しない
    // → 過去にexit到達日が記録されていても、その後復帰した可能性があるため
    let exitType = "", exitPhase = "", exitDate = "";
    if (hasExit && !_isActiveRecord(rec)) {
      let latestExitDt = null;
      exitPhases.forEach(p => {
        const d = rec.arrivals[p.key];
        if (d && (!latestExitDt || d > latestExitDt)) {
          latestExitDt = d;
          exitType = /[【]不合格[】]/.test(p.label) ? "不合格" :
                     /[【]不参加[】]/.test(p.label) ? "不参加" :
                     /[【]辞退[】]|^内定辞退$/.test(p.label) ? "辞退" : "";
          exitPhase = p.label;
          exitDate = formatDate(d);
        }
      });
    }

    const baseRow = [
      i + 1, rec.id, rec.lastName, rec.firstName, rec.lastKana, rec.firstKana, rec.school,
      rec.channel, rec.currentStage, rec.status,
      entryDt ? formatDate(entryDt) : "",
      entryDays === null ? "" : entryDays,
      nextStageName || "-",
      nextReserveDate || "-",
      latestEval || "-",
      latestEvalPhase || "-",
      lastActivity ? formatDate(lastActivity) : "",
      stagnant === null ? "" : stagnant,
      flags.join(" / "),
    ];
    return {
      row: hasExit ? baseRow.concat([exitType || "-", exitPhase || "-", exitDate || "-"]) : baseRow,
      stagnant,
      isActive: _isActiveRecord(rec),
      nextStatus,
    };
  });

  // 並び替え: アクティブ → 停滞日数降順
  enriched.sort((a, b) => {
    if (a.isActive !== b.isActive) return a.isActive ? -1 : 1;
    return (b.stagnant || 0) - (a.stagnant || 0);
  });

  const dataRows = enriched.map((e, i) => { e.row[0] = i + 1; return e.row; });
  const dataColors = enriched.map(e => {
    // 予約済の学生は停滞色にしない（予約日まで待機しているだけのため）
    const isBooked = e.nextStatus === "予約済";
    const bg = !e.isActive ? COLOR.bgRowAlt :
               e.nextStatus === "未予約" ? "#FFE0E0" :
               (!isBooked && e.stagnant !== null && e.stagnant > 14) ? COLOR.alert :
               (!isBooked && e.stagnant !== null && e.stagnant > 7) ? COLOR.warn :
               COLOR.bgRow;
    return new Array(cols).fill(bg);
  });

  if (dataRows.length) {
    sheet.getRange(3, 1, dataRows.length, cols).setValues(dataRows);
    sheet.getRange(3, 1, dataRows.length, cols).setBackgrounds(dataColors);
    _tableData(sheet, 3, 1, dataRows.length, cols, { keepBg: true });
  }

  // 列幅: #, ID, 姓, 名, セイ, メイ, 学校名, 経路, 現在の選考段階, 選考状況, エントリー日, 経過日数, 次回選考種別, 次回予約日, 直近の評価, 直近フェーズ, 直近活動日, 停滞日数, リスク [+ 離脱種別, 離脱フェーズ, 離脱日]
  const widths = [40, 70, 60, 60, 80, 80, 200, 110, 160, 80, 100, 80, 130, 100, 80, 130, 100, 80, 200]
    .concat(hasExit ? [80, 160, 100] : []);
  widths.forEach((w, i) => sheet.setColumnWidth(i + 1, w));
  // 2行目（ヘッダ）まで固定 + F列（メイまで）を固定 → 学生氏名が常に見える状態に
  sheet.setFrozenRows(2);
  sheet.setFrozenColumns(6);
  sheet.setHiddenGridlines(true);
}

// ─────────────────────────────────────────
// §7  ルールベース 示唆生成
// ─────────────────────────────────────────

// 全体サマリーから「強み・警戒・推奨・リスク」の4枠を生成
function generateOverviewInsights(records, phases, targets, targetsCh) {
  const now = new Date();
  const currentYM = monthKey(now);
  const prevYM = monthKey(new Date(now.getFullYear(), now.getMonth() - 1, 1));

  const fStats = aggregateFunnelMonthly(records, phases);
  const cStats = aggregateChannelMonthly(records);
  const atr = aggregateAttrition(records, phases);
  const schoolStats = aggregateBySchool(records, phases);
  const landing = aggregateLanding(records, phases, targets);

  const mainPhases = phases.filter(p => p.group === "main");
  const insights = [];

  // 🎯 最大の強み: 達成率が最も高い当月フェーズ + 評価
  const phasePerf = mainPhases.map(p => {
    const act = fStats[p.key]?.[currentYM] || 0;
    const tgt = targets[p.key]?.[currentYM] || 0;
    const prev = fStats[p.key]?.[prevYM] || 0;
    const rate = tgt ? act / tgt : null;
    return { label: p.label, act, tgt, rate, prev };
  }).filter(p => p.tgt > 0);
  const bestPhase = phasePerf.sort((a, b) => (b.rate || 0) - (a.rate || 0))[0];
  if (bestPhase && bestPhase.rate !== null) {
    const delta = bestPhase.act - bestPhase.prev;
    const trend = delta > 0 ? `（前月比 +${delta}名）` : delta < 0 ? `（前月比 ${delta}名）` : "";
    insights.push({
      type: "strength",
      icon: "🎯",
      title: "最大の強み",
      text: `${bestPhase.label}の当月達成率 ${Math.round(bestPhase.rate * 100)}%（${bestPhase.act}/${bestPhase.tgt}名）${trend}`,
    });
  }

  // ⚠️ 警戒ポイント: 達成率最低 + 実績ゼロチャネル数
  const worstPhase = phasePerf.sort((a, b) => (a.rate || 99) - (b.rate || 99))[0];
  const zeroChannels = Object.entries(cStats).filter(([, s]) => (s[currentYM] || 0) === 0).map(([ch]) => ch);
  const zeroSection = zeroChannels.length >= 3 ? `。チャネル ${zeroChannels.length}社で実績ゼロ` : "";
  if (worstPhase && worstPhase.rate !== null && worstPhase.rate < 0.7) {
    insights.push({
      type: "alert",
      icon: "⚠️",
      title: "警戒ポイント",
      text: `${worstPhase.label}の当月達成率 ${Math.round(worstPhase.rate * 100)}%（${worstPhase.act}/${worstPhase.tgt}名）${zeroSection}`,
    });
  }

  // 💡 推奨アクション: 達成率Topチャネル + 重点大学
  const chPerf = Object.entries(cStats)
    .map(([ch, s]) => {
      const act = s[currentYM] || 0;
      const tgt = targetsCh[ch]?.[currentYM] || 0;
      return { ch, act, tgt, rate: tgt ? act / tgt : null };
    })
    .filter(x => x.tgt > 0 && x.rate >= 0.7)
    .sort((a, b) => b.rate - a.rate);
  const topCh = chPerf[0];
  const acceptKey = phases.find(p => p.label === "内定承諾")?.key;
  const topSchool = Object.entries(schoolStats)
    .filter(([, s]) => s.entry > 0)
    .map(([sch, s]) => ({
      sch, entry: s.entry,
      eff: acceptKey && s.entry ? (s.byPhase[acceptKey] || 0) / s.entry : 0,
    }))
    .sort((a, b) => b.eff - a.eff || b.entry - a.entry)[0];
  const actions = [];
  if (topCh) actions.push(`${topCh.ch}が達成率${Math.round(topCh.rate * 100)}%で健闘→追加投資候補`);
  if (topSchool && topSchool.eff > 0) actions.push(`${topSchool.sch}が効率${Math.round(topSchool.eff * 100)}%でTop→注力大学`);
  if (actions.length) {
    insights.push({
      type: "action",
      icon: "💡",
      title: "推奨アクション",
      text: actions.join("。"),
    });
  }

  // 📉 リスク: 未予約候補者・停滞・着地予想ギャップ
  const unbooked = _countUnbookedActive(records, phases);
  const stagnant = _countStagnant(records, phases, 7);
  const accTarget = acceptKey ? Object.values(targets[acceptKey] || {}).reduce((s, n) => s + n, 0) : 0;
  const gap = accTarget - landing.grandTotal;
  const riskParts = [];
  if (unbooked > 0) riskParts.push(`未予約候補者 ${unbooked}名`);
  if (stagnant > 0) riskParts.push(`停滞7日超 ${stagnant}名`);
  if (gap > 0) riskParts.push(`内定承諾着地予想 ${landing.grandTotal.toFixed(1)}名 vs 目標${accTarget}名（不足${gap.toFixed(1)}名）`);
  if (riskParts.length) {
    insights.push({
      type: "risk",
      icon: "📉",
      title: "リスク",
      text: riskParts.join("／"),
    });
  }

  return insights;
}

function _countUnbookedActive(records, phases) {
  let count = 0;
  records.forEach(rec => {
    if (!_isActiveRecord(rec)) return;
    const idx = phases.findIndex(p => p.label === rec.currentStage);
    if (idx < 0) return;
    // 次の main/pass/reserved フェーズを探す（exit/interview はスキップ）
    let next = null;
    for (let j = idx + 1; j < phases.length; j++) {
      const g = phases[j].group;
      if (g === "main" || g === "pass" || g === "reserved") { next = phases[j]; break; }
    }
    if (next && !rec.arrivals[next.key]) count++;
  });
  return count;
}

function _countStagnant(records, phases, daysThreshold) {
  const now = new Date();
  let count = 0;
  records.forEach(rec => {
    if (!_isActiveRecord(rec)) return;
    // 次回予約が入っている学生は停滞対象外（予約日まで待機しているだけ）
    const idx = phases.findIndex(p => p.label === rec.currentStage);
    const startIdx = idx >= 0 ? idx : 0;
    for (let j = startIdx; j < phases.length; j++) {
      if (phases[j].group === "reserved") {
        if (rec.scheduled[phases[j].key]) return;
        break;
      }
    }
    let last = null;
    phases.forEach(p => {
      const d = rec.arrivals[p.key];
      if (d && (!last || d > last)) last = d;
    });
    if (!last) return;
    const days = Math.floor((now - last) / (24 * 60 * 60 * 1000));
    if (days > daysThreshold) count++;
  });
  return count;
}

// ─────────────────────────────────────────
// §8  レポート（Slack 週次 / 日次 / 月次Docs）
// ─────────────────────────────────────────

function sendSlackMessage(channel, text, blocks) {
  const { token } = getSlackSettings();
  if (!token) { Logger.log("[Slack] Token未設定"); return null; }
  if (!channel) { Logger.log("[Slack] チャンネルID未設定"); return null; }
  const payload = { channel, text: text || " " };
  if (blocks && blocks.length > 0) payload.blocks = blocks;
  const res = UrlFetchApp.fetch("https://slack.com/api/chat.postMessage", {
    method: "post", contentType: "application/json",
    headers: { Authorization: "Bearer " + token },
    payload: JSON.stringify(payload), muteHttpExceptions: true,
  });
  const result = JSON.parse(res.getContentText());
  if (!result.ok) { Logger.log("[Slack Error] " + result.error); try { _writeLog("SLACK_ERR", "channel=" + channel + " error=" + result.error + " detail=" + (result.errors ? JSON.stringify(result.errors) : "")); } catch(e){} }
  return result;
}

// 週次レポート Block Kit 構築
function composeWeeklyBlocks() {
  const cfg = getConfig();
  const company = String(cfg["企業名"] || "RPO").trim();
  const { records, phases } = loadRawRecords();
  const targets = loadTargetsFunnel(phases);
  const targetsCh = loadTargetsChannel();

  const fStats = aggregateFunnelMonthly(records, phases);
  const cStats = aggregateChannelMonthly(records);
  const atr = aggregateAttrition(records, phases);
  const aStats = aggregateActive(records);
  const schoolStats = aggregateBySchool(records, phases);
  const landing = aggregateLanding(records, phases, targets);

  const now = new Date();
  const ym = monthKey(now);
  const weekStart = _startOfWeek(now);
  const ssUrl = SpreadsheetApp.getActiveSpreadsheet().getUrl();

  const blocks = [];
  blocks.push({
    type: "header",
    text: { type: "plain_text", text: `${company} RPO 週次サマリー（${formatDate(weekStart)}週）` },
  });

  // 当月KPI
  const kpiKeys = _pickMainKpiKeys(phases);
  const kpiLines = kpiKeys.map(p => {
    const act = fStats[p.key]?.[ym] || 0;
    const tgt = targets[p.key]?.[ym] || 0;
    const rate = tgt ? Math.round(act / tgt * 100) : null;
    const emoji = rate === null ? "▫️" : rate >= 100 ? "🟢" : rate >= 70 ? "🟡" : "🔴";
    return `${emoji} *${p.label}*: ${act}${tgt ? ` / ${tgt} (${rate}%)` : ""}`;
  });
  blocks.push({ type: "section", text: { type: "mrkdwn", text: `*■ 当月KPI（${ym}）*\n${kpiLines.join("\n")}` }});

  // チャネル別Top5
  const chTop = Object.entries(cStats)
    .map(([ch, s]) => ({ ch, act: s[ym] || 0, tgt: targetsCh[ch]?.[ym] || 0 }))
    .sort((a, b) => b.act - a.act).slice(0, 5);
  const chLines = chTop.map(r => {
    const rate = r.tgt ? Math.round(r.act / r.tgt * 100) : null;
    const emoji = rate === null ? "▫️" : rate >= 100 ? "🟢" : rate >= 70 ? "🟡" : "🔴";
    return `${emoji} ${r.ch}: ${r.act}${r.tgt ? ` / ${r.tgt} (${rate}%)` : ""}`;
  });
  blocks.push({ type: "section", text: { type: "mrkdwn", text: `*■ チャネル別Top5（当月）*\n${chLines.join("\n") || "(データなし)"}` }});

  // 大学別Top3
  const acceptKey = phases.find(p => p.label === "内定承諾")?.key;
  const schTop = Object.entries(schoolStats)
    .filter(([, s]) => s.entry > 0)
    .map(([sch, s]) => ({
      sch, entry: s.entry,
      eff: acceptKey && s.entry ? (s.byPhase[acceptKey] || 0) / s.entry : 0,
    }))
    .sort((a, b) => b.entry - a.entry).slice(0, 3);
  const medals = ["🥇", "🥈", "🥉"];
  const schLines = schTop.map((s, i) => `${medals[i]} ${s.sch}: ${s.entry}名${s.eff ? `（効率${Math.round(s.eff * 100)}%）` : ""}`);
  if (schLines.length) {
    blocks.push({ type: "section", text: { type: "mrkdwn", text: `*■ 大学別Top3（累計エントリー）*\n${schLines.join("\n")}` }});
  }

  // 詳細アラート
  const unbooked = _countUnbookedActive(records, phases);
  const stagnant = _countStagnant(records, phases, 7);
  const alerts = [];
  if (unbooked > 0) alerts.push(`⚠️ 未予約候補者: ${unbooked}名`);
  if (stagnant > 0) alerts.push(`⚠️ 停滞7日超: ${stagnant}名`);
  // 達成率<70%のフェーズ
  phases.filter(p => p.group === "main").forEach(p => {
    const act = fStats[p.key]?.[ym] || 0;
    const tgt = targets[p.key]?.[ym] || 0;
    if (!tgt) return;
    const rate = act / tgt;
    if (rate < 0.7) alerts.push(`🔴 ${p.label}: ${act}/${tgt} (${Math.round(rate * 100)}%)`);
  });
  if (alerts.length) {
    blocks.push({ type: "section", text: { type: "mrkdwn", text: `*■ 詳細アラート*\n${alerts.join("\n")}` }});
  }

  // 採用着地予想
  blocks.push({ type: "section", text: { type: "mrkdwn", text: `*■ 採用着地予想*\n内定承諾期待値: ${landing.grandTotal.toFixed(1)}名（既承諾 ${landing.alreadyAccepted} + アクティブ予測 ${landing.totalExpected.toFixed(1)}）` }});

  // 離脱・承諾
  const sR = atr.summary;
  const breakdown = (sR.failed || sR.noShow || sR.voluntary)
    ? `\n　内訳: 不合格 ${sR.failed || 0} / 不参加 ${sR.noShow || 0} / 辞退 ${sR.voluntary || 0}` : "";
  const atrText = `候補者: ${sR.total}名（選考中 ${sR.active} / 離脱 ${sR.declined} / 内定獲得 ${sR.offered} / 承諾 ${sR.accepted}）`
                + breakdown
                + (sR.total ? `\n離脱率: ${Math.round(sR.declined / sR.total * 100)}%` : "")
                + (sR.offered ? `\n承諾率: ${Math.round(sR.acceptRate * 100)}%` : "");
  blocks.push({ type: "section", text: { type: "mrkdwn", text: `*■ 離脱・承諾*\n${atrText}` }});

  // 自動洞察セクション
  const insights = generateOverviewInsights(records, phases, targets, targetsCh);
  if (insights.length) {
    const insightText = insights.map(ins => `${ins.icon} *${ins.title}*: ${ins.text}`).join("\n\n");
    blocks.push({ type: "section", text: { type: "mrkdwn", text: `*■ 今週の示唆*\n${insightText}` }});
  }

  blocks.push({ type: "divider" });
  blocks.push({
    type: "context",
    elements: [{ type: "mrkdwn", text: `🔗 <${ssUrl}|詳細ダッシュボードへ>　|　自動生成: ${formatDatetime(now)}` }],
  });
  return blocks;
}

function sendWeeklyReport() {
  const { weeklyChannel } = getSlackSettings();
  const blocks = composeWeeklyBlocks();
  return sendSlackMessage(weeklyChannel, `RPO 週次サマリー (${formatDate(new Date())})`, blocks);
}

function previewWeeklyReport() {
  const blocks = composeWeeklyBlocks();
  Logger.log(JSON.stringify(blocks, null, 2));
  SpreadsheetApp.getUi().alert("プレビューはLogger（表示→ログ Cmd+Enter）で確認できます。");
}

// 日次スナップショットレポート
function composeDailyBlocks() {
  const cfg = getConfig();
  const company = String(cfg["企業名"] || "RPO").trim();
  const { records, phases } = loadRawRecords();
  const targets = loadTargetsFunnel(phases);
  const fStats = aggregateFunnelMonthly(records, phases);
  const now = new Date();
  const ym = monthKey(now);
  const ssUrl = SpreadsheetApp.getActiveSpreadsheet().getUrl();

  const blocks = [];
  blocks.push({
    type: "header",
    text: { type: "plain_text", text: `☀️ ${company} RPO 本日スナップショット（${formatDate(now)}）` },
  });

  // 当月累計
  const kpiKeys = _pickMainKpiKeys(phases);
  const kpiLines = kpiKeys.map(p => {
    const act = fStats[p.key]?.[ym] || 0;
    const tgt = targets[p.key]?.[ym] || 0;
    const rate = tgt ? Math.round(act / tgt * 100) : null;
    return `• ${p.label}: ${act}${tgt ? ` / ${tgt} (${rate}%)` : ""}`;
  });
  blocks.push({ type: "section", text: { type: "mrkdwn", text: `*📊 当月累計（${ym}）*\n${kpiLines.join("\n")}` }});

  // 本日のフォーカス
  const unbooked = _countUnbookedActive(records, phases);
  const stagnant = _countStagnant(records, phases, 7);
  const todaysEvents = _countTodayEvents(records, phases);
  const focusLines = [];
  if (unbooked > 0) focusLines.push(`• 未予約候補者: ${unbooked}名`);
  if (stagnant > 0) focusLines.push(`• 停滞7日超: ${stagnant}名`);
  if (todaysEvents > 0) focusLines.push(`• 本日選考予定: ${todaysEvents}件`);
  if (focusLines.length === 0) focusLines.push("• 特記事項なし");
  blocks.push({ type: "section", text: { type: "mrkdwn", text: `*🎯 本日のフォーカス*\n${focusLines.join("\n")}` }});

  blocks.push({ type: "divider" });
  blocks.push({
    type: "context",
    elements: [{ type: "mrkdwn", text: `🔗 <${ssUrl}|ダッシュボードへ>　|　${formatDatetime(now)}` }],
  });
  return blocks;
}

function _countTodayEvents(records, phases) {
  const today = formatDate(new Date());
  let count = 0;
  records.forEach(rec => {
    phases.forEach(p => {
      // exit（不合格・辞退・不参加）は「本日の選考予定」ではないので除外
      if (p.group === "exit") return;
      const d = rec.arrivals[p.key];
      if (d && formatDate(d) === today) count++;
    });
  });
  return count;
}

function sendDailyReport() {
  const settings = getSlackSettings();
  if (!settings.dailyEnabled) { Logger.log("[Daily] 無効化"); return; }
  const blocks = composeDailyBlocks();
  return sendSlackMessage(settings.dailyChannel, `本日のRPOスナップショット`, blocks);
}

function previewDailyReport() {
  const blocks = composeDailyBlocks();
  Logger.log(JSON.stringify(blocks, null, 2));
  SpreadsheetApp.getUi().alert("プレビューはLogger（表示→ログ Cmd+Enter）で確認できます。");
}

// 月次 Google Docs レポート
function generateMonthlyDoc(targetMonth) {
  const docs = getDocsSettings();
  if (!docs.templateId) {
    SpreadsheetApp.getUi().alert("200_設定に「月次レポートテンプレDocsID」が未設定です。");
    return null;
  }
  if (!docs.folderId) {
    SpreadsheetApp.getUi().alert("200_設定に「月次レポート保存先フォルダID」が未設定です。");
    return null;
  }

  const cfg = getConfig();
  const company = String(cfg["企業名"] || "RPO").trim();
  const now = new Date();
  let year, month;
  if (targetMonth && /^\d{4}-\d{1,2}$/.test(targetMonth)) {
    const parts = targetMonth.split("-");
    year = parseInt(parts[0], 10);
    month = parseInt(parts[1], 10);
  } else {
    const prev = new Date(now.getFullYear(), now.getMonth() - 1, 1);
    year = prev.getFullYear();
    month = prev.getMonth() + 1;
  }
  const ym = `${year}-${String(month).padStart(2, "0")}`;

  // テンプレを複製
  const template = DriveApp.getFileById(docs.templateId);
  const folder = DriveApp.getFolderById(docs.folderId);
  const newName = `RPO月次レポート_${company}_${ym}`;
  const copy = template.makeCopy(newName, folder);
  const doc = DocumentApp.openById(copy.getId());
  const body = doc.getBody();

  // 集計
  const { records, phases } = loadRawRecords();
  const targets = loadTargetsFunnel(phases);
  const targetsCh = loadTargetsChannel();
  const fStats = aggregateFunnelMonthly(records, phases);
  const cStats = aggregateChannelMonthly(records);
  const atr = aggregateAttrition(records, phases);
  const schoolStats = aggregateBySchool(records, phases);
  const landing = aggregateLanding(records, phases, targets);

  // 主要KPIテーブル文字列
  const kpiKeys = _pickMainKpiKeys(phases);
  const kpiTbl = kpiKeys.map(p => {
    const act = fStats[p.key]?.[ym] || 0;
    const tgt = targets[p.key]?.[ym] || 0;
    const rate = tgt ? Math.round(act / tgt * 100) + "%" : "-";
    return `・${p.label}: 実績${act} / 目標${tgt || "-"} / 達成率${rate}`;
  }).join("\n");

  // チャネル
  const chTbl = Object.entries(cStats)
    .map(([ch, s]) => ({ ch, act: s[ym] || 0, tgt: targetsCh[ch]?.[ym] || 0 }))
    .sort((a, b) => b.act - a.act).slice(0, 10)
    .map(c => `・${c.ch}: 実績${c.act} / 目標${c.tgt || "-"}`).join("\n");

  // 大学Top10
  const acceptKey = phases.find(p => p.label === "内定承諾")?.key;
  const schTop = Object.entries(schoolStats)
    .filter(([, s]) => s.entry > 0)
    .map(([sch, s]) => ({
      sch, entry: s.entry,
      accepted: acceptKey ? (s.byPhase[acceptKey] || 0) : 0,
      eff: acceptKey && s.entry ? (s.byPhase[acceptKey] || 0) / s.entry : 0,
    }))
    .sort((a, b) => b.entry - a.entry).slice(0, 10);
  const schTbl = schTop.map(s => `・${s.sch}: エントリー${s.entry} / 承諾${s.accepted} / 効率${Math.round(s.eff * 100)}%`).join("\n");

  // 離脱承諾サマリー
  const sR = atr.summary;
  const exitBreak = (sR.failed || sR.noShow || sR.voluntary)
    ? `（不合格${sR.failed || 0}／不参加${sR.noShow || 0}／辞退${sR.voluntary || 0}）` : "";
  const declineTbl = `総候補者: ${sR.total}名／選考中: ${sR.active}名／離脱: ${sR.declined}名${exitBreak}（${sR.total ? Math.round(sR.declined / sR.total * 100) : 0}%）／内定獲得: ${sR.offered}名／承諾: ${sR.accepted}名${sR.offered ? `（${Math.round(sR.acceptRate * 100)}%）` : ""}`;

  // 着地予想
  const landingTbl = `アクティブからの期待値: ${landing.totalExpected.toFixed(1)}名／既承諾: ${landing.alreadyAccepted}名／最終着地予想: ${landing.grandTotal.toFixed(1)}名`;

  // 自動洞察
  const insights = generateOverviewInsights(records, phases, targets, targetsCh);
  const insightTbl = insights.map(ins => `${ins.icon} ${ins.title}: ${ins.text}`).join("\n\n");

  // プレースホルダ置換
  body.replaceText("{{company}}", company);
  body.replaceText("{{month}}", ym);
  body.replaceText("{{generated_at}}", formatDatetime(new Date()));
  body.replaceText("{{kpi_table}}", kpiTbl || "（データなし）");
  body.replaceText("{{channel_table}}", chTbl || "（データなし）");
  body.replaceText("{{school_top10}}", schTbl || "（データなし）");
  body.replaceText("{{decline_summary}}", declineTbl);
  body.replaceText("{{landing_forecast}}", landingTbl);
  body.replaceText("{{insights}}", insightTbl || "（特記事項なし）");

  doc.saveAndClose();

  // Slackに通知
  const settings = getSlackSettings();
  if (settings.monthlyChannel) {
    const url = `https://docs.google.com/document/d/${copy.getId()}/edit`;
    sendSlackMessage(settings.monthlyChannel,
      `📄 ${company} RPO月次レポート（${ym}）生成完了\n${url}`);
  }
  return copy.getUrl();
}

function previewMonthlyDoc() {
  const url = generateMonthlyDoc();
  if (url) SpreadsheetApp.getUi().alert(`月次レポート生成完了\n${url}`);
}

function generatePastMonthlyDoc() {
  const ui = SpreadsheetApp.getUi();
  const res = ui.prompt("月次レポート生成", "対象月をYYYY-MM形式で入力（例: 2026-04）", ui.ButtonSet.OK_CANCEL);
  if (res.getSelectedButton() !== ui.Button.OK) return;
  const ym = res.getResponseText().trim();
  if (!/^\d{4}-\d{1,2}$/.test(ym)) { ui.alert("形式が不正です"); return; }
  const url = generateMonthlyDoc(ym);
  if (url) ui.alert(`生成完了\n${url}`);
}

// ─────────────────────────────────────────
// §9  メニュー & トリガー
// ─────────────────────────────────────────

function onOpen() {
  SpreadsheetApp.getUi().createMenu("RPO")
    .addItem("全体再集計", "rebuildAll")
    .addSeparator()
    .addItem("全体サマリー再生成", "rebuildOverviewOnly")
    .addItem("大学別 再生成", "rebuildSchoolOnly")
    .addItem("エントリー経路別 再生成", "rebuildChannelOnly")
    .addItem("バイネーム 再生成", "rebuildByNameOnly")
    .addItem("📅 説明会日程別 再生成", "rebuildBriefingByDateOnly")
    .addItem("🆕 全体KPI(211) 再生成", "rebuildOverviewAllOnly")
    .addItem("🆕 月別KPI(212) 再生成", "rebuildMonthlyOnly")
    .addSeparator()
    .addItem("ATS入力漏れチェック", "verifyDataIntegrity")
    .addSeparator()
    .addItem("週次レポート プレビュー (旧)", "previewWeeklyReport")
    .addItem("週次レポート 送信 (旧)", "sendWeeklyReport")
    .addItem("📊 週次レポートV2 プレビュー", "previewWeeklyReportV2")
    .addItem("📊 週次レポートV2 送信", "sendWeeklyReportV2")
    .addItem("⚙️ 週次V2 トリガー設定（水9時）", "setWeeklyTriggerV2")
    .addItem("日次レポート プレビュー", "previewDailyReport")
    .addItem("日次レポート 送信", "sendDailyReport")
    .addItem("月次Docsレポート 前月分生成 (旧)", "previewMonthlyDoc")
    .addItem("月次Docsレポート 過去月生成 (旧)", "generatePastMonthlyDoc")
    .addItem("📄 月次レポートV2 前月分生成", "previewMonthlyDocV2")
    .addItem("📄 月次レポートV2 過去月生成", "generatePastMonthlyDocV2")
    .addItem("⚙️ 月次V2 トリガー設定（毎月1日0時）", "setMonthlyTriggerV2")
    .addSeparator()
    .addItem("⚙️ 毎朝9時 再集計トリガー設定", "setDailyRebuildTrigger")
    .addItem("トリガー設定 (旧・一括)", "setAllTriggers")
    .addToUi();
}

// ATS入力漏れチェック: 最終到達フェーズより手前で穴のあるレコードを検出してログに出力
function verifyDataIntegrity() {
  const start = Date.now();
  try {
    const { phases, records } = loadRawRecords();
    if (!records.length) {
      SpreadsheetApp.getUi().alert("学生情報一覧rawにデータがありません");
      return;
    }
    // ファネル順序対象: main / pass / reserved（interview と exit は順序判定から除外）
    const orderedPhases = phases.filter(p =>
      p.group === "main" || p.group === "pass" || p.group === "reserved"
    );
    const issues = [];
    records.forEach(rec => {
      let lastIdx = -1;
      orderedPhases.forEach((p, i) => {
        if (rec.arrivals[p.key]) lastIdx = i;
      });
      if (lastIdx <= 0) return;
      const missing = [];
      for (let i = 0; i < lastIdx; i++) {
        if (!rec.arrivals[orderedPhases[i].key]) {
          missing.push(orderedPhases[i].label);
        }
      }
      if (missing.length > 0) {
        issues.push({
          id: rec.id,
          name: `${rec.lastName} ${rec.firstName}`.trim(),
          school: rec.school,
          lastReached: orderedPhases[lastIdx].label,
          missing,
        });
      }
    });

    // ログ出力
    _writeLog("DATA_INTEGRITY", `チェック開始: 全 ${records.length} 件 / 抜けあり ${issues.length} 件`);
    issues.forEach(it => {
      _writeLog(
        "DATA_INTEGRITY",
        `候補者ID ${it.id} (${it.name} / ${it.school}) — 最終到達=${it.lastReached} / 抜け=[${it.missing.join(", ")}]`
      );
    });
    _writeLog("DATA_INTEGRITY", `完了 (${Math.round((Date.now() - start) / 1000)}秒)`);

    const ui = SpreadsheetApp.getUi();
    if (issues.length === 0) {
      ui.alert(`ATS入力漏れチェック: 問題なし（全 ${records.length} 件・抜けなし）`);
    } else {
      ui.alert(
        `ATS入力漏れチェック\n\n` +
        `全 ${records.length} 件中、過去フェーズの到達日に抜けがあるレコード: ${issues.length} 件\n\n` +
        `詳細は 299_ログ タブを確認してください。`
      );
    }
  } catch (e) {
    _writeLog("ERROR", `verifyDataIntegrity 失敗: ${e.message}`);
    SpreadsheetApp.getUi().alert(`エラー: ${e.message}`);
  }
}

function rebuildAll() {
  const start = Date.now();
  try {
    const { records, phases } = loadRawRecords();
    const targets = loadTargetsFunnel(phases);
    const targetsCh = loadTargetsChannel();
    renderOverview(records, phases, targets, targetsCh);
    renderBySchool(records, phases);
    renderEntryChannel(records, phases, targetsCh);
    renderByName(records, phases);
    try { renderBriefingByDate(records, phases); } catch (e) { _writeLog("WARN", "説明会日程別 失敗: " + e.message); }
    try { renderOverviewAll(records, phases, targets, targetsCh); } catch (e) { _writeLog("WARN", "全体KPI(211) 失敗: " + e.message); }
    try { renderMonthly(records, phases, targets, targetsCh, null); } catch (e) { _writeLog("WARN", "月別KPI(212) 失敗: " + e.message); }
    _writeLog("OK", `件数=${records.length} / フェーズ=${phases.length} / 経過=${(Date.now() - start) / 1000}s`);
  } catch (e) {
    _writeLog("ERR", String(e) + "\n" + (e.stack || ""));
    throw e;
  }
}

function rebuildOverviewOnly() {
  const { records, phases } = loadRawRecords();
  renderOverview(records, phases, loadTargetsFunnel(phases), loadTargetsChannel());
}
function rebuildSchoolOnly() {
  const { records, phases } = loadRawRecords();
  renderBySchool(records, phases);
}
function rebuildChannelOnly() {
  const { records, phases } = loadRawRecords();
  renderEntryChannel(records, phases, loadTargetsChannel());
}
function rebuildByNameOnly() {
  const { records, phases } = loadRawRecords();
  renderByName(records, phases);
}

function setAllTriggers() {
  const settings = getSlackSettings();
  ScriptApp.getProjectTriggers().forEach(t => {
    if (["rebuildAll", "sendWeeklyReport", "sendDailyReport", "generateMonthlyDoc"].includes(t.getHandlerFunction())) {
      ScriptApp.deleteTrigger(t);
    }
  });
  // 毎朝の全体再集計
  const cfg = getConfig();
  const dailyHour = parseInt(cfg["再集計トリガー時刻"] || "9", 10);
  ScriptApp.newTrigger("rebuildAll").timeBased().atHour(dailyHour).everyDays(1).create();

  // 週次レポート
  if (settings.weeklyEnabled) {
    const wdMap = {
      "月曜": ScriptApp.WeekDay.MONDAY, "火曜": ScriptApp.WeekDay.TUESDAY,
      "水曜": ScriptApp.WeekDay.WEDNESDAY, "木曜": ScriptApp.WeekDay.THURSDAY,
      "金曜": ScriptApp.WeekDay.FRIDAY, "土曜": ScriptApp.WeekDay.SATURDAY,
      "日曜": ScriptApp.WeekDay.SUNDAY,
    };
    ScriptApp.newTrigger("sendWeeklyReport").timeBased()
      .onWeekDay(wdMap[settings.weeklyWday] || ScriptApp.WeekDay.MONDAY)
      .atHour(settings.weeklyHour).create();
  }

  // 日次レポート
  if (settings.dailyEnabled) {
    ScriptApp.newTrigger("sendDailyReport").timeBased().atHour(settings.dailyHour).everyDays(1).create();
  }

  // 月次レポート
  if (settings.monthlyEnabled) {
    ScriptApp.newTrigger("generateMonthlyDoc").timeBased().onMonthDay(1).atHour(0).create();
  }

  SpreadsheetApp.getUi().alert(
    `トリガー設定完了:\n` +
    `- 毎日 ${dailyHour}時 → 全体再集計\n` +
    (settings.weeklyEnabled  ? `- 毎週${settings.weeklyWday} ${settings.weeklyHour}時 → 週次Slack\n` : "") +
    (settings.dailyEnabled   ? `- 毎日 ${settings.dailyHour}時 → 日次Slack\n` : "") +
    (settings.monthlyEnabled ? `- 毎月1日 0時 → 月次Docs生成\n` : "")
  );
}

// ─────────────────────────────────────────
// §10  ユーティリティ
// ─────────────────────────────────────────

function parseDate(v) {
  if (!v && v !== 0) return null;
  if (v instanceof Date && !isNaN(v.getTime())) return v;
  const s = String(v).trim();
  if (!s) return null;
  const norm = s.replace(/\//g, "-").replace(/\./g, "-");
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
  const diff = (day === 0 ? -6 : 1 - day);
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

// ─────────────────────────────────────────
// §11  週次レポート V2 (累積アクティブ・予定・前週比・厳選アクション・一言)
// ─────────────────────────────────────────

// 累積アクティブ集計: 各フェーズに到達かつ離脱(exit)していないレコード数
function aggregateCumulativeActive(records, phases) {
  const targetGroups = ["main", "pass", "reserved"];
  const result = {};
  phases.forEach(p => { if (targetGroups.includes(p.group)) result[p.key] = 0; });
  records.forEach(rec => {
    const exited = phases.some(p => p.group === "exit" && rec.arrivals[p.key]);
    if (exited) return;
    phases.forEach(p => {
      if (!targetGroups.includes(p.group)) return;
      if (rec.arrivals[p.key]) result[p.key]++;
    });
  });
  return result;
}

// 今後7日に予約されているイベント数
function aggregateScheduledNext7Days(records, phases, today) {
  const startDay = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  // 参加予定 = 【予約】到達日あり かつ 対応する【参加】到達日なし かつ 未離脱
  // （予約が入っていれば日付を問わず参加予定に含める）
  const pendingForStage = (reserveLabel, partLabel) => {
    const resPhs = phases.filter(p => p.label === reserveLabel);
    const partPhs = phases.filter(p => p.label === partLabel);
    let count = 0;
    records.forEach(rec => {
      if (phases.some(p => p.group === "exit" && rec.arrivals[p.key])) return;
      const hasReserve = resPhs.some(p => rec.arrivals[p.key]);
      const hasPart    = partPhs.some(p => rec.arrivals[p.key]);
      if (hasReserve && !hasPart) count++;
    });
    return count;
  };
  // 新規エントリー: 過去7日のエントリー到達日
  const startPast = new Date(startDay.getTime() - 7 * 86400000);
  const entryPhase = phases.find(p => p.label === "エントリー");
  let newEntry = 0;
  if (entryPhase) {
    records.forEach(rec => {
      const d = rec.arrivals[entryPhase.key];
      if (d instanceof Date && d.getTime() >= startPast.getTime() && d.getTime() <= today.getTime()) newEntry++;
    });
  }
  return {
    newEntry:    newEntry,
    briefing:    pendingForStage("説明選考会【予約】", "説明選考会【参加】"),
    interview1:  pendingForStage("一次面接【予約】", "一次面接【参加】"),
    interview2:  pendingForStage("二次面接【予約】", "二次面接【参加】"),
    interviewF:  pendingForStage("最終選考【予約】", "最終選考【参加】"),
  };
}

// 媒体別 応募数（今週新規=過去7日 / 累計）— 複合経路は各媒体に計上
function aggregateChannelBreakdown(records, phases, today) {
  const startPast = new Date(today.getFullYear(), today.getMonth(), today.getDate()).getTime() - 7 * 86400000;
  const todayMs = today.getTime();
  const entryPhase = phases.find(p => p.label === "エントリー");
  const week = {}, total = {};
  let totalEntries = 0;
  if (!entryPhase) return { week, total, totalEntries };
  records.forEach(rec => {
    const d = rec.arrivals[entryPhase.key];
    if (!(d instanceof Date)) return;
    totalEntries++;
    const media = (rec.channels && rec.channels.length) ? rec.channels : [rec.channel || "(不明)"];
    const isThisWeek = d.getTime() >= startPast && d.getTime() <= todayMs;
    media.forEach(m => {
      total[m] = (total[m] || 0) + 1;
      if (isThisWeek) week[m] = (week[m] || 0) + 1;
    });
  });
  return { week, total, totalEntries };
}

// 厳選アクション抽出: 参加済みで合否未入力 (3日以上経過) + 内定承諾期限近い
function extractCriticalActions(records, phases, today, limit) {
  limit = limit || 8;
  const todayMs = new Date(today.getFullYear(), today.getMonth(), today.getDate()).getTime();
  const mainPhases = phases.filter(p => p.group === "main" && p.label !== "エントリー");
  const actions = [];
  records.forEach(rec => {
    if (phases.some(p => p.group === "exit" && rec.arrivals[p.key])) return;
    mainPhases.forEach(mp => {
      const partDate = rec.arrivals[mp.key];
      if (!(partDate instanceof Date)) return;
      const base = mp.label.replace(/【参加】.*$/, "");
      const passP = phases.find(p => p.label === `${base}【合格】`);
      const failP = phases.find(p => p.label === `${base}【不合格】`);
      const declP = phases.find(p => p.label === `${base}【辞退】`);
      const judged = (passP && rec.arrivals[passP.key]) || (failP && rec.arrivals[failP.key]) || (declP && rec.arrivals[declP.key]);
      if (judged) return;
      const days = Math.floor((todayMs - partDate.getTime()) / 86400000);
      if (days < 3) return;
      actions.push({
        urgency: days >= 7 ? "🔴" : "🟡",
        days,
        type: `${base}合否未入力`,
        name: `${rec.lastName || ""}${rec.firstName || ""}`.trim() || `ID:${rec.id || ""}`,
        school: rec.school || "",
      });
    });
  });
  // 内定到達してまだ承諾未確認 = オファー面談前候補
  const offerP = phases.find(p => p.label === "内定");
  const acceptP = phases.find(p => p.label === "内定承諾");
  if (offerP) {
    records.forEach(rec => {
      if (phases.some(p => p.group === "exit" && rec.arrivals[p.key])) return;
      const offerD = rec.arrivals[offerP.key];
      if (!(offerD instanceof Date)) return;
      if (acceptP && rec.arrivals[acceptP.key]) return;
      const days = Math.floor((todayMs - offerD.getTime()) / 86400000);
      actions.push({
        urgency: days >= 7 ? "🔴" : "🟡",
        days,
        type: "内定承諾待ち",
        name: `${rec.lastName || ""}${rec.firstName || ""}`.trim() || `ID:${rec.id || ""}`,
        school: rec.school || "",
      });
    });
  }
  actions.sort((a, b) => {
    if (a.urgency !== b.urgency) return a.urgency === "🔴" ? -1 : 1;
    return b.days - a.days;
  });
  return actions.slice(0, limit);
}

// 前週スナップショット
function loadPrevWeekSnapshot() {
  const raw = PropertiesService.getScriptProperties().getProperty("WEEKLY_SNAPSHOT");
  if (!raw) return null;
  try { return JSON.parse(raw); } catch (e) { return null; }
}
function saveWeekSnapshot(cumulative) {
  PropertiesService.getScriptProperties().setProperty(
    "WEEKLY_SNAPSHOT",
    JSON.stringify({ ts: new Date().toISOString(), counts: cumulative })
  );
}

// Gemini で一言コメント (最大80字)
function generateGeminiOneLiner(summary) {
  const apiKey = PropertiesService.getScriptProperties().getProperty("GEMINI_API_KEY");
  if (!apiKey) return "";
  const endpoint = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${apiKey}`;
  const payload = {
    systemInstruction: { parts: [{ text: "採用週次データを見て1〜2行で要点をコメントする。「コンサルタントとして」などの前置きや「〜と考えられます」のような曖昧表現は禁止。事実と推奨を端的に。" }] },
    contents: [{ role: "user", parts: [{ text: `以下の週次データに対してコメントしてください(80字以内・1〜2行):\n\n${summary}` }] }],
    generationConfig: { temperature: 0.3, maxOutputTokens: 200 },
  };
  try {
    const res = UrlFetchApp.fetch(endpoint, {
      method: "post", contentType: "application/json",
      payload: JSON.stringify(payload), muteHttpExceptions: true,
    });
    if (res.getResponseCode() !== 200) return "";
    const json = JSON.parse(res.getContentText());
    return (json.candidates?.[0]?.content?.parts?.[0]?.text || "").trim();
  } catch (e) { Logger.log("oneLiner: " + e.message); return ""; }
}

// 週次レポート V2: ユーザー仕様のSlack Block
function composeWeeklyBlocksV2() {
  const cfg = getConfig();
  const company = String(cfg["企業名"] || "RPO").trim();
  const { records, phases } = loadRawRecords();
  const today = new Date();
  const ssUrl = SpreadsheetApp.getActiveSpreadsheet().getUrl();

  const cumActive = aggregateCumulativeActive(records, phases);
  const prev = loadPrevWeekSnapshot();
  // 前週比を矢印付きで表示（⬆増加 / ⬇減少 / →変化なし）
  const arrow = (key) => {
    if (!prev || !prev.counts) return "";
    const d = (cumActive[key] || 0) - (prev.counts[key] || 0);
    if (d === 0) return " `→±0`";
    return d > 0 ? ` \`⬆+${d}\`` : ` \`⬇${d}\``;
  };

  const sched = aggregateScheduledNext7Days(records, phases, today);
  const actions = extractCriticalActions(records, phases, today, 10);
  const weekEnd = new Date(today.getTime() + 6 * 86400000);
  const periodLabel = `${formatDate(today)} 〜 ${formatDate(weekEnd)}`;

  const blocks = [];
  blocks.push({ type: "header", text: { type: "plain_text", text: `${company} 採用週次レポート (${periodLabel})` } });

  // 今週の予定
  const schedLines = [
    `🆕 *新規エントリー*: ${sched.newEntry}名 (過去7日)`,
    `🎤 *説明会参加予定*: ${sched.briefing}名`,
    `📋 *1次面接予定*: ${sched.interview1}名`,
    `📋 *2次面接予定*: ${sched.interview2}名`,
    `🎯 *最終面接予定*: ${sched.interviewF}名`,
  ];
  blocks.push({ type: "section", text: { type: "mrkdwn", text: `*■ 今週の予定・活動*\n${schedLines.join("\n")}` } });

  // 媒体別 応募数（今週新規 / 累計）— 媒体ごとに細かく
  const chBreak = aggregateChannelBreakdown(records, phases, today);
  const chKeys = Object.keys(chBreak.total).sort((a, b) => chBreak.total[b] - chBreak.total[a]);
  if (chKeys.length) {
    const denom = chBreak.totalEntries || 1;
    const chLines = chKeys.map(ch => {
      const w = chBreak.week[ch] || 0;
      const t = chBreak.total[ch] || 0;
      const pct = (t / denom * 100).toFixed(1);
      return `• *${ch}*　今週 ${w}名 ／ 累計 ${t}名 (${pct}%)`;
    });
    blocks.push({ type: "section", text: { type: "mrkdwn", text: `*■ 媒体別 応募数（今週新規／累計）*\n${chLines.join("\n")}\n_※複合経路は各媒体に計上。構成比は全応募${denom}名に対する割合_` } });
  }

  // 現在ステータス（累積・前週比）— 太字フェーズ名＋人数＋矢印
  const statusOrder = phases.filter(p => p.group === "main" || p.group === "pass" || p.group === "reserved");
  const statusLines = statusOrder.map(p => {
    const cnt = cumActive[p.key] || 0;
    return `• *${p.label}*　${cnt}名${arrow(p.key)}`;
  });
  blocks.push({ type: "section", text: { type: "mrkdwn", text: `*■ 現在のステータス（累積・前週比）*\n${statusLines.join("\n")}\n_※離脱（不参加/不合格/辞退）を除いた現在アクティブ数_` } });

  // アクション
  if (actions.length > 0) {
    const actLines = actions.map(a => `${a.urgency} ${a.type} — ${a.name}${a.school ? `(${a.school})` : ""} 〔${a.days}日経過〕`);
    blocks.push({ type: "section", text: { type: "mrkdwn", text: `*■ 今週のアクション一覧（要対応）*\n${actLines.join("\n")}` } });
  }

  // Good/More
  try {
    const targets = loadTargetsFunnel(phases);
    const targetsCh = loadTargetsChannel();
    const insights = generateOverviewInsights(records, phases, targets, targetsCh);
    const goods = insights.filter(i => i.icon === "✅").slice(0, 3).map(i => `✅ ${i.title}: ${i.text}`).join("\n");
    const mores = insights.filter(i => i.icon === "⚠️" || i.icon === "🔴").slice(0, 3).map(i => `⚠️ ${i.title}: ${i.text}`).join("\n");
    if (goods) blocks.push({ type: "section", text: { type: "mrkdwn", text: `*■ 今週のGood*\n${goods}` } });
    if (mores) blocks.push({ type: "section", text: { type: "mrkdwn", text: `*■ 今週のMore*\n${mores}` } });
  } catch (e) { Logger.log("good/more skip: " + e.message); }

  // 一言
  const summarySrc = [
    `新規エントリー: ${sched.newEntry}名 / 今週予定 説明会${sched.briefing} 1次${sched.interview1} 2次${sched.interview2} 最終${sched.interviewF}`,
    `現在ステータス: ` + statusOrder.slice(0, 8).map(p => `${p.label}=${cumActive[p.key]||0}`).join(", "),
    `要対応: ${actions.length}名`,
  ].join("\n");
  const oneLiner = generateGeminiOneLiner(summarySrc);
  if (oneLiner) blocks.push({ type: "section", text: { type: "mrkdwn", text: `*■ 一言*\n${oneLiner}` } });

  blocks.push({ type: "divider" });
  blocks.push({ type: "context", elements: [{ type: "mrkdwn", text: `🔗 <${ssUrl}|詳細ダッシュボード>　|　${formatDatetime(today)}` }] });

  // 次回用に今回のスナップショット保存
  saveWeekSnapshot(cumActive);

  return blocks;
}

function sendWeeklyReportV2() {
  try {
    const { weeklyChannel } = getSlackSettings();
    if (!weeklyChannel) throw new Error("Slack 週次チャンネルID が設定されていません (200_設定)");
    const blocks = composeWeeklyBlocksV2();
    const res = sendSlackMessage(weeklyChannel, `採用週次レポート (${formatDate(new Date())})`, blocks);
    _writeLog("WEEKLY_OK", "送信結果 ok=" + (res && res.ok) + (res && !res.ok ? " err=" + res.error : ""));
    return res;
  } catch (e) {
    _writeLog("WEEKLY_ERR", e.message + " @ " + (e.stack||"").substring(0,250));
    throw e;
  }
}

function previewWeeklyReportV2() {
  const blocks = composeWeeklyBlocksV2();
  Logger.log(JSON.stringify(blocks, null, 2));
  SpreadsheetApp.getUi().alert("週次V2プレビュー: 表示→ログ で確認");
}

// ─────────────────────────────────────────
// §12  説明会日程別タブ (250_説明会日程別)
// ─────────────────────────────────────────

function aggregateBriefingByDate(records, phases) {
  const reservP = phases.find(p => p.label === "説明選考会【予約】");
  const partP   = phases.find(p => p.label === "説明選考会【参加】");
  const noShowP = phases.find(p => p.label === "説明選考会【不参加】");
  const passP   = phases.find(p => p.label === "説明選考会【合格】");
  const i1ResP  = phases.find(p => p.label === "一次面接【予約】");
  const i1PartP = phases.find(p => p.label === "一次面接【参加】");
  const i1PassP = phases.find(p => p.label === "一次面接【合格】");
  const offerP  = phases.find(p => p.label === "内定");
  const acceptP = phases.find(p => p.label === "内定承諾");
  if (!reservP) return {};

  // 「今日」0時。開催日がこれより後の回は未開催（開催予定）として分離するための基準
  const now = new Date();
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());

  const buckets = {};   // dateKey -> stats
  records.forEach(rec => {
    // ★ 開催日は「説明選考会【予約】」列の生値（rec.scheduled）= 黄色列。到達日(予約操作日)ではない
    //    予約がない参加者は「説明選考会【参加】」列の開催日でフォールバック
    let d = rec.scheduled[reservP.key];
    if (!(d instanceof Date) && partP) d = rec.scheduled[partP.key];
    if (!(d instanceof Date)) return;
    const key = `${d.getFullYear()}/${String(d.getMonth()+1).padStart(2,"0")}/${String(d.getDate()).padStart(2,"0")}`;
    if (!buckets[key]) buckets[key] = {
      date: d,
      // 開催日が今日より後なら未開催（開催予定）。参加率・合計の対象外にする
      isFuture: d.getTime() > todayStart.getTime(),
      reserved: 0, participated: 0, noShow: 0,
      passed: 0, i1Reserved: 0, i1Participated: 0, i1Passed: 0,
      offered: 0, accepted: 0,
    };
    // ★ 各フェーズ「到達」判定: 生値(scheduled=開催日列) または 到達日(arrivals) のどちらかが入っていれば到達
    //    （データ入力が列によってバラつくため両対応。説明会合格などのカウント漏れを防ぐ）
    const reached = (p) => !!(p && (rec.arrivals[p.key] || rec.scheduled[p.key]));
    const b = buckets[key];
    b.reserved++;
    if (reached(partP)) b.participated++;
    // ★ 不参加は「説明選考会【不参加】」列の明示フラグで判定（未開催・未入力を不参加に含めない）
    if (reached(noShowP)) b.noShow++;
    // 後段フェーズは参加の有無に関係なく独立カウント（合格・1次・内定の取りこぼし防止）
    if (reached(passP))    b.passed++;
    if (reached(i1ResP))   b.i1Reserved++;
    if (reached(i1PartP))  b.i1Participated++;
    if (reached(i1PassP))  b.i1Passed++;
    if (reached(offerP))   b.offered++;
    if (reached(acceptP))  b.accepted++;
  });
  return buckets;
}

function renderBriefingByDate(records, phases) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheetName = "250_説明会日程別";
  let sheet = ss.getSheetByName(sheetName);
  if (!sheet) sheet = ss.insertSheet(sheetName);
  _clearSheet(sheet);
  sheet.setHiddenGridlines(true);

  const stats = aggregateBriefingByDate(records, phases);
  const allDates = Object.keys(stats).sort();
  if (!allDates.length) {
    sheet.getRange(1,1).setValue("説明選考会【予約】の到達日が記録されたレコードがありません").setFontStyle("italic");
    return;
  }

  // 開催済み / 未開催（開催予定）で分割
  const heldDates   = allDates.filter(d => !stats[d].isFuture);
  const futureDates = allDates.filter(d =>  stats[d].isFuture);

  // タイトル
  _bannerTitle(sheet, 1, 12, "■ 250_説明会日程別 歩留まり", `生成: ${formatDatetime(new Date())} / 開催済みのみ集計・開催予定は別表`);

  // ── 開催済み 本表 ──
  const headers = ["日付", "予約", "参加", "不参加", "参加率", "説明会合格", "1次予約", "1次参加", "1次合格", "内定", "承諾", "内定率"];
  const headerRow = 3;
  sheet.getRange(headerRow, 1, 1, headers.length).setValues([headers]);
  _tableHeader(sheet, headerRow, 1, headers.length);

  const rows = heldDates.map(d => {
    const s = stats[d];
    const partRate = s.reserved ? (s.participated / s.reserved * 100).toFixed(1) + "%" : "-";
    const offerRate = s.reserved ? (s.offered / s.reserved * 100).toFixed(1) + "%" : "-";
    return [d, s.reserved, s.participated, s.noShow, partRate, s.passed, s.i1Reserved, s.i1Participated, s.i1Passed, s.offered, s.accepted, offerRate];
  });
  // 合計行（開催済みのみ）
  const totals = heldDates.reduce((acc, d) => {
    const s = stats[d];
    acc.reserved += s.reserved;
    acc.participated += s.participated;
    acc.noShow += s.noShow;
    acc.passed += s.passed;
    acc.i1Reserved += s.i1Reserved;
    acc.i1Participated += s.i1Participated;
    acc.i1Passed += s.i1Passed;
    acc.offered += s.offered;
    acc.accepted += s.accepted;
    return acc;
  }, { reserved: 0, participated: 0, noShow: 0, passed: 0, i1Reserved: 0, i1Participated: 0, i1Passed: 0, offered: 0, accepted: 0 });
  const totalPartRate = totals.reserved ? (totals.participated / totals.reserved * 100).toFixed(1) + "%" : "-";
  const totalOfferRate = totals.reserved ? (totals.offered / totals.reserved * 100).toFixed(1) + "%" : "-";
  rows.push(["合計", totals.reserved, totals.participated, totals.noShow, totalPartRate, totals.passed, totals.i1Reserved, totals.i1Participated, totals.i1Passed, totals.offered, totals.accepted, totalOfferRate]);

  const dataRow = headerRow + 1;
  sheet.getRange(dataRow, 1, rows.length, headers.length).setValues(rows);
  _tableData(sheet, dataRow, 1, rows.length, headers.length);
  for (let r = 0; r < rows.length - 1; r++) {
    if (r % 2 === 1) sheet.getRange(dataRow + r, 1, 1, headers.length).setBackground(COLOR.bgRowAlt);
  }
  sheet.getRange(dataRow + rows.length - 1, 1, 1, headers.length)
    .setBackground(COLOR.totalBg).setFontWeight("bold");

  // ── 開催予定 別表（予約数のみ・参加率は出さない） ──
  if (futureDates.length) {
    let fr = dataRow + rows.length + 2;   // 本表の下に1行空けて配置
    sheet.getRange(fr, 1, 1, 2).merge().setValue("■ 開催予定（予約数のみ・未開催）")
      .setBackground(COLOR.totalBg).setFontWeight("bold").setFontSize(11)
      .setHorizontalAlignment("left").setFontFamily(FONT);
    fr++;
    const fHeaders = ["開催日", "予約"];
    sheet.getRange(fr, 1, 1, fHeaders.length).setValues([fHeaders]);
    _tableHeader(sheet, fr, 1, fHeaders.length);
    fr++;
    const fRows = futureDates.map(d => [d, stats[d].reserved]);
    const fTotal = futureDates.reduce((s, d) => s + stats[d].reserved, 0);
    fRows.push(["合計", fTotal]);
    sheet.getRange(fr, 1, fRows.length, fHeaders.length).setValues(fRows);
    _tableData(sheet, fr, 1, fRows.length, fHeaders.length);
    for (let r = 0; r < fRows.length - 1; r++) {
      if (r % 2 === 1) sheet.getRange(fr + r, 1, 1, fHeaders.length).setBackground(COLOR.bgRowAlt);
    }
    sheet.getRange(fr + fRows.length - 1, 1, 1, fHeaders.length)
      .setBackground(COLOR.totalBg).setFontWeight("bold");
  }

  // 列幅
  sheet.setColumnWidth(1, 110);
  for (let c = 2; c <= headers.length; c++) sheet.setColumnWidth(c, 80);
  sheet.setFrozenRows(headerRow);
}

function rebuildBriefingByDateOnly() {
  const { records, phases } = loadRawRecords();
  renderBriefingByDate(records, phases);
}

// ─────────────────────────────────────────
// §13  (廃止) 累積ファネル — 全体サマリーに同機能があるため未使用
//      aggregateCumulativeActive は週次レポートで使用中のため残す
// ─────────────────────────────────────────

function _UNUSED_renderCumulativeFunnel(records, phases) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheetName = "211_累積ファネル";
  let sheet = ss.getSheetByName(sheetName);
  if (!sheet) sheet = ss.insertSheet(sheetName);
  _clearSheet(sheet);
  sheet.setHiddenGridlines(true);

  const cumActive = aggregateCumulativeActive(records, phases);
  const prev = loadPrevWeekSnapshot();

  _bannerTitle(sheet, 1, 5, "■ 211_累積ファネル（離脱除く・現在アクティブ）", `生成: ${formatDatetime(new Date())} / 各フェーズ以降にアクティブな候補者数`);

  // ヘッダ
  const headers = ["フェーズ", "累積アクティブ人数", "前週比", "通過率", "備考"];
  const headerRow = 3;
  sheet.getRange(headerRow, 1, 1, headers.length).setValues([headers])
    .setBackground(COLOR.bgDark).setFontColor(COLOR.fgWhite).setFontWeight("bold")
    .setHorizontalAlignment("center");

  // データ行
  const order = phases.filter(p => p.group === "main" || p.group === "pass" || p.group === "reserved");
  const entryKey = phases.find(p => p.label === "エントリー")?.key;
  const baseCount = entryKey ? (cumActive[entryKey] || 0) : 0;
  const rows = order.map(p => {
    const cnt = cumActive[p.key] || 0;
    const prevCnt = (prev?.counts || {})[p.key] || 0;
    const diff = cnt - prevCnt;
    const diffStr = (!prev || !prev.counts) ? "-" : (diff === 0 ? "±0" : (diff > 0 ? `+${diff}` : `${diff}`));
    const rate = baseCount > 0 ? (cnt / baseCount * 100).toFixed(1) + "%" : "-";
    return [p.label, cnt, diffStr, rate, ""];
  });
  const dataRow = headerRow + 1;
  sheet.getRange(dataRow, 1, rows.length, headers.length).setValues(rows);

  // 交互背景
  for (let r = 0; r < rows.length; r++) {
    const bg = r % 2 === 0 ? COLOR.bgRow : COLOR.bgRowAlt;
    sheet.getRange(dataRow + r, 1, 1, headers.length).setBackground(bg);
  }

  sheet.setColumnWidth(1, 230);
  sheet.setColumnWidth(2, 130);
  sheet.setColumnWidth(3, 100);
  sheet.setColumnWidth(4, 100);
  sheet.setColumnWidth(5, 240);
  sheet.getRange(headerRow, 1, rows.length + 1, headers.length).setBorder(true,true,true,true,true,true);
  sheet.setFrozenRows(headerRow);
}

function _UNUSED_rebuildCumulativeFunnelOnly() {
  const { records, phases } = loadRawRecords();
  _UNUSED_renderCumulativeFunnel(records, phases);
}

// ─────────────────────────────────────────
// §14  月次Docsレポート V2 (ハイブリッド: 単月詳細 + 前月比 + 6ヶ月トレンド)
// ─────────────────────────────────────────

// その月の主要KPI数値を集計
function _monthlyKpiSnapshot(records, phases, year, month) {
  const ym = `${year}-${String(month).padStart(2, "0")}`;
  const fStats = aggregateFunnelMonthly(records, phases);
  const entryP = phases.find(p => p.label === "エントリー");
  const briefP = phases.find(p => p.label === "説明選考会【参加】");
  const i1P    = phases.find(p => p.label === "一次面接【参加】");
  const finalP = phases.find(p => p.label === "最終選考【参加】");
  const offerP = phases.find(p => p.label === "内定");
  const acceptP = phases.find(p => p.label === "内定承諾");
  return {
    ym,
    entry:    entryP ? (fStats[entryP.key]?.[ym] || 0) : 0,
    briefing: briefP ? (fStats[briefP.key]?.[ym] || 0) : 0,
    interview1: i1P ? (fStats[i1P.key]?.[ym] || 0) : 0,
    final:    finalP ? (fStats[finalP.key]?.[ym] || 0) : 0,
    offer:    offerP ? (fStats[offerP.key]?.[ym] || 0) : 0,
    accept:   acceptP ? (fStats[acceptP.key]?.[ym] || 0) : 0,
  };
}

// 過去Nヶ月のエントリー数推移 (QuickChart用)
function _monthlyTrendData(records, phases, year, month, monthsBack) {
  monthsBack = monthsBack || 6;
  const fStats = aggregateFunnelMonthly(records, phases);
  const labels = [], entries = [], offers = [];
  const entryP = phases.find(p => p.label === "エントリー");
  const offerP = phases.find(p => p.label === "内定");
  for (let i = monthsBack - 1; i >= 0; i--) {
    const d = new Date(year, month - 1 - i, 1);
    const ym = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}`;
    labels.push(`${d.getMonth()+1}月`);
    entries.push(entryP ? (fStats[entryP.key]?.[ym] || 0) : 0);
    offers.push(offerP ? (fStats[offerP.key]?.[ym] || 0) : 0);
  }
  return { labels, entries, offers };
}

function _buildTrendChartBlob(trend) {
  const config = {
    type: "line",
    data: {
      labels: trend.labels,
      datasets: [
        { label: "エントリー", data: trend.entries, borderColor: "#4285F4", backgroundColor: "rgba(66,133,244,0.1)", tension: 0.3 },
        { label: "内定",       data: trend.offers,  borderColor: "#EA4335", backgroundColor: "rgba(234,67,53,0.1)",  tension: 0.3 },
      ],
    },
    options: {
      plugins: {
        title: { display: true, text: "過去6ヶ月 月別トレンド", font: { size: 16, weight: "bold" }, align: "start" },
        legend: { position: "top" },
      },
      scales: { y: { beginAtZero: true } },
    },
  };
  const url = "https://quickchart.io/chart?width=720&height=360&format=png&c=" + encodeURIComponent(JSON.stringify(config));
  try {
    const res = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
    if (res.getResponseCode() !== 200) return null;
    return res.getBlob().setName("trend.png");
  } catch (e) { return null; }
}

function _docAppendKpiBlock(body, kpis) {
  // 1行目: ラベル / 2行目: 数値 / 3行目: 前月比
  const labels = kpis.map(k => k.label);
  const values = kpis.map(k => String(k.value));
  const diffs  = kpis.map(k => k.diff);
  const table = body.appendTable([labels, values, diffs]);
  try {
    // 列幅自動
    const usable = 480;
    const w = Math.floor(usable / kpis.length);
    for (let c = 0; c < kpis.length; c++) table.setColumnWidth(c, w);
  } catch (e) {}
  // ラベル行
  for (let c = 0; c < kpis.length; c++) {
    try {
      const cell = table.getRow(0).getCell(c);
      cell.setBackgroundColor("#37474F");
      const t = cell.getChild(0).asParagraph();
      t.editAsText().setForegroundColor("#FFFFFF").setBold(true);
      t.setAlignment(DocumentApp.HorizontalAlignment.CENTER);
    } catch (e) {}
  }
  // 数値行
  for (let c = 0; c < kpis.length; c++) {
    try {
      const cell = table.getRow(1).getCell(c);
      cell.setBackgroundColor("#ECEFF1");
      const t = cell.getChild(0).asParagraph();
      t.editAsText().setBold(true);
      t.setAlignment(DocumentApp.HorizontalAlignment.CENTER);
    } catch (e) {}
  }
  // 前月比行
  for (let c = 0; c < kpis.length; c++) {
    try {
      const cell = table.getRow(2).getCell(c);
      cell.setBackgroundColor("#F5F5F5");
      const t = cell.getChild(0).asParagraph();
      const txt = t.editAsText();
      txt.setForegroundColor("#666666").setFontSize(9);
      t.setAlignment(DocumentApp.HorizontalAlignment.CENTER);
    } catch (e) {}
  }
}

function _docAppendCallout(body, type, lines) {
  const bg = type === "good" ? "#C8E6C9" : type === "more" ? "#FFF59D" : "#ECEFF1";
  const titleStr = type === "good" ? "Good" : type === "more" ? "More" : "Note";
  const text = `${titleStr}\n` + lines.map(l => `・${l}`).join("\n");
  const table = body.appendTable([[text]]);
  try {
    const cell = table.getCell(0, 0);
    cell.setBackgroundColor(bg);
    const para = cell.getChild(0);
    const t = para.editAsText();
    const nl = t.getText().indexOf("\n");
    if (nl > 0) t.setBold(0, nl - 1, true);
  } catch (e) {}
}

function _appendDocTable(body, headers, rows) {
  if (!headers.length) return;
  const all = [headers].concat(rows);
  const table = body.appendTable(all);
  try {
    const usable = 480;
    const firstW = headers.length >= 5 ? 130 : 160;
    const restW = Math.floor((usable - firstW) / Math.max(1, headers.length - 1));
    table.setColumnWidth(0, firstW);
    for (let c = 1; c < headers.length; c++) table.setColumnWidth(c, restW);
  } catch (e) {}
  // フォント・パディング
  for (let r = 0; r < table.getNumRows(); r++) {
    const row = table.getRow(r);
    for (let c = 0; c < row.getNumCells(); c++) {
      try {
        const cell = row.getCell(c);
        cell.setPaddingTop(2).setPaddingBottom(2).setPaddingLeft(6).setPaddingRight(6);
        cell.editAsText().setFontSize(9);
      } catch (e) {}
    }
  }
  // ヘッダ
  for (let c = 0; c < headers.length; c++) {
    try {
      const cell = table.getRow(0).getCell(c);
      cell.setBackgroundColor("#37474F");
      cell.editAsText().setForegroundColor("#FFFFFF").setBold(true);
    } catch (e) {}
  }
  // データ行交互背景
  for (let r = 1; r < table.getNumRows(); r++) {
    try {
      const bg = r % 2 === 0 ? "#F5F5F5" : "#FFFFFF";
      const row = table.getRow(r);
      for (let c = 0; c < row.getNumCells(); c++) row.getCell(c).setBackgroundColor(bg);
    } catch (e) {}
  }
}

function _diffLabel(curr, prev) {
  if (prev === 0 && curr === 0) return "±0";
  if (prev === 0) return `+${curr} (新規)`;
  const d = curr - prev;
  const pct = ((curr - prev) / prev * 100).toFixed(0);
  return d === 0 ? "±0" : `${d > 0 ? "+" : ""}${d} (${d > 0 ? "+" : ""}${pct}%)`;
}

// 目標差分ラベル: 実績/目標 → "+2 (110%)" / "-3 (70%)" / 目標なしは "-"
function _targetDiffLabel(actual, target) {
  if (!target) return "-";
  const d = actual - target;
  const pct = (actual / target * 100).toFixed(0);
  return `${d >= 0 ? "+" : ""}${d} (${pct}%)`;
}

// 媒体・エージェント別の応募元内訳。複数経路レコードは rec.channels を分配カウント。
// 戻り値: { 経路名: { curr: 当月件数, total: 累計件数 } }（エントリー到達日基準）
function aggregateSourceBreakdown(records, phases, ym) {
  const entryP = phases.find(p => p.label === "エントリー");
  const result = {};
  records.forEach(rec => {
    const d = entryP ? rec.arrivals[entryP.key] : _firstArrival(rec);
    if (!(d instanceof Date)) return;
    const isCurr = monthKey(d) === ym;
    const sources = (rec.channels && rec.channels.length) ? rec.channels : [rec.channel || "(未分類)"];
    sources.forEach(s => {
      const name = s.trim() || "(未分類)";
      if (!result[name]) result[name] = { curr: 0, total: 0 };
      result[name].total++;
      if (isCurr) result[name].curr++;
    });
  });
  return result;
}

function generateMonthlyDocV2(targetMonth) {
  const cfg = getConfig();
  const company = String(cfg["企業名"] || "RPO").trim();
  const now = new Date();
  let year, month;
  if (targetMonth && /^\d{4}-\d{1,2}$/.test(targetMonth)) {
    const parts = targetMonth.split("-");
    year = parseInt(parts[0], 10);
    month = parseInt(parts[1], 10);
  } else {
    const prev = new Date(now.getFullYear(), now.getMonth() - 1, 1);
    year = prev.getFullYear();
    month = prev.getMonth() + 1;
  }
  const ymLabel = `${year}年${month}月`;

  const { records, phases } = loadRawRecords();
  const currKpi = _monthlyKpiSnapshot(records, phases, year, month);
  const prevDate = new Date(year, month - 2, 1);
  const prevKpi = _monthlyKpiSnapshot(records, phases, prevDate.getFullYear(), prevDate.getMonth() + 1);
  // 目標（フェーズ別・チャネル別）を先に読み込み、KPI/フェーズ表/経路表で目標差分に使う
  const targets = loadTargetsFunnel(phases);
  const targetsCh = loadTargetsChannel();
  // ラベル→当月目標 を引くヘルパー（labelに対応するphase.keyの目標を参照）
  const targetForLabel = (label) => {
    const p = phases.find(x => x.label === label);
    return p ? (targets[p.key]?.[currKpi.ym] || 0) : 0;
  };

  // Doc 作成
  const docName = `${company} 採用月次レポート ${ymLabel}`;
  const doc = DocumentApp.create(docName);
  const body = doc.getBody();
  Logger.log("[monthly] doc created: " + doc.getUrl());

  try {
    // タイトル
    body.appendParagraph(docName).setHeading(DocumentApp.ParagraphHeading.TITLE);
    const sub = body.appendParagraph(`${company} 新卒採用　／　${ymLabel}　／　生成日: ${formatDate(now)}`);
    sub.setItalic(true);

    // KPI ヒーローブロック (前月比付き)
    body.appendParagraph(" ");
    _docAppendKpiBlock(body, [
      { label: "新規エントリー", value: currKpi.entry,    diff: _diffLabel(currKpi.entry, prevKpi.entry) },
      { label: "説明会参加",     value: currKpi.briefing, diff: _diffLabel(currKpi.briefing, prevKpi.briefing) },
      { label: "1次面接参加",     value: currKpi.interview1, diff: _diffLabel(currKpi.interview1, prevKpi.interview1) },
      { label: "最終選考参加",   value: currKpi.final,    diff: _diffLabel(currKpi.final, prevKpi.final) },
      { label: "内定獲得",       value: currKpi.offer,    diff: _diffLabel(currKpi.offer, prevKpi.offer) },
    ]);
    body.appendParagraph(" ");

    // ② 目標 vs 実績（当月）— KPI主要フェーズの目標差分
    const kpiTargetRows = [
      ["新規エントリー", currKpi.entry,    "エントリー"],
      ["説明会参加",     currKpi.briefing, "説明選考会【参加】"],
      ["1次面接参加",    currKpi.interview1, "一次面接【参加】"],
      ["最終選考参加",   currKpi.final,    "最終選考【参加】"],
      ["内定獲得",       currKpi.offer,    "内定"],
    ].map(([disp, actual, label]) => {
      const tgt = targetForLabel(label);
      return [disp, String(actual), tgt ? String(tgt) : "-", _targetDiffLabel(actual, tgt)];
    });
    body.appendParagraph("◆ 当月 目標 vs 実績").setHeading(DocumentApp.ParagraphHeading.HEADING2);
    _appendDocTable(body, ["指標", "実績", "目標", "差分(達成率)"], kpiTargetRows);
    body.appendParagraph(" ");

    // トレンドチャート
    try {
      const trend = _monthlyTrendData(records, phases, year, month, 6);
      const blob = _buildTrendChartBlob(trend);
      if (blob) body.appendImage(blob).setWidth(520).setHeight(280);
    } catch (e) { Logger.log("trend chart skip: " + e.message); }

    body.appendParagraph(" ");

    // Good/More （targets/targetsCh は上部で読込済み）
    const insights = generateOverviewInsights(records, phases, targets, targetsCh);
    const goods = insights.filter(i => i.icon === "✅").slice(0, 3).map(i => `${i.title}: ${i.text}`);
    const mores = insights.filter(i => i.icon === "⚠️" || i.icon === "🔴").slice(0, 3).map(i => `${i.title}: ${i.text}`);
    if (goods.length) _docAppendCallout(body, "good", goods);
    if (mores.length) _docAppendCallout(body, "more", mores);

    // ─── 単月詳細 ───
    body.appendPageBreak();
    body.appendParagraph(`◆ ${ymLabel} 単月詳細`).setHeading(DocumentApp.ParagraphHeading.HEADING1);

    // ③ フェーズ別実績表 — 全選考フェーズ網羅（予約/参加/合格/不合格/辞退含む）＋ ② 目標差分
    //    順序: rawの列順(p.colIdx)を維持。後面談(interview)は補足として末尾に回す
    const fStats = aggregateFunnelMonthly(records, phases);
    const prevYm = `${prevDate.getFullYear()}-${String(prevDate.getMonth()+1).padStart(2,"0")}`;
    const orderedPhases = phases
      .filter(p => p.group !== "interview")
      .sort((a, b) => a.colIdx - b.colIdx);
    const phaseRows = orderedPhases.map(p => {
      const c = fStats[p.key]?.[currKpi.ym] || 0;
      const pv = fStats[p.key]?.[prevYm] || 0;
      const tgt = targets[p.key]?.[currKpi.ym] || 0;
      return [p.label, String(c), tgt ? String(tgt) : "-", _targetDiffLabel(c, tgt), String(pv), _diffLabel(c, pv)];
    });
    body.appendParagraph("◆ 全選考フェーズ実績 (当月)").setHeading(DocumentApp.ParagraphHeading.HEADING2);
    _appendDocTable(body, ["フェーズ", `${month}月`, "目標", "差分(達成率)", `${prevDate.getMonth()+1}月`, "前月比"], phaseRows);

    // ① 媒体・エージェント別 応募元内訳 (当月 / 累計 / 構成比) ＋ 当月目標差分
    const srcStats = aggregateSourceBreakdown(records, phases, currKpi.ym);
    const srcTotalCurr = Object.values(srcStats).reduce((s, v) => s + v.curr, 0);
    const sourceRows = Object.entries(srcStats)
      .filter(([, v]) => v.total > 0)
      .sort((a, b) => b[1].curr - a[1].curr || b[1].total - a[1].total)
      .map(([name, v]) => {
        const tgt = targetsCh[name]?.[currKpi.ym] || 0;
        const share = srcTotalCurr ? (v.curr / srcTotalCurr * 100).toFixed(0) + "%" : "-";
        return [name, String(v.curr), String(v.total), share, tgt ? String(tgt) : "-", _targetDiffLabel(v.curr, tgt)];
      });
    if (sourceRows.length) {
      const allTotal = Object.values(srcStats).reduce((s, v) => s + v.total, 0);
      sourceRows.push(["合計", String(srcTotalCurr), String(allTotal), "100%", "", ""]);
      body.appendParagraph(" ");
      body.appendParagraph("◆ 媒体・エージェント別 応募元内訳 (どこから応募が来たか)").setHeading(DocumentApp.ParagraphHeading.HEADING2);
      _appendDocTable(body, ["経路(媒体/エージェント)", "当月", "累計", "構成比", "当月目標", "差分(達成率)"], sourceRows);
    }

    // 大学別Top10
    const schoolStats = aggregateBySchool(records, phases);
    const acceptKey = phases.find(p => p.label === "内定承諾")?.key;
    const schoolRows = Object.entries(schoolStats)
      .filter(([, s]) => s.entry > 0)
      .map(([sch, s]) => [sch, String(s.entry), String(acceptKey ? (s.byPhase[acceptKey] || 0) : 0)])
      .sort((a, b) => parseInt(b[1]) - parseInt(a[1]))
      .slice(0, 10);
    if (schoolRows.length) {
      body.appendParagraph(" ");
      body.appendParagraph("◆ 大学別エントリーTop10 (累計)").setHeading(DocumentApp.ParagraphHeading.HEADING2);
      _appendDocTable(body, ["大学", "累計エントリー", "承諾"], schoolRows);
    }

    // ─── 翌月アクション ───
    body.appendPageBreak();
    body.appendParagraph("◆ 翌月アクション").setHeading(DocumentApp.ParagraphHeading.HEADING1);
    const actLines = insights.slice(0, 5).map((i, idx) => `${idx+1}. ${i.title}: ${i.text}`);
    if (actLines.length === 0) body.appendParagraph("（特記なし）");
    else actLines.forEach(l => body.appendListItem(l));

    // フッター
    body.appendHorizontalRule();
    const footer = body.appendParagraph(`Generated: ${formatDatetime(now)} / Gemini RPO ダッシュボード`);
    footer.setItalic(true);
  } catch (e) {
    Logger.log("[monthly] error: " + e.message + " stack: " + (e.stack||"").substring(0,300));
    body.appendParagraph("[本文生成エラー: " + e.message + "]").editAsText().setForegroundColor("#c00");
  }

  try { doc.saveAndClose(); } catch (e) { Logger.log("save error: " + e.message); }

  // ドメイン編集権限
  try {
    DriveApp.getFileById(doc.getId()).setSharing(DriveApp.Access.DOMAIN_WITH_LINK, DriveApp.Permission.EDIT);
  } catch (e) { Logger.log("share error: " + e.message); }

  const url = doc.getUrl();
  // Slack通知
  try {
    const settings = getSlackSettings();
    if (settings.monthlyChannel) {
      sendSlackMessage(settings.monthlyChannel, `📄 ${company} 採用月次レポート (${ymLabel}) 生成完了\n${url}`);
    }
  } catch (e) { Logger.log("slack notify skip: " + e.message); }
  return url;
}

function previewMonthlyDocV2() {
  const url = generateMonthlyDocV2();
  if (url) SpreadsheetApp.getUi().alert("月次レポートV2 生成完了\n" + url);
}

function generatePastMonthlyDocV2() {
  const ui = SpreadsheetApp.getUi();
  const resp = ui.prompt("過去月の月次レポートV2", "対象月を YYYY-MM 形式で入力 (例: 2026-04)", ui.ButtonSet.OK_CANCEL);
  if (resp.getSelectedButton() !== ui.Button.OK) return;
  const text = resp.getResponseText().trim();
  if (!/^\d{4}-\d{1,2}$/.test(text)) { ui.alert("形式エラー: YYYY-MM"); return; }
  const url = generateMonthlyDocV2(text);
  if (url) ui.alert("月次レポートV2 生成完了\n" + url);
}

// 月次トリガー: 毎月1日0時に前月分を自動生成
function setMonthlyTriggerV2() {
  ScriptApp.getProjectTriggers().forEach(t => {
    if (["generateMonthlyDoc", "generateMonthlyDocV2"].includes(t.getHandlerFunction())) {
      ScriptApp.deleteTrigger(t);
    }
  });
  ScriptApp.newTrigger("generateMonthlyDocV2").timeBased().onMonthDay(1).atHour(0).create();
  SpreadsheetApp.getUi().alert("月次レポートV2 トリガー設定完了: 毎月1日 0時");
}

// 毎朝9時の再集計トリガーをまとめて設定
function setDailyRebuildTrigger() {
  ScriptApp.getProjectTriggers().forEach(t => {
    if (t.getHandlerFunction() === "rebuildAll") ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger("rebuildAll").timeBased().atHour(9).everyDays(1).create();
  SpreadsheetApp.getUi().alert("毎朝9時 再集計トリガー設定完了");
}

// 水曜9:00 の週次レポート用トリガーを設定
function setWeeklyTriggerV2() {
  ScriptApp.getProjectTriggers().forEach(t => {
    if (["sendWeeklyReport", "sendWeeklyReportV2"].includes(t.getHandlerFunction())) {
      ScriptApp.deleteTrigger(t);
    }
  });
  ScriptApp.newTrigger("sendWeeklyReportV2").timeBased()
    .onWeekDay(ScriptApp.WeekDay.WEDNESDAY)
    .atHour(9)
    .create();
  SpreadsheetApp.getUi().alert("週次レポートV2 トリガー設定完了: 毎週水曜 9時");
}

function _writeLog(status, msg) {
  const { log } = getOutputSheetNames();
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(log);
  if (!sheet) sheet = ss.insertSheet(log);
  sheet.setHiddenGridlines(true);
  if (sheet.getLastRow() === 0) {
    sheet.getRange(1, 1, 1, 3).setValues([["日時", "結果", "詳細"]]);
    sheet.getRange(1, 1, 1, 3).setBackground(COLOR.bgDark).setFontColor(COLOR.fgWhite).setFontWeight("bold");
    sheet.setColumnWidth(1, 160);
    sheet.setColumnWidth(2, 80);
    sheet.setColumnWidth(3, 600);
  }
  sheet.appendRow([formatDatetime(new Date()), status, msg]);
}
