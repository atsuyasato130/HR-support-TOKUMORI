#!/usr/bin/env python3
"""
新卒CA研修「業界×職種マップ」を Google Sheets API で「ライブのGoogleスプレッドシート」として
ゼロから生成する（hr-support MCP の token_sheets.json 認証を直接利用）。
データ正本 = data_ca_training.json（gas_ca_training_v1.js から抽出）。
デザイン = Tokumori ブランド（赤 #AF322C ＋黒＋グレー）。
"""
import json, math, os, sys, warnings
warnings.filterwarnings("ignore")

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

BASE = "/Users/atsuyasato/Claude AI"
TOK = "/Users/atsuyasato/Claude AI/tokumori/agents/hr_support/config/token_sheets.json"
with open(os.path.join(BASE, "data_ca_training.json"), encoding="utf-8") as f:
    D = json.load(f)

# ===== カラー =====
RED="AF322C"; BLACK="000000"; WHITE="FFFFFF"; INK="1A1A1A"; SUB="6B6B6B"
ZEBRA="F7F5F4"; BORDER="D9D9D9"; CHIP_MID="E4E4E4"; CHIP_LOW="EFEDEC"; DARK="2B2B2B"; LINK="1155CC"

T = {"TOC":"00_使い方","IMAP":"01_業界マップ","IDET":"02_業界詳細","JMAP":"03_職種マップ",
     "JDET":"04_職種詳細","RANK":"05_人気ランキング","TIPS":"06_面談活用メモ","DEEP":"07_深掘りテンプレ"}
ORDER = ["TOC","IMAP","IDET","JMAP","JDET","RANK","TIPS","DEEP"]


def rgb(h):
    return {"red":int(h[0:2],16)/255,"green":int(h[2:4],16)/255,"blue":int(h[4:6],16)/255}


class SM:
    def __init__(self, sheet_id, gid):
        self.id = sheet_id      # batchUpdate用 sheetId
        self.gid = gid          # ハイパーリンク用 gid（=sheetId）
        self.grid = {}          # (r,c)->(value,fmt)  1-indexed
        self.merges = []        # (r1,c1,r2,c2) inclusive
        self.col_px = {1:24}    # A列=余白
        self.row_px = {}
        self.freeze = (0,0)
        self.filter = None      # (r1,c1,r2,c2) inclusive

    def put(self, r, c, value="", **fmt):
        self.grid[(r,c)] = (value, fmt)

    def fillblock(self, r1, c1, r2, c2, **fmt):
        for r in range(r1, r2+1):
            for c in range(c1, c2+1):
                if (r,c) in self.grid:
                    v,f = self.grid[(r,c)]; f2=dict(f); f2.update(fmt); self.grid[(r,c)]=(v,f2)
                else:
                    self.grid[(r,c)] = ("", dict(fmt))

    def merge(self, r1, c1, r2, c2):
        self.merges.append((r1,c1,r2,c2))


# ===== ヘルパー =====
def band_title(sm, row, c1, c2, text):
    sm.fillblock(row, c1, row, c2, bg=RED)
    sm.put(row, c1, text, bg=RED, font=WHITE, bold=True, size=12, valign="MIDDLE", halign="LEFT")
    sm.merge(row, c1, row, c2)
    sm.row_px[row] = 28


def note(sm, row, col, span, text, size=9, color=SUB, bold=False):
    sm.put(row, col, text, font=color, size=size, bold=bold, wrap=True, valign="MIDDLE")
    sm.merge(row, col, row, col+span-1)
    per = sum(sm.col_px.get(col+x, 90) for x in range(span)) / 14.0
    lines = max(1, math.ceil(len(str(text)) / max(6, per)))
    sm.row_px[row] = min(120, max(21, lines*16 + 5))
    return row + 1


def kpi(sm, label_row, items, start, width):
    c = start
    for it in items:
        sm.fillblock(label_row, c, label_row, c+width-1, bg=DARK, border=True)
        sm.put(label_row, c, it["label"], bg=DARK, font=WHITE, bold=True, size=10, halign="CENTER", valign="MIDDLE", border=True)
        sm.merge(label_row, c, label_row, c+width-1)
        sm.fillblock(label_row+1, c, label_row+1, c+width-1, bg=WHITE, border=True)
        sm.put(label_row+1, c, it["value"], bg=WHITE, font=(RED if it["accent"] else INK), bold=True, size=24, halign="CENTER", valign="MIDDLE", border=True)
        sm.merge(label_row+1, c, label_row+1, c+width-1)
        c += width
    sm.row_px[label_row] = 24
    sm.row_px[label_row+1] = 46


