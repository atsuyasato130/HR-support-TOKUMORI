#!/usr/bin/env python3
"""日次ランナー：★歩留まり分析ダッシュボード（②）を再生成する。
launchd/cron から毎日呼び出す想定。ログは stdout。"""
import datetime as dt
import sys
import os

sys.path.insert(0, os.path.expanduser("~/Claude AI"))
import build_hrmos_funnel_v2  # noqa: E402

if __name__ == "__main__":
    print(f"[daily_run] start {dt.datetime.now():%Y-%m-%d %H:%M:%S}")
    build_hrmos_funnel_v2.main()
    print("[daily_run] done")
