# Tokumori デザインカタログ

> 新規UI作成依頼を受けたとき、まずこのカタログを開いてプリセットを選ぶ。
> 5プリセットを束ねた選択式リファレンス。詳細は各セクション内の参照ファイル行番号にジャンプ。

---

## 0. プリセット一覧（カテゴリ別）

| Preset ID | カテゴリ | 用途 | 主トーン |
|---|---|---|---|
| `sheet/rpo-dark` | スプレッドシート | KPI・進捗・採用ダッシュ | ヘッダ `#37474F` ／ Arial ／ 条件付き三色 |
| `sheet/tokumori-navy` | スプレッドシート | 経営・社内ポータル系 | ヘッダ `#233447` ネイビー ／ アクセント `#DDFC54` ライム |
| `sheet/minimal-mono` | スプレッドシート | マスタ・設定タブ | 白＋黒罫線のみ・装飾最小 |
| `web/tokumori-v4` | Webアプリ | 社内ツール・ダッシュ | navy + lime + Noto Sans JP |
| `slack/block-default` | Slack通知 | 業務通知全般 | formatNotification + ステータス絵文字 |

### 自分の運用ルール

新規UI/スプシ作成依頼を受けたら**必ず**：
1. 該当カテゴリのプリセット一覧を AskUserQuestion で提示
2. 選ばれたプリセットIDをプラン文書冒頭に明記
3. 仕様を本カタログから引いて適用、逸脱は理由を明示

---

## 1. プロンプト4軸（全UIで宣言）

実装前に必ず宣言する。AIを「平均値デザイン」に収束させないための儀式。

```
Purpose:        誰がどう使うか（具体的ユーザー像）
Tone:           文化的参照で極端に振る（例: Bloomberg Terminal × 高級時計）
Constraints:    技術制約（フレームワーク・単一ファイルか・依存範囲）
Differentiation: 記憶に残る「一点」（例: 数値更新時のパタパタアニメ）
```

参照: [global CLAUDE.md](/Users/atsuyasato130/.claude/CLAUDE.md) の「フロントエンド UIデザインルール」

---

## 2. 共通の禁止と推奨

### 禁止フォント（Web）
Inter / Roboto / Arial / system-ui / Space Grotesk

### 推奨フォント組み合わせ（Web）
- 数字・データ: `IBM Plex Mono` or `DM Mono`
- 見出し: `Syne` or `Fraunces`
- 本文: `DM Sans` or `Outfit`
- 日本語UI: `Noto Sans JP`（バクラク準拠）

### 禁止カラーパターン
紫グラデーション+白背景 ／ 均等分散パレット ／ パステル多用

### カラー戦略
メイン1色（深背景）+ アクセント1色のみ。主役を必ず1つ作る。

### 絵文字
UI見出し・ボタン・タブには使わない（[feedback_no_emoji](/Users/atsuyasato130/.claude/projects/-Users-atsuyasato-Claude-AI/memory/feedback_no_emoji.md)）。Slack §5 のステータス記号は例外。

---

## 3. `sheet/rpo-dark` — RPO風ダークグレー（既存採用ダッシュ準拠）

実装の正本: [gas_rpo_v1.js](gas_rpo_v1.js)

### カラートークン（[gas_rpo_v1.js:25-43](gas_rpo_v1.js#L25-L43)）

```js
const COLOR = {
  bgDark:   "#37474F",  // ヘッダ濃グレー（タイトル・列ヘッダ）
  bgPanel:  "#546E7A",  // セクション帯
  bgRow:    "#FFFFFF",  // データ行
  bgRowAlt: "#F5F5F5",  // ストライプ
  ok:       "#C8E6C9",  // 達成（薄緑）
  warn:     "#FFF59D",  // 注意（薄黄）
  alert:    "#FFCDD2",  // 未達（薄赤）
  totalBg:  "#ECEFF1",  // 合計行
  textMain: "#212121",
  textDim:  "#757575",
};
const FONT_HEAD = "Arial";
const FONT_MONO = "Arial"; // 既存タブ統一（数字も装飾Mono使わない）
```

### ヘルパー関数（コピペで再利用可能）

