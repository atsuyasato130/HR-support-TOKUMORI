# HR Support インサイドセールス管理ツール 設計書

**作成日**: 2026-04-23
**対象事業**: HR support（新卒採用紹介）
**目的**: SF上でBDR/アウトバウンド営業リスト・ステータス・アポ率・自動情報補填を一気通貫管理
**方針**: DATAZORA/KIJI購入せず自社構築（KIJI相当機能をHR用途に絞って実装）
**背景**: 岡見悠平氏（クライアント）とSora Takeuchi氏（DATAZORA事業部長）の打ち合わせ（tldv meeting_id: 69e72779af3e9800132dd30b, 2026-04）を受けた要件反映

---

## 1. システム全体構成

```
┌───────────────────────────────────────────────┐
│ 1. データ収集層（GCP Cloud Run）                 │
│    - gBizINFO API ポーラー                      │
│    - 年金機構CSV 月次ダウンローダ                 │
│    - マイナビ新卒スクレイパー（Playwright）        │
│    - PRTimes RSSサブスクライバ                   │
│    - firecrawl連携（HP/部署情報抽出）             │
│    - Claude API呼び出し（課題抽出・スクリプト生成）│
└───────────────────────────────────────────────┘
                 ↓ JSONL / CSV
┌───────────────────────────────────────────────┐
│ 2. データ統合層（Supabase Postgres）            │
│    - 法人マスター（法人番号キー）                 │
│    - 求人／ニュース／人事異動／部署／従業員推移    │
│    - dbtでLeadScore事前計算                      │
└───────────────────────────────────────────────┘
                 ↓ Apex Callout / SOQL
┌───────────────────────────────────────────────┐
│ 3. Salesforce（業務OS）                        │
│    - Lead / Account + カスタムObj 5種           │
│    - Lightning Web Component: 部署直通リスト等  │
│    - Flow: 人事異動→Task自動生成                 │
│    - Apex: Claude API連携でトークスクリプト     │
└───────────────────────────────────────────────┘
                 ↓
┌───────────────────────────────────────────────┐
│ 4. IS運用層                                    │
│    - Kanban（Status遷移）                       │
│    - 1クリック架電（MiiTel連携）                 │
│    - アポ率・担当者別・時間帯別 ダッシュボード     │
└───────────────────────────────────────────────┘
```

## 2. データソース戦略

### 採用データソース一覧

| データ | ソース | 取得方法 | 更新頻度 | コスト |
|---|---|---|---|---|
| 法人マスター | gBizINFO API（経産省） | REST API | 週次 | 無料 |
| 資本金・代表・設立日 | gBizINFO / EDINET | REST API | 月次 | 無料 |
| 被保険者数 | 年金機構 適用事業所CSV | HTTPダウンロード | 月次 | 無料 |
| 新卒求人 | マイナビ新卒 / リクナビ新卒 | Playwright | 週次 | 実装コスト |
| 中途求人 | Indeed API | REST API | 日次 | 応相談 |
| 企業ニュース | PRTimes RSS/検索 | RSS | 日次 | 無料 |
| 人事異動 | PRTimes「人事異動」タグ | RSS+LLM分類 | 日次 | 従量（Claude） |
| 部署情報 | 各社HP | firecrawl MCP | 四半期 | 月5-10万 |
| 役員情報 | HP / EDINET有価証券報告書 | firecrawl/EDINET | 四半期 | 無料 |

### 岡見さんターゲットに絞った収集量見積

- 全法人: 577万社
- → マイナビ掲載企業に絞る: **約3万社**
- → 年間採用300名以下 × 新卒求人あり: **約1.5万社**

**結論**: 全量577万社は不要。マイナビ掲載 × 年金機構データ × gBizINFO の3軸ANDで1-3万社に絞れば、スクレイピング負荷も運用コストも現実的。

## 3. GCP Cloud Run アーキテクチャ

### サービス構成（マイクロサービス方式）

