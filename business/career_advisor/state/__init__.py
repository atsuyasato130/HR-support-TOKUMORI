# state/ — Micro-Workers ステート管理パッケージ
#
# Workers はここのファイルを介してデータを受け渡す。
# 大量テキストの直接受け渡しを禁止し、ID と最小JSONのみを伝達する。
from .state_manager import StateManager

__all__ = ["StateManager"]
