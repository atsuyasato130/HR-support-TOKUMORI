#!/usr/bin/env python3
"""
Tokumori 新卒研修 — Googleスライド ビルダー（プレミアム・テンプレ v2）
token_sheets.json(presentationsスコープ)で Slides API を直接利用。
「誰が見ても高品質」を狙った設計：分割パネル表紙／大番号の章扉／カスタム赤マーカー／
プロセスフロー図／対比カード／一貫フッター＋ページ番号。
"""
import warnings, os, uuid, json, time, math, socket
warnings.filterwarnings("ignore")
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import figs_html as FH

def safe_bu(slides,pid,reqs):
    # 書き込みクォータ(60/分)対策：小分け＋429/ネットワーク例外リトライ＋スリープ
    for i in range(0,len(reqs),60):
        chunk=reqs[i:i+60]
        for attempt in range(8):
            try:
                slides.presentations().batchUpdate(presentationId=pid,body={"requests":chunk}).execute(); break
            except HttpError as e:
                es=str(e)
                if ("429" in es) or ("RATE_LIMIT" in es):
                    print("  ...rate limit, wait 45s"); time.sleep(45); continue
                # createImageのDrive画像が未伝播の一時的400 → 待って再試行（画像が公開・取得可になるまで）
                if ("createImage" in es or "retrieving the image" in es) and attempt<7:
                    w=6+attempt*5; print("  ...image not ready, retry in %ds"%w); time.sleep(w); continue
                raise
            except (socket.timeout, OSError, ConnectionError, TimeoutError) as e:
                if attempt==7: raise
                print("  ...network error (%s), retry in 10s"%type(e).__name__); time.sleep(10); continue
        time.sleep(1.5)

BASE="/Users/atsuyasato/Claude AI"
TOK="/Users/atsuyasato/Claude AI/tokumori/agents/hr_support/config/token_sheets.json"
SSID=open(os.path.join(BASE,".ca_sheet_id")).read().strip()
_ENR=os.path.join(BASE,"data_deck_enrich.json")
ENRICH=json.load(open(_ENR,encoding="utf-8")) if os.path.exists(_ENR) else {}

IN=914400
PW, PH = 9144000, 5143500
MX=int(0.62*IN); CW=PW-2*MX
RED="AF322C"; REDD="7A211C"; INK="1A1714"; INKDK="23201E"; SUB="6B6B6B"; WHITE="FFFFFF"
LRED="F6ECEA"; LGREEN="F2F1F0"; PANEL="FAF8F7"; FAINT="EEEAE8"; RULE="E6E3E1"; GREEN="000000"; LINKC="1155CC"
ROSE="C9938F"; ONDARK="C9C2BD"  # 暗地用のローズ／淡文字
DISP="Shippori Mincho B1"; HEAD="Zen Kaku Gothic New"; BODY="Noto Sans JP"; MONO="IBM Plex Mono"

# ---- 用途別テーマ：set_theme(name) でモジュールglobalsを差し替え＝全コンポーネントに自動波及 ----
# 既定=training（脱AI済の赤editorial）。corporate=概要/採用ピッチ用（見出し明朝・余白広めの可読クリーン）。
# 脱AIの“構造”（赤下線撤去/POINT箱→引用線/箇条マーカー軽量化）は全テーマ共通でメソッド側に実装。
THEMES={
 "training": dict(RED="AF322C",REDD="7A211C",INK="1A1714",INKDK="23201E",SUB="6B6B6B",
                  PANEL="FAF8F7",FAINT="EEEAE8",LRED="F6ECEA",RULE="E6E3E1",ROSE="C9938F",
                  DISP="Shippori Mincho B1",HEAD="Zen Kaku Gothic New",BODY="Noto Sans JP",MONO="IBM Plex Mono",
                  FOOTLABEL="新卒研修プログラム"),
 "corporate":dict(RED="AF322C",REDD="7A211C",INK="1A1714",INKDK="23201E",SUB="7A736E",
                  PANEL="FBFAF9",FAINT="F1ECE9",LRED="F7EFED",RULE="ECE8E5",ROSE="C9938F",
                  DISP="Shippori Mincho B1",HEAD="Shippori Mincho B1",BODY="Noto Sans JP",MONO="IBM Plex Mono",
                  FOOTLABEL=""),
 # training_v2 = 新卒研修の新デザイン（クリーン・デジタル＝社内vivid系）: IBM Plex統一＋表紙/章扉を白基調の淡赤グラデ
 "training_v2":dict(RED="AF322C",REDD="7A211C",INK="1A1714",INKDK="23201E",SUB="6B6B6B",
                  PANEL="FAFAF9",FAINT="EEEAE8",LRED="F6ECEA",RULE="E6E3E1",ROSE="C9938F",
                  DISP="IBM Plex Sans JP",HEAD="IBM Plex Sans JP",BODY="IBM Plex Sans JP",MONO="IBM Plex Mono",
                  FOOTLABEL="新卒研修プログラム"),
}
THEME="training"; FOOTLABEL="新卒研修プログラム"
HERO_BG_URL=""  # training_v2 の表紙/章扉に敷く淡赤グラデ背景画像URL（main が起動時に1枚生成して設定）
# 図種ごとのHTML図の高さ(px)。Deck.diagram/各図メソッドが使用
_FIGH={"pyramid":430,"relation":440,"timeline":300,"ladder":430,"before_after":330,"cycle":430,
       "seating":430,"bar":380,"flow":300,"line":370,"quad":460,"matrix":460,"venn":430,"funnel":410,"donut":410,
       "platform":440,"formula":430,"converge":430,"process":320,"gridmatrix":420,"directions":430}
# 淡赤グラデ＋微細ドット（vivid系・クリーン）。html_to_slide で画像化して表紙/章扉に全幅挿入
GLOW_HTML=('<!DOCTYPE html><html><head><meta charset="utf-8"/><style>*{margin:0;}'
           'html,body{width:1280px;height:720px;}'
           '.c{width:1280px;height:720px;background:'
           'radial-gradient(60% 62% at 86% 94%, rgba(175,50,44,0.09), rgba(0,0,0,0) 70%),'
           'radial-gradient(46% 50% at 8% 2%, rgba(175,50,44,0.04), rgba(0,0,0,0) 70%),#ffffff;}'
           '.g{width:1280px;height:720px;background-image:radial-gradient(circle, rgba(26,23,20,0.04) 1px, transparent 1.4px);'
           'background-size:38px 38px;}'
           '</style></head><body><div class="c"><div class="g"></div></div></body></html>')
def set_theme(name):
    global THEME,RED,REDD,INK,INKDK,SUB,PANEL,FAINT,LRED,RULE,ROSE,DISP,HEAD,BODY,MONO,FOOTLABEL
    THEME=name if name in THEMES else "training"; t=THEMES[THEME]
    RED=t["RED"];REDD=t["REDD"];INK=t["INK"];INKDK=t["INKDK"];SUB=t["SUB"]
    PANEL=t["PANEL"];FAINT=t["FAINT"];LRED=t["LRED"];RULE=t["RULE"];ROSE=t["ROSE"]
    DISP=t["DISP"];HEAD=t["HEAD"];BODY=t["BODY"];MONO=t["MONO"];FOOTLABEL=t.get("FOOTLABEL","")
    return THEME

def rf(h): return {"red":int(h[0:2],16)/255,"green":int(h[2:4],16)/255,"blue":int(h[4:6],16)/255}

