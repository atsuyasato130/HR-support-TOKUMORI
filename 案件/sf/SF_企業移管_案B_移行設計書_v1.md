# SF 企業移管（案B）移行設計書 v1

作成日: 2026-06-24 / 対象org: tokumori-watanabe（00D2w00000RKk18EAD, prod=alias shunwatanabe）
位置づけ: **設計ドキュメント（本書時点で組織変更は一切なし）**。実装は本書承認 → sandboxリハーサル → 本番の順。

---

## 0. 目的・スコープ・前提

### 目的
Account に RecordType で混在している「企業（Client・212件）」を、**新カスタムオブジェクト `Company__c` へ物理移管**し、Account を候補者（Person Account）専用にする。

### スコープ
- IN: 企業212件の移管、企業を指す4リレーションの張り替え、企業向けApex/UI/外部連携の改修、事前クレンジング。
- OUT: 候補者（16,167件）・Person Account機能・売上集計（IsPersonAccount依存）・候補者向け連携。**これらには触れない**（企業移管の最大の利点）。

### 絶対前提（厳守）
- SF操作は必ず `sf ... --target-org prod`（alias=shunwatanabe）。config/.env の SF_USERNAME は ModifyMetadata 権限なしで失敗するため使わない。
- 本番投入前に **full sandbox でフルリハーサル必須**。ぶっつけ本番禁止。
- シークレット直書き禁止。RecordType Id / オブジェクトAPI名は環境変数化（外部連携）。

---

## 1. 現状（As-Is）実数サマリ

```
Account 16,379件
├─ Client（企業）          212件   IsPersonAccount=false  ← 移管対象
├─ NewGraduates（新卒）  16,165件   IsPersonAccount=true   ← 残す
└─ MidCareer（中途）          2件   IsPersonAccount=true   ← 残す

企業(Client)を指すリレーション（=移管で張り替える対象）
┌──────────────────────────────┬──────────┬────────┬───────────────┬─────────┐
│ 項目                          │ 型        │ 必須    │ 削除挙動       │ 件数    │
├──────────────────────────────┼──────────┼────────┼───────────────┼─────────┤
│ ① pipeline__c.Company__c      │ Lookup    │ 任意    │ SetNull        │ 5,586   │
│ ② attendance__c.ClientName__c │ Lookup    │ 任意    │ Restrict       │ 16,546  │
│ ③ JobOfferSlip__c.Company__c  │ M-D       │ 必須    │ cascade/再親不可│ 159     │
│ ④ event__c.CompanyName__c     │ M-D       │ 必須    │ cascade/再親不可│ 250     │
└──────────────────────────────┴──────────┴────────┴───────────────┴─────────┘
その他: Contact 3 / Task.WhatId 4 / Opportunity 0 / Case 0 / BudgetAndActual__c 22(別未精査) → 軽微

★最大の壁: ③④ は reparentable=false の Master-Detail。別オブジェクトへ親を張り替え不可
        → 新リレーションを作り、子レコードを再作成する必要がある。
```

### 既知の不整合（移管前に必ず是正）
- attendance__c.ClientName__c に **候補者(NewGrad)が1,571件 誤混入**。
- pipeline__c.Company__c に候補者5件、event__c.CompanyName__c に候補者8件 誤混入。
- tokumo-app の企業RT既定値 `0122w000001Ry2iAAC` は**実在しないId**（企業作成系が壊れている可能性）。

---

## 2. To-Be 設計

### 2.1 新オブジェクト
```
Company__c（カスタムオブジェクト・企業マスタ）
├─ Name（企業名）
├─ ExternalId: LegacyAccountId__c（Text(18), External ID, Unique）★移行の主キー
│   = 旧 Account.Id を保持。全リレーション張り替えの突き合わせキー
├─ 企業向け項目を Account(Client) から項目パリティ移植（※2.4の棚卸し結果で確定）
└─ Tab: **Company__c 単独カスタムタブ【確定】**（=当初要望「クライアント専用タブ」）。現行Lightning Appのナビに追加
```

### 2.2 リレーション再設計（4本）
```
① pipeline__c   : 新Lookup CompanyRef__c (→Company__c, 任意) を新設。旧Company__c(→Account)は移行後に廃止
② attendance__c : 新Lookup CompanyRef__c (→Company__c, 任意) を新設。旧ClientName__c は移行後に廃止
③ JobOfferSlip__c: **方式X【確定】** 新Lookup CompanyRef__c (→Company__c, 必須) を新設。旧M-D(→Account)は温存
④ event__c      : **方式X【確定】** 新Lookup CompanyRef__c (→Company__c, 必須) を新設。旧M-D(→Account)は温存
```
注: 旧項目は「即削除」せず**一定期間 deprecated 併存**（ロールバック余地確保）。

