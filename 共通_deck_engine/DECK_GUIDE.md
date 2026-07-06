# TOKUMORI 資料エンジン ガイド（作り方・ルール正本）

`build_pitch_deck.py` ＝ **テーマ(MODE) × 内容(SPEC) で高品質スライドを量産**するエンジン。
このガイドの**ルールに忠実に**作ること（HTML図・トンマナ・レイアウト規律は厳守）。

---

## 1. 量産の使い方（コマンド）

```bash
# 既定SPEC（HR支援サービス概要）を各テーマで
MODE=shu   python3 build_pitch_deck.py          # 対外（営業/概要/採用ピッチ）
MODE=vivid python3 build_pitch_deck.py          # 社内向け

# 内容を差し替えて量産（SPEC=JSON）
MODE=soft  SPEC=spec_student_sample.json python3 build_pitch_deck.py   # 学生向け
MODE=cool  SPEC=path/to/exec.json       python3 build_pitch_deck.py   # 経営陣
MODE=aura  SPEC=path/to/spec.json       python3 build_pitch_deck.py   # 対外（elu風・超ミニマル/多色オーラ）

# 既存デッキを上書き（URL固定）
MODE=shu PITCH_ID=<presentationId> python3 build_pitch_deck.py
```

出力＝Google Slides（編集可能）。共有は 0130atsuya / atsuya_sato / tokumori.co.jpドメイン閲覧。

---

## 2. 用途 → MODE → フォント（用途別にフォントを変えてよい）

| 用途 | MODE | 地/ヒーロー | フォント |
|---|---|---|---|
| 対外（営業・概要・採用ピッチ・社外振り返り） | **shu** | 白×ブランド赤#af322cの強グラデ（右が濃赤→左は白） | IBM Plex Sans JP ＋ IBM Plex Mono |
| 社内向け | **vivid** | 純白＋明赤#F23B27・高コントラスト | IBM Plex Sans JP ＋ IBM Plex Mono |
| 経営陣プレゼン | **cool** | 冷たい白＋電光赤＋クール青の対トーン（分析的） | IBM Plex Sans JP ＋ IBM Plex Mono |
| 学生向け | **soft** | メディア`.softfv`の温かい背景（就活メディアと同世界観） | **Shippori Mincho（見出し）** ＋ Noto Sans JP ＋ IBM Plex Mono |
| 対外/概要・採用ピッチ（超ミニマル・先進的） | **aura** | elu風＝白基調・大余白＋右に発光する多色の生成オーラ（“記憶に残る一点”）＋濃いインク大見出し | IBM Plex Sans JP ＋ IBM Plex Mono |
| （任意・大胆） | media | 黒×赤のダークヒーロー | IBM Plex |

---

## 3. トンマナ（厳守）

- **色**: ブランド赤 `#af322c`（唯一のアクセント）＋黒/インク `#17181c`＋クールグレー `#6a6e78`＋ヘアライン `#e5e7ec`。地は白。
- **赤の規律**: コンテンツ面で赤は**最大2〜3箇所**（kicker / マーカー / footer など）。塗り箱・赤の多用はしない。
- **“強さ”は背景（グラデ）で出す**。パネルの赤塗り（数値を赤・カード全塗り）はしない。
- **フォント**: 上表の通り用途別。数値・ラベルは必ず等幅（IBM Plex Mono）。
- **装飾絵文字は使わない**（状態は色/枠/テキストで表現）。

### やってはいけない（ユーザー却下事項）
- 全面ダークなデッキ（ヒーローのみ可）
- パネルの赤塗りで強さを出す
- 深赤のフルベタ（“パキッと”重い）
- 朱 `#e8513b` をブランド色として使う（ブランドは `#af322c`）

---

## 4. レイアウト規律（被り・はみ出しゼロ）