| サービス | 役割 | トリガー | 言語 |
|---|---|---|---|
| `gbizinfo-ingester` | gBizINFO API取得 → Supabase投入 | Cloud Scheduler 週次 | Python |
| `nenkin-ingester` | 年金機構CSV取得 → 差分適用 | Cloud Scheduler 月次 | Python |
| `mynavi-scraper` | マイナビ新卒クローリング | Cloud Scheduler 週次 | Python + Playwright |
| `prtimes-subscriber` | PRTimes RSS購読・人事異動判定 | Pub/Sub + Cloud Scheduler 日次 | Python |
| `hp-enricher` | 個別企業HPのfirecrawlスクレイプ | Pub/Sub オンデマンド | Python |
| `llm-scorer` | Claude APIで課題抽出・LeadScore算出 | Pub/Sub | Python |
| `sf-syncer` | Supabase → Salesforce Upsert | Cloud Scheduler 日次 + Webhook | Python (simple-salesforce) |

### 認証・秘匿情報
- Secret Manager: `DATAZORA_LIKE/` 配下に各APIキー
- Service Account: `ds-hr-insideservice@<project>.iam.gserviceaccount.com`

### データフロー例（人事異動検知 → SFタスク生成）
```
PRTimes RSS → prtimes-subscriber（Cloud Run）
  → 「人事異動」タグ付きRelease検出
  → Claude APIで本文から「新任部長」「部署」「会社名」抽出
  → 法人番号に名寄せ（gBizINFO検索）
  → Supabase personnel_change テーブルに挿入
  → Pub/Sub: `personnel-change-detected` publish
  → sf-syncer サブスクライブ
  → Salesforce REST API: Account.personnel_change_count +1
  → Flow: Task生成「○○社の新任人事部長へ再アプローチ」
```

## 4. データ統合層（Supabase Postgres）

### テーブル設計

```sql
-- 法人マスター
CREATE TABLE companies (
  corporate_number      TEXT PRIMARY KEY,  -- 法人番号13桁
  company_name          TEXT NOT NULL,
  company_name_kana     TEXT,
  address               TEXT,
  prefecture            TEXT,
  established_at        DATE,
  representative        TEXT,
  capital               BIGINT,
  revenue               BIGINT,
  listed_status         TEXT,              -- 上場/非上場/廃業
  industry_l            TEXT,              -- 業種大分類
  industry_m            TEXT,              -- 業種中分類
  industry_s            TEXT,              -- 業種小分類
  insured_count         INTEGER,           -- 被保険者数（年金機構由来）
  insured_count_updated TIMESTAMPTZ,
  employee_count        INTEGER,
  homepage_url          TEXT,
  activity_tags         TEXT[],            -- 新製品開発/DX推進等
  kiji_equivalent_source TEXT,             -- 情報源の引用URL
  updated_at            TIMESTAMPTZ DEFAULT NOW()
);

-- 被保険者数の月次推移（グラフ用）
CREATE TABLE insured_count_history (
  corporate_number TEXT REFERENCES companies(corporate_number),
  snapshot_month   DATE,
  insured_count    INTEGER,
  PRIMARY KEY (corporate_number, snapshot_month)
);

-- 求人情報
CREATE TABLE job_postings (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  corporate_number TEXT REFERENCES companies(corporate_number),
  media            TEXT,                    -- mynavi/rikunabi/indeed
  job_title        TEXT,
  job_type         TEXT,                    -- 新卒/中途/アルバイト
  salary_min       INTEGER,
  salary_max       INTEGER,
  posted_at        DATE,
  source_url       TEXT,
  ingested_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ニュース
CREATE TABLE company_news (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  corporate_number TEXT REFERENCES companies(corporate_number),
  published_at     DATE,
  title            TEXT,
  category_tags    TEXT[],                  -- 人事異動/新製品/資金調達
  summary          TEXT,                    -- Claude要約
  source           TEXT,                    -- PRTimes/EDINET/HP
  source_url       TEXT
);

-- 人事異動
CREATE TABLE personnel_changes (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  corporate_number TEXT REFERENCES companies(corporate_number),
  person_name      TEXT,
  role_title       TEXT,                    -- 人事部長/取締役等
  department       TEXT,
  change_type      TEXT,                    -- 新任/継続/退任
  changed_at       DATE,
  source_url       TEXT
);

-- 部署情報
CREATE TABLE departments (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  corporate_number TEXT REFERENCES companies(corporate_number),
  department_name  TEXT,
  department_tag   TEXT,                    -- 人事/総務/営業/研究開発
  manager_name     TEXT,
  direct_phone     TEXT,
  email            TEXT,
  address          TEXT,
  source_url       TEXT,
  updated_at       TIMESTAMPTZ DEFAULT NOW()
);

-- 事前計算済LeadScore
CREATE TABLE lead_scores (
  corporate_number TEXT PRIMARY KEY REFERENCES companies(corporate_number),
  total_score      INTEGER,                 -- 0-100
  insured_growth   INTEGER,                 -- 被保険者数増加率スコア
  job_posting      INTEGER,                 -- 求人出稿スコア
  news_activity    INTEGER,                 -- ニュース頻度スコア
  tag_match        INTEGER,                 -- 事業タグ一致スコア
  target_match     BOOLEAN,                 -- 岡見さんターゲット条件合致
  calculated_at    TIMESTAMPTZ DEFAULT NOW()
);
```