| 関数 | 役割 | 定義位置 |
|---|---|---|
| `_renderTitleBar(sheet, row, totalCols, frozenCols, title, subtitle)` | タイトル帯（マージ・サブタイトル右寄せ） | [L805](gas_rpo_v1.js#L805) |
| `_renderSectionHeader(sheet, row, totalCols, text)` | 中見出し帯（■ XXX） | [L789](gas_rpo_v1.js#L789) |
| `_applyTitleStyle(range)` | タイトル行装飾 | [L1740](gas_rpo_v1.js#L1740) |
| `_applyHeaderStyle(range)` | 列ヘッダ装飾 | [L1750](gas_rpo_v1.js#L1750) |
| `_applyDataStyle(range, opts)` | データ行装飾（1列目左寄せ・他中央） | [L1762](gas_rpo_v1.js#L1762) |
| `_applyTotalRowStyle(range)` | 合計行装飾 | [L1783](gas_rpo_v1.js#L1783) |

### レイアウト原則
- グリッド線は `sheet.setHiddenGridlines(true)` で**必ず**非表示（[L785](gas_rpo_v1.js#L785)・[feedback_rpo_borders](/Users/atsuyasato130/.claude/projects/-Users-atsuyasato-Claude-AI/memory/feedback_rpo_borders.md)）
- ヘッダ行 高さ 28-36 / データ行 24 / 合計行 26
- 罫線は `#37474F` で枠取り、内側は `#E3E7EF` 相当の薄グレー
- 凍結行=1 を基本
- 1列目（ラベル列）だけ左寄せ、他列は中央

### 条件付きセル ルール

| 達成率 / フラグ | 背景 |
|---|---|
| ≥100% / TRUE / OK | `#C8E6C9` |
| 70–99% / 注意 | `#FFF59D` |
| <70% / FALSE / NG | `#FFCDD2` |
| 負差分 | `#FEE2E2`（少し薄め） |

### 適用済みシート
- 採用ダッシュボード（210/220/230/240）
- Spir予約管理（チャネルマスタ・予約管理 N列）

---

## 4. `sheet/tokumori-navy` — ネイビー×ライム（バクラク準拠）

経営系・社内ポータル用。Tokumori Dashboard v4 をスプシに移植したトーン。

### カラートークン

```
ヘッダ:     #233447 (navy)        文字: #FFFFFF
セクション: #1A2737 (navy darker)  文字: #FFFFFF
データ行:   #FFFFFF                文字: #1A2332
ストライプ: #F2F4F7
アクセント: #DDFC54 (lime) ← 重要数値のセル背景
リンク:     #0E63C4
合計行:     #E3E7EF
```

### フォント
- 見出し・本文: `Noto Sans JP`（Google FontsからImport可能。GASでは `setFontFamily("Noto Sans JP")`）
- 数値: `IBM Plex Mono`

### レイアウト
- 凍結行=1、凍結列=2（社名/学生名列を固定）
- 重要KPIセルは背景 `#DDFC54` + 黒太字で「主役」を作る
- 罫線は `#E3E7EF`、ヘッダ下のみ navy 2pxで強調

### 使うべきケース
- 経営報告・予算管理・全社KPI
- バクラク的なクリーンさが求められるとき

### 使うべきでないケース
- 採用ダッシュ等の既存RPOラインナップ（`sheet/rpo-dark` で揃える）

---

## 5. `sheet/minimal-mono` — マスタ・設定タブ用

装飾を最小にしてデータの編集体験を優先する低密度プリセット。

### スタイル
- ヘッダ: 白背景 + 下線 1px `#000`、太字、Arial 10
- データ行: 白背景、グリッド線は**残す**（編集中にセル境界を明示）
- 列幅は内容に合わせて自動。装飾色は使わない
- TRUE/FALSE 等は条件付きで微妙に着色（薄緑 `#E8F5E9` / 薄赤 `#FFEBEE`）

### 使うべきケース
- 設定タブ・担当者マスタ・チャネルマスタの「裏方」用途
- 印刷する可能性があるシート

---

## 6. `web/tokumori-v4` — Webアプリ標準

実装の正本: [feedback_dashboard_v4_design](/Users/atsuyasato130/.claude/projects/-Users-atsuyasato-Claude-AI/memory/feedback_dashboard_v4_design.md)

### CSS変数（コピペ用）

```css
:root {
  --navy:    #233447;
  --navy2:   #1a2737;
  --lime:    #DDFC54;
  --blue:    #0E63C4;
  --blue-bg: #EBF3FF;
  --bg:      #F2F4F7;
  --surface: #FFFFFF;
  --border:  #E3E7EF;
  --text:    #1A2332;
  --muted:   #64748B;
  --green:   #16A34A;
  --red:     #DC2626;
  --amber:   #D97706;
  --radius:  6px;
  --font-jp: "Noto Sans JP", sans-serif;
  --font-num: "IBM Plex Mono", monospace;
}
```

### レイアウト原則
- サイドバー: `--navy` 固定、アクティブ項目はライム左ボーダー3px
- カード: 白、border 1px `--border`、shadow極薄、radius **6px**
- KPIは stat-grid（gap=1px, background=border色で疑似罫線）
- 最重要指標はネイビーヒーローカード（`background: var(--navy)`）で最上部
- タブUI: 丸ピル NG・アンダーラインタブ採用（バクラク準拠）
- ボタン: CTA=`--lime`、通常=`--navy`、ゴースト=`border:1px solid var(--border)`

### チャートカラー
- 損益折れ線: `#DDFC54`
- 資産推移: `#0E63C4`
- 日別棒: 正=`rgba(22,163,74,.75)` / 負=`rgba(220,38,38,.75)`
- ツールチップ背景: `#233447`

### モバイル
- サイドバーはスライドイン+オーバーレイ
- KPI 4col→2col、3col→2col、380px以下は1col
- 高さは `svh`（仮想キーボード対応）
- タイムバッジ等は非表示

### 適用済みプロダクト
- Tokumori Dashboard（port 8890）
- 28卒計画/27卒振り返り資料（スプシ移植も同トーン）

---

## 7. `slack/block-default` — Slack通知 標準

実装の正本: [gas_lg_ca_v5_7.js](gas_lg_ca_v5_7.js)（`formatNotification` ヘルパー）

### `formatNotification` ヘルパー（コピペ）

```js
function formatNotification({ statusEmoji, title, rowNo, account, grade, sns, lgUid, caName, detail, reporter }) {
  return `${statusEmoji} *#${rowNo} ${title}*\n` +
         `学生: ${account}${grade || sns ? `（${[grade,sns].filter(Boolean).join("・")}）` : ""}\n` +
         (lgUid ? `担当LG: <@${lgUid}>\n` : "") +
         (caName ? `担当CA: ${caName}\n` : "") +
         (detail ? `詳細: ${detail}\n` : "") +
         (reporter ? `\n報告者: ${reporter}` : "");
}
```

### ステータス絵文字（Slackは例外的に使用OK）

| 用途 | 絵文字 |
|---|---|
| 確認・承認 | `:white_check_mark:` `✅` |
| 警告・要対応 | `:warning:` `⚠️` |
| エラー・飛び | `:no_entry:` `🚫` |
| 再回収・リトライ | `:arrows_counterclockwise:` `🔁` |
| 日程入力 | `:calendar:` `📅` |
| 情報 | `:information_source:` `ℹ️` |

### Block構成パターン

**単発通知（formatNotification使用）**
```
section (mrkdwn) → 本文
divider
context → タイムスタンプ・実行者
```

**週次レポート**
```
header → タイトル
section → KPIブロック × 複数
divider
section → アクション項目（メンション含む）
context → 自動更新時刻
```

### チャンネル運用
- 飛びチャンネル: `C0A4VGTAPRB`
- 既存search_channels: `C0A4SJDDUV9`

---

## 8. 参照ファイル

| ファイル | 内容 |
|---|---|
| [gas_rpo_v1.js](gas_rpo_v1.js) | RPO風スプシ実装の正本（ヘルパー＋色トークン） |
| [gas_lg_ca_v5_7.js](gas_lg_ca_v5_7.js) | LG/CA 最新版（Block Kit / formatNotification） |
| [spir_yoyaku_gas.gs](spir_yoyaku_gas.gs) | Spir予約自動管理 v9.1（チャネルマスタ参照例） |
| [global CLAUDE.md](/Users/atsuyasato130/.claude/CLAUDE.md) | プロンプト4軸 / 禁止リスト の正本 |
| [feedback_dashboard_v4_design](/Users/atsuyasato130/.claude/projects/-Users-atsuyasato-Claude-AI/memory/feedback_dashboard_v4_design.md) | Tokumori v4 詳細 |
| [feedback_frontend_design](/Users/atsuyasato130/.claude/projects/-Users-atsuyasato-Claude-AI/memory/feedback_frontend_design.md) | 4軸プロンプト・禁止フォント |
| [feedback_no_emoji](/Users/atsuyasato130/.claude/projects/-Users-atsuyasato-Claude-AI/memory/feedback_no_emoji.md) | UI絵文字禁止ルール |
| [feedback_rpo_borders](/Users/atsuyasato130/.claude/projects/-Users-atsuyasato-Claude-AI/memory/feedback_rpo_borders.md) | RPOタブの罫線運用 |
