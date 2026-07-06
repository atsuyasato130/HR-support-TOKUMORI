# SF 企業（クライアント）分離 実装計画 v1（共有用）

> 作成: 2026-06-25 / 対象: Salesforce 本番組織 tokumori-watanabe
> ステータス: **計画承認済み・実装未着手**（full sandbox リハーサル前提）
> 方針: 案B（企業を専用オブジェクト＋専用タブへ）の **ゼロデータロス／アーカイブ方式** 確定版
> 関連: 詳細背景は `SF_企業移管_案B_移行設計書_v1.md`

---

## この計画のねらい（背景）

現状、Salesforce の Account に「企業（クライアント・**212社**・Business Account）」と「求職者（候補者・**16,167件**・Person Account）」が RecordType で混在し、同じ Account タブに同居している。**企業だけを専用タブに切り出したい**。

事前調査で確定した重要事実:

- **全体KPIの数値は企業Accountを経由しない**。売上・件数・ファネルは `pipeline__c.status__c × EffectiveUnitPrice__c` と候補者側 `IsPersonAccount=true` で完結（JobOfferKpiController / SoukyakuKpiController）。企業Accountは「企業名ラベルの表示」にしか使われていない。→ **企業を移しても全体KPIはズレない**。
- データ消失の本丸は「**旧Client Accountの物理削除**」だけ。子オブジェクトの削除挙動:
  - ③ JobOfferSlip__c(159件) / ④ event__c(250件) … Master-Detail・cascade=true → 親削除で**連鎖削除**
  - ① pipeline__c(5,586件) … Lookup・SetNull → 親削除で**孤児化**
  - ② attendance__c(16,546件) … Lookup・Restrict → 子がいると**削除がブロック**
- **求職者(Person Account)は一切触らない・移さない・削除しない**。企業Accountとの親子関係も無い（連鎖経路ゼロ）ため、求職者情報は構造的に安全。

**理想 = 「タブは分けるが、KPI・リレーション・データは今と同じ状態」。**

→ 採用方針: **アーカイブ方式**。旧Client Accountを削除せず「アーカイブ（非表示・不活性化）」して温存する。削除しないので cascade が永遠に発火せず、③④のMD子は旧Accountにぶら下がったまま生存し、再構築が不要。**孤児化・KPIズレ・データ消失の3懸念がすべて構造的にゼロ**になる。

---

## 確定した設計判断

| # | 論点 | 決定 |
|---|---|---|
| 1 | ③④ の Master-Detail の扱い | **方式X**：Company__c へ Lookup を新設し、旧MDは温存 |
| 2 | 企業のタブ | **単独カスタムタブ**（現行 Lightning App のナビに追加） |
| 3 | 旧 Client Account | **削除せずアーカイブ**（新規 `Archived__c` チェックボックスで非表示化） |
| 4 | 企業ごとの売上合計 | Company__c でも表示する → **Apexで集計を再実装**（Roll-Up SummaryはLookup親では作れないため） |

---

## 目指す最終状態

```
求職者(16,167) : Account のまま 100%不変（タブ・データ・KPIすべて今と同じ）
企業(212)      : ①Account上に温存（Archived__c=trueで非表示） ②新Company__cにコピーして専用タブで運用
子オブジェクト  : 全件生存。①②はCompany__cへLookup移送、③④は旧Accountに残存（cascade回避）
全体KPI        : 数値不変（企業名ラベル参照のみCompany__cへ張替）
企業別売上     : Company__c上にApex集計で再現
```

---

## アーカイブ機構（確定）

既存に企業の不活性を表す空きフラグは無い（GfaActive__c / CS_Capacity_Status__c は212社すべてnull＝未使用、ListedStatus__c は上場区分で用途固定）。

→ **新規 `Archived__c`（Checkbox, default=false）を Account に追加**。RecordType退避案より既存運用（ListView 113件・FlexiPage 6種・Apex）への影響が小さい。候補者は default=false のまま無影響。企業用ListView/タブに「Archived__c で除外/含む」フィルタを足すだけ。

---

## 実装フェーズ（すべて full sandbox でリハーサル → 本番。不可逆ステップなし）

