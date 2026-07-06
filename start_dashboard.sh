#!/bin/bash
# AI Empire Dashboard 起動スクリプト
# 使い方: bash start_dashboard.sh
# 初回のみ: python3 dashboard/migrate.py を先に実行してください

set -e
cd "/Users/atsuyasato130/Claude AI/ai-empire"

# DB未初期化の場合は自動セットアップ
if [ ! -f "dashboard/empire.db" ]; then
  echo "📦 empire.db を初期化中..."
  python3 dashboard/migrate.py
fi

echo "🚀 AI Empire Dashboard 起動中... http://localhost:8889"
python3 -m uvicorn dashboard.app:app --port 8889 --reload --host 0.0.0.0