class Deck:
    def __init__(self,total,nonce): self.reqs=[]; self.n=0; self.page=0; self.total=total; self.nonce=nonce; self.tag=""
    def _id(self,p): self.n+=1; return "%s%s%04d"%(self.nonce,p,self.n)
    def slide(self, bg=WHITE):
        self.page+=1; sid="%ssld%03d"%(self.nonce,self.page)
        self.reqs.append({"createSlide":{"objectId":sid,"slideLayoutReference":{"predefinedLayout":"BLANK"},"insertionIndex":self.page-1}})
        self.reqs.append({"updatePageProperties":{"objectId":sid,"pageProperties":{"pageBackgroundFill":{"solidFill":{"color":{"rgbColor":rf(bg)}}}},"fields":"pageBackgroundFill.solidFill.color"}})
        return sid
    def rect(self,sid,x,y,w,h,fill=None,line=None,lw=1.0,round=False,shape="RECTANGLE"):
        oid=self._id("r")
        self.reqs.append({"createShape":{"objectId":oid,"shapeType":("ROUND_RECTANGLE" if round else shape),
            "elementProperties":{"pageObjectId":sid,"size":{"width":{"magnitude":w,"unit":"EMU"},"height":{"magnitude":h,"unit":"EMU"}},
            "transform":{"scaleX":1,"scaleY":1,"translateX":x,"translateY":y,"unit":"EMU"}}}})
        sp={}; f=[]
        if fill is not None: sp["shapeBackgroundFill"]={"solidFill":{"color":{"rgbColor":rf(fill)}}}; f.append("shapeBackgroundFill.solidFill.color")
        else: sp["shapeBackgroundFill"]={"propertyState":"NOT_RENDERED"}; f.append("shapeBackgroundFill.propertyState")
        if line is not None: sp["outline"]={"outlineFill":{"solidFill":{"color":{"rgbColor":rf(line)}}},"weight":{"magnitude":lw,"unit":"PT"},"dashStyle":"SOLID"}; f.append("outline")
        else: sp["outline"]={"propertyState":"NOT_RENDERED"}; f.append("outline.propertyState")
        if f: self.reqs.append({"updateShapeProperties":{"objectId":oid,"shapeProperties":sp,"fields":",".join(f)}})
        return oid
    def fit_size(self,text,w_emu,h_emu,maxsize,minsize=8,lh=1.42):
        """枠(w,h)に収まる最大フォントpt。全角≈1em/半角≈0.56emで折返し行数を概算。
        lh=1.42はSlidesの日本語の実効行間に合わせた値（はみ出し防止）。"""
        units=sum(1.0 if ord(ch)>=0x2000 else 0.56 for ch in text)
        if units<=0: return maxsize
        w_pt=w_emu/12700.0; h_pt=h_emu/12700.0; s=maxsize
        while s>minsize:
            cpl=max(1.0, w_pt/s)                 # 1行の全角換算文字数
            lines=max(1, math.ceil(units/cpl))
            if lines*s*lh<=h_pt: break
            s-=0.5
        return round(s,1)
    def text(self,sid,x,y,w,h,runs,align="START",valign="TOP",spacing=116,sb=4,ls=None,fit=None):
        oid=self._id("t")
        self.reqs.append({"createShape":{"objectId":oid,"shapeType":"TEXT_BOX",
            "elementProperties":{"pageObjectId":sid,"size":{"width":{"magnitude":w,"unit":"EMU"},"height":{"magnitude":h,"unit":"EMU"}},
            "transform":{"scaleX":1,"scaleY":1,"translateX":x,"translateY":y,"unit":"EMU"}}}})
        full="".join(t for t,_ in runs); self.reqs.append({"insertText":{"objectId":oid,"insertionIndex":0,"text":full}})
        eff=self.fit_size(full,w,h,fit[0],fit[1]) if fit else None
        idx=0
        for t,st in runs:
            if not t: continue
            stl={"fontFamily":st.get("font",BODY),"fontSize":{"magnitude":(eff if eff is not None else st.get("size",12)),"unit":"PT"},
                 "foregroundColor":{"opaqueColor":{"rgbColor":rf(st.get("color",INK))}},"bold":st.get("bold",False)}
            if ls is not None: stl["weightedFontFamily"]={"fontFamily":st.get("font",BODY)}
            self.reqs.append({"updateTextStyle":{"objectId":oid,"textRange":{"type":"FIXED_RANGE","startIndex":idx,"endIndex":idx+len(t)},
                "style":stl,"fields":"fontFamily,fontSize,foregroundColor,bold"}})
            idx+=len(t)
        self.reqs.append({"updateParagraphStyle":{"objectId":oid,"textRange":{"type":"ALL"},
            "style":{"alignment":align,"lineSpacing":spacing,"spaceBelow":{"magnitude":sb,"unit":"PT"}},"fields":"alignment,lineSpacing,spaceBelow"}})
        self.reqs.append({"updateShapeProperties":{"objectId":oid,"shapeProperties":{"contentAlignment":valign},"fields":"contentAlignment"}})
        return oid
    # ---- 共通パーツ ----
    def logo_mark(self,sid,x,y,D):
        # TOKUMORI シンボル（ご飯のマーク）= 黒いドーム(盛ったご飯) ＋ 赤い半円(器)。白背景前提でマスク合成。
        bw=max(1.2, D/IN*7.5)
        self.rect(sid, x+int(D*0.09), y, int(D*0.82), int(D*0.82), line="000000", lw=bw, shape="ELLIPSE")  # 黒い円(輪郭のみ・器より少し細く)
        self.rect(sid, x-int(D*0.08), y+int(D*0.50), int(D*1.16), int(D*0.7), fill=WHITE)   # 下半分を白でマスク→上のドーム(下端をやや下げ隙間を詰める)
        self.rect(sid, x+int(D*0.05), y+int(D*0.52), int(D*0.9), int(D*0.62), fill=RED, shape="ELLIPSE")  # 赤い円(器)
        self.rect(sid, x-int(D*0.08), y+int(D*0.5), int(D*1.16), int(D*0.24), fill=WHITE)   # 赤の上半分を白でマスク→下の半円(上端をやや上げ隙間を詰める)
    def mark(self,sid): self.logo_mark(sid, MX, int(0.33*IN), int(0.27*IN))
    def bg(self,sid,url):  # 全幅背景画像（淡赤グラデ等）を最背面に
        self.reqs.append({"createImage":{"objectId":self._id("bg"),"url":url,
            "elementProperties":{"pageObjectId":sid,
                "size":{"width":{"magnitude":PW,"unit":"EMU"},"height":{"magnitude":PH,"unit":"EMU"}},
                "transform":{"scaleX":1,"scaleY":1,"translateX":0,"translateY":0,"unit":"EMU"}}}})
    def _tokens(self):  # figs_html 用トークン（現在のテーマ）
        return {"RED":RED,"INK":INK,"SUB":SUB,"PANEL":PANEL,"FAINT":FAINT,"RULE":RULE,"BORDER":RULE,
                "LRED":LRED,"CON":"C7BFB9","HEAD":HEAD,"BODY":BODY,"MONO":MONO}
    def diagram(self,kind,kick,title,data,note=None,h=None):
        """汎用ハイブリッド概念図。kind=pyramid/relation/timeline/ladder/before_after/cycle/seating/bar/flow…
        training_v2 のみハイブリッド。それ以外は content にフォールバック（データが箇条なら）。"""
        genkind="quad" if kind=="matrix" else kind
        gen=getattr(FH,genkind+"_html",None)
        if self.hybrid() and gen is not None:
            sid=self.slide(); self.mark(sid); self.kicker(sid,kick); self.head_title(sid,title)
            T=self._tokens()
            if kind in ("relation","before_after","directions"): html=gen(data[0],data[1],T)
            elif kind in ("quad","matrix"): html=FH.quad_html(data[0],data[1],data[2],T)
            elif kind in ("platform","converge","gridmatrix"): html=gen(data[0],data[1],data[2],T)
            elif kind=="formula": html=gen(data[0],data[1],T)
            else: html=gen(data,T)
            y=int(1.66*IN); imgH=self.figimg(sid,html,_FIGH.get(kind,420),y)
            if note: self.text(sid, MX, y+imgH+int(0.1*IN), CW, int(0.42*IN), [(note,{"size":11,"color":SUB,"font":BODY})], valign="MIDDLE")
            self.footer(sid,self.tag); return sid
        # フォールバック: データから箇条書きを抽出して content
        items=[]
        for d in (data if isinstance(data,(list,tuple)) else []):
            if isinstance(d,(list,tuple)) and d: items.append("　".join(str(x) for x in d if x))
            elif d: items.append(str(d))
        return self.content(kick,title,items[:6] or [title],callout=(("要点",note) if note else None))
    def hybrid(self):  # training_v2 かつ uploader 設定済みなら図をHTMLハイブリッド化
        return THEME=="training_v2" and getattr(self,"uploader",None) is not None
    def figimg(self,sid,html,hpx,y):  # HTMLスマート図→PNG→content域に画像挿入。imgH(EMU)を返す
        url=self.uploader(html,1280,hpx); imgH=CW*hpx//1280
        self.reqs.append({"createImage":{"objectId":self._id("fig"),"url":url,
            "elementProperties":{"pageObjectId":sid,
                "size":{"width":{"magnitude":CW,"unit":"EMU"},"height":{"magnitude":imgH,"unit":"EMU"}},
                "transform":{"scaleX":1,"scaleY":1,"translateX":MX,"translateY":y,"unit":"EMU"}}}})
        return imgH
    def kicker(self,sid,text): self.text(sid, MX+int(0.42*IN), int(0.4*IN), CW, int(0.24*IN), [(text,{"size":9,"color":SUB,"bold":True,"font":MONO})], valign="MIDDLE")  # 脱AI：赤→静かなグレーのセクション標
    def head_title(self,sid,title):
        self.text(sid, MX, int(0.72*IN), CW, int(0.62*IN), [(title,{"size":26,"color":INK,"bold":True,"font":HEAD})], valign="MIDDLE", fit=(26,15))
        self.rect(sid, MX, int(1.45*IN), CW, 12700, fill=RULE)  # 脱AI：赤の短い下線→全幅の細グレー罫（装飾でなく構造線）
    def footer(self,sid,tag=None):
        tag=tag or self.tag
        self.rect(sid, MX, PH-int(0.5*IN), CW, 12700, fill=RULE)  # 細い区切り線
        suffix=("  "+FOOTLABEL+" ｜ "+tag) if FOOTLABEL else ("  "+tag)
        self.text(sid, MX, PH-int(0.44*IN), CW-int(1*IN), int(0.3*IN), [("TOKUMORI",{"size":8.5,"color":RED,"bold":True,"font":MONO}),(suffix,{"size":8,"color":SUB,"font":MONO})], valign="MIDDLE")
        self.text(sid, PW-MX-int(1.2*IN), PH-int(0.44*IN), int(1.2*IN), int(0.3*IN), [("%02d"%self.page,{"size":8,"color":SUB,"font":MONO})], align="END", valign="MIDDLE")
    def point_rows(self,sid,y,items,avail,numbered=False,size=13):
        # 利用可能高さ avail を行数で等分し、各行に収まるよう自動縮小（はみ出し・重なり防止）
        # 脱AI：赤丸番号バッジ／赤四角マーカーを撤去 → ink等幅数字＋極細グレー罫／小さなグレーティック
        x=MX; n=max(1,len(items)); rowh=max(int(0.34*IN), avail//n)
        for i,it in enumerate(items):
            if numbered:
                if i>0: self.rect(sid, x, y, CW, 9525, fill=RULE)  # 行間の極細グレー罫（区切り）
                self.text(sid, x, y, int(0.46*IN), rowh, [("%02d"%(i+1),{"size":13,"color":INK,"bold":True,"font":MONO})], valign="MIDDLE")
                tx=x+int(0.56*IN)
            else:
                self.rect(sid, x+int(0.02*IN), y+int(0.12*IN), int(0.1*IN), int(0.1*IN), fill="B8AFA9")  # 小さなグレー角ティック
                tx=x+int(0.32*IN)
            self.text(sid, tx, y, CW-(tx-MX), rowh, [(it,{"size":size,"color":INK,"font":BODY})], valign="MIDDLE", fit=(size,9))
            y+=rowh
        return y
    def callout(self,sid,label,body,kind="point"):
        # 脱AI：淡赤パネル＋赤丸「POINT」バッジを撤去 → 編集的な要点ブロック（赤の細い縦罫＋小さなグレー見出し語＋本文）
        y=int(3.98*IN); h=int(0.8*IN); lc=INK if kind=="ok" else RED
        cap={"POINT":"要点","NG":"注意","OK":"ポイント"}.get(label, label)
        self.rect(sid, MX, y+int(0.03*IN), int(0.026*IN), h-int(0.06*IN), fill=lc)  # 細い縦罫（プルクオート風）
        self.text(sid, MX+int(0.26*IN), y, CW-int(0.3*IN), int(0.24*IN), [(cap,{"size":9,"color":SUB,"bold":True,"font":MONO})], valign="MIDDLE")
        self.text(sid, MX+int(0.26*IN), y+int(0.25*IN), CW-int(0.34*IN), h-int(0.25*IN), [(body,{"size":13.5,"color":INK,"font":BODY})], valign="TOP", fit=(13.5,10))
    # ---- スライド種別 ----
    def cover(self,code,cat,title,subtitle,minutes):
        if THEME=="training_v2":  # クリーン・デジタル（白＋淡赤グラデ＋IBM Plex太ゴシック）
            sid=self.slide()
            if HERO_BG_URL: self.bg(sid, HERO_BG_URL)
            self.mark(sid)
            self.text(sid, MX+int(0.42*IN), int(0.4*IN), CW, int(0.26*IN), [("TOKUMORI 新卒研修 ｜ ONBOARDING",{"size":10,"color":SUB,"bold":True,"font":MONO})], valign="MIDDLE")
            self.text(sid, MX, int(2.0*IN), CW, int(1.2*IN), [(title,{"size":44,"color":INK,"bold":True,"font":HEAD})], valign="MIDDLE", fit=(44,24))
            self.rect(sid, MX, int(3.18*IN), int(1.1*IN), int(0.055*IN), fill=RED)
            self.text(sid, MX, int(3.42*IN), CW, int(0.5*IN), [(subtitle,{"size":16,"color":SUB,"font":BODY})])
            self.text(sid, MX, PH-int(0.66*IN), CW, int(0.3*IN), [("Module %s ・ %s ・ 所要 約%s"%(code,cat,minutes),{"size":10,"color":SUB,"font":MONO})], valign="MIDDLE")
            return sid
        sid=self.slide()
        self.rect(sid, 0, 0, int(0.14*IN), PH, fill=RED)  # 左の赤アクセントレール
        self.text(sid, PW-MX-int(4.2*IN), int(0.25*IN), int(4.2*IN), int(2.2*IN), [(code,{"size":150,"color":FAINT,"bold":True,"font":DISP})], align="END", valign="MIDDLE")  # ゴースト巨大コード(明朝)
        self.mark(sid); self.text(sid, MX+int(0.42*IN), int(0.4*IN), CW, int(0.26*IN), [("TOKUMORI 新卒研修 ｜ ONBOARDING",{"size":10,"color":RED,"bold":True,"font":MONO})], valign="MIDDLE")
        self.text(sid, MX, int(2.0*IN), CW, int(1.3*IN), [(title,{"size":47,"color":INK,"bold":True,"font":DISP})], valign="MIDDLE", fit=(47,26))  # 明朝の大見出し
        self.rect(sid, MX, int(3.22*IN), int(1.3*IN), int(0.06*IN), fill=RED)
        self.text(sid, MX, int(3.44*IN), CW, int(0.5*IN), [(subtitle,{"size":17,"color":SUB,"font":BODY})])
        self.text(sid, MX, PH-int(1.06*IN), CW, int(0.36*IN), [("TOKUMORI",{"size":18,"color":RED,"bold":True,"font":DISP})])
        self.text(sid, MX, PH-int(0.66*IN), CW, int(0.3*IN), [("Module %s ・ %s ・ 所要 約%s"%(code,cat,minutes),{"size":10,"color":SUB,"font":MONO})], valign="MIDDLE")
        return sid
    def divider(self,num,part,title):
        if THEME=="training_v2":  # クリーン・デジタル（白＋淡赤グラデ＋大きなIBM Plex番号(赤)）
            sid=self.slide()
            if HERO_BG_URL: self.bg(sid, HERO_BG_URL)
            self.text(sid, MX, int(0.9*IN), int(4.2*IN), int(2.3*IN), [(num,{"size":150,"color":RED,"bold":True,"font":HEAD})], valign="MIDDLE")  # 大きな番号(赤)
            self.text(sid, MX+int(0.05*IN), int(3.05*IN), CW, int(0.3*IN), [(part,{"size":12,"color":SUB,"bold":True,"font":MONO})])
            self.rect(sid, MX, int(3.4*IN), int(0.9*IN), int(0.05*IN), fill=RED)
            self.text(sid, MX, int(3.5*IN), CW, int(0.9*IN), [(title,{"size":32,"color":INK,"bold":True,"font":HEAD})], fit=(32,18))
            self.text(sid, PW-MX-int(2.4*IN), PH-int(0.66*IN), int(2.4*IN), int(0.3*IN), [("TOKUMORI",{"size":11,"color":SUB,"bold":True,"font":MONO})], align="END", valign="MIDDLE")
            return sid
        sid=self.slide(bg=INKDK)
        self.rect(sid, 0, 0, int(0.14*IN), PH, fill=RED)  # 左の赤レール（カバーと統一）
        self.text(sid, MX, int(0.85*IN), int(4.2*IN), int(2.5*IN), [(num,{"size":150,"color":RED,"bold":True,"font":DISP})], valign="MIDDLE")  # 明朝の巨大番号
        self.text(sid, MX+int(0.05*IN), int(3.05*IN), CW, int(0.3*IN), [(part,{"size":12,"color":ROSE,"bold":True,"font":MONO})])
        self.rect(sid, MX, int(3.4*IN), int(0.9*IN), int(0.045*IN), fill=RED)
        self.text(sid, MX, int(3.5*IN), CW, int(0.9*IN), [(title,{"size":32,"color":WHITE,"bold":True,"font":DISP})], fit=(32,18))  # 明朝の白タイトル
        self.text(sid, PW-MX-int(2.4*IN), PH-int(0.66*IN), int(2.4*IN), int(0.3*IN), [("TOKUMORI",{"size":11,"color":WHITE,"bold":True,"font":DISP})], align="END", valign="MIDDLE")
        return sid
    def content(self,kick,title,items,callout=None,numbered=False,tag=None):
        sid=self.slide(); self.mark(sid); self.kicker(sid,kick); self.head_title(sid,title)
        top=int(1.65*IN); avail=(int(3.8*IN) if callout else int(4.55*IN))-top
        self.point_rows(sid, top, items, avail, numbered=numbered, size=14)
        if callout: self.callout(sid,*callout)
        self.footer(sid,tag); return sid
    def flow(self,kick,title,steps,note,tag=None):
        if self.hybrid():
            sid=self.slide(); self.mark(sid); self.kicker(sid,kick); self.head_title(sid,title)
            y=int(1.75*IN); imgH=self.figimg(sid, FH.flow_html([tuple(s) for s in steps], self._tokens(), H=300), 300, y)
            if note: self.text(sid, MX, y+imgH+int(0.16*IN), CW, int(0.5*IN), [(note,{"size":12,"color":INK,"font":BODY})], valign="MIDDLE")
            self.footer(sid,tag); return sid
        sid=self.slide(); self.mark(sid); self.kicker(sid,kick); self.head_title(sid,title)
        n=len(steps); gap=int(0.18*IN); bw=(CW-gap*(n-1))//n; y=int(1.9*IN); h=int(1.9*IN); x=MX
        for i,(badge,lbl,desc) in enumerate(steps):
            self.rect(sid,x,y,bw,h,fill=PANEL,line=RULE,lw=1,round=True)
            self.rect(sid,x+int(0.2*IN),y+int(0.22*IN),int(0.5*IN),int(0.5*IN),fill=RED,round=True)
            self.text(sid,x+int(0.2*IN),y+int(0.22*IN),int(0.5*IN),int(0.5*IN),[(badge,{"size":18,"color":WHITE,"bold":True,"font":HEAD})],align="CENTER",valign="MIDDLE")
            self.text(sid,x+int(0.2*IN),y+int(0.85*IN),bw-int(0.4*IN),int(0.4*IN),[(lbl,{"size":13,"color":INK,"bold":True,"font":HEAD})],fit=(13,9))
            self.text(sid,x+int(0.2*IN),y+int(1.2*IN),bw-int(0.4*IN),int(0.66*IN),[(desc,{"size":10.5,"color":SUB,"font":BODY})],fit=(10.5,8))
            if i<n-1: self.text(sid,x+bw-int(0.02*IN),y,gap+int(0.1*IN),h,[("›",{"size":22,"color":RED,"bold":True,"font":HEAD})],align="CENTER",valign="MIDDLE")
            x+=bw+gap
        self.text(sid, MX, int(4.05*IN), CW, int(0.6*IN), [(note,{"size":12.5,"color":INK,"font":BODY})], valign="MIDDLE")
        self.footer(sid,tag); return sid
    def compare(self,kick,title,ng,ok,tag=None):
        sid=self.slide(); self.mark(sid); self.kicker(sid,kick); self.head_title(sid,title)
        gap=int(0.3*IN); cw=(CW-gap)//2; y=int(1.7*IN); h=int(2.9*IN)
        for (x,head,items,c,glyph) in [(MX,ng[0],ng[1],RED,"✕"),(MX+cw+gap,ok[0],ok[1],GREEN,"○")]:
            self.rect(sid,x,y,cw,h,fill=WHITE,line=c,lw=1.5,round=True)
            self.rect(sid,x,y,cw,int(0.52*IN),fill=c,round=True)
            self.text(sid,x+int(0.2*IN),y,cw-int(0.4*IN),int(0.52*IN),[(glyph+"  "+head,{"size":13,"color":WHITE,"bold":True,"font":HEAD})],valign="MIDDLE",fit=(13,9))
            yy=y+int(0.7*IN)
            for it in items:
                self.rect(sid,x+int(0.22*IN),yy+int(0.07*IN),int(0.1*IN),int(0.1*IN),fill=c)
                self.text(sid,x+int(0.42*IN),yy,cw-int(0.62*IN),int(0.46*IN),[(it,{"size":11.5,"color":INK,"font":BODY})],valign="MIDDLE",fit=(11.5,8.5))
                yy+=int(0.5*IN)
        self.footer(sid,tag); return sid
    def work(self,kick,title,prompt,situation,hint,tag=None):
        sid=self.slide(); self.mark(sid); self.kicker(sid,kick); self.head_title(sid,title)
        self.rect(sid, MX, int(1.7*IN), CW, int(2.85*IN), fill=PANEL, line=RULE, lw=1, round=True)
        self.rect(sid, MX+int(0.3*IN), int(1.95*IN), int(1.5*IN), int(0.45*IN), fill=RED, round=True)
        self.text(sid, MX+int(0.3*IN), int(1.95*IN), int(1.5*IN), int(0.45*IN), [("WORK",{"size":12,"color":WHITE,"bold":True,"font":MONO})], align="CENTER", valign="MIDDLE")
        self.text(sid, MX+int(0.35*IN), int(2.55*IN), CW-int(0.7*IN), int(0.55*IN), [(prompt,{"size":16,"color":INK,"bold":True,"font":HEAD})])
        self.text(sid, MX+int(0.35*IN), int(3.15*IN), CW-int(0.7*IN), int(0.9*IN), [("状況  ",{"size":12,"color":RED,"bold":True,"font":BODY}),(situation,{"size":12.5,"color":INK,"font":BODY})])
        self.text(sid, MX+int(0.35*IN), int(4.1*IN), CW-int(0.7*IN), int(0.4*IN), [("ヒント  ",{"size":11,"color":SUB,"bold":True,"font":BODY}),(hint,{"size":11,"color":SUB,"font":BODY})])
        self.footer(sid,tag); return sid
    def checklist(self,kick,title,items,tag=None):
        sid=self.slide(); self.mark(sid); self.kicker(sid,kick); self.head_title(sid,title)
        y=int(1.75*IN)
        for it in items:
            self.rect(sid, MX, y+int(0.02*IN), int(0.26*IN), int(0.26*IN), fill=WHITE, line=RED, lw=1.6, round=True)
            self.text(sid, MX+int(0.46*IN), y, CW-int(0.46*IN), int(0.45*IN), [(it,{"size":14,"color":INK,"font":BODY})], valign="MIDDLE")
            y+=int(0.62*IN)
        self.footer(sid,tag); return sid
    def closing(self,kick,title,items,link_label,link_url,tag=None,link_kind="参考動画"):
        sid=self.slide(); self.mark(sid); self.kicker(sid,kick); self.head_title(sid,title)
        self.point_rows(sid, int(1.65*IN), items, int(3.75*IN)-int(1.65*IN), size=14)
        self.rect(sid, MX, int(3.9*IN), CW, int(0.82*IN), fill=LRED, round=True); self.rect(sid, MX, int(3.9*IN), int(0.08*IN), int(0.82*IN), fill=RED)
        self.text(sid, MX+int(0.28*IN), int(3.9*IN), CW-int(0.56*IN), int(0.82*IN),
                  [(link_kind+"  ",{"size":12,"color":RED,"bold":True,"font":BODY}),(link_label+"   ",{"size":12,"color":INK,"font":BODY}),(link_url,{"size":10.5,"color":LINKC,"font":MONO})], valign="MIDDLE")
        self.footer(sid,tag); return sid
    def radial(self,kick,title,center,roles,note,tag=None):
        sid=self.slide(); self.mark(sid); self.kicker(sid,kick); self.head_title(sid,title)
        cx=PW//2; cy=int(2.8*IN); rx=int(2.95*IN); ry=int(1.32*IN); bw=int(1.75*IN); bh=int(0.5*IN); n=len(roles)
        for i,role in enumerate(roles):
            ang=math.pi/2 - i*(2*math.pi/max(1,n))
            x=cx+int(rx*math.cos(ang))-bw//2; y=cy-int(ry*math.sin(ang))-bh//2
            self.rect(sid,x,y,bw,bh,fill=PANEL,line=RULE,lw=1,round=True)
            self.text(sid,x,y,bw,bh,[(role,{"size":10,"color":INK,"bold":True,"font":HEAD})],align="CENTER",valign="MIDDLE")
        cw=int(1.7*IN); ch=int(0.95*IN)
        self.rect(sid,cx-cw//2,cy-ch//2,cw,ch,fill=RED,round=True)
        self.text(sid,cx-cw//2,cy-ch//2,cw,ch,[(center,{"size":13,"color":WHITE,"bold":True,"font":HEAD})],align="CENTER",valign="MIDDLE")
        self.text(sid,MX,PH-int(0.96*IN),CW,int(0.4*IN),[(note,{"size":11,"color":INK,"font":BODY})],align="CENTER",valign="MIDDLE")
        self.footer(sid,tag); return sid
    def seating(self,kick,title,seats,note,door="入口",tag=None):
        if self.hybrid():
            sid=self.slide(); self.mark(sid); self.kicker(sid,kick); self.head_title(sid,title)
            y=int(1.66*IN); imgH=self.figimg(sid, FH.seating_html([tuple(s) for s in seats], self._tokens(), door=door, H=430), 430, y)
            if note: self.text(sid, MX, y+imgH+int(0.08*IN), CW, int(0.4*IN), [(note,{"size":11,"color":INK,"font":BODY})], align="CENTER", valign="MIDDLE")
            self.footer(sid,tag); return sid
        sid=self.slide(); self.mark(sid); self.kicker(sid,kick); self.head_title(sid,title)
        rw=int(5.4*IN); rh=int(2.45*IN); rx=PW//2-rw//2; ry=int(1.7*IN)
        self.rect(sid,rx,ry,rw,rh,fill=PANEL,line=INK,lw=1.2,round=True)
        self.rect(sid,PW//2-int(0.75*IN),ry+rh-int(0.12*IN),int(1.5*IN),int(0.3*IN),fill=INK,round=True)
        self.text(sid,PW//2-int(0.75*IN),ry+rh-int(0.12*IN),int(1.5*IN),int(0.3*IN),[(door,{"size":10,"color":WHITE,"bold":True,"font":HEAD})],align="CENTER",valign="MIDDLE")
        sw=int(1.5*IN); sh=int(0.6*IN)
        for (label,nx,ny,top) in seats:
            x=rx+int(nx*rw)-sw//2; y=ry+int(ny*rh)-sh//2
            self.rect(sid,x,y,sw,sh,fill=(LRED if top else WHITE),line=(RED if top else "BFBFBF"),lw=(1.6 if top else 1),round=True)
            self.text(sid,x,y,sw,sh,[(label,{"size":10.5,"color":(RED if top else INK),"bold":True,"font":HEAD})],align="CENTER",valign="MIDDLE")
        self.text(sid,MX,PH-int(0.95*IN),CW,int(0.42*IN),[(note,{"size":11,"color":INK,"font":BODY})],align="CENTER",valign="MIDDLE")
        self.footer(sid,tag); return sid
    def barchart(self,kick,title,items,note,tag=None):
        """items=[(label, frac0_1, valtext, highlight)] 横棒グラフ。"""
        if self.hybrid():
            sid=self.slide(); self.mark(sid); self.kicker(sid,kick); self.head_title(sid,title)
            y=int(1.7*IN); imgH=self.figimg(sid, FH.bar_html([tuple(it) for it in items], self._tokens(), H=380), 380, y)
            if note: self.text(sid, MX, y+imgH+int(0.14*IN), CW, int(0.42*IN), [(note,{"size":10.5,"color":SUB,"font":BODY})], valign="MIDDLE")
            self.footer(sid,tag); return sid
        sid=self.slide(); self.mark(sid); self.kicker(sid,kick); self.head_title(sid,title)
        n=len(items); top=int(1.85*IN); avail=int(2.7*IN)
        step=min(int(0.6*IN), avail//max(1,n)); bh=min(int(0.36*IN), step-int(0.12*IN))
        labw=int(2.1*IN); barx=MX+labw; barmax=CW-labw-int(1.4*IN)
        for i,(label,frac,val,hi) in enumerate(items):
            y=top+i*step
            self.text(sid,MX,y,labw-int(0.12*IN),bh,[(label,{"size":11,"color":(RED if hi else INK),"bold":True,"font":HEAD})],valign="MIDDLE")
            self.rect(sid,barx,y+int(0.03*IN),barmax,bh-int(0.06*IN),fill=PANEL,round=True)
            w=max(int(0.05*IN),int(barmax*max(0.0,min(1.0,frac))))
            self.rect(sid,barx,y+int(0.03*IN),w,bh-int(0.06*IN),fill=(RED if hi else "C8B7B3"),round=True)
            self.text(sid,barx+w+int(0.12*IN),y,int(1.4*IN),bh,[(val,{"size":10.5,"color":(RED if hi else SUB),"bold":True,"font":MONO})],valign="MIDDLE")
        if note: self.text(sid,MX,PH-int(0.95*IN),CW,int(0.42*IN),[(note,{"size":10.5,"color":SUB,"font":BODY})],valign="MIDDLE")
        self.footer(sid,tag); return sid
    def statcards(self,kick,title,stats,note=None,tag=None):
        """stats=[(大数値, ラベル, 出典/補足?)] 大きな数字を並べたインフォグラフィック。"""
        sid=self.slide(); self.mark(sid); self.kicker(sid,kick); self.head_title(sid,title)
        n=len(stats); gap=int(0.22*IN); cw=(CW-gap*(n-1))//n; y=int(1.95*IN); h=int(2.05*IN); x=MX
        bs=min(self.fit_size(s[0],cw-int(0.2*IN),int(0.85*IN),36,20) for s in stats)  # 大数値は全カード統一サイズ
        for s in stats:
            big=s[0]; lab=s[1]; sub=s[2] if len(s)>2 else ""
            self.rect(sid,x,y,cw,h,fill=PANEL,line=RULE,lw=1,round=True)
            self.rect(sid,x,y,cw,int(0.08*IN),fill=RED,round=True)
            self.text(sid,x,y+int(0.34*IN),cw,int(0.85*IN),[(big,{"size":bs,"color":RED,"bold":True,"font":DISP})],align="CENTER",valign="MIDDLE")
            self.text(sid,x+int(0.14*IN),y+int(1.32*IN),cw-int(0.28*IN),int(0.5*IN),[(lab,{"size":12.5,"color":INK,"bold":True,"font":HEAD})],align="CENTER",valign="TOP",fit=(12.5,9))
            if sub: self.text(sid,x+int(0.14*IN),y+int(1.74*IN),cw-int(0.28*IN),int(0.28*IN),[(sub,{"size":9,"color":SUB,"font":MONO})],align="CENTER",fit=(9,7))
            x+=cw+gap
        if note: self.text(sid,MX,PH-int(0.95*IN),CW,int(0.42*IN),[(note,{"size":10.5,"color":SUB,"font":BODY})],valign="MIDDLE")
        self.footer(sid,tag); return sid
    def cards(self,kick,title,items,note=None,tag=None):
        """items=[(見出し, サブ?, 説明)] 概念カードを横並び（左に赤アクセント）。"""
        sid=self.slide(); self.mark(sid); self.kicker(sid,kick); self.head_title(sid,title)
        n=len(items); gap=int(0.22*IN); cw=(CW-gap*(n-1))//n; y=int(1.9*IN); h=int(2.4*IN); x=MX
        for it in items:
            head=it[0]; hassub=len(it)>2; sub=it[1] if hassub else ""; desc=it[-1]
            self.rect(sid,x,y,cw,h,fill=WHITE,line=RULE,lw=1.2,round=True)
            self.rect(sid,x,y,int(0.08*IN),h,fill=RED)
            self.text(sid,x+int(0.28*IN),y+int(0.26*IN),cw-int(0.42*IN),int(0.5*IN),[(head,{"size":17,"color":INK,"bold":True,"font":HEAD})],fit=(17,12))
            if hassub: self.text(sid,x+int(0.28*IN),y+int(0.8*IN),cw-int(0.42*IN),int(0.3*IN),[(sub,{"size":10,"color":RED,"bold":True,"font":MONO})],fit=(10,8))
            self.text(sid,x+int(0.28*IN),y+int(1.16*IN),cw-int(0.5*IN),h-int(1.34*IN),[(desc,{"size":11.5,"color":INK,"font":BODY})],valign="TOP",spacing=128,fit=(11.5,9))
            x+=cw+gap
        if note: self.text(sid,MX,PH-int(0.95*IN),CW,int(0.42*IN),[(note,{"size":10.5,"color":SUB,"font":BODY})],valign="MIDDLE")
        self.footer(sid,tag); return sid
    def _seg(self,sid,x1,y1,x2,y2,color=INK,w=1.6):
        X=min(x1,x2); Y=min(y1,y2); W=max(1,abs(x2-x1)); H=max(1,abs(y2-y1))
        oid=self._id("ln")
        if (x2-x1)*(y2-y1)>=0:
            tf={"scaleX":1,"scaleY":1,"translateX":X,"translateY":Y,"unit":"EMU"}
        else:
            tf={"scaleX":1,"scaleY":-1,"translateX":X,"translateY":Y+H,"unit":"EMU"}
        self.reqs.append({"createLine":{"objectId":oid,"category":"STRAIGHT",
            "elementProperties":{"pageObjectId":sid,"size":{"width":{"magnitude":W,"unit":"EMU"},"height":{"magnitude":H,"unit":"EMU"}},"transform":tf}}})
        self.reqs.append({"updateLineProperties":{"objectId":oid,"lineProperties":{"lineFill":{"solidFill":{"color":{"rgbColor":rf(color)}}},"weight":{"magnitude":w,"unit":"PT"}},"fields":"lineFill,weight"}})
        return oid
    def linechart(self,kick,title,xlabels,series,note,tag=None,smooth=True,dots=True,ylab=None):
        """xlabels=[..n..]; series=[{name,ys:[0-1]*n,vals:[str]*n|None,hi:bool}] 滑らかな折れ線グラフ。
        ylab=(縦軸名, 上ラベル, 下ラベル) を渡すとy軸注記を描画。"""
        if self.hybrid():
            sid=self.slide(); self.mark(sid); self.kicker(sid,kick); self.head_title(sid,title)
            y=int(1.7*IN); imgH=self.figimg(sid, FH.line_html(list(xlabels), [dict(s) for s in series], self._tokens(), ylab=ylab, H=370), 370, y)
            if note: self.text(sid, MX, y+imgH+int(0.12*IN), CW, int(0.42*IN), [(note,{"size":10.5,"color":SUB,"font":BODY})], valign="MIDDLE")
            self.footer(sid,tag); return sid
        sid=self.slide(); self.mark(sid); self.kicker(sid,kick); self.head_title(sid,title)
        n=len(xlabels)
        plx=MX+int(0.55*IN); ply=int(2.05*IN); plw=CW-int(1.0*IN); plh=int(2.2*IN)
        dx=plw//max(1,(n-1)); xs=[plx+i*dx for i in range(n)]
        self.rect(sid,plx,ply+plh,plw,int(0.012*IN),fill="BFBFBF")
        self.rect(sid,plx,ply,int(0.012*IN),plh,fill="BFBFBF")
        def yp(v): v=max(0.0,min(1.0,float(v))); return ply+int((1-v)*plh)
        if ylab:
            self.text(sid,MX-int(0.05*IN),ply+plh//2-int(0.2*IN),int(0.5*IN),int(0.4*IN),[(ylab[0],{"size":10,"color":INK,"bold":True,"font":HEAD})],align="CENTER",valign="MIDDLE")
            self.text(sid,plx-int(0.55*IN),ply-int(0.05*IN),int(0.5*IN),int(0.22*IN),[(ylab[1],{"size":8.5,"color":SUB,"font":BODY})],align="CENTER")
            self.text(sid,plx-int(0.55*IN),ply+plh-int(0.18*IN),int(0.5*IN),int(0.22*IN),[(ylab[2],{"size":8.5,"color":SUB,"font":BODY})],align="CENTER")
        multi=len(series)>1; steps=(8 if multi else 16)
        def cr(p0,p1,p2,p3,t): return 0.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t)
        def dense(ys):
            if n<3 or not smooth: return [(xs[i],yp(ys[i])) for i in range(n)]
            out=[]
            for i in range(n-1):
                p0=ys[i-1] if i>0 else ys[i]; p1=ys[i]; p2=ys[i+1]; p3=ys[i+2] if i+2<n else ys[i+1]
                for k in range(steps+(1 if i==n-2 else 0)):
                    t=k/steps
                    out.append((int(xs[i]+(xs[i+1]-xs[i])*t), yp(cr(p0,p1,p2,p3,t))))
            return out
        for s in series:
            col=RED if s.get("hi") else "B0A09C"; ys=s["ys"]; vals=s.get("vals")
            dp=dense(ys)
            for i in range(len(dp)-1):
                self._seg(sid,dp[i][0],dp[i][1],dp[i+1][0],dp[i+1][1],color=col,w=(2.6 if s.get("hi") else 1.7))
            r=int(0.05*IN)
            for i in range(n):
                px,py=xs[i],yp(ys[i])
                if dots: self.rect(sid,px-r,py-r,2*r,2*r,fill=col,shape="ELLIPSE")
                if vals and i<len(vals) and vals[i] and (s.get("hi") or not multi):
                    self.text(sid,px-int(0.85*IN),py-int(0.4*IN),int(1.7*IN),int(0.26*IN),[(vals[i],{"size":10,"color":col,"bold":True,"font":HEAD})],align="CENTER")
        for i,px in enumerate(xs):
            if not xlabels[i]: continue
            self.text(sid,px-int(0.75*IN),ply+plh+int(0.05*IN),int(1.5*IN),int(0.3*IN),[(xlabels[i],{"size":9,"color":SUB,"font":BODY})],align="CENTER")
        if multi:
            lx=plx+int(0.1*IN); ly=ply-int(0.36*IN)
            for s in series:
                col=RED if s.get("hi") else "B0A09C"
                self.rect(sid,lx,ly+int(0.05*IN),int(0.3*IN),int(0.07*IN),fill=col,round=True)
                nm=s.get("name",""); w=int(0.135*IN)*len(nm)+int(0.2*IN)
                self.text(sid,lx+int(0.36*IN),ly,w,int(0.24*IN),[(nm,{"size":9.5,"color":INK,"bold":True,"font":HEAD})],valign="MIDDLE")
                lx+=int(0.42*IN)+w
        if note: self.text(sid,MX,PH-int(0.92*IN),CW,int(0.4*IN),[(note,{"size":10.5,"color":SUB,"font":BODY})],valign="MIDDLE")
        self.footer(sid,tag); return sid
    def quadrant(self,kick,title,xlab,ylab,quads,note,tag=None):
        """quads=[(head,desc,hi)] を TL,TR,BL,BR の順で。2×2マトリクス。"""
        if self.hybrid():
            sid=self.slide(); self.mark(sid); self.kicker(sid,kick); self.head_title(sid,title)
            y=int(1.62*IN); imgH=self.figimg(sid, FH.quad_html(xlab,ylab,[tuple(q) for q in quads], self._tokens(), H=420), 420, y)
            if note: self.text(sid, MX, y+imgH+int(0.1*IN), CW, int(0.38*IN), [(note,{"size":10.5,"color":SUB,"font":BODY})], valign="MIDDLE")
            self.footer(sid,tag); return sid
        sid=self.slide(); self.mark(sid); self.kicker(sid,kick); self.head_title(sid,title)
        gx=MX+int(0.45*IN); gy=int(2.0*IN); gw=CW-int(0.9*IN); gh=int(2.55*IN)
        cw=gw//2; ch=gh//2; cells=[(gx,gy),(gx+cw,gy),(gx,gy+ch),(gx+cw,gy+ch)]
        for idx,(hx,hy) in enumerate(cells):
            head,desc,h=quads[idx]
            self.rect(sid,hx+int(0.04*IN),hy+int(0.04*IN),cw-int(0.08*IN),ch-int(0.08*IN),fill=(LRED if h else PANEL),line=(RED if h else RULE),lw=1.2,round=True)
            self.text(sid,hx+int(0.2*IN),hy+int(0.16*IN),cw-int(0.4*IN),int(0.42*IN),[(head,{"size":12,"color":(RED if h else INK),"bold":True,"font":HEAD})])
            self.text(sid,hx+int(0.2*IN),hy+int(0.62*IN),cw-int(0.4*IN),ch-int(0.74*IN),[(desc,{"size":9.5,"color":INK,"font":BODY})])
        self.text(sid,gx,gy-int(0.3*IN),gw,int(0.24*IN),[(ylab,{"size":9.5,"color":SUB,"bold":True,"font":MONO})],align="CENTER")
        self.text(sid,gx,gy+gh+int(0.05*IN),gw,int(0.24*IN),[(xlab,{"size":9.5,"color":SUB,"bold":True,"font":MONO})],align="CENTER")
        if note: self.text(sid,MX,PH-int(0.9*IN),CW,int(0.38*IN),[(note,{"size":10.5,"color":SUB,"font":BODY})],valign="MIDDLE")
        self.footer(sid,tag); return sid
    def deepen(self):
        """ENRICH[mid] のリサーチ深掘りスライド（content/compare/barchart）を描画。"""
        mid=(self.tag or "").split()[0] if self.tag else ""
        pack=ENRICH.get(mid) or []
        if not pack: return
        self.divider("＋","DEEP DIVE","深掘り（リサーチ・実データ）")
        for s in pack:
            try:
                k=s.get("kind","content")
                if k=="compare":
                    self.compare(s.get("kick","CASE ・ 比較"),s.get("title",""),
                                 (s["ng"][0],list(s["ng"][1])[:5]),(s["ok"][0],list(s["ok"][1])[:5]))
                elif k=="barchart":
                    bars=[(b[0],float(b[1]),b[2],bool(b[3])) for b in s.get("bars",[])][:6]
                    self.barchart(s.get("kick","DATA ・ 図解"),s.get("title",""),bars,s.get("note",""))
                elif k=="linechart":
                    self.linechart(s.get("kick","DATA ・ 図解"),s.get("title",""),
                                   list(s.get("xlabels",[])),list(s.get("series",[])),s.get("note",""))
                else:
                    co=s.get("callout")
                    self.content(s.get("kick","DEEP ・ ポイント"),s.get("title",""),
                                 list(s.get("bullets",[]))[:5],
                                 callout=(tuple(co) if co else None))
            except Exception:
                continue


def build_hourenso(dk):
    dk.tag="B2 報連相"
    dk.cover("B2","ビジネス基礎","報連相","ホウ・レン・ソウ ― 信頼される仕事の土台","1時間")
    dk.content("GOAL ・ このモジュールのゴール","読み終えたらできること",[
        "報告・連絡・相談の違いと使い分けを、自分の言葉で説明できる",
        "「結論ファースト（PREP）」で30秒で簡潔に伝えられる",
        "“即報告すべき場面”を判断し、正しいタイミングで動ける",
    ], numbered=True, callout=("POINT","報連相は“自分のため”ではなく、チームの判断を速くするための共通言語。"))
    dk.divider("01","PART 1","報連相の3要素")
    dk.diagram("relation","WHAT ・ 報連相とは","3つの役割を押さえる",
        ("報連相",["報告","連絡","相談"]),
        note="報告＝経過・結果を上司へ／連絡＝決定事項を関係者へ／相談＝迷ったら早めに。「誰に・何を・いつ」をセットで。")
    dk.content("① REPORT ・ 報告のコツ","結論から、事実と意見を分けて",[
        "結論から伝える（結果 → 経緯の順）",
        "事実と意見（推測）を分けて話す",
        "仕事は“依頼者のもの”。完了・中間・トラブルで必ず報告する",
        "長い仕事は、途中の「中間報告」で相手に安心を渡す",
    ], callout=("POINT","終わったらすぐ。聞かれる前に報告するのがプロ。"))
    dk.content("② CONTACT ・ 連絡のコツ","漏れなく・簡潔に・記録に残す",[
        "関係者“全員”に、漏れなく届ける",
        "結論・要点を簡潔に（5W1Hで過不足なく）",
        "口頭だけで終わらせず、チャット／メールで記録に残す",
    ])
    dk.content("③ CONSULT ・ 相談のコツ","早めに・自分の案を持って",[
        "早めに相談する（手遅れになる前に）",
        "自分の案を持って相談する（丸投げしない）",
        "最初に「何を相談したいか」を一言で伝える",
    ], callout=("POINT","相談は“弱さ”ではなく、事故を防ぐ“強さ”。"))
    dk.divider("02","PART 2","伝え方の型と実践")
    dk.flow("FRAMEWORK ・ 結論ファーストの型","PREP法で組み立てる",[
        ("P","結論","まず結論を一言で"),("R","理由","なぜそうなのか"),
        ("E","具体例","事実・数字で裏づけ"),("P","結論","もう一度結論／次の依頼で締める"),
    ], "迷ったら PREP。話す前に頭の中でこの順に並べてから口を開く。")
    dk.compare("CASE ・ 悪い例 vs 良い例","30秒報告で差が出る",
        ("経緯から長く、結論が見えない",["「えーと、A社の件なんですが…」","昨日電話して、担当者が不在で…","折り返しがまだ来ていなくて…","→ 何が言いたいのか伝わらない"]),
        ("結論ファーストで“次の一手”まで",["「A社の件、まだ返答待ちです」（結論）","昨日連絡し担当者が不在でした（理由）","明日午前に再連絡します（次の一手）","→ 30秒で状況と次が分かる"]))
    dk.content("WHEN ・ 即、報告すべき場面","迷ったら報告、が正解",[
        "ミス・トラブル・クレーム（隠さず、すぐに）",
        "納期や予定に遅れが出そうなとき",
        "指示や前提が途中で変わったとき",
        "自分だけでは判断・決定できないとき",
    ], callout=("NG","悪い情報ほど早く。遅い報告は信頼を失う最大の原因。"))
    dk.content("TOOL ・ チャット(Slack)での報連相","オンラインでも結論ファースト",[
        "結論を先頭に。長文は「要点 → 詳細」の順で書く",
        "関係者は @メンション、話題は1スレッドにまとめる",
        "依頼は「相手・期限・お願いしたいこと」を明確に",
        "詳しい使い方はモジュール C5「Slackの使い方」へ",
    ])
    dk.work("WORK ・ 演習","30秒で報告してみよう","次の状況を“結論ファースト(PREP)”で報告して",
        "担当する求職者が、面接当日に体調不良で来られないと連絡。企業との面接は1時間後に迫っている。",
        "結論（どうなった／どうしたい）→ 理由 → 次の一手、の順で。")
    dk.deepen()
    dk.checklist("CHECK ・ 到達チェック","このモジュールの合格ライン",[
        "報告・連絡・相談を場面に応じて使い分けられる",
        "結論ファースト（PREP）で簡潔に話せる",
        "悪い情報を、すぐ・正しい相手に報告できる",
        "Slackで要点を先頭に、関係者へ漏れなく連絡できる",
    ])
    dk.closing("NEXT ・ まとめ／次のステップ","小さく・早く、が信頼をつくる",[
        "報連相は“信頼の通貨”。小さく・早く、が基本",
        "型に迷ったら PREP（結論→理由→具体例→結論）",
        "次モジュール：B3 ビジネスメール ／ B5 議事録",
    ], "一流の議事録・報連相（YouTube教材タブ参照）","youtube.com/@youseful")


def build_manner(dk):
    dk.tag="B1 ビジネスマナー"
    dk.cover("B1","ビジネス基礎","ビジネスマナー","第一印象と型で“信頼される人”になる","1.5時間")
    dk.content("GOAL ・ このモジュールのゴール","読み終えたらできること",[
        "身だしなみ・挨拶・お辞儀を場面別に実演できる","“よくある間違い敬語”を正しく言い換えられる","名刺交換・席次（会議室／応接室／乗り物）を実演・説明できる",
    ], numbered=True, callout=("POINT","マナーは“相手への敬意”の型。型を知れば緊張せず動ける。"))
    dk.divider("01","PART 1","第一印象をつくる")
    dk.content("① 身だしなみ","“おしゃれ”より“清潔感”",[
        "髪：寝ぐせ・伸びすぎNG、顔まわりをすっきり","服：体に合うサイズ・シワ／汚れ／ほつれを点検・落ち着いた色","足元：靴を磨く・かかと、爪は短く清潔に","強い香水・派手な装飾・露出は避ける（相手に集中してもらう）",
    ], callout=("POINT","第一印象は数秒で決まり、後から覆すのは難しい。準備で勝つ。"))
    dk.content("② 挨拶・お辞儀","自分から先に・止まって・体を向ける",[
        "明るい声で“自分から先に”・相手の目を見て","会釈15度（すれ違い）／敬礼30度（来客・訪問）／最敬礼45度（お詫び・お礼）","語先後礼：言葉を言い切ってから礼をする（同時にしない）","お詫び・お礼は最敬礼で2〜3秒静止し、気持ちを込める",
    ], callout=("NG","歩きながらの“ながら挨拶”は失礼。一度止まり、相手に正対する。"))
    dk.divider("02","PART 2","敬語を“正しく”使う")
    dk.content("③ 敬語の3種類と呼称","立てる・下げる・整える",[
        "尊敬語＝相手を立てる：おっしゃる／いらっしゃる／なさる","謙譲語＝自分を下げる：申す／伺う／拝見する／いたす","丁寧語＝です・ます調で整える","会社の呼称：自社＝弊社・当社／相手＝御社（話）・貴社（書）",
    ], callout=("POINT","迷ったら“丁寧語＋クッション言葉”で安全側に倒す。"))
    dk.compare("CHECK ・ よくある間違い①","二重敬語（敬語の重ねすぎ）",
        ("✕ つい言いがち",["おっしゃられる","ご覧になられる","拝見させていただきました","お伺いさせていただきます"]),
        ("○ 正しくは",["おっしゃる","ご覧になる","拝見しました","伺います"]))
    dk.compare("CHECK ・ よくある間違い②","バイト敬語・社会人の誤用",
        ("✕ つい言いがち",["よろしかったでしょうか","了解しました（目上に）","ご苦労様です（目上に）","すいません"]),
        ("○ 正しくは",["よろしいでしょうか","承知しました／かしこまりました","お疲れ様です","申し訳ございません／恐れ入ります"]))
    dk.content("もう一歩：呼称と言い回しの誤り","知っていると一段上に",[
        "“〜になります”（説明・提示）→ “〜でございます／〜です”","“とんでもございません”→ “とんでもないことです／恐れ入ります”","“させていただきます”の乱用 → 基本は“いたします”","身内（自社の上司）を社外に言う時は敬称を付けない（×部長の田中さんは…→○田中は…）",
    ], callout=("POINT","敬語は“1動作に1つ”。重ねるほど逆に失礼で幼く見える。"))
    dk.content("クッション言葉・依頼／お詫び","同じ内容でも印象が激変する",[
        "依頼：恐れ入りますが／お手数ですが＋“〜していただけますか？”","断り：申し訳ございませんが／あいにく〜","確認：差し支えなければ／よろしければ","お詫び：謝罪＋事実＋今後の対応をセットで（言い訳から入らない）",
    ], callout=("POINT","命令形を避け、クッション言葉＋依頼形にするだけで角が立たない。"))
    dk.divider("03","PART 3","名刺交換と席次")
    dk.flow("FLOW ・ 名刺交換","流れを体で覚える",[
        ("1","立ち上がる","机越しにしない・名刺入れを準備"),("2","名乗る","会社名→部署→氏名を名乗りながら"),
        ("3","両手で渡す","相手の名刺より低い位置で・字を相手向きに"),("4","受けて置く","名刺入れの上に置き、商談中は出しておく"),
    ], "目下（訪問した側）から先に出す。同時交換は右手で渡し左手で受ける。")
    dk.seating("席次①","会議室の席次（図で覚える）",
        [("①上座",0.28,0.30,True),("②",0.50,0.30,True),("③",0.72,0.30,True),
         ("④",0.28,0.72,False),("⑤",0.50,0.72,False),("⑥下座",0.72,0.72,False)],
        "入口から最も遠い列が上座（①〜③）。入口に近いほど下座。お客様・目上を奥へ。","入口")
    dk.seating("席次②","応接室（ソファ）の席次",
        [("①上座 長椅子",0.36,0.30,True),("② 長椅子",0.60,0.30,True),
         ("③ 一人掛け",0.36,0.72,False),("④下座 一人掛け",0.60,0.72,False)],
        "長椅子（ソファ）が上座、一人掛け（肘掛け椅子）が下座。入口から遠い側へお客様を通す。","入口")
    dk.seating("席次③","エレベーターの席次（図で覚える）",
        [("①上座",0.30,0.30,True),("②",0.70,0.30,False),
         ("③",0.30,0.72,False),("④下座（操作盤前）",0.70,0.72,False)],
        "操作盤の前が下座（操作役）。扉から見て奥が上座。乗るときは上司・お客様を先に通す。","扉・操作盤")
    dk.seating("席次④ ・ 乗り物","タクシーの席次（運転手＝他人の場合）",
        [("運転席",0.30,0.28,False),("助手席 ④下座",0.70,0.28,False),
         ("① 上座",0.30,0.72,True),("③ 中央",0.50,0.72,False),("②",0.70,0.72,False)],
        "運転席の後ろが①上座。助手席は支払い・道案内をする最下座(④)。後部中央③は足元が狭く下位。", door="")
    dk.content("その他の乗り物（車・新幹線）","“操作・支払いをする人＝下座”",[
        "社用車（上司・身内が運転）：助手席が上座（運転手の隣で会話）","新幹線：進行方向の窓側が上座、通路側が下座","新幹線3列：窓＞通路＞中央 の順","身内運転＝助手席が上座、と公共交通とは逆になる",
    ], callout=("POINT","公共交通＝運転手の後ろが上座。身内運転＝助手席が上座、と逆になる。"))
    dk.content("難しいケース・例外","迷ったら“相手を立て、安全を優先”",[
        "エレベーター：「お先にどうぞ」と上司・お客様を先に乗せ、自分は操作盤前へ（降りるときも相手が先）","お客様が下座を固辞 → 一度きちんと勧め、固辞されたら従い感謝を伝える","円卓・対面で複数：入口から最も遠い席が上座、あとは交互に座る","諸説ある場面は“型”に固執せず、相手の希望と安全を最優先にする",
    ], callout=("POINT","席次の目的は“相手への敬意”。形式より、相手が心地よいかで判断する。"))
    dk.content("来客・訪問の基本","迎える・訪ねる所作",[
        "来客：笑顔で迎え、斜め前を歩いて案内し上座へ通す","訪問：約束の5分前に到着・受付で社名／氏名／用件／アポ有無","入室：ノック3回・「失礼します」・勧められてから着席","コートは建物に入る前に脱ぐ／携帯はマナーモード",
    ])
    dk.work("WORK ・ 演習","型を体で覚える","①2人1組で 立ち上がり→名乗り→名刺交換→着席 を通しで（あなたは訪問側＝先に出す）","②次を正しい敬語に直す：『資料をご覧になられましたか？』『了解しました』『ご苦労様です』","会議室の図で①〜⑥の上座・下座を指させるか確認する")
    dk.deepen()
    dk.checklist("CHECK ・ 到達チェック","合格ライン",[
        "清潔感ある身だしなみを自分で点検できる","場面に応じたお辞儀（15／30／45度）ができる","二重敬語・バイト敬語を正しく言い換えられる","名刺交換と席次（会議室／応接室／乗り物）を実演・説明できる",
    ])
    dk.closing("NEXT ・ まとめ","型があるから、緊張しない",[
        "マナー＝相手への敬意の“型”","敬語は1動作1つ・クッション言葉＋依頼形","次：B2 報連相 ／ B3 ビジネスメール",
    ], "ビジネスマナー／名刺交換（YouTube教材タブ参照）","youtube.com/@yamazakura")

def build_phone(dk):
    dk.tag="B4 電話応対"
    dk.cover("B4","ビジネス基礎","電話応対","会社の“顔”として落ち着いて対応する","1時間")
    dk.content("GOAL ・ このモジュールのゴール","読み終えたらできること",[
        "3コール以内・正しい第一声で受けられる","取次ぎ・伝言を正確にできる","クレームの一次対応の型がわかる",
    ], numbered=True, callout=("POINT","電話はあなた＝会社。声だけで印象が決まる。"))
    dk.divider("01","PART 1","受ける・取り次ぐ")
    dk.content("① 受け方の基本","3コール以内・明るく名乗る",[
        "3コール以内に出る（遅れたら“お待たせしました”）","“はい、(社名)でございます”と名乗る","相手の社名・氏名を復唱してメモ","保留は20秒以内。長くなれば折り返しを提案",
    ], callout=("POINT","第一声は“明るく・はっきり・名乗る”。"))
    dk.diagram("flow","② 取次ぎ","正確につなぐ",
        [("①","用件確認","相手・用件を確認→保留"),("②","担当へ伝える","相手名・用件を取り次ぐ"),("③","不在対応","戻り時間＋伝言/折り返し"),("④","次の一手","“わかりません”で終えない")],
        note="保留→担当者へ相手名・用件を伝える。不在時は戻り時間を伝え伝言or折り返しを提案。")
    dk.flow("FLOW ・ 伝言メモ","5W1Hで漏れなく",[
        ("W1","いつ","受けた日時"),("W2","誰から","会社名・氏名・番号"),("W3","誰へ","担当者"),("W4","用件","要点・折り返し要否"),
    ], "メモは復唱して確認→担当者の見える所に。自分の名前も添える。")
    dk.divider("02","PART 2","かける・難しい場面")
    dk.content("③ かけ方","相手の時間に配慮",[
        "名乗り→“今お時間よろしいですか”","結論から・要点を簡潔に","昼休み・始業直後／終業間際は避ける","切る時は相手が切ってから静かに",
    ])
    dk.compare("CASE ・ NG / OK","第一声で差が出る",
        ("印象の悪い対応",["無言で保留にする","“え?”“はい?”と何度も聞き返す","早口で社名が聞き取れない","担当不在で“わかりません”だけ"]),
        ("好印象な対応",["“少々お待ちください”と一言添える","“恐れ入ります、もう一度”と丁寧に","ゆっくり明るく社名を名乗る","“戻り次第折り返します”と次の一手"]))
    dk.diagram("flow","④ クレームの一次対応","まず傾聴と謝意",
        [("①","傾聴","最後まで遮らず聞く"),("②","お詫び","不快にさせた事へ謝意"),("③","事実確認","事実を確認しメモを取る"),("④","上長連携","自分で判断せず即連携")],
        note="言い訳・反論・たらい回しは火に油。まず聞く。")
    dk.work("WORK ・ 演習","模擬電話をやってみよう","ペアで“取次ぎ＋伝言”を実演","相手：取引先。担当の田中は外出中。","第一声→相手確認→不在を伝える→伝言を5W1Hで")
    dk.deepen()
    dk.checklist("CHECK ・ 到達チェック","合格ライン",[
        "3コール以内・正しい第一声で受けられる","取次ぎと保留が適切にできる","伝言メモを5W1Hで残せる","クレームの一次対応の型を説明できる",
    ])
    dk.closing("NEXT ・ まとめ","落ち着いて・笑顔の声で",[
        "電話はあなた＝会社の顔","困ったら保留→上長に相談","次：B6 上司とのコミュニケーション",
    ], "新入社員の電話応対マニュアル（YouTube教材タブ参照）","youtube.com/@otaakiyo")

def build_boss(dk):
    dk.tag="B6 上司コミュニケーション"
    dk.cover("B6","ビジネス基礎","上司とのコミュニケーション","“質問できる人”が一番伸びる","1時間")
    dk.content("GOAL ・ このモジュールのゴール","読み終えたらできること",[
        "自分でリサーチ→要点をまとめて相談できる","報連相を“早め”に出せる","遠慮せず質問できる（聞くのが正解）",
    ], numbered=True, callout=("POINT","新人の最大の武器は“素直さと質問力”。"))
    dk.divider("01","PART 1","相談の前にやること")
    dk.content("① まず自分で調べる→要点化","“丸投げ質問”をしない",[
        "まず自分で調べる・考える（5分〜）","事実と自分の意見を分ける","“要点3つ”に整理してから相談","調べてわからなければ、すぐ聞く（抱え込まない）",
    ], callout=("POINT","“調べた上で詰まった点”を聞くと一気に伸びる。"))
    dk.content("② 報連相は“早め”に","特に悪い情報は即",[
        "ミス・遅延・トラブルは即報告（隠さない）","結論ファースト（PREP）で簡潔に","中間報告で相手に安心を渡す","判断に迷ったら早めに相談",
    ], callout=("NG","“あとで”が一番危険。悪い報告ほど早く。"))
    dk.divider("02","PART 2","質問力とケース")
    dk.content("③ 質問はしすぎなくらいでいい","“うるさい”と言われるくらい聞け",[
        "新人のうちは質問が“仕事”。遠慮はいらない","同じ質問を繰り返さないようメモを取る","“何がわからないか”を言語化して聞く","聞かずにミスする方がずっと損",
    ], callout=("POINT","「質問が多い新人」＝伸びる新人。歓迎される。"))
    dk.flow("FORMAT ・ 相談の型","この順で相談する",[
        ("1","結論","“〜について相談です”"),("2","状況","背景・事実を簡潔に"),("3","自分の案","“私はAが良いと考えます”"),("4","聞きたい点","“判断を伺いたいです”"),
    ], "“自分の案つき”で相談すると、上司は判断するだけで済む＝早い・伸びる。")
    dk.compare("CASE ・ 良い質問 / 悪い質問","聞き方で印象が変わる",
        ("伸びない聞き方",["“どうすればいいですか?”（丸投げ）","調べればわかることを聞く","ギリギリまで抱え込んで聞く","一度に大量・脈絡なく"]),
        ("伸びる聞き方",["“Aと考えましたが合っていますか?”","調べて詰まった点を具体的に","早めに・こまめに確認","要点を絞って・メモしながら"]))
    dk.content("④ 上司の時間を奪わない工夫","配慮で信頼が増す",[
        "質問はある程度まとめて（細切れにしすぎない）","“今お時間1分よろしいですか”と確認","チャットで済むものはチャットで","お礼と結果報告までがワンセット",
    ])
    dk.work("WORK ・ 演習","要点化して相談してみよう","状況を“結論→状況→自分の案→聞きたい点”で1分相談","担当する求職者が他社内定で迷っている。あなたはどう動くか上司に相談。","自分の案を必ず1つ持って相談する")
    dk.deepen()
    dk.checklist("CHECK ・ 到達チェック","合格ライン",[
        "調べて要点化してから相談できる","悪い情報を早めに報告できる","遠慮せず具体的に質問できる","“自分の案つき”で相談できる",
    ])
    dk.closing("NEXT ・ まとめ","素直に・早めに・たくさん聞く",[
        "新人の武器は素直さと質問力","報連相は早め、相談は“自分の案つき”で","次：思考力(D) ／ 面談スキル(F) へ",
    ], "アクティブリスニング（傾聴）完全ガイド（YouTube教材タブ参照）","youtube.com/@thecoach")


def build_company(dk):
    dk.tag="A1 Tokumori理解"
    dk.cover("A1","自社・マインド","Tokumori理解・事業理解","ありたい自分で生きられる世界を、あたりまえにする","1.5時間")
    dk.content("GOAL ・ このモジュールのゴール","読み終えたらできること",[
        "会社概要・ミッション・事業（HR Support／RPO）を説明できる","“本当のゴール”を理解する（承諾でなく入社後の活躍・ありたい自分）","自分の仕事が誰をどう幸せにするかを語れる",
    ], numbered=True, callout=("POINT","“何屋で、何をゴールにしているか”を3分で語れること。"))
    dk.content("HELLO ・ はじめに（代表より）","“すごい会社に入る”ではなく“すごい会社を創る”",[
        "代表取締役 岡見悠平。創業5年未満・本格始動から約3年のスタートアップ","ミッションドリブンな経営で“拡大期”に突入","次のリクルート／サイバーエージェントのような会社を創る挑戦","“青春物語”のようなフェーズに当社はいる",
    ], callout=("POINT","完成された会社に入るのではなく、一緒に創るフェーズ。"))
    dk.content("PROFILE ・ 会社概要","株式会社TOKUMORI（TOKUMORI, Inc.）",[
        "設立：2021年6月1日／資本金：200万円／代表：岡見悠平","従業員：243名（正社員9・業務委託24・インターン153・その他57）","所在地：神奈川県横浜市港北区 新横浜（新横浜駅 徒歩10分）","社名は『特盛』が由来＝最大級の価値貢献。ロゴは日の丸と同じ“赤”",
    ], callout=("POINT","“特盛サイズ”の価値貢献が社名の意味。"))
    dk.content("DATA ・ 数字で見るTOKUMORI","拡大期の実績",[
        "クライアント数：300社／学生支援数：6,176名","平均年齢：29.5歳／正社員男女比：男45%・女55%","会社成長性：+457%（21年〜24年 決算比較）","“すごい会社を創る”を数字でも体現中",
    ])
    dk.divider("01","PART 1","私たちの理念（MVV）")
    dk.content("MISSION ・ ミッション","ありたい自分で生きられる世界を、あたりまえにする。",[
        "物質的には豊かでも“ありたい自分”で生きられない人が多い時代","SNSの他者比較・失敗への恐怖・期待に応える疲弊","だから一人ひとりが“ありたい自分”で生きられる世界を目指す","＝私たちの仕事の“本当のゴール”そのもの",
    ], callout=("POINT","求職者が入社後に活躍し“ありたい自分”でいられること＝ミッションの実現。"))
    dk.content("VISION ・ ビジョン","こころも、おなかも、いっぱいに",[
        "まず事業を通じて関わる人の“こころ”を豊かにする","世界には“おなか”（貧困・飢餓）に苦しむ人も多くいる","こころも、おなかも満たされる世界へ","事業の先に社会への還元を見据える",
    ])
    dk.content("VALUES ・ 3つの価値観","行動の土台",[
        "① 元気に愉しく、前向きに（プロとしての“愉しむ強さ”）","② 特盛級の価値貢献（誠実さ＋深い理解で期待を超える）","③ 認め合い・称え合い・思いやり（愛を持って率直に指摘も）","“チームTOKUMORI”として支え合い高め合う",
    ], callout=("POINT","“らしい”＝個性を認め前向き・特盛の価値貢献・称え合い。"))
    dk.content("CULTURE ・ 大事にする考え方","“TOKUMORIらしさ”を最優先",[
        "らしい：個性を認め合う／こころが豊か／前向きなエネルギー","らしい：愉しむ心を忘れない／相手のために誰よりも考え実行する","らしい：仲間を称える／優しいこころで率直に指摘／約束に真摯","らしくない：自分が正しいと思い込む／後ろ向き／感謝やリスペクトがない／自分勝手",
    ], callout=("POINT","スキルより“考え方”が土台。ここが評価と信頼を決める。"))
    dk.diagram("venn","VALUE ・ FOR YOU と FOR ME","利他と利己が“重なる”ところに最高の仕事がある",
        ("FOR YOU 利他","FOR ME 利己","最高の仕事"),
        note="FOR YOU＝求職者・企業・社会に尽くす／FOR ME＝自分の成長・成果・報酬。両方が重なる時＝求職者に本気で尽くす（利他）ことが結果的に成果（利己）になる瞬間を増やすのが良いCAの仕事。")
    dk.divider("02","PART 2","事業モデル")
    dk.content("DOMAIN ・ 事業ドメイン","2つの柱で企業の採用を支える",[
        "HR Support 事業：新卒・中途紹介／送客","RPO 事業：RPO（採用業務の代行・設計）・人事コンサルティング","紹介＝“人を送る”、RPO＝“採用の仕組みごと担う”","両輪で企業の採用課題を多面的に解決",
    ], callout=("POINT","当社の事業は「HR Support」と「RPO」の2ドメイン。"))
    dk.diagram("timeline","EXPAND ・ 事業領域の拡張","HRから始まり、放射状に広がる",
        [("HR Support","新卒・中途紹介/送客"),("RPO・人事","採用代行・コンサル"),("採用×データ×AI","新たな領域へ")],
        note="“今の事業”が全てではない。広がる会社で、広がるキャリアを。")
    dk.content("VENTURE ・ 私たちはベンチャー","だから、ここで挑戦してほしい",[
        "拡大フェーズの成長企業＝若手にも大きな裁量がある","仕組みが完成していない＝“自分で仕事を作れる”","事業領域がHRから放射状に広がっていく途上","早く挑戦した人ほど、“創る側”に回れる",
    ], callout=("POINT","完成された大企業ではなく、これから創る会社。挑戦の伸びしろが大きい。"))
    dk.content("VENTURE ・ ベンチャーの作法","挑戦する人の構え（『ベンチャーの作法』より）",[
        "圧倒的当事者意識（“自分の会社”として動く）","スピードと量（完璧を待たず、まず出して直す）","指示待ちでなく“自分で課題を見つけ、仕事を作る”","不確実性を楽しみ、経営者目線で考える",
    ], callout=("POINT","任される範囲が広い分、自走と当事者意識が全て。挑戦が“複利”で効く。"))
    dk.content("★最重要 ・ ゴールの再定義","内定承諾はゴールではない",[
        "内定承諾は“通過点”にすぎない","本当のゴール＝入社して活躍し“ありたい自分”でいられること（＝ミッション）","だから入社後を見据えたマッチングをする","目先の承諾・売上のための無理な後押しはしない",
    ], callout=("POINT","我々が支えるのは“その人の人生”。承諾はその一歩。"))
    dk.content("MODEL ・ 収益モデル（＝手段）","売上は“良い支援の結果”",[
        "新卒紹介は内定承諾で売上が立つ（承諾課金）","ただし売上はゴールでなく、良い支援の“結果”","入社後の活躍＝継続的な信頼＝事業の持続","RPOは採用業務の支援・代行で対価を得る",
    ], callout=("POINT","承諾・売上は“目的”ではなく“結果”。順番を間違えない。"))
    dk.diagram("flow","FLOW ・ 採用〜定着を一気通貫","HR Support × RPO の全体像",
        [("入口","母集団形成","送客・説明会"),("中核","面談・マッチング","選考支援"),("出口","内定者フォロー","入社後の定着支援")],
        note="基盤：データ／Salesforce・AI活用・業界知識が入口〜出口を仕組みで支える。")
    dk.diagram("flow","FLOW ・ 求職者支援の流れ","登録から入社後の活躍まで一気通貫",
        [("①","登録・初回面談","価値観・希望を言語化"),("②","提案","業界・職種理解で選択肢を渡す"),
         ("③","選考対策","面接同席・対策"),("④","意思決定支援","内定→納得のクロージング"),("⑤","入社後フォロー","活躍まで伴走")],
        note="“④承諾”で終わらない。⑤入社後の活躍までが支援範囲。")
    dk.divider("03","PART 3","キャリアと仲間")
    dk.radial("CAREER ・ 多職能が放射状に広がる","1つの職能に留まらない",
        "あなた",["キャリア支援(CA)","営業(RA)","マーケティング","企画・事業開発","採用・人事","RPO/人事コンサル","マネジメント","新規事業"],
        "1つの職能に縛られず、様々な職能が放射状に身につく。中心にいるのは“あなた”。")
    dk.diagram("directions","CAREER ・ 縦・横・斜めに伸ばす","キャリアの広げ方は1本道じゃない",
        ("あなた",
         [("縦","専門を深め、トップ→リーダー→マネジメントへ",False),
          ("横","CA→RA→マーケ→企画 など職種を広げる",False),
          ("斜め","新規事業・事業拡大に乗り、領域を超える",True)]),
        note="若い会社 × 拡大期＝挑戦できる機会が多い。縦（専門深化）・横（職種拡大）・斜め（領域を超える）と多方向に伸ばせる。")
    dk.cards("CAREER ・ 関われるキャリアと身につく力","“人の人生を動かす”経験と、ポータブルスキルが同時に手に入る",[
        ("関われる経験","EXPERIENCE","求職者一人ひとりの“人生の岐路”に立ち会える。あらゆる業界・職種・企業を横断的に深く知れる。"),
        ("身につく力","SKILL","傾聴・提案・課題解決・対人折衝・数字をつくる力。AI活用・キャリア支援の専門性＝どこでも通用する市場価値。"),
    ])
    dk.content("TEAM ・ 経営陣","創る挑戦を率いるメンバー",[
        "代表取締役 岡見悠平：サイバーエージェントで新人MVP→採用責任者を経て創業","取締役副社長 築嶋宏宜：新卒紹介の創業/売却、MiL執行役員、HRBrain事業企画室長を経てジョイン","執行役員 渡邊駿：千趣会→マイナビ(新卒紹介)→WEB広告運用を経てジョイン","“市場に必要な会社を創る”を本気で目指す経営陣",
    ])
    dk.work("WORK ・ 演習","“ゴール”を自分の言葉で語ろう","学生役に『TOKUMORIは何をする会社で、何をゴールにしているか』を3分で","相手は就活中の大学生。","ミッション→事業(HR Support/RPO)→“承諾でなく入社後の活躍がゴール” を必ず入れる")
    dk.deepen()
    dk.checklist("CHECK ・ 到達チェック","合格ライン",[
        "会社概要とミッション（ありたい自分〜）を説明できる","事業ドメイン（HR Support／RPO）を説明できる","“本当のゴール＝入社後の活躍／ありたい自分”を語れる","収益（承諾課金）は“結果”だと説明できる",
    ])
    dk.closing("NEXT ・ まとめ","承諾は通過点、ありたい自分の実現がゴール",[
        "ミッション：ありたい自分で生きられる世界を、あたりまえにする","事業はHR Support（紹介/送客）とRPO（代行/コンサル）の両輪","次：A2 社会人マインド ／ A3 業界の全体像",
    ], "（社内・会社資料／ブランドブックも参照）","")

def build_mindset(dk):
    dk.tag="A2 社会人マインド"
    dk.cover("A2","自社・マインド","社会人マインドセット","学生から“価値を出す側”へ。意識を切り替える","1.5時間")
    dk.content("GOAL ・ このモジュールのゴール","読み終えたらできること",[
        "学生と社会人の違いを具体的に説明できる","当事者意識（オーナーシップ）を持って動ける","プロとしての時間・約束・品質の基準を実践できる","成長し続ける人の習慣を身につける",
    ], numbered=True, callout=("POINT","スキルより先に“スタンス”。意識が変われば行動と成果が変わる。"))
    dk.divider("01","PART 1","学生から社会人へ")
    dk.content("学生と社会人の違い","5つの軸で変わる",[
        "お金：払って学ぶ → もらって価値を出す","評価：努力・過程 → 成果・結果","時間：自分の都合 → 相手・チームの都合","責任：自分の成績 → 会社・お客様への責任","人間関係：選べる仲間 → 選べない多様な相手",
    ], callout=("POINT","“やった”ではなく“役に立った”が評価される。"))
    dk.content("求められる5つの転換","マインドの切り替え",[
        "受け身 → 主体的（自分から動く）","正解探し → 正解づくり（前例がない問いに挑む）","個人プレー → チームで成果","ミスを隠す → ミスを早く共有し学びに変える","“できない理由” → “どうすればできるか”",
    ])
    dk.content("当事者意識（オーナーシップ）","“自分ごと”にする力",[
        "“誰かがやる”ではなく“自分がやる”","コントロールできることに集中する（他責にしない）","指示の背景・目的まで考えて動く","小さな仕事も全力で（信頼は小さな仕事から）",
    ], callout=("POINT","主体性は才能でなく“選択”。誰でも今日から持てる最強スキル。"))
    dk.diagram("before_after","MINDSET ・ 自責思考で考える","“自分にできること”に焦点を当てる",
        (("他責思考","環境・上司・運のせい→手が止まる"),("自責思考","自分の打ち手で状況を動かす")),
        note="他責は楽だが成長しない。自責は“自分で人生を動かす力”。原因を自分側に置き、次の一手を考える。")
    dk.content("プロ意識①：時間と約束","信頼の土台",[
        "5分前行動・締切厳守（遅れそうなら早めに一報）","約束（納期・依頼・返信）を必ず守る","アポ・会議は準備してから臨む","“当たり前”を高いレベルで続ける",
    ])
    dk.content("プロ意識②：品質と数字","成果にこだわる",[
        "提出前に自分でチェック（誤字・抜け・宛先）","完璧主義より“早く出して直す”を優先する場面も","コスト・時間・利益の意識を持つ","“で、結局どうなった？”に答えられる仕事を",
    ], callout=("POINT","品質＝相手の期待を超えること。セルフチェックは礼儀。"))
    dk.divider("02","PART 2","成長し続ける習慣")
    dk.content("素直さ・吸収力","一番伸びる人の共通点",[
        "フィードバックは“感謝→改善”で受ける（言い訳しない）","まず型を真似る（守破離の“守”）","学んだらすぐ試す・記録する","わからないことはすぐ聞く（質問は武器）",
    ], callout=("POINT","“素直で打たれ強い人”が結局いちばん成長する。"))
    dk.content("振り返りと時間管理","自走するための型",[
        "PDCA／日々の振り返り（うまくいった/改善点）","優先順位＝緊急×重要で仕分け","重要だが緊急でないこと（学習・準備）に投資","タスクを見える化し、抱え込まない",
    ])
    dk.content("セルフマネジメント","土台は心身の健康",[
        "睡眠・運動・食事を整える（パフォーマンスの土台）","ストレスの対処法を自分で持つ","オン/オフを切り替える","不調は早めに相談する",
    ])
    dk.content("TOKUMORIのVALUESと接続","“らしさ”を体現する",[
        "① 元気に愉しく、前向きに（プロとしての“愉しむ強さ”）","② 特盛級の価値貢献（誠実さ＋深い理解）","③ 認め合い・称え合い・思いやり","マインドはVALUESを日々の行動に落とすこと",
    ], callout=("POINT","マインドセット＝TOKUMORI VALUESを“自分の行動”にする。"))
    dk.divider("03","PART 3","成長を加速する考え方")
    dk.content("伸びる人の3資質","才能より後天的に伸ばせる",[
        "素直さ：助言を“感謝→即実行”。プライドより成長を取る","粘り強さ：すぐ諦めず、できるまで工夫を続ける","GRIT（やり抜く力）：才能でなく“情熱×継続”が長期の成果を決める（ダックワース）","凡事徹底：当たり前を、誰よりも高いレベルで続ける",
    ], callout=("POINT","『素直さ×粘り強さ×やり抜く力』が、結局いちばん伸びる。"))
    dk.content("ロマンとそろばん","理想と数字は“両輪”",[
        "ロマン＝成し遂げたい理想・社会への意義","そろばん＝利益・売上という現実の数字","理想だけでは続かず、数字だけでは虚しい","両輪が回って初めて事業は継続し、貢献も広がる",
    ], callout=("POINT","ロマンとそろばんは対立でなく両輪。どちらも本気で追う。"))
    dk.content("まず“そろばん”を優先する理由","売上は貢献の“燃料”",[
        "売上を上げるほど、できることの幅が広がる","稼ぐ力がつくほど、関われる社会課題も大きくなる","だから最初は“そろばん”＝稼ぐ力を磨くことを優先する","利益は目的でなく、より大きな社会貢献のための手段",
    ], callout=("POINT","まず稼ぐ力をつける。それが結果的に社会課題解決の幅を広げる。"))
    dk.content("若いうちは“挑戦の量”","失敗の数＝成長の加速",[
        "若手の最大の武器は“失敗できること”","挑戦せず無傷でいることこそ、最大のリスク","小さく速く試し、振り返って次に活かす","完璧を待つより、まず打席に立つ",
    ], callout=("POINT","失敗の数＝成長の加速。現状維持は緩やかな後退。"))
    dk.barchart("図解 ・ 量と質","量と質：まず打席に立て",[
        ("10打数10安打（完璧主義）",0.91,"安打10本",False),
        ("100打数11安打（挑戦量）",1.0,"安打11本",True),
    ], "打率（失敗の少なさ）でなく“安打の絶対数”で評価される。100打数11安打＞10打数10安打。")
    dk.content("社会は“成果の数”で評価する","失敗は評価を下げない",[
        "評価されるのは打率ではなく“安打（成果）の数”","どれだけ失敗しても、出した成果の数だけが積み上がる","失敗は減点でなく、挑戦したからこそ生まれる副産物","だから打席を増やす＝挑戦量を最大化する人が伸びる",
    ], callout=("POINT","100打数11安打が社会では評価される。失敗の数でなく“成果の数”で見られる。"))
    dk.linechart("図解 ・ 複利の成長","毎日1%成長の“指数関数”",
        ["開始","3ヶ月","6ヶ月","9ヶ月","1年"],
        [{"name":"毎日 −1%","ys":[0.026,0.011,0.005,0.002,0.001],"hi":False},
         {"name":"現状維持","ys":[0.026,0.026,0.026,0.026,0.026],"hi":False},
         {"name":"毎日 +1%","ys":[0.026,0.066,0.163,0.405,1.0],"vals":["1.0","2.5倍","6.2倍","15倍","37.8倍"],"hi":True}],
        "1.01の365乗≒37.8、0.99の365乗≒0.03。毎日のわずかな差が複利で“指数関数的”に開く。")
    dk.linechart("図解 ・ 忘却曲線","エビングハウスの忘却曲線",
        ["20分後","1時間後","1日後","1週間後"],
        [{"name":"記憶保持率","ys":[0.58,0.44,0.34,0.21],"vals":["58%","44%","34%","21%"],"hi":True}],
        "学んだ事は1日で約7割忘れる（エビングハウス, 1885）。だから“即実行・当日復習・記録”で記憶を定着させる。",
        ylab=("保持率","100%","0%"))
    dk.linechart("図解 ・ 復習の効果","復習で忘却はゆるやかになる",
        ["学習直後","1日後","3日後","1週間後","2週間後","1ヶ月後"],
        [{"name":"復習なし","ys":[1.0,0.42,0.28,0.18,0.12,0.08],"hi":False},
         {"name":"復習あり","ys":[1.0,0.72,0.82,0.80,0.90,0.95],"vals":["","↑復習","","↑復習","","定着"],"hi":True}],
        "復習しないと1ヶ月で約1割しか残らない。直後・1日後・1週間後・1ヶ月後に復習すると、忘却がゆるやかになり長期記憶に定着する（分散学習）。",
        ylab=("保持率","100%","0%"))
    dk.content("忘れないための復習法","学びを“自分のもの”にする",[
        "覚えた直後・翌日・1週間後・1ヶ月後に復習する（分散学習）","インプットよりアウトプット（思い出す・人に説明・書く）で定着","研修は“受けて終わり”にせず、当日中に要点を3つ書き出す","毎日の振り返り（KPT・日報）が、学びを成果に変える最強の習慣",
    ], callout=("POINT","学びは“復習と振り返り”で初めて身につく。1回で覚えようとしない。"))
    dk.linechart("図解 ・ 自己認知","ダニング＝クルーガー効果の曲線",
        ["無知","","","","専門家"],
        [{"name":"自信","ys":[0.15,0.95,0.2,0.55,0.8],"vals":["","①「馬鹿の山」","②「絶望の谷」","③「啓蒙の坂」","④「継続の台地」"],"hi":True}],
        "能力が低いほど自信過剰（馬鹿の山）→学ぶほど無知に気づき急落（絶望の谷）→経験で回復（啓蒙の坂）。谷で辞めないことが本物への道。出典：Kruger & Dunning (1999)。",
        dots=False, ylab=("自信","高い","低い"))
    dk.content("新卒に期待すること","3ヶ月で“頭角を表す”",[
        "結果だけでなく、姿勢・学習速度・信頼など“様々な面”で","3ヶ月で『お、こいつは違う』と思わせる","最初の数ヶ月の本気度が、その後の評価と裁量を決める","頭角＝目立つことでなく『任せたくなる』状態をつくること",
    ], callout=("POINT","3ヶ月で頭角を表す。結果に限らず、あらゆる面で“違い”を見せる。"))
    dk.work("WORK ・ 演習","“なりたい社会人”を宣言しよう","学生と社会人の違いを5つ挙げ、3ヶ月後の自分を一言で宣言","例：『指示待ちせず、自分から提案できる人になる』","違い→なりたい姿→そのための具体行動3つ の順で")
    dk.deepen()
    dk.checklist("CHECK ・ 到達チェック","合格ライン",[
        "学生と社会人の違いを5軸で説明できる","当事者意識を持って動ける","時間・約束・品質の基準を実践できる","成長する習慣（素直さ・振り返り）を言える",
    ])
    dk.closing("NEXT ・ まとめ","“役に立つ”を基準に、主体的に動く",[
        "評価軸は 成果・相手起点・責任","主体性・プロ意識・素直さが伸びる人の3条件","次：A3 業界の全体像 ／ B1 ビジネスマナー",
    ], "（社内資料・VALUESを参照）","")

def build_industry(dk):
    dk.tag="A3 人材業界の全体像"
    dk.cover("A3","自社・マインド","人材紹介業界の全体像","“人と仕事をつなぐ”ビジネスの地図","1.5時間")
    dk.content("GOAL ・ このモジュールのゴール","読み終えたらできること",[
        "人材ビジネス4類型の違いとお金の流れを説明できる","新卒紹介の商流を白紙から描ける","職業安定法の基礎と市場の動きを理解する","TOKUMORIの立ち位置を語れる",
    ], numbered=True, callout=("POINT","業界の地図を持つと、求職者への提案の説得力が一気に増す。"))
    dk.divider("01","PART 1","人材ビジネスの地図")
    dk.content("人材ビジネス 4類型","“お金の入り方”で性質が変わる",[
        "人材紹介：採用成功で企業から成功報酬（当社の主軸）","人材派遣：派遣スタッフの稼働時間で料金","求人広告：求人掲載に対して課金（ナビ媒体等）","HRtech：採用支援SaaSの月額課金（ATS・スカウト等）",
    ], callout=("POINT","“いつ・誰から”お金が入るかで、事業の性質と動き方が決まる。"))
    dk.compare("CASE ・ 紹介 vs 求人広告","代表的な2モデルの違い",
        ("求人広告（掲載課金）",["掲載した時点で費用が発生","採用できなくても費用は戻らない","企業が自分で母集団・選考を回す","母集団は多いが質の見極めは企業側"]),
        ("人材紹介（成功報酬）",["採用成功（承諾）で初めて費用","採用できなければ費用は無し＝低リスク","エージェントが推薦・選考支援","質の高いマッチングと工数削減"]))
    dk.diagram("platform","FLOW ・ 新卒紹介の商流","求職者 ⇄ 当社 ⇄ 企業：価値とお金の流れ",
        (("TOKUMORI",["CA × RA が最適な出会いを設計","承諾で売上（＝良い支援の結果）"]),
         ("求職者",[("無料で登録・面談",">"),("求人を提案","<"),("内定・入社","<")]),
         ("企業",[("求人・採用要件",">"),("人材を紹介","<"),("成功報酬を支払う",">")])),
        note="求職者は無料。企業は採用成功（承諾）で成功報酬を支払う。CA×RAが最適な出会いを設計＝売上は結果、本当のゴールは入社後の活躍。")
    dk.content("なぜ企業は“紹介”にお金を払うのか","価値の正体",[
        "採用工数の削減（母集団形成・スクリーニングを代行）","マッチングの質（活躍・定着する人材）","スピード（必要な人材に早く出会える）","採用ノウハウ・市場情報の提供",
    ], callout=("POINT","“成功報酬を払ってでも欲しい価値”＝工数・質・スピード。"))
    dk.divider("02","PART 2","ルールと市場")
    dk.content("職業安定法の基礎","必ず守るルール",[
        "人材紹介は許可制（有料職業紹介事業の許可が必要）","求職者から手数料は原則取らない","個人情報・求人情報の適正な取扱い","虚偽・誇大な表示の禁止／違法求人は扱わない",
    ], callout=("NG","ルール違反は事業の根幹を揺るがす。迷ったら必ず確認。"))
    dk.content("市場規模で見る人材ビジネス","“伸びるパイ”の中で戦う",[
        "人材サービス産業全体は約9.8兆円（2024年度・矢野経済研究所／派遣・紹介・再就職）","うち人材紹介は前年比＋12%と特に好調・拡大基調","追い風：少子化による採用難・売り手市場・採用の外部委託化","新卒領域はナビ媒体中心から“紹介・スカウト型”へシフト中",
    ], callout=("POINT","縮むパイではなく伸びるパイ＝努力が成果に変わりやすい追い風の業界。"))
    dk.barchart("市場 ・ 図解","人材ビジネスの内訳（概算）",[
        ("人材派遣",1.0,"約7〜8兆円",False),
        ("有料職業紹介（当社領域）",0.13,"約0.98兆円（手数料収入）",True),
        ("求人広告",0.12,"約1兆円規模",False),
        ("HRTech・その他",0.05,"拡大中",False),
    ], "派遣が最大。紹介は規模では小さいが＋17%超で拡大（2024年度・矢野経済研究所/厚労省）。")
    dk.content("中途紹介 vs 新卒紹介","“紹介”の中での新卒の位置づけ",[
        "人材紹介市場は中途（転職）が大半（約9割以上）","ホワイトカラー人材紹介は約4,110億円（2024年度・前年比＋17.1%／矢野経済研究所）","新卒『紹介』は規模では小さいが、成長率は最も高い","少子化で“攻めの採用”需要 → 新卒紹介・スカウトが拡大",
    ], callout=("POINT","新卒紹介は小さなパイだが“最も伸びている”領域＝当社の勝ち筋。"))
    dk.barchart("図解 ・ 新卒採用の手法","新卒採用の手法別シェア（企業の利用・就職白書2024）",[
        ("ナビ媒体（リクナビ等）",0.95,"最大チャネル",False),
        ("ダイレクトリクルーティング",0.34,"約34%",False),
        ("エージェント（新卒紹介）",0.27,"利用 約2〜3割",True),
        ("リファラル（社員紹介）",0.21,"約21%",False),
        ("採用直結インターン",0.20,"約20%",False),
    ], "ナビ媒体は依然最大だが頭打ち。スカウト・新卒紹介・リファラルが伸びている（当社＝紹介）。")
    dk.content("新卒採用市場の動き","いま起きていること",[
        "早期化：インターン直結・3年生（夏）からの本格化","通年採用・初任給引き上げ競争（初任給30万円台の企業も）","売り手市場でも“納得内定／ミスマッチ防止”が課題","学生は情報過多で迷いやすい → 伴走の価値が高い",
    ])
    dk.content("最新トピック ・ オワハラと就活の“今”","学生に語れるニュース感度を持つ",[
        "オワハラ＝就活終われハラスメント。内定と引換に他社の選考辞退を強要する行為・売り手市場で問題化","インターンで得た情報の採用活用が解禁（三省合意の見直し）→インターンの比重増・早期化が加速","AIで就活が変化：ES生成・AI面接の拡大と、企業側のAIチェック","CAの役割：急かさず、学生が“納得して”意思決定できるよう中立に伴走する",
    ], callout=("POINT","ニュースを自分の言葉で語れると、学生からの信頼が一段上がる。"))
    dk.content("主要プレイヤー・採用手法","学生はここで動く",[
        "ナビ媒体（リクナビ・マイナビ等）：掲載・エントリー","エージェント（紹介）：推薦・面談支援","ダイレクトリクルーティング／逆求人（スカウト型）","SNS・リファラル・説明会／インターン",
    ])
    dk.content("学生側のプロセス","求職者の動きを理解する",[
        "自己分析 → 業界・企業研究","エントリー・ES → 適性検査","面接（複数回）→ 最終・オファー面談","内定 → 意思決定（複数内定で迷う）",
    ], callout=("POINT","学生がどこで詰まるかを知ると、支援のポイントが見える。"))
    dk.content("TOKUMORIの立ち位置","2ドメインで支える",[
        "HR Support 事業：新卒・中途紹介／送客","RPO 事業：RPO（採用代行）・人事コンサル","紹介＝“人”、RPO＝“仕組み”で企業を多面的に支援","収益は内定承諾課金（＝良い支援の結果）",
    ])
    dk.work("WORK ・ 演習","業界マップを白紙から描こう","紹介／派遣／求人広告／HRtech の違いとお金の流れを図にする","ヒント：誰が・いつ・誰にお金を払うか","描いた図を相手に1分で説明できればOK")
    dk.deepen()
    dk.checklist("CHECK ・ 到達チェック","合格ライン",[
        "人材ビジネス4類型の違いを説明できる","新卒紹介の商流を白紙から描ける","職業安定法の基礎を言える","新卒市場の動きとTOKUMORIの立ち位置を語れる",
    ])
    dk.closing("NEXT ・ まとめ","地図を持って提案する",[
        "我々は“紹介”で、企業からの成功報酬で成り立つ（売上は結果）","ルール（職安法）を守るのが大前提","次：F2 業界・職種理解（実務へ）",
    ], "（人気ランキング・業界×職種タブも参照）","")

def build_email(dk):
    dk.tag="B3 ビジネスメール"
    dk.cover("B3","ビジネス基礎","ビジネスメール","“伝わって・動いてもらえる”メールを書く","1時間")
    dk.content("GOAL ・ このモジュールのゴール","読み終えたらできること",[
        "件名・宛名・結びの型でメールを書ける","CC/BCCを正しく使い分けられる","結論ファーストで簡潔に書ける",
    ], numbered=True, callout=("POINT","メールは“読み手の時間を奪わない”のが礼儀。"))
    dk.diagram("flow","FLOW ・ メールの基本構成","上から順に積み上げる型",
        [("件名","用件を具体的に","ひと目でわかる"),("宛名","会社→部署→役職→氏名",""),
         ("挨拶＋名乗り","お世話になっております","＋自社名・氏名"),("本文","結論→詳細",""),
         ("結び＋署名","よろしくお願いします","")],
        note="件名で開かれ、最初の3行で要件が伝わる。")
    dk.content("書き出しと結びの型","定番フレーズ",[
        "書き出し：いつもお世話になっております","クッション言葉：恐れ入りますが／お手数ですが","依頼：〜していただけますと幸いです","結び：よろしくお願いいたします",
    ])
    dk.content("CC / BCC の使い分け","事故を防ぐ",[
        "CC：共有しておきたい関係者（全員に見える）","BCC：受信者同士に見せたくない一斉送信","TO：主に対応してほしい相手","送信前に宛先を最後に確認（誤送信防止）",
    ], callout=("NG","個人情報の一斉送信でCC→重大な漏洩。BCCを徹底。"))
    dk.compare("CASE ・ NG / OK","同じ用件でも伝わり方が違う",
        ("読みにくいメール",["件名が『お世話になります』だけ","経緯から長く結論が見えない","改行なしの一段落","宛名・署名がない"]),
        ("伝わるメール",["件名『◯◯の日程ご相談（◯/◯まで）』","結論→理由→お願いの順","適度な改行・箇条書き","宛名・挨拶・署名が揃っている"]))
    dk.content("悪い例 → 良い例（面談案内メール）","同じ用件でこう変わる",[
        "件名：✕「お世話になります」→ ○「【面談日程のご相談】◯/◯までにご返信ください」","宛名：✕いきなり本文 → ○「◯◯株式会社 ◯◯様」＋「お世話になっております。Tokumoriの△△です」","本文：✕長い経緯から書く → ○結論（候補3日程）を先に・箇条書きで","結び／署名：✕なし → ○「ご確認のほどよろしくお願いいたします」＋署名（社名・氏名・連絡先）",
    ], callout=("POINT","“件名・結論・署名”の3点を直すだけで、返信率が大きく変わる。"))
    dk.work("WORK ・ 演習","悪い例を“良い例”に直す＋署名設定","①読みにくい悪い例メールを、件名・宛名・結論ファースト・署名まで直す","②求職者への面談案内メール（候補3日程＋返信依頼）を一から書く","③自分のメール／Gmailに“署名”（社名・氏名・連絡先）を設定する")
    dk.deepen()
    dk.checklist("CHECK ・ 到達チェック","合格ライン",[
        "わかりやすい件名を付けられる","結論ファーストで本文を書ける","CC/BCCを正しく使い分けられる","誤送信を防ぐ確認ができる",
    ])
    dk.closing("NEXT ・ まとめ","読み手の時間を大切に",[
        "件名と最初の3行で勝負","個人情報はBCC・送信前確認を徹底","次：B5 議事録作成",
    ], "（社内のメール文例も参照）","")

def build_minutes(dk):
    dk.tag="B5 議事録"
    dk.cover("B5","ビジネス基礎","議事録作成","“決まったこと”と“やること”を残す","1時間")
    dk.content("GOAL ・ このモジュールのゴール","読み終えたらできること",[
        "決定事項とToDo（担当・期限）を構造化できる","会議後すぐに議事録を作れる","事実と意見を分けて書ける",
    ], numbered=True, callout=("POINT","議事録は“記録”ではなく“次の行動”のためにある。"))
    dk.content("議事録の目的","なぜ書くのか",[
        "決定事項を全員で共有する","ToDo（誰が・いつまでに）を明確にする","言った言わないを防ぐ","欠席者にも経緯を伝える",
    ])
    dk.diagram("flow","STEP ・ 基本の構成","この型で書く",
        [("①","日時/参加者/議題","会議の前提を記録"),("②","決定事項","結論を明確に"),
         ("③","ToDo","担当・期限つきで"),("④","保留・次回","継続検討/次回予定")],
        note="“決定事項”と“ToDo”が一番大事。ここを外さない。")
    dk.content("取り方のコツ","速く・正確に",[
        "結論・要点を簡潔に（逐語は不要）","事実と意見（推測）を分けて書く","重要発言は誰の発言か明確に","会議後すぐ作り、関係者へ早めに共有",
    ], callout=("NG","逐語の長文メモは“読まれない議事録”になる。"))
    dk.work("WORK ・ 演習","模擬会議を議事録にしよう","短い会議の録音/メモから、15分で議事録を作成","フォーマット：日時/参加者/議題/決定/ToDo/次回","ToDoは必ず担当と期限をつける")
    dk.deepen()
    dk.checklist("CHECK ・ 到達チェック","合格ライン",[
        "決定事項とToDoを構造化できる","担当・期限を明確に書ける","事実と意見を分けられる","会議後すぐ共有できる",
    ])
    dk.closing("NEXT ・ まとめ","決定とToDoを外さない",[
        "議事録は“次の行動”のため","早く作り、早く共有","次：C系（PCツール）へ",
    ], "一流の議事録の取り方/書き方講座（YouTube教材タブ）","youtube.com/@youseful")

def build_disc(dk):
    dk.tag="E1 DISC理論"
    dk.cover("E1","自己・対人","DISC理論","“相手のタイプ”に合わせて伝える","1時間")
    dk.content("GOAL ・ このモジュールのゴール","読み終えたらできること",[
        "自分のDISCタイプを理解する","4タイプの特徴を説明できる","相手のタイプに合わせた接し方ができる",
    ], numbered=True, callout=("POINT","人は4タイプで大きく傾向が違う。合わせると伝わる。"))
    dk.divider("01","PART 1","4つのタイプ")
    dk.diagram("matrix","TYPES ・ DISCとは","行動傾向を2軸・4象限で捉える",
        ("仕事・課題　⇄　人・感情","外向・積極　⇄　内向・慎重",
         [("D 主導","結果志向・決断が速い",True),("i 感化","社交的・熱量・ノリ",False),
          ("C 慎重","論理的・データ重視",False),("S 安定","協調的・聞き上手",False)]),
        note="2軸（仕事↔人／外向↔内向）で4象限。良い悪いでなく“傾向の違い”、優劣はない。")
    dk.content("タイプ別の接し方","相手に合わせる",[
        "D：結論から・要点を簡潔に・任せる","i：明るく・感情に共感・一緒に盛り上げる","S：丁寧に・安心感・急かさない","C：根拠・データ・手順を示す",
    ], callout=("POINT","CA面談でも、求職者のタイプに合わせると本音が出る。"))
    dk.diagram("flow","STEP ・ 自分のタイプを知る・活かす","自己理解→対人へ広げる",
        [("①","自分を知る","強み・クセを把握"),("②","苦手に備える","苦手タイプへの接し方を準備"),
         ("③","周囲を推測","チーム/上司のタイプを読む"),("④","相手優先","受け取りやすさを最優先")],
        note="まず自分の傾向（強み・クセ）を知り、対人へ広げる。最後は“相手の受け取りやすさ”を優先する。")
    dk.work("WORK ・ 演習","タイプ別に同じ要件を伝えてみよう","『面談日程を決めたい』をD/i/S/Cそれぞれ向けに言い換える","相手：4タイプの求職者を想定","各タイプの“響く言い方”を1文ずつ")
    dk.deepen()
    dk.checklist("CHECK ・ 到達チェック","合格ライン",[
        "自分のタイプを説明できる","4タイプの特徴を言える","相手のタイプを推測できる","タイプに合わせて接し方を変えられる",
    ])
    dk.closing("NEXT ・ まとめ","違いを知れば、伝わる",[
        "DISCは“相手に合わせる”ための地図","面談・社内コミュ両方で効く","次：傾聴・面談スキル（F）へ",
    ], "DISC理論 4タイプ解説（YouTube教材タブ）","workhappiness.co.jp")

def build_security(dk):
    dk.tag="G3 情報セキュリティ"
    dk.cover("G3","リスク・コンプラ","情報セキュリティ","“事故を起こさない”基本動作","1.5時間")
    dk.content("GOAL ・ このモジュールのゴール","読み終えたらできること",[
        "安全なパスワード・端末管理ができる","フィッシング等の手口を見抜ける","共有設定・情報持ち出しの危険を判断できる",
    ], numbered=True, callout=("POINT","情報事故は“一人のうっかり”から。基本動作で防ぐ。"))
    dk.content("パスワード・認証","入口を固める",[
        "推測されにくい長いパスワード／使い回さない","二段階認証を必ず有効化","付箋やメモにパスワードを書かない","共有アカウントの私的利用をしない",
    ])
    dk.content("端末・離席","物理の基本",[
        "離席時は画面ロック（必ず）","公共Wi-Fiでの機密作業を避ける","PC/スマホの紛失対策（ロック・追跡）","怪しいUSB・アプリを使わない",
    ], callout=("POINT","ちょっとの離席でもロック。習慣にする。"))
    dk.content("フィッシング・共有設定","だまされない・漏らさない",[
        "不審なメール/リンク/添付は開かず確認","送信元・URLをよく見る（なりすまし）","ファイル共有は“必要な人だけ”に限定","『リンクを知る全員』公開は慎重に",
    ], callout=("NG","求職者情報の入ったファイルを誰でも閲覧可で共有→重大事故。"))
    dk.work("WORK ・ 演習","危険を見抜こう","提示する状況のどこが危険か指摘する","例：『至急ログインして』という外部リンク付きメール","危険箇所→正しい対処 をセットで")
    dk.deepen()
    dk.checklist("CHECK ・ 到達チェック","合格ライン",[
        "強いパスワードと二段階認証を設定できる","離席時ロックを徹底できる","フィッシングを見抜ける","共有設定の危険を判断できる",
    ])
    dk.closing("NEXT ・ まとめ","基本動作で事故ゼロ",[
        "ロック・二段階認証・共有設定が三種の神器","怪しいと思ったら開かず相談","次：G4 ハラスメント・NG行動",
    ], "（社内セキュリティ規程を参照）","")

def build_harass(dk):
    dk.tag="G4 ハラスメント・NG行動"
    dk.cover("G4","リスク・コンプラ","ハラスメント研修","“安全な職場”を全員でつくる（職場のNG行動）","1.5時間")
    dk.content("GOAL ・ このモジュールのゴール","読み終えたらできること",[
        "ハラスメントの定義と種類を理解する","やってはいけない言動を判別できる","受けた・見た時の相談先を知る",
    ], numbered=True, callout=("POINT","知らずに加害者にならない・被害を抱え込まないために。"))
    dk.content("ハラスメントとは","相手が不快ならアウトになり得る",[
        "立場や言動で相手に苦痛を与える行為","“本人にその気がなくても”成立し得る","受け手がどう感じたかが重要","職場の安全・信頼を壊す",
    ])
    dk.diagram("relation","主な種類","代表例",
        ("ハラスメント", ["パワハラ","セクハラ","モラハラ","各種ハラ"]),
        note="“指導”と“パワハラ”は別物。人格でなく行動を指摘する。（時短/妊娠/SNS等の各種ハラもある）")
    dk.content("DON'T ・ やってはいけない言動と対処","迷う言動はしない",[
        "人格否定・暴言・無視・過度な叱責","SNSでの中傷・プライバシー暴露","断りにくい誘い・しつこい連絡","見聞きしたら：一人で抱えず相談窓口・上長へ",
    ], callout=("POINT","迷う言動はしない。相談は弱さではなく正しい行動。"))
    dk.work("WORK ・ 演習","NG言動を判別しよう","提示する言動がNGか、なぜNGかを判断","例：後輩に『これくらいできて当然』と全員の前で叱責","NG理由→より良い伝え方 をセットで")
    dk.deepen()
    dk.checklist("CHECK ・ 到達チェック","合格ライン",[
        "ハラスメントの定義を説明できる","主な種類を挙げられる","NG言動を判別できる","相談先を知っている",
    ])
    dk.closing("NEXT ・ まとめ","安全な職場は全員の責任",[
        "“相手がどう感じるか”を基準に","迷う言動はしない・見たら相談","Stage1修了→実務と並行でStage2へ",
    ], "（社内のハラスメント相談窓口を確認）","")

def build_incident(dk):
    dk.tag="G5 インシデント対応"
    dk.cover("G5","リスク・コンプラ","インシデント対応","“隠さず・即報告”で被害を最小化する","1時間")
    dk.content("GOAL ・ このモジュールのゴール","読み終えたらできること",[
        "インシデント発生時の初動フローを説明できる","『隠さず即報告→上長→対応』の原則を理解する","被害最小化と再発防止の動きができる",
    ], numbered=True, callout=("POINT","事故対応の良し悪しは“初動の速さと正直さ”で決まる。"))
    dk.divider("01","PART 1","起きた時の初動")
    dk.content("① まず即報告（隠さない）","スピードがすべて",[
        "ミス・事故・漏洩・トラブルは即、上長へ報告","隠す・自己判断で握り込むのが最悪","早く報告するほど被害は小さくなる","“悪い報告ほど早く”が鉄則",
    ], callout=("NG","隠蔽・改ざん・後回しは事態を悪化させ、信用を失う。"))
    dk.content("② 事実確認と記録","推測でなく事実を残す",[
        "何が・いつ・どこで・誰に影響したかを確認","事実と推測を分けてメモする","証跡（メール・ログ等）を残す","勝手に消さない・直さない",
    ])
    dk.content("③ 被害の最小化","拡大を止める",[
        "拡大を止める（共有停止・アカウント停止など）","関係者・顧客への影響を確認","上長の指示に従って対応","誠実に・スピーディに動く",
    ])
    dk.divider("02","PART 2","再発防止とケース")
    dk.content("④ 再発防止","個人でなく仕組みを直す",[
        "原因を記録し、チームへ共有","仕組みで防ぐ（チェック・権限・手順の見直し）","個人を責めず、仕組みを改善する","ナレッジとして残す",
    ])
    dk.diagram("flow","CASE ・ メール誤送信","よくある事故①",
        [("①","即報告","気づいたら即、上長へ"),("②","連絡・謝罪","指示に従い相手へ"),
         ("③","記録","送信先・内容を残す"),("④","再発防止","BCC徹底・宛先確認")],
        note="誤送信は“早く言う”ほど傷が浅い。")
    dk.diagram("flow","CASE ・ 情報漏洩の疑い","よくある事故②",
        [("①","すぐ報告","時間が命"),("②","範囲特定","影響範囲を見極める"),
         ("③","拡大防止","措置をとる"),("④","顧客対応","必ず上長と連携")],
        note="情報漏洩はスピードが命。自己判断せず必ず上長と連携する。")
    dk.deepen()
    dk.checklist("CHECK ・ 到達チェック","合格ライン",[
        "初動フロー（即報告→上長→対応）を説明できる","“隠さない”原則を理解している","事実確認と記録ができる","再発防止の考え方を言える",
    ])
    dk.closing("NEXT ・ まとめ","隠さず・早く・正直に",[
        "インシデントは“隠さず早く”が鉄則","目的は被害の最小化と再発防止","確認テスト（G5）で理解度をチェック",
    ], "（社内のインシデント報告フローを確認）","")

def build_claim(dk):
    dk.tag="G6 クレーム対応"
    dk.cover("G6","リスク・コンプラ","クレーム対応","一次対応の“型”で信頼を守る","1時間")
    dk.content("GOAL ・ このモジュールのゴール","読み終えたらできること",[
        "クレーム一次対応の型を説明できる","『傾聴→謝意→事実確認→代替案→上長連携』を実践できる","やってはいけないNG対応を避けられる",
    ], numbered=True, callout=("POINT","クレームは“ピンチ”であり“信頼回復のチャンス”でもある。"))
    dk.divider("01","PART 1","一次対応の型")
    dk.flow("FLOW ・ 一次対応の型","この順で対応する",[
        ("1","傾聴","最後まで遮らず聞く"),("2","謝意","不快にさせたことへ"),("3","事実確認","何が起きたか確認・記録"),("4","代替案/連携","できる範囲＋上長へ"),
    ], "まず感情を受け止め、その後で事実と解決に移る。")
    dk.content("① 傾聴と謝意","まず受け止める",[
        "最後まで遮らずに聞く","相手の感情を受け止める","不快にさせたことへ謝意（全面謝罪とは区別）","言い訳・反論をしない",
    ], callout=("NG","最初から反論・言い訳をすると、火に油を注ぐ。"))
    dk.content("② 事実確認","推測でなく事実",[
        "何が・いつ・どうなったかを確認","推測でなく事実をメモし復唱","不明点は持ち帰る","記録を残す",
    ])
    dk.content("③ 代替案と上長連携","抱え込まない",[
        "できる範囲で代替案を提示","即決できないことは約束しない","自分で抱えず上長へ連携","対応後に報告し再発防止へ",
    ])
    dk.divider("02","PART 2","心構えとケース")
    dk.compare("CASE ・ NG / OK","対応で印象が変わる",
        ("やってはいけない",["言い返す・反論する","言い訳を並べる","たらい回しにする","放置する"]),
        ("正しい一次対応",["最後まで傾聴する","共感し謝意を示す","事実を確認・記録する","代替案＋上長連携"]))
    dk.content("MIND ・ クレームの捉え方","ピンチをチャンスに",[
        "クレーム＝サービス改善のヒント","感情的な相手にも落ち着いて対応","一人で抱え込まない","記録して上長・チームへ共有",
    ])
    dk.deepen()
    dk.checklist("CHECK ・ 到達チェック","合格ライン",[
        "一次対応の型を順番どおり言える","傾聴→謝意の順を守れる","NG対応を避けられる","上長連携・再発防止ができる",
    ])
    dk.closing("NEXT ・ まとめ","傾聴→謝意→事実→代替案→連携",[
        "型＝傾聴→謝意→事実確認→代替案→上長連携","クレームは信頼回復のチャンス","確認テスト（G6）で理解度をチェック",
    ], "（社内のクレーム対応フローを確認）","")

def build_present(dk):
    dk.tag="C4 プレゼン資料作成"
    dk.cover("C4","PC・ツール","プレゼン資料の作り方","“伝わって・動いてもらえる”資料をつくる","1時間")
    dk.content("GOAL ・ このモジュールのゴール","読み終えたらできること",[
        "1スライド1メッセージで資料を作れる","結論ファーストで構成を組める","図解・配色・余白で“見やすく”できる",
    ], numbered=True, callout=("POINT","資料の目的は“きれい”ではなく“伝わって相手が動く”こと。"))
    dk.divider("01","PART 1","中身（構成）が9割")
    dk.content("① 目的と相手を決める","作る前に決めること",[
        "誰に・何をしてほしいか（ゴール）を最初に決める","相手の知識レベルに合わせる","1資料＝1ゴールに絞る","“読む資料”か“話す資料”かで作り分ける",
    ], callout=("POINT","作り始める前に“ゴールと相手”。ここで9割決まる。"))
    dk.diagram("flow","② 構成：結論ファースト","流れで納得させる（PREP）",
        [("結論","Point","まず言いたいこと"),("根拠","Reason","なぜそう言えるか"),
         ("詳細","Example","具体例・データ"),("まとめ","Point","だから何？に答える")],
        note="迷ったらPREP。結論を先に、理由と具体で支える。")
    dk.content("③ 情報を絞る","足し算でなく引き算",[
        "1スライドの要素は3〜5個まで","文章でなくキーワードで","1スライド＝1メッセージ","“あると親切”は思い切って削る",
    ])
    dk.divider("02","PART 2","見た目（デザイン）")
    dk.content("④ レイアウトと余白","視線を設計する",[
        "余白を恐れない（詰め込まない）","視線はZ型／F型に流れる","要素を揃える（整列）・関連を近づける（グルーピング）","強調は1スライドに1つだけ",
    ], callout=("POINT","“揃える・余白・1強調”で素人っぽさが消える。"))
    dk.content("⑤ 配色とフォント","読みやすさが最優先",[
        "色は3色まで（ベース／メイン／アクセント）","アクセント色は“強調したい所”だけに","読みやすいフォント・十分な文字サイズ（本文は大きめ）","背景と文字のコントラストを確保",
    ])
    dk.content("⑥ 図解・チャート","文字より図で伝える",[
        "プロセス→矢印、比較→表、割合→グラフ","1グラフ＝1メッセージ（言いたいことを際立たせる）","不要な装飾・3D・影は削る","アイコンで直感的に",
    ])
    dk.compare("CASE ・ NG / OK の資料","同じ内容でも伝わり方が激変",
        ("伝わらない資料",["文字びっしり・箇条書きだらけ","色が多すぎて主役が不明","結論が最後にしか出てこない","1枚に詰め込みすぎ"]),
        ("伝わる資料",["1スライド1メッセージ","色は3色・強調は1つ","結論ファースト","図解と余白で直感的"]))
    dk.content("⑦ 話し方（デリバリー）","資料は“話す”ためにある",[
        "スライドを読み上げない（要点を話す）","結論から話す","間と強弱をつける","相手の反応を見て調整",
    ])
    dk.content("AI活用で時短","たたき台はAIに",[
        "構成案・アウトラインをAIに出させる","文章の要約・言い換え・タイトル案","誤字・体裁のチェック","ただし事実・数字は必ず自分で確認（AI活用ガイド参照）",
    ], callout=("POINT","AIで“速く8割”、仕上げと事実確認は自分で。"))
    dk.work("WORK ・ 演習","ダメ資料を1枚リデザイン","ゴチャゴチャした1枚を「1メッセージ・余白・図解・3色」で作り直す","提示するビフォー資料を使用","改善ポイントをビフォー/アフターで説明する")
    dk.deepen()
    dk.checklist("CHECK ・ 到達チェック","合格ライン",[
        "1スライド1メッセージで作れる","結論ファーストで構成できる","色3色・余白・整列を守れる","図解で“伝わる”資料にできる",
    ])
    dk.closing("NEXT ・ まとめ","中身（構成）× 見た目（デザイン）",[
        "伝わる資料＝結論ファースト × 1メッセージ × 図解・余白","迷ったら“1枚1メッセージ・結論先・3色・余白”","次：C8 営業資料・提案資料の作り方",
    ], "ザ・プレゼン大学（YouTube教材タブ参照）","youtube.com/@tpu")


def build_logical(dk):
    dk.tag="D1 ロジカル/クリティカル"
    dk.cover("D1","思考・分析","ロジカル / クリティカルシンキング","筋道立てて考え、前提を疑う力","1時間")
    dk.content("GOAL ・ このモジュールのゴール","読み終えたらできること",[
        "MECE・ロジックツリーで課題を分解できる","結論ファースト（ピラミッド構造）で主張できる","“前提を疑う”クリティカルな視点を持てる",
    ], numbered=True, callout=("POINT","思考の“型”を持つと、速く・深く・伝わる考えができる。"))
    dk.divider("01","PART 1","ロジカルシンキング")
    dk.content("ロジカルシンキングとは","筋道を通す思考",[
        "主張に“根拠”と“筋道”をつけること","話が飛ばない・ヌケモレがない","相手が納得・再現できる","感覚でなく構造で考える",
    ], callout=("POINT","“なんとなく”を“だからこう”に変える技術。"))
    dk.content("MECE","モレなく・ダブりなく",[
        "Mutually Exclusive（ダブりなし）","Collectively Exhaustive（モレなし）","切り口を決めて分ける（例：新規/既存、年代別）","ヌケると見落とし、ダブると非効率",
    ], callout=("POINT","“切り口”を先に決めるとMECEになりやすい。"))
    dk.content("ロジックツリー","課題を分解する",[
        "Whyツリー：原因を掘る（なぜ？を繰り返す）","Howツリー：打ち手を広げる（どうやって？）","上位→下位へMECEに分岐","“どこに効くか”を特定できる",
    ])
    dk.diagram("pyramid","ピラミッド構造","結論から伝える",
        [("結論","頂点に言いたいこと（So What?で上へ）"),("根拠","結論を支える理由（Why So?で検証）"),("事実・データ","根拠の裏づけ＝土台")],
        note="結論→根拠→データ。上下が論理でつながっているか確認。PREPと同じ“結論ファースト”。")
    dk.diagram("pyramid","主張・根拠・データ（三角ロジック）","説得力の最小単位",
        [("主張","言いたいこと"),("根拠","なぜそう言えるか"),("データ","事実・数字の裏づけ")],
        note="3つが揃って初めて“筋が通る”。")
    dk.divider("02","PART 2","クリティカルシンキング")
    dk.content("クリティカルシンキングとは","前提を疑う思考",[
        "“本当にそう？”と問い直す","与えられた前提・常識を鵜呑みにしない","感情・思い込みと事実を分ける","より良い結論にたどり着くための姿勢",
    ], callout=("POINT","批判＝否定ではなく“健全な問い直し”。"))
    dk.diagram("flow","STEP ・ 3つの問い","クリティカルに考える",
        [("①","論点","そもそもイシューは何か"),("②","根拠・データ","十分で正しいか"),("③","他の見方","反論はないか")],
        note="この3問で思考の穴が見える。")
    dk.content("注意すべきバイアス","思考のワナ",[
        "確証バイアス（都合の良い情報だけ集める）","思い込み・先入観","平均の罠・少数事例の一般化","“みんな言ってる”に流される",
    ], callout=("NG","“自分は正しい”と思い込んだ瞬間に思考は止まる。"))
    dk.content("実務での使いどころ","CAの仕事で活きる",[
        "提案：主張→根拠→データで説得","原因分析：Whyツリーで真因を探す","意思決定：他の選択肢と比較","求職者支援：本当の悩み（論点）を見極める",
    ])
    dk.work("WORK ・ 演習","課題をロジックツリーで分解しよう","『紹介の内定承諾率を上げるには？』をHowツリーで分解","ヒント：MECEな切り口で2〜3段","出た打ち手から“どこに効くか”を1つ選ぶ")
    dk.deepen()
    dk.checklist("CHECK ・ 到達チェック","合格ライン",[
        "MECEに切り口を分けられる","ロジックツリーで分解できる","結論ファースト（ピラミッド）で話せる","前提を疑う3つの問いを使える",
    ])
    dk.closing("NEXT ・ まとめ","構造で考え、前提を疑う",[
        "ロジカル＝筋道（MECE・ツリー・ピラミッド）","クリティカル＝前提を疑う3つの問い","次：D5 仮説思考 ／ D6 論点思考 ／ D8 フェルミ推定",
    ], "10分で学ぶ『ロジカルシンキング』（YouTube教材タブ参照）","youtube.com/@gakushi-salon")

def build_hypothesis(dk):
    dk.tag="D5 仮説思考"
    dk.cover("D5","思考・分析","仮説思考","先に“仮の答え”を立て、速く前進する","1時間")
    dk.content("GOAL ・ このモジュールのゴール","読み終えたらできること",[
        "仮説思考の意味と効果を説明できる","少ない情報でも仮説を立てられる","仮説→検証のループで速く進められる",
    ], numbered=True, callout=("POINT","“とりあえず仮の答え”を置くと、思考のスピードが上がる。"))
    dk.divider("01","PART 1","仮説思考とは")
    dk.content("仮説思考とは","先に結論を仮置きする",[
        "先に“仮の答え（結論）”を置いて動く","全部調べてから決めない","逆算で“必要な情報だけ”集める","間違えたら修正すればよい",
    ], callout=("POINT","網羅してから考えるのでなく、仮説を立てて検証する。"))
    dk.content("なぜ速くなるのか","スピードと精度の両立",[
        "調査の的が絞れる（無駄を省く）","議論・行動が前に進む","早く検証 → 早く学べる","完璧主義の停滞を防ぐ",
    ])
    dk.divider("02","PART 2","立て方と検証")
    dk.diagram("flow","STEP ・ 仮説の立て方","現時点のベストを言い切る",
        [("①","今のベストを置く","情報が少なくても言い切る"),("②","So What?","だから何で一歩踏み込む"),
         ("③","別の可能性も","反対意見・他の見方も考える"),("④","検証できる形に","具体的な形にする")],
        note="情報が少なくても“今のベスト”を言い切り、検証できる具体に落とす。")
    dk.diagram("cycle","CYCLE ・ 仮説→検証→修正","当てるより速く回す",
        ["仮説を立てる","小さく早く検証","事実で確かめ修正"],
        note="仮説は“当てる”より“速く回す”もの。外れても前進。")
    dk.content("実務での使いどころ","CAの仕事で",[
        "原因の仮説：「たぶんここが原因」","提案の仮説：「この求人が合いそう」","面談前の仮説：「この学生はこう悩んでいそう」","検証して提案の精度を上げる",
    ])
    dk.work("WORK ・ 演習","仮説→検証計画を立てよう","『最近、面談後の紹介辞退が増えた』の原因仮説を3つ＋検証方法","ヒント：思いつく原因を仮説として言い切る","仮説 → 根拠 → 検証方法 の順で")
    dk.deepen()
    dk.checklist("CHECK ・ 到達チェック","合格ライン",[
        "仮説思考の意味を説明できる","少ない情報でも仮説を立てられる","検証で仮説を修正できる","外れを恐れず速く回せる",
    ])
    dk.closing("NEXT ・ まとめ","仮の答え→検証で前進",[
        "仮説思考＝先に仮の答え、検証で精度を上げる","外れてOK、速く回す","次：D6 論点思考 ／ D7 問題解決力",
    ], "（『仮説思考』内田和成・課題図書タブ参照）","")

def build_issue(dk):
    dk.tag="D6 論点思考"
    dk.cover("D6","思考・分析","論点思考","“解くべき問い”を見極めてから考える","1時間")
    dk.content("GOAL ・ このモジュールのゴール","読み終えたらできること",[
        "論点（イシュー）とは何か説明できる","与件から“本当の論点”を絞れる","論点を間違えない",
    ], numbered=True, callout=("POINT","正しい問いに60点 ＞ 間違った問いに100点。"))
    dk.divider("01","PART 1","論点とは")
    dk.content("論点（イシュー）とは","いま答えを出すべき問い",[
        "今この場で“答えを出すべき問い”","論点を間違えると努力が全部ムダになる","「何を考えるか」が「どう考えるか」より先","良い論点＝答えが出せて、インパクトが大きい",
    ], callout=("POINT","作業を始める前に「本当に解くべき問いは何か」。"))
    dk.content("論点を間違える例","ありがちな失敗",[
        "手段が目的化（資料を作ること自体が目的に）","些末な論点に時間を使う","相手の本当の問いとズレている","考えるのが怖くて“作業”に逃げる",
    ])
    dk.divider("02","PART 2","見極め方")
    dk.diagram("flow","STEP ・ 論点の見極め方","問いを問い直す",
        [("①","目的を問う","そもそも何を決めたいか"),("②","Whyで遡る","上位の目的に遡る"),
         ("③","前進で選ぶ","解ければ前進するか"),("④","仮説検証","仮の論点を置いて検証")],
        note="作業を始める前に、まず“本当に解くべき問い”を仮で置いて検証する。")
    dk.diagram("pyramid","TREE ・ 論点ツリー","問いを分解する",
        [("大論点","本当に解くべき問い"),("中論点","MECEに分解する"),("小論点","仮説を持ち着手")],
        note="大→中→小に分解し、インパクトの大きい論点から着手する。")
    dk.content("実務での使いどころ","CAの仕事で",[
        "求職者の“本当の悩み”を見極める（表面の希望でなく）","提案前に「何が決め手か」を定める","会議で「今日の論点は？」と確認","上司相談は論点を先に言う",
    ])
    dk.work("WORK ・ 演習","本当の論点を1つに絞ろう","『内定が出たのに学生が迷っている』。あなたが考えるべき論点は？","ヒント：表面の問いの奥にある問いを探す","表面の問い → 本当の論点 → なぜそれが論点か")
    dk.deepen()
    dk.checklist("CHECK ・ 到達チェック","合格ライン",[
        "論点とは何か説明できる","論点を間違える例を挙げられる","本当の論点を絞れる","論点ツリーで分解できる",
    ])
    dk.closing("NEXT ・ まとめ","正しい問いを立てる",[
        "論点思考＝解くべき問いの見極め","問いを間違えない（作業に逃げない）","次：D7 問題解決力 ／ D8 フェルミ推定",
    ], "（『論点思考』『イシューからはじめよ』課題図書タブ参照）","")

def build_problem(dk):
    dk.tag="D7 問題解決力"
    dk.cover("D7","思考・分析","問題解決力","問題を構造的に解く4ステップ","1時間")
    dk.content("GOAL ・ このモジュールのゴール","読み終えたらできること",[
        "問題＝あるべき姿と現状のギャップ と理解する","Where→Why→Howの手順で解ける","打ち手を優先順位づけできる",
    ], numbered=True, callout=("POINT","問題解決は“型”。手順に沿えば誰でも前に進める。"))
    dk.divider("01","PART 1","問題解決の型")
    dk.content("問題とは","ギャップを捉える",[
        "問題＝“あるべき姿”と“現状”の差","まずギャップを数字で捉える","困りごとを“解ける形”に置き直す","問題設定で半分決まる",
    ], callout=("POINT","“なんとなく困っている”を“具体的な差”に変える。"))
    dk.diagram("flow","FLOW ・ 問題解決の4ステップ","この順で解く",
        [("①","Where","問題はどこか（特定・分解）"),("②","Why","なぜ起きるか（真因）"),
         ("③","How","どう解くか（打ち手）"),("④","Do","実行と振り返り")],
        note="特定→真因→打ち手→実行。この順を飛ばさない。")
    dk.divider("02","PART 2","各ステップ")
    dk.content("① Where ・ 問題特定","どこが悪いかを絞る",[
        "全体を分解して“どこが悪いか”を特定","MECEに分ける","数字の大きい所・効く所から","感覚でなく事実で絞る",
    ])
    dk.content("② Why ・ 真因分析","根っこを掘る",[
        "「なぜ？」を繰り返す（なぜなぜ）","表面の症状でなく根本原因へ","思い込みを疑う（クリティカル）","真因に手を打つ",
    ])
    dk.content("③ How ＋ ④ Do","打ち手と実行",[
        "打ち手を複数出す","インパクト × 実現性で優先順位づけ","まず実行して検証","振り返って改善（PDCA）",
    ], callout=("POINT","“原因に効く打ち手”を選ぶ。対症療法に逃げない。"))
    dk.content("実務での使いどころ","CAの仕事で",[
        "紹介の歩留まり（通過率）改善","自分の数字が出ない原因の分析","業務の非効率を直す","求職者の課題を一緒に解決",
    ])
    dk.work("WORK ・ 演習","4ステップで整理しよう","『面談からの紹介決定率が低い』を Where→Why→How で整理","ヒント：どこが弱いか→なぜか→打ち手","どこが → なぜ → 打ち手を1つ")
    dk.deepen()
    dk.checklist("CHECK ・ 到達チェック","合格ライン",[
        "問題をギャップで定義できる","Where→Why→Howで分解できる","真因に手を打てる","打ち手を優先順位づけできる",
    ])
    dk.closing("NEXT ・ まとめ","Where→Why→How→Do",[
        "問題解決＝特定→真因→打ち手→実行","真因に効く打ち手を選ぶ","次：D8 フェルミ推定 ／ D2 SWOT・3C",
    ], "（『ザ・ゴール』『問題解決』課題図書タブ参照）","")

def build_fermi(dk):
    dk.tag="D8 フェルミ推定"
    dk.cover("D8","思考・分析","フェルミ推定","未知の数を“分解と仮定”で概算する","1時間")
    dk.content("GOAL ・ このモジュールのゴール","読み終えたらできること",[
        "フェルミ推定の意味と価値を理解する","分解→仮定→計算→検算で概算できる","地頭・面接・見積りに使える",
    ], numbered=True, callout=("POINT","答えの正確さより“分解と仮定の筋”が評価される。"))
    dk.divider("01","PART 1","フェルミ推定とは")
    dk.content("フェルミ推定とは","知らない数を概算する",[
        "正確な数を知らなくても概算する","例：日本のコンビニは何店ある？","分解と仮定で論理的に出す","“考える力（地頭）”の筋トレ",
    ], callout=("POINT","正解を知らなくても、筋道で“それっぽい数”を出せる。"))
    dk.content("なぜ役立つのか","実務にも効く",[
        "市場規模・見積りの感覚が持てる","論理的に分解する練習になる","面接（コンサル等）の定番","“数字で語る”力がつく",
    ])
    dk.divider("02","PART 2","解き方")
    dk.diagram("flow","STEP ・ 解き方の型","4ステップで概算する",
        [("①","分解","要素の掛け算に分ける"),("②","仮定","根拠ある数字を置く"),
         ("③","計算","掛け合わせる"),("④","検算","桁・現実性を確認")],
        note="分解 → 仮定 → 計算 → 検算。この順で“それっぽい数”を出す。")
    dk.diagram("formula","例 ・ 日本のカフェ市場規模","“分解 × 仮定”で概算する",
        ("人口 × 飲む割合 × 頻度 × 単価 = 市場規模",
         [("各要素に“仮定”を置く",["人口 ≒ 1.2億人","飲む割合 ≒ 6割","頻度 ≒ 週3回","単価 ≒ 400円"],"仮定の例"),
          ("検算（オーダー）",["桁が現実的か確認","別の解き方で照合","極端な数字でないか"],"検算のコツ")]),
        note="正確さより“分解と仮定の筋”。各要素に根拠ある常識的な数を置き、掛け合わせて概算→桁（オーダー）で検算する。")
    dk.content("仮定の置き方・検算","ズレを防ぐ",[
        "根拠のある仮定（割合・比率・常識）","極端な数字でないか確認","別の解き方で照合する","桁（オーダー）が現実的か",
    ])
    dk.work("WORK ・ 演習","概算してみよう","『日本で年間に就活する新卒は何人？』を概算","ヒント：大学等の卒業者数 × 就活する割合 など","分解 → 仮定 → 計算 → 検算")
    dk.deepen()
    dk.checklist("CHECK ・ 到達チェック","合格ライン",[
        "フェルミ推定の意味を説明できる","分解→仮定→計算→検算で解ける","根拠ある仮定を置ける","桁で現実性を検算できる",
    ])
    dk.closing("NEXT ・ まとめ","分解 × 仮定で概算する",[
        "フェルミ＝未知を分解と仮定で概算","数字で考える癖をつける","次：D2 SWOT・3C などの分析へ",
    ], "（『地頭力を鍛える』課題図書タブ参照）","")

def build_analysis(dk):
    dk.tag="D2 ビジネス分析"
    dk.cover("D2","思考・分析","ビジネス分析（SWOT / 3C）","フレームワークで現状を正しく捉える","1時間")
    dk.content("GOAL ・ このモジュールのゴール","読み終えたらできること",[
        "3C・SWOTの使い方を説明できる","担当企業を分析できる","分析を“打ち手・提案”につなげられる",
    ], numbered=True, callout=("POINT","フレームワークは“埋める”のが目的でなく“示唆を出す”ため。"))
    dk.divider("01","PART 1","フレームワークの基本")
    dk.content("フレームワークとは","思考の型",[
        "抜け漏れを防ぎ、速く整理できる","共通言語でチームと議論できる","“使うこと”でなく“示唆を出すこと”が目的","代表：3C／SWOT／4P／PEST",
    ], callout=("POINT","埋めて満足しない。“だから何が言えるか”まで。"))
    dk.diagram("relation","3C分析","勝ち筋を見つける",
        ("勝ち筋", ["Customer","Competitor","Company"]),
        note="市場・競合・自社の3つを見て、その重なりに“勝ち筋”を見つける。")
    dk.content("SWOT分析","現状を4象限で",[
        "強み(S)・弱み(W)＝内部要因","機会(O)・脅威(T)＝外部要因","事実ベースで埋める","“良い悪い”でなく事実を整理",
    ])
    dk.quadrant("図解 ・ SWOT","SWOT分析（4象限）",
        "プラス要因（左）／ マイナス要因（右）","↑ 内部 ／ 外部 ↓",
        [("S 強み","自社の強み・資源（内部×プラス）",True),
         ("W 弱み","自社の弱み・課題（内部×マイナス）",False),
         ("O 機会","市場の追い風（外部×プラス）",False),
         ("T 脅威","市場の逆風（外部×マイナス）",False)],
        "内部(S/W)×外部(O/T)で整理し、クロスSWOTで掛け合わせて打ち手に変える。")
    dk.content("クロスSWOT","分析を打ち手に変える",[
        "強み×機会＝積極的に攻める","強み×脅威＝強みで守る","弱み×機会＝弱みを克服して活かす","弱み×脅威＝撤退・回避",
    ], callout=("POINT","SWOTは並べて終わりでなく、掛け合わせて打ち手に。"))
    dk.divider("02","PART 2","実務で使う")
    dk.content("知っておく他のフレーム","引き出しを増やす",[
        "4P（製品・価格・流通・販促）","PEST（政治・経済・社会・技術）","ファイブフォース（業界の競争構造）","ロジックツリー（D1）と組み合わせる",
    ])
    dk.content("CAの仕事での活用","提案の武器に",[
        "担当企業を3C/SWOTで分析し魅力と課題を把握","求職者への提案の“根拠”にする","企業の勝ち筋・成長性を語れる","業界×職種タブと併用",
    ])
    dk.work("WORK ・ 演習","企業を分析しよう","担当（or 興味のある）企業を3CまたはSWOTで分析","ヒント：事実ベースで各要素を埋める","出た示唆から“この企業の魅力”を1つ言語化")
    dk.deepen()
    dk.checklist("CHECK ・ 到達チェック","合格ライン",[
        "3Cの3要素を説明できる","SWOTを4象限で整理できる","クロスSWOTで打ち手を出せる","分析を提案につなげられる",
    ])
    dk.closing("NEXT ・ まとめ","フレームで示唆を出す",[
        "3C＝市場/競合/自社、SWOT＝内部×外部","並べるだけでなく“だから何”まで","次：C7 AI活用 ／ C8 営業資料の作り方",
    ], "MECE・ロジックツリー（グロービス・YouTube教材タブ参照）","globis.jp")

def build_sales_doc(dk):
    dk.tag="C8 営業資料作成"
    dk.cover("C8","PC・ツール","営業資料・提案資料の作り方","“課題→解決→根拠→価格”で相手を動かす","1時間")
    dk.content("GOAL ・ このモジュールのゴール","読み終えたらできること",[
        "提案資料の基本構成を説明できる","相手の課題起点で資料を作れる","1スライド1メッセージで提案できる",
    ], numbered=True, callout=("POINT","提案資料は“自分が言いたいこと”でなく“相手の課題”起点。"))
    dk.divider("01","PART 1","提案の型")
    dk.content("提案資料とは","意思決定を促す資料",[
        "相手（企業/求職者）の意思決定を後押しする","主役は“相手の課題とメリット”","結論＝相手にとっての価値","プレゼン基礎（C4）の応用",
    ])
    dk.diagram("flow","FLOW ・ 基本構成（ストーリー）","相手の頭の順番で",
        [("①","現状・課題","相手ごとに言語化"),("②","解決策","提案として示す"),("③","根拠","実績・事例・データ"),
         ("④","価格・条件","分かりやすく明示"),("⑤","Next","次のアクション")],
        note="課題 → 解決 → 根拠 → 価格 → Next。これが基本の流れ。")
    dk.content("課題起点で作る","刺さる入口",[
        "ヒアリングで相手の課題を掴む","相手の言葉で課題を書く","1枚目で“課題の言語化”","提案は課題への回答として示す",
    ])
    dk.divider("02","PART 2","効く資料にする")
    dk.content("根拠で信頼をつくる","“なぜ選ぶべきか”",[
        "実績・事例（ビフォーアフター）","数字・データ","第三者の声・推薦","想定リスクへの先回り",
    ])
    dk.content("見せ方（C4の応用）","読みやすさで差",[
        "1スライド1メッセージ","図解・比較表で直感的に","価格は分かりやすく明示","余白・整列・3色",
    ], callout=("POINT","内容が良くても“見づらい”と伝わらない。C4の原則を適用。"))
    dk.content("CAの仕事での提案","どこで使うか",[
        "企業へ：この求職者を採用すべき理由","求職者へ：この求人の魅力（紹介）","社内へ：改善・企画の提案","※企業紹介文は社内の正本フォーマット（F3）に従う",
    ])
    dk.content("AI活用で時短","たたき台はAIに",[
        "構成・アウトラインをAIに出させる","言い回しのブラッシュアップ","ただし実績・数字は自分で用意・確認","（AI活用ガイド参照）",
    ])
    dk.work("WORK ・ 演習","提案資料を1枚作ろう","『ある企業へ、この学生を採用すべき理由』を1枚で提案","構成：課題（企業の採用課題）→ 解決（この学生）→ 根拠 → Next","C4の原則（1メッセージ・余白・図解）も適用")
    dk.deepen()
    dk.checklist("CHECK ・ 到達チェック","合格ライン",[
        "提案の基本構成を説明できる","相手の課題起点で作れる","根拠で信頼をつくれる","1スライド1メッセージで見せられる",
    ])
    dk.closing("NEXT ・ まとめ","相手の課題から始める",[
        "提案＝課題→解決→根拠→価格→Next","主役は相手のメリット","次：C9 Gmail活用 ／ C10 おすすめ拡張機能",
    ], "ザ・プレゼン大学（YouTube教材タブ参照）","youtube.com/@tpu")

def build_ai_use(dk):
    dk.tag="C7 AI活用"
    dk.cover("C7","PC・ツール","AIの使い方講座","“どこよりもAIを使い倒す”を自分のものに","1.5時間")
    dk.content("GOAL ・ このモジュールのゴール","読み終えたらできること",[
        "世界と日本のAI活用の現在地を説明できる","チャットとエージェントの違いを理解する","プロンプトの型で精度高く使える","Cowork（AIエージェント）で実務をやり切れる",
    ], numbered=True, callout=("POINT","ゴールは“AIエージェントを日常業務で使える”こと。"))

    dk.divider("00","PART 0","あなたはAIを使っていますか？")
    dk.content("問いかけ","“使うか”ではなく“使いこなすか”",[
        "毎日触る人とたまに使う人で、1年後に大差がつく","調べる・書く・まとめる・作るはAIと一緒の時代","“賢い新人アシスタント”を毎日となりに置ける","問題は“使うか”でなく“どこまで使いこなすか”",
    ], callout=("POINT","AIは知っているだけでは無意味。毎日使う人が伸びる。"))

    dk.divider("01","PART 1","世界と日本の現在地")
    dk.barchart("DATA ・ 企業のAI業務利用率","日本は主要国に大きく後れている",[
        ("中国",0.958,"95.8%",False),("米国",0.906,"90.6%",False),("ドイツ",0.903,"90.3%",False),("日本",0.552,"55.2%",True),
    ],"何らかの業務で生成AIを利用する企業の割合。出典：総務省『令和7年版 情報通信白書』(2025)")
    dk.content("個人利用はさらに差が開く","“使い方がわからない”が最大の壁",[
        "個人の生成AI利用：日本26.7%（前回比 約3倍）","中国81.2%／米国68.8%／ドイツ59.2%","使わない理由1位は『効果的な活用法がわからない』","出典：総務省『令和7年版 情報通信白書』(2025)",
    ], callout=("POINT","遅れている＝伸びしろ。使い方を覚えた人が抜ける。"))

    dk.divider("02","PART 2","AIで業務はどう変わる")
    dk.statcards("DATA ・ 仕事はどう変わる","作業はAIへ、人は判断・対人へ",[
        ("60–70%","労働時間が自動化可能","McKinsey"),
        ("2.6–4.4兆$","生成AIの年間価値","McKinsey"),
        ("+7,800万","2030年の純増雇用","WEF 2025"),
        ("59%","要リスキリング","WEF 2025"),
    ],"出典：McKinsey／WEF Future of Jobs 2025。作業を奪われるのではなく、“作業から解放され”判断・対人・付加価値に集中できる。")
    dk.content("“持っている”だけでは差がつかない","使いこなす側に回る",[
        "AIを使う組織は88%・成果を出せたのは6%だけ（McKinsey）","差は“ツールの有無”でなく“業務への組み込み方”","最も使われるのは生成タスク（Anthropic 2026/1）","CAのリサーチ・資料・要約・下書きにも組み込める",
    ], callout=("POINT","成果を出す6%になる＝使いこなして業務に組み込む。"))

    dk.divider("03","PART 3","チャットとエージェント")
    dk.diagram("before_after","Chat と Agent の違い","“答える”から“やり切る”へ",
        (("Chat：1往復で答える","相談する先輩。質問→回答で完結"),
         ("Agent：ゴールを渡すと自走","動く新人。ツールを操作し成果物まで")),
        note="Chat＝助言する先輩／Agent＝仕事を片付ける新人。違いは“自分で手を動かすか”。")
    dk.cards("Claudeの3つの顔","用途で使い分ける（新卒の主武器はCowork）",[
        ("Chat","claude.ai","聞けば答える汎用AI。相談・下書き・要約・学習に。"),
        ("Cowork","デスクトップ","ゴールを渡すとファイル仕事を“完成物”にする秘書。新卒がまず使う。"),
        ("Code","ターミナル","開発者向けの自走エージェント。最も高度。"),
    ],"ゴール＝Cowork（エージェント）を日常業務で使えるようになること。")

    dk.divider("04","PART 4","使い方の基本")
    dk.diagram("flow","FLOW ・ プロンプトの型","精度が上がる書き方",
        [("役割","立場を与える","「あなたは〜の専門家」"),("文脈","前提を渡す","背景・前提・制約を共有"),
         ("指示","やることを明確に","何をしてほしいか具体化"),("形式","出力形を指定","表/箇条書き/字数"),("例","お手本を渡す","欲しい出力の例を添える")],
        note="役割＋文脈＋指示＋形式（＋例）の順で組み立てると精度が上がる。")
    dk.content("業務での使いどころ","CAの仕事で",[
        "企業リサーチ／紹介文の下書き／メール作成","議事録の要約／面談準備の質問出し","企画の壁打ち・批判／学習・言い換え","※具体プロンプトは「AI活用ガイド」タブ参照",
    ])
    dk.content("注意点（セキュリティ）","やってはいけない",[
        "求職者の氏名・連絡先を貼らない（仮名化）","社外秘・機密を入れない","出力の事実・数字は必ず自分で確認","著作権・引用に注意",
    ], callout=("NG","個人情報・機密をそのまま貼るのは厳禁。漏洩リスク。"))

    dk.divider("05","PART 5","Coworkでエージェントを使う")
    dk.content("Cowork とは","“指示すると、完成物を返す”AIエージェント",[
        "Claudeデスクトップの「Cowork」＝知的労働のエージェント","自分のフォルダ/ファイルを直接読み書きする","Excel・PPT・Word・PDFを“実物で”作る","macOS/Windows・有料プラン（Pro 約$17/月〜）",
    ], callout=("POINT","“離席している間に資料ができている”が現実になる。"))
    dk.flow("FLOW ・ Coworkの始め方","5ステップで動かす",[
        ("1","アプリを開く","Claude Desktopで「Cowork」タブへ"),("2","フォルダを許可","作業フォルダを接続して権限を許可"),
        ("3","ゴールを指示","やってほしい作業を文章で渡す"),("4","計画を承認","手順を確認してから実行（削除等は必ず承認）"),("5","成果物を受領","完成ファイル＋作業サマリを受け取る"),
    ], "重要な判断は人が承認＝HITL。安全に任せ、最後は自分が確認する。")
    dk.content("Skillで“自分のエージェント”を作る","よく使う作業を保存して再利用",[
        "Skill＝Coworkに“やり方”を教える再利用ワークフロー","毎回説明せずワンコマンドで同じ品質を呼べる","『Skill Creator』で自作・改善・評価ができる","例：紹介文ドラフト／面談要約／月次集計を自分専用化",
    ], callout=("POINT","一度作れば毎回効く＝“自分専用のAI部下”が増える。"))
    dk.work("WORK ・ 演習","Coworkで“集計エージェント”を作る","「関数練習」タブのデータをCoworkに渡し、月次集計レポート（承諾率・企業別件数・売上合計）をスプレッドシートで作らせる","まず自分が「関数ワーク」タブのQUERYで手集計し、Coworkの出力と突き合わせて検証する","数字が合えばSkillとして保存＝再利用できる“自分専用の集計エージェント”になる")
    dk.deepen()
    dk.checklist("CHECK ・ 到達チェック","合格ライン",[
        "世界と日本のAI活用の差を数字で言える","チャットとエージェントの違いを説明できる","Chat/Cowork/Codeを使い分けられる","Coworkでやり切り、必ず検証できる",
    ])
    dk.closing("NEXT ・ まとめ","“使いこなす側”に回る",[
        "日本は遅れている＝今が伸びしろ。覚えた人が抜ける","Chat＝相談／Cowork＝作業を完了／Code＝開発を自走","ゴールはCowork（エージェント）を日常で使い倒すこと","出典：総務省 情報通信白書／McKinsey／WEF（各スライド明記）",
    ], "Claude Cowork 公式／社内AI活用ガイド","anthropic.com/product/claude-cowork")

def build_gmail(dk):
    dk.tag="C9 Gmail活用"
    dk.cover("C9","PC・ツール","Gmail活用","受信箱を“制御”して仕事を速くする","1時間")
    dk.content("GOAL ・ このモジュールのゴール","読み終えたらできること",[
        "ラベル／フィルタ／検索で整理できる","署名・テンプレで定型を高速化できる","受信箱を溜めない運用ができる",
    ], numbered=True, callout=("POINT","メールは“処理するもの”。仕組みで速く・漏らさない。"))
    dk.content("① 整理：ラベルとフィルタ","自動で仕分ける",[
        "ラベルで分類（求職者／企業／社内）","フィルタで自動振り分け","スター／重要マークで優先","アーカイブで受信箱を空に保つ",
    ])
    dk.content("② 速さ：検索とショートカット","探す時間をゼロに",[
        "検索演算子（from: to: has:attachment 期間）","ショートカット有効化（c=作成, e=アーカイブ 等）","既読/未読を使い分け","ラベル横断で一発検索",
    ], callout=("POINT","“探す”をやめる。検索演算子＋ラベルで即到達。"))
    dk.content("③ 定型：署名・テンプレ","同じ文章は作らない",[
        "署名を設定（社名・氏名・連絡先）","テンプレート（定型文）で返信を高速化","予約送信・スヌーズを活用","よく使う文面を保存",
    ])
    dk.diagram("flow","FLOW ・ ④ 受信箱ゼロの習慣","見たメールは即“振り分け”て溜めない",
        [("即処理","2分で返す","その場で返信して完了"),("委任","人に渡す","担当へ転送・依頼する"),("保留","スター/スヌーズ","後で対応する印を付ける")],
        note="重要を見逃さない通知設定を。見たメールは必ず3つのどれかに振り分け、受信箱を空に保つ。")
    dk.content("注意点","事故を防ぐ",[
        "誤送信防止（宛先は最後・送信取り消しON）","個人情報の取扱いに注意","公私のアカウントを分ける","BCCの徹底（一斉送信）",
    ], callout=("NG","誤送信・CC漏洩は信用問題。送信前に宛先を再確認。"))
    dk.work("WORK ・ 演習","Gmailを整える","①求職者／企業用のラベル＋自動振り分けフィルタを設定する","②返信テンプレ（定型文）と“署名”（社名・氏名・連絡先）を設定する","設定した内容を説明できればOK（設定→フィルタ／テンプレート／署名）")
    dk.deepen()
    dk.checklist("CHECK ・ 到達チェック","合格ライン",[
        "ラベル・フィルタで整理できる","検索演算子で素早く探せる","署名・テンプレを設定できる","受信箱を溜めない運用を言える",
    ])
    dk.closing("NEXT ・ まとめ","整理 × 定型 × 検索",[
        "Gmailは仕組みで速くなる","受信箱を溜めない・誤送信しない","次：C10 おすすめ拡張機能",
    ], "（Gmail公式ヘルプを参照）","")

def build_ext(dk):
    dk.tag="C10 拡張機能"
    dk.cover("C10","PC・ツール","おすすめ拡張機能","ブラウザを“仕事の道具”に最適化する","1時間")
    dk.content("GOAL ・ このモジュールのゴール","読み終えたらできること",[
        "業務効率化の拡張を安全に使える","用途を説明できる","入れすぎ・危険な拡張を避けられる",
    ], numbered=True, callout=("POINT","拡張は“小さな相棒”。安全に、必要な分だけ。"))
    dk.content("拡張機能とは","ブラウザを強化する",[
        "ブラウザ（Chrome等）に機能を追加する","効率化の小さな相棒","公式ストアから入れる","入れすぎは重くなる・リスク増",
    ])
    dk.diagram("relation","おすすめカテゴリ","用途で選ぶ",
        ("拡張機能",["画面分割","スクショ","翻訳・要約","パスワード","メモ/クリップ","AI補助"]),
        note="集中・共有・リサーチ・時短。用途で選んで必要な分だけ入れる。")
    dk.content("業務での活用例","CAの仕事で",[
        "リサーチを速く（翻訳・要約）","スクショで素早く共有","タブ整理で集中力キープ","定型入力・スニペットで時短",
    ])
    dk.content("安全に使う（最重要）","リスク管理",[
        "公式ストア・評価・更新状況を確認","要求“権限”を確認（過剰要求は警戒）","会社の許可・セキュリティポリシーに従う","個人情報を抜く悪質拡張に注意",
    ], callout=("NG","怪しい拡張は情報漏洩の入口。許可と権限を必ず確認。"))
    dk.work("WORK ・ 演習","拡張を1つ安全に導入","推奨拡張を1〜2個入れて用途を説明","導入時に“要求された権限”を確認する","会社のポリシーに沿っているかチェック")
    dk.deepen()
    dk.checklist("CHECK ・ 到達チェック","合格ライン",[
        "拡張機能の役割を説明できる","用途別に選べる","権限・公式性を確認できる","会社ポリシーに従える",
    ])
    dk.closing("NEXT ・ まとめ","安全に・必要な分だけ",[
        "拡張は効率化の相棒","権限とポリシーを必ず確認","Stage2修了 → Stage3 実務（面談・CA特化）へ",
    ], "（会社の許可・ポリシーを確認）","")

def build_interview(dk):
    dk.tag="F1 面談スキル"
    dk.cover("F1","CA職種特化","面談スキル","本音を引き出し、納得の意思決定を支える","1.5時間")
    dk.content("GOAL ・ このモジュールのゴール","読み終えたらできること",[
        "面談の型（オープニング〜クロージング）を実演できる","傾聴と質問で本音・価値観・不安を引き出せる","学生が“自分で納得して”決められるよう導ける",
    ], numbered=True, callout=("POINT","面談はゴールではなく、学生の人生の意思決定を支える場。"))
    dk.divider("01","PART 1","面談の全体像")
    dk.content("面談の目的とCAの役割","売り込む場ではない",[
        "学生の自己理解を助け、選択肢を広げる","信頼関係（ラポール）を築くのが土台","求人を押し込む場ではない","内定承諾は“結果”、本質は納得した意思決定の支援",
    ], callout=("POINT","“この人になら本音を話せる”と思ってもらうのが第一歩。"))
    dk.flow("FLOW ・ 面談の流れ","型を持てば聞き漏らさない",[
        ("1","アイスブレイク","場を和ませ・ラポール形成"),("2","ヒアリング","現状・価値観・不安を引き出す"),
        ("3","情報提供／提案","価値観に紐づけ選択肢を渡す"),("4","ネクスト合意","次の一歩と期限をすり合わせ"),
    ], "型を持つと緊張せず、聞き漏らさない。各ステップの“目的”を意識する。")
    dk.divider("02","PART 2","引き出す技術")
    dk.diagram("relation","HEARING ・ ヒアリングの観点","“何を聞くか”の軸を持つ",
        ("本音・軸", ["Will やりたい","Can できる","Must 求められる","価値観・譲れない軸","不安・本音","制約条件"]),
        note="6つの観点を“求職者の本音・軸”を中心に据えて引き出す。")
    dk.content("質問のテクニック","広げて、深めて、確認する",[
        "オープンクエスチョン（なぜ／どんな）で広げる","「具体的には？」「他には？」で深掘り","クローズドで事実確認・合意を取る","沈黙を恐れない（考える時間を奪わない）",
    ], callout=("POINT","良い質問は答えではなく“気づき”を生む。"))
    dk.content("傾聴の基本（詳細はE2）","聞く7：話す3",[
        "相づち・うなずき・オウム返しで受け止める","評価・否定をしない（まず受け止める）","学生が8割話す状態をつくる","言葉の裏の感情・本音を汲み取る",
    ], callout=("POINT","話させた分だけ信頼が生まれる。CAは聞き役。"))
    dk.content("バイアス・利益相反に注意","学生の人生は学生が決める",[
        "自分の結論へ誘導しない","成約のために都合の良い求人へ寄せない","事実と意見（自分の主観）を分けて伝える","ミスマッチ＝早期離職を生む“押し込み”をしない",
    ], callout=("NG","成約目的の誘導は信頼を壊し、結局は早期離職を生む。"))
    dk.divider("03","PART 3","提案とフォロー")
    dk.content("情報提供・提案","価値観に紐づけて渡す",[
        "ヒアリングで得た“軸”に紐づけて求人を提示","メリットだけでなくデメリットも両面で","比較軸を一緒に整理する","押しつけず、選ぶのは学生という前提で",
    ])
    dk.content("面談後のフォロー","伴走は記録から",[
        "面談内容・合意事項をSFに記録する","ネクストアクションと期限を合意","適切な頻度で連絡・伴走する","急かさない（オワハラにしない）",
    ])
    dk.work("WORK ・ 演習","模擬面談（ロープレ）","学生役の「やりたいことが分からない」に、ヒアリングで“価値観”を3つ引き出す","オープンクエスチョン中心・沈黙を活かす・誘導しない","終わったら学生役からフィードバックをもらう")
    dk.deepen()
    dk.checklist("CHECK ・ 到達チェック","合格ライン",[
        "面談の4ステップを実演できる","Will/Can/Must と価値観を引き出せる","聞く7：話す3を実践できる","誘導せず、納得の意思決定を支えられる",
    ])
    dk.closing("NEXT ・ まとめ","面談は“支える場”",[
        "面談＝学生の意思決定を支える場","聞く7：話す3・誘導しない・記録する","次：F4 クロージング",
    ], "キャリアカウンセリング／面談（YouTube教材タブ参照）","")

def build_closing(dk):
    dk.tag="F4 クロージング"
    dk.cover("F4","CA職種特化","クロージング","“納得して決める”を誠実に後押しする","1時間")
    dk.content("GOAL ・ このモジュールのゴール","読み終えたらできること",[
        "迷い・不安の正体を特定できる","意思決定を整理して後押しできる","押し売りせず“納得”を引き出せる",
    ], numbered=True, callout=("POINT","クロージング＝説得ではなく、納得の“整理”。"))
    dk.divider("01","PART 1","クロージングの本質")
    dk.content("よくある誤解を解く","強引な押しではない",[
        "クロージング≠強引に決めさせること","学生の迷いを言語化し、整理して取り除く","決定の主役はあくまで学生","“決めきれない要因”を一緒に外していく",
    ])
    dk.content("迷いの3分類","原因が違えば打ち手が違う",[
        "情報不足（分からない）→ 正確な情報提供","不安（怖い）→ 共感＋事実で安心を","比較で迷う（優先順位）→ 価値観の軸で整理","まず「なぜ迷うのか」を特定する",
    ], callout=("POINT","「なぜ迷うのか」を特定すれば、打ち手は自ずと決まる。"))
    dk.divider("02","PART 2","後押しの技術")
    dk.content("テストクロージング","本音と障害を探る",[
        "「今の気持ちは10点中何点ですか？」","「あと何が分かれば決められそう？」","反応から本音・残る障害を見つける","小さな合意を積み重ねる",
    ])
    dk.content("不安への対応","受け止めてから事実で応える",[
        "まず傾聴で受け止める → 事実で応える","入社後のイメージを具体化する","先輩事例・データで安心材料を渡す","嘘・誇張は絶対にしない",
    ], callout=("NG","不利な情報を隠して承諾を取るのは厳禁。後で必ず崩れる。"))
    dk.content("意思決定の整理","一緒に可視化する",[
        "価値観の軸で各社を比較する","メリット／デメリットを一緒に書き出す","期限を区切る（ただし急かさない）","家族・周囲への相談も後押しする",
    ])
    dk.content("オワハラにしない","信頼と定着を最優先に",[
        "他社の選考辞退を強要しない","「今ここで決めて」と迫らない","学生のペースを尊重する","納得して決める＝早期離職を防ぐ",
    ], callout=("NG","急かしクロージングはオワハラ。短期の数字より信頼と定着。"))
    dk.work("WORK ・ 演習","迷う学生を後押しする","迷っている学生役に、迷いの分類→テストクロージング→軸整理で後押し","押し売りワードを使わない・誠実に","終了後、学生役が“納得できたか”を確認")
    dk.deepen()
    dk.checklist("CHECK ・ 到達チェック","合格ライン",[
        "迷いを3分類で特定できる","テストクロージングで本音を探れる","事実で不安に応えられる","オワハラにせず納得を引き出せる",
    ])
    dk.closing("NEXT ・ まとめ","納得の整理で後押しする",[
        "クロージング＝納得の整理","迷いを特定し、誠実に後押し","次：F3 企業紹介文 ／ F5 職業安定法・個人情報",
    ], "（面談・傾聴モジュールとあわせて）","")

def build_listening(dk):
    dk.tag="E2 傾聴"
    dk.cover("E2","自己・対人","傾聴・コミュニケーション","“聞く力”が信頼と成果をつくる","1時間")
    dk.content("GOAL ・ このモジュールのゴール","読み終えたらできること",[
        "傾聴の3レベルを理解する","相づち・質問・要約で深く聞ける","相手が“話したくなる”聞き方ができる",
    ], numbered=True, callout=("POINT","人は“正しく聞いてくれた人”を信頼する。"))
    dk.divider("01","PART 1","傾聴とは")
    dk.diagram("ladder","LADDER ・ 傾聴の3レベル","どこまで聞けているか",
        [("レベル1","自分中心で聞く"),("レベル2","相手に集中して聞く"),("レベル3","感情・価値観まで汲む")],
        note="目指すはレベル2〜3。“聞いているフリ”は必ず伝わる。意識が相手に向いているか。")
    dk.content("アクティブリスニング","態度で「聞いている」を伝える",[
        "うなずき・相づちで反応する","アイコンタクト・前傾の姿勢","オウム返し（バックトラッキング）","評価・否定をしない",
    ])
    dk.divider("02","PART 2","深める技術")
    dk.content("質問で広げる・深める","沈黙も味方にする",[
        "オープン（どんな／なぜ）で広げる","「具体的には？」「他には？」で深掘り","クローズドで事実を確認する","沈黙を待つ（急かさない）",
    ])
    dk.content("共感と要約","気持ちを受け止め、確認する",[
        "感情をラベリング「不安なんですね」","事実より“気持ち”を先に受け止める","要約で「つまり〜ですね」と確認","ペーシング（話速・トーンを合わせる）",
    ], callout=("POINT","要約は“ちゃんと聞いた証拠”。相手の安心と信頼に直結する。"))
    dk.content("やってはいけない","心を閉ざさせる聞き方",[
        "話を奪う・かぶせる","すぐにアドバイス・否定する","結論を急かす","スマホを見ながらの“ながら聞き”",
    ], callout=("NG","“でも”“いや”で受けると心を閉ざす。まず受け止める。"))
    dk.content("場面別の傾聴","相手と状況で変える",[
        "面談：価値観・不安を引き出す","上司・同僚：背景・意図を確認する","クレーム：まず最後まで聴ききる","オンライン：相づち・反応を大きめに",
    ])
    dk.work("WORK ・ 演習","3分間の傾聴トレーニング","3人組（話し手／聞き手／観察者）で実施","聞き手はオウム返し＋要約＋オープン質問のみ（アドバイス禁止）","観察者が“話しやすかったか”をフィードバック")
    dk.deepen()
    dk.checklist("CHECK ・ 到達チェック","合格ライン",[
        "傾聴の3レベルを説明できる","オウム返し・要約ができる","オープン質問で深掘りできる","否定せず受け止められる",
    ])
    dk.closing("NEXT ・ まとめ","聞く力が土台",[
        "傾聴＝信頼の土台","受け止める→深める→要約する","次：E3 セルフマネジメント",
    ], "傾聴／コーチング入門（YouTube教材タブ参照）","")

def build_company_intro(dk):
    dk.tag="F3 企業紹介文"
    dk.cover("F3","CA職種特化","企業紹介文の書き方","心を動かし、正しく伝える","1時間")
    dk.content("GOAL ・ このモジュールのゴール","読み終えたらできること",[
        "社内の正本フォーマットで紹介文を書ける","学生目線で“魅力と事実”を両立できる","誇張せず惹きつける文章にできる",
    ], numbered=True, callout=("POINT","紹介文は“求人広告”ではなく、学生の意思決定材料。"))
    dk.divider("01","PART 1","紹介文の役割")
    dk.content("紹介文の目的","学生と企業の橋渡し",[
        "学生が企業に興味を持つ“入口”をつくる","事実に基づき、正しく伝える","学生の価値観と企業の魅力を結びつける","誇張・盛りは信頼を壊す（職業安定法の観点でもNG）",
    ], callout=("POINT","“正しく・魅力的に”。どちらか一方では足りない。"))
    dk.content("正本フォーマットに従う","自己流で書かない",[
        "社内の生成フォーマット（generate_company_intro）が正本","訴求タイプを学生に合わせて変える（例：稼ぎ／起業／マーケ志向）","勝手な構成・テンプレで書かない","迷ったら正本ツール・既存の良い紹介文を参照",
    ])
    dk.divider("02","PART 2","書き方")
    dk.content("構成要素","盛り込むべき情報",[
        "企業概要・事業・ビジネスモデル（どう稼ぐか）","魅力（成長性・裁量・文化・キャリア）","求める人物像","学生がイメージできる具体（事業の中身・働く姿）",
    ])
    dk.content("書き方のコツ","読み手目線に翻訳する",[
        "結論・魅力を先に書く","専門用語をかみ砕く","数字・事実で裏付ける","“学生のベネフィット”に翻訳する（自分にどう関係するか）",
    ], callout=("POINT","企業の言葉のままでは響かない。学生の言葉に翻訳する。"))
    dk.content("やってはいけない","信頼を壊すNG",[
        "事実と異なる誇張・盛り","ネガティブ情報の意図的な隠蔽","コピペ・使い回しの薄い文","主観の押しつけ（“絶対おすすめ”等）",
    ], callout=("NG","盛った紹介文はミスマッチと不信の元。事実ベースで魅力を出す。"))
    dk.work("WORK ・ 演習","企業紹介文を書く","ある企業を、正本フォーマットで紹介文化する","訴求タイプを1つ選び、その軸で魅力を書き分ける","数字・事実の裏取りを必ず行う")
    dk.deepen()
    dk.checklist("CHECK ・ 到達チェック","合格ライン",[
        "正本フォーマットで書ける","魅力と事実を両立できる","学生のベネフィットに翻訳できる","誇張・隠蔽をしない",
    ])
    dk.closing("NEXT ・ まとめ","正しく、魅力的に",[
        "紹介文＝学生の意思決定材料","正本フォーマット・事実ベース・学生目線","次：F5 職業安定法・個人情報",
    ], "（企業紹介文フォーマットタブ・正本ツールを参照）","")

def build_law(dk):
    dk.tag="F5 職安法・個人情報"
    dk.cover("F5","CA職種特化","職業安定法・個人情報","守るべきルールを“自分の言葉”で","1時間")
    dk.content("GOAL ・ このモジュールのゴール","読み終えたらできること",[
        "人材紹介の法的ルールの要点を説明できる","個人情報を適正に扱える","NG行為を自分で判断できる",
    ], numbered=True, callout=("POINT","ルールは事業の生命線。“知らなかった”では済まされない。"))
    dk.divider("01","PART 1","職業安定法")
    dk.content("有料職業紹介のルール","紹介事業の大前提",[
        "許可制（厚生労働大臣の許可が必要）","求職者から手数料は原則取らない","労働条件の明示義務（正確に伝える）","求人の真実性（虚偽・誇大な求人はNG）",
    ])
    dk.content("取り扱えない求人","扱ってはいけないもの",[
        "違法・危険な仕事","労働条件が法令違反のもの","差別的求人（性別・年齢の不当な限定 等）","公序良俗に反するもの",
    ], callout=("NG","怪しい求人は扱わない。判断に迷えば必ず上長に確認。"))
    dk.divider("02","PART 2","個人情報保護")
    dk.diagram("flow","FLOW ・ 個人情報の基本","求職者の情報を“流れ”で守る",
        [("管理","厳重に管理","アクセス制限"),("利用","目的の範囲内","利用目的を超えない"),
         ("提供","第三者提供しない","本人同意が原則"),("廃棄","適正に廃棄","不要になれば消す")],
        note="取得→利用→提供→廃棄のどの段階でも、本人の情報を守る。")
    dk.content("実務での注意","事故を防ぐ所作",[
        "指定ツール（SF等）の外に持ち出さない","個人情報をAI・外部にそのまま入れない（仮名化）","画面ロック・離席・クリアデスク","誤送信（CC・添付）に注意",
    ], callout=("NG","個人情報の流出は事業存続に関わる重大事故。"))
    dk.content("求職者の権利・公正な取扱い","人として誠実に",[
        "本人の開示・訂正請求に対応する","差別の禁止・公平な取扱い","ハラスメントのない面談","嘘の経歴・求人を作らない",
    ])
    dk.work("WORK ・ 演習","OK / NG を判断する","次の事例はOK？NG？理由とともに答える","①求職者の連絡先を、知人の会社に無断で渡す","②条件を実際より良く見せて求人を提示する")
    dk.deepen()
    dk.checklist("CHECK ・ 到達チェック","合格ライン",[
        "有料職業紹介のルールを言える","扱えない求人を判断できる","個人情報の取扱い原則を守れる","NG事例をOK/NGで判断できる",
    ])
    dk.closing("NEXT ・ まとめ","ルールを守って信頼を築く",[
        "職業安定法・個人情報は事業の土台","迷ったら必ず確認する","Stage3修了 → 独り立ちへ",
    ], "（コンプライアンス・情報セキュリティ教材も参照）","")

def build_research(dk):
    dk.tag="D3 情報収集"
    dk.cover("D3","思考・分析","情報収集・リサーチ","速く・正しく・偏りなく集める","1時間")
    dk.content("GOAL ・ このモジュールのゴール","読み終えたらできること",[
        "一次情報と二次情報を使い分けられる","信頼できる情報源を選べる","目的に沿って効率的にリサーチできる",
    ], numbered=True, callout=("POINT","意思決定の質は、集める情報の質で決まる。"))
    dk.content("一次情報と二次情報","情報には“距離”がある",[
        "一次＝自分で得た事実（面談・現場・IR資料）","二次＝他人がまとめた情報（記事・まとめ）","一次を重視し、二次は必ず裏取りする","又聞き・伝聞を鵜呑みにしない",
    ])
    dk.diagram("pyramid","RANK ・ 情報源の信頼性","“誰が・いつ・何を根拠に”",
        [("公式・一次","企業IR・官公庁・業界団体＝最優先"),("専門メディア","業界紙・専門誌は次点"),("個人ブログ・SNS","要注意・必ず裏取り")],
        note="一つのソースを信じない。出典・日付・作成者を確認し、複数で裏を取る。")
    dk.diagram("flow","FLOW ・ 効率的な集め方","目的から逆算する",
        [("①","問い・目的を決める","先にゴールを定める"),("②","検索演算子で絞る","ノイズを削る"),("③","AIで全体像","ざっと俯瞰する"),("④","一次情報で裏取り","必要な分だけ確かめる")],
        note="集めすぎない。目的に必要な分だけを、目的から逆算して集める。")
    dk.content("企業リサーチの型（CA実務）","学生に語れる材料を集める",[
        "事業・ビジネスモデル・強み","採用背景・求める人物像","業界でのポジション・競合","学生に語れる“魅力と事実”",
    ])
    dk.content("バイアスに注意","集め方の落とし穴",[
        "確証バイアス（都合の良い情報だけ集める）","情報の鮮度（古い情報のまま使う）","一次の取り違え・誤読","AI・記事の誤情報（ハルシネーション）",
    ], callout=("NG","AIや記事の情報は必ず一次で裏取り。鵜呑みは事故のもと。"))
    dk.work("WORK ・ 演習","15分企業リサーチ","ある企業を15分でリサーチし、学生向け要点を3つにまとめる","一次情報を1つは含める","各要点に出典を必ず添える")
    dk.deepen()
    dk.checklist("CHECK ・ 到達チェック","合格ライン",[
        "一次／二次を使い分けられる","情報源の信頼性を判断できる","目的から逆算して集められる","裏取り・出典確認ができる",
    ])
    dk.closing("NEXT ・ まとめ","正しい情報が判断を支える",[
        "一次重視・複数で裏取り・出典確認","目的から逆算して集める","次：D4 目標設定",
    ], "（リサーチ・ファクトチェック教材を参照）","")

def build_goal(dk):
    dk.tag="D4 目標設定"
    dk.cover("D4","思考・分析","目標設定（MBO／OKR）","“正しい目標”が毎日の行動を変える","1時間")
    dk.content("GOAL ・ このモジュールのゴール","読み終えたらできること",[
        "SMART／MBO／OKRを理解する","売上目標から逆算できる","目標を日々の行動に落とせる",
    ], numbered=True, callout=("POINT","良い目標は、毎日の行動を具体的に変える。"))
    dk.content("なぜ目標設定が要るのか","行動の羅針盤",[
        "行動の指針・優先順位が決まる","成長の速度が上がる","振り返り・改善ができる","Tokumoriの“半年で売上300万”の土台になる",
    ])
    dk.diagram("pyramid","STRUCTURE ・ 目標の階層構造","上から下へ一本の線でつなぐ",
        [("ミッション／ビジョン","何のために働くか"),("KGI＝最終目標","半年で売上300万 など"),
         ("KPI＝中間指標","面談数・紹介数・承諾数"),("行動目標","日々のアクション（架電・面談）")],
        note="上位の目標と毎日の行動が“線”でつながると、ブレない。")
    dk.content("SMARTの原則","あいまいな目標を捨てる",[
        "Specific：具体的に","Measurable：測れる（数値）","Achievable：達成可能","Relevant／Time-bound：関連・期限を切る",
    ], callout=("POINT","「頑張る」は目標ではない。数値と期限を必ず入れる。"))
    dk.content("MBOとOKR","目標管理の型",[
        "MBO＝目標による管理（評価と接続）","OKR＝高い目標(O)＋主要成果(KR)","いずれも定量で測る","定期的に見直す（立てっぱなしにしない）",
    ])
    dk.content("OKRの書き方（具体例）","高い目標＋測れる成果",[
        "Objective（目標）：半年で“頼られるCA”になる","KR1：内定承諾を累計◯件（測れる数値）","KR2：面談満足度アンケート平均◯以上","KR3：担当業界の知識テスト◯点（達成度0〜1.0で評価）",
    ], callout=("POINT","Oはワクワクする定性、KRは必ず数値。KRは3つ前後に絞る。"))
    dk.diagram("flow","FLOW ・ KGI／KPIと逆算","ゴールを行動に分解する",
        [("KGI","最終目標","半年で売上300万"),("KPI","中間指標","面談・紹介・承諾数"),
         ("分解","行動量へ","KPIを行動量に変換"),("実行","日・週へ","日週のアクションに落とす")],
        note="ゴールは“今日の行動”まで分解して初めて動き出す。")
    dk.diagram("flow","FLOW ・ CA実務の目標例","逆算してみる",
        [("①","承諾目標","承諾◯件/月から逆算"),("②","必要母数","通過率から面談数を算出"),
         ("③","行動量","架電・面談・紹介に落とす"),("④","週次調整","進捗を振り返り調整")])
    dk.diagram("cycle","CYCLE ・ 振り返りで回す（PDCA／KPT）","目標は“見直して”達成する",
        ["数字で確認","原因を分解","Keep/Problem/Try","上長と微修正"],
        note="立てっぱなしは未達のもと。週次の見直しが達成率を決める。")
    dk.work("WORK ・ 演習","300万を行動に逆算する","「半年で売上300万」を 月次→KPI→週次行動 に分解する","各段階の数値（通過率・件数）を仮で置く","自分の数値目標を1つSMARTで書き、週次の振り返り方法も決める")
    dk.deepen()
    dk.checklist("CHECK ・ 到達チェック","合格ライン",[
        "SMARTで目標を書ける","MBO／OKRを説明できる","KGI→KPI→行動に分解できる","売上目標から逆算できる",
    ])
    dk.closing("NEXT ・ まとめ","目標を行動に変える",[
        "数値と期限を入れる（SMART）","KGI→KPI→日々の行動へ逆算","次：E2 傾聴 ／ E3 セルフマネジメント",
    ], "（目標設定・KPIマネジメント教材を参照）","")

def build_selfmgmt(dk):
    dk.tag="E3 セルフマネジメント"
    dk.cover("E3","自己・対人","セルフマネジメント","自分を整え、成果を出し続ける","1時間")
    dk.content("GOAL ・ このモジュールのゴール","読み終えたらできること",[
        "時間・タスク・体調・メンタルを自己管理できる","優先順位をつけられる","長く成果を出せる状態を保てる",
    ], numbered=True, callout=("POINT","成果は才能より“続けられる状態”から生まれる。"))
    dk.content("時間管理","時間を“設計”する",[
        "緊急／重要マトリクス（第2領域＝重要・非緊急を確保）","朝に計画・終業に振り返り","集中ブロック／シングルタスク","スキマ時間を活用する",
    ])
    dk.quadrant("図解 ・ 時間管理","緊急／重要マトリクス",
        "← 緊急でない  緊急 →","↑ 重要",
        [("第2領域：重要×非緊急","計画・準備・自己投資。ここを死守する",True),
         ("第1領域：重要×緊急","締切・トラブル。すぐ対応する",False),
         ("第4領域：非重要×非緊急","娯楽・浪費。減らす",False),
         ("第3領域：非重要×緊急","割り込み・雑務。任せる／減らす",False)],
        "成果は“第2領域（重要・非緊急）”をどれだけ確保できるかで決まる。")
    dk.content("タスク管理","抱え込まない仕組み",[
        "見える化（ToDo・SF・カレンダー）","締切と優先度を明確にする","大きい仕事は分解する","抱え込まず報連相する",
    ])
    dk.diagram("pyramid","メンタル・体調の管理","土台を整える",
        [("一人で抱えない","不調は早めに相談する"),
         ("切り替える・休む","休む技術／早めにサインに気づく"),
         ("基盤を守る","睡眠・運動・食事の生活基盤")],
        note="不調は早めに相談。隠して悪化が一番もったいない。")
    dk.diagram("cycle","学び続ける","小さく改善を積む",
        ["振り返り(KPT)","FBを歓迎","改善を積む","目標(D4)接続"],
        note="KPTを習慣にし、フィードバックと小さな改善を回し続ける。")
    dk.content("モチベーション維持","自分の機嫌は自分でとる",[
        "目的（なぜやるか）に立ち返る","小さな成功を可視化する","仲間と高め合う","気分に左右されすぎない仕組みを持つ",
    ])
    dk.work("WORK ・ 演習","1週間を振り返る","自分の1週間を“緊急／重要”の4象限で振り返る","時間を使いすぎた象限・足りない象限を特定","第2領域（重要・非緊急）の予定を1つ入れる")
    dk.deepen()
    dk.checklist("CHECK ・ 到達チェック","合格ライン",[
        "緊急／重要で優先順位をつけられる","タスクを見える化・分解できる","体調・メンタルのサインに気づける","振り返りを習慣化できる",
    ])
    dk.closing("NEXT ・ まとめ","整えて、続ける",[
        "第2領域を確保する","抱え込まず相談・振り返る","Stage修了 → 実務で磨き続ける",
    ], "（セルフマネジメント・タイムマネジメント教材を参照）","")

def build_compliance(dk):
    dk.tag="G1 コンプライアンス"
    dk.cover("G1","リスク・コンプラ","コンプライアンス基礎","“当たり前を、当たり前に”守る","1.5時間")
    dk.content("GOAL ・ このモジュールのゴール","読み終えたらできること",[
        "コンプライアンスの意味と重要性を理解する","違反のリスク（会社・個人）を説明できる","迷った時に判断・相談ができる",
    ], numbered=True, callout=("POINT","一人の違反が、会社全体の信用を一瞬で壊す。"))
    dk.divider("01","PART 1","コンプラとは")
    dk.content("コンプライアンスとは","法令“だけ”ではない",[
        "法令・社内ルール・社会規範・倫理を守ること","“バレなければ良い”ではない","会社の信用と存続を守る土台","全員が当事者（自分ごと）",
    ])
    dk.content("守るべき範囲","身近なルールの全体像",[
        "法令（労基法・職業安定法・個人情報・下請法 等）","社内規程・就業規則","契約・守秘義務","社会的モラル・SNSでの振る舞い",
    ])
    dk.content("違反のリスク","失うものは大きい",[
        "会社：信用失墜・行政処分・損害賠償","個人：懲戒・損害賠償・刑事責任","取引停止・採用への悪影響","一度の違反が、積み上げた全てを失わせる",
    ], callout=("NG","「これくらい大丈夫」という油断が、最大のリスク。"))
    dk.divider("02","PART 2","実務で守る")
    dk.content("身近な違反の例","“うっかり”を防ぐ",[
        "情報漏洩（個人情報・機密の持ち出し）","ハラスメント","SNSでの不適切な投稿","経費・勤怠の不正／著作権侵害（無断転載）",
    ])
    dk.content("迷った時の判断軸","“やらない・確認する”",[
        "家族や世間に堂々と説明できるか","ルール・上長に確認したか","短期の利益より“信頼”を選ぶ","違和感は放置せず相談・報告する",
    ], callout=("POINT","迷ったら“やらない・確認する”。判断を一人で抱えない。"))
    dk.diagram("flow","FLOW ・ 通報・相談","隠蔽が最も重い",
        [("①","気づく","おかしいと感じたら放置しない"),("②","即報告","上長・相談窓口へ。隠す・もみ消すが最悪"),
         ("③","被害最小化","早期報告が被害を最小化する"),("④","守られる","正直に報告した人は守られる")],
        note="隠す・もみ消すが最悪の対応。早期報告が被害を最小化し、報告した人は守られる。")
    dk.work("WORK ・ 演習","OK / NG を判断する","次はコンプラ的にOK？NG？理由とともに","①顧客情報を私物PCに保存　②SNSに社内の出来事を投稿","③上長の承認なしに値引きを約束",)
    dk.deepen()
    dk.checklist("CHECK ・ 到達チェック","合格ライン",[
        "コンプラの意味を説明できる","違反のリスクを言える","判断軸で迷いを処理できる","おかしいと思ったら相談・報告できる",
    ])
    dk.closing("NEXT ・ まとめ","信頼は一瞬で崩れる",[
        "コンプラ＝信用と存続を守る土台","迷ったら やらない・確認する・相談する","次：G2 個人情報保護",
    ], "（コンプライアンス研修教材を参照）","")

def build_privacy(dk):
    dk.tag="G2 個人情報保護"
    dk.cover("G2","リスク・コンプラ","個人情報保護","求職者の情報を“預かっている”自覚","1.5時間")
    dk.content("GOAL ・ このモジュールのゴール","読み終えたらできること",[
        "個人情報の定義と原則を理解する","適正に取得・利用・管理できる","漏洩を防ぎ、起きたら正しく動ける",
    ], numbered=True, callout=("POINT","個人情報は“借り物”。雑に扱う権利は誰にもない。"))
    dk.content("個人情報とは","求職者情報はその塊",[
        "氏名・連絡先・学歴・顔写真など個人を識別できる情報","求職者の情報はまさに個人情報の塊","要配慮情報（健康・信条 等）は特に厳重に","“匿名でも組合せで特定できる”ことに注意",
    ])
    dk.diagram("flow","FLOW ・ 4つの基本ルール","各段階で“同意と目的”",
        [("取得","利用目的を明示","適正に取得する"),("利用","目的の範囲内で使う","逸脱しない"),
         ("保管","安全に管理する","アクセス制限"),("提供","本人同意が前提","無断で第三者提供しない")],
        note="取得・利用・保管・提供。すべての段で“同意と目的”を意識。")
    dk.content("安全管理の実務","日々の所作で守る",[
        "指定ツール（SF等）の外に持ち出さない","パスワード・アクセス権限を適切に","画面ロック・クリアデスク","AI・外部入力は仮名化／誤送信を防ぐ",
    ])
    dk.content("やってはいけない","重大事故になる行為",[
        "私物PC・USB・個人クラウドに保存","無断で第三者（知人・他社）に渡す","退職時の情報持ち出し","SNS・雑談での口外",
    ], callout=("NG","個人情報の持ち出し・口外は重大事故＝懲戒・法的責任。"))
    dk.diagram("flow","FLOW ・ 漏洩が起きたら","隠すが最悪・即報告で被害最小化",
        [("①","即報告","隠さず上長・担当へ"),("②","事実整理","何が・どこまでか"),
         ("③","拡大防止","本人対応・封じ込め"),("④","再発防止","原因をつかむ")],
        note="漏洩は“隠す”が最悪。即報告が被害を最小化する。")
    dk.work("WORK ・ 演習","自分の業務で点検する","業務で個人情報に触れる場面を3つ挙げる","各場面のリスクと対策を書く","“持ち出していないか”を自己点検")
    dk.deepen()
    dk.checklist("CHECK ・ 到達チェック","合格ライン",[
        "個人情報の定義を言える","取得・利用・保管・提供の原則を守れる","安全管理の所作を実践できる","漏洩時に即報告できる",
    ])
    dk.closing("NEXT ・ まとめ","“預かりもの”を守り抜く",[
        "個人情報は借り物・厳重に扱う","持ち出さない・口外しない・即報告","次：G3 情報セキュリティ ／ G4 ハラスメント",
    ], "（個人情報保護・情報セキュリティ教材を参照）","")

def build_slack(dk):
    dk.tag="C5 Slack"
    dk.cover("C5","PC・ツール","Slackの使い方","チームの“流れ”を速く、正しく","1時間")
    dk.content("GOAL ・ このモジュールのゴール","読み終えたらできること",[
        "チャンネル／スレッド／メンションを使い分けられる","報連相をSlackで適切にできる","マナーと情報管理を守れる",
    ], numbered=True, callout=("POINT","Slackは“早く・オープンに”が基本。"))
    dk.diagram("relation","STRUCTURE ・ 基本の構造","どこで何を話すか",
        ("Slack",["チャンネル","スレッド","DM","全体像"]),
        note="基本はチャンネルでオープンに。スレッドで話題をまとめ、DMは限定的に。")
    dk.content("メンション・通知","相手の時間を奪わない",[
        "@here／@channel は慎重に（全員に通知）","個人宛は @名前 で明確に","通知設定で自分の集中を守る","軽い反応はリアクション（絵文字）で",
    ])
    dk.content("報連相のコツ","流れを散らさない",[
        "結論先・要点を箇条書きで","会話はスレッドにまとめる","緊急は電話・メンションを併用","依頼は“相手と期限”を明確に",
    ], callout=("POINT","オープンチャンネルで共有＝後から見返せる・属人化を防ぐ。"))
    dk.content("マナーと情報管理","公開範囲を常に意識",[
        "誰が見るかを意識して書く","個人情報・機密・パスワードを貼らない","感情的な投稿をしない","リアクションで温度感を伝える",
    ], callout=("NG","個人情報・パスワードをSlackに貼らない。公開範囲を必ず確認。"))
    dk.work("WORK ・ 演習","Slackで報連相する","指定チャンネルで自己紹介＋報連相を1件スレッドで投稿","メンションと箇条書きを使う","オープンに共有する練習をする")
    dk.deepen()
    dk.checklist("CHECK ・ 到達チェック","合格ライン",[
        "チャンネル／スレッドを使い分けられる","メンション・通知を適切に使える","結論先で報連相できる","情報管理・公開範囲を守れる",
    ])
    dk.closing("NEXT ・ まとめ","早く・オープンに",[
        "Slackは“早く・オープンに”共有","スレッドでまとめ・公開範囲を意識","次：C6 Salesforce（実務で習得）",
    ], "（Slack公式ヘルプを参照）","")

def build_sf(dk):
    dk.tag="C6 Salesforce"
    dk.cover("C6","PC・ツール","Salesforce(SF)の使い方","顧客情報を“資産”に変える","1時間")
    dk.content("GOAL ・ このモジュールのゴール","読み終えたらできること",[
        "SFの役割と基本オブジェクトを理解する","面談・求職者情報を正しく記録できる","データを次の行動・KPIに活かせる",
    ], numbered=True, callout=("POINT","記録しない情報は“無かったこと”になる。SFは全員の共有資産。"))
    dk.divider("01","PART 1","SFとは")
    dk.content("SFとは何か","チームのCRM",[
        "顧客・求職者の情報を一元管理するCRM","属人化を防ぎ、チームで共有する","行動履歴・進捗を可視化する","数字（KPI）の源泉になる",
    ])
    dk.diagram("relation","主要オブジェクト（用語）","SFを中心に、登場人物を覚える",
        ("SF",["求職者","企業","担当者","商談・選考","活動記録"]),
        note="リード/求職者=見込み学生、取引先=企業、取引先責任者=担当者、パイプライン=選考進捗、活動=面談・架電の記録。")
    dk.divider("02","PART 2","実務での使い方")
    dk.content("面談・活動の記録","忘れる前に残す",[
        "面談後すぐに記録する","事実と“次アクション”を残す","5W1Hで簡潔に","個人情報の取扱いに注意する",
    ])
    dk.content("進捗（パイプライン）管理","最新の状態を保つ",[
        "各学生のフェーズを最新に更新","承諾／見送りを正しく入力","抜け漏れを防ぐ","数字は入力の正確さで決まる",
    ], callout=("POINT","入力の正確さ＝KPIの正確さ。雑な入力は判断を誤らせる。"))
    dk.diagram("cycle","データを行動に活かす","“次に動く人”を見つけ、回し続ける",
        ["抽出","追客","共有","振り返り"],
        note="リストで“次に動くべき人”を抽出→期限・リマインドで追客→上長と共有→レポートで振り返り・改善。")
    dk.content("注意点","データの信頼を守る",[
        "指定の入力ルールに従う","個人情報をSF外に出さない","推測でデータを埋めない","分からなければ必ず確認",
    ], callout=("NG","SF外への個人情報の持ち出しは厳禁（G2 個人情報保護を参照）。"))
    dk.work("WORK ・ 演習","SFに記録してみる","模擬データで 求職者登録 → 面談記録 → 次アクション設定 を一通り","活動は5W1Hで1件入力する","入力ルールに沿っているか確認")
    dk.deepen()
    dk.checklist("CHECK ・ 到達チェック","合格ライン",[
        "SFの役割を説明できる","主要オブジェクトを言える","面談・活動を正しく記録できる","個人情報を持ち出さず運用できる",
    ])
    dk.closing("NEXT ・ まとめ","記録が力になる",[
        "SF＝チームの共有資産・KPIの源泉","正確に記録し、次の行動に活かす","Week3 実践 → OJTで磨く",
    ], "（社内SF操作マニュアル・OJTで習得）","")

def build_claude_code(dk):
    dk.tag="C11 Claude Code活用"
    dk.cover("C11","PC・ツール / 応用","Claude Code 活用（応用編）","“どの会社よりもAIを使いこなす”の正体","1.5時間")
    dk.content("GOAL ・ このモジュールのゴール","読み終えたらできること",[
        "claude／Cowork／Codeの違いを説明できる","自分のPCにセットアップし、CLAUDE.mdを書ける","MCP・プラグイン・サブエージェント・高度機能を使い分けられる","実務タスクを1つ、最後までやり切れる",
    ], numbered=True, callout=("POINT","AIに“指示する”時代から、AIと“協働する”時代へ。"))
    dk.divider("01","PART 1","Claude Codeとは")
    dk.content("Claude Codeとは","“手を動かす”AIエージェント",[
        "ターミナル／エディタで動くAIエージェント","チャットで終わらず、ファイル・調査・作成まで自律実行","CLI・デスクトップ・VS Code／JetBrains・Web（claude.ai/code）","“賢い同僚”として一緒に仕事を進める",
    ], callout=("POINT","ただ答えるAIではなく、実際に作業を完了させるAI。"))
    dk.diagram("relation","claude / Cowork / Code の違い","同じAIの“3つの舞台”",
        ("同じAI", ["Chat","Cowork","Code"]),
        note="Chat＝相談・下書き、Cowork＝デスクトップで自走、Code＝ターミナルで自走。Codeの力をデスクトップ業務へ広げたのがCowork。")
    dk.content("Coworkの正体","Claude Codeの力を“非エンジニア”へ",[
        "Coworkは「Claude Codeのパワーを知的労働に」開いたもの","だからCode＝最前線。ここで分かる機能がCoworkにも降りる","“開発者の道具”を知ると、Coworkをより深く使える","本モジュールはその最前線＝Claude Codeを体験する",
    ], callout=("POINT","Codeを知る＝AIエージェントの“天井”を知ること。"))
    dk.content("CAの実務でも効く","“雑務”を任せて本質に集中",[
        "企業リサーチ・要約・資料作成の自動化","スプレッドシート／スライド／フォームをAPIで自動生成","議事録の要約・メール下書き・面談準備","反復作業をスクリプト化して時短",
    ])
    dk.content("モデルと料金感","用途で賢く使い分け",[
        "最新は Opus 4.8（高難度）／ Sonnet（標準）／ Haiku（軽量・高速）","Fast モードで高速化（Opusのまま速く）","1Mトークンの長い文脈＝巨大資料も分割せず読める","重い仕事はOpus、軽い反復はHaiku、と切替",
    ])
    dk.divider("02","PART 2","セットアップ")
    dk.flow("FLOW ・ セットアップ手順","4ステップで使い始める",[
        ("1","インストール","CLI導入＋VS Code拡張を入れる"),("2","ログイン","Anthropicアカウントで認証"),
        ("3","CLAUDE.md","前提・ルールを書く"),("4","拡張設定","MCP・プラグインを足す"),
    ], "まずは動かす→自分ルールを書く→拡張、の順で育てる。")
    dk.content("セットアップ詳細","最初の一歩",[
        "CLIを導入して `claude` で起動／VS Code拡張も追加","Anthropicアカウントでログイン認証","作業フォルダ直下に CLAUDE.md を置く","まず小さなタスクで動作を体感する",
    ])
    dk.content("CLAUDE.md（自分ルール）","“毎回の指示”を減らす",[
        "全プロジェクト共通＝ ~/.claude/CLAUDE.md","プロジェクト個別＝フォルダ直下の CLAUDE.md","コーディング規約・口調（日本語）・禁止事項を明記","“こう動いてほしい”を一度書けば毎回効く",
    ], callout=("POINT","CLAUDE.mdの作り込みが、AIの精度と一貫性を決める。"))
    dk.divider("03","PART 3","拡張：MCP・プラグイン・エージェント")
    dk.content("MCP（外部接続）","AIを社内ツールに繋ぐ",[
        "MCP＝Model Context Protocol（外部ツール／データへの接続口）","当環境の例：context7（最新ドキュメント取得）","salesforce系（SF操作）・hr-support（自社API）・tldv（会議文字起こし）","必要なものだけ常駐させる（最小構成）",
    ], callout=("POINT","MCPで“自社のSF・会議・APIにAIが直接アクセス”できる。"))
    dk.content("プラグイン／コマンド","定番の“技”を呼ぶ",[
        "/feature-dev（新機能）・/pr-review-toolkit（レビュー）","/commit-commands（コミット・PR）・/deep-research（相互検証リサーチ）","/session-report・/context-budget（状態診断）","/skill-creator・frontend-design・code-simplifier 等",
    ])
    dk.content("サブエージェント（並列の専門家）","同時に手分けして調べる",[
        "専門特化AIを並列で起動できる","当環境：python-reviewer／security-reviewer／code-explorer","business-writer／salesforce-architect／gas-debugger 等も常備","独立した調査を同時並行→結論だけ受け取る",
    ])
    dk.content("スキル（/コマンド）","業務を“ワンコマンド”に",[
        "定型業務を技として呼び出す","当環境：company-research・sf-register・email・lgca-ops 等","`/名前` で発火","自分専用スキルも作れる（skill-creator）",
    ])
    dk.divider("04","PART 4","高度な使い方")
    dk.content("大規模・徹底モード","“全部まとめて”やり切る",[
        "Workflow＝多エージェント編成（並列ファンアウト＋敵対的検証）","「ultracode」で徹底監査・網羅レビュー","/effort で思考の深さを調整","大規模調査・全コード監査・横断作業に",
    ], callout=("POINT","ここまでの自走力がCoworkの土台＝だから知る価値がある。"))
    dk.content("自動化・常駐","放っておいても進む",[
        "/schedule＝クラウドで定期実行（cron）","/loop＝間隔指定 or 自己ペースで反復（CI監視等）","バックグラウンド実行＝裏で並走し完了時に通知","/goal＝ゴール／完了条件を保持し進捗を追う",
    ], callout=("POINT","“夜のうちに調べておいて”が現実になる＝時間の使い方が変わる。"))
    dk.content("1Mコンテキスト・並列","規模の壁を越える",[
        "巨大ログ・複数リポジトリを分割せず一気に読む","独立タスクは並列サブエージェントで同時実行","長時間処理は裏で走らせて他を進める","“分けずに丸ごと”が可能になる",
    ])
    dk.diagram("cycle","自己進化（cc-evolution）","環境が“育つ”仕組み",
        ["週次リサーチ","採用提案","承認・適用","学習・最適化"],
        note="週次でAIが新機能をリサーチ→採用提案→/cc-evolveでapply（承認分だけHITL適用）→判断を学習。使うほど自分仕様に最適化される。")
    dk.divider("05","PART 5","使いこなしの作法")
    dk.content("効果を最大化する原則","“相棒”を活かすコツ",[
        "前提と制約を渡す（CLAUDE.mdに書く）","大きい仕事は 計画（Plan）→実行 に分ける","出力は鵜呑みにせず必ず検証する","反復する作業は自動化（スクリプト／スキル）",
    ])
    dk.content("注意・セキュリティ","便利さの裏のリスク管理",[
        "APIキー・トークンを直書きしない（環境変数で参照）","個人情報・機密を入れない（仮名化）","同期／Git対象にシークレットを置かない","破壊的操作（削除等）は必ず確認してから",
    ], callout=("NG","鍵・個人情報の直書きは厳禁。環境変数＋同期外で管理する。"))
    dk.work("WORK ・ 演習","セットアップして“実務を1つ”やり切る","Claude Codeをセットアップし、CLAUDE.mdを書き、実務タスクを1つ最後までやらせる","例：ある企業をリサーチ→紹介文のたたき台まで生成。/コマンドかサブエージェントを使う","出力を検証→改善点をCLAUDE.mdに追記。Coworkでも同じ作業を試して違いを体感する")
    dk.deepen()
    dk.checklist("CHECK ・ 到達チェック","合格ライン",[
        "claude／Cowork／Codeの違いを説明できる","セットアップしCLAUDE.mdを書ける","MCP／プラグイン／サブエージェントを使い分けられる","実務タスクを1つ最後までやり切れる",
    ])
    dk.closing("NEXT ・ まとめ","これが“使いこなす”の中身",[
        "Claude Code＝手を動かす相棒（Coworkの最前線）","claude＝相談／Cowork＝作業完了／Code＝開発を自走","セットアップ→ルール→拡張→高度機能→作法","どの会社より使いこなす土台がここにある",
    ], "Claude Code公式ドキュメント／社内AI活用ガイド","docs.claude.com/claude-code")

def build_claude_setup(dk):
    dk.tag="C12 Claude Code セットアップ"
    dk.cover("C12","PC・ツール / セットアップ","Claude Code はじめてのセットアップ＆活用","ゼロから“賢く使える”状態まで（VSCode・Mac/Windows）","1時間")
    dk.content("GOAL ・ このモジュールのゴール","読み終えたらできること",[
        "自力でインストール〜ログインまでできる","VSCodeで起動して動かせる","CLAUDE.md・計画モード・権限など“賢い基本設定”ができる","秘密情報を守り、安全に使える",
    ], numbered=True, callout=("POINT","このスライド＋コマンド集Docを見れば、迷わずセットアップできる。"))
    dk.content("Claude Codeとは","ターミナル/VSCodeで動く“手を動かす”AIエージェント",[
        "コードを読み書きし、コマンドを実行し、検証まで自走する","Node.js不要のスタンドアロン（入れて、ログインするだけ）","Cowork＝デスクトップ版／Code＝開発の最前線（応用はC11へ）","“どの会社よりAIを使いこなす”の土台がこれ",
    ])
    dk.diagram("flow","FLOW ・ 全体像","5ステップで“賢く使える”まで",
        [("01","インストール","ネイティブ1行で導入"),("02","ログイン","claude→ブラウザ認証"),("03","VSCode連携","拡張を入れる"),
         ("04","動作確認","最初の一手"),("05","賢い基本設定","CLAUDE.md/計画/権限")],
        note="まず動かす→次に“賢い設定”。コマンドの実体はコピー用Docに掲載。")
    dk.divider("01","SETUP","インストール 〜 VSCodeで動かす")
    dk.content("準備するもの（前提）","用意するのはアカウントだけ",[
        "OS：macOS / Windows / Linux すべて対応","Node.js：不要（スタンドアロン・バイナリ）","ターミナル：zsh/bash（Mac）・PowerShell（Win）","アカウント：Claude Pro/Max/Team 推奨（or APIキー）",
    ], callout=("POINT","Node.jsは要りません。Claudeアカウントを用意すればOK。"))
    dk.cards("INSTALL ・ インストール（Mac / Windows）","ターミナルに1行（自動更新つき）",[
        ("macOS / Linux / WSL","TERMINAL","curl -fsSL https://claude.ai/install.sh | bash"),
        ("Windows","POWERSHELL","irm https://claude.ai/install.ps1 | iex"),
    ], note="Homebrew（brew install --cask claude-code）・winget（winget install Anthropic.ClaudeCode）も可。全コマンドはコピー用Doc参照。")
    dk.diagram("flow","FLOW ・ ログイン（初回起動）","アカウントで認証するだけ",
        [("01","プロジェクトへ移動","cd ~/your-project"),("02","claude を起動","claude と入力"),
         ("03","ブラウザで認証","OAuthでログイン"),("04","完了","トークン自動保存")],
        note="Claude Pro/Max/Team でログイン（or APIキー）。切替・再ログインは /login。")
    dk.diagram("flow","FLOW ・ VSCode連携","エディタの中で快適に使う",
        [("01","拡張を入れる","Marketplaceで『Claude Code』"),("02","開く","✨アイコン/コマンドパレット"),
         ("03","ターミナル統合","code . → claude で起動"),("04","便利機能","@でファイル参照・差分表示")],
        note="VSCode 1.98+。Cmd/Ctrl+Esc でエディタ↔Claude、Shift+Tab で権限モード切替（default→acceptEdits→plan）。")
    dk.content("動作確認（最初の一手）","これが動けばセットアップ完了",[
        "「このプロジェクトは何をする？」と聞いてみる","「コメントを1つ追加して」で編集を試す","「変更したファイルは？」でGit連携を確認","困ったら /help でヘルプ",
    ], callout=("POINT","“質問→編集→確認”が通ればOK。ここから賢い設定へ。"))
    dk.divider("02","SMART","賢く使う基本設定")
    dk.content("CLAUDE.md（プロジェクトメモリ）","“毎回の指示”を先に書いておく",[
        "/init で雛形を自動生成（ビルド/テスト/規約を検出）","置き場所：プロジェクト=./CLAUDE.md／個人=~/.claude/CLAUDE.md","書く：ビルド・テスト・コード規約・落とし穴（200行以内）","@README.md のように他ファイルをインポートできる",
    ], callout=("POINT","API詳細や一般知識は書かない（リンク参照）。要点だけ＝毎回の説明が減る。"))
    dk.diagram("before_after","SMART ・ 計画モード","“いきなり実装”をやめる",
        (("いきなり実装","大きな変更で手戻り・暴走しがち"),("計画→承認→実装","Shift+Tab×2で計画を確認してから")),
        note="Plan Mode＝まず読むだけで計画を提示→OKしてから実装。大きな変更ほど効く。")
    dk.content("権限モード・許可ルール","“勝手に実行”を制御する",[
        "Shift+Tab で循環：default（毎回確認）/ acceptEdits / plan","よく使う操作は settings.json の allow に登録","危険な操作は deny（例：.env読み・rm -rf・push --force）","セッション内は /permissions でUI管理",
    ], callout=("NG","秘密情報の読み取り・破壊的コマンドは必ず deny に入れる。"))
    dk.diagram("relation","POWER ・ 賢さの源","“素のチャット”との差はここ",
        ("Claude Code", ["スラッシュコマンド","スキル","サブエージェント","MCP連携","プラン/権限"]),
        note="/help /model /init /context /compact /clear /agents /mcp。スキル=定番作業を1コマンドに、MCP=社内ツール接続。深掘りはC11。")
    dk.content("コンテキスト運用（賢く・速く）","AIの“作業机”を整える",[
        "/context：今どれだけ使っているか確認","/compact：会話を圧縮（焦点を指定できる）","/clear：別タスクに移るときはリセット","/model で用途別に切替（Opus 4.8 / Sonnet 4.6 / Haiku 4.5 / Fable 5）",
    ], callout=("POINT","別作業に移る・同じ間違いが続く→ /clear ＋ 具体的なプロンプトで立て直す。"))
    dk.compare("WORKFLOW ・ 使いこなしの型","“良い相棒”にするコツ",
        ("やりがちな失敗",["『bug直して』など曖昧な指示","計画せずいきなり実装","テスト/ビルドせず完成扱い","文脈を溜めすぎて遅く・混乱"]),
        ("効くワークフロー",["症状＋対象ファイル＋検証方法を具体的に","計画モードで承認→実装","必ずテスト/ビルドで検証","区切りで /clear・/compact"]))
    dk.divider("03","UNDER THE HOOD","仕組みを理解する（ハーネス・MCP・API連携）")
    dk.diagram("flow","UNDER THE HOOD ・ ハーネスとは","モデル（頭脳）を動かす“体”＝Claude Code",
        [("①","指示を受ける","ゴール・文脈を読む"),("②","計画・判断","何をするか決める"),
         ("③","ツール実行","読む・書く・実行する"),("④","結果を検証","確かめて次へ（繰返し）")],
        note="モデル＝頭脳、ハーネス＝体（ループ＋ツール＋権限＋文脈管理＋フック）。同じモデルでもハーネスで使い勝手が大きく変わる。計画モードや権限もここが司る。")
    dk.content("ツールと MCP","AIに“手足”と“社内への差込口”を与える",[
        "ツール＝AIの手足（ファイル読み書き・コマンド実行・検索）","MCP（Model Context Protocol）＝社内ツールを“差し込む”標準コネクタ","たとえるなら AI版USB-C＝挿せばつながる共通規格","Gmail・Slack・Salesforce・Notion・DB を公開→AIが直接操作",
    ], callout=("POINT","ツールが手足、MCPが“社内システムへの差込口”。これで実務に触れられる。"))
    dk.diagram("flow","UNDER THE HOOD ・ API連携とは","外部サービスと“繋いで流す”仕組み",
        [("①","あなた","やりたいことを指示"),("②","Claude（ハーネス）","計画して呼び出す"),
         ("③","API / MCP","共通の窓口へ渡す"),("④","外部サービス","Sheets・SF が動く→結果")],
        note="API＝サービスごとの“共通の窓口・約束事”。連携＝それを繋いでデータを流すこと。MCPは「AI向けのAPI連携」を標準化したもの。書面の早わかり（設計図つき）はコマンド集Docの『仕組み』章にも掲載。")
    dk.content("まとめ：4つの層で動く","賢いモデル“だけ”では動かない",[
        "ハーネス＝器（ループ・権限・文脈を司る“体”）","ツール＝手足（読む・書く・実行する）","MCP＝社内ツールへのコネクタ（差込口）","API＝外部サービスの窓口（約束事）",
    ], numbered=True, callout=("POINT","頭脳（モデル）＋器（ハーネス）＋手足（ツール）＋接続（MCP/API）＝はじめて実務になる。"))
    dk.divider("04","SAFETY","安全に使う")
    dk.content("セキュリティ・安全運用","便利さの裏のリスク管理",[
        "鍵・トークンはコード/CLAUDE.mdに直書きしない（環境変数・.env）",".env や *.pem は deny で読ませない","破壊的コマンド（rm -rf・push --force）は deny","実行中は Esc で中止／差分は Accept・Reject で承認",
    ], callout=("NG","秘密情報は絶対にコミットしない。.gitignore＋環境変数を徹底。"))
    dk.content("TOKUMORI クイックスタート","社内で“賢く”始める",[
        "各自のClaudeプランでログイン → まず /init で CLAUDE.md","最初の一手：企業リサーチ→紹介文のたたき台を作らせる","計画モードで承認しながら、テストで検証する癖をつける","関連：C7（AIの使い方）／C11（応用）／コマンド集Doc",
    ], callout=("POINT","“見れば賢く始められる”を全員の標準に。詰まったらDocのトラブルシュート。"))
    dk.divider("05","POWER-UP","便利設定＆自己学習（さらに上へ）")
    dk.content("便利設定① 安全の自動ガード","“事故らない”土台を仕込む",[
        "危険コマンド（rm・force push・reset）は settings の deny で実行させない",".env・鍵ファイルは「読む前にブロック」（フック）","編集したら自動で lint（フック・警告のみ）","破壊的操作・秘密の読み取りは“承認制”にする",
    ], callout=("POINT","設定＋フックで“ミスしても止まる”状態に。最初に仕込むほど効く。"))
    dk.content("便利設定② 賢い既定にしておく","毎回が速く・安全になる",[
        "起動から計画モード（plan）＝いきなり実行しない","強いモデル＋大きな文脈を既定に（用途で /model 切替）","推論強度（effort）を上げて難所に強く","キーバインドで誤送信を防ぐ（Enter=改行 等）",
    ], callout=("POINT","“最初の整え”が毎日の生産性を決める。"))
    dk.diagram("flow","SELF-LEARN ・ 自己学習(instinct)","訂正が“次から効く”仕組み",
        [("①","訂正・好み","同じことを2回以上"),("②","蒸留","ログから判断を抽出"),
         ("③","承認(HITL)","/cc-evolve apply"),("④","自動注入","関連だけ会話へ")],
        note="人が承認するまで自動で設定を変えない。関連する学びだけを注入＝軽い。秘匿情報は学習に入れない。")
    dk.content("自己進化：環境が“育つ”","使うほど賢くなる",[
        "定期リサーチで新機能・改善点を発見","提案 → 人が承認（/cc-evolve apply）して反映","棚卸し・履歴を蓄積して積み上げる","汎用エージェントを増やし“作る品質”も上げる",
    ], callout=("POINT","鍵は HITL＝自動で書き換えない。安全に積み上げる。"))
    dk.work("WORK ・ 演習","セットアップして“実務を1つ”やり切る","Claude Codeを入れてログイン→/initでCLAUDE.md→実務を1つ最後までやらせる","VSCodeで起動し、計画モードで承認しながら進める。","例：ある企業をリサーチ→紹介文のたたき台まで。コマンドはコピー用Docから。")
    dk.checklist("CHECK ・ 到達チェック","合格ライン",[
        "インストール〜ログインを自力でできた","VSCodeで起動して動かせた","CLAUDE.md作成・計画モード・権限を説明できる","秘密情報を守り安全に使える",
    ])
    dk.closing("NEXT ・ まとめ","見れば誰でも“賢い状態”で始められる",[
        "ネイティブ1行でインストール → claude でログイン","VSCode拡張で快適に（@参照・差分・計画モード）","CLAUDE.md・計画・権限が“賢さ”の基本設定","詳細コマンドはDoc／応用はC11／公式 code.claude.com",
    ], "コマンド集Doc（仕組み・コマンド・設定／社内）","https://docs.google.com/document/d/1TgOoWV24tj_EXAx9Cn_BvbKLiDiPkiI2UfysD6udhNE/edit", link_kind="関連資料")

def build_company_size(dk):
    dk.tag="F6 企業規模の地図"
    dk.cover("F6","CA職種特化","企業規模の地図","大手〜スタートアップ、どう違うのか","1時間")
    dk.content("GOAL ・ このモジュールのゴール","読み終えたらできること",[
        "規模別カテゴリの違いを説明できる","難易度・年収・安定性・身につく力を比較できる","学生の志向に合わせて規模を提案できる",
    ], numbered=True, callout=("POINT","“大手が正解”ではない。学生の価値観に合う規模を一緒に探す。"))
    dk.divider("01","PART 1","規模カテゴリの全体像")
    dk.content("6つのカテゴリ","規模＝従業員数・売上・歴史",[
        "大手・財閥系／メガベンチャー／中堅","中小／ベンチャー／スタートアップ","それぞれに強みと弱みがある","“数の大小”より“自分に合うか”",
    ])
    dk.content("比較する6つの軸","ここを揃えて比べる",[
        "安定性／年収・上がり方","裁量・成長スピード／教育体制","ブランド／リスク","この軸で各カテゴリを横並びにする",
    ], callout=("POINT","軸を固定して比較すると、“なんとなく大手”がほぐれる。"))
    dk.quadrant("図解 ・ ポジショニング","規模のポジショニング（成長×安定）",
        "← 安定性  高 →","↑ 成長・裁量",
        [("スタートアップ／ベンチャー","裁量・成長は最大／安定は低い",True),
         ("メガベンチャー","成長と安定のバランス型",False),
         ("中小・中堅","裁量はあるが企業差が大きい",False),
         ("大手・財閥系","安定は最高／裁量は出にくい",False)],
        "規模は“成長・裁量”と“安定”のトレードオフ。学生の価値観の軸で選ぶ。")
    dk.divider("02","PART 2","カテゴリ別の特徴")
    dk.content("大手・財閥系","安定とブランド",[
        "特徴：安定・整った体制・高いブランド力","難易度：最難関〜難関","年収：高水準・安定","向いている人：安定志向／大きな仕事・体制で学びたい",
    ], callout=("POINT","注意：裁量は出にくく、配属・異動は会社都合になりがち。"))
    dk.content("メガベンチャー","成長と裁量の両立",[
        "特徴：急成長・規模もそこそこ・裁量も大きい","難易度：難関（人気が上昇中）","年収：高め・上昇余地あり","向いている人：成長と裁量を両立したい",
    ], callout=("POINT","注意：変化が速く、求められる水準も高い。"))
    dk.content("中堅・中小","早く幅広く任される",[
        "特徴：幅広い業務・地域密着・社長との距離が近い","難易度：中（狙いやすい）","年収：中（企業差が大きい）","向いている人：早くいろいろ任されたい／裁量がほしい",
    ], callout=("POINT","注意：ブランド・制度・教育体制は企業差が大きい。"))
    dk.content("ベンチャー","スピードと自走",[
        "特徴：少人数・スピード重視・裁量が大きい","難易度：中（実力・カルチャー適合を重視）","年収：幅広い","向いている人：自走できる／成長スピード最優先",
    ], callout=("POINT","注意：不安定・体制が未整備なことも。覚悟が要る。"))
    dk.content("スタートアップ","0→1を作る",[
        "特徴：創業期・0→1・ストックオプションの可能性","難易度：中（実力重視）","年収：変動大（株式で大きく上振れも）","向いている人：リスクを取れる／事業を自分で作りたい",
    ], callout=("NG","注意：倒産リスク・多忙。生活の安定とは両立しにくい時期も。"))
    dk.divider("03","PART 3","学生への伝え方")
    dk.content("規模選びのリアル","固定観念をほぐす",[
        "大手＝安定だが、配属・異動のリスクもある","ベンチャー＝成長だが、当たり外れがある","“規模”より“何をしたいか・誰と働くか”","1社目で全てが決まるわけではない（転職前提のキャリアも）",
    ])
    dk.diagram("flow","FLOW ・ 面談での提案","価値観と規模を照合する",
        [("①","価値観を聞く","安定／成長／年収／裁量"),("②","固定観念をほぐす","大手＝正解を疑う"),
         ("③","複数を比較","規模を横並びにする"),("④","照らし合わせる","“向いている人”と本人")],
        note="規模に優劣はない。学生の軸に“合うか”だけが判断基準。")
    dk.work("WORK ・ 演習","学生に規模を提案する","「安定志向の学生」と「成長志向の学生」、それぞれに合う規模カテゴリを根拠つきで提案","各カテゴリのメリット・デメリットを言えるか確認","固定観念に流されず、本人の軸で選ぶ")
    dk.deepen()
    dk.checklist("CHECK ・ 到達チェック","合格ライン",[
        "6カテゴリの違いを説明できる","6つの軸で比較できる","各カテゴリの“向いている人”を言える","学生の志向に合わせて提案できる",
    ])
    dk.closing("NEXT ・ まとめ","規模に優劣なし、“合うか”が全て",[
        "規模＝安定・年収・裁量・リスクのトレードオフ","軸で比較し、学生の納得を作る","次：F2 業界・職種理解（業界タブ）へ",
    ], "（業界マップ・業界内定攻略タブとあわせて）","")

def build_lateral(dk):
    dk.tag="D9 ラテラルシンキング"
    dk.cover("D9","思考・分析","ラテラルシンキング","“前提を疑い”常識の外から発想する","1時間")
    dk.content("GOAL ・ このモジュールのゴール","読み終えたらできること",[
        "垂直思考（ロジカル）と水平思考（ラテラル）の違いを説明できる","前提を疑い、多様な発想を出せる","発想法を使って打ち手の選択肢を広げられる",
    ], numbered=True, callout=("POINT","正解を1つに絞る思考と、答えを無数に広げる思考。両方を使い分ける。"))
    dk.divider("01","PART 1","ラテラルシンキングとは")
    dk.content("水平思考と垂直思考","掘るか、広げるか",[
        "垂直思考（ロジカル）＝筋道を立てて深く掘る","水平思考（ラテラル）＝前提を外して横に広げる","答えは1つでなく“無数”にある","“正しさ”より“新しさ・面白さ”を重視",
    ])
    dk.content("なぜ必要か","ロジカルだけでは平凡になる",[
        "前例のない問題・行き詰まりに効く","差別化・イノベーションの源泉","“当たり前”の外に答えがある","発想の幅が、打ち手の幅になる",
    ])
    dk.content("3つの基本姿勢","発想を止めない構え",[
        "①前提を疑う（本当にそうか？）","②抽象化して捉え直す（要するに何か？）","③偶然・組み合わせを歓迎する","批判・評価は後回しにする",
    ], callout=("POINT","『当たり前』を疑うと、新しい問いが生まれる。"))
    dk.divider("02","PART 2","発想の技法")
    dk.content("前提を疑う“問い”","視点を反転させる",[
        "「なぜそれをやるのか？」","「そもそも〜は必要か？」","「逆にしたらどうなる？」","「制約がなければ何をする？」",
    ])
    dk.diagram("relation","TECHNIQUE ・ 発想を広げる技法","引き出しを増やす",
        ("発想を広げる",["ブレスト","アナロジー","SCAMPER","ランダム刺激"]),
        note="量を出す（ブレスト）・別分野から借りる（アナロジー）・型で変形（SCAMPER）・偶然と結ぶ（ランダム刺激）。")
    dk.content("クイズで体感する","固定観念が答えを狭める",[
        "9つの点を4本の直線で一筆書き→“枠の外”に出る","マッチ6本で正三角形4つ→平面でなく立体で","「答えは1つ」という思い込みを外す","解けない時は“前提”を疑う",
    ], callout=("POINT","枠（前提）の外に出て初めて解ける問題がある。"))
    dk.divider("03","PART 3","実務で使う")
    dk.content("CA・ビジネスでの活用","視点を変えて打開する",[
        "求人の見せ方を変える（弱み→別角度の魅力）","学生の強みを別の言葉で言語化する","集客・説明会・企画のアイデア出し","行き詰まった面談を別角度から打開",
    ])
    dk.diagram("before_after","USE ・ ロジカルとの使い分け","発散→収束のセット",
        (("発散：ラテラル","広げる・たくさん出す・まず量"),("収束：ロジカル","根拠で選ぶ・絞る・それから質")),
        note="アイデアは“広げてから絞る”。最初から正解を狙わない。2つは対立でなく補完関係。")
    dk.work("WORK ・ 演習","前提を外して発想する","『新卒の説明会、参加者を増やすには？』を“前提を外して”20案出す","ルール：質より量・批判禁止・突飛OK","出た案から、ロジカルに実行する1つを選ぶ")
    dk.checklist("CHECK ・ 到達チェック","合格ライン",[
        "垂直思考と水平思考の違いを言える","前提を疑う問いを立てられる","発想技法（ブレスト/SCAMPER等）を使える","発散と収束を使い分けられる",
    ])
    dk.closing("NEXT ・ まとめ","前提を疑い、横に広げる",[
        "ラテラル＝前提を外して答えを無数に広げる","発散はラテラル・収束はロジカル","次：D2 ビジネス分析 ／ E4 チームビルディング",
    ], "（ロジカルシンキングD1とセットで）","")

def build_team(dk):
    dk.tag="E4 チームビルディング"
    dk.cover("E4","自己・対人","チームビルディング","“1人の100歩より、100人の1歩”","1時間")
    dk.content("GOAL ・ このモジュールのゴール","読み終えたらできること",[
        "良いチームの条件を説明できる","チームの成長段階（タックマンモデル）を理解する","合意形成（コンセンサス）を体験し実践できる",
    ], numbered=True, callout=("POINT","成果はスキルの足し算でなく、関係性の掛け算で決まる。"))
    dk.divider("01","PART 1","良いチームとは")
    dk.content("チームとグループの違い","ただの集まりではない",[
        "グループ＝同じ場所にいるだけの集まり","チーム＝共通の目的へ補完し合う集団","1＋1を3にする（相乗効果）","役割と相互依存がある",
    ])
    dk.content("良いチームの条件","土台は心理的安全性",[
        "共通の目的・目標がある","心理的安全性（誰もが安心して発言できる）","役割と責任が明確","信頼と相互理解がある",
    ], callout=("POINT","効果的なチームの最重要因子は心理的安全性（Google プロジェクトアリストテレス）。"))
    dk.diagram("timeline","TIMELINE ・ タックマンモデル","チームは段階で育つ",
        [("形成期","集まったばかり"),("混乱期","対立・衝突が起きる"),("統一期","役割と規範が定まる"),("機能期","最大の成果が出る")],
        note="混乱期（対立）を避けず乗り越える。衝突は成長の通過点。機能期で最大の成果が出る。")
    dk.divider("02","PART 2","チームで成果を出す")
    dk.content("役割分担と協働","得意で補い合う",[
        "得意を活かし、苦手を補う","報連相で情報をそろえる","目的を共有し続ける","一人で抱え込まない",
    ])
    dk.content("合意形成（コンセンサス）","納得で決める",[
        "多数決でなく“納得”で決める","全員の意見を出し切る","反対意見も検討材料にする","質の高い決定は“プロセス”から生まれる",
    ], callout=("POINT","早く決めるより、“納得して決める”方が結果的に強い。"))
    dk.divider("03","PART 3","ワーク：砂漠の遭難ゲーム")
    dk.work("WORK ・ 砂漠の遭難ゲーム","チームで“生存アイテムの優先順位”を合意せよ","設定：飛行機が砂漠に不時着。手元に残った12個のアイテムを“生存に重要な順”に並べる","①まず個人で順位付け → ②チームで話し合い、1つの順位に合意（多数決・平均は禁止）","③専門家の模範順位と比べ、個人とチーム、どちらが近いかを確認する")
    dk.content("シナリオと12個のアイテム","“生存に重要な順”に並べる",[
        "7月の正午、灼熱のサハラ砂漠に不時着。最寄りの町まで約100km・気温50℃","懐中電灯／ジャックナイフ／この地域の航空写真の地図／ビニールの雨具","磁石コンパス／救急セット／45口径ピストル／塩の錠剤／1人1Lの水","「食用になる砂漠の動物」の本／サングラス／1人2Lのウォッカ",
    ], callout=("POINT","この12個を、生死を分ける“重要度の高い順”に1〜12位で並べる。"))
    dk.diagram("flow","FLOW ・ 進め方と採点方法","個人 → チーム → 答え合わせ",
        [("①","個人で順位付け","約5分・相談なし"),("②","チームで合意","約15分/多数決・平均は禁止"),("③","差を計算","専門家の順位との差の合計"),("④","比べる","個人とチームの差を比較")],
        note="差が小さいほど生存に近い。チームの差が個人より小さければ集合知が働いた証拠。")
    dk.content("“正解”の考え方（生存の原則）","動くな、留まって発見されろ",[
        "原則①：その場にとどまり救助を待つ（歩いて移動＝死を早める）","原則②：体力を温存し脱水を防ぐ（日中は動かない）","だから上位＝鏡（救助信号）・雨具／水（脱水防止）・懐中電灯（夜間の信号）","下位＝地図・コンパス（“移動”を促す＝生存戦略に反する）",
    ], callout=("POINT","生存の鍵は“移動”でなく“留まって生き延び、発見されること”。"))
    dk.content("砂漠ゲームの学び","“集合知”を体感する",[
        "多くの場合、チームの答えが個人の平均を上回る","声の大きい人で決めない（根拠で決める）","意見を出し合うほど精度が上がる","“合意のプロセス”こそチーム力の正体",
    ], callout=("POINT","良い話し合いは、メンバー個人の最高得点をチームが超える。"))
    dk.content("ふりかえりの問い（デブリーフ）","体験を学びに変える",[
        "チームの点数は、個人の平均より良かった？ なぜ？","意見が割れた時、どうやって合意した？","声の大きい人や役職に流されなかった？","この学びを、日々のチーム（面談・案件）にどう活かす？",
    ], callout=("POINT","ゲームは“やって終わり”でなく、ふりかえりで初めて学びになる。"))
    dk.content("現場での活かし方","日々の仕事はチーム戦",[
        "面談・提案も一人で抱えず相談する","違う視点（RA／先輩）を巻き込む","対立を恐れず、事実と目的で議論する","チームの目標（売上・支援数）を自分ごとに",
    ])
    dk.checklist("CHECK ・ 到達チェック","合格ライン",[
        "チームとグループの違いを言える","良いチームの条件を挙げられる","タックマンモデルを説明できる","合意形成を実践できる（多数決に逃げない）",
    ])
    dk.closing("NEXT ・ まとめ","関係性の掛け算で勝つ",[
        "チーム＝目的のために補完し合う集団","心理的安全性が土台・合意は納得で","次：E2 傾聴 ／ E3 セルフマネジメント",
    ], "（砂漠ゲーム＝コンセンサス実習）","")


# モジュールID → (総ページ数, ビルド関数, プレゼン名)
DECKS={
 "C4":(16,build_present,"プレゼン資料作成"),
 "D1":(16,build_logical,"ロジカル/クリティカルシンキング"),
 "D5":(12,build_hypothesis,"仮説思考"),
 "D6":(12,build_issue,"論点思考"),
 "D7":(13,build_problem,"問題解決力"),
 "D8":(12,build_fermi,"フェルミ推定"),
 "D2":(14,build_analysis,"ビジネス分析(SWOT/3C)"),
 "C8":(14,build_sales_doc,"営業資料・提案資料の作り方"),
 "C7":(32,build_ai_use,"AIの使い方講座"),
 "C9":(10,build_gmail,"Gmail活用"),
 "C10":(9,build_ext,"おすすめ拡張機能"),
 "F1":(16,build_interview,"面談スキル"),
 "F4":(13,build_closing,"クロージング"),
 "E2":(13,build_listening,"傾聴・コミュニケーション"),
 "F3":(12,build_company_intro,"企業紹介文の書き方"),
 "F5":(12,build_law,"職業安定法・個人情報"),
 "D3":(10,build_research,"情報収集・リサーチ"),
 "D4":(13,build_goal,"目標設定(MBO/OKR)"),
 "E3":(11,build_selfmgmt,"セルフマネジメント"),
 "G1":(13,build_compliance,"コンプライアンス基礎"),
 "G2":(10,build_privacy,"個人情報保護"),
 "C5":(9,build_slack,"Slackの使い方"),
 "C6":(13,build_sf,"Salesforceの使い方"),
 "C11":(36,build_claude_code,"Claude Code活用(応用)"),
 "C12":(26,build_claude_setup,"Claude Codeセットアップ＆活用(VSCode)"),
 "F6":(18,build_company_size,"企業規模の地図(大手〜スタートアップ)"),
 "D9":(15,build_lateral,"ラテラルシンキング"),
 "E4":(14,build_team,"チームビルディング"),
 "B2":(15,build_hourenso,"報連相"),
 "B1":(22,build_manner,"ビジネスマナー"),
 "B4":(13,build_phone,"電話応対"),
 "B6":(13,build_boss,"上司とのコミュニケーション"),
 "G5":(12,build_incident,"インシデント対応"),
 "G6":(12,build_claim,"クレーム対応"),
 "A1":(25,build_company,"Tokumori理解・事業理解"),
 "A2":(16,build_mindset,"社会人マインドセット"),
 "A3":(21,build_industry,"人材紹介業界の全体像"),
 "B3":(10,build_email,"ビジネスメール"),
 "B5":(8,build_minutes,"議事録作成"),
 "E1":(9,build_disc,"DISC理論"),
 "G3":(8,build_security,"情報セキュリティ"),
 "G4":(8,build_harass,"ハラスメント研修"),
}


def link_to_sheet(sheets,ssid,mid,url,label="スライドを開く"):
    vals=sheets.spreadsheets().values().get(spreadsheetId=ssid,range="カリキュラム一覧!B6:B100").execute().get("values",[])
    row=next((6+i for i,r in enumerate(vals) if r and r[0]==mid),None)
    if row: sheets.spreadsheets().values().update(spreadsheetId=ssid,range="カリキュラム一覧!J%d"%row,valueInputOption="USER_ENTERED",body={"values":[['=HYPERLINK("%s","%s")'%(url,label)]]}).execute()
    return row


def main():
    global HERO_BG_URL
    set_theme(os.environ.get("THEME","training"))  # 既定=training（脱AI赤editorial）／training_v2=新デザイン
    creds=Credentials.from_authorized_user_file(TOK)
    if not creds.valid: creds.refresh(Request())
    slides=build("slides","v1",credentials=creds); sheets=build("sheets","v4",credentials=creds)
    MAPF=os.path.join(BASE, os.environ.get("MAPF",".slide_map.json"))  # v2は .slide_map_v2.json で別管理（既存ID不変）
    SUFFIX=os.environ.get("TITLE_SUFFIX","")
    smap=json.load(open(MAPF)) if os.path.exists(MAPF) else {}
    legacy=os.path.join(BASE,".slide_hourenso")
    if "B2" not in smap and os.path.exists(legacy): smap["B2"]=open(legacy).read().strip()
    # training_v2: 表紙/章扉の淡赤グラデ背景＋図のHTMLハイブリッド用 uploader を準備
    uploader=None
    if THEME=="training_v2":
        import html_to_slide as H
        dr=build("drive","v3",credentials=creds)
        def uploader(html,w,h):  # HTML→PNG(DPI4)→Drive→画像URL
            return "https://drive.google.com/uc?export=download&id=%s"%H.upload_drive(dr,H.render_png_fromstr(html,w,h,4))
        try:
            HERO_BG_URL="https://drive.google.com/uc?export=download&id=%s"%H.upload_drive(dr,H.render_png_fromstr(GLOW_HTML,1280,720,3))
            print("glow bg:",HERO_BG_URL)
        except Exception as e:
            print("glow render skipped:",str(e)[:80])
    only=os.environ.get("DECKS","").split(",") if os.environ.get("DECKS") else list(DECKS.keys())
    fails=[]
    for mid in only:
        if mid not in DECKS: continue
        total,fn,name=DECKS[mid]; title="%s｜Tokumori新卒研修%s"%(name,SUFFIX)
        try:
            if smap.get(mid):
                pres=slides.presentations().get(presentationId=smap[mid]).execute(); pid=smap[mid]
                delr=[{"deleteObject":{"objectId":s["objectId"]}} for s in pres.get("slides",[])]
            else:
                pres=slides.presentations().create(body={"title":title}).execute(); pid=pres["presentationId"]; smap[mid]=pid
                delr=[{"deleteObject":{"objectId":pres["slides"][0]["objectId"]}}]
                json.dump(smap,open(MAPF,"w"),ensure_ascii=False,indent=0)  # ID作成直後に保存（クラッシュでIDを失わない）
            dk=Deck(total=total,nonce="z"+uuid.uuid4().hex[:4]); dk.uploader=uploader; fn(dk)
            reqs=delr+dk.reqs  # 旧スライド削除を先に（生成失敗時の累積=二重化を防ぐ）
            safe_bu(slides,pid,reqs)
            time.sleep(2)
            url="https://docs.google.com/presentation/d/%s/edit"%pid
            # v2(新デザイン・別マップ)はカリキュラム一覧のJ/Kリンクを書き換えない（既存運用を保持）
            row=None
            if THEME!="training_v2": row=link_to_sheet(sheets,SSID,mid,url)
            print("%s %s -> %d pages  row=%s  %s"%(mid,name,dk.page,row,url))
        except Exception as e:
            fails.append(mid); print("!! %s FAILED: %s"%(mid,str(e)[:120]))
        json.dump(smap,open(MAPF,"w"),ensure_ascii=False,indent=0)
    if fails: print("FAILED decks (再実行を):",fails)
    json.dump(smap,open(MAPF,"w"),ensure_ascii=False,indent=0)
    print("DONE decks:",list(smap.keys()),"-> map:",MAPF)

if __name__=="__main__":
    main()