def table(sm, row, col, header, rows, col_px, red_cols=None, pop_col=None):
    w = len(header)
    for j, h in enumerate(header):
        sm.put(row, col+j, h, bg=BLACK, font=WHITE, bold=True, size=10, halign="CENTER", valign="MIDDLE", wrap=True, border=True)
    sm.row_px[row] = 24
    for i, rd in enumerate(rows):
        rr = row+1+i
        bg = ZEBRA if i % 2 else WHITE
        for j, val in enumerate(rd):
            f = dict(bg=bg, font=INK, size=10, valign="TOP", wrap=True, border=True)
            if red_cols and j in red_cols:
                f["font"]=RED; f["bold"]=True
            sm.put(rr, col+j, val, **f)
        if pop_col is not None:
            v = str(rd[pop_col])
            if v[:1] == "高": pf = dict(bg=RED, font=WHITE)
            elif "低" in v: pf = dict(bg=CHIP_LOW, font=SUB)
            else: pf = dict(bg=CHIP_MID, font=INK)
            sm.put(rr, col+pop_col, rd[pop_col], bold=True, size=10, halign="CENTER", valign="MIDDLE", wrap=True, border=True, **pf)
    for j, px in enumerate(col_px):
        sm.col_px[col+j] = px
    return row + len(rows) + 2


def merge_table(sm, row, start, header, spans, rows, red_cols=None, link_col=None):
    c = start
    for k, h in enumerate(header):
        sm.fillblock(row, c, row, c+spans[k]-1, bg=BLACK, border=True)
        sm.put(row, c, h, bg=BLACK, font=WHITE, bold=True, size=10, halign="CENTER", valign="MIDDLE", wrap=True, border=True)
        sm.merge(row, c, row, c+spans[k]-1)
        c += spans[k]
    sm.row_px[row] = 24
    for i, rd in enumerate(rows):
        rr = row+1+i; c = start; bg = ZEBRA if i % 2 else WHITE; maxlen = 1
        for k, val in enumerate(rd):
            sm.fillblock(rr, c, rr, c+spans[k]-1, bg=bg, border=True)
            if link_col is not None and k == link_col and str(val).startswith("http"):
                sm.put(rr, c, '=HYPERLINK("%s","%s")' % (val, val), bg=bg, font=LINK, size=9, valign="TOP", wrap=True, border=True)
            else:
                f = dict(bg=bg, font=INK, size=10, valign="TOP", wrap=True, border=True)
                if red_cols and k in red_cols: f["font"]=RED; f["bold"]=True
                sm.put(rr, c, val, **f)
            sm.merge(rr, c, rr, c+spans[k]-1)
            maxlen = max(maxlen, len(str(val)))
            c += spans[k]
        sm.row_px[rr] = min(190, max(21, math.ceil(maxlen/30)*16 + 6))
    return row + len(rows) + 2


def backlink(sm, col, toc_gid):
    sm.put(1, col, '=HYPERLINK("#gid=%d","← 目次へ戻る")' % toc_gid, font=SUB, size=9, halign="RIGHT")
    sm.row_px[1] = 16


def group_by_dai(items, idx=1):
    order, m = [], {}
    for r in items:
        d = r[idx]
        if d not in m: m[d]=[]; order.append(d)
        m[d].append(r)
    return [(d, m[d]) for d in order]