## 5. Salesforce オブジェクト設計

### カスタムフィールド（Lead / Account 共通）

| API Name | Type | 由来 | 用途 |
|---|---|---|---|
| `Corporate_Number__c` | Text(13), External ID | gBizINFO | 名寄せキー |
| `Insured_Count__c` | Number | 年金機構 | 実働規模 |
| `Insured_Growth_Rate__c` | Percent | 計算 | 成長度 |
| `Activity_Tags__c` | Multi-Picklist | 各種 | 事業タグ |
| `Industry_L__c` / `Industry_M__c` / `Industry_S__c` | Picklist×3 | gBizINFO | 業種3階層 |
| `Listed_Status__c` | Picklist | gBizINFO | 上場区分 |
| `Last_Sync_At__c` | DateTime | sf-syncer | 同期タイムスタンプ |
| `Lead_Score__c` | Number | Supabase計算済 | スコア |
| `Target_Match__c` | Checkbox | 計算 | ターゲット条件合致 |
| `HP_URL__c` | URL | gBizINFO/HP | HPリンク |
| `Memo_Talk_Script__c` | Long Text | Claude | 自動生成スクリプト |

### カスタムオブジェクト

```
KIJI_Department__c       （Account子）
  - Account__c (Lookup)
  - Department_Name__c (Text)
  - Department_Tag__c (Picklist: 人事/総務/営業...)
  - Manager_Name__c (Text)
  - Direct_Phone__c (Phone)
  - Email__c (Email)
  - Address__c (Text)
  - Source_URL__c (URL)

KIJI_Officer__c          （Account子）
  - Account__c, Person_Name__c, Role_Title__c, Department__c, Source_URL__c

KIJI_Job_Posting__c      （Account子）
  - Account__c, Media__c, Job_Title__c, Job_Type__c, Salary_Min__c, Salary_Max__c, Posted_Date__c, Source_URL__c

KIJI_Company_News__c     （Account子）
  - Account__c, Published_Date__c, Title__c, Category_Tags__c(MSP), Summary__c(LongText), Source__c, Source_URL__c

KIJI_Personnel_Change__c （Account子）
  - Account__c, Person_Name__c, Role_Title__c, Department__c, Change_Type__c(Picklist), Changed_Date__c, Source_URL__c
```

### Lead Status / Path
```
未着手 → 架電中 → 接続済 → 担当者不在 → 再架電予定
       → アポ獲得 ↗
       → 失注  → 失注理由（ピックリスト）
       → 却下（ターゲット外）
```

### Lightning Web Components

| 名称 | 配置 | 役割 |
|---|---|---|
| `kijiDepartmentList` | Accountページ | 部署直通リスト＋1クリック架電ボタン |
| `kijiEmployeeTrend` | Accountページ | 被保険者数月次推移グラフ（Chart.js） |
| `kijiCompanyNewsFeed` | Accountページ | ニュース時系列表示 |
| `kijiTalkScriptGenerator` | Leadページ | Claude API呼出でトークスクリプト生成 |

