# RPO 211/212 着地予想ロジック修正 — 引き継ぎ（→ macmini）

更新: 2026-06-10 / MacBook側Claude → macmini（このGASを元々編集・デプロイしていた環境）

## ★ 状態：コード修正は完了。macminiは「デプロイするだけ」★

- **デプロイ済みソースを取得済 → `~/Claude AI/gas_rpo_DEPLOYED.gs`（全コード）に修正を適用済み・構文チェック✅**。
- **ライブのApps Scriptプロジェクトはまだ未変更**（反映操作は中断したので元コードのまま）。
- macminiのタスク: **`gas_rpo_DEPLOYED.gs` の内容をApps Scriptプロジェクトに反映 → `rebuildAll` 実行 → 検証**。これだけ。

---

## 1. 対象・環境
- スプレッドシート: `https://docs.google.com/spreadsheets/d/1Jst9O1xcgDOgpRylhUIslnbLzgPZMk9zKy9W0NFyFtM/`
- タブ: **211_全体KPI** / **212_月別KPI**
- bound script「fusion Project」 scriptId `1YhFRJx8guwjUJjKWc_CsYHckB0rpSYSBQh0agdQA7L5ZiRLrs6J7FNsE`（拡張機能→Apps Script、ログインは atsuya_sato@tokumori.co.jp で編集者権限あり）
- **正本ファイル: `~/Claude AI/gas_rpo_DEPLOYED.gs`**（＝デプロイ版全文＋今回修正。ファイルは1ファイル `コード.gs` 相当・約173KB）
- 旧ローカル `~/Claude AI/gas_rpo_v2.js` は211/212生成コードが無い古い版＝**使わない**。`gas_rpo_DEPLOYED.gs` が最新正本。

## 2. 背景（なぜGAS修正なのか）
211/212は**デプロイ済みGASが静的値で生成**している（毎朝9時`rebuildAll`＆手動「全体再集計」で全上書き）。シートに数式を直接入れてもGAS実行で消えるため、修正はGASコード側が唯一の恒久策。デプロイ版には `renderOverviewAll`(211)/`renderMonthly`(212)/`_landingByPhase`(着地予想) が存在する（ローカル旧版には無かった）。

## 3. 適用済みの修正内容（`gas_rpo_DEPLOYED.gs`）
### (A) `function _landingByPhase(records, phases, targets)` を全面改修
- **305バグ修正**: 旧コードは現アクティブを段階へ寄せる際 `if (idx<0) idx=0` で**未マップを全部エントリーに加算**していた（エントリー着地が過大化＝305の主因）。→ **未マップは加算しない**。「一次後面談（人事）」は「一次面接【合格】」へ寄せる。
- **モデル変更**: 旧「累計実績＋手前アクティブ×通過率」は下流が上流を超える非整合があった。→ **現パイプライン・カスケード**（現在選考中の学生だけを実績通過率で各段階へ進める）に変更し、**単調非増加を保証**。
- ラダー = `main+pass+reserved`（予約も位置決めに含む）、**内定承諾は着地対象外**（着地は内定まで）。インターン・二次・最終も対象に含む。

### (B) `renderMonthly`（212）
- ハイライト帯の **「着地予想（承諾）」列を削除**（6→5列）。
- **「■ 着地予想（最終到達見込）」ブロックを削除**（承諾ベースのため非表示）。
- フェーズ別表:
  - **エントリー着地予想＝日割りペース**（`当月実績 ÷ 経過日数 × 当月日数`、当月のみ。`new Date()`/`monthKey`使用）。
  - **予約フェーズ・内定承諾の着地予想は「-」**。
  - **「着地予想/目標」＝着地予想 ÷ 当月目標**（旧: 累計目標で割っていたのを是正）。

### (C) `renderOverviewAll`（211）
- ハイライト帯の **「着地予想（承諾）」列を削除**（6→5列）。
- **「■ 着地予想（過去実績ベース）」の承諾合計ブロック（確定/見込/合計/期間目標/達成見込率）を削除**し、フェーズ別内訳テーブルのみ残す。

※ `const landing = aggregateLanding(...)` は211/212で未使用化したが残置（無害）。Slack/月次Docレポート側の `aggregateLanding` 使用は変更なし。

## 4. デプロイ手順（macmini）
**いずれか**：
- **clasp**: `clasp login`（再認証。invalid_grant対策）→ `.clasp.json` に scriptId 設定 → `clasp push`（`gas_rpo_DEPLOYED.gs` を `コード.gs` として push）。
- **Playwright（実績手法）**: エディタを開く → クリップボードに `pbcopy < gas_rpo_DEPLOYED.gs` → `browser_run_code_unsafe` で monaco frame の `getModels()[0].setValue(await navigator.clipboard.readText())` → `Cmd+S` 保存 → `cloud_done` 確認。（Base64 inject手法はメモリ `project_rpo_shinsotsu_sheet` 参照）

反映後 **メニュー「RPO」→「全体再集計」(`rebuildAll`)** を実行（211/212再生成）。

## 5. 検証（`token_sheets.json` でSheets API読取）
- 212 フェーズ別: **エントリー着地＝当月実績の日割りペース**（例 当月56・10日経過なら≈168）。日付/エントリーで変動。
- 着地予想が**ファネル下流で単調非増加**。インターン・二次・最終・内定も値（現状0.0）が出る。**予約・内定承諾は「-」**。
- **着地予想/目標＝着地÷当月目標**（100%超で上回り表示）。
- **211・212とも「着地予想（承諾）」列が無い**。212の「■着地予想（最終到達見込）」ブロックが無い。211の承諾合計ブロックが無い。

## 6. 注意
- 毎朝9時 `rebuildAll` トリガー稼働中。生データ `学生情報一覧raw`（かんりくんCSV取込先）が空のまま走ると全0になる（2026-06-10朝に発生・CSV再取込で復旧済）。
- デプロイは bound script オーナー権限環境で（atsuya_sato@tokumori.co.jp で編集者確認済）。
- MacBook側で212へ暫定で入れたシート数式・ヘルパー列(W:AD)・拡張列(34列)が残っているが、**`rebuildAll` 実行で正規の静的値に上書きされ消える**ので放置でOK。
- 検証用Sheets API: `~/Claude AI/tokumori/agents/hr_support/config/token_sheets.json`（spreadsheetsスコープ）。
