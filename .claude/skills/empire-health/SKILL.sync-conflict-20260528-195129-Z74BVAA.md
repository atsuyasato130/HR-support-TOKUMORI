---
name: empire-health
description: Tokumoriシステムの稼働状況を確認。「Tokumoriの状態確認」「エージェントは動いてる？」「ヘルスチェック」「システム確認」「empire status」で発火。
---

Tokumori Business Platform のヘルスチェックを実行する。

## 1. empire_os.py ステータス確認

```bash
cd '/Users/atsuyasato/Claude AI/ai-empire' && python3 core/infrastructure/empire_os.py status 2>/dev/null | head -40
```

取得できる情報:
- 各部門（hr_support/sales/rpo/hr_dept/management/quality）の稼働状態
- DEPARTMENTSに登録されたエントリポイントの存在確認

## 2. launchd ジョブ稼働確認

```bash
launchctl list | grep -E "tokumori|aiempire|hrbot"
```

期待される稼働ジョブ:
- `com.tokumori.orchestrator` — メインオーケストレーター
- `com.tokumori.sf-patrol` — SF パトロール
- `com.tokumori.dashboard` — ダッシュボード
- `com.tokumori.email-pipeline` — メールパイプライン
- `com.tokumori.slack` — Slackボット
- その他 `com.tokumori.*`

## 3. 直近ログ確認

```bash
ls -lt '/Users/atsuyasato/Claude AI/ai-empire/agents/logs/' 2>/dev/null | head -10
ls -lt '/Users/atsuyasato/Claude AI/ai-empire/logs/patrol/' 2>/dev/null | head -5
```

## 4. ダッシュボード稼働確認

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8889/ 2>/dev/null || echo "offline"
```

## 5. MCP接続確認

```bash
# hr-support MCP プロセス確認
ps aux | grep "mcp_salesforce_notion" | grep -v grep | head -3
# salesforce-dx MCP
ps aux | grep "salesforce/mcp" | grep -v grep | head -3
```

## 6. パトロール最新レポート

```bash
cat '/Users/atsuyasato/Claude AI/ai-empire/logs/patrol/'$(ls -t '/Users/atsuyasato/Claude AI/ai-empire/logs/patrol/' 2>/dev/null | head -1) 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'  overall: {d[\"overall_status\"]}, ok={d[\"summary\"][\"ok\"]}, warn={d[\"summary\"][\"warning\"]}, err={d[\"summary\"][\"error\"]}')" 2>&1
```

## 7. サマリー出力

以下のフォーマットで統合表示:

```
━━━━━━━━━━━━━━━━━━━━━━━━━
🩺 Tokumori ヘルスチェック — YYYY-MM-DD HH:MM
━━━━━━━━━━━━━━━━━━━━━━━━━

✅ 稼働中:
  - <service>: <status>

⚠️ 要確認:
  - <service>: <reason>

❌ 停止中:
  - <service>: <error>

【ダッシュボード】
  URL: http://localhost:8889/
  HTTP: <status_code>

【最新パトロール】
  overall: <status>
  ok/warn/err: <N/N/N>

【推奨アクション】
  <必要があれば>
```

## 失敗時の対処

| 問題 | 推奨対処 |
|---|---|
| empire_os.py が応答しない | `python3 core/infrastructure/empire_os.py status` を直接手動実行してエラー確認 |
| launchctlが何も返さない | `launchctl load ~/Library/LaunchAgents/com.tokumori.*.plist` で再ロード |
| ダッシュボードoffline | `bash start_dashboard.sh` で起動 |
| MCPプロセス停止 | Claude Code再起動を案内 |
| パトロール最新ログがない | `python3 agents/quality/patrol/agent.py --quick` 手動実行を提案 |

## 注意事項

- このスキルは read-only（状態確認のみ）。システム状態を変更しない
- 停止サービスの自動起動は行わない（ユーザー判断を仰ぐ）