### Phase 0｜事前クレンジング
- 企業欄への候補者誤混入を是正: attendance__c.ClientName__c の NewGrad **1,571件** / pipeline__c.Company__c **5件** / event__c.CompanyName__c **8件**。変更前値をCSV退避してから是正。
- tokumo-app の実在しない企業RT既定値 `0122w000001Ry2iAAC` を是正（別タスク扱いでも可）。
- 受入: 企業を指す全リレーションに `IsPersonAccount=true` が0件。

### Phase 1｜メタデータ構築（追加のみ／既存は不変）
1. **Account に `Archived__c`（Checkbox, default=false）追加**。FLSは企業運用プロファイルにのみ付与。
2. **新オブジェクト `Company__c` 作成**。`Name` ＋ `LegacyAccountId__c`（Text(18), External ID, Unique）＝移行の突合キー（旧Account.Idを保持）。
3. **企業項目パリティ複製**（Client 212社で値が入っている非__pc項目のみ）。代表例:
   - 標準: Website(187), NumberOfEmployees(108), Industry(95), BillingCity/PostalCode/Street, Phone
   - カスタム: RepresentativeFullName__c(149), FoundationYearMonth__c(143), CompanyPhase__c(124), IntroductionMethod__c(108), GfaCapital__c(107), ListedStatus__c(65), Field19__c/Field17__c, URLForIntroduction__c, Phase__c, CS_keiyu__c
   - textarea企業説明系: GfaBusinessContent__c, StrengthOfferPoint__c, SelectionFlow__c, Mission/Vision 等
   - **除外**: Total*Sales 9項目（うち4つはRoll-Up Summary）→ Phase 4でApex集計として再実装。
4. **子に Company__c への新Lookupを新設**（旧リンクは温存）:
   - ① `pipeline__c.CompanyRef__c`（Lookup→Company__c, 任意）
   - ② `attendance__c.CompanyRef__c`（Lookup→Company__c, 任意）
   - ③ `JobOfferSlip__c.CompanyRef__c`（Lookup→Company__c, 任意）※旧MD Company__c は残す
   - ④ `event__c.CompanyRef__c`（Lookup→Company__c, 任意）※旧MD CompanyName__c は残す
5. **Company__c の UI**: 単独カスタムタブ、FlexiPage（GfaClientAccountRecord 相当を新規）、企業用ListView、現行Lightning Appナビに追加。
6. **企業別売上の再実装用項目**: Company__c に `TotalReferralSales__c` 等（通常Number。Phase 4のApexが書込）。

### Phase 2｜データ移行（ExternalIdキーで冪等）
1. 企業212社を Company__c へ INSERT（`LegacyAccountId__c = 旧Account.Id` を必ずセット）。
2. ①②③④ の各 `CompanyRef__c` を ExternalId突合で一括UPDATE。件数: ①5,586 ②16,546 ③159 ④250。
3. 旧リンクは**残したまま**＝子は新旧両方を向く（ロールバック余地）。

### Phase 3｜ロジック/連携の張り替え
- **Apex 企業名表示参照を Company__c 経由へ**（数値計算は非依存なので表示ラベルのみ）:
  - JobOfferKpiController.cls / SoukyakuKpiController.cls … `…Company__r.Name`。`IndividualCompanyName__c` のOR併用は維持。
  - 企業起点コントローラは全面見直し: ClientAccountController / CompanyListController / CompanyEntryController を Company__c 基準へ。
  - JobRecommendationController / TaskAutoGenerator / TaskDashboardController。
  - LWC（jobOfferSummaryCard / infoSessionBulkEntry）は Slip側 AutoCompanyName__c 経由のため影響小（要確認のみ）。
