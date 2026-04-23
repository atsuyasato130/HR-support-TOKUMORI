# Monitoring OS v2.0 セットアップガイド

## 対象スプレッドシート
https://docs.google.com/spreadsheets/d/1g8PzcuPuUTTdO-kcSh4niuwfLw6d8zN8JQMZCrmyuH8/edit

---

## デプロイ手順（5分）

1. 上記SSを開く
2. メニュー → **拡張機能 → Apps Script**
3. 既存コードを全削除 → `monitoring_os_v2.gs` の内容を全貼り付け
4. 保存（Ctrl+S）
5. 関数を `setupAll` に選択 → **▶ 実行**
6. 初回は権限承認が出るので許可する
7. 完了（約30秒）

---

## セットアップ後のタブ構成

| タブ | 誰が使う | 書き込み |
|------|----------|----------|
| 🏠 HOME | 全員 | 読むだけ |
| 📊 Dashboard | 全員 | Manual KPI欄のみ手入力 |
| 🗺️ Roadmap | PM/開発者 | Status・担当者欄を更新 |
| 📋 Project Board | **全員** | 自由に追記・ステータス更新 |
| 🏢 BU Backlog | **全員** | 自由に課題起票 |
| 📝 Update_Log | システム | 手動書き込み不要 |
| 🤖 Agent Registry | 開発者 | エージェント追加時に更新 |
| 💡 Intel Log | 開発者/全員 | ログを積極的に記録 |

---

## dashboard_logger.py との互換性

`Update_Log` タブのフォーマットは **完全互換**。
既存の `dashboard_logger.py` はそのまま動作します。

```python
# 変更不要。今まで通り使えます
from utils.dashboard_logger import log_update
log_update(icon="🔧 修正", summary="...", targets="...", details="...")
```

---

## 毎時自動更新トリガーの設定（任意）

Apps Script エディタで `setupHourlyRefresh` を実行すると、
HOMEタブの最終更新時刻が毎時自動更新されます。
