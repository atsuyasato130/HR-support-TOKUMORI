# HRサポート AI エージェントシステム 構成図

## システム全体図

```mermaid
flowchart TD
    CA["👤 キャリアアドバイザー（CA）"]

    subgraph INPUT["📥 インプット"]
        tldv["🎙️ tldv\n面談録音・議事録"]
        memo["📝 面談メモ\n手入力テキスト"]
        company["🏢 企業名\n入力"]
    end

    subgraph MAIN["🖥️ Claude Code / AI エージェント基盤\nmain.py（メニュー形式で起動）"]
        direction TB

        subgraph GROUP1["🎓 学生支援"]
            A1["① ES・面接対策\nガクチカ/自己PR/志望動機を\n対話形式で深掘り→ES文章を生成"]
            A2["② 就活軸深掘り\n就活軸を言語化・\nブラッシュアップ"]
        end

        subgraph GROUP2["📊 情報管理・記録"]
            A8["⑧ Salesforce記載\ntldv議事録→学生情報・\n活動記録を自動登録"]
            A9["⑨ tldv内容確認\n議事録詳細表示・\nClaude分析"]
        end

        subgraph GROUP3["💬 コミュニケーション生成"]
            A6["⑥ Lステップ文章生成\n学生へのLINEメッセージを\n6シーン対応で自動生成"]
            A11["⑪ 企業紹介文生成\nNotionDB→LINE送信用\n紹介文を一括生成"]
            A10["⑩ 選考進捗Slack共有\nSalesforceのパイプラインを\nSlackスレッドに投稿"]
        end

        subgraph GROUP4["📋 レポート作成"]
            A7["⑦ 所感フォーマット作成\n面談メモ→学生所感レポートを\n自動生成・保存"]
        end

        subgraph COMING["🚧 開発中"]
            A3["③ クロージングプラン"]
            A4["④ 企業レコメンド"]
            A5["⑤ リマインド通知"]
        end
    end

    subgraph EXT["🔗 外部サービス連携"]
        SF["☁️ Salesforce\n学生DB・活動記録\n（PersonAccount）"]
        NOTION["📓 Notion\n企業DB\n（説明会日程・選考フロー）"]
        SLACK["💬 Slack\n選考進捗・チーム共有"]
        LINE["📱 Lステップ（LINE）\n学生へのメッセージ配信"]
        SHEETS["📊 Google Sheets\nLステップ入力フォーム"]
    end

    AI["🤖 Claude API\n（Anthropic）\n自然言語処理エンジン"]

    CA --> INPUT
    tldv --> A8
    tldv --> A9
    memo --> A1
    memo --> A2
    memo --> A7
    company --> A11

    A8 --> SF
    A10 --> SF
    A10 --> SLACK
    A11 --> NOTION
    A11 --> LINE
    A6 --> LINE
    A8 --> SHEETS

    MAIN --> AI
    AI --> MAIN
```

---

## エージェント一覧（詳細）

| No. | エージェント名 | 入力 | 出力 | 連携先 |
|-----|-------------|------|------|--------|
| ① | ES・面接対策 | 面談メモ・対話 | ES文章 | - |
| ② | 就活軸深掘り | 面談メモ・対話 | 就活軸文章 | - |
| ⑥ | Lステップ文章生成 | 学生情報・シーン選択 | LINEメッセージ | Lステップ |
| ⑦ | 所感フォーマット作成 | 面談メモ | 所感レポート | - |
| ⑧ | Salesforce記載 | tldv議事録 | Account・Task登録 | Salesforce |
| ⑨ | tldv内容確認 | tldv URL/ファイル | 議事録分析 | tldv |
| ⑩ | 選考進捗Slack共有 | - | Slackスレッド投稿 | Salesforce・Slack |
| ⑪ | 企業紹介文生成 | 企業名 | LINE用紹介文 | Notion |

---

## データフロー（面談後の典型的な使い方）

```
面談（tldv録音）
    ↓
⑨ tldv内容確認 → 議事録を素早く確認・要約
    ↓
⑧ Salesforce記載 → 学生情報・活動記録を自動登録（手入力ゼロ）
    ↓
⑦ 所感フォーマット → 面談所感レポートを自動生成
    ↓
⑥ Lステップ文章生成 → フォローLINEメッセージを生成
    ↓
⑩ 選考進捗Slack共有 → チームへ進捗を自動通知
```