- **Apexテスト**: 変更クラスのカバレッジ75%以上を担保。
- **外部連携を Company__c 参照＋env化**（シークレット直書き禁止・RT/オブジェクトAPI名は環境変数）:
  - hr_support: notion_to_sf_sync.py（`SF_CLIENT_RECORDTYPE`）, notion_info_session_sync.py, scheduling/auto_email_pipeline.py, agents/chuto/orchestrator.py, agents/workers/*, services/sf_service.py, communication/slack_bot.py, sf_lwc/*
  - tokumo-app: src/lib/salesforce/client.ts（企業作成を Company__c へ＋実在しないRT既定値の是正）, src/app/api/sf/*, api/main.py

### Phase 4｜企業別売上の再実装
- 旧Account側の Roll-Up Summary（TotalRPOSales__c / TotalReferralSales__c / TotalSoukyakuSales__c / TotalRefundAmount__c）相当を **Apexで Company__c に再集計**:
  - pipeline__c / attendance__c のトリガハンドラ（「1オブジェクト1トリガ」規約）で `CompanyRef__c` 単位に集計し Company__c の Number項目へ書込。初期値は Batch Apex でバックフィル。
  - 集計条件は旧Roll-Up Summaryを踏襲し、移行前後で企業別合計が一致することを検証。
- 旧Account側のRoll-Up Summaryは温存（照合用の安全網）。

### Phase 5｜アーカイブ化
- 旧Client Account 212社の `Archived__c = true` に一括UPDATE（**削除しない**）。
- 企業用ListView / 検索 / タブから Archived を除外＝画面上は新Company__cタブのみが企業の入口に。
- 旧Accountは裏で生存 → ③④のMD子は親を保持＝cascadeも孤児化も発生しない。

### Phase 6｜本番適用 → 観測 → クローズ
- sandboxフルリハーサル完了後にのみ本番適用。低トラフィック時間帯・全操作ログ取得。
- 観測期間（例: 2週間）は旧リンクも温存し差分監視。
- **旧Accountを物理削除しない**ため最後まで不可逆ステップ無し。旧リンク項目の廃止は将来別計画で慎重に判断。

---

## 移行順序の鉄則（データを失わない理由）

```
追加だけ先に全部やる（新オブジェクト・新Lookup・新参照）→ 検証 → 旧はアーカイブで隠すだけ
旧を「消す」操作が一度も無い ⇒ cascade(③④)も SetNull孤児化(①)も発生しようがない
ExternalId(LegacyAccountId__c)で冪等 ⇒ 何度流しても同じ結果・途中失敗も再実行で回復
```

---

## 検証（受け入れ条件）

- [ ] 企業を指す全リレーションに候補者(IsPersonAccount=true)が0件（Phase 0後）
- [ ] Company__c件数 = 旧Client件数(212)。`LegacyAccountId__c` 全件ユニーク・欠損0
- [ ] ①②③④ の `CompanyRef__c` セット件数が移行前のリンク件数と一致（5,586/16,546/159/250）。孤児0
- [ ] **全体KPIの金額・件数が移行前後で完全一致**（SOQL/UIで前後スナップショット比較）
- [ ] 企業別売上（Phase 4のApex集計）が旧Account側Roll-Up Summaryと全社一致
- [ ] 企業名ラベルが新タブ・KPI画面で正しく表示
- [ ] 企業用タブ・ListView・FlexiPageが Company__c で機能。Archived企業が新タブに出ない
- [ ] 求職者側（候補者ListView・面談・選考・KPI）が一切変化していないこと
- [ ] 外部連携（notion_to_sf_sync / tokumo-app）が Company__c で正常動作（sandboxで実行）
- [ ] Apexテスト カバレッジ75%以上・全パス

---

## ロールバック

- Phase 1-4 はすべて「追加」のみ → 不要なら新メタ削除・新Lookupクリアで原状復帰（旧は無傷）。
- Phase 5 アーカイブは `Archived__c=false` に戻すだけで即時復帰。
- 物理削除を行わないため、全フェーズで旧状態へ戻せる。

---

## デプロイ規約（厳守）

- SF操作は必ず `sf project deploy/retrieve start --target-org prod`（alias=shunwatanabe）。config/.env の SF_USERNAME は ModifyMetadata権限なしで失敗するため使わない。
- まず full sandbox で全フェーズをリハーサル。本番はリハ完了後のみ。
- シークレット直書き禁止（RT Id/オブジェクトAPI名は環境変数経由）。

---

## 工数の目安

| Phase | 内容 | 目安 |
|---|---|---|
| 0 | クレンジング | 0.5〜1日 |
| 1 | メタ構築（項目/タブ/FlexiPage/テスト） | 2〜4日 |
| 2 | データ移行（sandbox） | 1〜2日 |
| 3 | Apex/連携 張替 | 2〜3日 |
| 4 | 企業別売上 Apex再実装 | 1〜2日 |
| 5 | アーカイブ化 | 0.5日 |
| 6 | 本番適用＋観測 | 0.5日＋2週間観測 |

**中核実働 ≈ 1.5〜3週間 ＋ 観測期間。**
