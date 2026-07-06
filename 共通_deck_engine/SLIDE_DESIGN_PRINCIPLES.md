# 高品質スライド/図解を“AIで一発生成”するための設計指針（リサーチ統合・2026-06-23）

build_infographic_html.py / build_slides.py / 将来のスライド生成Skill が従う原則。ディープリサーチ（出典付き）の統合。

## A. ストーリー設計（コンサル流＝中身の質）
1. **アクションタイトル**：各スライドの見出しは「説明（例：売上推移）」でなく**主張する短い文**（例：「主力2事業が縮小、収益源の入替が急務」）。タイトルだけ読めば要点が分かる。**1〜2行・〜15語以内**。出典: slideworks.io（McKinsey流）, think-cell。
2. **1スライド1メッセージ**：1枚に主張は1つだけ。出典: think-cell（日本語版含む）。
3. **ピラミッド原理（Minto）**：結論先出し→支える論拠→データ。要約は **Situation–Complication–Resolution**（状況→問題→解決＝主張）。出典: think-cell。
4. **ストーリーライン先行（ゴーストデッキ）**：先に全アクションタイトルだけ並べて筋を通し、後から各スライドの中身を埋める。出典: slideworks, think-cell。
5. **KEY TAKEAWAY/ガバニングメッセージ**を各図に必ず置く（1枚図解でも“だから何”を明示）。

## B. ビジュアル設計（見た目の質）
6. **データインク比（Tufte）**：罫線・枠・凡例・装飾など“データでないインク”を削る。チャートのタイトルも**所見**を書く（軸名でなく）。出典: tufte-data-viz Agent Skill, Tufte。
7. **密度/タイポ**：箇条書きは**4〜6個・各〜12語**まで。本文は**1920×1080で24px以上**（密な1枚リファレンスは例外的に小さくてよいが、被らせない）。スライド内スクロール禁止。
8. **グリッド・余白・階層**：見出し/小見出し/本文/キャプションの階層を明確に。余白で“呼吸”。フォントは2ペア以内で一貫。
9. **色**：アクセント1色＋深い面1色を基本（当社=赤#AF322C＋ディープインク）。機能色（成長↑↓・人気度）は意味づけに限定。

## C. 実装の質（HTML/CSS が最適な理由）
10. **HTMLが高品質スライドの基盤として有効**：1枚=自己完結HTML、`<deck-stage>`的Web Component＋`<section>`×スライド、**固定1920×1080キャンバスを`transform: scale()`でビューポートに合わせる**。出典: claude-pptx-design（OnlyPaul/GitHub, 3-0検証）。→ レイアウトエンジンが自動整列＝**文字が原理的に被らない**（Slides APIの絶対座標と決定的に違う）。
11. **クローズドループ目視検証は必須**：生成→画像化→**はみ出し/重なり/コントラストを目視点検→修正→再検証**を最低1周。完了宣言の前に必ず“見る”。出典: claude-pptx-design（2-0検証）。当環境では `Google Chrome --headless=new --screenshot` でPNG化→Readで実施。
12. **diagram-as-code**：Mermaid（フロー/マインドマップ/シーケンス）・Chart.js/D3（グラフ）・CSS Grid/Flex（マトリクス/カード）。NL→Mermaidは測定可能タスク（MermaidSeqBench）。画像→Mermaid変換もVLMで可能。

## D. AIワークフロー（生成の質）
13. **コンサルの型をSkill化**：MECE分解 / Day-1仮説 / Minto / アクションタイトル / Top-Downメモ を**離散の再利用Skill**として持たせ、毎回即興でなく**固定構造**を適用。出典: enterprise-ai-skills（GitHub）。
14. **多エージェント自己批評**：Strategist→Builder→**Critic→Fixer** のパイプライン（ストーリーライン＋チャートを入力→自己批評済みデッキ）。出典: enterprise-ai-skills。
15. **構造化指示＋反復**：データ・主張・制約・出力形式を構造で渡し、検証ループで詰める。

## E. ツール比較（編集可能性 × 品質の両立策）
- **Google Slides API**：編集可だが絶対座標で密だと被る。社内体系・リンク運用向き。
- **HTML（Claude Design）**：被りゼロ・Canva級。編集はDesignエディタ、配布はPDF/リンク。対外・作品向き。
- **Presenton（OSS・Apache2.0）★注目**：**HTML+Tailwindのテンプレで“編集可能なPPTX”を自動生成**、`/api/v1/ppt/presentation/generate` の**API**あり。→ **「HTMLの質 × PPTX編集可 × APIでCowork/メンバー自動生成」を同時に満たしうる**。Gamma/Canva/Beautiful.aiの代替。要評価。出典: presenton（GitHub）。
- Gamma/Tome/Beautiful.ai/Canva Magic：手早いが細部の作り込み・ブランド厳密さ・データ密度に限界（一般評）。

## 当プロジェクトへの適用方針
- **対外・作品＝HTML（Claude Design）**を磨く。**業界マップ**等の1枚図解はこの指針で作る（アクションタイトル＋KEY TAKEAWAY＋データインク＋被りゼロ＋目視検証）。
- **engine設計**：データ＋（主張/制約/テーマ）を渡すと、上記の型に沿った1枚図解/デッキを生成する `build_infographic_html.py` を仕様駆動化→Skill化（メンバー/Cowork利用）。
- **Presentonの評価**を次の検討事項に（編集可能PPTX＋APIが刺されば本命候補）。
- 社内研修の体系（41デッキ＋テスト＋WBS）は Google Slides/Sheets 継続。