# ===== 各タブ =====
def build_toc(sm, gids):
    for c,px in enumerate([96]*12): sm.col_px[2+c]=px
    band_title(sm, 2, 2, 13, "■ 新卒キャリアアドバイザー研修｜業界 × 職種マップ")
    note(sm, 3, 2, 12, "面談の前提知識（業界理解・職種理解）を体系的にインプットするための資料です。学生人気の高い業界から学べる構成。各表はフィルタで絞り込み・並べ替えができます。", size=10, color=INK)
    n_dai = len(group_by_dai(D["INDUSTRIES"]))
    kpi(sm, 5, [
        {"label":"収録 業界数","value":len(D["INDUSTRIES"]),"accent":True},
        {"label":"収録 職種数","value":len(D["JOBS"]),"accent":True},
        {"label":"業界 大分類","value":n_dai,"accent":False},
        {"label":"最終更新","value":D["UPDATED"],"accent":False},
    ], 2, 3)
    r = 8
    band_title(sm, r, 2, 13, "■ 目次（タブ名をクリックで各シートへ移動）"); r += 1
    toc = [("IMAP","10大分類→業界の俯瞰マップ。1業界1行で人気度・代表企業を一覧"),
           ("IDET","メインのインプット表。各業界をビジネスモデル〜面談ポイントまで詳細に"),
           ("JMAP","職種の全体像。営業を6軸に分解。大分類→中分類のマップ"),
           ("JDET","各職種の仕事内容・向き不向き・キャリアパス・面談での伝え方"),
           ("RANK","最新（2027/2026卒）人気企業ランキング・業界トレンド・就活トレンド"),
           ("TIPS","面談で押さえる横断ポイントと、学生に説明するための用語集"),
           ("DEEP","人気業界を1業界1タブで深掘りするための空テンプレ（複製して充填）")]
    sm.fillblock(r, 2, r, 3, bg=BLACK, border=True); sm.put(r, 2, "タブ", bg=BLACK, font=WHITE, bold=True, size=10, halign="CENTER", valign="MIDDLE", border=True); sm.merge(r,2,r,3)
    sm.fillblock(r, 4, r, 13, bg=BLACK, border=True); sm.put(r, 4, "内容", bg=BLACK, font=WHITE, bold=True, size=10, halign="CENTER", valign="MIDDLE", border=True); sm.merge(r,4,r,13)
    sm.row_px[r]=24
    for i,(key,desc) in enumerate(toc):
        rr=r+1+i; bg=ZEBRA if i%2 else WHITE
        sm.fillblock(rr,2,rr,3,bg=bg,border=True)
        sm.put(rr,2,'=HYPERLINK("#gid=%d","%s")'%(gids[key],T[key]), bg=bg, font=LINK, bold=True, size=10, valign="MIDDLE", border=True)
        sm.merge(rr,2,rr,3)
        sm.fillblock(rr,4,rr,13,bg=bg,border=True)
        sm.put(rr,4,desc,bg=bg,font=INK,size=10,wrap=True,valign="MIDDLE",border=True)
        sm.merge(rr,4,rr,13)
        sm.row_px[rr]=22
    r=r+len(toc)+2
    band_title(sm, r, 2, 13, "■ 人気度の凡例"); r+=1
    for cc,lab,bgc,fc in [(2,"高",RED,WHITE),(5,"中",CHIP_MID,INK),(8,"低",CHIP_LOW,SUB)]:
        sm.fillblock(r,cc,r,cc+2,bg=bgc); sm.put(r,cc,lab,bg=bgc,font=fc,bold=True,halign="CENTER",valign="MIDDLE"); sm.merge(r,cc,r,cc+2)
    sm.row_px[r]=22; r+=1
    r=note(sm,r,2,12,"人気度は各種ランキングを踏まえた体感の目安です。年度・大学・学生の志向で変動します（断定ではなく面談の入口として活用してください）。",size=9,color=SUB)
    note(sm,r,2,12,"出典・更新：人気ランキングの数値と出典URLは「05_人気ランキング」タブに記載。データは "+D["UPDATED"]+" 時点。",size=9,color=SUB)
    sm.freeze=(2,0)


def build_imap(sm, gids):
    px=[160,330,70,300]
    for c,p in enumerate(px): sm.col_px[2+c]=p
    backlink(sm,5,gids["TOC"])
    band_title(sm,2,2,5,"■ 業界マップ（大分類 → 中分類の俯瞰）")
    r=note(sm,3,2,4,"人気の高い大分類を上から配置。詳細は「02_業界詳細」へ。",size=9,color=SUB); r+=1
    for dai,rows in group_by_dai(D["INDUSTRIES"]):
        band_title(sm,r,2,5,"■ %s（%d業界）"%(dai,len(rows))); r+=1
        data=[[x[0],x[2],x[8],x[4]] for x in rows]
        r=table(sm,r,2,["業界（中分類）","一言でいうと","人気度","代表企業"],data,px,pop_col=2)
    sm.freeze=(0,0)


