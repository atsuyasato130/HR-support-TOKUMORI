# sf_change_rules.md — Salesforce変更の鉄則・副作用チェックリスト

> **このファイルはSF変更作業の前に必ず参照すること。**
> 過去の失敗パターンを集約した「やり直しゼロ」のための知識ベース。
> 最終更新: 2026-04-12

---

## 0. SF変更の標準フロー（必須順序）

```
[1] PLAN    変更内容 + 影響範囲 + 副作用を確認（このファイルを参照）
[2] DEPLOY  Metadata API でデプロイ（tools/sf_deployer.py を使う）
[3] QA      tools/sf_qa_checker.py で自動検証
[4] LOG     architecture_master.md + Update_Log を更新
```

---

## 1. ピックリスト — 絶対ルール

### 1.1 fullName と label の関係

| パターン | fullName | label | 結果 |
|----------|----------|-------|------|
| ✅ 正しい（基準付き） | `S：テキスト` | `S：テキスト` | ドロップダウンに全文表示 |
| ❌ NG（旧形式） | `S` | `S：テキスト` | 保存時エラー or _old_ 表示 |

**鉄則: fullName = label = 長テキスト（JobHuntingProficiency__pc が正例）**

### 1.2 restricted=true を使う場合の注意

- restricted=true のとき、保存値が activeな fullName のどれとも一致しないと **「制限つき選択リスト項目の値が不適切」** エラー
- 既存レコードの保存値と新しい fullName が一致するよう設計する
- **変更前に必ず既存レコードの保存値を確認すること**

### 1.3 updateMetadata で値を変更するときの罠

- **「Duplicate label」エラー** → 既存の inactive な値と同じ label を持つ値を追加しようとしている
- 解決策: フィールドを削除して再作成（副作用に注意→§3参照）
- inactive 値を active にするだけなら isActive=true にすれば OK

---

## 2. PersonAccount / Contact の使い分け

```
PersonAccount フィールドの見え方:
  Account 上の表示名  → __pc  (例: ThinkingSkill__pc)
  実体はContactの     → __c   (例: ThinkingSkill__c)
  デプロイ先オブジェクト → Contact（Account では NG！）
```

**鉄則: PersonAccount のカスタムフィールドは必ず `Contact` オブジェクトにデプロイする**

```python
# 正しいデプロイ例
files = {
    "objects/Contact.object": contact_xml,  # ← Contact！
    "package.xml": package_xml_with_Contact_members,
}
```

---

## 3. フィールド削除時の副作用（必ず事前確認）

フィールドを削除すると **自動的に以下も削除/無効化される：**

| 副作用 | 対処 |
|--------|------|
| ページレイアウトから除外 | 削除後に再追加デプロイ必要 |
| FLS（プロファイル権限）消滅 | Admin Profile FLS を再設定 |
| フロー内参照が壊れる可能性 | 削除前にフロー参照確認 |
| レポート/ダッシュボードから消える | 手動で再設定 |

**チェックリスト（削除前に必ず確認）:**
```
□ ページレイアウト: 削除後の再追加スクリプトを用意してから削除
□ FLS: Admin プロファイルの FLS 再設定スクリプトを用意してから削除
□ フロー: 当該フィールドを参照しているフローがないか確認
□ バリデーションルール: 参照なし確認
□ 数式フィールド: 参照なし確認
```

---

## 4. Metadata API の使い分け

| API | 用途 | 注意点 |
|-----|------|--------|
| SOAP Metadata API | フィールド作成・更新・削除、レイアウト、プロファイル | 本番環境向け推奨 |
| REST Metadata API | 同上（簡易版） | エラーメッセージが詳細 |
| Tooling API | デバッグ用クエリ（FlowDefinition等） | `FieldPermissions` が使えないことがある |
| Bulk API | 大量レコード更新（バックフィル等） | 200件/バッチ推奨 |

**Tooling API の制限:**
- `FieldPermissions` クエリが使えない場合あり → `describe()` の `updateable` フラグで代替
- `Flow` オブジェクトの列名が環境により異なる

---

## 5. FLS（フィールドレベルセキュリティ）設定

### 確認方法
```python
# describe() の updateable/createable フラグで現ユーザーの権限確認
desc = sf.Account.describe()
field = next(f for f in desc["fields"] if f["name"] == "MyField__c")
print(field["updateable"])  # True なら編集可
```

