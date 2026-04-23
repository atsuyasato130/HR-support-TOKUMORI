# _experimental/ — 未稼働エージェント部門

ここに配置されている部門エージェントは **骨格のみ実装済み・本稼働していません**。
本稼働が確定した段階で `agents/` 直下に昇格させてください。

## 現在の内容

| 部門 | 状態 | 備考 |
|---|---|---|
| executive/ | 骨格 | ai_trend / approval / pl / strategy / team_health |
| organization/ | 骨格 | kpi / onboarding / recruiting / team_pulse |
| hr_dept/ | 骨格 | intern_hiring / contractor_hiring / employee_hiring |
| rpo/ | 骨格 | cs |
| management/ | 骨格 | legal / accounting |

## 昇格手順

1. 部門フォルダを `agents/<department>/` へ `mv`
2. `orchestrator.py` 内の import を `agents._experimental.<dept>.` → `agents.<dept>.` に置換
3. `knowledge/hr_support/AGENT_MANIFEST.json` に登録
4. 該当する `scripts/launchd/` plist を用意（必要なら）

## 非推奨事項

- `_experimental/` 配下は本番ワークロードから呼び出さないこと
- 実験段階のロジックが紛れ込むため、本稼働コードとの import 結合を避ける