def build_idet(sm, gids):
    px=[130,95,200,220,175,175,195,220,64,270]
    for c,p in enumerate(px): sm.col_px[2+c]=p
    backlink(sm,11,gids["TOC"])
    band_title(sm,2,2,11,"■ 業界詳細（面談インプット用マスタ）")
    note(sm,3,2,10,"ヘッダーのフィルタで大分類・人気度などで絞り込み／並べ替えできます。",size=9,color=SUB)
    header=["業界（中分類）","大分類","一言でいうと","ビジネスモデル・収益源","代表企業","主要職種","働き方の特徴","将来性・トレンド","人気度","面談ポイント・よくある誤解"]
    n=len(D["INDUSTRIES"])
    table(sm,5,2,header,D["INDUSTRIES"],px,pop_col=8)
    sm.freeze=(5,0)
    sm.filter=(5,2,5+n,11)


def build_jmap(sm, gids):
    px=[200,110,360]
    for c,p in enumerate(px): sm.col_px[2+c]=p
    backlink(sm,5,gids["TOC"])
    band_title(sm,2,2,4,"■ 職種マップ（大分類 → 中分類）")
    r=note(sm,3,2,3,"「営業」は一括りにせず6つの軸で別物として捉えるのがポイント。詳細は「04_職種詳細」へ。",size=9,color=SUB); r+=1
    band_title(sm,r,2,4,"■ 営業を読み解く6軸"); r+=1
    r=table(sm,r,2,["軸","対比","ひとことで"],D["SALES_AXES"],px)
    for dai,rows in group_by_dai(D["JOBS"]):
        band_title(sm,r,2,4,"■ %s（%d職種）"%(dai,len(rows))); r+=1
        data=[[x[0],x[2],x[3]] for x in rows]
        r=table(sm,r,2,["職種","分類軸","仕事内容（要約）"],data,px)
    sm.freeze=(0,0)


def build_jdet(sm, gids):
    px=[160,110,80,220,160,150,150,175,175,120,260]
    for c,p in enumerate(px): sm.col_px[2+c]=p
    backlink(sm,12,gids["TOC"])
    band_title(sm,2,2,12,"■ 職種詳細（面談インプット用マスタ）")
    note(sm,3,2,11,"ヘッダーのフィルタで大分類・分類軸で絞り込み／並べ替えできます。",size=9,color=SUB)
    header=["職種","大分類","分類軸","仕事内容","求められる力","向いている人","向かない人","代表業界・配属","キャリアパス","採用の多さ・人気","学生の誤解・面談で伝えること"]
    n=len(D["JOBS"])
    table(sm,5,2,header,D["JOBS"],px)
    sm.freeze=(5,0)
    sm.filter=(5,2,5+n,12)


def rank_table(sm, row, col, title, data):
    sm.fillblock(row,col,row,col+2,bg=BLACK,border=True)
    sm.put(row,col,title,bg=BLACK,font=WHITE,bold=True,size=10,valign="MIDDLE",halign="LEFT",border=True)
    sm.merge(row,col,row,col+2)
    sm.row_px[row]=22
    table(sm,row+1,col,["#","企業","業界"],data,[44,200,170],red_cols=[0])
    return row+1+len(data)


def build_rank(sm, gids):
    for c,p in enumerate([44,200,170,44,200,170]): sm.col_px[2+c]=p
    backlink(sm,7,gids["TOC"])
    band_title(sm,2,2,7,"■ 人気ランキング・トレンド（2027/2026卒）")
    r=4
    band_title(sm,r,2,7,"■ 最初に押さえる要点"); r+=1
    r=merge_table(sm,r,2,["観点","内容"],[2,4],D["RANK_NOTES"],red_cols=[0])
    band_title(sm,r,2,7,"■ 人気企業ランキング（出典・集計方法で順位は変わる）"); r+=1
    a=rank_table(sm,r,2,"マイナビ・日経 27卒｜文系TOP10",D["RANK_MYNAVI_BUNKEI"])
    b=rank_table(sm,r,5,"マイナビ・日経 27卒｜理系TOP10",D["RANK_MYNAVI_RIKEI"])
    r=max(a,b)+2
    c=rank_table(sm,r,2,"ワンキャリア 27卒｜文系TOP10",D["RANK_ONECAREER_B"])
    d=rank_table(sm,r,5,"ワンキャリア 27卒｜理系TOP10",D["RANK_ONECAREER_R"])
    r=max(c,d)+2
    e=rank_table(sm,r,2,"文化放送 27卒｜総合TOP15（ブランド志向）",D["RANK_BUNKA"])
    f=rank_table(sm,r,5,"学情 27卒｜総合TOP5",D["RANK_GAKUJO"])
    r=max(e,f)+2
    band_title(sm,r,2,7,"■ 業界人気のトレンド"); r+=1
    r=merge_table(sm,r,2,["業界","動向","確度"],[2,3,1],D["TREND"],red_cols=[0])
    band_title(sm,r,2,7,"■ 出典"); r+=1
    r=merge_table(sm,r,2,["調査","URL"],[2,4],D["RANK_SOURCES"],link_col=1)
    note(sm,r,2,6,"注：数値・順位は各調査の集計方法（エントリー実数型／ブランド志向型／お気に入り型）で異なります。11〜30位や一部業界別順位は最新未確認のため、研修配布時は各URLで補完してください。",size=9,color=SUB)
    sm.freeze=(2,0)