### Flow
- **Flow: 人事異動検知**
  - トリガー: `KIJI_Personnel_Change__c` insert
  - 判定: Change_Type = 新任 AND Department = 人事
  - アクション: 親Account担当者に Task 作成（「新任人事部長へ架電」、期限=翌営業日）
- **Flow: 求人新規検知**
  - トリガー: `KIJI_Job_Posting__c` insert
  - 判定: Job_Type = 新卒 AND Posted_Date = TODAY
  - アクション: LeadScore再計算トリガー + Task生成
- **Flow: 再架電リマインダ**
  - トリガー: Lead Status = 担当者不在 + 3日経過
  - アクション: Task「再架電」生成

### Apex / Webhook
- `DatazoraLikeWebhookController`: Supabaseからの人事異動Webhook受信
- `TalkScriptGenerator.cls`: Claude API呼出でトークスクリプト生成（非同期）
- `LeadScoreCalloutBatch`: 週次でSupabaseから最新スコア取得してLead/Account更新

## 6. Lead Scoring ロジック

```python
# llm-scorer サービス内
def calculate_lead_score(company):
    score = 0

    # 被保険者数増加率（直近3ヶ月 vs 前年同月）
    if company.insured_growth_rate >= 0.10:   score += 25
    elif company.insured_growth_rate >= 0.05: score += 15
    elif company.insured_growth_rate >= 0.02: score += 8

    # 新卒求人出稿（直近90日）
    if company.new_grad_postings >= 5: score += 20
    elif company.new_grad_postings >= 1: score += 10

    # ニュース頻度（直近90日）
    score += min(company.news_count_90d * 2, 15)

    # 事業タグ一致（新製品開発/DX推進/組織改革意欲）
    match_tags = set(company.activity_tags) & TARGET_TAGS
    score += len(match_tags) * 5

    # ターゲット条件（年間採用300名以下・ベンチャー/中小）
    if 10 <= company.insured_count <= 2000:  score += 15
    if company.listed_status == "非上場":     score += 5

    return min(score, 100)
```

## 7. ロードマップ（Phase 1-4）

### Phase 1（1-2週）: 最小限のIS管理ツール
**目標**: 社内リスト + gBizINFO補填で SF Leadが回る状態
- [ ] SFカスタムオブジェクト5種、カスタムフィールド作成（Metadata API deploy）
- [ ] Lead Status / Path / ListView 設定
- [ ] gbizinfo-ingester Cloud Run 実装・デプロイ
- [ ] sf-syncer Cloud Run 実装・デプロイ
- [ ] 社内リストCSV投入（法人番号で名寄せ）
- [ ] Report: 架電数/接続数/アポ数/アポ率 by 担当者

### Phase 2（2-4週）: 求人・被保険者数連携
- [ ] nenkin-ingester 実装
- [ ] mynavi-scraper 実装（法的リスク調査→Indeed API併用検討）
- [ ] `lead_scores` テーブル更新ロジック
- [ ] `kijiEmployeeTrend` LWC 実装
- [ ] ターゲット条件合致 Lead の自動キュー投入Flow

### Phase 3（3-4週）: 自動化・通知
- [ ] prtimes-subscriber 実装
- [ ] 人事異動検知 + Task自動生成Flow
- [ ] Slack通知: 「ターゲット企業で人事異動」
- [ ] MiiTel/Dialpad 連携で1クリック架電
- [ ] アポ率ダッシュボード（時間帯別・曜日別ヒートマップ）

### Phase 4（4-6週）: AI高度化
- [ ] hp-enricher 実装（firecrawl + 部署情報抽出）
- [ ] `kijiDepartmentList` LWC 実装
- [ ] `TalkScriptGenerator` Apex + Claude API実装
- [ ] 課題抽出・提案メール自動生成

## 8. 技術スタック

