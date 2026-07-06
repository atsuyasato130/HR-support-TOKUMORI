#!/bin/zsh
# DOTZ ★KPIサマリー 自動再生成ラッパー（launchdから平日9時/18時に起動）
# ログは hostname 付きで保存（Syncthing衝突防止）
SCRIPT="/Users/atsuyasato130/Claude AI/build_dotz_kpi.py"
LOG="/Users/atsuyasato130/Claude AI/logs/dotz_kpi_$(hostname -s).log"

echo "===== $(date '+%Y-%m-%d %H:%M:%S') start =====" >> "$LOG"
/usr/bin/python3 "$SCRIPT" >> "$LOG" 2>&1
echo "===== $(date '+%Y-%m-%d %H:%M:%S') exit=$? =====" >> "$LOG"
