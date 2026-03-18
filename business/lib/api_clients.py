#!/usr/bin/env python3
"""
api_clients.py — 外部API クライアント薄いラッパー

接続・認証・基本エラーハンドリングのみを担う。
ビジネスロジックは各 Worker に書かず、このモジュールから接続オブジェクトを受け取って使う。

## 使い方
  from business.lib.api_clients import get_notion_client, get_sf_session, get_slack_client

  notion = get_notion_client()
  pages = notion.databases.query(database_id=DB_ID)

  sf = get_sf_session()
  result = sf.query("SELECT Id, Name FROM Account LIMIT 10")
"""

from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


# ── Notion ────────────────────────────────────────────────────────────

def get_notion_client():
    """
    Notion クライアントを返す。

    環境変数:
        NOTION_TOKEN: Notion Integration Token

    Returns:
        notion_client.Client インスタンス

    Raises:
        ImportError: notion-client パッケージが未インストール
        ValueError: NOTION_TOKEN 未設定
    """
    try:
        from notion_client import Client
    except ImportError as e:
        raise ImportError("notion-client パッケージをインストールしてください: pip install notion-client") from e

    token = os.environ.get("NOTION_TOKEN")
    if not token:
        raise ValueError("環境変数 NOTION_TOKEN が設定されていません。config/.env を確認してください。")

    logger.debug("Notion クライアント初期化")
    return Client(auth=token)


# ── Salesforce ────────────────────────────────────────────────────────

def get_sf_session():
    """
    Salesforce セッションを返す（simple-salesforce 使用）。

    環境変数:
        SF_USERNAME, SF_PASSWORD, SF_SECURITY_TOKEN, SF_DOMAIN (省略可、デフォルト "login")

    Returns:
        simple_salesforce.Salesforce インスタンス

    Raises:
        ImportError: simple-salesforce パッケージが未インストール
        ValueError: 必須環境変数が未設定
    """
    try:
        from simple_salesforce import Salesforce
    except ImportError as e:
        raise ImportError("simple-salesforce パッケージをインストールしてください: pip install simple-salesforce") from e

    username = os.environ.get("SF_USERNAME")
    password = os.environ.get("SF_PASSWORD")
    token    = os.environ.get("SF_SECURITY_TOKEN")

    if not all([username, password, token]):
        raise ValueError(
            "Salesforce 接続に必要な環境変数が不足しています。\n"
            "  必須: SF_USERNAME / SF_PASSWORD / SF_SECURITY_TOKEN"
        )

    domain = os.environ.get("SF_DOMAIN", "login")
    logger.debug("Salesforce セッション初期化 (domain=%s)", domain)
    return Salesforce(username=username, password=password, security_token=token, domain=domain)


# ── Slack ─────────────────────────────────────────────────────────────

def get_slack_client():
    """
    Slack WebClient を返す（slack-sdk 使用）。

    環境変数:
        SLACK_BOT_TOKEN: Bot Token（xoxb-...）

    Returns:
        slack_sdk.WebClient インスタンス

    Raises:
        ImportError: slack-sdk パッケージが未インストール
        ValueError: SLACK_BOT_TOKEN 未設定
    """
    try:
        from slack_sdk import WebClient
    except ImportError as e:
        raise ImportError("slack-sdk パッケージをインストールしてください: pip install slack-sdk") from e

    token = os.environ.get("SLACK_BOT_TOKEN")
    if not token:
        raise ValueError("環境変数 SLACK_BOT_TOKEN が設定されていません。")

    logger.debug("Slack WebClient 初期化")
    return WebClient(token=token)


# ── Anthropic (Claude) ────────────────────────────────────────────────

def get_anthropic_client(model: str = "claude-sonnet-4-6"):
    """
    Anthropic クライアントと推奨モデル名を返す。

    環境変数:
        ANTHROPIC_API_KEY: Anthropic API Key

    Returns:
        (anthropic.Anthropic, model_name) のタプル

    Raises:
        ImportError: anthropic パッケージが未インストール
        ValueError: ANTHROPIC_API_KEY 未設定
    """
    try:
        import anthropic
    except ImportError as e:
        raise ImportError("anthropic パッケージをインストールしてください: pip install anthropic") from e

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("環境変数 ANTHROPIC_API_KEY が設定されていません。")

    logger.debug("Anthropic クライアント初期化 (model=%s)", model)
    return anthropic.Anthropic(api_key=api_key), model
