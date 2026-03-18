"""
business/lib — 100+ Agent Governance 共通ライブラリ

## 方針
各 Worker ファイルにロジックを直接書かず、ここのモジュールを import して使う。

## モジュール一覧
  api_clients     : Notion / Salesforce / Slack クライアントの薄いラッパー
  validators      : picklist バリデーション・フィールド型チェック
  state_io        : state/ ファイルの読み書き統一インターフェース
  registry_loader : registry.json のロード・検索・重複チェック

## import 例
  from business.lib.validators import validate_picklist
  from business.lib.state_io import read_state, write_state
  from business.lib.registry_loader import RegistryLoader
"""
