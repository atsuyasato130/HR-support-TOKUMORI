#!/usr/bin/env python3
"""C12「Claude Code セットアップ」付録＝コピペ用コマンド集 Google Doc を生成（Mac/Windows）。
公式 code.claude.com/docs 準拠。見出し=Heading、コマンド=等幅(Courier New)＋淡グレー背景。"""
import warnings

warnings.filterwarnings("ignore")
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

TOKEN = "tokumori/agents/hr_support/config/token_sheets.json"
creds = Credentials.from_authorized_user_file(TOKEN)
docs = build("docs", "v1", credentials=creds)
dr = build("drive", "v3", credentials=creds)

# (テキスト, 種別)  種別: H1/H2/p/code
SEGS = [
    ("Claude Code セットアップ コマンド集（Mac / Windows）", "H1"),
    ("社内研修 C12 の付録。コマンドはコピーして使ってください。出典: code.claude.com/docs", "p"),

    ("0. 前提", "H2"),
    ("Node.js は不要（スタンドアロン）。Claude Pro / Max / Team でログイン（または APIキー）。", "p"),

    ("1. インストール（どれか1つ）", "H2"),
    ("macOS / Linux / WSL（推奨・自動更新つき）", "p"),
    ("curl -fsSL https://claude.ai/install.sh | bash", "code"),
    ("Windows（PowerShell）", "p"),
    ("irm https://claude.ai/install.ps1 | iex", "code"),
    ("Homebrew（Mac）", "p"),
    ("brew install --cask claude-code", "code"),
    ("winget（Windows）", "p"),
    ("winget install Anthropic.ClaudeCode", "code"),
    ("インストール確認", "p"),
    ("claude --version", "code"),

    ("2. ログイン", "H2"),
    ("プロジェクトに移動して起動 → ブラウザで認証（トークンは自動保存）", "p"),
    ("cd ~/your-project", "code"),
    ("claude", "code"),
    ("再ログイン・アカウント切替（セッション内で）", "p"),
    ("/login", "code"),

    ("3. VSCode 連携", "H2"),
    ("拡張をインストール（Marketplace で「Claude Code」、またはリンクを開く）", "p"),
    ("vscode://extension/anthropic.claude-code", "code"),
    ("プロジェクトを VSCode で開き、統合ターミナルで起動", "p"),
    ("code .", "code"),
    ("claude", "code"),
    ("便利キー: Cmd/Ctrl+Esc（エディタ↔Claude）、@ でファイル参照、Shift+Tab で権限モード切替"
     "（default → acceptEdits → plan）。VSCode 1.98 以上。", "p"),

    ("4. よく使うコマンド", "H2"),
    ("/help        ヘルプを表示", "code"),
    ("/init        CLAUDE.md を自動生成", "code"),
    ("/model       モデル切替（Opus 4.8 / Sonnet 4.6 / Haiku 4.5 / Fable 5）", "code"),
    ("/context     文脈の使用量を確認", "code"),
    ("/compact     会話を圧縮（焦点を指定できる）", "code"),
    ("/clear       履歴をリセット（別タスクの前に）", "code"),
    ("/plan        計画モード", "code"),
    ("/permissions 権限を UI で管理", "code"),
    ("/agents      サブエージェント", "code"),
    ("/mcp         外部ツール接続（MCP）", "code"),
    ("/login       ログイン     /exit   終了", "code"),

    ("5. 賢い設定（最初にやる）", "H2"),
    ("CLAUDE.md を作る（ビルド / テスト / 規約 / 落とし穴 を 200行以内で）。記入例は社内の "
     "CLAUDE.example.md を参照（cc-team-starter）。", "p"),
    ("/init", "code"),
    (".claude/settings.json でひととおり整える（許可 / 禁止 / 既定モード / モデル / フック）", "p"),
    ('{\n'
     '  "permissions": {\n'
     '    "allow": ["Bash(npm run build)", "Bash(npm test)", "Bash(pytest*)"],\n'
     '    "deny":  ["Read(**/.env)", "Read(**/*.pem)", "Read(**/id_rsa*)",\n'
     '              "Bash(rm -rf *)", "Bash(git push --force*)", "Bash(git reset --hard*)"]\n'
     '  },\n'
     '  "defaultMode": "plan",\n'
     '  "model": "opus",\n'
     '  "hooks": {\n'
     '    "PreToolUse":  [{ "matcher": "Bash", "hooks": [{ "type": "command",\n'
     '                      "command": "~/.claude/hooks/check_risky_bash.py" }] }],\n'
     '    "PostToolUse": [{ "matcher": "Edit|Write", "hooks": [{ "type": "command",\n'
     '                      "command": "~/.claude/hooks/auto_lint.py" }] }]\n'
     '  }\n'
     '}', "code"),
    ("ねらい：危険操作は deny で“実行させない”、起動から plan で“いきなり実行しない”、"
     "フックで“編集後に自動チェック”。フック実体は各自で用意（社内 clean 版を複製）。", "p"),

    ("6. MCP・サブエージェント（接続と分業）", "H2"),
    ("MCP＝社内ツールへの差込口。プロジェクト直下 .mcp.json に登録（鍵は環境変数 ${ } で渡し、直書きしない）", "p"),
    ('{\n'
     '  "mcpServers": {\n'
     '    "my-tools": {\n'
     '      "command": "python",\n'
     '      "args": ["-m", "my_tools_server"],\n'
     '      "env": { "API_TOKEN": "${MY_API_TOKEN}" }\n'
     '    }\n'
     '  }\n'
     '}', "code"),
    ("接続の確認・サブエージェントの一覧", "p"),
    ("/mcp         接続中の外部ツールを確認\n"
     "/agents      サブエージェント（分業する専門役）を一覧・追加", "code"),
    ("使い分け：定型の外部操作は MCP、独立した調査やレビューはサブエージェントに任せる。"
     "固有名・鍵は設定に直書きしない（環境変数へ）。", "p"),

    ("7. 仕組み（ハーネス・MCP・API連携）— 早わかり", "H2"),
    ("スライド C12「UNDER THE HOOD」の書面版。なぜ賢いモデル“だけ”では動かないのかを4層で。", "p"),
    ("● ハーネスとは：モデル（頭脳）を動かす“体”＝Claude Code", "p"),
    ("モデル＝LLM（考える・書く頭脳。/model で差し替え可）。ハーネス＝それを“動かす体”"
     "＝ループ＋ツール＋権限＋文脈管理＋フック。同じモデルでもハーネスで使い勝手が大きく変わる。"
     "計画モードや権限もハーネスが司る。", "p"),
    ("［設計図：ハーネスのループ］", "p"),
    ("  モデル（頭脳）  +  ハーネス（体）  =  Claude Code\n"
     "\n"
     "  (1) 指示を受ける（ゴール・文脈を読む）\n"
     "        |\n"
     "        v\n"
     "  (2) 計画・判断（何をするか決める）\n"
     "        |\n"
     "        v\n"
     "  (3) ツール実行（読む・書く・実行する）\n"
     "        |\n"
     "        v\n"
     "  (4) 結果を検証  --->  繰返し（(1)へ戻る）", "code"),
    ("● ツールと MCP：AIに“手足”と“社内への差込口”を与える", "p"),
    ("ツール＝AIの手足（ファイル読み書き・コマンド実行・検索）。"
     "MCP（Model Context Protocol）＝社内ツールを“差し込む”標準コネクタ＝AI版USB-C。"
     "Gmail・Slack・Salesforce・Notion・DB を公開すれば、AIが直接操作できる。", "p"),
    ("● API連携とは：外部サービスと“繋いで流す”仕組み", "p"),
    ("API＝サービスごとの“共通の窓口・約束事”。連携＝それを繋いでデータを流すこと。"
     "MCP は「AI向けの API 連携」を標準化したもの。", "p"),
    ("［設計図：API連携の流れ］", "p"),
    ("  あなた  -->  Claude（ハーネス）  -->  API / MCP  -->  外部サービス  -->  結果\n"
     "  指示          計画して呼び出す         共通の窓口        Sheets・SF が動く", "code"),
    ("● まとめ：4つの層で動く（賢いモデル“だけ”では動かない）", "p"),
    ("［設計図：4つの層］", "p"),
    ("  [1] 頭脳  = モデル（考える・書く。/model で差し替え可）\n"
     "  [2] 器    = ハーネス（ループ・権限・文脈・フック）\n"
     "  [3] 手足  = ツール（読む・書く・実行する）\n"
     "  [4] 接続  = MCP / API（社内ツール・外部サービスへ）\n"
     "\n"
     "  頭脳 + 器 + 手足 + 接続  =  はじめて実務になる", "code"),

    ("8. トラブルシュート", "H2"),
    ("・claude が見つからない → ターミナル（Windows は新しい PowerShell）を開き直す", "p"),
    ("・うまく動かない → claude --version で確認し、再インストール", "p"),
    ("・Windows でうまくいかない → WSL 内で install.sh を実行する手もある", "p"),
    ("・勝手な実行が不安 → Shift+Tab で plan / default、危険操作は deny に登録", "p"),
    ("・秘密情報は絶対にコミットしない（環境変数・.env・.gitignore を徹底）", "p"),
]


