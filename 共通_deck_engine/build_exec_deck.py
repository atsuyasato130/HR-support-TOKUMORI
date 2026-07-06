#!/usr/bin/env python3
"""
とくもり就活 ― データカンパニー構想 / 経営会議向けピッチデッキ（Google Slides）
token_sheets.json(presentationsスコープ)で Slides API を直接利用して新規作成。
プレミアム志向：紙地＋赤1色＋明朝見出し＋大きな数字＋図解。脱チープ。
正本＝~/Claude AI/とくもり就活_マスター仕様書_v1.md
再実行時は .exec_deck_id の同一デッキを更新（重複作成しない）。
"""
import warnings, os, json, time, socket, math
warnings.filterwarnings("ignore")
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

BASE = "/Users/atsuyasato/Claude AI"
TOK = "/Users/atsuyasato/Claude AI/tokumori/agents/hr_support/config/token_sheets.json"
IDF = os.path.join(BASE, ".exec_deck_id")
TITLE = "とくもり就活｜データカンパニー構想 経営会議資料"

# ---- 寸法（16:9） ----
IN = 914400
PW, PH = 9144000, 5143500
MX = int(0.62 * IN)
CW = PW - 2 * MX

# ---- ブランド（赤1色＋黒＋温かい紙） ----
RED = "AF322C"; REDD = "8F231F"; EMBER = "E2574A"
INK = "241C17"; SUB = "6F655C"; WHITE = "FFFFFF"
PAPER = "FAF7F1"; PAPER2 = "F3ECE1"; LINE = "ECE3D6"; NIGHT = "2A201A"
HEAD = "Shippori Mincho"           # 明朝ディスプレイ（上質）
BODY = "Zen Kaku Gothic New"       # 本文
MONO = "DM Mono"                   # 数値・ラベル


def rf(h): return {"red": int(h[0:2], 16) / 255, "green": int(h[2:4], 16) / 255, "blue": int(h[4:6], 16) / 255}


def safe_bu(slides, pid, reqs):
    for i in range(0, len(reqs), 60):
        chunk = reqs[i:i + 60]
        for attempt in range(8):
            try:
                slides.presentations().batchUpdate(presentationId=pid, body={"requests": chunk}).execute(); break
            except HttpError as e:
                if ("429" in str(e)) or ("RATE_LIMIT" in str(e)):
                    print("  ...rate limit, wait 45s"); time.sleep(45); continue
                raise
            except (socket.timeout, OSError, ConnectionError, TimeoutError) as e:
                if attempt == 7: raise
                print("  ...network error, retry 10s"); time.sleep(10); continue
        time.sleep(1.2)


