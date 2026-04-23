# CA評価 × 学生評価 自動化システム 設計書

**作成日:** 2026-04-21
**目的:** tldv録音 → LLM分析 → SF自動入力 を軸に、CAの面談力向上と学生評価の客観化を両立する評価システムを設計する。
**関連研究:** 本設計は3本のディープリサーチ（Gong/Chorus営業指標・Big5/STAR/Korn Ferry学生評価・BEI/構造化面接学術）を統合したもの。

---

## 1. アーキテクチャ全体像

```
tldv API (TranscriptReady Webhook)
     ↓
meeting_router (既実装)
     ↓
 ┌───────────────┴───────────────┐
面談ルート                       商談ルート
     ↓                             ↓
evaluation_engine                notion_minutes_writer
  ├─ CA_Scorer (10指標)           (既実装)
  ├─ Student_Scorer (15指標)
  └─ Question_Coverage (30Q整合)
     ↓
SF更新 + CA育成レポート
```

---

## 2. CA評価スコアリング（10指標）

録音音声のタイムスタンプ付き文字起こしから自動算出。6指標は正規表現/カウントベース、4指標はClaudeで意味解析。

| # | 指標 | 測定方法 | 業界標準値 | 出典 |
|---|---|---|---|---|
| 1 | **Talk-to-Listen Ratio** | CA発話秒 / 学生発話秒 | 40-45% (CA側) | Gong Labs "Golden Ratio" |
| 2 | **Longest Monologue** | CA最長発話秒 | ≤90秒（150秒赤信号） | Atrium/Gong |
| 3 | **Open-ended Q Rate** | Yes/No以外の質問比率 | ≥60% | Gong sales-stats |
| 4 | **Question Count** | 面談あたり総質問数 | 11-16問 | Gong (受注=15-16問) |
| 5 | **Why深掘り回数 (Implication)** | "なぜ/what if/具体的には" 類型出現回数 | トップCA=平均の4倍 | SPIN/Highspot |
| 6 | **Patience (応答ラグ)** | 学生発話終了→CA発話開始の秒数平均 | ≥0.5秒 | Zoom Revenue Accelerator |
| 7 | **Filler Words/分** | "えー/あー/まぁ"頻度 | <3回/分 | Zoom Library |
| 8 | **Talk Speed (WPM)** | CA発話単語数/分 | 140-160WPM | 同上 |
| 9 | **Sentiment Drift** | 学生感情の面談前半→後半変化 | ポジティブ推移が理想 | Chorus.ai |
| 10 | **30Q Coverage Rate** | 必須30問中カバーした問数/30 | ≥80%（Aランク） | 自社設計 |

### CAスコア算出式（暫定）

```
CA_Overall = 
  (Talk比適合度 × 0.15) + 
  (Monologue適合度 × 0.10) + 
  (Open-Q率 × 0.15) + 
  (Q数適合度 × 0.10) + 
  (Implication深掘り率 × 0.20) +  ← トップCAの差別化特徴量
  (Patience適合度 × 0.05) + 
  (Filler減点 × 0.05) + 
  (Speed適合度 × 0.05) + 
  (Sentiment Drift × 0.05) + 
  (30Q Coverage × 0.10)
```

---

## 3. 学生評価SFカスタムフィールド（15項目）

tldv録音から自動採点。既存Field21__cメモとは別に、定量スコアを持つフィールドを新設する。