def build_tips(sm, gids):
    px=[210,620]
    for c,p in enumerate(px): sm.col_px[2+c]=p
    backlink(sm,3,gids["TOC"])
    band_title(sm,2,2,3,"■ 面談で押さえる横断ポイント")
    r=table(sm,4,2,["観点","内容"],D["TIPS"],px,red_cols=[0])
    band_title(sm,r,2,3,"■ 用語集（学生に説明できるように）"); r+=1
    table(sm,r,2,["用語","意味"],D["GLOSSARY"],px,red_cols=[0])
    sm.freeze=(0,0)


def build_deep(sm, gids):
    px=[320,520]
    for c,p in enumerate(px): sm.col_px[2+c]=p
    backlink(sm,3,gids["TOC"])
    band_title(sm,2,2,3,"■ 業界深掘りテンプレート（このシートを複製して使用）")
    r=note(sm,3,2,2,"使い方：このタブを複製し、タブ名を「08_総合商社」等に変更。下表の各章を埋めて、その業界の『面談で使えるレベル』の深掘り版を作る。まずは人気上位（総合商社/コンサル/IT/金融/メーカー/広告/人材）から。",size=10,color=INK); r+=1
    sm.put(r,2,"対象業界：＿＿＿＿＿＿＿＿",font=RED,bold=True,size=12); sm.row_px[r]=26; r+=2
    rows=[[s,""] for s in D["DEEP_SECTIONS"]]
    start=r
    r=table(sm,r,2,["章立て","記入欄"],rows,px,red_cols=[0])
    for i in range(len(rows)): sm.row_px[start+1+i]=52
    sm.freeze=(0,0)


# ===== Sheets API リクエスト生成 =====
def cell_data(entry):
    if entry is None:
        return {}
    value, fmt = entry
    cd = {}
    if value not in ("", None):
        if isinstance(value, bool):
            cd["userEnteredValue"]={"boolValue":value}
        elif isinstance(value, (int, float)):
            cd["userEnteredValue"]={"numberValue":value}
        elif isinstance(value, str) and value.startswith("="):
            cd["userEnteredValue"]={"formulaValue":value}
        else:
            cd["userEnteredValue"]={"stringValue":str(value)}
    uf={}
    if fmt.get("bg"): uf["backgroundColor"]=rgb(fmt["bg"])
    tf={}
    if fmt.get("font"): tf["foregroundColor"]=rgb(fmt["font"])
    if fmt.get("bold"): tf["bold"]=True
    if fmt.get("size"): tf["fontSize"]=fmt["size"]
    if tf: uf["textFormat"]=tf
    if fmt.get("halign"): uf["horizontalAlignment"]=fmt["halign"]
    if fmt.get("valign"): uf["verticalAlignment"]=fmt["valign"]
    if fmt.get("wrap"): uf["wrapStrategy"]="WRAP"
    if fmt.get("border"):
        b={"style":"SOLID","color":rgb(BORDER)}
        uf["borders"]={"top":b,"bottom":b,"left":b,"right":b}
    if uf: cd["userEnteredFormat"]=uf
    return cd


