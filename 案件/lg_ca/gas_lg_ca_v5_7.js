// ============================================================
// LG/CA 面談連携シート GAS v5.7
// v5.7変更:
//   - 重複報告モーダル（Modal-D）廃止
//   - buildThreadButtons から「⚠️ 重複報告」ボタン削除
//   - handleDuplicateReport / _buildModalDuplicate 削除
//   - 重複検知は以下の2系統に集約:
//     a) 登録時の自動チェック（checkDuplicate）→ Ephemeral警告 + スレッド返信
//     b) 面談後のCA発覚 → シートW列(重複チェック)をON → onEditInstallable が
//        学生スレッドに「⚠️ 重複発覚（CAから報告）」通知
// ============================================================
// LG/CA 面談連携シート GAS v5.6
// v5.6変更:
//   - createMonthlyDigest() 関数追加（月次集計シート自動生成）
//     - 毎月1日0時に前月分のサマリーシートを自動生成
//     - シート名: 月次集計_YYYY-MM
//     - 集計: 全体KPI / LG別 / CA別 / 流入経路別 / 卒年別 / 業界別
//     - 引数指定で過去月も手動生成可能
//   - setAllTriggers に毎月1日のトリガー追加
// ============================================================
// LG/CA 面談連携シート GAS v5.5
// v5.5変更:
//   - LGカレンダー登録を「LG共通カレンダーID」（info アカウント等）に一元化
//     - 設定タブ「LG共通カレンダーID」を参照（推奨: info@tokumori.co.jp）
//     - LGリストB列の個別カレンダーIDは未参照に
//     - LGメンバー追加時のカレンダー権限取得不要
// ============================================================
// LG/CA 面談連携シート GAS v5.4
// v5.4変更（Block Kit モーダル統合・リマインド・再回収・重複強化）:
//   - Slackワークフローへの依存を撤廃 → Block Kit モーダル方式
//     - Modal-A: 面談登録（LG）
//     - Modal-B: 日程入力（CA）
//     - Modal-C: 日程再回収（LG）
//     - Modal-D: 重複報告（CA）
//   - doPost を block_actions / view_submission 両対応に拡張
//   - openModal / handleViewSubmission / buildThreadButtons 追加
//   - applyRecollect: 候補日時を上書きしCA再照合
//   - handleDuplicateReport: フェーズ「重複（要整理）」+ 飛びCh通知
//   - remindStalledMeetings: 12h/24h/36h で段階リマインド、36h超で自動「調整不可」
//   - formatNotification: 全通知メッセージのフォーマット統一
//   - pollSlackMessages / parseWorkflowMessage / parseRescheduleMessage 削除
//   - 卒年シートに AB=_SF除外 / AC=_リマインドフラグ / AD=_最終リマインド時刻 追加
//   - setAllTriggers: ポーリング撤去・remindStalledMeetings 1時間毎追加
// ============================================================
// LG/CA 面談連携シート GAS v5.3
// v5.3変更:
//   - スロット刻みを設定タブ「スロット刻み（分）」で可変化（getSlotStepMin）
//     - デフォルト15分。10:00/10:15/10:30/10:45 起点で面談開始可能
//     - 1〜120分の範囲で受付。無効値は15分にフォールバック
//   - SLOT_STEP_MIN / AVAIL_CAL_STEP_MIN → getSlotStepMin() に統一
//   - 空き枠カレンダー表示も同じ刻みに連動
// ============================================================
// LG/CA 面談連携シート GAS v5.2
// v5.2変更:
//   - 面談時間を設定タブ「面談時間（分）」で可変化（getMeetingDurationMin）
//     - デフォルト60分、未設定や無効値は60分にフォールバック
//     - 1〜240分の範囲で受付
//   - MEETING_DURATION_MIN → MEETING_DURATION_MIN_DEFAULT に改名
//   - AVAIL_CAL_DURATION_MIN 廃止（getMeetingDurationMin と統合）
// ============================================================
// LG/CA 面談連携シート GAS v5.1
// v5.1変更:
//   - renderAvailabilityCalendar の再実行時 merge 衝突エラーを修正
//     - 描画前に breakApart / setFrozenRows(0) / setFrozenColumns(0) を実行
//   - cleanupOldTabs に「連携メイン_2026-05」を追加（v4.0時代の月次シート残骸）
// ============================================================
// LG/CA 面談連携シート GAS v5.0
// SpreadsheetID: 1NmJXivFLnPC-Nb50ANZx2gZWT4vPneOm7XVF-B4t698
// v5.0変更（卒年シート＋LG実績ダッシュボード）:
//   - シート単位を「月次」から「卒年ごと」に変更
//     - シート名: 連携メイン_27卒 / 連携メイン_28卒 / 連携メイン_未分類
//     - Slackワークフロー入力時、卒年シートが無ければ自動作成
//   - LG実績ダッシュボードタブを新設（updateLGDashboard で5分毎更新）
//   - cleanupOldTabs() で旧サンプル系タブを一掃
//   - DEFAULT_MAIN・cfg["現在のシート名"] への依存を撤廃
//   - 重複チェック・リスケ・SF同期・当日リマインドを全卒年シート横断に変更
// v4.0変更:
//   - P1-A: pollSlackMessages のポーリングチャンネルを設定化
//     - 「Slack ワークフローチャンネルID」設定キーで本番/テスト切り替え可能に
//   - P1-B: handleButtonAction の飛び報告で「Slack 飛びチャンネルID」に追加通知
//   - P2: parseWorkflowMessage/parseRescheduleMessage のlook-aheadを必須フィールド限定に変更
//     - 任意フィールド（志望業界等）が空欄でも次行を誤って拾わなくなる
//   - P3: createMonthlySheet() 関数追加（月初に新シート自動作成）
//   - P4: setAllTriggers に毎月1日のトリガーを追加
// v3.9変更:
//   - 「空き枠カレンダー」タブを自動描画（renderAvailabilityCalendar）
//     - 翌日〜14日先・10:00〜21:00（30分刻み・21スロット）の集計型マトリクス
//     - 🟢 全員空き / 🟡 一部空き / 🔴 全員埋まり を背景色＋アイコンで表示
//     - 5分毎トリガーで自動更新
//     - アクティブCAのみ集計（v3.8 連動）
//     - 既存 getExcludeKeywords を再利用してブロッカー予定を無視
// v3.8変更:
//   - CAリスト/LGリストにステータス列(E)導入「アクティブ/非アクティブ/共有待ち」
//   - checkCAAvailability: アクティブCAのみカレンダー照合
//   - getCAInfoByUid: 非アクティブUIDはnull返却（日程入力WF拒否）
//   - getLGInfo: 非アクティブLGも未解決扱い（メンション・LINE URL等で参照されない）
//   - 後方互換: ステータス列が空欄の行はアクティブとみなす
// v3.7.2変更:
//   - 飛び報告ボタン押下時にカレンダー削除を廃止（_deleteEventByStr → _annotateEventNoShow）
//   - description 末尾に「🚫 飛び報告 / 報告日時 / 報告者」を追記
//   - イベントタイトルに [飛び] プレフィックスを付与（一覧で識別容易）
//   - 二重追記防止チェックあり
// v3.7.1変更:
//   - onEditInstallable W列ON時の通知を「CAが面談後に重複発覚」固定文面に変更
//   - LGメンバーへ Slack メンション（<@UID>）付き通知
//   - 面談前/後の自動判定（v3.6で追加）は廃止
// v3.7変更:
//   - CA空き枠無し時: 学生スレッドに :hourglass_flowing_sand: 付与＋ @ca 調整依頼を投稿
//   - 新ワークフロー「日程入力」を pollSlackMessages が検出
//     - parseRescheduleMessage / applyReschedule で確定日時パース・反映
//     - CAカレンダーに自動登録（record@tokumori.co.jp 招待）
//     - スタンプ遷移: ⏳ → 🙋 → ✅ を自動運用
//   - onEditInstallable: V列「調整不可」手動入力で :no_entry: 通知＋スタンプ
//   - 設定タブに「CAユーザーグループID」行を追加（subteam mention 用）
// v3.6変更:
//   - onEditInstallable: 重複チェック時のSlackスレッド通知に学生情報を含める
//     - フェーズで「面談前/面談後」を判定して文言を切替
//   - setAllTriggers: インストーラブル onEdit トリガーを追加（W列チェックで発火）
// v3.5変更:
//   - parseWorkflowMessage: 任意フィールド空時の次行ラベル誤検出を修正
//     （「相談内容: 業界分析」のような『先頭ラベル + 値』形式の行も
//       FIELD_MAP 照合対象にしてラベルとして判定）
// v3.4変更:
//   - pollSlackMessages に並行実行ロック（LockService）と処理済みts重複防止を追加
// v3.3変更:
//   - CA判定で「ブロッカー系イベント」を無視するフィルタ追加
//     （例: 基本休み / オフィス / 作業block / block / ※Block / 定例 など）
//   - 設定タブ「CA判定 除外キーワード」(B列にパイプ区切り) で動的変更可能
// v3.2変更:
//   - 候補時間①②③: 範囲入力対応（例: "10:00~19:00"）→ 30分刻みで空きCA探索
//   - record@tokumori.co.jp を必ず招待（カレンダーイベント）
//   - @tokumori.co.jp 宛は通知送らない（sendUpdates: none）
//   - 1学生=1スレッド: 確認メッセージを元ワークフロー投稿にスレッド返信
//   - Ephemeral メッセージ: 重複・エラー時は投稿者本人にだけ表示
//   - メモ(AA列)に申し送りを自動記入
// ============================================================

const CONFIG_SHEET    = "設定";
const KANRI_SS_ID     = "1F0QX887geYtLetarmPnQuyvxCGpOm_bbC_hSJeurPSs";
const UNCLASSIFIED    = "連携メイン_未分類";
const GRADE_SHEET_RE  = /^連携メイン_(\d+卒|未分類)$/;
// v5.7.1: 卒年シート読込時の最大列数 (A〜AD = 30列) — 余剰列の読込を防ぎ高速化
const GRADE_SHEET_COLS = 30;
const DASHBOARD_SHEET = "LG実績ダッシュボード";
const MEETING_DURATION_MIN_DEFAULT = 60; // 面談時間（分）デフォルト値。設定タブ「面談時間（分）」で上書き可
const SLOT_STEP_MIN_DEFAULT        = 15; // スロット刻み（分）デフォルト値。設定タブ「スロット刻み（分）」で上書き可
const RECORD_EMAIL                 = "record@tokumori.co.jp";

// 設定タブの「面談時間（分）」を読み込む（無効値はデフォルト60にフォールバック）
function getMeetingDurationMin() {
  const raw = parseInt(String(getConfig()["面談時間（分）"] || "").trim(), 10);
  if (isNaN(raw) || raw <= 0 || raw > 240) return MEETING_DURATION_MIN_DEFAULT;
  return raw;
}

// 設定タブの「スロット刻み（分）」を読み込む（無効値はデフォルト15にフォールバック）
// 例: 15 → 10:00/10:15/10:30/10:45 起点で面談を開始可能
//     30 → 10:00/10:30 起点のみ
function getSlotStepMin() {
  const raw = parseInt(String(getConfig()["スロット刻み（分）"] || "").trim(), 10);
  if (isNaN(raw) || raw <= 0 || raw > 120) return SLOT_STEP_MIN_DEFAULT;
  return raw;
}

// 空き枠カレンダー（v3.9）
const AVAIL_CAL_SHEET        = "空き枠カレンダー";
const AVAIL_CAL_DAYS         = 14;
// v5.7+: 全CAのビジネスアワーをカバー (業務委託/gmail = 9-23:15 / tokumori = 平日9-20)
const AVAIL_CAL_HOUR_START   = 9;
const AVAIL_CAL_HOUR_END     = 23;
// デフォルトの除外キーワード（設定タブで上書き可）
// v5.7+: 厳格モード — 既存予定があれば例外なくブロッカー扱い
// （旧デフォルトリストは廃止。設定タブを空欄にすれば一切除外しない）
const DEFAULT_EXCLUDE_KEYWORDS = [];

// ─────────────────────────────────────────
// 設定管理
// ─────────────────────────────────────────

function getConfig() {
  // v5.7+: CacheService で 5分キャッシュ。doPost の重さを軽減
  try {
    const cache = CacheService.getScriptCache();
    const cached = cache.get("__cfg__");
    if (cached) return JSON.parse(cached);
  } catch(_) {}
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(CONFIG_SHEET);
  const data  = sheet.getDataRange().getValues();
  const cfg   = {};
  data.forEach(row => { if (row[0]) cfg[String(row[0]).trim()] = row[1]; });
  // v5.7+: シートB2が空でも Script Properties から Bot Token を自動補完
  if (!cfg["Slack Bot Token"]) {
    const propToken = PropertiesService.getScriptProperties().getProperty("SLACK_BOT_TOKEN");
    if (propToken) cfg["Slack Bot Token"] = propToken;
  }
  try { CacheService.getScriptCache().put("__cfg__", JSON.stringify(cfg), 300); } catch(_) {}
  return cfg;
}

function setConfig(key, value) {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(CONFIG_SHEET);
  const data  = sheet.getDataRange().getValues();
  for (let i = 0; i < data.length; i++) {
    if (String(data[i][0]).trim() === key) { sheet.getRange(i + 1, 2).setValue(value); break; }
  }
  // v5.7+: 設定変更時はキャッシュ無効化
  try { CacheService.getScriptCache().remove("__cfg__"); } catch(_) {}
}

// ─────────────────────────────────────────
// Slack API
// ─────────────────────────────────────────

// v5.7+: Slack リクエスト検証
//   GAS doPost は HTTP ヘッダを露出しないため、Slack 公式の Signing Secret 検証は実装不可。
//   代替策として URL クエリに共有秘密トークンを付与し検証する。
//   設定方法:
//     1. Script Property "SLACK_URL_TOKEN" にランダム文字列を設定
//     2. Slack App の Request URL を `https://script.google.com/.../exec?token=XXX` に変更
//   未設定の場合は互換のため通す（本番運用前に必ず設定）
function _verifySlackSignature(e) {
  const required = (PropertiesService.getScriptProperties().getProperty("SLACK_URL_TOKEN") || "").trim();
  if (!required) {
    Logger.log("[verifySig] SLACK_URL_TOKEN 未設定 → スキップ (本番では必ず設定すること)");
    return true;
  }
  const got = (e?.parameter?.token || "").toString().trim();
  return got === required;
}

function sendSlackMessage(channel, text, blocks, threadTs) {
  const token   = getConfig()["Slack Bot Token"];
  const payload = {
    channel, text: text || " ",
    // v5.7+: Meet等のURL自動プレビューを抑止（メッセージのノイズ削減）
    unfurl_links: false,
    unfurl_media: false,
  };
  if (blocks && blocks.length > 0) payload.blocks = blocks;
  if (threadTs) payload.thread_ts = threadTs;

  const res    = UrlFetchApp.fetch("https://slack.com/api/chat.postMessage", {
    method: "post", contentType: "application/json",
    headers: { Authorization: "Bearer " + token },
    payload: JSON.stringify(payload), muteHttpExceptions: true,
  });
  const result = JSON.parse(res.getContentText());
  if (!result.ok) Logger.log("[Slack Error] " + result.error);
  return result;
}

// reactions.add / reactions.remove
function addReaction(channel, ts, name) {
  if (!channel || !ts || !name) return null;
  const token = getConfig()["Slack Bot Token"];
  const res   = UrlFetchApp.fetch("https://slack.com/api/reactions.add", {
    method: "post", contentType: "application/json",
    headers: { Authorization: "Bearer " + token },
    payload: JSON.stringify({ channel, timestamp: ts, name }),
    muteHttpExceptions: true,
  });
  const result = JSON.parse(res.getContentText());
  if (!result.ok && result.error !== "already_reacted") Logger.log(`[Reaction add ${name}] ${result.error}`);
  return result;
}

function removeReaction(channel, ts, name) {
  if (!channel || !ts || !name) return null;
  const token = getConfig()["Slack Bot Token"];
  const res   = UrlFetchApp.fetch("https://slack.com/api/reactions.remove", {
    method: "post", contentType: "application/json",
    headers: { Authorization: "Bearer " + token },
    payload: JSON.stringify({ channel, timestamp: ts, name }),
    muteHttpExceptions: true,
  });
  const result = JSON.parse(res.getContentText());
  if (!result.ok && result.error !== "no_reaction") Logger.log(`[Reaction remove ${name}] ${result.error}`);
  return result;
}

// CA情報の Slack UID 逆引き（アクティブのみ）
function getCAInfoByUid(slackUid) {
  if (!slackUid) return null;
  const uidTrim = String(slackUid).trim();
  const rows = _caListRows();
  for (const r of rows) {
    if (String(r[2] || "").trim() === uidTrim && String(r[4] || "").trim() === "アクティブ") {
      return { name: String(r[0]).trim(), calId: String(r[1]).trim(), slackUid: uidTrim };
    }
  }
  return null;
}

// v5.7+: CA情報の Slack UID 逆引き（アクティブ＋非アクティブ含む / 共有待ちは除外）
//   代打受諾・CA未確定の日程入力で使用 (非アクティブでも対応可能にする)
function getCAInfoByUidAny(slackUid) {
  if (!slackUid) return null;
  const uidTrim = String(slackUid).trim();
  const rows = _caListRows();
  for (const r of rows) {
    const status = String(r[4] || "").trim();
    if (String(r[2] || "").trim() === uidTrim && status !== "共有待ち") {
      return { name: String(r[0]).trim(), calId: String(r[1]).trim(), slackUid: uidTrim, status };
    }
  }
  return null;
}

// v5.7+: 通知メッセージのフォーマット統一ヘルパー
//   [絵文字] *#No タイトル*
//
//   ・担当LG: <@UID>
//   ・担当CA: <@UID>
//   ・学生: account（卒年・SNS）
//   [detail各行を箇条書きで]
//
//   報告者: reporter
function formatNotification(opts) {
  const { statusEmoji, title, rowNo, account, grade, sns, lgUid, caUid, caName, detail, reporter } = opts;
  const lines = [];
  lines.push(`${statusEmoji || ""} *#${_padNo(rowNo)} ${title}*`.trim());
  lines.push(``);  // タイトル下に呼吸用空行

  if (lgUid)        lines.push(`・担当LG: <@${lgUid}>`);
  if (caUid)        lines.push(`・担当CA: <@${caUid}>`);
  else if (caName)  lines.push(`・担当CA: ${caName}`);
  if (account) {
    const meta = [grade, sns].filter(Boolean).join("・");
    lines.push(`・学生: ${account}${meta ? `（${meta}）` : ""}`);
  }

  // detail を箇条書きに整形（改行/区切りごとに ・ 付与）
  if (detail) {
    const detailLines = String(detail)
      .split(/\n+/)
      .map(s => s.trim())
      .filter(Boolean)
      .map(s => s.startsWith("・") || s.startsWith("→") || s.startsWith("⇒") ? s : `・${s}`);
    if (detailLines.length) {
      lines.push(...detailLines);
    }
  }

  if (reporter) {
    lines.push(``);
    lines.push(`報告者: ${reporter}`);
  }
  return lines.join("\n");
}

// Ephemeral: 投稿者にだけ見えるメッセージ
function sendEphemeral(channel, user, text, blocks) {
  if (!user) return null;
  const token   = getConfig()["Slack Bot Token"];
  const payload = { channel, user, text: text || " " };
  if (blocks && blocks.length > 0) payload.blocks = blocks;

  const res    = UrlFetchApp.fetch("https://slack.com/api/chat.postEphemeral", {
    method: "post", contentType: "application/json",
    headers: { Authorization: "Bearer " + token },
    payload: JSON.stringify(payload), muteHttpExceptions: true,
  });
  const result = JSON.parse(res.getContentText());
  if (!result.ok) Logger.log("[Ephemeral Error] " + result.error);
  return result;
}

// ─────────────────────────────────────────
// v5.4: 日程入力モーダル送信処理（CA用）
// payload: { rowNo, date, startTime, endTime?, memo?, userId, channel, threadTs }
// ─────────────────────────────────────────

function applyDateInput(args) {
  const { rowNo, date, startTime, endTime, memo, userId, channel } = args;
  // v5.7+: アクティブ＋非アクティブを許可 (共有待ちのみ除外)
  const caInfo = getCAInfoByUidAny(userId);
  if (!caInfo) {
    sendEphemeral(channel, userId, "⚠️ メンバーCAに自分のSlack User IDが未登録 or 「共有待ち」のため日程入力を受付できません。管理者に連絡してください。");
    return;
  }

  const found = findRowByNo(rowNo);
  if (!found) {
    sendEphemeral(channel, userId, `⚠️ #${_padNo(rowNo)} がシートに見つかりません`);
    return;
  }
  const { sheet, rowIdx, data } = found;
  const studentTs = String(data[rowIdx][25] || "").trim();

  const startDt = parseDatetime(date, startTime);
  const endDt   = endTime
    ? parseDatetime(date, endTime)
    : (startDt ? new Date(startDt.getTime() + getMeetingDurationMin() * 60 * 1000) : null);
  if (!startDt || !endDt) {
    sendEphemeral(channel, userId, `⚠️ #${_padNo(rowNo)} 日時パース失敗（date=${date} time=${startTime}）`);
    return;
  }

  const rowData   = data[rowIdx];
  const calParams = {
    lgMember: rowData[2], account: rowData[4], grade: rowData[5],
    sns: rowData[6], industry: rowData[7], topic: rowData[8], reach: rowData[11],
  };
  const lgName = String(rowData[2] || "").trim();

  if (studentTs) addReaction(channel, studentTs, "raised_hand");

  const cal     = createCalendarEvent(caInfo.calId, calParams, startDt, endDt, lgName, caInfo.name, rowData[0]);
  const meetUrl = cal.meetUrl;

  const confirmedStr = `${formatDatetime(startDt)}〜${formatTime(endDt)}`;
  sheet.getRange(rowIdx + 1, 19, 1, 4).setValues([[confirmedStr, caInfo.name, meetUrl, "実施予定"]]);

  const memoText = [
    `【申し送り（CA調整後）】`,
    `学生: @${calParams.account}（${calParams.grade || "-"}・${calParams.sns || "-"}）`,
    `日時: ${confirmedStr}`,
    `業界: ${calParams.industry || "-"} / 相談: ${calParams.topic || "-"}`,
    `つなぎ方: ${calParams.reach || "-"}`,
    `Meet: ${meetUrl || "-"}`,
    `担当LG: ${lgName}`,
    `担当CA: ${caInfo.name} (<@${caInfo.slackUid}>)`,
    memo ? `備考: ${memo}` : null,
  ].filter(Boolean).join("\n");
  sheet.getRange(rowIdx + 1, 27).setValue(memoText);

  const replyTs = studentTs || args.threadTs || null;
  // v5.7: LG担当もメンション化
  const _lgInfoA = getLGInfo(calParams.lgMember);
  const _lgUidA  = /^U[A-Z0-9]+$/.test(String(calParams.lgMember).trim()) ? String(calParams.lgMember).trim() : _lgInfoA.slackUid;
  // v5.7+: 調整完了メッセージにフェーズ「実施予定」のボタンを付与（CA確認・再回収・飛び報告）
  const _notifText = formatNotification({
    statusEmoji: "✅", title: "調整完了", rowNo,
    account: calParams.account, grade: calParams.grade, sns: calParams.sns,
    lgUid: _lgUidA, caUid: caInfo.slackUid, caName: caInfo.name,
    detail: `日時: ${confirmedStr}\nMeet: ${meetUrl}`,
    reporter: `<@${caInfo.slackUid}>`,
  });
  const _blocks = [{ type: "section", text: { type: "mrkdwn", text: _notifText } }];
  const _btnBlock = buildThreadButtons(rowNo, "実施予定");
  if (_btnBlock) _blocks.push(..._btnBlock);
  sendSlackMessage(channel, _notifText, _blocks, replyTs);

  if (studentTs) {
    removeReaction(channel, studentTs, "hourglass_flowing_sand");
    removeReaction(channel, studentTs, "raised_hand");
    addReaction(channel, studentTs, "white_check_mark");
  }
}


// ─────────────────────────────────────────
// 重複チェック
// ─────────────────────────────────────────

function checkDuplicate(account, sns) {
  const a = String(account || "").trim();
  const s = String(sns || "").trim();
  if (!a) return { isDuplicate: false };
  // v5.7.1: 必要列のみ (A=連携番号 / B=日時 / E=学生 / G=SNS) → 高速化
  for (const sheet of getAllGradeSheets()) {
    const lastRow = sheet.getLastRow();
    if (lastRow < 2) continue;
    const data = sheet.getRange(1, 1, lastRow, 7).getValues();
    for (let i = 1; i < data.length; i++) {
      if (!data[i][0]) continue;
      if (String(data[i][4]).trim() === a && String(data[i][6]).trim() === s) {
        return { isDuplicate: true, rowNo: data[i][0], date: data[i][1], sheetName: sheet.getName() };
      }
    }
  }
  return { isDuplicate: false };
}

// ─────────────────────────────────────────
// LGメンバー情報取得（v3.1: UID優先・名前フォールバック）
// LGリスト列構成: A=LG名 / B=カレンダーID / C=Slack User ID / D=LINE追加URL
// ─────────────────────────────────────────

function getLGInfo(lgMemberOrUid) {
  const key = String(lgMemberOrUid || "").trim();
  if (!key) return _emptyLGInfo("");

  const rows = _lgListRows();
  const isUid = /^U[A-Z0-9]+$/.test(key);
  for (const r of rows) {
    const name   = String(r[0] || "").trim();
    const uid    = String(r[2] || "").trim();
    const status = String(r[4] || "").trim();
    if ((isUid && uid === key) || (!isUid && name === key)) {
      if (status && status !== "アクティブ") {
        Logger.log(`[getLGInfo] LGステータス=${status} のため未解決扱い: ${key}`);
        return _emptyLGInfo(key);
      }
      return {
        name:     name,
        calId:    String(r[1] || "").trim(),
        slackUid: uid,
        lineUrl:  String(r[3] || "").trim(),
      };
    }
  }
  return _emptyLGInfo(key);
}

function _emptyLGInfo(key) {
  const isUid = /^U[A-Z0-9]+$/.test(String(key).trim());
  return { name: isUid ? "" : String(key).trim(), calId: "", slackUid: isUid ? String(key).trim() : "", lineUrl: "" };
}

// ─────────────────────────────────────────
// 日時パース
// ─────────────────────────────────────────

function parseDatetime(dateStr, timeStr) {
  try {
    // v5.7+: Date オブジェクトを受けたら JST の "YYYY-MM-DD" に正規化
    let d;
    if (dateStr instanceof Date && !isNaN(dateStr.getTime())) {
      d = Utilities.formatDate(dateStr, "Asia/Tokyo", "yyyy-MM-dd");
    } else {
      d = String(dateStr).trim();
    }
    let t;
    if (timeStr instanceof Date && !isNaN(timeStr.getTime())) {
      t = Utilities.formatDate(timeStr, "Asia/Tokyo", "HH:mm");
    } else {
      t = String(timeStr).trim();
    }
    if (!d || !t) return null;

    const enM = d.match(/([A-Za-z]+)\s+(\d+),\s+(\d{4})/);
    if (enM) {
      const mo = ["january","february","march","april","may","june","july","august","september","october","november","december"].indexOf(enM[1].toLowerCase());
      if (mo >= 0) d = `${enM[3]}-${String(mo+1).padStart(2,"0")}-${String(enM[2]).padStart(2,"0")}`;
    }
    const jpF = d.match(/(\d{4})年(\d{1,2})月(\d{1,2})日/);
    if (jpF) d = `${jpF[1]}-${String(jpF[2]).padStart(2,"0")}-${String(jpF[3]).padStart(2,"0")}`;
    const jpS = d.match(/^(\d{1,2})月(\d{1,2})日$/);
    if (jpS) d = `${new Date().getFullYear()}-${String(jpS[1]).padStart(2,"0")}-${String(jpS[2]).padStart(2,"0")}`;
    d = d.replace(/\//g, "-");

    // 時刻正規化: "10:00" / "10時" / "10" などに対応
    t = t.replace(/時\s*(\d+)?分?/, (_, m) => ":" + (m || "00"));
    t = t.replace(/[：]/g, ":");
    if (/^\d{1,2}$/.test(t)) t = t.padStart(2, "0") + ":00";
    if (/^\d{1,2}:\d{2}$/.test(t)) t = t.split(":").map((x, i) => i === 0 ? x.padStart(2, "0") : x).join(":");

    const dt = new Date(`${d}T${t}:00+09:00`);
    return isNaN(dt.getTime()) ? null : dt;
  } catch(e) { Logger.log("[parseDatetime] " + e); return null; }
}

// ─────────────────────────────────────────
// 時刻または時刻範囲のパース
//   "10:00"        → { start:"10:00", end:null }
//   "10:00~19:00"  → { start:"10:00", end:"19:00" }  (〜・-・～ も許容)
// ─────────────────────────────────────────

// v5.7+: フリーフォーマット候補時間パーサ
//   "10:00~12:00" / "10-15" / "10時-15時" / "10時以降" / "午前中" / "午後" / "夕方"
function parseTimeOrRange(timeStr) {
  // v5.7+: Date オブジェクトが来たら JST の "HH:mm" に変換
  let s;
  if (timeStr instanceof Date && !isNaN(timeStr.getTime())) {
    s = Utilities.formatDate(timeStr, "Asia/Tokyo", "HH:mm");
  } else {
    s = String(timeStr || "").trim();
  }
  if (!s) return null;

  // v5.7+: 24時超は 23:59 にクランプ (JS Date "24:00" パース失敗対策)
  const HH = (h, m) => {
    let hh = parseInt(h, 10);
    let mm = parseInt(m || 0, 10);
    if (hh >= 24) { hh = 23; mm = 59; }
    if (hh < 0) hh = 0;
    return `${String(hh).padStart(2,"0")}:${String(mm).padStart(2,"0")}`;
  };
  const DAY_MAX_END = "23:15";  // 業務委託営業時間上限と整合
  const DAY_MIN_START = "09:00";

  // v5.7+: 末尾「~」/「〜」(右開放) → 「N時以降」と同義
  const mOpenEnd = s.match(/^(\d{1,2})\s*[時:]?\s*(\d{2})?\s*[〜～~]\s*$/);
  if (mOpenEnd) {
    return { start: HH(mOpenEnd[1], mOpenEnd[2]), end: DAY_MAX_END, isRange: true };
  }
  // v5.7+: 先頭「~17:00」(左開放) → 「N時まで」と同義
  const mOpenStart = s.match(/^\s*[〜～~]\s*(\d{1,2})\s*[時:]?\s*(\d{2})?\s*$/);
  if (mOpenStart) {
    return { start: DAY_MIN_START, end: HH(mOpenStart[1], mOpenStart[2]), isRange: true };
  }

  // 1. 明示的レンジ: "10:00~12:00" / "10-15" / "10:00-15:30" / "10時-15時" 等
  const mRange = s.match(/(\d{1,2})\s*[時:]?\s*(\d{2})?\s*[〜～~\-–ー]\s*(\d{1,2})\s*[時:]?\s*(\d{2})?/);
  if (mRange) {
    return {
      start:   HH(mRange[1], mRange[2]),
      end:     HH(mRange[3], mRange[4]),
      isRange: true,
    };
  }

  // 2. 「N時以降」 → N:00 〜 営業時間終端
  const mAfter = s.match(/(\d{1,2})\s*時?[:：]?\s*(\d{2})?\s*以降/);
  if (mAfter) {
    return { start: HH(mAfter[1], mAfter[2]), end: DAY_MAX_END, isRange: true };
  }

  // 3. 「N時まで」 → 営業時間下限 〜 N:00
  const mBefore = s.match(/(\d{1,2})\s*時?[:：]?\s*(\d{2})?\s*(?:まで|以前)/);
  if (mBefore) {
    return { start: DAY_MIN_START, end: HH(mBefore[1], mBefore[2]), isRange: true };
  }

  // 4. キーワード
  if (/午前(?:中)?/.test(s))   return { start: "09:00", end: "12:00", isRange: true };
  if (/午後/.test(s))          return { start: "13:00", end: DAY_MAX_END, isRange: true };
  if (/夕方/.test(s))          return { start: "17:00", end: DAY_MAX_END, isRange: true };
  if (/夜/.test(s))            return { start: "19:00", end: DAY_MAX_END, isRange: true };
  if (/終日|いつでも|全日/.test(s)) return { start: DAY_MIN_START, end: DAY_MAX_END, isRange: true };

  // 5. 単一時刻: "10:00" / "10時" / "10"
  const mSingle = s.match(/(\d{1,2})\s*[時:]?\s*(\d{2})?/);
  if (mSingle) {
    return { start: HH(mSingle[1], mSingle[2]), end: null, isRange: false };
  }

  return null;
}

// ─────────────────────────────────────────
// 除外キーワード取得（設定タブ優先・なければデフォルト）
// ─────────────────────────────────────────

function getExcludeKeywords() {
  const cfg = getConfig();
  const raw = String(cfg["CA判定 除外キーワード"] || "").trim();
  if (!raw) return DEFAULT_EXCLUDE_KEYWORDS;
  return raw.split(/[|｜、,\s]+/).map(s => s.trim()).filter(Boolean);
}

function _isBlockerEvent(event, keywords) {
  const title = String(event.getTitle() || "");
  return keywords.some(k => k && title.includes(k));
}

// v5.7+: Advanced Service の event オブジェクト用ブロッカー判定
function _isBlockerEventAdv(event, keywords) {
  const title = String(event.summary || "");
  return keywords.some(k => k && title.includes(k));
}

// v5.7+: CAの設定可能時間ルール判定
//   - @tokumori.co.jp ドメイン → 平日(月-金) 9:00-20:00 (社員)
//   - その他（業務委託/個人Gmail等）→ 全日 9:00-23:15
function _isCAAvailableInHours(calId, startDt, endDt) {
  const dow = startDt.getDay();  // 0=日, 6=土
  const startMin = startDt.getHours() * 60 + startDt.getMinutes();
  // 終了時刻は (start + 経過分) で算出（24:00ピッタリのケース対応）
  const endMin   = startMin + Math.round((endDt - startDt) / 60000);
  const isTokumori = String(calId || "").toLowerCase().endsWith("@tokumori.co.jp");
  if (isTokumori) {
    if (dow === 0 || dow === 6) return false;     // 土日NG
    if (startMin < 9 * 60) return false;          // 9時前NG
    if (endMin > 20 * 60) return false;           // 20時以降NG
  } else {
    if (startMin < 9 * 60) return false;          // 9時前NG
    if (endMin > 23 * 60 + 15) return false;      // 23:15以降NG
  }
  return true;
}

// ─────────────────────────────────────────
// CA空き照合（v3.3: 除外キーワードを適用）
// CAリスト列構成: A=CA名 / B=カレンダーID / C=Slack User ID
// ─────────────────────────────────────────

function checkCAAvailability(candidates) {
  const caList = _caListRows()
    .filter(r => r[0] && r[1] && String(r[4] || "").trim() === "アクティブ")
    .map(r => ({
      name:     String(r[0]).trim(),
      calId:    String(r[1]).trim(),
      slackUid: String(r[2] || "").trim(),
    }));
  Logger.log(`[CAAvail] アクティブCA数=${caList.length}`);

  const excludeKeywords = getExcludeKeywords();
  // v5.7.1: 除外キーワード未設定なら高速な Freebusy.query 経路を使う (API call 数 = 候補数 のみ)
  //         除外キーワードが設定されている場合は従来の Events.list でタイトル判定が必要
  const useFreeBusy = !excludeKeywords || excludeKeywords.length === 0;
  Logger.log(`[CAAvail] excludeKeywords=${JSON.stringify(excludeKeywords)} useFreeBusy=${useFreeBusy}`);

  const _parseEvDate = (d) => d.dateTime ? new Date(d.dateTime)
    : (d.date && /^\d{4}-\d{2}-\d{2}$/.test(d.date) ? new Date(...d.date.split("-").map((v,i)=> i===1? +v-1 : +v)) : new Date(d.date));

  // v5.7.1: Freebusy.query 経路 (1リクエストで全CA分の busy 配列を取得)
  const _fetchAllBusyViaFB = (timeMin, timeMax) => {
    try {
      const res = Calendar.Freebusy.query({
        timeMin: timeMin.toISOString(),
        timeMax: timeMax.toISOString(),
        items: caList.map(ca => ({ id: ca.calId })),
      });
      return caList.map(ca => {
        const entry = res.calendars && res.calendars[ca.calId];
        if (!entry || entry.errors) {
          Logger.log(`[FBQuery] ${ca.name} (${ca.calId}) error: ${JSON.stringify(entry?.errors)}`);
          return { ca, events: null };
        }
        return { ca, events: (entry.busy || []).map(b => ({ start: new Date(b.start), end: new Date(b.end) })) };
      });
    } catch(e) {
      Logger.log(`[FBQuery] 失敗 fallback to Events.list: ${e}`);
      return null;
    }
  };

  // 旧経路: 除外キーワード適用が必要な場合の Events.list ベース
  const _fetchCAEvents = (ca, timeMin, timeMax) => {
    try {
      const res = Calendar.Events.list(ca.calId, {
        timeMin: timeMin.toISOString(), timeMax: timeMax.toISOString(),
        singleEvents: true, maxResults: 500,
      });
      return (res.items || []).filter(ev => {
        if (ev.status === "cancelled") return false;
        if (ev.transparency === "transparent") return false;
        if (_isBlockerEventAdv(ev, excludeKeywords)) return false;
        if (Array.isArray(ev.attendees)) {
          const self = ev.attendees.find(a => a.email && a.email.toLowerCase() === ca.calId.toLowerCase());
          if (self && self.responseStatus === "declined") return false;
        }
        return true;
      }).map(ev => ({ start: _parseEvDate(ev.start), end: _parseEvDate(ev.end) }));
    } catch(e) {
      Logger.log(`[CalCheck] ${ca.name}: ${e}`);
      return null;
    }
  };

  // v5.7+: 本日+14日以降の候補は自動マッチング対象外 (CA未確定 = 日程調整中フロー)
  const _todayJST = new Date(); _todayJST.setHours(0, 0, 0, 0);
  const _maxAhead = new Date(_todayJST.getTime() + 14 * 24 * 3600 * 1000);

  for (const c of candidates) {
    if (!c.date || !c.time) { Logger.log(`[CAAvail] skip: date=${c.date} time=${c.time}`); continue; }
    const range = parseTimeOrRange(c.time);
    if (!range) continue;

    const rangeStart = parseDatetime(c.date, range.start);
    if (!rangeStart) { Logger.log(`[CAAvail] parseDatetime NULL: ${c.date} ${range.start}`); continue; }
    if (rangeStart >= _maxAhead) {
      Logger.log(`[CAAvail] skip (>14日先): ${c.date} ${c.time}`);
      continue;
    }
    const rangeEnd = range.end ? parseDatetime(c.date, range.end) : new Date(rangeStart.getTime() + getMeetingDurationMin() * 60 * 1000);
    if (!rangeEnd) continue;

    const lastStart = new Date(rangeEnd.getTime() - getMeetingDurationMin() * 60 * 1000);
    Logger.log(`[CAAvail] range ${rangeStart.toISOString()} — ${rangeEnd.toISOString()}`);

    // v5.7.1: 高速化 — Freebusy.query を優先 (1 API call で全CA分)。失敗時のみ Events.list にフォールバック
    let caWithEvents = null;
    if (useFreeBusy) caWithEvents = _fetchAllBusyViaFB(rangeStart, rangeEnd);
    if (!caWithEvents) {
      caWithEvents = caList.map(ca => ({ ca, events: _fetchCAEvents(ca, rangeStart, rangeEnd) }));
    }
    caWithEvents = caWithEvents.filter(x => x.events !== null);

    for (let t = rangeStart.getTime(); t <= lastStart.getTime(); t += getSlotStepMin() * 60 * 1000) {
      const startDt = new Date(t);
      const endDt   = new Date(t + getMeetingDurationMin() * 60 * 1000);

      for (const { ca, events } of caWithEvents) {
        if (!_isCAAvailableInHours(ca.calId, startDt, endDt)) continue;
        const overlap = events.some(ev => ev.start < endDt && ev.end > startDt);
        if (!overlap) {
          Logger.log(`[CAAvail] FREE ${ca.name} @ ${startDt.toISOString()}`);
          return { caName: ca.name, calId: ca.calId, slackUid: ca.slackUid, startDt, endDt };
        }
      }
    }
  }
  Logger.log(`[CAAvail] no free slot found`);
  return null;
}

// ─────────────────────────────────────────
// カレンダーイベント作成（Calendar Advanced Service 必須）
// ─────────────────────────────────────────

// v5.7+: カレンダーイベントの命名規則
//   `#34 @test_second｜27卒/Instagram｜CA石塚×LG佐藤`
function _shortHumanName(fullName) {
  if (!fullName) return "";
  // "CA005-石塚亘" / "999-佐藤篤也（テスト）" → "石塚亘" / "佐藤篤也（テスト）"
  return String(fullName).replace(/^(?:CA\d+|LG\d+|\d+)-/, "").trim();
}

// v5.7+: 既存Meet URL を再利用するイベント作成（代打受諾用）
//   reuseMeetUrl が指定されればそれを description に埋め込み、新Meet生成しない
function createCalendarEvent(calId, params, startDt, endDt, lgName, caName, rowNo, reuseMeetUrl) {
  try {
    const lineUrl = _getLineUrlForSns(params.sns);
    const description =
      `連携番号: #${rowNo ? _padNo(rowNo) : "-"}\n` +
      `担当CA: ${caName || "（確定後記載）"}\n` +
      `LG担当: ${lgName || params.lgMember}\n` +
      `学生: ${params.account}（${params.grade || ""}・${params.sns || ""}）\n` +
      `つなぎ方: ${params.reach || ""}\n` +
      `業界: ${params.industry || ""}\n` +
      `相談: ${params.topic || ""}\n` +
      (reuseMeetUrl ? `Meet: ${reuseMeetUrl}\n` : "") +
      `LINE追加URL: ${lineUrl}`;

    const _caShort = _shortHumanName(caName) || "未定";
    const _lgShort = _shortHumanName(lgName) || "未定";
    const _summary = `#${rowNo ? _padNo(rowNo) : "-"} @${params.account || "未定"}｜${params.grade || "-"}/${params.sns || "-"}｜CA${_caShort}×LG${_lgShort}`;

    const eventBody = {
      summary: _summary,
      description,
      start: { dateTime: startDt.toISOString(), timeZone: "Asia/Tokyo" },
      end:   { dateTime: endDt.toISOString(),   timeZone: "Asia/Tokyo" },
      attendees: [{ email: RECORD_EMAIL }],
    };
    if (reuseMeetUrl) {
      // 既存URLを使用 (Meet として表示・新生成しない / 競合関係なく強制作成)
      eventBody.conferenceData = {
        conferenceSolution: { key: { type: "hangoutsMeet" } },
        entryPoints: [{ entryPointType: "video", uri: reuseMeetUrl }],
        conferenceId: reuseMeetUrl.split("/").pop(),
      };
      eventBody.location = reuseMeetUrl;
    } else {
      eventBody.conferenceData = { createRequest: { requestId: Utilities.getUuid(), conferenceSolutionKey: { type: "hangoutsMeet" } } };
    }

    const event = Calendar.Events.insert(eventBody, calId, { conferenceDataVersion: 1, sendUpdates: "none" });

    const meetUrl = reuseMeetUrl || (event.conferenceData?.entryPoints || []).find(ep => ep.entryPointType === "video")?.uri || "";
    Logger.log(`[CreateEvent] OK id=${event.id} meet=${meetUrl}${reuseMeetUrl ? " (reused)" : ""}`);
    return { event, meetUrl };
  } catch(e) { Logger.log("[CreateEvent] ERROR: " + e + " stack: " + e.stack); return { event: null, meetUrl: "" }; }
}

// ─────────────────────────────────────────
// メイン処理
// ─────────────────────────────────────────

function scheduleMeeting(params) {
  const cfg     = getConfig();
  const channel = params._channel || cfg["Slack ワークフローチャンネルID"] || cfg["Slack テストチャンネルID"];
  const slackTs = params._slackTs || null;
  const ss      = SpreadsheetApp.getActiveSpreadsheet();
  // v5.0: 卒年から動的にシートを決定（必要なら自動作成）
  const sheetName = getSheetNameForGrade(params.grade);
  const sheet     = ss.getSheetByName(sheetName) || createGradeSheet(params.grade);

  // LG情報解決（UID/名前どちらでも）
  const lgInfo = getLGInfo(params.lgMember);
  const lgUid  = /^U[A-Z0-9]+$/.test(String(params.lgMember).trim()) ? String(params.lgMember).trim() : lgInfo.slackUid;
  // v5.7+: LGリスト未登録UIDは Slack users.info から表示名を解決（UID直書きを防止）
  const lgName = lgInfo.name || (lgUid ? _resolveSlackUserName(lgUid) : "") || params.lgMember;

  const dup = checkDuplicate(params.account, params.sns || "");
  if (dup.isDuplicate) {
    // v5.7+: 重複時はシートに一切書き込まず、LGに「登録不成立」を明示通知
    const msg =
      `⚠️ *面談登録は成立しませんでした（重複のため）*\n` +
      `学生: ${params.account}（${params.sns || "-"}経由）\n` +
      `既存登録: #${_padNo(dup.rowNo)}（登録日: ${formatDate(dup.date)} / シート: ${dup.sheetName || "-"}）\n` +
      `\n対応をお願いします:\n` +
      `・別学生の場合 → アカウント名/SNS種別を見直して再登録\n` +
      `・同じ学生の場合 → 既存スレッドで日程調整を継続`;
    // ① チャネル内 Ephemeral（投稿者本人にだけ即時表示）
    if (lgUid) sendEphemeral(channel, lgUid, msg);
    // ② LG への DM（Ephemeral 見落とし防止のフォールバック）
    if (lgUid) sendSlackMessage(lgUid, msg, null, null);
    // ③ ワークフロー投稿スレッド返信（チーム可視化）
    if (slackTs) sendSlackMessage(channel, msg, null, slackTs);
    return;
  }

  const candidates = [
    { date: params.date1, time: params.time1 },
    { date: params.date2, time: params.time2 },
    { date: params.date3, time: params.time3 },
  ].filter(c => c.date && c.time);

  // v5.7+: 2週間以上先の候補をリストアップ (LG通知用)
  const _today14 = new Date(); _today14.setHours(0, 0, 0, 0);
  _today14.setDate(_today14.getDate() + 14);
  const farCandidates = candidates.filter(c => {
    const range = parseTimeOrRange(c.time);
    if (!range) return false;
    const d = parseDatetime(c.date, range.start);
    return d && d >= _today14;
  });

  // v5.7+: 連携番号はカレンダーイベントタイトルにも入れるので、CA確定処理より前に確定させる
  const rowNo = getNextGlobalRowNo();

  // CAカレンダー照合（範囲入力にも対応）
  let confirmed = null, meetUrl = "";

  if (params._selfBooking) {
    // v5.7+: 兼任モード = LG=CA本人。CA検索をスキップして候補①で即確定
    const caInfo = getCAInfoByUid(lgUid);
    if (!caInfo) {
      const msg = `⚠️ *兼任モード: 登録不成立*\nCAリストにあなたのSlack UID(${lgUid || "-"})が登録されていません。\nCAリストのC列にUID、B列に自分のカレンダーIDを登録してください。`;
      if (lgUid) sendEphemeral(channel, lgUid, msg);
      if (slackTs) sendSlackMessage(channel, msg, null, slackTs);
      return;
    }
    if (!params.date1 || !params.time1) {
      const msg = "⚠️ 兼任モード: 候補日①と候補時間①は必須です";
      if (lgUid) sendEphemeral(channel, lgUid, msg);
      return;
    }
    const range  = parseTimeOrRange(params.time1);
    const startDt = parseDatetime(params.date1, range?.start);
    if (!startDt) {
      const msg = `⚠️ 兼任モード: 日時パース失敗（${params.date1} ${params.time1}）`;
      if (lgUid) sendEphemeral(channel, lgUid, msg);
      return;
    }
    const endDt = new Date(startDt.getTime() + getMeetingDurationMin() * 60 * 1000);
    const cal   = createCalendarEvent(caInfo.calId, params, startDt, endDt, lgName, caInfo.name, rowNo);
    confirmed = { caName: caInfo.name, calId: caInfo.calId, slackUid: caInfo.slackUid, startDt, endDt };
    meetUrl   = cal.meetUrl;
  } else {
    const caHasIds = _caListRows().some(r => r[1]);
    if (caHasIds) {
      // v5.7+: check→insert を LockService で直列化（同時設定によるダブルブッキング防止）
      const lock = LockService.getScriptLock();
      const gotLock = lock.tryLock(10000);
      if (!gotLock) {
        Logger.log(`[scheduleMeeting] LockService 取得失敗 → 日程調整中扱い`);
        // v5.7+: ロック失敗時にLGへephemeral通知（リトライ促し）
        if (lgUid) sendEphemeral(channel, lgUid, "⏳ 他のリクエスト処理中で取得待機がタイムアウトしました。日程調整中扱いになります。再度設定する場合は数秒後にお試しください。");
      } else {
        try {
          confirmed = checkCAAvailability(candidates);
          if (confirmed) {
            const calRes = createCalendarEvent(confirmed.calId, params, confirmed.startDt, confirmed.endDt, lgName, confirmed.caName, rowNo);
            // v5.7+: イベント作成失敗時は confirmed をリセットして「日程調整中」フェーズに戻す
            if (!calRes.event) {
              Logger.log(`[scheduleMeeting] カレンダー登録失敗 (${confirmed.caName}) → 日程調整中扱い`);
              // v5.7+: カレンダー書込失敗時にLGへephemeral通知（共有設定の確認促し）
              if (lgUid) sendEphemeral(channel, lgUid, `⚠️ ${confirmed.caName} のカレンダーに書き込めず日程調整中扱いになりました。CAのカレンダーが record@tokumori.co.jp に「予定の変更」権限で共有されているかご確認ください。`);
              confirmed = null;
              meetUrl = "";
            } else {
              meetUrl = calRes.meetUrl;
            }
          }
        } finally { lock.releaseLock(); }
      }
    }
  }

  const newRow       = sheet.getLastRow() + 1;
  const confirmedStr = confirmed ? `${formatDatetime(confirmed.startDt)}〜${formatTime(confirmed.endDt)}` : "";

  // v5.7+: SNS種別に応じた LINE追加用 LIFF URL
  const lineUrlForSns = _getLineUrlForSns(params.sns);

  // 申し送り文面をメモ列に記入
  const memo = confirmed ? [
    `【申し送り】`,
    `学生: @${params.account}（${params.grade || "-"}・${params.sns || "-"}）`,
    `日時: ${confirmedStr}`,
    `業界: ${params.industry || "-"} / 相談: ${params.topic || "-"}`,
    `つなぎ方: ${params.reach || "-"}`,
    `Meet: ${meetUrl || "-"}`,
    `LINE追加URL: ${lineUrlForSns}`,
    `担当LG: ${lgName}${lgUid ? ` (<@${lgUid}>)` : ""}`,
  ].filter(Boolean).join("\n") : `日程調整中（候補: ${candidates.map(c => `${c.date} ${c.time}`).join(" / ")}）`;

  sheet.getRange(newRow, 1, 1, 27).setValues([[
    rowNo,
    formatDatetime(new Date()),
    lgName,
    lineUrlForSns,
    params.account,
    params.grade    || "",
    params.sns      || "",
    params.industry || "",
    params.topic    || "",
    params.date1    || "",
    params.time1    || "",
    params.reach    || "",
    params.date2    || "",
    params.time2    || "",
    "",
    params.date3    || "",
    params.time3    || "",
    "",
    confirmedStr,
    confirmed ? confirmed.caName : "",
    meetUrl,
    confirmed ? "実施予定" : "日程調整中",
    false,
    false,
    lgUid || "",  // v5.7+: Y(25)列 = LG UID (no_show/cancel から確実にメンション解決するため)
    "",
    memo,
  ]]);

  sheet.getRange(newRow, 23).insertCheckboxes();
  sheet.getRange(newRow, 24).insertCheckboxes();
  // v5.7+: 連携番号(A列)は4桁ゼロ埋めで表示
  sheet.getRange(newRow, 1).setNumberFormat("0000");
  // v5.7+: 登録日時(B列)は yyyy/MM/dd HH:mm 表記
  sheet.getRange(newRow, 2).setNumberFormat("yyyy/MM/dd HH:mm");

  // 確認メッセージ: 元のワークフロー投稿にスレッド返信（1学生=1スレッド）
  const msgResult = sendConfirmationMessage(channel, params, confirmed, meetUrl, rowNo, lgInfo, slackTs);
  // v5.7+: Slack ts はテキスト形式で保存（数値化により小数部が丸められる事故防止）
  if (msgResult && msgResult.ts) {
    sheet.getRange(newRow, 26).setNumberFormat("@").setValue(msgResult.ts);
  }

  // v5.7+: 1設定=1スレッド統合
  // 親スレッド ts = (元のワークフロー投稿 slackTs があればそれ / なければ今投稿した確認メッセージ)
  const threadTs = slackTs || (msgResult && msgResult.ts) || null;

  // v5.7+: 重複削減のため Ephemeral 確認は廃止（スレッドの確定/調整中メッセージで十分）
  if (lgUid && !confirmed) {
    // CA空き無し or 14日超: 学生スレッドに調整依頼を投稿＋スタンプ付与（親メッセージにスレッド返信）
    const cgId      = cfg["CAユーザーグループID"];
    const caMention = cgId ? `<!subteam^${cgId}>` : "@CA";
    const lgMentionR = lgUid ? `<@${lgUid}>` : (lgInfo.name || lgName || "未登録");
    // 14日超候補があれば理由を明示
    const farNote = farCandidates.length
      ? `\n⚠️ ${lgMentionR} 候補のうち本日から2週間以上先の日程は自動調整対象外です:\n` +
        farCandidates.map(c => `  ・${c.date} ${c.time}`).join("\n") +
        `\n  → 2週間以内の代替候補を再回収するか、CAが手動で「📅 日程入力」してください。`
      : "";
    const reqText   =
      `:hourglass_flowing_sand: *#${_padNo(rowNo)} CA調整依頼* ${caMention}\n` +
      `学生: ${params.account}（${params.grade || ""}・${params.sns || ""}）\n` +
      `希望日程: ${candidates.map(c => `${c.date} ${c.time}`).join(" / ")}\n` +
      `業界: ${params.industry || "-"} / 相談: ${params.topic || "-"}\n` +
      `担当LG: ${lgMentionR}` +
      farNote +
      `\n\n→ 調整できる方はこのスレッドの「📅 日程入力」ボタンを押してください。`;
    sendSlackMessage(channel, reqText, null, threadTs);
    if (threadTs) addReaction(channel, threadTs, "hourglass_flowing_sand");
  }

  updateSettingCount(params.lgMember);
}

// ─────────────────────────────────────────
// Block Kit 確認メッセージ
// ─────────────────────────────────────────

function sendConfirmationMessage(channel, params, confirmed, meetUrl, rowNo, lgInfo, threadTs) {
  // メンション
  const isLgUid   = /^U[A-Z0-9]+$/.test(String(params.lgMember).trim());
  const lgMention = isLgUid ? `<@${params.lgMember}>` : (lgInfo?.slackUid ? `<@${lgInfo.slackUid}>` : (lgInfo?.name || params.lgMember));
  const caMention = confirmed?.slackUid ? `<@${confirmed.slackUid}>` : (confirmed?.caName || "未定");

  let bodyLines;
  let mentionPrefix = "";

  if (confirmed) {
    // 確定パターン: LG・CA・日程・Meet URL の順
    const dt = `${formatDatetime(confirmed.startDt)}〜${formatTime(confirmed.endDt)}`;
    bodyLines = [
      `🗓 *面談確定 #${_padNo(rowNo)}*`,
      ``,
      `・担当LG: ${lgMention}`,
      `・担当CA: ${caMention}`,
      `・日程: ${dt}`,
    ];
    if (meetUrl) bodyLines.push(`・Meet: ${meetUrl}`);
  } else {
    // 未確定パターン: CAグループメンション + LG + 希望日程
    const cfg = getConfig();
    const caGroupId = String(cfg["CAユーザーグループID"] || "").trim();
    mentionPrefix = caGroupId ? `<!subteam^${caGroupId}> ` : "@CA ";
    const candidates = [
      params.date1 && params.time1 ? `${params.date1} ${params.time1}` : null,
      params.date2 && params.time2 ? `${params.date2} ${params.time2}` : null,
      params.date3 && params.time3 ? `${params.date3} ${params.time3}` : null,
    ].filter(Boolean).join(" / ") || "未指定";
    bodyLines = [
      mentionPrefix.trim(),
      `📋 *面談登録 #${_padNo(rowNo)}*（CA未確定）`,
      ``,
      `・担当LG: ${lgMention}`,
      `・希望日程: ${candidates}`,
    ];
  }

  const mainText = bodyLines.join("\n");
  const blocks = [{ type: "section", text: { type: "mrkdwn", text: mainText } }];

  // ボタン (2行: LG/CA)
  const btnBlock = buildThreadButtons(rowNo, confirmed ? "実施予定" : "日程調整中");
  if (btnBlock) blocks.push(...btnBlock);

  return sendSlackMessage(channel, mainText, blocks, threadTs || null);
}

// ─────────────────────────────────────────
// Interactivity Webhook
// ─────────────────────────────────────────

// v5.7+: 管理用 GET エンドポイント（?action=fullCleanupAndCheck 等）
function doGet(e) {
  if (!_verifySlackSignature(e)) {
    return ContentService.createTextOutput("invalid").setMimeType(ContentService.MimeType.TEXT);
  }
  const action = (e?.parameter?.action || "").trim();
  const allowed = ["fullCleanupAndCheck", "cleanupTestData", "validateProductionReadiness", "debugCAAccess", "setAllTriggers", "applyRowNoFormatAllSheets", "listAllTabs", "deleteUnusedTabs", "applyDesignToAllTabs", "updateLGDashboard", "repaintMonotone", "applyMinimalDesign", "applyBakurakuDesign", "restoreGradeSheetHeaders", "buildWorkflowDiagram", "buildManualUnified", "buildLGDashboard", "buildSystemSpec", "buildFlowComparison", "buildManualUnifiedV2", "clearConfigCache", "buildManualV3", "buildWorkflowSwimlane", "buildFlowComparisonCards", "syncBotTokenToProperties", "setBotTokenProp", "diagBotToken", "backfillLGNames", "renderAvailabilityCalendar", "checkAllCACalendarAccess", "dumpCAEvents", "activateSatoCA", "postOperationPanel", "sendDailyReminders", "deleteJisseiSheet", "buildAllLGDashboards", "ensureGoalSheet", "buildMonthlyDashboard", "refreshThreadButtons", "cleanupOldJobs", "rematchRow", "dumpRowFreeSlots", "testCAWritePerm", "fixReactionsForRow", "announceConfirmation", "assignSubstituteByName", "resendCalendarInvite", "purgeThreadMessages", "repostCARequest", "inspectThread", "inviteCANoMeet", "setMeetUrl", "autoRematchStalled"];
  if (allowed.includes(action)) {
    try {
      // eslint-disable-next-line
      const r = (this[action] || globalThis[action])(e);
      return ContentService.createTextOutput(`OK: ${action}\n${JSON.stringify(r || "done")}`).setMimeType(ContentService.MimeType.TEXT);
    } catch (err) {
      return ContentService.createTextOutput(`ERROR: ${err}\n${err.stack || ""}`).setMimeType(ContentService.MimeType.TEXT);
    }
  }
  return ContentService.createTextOutput(`ready (actions: ${allowed.join(", ")})`).setMimeType(ContentService.MimeType.TEXT);
}

function doPost(e) {
  // v5.7+: ホットパス最速化のため、ログはメモリにバッファし最後に1回だけ書き込む
  const _dbgStart = Date.now();
  const _dbgBuf = [];
  const _dbgLog = (msg) => { _dbgBuf.push([new Date(), `${Date.now() - _dbgStart}ms`, msg]); };
  const _dbgFlush = () => {
    try {
      if (!_dbgBuf.length) return;
      const ss = SpreadsheetApp.getActiveSpreadsheet();
      let sh = ss.getSheetByName("_debug_doPost");
      if (!sh) sh = ss.insertSheet("_debug_doPost");
      sh.getRange(sh.getLastRow() + 1, 1, _dbgBuf.length, 3).setValues(_dbgBuf);
    } catch(_) {}
  };

  try {
    if (!_verifySlackSignature(e)) {
      return ContentService.createTextOutput("invalid signature").setMimeType(ContentService.MimeType.TEXT);
    }

    // ★ Slash Command（最優先パス）: 例 /面談登録 — body は form-encoded で token=...&command=...&trigger_id=...
    const rawBody = e.postData?.contents || "";
    if (!rawBody.startsWith("payload=") && rawBody.includes("command=") && rawBody.includes("trigger_id=")) {
      const params = {};
      rawBody.split("&").forEach(kv => {
        const i = kv.indexOf("=");
        if (i > 0) params[decodeURIComponent(kv.slice(0, i))] = decodeURIComponent(kv.slice(i + 1).replace(/\+/g, " "));
      });
      const cmd = (params.command || "").trim();
      if (cmd === "/面談登録" || cmd === "/meeting" || cmd === "/lgca") {
        const view = _buildModalRegister({
          channel: params.channel_id || "",
          threadTs: "",
          userId: params.user_id || "",
        });
        const res = _slackViewsOpenFast(params.trigger_id, view);
        _dbgLog(`slash cmd=${cmd} views.open ok=${res?.ok} err=${res?.error || ""} elapsed=${Date.now() - _dbgStart}ms`);
        _dbgFlush();
        return ContentService.createTextOutput("").setMimeType(ContentService.MimeType.TEXT);
      }
      return ContentService.createTextOutput("").setMimeType(ContentService.MimeType.TEXT);
    }

    if (e.postData?.contents?.startsWith("payload=")) {
      const payload = JSON.parse(decodeURIComponent(e.postData.contents.slice("payload=".length)));

      // ★ ショートカット = 最優先パス（3秒ルール厳守。シートアクセス等は一切しない）
      if (payload.type === "shortcut" || payload.type === "message_action") {
        const cb = payload.callback_id || "";
        const _uidShortcut = payload.user?.id;
        // ショートカット → 対応 open_modal_xxx と同じ権限チェック
        const _shortcutToAction = {
          "shortcut_register":   "open_modal_register",
          "shortcut_member_add": "open_modal_member_add",
        };
        const _equivAction = _shortcutToAction[cb];
        if (_equivAction) {
          const perm = _isAllowed(_uidShortcut, _equivAction);
          if (!perm.ok) {
            try {
              sendSlackMessage(_uidShortcut, `⚠️ この操作は ${perm.allowed.join("/")} 限定です。あなたの役職: ${(perm.roles.length ? perm.roles.join(",") : "未登録")}`, null, null);
            } catch(_) {}
            return ContentService.createTextOutput("").setMimeType(ContentService.MimeType.TEXT);
          }
        }
        let view = null;
        if (cb === "shortcut_register") {
          view = _buildModalRegister({
            channel: payload.channel?.id || "",
            threadTs: "",
            userId: payload.user?.id || "",
          });
        } else if (cb === "shortcut_member_add") {
          view = _buildModalMemberAdd();
        }
        if (view) {
          const res = _slackViewsOpenFast(payload.trigger_id, view);
          _dbgLog(`shortcut cb=${cb} views.open ok=${res?.ok} err=${res?.error || ""} elapsed=${Date.now() - _dbgStart}ms`);
          _dbgFlush();
        }
        return ContentService.createTextOutput("").setMimeType(ContentService.MimeType.TEXT);
      }

      // block_actions: モーダル起動も最速で
      if (payload.type === "block_actions") {
        const actionId = payload.actions?.[0]?.action_id || "";
        if (actionId.startsWith("open_modal_")) {
          openModal(actionId, payload);
          _dbgLog(`block_actions ${actionId} elapsed=${Date.now() - _dbgStart}ms`);
          _dbgFlush();
          return ContentService.createTextOutput("").setMimeType(ContentService.MimeType.TEXT);
        }
        handleButtonAction(payload);
        return ContentService.createTextOutput("").setMimeType(ContentService.MimeType.TEXT);
      }

      if (payload.type === "view_submission") {
        const ack = handleViewSubmission(payload);
        return ContentService.createTextOutput(JSON.stringify(ack || {}))
          .setMimeType(ContentService.MimeType.JSON);
      }

      handleButtonAction(payload);
      return ContentService.createTextOutput("").setMimeType(ContentService.MimeType.TEXT);
    }

    const body = JSON.parse(e.postData?.contents || "{}");
    if (body.type === "url_verification") {
      return ContentService.createTextOutput(body.challenge).setMimeType(ContentService.MimeType.TEXT);
    }
    // v5.7+: Events API（app_home_opened など）
    if (body.type === "event_callback" && body.event) {
      const ev = body.event;
      if (ev.type === "app_home_opened" && ev.user) {
        _publishHomeView(ev.user);
        _dbgLog(`app_home_opened user=${ev.user} elapsed=${Date.now() - _dbgStart}ms`);
        _dbgFlush();
      }
      return ContentService.createTextOutput("").setMimeType(ContentService.MimeType.TEXT);
    }
    handleButtonAction(body);
  } catch(err) { Logger.log("[doPost] " + err + " stack: " + err.stack); }
  return ContentService.createTextOutput("OK").setMimeType(ContentService.MimeType.TEXT);
}

// v5.7+: App Home タブの内容を更新（views.publish）
function _publishHomeView(userId) {
  const props = PropertiesService.getScriptProperties();
  let token = props.getProperty("SLACK_BOT_TOKEN");
  if (!token) token = getConfig()["Slack Bot Token"];
  if (!token) return { ok: false, error: "bot_token_missing" };

  const view = {
    type: "home",
    blocks: [
      { type: "header", text: { type: "plain_text", text: "LG/CA 連携 ホーム" } },
      { type: "section", text: { type: "mrkdwn", text: "面談登録・運用操作はこちらから。" } },
      { type: "divider" },
      { type: "section", text: { type: "mrkdwn", text: "*📝 面談登録*\n学生面談を新規登録します。" } },
      { type: "actions", elements: [
        { type: "button", text: { type: "plain_text", text: "📝 新規面談登録" }, style: "primary", action_id: "open_modal_register", value: "register" },
      ]},
      { type: "divider" },
      { type: "section", text: { type: "mrkdwn", text: "*🔗 関連リンク*" } },
      { type: "context", elements: [
        { type: "mrkdwn", text: "<https://docs.google.com/spreadsheets/d/1NmJXivFLnPC-Nb50ANZx2gZWT4vPneOm7XVF-B4t698/edit|📊 連携シート> ｜ コマンド `/面談登録` でも起動可能" },
      ]},
      { type: "divider" },
      { type: "context", elements: [
        { type: "mrkdwn", text: "LG/CA 連携 v5.7  ｜  日程入力・再回収・重複報告は各学生スレッド内のボタンから" },
      ]},
    ],
  };

  try {
    const res = UrlFetchApp.fetch("https://slack.com/api/views.publish", {
      method: "post", contentType: "application/json",
      headers: { Authorization: "Bearer " + token },
      payload: JSON.stringify({ user_id: userId, view }),
      muteHttpExceptions: true,
    });
    const r = JSON.parse(res.getContentText());
    if (!r.ok) Logger.log("[views.publish] " + r.error);
    return r;
  } catch(err) {
    return { ok: false, error: "fetch_exception", detail: String(err) };
  }
}

// v5.7+: ショートカット高速版 views.open — Script Properties から直読み（シートアクセス回避）
function _slackViewsOpenFast(triggerId, view) {
  const props = PropertiesService.getScriptProperties();
  let token = props.getProperty("SLACK_BOT_TOKEN");
  if (!token) {
    // 初回フォールバック: シートから読み出してキャッシュ
    token = getConfig()["Slack Bot Token"];
    if (token) props.setProperty("SLACK_BOT_TOKEN", token);
  }
  if (!token) return { ok: false, error: "bot_token_missing" };
  try {
    const res = UrlFetchApp.fetch("https://slack.com/api/views.open", {
      method: "post", contentType: "application/json",
      headers: { Authorization: "Bearer " + token },
      payload: JSON.stringify({ trigger_id: triggerId, view }),
      muteHttpExceptions: true,
    });
    return JSON.parse(res.getContentText());
  } catch(err) {
    return { ok: false, error: "fetch_exception", detail: String(err) };
  }
}

// ─────────────────────────────────────────
// v5.7+: 役職ベースの操作権限制御
// ─────────────────────────────────────────
const ADMIN_UIDS = ["U08SGGC5QR4", "U06NB1UFYN7", "U07TWUDKUCW"]; // 佐藤篤也 / 渡邊駿 / 山口扇世
const ACTION_ALLOWED_ROLES = {
  "open_modal_register":   ["LG"],
  "open_modal_recollect":  ["LG"],
  "cancel_meeting":        ["LG"],
  "no_show":               ["CA"],
  "open_modal_dateinput":  ["CA"],
  "open_modal_duplicate":  ["CA"],
  "open_modal_member_add": ["LG", "CA"], // 全員(LG or CA)
  "open_modal_substitute": ["CA"],       // 代打依頼 = CA限定
  "accept_substitute":     ["CA"],       // 「✋ 代わります」も CA限定
};

function _getUserRoles(uid) {
  if (!uid) return [];
  // v5.7+: 5分キャッシュで sheet read の重さを回避 (trigger_id 失効防止)
  const cacheKey = "__roles_" + uid;
  try {
    const c = CacheService.getScriptCache().get(cacheKey);
    if (c) return JSON.parse(c);
  } catch(_) {}
  const roles = new Set();
  if (ADMIN_UIDS.includes(uid)) roles.add("admin");
  const caRow = _caListRows().find(r => String(r[2] || "").trim() === uid);
  if (caRow) {
    roles.add("CA");
    const email = String(caRow[1] || "").toLowerCase();
    if (email.endsWith("@tokumori.co.jp")) roles.add("admin");
  }
  const lgRow = _lgListRows().find(r => String(r[2] || "").trim() === uid);
  if (lgRow) roles.add("LG");
  if (roles.has("CA") && roles.has("LG")) roles.add("兼任");
  const arr = Array.from(roles);
  try { CacheService.getScriptCache().put(cacheKey, JSON.stringify(arr), 300); } catch(_) {}
  return arr;
}

function _isAllowed(uid, actionId) {
  const roles = _getUserRoles(uid);
  if (roles.includes("admin")) return { ok: true };
  const allowed = ACTION_ALLOWED_ROLES[actionId];
  if (!allowed) return { ok: true };
  const matched = allowed.some(r => roles.includes(r));
  if (matched) return { ok: true };
  return { ok: false, allowed, roles };
}

// ─────────────────────────────────────────
// v5.7+: メンバーシート(単一シート / 左:CA / 右:LG)
// 列 A-G = CAブロック、列 H = セパレータ、列 I-N = LGブロック
// 旧 CAリスト / LGリスト 形式に変換して返す（呼び出し側のコード変更を最小化）
// ─────────────────────────────────────────
const MEMBER_SHEET = "メンバー";
// 列インデックス（0-based）
const M_CA_START = 0; // A
const M_CA_COLS = 7;  // A-G
const M_LG_START = 8; // I
const M_LG_COLS = 6;  // I-N
// ヘッダ占有行数（タイトル行 + 列ヘッダ行）
const M_HEADER_ROWS = 2;

// CAブロック → 旧形式 [A=CA001-名前, B=メール, C=UID, D=区分, E=ステータス]
// v5.7+: 5分キャッシュで sheet read を高速化 (trigger_id 失効防止)
function _caListRows() {
  try {
    const c = CacheService.getScriptCache().get("__ca_rows__");
    if (c) return JSON.parse(c);
  } catch(_) {}
  const sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(MEMBER_SHEET);
  if (!sh) return [];
  const last = sh.getLastRow();
  if (last <= M_HEADER_ROWS) return [];
  const data = sh.getRange(M_HEADER_ROWS + 1, M_CA_START + 1, last - M_HEADER_ROWS, M_CA_COLS).getValues();
  const rows = data
    .filter(r => r[0] && r[1])
    .map(r => [
      `${String(r[0]).trim()}-${String(r[1]).trim()}`,
      String(r[2] || "").trim(),
      String(r[3] || "").trim(),
      String(r[4] || "").trim(),
      String(r[5] || "").trim(),
    ]);
  try { CacheService.getScriptCache().put("__ca_rows__", JSON.stringify(rows), 300); } catch(_) {}
  return rows;
}

// LGブロック → 旧形式 [A=LG001-名前, B=空, C=UID, D=空, E=ステータス]
function _lgListRows() {
  try {
    const c = CacheService.getScriptCache().get("__lg_rows__");
    if (c) return JSON.parse(c);
  } catch(_) {}
  const sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(MEMBER_SHEET);
  if (!sh) return [];
  const last = sh.getLastRow();
  if (last <= M_HEADER_ROWS) return [];
  const data = sh.getRange(M_HEADER_ROWS + 1, M_LG_START + 1, last - M_HEADER_ROWS, M_LG_COLS).getValues();
  const rows = data
    .filter(r => r[0] && r[1])
    .map(r => [
      `${String(r[0]).trim()}-${String(r[1]).trim()}`,
      "",
      String(r[2] || "").trim(),
      "",
      String(r[4] || "").trim(),
    ]);
  try { CacheService.getScriptCache().put("__lg_rows__", JSON.stringify(rows), 300); } catch(_) {}
  return rows;
}

// v5.7+: view_submission 即時ACK→裏で処理 のキュー機構（3秒タイムアウト回避）
function _enqueueVSJob(callbackId, params) {
  // 連打防止: 同一submit (callback + rowNo + 主要パラメータ) を 15秒内は1回のみ
  try {
    const dedupKey = `__vs_${callbackId}_${params.rowNo || ""}_${params.account || ""}_${params.requesterId || params.userId || ""}`;
    const cache = CacheService.getScriptCache();
    if (cache.get(dedupKey)) {
      Logger.log(`[VS dedup] ${dedupKey} → skip enqueue`);
      const uid = params.requesterId || params.userId;
      if (uid) { try { sendSlackMessage(uid, "⏳ 直前の操作を処理中です。完了をお待ちください", null, null); } catch(_) {} }
      return;
    }
    cache.put(dedupKey, "1", 15);
  } catch(_) {}

  // v5.7.1: まず即時インライン実行を試みる (Freebusy.query 経由でマッチングが高速化したため大半は3〜5秒で完了)
  //          失敗時のみ Properties + トリガー1分後実行にフォールバック
  const t0 = Date.now();
  try {
    _processVSJob(callbackId, params);
    Logger.log(`[VS inline] ${callbackId} done in ${Date.now() - t0}ms`);
    return;
  } catch(e) {
    Logger.log(`[VS inline] ${callbackId} failed: ${e}\n${e.stack || ""} → queue fallback`);
  }

  // フォールバック: Properties + 1分後トリガー
  const jobKey = "vsJob_" + Date.now() + "_" + Math.random().toString(36).slice(2, 8);
  PropertiesService.getScriptProperties().setProperty(jobKey, JSON.stringify({ cb: callbackId, params }));
  const exists = ScriptApp.getProjectTriggers().some(t => t.getHandlerFunction() === "_drainVSQueue");
  if (!exists) {
    ScriptApp.newTrigger("_drainVSQueue").timeBased().after(1).create();
  }
}

function _drainVSQueue() {
  const props = PropertiesService.getScriptProperties();
  const keys = props.getKeys().filter(k => k.startsWith("vsJob_")).sort();
  keys.forEach(k => {
    let raw = null;
    try { raw = props.getProperty(k); } catch(_) {}
    try { props.deleteProperty(k); } catch(_) {}
    if (!raw) return;
    try {
      const { cb, params } = JSON.parse(raw);
      _processVSJob(cb, params);
    } catch(e) {
      Logger.log(`[drainVSQueue] ${k}: ${e}\n${e.stack || ""}`);
    }
  });
  // 自分自身のトリガーを掃除（再エンキュー時に新規登録される）
  ScriptApp.getProjectTriggers().forEach(t => {
    if (t.getHandlerFunction() === "_drainVSQueue") {
      try { ScriptApp.deleteTrigger(t); } catch(_) {}
    }
  });
}

function _processVSJob(callbackId, params) {
  if (callbackId === "modal_register") {
    scheduleMeeting(params);
  } else if (callbackId === "modal_dateinput") {
    applyDateInput(params);
  } else if (callbackId === "modal_recollect") {
    applyRecollect(params);
  } else if (callbackId === "modal_duplicate") {
    handleDuplicateReport(params);
  } else if (callbackId === "modal_substitute") {
    handleSubstituteRequest(params);
  } else if (callbackId === "modal_member_add") {
    const result = addMember(params);
    if (params.requesterId) {
      const msg = result.ok
        ? `✅ メンバー追加完了\n*${result.id}* ${result.name} (${params.role})\n→ メンバーシートに追加されました`
        : `⚠️ メンバー追加失敗: ${result.error}`;
      try { sendSlackMessage(params.requesterId, msg, null, null); } catch(_) {}
    }
  } else {
    Logger.log(`[processVSJob] 未対応 callbackId=${callbackId}`);
  }
}

// v5.7+: メンバーシートへの追記 (Slackユーザー → 名前/メール自動resolve + ID自動採番)
// 役割=兼任 の場合は CA/LG 両方のシートに追加
function addMember(params) {
  const { role, userId, division, email, status, memo } = params;
  if (!role || !userId) return { ok: false, error: "役割とユーザーは必須です" };
  // Slack users.info を1回だけ呼んで 名前 + メール を同時取得
  let name = "";
  let resolvedEmail = email;
  try {
    const token = PropertiesService.getScriptProperties().getProperty("SLACK_BOT_TOKEN") || getConfig()["Slack Bot Token"];
    if (token) {
      const res = UrlFetchApp.fetch(`https://slack.com/api/users.info?user=${userId}`, {
        headers: { Authorization: "Bearer " + token }, muteHttpExceptions: true,
      });
      const r = JSON.parse(res.getContentText());
      if (r.ok && r.user) {
        name = _trimSlackDisplayName(r.user.profile?.display_name || r.user.profile?.real_name || r.user.real_name || "");
        if (!resolvedEmail) resolvedEmail = (r.user.profile?.email || "").trim();
      }
    }
  } catch(_) {}
  if (!name) name = _resolveSlackUserName(userId) || ""; // フォールバック
  if (!name) return { ok: false, error: "Slackユーザー名取得失敗" };
  if ((role === "CA" || role === "兼任") && !resolvedEmail) {
    return { ok: false, error: "CA/兼任 はメール必須 (Slack profile に未設定の場合は手入力してください)" };
  }

  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sh = ss.getSheetByName(MEMBER_SHEET);
  if (!sh) return { ok: false, error: "メンバーシートが見つかりません" };

  // 既存ID解析 + 各ブロックの空き先頭行検出
  const last = Math.max(sh.getLastRow(), M_HEADER_ROWS);
  const caCol = sh.getRange(M_HEADER_ROWS + 1, M_CA_START + 1, Math.max(last - M_HEADER_ROWS, 1), 1).getValues();
  const lgCol = sh.getRange(M_HEADER_ROWS + 1, M_LG_START + 1, Math.max(last - M_HEADER_ROWS, 1), 1).getValues();

  const _maxN = (col, prefix) => {
    let max = 0;
    col.forEach(([v]) => {
      const m = String(v || "").match(new RegExp("^" + prefix + "(\\d{3})$"));
      if (m) {
        const n = parseInt(m[1], 10);
        if (n < 900) max = Math.max(max, n);
      }
    });
    return max;
  };
  // 各ブロックの「最後の埋まっている行」index (0-based, ヘッダ込みでない)
  const _lastFilled = (col) => {
    let lastIdx = -1;
    col.forEach((row, i) => { if (row[0]) lastIdx = i; });
    return lastIdx;
  };

  const ids = [];
  if (role === "CA" || role === "兼任") {
    const newId = "CA" + String(_maxN(caCol, "CA") + 1).padStart(3, "0");
    const targetRowIdx = _lastFilled(caCol) + 1; // 0-based after header
    const targetRow = M_HEADER_ROWS + 1 + targetRowIdx; // 1-based sheet row
    sh.getRange(targetRow, M_CA_START + 1, 1, M_CA_COLS).setValues([[
      newId, name, resolvedEmail || "", userId, division || "", status || "共有待ち", memo || (role === "兼任" ? "LGと兼任" : "")
    ]]);
    ids.push(newId);
    Logger.log(`[addMember CA] ${newId} ${name} row=${targetRow}`);
  }
  if (role === "LG" || role === "兼任") {
    const newId = "LG" + String(_maxN(lgCol, "LG") + 1).padStart(3, "0");
    const targetRowIdx = _lastFilled(lgCol) + 1;
    const targetRow = M_HEADER_ROWS + 1 + targetRowIdx;
    sh.getRange(targetRow, M_LG_START + 1, 1, M_LG_COLS).setValues([[
      newId, name, userId, division || "", status || "アクティブ", memo || (role === "兼任" ? "CAと兼任" : "")
    ]]);
    ids.push(newId);
    Logger.log(`[addMember LG] ${newId} ${name} row=${targetRow}`);
  }
  return { ok: true, id: ids.join(" + "), name };
}

// v5.7+: Slack表示名を「日本語名のみ」に整形 (メンバー表との統一)
//   例: "松﨑 雄飛/Matsuzaki Yuhi/CA/社会人" → "松﨑 雄飛"
//       "佐藤 篤也/Sato Atsuya"             → "佐藤 篤也"
//       "金田 夏輝"                          → "金田 夏輝"
//   半角スペースは詰める: "松﨑 雄飛" → "松﨑雄飛"
function _trimSlackDisplayName(s) {
  const t = String(s || "").trim();
  if (!t) return "";
  const first = t.split("/")[0].trim();
  // 半角スペース1つで分割されている日本語名を詰める (例: "松﨑 雄飛" → "松﨑雄飛")
  return first.replace(/\s+/g, "");
}

// v5.7+: Slack users.info で表示名を取得（display_name → real_name → 失敗時 空）。1時間キャッシュ。
function _resolveSlackUserName(uid) {
  if (!uid || !/^U[A-Z0-9]+$/.test(uid)) return "";
  const cacheKey = "__slack_user_v3_" + uid;
  try {
    const cache = CacheService.getScriptCache();
    const c = cache.get(cacheKey);
    if (c !== null) return c;
  } catch(_) {}
  const token = PropertiesService.getScriptProperties().getProperty("SLACK_BOT_TOKEN") || getConfig()["Slack Bot Token"];
  if (!token) return "";
  try {
    const res = UrlFetchApp.fetch(`https://slack.com/api/users.info?user=${uid}`, {
      method: "get",
      headers: { Authorization: "Bearer " + token },
      muteHttpExceptions: true,
    });
    const r = JSON.parse(res.getContentText());
    if (r.ok && r.user) {
      const raw = (r.user.profile?.display_name || "").trim() || (r.user.profile?.real_name || "").trim() || (r.user.real_name || "").trim() || "";
      const name = _trimSlackDisplayName(raw);
      try { CacheService.getScriptCache().put(cacheKey, name, 3600); } catch(_) {}
      return name;
    }
    Logger.log(`[users.info ${uid}] ${r.error || "no_user"}`);
  } catch(err) { Logger.log("[users.info] " + err); }
  return "";
}

// 既存行のC列(LGメンバー)が UID or 未トリム名 だったら、適切な形に整形
function backfillLGNames() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const targets = ["連携メイン_27卒", "連携メイン_28卒", "連携メイン_29卒", "連携メイン_30卒"];
  const summary = [];
  targets.forEach(name => {
    const sh = ss.getSheetByName(name);
    if (!sh) return;
    const last = sh.getLastRow();
    if (last < 2) return;
    const range = sh.getRange(2, 3, last - 1, 1);
    const vals  = range.getValues();
    let changed = 0;
    for (let i = 0; i < vals.length; i++) {
      const v = String(vals[i][0] || "").trim();
      if (!v) continue;
      if (/^U[A-Z0-9]+$/.test(v)) {
        // UID → 名前解決
        const info = getLGInfo(v);
        const display = info.name || _resolveSlackUserName(v);
        if (display) { vals[i][0] = display; changed++; }
      } else if (v.includes("/") || /\s/.test(v)) {
        // "/" や スペースを含む形式 → 日本語名のみに統一
        const trimmed = _trimSlackDisplayName(v);
        if (trimmed && trimmed !== v) { vals[i][0] = trimmed; changed++; }
      }
    }
    if (changed) range.setValues(vals);
    summary.push(`${name}: ${changed}件更新`);
  });
  Logger.log("[backfillLGNames] " + summary.join(" / "));
  return summary.join(" / ") || "対象なし";
}

// Bot Token を Script Properties に同期する手動関数（設定変更時に1回呼ぶ）
function syncBotTokenToProperties() {
  const token = getConfig()["Slack Bot Token"];
  if (!token) { Logger.log("[syncBotToken] Slack Bot Token がシートに無い"); return "sheet_empty"; }
  PropertiesService.getScriptProperties().setProperty("SLACK_BOT_TOKEN", token);
  Logger.log("[syncBotToken] OK length=" + token.length);
  return "ok len=" + token.length;
}

// v5.7+: 既存の日程調整中行をシート候補時間で再マッチング (?action=rematchRow&no=55)
function rematchRow(e) {
  const rowNoQ = parseInt(e?.parameter?.no || "", 10);
  if (!rowNoQ) return "no パラメータが必要 (例: ?action=rematchRow&no=55)";
  return _doRematch(rowNoQ, "再マッチング (admin)");
}

// v5.7.2: 再マッチのコアロジック (rematchRow / autoRematchStalled から共用)
//   reporterLabel: スレッド通知の「報告者」表記
//   戻り値: 結果メッセージ文字列。成立時は "...再マッチ成立..." を含む
function _doRematch(rowNoQ, reporterLabel) {
  const found = findRowByNo(rowNoQ);
  if (!found) return `#${_padNo(rowNoQ)} 見つかりません`;
  const { sheet, data, rowIdx } = found;
  const r = data[rowIdx];
  const phase = String(r[21] || "").trim();
  if (phase !== "日程調整中") return `#${_padNo(rowNoQ)} は ${phase} なのでスキップ (日程調整中のみ対象)`;
  // v5.7+: セル値が Date オブジェクトの場合に備え raw を渡す (parseDatetime/parseTimeOrRange 側で正規化)
  const candidates = [
    { date: r[9],  time: r[10] },
    { date: r[12], time: r[13] },
    { date: r[15], time: r[16] },
  ].filter(c => c.date && c.time);
  if (!candidates.length) return `#${_padNo(rowNoQ)} 候補なし`;
  const confirmed = checkCAAvailability(candidates);
  if (!confirmed) return `#${_padNo(rowNoQ)} 再マッチ結果: 空きCAなし`;
  // カレンダー作成 + シート更新
  const lgKey = String(r[2] || "").trim();
  const lgInfo = getLGInfo(lgKey);
  const cal2 = createCalendarEvent(confirmed.calId, {
    account: String(r[4] || ""), grade: String(r[5] || ""), sns: String(r[6] || ""),
    industry: String(r[7] || ""), topic: String(r[8] || ""), reach: String(r[11] || ""),
    lgMember: lgKey,
  }, confirmed.startDt, confirmed.endDt, lgInfo.name || lgKey, confirmed.caName, rowNoQ);
  // v5.7+: カレンダーイベント作成失敗時はシート更新せず終了 (実施予定にした上でMeet空欄の不整合を防ぐ)
  if (!cal2.event) {
    return `#${_padNo(rowNoQ)} エラー: ${confirmed.caName} のカレンダーへイベント作成失敗 (権限不足/Meet生成不可の可能性)。シートは 日程調整中 のまま。`;
  }
  const confStr = `${formatDatetime(confirmed.startDt)}〜${formatTime(confirmed.endDt)}`;
  sheet.getRange(rowIdx + 1, 19, 1, 4).setValues([[confStr, confirmed.caName, cal2.meetUrl, "実施予定"]]);

  // v5.7+: 申し送りメモ列(AA=27)を applyDateInput と同様に更新
  const _account = String(r[4] || ""), _grade = String(r[5] || ""), _sns = String(r[6] || "");
  const _industry = String(r[7] || ""), _topic = String(r[8] || ""), _reach = String(r[11] || "");
  const memoText = [
    `【申し送り（CA調整後・再マッチング）】`,
    `学生: @${_account}（${_grade || "-"}・${_sns || "-"}）`,
    `日時: ${confStr}`,
    `業界: ${_industry || "-"} / 相談: ${_topic || "-"}`,
    `つなぎ方: ${_reach || "-"}`,
    `Meet: ${cal2.meetUrl || "-"}`,
    `担当LG: ${lgInfo.name || lgKey}`,
    `担当CA: ${confirmed.caName}${confirmed.slackUid ? ` (<@${confirmed.slackUid}>)` : ""}`,
  ].join("\n");
  sheet.getRange(rowIdx + 1, 27).setValue(memoText);

  // スレッド通知: applyDateInput と同じ命名規則 (formatNotification + buildThreadButtons)
  const slackTs = String(r[25] || "").trim();
  const channel = getConfig()["Slack ワークフローチャンネルID"];
  if (slackTs && channel) {
    const _lgUid = /^U[A-Z0-9]+$/.test(lgKey) ? lgKey : (lgInfo && lgInfo.slackUid);
    const _notifText = formatNotification({
      statusEmoji: "✅", title: "調整完了", rowNo: rowNoQ,
      account: _account, grade: _grade, sns: _sns,
      lgUid: _lgUid, caUid: confirmed.slackUid, caName: confirmed.caName,
      detail: `日時: ${confStr}\nMeet: ${cal2.meetUrl}`,
      reporter: reporterLabel || "再マッチング",
    });
    const _blocks = [{ type: "section", text: { type: "mrkdwn", text: _notifText } }];
    const _btnBlock = buildThreadButtons(rowNoQ, "実施予定");
    if (_btnBlock) _blocks.push(..._btnBlock);
    sendSlackMessage(channel, _notifText, _blocks, slackTs);
    // スタンプ切替: ⏳/✋ を外して ✅ を付与
    removeReaction(channel, slackTs, "hourglass_flowing_sand");
    removeReaction(channel, slackTs, "raised_hand");
    addReaction(channel, slackTs, "white_check_mark");
  }
  return `#${_padNo(rowNoQ)} 再マッチ成立: ${confirmed.caName} / ${confStr}`;
}

// v5.7.2: 未確定(日程調整中)面談を定期的に自動再マッチング
//   - 登録から36時間以内の行のみ対象 (それ以降は remindStalledMeetings が調整不可へ)
//   - CAが増えた / 既存CAの枠が空いた場合に自動で拾う
//   - トリガー: 1時間毎 (setAllTriggers で登録)
function autoRematchStalled() {
  const now = Date.now();
  const cutoff36h = now - 36 * 3600 * 1000;
  const results = [];
  let scanned = 0, matched = 0;
  for (const sheet of getAllGradeSheets()) {
    const lastRow = sheet.getLastRow();
    if (lastRow < 2) continue;
    const data = sheet.getRange(1, 1, lastRow, GRADE_SHEET_COLS).getValues();
    for (let i = 1; i < data.length; i++) {
      if (!data[i][0]) continue;
      if (String(data[i][21] || "").trim() !== "日程調整中") continue;
      // 登録日時(B列)で36時間以内か判定
      const reg = data[i][1] instanceof Date ? data[i][1] : new Date(data[i][1]);
      if (isNaN(reg.getTime()) || reg.getTime() < cutoff36h) continue;
      scanned++;
      const rowNo = parseInt(data[i][0], 10);
      try {
        const res = _doRematch(rowNo, "自動再マッチ (定期)");
        results.push(res);
        if (res.includes("再マッチ成立")) matched++;
      } catch(e) {
        results.push(`#${_padNo(rowNo)} ERR: ${e}`);
      }
    }
  }
  Logger.log(`[autoRematchStalled] scanned=${scanned} matched=${matched}\n${results.join("\n")}`);
  return `scanned=${scanned} matched=${matched}\n${results.join("\n")}`;
}

// v5.7+: 指定行の元スレッドに「CA調整依頼」を再投稿する (CAグループメンション)
//   使い方: ?action=repostCARequest&no=55
function repostCARequest(e) {
  const rowNoQ = parseInt(e?.parameter?.no || "", 10);
  if (!rowNoQ) return "no パラメータ必須";
  const found = findRowByNo(rowNoQ);
  if (!found) return `#${_padNo(rowNoQ)} 見つかりません`;
  const sd = found.data[found.rowIdx];
  const phase = String(sd[21] || "").trim();
  if (phase !== "日程調整中") return `#${_padNo(rowNoQ)} は ${phase} なのでスキップ (日程調整中のみ)`;
  const ts = String(sd[25] || "").trim();
  const cfg = getConfig();
  const channel = cfg["Slack ワークフローチャンネルID"];
  if (!ts || !channel) return "ts/channel なし";
  const account = String(sd[4] || ""), grade = String(sd[5] || ""), sns = String(sd[6] || "");
  const industry = String(sd[7] || ""), topic = String(sd[8] || "");
  const candidates = [
    { date: sd[9],  time: sd[10] },
    { date: sd[12], time: sd[13] },
    { date: sd[15], time: sd[16] },
  ].filter(c => c.date && c.time).map(c => {
    const d = c.date instanceof Date ? Utilities.formatDate(c.date, "Asia/Tokyo", "yyyy-MM-dd") : String(c.date).trim();
    const t = c.time instanceof Date ? Utilities.formatDate(c.time, "Asia/Tokyo", "HH:mm") : String(c.time).trim();
    return `${d} ${t}`;
  });
  const lgKey = String(sd[2] || "").trim();
  const lgUidStored = String(sd[24] || "").trim();
  const lgInfo = getLGInfo(lgKey);
  const lgUid = lgUidStored && /^U[A-Z0-9]+$/.test(lgUidStored) ? lgUidStored
              : (/^U[A-Z0-9]+$/.test(lgKey) ? lgKey : lgInfo.slackUid);
  const lgMention = lgUid ? `<@${lgUid}>` : (lgInfo.name || lgKey);
  const cgId = cfg["CAユーザーグループID"];
  const caMention = cgId ? `<!subteam^${cgId}>` : "@CA";
  const reqText =
    `:hourglass_flowing_sand: *#${_padNo(rowNoQ)} CA調整依頼 (再掲)* ${caMention}\n` +
    `学生: ${account}（${grade || ""}・${sns || ""}）\n` +
    `希望日程: ${candidates.join(" / ")}\n` +
    `業界: ${industry || "-"} / 相談: ${topic || "-"}\n` +
    `担当LG: ${lgMention}\n\n` +
    `→ 調整できる方はこのスレッドの「📅 日程入力」ボタンを押してください。`;
  sendSlackMessage(channel, reqText, null, ts);
  addReaction(channel, ts, "hourglass_flowing_sand");
  return `#${_padNo(rowNoQ)} CA調整依頼を再投稿しました`;
}

// v5.7+: 指定行のSlackスレッド内容を表示 (調査用)
//   使い方: ?action=inspectThread&no=39
function inspectThread(e) {
  const rowNoQ = parseInt(e?.parameter?.no || "", 10);
  if (!rowNoQ) return "no必須";
  const found = findRowByNo(rowNoQ);
  if (!found) return `#${_padNo(rowNoQ)} 見つからない`;
  const ts = String(found.data[found.rowIdx][25] || "").trim();
  const channel = getConfig()["Slack ワークフローチャンネルID"];
  if (!ts || !channel) return "ts/channel なし";
  const token = getConfig()["Slack Bot Token"];
  const res = UrlFetchApp.fetch(
    `https://slack.com/api/conversations.replies?channel=${channel}&ts=${ts}&limit=200`,
    { headers: { Authorization: "Bearer " + token }, muteHttpExceptions: true });
  const data = JSON.parse(res.getContentText());
  if (!data.ok) return `err: ${data.error}`;
  const lines = [];
  (data.messages || []).forEach(m => {
    const ts2 = m.ts;
    const userOrBot = m.user || m.bot_id || "(unknown)";
    const txt = (m.text || "").substring(0, 200).replace(/\n/g, " | ");
    lines.push(`[${ts2}] ${userOrBot}: ${txt}`);
  });
  return `#${_padNo(rowNoQ)} thread messages=${data.messages?.length || 0}\n` + lines.join("\n");
}

// v5.7+: 指定行の元スレッドから、特定文字列を含むbotメッセージを削除する
//   使い方: ?action=purgeThreadMessages&no=55&q=再マッチング成立
function purgeThreadMessages(e) {
  const rowNoQ = parseInt(e?.parameter?.no || "", 10);
  const q = (e?.parameter?.q || "").trim();
  if (!rowNoQ || !q) return "no と q パラメータ必須";
  const found = findRowByNo(rowNoQ);
  if (!found) return `#${_padNo(rowNoQ)} 見つかりません`;
  const sd = found.data[found.rowIdx];
  const ts = String(sd[25] || "").trim();
  const channel = getConfig()["Slack ワークフローチャンネルID"];
  if (!ts || !channel) return "ts/channel なし";
  const token = getConfig()["Slack Bot Token"];
  const repRes = UrlFetchApp.fetch(
    `https://slack.com/api/conversations.replies?channel=${channel}&ts=${ts}&limit=100`,
    { headers: { Authorization: "Bearer " + token }, muteHttpExceptions: true });
  const repData = JSON.parse(repRes.getContentText());
  if (!repData.ok) return `replies err: ${repData.error}`;
  const tokens = q.split(/[,|]/).map(s => s.trim()).filter(Boolean);
  const targets = (repData.messages || []).filter(m => {
    const t = String(m.text || "");
    return tokens.some(tk => t.includes(tk));
  });
  const out = [];
  targets.forEach(m => {
    const dres = UrlFetchApp.fetch("https://slack.com/api/chat.delete", {
      method: "post", contentType: "application/json",
      headers: { Authorization: "Bearer " + token },
      payload: JSON.stringify({ channel, ts: m.ts }),
      muteHttpExceptions: true,
    });
    const dd = JSON.parse(dres.getContentText());
    out.push(`${m.ts} ok=${dd.ok}${dd.error ? " err=" + dd.error : ""}`);
  });
  return `#${_padNo(rowNoQ)} 検索=${q} → 削除対象=${targets.length}\n${out.join("\n")}`;
}

// v5.7+: 指定行のMeet URLを差し替える (シートU列 + カレンダー説明 + スレッド通知)
//   使い方: ?action=setMeetUrl&no=74&url=https://meet.google.com/qat-ikqa-rar
function setMeetUrl(e) {
  const rowNoQ = parseInt(e?.parameter?.no || "", 10);
  const newUrl = (e?.parameter?.url || "").trim();
  if (!rowNoQ || !newUrl) return "no と url パラメータ必須";
  const found = findRowByNo(rowNoQ);
  if (!found) return `#${_padNo(rowNoQ)} 見つからない`;
  const sd = found.data[found.rowIdx];
  const oldUrl = String(sd[20] || "").trim();
  const caName = String(sd[19] || "").trim();

  // 1. シートU列更新
  found.sheet.getRange(found.rowIdx + 1, 21).setValue(newUrl);

  // 2. カレンダーイベントの説明・location を更新
  let calMsg = "カレンダー更新なし";
  const calId = _getCalIdByCaName(caName);
  if (calId) {
    try {
      const padded = _padNo(rowNoQ);
      const res = Calendar.Events.list(calId, {
        timeMin: new Date(Date.now() - 7 * 86400e3).toISOString(),
        timeMax: new Date(Date.now() + 365 * 86400e3).toISOString(),
        singleEvents: true, q: padded, maxResults: 50,
      });
      const ev = (res.items || []).find(it => String(it.summary || "").startsWith(`#${padded} `));
      if (ev) {
        const desc = String(ev.description || "").replace(/Meet[^\n]*/g, `Meet: ${newUrl}`);
        Calendar.Events.patch({
          description: desc.includes(newUrl) ? desc : `${desc}\nMeet: ${newUrl}`,
          location: newUrl,
        }, calId, ev.id, { sendUpdates: "all" });
        calMsg = `カレンダー更新OK (eventId=${ev.id})`;
      } else {
        calMsg = "カレンダーイベント未検出";
      }
    } catch(err) { calMsg = "カレンダー更新ERR: " + String(err).slice(0, 100); }
  }

  // 3. スレッド通知
  const ts = String(sd[25] || "").trim();
  const channel = getConfig()["Slack ワークフローチャンネルID"];
  if (ts && channel) {
    sendSlackMessage(channel,
      `🔗 *#${_padNo(rowNoQ)} Meet URL 変更*\n旧: ${oldUrl || "(なし)"}\n新: ${newUrl}\n→ 今後はこちらのURLをご利用ください`,
      null, ts);
  }
  return `#${_padNo(rowNoQ)} URL更新: ${oldUrl} → ${newUrl} / ${calMsg}`;
}

// v5.7+: 指定行に対し、現在のCAカレンダーへMeet生成「なし」で予定を作成して招待する
//   個人発行のMeet URLが既に学生に共有済の場合に使う (URLは申し送り欄に記載)
//   使い方: ?action=inviteCANoMeet&no=39
function inviteCANoMeet(e) {
  const rowNoQ = parseInt(e?.parameter?.no || "", 10);
  if (!rowNoQ) return "no必須";
  const found = findRowByNo(rowNoQ);
  if (!found) return `#${_padNo(rowNoQ)} 見つからない`;
  const sd = found.data[found.rowIdx];
  const confTime = String(sd[18] || "").trim();
  const caName = String(sd[19] || "").trim();
  const meetUrlMemo = String(sd[20] || "").trim();
  const m = confTime.match(/^(\d{4})\/(\d{1,2})\/(\d{1,2})\s+(\d{1,2}):(\d{2})/);
  if (!m) return `#${_padNo(rowNoQ)} 確定日時パース失敗`;
  const caRow = _caListRows().find(r => String(r[0]).trim() === caName);
  if (!caRow) return `CA ${caName} 見つからない`;
  const calId = String(caRow[1]).trim();

  const startDt = new Date(+m[1], +m[2] - 1, +m[3], +m[4], +m[5]);
  const endDt = new Date(startDt.getTime() + getMeetingDurationMin() * 60 * 1000);
  const lgKey = String(sd[2] || "").trim();
  const lgInfo = getLGInfo(lgKey);
  const account = String(sd[4] || ""), grade = String(sd[5] || ""), sns = String(sd[6] || "");
  const industry = String(sd[7] || ""), topic = String(sd[8] || ""), reach = String(sd[11] || "");

  const description =
    `連携番号: #${_padNo(rowNoQ)}\n` +
    `担当CA: ${caName}\n` +
    `LG担当: ${lgInfo.name || lgKey}\n` +
    `学生: ${account}（${grade}・${sns}）\n` +
    `つなぎ方: ${reach || "-"}\n` +
    `業界: ${industry || "-"}\n` +
    `相談: ${topic || "-"}\n` +
    (meetUrlMemo ? `Meet (個人発行): ${meetUrlMemo}\n` : "") +
    `※Meet URLは担当者個別発行のものを使用してください`;

  const _caShort = caName.replace(/^(?:CA\d+|LG\d+|\d+)-/, "");
  const _lgShort = (lgInfo.name || lgKey).replace(/^(?:CA\d+|LG\d+|\d+)-/, "");
  const summary = `#${_padNo(rowNoQ)} @${account}｜${grade}/${sns}｜CA${_caShort}×LG${_lgShort}`;

  try {
    const event = Calendar.Events.insert({
      summary,
      description,
      start: { dateTime: startDt.toISOString(), timeZone: "Asia/Tokyo" },
      end:   { dateTime: endDt.toISOString(),   timeZone: "Asia/Tokyo" },
      attendees: [
        { email: RECORD_EMAIL },
        { email: calId, responseStatus: "accepted" },
      ],
      // conferenceData は意図的に未指定 (Meet 生成なし)
    }, calId, { sendUpdates: "all" });
    return `#${_padNo(rowNoQ)} 招待送付OK → ${calId} eventId=${event.id}`;
  } catch(err) {
    return `#${_padNo(rowNoQ)} ERR: ${String(err).slice(0, 200)}`;
  }
}

// v5.7+: 指定行のCAカレンダーイベントに招待を再送する (attendees patch + sendUpdates="all")
//   使い方: ?action=resendCalendarInvite&no=9
function resendCalendarInvite(e) {
  const rowNoQ = parseInt(e?.parameter?.no || "", 10);
  if (!rowNoQ) return "no パラメータ必須";
  const found = findRowByNo(rowNoQ);
  if (!found) return `#${_padNo(rowNoQ)} 見つかりません`;
  const sd = found.data[found.rowIdx];
  const caName = String(sd[19] || "").trim();
  const caRow = _caListRows().find(r => String(r[0]).trim() === caName);
  if (!caRow) return `CA ${caName} 見つかりません`;
  const calId = String(caRow[1]).trim();
  const padded = _padNo(rowNoQ);
  try {
    const res = Calendar.Events.list(calId, {
      timeMin: new Date(Date.now() - 7 * 86400e3).toISOString(),
      timeMax: new Date(Date.now() + 365 * 86400e3).toISOString(),
      singleEvents: true, q: padded, maxResults: 50,
    });
    const ev = (res.items || []).find(it => String(it.summary || "").startsWith(`#${padded} `));
    if (!ev) return `#${padded} event not found on ${calId}`;
    const existing = (ev.attendees || []).slice();
    if (!existing.find(a => String(a.email || "").toLowerCase() === calId.toLowerCase())) {
      existing.push({ email: calId, responseStatus: "accepted" });
    }
    Calendar.Events.patch({ attendees: existing }, calId, ev.id, { sendUpdates: "all" });
    return `#${padded} 招待再送 → ${calId} attendees=${existing.map(a => a.email).join(",")}`;
  } catch(err) {
    return `#${padded} ERR: ${String(err).slice(0, 200)}`;
  }
}

// v5.7+: admin が手動で 代打 を指定CAにアサインする (代わりますボタン と同等の処理)
//   使い方: ?action=assignSubstituteByName&no=9&ca=関藤&subTs=1779759458.084699
//   - 旧CAカレンダーから該当イベント削除
//   - 新CAカレンダーに既存Meet URL再利用で作成
//   - シート T列(CA名) を新CAに更新
//   - 代打チャンネル / 元スレッド / 新CA DM へ通知
function assignSubstituteByName(e) {
  const rowNoQ = parseInt(e?.parameter?.no || "", 10);
  const caQ = (e?.parameter?.ca || "").trim();
  const subTs = (e?.parameter?.subTs || "").trim();
  if (!rowNoQ || !caQ) return "no & ca パラメータ必須";

  const caRow = _caListRows().find(r => String(r[0]).trim().includes(caQ));
  if (!caRow) return `CA "${caQ}" 見つかりません`;
  const newCaInfo = { name: String(caRow[0]).trim(), calId: String(caRow[1]).trim(), slackUid: String(caRow[2]).trim() };

  const found = findRowByNo(rowNoQ);
  if (!found) return `#${_padNo(rowNoQ)} 見つかりません`;
  const sd = found.data[found.rowIdx];
  const oldCA = String(sd[19] || "").trim();
  if (newCaInfo.name === oldCA) return `#${_padNo(rowNoQ)} 受諾者=現CA でスキップ`;

  const confTime = String(sd[18] || "").trim();
  const existingMeetUrl = String(sd[20] || "").trim();
  const m = confTime.match(/^(\d{4})\/(\d{1,2})\/(\d{1,2})\s+(\d{1,2}):(\d{2})/);
  if (!m) return `#${_padNo(rowNoQ)} 確定日時パース失敗`;

  const oldCalId = _getCalIdByCaName(oldCA);
  let delRes = null;
  if (oldCalId) delRes = _deleteCalendarEventByRowNo(oldCalId, rowNoQ);

  const startDt = new Date(+m[1], +m[2] - 1, +m[3], +m[4], +m[5]);
  const endDt = new Date(startDt.getTime() + getMeetingDurationMin() * 60 * 1000);
  const lgKey = String(sd[2] || "").trim();
  const lgInfo = getLGInfo(lgKey);
  const cal = createCalendarEvent(newCaInfo.calId, {
    account: String(sd[4] || ""), grade: String(sd[5] || ""), sns: String(sd[6] || ""),
    industry: String(sd[7] || ""), topic: String(sd[8] || ""), reach: String(sd[11] || ""),
    lgMember: lgKey,
  }, startDt, endDt, lgInfo.name || lgKey, newCaInfo.name, rowNoQ, existingMeetUrl);
  if (!cal.event) return `#${_padNo(rowNoQ)} 新CAカレンダー作成失敗 (権限/Meet生成NGの可能性)`;

  found.sheet.getRange(found.rowIdx + 1, 20).setValue(newCaInfo.name);

  const cfg = getConfig();
  const subCh = cfg["Slack 代打チャンネルID"] || "C0A4YVD662E";
  const origCh = cfg["Slack ワークフローチャンネルID"];
  const origTs = String(sd[25] || "").trim();
  const newCaMention = newCaInfo.slackUid ? `<@${newCaInfo.slackUid}>` : newCaInfo.name;
  const lgUidStored = String(sd[24] || "").trim();
  const lgUid = lgUidStored && /^U[A-Z0-9]+$/.test(lgUidStored) ? lgUidStored
              : (/^U[A-Z0-9]+$/.test(lgKey) ? lgKey : lgInfo.slackUid);
  const lgMention = lgUid ? `<@${lgUid}>` : (lgInfo.name || lgKey);

  // 代打チャンネル: 募集メッセージへの返信
  sendSlackMessage(subCh,
    `✅ *代打成立 #${_padNo(rowNoQ)}* (admin手動アサイン)\n${oldCA} → ${newCaMention} (${newCaInfo.name})\n日時: ${confTime}\nMeet: ${existingMeetUrl}\n※Meet URLは変わりません。新CAは当日上記URLでご参加ください。`,
    null, subTs || null);

  // 元スレッド
  if (origCh && origTs) {
    sendSlackMessage(origCh,
      `🔄 *#${_padNo(rowNoQ)} 代打成立* (admin手動アサイン)\n` +
      `${lgMention} ← 担当LG確認お願いします\n` +
      `旧CA: ${oldCA}\n` +
      `新CA: ${newCaMention} (${newCaInfo.name})\n` +
      `日時: ${confTime}\n` +
      `🔗 *Meet URLは変更なし*: ${existingMeetUrl}\n` +
      `→ 学生に既に共有済のURLでそのままご案内ください`, null, origTs);
  }

  // 新CA DM
  if (newCaInfo.slackUid) {
    sendSlackMessage(newCaInfo.slackUid,
      `🔄 *代打受諾 #${_padNo(rowNoQ)}* (admin手動アサイン)\n学生: ${String(sd[4] || "")}\n日時: ${confTime}\nMeet: ${existingMeetUrl}\n\n※Meet URLは変わりません。当日上記URLからご参加ください。\n※カレンダーへの追加が必要な場合は手動でお願いします`, null, null);
  }

  return `#${_padNo(rowNoQ)} ${oldCA} → ${newCaInfo.name} 代打成立 (旧カレ削除=${JSON.stringify(delRes)})`;
}

// v5.7+: 指定行の確定情報をスレッドに「調整完了」フォーマットで再アナウンス
//   既に rematchRow 等で別フォーマット送信済みの行を整える用
function announceConfirmation(e) {
  const rowNoQ = parseInt(e?.parameter?.no || "", 10);
  if (!rowNoQ) return "no パラメータ必須";
  const found = findRowByNo(rowNoQ);
  if (!found) return `#${_padNo(rowNoQ)} 見つかりません`;
  const r = found.data[found.rowIdx];
  const phase = String(r[21] || "").trim();
  if (phase !== "実施予定") return `#${_padNo(rowNoQ)} は ${phase} なのでスキップ`;
  const ts = String(r[25] || "").trim();
  const channel = getConfig()["Slack ワークフローチャンネルID"];
  if (!ts || !channel) return `#${_padNo(rowNoQ)} ts/channel なし`;
  const confStr = String(r[18] || "").trim();
  const caName  = String(r[19] || "").trim();
  const meetUrl = String(r[20] || "").trim();
  const account = String(r[4] || ""), grade = String(r[5] || ""), sns = String(r[6] || "");
  const lgKey = String(r[2] || "").trim();
  const lgInfo = getLGInfo(lgKey);
  const _lgUid = /^U[A-Z0-9]+$/.test(lgKey) ? lgKey : (lgInfo && lgInfo.slackUid);
  const caRow = _caListRows().find(row => String(row[0] || "").trim() === caName.split("-")[0] || String(row[0] || "").trim() === caName);
  const caUid = caRow ? String(caRow[2] || "").trim() : "";
  const _notifText = formatNotification({
    statusEmoji: "✅", title: "調整完了", rowNo: rowNoQ,
    account, grade, sns,
    lgUid: _lgUid, caUid, caName,
    detail: `日時: ${confStr}\nMeet: ${meetUrl || "-"}`,
    reporter: "再マッチング (admin)",
  });
  const _blocks = [{ type: "section", text: { type: "mrkdwn", text: _notifText } }];
  const _btnBlock = buildThreadButtons(rowNoQ, "実施予定");
  if (_btnBlock) _blocks.push(..._btnBlock);
  sendSlackMessage(channel, _notifText, _blocks, ts);
  return `#${_padNo(rowNoQ)} 調整完了アナウンスを再送`;
}

// v5.7+: 指定行のフェーズに応じてスレッドのスタンプを正しい状態へ合わせる
//   実施予定 → :white_check_mark: のみ
//   日程調整中 → :hourglass_flowing_sand: のみ
//   飛び → :no_entry_sign: を追加 (他はそのまま)
function fixReactionsForRow(e) {
  const rowNoQ = parseInt(e?.parameter?.no || "", 10);
  if (!rowNoQ) return "no パラメータ必須";
  const found = findRowByNo(rowNoQ);
  if (!found) return `#${_padNo(rowNoQ)} 見つかりません`;
  const r = found.data[found.rowIdx];
  const phase = String(r[21] || "").trim();
  const ts = String(r[25] || "").trim();
  const channel = getConfig()["Slack ワークフローチャンネルID"];
  if (!ts || !channel) return `#${_padNo(rowNoQ)} ts/channel なし`;
  if (phase === "実施予定") {
    removeReaction(channel, ts, "hourglass_flowing_sand");
    removeReaction(channel, ts, "raised_hand");
    addReaction(channel, ts, "white_check_mark");
  } else if (phase === "日程調整中") {
    removeReaction(channel, ts, "white_check_mark");
    addReaction(channel, ts, "hourglass_flowing_sand");
  } else if (phase === "飛び") {
    addReaction(channel, ts, "no_entry_sign");
  }
  return `#${_padNo(rowNoQ)} reaction 更新 (phase=${phase})`;
}

// v5.7+: 各アクティブCAのカレンダーへの書き込み権限テスト
//   2026-01-01 00:00-00:15 にテストイベントを insert → 即 delete
function testCAWritePerm() {
  const cas = _caListRows()
    .filter(r => r[0] && r[1] && String(r[4] || "").trim() === "アクティブ")
    .map(r => ({ name: String(r[0]).trim(), calId: String(r[1]).trim() }));
  const out = [];
  const t0 = new Date("2030-01-01T00:00:00+09:00");
  const t1 = new Date("2030-01-01T00:15:00+09:00");
  cas.forEach(ca => {
    try {
      const ev = Calendar.Events.insert({
        summary: "_perm_test_DELETE_ME",
        start: { dateTime: t0.toISOString(), timeZone: "Asia/Tokyo" },
        end:   { dateTime: t1.toISOString(), timeZone: "Asia/Tokyo" },
      }, ca.calId);
      try { Calendar.Events.remove(ca.calId, ev.id); } catch(_) {}
      out.push(`✅ ${ca.name} (${ca.calId}) 書き込みOK`);
    } catch(e) {
      out.push(`❌ ${ca.name} (${ca.calId}) — ${String(e).slice(0, 200)}`);
    }
  });
  return out.join("\n");
}

// v5.7+: 指定行の候補時間に対し、各アクティブCAの 6/1 19:00-22:30 等の空き状況を診断
// 使い方: ?action=dumpRowFreeSlots&no=55
function dumpRowFreeSlots(e) {
  const rowNoQ = parseInt(e?.parameter?.no || "", 10);
  if (!rowNoQ) return "no パラメータが必要 (例: ?action=dumpRowFreeSlots&no=55)";
  const found = findRowByNo(rowNoQ);
  if (!found) return `#${_padNo(rowNoQ)} 見つかりません`;
  const r = found.data[found.rowIdx];
  const candidates = [
    { date: r[9],  time: r[10] },
    { date: r[12], time: r[13] },
    { date: r[15], time: r[16] },
  ].filter(c => c.date && c.time);
  const cas = _caListRows()
    .filter(row => row[0] && row[1] && String(row[4] || "").trim() === "アクティブ")
    .map(row => ({ name: String(row[0]).trim(), calId: String(row[1]).trim() }));
  const meet = getMeetingDurationMin();
  const step = getSlotStepMin();
  const out = [`#${_padNo(rowNoQ)} 候補=${candidates.length} アクティブCA=${cas.length}`];
  candidates.forEach((c, ci) => {
    const range = parseTimeOrRange(c.time);
    if (!range) { out.push(`候補${ci+1}: ${c.date} ${c.time} → parseTimeOrRange NULL`); return; }
    const rs = parseDatetime(c.date, range.start);
    const re = range.end ? parseDatetime(c.date, range.end) : new Date(rs.getTime() + meet*60000);
    out.push(`\n候補${ci+1}: ${c.date} ${c.time} → range ${range.start}-${range.end}`);
    cas.forEach(ca => {
      let evs = [];
      try {
        const res = Calendar.Events.list(ca.calId, {
          timeMin: rs.toISOString(), timeMax: re.toISOString(),
          singleEvents: true, maxResults: 100,
        });
        evs = (res.items || []).filter(ev => ev.status !== "cancelled" && ev.transparency !== "transparent");
      } catch(err) { out.push(`  ${ca.name}: ERR ${err}`); return; }
      const lastStart = new Date(re.getTime() - meet*60000);
      const freeSlots = [];
      for (let t = rs.getTime(); t <= lastStart.getTime(); t += step*60000) {
        const sDt = new Date(t);
        const eDt = new Date(t + meet*60000);
        if (!_isCAAvailableInHours(ca.calId, sDt, eDt)) continue;
        const overlap = evs.some(ev => {
          const evS = ev.start.dateTime ? new Date(ev.start.dateTime) : new Date(ev.start.date);
          const evE = ev.end.dateTime ? new Date(ev.end.dateTime) : new Date(ev.end.date);
          return evS < eDt && evE > sDt;
        });
        if (!overlap) freeSlots.push(formatTime(sDt));
      }
      const busy = evs.map(ev => {
        const s = ev.start.dateTime ? ev.start.dateTime.substring(11,16) : "終日";
        const en = ev.end.dateTime ? ev.end.dateTime.substring(11,16) : "終日";
        return `${s}-${en} ${ev.summary || ""}`;
      });
      out.push(`  ${ca.name}: 空き[${freeSlots.join(",") || "なし"}] / 予定[${busy.join(" | ") || "なし"}]`);
    });
  });
  return out.join("\n");
}

// v5.7+: PropertiesService の古いジョブ・キャッシュキーをクリーンアップ
// 1時間毎の自動トリガーで実行 + 手動実行も可
function cleanupOldJobs() {
  const props = PropertiesService.getScriptProperties();
  const allKeys = props.getKeys();
  const now = Date.now();
  const cutoff1h = now - 60 * 60 * 1000;
  const summary = { vsJobsDeleted: 0, memberAddDeleted: 0, otherSkipped: 0 };
  allKeys.forEach(k => {
    // vsJob_ または memberAddJob_ から timestamp を抽出
    const m = k.match(/^(vsJob_|memberAddJob_)(\d+)/);
    if (m) {
      const ts = parseInt(m[2], 10);
      if (ts && ts < cutoff1h) {
        try {
          props.deleteProperty(k);
          if (m[1] === "vsJob_") summary.vsJobsDeleted++;
          else summary.memberAddDeleted++;
        } catch(e) { Logger.log("[cleanupOldJobs] " + k + ": " + e); }
      }
    } else {
      summary.otherSkipped++;
    }
  });
  Logger.log("[cleanupOldJobs] " + JSON.stringify(summary));
  return summary;
}

// v5.7+: 既存の実施予定スレッドに新ボタン群(代打依頼を含む)を再投稿
function refreshThreadButtons() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const cfg = getConfig();
  const channel = cfg["Slack ワークフローチャンネルID"] || cfg["Slack テストチャンネルID"];
  const out = [];
  for (const sh of getAllGradeSheets()) {
    const data = sh.getDataRange().getValues();
    for (let i = 1; i < data.length; i++) {
      if (!data[i][0]) continue;
      const phase = String(data[i][21] || "").trim();
      const slackTs = String(data[i][25] || "").trim();
      if (!slackTs) continue;
      if (phase !== "実施予定" && phase !== "日程調整中") continue;
      const rowNo = data[i][0];
      const btn = buildThreadButtons(rowNo, phase);
      if (!btn) continue;
      const noteBlocks = [
        { type: "section", text: { type: "mrkdwn", text: `🔄 *#${_padNo(rowNo)} 操作ボタン更新* — 「代打依頼」が利用可能になりました` } },
        ...btn,
      ];
      try {
        sendSlackMessage(channel, `#${_padNo(rowNo)} ボタン更新`, noteBlocks, slackTs);
        out.push(`#${_padNo(rowNo)} ${phase}`);
      } catch(e) { Logger.log(`[refreshThreadButtons] ${rowNo}: ${e}`); }
    }
  }
  return `更新: ${out.length}件 (${out.join(", ")})`;
}

// 実績管理シート削除（一回限り）
function deleteJisseiSheet() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sh = ss.getSheetByName("実績管理");
  if (sh) { ss.deleteSheet(sh); return "deleted"; }
  return "not_found";
}

// 佐藤(CA001)をアクティブ化（MCP書き込みが効かない時用のフォールバック）
function activateSatoCA() {
  const sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("CAリスト");
  // protectedや余計なmergeを解除
  try {
    sh.getRange("A2:E2").breakApart();
    (sh.getProtections(SpreadsheetApp.ProtectionType.RANGE) || []).forEach(p => {
      const r = p.getRange();
      if (r && r.getRow() === 2) try { p.remove(); } catch(_) {}
    });
  } catch(_) {}
  sh.getRange("A2:E2").setValues([["CA001-佐藤篤也","atsuya_sato@tokumori.co.jp","U08SGGC5QR4","社員","アクティブ"]]);
  return sh.getRange("A2:E2").getValues();
}

// 特定CAの直近予定をダンプ（診断用）
// ?action=dumpCAEvents&ca=石塚亘&days=14
function dumpCAEvents(e) {
  const caQuery = (e?.parameter?.ca || "").trim();
  const days = parseInt(e?.parameter?.days || "7", 10);
  if (!caQuery) return "ca パラメータ必須";
  const cas = _caListRows()
    .filter(r => r[0] && r[1])
    .map(r => ({ name: String(r[0]).trim(), calId: String(r[1]).trim(), status: String(r[4] || "").trim() }));
  const ca = cas.find(c => c.name.includes(caQuery));
  if (!ca) return "該当CA見つからない: " + caQuery;
  const tomorrow = new Date(); tomorrow.setDate(tomorrow.getDate() + 1); tomorrow.setHours(0,0,0,0);
  const end = new Date(tomorrow.getTime() + days * 24*3600*1000);
  try {
    const res = Calendar.Events.list(ca.calId, {
      timeMin: tomorrow.toISOString(),
      timeMax: end.toISOString(),
      singleEvents: true,
      orderBy: "startTime",
      maxResults: 2500,
    });
    const items = res.items || [];
    const lines = [`${ca.name} (${ca.calId}) [${ca.status}] events=${items.length}`];
    items.forEach(ev => {
      const s = ev.start.dateTime || ev.start.date;
      const en = ev.end.dateTime || ev.end.date;
      lines.push(`  ${ev.status} ${s} → ${en}: ${ev.summary || "(no title)"}`);
    });
    return lines.join("\n");
  } catch(err) {
    return "ERR: " + String(err);
  }
}

// 全CAのカレンダー共有状況をチェック（アクティブ・非アクティブ・共有待ち 全件）
function checkAllCACalendarAccess() {
  const cas = _caListRows()
    .filter(r => r[0] && r[1])
    .map(r => ({
      name: String(r[0]).trim(),
      calId: String(r[1]).trim(),
      status: String(r[4] || "").trim(),
    }));
  const results = [];
  cas.forEach(ca => {
    try {
      Calendar.Events.list(ca.calId, { maxResults: 1, timeMin: new Date().toISOString() });
      results.push(`✅ [${ca.status}] ${ca.name} (${ca.calId})`);
    } catch(e) {
      results.push(`❌ [${ca.status}] ${ca.name} (${ca.calId}) — ${String(e).slice(0, 80)}`);
    }
  });
  return results.join("\n");
}

// URL クエリ ?value=<token> でScript Propertyに直接Bot Tokenをセット
function setBotTokenProp(e) {
  const v = (e?.parameter?.value || "").trim();
  if (!v || !v.startsWith("xoxb-")) return "invalid_or_missing_value";
  PropertiesService.getScriptProperties().setProperty("SLACK_BOT_TOKEN", v);
  // シートにも反映（B2 = Slack Bot Token）
  try {
    const sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(CONFIG_SHEET);
    if (sh) sh.getRange("B2").setValue(v);
  } catch(_) {}
  try { CacheService.getScriptCache().remove("__cfg__"); } catch(_) {}
  return "set len=" + v.length;
}

// 現状診断: Script Property / 設定シート の Bot Token 状況を返す
function diagBotToken() {
  const prop = PropertiesService.getScriptProperties().getProperty("SLACK_BOT_TOKEN") || "";
  const cfg = getConfig()["Slack Bot Token"] || "";
  return {
    propertyLen: prop.length,
    propertyPrefix: prop.slice(0, 10),
    configSheetLen: cfg.length,
    configSheetPrefix: cfg.slice(0, 10),
  };
}

function handleButtonAction(payload) {
  const cfg     = getConfig();
  const channel = payload.channel?.id || cfg["Slack ワークフローチャンネルID"] || cfg["Slack テストチャンネルID"];
  const msgTs   = payload.message?.ts;
  const actions = payload.actions || [];
  if (!actions.length) return;

  const { action_id, value } = actions[0];
  const _uid = payload.user?.id;

  // v5.7+: 連打防止 — 同一(action_id+value+user) を 60秒間ブロック
  // ※Slackのリトライ・ユーザー再クリック両方をカバー
  try {
    const dedupKey = `__btn_${action_id}_${value || ""}_${_uid || ""}`;
    const cache = CacheService.getScriptCache();
    if (cache.get(dedupKey)) {
      Logger.log(`[btn dedup] ${dedupKey} → skip`);
      try { sendEphemeral(channel, _uid, "⏳ 直前の操作を処理中です。完了をお待ちください (約30秒〜1分)"); } catch(_) {}
      return;
    }
    cache.put(dedupKey, "1", 15);
  } catch(_) {}

  // v5.7+: 権限チェック (admin=tokumori社員/指名管理者は全許可)
  const perm = _isAllowed(_uid, action_id);
  if (!perm.ok) {
    try {
      sendEphemeral(channel, _uid,
        `⚠️ この操作は ${perm.allowed.join("/")} 限定です。あなたの役職: ${(perm.roles.length ? perm.roles.join(",") : "未登録")}`);
    } catch(_) {}
    return;
  }
  const rowNo = parseInt(value, 10);
  const user  = payload.user?.name || "不明";
  // v5.7: 操作者を Slack メンション形式で表現
  const userMention = payload.user?.id ? `<@${payload.user.id}>` : user;

  // v5.0: 全卒年シート横断で行を検索
  const found = findRowByNo(rowNo);
  if (!found) return;
  const { sheet, data } = found;
  const targetRow = found.rowIdx + 1;

  // v5.7+: 代打公募「✋ 代わります」処理
  if (action_id === "accept_substitute") {
    let v;
    try { v = JSON.parse(value); } catch(_) { return; }
    const { rowNo: subRowNo, origCh, origTs, requesterId } = v;
    if (_uid === requesterId) {
      sendEphemeral(channel, _uid, "⚠️ 依頼元のCA本人は代打を受諾できません");
      return;
    }
    // v5.7+: アクティブ＋非アクティブを許可 (共有待ちのみ除外)
    const newCaInfo = getCAInfoByUidAny(_uid);
    if (!newCaInfo) {
      sendEphemeral(channel, _uid, "⚠️ メンバーCAに登録なし or「共有待ち」のため受諾できません");
      return;
    }
    const sub = findRowByNo(subRowNo);
    if (!sub) {
      sendEphemeral(channel, _uid, `⚠️ #${_padNo(subRowNo)} が見つかりません`);
      return;
    }
    const sd = sub.data[sub.rowIdx];
    const oldCA = String(sd[19] || "").trim();
    // v5.7+: 受諾者 = 現CA ガード (自分→自分の切替防止)
    if (newCaInfo.name === oldCA) {
      sendEphemeral(channel, _uid, `⚠️ あなたが現在の担当CAです。代打受諾不要です`);
      return;
    }
    const confTime = String(sd[18] || "").trim();
    const existingMeetUrl = String(sd[20] || "").trim();
    const m2 = confTime.match(/^(\d{4})\/(\d{1,2})\/(\d{1,2})\s+(\d{1,2}):(\d{2})/);
    // v5.7+: 旧CAのカレンダーから #NNNN イベントを削除
    const oldCalId2 = _getCalIdByCaName(oldCA);
    if (oldCalId2) _deleteCalendarEventByRowNo(oldCalId2, subRowNo);
    // 新CAのカレンダーに既存Meet URLで上書き作成 (既存予定との競合は無視・CA側で拾ったため)
    if (m2 && newCaInfo.calId) {
      const startDt2 = new Date(+m2[1], +m2[2] - 1, +m2[3], +m2[4], +m2[5]);
      const endDt2 = new Date(startDt2.getTime() + getMeetingDurationMin() * 60 * 1000);
      const lgKey3 = String(sd[2] || "").trim();
      const lgInfo3 = getLGInfo(lgKey3);
      createCalendarEvent(newCaInfo.calId, {
        account: String(sd[4] || ""), grade: String(sd[5] || ""), sns: String(sd[6] || ""),
        industry: String(sd[7] || ""), topic: String(sd[8] || ""), reach: String(sd[11] || ""),
        lgMember: lgKey3,
      }, startDt2, endDt2, lgInfo3.name || lgKey3, newCaInfo.name, subRowNo, existingMeetUrl);
    }
    sub.sheet.getRange(sub.rowIdx + 1, 20).setValue(newCaInfo.name);
    // sheet U列(Meet URL) は変更しない
    // LG解決
    const lgKeyA = String(sd[2] || "").trim();
    const lgUidStoredA = String(sd[24] || "").trim();
    const lgInfoA = getLGInfo(lgKeyA);
    const lgUidA = lgUidStoredA && /^U[A-Z0-9]+$/.test(lgUidStoredA) ? lgUidStoredA
                 : (/^U[A-Z0-9]+$/.test(lgKeyA) ? lgKeyA : lgInfoA.slackUid);
    const lgMentionA = lgUidA ? `<@${lgUidA}>` : (lgInfoA.name || lgKeyA);
    // 代打チャンネルにも完了報告 + 元スレッドにも通知
    sendSlackMessage(channel, `✅ *代打成立 #${_padNo(subRowNo)}*\n${oldCA} → <@${_uid}> (${newCaInfo.name})\n日時: ${confTime}\nMeet: ${existingMeetUrl}\n※Meet URLは変わりません。新CAは当日上記URLでご参加ください。`, null, msgTs);
    if (origCh && origTs) {
      sendSlackMessage(origCh,
        `🔄 *#${_padNo(subRowNo)} 代打成立* (公募から受諾)\n` +
        `${lgMentionA} ← 担当LG確認お願いします\n` +
        `旧CA: ${oldCA}\n` +
        `新CA: <@${_uid}> (${newCaInfo.name})\n` +
        `日時: ${confTime}\n` +
        `🔗 *Meet URLは変更なし*: ${existingMeetUrl}\n` +
        `→ 学生に既に共有済のURLでそのままご案内ください`, null, origTs);
    }
    if (requesterId) sendSlackMessage(requesterId, `✅ 代打受諾されました #${_padNo(subRowNo)} → ${newCaInfo.name}\nMeet URLは変わりません`, null, null);
    // 新CA本人にも詳細DM (カレンダー手動追加促し)
    sendSlackMessage(_uid, `🔄 *代打受諾 #${_padNo(subRowNo)}*\n学生: ${String(sd[4] || "")}\n日時: ${confTime}\nMeet: ${existingMeetUrl}\n\n※Meet URLは変わりません。当日上記URLからご参加ください。\n※カレンダーへの追加が必要な場合は手動でお願いします`, null, null);
    return;
  }

  if (action_id === "reschedule") {
    sheet.getRange(targetRow, 22).setValue("リスケ");
    sendSlackMessage(channel, `📅 #${_padNo(rowNo)} 日程変更リクエスト（${userMention}）\n再登録をお願いします。`, null, msgTs);

  } else if (action_id === "no_show") {
    sheet.getRange(targetRow, 22).setValue("飛び");
    const account2  = String(data[targetRow - 1][4] || "").trim();
    const lgKey2    = String(data[targetRow - 1][2] || "").trim();
    const confTime2 = String(data[targetRow - 1][18] || "").trim();
    // v5.7+: LG UIDは Y列(24=0-based, 25=1-based) に登録時保存。なければ従来ロジック
    const lgUidStored = String(data[targetRow - 1][24] || "").trim();
    const lgInfo2    = getLGInfo(lgKey2);
    const lgUid2     = lgUidStored && /^U[A-Z0-9]+$/.test(lgUidStored) ? lgUidStored
                     : (/^U[A-Z0-9]+$/.test(lgKey2) ? lgKey2 : lgInfo2.slackUid);
    const lgMention2 = lgUid2 ? `<@${lgUid2}>` : (lgInfo2.name || lgKey2 || "未登録");
    // v5.7+: 飛び報告フォーマット（固定メンション + 通知）
    //   メンション先: 渡邊駿 / 佐藤篤也 / 山口扇世 (運用責任者ライン)
    const NOSHOW_MENTIONS = "<@U06NB1UFYN7> <@U08SGGC5QR4> <@U07TWUDKUCW>";
    const grade2 = String(data[targetRow - 1][5] || "").trim();
    const sns2   = String(data[targetRow - 1][6] || "").trim();
    const caName2 = String(data[targetRow - 1][19] || "").trim();
    const noShowMsg =
      `🚫 *#${_padNo(rowNo)} 飛び報告*\n` +
      `${NOSHOW_MENTIONS}\n\n` +
      `①学生アカウント名: ${account2}\n` +
      `②面談予定時間: ${confTime2}\n` +
      `③LG担当: ${lgMention2}\n` +
      `④5分待ちましたが不参加です。担当LGは確認をしCA宛に連絡をお願いします。`;
    // 飛び一覧タブに追記
    try {
      const noShowSheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("飛び一覧");
      if (noShowSheet) {
        const reporterName = payload.user?.id ? _resolveSlackUserName(payload.user.id) : "";
        noShowSheet.appendRow([
          _padNo(rowNo), account2, grade2, sns2, confTime2,
          lgInfo2.name || lgKey2, caName2,
          formatDatetime(new Date()), reporterName || user,
        ]);
      }
    } catch(e) { Logger.log("[noShow→飛び一覧] " + e); }
    sendSlackMessage(channel, noShowMsg, null, msgTs);
    const noShowChannel = cfg["Slack 飛びチャンネルID"];
    if (noShowChannel && noShowChannel !== channel) {
      sendSlackMessage(noShowChannel, noShowMsg, null, null);
    }
    const caName   = String(data[targetRow - 1][19]).trim();
    if (caName) {
      const caRow = _caListRows().find(r => String(r[0]).trim() === caName);
      const calId = caRow ? String(caRow[1]).trim() : "";
      const confStr = String(data[targetRow - 1][18]);
      if (calId && confStr) _annotateEventNoShow(calId, confStr, user);
    }

  } else if (action_id === "cancel_meeting") {
    // v5.7+: 学生事前キャンセル
    const account3  = String(data[targetRow - 1][4] || "").trim();
    const lgKey3    = String(data[targetRow - 1][2] || "").trim();
    const confTime3 = String(data[targetRow - 1][18] || "").trim();
    const caName3   = String(data[targetRow - 1][19] || "").trim();
    const grade3    = String(data[targetRow - 1][5] || "").trim();
    const sns3      = String(data[targetRow - 1][6] || "").trim();
    const lgUidStored3 = String(data[targetRow - 1][24] || "").trim();
    const lgInfo3   = getLGInfo(lgKey3);
    const lgUid3    = lgUidStored3 && /^U[A-Z0-9]+$/.test(lgUidStored3) ? lgUidStored3
                    : (/^U[A-Z0-9]+$/.test(lgKey3) ? lgKey3 : lgInfo3.slackUid);
    const lgMention3 = lgUid3 ? `<@${lgUid3}>` : (lgInfo3.name || lgKey3 || "未登録");
    const caUid3    = _getCASlackUid(caName3);
    const caMention3 = caUid3 ? `<@${caUid3}>` : (caName3 || "未確定");

    // 当日キャンセルなら 当日キャンセル面談 タブに追記
    try {
      const todayStr = formatDate(new Date());
      if (confTime3 && confTime3.startsWith(todayStr)) {
        const todaySh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("当日キャンセル面談");
        if (todaySh) {
          const reporterName = payload.user?.id ? _resolveSlackUserName(payload.user.id) : "";
          todaySh.appendRow([
            _padNo(rowNo), account3, grade3, sns3, confTime3,
            lgInfo3.name || lgKey3, caName3,
            formatDatetime(new Date()), reporterName || user,
          ]);
        }
      }
    } catch(e) { Logger.log("[cancel→当日キャンセル] " + e); }

    // フェーズを「キャンセル」に
    sheet.getRange(targetRow, 22).setValue("キャンセル");

    // CAカレンダーから該当予定を削除
    let delResult = { ok: false, reason: "no_ca" };
    if (caName3) {
      const calId3 = _getCalIdByCaName(caName3);
      if (calId3) delResult = _deleteCalendarEventByRowNo(calId3, rowNo);
    }

    // v5.7.1: 押下者(報告者) を記録 — 学生・CAキャンセル一覧 + スレッド通知に含める
    const reporterUid = payload.user?.id || "";
    const reporterName = reporterUid ? _resolveSlackUserName(reporterUid) : "";
    const reporterMention = reporterUid ? `<@${reporterUid}>` : (reporterName || "不明");

    // スレッド通知
    const cancelMsg = [
      `❌ *#${_padNo(rowNo)} 面談キャンセル*`,
      ``,
      `・担当LG: ${lgMention3}`,
      `・担当CA: ${caMention3}`,
      `・学生: ${account3}`,
      confTime3 ? `・元の予定: ${confTime3}` : null,
      `・報告者: ${reporterMention}`,
      ``,
      delResult.ok
        ? `カレンダー予定を削除しました（${delResult.deleted || 1}件）`
        : `カレンダー予定の自動削除に失敗しました（${delResult.reason || "unknown"}）。CA側で手動削除をお願いします`,
      `→ 学生からの事前キャンセルのため、CAは予定削除のみで対応してください`,
    ].filter(Boolean).join("\n");
    sendSlackMessage(channel, cancelMsg, null, msgTs);
  }
}

function _getCASlackUid(caName) {
  const row = _caListRows().find(r => String(r[0]).trim() === caName);
  return row ? String(row[2] || "").trim() : "";
}

// v5.7+: CA名 → カレンダーID
function _getCalIdByCaName(caName) {
  const row = _caListRows().find(r => String(r[0]).trim() === String(caName).trim());
  return row ? String(row[1] || "").trim() : "";
}

// v5.7+: 連携番号でCAカレンダーから該当イベントを検索→削除
function _deleteCalendarEventByRowNo(calId, rowNo) {
  if (!calId || !rowNo) return { ok: false, reason: "no_calId_or_rowNo" };
  const padded = _padNo(rowNo);
  const timeMin = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString();
  const timeMax = new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString();
  try {
    const res = Calendar.Events.list(calId, { timeMin, timeMax, singleEvents: true, maxResults: 500, q: padded });
    const targets = (res.items || []).filter(ev => String(ev.summary || "").startsWith(`#${padded} `));
    if (targets.length === 0) return { ok: false, reason: "not_found" };
    let deleted = 0;
    for (const ev of targets) {
      try { Calendar.Events.remove(calId, ev.id, { sendUpdates: "none" }); deleted++; }
      catch(e) { Logger.log(`[DelCal] ${ev.id}: ${e}`); }
    }
    return { ok: deleted > 0, deleted };
  } catch(e) {
    Logger.log(`[DelCal] list失敗 ${calId}: ${e}`);
    return { ok: false, reason: String(e).slice(0, 80) };
  }
}

// v5.7: LG担当を Slack メンション形式に解決（UID未登録時は名前フォールバック）
function _resolveLGMention(lgMemberOrUid) {
  const key = String(lgMemberOrUid || "").trim();
  if (!key) return "未登録";
  const info = getLGInfo(key);
  const uid  = /^U[A-Z0-9]+$/.test(key) ? key : info.slackUid;
  return uid ? `<@${uid}>` : (info.name || key);
}

// v5.7: CA担当を Slack メンション形式に解決（UID未登録時は名前フォールバック）
function _resolveCAMention(caName) {
  const name = String(caName || "").trim();
  if (!name) return "未確定";
  const uid = _getCASlackUid(name);
  return uid ? `<@${uid}>` : name;
}

// 飛び報告: 該当カレンダーイベントを削除せず description にメモを追記、タイトルに [飛び] プレフィックス
function _annotateEventNoShow(calId, confirmedStr, user) {
  try {
    const m = confirmedStr.match(/(\d{4}[\/\-]\d{2}[\/\-]\d{2})\s+(\d{2}:\d{2})/);
    if (!m) return;
    const startDt = new Date(`${m[1].replace(/\//g,"-")}T${m[2]}:00+09:00`);
    const endDt   = new Date(startDt.getTime() + 90 * 60 * 1000);
    const cal = CalendarApp.getCalendarById(calId);
    if (!cal) return;
    const annotation =
      `\n\n────────\n` +
      `🚫 飛び報告\n` +
      `報告日時: ${formatDatetime(new Date())}\n` +
      `報告者: ${user || "-"}`;
    cal.getEvents(new Date(startDt.getTime() - 5*60*1000), endDt).forEach(ev => {
      const oldDesc = ev.getDescription() || "";
      // 二重追記防止
      if (oldDesc.includes("🚫 飛び報告")) return;
      ev.setDescription(oldDesc + annotation);
      const oldTitle = ev.getTitle() || "";
      if (!oldTitle.startsWith("[飛び]")) ev.setTitle(`[飛び] ${oldTitle}`);
    });
  } catch(e) { Logger.log("[annotateNoShow] " + e); }
}

// ─────────────────────────────────────────
// 空き枠カレンダー描画（v3.9）
//   - アクティブCAのみ集計
//   - 行: 時間（10:00〜20:00 / 30分刻み）
//   - 列: 翌日〜AVAIL_CAL_DAYS日先（曜日付き）
//   - セル: 🟢 ×N 名前 / 🟡 ×N 名前 / 🔴 ×0
// ─────────────────────────────────────────

function renderAvailabilityCalendar() {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    let sheet = ss.getSheetByName(AVAIL_CAL_SHEET);
    if (!sheet) sheet = ss.insertSheet(AVAIL_CAL_SHEET);

    // 1. アクティブCA抽出（v3.8 ステータス連動）
    const activeCAs = _caListRows()
      .filter(r => r[0] && r[1] && String(r[4] || "").trim() === "アクティブ")
      .map(r => ({
        // ID-名前 形式から名前部分のみ抽出（例: CA002-山口扇世 → 山口扇世）
        name:  String(r[0]).trim().replace(/^[A-Za-z]+\d+-/, ""),
        calId: String(r[1]).trim(),
      }));

    if (activeCAs.length === 0) {
      sheet.clearContents();
      sheet.clearFormats();
      sheet.getRange(1,1).setValue("⚠️ アクティブCAが0名です。メンバーシートでステータスを確認してください。");
      return;
    }

    // 2. 期間: 翌日0時 〜 +AVAIL_CAL_DAYS日
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    tomorrow.setHours(0,0,0,0);
    const periodEnd = new Date(tomorrow.getTime() + AVAIL_CAL_DAYS * 24 * 3600 * 1000);

    // 3. 各CAの予定をバルク取得（v5.7+: Advanced Service で外部Gmailカレンダーにも対応）
    const excludeKeywords = getExcludeKeywords();
    // v5.7+: 終日イベント(date only) を JST 0時として解釈（UTC解釈による9hズレを修正）
    const _parseEventDate = (d) => {
      if (!d) return null;
      if (d.dateTime) return new Date(d.dateTime);
      // d.date = "YYYY-MM-DD" → local midnight
      const m = String(d.date).match(/^(\d{4})-(\d{2})-(\d{2})$/);
      if (m) return new Date(+m[1], +m[2] - 1, +m[3]);
      return new Date(d.date);
    };
    // v5.7+: events.list はたまに transient error を返す → 最大3回リトライ + 前回成功結果のキャッシュフォールバック
    const cache = CacheService.getScriptCache();
    const _fetchEvents = (ca) => {
      let lastErr = null;
      for (let attempt = 1; attempt <= 3; attempt++) {
        try {
          const res = Calendar.Events.list(ca.calId, {
            timeMin:      tomorrow.toISOString(),
            timeMax:      periodEnd.toISOString(),
            singleEvents: true,
            maxResults:   2500,
          });
          return (res.items || []).filter(ev => {
            if (ev.status === "cancelled") return false;
            if (_isBlockerEventAdv(ev, excludeKeywords)) return false;
            if (ev.transparency === "transparent") return false;
            if (Array.isArray(ev.attendees)) {
              const self = ev.attendees.find(a => a.email && a.email.toLowerCase() === ca.calId.toLowerCase());
              if (self && self.responseStatus === "declined") return false;
            }
            return true;
          }).map(ev => ({
            start: _parseEventDate(ev.start),
            end:   _parseEventDate(ev.end),
          }));
        } catch(err) {
          lastErr = err;
          Logger.log(`[Avail] retry${attempt} fail ca=${ca.name}: ${err}`);
          if (attempt < 3) Utilities.sleep(400 * attempt);
        }
      }
      throw lastErr || new Error("unknown fetch failure");
    };

    const caEventMaps = activeCAs.map(ca => {
      const cacheKey = "__avail_events_" + ca.calId;
      try {
        const events = _fetchEvents(ca);
        // 成功 → キャッシュ更新（serialize: start/end は Date → ISO 文字列）
        try {
          const serial = events.map(e => ({ s: e.start.toISOString(), e: e.end.toISOString() }));
          cache.put(cacheKey, JSON.stringify(serial), 3600);  // 1h
        } catch(_) {}
        Logger.log(`[Avail] ${ca.name} (${ca.calId}) events=${events.length}`);
        return { ca, events };
      } catch(err) {
        Logger.log(`[Avail] events取得エラー ca=${ca.name} (${ca.calId}): ${err} → cacheから復元試行`);
        // 失敗 → 前回成功結果から復元（あれば）
        try {
          const cached = cache.get(cacheKey);
          if (cached) {
            const serial = JSON.parse(cached);
            const events = serial.map(o => ({ start: new Date(o.s), end: new Date(o.e) }));
            Logger.log(`[Avail] ${ca.name} cache fallback events=${events.length}`);
            return { ca, events };
          }
        } catch(_) {}
        // キャッシュも無い → null (アクセス失敗扱いで除外)
        return { ca, events: null };
      }
    });

    // 4. グリッド構築
    // 最終枠は (HOUR_END - 1) 開始 → HOUR_END 終了
    const slotCount = Math.floor((AVAIL_CAL_HOUR_END - AVAIL_CAL_HOUR_START) * 60 / getSlotStepMin()) - 1;

    const headerRow = ["時間 \\ 日付"];
    for (let d = 0; d < AVAIL_CAL_DAYS; d++) {
      const dt  = new Date(tomorrow.getTime() + d * 24*3600*1000);
      const dow = ["日","月","火","水","木","金","土"][dt.getDay()];
      headerRow.push(`${String(dt.getMonth()+1).padStart(2,"0")}/${String(dt.getDate()).padStart(2,"0")}(${dow})`);
    }

    const valueRows = [];
    const bgRows    = [];
    const totalCAs  = activeCAs.length;
    // v5.7+: 日別の空き枠サマリ（≥1 CAが空いてるスロット数）
    const dayFreeSlotCount = new Array(AVAIL_CAL_DAYS).fill(0);

    for (let s = 0; s < slotCount; s++) {
      const totalMin = AVAIL_CAL_HOUR_START * 60 + s * getSlotStepMin();
      const hh = Math.floor(totalMin / 60);
      const mm = totalMin % 60;
      const timeLabel = `${String(hh).padStart(2,"0")}:${String(mm).padStart(2,"0")}`;
      const valueRow = [timeLabel];
      const bgRow    = ["#FFFFFF"];

      for (let d = 0; d < AVAIL_CAL_DAYS; d++) {
        const slotStart = new Date(tomorrow.getTime() + d * 24*3600*1000 + totalMin * 60 * 1000);
        const slotEnd   = new Date(slotStart.getTime() + getMeetingDurationMin() * 60 * 1000);
        // v5.7+: ビジネスアワー外のCA / events=null(アクセス失敗) は「空き」と数えない
        const freeCAs = caEventMaps.filter(({ ca, events }) =>
          events !== null &&
          _isCAAvailableInHours(ca.calId, slotStart, slotEnd) &&
          !events.some(ev => ev.start < slotEnd && ev.end > slotStart)
        ).map(({ ca }) => ca.name);

        const free = freeCAs.length;
        if (free > 0) dayFreeSlotCount[d]++;
        // v5.7+: 名前は ID-Prefix を除去し、最初の2文字（姓）に短縮
        const shortNames = freeCAs.map(n => _shortHumanName(n).slice(0, 3));
        let label, bg;
        if (free === 0) {
          label = ""; bg = "#fce8e6";  // 薄い赤（busy 強調）
        } else if (free === 1) {
          label = `×${free}  ${shortNames.join(" ")}`; bg = "#fff7d6";
        } else if (free <= 3) {
          label = `×${free}  ${shortNames.join(" ")}`; bg = "#fff3c4";
        } else if (free < totalCAs) {
          label = `×${free}  ${shortNames.join(" ")}`; bg = "#e6f4ea";
        } else {
          label = `×${free}  ALL`; bg = "#a8d5ba";
        }
        valueRow.push(label);
        bgRow.push(bg);
      }
      valueRows.push(valueRow);
      bgRows.push(bgRow);
    }

    // 5. シート書き込み
    // v5.1: 既存の merge / 固定行列を解除（再描画時の merge 衝突エラー回避）
    sheet.getRange(1, 1, sheet.getMaxRows(), sheet.getMaxColumns()).breakApart();
    sheet.setFrozenRows(0);
    sheet.setFrozenColumns(0);
    sheet.clearContents();
    sheet.clearFormats();

    // v5.7+: グリッド線非表示・ヘッダー = Bakuraku navy / Noto Sans JP
    sheet.setHiddenGridlines(true);

    const updateLabel = `空き枠カレンダー  ｜  最終更新: ${formatDatetime(new Date())}  ｜  アクティブCA ${totalCAs}名`;
    sheet.getRange(1,1,1, headerRow.length).merge()
      .setValue(updateLabel)
      .setFontWeight("bold").setFontSize(12).setBackground("#233447").setFontColor("#FFFFFF")
      .setFontFamily("Noto Sans JP")
      .setHorizontalAlignment("left").setVerticalAlignment("middle");

    // v5.7+: 行 2 = サマリー行（日別空き枠数）
    const totalFreeSlots = dayFreeSlotCount.reduce((a, b) => a + b, 0);
    const summaryRow = [`空き合計  ×${totalFreeSlots}`];
    for (let d = 0; d < AVAIL_CAL_DAYS; d++) {
      summaryRow.push(`×${dayFreeSlotCount[d]}`);
    }
    // サマリー行: 空きが多い日は濃い緑、少ない日は薄い赤のグラデーション
    const summaryBgs = ["#1f2e3d"];
    const summaryFgs = ["#a8d5ba"];
    for (let d = 0; d < AVAIL_CAL_DAYS; d++) {
      const n = dayFreeSlotCount[d];
      if (n === 0)       { summaryBgs.push("#fce8e6"); summaryFgs.push("#a02828"); }
      else if (n < 6)    { summaryBgs.push("#fff7d6"); summaryFgs.push("#7c5e10"); }
      else if (n < 15)   { summaryBgs.push("#e6f4ea"); summaryFgs.push("#1e6b3a"); }
      else               { summaryBgs.push("#a8d5ba"); summaryFgs.push("#0f3d22"); }
    }
    sheet.getRange(2, 1, 1, headerRow.length).setValues([summaryRow])
      .setFontWeight("bold").setFontSize(11).setFontFamily("Noto Sans JP")
      .setBackgrounds([summaryBgs]).setFontColors([summaryFgs])
      .setHorizontalAlignment("center").setVerticalAlignment("middle");

    // 行 3 = 日付ヘッダー (土日色分け)
    const dateBgs = ["#233447"];
    const dateFgs = ["#FFFFFF"];
    for (let d = 0; d < AVAIL_CAL_DAYS; d++) {
      const dt = new Date(tomorrow.getTime() + d * 24*3600*1000);
      const dow = dt.getDay();
      if (dow === 0) { dateBgs.push("#fdebeb"); dateFgs.push("#a02828"); }
      else if (dow === 6) { dateBgs.push("#e3eefa"); dateFgs.push("#1a4e8c"); }
      else { dateBgs.push("#f4f5f7"); dateFgs.push("#233447"); }
    }
    sheet.getRange(3, 1, 1, headerRow.length).setValues([headerRow])
      .setFontWeight("bold").setFontSize(11).setFontFamily("Noto Sans JP")
      .setBackgrounds([dateBgs]).setFontColors([dateFgs])
      .setHorizontalAlignment("center").setVerticalAlignment("middle");

    // 行 4+ = タイムグリッド
    sheet.getRange(4, 1, slotCount, headerRow.length).setValues(valueRows);
    sheet.getRange(4, 1, slotCount, headerRow.length).setBackgrounds(bgRows);
    sheet.getRange(4, 1, slotCount, headerRow.length)
      .setVerticalAlignment("middle").setHorizontalAlignment("center")
      .setFontFamily("Noto Sans JP").setFontSize(10).setFontColor("#233447");
    sheet.getRange(4, 1, slotCount, headerRow.length).setWrap(true);

    // 時間列(A列)は強調
    sheet.getRange(4, 1, slotCount, 1)
      .setBackground("#f4f5f7").setFontColor("#233447")
      .setFontWeight("bold").setFontFamily("IBM Plex Mono").setFontSize(10);
    for (let s = 0; s < slotCount; s++) {
      const totalMin = AVAIL_CAL_HOUR_START * 60 + s * getSlotStepMin();
      if (totalMin % 60 === 0) {
        sheet.getRange(4 + s, 1).setBackground("#e8eaed");
      }
    }

    // 列幅・行高
    sheet.setColumnWidth(1, 90);
    for (let c = 2; c <= headerRow.length; c++) {
      const dt = new Date(tomorrow.getTime() + (c - 2) * 24*3600*1000);
      const dow = dt.getDay();
      sheet.setColumnWidth(c, (dow === 0 || dow === 6) ? 105 : 120);
    }
    sheet.setRowHeight(1, 36);
    sheet.setRowHeight(2, 32);
    sheet.setRowHeight(3, 30);
    sheet.setRowHeights(3, slotCount, 30);

    // 罫線: 時間境界(hh:00)で水平線を太く
    sheet.getRange(3, 1, slotCount, headerRow.length)
      .setBorder(true, true, true, true, true, true, "#e0e0e0", SpreadsheetApp.BorderStyle.SOLID);

    sheet.setFrozenRows(2);
    sheet.setFrozenColumns(1);

    Logger.log(`[Avail] 描画完了: アクティブCA=${totalCAs} / 期間=${AVAIL_CAL_DAYS}日 / スロット=${slotCount}`);
  } catch(e) {
    Logger.log("[Avail] ERROR: " + e + " stack: " + e.stack);
  }
}

// ─────────────────────────────────────────
// チェックボックス変更（installable trigger）
// ─────────────────────────────────────────

function onEditInstallable(e) {
  const cfg = getConfig();
  // v5.0: 全卒年シートで反応
  if (!GRADE_SHEET_RE.test(e.source.getActiveSheet().getName())) return;
  const { range } = e;
  if (range.getRow() <= 1) return;

  const channel = cfg["Slack ワークフローチャンネルID"] || cfg["Slack テストチャンネルID"];
  const data    = e.source.getActiveSheet().getDataRange().getValues();
  const rowData = data[range.getRow() - 1];
  const rowNo   = rowData[0];
  const slackTs = String(rowData[25]).trim();
  if (!slackTs) return;

  const account = String(rowData[4] || "").trim();
  const grade   = String(rowData[5] || "").trim();
  const sns     = String(rowData[6] || "").trim();
  const lgName  = String(rowData[2] || "").trim();
  const caName  = String(rowData[19] || "").trim();
  const editorEmail = (e.user && typeof e.user.getEmail === "function") ? e.user.getEmail() : "";
  // v5.7+: 編集者メールをSlackメンションに変換（失敗時はメールフォールバック）
  const reporter = _resolveEmailToMention(editorEmail) || (editorEmail || "手動チェック");

  // W列（重複チェック）ON: CAが面談後に重複発覚した時の通知
  if (range.getColumn() === 23 && range.getValue() === true) {
    // LGメンバーUID解決（rowData[2]はUID直接 or 名前 → getLGInfoでUID取得）
    const lgInfo    = getLGInfo(rowData[2]);
    const lgUidRaw  = String(rowData[2] || "").trim();
    const lgUid     = lgInfo.slackUid || (/^U[A-Z0-9]+$/.test(lgUidRaw) ? lgUidRaw : "");
    const lgMention = lgUid ? `<@${lgUid}>` : (lgInfo.name || lgName || "担当LG");
    // v5.7+: 担当CAもメンション化
    const caUid     = _getCASlackUid(caName);

    const detail = `${lgMention} → この学生は既に登録済みでした。SF側のステータス整理・過去面談ログの確認をお願いします。`;
    sendSlackMessage(channel, formatNotification({
      statusEmoji: "⚠️", title: "重複発覚（CAから報告）", rowNo,
      account, grade, sns, lgUid, caUid, caName, detail, reporter,
    }), null, slackTs);
    return;
  }

  // V列（フェーズ）= 「調整不可」が手動入力された場合
  if (range.getColumn() === 22 && String(range.getValue()).trim() === "調整不可") {
    // v5.7: LG担当をmention化
    const _lgInfoX = getLGInfo(rowData[2]);
    const _lgUidRawX = String(rowData[2] || "").trim();
    const _lgUidX = _lgInfoX.slackUid || (/^U[A-Z0-9]+$/.test(_lgUidRawX) ? _lgUidRawX : "");
    sendSlackMessage(channel, formatNotification({
      statusEmoji: "🚫", title: "調整不可フラグ", rowNo,
      account, grade, sns, lgUid: _lgUidX,
      detail: "全CAで調整不可。学生側へのフォロー・別動線検討をお願いします。",
      reporter,
    }), null, slackTs);
    addReaction(channel, slackTs, "no_entry");
  }
}

// v5.7+: 編集者のメールアドレスを Slack <@UID> メンションに変換
//   - Slack の users.lookupByEmail API を呼び出す
//   - 失敗時は null を返す（呼び出し側でフォールバック）
function _resolveEmailToMention(email) {
  if (!email) return null;
  try {
    const token = getConfig()["Slack Bot Token"];
    const res = UrlFetchApp.fetch(
      "https://slack.com/api/users.lookupByEmail?email=" + encodeURIComponent(email),
      { headers: { Authorization: "Bearer " + token }, muteHttpExceptions: true }
    );
    const r = JSON.parse(res.getContentText());
    if (r.ok && r.user?.id) return `<@${r.user.id}>`;
  } catch(e) { Logger.log("[resolveEmail] " + e); }
  return null;
}

// ─────────────────────────────────────────
// 当日面談リマインド（毎朝9時）→ passチャンネルに送信
// ─────────────────────────────────────────

function sendDailyReminders() {
  const cfg     = getConfig();
  const channel = cfg["Slack passチャンネルID"] || cfg["Slack ワークフローチャンネルID"] || cfg["Slack テストチャンネルID"];

  const todayStr = formatDate(new Date());
  const list = [];
  // v5.0: 全卒年シート横断で当日の実施予定を集約
  for (const sheet of getAllGradeSheets()) {
    const lastRow = sheet.getLastRow();
    if (lastRow < 2) continue;
    const data = sheet.getRange(1, 1, lastRow, GRADE_SHEET_COLS).getValues();
    for (let i = 1; i < data.length; i++) {
      if (!data[i][0]) continue;
      if (String(data[i][21]) !== "実施予定") continue;
      if (!String(data[i][18]).includes(todayStr)) continue;
      const caUid = _getCASlackUid(String(data[i][19]).trim());
      // v5.7: LG担当もmention化
      const _lgKey = String(data[i][2] || "").trim();
      const _lgInfo = getLGInfo(_lgKey);
      const _lgUid  = /^U[A-Z0-9]+$/.test(_lgKey) ? _lgKey : _lgInfo.slackUid;
      list.push({
        no:      data[i][0],
        account: data[i][4],
        conf:    data[i][18],
        ca:      caUid ? `<@${caUid}>` : String(data[i][19]),
        lg:      _lgUid ? `<@${_lgUid}>` : (_lgInfo.name || _lgKey),
        meet:    data[i][20],
      });
    }
  }
  if (!list.length) return;

  const blocks = [{ type: "header", text: { type: "plain_text", text: `📅 本日の面談 ${list.length}件` } }];
  list.forEach(m => {
    blocks.push({ type: "section", text: { type: "mrkdwn", text: `*#${m.no}* ${m.account}\n担当LG: ${m.lg}\n担当CA: ${m.ca}\n日時: ${m.conf}\nMeet: ${m.meet}` } });
    blocks.push({ type: "divider" });
  });
  sendSlackMessage(channel, `本日の面談: ${list.length}件`, blocks, null);
}

// ─────────────────────────────────────────
// 管理票 設定数+1（v3.1: UID→名前自動解決）
// ─────────────────────────────────────────

function updateSettingCount(lgMemberOrUid) {
  try {
    const lgName = _resolveToLGName(lgMemberOrUid);
    if (!lgName) { Logger.log("[settingCount] LG名解決失敗: " + lgMemberOrUid); return; }

    const ss    = SpreadsheetApp.openById(KANRI_SS_ID);
    const sheet = ss.getSheets()[0];
    const data  = sheet.getDataRange().getValues();
    const now   = new Date();
    const key   = `${now.getFullYear()}/${String(now.getMonth()+1).padStart(2,"0")}`;

    let monthCol = -1;
    for (let c = 7; c < data[0].length; c++) {
      if (String(data[0][c]).includes(key)) { monthCol = c; break; }
    }
    if (monthCol < 0) { Logger.log("[settingCount] 今月列なし: " + key); return; }

    const name = lgName.includes("-") ? lgName.split("-").slice(1).join("-") : lgName;
    let memberRow = -1;
    for (let r = 1; r < data.length; r++) {
      if (String(data[r][6]).includes(name)) { memberRow = r; break; }
    }
    if (memberRow < 0) { Logger.log("[settingCount] メンバー未検出: " + lgName); return; }

    sheet.getRange(memberRow + 1, monthCol + 1).setValue((parseInt(data[memberRow][monthCol]) || 0) + 1);
  } catch(e) { Logger.log("[settingCount] " + e); }
}

function _resolveToLGName(lgMemberOrUid) {
  const key = String(lgMemberOrUid || "").trim();
  if (!key) return "";
  if (/^U[A-Z0-9]+$/.test(key)) {
    const info = getLGInfo(key);
    return info.name || "";
  }
  return key;
}

// ─────────────────────────────────────────
// Salesforce 連携
// ─────────────────────────────────────────

const SF_SOQL = `SELECT Id, LastName, FirstName, KanaLastName__c, KanaFirstName__c,
  GraduationYears__c, UniversityName__c, SheetNumber__c,
  CustomerTransferExistence__c, Account.gakka__c
  FROM Contact
  WHERE SheetNumber__c != null AND SheetNumber__c != 0
  LIMIT 200`;

const SF_COL_OFFSET = 31; // v5.4: AE列 = 31列目（AB/AC/AD はリマインド管理列に予約）
const COL_SKIP_SF       = 28; // AB: SF同期除外フラグ
const COL_REMIND_FLAGS  = 29; // AC: リマインド送信フラグ（"12h|24h|36h"）
const COL_LAST_REMINDED = 30; // AD: 最終リマインド時刻

function getSFAccessToken() {
  const cfg      = getConfig();
  const loginUrl = String(cfg["SF ログインURL"] || "https://login.salesforce.com").replace(/\/+$/, "");
  const res = UrlFetchApp.fetch(`${loginUrl}/services/oauth2/token`, {
    method: "post",
    contentType: "application/x-www-form-urlencoded",
    payload: {
      grant_type:    "password",
      client_id:     cfg["SF Consumer Key"],
      client_secret: cfg["SF Consumer Secret"],
      username:      cfg["SF ユーザー名"],
      password:      String(cfg["SF パスワード+セキュリティトークン"] || ""),
    },
    muteHttpExceptions: true,
  });
  const data = JSON.parse(res.getContentText());
  if (!data.access_token) throw new Error("[SF] 認証失敗: " + JSON.stringify(data));
  return { token: data.access_token, instanceUrl: data.instance_url };
}

function syncSalesforce() {
  const cfg = getConfig();
  if (!cfg["SF Consumer Key"] || !cfg["SF ユーザー名"]) {
    Logger.log("[SF Sync] SF認証情報未設定"); return;
  }

  let sfToken, instanceUrl;
  try {
    ({ token: sfToken, instanceUrl } = getSFAccessToken());
  } catch(e) { Logger.log("[SF Sync] 認証エラー: " + e); return; }

  const soql     = encodeURIComponent(SF_SOQL.replace(/\n\s*/g, " "));
  const queryRes = UrlFetchApp.fetch(`${instanceUrl}/services/data/v60.0/query?q=${soql}`, {
    headers: { Authorization: "Bearer " + sfToken },
    muteHttpExceptions: true,
  });
  const queryData = JSON.parse(queryRes.getContentText());
  if (queryData.error || queryData.errors) {
    Logger.log("[SF Sync] Query Error: " + JSON.stringify(queryData)); return;
  }

  const records = queryData.records || [];
  if (!records.length) { Logger.log("[SF Sync] 対象レコードなし"); return; }

  // v5.0: 全卒年シート横断で SheetNumber__c → 行 を解決
  const allSheets = getAllGradeSheets();
  allSheets.forEach(_ensureSFHeaders);

  let updatedCount = 0;
  for (const rec of records) {
    const sfNo = parseInt(rec.SheetNumber__c, 10);
    if (isNaN(sfNo) || sfNo <= 0) continue;

    const found = findRowByNo(sfNo);
    if (!found) continue;
    const { sheet, rowIdx, data } = found;

    const sfRow = [
      rec.LastName                     || "",
      rec.FirstName                    || "",
      rec.KanaLastName__c              || "",
      rec.KanaFirstName__c             || "",
      rec.GraduationYears__c           || "",
      rec.UniversityName__c            || "",
      rec.Account?.gakka__c            || "",
      rec.CustomerTransferExistence__c ? "✅" : "",
    ];
    sheet.getRange(rowIdx + 1, SF_COL_OFFSET, 1, sfRow.length).setValues([sfRow]);

    if (String(data[rowIdx][21]) !== "実施済") {
      sheet.getRange(rowIdx + 1, 22).setValue("実施済");
      updateJisshuCount(String(data[rowIdx][2]));
      Logger.log(`[SF Sync] #${sfNo} → 実施済 (${sheet.getName()})`);
      updatedCount++;
    }
  }

  setConfig("最終SF同期日時", Utilities.formatDate(new Date(), "Asia/Tokyo", "yyyy/MM/dd HH:mm"));
  Logger.log(`[SF Sync] 完了: ${updatedCount}件更新`);
}

function _ensureSFHeaders(sheet) {
  const headers = ["姓（SF）", "名（SF）", "フリガナ姓", "フリガナ名", "卒年（SF）", "大学名（SF）", "学科名", "送客済み"];
  const row1    = sheet.getRange(1, SF_COL_OFFSET, 1, headers.length).getValues()[0];
  if (row1[0] === headers[0]) return;
  sheet.getRange(1, SF_COL_OFFSET, 1, headers.length).setValues([headers]);
  styleHeader(sheet, SF_COL_OFFSET + headers.length - 1);
}

function updateJisshuCount(lgMemberOrUid) {
  try {
    const lgName = _resolveToLGName(lgMemberOrUid);
    if (!lgName) return;

    const ss    = SpreadsheetApp.openById(KANRI_SS_ID);
    const sheet = ss.getSheets()[0];
    const data  = sheet.getDataRange().getValues();
    const now   = new Date();
    const key   = `${now.getFullYear()}/${String(now.getMonth()+1).padStart(2,"0")}`;

    let monthCol = -1;
    for (let c = 7; c < data[0].length; c++) {
      if (String(data[0][c]).includes(key)) { monthCol = c; break; }
    }
    if (monthCol < 0) { Logger.log("[jisshuCount] 今月列なし"); return; }

    const name = lgName.includes("-") ? lgName.split("-").slice(1).join("-") : lgName;
    let memberRow = -1;
    for (let r = 1; r < data.length; r++) {
      if (String(data[r][6]).includes(name)) { memberRow = r; break; }
    }
    if (memberRow < 0) return;

    sheet.getRange(memberRow + 1, monthCol + 2).setValue((parseInt(data[memberRow][monthCol + 1]) || 0) + 1);
  } catch(e) { Logger.log("[jisshuCount] " + e); }
}

// ─────────────────────────────────────────
// 卒年シート関連（v5.0）
// ─────────────────────────────────────────

const SHEET_HEADERS = [
  "No.", "登録日", "LGメンバー", "LINE追加URL", "学生アカウント名", "卒年",
  "SNS種別", "志望業界", "相談内容", "候補日①", "候補時間①", "つなぎ方",
  "候補日②", "候補時間②", "(予備)", "候補日③", "候補時間③", "(予備)",
  "確定日時", "CAメンバー", "Meet URL", "フェーズ", "重複チェック",
  "Lステップ登録", "CA確認", "Slack ts", "メモ",
  // v5.4 拡張列
  "_SF除外", "_リマインドフラグ", "_最終リマインド時刻",
];

// 卒年文字列 → シート名（"27卒" / "27" / "2027" / "2027卒" → "連携メイン_27卒"）
function getSheetNameForGrade(grade) {
  const match = String(grade || "").match(/(\d{2,4})/);
  if (!match) return UNCLASSIFIED;
  let n = parseInt(match[1], 10);
  if (n >= 2000) n -= 2000;  // 西暦4桁を2桁に
  if (n < 20 || n > 99) return UNCLASSIFIED;
  return `連携メイン_${n}卒`;
}

// 全卒年シートを取得（連携メイン_XX卒 / 連携メイン_未分類）
function getAllGradeSheets() {
  return SpreadsheetApp.getActiveSpreadsheet().getSheets()
    .filter(s => GRADE_SHEET_RE.test(s.getName()));
}

// 卒年シートを必要に応じて新規作成
function createGradeSheet(grade) {
  const sheetName = getSheetNameForGrade(grade);
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(sheetName);
  if (sheet) return sheet;

  sheet = ss.insertSheet(sheetName);
  sheet.getRange(1, 1, 1, SHEET_HEADERS.length).setValues([SHEET_HEADERS]);
  styleHeader(sheet, SHEET_HEADERS.length);
  sheet.setFrozenRows(1);
  Logger.log(`[卒年シート] 新規作成: ${sheetName}`);
  return sheet;
}

// グローバル No. 採番（全卒年シート横断で一意）
function getNextGlobalRowNo() {
  const props   = PropertiesService.getScriptProperties();
  const current = parseInt(props.getProperty("globalRowNo") || "0", 10);
  const next    = current + 1;
  props.setProperty("globalRowNo", String(next));
  return next;
}

// v5.7+: 連携番号を4桁ゼロ埋め表示（1 → "0001"）
function _padNo(n) {
  return String(n || 0).padStart(4, "0");
}

// v5.7+: SNS種別ごとの LINE追加 LIFF URL
const SNS_LINE_URLS = {
  "Instagram": "https://liff.line.me/1657845972-Y79yjqRL/landing?follow=%40516aknrw&lp=F3Ejz7&liff_id=1657845972-Y79yjqRL",
  "X":         "https://liff.line.me/1657845972-Y79yjqRL/landing?follow=%40516aknrw&lp=Ohe7j3&liff_id=1657845972-Y79yjqRL",
  "TikTok":    "https://liff.line.me/1657845972-Y79yjqRL/landing?follow=%40516aknrw&lp=JuUtkO&liff_id=1657845972-Y79yjqRL",
  "YouTube":   "https://liff.line.me/1657845972-Y79yjqRL/landing?follow=%40516aknrw&lp=OL8WLc&liff_id=1657845972-Y79yjqRL",
  "Threads":   "https://liff.line.me/1657845972-Y79yjqRL/landing?follow=%40516aknrw&lp=1QvvPc&liff_id=1657845972-Y79yjqRL",
  "リファラル": "https://liff.line.me/1657845972-Y79yjqRL/landing?follow=%40516aknrw&lp=ehWACq&liff_id=1657845972-Y79yjqRL",
  "その他":     "https://liff.line.me/1657845972-Y79yjqRL/landing?follow=%40516aknrw&lp=SME5lJ&liff_id=1657845972-Y79yjqRL",
};

// SNSキー（または「その他」自由記述）から LIFF URL を解決
function _getLineUrlForSns(sns) {
  if (sns && SNS_LINE_URLS[sns]) return SNS_LINE_URLS[sns];
  return SNS_LINE_URLS["その他"];  // 知らないSNS/自由記述は「その他」URL
}

// v5.7+: 全タブにデザイン共通適用（グリッド非表示+タブ色+フォント+枠線+行高）
function applyDesignToAllTabs() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  // v5.7+: 色数最小化 (3色のみ)
  //   ドキュメント/データ系 → ネイビー
  //   分析系 → パープル
  //   管理系 → グレー
  const DOC_COLOR  = "#1A2845";  // ネイビー (ドキュメント+データ統合)
  const DATA_COLOR = "#1A2845";  // 同じ
  const ANA_COLOR  = "#9C27B0";  // パープル
  const SYS_COLOR  = "#607D8B";  // グレー
  const tabColors = {
    "マニュアル_LG向け":     DOC_COLOR,
    "マニュアル_CA向け":     DOC_COLOR,
    "システム仕様書":         DOC_COLOR,
    "業務フロー_新旧比較":    DOC_COLOR,
    "ワークフロー図":         DOC_COLOR,
    "CAリスト":              DATA_COLOR,
    "LGリスト":              DATA_COLOR,
    "LG実績ダッシュボード":  ANA_COLOR,
    "空き枠カレンダー":      ANA_COLOR,
    "実績管理":              ANA_COLOR,
    "設定":                  SYS_COLOR,
  };
  const log = [];
  for (const sheet of ss.getSheets()) {
    const name = sheet.getName();
    try {
      sheet.setHiddenGridlines(true);
      if (tabColors[name]) sheet.setTabColor(tabColors[name]);
      else if (/^連携メイン_\d+卒$/.test(name)) sheet.setTabColor(DATA_COLOR);
      const maxR = sheet.getMaxRows();
      const maxC = sheet.getMaxColumns();
      sheet.getRange(1, 1, maxR, maxC).setFontFamily("Noto Sans JP");

      // 連携メイン_NN卒: ヘッダー強調 + 全行 (maxRows) に枠線
      if (/^連携メイン_\d+卒$/.test(name)) {
        const lastCol = Math.max(sheet.getLastColumn(), 30);  // 最低30列に枠線
        const maxRowAll = sheet.getMaxRows();
        if (lastCol >= 1) {
          // ヘッダー (row 1)
          sheet.getRange(1, 1, 1, lastCol)
            .setBackground("#1A2845")
            .setFontColor("#FFFFFF")
            .setFontWeight("bold")
            .setFontSize(10)
            .setVerticalAlignment("middle")
            .setHorizontalAlignment("center");
          sheet.setRowHeight(1, 36);
          sheet.setFrozenRows(1);
          // v5.7+: maxRows 全体に細い罫線
          sheet.getRange(1, 1, maxRowAll, lastCol).setBorder(
            true, true, true, true, true, true,
            "#CFD8DC", SpreadsheetApp.BorderStyle.SOLID
          );
          // 外枠だけ濃く
          sheet.getRange(1, 1, maxRowAll, lastCol).setBorder(
            true, true, true, true, null, null,
            "#1A2845", SpreadsheetApp.BorderStyle.SOLID_MEDIUM
          );
          // wrap (データ範囲のみ)
          const lastRowData = sheet.getLastRow();
          if (lastRowData >= 2) {
            sheet.getRange(2, 1, lastRowData - 1, lastCol).setWrap(true).setVerticalAlignment("middle");
          }
        }
      }

      // CAリスト / LGリスト 等のシンプルなリストにも枠線
      if (name === "CAリスト" || name === "LGリスト" || name === "設定") {
        const lastRow = sheet.getLastRow();
        const lastCol = sheet.getLastColumn();
        if (lastRow >= 1 && lastCol >= 1) {
          sheet.getRange(1, 1, 1, lastCol)
            .setBackground("#1A2845").setFontColor("#FFFFFF").setFontWeight("bold")
            .setVerticalAlignment("middle").setHorizontalAlignment("center");
          sheet.setRowHeight(1, 36);
          sheet.setFrozenRows(1);
          if (lastRow >= 2) {
            sheet.getRange(1, 1, lastRow, lastCol).setBorder(true, true, true, true, true, true, "#CFD8DC", SpreadsheetApp.BorderStyle.SOLID);
            sheet.getRange(1, 1, lastRow, lastCol).setBorder(true, true, true, true, null, null, "#1A2845", SpreadsheetApp.BorderStyle.SOLID_MEDIUM);
            sheet.getRange(2, 1, lastRow - 1, lastCol).setWrap(true).setVerticalAlignment("middle");
          }
        }
      }

      log.push(`${name}: OK`);
    } catch(e) {
      log.push(`${name}: ${String(e).slice(0,80)}`);
    }
  }
  Logger.log("=== applyDesignToAllTabs ===");
  log.forEach(l => Logger.log(l));
  return log;
}

// v5.7+: 設定キャッシュをクリア
function clearConfigCache() {
  try { CacheService.getScriptCache().removeAll(["__cfg__", "__ca_rows__", "__lg_rows__"]); } catch(_) {}
  return "cleared (config + ca_rows + lg_rows)";
}

// v5.7+: ライム/オレンジ/グリーン等の色を全タブで一括置換してモノトーン化 + 枠線追加
function repaintMonotone() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  // 置換対象色（範囲一致でフレキシブルに判定）
  const isLimeOrColored = (h) => {
    const m = String(h).match(/#?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})/i);
    if (!m) return false;
    const r = parseInt(m[1], 16), g = parseInt(m[2], 16), b = parseInt(m[3], 16);
    // 1) ライム (C2D938 ±20)
    if (Math.abs(r - 194) < 30 && Math.abs(g - 217) < 30 && Math.abs(b - 56) < 30) return true;
    // 2) 旧フロー薄オレンジ (FFF3E1 ±20)
    if (Math.abs(r - 255) < 15 && Math.abs(g - 243) < 25 && Math.abs(b - 225) < 30) return true;
    // 3) 新フロー薄グリーン (EDF7E3 ±20)
    if (Math.abs(r - 237) < 20 && Math.abs(g - 247) < 15 && Math.abs(b - 227) < 25) return true;
    // 4) オレンジ強 (FF9800 ±20)
    if (Math.abs(r - 255) < 15 && Math.abs(g - 152) < 30 && Math.abs(b - 0) < 30) return true;
    // 5) グリーン強 (4CAF50 ±20)
    if (Math.abs(r - 76) < 30 && Math.abs(g - 175) < 30 && Math.abs(b - 80) < 30) return true;
    return false;
  };
  const NEW_BG_STRONG = "#455a64";  // ダークグレー (見出し)
  const NEW_BG_LIGHT  = "#f5f7f9";  // 薄グレー (淡背景)
  const NEW_FG = "#ffffff";
  const SUB_FG = "#cfd8dc";
  const log = [];
  for (const sheet of ss.getSheets()) {
    const name = sheet.getName();
    const lastRow = Math.max(sheet.getLastRow(), 1);
    const lastCol = Math.max(sheet.getLastColumn(), 1);
    try {
      const range = sheet.getRange(1, 1, lastRow, lastCol);
      const bgs = range.getBackgrounds();
      let replaced = 0;
      for (let r = 0; r < bgs.length; r++) {
        for (let c = 0; c < bgs[r].length; c++) {
          const bg = String(bgs[r][c]).toLowerCase();
          // ライム/強色 → ダークグレー強
          if (isLimeOrColored(bg)) {
            sheet.getRange(r+1, c+1).setBackground(NEW_BG_STRONG).setFontColor(NEW_FG);
            replaced++;
          }
        }
      }
      // サブタイトル行 (row 2) のライム/グリーン文字色を白寄り灰に
      try {
        const subFg = String(sheet.getRange(2, 1).getFontColor()).toLowerCase();
        if (isLimeOrColored(subFg) || subFg === "#c2d938") {
          sheet.getRange(2, 1, 1, lastCol).setFontColor(SUB_FG);
        }
      } catch(_) {}
      // データ範囲全体に細い枠線
      if (lastRow >= 1 && lastCol >= 1) {
        sheet.getRange(1, 1, lastRow, lastCol).setBorder(
          true, true, true, true, true, true,
          "#CFD8DC", SpreadsheetApp.BorderStyle.SOLID
        );
      }
      log.push(`${name}: ${replaced}箇所置換`);
    } catch(e) { log.push(`${name}: ${String(e).slice(0,80)}`); }
  }
  Logger.log("=== repaintMonotone ===");
  log.forEach(l => Logger.log(l));
  return log;
}

// v5.7+: ワークフロー図 スイムレーン式 (LG | SYS | CA の3レーン)
function buildWorkflowSwimlane() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName("ワークフロー図");
  if (sheet) ss.deleteSheet(sheet);
  const sh = ss.insertSheet("ワークフロー図");

  const NAVY = "#233447";
  const MUTED = "#64748B";
  const BORDER = "#E3E7EF";
  const BG_SOFT = "#F2F4F7";
  const LG_TINT = "#EFF3FB";
  const SYS_TINT = "#F1F5F9";
  const CA_TINT = "#FDF2F4";
  const AMBER_BG = "#FEF3E7";
  const AMBER_FG = "#D97706";

  sh.setHiddenGridlines(true);

  // 列幅: 13列構成
  // LG lane:    A-C (3 cols)
  // arrow gutter: D
  // SYS lane:   E-G
  // arrow gutter: H
  // CA lane:    I-K
  // misc:       L-M
  const widths = [80, 130, 130, 50, 80, 130, 130, 50, 80, 130, 130, 30, 50];
  widths.forEach((w, i) => sh.setColumnWidth(i + 1, w));

  // タイトル
  sh.getRange(1, 1).setValue("ワークフロー図");
  sh.getRange(2, 1).setValue("面談連携システム v5.7 / 3レーン式 (LG | SYS | CA)");
  sh.getRange(1, 1, 1, 13).merge().setBackground(NAVY).setFontColor("#FFFFFF").setFontWeight("bold").setFontSize(20)
    .setFontFamily("Noto Sans JP").setHorizontalAlignment("left").setVerticalAlignment("middle");
  sh.setRowHeight(1, 60);
  sh.getRange(2, 1, 1, 13).merge().setBackground(BG_SOFT).setFontColor(MUTED).setFontSize(10)
    .setFontFamily("Noto Sans JP").setHorizontalAlignment("left").setVerticalAlignment("middle");
  sh.setRowHeight(2, 28);
  sh.getRange(2, 1, 1, 13).setBorder(null, null, true, null, null, null, NAVY, SpreadsheetApp.BorderStyle.SOLID_THICK);

  const sectionRow = (row, title) => {
    sh.getRange(row, 1, 1, 13).merge().setValue(title)
      .setFontColor(NAVY).setFontWeight("bold").setFontSize(14)
      .setFontFamily("Noto Sans JP").setHorizontalAlignment("left").setVerticalAlignment("middle");
    sh.setRowHeight(row, 44);
    sh.getRange(row, 1, 1, 13).setBorder(null, null, true, null, null, null, NAVY, SpreadsheetApp.BorderStyle.SOLID);
  };

  // ── メインフロー ──
  sectionRow(4, "メインフロー — 登録から実施まで");

  // レーンヘッダー (row 5)
  const laneHeader = (col, span, label, bg) => {
    sh.getRange(5, col, 1, span).merge().setValue(label)
      .setBackground(bg).setFontColor("#FFFFFF").setFontWeight("bold").setFontSize(12)
      .setFontFamily("Noto Sans JP").setHorizontalAlignment("center").setVerticalAlignment("middle");
  };
  laneHeader(1, 3, "LG (人)", NAVY);
  laneHeader(5, 3, "SYS (自動)", "#475569");
  laneHeader(9, 3, "CA (人)", NAVY);
  sh.setRowHeight(5, 36);

  // ボックス描画ヘルパー
  // pos: "lg" | "sys" | "ca"  / row: 1行目
  // box は 2行 (title + sub) を merge
  const drawBox = (row, pos, title, sub, opts) => {
    opts = opts || {};
    let startCol, span, tint;
    if (pos === "lg")  { startCol = 1; span = 3; tint = LG_TINT; }
    if (pos === "sys") { startCol = 5; span = 3; tint = SYS_TINT; }
    if (pos === "ca")  { startCol = 9; span = 3; tint = CA_TINT; }
    const borderColor = opts.amber ? AMBER_FG : NAVY;
    const borderStyle = opts.thick ? SpreadsheetApp.BorderStyle.SOLID_THICK : SpreadsheetApp.BorderStyle.SOLID_MEDIUM;
    const bg = opts.amber ? AMBER_BG : tint;
    const fg = opts.dark ? "#FFFFFF" : NAVY;
    const realBg = opts.dark ? NAVY : bg;

    sh.getRange(row, startCol, 1, span).merge().setValue(title)
      .setBackground(realBg).setFontColor(fg).setFontWeight("bold").setFontSize(11)
      .setFontFamily("Noto Sans JP").setHorizontalAlignment("center").setVerticalAlignment("middle");
    sh.setRowHeight(row, 34);
    if (sub) {
      sh.getRange(row + 1, startCol, 1, span).merge().setValue(sub)
        .setBackground(realBg).setFontColor(opts.dark ? "#E2E8F0" : MUTED).setFontSize(9)
        .setFontFamily("Noto Sans JP").setHorizontalAlignment("center").setVerticalAlignment("middle");
      sh.setRowHeight(row + 1, 22);
      sh.getRange(row, startCol, 2, span).setBorder(true, true, true, true, null, null, borderColor, borderStyle);
    } else {
      sh.setRowHeight(row, 56);
      sh.getRange(row, startCol, 1, span).setBorder(true, true, true, true, null, null, borderColor, borderStyle);
    }
  };

  // 各レーンの「下向き矢印」ヘルパー
  const drawArrow = (row, pos) => {
    let col;
    if (pos === "lg")  col = 2;
    if (pos === "sys") col = 6;
    if (pos === "ca")  col = 10;
    sh.getRange(row, col).setValue("▼")
      .setFontSize(18).setFontColor(NAVY).setFontWeight("bold")
      .setHorizontalAlignment("center").setVerticalAlignment("middle");
    sh.setRowHeight(row, 22);
  };

  // レーン間の矢印 (LG→SYS など右向き)
  const drawCrossArrow = (row, fromPos) => {
    let col;
    if (fromPos === "lg")  col = 4;   // LG→SYS
    if (fromPos === "sys") col = 8;   // SYS→CA
    sh.getRange(row, col).setValue("▶")
      .setFontSize(16).setFontColor(NAVY).setFontWeight("bold")
      .setHorizontalAlignment("center").setVerticalAlignment("middle");
  };

  // === フロー描画 ===
  let r = 6;
  // Step 1: LG 学生連絡
  drawBox(r, "lg", "学生から日程受領", "LINE / DM");
  r += 2;
  drawArrow(r, "lg");
  r++;
  // Step 2: LG モーダル送信
  drawBox(r, "lg", "Slack ⚡ 面談登録", "モーダル送信");
  // → SYS へ
  drawCrossArrow(r + 1, "lg");
  // SYS: 重複check (右並び)
  drawBox(r, "sys", "重複チェック", "shet全件マッチ", { amber: true });
  r += 2;
  drawArrow(r, "sys");
  r++;
  // SYS: CA照合
  drawBox(r, "sys", "CAカレンダー照合", "Calendar API");
  r += 2;
  drawArrow(r, "sys");
  r++;
  // SYS: 確定処理
  drawBox(r, "sys", "確定処理", "Cal登録+Meet+シート+LINE URL");
  r += 2;
  drawArrow(r, "sys");
  r++;
  // SYS: Slack通知
  drawBox(r, "sys", "Slack スレッド投稿", "確定 or 未確定");
  // → CA へ
  drawCrossArrow(r + 1, "sys");
  // CA: 通知受信
  drawBox(r, "ca", "通知を確認", "Meet URLメモ / @CAメンション");
  r += 2;
  drawArrow(r, "ca");
  // LG側にも矢印: LGが学生にLINE
  sh.getRange(r, 2).setValue("▼")
    .setFontSize(18).setFontColor(NAVY).setFontWeight("bold")
    .setHorizontalAlignment("center").setVerticalAlignment("middle");
  sh.setRowHeight(r, 22);
  r++;
  // LG: 学生にLINE
  drawBox(r, "lg", "学生にLINE+Meet送付", "LG");
  // CA: 未確定なら日程入力
  drawBox(r, "ca", "未確定なら 📅 日程入力", "希望日程内で調整");
  r += 2;
  // Both → 面談前
  drawArrow(r, "lg");
  drawArrow(r, "ca");
  r++;
  // CA: ✅CA確認
  drawBox(r, "ca", "✅ CA確認", "面談前");
  r += 2;
  drawArrow(r, "ca");
  r++;
  // 面談実施 (中央 SYS lane を3レーン跨ぐ感じで)
  drawBox(r, "sys", "面談実施", "Google Meet", { dark: true, thick: true });
  r += 2;
  drawArrow(r, "sys");
  r++;
  drawBox(r, "sys", "実施済 (SF同期)", "終着", { dark: true, thick: true });
  r += 2;

  // ── イレギュラーフロー ──
  r += 1;
  sectionRow(r, "イレギュラーフロー — 事前キャンセル / リスケ / 飛び報告");
  r++;
  laneHeader(1, 3, "事前キャンセル", NAVY);
  laneHeader(5, 3, "リスケ要望", NAVY);
  laneHeader(9, 3, "無断欠席 (飛び)", NAVY);
  sh.setRowHeight(r, 36);
  // ... 3パターン縦並びの簡易フロー
  const irrFlow = [
    ["学生から事前連絡", "学生から日程変更要望", "学生が予約時刻に来ない"],
    ["▼", "▼", "▼"],
    ["LG: ❌ キャンセル", "LG: 🔁 リスケ依頼", "LG: 🚫 飛び報告"],
    ["▼", "▼", "▼"],
    ["カレンダー予定削除 (自動)", "旧予定削除 + 新候補入力", "カレンダー注記 (自動)"],
    ["▼", "▼", "▼"],
    ["フェーズ → キャンセル", "新候補で CA 再マッチング", "飛びチャンネル通知"],
  ];
  r++;
  irrFlow.forEach((row, i) => {
    [1, 5, 9].forEach((col, idx) => {
      sh.getRange(r + i, col, 1, 3).merge().setValue(row[idx]);
      if (row[idx] === "▼") {
        sh.getRange(r + i, col, 1, 3).setHorizontalAlignment("center").setVerticalAlignment("middle")
          .setFontSize(16).setFontWeight("bold").setFontColor(NAVY);
        sh.setRowHeight(r + i, 22);
      } else {
        sh.getRange(r + i, col, 1, 3).setBackground([LG_TINT, SYS_TINT, CA_TINT][idx])
          .setFontWeight("bold").setHorizontalAlignment("center").setVerticalAlignment("middle")
          .setBorder(true, true, true, true, null, null, NAVY, SpreadsheetApp.BorderStyle.SOLID_MEDIUM);
        sh.setRowHeight(r + i, 38);
      }
    });
  });
  r += irrFlow.length;

  // ── ボタン早見表 ──
  r += 2;
  sectionRow(r, "ボタン早見表");
  r++;
  const btnTable = [
    ["フェーズ", "🔁 (LG)", "❌ (LG)", "🚫 (LG)", "⚠️ (共通)", "✅ CA / 📅 CA"],
    ["実施予定", "🔁 リスケ依頼", "❌ キャンセル", "🚫 飛び報告", "⚠️ 重複報告", "✅ CA確認"],
    ["日程調整中", "🔁 日程再回収", "❌ キャンセル", "🚫 飛び報告", "⚠️ 重複報告", "📅 日程入力"],
  ];
  // 6列を col 1-12 に分散
  const colWidths = [2, 2, 2, 2, 2, 2];  // 各 2 col merge
  let colCursor = 1;
  for (let i = 0; i < btnTable[0].length; i++) {
    const w = colWidths[i];
    sh.getRange(r, colCursor, 1, w).merge().setValue(btnTable[0][i])
      .setBackground(NAVY).setFontColor("#FFFFFF").setFontWeight("bold").setFontSize(10)
      .setFontFamily("Noto Sans JP").setHorizontalAlignment("center").setVerticalAlignment("middle");
    colCursor += w;
  }
  sh.setRowHeight(r, 34);
  r++;
  for (let rowIdx = 1; rowIdx < btnTable.length; rowIdx++) {
    colCursor = 1;
    for (let i = 0; i < btnTable[rowIdx].length; i++) {
      const w = colWidths[i];
      sh.getRange(r + rowIdx - 1, colCursor, 1, w).merge().setValue(btnTable[rowIdx][i])
        .setBackground(BG_SOFT).setFontFamily("Noto Sans JP").setFontSize(10).setHorizontalAlignment("center").setVerticalAlignment("middle");
      colCursor += w;
    }
    sh.setRowHeight(r + rowIdx - 1, 34);
  }
  sh.getRange(r - 1, 1, btnTable.length, 12).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);

  // 全体フォント
  sh.getRange(1, 1, sh.getLastRow(), 13).setFontFamily("Noto Sans JP").setWrap(true);
  sh.setTabColor("#233447");
  return "ワークフロー図 スイムレーン構築完了";
}

// v5.7+: 業務フロー新旧比較 Before/Afterカード型
function buildFlowComparisonCards() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const old = ss.getSheetByName("業務フロー_新旧比較");
  if (old) ss.deleteSheet(old);
  const sh = ss.insertSheet("業務フロー_新旧比較");

  const NAVY = "#233447";
  const MUTED = "#64748B";
  const BORDER = "#E3E7EF";
  const BG_SOFT = "#F2F4F7";
  const BG_BOX = "#F8FAFC";
  const OLD_TINT = "#FFF8F0";
  const NEW_TINT = "#F4FBF5";
  const RED = "#DC2626";
  const GREEN = "#16A34A";

  sh.setHiddenGridlines(true);

  // 列幅: A-K 11列。旧カード = A-D / 中央矢印 = E / 新カード = F-I / 余白 J-K
  const widths = [80, 200, 220, 100, 50, 80, 200, 220, 100, 50, 50];
  widths.forEach((w, i) => sh.setColumnWidth(i + 1, w));

  // タイトル
  sh.getRange(1, 1).setValue("業務フロー 新旧比較");
  sh.getRange(2, 1).setValue("Spir+3チャンネル時代 → v5.7 自動化 / 1件 30-40分 → 2-3分 (約90%削減)");
  sh.getRange(1, 1, 1, 11).merge().setBackground(NAVY).setFontColor("#FFFFFF").setFontWeight("bold").setFontSize(20)
    .setFontFamily("Noto Sans JP").setHorizontalAlignment("left").setVerticalAlignment("middle");
  sh.setRowHeight(1, 60);
  sh.getRange(2, 1, 1, 11).merge().setBackground(BG_SOFT).setFontColor(MUTED).setFontSize(10)
    .setFontFamily("Noto Sans JP").setHorizontalAlignment("left").setVerticalAlignment("middle");
  sh.setRowHeight(2, 28);
  sh.getRange(2, 1, 1, 11).setBorder(null, null, true, null, null, null, NAVY, SpreadsheetApp.BorderStyle.SOLID_THICK);

  const sectionRow = (row, title) => {
    sh.getRange(row, 1, 1, 11).merge().setValue(title)
      .setFontColor(NAVY).setFontWeight("bold").setFontSize(14)
      .setFontFamily("Noto Sans JP").setHorizontalAlignment("left").setVerticalAlignment("middle");
    sh.setRowHeight(row, 44);
    sh.getRange(row, 1, 1, 11).setBorder(null, null, true, null, null, null, NAVY, SpreadsheetApp.BorderStyle.SOLID);
  };

  // ── Before / After ハイレベル カード ──
  sectionRow(4, "高レベル比較 — Before / After");
  // 旧カード (col 1-4) / 中央矢印 (col 5) / 新カード (col 6-9)
  let r = 5;
  // カードタイトル
  sh.getRange(r, 1, 1, 4).merge().setValue("BEFORE   旧フロー (Spir+3ch)")
    .setBackground(RED).setFontColor("#FFFFFF").setFontWeight("bold").setFontSize(13)
    .setFontFamily("Noto Sans JP").setHorizontalAlignment("center").setVerticalAlignment("middle");
  sh.getRange(r, 6, 1, 4).merge().setValue("AFTER   v5.7 自動化")
    .setBackground(GREEN).setFontColor("#FFFFFF").setFontWeight("bold").setFontSize(13)
    .setFontFamily("Noto Sans JP").setHorizontalAlignment("center").setVerticalAlignment("middle");
  sh.setRowHeight(r, 40);
  r++;
  // KPI 行
  const kpis = [
    ["1件あたり作業時間", "30-40分", "2-3分", "約90%削減"],
    ["ステップ数", "14ステップ", "3クリック", "1/4以下"],
    ["Slack投稿回数", "3-4回", "0回 (ボタン)", "100%削減"],
    ["手動入力項目数", "20項目超", "10項目 (1モーダル)", "約50%削減"],
    ["Spir/カレンダー画面遷移", "CA全員分(N画面)", "0", "100%削減"],
    ["重複検知ミスのリスク", "高 (目視)", "低 (自動)", "新機能"],
    ["リマインド漏れリスク", "高 (手動フォロー)", "低 (自動12h/24h)", "新機能"],
    ["カレンダー削除 (キャンセル時)", "手動", "ワンクリック", "自動化"],
  ];
  for (let i = 0; i < kpis.length; i++) {
    sh.getRange(r + i, 1, 1, 3).merge().setValue(kpis[i][0] + ":  " + kpis[i][1])
      .setBackground(OLD_TINT).setFontFamily("Noto Sans JP").setFontSize(10)
      .setHorizontalAlignment("left").setVerticalAlignment("middle");
    sh.getRange(r + i, 4).setValue("→").setFontSize(14).setFontWeight("bold").setFontColor(MUTED).setHorizontalAlignment("center");
    sh.getRange(r + i, 5).setValue(""); // gutter
    sh.getRange(r + i, 6, 1, 3).merge().setValue(kpis[i][0] + ":  " + kpis[i][2])
      .setBackground(NEW_TINT).setFontFamily("Noto Sans JP").setFontSize(10)
      .setHorizontalAlignment("left").setVerticalAlignment("middle");
    sh.getRange(r + i, 9).setValue(kpis[i][3]).setBackground(BG_BOX).setFontWeight("bold").setHorizontalAlignment("center").setFontColor(NAVY);
    sh.setRowHeight(r + i, 36);
  }
  // カード枠
  sh.getRange(5, 1, kpis.length + 1, 4).setBorder(true, true, true, true, null, null, RED, SpreadsheetApp.BorderStyle.SOLID_THICK);
  sh.getRange(5, 6, kpis.length + 1, 4).setBorder(true, true, true, true, null, null, GREEN, SpreadsheetApp.BorderStyle.SOLID_THICK);
  r += kpis.length;
  r += 2;

  // ── 詳細ステップ並列 (横並び) ──
  sectionRow(r, "詳細ステップ — 並列");
  r++;
  // ヘッダー
  sh.getRange(r, 1).setValue("#").setBackground(NAVY).setFontColor("#FFFFFF").setFontWeight("bold").setFontFamily("Noto Sans JP").setHorizontalAlignment("center");
  sh.getRange(r, 2, 1, 2).merge().setValue("旧 (Spir+3ch)").setBackground(RED).setFontColor("#FFFFFF").setFontWeight("bold").setFontFamily("Noto Sans JP").setHorizontalAlignment("center");
  sh.getRange(r, 4).setValue("→").setBackground(BG_SOFT).setHorizontalAlignment("center");
  sh.getRange(r, 5, 1, 2).merge().setValue("新 (v5.7)").setBackground(GREEN).setFontColor("#FFFFFF").setFontWeight("bold").setFontFamily("Noto Sans JP").setHorizontalAlignment("center");
  sh.getRange(r, 7, 1, 3).merge().setValue("自動化内容").setBackground(NAVY).setFontColor("#FFFFFF").setFontWeight("bold").setFontFamily("Noto Sans JP").setHorizontalAlignment("center");
  sh.getRange(r, 10, 1, 2).merge().setValue("効果").setBackground(NAVY).setFontColor("#FFFFFF").setFontWeight("bold").setFontFamily("Noto Sans JP").setHorizontalAlignment("center");
  sh.setRowHeight(r, 36);
  r++;
  const steps = [
    ["1", "学生から候補日程受領", "学生から候補日程受領", "変更なし", "—"],
    ["2", "3 Slackチャンネル投稿", "Slack ⚡ ショートカット", "投稿先1モーダルに集約", "Slack 3→0"],
    ["3", "Cmd+F で重複検索", "(自動)", "checkDuplicate関数で自動", "検索ゼロ"],
    ["4", "CA全員のSpir照合", "(自動)", "Calendar APIで一斉照合", "Spir確認ゼロ"],
    ["5", "Spirで予約 + Meet発行", "(自動)", "Calendar.Events.insert + conferenceData", "手動操作ゼロ"],
    ["6", "Spirに8項目入力", "モーダル1画面で全項目", "8→1画面", "入力 8→1"],
    ["7", "発行URLを学生に手動送付", "Meet URLをスレッドからコピー", "URLは確定スレッド内", "変更なし"],
    ["8", "数値管理シート手動入力", "(自動)", "全項目シート自動記録", "入力ゼロ"],
    ["9", "Pass-ch 申し送り投稿", "(自動)", "スレッド内に自動表示", "投稿ゼロ"],
    ["10", "リマインドは手動", "(自動 12h/24h)", "remindStalledMeetings", "新機能"],
    ["11", "(無) 36h経過対応", "(自動「調整不可」化)", "状態管理自動", "新機能"],
    ["12", "canceled-ch 手動投稿", "❌ キャンセルボタン", "+カレンダー自動削除", "投稿+削除ゼロ"],
    ["13", "リスケは再度全フロー", "🔁 リスケ依頼ボタン", "旧予定削除+再マッチング", "再登録ゼロ"],
    ["14", "cara-ch + 10分待機", "🚫 飛び報告ボタン", "+カレンダー注記", "投稿ゼロ"],
  ];
  for (let i = 0; i < steps.length; i++) {
    sh.getRange(r + i, 1).setValue(steps[i][0]).setBackground(BG_SOFT).setFontWeight("bold").setHorizontalAlignment("center");
    sh.getRange(r + i, 2, 1, 2).merge().setValue(steps[i][1]).setBackground(OLD_TINT);
    sh.getRange(r + i, 4).setValue("→").setHorizontalAlignment("center").setFontColor(MUTED).setFontWeight("bold");
    sh.getRange(r + i, 5, 1, 2).merge().setValue(steps[i][2]).setBackground(NEW_TINT);
    sh.getRange(r + i, 7, 1, 3).merge().setValue(steps[i][3]).setBackground(BG_BOX);
    sh.getRange(r + i, 10, 1, 2).merge().setValue(steps[i][4]).setBackground(BG_BOX).setFontWeight("bold").setHorizontalAlignment("center");
    sh.setRowHeight(r + i, 32);
  }
  sh.getRange(r - 1, 1, steps.length + 1, 11).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);
  sh.getRange(r - 1, 1, steps.length + 1, 11).setFontFamily("Noto Sans JP").setFontSize(10).setVerticalAlignment("middle");

  sh.setTabColor("#233447");
  return "業務フロー比較 Before/Afterカード構築完了";
}

// v5.7+: マニュアル v3 (2カラム LG/CA 並列)
function buildManualV3() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  ["マニュアル_LG向け", "マニュアル_CA向け", "マニュアル"].forEach(n => {
    const sh = ss.getSheetByName(n);
    if (sh) ss.deleteSheet(sh);
  });
  const sh = ss.insertSheet("マニュアル");

  const NAVY = "#233447";
  const MUTED = "#64748B";
  const BORDER = "#E3E7EF";
  const BG_SOFT = "#F2F4F7";
  const BG_BOX = "#F8FAFC";
  const LG_TINT = "#EFF3FB";   // 薄いLG系
  const CA_TINT = "#FDF2F4";   // 薄いCA系
  const ACCENT_BG = "#FEF3E7";
  const ACCENT_FG = "#D97706";

  sh.setHiddenGridlines(true);

  // 列幅: A-M 13列
  // 左カラム (LG) = col 1-6, gutter = col 7, 右カラム (CA) = col 8-13
  const widths = [50, 200, 280, 280, 80, 90, 40, 50, 200, 280, 280, 80, 90];
  widths.forEach((w, i) => sh.setColumnWidth(i + 1, w));

  // タイトル
  sh.getRange(1, 1).setValue("マニュアル — 面談連携システム");
  sh.getRange(2, 1).setValue("v5.7 / 新メンバー向け / 左:LG用 / 右:CA用 / CA初回はSTEP1のカレンダー共有から");
  sh.getRange(1, 1, 1, 13).merge().setBackground(NAVY).setFontColor("#FFFFFF").setFontWeight("bold").setFontSize(20)
    .setFontFamily("Noto Sans JP").setHorizontalAlignment("left").setVerticalAlignment("middle");
  sh.setRowHeight(1, 60);
  sh.getRange(2, 1, 1, 13).merge().setBackground(BG_SOFT).setFontColor(MUTED).setFontSize(10)
    .setFontFamily("Noto Sans JP").setHorizontalAlignment("left").setVerticalAlignment("middle");
  sh.setRowHeight(2, 28);
  sh.getRange(2, 1, 1, 13).setBorder(null, null, true, null, null, null, NAVY, SpreadsheetApp.BorderStyle.SOLID_THICK);

  const sectionFull = (row, title) => {
    sh.getRange(row, 1, 1, 13).merge().setValue(title)
      .setFontColor(NAVY).setFontWeight("bold").setFontSize(14)
      .setFontFamily("Noto Sans JP").setHorizontalAlignment("left").setVerticalAlignment("middle");
    sh.setRowHeight(row, 44);
    sh.getRange(row, 1, 1, 13).setBorder(null, null, true, null, null, null, NAVY, SpreadsheetApp.BorderStyle.SOLID);
  };

  const subHeader = (row, title, startCol, span, bgColor) => {
    sh.getRange(row, startCol, 1, span).merge().setValue(title)
      .setBackground(bgColor || NAVY).setFontColor("#FFFFFF").setFontWeight("bold").setFontSize(12)
      .setFontFamily("Noto Sans JP").setHorizontalAlignment("center").setVerticalAlignment("middle");
    sh.setRowHeight(row, 34);
  };

  // ========== STEP 1 LG/CA 並列の事前準備 ==========
  let r = 4;
  sectionFull(r, "STEP 1.   事前準備");
  r++;
  subHeader(r, "LG向け (新人さんへ)", 1, 6);
  subHeader(r, "CA向け ⚠️ 必須 (初回1回だけ)", 8, 6);
  r++;
  // LG 事前準備 (col 1-6): シンプルな説明テーブル
  const lgPrep = [
    ["#", "やること", "詳細"],
    ["1", "Slack を開ける", "本番チャンネル: #test-lg-ca-連携-new"],
    ["2", "面談登録 ショートカット", "Slack入力欄左の ⚡から「面談登録」"],
    ["3", "学生から日程を受け取る", "LINE/DMで「候補日時を3つください」"],
    ["4", "重複登録に注意", "同じ学生は登録不成立メッセージが出る"],
  ];
  sh.getRange(r, 1, 1, 3).setValues([lgPrep[0]])
    .setBackground(BG_SOFT).setFontWeight("bold").setFontSize(10).setFontFamily("Noto Sans JP")
    .setHorizontalAlignment("center");
  sh.getRange(r, 4, 1, 3).merge(); // 4列目以降は空欄マージ
  sh.setRowHeight(r, 32);
  r++;
  for (let i = 1; i < lgPrep.length; i++) {
    sh.getRange(r + i - 1, 1).setValue(lgPrep[i][0]).setBackground(BG_SOFT).setFontWeight("bold").setHorizontalAlignment("center");
    sh.getRange(r + i - 1, 2).setValue(lgPrep[i][1]);
    sh.getRange(r + i - 1, 3, 1, 4).merge().setValue(lgPrep[i][2]);
    sh.setRowHeight(r + i - 1, 36);
  }
  // CA 事前準備 (col 8-13): カレンダー共有 9ステップ
  const caPrep = [
    ["#", "やること", "詳細"],
    ["1", "Googleカレンダーを開く", "calendar.google.com"],
    ["2", "マイカレンダー欄", "左サイドの自分の名前を探す"],
    ["3", "︙ 3点メニュー", "ホバーで出るメニュー"],
    ["4", "「設定と共有」をクリック", ""],
    ["5", "ページ下部にスクロール", "「特定のユーザーや...」"],
    ["6", "「+ ユーザーを追加」", "ダイアログ表示"],
    ["7", "record@tokumori.co.jp を追加", "GAS所有アカウント"],
    ["8", "権限「予定の変更」に変更", "⚠️ 「閲覧」のままだと失敗"],
    ["9", "「送信」をクリック", "完了"],
  ];
  const caHeaderR = r - 1;
  sh.getRange(caHeaderR, 8, 1, 3).setValues([caPrep[0]])
    .setBackground(BG_SOFT).setFontWeight("bold").setFontSize(10).setFontFamily("Noto Sans JP")
    .setHorizontalAlignment("center");
  sh.getRange(caHeaderR, 11, 1, 3).merge();
  for (let i = 1; i < caPrep.length; i++) {
    sh.getRange(r + i - 1, 8).setValue(caPrep[i][0]).setBackground(BG_SOFT).setFontWeight("bold").setHorizontalAlignment("center");
    sh.getRange(r + i - 1, 9).setValue(caPrep[i][1]);
    sh.getRange(r + i - 1, 10, 1, 4).merge().setValue(caPrep[i][2]);
    sh.setRowHeight(r + i - 1, 36);
  }
  // 罫線 (LG側 1-6 / CA側 8-13)
  const stepBlockHeight = Math.max(lgPrep.length, caPrep.length);
  sh.getRange(caHeaderR, 1, stepBlockHeight, 6).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);
  sh.getRange(caHeaderR, 8, stepBlockHeight, 6).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);
  // LG/CA tint
  sh.getRange(caHeaderR, 1, stepBlockHeight, 6).setBackground(LG_TINT);
  sh.getRange(caHeaderR, 1, 1, 3).setBackground(BG_SOFT);
  sh.getRange(caHeaderR, 8, stepBlockHeight, 6).setBackground(CA_TINT);
  sh.getRange(caHeaderR, 8, 1, 3).setBackground(BG_SOFT);
  // ヘッダー以外を再度色塗り (BG_SOFTを残すため)
  for (let i = 1; i < Math.max(lgPrep.length, caPrep.length); i++) {
    if (i < lgPrep.length) {
      sh.getRange(r + i - 1, 2, 1, 5).setBackground(LG_TINT);
    }
    if (i < caPrep.length) {
      sh.getRange(r + i - 1, 9, 1, 5).setBackground(CA_TINT);
    }
  }
  r += stepBlockHeight - 1;
  r += 2;

  // ========== STEP 2 共通基礎 ==========
  sectionFull(r, "STEP 2.   共通基礎 — 用語 / ビジネスアワー / SNS別URL");
  r++;
  // 3列: 用語(1-4) | ビジネスアワー(6-8) | SNS別URL(10-13)
  const terms = [
    ["LG", "Lead Generator (学生獲得)"],
    ["CA", "Career Adviser (面談実施)"],
    ["スレッド", "Slack返信ツリー (登録ごとに1つ)"],
    ["モーダル", "Slackポップアップ入力画面"],
    ["連携番号", "#0001 4桁ゼロ埋め"],
    ["フェーズ", "面談の状態 (7種類)"],
    ["リスケ", "学生からの日程変更要望"],
    ["飛び", "学生の無断欠席"],
  ];
  subHeader(r, "用語集", 1, 4);
  subHeader(r, "ビジネスアワー", 6, 3);
  subHeader(r, "SNS別 LINE追加URL", 10, 4);
  r++;
  sh.getRange(r, 1).setValue("用語").setBackground(BG_SOFT).setFontWeight("bold").setHorizontalAlignment("center");
  sh.getRange(r, 2, 1, 3).merge().setValue("意味").setBackground(BG_SOFT).setFontWeight("bold").setHorizontalAlignment("center");
  sh.getRange(r, 6).setValue("対象").setBackground(BG_SOFT).setFontWeight("bold").setHorizontalAlignment("center");
  sh.getRange(r, 7, 1, 2).merge().setValue("時間").setBackground(BG_SOFT).setFontWeight("bold").setHorizontalAlignment("center");
  sh.getRange(r, 10).setValue("SNS").setBackground(BG_SOFT).setFontWeight("bold").setHorizontalAlignment("center");
  sh.getRange(r, 11, 1, 3).merge().setValue("LIFF URL末尾").setBackground(BG_SOFT).setFontWeight("bold").setHorizontalAlignment("center");
  sh.setRowHeight(r, 32);
  r++;
  const baseR = r;
  for (let i = 0; i < terms.length; i++) {
    sh.getRange(r + i, 1).setValue(terms[i][0]);
    sh.getRange(r + i, 2, 1, 3).merge().setValue(terms[i][1]);
    sh.setRowHeight(r + i, 32);
  }
  const bhData = [
    ["@tokumori.co.jp", "平日 9-20時"],
    ["", "土日: 予約NG"],
    ["その他 (gmail等)", "毎日 8-23時"],
    ["", ""],
    ["完全空きルール", "1分でも予定があれば回避"],
    ["「ブロック」予定", "尊重 (予約されない)"],
    ["", ""],
    ["休憩したい時間", "予定を入れて自衛"],
  ];
  for (let i = 0; i < bhData.length; i++) {
    sh.getRange(r + i, 6).setValue(bhData[i][0]);
    sh.getRange(r + i, 7, 1, 2).merge().setValue(bhData[i][1]);
  }
  const snsData = [
    ["Instagram", "lp=F3Ejz7"],
    ["X", "lp=Ohe7j3"],
    ["TikTok", "lp=JuUtkO"],
    ["YouTube", "lp=OL8WLc"],
    ["Threads", "lp=1QvvPc"],
    ["リファラル", "lp=ehWACq"],
    ["その他", "lp=SME5lJ"],
    ["", ""],
  ];
  for (let i = 0; i < snsData.length; i++) {
    sh.getRange(r + i, 10).setValue(snsData[i][0]);
    sh.getRange(r + i, 11, 1, 3).merge().setValue(snsData[i][1]);
  }
  // 罫線
  sh.getRange(baseR - 1, 1, 9, 4).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);
  sh.getRange(baseR - 1, 6, 9, 3).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);
  sh.getRange(baseR - 1, 10, 9, 4).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);
  r += 8;
  r += 2;

  // ========== STEP 3 役割別 操作手順 ==========
  sectionFull(r, "STEP 3.   役割別 操作手順 — 左:LG / 右:CA");
  r++;
  subHeader(r, "LG 操作手順", 1, 6);
  subHeader(r, "CA 対応手順", 8, 6);
  r++;
  const lgOps = [
    ["#", "操作", "詳細"],
    ["1", "Slack ⚡ から面談登録", "ショートカット押下 → モーダル"],
    ["2", "モーダル入力", "学生名/卒年/SNS/業界/相談/候補日程"],
    ["3", "送信", "重複なら登録不成立メッセージ"],
    ["4", "結果スレッド確認", "確定/未確定/重複の3パターン"],
    ["5", "学生にLINE送付", "確定スレッド内のMeet URLを送付"],
    ["6", "🔁 リスケ依頼", "学生から日程変更要望時"],
    ["7", "❌ キャンセル", "学生から事前キャンセル時"],
    ["8", "🚫 飛び報告", "学生が当日不参加時"],
    ["9", "⚠️ 重複報告", "重複に気付いた時"],
  ];
  const caOps = [
    ["#", "操作", "詳細"],
    ["1", "通知を見る", "確定 or 未確定 を判別"],
    ["2-A", "確定の場合", "Meet URLをメモ → 当日参加"],
    ["2-B", "未確定 (@CAメンション)", "希望日程内で空きを確認"],
    ["3", "📅 日程入力", "自分が対応する場合のボタン"],
    ["4", "✅ CA確認", "面談前 (準備OKの合図)"],
    ["5", "面談実施", "Google Meet"],
    ["6", "⚠️ 重複報告", "他CAが既に対応中だった時"],
    ["—", "キャンセル/リスケ", "対応不要 (LGが処理)"],
    ["—", "飛び報告", "対応不要 (注記自動)"],
  ];
  // ヘッダー
  sh.getRange(r, 1).setValue("#").setBackground(BG_SOFT).setFontWeight("bold").setHorizontalAlignment("center");
  sh.getRange(r, 2).setValue("操作").setBackground(BG_SOFT).setFontWeight("bold").setHorizontalAlignment("center");
  sh.getRange(r, 3, 1, 4).merge().setValue("詳細").setBackground(BG_SOFT).setFontWeight("bold").setHorizontalAlignment("center");
  sh.getRange(r, 8).setValue("#").setBackground(BG_SOFT).setFontWeight("bold").setHorizontalAlignment("center");
  sh.getRange(r, 9).setValue("操作").setBackground(BG_SOFT).setFontWeight("bold").setHorizontalAlignment("center");
  sh.getRange(r, 10, 1, 4).merge().setValue("詳細").setBackground(BG_SOFT).setFontWeight("bold").setHorizontalAlignment("center");
  sh.setRowHeight(r, 32);
  r++;
  const lgHeight = lgOps.length - 1;
  const caHeight = caOps.length - 1;
  const opHeight = Math.max(lgHeight, caHeight);
  const opStart = r;
  for (let i = 1; i < lgOps.length; i++) {
    sh.getRange(r + i - 1, 1).setValue(lgOps[i][0]).setBackground(LG_TINT).setHorizontalAlignment("center").setFontWeight("bold");
    sh.getRange(r + i - 1, 2).setValue(lgOps[i][1]).setBackground(LG_TINT);
    sh.getRange(r + i - 1, 3, 1, 4).merge().setValue(lgOps[i][2]).setBackground(LG_TINT);
    sh.setRowHeight(r + i - 1, 36);
  }
  for (let i = 1; i < caOps.length; i++) {
    sh.getRange(r + i - 1, 8).setValue(caOps[i][0]).setBackground(CA_TINT).setHorizontalAlignment("center").setFontWeight("bold");
    sh.getRange(r + i - 1, 9).setValue(caOps[i][1]).setBackground(CA_TINT);
    sh.getRange(r + i - 1, 10, 1, 4).merge().setValue(caOps[i][2]).setBackground(CA_TINT);
  }
  // 罫線
  sh.getRange(opStart - 1, 1, opHeight + 1, 6).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);
  sh.getRange(opStart - 1, 8, opHeight + 1, 6).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);
  r += opHeight;
  r += 2;

  // ========== STEP 4 候補時間早見表 + FAQ ==========
  sectionFull(r, "STEP 4.   候補時間フォーマット早見表 / FAQ");
  r++;
  subHeader(r, "候補時間 早見表", 1, 6);
  subHeader(r, "FAQ / トラブルシュート", 8, 6);
  r++;
  // 候補時間 (col 1-6)
  const timeFormat = [
    ["入力", "解釈"],
    ["10:00~12:00", "10:00〜12:00 (標準)"],
    ["10-15", "10:00〜15:00 (簡易)"],
    ["10時以降", "10:00〜23:00"],
    ["午前中 / 午前", "9:00〜12:00"],
    ["午後", "13:00〜23:00"],
    ["夕方", "17:00〜23:00"],
    ["終日 / いつでも", "8:00〜23:00"],
    ["10 / 10時", "10:00 単点 (45分)"],
  ];
  // FAQ (col 8-13)
  const faqs = [
    ["Q", "A"],
    ["[LG] ショートカット見当たらない", "Slack ⚡ から「面談」検索"],
    ["[LG] 送信したのに無反応", "GAS応答待ち3秒越え可能性。再操作"],
    ["[LG] Meet URLどこ", "確定スレッド内「・Meet: ...」"],
    ["[LG] LINE追加URL自動?", "はい。SNS種別で自動セット"],
    ["[CA] 自分に依頼が来ない", "record@ にカレンダー共有を再確認"],
    ["[CA] モーダルが開かない", "ボタン再押下 / GAS warm待ち"],
    ["[CA] 共有したのに反映されない", "数分待つ / 権限「予定の変更」を確認"],
    ["[CA] 土曜に依頼が来た (tokumori)", "システムバグ。報告ください"],
  ];
  sh.getRange(r, 1).setValue(timeFormat[0][0]).setBackground(BG_SOFT).setFontWeight("bold").setHorizontalAlignment("center");
  sh.getRange(r, 2, 1, 5).merge().setValue(timeFormat[0][1]).setBackground(BG_SOFT).setFontWeight("bold").setHorizontalAlignment("center");
  sh.getRange(r, 8).setValue(faqs[0][0]).setBackground(BG_SOFT).setFontWeight("bold").setHorizontalAlignment("center");
  sh.getRange(r, 9, 1, 5).merge().setValue(faqs[0][1]).setBackground(BG_SOFT).setFontWeight("bold").setHorizontalAlignment("center");
  sh.setRowHeight(r, 32);
  r++;
  for (let i = 1; i < Math.max(timeFormat.length, faqs.length); i++) {
    if (i < timeFormat.length) {
      sh.getRange(r + i - 1, 1).setValue(timeFormat[i][0]);
      sh.getRange(r + i - 1, 2, 1, 5).merge().setValue(timeFormat[i][1]);
    }
    if (i < faqs.length) {
      sh.getRange(r + i - 1, 8).setValue(faqs[i][0]);
      sh.getRange(r + i - 1, 9, 1, 5).merge().setValue(faqs[i][1]);
    }
    sh.setRowHeight(r + i - 1, 36);
  }
  const blockH = Math.max(timeFormat.length, faqs.length);
  sh.getRange(r - 1, 1, blockH, 6).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);
  sh.getRange(r - 1, 8, blockH, 6).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);

  // 全体のフォント設定
  sh.getRange(1, 1, sh.getLastRow(), 13).setFontFamily("Noto Sans JP").setFontSize(10).setVerticalAlignment("middle").setWrap(true);
  // 再適用が必要なヘッダー行
  sh.getRange(1, 1, 1, 13).setFontSize(20).setFontWeight("bold");
  sh.setTabColor("#233447");
  return "マニュアル v3 構築完了";
}

// v5.7+: マニュアル v2 (新人向け詳細版)
function buildManualUnifiedV2() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  ["マニュアル_LG向け", "マニュアル_CA向け", "マニュアル"].forEach(n => {
    const sh = ss.getSheetByName(n);
    if (sh) ss.deleteSheet(sh);
  });
  const sh = ss.insertSheet("マニュアル");

  const NAVY = "#233447";
  const MUTED = "#64748B";
  const BORDER = "#E3E7EF";
  const BG_SOFT = "#F2F4F7";
  const BG_BOX = "#F8FAFC";
  const ACCENT_BG = "#FEF3E7";   // 注意点用
  const ACCENT_FG = "#D97706";

  sh.setHiddenGridlines(true);

  // 列幅 (A-M 13列)
  // A: 番号/ラベル
  // B-D: 主コンテンツ(3列分のメイン)
  // E: 仕切り
  // F-H: 補助コンテンツ
  // I: 仕切り
  // J-L: 追加(注意点・例など)
  // M: 余白
  const widths = [70, 200, 230, 230, 30, 130, 230, 230, 30, 130, 230, 230, 60];
  widths.forEach((w, i) => sh.setColumnWidth(i + 1, w));

  // タイトル
  sh.getRange(1, 1).setValue("マニュアル — 面談連携システム");
  sh.getRange(2, 1).setValue("v5.7 / 新メンバー向けガイド / 初回はSTEP2(CAカレンダー共有)から");
  sh.getRange(1, 1, 1, 13).merge().setBackground(NAVY).setFontColor("#FFFFFF").setFontWeight("bold").setFontSize(20)
    .setFontFamily("Noto Sans JP").setHorizontalAlignment("left").setVerticalAlignment("middle");
  sh.setRowHeight(1, 60);
  sh.getRange(2, 1, 1, 13).merge().setBackground(BG_SOFT).setFontColor(MUTED).setFontSize(10)
    .setFontFamily("Noto Sans JP").setHorizontalAlignment("left").setVerticalAlignment("middle");
  sh.setRowHeight(2, 28);
  sh.getRange(2, 1, 1, 13).setBorder(null, null, true, null, null, null, NAVY, SpreadsheetApp.BorderStyle.SOLID_THICK);

  // helper
  const section = (row, num, title, span) => {
    span = span || 13;
    sh.getRange(row, 1, 1, span).merge().setValue(`STEP ${num}.   ${title}`)
      .setFontColor(NAVY).setFontWeight("bold").setFontSize(15)
      .setFontFamily("Noto Sans JP").setHorizontalAlignment("left").setVerticalAlignment("middle");
    sh.setRowHeight(row, 44);
    sh.getRange(row, 1, 1, span).setBorder(null, null, true, null, null, null, NAVY, SpreadsheetApp.BorderStyle.SOLID);
  };

  const subSection = (row, title, startCol, span) => {
    sh.getRange(row, startCol, 1, span).merge().setValue(title)
      .setBackground(NAVY).setFontColor("#FFFFFF").setFontWeight("bold").setFontSize(11)
      .setFontFamily("Noto Sans JP").setHorizontalAlignment("center").setVerticalAlignment("middle");
    sh.setRowHeight(row, 32);
  };

  let r = 4;

  // ==================== STEP 1 ====================
  section(r, "1", "システム全体像 — 何が起きるか");
  r++;
  const overviewText = "LG (Lead Generator) が学生から日程を受け取り → Slackから「面談登録」モーダル送信 → システムが自動で CA (Career Adviser) のカレンダーを照合してマッチング → Meet URL自動発行 → スレッドで通知。\n\nLGは学生対応、CAは面談実施に集中できる仕組みです。1件あたり旧フローの30-40分 → 2-3分に短縮。";
  sh.getRange(r, 1, 1, 13).merge().setValue(overviewText)
    .setBackground(BG_BOX).setFontColor(NAVY).setFontSize(11).setFontFamily("Noto Sans JP")
    .setHorizontalAlignment("left").setVerticalAlignment("middle").setWrap(true);
  sh.setRowHeight(r, 70);
  sh.getRange(r, 1, 1, 13).setBorder(true, true, true, true, null, null, BORDER, SpreadsheetApp.BorderStyle.SOLID);
  r++;
  r++;  // 空行
  r++;

  // ==================== STEP 2 CA向け カレンダー共有 ====================
  section(r, "2", "【CA必須】 カレンダー共有設定 — 入社時に1回だけ");
  r++;
  // 説明
  sh.getRange(r, 1, 1, 13).merge().setValue("⚠️ CAの方は、まずGoogleカレンダーを record@tokumori.co.jp に共有してください。共有しないと自動マッチング対象に入りません。")
    .setBackground(ACCENT_BG).setFontColor(ACCENT_FG).setFontSize(11).setFontWeight("bold")
    .setFontFamily("Noto Sans JP").setHorizontalAlignment("left").setVerticalAlignment("middle")
    .setBorder(true, true, true, true, null, null, ACCENT_FG, SpreadsheetApp.BorderStyle.SOLID);
  sh.setRowHeight(r, 50);
  r += 2;

  // 手順テーブル (左) + 注意点 (右)
  subSection(r, "操作手順 (1回だけ)", 1, 8);
  subSection(r, "よくある失敗と対処", 10, 3);
  r++;
  const calSteps = [
    ["1", "Google カレンダーを開く", "calendar.google.com にアクセス"],
    ["2", "左サイドの「マイカレンダー」", "自分の名前のカレンダーを探す"],
    ["3", "カレンダー名にホバー → ︙(3点メニュー)", "「設定と共有」をクリック"],
    ["4", "ページ下部にスクロール", "「特定のユーザーや...」セクションへ"],
    ["5", "「+ユーザーや...を追加」をクリック", "ダイアログが開く"],
    ["6", "メールアドレス欄に入力", "record@tokumori.co.jp"],
    ["7", "権限プルダウンを変更", "「予定の変更」を選択"],
    ["8", "「送信」をクリック", "完了"],
    ["✓", "確認: 数分待つ", "システムから依頼が来始める"],
  ];
  sh.getRange(r, 1, calSteps.length, 3).setValues(calSteps);
  // 3-8 列がマージ範囲なので、3列のテーブルを A-C にしてその後D列も含める
  sh.getRange(r, 4, calSteps.length, 5).merge();
  // Wait actually I want col A=#, B=操作, C-H=説明
  // Let me restructure: A=#, B=操作タイトル, C-H=詳細 (merge 6 cells per row)
  // Need to re-do

  // mistakes col (J-L)
  const mistakes = [
    ["権限「閲覧」のまま", "→ 書き込めず予約失敗。「予定の変更」に修正"],
    ["違うアカウントで共有", "→ 個人ではなく業務カレンダーで共有"],
    ["共有後に依頼が来ない", "→ record@ に送信できたか再確認"],
    ["土日に依頼が来ない (tokumori)", "→ 仕様 (tokumori土日NG)"],
  ];
  sh.getRange(r, 10, mistakes.length, 2).setValues(mistakes);

  // 罫線
  sh.getRange(r, 1, calSteps.length, 3).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);
  sh.getRange(r, 10, mistakes.length, 2).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);

  // セル中央寄せ
  sh.getRange(r, 1, calSteps.length, 1).setHorizontalAlignment("center").setFontWeight("bold").setBackground(BG_SOFT);
  for (let rr = r; rr < r + calSteps.length; rr++) sh.setRowHeight(rr, 36);
  // フォント設定
  sh.getRange(r, 1, calSteps.length, 13).setFontFamily("Noto Sans JP").setFontSize(10).setVerticalAlignment("middle").setWrap(false);
  r += calSteps.length;
  r += 2;

  // ==================== STEP 3 共通基礎 ====================
  section(r, "3", "共通基礎 — 用語・ビジネスアワー・SNS別URL");
  r++;
  subSection(r, "用語集", 1, 4);
  subSection(r, "ビジネスアワー", 6, 3);
  subSection(r, "SNS別 LINE追加URL", 10, 3);
  r++;
  const terms2 = [
    ["LG", "Lead Generator", "学生獲得・面談調整担当"],
    ["CA", "Career Adviser", "面談実施担当"],
    ["スレッド", "Slackメッセージの返信ツリー", "登録ごとに1つ立つ"],
    ["モーダル", "Slackポップアップ入力", "ショートカット/ボタンから開く"],
    ["連携番号", "システム通し番号", "#0001 4桁ゼロ埋め"],
    ["フェーズ", "面談の状態", "下記の7状態のいずれか"],
    ["実施予定", "CA確定済", "面談実施待ち"],
    ["日程調整中", "CA未確定", "リマインド対象"],
    ["飛び", "学生当日不参加", "🚫飛び報告ボタンで遷移"],
  ];
  sh.getRange(r, 1, terms2.length, 4).setValues(terms2.map(t => [t[0], t[1], t[2], ""]));
  // 4列目は空欄 → 3列目を広げて使うため、後でマージしてもよい
  sh.getRange(r, 1, terms2.length, 4).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);

  const bh2 = [
    ["@tokumori.co.jp", "平日 9-20時", "土日NG"],
    ["その他 (個人Gmail)", "毎日 8-23時", "土日OK"],
    ["", "", ""],
    ["完全空きのみ予約可", "1分でも予定が入っていたら回避", ""],
    ["「ブロック」予定も尊重", "全タイトル一律", ""],
    ["", "", ""],
    ["休憩したい時間は", "予定を入れる(自衛)", ""],
    ["", "", ""],
    ["", "", ""],
  ];
  sh.getRange(r, 6, bh2.length, 3).setValues(bh2);
  sh.getRange(r, 6, bh2.length, 3).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);

  const sns2 = [
    ["Instagram", "lp=F3Ejz7", "自動"],
    ["X", "lp=Ohe7j3", "自動"],
    ["TikTok", "lp=JuUtkO", "自動"],
    ["YouTube", "lp=OL8WLc", "自動"],
    ["Threads", "lp=1QvvPc", "自動"],
    ["リファラル", "lp=ehWACq", "自動"],
    ["その他", "lp=SME5lJ", "自動"],
    ["", "", ""],
    ["", "", ""],
  ];
  sh.getRange(r, 10, sns2.length, 3).setValues(sns2);
  sh.getRange(r, 10, sns2.length, 3).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);

  // 行高
  for (let rr = r; rr < r + 9; rr++) sh.setRowHeight(rr, 32);
  sh.getRange(r, 1, 9, 13).setFontFamily("Noto Sans JP").setFontSize(10).setVerticalAlignment("middle").setWrap(false);
  // 列ヘッダー風
  sh.getRange(r, 1, 1, 1).setBackground(BG_SOFT).setFontWeight("bold");
  r += 9;
  r += 2;

  // ==================== STEP 4 LG向け 詳細手順 ====================
  section(r, "4", "【LG必須】 面談登録から確定まで");
  r++;
  // テキスト概要
  sh.getRange(r, 1, 1, 13).merge().setValue("学生から候補日程をもらったら、ここを見ながら登録すれば誰でも完結できます。所要時間 1-2分。")
    .setBackground(BG_BOX).setFontColor(MUTED).setFontSize(10).setFontFamily("Noto Sans JP")
    .setHorizontalAlignment("left").setVerticalAlignment("middle")
    .setBorder(true, true, true, true, null, null, BORDER, SpreadsheetApp.BorderStyle.SOLID);
  sh.setRowHeight(r, 40);
  r += 2;

  subSection(r, "STEP 4-1   モーダル起動", 1, 13);
  r++;
  const lgStep1 = [
    ["1", "Slack入力欄左下の ⚡ アイコンをクリック", "本番チャンネル外でも使用可能"],
    ["2", "検索欄に「面談」入力 → 「面談登録」をクリック", "2-3秒待つとモーダル表示"],
  ];
  sh.getRange(r, 1, lgStep1.length, 3).setValues(lgStep1);
  sh.getRange(r, 4, lgStep1.length, 10).merge();
  // No actually merging row by row
  // Let me just do simple 3-col layout for now
  for (let rr = r; rr < r + lgStep1.length; rr++) sh.setRowHeight(rr, 32);
  sh.getRange(r, 1, lgStep1.length, 1).setBackground(BG_SOFT).setFontWeight("bold").setHorizontalAlignment("center");
  sh.getRange(r, 1, lgStep1.length, 13).setFontFamily("Noto Sans JP").setFontSize(10).setVerticalAlignment("middle");
  sh.getRange(r, 1, lgStep1.length, 13).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);
  r += lgStep1.length;
  r += 1;

  subSection(r, "STEP 4-2   モーダル各フィールドの入力", 1, 13);
  r++;
  const lgFields = [
    ["フィールド", "入力内容", "例", "備考"],
    ["予約モード", "通常 or 自分のカレンダー(兼任)", "通常", "兼任はLG=CA本人時のみ"],
    ["LGメンバー", "デフォルトは自分", "(自動)", "代理時のみ変更"],
    ["学生アカウント名", "@は不要", "tanaka_taro", "重複チェックの基準"],
    ["卒年", "プルダウン", "27卒", "シート振り分け"],
    ["SNS種別", "プルダウン", "Instagram", "LINE追加URL自動セット"],
    ["└ その他選択時の記述", "「その他」選んだ時のみ", "Threads派生", "任意"],
    ["つなぎ方", "プルダウン", "友達繋ぎ", "「その他」可"],
    ["志望業界", "プルダウン", "IT・通信", "「その他」可"],
    ["相談内容", "プルダウン", "自己分析", "「その他」可"],
    ["候補日① + 時間①", "必須", "2026-06-10, 10-15", "自由フォーマット可"],
    ["候補日② + 時間②", "任意", "(空欄OK)", "代替案"],
    ["候補日③ + 時間③", "任意", "(空欄OK)", "代替案"],
  ];
  const headerRow = lgFields[0];
  sh.getRange(r, 1, 1, 4).setValues([headerRow])
    .setBackground(BG_SOFT).setFontWeight("bold").setFontSize(10).setFontFamily("Noto Sans JP")
    .setHorizontalAlignment("center");
  sh.setRowHeight(r, 32);
  r++;
  sh.getRange(r, 1, lgFields.length - 1, 4).setValues(lgFields.slice(1));
  for (let rr = r; rr < r + lgFields.length - 1; rr++) sh.setRowHeight(rr, 32);
  sh.getRange(r - 1, 1, lgFields.length, 4).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);
  sh.getRange(r, 1, lgFields.length - 1, 4).setFontFamily("Noto Sans JP").setFontSize(10).setVerticalAlignment("middle").setWrap(false);

  // 候補時間早見表 (右側 F-L)
  sh.getRange(r - 1, 6, 1, 7).merge().setValue("候補時間 自由フォーマット早見表")
    .setBackground(NAVY).setFontColor("#FFFFFF").setFontWeight("bold").setFontSize(11)
    .setFontFamily("Noto Sans JP").setHorizontalAlignment("center").setVerticalAlignment("middle");
  sh.setRowHeight(r - 1, 32);
  const timeTable = [
    ["入力", "解釈", "用途"],
    ["10:00~12:00", "10:00〜12:00", "標準"],
    ["10-15", "10:00〜15:00", "簡易レンジ"],
    ["10時以降", "10:00〜23:00", "終端不明"],
    ["午前中 / 午前", "9:00〜12:00", "tokumori 9時以降"],
    ["午後", "13:00〜23:00", "幅広く拾える"],
    ["夕方", "17:00〜23:00", "夜寄り"],
    ["夜", "19:00〜23:00", "gmail CAのみ"],
    ["終日/いつでも", "8:00〜23:00", "最大"],
    ["10 / 10時", "10:00 単点", "45分枠確保"],
    ["", "", ""],
    ["", "", ""],
  ];
  sh.getRange(r, 6, 1, 3).setValues([timeTable[0]])
    .setBackground(BG_SOFT).setFontWeight("bold").setFontSize(10).setFontFamily("Noto Sans JP")
    .setHorizontalAlignment("center");
  sh.getRange(r + 1, 6, timeTable.length - 1, 3).setValues(timeTable.slice(1))
    .setFontFamily("Noto Sans JP").setFontSize(10).setVerticalAlignment("middle");
  sh.getRange(r, 6, timeTable.length, 3).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);

  r += lgFields.length - 1;
  r += 1;

  // STEP 4-3 結果スレッドの読み方
  subSection(r, "STEP 4-3   結果スレッドの読み方 / 次のアクション", 1, 13);
  r++;
  const resultTable = [
    ["状況", "スレッドの見え方", "あなたの次のアクション"],
    ["✅ CA確定", "🗓 面談確定 #0042  ・担当LG/担当CA/日程/Meet URL", "学生にLINEで日時+Meet URLを送付"],
    ["⏳ CA未確定", "📋 面談登録 #0042（CA未確定） + @CAメンション", "そのまま待機 → 12hで自動リマインド"],
    ["⚠️ 重複検知", "登録不成立メッセージ (あなただけに表示)", "学生情報を見直す or 既存スレで継続"],
  ];
  sh.getRange(r, 1, 1, 3).setValues([resultTable[0]])
    .setBackground(BG_SOFT).setFontWeight("bold").setFontSize(10).setFontFamily("Noto Sans JP")
    .setHorizontalAlignment("center");
  sh.setRowHeight(r, 32);
  r++;
  sh.getRange(r, 1, resultTable.length - 1, 3).setValues(resultTable.slice(1));
  for (let rr = r; rr < r + resultTable.length - 1; rr++) sh.setRowHeight(rr, 36);
  sh.getRange(r - 1, 1, resultTable.length, 3).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);
  sh.getRange(r, 1, resultTable.length - 1, 3).setFontFamily("Noto Sans JP").setFontSize(10).setVerticalAlignment("middle").setWrap(false);
  r += resultTable.length - 1;
  r += 1;

  // STEP 4-4 ボタン操作 (LG)
  subSection(r, "STEP 4-4   スレッド内ボタン操作 (LG用)", 1, 13);
  r++;
  const lgBtns = [
    ["ボタン", "アイコン", "押すタイミング", "システムが何をするか"],
    ["リスケ依頼", "🔁", "学生から日程変更要望が来た時", "モーダル → 新候補入力 → 旧予定削除 + CA再マッチング"],
    ["日程再回収", "🔁", "CA未確定が長引き別候補を回収する時", "モーダル → 新候補で再マッチング (旧予定なし)"],
    ["キャンセル", "❌", "学生から事前キャンセル連絡時", "フェーズ「キャンセル」化 + CAカレンダー予定削除 + スレッド通知"],
    ["飛び報告", "🚫", "学生が当日不参加/連絡なし", "フェーズ「飛び」化 + 飛びチャンネル通知 + カレンダー注記"],
    ["重複報告", "⚠️", "事後で重複に気付いた時", "モーダル → 詳細入力 → 「重複（要整理）」化"],
  ];
  sh.getRange(r, 1, 1, 4).setValues([lgBtns[0]])
    .setBackground(BG_SOFT).setFontWeight("bold").setFontSize(10).setFontFamily("Noto Sans JP")
    .setHorizontalAlignment("center");
  sh.setRowHeight(r, 32);
  r++;
  sh.getRange(r, 1, lgBtns.length - 1, 4).setValues(lgBtns.slice(1));
  for (let rr = r; rr < r + lgBtns.length - 1; rr++) sh.setRowHeight(rr, 36);
  sh.getRange(r - 1, 1, lgBtns.length, 4).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);
  sh.getRange(r, 1, lgBtns.length - 1, 4).setFontFamily("Noto Sans JP").setFontSize(10).setVerticalAlignment("middle").setWrap(false);
  r += lgBtns.length - 1;
  r += 2;

  // ==================== STEP 5 CA向け 通知受信時 ====================
  section(r, "5", "【CA必須】 通知受信時の対応");
  r++;
  sh.getRange(r, 1, 1, 13).merge().setValue("通知が来たら、スレッドの先頭を見て確定か未確定かを判別 → 次のアクションを取ります。")
    .setBackground(BG_BOX).setFontColor(MUTED).setFontSize(10).setFontFamily("Noto Sans JP")
    .setHorizontalAlignment("left").setVerticalAlignment("middle")
    .setBorder(true, true, true, true, null, null, BORDER, SpreadsheetApp.BorderStyle.SOLID);
  sh.setRowHeight(r, 36);
  r += 2;

  subSection(r, "STEP 5-1   通知パターン別の対応", 1, 13);
  r++;
  const caTable = [
    ["状況", "スレッドの見え方", "あなたの行動"],
    ["✅ CA確定 (自分が担当)", "🗓 面談確定 #0042 / 担当CA: 自分", "Meet URLをメモ / 面談前に「✅ CA確認」ボタン押下 / 当日Meetに参加"],
    ["⏳ CA未確定 (@CAグループメンション)", "📋 面談登録 #0042 + 希望日程", "自分のカレンダーで希望日程内の空き確認 → 取れるなら「📅 日程入力」"],
    ["📅 日程入力 が他CAにより完了", "他CAが取った通知", "対応不要"],
    ["❌ キャンセル / 🔁 リスケ通知", "LGがボタン押下", "カレンダー予定が自動削除される。何もしなくてOK"],
    ["🚫 飛び報告", "LGが飛び報告押下", "対応不要。カレンダーに自動注記"],
  ];
  sh.getRange(r, 1, 1, 3).setValues([caTable[0]])
    .setBackground(BG_SOFT).setFontWeight("bold").setFontSize(10).setFontFamily("Noto Sans JP")
    .setHorizontalAlignment("center");
  sh.setRowHeight(r, 32);
  r++;
  sh.getRange(r, 1, caTable.length - 1, 3).setValues(caTable.slice(1));
  for (let rr = r; rr < r + caTable.length - 1; rr++) sh.setRowHeight(rr, 40);
  sh.getRange(r - 1, 1, caTable.length, 3).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);
  sh.getRange(r, 1, caTable.length - 1, 3).setFontFamily("Noto Sans JP").setFontSize(10).setVerticalAlignment("middle").setWrap(true);
  r += caTable.length - 1;
  r += 1;

  subSection(r, "STEP 5-2   ボタン操作 (CA用)", 1, 13);
  r++;
  const caBtns = [
    ["ボタン", "アイコン", "押すタイミング", "システムが何をするか"],
    ["CA確認", "✅", "面談前 (自分が当日来られると確定)", "シートY列「✅確認済」+ LGに準備完了通知"],
    ["日程入力", "📅", "希望日程内で自分が対応する場合", "モーダル → 確定日時入力 → カレンダー登録 + Meet生成"],
    ["重複報告", "⚠️", "他CAでも既に対応中だった場合", "モーダル → 詳細入力 → 「重複（要整理）」化"],
  ];
  sh.getRange(r, 1, 1, 4).setValues([caBtns[0]])
    .setBackground(BG_SOFT).setFontWeight("bold").setFontSize(10).setFontFamily("Noto Sans JP")
    .setHorizontalAlignment("center");
  sh.setRowHeight(r, 32);
  r++;
  sh.getRange(r, 1, caBtns.length - 1, 4).setValues(caBtns.slice(1));
  for (let rr = r; rr < r + caBtns.length - 1; rr++) sh.setRowHeight(rr, 36);
  sh.getRange(r - 1, 1, caBtns.length, 4).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);
  sh.getRange(r, 1, caBtns.length - 1, 4).setFontFamily("Noto Sans JP").setFontSize(10).setVerticalAlignment("middle").setWrap(false);
  r += caBtns.length - 1;
  r += 2;

  // ==================== STEP 6 FAQ ====================
  section(r, "6", "FAQ / トラブルシュート");
  r++;
  // 左半 (LG): col 1-6 / 右半 (CA): col 8-13
  subSection(r, "LG向け FAQ", 1, 6);
  subSection(r, "CA向け FAQ", 8, 6);
  r++;
  // 各FAQヘッダー: Q (col 1, 70px) | A (col 2-6 merge, 200+230+230+30+130=820px)
  // 同様にCA側 Q (col 8, 230px) | A (col 9-13 merge)
  const lgFaqs = [
    ["ショートカットが見当たらない", "Slack ⚡から「面談」検索 / 本番Ch外でも使用可"],
    ["送信したのに無反応", "3秒以内に応答できなかった可能性。再操作"],
    ["Meet URLどこ", "確定スレッド内「・Meet: ...」"],
    ["LINE追加URLは自動?", "はい。SNS種別を選ぶと対応URLが自動セット"],
    ["未確定が長引いて寝てしまった", "翌朝12h/24hリマインドで自動再促し"],
    ["土曜の依頼ができない", "tokumori CAは土日NG。gmail CAはOK"],
    ["重複登録を間違ってしてしまった", "⚠️ 重複報告ボタンで処理"],
  ];
  // ヘッダー Q | A
  sh.getRange(r, 1, 1, 1).setValue("Q").setBackground(BG_SOFT).setFontWeight("bold").setFontSize(10)
    .setFontFamily("Noto Sans JP").setHorizontalAlignment("center");
  sh.getRange(r, 2, 1, 5).merge().setValue("A").setBackground(BG_SOFT).setFontWeight("bold").setFontSize(10)
    .setFontFamily("Noto Sans JP").setHorizontalAlignment("center");
  sh.setRowHeight(r, 32);
  const lgFaqHeaderRow = r;
  r++;
  // 各行: Q col 1, A col 2-6 merge
  lgFaqs.forEach((row, i) => {
    sh.getRange(r + i, 1).setValue(row[0]);
    sh.getRange(r + i, 2, 1, 5).merge().setValue(row[1]);
    sh.setRowHeight(r + i, 36);
  });
  // 罫線+wrap
  sh.getRange(lgFaqHeaderRow, 1, lgFaqs.length + 1, 6).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);
  sh.getRange(r, 1, lgFaqs.length, 6).setFontFamily("Noto Sans JP").setFontSize(10).setVerticalAlignment("middle").setWrap(true);

  // CA FAQ (col 8-13)
  const caFaqs = [
    ["自分に依頼が来ない", "カレンダー権限「予定の変更」を record@tokumori.co.jp に共有しているか再確認"],
    ["「📅 日程入力」モーダルが開かない", "ボタン再押下 / Slack App再起動 / GAS応答待ち3秒越えの可能性"],
    ["土曜に依頼が来た (tokumori所属)", "システムバグの可能性。報告お願いします"],
    ["登録された予定を削除したい", "LGに連絡 → キャンセル/リスケボタンで処理"],
    ["@CA メンションがうるさい", "通知設定で「メンションのみ」に / 対応するCAだけ反応すればOK"],
    ["カレンダーに「飛び」注記された", "学生が当日不参加だった印。対応不要"],
    ["共有したのに反映されない", "数分待つ / record@ への共有か再確認"],
  ];
  sh.getRange(lgFaqHeaderRow, 8, 1, 1).setValue("Q").setBackground(BG_SOFT).setFontWeight("bold").setFontSize(10)
    .setFontFamily("Noto Sans JP").setHorizontalAlignment("center");
  sh.getRange(lgFaqHeaderRow, 9, 1, 5).merge().setValue("A").setBackground(BG_SOFT).setFontWeight("bold").setFontSize(10)
    .setFontFamily("Noto Sans JP").setHorizontalAlignment("center");
  caFaqs.forEach((row, i) => {
    sh.getRange(r + i, 8).setValue(row[0]);
    sh.getRange(r + i, 9, 1, 5).merge().setValue(row[1]);
  });
  sh.getRange(lgFaqHeaderRow, 8, caFaqs.length + 1, 6).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);
  sh.getRange(r, 8, caFaqs.length, 6).setFontFamily("Noto Sans JP").setFontSize(10).setVerticalAlignment("middle").setWrap(true);

  sh.setTabColor("#233447");
  return "マニュアル v2 構築完了";
}

// v5.7+: マニュアル (LG+CA統合) を完全構築
function buildManualUnified() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  // 旧タブ削除
  ["マニュアル_LG向け", "マニュアル_CA向け"].forEach(n => {
    const sh = ss.getSheetByName(n);
    if (sh) ss.deleteSheet(sh);
  });
  // 新タブ作成 (存在なら削除して再作成)
  const existing = ss.getSheetByName("マニュアル");
  if (existing) ss.deleteSheet(existing);
  const sheet = ss.insertSheet("マニュアル");

  const NAVY = "#233447";
  const MUTED = "#64748B";
  const BORDER = "#E3E7EF";
  const BG_SOFT = "#F2F4F7";
  const BG_BOX = "#F8FAFC";

  sheet.setHiddenGridlines(true);

  // 列幅 (A-M, 13列)
  const widths = [120, 280, 280, 40, 120, 280, 280, 40, 120, 280, 280, 40, 80];
  widths.forEach((w, i) => sheet.setColumnWidth(i + 1, w));

  // タイトル/サブタイトル
  sheet.getRange(1, 1).setValue("マニュアル");
  sheet.getRange(2, 1).setValue("LG/CA面談連携システム v5.7 / 新メンバーでもこの1ページで業務完結");
  sheet.getRange(1, 1, 1, 13).merge().setBackground(NAVY).setFontColor("#FFFFFF").setFontWeight("bold").setFontSize(20)
    .setFontFamily("Noto Sans JP").setHorizontalAlignment("left").setVerticalAlignment("middle");
  sheet.setRowHeight(1, 60);
  sheet.getRange(2, 1, 1, 13).merge().setBackground(BG_SOFT).setFontColor(MUTED).setFontSize(10)
    .setFontFamily("Noto Sans JP").setHorizontalAlignment("left").setVerticalAlignment("middle");
  sheet.setRowHeight(2, 28);
  sheet.getRange(2, 1, 1, 13).setBorder(null, null, true, null, null, null, NAVY, SpreadsheetApp.BorderStyle.SOLID_THICK);

  // セクション見出しヘルパー
  const section = (row, title, cols) => {
    cols = cols || 13;
    sheet.getRange(row, 1, 1, cols).merge().setValue(title)
      .setFontColor(NAVY).setFontWeight("bold").setFontSize(14)
      .setFontFamily("Noto Sans JP").setHorizontalAlignment("left").setVerticalAlignment("middle");
    sheet.setRowHeight(row, 40);
    sheet.getRange(row, 1, 1, cols).setBorder(null, null, true, null, null, null, NAVY, SpreadsheetApp.BorderStyle.SOLID);
  };

  // 用語集 (A-C) | 1日の流れ (E-G) | ビジネスアワー & SNS別URL (I-K)
  section(4, "共通基礎 — 用語集 / 1日の流れ / ビジネスアワー / SNS別URL");

  const termHeader = ["用語", "意味", "備考"];
  const terms = [
    ["LG", "Lead Generator", "学生獲得・面談調整担当"],
    ["CA", "Career Adviser", "面談実施担当"],
    ["スレッド", "Slackメッセージの返信ツリー", "登録ごとに1つ立つ"],
    ["モーダル", "Slackポップアップ入力", "ショートカット/ボタンから開く"],
    ["連携番号", "システム通し番号", "#0001 4桁ゼロ埋め"],
    ["フェーズ", "面談の状態", "日程調整中/実施予定/実施済/飛び/キャンセル/調整不可/重複"],
    ["リスケ", "日程変更要望", "学生から「別の日に」と来た時"],
    ["飛び", "無断欠席", "学生が予約時刻に来ない"],
  ];
  sheet.getRange(5, 1, 1, 3).setValues([termHeader]);
  sheet.getRange(6, 1, terms.length, 3).setValues(terms);

  const flowHeader = ["時点", "アクション", "担当"];
  const flows = [
    ["学生連絡時", "候補日程を受け取る", "LG"],
    ["登録時", "Slack⚡から「面談登録」", "LG"],
    ["即時", "結果スレッド確認 (確定 or 未確定)", "LG"],
    ["12h/24h", "未確定リマインド対応", "CA"],
    ["前日〜当日", "確定面談のMeet URLで参加", "CA"],
    ["面談前", "✅ CA確認 ボタン押下", "CA"],
    ["例外", "リスケ/キャンセル/飛び/重複報告", "LG/CA"],
  ];
  sheet.getRange(5, 5, 1, 3).setValues([flowHeader]);
  sheet.getRange(6, 5, flows.length, 3).setValues(flows);

  const bhHeader = ["項目", "値", "備考"];
  const bh = [
    ["@tokumori.co.jp ドメイン", "平日 9:00-20:00", "土日NG"],
    ["その他 (個人Gmail)", "毎日 8:00-23:00", "土日OK"],
    ["", "", ""],
    ["Instagram", "lp=F3Ejz7", "自動セット"],
    ["X", "lp=Ohe7j3", "自動セット"],
    ["TikTok", "lp=JuUtkO", "自動セット"],
    ["Threads", "lp=1QvvPc", "自動セット"],
    ["YouTube/リファラル/その他", "OL8WLc/ehWACq/SME5lJ", "自動セット"],
  ];
  sheet.getRange(5, 9, 1, 3).setValues([bhHeader]);
  sheet.getRange(6, 9, bh.length, 3).setValues(bh);

  // テーブルヘッダー強調 (5行目)
  [1, 5, 9].forEach(c => {
    sheet.getRange(5, c, 1, 3).setBackground(BG_SOFT).setFontWeight("bold")
      .setFontSize(10).setFontFamily("Noto Sans JP").setHorizontalAlignment("center");
  });
  // 各テーブルに罫線 (rows 5-13, cols [1-3, 5-7, 9-11])
  [1, 5, 9].forEach(c => {
    sheet.getRange(5, c, 9, 3).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);
  });
  // 行高
  for (let r = 5; r <= 13; r++) sheet.setRowHeight(r, 32);

  // ── LG向け vs CA向け 操作手順 (2カラム) ──
  section(16, "操作手順 — LG向け (左) / CA向け (右)");

  // LG列 A-F
  sheet.getRange(17, 1, 1, 6).merge().setValue("LG: 面談登録 〜 各種報告")
    .setBackground(NAVY).setFontColor("#FFFFFF").setFontWeight("bold").setFontSize(12)
    .setFontFamily("Noto Sans JP").setHorizontalAlignment("center").setVerticalAlignment("middle");
  sheet.setRowHeight(17, 34);

  const lgHeader = ["#", "手順", "詳細"];
  const lgRows = [
    ["1", "Slack ⚡ から「面談登録」", "本番チャンネル外でもOK"],
    ["2", "モーダルで予約モード選択", "通常 / 自分のカレンダー (兼任)"],
    ["3", "学生情報入力", "アカウント名/卒年/SNS/業界/相談"],
    ["4", "候補日程入力", "候補① 必須 / ②③ 任意"],
    ["5", "登録ボタン", "重複なら登録不成立メッセージ"],
    ["6", "スレッド結果確認", "確定 (CA決定) or 未確定 (@CA通知)"],
    ["7", "学生にLINE+Meet送付", "確定時のみ"],
    ["8", "🔁 リスケ依頼 ボタン", "学生から日程変更要望"],
    ["9", "❌ キャンセル ボタン", "学生からキャンセル連絡"],
    ["10", "🚫 飛び報告 ボタン", "学生が当日不参加"],
    ["11", "⚠️ 重複報告 ボタン", "重複に気付いた時"],
  ];
  sheet.getRange(18, 1, 1, 3).setValues([lgHeader]);
  sheet.getRange(19, 1, lgRows.length, 3).setValues(lgRows);

  // CA列 H-M (H=8, 9, 10)
  sheet.getRange(17, 9, 1, 5).merge().setValue("CA: スレッド受信 〜 面談実施")
    .setBackground(NAVY).setFontColor("#FFFFFF").setFontWeight("bold").setFontSize(12)
    .setFontFamily("Noto Sans JP").setHorizontalAlignment("center").setVerticalAlignment("middle");

  const caHeader = ["#", "手順", "詳細"];
  const caRows = [
    ["事前", "カレンダー権限共有", "record@tokumori.co.jp に「予定の変更」"],
    ["1", "スレッド通知を確認", "確定通知 or 未確定通知"],
    ["2-A", "確定の場合 → 当日参加", "Meet URLはスレッド内"],
    ["2-B", "未確定の場合 → 📅 日程入力", "希望日程内で空き調整"],
    ["3", "面談前: ✅ CA確認", "LGに準備完了の合図"],
    ["4", "面談実施", "Google Meet"],
    ["5", "重複に気付いたら ⚠️ 重複報告", "別CAが既に対応中だった等"],
    ["—", "キャンセル/リスケ通知が来たら", "対応不要 (カレンダー自動削除)"],
    ["—", "飛び報告が来たら", "対応不要 (注記自動)"],
    ["", "", ""],
    ["", "", ""],
  ];
  sheet.getRange(18, 9, 1, 3).setValues([caHeader]);
  sheet.getRange(19, 9, caRows.length, 3).setValues(caRows);

  // テーブルヘッダー強調
  sheet.getRange(18, 1, 1, 3).setBackground(BG_SOFT).setFontWeight("bold").setFontSize(10)
    .setFontFamily("Noto Sans JP").setHorizontalAlignment("center");
  sheet.getRange(18, 9, 1, 3).setBackground(BG_SOFT).setFontWeight("bold").setFontSize(10)
    .setFontFamily("Noto Sans JP").setHorizontalAlignment("center");

  // 罫線
  sheet.getRange(18, 1, 12, 3).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);
  sheet.getRange(18, 9, 12, 3).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);
  for (let r = 18; r <= 29; r++) sheet.setRowHeight(r, 32);

  // ── 候補時間早見表 (LG向けに重要) + FAQ ──
  section(32, "候補時間フォーマット早見表 / FAQ");

  const timeHeader = ["入力", "解釈", "用途"];
  const timeRows = [
    ["10:00~12:00", "10:00〜12:00", "標準"],
    ["10-15", "10:00〜15:00", "簡易記法"],
    ["10時以降", "10:00〜23:00", "終端不明"],
    ["午前中 / 午前", "9:00〜12:00", "tokumori 9時以降"],
    ["午後", "13:00〜23:00", "幅広く拾える"],
    ["夕方", "17:00〜23:00", "夜寄り"],
    ["終日/いつでも", "8:00〜23:00", "最大幅"],
  ];
  sheet.getRange(33, 1, 1, 3).setValues([timeHeader]);
  sheet.getRange(34, 1, timeRows.length, 3).setValues(timeRows);
  sheet.getRange(33, 1, 1, 3).setBackground(BG_SOFT).setFontWeight("bold").setFontSize(10)
    .setFontFamily("Noto Sans JP").setHorizontalAlignment("center");
  sheet.getRange(33, 1, 8, 3).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);

  const faqHeader = ["Q", "A"];
  const faqs = [
    ["ショートカットが見当たらない", "Slack⚡から「面談」で検索"],
    ["モーダル送信したのに反応なし", "3秒以内に応答できなかった可能性。再操作"],
    ["Meet URLはどこ", "確定スレッド内「・Meet: ...」"],
    ["LINE追加URLは自動?", "はい。SNS種別で自動セット"],
    ["未確定のまま夜寝てしまった", "12h/24h自動リマインドが動く"],
    ["土曜の依頼が来た", "tokumori 土日NG / gmail CAはOK"],
    ["自分に依頼が来ない (CA)", "カレンダー権限を要確認"],
  ];
  sheet.getRange(33, 5, 1, 2).setValues([faqHeader]);
  sheet.getRange(34, 5, faqs.length, 2).setValues(faqs);
  sheet.getRange(33, 5, 1, 2).setBackground(BG_SOFT).setFontWeight("bold").setFontSize(10)
    .setFontFamily("Noto Sans JP").setHorizontalAlignment("center");
  sheet.getRange(33, 5, 8, 2).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);

  // データの基本フォント
  sheet.getRange(5, 1, 40, 13).setFontFamily("Noto Sans JP").setFontSize(10).setVerticalAlignment("middle").setWrap(false);
  for (let r = 32; r <= 41; r++) sheet.setRowHeight(r, 32);

  // タブ色 (ネイビー)
  sheet.setTabColor("#233447");

  return "マニュアル統合完了";
}

// v5.7+: システム仕様書 を3カラムレイアウトで再構築
function buildSystemSpec() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sh = ss.getSheetByName("システム仕様書");
  if (sh) ss.deleteSheet(sh);
  sh = ss.insertSheet("システム仕様書");

  const NAVY = "#233447";
  const MUTED = "#64748B";
  const BORDER = "#E3E7EF";
  const BG_SOFT = "#F2F4F7";
  const BG_BOX = "#F8FAFC";

  sh.setHiddenGridlines(true);
  // 列幅: 13列 = A-M。3カラム×4列 + 仕切り1列
  const widths = [120, 220, 220, 40, 120, 220, 220, 40, 120, 220, 220, 40, 80];
  widths.forEach((w, i) => sh.setColumnWidth(i + 1, w));

  // タイトル/サブ
  sh.getRange(1, 1).setValue("システム仕様書");
  sh.getRange(2, 1).setValue("LG/CA面談連携システム v5.7 / アーキテクチャ・データ構造・API仕様");
  sh.getRange(1, 1, 1, 13).merge().setBackground(NAVY).setFontColor("#FFFFFF").setFontWeight("bold").setFontSize(20)
    .setFontFamily("Noto Sans JP").setHorizontalAlignment("left").setVerticalAlignment("middle");
  sh.setRowHeight(1, 60);
  sh.getRange(2, 1, 1, 13).merge().setBackground(BG_SOFT).setFontColor(MUTED).setFontSize(10)
    .setFontFamily("Noto Sans JP").setHorizontalAlignment("left").setVerticalAlignment("middle");
  sh.setRowHeight(2, 28);
  sh.getRange(2, 1, 1, 13).setBorder(null, null, true, null, null, null, NAVY, SpreadsheetApp.BorderStyle.SOLID_THICK);

  const section = (row, title) => {
    sh.getRange(row, 1, 1, 13).merge().setValue(title)
      .setFontColor(NAVY).setFontWeight("bold").setFontSize(14)
      .setFontFamily("Noto Sans JP").setHorizontalAlignment("left").setVerticalAlignment("middle");
    sh.setRowHeight(row, 40);
    sh.getRange(row, 1, 1, 13).setBorder(null, null, true, null, null, null, NAVY, SpreadsheetApp.BorderStyle.SOLID);
  };

  const writeTable = (startRow, startCol, title, header, data) => {
    // タイトル行 (subsection)
    sh.getRange(startRow, startCol, 1, 3).merge().setValue(title)
      .setBackground(NAVY).setFontColor("#FFFFFF").setFontWeight("bold").setFontSize(11)
      .setFontFamily("Noto Sans JP").setHorizontalAlignment("center").setVerticalAlignment("middle");
    sh.setRowHeight(startRow, 32);
    // ヘッダー行
    sh.getRange(startRow + 1, startCol, 1, header.length).setValues([header])
      .setBackground(BG_SOFT).setFontWeight("bold").setFontSize(10).setFontFamily("Noto Sans JP")
      .setHorizontalAlignment("center");
    sh.setRowHeight(startRow + 1, 30);
    // データ
    if (data.length > 0) {
      sh.getRange(startRow + 2, startCol, data.length, header.length).setValues(data)
        .setFontFamily("Noto Sans JP").setFontSize(10).setVerticalAlignment("middle").setWrap(false);
      for (let r = startRow + 2; r < startRow + 2 + data.length; r++) sh.setRowHeight(r, 30);
    }
    // 罫線
    const totalRows = data.length + 2;
    sh.getRange(startRow, startCol, totalRows, header.length).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);
  };

  // ── アーキテクチャ + 主要関数 + シート構造 (3カラム並列) ──
  section(4, "概要 & 構造");

  writeTable(5, 1, "アーキテクチャ", ["コンポーネント", "技術"], [
    ["Slack App", "Block Kit Modals"],
    ["GAS Web App", "GAS V8 (doPost/doGet)"],
    ["連携シート", "Google Spreadsheet"],
    ["Google Calendar", "Advanced Service v3"],
    ["LockService", "並行制御"],
    ["ScriptProperties", "状態管理"],
  ]);
  writeTable(5, 5, "主要関数", ["関数名", "用途"], [
    ["doPost", "Slack Interactivity 受信"],
    ["doGet", "管理用エンドポイント"],
    ["scheduleMeeting", "面談登録メイン"],
    ["checkCAAvailability", "CA空き枠探索"],
    ["createCalendarEvent", "Cal登録 + Meet発行"],
    ["applyDateInput", "CA日程入力処理"],
    ["applyRecollect", "リスケ/日程再回収"],
    ["handleDuplicateReport", "重複報告処理"],
    ["remindStalledMeetings", "12h/24h/36h リマインド"],
  ]);
  writeTable(5, 9, "ビジネスアワー & 番号体系", ["項目", "値"], [
    ["tokumori 平日", "9:00 - 20:00"],
    ["tokumori 土日", "予約NG"],
    ["gmail 全日", "8:00 - 23:00"],
    ["連携番号", "#0001 4桁ゼロ埋め"],
    ["CA番号", "CA001 3桁"],
    ["LG番号", "LG001 3桁"],
  ]);

  // ── シート連携メイン列定義 (横長表 1テーブル) ──
  section(17, "シート: 連携メイン_NN卒 列定義");
  const colsData = [
    ["A", "No.", "整数(4桁表示)"],
    ["B", "登録日", "yyyy/MM/dd"],
    ["C", "LGメンバー", "LG001-名前"],
    ["D", "LINE追加URL", "SNS別自動セット"],
    ["E", "学生アカウント名", "@は不要"],
    ["F", "卒年", "27卒〜30卒"],
    ["G", "SNS種別", "選択肢"],
    ["H", "志望業界", "選択肢 or 記述"],
    ["I", "相談内容", "選択肢 or 記述"],
    ["J/K", "候補日① / 時間①", "必須"],
    ["L", "つなぎ方", "選択肢 or 記述"],
    ["M/N", "候補日② / 時間②", "任意"],
    ["P/Q", "候補日③ / 時間③", "任意"],
    ["S", "確定日時", ""],
    ["T", "CAメンバー", "CA001-名前"],
    ["U", "Meet URL", "自動発行"],
    ["V", "フェーズ", "後述"],
    ["W", "重複チェック", "boolean"],
    ["X", "メモ", "申し送り/履歴"],
    ["Y", "CA確認", "✅確認済 or 空"],
    ["Z", "Slack ts", "スレッドid"],
    ["AB", "_SF除外フラグ", "重複時 ON"],
    ["AC", "_リマインドフラグ", "12h/24h/36h"],
    ["AD", "_最終リマインド時刻", "datetime"],
  ];
  writeTable(18, 1, "列定義", ["列", "名前", "備考"], colsData);
  // ボタン/モーダル/フェーズ (横並び 3カラム)
  writeTable(18, 5, "モーダル一覧", ["callback_id", "用途"], [
    ["modal_register", "面談登録"],
    ["modal_dateinput", "CA確定日時入力"],
    ["modal_recollect", "リスケ/日程再回収"],
    ["modal_duplicate", "重複報告"],
  ]);
  writeTable(24, 5, "ボタン一覧", ["action_id", "操作者"], [
    ["open_modal_register", "LG"],
    ["confirm_ca", "CA"],
    ["open_modal_recollect", "LG"],
    ["open_modal_dateinput", "CA"],
    ["open_modal_duplicate", "LG/CA"],
    ["cancel_meeting", "LG"],
    ["no_show", "LG"],
  ]);
  writeTable(18, 9, "フェーズ一覧", ["フェーズ", "意味"], [
    ["日程調整中", "CA未確定"],
    ["実施予定", "CA確定済"],
    ["実施済", "面談完了"],
    ["キャンセル", "学生事前キャンセル"],
    ["飛び", "学生当日不参加"],
    ["調整不可", "36h経過"],
    ["重複（要整理）", "重複検知"],
  ]);

  // ── 管理者関数 + トリガー (2カラム) ──
  section(45, "管理 & 運用");
  writeTable(46, 1, "管理者関数 (doGet ?action=)", ["関数名", "用途"], [
    ["fullCleanupAndCheck", "全クリーンアップ+検証"],
    ["cleanupTestData", "テストデータ削除"],
    ["validateProductionReadiness", "本番運用前検証"],
    ["debugCAAccess", "空き枠カウント"],
    ["setAllTriggers", "トリガー再登録"],
    ["buildWorkflowDiagram", "ワークフロー図再構築"],
    ["buildManualUnified", "マニュアル再構築"],
    ["buildLGDashboard", "ダッシュボード再構築"],
    ["buildSystemSpec", "本ページ再構築"],
  ]);
  writeTable(46, 5, "トリガー (時間ベース自動)", ["関数名", "頻度"], [
    ["sendDailyReminders", "毎日9時"],
    ["syncSalesforce", "毎時"],
    ["renderAvailabilityCalendar", "30分毎"],
    ["updateLGDashboard", "5分毎"],
    ["remindStalledMeetings", "毎時"],
    ["createMonthlyDigest", "毎月1日0時"],
    ["onEditInstallable", "シート編集時"],
  ]);

  sh.setTabColor("#233447");
  return "システム仕様書 構築完了";
}

// v5.7+: 業務フロー_新旧比較 を完全リセットして並列レイアウトで再構築
function buildFlowComparison() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sh = ss.getSheetByName("業務フロー_新旧比較");
  if (sh) ss.deleteSheet(sh);
  sh = ss.insertSheet("業務フロー_新旧比較");

  const NAVY = "#233447";
  const MUTED = "#64748B";
  const BORDER = "#E3E7EF";
  const BG_SOFT = "#F2F4F7";
  const BG_BOX = "#F8FAFC";

  sh.setHiddenGridlines(true);

  const widths = [50, 90, 280, 50, 50, 90, 280, 50, 240, 140];
  widths.forEach((w, i) => sh.setColumnWidth(i + 1, w));

  sh.getRange(1, 1).setValue("業務フロー 新旧比較");
  sh.getRange(2, 1).setValue("Spir+3チャンネル時代 → v5.7 自動化 / 1件 30-40分 → 2-3分 (90%削減)");
  sh.getRange(1, 1, 1, 10).merge().setBackground(NAVY).setFontColor("#FFFFFF").setFontWeight("bold").setFontSize(20)
    .setFontFamily("Noto Sans JP").setHorizontalAlignment("left").setVerticalAlignment("middle");
  sh.setRowHeight(1, 60);
  sh.getRange(2, 1, 1, 10).merge().setBackground(BG_SOFT).setFontColor(MUTED).setFontSize(10)
    .setFontFamily("Noto Sans JP").setHorizontalAlignment("left").setVerticalAlignment("middle");
  sh.setRowHeight(2, 28);
  sh.getRange(2, 1, 1, 10).setBorder(null, null, true, null, null, null, NAVY, SpreadsheetApp.BorderStyle.SOLID_THICK);

  const section = (row, title) => {
    sh.getRange(row, 1, 1, 10).merge().setValue(title)
      .setFontColor(NAVY).setFontWeight("bold").setFontSize(14)
      .setFontFamily("Noto Sans JP").setHorizontalAlignment("left").setVerticalAlignment("middle");
    sh.setRowHeight(row, 40);
    sh.getRange(row, 1, 1, 10).setBorder(null, null, true, null, null, null, NAVY, SpreadsheetApp.BorderStyle.SOLID);
  };

  section(4, "ステップ別 並列比較");

  // 列見出し: # | 担当 | 旧 | → | # | 担当 | 新 | 自動化 | 削減
  const headers = [["#", "担当(旧)", "旧フロー", "→", "#", "担当(新)", "新フロー", "自動化詳細", "削減効果"]];
  sh.getRange(5, 1, 1, 9).setValues(headers)
    .setBackground(NAVY).setFontColor("#FFFFFF").setFontWeight("bold").setFontSize(10)
    .setFontFamily("Noto Sans JP").setHorizontalAlignment("center");
  sh.setRowHeight(5, 36);
  // セル分け: 旧側 col 1-3, 矢印 col 4, 新側 col 5-7, 自動化 col 8, 削減 col 9

  // ステップデータ (旧#, 旧担当, 旧アクション, , 新#, 新担当, 新アクション, 自動化, 削減)
  const steps = [
    ["1", "学生", "学生から候補日程+SNSアカウント受領", "→", "1", "学生", "学生から候補日程+SNSアカウント受領", "変更なし", "—"],
    ["2", "LG", "3つのSlackチャンネルへ投稿", "→", "2", "LG", "Slack⚡ショートカット「面談登録」", "1モーダルに集約", "投稿3→0"],
    ["3", "LG", "連携シート Cmd+F 重複検索", "→", "—", "SYS", "登録時に自動マッチ", "checkDuplicate", "手動検索ゼロ"],
    ["4", "LG", "判断: 重複あり?", "→", "—", "SYS", "重複時は登録不成立メッセージ", "完全自動化", "判断作業ゼロ"],
    ["5", "LG", "CA全員のSpirを順に確認", "→", "—", "SYS", "Calendar APIで一斉照合", "checkCAAvailability", "Spir確認ゼロ"],
    ["6", "LG", "判断: 空きCAあり?", "→", "—", "SYS", "ビジネスアワー判定+完全空き判定", "_isCAAvailableInHours", "判断作業ゼロ"],
    ["7", "LG", "Spirで予約確定", "→", "—", "SYS", "Calendar.Events.insert", "GASで自動", "手動操作ゼロ"],
    ["8", "LG", "Spirで Meet URL 発行", "→", "—", "SYS", "conferenceData 自動付与", "Meet自動発行", "発行作業ゼロ"],
    ["9", "LG", "Spirに8項目入力", "→", "3", "LG", "モーダル1画面で全項目", "8→1画面", "入力画面数 8→1"],
    ["10", "LG", "発行URLを学生に手動送付", "→", "4", "LG", "確定スレッドのMeet URL送付", "URLは自動表示", "ほぼ変更なし"],
    ["11", "LG", "pass-ch に @channel 投稿 (拾えない時)", "→", "—", "SYS", "@CAグループ自動スレッド投稿", "投稿不要", "@channel投稿ゼロ"],
    ["12", "LG", "数値管理シート 手動入力", "→", "—", "SYS", "連携メイン_NN卒 自動記録", "全項目自動", "入力作業ゼロ"],
    ["13", "LG", "pass-ch に申し送り投稿(4項目)", "→", "—", "SYS", "スレッド内に全項目自動表示", "投稿不要", "申し送りゼロ"],
    ["14", "LG", "リマインド手動フォロー", "→", "—", "SYS", "12h/24h 自動", "remindStalledMeetings", "新機能"],
    ["15", "—", "(無し) 36h経過は手動", "→", "—", "SYS", "36h経過で自動「調整不可」", "状態管理自動", "新機能"],
    ["16", "LG", "canceled-ch に手動投稿", "→", "5", "LG", "❌キャンセルボタン", "+カレンダー自動削除", "投稿+削除ゼロ"],
    ["17", "LG", "リスケは再度全フロー実行", "→", "5", "LG", "🔁リスケ依頼ボタン", "旧予定削除+再マッチング", "再登録ゼロ"],
    ["18", "CA/LG", "cara-ch 投稿 → 10分待機", "→", "5", "LG", "🚫飛び報告ボタン", "+カレンダー注記", "投稿ゼロ"],
  ];
  sh.getRange(6, 1, steps.length, 9).setValues(steps);
  sh.getRange(6, 1, steps.length, 9).setFontFamily("Noto Sans JP").setFontSize(10)
    .setVerticalAlignment("middle").setWrap(false);
  for (let r = 6; r < 6 + steps.length; r++) sh.setRowHeight(r, 32);

  // 旧側 col 1-3: 薄オレンジ系
  sh.getRange(6, 1, steps.length, 3).setBackground("#FFF8F0");
  // 矢印 col 4: 中央寄せ
  sh.getRange(6, 4, steps.length, 1).setHorizontalAlignment("center").setFontSize(14).setFontColor(MUTED);
  // 新側 col 5-7: 薄グリーン系
  sh.getRange(6, 5, steps.length, 3).setBackground("#F4FBF5");
  // 自動化詳細 col 8: BG_BOX
  sh.getRange(6, 8, steps.length, 1).setBackground(BG_BOX);
  // 削減 col 9: 太字
  sh.getRange(6, 9, steps.length, 1).setBackground(BG_BOX).setFontWeight("bold");
  // 担当列センター
  [2, 6].forEach(c => sh.getRange(6, c, steps.length, 1).setHorizontalAlignment("center"));
  [1, 5].forEach(c => sh.getRange(6, c, steps.length, 1).setHorizontalAlignment("center"));

  // 罫線
  sh.getRange(5, 1, 1 + steps.length, 9).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);

  // ── KPI比較 ──
  const kpiStart = 6 + steps.length + 2;
  section(kpiStart, "KPI比較 (1件あたり)");
  const kpiHeader = [["指標", "旧フロー", "新フロー", "差分"]];
  sh.getRange(kpiStart + 1, 1, 1, 4).setValues(kpiHeader)
    .setBackground(BG_SOFT).setFontWeight("bold").setFontSize(10).setFontFamily("Noto Sans JP").setHorizontalAlignment("center");
  const kpiData = [
    ["1件の作業時間", "30-40分", "2-3分", "約90%削減"],
    ["Slack投稿回数", "3-4回", "0回 (ボタン操作)", "100%削減"],
    ["手動入力項目", "20項目超", "10項目 (1モーダル)", "約50%削減"],
    ["Spir画面遷移", "CA全員分(N画面)", "0", "100%削減"],
    ["重複検知ミスのリスク", "高 (目視)", "低 (自動)", "新機能"],
    ["リマインド漏れリスク", "高", "低 (12h/24h自動)", "新機能"],
  ];
  sh.getRange(kpiStart + 2, 1, kpiData.length, 4).setValues(kpiData)
    .setFontFamily("Noto Sans JP").setFontSize(10).setVerticalAlignment("middle");
  for (let r = kpiStart + 1; r < kpiStart + 2 + kpiData.length; r++) sh.setRowHeight(r, 32);
  sh.getRange(kpiStart + 1, 1, 1 + kpiData.length, 4).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);

  sh.setTabColor("#233447");
  return "業務フロー_新旧比較 構築完了";
}

// v5.7+: LG実績ダッシュボード を KPIカード型に再構築
// v5.7+: 期間別フィルタ
function _periodFilter(period) {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  if (period === "月次") {
    const start = new Date(now.getFullYear(), now.getMonth(), 1);
    const end = new Date(now.getFullYear(), now.getMonth() + 1, 1);
    return { fn: (d) => d instanceof Date && d >= start && d < end, label: `${now.getFullYear()}年${now.getMonth() + 1}月` };
  }
  if (period === "週次") {
    const dow = today.getDay();
    const monday = new Date(today.getTime() - ((dow + 6) % 7) * 86400000);
    const nextMonday = new Date(monday.getTime() + 7 * 86400000);
    return { fn: (d) => d instanceof Date && d >= monday && d < nextMonday, label: `${monday.getMonth() + 1}/${monday.getDate()}〜${new Date(nextMonday.getTime() - 86400000).getMonth() + 1}/${new Date(nextMonday.getTime() - 86400000).getDate()}` };
  }
  if (period === "日次") {
    const tomorrow = new Date(today.getTime() + 86400000);
    return { fn: (d) => d instanceof Date && d >= today && d < tomorrow, label: `${today.getMonth() + 1}/${today.getDate()}` };
  }
  return { fn: () => true, label: "全期間" };
}

// v5.7+: 全期間 + 当月の月次ダッシュボードを一括更新
function buildAllLGDashboards() {
  const _t0 = Date.now();
  const out = [];
  try { const r = buildLGDashboard("全期間"); out.push(`全期間 OK (${Date.now()-_t0}ms)`); } catch(e) { out.push("全期間 ERR " + e); Logger.log(e); }
  const _t1 = Date.now();
  try {
    const now = new Date();
    const ym = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
    buildMonthlyDashboard(ym);
    out.push(`${ym} OK (${Date.now()-_t1}ms)`);
  } catch(e) { out.push("monthly ERR " + e); Logger.log(e); }
  // 古い 月次/週次/日次 タブを掃除（一度だけ実行されればOK / 存在しなければスキップ）
  ["LG実績_月次", "LG実績_週次", "LG実績_日次"].forEach(name => {
    try {
      const sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(name);
      if (sh) SpreadsheetApp.getActiveSpreadsheet().deleteSheet(sh);
    } catch(_) {}
  });
  return out.join(" / ");
}

// v5.7+: 卒年シート読み取り最適化版 — 空シート(最終行1以下)をスキップ
function getActiveGradeSheets() {
  return SpreadsheetApp.getActiveSpreadsheet().getSheets()
    .filter(s => GRADE_SHEET_RE.test(s.getName()))
    .filter(s => s.getLastRow() > 1);
}

// v5.7+: 月次ダッシュボード — 上から: KPI → 目標 → LG×月次 → LG×週次 → LG×日次
function buildMonthlyDashboard(yearMonth) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheetName = `LG実績_${yearMonth}`;

  // v5.7.1: 差分判定 — 直近5分以内・行数変化なしならskip
  const propsKey = `__lgdash_meta_monthly_${yearMonth}`;
  const totalRowsNow = getAllGradeSheets().reduce((acc, gs) => acc + gs.getLastRow(), 0);
  try {
    const metaRaw = PropertiesService.getScriptProperties().getProperty(propsKey);
    if (metaRaw) {
      const meta = JSON.parse(metaRaw);
      const elapsed = Date.now() - (meta.lastBuildTs || 0);
      // v5.7.2: フェーズ変更は行数を変えないため、行数一致での skip は廃止。
      //         連打デバウンス目的で「90秒以内」のみ skip (データ変更は常に反映)
      if (elapsed < 90 * 1000) {
        Logger.log(`[buildMonthlyDashboard] skip (last ${elapsed}ms / rows unchanged=${totalRowsNow})`);
        return `skipped (recently built ${elapsed}ms ago)`;
      }
    }
  } catch(_) {}

  // v5.7.1: deleteSheet+insertSheet (重い) ではなく clear() で内容のみ削除
  let sh = ss.getSheetByName(sheetName);
  const isFirstBuild = !sh;
  if (sh) {
    sh.clear({ contentsOnly: false, formatOnly: false, validationsOnly: false });
    sh.getCharts().forEach(c => sh.removeChart(c));
    // v5.7.1: マージ済みレンジを個別にbreakApart (全範囲指定だと結合範囲外を含むと失敗)
    try { sh.getDataRange().getMergedRanges().forEach(r => { try { r.breakApart(); } catch(_) {} }); } catch(_) {}
    // 確認用: 念のため最大行数の維持
  } else {
    sh = ss.insertSheet(sheetName);
  }

  const NAVY = "#233447";
  const MUTED = "#64748B";
  const BORDER = "#E3E7EF";
  const BG_SOFT = "#F2F4F7";
  const BG_BOX = "#F8FAFC";
  const AMBER = "#D97706";
  const GREEN = "#1e6b3a";

  if (isFirstBuild) sh.setHiddenGridlines(true);

  // 期間
  const [yy, mm] = yearMonth.split("-").map(Number);
  const monthStart = new Date(yy, mm - 1, 1);
  const monthEnd   = new Date(yy, mm, 1);

  // アクティブLG
  const lgs = _lgListRows()
    .filter(r => r[0] && String(r[4] || "").trim() === "アクティブ")
    .map(r => ({ name: String(r[0]).trim(), uid: String(r[2] || "").trim() }));

  // 週/日キー生成（月曜始まり）
  const _mondayOf = (d) => {
    const dow = d.getDay();
    const ms = new Date(d.getFullYear(), d.getMonth(), d.getDate() - ((dow + 6) % 7));
    return ms;
  };
  const _wkKey = (d) => { const m = _mondayOf(d); return `${m.getMonth()+1}/${m.getDate()}週`; };
  const _dKey  = (d) => `${String(d.getMonth()+1).padStart(2,"0")}/${String(d.getDate()).padStart(2,"0")}`;

  const weekKeys = []; const seen = new Set();
  const dayKeys = [];
  for (let d = new Date(monthStart); d < monthEnd; d.setDate(d.getDate() + 1)) {
    const wk = _wkKey(d);
    if (!seen.has(wk)) { seen.add(wk); weekKeys.push(wk); }
    dayKeys.push(_dKey(d));
  }

  // 集計バケット
  const lgMonthly = {}, lgWeekly = {}, lgDaily = {};
  lgs.forEach(lg => {
    lgMonthly[lg.name] = { total: 0, jisshi: 0, tobi: 0 };
    lgWeekly[lg.name]  = {}; weekKeys.forEach(k => lgWeekly[lg.name][k] = { total: 0, jisshi: 0, tobi: 0 });
    lgDaily[lg.name]   = {}; dayKeys.forEach(k  => lgDaily[lg.name][k]  = { total: 0, jisshi: 0, tobi: 0 });
  });
  // v5.7.1: CA別 月次集計 (列T=担当CA)
  const cas = _caListRows()
    .filter(r => r[0] && String(r[4] || "").trim() === "アクティブ")
    .map(r => String(r[0]).trim());
  const caMonthly = {};
  cas.forEach(name => { caMonthly[name] = { total: 0, jisshi: 0, jisshiYotei: 0, tobi: 0, cancel: 0, adjusting: 0 }; });
  let totalSet = 0, totalJ = 0, totalT = 0, totalC = 0;

  // v5.7.1: 必要列のみ読込 (A〜AD)
  for (const gsh of getAllGradeSheets()) {
    const lastRow = gsh.getLastRow();
    if (lastRow < 2) continue;
    const data = gsh.getRange(1, 1, lastRow, GRADE_SHEET_COLS).getValues();
    for (let i = 1; i < data.length; i++) {
      if (!data[i][0]) continue;
      const regDate = data[i][1];
      if (!(regDate instanceof Date)) continue;
      if (regDate < monthStart || regDate >= monthEnd) continue;
      const lgKey = String(data[i][2] || "").trim();
      const phase = String(data[i][21] || "").trim();
      totalSet++;
      if (phase === "実施済") totalJ++;
      else if (phase === "飛び") totalT++;
      else if (phase === "キャンセル") totalC++;
      // v5.7.1: CA別 月次集計
      const caKey = String(data[i][19] || "").trim();
      if (caMonthly[caKey]) {
        const cm = caMonthly[caKey];
        cm.total++;
        if (phase === "実施済") cm.jisshi++;
        else if (phase === "実施予定") cm.jisshiYotei++;
        else if (phase === "飛び") cm.tobi++;
        else if (phase === "キャンセル") cm.cancel++;
        else if (phase === "日程調整中") cm.adjusting++;
      }
      const ms = lgMonthly[lgKey], ws = lgWeekly[lgKey], ds = lgDaily[lgKey];
      if (!ms) continue;
      ms.total++;
      const wk = _wkKey(regDate); const dk = _dKey(regDate);
      const wb = ws[wk]; if (wb) wb.total++;
      const db = ds[dk]; if (db) db.total++;
      if (phase === "実施済") { ms.jisshi++; if (wb) wb.jisshi++; if (db) db.jisshi++; }
      else if (phase === "飛び") { ms.tobi++; if (wb) wb.tobi++; if (db) db.tobi++; }
    }
  }

  // 設定数降順ソート
  const sortedLgs = lgs.slice().sort((a, b) => lgMonthly[b.name].total - lgMonthly[a.name].total);

  // 目標
  const goal = _readGoal(yearMonth);

  // ── 描画 ──
  // 必要列数 = 1 (LG名) + 3 (月次) + weekKeys.length*3 + dayKeys.length*3
  const totalCols = 1 + 3 + weekKeys.length * 3 + dayKeys.length * 3;
  // シートの列数を確保
  const curMaxCols = sh.getMaxColumns();
  if (totalCols > curMaxCols) sh.insertColumnsAfter(curMaxCols, totalCols - curMaxCols);
  // 列幅
  sh.setColumnWidth(1, 130);
  for (let c = 2; c <= totalCols; c++) sh.setColumnWidth(c, 48);

  // タイトル
  sh.getRange(1, 1, 1, Math.min(totalCols, 12)).merge().setValue(`LG実績｜${yearMonth}`)
    .setBackground(NAVY).setFontColor("#FFFFFF").setFontWeight("bold").setFontSize(18)
    .setFontFamily("Noto Sans JP").setHorizontalAlignment("left").setVerticalAlignment("middle");
  sh.setRowHeight(1, 50);
  sh.getRange(2, 1, 1, Math.min(totalCols, 12)).merge().setValue(`更新: ${formatDatetime(new Date())}｜アクティブLG ${lgs.length}名`)
    .setBackground(BG_SOFT).setFontColor(MUTED).setFontSize(10)
    .setFontFamily("Noto Sans JP").setHorizontalAlignment("left").setVerticalAlignment("middle");
  sh.setRowHeight(2, 22);

  const section = (row, title) => {
    sh.getRange(row, 1, 1, Math.min(totalCols, 12)).merge().setValue(title)
      .setFontColor(NAVY).setFontWeight("bold").setFontSize(13)
      .setFontFamily("Noto Sans JP").setHorizontalAlignment("left").setVerticalAlignment("middle");
    sh.setRowHeight(row, 32);
    sh.getRange(row, 1, 1, Math.min(totalCols, 12)).setBorder(null, null, true, null, null, null, NAVY, SpreadsheetApp.BorderStyle.SOLID);
  };

  // ▌ 月次サマリ KPI
  section(4, "▌ 月次サマリ (この月の合計)");
  const card = (r, c, label, value, sub, color) => {
    sh.getRange(r, c, 1, 3).merge().setValue(label).setBackground(BG_BOX).setFontColor(MUTED).setFontSize(10).setFontWeight("bold").setFontFamily("Noto Sans JP").setHorizontalAlignment("center").setVerticalAlignment("middle");
    sh.getRange(r+1, c, 1, 3).merge().setValue(value).setBackground(BG_BOX).setFontColor(color || NAVY).setFontSize(22).setFontWeight("bold").setFontFamily("Noto Sans JP").setHorizontalAlignment("center").setVerticalAlignment("middle");
    sh.getRange(r+2, c, 1, 3).merge().setValue(sub || "").setBackground(BG_BOX).setFontColor(MUTED).setFontSize(10).setFontFamily("Noto Sans JP").setHorizontalAlignment("center").setVerticalAlignment("middle");
    sh.getRange(r, c, 3, 3).setBorder(true, true, true, true, null, null, NAVY, SpreadsheetApp.BorderStyle.SOLID_MEDIUM);
  };
  card(5, 1,  "累計設定", totalSet, "今月");
  card(5, 4,  "実施済",   totalJ,   totalSet ? `${Math.round(totalJ/totalSet*100)}%` : "-");
  card(5, 7,  "飛び",     totalT,   totalSet ? `${Math.round(totalT/totalSet*100)}%` : "-", AMBER);
  card(5, 10, "キャンセル", totalC, totalSet ? `${Math.round(totalC/totalSet*100)}%` : "-");
  sh.setRowHeight(5, 26); sh.setRowHeight(6, 44); sh.setRowHeight(7, 22);

  // ▌ 目標 vs 実績
  section(9, "▌ 目標 vs 実績 (目標設定シートで編集)");
  const goalRows = [
    ["KPI", "目標", "実績", "達成率"],
    ["累計設定", goal.set || 0, totalSet, goal.set ? `${Math.round(totalSet/goal.set*100)}%` : "-"],
    ["実施数", goal.jisshi || 0, totalJ, goal.jisshi ? `${Math.round(totalJ/goal.jisshi*100)}%` : "-"],
    ["飛び率", goal.tobiRate ? `${goal.tobiRate}%以下` : "-",
       totalSet ? `${Math.round(totalT/totalSet*100)}%` : "-",
       (totalSet && goal.tobiRate) ? ((totalT/totalSet*100) <= goal.tobiRate ? "✅達成" : "❌未達") : "-"],
  ];
  sh.getRange(10, 1, goalRows.length, 4).setValues(goalRows);
  sh.getRange(10, 1, 1, 4).setBackground(BG_SOFT).setFontWeight("bold").setFontSize(10).setHorizontalAlignment("center").setFontFamily("Noto Sans JP");
  sh.getRange(10, 1, goalRows.length, 4).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);
  for (let r = 10; r < 10 + goalRows.length; r++) sh.setRowHeight(r, 26);

  let row = 10 + goalRows.length + 2;

  // ▌ LG別 目標進捗 + 月次+週次 (左右並列)
  section(row, "▌ LG別 目標進捗 + 月次+週次 (目標は目標設定シートで編集)");
  row++;
  const lgGoals = _readLGGoals(yearMonth);
  // 進捗パート: 10列 (LG名 + 9 metric)
  const progCols = 10;
  // 区切り: 1列
  const gapCol = 1;
  // 月次+週次パート: 3 + weeks*3 列
  const mwCols = 3 + weekKeys.length * 3;
  const totalLgCols = progCols + gapCol + mwCols;

  // Header row 1: top (LG名 + 進捗各列ヘッダ + 区切り + 月次合計(merged) + 各週(merged))
  const hdr1 = ["LGメンバー", "設定目標", "設定実績", "設定達成率", "実施目標", "実施実績", "実施達成率", "飛率目標", "飛率実績", "飛率判定", "", "月次合計", "", "", ...weekKeys.flatMap(k => [k, "", ""])];
  sh.getRange(row, 1, 1, totalLgCols).setValues([hdr1])
    .setBackground(NAVY).setFontColor("#FFFFFF").setFontWeight("bold").setFontSize(10).setHorizontalAlignment("center").setFontFamily("Noto Sans JP");
  // merge: 月次合計 = cols 12-14
  sh.getRange(row, 12, 1, 3).merge();
  // 各週 = cols 15,16,17 / 18,19,20 / ...
  weekKeys.forEach((_, i) => sh.getRange(row, 15 + i * 3, 1, 3).merge());
  row++;
  // Header row 2: sub (空欄 for 進捗, gap, 設実飛% for 月次/週次)
  const hdr2 = ["", "", "", "", "", "", "", "", "", "", "", "設", "実", "飛%", ...weekKeys.flatMap(() => ["設", "実", "飛%"])];
  sh.getRange(row, 1, 1, totalLgCols).setValues([hdr2])
    .setBackground(BG_SOFT).setFontWeight("bold").setFontSize(9).setHorizontalAlignment("center").setFontFamily("Noto Sans JP");
  // 1段目との結合 (進捗パートはヘッダ1行のみ → 2行マージ)
  for (let c = 1; c <= 10; c++) sh.getRange(row - 1, c, 2, 1).merge();
  // gap col も2行マージ (空白)
  sh.getRange(row - 1, 11, 2, 1).merge().setBackground("#FFFFFF").setBorder(null, null, null, null, null, null);
  row++;
  // Data rows
  const combRows = sortedLgs.map(lg => {
    const s = lgMonthly[lg.name];
    const g = lgGoals[lg.name] || {};
    const setRate = g.set ? Math.round(s.total / g.set * 100) : "";
    const jisRate = g.jisshi ? Math.round(s.jisshi / g.jisshi * 100) : "";
    const tobiActual = s.total ? Math.round(s.tobi / s.total * 100) : 0;
    const tobiOK = g.tobiRate ? (tobiActual <= g.tobiRate ? "✅" : "❌") : "";
    const progPart = [
      lg.name,
      g.set || "-", s.total, setRate !== "" ? `${setRate}%` : "-",
      g.jisshi || "-", s.jisshi, jisRate !== "" ? `${jisRate}%` : "-",
      g.tobiRate ? `${g.tobiRate}%以下` : "-", s.total ? `${tobiActual}%` : "-", tobiOK,
    ];
    const monthlyPart = [s.total || "-", s.jisshi || "-", s.total ? `${Math.round(s.tobi/s.total*100)}%` : "-"];
    const weeklyPart = [];
    weekKeys.forEach(k => {
      const w = lgWeekly[lg.name][k];
      weeklyPart.push(w.total || "-", w.jisshi || "-", w.total ? `${Math.round(w.tobi/w.total*100)}%` : "-");
    });
    return [...progPart, "", ...monthlyPart, ...weeklyPart];
  });
  if (combRows.length) {
    sh.getRange(row, 1, combRows.length, totalLgCols).setValues(combRows);
    sh.getRange(row - 2, 1, combRows.length + 2, totalLgCols).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);
    // 月次合計列は強調
    sh.getRange(row - 1, 12, combRows.length + 1, 3).setBackground("#fff3c4");
    // gap列は枠なし (見た目区切り)
    sh.getRange(row, 11, combRows.length, 1).setBackground("#FFFFFF").setBorder(false, false, false, false, false, false);
    for (let r = row; r < row + combRows.length; r++) sh.setRowHeight(r, 24);
    row += combRows.length + 2;
  } else { row += 2; }

  // ▌ LG × 日次
  section(row, "▌ LG × 日次 (月内の各日)");
  row++;
  const dHeaderTop = ["LGメンバー"];
  const dHeaderSub = [""];
  dayKeys.forEach(k => { dHeaderTop.push(k, "", ""); dHeaderSub.push("設", "実", "飛%"); });
  const dCols = 1 + dayKeys.length * 3;
  sh.getRange(row, 1, 1, dCols).setValues([dHeaderTop])
    .setBackground(NAVY).setFontColor("#FFFFFF").setFontWeight("bold").setFontSize(10).setHorizontalAlignment("center").setFontFamily("Noto Sans JP");
  dayKeys.forEach((_, i) => sh.getRange(row, 2 + i * 3, 1, 3).merge());
  row++;
  sh.getRange(row, 1, 1, dCols).setValues([dHeaderSub])
    .setBackground(BG_SOFT).setFontWeight("bold").setFontSize(9).setHorizontalAlignment("center").setFontFamily("Noto Sans JP");
  row++;
  const dValues = sortedLgs.map(lg => {
    const r = [lg.name];
    dayKeys.forEach(k => {
      const d = lgDaily[lg.name][k];
      r.push(d.total || "-", d.jisshi || "-", d.total ? `${Math.round(d.tobi/d.total*100)}%` : "-");
    });
    return r;
  });
  if (dValues.length) {
    sh.getRange(row, 1, dValues.length, dCols).setValues(dValues);
    sh.getRange(row - 2, 1, dValues.length + 2, dCols).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);
    for (let r = row; r < row + dValues.length; r++) sh.setRowHeight(r, 22);
  }

  sh.setFrozenRows(3);
  // タイトル行のマージとの干渉を避けるため列固定はしない
  sh.setTabColor(NAVY);
  // v5.7.1: ビルドメタ保存 (差分判定用)
  try {
    PropertiesService.getScriptProperties().setProperty(propsKey, JSON.stringify({
      lastBuildTs: Date.now(), totalRows: totalRowsNow,
    }));
  } catch(_) {}
  return `${sheetName} 構築完了`;
}

function _buildMonthlyDashboard_OLD(yearMonth) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheetName = `LG実績_${yearMonth}`;
  let sh = ss.getSheetByName(sheetName);
  if (sh) ss.deleteSheet(sh);
  sh = ss.insertSheet(sheetName);

  const NAVY = "#233447";
  const MUTED = "#64748B";
  const BORDER = "#E3E7EF";
  const BG_SOFT = "#F2F4F7";
  const BG_BOX = "#F8FAFC";
  const AMBER = "#D97706";
  const GREEN = "#1e6b3a";

  sh.setHiddenGridlines(true);
  const widths = [110, 100, 100, 70, 110, 100, 100, 70, 110, 100, 100, 100];
  widths.forEach((w, i) => sh.setColumnWidth(i + 1, w));

  // 期間定義: YYYY-MM
  const [yy, mm] = yearMonth.split("-").map(Number);
  const monthStart = new Date(yy, mm - 1, 1);
  const monthEnd   = new Date(yy, mm, 1);  // exclusive
  const inMonth = (d) => d instanceof Date && d >= monthStart && d < monthEnd;

  // アクティブLG
  const lgs = _lgListRows()
    .filter(r => r[0] && String(r[4] || "").trim() === "アクティブ")
    .map(r => ({ name: String(r[0]).trim(), uid: String(r[2] || "").trim() }));
  const stats = {};
  lgs.forEach(lg => {
    stats[lg.name] = { total: 0, jisshi: 0, jisshiYotei: 0, tobi: 0, cancel: 0, futeki: 0, adjusting: 0 };
  });

  // 集計
  let total = 0, totalJ = 0, totalJY = 0, totalT = 0, totalC = 0, totalF = 0, totalA = 0;
  // 週次バケット (この月の各週): キー=月曜の日付
  const weekly = {};
  // 日次バケット (この月の各日): キー=YYYY-MM-DD
  const daily = {};
  // 実施予定日ベース
  const dailyByConf = {};

  const _weekKey = (d) => {
    const dow = d.getDay();
    const monday = new Date(d.getFullYear(), d.getMonth(), d.getDate() - ((dow + 6) % 7));
    return `${monday.getMonth() + 1}/${monday.getDate()}〜`;
  };
  const _dayKey = (d) => `${String(d.getMonth() + 1).padStart(2, "0")}/${String(d.getDate()).padStart(2, "0")}`;

  for (const gsh of getAllGradeSheets()) {
    const data = gsh.getDataRange().getValues();
    for (let i = 1; i < data.length; i++) {
      if (!data[i][0]) continue;
      const regDate = data[i][1];
      const confTimeStr = String(data[i][18] || "").trim();
      const phase = String(data[i][21] || "").trim();
      const lgKey = String(data[i][2] || "").trim();
      // 設定日ベース集計
      if (inMonth(regDate)) {
        total++;
        if (phase === "実施済") totalJ++;
        else if (phase === "実施予定") totalJY++;
        else if (phase === "飛び") totalT++;
        else if (phase === "キャンセル") totalC++;
        else if (phase === "調整不可") totalF++;
        else if (phase === "日程調整中") totalA++;
        // 週/日バケット
        const wk = _weekKey(regDate);
        const dk = _dayKey(regDate);
        if (!weekly[wk]) weekly[wk] = { total: 0, jisshi: 0, tobi: 0, cancel: 0 };
        if (!daily[dk])  daily[dk]  = { total: 0, jisshi: 0, tobi: 0, cancel: 0 };
        weekly[wk].total++; daily[dk].total++;
        if (phase === "実施済") { weekly[wk].jisshi++; daily[dk].jisshi++; }
        else if (phase === "飛び") { weekly[wk].tobi++; daily[dk].tobi++; }
        else if (phase === "キャンセル") { weekly[wk].cancel++; daily[dk].cancel++; }
        // LG別
        const s = stats[lgKey];
        if (s) {
          s.total++;
          if (phase === "実施済") s.jisshi++;
          else if (phase === "実施予定") s.jisshiYotei++;
          else if (phase === "飛び") s.tobi++;
          else if (phase === "キャンセル") s.cancel++;
          else if (phase === "調整不可") s.futeki++;
          else if (phase === "日程調整中") s.adjusting++;
        }
      }
      // 実施予定日ベース集計
      if (confTimeStr) {
        const m = confTimeStr.match(/^(\d{4})\/(\d{1,2})\/(\d{1,2})/);
        if (m) {
          const confDate = new Date(+m[1], +m[2] - 1, +m[3]);
          if (inMonth(confDate)) {
            const dk = _dayKey(confDate);
            if (!dailyByConf[dk]) dailyByConf[dk] = { total: 0, jisshi: 0, tobi: 0, cancel: 0 };
            dailyByConf[dk].total++;
            if (phase === "実施済") dailyByConf[dk].jisshi++;
            else if (phase === "飛び") dailyByConf[dk].tobi++;
            else if (phase === "キャンセル") dailyByConf[dk].cancel++;
          }
        }
      }
    }
  }

  // 目標設定読み込み
  const goal = _readGoal(yearMonth);

  // ── タイトル ──
  sh.getRange(1, 1, 1, 12).merge().setValue(`LG実績｜${yearMonth}`)
    .setBackground(NAVY).setFontColor("#FFFFFF").setFontWeight("bold").setFontSize(20)
    .setFontFamily("Noto Sans JP").setHorizontalAlignment("left").setVerticalAlignment("middle");
  sh.setRowHeight(1, 56);
  sh.getRange(2, 1, 1, 12).merge().setValue(`自動更新 / 最終: ${formatDatetime(new Date())}`)
    .setBackground(BG_SOFT).setFontColor(MUTED).setFontSize(10)
    .setFontFamily("Noto Sans JP").setHorizontalAlignment("left").setVerticalAlignment("middle");
  sh.setRowHeight(2, 24);

  const section = (row, title) => {
    sh.getRange(row, 1, 1, 12).merge().setValue(title)
      .setFontColor(NAVY).setFontWeight("bold").setFontSize(13)
      .setFontFamily("Noto Sans JP").setHorizontalAlignment("left").setVerticalAlignment("middle");
    sh.setRowHeight(row, 32);
    sh.getRange(row, 1, 1, 12).setBorder(null, null, true, null, null, null, NAVY, SpreadsheetApp.BorderStyle.SOLID);
  };

  // ── 月次KPI (4 cards) ──
  section(4, "▌ 月次サマリ (設定日ベース)");
  const card = (r, c, label, value, sub, color) => {
    sh.getRange(r, c, 1, 3).merge().setValue(label).setBackground(BG_BOX).setFontColor(MUTED).setFontSize(10).setFontWeight("bold").setFontFamily("Noto Sans JP").setHorizontalAlignment("center").setVerticalAlignment("middle");
    sh.getRange(r + 1, c, 1, 3).merge().setValue(value).setBackground(BG_BOX).setFontColor(color || NAVY).setFontSize(24).setFontWeight("bold").setFontFamily("Noto Sans JP").setHorizontalAlignment("center").setVerticalAlignment("middle");
    sh.getRange(r + 2, c, 1, 3).merge().setValue(sub || "").setBackground(BG_BOX).setFontColor(MUTED).setFontSize(10).setFontFamily("Noto Sans JP").setHorizontalAlignment("center").setVerticalAlignment("middle");
    sh.getRange(r, c, 3, 3).setBorder(true, true, true, true, null, null, NAVY, SpreadsheetApp.BorderStyle.SOLID_MEDIUM);
  };
  card(5, 1,  "累計設定",  total,  "今月分");
  card(5, 4,  "実施済",    totalJ, total ? `${(totalJ/total*100).toFixed(1)}%` : "-");
  card(5, 7,  "飛び",      totalT, total ? `${(totalT/total*100).toFixed(1)}%` : "-", AMBER);
  card(5, 10, "キャンセル", totalC, total ? `${(totalC/total*100).toFixed(1)}%` : "-");
  sh.setRowHeight(5, 28); sh.setRowHeight(6, 48); sh.setRowHeight(7, 24);

  // ── 目標 vs 実績 ──
  section(9, "▌ 目標 vs 実績 (目標設定シートで編集可)");
  const goalRows = [
    ["KPI", "目標", "実績", "達成率"],
    ["累計設定", goal.set || 0, total, goal.set ? `${(total / goal.set * 100).toFixed(1)}%` : "-"],
    ["実施数",   goal.jisshi || 0, totalJ, goal.jisshi ? `${(totalJ / goal.jisshi * 100).toFixed(1)}%` : "-"],
    ["飛び率(目標以下)", goal.tobiRate ? `${goal.tobiRate}%以下` : "-", total ? `${(totalT/total*100).toFixed(1)}%` : "-", total && goal.tobiRate ? ((totalT/total*100) <= goal.tobiRate ? "✅達成" : "❌未達") : "-"],
  ];
  sh.getRange(10, 1, goalRows.length, 4).setValues(goalRows);
  sh.getRange(10, 1, 1, 4).setBackground(BG_SOFT).setFontWeight("bold").setHorizontalAlignment("center").setFontSize(10).setFontFamily("Noto Sans JP");
  sh.getRange(10, 1, goalRows.length, 4).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);
  for (let r = 10; r < 10 + goalRows.length; r++) sh.setRowHeight(r, 28);

  // ── 週次内訳 ──
  let rowCursor = 10 + goalRows.length + 2;
  section(rowCursor, "▌ 週次内訳 (設定日ベース・今月の週ごと)");
  rowCursor++;
  const wkKeys = Object.keys(weekly).sort((a, b) => {
    const [am, ad] = a.replace("〜", "").split("/").map(Number);
    const [bm, bd] = b.replace("〜", "").split("/").map(Number);
    return am - bm || ad - bd;
  });
  const wkHeader = ["週(月曜〜)", "設定", "実施", "飛び", "キャンセル", "実施率", "飛び率"];
  const wkRows = [wkHeader].concat(wkKeys.map(k => {
    const w = weekly[k];
    return [k, w.total, w.jisshi, w.tobi, w.cancel,
      w.total ? `${(w.jisshi/w.total*100).toFixed(1)}%` : "-",
      w.total ? `${(w.tobi/w.total*100).toFixed(1)}%` : "-",
    ];
  }));
  if (wkRows.length > 1) {
    sh.getRange(rowCursor, 1, wkRows.length, 7).setValues(wkRows);
    sh.getRange(rowCursor, 1, 1, 7).setBackground(BG_SOFT).setFontWeight("bold").setFontSize(10).setHorizontalAlignment("center").setFontFamily("Noto Sans JP");
    sh.getRange(rowCursor, 1, wkRows.length, 7).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);
    for (let r = rowCursor; r < rowCursor + wkRows.length; r++) sh.setRowHeight(r, 26);
    rowCursor += wkRows.length + 2;
  } else {
    sh.getRange(rowCursor, 1).setValue("(今月のデータなし)").setFontColor(MUTED).setFontStyle("italic");
    rowCursor += 2;
  }

  // ── 日次内訳 (設定日) ──
  section(rowCursor, "▌ 日次内訳 (設定日ベース)");
  rowCursor++;
  const dayKeysSet = Object.keys(daily).sort();
  const dHeader = ["日付", "設定", "実施", "飛び", "キャンセル", "実施率"];
  const dRows = [dHeader].concat(dayKeysSet.map(k => {
    const d = daily[k];
    return [k, d.total, d.jisshi, d.tobi, d.cancel,
      d.total ? `${(d.jisshi/d.total*100).toFixed(1)}%` : "-",
    ];
  }));
  if (dRows.length > 1) {
    sh.getRange(rowCursor, 1, dRows.length, 6).setValues(dRows);
    sh.getRange(rowCursor, 1, 1, 6).setBackground(BG_SOFT).setFontWeight("bold").setFontSize(10).setHorizontalAlignment("center").setFontFamily("Noto Sans JP");
    sh.getRange(rowCursor, 1, dRows.length, 6).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);
    for (let r = rowCursor; r < rowCursor + dRows.length; r++) sh.setRowHeight(r, 24);
    rowCursor += dRows.length + 2;
  } else {
    rowCursor += 2;
  }

  // ── 日次内訳 (実施予定日) ──
  section(rowCursor, "▌ 日次内訳 (実施予定日ベース)");
  rowCursor++;
  const dayKeysConf = Object.keys(dailyByConf).sort();
  const cHeader = ["実施予定日", "件数", "実施済", "飛び", "キャンセル", "実施率"];
  const cRows = [cHeader].concat(dayKeysConf.map(k => {
    const d = dailyByConf[k];
    return [k, d.total, d.jisshi, d.tobi, d.cancel,
      d.total ? `${(d.jisshi/d.total*100).toFixed(1)}%` : "-",
    ];
  }));
  if (cRows.length > 1) {
    sh.getRange(rowCursor, 1, cRows.length, 6).setValues(cRows);
    sh.getRange(rowCursor, 1, 1, 6).setBackground(BG_SOFT).setFontWeight("bold").setFontSize(10).setHorizontalAlignment("center").setFontFamily("Noto Sans JP");
    sh.getRange(rowCursor, 1, cRows.length, 6).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);
    for (let r = rowCursor; r < rowCursor + cRows.length; r++) sh.setRowHeight(r, 24);
    rowCursor += cRows.length + 2;
  } else {
    rowCursor += 2;
  }

  // ── v5.7.2: LG別 (左 A〜H) と CA別 (右 J〜Q) を並列配置 ──
  const blockHeaderRow = rowCursor;
  const blockTableRow  = rowCursor + 1;
  const _sectHdr = (col, title) => {
    sh.getRange(blockHeaderRow, col, 1, 8).merge().setValue(title)
      .setFontColor(NAVY).setFontWeight("bold").setFontSize(13).setFontFamily("Noto Sans JP")
      .setHorizontalAlignment("left").setVerticalAlignment("middle");
    sh.getRange(blockHeaderRow, col, 1, 8).setBorder(null, null, true, null, null, null, NAVY, SpreadsheetApp.BorderStyle.SOLID);
  };
  sh.setRowHeight(blockHeaderRow, 32);

  // LG別 (左: 列1〜8)
  _sectHdr(1, "▌ LG別 実績 (設定日ベース・実施率順)");
  const sortedLgs = lgs.slice().sort((a, b) => {
    const sa = stats[a.name], sb = stats[b.name];
    const ra = sa.total ? sa.jisshi / sa.total : 0;
    const rb = sb.total ? sb.jisshi / sb.total : 0;
    return rb - ra;
  });
  const lgHeader = ["LGメンバー", "累計設定", "実施済", "実施予定", "調整中", "飛び", "キャンセル", "実施率"];
  const lgRows = [lgHeader].concat(sortedLgs.map(lg => {
    const s = stats[lg.name];
    return [lg.name, s.total, s.jisshi, s.jisshiYotei, s.adjusting, s.tobi, s.cancel,
      s.total ? `${(s.jisshi/s.total*100).toFixed(1)}%` : "-",
    ];
  }));
  sh.getRange(blockTableRow, 1, lgRows.length, 8).setValues(lgRows);
  sh.getRange(blockTableRow, 1, 1, 8).setBackground(BG_SOFT).setFontWeight("bold").setFontSize(10).setHorizontalAlignment("center").setFontFamily("Noto Sans JP");
  sh.getRange(blockTableRow, 1, lgRows.length, 8).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);

  // CA別 (右: 列10〜17 = J〜Q)
  const CA_COL = 10;
  _sectHdr(CA_COL, "▌ CA別 実績 (担当面談ベース・実施率順)");
  const sortedCas = cas.slice().sort((a, b) => {
    const ca = caMonthly[a], cb = caMonthly[b];
    const ra = ca.total ? ca.jisshi / ca.total : 0;
    const rb = cb.total ? cb.jisshi / cb.total : 0;
    return rb - ra;
  });
  const caHeader = ["CAメンバー", "担当総数", "実施済", "実施予定", "調整中", "飛び", "キャンセル", "実施率"];
  const caRows = [caHeader].concat(sortedCas.map(name => {
    const c = caMonthly[name];
    return [name, c.total, c.jisshi, c.jisshiYotei, c.adjusting, c.tobi, c.cancel,
      c.total ? `${(c.jisshi/c.total*100).toFixed(1)}%` : "-",
    ];
  }));
  sh.getRange(blockTableRow, CA_COL, caRows.length, 8).setValues(caRows);
  sh.getRange(blockTableRow, CA_COL, 1, 8).setBackground(BG_SOFT).setFontWeight("bold").setFontSize(10).setHorizontalAlignment("center").setFontFamily("Noto Sans JP");
  sh.getRange(blockTableRow, CA_COL, caRows.length, 8).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);

  const maxRows = Math.max(lgRows.length, caRows.length);
  for (let r = blockTableRow; r < blockTableRow + maxRows; r++) sh.setRowHeight(r, 26);
  rowCursor = blockTableRow + maxRows + 2;

  sh.setFrozenRows(2);
  return `${sheetName} 構築完了`;
}

// 目標設定シート読み込み — 全体行を返す (なければ空)
function _readGoal(yearMonth) {
  const sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("目標設定");
  if (!sh) return {};
  const data = sh.getDataRange().getValues();
  for (let i = 1; i < data.length; i++) {
    if (String(data[i][0]).trim() === yearMonth && String(data[i][1]).trim() === "全体") {
      return {
        set:      Number(data[i][2]) || 0,
        jisshi:   Number(data[i][3]) || 0,
        tobiRate: Number(data[i][4]) || 0,
      };
    }
  }
  return {};
}

// LG別 目標 マップ {lgName: {set, jisshi, tobiRate}}
function _readLGGoals(yearMonth) {
  const sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("目標設定");
  if (!sh) return {};
  const data = sh.getDataRange().getValues();
  const map = {};
  for (let i = 1; i < data.length; i++) {
    if (String(data[i][0]).trim() !== yearMonth) continue;
    const name = String(data[i][1]).trim();
    if (!name || name === "全体") continue;
    map[name] = {
      set:      Number(data[i][2]) || 0,
      jisshi:   Number(data[i][3]) || 0,
      tobiRate: Number(data[i][4]) || 0,
    };
  }
  return map;
}

// v5.7+: 目標設定シート (LG別)
// 列: 月(YYYY-MM) / LGメンバー / 設定目標 / 実施目標 / 飛率目標(%) / 備考
//      "全体" 行 = 月の全体目標 (LG別とは別) もサポート
function ensureGoalSheet() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sh = ss.getSheetByName("目標設定");
  if (!sh) {
    sh = ss.insertSheet("目標設定");
    sh.getRange(1, 1, 1, 6).setValues([["月 (YYYY-MM)", "LGメンバー", "設定目標", "実施目標", "飛率目標(%)", "備考"]])
      .setBackground("#233447").setFontColor("#FFFFFF").setFontWeight("bold").setFontFamily("Noto Sans JP");
    [120, 150, 100, 100, 130, 200].forEach((w, i) => sh.setColumnWidth(i + 1, w));
    sh.setFrozenRows(1);
  } else if (sh.getRange(1, 2).getValue() !== "LGメンバー") {
    // 旧スキーマ (月のみ)からマイグレーション
    const old = sh.getDataRange().getValues();
    sh.clear();
    sh.getRange(1, 1, 1, 6).setValues([["月 (YYYY-MM)", "LGメンバー", "設定目標", "実施目標", "飛率目標(%)", "備考"]])
      .setBackground("#233447").setFontColor("#FFFFFF").setFontWeight("bold").setFontFamily("Noto Sans JP");
    [120, 150, 100, 100, 130, 200].forEach((w, i) => sh.setColumnWidth(i + 1, w));
    sh.setFrozenRows(1);
    // 旧データ: [月, 設定目標, 実施目標, 飛率目標, 備考] → 全体行として移行
    old.slice(1).forEach(r => {
      if (r[0]) sh.appendRow([r[0], "全体", r[1] || 0, r[2] || 0, r[3] || 0, r[4] || ""]);
    });
  }
  // 当月の全LG行が無ければ追加 (全体 + 各アクティブLG)
  const now = new Date();
  const ym = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
  const data = sh.getDataRange().getValues();
  const existing = new Set(data.slice(1).filter(r => String(r[0]).trim() === ym).map(r => String(r[1]).trim()));
  if (!existing.has("全体")) sh.appendRow([ym, "全体", 0, 0, 0, ""]);
  const lgs = _lgListRows().filter(r => r[0] && String(r[4] || "").trim() === "アクティブ").map(r => String(r[0]).trim());
  lgs.forEach(name => { if (!existing.has(name)) sh.appendRow([ym, name, 0, 0, 0, ""]); });
  return `目標設定 ready (${ym} ${lgs.length + 1}行確認)`;
}

function buildLGDashboard(period) {
  period = period || "全期間";
  const periodCfg = _periodFilter(period);
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheetName = period === "全期間" ? (DASHBOARD_SHEET || "LG実績ダッシュボード") : `LG実績_${period}`;

  // v5.7.1: 差分判定 — 直近5分以内に再ビルド済 かつ シート総行数に変化なしならskip
  //   propsKey: __lgdash_meta_<period> に { lastBuildTs, totalRows } を保存
  const propsKey = `__lgdash_meta_${period}`;
  const totalRowsNow = getAllGradeSheets().reduce((acc, gs) => acc + gs.getLastRow(), 0);
  try {
    const metaRaw = PropertiesService.getScriptProperties().getProperty(propsKey);
    if (metaRaw) {
      const meta = JSON.parse(metaRaw);
      const elapsed = Date.now() - (meta.lastBuildTs || 0);
      // v5.7.2: フェーズ変更は行数を変えないため、行数一致での skip は廃止。
      //         連打デバウンス目的で「90秒以内」のみ skip (データ変更は常に反映)
      if (elapsed < 90 * 1000) {
        Logger.log(`[buildLGDashboard] skip (last ${elapsed}ms / rows unchanged=${totalRowsNow})`);
        return `skipped (recently built ${elapsed}ms ago)`;
      }
    }
  } catch(_) {}

  // v5.7.1: deleteSheet+insertSheet (重い) ではなく clear() で内容のみ削除 — 列幅とグリッド設定を再利用
  let sh = ss.getSheetByName(sheetName);
  const isFirstBuild = !sh;
  if (sh) {
    sh.clear({ contentsOnly: false, formatOnly: false, validationsOnly: false });
    // チャートも消す
    sh.getCharts().forEach(c => sh.removeChart(c));
    // マージ解除
    try { sh.getRange(1, 1, Math.max(sh.getMaxRows(), 200), 12).breakApart(); } catch(_) {}
  } else {
    sh = ss.insertSheet(sheetName);
  }

  const NAVY = "#233447";
  const MUTED = "#64748B";
  const BORDER = "#E3E7EF";
  const BG_SOFT = "#F2F4F7";
  const BG_BOX = "#F8FAFC";

  // v5.7.1: 初回のみ列幅・グリッド設定を実行 (2回目以降は既存設定を再利用)
  if (isFirstBuild) {
    sh.setHiddenGridlines(true);
    const widths = [120, 120, 120, 70, 120, 120, 120, 70, 120, 120, 120, 100];
    widths.forEach((w, i) => sh.setColumnWidth(i + 1, w));
  }

  // 集計（v5.7+: 非アクティブLGは厳格除外。「アクティブ」のみ）
  const lgs = _lgListRows()
    .filter(r => r[0] && String(r[4] || "").trim() === "アクティブ")
    .map(r => ({ name: String(r[0]).trim(), uid: String(r[2] || "").trim() }));
  const stats = {};
  lgs.forEach(lg => {
    const obj = { total: 0, jisshi: 0, jisshiYotei: 0, tobi: 0, risuke: 0, cancel: 0, futeki: 0, dup: 0, adjusting: 0, bySns: {}, lastReg: null };
    stats[lg.name] = obj;
    if (lg.uid) stats[lg.uid] = obj;
  });
  // v5.7.1: CA別集計 (列T=担当CA)。アクティブCAのみ
  const cas = _caListRows()
    .filter(r => r[0] && String(r[4] || "").trim() === "アクティブ")
    .map(r => String(r[0]).trim());
  const caStats = {};
  cas.forEach(name => { caStats[name] = { total: 0, jisshi: 0, jisshiYotei: 0, tobi: 0, cancel: 0, adjusting: 0 }; });
  let total = 0, totalJisshi = 0, totalJisshiYotei = 0, totalTobi = 0, totalCancel = 0, totalFuteki = 0, totalAdjusting = 0;
  const snsCount = {};
  // v5.7.1: 必要列のみ読込 (A〜AD)
  for (const gsh of getAllGradeSheets()) {
    const lastRow = gsh.getLastRow();
    if (lastRow < 2) continue;
    const data = gsh.getRange(1, 1, lastRow, GRADE_SHEET_COLS).getValues();
    for (let i = 1; i < data.length; i++) {
      if (!data[i][0]) continue;
      const regDate = data[i][1];  // B列: 登録日
      if (!periodCfg.fn(regDate)) continue;  // 期間フィルタ
      const lgKey = String(data[i][2] || "").trim();
      const phase = String(data[i][21] || "").trim();
      const sns   = String(data[i][6] || "").trim() || "未指定";
      total++;
      snsCount[sns] = (snsCount[sns] || 0) + 1;
      if (phase === "実施済") totalJisshi++;
      else if (phase === "実施予定") totalJisshiYotei++;
      else if (phase === "飛び") totalTobi++;
      else if (phase === "キャンセル") totalCancel++;
      else if (phase === "調整不可") totalFuteki++;
      else if (phase === "日程調整中") totalAdjusting++;
      // v5.7.1: CA別集計 (列T=index19)
      const caKey = String(data[i][19] || "").trim();
      if (caStats[caKey]) {
        const cs = caStats[caKey];
        cs.total++;
        if (phase === "実施済") cs.jisshi++;
        else if (phase === "実施予定") cs.jisshiYotei++;
        else if (phase === "飛び") cs.tobi++;
        else if (phase === "キャンセル") cs.cancel++;
        else if (phase === "日程調整中") cs.adjusting++;
      }
      if (!stats[lgKey]) continue;
      const s = stats[lgKey];
      s.total++;
      s.bySns[sns] = (s.bySns[sns] || 0) + 1;
      if (phase === "実施済") s.jisshi++;
      else if (phase === "実施予定") s.jisshiYotei++;
      else if (phase === "飛び") s.tobi++;
      else if (phase === "リスケ") s.risuke++;
      else if (phase === "キャンセル") s.cancel++;
      else if (phase === "調整不可") s.futeki++;
      else if (phase === "日程調整中") s.adjusting++;
    }
  }

  // タイトル
  sh.getRange(1, 1).setValue(`LG実績ダッシュボード｜${periodCfg.label}`);
  sh.getRange(2, 1).setValue(`自動更新 / 最終: ${formatDatetime(new Date())} / 期間: ${periodCfg.label}`);
  sh.getRange(1, 1, 1, 12).merge().setBackground(NAVY).setFontColor("#FFFFFF").setFontWeight("bold").setFontSize(20)
    .setFontFamily("Noto Sans JP").setHorizontalAlignment("left").setVerticalAlignment("middle");
  sh.setRowHeight(1, 60);
  sh.getRange(2, 1, 1, 12).merge().setBackground(BG_SOFT).setFontColor(MUTED).setFontSize(10)
    .setFontFamily("Noto Sans JP").setHorizontalAlignment("left").setVerticalAlignment("middle");
  sh.setRowHeight(2, 28);
  sh.getRange(2, 1, 1, 12).setBorder(null, null, true, null, null, null, NAVY, SpreadsheetApp.BorderStyle.SOLID_THICK);

  const section = (row, title, cols) => {
    cols = cols || 12;
    sh.getRange(row, 1, 1, cols).merge().setValue(title)
      .setFontColor(NAVY).setFontWeight("bold").setFontSize(14)
      .setFontFamily("Noto Sans JP").setHorizontalAlignment("left").setVerticalAlignment("middle");
    sh.setRowHeight(row, 40);
    sh.getRange(row, 1, 1, cols).setBorder(null, null, true, null, null, null, NAVY, SpreadsheetApp.BorderStyle.SOLID);
  };

  // ── KPIカード 4枚 (行 4-7) ──
  section(4, "全体KPI");
  const cards = [
    { col: 1, label: "累計設定", value: total, sub: "全フェーズ" },
    { col: 4, label: "実施済", value: totalJisshi, sub: total ? `${(totalJisshi/total*100).toFixed(1)}%` : "-" },
    { col: 7, label: "実施予定", value: totalJisshiYotei, sub: total ? `${(totalJisshiYotei/total*100).toFixed(1)}%` : "-" },
    { col: 10, label: "日程調整中", value: totalAdjusting, sub: total ? `${(totalAdjusting/total*100).toFixed(1)}%` : "-" },
  ];
  cards.forEach(c => {
    const startCol = c.col;
    const cspan = 3;
    // ラベル行 (5行目)
    sh.getRange(5, startCol, 1, cspan).merge().setValue(c.label)
      .setBackground(BG_BOX).setFontColor(MUTED).setFontSize(11).setFontWeight("bold")
      .setFontFamily("Noto Sans JP").setHorizontalAlignment("center").setVerticalAlignment("middle");
    sh.setRowHeight(5, 32);
    // 数字行 (6行目)
    sh.getRange(6, startCol, 1, cspan).merge().setValue(c.value)
      .setBackground(BG_BOX).setFontColor(NAVY).setFontSize(28).setFontWeight("bold")
      .setFontFamily("Noto Sans JP").setHorizontalAlignment("center").setVerticalAlignment("middle");
    sh.setRowHeight(6, 56);
    // サブ行 (7行目)
    sh.getRange(7, startCol, 1, cspan).merge().setValue(c.sub)
      .setBackground(BG_BOX).setFontColor(MUTED).setFontSize(11)
      .setFontFamily("Noto Sans JP").setHorizontalAlignment("center").setVerticalAlignment("middle");
    sh.setRowHeight(7, 32);
    // 枠線
    sh.getRange(5, startCol, 3, cspan).setBorder(true, true, true, true, null, null, NAVY, SpreadsheetApp.BorderStyle.SOLID_MEDIUM);
  });

  // ── 2段目: 飛び・キャンセル・調整不可・重複 ──
  const cards2 = [
    { col: 1, label: "飛び", value: totalTobi, sub: total ? `${(totalTobi/total*100).toFixed(1)}%` : "-" },
    { col: 4, label: "キャンセル", value: totalCancel, sub: total ? `${(totalCancel/total*100).toFixed(1)}%` : "-" },
    { col: 7, label: "調整不可", value: totalFuteki, sub: total ? `${(totalFuteki/total*100).toFixed(1)}%` : "-" },
    { col: 10, label: "総LG数", value: lgs.length, sub: "アクティブ" },
  ];
  cards2.forEach(c => {
    const startCol = c.col, cspan = 3;
    sh.getRange(9, startCol, 1, cspan).merge().setValue(c.label)
      .setBackground(BG_BOX).setFontColor(MUTED).setFontSize(11).setFontWeight("bold")
      .setFontFamily("Noto Sans JP").setHorizontalAlignment("center").setVerticalAlignment("middle");
    sh.setRowHeight(9, 32);
    sh.getRange(10, startCol, 1, cspan).merge().setValue(c.value)
      .setBackground(BG_BOX).setFontColor(NAVY).setFontSize(28).setFontWeight("bold")
      .setFontFamily("Noto Sans JP").setHorizontalAlignment("center").setVerticalAlignment("middle");
    sh.setRowHeight(10, 56);
    sh.getRange(11, startCol, 1, cspan).merge().setValue(c.sub)
      .setBackground(BG_BOX).setFontColor(MUTED).setFontSize(11)
      .setFontFamily("Noto Sans JP").setHorizontalAlignment("center").setVerticalAlignment("middle");
    sh.setRowHeight(11, 32);
    sh.getRange(9, startCol, 3, cspan).setBorder(true, true, true, true, null, null, NAVY, SpreadsheetApp.BorderStyle.SOLID_MEDIUM);
  });

  // ── SNS別 ──
  section(13, "SNS別 内訳");
  const snsArr = Object.keys(snsCount).sort((a,b) => snsCount[b]-snsCount[a]);
  const snsRows = [["SNS種別", "件数", "比率"]];
  snsArr.forEach(s => snsRows.push([s, snsCount[s], total ? (snsCount[s]/total*100).toFixed(1)+"%" : "-"]));
  sh.getRange(14, 1, snsRows.length, 3).setValues(snsRows);
  sh.getRange(14, 1, 1, 3).setBackground(BG_SOFT).setFontWeight("bold").setFontSize(10)
    .setFontFamily("Noto Sans JP").setHorizontalAlignment("center");
  sh.getRange(14, 1, snsRows.length, 3).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);
  for (let r = 14; r < 14 + snsRows.length; r++) sh.setRowHeight(r, 32);

  // ── LG別 詳細表 (左: A〜I) ──
  const lgDetailStart = 14 + snsRows.length + 2;
  section(lgDetailStart, "LG別 詳細実績 (実施率順)", 9);
  const lgHeader = ["LGメンバー", "累計設定", "実施済", "実施予定", "調整中", "飛び", "キャンセル", "実施率", "飛び率"];
  const sortedLgs = lgs.slice().sort((a, b) => {
    const sa = stats[a.name], sb = stats[b.name];
    const ra = sa.total ? sa.jisshi / sa.total : 0;
    const rb = sb.total ? sb.jisshi / sb.total : 0;
    return rb - ra;
  });
  const lgRows = [lgHeader];
  sortedLgs.forEach(lg => {
    const s = stats[lg.name];
    const rate = s.total ? (s.jisshi / s.total * 100).toFixed(1) + "%" : "-";
    const trate = s.total ? (s.tobi / s.total * 100).toFixed(1) + "%" : "-";
    lgRows.push([lg.name, s.total, s.jisshi, s.jisshiYotei, s.adjusting, s.tobi, s.cancel, rate, trate]);
  });
  const lgTableStart = lgDetailStart + 1;
  sh.getRange(lgTableStart, 1, lgRows.length, 9).setValues(lgRows);
  sh.getRange(lgTableStart, 1, 1, 9).setBackground(BG_SOFT).setFontWeight("bold").setFontSize(10)
    .setFontFamily("Noto Sans JP").setHorizontalAlignment("center");
  sh.getRange(lgTableStart, 1, lgRows.length, 9).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);
  for (let r = lgTableStart; r < lgTableStart + lgRows.length; r++) sh.setRowHeight(r, 32);

  // ── v5.7.2: CA別 詳細表 (右: K〜S) — LG別表と並列配置 ──
  const CA_COL = 11; // K列
  // 列幅 (K〜S) を初回設定
  if (isFirstBuild) {
    [120, 70, 70, 70, 70, 60, 70, 70, 70].forEach((w, i) => sh.setColumnWidth(CA_COL + i, w));
  }
  // セクションヘッダ (LG別と同じ行・右側)
  sh.getRange(lgDetailStart, CA_COL, 1, 9).merge()
    .setValue("CA別 詳細実績 (担当面談ベース・実施率順)")
    .setFontColor(NAVY).setFontWeight("bold").setFontSize(14).setFontFamily("Noto Sans JP")
    .setHorizontalAlignment("left").setVerticalAlignment("middle");
  sh.getRange(lgDetailStart, CA_COL, 1, 9).setBorder(null, null, true, null, null, null, NAVY, SpreadsheetApp.BorderStyle.SOLID);
  const caHeader = ["CAメンバー", "担当総数", "実施済", "実施予定", "調整中", "飛び", "キャンセル", "実施率", "飛び率"];
  const sortedCas = cas.slice().sort((a, b) => {
    const ca = caStats[a], cb = caStats[b];
    const ra = ca.total ? ca.jisshi / ca.total : 0;
    const rb = cb.total ? cb.jisshi / cb.total : 0;
    return rb - ra;
  });
  const caRows = [caHeader];
  sortedCas.forEach(name => {
    const c = caStats[name];
    const rate  = c.total ? (c.jisshi / c.total * 100).toFixed(1) + "%" : "-";
    const trate = c.total ? (c.tobi   / c.total * 100).toFixed(1) + "%" : "-";
    caRows.push([name, c.total, c.jisshi, c.jisshiYotei, c.adjusting, c.tobi, c.cancel, rate, trate]);
  });
  // LG別テーブルと同じ開始行 (lgTableStart) に右側配置
  const caTableStart = lgTableStart;
  sh.getRange(caTableStart, CA_COL, caRows.length, 9).setValues(caRows);
  sh.getRange(caTableStart, CA_COL, 1, 9).setBackground(BG_SOFT).setFontWeight("bold").setFontSize(10)
    .setFontFamily("Noto Sans JP").setHorizontalAlignment("center");
  sh.getRange(caTableStart, CA_COL, caRows.length, 9).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);
  for (let r = caTableStart; r < caTableStart + caRows.length; r++) sh.setRowHeight(r, 32);

  sh.setTabColor("#233447");
  // v5.7.1: ビルドメタ保存 (差分判定用)
  try {
    PropertiesService.getScriptProperties().setProperty(propsKey, JSON.stringify({
      lastBuildTs: Date.now(), totalRows: totalRowsNow,
    }));
  } catch(_) {}
  return `LG実績ダッシュボード ${period} 構築完了`;
}

// v5.7+: ワークフロー図 を完全リセットしてフローチャート風に再構築
function buildWorkflowDiagram() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName("ワークフロー図");
  if (!sheet) return "no sheet";

  const NAVY = "#233447";
  const MUTED = "#64748B";
  const BORDER = "#E3E7EF";
  const BG_SOFT = "#F2F4F7";
  const BG_BOX = "#F8FAFC";
  const AMBER = "#D97706";  // 判断分岐用
  const BG_AMBER = "#FEF3E7";

  // ── 0. 完全リセット ──
  const maxR = sheet.getMaxRows();
  const maxC = sheet.getMaxColumns();
  sheet.getRange(1, 1, maxR, maxC).clearFormat();
  sheet.getRange(1, 1, maxR, maxC).breakApart();
  sheet.setHiddenGridlines(true);

  // ── 1. 値を書き直し（既存の内容を上書き） ──
  // 簡略化: ボックス位置をマップで管理
  // [startRow, endRow(inclusive 1-idx)] => 中身 [titleText, roleText]
  const boxes = [
    // メインフロー (列 C-E, 行 6-7 ペア, arrow行を挟む)
    { row: 6,  col: 3, text: "学生から日程受領", role: "LG", style: "normal" },
    { row: 9,  col: 3, text: "Slack ⚡ 面談登録 起動", role: "LG", style: "normal" },
    { row: 12, col: 3, text: "モーダル送信", role: "LG", style: "normal" },
    { row: 15, col: 3, text: "重複チェック", role: "判断", style: "diamond" },
    { row: 15, col: 7, text: "登録不成立 通知", role: "LG ephemeral", style: "branch" },
    { row: 18, col: 3, text: "CAカレンダー一斉照合", role: "SYS", style: "normal" },
    { row: 21, col: 3, text: "空きCAあり?", role: "判断", style: "diamond" },
    { row: 21, col: 7, text: "日程調整中", role: "@CA グループ通知", style: "branch" },
    { row: 24, col: 3, text: "確定処理", role: "Cal登録 / Meet / シート / LINE URL", style: "normal" },
    { row: 24, col: 7, text: "12h リマインド", role: "自動", style: "small" },
    { row: 27, col: 3, text: "確定スレッド投稿", role: "SYS", style: "normal" },
    { row: 27, col: 7, text: "24h リマインド", role: "自動", style: "small" },
    { row: 30, col: 3, text: "LG: 学生にLINEで連絡", role: "LG", style: "normal" },
    { row: 30, col: 7, text: "36h → 調整不可化", role: "自動", style: "small" },
    { row: 33, col: 3, text: "面談前: ✅ CA確認", role: "CA", style: "normal" },
    { row: 36, col: 3, text: "面談実施", role: "LG + CA", style: "normal" },
    { row: 39, col: 3, text: "実施済", role: "終着 (SF同期)", style: "filled" },
    // イレギュラー (列 A-C / E-G / I-K, 3パネル, 行 44-)
    { row: 44, col: 1, text: "事前キャンセル", role: "学生 → LG", style: "panel" },
    { row: 44, col: 5, text: "リスケ要望", role: "学生 → LG", style: "panel" },
    { row: 44, col: 9, text: "無断欠席 (飛び)", role: "面談時刻に来ない", style: "panel" },
    { row: 47, col: 1, text: "LG: ❌ キャンセル", role: "LG", style: "normal-narrow" },
    { row: 47, col: 5, text: "LG: 🔁 リスケ依頼", role: "LG", style: "normal-narrow" },
    { row: 47, col: 9, text: "LG: 🚫 飛び報告", role: "LG", style: "normal-narrow" },
    { row: 50, col: 1, text: "カレンダー予定削除", role: "自動", style: "normal-narrow" },
    { row: 50, col: 5, text: "旧予定削除 + 新候補入力", role: "自動 + LG", style: "normal-narrow" },
    { row: 50, col: 9, text: "カレンダー注記 + 飛びCh通知", role: "自動", style: "normal-narrow" },
    { row: 53, col: 1, text: "フェーズ → キャンセル", role: "終着", style: "filled-narrow" },
    { row: 53, col: 5, text: "確定 or 日程調整中", role: "再マッチング結果", style: "normal-narrow" },
    { row: 53, col: 9, text: "フェーズ → 飛び", role: "終着", style: "filled-narrow" },
  ];

  // 値書き込み（タイトル/サブ/セクション）
  sheet.getRange(1, 1).setValue("ワークフロー図");
  sheet.getRange(2, 1).setValue("面談連携システム v5.7 / 登録 → 確定 → 実施 → 各種報告");
  sheet.getRange(4, 1).setValue("メインフロー — 登録から確定まで");
  sheet.getRange(42, 1).setValue("イレギュラーフロー — 各種報告");
  sheet.getRange(57, 1).setValue("ボタン早見表");

  // 全セルクリア (フローエリア部分)
  sheet.getRange(5, 1, 50, 13).clearContent();

  // ── 2. 列幅 ──
  // A B narrow (panel left margin), C-E box, F arrow, G-I right branch, J arrow, K-M misc
  const widths = [40, 110, 100, 100, 100, 40, 110, 110, 110, 40, 110, 110, 110];
  widths.forEach((w, i) => sheet.setColumnWidth(i + 1, w));

  // ── 3. タイトル / サブタイトル / セクション ──
  sheet.getRange(1, 1, 1, 13).merge()
    .setBackground(NAVY).setFontColor("#FFFFFF").setFontWeight("bold").setFontSize(20)
    .setFontFamily("Noto Sans JP").setHorizontalAlignment("left").setVerticalAlignment("middle");
  sheet.setRowHeight(1, 60);

  sheet.getRange(2, 1, 1, 13).merge()
    .setBackground(BG_SOFT).setFontColor(MUTED).setFontSize(10)
    .setFontFamily("Noto Sans JP").setHorizontalAlignment("left").setVerticalAlignment("middle");
  sheet.setRowHeight(2, 28);
  sheet.getRange(2, 1, 1, 13).setBorder(
    null, null, true, null, null, null,
    NAVY, SpreadsheetApp.BorderStyle.SOLID_THICK
  );

  [4, 42, 57].forEach(r => {
    sheet.getRange(r, 1, 1, 13).merge()
      .setFontColor(NAVY).setFontWeight("bold").setFontSize(14)
      .setFontFamily("Noto Sans JP").setHorizontalAlignment("left").setVerticalAlignment("middle");
    sheet.setRowHeight(r, 40);
    sheet.getRange(r, 1, 1, 13).setBorder(
      null, null, true, null, null, null,
      NAVY, SpreadsheetApp.BorderStyle.SOLID
    );
  });

  // ── 4. 各ボックス描画 ──
  const drawBox = (b) => {
    let cspan = 3;  // デフォルト 3列幅
    let bg = BG_BOX, fg = NAVY, borderStyle = SpreadsheetApp.BorderStyle.SOLID_MEDIUM, borderColor = NAVY;
    let titleFs = 11, roleFs = 9;
    if (b.style === "diamond") { borderColor = AMBER; bg = BG_AMBER; }
    else if (b.style === "branch") { borderColor = NAVY; }
    else if (b.style === "small") { titleFs = 10; roleFs = 8; }
    else if (b.style === "filled") { bg = NAVY; fg = "#FFFFFF"; titleFs = 13; borderStyle = SpreadsheetApp.BorderStyle.SOLID_THICK; }
    else if (b.style === "panel") { bg = NAVY; fg = "#FFFFFF"; titleFs = 12; borderStyle = SpreadsheetApp.BorderStyle.SOLID_THICK; cspan = 3; }
    else if (b.style === "normal-narrow") { cspan = 3; }
    else if (b.style === "filled-narrow") { bg = NAVY; fg = "#FFFFFF"; cspan = 3; borderStyle = SpreadsheetApp.BorderStyle.SOLID_THICK; }

    const titleR = b.row, roleR = b.row + 1;
    const c = b.col;
    sheet.getRange(titleR, c, 1, cspan).merge().setValue(b.text)
      .setBackground(bg).setFontColor(fg).setFontWeight("bold").setFontSize(titleFs)
      .setFontFamily("Noto Sans JP").setHorizontalAlignment("center").setVerticalAlignment("middle");
    sheet.setRowHeight(titleR, 34);
    sheet.getRange(roleR, c, 1, cspan).merge().setValue(b.role)
      .setBackground(bg).setFontColor(b.style === "filled" || b.style === "panel" || b.style === "filled-narrow" ? "#E2E8F0" : MUTED)
      .setFontSize(roleFs).setFontFamily("Noto Sans JP")
      .setHorizontalAlignment("center").setVerticalAlignment("middle");
    sheet.setRowHeight(roleR, 22);
    sheet.getRange(titleR, c, 2, cspan).setBorder(true, true, true, true, null, null, borderColor, borderStyle);
  };
  boxes.forEach(drawBox);

  // ── 5. 矢印 (▼) を中央列に ──
  const arrowRows = [8, 11, 14, 17, 20, 23, 26, 29, 32, 35, 38];
  arrowRows.forEach(r => {
    sheet.getRange(r, 4).setValue("▼")
      .setFontSize(18).setFontColor(NAVY).setFontWeight("bold")
      .setHorizontalAlignment("center").setVerticalAlignment("middle");
    sheet.setRowHeight(r, 24);
  });
  // イレギュラー 縦矢印
  [46, 49, 52, 55].forEach(r => {
    [1, 5, 9].forEach(c => {
      sheet.getRange(r, c, 1, 3).merge().setValue("▼")
        .setFontSize(16).setFontColor(NAVY).setFontWeight("bold")
        .setHorizontalAlignment("center").setVerticalAlignment("middle");
    });
    sheet.setRowHeight(r, 22);
  });

  // 分岐の右矢印 (15, 21の右側)
  [16, 22].forEach(r => {
    sheet.getRange(r, 6).setValue("→")
      .setFontSize(16).setFontColor(NAVY).setFontWeight("bold")
      .setHorizontalAlignment("center").setVerticalAlignment("middle");
  });

  // ── 6. ボタン早見表 (行 58-60) ──
  const btn = [
    ["フェーズ", "🔁 (LG)", "❌ (LG)", "🚫 (LG)", "⚠️ (共通)", "CA"],
    ["実施予定", "🔁 リスケ依頼", "❌ キャンセル", "🚫 飛び報告", "⚠️ 重複報告", "✅ CA確認"],
    ["日程調整中", "🔁 日程再回収", "❌ キャンセル", "🚫 飛び報告", "⚠️ 重複報告", "📅 日程入力"],
  ];
  sheet.getRange(58, 1, 3, 6).setValues(btn);
  sheet.getRange(58, 1, 1, 6).setBackground(NAVY).setFontColor("#FFFFFF").setFontWeight("bold")
    .setFontFamily("Noto Sans JP").setFontSize(10).setHorizontalAlignment("center");
  sheet.getRange(59, 1, 2, 6).setBackground(BG_BOX).setFontFamily("Noto Sans JP").setFontSize(10)
    .setHorizontalAlignment("center");
  for (let r = 58; r <= 60; r++) sheet.setRowHeight(r, 34);
  sheet.getRange(58, 1, 3, 6).setBorder(true, true, true, true, true, true, BORDER, SpreadsheetApp.BorderStyle.SOLID);

  return "ワークフロー図 構築完了";
}

// v5.7+: 連携メイン_NN卒 のヘッダー行を復元
function restoreGradeSheetHeaders() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const log = [];
  for (const sheet of ss.getSheets()) {
    if (!/^連携メイン_\d+卒$/.test(sheet.getName())) continue;
    try {
      // row 1 のマージを解除
      sheet.getRange(1, 1, 1, sheet.getMaxColumns()).breakApart();
      // ヘッダー再書込み
      sheet.getRange(1, 1, 1, SHEET_HEADERS.length).setValues([SHEET_HEADERS]);
      log.push(`${sheet.getName()}: ヘッダー復元`);
    } catch(e) { log.push(`${sheet.getName()}: ${e}`); }
  }
  Logger.log("=== restoreGradeSheetHeaders ===");
  log.forEach(l => Logger.log(l));
  return log;
}

// v5.7+: バクラク準拠デザイン (Tokumori Dashboard v4 SS版)
//   ヘッダー帯=ネイビー#233447 / 本文=白+1px下線 / 列幅=320px / 行高=32px
function applyBakurakuDesign() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const NAVY = "#233447";
  const TEXT = "#1A2332";
  const MUTED = "#64748B";
  const BORDER = "#E3E7EF";
  const BG_SOFT = "#F2F4F7";
  // 「データ系」= 列ヘッダーが行1に並ぶシート。タイトルマージは厳禁。
  const DATA_TABS = new Set(["CAリスト", "LGリスト", "設定", "空き枠カレンダー", "実績管理", "LG実績ダッシュボード"]);
  const isGradeSheet = (name) => /^連携メイン_\d+卒$/.test(name);
  // 「ドキュメント系」= 行1に「タイトル文」が入るシート (マニュアル/仕様書/フロー)
  const DOC_TABS = new Set(["マニュアル_LG向け", "マニュアル_CA向け", "システム仕様書", "業務フロー_新旧比較", "ワークフロー図"]);

  const log = [];
  for (const sheet of ss.getSheets()) {
    const name = sheet.getName();
    try {
      const maxR = sheet.getMaxRows();
      const maxC = sheet.getMaxColumns();
      const lastRow = Math.max(sheet.getLastRow(), 1);
      const lastCol = Math.max(sheet.getLastColumn(), 1);
      sheet.setHiddenGridlines(true);

      if (DOC_TABS.has(name)) {
        // ----- ドキュメント系 -----
        sheet.getRange(1, 1, maxR, maxC).clearFormat();
        sheet.getRange(1, 1, maxR, maxC).breakApart();
        sheet.getRange(1, 1, maxR, maxC)
          .setFontFamily("Noto Sans JP").setFontSize(11).setFontColor(TEXT);

        // タイトル
        sheet.getRange(1, 1, 1, lastCol)
          .setBackground(NAVY).setFontColor("#FFFFFF").setFontWeight("bold").setFontSize(20)
          .setHorizontalAlignment("left").setVerticalAlignment("middle");
        sheet.setRowHeight(1, 60);
        if (lastCol >= 2) sheet.getRange(1, 1, 1, lastCol).merge();
        // サブ
        sheet.getRange(2, 1, 1, lastCol)
          .setBackground(BG_SOFT).setFontColor(MUTED).setFontSize(10)
          .setHorizontalAlignment("left").setVerticalAlignment("middle");
        sheet.setRowHeight(2, 28);
        if (lastCol >= 2) sheet.getRange(2, 1, 1, lastCol).merge();
        sheet.getRange(2, 1, 1, lastCol).setBorder(
          null, null, true, null, null, null,
          NAVY, SpreadsheetApp.BorderStyle.SOLID_THICK
        );

        // セクション見出し
        const colA = sheet.getRange(1, 1, lastRow, 1).getValues();
        const SECTION_KW = /^(■|【|〈|はじめに|概要|用語集|事前準備|あなたの|重要ルール|1日の流れ|STEP\s*\d|候補時間|登録結果|ボタン操作|リマインド|FAQ|トラブル|旧フロー|凡例|関連リソース|アーキテクチャ|主要関数|シート:|モーダル仕様|フェーズ|CA自動マッチング|ビジネスアワー|SNS種別|管理者関数|トリガー一覧|メインフロー|イレギュラー|ボタン配置|フェーズ遷移|全体サマリー|LG別|並列比較|自動化された|KPI比較|主要な改善|ハマりやすい|新フロー|旧フロー \()/;
        for (let r = 2; r < colA.length; r++) {
          const v = String(colA[r][0] || "").trim();
          if (!v || !SECTION_KW.test(v)) continue;
          const rowNum = r + 1;
          sheet.getRange(rowNum, 1, 1, lastCol)
            .setBackground("#FFFFFF").setFontColor(NAVY).setFontSize(14).setFontWeight("bold")
            .setHorizontalAlignment("left").setVerticalAlignment("middle");
          sheet.setRowHeight(rowNum, 44);
          sheet.getRange(rowNum, 1, 1, lastCol).setBorder(
            null, null, true, null, null, null,
            NAVY, SpreadsheetApp.BorderStyle.SOLID
          );
          if (lastCol >= 2) sheet.getRange(rowNum, 1, 1, lastCol).merge();
        }

        // 本文
        if (lastRow >= 3) {
          sheet.getRange(3, 1, lastRow - 2, lastCol)
            .setBackground("#FFFFFF").setVerticalAlignment("middle").setWrap(false).setFontSize(11);
          for (let r = 3; r <= lastRow; r++) sheet.setRowHeight(r, 32);
          sheet.getRange(3, 1, lastRow - 2, lastCol).setBorder(
            null, null, null, null, null, true,
            BORDER, SpreadsheetApp.BorderStyle.SOLID
          );
        }

      } else if (isGradeSheet(name) || DATA_TABS.has(name)) {
        // ----- データ系 (連携メイン/CAリスト/LGリスト/設定/ダッシュボード/空き枠/実績) -----
        // マージは絶対にしない。ヘッダー行(row 1) はそのまま。
        sheet.getRange(1, 1, maxR, maxC).setFontFamily("Noto Sans JP").setFontColor(TEXT);
        // ヘッダー強調
        sheet.getRange(1, 1, 1, lastCol)
          .setBackground(NAVY).setFontColor("#FFFFFF").setFontWeight("bold")
          .setFontSize(11).setHorizontalAlignment("center").setVerticalAlignment("middle");
        sheet.setRowHeight(1, 40);
        try { sheet.setFrozenRows(1); } catch(_) {}
        // データ範囲: 罫線=行間細線のみ
        if (lastRow >= 2 && lastCol >= 1) {
          sheet.getRange(2, 1, lastRow - 1, lastCol)
            .setFontSize(10).setVerticalAlignment("middle").setWrap(false);
          for (let r = 2; r <= lastRow; r++) sheet.setRowHeight(r, 32);
          sheet.getRange(2, 1, lastRow - 1, lastCol).setBorder(
            null, null, null, null, null, true,
            BORDER, SpreadsheetApp.BorderStyle.SOLID
          );
        }
        // 連携メインは maxRow まで縦罫線を引く (新規行追加先にも線が乗るよう)
        if (isGradeSheet(name)) {
          sheet.getRange(1, 1, maxR, lastCol).setBorder(
            null, null, null, null, true, null,
            BORDER, SpreadsheetApp.BorderStyle.SOLID
          );
        }
      }

      log.push(`${name}: OK`);
    } catch(e) {
      log.push(`${name}: ${String(e).slice(0,80)}`);
    }
  }
  Logger.log("=== applyBakurakuDesign ===");
  log.forEach(l => Logger.log(l));
  return log;
}

// v5.7+ legacy alias (互換)
function applyMinimalDesign() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const NAVY = "#0F172A";          // ほぼ黒のネイビー
  const TEXT_PRIMARY = "#0F172A";
  const TEXT_MUTED = "#64748B";    // ミューテッドグレー
  const BORDER = "#E2E8F0";        // 薄ライン
  const HEADER_BG = "#F8FAFC";     // ほぼ白の背景
  const log = [];
  // チェックボックス等の機能を持つ連携メインは clearFormats を避ける
  const PROTECTED = (name) => /^連携メイン_\d+卒$/.test(name) || name === "CAリスト" || name === "LGリスト";
  for (const sheet of ss.getSheets()) {
    const name = sheet.getName();
    try {
      const lastRow = Math.max(sheet.getLastRow(), 1);
      const lastCol = Math.max(sheet.getLastColumn(), 1);
      sheet.setHiddenGridlines(true);

      // 0. ドキュメント系は古い書式を完全リセット
      if (!PROTECTED(name)) {
        sheet.getRange(1, 1, sheet.getMaxRows(), sheet.getMaxColumns()).clearFormat();
        // マージ解除
        sheet.getRange(1, 1, sheet.getMaxRows(), sheet.getMaxColumns()).breakApart();
      }

      // 1. 全罫線をクリア
      sheet.getRange(1, 1, sheet.getMaxRows(), sheet.getMaxColumns()).setBorder(
        false, false, false, false, false, false, null, SpreadsheetApp.BorderStyle.SOLID
      );
      sheet.getRange(1, 1, sheet.getMaxRows(), sheet.getMaxColumns()).setBackground(null);

      // 2. 全セル基本フォント + 色
      sheet.getRange(1, 1, sheet.getMaxRows(), sheet.getMaxColumns())
        .setFontFamily("Noto Sans JP")
        .setFontSize(10)
        .setFontColor(TEXT_PRIMARY)
        .setFontWeight("normal");

      // 3. タイトル行 (row 1): 太字大きめ・左寄せ・行高 56
      if (lastCol >= 1) {
        sheet.getRange(1, 1, 1, lastCol)
          .setFontSize(20).setFontWeight("bold").setFontColor(NAVY)
          .setHorizontalAlignment("left").setVerticalAlignment("middle");
        sheet.setRowHeight(1, 56);
      }
      // 4. サブタイトル行 (row 2): ミューテッド
      if (lastCol >= 1) {
        sheet.getRange(2, 1, 1, lastCol)
          .setFontSize(10).setFontColor(TEXT_MUTED).setFontWeight("normal");
        sheet.setRowHeight(2, 24);
        // タイトル下にアクセントライン (row 2 下)
        sheet.getRange(2, 1, 1, lastCol).setBorder(
          null, null, true, null, null, null, NAVY, SpreadsheetApp.BorderStyle.SOLID_THICK
        );
      }

      // 5. 既存の "■" や "STEP" や "セクション名"を含む行を H2 化（太字+大きめ+下にライン）
      const colA = sheet.getRange(1, 1, lastRow, 1).getValues();
      for (let r = 3; r < colA.length; r++) {
        const v = String(colA[r][0] || "").trim();
        if (!v) continue;
        // セクション見出し判定: ■で始まる / 「概要」「用語集」「STEP」など特定キーワード
        const isSection = /^■/.test(v) || /^[【〈]/.test(v) ||
          /^(はじめに|概要|用語集|事前準備|あなたの|重要ルール|1日の流れ|STEP\s*\d|候補時間|登録結果|ボタン操作|リマインド|FAQ|トラブル|旧フロー|凡例|関連リソース|アーキテクチャ|主要関数|シート|モーダル|フェーズ|CA自動マッチング|ビジネスアワー|SNS種別|管理者関数|トリガー|メインフロー|イレギュラー|ボタン配置|フェーズ遷移|全体サマリー|LG別|並列比較|自動化された|KPI比較|主要な改善|ハマりやすい)/.test(v);
        if (isSection) {
          sheet.getRange(r + 1, 1, 1, lastCol)
            .setFontSize(14).setFontWeight("bold").setFontColor(NAVY)
            .setHorizontalAlignment("left").setVerticalAlignment("middle");
          sheet.setRowHeight(r + 1, 40);
          // セクション見出し下に細いライン
          sheet.getRange(r + 1, 1, 1, lastCol).setBorder(
            null, null, true, null, null, null, NAVY, SpreadsheetApp.BorderStyle.SOLID
          );
        }
      }

      // 6. 各行のセル内: 中央寄せ・改行禁止 (列幅で対応)・行高 32
      if (lastRow >= 3 && lastCol >= 1) {
        sheet.getRange(3, 1, lastRow - 2, lastCol)
          .setVerticalAlignment("middle")
          .setWrap(false);  // セル内改行を禁止 (列幅で十分に幅を取る)
        // 行高を一括 32px に
        for (let r = 3; r <= lastRow; r++) sheet.setRowHeight(r, 32);
      }

      log.push(`${name}: OK`);
    } catch(e) {
      log.push(`${name}: ${String(e).slice(0,80)}`);
    }
  }
  Logger.log("=== applyMinimalDesign ===");
  log.forEach(l => Logger.log(l));
  return log;
}

// v5.7+: 全タブ名と行数を一覧化（不要タブ削除用の確認）
function listAllTabs() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const result = ss.getSheets().map(s => ({
    name: s.getName(),
    lastRow: s.getLastRow(),
    lastCol: s.getLastColumn(),
  }));
  Logger.log("=== 全タブ一覧 ===");
  result.forEach(r => Logger.log(`${r.name} (rows=${r.lastRow}, cols=${r.lastCol})`));
  return result;
}

// v5.7+: 不要タブを一括削除（明示リスト指定）
function deleteUnusedTabs() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  // 削除対象タブ名（保護タブは絶対に消さない）
  const toDelete = [
    "📖 運用マニュアル",       // 旧版 → 新マニュアル_LG/CA向けに置き換え
    "🔄 全体フロー図",         // 旧版 → 業務フロー_新旧比較に置き換え
    "🛠 Slack WF 仕様書",       // Slack Workflow廃止済み
    "連携メイン_2026-05",     // 旧初期タブ（卒年シートが本流）
    "_debug_ca_access",       // 都度再生成
    "_prod_readiness",        // 都度再生成
  ];
  const log = [];
  for (const name of toDelete) {
    const sh = ss.getSheetByName(name);
    if (sh) {
      ss.deleteSheet(sh);
      log.push(`${name} 削除`);
    } else {
      log.push(`${name} 存在しない（スキップ）`);
    }
  }
  Logger.log("=== deleteUnusedTabs 完了 ===");
  log.forEach(l => Logger.log("  " + l));
  return log;
}

// v5.7+: 既存行の連携番号(A列)に4桁ゼロ埋め書式を一括適用（一度だけ実行）
function applyRowNoFormatAllSheets() {
  const sheets = getAllGradeSheets();
  for (const sh of sheets) {
    const lastRow = sh.getLastRow();
    if (lastRow > 1) sh.getRange(2, 1, lastRow - 1, 1).setNumberFormat("0000");
  }
  Logger.log(`連携番号書式適用完了: ${sheets.length}シート`);
}

// rowNo から該当行を全卒年シート横断で検索
function findRowByNo(rowNo) {
  const target = parseInt(rowNo, 10);
  if (isNaN(target)) return null;
  // v5.7.1: 余剰列読込を避けて高速化 (A〜AD のみ)
  for (const sheet of getAllGradeSheets()) {
    const lastRow = sheet.getLastRow();
    if (lastRow < 2) continue;
    const data = sheet.getRange(1, 1, lastRow, GRADE_SHEET_COLS).getValues();
    for (let i = 1; i < data.length; i++) {
      if (parseInt(data[i][0], 10) === target) {
        return { sheet, rowIdx: i, data, sheetName: sheet.getName() };
      }
    }
  }
  return null;
}

// 旧タブのクリーンアップ（1回だけ手動実行）
function cleanupOldTabs() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  ["個人ダッシュボード（サンプル）", "Slackテンプレ", "使い方", "連携メイン_2026-04", "連携メイン_2026-05"]
    .forEach(name => {
      const s = ss.getSheetByName(name);
      if (s) {
        ss.deleteSheet(s);
        Logger.log(`[cleanup] 削除: ${name}`);
      }
    });
}

// ─────────────────────────────────────────
// LG実績ダッシュボード（v5.0）
//   - 全卒年シートを横断してLG別に累計KPIを集計
//   - 列: LGメンバー / 累計設定 / 累計実施 / 累計飛び / 累計リスケ / 実施率 / 飛び率
//        + 卒年別（XX卒設定 / XX卒実施）
// ─────────────────────────────────────────

// v5.7+: LG実績ダッシュボード - 多角的分析対応
function updateLGDashboard() {
  // v5.7+: 全期間/月次/週次/日次 を一括更新
  try { return buildAllLGDashboards(); } catch(e) { Logger.log("[updateLGDashboard] " + e); }
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    let sh = ss.getSheetByName(DASHBOARD_SHEET);
    if (!sh) sh = ss.insertSheet(DASHBOARD_SHEET);

    const lgs = _lgListRows()
      .filter(r => r[0] && String(r[4] || "").trim() === "アクティブ")
      .map(r => ({ name: String(r[0]).trim(), uid: String(r[2] || "").trim() }));

    const gradeSheets = getAllGradeSheets();
    const stats = {};
    lgs.forEach(lg => {
      const obj = { total: 0, jisshi: 0, jisshiYotei: 0, tobi: 0, risuke: 0, cancel: 0, futeki: 0, dup: 0, adjusting: 0, byGrade: {}, bySns: {}, lastReg: null };
      stats[lg.name] = obj;
      if (lg.uid) stats[lg.uid] = obj;
    });

    let totalSet = 0, totalJisshi = 0, totalTobi = 0, totalCancel = 0, totalFuteki = 0, totalAdjusting = 0;
    const snsCounter = {};
    const phaseCounter = {};

    gradeSheets.forEach(sheet => {
      const grade = sheet.getName().replace("連携メイン_", "");
      const data = sheet.getDataRange().getValues();
      for (let i = 1; i < data.length; i++) {
        if (!data[i][0]) continue;
        const lgKey = String(data[i][2] || "").trim();
        const phase = String(data[i][21] || "").trim();
        const sns   = String(data[i][6] || "").trim() || "未指定";
        const regDate = data[i][1];

        totalSet++;
        snsCounter[sns] = (snsCounter[sns] || 0) + 1;
        phaseCounter[phase] = (phaseCounter[phase] || 0) + 1;
        if (phase === "実施済") totalJisshi++;
        else if (phase === "飛び") totalTobi++;
        else if (phase === "キャンセル") totalCancel++;
        else if (phase === "調整不可") totalFuteki++;
        else if (phase === "日程調整中") totalAdjusting++;

        if (!stats[lgKey]) continue;
        const s = stats[lgKey];
        s.total++;
        if (!s.byGrade[grade]) s.byGrade[grade] = { set: 0, jis: 0 };
        s.byGrade[grade].set++;
        s.bySns[sns] = (s.bySns[sns] || 0) + 1;
        if (phase === "実施済") { s.jisshi++; s.byGrade[grade].jis++; }
        else if (phase === "実施予定") s.jisshiYotei++;
        else if (phase === "飛び")       s.tobi++;
        else if (phase === "リスケ")     s.risuke++;
        else if (phase === "キャンセル") s.cancel++;
        else if (phase === "調整不可")   s.futeki++;
        else if (phase === "重複（要整理）") s.dup++;
        else if (phase === "日程調整中") s.adjusting++;
        if (regDate instanceof Date && (!s.lastReg || regDate > s.lastReg)) s.lastReg = regDate;
      }
    });

    sh.clearContents();
    sh.clearFormats();

    const out = [];
    // タイトル
    out.push(["LG実績ダッシュボード", "", "", "", "", "", "", ""]);
    out.push([`自動更新 / 最終: ${formatDatetime(new Date())} / 5分毎に更新`, "", "", "", "", "", "", ""]);
    out.push(["", "", "", "", "", "", "", ""]);
    // 全体サマリー
    out.push(["全体サマリー", "", "", "", "", "", "", ""]);
    out.push(["指標", "値", "比率", "", "指標", "値", "比率", ""]);
    out.push(["累計設定数", totalSet, "100%", "", "実施済", totalJisshi, totalSet ? (totalJisshi/totalSet*100).toFixed(1)+"%" : "-", ""]);
    out.push(["日程調整中", totalAdjusting, totalSet ? (totalAdjusting/totalSet*100).toFixed(1)+"%" : "-", "", "飛び", totalTobi, totalSet ? (totalTobi/totalSet*100).toFixed(1)+"%" : "-", ""]);
    out.push(["キャンセル", totalCancel, totalSet ? (totalCancel/totalSet*100).toFixed(1)+"%" : "-", "", "調整不可", totalFuteki, totalSet ? (totalFuteki/totalSet*100).toFixed(1)+"%" : "-", ""]);
    out.push(["", "", "", "", "", "", "", ""]);
    // SNS別
    out.push(["SNS種別 集計", "", "", "", "", "", "", ""]);
    out.push(["SNS種別", "件数", "比率", "", "", "", "", ""]);
    Object.keys(snsCounter).sort((a,b) => snsCounter[b]-snsCounter[a]).forEach(s => {
      out.push([s, snsCounter[s], totalSet ? (snsCounter[s]/totalSet*100).toFixed(1)+"%" : "-", "", "", "", "", ""]);
    });
    out.push(["", "", "", "", "", "", "", ""]);
    // フェーズ別
    out.push(["フェーズ別 分布", "", "", "", "", "", "", ""]);
    out.push(["フェーズ", "件数", "比率", "", "", "", "", ""]);
    Object.keys(phaseCounter).sort((a,b) => phaseCounter[b]-phaseCounter[a]).forEach(p => {
      out.push([p || "(未設定)", phaseCounter[p], totalSet ? (phaseCounter[p]/totalSet*100).toFixed(1)+"%" : "-", "", "", "", "", ""]);
    });
    out.push(["", "", "", "", "", "", "", ""]);

    // LG別詳細
    const allGrades = [...new Set(gradeSheets.map(s => s.getName().replace("連携メイン_", "")))].sort();
    const lgHeader = ["LGメンバー", "累計設定", "実施済", "実施予定", "調整中", "飛び", "キャンセル", "実施率"];
    out.push(["LG別 概要", "", "", "", "", "", "", ""]);
    out.push(lgHeader);
    lgs.forEach(lg => {
      const s = stats[lg.name];
      const rate = s.total ? (s.jisshi / s.total * 100).toFixed(1) + "%" : "-";
      out.push([lg.name, s.total, s.jisshi, s.jisshiYotei, s.adjusting, s.tobi, s.cancel, rate]);
    });
    out.push(["", "", "", "", "", "", "", ""]);
    out.push(["", "", "", "", "", "", "", ""]);
    // LG個別詳細 (卒年×フェーズ クロス)
    out.push(["LG別 個別詳細 (卒年内訳/SNS内訳/各種比率)", "", "", "", "", "", "", ""]);
    const allSns = [...new Set(Object.keys(snsCounter))];
    const detailHeader = ["LGメンバー", "総数"];
    allGrades.forEach(g => detailHeader.push(g));
    detailHeader.push("...");
    out.push(detailHeader.concat(new Array(8 - detailHeader.length).fill("")).slice(0, 8));
    lgs.forEach(lg => {
      const s = stats[lg.name];
      const row = [lg.name, s.total];
      allGrades.forEach(g => row.push((s.byGrade[g] && s.byGrade[g].set) || 0));
      while (row.length < 8) row.push("");
      out.push(row);
    });
    out.push(["", "", "", "", "", "", "", ""]);
    out.push(["", "", "", "", "", "", "", ""]);
    // LG別 各種比率
    out.push(["LG別 各種比率 (低い順に確認)", "", "", "", "", "", "", ""]);
    out.push(["LGメンバー", "総数", "実施率", "飛び率", "キャンセル率", "調整中率", "最終登録日", ""]);
    const sortedLgs = lgs.slice().sort((a, b) => {
      const sa = stats[a.name], sb = stats[b.name];
      const ra = sa.total ? sa.jisshi / sa.total : 0;
      const rb = sb.total ? sb.jisshi / sb.total : 0;
      return rb - ra;
    });
    sortedLgs.forEach(lg => {
      const s = stats[lg.name];
      const last = s.lastReg ? formatDate(s.lastReg) : "-";
      const fmt = (n, d) => d ? (n / d * 100).toFixed(1) + "%" : "-";
      out.push([
        lg.name, s.total,
        fmt(s.jisshi, s.total),
        fmt(s.tobi, s.total),
        fmt(s.cancel, s.total),
        fmt(s.adjusting, s.total),
        last,
        "",
      ]);
    });

    sh.getRange(1, 1, out.length, 8).setValues(out);

    // タイトル
    sh.getRange(1, 1, 1, 8).merge().setBackground("#1A2845").setFontColor("#FFFFFF").setFontWeight("bold").setFontSize(18).setFontFamily("Noto Sans JP").setVerticalAlignment("middle").setHorizontalAlignment("left");
    sh.setRowHeight(1, 48);
    sh.getRange(2, 1, 1, 8).merge().setBackground("#1A2845").setFontColor("#C2D938").setFontFamily("Noto Sans JP").setFontSize(10);

    // セクション見出し関数
    const lime = (row) => sh.getRange(row, 1, 1, 8).merge().setBackground("#C2D938").setFontColor("#1A2845").setFontWeight("bold").setFontFamily("Noto Sans JP").setFontSize(12);
    lime(4);   // 全体サマリー
    const snsRow = 4 + 1 + 3 + 2; // header + 3 KPI + 2blank = row 10
    lime(10);  // SNS別
    const snsHeaderRow = 11;
    sh.getRange(snsHeaderRow, 1, 1, 3).setBackground("#ECEFF1").setFontWeight("bold").setFontFamily("Noto Sans JP");
    const snsCount = Object.keys(snsCounter).length;
    const phaseSectionRow = snsHeaderRow + snsCount + 2; // sns data + 2 blank lines = phase title
    lime(phaseSectionRow);
    const phaseHeaderRow = phaseSectionRow + 1;
    sh.getRange(phaseHeaderRow, 1, 1, 3).setBackground("#ECEFF1").setFontWeight("bold").setFontFamily("Noto Sans JP");
    const phaseCount = Object.keys(phaseCounter).length;
    const lgSectionRow = phaseHeaderRow + phaseCount + 2;
    lime(lgSectionRow);
    const lgHeaderRow = lgSectionRow + 1;
    sh.getRange(lgHeaderRow, 1, 1, 8).setBackground("#ECEFF1").setFontWeight("bold").setFontFamily("Noto Sans JP");

    // 全体サマリーKPI ヘッダー(row 5)を強調
    sh.getRange(5, 1, 1, 8).setBackground("#ECEFF1").setFontWeight("bold").setFontFamily("Noto Sans JP");

    // 列幅
    sh.setColumnWidth(1, 220);
    sh.setColumnWidth(2, 100);
    sh.setColumnWidth(3, 100);
    sh.setColumnWidth(4, 30);
    sh.setColumnWidth(5, 130);
    sh.setColumnWidth(6, 80);
    sh.setColumnWidth(7, 100);
    sh.setColumnWidth(8, 100);

    sh.setHiddenGridlines(true);
    sh.setFrozenRows(2);
    sh.getRange(1, 1, out.length, 8).setFontFamily("Noto Sans JP");

    Logger.log(`[LGDash] 更新完了: ${lgs.length}名 × ${allGrades.length}卒年`);
  } catch (e) {
    Logger.log(`[LGDash] ERROR: ${e}\nstack: ${e.stack}`);
  }
}

// ═════════════════════════════════════════════════════════
// v5.4: Block Kit モーダル統合
// ═════════════════════════════════════════════════════════

// Slack views.open API 呼び出し
function _slackViewsOpen(triggerId, view, userIdForErrDM) {
  // v5.7+: Script Properties を最優先（シートB2が空でも動く）
  let token = PropertiesService.getScriptProperties().getProperty("SLACK_BOT_TOKEN");
  if (!token) token = getConfig()["Slack Bot Token"];
  const res = UrlFetchApp.fetch("https://slack.com/api/views.open", {
    method: "post", contentType: "application/json",
    headers: { Authorization: "Bearer " + token },
    payload: JSON.stringify({ trigger_id: triggerId, view }),
    muteHttpExceptions: true,
  });
  const result = JSON.parse(res.getContentText());
  if (!result.ok) {
    Logger.log(`[views.open] ERROR: ${result.error} ${JSON.stringify(result.response_metadata || {})}`);
    // v5.7+: モーダルが開かなかった理由をユーザーにDMで即伝える
    if (userIdForErrDM) {
      try {
        sendSlackMessage(userIdForErrDM, `⚠️ モーダルを開けませんでした\nエラー: \`${result.error}\`\n詳細: ${JSON.stringify(result.response_metadata || {}).slice(0, 300)}\n\n対応の手がかり:\n- \`invalid_trigger_id\` / \`expired_trigger_id\` → GAS応答が遅い。再度ショートカット押下\n- \`missing_scope\` → Slack App に該当スコープ追加要\n- それ以外 → 開発担当へこの全文を共有`, null, null);
      } catch (e2) { Logger.log("[views.open] DM送信失敗: " + e2); }
    }
  }
  return result;
}

// チャンネル固定の操作パネル投稿（初回のみ手動実行）
function postOperationPanel() {
  const cfg     = getConfig();
  const channel = cfg["Slack ワークフローチャンネルID"] || cfg["Slack テストチャンネルID"];
  if (!channel) { Logger.log("[OpPanel] チャンネル未設定"); return; }

  const blocks = [
    { type: "header", text: { type: "plain_text", text: "🗓 LG/CA 連携 操作パネル" } },
    { type: "section", text: { type: "mrkdwn", text: "*面談登録* はこのボタンから。\n*メンバー追加* (CA/LG新規登録) もこのパネルから。\n日程入力・再回収・重複報告は各学生スレッド内のボタンを使ってください。" } },
    { type: "actions", elements: [
      { type: "button", text: { type: "plain_text", text: "📝 新規面談登録" }, style: "primary", action_id: "open_modal_register", value: "register" },
      { type: "button", text: { type: "plain_text", text: "👤 メンバー追加" }, action_id: "open_modal_member_add", value: "member_add" },
    ]},
  ];
  const r = sendSlackMessage(channel, "LG/CA 連携 操作パネル", blocks, null);
  if (r?.ts) Logger.log(`[OpPanel] 投稿完了 ts=${r.ts}`);
  return r;
}

// スレッド内のボタン群（フェーズに応じて出し分け）
// v5.7+: 2行レイアウト — 上段=LG用 / 下段=CA用
// 戻り値は blocks 配列 (caller は ...spread で挿入)
function buildThreadButtons(rowNo, phase) {
  const v = String(rowNo);
  const btn = (text, action_id, style) => ({
    type: "button",
    text: { type: "plain_text", text },
    action_id,
    value: v,
    ...(style ? { style } : {}),
  });
  // v5.7.1: 誤操作防止用 confirm ダイアログ付きボタン (キャンセル・飛び報告 等の不可逆操作向け)
  const btnConfirm = (text, action_id, style, confirmCfg) => ({
    type: "button",
    text: { type: "plain_text", text },
    action_id,
    value: v,
    ...(style ? { style } : {}),
    confirm: {
      title:   { type: "plain_text", text: confirmCfg.title },
      text:    { type: "mrkdwn",      text: confirmCfg.message },
      confirm: { type: "plain_text", text: confirmCfg.confirmText || "はい、実行する" },
      deny:    { type: "plain_text", text: "やめる" },
      style: "danger",
    },
  });
  const lgRow = [];
  const caRow = [];
  if (phase === "実施予定") {
    // LG行
    lgRow.push(btn("LG・🔁 リスケ依頼", "open_modal_recollect"));
    lgRow.push(btnConfirm("LG・❌ キャンセル", "cancel_meeting", "danger", {
      title: "面談キャンセル",
      message: `*#${_padNo(rowNo)} の面談がキャンセルされます。*\n本当によろしいですか？\n（カレンダー予定も削除されます）`,
      confirmText: "はい、キャンセルする",
    }));
    // CA行
    caRow.push(btnConfirm("CA・🚫 飛び報告", "no_show", "danger", {
      title: "飛び報告",
      message: `*#${_padNo(rowNo)} を「飛び」として報告します。*\n本当によろしいですか？\n（運用責任者に通知されます）`,
      confirmText: "はい、飛び報告する",
    }));
    caRow.push(btn("CA・⚠️ 重複報告", "open_modal_duplicate"));
    caRow.push(btn("CA・🔄 代打依頼", "open_modal_substitute"));
  } else if (phase === "日程調整中") {
    // LG行
    lgRow.push(btn("LG・🔁 日程再回収", "open_modal_recollect"));
    lgRow.push(btnConfirm("LG・❌ キャンセル", "cancel_meeting", "danger", {
      title: "面談キャンセル",
      message: `*#${_padNo(rowNo)} の面談がキャンセルされます。*\n本当によろしいですか？`,
      confirmText: "はい、キャンセルする",
    }));
    // CA行
    caRow.push(btn("CA・📅 日程入力", "open_modal_dateinput", "primary"));
    caRow.push(btnConfirm("CA・🚫 飛び報告", "no_show", "danger", {
      title: "飛び報告",
      message: `*#${_padNo(rowNo)} を「飛び」として報告します。*\n本当によろしいですか？`,
      confirmText: "はい、飛び報告する",
    }));
    caRow.push(btn("CA・⚠️ 重複報告", "open_modal_duplicate"));
  } else {
    caRow.push(btn("CA・⚠️ 重複報告", "open_modal_duplicate"));
  }
  const blocks = [];
  if (lgRow.length) blocks.push({ type: "actions", elements: lgRow });
  if (caRow.length) blocks.push({ type: "actions", elements: caRow });
  // 互換: 単一blockとしても扱えるよう .type をつける (旧呼び出し側用)
  blocks.type = "actions";
  blocks.elements = [...lgRow, ...caRow];
  return blocks.length ? blocks : null;
}

// モーダルを開く: actionId に応じて 4種を切替
function openModal(actionId, payload) {
  const triggerId = payload.trigger_id;
  const rowNo     = payload.actions?.[0]?.value || "";
  const channel   = payload.channel?.id || payload.container?.channel_id || "";
  const threadTs  = payload.message?.thread_ts || payload.message?.ts || "";
  const userId    = payload.user?.id || "";

  // v5.7+: 権限チェック (admin=tokumori社員/指名管理者は全許可)
  const perm = _isAllowed(userId, actionId);
  if (!perm.ok) {
    try {
      sendEphemeral(channel, userId,
        `⚠️ この操作は ${perm.allowed.join("/")} 限定です。あなたの役職: ${(perm.roles.length ? perm.roles.join(",") : "未登録")}`);
    } catch(_) {}
    return;
  }

  let view = null;
  if (actionId === "open_modal_register") {
    view = _buildModalRegister({ channel, threadTs, userId });
  } else if (actionId === "open_modal_dateinput") {
    view = _buildModalDateInput({ channel, threadTs, rowNo });
  } else if (actionId === "open_modal_recollect") {
    view = _buildModalRecollect({ channel, threadTs, rowNo });
  } else if (actionId === "open_modal_duplicate") {
    view = _buildModalDuplicate({ channel, threadTs, rowNo });
  } else if (actionId === "open_modal_member_add") {
    view = _buildModalMemberAdd();
  } else if (actionId === "open_modal_substitute") {
    view = _buildModalSubstitute({ channel, threadTs, rowNo });
  }
  if (!view) { Logger.log(`[openModal] 不明な actionId=${actionId}`); return; }
  _slackViewsOpen(triggerId, view, userId);
}

// 共通: input ブロックビルダー
function _inputBlock(blockId, label, element, optional) {
  return {
    type: "input", block_id: blockId,
    label: { type: "plain_text", text: label },
    element,
    optional: !!optional,
  };
}
function _txt(actionId, placeholder, multiline, initial) {
  const el = { type: "plain_text_input", action_id: actionId, multiline: !!multiline };
  if (placeholder) el.placeholder = { type: "plain_text", text: placeholder };
  if (initial) el.initial_value = initial;
  return el;
}
function _select(actionId, options) {
  return {
    type: "static_select", action_id: actionId,
    options: options.map(o => ({ text: { type: "plain_text", text: o }, value: o })),
  };
}
function _datepicker(actionId) {
  return { type: "datepicker", action_id: actionId };
}

// Modal-A: 面談登録
function _buildModalRegister({ channel, threadTs, userId }) {
  return {
    type: "modal",
    callback_id: "modal_register",
    private_metadata: JSON.stringify({ channel, threadTs }),
    title: { type: "plain_text", text: "📝 面談登録" },
    submit: { type: "plain_text", text: "登録" },
    close: { type: "plain_text", text: "キャンセル" },
    blocks: [
      _inputBlock("mode", "🔴必須｜予約モード", _select("value", [
        "通常モード（CA自動マッチング）",
        "自分のカレンダーで直接予約（LG=CA兼任）",
      ])),
      _inputBlock("lg_member", "🔴必須｜LGメンバー", { type: "users_select", action_id: "value", initial_user: userId || undefined }),
      _inputBlock("account",   "🔴必須｜学生アカウント名", _txt("value", "例: tanaka_taro")),
      _inputBlock("grade",     "🔴必須｜卒年", _select("value", ["28卒","29卒","30卒"])),
      _inputBlock("sns",       "🔴必須｜SNS種別", _select("value", ["Instagram","X","TikTok","YouTube","Threads","オープンチャット","リファラル","その他"])),
      _inputBlock("sns_other", "（任意）└ その他選択時の記述", _txt("value", "例: Threads / Note"), true),
      _inputBlock("reach",     "🔴必須｜つなぎ方", _select("value", [
        "友達繋ぎ","先輩繋ぎ","インターンの人繋ぎ","その他(自由記述)"
      ])),
      _inputBlock("reach_other", "（任意）└ その他選択時の記述", _txt("value", "例: 紹介媒体経由"), true),
      _inputBlock("industry",  "（任意）志望業界", _select("value", [
        "メーカー","IT・通信","コンサルティング","金融","商社",
        "人材・教育","インフラ・エネルギー","広告・メディア・サービス","その他(自由記述)"
      ]), true),
      _inputBlock("industry_other", "（任意）└ その他選択時の記述", _txt("value", "例: Web3"), true),
      _inputBlock("topic",     "🔴必須｜相談内容", _select("value", [
        "就活の始め方について","自己分析","面接対策","ES添削","GDについて","業界分析","その他(自由記述)"
      ])),
      _inputBlock("topic_other", "（任意）└ その他選択時の記述", _txt("value", "例: インターン応募"), true),
      _inputBlock("date1",     "🔴必須｜候補日①", _datepicker("value")),
      _inputBlock("time1",     "🔴必須｜候補時間①", _txt("value", "例: 10:00~12:00")),
      _inputBlock("date2",     "（任意）候補日②", _datepicker("value"), true),
      _inputBlock("time2",     "（任意）候補時間②", _txt("value", "例: 14:00~17:00"), true),
      _inputBlock("date3",     "（任意）候補日③", _datepicker("value"), true),
      _inputBlock("time3",     "（任意）候補時間③", _txt("value", "例: 10:00"), true),
    ],
  };
}

// Modal-B: 日程入力（CA）
function _buildModalDateInput({ channel, threadTs, rowNo }) {
  return {
    type: "modal",
    callback_id: "modal_dateinput",
    private_metadata: JSON.stringify({ channel, threadTs, rowNo }),
    title: { type: "plain_text", text: `📅 日程入力 #${_padNo(rowNo)}` },
    submit: { type: "plain_text", text: "登録" },
    close: { type: "plain_text", text: "キャンセル" },
    blocks: [
      _inputBlock("date",       "確定日", _datepicker("value")),
      _inputBlock("start_time", "確定開始時刻", _txt("value", "例: 10:00")),
      _inputBlock("end_time",   "確定終了時刻", _txt("value", "空欄なら自動算出"), true),
      _inputBlock("memo",       "補足メモ", _txt("value", "備考があれば", true), true),
    ],
  };
}

// Modal-C: 日程再回収（LG）
function _buildModalRecollect({ channel, threadTs, rowNo }) {
  return {
    type: "modal",
    callback_id: "modal_recollect",
    private_metadata: JSON.stringify({ channel, threadTs, rowNo }),
    title: { type: "plain_text", text: `🔁 日程再回収 #${_padNo(rowNo)}` },
    submit: { type: "plain_text", text: "再回収" },
    close: { type: "plain_text", text: "キャンセル" },
    blocks: [
      _inputBlock("date1", "新候補日①", _datepicker("value")),
      _inputBlock("time1", "新候補時間①", _txt("value", "例: 10:00~12:00")),
      _inputBlock("date2", "新候補日②", _datepicker("value"), true),
      _inputBlock("time2", "新候補時間②", _txt("value", "例: 14:00~17:00"), true),
      _inputBlock("date3", "新候補日③", _datepicker("value"), true),
      _inputBlock("time3", "新候補時間③", _txt("value", "例: 10:00"), true),
    ],
  };
}

// v5.7+: 重複報告モーダル
// v5.7+: Modal-E メンバー追加（CA/LG/兼任 を一発登録）
function _buildModalMemberAdd() {
  return {
    type: "modal",
    callback_id: "modal_member_add",
    title: { type: "plain_text", text: "👤 メンバー追加" },
    submit: { type: "plain_text", text: "登録" },
    close: { type: "plain_text", text: "キャンセル" },
    blocks: [
      { type: "section", text: { type: "mrkdwn", text: "Slack上のユーザーを選ぶだけでメンバーシートに自動登録します。\n名前・UIDは自動取得。CA/兼任の場合はメールも自動取得します。" } },
      _inputBlock("role", "役割", _select("value", ["LG", "CA", "兼任"])),
      _inputBlock("user", "Slackユーザー", { type: "users_select", action_id: "value" }),
      _inputBlock("division", "区分", _select("value", [
        "社員","業務委託","個人Gmail","社会人","27卒","28卒","29卒","30卒","メンター","その他"
      ])),
      _inputBlock("email", "メール (CAの場合・空欄ならSlackから取得)", _txt("value", "例: example@gmail.com"), true),
      _inputBlock("status", "ステータス", _select("value", ["アクティブ","共有待ち","非アクティブ"])),
      _inputBlock("memo", "備考 (任意)", _txt("value", "例: 4,5月稼働不可", true), true),
    ],
  };
}

// v5.7+: Modal-F 代打依頼 (CA)
function _buildModalSubstitute({ channel, threadTs, rowNo }) {
  return {
    type: "modal",
    callback_id: "modal_substitute",
    private_metadata: JSON.stringify({ channel, threadTs, rowNo }),
    title: { type: "plain_text", text: `🔄 代打依頼 #${_padNo(rowNo)}` },
    submit: { type: "plain_text", text: "依頼を出す" },
    close: { type: "plain_text", text: "キャンセル" },
    blocks: [
      { type: "section", text: { type: "mrkdwn", text: "同時間帯で空きのある他CAを自動マッチングします。見つからない場合は代打チャンネルで公募します。" } },
      _inputBlock("reason", "🔴必須｜理由 (代打を依頼する理由)", _txt("value", "例: 急な予定が入ったため", true)),
    ],
  };
}

function _buildModalDuplicate({ channel, threadTs, rowNo }) {
  return {
    type: "modal",
    callback_id: "modal_duplicate",
    private_metadata: JSON.stringify({ channel, threadTs, rowNo }),
    title: { type: "plain_text", text: `⚠️ 重複報告 #${_padNo(rowNo)}` },
    submit: { type: "plain_text", text: "報告" },
    close: { type: "plain_text", text: "キャンセル" },
    blocks: [
      { type: "section", text: { type: "mrkdwn", text: `*#${_padNo(rowNo)}* の重複を報告します。既存の登録番号がわかれば入力してください。` } },
      _inputBlock("existing_no", "既存の連携番号 (任意)", _txt("value", "例: 27"), true),
      _inputBlock("detail", "詳細メモ (任意)", _txt("value", "例: 既に石塚さんが対応中", true), true),
    ],
  };
}

// モーダル送信を受け取って分岐処理
function handleViewSubmission(payload) {
  const callbackId = payload.view?.callback_id;
  const meta       = JSON.parse(payload.view?.private_metadata || "{}");
  const values     = payload.view?.state?.values || {};
  const userId     = payload.user?.id;

  try {
    if (callbackId === "modal_register") {
      const modeLabel = values.mode?.value?.selected_option?.value || "";
      // v5.7+: 「その他」選択時は対応する補足テキストを採用
      const _resolveOther = (sel, other) => {
        const s = sel || "";
        const o = (other || "").trim();
        if (/その他/.test(s) && o) return o;
        return s;
      };
      const params = {
        _selfBooking: modeLabel.startsWith("自分のカレンダー"),
        lgMember: values.lg_member?.value?.selected_user || "",
        account:  values.account?.value?.value || "",
        grade:    values.grade?.value?.selected_option?.value || "",
        sns:      _resolveOther(values.sns?.value?.selected_option?.value, values.sns_other?.value?.value),
        reach:    _resolveOther(values.reach?.value?.selected_option?.value, values.reach_other?.value?.value),
        industry: _resolveOther(values.industry?.value?.selected_option?.value, values.industry_other?.value?.value),
        topic:    _resolveOther(values.topic?.value?.selected_option?.value, values.topic_other?.value?.value),
        date1:    values.date1?.value?.selected_date || "",
        time1:    values.time1?.value?.value || "",
        date2:    values.date2?.value?.selected_date || "",
        time2:    values.time2?.value?.value || "",
        date3:    values.date3?.value?.selected_date || "",
        time3:    values.time3?.value?.value || "",
        _channel: meta.channel,
        _slackTs: null,  // 後で操作パネル下に新規スレッドを作成
      };
      // v5.7+: 重い処理(CA照合+カレンダー作成) はキュー化してモーダルを即時クローズ
      _enqueueVSJob("modal_register", params);
      return {};
    }

    // v5.7+: 速い処理はインライン即時実行（タイムアウトしないものはキュー化しない）
    if (callbackId === "modal_dateinput") {
      applyDateInput({
        rowNo:     parseInt(meta.rowNo, 10),
        date:      values.date?.value?.selected_date || "",
        startTime: values.start_time?.value?.value || "",
        endTime:   values.end_time?.value?.value || "",
        memo:      values.memo?.value?.value || "",
        userId, channel: meta.channel, threadTs: meta.threadTs,
      });
      return {};
    }

    if (callbackId === "modal_recollect") {
      applyRecollect({
        rowNo: parseInt(meta.rowNo, 10),
        date1: values.date1?.value?.selected_date || "",
        time1: values.time1?.value?.value || "",
        date2: values.date2?.value?.selected_date || "",
        time2: values.time2?.value?.value || "",
        date3: values.date3?.value?.selected_date || "",
        time3: values.time3?.value?.value || "",
        userId, channel: meta.channel, threadTs: meta.threadTs,
      });
      return {};
    }

    if (callbackId === "modal_duplicate") {
      handleDuplicateReport({
        rowNo:      parseInt(meta.rowNo, 10),
        existingNo: values.existing_no?.value?.value || "",
        detail:     values.detail?.value?.value || "",
        userId, channel: meta.channel, threadTs: meta.threadTs,
      });
      return {};
    }

    if (callbackId === "modal_substitute") {
      const reason = (values.reason?.value?.value || "").trim();
      if (!reason) {
        return { response_action: "errors", errors: { reason: "理由は必須です" } };
      }
      // CA再照合は時間かかるのでキュー化
      _enqueueVSJob("modal_substitute", {
        rowNo: parseInt(meta.rowNo, 10),
        reason,
        requesterId: userId,
        channel: meta.channel,
        threadTs: meta.threadTs,
      });
      return {};
    }

    if (callbackId === "modal_member_add") {
      const result = addMember({
        role:        values.role?.value?.selected_option?.value || "",
        userId:      values.user?.value?.selected_user || "",
        division:    values.division?.value?.selected_option?.value || "",
        email:       (values.email?.value?.value || "").trim(),
        status:      values.status?.value?.selected_option?.value || "共有待ち",
        memo:        values.memo?.value?.value || "",
      });
      if (result.ok) {
        try { sendSlackMessage(userId, `✅ メンバー追加完了\n*${result.id}* ${result.name}\n→ メンバーシートに追加されました`, null, null); } catch(_) {}
      } else {
        try { sendSlackMessage(userId, `⚠️ メンバー追加失敗: ${result.error}`, null, null); } catch(_) {}
      }
      return {};
    }

  } catch (e) {
    Logger.log(`[handleViewSubmission] ERROR ${callbackId}: ${e}\nstack:${e.stack}`);
    return { response_action: "errors", errors: { _global: String(e).slice(0, 100) } };
  }
  return {};
}

// 日程再回収: 候補日時を上書きしてCA再照合
function applyRecollect(args) {
  const { rowNo, date1, time1, date2, time2, date3, time3, channel, threadTs } = args;
  const found = findRowByNo(rowNo);
  if (!found) {
    sendEphemeral(channel, args.userId, `⚠️ #${_padNo(rowNo)} がシートに見つかりません`);
    return;
  }
  const { sheet, rowIdx, data } = found;
  const rowData = data[rowIdx];

  // v5.7+: 旧確定CAのカレンダーから該当面談イベントを削除（リスケ＝古い予定無効化）
  const prevCaName = String(rowData[19] || "").trim();
  if (prevCaName) {
    const prevCalId = _getCalIdByCaName(prevCaName);
    if (prevCalId) {
      const delRes = _deleteCalendarEventByRowNo(prevCalId, rowNo);
      Logger.log(`[applyRecollect] 旧予定削除 CA=${prevCaName}: ${JSON.stringify(delRes)}`);
      const prevCaUid = _getCASlackUid(prevCaName);
      if (prevCaUid && threadTs) {
        sendSlackMessage(channel, `🔁 *リスケのため #${_padNo(rowNo)} の予定を <@${prevCaUid}> のカレンダーから削除しました*`, null, threadTs);
      }
    }
  }

  // 候補日時上書き（J/K/M/N/P/Q列）
  sheet.getRange(rowIdx + 1, 10).setValue(date1);
  sheet.getRange(rowIdx + 1, 11).setValue(time1);
  sheet.getRange(rowIdx + 1, 13).setValue(date2 || "");
  sheet.getRange(rowIdx + 1, 14).setValue(time2 || "");
  sheet.getRange(rowIdx + 1, 16).setValue(date3 || "");
  sheet.getRange(rowIdx + 1, 17).setValue(time3 || "");

  // 履歴をメモ列(AA=27)に追記
  const oldMemo = String(rowData[26] || "");
  const historyEntry = `\n\n【日程再回収 ${formatDatetime(new Date())}】\n${[`${date1} ${time1}`, date2 && `${date2} ${time2}`, date3 && `${date3} ${time3}`].filter(Boolean).join(" / ")}`;
  sheet.getRange(rowIdx + 1, 27).setValue(oldMemo + historyEntry);

  // フェーズを「日程調整中」に戻す + リマインドフラグリセット
  sheet.getRange(rowIdx + 1, 22).setValue("日程調整中");
  sheet.getRange(rowIdx + 1, COL_REMIND_FLAGS).setValue("");
  sheet.getRange(rowIdx + 1, COL_LAST_REMINDED).setValue("");
  // v5.7+: 確定日時・CAメンバー・Meet URL・CA確認 をクリア（再調整中なので古い情報を残さない）
  sheet.getRange(rowIdx + 1, 19, 1, 3).setValues([["", "", ""]]);  // S/T/U: 確定日時・CA・Meet URL
  sheet.getRange(rowIdx + 1, 25).setValue("");                       // Y: CA確認
  // 登録日(B列)をリセットしてリマインド経過時間を再カウント
  sheet.getRange(rowIdx + 1, 2).setValue(formatDate(new Date()));

  // CA再照合
  const candidates = [
    { date: date1, time: time1 },
    { date: date2, time: time2 },
    { date: date3, time: time3 },
  ].filter(c => c.date && c.time);

  const calParams = {
    lgMember: rowData[2], account: rowData[4], grade: rowData[5],
    sns: rowData[6], industry: rowData[7], topic: rowData[8], reach: rowData[11],
  };
  // v5.7+: check→insert を LockService で直列化（同時設定によるダブルブッキング防止）
  let confirmed = null;
  let cal = null;
  let _lockFailedR = false;
  let _calFailedR  = null;  // 失敗したCA名
  {
    const _lockR = LockService.getScriptLock();
    const _gotR  = _lockR.tryLock(10000);
    if (!_gotR) {
      Logger.log(`[applyRecollect] LockService 取得失敗 → 日程調整中扱い`);
      _lockFailedR = true;
    } else {
      try {
        confirmed = checkCAAvailability(candidates);
        if (confirmed) {
          const _lgNameR = String(rowData[2] || "").trim();
          cal = createCalendarEvent(confirmed.calId, calParams, confirmed.startDt, confirmed.endDt, _lgNameR, confirmed.caName, rowNo);
          if (!cal || !cal.event) {
            Logger.log(`[applyRecollect] カレンダー登録失敗 (${confirmed.caName}) → 日程調整中扱い`);
            _calFailedR = confirmed.caName;
            confirmed = null;
            cal = null;
          }
        }
      } finally { _lockR.releaseLock(); }
    }
  }
  const studentTs = String(rowData[25] || "").trim() || threadTs;

  // v5.7: LG担当mention解決
  const _lgInfoR = getLGInfo(calParams.lgMember);
  const _lgUidR  = /^U[A-Z0-9]+$/.test(String(calParams.lgMember).trim()) ? String(calParams.lgMember).trim() : _lgInfoR.slackUid;

  if (confirmed) {
    const confirmedStr = `${formatDatetime(confirmed.startDt)}〜${formatTime(confirmed.endDt)}`;
    sheet.getRange(rowIdx + 1, 19, 1, 4).setValues([[confirmedStr, confirmed.caName, cal.meetUrl, "実施予定"]]);
    // v5.7+: 再回収→確定メッセージにもボタン付与
    const _rNotifText = formatNotification({
      statusEmoji: "✅", title: "再回収→確定", rowNo,
      account: calParams.account, grade: calParams.grade, sns: calParams.sns,
      lgUid: _lgUidR, caUid: confirmed.slackUid, caName: confirmed.caName,
      detail: `日時: ${confirmedStr}\nMeet: ${cal.meetUrl}`,
    });
    const _rBlocks = [{ type: "section", text: { type: "mrkdwn", text: _rNotifText } }];
    const _rBtn = buildThreadButtons(rowNo, "実施予定");
    if (_rBtn) _rBlocks.push(..._rBtn);
    sendSlackMessage(channel, _rNotifText, _rBlocks, studentTs);
  } else {
    // v5.7+: 失敗理由をLGに ephemeral 通知（ロック/カレンダー権限の問題切り分け用）
    if (_lockFailedR && _lgUidR) {
      sendEphemeral(channel, _lgUidR, "⏳ 再回収処理がロック取得待ちでタイムアウトしました。日程調整中扱いです。数秒後に再操作してください。");
    } else if (_calFailedR && _lgUidR) {
      sendEphemeral(channel, _lgUidR, `⚠️ ${_calFailedR} のカレンダーに書き込めず日程調整中扱いになりました。CAのカレンダー共有設定をご確認ください。`);
    }
    // v5.7+: 再回収→CA調整依頼にもボタン付与（日程調整中フェーズのボタン群）
    const _r2Text = formatNotification({
      statusEmoji: "⏳", title: "再回収→CA調整依頼", rowNo,
      account: calParams.account, grade: calParams.grade, sns: calParams.sns,
      lgUid: _lgUidR,
      detail: `希望日程: ${candidates.map(c => `${c.date} ${c.time}`).join(" / ")}\n→ CAは「日程入力」ボタンから日程を入れてください。`,
    });
    const _r2Blocks = [{ type: "section", text: { type: "mrkdwn", text: _r2Text } }];
    const _r2Btn = buildThreadButtons(rowNo, "日程調整中");
    if (_r2Btn) _r2Blocks.push(..._r2Btn);
    sendSlackMessage(channel, _r2Text, _r2Blocks, studentTs);
  }
}

// v5.7+: 代打依頼処理 — 自動マッチング → 失敗時は公募
function handleSubstituteRequest(args) {
  const { rowNo, reason, requesterId, channel, threadTs } = args;
  const found = findRowByNo(rowNo);
  if (!found) {
    sendSlackMessage(requesterId, `⚠️ #${_padNo(rowNo)} がシートに見つかりません`, null, null);
    return;
  }
  const { sheet, data, rowIdx } = found;
  const targetRow = rowIdx + 1;
  const rowData   = data[rowIdx];
  const account   = String(rowData[4] || "").trim();
  const grade     = String(rowData[5] || "").trim();
  const sns       = String(rowData[6] || "").trim();
  const confStr   = String(rowData[18] || "").trim();
  const currentCA = String(rowData[19] || "").trim();
  const meetUrl   = String(rowData[20] || "").trim();
  if (!confStr) {
    sendSlackMessage(requesterId, `⚠️ #${_padNo(rowNo)} 確定日時が未設定のため代打依頼できません`, null, null);
    return;
  }
  // confStr "2026/05/26 14:00〜14:45" → startDt
  const m = confStr.match(/^(\d{4})\/(\d{1,2})\/(\d{1,2})\s+(\d{1,2}):(\d{2})/);
  if (!m) {
    sendSlackMessage(requesterId, `⚠️ 確定日時の解析失敗: ${confStr}`, null, null);
    return;
  }
  const startDt = new Date(+m[1], +m[2] - 1, +m[3], +m[4], +m[5]);
  const endDt   = new Date(startDt.getTime() + getMeetingDurationMin() * 60 * 1000);

  // 元スレッドのpermalink
  let originalPermalink = "";
  if (threadTs) {
    try {
      const token = PropertiesService.getScriptProperties().getProperty("SLACK_BOT_TOKEN") || getConfig()["Slack Bot Token"];
      const r = UrlFetchApp.fetch(`https://slack.com/api/chat.getPermalink?channel=${channel}&message_ts=${threadTs}`,
        { headers: { Authorization: "Bearer " + token }, muteHttpExceptions: true });
      const j = JSON.parse(r.getContentText());
      if (j.ok) originalPermalink = j.permalink;
    } catch(_) {}
  }

  const subCh = getConfig()["Slack 代打チャンネルID"] || "C0A4YVD662E";
  const cgId  = getConfig()["CAユーザーグループID"];
  const caMention = cgId ? `<!subteam^${cgId}>` : "@CA";

  // 自動マッチング: 現CA以外のアクティブCAで同時間帯が空いてるCAを探す
  const caList = _caListRows()
    .filter(r => r[0] && r[1] && String(r[4] || "").trim() === "アクティブ" && String(r[0]).trim() !== currentCA)
    .map(r => ({ name: String(r[0]).trim(), calId: String(r[1]).trim(), slackUid: String(r[2] || "").trim() }));

  let matched = null;
  const excludeKeywords = getExcludeKeywords();
  for (const ca of caList) {
    if (!_isCAAvailableInHours(ca.calId, startDt, endDt)) continue;
    try {
      const res = Calendar.Events.list(ca.calId, {
        timeMin: startDt.toISOString(), timeMax: endDt.toISOString(),
        singleEvents: true, maxResults: 50,
      });
      const events = (res.items || []).filter(ev => {
        if (ev.status === "cancelled") return false;
        if (ev.transparency === "transparent") return false;
        if (_isBlockerEventAdv(ev, excludeKeywords)) return false;
        return true;
      });
      if (events.length === 0) { matched = ca; break; }
    } catch(e) { Logger.log(`[Substitute CalCheck ${ca.name}] ${e}`); }
  }

  if (matched) {
    // v5.7+: 自動マッチ成功 → 旧CA削除 → 新CAに既存URLで上書き作成
    const oldCalId = _getCalIdByCaName(currentCA);
    if (oldCalId) _deleteCalendarEventByRowNo(oldCalId, rowNo);
    const lgKeyA = String(rowData[2] || "").trim();
    const lgInfoA = getLGInfo(lgKeyA);
    createCalendarEvent(matched.calId, {
      account, grade, sns,
      industry: String(rowData[7] || ""),
      topic:    String(rowData[8] || ""),
      reach:    String(rowData[11] || ""),
      lgMember: lgKeyA,
    }, startDt, endDt, lgInfoA.name || lgKeyA, matched.name, rowNo, meetUrl);
    sheet.getRange(targetRow, 20).setValue(matched.name);
    // sheet U列(Meet URL) は変更しない

    const subMsg =
      `✅ *代打成立 #${_padNo(rowNo)}*\n` +
      `学生: ${account}（${grade}・${sns}）\n` +
      `日時: ${confStr}\n` +
      `旧CA: ${currentCA}\n` +
      `新CA: ${matched.slackUid ? `<@${matched.slackUid}>` : matched.name}\n` +
      `Meet (変更なし): ${meetUrl}\n` +
      `理由: ${reason}\n` +
      (originalPermalink ? `元スレッド: ${originalPermalink}` : "") +
      `\n※Meet URLは変わりません。新CAは当日上記URLでご参加ください。`;
    try { sendSlackMessage(subCh, subMsg, null, null); } catch(_) {}
    // LG解決して元スレッドにも通知
    const lgKey3 = String(rowData[2] || "").trim();
    const lgUidStored3 = String(rowData[24] || "").trim();
    const lgInfo3 = getLGInfo(lgKey3);
    const lgUid3 = lgUidStored3 && /^U[A-Z0-9]+$/.test(lgUidStored3) ? lgUidStored3
                 : (/^U[A-Z0-9]+$/.test(lgKey3) ? lgKey3 : lgInfo3.slackUid);
    const lgMention3 = lgUid3 ? `<@${lgUid3}>` : (lgInfo3.name || lgKey3);
    sendSlackMessage(channel,
      `🔄 *#${_padNo(rowNo)} 代打成立* (自動マッチ)\n` +
      `${lgMention3} ← 担当LG確認お願いします\n` +
      `旧CA: ${currentCA}\n` +
      `新CA: ${matched.slackUid ? `<@${matched.slackUid}>` : matched.name}\n` +
      `日時: ${confStr}\n` +
      `🔗 *Meet URLは変更なし*: ${meetUrl}\n` +
      `→ 学生に既に共有済のURLでそのままご案内ください`, null, threadTs);
    // 依頼者にもDM
    if (requesterId) sendSlackMessage(requesterId, `✅ 代打成立 #${_padNo(rowNo)} → ${matched.name}\nMeet URLは変わりません`, null, null);
    // 新CA本人にも詳細DM
    if (matched.slackUid) {
      sendSlackMessage(matched.slackUid, `🔄 *代打受諾 #${_padNo(rowNo)}* (自動マッチ)\n学生: ${account}\n日時: ${confStr}\nMeet: ${meetUrl}\n\n※Meet URLは変わりません。当日上記URLからご参加ください。\n※カレンダーへの追加が必要な場合は手動でお願いします`, null, null);
    }
  } else {
    // 公募
    const subMsg =
      `🆘 *代打募集 #${_padNo(rowNo)}* ${caMention}\n` +
      `学生: ${account}（${grade}・${sns}）\n` +
      `日時: ${confStr}\n` +
      `現CA: ${currentCA}\n` +
      `理由: ${reason}\n` +
      (originalPermalink ? `元スレッド: ${originalPermalink}\n\n` : "\n") +
      `→ 代われる方は下記ボタンを押してください`;
    const blocks = [
      { type: "section", text: { type: "mrkdwn", text: subMsg } },
      { type: "actions", elements: [
        { type: "button", text: { type: "plain_text", text: "✋ 代わります" }, style: "primary", action_id: "accept_substitute", value: JSON.stringify({ rowNo, origCh: channel, origTs: threadTs, requesterId }) },
      ]},
    ];
    try { sendSlackMessage(subCh, subMsg, blocks, null); } catch(_) {}
    sendSlackMessage(channel, `🆘 *#${_padNo(rowNo)} 代打公募中* (代打チャンネルへ投稿)\n${currentCA} の代打を募集しています。理由: ${reason}`, null, threadTs);
    if (requesterId) sendSlackMessage(requesterId, `🆘 自動マッチ失敗 → 代打チャンネルで公募投稿しました`, null, null);
  }
}

// v5.7+: 重複報告（モーダル経由）→ シート行のフェーズを「重複（要整理）」+ 飛びChに通知
function handleDuplicateReport(args) {
  const { rowNo, existingNo, detail, userId, channel, threadTs } = args;
  const found = findRowByNo(rowNo);
  if (!found) {
    if (userId) sendEphemeral(channel, userId, `⚠️ #${_padNo(rowNo)} が見つかりません`);
    return;
  }
  const { sheet, rowIdx } = found;
  // フェーズ列(V=22)を「重複（要整理）」、AB列(_SF除外フラグ=28)に TRUE
  sheet.getRange(rowIdx + 1, 22).setValue("重複（要整理）");
  sheet.getRange(rowIdx + 1, 28).setValue(true);
  if (detail) sheet.getRange(rowIdx + 1, 24).setValue(detail);  // X列メモ

  const cfg = getConfig();
  const reporter = userId ? `<@${userId}>` : "手動報告";
  const text = `⚠️ *重複報告 #${_padNo(rowNo)}*\n` +
               (existingNo ? `既存登録: #${existingNo}\n` : "") +
               (detail ? `詳細: ${detail}\n` : "") +
               `報告者: ${reporter}`;
  // 飛びチャンネルに通知
  const flyCh = cfg["Slack 飛びチャンネルID"];
  if (flyCh) sendSlackMessage(flyCh, text, null, null);
  // 学生スレッドにも返信
  if (threadTs) sendSlackMessage(channel, text, null, threadTs);
}

// ─────────────────────────────────────────
// リマインド（12h / 24h / 36h で段階通知、36h超で自動「調整不可」化）
// 毎時実行
// ─────────────────────────────────────────

function remindStalledMeetings() {
  const cfg = getConfig();
  const channel = cfg["Slack ワークフローチャンネルID"] || cfg["Slack テストチャンネルID"];
  const now = new Date();
  const cgId = cfg["CAユーザーグループID"];
  const caMention = cgId ? `<!subteam^${cgId}>` : "@CA";

  for (const sheet of getAllGradeSheets()) {
    const lastRow = sheet.getLastRow();
    if (lastRow < 2) continue;
    const data = sheet.getRange(1, 1, lastRow, GRADE_SHEET_COLS).getValues();
    for (let i = 1; i < data.length; i++) {
      if (!data[i][0]) continue;
      const phase = String(data[i][21] || "").trim();
      if (phase !== "日程調整中") continue;

      const regDate = data[i][1] instanceof Date ? data[i][1] : new Date(String(data[i][1]));
      if (isNaN(regDate.getTime())) continue;
      const elapsedH = (now - regDate) / (60 * 60 * 1000);

      const flags = String(data[i][COL_REMIND_FLAGS - 1] || "").split("|").filter(Boolean);
      const rowNo   = data[i][0];
      const slackTs = String(data[i][25] || "").trim();
      const account = String(data[i][4] || "");
      const grade   = String(data[i][5] || "");
      const sns     = String(data[i][6] || "");
      const lgKey   = String(data[i][2] || "").trim();
      const lgInfo  = getLGInfo(lgKey);
      const lgUid   = /^U[A-Z0-9]+$/.test(lgKey) ? lgKey : lgInfo.slackUid;

      // v5.7+: 希望日程をリマインド本文に含める
      const candPairs = [
        [data[i][9],  data[i][10]],
        [data[i][12], data[i][13]],
        [data[i][15], data[i][16]],
      ].filter(p => p[0] && p[1]).map(p => `${p[0]} ${p[1]}`);
      const candText = candPairs.length ? candPairs.join(" / ") : "未指定";
      const lgMentionR = lgUid ? `<@${lgUid}>` : (lgInfo?.name || lgKey || "未設定");

      const reminders = [
        { hours: 12, flag: "12h", emoji: "⏰",  hoursLabel: "12時間",
          cta: "「📅 日程入力」ボタンから日程確定をお願いします" },
        { hours: 24, flag: "24h", emoji: "⏰⏰", hoursLabel: "24時間",
          cta: "丸1日経過しました。最優先で日程入力をお願いします" },
      ];

      for (const r of reminders) {
        if (elapsedH >= r.hours && !flags.includes(r.flag) && slackTs) {
          // v5.7+: 文章構成を厳密化 — CAメンション → タイトル → 詳細箇条書き → CTA
          const body = [
            caMention,
            ``,
            `${r.emoji} *面談リマインド #${_padNo(rowNo)}（${r.hoursLabel}経過）*`,
            ``,
            `・担当LG: ${lgMentionR}`,
            `・学生: ${account}${grade || sns ? `（${[grade,sns].filter(Boolean).join("・")}）` : ""}`,
            `・希望日程: ${candText}`,
            ``,
            `→ ${r.cta}`,
          ].join("\n");
          sendSlackMessage(channel, body, null, slackTs);
          flags.push(r.flag);
          sheet.getRange(i + 1, COL_REMIND_FLAGS).setValue(flags.join("|"));
          sheet.getRange(i + 1, COL_LAST_REMINDED).setValue(formatDatetime(now));
        }
      }

      // 36h経過 → 自動「調整不可」化
      if (elapsedH >= 36 && !flags.includes("36h")) {
        sheet.getRange(i + 1, 22).setValue("調整不可");
        flags.push("36h");
        sheet.getRange(i + 1, COL_REMIND_FLAGS).setValue(flags.join("|"));
        if (slackTs) {
          const lgMentionR2 = lgUid ? `<@${lgUid}>` : (lgInfo?.name || lgKey || "未設定");
          const body = [
            `🚫 *自動「調整不可」化 #${_padNo(rowNo)}（36時間経過）*`,
            ``,
            `・担当LG: ${lgMentionR2}`,
            `・学生: ${account}${grade || sns ? `（${[grade,sns].filter(Boolean).join("・")}）` : ""}`,
            ``,
            `36時間経過しても日程確定できなかったため、フェーズを「調整不可」に変更しました。`,
            `→ 学生フォロー・別動線の検討をお願いします`,
          ].join("\n");
          sendSlackMessage(channel, body, null, slackTs);
        }
      }
    }
  }
}

// ─────────────────────────────────────────
// 月次集計シート（v5.6）
//   - 全卒年シートを走査し、登録日が指定月のものを集計
//   - 引数なし: 前月を集計（毎月1日トリガー想定）
//   - 引数指定: "YYYY-MM" 形式で過去月を手動生成可能
//   - 集計: 全体KPI / LG別 / CA別 / 流入経路別 / 卒年別 / 業界別
// ─────────────────────────────────────────

function createMonthlyDigest(targetMonth) {
  const now = new Date();
  let year, month;
  if (targetMonth && /^\d{4}-\d{1,2}$/.test(targetMonth)) {
    const parts = targetMonth.split("-");
    year  = parseInt(parts[0], 10);
    month = parseInt(parts[1], 10);
  } else {
    const prev = new Date(now.getFullYear(), now.getMonth() - 1, 1);
    year  = prev.getFullYear();
    month = prev.getMonth() + 1;
  }
  const ym = `${year}-${String(month).padStart(2, "0")}`;
  const sheetName = `月次集計_${ym}`;

  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(sheetName);
  if (sheet) {
    sheet.clearContents();
    sheet.clearFormats();
  } else {
    sheet = ss.insertSheet(sheetName);
  }

  // 集計用データ構造
  const stats = {
    total: 0, confirmed: 0, jisshi: 0, tobi: 0, futeki: 0, risuke: 0, dup: 0, adjusting: 0,
    byLG: {}, byCA: {}, bySns: {}, byIndustry: {}, byGrade: {},
  };

  const incr = (bucket, key, field) => {
    if (!key) return;
    if (!bucket[key]) bucket[key] = { total: 0, jis: 0, tobi: 0, futeki: 0, risuke: 0 };
    bucket[key][field]++;
  };

  for (const gs of getAllGradeSheets()) {
    const data = gs.getDataRange().getValues();
    for (let i = 1; i < data.length; i++) {
      if (!data[i][0]) continue;
      const regDate = data[i][1] instanceof Date ? data[i][1] : new Date(String(data[i][1]));
      if (isNaN(regDate.getTime())) continue;
      if (regDate.getFullYear() !== year || regDate.getMonth() + 1 !== month) continue;

      const lg       = String(data[i][2] || "").trim();
      const account  = String(data[i][4] || "").trim();
      const grade    = String(data[i][5] || "").trim();
      const sns      = String(data[i][6] || "").trim();
      const industry = String(data[i][7] || "").trim();
      const ca       = String(data[i][19] || "").trim();
      const phase    = String(data[i][21] || "").trim();

      stats.total++;
      if (phase === "実施済" || phase === "実施予定") stats.confirmed++;
      if (phase === "実施済")            stats.jisshi++;
      if (phase === "飛び")              stats.tobi++;
      if (phase === "調整不可")          stats.futeki++;
      if (phase === "リスケ")            stats.risuke++;
      if (phase === "重複（要整理）")    stats.dup++;
      if (phase === "日程調整中")        stats.adjusting++;

      incr(stats.byLG, lg, "total");
      if (phase === "実施済")   incr(stats.byLG, lg, "jis");
      if (phase === "飛び")     incr(stats.byLG, lg, "tobi");
      if (phase === "調整不可") incr(stats.byLG, lg, "futeki");
      if (phase === "リスケ")   incr(stats.byLG, lg, "risuke");

      if (ca) {
        incr(stats.byCA, ca, "total");
        if (phase === "実施済") incr(stats.byCA, ca, "jis");
        if (phase === "飛び")   incr(stats.byCA, ca, "tobi");
      }
      if (sns) {
        incr(stats.bySns, sns, "total");
        if (phase === "実施済") incr(stats.bySns, sns, "jis");
      }
      if (industry) {
        incr(stats.byIndustry, industry, "total");
        if (phase === "実施済") incr(stats.byIndustry, industry, "jis");
      }
      if (grade) {
        incr(stats.byGrade, grade, "total");
        if (phase === "実施済") incr(stats.byGrade, grade, "jis");
      }
    }
  }

  // 描画ヘルパー
  let row = 1;
  const write = (vals, opts) => {
    const r = sheet.getRange(row, 1, 1, vals.length);
    r.setValues([vals]);
    if (opts?.bold) r.setFontWeight("bold");
    if (opts?.bg)   r.setBackground(opts.bg);
    if (opts?.fg)   r.setFontColor(opts.fg);
    row++;
  };
  const section = (title) => write([title], { bold: true, bg: "#ECEFF1" });
  const pct = (n, d) => d ? (n / d * 100).toFixed(1) + "%" : "-";

  // タイトル
  sheet.getRange(1, 1, 1, 7).merge();
  write([`📊 ${ym} 月次集計`], { bold: true, bg: "#37474F", fg: "#FFFFFF" });
  write([`生成日時: ${formatDatetime(new Date())}`]);
  row++;

  // 全体KPI
  section("■ 全体KPI");
  write(["項目", "件数", "比率"], { bold: true });
  write(["月間総登録数", stats.total, ""]);
  write(["確定数（実施予定+実施済）", stats.confirmed, pct(stats.confirmed, stats.total)]);
  write(["実施数", stats.jisshi, pct(stats.jisshi, stats.confirmed) + "（対確定）"]);
  write(["飛び数", stats.tobi, pct(stats.tobi, stats.total)]);
  write(["調整不可数", stats.futeki, pct(stats.futeki, stats.total)]);
  write(["リスケ数", stats.risuke, ""]);
  write(["日程調整中（月末時点）", stats.adjusting, ""]);
  write(["重複（要整理）", stats.dup, ""]);
  row++;

  // LG別
  section("■ LG別KPI");
  write(["LGメンバー", "登録数", "実施数", "飛び", "調整不可", "リスケ", "実施率"], { bold: true });
  Object.entries(stats.byLG)
    .sort((a, b) => b[1].total - a[1].total)
    .forEach(([name, s]) => write([name, s.total, s.jis, s.tobi, s.futeki, s.risuke, pct(s.jis, s.total)]));
  row++;

  // CA別
  section("■ CA別KPI");
  write(["CAメンバー", "担当数", "実施数", "飛び", "実施率"], { bold: true });
  Object.entries(stats.byCA)
    .sort((a, b) => b[1].total - a[1].total)
    .forEach(([name, s]) => write([name, s.total, s.jis, s.tobi, pct(s.jis, s.total)]));
  row++;

  // 流入経路別
  section("■ 流入経路別");
  write(["SNS種別", "登録数", "実施数", "実施率"], { bold: true });
  Object.entries(stats.bySns)
    .sort((a, b) => b[1].total - a[1].total)
    .forEach(([name, s]) => write([name, s.total, s.jis, pct(s.jis, s.total)]));
  row++;

  // 卒年別
  section("■ 卒年別");
  write(["卒年", "登録数", "実施数", "実施率"], { bold: true });
  Object.entries(stats.byGrade)
    .sort()
    .forEach(([name, s]) => write([name, s.total, s.jis, pct(s.jis, s.total)]));
  row++;

  // 業界別
  section("■ 志望業界別");
  write(["業界", "登録数", "実施数", "実施率"], { bold: true });
  Object.entries(stats.byIndustry)
    .sort((a, b) => b[1].total - a[1].total)
    .forEach(([name, s]) => write([name, s.total, s.jis, pct(s.jis, s.total)]));

  for (let c = 1; c <= 7; c++) sheet.autoResizeColumn(c);
  sheet.setFrozenRows(2);

  Logger.log(`[MonthlyDigest] ${sheetName} 生成完了（登録数=${stats.total}）`);
  return sheetName;
}

// ─────────────────────────────────────────
// v5.7+: テストデータ一括クリーンアップ
//   - 全卒年シートのデータ行をクリア（ヘッダーは残す）
//   - _debug_ca_access タブを削除
//   - globalRowNo を 0 にリセット
// 実行: GASエディタで cleanupTestData を選択 → 実行
// ─────────────────────────────────────────

function cleanupTestData() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const log = [];

  // 1. 全卒年シートのデータ行を削除（行2以降を全て削除、ヘッダー1行は残す）
  for (const sheet of getAllGradeSheets()) {
    const lastRow = sheet.getLastRow();
    if (lastRow > 1) {
      sheet.deleteRows(2, lastRow - 1);
      log.push(`${sheet.getName()}: ${lastRow - 1}行削除`);
    }
  }

  // 2. _debug_ca_access / _prod_readiness タブ削除
  ["_debug_ca_access", "_prod_readiness"].forEach(name => {
    const sh = ss.getSheetByName(name);
    if (sh) { ss.deleteSheet(sh); log.push(`${name} タブ削除`); }
  });

  // 3. globalRowNo を 0 にリセット
  PropertiesService.getScriptProperties().setProperty("globalRowNo", "0");
  log.push("globalRowNo → 0");

  // 4. v5.7+: 全CAカレンダーのテスト面談イベントを削除（過去1週間〜未来3ヶ月）
  //    対象パターン: 新形式 "#NNNN @account｜..." / 旧形式 "【面談】SNS経由/..."
  {
    const cas = _caListRows()
      .filter(r => r[0] && r[1] && String(r[4] || "").trim() === "アクティブ")
      .map(r => ({ name: String(r[0]).trim(), calId: String(r[1]).trim() }));
    const timeMin = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString();
    const timeMax = new Date(Date.now() + 90 * 24 * 60 * 60 * 1000).toISOString();
    let deleted = 0, failed = 0;
    for (const ca of cas) {
      try {
        const res = Calendar.Events.list(ca.calId, { timeMin, timeMax, singleEvents: true, maxResults: 2500, q: "面談" });
        const targets = (res.items || []).filter(ev => {
          const t = String(ev.summary || "");
          return /^#\d{4}\s+@/.test(t) || /^【面談】.+経由\//.test(t);
        });
        for (const ev of targets) {
          try { Calendar.Events.remove(ca.calId, ev.id, { sendUpdates: "none" }); deleted++; }
          catch(e2) { failed++; Logger.log(`[Cleanup] ${ca.name} ${ev.id}: ${e2}`); }
        }
        log.push(`${ca.name}: ${targets.length}件 削除候補`);
      } catch(e) {
        log.push(`${ca.name}: list失敗 (${String(e).slice(0, 60)})`);
      }
    }
    log.push(`カレンダー削除合計: ${deleted}件 / 失敗: ${failed}件`);
  }

  Logger.log("=== cleanupTestData 完了 ===");
  log.forEach(l => Logger.log("  " + l));
  return log;
}

// v5.7+: クリーンアップ→検証→空き枠の一括チェック
function fullCleanupAndCheck() {
  Logger.log("STEP1: cleanupTestData");
  cleanupTestData();
  Logger.log("STEP2: validateProductionReadiness");
  validateProductionReadiness();
  Logger.log("STEP3: debugCAAccess");
  debugCAAccess();
  Logger.log("=== fullCleanupAndCheck 完了 ===");
}

// ─────────────────────────────────────────
// v5.7+: 全CAカレンダーアクセステスト + 直近1週間の空き枠カウント
// 実行: GASエディタで debugCAAccess を選択 → 実行
// ─────────────────────────────────────────

function debugCAAccess() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let outSheet = ss.getSheetByName("_debug_ca_access");
  if (!outSheet) outSheet = ss.insertSheet("_debug_ca_access");
  outSheet.clearContents();
  const rows = [["CAメンバー", "アクセス書き込み", "エラー詳細", "直近2週間 空き枠"]];

  const cas = _caListRows()
    .filter(r => r[0] && r[1] && String(r[4] || "").trim() === "アクティブ")
    .map(r => ({ name: String(r[0]).trim(), calId: String(r[1]).trim() }));

  Logger.log(`=== アクティブCA: ${cas.length}名 ===`);

  // 1. テストイベント作成（45分後の枠に1分イベント → すぐ削除）
  const now = new Date();
  const startDt = new Date(now.getTime() + 60 * 60 * 1000);   // 1h後
  const endDt   = new Date(startDt.getTime() + 60 * 1000);    // +1min

  const writeResults = [];
  for (const ca of cas) {
    try {
      const ev = Calendar.Events.insert({
        summary: "🧪 record@ access test (auto-delete)",
        start: { dateTime: startDt.toISOString(), timeZone: "Asia/Tokyo" },
        end:   { dateTime: endDt.toISOString(),   timeZone: "Asia/Tokyo" },
      }, ca.calId, { sendUpdates: "none" });
      // 即削除
      Calendar.Events.remove(ca.calId, ev.id, { sendUpdates: "none" });
      writeResults.push({ ca: ca.name, ok: true });
    } catch(e) {
      writeResults.push({ ca: ca.name, ok: false, err: String(e).slice(0, 100) });
    }
  }

  Logger.log("=== 書き込みアクセステスト ===");
  writeResults.forEach(r => {
    Logger.log(`  ${r.ok ? "✅" : "❌"} ${r.ca}${r.err ? " : " + r.err : ""}`);
  });

  // 2. 直近2週間の空き枠カウント
  //    ルール: tokumori平日 9-20 / その他 全日 8-24
  //    Advanced Service で 1日分のイベント取得 → スロットごとに重複判定
  const meetingMin = getMeetingDurationMin();
  const stepMin    = getSlotStepMin();
  const excludeKeywords = getExcludeKeywords();

  const today = new Date();
  today.setHours(0,0,0,0);
  let totalFreePerCA = {};
  let totalFreeAny   = 0;
  let totalAllFree   = 0;
  let dayBreakdown   = [];

  for (let d = 0; d < 14; d++) {
    const dt = new Date(today.getTime() + d * 24*60*60*1000);
    const dow = ["日","月","火","水","木","金","土"][dt.getDay()];
    const dayLabel = `${dt.getMonth()+1}/${dt.getDate()}(${dow})`;

    // その日の各CAの全イベント（営業時間最大幅 = 8:00-24:00）を取得
    const dayWindowStart = new Date(dt); dayWindowStart.setHours(8, 0, 0, 0);
    const dayWindowEnd   = new Date(dt); dayWindowEnd.setHours(23, 0, 0, 0);
    const caEvents = cas.map(ca => {
      try {
        const res = Calendar.Events.list(ca.calId, {
          timeMin: dayWindowStart.toISOString(),
          timeMax: dayWindowEnd.toISOString(),
          singleEvents: true,
          maxResults: 250,
        });
        const events = (res.items || [])
          .filter(ev => ev.status !== "cancelled")
          .filter(ev => !_isBlockerEventAdv(ev, excludeKeywords))
          .map(ev => ({
            start: new Date(ev.start.dateTime || ev.start.date),
            end:   new Date(ev.end.dateTime   || ev.end.date),
          }));
        return { ca, events };
      } catch(e) { return { ca, events: [], err: String(e).slice(0,80) }; }
    });

    // 1日のスロット候補を 8:00 から 24:00-meetingMin まで stepMin 刻みで列挙
    let dayAnyFree = 0;
    let dayAllFree = 0;
    let daySlotsConsidered = 0;
    const lastStartMs = new Date(dt).setHours(23, 0, 0, 0) - meetingMin * 60 * 1000;
    for (let t = new Date(dt).setHours(8, 0, 0, 0); t <= lastStartMs; t += stepMin * 60 * 1000) {
      const slotStart = new Date(t);
      const slotEnd   = new Date(t + meetingMin * 60 * 1000);

      // この slot に参加可能な CA を絞り込み（ビジネスアワー判定 + 既存予定との重複なし）
      let freeCount = 0;
      let anyEligible = false;
      caEvents.forEach(({ca, events}) => {
        if (!_isCAAvailableInHours(ca.calId, slotStart, slotEnd)) return;
        anyEligible = true;
        const overlap = events.some(ev => ev.start < slotEnd && ev.end > slotStart);
        if (!overlap) {
          freeCount++;
          totalFreePerCA[ca.name] = (totalFreePerCA[ca.name] || 0) + 1;
        }
      });
      if (!anyEligible) continue; // 全CAが営業時間外のスロット → カウント対象外
      daySlotsConsidered++;
      if (freeCount > 0) dayAnyFree++;
      const eligibleCount = caEvents.filter(({ca}) => _isCAAvailableInHours(ca.calId, slotStart, slotEnd)).length;
      if (freeCount === eligibleCount && eligibleCount > 0) dayAllFree++;
    }
    totalFreeAny += dayAnyFree;
    totalAllFree += dayAllFree;
    dayBreakdown.push({ label: dayLabel, slots: daySlotsConsidered, anyFree: dayAnyFree, allFree: dayAllFree });
  }

  Logger.log("\n=== 直近2週間の空き枠 ===");
  Logger.log(`面談時間: ${meetingMin}分 / スロット刻み: ${stepMin}分 / tokumori平日9-20 / その他全日8-24`);
  Logger.log(`合計: 誰か空き=${totalFreeAny}枠 / 全員空き=${totalAllFree}枠`);
  Logger.log("--- 日別 ---");
  dayBreakdown.forEach(d => {
    Logger.log(`  ${d.label}: スロット${d.slots} / 誰か空き=${d.anyFree} / 全員空き=${d.allFree}`);
  });
  Logger.log("--- CA別合計空き枠 ---");
  cas.forEach(ca => {
    Logger.log(`  ${ca.name}: ${totalFreePerCA[ca.name] || 0}枠`);
  });

  // シートに書き出し（4列固定）
  cas.forEach(ca => {
    const wr = writeResults.find(w => w.ca === ca.name);
    rows.push([ca.name, wr?.ok ? "✅ OK" : "❌ NG", wr?.err || "", totalFreePerCA[ca.name] || 0]);
  });
  rows.push(["", "", "", ""]);
  rows.push(["=== 日別合計 ===", "誰か空き", "全員空き", "スロット"]);
  dayBreakdown.forEach(d => rows.push([d.label, d.anyFree, d.allFree, d.slots]));
  rows.push(["", "", "", ""]);
  rows.push(["合計", totalFreeAny, totalAllFree, `アクティブCA${cas.length}名`]);
  outSheet.getRange(1, 1, rows.length, 4).setValues(rows);

  // calId access 詳細を追加（cal=null判定）
  const detailRows = [["", "", "", ""], ["=== getCalendarById 詳細 ===", "", "", ""], ["CA", "calId", "cal!=null", "events数(5/22 10-21)"]];
  const sampleDt = new Date(); sampleDt.setHours(10,0,0,0);
  const sampleEnd = new Date(sampleDt); sampleEnd.setHours(21,0,0,0);
  cas.forEach(ca => {
    let calOk = false, eventCount = "?";
    try {
      const cal = CalendarApp.getCalendarById(ca.calId);
      calOk = !!cal;
      if (cal) eventCount = String(cal.getEvents(sampleDt, sampleEnd).length);
    } catch(e) { eventCount = "ERR: " + String(e).slice(0, 50); }
    detailRows.push([ca.name, ca.calId, calOk ? "✅" : "❌ null", eventCount]);
  });
  outSheet.getRange(rows.length + 1, 1, detailRows.length, 4).setValues(detailRows);
}

// ─────────────────────────────────────────
// トリガー一括設定（v5.6: createMonthlyDigest 毎月1日 0時 追加）
// ─────────────────────────────────────────

// ─────────────────────────────────────────
// v5.7+: 本番運用前バリデーション
// 実行: GASエディタで validateProductionReadiness を選択 → 実行 → 実行ログ確認
// ─────────────────────────────────────────

function validateProductionReadiness() {
  const result = [];
  const cfg = getConfig();
  const ss  = SpreadsheetApp.getActiveSpreadsheet();

  // 1. 必須設定キー
  const required = {
    "Slack Bot Token": v => /^xoxb-/.test(String(v)),
    "Slack ワークフローチャンネルID": v => /^C[A-Z0-9]+$/.test(String(v)),
    "Slack 飛びチャンネルID": v => /^C[A-Z0-9]+$/.test(String(v)),
    "面談時間（分）": v => Number(v) > 0,
    "スロット刻み（分）": v => Number(v) > 0,
    "CA判定 除外キーワード": v => true,  // v5.7+: 空欄を推奨（完全空きのみブッキング）
    // v5.7+: LG共通カレンダー廃止
    "CAユーザーグループID": v => /^S[A-Z0-9]+$/.test(String(v)),
  };
  Object.keys(required).forEach(key => {
    const val = cfg[key];
    const ok  = required[key](val);  // v5.7+: 空欄OKなキーもあるので val 前置きはしない
    result.push(`${ok ? "✅" : "❌"} 設定[${key}] = ${val || "(空)"}`);
  });

  // 2. 必須シート存在
  const requiredSheets = ["設定", "メンバー"];
  requiredSheets.forEach(name => {
    const sh = ss.getSheetByName(name);
    result.push(`${sh ? "✅" : "❌"} シート[${name}]`);
  });

  // 3. メンバーシート アクティブCA 全員のカレンダー書き込み可否
  {
    const cas = _caListRows()
      .filter(r => r[0] && r[1] && String(r[4] || "").trim() === "アクティブ")
      .map(r => ({ name: String(r[0]).trim(), calId: String(r[1]).trim() }));
    result.push(`--- アクティブCA ${cas.length}名 カレンダー権限 ---`);
    const probeStart = new Date(Date.now() + 60 * 60 * 1000);  // 1h後
    const probeEnd   = new Date(probeStart.getTime() + 60 * 1000);
    for (const ca of cas) {
      try {
        const ev = Calendar.Events.insert({
          summary: "🧪 prod readiness probe (auto-delete)",
          start: { dateTime: probeStart.toISOString(), timeZone: "Asia/Tokyo" },
          end:   { dateTime: probeEnd.toISOString(),   timeZone: "Asia/Tokyo" },
        }, ca.calId, { sendUpdates: "none" });
        Calendar.Events.remove(ca.calId, ev.id, { sendUpdates: "none" });
        result.push(`  ✅ ${ca.name}`);
      } catch(e) { result.push(`  ❌ ${ca.name}: ${String(e).slice(0, 80)}`); }
    }
  }

  // 4. Slack URL Token（本番ガード）
  const slackTok = (PropertiesService.getScriptProperties().getProperty("SLACK_URL_TOKEN") || "").trim();
  result.push(slackTok ? "✅ SLACK_URL_TOKEN セット済み (doPost 検証ON)" : "⚠️ SLACK_URL_TOKEN 未設定 (doPost 検証スキップ・本番前に必ず設定)");

  // 5. トリガー登録状況
  const trigNames = ScriptApp.getProjectTriggers().map(t => t.getHandlerFunction());
  const expectedTriggers = ["sendDailyReminders", "syncSalesforce", "renderAvailabilityCalendar", "updateLGDashboard", "remindStalledMeetings", "createMonthlyDigest", "onEditInstallable"];
  expectedTriggers.forEach(name => {
    result.push(`${trigNames.includes(name) ? "✅" : "❌"} トリガー[${name}]`);
  });

  Logger.log("=== 本番運用前バリデーション ===");
  result.forEach(line => Logger.log(line));
  Logger.log("===============================");

  // シートにも書き出し
  let outSh = ss.getSheetByName("_prod_readiness");
  if (!outSh) outSh = ss.insertSheet("_prod_readiness");
  outSh.clearContents();
  outSh.getRange(1, 1, result.length, 1).setValues(result.map(r => [r]));
  return result;
}

function setAllTriggers() {
  ScriptApp.getProjectTriggers().forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger("sendDailyReminders").timeBased().atHour(9).everyDays(1).create();
  ScriptApp.newTrigger("syncSalesforce").timeBased().everyHours(1).create();
  ScriptApp.newTrigger("renderAvailabilityCalendar").timeBased().everyMinutes(30).create();
  ScriptApp.newTrigger("updateLGDashboard").timeBased().everyMinutes(30).create();
  ScriptApp.newTrigger("remindStalledMeetings").timeBased().everyHours(1).create();
  // v5.7.2: 未確定面談の自動再マッチ (CA増員/枠空き対応・36時間以内)
  ScriptApp.newTrigger("autoRematchStalled").timeBased().everyHours(1).create();
  ScriptApp.newTrigger("createMonthlyDigest").timeBased().onMonthDay(1).atHour(0).create();
  ScriptApp.newTrigger("onEditInstallable")
    .forSpreadsheet(SpreadsheetApp.getActiveSpreadsheet())
    .onEdit()
    .create();
  Logger.log("トリガー設定完了 (v5.7)");
}

// ─────────────────────────────────────────
// ヘッダースタイル
// ─────────────────────────────────────────

function styleHeader(sheet, colCount) {
  sheet.getRange(1, 1, 1, colCount)
    .setBackground("#37474F").setFontColor("#FFFFFF")
    .setFontWeight("bold").setHorizontalAlignment("center");
}

// ─────────────────────────────────────────
// 日時ユーティリティ
// ─────────────────────────────────────────

function formatDate(dt)     { return (dt instanceof Date && !isNaN(dt)) ? `${dt.getFullYear()}/${String(dt.getMonth()+1).padStart(2,"0")}/${String(dt.getDate()).padStart(2,"0")}` : ""; }
function formatDatetime(dt) { return (dt instanceof Date && !isNaN(dt)) ? `${formatDate(dt)} ${formatTime(dt)}` : ""; }
function formatTime(dt)     { return (dt instanceof Date && !isNaN(dt)) ? `${String(dt.getHours()).padStart(2,"0")}:${String(dt.getMinutes()).padStart(2,"0")}` : ""; }
function formatDateJP(dt)   { return (dt instanceof Date && !isNaN(dt)) ? `${dt.getFullYear()}年${dt.getMonth()+1}月${dt.getDate()}日` : ""; }