# 既存Docを“その場で更新”するとURLが固定され、スライドから安全に参照できる。
# DOC_ID を空にすると従来どおり新規作成（フォールバック）。
DOC_ID = "1TgOoWV24tj_EXAx9Cn_BvbKLiDiPkiI2UfysD6udhNE"


def main():
    if DOC_ID:
        did = DOC_ID
        # 既存本文を全削除してから入れ直す（末尾の改行は削除できないので endIndex-1 まで）。
        doc = docs.documents().get(documentId=did).execute()
        end = doc["body"]["content"][-1]["endIndex"]
        reqs = []
        if end > 2:
            reqs.append({"deleteContentRange": {"range": {"startIndex": 1, "endIndex": end - 1}}})
    else:
        doc = docs.documents().create(body={"title": "Claude Code セットアップ コマンド集（Mac/Windows）"}).execute()
        did = doc["documentId"]
        reqs = []

    # 全文を組み立て（各セグメントは改行で区切る）。indexは1始まり（先頭段落の前に挿入）。
    full = "".join(t + "\n" for t, _ in SEGS)
    reqs.append({"insertText": {"location": {"index": 1}, "text": full}})

    cur = 0
    for text, kind in SEGS:
        start = 1 + cur
        end = 1 + cur + len(text)
        if kind in ("H1", "H2"):
            reqs.append({"updateParagraphStyle": {
                "range": {"startIndex": start, "endIndex": end},
                "paragraphStyle": {"namedStyleType": "HEADING_1" if kind == "H1" else "HEADING_2"},
                "fields": "namedStyleType"}})
        elif kind == "code":
            reqs.append({"updateTextStyle": {
                "range": {"startIndex": start, "endIndex": end},
                "textStyle": {
                    "weightedFontFamily": {"fontFamily": "Courier New", "weight": 400},
                    "backgroundColor": {"color": {"rgbColor": {"red": 0.96, "green": 0.96, "blue": 0.965}}}},
                "fields": "weightedFontFamily,backgroundColor"}})
        cur += len(text) + 1

    docs.documents().batchUpdate(documentId=did, body={"requests": reqs}).execute()

    for b in [{"type": "user", "role": "writer", "emailAddress": "0130atsuya@gmail.com"},
              {"type": "user", "role": "writer", "emailAddress": "atsuya_sato@tokumori.co.jp"},
              {"type": "domain", "role": "reader", "domain": "tokumori.co.jp"}]:
        try:
            dr.permissions().create(fileId=did, body=b, sendNotificationEmail=False, fields="id").execute()
        except Exception as e:
            print("share note:", str(e)[:60])

    print("DOC:", "https://docs.google.com/document/d/%s/edit" % did)


if __name__ == "__main__":
    main()