def sm_requests(sm):
    reqs=[]
    rmax=max((r for (r,c) in sm.grid), default=1)
    cmax=max((c for (r,c) in sm.grid), default=1)
    # クリーンアップ先行：既存の結合を解除してから再描画（再実行時の二重結合防止）
    reqs.append({"unmergeCells":{"range":{"sheetId":sm.id,"startRowIndex":0,
        "endRowIndex":max(rmax,200),"startColumnIndex":0,"endColumnIndex":max(cmax,26)}}})
    rows=[]
    for r in range(1, rmax+1):
        vals=[cell_data(sm.grid.get((r,c))) for c in range(1, cmax+1)]
        rows.append({"values":vals})
    reqs.append({"updateCells":{"rows":rows,"fields":"userEnteredValue,userEnteredFormat",
                "start":{"sheetId":sm.id,"rowIndex":0,"columnIndex":0}}})
    for (r1,c1,r2,c2) in sm.merges:
        reqs.append({"mergeCells":{"mergeType":"MERGE_ALL","range":{"sheetId":sm.id,
            "startRowIndex":r1-1,"endRowIndex":r2,"startColumnIndex":c1-1,"endColumnIndex":c2}}})
    for c,px in sm.col_px.items():
        reqs.append({"updateDimensionProperties":{"range":{"sheetId":sm.id,"dimension":"COLUMNS",
            "startIndex":c-1,"endIndex":c},"properties":{"pixelSize":px},"fields":"pixelSize"}})
    for r,px in sm.row_px.items():
        reqs.append({"updateDimensionProperties":{"range":{"sheetId":sm.id,"dimension":"ROWS",
            "startIndex":r-1,"endIndex":r},"properties":{"pixelSize":px},"fields":"pixelSize"}})
    fr,fc=sm.freeze
    reqs.append({"updateSheetProperties":{"properties":{"sheetId":sm.id,
        "gridProperties":{"hideGridlines":True,"frozenRowCount":fr,"frozenColumnCount":fc}},
        "fields":"gridProperties.hideGridlines,gridProperties.frozenRowCount,gridProperties.frozenColumnCount"}})
    if sm.filter:
        r1,c1,r2,c2=sm.filter
        reqs.append({"setBasicFilter":{"filter":{"range":{"sheetId":sm.id,
            "startRowIndex":r1-1,"endRowIndex":r2,"startColumnIndex":c1-1,"endColumnIndex":c2}}}})
    return reqs


def main():
    creds = Credentials.from_authorized_user_file(TOK)
    if not creds.valid:
        creds.refresh(Request())
    svc = build("sheets","v4",credentials=creds)

    reuse=os.environ.get("CA_SHEET_ID","").strip()
    if reuse:
        # 既存スプレッドシートを再利用（作り直し）。Drive削除APIが無効なため孤児を増やさない。
        ss=svc.spreadsheets().get(spreadsheetId=reuse, fields="spreadsheetId,spreadsheetUrl,sheets(properties(sheetId,title))").execute()
        print("reuse:", ss["spreadsheetUrl"])
    else:
        body={"properties":{"title":"新卒CA研修_業界×職種マップ_v1"},
              "sheets":[{"properties":{"title":T[k]}} for k in ORDER]}
        ss=svc.spreadsheets().create(body=body, fields="spreadsheetId,spreadsheetUrl,sheets(properties(sheetId,title))").execute()
        print("created:", ss["spreadsheetUrl"])
    ssid=ss["spreadsheetId"]; url=ss["spreadsheetUrl"]
    title2gid={s["properties"]["title"]:s["properties"]["sheetId"] for s in ss["sheets"]}
    gids={k:title2gid[T[k]] for k in ORDER}

    # 2) 各タブを構築
    models={}
    for k in ORDER:
        sm=SM(gids[k], gids[k]); models[k]=sm
    build_toc(models["TOC"], gids)
    build_imap(models["IMAP"], gids)
    build_idet(models["IDET"], gids)
    build_jmap(models["JMAP"], gids)
    build_jdet(models["JDET"], gids)
    build_rank(models["RANK"], gids)
    build_tips(models["TIPS"], gids)
    build_deep(models["DEEP"], gids)

    # 3) batchUpdate（タブごとに分割実行＝リクエスト過大回避）
    for k in ORDER:
        reqs=sm_requests(models[k])
        svc.spreadsheets().batchUpdate(spreadsheetId=ssid, body={"requests":reqs}).execute()
        print("built tab:", T[k], "reqs=", len(reqs))

    open(os.path.join(BASE,".ca_sheet_id"),"w").write(ssid)
    print("DONE")
    print("URL:", url)
    print("ID:", ssid)


if __name__ == "__main__":
    main()