| 領域 | 採用技術 | 理由 |
|---|---|---|
| スクレイピング | Python + Playwright | JavaScript重いサイト対応 |
| 軽量スクレイピング | firecrawl MCP | 既存インフラ活用 |
| バッチ実行 | Cloud Run + Cloud Scheduler | 従量課金・スケーラブル |
| イベント駆動 | Cloud Pub/Sub | 疎結合・再処理容易 |
| データ保存 | Supabase Postgres | 既存HR supportインフラと親和 |
| SF連携 | simple-salesforce (Python) | バッチ向け |
| LWC・Apex | Salesforce Metadata API | 既存SF orchestrator準拠 |
| LLM | Claude Opus 4.7 / Haiku 4.5 | 課題抽出=Opus、分類=Haiku |
| 秘匿情報 | GCP Secret Manager | IAM制御 |
| 監視 | Cloud Logging + Sentry | エラー可視化 |

## 9. コスト試算

### 初期構築（Phase 1-4合計）
| 項目 | 工数 | 金額換算 |
|---|---|---|
| SFメタデータ設計・deploy | 20h | - |
| Cloud Run 7サービス実装 | 60h | - |
| Supabase テーブル・dbt | 15h | - |
| LWC 4コンポーネント | 30h | - |
| Flow / Apex | 25h | - |
| **合計** | **150h** | **≒ 120万円**（内製） |

### 月次運用（Phase 4完了後）
| 項目 | 金額 |
|---|---|
| GCP Cloud Run | 5,000円 |
| GCP Cloud Scheduler | 100円 |
| Supabase Pro | 3,200円 |
| firecrawl MCP | 既存（0円増） |
| Claude API（課題抽出+スクリプト） | 30,000円 |
| **合計/月** | **約4万円** |

### KIJIとの比較
| 項目 | KIJI | 自社構築 |
|---|---|---|
| 初期 | 0円 | 120万円 |
| 年間運用 | 180万円 | 48万円 |
| **3年累計** | **540万円** | **264万円** |
| 資産化 | なし（解約で消失） | 社内ノウハウ・他事業展開可 |

## 10. リスク・代替案

| リスク | 対策 |
|---|---|
| マイナビスクレイピングの規約違反 | Indeed API / ハローワークAPI / ECナビ等へ切替 |
| 部署直通番号の取得精度 | firecrawl + LLMでHP構造解析、不足時KIJIスポット活用 |
| 年金機構データの更新遅延 | 被保険者数は月次でOKと割り切る |
| Claude APIコスト超過 | バッチ化・キャッシュ・分類はHaikuに委譲 |
| SF APIコール上限 | バルクAPI使用、夜間バッチ化 |
| KIJIとの機能差 | Phase 4時点で追いつける。途中でKIJI 1ヶ月契約で繋ぎも可 |

## 11. 5月中判断への対応

- **Phase 1を2週間で完遂**（5月初旬）→ 社内リストでSF運用開始
- 効果検証（アポ率改善）を5月中旬まで
- 5月末時点の判断基準:
  - Phase 1でアポ率が 営業代行相当（10-15件）に届くか
  - 届かなければ KIJI 3日トライアル → 1ヶ月契約で繋ぎ、Phase 2-4を継続開発

## 12. 未決事項

- [ ] マイナビスクレイピングの法的判断（代替データソース候補確定）
- [ ] 社内既存リストのフィールド構成ヒアリング
- [ ] SF Sandbox のアクセス権限
- [ ] MiiTel / Dialpad のどちらと連携するか
- [ ] GCP プロジェクトの既存利用 or 新規作成
- [ ] Supabase プロジェクトの既存利用 or 新規作成
- [ ] スクレイピングの巡回頻度（サイト負荷とのバランス）
- [ ] 個人情報（直通電話・担当者名）の SF 上の扱い・権限セット

## 付録: 参考リンク

- KIJI公式: https://www.kiji.app/
- gBizINFO: https://info.gbiz.go.jp/
- 年金機構 適用事業所検索: https://www2.nenkin.go.jp/do/search_section/
- PRTimes RSS: https://prtimes.jp/rss/
- tldv meeting: https://tldv.io/app/meetings/69e72779af3e9800132dd30b/
