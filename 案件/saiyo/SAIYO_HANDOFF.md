# 自社採用管理シート（Tokumori）引き継ぎ

## 概要
ATSを使わず自社採用をGoogleスプレッドシートで一元管理する仕組み。将来は自社ATSへ移管する前提で正規化設計。

- **スプレッドシート**: `Tokumori 採用管理シート`
  - ID: `1dEGDtUAgoeWadUHorLMxhVr4BBNwyI01Gs2v6Pg834g`
  - URL: https://docs.google.com/spreadsheets/d/1dEGDtUAgoeWadUHorLMxhVr4BBNwyI01Gs2v6Pg834g/edit
- **bound script (Apps Script)**
  - projectId: `1e5h5YtPMb51FdL2aYqQ1SogfW0c9kN30oTNESJcrAVCvGQwBp92hn1sP`
  - URL: https://script.google.com/u/0/home/projects/1e5h5YtPMb51FdL2aYqQ1SogfW0c9kN30oTNESJcrAVCvGQwBp92hn1sP/edit
- **ローカルGAS正本**: `~/Claude AI/gas_saiyo_v1.js`（編集用）／`gas_saiyo_DEPLOYED.gs`（反映済コピー）
- **計画書**: `~/.claude/plans/lucky-snacking-stardust.md`

## 設計3原則
1. データ(設定/マスタ/面接)と表示(ダッシュボード)を分離。表示はGASが静的値で生成。
2. 位置参照禁止 → `headerIndex_()` でヘッダー名から列を引く（並べ替え耐性）。
3. ステージ・チャネルは `01_設定` の“行”。プルダウンは範囲参照で即時反映、表は🔄更新で再生成。

## タブ
- `00_README` 使い方 / `01_設定`（ステージ/チャネル/職種/メンバー/目標、各テーブルは専有列に配置）
- `10_候補者マスタ`（唯一の入力先・1行=1候補者） / `11_面接スケジュール`（1行=1面接）
- `21_中途`（稼働中ダッシュボード） / `20_統合`・`22〜24`・`30/31`・`40/50/60`（Phase2/3でプレースホルダ）

## メニュー（採用）
- 🔄 ダッシュボードを更新 = `refreshAll`（syncNextInterview + renderMidDash_）
- 📄 レポートを生成 = `generateReports`（renderReports_ → 60_レポート出力）
- ⚙️ 初期セットアップ/再構築 = `setupAll`（構造再構築。**データは消えないが、原則初回のみ**）
- `reseedSampleData`（メニュー外・初期化用。サンプル再投入）

## Phase 進捗
- **Phase 1 完了**: 設定/マスタ/面接/中途ダッシュボード + ブランドデザイン + サンプル。
- **中途ダッシュボードの詳細分析（追加要望対応済）**: サマリ(KPI+ファネル+目標進捗)の下に
  ①ステージ間歩留まり（前段比/累積/離脱）②月次コホート歩留まり（応募月別）③チャネル別 ④職種別+目標充足 ⑤見送り理由内訳。
- **レポート（追加要望対応済・中途のみ）**: `60_レポート出力` に `renderReports_` がGAS整形出力。
  月次(経営向け: サマリ前月比/目標達成/ファネル歩留まり/チャネルCVR・CPA/職種充足/所感Good課題Risk)・週次(担当向け: 今週の動き/来週面接/要対応NA/ファネル現況)・日次(本日面接/要対応)。配信(Slack/Gmail)は未実装=体裁固め優先。
  - レポート全区分版ロジック: `renderMonthlyReportAll_`/`renderWeeklyReportAll_`/`renderDailyReportAll_` + `buildCrossChannel_`/`insightsAll_`/`allMaster_`/`weeklyData_`、日付は `tokyoDayMs_`/`daysFromToday_`/`tokyoYM_`/`fmtD_`/`fmtDT_`。
- **Phase 2 完了**: 区分汎用化 `computeSegment_`/`renderSegmentDash_` → 21〜24 全区分ダッシュボード稼働。`renderAllDash_`=**20_統合**(全体KPI+区分別サマリ+5段正規化ファネル `normalizedFunnel_`/`finalGoal_`/`idxByType_`)。`renderChannelAnalysis_`/`renderJobAnalysis_`=**30/31**(全区分横断 `crossAgg_`、確定=accept/join到達でCPA算出)。`onEdit`+`applyStageValidationForRow_`=**現ステージを区分でフィルタ**。`renderReports_`は**全区分対応**(全区分サマリ+区分別ファネル歩留まり+全区分チャネルCVR/CPA+週次/日次は全区分横断)。一括再生成=`renderAllDashboards_`(refreshAll/setupAllが呼ぶ)。
  - 目標は種別ベースでマップ(内定目標→offer/承諾目標→accept/入社目標→join)。業務委託=契約(offer)止まり等でも自動対応。
  - ⚠️ `clearSheet_` は `setNumberFormat('General')` で%書式残骸をリセット必須(再描画でレイアウトが変わり旧%が残るため)。
- **未着手(Phase3残)**: レポートのSlack/Gmail配信・自動トリガー、カレンダー[ステイ中]、40_ネクストアクション、50_履歴書、exportJson。サンプルは中途のみ(新卒/業務委託/インターンはデータ投入待ち)。

## デザイン（Tokumoriブランド）
- アクセント=TOKUMORI Red `#AF322C`（タイトル帯・KPI主要数値・%列・バー）、構造=Black `#000000`（表ヘッダー）、ゼブラ`#F7F5F4`/罫線`#D9D9D9`/グリッドOFF。
- 定数は `var C` に集約。書式ヘルパー: `bandTitle_`/`kpiHero_`/`table_`/`sectionBand_`/`section_`。

## ⚠️ 重要な技術メモ
- **タイムゾーン**: スプレッドシートTZ=東京、`setValue(Date)`はUTC基準でシリアライズされる挙動。
  - 日付のみ → `d_()`（`Date.UTC`）でOK（月コホート集計は `getUTC*` + `ymKey_` + `nowTokyo_` で一貫）。
  - **時刻付き(面接日時)** → `dt_()`（`Date.UTC(...) - 9h`）で書くと東京時刻でそのまま表示される。
  - `setSpreadsheetTimeZone('Asia/Tokyo')` はMCP作成シートで効きづらい。シートTZはUI(ファイル→設定)で東京に設定済み。
- **デプロイ動線**: ローカル正本を`pbcopy` → Apps Scriptエディタを開く → Playwrightで `monaco.editor.getModels()[].setValue(clipboard)` 注入 → `Cmd+S` → 関数選択して実行。初回は権限承認（スコープ=スプレッドシート編集のみ）。
- 関数末尾`_`はApps Scriptの実行ドロップダウンに出ない（手動実行する関数は`_`なしで命名）。
- MCPの`read_google_spreadsheet`の日時レンダリングは実シート表示と一致（FORMATTED）。検証は実シートUIが真値。

## 次の一手（Phase2想定）
1. `renderMidDash_`を区分汎用化 → 22/23/24 を各ステージ定義で展開。
2. `20_統合`: 4区分を5段正規化で横断。
3. `30_チャネル分析`/`31_職種分析`タブへ詳細分析を独立配置（RPOの動的集計流用）。