class Deck:
    def __init__(self, nonce="x"):
        self.reqs = []; self.n = 0; self.page = 0; self.nonce = nonce; self.total = 16

    def _id(self, p): self.n += 1; return "%s%s%04d" % (self.nonce, p, self.n)

    def slide(self, bg=PAPER):
        self.page += 1; sid = "%ssld%03d" % (self.nonce, self.page)
        self.reqs.append({"createSlide": {"objectId": sid, "slideLayoutReference": {"predefinedLayout": "BLANK"}, "insertionIndex": self.page - 1}})
        self.reqs.append({"updatePageProperties": {"objectId": sid, "pageProperties": {"pageBackgroundFill": {"solidFill": {"color": {"rgbColor": rf(bg)}}}}, "fields": "pageBackgroundFill.solidFill.color"}})
        return sid

    def rect(self, sid, x, y, w, h, fill=None, line=None, lw=1.0, round=False, shape="RECTANGLE"):
        oid = self._id("r")
        self.reqs.append({"createShape": {"objectId": oid, "shapeType": ("ROUND_RECTANGLE" if round else shape),
            "elementProperties": {"pageObjectId": sid, "size": {"width": {"magnitude": w, "unit": "EMU"}, "height": {"magnitude": h, "unit": "EMU"}},
            "transform": {"scaleX": 1, "scaleY": 1, "translateX": x, "translateY": y, "unit": "EMU"}}}})
        sp = {}; f = []
        if fill is not None: sp["shapeBackgroundFill"] = {"solidFill": {"color": {"rgbColor": rf(fill)}}}; f.append("shapeBackgroundFill.solidFill.color")
        else: sp["shapeBackgroundFill"] = {"propertyState": "NOT_RENDERED"}; f.append("shapeBackgroundFill.propertyState")
        if line is not None: sp["outline"] = {"outlineFill": {"solidFill": {"color": {"rgbColor": rf(line)}}}, "weight": {"magnitude": lw, "unit": "PT"}, "dashStyle": "SOLID"}; f.append("outline")
        else: sp["outline"] = {"propertyState": "NOT_RENDERED"}; f.append("outline.propertyState")
        self.reqs.append({"updateShapeProperties": {"objectId": oid, "shapeProperties": sp, "fields": ",".join(f)}})
        return oid

    def text(self, sid, x, y, w, h, runs, align="START", valign="TOP", spacing=116, sb=3):
        oid = self._id("t")
        self.reqs.append({"createShape": {"objectId": oid, "shapeType": "TEXT_BOX",
            "elementProperties": {"pageObjectId": sid, "size": {"width": {"magnitude": w, "unit": "EMU"}, "height": {"magnitude": h, "unit": "EMU"}},
            "transform": {"scaleX": 1, "scaleY": 1, "translateX": x, "translateY": y, "unit": "EMU"}}}})
        full = "".join(t for t, _ in runs)
        self.reqs.append({"insertText": {"objectId": oid, "insertionIndex": 0, "text": full}})
        idx = 0
        for t, st in runs:
            if not t: continue
            stl = {"fontFamily": st.get("font", BODY), "fontSize": {"magnitude": st.get("size", 12), "unit": "PT"},
                   "foregroundColor": {"opaqueColor": {"rgbColor": rf(st.get("color", INK))}}, "bold": st.get("bold", False)}
            self.reqs.append({"updateTextStyle": {"objectId": oid, "textRange": {"type": "FIXED_RANGE", "startIndex": idx, "endIndex": idx + len(t)},
                "style": stl, "fields": "fontFamily,fontSize,foregroundColor,bold"}})
            idx += len(t)
        self.reqs.append({"updateParagraphStyle": {"objectId": oid, "textRange": {"type": "ALL"},
            "style": {"alignment": align, "lineSpacing": spacing, "spaceBelow": {"magnitude": sb, "unit": "PT"}}, "fields": "alignment,lineSpacing,spaceBelow"}})
        self.reqs.append({"updateShapeProperties": {"objectId": oid, "shapeProperties": {"contentAlignment": valign}, "fields": "contentAlignment"}})
        return oid

    # ---- 共通パーツ ----
    def kicker(self, sid, t):
        self.text(sid, MX, int(0.46 * IN), CW, int(0.26 * IN), [(t, {"size": 10, "color": RED, "bold": True, "font": MONO})], valign="MIDDLE")

    def title(self, sid, t, size=29):
        self.text(sid, MX, int(0.78 * IN), CW, int(0.7 * IN), [(t, {"size": size, "color": INK, "bold": True, "font": HEAD})], valign="MIDDLE")
        self.rect(sid, MX, int(1.52 * IN), int(0.62 * IN), int(0.05 * IN), fill=RED)

    def foot(self, sid, dark=False):
        c = "9B8F84" if dark else SUB; rc = EMBER if dark else RED
        self.rect(sid, MX, PH - int(0.46 * IN), CW, 9525, fill=(("3A2E26") if dark else LINE))
        self.text(sid, MX, PH - int(0.4 * IN), CW - int(1 * IN), int(0.3 * IN),
                  [("とくもり就活", {"size": 8.5, "color": rc, "bold": True, "font": MONO}), ("  ｜ データカンパニー構想 ・ 経営会議資料", {"size": 8, "color": c, "font": MONO})], valign="MIDDLE")
        self.text(sid, PW - MX - int(1.2 * IN), PH - int(0.4 * IN), int(1.2 * IN), int(0.3 * IN),
                  [("%02d / %d" % (self.page, self.total), {"size": 8, "color": c, "font": MONO})], align="END", valign="MIDDLE")

    def chip(self, sid, x, y, w, h, label, fill=PAPER2, fg=INK, line=None, size=11, bold=True, font=None):
        self.rect(sid, x, y, w, h, fill=fill, line=line, lw=1, round=True)
        self.text(sid, x + int(0.1 * IN), y, w - int(0.2 * IN), h, [(label, {"size": size, "color": fg, "bold": bold, "font": font or BODY})], align="CENTER", valign="MIDDLE")

    def bullets(self, sid, y, items, size=14, gap=0.62, lead=RED):
        for it in items:
            head, body = it if isinstance(it, tuple) else (None, it)
            self.rect(sid, MX, y + int(0.08 * IN), int(0.12 * IN), int(0.12 * IN), fill=lead)
            runs = []
            if head: runs.append((head + "　", {"size": size, "color": INK, "bold": True, "font": BODY}))
            runs.append((body, {"size": size, "color": (INK if head else SUB if False else INK), "font": BODY}))
            self.text(sid, MX + int(0.34 * IN), y, CW - int(0.34 * IN), int(gap * IN), runs, valign="TOP")
            y += int(gap * IN)
        return y


