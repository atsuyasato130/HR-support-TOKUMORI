---
name: company-doc-ingest
description: 選考対策資料（PDF/スライド/ドキュメント/テキスト）を受け取り、企業情報をSFに自動反映。「選考対策資料を登録して」「この資料をSFに入れて」「〇〇の選考情報を登録」「資料からSF更新」で発火。引数: ファイルパス or URL or 企業名（テキスト貼り付けの場合）
---

選考対策資料を読み取り、SF企業（Account）情報を更新する。入力=$ARGUMENTS

## Step 1: 入力タイプ判定と読み取り

### パターンA: Google スライド URL
`docs.google.com/presentation/d/` を含む場合:
```
presentation_id = URLから抽出（/d/<ID>/の部分）
read_google_slides(presentation_id=<ID>)
```

### パターンB: Google ドキュメント URL
`docs.google.com/document/d/` を含む場合:
```
doc_id = URLから抽出
read_google_doc(doc_id=<ID>)
```

### パターンC: PDF ファイルパス（.pdf）
```
Read(file_path="<パス>")  # Claude CodeのRead toolはPDF対応済
```

### パターンD: PowerPoint（.pptx）/ Word（.docx）ファイル
```bash
# pptxの場合
python3 -c "
import pptx, sys
prs = pptx.Presentation(sys.argv[1])
for slide in prs.slides:
    for shape in slide.shapes:
        if hasattr(shape, 'text'): print(shape.text)
" "<パス>"

# docxの場合
python3 -c "
import docx, sys
doc = docx.Document(sys.argv[1])
for para in doc.paragraphs: print(para.text)
" "<パス>"
```

### パターンE: テキスト貼り付け
引数またはユーザーが直接貼ったテキストをそのまま処理。

---

## Step 2: 企業名の特定

読み取ったコンテンツから企業名を自動抽出し、SFで検索:

```
search_salesforce("SELECT Id, Name, Website, Description, Field2__c FROM Account WHERE IsPersonAccount = false AND Name LIKE '%<企業名>%'")
```

企業名が不明な場合はユーザーに確認:
```
❓ 資料から企業名を特定できませんでした。
対象企業名を教えてください:
```

複数ヒットの場合は候補を提示してユーザーに選択させる。

---

## Step 3: 構造化情報の抽出（Claude自身が実行）

読み取ったコンテンツから以下の情報を抽出する:

```
【抽出チェックリスト】
□ 企業名（確認）
□ 公式HP URL
□ 事業概要・事業内容
□ 選考フロー（ES→説明会→GD→一次→二次→最終 等）
□ 各選考フェーズの詳細・通過ポイント
□ 求める人物像・カルチャー
□ 面接でよく聞かれる質問・対策
□ 評価軸・選考ポイント
□ 難易度・倍率に関する記述
□ 初任給・待遇・勤務地
□ 学歴フィルターの有無
```

## Step 4: SF格納マッピング

抽出情報をSFフィールドにマッピング:

| 抽出情報 | SF格納先 | 更新ルール |
|---|---|---|
| HP URL | `Website` | 未設定の場合のみ設定 |
| 選考難易度（計算） | `Field2__c` | 常に更新OK |
| 以下はすべて`Description`内のセクション | | |
| 事業概要・推しポイント | `📌 事業内容` `✅` セクション | 既存があれば補完・強化 |
| 選考フロー | `📋 選考フロー` セクション | 上書き |
| 面接対策・合格ポイント | `✨ おすすめポイント` セクション | 資料情報で強化・上書き |
| 難易度 | `📊 選考難易度` セクション | 追記または上書き |

### Description再構成ルール

既存Descriptionがある場合: セクション単位でマージ（資料情報を優先）
既存Descriptionがない場合: 以下フォーマットで新規生成

```
🎯 一言で言うと
「<キャッチコピー>」

📌 事業内容
<概要>

✅ 就活生に知ってほしいポイント
・<ポイント1>
・<ポイント2>
・<ポイント3>

📋 選考フロー
<フロー>

✨ おすすめポイント（選考対策）
・<面接対策ポイント1>
・<面接対策ポイント2>
・<よく聞かれる質問: 〇〇について>

📊 選考難易度
<ランク>｜<理由一文>
```

### 難易度判定（資料情報から）

資料に倍率・通過率が明記 → そのまま採用
記載なし → 選考回数・求める人物像・学歴要件から推定

| ランク | 目安 |
|---|---|
| S | 倍率50x以上 or 旧帝・早慶必須レベル |
| A | 倍率20〜50x or MARCH以上想定 |
| B | 倍率5〜20x or 大卒以上 |
| C | 倍率5x以下 or 学歴不問 |

Field2__c形式: `"B｜中堅ベンチャー・面接3回・書類〜最終1.5ヶ月"`

---

## Step 5: 変更プレビュー表示

```
━━━━━━━━━━━━━━━━━━
📋 更新プレビュー
━━━━━━━━━━━━━━━━━━
企業: 株式会社〇〇 (ID: 001xxx)
資料: <ファイル名 or URL>

【Website】
  Before: なし
  After:  https://〇〇.co.jp/

【Field2__c（選考難易度）】
  Before: なし
  After:  "B｜中堅ベンチャー・面接3回・MARCH以上"

【Description 変更箇所】
  ✅ おすすめポイントセクション → 資料の選考対策情報で強化
  ✅ 選考フローセクション → 詳細フローに更新
  ✅ 📊選考難易度セクション → 新規追加

━━━━━━━━━━━━━━━━━━
✅ このまま更新しますか？（はい / キャンセル）
━━━━━━━━━━━━━━━━━━
```

---

## Step 6: SF更新実行

確認後、`update_salesforce_record` MCP で更新:

```
update_salesforce_record(
    object_type="Account",
    record_id="<Id>",
    fields_json='{
        "Website": "<URL（未設定時のみ）>",
        "Field2__c": "<難易度テキスト>",
        "Description": "<再構成したDescription全文>"
    }'
)
```

---

## Step 7: 完了報告

```
━━━━━━━━━━━━━━━━━━
✅ 選考対策資料の取り込み完了
━━━━━━━━━━━━━━━━━━
企業: 株式会社〇〇
更新フィールド:
  ✅ Website → https://〇〇.co.jp/
  ✅ Field2__c → B｜中堅ベンチャー・面接3回
  ✅ Description → 選考フロー・対策情報を更新
  
次回 /company-intro-gen 〇〇 で新しい情報が反映されます。
━━━━━━━━━━━━━━━━━━
```

---

## エラー対処

| 問題 | 対処 |
|---|---|
| pptx/docxモジュールなし | `pip3 install python-pptx python-docx` を案内 |
| Google認証エラー | `token_sheets.json` 再認証を案内 |
| SF企業が見つからない | 企業名の表記揺れを確認・手動指定を促す |
| Description上書きで既存情報が消える恐れ | セクション単位でマージし、説明会日程セクションは絶対に保護 |

## ❌ してはいけないこと

- 既存の `📅 説明会・選考案内` セクションを削除・上書きすること
- 既存の `Website` を勝手に上書きすること  
- 学歴フィルター等の学生に見せてはいけない情報をDescriptionに含めること（「旧帝以外は書類落ち」等の内部情報は記述しない）
- ユーザー確認なしでSF更新を実行すること
- `Field3__c` を変更すること