### 2.3 UI / ロジック移植
```
- Apex: ClientAccountController / CompanyListController / CompanyEntryController を Company__c 基準に書換
- FlexiPage: GfaClientAccountRecord 相当を Company__c 用に新規
- ListView: 企業用ビューを Company__c 上に再作成
- Report: 「Account=Client」型レポートを Company__c 型へ再作成（候補者レポートは無傷）
- Tab/App: Company__c タブを作成し、企業App（または共通App）のナビに配置
```

### 2.4 項目パリティ棚卸し（Phase 1 の必須サブタスク）
Account(Client)で実際に使われている企業向けカスタム項目を describe で全列挙 → Company__c に同型で複製する一覧表を作る。これをやらないと移行で項目欠落が起きる。

---

## 3. ③④ Master-Detail の扱い（移管可否の決定打）

reparentable=false の M-D は親オブジェクトを変えられないため、選択肢は2つ：

```
方式X: Lookup へ格下げして移行（推奨・可逆性高い）
  JobOfferSlip__c / event__c に Company__c への新規Lookup(必須)を作り、
  旧M-D(→Account)はそのまま温存 → 子レコードは再作成せず「親参照だけ追加」
  長所: 子レコード再作成不要・データ消失リスク最小・ロールバック容易
  短所: M-D特典(ロールアップ集計・親共有継承・cascade削除)を失う
        → ロールアップが必要なら数式/Apex/Flowで代替設計が要る

方式Y: 新M-D で子を再作成（厳密だが高リスク）
  Company__c を親とする新M-Dを張り、子(159/250件)を新規作成して旧子を廃止
  長所: M-D特典を維持
  短所: 再作成中の整合性・cascade・共有の再設計が重く不可逆性が高い
```

**本設計は 方式X で確定。** ただし方式XはM-D特典（ロールアップ集計・親共有継承・cascade削除）を失うため、Phase 1 で以下を必ず確認し、使われていれば代替設計を移行前に用意する：
- JobOfferSlip__c / event__c → 親(企業Account)側のロールアップ集計項目の有無 → あれば数式/Flow/Apexで代替
- 子の共有が親(M-D継承)に依存していないか → Company__cのOWD/共有で再設計
- cascade削除に依存した運用がないか → Lookupの削除制約（Restrict等）で代替

---

## 4. 段階手順（Phase 0 → 6）

```
Phase 0  事前クレンジング（本番・移行前）
  - attendance 1,571 / pipeline 5 / event 8 の候補者誤混入を是正（正しい企業へ付替 or 除外）
  - tokumo-app の存在しない企業RT Id を是正
  - 受入: 企業を指す全リレーションに候補者Account(IsPersonAccount=true)が0件

Phase 1  設計確定（sandbox・非破壊）
  - 企業向けカスタム項目の全棚卸し（2.4）
  - ③④のロールアップ/共有/cascade依存の有無を確認（方式X確定済 → 依存があれば代替設計を用意）
  - 外部連携の企業参照箇所を全特定（6章）

Phase 2  メタデータ構築（full sandbox）
  - Company__c 作成・項目パリティ複製・ExternalId(LegacyAccountId__c)
  - ①②に CompanyRef__c(Lookup) 新設、③④に新リレーション（方式Xなら新Lookup必須）
  - Apex/FlexiPage/ListView/Tab を Company__c 基準で構築（旧は温存）
  - Apexテスト カバレッジ75%以上を先に用意

Phase 3  データ移行（full sandbox）
  3-1 企業212件を Company__c へ INSERT（LegacyAccountId__c=旧Account.Id を必ずセット）
  3-2 ①② を ExternalId突合で一括UPDATE（CompanyRef__c に新Idをセット）5,586/16,546件
  3-3 ③④ を方式に従い紐付け（X=新Lookupに値セット / Y=子再作成）
  3-4 全件突合検証（旧件数=新件数、孤児0、誤混入0）

Phase 4  連携・UI切替（full sandbox）
  - 外部連携（tokumo-app / hr_support / GAS）を Company__c 参照へ改修＋env化
  - 旧Account.Client 参照を新参照へ全切替。並行稼働で差分監視

Phase 5  本番適用（リハーサル完了後のみ）
  - Phase 2→4 を本番で再実行。低トラフィック時間帯・全操作ログ取得
  - 旧項目/旧データは即削除せず deprecated 保持（ロールバック窓）

Phase 6  クローズ
  - 一定観測期間（例: 2週間）後、旧Client Account・旧項目をアーカイブ/削除
  - 受入条件を全て満たしたら完了
```

