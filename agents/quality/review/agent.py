#!/usr/bin/env python3
"""
ReviewAgent — コード品質自動レビューエージェント

ファイルパスを受け取り、Claude APIでレビューを実行する。
結果を Slack に投稿し、logs/code_reviews/ に JSON で保存する。
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# プロジェクトルート設定
_REVIEW_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR   = str(Path(_REVIEW_DIR).parents[2])  # ai-empire/

sys.path.insert(0, _ROOT_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(_ROOT_DIR, "agents/hr_support/config/.env"))

import anthropic

# ── ログ設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(
            os.path.join(_ROOT_DIR, "logs", "review_agent.log"),
            encoding="utf-8",
        ),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("quality.review")

# ── 設定
ANTHROPIC_API_KEY      = os.environ.get("ANTHROPIC_API_KEY", "")
SLACK_BOT_TOKEN        = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_REVIEW_CHANNEL   = os.environ.get("SLACK_REVIEW_CHANNEL", "")  # 例: C0XXXXXXXX
CLAUDE_MODEL           = "claude-sonnet-4-6"
MAX_FILE_CHARS         = 12000  # レビュー対象の最大文字数

# ── レビュー対象から除外するパターン
_SKIP_PATTERNS = [
    "__pycache__",
    "_deprecated",
    ".pyc",
    "node_modules",
    "venv",
    ".env",
    "test_",
    "_test.py",
]

_SYSTEM_PROMPT = """\
あなたは経験豊富なPythonテックリードです。コードを以下の5軸でレビューし、
開発者がすぐにアクションできる具体的なフィードバックを提供します。

## レビュー軸（優先順位順）
1. 🔴 セキュリティ: APIキーのハードコード / SQL injection / 外部入力のバリデーション不足
2. 🟠 バグリスク: 境界値・例外処理漏れ / レースコンディション / None参照
3. 🟡 パフォーマンス: 不要なAPI呼び出し / N+1 / ループ内の重い処理
4. 🟢 保守性: 関数の単責任 / 重複コード / 命名規則（snake_case等）
5. 🔵 スタイル: コーディング規約 / コメントの適切さ

## 出力形式（必ずこの形式で）
```
総合評価: [A/B/C/D] — [一言コメント]

🔴 Critical（必ず修正）
- [行番号] [問題] → [修正案]

🟠 Warning（修正推奨）
- [行番号] [問題] → [改善案]

🟢 Good（良い点）
- [具体的に評価した点]

📊 スコア
セキュリティ: X/25 | バグリスク: X/25 | パフォーマンス: X/25 | 保守性: X/25 | 合計: X/100
```

## 禁止事項
- 根拠なしの評価
- 修正案のない指摘
- セキュリティリスクの軽視
- 問題がない場合でも「問題なし」だけで終わらせない（良い点を必ず挙げる）
"""


def should_skip(filepath: str) -> bool:
    """レビュー対象外ファイルか判定する。"""
    return any(pat in filepath for pat in _SKIP_PATTERNS)


def review_file(filepath: str) -> dict | None:
    """
    指定ファイルをClaude APIでレビューする。

    Returns:
        レビュー結果dict、またはNone（スキップ / エラー）
    """
    if should_skip(filepath):
        logger.info("スキップ: %s", filepath)
        return None

    if not os.path.exists(filepath):
        logger.warning("ファイルが存在しない: %s", filepath)
        return None

    try:
        with open(filepath, encoding="utf-8") as f:
            code = f.read()
    except Exception as e:
        logger.error("ファイル読み込みエラー: %s — %s", filepath, e)
        return None

    if len(code.strip()) < 50:
        logger.info("コードが短すぎるためスキップ: %s", filepath)
        return None

    if not ANTHROPIC_API_KEY:
        logger.error("ANTHROPIC_API_KEY が未設定")
        return None

    rel_path = os.path.relpath(filepath, _ROOT_DIR)
    user_message = f"以下のファイルをレビューしてください。\n\nファイル: {rel_path}\n\n```python\n{code[:MAX_FILE_CHARS]}\n```"
    if len(code) > MAX_FILE_CHARS:
        user_message += f"\n\n※ファイルが長いため先頭 {MAX_FILE_CHARS} 文字のみ対象"

    logger.info("レビュー開始: %s", rel_path)

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2000,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        review_text = message.content[0].text
    except Exception as e:
        logger.error("Claude API エラー: %s", e)
        return None

    result = {
        "filepath": filepath,
        "rel_path": rel_path,
        "reviewed_at": datetime.now().isoformat(),
        "review_text": review_text,
        "lines": len(code.splitlines()),
    }

    _save_review_log(result)
    logger.info("レビュー完了: %s", rel_path)
    return result


def _save_review_log(result: dict) -> None:
    """レビュー結果を logs/code_reviews/ に保存する。"""
    log_dir = os.path.join(_ROOT_DIR, "logs", "code_reviews")
    os.makedirs(log_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(log_dir, f"review_{ts}.json")
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        logger.debug("ログ保存: %s", filename)
    except Exception as e:
        logger.error("ログ保存エラー: %s", e)


def post_to_slack(result: dict) -> None:
    """レビュー結果を Slack の SLACK_REVIEW_CHANNEL に投稿する。"""
    if not SLACK_BOT_TOKEN or not SLACK_REVIEW_CHANNEL:
        logger.warning("Slack 投稿スキップ（SLACK_BOT_TOKEN / SLACK_REVIEW_CHANNEL 未設定）")
        return

    rel_path  = result["rel_path"]
    review    = result["review_text"]
    lines     = result["lines"]

    # 総合評価行を抽出（先頭行）
    grade_line = next(
        (ln for ln in review.splitlines() if ln.startswith("総合評価:")),
        "総合評価: 不明"
    )
    grade = grade_line.split("—")[0].replace("総合評価:", "").strip()
    grade_emoji = {"A": "🟢", "B": "🟡", "C": "🟠", "D": "🔴"}.get(grade, "⚪")

    # Slack メッセージ（3000文字制限考慮）
    review_body = review if len(review) <= 2800 else review[:2800] + "\n...(省略)"
    msg = (
        f"{grade_emoji} *コードレビュー完了* — `{rel_path}` ({lines}行)\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"```\n{review_body}\n```"
    )

    try:
        import urllib.request
        payload = json.dumps({
            "channel": SLACK_REVIEW_CHANNEL,
            "text": msg,
            "username": "Review Agent",
            "icon_emoji": ":mag:",
        }).encode()
        req = urllib.request.Request(
            "https://slack.com/api/chat.postMessage",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            resp = json.loads(r.read())
            if not resp.get("ok"):
                logger.error("Slack 投稿エラー: %s", resp.get("error"))
            else:
                logger.info("Slack 投稿完了: %s", rel_path)
    except Exception as e:
        logger.error("Slack 投稿例外: %s", e)


def run(filepath: str) -> None:
    """レビューを実行してSlackに投稿する（外部から呼び出すエントリポイント）。"""
    result = review_file(filepath)
    if result:
        post_to_slack(result)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使い方: python3 agent.py <filepath>")
        sys.exit(1)
    run(sys.argv[1])