# ============================ スライド ============================
def build_deck(dk):
    # 1. 表紙
    sid = dk.slide(bg=PAPER)
    dk.rect(sid, 0, 0, int(0.18 * IN), PH, fill=RED)
    dk.text(sid, MX, int(0.7 * IN), CW, int(0.3 * IN), [("とくもり就活  ｜  TOKUMORI", {"size": 11, "color": RED, "bold": True, "font": MONO})])
    dk.text(sid, MX, int(1.7 * IN), CW, int(1.7 * IN),
            [("読むメディアから、\n受かるメディアへ。", {"size": 46, "color": INK, "bold": True, "font": HEAD})], valign="MIDDLE", spacing=108)
    dk.rect(sid, MX, int(3.55 * IN), int(1.3 * IN), int(0.06 * IN), fill=RED)
    dk.text(sid, MX, int(3.75 * IN), CW, int(0.5 * IN), [("データカンパニー構想 ― 就活の全データを束ね、企業を強くする。", {"size": 16, "color": SUB, "font": BODY})])
    dk.text(sid, MX, PH - int(0.7 * IN), CW, int(0.3 * IN),
            [("経営会議資料  ・  2026.06  ・  株式会社TOKUMORI", {"size": 10, "color": SUB, "font": MONO})], valign="MIDDLE")

    # 2. エグゼクティブサマリー
    sid = dk.slide(); dk.kicker(sid, "EXECUTIVE SUMMARY"); dk.title(sid, "結論：就活の基盤（OS）を、私たちが持つ。")
    y = dk.bullets(sid, int(1.78 * IN), [
        ("何を", "学生の就活データを1か所に束ねる無料ツール。使われるほど一次データが溜まる収集装置。"),
        ("なぜ今", "AIが情報を無料化＝情報メディアは死ぬ。残るのは「成果に責任を持つ生きたネットワーク」。"),
        ("唯一の強み", "本業で人事(企業側)×新卒コーチング(学生側)の両方を保有。二面ネットワークの鶏卵問題を最初から解ける。"),
        ("到達点", "内定→OB→データ→マネタイズの複利。学生信用値を就活の外(賃貸/金融)へ広げ、LTVが続く。"),
    ], size=13.5, gap=0.66)
    dk.rect(sid, MX, int(4.5 * IN), CW, int(0.62 * IN), fill=PAPER2, round=True)
    dk.text(sid, MX + int(0.25 * IN), int(4.5 * IN), CW - int(0.5 * IN), int(0.62 * IN),
            [("最優先KPI＝一次データ収集の最大化　　│　　2027卒 内定率 ", {"size": 11.5, "color": INK, "bold": True, "font": BODY}),
             ("67.0%", {"size": 14, "color": RED, "bold": True, "font": MONO}),
             ("（就職みらい研究所）　│　現状：触れるMVPが稼働中", {"size": 11.5, "color": INK, "font": BODY})], valign="MIDDLE")

    # 3. 課題
    sid = dk.slide(); dk.kicker(sid, "THE PROBLEM"); dk.title(sid, "就活は、いまだに「ブラックボックス」。")
    gap = int(0.3 * IN); cw = (CW - gap) // 2; yy = int(1.75 * IN); hh = int(2.25 * IN)
    for x, head, items in [(MX, "学生", ["みんながどれだけ動いているか見えない", "内定をいつ・何社が持っているか不明", "→ 不安と出遅れ。情報格差が結果を分ける"]),
                            (MX + cw + gap, "企業", ["母集団の「質」が事前に読めない", "惜しくも落ちた優秀層を拾えない", "→ 採用のミスマッチとコスト増"])]:
        dk.rect(sid, x, yy, cw, hh, fill=WHITE, line=LINE, lw=1.2, round=True)
        dk.rect(sid, x, yy, cw, int(0.5 * IN), fill=NIGHT, round=True)
        dk.text(sid, x + int(0.25 * IN), yy, cw - int(0.4 * IN), int(0.5 * IN), [(head, {"size": 13, "color": WHITE, "bold": True, "font": HEAD})], valign="MIDDLE")
        ry = yy + int(0.68 * IN)
        for it in items:
            dk.rect(sid, x + int(0.25 * IN), ry + int(0.07 * IN), int(0.1 * IN), int(0.1 * IN), fill=RED)
            dk.text(sid, x + int(0.45 * IN), ry, cw - int(0.7 * IN), int(0.5 * IN), [(it, {"size": 11.5, "color": INK, "font": BODY})])
            ry += int(0.5 * IN)
    dk.rect(sid, MX, int(4.3 * IN), CW, int(0.6 * IN), fill="F6ECEA", round=True); dk.rect(sid, MX, int(4.3 * IN), int(0.08 * IN), int(0.6 * IN), fill=RED)
    dk.text(sid, MX + int(0.3 * IN), int(4.3 * IN), CW - int(0.6 * IN), int(0.6 * IN),
            [("さらにAIが「情報」を無料化 → ノウハウ提供メディアは価値を失う。", {"size": 13, "color": INK, "bold": True, "font": BODY})], valign="MIDDLE")
    dk.foot(sid)

    # 4. ビジョン
    sid = dk.slide(bg=NIGHT)
    dk.text(sid, MX, int(0.5 * IN), CW, int(0.26 * IN), [("OUR THESIS", {"size": 10, "color": EMBER, "bold": True, "font": MONO})])
    dk.text(sid, MX, int(1.2 * IN), CW, int(1.9 * IN),
            [("情報ではなく、\n", {"size": 40, "color": WHITE, "bold": True, "font": HEAD}),
             ("「判断と成果」を渡す。", {"size": 40, "color": EMBER, "bold": True, "font": HEAD})], spacing=110)
    dk.rect(sid, MX, int(3.35 * IN), int(1.1 * IN), int(0.05 * IN), fill=RED)
    dk.text(sid, MX, int(3.6 * IN), CW, int(0.5 * IN),
            [("「読むメディア」から「受かるメディア」へ。 ＝ 成果に責任を持つ、生きたネットワーク。", {"size": 15, "color": "E7DED5", "font": BODY})])
    dk.text(sid, MX, int(4.35 * IN), CW, int(0.4 * IN),
            [("餌＝コンテンツ　／　頭脳＝データ　／　体＝ネットワーク　／　証明＝成果", {"size": 11, "color": "9B8F84", "font": MONO})])
    dk.foot(sid, dark=True)

    # 5. 唯一の強み（堀）
    sid = dk.slide(); dk.kicker(sid, "UNFAIR ADVANTAGE"); dk.title(sid, "新規参入が、絶対に作れない強み。")
    bw = int(2.75 * IN); bh = int(1.5 * IN); by = int(1.95 * IN)
    dk.rect(sid, MX, by, bw, bh, fill=PAPER2, line=LINE, lw=1, round=True)
    dk.text(sid, MX, by + int(0.2 * IN), bw, int(0.4 * IN), [("企業側", {"size": 12, "color": RED, "bold": True, "font": MONO})], align="CENTER")
    dk.text(sid, MX + int(0.2 * IN), by + int(0.62 * IN), bw - int(0.4 * IN), int(0.8 * IN), [("本業の人事ネットワーク\n（採用支援で既に保有）", {"size": 13, "color": INK, "bold": True, "font": BODY})], align="CENTER", valign="MIDDLE")
    rx = PW - MX - bw
    dk.rect(sid, rx, by, bw, bh, fill=PAPER2, line=LINE, lw=1, round=True)
    dk.text(sid, rx, by + int(0.2 * IN), bw, int(0.4 * IN), [("学生側", {"size": 12, "color": RED, "bold": True, "font": MONO})], align="CENTER")
    dk.text(sid, rx + int(0.2 * IN), by + int(0.62 * IN), bw - int(0.4 * IN), int(0.8 * IN), [("新卒コーチング\n（学生との接点を既に保有）", {"size": 13, "color": INK, "bold": True, "font": BODY})], align="CENTER", valign="MIDDLE")
    dk.text(sid, MX + bw, by, rx - (MX + bw), bh, [("＋", {"size": 30, "color": RED, "bold": True, "font": HEAD})], align="CENTER", valign="MIDDLE")
    dk.rect(sid, MX, int(3.75 * IN), CW, int(0.85 * IN), fill=RED, round=True)
    dk.text(sid, MX + int(0.3 * IN), int(3.75 * IN), CW - int(0.6 * IN), int(0.85 * IN),
            [("二面ネットワークの最難関＝「鶏卵問題」を、最初から解ける唯一の立場。", {"size": 15, "color": WHITE, "bold": True, "font": HEAD})], align="CENTER", valign="MIDDLE")
    dk.foot(sid)

    # 6. フライホイール
    sid = dk.slide(); dk.kicker(sid, "THE FLYWHEEL"); dk.title(sid, "すべてがつながる、データ・フライホイール。")
    steps = [("学生が毎日使う", "就活管理ツール"), ("トクモリ偏差値", "全データを束ねる"), ("スカウト/企業支援", "偏差値ゲート"), ("内定 → OB/OG", "成果が残る"), ("データ蓄積", "母集団の質"), ("マネタイズ", "企業を強くする")]
    n = len(steps); g = int(0.16 * IN); bw = (CW - g * (n - 1)) // n; y = int(2.0 * IN); h = int(1.55 * IN); x = MX
    for i, (lbl, desc) in enumerate(steps):
        dk.rect(sid, x, y, bw, h, fill=(RED if i in (1,) else WHITE), line=(None if i in (1,) else LINE), lw=1.2, round=True)
        fg = WHITE if i in (1,) else INK
        dk.rect(sid, x + int(0.18 * IN), y + int(0.2 * IN), int(0.34 * IN), int(0.34 * IN), fill=(WHITE if i in (1,) else RED), round=True)
        dk.text(sid, x + int(0.18 * IN), y + int(0.2 * IN), int(0.34 * IN), int(0.34 * IN), [("%d" % (i + 1), {"size": 12, "color": (RED if i in (1,) else WHITE), "bold": True, "font": MONO})], align="CENTER", valign="MIDDLE")
        dk.text(sid, x + int(0.18 * IN), y + int(0.66 * IN), bw - int(0.36 * IN), int(0.5 * IN), [(lbl, {"size": 11.5, "color": fg, "bold": True, "font": HEAD})])
        dk.text(sid, x + int(0.18 * IN), y + int(1.06 * IN), bw - int(0.36 * IN), int(0.4 * IN), [(desc, {"size": 9.5, "color": (WHITE if i in (1,) else SUB), "font": BODY})])
        if i < n - 1:
            dk.text(sid, x + bw - int(0.02 * IN), y, g + int(0.08 * IN), h, [("›", {"size": 18, "color": RED, "bold": True, "font": HEAD})], align="CENTER", valign="MIDDLE")
        x += bw + g
    dk.rect(sid, MX, int(3.95 * IN), CW, int(0.6 * IN), fill=PAPER2, round=True)
    dk.text(sid, MX + int(0.25 * IN), int(3.95 * IN), CW - int(0.5 * IN), int(0.6 * IN),
            [("回るほど学生が集まり、データが濃くなり、企業価値が上がる ― 複利で効く堀。", {"size": 12.5, "color": INK, "bold": True, "font": BODY})], align="CENTER", valign="MIDDLE")
    dk.foot(sid)

    # 7. トクモリ偏差値
    sid = dk.slide(); dk.kicker(sid, "THE CORE ASSET"); dk.title(sid, "中核：トクモリ偏差値 ― 全データの集約点。")
    axes = ["学歴", "実行力", "対人力", "人格", "思考力", "就活習熟度", "ガクチカ"]
    ax_y = int(1.85 * IN); cwid = int(4.6 * IN)
    dk.text(sid, MX, ax_y, cwid, int(0.3 * IN), [("7軸を自動スコアリング", {"size": 12, "color": RED, "bold": True, "font": MONO})])
    cy = ax_y + int(0.5 * IN); cwd = int(1.45 * IN); chh = int(0.42 * IN); gx = int(0.14 * IN)
    px = MX; pr = 0
    for i, a in enumerate(axes):
        col = i % 3
        x = MX + col * (cwd + gx); yy = cy + (i // 3) * (chh + int(0.14 * IN))
        dk.chip(sid, x, yy, cwd, chh, a, fill=WHITE, fg=INK, line=LINE, size=11)
    # 右：偏差値ブロック
    bx = PW - MX - int(2.9 * IN)
    dk.rect(sid, bx, int(1.8 * IN), int(2.9 * IN), int(2.5 * IN), fill=NIGHT, round=True)
    dk.text(sid, bx, int(2.0 * IN), int(2.9 * IN), int(0.3 * IN), [("会員内偏差値（サンプル）", {"size": 10, "color": "9B8F84", "font": MONO})], align="CENTER")
    dk.text(sid, bx, int(2.35 * IN), int(2.9 * IN), int(1.1 * IN), [("62.4", {"size": 64, "color": WHITE, "bold": True, "font": MONO})], align="CENTER", valign="MIDDLE")
    dk.text(sid, bx, int(3.5 * IN), int(2.9 * IN), int(0.6 * IN), [("月1回のAI面接で更新\n「伸び」を可視化", {"size": 10.5, "color": "E7DED5", "font": BODY})], align="CENTER")
    dk.text(sid, MX, int(4.5 * IN), int(4.6 * IN), int(0.5 * IN),
            [("→ 企業はこの偏差値帯でスカウト/特別オファー。模試型の合格可能性判定にも使う。", {"size": 11, "color": INK, "font": BODY})])
    dk.foot(sid)

    # 8. プロダクト①学生
    sid = dk.slide(); dk.kicker(sid, "PRODUCT ・ STUDENT"); dk.title(sid, "学生：毎日使う「就活の司令塔」。")
    tiles = [("選考ノート", "進捗・面接で聞かれた質問を記録"), ("スケジュール", "選考予定と締切を一元管理"), ("ES・OpenES", "保存＆ワンクリックでPDF生成"),
             ("AI添削", "自己PR/ESを即チェック"), ("パーソナル分析", "業界/企業/社風×自分の相性"), ("偏差値・模試", "現在地と合格可能性が分かる")]
    g = int(0.22 * IN); cwd = (CW - g * 2) // 3; chh = int(1.2 * IN); y0 = int(1.78 * IN)
    for i, (t, d) in enumerate(tiles):
        x = MX + (i % 3) * (cwd + g); yy = y0 + (i // 3) * (chh + int(0.2 * IN))
        dk.rect(sid, x, yy, cwd, chh, fill=WHITE, line=LINE, lw=1.2, round=True)
        dk.rect(sid, x, yy, int(0.07 * IN), chh, fill=RED)
        dk.text(sid, x + int(0.26 * IN), yy + int(0.16 * IN), cwd - int(0.4 * IN), int(0.4 * IN), [(t, {"size": 13.5, "color": INK, "bold": True, "font": HEAD})])
        dk.text(sid, x + int(0.26 * IN), yy + int(0.62 * IN), cwd - int(0.4 * IN), int(0.5 * IN), [(d, {"size": 10.5, "color": SUB, "font": BODY})])
    dk.text(sid, MX, int(4.65 * IN), CW, int(0.35 * IN),
            [("使うほどデータが濃くなる ＝ そのまま「データ収集エンジン」。", {"size": 12.5, "color": RED, "bold": True, "font": BODY})], align="CENTER")
    dk.foot(sid)

    # 9. プロダクト②企業
    sid = dk.slide(); dk.kicker(sid, "PRODUCT ・ COMPANY"); dk.title(sid, "企業：0円で始め、質の高い母集団に出会う。")
    steps = [("0円掲載", "まず母集団を集める\n企業ページは自社で編集"), ("偏差値ゲートのスカウト", "閾値以上へスカウト/特別オファー\nABABA型で「惜しい優秀層」も"), ("掲載企業ダッシュボード", "採用学生の偏差値推移＝\n母集団の「質」が見える")]
    n = len(steps); g = int(0.24 * IN); bw = (CW - g * (n - 1)) // n; y = int(1.95 * IN); h = int(2.0 * IN); x = MX
    for i, (lbl, desc) in enumerate(steps):
        dk.rect(sid, x, y, bw, h, fill=PAPER2, line=LINE, lw=1, round=True)
        dk.rect(sid, x + int(0.22 * IN), y + int(0.24 * IN), int(0.5 * IN), int(0.5 * IN), fill=RED, round=True)
        dk.text(sid, x + int(0.22 * IN), y + int(0.24 * IN), int(0.5 * IN), int(0.5 * IN), [("%d" % (i + 1), {"size": 18, "color": WHITE, "bold": True, "font": HEAD})], align="CENTER", valign="MIDDLE")
        dk.text(sid, x + int(0.22 * IN), y + int(0.9 * IN), bw - int(0.44 * IN), int(0.5 * IN), [(lbl, {"size": 13, "color": INK, "bold": True, "font": HEAD})])
        dk.text(sid, x + int(0.22 * IN), y + int(1.32 * IN), bw - int(0.44 * IN), int(0.6 * IN), [(desc, {"size": 10, "color": SUB, "font": BODY})])
        if i < n - 1:
            dk.text(sid, x + bw - int(0.02 * IN), y, g + int(0.1 * IN), h, [("›", {"size": 22, "color": RED, "bold": True, "font": HEAD})], align="CENTER", valign="MIDDLE")
        x += bw + g
    dk.text(sid, MX, int(4.5 * IN), CW, int(0.4 * IN), [("掲載は無料。価値（スカウト/オファー/データ）が出てから課金する設計。", {"size": 12, "color": INK, "font": BODY})], align="CENTER")
    dk.foot(sid)

    # 10. データが資産
    sid = dk.slide(); dk.kicker(sid, "DATA IS THE MOAT"); dk.title(sid, "データが、最大の資産。")
    dk.bullets(sid, int(1.8 * IN), [
        ("最優先KPI", "一次データ収集の最大化。本人確認・実名で「質」を、継続利用で「密度」を最大化する。"),
        ("ブラックボックスを開ける", "集めた実数で「同卒年の動き出し率/内定率/募集締切済み企業%」を可視化＝健全な焦り→行動。"),
        ("段階開放", "会員データの公開は会員1万人超で解放（それ未満は公式統計のみ・捏造はしない）。"),
    ], size=13.5, gap=0.72)
    dk.rect(sid, MX, int(4.35 * IN), CW, int(0.62 * IN), fill=NIGHT, round=True)
    dk.text(sid, MX + int(0.25 * IN), int(4.35 * IN), CW - int(0.5 * IN), int(0.62 * IN),
            [("溜まるほど価値が増す ― メディアの質も、マネタイズ手段も、データが増やす。", {"size": 12.5, "color": WHITE, "bold": True, "font": BODY})], align="CENTER", valign="MIDDLE")
    dk.foot(sid)

    # 11. 信用値の外部展開
    sid = dk.slide(); dk.kicker(sid, "THE BIG EXPANSION"); dk.title(sid, "最大の拡張：学生信用値（個信）。")
    dk.text(sid, MX, int(1.8 * IN), CW, int(0.5 * IN),
            [("偏差値（実力）＋誠実さ（飛びの無さ）＋実績 ＝ ", {"size": 14, "color": INK, "font": BODY}), ("ポータブルな信用", {"size": 14, "color": RED, "bold": True, "font": BODY})])
    flow = ["就活で信用を蓄積", "本人同意で外部へ", "賃貸・金融・保証", "就活後もLTVが続く"]
    n = len(flow); g = int(0.16 * IN); bw = (CW - g * (n - 1)) // n; y = int(2.5 * IN); h = int(1.0 * IN); x = MX
    for i, t in enumerate(flow):
        dk.rect(sid, x, y, bw, h, fill=WHITE, line=LINE, lw=1.2, round=True)
        dk.text(sid, x + int(0.15 * IN), y, bw - int(0.3 * IN), h, [(t, {"size": 11.5, "color": INK, "bold": True, "font": BODY})], align="CENTER", valign="MIDDLE")
        if i < n - 1:
            dk.text(sid, x + bw - int(0.02 * IN), y, g + int(0.08 * IN), h, [("›", {"size": 18, "color": RED, "bold": True, "font": HEAD})], align="CENTER", valign="MIDDLE")
        x += bw + g
    dk.text(sid, MX, int(3.85 * IN), CW, int(0.5 * IN),
            [("Timee型の発想転換（行動データ→信用→生活サービス）。これが収益の最大拡張点。", {"size": 12.5, "color": INK, "font": BODY})])
    dk.rect(sid, MX, int(4.45 * IN), CW, int(0.5 * IN), fill="F6ECEA", round=True); dk.rect(sid, MX, int(4.45 * IN), int(0.08 * IN), int(0.5 * IN), fill=RED)
    dk.text(sid, MX + int(0.28 * IN), int(4.45 * IN), CW - int(0.56 * IN), int(0.5 * IN),
            [("※ 信用情報規制・個人情報保護＝要法務。同意基盤は早期に、実装は最終フェーズ＋専門家レビュー。", {"size": 10.5, "color": INK, "font": BODY})], valign="MIDDLE")
    dk.foot(sid)

    # 12. マネタイズ
    sid = dk.slide(); dk.kicker(sid, "MONETIZATION"); dk.title(sid, "0円掲載を入口に、多層マネタイズ。")
    items = [("スカウト課金", "通数 or 枠"), ("特別オファー枠", "偏差値上位への限定"), ("成功報酬", "採用確定で"),
             ("データプロダクト", "母集団分析・採用ベンチマーク"), ("長期インターン送客", "姉妹メディア連携"), ("信用値レベニューシェア", "外部提携")]
    g = int(0.22 * IN); cwd = (CW - g * 2) // 3; chh = int(1.05 * IN); y0 = int(1.8 * IN)
    for i, (t, d) in enumerate(items):
        x = MX + (i % 3) * (cwd + g); yy = y0 + (i // 3) * (chh + int(0.2 * IN))
        dk.rect(sid, x, yy, cwd, chh, fill=WHITE, line=LINE, lw=1.2, round=True)
        dk.text(sid, x + int(0.22 * IN), yy + int(0.16 * IN), cwd - int(0.4 * IN), int(0.4 * IN), [(t, {"size": 12.5, "color": INK, "bold": True, "font": HEAD})])
        dk.text(sid, x + int(0.22 * IN), yy + int(0.58 * IN), cwd - int(0.4 * IN), int(0.4 * IN), [(d, {"size": 10, "color": SUB, "font": BODY})])
    dk.text(sid, MX, int(4.55 * IN), CW, int(0.35 * IN), [("データが溜まるほど、商品が増える。", {"size": 13, "color": RED, "bold": True, "font": HEAD})], align="CENTER")
    dk.foot(sid)

    # 13. 市場とタイミング
    sid = dk.slide(); dk.kicker(sid, "MARKET ・ WHY NOW"); dk.title(sid, "なぜ「今」か。")
    cols = [("転換点", "AIが情報を無料化。情報メディアが崩れ、「成果ネットワーク」へ価値が移る一度きりの窓。"),
            ("市場", "新卒就活市場 約〔要数値〕万人/年。採用費は1人あたり〔要数値〕万円規模（実数を差し込み）。"),
            ("数字が示す", "2027卒 内定率 67.0%（5/1時点・就職みらい研究所）。3月38.1%→5月67.0%＝動き出しの差が内定を分ける。")]
    g = int(0.24 * IN); cwd = (CW - g * 2) // 3; y = int(1.85 * IN); h = int(2.6 * IN)
    for i, (t, d) in enumerate(cols):
        x = MX + i * (cwd + g)
        dk.rect(sid, x, y, cwd, h, fill=(NIGHT if i == 2 else WHITE), line=(None if i == 2 else LINE), lw=1.2, round=True)
        dk.text(sid, x + int(0.24 * IN), y + int(0.22 * IN), cwd - int(0.48 * IN), int(0.4 * IN), [(t, {"size": 12, "color": (EMBER if i == 2 else RED), "bold": True, "font": MONO})])
        dk.text(sid, x + int(0.24 * IN), y + int(0.7 * IN), cwd - int(0.48 * IN), int(1.7 * IN), [(d, {"size": 12, "color": ("E7DED5" if i == 2 else INK), "font": BODY})])
    dk.text(sid, MX, int(4.6 * IN), CW, int(0.3 * IN), [("〔要数値〕は確定実数を後で差し込む（捏造しない）。", {"size": 9.5, "color": SUB, "font": MONO})])
    dk.foot(sid)

    # 14. 現在地
    sid = dk.slide(); dk.kicker(sid, "TRACTION"); dk.title(sid, "絵に描いた餅ではない ― すでに動くMVP。")
    live = [("リッチな新メディア", "明朝×実写の上質トップ・人気企業ランキング・締切"), ("会員登録基盤", "低ハードル登録→プロフィール保存→会員状態で出し分け"),
            ("人事のリアル（会員限定）", "公開ティーザーはAI引用、本文は会員だけに"), ("特典AIツール", "自己分析シート・対策AI(β)が稼働"),
            ("二面ネットワークのプロト", "マイページ↔スカウト↔企業(/recruiter) が両方向で動く"), ("AIO/クローラビリティ", "公開は引用される・会員データは非露出を実装で担保")]
    g = int(0.22 * IN); cwd = (CW - g) // 2; chh = int(0.86 * IN); y0 = int(1.78 * IN)
    for i, (t, d) in enumerate(live):
        x = MX + (i % 2) * (cwd + g); yy = y0 + (i // 2) * (chh + int(0.14 * IN))
        dk.rect(sid, x, yy, cwd, chh, fill=WHITE, line=LINE, lw=1.1, round=True)
        dk.rect(sid, x + int(0.2 * IN), yy + int(0.28 * IN), int(0.26 * IN), int(0.26 * IN), fill=RED, round=True)
        dk.text(sid, x + int(0.2 * IN), yy + int(0.27 * IN), int(0.26 * IN), int(0.26 * IN), [("✓", {"size": 11, "color": WHITE, "bold": True, "font": BODY})], align="CENTER", valign="MIDDLE")
        dk.text(sid, x + int(0.6 * IN), yy + int(0.14 * IN), cwd - int(0.8 * IN), int(0.36 * IN), [(t, {"size": 12.5, "color": INK, "bold": True, "font": HEAD})])
        dk.text(sid, x + int(0.6 * IN), yy + int(0.5 * IN), cwd - int(0.8 * IN), int(0.32 * IN), [(d, {"size": 9.5, "color": SUB, "font": BODY})])
    dk.foot(sid)

    # 15. ロードマップ＆Ask
    sid = dk.slide(); dk.kicker(sid, "ROADMAP ・ THE ASK"); dk.title(sid, "ロードマップと、お願いしたい意思決定。")
    ph = [("P1", "学生の司令塔", "選考ノート/スケジュール/ES・OpenES/偏差値/分析"), ("P2", "スコア基盤", "7軸偏差値・各テスト・模試判定"),
          ("P3", "企業/ネットワーク", "偏差値スカウト/OB訪問/掲載ダッシュボード"), ("P4", "実インフラ", "認証/DB/LINE/実AI/課金/信用値")]
    n = len(ph); g = int(0.16 * IN); bw = (CW - g * (n - 1)) // n; y = int(1.85 * IN); h = int(1.7 * IN); x = MX
    for i, (p, t, d) in enumerate(ph):
        dk.rect(sid, x, y, bw, h, fill=(RED if i == 0 else PAPER2), line=(None if i == 0 else LINE), lw=1, round=True)
        fg = WHITE if i == 0 else INK
        dk.text(sid, x + int(0.2 * IN), y + int(0.18 * IN), bw - int(0.4 * IN), int(0.4 * IN), [(p, {"size": 16, "color": (WHITE if i == 0 else RED), "bold": True, "font": MONO})])
        dk.text(sid, x + int(0.2 * IN), y + int(0.62 * IN), bw - int(0.4 * IN), int(0.4 * IN), [(t, {"size": 12, "color": fg, "bold": True, "font": HEAD})])
        dk.text(sid, x + int(0.2 * IN), y + int(1.0 * IN), bw - int(0.4 * IN), int(0.6 * IN), [(d, {"size": 9, "color": (WHITE if i == 0 else SUB), "font": BODY})])
        x += bw + g
    dk.rect(sid, MX, int(3.85 * IN), CW, int(1.05 * IN), fill=NIGHT, round=True)
    dk.text(sid, MX + int(0.3 * IN), int(3.98 * IN), CW - int(0.6 * IN), int(0.4 * IN), [("ご判断いただきたいこと", {"size": 11, "color": EMBER, "bold": True, "font": MONO})])
    dk.text(sid, MX + int(0.3 * IN), int(4.32 * IN), CW - int(0.6 * IN), int(0.55 * IN),
            [("① 開発投資（プロト→本番）　② エンジニア採用　③ 法務（職安法/個情法/信用情報）の着手承認", {"size": 12.5, "color": WHITE, "bold": True, "font": BODY})])
    dk.foot(sid, dark=False)

    # 16. クロージング
    sid = dk.slide(bg=NIGHT)
    dk.text(sid, MX, int(0.55 * IN), CW, int(0.26 * IN), [("CLOSING", {"size": 10, "color": EMBER, "bold": True, "font": MONO})])
    dk.text(sid, MX, int(1.5 * IN), CW, int(1.8 * IN),
            [("全部つながり、\nデータで企業を良くする。", {"size": 38, "color": WHITE, "bold": True, "font": HEAD})], spacing=112)
    dk.rect(sid, MX, int(3.5 * IN), int(1.1 * IN), int(0.05 * IN), fill=RED)
    dk.text(sid, MX, int(3.75 * IN), CW, int(0.5 * IN), [("就活のブラックボックスを開け、世の中の採用を変える。", {"size": 15, "color": "E7DED5", "font": BODY})])
    dk.text(sid, MX, PH - int(0.7 * IN), CW, int(0.3 * IN), [("次の一歩 ＝ P1（学生の司令塔）着手　・　とくもり就活", {"size": 11, "color": "9B8F84", "font": MONO})])
    return dk


def main():
    creds = Credentials.from_authorized_user_file(TOK)
    if not creds.valid: creds.refresh(Request())
    slides = build("slides", "v1", credentials=creds)
    pid = open(IDF).read().strip() if os.path.exists(IDF) else None
    if pid:
        pres = slides.presentations().get(presentationId=pid).execute()
        delr = [{"deleteObject": {"objectId": s["objectId"]}} for s in pres.get("slides", [])]
    else:
        pres = slides.presentations().create(body={"title": TITLE}).execute()
        pid = pres["presentationId"]; delr = [{"deleteObject": {"objectId": pres["slides"][0]["objectId"]}}]
    dk = Deck(nonce="e"); build_deck(dk)
    safe_bu(slides, pid, delr + dk.reqs)
    open(IDF, "w").write(pid)
    print("PAGES:", dk.page)
    print("URL: https://docs.google.com/presentation/d/%s/edit" % pid)


if __name__ == "__main__":
    main()