- **統一ヘッダー**: 全コンテンツ・スライドで kicker(y=0.98") / タイトル(y=1.26"・**固定26pt**・fitで縮めない) / 細グレー罫(y=1.88") を**同一座標・同一サイズ**に揃える。
- **本文は上下やや上寄り中央**（`ctop()`）。罫と本文の隙間を空けすぎない。
- **はみ出し/被り防止**: テキストは `fit_size`（lh=1.42）で枠に収める＋**短文**にする。fit見積りは楽観的なので、カード説明やCTA箇条は**3行に収まる長さ**にし、枠/間隔を広めに取る。
- **footer**: 細罫＋`TOKUMORI ｜ <tag>`＋ページ番号（mono）。

---

## 5. 図は必ず「HTMLハイブリッド」（最重要・既定の標準）＋ 図解ファースト

**ハイブリッド＝高品質の標準。今後すべての資料で、図はHTMLハイブリッドを既定にする**（ユーザー方針）。

### 図解ファースト（判断軸＝積極的に図にする・文字の壁を作らない）
**構造があれば必ず図にする。** 箇条書きは“短い・並列・非構造”の時だけ。1スライド1メッセージ＋図＋短い要点。
| 内容の構造 | 使う図 |
|---|---|
| 順序・流れ・手順 | flow / timeline |
| 段階・キャリア・成長 | ladder（昇る段）/ timeline |
| 比較・対比 | compare / before_after / quadrant(matrix) |
| 階層・優先順位 | pyramid |
| 関係・登場人物・エコシステム | relation |
| 反復・サイクル | cycle（PDCA等）|
| 割合・構成比 | donut |
| 量・ランキング | bar |
| 2軸ポジショニング | quadrant / matrix |
| 席次・配置 | seating |
| 集合・重なり（AかつB）| venn |
| 選考・採用ファネル | funnel |
| 二面・仲介・プラットフォーム | platform（左アクター⇄中央基盤⇄右アクター・番号付き矢印）|
| KPI・数式の分解（A×B=C）| formula（要素ボックス＋改善施策）|
| 多チャネル → 1ゴールへ収束 | converge |
| 期間・所要日数つきの工程 | process（番号丸＋期間ラベル）|
| カテゴリ網羅マップ（行×列）| gridmatrix |
| 方向・成長の広げ方（縦/横/斜め等）| directions（起点→複数方向の矢印＋説明チップ）|
- 研修(`build_slides.py`/training_v2)では `dk.diagram(kind, kick, title, data, note)` で上記を呼ぶ（`figs_html.py`: pyramid/relation/timeline/ladder/before_after/cycle/seating/bar/flow/line/quad(matrix)/venn/funnel/donut(center=可)/**platform/formula/converge/process/gridmatrix/directions**）。`seating()`/`barchart()`/`linechart()`/`quadrant()`/`flow()` は training_v2 で自動ハイブリッド。各 data 形は `figs_html.py` の docstring参照。

### 図の品質原則（editorial 級・ディープリサーチ準拠＝Tufte/SWD/IBM Carbon/MBB）
1. **数値＝等幅(IBM Plex Mono)・文章＝Plex Sans JP** に厳格分離（桁が揃う＝比較が速い）。
2. **赤 #af322c は「結論・主役」1図1〜2箇所のみ**。残りは全てグレー3段（濃 `4A4D52`／中 `8A8D93`／淡 `D8DADD`）。ピンク等の中間色は使わない。
3. **グリッド線・凡例・影・3D・不要枠を排し data-ink を最大化**（chartjunkゼロ）。
4. **角丸は 8px に統一**、線は1〜1.5px（強調のみ2〜2.5px）、矢印ヘッドは小さく細く・単一方向。
5. **マトリクスの軸ラベルは外側のガター帯に逃がす**（縦=左64px／横=下48px）。プロットを端まで詰めない。
6. **外周マージン 64–96px・余白を15%以上**確保（呼吸する余白）。8pxグリッド／ベースライン整列。
7. タイポ階層は **1.333スケール**（タイトル≒本文×2）。軸/キャプションは16px下限・全大文字は字間+0.06em。
- 「文字ばかりで疲れる」を避ける。長い箇条・構造ある説明は迷わず図へ。
- 図解・チャート・フロー図は **HTML/CSS/SVGで作成 → 高解像度PNG化 → Slidesに画像挿入**（`html_to_slide.py`）。文字（タイトル/本文/要点）は**ネイティブの編集可能テキスト**のまま。
- **解像度**: 背景=DPI3、文字の多い図=**DPI4**（“荒い”を回避）。
- **スマートな図の指針**（引き算）: 赤は1図1アクセント / 塗りは控えめ / 細い線 / 等幅ラベル / 余白（データインク比を上げる）。
- 図は MODE のフォント・配色で描画される。
- **対外/社内ピッチ**（build_pitch_deck.py）: flow図はハイブリッド標準。
- **研修**（build_slides.py・`THEME=training_v2`）: `barchart`/`linechart`/`quadrant`/`flow` は **`figs_html.py` のスマートHTML図で自動ハイブリッド化**（`dk.uploader` 経由・DPI4）。表紙/章扉は淡赤グラデ背景もHTML。本文テキストはネイティブ編集可。
- 新しい図タイプも、まずHTML/SVGで作る（`figs_html.py`/`html_to_slide.py` に追加）。

---

## 6. SPEC（内容）の書き方

JSON（または `DEFAULT_SPEC`）。`type` でスライド種別を指定。

```jsonc
{
  "title_doc": "ドキュメント名",
  "tag": "フッターのタグ",
  "cover":  {"kicker":"…","title":"…","subtitle":"…","org":"…"},
  "slides": [
    {"type":"bullets","kicker":"…","title":"…","items":["…","…"]},
    {"type":"stats","kicker":"…","title":"…",
     "stats":[["33.8%","ラベル","出典"], …], "note":"出典など"},
    {"type":"cards","kicker":"…","title":"…",
     "cards":[["見出し","TAG","説明（3行以内）"], …]},
    {"type":"flow","kicker":"…","title":"…","accent":2,
     "steps":[["01","名称","説明"], …], "point":"要点（So-What）"}
  ],
  "cta": {"kicker":"…","title":"…","points":["…"],"contact":"…"}
}
```

- `bullets`=箇条／`stats`=等幅大数値カード（出典付き・**実績の捏造はしない**）／`cards`=価値カード＋ピル／`flow`=ハイブリッド・ステップ図（`accent`=強調するステップ番号・0始まり）。
- 表紙/CTAはMODEに応じ自動でヒーロー化（shu=赤グラデ／media=黒×赤）。

---

## 7. 検証（必須）

- 生成後、**Slides公式サムネ（getThumbnail, LARGE）＝Googleの実描画**で**全スライドを目視**。
- チェック: 被り/はみ出しゼロ・赤の規律(最大2〜3)・タイトル位置/サイズ統一・図がくっきり・装飾絵文字なし。
- （PlaywrightはSlides編集URLのGoogleログイン壁で不可。サムネが実描画＝代替）。

---

## 8. ロゴ（共有後）

公式ロゴ共有後、各ヒーローの**白余白**（右上 等）に `createImage` で配置し、ワードマークと差し替え。

---

## 9. ファイル

- `build_pitch_deck.py` … エンジン（MODE/PAL/背景/レンダラ/SPEC）
- `html_to_slide.py` … HTML→PNG→Slides挿入（ハイブリッド）
- `build_slides.py` … 低レベル部品（Deck/rect/text/fit_size）＋研修41デッキ
- `spec_student_sample.json` … SPECの記入例（学生向け）