---

## 5. ロールバック計画

```
Phase     ロールバック手段                                       不可逆性
────────────────────────────────────────────────────────────────────────
0 클렌징   変更前の値をCSVバックアップ → 復元UPDATE                低
1 設計     メタのみ・破棄で原状復帰                                なし
2 構築     新規メタを削除（旧は無傷で温存）                        なし
3 移行     新Company__c/新Lookup値をdeleteで除去・旧参照が生存     低（旧温存が前提）
4 切替     連携を旧参照へ戻す（feature flagで瞬時切替できる設計に） 中
5 本番     観測窓の間は旧を保持→旧へ戻す。方式Yの子再作成のみ注意  中〜高
6 クローズ 旧削除後は不可逆 → ここに進むのは受入完全合格後のみ      高
```
原則: **「旧を消す」のは最後（Phase 6）だけ**。それ以前は常に旧へ戻せる状態を維持する。

---

## 6. 外部連携 改修リスト（企業参照箇所）

```
ファイル                                         対応
──────────────────────────────────────────────────────────────────────
hr_support/tools/notion_to_sf_sync.py            SF_CLIENT_RECORDTYPE → Company__c生成へ。env化
tokumo-app/src/lib/salesforce/client.ts          企業作成を Company__c へ。壊れたRT Id(Ry2iAAC)是正
tokumo-app 企業作成系 route/api                   同上
（候補者系: client.ts/main.py/sf_auto_register.py 等の新卒RTは触らない）
Apex: ClientAccountController/CompanyListController/CompanyEntryController を Company__c基準へ
```
注: 候補者向け連携・JobOfferKpiController（IsPersonAccount売上集計）は**無改修**。これが企業移管の核心メリット。

---

## 7. リスク一覧と最小化策

```
# リスク                              重大度  最小化策
──────────────────────────────────────────────────────────────────────────
1 ③④ M-Dの再設計失敗・ロールアップ喪失  高    方式X採用＋Phase1でロールアップ依存を実確認。
                                              代替集計(数式/Flow)を移行前に用意
2 ①②大量UPDATE中の整合崩れ            中    ExternalId(LegacyAccountId__c)で冪等突合。
   (5,586/16,546件)                          Bulk＋件数検証ゲート。旧項目温存
3 誤混入データの持ち込み                中    Phase0で必ずクレンジング→受入0件を確認してから移行
4 企業向けApex/UIの取りこぼし           中    Phase1棚卸しで全特定。テスト75%先行。FlexiPage再作成
5 Report破損                           中    企業型レポートのみ再作成。候補者型は無傷を確認
6 外部連携のRT/オブジェクト直書き残存    高    grep全数→env化。本番切替はfeature flagで瞬時ロールバック可に
7 共有/FLS設計漏れ                      中    Company__cのOWD/ロール/共有を新規設計（Account OWD=Internal RW踏襲）
8 本番ぶっつけ                          高    full sandboxでPhase2-4を完全リハーサル後のみ本番
```

---

## 8. 受け入れ条件（完了判定ゲート）

```
[ ] 企業を指す全リレーションに候補者Account(IsPersonAccount=true)が0件
[ ] 旧Client件数(212) = Company__c件数。孤児リレーション0
[ ] ①②③④ の件数が移行前後で一致（5,586/16,546/159/250）
[ ] 企業向け画面・リスト・レポートが Company__c 上で再現
[ ] 売上集計(JobOfferKpiController)の数値が移行前後で不変（=無改修の証明）
[ ] 外部連携(notion_sync/tokumo-app/GAS)が Company__c で正常動作
[ ] Apexテスト カバレッジ75%以上・全パス
[ ] sandboxフルリハーサル完了・所要時間と手順が確定
```

---

## 9. 工数・期間の目安（粗見積り）

```
Phase 0  クレンジング        0.5〜1日
Phase 1  設計確定/棚卸し      1〜2日
Phase 2  メタ構築            2〜4日（Apex/FlexiPage/テスト含む）
Phase 3  データ移行(sandbox) 1〜2日
Phase 4  連携/UI切替         2〜3日
Phase 5  本番適用            0.5〜1日（リハ済前提）
Phase 6  観測〜クローズ       2週間観測 + 0.5日
──────────────────────────────────────────
中核実働 ≈ 1.5〜3週間 + 観測期間。MD2本の方式判断と外部連携改修が変動要因。
```

---

## 付録: 関連メモリ / 正本
- project_sf_orchestrator, reference_sf_revenue_model, feedback_sf_deploy_account, feedback_sf_interview_date
- 退避メタ: scratchpad/mdapi_x, md2_x（Account.object・4項目field-meta・主要Apex）
