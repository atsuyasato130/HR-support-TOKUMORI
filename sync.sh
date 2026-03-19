#!/bin/bash
# ============================================================
# sync.sh — TOKUMO OS 安全同期スクリプト
# GitHub への安全な自動同期（private/ 漏洩防止付き）
# ============================================================

set -e

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_ROOT"

echo "=================================================="
echo " TOKUMO OS — GitHub 安全同期"
echo "=================================================="

# ----------------------------------------------------------
# [Safety Check] private/ が同期対象に含まれていないか確認
# ----------------------------------------------------------
echo ""
echo "[1/4] Safety Check: private/ の漏洩チェック中..."

PRIVATE_LEAKED=$(git ls-files private/ 2>/dev/null)
if [ -n "$PRIVATE_LEAKED" ]; then
  echo "ERROR: private/ 内のファイルがインデックスに含まれています！"
  echo "$PRIVATE_LEAKED"
  echo "git rm -r --cached private/ を実行してから再試行してください。"
  exit 1
fi

ENV_LEAKED=$(git ls-files | grep -E "(^|\/)\.env" 2>/dev/null)
if [ -n "$ENV_LEAKED" ]; then
  echo "ERROR: .env ファイルがインデックスに含まれています！"
  echo "$ENV_LEAKED"
  exit 1
fi

echo "  OK: private/ はインデックスに含まれていません"
echo "  OK: .env ファイルはインデックスに含まれていません"

# ----------------------------------------------------------
# [Stage & Commit] 変更をコミット
# ----------------------------------------------------------
echo ""
echo "[2/4] 変更をステージング中..."

git add -A

if git diff --cached --quiet; then
  echo "  変更はありません。同期をスキップします。"
  exit 0
fi

TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")
COMMIT_MSG="Update by TOKUMO OS: ${TIMESTAMP}"

echo "[3/4] コミット中: ${COMMIT_MSG}"
git commit -m "$COMMIT_MSG"

# ----------------------------------------------------------
# [Push] GitHub の main ブランチへプッシュ
# ----------------------------------------------------------
echo ""
echo "[4/4] GitHub (main) へプッシュ中..."
git push origin main

echo ""
echo "=================================================="
echo " 同期完了: ${TIMESTAMP}"
echo "=================================================="
echo ""
echo "アップロード済みファイル一覧:"
git ls-files
echo ""
echo "宣誓: private/ は GitHub にアップロードされていません。"
