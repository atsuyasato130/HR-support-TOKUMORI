# FUSION 中途 HRMOS レポート/分析 自動化

新2タブ（**レポート出力**＝報告／**★歩留まり分析ダッシュボード**＝分析）は Python で生成する。
本フォルダはその自動実行一式。**全スクリプト検証済み**（手動実行で動作確認済み）。

## 構成
| ファイル | 役割 |
|---|---|
| `daily_run.py` | 毎日：★歩留まり分析ダッシュボード（②）を再生成 |
| `weekly_run.py` | 毎週水10:30：レポート出力（①）を再生成＋週次レポートをSlack配信（Block Kit＋QuickChartグラフ） |
| `com.tokumori.hrmos.daily.plist` | 日次 7:00 の launchd 定義 |
| `com.tokumori.hrmos.weekly.plist` | 週次 水曜 10:30 の launchd 定義 |
| 正本スクリプト | `~/Claude AI/build_hrmos_funnel_v2.py`（②）／`~/Claude AI/build_hrmos_report.py`（①） |

Slack配信先: チャンネル `C0A59L3LU12`（既存 `SLACK_BOT_TOKEN` 使用）。

---

## ✅ 旧GASトリガーの上書き問題：解消済み（2026-06-25）

clasp 再ログイン後、`gas_hrmos_funnel_v1.js`（=デプロイ済`コード.js`）の
`buildReportTabAuto` / `refreshWeeklyReportTab` を **no-op（`return;`）化して clasp push 済**。
→ 月曜/月次トリガーが発火しても**レポート出力を上書きしない**（トリガー削除も不要）。
`rebuildFunnelAnalysis`（旧・歩留まり分析用）はそのまま残置で無害（旧タブ非表示済）。

---

## 自動実行を有効化（スケジューラは Mac mini 推奨）

メモリ方針：自動化は **24h稼働の Mac mini に集約（MacBookは停止）**。
よって launchd は **mini 側に配置**するのが正。`hrmos_automation/` 一式を mini の `~/Claude AI/` 下へ置き：
```
cp "~/Claude AI/hrmos_automation/com.tokumori.hrmos.daily.plist"  ~/Library/LaunchAgents/
cp "~/Claude AI/hrmos_automation/com.tokumori.hrmos.weekly.plist" ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.tokumori.hrmos.daily.plist
launchctl load ~/Library/LaunchAgents/com.tokumori.hrmos.weekly.plist
```
※ mini はユーザー名/パスが異なる場合あり（plist内の絶対パスを mini 環境に合わせて修正）。

## 手動実行（いつでも）
```
cd "~/Claude AI" && python3 hrmos_automation/daily_run.py    # ②更新
cd "~/Claude AI" && python3 hrmos_automation/weekly_run.py   # ①更新＋Slack配信
```

## 注意
- Python は `/usr/bin/python3`（3.9・google/slack_sdk導入済）。
- 期間定義：週次＝前週木〜当週水。判定＝応募の前週比で 順調/要注意/要警戒（色バー）。
- べき等：何度実行しても対象タブのみ再描画（他タブ不変ゲートあり）。
