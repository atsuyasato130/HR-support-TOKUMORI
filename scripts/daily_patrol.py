#!/usr/bin/env python3
"""
Daily Patrol — Tokumori 日次パトロール統合スクリプト

フロー:
  1. Patrol Agent  — 全ジョブのヘルスチェック + Claude 診断
  2. Repair Agent  — エラージョブの自動修復
  3. 修復後再チェック — 修復結果を再確認
  4. メール送信    — 毎朝 9:00 に atsuya_sato@tokumori.co.jp へ報告

実行方法:
  python3 scripts/daily_patrol.py           # 通常実行
  python3 scripts/daily_patrol.py --no-mail # メール送信なし（テスト用）
  python3 scripts/daily_patrol.py --quick   # Claude診断スキップ

launchd:
  com.atsuyasato.ai-empire-patrol-daily（毎朝 9:00 JST）
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv
load_dotenv(_ROOT / "config" / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("DailyPatrol")

REPORT_TO = "atsuya_sato@tokumori.co.jp"


# ─── メール送信 ───────────────────────────────────────────────────────────────

def _build_email_body(
    patrol_report,
    repair_report,
    recheck_report,
) -> tuple[str, str]:
    """
    メール件名と本文を生成する。

    Returns:
        (subject, body_html)
    """
    from agents.quality.patrol.agent import PatrolReport
    from agents.quality.repair.agent import RepairReport

    now = datetime.now().strftime("%Y/%m/%d %H:%M")
    overall = patrol_report.overall_status
    status_emoji = {"OK": "✅", "WARNING": "⚠️", "ERROR": "❌", "CRITICAL": "🚨"}.get(overall, "❓")

    subject = f"[Tokumori] {status_emoji} 日次パトロール報告 — {overall} ({now})"

    # ジョブ行を生成
    def job_row(j) -> str:
        icons = {"ok": "✅", "warning": "⚠️", "error": "❌", "stale": "🔄", "unknown": "❓"}
        icon = icons.get(j.status, "❓")
        critical = " <b>[重要]</b>" if j.critical else ""
        diag = f"<br>&nbsp;&nbsp;&nbsp;→ {j.diagnosis}" if j.diagnosis and j.status != "ok" else ""
        return (
            f"<tr>"
            f"<td>{icon}</td>"
            f"<td>{j.name}{critical}</td>"
            f"<td>{j.system}</td>"
            f"<td>{j.status.upper()}</td>"
            f"<td>{j.last_activity}</td>"
            f"</tr>"
            f"{'<tr><td colspan=5>' + diag + '</td></tr>' if diag else ''}"
        )

    jobs_html = "\n".join(job_row(j) for j in patrol_report.jobs)

    # 修復アクション行
    repair_rows = ""
    if repair_report and repair_report.actions:
        rows = []
        for a in repair_report.actions:
            icon = "✅" if a.success else "❌"
            rows.append(
                f"<tr><td>{icon}</td><td>{a.job_name}</td>"
                f"<td>{a.action}</td><td>{a.message[:80]}</td></tr>"
            )
        repair_rows = f"""
        <h3 style="color:#e67e22;">🔧 自動修復アクション ({repair_report.repaired_count}/{len(repair_report.actions)}件成功)</h3>
        <table border="1" cellpadding="5" style="border-collapse:collapse;font-size:13px;">
          <tr style="background:#f39c12;color:white;">
            <th>結果</th><th>ジョブ名</th><th>アクション</th><th>詳細</th>
          </tr>
          {''.join(rows)}
        </table>
        """

    # 手動対応リスト
    manual_html = ""
    if repair_report:
        manual = repair_report.manual_needed
        if manual:
            items = "".join(f"<li><b>{a.job_name}</b>: {a.reason}</li>" for a in manual)
            manual_html = f"""
            <div style="background:#fadbd8;border:1px solid #e74c3c;padding:10px;margin:10px 0;border-radius:5px;">
              <h3 style="color:#c0392b;">🚨 手動対応が必要なジョブ</h3>
              <ul>{items}</ul>
            </div>
            """

    # 再チェック結果
    recheck_html = ""
    if recheck_report:
        recheck_html = f"""
        <h3 style="color:#27ae60;">🔄 修復後の再チェック結果: {recheck_report.overall_status}</h3>
        <p>正常: {len(recheck_report.ok_jobs)}件 / 警告: {len(recheck_report.warning_jobs)}件 / エラー: {len(recheck_report.error_jobs)}件</p>
        """

    body = f"""
    <html><body style="font-family:sans-serif;max-width:800px;margin:0 auto;">
    <h2 style="color:#2c3e50;">Tokumori 日次パトロール報告</h2>
    <p style="color:#7f8c8d;">生成時刻: {now} / patrol_id: {patrol_report.patrol_id}</p>

    <div style="background:{'#eafaf1' if overall=='OK' else '#fef9e7' if overall=='WARNING' else '#fdedec'};
                border:2px solid {'#27ae60' if overall=='OK' else '#f39c12' if overall=='WARNING' else '#e74c3c'};
                padding:15px;border-radius:8px;margin-bottom:20px;">
      <h3 style="margin:0;">全体ステータス: {status_emoji} {overall}</h3>
      <p style="margin:5px 0 0;">
        ✅ 正常: {len(patrol_report.ok_jobs)}件 &nbsp;
        ⚠️ 警告: {len(patrol_report.warning_jobs)}件 &nbsp;
        ❌ エラー: {len(patrol_report.error_jobs)}件 &nbsp;
        🔄 停止疑い: {len(patrol_report.stale_jobs)}件
      </p>
    </div>

    {manual_html}

    <h3 style="color:#2980b9;">📋 全ジョブ一覧</h3>
    <table border="1" cellpadding="5" style="border-collapse:collapse;font-size:13px;width:100%;">
      <tr style="background:#2980b9;color:white;">
        <th>状態</th><th>ジョブ名</th><th>システム</th><th>ステータス</th><th>最終活動</th>
      </tr>
      {jobs_html}
    </table>

    {repair_rows}
    {recheck_html}

    <hr>
    <p style="color:#95a5a6;font-size:12px;">
      このメールは Tokumori Daily Patrol により自動送信されました。<br>
      返信不要 / 問題がある場合は直接 Claude Code で確認してください。
    </p>
    </body></html>
    """

    return subject, body


def _send_email(subject: str, body_html: str, send_mail: bool = True) -> bool:
    """Gmail API または SMTP でメールを送信する。"""
    if not send_mail:
        logger.info(f"[DRY-RUN] メール送信スキップ: {subject}")
        return True

    # ai-empire の Gmail クライアントを使用
    try:
        from agents.hr_support.utils.gmail_client import GmailClient
        client = GmailClient()
        client.send(
            to=REPORT_TO,
            subject=subject,
            body=body_html,
            content_type="text/html",
        )
        logger.info(f"メール送信完了: {REPORT_TO}")
        return True
    except Exception as e:
        logger.error(f"Gmail Client 失敗: {e}")

    # フォールバック: smtplib（環境変数 SMTP_* が設定されている場合）
    try:
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        smtp_user = os.environ.get("SMTP_USER", "")
        smtp_pass = os.environ.get("SMTP_PASS", "")

        if not smtp_user or not smtp_pass:
            logger.warning("SMTP 認証情報が未設定 — メール送信をスキップ")
            return False

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = smtp_user
        msg["To"] = REPORT_TO
        msg.attach(MIMEText(body_html, "html", "utf-8"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, REPORT_TO, msg.as_string())

        logger.info(f"SMTP 送信完了: {REPORT_TO}")
        return True

    except Exception as e:
        logger.error(f"SMTP 送信失敗: {e}")
        return False


# ─── メインフロー ─────────────────────────────────────────────────────────────

def main(quick: bool = False, send_mail: bool = True) -> dict:
    """
    日次パトロールのメインフロー。

    1. パトロール（全ジョブ監視）
    2. 修復（エラージョブを自動修復）
    3. 再チェック（修復結果を確認）
    4. メール送信（朝9時報告）
    """
    logger.info("=" * 55)
    logger.info("  Tokumori 日次パトロール 開始")
    logger.info("=" * 55)

    # ── Step 1: パトロール ────────────────────────────────────────────────────
    logger.info("\n[Step 1] パトロール実行中...")
    from agents.quality.patrol.agent import run as patrol_run
    patrol_report = patrol_run(quick=quick, log_dashboard=True)

    logger.info(
        f"パトロール完了: {patrol_report.overall_status} "
        f"(ok={len(patrol_report.ok_jobs)} err={len(patrol_report.error_jobs)})"
    )

    # ── Step 2: 修復（エラーがある場合のみ） ──────────────────────────────────
    repair_report = None
    if patrol_report.error_jobs or patrol_report.stale_jobs:
        logger.info(f"\n[Step 2] 修復実行中... ({len(patrol_report.error_jobs + patrol_report.stale_jobs)}件)")
        from agents.quality.repair.agent import RepairAgent
        import json

        # patrol_report を dict に変換して渡す
        patrol_dict = {
            "jobs": [
                {
                    "label": j.label,
                    "name": j.name,
                    "system": j.system,
                    "critical": j.critical,
                    "status": j.status,
                    "error_lines": j.error_lines,
                    "diagnosis": j.diagnosis,
                    "repair_needed": j.repair_needed,
                }
                for j in patrol_report.jobs
            ]
        }
        repair_report = RepairAgent().run(patrol_dict)
        logger.info(f"修復完了: {repair_report.repaired_count}/{len(repair_report.actions)}件")
    else:
        logger.info("\n[Step 2] エラーなし — 修復スキップ")

    # ── Step 3: 修復後の再チェック ────────────────────────────────────────────
    recheck_report = None
    if repair_report and repair_report.repaired_count > 0:
        logger.info("\n[Step 3] 修復後の再チェック...")
        import time
        time.sleep(10)  # 再起動を待つ
        recheck_report = patrol_run(quick=True, log_dashboard=False)
        logger.info(f"再チェック完了: {recheck_report.overall_status}")
    else:
        logger.info("\n[Step 3] 修復なし — 再チェックスキップ")

    # ── Step 4: メール送信 ────────────────────────────────────────────────────
    logger.info(f"\n[Step 4] メール送信: {REPORT_TO}")
    subject, body = _build_email_body(patrol_report, repair_report, recheck_report)
    mail_sent = _send_email(subject, body, send_mail=send_mail)

    if mail_sent:
        logger.info("メール送信完了")
    else:
        logger.warning("メール送信失敗")

    # ── 完了 ──────────────────────────────────────────────────────────────────
    result = {
        "patrol_id": patrol_report.patrol_id,
        "overall_status": patrol_report.overall_status,
        "ok": len(patrol_report.ok_jobs),
        "warning": len(patrol_report.warning_jobs),
        "error": len(patrol_report.error_jobs),
        "stale": len(patrol_report.stale_jobs),
        "repaired": repair_report.repaired_count if repair_report else 0,
        "manual_needed": len(repair_report.manual_needed) if repair_report else 0,
        "mail_sent": mail_sent,
    }

    logger.info("\n" + "=" * 55)
    logger.info(f"  日次パトロール完了: {patrol_report.overall_status}")
    logger.info(f"  修復: {result['repaired']}件 / 手動対応: {result['manual_needed']}件")
    logger.info("=" * 55)

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tokumori 日次パトロール")
    parser.add_argument("--quick", action="store_true", help="Claude診断をスキップ（高速）")
    parser.add_argument("--no-mail", action="store_true", help="メール送信なし（テスト用）")
    args = parser.parse_args()

    result = main(quick=args.quick, send_mail=not args.no_mail)

    status_icon = {"OK": "✅", "WARNING": "⚠️", "ERROR": "❌", "CRITICAL": "🚨"}.get(
        result["overall_status"], "❓"
    )
    print(f"\n{status_icon} {result['overall_status']}")
    print(f"  正常: {result['ok']} / 警告: {result['warning']} / エラー: {result['error']} / 停止疑い: {result['stale']}")
    if result["repaired"]:
        print(f"  自動修復: {result['repaired']}件")
    if result["manual_needed"]:
        print(f"  ⚠️  手動対応: {result['manual_needed']}件")
    print(f"  メール: {'送信済み' if result['mail_sent'] else '送信失敗'} → {REPORT_TO}")