### デプロイ方法（Admin プロファイルへ）
```xml
<Profile xmlns="...">
    <fieldPermissions>
        <field>Contact.ThinkingSkill__c</field>  <!-- PersonAccount は Contact -->
        <readable>true</readable>
        <editable>true</editable>
    </fieldPermissions>
</Profile>
```

**鉄則: 新規フィールド作成後は必ず FLS デプロイを続けてセットで実行する**

---

## 6. レイアウト操作

### retrieve → 編集 → deploy の手順
```python
# 1. SOAP retrieve でレイアウト取得
# 2. XML を直接編集（re.sub or string replace）
# 3. SOAP deploy でデプロイ

# 注意: <field> タグの重複は「Element is duplicated」エラーになる
# 重複除去してから追加すること
```

### 挿入位置マーカー
- 学生評価セクション: `Field31__c（ガクチカレベル）` の後
- PersonAccount-新卒 レイアウト名: `PersonAccount-新卒`

---

## 7. After-Save Flow のパターン

### pipeline__c → Account 転記フロー
```
オブジェクト: pipeline__c
トリガー: CreateAndUpdate
参照: $Record.JobApplicant__c → Account.Id
転記フィールド:
  GfaAccuracy__c → LatestYomiAccuracy__c
  Status__c      → LatestPipelineStatus__c
```

**注意: Flow は新規/更新時のみ動く。既存レコードへのバックフィルは別途スクリプトが必要。**

---

## 8. よくあるエラーと解決策

| エラー | 原因 | 解決策 |
|--------|------|--------|
| `Duplicate label` | updateMetadata で同ラベルの inactive 値が既存 | フィールド削除→再作成 |
| `制限つき選択リスト項目の値が不適切` | 保存値が active な fullName と不一致 | 保存値と fullName を一致させる |
| `Element X is duplicated` | レイアウトに同じフィールドが複数 | 重複除去してから追加 |
| `sObject type 'FieldPermissions' is not supported` | Tooling API 制限 | describe() の updateable フラグで代替 |
| `str \| None` 構文エラー | Python 3.9 非対応 | `Optional[str]` か型注釈なしを使う |
| フィールド作成後 SOQL 不可 | Tooling API 経由で作成すると draft 状態 | Metadata API（SOAP deploy）で作成する |

---

## 9. QA チェックコマンド

```bash
# 全チェック
python3 tools/sf_qa_checker.py \
  --check all \
  --object Account \
  --fields "ThinkingSkill__pc,Character__pc,Execution__pc,InterpersonalSkill__pc,JobHuntingProficiency__pc" \
  --layout "PersonAccount-新卒"

# フィールドのみ
python3 tools/sf_qa_checker.py --check fields --object Account --fields "MyField__pc"
```

---

## 10. 現在のカスタムフィールド一覧（2026-04-12 時点）

### 評価フィールド（PersonAccount）
| API名（Account表示） | 実体（Contact） | 形式 | 値 |
|---------------------|----------------|------|-----|
| ThinkingSkill__pc | ThinkingSkill__c | Picklist/restricted | S〜D（長テキスト fullName）|
| Character__pc | Character__c | Picklist/restricted | S〜D |
| Execution__pc | Execution__c | Picklist/restricted | S〜D |
| InterpersonalSkill__pc | InterpersonalSkill__c | Picklist/restricted | S〜D |
| JobHuntingProficiency__pc | JobHuntingProficiency__c | Picklist/restricted | S〜D |
| Field31__c | — | Multipicklist | S(起業)/A(長期IS)/... |

### パイプライン転記フィールド（Account）
| API名 | 型 | 転記元 |
|-------|-----|--------|
| LatestYomiAccuracy__c | Text(10) | pipeline__c.GfaAccuracy__c |
| LatestPipelineStatus__c | Text(50) | pipeline__c.Status__c |

### 面談回数フィールド（Account）
| API名 | 型 | 説明 |
|-------|-----|------|
| FollowMeetingCount__c | Number | フォロー面談回数 |
| ClosingMeetingCount__c | Number | クロージング面談回数 |

### デプロイ済みフロー
| フロー名 | オブジェクト | トリガー | 機能 |
|---------|------------|---------|------|
| PipelineSummary_UpdateAccount | pipeline__c | CreateAndUpdate | ヨミ確度・選考進捗をAccountへ転記 |
| MeetingRecord_SubjectAutoSet | — | — | 面談記録の件名自動設定（要確認） |
| MeetingRecord_CountUpdate | — | — | 面談回数カウント（要確認） |