| # | SF API名 | 型 | 評価観点 | 理論根拠 |
|---|---|---|---|---|
| 1 | `Logic_Score__c` | Number(1-5) | 論理構成力（MECE・結論先行） | McKinsey/ガクチカ論理性 |
| 2 | `Reproducibility_Score__c` | Number(1-5) | 再現性（抽象化された行動特性） | ガクチカ再現性ルーブリック |
| 3 | `Growth_Mindset_Score__c` | Number(1-5) | 成長志向・Receptivity to Feedback | DDI/McKinsey Growth |
| 4 | `Learning_Agility_Score__c` | Number(1-5) | 学習敏捷性（5因子平均） | Korn Ferry ViaEDGE |
| 5 | `Drive_Score__c` | Number(1-5) | 実行力・オーナーシップ | McKinsey PEI Drive |
| 6 | `Leadership_Score__c` | Number(1-5) | 巻き込み力・多様性包摂 | McKinsey PEI Leadership |
| 7 | `Connection_Empathy_Score__c` | Number(1-5) | 傾聴・共感・信頼構築 | McKinsey PEI Connection |
| 8 | `Listening_Score__c` | Number(1-5) | 傾聴力（発話比・質問返し） | 経産省 社会人基礎力 |
| 9 | `Expression_Score__c` | Number(1-5) | 発信力（結論先行度） | 同上 |
| 10 | `Conscientiousness_Score__c` | Number(1-5) | 誠実性（最強の業績予測因子） | Big Five (OCEAN) |
| 11 | `Openness_Score__c` | Number(1-5) | 開放性（新環境適応） | Big Five (OCEAN) |
| 12 | `STAR_Completeness__c` | Number(1-5) | STAR4要素の充足度平均 | BARS/MIT CAPD |
| 13 | `Motivation_Authenticity__c` | Number(1-5) | 「なぜ」の真正性 | ガクチカ三段階深掘り |
| 14 | `Potential_Quadrant__c` | Picklist | 9-boxグリッド位置 | Korn Ferry |
| 15 | `Evaluation_Summary__c` | Long Text | LLM所見（タイムスタンプ引用付き） | 統合所見 |

**+ 信頼度フィールド:**
- `Evaluation_Confidence__c` (Number 0.0-1.0): Claude判定のconfidence。<0.7は人手レビュー待ち。

---

## 4. CA面談標準スクリプト（30質問セット）

**理論根拠:** Schmidt&Hunter(1998)の構造化面接の予測的妥当性 r=.51、McClelland BEI法、Schein Career Anchors。

### A. 基本情報（5問）
1. 自己紹介と現在のゼミ／研究テーマを1分で
2. 学業以外で最も時間を使っていることは？
3. 現在の就活状況（選考中企業数・内定数）
4. 就活開始時期と情報源
5. 家族・身近な人からの期待や影響

### B. 就活軸（7問）※Schein Career Anchors
6. 企業選びで譲れない3条件（優先順位付き）
7. 逆に絶対に避けたい条件
8. 5年後・10年後に実現したい状態
9. 給与・やりがい・安定性の優先順位
10. 大企業／ベンチャーの志向と理由
11. 業界を絞っている／広げている理由
12. 勤務地・働き方の希望

### C. 過去経験（BEI型 8問）
13. 学生時代に最も熱中したこと、その理由
14. 直近で成功した具体的エピソード（S/T/A/R）
15. 直近で失敗した経験と学び
16. 複数人で何かを成し遂げた経験
17. 困難な人間関係をどう乗り越えたか
18. 自分でゼロから始めた経験
19. 長期間継続できたこと、その動機源
20. アルバイト・インターンで褒められた／叱られた経験

### D. コミュニケーション（5問）
21. 意見の違う相手を説得した経験
22. 初対面の人と関係を築く工夫
23. チームで板挟みになったときの対応
24. 周囲から自分はどんな人と言われるか
25. フィードバックをもらって行動を変えた経験

### E. ポテンシャル／Learning Agility（5問）
26. 最近学んで面白かったこと
27. 未知の状況に飛び込んだ経験
28. 自分の弱みと、それに対する取り組み
29. 「当たり前」を疑って変えた経験
30. なぜ働くのか／仕事に何を求めるか

**各質問のマッピング:**
- A群（5問） → 基本情報系Field21__cへ
- B群（7問） → JobSearchAxisThree / FutureDreamAndLifeMission 等
- C群（8問） → STAR_Completeness / Drive / Leadership / Growth_Mindset
- D群（5問） → Listening / Expression / Connection_Empathy
- E群（5問） → Learning_Agility / Openness / Motivation_Authenticity

---

## 5. 実装ロードマップ

### Phase A: 評価エンジン基盤（1-2週間）
- [ ] SFカスタムフィールド15項目をSalesforce Metadata APIで作成
- [ ] `evaluation_engine.py` 作成（CA_Scorer + Student_Scorer + Question_Coverage）
- [ ] Whisper or tldv Transcript API からの話者分離付き文字起こし確認
- [ ] 6つの規則ベース指標（Talk比/Monologue/Q数/Filler/Patience/Speed）実装
- [ ] 4つのLLM指標（Open-Q/Implication/Sentiment/Coverage）実装

