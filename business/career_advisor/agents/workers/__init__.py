# workers/ — Micro-Workers 実装パッケージ
#
# 各ファイルは1つの役割（WATCHER/PARSER/PROCESSOR/EXECUTOR）のみを持つ。
# パイプライン: NotionWatcher → NotionPageParser → SFFieldMapper → SFBulkExecutor
