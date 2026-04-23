# GitHub ディレクトリ構成 — AI帝国建国ロードマップ

## 2系統の分離設計

```
GitHub
├── [Private Repo] hr-support-ai-internal          ← 業務運用リポジトリ
│   ├── README.md
│   ├── .env.example
│   ├── agents/                                     ← 11体のエージェント本体
│   │   ├── career_advisor/
│   │   ├── interview_master/
│   │   ├── post_interview_support/
│   │   ├── notion_agent/
│   │   ├── salesforce_agent/
│   │   ├── line_agent/
│   │   ├── slack_agent/
│   │   ├── google_agent/
│   │   ├── report_agent/
│   │   ├── coaching_agent/
│   │   ├── tldv_agent/
│   │   └── orchestrator/                           ← ⑫（開発中）
│   │       ├── task_decomposer.py                  ← タスク分解AI
│   │       ├── executor.py                         ← 実行AI
│   │       └── verifier.py                         ← 検証AI
│   ├── knowledge/                                  ← ドメイン知識ベース
│   │   ├── rpo/
│   │   │   ├── glossary.md                         ← RPO専門用語辞書
│   │   │   ├── workflows.md                        ← 業務フロー定義
│   │   │   ├── prompt_templates/                   ← RPO特化プロンプト
│   │   │   └── examples/                           ← 成功事例集
│   │   └── hrsupport/
│   │       ├── glossary.md
│   │       ├── workflows.md
│   │       ├── prompt_templates/
│   │       └── examples/
│   ├── monitoring_os/                              ← Monitoring OS（GAS）
│   │   ├── monitoring_os.gs
│   │   ├── bu_survey_analysis.gs
│   │   └── README.md
│   ├── integrations/                               ← 外部API連携
│   │   ├── mcp_salesforce_notion.py
│   │   ├── google_sheets_client.py
│   │   └── webhook_receiver.py
│   └── docs/
│       ├── agent_specs/                            ← 各エージェント仕様書
│       └── runbooks/                               ← 障害対応手順
│
└── [Private Repo] sato-personal-ai-assets          ← 個人資産リポジトリ
    ├── README.md
    ├── frameworks/                                 ← 外販可能な抽象フレームワーク
    │   ├── orchestration/                          ← マルチエージェントOSS化候補
    │   │   ├── orchestrator_template.py
    │   │   ├── prompt_chain_builder.py
    │   │   └── README.md
    │   ├── monitoring_os/                          ← Monitoring OS（業務情報除去版）
    │   │   └── monitoring_os_template.gs
    │   └── knowledge_format/                       ← ドメイン知識構造化テンプレ
    │       ├── knowledge_schema.md
    │       └── knowledge_loader.py
    ├── intelligence_db/                            ← 外販アセット: 学習ログ（匿名化）
    │   ├── success_patterns.jsonl
    │   └── failure_catalog.jsonl
    └── playbooks/                                  ← AI組織化プレイブック（外販コンテンツ）
        ├── phase1_monitoring.md
        ├── phase2_orchestration.md
        └── phase3_commercialization.md
```

---

## ドメイン知識（Knowledge）の構造化フォーマット

各 `knowledge/{domain}/` 配下のファイルは以下のスキーマで統一する。

### `glossary.md`
```markdown
# {Domain} 用語辞書

| 用語 | 定義 | 使用文脈 | エージェントへの注意点 |
|------|------|----------|----------------------|
| 直紹介 | 紹介会社を介さない直接採用 | RPO営業 | SFへの記録方法が異なる |
```

### `workflows.md`
```markdown
# {Domain} 業務フロー

## フロー名: {例: 面接後フォロー}

**トリガー:** 面接実施確認
**ステップ:**
1. TLDV文字起こし取得
2. 評価シートSF入力
3. 候補者フォローメール送信（24h以内）
4. Notionに議事録登録

**成功定義:** 上記4ステップが48h以内に完了
**担当エージェント:** Interview Master + Post Interview Support
```

### `prompt_templates/{task}.md`
```markdown
---
agent: {agent_name}
domain: {rpo|hrsupport}
task: {task_name}
version: 1.0.0
---

## System Prompt
{エージェントへのシステムプロンプト}

## User Prompt Template
{変数: {{candidate_name}}, {{job_title}} など}

## Output Format
{期待する出力形式}

## Example
### Input
{入力例}
### Output
{出力例}
```

---

## 2系統の分離ルール

| 項目 | hr-support-ai-internal | sato-personal-ai-assets |
|------|----------------------|------------------------|
| アクセス | 社内チームのみ | 個人（外販時はfork） |
| 機密情報 | 含む（SF ID等） | 含まない（抽象化済み） |
| デプロイ | 本番直結 | テンプレート・デモ用 |
| 更新頻度 | 毎日 | 四半期ごとの抽象化 |
| 外販可否 | 不可 | 可（ライセンス: MIT or 商用） |
