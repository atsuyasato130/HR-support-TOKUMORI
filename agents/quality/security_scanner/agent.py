"""
Security Scanner Agent — ai-empire 品質管理層

シークレットスキャン・APIコスト監視・監査ログを担う品質管理エージェント。

機能:
  1. シークレットスキャン    — APIキー/パスワード/tokenのハードコード検出
  2. セキュリティ静的解析   — eval/exec/shell injection パターン検出
  3. 依存関係チェック       — requirements.txt の既知脆弱パッケージ検出
  4. スキャンレポート生成   — JSON + サマリー表示
  5. dashboard_logger 連携  — 結果を Update_Log に自動記録

使い方:
  python3 agents/quality/security_scanner/agent.py          # 全スキャン
  python3 agents/quality/security_scanner/agent.py --path agents/hr_support/
  python3 agents/quality/security_scanner/agent.py --severity CRITICAL

BU: Quality / Layer: Security
canonical_id: quality_security_scanner
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

# ─── パス設定 ─────────────────────────────────────────────────────────────────
AI_EMPIRE = Path(__file__).parent.parent.parent.parent  # ai-empire/
load_dotenv(AI_EMPIRE / "config" / ".env")

sys.path.insert(0, str(AI_EMPIRE))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("SecurityScanner")

SCAN_OUT = AI_EMPIRE / "logs" / "security_scans"

# ─── シークレットパターン ──────────────────────────────────────────────────────

@dataclass
class SecretPattern:
    name: str
    pattern: str
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    description: str


SECRET_PATTERNS: list[SecretPattern] = [
    SecretPattern("Anthropic API Key", r"sk-ant-[a-zA-Z0-9\-_]{20,}", "CRITICAL",
                  "Anthropic APIキーがハードコードされています"),
    SecretPattern("OpenAI API Key", r"sk-[a-zA-Z0-9]{32,}", "CRITICAL",
                  "OpenAI APIキーがハードコードされています"),
    SecretPattern("AWS Access Key", r"AKIA[0-9A-Z]{16}", "CRITICAL",
                  "AWS Access Key IDがハードコードされています"),
    SecretPattern("AWS Secret Key", r"[a-zA-Z0-9/+]{40}", "HIGH",
                  "AWS Secret Access Keyの可能性があります"),
    SecretPattern("GitHub Token", r"ghp_[a-zA-Z0-9]{36}", "HIGH",
                  "GitHub Personal Access Tokenがハードコードされています"),
    SecretPattern("GitHub OAuth", r"gho_[a-zA-Z0-9]{36}", "HIGH",
                  "GitHub OAuth Tokenがハードコードされています"),
    SecretPattern("Slack Token", r"xox[baprs]-[0-9A-Za-z\-]+", "HIGH",
                  "Slack Tokenがハードコードされています"),
    SecretPattern("Generic Password", r'(?i)password\s*=\s*["\'][^"\']{8,}["\']', "MEDIUM",
                  "パスワードがハードコードされています"),
    SecretPattern("Generic Secret", r'(?i)secret\s*=\s*["\'][^"\']{8,}["\']', "MEDIUM",
                  "シークレットがハードコードされています"),
    SecretPattern("Bearer Token", r"Bearer\s+[a-zA-Z0-9\-._~+/]+=*", "MEDIUM",
                  "Bearer Tokenがコード内に存在します"),
]

# ─── セキュリティリスクパターン ───────────────────────────────────────────────

@dataclass
class RiskPattern:
    name: str
    pattern: str
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    description: str
    fix: str


RISK_PATTERNS: list[RiskPattern] = [
    RiskPattern("eval() 使用", r"\beval\s*\(", "CRITICAL",
                "eval() は任意コード実行の危険があります",
                "eval() を使わない実装に変更"),
    RiskPattern("exec() 使用", r"\bexec\s*\(", "HIGH",
                "exec() は任意コード実行の危険があります",
                "exec() を使わない実装に変更"),
    RiskPattern("shell=True", r"shell\s*=\s*True", "HIGH",
                "shell=True はシェルインジェクションの危険があります",
                "shell=False で配列形式のコマンドを使用"),
    RiskPattern("os.system()", r"\bos\.system\s*\(", "HIGH",
                "os.system() はシェルインジェクションの危険があります",
                "subprocess.run() に置き換え"),
    RiskPattern("pickle.load()", r"\bpickle\.load\s*\(", "HIGH",
                "pickle は任意コード実行の危険があります",
                "json や安全なシリアライザを使用"),
    RiskPattern("SQL文字列結合", r'(?i)(?:select|insert|update|delete).+\+', "HIGH",
                "SQL文字列結合はSQLインジェクションの危険があります",
                "パラメータ化クエリを使用"),
    RiskPattern("print()でAPIキー", r'print\s*\(.*(?:api_key|token|secret|password)', "MEDIUM",
                "機密情報をprintで出力している可能性があります",
                "デバッグ出力を削除またはlogging.debug()に変更"),
    RiskPattern("urllib未検証", r"urllib\.request\.urlopen", "LOW",
                "SSL証明書の検証をスキップしていないか確認",
                "ssl.create_default_context() を使用"),
]

# ─── 既知の脆弱パッケージ（参考：OSV/PyPI advisory） ─────────────────────────

VULNERABLE_PACKAGES: dict[str, str] = {
    "pillow": "< 9.0.0 に複数のCVE",
    "requests": "< 2.20.0 に SSRF脆弱性",
    "pyyaml": "< 5.4 に任意コード実行",
    "cryptography": "古いバージョンに複数のCVE",
    "urllib3": "< 1.26.5 に脆弱性",
    "paramiko": "< 2.7.2 に脆弱性",
    "sqlalchemy": "< 1.3.0 にSQLインジェクション",
}


# ─── データクラス ─────────────────────────────────────────────────────────────

@dataclass
class Finding:
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    category: str
    file: str
    line: int
    description: str
    match: str = ""
    fix: str = ""


@dataclass
class ScanResult:
    scanned_files: int = 0
    findings: list[Finding] = field(default_factory=list)
    scan_time: str = ""

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "CRITICAL")

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "HIGH")

    @property
    def is_clean(self) -> bool:
        return self.critical_count == 0 and self.high_count == 0


# ─── スキャン実行 ─────────────────────────────────────────────────────────────

def scan_secrets(filepath: Path, source: str) -> list[Finding]:
    findings = []
    lines = source.splitlines()

    for pattern in SECRET_PATTERNS:
        for i, line in enumerate(lines, 1):
            # コメント行・空行は除外
            stripped = line.strip()
            if stripped.startswith("#") or not stripped:
                continue
            # os.environ.get() や env.get() での参照は除外
            if "os.environ" in line or "env.get" in line or "getenv" in line:
                continue

            m = re.search(pattern.pattern, line)
            if m:
                matched = m.group(0)
                # マスク（先頭8文字だけ表示）
                masked = matched[:8] + "***" if len(matched) > 8 else "***"
                findings.append(Finding(
                    severity=pattern.severity,
                    category="secret",
                    file=str(filepath),
                    line=i,
                    description=pattern.description,
                    match=masked,
                    fix="os.environ.get('KEY_NAME') に変更",
                ))
    return findings


def scan_risks(filepath: Path, source: str) -> list[Finding]:
    findings = []
    lines = source.splitlines()

    for pattern in RISK_PATTERNS:
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if re.search(pattern.pattern, line):
                findings.append(Finding(
                    severity=pattern.severity,
                    category="security_risk",
                    file=str(filepath),
                    line=i,
                    description=pattern.description,
                    match=stripped[:80],
                    fix=pattern.fix,
                ))
    return findings


def scan_file(filepath: Path) -> list[Finding]:
    try:
        source = filepath.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        logger.warning(f"読み込み失敗: {filepath}: {e}")
        return []

    findings = []
    findings.extend(scan_secrets(filepath, source))
    findings.extend(scan_risks(filepath, source))
    return findings


def scan_requirements(filepath: Path) -> list[Finding]:
    """requirements.txt の脆弱パッケージチェック"""
    findings = []
    try:
        lines = filepath.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []

    for i, line in enumerate(lines, 1):
        pkg = re.split(r"[>=<!]", line.strip())[0].lower().strip()
        if pkg in VULNERABLE_PACKAGES:
            findings.append(Finding(
                severity="MEDIUM",
                category="dependency",
                file=str(filepath),
                line=i,
                description=f"`{pkg}` は脆弱バージョンが存在します: {VULNERABLE_PACKAGES[pkg]}",
                match=line.strip(),
                fix="最新バージョンにアップデートしてください",
            ))
    return findings


def run_scan(
    target_path: Path,
    min_severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] = "LOW",
    max_files: int = 200,
) -> ScanResult:
    result = ScanResult(scan_time=datetime.now().isoformat())
    severity_order = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    min_idx = severity_order.index(min_severity)

    # Python ファイルをスキャン
    py_files = sorted(target_path.rglob("*.py"))[:max_files]
    for f in py_files:
        findings = scan_file(f)
        # 重要度フィルタ
        filtered = [
            fnd for fnd in findings
            if severity_order.index(fnd.severity) <= min_idx
        ]
        result.findings.extend(filtered)
        result.scanned_files += 1

    # requirements.txt
    for req in target_path.rglob("requirements*.txt"):
        result.findings.extend(scan_requirements(req))

    # 重要度順にソート
    result.findings.sort(
        key=lambda f: severity_order.index(f.severity)
    )
    return result


# ─── レポート保存・表示 ───────────────────────────────────────────────────────

def save_report(result: ScanResult) -> Path:
    SCAN_OUT.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = SCAN_OUT / f"security_scan_{ts}.json"

    data = {
        "scan_time": result.scan_time,
        "scanned_files": result.scanned_files,
        "summary": {
            "total": len(result.findings),
            "critical": result.critical_count,
            "high": result.high_count,
            "medium": sum(1 for f in result.findings if f.severity == "MEDIUM"),
            "low": sum(1 for f in result.findings if f.severity == "LOW"),
            "is_clean": result.is_clean,
        },
        "findings": [
            {
                "severity": f.severity,
                "category": f.category,
                "file": f.file,
                "line": f.line,
                "description": f.description,
                "match": f.match,
                "fix": f.fix,
            }
            for f in result.findings
        ],
    }
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def print_summary(result: ScanResult) -> None:
    severity_icons = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🔵"}
    print(f"\n{'='*60}")
    print(f"  セキュリティスキャン結果  — {result.scanned_files}ファイル")
    print(f"{'='*60}")

    if result.is_clean:
        print("  ✅ CRITICAL/HIGH の問題は検出されませんでした")
    else:
        print(f"  ⚠️  CRITICAL: {result.critical_count} / HIGH: {result.high_count}")

    # Finding 一覧（上位15件）
    for fnd in result.findings[:15]:
        icon = severity_icons.get(fnd.severity, "?")
        fname = Path(fnd.file).name
        print(f"  {icon} [{fnd.severity}] {fname}:{fnd.line} — {fnd.description}")
        if fnd.fix:
            print(f"        → {fnd.fix}")

    if len(result.findings) > 15:
        print(f"  ... 他 {len(result.findings) - 15}件（レポートを参照）")
    print(f"{'='*60}\n")


# ─── dashboard_logger 連携 ────────────────────────────────────────────────────

def _log_to_dashboard(result: ScanResult) -> None:
    try:
        from utils.dashboard_logger import log_update
        status_icon = "🆕 新規作成" if result.is_clean else "🔧 修正"
        log_update(
            icon=status_icon,
            summary=(
                f"セキュリティスキャン完了: {result.scanned_files}ファイル "
                f"/ CRITICAL:{result.critical_count} HIGH:{result.high_count}"
            ),
            targets="agents/ 全体",
            details=(
                f"①総検出数: {len(result.findings)}件 "
                f"②CRITICAL: {result.critical_count} "
                f"③HIGH: {result.high_count} "
                f"④クリーン: {'Yes' if result.is_clean else 'No'}"
            ),
        )
    except Exception as e:
        logger.debug(f"dashboard_logger 記録スキップ: {e}")


# ─── パブリックAPI ────────────────────────────────────────────────────────────

def run(
    path: str | None = None,
    severity: str = "LOW",
    log_dashboard: bool = True,
) -> dict:
    """
    パブリックAPI

    Args:
        path: スキャン対象パス（Noneなら ai-empire/agents/ 全体）
        severity: 最低重要度フィルタ (CRITICAL/HIGH/MEDIUM/LOW)
        log_dashboard: Update_Logに記録するか
    """
    target = Path(path) if path else AI_EMPIRE / "agents"
    logger.info(f"セキュリティスキャン開始: {target}")

    result = run_scan(target, min_severity=severity)  # type: ignore[arg-type]
    print_summary(result)

    report_path = save_report(result)
    logger.info(f"スキャンレポート保存: {report_path}")

    if log_dashboard:
        _log_to_dashboard(result)

    return {
        "scanned_files": result.scanned_files,
        "total_findings": len(result.findings),
        "critical": result.critical_count,
        "high": result.high_count,
        "is_clean": result.is_clean,
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="ai-empire セキュリティスキャン")
    parser.add_argument("--path", help="スキャン対象パス")
    parser.add_argument("--severity", default="LOW",
                        choices=["CRITICAL", "HIGH", "MEDIUM", "LOW"],
                        help="最低重要度フィルタ (default: LOW)")
    parser.add_argument("--no-log", action="store_true", help="Update_Log への記録をスキップ")
    args = parser.parse_args()

    result = run(path=args.path, severity=args.severity, log_dashboard=not args.no_log)
    status = "✅ クリーン" if result["is_clean"] else f"⚠️  要対応 (CRITICAL:{result['critical']})"
    print(f"完了: {result['scanned_files']}ファイルスキャン / {status}")