### Phase B: 学生評価LLM採点（1週間）
- [ ] `student_scorer.py` 実装（Claude Sonnetで15項目自動採点）
- [ ] 過去面談データ10件でキャリブレーション
- [ ] Confidence閾値の調整

### Phase C: CA育成レポート自動生成（1週間）
- [ ] 面談後レポート生成（強み・改善点・次回目標）
- [ ] CA個人別ダッシュボード（port 8890 追加ページ）
- [ ] 月次CAランキング自動集計

### Phase D: 研修モード（新人CA用）（1-2週間）
- [ ] 30Q Coverageが<50%なら「次の質問提案」を面談中にLINEへ通知
- [ ] ロールプレイ用のシミュレーション面談（Claude = 学生役）
- [ ] ベテランCAの面談録音を「お手本集」として分析・ナレッジ化

### Phase E: 運用自動化（1週間）
- [ ] tldv Webhook → evaluation_engine → SF反映の全自動化
- [ ] 月次KPIダッシュボード（CA成長曲線・学生品質分布）

---

## 6. 研修活用の設計

新人CAが「採点される」のではなく「育つ」システムに。

### フィードバックループ
1. **面談直後（5分以内）**: Slackに3点フィードバック（良かった点/改善点/次回の具体アクション）
2. **週次（毎週金曜）**: CA個人のスコア推移レポート
3. **月次**: 30Q Coverage が80%未満のCAには該当質問の改善ワークショップ
4. **四半期**: ベテランCAとスコア比較、Implication深掘り回数の差分分析

### ロールプレイ機能
- Claude=学生役でシミュレーション面談（録音不要）
- 実際の学生背景をパターン化（Aタイプ=安定志向、Cタイプ=稼ぎたい等）
- 新人CAが1日20分×30日で30Q全対応を体得

---

## 7. 差別化ポイント

Gong/Chorusは商談向け・英語主体。**ai-empireの優位性**:
1. 日本語CA × 学生向けのドメイン特化
2. Implication深掘り×30Q CoverageというSPIN×構造化面接のハイブリッド指標
3. CAスコアと学生評価を同時出力（他社はどちらか片方のみ）
4. 承諾率/マッチ率との因果推論で予測精度向上
5. 研修モード（新人育成）を標準装備

---

## 8. 参考文献（主要出典）

**CA評価:**
- [Gong Labs Talk-to-Listen Ratio](https://www.gong.io/resources/labs/talk-to-listen-conversion-ratio/)
- [Gong 2025 Sales Insights](https://www.gong.io/blog/the-best-sales-insights-of-2025)
- [Highspot SPIN Selling](https://www.highspot.com/blog/spin-selling/)

**学生評価:**
- [Korn Ferry High-Potential Talent](https://www.kornferry.com/content/dam/kornferry/docs/pdfs/kfi_identifying-high-potential-talent.pdf)
- [DDI Global Leadership Forecast 2025](https://www.ddi.com/research/global-leadership-forecast-2025)
- [MIT CAPD STAR Method](https://capd.mit.edu/resources/the-star-method-for-behavioral-interviews/)
- [McKinsey PEI Guide Fall 2025](https://mece.academy/resources/mckinsey-pei-guide-fall-2025)
- [Big Five Meta-analysis (Science Direct)](https://www.sciencedirect.com/science/article/abs/pii/S0167487022000812)

**面談設計:**
- [McClelland 1973 "Testing for Competence"](https://www.therapiebreve.be/documents/mcclelland-1973.pdf)
- [Schmidt & Hunter 1998 Meta-Analysis](https://firstpersonnel.org/wp-content/uploads/2013/10/Summary-Schmidt-Hunter-1998.pdf)
- [Schmidt, Oh, Shaffer 2016 Update](https://home.ubalt.edu/tmitch/645/session%204/Schmidt%20&%20Oh%20validity%20and%20util%20100%20yrs%20of%20research%20Wk%20PPR%202016.pdf)
- [DDI Behavioral Interviewing](https://www.ddi.com/solutions/behavioral-interviewing)
- [SIOP Cognitive Ability Research 2022](https://www.siop.org/tip-article/is-cognitive-ability-the-best-predictor-of-job-performance-new-research-says-its-time-to-think-again/)
