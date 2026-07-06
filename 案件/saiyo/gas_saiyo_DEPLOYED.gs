/**
 * Tokumori 採用管理シート — bound GAS 正本 v1 (Phase 1)
 * SpreadsheetId: 1dEGDtUAgoeWadUHorLMxhVr4BBNwyI01Gs2v6Pg834g
 *
 * 設計3原則:
 *  1) データ(設定/マスタ/面接)と表示(ダッシュボード)を分離。表示はGASが静的値で生成。
 *  2) 位置参照禁止 → headerIndex_() でヘッダー名から列を引く(並べ替え耐性)。
 *  3) ステージ・チャネルは 01_設定 の"行"。プルダウンは範囲参照で即時反映、表は🔄更新で再生成。
 *
 * Phase1: 00_README / 01_設定 / 10_候補者マスタ / 11_面接スケジュール / 21_中途ダッシュボード
 */

/* ============================== 定数 ============================== */

// TOKUMORI ブランドカラー
var C = {
  RED:    '#AF322C',  // TOKUMORI Red (アクセント=唯一の主役色)
  BLACK:  '#000000',  // TOKUMORI Black (表ヘッダー)
  WHITE:  '#FFFFFF',
  INK:    '#1A1A1A',  // 本文
  SUB:    '#6B6B6B',  // 補足
  ZEBRA:  '#F7F5F4',  // ゼブラ
  BORDER: '#D9D9D9'   // 罫線(枠囲いのみ)
};
// 表ヘッダーの共通トーン(白基調プレミアム・全タブ統一)。淡グレー地＋濃文字＋下罫。
var HEAD_BG = '#ECE9E4', HEAD_RULE = '#C9C4BC', BOX_LT = '#E4E0D8';

var SH = {
  README: '00_README', CONF: '01_設定',
  FLOW: '02_選考設計・社内体制', GOAL: '03_採用目標・月別ファネル', ENTRY: '04_エントリー目標管理',
  MASTER: '10_候補者マスタ', IV: '11_面接スケジュール',
  D_ALL: '20_統合ダッシュボード', D_MID: '21_中途', D_NEW: '22_新卒', D_BIZ: '23_業務委託', D_INT: '24_インターン',
  AN_CH: '30_チャネル分析', AN_JOB: '31_職種分析', NA: '40_ネクストアクション', CV: '50_履歴書管理', RP: '60_レポート出力',
  NOTE: '12_面接評価ノート', CSV: '09_CSV取込', MAIL: '07_メール設定', BRIEFWORK: '08_説明会テキストワーク',
  SURVEYCFG: '13_段階別アンケート設定', SURVEYLOG: '14_アンケート回答'
};
// コンサル設計タブのカテゴリ(04エントリー目標管理の集客カテゴリ)
var ENTRY_CATEGORIES = ['エージェント', 'ダイレクトリクルーティング', '媒体', 'リファラル', 'その他'];

var MASTER_COLS = [
  'candidate_id', '区分', '職種', 'チャネル',
  '氏名', '性別', '生年月日', '連絡先', '電話番号', '大学', '学部', '学科', '高校名',
  '応募日', '現ステージ', 'ステータス',
  '見送り辞退理由', '競合先', '採用担当RC', 'ネクストアクション', 'NA期限',
  '次回面接日時', '次回面接URL', '次回面接官', '内定日', '承諾日', '入社日',
  '履歴書リンク', '履歴書回収日', '職務経歴書リンク', '職務経歴書回収日', 'サンクス送信日', '評価メモ',
  '面接回数', '直近面接日', '直近面接官', '直近フェーズ', '総合評価', '最新評価'   // ← 11_から自動集計(集計専用)
];
// 回収対象の書類定義(履歴書・職務経歴書)。各=マスタのリンク列/回収日列。
var DOC_TYPES = [
  { key: '履歴書', link: '履歴書リンク', date: '履歴書回収日' },
  { key: '職務経歴書', link: '職務経歴書リンク', date: '職務経歴書回収日' }
];
var GENDERS = ['男性', '女性', 'その他'];

var IV_COLS = [
  'interview_id', 'candidate_id', '候補者名', '区分', '職種', 'ステージ',
  '予定日時', '面接URL', '面接官', '形式', 'ステータス', '結果', '評点', '評価メモ',
  '総合点', '評価明細', '判定'   // 評価エンジン: 加重総合(数値)/項目別JSON/合否(合・NG)
];

// 評価項目の既定セット(企業ごとに 01_設定 で編集可・行を足すだけで増やせる)。[項目名, 比重, 最低点(1-5)]
var EVAL_DEFAULT = [
  ['コミュニケーション', 1, 2], ['カルチャーマッチ', 1, 2], ['論理的思考力', 1, 2],
  ['問題解決力', 1, 2], ['ストレス耐性', 1, 2], ['専門スキル', 1, 2], ['熱意・主体性', 1, 2],
  ['リーダーシップ', 1, 1], ['成長意欲・学習力', 1, 2], ['誠実性・素直さ', 1, 2], ['チームワーク', 1, 1]
];
// 拡張カタログ(設定に「無効」で投入。企業がチェックで有効化 → 評価ノートに動的追加)。[項目, 比重, 最低点]
var EVAL_CATALOG = [
  ['主体性・自走力', 1, 0], ['協調性', 1, 0], ['達成意欲・成果志向', 1, 0], ['ビジネスマナー', 1, 0],
  ['プレゼンテーション力', 1, 0], ['傾聴力', 1, 0], ['数値・分析力', 1, 0], ['創造性・発想力', 1, 0],
  ['柔軟性・適応力', 1, 0], ['オーナーシップ', 1, 0], ['顧客志向', 1, 0], ['マネジメント力', 1, 0],
  ['育成・コーチング力', 1, 0], ['語学力(英語)', 1, 0], ['専門知識の深さ', 1, 0], ['行動力・実行力', 1, 0],
  ['自己認識・内省', 1, 0], ['志望度・入社意欲', 1, 0]
];
var EVAL_COL = 36;  // 01_設定 評価項目マスタ開始列(AJ)

var SEGMENTS  = ['中途', '新卒', '業務委託', 'インターン'];
// 選考ステージ名の候補カタログ(新卒/中途 全パターン対応)。01_設定 選考ステージ定義の「ステージ名」をプルダウン化し、
// 選択時に隣の「種別」を自動補完(onEdit)。種別=entry/screen/interview/task/offer/accept/join。不足はこの配列に追記。
var STAGE_TYPES = ['entry', 'screen', 'interview', 'task', 'offer', 'accept', 'join'];
// 名称は標準フロー(seedDefaults)と揃える(応募/書類/承諾/グループ面接/面談/トライアル/契約)＝既定行が候補に含まれ無効フラグが出ない。
var STAGE_CATALOG = [
  ['応募', 'entry'], ['会社説明会', 'entry'], ['説明会参加', 'entry'], ['説明選考会', 'screen'],
  ['エントリーシート提出', 'entry'], ['カジュアル面談', 'entry'], ['リクルーター面談', 'interview'],
  ['書類', 'screen'], ['適性検査・Webテスト', 'screen'], ['筆記試験', 'screen'],
  ['1dayインターン', 'task'], ['2daysインターン', 'task'], ['5daysインターン', 'task'], ['インターンシップ', 'task'],
  ['コーディングテスト', 'task'], ['技術課題・ワークサンプル', 'task'], ['トライアル', 'task'],
  ['グループディスカッション', 'interview'], ['グループワーク', 'interview'], ['グループ面接', 'interview'],
  ['一次面接', 'interview'], ['二次面接', 'interview'], ['三次面接', 'interview'],
  ['現場面接', 'interview'], ['技術面接', 'interview'], ['部門長面接', 'interview'],
  ['役員面接', 'interview'], ['社長面接', 'interview'], ['最終面接', 'interview'], ['面談', 'interview'],
  ['リファレンスチェック', 'screen'], ['オファー面談・条件面談', 'offer'],
  ['内定', 'offer'], ['契約', 'offer'], ['内定者面談・フォロー', 'offer'],
  ['承諾', 'accept'], ['入社', 'join']
];
var STAGE_CANDIDATES = STAGE_CATALOG.map(function (r) { return r[0]; });
var STATUSES  = ['進行中', '内定', '承諾', '入社', '見送り', '辞退'];
var REASONS   = ['スキル不一致', 'カルチャー不一致', '条件不一致', '辞退（他社決定）', '辞退（意欲低下）', '連絡不通', 'その他'];
var IV_FORMAT = ['オンライン', '来社'];
var IV_STATUS = ['予定', '実施済', '調整中', 'キャンセル'];
var IV_RESULT = ['通過', '見送り', '保留'];
var IV_SCORE  = ['S', 'A', 'B', 'C', 'D'];
var SCORE_MAP = { 'S': 5, 'A': 4, 'B': 3, 'C': 2, 'D': 1 };

// 区分別 ②進捗管理タブ: マスタ(共通=識別＋N〜AM)を正本に、区分専用タブで進捗＋区分固有の取得項目を名前単位で管理。
// ②上のマスタ作業ビュー列(MANAGE_VIEW)の編集は onEdit で候補者IDを引き当てマスタへ書き戻し同期(正本=マスタ)。
// 区分固有項目(SEG_FIELDS)とメモは②タブ側に保持(再生成時も候補者IDで保持＝buildBriefingWork_と同方式)。
var MANAGE_SUFFIX = '_進捗管理';
// マスタ参照(読取専用・②では編集しない文脈列)。直近フェーズ/総合評価は syncInterviewSummary_ が11_から自動集計で
// 上書きするため、②で編集しても次回更新で消える → 編集不可の自動列として扱う(同期対象から除外)。
var MANAGE_REF_COLS = ['職種', 'チャネル', '応募日', '直近フェーズ', '総合評価'];
// マスタ作業ビュー(②で編集→マスタへ同期。基本同名・自動集計列は含めない)
var MANAGE_VIEW_COLS = ['現ステージ', 'ステータス', '採用担当RC', 'ネクストアクション', 'NA期限',
  '内定日', '承諾日', '入社日', '見送り辞退理由'];
// 日付として往復させる作業ビュー列(同期時 parseDateLoose_)
var MANAGE_DATE_COLS = { 'NA期限': 1, '内定日': 1, '承諾日': 1, '入社日': 1 };
// 区分固有の標準取得項目(②保持・コード定数。P6で設定駆動化)
var SEG_FIELDS = {
  '中途': ['現年収', '希望年収', '現職企業', '現職役職', '転職理由', '経験年数', '稼働開始可能時期'],
  '新卒': ['卒業年度', '文理', '説明会参加状況', 'アンケート満足度', '志望度', 'インターン参加'],
  'インターン': ['学年', '就業可能曜日', '就業可能時間帯', '希望期間', '時給希望'],
  '業務委託': ['専門領域', '希望単価', '稼働可能工数', '契約形態', 'ポートフォリオURL'],
};
// ヨミ管理(採用確度)の入力項目。新卒=③専用タブ(buildYomi_)・他区分=②進捗管理に内包(segOwnExtra_)。
var YOMI_OWN = ['ヨミランク', '志望度合い', '競合状況', '想定承諾時期', 'クロージング状況', '懸念・ネック', '決め手'];
var YOMI_RANKS = ['S 確実', 'A 有力', 'B 五分', 'C 厳しい'];
// ②に内包する追加の②保持項目: 新卒以外はヨミ項目を②で管理(新卒は③ヨミ管理タブが別にある)
function segOwnExtra_(seg) { return (seg === '新卒') ? [] : YOMI_OWN; }
// 区分固有の取得項目: 01_設定❿で有効✓の項目を返す(設定駆動)。未設定/空ならSEG_FIELDS定数にフォールバック。
function segFields_(seg) {
  try {
    var out = confRead_('SEGFIELDS')
      .filter(function (r) { return String(r[0]).trim() === seg && (r[2] === true || String(r[2]).toUpperCase() === 'TRUE'); })
      .map(function (r) { return String(r[1]).trim(); }).filter(Boolean);
    if (out.length) return out;
  } catch (e) {}
  return SEG_FIELDS[seg] || [];
}

// WP13 エントリー方式 / WP4 CSV取込 / WP11 表示パネル
var ENTRY_METHODS = ['手入力', 'Googleフォーム', 'ATS-CSV取込'];
// 応募フォーム項目(設定駆動)。タイプ/対象区分/選択肢ソースの語彙。
var FORMFIELD_TYPES = ['短文', '長文', '選択', '日付', '数値'];
var FORMFIELD_SOURCES = ['自由', '職種', 'チャネル', '性別', '説明会日程'];
// フォーム項目名 → マスタ列のエイリアス(同名はそのまま)。説明会日程は特別扱い(11_イベント化)。
var FORMFIELD_ALIAS = { 'メールアドレス': '連絡先', '応募職種': '職種', 'お名前': '氏名' };
var CSV_COL = 41;    // 01_設定 CSV列マッピング開始列(AO)。[ATS列名, マスタ列名]
var PANEL_COL = 45;  // 01_設定 表示パネル開始列(AS)。[パネル, 有効, 表示順]
// マスタへ取り込めるフィールド(CSVマッピングの宛先候補)
var CSV_TARGETS = ['氏名', '姓', '名', '性別', '生年月日', '連絡先', '電話番号', '区分', '職種', '大学', '学部', '学科', '高校名', 'チャネル', '応募日', '現ステージ', 'ステータス', '競合先', '履歴書リンク', '評価メモ'];
// 詳細分析パネル定義(WP11): key=内部キー, label=設定表示名。レパートリーを拡充。
var PANELS = [
  { key: 'stepyield', label: '①ステージ間 歩留まり' },
  { key: 'monthly', label: '②月次コホート歩留まり' },
  { key: 'channel', label: '③チャネル別' },
  { key: 'job', label: '④職種別' },
  { key: 'reasons', label: '⑤見送り理由' },
  { key: 'chxmonth', label: '⑥チャネル×月' },
  { key: 'jobxmonth', label: '⑦職種×月' },
  { key: 'monthfunnel', label: '⑧月次ファネル' },
  { key: 'weekfunnel', label: '⑨週次ファネル' },
  { key: 'university', label: '⑩大学別' },
  { key: 'competitor', label: '⑪競合先別' },
  { key: 'rc', label: '⑫担当RC別' },
  { key: 'score', label: '⑬総合評価分布' },
  { key: 'gender', label: '⑭性別別' },
  { key: 'age', label: '⑮年齢別' },
  { key: 'yomi', label: '⑯ヨミ計測' }
];

// レポート項目定義(Phase10): key=内部キー, rep=対象レポート(月次/週次), label=設定表示名。
// 出す表を出力先(60タブ/Slack/Doc/メール)別にON/OFFする(PANELS同型)。日次は対象外(固定)。
var REPORT_ITEMS = [
  // 月次(経営向け)
  { key: 'm_summary', rep: '月次', label: '月次:全区分サマリ' },
  { key: 'm_funnel',  rep: '月次', label: '月次:区分別ファネル歩留まり' },
  { key: 'm_channel', rep: '月次', label: '月次:チャネル別CVR/CPA' },
  { key: 'm_mom',          rep: '月次', label: '月次:前月比サマリ(当月/前月/前月比)' },
  { key: 'm_channel_need', rep: '月次', label: '月次:経路別 必要エントリー数(1/CVR)' },
  { key: 'm_job_full',     rep: '月次', label: '月次:職種別 フル実績(全選考段)' },
  { key: 'm_emp_rc',       rep: '月次', label: '月次:雇用区分別・担当者別' },
  { key: 'm_insight', rep: '月次', label: '月次:所感(Good/課題/Risk)' },
  { key: 'm_chart',   rep: '月次', label: '月次:チャート(タブのみ)' },
  // 週次(担当者向け・タブ/Slackのみ)
  { key: 'w_move',     rep: '週次', label: '週次:今週の動き' },
  { key: 'w_upcoming', rep: '週次', label: '週次:来週の面接予定' },
  { key: 'w_todo',     rep: '週次', label: '週次:要対応(NA超過)' },
  { key: 'w_funnel',   rep: '週次', label: '週次:区分別ファネル現況' },
  { key: 'w_pace',     rep: '週次', label: '週次:今月目標進捗' }
];
// 出力先列のラベル(REPORTブロック header と対応)。週次はDoc/メール非対応。
var REPORT_DESTS = [
  { key: 'tab', label: '60タブ' }, { key: 'slack', label: 'Slack' },
  { key: 'doc', label: 'Doc' }, { key: 'mail', label: 'メール' }
];
// 週次が対応する出力先(これ以外は設定上 — 表示・描画で無視)
var REPORT_WEEKLY_DESTS = { tab: true, slack: true };

// 01_設定 レイアウトレジストリ(単一の正本)。書き手(buildSettings_)も読み手(各ヘルパー)もここを参照。
// 縦4バンド・3レーン構成 → 横スクロール解消。row=データ開始行/titleRow=黒タイトル帯/col,w=列範囲/max=確保行数。
// title行=row-2, ヘッダー行=row-1 (kv型は title=row-1・ヘッダーなし)。読み=confRead_(key) / 入力規則元=confSrc_(sh,key,off)。
var CONF_LAYOUT = {
  // ❶ 基本設定 (band1: group行1 / title行2 / data行3-4)  レーンA
  BASIC:  { col: 1,  w: 3, titleRow: 2,  row: 3,  max: 2,  type: 'kv', solo: true, hint: '会社名と入力方式を設定（下に入力）',
            title: '■ 基本設定', companyCell: [3, 2], methodCell: [4, 2] },
  // 使う区分  レーンB
  SEG:    { col: 8,  w: 4, titleRow: 2,  row: 4,  max: 4,  type: 'seg',  // max=SEGMENTS.length(固定)
            title: '■ 使う区分（有効✓＋書類回収の要否）', header: ['区分', '有効', '表示順', '書類回収'] },
  // ❷ 選考定義 (band2: group行13 / title行14 / header行15 / data行16-65)  A:F / H:L(チャネル候補マスタへ一本化=空) / O:R
  STAGE:  { col: 1,  w: 6, titleRow: 14, row: 16, max: 50, type: 'table',
            title: '■ 選考ステージ定義', header: ['区分', '順序', 'ステージ名', '種別', '目標通過率', '色'] },
  // CHAN は撤去(基本チャネル定義 → 右側「チャネル候補マスタ」に一本化)。confRead_('CHAN')=候補マスタ有効✓。
  // JOB は v9 で col15(O)→col8(H) へ移動(チャネル定義撤去後の隙間を詰める)。選考ステージ(A-F)の直後に配置。
  JOB:    { col: 8, w: 4, titleRow: 14, row: 16, max: 50, type: 'table',
            title: '■ 職種定義', header: ['職種名', '区分', '目標採用数', '備考'] },
  // ❸ 目標・メンバー (band3: group行68 / title行69 / header行70 / data行71-)  ※band2拡張で+12
  TARGET: { col: 1,  w: 5, titleRow: 69, row: 71, max: 24, type: 'table',
            title: '■ 区分別 採用目標', header: ['区分', '内定目標', '承諾目標', '入社目標', '対象期間'],
            primaryLabelCell: [69, 15], primaryCell: [70, 15] },  // 主要目標指標セレクタ(レーンC)
  MEMBER: { col: 8,  w: 5, titleRow: 69, row: 71, max: 24, type: 'table',
            title: '■ メンバー', header: ['氏名', '役割', 'メール', 'SlackユーザーID', '月次メール'] },
  // ❹ 評価・表示・連携 (band4: group行97 / title行98 / header行99 / data行100-)
  EVAL:   { col: 1,  w: 4, titleRow: 98, row: 100, max: 30, type: 'eval',
            title: '■ 評価項目（比重・最低点）', header: ['評価項目', '比重', '最低点', '有効'] },
  PANEL:  { col: 8,  w: 4, titleRow: 98, row: 100, max: 16, type: 'panel',  // max=PANELS.length(固定)
            title: '■ 表示パネル（ダッシュ表示＋レポート出力）', header: ['パネル', '有効', '表示順', 'レポート出力'] },
  CSV:    { col: 15, w: 2, titleRow: 98, row: 100, max: 30, type: 'csv',
            title: '■ CSV列マッピング(ATS→マスタ)', header: ['CSVの列名', 'マスタ項目'] },
  // ❺ 連携設定 (band5: group行131 / Slack=title132 / data134-)
  SLACK:  { col: 1,  w: 5, titleRow: 132, row: 134, max: 6, type: 'slack', asOfCell: [134, 8], solo: true,  // 既定4種別+2余裕
            hint: '配信種別ごとにチャネル/曜日/時刻を指定して、有効✓',
            title: '■ Slack配信（種別ごとにチャネル指定）', header: ['配信種別', 'チャネル(#名/ID)', '曜日/日', '時刻', '有効'] },
  // ❻ レポート項目 (band6: group行143 / title行144 / header行145 / data行146-)
  REPORT: { col: 1,  w: 6, titleRow: 144, row: 146, max: 14, type: 'report', solo: true,  // max=REPORT_ITEMS.length(固定)
            hint: '出す表をONにして、出力先（60タブ/Slack/Doc/メール）を選ぶ',
            title: '■ レポート項目（出す表をON＋出力先）',
            header: ['レポート項目', '60タブ', 'Slack', 'Doc', 'メール', '順'] },
  // ❼ 必要書類・回収 (band7: group行162 / title行163 / header行164 / data行165-)  区分×書類
  DOCS:   { col: 1,  w: 5, titleRow: 163, row: 165, max: 8, type: 'docs', solo: true,  // max=SEGMENTS×DOC_TYPES(固定)
            hint: '区分ごとに必要な書類と回収タイミングを設定（有効✓で回収管理）',
            title: '■ 必要書類・回収（区分ごとに必要な書類と回収タイミング）',
            header: ['区分', '書類', '回収タイミング', '回収ステージ', '有効'] },
  // ❽ 応募フォーム (band8: group行184 / title行185 / header行186 / data行187-)  レーンA=項目 / レーンB=説明会日程
  FORMFIELDS: { col: 1, w: 7, titleRow: 185, row: 187, max: 22, type: 'formfields',
            title: '■ 応募フォーム項目（Googleフォームを設定で生成）',
            header: ['項目名', 'タイプ', '必須', '対象区分', '選択肢ソース', '有効', '選択肢(選択型・改行/カンマ区切り)'] },
  BRIEF:  { col: 8, w: 4, titleRow: 185, row: 187, max: 30, type: 'brief',
            title: '■ 説明会日程（追記式・フォーム選択肢になる）',
            header: ['説明会日時', '場所/URL', '備考', '定員'] },
  // ❾ 説明会・アンケート (band9: group行218 / トグル219-220 / アンケート項目 title行222 / header223 / data224-)
  SURVEY: { col: 1, w: 4, titleRow: 222, row: 224, max: 20, type: 'survey',
            title: '■ 参加後アンケート項目（チェックでフォームに出す）',
            header: ['アンケート項目', 'タイプ', '必須', '有効'],
            briefWorkCell: [219, 2], surveyOnCell: [220, 2] },
  // ❿ 区分別 取得項目 (band10: group行247 / title248 / header249 / data250-)  ②進捗管理の区分固有項目を設定駆動化
  SEGFIELDS: { col: 1, w: 3, titleRow: 248, row: 250, max: 40, type: 'segfields', solo: true,
            hint: '②進捗管理タブに出す、区分固有の取得項目を定義（有効✓）',
            title: '■ 区分別 取得項目（②進捗管理タブの固有列・区分ごとに定義）', header: ['区分', '項目名', '有効'] }
};
// 書類の回収タイミング選択肢
var DOC_TIMINGS = ['エントリー時', '選考途中', '任意'];
// 参加後アンケートの既定項目 [項目名, タイプ, 必須, 有効]
var SURVEY_DEFAULT = [
  ['お名前', '短文', true, true],
  ['メールアドレス', '短文', true, true],
  ['説明会の満足度(5段階)', '選択', true, true],
  ['志望度(5段階)', '選択', true, true],
  ['印象に残った点', '長文', false, true],
  ['質問・相談したいこと', '長文', false, true],
  ['選考への参加希望', '選択', false, true]
];
// 5段階の汎用選択肢(タイプ「5段階」に注入)
var SURVEY_SCALE5 = ['5 とても高い', '4 高い', '3 普通', '2 低い', '1 とても低い'];
// 満足度スケール(タイプ「満足度」に注入)
var SURVEY_SATISFACTION = ['大変満足', '満足', '普通', 'やや不満', '不満'];
// 志望度スケール(タイプ「志望度」に注入)。%アンカー方式(元シートの当社との相性に準拠・文言は各社で編集可)
var SURVEY_ASPIRATION = ['120% 内定が出たら即承諾したい', '100% 第一志望群・優先して進みたい', '75% 方向性は合致・前向き', '50% 興味あり・これから理解を深めたい', '25% 様子見・志望度は低め'];
// 段階別アンケート設定タブの列＋既定(元シート 説明会テキストワーク／一次面接アンケート に準拠)。[対象段階,項目名,タイプ,必須,有効]。タイプ=5段階/満足度/志望度/短文/長文/選択
var SURVEYCFG_COLS = ['フォーム名', '項目名', 'タイプ', '必須', '有効', '選択肢(選択型・改行/カンマ区切り)'];
var SURVEY_TYPES = ['5段階', '満足度', '志望度', '短文', '長文', '選択', '順位', 'グリッド'];
// グリッド型(行=選択肢/列=評価)で列を省略したときの既定列(重要度5段階)
var SURVEY_GRID_COLS = ['とても重要', '重要', '普通', 'あまり重要でない', '重要でない'];
var SURVEY_STAGE_DEFAULT = [
  ['説明選考会', '本日の満足度', '満足度', true, true],
  ['説明選考会', '満足度をつけた理由', '長文', false, true],
  ['説明選考会', '当社との相性・志望度', '志望度', true, true],
  ['説明選考会', '就職活動を終えたい時期', '短文', false, true],
  ['説明選考会', '就職活動後に挑戦したいこと', '長文', false, true],
  ['一次面接', '担当面接官の名前', '短文', false, true],
  ['一次面接', '当社との相性・志望度', '志望度', true, true],
  ['一次面接', '上記をつけた理由', '長文', false, true],
  ['一次面接', '最も印象に残ったこと', '長文', false, true],
  ['一次面接', '気になっている点・もっと知りたいこと', '長文', false, true],
  ['一次面接', '就職活動の悩み', '長文', false, true],
  ['一次面接', '現在の志望度が高い企業(3つ)', '短文', false, true],
  // 順位/グリッド型の見本(DOTZの価値観ランキング相当)。選択肢列=順位は項目を改行/カンマ区切り、グリッドは「行 ｜ 列」。
  ['内定者アンケート', '大切にしたい価値観の順位（上位ほど重視）', '順位', false, true, '成長機会,裁量・自由度,給与・待遇,安定性,人間関係,理念への共感'],
  ['内定者アンケート', '当社の各魅力の重要度', 'グリッド', false, true, '事業の将来性,一緒に働く人,成長環境,待遇 ｜ とても重要,重要,普通,あまり重要でない'],
];
// アンケート回答ログタブの列
var SURVEYLOG_COLS = ['回答日時', '候補者ID', '氏名', '区分', 'フォーム名', '満足度', '志望度', '回答詳細'];
// グループ見出し帯(各バンド先頭・全幅の赤帯)
var CONF_BANDS = [
  { title: '❶ 基本設定',       row: 1,   col: 1, w: 18 },
  { title: '❷ 選考定義',       row: 13,  col: 1, w: 18 },
  { title: '❸ 目標・メンバー', row: 68,  col: 1, w: 18 },
  { title: '❹ 評価・表示・連携', row: 97, col: 1, w: 18 },
  { title: '❺ 連携設定（Slack配信）', row: 131, col: 1, w: 18 },
  { title: '❻ レポート項目',   row: 143, col: 1, w: 18 },
  { title: '❼ 必要書類・回収', row: 162, col: 1, w: 18 },
  { title: '❽ 応募フォーム',   row: 184, col: 1, w: 18 },
  { title: '❾ 説明会・アンケート', row: 218, col: 1, w: 18 },
  { title: '❿ 区分別 取得項目', row: 246, col: 1, w: 18 }
];
// v6でband3-9を+12行下げた。pre-v6(v2〜v5)バンド版から移行時、退避はこの旧位置で読む(データ保持)。
var PRE_V6 = {
  TARGET: { row: 59, col: 1, w: 5 }, MEMBER: { row: 59, col: 8, w: 5 },
  EVAL: { row: 88, col: 1, w: 4 }, PANEL: { row: 88, col: 8, w: 3 }, CSV: { row: 88, col: 15, w: 2 },
  SLACK: { row: 122, col: 1, w: 5 }, REPORT: { row: 134, col: 1, w: 6 }, DOCS: { row: 153, col: 1, w: 5 },
  FORMFIELDS: { row: 175, col: 1, w: 6 }, BRIEF: { row: 175, col: 8, w: 3 }, SURVEY: { row: 212, col: 1, w: 4 },
  asOfCell: [122, 8], primaryCell: [58, 15], briefWorkCell: [207, 2], surveyOnCell: [208, 2]
};
// 列幅(1-18)。レーンA=1-6 / gap7 / レーンB=8-12 / gap13,14 / レーンC=15-18。
var CONF_WIDTHS = { 1: 130, 2: 72, 3: 120, 4: 80, 5: 92, 6: 56, 7: 18,
                    8: 160, 9: 72, 10: 150, 11: 120, 12: 120, 13: 18, 14: 18,
                    15: 150, 16: 120, 17: 90, 18: 120 };
// 旧レイアウト(マイグレーション退避元)。confLayoutVer 未設定時はここから読み、新位置へ移す。
var OLD_LAYOUT = {
  STAGE: { row: 3, col: 1, w: 6 }, CHAN: { row: 3, col: 8, w: 5 }, JOB: { row: 3, col: 14, w: 4 },
  MEMBER: { row: 3, col: 19, w: 4 }, TARGET: { row: 3, col: 24, w: 5 }, SEG: { row: 3, col: 30, w: 3 },
  EVAL: { row: 3, col: 36, w: 4 }, CSV: { row: 3, col: 41, w: 2 }, PANEL: { row: 3, col: 45, w: 3 },
  companyCell: [8, 31], methodCell: [10, 31]
};
var CONF_LAYOUT_VER = 'v10-docstoggle';
var CONF_DATA_ROW = 3;   // 後方互換(旧コードの一部が参照)。新リーダーは CONF_LAYOUT.<key>.row を使う。
var CONF_MAX_ROW  = 60;  // 後方互換

/* ============================== メニュー ============================== */

// READMEレイアウト版。変更時にバンプすると、次にシートを開いた時 00_README が自動で一度だけカード版に再生成される。
var README_VER = 'v-manual-4';

function onOpen() {
  SpreadsheetApp.getUi().createMenu('採用')
    .addItem('ダッシュボードを更新', 'refreshAll')
    .addItem('ダッシュボード自動更新を設定（毎朝9時）', 'setRefreshTrigger')
    .addItem('面接評価を保存（12_ノート）', 'saveEvaluation')
    .addItem('レポートを生成', 'generateReports')
    .addItem('月次レポートをDoc出力', 'generateMonthlyDoc')
    .addItem('半期振り返りをスライド出力', 'generateHalfYearSlides')
    .addSeparator()
    .addItem('CSVファイルを取込（推奨）', 'showCsvImportDialog')
    .addItem('CSV貼付から取込（09_）', 'importCsv')
    .addItem('応募フォームを作成/更新（区分別）', 'createEntryForms')
    .addItem('参加後アンケートを作成/更新', 'createSurveyForm')
    .addItem('アンケート/フォームを作成・更新（任意名）', 'createStageSurveyForms')
    .addItem('媒体別 進捗シートを作成/更新（社内限定）', 'createAgentSheet')
    .addSeparator()
    .addSubMenu(SpreadsheetApp.getUi().createMenu('レポート配信')
      .addItem('週次レポートをSlackへ送信', 'slackSendWeekly')
      .addItem('月次レポートをSlackへ送信', 'slackSendMonthly')
      .addItem('日次（本日面接/要対応）をSlackへ送信', 'slackSendDaily')
      .addSeparator()
      .addItem('月次レポートをメール送信', 'sendMonthlyMail')
      .addSeparator()
      .addItem('Slack Bot Tokenを設定', 'setSlackToken')
      .addItem('自動配信を設定（Slack＋月次メール）', 'installSlackTriggers')
      .addItem('自動配信を解除', 'removeSlackTriggers'))
    .addSubMenu(SpreadsheetApp.getUi().createMenu('メール（応募者向け）')
      .addItem('サンクスメールを今すぐ送信', 'sendThanksNow')
      .addItem('リマインドを今すぐ送信', 'sendRemindersNow')
      .addItem('メール設定タブを開く', 'openMailSettings')
      .addSeparator()
      .addItem('AIで文面を下書き（Gemini）', 'draftMailWithAI')
      .addItem('AIキー(Gemini)を設定', 'setGeminiKey'))
    .addSeparator()
    .addItem('健全性チェック（自動修復）', 'healthCheckRun')
    .addItem('初期セットアップ / 再構築', 'setupAll')
    .addItem('初期化パスワードを設定', 'setCleanInitPassword')
    .addItem('クリーン初期化（白紙の雛形にする）', 'cleanInit')
    .addToUi();

  // README自動更新: レイアウト版が変わっていたら一度だけ 00_README を描き直す(メニューは生成済みなので失敗しても運用に影響しない)。
  try {
    if (PropertiesService.getDocumentProperties().getProperty('readmeVer') !== README_VER) buildReadme_();
  } catch (e) { console.error('README auto-render skipped: ' + e); }
}

function refreshAll() {
  syncNextInterview();
  syncInterviewSummary_();
  renderAllDashboards_();
  try { buildEntryTargets_(); } catch (e) { Logger.log('refreshAll buildEntryTargets_ error: ' + e); }  // 04 チャネル再同期＋実績再集計
  try { refreshChannelDropdown_(); } catch (e) { Logger.log('refreshAll refreshChannelDropdown_ error: ' + e); }
  try { applySegmentGrayout_(); } catch (e) { Logger.log('refreshAll applySegmentGrayout_ error: ' + e); }
  try { reorderTabs_(); } catch (e) { Logger.log('refreshAll reorderTabs_ error: ' + e); }
  toast_('全ダッシュボードを更新しました');
}

// 候補者マスタのチャネルプルダウンを confRead_('CHAN')(基本定義＋候補マスタ有効✓)で更新。🔄で反映。
function refreshChannelDropdown_() {
  var ms = ss_().getSheetByName(SH.MASTER); if (!ms) return;
  var mh = headerIndex_(ms.getRange(1, 1, 1, ms.getLastColumn()).getValues()[0]);
  if (mh['チャネル'] == null) return;
  var names = confRead_('CHAN').map(function (r) { return String(r[0]); }).filter(Boolean);
  if (names.length) setVL_(ms, mh['チャネル'] + 1, 500, names);
}

// 使う区分(enabledSegments_)に連動し、01_設定の区分別入力行のうち無効区分をグレーアウト(全区分有効ならグレーなし)。
// setupAll/refreshAll末で適用。reversible(有効行はnull=既定背景に戻す)。STAGE/JOB/TARGET/DOCS の区分行が対象。
function applySegmentGrayout_() {
  var sh = sheet_(SH.CONF), en = enabledSegments_(), L = CONF_LAYOUT, GRAY = '#ECECEC', WHITE = '#FFFFFF';
  function gray(key, segOff) {
    var b = L[key]; if (!b) return;
    var segs = sh.getRange(b.row, b.col + segOff, b.max, 1).getValues();
    var bgs = [];  // ブロック単位で1回 setBackgrounds(API呼び出しを最小化)
    for (var i = 0; i < b.max; i++) {
      var seg = String(segs[i][0] || '').trim();
      var color = (!seg || en.indexOf(seg) >= 0) ? WHITE : GRAY;  // 無効区分のみグレー
      var rowc = []; for (var j = 0; j < b.w; j++) rowc.push(color);
      bgs.push(rowc);
    }
    sh.getRange(b.row, b.col, b.max, b.w).setBackgrounds(bgs);
  }
  gray('STAGE', 0); gray('JOB', 1); gray('TARGET', 0); gray('DOCS', 0); gray('SEGFIELDS', 0);
  // 必要書類: 有効区分でも「書類回収」OFFの区分行はグレー(その区分は書類を集めない)
  try {
    var bd = L.DOCS, dsegs = sh.getRange(bd.row, bd.col, bd.max, 1).getValues();
    for (var di = 0; di < bd.max; di++) {
      var dseg = String(dsegs[di][0] || '').trim();
      if (dseg && en.indexOf(dseg) >= 0 && !docsEnabledForSeg_(dseg)) {
        sh.getRange(bd.row + di, bd.col, 1, bd.w).setBackground(GRAY);
      }
    }
  } catch (e) { console.error('docs grayout: ' + e); }
  try { applySingleSegmentMode_(sh, en); } catch (e) { console.error('singleSegmentMode: ' + e); }
}

// 連続する「非表示にすべき行」をまとめて hideRows(API最小化)。pred(i)=その行を隠すか。
function hideRunsIf_(sh, startRow, n, pred) {
  var run = 0;
  for (var i = 0; i <= n; i++) {
    var h = (i < n) && pred(i);
    if (h) { run++; }
    else if (run) { try { sh.hideRows(startRow + i - run, run); } catch (e) {} run = 0; }
  }
}

// 単一区分モード: 使う区分が1つだけのとき、01_設定の無効区分の行を非表示＋ステージ名を自由入力化。
// ⚠️ 01_設定はバンドが横に同居(STAGE↔JOB, TARGET↔MEMBER が同じ行)するため、行非表示は
//    「その行を共有する全バンドが無効区分 or 空」のときだけ実施(有効区分の職種/メンバーを巻き込まない)。
// 2区分以上のときは全行を再表示(可逆)。applySegmentGrayout_ の末尾から呼ばれる。
function applySingleSegmentMode_(sh, en) {
  var L = CONF_LAYOUT, single = en.length === 1;
  function off(v) { var s = String(v || '').trim(); return !s || en.indexOf(s) < 0; }   // 空 or 無効区分
  function dis(v) { var s = String(v || '').trim(); return s && en.indexOf(s) < 0; }     // 無効区分(非空)
  var lo = L.STAGE.row, hi = L.SEGFIELDS.row + L.SEGFIELDS.max;
  try { sh.showRows(lo, hi - lo); } catch (e) {}  // 一旦全表示(可逆・stale hidden回避)
  if (!single) return;
  // STAGE(colA区分) ↔ JOB(col I区分) 同居: 両方が off かつ どちらかが実無効 のときだけ隠す
  var n1 = L.STAGE.max;
  var stg = sh.getRange(L.STAGE.row, L.STAGE.col, n1, 1).getValues();
  var job = sh.getRange(L.JOB.row, L.JOB.col + 1, n1, 1).getValues();
  hideRunsIf_(sh, L.STAGE.row, n1, function (i) { return off(stg[i][0]) && off(job[i][0]) && (dis(stg[i][0]) || dis(job[i][0])); });
  // TARGET(colA区分) ↔ MEMBER(col H 氏名・非区分) 同居: TARGET無効 かつ メンバー空 のときだけ
  var n2 = L.TARGET.max;
  var tgt = sh.getRange(L.TARGET.row, L.TARGET.col, n2, 1).getValues();
  var mem = sh.getRange(L.MEMBER.row, L.MEMBER.col, n2, 1).getValues();
  hideRunsIf_(sh, L.TARGET.row, n2, function (i) { return dis(tgt[i][0]) && !String(mem[i][0] || '').trim(); });
  // DOCS(単独) / SEGFIELDS(単独): 無効区分の行をそのまま隠す
  [['DOCS', L.DOCS], ['SEGFIELDS', L.SEGFIELDS]].forEach(function (bk) {
    var b = bk[1], col = sh.getRange(b.row, b.col, b.max, 1).getValues();
    hideRunsIf_(sh, b.row, b.max, function (i) { return dis(col[i][0]); });
  });
  // ステージ名(STAGE列+2)プルダウン → 自由入力化(カスタムフローの「リスト外」警告を除去)
  try { sh.getRange(L.STAGE.row, L.STAGE.col + 2, L.STAGE.max, 1).clearDataValidations(); } catch (e) {}
}

var SEG_TAB = { '中途': SH.D_MID, '新卒': SH.D_NEW, '業務委託': SH.D_BIZ, 'インターン': SH.D_INT };

// 有効区分の区分別ダッシュボードのみ生成し、無効区分のタブは非表示。+ 20統合/30/31。
function renderAllDashboards_() {
  docsCacheClear_();  // SEG(書類回収)キャッシュをこの実行用に初期化(直前のsetupAllでSEG書換→最新を読む)
  var en = enabledSegments_();
  SEGMENTS.forEach(function (s) {
    var tab = SEG_TAB[s]; var sh = ss_().getSheetByName(tab); if (!sh) return;
    if (en.indexOf(s) >= 0) {
      try { sh.showSheet(); } catch (e) {}
      renderSegmentDash_(tab, s);
    } else {
      try { sh.hideSheet(); } catch (e) {}  // 最後の可視シートは隠せない→無視
    }
  });
  renderAllDash_();  // チャネル別/職種別は20統合のセクションに統合(旧30/31)
  // 50_書類回収: 書類回収ONの区分が1つでもあれば生成＋表示、全区分OFFなら非表示(書類管理を使わない運用)
  try {
    if (docsActive_()) { buildDocsTab_(); var cvsh = ss_().getSheetByName(SH.CV); if (cvsh) cvsh.showSheet(); }
    else { var cvsh2 = ss_().getSheetByName(SH.CV); if (cvsh2) { try { cvsh2.hideSheet(); } catch (e) {} } }
  } catch (e) { Logger.log('renderAllDashboards docs: ' + e); }
  // 区分別②進捗管理タブ: 有効区分は再生成(マスタ作業ビュー＋区分固有項目)、無効区分は非表示。
  // 新卒は3部構成: ②=説明会参加者のみ(説明会設定ON時のみ)・③ヨミ管理(有効時に常時)。
  var briefOn = false; try { briefOn = !!surveyConfig_().briefWork; } catch (e) {}
  var briefIds = briefOn ? briefingParticipantIds_() : null;
  SEGMENTS.forEach(function (s) {
    var enabled = en.indexOf(s) >= 0;
    if (s === '新卒') {
      var mName = manageName_('新卒');
      // 有効＋説明会ON時は生成＋表示(無効→有効に戻したとき隠れたままにしない)
      if (enabled && briefOn) { try { buildSegManage_('新卒', briefIds); var ms = ss_().getSheetByName(mName); if (ms) ms.showSheet(); } catch (e) { Logger.log('renderAllDashboards 新卒② error: ' + e); } }
      else { var m0 = ss_().getSheetByName(mName); if (m0) { try { m0.hideSheet(); } catch (e) {} } }
      var yName = yomiName_('新卒');
      if (enabled) { try { buildYomi_('新卒'); var ys = ss_().getSheetByName(yName); if (ys) ys.showSheet(); } catch (e) { Logger.log('renderAllDashboards ヨミ error: ' + e); } }
      else { var y0 = ss_().getSheetByName(yName); if (y0) { try { y0.hideSheet(); } catch (e) {} } }
    } else if (enabled) { try { buildSegManage_(s); var es = ss_().getSheetByName(manageName_(s)); if (es) es.showSheet(); } catch (e) { Logger.log('renderAllDashboards ' + s + '② error: ' + e); } }
    else { var msh = ss_().getSheetByName(manageName_(s)); if (msh) { try { msh.hideSheet(); } catch (e) {} } }
  });
  try { buildChannelMaster_(); } catch (e) {}  // チャネル候補マスタ(研究リスト・区分レーン・チェック式)
  // 旧タブ撤去: 30/31分析(→20統合)・08説明会テキストワーク(→新卒②へ統合)・旧読取専用名簿(_名簿)
  [SH.AN_CH, SH.AN_JOB, SH.BRIEFWORK, 'チャネル候補マスタ'].forEach(function (nm) {
    var t = ss_().getSheetByName(nm); if (t) { try { ss_().deleteSheet(t); } catch (e) {} }
  });
  ss_().getSheets().forEach(function (s2) { if (/_名簿$/.test(s2.getName())) { try { ss_().deleteSheet(s2); } catch (e) {} } });
}

// タブを論理順に整列(設定→データ→区分管理→ダッシュ→出力→ログ)。順序のみ・データ非破壊・冪等。
// 未作成タブはスキップ。非表示タブも一旦表示→移動→再非表示で正位置へ(使う区分で隠れた区分も再有効化に備える)。
// 未知タブ(媒体別 等)は order に無いので末尾に順序維持で自然に残る。setupAll/refreshAll末で呼ぶ。
function reorderTabs_() {
  var ss = ss_();
  var orig = null; try { orig = ss.getActiveSheet(); } catch (e) {}
  var order = [
    SH.README, SH.CONF, SH.FLOW, SH.GOAL, SH.ENTRY, SH.MAIL, SH.BRIEFWORK,
    '09_取込元データ', SH.CSV, SH.MASTER, SH.IV, SH.NOTE, SH.SURVEYCFG, SH.SURVEYLOG
  ];
  SEGMENTS.forEach(function (s) {
    order.push(manageName_(s));
    if (s === '新卒') order.push(yomiName_(s));
  });
  order = order.concat([
    SH.D_ALL, SH.D_MID, SH.D_NEW, SH.D_BIZ, SH.D_INT,
    SH.NA, SH.CV, SH.RP, '99_ヘルスログ'
  ]);
  var idx = 1, toHide = [];
  order.forEach(function (nm) {
    var sh = ss.getSheetByName(nm); if (!sh) return;
    var hid = false; try { hid = sh.isSheetHidden(); } catch (e) {}
    // 移動するにはアクティブ化が必要だが、アクティブシートは hideSheet できない。
    // よって一旦表示して移動し、隠すべきものは toHide に貯めて最後にまとめて隠す。
    if (hid) { toHide.push(sh); try { sh.showSheet(); } catch (e) {} }
    try { ss.setActiveSheet(sh); ss.moveActiveSheet(idx++); } catch (e) {}
  });
  // 安全な可視シート(設定/README=常時有効・toHide非該当)をアクティブにしてから再非表示
  var home = ss.getSheetByName(SH.CONF) || ss.getSheetByName(SH.README) ||
             (orig && !orig.isSheetHidden() ? orig : null);
  if (home) { try { ss.setActiveSheet(home); } catch (e) {} }
  toHide.forEach(function (sh) { try { sh.hideSheet(); } catch (e) {} });
}

function setupAll() {
  ss_().setSpreadsheetTimeZone('Asia/Tokyo');  // 日付の-9hズレ防止(スクリプトと表示TZを揃える)
  buildReadme_();
  buildSettings_();
  buildChannelMaster_();  // チャネル候補マスタ(右側)を先に生成→confRead_('CHAN')がbuildMaster_/04より前に有効✓を拾える
  buildMaster_();
  buildInterview_();
  buildEvalNote_();
  buildCsvTab_();
  try { buildSurveyConfigTab_(); } catch (e) {}  // 13 段階別アンケート設定(項目シード・入力保持)
  try { buildSurveyLogTab_(); } catch (e) {}     // 14 アンケート回答ログ(追記専用)
  buildMailTab_();      // 07 メール設定(サンクス/リマインド・build-if-empty)
  buildFlowDesign_();   // 02 選考設計・社内体制(版不一致or空で再構築・入力保持)
  buildGoalDesign_();   // 03 採用目標・月別ファネル
  buildEntryTargets_(); // 04 エントリー目標管理(構造生成＋実績自動)
  PropertiesService.getDocumentProperties().setProperty('designVer', DESIGN_VER);  // 設計タブ版を確定
  reservePlaceholders_();
  syncNextInterview();
  syncInterviewSummary_();
  renderAllDashboards_();
  renderReports_();
  try { reorderTabs_(); } catch (e) {}  // タブを論理順に整列
  // 自動送信ONなら配信トリガーを自動設置(冪等=installSlackTriggersが既存を削除して再作成)。コピー先でも自動でフックされる。
  try { if (mailConfig_().autoOn) installSlackTriggers(); } catch (e) { Logger.log('setupAll auto-trigger install error: ' + e); }
  toast_('セットアップ完了');
}

// 別名 (計画上の呼称)
function refreshSummaries() { refreshAll(); }

// レポート生成(メニュー: 📄 レポートを生成)
function generateReports() { renderReports_(); toast_('レポートを生成しました'); }

// サンプルデータを正しいTZで再投入する一回限りの保守関数(初期構築時のみ使用)
function reseedSampleData() {
  ss_().setSpreadsheetTimeZone('Asia/Tokyo');
  var m = sheet_(SH.MASTER);
  if (m.getLastRow() > 1) m.getRange(2, 1, m.getLastRow() - 1, m.getMaxColumns()).clearContent();
  seedMaster_(m);
  var iv = sheet_(SH.IV);
  if (iv.getLastRow() > 1) iv.getRange(2, 1, iv.getLastRow() - 1, iv.getMaxColumns()).clearContent();
  seedInterview_(iv);
  syncNextInterview();
  syncInterviewSummary_();
  buildEvalNote_();
  renderAllDashboards_();
  renderReports_();
  toast_('サンプルデータを再投入しました');
}

/* ============================== 共通ヘルパー ============================== */

function ss_() { return SpreadsheetApp.getActive(); }
function sheet_(name) {
  var ss = ss_();
  var sh = ss.getSheetByName(name);
  if (!sh) sh = ss.insertSheet(name);
  return sh;
}
function toast_(msg) { ss_().toast(msg, '採用管理', 4); }

// シートのグリッドを最低 rows×cols まで広げる(MCP作成シートは26列しかなく範囲外になるため)
function ensureGrid_(sh, rows, cols) {
  if (sh.getMaxColumns() < cols) sh.insertColumnsAfter(sh.getMaxColumns(), cols - sh.getMaxColumns());
  if (sh.getMaxRows() < rows) sh.insertRowsAfter(sh.getMaxRows(), rows - sh.getMaxRows());
}

// 会社名(01_設定 区分マスタ下の会社名セル AE8)。未設定なら Tokumori。タイトルやレポートに反映。
function companyName_() {
  try {
    var c = CONF_LAYOUT.BASIC.companyCell;
    var v = sheet_(SH.CONF).getRange(c[0], c[1]).getValue();
    var s = String(v || '').trim();
    return s || 'Tokumori';
  } catch (e) { return 'Tokumori'; }
}
// 会社名の生値(未設定なら'')。表示用companyName_と違いフォールバックしない=外向き送信のガード判定に使う。
function companyRaw_() {
  try { var c = CONF_LAYOUT.BASIC.companyCell; return String(sheet_(SH.CONF).getRange(c[0], c[1]).getValue() || '').trim(); }
  catch (e) { return ''; }
}
// 会社名未設定なら外向きアクション(フォーム/メール)を中止＋警告(他社コピーでの誤名義送信を防ぐ)。
function requireCompany_(action) {
  if (companyRaw_()) return true;
  var msg = '会社名が未設定です（01_設定 基本設定）。誤送信防止のため「' + (action || 'この操作') + '」を中止しました。会社名を入力してから再実行してください。';
  Logger.log('requireCompany_ blocked: ' + (action || ''));
  try { toast_(msg); } catch (e) {}
  try { SpreadsheetApp.getUi().alert(msg); } catch (e) {}
  return false;
}

// 有効な区分(01_設定 使う区分テーブルの有効✓)を表示順で返す。未設定なら全区分。
function enabledSegments_() {
  try {
    var rows = confRead_('SEG'); // 区分,有効,表示順
    var en = rows.filter(function (r) {
      var v = r[1]; return v === true || String(v).trim() === '✓' || String(v).toUpperCase() === 'TRUE';
    }).sort(function (a, b) { return (Number(a[2]) || 99) - (Number(b[2]) || 99); })
      .map(function (r) { return String(r[0]); });
    return en.length ? en : SEGMENTS.slice();
  } catch (e) { return SEGMENTS.slice(); }
}

// 区分ごとの「書類回収」要否(01_設定 使う区分テーブルの4列目✓)。列が無い旧シートは true(後方互換)。
// ⚠️実行内キャッシュ必須: docStats_/buildDocsTab_ が候補者1行ごとに呼ぶため、毎回SEGをシート読みすると
//   100名規模で数百回の読み取り=refreshAllが数分→タイムアウト。SEGは実行中に変わらないので1回読んで使い回す。
var _docsSegCache = null;
function docsEnabledForSeg_(seg) {
  try {
    if (!_docsSegCache) {
      _docsSegCache = {};
      confRead_('SEG').forEach(function (r) {  // [区分,有効,表示順,書類回収]
        var s = String(r[0]).trim(); if (!s) return;
        var v = r[3];
        _docsSegCache[s] = (v === '' || v == null) ? true : (v === true || String(v).trim() === '✓' || String(v).toUpperCase() === 'TRUE');
      });
    }
    var hit = _docsSegCache[String(seg).trim()];
    return (hit == null) ? true : hit;  // 未登録(旧シート/未知区分)=ON扱い
  } catch (e) { return true; }
}
// SEG/STAGEを書き換えた直後(setupAll/onEditの設定変更)に実行内キャッシュを捨てる。
function docsCacheClear_() { _docsSegCache = null; _segStagesCache = null; }
// いずれかの有効区分が書類回収ONか(50タブ生成/非表示の判定)。
function docsActive_() {
  try { return enabledSegments_().some(function (s) { return docsEnabledForSeg_(s); }); } catch (e) { return true; }
}

// 有効な評価項目(01_設定 評価項目マスタ)を返す。[{name,weight,min}]。未設定なら既定セット。
function evalItems_() {
  try {
    var rows = confRead_('EVAL'); // 項目,比重,最低点,有効
    var items = rows.filter(function (r) {
      var v = r[3]; return v === true || String(v).trim() === '✓' || String(v).toUpperCase() === 'TRUE';
    }).map(function (r) { return { name: String(r[0]), weight: Number(r[1]) || 1, min: Number(r[2]) || 0 }; });
    if (items.length) return items;
  } catch (e) {}
  return EVAL_DEFAULT.map(function (d) { return { name: d[0], weight: d[1], min: d[2] }; });
}
// 1-5平均 → S/A/B/C/D
function scoreToLetter_(v) {
  return v >= 4.5 ? 'S' : v >= 3.5 ? 'A' : v >= 2.5 ? 'B' : v >= 1.5 ? 'C' : 'D';
}
// エントリー方式(01_設定 AE10)。未設定なら手入力。
function entryMethod_() {
  try { var c = CONF_LAYOUT.BASIC.methodCell; var v = String(sheet_(SH.CONF).getRange(c[0], c[1]).getValue() || '').trim(); return v || '手入力'; }
  catch (e) { return '手入力'; }
}
// 有効な表示パネル(01_設定 表示パネル)をkey配列で返す(表示順)。未設定なら全パネル既定順。
function enabledPanels_() {
  try {
    var rows = confRead_('PANEL'); // パネル,有効,表示順
    var lab2key = {}; PANELS.forEach(function (p) { lab2key[p.label] = p.key; });
    var on = rows.filter(function (r) {
      var v = r[1]; return v === true || String(v).trim() === '✓' || String(v).toUpperCase() === 'TRUE';
    }).sort(function (a, b) { return (Number(a[2]) || 99) - (Number(b[2]) || 99); })
      .map(function (r) { return lab2key[String(r[0])]; }).filter(Boolean);
    return on.length ? on : PANELS.map(function (p) { return p.key; });
  } catch (e) { return PANELS.map(function (p) { return p.key; }); }
}
// レポート出力ONの詳細分析パネル(01_設定 表示パネルの「レポート出力」列)。表示順でkey配列。
function reportPanels_() {
  try {
    var rows = confRead_('PANEL');  // [パネル, 有効, 表示順, レポート出力]
    var lab2key = {}; PANELS.forEach(function (p) { lab2key[p.label] = p.key; });
    return rows.filter(function (r) { return confTrue_(r[3]); })
      .sort(function (a, b) { return (Number(a[2]) || 99) - (Number(b[2]) || 99); })
      .map(function (r) { return lab2key[String(r[0])]; }).filter(Boolean);
  } catch (e) { return []; }
}
// truthy判定(チェックボックス/✓/TRUE)
function confTrue_(v) { return v === true || String(v).trim() === '✓' || String(v).toUpperCase() === 'TRUE'; }
// レポート項目: rep(月次/週次) × dest(tab/slack/doc/mail) でONのkeyを表示順で返す。
// 設定空/例外時は当該repの全項目(消失防止フォールバック)。
function reportItemsOn_(rep, dest) {
  var destCol = { tab: 1, slack: 2, doc: 3, mail: 4 }[dest];
  function allOf() { return REPORT_ITEMS.filter(function (it) { return it.rep === rep; }).map(function (it) { return it.key; }); }
  try {
    var rows = confRead_('REPORT'); // 項目,60タブ,Slack,Doc,メール,順
    if (!rows.length) return allOf();
    var lab2 = {}; REPORT_ITEMS.forEach(function (it) { lab2[it.label] = it; });
    var repRows = rows.filter(function (r) { var it = lab2[String(r[0])]; return it && it.rep === rep; });
    if (!repRows.length) return allOf();  // ラベルずれ/未シード → 全項目(消失防止)
    return repRows.filter(function (r) { return confTrue_(r[destCol]); })
      .sort(function (a, b) { return (Number(a[5]) || 99) - (Number(b[5]) || 99); })
      .map(function (r) { return lab2[String(r[0])].key; });  // 行はあるが全OFF → [](意図的に出さない)
  } catch (e) { return allOf(); }
}
// 月次メール受信者(01_設定 メンバー: 月次メール✓ かつ 有効メール)を配列で返す。
function mailRecipients_() {
  try {
    return confRead_('MEMBER').filter(function (r) {
      return confTrue_(r[4]) && /.+@.+\..+/.test(String(r[2] || '').trim());
    }).map(function (r) { return String(r[2]).trim(); });
  } catch (e) { return []; }
}
// 必要書類設定 → {区分: {書類: {timing, reqStage, enabled}}}。01_設定 DOCSブロック。
function docsConfig_() {
  var cfg = {};
  try {
    confRead_('DOCS').forEach(function (r) {
      var seg = String(r[0]).trim(), doc = String(r[1]).trim();
      if (!seg || !doc) return;
      if (!cfg[seg]) cfg[seg] = {};
      cfg[seg][doc] = { timing: String(r[2] || '').trim(), reqStage: String(r[3] || '').trim(), enabled: confTrue_(r[4]) };
    });
  } catch (e) {}
  return cfg;
}
// curステージが targetステージ以降に到達しているか(区分の選考順)。targetが空/不明なら true(=既に対象)。
function stageReached_(seg, cur, target) {
  if (!target) return true;
  var names = segStages_(seg).map(function (s) { return s.name; });
  var ci = names.indexOf(String(cur).trim()), ti = names.indexOf(String(target).trim());
  if (ti < 0) return true;       // 回収ステージ名が未定義 → 常に対象扱い
  if (ci < 0) return false;      // 現ステージ不明 → 未到達扱い
  return ci >= ti;
}
// 1候補×1書類の状態。in-play=ステータスが見送り/辞退以外。
function docState_(row, H, seg, docDef, cfg) {
  var link = String(row[H[docDef.link]] || '').trim();
  var collected = !!link;
  var dcfg = (cfg[seg] && cfg[seg][docDef.key]) ? cfg[seg][docDef.key] : null;
  if (!dcfg || !dcfg.enabled || dcfg.timing === '任意') {
    return { collected: collected, target: false, due: false, label: collected ? '回収済' : '対象外' };
  }
  var target;
  if (dcfg.timing === 'エントリー時') target = true;
  else target = stageReached_(seg, row[H['現ステージ']], dcfg.reqStage);  // 選考途中
  var status = String(row[H['ステータス']] || '').trim();
  var inPlay = status !== '見送り' && status !== '辞退';
  var due = target && !collected && inPlay;
  return { collected: collected, target: target, due: due, label: collected ? '回収済' : (target ? '未回収' : '回収予定') };
}
// 書類回収率(全必要書類ベース)。segs=区分配列(省略=全有効区分)。{target,collected,rate}。
function docStats_(segs) {
  if (typeof segs === 'string') segs = [segs];
  var set = segs ? {} : null; if (segs) segs.forEach(function (s) { set[s] = true; });
  var cfg = docsConfig_(), am = allMaster_(), H = am.H, t = 0, c = 0;
  am.rows.forEach(function (r) {
    var seg = String(r[H['区分']] || '').trim();
    if (set && !set[seg]) return;
    if (!docsEnabledForSeg_(seg)) return;  // 書類回収OFFの区分は集計対象外(KPIは「—」表示に)
    var status = String(r[H['ステータス']] || '').trim();
    if (status === '見送り' || status === '辞退') return;
    DOC_TYPES.forEach(function (d) {
      var st = docState_(r, H, seg, d, cfg);
      if (st.target) { t++; if (st.collected) c++; }
    });
  });
  return { target: t, collected: c, rate: pct_(c, t) };
}

/* ============================== Slack配信 (WP24-26) ============================== */

// Bot Token は PropertiesService に秘匿(シートに置かない)
function slackToken_() { return String(PropertiesService.getDocumentProperties().getProperty('slackBotToken') || '').trim(); }
function setSlackToken() {
  var ui = SpreadsheetApp.getUi();
  var res = ui.prompt('Slack Bot Token 設定', 'xoxb- で始まる Bot Token を貼り付け（空欄でクリア）。現在: ' + (slackToken_() ? '設定済' : '未設定'), ui.ButtonSet.OK_CANCEL);
  if (res.getSelectedButton() !== ui.Button.OK) return;
  var t = String(res.getResponseText() || '').trim();
  PropertiesService.getDocumentProperties().setProperty('slackBotToken', t);
  toast_(t ? 'Slack Bot Tokenを保存しました' : 'Slack Bot Tokenをクリアしました');
}
// 配信種別 → {channel,day,time,enabled} (01_設定 Slack配信ブロック)
function slackTargets_() {
  var map = {};
  confRead_('SLACK').forEach(function (r) {
    var kind = String(r[0] || '').trim(); if (!kind) return;
    var on = (r[4] === true || String(r[4]).toUpperCase() === 'TRUE' || String(r[4]).trim() === '✓');
    map[kind] = { channel: String(r[1] || '').trim(), day: String(r[2] || '').trim(), time: String(r[3] || '').trim(), enabled: on };
  });
  return map;
}
function slackTargetByPrefix_(prefix) { var t = slackTargets_(); for (var k in t) { if (k.indexOf(prefix) === 0) return t[k]; } return null; }
// レポート基準日(空=今日)。東京壁時計フレームのDateで返す。
function reportAsOf_() {
  try {
    var ac = CONF_LAYOUT.SLACK.asOfCell, v = sheet_(SH.CONF).getRange(ac[0], ac[1]).getValue();
    if (v instanceof Date && !isNaN(v.getTime())) return new Date(v.getTime() + 9 * 3600 * 1000);
    var s = String(v || '').replace(/[\/.]/g, '-');
    var m = s.match(/(\d{4})-(\d{1,2})-(\d{1,2})/); if (m) return d_(Number(m[1]), Number(m[2]), Number(m[3]));
    var m2 = s.match(/(\d{4})-(\d{1,2})/); if (m2) return d_(Number(m2[1]), Number(m2[2]), 1);
  } catch (e) {}
  return nowTokyo_();
}
// chat.postMessage
function sendSlack_(channel, text) {
  var token = slackToken_();
  if (!token) { toast_('Slack Bot Token未設定（メニュー「Slack Bot Tokenを設定」）'); return false; }
  if (!channel) { toast_('配信チャネル未設定（01_設定 Slack配信）'); return false; }
  try {
    var res = UrlFetchApp.fetch('https://slack.com/api/chat.postMessage', {
      method: 'post', contentType: 'application/json; charset=utf-8',
      headers: { Authorization: 'Bearer ' + token },
      payload: JSON.stringify({ channel: channel, text: text, mrkdwn: true }), muteHttpExceptions: true
    });
    var ok = false, body = res.getContentText(); try { ok = JSON.parse(body).ok; } catch (e) {}
    if (!ok) console.error('Slack送信失敗: ' + body);
    return ok;
  } catch (e) { console.error('Slack送信例外', e); return false; }
}

// ---- レポート→mrkdwnテキスト(基準日 asOf を反映) ----
function slackMonthlyText_(asOf) {
  var n = asOf || reportAsOf_();
  var head = '*' + companyName_() + ' 採用 月次レポート ' + n.getUTCFullYear() + '年' + (n.getUTCMonth() + 1) + '月*';
  var keys = reportItemsOn_('月次', 'slack');
  if (!keys.length) return head + '\n（Slack配信項目が未設定／全OFF）';
  var Ms = enabledSegments_().map(function (s) { return computeSegment_(s); });
  var segRows = Ms.map(function (M) {
    if (!M.stageNames.length) return [M.seg, 0, 0, 0, 0, '—', '—', 0];
    var nf = normalizedFunnel_(M), fg = finalGoal_(M), pc = pace_(M, n), pg = pc.goals.length ? pc.goals[pc.goals.length - 1] : null;
    return [M.seg, nf.app, nf.offer, nf.fin, (fg ? fg.tgt : 0), (fg ? pct_(fg.act, fg.tgt) : '—'), (pg ? paceText_(pg) : '—'), (pg ? pg.forecast : 0)];
  });
  var frag = {
    m_summary: function () {
      return Ms.filter(function (M) { return M.stageNames.length; }).map(function (M) {
        var nf = normalizedFunnel_(M), fg = finalGoal_(M), pc = pace_(M, n), pg = pc.goals.length ? pc.goals[pc.goals.length - 1] : null;
        return '• *' + M.seg + '* 応募' + nf.app + ' / 確定 ' + nf.fin + '/' + (fg ? fg.tgt : 0)
          + '（達成' + (fg ? pct_(fg.act, fg.tgt) : '—') + (pg ? ' ・ペース' + paceText_(pg) + ' ・着地' + pg.forecast : '') + '）';
      });
    },
    m_funnel: function () {
      return ['_ファネル全体CVR（応募→確定）_'].concat(Ms.filter(function (M) { return M.stageNames.length && M.counts[0]; }).map(function (M) {
        var nf = normalizedFunnel_(M); return '• ' + M.seg + ' 応募' + nf.app + '→確定' + nf.fin + '（' + pct_(nf.fin, nf.app) + '）';
      }));
    },
    m_channel: function () {
      var ch = buildCrossChannel_();
      return ['_チャネル別（上位3）_'].concat(ch.rows.slice(0, 3).map(function (r) {
        return '• ' + r[0] + ' 応募' + r[1] + '→確定' + r[2] + '（CVR' + r[3] + ' / CPA' + r[5] + '）';
      }));
    },
    m_mom: function () {
      var cur = tokyoYM_(n), prev = prevYM_(cur), c = { app: 0, off: 0, acc: 0, join: 0 }, p = { app: 0, off: 0, acc: 0, join: 0 };
      Ms.forEach(function (M) { var a = milestoneMonth_(M, cur), b = milestoneMonth_(M, prev); ['app', 'off', 'acc', 'join'].forEach(function (k) { c[k] += a[k]; p[k] += b[k]; }); });
      function d(a, b) { var x = a - b; return (x > 0 ? '+' : '') + x; }
      return ['_前月比（全区分）_', '• 応募 ' + c.app + '（前月比' + d(c.app, p.app) + '） ・内定 ' + c.off + '（' + d(c.off, p.off) + '） ・承諾 ' + c.acc + '（' + d(c.acc, p.acc) + '）'];
    },
    m_channel_need: function () {
      var g = crossAgg_('チャネル'), keys = Object.keys(g).filter(function (k) { return g[k].off > 0; }).sort(function (a, b) { return (g[a].app / g[a].off) - (g[b].app / g[b].off); }).slice(0, 3);
      if (!keys.length) return ['_必要エントリー数_', '• 内定実績がまだないため算出不可'];
      return ['_必要エントリー数（内定1名あたり・効率上位3）_'].concat(keys.map(function (k) { var x = g[k]; return '• ' + k + ' 内定1名/約' + (Math.round(x.app / x.off * 10) / 10) + '応募（内定率' + pct_(x.off, x.app) + '）'; }));
    },
    m_insight: function () {
      var ins = insightsAll_(segRows), out = [];
      ins.good.slice(0, 3).forEach(function (t) { out.push('◎ ' + t); });
      ins.issue.slice(0, 3).forEach(function (t) { out.push('△ ' + t); });
      ins.risk.slice(0, 3).forEach(function (t) { out.push('⚠ ' + t); });
      return out;
    }
  };
  var lines = [head];
  keys.forEach(function (k) { if (frag[k]) lines = lines.concat(frag[k]()); }); // m_chartはSlack断片なし→skip
  return lines.join('\n');
}
function slackWeeklyText_(asOf) {
  var n = asOf || reportAsOf_(), anchor = tokyoDayMs_(n);
  var head = '*' + companyName_() + ' 採用 週次レポート（〜' + fmtD_(n) + '）*';
  var keys = reportItemsOn_('週次', 'slack');
  if (!keys.length) return head + '\n（Slack配信項目が未設定／全OFF）';
  var am = allMaster_(), H = am.H;
  function inDays(d, lo, hi) { if (!(d instanceof Date)) return false; var k = (tokyoDayMs_(d) - anchor) / 86400000; return k >= lo && k <= hi; }
  var app = 0, off = 0, acc = 0, joi = 0, todo = 0;
  am.rows.forEach(function (r) {
    if (inDays(r[H['応募日']], -6, 0)) app++;
    if (inDays(r[H['内定日']], -6, 0)) off++;
    if (inDays(r[H['承諾日']], -6, 0)) acc++;
    if (inDays(r[H['入社日']], -6, 0)) joi++;
    var na = r[H['NA期限']]; if (String(r[H['ステータス']]) === '進行中' && na instanceof Date && (tokyoDayMs_(na) - anchor) / 86400000 <= 0) todo++;
  });
  var iv = sheet_(SH.IV), ivd = iv.getDataRange().getValues(), ivH = headerIndex_(ivd.shift()), up = 0;
  ivd.forEach(function (r) { var dt = r[ivH['予定日時']]; if (String(r[ivH['ステータス']]) === 'キャンセル') return; if (inDays(dt, 1, 7)) up++; });
  var frag = {
    w_move: function () { return ['今週: 応募' + app + ' / 内定' + off + ' / 承諾' + acc + ' / 入社' + joi]; },
    w_upcoming: function () { return ['来週の面接予定: ' + up + '件']; },
    w_todo: function () { return ['要対応(NA期限超過): ' + todo + '件']; },
    w_funnel: function () {
      return ['_区分別ファネル現況（応募→確定）_'].concat(enabledSegments_().map(function (s) {
        var nf = normalizedFunnel_(computeSegment_(s));
        return '• ' + s + ' 応募' + nf.app + '→確定' + nf.fin + '（' + pct_(nf.fin, nf.app) + '）';
      }));
    },
    w_pace: function () {
      return enabledSegments_().map(function (s) {
        var pc = pace_(computeSegment_(s), n), pg = pc.goals.length ? pc.goals[pc.goals.length - 1] : null;
        return pg ? ('• ' + s + ' ' + pg.name + ' ' + pg.act + '/' + pg.tgt + '（' + pct_(pg.act, pg.tgt) + ' ペース' + paceText_(pg) + ' 着地' + pg.forecast + '）') : null;
      }).filter(Boolean);
    }
  };
  var lines = [head];
  keys.forEach(function (k) { if (frag[k]) lines = lines.concat(frag[k]()); });
  return lines.join('\n');
}
function slackDailyText_(asOf) {
  var n = asOf || reportAsOf_(), anchor = tokyoDayMs_(n);
  var iv = sheet_(SH.IV), ivd = iv.getDataRange().getValues(), ivH = headerIndex_(ivd.shift());
  var today = [];
  ivd.forEach(function (r) { var dt = r[ivH['予定日時']]; if (String(r[ivH['ステータス']]) === 'キャンセル') return; if (dt instanceof Date && tokyoDayMs_(dt) === anchor) today.push('  - ' + fmtDT_(dt) + ' ' + String(r[ivH['候補者名']]) + '（' + String(r[ivH['ステージ']]) + '/' + String(r[ivH['面接官']]) + '）'); });
  var am = allMaster_(), H = am.H, todo = [];
  am.rows.forEach(function (r) { if (String(r[H['ステータス']]) !== '進行中') return; var na = r[H['NA期限']]; if (na instanceof Date && (tokyoDayMs_(na) - anchor) / 86400000 <= 0) todo.push('  - ' + fmtD_(na) + ' ' + String(r[H['氏名']]) + '：' + String(r[H['ネクストアクション']])); });
  var lines = ['*' + companyName_() + ' 本日(' + fmtD_(n) + ')*', '面接 ' + today.length + '件'];
  if (today.length) lines = lines.concat(today.slice(0, 20));
  lines.push('要対応(NA期限超過) ' + todo.length + '件'); if (todo.length) lines = lines.concat(todo.slice(0, 20));
  return lines.join('\n');
}

// ---- 手動送信(メニュー) ----
function slackSendWeekly() { var t = slackTargetByPrefix_('週次'); if (!t || !t.enabled) { toast_('週次配信が無効（01_設定 Slack配信）'); return; } if (sendSlack_(t.channel, slackWeeklyText_(reportAsOf_()))) toast_('週次レポートをSlackへ送信しました'); }
function slackSendMonthly() { var t = slackTargetByPrefix_('月次'); if (!t || !t.enabled) { toast_('月次配信が無効（01_設定 Slack配信）'); return; } if (sendSlack_(t.channel, slackMonthlyText_(reportAsOf_()))) toast_('月次レポートをSlackへ送信しました'); }
function slackSendDaily() { var t = slackTargetByPrefix_('日次'); if (!t || !t.enabled) { toast_('日次配信が無効（01_設定 Slack配信）'); return; } if (sendSlack_(t.channel, slackDailyText_(reportAsOf_()))) toast_('日次をSlackへ送信しました'); }

// ---- 自動配信トリガー(WP25) ----
function installSlackTriggers() {
  removeSlackTriggers();
  ScriptApp.newTrigger('slackWeeklyAuto').timeBased().onWeekDay(ScriptApp.WeekDay.MONDAY).atHour(9).create();
  ScriptApp.newTrigger('slackMonthlyAuto').timeBased().onMonthDay(1).atHour(9).create();
  ScriptApp.newTrigger('slackDailyAuto').timeBased().everyDays(1).atHour(8).create();
  ScriptApp.newTrigger('healthDailyAuto').timeBased().everyDays(1).atHour(7).create();  // 健全性チェック(毎朝7時)
  ScriptApp.newTrigger('monthlyMailAuto').timeBased().onMonthDay(1).atHour(9).create();
  ScriptApp.newTrigger('thanksDailyAuto').timeBased().everyDays(1).atHour(8).create();      // エントリー当日サンクス
  ScriptApp.newTrigger('remindDailyAuto').timeBased().everyDays(1).atHour(8).create();      // イベント前リマインド
  ScriptApp.newTrigger('refreshAll').timeBased().everyDays(1).atHour(9).create();           // ダッシュボード自動更新(毎朝9時=グラフ画像も再生成)
  toast_('自動配信を設定しました（週次/月次/日次Slack・月次メール・サンクス/リマインド毎朝8時・ダッシュ更新毎朝9時。各テンプレ・有効分のみ）');
}
function removeSlackTriggers() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    var f = t.getHandlerFunction();
    if (f === 'slackWeeklyAuto' || f === 'slackMonthlyAuto' || f === 'slackDailyAuto' || f === 'monthlyMailAuto'
      || f === 'thanksDailyAuto' || f === 'remindDailyAuto' || f === 'healthDailyAuto' || f === 'refreshAll') ScriptApp.deleteTrigger(t);
  });
  toast_('自動配信トリガーを解除しました');
}
// ダッシュボード自動更新トリガー(毎朝9時)を単独で設定。グラフ画像の鮮度維持用。
function setRefreshTrigger() {
  ScriptApp.getProjectTriggers().forEach(function (t) { if (t.getHandlerFunction() === 'refreshAll') ScriptApp.deleteTrigger(t); });
  ScriptApp.newTrigger('refreshAll').timeBased().everyDays(1).atHour(9).create();
  toast_('ダッシュボード自動更新を設定しました（毎朝9時に再生成＝グラフ画像も最新化）');
}
function slackWeeklyAuto() { var t = slackTargetByPrefix_('週次'); if (t && t.enabled) sendSlack_(t.channel, slackWeeklyText_(nowTokyo_())); }
function slackMonthlyAuto() { var t = slackTargetByPrefix_('月次'); if (t && t.enabled) sendSlack_(t.channel, slackMonthlyText_(nowTokyo_())); }
function slackDailyAuto() { var t = slackTargetByPrefix_('日次'); if (t && t.enabled) sendSlack_(t.channel, slackDailyText_(nowTokyo_())); }
function monthlyMailAuto() { try { sendMonthlyMail_(nowTokyo_(), true); } catch (e) { Logger.log('monthlyMailAuto error: ' + e); } }
function thanksDailyAuto() { try { sendThanksAuto_(); } catch (e) { Logger.log('thanksDailyAuto error: ' + e); } }
function remindDailyAuto() { try { sendRemindersAuto_(); } catch (e) { Logger.log('remindDailyAuto error: ' + e); } }
// items=[{name,weight,min}], scores={name:1-5}。加重平均・総合letter・NG(最低点割れ)を算出。
function computeEval_(items, scores) {
  var sw = 0, ws = 0, ng = false, n = 0, detail = {};
  items.forEach(function (it) {
    var s = Number(scores[it.name]);
    if (!s) return;  // 未入力はスキップ
    detail[it.name] = s; n++;
    ws += s * it.weight; sw += it.weight;
    if (it.min && s < it.min) ng = true;
  });
  var avg = sw ? (ws / sw) : 0;
  return { avg: Math.round(avg * 10) / 10, letter: n ? scoreToLetter_(avg) : '', ng: ng, n: n, detail: detail };
}

// ヘッダー行(配列)→ {ヘッダー名: 列index(0始まり)}
function headerIndex_(headerRow) {
  var idx = {};
  for (var i = 0; i < headerRow.length; i++) idx[String(headerRow[i]).trim()] = i;
  return idx;
}
// 列番号(1始まり)→ A1記法の列レター
function colLetter_(n) { var s = ''; while (n > 0) { var m = (n - 1) % 26; s = String.fromCharCode(65 + m) + s; n = Math.floor((n - 1) / 26); } return s; }

// シート全体をクリーンアップ(結合解除→内容/書式クリア→グリッドOFF)。表示専用シートに使う。
function clearSheet_(sh) {
  sh.getCharts().forEach(function (c) { sh.removeChart(c); });  // 既存チャート削除(再描画で重複防止)
  // QuickChartの埋め込み画像も全消去。アンカー移動や単一区分モード(チャート非挿入)での取り残し(浮き画像)を防止。
  try { sh.getImages().forEach(function (im) { im.remove(); }); } catch (e) {}
  var rng = sh.getRange(1, 1, sh.getMaxRows(), sh.getMaxColumns());
  try { rng.breakApart(); } catch (e) {}
  try { sh.showColumns(1, sh.getMaxColumns()); } catch (e) {}  // 隠し列(チャート元データ)を戻す
  rng.clear();
  rng.clearDataValidations();       // 古いプルダウン残骸を除去(評価ノート等の再描画で重要)
  rng.clearNote();                  // メモ残骸も除去
  rng.setNumberFormat('General');   // 残存の%等の数値書式をリセット(再描画でレイアウトが変わるため)
  rng.setWrap(false);
  sh.setHiddenGridlines(true);
}

// テーブル読み取り: startRow,startCol から nCols 取得、先頭列が空になるまで。
function readTable_(sh, startRow, startCol, nCols) {
  var last = sh.getLastRow();
  var out = [];
  if (last < startRow) return out;
  var vals = sh.getRange(startRow, startCol, last - startRow + 1, nCols).getValues();
  for (var i = 0; i < vals.length; i++) {
    if (String(vals[i][0]).trim() === '') break;
    out.push(vals[i]);
  }
  return out;
}

// 01_設定 レジストリ経由の読み取り(位置参照を一元化 → 並び替えに強い)
function confRead_(key) {
  // チャネルは「候補マスタ(有効✓)」が唯一の定義元(基本ブロックband2は撤去・一本化)。
  if (key === 'CHAN') return chanFromMaster_();
  var L = CONF_LAYOUT[key];
  return readTable_(sheet_(SH.CONF), L.row, L.col, L.w);
}
// チャネル候補マスタの有効✓を稼働チャネルとして返す([名称,種別,コスト,有効,対象区分])。
// これで「有効✓」が04エントリー目標/候補者マスタのチャネルプルダウン/分析(crossAgg等)に反映される。
function chanFromMaster_() {
  try { return activeChannels_().map(function (c) { return [c.name, c.type, c.cost, true, c.seg]; }); }
  catch (e) { return []; }
}
// チャネル候補マスタ(01_設定の右側 CHMASTER_BASE_COL〜・3レーン)から 有効✓ のチャネルを返す。
function activeChannels_() {
  var sh = sheet_(SH.CONF), base = CHMASTER_BASE_COL, lanes = ['共通', '新卒', '中途'], laneW = 5;
  if (sh.getLastColumn() < base + 3) return [];
  var maxRows = 4; lanes.forEach(function (l) { if ((CHMASTER[l] || []).length + 4 > maxRows) maxRows = CHMASTER[l].length + 4; });
  var data = sh.getRange(4, base, maxRows, lanes.length * laneW).getValues(), out = [];
  data.forEach(function (r) {
    lanes.forEach(function (lane, li) {
      var c = li * laneW, nm = String(r[c] || '').trim(); if (!nm) return;
      var on = r[c + 3]; if (on === true || String(on).toUpperCase() === 'TRUE') out.push({ name: nm, type: String(r[c + 1] || ''), cost: r[c + 2], seg: lane });
    });
  });
  return out;
}
// 入力規則/書式の元となる1列レンジ(blockのdata範囲・col+off列)
function confSrc_(sh, key, off) { var L = CONF_LAYOUT[key]; return sh.getRange(L.row, L.col + (off || 0), L.max, 1); }

function pct_(n, d) { return (d && d > 0) ? Math.round((n / d) * 100) + '%' : '—'; }
function bar_(n, max, w) {
  w = w || 10;
  if (!max || max <= 0) return '';
  var k = Math.max(0, Math.min(w, Math.round((n / max) * w)));
  return repeat_('█', k) + repeat_('░', w - k);
}
function repeat_(s, n) { var o = ''; for (var i = 0; i < n; i++) o += s; return o; }
// 日付は Date.UTC で生成する。GASのsetValueはUTC基準でシリアライズするため、
// これで「指定した壁時計」がそのままセルに表示される(JST固定運用・DSTなし)。
function d_(y, m, day, hh, mm) { return new Date(Date.UTC(y, m - 1, day, hh || 0, mm || 0, 0)); }
// 時刻付き(面接等): 東京の壁時計 hh:mm を表す実インスタント(=UTC hh:mm から9h引く)。
// シート(東京TZ)で hh:mm にそのまま表示される。
function dt_(y, m, day, hh, mm) { return new Date(Date.UTC(y, m - 1, day, hh || 0, mm || 0, 0) - 9 * 3600 * 1000); }
// 月次比較用: 保存値(UTC壁時計)と整合する月キー
function ymKey_(dt) { return dt.getUTCFullYear() + '-' + ('0' + (dt.getUTCMonth() + 1)).slice(-2); }
// 「今」を東京壁時計のUTCフレームで取得(保存値と同じ土俵で月比較するため)
function nowTokyo_() { return new Date(Date.now() + 9 * 3600 * 1000); }
// 任意のDate(d_/dt_どちらでも)を東京カレンダー日の0時(ms)に丸める
function tokyoDayMs_(date) { var t = new Date(date.getTime() + 9 * 3600 * 1000); return Date.UTC(t.getUTCFullYear(), t.getUTCMonth(), t.getUTCDate()); }
// 東京基準で「今日から何日後か」(負=過去, 0=今日, 正=未来)
function daysFromToday_(date) { return (tokyoDayMs_(date) - tokyoDayMs_(new Date())) / 86400000; }
// 東京基準の年月キー(YYYY*100+月0始まり)
function tokyoYM_(date) { var t = new Date(date.getTime() + 9 * 3600 * 1000); return t.getUTCFullYear() * 100 + t.getUTCMonth(); }
function fmtD_(date) { return Utilities.formatDate(date, 'Asia/Tokyo', 'MM/dd'); }
function fmtDT_(date) { return Utilities.formatDate(date, 'Asia/Tokyo', 'MM/dd HH:mm'); }

/* ---------- 書式ヘルパー (DOTZ writeDynTable_ をブランド色に再スキン) ---------- */

// 赤帯タイトル(ブランドの顔)
// メインタイトル(プレミアムLight・細い赤罫): 白地＋黒太字＋下端の赤罫(アクセント)。赤ベタ塗りは廃止。
// opts.thin=true で01_設定グループ帯用の細い赤罫(SOLID)、既定はメインタイトル用の太い赤罫(SOLID_THICK)。
function bandTitle_(sh, row, c1, c2, text, opts) {
  opts = opts || {};
  var r = sh.getRange(row, c1, 1, c2 - c1 + 1);
  r.breakApart();
  r.merge().setValue(text)
    .setBackground(C.WHITE).setFontColor(C.BLACK)
    .setFontWeight('bold').setFontSize(13)
    .setVerticalAlignment('middle').setHorizontalAlignment('left');
  var style = opts.thin ? SpreadsheetApp.BorderStyle.SOLID : SpreadsheetApp.BorderStyle.SOLID_THICK;
  r.setBorder(null, null, true, null, null, null, C.RED, style);  // 下端=赤罫(唯一のアクセント)
  sh.setRowHeight(row, 36);
}

// プレミアムLightのセクション見出し(白地＋黒太字＋チャコール下罫・主タイトルより一段小さい)。startCol から span 列を結合。
function sectionHead_(sh, row, startCol, span, text) {
  var r = sh.getRange(row, startCol, 1, span); r.breakApart();
  r.merge().setValue(text).setBackground(C.WHITE).setFontColor(C.BLACK)
    .setFontWeight('bold').setFontSize(11)
    .setVerticalAlignment('middle').setHorizontalAlignment('left');
  r.setBorder(null, null, true, null, null, null, '#3A3A3A', SpreadsheetApp.BorderStyle.SOLID);  // 下端=チャコール罫
  sh.setRowHeight(row, 26);
}

// 長文の注記/説明/タイトルをマージして見やすく(B列からspan列・折返し・行高自動)。次の行を返す。
function note_(sh, row, span, text, opts) {
  opts = opts || {};
  var r = sh.getRange(row, 2, 1, span); r.breakApart();
  r.merge().setValue(text).setFontColor(opts.color || C.SUB).setFontSize(opts.size || 9)
    .setWrap(true).setVerticalAlignment('middle');
  if (opts.bold) r.setFontWeight('bold');
  var perRow = Math.max(8, span * 11);  // 1行あたり概算文字数(全角)
  var lines = Math.max(1, Math.ceil(String(text).length / perRow));
  sh.setRowHeight(row, Math.min(80, 22 + (lines - 1) * 16));
  return row + 1;
}

// KPIヒーロー(主役・プレミアムLight): items=[{label,value,accent}] を白カードで横並び。
// 小さなミュートのラベル＋特大の数値、カード上辺に赤アクセント罫(記憶に残る一点)。
// labelRow=ラベル, labelRow+1=数値。opts.big=true で一段目ヘッドラインを大型化。
function kpiHero_(sh, labelRow, items, startCol, width, opts) {
  opts = opts || {};
  startCol = startCol || 2; width = width || 3;
  var valSize = opts.big ? 36 : 24;
  var valH = opts.big ? 66 : 50;
  var c = startCol;
  for (var i = 0; i < items.length; i++) {
    var it = items[i];
    // ラベル(上段・小さくミュート・白地)
    var lab = sh.getRange(labelRow, c, 1, width); lab.breakApart();
    lab.merge().setValue(it.label).setBackground(C.WHITE).setFontColor(C.SUB)
      .setFontSize(opts.big ? 11 : 10).setFontWeight('bold')
      .setHorizontalAlignment('center').setVerticalAlignment('middle');
    // 数値(下段・特大)
    var val = sh.getRange(labelRow + 1, c, 1, width); val.breakApart();
    val.merge().setValue(it.value).setBackground(C.WHITE)
      .setFontColor(it.accent ? C.RED : C.INK).setFontSize(valSize).setFontWeight('bold')
      .setHorizontalAlignment('center').setVerticalAlignment('middle');
    // 白カード(細枠)＋上辺に赤アクセント罫
    sh.getRange(labelRow, c, 2, width).setBorder(true, true, true, true, false, false, C.BORDER, SpreadsheetApp.BorderStyle.SOLID);
    sh.getRange(labelRow, c, 1, width).setBorder(true, null, null, null, null, null, C.RED, SpreadsheetApp.BorderStyle.SOLID_THICK);
    c += width;
  }
  sh.setRowHeight(labelRow, opts.big ? 24 : 22);
  sh.setRowHeight(labelRow + 1, valH);
}

/* ---------- グラフ(QuickChart画像・黒×朱・データラベル) ---------- */
// FUSION月間Docと同品質: 横/縦棒＝データラベル・クリーン、ドーナツ＝ブランド配色＋ラベル。
// シート埋め込み純正チャート→QuickChart画像へ置換。範囲(1行目=ヘッダ/系列名)はそのまま流用。
var SQC_INK = '#1A1A1A', SQC_MUTED = '#8A8A8A', SQC_GRID = '#EEEEEE';
var SQC_SERIES = ['#AF322C', '#1A1A1A', '#8A8A8A', '#C77B74'];                 // 系列色(朱/黒/グレー/薄朱)
var PIE_COLORS = ['#AF322C', '#000000', '#6B6B6B', '#C77B74', '#9A9A9A', '#7A211C', '#404040', '#D9B3B0', '#BFBFBF'];

function _sqcImg_(config, w, h) {
  var url = 'https://quickchart.io/chart?width=' + (w || 470) + '&height=' + (h || 250) + '&format=png&v=4&c=' + encodeURIComponent(JSON.stringify(config));
  try {
    var r = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
    if (r.getResponseCode() !== 200) { Logger.log('QuickChart ' + r.getResponseCode()); return null; }
    return r.getBlob().setName('chart.png');
  } catch (e) { Logger.log('QuickChart err: ' + e); return null; }
}
// アンカー位置の旧画像を消してから挿入(再生成での画像累積を防止)
function _sqcInsert_(sh, blob, anchorRow, anchorCol) {
  if (!blob) return;
  try {
    sh.getImages().forEach(function (im) {
      var a = im.getAnchorCell();
      if (a && a.getRow() === anchorRow && a.getColumn() === anchorCol) im.remove();
    });
  } catch (e) {}
  sh.insertImage(blob, anchorCol, anchorRow);
}

function addColumnChart_(sh, range, anchorRow, anchorCol, title, w, h) {
  var vals = range.getValues();
  if (vals.length < 2) return;
  var header = vals[0];
  var rows = vals.slice(1);
  var labels = rows.map(function (r) { return String(r[0]); });
  var datasets = [];
  for (var c = 1; c < header.length; c++) {
    datasets.push({
      label: String(header[c]),
      data: rows.map(function (r) { return Number(r[c]) || 0; }),
      backgroundColor: SQC_SERIES[(c - 1) % SQC_SERIES.length], borderRadius: 4, borderSkipped: false,
    });
  }
  var config = {
    type: 'bar',
    data: { labels: labels, datasets: datasets },
    options: {
      plugins: {
        title: { display: true, text: title, color: SQC_INK, font: { size: 13, weight: 'bold' }, align: 'start' },
        legend: { position: 'top', align: 'end', labels: { color: SQC_INK, boxWidth: 10, font: { size: 11 } } },
        datalabels: { anchor: 'end', align: 'end', color: SQC_INK, font: { weight: 'bold', size: 10 } },
      },
      scales: { x: { grid: { display: false }, ticks: { color: SQC_INK, font: { size: 11 } } }, y: { beginAtZero: true, grid: { color: SQC_GRID }, ticks: { color: SQC_MUTED } } },
    },
  };
  _sqcInsert_(sh, _sqcImg_(config, w || 470, h || 250), anchorRow, anchorCol);
}
function addPieChart_(sh, range, anchorRow, anchorCol, title, w, h) {
  var vals = range.getValues();
  if (vals.length < 2) return;
  var rows = vals.slice(1);
  var labels = rows.map(function (r) { return String(r[0]); });
  var data = rows.map(function (r) { return Number(r[1]) || 0; });
  var config = {
    type: 'doughnut',
    data: { labels: labels, datasets: [{ data: data, backgroundColor: PIE_COLORS, borderColor: '#ffffff', borderWidth: 2 }] },
    options: {
      cutout: '58%',
      plugins: {
        title: { display: true, text: title, color: SQC_INK, font: { size: 13, weight: 'bold' }, align: 'start' },
        legend: { position: 'right', labels: { color: SQC_INK, font: { size: 11 } } },
        datalabels: { color: '#ffffff', font: { weight: 'bold', size: 11 } },
      },
    },
  };
  _sqcInsert_(sh, _sqcImg_(config, w || 430, h || 250), anchorRow, anchorCol);
}

// 黒ヘッダーの表。header=配列, rows=2D。戻り=次の空き行。
function table_(sh, row, col, header, rows, redCols) {
  var w = header.length;
  sh.getRange(row, col, 1, w).setValues([header])
    .setBackground(HEAD_BG).setFontColor(C.INK).setFontWeight('bold').setFontSize(10)
    .setHorizontalAlignment('center').setVerticalAlignment('middle')
    .setBorder(null, null, true, null, null, null, HEAD_RULE, SpreadsheetApp.BorderStyle.SOLID);  // 下罫(白基調統一)
  sh.setRowHeight(row, 26);
  if (rows.length) {
    var dr = sh.getRange(row + 1, col, rows.length, w);
    dr.setValues(rows).setFontColor(C.INK).setFontSize(10).setVerticalAlignment('middle').setWrap(true);
    var bgs = [];
    for (var i = 0; i < rows.length; i++) {
      var line = [];
      for (var j = 0; j < w; j++) line.push(i % 2 === 1 ? C.ZEBRA : C.WHITE);
      bgs.push(line);
    }
    dr.setBackgrounds(bgs);
    if (redCols) {
      for (var k = 0; k < redCols.length; k++) {
        sh.getRange(row + 1, col + redCols[k], rows.length, 1).setFontColor(C.RED).setFontWeight('bold');
      }
    }
  }
  sh.getRange(row, col, rows.length + 1, w)
    .setBorder(true, true, true, true, true, true, C.BORDER, SpreadsheetApp.BorderStyle.SOLID);
  return row + rows.length + 2;
}

/* ============================== 00_README ============================== */

// 00_スタートガイド: 4フェーズ導線＋各タブへのリンク(WP33)
function tabLink_(name, label) {
  var t = ss_().getSheetByName(name);
  if (!t) return '"' + (label || name) + '"';
  return '=HYPERLINK("#gid=' + t.getSheetId() + '","▸ ' + (label || name) + '")';
}
function buildReadme_() {
  var sh = sheet_(SH.README);
  // 立ち上げチェックリスト(ラベル=状態保持キー)。再生成を跨いでチェック状態を保持する。
  var CHECKLIST = [
    '使う区分を選んだ（採用する区分だけ有効に）',
    '選考ステージを確認・調整した（標準フローが入っています）',
    '職種を入力した',
    '採用目標を入力した（03_採用目標）',
    'メニュー「初期セットアップ / 再構築」を実行した',
    'エントリー方式を決めた（手入力 / フォーム / CSV）',
    'Slack・メールの配信を設定した（任意）',
    'テスト候補者を1件入れて、ダッシュボードを確認した'
  ];
  // 既存READMEのチェック状態をラベルで退避(clearSheet_前に読む)→再生成後に復元
  var checkState = {};
  try {
    var last0 = sh.getLastRow();
    if (last0 >= 1) {
      var prev = sh.getRange(1, 2, last0, 8).getValues();  // B〜I
      for (var p = 0; p < prev.length; p++) {
        var plbl = String(prev[p][1] || '').trim();        // C列=ラベル
        if (CHECKLIST.indexOf(plbl) >= 0) checkState[plbl] = (prev[p][0] === true);  // B列=チェック
      }
    }
  } catch (e0) {}

  clearSheet_(sh);
  sh.setColumnWidth(1, 28);                                // A=左余白(呼吸)
  sh.setColumnWidth(2, 188);                               // B=見出し/チェック
  for (var c = 3; c <= 9; c++) sh.setColumnWidth(c, 120);  // C〜I=本文

  var co = String(companyName_() || '').trim();
  var row = 2;
  // READMEの黒帯ヘッダは本文・表と同じ B〜I 幅で描く(共有sectionBand_はB〜Mで広く、表と右端が揃わないため)
  // セクション見出し=赤帯でダッシュボードと統一(ブランドの顔)。B〜I幅で表と右端を揃える。
  function band_(r, text) {
    var rr = sh.getRange(r, 2, 1, 8); rr.breakApart();
    rr.merge().setValue('■ ' + text).setBackground(C.WHITE).setFontColor(C.BLACK).setFontWeight('bold').setFontSize(11).setVerticalAlignment('middle');
    rr.setBorder(null, null, true, null, null, null, '#3A3A3A', SpreadsheetApp.BorderStyle.SOLID);  // 下端=チャコール罫
    sh.setRowHeight(r, 28);
  }
  // ── ヒーロー(表紙=社名大見出し・余白を効かせる) ──
  bandTitle_(sh, row, 2, 9, (co ? co + '　' : '') + '採用管理シート');
  sh.getRange(row, 2, 1, 8).setFontSize(20);   // 社名を大見出しに(プレミアムな表紙)
  sh.setRowHeight(row, 60); row++;
  sh.setRowHeight(row, 8); row++;                // 余白(細いスペーサー)
  row = note_(sh, row, 8, '採用の設計から日々の運用まで、この1枚で完結します。はじめての方は、下の STEP1 → STEP5 を上から順に進めれば立ち上げ完了です。', { color: C.INK, size: 11 });
  row++;

  // ── 概要：このシートでできること＋データの流れ ──
  band_(row, 'このシートでできること（全体像）'); row++;
  row = note_(sh, row, 8, '・候補者を一元管理し、選考の進み（ファネル）・採用目標の達成度・チャネル別の成果を自動で可視化します。\n・中途／新卒／業務委託／インターンを「使う区分」で出し分け（1社1区分でも複数区分でもOK）。\n・レポートはSlackやメールへ自動配信。応募フォームやアンケートもこのシートから作れます。\n・主な利用者＝採用担当（日々の入力・進捗管理）と 経営／責任者（目標vs実績のレビュー）。', { color: C.INK, size: 10 });
  // データの流れ(横一本の帯で図示)
  var flow = '【データの流れ】　① 候補者を入力（10_候補者マスタ／応募フォーム／CSV取込）　→　② 選考を記録（11_面接・12_評価・(区分)_進捗管理）　→　③ システムが自動で集計　→　④ ダッシュボードで見る（20_統合）　→　⑤ レポートで共有（60／Slack／メール）';
  var fr = sh.getRange(row, 2, 1, 8); fr.breakApart();
  fr.merge().setValue(flow).setBackground('#FFF3F2').setFontColor(C.INK).setFontSize(10).setFontWeight('bold').setWrap(true).setVerticalAlignment('middle');
  sh.getRange(row, 2, 1, 8).setBorder(true, true, true, true, false, false, C.RED, SpreadsheetApp.BorderStyle.SOLID);
  sh.setRowHeight(row, 50); row++;
  row = note_(sh, row, 8, '正本（おおもと）は 10_候補者マスタ です。(区分)_進捗管理 で進捗を編集すると自動でマスタへ反映され、ダッシュボードやレポートは常にマスタを基準に作られます。', { color: C.SUB, size: 9 });
  row++;

  // ── タブの役割マップ(3分類) ──
  band_(row, 'タブの役割マップ ── ［入力］あなたが入れる ／ ［自動］システムが作る（触らない）'); row++;
  var mapStart = row;
  [
    ['① 設定する\n（最初に組む）', '00_README（この画面）／ 01_設定［入力→自動展開］／ 07_メール設定［入力］'],
    ['② 毎日入力する', '10_候補者マスタ［入力］／ 11_面接スケジュール［自動追記］／ 12_面接評価ノート［入力］／ (区分)_進捗管理［入力→マスタ同期］／ 新卒_ヨミ管理［入力］'],
    ['③ 自動で見る\n（手編集しない）', '20_統合ダッシュボード〜24_区分別［自動］／ 50_履歴書管理［自動］／ 60_レポート出力［自動］']
  ].forEach(function (r) {
    sh.getRange(row, 2).setValue(r[0]).setFontColor(C.BLACK).setFontWeight('bold').setFontSize(10).setVerticalAlignment('middle').setWrap(true);
    var rc = sh.getRange(row, 3, 1, 7); rc.breakApart();
    rc.merge().setValue(r[1]).setFontColor(C.INK).setFontSize(10).setWrap(true).setVerticalAlignment('middle');
    sh.setRowHeight(row, 38); row++;
  });
  sh.getRange(mapStart, 2, row - mapStart, 8).setBorder(true, true, true, true, true, true, C.BORDER, SpreadsheetApp.BorderStyle.SOLID);
  row++;

  // ── 立ち上げ手順(操作レベルで超具体・誰でもこの通りで完成) ──
  band_(row, '立ち上げ手順 ── STEP1 → STEP5 を上から順に（この通りで完成）'); row++;
  // 各STEPを枠付きカードで描く: 左=赤いSTEP番号バッジ / 右=タイトル+番号付き操作リスト+タブリンク。instrは改行で操作を区切る。
  function step_(n, title, instr, links) {
    var r0 = row;
    var tr = sh.getRange(row, 3, 1, 7); tr.breakApart();
    tr.merge().setValue(title).setFontColor(C.BLACK).setFontWeight('bold').setFontSize(11).setVerticalAlignment('middle');
    sh.setRowHeight(row, 26); row++;
    var ir = sh.getRange(row, 3, 1, 7); ir.breakApart();
    ir.merge().setValue(instr).setFontColor(C.INK).setFontSize(10).setWrap(true).setVerticalAlignment('top');
    var lines = 0; String(instr).split('\n').forEach(function (s) { lines += Math.max(1, Math.ceil(s.length / 52)); });
    sh.setRowHeight(row, Math.min(260, 20 + lines * 16)); row++;
    for (var i = 0; i < (links ? links.length : 0); i++) {
      sh.getRange(row, 3 + i).setFormula(tabLink_(links[i][0], links[i][1])).setFontColor('#1155CC').setFontSize(10).setFontWeight('bold');
    }
    sh.setRowHeight(row, 24); row++;
    var bc = sh.getRange(r0, 2, row - r0, 1); bc.breakApart();
    bc.merge().setValue('STEP\n' + n).setBackground('#FFF3F2').setFontColor(C.RED).setFontWeight('bold').setFontSize(13)
      .setHorizontalAlignment('center').setVerticalAlignment('middle').setWrap(true);
    sh.getRange(r0, 2, row - r0, 8).setBorder(true, true, true, true, false, false, C.BORDER, SpreadsheetApp.BorderStyle.SOLID);
    sh.getRange(r0, 2, row - r0, 1).setBorder(null, null, null, true, null, null, C.RED, SpreadsheetApp.BorderStyle.SOLID);
    row++;  // カード間スペーサー
  }
  step_(1, '使う区分と選考フローを決める（01_設定 ❶❷）',
    '① 01_設定 タブを開く（右上の「設定ナビ」から各設定へジャンプできます。◎＝必須）\n② ❶基本設定：B3 に会社名を入力\n③ ❶使う区分：採用する区分の「有効」列に ✓（使わない区分は空欄→そのタブは自動で隠れます）。表示順で並びを調整。さらに『書類回収』列で 履歴書/職経を集める区分だけ ✓（新卒など不要なら外す）\n④ ❷選考ステージ定義：区分ごとに 順序(1,2,3…)／ステージ名（セルのプルダウンから選択）／目標通過率%（例 80%）を確認・調整（標準フロー入り。不要な段は行を削除、足りない段は行を追加）\n⑤ ❷職種定義：職種名／区分／目標採用数 を入力',
    [[SH.CONF, '01_設定']]);
  step_(2, '目標・評価・必要書類を設定（01_設定 ❸❹❼ ＋ 03/04）',
    '① ❸採用目標：区分ごとに 内定／承諾／入社 の目標数と対象期間（例 2026-06）を入力。右の「主要目標指標」で主役（入社/承諾/内定）を選択\n② ❸メンバー：氏名／役割／メール／SlackユーザーID（「月次メール受信」ONの人へ月次が届く）\n③ ❹評価項目：面接の評価軸 項目名／比重／最低点／有効（加重平均で S〜D 判定）\n④ ❼必要書類：上の『書類回収』を ✓ にした区分だけ 書類／回収タイミング／有効 を設定（OFFの区分は灰色＝設定不要）\n⑤ 03_採用目標 で月別ファネル、04_エントリー目標 でチャネル別の応募目標を入力',
    [[SH.CONF, '01_設定'], [SH.GOAL, '03_採用目標'], [SH.ENTRY, '04_エントリー目標']]);
  step_(3, '入口（エントリー）・アンケート・配信を設定（01_設定 ❺❻❽❾ ＋ 07/13）',
    '① エントリー方式に応じて：CSV取込なら ❹CSV列マッピング、Googleフォームなら ❽応募フォーム項目 を設定 →メニュー「応募フォームを作成/更新」\n② ❾説明会：説明会日時を追記（フォームの選択肢になります）。説明会テキストワーク／参加後アンケートの作成ON/OFF\n③ アンケートを作る：13_段階別アンケート設定 に フォーム名／項目／タイプ／選択肢。タイプは 5段階/満足度/志望度/短文/長文/選択 に加え 順位・グリッド も可（価値観ランキング等）→メニュー「アンケート/フォームを作成・更新（任意名）」\n④ 配信：❺Slack配信・❻レポート項目・07_メール設定（サンクス／リマインドのテンプレ。下部「段階別リマインド設定」でステージごとに日数・文面を変更可）を入力\n⑤ 自動で送るなら メニュー「自動配信を設定」',
    [[SH.CONF, '01_設定'], [SH.MAIL, '07_メール設定'], [SH.SURVEYCFG, '13_アンケート設定']]);
  step_(4, 'セットアップを実行してタブを生成',
    '① 01_設定 の入力が終わったら、メニュー「採用」＞「初期セットアップ / 再構築」を実行\n② 「使う区分」と各設定に従って、必要なタブ（ダッシュボード／(区分)_進捗管理／書類回収 等）が自動生成・整列されます\n③ あとで設定を変えたら、同じメニューを再実行（または「ダッシュボードを更新」）で反映されます',
    [[SH.CONF, '01_設定']]);
  step_(5, '本番運用 ── 入力して可視化・共有',
    '① 候補者を 10_候補者マスタ に入力（または CSV取込／フォームから自動追記）\n② 面接は 12_面接評価ノート で記録（11_面接スケジュールへ自動追記）。日々の進捗は (区分)_進捗管理 で更新 → マスタへ自動同期\n③ 20_統合ダッシュボード で 進捗・達成率・ファネルを確認\n④ 60_レポート出力 や Slack／メールでチームに共有',
    [[SH.MASTER, '10_候補者マスタ'], [SH.IV, '11_面接'], [SH.D_ALL, '20_ダッシュ'], [SH.RP, '60_レポート']]);

  // ── 立ち上げチェックリスト（記憶に残る一点・状態保持） ──
  band_(row, '立ち上げチェックリスト ── 順にチェックすれば抜け漏れなし'); row++;
  var clStart = row;
  CHECKLIST.forEach(function (label) {
    var cb = sh.getRange(row, 2); cb.insertCheckboxes(); cb.setValue(checkState[label] === true);
    var lc = sh.getRange(row, 3, 1, 7); lc.breakApart();
    lc.merge().setValue(label).setFontColor(C.INK).setFontSize(10).setVerticalAlignment('middle');
    sh.setRowHeight(row, 24); row++;
  });
  sh.getRange(clStart, 2, CHECKLIST.length, 8).setBorder(true, true, true, true, false, false, C.BORDER, SpreadsheetApp.BorderStyle.SOLID);
  row++;

  // ── 01_設定 の詳しい埋め方(バンド別) ──
  band_(row, '01_設定 の詳しい埋め方（上から順に）'); row++;
  row = note_(sh, row, 8, '下の STEP1 で開く 01_設定 を、上から順にこの通り埋めれば設定は完了です。入力欄=ピンク / 自動算出=グレー。\n右上の「設定ナビ」から各設定（❶〜❿）へワンクリックで移動できます。ラベルの ◎ は必須項目。各セルにカーソルを置くと記入例（ツールチップ）が出ます。', { color: C.SUB, size: 9 });
  var howStart = row;
  [
    ['基本設定', '会社名を入力。エントリー方式は 手入力 / Googleフォーム / ATS-CSV から選択（候補者の入り口）。'],
    ['使う区分', '採用する区分（中途 / 新卒 / 業務委託 / インターン）の「有効」をON、使わない区分はOFF（そのダッシュ・進捗タブは自動で隠れます）。表示順で並びを調整。「書類回収」列で区分ごとに履歴書/職経の回収要否を切替（新卒は基本OFFでOK＝50_履歴書管理と回収率KPIが出ません）。'],
    ['選考ステージ定義', '区分ごとに各段を1行ずつ: 順序(1,2,3…) ／ ステージ名（セルのプルダウンから選択＝応募・書類・一次面接・最終面接 等）／ 種別は自動補完 ／ 目標通過率（例 80%）。標準フローが入っているので、不要な段は行を削除、足りない段は行を追加。'],
    ['職種定義', '募集する職種を1行ずつ: 職種名 ／ 区分 ／ 目標採用数（例: エンジニア・中途・3）。'],
    ['採用目標（区分別）', '区分ごとに 内定 / 承諾 / 入社 の目標数と対象期間（例 2026-06）。右の「主要目標指標」でダッシュボードの主役（入社 / 承諾 / 内定）を選択。'],
    ['メンバー', '採用担当者: 氏名 ／ 役割 ／ メール ／ SlackユーザーID。「月次メール受信」をONにした人へ月次レポートが届きます。'],
    ['評価項目', '面接の評価軸: 項目名 ／ 比重（重み）／ 最低点 ／ 有効。加重平均で S〜D を判定し、最低点割れは NG 表示。'],
    ['表示パネル', 'ダッシュボードに出す分析を「有効」で選択・表示順を指定。「レポート出力」をONにすると 60_レポート にも掲載。'],
    ['CSV列マッピング', 'ATSのCSVの列名 → マスタ項目 の対応づけ（CSV取込を使う場合に設定）。'],
    ['Slack配信', '配信種別（週次 / 月次 / 日次 / 評価申し送り）ごとにチャネル・曜日/時刻・有効。「レポート基準日」は空=今日。'],
    ['レポート項目', '出す表ごとに 60タブ / Slack / Doc / メール のON/OFFと表示順を指定。高度分析（前月比サマリ・経路別 必要エントリー数・職種別フル実績・雇用区分別/担当者別）も項目として選べます（週次のDoc/メールは非対応）。'],
    ['必要書類・回収', '区分×書類（履歴書 / 職務経歴書）ごとに 回収タイミング（エントリー時 / 内定後 等）・有効。50_書類回収 に反映。'],
    ['応募フォーム項目', 'Googleフォーム生成時の項目: 項目名 ／ タイプ ／ 必須 ／ 対象区分 ／ 選択肢ソース（職種・性別・説明会日程）／ 有効。'],
    ['説明会日程・アンケート', '説明会日時を追記（フォームの選択肢になります）。「説明会テキストワーク作成」「参加後アンケート作成」のトグル＋アンケート項目を選択（主に新卒）。'],
    ['区分別 取得項目', '（区分）_進捗管理タブに出す区分固有の列（中途＝現年収 / 転職理由 等）: 区分 ／ 項目名 ／ 有効。']
  ].forEach(function (r) {
    sh.getRange(row, 2).setValue(r[0]).setFontColor(C.BLACK).setFontWeight('bold').setFontSize(10).setVerticalAlignment('top').setWrap(true);
    var rc = sh.getRange(row, 3, 1, 7); rc.breakApart();
    rc.merge().setValue(r[1]).setFontColor(C.INK).setFontSize(10).setWrap(true).setVerticalAlignment('middle');
    var lines = Math.max(1, Math.ceil(String(r[1]).length / 62));
    sh.setRowHeight(row, Math.min(84, 24 + (lines - 1) * 15));
    row++;
  });
  sh.getRange(howStart, 2, row - howStart, 8).setBorder(true, true, true, true, true, true, C.BORDER, SpreadsheetApp.BorderStyle.SOLID);
  row++;

  // ── 運用サイクル(日/週/月・いつ誰が何を) ──
  band_(row, '運用サイクル ── いつ・誰が・何を・どこで'); row++;
  var cycStart = row;
  [
    ['日次', '採用担当：候補者の取込/入力（10）・面接記録（12）・進捗更新（(区分)_進捗管理）・書類督促（50・回収する区分のみ）。サンクス／面接リマインドは自動送信（07で設定時）'],
    ['週次', '採用担当：20で進捗確認・週次レポート（60／Slack）でチャネル/職種の動きを共有・エージェントMTG'],
    ['月次', '責任者：月次レポート（経営向け・Doc/メール）と 目標vs実績 のレビュー。ズレたら 01_設定 で目標/フローを調整 →「初期セットアップ/再構築」']
  ].forEach(function (r) {
    sh.getRange(row, 2).setValue(r[0]).setFontColor(C.RED).setFontWeight('bold').setFontSize(11).setVerticalAlignment('middle');
    var rc = sh.getRange(row, 3, 1, 7); rc.breakApart();
    rc.merge().setValue(r[1]).setFontColor(C.INK).setFontSize(10).setWrap(true).setVerticalAlignment('middle');
    sh.setRowHeight(row, 40); row++;
  });
  sh.getRange(cycStart, 2, row - cycStart, 8).setBorder(true, true, true, true, true, true, C.BORDER, SpreadsheetApp.BorderStyle.SOLID);
  row++;

  // ── 用語ミニ辞典 ──
  band_(row, '用語ミニ辞典'); row++;
  var glStart = row;
  [
    ['ファネル', '応募→書類→面接→内定→確定 と絞られていく人数の流れ。各段の人数と通過率で見ます'],
    ['通過率', '前の段から次の段へ進んだ割合（例：応募100→書類80 なら 80%）'],
    ['着地予想', '今のペース（応募の日割×各段の通過率）でいくと最終的に何名になりそうかの予測'],
    ['ヨミ', '終盤の候補の採用確度（S/A/B/C 等）。新卒は 新卒_ヨミ管理 タブで厚く管理します'],
    ['エントリー', '候補者が応募して母集団に入ること。エントリー目標＝チャネル別の応募目標'],
    ['CVR / CPA', 'CVR＝応募→確定の割合 ／ CPA＝確定1名あたりのコスト（円）'],
    ['必要エントリー数', '内定1名（確定1名）を得るのに必要な応募数 ＝ 1/CVR。採用計画の逆算に使う'],
    ['順位/グリッド', 'アンケートの設問タイプ。順位＝項目を1位…N位で評価／グリッド＝行×列の評価表（価値観ランキング等）'],
    ['5段正規化', '区分でステージ数が違っても 応募/書類/面接/内定/確定 の5段に揃えて比較する集計']
  ].forEach(function (r) {
    sh.getRange(row, 2).setValue(r[0]).setFontColor(C.BLACK).setFontWeight('bold').setFontSize(10).setVerticalAlignment('middle');
    var rc = sh.getRange(row, 3, 1, 7); rc.breakApart();
    rc.merge().setValue(r[1]).setFontColor(C.INK).setFontSize(10).setWrap(true).setVerticalAlignment('middle');
    sh.setRowHeight(row, 26); row++;
  });
  sh.getRange(glStart, 2, row - glStart, 8).setBorder(true, true, true, true, true, true, C.BORDER, SpreadsheetApp.BorderStyle.SOLID);
  row++;

  // ── 困ったとき / 注意 ──
  band_(row, '困ったとき・注意'); row++;
  row = note_(sh, row, 8, 'よくある操作 ── 区分/職種/チャネルの増減：01_設定で編集し「ダッシュボードを更新」。　レポートの基準日：01_設定「レポート基準日（空=今日）」。　CSV再取込：メニュー「CSVファイルを取込」（連絡先一致は上書き更新）。', { color: C.SUB, size: 9 });
  row = note_(sh, row, 8, '【注意】「クリーン初期化」は全データ・全設定を消す破壊的操作です。メニュー「初期化パスワードを設定」で保護でき、候補者や会社名が入った使用中シートはパスワード必須になります（誤実行の防止）。', { color: C.RED, size: 9 });
  row++;

  // ── フッター ──
  note_(sh, row, 8, 'メニュー「採用」: ダッシュボードを更新 / 面接評価を保存 / レポートを生成・配信 / CSVファイルを取込 / 初期セットアップ・再構築 / クリーン初期化。　｜　この親シートをコピーし「使う区分」を絞れば、各社・各区分の子シートになります。', { color: C.SUB, size: 9 });

  // このREADMEのレイアウト版を記録(onOpenの自動再生成ガード用)。
  try { PropertiesService.getDocumentProperties().setProperty('readmeVer', README_VER); }
  catch (e) { console.error('readmeVer stamp failed: ' + e); }
}

/* ============================== 01_設定 ============================== */

function buildSettings_() {
  var sh = sheet_(SH.CONF);
  // === マイグレーション(恒久ルール): 退避 → 全クリア → 新レイアウト再描画 → 復元 ===
  // 退避はクラッシュ安全のため一旦 confBackup に保存(全クリア後に落ちても次回復元できる)。
  var props = PropertiesService.getDocumentProperties();
  // バンドレイアウト(v2-bands以降)は位置がほぼ共通(v3でMEMBER幅+1列・REPORT新設=どちらも空読みで安全)。
  // → バンド版からの退避は CONF_LAYOUT 位置で読む。null/v1(横並び)のみ OLD_LAYOUT で読む。
  var stored = props.getProperty('confLayoutVer');
  // バウンドGASのコピーはDocumentProperties(confLayoutVer)を引き継がない場合がある(stored=null)。
  // だが既に現行バンドレイアウト(「選考ステージ定義」見出し)があれば現行版扱いにし、誤migration(OLD_LAYOUT誤読で設定破壊)を防ぐ。
  if (!stored) { try { if (String(sh.getRange(14, 1).getValue() || '').indexOf('選考ステージ') >= 0) stored = CONF_LAYOUT_VER; } catch (e) {} }
  var preV6 = (stored === 'v2-bands' || stored === 'v3-report' || stored === 'v4-docs' || stored === 'v4-docs-form' || stored === 'v5-survey');
  // band❶〜❾位置が共通のバンド版(v6/v8/v9)はCONF_LAYOUT位置で読む(=isNew)。※新VER追加時は必ずここに足す(漏れると全設定喪失)。
  var isNew = (preV6 || stored === 'v6-rows' || stored === 'v8-segfields' || stored === 'v9-jobmove' || stored === CONF_LAYOUT_VER);
  // 職種定義(JOB)はv9でcol15→col8へ移動(チャネル定義撤去後の隙間詰め)。pre-v9(preV6/v6/v8)はcol15で退避・v9以降はcol8。
  var jobOld = isNew && stored !== 'v9-jobmove' && stored !== CONF_LAYOUT_VER;
  var backup = props.getProperty('confBackup');
  var snap = backup ? JSON.parse(backup) : snapshotSettings_(sh, isNew, preV6, jobOld);
  if (!backup) props.setProperty('confBackup', JSON.stringify(snap));

  ensureGrid_(sh, 295, 52);
  // バンド領域(A〜R=1-18)のみクリア。右側(T列〜)に折り込んだチャネル候補マスタ(buildChannelMaster_)は保持。
  var full = sh.getRange(1, 1, sh.getMaxRows(), 18);
  try { full.breakApart(); } catch (e) {}
  full.clear();
  full.clearDataValidations();
  full.clearNote();
  full.setWrap(false);
  sh.setHiddenGridlines(true);

  // 列幅(レーンA/B/C)。旧レイアウトの右側残り列は控えめ幅に戻す。
  for (var k in CONF_WIDTHS) sh.setColumnWidth(Number(k), CONF_WIDTHS[k]);
  for (var c = 19; c <= 48; c++) sh.setColumnWidth(c, 80);

  // グループ見出し帯(赤・全幅)
  CONF_BANDS.forEach(function (b) { bandTitle_(sh, b.row, b.col, b.col + b.w - 1, b.title); });
  // 各ブロックの枠組み(白地サブ見出し・淡色ヘッダー・淡枠)
  for (var key in CONF_LAYOUT) drawConfBlock_(sh, key);
  buildConfNav_(sh);  // 設定ナビ(目次・各❶〜❿へジャンプ)を帯❶右レーンに描画
  // 入力規則・チェックボックス・数値書式
  var segRule = SpreadsheetApp.newDataValidation().requireValueInList(SEGMENTS, true).setAllowInvalid(true).build();
  applyConfFormats_(sh, segRule);
  // 値の復元(退避があればそれ・無ければ既定をシード)
  populateSettings_(sh, snap);
  try { applySegmentGrayout_(); } catch (e) {}  // 使う区分に連動した無効区分のグレーアウト
  try { renderFormUrls_(); } catch (e) {}       // 生成済みフォームURL(配布用)を再描画

  props.setProperty('confLayoutVer', CONF_LAYOUT_VER);
  props.deleteProperty('confBackup');  // 復元完了 → 安全バックアップ解除
}

// 退避: 現在のレイアウト(新=registry / 旧=OLD_LAYOUT)から全設定値を読み取りメモリへ
function snapshotSettings_(sh, isNew, preV6, jobOld) {
  // band3-9はv6で+12行移動 → preV6移行時は旧位置(PRE_V6)で読む。band1-2は不変=CONF_LAYOUT。
  // JOBはv9でcol15→col8へ移動 → pre-v9(jobOld)は旧位置col15で退避。
  function pos(key) {
    if (key === 'JOB' && jobOld) return { row: 16, col: 15, w: 4 };
    return (preV6 && PRE_V6[key]) ? PRE_V6[key] : (isNew ? CONF_LAYOUT[key] : OLD_LAYOUT[key]);
  }
  function rd(key) { var b = pos(key); return b ? readTable_(sh, b.row, b.col, b.w) : []; }
  function cellVal(oldCell, newCell) { var c = preV6 ? oldCell : newCell; try { return c ? sh.getRange(c[0], c[1]).getValue() : ''; } catch (e) { return ''; } }
  var cc = isNew ? CONF_LAYOUT.BASIC.companyCell : OLD_LAYOUT.companyCell;
  var mc = isNew ? CONF_LAYOUT.BASIC.methodCell : OLD_LAYOUT.methodCell;
  var company = '', method = '';
  try { company = String(sh.getRange(cc[0], cc[1]).getValue() || '').trim(); } catch (e) {}
  try { method = String(sh.getRange(mc[0], mc[1]).getValue() || '').trim(); } catch (e) {}
  return {
    STAGE: rd('STAGE'), JOB: rd('JOB'), MEMBER: rd('MEMBER'), TARGET: rd('TARGET'),
    SEG: rd('SEG'), EVAL: rd('EVAL'), CSV: rd('CSV'), PANEL: rd('PANEL'), SLACK: rd('SLACK'),
    REPORT: rd('REPORT'), DOCS: rd('DOCS'), FORMFIELDS: rd('FORMFIELDS'), BRIEF: rd('BRIEF'), SURVEY: rd('SURVEY'),
    SEGFIELDS: rd('SEGFIELDS'),
    briefWork: cellVal(PRE_V6.briefWorkCell, CONF_LAYOUT.SURVEY.briefWorkCell),
    surveyOn: cellVal(PRE_V6.surveyOnCell, CONF_LAYOUT.SURVEY.surveyOnCell),
    primaryGoal: String(cellVal(PRE_V6.primaryCell, CONF_LAYOUT.TARGET.primaryCell) || '').trim(),
    company: company, method: method,
    asOf: cellVal(PRE_V6.asOfCell, CONF_LAYOUT.SLACK.asOfCell)
  };
}

// 1ブロックの枠組み(プレミアムLight: 白地サブ見出し+淡色ヘッダー+淡枠)を描く。
// L.solo=true は群帯(❶〜❿)がタイトルを兼ねる＝■を描かず二重見出しを解消(L.hintがあれば淡色注記)。
function drawConfBlock_(sh, key) {
  var L = CONF_LAYOUT[key];
  var t = sh.getRange(L.titleRow, L.col, 1, L.w); t.breakApart();
  if (L.solo) {
    // 群帯がタイトル＝■は出さない。ガイド(hint)があれば淡色SUB注記で残す。
    t.merge().setValue(L.hint || '').setBackground(C.WHITE).setFontColor(C.SUB)
      .setFontWeight('normal').setFontSize(9).setVerticalAlignment('middle');
  } else {
    // 白地＋黒太字＋チャコール細下線(ダッシュのセクション見出しと統一)
    t.merge().setValue(L.title).setBackground(C.WHITE).setFontColor(C.BLACK)
      .setFontWeight('bold').setFontSize(11).setVerticalAlignment('middle')
      .setBorder(null, null, true, null, null, null, '#3A3A3A', SpreadsheetApp.BorderStyle.SOLID);
  }
  if (L.type !== 'kv') {
    sh.getRange(L.row - 1, L.col, 1, L.w).setValues([L.header])
      .setBackground(HEAD_BG).setFontColor(C.INK).setFontWeight('bold').setFontSize(9)
      .setHorizontalAlignment('center')
      .setBorder(null, null, true, null, null, null, HEAD_RULE, SpreadsheetApp.BorderStyle.SOLID);
  }
  var endRow = L.row + L.max - 1;
  sh.getRange(L.titleRow, L.col, endRow - L.titleRow + 1, L.w)
    .setBorder(true, true, true, true, true, true, BOX_LT, SpreadsheetApp.BorderStyle.SOLID);
}

// 設定ナビ(目次): 帯❶の右レーン(col15-18・row2-12=空き領域)に各群帯❶〜❿へのジャンプを描画。
// 行位置は不変＝既存データ非破壊。同シート内ジャンプ=HYPERLINK("#gid=…&range=A{群帯行}")。
function buildConfNav_(sh) {
  var gid = sh.getSheetId(), c0 = 15, w = 4, top = 2;
  var head = sh.getRange(top, c0, 1, w); head.breakApart();
  head.merge().setValue('■ 設定ナビ（クリックで各設定へ移動）').setBackground(C.WHITE).setFontColor(C.BLACK)
    .setFontWeight('bold').setFontSize(11).setVerticalAlignment('middle')
    .setBorder(null, null, true, null, null, null, '#3A3A3A', SpreadsheetApp.BorderStyle.SOLID);
  sh.setRowHeight(top, 24);
  for (var i = 0; i < CONF_BANDS.length; i++) {
    var b = CONF_BANDS[i], r = top + 1 + i;  // row3..row12
    var cell = sh.getRange(r, c0, 1, w); cell.breakApart();
    cell.merge()
      .setFormula('=HYPERLINK("#gid=' + gid + '&range=A' + b.row + '","▸ ' + String(b.title).replace(/"/g, '') + '")')
      .setFontColor(C.INK).setFontSize(10).setVerticalAlignment('middle');
    sh.setRowHeight(r, 21);
  }
  sh.getRange(top, c0, CONF_BANDS.length + 1, w)
    .setBorder(true, true, true, true, false, false, BOX_LT, SpreadsheetApp.BorderStyle.SOLID);
}

// 入力規則・チェックボックス・数値書式をデータ範囲へ適用
function applyConfFormats_(sh, segRule) {
  var L = CONF_LAYOUT;
  confSrc_(sh, 'STAGE', 0).setDataValidation(segRule);   // ステージ 区分
  vCellListRange_(sh, L.STAGE.row, L.STAGE.col + 2, L.STAGE.max, STAGE_CANDIDATES);  // ステージ名=候補プルダウン(新卒/中途 全パターン)
  vCellListRange_(sh, L.STAGE.row, L.STAGE.col + 3, L.STAGE.max, STAGE_TYPES);        // 種別=プルダウン(選択時onEditで自動補完)
  confSrc_(sh, 'JOB', 1).setDataValidation(segRule);     // 職種 区分
  confSrc_(sh, 'TARGET', 0).setDataValidation(segRule);  // 採用目標 区分
  vCellList_(sh, L.TARGET.primaryCell[0], L.TARGET.primaryCell[1], ['入社', '承諾', '内定']);  // 主要目標指標
  // チャネルは候補マスタ(右側)に一本化のため band2 CHAN ブロックは無し(buildChannelMaster_が描画)
  confSrc_(sh, 'TARGET', 4).setNumberFormat('@');        // 対象期間=テキスト(日付化防止 "2026-06")
  confSrc_(sh, 'SEG', 0).setNumberFormat('@');           // 使う区分
  confSrc_(sh, 'SEG', 1).insertCheckboxes();
  confSrc_(sh, 'SEG', 2).setNumberFormat('0');
  confSrc_(sh, 'SEG', 3).insertCheckboxes();             // 書類回収(区分ごとON/OFF)
  confSrc_(sh, 'EVAL', 0).setNumberFormat('@');          // 評価項目
  sh.getRange(L.EVAL.row, L.EVAL.col + 1, L.EVAL.max, 2).setNumberFormat('0.#');
  confSrc_(sh, 'EVAL', 3).insertCheckboxes();
  confSrc_(sh, 'PANEL', 0).setNumberFormat('@');         // 表示パネル
  confSrc_(sh, 'PANEL', 1).insertCheckboxes();           // 有効(ダッシュ表示)
  confSrc_(sh, 'PANEL', 2).setNumberFormat('0');         // 表示順
  confSrc_(sh, 'PANEL', 3).insertCheckboxes();           // レポート出力
  vCellListRange_(sh, L.CSV.row, L.CSV.col + 1, L.CSV.max, CSV_TARGETS); // CSV マスタ項目=リスト
  confSrc_(sh, 'SLACK', 4).insertCheckboxes();           // Slack配信 有効
  confSrc_(sh, 'MEMBER', 4).insertCheckboxes();          // メンバー 月次メール受信
  confSrc_(sh, 'REPORT', 0).setNumberFormat('@').setWrap(true); // レポート項目名(折返し)
  confSrc_(sh, 'REPORT', 1).insertCheckboxes();          // 60タブ
  confSrc_(sh, 'REPORT', 2).insertCheckboxes();          // Slack
  confSrc_(sh, 'REPORT', 3).insertCheckboxes();          // Doc
  confSrc_(sh, 'REPORT', 4).insertCheckboxes();          // メール
  confSrc_(sh, 'REPORT', 5).setNumberFormat('0');        // 順
  // 必要書類・回収
  confSrc_(sh, 'DOCS', 0).setDataValidation(segRule);                                  // 区分
  vCellListRange_(sh, L.DOCS.row, L.DOCS.col + 1, L.DOCS.max, DOC_TYPES.map(function (d) { return d.key; })); // 書類
  vCellListRange_(sh, L.DOCS.row, L.DOCS.col + 2, L.DOCS.max, DOC_TIMINGS);             // 回収タイミング
  var stageRule = SpreadsheetApp.newDataValidation().requireValueInRange(confSrc_(sh, 'STAGE', 2), true).setAllowInvalid(true).build();
  confSrc_(sh, 'DOCS', 3).setDataValidation(stageRule);                                // 回収ステージ=ステージ名範囲参照(即時)
  confSrc_(sh, 'DOCS', 4).insertCheckboxes();                                          // 有効
  // 応募フォーム項目
  confSrc_(sh, 'FORMFIELDS', 0).setNumberFormat('@');                                  // 項目名
  vCellListRange_(sh, L.FORMFIELDS.row, L.FORMFIELDS.col + 1, L.FORMFIELDS.max, FORMFIELD_TYPES);      // タイプ
  confSrc_(sh, 'FORMFIELDS', 2).insertCheckboxes();                                    // 必須
  vCellListRange_(sh, L.FORMFIELDS.row, L.FORMFIELDS.col + 3, L.FORMFIELDS.max, ['全'].concat(SEGMENTS)); // 対象区分
  vCellListRange_(sh, L.FORMFIELDS.row, L.FORMFIELDS.col + 4, L.FORMFIELDS.max, FORMFIELD_SOURCES);    // 選択肢ソース
  confSrc_(sh, 'FORMFIELDS', 5).insertCheckboxes();                                    // 有効
  confSrc_(sh, 'FORMFIELDS', 6).setNumberFormat('@').setWrap(true);                    // 選択肢(選択型用・自由入力)
  // 説明会日程(追記式)
  confSrc_(sh, 'BRIEF', 0).setNumberFormat('@');                                       // 説明会日時(テキスト)
  confSrc_(sh, 'BRIEF', 3).setNumberFormat('0');                                       // 定員(空=無制限・満席で日程を自動クローズ)
  // 説明会・アンケート
  confSrc_(sh, 'SURVEY', 0).setNumberFormat('@');                                      // アンケート項目名
  vCellListRange_(sh, L.SURVEY.row, L.SURVEY.col + 1, L.SURVEY.max, FORMFIELD_TYPES);  // タイプ
  confSrc_(sh, 'SURVEY', 2).insertCheckboxes();                                        // 必須
  confSrc_(sh, 'SURVEY', 3).insertCheckboxes();                                        // 有効
  sh.getRange(L.SURVEY.briefWorkCell[0], L.SURVEY.briefWorkCell[1]).insertCheckboxes(); // 説明会テキストワーク作成
  sh.getRange(L.SURVEY.surveyOnCell[0], L.SURVEY.surveyOnCell[1]).insertCheckboxes();   // 参加後アンケート作成
  // ❿ 区分別取得項目
  confSrc_(sh, 'SEGFIELDS', 0).setDataValidation(segRule);  // 区分
  confSrc_(sh, 'SEGFIELDS', 1).setNumberFormat('@');        // 項目名(テキスト)
  confSrc_(sh, 'SEGFIELDS', 2).insertCheckboxes();          // 有効
}

// 値の復元(退避優先・無ければ既定)。評価/パネルは不足分のみ追記しトグルを維持。
function populateSettings_(sh, snap) {
  var L = CONF_LAYOUT, seed = seedDefaults_();
  // クリーン雛形モード(cleanInitで設定): 既定の自動投入を抑止し退避値のみ復元=白紙が初期セットアップを跨いで保たれる。
  var clean = PropertiesService.getDocumentProperties().getProperty('cleanTemplate') === 'true';
  function put(key, rows) { if (rows && rows.length) sh.getRange(L[key].row, L[key].col, rows.length, L[key].w).setValues(rows); }

  // 基本設定(kv): 会社名 / エントリー方式。◎=必須・セルのメモ(ツールチップ)に記入例。
  sh.getRange(3, 1).setValue('◎ 会社名').setFontWeight('bold').setFontColor(C.BLACK);
  sh.getRange(4, 1).setValue('◎ エントリー方式').setFontWeight('bold').setFontColor(C.BLACK);
  sh.getRange(3, 2, 1, 2).merge(); sh.getRange(4, 2, 1, 2).merge();
  sh.getRange(3, 2).setValue(snap.company || (clean ? '' : 'Tokumori')).setFontColor(C.INK).setVerticalAlignment('middle')
    .setNote('【◎必須】記入例: Tokumori株式会社\nレポート・メール・フォームの社名として使われます。');
  sh.getRange(4, 2).setValue(snap.method || '手入力').setFontColor(C.INK).setVerticalAlignment('middle')
    .setNote('【◎必須】応募者の入れ方を選択。\n手入力／Googleフォーム／ATS-CSV のいずれか。');
  vCellList_(sh, 4, 2, ENTRY_METHODS);

  // 主要テーブル(STAGE 通過率 / TARGET 対象期間 は表示正規化)
  ['STAGE', 'JOB', 'MEMBER', 'TARGET', 'SEGFIELDS'].forEach(function (key) {
    // clean時に白紙にするのは設計バンド(職種/メンバー/採用目標)のみ。選考ステージ(標準フロー)・SEGFIELDSはカタログ→常に既定。
    var blankIt = clean && ['JOB', 'MEMBER', 'TARGET'].indexOf(key) >= 0;
    var rows = (snap[key] && snap[key].length) ? snap[key] : (blankIt ? [] : seed[key]);
    if (key === 'STAGE') rows = rows.map(function (r) { r = r.slice(); r[4] = normPctText_(r[4]); return r; });
    if (key === 'TARGET') rows = rows.map(function (r) { r = r.slice(); r[4] = normMonth_(r[4]); return r; });
    // MEMBER: 旧4列退避を5列(月次メール=false)へpad
    if (key === 'MEMBER') rows = rows.map(function (r) { r = r.slice(); while (r.length < 5) r.push(false); return r.slice(0, 5); });
    put(key, rows);
  });
  // 使う区分（4列目=書類回収。既存退避は4列目を true=既存挙動不変でpad／新規は新卒・インターンを書類回収OFF既定）
  var segRows = (snap.SEG && snap.SEG.length)
    ? snap.SEG.map(function (r) { r = r.slice(); while (r.length < 4) r.push(true); if (r[3] === '' || r[3] == null) r[3] = true; return r.slice(0, 4); })
    : [['中途', true, 1, true], ['新卒', true, 2, false], ['業務委託', true, 3, true], ['インターン', true, 4, false]];
  put('SEG', segRows);
  // 記入例(ツールチップ): 主要な入力ブロックにメモを付与。
  sh.getRange(L.SEG.titleRow, L.SEG.col).setNote('【◎必須】使う区分だけ「有効」に☑（新卒のみ等もOK）。\n書類回収が要る区分は「書類回収」も☑。');
  sh.getRange(L.STAGE.titleRow, L.STAGE.col).setNote('選考ステージを上から順に並べる（区分ごと）。\nステージ名はプルダウン候補から。目標通過率は任意。');
  // 評価項目(カタログ): 退避 + 不足コア(有効) + 不足カタログ(無効)を追記。トグルは維持。clean時も既定を残す。
  var ev = (snap.EVAL && snap.EVAL.length) ? snap.EVAL.slice() : [];
  var haveE = ev.map(function (r) { return String(r[0]); });
  EVAL_DEFAULT.forEach(function (d) { if (haveE.indexOf(d[0]) < 0) { ev.push([d[0], d[1], d[2], true]); haveE.push(d[0]); } });
  EVAL_CATALOG.forEach(function (d) { if (haveE.indexOf(d[0]) < 0) { ev.push([d[0], d[1], d[2], false]); haveE.push(d[0]); } });
  put('EVAL', ev);
  // 表示パネル(カタログ): 退避 + 不足既定を追記。各行を4列に(レポート出力=既定false)。clean時も既定を残す。
  var pn = (snap.PANEL && snap.PANEL.length) ? snap.PANEL.slice() : [];
  var haveP = pn.map(function (r) { return String(r[0]); });
  var ord = pn.length;
  PANELS.forEach(function (p) { if (haveP.indexOf(p.label) < 0) { ord++; pn.push([p.label, true, ord, false]); } });
  pn = pn.map(function (r) { r = r.slice(); while (r.length < 4) r.push(false); return r.slice(0, 4); });  // レポート出力列を4列目にpad
  put('PANEL', pn);
  // レポート項目: 正本(REPORT_ITEMS)順で再構築。ON/OFFは退避からラベルで引継ぎ、順は正本順(1..N)。
  // → 月次→週次のグループ順を常に維持し、後付け項目が末尾に付いて分断する問題を恒久解消(stale行も自然消去)。
  var prevR = {}; (snap.REPORT || []).forEach(function (r) { prevR[String(r[0])] = r; });
  var rp = REPORT_ITEMS.map(function (it, i) {
    var weekly = it.rep === '週次';
    var p = prevR[it.label];
    // [項目, 60タブ, Slack, Doc, メール, 順]  週次のDoc/メールは false (後段で—表示)
    if (p) return [it.label, p[1], p[2], weekly ? false : p[3], weekly ? false : p[4], i + 1];
    return [it.label, true, true, weekly ? false : true, weekly ? false : true, i + 1];
  });
  put('REPORT', rp);
  decorateReportBlock_(sh);  // 週次行のDoc/メールを—(無効)に・所属repでゼブラ
  // 必要書類・回収: 退避 + 不足(区分×書類)を既定で追記。キー=区分+書類。トグル/タイミング維持。
  var dc = (snap.DOCS && snap.DOCS.length) ? snap.DOCS.slice() : [];
  var haveD = {}; dc.forEach(function (r) { haveD[String(r[0]) + '|' + String(r[1])] = true; });
  SEGMENTS.forEach(function (seg) {
    DOC_TYPES.forEach(function (d) {
      if (haveD[seg + '|' + d.key]) return;
      // 既定: 履歴書=全区分エントリー時✓ / 職務経歴書=中途のみエントリー時✓・他は任意✗
      var def = (d.key === '履歴書') ? ['エントリー時', '', true]
              : (seg === '中途' ? ['エントリー時', '', true] : ['任意', '', false]);
      dc.push([seg, d.key, def[0], def[1], def[2]]);
    });
  });
  put('DOCS', dc);
  // 応募フォーム項目: 退避優先・無ければ既定(同名項目で不足分追記)
  var ff = (snap.FORMFIELDS && snap.FORMFIELDS.length) ? snap.FORMFIELDS.slice() : [];
  var haveF = {}; ff.forEach(function (r) { haveF[String(r[0])] = true; });
  // [項目名, タイプ, 必須, 対象区分, 選択肢ソース, 有効, 選択肢]  カタログ→clean時も既定を残す。
  [
    ['お名前', '短文', true, '全', '自由', true, ''],
    ['メールアドレス', '短文', true, '全', '自由', true, ''],
    ['電話番号', '短文', false, '全', '自由', true, ''],
    ['応募職種', '選択', true, '全', '職種', true, ''],
    ['性別', '選択', false, '全', '性別', true, ''],
    ['大学', '短文', false, '新卒', '自由', true, ''],
    ['学部', '短文', false, '新卒', '自由', true, ''],
    ['説明会日程', '選択', false, '新卒', '説明会日程', true, '']
  ].forEach(function (d) { if (!haveF[d[0]]) { ff.push(d); haveF[d[0]] = true; } });
  ff = ff.map(function (r) { r = r.slice(0, CONF_LAYOUT.FORMFIELDS.w); while (r.length < CONF_LAYOUT.FORMFIELDS.w) r.push(''); return r; });  // 退避値(旧6列)も新幅(7列)へpad
  put('FORMFIELDS', ff);
  // 説明会日程(退避優先・無ければ例の1行)。clean時は空。
  put('BRIEF', (snap.BRIEF && snap.BRIEF.length) ? snap.BRIEF : (clean ? [] : [['(例) 2026-07-01 14:00', 'オンライン(Zoom)', '第1回', 30]]));
  // 説明会・アンケート: トグル2つ＋アンケート項目(退避優先・不足は既定追記)。ラベルはトグルセルの左(col1)に動的配置。
  sh.getRange(L.SURVEY.briefWorkCell[0], 1).setValue('説明会テキストワーク作成').setFontWeight('bold').setFontColor(C.BLACK);
  sh.getRange(L.SURVEY.surveyOnCell[0], 1).setValue('参加後アンケート作成').setFontWeight('bold').setFontColor(C.BLACK);
  sh.getRange(L.SURVEY.briefWorkCell[0], L.SURVEY.briefWorkCell[1]).setValue(snap.briefWork === '' || snap.briefWork == null ? false : !!snap.briefWork);
  sh.getRange(L.SURVEY.surveyOnCell[0], L.SURVEY.surveyOnCell[1]).setValue(snap.surveyOn === '' || snap.surveyOn == null ? false : !!snap.surveyOn);
  var sv = (snap.SURVEY && snap.SURVEY.length) ? snap.SURVEY.slice() : [];
  var haveS = {}; sv.forEach(function (r) { haveS[String(r[0])] = true; });
  SURVEY_DEFAULT.forEach(function (d) { if (!haveS[d[0]]) { sv.push(d); haveS[d[0]] = true; } });
  put('SURVEY', sv);
  // CSVマッピング(カタログ→既定を残す)
  put('CSV', (snap.CSV && snap.CSV.length) ? snap.CSV : seed.CSV);
  // Slack配信(退避優先・無ければ既定。カタログ→既定を残す)
  put('SLACK', (snap.SLACK && snap.SLACK.length) ? snap.SLACK : [
    ['週次レポート', '#saiyo-weekly', '月', '09:00', false],
    ['月次レポート', '#keiei', '1', '09:00', false],
    ['日次(本日面接/要対応)', '#saiyo-daily', '毎日', '08:00', false],
    ['評価申し送り', '#saiyo-eval', '', '', false]
  ]);
  // レポート基準日(空=今日)
  var ac = L.SLACK.asOfCell;
  sh.getRange(ac[0] - 1, ac[1]).setValue('レポート基準日(空=今日)').setFontWeight('bold').setFontColor(C.BLACK);
  sh.getRange(ac[0], ac[1]).setValue(snap.asOf || '').setNumberFormat('@').setBackground('#FFF3F2')
    .setBorder(true, true, true, true, false, false, C.BORDER, SpreadsheetApp.BorderStyle.SOLID);
  // 主要目標指標(ダッシュ/レポートの主役・区分別採用目標の右)
  var pl = L.TARGET.primaryLabelCell, pcc = L.TARGET.primaryCell;
  sh.getRange(pl[0], pl[1]).setValue('主要目標指標(ダッシュの主役)').setFontWeight('bold').setFontColor(C.BLACK);
  sh.getRange(pcc[0], pcc[1]).setValue(snap.primaryGoal || '入社').setBackground('#FFF3F2')
    .setBorder(true, true, true, true, false, false, C.BORDER, SpreadsheetApp.BorderStyle.SOLID);
}

// REPORTブロック: 週次行のDoc/メールはチェックボックス不可 → クリアして「—」(薄グレー)に。
function decorateReportBlock_(sh) {
  var L = CONF_LAYOUT.REPORT;
  var rep2 = {}; REPORT_ITEMS.forEach(function (it) { rep2[it.label] = it.rep; });
  var vals = sh.getRange(L.row, L.col, L.max, L.w).getValues();
  for (var i = 0; i < vals.length; i++) {
    var label = String(vals[i][0]).trim();
    if (!label) continue;
    sh.setRowHeight(L.row + i, 32);            // 項目名(折返し)が全文見えるよう行高確保
    if (rep2[label] !== '週次') continue;
    [3, 4].forEach(function (off) {            // Doc=+3, メール=+4
      var c = sh.getRange(L.row + i, L.col + off);
      c.clearDataValidations();
      c.setValue('—').setFontColor(C.SUB).setHorizontalAlignment('center');
    });
  }
}

// 列範囲に固定リストの入力規則を一括設定
function vCellListRange_(sh, r, c, n, list) {
  var rule = SpreadsheetApp.newDataValidation().requireValueInList(list, true).setAllowInvalid(true).build();
  sh.getRange(r, c, n, 1).setDataValidation(rule);
}

// 既定値(初回 or 退避が空のときに使用)。位置はレジストリ経由なのでここは値だけ持つ。
function seedDefaults_() {
  return {
    // 種別: entry/screen/interview/task/offer/accept/join
    STAGE: [
      ['中途', 1, '応募', 'entry', '', ''], ['中途', 2, '書類', 'screen', '80%', ''],
      ['中途', 3, '一次面接', 'interview', '50%', ''], ['中途', 4, '二次面接', 'interview', '60%', ''],
      ['中途', 5, '最終面接', 'interview', '70%', ''], ['中途', 6, '内定', 'offer', '90%', ''],
      ['中途', 7, '承諾', 'accept', '80%', ''], ['中途', 8, '入社', 'join', '95%', ''],
      ['新卒', 1, '応募', 'entry', '', ''], ['新卒', 2, '書類', 'screen', '80%', ''],
      ['新卒', 3, '一次面接', 'interview', '50%', ''], ['新卒', 4, 'グループ面接', 'interview', '60%', ''],
      ['新卒', 5, '最終面接', 'interview', '70%', ''], ['新卒', 6, '内定', 'offer', '90%', ''],
      ['新卒', 7, '承諾', 'accept', '80%', ''], ['新卒', 8, '入社', 'join', '95%', ''],
      ['業務委託', 1, '応募', 'entry', '', ''], ['業務委託', 2, '面談', 'interview', '60%', ''],
      ['業務委託', 3, 'トライアル', 'task', '70%', ''], ['業務委託', 4, '契約', 'offer', '90%', ''],
      ['インターン', 1, '応募', 'entry', '', ''], ['インターン', 2, '面談', 'interview', '60%', ''],
      ['インターン', 3, '課題選考', 'task', '70%', ''], ['インターン', 4, '受入', 'accept', '85%', ''],
      ['インターン', 5, '稼働', 'join', '95%', '']
    ],
    CHAN: [
      ['直接応募', 'organic', 0, true, ''], ['リファラル', 'referral', 0, true, '社員紹介'],
      ['エージェント', 'agent', '成功報酬', true, ''], ['Wantedly', '媒体', 50000, true, ''],
      ['Green', '媒体', 50000, true, ''], ['Indeed', '媒体', 30000, true, ''],
      ['スカウト', 'scout', 0, true, ''], ['SNS', 'organic', 0, true, 'X/LinkedIn']
    ],
    JOB: [
      ['エンジニア', '中途', 3, ''], ['セールス', '中途', 2, ''], ['マーケティング', '中途', 1, ''],
      ['コーポレート', '中途', 1, ''], ['デザイナー', '中途', 1, ''], ['PdM', '中途', 1, '']
    ],
    MEMBER: [
      ['鈴木', 'RC', 'suzuki@example.com', '', false], ['田中', '面接官', 'tanaka@example.com', '', false],
      ['佐藤', '面接官', 'sato@example.com', '', false], ['経営A', '経営', 'exec@example.com', '', true]
    ],
    TARGET: [
      ['中途', 10, 7, 5, '2026-06'], ['新卒', 8, 6, 4, '2026-06'],
      ['業務委託', 5, 5, 5, '2026-06'], ['インターン', 6, 6, 6, '2026-06']
    ],
    CSV: [
      ['氏名', '氏名'], ['メールアドレス', '連絡先'], ['応募職種', '職種'],
      ['応募経路', 'チャネル'], ['応募日', '応募日'], ['区分', '区分']
    ],
    // 区分別取得項目: SEG_FIELDS定数をフラット化([区分,項目名,有効])。設定で追加/編集/無効化できる。
    SEGFIELDS: (function () {
      var out = [];
      SEGMENTS.forEach(function (seg) { (SEG_FIELDS[seg] || []).forEach(function (f) { out.push([seg, f, true]); }); });
      return out;
    })()
  };
}

/* ============================== 10_候補者マスタ ============================== */

function buildMaster_() {
  var sh = sheet_(SH.MASTER);
  sh.setHiddenGridlines(true);
  var N = 500, w = MASTER_COLS.length;  // 予約行(候補者増でもゼブラ/罫線/入力規則が下まで整う)

  // === マイグレーション(恒久ルール): 列追加/並べ替えでも既存データをヘッダー名で保持 ===
  var snap = snapshotMaster_(sh);
  ensureGrid_(sh, N + 5, Math.max(w, sh.getMaxColumns()));
  // データ域クリア(旧列も含めて一掃 → 新順で書き戻す)
  if (sh.getLastRow() > 1) sh.getRange(2, 1, sh.getLastRow() - 1, sh.getMaxColumns()).clear();

  // ヘッダー(黒)+固定
  sh.getRange(1, 1, 1, w).setValues([MASTER_COLS])
    .setBackground(HEAD_BG).setFontColor(C.INK).setFontWeight('bold').setFontSize(10)
    .setHorizontalAlignment('center').setVerticalAlignment('middle');
  sh.setRowHeight(1, 28);
  sh.setFrozenRows(1);
  sh.setFrozenColumns(2);

  // ゼブラ(2..N)
  var bgs = [];
  for (var i = 0; i < N; i++) { var line = []; for (var j = 0; j < w; j++) line.push(i % 2 === 1 ? C.ZEBRA : C.WHITE); bgs.push(line); }
  sh.getRange(2, 1, N, w).setBackgrounds(bgs).setFontColor(C.INK).setFontSize(10).setVerticalAlignment('middle');

  // 列幅(MASTER_COLS順に対応)
  var WIDTHS = { 'candidate_id': 110, '区分': 70, '職種': 110, 'チャネル': 100, '氏名': 90, '性別': 64,
    '生年月日': 100, '連絡先': 150, '電話番号': 120, '大学': 110, '学部': 110, '学科': 110, '高校名': 120,
    '応募日': 90, '現ステージ': 90, 'ステータス': 70, '見送り辞退理由': 110, '競合先': 110, '採用担当RC': 90,
    'ネクストアクション': 200, 'NA期限': 90, '次回面接日時': 130, '次回面接URL': 110, '次回面接官': 110,
    '内定日': 90, '承諾日': 90, '入社日': 90, '履歴書リンク': 150, '履歴書回収日': 100,
    '職務経歴書リンク': 150, '職務経歴書回収日': 110, 'サンクス送信日': 100, '評価メモ': 200,
    '面接回数': 64, '直近面接日': 100, '直近面接官': 100, '直近フェーズ': 90, '総合評価': 72, '最新評価': 180 };
  for (var ci = 0; ci < MASTER_COLS.length; ci++) sh.setColumnWidth(ci + 1, WIDTHS[MASTER_COLS[ci]] || 100);

  var H = headerIndex_(MASTER_COLS);

  // 退避データを新順で書き戻し。無ければサンプル投入。
  if (snap.length) {
    var out = snap.map(function (o) { return MASTER_COLS.map(function (c) { return (o[c] !== undefined && o[c] !== null) ? o[c] : ''; }); });
    sh.getRange(2, 1, out.length, w).setValues(out);
  } else {
    seedMaster_(sh);
  }

  // 日付書式
  ['生年月日', '応募日', 'NA期限', '内定日', '承諾日', '入社日', '直近面接日',
   '履歴書回収日', '職務経歴書回収日', 'サンクス送信日'].forEach(function (k) {
    sh.getRange(2, H[k] + 1, N, 1).setNumberFormat('yyyy-mm-dd');
  });
  sh.getRange(2, H['次回面接日時'] + 1, N, 1).setNumberFormat('yyyy-mm-dd hh:mm');

  // プルダウン(範囲参照=即時反映)。先に予約行全体の入力規則を一掃(旧レイアウトの残骸プルダウンを除去＝clear()は規則を消さないため)。
  sh.getRange(2, 1, N, w).clearDataValidations();
  var conf = sheet_(SH.CONF);
  setVR_(sh, H['職種'] + 1, N, confSrc_(conf, 'JOB', 0));
  // チャネルは基本定義＋候補マスタ有効✓の統合リスト(setVLで固定リスト。チャネル変更後は🔄更新で反映)
  setVL_(sh, H['チャネル'] + 1, N, confRead_('CHAN').map(function (r) { return String(r[0]); }).filter(Boolean));
  // 現ステージ: 有効区分の選考ステージ名のみをリストに(無効区分の段は出さない)。空時は全STAGE名範囲にフォールバック。
  var stageList = [];
  try { enabledSegments_().forEach(function (s) { segStages_(s).forEach(function (st) { var nm = String(st.name || '').trim(); if (nm && stageList.indexOf(nm) < 0) stageList.push(nm); }); }); } catch (e) {}
  if (stageList.length) setVL_(sh, H['現ステージ'] + 1, N, stageList);
  else setVR_(sh, H['現ステージ'] + 1, N, confSrc_(conf, 'STAGE', 2));
  setVR_(sh, H['採用担当RC'] + 1, N, confSrc_(conf, 'MEMBER', 0));
  setVL_(sh, H['区分'] + 1, N, SEGMENTS);
  setVL_(sh, H['性別'] + 1, N, GENDERS);
  setVL_(sh, H['ステータス'] + 1, N, STATUSES);
  setVL_(sh, H['見送り辞退理由'] + 1, N, REASONS);

  // 現ステージの色付け(条件付き書式: 内定以降を赤太字)
  applyStageHighlight_(sh, H['現ステージ'] + 1, N);

  // 枠囲い
  sh.getRange(1, 1, N + 1, w).setBorder(true, true, true, true, false, false, C.BORDER, SpreadsheetApp.BorderStyle.SOLID);
}

// マスタの既存行をヘッダー名でスナップショット([{列名:値}])。列追加/並べ替えに耐えるため。
function snapshotMaster_(sh) {
  var lastRow = sh.getLastRow(), lastCol = sh.getLastColumn();
  if (lastRow < 2 || lastCol < 1) return [];
  var vals = sh.getRange(1, 1, lastRow, lastCol).getValues();
  var oldH = headerIndex_(vals[0]);
  var out = [];
  for (var i = 1; i < vals.length; i++) {
    var o = {};
    for (var name in oldH) o[name] = vals[i][oldH[name]];
    if (String(o['candidate_id'] || '').trim() !== '') out.push(o);
  }
  return out;
}

function seedMaster_(sh) {
  // ヘッダー駆動(列の追加/並べ替えに強い)。性別/生年月日入りで性別別・年齢別パネルをデモ。
  var samples = [
    { candidate_id: 'C-2026-0001', 区分: '中途', 職種: 'エンジニア', チャネル: 'リファラル', 氏名: '山田太郎', 性別: '男性', 生年月日: d_(1994, 4, 12), 連絡先: 'yamada@example.com', 電話番号: '090-1111-0001', 応募日: d_(2026, 5, 10), 現ステージ: '二次面接', ステータス: '進行中', 採用担当RC: '鈴木', ネクストアクション: '二次FB共有', 'NA期限': d_(2026, 6, 17), 評価メモ: '一次good' },
    { candidate_id: 'C-2026-0002', 区分: '中途', 職種: 'セールス', チャネル: 'エージェント', 氏名: '佐藤花子', 性別: '女性', 生年月日: d_(1990, 8, 3), 連絡先: 'sato.h@example.com', 電話番号: '090-1111-0002', 応募日: d_(2026, 5, 12), 現ステージ: '内定', ステータス: '内定', 競合先: 'B社', 採用担当RC: '鈴木', ネクストアクション: '条件提示', 'NA期限': d_(2026, 6, 18), 内定日: d_(2026, 6, 5) },
    { candidate_id: 'C-2026-0003', 区分: '中途', 職種: 'エンジニア', チャネル: 'Green', 氏名: '鈴木一郎', 性別: '男性', 生年月日: d_(1988, 1, 20), 連絡先: 'suzuki.i@example.com', 電話番号: '090-1111-0003', 応募日: d_(2026, 5, 15), 現ステージ: '入社', ステータス: '入社', 採用担当RC: '鈴木', ネクストアクション: '入社手続き', 内定日: d_(2026, 5, 28), 承諾日: d_(2026, 6, 1), 入社日: d_(2026, 7, 1) },
    { candidate_id: 'C-2026-0004', 区分: '中途', 職種: 'マーケティング', チャネル: 'Wantedly', 氏名: '田中美咲', 性別: '女性', 生年月日: d_(1997, 11, 5), 連絡先: 'tanaka.m@example.com', 電話番号: '090-1111-0004', 応募日: d_(2026, 5, 20), 現ステージ: '書類', ステータス: '見送り', 見送り辞退理由: 'スキル不一致', 採用担当RC: '田中' },
    { candidate_id: 'C-2026-0005', 区分: '中途', 職種: 'コーポレート', チャネル: '直接応募', 氏名: '高橋健', 性別: '男性', 生年月日: d_(1985, 6, 30), 連絡先: 'takahashi@example.com', 電話番号: '090-1111-0005', 応募日: d_(2026, 5, 22), 現ステージ: '一次面接', ステータス: '進行中', 採用担当RC: '田中', ネクストアクション: '一次日程調整', 'NA期限': d_(2026, 6, 16) },
    { candidate_id: 'C-2026-0006', 区分: '中途', 職種: 'エンジニア', チャネル: 'スカウト', 氏名: '伊藤遼', 性別: '男性', 生年月日: d_(1999, 3, 9), 連絡先: 'ito@example.com', 電話番号: '090-1111-0006', 応募日: d_(2026, 6, 1), 現ステージ: '最終面接', ステータス: '進行中', 採用担当RC: '鈴木', ネクストアクション: '最終調整', 'NA期限': d_(2026, 6, 19) },
    { candidate_id: 'C-2026-0007', 区分: '中途', 職種: 'セールス', チャネル: 'Indeed', 氏名: '渡辺彩', 性別: '女性', 生年月日: d_(1995, 9, 18), 連絡先: 'watanabe@example.com', 電話番号: '090-1111-0007', 応募日: d_(2026, 6, 3), 現ステージ: '応募', ステータス: '見送り', 見送り辞退理由: '連絡不通', 採用担当RC: '佐藤' },
    { candidate_id: 'C-2026-0008', 区分: '中途', 職種: 'エンジニア', チャネル: 'リファラル', 氏名: '中村翔', 性別: '男性', 生年月日: d_(2001, 2, 14), 連絡先: 'nakamura@example.com', 電話番号: '090-1111-0008', 応募日: d_(2026, 6, 8), 現ステージ: '承諾', ステータス: '承諾', 競合先: 'C社', 採用担当RC: '鈴木', ネクストアクション: '入社日調整', 内定日: d_(2026, 6, 10), 承諾日: d_(2026, 6, 12) }
  ];
  var rows = samples.map(function (o) { return MASTER_COLS.map(function (c) { return (o[c] !== undefined) ? o[c] : ''; }); });
  sh.getRange(2, 1, rows.length, MASTER_COLS.length).setValues(rows);  // 集計列(末尾)は空のまま→自動集計
}

/* ============================== 11_面接スケジュール ============================== */

function buildInterview_() {
  var sh = sheet_(SH.IV);
  sh.setHiddenGridlines(true);
  var N = 500, w = IV_COLS.length;  // 予約行(面接増でもゼブラ/罫線が下まで整う)
  ensureGrid_(sh, N + 5, w);

  sh.getRange(1, 1, 1, w).setValues([IV_COLS])
    .setBackground(HEAD_BG).setFontColor(C.INK).setFontWeight('bold').setFontSize(10)
    .setHorizontalAlignment('center').setVerticalAlignment('middle');
  sh.setRowHeight(1, 28);
  sh.setFrozenRows(1);

  var bgs = [];
  for (var i = 0; i < N; i++) { var line = []; for (var j = 0; j < w; j++) line.push(i % 2 === 1 ? C.ZEBRA : C.WHITE); bgs.push(line); }
  sh.getRange(2, 1, N, w).setBackgrounds(bgs).setFontColor(C.INK).setFontSize(10).setVerticalAlignment('middle');

  var iw = [110, 110, 90, 70, 110, 110, 130, 200, 110, 80, 80, 70, 56, 200, 64, 220, 56];  // +評点,総合点,評価明細,判定
  for (var c = 0; c < iw.length; c++) sh.setColumnWidth(c + 1, iw[c]);

  if (sh.getLastRow() <= 1) seedInterview_(sh);

  var H = headerIndex_(IV_COLS);
  sh.getRange(2, H['予定日時'] + 1, N, 1).setNumberFormat('yyyy-mm-dd hh:mm');

  var conf = sheet_(SH.CONF), L = CONF_LAYOUT;
  setVR_(sh, H['ステージ'] + 1, N, confSrc_(conf, 'STAGE', 2));
  setVR_(sh, H['面接官'] + 1, N, confSrc_(conf, 'MEMBER', 0));
  setVL_(sh, H['区分'] + 1, N, SEGMENTS);
  setVL_(sh, H['形式'] + 1, N, IV_FORMAT);
  setVL_(sh, H['ステータス'] + 1, N, IV_STATUS);
  setVL_(sh, H['結果'] + 1, N, IV_RESULT);
  setVL_(sh, H['評点'] + 1, N, IV_SCORE);
  setVL_(sh, H['判定'] + 1, N, ['合', 'NG']);

  sh.getRange(1, 1, N + 1, w).setBorder(true, true, true, true, false, false, C.BORDER, SpreadsheetApp.BorderStyle.SOLID);
}

function seedInterview_(sh) {
  var rows = [
    ['IV-2026-0001', 'C-2026-0001', '山田太郎', '中途', 'エンジニア', '一次面接', dt_(2026,6,8,10,0),  'https://meet.google.com/aaa-bbbb-ccc', '田中', 'オンライン', '実施済', '通過', 'A', '論理的で実装経験も十分。次は二次でカルチャー確認', 4, '{"コミュニケーション":4,"論理的思考力":5,"専門スキル":4}', '合'],
    ['IV-2026-0002', 'C-2026-0001', '山田太郎', '中途', 'エンジニア', '二次面接', dt_(2026,6,20,14,0), 'https://meet.google.com/ddd-eeee-fff', '田中, 佐藤', 'オンライン', '予定', '', '', '', '', '', ''],
    ['IV-2026-0003', 'C-2026-0005', '高橋健',   '中途', 'コーポレート', '一次面接', dt_(2026,6,16,11,0), 'https://meet.google.com/ggg-hhhh-iii', '佐藤', 'オンライン', '予定', '', '', '', '', '', ''],
    ['IV-2026-0004', 'C-2026-0006', '伊藤遼',   '中途', 'エンジニア', '最終面接', dt_(2026,6,19,16,0), 'https://meet.google.com/jjj-kkkk-lll', '経営A', 'オンライン', '予定', '', '', '', '', '', '']
  ];
  sh.getRange(2, 1, rows.length, rows[0].length).setValues(rows);
}

/* ============================== バリデーション補助 ============================== */

function setVR_(sh, col, n, range) { // 範囲参照(即時反映)
  var rule = SpreadsheetApp.newDataValidation().requireValueInRange(range, true).setAllowInvalid(true).build();
  sh.getRange(2, col, n, 1).setDataValidation(rule);
}
function setVL_(sh, col, n, list) { // 固定リスト
  var rule = SpreadsheetApp.newDataValidation().requireValueInList(list, true).setAllowInvalid(true).build();
  sh.getRange(2, col, n, 1).setDataValidation(rule);
}

function applyStageHighlight_(sh, col, n) {
  var rng = sh.getRange(2, col, n, 1);
  var rules = sh.getConditionalFormatRules().filter(function (r) {
    var rs = r.getRanges();
    return !(rs.length === 1 && rs[0].getColumn() === col && rs[0].getRow() === 2);
  });
  ['内定', '承諾', '入社'].forEach(function (s) {
    rules.push(SpreadsheetApp.newConditionalFormatRule()
      .whenTextEqualTo(s).setFontColor(C.RED).setBold(true).setRanges([rng]).build());
  });
  sh.setConditionalFormatRules(rules);
}

/* ============================== 21_中途ダッシュボード ============================== */

function computeMid_() { return computeSegment_('中途'); }

function computeSegment_(seg) {
  var conf = sheet_(SH.CONF);
  var stagesAll = confRead_('STAGE');
  var stages = stagesAll.filter(function (r) { return String(r[0]) === seg; })
                        .sort(function (a, b) { return Number(a[1]) - Number(b[1]); });
  var stageNames = stages.map(function (r) { return String(r[2]); });
  var stageTypes = stages.map(function (r) { return String(r[3]); });
  var stageRates = stages.map(function (r) { return parsePct_(r[4]); });  // 目標通過率(0-1 or null)
  var idxOf = {}; stageNames.forEach(function (n, i) { idxOf[n] = i; });

  var m = sheet_(SH.MASTER);
  var data = m.getDataRange().getValues();
  var head = data.shift();
  var H = headerIndex_(head);
  var rows = data.filter(function (r) {
    return String(r[H['区分']]) === seg && String(r[H['candidate_id']]).trim() !== '';
  });

  var counts = stageNames.map(function () { return 0; });
  var now = nowTokyo_(); var ym = now.getUTCFullYear() * 100 + now.getUTCMonth();
  var active = 0, offM = 0, accM = 0; var days = [];
  rows.forEach(function (r) {
    var cur = String(r[H['現ステージ']]);
    var si = (cur in idxOf) ? idxOf[cur] : -1;
    if (si >= 0) for (var k = 0; k <= si; k++) counts[k]++;
    if (String(r[H['ステータス']]) === '進行中') active++;
    var od = r[H['内定日']], ad = r[H['承諾日']], ap = r[H['応募日']];
    if (od instanceof Date) {
      if (od.getUTCFullYear() * 100 + od.getUTCMonth() === ym) offM++;
      if (ap instanceof Date) days.push((od - ap) / 86400000);
    }
    if (ad instanceof Date && ad.getUTCFullYear() * 100 + ad.getUTCMonth() === ym) accM++;
  });

  var tgRow = confRead_('TARGET')
                .filter(function (r) { return String(r[0]) === seg; })[0] || [];
  var target = { '内定': Number(tgRow[1] || 0), '承諾': Number(tgRow[2] || 0), '入社': Number(tgRow[3] || 0) };
  var avgDays = days.length ? Math.round(days.reduce(function (a, b) { return a + b; }, 0) / days.length) : null;

  return { seg: seg, stageNames: stageNames, stageTypes: stageTypes, stageRates: stageRates, counts: counts, idxOf: idxOf,
           active: active, offM: offM, accM: accM, avgDays: avgDays,
           target: target, targetMonth: tgRow[4], total: rows.length, rows: rows, H: H };
}

// 種別から最初のステージindexを返す(set=種別の配列)。なければ -1
function idxByType_(stageTypes, set) {
  for (var i = 0; i < stageTypes.length; i++) if (set.indexOf(stageTypes[i]) >= 0) return i;
  return -1;
}
// 区分の「最終目標」ステージ(join>accept>offerの深い方)と目標値
function finalGoal_(M) {
  var all = { join: ['join', M.target['入社']], accept: ['accept', M.target['承諾']], offer: ['offer', M.target['内定']] };
  var pri = primaryGoalType_();
  var order = [pri].concat(['join', 'accept', 'offer'].filter(function (t) { return t !== pri; }));  // 主要指標を優先
  for (var i = 0; i < order.length; i++) {
    var d = all[order[i]];
    var idx = idxByType_(M.stageTypes, [d[0]]);
    if (idx >= 0) return { name: M.stageNames[idx], act: M.counts[idx], tgt: d[1] };
  }
  return null;
}
// 主要目標指標(01_設定 区分別採用目標の右)。内定=offer/承諾=accept/入社=join。既定=入社。
function primaryGoalType_() {
  try {
    var c = CONF_LAYOUT.TARGET.primaryCell;
    var v = String(sheet_(SH.CONF).getRange(c[0], c[1]).getValue() || '').trim();
    return v === '内定' ? 'offer' : (v === '承諾' ? 'accept' : 'join');
  } catch (e) { return 'join'; }
}

// "60%"/0.6/60 → 0.6。空/不正は null。
function parsePct_(v) {
  if (v === '' || v == null) return null;
  if (typeof v === 'number') return v > 1 ? v / 100 : v;
  var s = String(v).trim();
  if (s.indexOf('%') >= 0) { var n = parseFloat(s); return isNaN(n) ? null : n / 100; }
  var f = parseFloat(s); if (isNaN(f)) return null; return f > 1 ? f / 100 : f;
}
// 表示正規化: 通過率→"NN%"テキスト / 対象期間→"YYYY-MM"テキスト(設定タブの体裁統一)
function normPctText_(v) { var p = parsePct_(v); return p == null ? (v === 0 ? '' : (v || '')) : (Math.round(p * 100) + '%'); }
function normMonth_(v) {
  if (v instanceof Date) { var t = new Date(v.getTime() + 9 * 3600 * 1000); return t.getUTCFullYear() + '-' + ('0' + (t.getUTCMonth() + 1)).slice(-2); }
  var m = String(v || '').replace(/[\/.]/g, '-').match(/(\d{4})-(\d{1,2})/); return m ? (m[1] + '-' + ('0' + m[2]).slice(-2)) : (v || '');
}
// ステージkの前段→当段 通過率: 母数十分(≥8)なら実績、なければ設定の目標通過率、最後にフォールバック。
function stepRate_(M, k) {
  var prev = M.counts[k - 1] || 0, cur = M.counts[k] || 0;
  if (prev >= 8) return prev > 0 ? cur / prev : 0;
  var cfg = M.stageRates ? M.stageRates[k] : null;
  if (cfg != null && cfg > 0) return cfg;
  return prev > 0 ? cur / prev : 0.5;
}
// WP16: 目標ペース判定＋着地予想(RPO方式=エントリー日割×通過率カスケード)。
// 返り: { elapsed(0-1 or null), label, entryForecast, goals:[{type,name,idx,tgt,act,rate,pace,status,forecast}] }
function pace_(M, asOf) {
  // 対象期間 → 年/月(東京) と 経過率
  var tm = M.targetMonth, ty = null, tmo = null, label = '';
  if (tm instanceof Date) { var t = new Date(tm.getTime() + 9 * 3600 * 1000); ty = t.getUTCFullYear(); tmo = t.getUTCMonth(); }
  else { var mm = String(tm || '').replace(/[\/.]/g, '-').match(/(\d{4})-(\d{1,2})/); if (mm) { ty = Number(mm[1]); tmo = Number(mm[2]) - 1; } }
  var now = asOf || nowTokyo_(), elapsed = null;
  if (ty != null && !isNaN(ty)) {
    label = ty + '-' + ('0' + (tmo + 1)).slice(-2);
    var totDays = new Date(Date.UTC(ty, tmo + 1, 0)).getUTCDate();
    var cmp = (ty * 12 + tmo) - (now.getUTCFullYear() * 12 + now.getUTCMonth());
    elapsed = cmp > 0 ? 0 : (cmp < 0 ? 1 : Math.min(1, now.getUTCDate() / totDays));
  }
  var iApp = idxByType_(M.stageTypes, ['entry', 'reserve', '予約']); if (iApp < 0) iApp = 0;
  var entryAct = M.counts[iApp] || 0;
  var entryFc = (elapsed && elapsed > 0 && elapsed < 1) ? Math.round(entryAct / elapsed) : entryAct;
  function cumRate(iGoal) { var r = 1; for (var k = iApp + 1; k <= iGoal; k++) r *= stepRate_(M, k); return r; }
  function forecastAt(iGoal) {
    if (elapsed == null || elapsed >= 1) return M.counts[iGoal] || 0;  // 終了/不明は実績
    return Math.max(M.counts[iGoal] || 0, Math.round(entryFc * cumRate(iGoal)));
  }
  var goals = [];
  var ord = [['offer', '内定'], ['accept', '承諾'], ['join', '入社']];
  var pri0 = primaryGoalType_();
  ord.sort(function (a, b) { return (a[0] === pri0 ? 1 : 0) - (b[0] === pri0 ? 1 : 0); });  // 主要指標を末尾(=ダッシュの主役)へ
  ord.forEach(function (gt) {
    var idx = idxByType_(M.stageTypes, [gt[0]]); if (idx < 0) return;
    var act = M.counts[idx], tgt = M.target[gt[1]] || 0;
    var rate = tgt > 0 ? act / tgt : null;
    var p = (elapsed && elapsed > 0 && rate != null) ? rate / elapsed : null;
    var status = (p == null) ? '—' : (p >= 1 ? '🟢' : (p >= 0.8 ? '🟡' : '🔴'));
    goals.push({ type: gt[0], name: M.stageNames[idx], idx: idx, tgt: tgt, act: act, rate: rate, pace: p, status: status, forecast: forecastAt(idx) });
  });
  return { elapsed: elapsed, label: label, entryForecast: entryFc, goals: goals };
}
// ペースセルの表示文字列(🟢1.13 等)
function paceText_(g) { return g.pace == null ? '—' : (g.status + Math.round(g.pace * 100) / 100); }
// 5段正規化ファネル(応募/書類/面接/内定/確定)の到達数
function normalizedFunnel_(M) {
  // 予約/参加(reserve/attend)も認識: 予約=応募段, 参加=面接段。合格=内定段。
  var iApp = idxByType_(M.stageTypes, ['entry', 'reserve', '予約']); if (iApp < 0) iApp = 0;
  var iScr = idxByType_(M.stageTypes, ['screen', '書類']); if (iScr < 0) iScr = iApp;
  var iInt = idxByType_(M.stageTypes, ['interview', 'task', 'attend', '参加']); if (iInt < 0) iInt = iScr;
  var iOff = idxByType_(M.stageTypes, ['offer', '合格']); if (iOff < 0) iOff = iInt;
  var iFin = idxByType_(M.stageTypes, ['join']);
  if (iFin < 0) iFin = idxByType_(M.stageTypes, ['accept']);
  if (iFin < 0) iFin = iOff;
  var c = M.counts;
  return { app: c[iApp] || 0, doc: c[iScr] || 0, interview: c[iInt] || 0, offer: c[iOff] || 0, fin: c[iFin] || 0 };
}

// WP11: 詳細分析パネルを key で描画(表示パネル設定で出し分け)
function renderPanel_(sh, row, key, M, seg) {
  switch (key) {
    case 'stepyield':
      return section_(sh, row, '① ステージ間 歩留まり（前段比・累積・離脱）', buildStepYield_(M.stageNames, M.counts), [2, 3, 4]);
    case 'monthly':
      var mo = buildMonthly_(M.rows, M.H, M.stageNames, M.idxOf);
      return section_(sh, row, '② 月次推移（応募月別コホートの歩留まり）', mo, [mo.header.length - 2, mo.header.length - 1]);
    case 'channel': { var tc = buildByKey_(M.rows, M.H, M.stageNames, M.idxOf, 'チャネル'); return section_(sh, row, '③ チャネル別 ファネル＆全ステージ通過率', tc, tc.redCols); }
    case 'job': { var tj = buildByJob_(M.rows, M.H, M.stageNames, M.idxOf, seg, M.stageTypes); return section_(sh, row, '④ 職種別 ファネル＆通過率＆目標充足', tj, tj.redCols); }
    case 'reasons':
      return section_(sh, row, '⑤ 見送り・辞退 理由内訳', buildReasons_(M.rows, M.H), [2]);
    case 'chxmonth':
      return section_(sh, row, '⑥ チャネル×月（応募数の推移）', buildMonthlyCross_(M.rows, M.H, 'チャネル'), []);
    case 'jobxmonth':
      return section_(sh, row, '⑦ 職種×月（応募数の推移）', buildMonthlyCross_(M.rows, M.H, '職種'), []);
    case 'monthfunnel':
      return section_(sh, row, '⑧ 月次ファネル（コホート・件数＋遷移率）', buildPeriodFunnel_(M, 'month'), []);
    case 'weekfunnel':
      return section_(sh, row, '⑨ 週次ファネル（直近12週・件数＋遷移率）', buildPeriodFunnel_(M, 'week'), []);
    case 'university': { var tu = buildByKey_(M.rows, M.H, M.stageNames, M.idxOf, '大学'); return section_(sh, row, '⑩ 大学別 ファネル＆全ステージ通過率', tu, tu.redCols); }
    case 'competitor':
      return section_(sh, row, '⑪ 競合先別（接触・勝敗・勝率）', buildCompetitor_(M.rows, M.H), [4]);
    case 'rc': { var tr = buildByKey_(M.rows, M.H, M.stageNames, M.idxOf, '採用担当RC'); return section_(sh, row, '⑫ 担当RC別 ファネル＆全ステージ通過率', tr, tr.redCols); }
    case 'score':
      return section_(sh, row, '⑬ 総合評価(S〜D) 分布', buildScoreDist_(M.rows, M.H), [2]);
    case 'gender': { var tg = buildByKey_(M.rows, M.H, M.stageNames, M.idxOf, '性別'); return section_(sh, row, '⑭ 性別別 ファネル＆全ステージ通過率', tg, tg.redCols); }
    case 'age': { var ta = buildByAge_(M.rows, M.H, M.stageNames, M.idxOf); return section_(sh, row, '⑮ 年齢別 ファネル＆全ステージ通過率', ta, ta.redCols); }
    case 'yomi': return buildYomiMetricsPanel_(sh, row, M, seg);
  }
  return row;
}

// ⑪ 競合先別: 接触数・自社勝ち(承諾/入社)・負け(辞退)・勝率
function buildCompetitor_(rows, H) {
  var g = {};
  rows.forEach(function (r) {
    var c = String(r[H['競合先']] || '').trim(); if (!c) return;
    if (!g[c]) g[c] = { n: 0, win: 0, lose: 0 };
    g[c].n++;
    var st = String(r[H['ステータス']]);
    if (st === '承諾' || st === '入社') g[c].win++; else if (st === '辞退') g[c].lose++;
  });
  var keys = Object.keys(g).sort(function (a, b) { return g[b].n - g[a].n; });
  var data = keys.map(function (k) { var x = g[k], d = x.win + x.lose; return [k, x.n, x.win, x.lose, d ? Math.round(x.win / d * 100) + '%' : '—']; });
  return { header: ['競合先', '接触', '自社勝ち', '負け(辞退)', '勝率'], rows: data };
}

// ⑬ 総合評価(S〜D)の分布
function buildScoreDist_(rows, H) {
  var order = ['S', 'A', 'B', 'C', 'D'], cnt = {}, total = 0;
  rows.forEach(function (r) {
    var v = String(r[H['総合評価']] || '').trim(); if (!v) return;
    var letter = v.charAt(0); if (order.indexOf(letter) < 0) return;
    cnt[letter] = (cnt[letter] || 0) + 1; total++;
  });
  var data = order.filter(function (l) { return cnt[l]; }).map(function (l) { return [l, cnt[l], pct_(cnt[l], total)]; });
  return { header: ['評価', '人数', '構成比'], rows: data };
}

function renderMidDash_() { renderSegmentDash_(SH.D_MID, '中途'); }

function renderSegmentDash_(sheetName, seg) {
  var sh = sheet_(sheetName);
  clearSheet_(sh);
  ensureGrid_(sh, 200, 28);

  // 列幅(画面幅を活用・均一でヒーローを左右対称に)
  sh.setColumnWidth(1, 28);
  for (var c = 2; c <= 19; c++) sh.setColumnWidth(c, 92);

  var M = computeSegment_(seg);
  var now = nowTokyo_();
  var ymLabel = now.getUTCFullYear() + '年' + (now.getUTCMonth() + 1) + '月';
  bandTitle_(sh, 1, 2, 19, '■ ' + companyName_() + ' 採用ダッシュボード ─ ' + seg + '    （' + ymLabel + '時点）');

  if (!M.stageNames.length) {
    sh.getRange(3, 2).setValue('01_設定 に「' + seg + '」のステージ定義がありません。設定後に更新してください。')
      .setFontColor(C.SUB).setFontSize(11);
    return;
  }

  // === KPIヒーロー(主役・2段: ヘッドライン4枚＋補助) ===
  var fg = finalGoal_(M);
  var ds = docStats_(seg);
  kpiHero_(sh, 3, [
    { label: '進行中', value: M.active },
    { label: '今月 内定', value: M.offM },
    { label: '今月 承諾', value: M.accM },
    { label: (fg ? fg.name + ' 達成 ' + fg.act + '/' + fg.tgt : '目標達成'), value: (fg ? pct_(fg.act, fg.tgt) : '—'), accent: true }
  ], 2, 3, { big: true });
  kpiHero_(sh, 6, [
    { label: '平均選考日数', value: (M.avgDays != null ? M.avgDays + '日' : '—') },
    { label: '書類回収率 ' + ds.collected + '/' + ds.target, value: ds.target ? ds.rate : '—' }
  ], 2, 3);

  // ファネル(左) + 目標(中) + チャート(右)。ヒーロー(3〜7)の下から。
  var funnelTop = 9;
  var funnelRows = M.stageNames.map(function (n, i) {
    var cvr = (i === 0) ? '—' : pct_(M.counts[i], M.counts[i - 1]);
    return [n, M.counts[i], cvr, bar_(M.counts[i], M.counts[0], 10)];
  });
  sectionHead_(sh, funnelTop, 2, 4, '選考ファネル');
  var leftEnd = table_(sh, funnelTop + 1, 2, ['ステージ', '到達数', '通過率', '推移'], funnelRows, [3]);

  var pc = pace_(M);
  var goalRows = pc.goals.map(function (g) {
    return [g.name, g.tgt, g.act, pct_(g.act, g.tgt), paceText_(g), g.forecast];
  });
  if (!goalRows.length) goalRows = [['—', 0, 0, '—', '—', 0]];
  sectionHead_(sh, funnelTop, 7, 6, '目標 vs 進捗（ペース・着地予想）');
  var gEnd = table_(sh, funnelTop + 1, 7, ['指標', '目標', '実績', '達成率', 'ペース', '着地予想'], goalRows, [4]);
  if (pc.elapsed != null) {
    sh.getRange(gEnd, 7, 1, 6).merge()
      .setValue('※ ' + (pc.label || '対象月') + '：' + Math.round(pc.elapsed * 100) + '% 経過 ／ ペース=達成率÷経過率（🟢順調 🟡注意 🔴遅れ）／ 着地=応募日割×通過率カスケード')
      .setFontColor(C.SUB).setFontSize(8).setWrap(true).setVerticalAlignment('top');
    sh.setRowHeight(gEnd, 28);
  }

  // チャート(右 N列〜): 目標 vs 実績 vs 着地バー + 経路別円。元データは off-screen(U列〜)。
  var cd = 21;
  var goalData = [['指標', '目標', '実績', '着地']].concat(pc.goals.map(function (g) { return [g.name, g.tgt, g.act, g.forecast]; }));
  if (goalData.length < 2) goalData.push(['—', 0, 0, 0]);
  sh.getRange(3, cd, goalData.length, 4).setValues(goalData);
  addColumnChart_(sh, sh.getRange(3, cd, goalData.length, 4), funnelTop, 14, seg + '：目標 vs 実績 vs 着地');

  var chT = buildByKey_(M.rows, M.H, M.stageNames, M.idxOf, 'チャネル');
  var chData = [['チャネル', '応募']].concat(chT.rows.map(function (r) { return [r[0], Number(r[1]) || 0]; }));
  if (chData.length < 2) chData.push(['(データなし)', 0]);
  sh.getRange(3, cd + 5, chData.length, 2).setValues(chData);
  addPieChart_(sh, sh.getRange(3, cd + 5, chData.length, 2), funnelTop + 14, 14, '応募 経路別構成');
  // 元データはU列以降(画面のA〜S外)に置く。列は隠さない(隠すとグラフが空になるため)。

  // === サマリの下: 詳細分析(WP11: 表示パネル設定で出し分け・表示順) ===
  var row = leftEnd + 1;
  sectionHead_(sh, row, 2, 12, '詳細分析'); row += 2;
  var panels = enabledPanels_();
  for (var pi = 0; pi < panels.length; pi++) row = renderPanel_(sh, row, panels[pi], M, seg);

  // フッター
  var tz = ss_().getSpreadsheetTimeZone();
  sh.getRange(row + 1, 2, 1, 12).merge()
    .setValue('最終更新: ' + Utilities.formatDate(new Date(), tz, 'yyyy-MM-dd HH:mm')
      + '  ／  入力は 10_候補者マスタ・11_面接スケジュール、設定は 01_設定')
    .setFontColor(C.SUB).setFontSize(9);
}

/* ============================== 区分別 ②進捗管理タブ ============================== */
// 10_候補者マスタ(正本)を区分でフィルタし、進捗(作業ビュー)＋区分固有の取得項目を名前単位で管理する編集可能タブ。
// 作業ビュー列(MANAGE_VIEW_COLS)の編集 → onEdit(syncManageEditToMaster_) で候補者IDを引き当てマスタへ書き戻し(正本=マスタ)。
// 区分固有項目(SEG_FIELDS)とメモは②タブ側に保持(再生成時も候補者IDで保持＝buildBriefingWork_と同方式)。
function manageName_(seg) { return (seg + MANAGE_SUFFIX).slice(0, 95); }
// 新卒②のアンケート閲覧列(②保持・編集可・設定❿のSEG_FIELDSとは別の固定ビュー列)。説明会/一次面接ESの主要項目。
function surveyViewCols_(seg) {
  if (seg !== '新卒') return [];
  return ['満足度理由', '就活終了時期', '挑戦したいこと', '一次面接官', '一次志望度', '一次志望理由', '一次印象', '一次気になる点', '一次悩み', '志望企業'];
}
// 各選考段の評価入力列(全区分共通・②保持・編集可)。選考段＝type が entry/offer/accept/join 以外(説明選考会/一次/カジュアル/1day/二次/最終)。
function perStageEvalCols_(seg) {
  var out = [];
  segStages_(seg).forEach(function (s) {
    if (['entry', 'offer', 'accept', 'join'].indexOf(s.type) >= 0) return;
    out.push(s.name + '_評価'); out.push(s.name + '_合否'); out.push(s.name + '_所感');
  });
  return out;
}
function manageCols_(seg) {
  return ['候補者ID', '氏名'].concat(MANAGE_REF_COLS).concat(MANAGE_VIEW_COLS)
    .concat(segFields_(seg)).concat(surveyViewCols_(seg)).concat(perStageEvalCols_(seg)).concat(segOwnExtra_(seg)).concat(['メモ']);
}
function manageColWidth_(cn) {
  if (cn === '候補者ID') return 100;
  if (cn === '氏名' || cn === 'ポートフォリオURL') return 110;
  if (/_評価$|_合否$/.test(cn)) return 64;
  if (/満足度$|参加状況|卒業年度|文理|インターン参加/.test(cn)) return 90;
  if (/所感$|理由$|挑戦したいこと|印象|気になる点|悩み|志望企業|志望度|メモ|転職理由|ネクストアクション/.test(cn)) return 200;
  return 96;
}

// allowIds(任意): {candidate_id:true} の集合を渡すと、その候補者だけに母集団を絞る(新卒②=説明会参加者のみ 等)。
function buildSegManage_(seg, allowIds) {
  var ss = ss_(), name = manageName_(seg);
  var existed = !!ss.getSheetByName(name);
  var sh = ss.getSheetByName(name) || ss.insertSheet(name);
  var tz = ss.getSpreadsheetTimeZone();
  var cols = manageCols_(seg), w = cols.length;
  var segF = segFields_(seg);
  var ownCols = segF.concat(surveyViewCols_(seg)).concat(perStageEvalCols_(seg)).concat(segOwnExtra_(seg)).concat(['メモ']);  // ②保持列(候補者IDキー・区分固有＋アンケート閲覧＋各段評価＋ヨミ項目)
  function colIdx(cn) { return cols.indexOf(cn); }

  // 既存の②保持列を候補者IDで退避(継続運用=手入力保持)
  var keep = {};
  if (existed && sh.getLastRow() >= 3 && sh.getLastColumn() >= 3) {
    var od = sh.getRange(2, 2, sh.getLastRow() - 1, sh.getLastColumn() - 1).getValues();
    var oH = {}; (od[0] || []).forEach(function (h, i) { oH[String(h)] = i; });
    for (var i = 1; i < od.length; i++) {
      var c0 = String((oH['候補者ID'] != null ? od[i][oH['候補者ID']] : '') || '').trim(); if (!c0) continue;
      keep[c0] = {}; ownCols.forEach(function (cn) { if (oH[cn] != null) keep[c0][cn] = od[i][oH[cn]]; });
    }
  }
  // フォーム由来の区分固有項目(segStash・onFormSubmitが候補者IDで保存)を②へマージ。②の手入力が優先＝空のみ補完。
  try {
    var sj = JSON.parse(PropertiesService.getDocumentProperties().getProperty('segStash') || '{}');
    for (var sc in sj) { if (!keep[sc]) keep[sc] = {}; for (var sf in sj[sc]) { if (ownCols.indexOf(sf) >= 0 && (keep[sc][sf] == null || keep[sc][sf] === '')) keep[sc][sf] = sj[sc][sf]; } }
  } catch (e) {}

  var M = computeSegment_(seg), H = M.H;
  var rows = M.rows.slice();
  if (allowIds) rows = rows.filter(function (r) { return allowIds[String(r[H['candidate_id']] || '').trim()]; });
  rows.sort(function (a, b) {
    var ta = (a[H['応募日']] instanceof Date) ? a[H['応募日']].getTime() : 0;
    var tb = (b[H['応募日']] instanceof Date) ? b[H['応募日']].getTime() : 0;
    return tb - ta;
  });
  var body = rows.map(function (r) {
    var cid = String(r[H['candidate_id']] || ''), kp = keep[cid] || {};
    return cols.map(function (cn) {
      if (cn === '候補者ID') return cid;
      if (ownCols.indexOf(cn) >= 0) return (kp[cn] != null ? kp[cn] : '');
      var v = (H[cn] != null) ? r[H[cn]] : '';
      return (v == null) ? '' : v;  // Date はそのまま(列書式で表示・編集で往復)
    });
  });

  clearSheet_(sh);
  var N = Math.max(rows.length + 30, 60);
  ensureGrid_(sh, N + 3, w + 1);
  bandTitle_(sh, 1, 2, w + 1, '■ ' + companyName_() + '　' + seg + ' 進捗管理（バイネーム・進捗はマスタへ自動同期）');
  sh.getRange(2, 2, 1, w).setValues([cols]).setBackground(HEAD_BG).setFontColor(C.INK).setFontWeight('bold').setFontSize(9).setHorizontalAlignment('center');
  var dataTop = 3;
  if (rows.length) sh.getRange(dataTop, 2, rows.length, w).setValues(body).setFontSize(10).setVerticalAlignment('middle').setWrap(true);
  // ゼブラ予約行まで
  var bgs = []; for (var z = 0; z < N; z++) { var line = []; for (var x = 0; x < w; x++) line.push(z % 2 ? C.ZEBRA : C.WHITE); bgs.push(line); }
  sh.getRange(dataTop, 2, N, w).setBackgrounds(bgs);
  // REF=自動(グレー) / VIEW・固有・メモ=入力(ピンク)
  MANAGE_REF_COLS.forEach(function (cn) { var i = colIdx(cn); if (i >= 0) sh.getRange(dataTop, 2 + i, N, 1).setBackground(DESIGN_AUTO_BG); });
  MANAGE_VIEW_COLS.concat(ownCols).forEach(function (cn) { var i = colIdx(cn); if (i >= 0) sh.getRange(dataTop, 2 + i, N, 1).setBackground(DESIGN_INPUT_BG); });
  // 日付書式(応募日 ref + 作業ビューの日付)
  ['応募日'].concat(Object.keys(MANAGE_DATE_COLS)).forEach(function (cn) { var i = colIdx(cn); if (i >= 0) sh.getRange(dataTop, 2 + i, N, 1).setNumberFormat('yyyy/mm/dd'); });
  // 入力規則(作業ビュー)
  function setList(cn, list) { var i = colIdx(cn); if (i >= 0 && list && list.length) sh.getRange(dataTop, 2 + i, N, 1).setDataValidation(SpreadsheetApp.newDataValidation().requireValueInList(list, true).setAllowInvalid(true).build()); }
  setList('現ステージ', M.stageNames);
  setList('ステータス', STATUSES);
  setList('総合評価', IV_SCORE);
  setList('見送り辞退理由', REASONS);
  setList('ヨミランク', YOMI_RANKS);  // 新卒以外は②にヨミ管理を内包
  perStageEvalCols_(seg).forEach(function (cn) { if (/_評価$/.test(cn)) setList(cn, IV_SCORE); else if (/_合否$/.test(cn)) setList(cn, IV_RESULT); });  // 各選考段の評価/合否プルダウン
  sh.getRange(2, 2, N + 1, w).setBorder(true, true, true, true, true, true, C.BORDER, SpreadsheetApp.BorderStyle.SOLID);
  sh.setColumnWidth(1, 28);
  for (var ci = 0; ci < w; ci++) sh.setColumnWidth(2 + ci, manageColWidth_(cols[ci]));
  var extra = segOwnExtra_(seg);
  note_(sh, dataTop + N + 1, w, seg + 'の候補者をバイネームで管理。グレー列(' + MANAGE_REF_COLS.join('/') + ')=マスタ自動。ピンク列=入力／うち「' + MANAGE_VIEW_COLS.join('・') + '」はマスタ(10_候補者マスタ)へ自動同期＝正本はマスタ。'
    + (segF.length ? '区分固有項目(' + segF.join('/') + '・01_設定❿で編集可)とメモはこのタブに保存(再生成しても保持)。' : 'メモはこのタブに保存。')
    + (extra.length ? 'ヨミ管理(' + extra.join('/') + ')もこのタブで管理(⑯ヨミ計測パネルに集計)。' : ''));
  if (!existed) {  // 新規作成時のみ 12_面接評価ノートの直後へ配置
    var ns = ss.getSheetByName(SH.NOTE); if (ns) { try { ss.setActiveSheet(sh); ss.moveActiveSheet(ns.getIndex() + 1); } catch (e) {} }
  }
  return rows.length;
}

// ②の作業ビュー列の編集をマスタへ書き戻す(正本=マスタ)。onEditから呼ぶ。
function syncManageEditToMaster_(e, sh) {
  var lc = sh.getLastColumn(); if (lc < 2) return;
  var hdr = sh.getRange(2, 1, 1, lc).getValues()[0];
  var oH = {}; hdr.forEach(function (h, i) { oH[String(h)] = i + 1; });  // 1-based col
  var col = e.range.getColumn(), row = e.range.getRow(); if (row < 3) return;
  var label = null; for (var k in oH) { if (oH[k] === col) { label = k; break; } }
  if (!label || MANAGE_VIEW_COLS.indexOf(label) < 0) return;  // 作業ビュー列のみ同期
  if (oH['候補者ID'] == null) return;
  var cid = String(sh.getRange(row, oH['候補者ID']).getValue() || '').trim(); if (!cid) return;
  var m = sheet_(SH.MASTER), md = m.getDataRange().getValues(), mH = headerIndex_(md[0]);
  if (mH[label] == null || mH['candidate_id'] == null) return;
  var target = -1; for (var i = 1; i < md.length; i++) { if (String(md[i][mH['candidate_id']]).trim() === cid) { target = i; break; } }
  if (target < 0) return;
  var val = e.range.getValue();
  if (MANAGE_DATE_COLS[label]) { var d = parseDateLoose_(val); m.getRange(target + 1, mH[label] + 1).setValue(d || ''); }
  else m.getRange(target + 1, mH[label] + 1).setValue(val == null ? '' : val);
}

// 説明会参加者(新卒②の母集団): 11_の「説明会」ステージに行がある候補者IDの集合。
// 新卒②(説明会参加者)の母体。命名("説明会"/"説明選考会")非依存=master現ステージが
// 説明会段(screen/attend型 or 名前に"説明"含む段)以降に到達した候補者。＋11_説明会イベント参加者もunion(他社で11_運用時の後方互換)。
function briefingParticipantIds_() {
  var set = {};
  try {
    var M = computeSegment_('新卒'), H = M.H;
    // 説明会段のindexを特定(最初の screen/attend、無ければ名前に"説明"を含む段、無ければ2段目)
    var bi = -1;
    for (var k = 0; k < M.stageNames.length; k++) {
      if (M.stageTypes[k] === 'screen' || M.stageTypes[k] === 'attend' || String(M.stageNames[k]).indexOf('説明') >= 0) { bi = k; break; }
    }
    if (bi < 0) bi = Math.min(1, M.stageNames.length - 1);
    M.rows.forEach(function (r) {
      var cur = String(r[H['現ステージ']] || ''), si = M.idxOf[cur];
      if (si != null && si >= bi) { var c = String(r[H['candidate_id']] || '').trim(); if (c) set[c] = true; }
    });
  } catch (e) {}
  // 11_面接スケジュールの説明会(=説明含む)イベント参加者もunion
  try {
    var iv = ss_().getSheetByName(SH.IV);
    if (iv && iv.getLastRow() >= 2) {
      var d = iv.getDataRange().getValues(), H2 = headerIndex_(d[0]);
      for (var i = 1; i < d.length; i++) {
        if (String(d[i][H2['ステージ']] || '').indexOf('説明') < 0) continue;
        var cc = String(d[i][H2['candidate_id']] || '').trim(); if (cc) set[cc] = true;
      }
    }
  } catch (e2) {}
  return set;
}

/* ============================== ③ 新卒_ヨミ管理 ============================== */
// 最終フェーズ近く(現ステージが終盤) or 内定/承諾/入社 の候補者を、採用確度・クロージングで厚く管理。新卒の3部構成の③。
var YOMI_SUFFIX = '_ヨミ管理';
// ③新卒_ヨミ管理: 読取(マスタ自動)列 + ③保持(入力)列。新卒以外はヨミを②に内包(segOwnExtra_)。
var YOMI_READ = ['候補者ID', '氏名', '大学', '学部', '学科', '性別', '職種', 'チャネル', '採用担当RC', '現ステージ', 'ステータス', '総合評価', '直近面接日', '内定日', '承諾日'];
var YOMI_OWN3 = YOMI_OWN.concat(['ネクストアクション', 'メモ']);  // ③はマスタ非同期=NA/メモも③ローカル保持
var YOMI_SURVEY = ['アンケート満足度', '志望度'];  // ②進捗管理(新卒)から候補者IDで読む(③でアンケート結果も確認・読取専用)
function yomiName_(seg) { return (seg + YOMI_SUFFIX).slice(0, 95); }
// ヨミ母集団(終盤フェーズ近く or 内定/承諾/入社・見送り辞退は除外)。buildYomi_ とヨミ計測パネルで共有。
function yomiPopulation_(M) {
  var H = M.H, n = M.stageNames.length, threshold = Math.max(0, n - 3);
  return M.rows.filter(function (r) {
    var st = String(r[H['ステータス']] || '');
    if (st === '見送り' || st === '辞退') return false;
    if (st === '内定' || st === '承諾' || st === '入社') return true;
    var si = M.idxOf[String(r[H['現ステージ']] || '')];
    return (si != null && si >= threshold);
  });
}
function buildYomi_(seg) {
  var ss = ss_(), name = yomiName_(seg);
  var existed = !!ss.getSheetByName(name);
  var sh = ss.getSheetByName(name) || ss.insertSheet(name);
  var M = computeSegment_(seg), H = M.H;
  var hot = yomiPopulation_(M);
  // ②進捗管理(新卒)から アンケート満足度/志望度 を候補者IDで取得し ③に読取表示する。
  var surveyMap = {};
  try {
    var mgr = ss.getSheetByName(manageName_(seg));
    if (mgr && mgr.getLastRow() >= 3 && mgr.getLastColumn() >= 3) {
      var gd = mgr.getRange(2, 2, mgr.getLastRow() - 1, mgr.getLastColumn() - 1).getValues();
      var gH = {}; (gd[0] || []).forEach(function (h, i) { gH[String(h)] = i; });
      if (gH['候補者ID'] != null) for (var gi = 1; gi < gd.length; gi++) {
        var gc = String(gd[gi][gH['候補者ID']] || '').trim(); if (!gc) continue;
        surveyMap[gc] = {};
        YOMI_SURVEY.forEach(function (cn) { if (gH[cn] != null) surveyMap[gc][cn] = gd[gi][gH[cn]]; });
      }
    }
  } catch (e) { Logger.log('buildYomi_ surveyMap: ' + e); }
  var cols = YOMI_READ.concat(YOMI_SURVEY).concat(YOMI_OWN3), w = cols.length;
  var keep = {};
  if (existed && sh.getLastRow() >= 3 && sh.getLastColumn() >= 3) {
    var od = sh.getRange(2, 2, sh.getLastRow() - 1, sh.getLastColumn() - 1).getValues();
    var oH = {}; (od[0] || []).forEach(function (h, i) { oH[String(h)] = i; });
    for (var i = 1; i < od.length; i++) { var c0 = String((oH['候補者ID'] != null ? od[i][oH['候補者ID']] : '') || '').trim(); if (!c0) continue; keep[c0] = {}; YOMI_OWN3.forEach(function (cn) { if (oH[cn] != null) keep[c0][cn] = od[i][oH[cn]]; }); }
  }
  hot.sort(function (a, b) { var sa = M.idxOf[String(a[H['現ステージ']] || '')] || 0, sb = M.idxOf[String(b[H['現ステージ']] || '')] || 0; return sb - sa; });
  var body = hot.map(function (r) {
    var cid = String(r[H['candidate_id']] || ''), kp = keep[cid] || {};
    return cols.map(function (cn) {
      if (cn === '候補者ID') return cid;
      if (YOMI_OWN3.indexOf(cn) >= 0) return (kp[cn] != null ? kp[cn] : '');
      if (YOMI_SURVEY.indexOf(cn) >= 0) { var sv = surveyMap[cid] || {}; return (sv[cn] != null ? sv[cn] : ''); }
      var v = (H[cn] != null) ? r[H[cn]] : ''; return (v == null) ? '' : v;
    });
  });
  clearSheet_(sh);
  var N = Math.max(hot.length + 20, 40);
  ensureGrid_(sh, N + 3, w + 1);
  bandTitle_(sh, 1, 2, w + 1, '■ ' + companyName_() + '　' + seg + ' ヨミ管理（最終フェーズ近く・採用確度を厚く管理）');
  sh.getRange(2, 2, 1, w).setValues([cols]).setBackground(HEAD_BG).setFontColor(C.INK).setFontWeight('bold').setFontSize(9).setHorizontalAlignment('center');
  if (hot.length) sh.getRange(3, 2, hot.length, w).setValues(body).setFontSize(10).setVerticalAlignment('middle').setWrap(true);
  var bgs = []; for (var z = 0; z < N; z++) { var line = []; for (var x = 0; x < w; x++) line.push(z % 2 ? C.ZEBRA : C.WHITE); bgs.push(line); }
  sh.getRange(3, 2, N, w).setBackgrounds(bgs);
  YOMI_OWN3.forEach(function (cn) { var i = cols.indexOf(cn); if (i >= 0) sh.getRange(3, 2 + i, N, 1).setBackground(DESIGN_INPUT_BG); });
  YOMI_READ.concat(YOMI_SURVEY).forEach(function (cn) { var i = cols.indexOf(cn); if (i >= 0) sh.getRange(3, 2 + i, N, 1).setBackground(DESIGN_AUTO_BG); });
  ['直近面接日', '内定日', '承諾日'].forEach(function (cn) { var i = cols.indexOf(cn); if (i >= 0) sh.getRange(3, 2 + i, N, 1).setNumberFormat('yyyy/mm/dd'); });
  var ri = cols.indexOf('ヨミランク'); if (ri >= 0) sh.getRange(3, 2 + ri, N, 1).setDataValidation(SpreadsheetApp.newDataValidation().requireValueInList(YOMI_RANKS, true).setAllowInvalid(true).build());
  sh.getRange(2, 2, N + 1, w).setBorder(true, true, true, true, true, true, C.BORDER, SpreadsheetApp.BorderStyle.SOLID);
  sh.setColumnWidth(1, 28);
  for (var ci = 0; ci < w; ci++) sh.setColumnWidth(2 + ci, manageColWidth_(cols[ci]));
  note_(sh, 3 + N + 1, w, seg + 'の終盤フェーズ(終盤' + Math.min(3, M.stageNames.length) + 'ステージ)到達 or 内定/承諾/入社を自動抽出。グレー=マスタ自動・ピンク=入力(このタブに保存・再生成で保持)。採用確度は「⑯ヨミ計測」パネル(新卒ダッシュ)に集計。');
  if (!existed) { var ms = ss.getSheetByName(manageName_(seg)) || ss.getSheetByName(SH.NOTE); if (ms) { try { ss.setActiveSheet(sh); ss.moveActiveSheet(ms.getIndex() + 1); } catch (e) {} } }
  return hot.length;
}

// ヨミランクの候補者ID→ランク マップ。新卒=③ヨミ管理タブ・他区分=②進捗管理タブ から読む。
function yomiRankMap_(seg) {
  var name = (seg === '新卒') ? yomiName_(seg) : manageName_(seg);
  var sh = ss_().getSheetByName(name); if (!sh || sh.getLastRow() < 3) return {};
  var lc = sh.getLastColumn(), hdr = sh.getRange(2, 1, 1, lc).getValues()[0], oH = {};
  hdr.forEach(function (h, i) { oH[String(h)] = i; });
  if (oH['候補者ID'] == null || oH['ヨミランク'] == null) return {};
  var d = sh.getRange(3, 1, sh.getLastRow() - 2, lc).getValues(), map = {};
  d.forEach(function (r) { var c = String(r[oH['候補者ID']] || '').trim(); if (c) map[c] = String(r[oH['ヨミランク']] || '').trim(); });
  return map;
}

// ⑯ ヨミ計測パネル: ヨミ母集団の 全体/確度別/ステージ別/内定/承諾/歩留まり を集計(各区分ダッシュ)。
function buildYomiMetricsPanel_(sh, row, M, seg) {
  var H = M.H, pop = yomiPopulation_(M), total = pop.length, rankMap = yomiRankMap_(seg);
  var rankCount = {}; YOMI_RANKS.forEach(function (rr) { rankCount[rr.charAt(0)] = 0; }); var rankUnset = 0;
  var stageCount = {}, offers = 0, accepts = 0;
  pop.forEach(function (r) {
    var cid = String(r[H['candidate_id']] || '').trim();
    var rk = String(rankMap[cid] || '').charAt(0);
    if (rk && rankCount[rk] != null) rankCount[rk]++; else rankUnset++;
    var stg = String(r[H['現ステージ']] || '不明'); stageCount[stg] = (stageCount[stg] || 0) + 1;
    var st = String(r[H['ステータス']] || '');
    if ((r[H['内定日']] instanceof Date) || st === '内定' || st === '承諾' || st === '入社') offers++;
    if ((r[H['承諾日']] instanceof Date) || st === '承諾' || st === '入社') accepts++;
  });
  sh.getRange(row, 2).setValue('▎⑯ ヨミ計測（採用確度・歩留まり）').setFontColor(C.BLACK).setFontWeight('bold').setFontSize(11); row += 1;
  row = table_(sh, row, 2, ['指標', '人数/率'], [
    ['ヨミ対象 全体', total], ['内定', offers], ['内定承諾', accepts],
    ['ヨミ→内定 歩留まり', pct_(offers, total)], ['内定→承諾 歩留まり', pct_(accepts, offers)], ['ヨミ→承諾 歩留まり', pct_(accepts, total)]
  ], [1]);
  var rankRows = YOMI_RANKS.map(function (rr) { var k = rr.charAt(0); return [rr, rankCount[k] || 0, pct_(rankCount[k] || 0, total)]; });
  rankRows.push(['未設定', rankUnset, pct_(rankUnset, total)]);
  sh.getRange(row, 2).setValue('▎ヨミ確度別 人数').setFontColor(C.BLACK).setFontWeight('bold').setFontSize(11); row += 1;
  row = table_(sh, row, 2, ['ヨミランク', '人数', '構成比'], rankRows, [1]);
  var stRows = M.stageNames.filter(function (s) { return stageCount[s]; }).map(function (s) { return [s, stageCount[s], pct_(stageCount[s], total)]; });
  sh.getRange(row, 2).setValue('▎選考ステータス別（ヨミ母集団）').setFontColor(C.BLACK).setFontWeight('bold').setFontSize(11); row += 1;
  row = table_(sh, row, 2, ['現ステージ', '人数', '構成比'], stRows.length ? stRows : [['(該当なし)', '', '']], [1]);
  return row;
}

/* ============================== チャネル候補マスタ(研究リスト・区分レーン) ============================== */
// 世の中のスカウト媒体・エージェント＋自社の実パートナーを区分レーン(共通/新卒/中途)で一覧。有効✓で使うものを選ぶ。
// 派遣・媒体(求人広告型)・北陸地域は除外。※現時点は参考マスタ(独立タブ)。01_設定「チャネル定義」の稼働分との統合は次ステップ。
var CHMASTER_BASE_COL = 20;  // 01_設定の右側(T列〜)に折り込む。バンド(A〜R=1-18)と列を分け、列幅競合を回避(横に広くなる)。
// 基本チャネルは既定で有効(band2撤去後も直接応募/リファラル等が稼働チャネルに常にある)。再生成で常にON。
var CHMASTER_DEFAULT_ON = { '直接応募': 1, 'リファラル': 1, '自社採用サイト': 1, 'SNS(X/Instagram等)': 1 };
var CHMASTER = {
  '共通': [['直接応募', 'organic'], ['リファラル', 'referral'], ['自社採用サイト', 'organic'], ['SNS(X/Instagram等)', 'organic'], ['Wantedly', 'scout'], ['LinkedIn', 'scout'], ['YOUTRUST', 'scout'], ['株式会社マイナビ', 'agent'], ['株式会社ネオキャリア', 'agent'], ['レバレジーズ株式会社', 'agent'], ['株式会社キャリアデザインセンター', 'agent'], ['株式会社スポーツフィールド', 'agent'], ['TOKUMORI(自社)', 'referral']],
  '新卒': [['OfferBox', 'scout'], ['dodaキャンパス', 'scout'], ['キミスカ', 'scout'], ['iroots', 'scout'], ['ONE CAREERスカウト', 'scout'], ['ビズリーチ・キャンパス', 'scout'], ['Matcher Scout', 'scout'], ['Future Finder', 'scout'], ['チアキャリア', 'scout'], ['JOBRASS新卒', 'scout'], ['LabBase', 'scout'], ['TECH OFFER', 'scout'], ['アカリク', 'scout'], ['リケイマッチ', 'scout'], ['paiza新卒', 'scout'], ['ViViViT', 'scout'], ['ReDesigner for Student', 'scout'], ['キャリアチケット', 'agent'], ['マイナビ新卒紹介', 'agent'], ['リクナビ就職エージェント', 'agent'], ['doda新卒エージェント', 'agent'], ['レバテックルーキー', 'agent'], ['ジョブスプリング', 'agent'], ['DiG UP CAREER', 'agent'], ['株式会社ローカルイノベーション', 'agent'], ['株式会社ジールコミュニケーションズ', 'agent'], ['株式会社キャリタス', 'agent'], ['株式会社ANCa', 'agent'], ['株式会社HRteam', 'agent'], ['株式会社ABABA', 'agent'], ['ヒトツメ株式会社', 'agent'], ['株式会社エージェントシェア', 'agent'], ['株式会社irodas', 'agent'], ['株式会社DYM', 'agent'], ['株式会社ナイモノ', 'agent'], ['株式会社maenomery', 'agent'], ['株式会社トランキロ', 'agent'], ['株式会社イノース', 'agent'], ['株式会社キャリアコンサルティング', 'agent'], ['株式会社ワークアズライフ', 'agent'], ['株式会社就活キャリア', 'agent'], ['株式会社ピーアール・デイリー', 'agent'], ['J-SHIP株式会社', 'agent'], ['宅建JOBエージェント', 'agent'], ['株式会社Hajimari', 'agent'], ['キャリアスタート株式会社', 'agent'], ['株式会社ユナイテッドウィル', 'agent'], ['キャリア美人コンサルティング株式会社', 'agent'], ['株式会社LMC', 'agent'], ['ブティックス株式会社(リアライブ)', 'agent'], ['ワークプラス株式会社', 'agent'], ['Dreamcloud Holdings株式会社', 'agent'], ['株式会社シーマインドキャリア', 'agent'], ['株式会社Birth', 'agent'], ['株式会社イングリウッド', 'agent'], ['ハイリンクキャリア株式会社', 'agent'], ['BASEME', 'scout']],
  '中途': [['ビズリーチ', 'scout'], ['リクルートダイレクトスカウト', 'scout'], ['dodaダイレクト', 'scout'], ['AMBI', 'scout'], ['ミドルの転職', 'scout'], ['ミイダス', 'scout'], ['OpenWorkリクルーティング', 'scout'], ['Eight Career Design', 'scout'], ['Green', 'scout'], ['Findy', 'scout'], ['LAPRAS', 'scout'], ['paiza転職', 'scout'], ['転職ドラフト', 'scout'], ['Forkwell', 'scout'], ['Offers', 'scout'], ['レバテックキャリア', 'scout'], ['リクルートエージェント', 'agent'], ['doda(エージェント)', 'agent'], ['マイナビエージェント', 'agent'], ['パソナキャリア', 'agent'], ['type転職エージェント', 'agent'], ['LHH転職エージェント', 'agent'], ['JACリクルートメント', 'agent'], ['dodaX', 'agent'], ['ロバート・ウォルターズ', 'agent'], ['マイケル・ペイジ', 'agent'], ['ランスタッド', 'agent'], ['第二新卒エージェントneo', 'agent'], ['ワークポート', 'agent'], ['スローガン株式会社', 'agent'], ['株式会社カカクコム', 'agent'], ['CPAキャリアサポート株式会社', 'agent'], ['株式会社フルリノ', 'agent'], ['エンエージェント', 'agent'], ['株式会社オズぺック', 'agent'], ['ツクリテ', 'agent'], ['株式会社OTOGI', 'agent'], ['株式会社コントラフト', 'agent'], ['株式会社テックビズ', 'agent'], ['株式会社みらいワークス', 'agent'], ['株式会社プロフェッショナルバンク', 'agent'], ['株式会社アドプション', 'agent'], ['株式会社ArchiBase', 'agent'], ['株式会社RSG', 'agent'], ['株式会社レガリス', 'agent'], ['株式会社昼JOB', 'agent'], ['株式会社freemova', 'agent'], ['株式会社NewSPO', 'agent'], ['株式会社Revengers', 'agent'], ['株式会社アーシャルデザイン', 'agent'], ['ヴォイスキャリアコンサルティング株式会社', 'agent'], ['株式会社ビーバーズ', 'agent'], ['株式会社RYOMA', 'agent'], ['キャリアバンク株式会社', 'agent'], ['X Mile株式会社', 'agent'], ['株式会社エス・エム・エス', 'agent'], ['株式会社よきあす', 'agent'], ['株式会社Liberty', 'agent'], ['ランコント株式会社', 'agent'], ['株式会社CockPit', 'agent'], ['一般社団法人全国建設人材協会', 'agent'], ['XTalent株式会社', 'agent'], ['株式会社ディプコア', 'agent'], ['株式会社アサイン', 'agent'], ['株式会社クライス＆カンパニー', 'agent'], ['株式会社スタートアップクラス', 'agent'], ['株式会社トラスポ', 'agent'], ['株式会社ミライフ', 'agent'], ['パーソルキャリア株式会社', 'agent']]
};
// 01_設定の右側(T列〜)にチャネル候補マスタを折り込む。バンド(A〜R)とは列を分けるので幅競合なし(横に広くなる)。
// buildSettings_ は A〜R(1-18)のみクリアするため、この右側領域は保持される(チェック/単価が残る)。
function buildChannelMaster_() {
  var sh = sheet_(SH.CONF);
  var lanes = ['共通', '新卒', '中途'], base = CHMASTER_BASE_COL, laneW = 5;
  var totalW = lanes.length * laneW;  // 各レーン=名称/種別/単価/有効(4)＋gap(1)
  var maxRows = Math.max.apply(null, lanes.map(function (l) { return CHMASTER[l].length; }));
  var N = maxRows + 4;
  // 既存の有効✓/単価を名称キーで退避(この右側領域から・継続運用=チェック/単価保持)
  var keep = {};
  if (sh.getLastRow() >= 4 && sh.getLastColumn() >= base + 3) {
    var rd = sh.getRange(4, base, Math.min(sh.getLastRow() - 3, N + 4), totalW).getValues();
    rd.forEach(function (r) { for (var c = 0; c + 3 < r.length; c += laneW) { var nm = String(r[c] || '').trim(); if (nm) keep[nm] = { cost: r[c + 2], on: r[c + 3] }; } });
  }
  ensureGrid_(sh, Math.max(N + 8, 255), base + totalW + 1);
  // 右側領域のみクリア(バンドは触らない)
  var region = sh.getRange(1, base, Math.max(N + 8, sh.getMaxRows()), totalW);
  try { region.breakApart(); } catch (e) {}
  region.clear(); region.clearDataValidations(); region.setWrap(false);
  bandTitle_(sh, 1, base, base + totalW - 2, '■ チャネル候補マスタ（区分レーン・有効✓で使う先を選択／単価は後日）');
  lanes.forEach(function (lane, li) {
    var c0 = base + li * laneW;
    sh.getRange(2, c0, 1, 4).merge().setValue(lane).setBackground(C.WHITE).setFontColor(C.BLACK).setFontWeight('bold').setHorizontalAlignment('center')
      .setBorder(null, null, true, null, null, null, '#3A3A3A', SpreadsheetApp.BorderStyle.SOLID);  // 下端=チャコール罫
    sh.getRange(3, c0, 1, 4).setValues([['名称', '種別', '単価', '有効']]).setBackground(HEAD_BG).setFontColor(C.INK).setFontWeight('bold').setFontSize(9).setHorizontalAlignment('center').setBorder(null, null, true, null, null, null, HEAD_RULE, SpreadsheetApp.BorderStyle.SOLID);
    var rows = CHMASTER[lane].map(function (x) { var k = keep[x[0]] || {}; var on = CHMASTER_DEFAULT_ON[x[0]] ? true : (k.on === true || k.on === 'TRUE'); return [x[0], x[1], (k.cost != null ? k.cost : ''), on]; });
    if (rows.length) sh.getRange(4, c0, rows.length, 4).setValues(rows).setFontSize(9).setVerticalAlignment('middle');
    var bgs = []; for (var z = 0; z < N; z++) { var ln = z % 2 ? C.ZEBRA : C.WHITE; bgs.push([ln, ln, ln, ln]); }
    sh.getRange(4, c0, N, 4).setBackgrounds(bgs);
    sh.getRange(4, c0 + 3, N, 1).insertCheckboxes();
    sh.getRange(4, c0 + 2, N, 1).setBackground(DESIGN_INPUT_BG);
    sh.getRange(2, c0, N + 2, 4).setBorder(true, true, true, true, true, true, C.BORDER, SpreadsheetApp.BorderStyle.SOLID);
    sh.setColumnWidth(c0, 200); sh.setColumnWidth(c0 + 1, 60); sh.setColumnWidth(c0 + 2, 70); sh.setColumnWidth(c0 + 3, 46);
    if (li < lanes.length - 1) sh.setColumnWidth(c0 + 4, 16);
  });
  sh.getRange(4 + N + 1, base, 1, totalW - 1).merge().setValue('世の中のスカウト媒体/エージェント＋自社の実パートナーを区分レーンで一覧。派遣・媒体(求人広告型)・北陸地域は除外。有効✓=使う先(単価は後日／チェック・単価は再生成しても保持)。※稼働(04/プルダウン)への反映は次ステップ。')
    .setFontColor(C.SUB).setFontSize(9).setWrap(true).setVerticalAlignment('top');
  return lanes.reduce(function (s, l) { return s + CHMASTER[l].length; }, 0);
}

/* ---------- 分析セクションのビルダー ---------- */

// 区切り帯(プレミアム■: 白地＋黒太字＋チャコール下罫)
function sectionBand_(sh, row, text) {
  var r = sh.getRange(row, 2, 1, 12);
  r.breakApart();
  r.merge().setValue('■ ' + text).setBackground(C.WHITE).setFontColor(C.BLACK)
    .setFontWeight('bold').setFontSize(11).setVerticalAlignment('middle')
    .setBorder(null, null, true, null, null, null, '#3A3A3A', SpreadsheetApp.BorderStyle.SOLID);
  sh.setRowHeight(row, 28);
}

// 小見出し＋表を置いて次の行を返す
function section_(sh, row, title, t, redCols) {
  sh.getRange(row, 2).setValue('▎' + title).setFontColor(C.BLACK).setFontWeight('bold').setFontSize(11);
  if (!t.rows.length) {
    var blank = [];
    for (var i = 0; i < t.header.length; i++) blank.push(i === 0 ? '(該当なし)' : '');
    t.rows = [blank];
  }
  return table_(sh, row + 1, 2, t.header, t.rows, redCols);
}

// ① 各ステージの 到達数 / 前段通過率 / 応募からの累積 / 離脱数
function buildStepYield_(stageNames, counts) {
  var header = ['ステージ', '到達数', '前段通過率', '応募累積', '離脱数'];
  var rows = stageNames.map(function (n, i) {
    var step = i === 0 ? '—' : pct_(counts[i], counts[i - 1]);
    var cum = pct_(counts[i], counts[0]);
    var drop = i === 0 ? 0 : (counts[i - 1] - counts[i]);
    return [n, counts[i], step, cum, drop];
  });
  return { header: header, rows: rows };
}

// ② 応募月別コホート: 各月の応募者が各ステージへ到達した数＋応募比CVR
function buildMonthly_(rows, H, stageNames, idxOf) {
  var groups = {};
  rows.forEach(function (r) {
    var ap = r[H['応募日']]; if (!(ap instanceof Date)) return;
    var key = ymKey_(ap);
    if (!groups[key]) groups[key] = stageNames.map(function () { return 0; });
    var cur = String(r[H['現ステージ']]);
    var si = (cur in idxOf) ? idxOf[cur] : -1;
    if (si >= 0) for (var k = 0; k <= si; k++) groups[key][k]++;
  });
  var months = Object.keys(groups).sort();
  var offIdx = idxOf['内定'], accIdx = idxOf['承諾'];
  var header = ['応募月'].concat(stageNames).concat(['応募→内定', '応募→承諾']);
  var data = months.map(function (m) {
    var c = groups[m];
    var rowv = [m].concat(c);
    rowv.push(pct_(offIdx != null ? c[offIdx] : 0, c[0]));
    rowv.push(pct_(accIdx != null ? c[accIdx] : 0, c[0]));
    return rowv;
  });
  return { header: header, rows: data };
}

// 任意のグループ(キー別/年齢層別)を 件数(各ステージ)＋全ステージ間の通過率(→stage) のカスケード表に。
// groups={key: counts[]} を受け取り {header,rows,redCols(通過率列=赤字)} を返す。
function cascadeTable_(keyHeader, groups, keys, stageNames) {
  var header = [keyHeader].concat(stageNames);
  for (var s = 1; s < stageNames.length; s++) header.push('→' + stageNames[s]);
  var data = keys.map(function (k) {
    var c = groups[k], row = [k].concat(c);
    for (var s2 = 1; s2 < stageNames.length; s2++) row.push(pct_(c[s2], c[s2 - 1]));
    return row;
  });
  var redCols = [];  // 通過率列(0始まりindex): 1+stageNames.length 以降
  for (var rc = 0; rc < stageNames.length - 1; rc++) redCols.push(1 + stageNames.length + rc);
  return { header: header, rows: data, redCols: redCols };
}
// キー別の各ステージ到達数を集計
function groupCounts_(rows, H, stageNames, idxOf, keyFn) {
  var groups = {};
  rows.forEach(function (r) {
    var key = keyFn(r);
    if (!groups[key]) groups[key] = stageNames.map(function () { return 0; });
    var cur = String(r[H['現ステージ']]);
    var si = (cur in idxOf) ? idxOf[cur] : -1;
    if (si >= 0) for (var k = 0; k <= si; k++) groups[key][k]++;
  });
  return groups;
}
// ③⑩⑫⑭ 任意キー別: 件数＋全ステージ間通過率(応募数の多い順)
function buildByKey_(rows, H, stageNames, idxOf, keyName) {
  var groups = groupCounts_(rows, H, stageNames, idxOf, function (r) { return String(r[H[keyName]] || '(未設定)'); });
  var keys = Object.keys(groups).sort(function (a, b) { return groups[b][0] - groups[a][0]; });
  return cascadeTable_(keyName, groups, keys, stageNames);
}

// ④ 職種別: ③に加えて 01_設定 の目標採用数に対する充足率(内定相当数/目標)
function buildByJob_(rows, H, stageNames, idxOf, seg, stageTypes) {
  var base = buildByKey_(rows, H, stageNames, idxOf, '職種');
  var offIdx = idxByType_(stageTypes || [], ['offer']);
  if (offIdx < 0) offIdx = idxByType_(stageTypes || [], ['accept', 'join']);
  if (offIdx < 0) offIdx = stageNames.length - 1;
  var targets = {};
  confRead_('JOB').forEach(function (r) { if (String(r[1]) === seg) targets[String(r[0])] = Number(r[2] || 0); });
  var header = base.header.concat(['目標', '充足率']);
  var data = base.rows.map(function (r) {
    var tgt = targets[r[0]] || 0, off = Number(r[1 + offIdx]) || 0;  // counts は index 1..stageNames.length
    return r.concat([tgt, pct_(off, tgt)]);
  });
  return { header: header, rows: data, redCols: base.redCols.concat([header.length - 1]) };
}

// ⑮ 年齢別: 生年月日から現在年齢(東京)を算出しバケット化 → カスケード
function ageBucket_(birth) {
  if (!(birth instanceof Date) || isNaN(birth.getTime())) return '不明';
  var now = nowTokyo_();
  var age = now.getUTCFullYear() - birth.getUTCFullYear();
  if ((now.getUTCMonth() * 100 + now.getUTCDate()) < (birth.getUTCMonth() * 100 + birth.getUTCDate())) age--;
  if (age < 0 || age > 120) return '不明';
  if (age <= 24) return '〜24';
  if (age <= 29) return '25-29';
  if (age <= 34) return '30-34';
  if (age <= 39) return '35-39';
  return '40〜';
}
function buildByAge_(rows, H, stageNames, idxOf) {
  var ORDER = ['〜24', '25-29', '30-34', '35-39', '40〜', '不明'];
  var groups = groupCounts_(rows, H, stageNames, idxOf, function (r) { return ageBucket_(r[H['生年月日']]); });
  var keys = ORDER.filter(function (k) { return groups[k]; });
  return cascadeTable_('年齢層', groups, keys, stageNames);
}

// ⑤ 見送り/辞退の理由内訳
function buildReasons_(rows, H) {
  var g = {}, total = 0;
  rows.forEach(function (r) {
    var st = String(r[H['ステータス']]);
    if (st !== '見送り' && st !== '辞退') return;
    var reason = String(r[H['見送り辞退理由']] || '(理由未記入)');
    g[reason] = (g[reason] || 0) + 1; total++;
  });
  var keys = Object.keys(g).sort(function (a, b) { return g[b] - g[a]; });
  var header = ['見送り/辞退理由', '件数', '構成比'];
  var data = keys.map(function (k) { return [k, g[k], pct_(g[k], total)]; });
  return { header: header, rows: data, total: total };
}

// ⑥⑦ 任意キー × 月 のクロス集計(応募月別の応募数推移)
function buildMonthlyCross_(rows, H, keyName) {
  var months = {}, keys = {};
  rows.forEach(function (r) {
    var ap = r[H['応募日']]; if (!(ap instanceof Date)) return;
    var mk = ymKey_(ap); months[mk] = true;
    var k = String(r[H[keyName]] || '(未設定)');
    if (!keys[k]) keys[k] = {};
    keys[k][mk] = (keys[k][mk] || 0) + 1;
  });
  var ms = Object.keys(months).sort();
  if (!ms.length) return { header: [keyName, '(データなし)'], rows: [['—', '']] };
  var header = [keyName].concat(ms).concat(['合計']);
  var keyList = Object.keys(keys).sort(function (a, b) {
    var ta = 0, tb = 0; ms.forEach(function (m) { ta += keys[a][m] || 0; tb += keys[b][m] || 0; }); return tb - ta;
  });
  var data = keyList.map(function (k) {
    var row = [k], tot = 0;
    ms.forEach(function (m) { var v = keys[k][m] || 0; row.push(v); tot += v; });
    row.push(tot); return row;
  });
  return { header: header, rows: data };
}

// ⑧⑨ 月次/週次ファネル(コホート＝応募期間別の各ステージ到達数＋遷移率)。画像形式。
function mondayMs_(date) {
  var d = tokyoDayMs_(date); var dow = new Date(d).getUTCDay(); var off = (dow === 0 ? 6 : dow - 1);
  return d - off * 86400000;
}
function buildPeriodFunnel_(M, period) {
  var rows = M.rows, H = M.H, names = M.stageNames, idxOf = M.idxOf;
  if (!names.length) return { header: ['(ステージ未設定)'], rows: [['—']] };
  var now = nowTokyo_(), keys = [], labels = {};
  if (period === 'month') {
    for (var i = 11; i >= 0; i--) {
      var d = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() - i, 1));
      var k = d.getUTCFullYear() + '-' + ('0' + (d.getUTCMonth() + 1)).slice(-2);
      keys.push(k); labels[k] = k;
    }
  } else {
    var monday = mondayMs_(new Date());
    for (var w = 0; w < 12; w++) { var ms = monday - w * 7 * 86400000; keys.push('W' + ms); labels['W' + ms] = Utilities.formatDate(new Date(ms), 'Asia/Tokyo', 'MM/dd'); }
  }
  var buckets = {}; keys.forEach(function (k) { buckets[k] = names.map(function () { return 0; }); });
  rows.forEach(function (r) {
    var ap = r[H['応募日']]; if (!(ap instanceof Date)) return;
    var key = (period === 'month') ? (ap.getUTCFullYear() + '-' + ('0' + (ap.getUTCMonth() + 1)).slice(-2)) : ('W' + mondayMs_(ap));
    if (!buckets[key]) return;
    var cur = String(r[H['現ステージ']]); var si = (cur in idxOf) ? idxOf[cur] : -1;
    if (si >= 0) for (var k2 = 0; k2 <= si; k2++) buckets[key][k2]++;
  });
  var header = [(period === 'month' ? '月' : '週(月曜)')].concat(names);
  for (var s = 1; s < names.length; s++) header.push('→' + names[s]);
  var data = keys.map(function (k) {
    var c = buckets[k], row = [labels[k]].concat(c);
    for (var s2 = 1; s2 < names.length; s2++) row.push(pct_(c[s2], c[s2 - 1]));
    return row;
  });
  return { header: header, rows: data };
}

/* ============================== 60_レポート出力 ============================== */

function renderReports_(asOf) {
  var sh = sheet_(SH.RP);
  clearSheet_(sh);
  ensureGrid_(sh, 260, 24);
  sh.setColumnWidth(1, 30);
  sh.setColumnWidth(2, 150);
  for (var c = 3; c <= 13; c++) sh.setColumnWidth(c, 80);

  var n = asOf || reportAsOf_();
  var docUrl = String(PropertiesService.getDocumentProperties().getProperty('monthlyDocUrl') || '').trim();
  bandTitle_(sh, 1, 2, 13, '■ ' + companyName_() + ' 採用レポート（全区分）    （基準日: ' + fmtD_(n) + ' / 生成: ' +
    Utilities.formatDate(new Date(), ss_().getSpreadsheetTimeZone(), 'yyyy-MM-dd HH:mm') + '）');
  if (docUrl) sh.getRange(2, 2).setValue('月次Doc: ' + docUrl).setFontColor('#1155CC').setFontSize(9);

  var row = 3;
  row = renderMonthlyReportAll_(sh, row, n) + 1;
  row = renderWeeklyReportAll_(sh, row, n) + 1;
  row = renderDailyReportAll_(sh, row, n) + 2;

  // チャート(末尾・全幅) WP5 — 設定: レポート項目 月次:チャート(m_chart) / 60タブ がONのときのみ
  if (reportItemsOn_('月次', 'tab').indexOf('m_chart') >= 0) {
    sectionHead_(sh, row, 2, 12, 'チャート（全区分）'); row += 2;
    var Ms = enabledSegments_().map(function (s) { return computeSegment_(s); });
    var cd = 21;
    var barData = [['区分', '確定', '目標']].concat(Ms.map(function (M) { var nf = normalizedFunnel_(M); var fg = finalGoal_(M); return [M.seg, nf.fin, fg ? fg.tgt : 0]; }));
    sh.getRange(row, cd, barData.length, 3).setValues(barData);
    addColumnChart_(sh, sh.getRange(row, cd, barData.length, 3), row, 2, '区分別 確定 vs 目標', 420, 240);
    var g = crossAgg_('チャネル'); var keys = Object.keys(g).sort(function (a, b) { return g[b].app - g[a].app; });
    var pieData = [['チャネル', '応募']].concat(keys.map(function (k) { return [k, g[k].app]; }));
    sh.getRange(row, cd + 4, pieData.length, 2).setValues(pieData);
    addPieChart_(sh, sh.getRange(row, cd + 4, pieData.length, 2), row, 9, '応募 経路別構成', 420, 240);
  }
  return row;
}

// 区分Mの 応募/内定/承諾/入社 を「発生月(YMキー=year*100+month0)」でカウント。前月比サマリ用。
function milestoneMonth_(M, ym) {
  var H = M.H, o = { app: 0, off: 0, acc: 0, join: 0 }, map = { app: '応募日', off: '内定日', acc: '承諾日', join: '入社日' };
  (M.rows || []).forEach(function (r) {
    for (var k in map) { var d = (H[map[k]] != null) ? r[H[map[k]]] : null; if (d instanceof Date && tokyoYM_(d) === ym) o[k]++; }
  });
  return o;
}
function prevYM_(ym) { var y = Math.floor(ym / 100), m = ym % 100, pm = m - 1, py = y; if (pm < 0) { pm = 11; py--; } return py * 100 + pm; }

function renderMonthlyReportAll_(sh, row, n) {
  var keys = reportItemsOn_('月次', 'tab');
  if (!keys.length) return row;  // 月次タブ出力が全OFF → セクションごと出さない
  var label = n.getUTCFullYear() + '年' + (n.getUTCMonth() + 1) + '月';
  sectionHead_(sh, row, 2, 12, '月次レポート（経営向け）  ' + label); row += 2;

  var Ms = enabledSegments_().map(function (s) { return computeSegment_(s); });
  var segRows = Ms.map(function (M) {
    if (!M.stageNames.length) return [M.seg, 0, 0, 0, 0, '—', '—', 0];
    var nf = normalizedFunnel_(M); var fg = finalGoal_(M);
    var pc = pace_(M, n); var pg = pc.goals.length ? pc.goals[pc.goals.length - 1] : null;
    return [M.seg, nf.app, nf.offer, nf.fin, (fg ? fg.tgt : 0), (fg ? pct_(fg.act, fg.tgt) : '—'),
            (pg ? paceText_(pg) : '—'), (pg ? pg.forecast : 0)];
  });
  // 出す表をkeyで制御(設定: レポート項目 月次 / 60タブ)
  var sect = {
    m_summary: function () {
      row = subhead_(sh, row, '▎全区分サマリ（応募 / 内定相当 / 確定 / 確定目標 / 達成率 / ペース / 着地予想）');
      row = table_(sh, row, 2, ['区分', '応募', '内定相当', '確定', '確定目標', '達成率', 'ペース', '着地予想'], segRows, [5]);
    },
    m_funnel: function () {
      Ms.forEach(function (M) {
        if (!M.stageNames.length || M.counts[0] === 0) return;
        var sy = buildStepYield_(M.stageNames, M.counts);
        row = subhead_(sh, row, '▎' + M.seg + ' ファネル歩留まり');
        row = table_(sh, row, 2, sy.header, sy.rows, [2, 3, 4]);
      });
    },
    m_channel: function () {
      var ch = buildCrossChannel_();
      row = subhead_(sh, row, '▎チャネル別 CVR / CPA（全区分横断）');
      row = table_(sh, row, 2, ch.header, ch.rows, [3, 5]);
    },
    m_mom: function () {
      var cur = tokyoYM_(n), prev = prevYM_(cur);
      var c = { app: 0, off: 0, acc: 0, join: 0 }, p = { app: 0, off: 0, acc: 0, join: 0 };
      Ms.forEach(function (M) { var a = milestoneMonth_(M, cur), b = milestoneMonth_(M, prev); ['app', 'off', 'acc', 'join'].forEach(function (k) { c[k] += a[k]; p[k] += b[k]; }); });
      function dlt(a, b) { var d = a - b; return (d > 0 ? '+' : '') + d; }
      var mrows = [
        ['応募', c.app, p.app, dlt(c.app, p.app)],
        ['内定', c.off, p.off, dlt(c.off, p.off)],
        ['承諾', c.acc, p.acc, dlt(c.acc, p.acc)],
        ['入社', c.join, p.join, dlt(c.join, p.join)],
        ['内定率', pct_(c.off, c.app), pct_(p.off, p.app), '—']
      ];
      row = subhead_(sh, row, '▎月次サマリ 前月比（全区分・応募/内定/承諾/入社の発生月ベース）');
      row = table_(sh, row, 2, ['指標', '当月', '前月', '前月比'], mrows, [3]);
    },
    m_channel_need: function () {
      var g = crossAgg_('チャネル'), keys = Object.keys(g).sort(function (a, b) { return g[b].app - g[a].app; });
      var crows = keys.map(function (k) {
        var x = g[k];
        var nOff = x.off > 0 ? String(Math.round(x.app / x.off * 10) / 10) : '—';
        var nFin = x.fin > 0 ? String(Math.round(x.app / x.fin * 10) / 10) : '—';
        return [k, x.app, x.off, x.fin, pct_(x.fin, x.app), nOff, nFin];
      });
      row = subhead_(sh, row, '▎経路別 必要エントリー数（内定1名/確定1名あたり ＝ 1/CVR）');
      row = table_(sh, row, 2, ['経路', '応募', '内定相当', '確定', '応募→確定', '内定1名/必要', '確定1名/必要'], crows.length ? crows : [['—', 0, 0, 0, '—', '—', '—']], [4]);
    },
    m_job_full: function () {
      Ms.forEach(function (M) {
        if (!M.stageNames.length || !M.counts[0]) return;
        var t = buildByKey_(M.rows, M.H, M.stageNames, M.idxOf, '職種');
        row = subhead_(sh, row, '▎' + M.seg + ' 職種別 実績（全選考段）');
        row = table_(sh, row, 2, t.header, t.rows.length ? t.rows : [['(該当なし)']], []);
      });
    },
    m_emp_rc: function () {
      var er = Ms.map(function (M) { var nf = normalizedFunnel_(M); return [M.seg, nf.app, nf.interview, nf.offer, nf.fin, pct_(nf.offer, nf.app)]; });
      row = subhead_(sh, row, '▎雇用区分別 実績');
      row = table_(sh, row, 2, ['区分', '応募', '面接相当', '内定相当', '確定', '内定率'], er, [5]);
      var rg = crossAgg_('採用担当RC'), rks = Object.keys(rg).filter(function (k) { return k && k !== 'undefined' && String(k).trim() !== '' && k !== '(未設定)'; }).sort(function (a, b) { return rg[b].app - rg[a].app; });
      var rr = rks.map(function (k) { var x = rg[k]; return [k, x.app, x.off, x.fin, pct_(x.off, x.app)]; });
      row = subhead_(sh, row, '▎採用担当者別 実績');
      row = table_(sh, row, 2, ['担当者', '応募', '内定相当', '確定', '内定率'], rr.length ? rr : [['(担当未設定)', 0, 0, 0, '—']], [4]);
    },
    m_insight: function () {
      var ins = insightsAll_(segRows);
      row = subhead_(sh, row, '▎所感');
      row = renderBullets_(sh, row, '◎ Good', ins.good);
      row = renderBullets_(sh, row, '△ 課題', ins.issue);
      row = renderBullets_(sh, row, '⚠ Risk', ins.risk);
    }
  };
  keys.forEach(function (k) { if (sect[k]) sect[k](); });
  // 詳細分析(表示パネルの「レポート出力」ON)を区分ごとに出力（表示パネルと同じ分析をレポートにも）
  var rpanels = reportPanels_();
  if (rpanels.length) {
    Ms.forEach(function (M) {
      if (!M.stageNames.length || !M.counts[0]) return;
      row = subhead_(sh, row, '▎' + M.seg + ' 詳細分析');
      rpanels.forEach(function (pk) { try { row = renderPanel_(sh, row, pk, M, M.seg); } catch (e) {} });
    });
  }
  return row;
}

function renderWeeklyReportAll_(sh, row, asOf) {
  var keys = reportItemsOn_('週次', 'tab');
  if (!keys.length) return row;  // 週次タブ出力が全OFF → セクションごと出さない
  var am = allMaster_();
  var iv = sheet_(SH.IV); var ivData = iv.getDataRange().getValues(); var ivH = headerIndex_(ivData.shift());
  var wd = weeklyData_(am.rows, am.H, ivData, ivH, asOf);
  sectionHead_(sh, row, 2, 12, '週次レポート（担当者向け・全区分）  ' + fmtD_(asOf || nowTokyo_()) + ' 基準'); row += 2;

  var sect = {
    w_move: function () {
      row = subhead_(sh, row, '▎今週の動き（直近7日）');
      row = table_(sh, row, 2, ['新規応募', '内定', '承諾', '入社'], [[wd.w.app, wd.w.off, wd.w.acc, wd.w.join]], []);
    },
    w_upcoming: function () {
      row = subhead_(sh, row, '▎来週の面接予定（7日内）');
      row = table_(sh, row, 2, ['日時', '候補者', 'ステージ', '面接官'], wd.upcoming.length ? wd.upcoming : [['—', '', '', '']], []);
    },
    w_todo: function () {
      row = subhead_(sh, row, '▎要対応（NA期限 7日内・超過）');
      row = table_(sh, row, 2, ['期限', '候補者', 'ネクストアクション', '担当', '状態'], wd.todo.length ? wd.todo : [['—', '', '', '', '']], [4]);
    },
    w_funnel: function () {
      var fRows = enabledSegments_().map(function (s) {
        var M = computeSegment_(s); var nf = normalizedFunnel_(M);
        return [s, nf.app, nf.doc, nf.interview, nf.offer, nf.fin];
      });
      row = subhead_(sh, row, '▎区分別ファネル現況（5段正規化）');
      row = table_(sh, row, 2, ['区分', '応募', '書類相当', '面接相当', '内定相当', '確定'], fRows, []);
    },
    w_pace: function () {
      var pRows = enabledSegments_().map(function (s) {
        var M = computeSegment_(s); var pc = pace_(M, asOf);
        var pg = pc.goals.length ? pc.goals[pc.goals.length - 1] : null;
        return [s, (pg ? pg.name : '—'), (pg ? pg.tgt : 0), (pg ? pg.act : 0),
                (pg ? pct_(pg.act, pg.tgt) : '—'), (pg ? paceText_(pg) : '—'), (pg ? pg.forecast : 0)];
      });
      row = subhead_(sh, row, '▎今月目標への進捗（達成率・ペース・着地予想）');
      row = table_(sh, row, 2, ['区分', '指標', '目標', '実績', '達成率', 'ペース', '着地予想'], pRows, [4]);
    }
  };
  keys.forEach(function (k) { if (sect[k]) sect[k](); });
  return row;
}

function renderDailyReportAll_(sh, row, asOf) {
  var am = allMaster_();
  var iv = sheet_(SH.IV); var ivData = iv.getDataRange().getValues(); var ivH = headerIndex_(ivData.shift());
  var anchor = tokyoDayMs_(asOf || nowTokyo_());
  sectionHead_(sh, row, 2, 12, '日次（要対応・全区分）  ' + fmtD_(asOf || nowTokyo_())); row += 2;

  var today = [];
  ivData.forEach(function (r) {
    var dt = r[ivH['予定日時']]; if (!(dt instanceof Date)) return;
    if (String(r[ivH['ステータス']]) === 'キャンセル') return;
    if (tokyoDayMs_(dt) === anchor) today.push([fmtDT_(dt), String(r[ivH['候補者名']]), String(r[ivH['区分']]), String(r[ivH['ステージ']]), String(r[ivH['面接官']])]);
  });
  today.sort(function (a, b) { return a[0] < b[0] ? -1 : 1; });
  row = subhead_(sh, row, '▎本日の面接');
  row = table_(sh, row, 2, ['日時', '候補者', '区分', 'ステージ', '面接官'], today.length ? today : [['—', '', '', '', '']], []);

  var todo = [];
  am.rows.forEach(function (r) {
    if (String(r[am.H['ステータス']]) !== '進行中') return;
    var na = r[am.H['NA期限']]; if (!(na instanceof Date)) return;
    if ((tokyoDayMs_(na) - anchor) / 86400000 <= 0) todo.push([fmtD_(na), String(r[am.H['氏名']]), String(r[am.H['区分']]), String(r[am.H['ネクストアクション']]), String(r[am.H['採用担当RC']])]);
  });
  todo.sort(function (a, b) { return a[0] < b[0] ? -1 : 1; });
  row = subhead_(sh, row, '▎要対応（本日・超過）');
  row = table_(sh, row, 2, ['期限', '候補者', '区分', 'ネクストアクション', '担当'], todo.length ? todo : [['—', '', '', '', '']], []);
  return row;
}

// 全区分のマスタ行
function allMaster_() {
  var m = sheet_(SH.MASTER); var data = m.getDataRange().getValues(); var H = headerIndex_(data.shift());
  return { rows: data.filter(function (r) { return String(r[H['candidate_id']]).trim() !== ''; }), H: H };
}

// 全区分横断のチャネル別CVR/CPA(レポート用)
function buildCrossChannel_() {
  var g = crossAgg_('チャネル');
  var cost = {};
  confRead_('CHAN')
    .forEach(function (r) { cost[String(r[0])] = r[2]; });
  var keys = Object.keys(g).sort(function (a, b) { return g[b].app - g[a].app; });
  var rows = keys.map(function (k) {
    var x = g[k], c = cost[k];
    var cpa = (typeof c === 'number' && c > 0 && x.fin > 0) ? String(Math.round(c / x.fin)) : (typeof c === 'number' ? '—' : (c || '—'));
    return [k, x.app, x.fin, pct_(x.fin, x.app), (typeof c === 'number' ? String(c) : (c || '')), cpa];
  });
  return { header: ['チャネル', '応募', '確定', '応募→確定', 'コスト/月', 'CPA(円/確定)'], rows: rows.length ? rows : [['—', 0, 0, '—', '', '—']] };
}

// 全体所感(区分別サマリから)
function insightsAll_(segRows) {
  var good = [], issue = [], risk = [];
  segRows.forEach(function (r) {
    var seg = r[0], app = r[1], fin = r[3], tgt = r[4];
    if (tgt > 0) {
      var p = Math.round(fin / tgt * 100);
      if (p >= 80) good.push(seg + '：確定が目標の' + p + '%で順調');
      else if (p < 40) risk.push(seg + '：確定' + p + '%。母集団と歩留まりの両面で対策を');
    }
    if (app === 0 && tgt > 0) issue.push(seg + '：当区分の応募が0件。母集団形成が必要');
  });
  if (!good.length && !issue.length && !risk.length) good.push('特記事項なし');
  return { good: good, issue: issue, risk: risk };
}

/* ---------- WP5: 月次レポートを Google Doc 出力 ---------- */

function generateMonthlyDoc() {
  var props = PropertiesService.getDocumentProperties();
  var doc = null, ex = String(props.getProperty('monthlyDocId') || '').trim();
  if (ex) { try { doc = DocumentApp.openById(ex); } catch (e) { doc = null; } }
  if (!doc) { doc = DocumentApp.create(companyName_() + ' 採用月次レポート'); props.setProperty('monthlyDocId', doc.getId()); }
  var body = doc.getBody(); body.clear();
  var n = reportAsOf_(), label = n.getUTCFullYear() + '年' + (n.getUTCMonth() + 1) + '月';

  docHeading_(body, companyName_() + ' 採用 月次レポート  ' + label, DocumentApp.ParagraphHeading.TITLE, '#AF322C');
  body.appendParagraph('生成: ' + Utilities.formatDate(new Date(), ss_().getSpreadsheetTimeZone(), 'yyyy-MM-dd HH:mm'))
    .editAsText().setForegroundColor('#6B6B6B');

  var Ms = enabledSegments_().map(function (s) { return computeSegment_(s); });
  var segNum = Ms.map(function (M) {
    var nf = normalizedFunnel_(M); var fg = finalGoal_(M);
    var pc = pace_(M, n); var pg = pc.goals.length ? pc.goals[pc.goals.length - 1] : null;
    return [M.seg, nf.app, nf.offer, nf.fin, (fg ? fg.tgt : 0), (fg ? pct_(fg.act, fg.tgt) : '—'),
            (pg ? paceText_(pg) : '—'), (pg ? pg.forecast : 0)];
  });
  // 出すセクションを設定(レポート項目 月次 / Doc)で制御。m_chartはDoc非対応→無視。
  var sect = {
    m_summary: function () {
      docHeading_(body, '■ 全区分サマリ', DocumentApp.ParagraphHeading.HEADING1, '#000000');
      appendDocTable_(body, ['区分', '応募', '内定相当', '確定', '確定目標', '達成率', 'ペース', '着地予想'], segNum.map(function (r) { return r.map(String); }));
    },
    m_funnel: function () {
      Ms.forEach(function (M) {
        if (!M.counts[0]) return;
        docHeading_(body, '■ ' + M.seg + ' ファネル歩留まり', DocumentApp.ParagraphHeading.HEADING2, '#000000');
        var sy = buildStepYield_(M.stageNames, M.counts);
        appendDocTable_(body, sy.header, sy.rows.map(function (r) { return r.map(String); }));
      });
    },
    m_channel: function () {
      docHeading_(body, '■ チャネル別 CVR / CPA（全区分横断）', DocumentApp.ParagraphHeading.HEADING1, '#000000');
      var ch = buildCrossChannel_();
      appendDocTable_(body, ch.header, ch.rows.map(function (r) { return r.map(String); }));
    },
    m_mom: function () {
      docHeading_(body, '■ 月次サマリ 前月比（全区分）', DocumentApp.ParagraphHeading.HEADING1, '#000000');
      var cur = tokyoYM_(n), prev = prevYM_(cur);
      var c = { app: 0, off: 0, acc: 0, join: 0 }, p = { app: 0, off: 0, acc: 0, join: 0 };
      Ms.forEach(function (M) { var a = milestoneMonth_(M, cur), b = milestoneMonth_(M, prev); ['app', 'off', 'acc', 'join'].forEach(function (k) { c[k] += a[k]; p[k] += b[k]; }); });
      function dlt(a, b) { var d = a - b; return (d > 0 ? '+' : '') + d; }
      appendDocTable_(body, ['指標', '当月', '前月', '前月比'], [
        ['応募', String(c.app), String(p.app), dlt(c.app, p.app)],
        ['内定', String(c.off), String(p.off), dlt(c.off, p.off)],
        ['承諾', String(c.acc), String(p.acc), dlt(c.acc, p.acc)],
        ['入社', String(c.join), String(p.join), dlt(c.join, p.join)],
        ['内定率', pct_(c.off, c.app), pct_(p.off, p.app), '—']
      ]);
    },
    m_channel_need: function () {
      docHeading_(body, '■ 経路別 必要エントリー数（内定1名/確定1名あたり＝1/CVR）', DocumentApp.ParagraphHeading.HEADING1, '#000000');
      var g = crossAgg_('チャネル'), keys = Object.keys(g).sort(function (a, b) { return g[b].app - g[a].app; });
      appendDocTable_(body, ['経路', '応募', '内定相当', '確定', '応募→確定', '内定1名/必要', '確定1名/必要'], keys.map(function (k) {
        var x = g[k], nOff = x.off > 0 ? String(Math.round(x.app / x.off * 10) / 10) : '—', nFin = x.fin > 0 ? String(Math.round(x.app / x.fin * 10) / 10) : '—';
        return [k, String(x.app), String(x.off), String(x.fin), pct_(x.fin, x.app), nOff, nFin];
      }));
    },
    m_job_full: function () {
      Ms.forEach(function (M) {
        if (!M.counts[0]) return;
        docHeading_(body, '■ ' + M.seg + ' 職種別 実績（全選考段）', DocumentApp.ParagraphHeading.HEADING2, '#000000');
        var t = buildByKey_(M.rows, M.H, M.stageNames, M.idxOf, '職種');
        appendDocTable_(body, t.header, t.rows.map(function (r) { return r.map(String); }));
      });
    },
    m_emp_rc: function () {
      docHeading_(body, '■ 雇用区分別・担当者別', DocumentApp.ParagraphHeading.HEADING1, '#000000');
      appendDocTable_(body, ['区分', '応募', '面接相当', '内定相当', '確定', '内定率'], Ms.map(function (M) { var nf = normalizedFunnel_(M); return [M.seg, String(nf.app), String(nf.interview), String(nf.offer), String(nf.fin), pct_(nf.offer, nf.app)]; }));
      var rg = crossAgg_('採用担当RC'), rks = Object.keys(rg).filter(function (k) { return k && k !== 'undefined' && String(k).trim() !== '' && k !== '(未設定)'; }).sort(function (a, b) { return rg[b].app - rg[a].app; });
      if (rks.length) appendDocTable_(body, ['担当者', '応募', '内定相当', '確定', '内定率'], rks.map(function (k) { var x = rg[k]; return [k, String(x.app), String(x.off), String(x.fin), pct_(x.off, x.app)]; }));
    },
    m_insight: function () {
      docHeading_(body, '■ 所感', DocumentApp.ParagraphHeading.HEADING1, '#000000');
      var ins = insightsAll_(segNum);
      [['◎ Good', ins.good], ['△ 課題', ins.issue], ['⚠ Risk', ins.risk]].forEach(function (grp) {
        grp[1].forEach(function (t) { body.appendListItem(grp[0] + '  ' + t).setGlyphType(DocumentApp.GlyphType.BULLET); });
      });
    }
  };
  reportItemsOn_('月次', 'doc').forEach(function (k) { if (sect[k]) sect[k](); });

  doc.saveAndClose();
  var url = doc.getUrl();
  props.setProperty('monthlyDocUrl', url);
  try { sheet_(SH.RP).getRange(2, 2).setValue('月次Doc: ' + url).setFontColor('#1155CC').setFontSize(9); } catch (e) {}
  toast_('月次レポートをGoogle Docに出力しました');
  return url;
}

/* ---------- 半期振り返り資料を Google スライド出力 ---------- */
// スライドにタイトル＋表を1枚追加(ブランド体裁)
function slideTitle_(slide, title, sub) {
  var t = slide.insertTextBox(title, 24, 24, 672, 50);
  t.getText().getTextStyle().setFontSize(22).setBold(true).setForegroundColor('#AF322C');
  if (sub) { var s = slide.insertTextBox(sub, 24, 74, 672, 24); s.getText().getTextStyle().setFontSize(11).setForegroundColor('#6B6B6B'); }
}
function slideTable_(slide, header, rows, top) {
  var data = [header].concat(rows.map(function (r) { return r.map(String); }));
  var nR = data.length, nC = header.length;
  var tbl = slide.insertTable(nR, nC, 24, top || 110, 672, Math.min(330, 22 * nR));
  for (var r = 0; r < nR; r++) for (var c = 0; c < nC; c++) {
    var cell = tbl.getCell(r, c); cell.getText().setText(data[r][c]);
    var ts = cell.getText().getTextStyle(); ts.setFontSize(9);
    if (r === 0) { ts.setBold(true).setForegroundColor('#FFFFFF'); cell.getFill().setSolidFill('#000000'); }
    else if (r % 2 === 0) cell.getFill().setSolidFill('#F7F5F4');
  }
  return tbl;
}
function generateHalfYearSlides() {
  var props = PropertiesService.getDocumentProperties(), cn = companyName_();
  var n = reportAsOf_(), anchor = tokyoDayMs_(n);
  var label = n.getUTCFullYear() + '年' + (n.getUTCMonth() + 1) + '月時点';
  // 直近6ヶ月の窓集計(応募/内定/承諾/入社)
  var am = allMaster_(), H = am.H, win = { app: 0, off: 0, acc: 0, joi: 0 };
  function inHalf(d) { if (!(d instanceof Date)) return false; var k = (anchor - tokyoDayMs_(d)) / 86400000; return k >= 0 && k <= 183; }
  am.rows.forEach(function (r) {
    if (inHalf(r[H['応募日']])) win.app++; if (inHalf(r[H['内定日']])) win.off++;
    if (inHalf(r[H['承諾日']])) win.acc++; if (inHalf(r[H['入社日']])) win.joi++;
  });
  var Ms = enabledSegments_().map(function (s) { return computeSegment_(s); });
  var segRows = Ms.map(function (M) {
    var nf = normalizedFunnel_(M), fg = finalGoal_(M);
    return [M.seg, nf.app, nf.offer, nf.fin, (fg ? fg.tgt : 0), (fg ? pct_(fg.act, fg.tgt) : '—')];
  });
  var pres = null, ex = String(props.getProperty('halfYearSlideId') || '').trim();
  if (ex) { try { pres = SlidesApp.openById(ex); } catch (e) { pres = null; } }
  if (!pres) { pres = SlidesApp.create(cn + ' 採用 半期振り返り'); props.setProperty('halfYearSlideId', pres.getId()); }
  pres.getSlides().forEach(function (s, i) { if (i > 0) s.remove(); else s.getPageElements().forEach(function (e) { e.remove(); }); });
  // 1. 表紙
  var s1 = pres.getSlides()[0];
  slideTitle_(s1, cn + ' 採用 半期振り返り', label + ' / 生成 ' + Utilities.formatDate(new Date(), ss_().getSpreadsheetTimeZone(), 'yyyy-MM-dd'));
  s1.insertTextBox('直近6ヶ月: 応募 ' + win.app + ' / 内定 ' + win.off + ' / 承諾 ' + win.acc + ' / 入社 ' + win.joi, 24, 150, 672, 40)
    .getText().getTextStyle().setFontSize(16).setBold(true);
  // 2. 区分別サマリ
  var s2 = pres.appendSlide(SlidesApp.PredefinedLayout.BLANK);
  slideTitle_(s2, '区分別サマリ（応募→確定・目標達成）');
  slideTable_(s2, ['区分', '応募', '内定相当', '確定', '確定目標', '達成率'], segRows.length ? segRows : [['—', 0, 0, 0, 0, '—']]);
  // 3. チャネル別
  var s3 = pres.appendSlide(SlidesApp.PredefinedLayout.BLANK);
  slideTitle_(s3, 'チャネル別 CVR / CPA（全区分横断）');
  var ch = buildCrossChannel_();
  slideTable_(s3, ch.header, ch.rows.slice(0, 12));
  // 4. 所感
  var s4 = pres.appendSlide(SlidesApp.PredefinedLayout.BLANK);
  slideTitle_(s4, '所感（Good / 課題 / Risk）');
  var ins = insightsAll_(segRows.map(function (r) { return [r[0], r[1], 0, r[3], r[4]]; }));
  var lines = [];
  ins.good.forEach(function (t) { lines.push('◎ ' + t); });
  ins.issue.forEach(function (t) { lines.push('△ ' + t); });
  ins.risk.forEach(function (t) { lines.push('⚠ ' + t); });
  s4.insertTextBox(lines.join('\n') || '特記事項なし', 24, 110, 672, 300).getText().getTextStyle().setFontSize(12);
  pres.saveAndClose();
  var url = pres.getUrl(); props.setProperty('halfYearSlideUrl', url);
  toast_('半期振り返りスライドを出力しました（URLは実行ログ）');
  Logger.log('半期スライド: ' + url);
  return url;
}

/* ---------- 月次レポートをメール送信(担当者宛) ---------- */
function sendMonthlyMail() { sendMonthlyMail_(reportAsOf_(), false); }
// silent=true: 自動トリガー用(toastせずログのみ)。受信者0/項目0/送信失敗時は false。
function sendMonthlyMail_(asOf, silent) {
  var to = mailRecipients_();
  if (!to.length) { if (!silent) toast_('月次メールの受信者が未設定（01_設定 メンバー「月次メール」をON）'); return false; }
  var keys = reportItemsOn_('月次', 'mail');
  if (!keys.length) { if (!silent) toast_('月次メールの配信項目が全OFF（01_設定 レポート項目 / メール列）'); return false; }
  var n = asOf || reportAsOf_(), label = n.getUTCFullYear() + '年' + (n.getUTCMonth() + 1) + '月', cn = companyName_();
  var Ms = enabledSegments_().map(function (s) { return computeSegment_(s); });
  var segNum = Ms.map(function (M) {
    var nf = normalizedFunnel_(M); var fg = finalGoal_(M);
    var pc = pace_(M, n); var pg = pc.goals.length ? pc.goals[pc.goals.length - 1] : null;
    return [M.seg, nf.app, nf.offer, nf.fin, (fg ? fg.tgt : 0), (fg ? pct_(fg.act, fg.tgt) : '—'),
            (pg ? paceText_(pg) : '—'), (pg ? pg.forecast : 0)];
  });
  var docUrl = String(PropertiesService.getDocumentProperties().getProperty('monthlyDocUrl') || '').trim();
  var h = ['<div style="font-family:sans-serif;color:#1A1A1A;max-width:720px">',
    '<h1 style="color:#AF322C;border-bottom:3px solid #AF322C;padding-bottom:6px">' + esc_(cn) + ' 採用 月次レポート ' + label + '</h1>'];
  if (docUrl) h.push('<p><a href="' + docUrl + '">📄 詳細を Google Doc で開く</a></p>');
  var sect = {
    m_summary: function () {
      h.push(mailH2_('全区分サマリ'));
      h.push(mailTable_(['区分', '応募', '内定相当', '確定', '確定目標', '達成率', 'ペース', '着地予想'], segNum.map(function (r) { return r.map(String); })));
    },
    m_funnel: function () {
      Ms.forEach(function (M) {
        if (!M.counts[0]) return; var sy = buildStepYield_(M.stageNames, M.counts);
        h.push(mailH2_(M.seg + ' ファネル歩留まり'));
        h.push(mailTable_(sy.header, sy.rows.map(function (r) { return r.map(String); })));
      });
    },
    m_channel: function () {
      var ch = buildCrossChannel_();
      h.push(mailH2_('チャネル別 CVR / CPA（全区分横断）'));
      h.push(mailTable_(ch.header, ch.rows.map(function (r) { return r.map(String); })));
    },
    m_insight: function () {
      var ins = insightsAll_(segNum); h.push(mailH2_('所感'), '<ul>');
      [['◎ Good', ins.good], ['△ 課題', ins.issue], ['⚠ Risk', ins.risk]].forEach(function (grp) {
        grp[1].forEach(function (t) { h.push('<li>' + esc_(grp[0] + '  ' + t) + '</li>'); });
      });
      h.push('</ul>');
    }
  };
  keys.forEach(function (k) { if (sect[k]) sect[k](); }); // m_chartはメール非対応→skip
  h.push('<p style="color:#6B6B6B;font-size:12px">自動送信 / 基準日 ' + fmtD_(n) + '</p></div>');
  try {
    MailApp.sendEmail({ to: to.join(','), subject: '[' + cn + '] 採用 月次レポート ' + label, htmlBody: h.join(''), name: cn + ' 採用管理' });
  } catch (e) {
    if (!silent) toast_('メール送信に失敗: ' + e); else Logger.log('monthly mail send error: ' + e);
    return false;
  }
  if (!silent) toast_('月次レポートを ' + to.length + '名へメール送信しました');
  return true;
}
// メールHTML用ヘルパー
function esc_(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }
function mailH2_(t) { return '<h2 style="color:#000;border-left:5px solid #AF322C;padding-left:8px;margin-top:18px;font-size:15px">' + esc_(t) + '</h2>'; }
function mailTable_(header, rows) {
  var s = '<table style="border-collapse:collapse;width:100%;font-size:13px;margin:6px 0">';
  s += '<tr>' + header.map(function (x) { return '<th style="background:#000;color:#fff;border:1px solid #D9D9D9;padding:5px 8px;text-align:left">' + esc_(x) + '</th>'; }).join('') + '</tr>';
  rows.forEach(function (r, i) {
    var bg = (i % 2) ? '#F7F5F4' : '#ffffff';
    s += '<tr>' + r.map(function (c) { return '<td style="background:' + bg + ';border:1px solid #D9D9D9;padding:5px 8px">' + esc_(c) + '</td>'; }).join('') + '</tr>';
  });
  return s + '</table>';
}
function docHeading_(body, text, level, color) {
  var p = body.appendParagraph(text); p.setHeading(level);
  if (color) p.editAsText().setForegroundColor(color);
  return p;
}
function appendDocTable_(body, header, rows) {
  var table = body.appendTable([header].concat(rows));
  var hr = table.getRow(0);
  for (var c = 0; c < hr.getNumCells(); c++) {
    var cell = hr.getCell(c); cell.setBackgroundColor('#000000');
    cell.editAsText().setForegroundColor('#FFFFFF').setBold(true);
  }
  return table;
}

/* ---------- レポート用ヘルパー ---------- */

function subhead_(sh, row, text, span) {
  // 白地＋黒太字＋チャコール下罫(セクション見出しと統一)。span=下罫の列数(既定12=B〜M)。
  sh.getRange(row, 2).setValue(text).setFontColor(C.BLACK).setFontWeight('bold').setFontSize(11);
  sh.getRange(row, 2, 1, span || 12).setBorder(null, null, true, null, null, null, '#3A3A3A', SpreadsheetApp.BorderStyle.SOLID);
  return row + 1;
}

function renderBullets_(sh, row, title, items) {
  if (!items.length) items = ['—'];
  var isWarn = (title.indexOf('Risk') >= 0 || title.indexOf('課題') >= 0);
  for (var i = 0; i < items.length; i++) {
    sh.getRange(row, 2).setValue(i === 0 ? title : '')
      .setFontColor(isWarn ? C.RED : C.INK).setFontWeight('bold').setFontSize(10);
    var c = sh.getRange(row, 3, 1, 9); c.breakApart();
    c.merge().setValue(items[i]).setFontColor(C.INK).setFontSize(10).setWrap(true).setVerticalAlignment('middle');
    row++;
  }
  return row + 1;
}

// 当月/前月の活動量(各日付フィールドの該当月カウント)
function monthlyActivity_(rows, H) {
  var g = {};
  function add(d, key) { if (!(d instanceof Date)) return; var k = tokyoYM_(d); if (!g[k]) g[k] = { app: 0, off: 0, acc: 0, join: 0 }; g[k][key]++; }
  rows.forEach(function (r) {
    add(r[H['応募日']], 'app'); add(r[H['内定日']], 'off');
    add(r[H['承諾日']], 'acc'); add(r[H['入社日']], 'join');
  });
  return g;
}

// チャネル別 CVR + CPA(コスト/承諾)
function buildChannelReport_(rows, H, stageNames, idxOf) {
  var base = buildByKey_(rows, H, stageNames, idxOf, 'チャネル'); // [ch,応募,内定,承諾,入社,応募→承諾]
  var cost = {};
  confRead_('CHAN')
    .forEach(function (r) { cost[String(r[0])] = r[2]; });
  var header = ['チャネル', '応募', '内定', '承諾', '応募→承諾', 'コスト/月', 'CPA(円/承諾)'];
  var data = base.rows.map(function (r) {
    var c = cost[r[0]], acc = r[3];
    var cpa = (typeof c === 'number' && c > 0 && acc > 0) ? String(Math.round(c / acc))
      : (typeof c === 'number' ? '—' : (c || '—'));
    var costDisp = (typeof c === 'number') ? String(c) : (c || '');
    return [r[0], r[1], r[2], r[3], r[5], costDisp, cpa];
  });
  return { header: header, rows: data };
}

// ルールベースの所感(Good/課題/Risk)
function insights_(M) {
  var good = [], issue = [], risk = [];
  var accAct = (M.idxOf['承諾'] != null && M.counts[M.idxOf['承諾']] != null) ? M.counts[M.idxOf['承諾']] : 0;
  var accT = M.target['承諾'] || 0;
  if (accT > 0) {
    var p = Math.round(accAct / accT * 100);
    if (p >= 80) good.push('承諾が目標の' + p + '%。順調に着地見込み');
    else if (p < 50) risk.push('承諾達成率' + p + '%。目標未達リスク、母数(応募)の強化が必要');
    else issue.push('承諾達成率' + p + '%。内定→承諾の歩留まり改善で射程内');
  }
  var maxDrop = 0, dropStage = '';
  for (var i = 1; i < M.stageNames.length; i++) {
    var d = M.counts[i - 1] - M.counts[i];
    if (d > maxDrop) { maxDrop = d; dropStage = M.stageNames[i - 1] + '→' + M.stageNames[i]; }
  }
  if (maxDrop > 0) issue.push('最大の離脱は ' + dropStage + '（' + maxDrop + '名）。ここの通過率改善が効く');
  if (M.avgDays != null && M.avgDays > 30) risk.push('平均選考日数' + M.avgDays + '日。長期化で辞退リスク');
  else if (M.avgDays != null) good.push('平均選考日数' + M.avgDays + '日でスピード良好');
  return { good: good, issue: issue, risk: risk };
}

// 週次データ(今週の動き/来週の面接/要対応)。asOf 基準(空=今日)。
function weeklyData_(rows, H, ivData, ivH, asOf) {
  var anchor = tokyoDayMs_(asOf || nowTokyo_());
  function df_(d) { return (tokyoDayMs_(d) - anchor) / 86400000; }
  function inLastWeek(d) { if (!(d instanceof Date)) return false; var df = df_(d); return df <= 0 && df >= -6; }
  var w = { app: 0, off: 0, acc: 0, join: 0 };
  rows.forEach(function (r) {
    if (inLastWeek(r[H['応募日']])) w.app++;
    if (inLastWeek(r[H['内定日']])) w.off++;
    if (inLastWeek(r[H['承諾日']])) w.acc++;
    if (inLastWeek(r[H['入社日']])) w.join++;
  });
  var upcoming = [];
  ivData.forEach(function (r) {
    var st = String(r[ivH['ステータス']]); if (st !== '予定' && st !== '調整中') return;
    var dt = r[ivH['予定日時']]; if (!(dt instanceof Date)) return;
    var df = df_(dt); if (df >= 0 && df <= 7)
      upcoming.push([fmtDT_(dt), String(r[ivH['候補者名']]), String(r[ivH['ステージ']]), String(r[ivH['面接官']])]);
  });
  upcoming.sort(function (a, b) { return a[0] < b[0] ? -1 : 1; });
  var todo = [];
  rows.forEach(function (r) {
    if (String(r[H['ステータス']]) !== '進行中') return;
    var na = r[H['NA期限']]; if (!(na instanceof Date)) return;
    var df = df_(na); if (df <= 7)
      todo.push([fmtD_(na), String(r[H['氏名']]), String(r[H['ネクストアクション']]), String(r[H['採用担当RC']]), df < 0 ? '超過' : (df === 0 ? '本日' : '今週')]);
  });
  todo.sort(function (a, b) { return a[0] < b[0] ? -1 : 1; });
  return { w: w, upcoming: upcoming, todo: todo };
}

/* ============================== syncNextInterview ============================== */

function syncNextInterview() {
  var ss = ss_();
  var iv = sheet_(SH.IV), m = sheet_(SH.MASTER);
  var ivData = iv.getDataRange().getValues();
  if (ivData.length < 2) return;
  var ivH = headerIndex_(ivData.shift());
  var best = {};
  ivData.forEach(function (r) {
    var cid = String(r[ivH['candidate_id']]).trim(); if (!cid) return;
    var st = String(r[ivH['ステータス']]); if (st !== '予定' && st !== '調整中') return;
    var dt = r[ivH['予定日時']]; if (!(dt instanceof Date)) return;
    if (!best[cid] || dt < best[cid].dt) {
      best[cid] = { dt: dt, url: r[ivH['面接URL']], who: r[ivH['面接官']] };
    }
  });

  var mData = m.getDataRange().getValues();
  if (mData.length < 2) return;
  var mH = headerIndex_(mData[0]);
  var out = [];
  for (var i = 1; i < mData.length; i++) {
    var cid = String(mData[i][mH['candidate_id']]).trim();
    var b = best[cid];
    out.push([b ? b.dt : '', b ? b.url : '', b ? b.who : '']);
  }
  // 次回面接日時/URL/面接官 は連続列
  m.getRange(2, mH['次回面接日時'] + 1, out.length, 3).setValues(out);
}

/* ============================== 面接サマリ集計（マスタ集計列） ============================== */

// 11_の「実施済」面接から候補者ごとの 面接回数/直近面接日/直近フェーズ/平均評点/最新評価 をマスタへ反映
function syncInterviewSummary_() {
  var iv = sheet_(SH.IV), m = sheet_(SH.MASTER);
  var ivData = iv.getDataRange().getValues();
  var agg = {};
  if (ivData.length >= 2) {
    var ivH = headerIndex_(ivData.shift());
    ivData.forEach(function (r) {
      var cid = String(r[ivH['candidate_id']]).trim(); if (!cid) return;
      if (String(r[ivH['ステータス']]) !== '実施済') return;  // 評価がつく=実施済のみ
      var dt = r[ivH['予定日時']];
      var letter = String(r[ivH['評点']] || '').trim();   // 評点=総合(S〜D)
      var memo = String(r[ivH['評価メモ']] || ''), stage = String(r[ivH['ステージ']] || ''), who = String(r[ivH['面接官']] || '');
      if (!agg[cid]) agg[cid] = { count: 0, last: null, lastWho: '', lastStage: '', lastLetter: '', lastMemo: '' };
      var a = agg[cid]; a.count++;
      if (dt instanceof Date && (!a.last || dt > a.last)) { a.last = dt; a.lastWho = who; a.lastStage = stage; a.lastLetter = letter; a.lastMemo = memo; }
    });
  }
  var mData = m.getDataRange().getValues();
  if (mData.length < 2) return;
  var mH = headerIndex_(mData[0]);
  var out = [];
  for (var i = 1; i < mData.length; i++) {
    var a = agg[String(mData[i][mH['candidate_id']]).trim()];
    if (a) { out.push([a.count, a.last || '', a.lastWho, a.lastStage, a.lastLetter, a.lastMemo]); }
    else { out.push([0, '', '', '', '', '']); }
  }
  // 面接回数/直近面接日/直近面接官/直近フェーズ/総合評価/最新評価 は連続6列
  m.getRange(2, mH['面接回数'] + 1, out.length, 6).setValues(out);
}

/* ============================== 12_面接評価ノート ============================== */

function buildEvalNote_() {
  var sh = sheet_(SH.NOTE);
  clearSheet_(sh);
  ensureGrid_(sh, 140, 12);
  sh.setColumnWidth(1, 28);
  sh.setColumnWidth(2, 96); sh.setColumnWidth(3, 150); sh.setColumnWidth(4, 96); sh.setColumnWidth(5, 96); sh.setColumnWidth(6, 150);
  sh.setColumnWidth(7, 16);
  sh.setColumnWidth(8, 188); sh.setColumnWidth(9, 50); sh.setColumnWidth(10, 160); sh.setColumnWidth(11, 120);
  bandTitle_(sh, 1, 2, 11, '■ ' + companyName_() + ' 面接評価ノート（入力して「保存」にチェック）');

  var conf = sheet_(SH.CONF), L = CONF_LAYOUT, m = sheet_(SH.MASTER);
  var mref = "'" + SH.MASTER + "'";

  // 候補者情報カード(候補者IDを入れると自動表示)
  labelCell_(sh, 3, 2, '候補者ID'); sh.getRange(3, 3).setBackground('#FFF3F2');
  vCellRange_(sh, 3, 3, m.getRange(2, 1, 300, 1));
  pairLabels_(sh, 4, '氏名', '区分'); pairLabels_(sh, 5, '職種', 'チャネル'); pairLabels_(sh, 6, '現ステージ', '担当RC');
  // VLOOKUP列番号はヘッダー名から算出(マスタ列追加/並べ替えに耐える)
  var mH = headerIndex_(MASTER_COLS), mLast = colLetter_(MASTER_COLS.length);
  var vl_ = function (name) { return '=IFERROR(VLOOKUP($C$3,' + mref + '!$A:$' + mLast + ',' + (mH[name] + 1) + ',FALSE),"")'; };
  sh.getRange(4, 3).setFormula(vl_('氏名'));
  sh.getRange(4, 6).setFormula(vl_('区分'));
  sh.getRange(5, 3).setFormula(vl_('職種'));
  sh.getRange(5, 6).setFormula(vl_('チャネル'));
  sh.getRange(6, 3).setFormula(vl_('現ステージ'));
  sh.getRange(6, 6).setFormula(vl_('採用担当RC'));
  sh.getRange(3, 2, 4, 5).setBorder(true, true, true, true, true, true, C.BORDER, SpreadsheetApp.BorderStyle.SOLID);

  // 面接メタ
  pairLabels_(sh, 8, 'フェーズ', '面接日'); pairLabels_(sh, 9, '面接官', '形式'); pairLabels_(sh, 10, '結果', '面接URL');
  sh.getRange(8, 6).setNumberFormat('yyyy-mm-dd');
  vCellRange_(sh, 8, 3, confSrc_(conf, 'STAGE', 2));
  vCellRange_(sh, 9, 3, confSrc_(conf, 'MEMBER', 0));
  vCellList_(sh, 9, 6, IV_FORMAT);
  vCellList_(sh, 10, 3, IV_RESULT);
  sh.getRange(8, 2, 3, 5).setBorder(true, true, true, true, true, true, C.BORDER, SpreadsheetApp.BorderStyle.SOLID);
  for (var rh = 3; rh <= 11; rh++) sh.setRowHeight(rh, 26);  // カード/メタ/評価項目行を入力しやすく

  // メモ(充実・3分割＋総合所感)
  memoBox_(sh, 12, '良かった点', '強み・通過理由を具体的に', 2);
  memoBox_(sh, 14, '懸念点', '不安要素・要確認点', 2);
  memoBox_(sh, 16, '次アクション', '次フェーズ/見送り/要相談など', 2);
  memoBox_(sh, 18, '総合所感', '全体の所感（複数行で記入可）', 4);

  // 評価(右ブロック・設定の評価項目を動的展開)
  var items = evalItems_();
  sh.getRange(3, 8, 1, 4).merge().setValue('■ 評価（1〜5・5=最高／最低点割れはNG）')
    .setBackground(C.WHITE).setFontColor(C.BLACK).setFontWeight('bold').setVerticalAlignment('middle')
    .setBorder(null, null, true, null, null, null, '#3A3A3A', SpreadsheetApp.BorderStyle.SOLID);
  sh.getRange(4, 8, 1, 4).setValues([['評価項目', '点', '観点メモ', '']])
    .setBackground('#3A3A3A').setFontColor(C.WHITE).setFontWeight('bold').setFontSize(9).setHorizontalAlignment('center');
  var R0 = 5;
  for (var i = 0; i < items.length; i++) {
    var rr = R0 + i;
    sh.getRange(rr, 8).setValue(items[i].name + (items[i].min ? ' (≥' + items[i].min + ')' : '')).setFontSize(10).setVerticalAlignment('middle').setWrap(true);
    sh.getRange(rr, 9).setBackground(C.WHITE).setHorizontalAlignment('center');
    vCellList_(sh, rr, 9, ['1', '2', '3', '4', '5']);
    sh.getRange(rr, 10, 1, 2).merge().setBackground(C.WHITE).setWrap(true);
  }
  var prevRow = R0 + items.length;
  sh.getRange(prevRow, 8).setValue('総合プレビュー').setFontWeight('bold').setFontColor(C.BLACK).setBackground(HEAD_BG);
  sh.getRange(prevRow, 9, 1, 3).merge().setValue('（点入力で自動計算）').setFontColor(C.SUB).setFontSize(10).setVerticalAlignment('middle');
  sh.getRange(3, 8, items.length + 3, 4).setBorder(true, true, true, true, true, true, C.BORDER, SpreadsheetApp.BorderStyle.SOLID);

  // 保存
  sh.getRange(23, 2).setValue('保存する →').setFontWeight('bold').setFontColor(C.RED).setVerticalAlignment('middle');
  sh.getRange(23, 3).insertCheckboxes().setValue(false);
  sh.getRange(23, 4, 1, 8).breakApart();
  sh.getRange(23, 4, 1, 8).merge().setValue('チェックで 11_面接スケジュール に記録＋マスタ集計を更新（評価申し送りが有効ならSlackへ自動配信）').setFontColor(C.SUB).setFontSize(9).setWrap(true).setVerticalAlignment('middle');

  // 申し送り(候補者IDを入れるとこれまでの評価を自動表示→次の面接官へ)
  sh.getRange(25, 2, 1, 10).breakApart();
  sh.getRange(25, 2, 1, 10).merge().setValue('▎📋 申し送り（この候補者のこれまでの評価｜次の面接官へ）').setFontColor(C.RED).setFontWeight('bold').setFontSize(11).setVerticalAlignment('middle');
  refreshHandover_(String(sh.getRange(3, 3).getValue()).trim());

  // 評価履歴(全候補者・実施済・新しい順)
  var iv = sheet_(SH.IV); var ivData = iv.getDataRange().getValues(); var hist = [];
  if (ivData.length >= 2) {
    var ivH = headerIndex_(ivData.shift());
    ivData.forEach(function (r) {
      if (String(r[ivH['ステータス']]) !== '実施済') return;
      var dt = r[ivH['予定日時']];
      hist.push([dt instanceof Date ? dt : '', String(r[ivH['候補者名']] || ''), String(r[ivH['区分']] || ''),
        String(r[ivH['ステージ']] || ''), String(r[ivH['面接官']] || ''), String(r[ivH['評点']] || ''),
        String(r[ivH['判定']] || ''), String(r[ivH['評価メモ']] || '')]);
    });
    hist.sort(function (a, b) { return (b[0] instanceof Date ? b[0].getTime() : 0) - (a[0] instanceof Date ? a[0].getTime() : 0); });
  }
  sh.getRange(34, 2).setValue('▎評価履歴（全候補者・実施済・新しい順）').setFontColor(C.BLACK).setFontWeight('bold').setFontSize(11);
  var hRows = hist.length ? hist.map(function (r) {
    return [r[0] ? Utilities.formatDate(r[0], ss_().getSpreadsheetTimeZone(), 'MM/dd') : '', r[1], r[2], r[3], r[4], r[5], r[6], r[7]];
  }) : [['—', '', '', '', '', '', '', '']];
  table_(sh, 35, 2, ['面接日', '候補者', '区分', 'フェーズ', '面接官', '総合', '判定', '所感'], hRows, [5, 6]);
}

// 申し送り: 指定候補者の過去「実施済」評価を 12_ の申し送り欄(行26〜)に描画
function refreshHandover_(cid) {
  var sh = sheet_(SH.NOTE);
  var area = sh.getRange(26, 2, 8, 10); area.breakApart(); area.clearContent().setBackground(C.WHITE);
  var hdr = ['面接日', 'フェーズ', '面接官', '総合', '判定', '所感(要約)'];
  if (!cid) { table_(sh, 26, 2, hdr, [['候補者IDを入力すると表示されます', '', '', '', '', '']], []); return; }
  var iv = sheet_(SH.IV); var data = iv.getDataRange().getValues();
  if (data.length < 2) { table_(sh, 26, 2, hdr, [['(履歴なし)', '', '', '', '', '']], []); return; }
  var H = headerIndex_(data.shift()); var list = [];
  data.forEach(function (r) {
    if (String(r[H['candidate_id']]).trim() !== cid) return;
    if (String(r[H['ステータス']]) !== '実施済') return;
    var dt = r[H['予定日時']];
    var memo = String(r[H['評価メモ']] || '').replace(/\n/g, ' / '); if (memo.length > 60) memo = memo.slice(0, 60) + '…';
    list.push([dt instanceof Date ? dt : '', String(r[H['ステージ']] || ''), String(r[H['面接官']] || ''), String(r[H['評点']] || ''), String(r[H['判定']] || ''), memo]);
  });
  list.sort(function (a, b) { return (a[0] instanceof Date ? a[0].getTime() : 0) - (b[0] instanceof Date ? b[0].getTime() : 0); });
  list = list.slice(0, 6);
  var rows = list.length ? list.map(function (r) { return [r[0] ? Utilities.formatDate(r[0], ss_().getSpreadsheetTimeZone(), 'MM/dd') : '', r[1], r[2], r[3], r[4], r[5]]; })
    : [['(この候補者の実施済評価はまだありません)', '', '', '', '', '']];
  table_(sh, 26, 2, hdr, rows, [3, 4]);
}

function labelCell_(sh, r, c, text) {
  sh.getRange(r, c).setValue(text).setFontWeight('bold').setFontColor(C.BLACK).setBackground(HEAD_BG).setVerticalAlignment('middle');
}
function pairLabels_(sh, r, l1, l2) {
  labelCell_(sh, r, 2, l1); sh.getRange(r, 3).setBackground(C.WHITE);
  labelCell_(sh, r, 5, l2); sh.getRange(r, 6).setBackground(C.WHITE);
}
function memoBox_(sh, r, label, hint, h) {
  labelCell_(sh, r, 2, label); sh.getRange(r, 2).setNote(hint);
  var box = sh.getRange(r, 3, h, 4); box.breakApart();
  box.merge().setBackground(C.WHITE).setWrap(true).setVerticalAlignment('top').setFontColor(C.INK);
  for (var k = 0; k < h; k++) sh.setRowHeight(r + k, 30);  // 入力しやすいよう行高を確保
  sh.getRange(r, 2, h, 5).setBorder(true, true, true, true, false, false, C.BORDER, SpreadsheetApp.BorderStyle.SOLID);
}
function vCellRange_(sh, r, c, range) {
  sh.getRange(r, c).setDataValidation(SpreadsheetApp.newDataValidation().requireValueInRange(range, true).setAllowInvalid(true).build());
}
function vCellList_(sh, r, c, list) {
  sh.getRange(r, c).setDataValidation(SpreadsheetApp.newDataValidation().requireValueInList(list, true).setAllowInvalid(true).build());
}

// 総合プレビュー再計算(onEditから)
function refreshEvalPreview_() {
  var sh = sheet_(SH.NOTE);
  var items = evalItems_(), R0 = 5, scores = {};
  for (var i = 0; i < items.length; i++) scores[items[i].name] = sh.getRange(R0 + i, 9).getValue();
  var ev = computeEval_(items, scores);
  var prevRow = R0 + items.length;
  var txt = ev.n ? (ev.letter + '（' + ev.avg + '）' + (ev.ng ? '  ⚠NG基準未達' : '')) : '（点入力で自動計算）';
  sh.getRange(prevRow, 9, 1, 3).setValue(txt).setFontColor(ev.ng ? C.RED : C.INK).setFontWeight(ev.n ? 'bold' : 'normal');
}

// 面接評価ノートを 11_ に保存(メニュー or 保存チェックから)。評価エンジンで総合S〜D/判定を算出。
function saveEvaluation() {
  var sh = sheet_(SH.NOTE);
  var cid = String(sh.getRange(3, 3).getValue()).trim();
  if (!cid) { toast_('候補者IDを入力してください'); return; }
  var stage = String(sh.getRange(8, 3).getValue()).trim();
  var date = sh.getRange(8, 6).getValue();
  var member = String(sh.getRange(9, 3).getValue()).trim();
  var format = String(sh.getRange(9, 6).getValue()).trim() || 'オンライン';
  var result = String(sh.getRange(10, 3).getValue()).trim();
  var url = String(sh.getRange(10, 6).getValue()).trim();
  var good = String(sh.getRange(12, 3).getValue()).trim();
  var concern = String(sh.getRange(14, 3).getValue()).trim();
  var nextA = String(sh.getRange(16, 3).getValue()).trim();
  var overall = String(sh.getRange(18, 3).getValue()).trim();

  var items = evalItems_(), R0 = 5, scores = {}, imemos = {};
  for (var i = 0; i < items.length; i++) {
    var s = sh.getRange(R0 + i, 9).getValue();
    if (s !== '' && s != null) scores[items[i].name] = Number(s);
    var im = String(sh.getRange(R0 + i, 10).getValue()).trim();
    if (im) imemos[items[i].name] = im;
  }
  var ev = computeEval_(items, scores);

  var m = sheet_(SH.MASTER); var md = m.getDataRange().getValues(); var mH = headerIndex_(md[0]);
  var name = '', seg = '', job = '';
  for (var j = 1; j < md.length; j++) {
    if (String(md[j][mH['candidate_id']]).trim() === cid) { name = md[j][mH['氏名']]; seg = md[j][mH['区分']]; job = md[j][mH['職種']]; break; }
  }
  if (!name) { toast_('候補者ID「' + cid + '」がマスタに見つかりません'); return; }

  var memoParts = [];
  if (overall) memoParts.push(overall);
  if (good) memoParts.push('◎良かった点: ' + good);
  if (concern) memoParts.push('△懸念: ' + concern);
  if (nextA) memoParts.push('→次: ' + nextA);
  var memo = memoParts.join('\n');

  var iv = sheet_(SH.IV); var ivH = headerIndex_(iv.getRange(1, 1, 1, iv.getLastColumn()).getValues()[0]);
  var arr = new Array(IV_COLS.length); for (var k = 0; k < arr.length; k++) arr[k] = '';
  arr[ivH['interview_id']] = nextInterviewId_(iv, ivH);
  arr[ivH['candidate_id']] = cid; arr[ivH['候補者名']] = name; arr[ivH['区分']] = seg; arr[ivH['職種']] = job;
  arr[ivH['ステージ']] = stage; arr[ivH['予定日時']] = (date instanceof Date) ? date : new Date();
  arr[ivH['面接URL']] = url; arr[ivH['面接官']] = member; arr[ivH['形式']] = format;
  arr[ivH['ステータス']] = '実施済'; arr[ivH['結果']] = result;
  arr[ivH['評点']] = ev.letter; arr[ivH['評価メモ']] = memo;
  arr[ivH['総合点']] = ev.n ? ev.avg : '';
  arr[ivH['評価明細']] = JSON.stringify({ scores: ev.detail, memos: imemos });
  arr[ivH['判定']] = ev.n ? (ev.ng ? 'NG' : '合') : '';
  iv.getRange(iv.getLastRow() + 1, 1, 1, arr.length).setValues([arr]);

  syncInterviewSummary_();
  syncNextInterview();
  buildEvalNote_();
  // WP26: 評価申し送りをSlackへ(有効なら)
  var st = slackTargetByPrefix_('評価申し送り');
  if (st && st.enabled && st.channel) {
    var lines = ['*評価申し送り｜' + name + '（' + seg + ' / ' + stage + '）*',
      '総合評価: ' + (ev.letter || '—') + (ev.ng ? '  ⚠NG（基準未達）' : '') + (member ? '　面接官: ' + member : '')];
    if (good) lines.push('◎ 良かった点: ' + good);
    if (concern) lines.push('△ 懸念点: ' + concern);
    if (nextA) lines.push('→ 次アクション: ' + nextA);
    sendSlack_(st.channel, lines.join('\n'));
  }
  toast_('保存: ' + name + ' / 総合 ' + (ev.letter || '—') + (ev.ng ? '（NG・基準未達）' : '') + ' → 11_記録・マスタ更新');
}
function nextInterviewId_(iv, ivH) {
  var data = iv.getDataRange().getValues(); var max = 0;
  for (var i = 1; i < data.length; i++) { var mm = String(data[i][ivH['interview_id']]).match(/(\d+)\s*$/); if (mm) max = Math.max(max, Number(mm[1])); }
  return 'IV-' + nowTokyo_().getUTCFullYear() + '-' + ('000' + (max + 1)).slice(-4);
}

/* ============================== 20_統合ダッシュボード ============================== */

// 全区分横断の月次ファネル(応募月コホート×5段正規化＋遷移率)。直近12ヶ月。
function buildAllMonthlyFunnel_() {
  var now = nowTokyo_(), keys = [], labels = {};
  for (var i = 11; i >= 0; i--) {
    var d = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() - i, 1));
    var k = d.getUTCFullYear() + '-' + ('0' + (d.getUTCMonth() + 1)).slice(-2);
    keys.push(k); labels[k] = k;
  }
  var buckets = {}; keys.forEach(function (k) { buckets[k] = [0, 0, 0, 0, 0]; }); // [応募,書類,面接,内定,確定]
  enabledSegments_().forEach(function (seg) {
    var M = computeSegment_(seg); if (!M.stageNames.length) return;
    var iApp = idxByType_(M.stageTypes, ['entry']); if (iApp < 0) iApp = 0;
    var iScr = idxByType_(M.stageTypes, ['screen']); if (iScr < 0) iScr = iApp;
    var iInt = idxByType_(M.stageTypes, ['interview', 'task']); if (iInt < 0) iInt = iScr;
    var iOff = idxByType_(M.stageTypes, ['offer']); if (iOff < 0) iOff = iInt;
    var iFin = idxByType_(M.stageTypes, ['join']); if (iFin < 0) iFin = idxByType_(M.stageTypes, ['accept']); if (iFin < 0) iFin = iOff;
    var idxs = [iApp, iScr, iInt, iOff, iFin];
    M.rows.forEach(function (r) {
      var ap = r[M.H['応募日']]; if (!(ap instanceof Date)) return;
      var key = ap.getUTCFullYear() + '-' + ('0' + (ap.getUTCMonth() + 1)).slice(-2);
      if (!buckets[key]) return;
      var cur = String(r[M.H['現ステージ']]); var si = (cur in M.idxOf) ? M.idxOf[cur] : -1;
      if (si < 0) return;
      for (var s = 0; s < 5; s++) if (si >= idxs[s]) buckets[key][s]++;
    });
  });
  var names = ['応募', '書類相当', '面接相当', '内定相当', '確定'];
  var header = ['月'].concat(names);
  for (var s2 = 1; s2 < 5; s2++) header.push('→' + names[s2]);
  var data = keys.map(function (k) {
    var c = buckets[k], row = [labels[k]].concat(c);
    for (var s3 = 1; s3 < 5; s3++) row.push(pct_(c[s3], c[s3 - 1]));
    return row;
  });
  return { header: header, rows: data };
}

function renderAllDash_() {
  var sh = sheet_(SH.D_ALL);
  clearSheet_(sh);
  ensureGrid_(sh, 200, 28);
  sh.setColumnWidth(1, 28);
  for (var c = 2; c <= 19; c++) sh.setColumnWidth(c, 92);

  var now = nowTokyo_();
  var ymLabel = now.getUTCFullYear() + '年' + (now.getUTCMonth() + 1) + '月';
  var en0 = enabledSegments_(), single = en0.length === 1;  // 単一区分モード: 区分横断の要素を省く
  bandTitle_(sh, 1, 2, 19, single
    ? '■ ' + companyName_() + ' ' + en0[0] + ' 採用ダッシュボード    （' + ymLabel + '時点）'
    : '■ ' + companyName_() + ' 採用 統合ダッシュボード（全区分横断）    （' + ymLabel + '時点）');

  var Ms = enabledSegments_().map(function (s) { return computeSegment_(s); });

  // 全体KPI(ヘッドライン4枚＋補助3枚)
  var totActive = 0, totApp = 0, totOffer = 0, totFin = 0, totFinTgt = 0, allDays = 0, dayN = 0;
  Ms.forEach(function (M) {
    totActive += M.active;
    var nf = normalizedFunnel_(M); totApp += nf.app; totOffer += nf.offer; totFin += nf.fin;
    var fg = finalGoal_(M); if (fg) totFinTgt += fg.tgt;
    if (M.avgDays != null) { allDays += M.avgDays; dayN++; }
  });
  var dsAll = docStats_(enabledSegments_());
  kpiHero_(sh, 3, [
    { label: single ? '進行中' : '進行中（全）', value: totActive },
    { label: single ? '応募' : '応募（全）', value: totApp },
    { label: '内定相当', value: totOffer },
    { label: '確定', value: totFin, accent: true }
  ], 2, 3, { big: true });
  kpiHero_(sh, 6, [
    { label: '確定 目標達成 ' + totFin + '/' + totFinTgt, value: (totFinTgt ? pct_(totFin, totFinTgt) : '—'), accent: true },
    { label: '平均選考日数', value: (dayN ? Math.round(allDays / dayN) + '日' : '—') },
    { label: '書類回収率 ' + dsAll.collected + '/' + dsAll.target, value: (dsAll.target ? dsAll.rate : '—') }
  ], 2, 3);

  var row = 9;  // ヒーロー(3〜7)の下から本文

  // 区分別サマリ・区分別ファネルは2区分以上のときのみ(1区分では冗長＝KPI/月次と重複)
  if (!single) {
    var sumRows = Ms.map(function (M) {
      var nf = normalizedFunnel_(M); var fg = finalGoal_(M);
      var pc = pace_(M); var pg = pc.goals.length ? pc.goals[pc.goals.length - 1] : null;
      return [M.seg, M.active, nf.app, nf.offer, nf.fin, (fg ? fg.tgt : 0), (fg ? pct_(fg.act, fg.tgt) : '—'),
              (pg ? paceText_(pg) : '—'), (pg ? pg.forecast : 0)];
    });
    sectionHead_(sh, row, 2, 9, '区分別サマリ（達成率・ペース・着地予想）');
    row = table_(sh, row + 1, 2, ['区分', '進行中', '応募', '内定相当', '確定', '確定目標', '達成率', 'ペース', '着地予想'], sumRows, [6]);
    var fRows = Ms.map(function (M) {
      var nf = normalizedFunnel_(M);
      return [M.seg, nf.app, nf.doc, nf.interview, nf.offer, nf.fin, pct_(nf.fin, nf.app)];
    });
    sectionHead_(sh, row, 2, 7, '区分別ファネル（5段正規化）');
    row = table_(sh, row + 1, 2, ['区分', '応募', '書類相当', '面接相当', '内定相当', '確定', '応募→確定'], fRows, [6]);
  }

  // 月次ファネル(5段正規化・応募月コホート＋遷移率)
  var amf = buildAllMonthlyFunnel_();
  sectionHead_(sh, row, 2, amf.header.length, single ? '月次ファネル（5段正規化／応募月コホート）' : '月次ファネル（全区分・5段正規化／応募月コホート）');
  row = table_(sh, row + 1, 2, amf.header, amf.rows, [6, 7, 8, 9]);

  // チャネル別 CVR/CPA(旧30を統合)
  var cg = crossAgg_('チャネル'), ccost = {};
  confRead_('CHAN').forEach(function (r) { ccost[String(r[0])] = r[2]; });
  var cKeys = Object.keys(cg).sort(function (a, b) { return cg[b].app - cg[a].app; });
  var cRows = cKeys.map(function (k) {
    var x = cg[k], cst = ccost[k];
    var cpa = (typeof cst === 'number' && cst > 0 && x.fin > 0) ? String(Math.round(cst / x.fin)) : (typeof cst === 'number' ? '—' : (cst || '—'));
    return [k, x.app, x.off, x.fin, pct_(x.fin, x.app), (typeof cst === 'number' ? String(cst) : (cst || '')), cpa];
  });
  sectionHead_(sh, row, 2, 7, single ? 'チャネル別 CVR / CPA' : 'チャネル別 CVR / CPA（全区分横断）');
  row = table_(sh, row + 1, 2, ['チャネル', '応募', '内定相当', '確定', '応募→確定', 'コスト/月', 'CPA(円/確定)'], cRows.length ? cRows : [['—', 0, 0, 0, '—', '', '—']], [4, 6]);

  // 職種別 目標充足(旧31を統合)
  var jg = crossAgg_('職種'), jtgt = {};
  confRead_('JOB').forEach(function (r) { var k = String(r[0]); jtgt[k] = (jtgt[k] || 0) + Number(r[2] || 0); });
  var jKeys = Object.keys(jg).sort(function (a, b) { return jg[b].app - jg[a].app; });
  var jRows = jKeys.map(function (k) { var x = jg[k], t = jtgt[k] || 0; return [k, x.app, x.off, x.fin, pct_(x.fin, x.app), t, pct_(x.off, t)]; });
  sectionHead_(sh, row, 2, 7, '職種別（応募→確定・充足率=内定相当/目標）');
  var footRow = table_(sh, row + 1, 2, ['職種', '応募', '内定相当', '確定', '応募→確定', '目標', '充足率'], jRows.length ? jRows : [['—', 0, 0, 0, '—', 0, '—']], [4, 6]);

  // チャート(右 M列〜): 区分別 確定vs目標 バー + 区分別 応募 円。2区分以上のときのみ(1区分では無意味・ヒーロー下に配置)
  if (!single) {
    var cd = 21;
    var barData = [['区分', '確定', '確定目標']].concat(Ms.map(function (M) {
      var nf = normalizedFunnel_(M); var fg = finalGoal_(M);
      return [M.seg, nf.fin, (fg ? fg.tgt : 0)];
    }));
    sh.getRange(3, cd, barData.length, 3).setValues(barData);
    addColumnChart_(sh, sh.getRange(3, cd, barData.length, 3), 9, 13, '区分別 確定 vs 目標');
    var pieData = [['区分', '応募']].concat(Ms.map(function (M) { return [M.seg, normalizedFunnel_(M).app]; }));
    sh.getRange(3, cd + 4, pieData.length, 2).setValues(pieData);
    addPieChart_(sh, sh.getRange(3, cd + 4, pieData.length, 2), 23, 13, '応募 区分別構成');
  }

  var tz = ss_().getSpreadsheetTimeZone();
  sh.getRange(footRow + 1, 2, 1, 10).merge()
    .setValue('最終更新: ' + Utilities.formatDate(new Date(), tz, 'yyyy-MM-dd HH:mm')
      + (single ? '' : '  ／  各区分の詳細は 21〜24 タブ'))
    .setFontColor(C.SUB).setFontSize(9);
}

/* ============================== 30_チャネル分析 / 31_職種分析 ============================== */

// 全区分を横断し、候補者ごとに「確定(accept/join到達)」「内定相当(offer到達)」を正規化判定して集計
function crossAgg_(keyName) {
  var conf = sheet_(SH.CONF);
  var stagesAll = confRead_('STAGE');
  var segMeta = {}; // seg -> {idxOf, types}
  enabledSegments_().forEach(function (s) {
    var st = stagesAll.filter(function (r) { return String(r[0]) === s; })
                      .sort(function (a, b) { return Number(a[1]) - Number(b[1]); });
    var idxOf = {}, types = [];
    st.forEach(function (r, i) { idxOf[String(r[2])] = i; types.push(String(r[3])); });
    segMeta[s] = { idxOf: idxOf, types: types };
  });
  var m = sheet_(SH.MASTER);
  var data = m.getDataRange().getValues(); var H = headerIndex_(data.shift());
  var g = {};
  data.forEach(function (r) {
    var cid = String(r[H['candidate_id']]).trim(); if (!cid) return;
    var seg = String(r[H['区分']]); var meta = segMeta[seg]; if (!meta) return;
    var key = String(r[H[keyName]] || '(未設定)');
    if (!g[key]) g[key] = { app: 0, off: 0, fin: 0 };
    g[key].app++;
    var si = (String(r[H['現ステージ']]) in meta.idxOf) ? meta.idxOf[String(r[H['現ステージ']])] : -1;
    if (si < 0) return;
    var iOff = idxByType_(meta.types, ['offer']);
    var iFin = idxByType_(meta.types, ['join']); if (iFin < 0) iFin = idxByType_(meta.types, ['accept']); if (iFin < 0) iFin = iOff;
    if (iOff >= 0 && si >= iOff) g[key].off++;
    if (iFin >= 0 && si >= iFin) g[key].fin++;
  });
  return g;
}

// 旧 renderChannelAnalysis_ / renderJobAnalysis_ は廃止。内容は renderAllDash_(20統合) のセクションに統合。

/* ============================== onEdit: 現ステージを区分で絞り込む ============================== */

function onEdit(e) {
  try {
    if (!e || !e.range) return;
    var sh = e.range.getSheet();
    var name = sh.getName();
    if (name === SH.MASTER) {
      var H = headerIndex_(sh.getRange(1, 1, 1, sh.getLastColumn()).getValues()[0]);
      var col = e.range.getColumn(), rown = e.range.getRow(); if (rown < 2) return;
      if (col === H['区分'] + 1) {
        applyStageValidationForRow_(sh, rown, String(e.range.getValue()), H);
        return;
      }
      // 履歴書/職務経歴書リンク入力 → 対応する回収日が空なら本日(東京)を自動記録
      DOC_TYPES.forEach(function (d) {
        if (col !== H[d.link] + 1) return;
        if (String(e.range.getValue() || '').trim() === '') return;
        if (H[d.date] == null) return;
        var dc = sh.getRange(rown, H[d.date] + 1);
        if (String(dc.getValue() || '').trim() === '') {
          var n = nowTokyo_();
          dc.setValue(d_(n.getUTCFullYear(), n.getUTCMonth() + 1, n.getUTCDate())).setNumberFormat('yyyy-mm-dd');
        }
      });
    } else if (name === SH.NOTE) {
      var rr = e.range.getRow(), cc = e.range.getColumn();
      if (rr === 23 && cc === 3 && String(e.value).toUpperCase() === 'TRUE') {
        sh.getRange(23, 3).setValue(false);  // チェックを戻す(setValueは簡易onEditを再発火しない)
        saveEvaluation();
      } else if (cc === 9 && rr >= 5 && rr <= 20) {
        refreshEvalPreview_();  // 評価点入力→総合プレビュー再計算
      } else if (cc === 3 && rr === 3) {
        refreshHandover_(String(e.value || '').trim());  // 候補者ID→申し送り自動表示
      }
    } else if (name === SH.CSV) {
      if (e.range.getRow() === 21 && e.range.getColumn() === 3 && String(e.value).toUpperCase() === 'TRUE') {
        sh.getRange(21, 3).setValue(false);
        importCsv();
      }
    } else if (name === SH.CONF) {
      // 選考ステージ定義: ステージ名(C列)を候補から選択→隣の種別(D列)を STAGE_CATALOG から自動補完
      var LS = CONF_LAYOUT.STAGE, ec = e.range.getColumn(), er = e.range.getRow();
      if (ec === LS.col + 2 && er >= LS.row && er < LS.row + LS.max) {
        var picked = String(e.range.getValue() || '').trim(), hit = null;
        for (var i = 0; i < STAGE_CATALOG.length; i++) { if (STAGE_CATALOG[i][0] === picked) { hit = STAGE_CATALOG[i][1]; break; } }
        if (hit) sh.getRange(er, LS.col + 3).setValue(hit);
      }
    } else if (name.slice(-MANAGE_SUFFIX.length) === MANAGE_SUFFIX) {
      syncManageEditToMaster_(e, sh);  // ②進捗管理の作業ビュー編集→マスタへ書き戻し(正本=マスタ)
    }
  } catch (err) { try { Logger.log('onEdit error: ' + err + ' | sheet=' + (e && e.range ? e.range.getSheet().getName() : '?') + ' | cell=' + (e && e.range ? e.range.getA1Notation() : '?')); } catch (e2) {} }  // simple triggerは再throw不可→最低限ログ
}

function applyStageValidationForRow_(sh, rown, seg, H) {
  var stages = confRead_('STAGE')
    .filter(function (r) { return String(r[0]) === seg; })
    .sort(function (a, b) { return Number(a[1]) - Number(b[1]); })
    .map(function (r) { return String(r[2]); });
  if (!stages.length) return;
  var rule = SpreadsheetApp.newDataValidation().requireValueInList(stages, true).setAllowInvalid(true).build();
  sh.getRange(rown, H['現ステージ'] + 1).setDataValidation(rule);
}

/* ============================== コンサル設計タブ (WP27-29) ============================== */

// 区分のステージ([{name,type,rate}], 順序ソート)
// ⚠️実行内キャッシュ: docState_(書類)等が候補者1行ごとに呼ぶため、毎回STAGEをシート読みすると重い。
//   STAGEは実行中に変わらない(setupAllはbuildSettings_で先に書込→以降の参照は最新)。docsCacheClear_でリセット。
var _segStagesCache = null;
function segStages_(seg) {
  if (!_segStagesCache) {
    _segStagesCache = {};
    confRead_('STAGE').forEach(function (r) { var s = String(r[0]); (_segStagesCache[s] = _segStagesCache[s] || []).push(r); });
  }
  return (_segStagesCache[String(seg)] || []).slice()
    .sort(function (a, b) { return Number(a[1]) - Number(b[1]); })
    .map(function (r) { return { name: String(r[2]), type: String(r[3]), rate: parsePct_(r[4]) }; });
}
// 設計用の月レンジ [{key:'YYYY-MM', label:'YYYY/MM'}]。対象期間=〆(最終月)としてアンカーし、
// 活動月が手前に並ぶよう count ヶ月を 〆 で終わるように生成(新卒は活動が〆の前年から始まるため)。対象期間が空なら当月を最終月に。
function designMonths_(seg, count) {
  count = count || 12;
  var tgt = confRead_('TARGET').filter(function (r) { return String(r[0]) === seg; })[0];
  var mm = tgt ? String(tgt[4] || '').replace(/[\/.]/g, '-').match(/(\d{4})-(\d{1,2})/) : null;
  var y, m;
  if (mm) { y = Number(mm[1]); m = Number(mm[2]) - 1; } else { var n = nowTokyo_(); y = n.getUTCFullYear(); m = n.getUTCMonth(); }
  var out = [];
  for (var i = 0; i < count; i++) { var d = new Date(Date.UTC(y, m - (count - 1) + i, 1)); out.push({ key: d.getUTCFullYear() + '-' + ('0' + (d.getUTCMonth() + 1)).slice(-2), label: d.getUTCFullYear() + '/' + ('0' + (d.getUTCMonth() + 1)).slice(-2) }); }
  return out;
}

// WP27: 02_選考設計・社内体制(区分ごと・手入力・入力保持)
// 設計タブの版管理(版不一致なら再構築・以降は入力保持)
var DESIGN_VER = 'v3-goalactual';
function designNeedsRebuild_() { return PropertiesService.getDocumentProperties().getProperty('designVer') !== DESIGN_VER; }
// STEPバナー(赤帯＋ガイド2行)。次の空き行を返す。
function stepBanner_(sh, row, step, phase, subTitle, doText, nextText) {
  var r = sh.getRange(row, 2, 1, 16); r.breakApart();
  r.merge().setValue('STEP ' + step + '　' + phase + '　／　' + subTitle)
    .setBackground(C.WHITE).setFontColor(C.BLACK).setFontWeight('bold').setFontSize(13).setVerticalAlignment('middle');
  r.setBorder(null, null, true, null, null, null, C.RED, SpreadsheetApp.BorderStyle.SOLID);  // 下端=赤罫(アクセント)
  sh.setRowHeight(row, 34);
  sh.getRange(row + 1, 2, 1, 16).merge().setValue('▶ このタブで決めること： ' + doText).setFontColor(C.INK).setFontSize(10).setWrap(true).setVerticalAlignment('middle');
  sh.getRange(row + 2, 2, 1, 16).merge().setValue('▶ 次にやること： ' + nextText).setFontColor(C.SUB).setFontSize(10).setWrap(true).setVerticalAlignment('middle');
  return row + 4;
}
// 入力/自動の凡例。次の空き行を返す。
function inputLegend_(sh, row) {
  sh.getRange(row, 2).setValue('凡例').setFontWeight('bold').setFontColor(C.BLACK).setFontSize(9);
  sh.getRange(row, 3).setValue('✏️ 入力').setBackground('#FFF3F2').setFontSize(9).setHorizontalAlignment('center').setBorder(true, true, true, true, false, false, C.BORDER, SpreadsheetApp.BorderStyle.SOLID);
  sh.getRange(row, 4).setValue('自動計算').setBackground('#EFEFEF').setFontColor(C.SUB).setFontSize(9).setHorizontalAlignment('center').setBorder(true, true, true, true, false, false, C.BORDER, SpreadsheetApp.BorderStyle.SOLID);
  return row + 2;
}
var DESIGN_INPUT_BG = '#FFF3F2', DESIGN_AUTO_BG = '#EFEFEF';

// WP30: 02_選考設計・社内体制(区分ごと・STEPガイド・フロー帯・入力/自動色分け)
function buildFlowDesign_() {
  var sh = sheet_(SH.FLOW);
  var built = sh.getLastRow() > 5 && String(sh.getRange(8, 2).getValue() || '').trim() !== '';
  if (!designNeedsRebuild_() && built) return; // 入力保持
  clearSheet_(sh); ensureGrid_(sh, 300, 20);
  sh.setColumnWidth(1, 28); sh.setColumnWidth(2, 130); for (var c = 3; c <= 18; c++) sh.setColumnWidth(c, 104);
  bandTitle_(sh, 1, 2, 16, '■ ' + companyName_() + '　選考設計・社内体制');
  var row = stepBanner_(sh, 2, '①-1 / 初期設計', '選考フロー・社内体制', '各選考段階の通過率・担当・会場・URL・対応事項を設計',
    '各段階の通過率/担当/会場を埋める（区分ごと）', 'STEP②-2 採用目標（03）へ');
  row = inputLegend_(sh, row);
  enabledSegments_().forEach(function (seg) {
    var st = segStages_(seg); if (!st.length) return;
    sectionBand_(sh, row, seg + '　選考フロー'); row += 1;
    // フロー帯: 応募 ─80%→ 書類 …
    var flow = [];
    st.forEach(function (s, i) { if (i > 0) flow.push(s.rate != null ? '─' + Math.round(s.rate * 100) + '%→' : '→'); flow.push(s.name); });
    sh.getRange(row, 2, 1, Math.min(16, flow.length)).merge().setValue(flow.join('  ')).setFontColor(C.BLACK).setFontWeight('bold').setFontSize(10).setWrap(true).setBackground('#F7F5F4').setBorder(true, true, true, true, false, false, C.BORDER, SpreadsheetApp.BorderStyle.SOLID);
    row += 2;
    // 社内体制テーブル(項目×フェーズ)
    var head = ['項目'].concat(st.map(function (s) { return s.name; }));
    var items = [['想定通過率'].concat(st.map(function (s) { return s.rate != null ? Math.round(s.rate * 100) + '%' : ''; }))];
    ['リードタイム', 'スキップ可否', 'フロント担当', '担当者名', '開催場所', '交通費支給', '所要時間', '面接/面談URL', '対応事項', 'その他'].forEach(function (lab) {
      items.push([lab].concat(st.map(function () { return ''; })));
    });
    var tEnd = table_(sh, row, 2, head, items, []);
    // 想定通過率行=自動グレー / その他の値セル=入力ピンク
    sh.getRange(row + 1, 3, 1, st.length).setBackground(DESIGN_AUTO_BG);
    sh.getRange(row + 2, 3, items.length - 1, st.length).setBackground(DESIGN_INPUT_BG);
    row = tEnd + 1;
  });
}

// WP31: 03_採用目標・月別ファネル(STEPガイド・目標カード・合計列・最終段ハイライト・通過率カスケード)
function buildGoalDesign_() {
  var sh = sheet_(SH.GOAL);
  var built = sh.getLastRow() > 6 && String(sh.getRange(9, 2).getValue() || '').trim() !== '';
  if (!designNeedsRebuild_() && built) return; // 入力保持
  clearSheet_(sh); ensureGrid_(sh, 440, 20);
  sh.setColumnWidth(1, 28); sh.setColumnWidth(2, 140);
  sh.setColumnWidth(3, 70); sh.setColumnWidth(4, 70); sh.setColumnWidth(5, 64); sh.setColumnWidth(6, 56); sh.setColumnWidth(7, 60);
  for (var c = 8; c <= 20; c++) sh.setColumnWidth(c, 58);
  bandTitle_(sh, 1, 2, 18, '■ ' + companyName_() + '　採用目標・月別ファネル');
  var row = stepBanner_(sh, 2, '②-2 / 目標設計', '採用目標・月別ファネル', '各段の 目標 / 実績 / 達成率 と 月別エントリー目標＋遷移率（実績は候補者マスタから自動集計）',
    '👉行に月別エントリー目標を入力（目標通過率は調整可）', 'STEP②-3 エントリー目標（04）で媒体別に配分');
  row = inputLegend_(sh, row);
  var MS = 8; // 月の開始列(H)。B〜G＝フェーズ/目標通過率/実績通過率/目標合計/実績/達成率
  enabledSegments_().forEach(function (seg) {
    var st = segStages_(seg); if (!st.length) return;
    var months = designMonths_(seg, 12);
    var M = computeSegment_(seg); var cnt = (M && M.counts) || [];  // 実績(現ステージ到達数・累積)
    sectionBand_(sh, row, seg + '　採用目標'); row += 1;
    // 採用目標カード
    var cardRow = row;
    sh.getRange(cardRow, 2).setValue('🎯 採用目標(名)').setFontWeight('bold').setFontColor(C.BLACK);
    sh.getRange(cardRow, 3).setBackground(DESIGN_INPUT_BG);
    sh.getRange(cardRow, 4).setValue('〜').setHorizontalAlignment('center');
    sh.getRange(cardRow, 5).setBackground(DESIGN_INPUT_BG);
    sh.getRange(cardRow, 6).setValue('目標〆').setFontWeight('bold').setFontColor(C.BLACK);
    sh.getRange(cardRow, 7).setBackground(DESIGN_INPUT_BG);
    sh.getRange(cardRow, 8).setValue('着地見込み').setFontWeight('bold').setFontColor(C.BLACK);
    sh.getRange(cardRow, 2, 1, 9).setBorder(true, true, true, true, false, false, C.BORDER, SpreadsheetApp.BorderStyle.SOLID);
    row += 2;
    // 月別ファネル: フェーズ/目標通過率/実績通過率/目標合計/実績/達成率/各月
    var head = ['フェーズ', '目標通過率', '実績通過率', '目標合計', '実績', '達成率'].concat(months.map(function (m) { return m.label; }));
    sh.getRange(row, 2, 1, head.length).setNumberFormat('@').setValues([head]).setBackground(HEAD_BG).setFontColor(C.INK).setFontWeight('bold').setFontSize(9).setHorizontalAlignment('center');
    var hdr = row; row += 1;
    var firstDataRow = row;
    st.forEach(function (s, i) {
      var rr = row;
      sh.getRange(rr, 2).setValue(s.name).setVerticalAlignment('middle');
      // C=目標通過率(入力・i>0) / D=実績通過率(自動) / E=目標合計(=SUM月) / F=実績 / G=達成率
      if (i > 0 && s.rate != null) sh.getRange(rr, 3).setValue(s.rate);
      sh.getRange(rr, 3).setNumberFormat('0%').setBackground(i > 0 ? DESIGN_INPUT_BG : DESIGN_AUTO_BG);
      if (i > 0) sh.getRange(rr, 4).setFormula('=IF(F' + (rr - 1) + '>0,F' + rr + '/F' + (rr - 1) + ',"")');
      sh.getRange(rr, 4).setNumberFormat('0%').setBackground(DESIGN_AUTO_BG).setFontColor(C.SUB);
      sh.getRange(rr, 5).setFormula('=SUM(' + colLetter_(MS) + rr + ':' + colLetter_(MS + months.length - 1) + rr + ')').setFontWeight('bold').setBackground(DESIGN_AUTO_BG);
      sh.getRange(rr, 6).setValue(cnt[i] || 0).setFontWeight('bold').setBackground('#EAF3FB');  // 実績=マスタ集計
      sh.getRange(rr, 7).setFormula('=IF(E' + rr + '>0,F' + rr + '/E' + rr + ',"")').setNumberFormat('0%').setBackground(DESIGN_AUTO_BG);
      for (var j = 0; j < months.length; j++) {
        var col = MS + j, cell = sh.getRange(rr, col);
        if (i === 0) cell.setBackground(DESIGN_INPUT_BG);
        else cell.setFormula('=ROUND(' + colLetter_(col) + (rr - 1) + '*$C' + rr + ',0)').setBackground(DESIGN_AUTO_BG);
      }
      row += 1;
    });
    sh.getRange(firstDataRow, 2).setValue('👉 ' + st[0].name + '（エントリー目標）').setFontWeight('bold');
    var finalRow = firstDataRow + st.length - 1;
    sh.getRange(finalRow, 2, 1, head.length).setBackground('#F7E7E6');
    sh.getRange(finalRow, 2).setFontColor(C.RED).setFontWeight('bold');
    sh.getRange(cardRow, 10).setFormula('=E' + finalRow).setFontColor(C.RED).setFontWeight('bold').setBackground(DESIGN_AUTO_BG);
    sh.getRange(hdr, 2, finalRow - hdr + 1, head.length).setBorder(true, true, true, true, true, true, C.BORDER, SpreadsheetApp.BorderStyle.SOLID);
    row += 1;
    sh.getRange(row, 2, 1, 12).merge().setValue('※ ' + seg + '：👉行に月別エントリー目標を入力（目標合計・以降の段・着地見込みは自動カスケード）。実績＝10_候補者マスタの現ステージ到達数を自動集計、実績通過率＝実績の前段比、達成率＝実績÷目標合計（🔄更新で反映）。')
      .setFontColor(C.SUB).setFontSize(9).setWrap(true); row += 2;
  });
}

// WP29: 04_エントリー目標管理(カテゴリ>媒体名 × 月。目標=入力 / 実績=自動 / 差分)
// WP32: 04_エントリー目標管理(STEPガイド・カテゴリ色分け・差分の条件付き書式・実績自動)
// 既存04(3段レイアウト)の「目標」行の月別値を {媒体名: {月ラベル: 値}} で退避(チャネル追加でも入力保持・[[feedback_relayout_migration]])
function snapshotEntryTargets_(sh) {
  var snap = {}, last = sh.getLastRow(); if (last < 3) return snap;
  var lastCol = sh.getLastColumn();
  var scan = sh.getRange(1, 3, Math.min(last, 15), 1).getValues(), hdrRow = 0;
  for (var s = 0; s < scan.length; s++) { if (String(scan[s][0]).trim() === '媒体名') { hdrRow = s + 1; break; } }
  if (!hdrRow) return snap;
  var head = sh.getRange(hdrRow, 1, 1, lastCol).getValues()[0], labelCol = {};
  for (var c = 1; c <= lastCol; c++) {
    var raw = head[c - 1], hh;
    if (raw instanceof Date) hh = raw.getFullYear() + '/' + ('0' + (raw.getMonth() + 1)).slice(-2);  // 日付化した見出しも YYYY/MM に
    else hh = String(raw || '').trim().replace('-', '/');
    if (/^\d{4}\/\d{1,2}/.test(hh)) labelCol[c] = hh;  // 月列(YYYY/MM 見出し)
  }
  var vals = sh.getRange(hdrRow + 1, 1, last - hdrRow, lastCol).getValues();
  var curName = null;
  for (var i = 0; i < vals.length; i++) {
    var cName = String(vals[i][2] || '').trim();  // C=媒体名(マージ先頭=目標行)
    var metric = String(vals[i][3] || '').trim(); // D=指標
    if (metric === '目標' && cName) curName = cName;
    if (metric === '目標' && curName && curName !== '総合計' && curName !== '小計') {
      for (var col in labelCol) {
        var v = vals[i][Number(col) - 1];
        if (v !== '' && v !== null && !isNaN(Number(v)) && Number(v) !== 0) {
          if (!snap[curName]) snap[curName] = {};
          snap[curName][labelCol[col]] = Number(v);
        }
      }
    }
  }
  return snap;
}

// 04_エントリー目標管理(月=上段見出し・各媒体=目標/実績/達成率の3段・カテゴリ小計＋総合計)
function buildEntryTargets_() {
  var sh = sheet_(SH.ENTRY);
  var months = designMonths_(enabledSegments_()[0] || '新卒', 12);
  var nMon = months.length, MS2 = 6, lastMonCol = MS2 + nMon - 1;  // B=カテゴリ C=媒体名 D=指標 E=合計 F〜=月
  var snap = snapshotEntryTargets_(sh);  // 既存の月別目標(目標行)を退避→チャネル追加でも入力保持
  clearSheet_(sh); ensureGrid_(sh, 240, MS2 + nMon + 1);
  sh.setColumnWidth(1, 28); sh.setColumnWidth(2, 112); sh.setColumnWidth(3, 150); sh.setColumnWidth(4, 52); sh.setColumnWidth(5, 64);
  for (var cw = MS2; cw <= lastMonCol; cw++) sh.setColumnWidth(cw, 58);
  bandTitle_(sh, 1, 2, MS2 + nMon - 1, '■ ' + companyName_() + '　エントリー目標管理');
  var row = stepBanner_(sh, 2, '②-3 / 目標設計', 'エントリー目標管理', '媒体×月の エントリー目標 / 実績 / 達成率（実績は応募から自動集計）',
    '各媒体の「目標」行に月別エントリー目標を入力', 'STEP③ 連携設定（CSV/Slack）→ ④本番運用');
  row = inputLegend_(sh, row);

  // 有効✓チャネル(カテゴリ順)
  var typeToCat = { 'agent': 'エージェント', 'scout': 'ダイレクトリクルーティング', '媒体': '媒体', 'referral': 'リファラル', 'organic': 'その他' };
  var media = confRead_('CHAN').map(function (r) { return [typeToCat[String(r[1])] || 'その他', String(r[0])]; }).filter(function (x) { return x[1]; });
  media.sort(function (a, b) { return ENTRY_CATEGORIES.indexOf(a[0]) - ENTRY_CATEGORIES.indexOf(b[0]); });
  if (!media.length) media = [['媒体', '（媒体名を入力）']];

  // ヘッダー
  var hdrRow = row;
  var head = ['カテゴリ', '媒体名', '指標', '合計'].concat(months.map(function (m) { return m.label; }));
  // 月見出しはテキスト(@)で書く。'2026/04'が日付化するとsnapshot/実績集計の月列照合が壊れるため。
  sh.getRange(hdrRow, 2, 1, head.length).setNumberFormat('@').setValues([head]).setBackground(HEAD_BG).setFontColor(C.INK).setFontWeight('bold').setFontSize(9).setHorizontalAlignment('center');

  // レイアウト位置を先に確定(総合計が先頭・媒体行を前方参照するため)
  var byCat = {}; media.forEach(function (m) { (byCat[m[0]] = byCat[m[0]] || []).push(m[1]); });
  var cats = ENTRY_CATEGORIES.filter(function (c) { return byCat[c] && byCat[c].length; });
  var cur = hdrRow + 1;
  var totalBase = cur; cur += 3;
  var catPlan = [];                 // {cat, mediaBases:[{name,base}], subBase}
  var allMediaBases = [];
  cats.forEach(function (cat) {
    var mb = [];
    byCat[cat].forEach(function (name) { mb.push({ name: name, base: cur }); allMediaBases.push(cur); cur += 3; });
    var subBase = cur; cur += 3;
    catPlan.push({ cat: cat, mediaBases: mb, subBase: subBase });
  });
  var MET = ['目標', '実績', '達成率'];

  // 3段ブロック描画。kind='media'は月目標=入力/実績=自動。'sub'/'total'は sumBases の合算。
  function drawBlock(base, name, kind, sumBases) {
    for (var t = 0; t < 3; t++) {
      var rr = base + t;
      sh.getRange(rr, 4).setValue(MET[t]).setFontSize(9).setFontColor(t === 2 ? C.SUB : C.BLACK).setHorizontalAlignment('center').setVerticalAlignment('middle');
      // 合計列(E)
      if (t < 2) sh.getRange(rr, 5).setFormula('=SUM(' + colLetter_(MS2) + rr + ':' + colLetter_(lastMonCol) + rr + ')').setFontWeight('bold');
      else sh.getRange(rr, 5).setFormula('=IF(E' + base + '>0,E' + (base + 1) + '/E' + base + ',"")').setNumberFormat('0%').setFontWeight('bold');
      // 月列(F〜)
      for (var j = 0; j < nMon; j++) {
        var col = MS2 + j, cl = colLetter_(col), cell = sh.getRange(rr, col);
        if (t === 2) { cell.setFormula('=IF(' + cl + base + '>0,' + cl + (base + 1) + '/' + cl + base + ',"")').setNumberFormat('0%').setBackground(DESIGN_AUTO_BG).setFontColor(C.SUB); }
        else if (kind === 'media') {
          if (t === 0) { var keep = (snap[name] && snap[name][months[j].label] != null) ? snap[name][months[j].label] : 0; cell.setValue(keep).setBackground(DESIGN_INPUT_BG); }
          else cell.setValue(0).setBackground(DESIGN_AUTO_BG);   // 実績=refreshEntryActuals_で上書き
        } else {  // sub / total: 目標=媒体目標の和, 実績=媒体実績の和
          var refs = sumBases.map(function (b) { return cl + (b + t); });
          cell.setFormula(refs.length ? '=SUM(' + refs.join(',') + ')' : '0').setBackground(kind === 'total' ? '#F7E7E6' : HEAD_BG).setFontWeight('bold');
        }
      }
    }
    // 媒体名(C)=3行マージ
    var cc = sh.getRange(base, 3, 3, 1); cc.breakApart(); cc.merge();
    cc.setValue(name).setVerticalAlignment('middle').setFontWeight(kind === 'media' ? 'normal' : 'bold').setFontSize(kind === 'media' ? 10 : 10);
    if (kind === 'total') { sh.getRange(base, 2, 3, 1).breakApart(); sh.getRange(base, 2, 3, 1).merge().setValue('総合計').setVerticalAlignment('middle').setFontWeight('bold').setFontColor(C.RED).setBackground('#F7E7E6'); cc.setFontColor(C.RED); }
    sh.getRange(base, 2, 3, head.length).setBorder(true, true, true, true, false, false, C.BORDER, SpreadsheetApp.BorderStyle.SOLID);
  }

  // 総合計(全媒体の目標行/実績行を合算)
  drawBlock(totalBase, '', 'total', allMediaBases);
  // カテゴリ別
  catPlan.forEach(function (cp) {
    cp.mediaBases.forEach(function (mb) { drawBlock(mb.base, mb.name, 'media', null); });
    drawBlock(cp.subBase, '小計', 'sub', cp.mediaBases.map(function (x) { return x.base; }));
    // カテゴリ(B)=このカテゴリの全行(媒体×3＋小計×3)をマージ
    var top = cp.mediaBases[0].base, h = (cp.mediaBases.length + 1) * 3;
    var bc = sh.getRange(top, 2, h, 1); bc.breakApart(); bc.merge();
    bc.setValue(cp.cat).setVerticalAlignment('top').setFontWeight('bold').setBackground('#F7F5F4').setFontSize(9).setWrap(true);
  });

  var endRow = cur - 1;
  sh.getRange(hdrRow, 2, endRow - hdrRow + 1, head.length).setBorder(true, true, true, true, false, false, C.BORDER, SpreadsheetApp.BorderStyle.SOLID);
  // 達成率の色(全達成率行=各ブロックbase+2 を含む E〜月レンジ)
  var rateRanges = [];
  function pushRate(base) { rateRanges.push(sh.getRange(base + 2, 5, 1, 1 + nMon)); }
  pushRate(totalBase); allMediaBases.forEach(pushRate); catPlan.forEach(function (cp) { pushRate(cp.subBase); });
  sh.setConditionalFormatRules([
    SpreadsheetApp.newConditionalFormatRule().whenNumberGreaterThanOrEqualTo(1).setBackground('#D6EFD6').setFontColor('#1E6B2E').setRanges(rateRanges).build(),
    SpreadsheetApp.newConditionalFormatRule().whenNumberBetween(0.6, 0.999).setBackground('#FFF3CD').setFontColor('#8a6d00').setRanges(rateRanges).build(),
    SpreadsheetApp.newConditionalFormatRule().whenNumberLessThan(0.6).setBackground('#F8D7DA').setFontColor('#AF322C').setRanges(rateRanges).build()
  ]);
  sh.getRange(endRow + 2, 2, 1, Math.min(8, head.length)).merge().setValue('※ チャネルは 01_設定「チャネル定義」の有効✓で増減 → 🔄更新でこの表に反映（入力済みの月別目標は保持）。各媒体の「目標」行に月別エントリー目標を入力 → 🔄更新で「実績」を応募から自動集計、「達成率」=実績÷目標を自動表示（緑=達成/黄=注意/赤=未達）。')
    .setFontColor(C.SUB).setFontSize(9).setWrap(true);
  refreshEntryActuals_();
}

// 04(3段レイアウト)の各媒体「実績」行へ 10_マスタ応募(チャネル×応募月)を集計して書込み
function refreshEntryActuals_() {
  var sh = ss_().getSheetByName(SH.ENTRY); if (!sh || sh.getLastRow() < 3) return;
  var lastCol = sh.getLastColumn(), lastRow = sh.getLastRow();
  // ヘッダー行(col3='媒体名')と月列(プレーン YYYY/MM)を特定
  var hdrRow = 0;
  var scan = sh.getRange(1, 3, Math.min(lastRow, 15), 1).getValues();
  for (var s = 0; s < scan.length; s++) { if (String(scan[s][0]).trim() === '媒体名') { hdrRow = s + 1; break; } }
  if (!hdrRow) return;
  var head = sh.getRange(hdrRow, 1, 1, lastCol).getValues()[0];
  var monthCol = {}; // colIndex(1-based) -> 'YYYY-MM'
  for (var c = 1; c <= lastCol; c++) {
    var raw = head[c - 1], y = null, mo = null;
    if (raw instanceof Date) { y = raw.getFullYear(); mo = raw.getMonth() + 1; }  // 日付化した見出しも拾う
    else { var m = String(raw || '').match(/(\d{4})[\/\-](\d{1,2})/); if (m) { y = Number(m[1]); mo = Number(m[2]); } }
    if (y) monthCol[c] = y + '-' + ('0' + mo).slice(-2);
  }
  // 有効チャネル集合(総合計/小計の行を実績書込み対象から除外するため)
  var chanSet = {}; try { confRead_('CHAN').forEach(function (r) { var n = String(r[0] || '').trim(); if (n) chanSet[n] = 1; }); } catch (e) {}
  // マスタ集計: 媒体名(チャネル) × 月
  var mm = sheet_(SH.MASTER), md = mm.getDataRange().getValues(), mH = headerIndex_(md[0]);
  var agg = {};
  for (var i = 1; i < md.length; i++) {
    var ch = String(md[i][mH['チャネル']] || '').trim(); if (!ch) continue;
    var ap = md[i][mH['応募日']]; if (!(ap instanceof Date)) continue;
    var key = ap.getUTCFullYear() + '-' + ('0' + (ap.getUTCMonth() + 1)).slice(-2);
    if (!agg[ch]) agg[ch] = {}; agg[ch][key] = (agg[ch][key] || 0) + 1;
  }
  // 行走査: 「目標」行で媒体名を確定→次の「実績」行へ各月実績を書込み(合計実績=SUM式なので触らない)
  var dvals = sh.getRange(hdrRow + 1, 3, lastRow - hdrRow, 2).getValues(); // C=媒体名, D=指標
  var curMedia = null;
  for (var rIdx = 0; rIdx < dvals.length; rIdx++) {
    var rowAbs = hdrRow + 1 + rIdx;
    var cName = String(dvals[rIdx][0] || '').trim();   // C(マージ先頭=目標行に値)
    var metric = String(dvals[rIdx][1] || '').trim();  // D
    if (metric === '目標') curMedia = chanSet[cName] ? cName : null;
    else if (metric === '実績' && curMedia) {
      for (var col in monthCol) {
        var k = monthCol[col]; sh.getRange(rowAbs, Number(col)).setValue((agg[curMedia] && agg[curMedia][k]) || 0);
      }
    }
  }
}

/* ============================== 09_CSV取込 (WP4) ============================== */

function buildCsvTab_() {
  var sh = sheet_(SH.CSV);
  clearSheet_(sh);
  ensureGrid_(sh, 60, 14);
  sh.setColumnWidth(1, 28); for (var c = 2; c <= 11; c++) sh.setColumnWidth(c, 110);
  bandTitle_(sh, 1, 2, 11, '■ CSV取込（ATSのCSVをマスタへ正規化）');
  note_(sh, 3, 11, '★おすすめ＝メニュー「採用 ▸ 📥 CSVファイルを取込（推奨）」でファイルを選ぶだけ（原本保持＋自動正規化）。 ／ 以下は貼付用: ① 下のセルにCSVを貼付（1行目=ヘッダー）② 列対応は 01_設定「CSV列マッピング」③ 取込実行にチェック');
  sh.getRange(5, 2).setValue('CSV貼付↓').setFontWeight('bold').setFontColor(C.BLACK).setBackground(HEAD_BG);
  var paste = sh.getRange(6, 2, 14, 10); paste.breakApart(); paste.merge().setBackground(C.WHITE).setWrap(true).setVerticalAlignment('top')
    .setBorder(true, true, true, true, false, false, C.BORDER, SpreadsheetApp.BorderStyle.SOLID);
  sh.getRange(21, 2).setValue('取込実行 →').setFontWeight('bold').setFontColor(C.RED).setVerticalAlignment('middle');
  sh.getRange(21, 3).insertCheckboxes().setValue(false);
  sh.getRange(21, 4, 1, 6).merge().setValue('チェックで取込（新規=candidate_id採番／連絡先一致=既存を上書き更新・応募日と集計と手入力は保持・原本は最新で上書き）').setFontColor(C.SUB).setFontSize(9).setVerticalAlignment('middle');
  sh.getRange(23, 2).setValue('結果:').setFontWeight('bold');
}

// CSV貼付パス(09_)→ 取込コアへ
function importCsv() {
  var sh = sheet_(SH.CSV);
  var raw = String(sh.getRange(6, 2).getValue() || '').trim();
  if (!raw) { toast_('CSVを貼り付けてください'); return; }
  var grid;
  try { grid = Utilities.parseCsv(raw); } catch (e) { toast_('CSV解析に失敗: ' + e.message); return; }
  if (!grid || grid.length < 2) { toast_('データ行がありません'); return; }
  saveRawImport_(grid);
  var r = importCsvGrid_(grid);
  var ivr = importAtsBlocks_(r.head, r.ids || []);
  syncNextInterview(); syncInterviewSummary_(); renderAllDashboards_();
  sh.getRange(23, 3, 1, 8).merge().setValue('取込 新規' + r.added + '件 / 更新' + r.updated + '件 / 面接 ' + ivr.interviews + '行（' + Utilities.formatDate(new Date(), ss_().getSpreadsheetTimeZone(), 'HH:mm') + '）').setFontColor(C.INK);
  toast_('CSV取込: 新規' + r.added + '件 / 更新' + r.updated + '件 / 面接' + ivr.interviews + '行');
}

/* ---------- WP21: 取込コア(原本保持＋10_マスタへ汎用マッピング) ---------- */

// ヘッダー行を検出(かんりくん等は上に職種帯などの super-header がある)。
function findHeaderRow_(grid) {
  var anchors = ['ID', '氏名', '姓', '名', '現在の選考段階', 'メールアドレス', 'メール', '応募職種', '学校名', 'エントリー日', '連絡先'];
  for (var i = 0; i < Math.min(grid.length, 6); i++) {
    var hit = grid[i].map(function (s) { return String(s).trim(); }).filter(function (c) { return anchors.indexOf(c) >= 0; }).length;
    if (hit >= 2) return i;
  }
  return 0;
}
// "YYYY/MM/DD" 等を東京日付(d_)に。失敗時 null。
function parseDateLoose_(v) {
  if (v instanceof Date) return isNaN(v.getTime()) ? null : v;
  var s = String(v || '').trim(); if (!s) return null;
  var m = s.match(/(\d{4})[\/\-.](\d{1,2})[\/\-.](\d{1,2})/);
  if (m) return d_(Number(m[1]), Number(m[2]), Number(m[3]));
  var m2 = s.match(/^(\d{4})[\/\-.](\d{1,2})$/); if (m2) return d_(Number(m2[1]), Number(m2[2]), 1);
  var dd = new Date(s); return isNaN(dd.getTime()) ? null : dd;
}
// 説明会日時の解析(時刻を保持)。'2026-07-01 14:00'→時刻込みDate。同日の別時刻セッションを区別するために使う(定員カウント)。
function parseBriefDateTime_(v) {
  if (v instanceof Date) return isNaN(v.getTime()) ? null : v;
  var s = String(v || '').trim(); if (!s) return null;
  var m = s.match(/(\d{4})[\/\-.](\d{1,2})[\/\-.](\d{1,2})(?:[ 　T]+(\d{1,2})[:：](\d{2}))?/);
  if (m) return new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]), m[4] ? Number(m[4]) : 0, m[5] ? Number(m[5]) : 0);
  return parseDateLoose_(s);
}
// ATSの「現在の選考段階(【】付)」を 現ステージ + ステータス に分解
function splitAtsStage_(s) {
  var raw = String(s || '').trim();
  var stage = raw.replace(/【[^】]*】/g, '').trim();
  var status = '';
  if (/不合格|不採用|お見送り|見送り/.test(raw)) status = '見送り';
  else if (/辞退/.test(raw)) status = '辞退';
  else if (/入社/.test(raw)) status = '入社';
  else if (/承諾/.test(raw)) status = '承諾';
  else if (/内定/.test(raw)) status = '内定';
  return { stage: stage || raw, status: status };
}
// 取込元CSVを 09_取込元データ タブへ無加工保存(原本保持)
function saveRawImport_(grid) {
  var name = '09_取込元データ';
  var sh = ss_().getSheetByName(name) || ss_().insertSheet(name);
  sh.clear();
  if (grid && grid.length) {
    var w = 1; grid.forEach(function (r) { w = Math.max(w, r.length); });
    var norm = grid.map(function (r) { var x = r.slice(); while (x.length < w) x.push(''); return x; });
    ensureGrid_(sh, norm.length + 2, w + 1);
    sh.getRange(1, 1, norm.length, w).setValues(norm);
    sh.getRange(1, 1, 1, w).setFontWeight('bold').setBackground(HEAD_BG).setFontColor(C.INK);
  }
  sh.getRange(1, 1).setNote('取込元CSV(無加工) ' + Utilities.formatDate(new Date(), ss_().getSpreadsheetTimeZone(), 'yyyy-MM-dd HH:mm'));
}

// parse済2D配列 → 10_マスタへ upsert(連絡先一致は既存更新・新規は追記)。返り {added,updated,head,ids}
// 上書き対象=CSVにマップされた項目。candidate_id/応募日(初回履歴)/集計列/手入力NA等は保持。
function importCsvGrid_(grid) {
  var hr = findHeaderRow_(grid);
  var head = grid[hr].map(function (s) { return String(s).trim(); });
  var body = grid.slice(hr + 1);
  var map = {}; confRead_('CSV').forEach(function (r) { if (String(r[0]).trim()) map[String(r[0]).trim()] = String(r[1]).trim(); });
  var m = sheet_(SH.MASTER); var md = m.getDataRange().getValues(); var mH = headerIndex_(md[0]), w = MASTER_COLS.length;
  var data = md.slice(1).filter(function (r) { return String(r[mH['candidate_id']]).trim() !== ''; });  // 既存データ行
  var emailIdx = {}; data.forEach(function (r, i) { var em = String(r[mH['連絡先']] || '').trim().toLowerCase(); if (em) emailIdx[em] = i; });
  var maxId = 0; data.forEach(function (r) { var mm = String(r[mH['candidate_id']]).match(/(\d+)\s*$/); if (mm) maxId = Math.max(maxId, Number(mm[1])); });
  var stagesAll = confRead_('STAGE'), yr = nowTokyo_().getUTCFullYear();
  var dateF = { '応募日': 1, '生年月日': 1, '内定日': 1, '承諾日': 1, '入社日': 1, 'NA期限': 1, '直近面接日': 1 };
  var ids = [], added = 0, updated = 0;
  // 上書きしない列(採番/集計/分割元)。応募日は新規=CSV値/更新=保持(下で分岐)。
  var KEEP = { 'candidate_id': 1, '面接回数': 1, '直近面接日': 1, '直近面接官': 1, '直近フェーズ': 1, '総合評価': 1, '最新評価': 1, '姓': 1, '名': 1 };
  body.forEach(function (line) {
    if (!line || !line.join('').trim()) return;
    var rec = {}; head.forEach(function (h, ci) { var dst = map[h]; if (dst && (rec[dst] == null || rec[dst] === '')) rec[dst] = line[ci]; });
    if (!rec['氏名']) { var sei = String(rec['姓'] || '').trim(), mei = String(rec['名'] || '').trim(); if (sei || mei) rec['氏名'] = (sei + ' ' + mei).trim(); }
    if (rec['現ステージ']) { var sp = splitAtsStage_(rec['現ステージ']); rec['現ステージ'] = sp.stage; if (!rec['ステータス'] && sp.status) rec['ステータス'] = sp.status; }
    var email = String(rec['連絡先'] || '').trim().toLowerCase();
    function applyTo(row, isNew) {
      Object.keys(rec).forEach(function (dst) {
        if (mH[dst] == null || KEEP[dst]) return;            // 保持列は上書きしない
        if (!isNew && dst === '応募日') return;              // 更新時は応募日(初回履歴)を保持
        var v = rec[dst]; if (v == null || v === '') return;
        if (dateF[dst]) { var dd = parseDateLoose_(v); if (dd) row[mH[dst]] = dd; } else row[mH[dst]] = v;
      });
    }
    if (email && emailIdx[email] != null) {                  // 既存 → 更新(上書き)
      applyTo(data[emailIdx[email]], false);
      var er = data[emailIdx[email]];
      ids.push({ cid: String(er[mH['candidate_id']]), line: line, name: String(er[mH['氏名']] || ''), seg: String(er[mH['区分']] || ''), job: String(er[mH['職種']] || '') });
      updated++; return;
    }
    var seg = String(rec['区分'] || '新卒').trim();
    if (!rec['現ステージ']) { var st = stagesAll.filter(function (r) { return String(r[0]) === seg; }).sort(function (a, b) { return Number(a[1]) - Number(b[1]); })[0]; rec['現ステージ'] = st ? String(st[2]) : ''; }
    maxId++;
    var cid = 'C-' + yr + '-' + ('0000' + maxId).slice(-4);
    var row = new Array(w); for (var k = 0; k < w; k++) row[k] = '';
    row[mH['candidate_id']] = cid; row[mH['区分']] = seg;
    applyTo(row, true);
    if (!row[mH['応募日']]) row[mH['応募日']] = new Date();
    if (!row[mH['ステータス']]) row[mH['ステータス']] = '進行中';
    if (!row[mH['チャネル']]) row[mH['チャネル']] = 'ATS取込';
    if (email) emailIdx[email] = data.length;
    data.push(row);
    ids.push({ cid: cid, line: line, name: rec['氏名'] || '', seg: seg, job: String(rec['職種'] || '') });
    added++;
  });
  if (data.length) m.getRange(2, 1, data.length, w).setValues(data);  // 既存更新＋新規を一括書込み
  return { added: added, updated: updated, skipped: 0, head: head, ids: ids };
}

/* ---------- WP23: 横長ATSの選考ブロック → 11_面接スケジュール ---------- */

// ヘッダーから選考イベントブロックを検出([{event,phase,kind,dateCol,whoCol,evalCol,memoCol}])
function detectStageBlocks_(head) {
  var blocks = [];
  for (var i = 0; i < head.length; i++) {
    var h = String(head[i]).trim();
    if (h.length > 4 && h.slice(-4) === '・到達日') {
      var event = h.slice(0, -4);
      var phase = event.replace(/【[^】]*】/g, '').trim();
      var km = event.match(/【([^】]*)】/);
      var b = { event: event, phase: phase, kind: km ? km[1] : '', dateCol: i, whoCol: -1, evalCol: -1, memoCol: -1 };
      if (i + 1 < head.length && String(head[i + 1]).trim() === event + '・評価者') b.whoCol = i + 1;
      for (var j = (b.whoCol >= 0 ? b.whoCol + 1 : i + 1); j < head.length; j++) {
        var hj = String(head[j]).trim();
        if (hj === '総合評価' && b.evalCol < 0) b.evalCol = j;
        else if (hj === '自由記述' && b.memoCol < 0) b.memoCol = j;
        else break;
      }
      blocks.push(b);
    }
  }
  return blocks;
}
// 各候補者の選考ブロックを フェーズ単位で 11_ へ1行ずつ展開(実イベントのみ)
function importAtsBlocks_(head, ids) {
  if (!ids || !ids.length) return { interviews: 0 };
  var blocks = detectStageBlocks_(head);
  if (!blocks.length) return { interviews: 0 };
  var iv = sheet_(SH.IV); var ivData = iv.getDataRange().getValues(); var ivH = headerIndex_(ivData[0]);
  var maxIv = 0; for (var i = 1; i < ivData.length; i++) { var mm = String(ivData[i][ivH['interview_id']]).match(/(\d+)\s*$/); if (mm) maxIv = Math.max(maxIv, Number(mm[1])); }
  var yr = nowTokyo_().getUTCFullYear();
  var tz = ss_().getSpreadsheetTimeZone();
  // 再取込でも重複させない: 既存(candidate_id|ステージ|日付)を集合化し、既にある面接行はスキップ(手入力の評価/官は保持)
  function ivKey_(cid, stage, dv) { var d = (dv instanceof Date) ? dv : parseDateLoose_(dv); return String(cid) + '|' + String(stage) + '|' + (d ? Utilities.formatDate(d, tz, 'yyyy-MM-dd') : String(dv || '')); }
  var seenIv = {};
  for (var j = 1; j < ivData.length; j++) { var cidv = String(ivData[j][ivH['candidate_id']] || '').trim(); if (cidv) seenIv[ivKey_(cidv, ivData[j][ivH['ステージ']], ivData[j][ivH['予定日時']])] = 1; }
  var out = [];
  ids.forEach(function (cand) {
    var line = cand.line, phases = {};
    blocks.forEach(function (b) {
      if (b.phase === 'エントリー' || !b.phase) return;  // 応募は面接ではない
      var date = parseDateLoose_(line[b.dateCol]);
      var who = b.whoCol >= 0 ? String(line[b.whoCol] || '').trim() : '';
      var ev = b.evalCol >= 0 ? String(line[b.evalCol] || '').trim() : '';
      var memo = b.memoCol >= 0 ? String(line[b.memoCol] || '').trim() : '';
      if (!phases[b.phase]) phases[b.phase] = { attend: null, prio: 9, who: '', ev: '', memo: '', result: '' };
      var p = phases[b.phase];
      var prio = b.kind === '参加' ? 1 : b.kind === '合格' ? 2 : b.kind === '不合格' ? 3 : 9;
      if (date && prio < 9 && prio < p.prio) { p.attend = date; p.prio = prio; }
      if (date && b.kind === '合格') p.result = '通過';
      if (date && b.kind === '不合格') p.result = '見送り';
      if (date && b.kind === '辞退') p.result = '辞退';
      if (who && !p.who) p.who = who;
      if (ev && !p.ev) p.ev = ev;
      if (memo && !p.memo) p.memo = memo;
    });
    Object.keys(phases).forEach(function (phase) {
      var p = phases[phase]; if (!p.attend) return;
      var key = ivKey_(cand.cid, phase, p.attend); if (seenIv[key]) return; seenIv[key] = 1;  // 既存面接行はスキップ(再取込で重複防止)
      maxIv++;
      var row = new Array(IV_COLS.length); for (var k = 0; k < row.length; k++) row[k] = '';
      row[ivH['interview_id']] = 'IV-' + yr + '-' + ('0000' + maxIv).slice(-4);
      row[ivH['candidate_id']] = cand.cid;
      row[ivH['候補者名']] = cand.name;
      row[ivH['区分']] = cand.seg;
      row[ivH['職種']] = cand.job;
      row[ivH['ステージ']] = phase;
      row[ivH['予定日時']] = p.attend;
      row[ivH['面接官']] = p.who;
      row[ivH['ステータス']] = '実施済';
      row[ivH['結果']] = p.result || '';
      if (/^[SABCD]$/.test(p.ev)) row[ivH['評点']] = p.ev;
      row[ivH['評価メモ']] = p.memo;
      out.push(row);
    });
  });
  if (out.length) iv.getRange(iv.getLastRow() + 1, 1, out.length, IV_COLS.length).setValues(out);
  return { interviews: out.length };
}

/* ---------- WP22: ファイル選択ダイアログ(Shift_JIS対応) ---------- */

function showCsvImportDialog() {
  SpreadsheetApp.getUi().showModalDialog(HtmlService.createHtmlOutput(csvDialogHtml_()).setWidth(500).setHeight(460), 'CSVファイル取込');
}
// 文字コード復号 → parseCsv
function decodeCsv_(b64, charset) {
  var bytes = Utilities.base64Decode(b64);
  var text = Utilities.newBlob(bytes).getDataAsString(charset || 'UTF-8');
  return Utilities.parseCsv(text);
}
// google.script.run から呼ぶ(末尾 _ なし)
function previewUploadedCsv(b64, charset) {
  try {
    var grid = decodeCsv_(b64, charset);
    if (!grid || grid.length < 2) return { ok: false, msg: 'データ行がありません' };
    var hr = findHeaderRow_(grid);
    var head = grid[hr].map(function (s) { return String(s).trim(); });
    var map = {}; confRead_('CSV').forEach(function (r) { if (String(r[0]).trim()) map[String(r[0]).trim()] = String(r[1]).trim(); });
    var mapped = [], unmapped = 0;
    head.forEach(function (h) { if (map[h]) mapped.push(h + '→' + map[h]); else if (h) unmapped++; });
    var ph = {}; detectStageBlocks_(head).forEach(function (b) { if (b.phase && b.phase !== 'エントリー') ph[b.phase] = 1; });
    return { ok: true, rows: grid.length - 1 - hr, headers: head.length, mapped: mapped, unmapped: unmapped, phases: Object.keys(ph) };
  } catch (e) { return { ok: false, msg: String(e && e.message || e) }; }
}
function importUploadedCsv(b64, charset) {
  try {
    var grid = decodeCsv_(b64, charset);
    if (!grid || grid.length < 2) return { ok: false, msg: 'データ行がありません' };
    saveRawImport_(grid);
    var r = importCsvGrid_(grid);
    var ivr = importAtsBlocks_(r.head, r.ids || []);
    syncNextInterview(); syncInterviewSummary_(); renderAllDashboards_();
    return { ok: true, added: r.added, updated: r.updated, interviews: ivr.interviews };
  } catch (e) { return { ok: false, msg: String(e && e.message || e) }; }
}
// ダイアログHTML(ブランド配色)
function csvDialogHtml_() {
  return '' +
'<!DOCTYPE html><html><head><meta charset="utf-8"><base target="_top">' +
'<style>' +
'body{font-family:"Helvetica Neue",Arial,sans-serif;color:#1A1A1A;margin:0;padding:16px;font-size:13px;}' +
'.bar{background:#AF322C;color:#fff;padding:10px 14px;margin:-16px -16px 14px;font-weight:bold;font-size:14px;}' +
'.row{margin:10px 0;}label{font-weight:bold;display:block;margin-bottom:4px;}' +
'input[type=file]{width:100%;}select{padding:4px;}' +
'.btn{background:#AF322C;color:#fff;border:none;padding:9px 16px;border-radius:4px;font-weight:bold;cursor:pointer;margin-right:8px;}' +
'.btn.sub{background:#fff;color:#AF322C;border:1px solid #AF322C;}' +
'#st{margin-top:14px;padding:10px;background:#F7F5F4;border:1px solid #D9D9D9;border-radius:4px;min-height:48px;font-size:12px;line-height:1.5;}' +
'small{color:#6B6B6B;}' +
'</style></head><body>' +
'<div class="bar">📥 CSVファイル取込</div>' +
'<div class="row"><label>① CSVファイルを選択</label><input type="file" id="f" accept=".csv,text/csv"></div>' +
'<div class="row"><label>② 文字コード</label><select id="cs"><option value="Shift_JIS">Shift_JIS（かんりくん等・日本語ATS）</option><option value="UTF-8">UTF-8</option></select> <small>文字化けする場合は切替</small></div>' +
'<div class="row"><button class="btn sub" onclick="doPreview()">プレビュー</button><button class="btn" onclick="doImport()">取り込む</button></div>' +
'<div id="st">CSVを選んで「プレビュー」で内容確認 → 「取り込む」。原本は「09_取込元データ」に保存されます。</div>' +
'<script>' +
'function rf(cb){var f=document.getElementById("f").files[0];if(!f){alert("CSVファイルを選択してください");return;}var r=new FileReader();r.onload=function(){var b=new Uint8Array(r.result),s="";for(var i=0;i<b.length;i++)s+=String.fromCharCode(b[i]);cb(btoa(s));};r.readAsArrayBuffer(f);}' +
'function cs(){return document.getElementById("cs").value;}' +
'function setS(h){document.getElementById("st").innerHTML=h;}' +
'function doPreview(){rf(function(b64){setS("解析中…");google.script.run.withSuccessHandler(function(res){if(!res.ok){setS("⚠ "+res.msg);return;}setS("検出: "+res.headers+"列 / "+res.rows+"行<br>マッピング済 "+res.mapped.length+"項目 ／ 未マップ "+res.unmapped+"<br>選考フェーズ: "+(res.phases.join(" / ")||"なし")+"<br><small>"+res.mapped.join("、")+"</small>");}).withFailureHandler(function(e){setS("⚠ "+e.message);}).previewUploadedCsv(b64,cs());});}' +
'function doImport(){if(!confirm("マスタへ取り込みます。よろしいですか？"))return;rf(function(b64){setS("取込中…（少々お待ちください）");google.script.run.withSuccessHandler(function(res){if(!res.ok){setS("⚠ "+res.msg);return;}setS("✅ 取込完了<br>新規 "+res.added+"件 ／ 既存更新 "+res.updated+"件<br>面接スケジュール展開 "+res.interviews+"行<br><small>同じ連絡先は上書き更新。原本は「09_取込元データ」に最新で保存。閉じてOK。</small>");}).withFailureHandler(function(e){setS("⚠ "+e.message);}).importUploadedCsv(b64,cs());});}' +
'</script></body></html>';
}

/* ============================== 応募フォーム(設定駆動・区分別) ============================== */

// 有効なフォーム項目 → [{name,type,required,target,source}]
function formFields_() {
  return confRead_('FORMFIELDS').filter(function (r) { return confTrue_(r[5]) && String(r[0]).trim(); })
    .map(function (r) {
      return { name: String(r[0]).trim(), type: String(r[1]).trim() || '短文', required: confTrue_(r[2]),
        target: String(r[3]).trim() || '全', source: String(r[4]).trim() || '自由', choices: parseChoices_(r[6]) };
    });
}
// カスタム選択肢文字列(改行/カンマ/読点区切り)→配列。空なら[]。
function parseChoices_(s) {
  return String(s == null ? '' : s).split(/[\n,、，]+/).map(function (x) { return x.trim(); }).filter(Boolean);
}
// 選択ListItemに選択肢を安全にセット(空ならプレースホルダ＝Forms仕様の最低1選択肢を満たし破綻を防ぐ)。
function setChoicesSafe_(item, choices) {
  item.setChoiceValues((choices && choices.length) ? choices : ['（選択肢未設定）']);
  return item;
}
// 生成フォームの公開URLをProperties(formUrls)へ蓄積→01_設定に配布用リンクを描画。
function saveFormUrls_(obj) {
  var props = PropertiesService.getDocumentProperties(), cur = {};
  try { cur = JSON.parse(props.getProperty('formUrls') || '{}'); } catch (e) {}
  for (var k in obj) { if (obj[k]) cur[k] = obj[k]; }
  props.setProperty('formUrls', JSON.stringify(cur));
  try { renderFormUrls_(); } catch (e) { Logger.log('renderFormUrls_ error: ' + e); }
}
// 01_設定 のFORMFIELDS帯の下(行210〜・cols2-7)に「生成フォームURL（配布用）」をHYPERLINKで表示。Propertiesが正。
function renderFormUrls_() {
  var sh = ss_().getSheetByName(SH.CONF); if (!sh) return;
  var urls = {}; try { urls = JSON.parse(PropertiesService.getDocumentProperties().getProperty('formUrls') || '{}'); } catch (e) { return; }
  var keys = Object.keys(urls), r0 = 210, maxRows = 6;
  sh.getRange(r0, 2, maxRows + 1, 6).breakApart().clearContent().setBorder(false, false, false, false, false, false);
  if (!keys.length) return;
  sh.getRange(r0, 2, 1, 6).merge().setValue('■ 生成フォームURL（配布用・最新）').setBackground(C.WHITE).setFontColor(C.BLACK).setFontWeight('bold').setFontSize(10).setBorder(null, null, true, null, null, null, '#3A3A3A', SpreadsheetApp.BorderStyle.SOLID);
  keys.slice(0, maxRows).forEach(function (k, i) {
    var rr = r0 + 1 + i, u = String(urls[k] || '');
    sh.getRange(rr, 2).setValue(k).setFontWeight('bold').setFontSize(9);
    sh.getRange(rr, 3, 1, 4).merge().setFormula('=HYPERLINK("' + u.replace(/"/g, '') + '","' + u.replace(/"/g, '') + '")').setFontSize(9);
  });
  sh.getRange(r0, 2, Math.min(keys.length, maxRows) + 1, 6).setBorder(true, true, true, true, true, true, C.BORDER, SpreadsheetApp.BorderStyle.SOLID);
}
// 説明会日程ごとの定員・現登録数・残枠。定員(BRIEF 4列目)空/0=無制限。
// 登録数=11_面接スケジュールの ステージに"説明会"を含む × 予定日時一致(ステータス=キャンセル待ち/キャンセルは除外)。
function briefingCapacity_() {
  var brief = confRead_('BRIEF').filter(function (r) {
    var d = String(r[0] || '').trim(); return d && d.indexOf('(例)') < 0 && d.indexOf('（例') < 0;
  });
  var counts = {};
  try {
    var iv = ss_().getSheetByName(SH.IV);
    if (iv && iv.getLastRow() >= 2) {
      var d = iv.getDataRange().getValues(), H = headerIndex_(d[0]);
      for (var i = 1; i < d.length; i++) {
        if (String(d[i][H['ステージ']] || '').indexOf('説明会') < 0) continue;
        var st = String(d[i][H['ステータス']] || ''); if (st === 'キャンセル待ち' || st === 'キャンセル') continue;
        var dt = d[i][H['予定日時']]; if (!(dt instanceof Date)) continue;
        var k = dt.getTime(); counts[k] = (counts[k] || 0) + 1;
      }
    }
  } catch (e) {}
  return brief.map(function (r) {
    var date = String(r[0]).trim(), cap = parseInt(r[3], 10), hasCap = !isNaN(cap) && cap > 0;
    var dt = parseBriefDateTime_(date), key = dt ? dt.getTime() : null;
    var cnt = (key != null && counts[key]) ? counts[key] : 0;
    return { date: date, label: String(r[2] || ''), cap: hasCap ? cap : null, count: cnt, remaining: hasCap ? (cap - cnt) : null, full: hasCap && cnt >= cap };
  });
}
// 説明会日程の選択肢(満席=除外・定員空は無制限で常に出す)。フォームの選択肢ソース。
function briefingChoices_() {
  return briefingCapacity_().filter(function (c) { return !c.full; }).map(function (c) { return c.date; });
}
// フォームの「説明会日程」選択肢を残枠ある日程に再セット(満席を自動クローズ)。全満席なら「満席（受付終了）」1択。
function syncBriefingFormChoices_(form) {
  if (!form) return;
  var avail = briefingChoices_();
  form.getItems(FormApp.ItemType.LIST).forEach(function (it) {
    if (String(it.getTitle()).trim() !== '説明会日程') return;
    try { it.asListItem().setChoiceValues(avail.length ? avail : ['満席（受付終了）']); } catch (e) { Logger.log('syncBriefingFormChoices_ 失敗(満席が閉じない恐れ): ' + e); }
  });
}
// 選択肢ソース → 配列(職種は区分でフィルタ)
function fieldChoices_(source, seg) {
  if (source === '職種') return confRead_('JOB').filter(function (r) { return !seg || String(r[1]) === seg || String(r[1]) === '全'; }).map(function (r) { return String(r[0]); }).filter(Boolean);
  if (source === 'チャネル') return confRead_('CHAN').map(function (r) { return String(r[0]); }).filter(Boolean);
  if (source === '性別') return GENDERS.slice();
  if (source === '説明会日程') return briefingChoices_();
  return [];
}

// 区分別にGoogleフォームを生成/更新(設定駆動)。メニューから実行。
function createEntryForms() {
  if (!requireCompany_('応募フォーム生成')) return;
  var props = PropertiesService.getDocumentProperties();
  var map = {}; try { map = JSON.parse(props.getProperty('formIds') || '{}'); } catch (e) { map = {}; }
  var fields = formFields_(), cn = companyName_(), made = [], urls = {};
  enabledSegments_().forEach(function (seg) {
    var form = null;
    if (map[seg]) { try { form = FormApp.openById(map[seg]); } catch (e) { form = null; } }
    if (!form) { form = FormApp.create(cn + ' ' + seg + ' エントリーフォーム'); map[seg] = form.getId(); }
    form.setTitle(cn + ' ' + seg + ' エントリーフォーム').setDescription('ご応募ありがとうございます。以下をご入力ください。');
    form.getItems().forEach(function (it) { form.deleteItem(it); });  // 再生成(設定の最新を反映)
    fields.filter(function (f) { return f.target === '全' || f.target === seg; }).forEach(function (f) {
      var item;
      if (f.type === '選択') {
        item = form.addListItem().setTitle(f.name);
        var ch = (f.choices && f.choices.length) ? f.choices : fieldChoices_(f.source, seg);  // カスタム選択肢優先→ソース→空はプレースホルダ
        setChoicesSafe_(item, ch);
      } else if (f.type === '長文') item = form.addParagraphTextItem().setTitle(f.name);
      else if (f.type === '日付') item = form.addDateItem().setTitle(f.name);
      else item = form.addTextItem().setTitle(f.name);  // 短文/数値
      if (item.setRequired) item.setRequired(!!f.required);
    });
    // 区分固有の取得項目(❿)もフォームで収集 → onFormSubmitで②進捗管理へ連動
    segFields_(seg).forEach(function (fn) { form.addTextItem().setTitle(fn); });
    ensureFormTrigger_(form);
    var u = form.getPublishedUrl(); made.push(seg + ': ' + u); urls['エントリー(' + seg + ')'] = u;
  });
  props.setProperty('formIds', JSON.stringify(map));
  saveFormUrls_(urls);  // 01_設定に配布用URLを表示
  ss_().toast('エントリーフォームを生成しました（URLは01_設定下部「生成フォームURL」に表示）', 'フォーム', 8);
  Logger.log('フォームURL:\n' + made.join('\n'));
}
function ensureFormTrigger_(form) {
  var fid = form.getId();
  var has = ScriptApp.getProjectTriggers().some(function (t) {
    return t.getHandlerFunction() === 'onFormSubmit' && t.getTriggerSourceId && t.getTriggerSourceId() === fid;
  });
  if (!has) ScriptApp.newTrigger('onFormSubmit').forForm(form).onFormSubmit().create();
}

// 1候補をマスタへ追記(連絡先重複はスキップ=既存cid返す)。candidate_id採番・現ステージ既定。
function appendCandidate_(rec) {
  var m = sheet_(SH.MASTER), md = m.getDataRange().getValues(), mH = headerIndex_(md[0]);
  var email = String(rec['連絡先'] || '').trim().toLowerCase();
  if (email) { for (var i = 1; i < md.length; i++) { if (String(md[i][mH['連絡先']] || '').trim().toLowerCase() === email) return String(md[i][mH['candidate_id']] || ''); } }
  var maxId = 0; for (var j = 1; j < md.length; j++) { var mm = String(md[j][mH['candidate_id']]).match(/(\d+)\s*$/); if (mm) maxId = Math.max(maxId, Number(mm[1])); }
  var yr = nowTokyo_().getUTCFullYear();
  var cid = 'C-' + yr + '-' + ('0000' + (maxId + 1)).slice(-4);
  var seg = String(rec['区分'] || '新卒').trim();
  if (!rec['現ステージ']) { var st = confRead_('STAGE').filter(function (r) { return String(r[0]) === seg; }).sort(function (a, b) { return Number(a[1]) - Number(b[1]); })[0]; rec['現ステージ'] = st ? String(st[2]) : ''; }
  var row = new Array(MASTER_COLS.length); for (var k = 0; k < row.length; k++) row[k] = '';
  row[mH['candidate_id']] = cid;
  var dateF = { '応募日': 1, '生年月日': 1 };
  Object.keys(rec).forEach(function (dst) {
    if (mH[dst] == null || dst === 'candidate_id') return;
    var v = rec[dst]; if (v == null || v === '') return;
    if (dateF[dst] && !(v instanceof Date)) { var dd = parseDateLoose_(v); row[mH[dst]] = dd || v; } else row[mH[dst]] = v;
  });
  if (!row[mH['応募日']]) row[mH['応募日']] = new Date();
  if (!row[mH['ステータス']]) row[mH['ステータス']] = '進行中';
  if (!row[mH['チャネル']]) row[mH['チャネル']] = 'フォーム';
  m.getRange(m.getLastRow() + 1, 1, 1, MASTER_COLS.length).setValues([row]);
  return cid;
}
// 説明会日程の回答 → 11_面接スケジュールに「説明会」イベント行を作成(リマインド対象になる)
function addBriefingEvent_(cid, rec, when, seg, waitlist) {
  var dt = parseBriefDateTime_(when); if (!dt) return;
  var iv = sheet_(SH.IV), ivd = iv.getDataRange().getValues(), ivH = headerIndex_(ivd[0]);
  // 二重予約ガード: 同候補×同日時×説明会が既にあれば追加しない(フォーム重複送信で定員を不当圧迫しない)
  for (var g = 1; g < ivd.length; g++) {
    if (String(ivd[g][ivH['candidate_id']] || '').trim() !== cid) continue;
    if (String(ivd[g][ivH['ステージ']] || '').indexOf('説明会') < 0) continue;
    var ed = ivd[g][ivH['予定日時']];
    if (ed instanceof Date && Math.abs(ed.getTime() - dt.getTime()) < 60000) return;  // 同一セッション=スキップ
  }
  var maxIv = 0; for (var j = 1; j < ivd.length; j++) { var mm = String(ivd[j][ivH['interview_id']]).match(/(\d+)\s*$/); if (mm) maxIv = Math.max(maxIv, Number(mm[1])); }
  var arr = new Array(IV_COLS.length); for (var k = 0; k < arr.length; k++) arr[k] = '';
  arr[ivH['interview_id']] = 'IV-' + ('0000' + (maxIv + 1)).slice(-4);
  arr[ivH['candidate_id']] = cid; arr[ivH['候補者名']] = rec['氏名'] || ''; arr[ivH['区分']] = seg; arr[ivH['職種']] = rec['職種'] || '';
  arr[ivH['ステージ']] = '説明会'; arr[ivH['予定日時']] = dt; arr[ivH['ステータス']] = waitlist ? 'キャンセル待ち' : '予定';  // 満席超過分はキャンセル待ち(定員カウント外)
  iv.getRange(iv.getLastRow() + 1, 1, 1, arr.length).setValues([arr]);
}

// フォーム送信トリガー: 回答→マスタ追記(＋説明会日程→11_イベント)
function onFormSubmit(e) {
  try {
    if (!e || !e.source || !e.response) return;
    var fid = e.source.getId();
    var props = PropertiesService.getDocumentProperties();
    if (String(props.getProperty('surveyFormId') || '') === fid) { recordSurveyResponse_(e); return; }  // 参加後アンケート
    var smap = {}; try { smap = JSON.parse(props.getProperty('stageSurveyForms') || '{}'); } catch (er) {}
    for (var st in smap) { if (smap[st] === fid) { recordStageSurvey_(e, st); return; } }  // 段階別アンケート
    var map = {}; try { map = JSON.parse(props.getProperty('formIds') || '{}'); } catch (er) {}
    var seg = ''; for (var s in map) { if (map[s] === fid) { seg = s; break; } }
    var rec = { 区分: seg || '新卒', 応募日: new Date(), ステータス: '進行中' }, brief = '';
    var segSet = {}; segFields_(seg || '新卒').forEach(function (fn) { segSet[fn] = 1; });  // 区分固有の取得項目
    var stash = {};
    e.response.getItemResponses().forEach(function (ir) {
      var title = String(ir.getItem().getTitle()).trim();
      var val = ir.getResponse();
      if (title === '説明会日程') { brief = String(val || ''); return; }
      if (segSet[title]) { if (val != null && val !== '') stash[title] = val; return; }  // ②固有項目はstash経由で②へ
      var col = FORMFIELD_ALIAS[title] || title;
      if (col === '氏名' || col === '連絡先' || col === '電話番号' || col === '職種' || col === '性別' || col === '大学' || col === '学部' || col === '学科' || col === '高校名' || col === 'チャネル') rec[col] = val;
    });
    if (!rec['チャネル']) rec['チャネル'] = 'フォーム(' + (seg || '') + ')';
    var cid = appendCandidate_(rec);
    if (cid && brief) {
      var capRow = briefingCapacity_().filter(function (c) { return c.date === brief; })[0];  // 満席にレースで滑り込んだ場合はキャンセル待ち
      addBriefingEvent_(cid, rec, brief, seg || rec['区分'], !!(capRow && capRow.full));
      try { syncBriefingFormChoices_(e.source); } catch (er) {}  // 送信後に満席日程をフォームから自動クローズ
    }
    // 区分固有の取得項目を候補者IDでstash → 次の🔄でbuildSegManage_が②へ反映
    if (cid && Object.keys(stash).length) {
      var sj = {}; try { sj = JSON.parse(props.getProperty('segStash') || '{}'); } catch (e) {}
      sj[cid] = stash; props.setProperty('segStash', JSON.stringify(sj));
    }
  } catch (err) { Logger.log('onFormSubmit error: ' + err); }
}

/* ============================== 説明会テキストワーク＋参加後アンケート ============================== */

// 説明会・アンケート設定 → {briefWork, surveyOn, items:[{name,type,required}]}
function surveyConfig_() {
  var sh = sheet_(SH.CONF), L = CONF_LAYOUT.SURVEY;
  var items = confRead_('SURVEY').filter(function (r) { return confTrue_(r[3]) && String(r[0]).trim(); })
    .map(function (r) { return { name: String(r[0]).trim(), type: String(r[1]).trim() || '短文', required: confTrue_(r[2]) }; });
  return {
    briefWork: confTrue_(sh.getRange(L.briefWorkCell[0], L.briefWorkCell[1]).getValue()),
    surveyOn: confTrue_(sh.getRange(L.surveyOnCell[0], L.surveyOnCell[1]).getValue()),
    items: items
  };
}

var BRIEFWORK_COLS = ['候補者ID', '氏名', '大学', '学部', '説明会日時', '参加状況', 'アンケート回答', '満足度', '志望度', '所感メモ', 'ネクストアクション', '次選考へ'];
var BRIEFWORK_MANUAL = { '参加状況': 1, '所感メモ': 1, 'ネクストアクション': 1, '次選考へ': 1 };  // 手入力=保持

// 08_説明会テキストワーク: 11_の説明会イベント参加者をバイネーム一覧。継続運用=差分追記・手入力保持。設定ONのときのみ。
function buildBriefingWork_() {
  var cfg = surveyConfig_();
  var existSh = ss_().getSheetByName(SH.BRIEFWORK);
  if (!cfg.briefWork) return;  // OFFなら何もしない(既存タブも触らない)
  var sh = sheet_(SH.BRIEFWORK);
  // 既存の手入力＋アンケート結果を候補者IDで退避
  var keep = {};
  if (existSh && sh.getLastRow() > 1) {
    var od = sh.getDataRange().getValues(), oH = headerIndex_(od[0]);
    for (var i = 1; i < od.length; i++) {
      var cid = String(od[i][oH['候補者ID']] || '').trim(); if (!cid) continue;
      keep[cid] = { 参加状況: od[i][oH['参加状況']], 'アンケート回答': od[i][oH['アンケート回答']], 満足度: od[i][oH['満足度']], 志望度: od[i][oH['志望度']], 所感メモ: od[i][oH['所感メモ']], ネクストアクション: od[i][oH['ネクストアクション']], '次選考へ': od[i][oH['次選考へ']] };
    }
  }
  // 11_の説明会イベント × マスタ(大学/学部)
  var iv = sheet_(SH.IV), ivd = iv.getDataRange().getValues(), ivH = headerIndex_(ivd[0]);
  var m = sheet_(SH.MASTER), md = m.getDataRange().getValues(), mH = headerIndex_(md[0]);
  var mInfo = {}; for (var j = 1; j < md.length; j++) { var c = String(md[j][mH['candidate_id']] || '').trim(); if (c) mInfo[c] = { 大学: md[j][mH['大学']], 学部: md[j][mH['学部']], 氏名: md[j][mH['氏名']] }; }
  var rows = [], seenCid = {};
  for (var k = 1; k < ivd.length; k++) {
    if (String(ivd[k][ivH['ステージ']] || '').indexOf('説明会') < 0) continue;
    var cid2 = String(ivd[k][ivH['candidate_id']] || '').trim(); if (!cid2 || seenCid[cid2]) continue;
    seenCid[cid2] = true;
    var info = mInfo[cid2] || {}, kp = keep[cid2] || {};
    var dt = ivd[k][ivH['予定日時']];
    rows.push([
      cid2, info.氏名 || ivd[k][ivH['候補者名']] || '', info.大学 || '', info.学部 || '',
      (dt instanceof Date) ? fmtDT_(dt) : '',
      kp.参加状況 || '', kp['アンケート回答'] || '', kp.満足度 || '', kp.志望度 || '',
      kp.所感メモ || '', kp.ネクストアクション || '', kp['次選考へ'] || ''
    ]);
  }
  // 描画(ブランド・ゼブラは予約行最下部まで)
  clearSheet_(sh);
  var N = Math.max(rows.length + 30, 60);  // 余白込み予約行(候補者増でも整う)
  ensureGrid_(sh, N + 3, BRIEFWORK_COLS.length + 1);
  bandTitle_(sh, 1, 2, BRIEFWORK_COLS.length + 1, '■ ' + companyName_() + '　説明会テキストワーク（新卒・参加者バイネーム管理）');
  sh.getRange(2, 2, 1, BRIEFWORK_COLS.length).setValues([BRIEFWORK_COLS]).setBackground(HEAD_BG).setFontColor(C.INK).setFontWeight('bold').setFontSize(10).setHorizontalAlignment('center');
  var dataTop = 3;
  if (rows.length) sh.getRange(dataTop, 2, rows.length, BRIEFWORK_COLS.length).setValues(rows).setFontSize(10).setVerticalAlignment('middle').setWrap(true);
  // ゼブラ・罫線を予約行(N)まで拡張
  var bgs = [];
  for (var z = 0; z < N; z++) { var line = []; for (var w = 0; w < BRIEFWORK_COLS.length; w++) line.push(z % 2 ? C.ZEBRA : C.WHITE); bgs.push(line); }
  sh.getRange(dataTop, 2, N, BRIEFWORK_COLS.length).setBackgrounds(bgs);
  // 手入力列を薄ピンクで明示
  ['参加状況', '所感メモ', 'ネクストアクション', '次選考へ'].forEach(function (cn2) { var idx = BRIEFWORK_COLS.indexOf(cn2); if (idx >= 0) sh.getRange(dataTop, 2 + idx, N, 1).setBackground(DESIGN_INPUT_BG); });
  sh.getRange(2, 2, N + 1, BRIEFWORK_COLS.length).setBorder(true, true, true, true, true, true, C.BORDER, SpreadsheetApp.BorderStyle.SOLID);
  var W2 = [30, 100, 90, 110, 110, 130, 80, 90, 80, 80, 200, 200, 70];
  for (var ci = 0; ci < W2.length; ci++) sh.setColumnWidth(ci + 1, W2[ci]);
  note_(sh, dataTop + N + 1, 11, '新卒フォームで説明会日程を選んだ応募者が自動で並びます（継続更新・手入力は保持）。参加状況/所感/ネクストアクション/次選考へ=手入力。アンケート回答/満足度/志望度=参加後アンケートから自動。');
}

// 参加後アンケートのGoogleフォーム生成(設定項目から・surveyOn時)
function createSurveyForm() {
  if (!requireCompany_('参加後アンケート生成')) return;
  var cfg = surveyConfig_();
  if (!cfg.items.length) { toast_('アンケート項目が未設定（01_設定 ❾）'); return; }
  var props = PropertiesService.getDocumentProperties(), cn = companyName_();
  var form = null, ex = String(props.getProperty('surveyFormId') || '').trim();
  if (ex) { try { form = FormApp.openById(ex); } catch (e) { form = null; } }
  if (!form) { form = FormApp.create(cn + ' 説明会 参加後アンケート'); props.setProperty('surveyFormId', form.getId()); }
  form.setTitle(cn + ' 説明会 参加後アンケート').setDescription('説明会へのご参加ありがとうございました。アンケートにご協力ください。');
  form.getItems().forEach(function (it) { form.deleteItem(it); });
  cfg.items.forEach(function (f) {
    var item;
    if (f.type === '選択') {
      item = form.addListItem().setTitle(f.name);
      if (f.name.indexOf('5段階') >= 0) item.setChoiceValues(SURVEY_SCALE5);
      else if (f.name.indexOf('参加希望') >= 0) item.setChoiceValues(['ぜひ参加したい', '前向きに検討', '検討中', '今回は見送り']);
      else setChoicesSafe_(item, []);  // 選択肢不明はプレースホルダで破綻防止
    } else if (f.type === '長文') item = form.addParagraphTextItem().setTitle(f.name);
    else if (f.type === '日付') item = form.addDateItem().setTitle(f.name);
    else item = form.addTextItem().setTitle(f.name);
    if (item.setRequired) item.setRequired(!!f.required);
  });
  ensureFormTrigger_(form);
  saveFormUrls_({ '参加後アンケート': form.getPublishedUrl() });
  ss_().toast('参加後アンケートを生成しました（URLは01_設定下部「生成フォームURL」に表示）', 'アンケート', 8);
  Logger.log('アンケートURL: ' + form.getPublishedUrl());
}

// アンケート回答 → 新卒②(新卒_進捗管理)の該当候補者(メール一致)へ 説明会参加状況/満足度/志望度 を記録
function recordSurveyResponse_(e) {
  var sh = ss_().getSheetByName(manageName_('新卒')); if (!sh || sh.getLastRow() < 3) return;
  var email = '', sat = '', asp = '';
  e.response.getItemResponses().forEach(function (ir) {
    var t = String(ir.getItem().getTitle()), v = String(ir.getResponse() || '');
    if (/メール|mail/i.test(t)) email = v.trim().toLowerCase();
    else if (t.indexOf('満足') >= 0) sat = v;
    else if (t.indexOf('志望') >= 0) asp = v;
  });
  if (!email) return;
  var m = sheet_(SH.MASTER), md = m.getDataRange().getValues(), mH = headerIndex_(md[0]), cid = '';
  for (var j = 1; j < md.length; j++) { if (String(md[j][mH['連絡先']] || '').trim().toLowerCase() === email) { cid = String(md[j][mH['candidate_id']]); break; } }
  if (!cid) return;
  var lc = sh.getLastColumn(), hdr = sh.getRange(2, 1, 1, lc).getValues()[0], oH = {}; hdr.forEach(function (h, i) { oH[String(h)] = i + 1; });
  if (oH['候補者ID'] == null) return;
  var last = sh.getLastRow();
  for (var i = 3; i <= last; i++) {
    if (String(sh.getRange(i, oH['候補者ID']).getValue() || '').trim() === cid) {
      if (oH['説明会参加状況']) sh.getRange(i, oH['説明会参加状況']).setValue('回答済');
      if (sat && oH['アンケート満足度']) sh.getRange(i, oH['アンケート満足度']).setValue(sat);
      if (asp && oH['志望度']) sh.getRange(i, oH['志望度']).setValue(asp);
      break;
    }
  }
}

/* ============================== 段階別アンケート（候補者の評価/志望度を選考段階ごとに回収） ============================== */
// 13_段階別アンケート設定: 段階×項目を設定。既存の手入力は保持し、空なら既定をシード。
function buildSurveyConfigTab_() {
  var sh = sheet_(SH.SURVEYCFG);
  var existing = [];
  if (sh.getLastRow() > 2) {
    sh.getRange(3, 2, sh.getLastRow() - 2, SURVEYCFG_COLS.length).getValues().forEach(function (r) {
      if (String(r[0]).trim() || String(r[1]).trim()) existing.push(r.slice(0, SURVEYCFG_COLS.length));
    });
  }
  var rows = existing.length ? existing : SURVEY_STAGE_DEFAULT.map(function (d) { return d.slice(); });
  clearSheet_(sh);
  var N = Math.max(rows.length + 20, 40);
  ensureGrid_(sh, N + 5, SURVEYCFG_COLS.length + 2);
  bandTitle_(sh, 1, 2, SURVEYCFG_COLS.length + 1, '■ ' + companyName_() + '　アンケート/フォーム設定（フォーム名ごとに1つGoogleフォームHTMLを生成・任意の名前でいくつでも）');
  sh.getRange(2, 2, 1, SURVEYCFG_COLS.length).setValues([SURVEYCFG_COLS]).setBackground(HEAD_BG).setFontColor(C.INK).setFontWeight('bold').setFontSize(10).setHorizontalAlignment('center');
  if (rows.length) {
    var norm = rows.map(function (r) { var x = r.slice(0, SURVEYCFG_COLS.length); while (x.length < SURVEYCFG_COLS.length) x.push(''); return x; });
    sh.getRange(3, 2, norm.length, SURVEYCFG_COLS.length).setValues(norm).setFontSize(10).setVerticalAlignment('middle').setWrap(true);
  }
  var bgs = []; for (var z = 0; z < N; z++) { var ln = []; for (var w = 0; w < SURVEYCFG_COLS.length; w++) ln.push(z % 2 ? C.ZEBRA : C.WHITE); bgs.push(ln); }
  sh.getRange(3, 2, N, SURVEYCFG_COLS.length).setBackgrounds(bgs);
  sh.getRange(3, 2, N, 3).setBackground(DESIGN_INPUT_BG);  // 対象段階/項目名/タイプ=入力
  sh.getRange(3, 7, N, 1).setBackground(DESIGN_INPUT_BG);  // 選択肢=入力(選択型用)
  sh.getRange(2, 2, N + 1, SURVEYCFG_COLS.length).setBorder(true, true, true, true, true, true, C.BORDER, SpreadsheetApp.BorderStyle.SOLID);
  sh.getRange(3, 2, N, 1).clearDataValidations();  // フォーム名=フリーテキスト(任意の名前。選考段階名にすると進捗管理の満足度/志望度に紐づく)
  sh.getRange(3, 4, N, 1).setDataValidation(SpreadsheetApp.newDataValidation().requireValueInList(SURVEY_TYPES, true).setAllowInvalid(true).build());
  sh.getRange(3, 5, N, 1).insertCheckboxes();
  sh.getRange(3, 6, N, 1).insertCheckboxes();
  var W = [120, 150, 230, 90, 56, 56, 240]; for (var ci = 0; ci < W.length; ci++) sh.setColumnWidth(ci + 1, W[ci]);
  note_(sh, N + 4, SURVEYCFG_COLS.length, '同じ「フォーム名」の行をまとめて1つのGoogleフォームにします＝任意の名前でいくつでも作れます（例: 会社説明会アンケート / 一次面接アンケート / 内定者アンケート / イベント参加フォーム）。フォーム名を選考段階名(説明選考会・一次面接 等)にすると、回答の満足度/志望度が進捗管理タブの該当候補者に自動反映。タイプ=5段階/満足度/志望度/短文/長文/選択/順位/グリッド。「選択」型は選択肢欄に改行orカンマ区切り。「順位」型は選択肢欄に項目を並べると 行=項目・列=1位…N位 のグリッドに（価値観ランキング等）。「グリッド」型は選択肢欄を『行 ｜ 列』で区切る（例: 成長,待遇,人間関係 ｜ とても重要,普通,不要／列省略時は重要度5段階）。有効✓のある項目だけ出力。メニュー「採用 ▸ アンケート/フォームを作成・更新」で生成→URLは 01_設定 下部「生成フォームURL」。回答は 14_アンケート回答 に自動記録。');
}

// 14_アンケート回答: 回答ログ(追記専用)。データがあれば見出しのみ整える(消さない)。
function buildSurveyLogTab_() {
  var sh = sheet_(SH.SURVEYLOG);
  if (sh.getLastRow() > 2) return;  // 既存回答は触らない
  ensureGrid_(sh, 80, SURVEYLOG_COLS.length + 2);
  bandTitle_(sh, 1, 2, SURVEYLOG_COLS.length + 1, '■ ' + companyName_() + '　アンケート回答（段階別・候補者ごと／フォーム回答が自動追記）');
  sh.getRange(2, 2, 1, SURVEYLOG_COLS.length).setValues([SURVEYLOG_COLS]).setBackground(HEAD_BG).setFontColor(C.INK).setFontWeight('bold').setFontSize(10).setHorizontalAlignment('center');
  var W = [30, 130, 110, 110, 70, 130, 70, 70, 420]; for (var ci = 0; ci < W.length; ci++) sh.setColumnWidth(ci + 1, W[ci]);
  try { sh.setFrozenRows(2); } catch (e) {}
}

// 段階別アンケート設定 → {段階: [{name,type,required}]}(有効のみ)
function stageSurveys_() {
  var sh = ss_().getSheetByName(SH.SURVEYCFG); var out = {};
  if (!sh || sh.getLastRow() < 3) return out;
  sh.getRange(3, 2, sh.getLastRow() - 2, SURVEYCFG_COLS.length).getValues().forEach(function (r) {
    var stage = String(r[0] || '').trim(), name = String(r[1] || '').trim();
    if (!stage || !name || !confTrue_(r[4])) return;
    (out[stage] = out[stage] || []).push({ name: name, type: String(r[2] || '短文').trim(), required: confTrue_(r[3]), choices: parseChoices_(r[5]), choicesRaw: String(r[5] == null ? '' : r[5]) });
  });
  return out;
}

// 段階ごとにGoogleフォームを生成/更新(メニュー)。フォームID=props stageSurveyForms{段階:id}。
function createStageSurveyForms() {
  if (!requireCompany_('段階別アンケート生成')) return;
  var surveys = stageSurveys_(), stages = Object.keys(surveys);
  if (!stages.length) { toast_('有効なアンケート項目がありません（13_段階別アンケート設定）'); return; }
  var props = PropertiesService.getDocumentProperties(), cn = companyName_();
  var map = {}; try { map = JSON.parse(props.getProperty('stageSurveyForms') || '{}'); } catch (e) { map = {}; }
  var made = [], urls = {};
  stages.forEach(function (stage) {
    var form = null, ex = String(map[stage] || '').trim();
    if (ex) { try { form = FormApp.openById(ex); } catch (e) { form = null; } }
    if (!form) { form = FormApp.create(cn + ' ' + stage + ' アンケート'); map[stage] = form.getId(); }
    form.setTitle(cn + ' ' + stage + ' アンケート').setDescription('本日はありがとうございました。アンケートにご協力ください。');
    form.getItems().forEach(function (it) { form.deleteItem(it); });
    form.addTextItem().setTitle('メールアドレス').setRequired(true);  // 候補者突合用
    surveys[stage].forEach(function (f) {
      var item;
      if (f.type === '満足度') item = form.addListItem().setTitle(f.name).setChoiceValues(SURVEY_SATISFACTION);
      else if (f.type === '志望度') item = form.addListItem().setTitle(f.name).setChoiceValues(SURVEY_ASPIRATION);
      else if (f.type === '5段階') item = form.addListItem().setTitle(f.name).setChoiceValues(SURVEY_SCALE5);
      else if (f.type === '選択') item = setChoicesSafe_(form.addListItem().setTitle(f.name), f.choices);  // カスタム選択肢(13_設定)
      else if (f.type === '順位') {  // 行=選択肢の項目・列=1位…N位(価値観ランキング等)
        var rrows = (f.choices && f.choices.length) ? f.choices : ['項目1', '項目2', '項目3'];
        var rcols = []; for (var ri = 1; ri <= rrows.length; ri++) rcols.push(ri + '位');
        item = form.addGridItem().setTitle(f.name).setRows(rrows).setColumns(rcols);
      } else if (f.type === 'グリッド') {  // 選択肢欄を「行 ｜ 列」で分割(列省略時は重要度5段階)
        var gp = String(f.choicesRaw || '').split(/[／｜|]/);
        var grows = parseChoices_(gp[0]); var gcols = gp.length > 1 ? parseChoices_(gp[1]) : [];
        if (!grows.length) grows = ['項目1', '項目2'];
        if (!gcols.length) gcols = SURVEY_GRID_COLS;
        item = form.addGridItem().setTitle(f.name).setRows(grows).setColumns(gcols);
      }
      else if (f.type === '長文') item = form.addParagraphTextItem().setTitle(f.name);
      else item = form.addTextItem().setTitle(f.name);
      if (item.setRequired) item.setRequired(!!f.required);
    });
    ensureFormTrigger_(form);
    var u = form.getPublishedUrl(); made.push(stage + ': ' + u); urls['アンケート(' + stage + ')'] = u;
  });
  props.setProperty('stageSurveyForms', JSON.stringify(map));
  saveFormUrls_(urls);
  Logger.log('段階別アンケートURL:\n' + made.join('\n'));
  ss_().toast(stages.length + '段階のアンケートを生成/更新しました（URLは01_設定下部「生成フォームURL」に表示）', 'アンケート', 8);
}

// 段階別アンケート回答 → 14_アンケート回答へ追記＋候補者(メール一致)へ満足度/志望度反映
function recordStageSurvey_(e, stage) {
  var email = '', sat = '', asp = '', detail = [];
  e.response.getItemResponses().forEach(function (ir) {
    var resp = ir.getResponse(), t = String(ir.getItem().getTitle()), v;
    if (Array.isArray(resp)) {  // グリッド/順位=行ごとの回答配列 → 「行:選択」で整形
      var grows = []; try { grows = ir.getItem().asGridItem().getRows(); } catch (e2) {}
      v = resp.map(function (ans, i) { return (grows[i] || ('行' + (i + 1))) + ':' + ans; }).join(' / ');
    } else v = String(resp || '');
    if (/メール|mail/i.test(t)) { email = v.trim().toLowerCase(); return; }
    if (t.indexOf('満足') >= 0 && !sat) sat = v;
    if (t.indexOf('志望') >= 0 && !asp) asp = v;
    detail.push(t + '=' + v);
  });
  var cid = '', name = '', seg = '';
  if (email) {
    var m = sheet_(SH.MASTER), md = m.getDataRange().getValues(), mH = headerIndex_(md[0]);
    for (var j = 1; j < md.length; j++) {
      if (String(md[j][mH['連絡先']] || '').trim().toLowerCase() === email) {
        cid = String(md[j][mH['candidate_id']] || ''); name = String(md[j][mH['氏名']] || ''); seg = String(md[j][mH['区分']] || ''); break;
      }
    }
  }
  var log = sheet_(SH.SURVEYLOG);
  var nextR = Math.max(log.getLastRow() + 1, 3);
  log.getRange(nextR, 2, 1, SURVEYLOG_COLS.length).setValues([[fmtDT_(nowTokyo_()), cid, name, seg, stage, sat, asp, detail.join(' / ')]]);
  if (cid && !seg && (sat || asp)) Logger.log('recordStageSurvey_: 区分不明のため②反映をスキップ(cid=' + cid + ')');  // 誤って新卒②へ入れない
  if (cid && seg && (sat || asp)) {
    try {
      var sm = ss_().getSheetByName(manageName_(seg));
      if (sm && sm.getLastRow() >= 3) {
        var hdr = sm.getRange(2, 1, 1, sm.getLastColumn()).getValues()[0], oH = {}; hdr.forEach(function (h, i) { oH[String(h)] = i + 1; });
        if (oH['候補者ID']) for (var i = 3; i <= sm.getLastRow(); i++) {
          if (String(sm.getRange(i, oH['候補者ID']).getValue() || '').trim() === cid) {
            if (sat && oH['アンケート満足度']) sm.getRange(i, oH['アンケート満足度']).setValue(sat);
            if (asp && oH['志望度']) sm.getRange(i, oH['志望度']).setValue(asp);
            break;
          }
        }
      }
    } catch (er) { Logger.log('recordStageSurvey_ reflect: ' + er); }
  }
}

/* ============================== 媒体(エージェント)別 バイネーム進捗シート ============================== */
// ⚠️ 他媒体の候補は絶対に含めない厳格フィルタ。タブ生成＝社内のみ(本体SSを外部共有しない/将来は別SS切出しが必須)。
// 自動生成しない。メニューからユーザーが指定媒体を任意タイミングで作成。継続運用=再実行で最新化＋NA手入力保持。
var AGENT_COLS = ['候補者ID', '氏名', '区分', '職種', '現ステージ', '選考状況', '直近面接日', '総合評価', '最新評価/FB', 'エージェント側NA', '自社側NA'];

function createAgentSheet() {
  var ui = SpreadsheetApp.getUi();
  var chans = confRead_('CHAN').map(function (r) { return String(r[0]).trim(); }).filter(Boolean);
  var r = ui.prompt('媒体別 進捗シートを作成/更新', '対象の媒体名を入力してください。\n（チャネル定義: ' + chans.join(' / ') + '）', ui.ButtonSet.OK_CANCEL);
  if (r.getSelectedButton() !== ui.Button.OK) return;
  var name = String(r.getResponseText() || '').trim();
  if (!name) { toast_('媒体名が空です'); return; }
  var n = buildAgentSheet_(name);
  ss_().setActiveSheet(sheet_('媒体_' + name.slice(0, 90)));
  toast_('媒体別シート「媒体_' + name + '」を作成/更新（' + n + '名・社内限定・他媒体は含まず）');
}

function buildAgentSheet_(name) {
  var tab = ('媒体_' + name).slice(0, 95);
  var sh = ss_().getSheetByName(tab) || ss_().insertSheet(tab);
  // 既存のNA手入力を候補者IDで退避(継続運用=保持)
  var keep = {};
  if (sh.getLastRow() > 2) {
    var od = sh.getRange(2, 2, sh.getLastRow() - 1, AGENT_COLS.length).getValues();
    var hh = {}; (od[0] || []).forEach(function (h, i) { hh[String(h)] = i; });
    for (var i = 1; i < od.length; i++) {
      var cid0 = String(od[i][hh['候補者ID']] || '').trim(); if (!cid0) continue;
      keep[cid0] = { ag: od[i][hh['エージェント側NA']], own: od[i][hh['自社側NA']] };
    }
  }
  var m = sheet_(SH.MASTER), md = m.getDataRange().getValues(), mH = headerIndex_(md[0]);
  var rows = [];
  for (var j = 1; j < md.length; j++) {
    var rr = md[j];
    if (String(rr[mH['チャネル']] || '').trim() !== name) continue;  // 厳格フィルタ=他媒体ゼロ
    var cid = String(rr[mH['candidate_id']] || '').trim(); if (!cid) continue;
    var kp = keep[cid] || {}, lastIv = rr[mH['直近面接日']];
    rows.push([cid, rr[mH['氏名']] || '', rr[mH['区分']] || '', rr[mH['職種']] || '', rr[mH['現ステージ']] || '', rr[mH['ステータス']] || '',
      (lastIv instanceof Date) ? fmtD_(lastIv) : '', rr[mH['総合評価']] || '', rr[mH['最新評価']] || '', kp.ag || '', kp.own || '']);
  }
  clearSheet_(sh);
  var N = Math.max(rows.length + 30, 60);
  ensureGrid_(sh, N + 3, AGENT_COLS.length + 1);
  bandTitle_(sh, 1, 2, AGENT_COLS.length + 1, '■ ' + companyName_() + '　媒体別 進捗管理 ─ ' + name + '（社内限定・バイネーム）');
  sh.getRange(2, 2, 1, AGENT_COLS.length).setValues([AGENT_COLS]).setBackground(HEAD_BG).setFontColor(C.INK).setFontWeight('bold').setFontSize(10).setHorizontalAlignment('center');
  if (rows.length) sh.getRange(3, 2, rows.length, AGENT_COLS.length).setValues(rows).setFontSize(10).setVerticalAlignment('middle').setWrap(true);
  var bgs = []; for (var z = 0; z < N; z++) { var line = []; for (var w = 0; w < AGENT_COLS.length; w++) line.push(z % 2 ? C.ZEBRA : C.WHITE); bgs.push(line); }
  sh.getRange(3, 2, N, AGENT_COLS.length).setBackgrounds(bgs);
  ['エージェント側NA', '自社側NA'].forEach(function (cn2) { var idx = AGENT_COLS.indexOf(cn2); if (idx >= 0) sh.getRange(3, 2 + idx, N, 1).setBackground(DESIGN_INPUT_BG); });
  sh.getRange(2, 2, N + 1, AGENT_COLS.length).setBorder(true, true, true, true, true, true, C.BORDER, SpreadsheetApp.BorderStyle.SOLID);
  sh.setColumnWidth(1, 30);
  var W = [100, 90, 70, 110, 90, 90, 100, 72, 220, 220, 220];
  for (var ci = 0; ci < W.length; ci++) sh.setColumnWidth(ci + 2, W[ci]);
  note_(sh, 3 + N + 1, 10, 'この媒体(' + name + ')から応募/紹介された候補者のみ（他媒体は含まない・社内限定）。エージェント側NA/自社側NAは手入力＝再作成しても保持。再実行で最新化＋新規候補を追記。エージェント共有時は本体SSではなくこのシートだけ別ファイルに切り出すこと。');
  return rows.length;
}

/* ============================== ウォッチドッグ（健全性監視・自動修復） ============================== */
// 構造/書式/位置のドリフトを検出し、入力保持の冪等再構築で自動修復。要判断は警告のみ。99_ヘルスログに記録。
// シート外(実Form削除/OAuth失効/Drive権限)やデータ中身の誤りは対象外。修復は1実行1パス。

function healthCheckRun() { var f = healthCheck_(true); toast_('健全性チェック: ' + f.repaired + '件修復 / ' + f.warn + '件要対応（99_ヘルスログ参照）'); }
function healthDailyAuto() { try { healthCheck_(true); } catch (e) { Logger.log('healthDailyAuto error: ' + e); } }

function healthCheck_(repair) {
  var ss = ss_(), rows = [], repaired = 0, warn = 0;
  var now = nowTokyo_(), ts = Utilities.formatDate(new Date(), ss.getSpreadsheetTimeZone(), 'yyyy-MM-dd HH:mm');
  function rec(area, status, detail) { rows.push([ts, area, status, detail]); if (status === '修復') repaired++; if (status === '要対応') warn++; }
  // 1) 必須タブの存在
  var need = [SH.README, SH.CONF, SH.MASTER, SH.IV, SH.NOTE, SH.D_ALL, SH.RP, SH.MAIL, SH.CSV];
  var missing = need.filter(function (n) { return !ss.getSheetByName(n); });
  if (missing.length) {
    if (repair) { try { setupAll(); rec('必須タブ', '修復', '不足を再構築: ' + missing.join(',')); } catch (e) { rec('必須タブ', '要対応', '不足: ' + missing.join(',') + ' / 再構築失敗'); } }
    else rec('必須タブ', '要対応', '不足: ' + missing.join(','));
  } else rec('必須タブ', 'OK', need.length + '枚');
  // 2) マスタ/11_ ヘッダ整合(列名)
  function hdrOk(tab, cols) { var sh = ss.getSheetByName(tab); if (!sh) return false; var h = sh.getRange(1, 1, 1, cols.length).getValues()[0]; for (var i = 0; i < cols.length; i++) if (String(h[i]) !== cols[i]) return false; return true; }
  if (ss.getSheetByName(SH.MASTER) && !hdrOk(SH.MASTER, MASTER_COLS)) {
    if (repair) { try { buildMaster_(); rec('マスタ列', '修復', 'ヘッダ不一致→snapshot再構築(データ保持)'); } catch (e) { rec('マスタ列', '要対応', 'ヘッダ不一致/修復失敗'); } }
    else rec('マスタ列', '要対応', 'ヘッダ不一致');
  } else rec('マスタ列', 'OK', '');
  if (ss.getSheetByName(SH.IV) && !hdrOk(SH.IV, IV_COLS)) {
    if (repair) { try { buildInterview_(); rec('11_列', '修復', 'ヘッダ不一致→再構築'); } catch (e) { rec('11_列', '要対応', 'ヘッダ不一致/修復失敗'); } }
    else rec('11_列', '要対応', 'ヘッダ不一致');
  } else rec('11_列', 'OK', '');
  // 3) 設定バージョン＆主要ブロック健全性
  var verOk = PropertiesService.getDocumentProperties().getProperty('confLayoutVer') === CONF_LAYOUT_VER;
  var stageEmpty = false; try { stageEmpty = confRead_('STAGE').length === 0; } catch (e) { stageEmpty = true; }
  if (!verOk || stageEmpty) {
    if (repair && !stageEmpty) { try { buildSettings_(); rec('01_設定', '修復', 'レイアウト版ズレ→migration再構築(入力保持)'); } catch (e) { rec('01_設定', '要対応', 'バージョンズレ/修復失敗'); } }
    else rec('01_設定', '要対応', (stageEmpty ? '選考ステージが空(設定未投入の可能性)' : 'レイアウト版ズレ') + ' ※空のときは自動修復しません');
  } else rec('01_設定', 'OK', CONF_LAYOUT_VER);
  // 4) 自動配信トリガー整合
  try {
    var mc = mailConfig_(), trigs = ScriptApp.getProjectTriggers().map(function (t) { return t.getHandlerFunction(); });
    if (mc.autoOn && (trigs.indexOf('remindDailyAuto') < 0 || trigs.indexOf('thanksDailyAuto') < 0)) rec('自動メール', '要対応', '自動送信ONだがトリガー不足→「自動配信を設定」を実行');
    else rec('自動メール', 'OK', mc.autoOn ? '自動ON・トリガー有' : '自動OFF');
    // Slack配信: 有効なのにトリガー/トークン不足を検知
    var slackOn = false; try { ['週次', '月次', '日次'].forEach(function (p) { var t = slackTargetByPrefix_(p); if (t && t.enabled) slackOn = true; }); } catch (e3) {}
    if (slackOn) {
      var slackTrig = trigs.indexOf('slackWeeklyAuto') >= 0 || trigs.indexOf('slackDailyAuto') >= 0 || trigs.indexOf('slackMonthlyAuto') >= 0;
      var tokenOk = false; try { tokenOk = !!slackToken_(); } catch (e4) {}
      if (!tokenOk) rec('Slack配信', '要対応', 'Slack配信が有効だがトークン未設定→送信されません');
      else if (!slackTrig) rec('Slack配信', '要対応', 'Slack配信が有効だがトリガー未設置→「自動配信を設定」を実行');
      else rec('Slack配信', 'OK', '有効・トークン/トリガー有');
    }
    // フォーム運用: フォーム生成済みなのに onFormSubmit トリガーが無い(応募が取り込まれない)
    var formIds = {}; try { formIds = JSON.parse(PropertiesService.getDocumentProperties().getProperty('formIds') || '{}'); } catch (e5) {}
    if (Object.keys(formIds).length && trigs.indexOf('onFormSubmit') < 0) rec('フォーム', '要対応', '応募フォーム生成済だがonFormSubmitトリガー無し→応募が取り込まれません。フォームを再生成してください');
  } catch (e) { rec('自動メール', 'OK', ''); }
  // 5) 媒体別シートの存在(混入は要目視のため件数のみ記録)
  var agentTabs = ss.getSheets().map(function (s) { return s.getName(); }).filter(function (n) { return n.indexOf('媒体_') === 0; });
  if (agentTabs.length) rec('媒体別シート', 'OK', agentTabs.length + '枚(' + agentTabs.join(',') + ') ※他媒体混入は目視確認');
  // 6) 区分別②進捗管理タブ: 有効区分ごとに存在を点検→欠落は再構築
  try {
    var enR = enabledSegments_(), missR = [];
    // 新卒②は説明会設定の有無で存在が変わる(③ヨミは任意)ため健全性チェック対象外。
    enR.forEach(function (s) { if (s !== '新卒' && !ss.getSheetByName(manageName_(s))) missR.push(s); });
    if (missR.length) {
      if (repair) { try { missR.forEach(function (s) { buildSegManage_(s); }); rec('区分別進捗管理', '修復', '欠落を再構築: ' + missR.join(',')); } catch (e) { rec('区分別進捗管理', '要対応', '欠落: ' + missR.join(',') + ' / 再構築失敗'); } }
      else rec('区分別進捗管理', '要対応', '欠落: ' + missR.join(','));
    } else rec('区分別進捗管理', 'OK', enR.length + '区分');
  } catch (e) { rec('区分別進捗管理', 'OK', ''); }
  // ログ出力(99_ヘルスログ・最新を上に)
  var log = ss.getSheetByName('99_ヘルスログ') || ss.insertSheet('99_ヘルスログ');
  if (log.getLastRow() === 0) {
    log.getRange(1, 1, 1, 4).setValues([['日時', '項目', '状態', '詳細']]).setBackground(HEAD_BG).setFontColor(C.INK).setFontWeight('bold');
    log.setColumnWidth(1, 130); log.setColumnWidth(2, 120); log.setColumnWidth(3, 70); log.setColumnWidth(4, 420);
    log.setFrozenRows(1); log.setHiddenGridlines(true);
  }
  if (rows.length) {
    log.insertRowsAfter(1, rows.length);
    log.getRange(2, 1, rows.length, 4).setValues(rows).setFontSize(9).setVerticalAlignment('top').setWrap(true);
    var warnRange = log.getRange(2, 3, rows.length, 1);
    log.setConditionalFormatRules([
      SpreadsheetApp.newConditionalFormatRule().whenTextEqualTo('要対応').setBackground('#F8D7DA').setFontColor(C.RED).setRanges([warnRange]).build(),
      SpreadsheetApp.newConditionalFormatRule().whenTextEqualTo('修復').setBackground('#FCEFE6').setFontColor('#B45309').setRanges([warnRange]).build()
    ]);
  }
  return { repaired: repaired, warn: warn };
}

/* ============================== 応募フォーム後始末 ============================== */

// フォーム機能の後始末(実行DropDownから1回): onFormSubmitトリガー削除＋回答タブ削除＋formIdsプロパティ削除。
// ※ Google Drive上の実フォーム本体は手動削除（Driveスコープ回避のためDriveAppは使わない）。
// ※ フォームにリンク済みの「フォームの回答」シートはGoogle仕様でdeleteSheetが例外→握り潰さず検出し、手動リンク解除を案内する。
function cleanupForms() {
  var n = 0;
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'onFormSubmit') { ScriptApp.deleteTrigger(t); n++; }
  });
  var ss = ss_(), del = 0, linked = [];
  ss.getSheets().forEach(function (s) {
    if (!/^フォームの回答/.test(s.getName())) return;
    try { ss.deleteSheet(s); del++; }
    catch (e) { linked.push(s.getName()); }  // フォームにリンク済=APIで削除不可→握り潰さず記録
  });
  PropertiesService.getDocumentProperties().deleteProperty('formIds');
  reportFormCleanup_('フォーム後始末: トリガー' + n + '件削除 / 回答タブ' + del + '件削除', linked);
}

// フォーム後始末/クリーン初期化の結果通知。リンク済みで消せなかったシートがあれば手順を明示(サイレント失敗を防ぐ)。
function reportFormCleanup_(summary, linked) {
  if (linked && linked.length) {
    var how = summary + '\n\n⚠️ ' + linked.length + '枚はフォームにリンク済みのため自動削除できません:\n・'
      + linked.join('\n・') + '\n\n削除手順: 各タブを右クリック →「フォームのリンクを解除」→ もう一度右クリック →「削除」。\n'
      + '（リンク済みシートはGoogleの仕様でスクリプトから削除できません）';
    try { var ui = SpreadsheetApp.getUi(); ui.alert('フォーム後始末', how, ui.ButtonSet.OK); }
    catch (e) { toast_(summary + ' ／⚠️' + linked.length + '枚はリンク解除が必要(右クリック→フォームのリンクを解除→削除)'); }
  } else {
    toast_(summary + '（実フォームはDriveで手動削除）');
  }
}

// クリーン初期化(メニュー): このシートを「初期設定前の白紙」状態にする。多クライアント横展開の雛形を白紙から設計するため。
// 01_設定の全入力を空に / README・01_設定以外のタブを削除 / フォーム未設定化。cleanTemplateフラグで以後デフォルト自動投入を抑止。
function cleanInit() {
  var ui = null; try { ui = SpreadsheetApp.getUi(); } catch (e) {}
  // ガード: 使用中シート(候補者/会社名あり)はパスワード必須。白紙テンプレは簡易確認。
  // UIなし(スクリプトエディタ実行)はオーナーの復旧経路として確認をスキップ。
  if (ui) {
    var dp0 = PropertiesService.getDocumentProperties();
    var impact = cleanInitImpact_();
    if (cleanInitInUse_()) {
      var pwHash = dp0.getProperty('cleanInitPwHash');
      if (!pwHash) {
        ui.alert('クリーン初期化はロックされています',
          'このシートは使用中です（' + impact + '）。\n'
          + '初期化するには、先にメニュー「採用 ＞ 初期化パスワードを設定」でパスワードを設定してください。',
          ui.ButtonSet.OK);
        return;
      }
      var rp = ui.prompt('クリーン初期化（パスワードが必要です）',
        '【警告】次の内容が完全に消えます（元に戻せません）:\n  ' + impact + '\n\n'
        + '初期化パスワードを入力してください（空欄=中止）:',
        ui.ButtonSet.OK_CANCEL);
      if (rp.getSelectedButton() !== ui.Button.OK) return;
      var entered = String(rp.getResponseText() || '').trim();
      if (!entered) return;
      if (cleanInitPwHash_(entered, dp0.getProperty('cleanInitSalt') || '') !== pwHash) {
        ui.alert('パスワードが違います。クリーン初期化を中止しました。');
        return;
      }
      if (ui.alert('最終確認',
        impact + '\nを消去して白紙の雛形にします。本当によろしいですか？',
        ui.ButtonSet.YES_NO) !== ui.Button.YES) return;
    } else {
      if (ui.alert('クリーン初期化',
        'このシートを白紙の雛形にします（消えるデータはありません）。実行しますか？',
        ui.ButtonSet.YES_NO) !== ui.Button.YES) return;
    }
  }
  var props = PropertiesService.getDocumentProperties();
  props.setProperty('cleanTemplate', 'true');
  // フォーム未設定化(onFormSubmitトリガー＋formIds)
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'onFormSubmit') { try { ScriptApp.deleteTrigger(t); } catch (e) {} }
  });
  props.deleteProperty('formIds');
  // README/CONF以外の全タブ削除(リンク済みフォーム回答シートは握り潰さず記録)
  var ss = ss_(), keep = [SH.README, SH.CONF], removed = 0, linked = [];
  ss.getSheets().forEach(function (s) {
    var nm = s.getName(); if (keep.indexOf(nm) >= 0) return;
    try { ss.deleteSheet(s); removed++; }
    catch (e) { linked.push(nm); }
  });
  // 01_設定を白紙化してから再構築(snapshotが空になる→cleanTemplateと併せて既定も投入されない)
  var conf = sheet_(SH.CONF);
  try { conf.getRange(1, 1, conf.getMaxRows(), 52).breakApart(); } catch (e) {}
  conf.getRange(1, 1, conf.getMaxRows(), 52).clearContent();
  props.deleteProperty('confBackup');  // 退避バックアップも破棄(古い既定で復元されないように)
  buildReadme_();
  buildSettings_();                    // cleanTemplate=true → 設計バンドのみ空・カタログ系は既定投入
  try { buildChannelMaster_(); } catch (e) {}  // チャネル候補マスタ(既定リスト・基本ON)を復元=チェックで選ぶカタログ
  try { reorderTabs_(); } catch (e) {}
  reportFormCleanup_('クリーン初期化: タブ' + removed + '枚削除・01_設定を白紙化(設計欄のみ・選択肢カタログは保持)。次は 01_設定 を埋めてから、メニュー「初期セットアップ / 再構築」を実行してください', linked);
}

// ── クリーン初期化のパスワード保護(誤実行・不正実行の防止) ──
// パスワードは salt付きSHA-256ハッシュで DocumentProperties に保存。平文はシート/プロパティに残さない。
function cleanInitPwHash_(pw, salt) {
  var raw = Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, String(salt) + '::' + String(pw), Utilities.Charset.UTF_8);
  return Utilities.base64Encode(raw);
}

// シートが「使用中」か(=破壊で実データが失われるか)。候補者データありor会社名ありなら true。
function cleanInitInUse_() {
  try {
    var m = ss_().getSheetByName(SH.MASTER);
    if (m && m.getLastRow() > 1) return true;  // ヘッダ以外に候補者行がある
  } catch (e) { console.error('cleanInitInUse_ master: ' + e); }
  try { if (String(companyName_() || '').trim()) return true; } catch (e) { console.error('cleanInitInUse_ company: ' + e); }
  return false;
}

// 何が消えるかのサマリ文字列(警告表示用)。
function cleanInitImpact_() {
  var parts = [];
  try { var cn = String(companyName_() || '').trim(); if (cn) parts.push('会社「' + cn + '」の設定'); } catch (e) { console.error('cleanInitImpact_ company: ' + e); }
  try {
    var ss = ss_(), m = ss.getSheetByName(SH.MASTER);
    var n = m ? Math.max(0, m.getLastRow() - 1) : 0;
    if (n > 0) parts.push('候補者 ' + n + '件');
    var tabs = ss.getSheets().length - 2;  // 00_README と 01_設定 以外
    if (tabs > 0) parts.push('タブ ' + tabs + '枚');
  } catch (e) { console.error('cleanInitImpact_ tabs: ' + e); }
  return parts.length ? parts.join(' / ') : '（消えるデータはありません）';
}

// 初期化パスワードの設定/変更/解除(メニュー「初期化パスワードを設定」)。
function setCleanInitPassword() {
  var ui = SpreadsheetApp.getUi();
  var dp = PropertiesService.getDocumentProperties();
  var cur = dp.getProperty('cleanInitPwHash');
  if (cur) {
    var rc = ui.prompt('初期化パスワードの変更',
      '現在のパスワードを入力してください（変更・解除に必要・空欄=中止）:', ui.ButtonSet.OK_CANCEL);
    if (rc.getSelectedButton() !== ui.Button.OK) return;
    var curIn = String(rc.getResponseText() || '').trim();
    if (!curIn || cleanInitPwHash_(curIn, dp.getProperty('cleanInitSalt') || '') !== cur) {
      ui.alert('現在のパスワードが違います。中止しました。');
      return;
    }
  }
  var rn = ui.prompt('初期化パスワードの設定',
    '新しいパスワードを入力してください。\nこのパスワードは「クリーン初期化」の実行時に必要になります。\n（空欄のまま実行すると、パスワード保護を解除します）',
    ui.ButtonSet.OK_CANCEL);
  if (rn.getSelectedButton() !== ui.Button.OK) return;
  var np = String(rn.getResponseText() || '').trim();
  if (!np) {
    dp.deleteProperty('cleanInitPwHash');
    dp.deleteProperty('cleanInitSalt');
    ui.alert('初期化パスワードの保護を解除しました。');
    return;
  }
  var salt = Utilities.getUuid();
  dp.setProperty('cleanInitSalt', salt);
  dp.setProperty('cleanInitPwHash', cleanInitPwHash_(np, salt));
  ui.alert('初期化パスワードを設定しました。\n以後、使用中シートの「クリーン初期化」にはこのパスワードが必要です。');
}

/* ============================== 07_メール設定 ＋ 自動メール（サンクス/リマインド） ============================== */

// 07_メール設定の固定セル(行,列)。本文は背の高いマージセル。
var MAIL_CELLS = {
  fromName: [4, 3], replyTo: [5, 3], autoOn: [6, 3], leadDays: [7, 3],
  thanksSubj: [11, 3], thanksBody: [12, 3],
  ivSubj: [16, 3], ivBody: [17, 3],
  briefSubj: [21, 3], briefBody: [22, 3]
};

function buildMailTab_() {
  var sh = sheet_(SH.MAIL);
  var marker = sh.getRange(MAIL_CELLS.thanksSubj[0], MAIL_CELLS.thanksSubj[1]).getValue();
  if (sh.getLastRow() > 5 && String(marker || '').trim() !== '') { ensureMailReminders_(sh); return; }  // 既に生成済→編集保持(段階別リマインド表だけ後付け確認)
  clearSheet_(sh);
  ensureGrid_(sh, 30, 12);
  sh.setColumnWidth(1, 28); sh.setColumnWidth(2, 150);
  for (var c = 3; c <= 11; c++) sh.setColumnWidth(c, 92);
  var cn = companyName_();
  bandTitle_(sh, 1, 2, 11, '■ ' + cn + '　メール配信設定（サンクス／リマインド）');

  subhead_(sh, 3, '▎送信設定（送付元は実行アカウントのアドレス。表示名と返信先のみ指定可）');
  function lbl(r, t) { sh.getRange(r, 2).setValue(t).setFontWeight('bold').setFontColor(C.BLACK).setVerticalAlignment('middle'); }
  function box(r, span) { var rg = sh.getRange(r, 3, 1, span || 9); rg.breakApart(); rg.merge().setBackground(DESIGN_INPUT_BG).setVerticalAlignment('middle').setWrap(true).setBorder(true, true, true, true, false, false, C.BORDER, SpreadsheetApp.BorderStyle.SOLID); return rg; }
  lbl(4, '表示名'); box(4).setValue(cn + ' 採用担当');
  lbl(5, '返信先(Reply-To)'); box(5).setValue('');
  lbl(6, '自動送信(毎朝8時)'); sh.getRange(6, 3).insertCheckboxes().setValue(false);
  lbl(7, 'リマインド日数(カンマ区切り)'); box(7, 3).setValue('3,1').setNumberFormat('@');

  subhead_(sh, 9, '▎テンプレート（{ }は差込。件名・本文を自由に編集できます）');
  function tmpl(subjRow, bodyRow, name, subj, body) {
    lbl(subjRow, name + ' 件名'); box(subjRow).setValue(subj);
    lbl(bodyRow, name + ' 本文'); var b = box(bodyRow); b.setValue(body).setVerticalAlignment('top');
    sh.setRowHeight(bodyRow, 110);
  }
  tmpl(MAIL_CELLS.thanksSubj[0], MAIL_CELLS.thanksBody[0], 'サンクス(エントリー当日)',
    '【{会社名}】ご応募ありがとうございます',
    '{氏名} 様\n\nこの度は{会社名}の{職種}へご応募いただき、誠にありがとうございます。\n担当者より追ってご連絡いたします。\n\n{会社名} 採用担当');
  tmpl(MAIL_CELLS.ivSubj[0], MAIL_CELLS.ivBody[0], '面接リマインド',
    '【{会社名}】{ステージ}のご案内（{日時}）',
    '{氏名} 様\n\n{日時}より{ステージ}を予定しております。\n形式: {形式}\nURL/場所: {URL}\n担当: {面接官}\n\nお気をつけてお越しください。\n{会社名} 採用担当');
  tmpl(MAIL_CELLS.briefSubj[0], MAIL_CELLS.briefBody[0], '説明会リマインド',
    '【{会社名}】会社説明会のご案内（{日時}）',
    '{氏名} 様\n\n{日時}より会社説明会を開催いたします。\nURL/場所: {URL}\n\nご参加をお待ちしております。\n{会社名} 採用担当');

  note_(sh, 24, 10, '差込タグ: {氏名} {区分} {職種} {ステージ} {日時} {形式} {面接官} {URL} {会社名}。サンクス=エントリー(応募日)当日に1回。リマインド=11_面接スケジュールの予定日時の指定日数前。標準は「面接」「説明会」の2テンプレ。下の「段階別リマインド設定」で段ごとに 何日前・文面 を上書きできます。自動送信ONで毎朝8時に送信。送付元アドレスはGAS仕様で実行アカウント固定（表示名/返信先のみ指定可）。');
  ensureMailReminders_(sh);
}

// 段階別リマインド設定テーブル(07_メール設定の下部)。既存07にも後付けで追加し、編集は保持(タイトル有→何もしない)。
var MAIL_REMIND = { titleRow: 27, headerRow: 28, row: 29, w: 5, max: 10 };
function ensureMailReminders_(sh) {
  var L = MAIL_REMIND;
  if (String(sh.getRange(L.titleRow, 2).getValue() || '').trim() !== '') return;  // 既にある→保持
  ensureGrid_(sh, L.row + L.max + 2, 12);
  subhead_(sh, L.titleRow, '▎段階別リマインド設定（ステージ/イベント名ごとに 何日前・件名・本文・有効。空欄/未設定の段は上の標準テンプレを使用）');
  sh.getRange(L.headerRow, 2, 1, L.w).setValues([['対象（ステージ/イベント名・部分一致）', '何日前(カンマ可)', '件名(空=標準)', '本文(空=標準)', '有効']])
    .setBackground(HEAD_BG).setFontColor(C.INK).setFontWeight('bold').setFontSize(9).setHorizontalAlignment('center');
  var seed = [['一次面接', '3,1', '', '', false], ['最終面接', '5,3,1', '', '', false], ['説明会', '3,1', '', '', false]];
  for (var c = 0; c < L.w; c++) sh.getRange(L.row, 2 + c, L.max, 1).setBackground(DESIGN_INPUT_BG);
  sh.getRange(L.row, 2, seed.length, L.w).setValues(seed);
  sh.getRange(L.row, 2, L.max, 1).setNumberFormat('@');   // 対象
  sh.getRange(L.row, 3, L.max, 1).setNumberFormat('@');   // 何日前
  sh.getRange(L.row, 5, L.max, 1).setWrap(true);          // 本文
  sh.getRange(L.row, 6, L.max, 1).insertCheckboxes();     // 有効
  sh.getRange(L.headerRow, 2, L.max + 1, L.w).setBorder(true, true, true, true, true, true, C.BORDER, SpreadsheetApp.BorderStyle.SOLID);
}
// ステージ名に部分一致する有効なリマインド規則を返す(無ければnull=標準テンプレ)。
function matchReminderRule_(reminders, stage) {
  if (!reminders) return null;
  for (var i = 0; i < reminders.length; i++) {
    var rl = reminders[i];
    if (rl.on && rl.match && String(stage).indexOf(rl.match) >= 0) return rl;
  }
  return null;
}

// 07_メール設定の読み取り → {fromName, replyTo, autoOn, leadDays[], thanks{subj,body}, iv{...}, brief{...}, reminders[]}
function mailConfig_() {
  var sh = sheet_(SH.MAIL);
  function g(key) { var c = MAIL_CELLS[key]; return String(sh.getRange(c[0], c[1]).getValue() || ''); }
  var lead = g('leadDays').split(/[,、\s]+/).map(function (x) { return parseInt(x, 10); }).filter(function (n) { return !isNaN(n) && n >= 0; });
  // 段階別リマインド設定(下部テーブル)
  var reminders = [];
  try {
    var RL = MAIL_REMIND, rd = sh.getRange(RL.row, 2, RL.max, RL.w).getValues();
    rd.forEach(function (rr) {
      var match = String(rr[0] || '').trim(); if (!match) return;
      var ld = String(rr[1] || '').split(/[,、\s]+/).map(function (x) { return parseInt(x, 10); }).filter(function (n) { return !isNaN(n) && n >= 0; });
      reminders.push({ match: match, leadDays: ld, subj: String(rr[2] || ''), body: String(rr[3] || ''), on: confTrue_(rr[4]) });
    });
  } catch (e) {}
  return {
    fromName: g('fromName').trim() || companyName_(),
    replyTo: g('replyTo').trim(),
    autoOn: confTrue_(sh.getRange(MAIL_CELLS.autoOn[0], MAIL_CELLS.autoOn[1]).getValue()),
    leadDays: lead.length ? lead : [3, 1],
    thanks: { subj: g('thanksSubj'), body: g('thanksBody') },
    iv: { subj: g('ivSubj'), body: g('ivBody') },
    brief: { subj: g('briefSubj'), body: g('briefBody') },
    reminders: reminders
  };
}

// 差込: {key}を ctx[key] で置換
function fillTemplate_(tmpl, ctx) {
  return String(tmpl || '').replace(/\{(\w+|[^}]+)\}/g, function (m, k) { return (ctx[k] != null) ? String(ctx[k]) : m; });
}
// メール送信(実行アカウント・表示名/返信先付き・本文は改行→<br>のHTML)
function mailSend_(to, subject, body, cfg) {
  if (!to || !subject) return false;
  var opt = { name: cfg.fromName || companyName_(), htmlBody: String(body || '').replace(/\n/g, '<br>') };
  if (cfg.replyTo) opt.replyTo = cfg.replyTo;
  try { MailApp.sendEmail(to, subject, String(body || ''), opt); return true; }
  catch (e) { Logger.log('mailSend error: ' + e); return false; }
}
function validEmail_(s) { return /.+@.+\..+/.test(String(s || '').trim()); }

// エントリー当日サンクス: 応募日==今日 & サンクス送信日空 & 連絡先有効 → 送信＋送信日記録
function sendThanksAuto_(opts) {
  opts = opts || {}; var cfg = mailConfig_();
  if (!opts.manual && !cfg.autoOn) return 0;
  if (!requireCompany_('サンクスメール送信')) return 0;
  if (!cfg.thanks.subj || !cfg.thanks.body) { if (opts.manual) toast_('サンクスのテンプレが未設定（07_メール設定）'); return 0; }
  var m = sheet_(SH.MASTER), data = m.getDataRange().getValues(), H = headerIndex_(data[0]);
  var today = tokyoDayMs_(new Date()), cn = companyName_(), sent = 0;
  for (var i = 1; i < data.length; i++) {
    var r = data[i];
    if (String(r[H['candidate_id']] || '').trim() === '') continue;
    var ap = r[H['応募日']]; if (!(ap instanceof Date) || tokyoDayMs_(ap) !== today) continue;
    if (String(r[H['サンクス送信日']] || '').trim() !== '') continue;
    var to = String(r[H['連絡先']] || '').trim(); if (!validEmail_(to)) continue;
    var ctx = { 氏名: r[H['氏名']], 区分: r[H['区分']], 職種: r[H['職種']], 会社名: cn };
    if (mailSend_(to, fillTemplate_(cfg.thanks.subj, ctx), fillTemplate_(cfg.thanks.body, ctx), cfg)) {
      var n = nowTokyo_();
      m.getRange(i + 1, H['サンクス送信日'] + 1).setValue(d_(n.getUTCFullYear(), n.getUTCMonth() + 1, n.getUTCDate())).setNumberFormat('yyyy-mm-dd');
      sent++;
    }
  }
  if (opts.manual) toast_('サンクスメールを' + sent + '件送信しました');
  return sent;
}

// イベント前リマインド: 11_の予定日時の指定日数前に送信(重複防止ログ)
function sendRemindersAuto_(opts) {
  opts = opts || {}; var cfg = mailConfig_();
  if (!opts.manual && !cfg.autoOn) return 0;
  if (!requireCompany_('リマインドメール送信')) return 0;
  var iv = sheet_(SH.IV), ivd = iv.getDataRange().getValues(); if (ivd.length < 2) { if (opts.manual) toast_('面接予定がありません'); return 0; }
  var ivH = headerIndex_(ivd[0]);
  var m = sheet_(SH.MASTER), md = m.getDataRange().getValues(), mH = headerIndex_(md[0]);
  var email = {}; for (var j = 1; j < md.length; j++) { var cid = String(md[j][mH['candidate_id']] || '').trim(); if (cid) email[cid] = String(md[j][mH['連絡先']] || '').trim(); }
  var props = PropertiesService.getDocumentProperties();
  var log = {}; try { log = JSON.parse(props.getProperty('mailRemindLog') || '{}'); } catch (e) { log = {}; }
  var cn = companyName_(), sent = 0;
  for (var i = 1; i < ivd.length; i++) {
    var r = ivd[i];
    var dt = r[ivH['予定日時']]; if (!(dt instanceof Date)) continue;
    if (String(r[ivH['ステータス']] || '') === 'キャンセル') continue;
    var du = daysFromToday_(dt); if (du < 0) continue;
    var stage = String(r[ivH['ステージ']] || '');
    var rule = matchReminderRule_(cfg.reminders, stage);                          // 段階別設定(部分一致・有効)優先
    var effLead = (rule && rule.leadDays && rule.leadDays.length) ? rule.leadDays : cfg.leadDays;
    if (effLead.indexOf(du) < 0) continue;
    var ivId = String(r[ivH['interview_id']] || ('row' + i));
    var doneList = log[ivId] || [];
    if (doneList.indexOf(du) >= 0) continue;  // 既送信
    var cid = String(r[ivH['candidate_id']] || '').trim();
    var to = email[cid] || ''; if (!validEmail_(to)) continue;
    var isBrief = stage.indexOf('説明会') >= 0;
    var baseTpl = isBrief ? cfg.brief : cfg.iv;
    var subj = (rule && rule.subj) ? rule.subj : baseTpl.subj;   // 段階別の件名/本文が空なら標準テンプレ
    var body = (rule && rule.body) ? rule.body : baseTpl.body;
    if (!subj || !body) continue;
    var ctx = { 氏名: r[ivH['候補者名']], 区分: r[ivH['区分']], 職種: r[ivH['職種']], ステージ: stage,
      日時: fmtDT_(dt), 形式: r[ivH['形式']], 面接官: r[ivH['面接官']], URL: r[ivH['面接URL']], 会社名: cn };
    if (mailSend_(to, fillTemplate_(subj, ctx), fillTemplate_(body, ctx), cfg)) {
      doneList.push(du); log[ivId] = doneList; sent++;
    }
  }
  try { props.setProperty('mailRemindLog', JSON.stringify(log)); }
  catch (e) { Logger.log('mailRemindLog 保存失敗(次回重複送信の恐れ): ' + e); }  // 保存失敗を可視化
  if (opts.manual) toast_('リマインドメールを' + sent + '件送信しました');
  return sent;
}
// 手動メニュー用
function sendThanksNow() { sendThanksAuto_({ manual: true }); }
function sendRemindersNow() { sendRemindersAuto_({ manual: true }); }
function openMailSettings() { var sh = sheet_(SH.MAIL); ss_().setActiveSheet(sh); toast_('07_メール設定でテンプレ・送信設定を編集できます'); }

/* ---------- Gemini API でメール文面を下書き ---------- */
var GEMINI_MODEL = 'gemini-2.0-flash';
function setGeminiKey() {
  var ui = SpreadsheetApp.getUi();
  var r = ui.prompt('Gemini APIキー設定', 'Google AI Studio のAPIキーを貼り付け（PropertiesServiceに保存・シートには残りません）', ui.ButtonSet.OK_CANCEL);
  if (r.getSelectedButton() !== ui.Button.OK) return;
  var k = String(r.getResponseText() || '').trim();
  if (!k) { toast_('キーが空です'); return; }
  PropertiesService.getDocumentProperties().setProperty('geminiApiKey', k);
  toast_('Gemini APIキーを保存しました');
}
function geminiDraft_(instruction) {
  var key = String(PropertiesService.getDocumentProperties().getProperty('geminiApiKey') || '').trim();
  if (!key) throw new Error('Gemini APIキー未設定（メニュー「AIキー(Gemini)を設定」）');
  var url = 'https://generativelanguage.googleapis.com/v1beta/models/' + GEMINI_MODEL + ':generateContent?key=' + encodeURIComponent(key);
  var res = UrlFetchApp.fetch(url, {
    method: 'post', contentType: 'application/json', muteHttpExceptions: true,
    payload: JSON.stringify({ contents: [{ parts: [{ text: instruction }] }] })
  });
  if (res.getResponseCode() !== 200) throw new Error('Gemini APIエラー(' + res.getResponseCode() + '): ' + res.getContentText().slice(0, 200));
  try { return JSON.parse(res.getContentText()).candidates[0].content.parts[0].text; } catch (e) { return ''; }
}
function draftMailWithAI() {
  var ui = SpreadsheetApp.getUi(), cn = companyName_();
  var kinds = { '1': ['thanks', 'サンクス(エントリー当日)', 'エントリー当日のお礼メール'],
    '2': ['iv', '面接リマインド', '面接の数日前/前日のリマインドメール'],
    '3': ['brief', '説明会リマインド', '会社説明会前のリマインドメール'] };
  var r1 = ui.prompt('AIメール下書き', 'どのメール？ 1=サンクス / 2=面接リマインド / 3=説明会リマインド', ui.ButtonSet.OK_CANCEL);
  if (r1.getSelectedButton() !== ui.Button.OK) return;
  var k = kinds[String(r1.getResponseText() || '').trim()]; if (!k) { toast_('1〜3で指定してください'); return; }
  var r2 = ui.prompt('トーン', '例: 丁寧 / カジュアル / フォーマル / 親しみやすい（空欄=丁寧）', ui.ButtonSet.OK_CANCEL);
  if (r2.getSelectedButton() !== ui.Button.OK) return;
  var tone = String(r2.getResponseText() || '丁寧').trim() || '丁寧';
  var instruction = '採用担当として、応募者へ送る「' + k[2] + '」の日本語メール文面を作成してください。会社名は「' + cn + '」、トーンは「' + tone + '」。'
    + '差込タグ {氏名} {会社名} {職種} {ステージ} {日時} {形式} {面接官} {URL} を本文に適切に使う（実値ではなくこのタグのまま埋め込む）。'
    + '出力は1行目に「件名: 〜」、2行目以降に本文。署名は「' + cn + ' 採用担当」。記号の装飾や絵文字は使わない。';
  var out;
  try { out = geminiDraft_(instruction); } catch (e) { ui.alert(String(e)); return; }
  if (!out) { toast_('生成に失敗しました'); return; }
  var lines = out.split('\n'), subj = '', bodyStart = 0;
  for (var i = 0; i < lines.length; i++) { var m = lines[i].match(/^\s*件名[:：]\s*(.+)/); if (m) { subj = m[1].trim(); bodyStart = i + 1; break; } }
  var body = lines.slice(bodyStart).join('\n').trim();
  var sh = sheet_(SH.MAIL);
  var sc = { thanks: ['thanksSubj', 'thanksBody'], iv: ['ivSubj', 'ivBody'], brief: ['briefSubj', 'briefBody'] }[k[0]];
  if (subj) sh.getRange(MAIL_CELLS[sc[0]][0], MAIL_CELLS[sc[0]][1]).setValue(subj);
  if (body) sh.getRange(MAIL_CELLS[sc[1]][0], MAIL_CELLS[sc[1]][1]).setValue(body);
  ss_().setActiveSheet(sh);
  toast_(k[1] + ' のAI下書きを07_メール設定に反映しました（確認・微調整してください）');
}

/* ============================== 50_履歴書管理（書類回収：履歴書・職務経歴書） ============================== */

function buildDocsTab_() {
  var sh = sheet_(SH.CV);
  clearSheet_(sh);
  ensureGrid_(sh, 320, 13);
  var W = [30, 100, 90, 70, 110, 90, 80, 90, 110, 150, 150, 130];
  for (var i = 0; i < W.length; i++) sh.setColumnWidth(i + 1, W[i]);
  bandTitle_(sh, 1, 2, 12, '■ ' + companyName_() + '　書類回収管理（履歴書・職務経歴書）');

  var cfg = docsConfig_();
  var am = allMaster_(), H = am.H;
  var overall = {}, bySeg = {};
  DOC_TYPES.forEach(function (d) { overall[d.key] = { target: 0, collected: 0, due: 0 }; });
  var rows = [];
  am.rows.forEach(function (r) {
    var status = String(r[H['ステータス']] || '').trim();
    if (status === '見送り' || status === '辞退') return;
    var seg = String(r[H['区分']] || '').trim();
    if (!docsEnabledForSeg_(seg)) return;  // 書類回収OFFの区分は50タブに出さない
    if (!bySeg[seg]) { bySeg[seg] = {}; DOC_TYPES.forEach(function (d) { bySeg[seg][d.key] = { target: 0, collected: 0, due: 0 }; }); }
    var labels = {}, dueDocs = [];
    DOC_TYPES.forEach(function (d) {
      var st = docState_(r, H, seg, d, cfg);
      labels[d.key] = st.label;
      if (st.target) { overall[d.key].target++; bySeg[seg][d.key].target++; }
      if (st.target && st.collected) { overall[d.key].collected++; bySeg[seg][d.key].collected++; }
      if (st.due) { overall[d.key].due++; bySeg[seg][d.key].due++; dueDocs.push(d.key); }
    });
    rows.push([
      String(r[H['candidate_id']] || ''), String(r[H['氏名']] || ''), seg, String(r[H['職種']] || ''),
      String(r[H['現ステージ']] || ''), status,
      labels['履歴書'], labels['職務経歴書'],
      String(r[H['履歴書リンク']] || ''), String(r[H['職務経歴書リンク']] || ''),
      dueDocs.length ? ('要（' + dueDocs.join('・') + '）') : '-'
    ]);
  });
  rows.sort(function (a, b) {
    var ad = (String(a[10])[0] === '要') ? 0 : 1, bd = (String(b[10])[0] === '要') ? 0 : 1;
    if (ad !== bd) return ad - bd;
    return String(a[2]).localeCompare(String(b[2]));
  });

  var row = 3;
  // サマリ: 書類別(全体)
  row = subhead_(sh, row, '▎書類別 回収状況（対象＝その区分で回収が必要な候補・選考中）');
  var sumRows = DOC_TYPES.map(function (d) {
    var o = overall[d.key];
    return [d.key, o.target, o.collected, pct_(o.collected, o.target), o.due];
  });
  row = table_(sh, row, 2, ['書類', '対象', '回収済', '回収率', '督促要'], sumRows, [3, 4]);

  // サマリ: 区分×書類
  var segRows = [];
  Object.keys(bySeg).forEach(function (seg) {
    DOC_TYPES.forEach(function (d) {
      var o = bySeg[seg][d.key];
      if (o.target === 0 && o.collected === 0) return;  // その区分で不要な書類は省略
      segRows.push([seg, d.key, o.target, o.collected, pct_(o.collected, o.target), o.due]);
    });
  });
  if (segRows.length) {
    row = subhead_(sh, row, '▎区分別');
    row = table_(sh, row, 2, ['区分', '書類', '対象', '回収済', '回収率', '督促要'], segRows, [4, 5]);
  }

  // 本表
  row = subhead_(sh, row, '▎候補者別 書類回収（督促要を上に表示）');
  var hdr = ['ID', '氏名', '区分', '職種', '現ステージ', '選考状況', '履歴書', '職務経歴書', '履歴書リンク', '職経リンク', '督促'];
  var bodyRow = row;
  row = table_(sh, row, 2, hdr, rows.length ? rows : [['—', '', '', '', '', '', '', '', '', '', '']], []);

  // 条件付き書式: 督促列(M=col13)に"要"→赤 / 状態列(履歴書H=col9・職経I=col10)の"未回収"→薄赤
  if (rows.length) {
    var dueRange = sh.getRange(bodyRow + 1, 13, rows.length, 1);
    var docRange = sh.getRange(bodyRow + 1, 9, rows.length, 2);
    sh.setConditionalFormatRules([
      SpreadsheetApp.newConditionalFormatRule().whenTextStartsWith('要').setBackground('#F8D7DA').setFontColor(C.RED).setBold(true).setRanges([dueRange]).build(),
      SpreadsheetApp.newConditionalFormatRule().whenTextEqualTo('未回収').setBackground('#FCEFE6').setFontColor('#B45309').setRanges([docRange]).build(),
      SpreadsheetApp.newConditionalFormatRule().whenTextEqualTo('回収済').setFontColor('#1E6B2E').setRanges([docRange]).build()
    ]);
  }
  note_(sh, row + 1, 11, '回収済=リンク有 / 未回収=対象だが未取得（督促要） / 対象外=その区分で不要 or 任意 / 回収予定=選考途中設定で回収ステージ未到達。回収タイミングは 01_設定「必要書類・回収」で区分ごとに設定。リンクを入れると回収日が自動記録。');
}

/* ============================== ネクストアクション プレースホルダ ============================== */

function reservePlaceholders_() {
  var map = [
    [SH.NA, '■ ネクストアクション', '今後実装予定（期限切れSlackリマインド連動）']
  ];
  map.forEach(function (x) {
    var sh = ss_().getSheetByName(x[0]); if (!sh) return;
    clearSheet_(sh);
    sh.setColumnWidth(1, 30);
    for (var c = 2; c <= 9; c++) sh.setColumnWidth(c, 95);
    bandTitle_(sh, 1, 2, 9, x[1]);
    sh.getRange(3, 2).setValue(x[2]).setFontColor(C.SUB).setFontSize(11);
  });
}
