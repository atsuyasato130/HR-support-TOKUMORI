#!/usr/bin/env python3
"""
Tokumori 新卒研修ハブ（研修プログラム）ビルダー v2「Light & whitespace」
既存ライブSS(業界×職種 v1)を再利用し、研修ハブ(14タブ)へ拡張・全タブをライト設計で再描画。
認証 = hr_support token_sheets.json（Sheets API）。
データ = data_ca_training.json（業界×職種）＋ data_training.json（カリキュラム/教材/ショートカット/関数/週間）。
"""
import json, math, os, warnings
warnings.filterwarnings("ignore")
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

BASE = "/Users/atsuyasato/Claude AI"
TOK = "/Users/atsuyasato/Claude AI/tokumori/agents/hr_support/config/token_sheets.json"
SSID = open(os.path.join(BASE, ".ca_sheet_id")).read().strip()
D = json.load(open(os.path.join(BASE, "data_ca_training.json"), encoding="utf-8"))
TR = json.load(open(os.path.join(BASE, "data_training.json"), encoding="utf-8"))
FIT = json.load(open(os.path.join(BASE, "data_industry_fit.json"), encoding="utf-8"))
MKT = json.load(open(os.path.join(BASE, "data_industry_market.json"), encoding="utf-8"))["MARKET"]
OUT = json.load(open(os.path.join(BASE, "data_industry_outlook.json"), encoding="utf-8"))["OUTLOOK"]
JOBOUT = json.load(open(os.path.join(BASE, "data_job_outlook.json"), encoding="utf-8"))["OUTLOOK"]

# ===== カラー v2（ライト） =====
RED="AF322C"; INK="1A1A1A"; SUB="6B6B6B"; WHITE="FFFFFF"
RULE="E8E6E4"; HRULE="C9C7C5"; ZEBRA="FAFAF9"; LINK="1155CC"
OK_BG="E6F4EA"; OK_FG="137333"; WIP_BG="FEF7E0"; WIP_FG="B06000"; NG_BG="FCE8E6"; NG_FG="C5221F"

def rgb(h):
    return {"red":int(h[0:2],16)/255,"green":int(h[2:4],16)/255,"blue":int(h[4:6],16)/255}


class SM:
    def __init__(self, sid):
        self.id=sid; self.grid={}; self.merges=[]; self.col_px={1:30}; self.row_px={}
        self.freeze=(0,0); self.filter=None; self.validations=[]; self.cfmts=[]; self.cfmt_formulas=[]
    def put(self,r,c,v="",**f): self.grid[(r,c)]=(v,f)
    def fill(self,r1,c1,r2,c2,**f):
        for r in range(r1,r2+1):
            for c in range(c1,c2+1):
                if (r,c) in self.grid:
                    v,ff=self.grid[(r,c)]; ff=dict(ff); ff.update(f); self.grid[(r,c)]=(v,ff)
                else: self.grid[(r,c)]=("",dict(f))
    def merge(self,r1,c1,r2,c2): self.merges.append((r1,c1,r2,c2))


# ===== ヘルパー（ライト設計） =====
def section(sm,row,col,text,width):
    """赤文字＋赤い下線（全幅塗りなし・非結合）"""
    sm.fill(row,col,row,col+width-1, underline=True)
    sm.put(row,col,text, font=RED, bold=True, size=13, valign="MIDDLE", underline=True)
    sm.row_px[row]=32

def note(sm,row,col,span,text,size=10,color=SUB):
    sm.put(row,col,text, font=color, size=size, wrap=True, valign="MIDDLE")
    sm.merge(row,col,row,col+span-1)
    per=sum(sm.col_px.get(col+x,90) for x in range(span))/14.0
    sm.row_px[row]=min(120,max(20,math.ceil(len(str(text))/max(6,per))*16+4))
    return row+1

def kpi(sm,row,items,start,width):
    c=start
    for it in items:
        sm.put(row,c,it["label"], font=SUB, size=10, bold=True, valign="BOTTOM")
        sm.put(row+1,c,it["value"], font=(RED if it.get("accent") else INK), bold=True, size=22, valign="MIDDLE")
        sm.fill(row+2,c,row+2,c+width-1, underline=True)  # 赤の細い下線
        c+=width
    sm.row_px[row]=20; sm.row_px[row+1]=40; sm.row_px[row+2]=4

def tbl(sm,row,col,header,rows,col_px,zebra=False,red_cols=None,pop_col=None,link_col=None,text_cols=None):
    w=len(header)
    for j,h in enumerate(header):
        sm.put(row,col+j,h, font=INK, bold=True, size=10, valign="MIDDLE", wrap=True, hrule=True)
    sm.row_px[row]=26
    for i,rd in enumerate(rows):
        rr=row+1+i; bg=ZEBRA if (zebra and i%2) else WHITE
        for j,val in enumerate(rd):
            f=dict(font=INK,size=10,valign="TOP",wrap=True,sep=True)
            if bg!=WHITE: f["bg"]=bg
            if red_cols and j in red_cols: f["font"]=RED; f["bold"]=True
            if link_col is not None and j==link_col and isinstance(val,str) and val.startswith("="):
                f["font"]=LINK
            if text_cols and j in text_cols: f["astext"]=True
            sm.put(rr,col+j,val,**f)
        if pop_col is not None:
            v=str(rd[pop_col]); pf = RED if v[:1]=="高" else (SUB if "低" in v else INK)
            sm.put(rr,col+pop_col,rd[pop_col], font=pf, bold=(v[:1]=="高"), size=10, valign="TOP", wrap=True, sep=True, halign="CENTER")
    for j,px in enumerate(col_px): sm.col_px[col+j]=px
    return row+len(rows)+2

def mtbl(sm,row,start,header,spans,rows,red_cols=None,link_col=None):
    c=start
    for k,h in enumerate(header):
        sm.fill(row,c,row,c+spans[k]-1, hrule=True)
        sm.put(row,c,h, font=INK, bold=True, size=10, valign="MIDDLE", wrap=True, hrule=True)
        sm.merge(row,c,row,c+spans[k]-1); c+=spans[k]
    sm.row_px[row]=26
    for i,rd in enumerate(rows):
        rr=row+1+i; c=start; mx=1
        for k,val in enumerate(rd):
            sm.fill(rr,c,rr,c+spans[k]-1, sep=True)
            f=dict(font=INK,size=10,valign="TOP",wrap=True,sep=True)
            if link_col is not None and k==link_col and str(val).startswith("http"):
                sm.put(rr,c,'=HYPERLINK("%s","%s")'%(val,val), font=LINK, size=9, valign="TOP", wrap=True, sep=True)
            else:
                if red_cols and k in red_cols: f["font"]=RED; f["bold"]=True
                sm.put(rr,c,val,**f)
            sm.merge(rr,c,rr,c+spans[k]-1); mx=max(mx,len(str(val))); c+=spans[k]
        sm.row_px[rr]=min(180,max(20,math.ceil(mx/30)*16+6))
    return row+len(rows)+2

def hlink(gid,label): return '=HYPERLINK("#gid=%d","%s")'%(gid,label)
def stage_label(ph):
    if "Week1" in ph: return "Stage1｜基礎(初期必修)"
    if "Week2" in ph: return "Stage2｜応用"
    if "Week3" in ph: return "Stage3｜実践"
    return ph


# ===== タブ・ビルダー =====
def build_home(sm,G):
    for c,p in enumerate([150,150,150,150,150,150,150,150]): sm.col_px[2+c]=p
    sm.put(2,2,"Tokumori 新卒研修プログラム", font=RED, bold=True, size=20, valign="MIDDLE"); sm.row_px[2]=44
    note(sm,3,2,8,"大手に遜色ない新卒研修のハブ。基礎は1週間で完了する密度。詳細はGoogleスライド、概要・進捗はこのスプレッドシートで管理します。", size=11, color=INK)
    kpi(sm,5,[{"label":"研修モジュール","value":len(TR["CURRICULUM"]),"accent":True},
              {"label":"基礎の期間","value":"1週間","accent":True},
              {"label":"カテゴリ","value":"A〜G (7)","accent":False},
              {"label":"業界×職種 収録","value":"36×41","accent":False}],2,2)
    r=9
    section(sm,r,2,"目次（クリックで各タブへ）",8); r+=1
    rows=[
        [hlink(G["カリキュラム一覧"],"カリキュラム一覧"),"A〜G 全モジュールの目標/時間/到達基準/フェーズ/教材リンク"],
        [hlink(G["週間プログラム"],"週間プログラム"),"基礎研修 Day1〜5 の時間割"],
        [hlink(G["進捗管理"],"進捗管理"),"受講者ごとの進捗（ステータス/完了日/点数）"],
        [hlink(G["YouTube教材"],"YouTube教材"),"テーマ別の動画教材リンク集"],
        [hlink(G["ショートカット"],"ショートカット"),"Windows/Mac/スプレッドシートのショートカット一覧"],
        [hlink(G["関数ワーク"],"関数ワーク"),"頻出関数の一覧＋演習課題"],
        [hlink(G["業界詳細"],"業界マップ/詳細ほか"),"業界・職種理解モジュール（業界36×職種41）"],
    ]
    r=tbl(sm,r,2,["タブ","内容"],rows,[200,560],link_col=0); r+=1
    section(sm,r,2,"研修の進め方",8); r+=1
    for t in ["1. 週間プログラム(Day1-5)に沿って基礎を1週間で完了する。",
              "2. 各モジュールはカリキュラム一覧の教材リンク(Googleスライド)＋YouTube教材で学ぶ。",
              "3. 受講後に進捗管理タブのステータスを更新し、確認テストを受ける。",
              "4. 基礎修了後、応用フェーズ(思考法・分析・CA職種特化)へ進む。"]:
        r=note(sm,r,2,8,t,size=10,color=INK)
    r+=1
    note(sm,r,2,8,"運用メモ：詳細スライドはGoogleスライドで作成しカリキュラム一覧にリンク。確認テストはGoogleフォーム等を作成しリンク。データは順次拡充。", size=9, color=SUB)
    sm.freeze=(1,0)

YT_MAP={
 "B1":"https://www.youtube.com/watch?v=hzE51hMi-sY","B2":"https://www.youtube.com/watch?v=-_qTEUo1v28",
 "B4":"https://www.youtube.com/watch?v=TJijEwCubNk","B5":"https://www.youtube.com/watch?v=-Inac4T8kQ8",
 "C1":"https://sushida.net/","C2":"https://support.google.com/docs/answer/181110?hl=ja",
 "C3":"https://support.google.com/docs/table/25273?hl=ja","C4":"https://www.youtube.com/@tpu","C8":"https://www.youtube.com/@tpu",
 "C7":"https://www.youtube.com/watch?v=UIyokWUJHck","D1":"https://www.youtube.com/watch?v=WcWX_7HEfGQ",
 "D2":"https://globis.jp/article/5541/","E1":"https://workhappiness.co.jp/blog/trend/disc/",
 "E2":"https://www.youtube.com/watch?v=QyOWqxwNKTA","F1":"https://www.youtube.com/watch?v=QyOWqxwNKTA","B6":"https://www.youtube.com/watch?v=QyOWqxwNKTA",
}
def build_curriculum(sm,G):
    px=[44,138,196,280,62,240,104,108,132,118,150]
    for c,p in enumerate(px): sm.col_px[2+c]=p
    sm.put(1,12,hlink(G["研修ホーム"],"← 研修ホーム"), font=SUB, size=9, halign="RIGHT"); sm.row_px[1]=16
    section(sm,2,2,"研修カリキュラム一覧（A〜G）",11)
    note(sm,3,2,11,"各モジュールの完了条件＝『到達基準を満たす ＋ 確認テスト90点以上 ＋ 上長承認』。スライド・YouTube・テストはこの1タブに集約。Stageは 初期必修(1)→応用(2)→実践(3)。",size=10,color=SUB)
    header=["ID","カテゴリ","モジュール","学習目標","所要時間","到達基準(完了条件)","形式","ステージ/フェーズ","教材リンク","確認テスト","YouTube/教材"]
    def yt(mid):
        u=YT_MAP.get(mid,""); return ('=HYPERLINK("%s","動画/教材を見る")'%u) if u else ""
    rows=[r[:7]+[stage_label(r[7]),"","",yt(r[0])] for r in TR["CURRICULUM"]]
    head=5; n=len(rows)
    tbl(sm,head,2,header,rows,px,zebra=True,red_cols=[0],link_col=10)
    sm.freeze=(head,0); sm.filter=(head,2,head+n,12)

def build_weekly(sm,G):
    px=[96,64,80,330,130,170]
    for c,p in enumerate(px): sm.col_px[2+c]=p
    sm.put(1,8,hlink(G["研修ホーム"],"← 研修ホーム"), font=SUB, size=9, halign="RIGHT"); sm.row_px[1]=16
    section(sm,2,2,"週間プログラム（3週間：基礎→応用→実践）",6)
    note(sm,3,2,6,"Week1で社会人の基礎、Week2でビジネススキル、Week3でリスク対応＆CA実践。各内容はカリキュラム一覧・YouTube教材・スライドに紐づきます。",size=10,color=SUB)
    header=["Week","Day","時間帯","内容","モジュールID","形式"]
    tbl(sm,5,2,header,TR["WEEKLY"],px,zebra=True,red_cols=[0])
    sm.freeze=(5,0)

def build_progress(sm,G):
    px=[46,140,220,120,112,92,58,104,92,210]
    for c,p in enumerate(px): sm.col_px[2+c]=p
    sm.put(1,11,hlink(G["研修ホーム"],"← 研修ホーム"), font=SUB, size=9, halign="RIGHT"); sm.row_px[1]=16
    section(sm,2,2,"進捗管理（受講者ごとにこのタブを複製して配布）",10)
    note(sm,3,2,10,"運用：受講者が「自己ステータス」を更新 → 上長が「上長確認」で承認/差し戻し。色と進捗率は自動。1人1コピーで配布します。",size=10,color=SUB)
    sm.put(4,2,"受講者名", font=SUB, size=10, bold=True, valign="MIDDLE"); sm.put(4,3,"（氏名を入力）", font=INK, size=11, sep=True)
    sm.put(4,6,"上長名", font=SUB, size=10, bold=True, valign="MIDDLE"); sm.put(4,7,"（上長名を入力）", font=INK, size=11, sep=True)
    head=9; n=len(TR["CURRICULUM"]); d0=head+1; d1=head+n
    fcol="F%d:F%d"%(d0,d1); bcol="B%d:B%d"%(d0,d1); icol="I%d:I%d"%(d0,d1)
    kpi(sm,5,[{"label":"自己完了","value":'=COUNTIF(%s,"完了")'%fcol,"accent":True},
              {"label":"上長承認","value":'=COUNTIF(%s,"承認")'%icol,"accent":True},
              {"label":"承認率","value":'=IFERROR(TEXT(COUNTIF(%s,"承認")/COUNTA(%s),"0%%"),"0%%")'%(icol,bcol),"accent":True}],5,2)
    header=["ID","カテゴリ","モジュール","ステージ","自己ステータス","完了日","点数","上長確認","確認日","上長コメント"]
    rows=[[m[0],m[1],m[2],stage_label(m[7]),"未着手","","","未確認","",""] for m in TR["CURRICULUM"]]
    tbl(sm,head,2,header,rows,px,zebra=True,red_cols=[0])
    # 自己ステータス(F=col6)
    sm.validations.append((d0,6,d1,6,["未着手","受講中","完了","要再受講"]))
    sm.cfmts.append((d0,6,d1,6,"完了",OK_BG,OK_FG)); sm.cfmts.append((d0,6,d1,6,"受講中",WIP_BG,WIP_FG)); sm.cfmts.append((d0,6,d1,6,"要再受講",NG_BG,NG_FG))
    # 上長確認(I=col9)
    sm.validations.append((d0,9,d1,9,["未確認","承認","差し戻し"]))
    sm.cfmts.append((d0,9,d1,9,"承認",OK_BG,OK_FG)); sm.cfmts.append((d0,9,d1,9,"差し戻し",NG_BG,NG_FG))
    sm.freeze=(head,0)

def build_wbs(sm,G):
    # WBS = 週軸ガント。Stage順にグルーピング＋帯見出し。研修開始日(C4)で予定・棒が自動表示
    DONE="B7E1C2"; WIP="FCE8B2"; PLAN="E6E8EB"; TODAY="FBE3E1"; ZONE="F7DAD7"
    DATEF={"type":"DATE","pattern":"m/d"}; PCT={"type":"PERCENT","pattern":"0%"}
    NW=16  # 週数（=16週・約4ヶ月。Stage3はOJTで以降も継続）
    head=12; wk=head-1  # head=ヘッダ(週=日付)行 / wk=週番号行(W1..)
    wlast=10+NW-1
    nrow=len(TR["CURRICULUM"])+3  # モジュール45＋Stage帯3
    d0=head+1; d1=head+nrow      # 内容ブロック先頭〜末尾
    sm.col_px[2]=92; sm.col_px[3]=44; sm.col_px[4]=250; sm.col_px[5]=62; sm.col_px[6]=62; sm.col_px[7]=86; sm.col_px[8]=80; sm.col_px[9]=60
    for c in range(10,10+NW): sm.col_px[c]=38
    sm.put(1,wlast,hlink(G["研修ホーム"],"← 研修ホーム"), font=SUB, size=9, halign="RIGHT"); sm.row_px[1]=16
    section(sm,2,2,"WBS（ガントチャート・予定と進捗）",NW+8)
    sm.put(3,2,"凡例: 緑=完了 ／ 橙=着手中 ／ 灰=予定 ／ 薄赤=今週・Stage1ゾーン｜まずStage1を3週間（W1–W3）で完了が目標。研修開始日を入れると予定・棒が自動表示。", font=SUB, size=9, valign="MIDDLE"); sm.row_px[3]=18
    sm.put(4,2,"研修開始日", font=SUB, size=10, bold=True, valign="MIDDLE")
    sm.put(4,3,"", numfmt={"type":"DATE","pattern":"yyyy/m/d"}, bg=WIP, halign="CENTER", valign="MIDDLE", bold=True)
    sm.put(4,5,"← ここに開始日を入力（例 2026/4/1）", font=SUB, size=9, valign="MIDDLE")
    kpi(sm,5,[
        {"label":"全体進捗","value":'=IFERROR(TEXT(AVERAGE(I%d:I%d),"0%%"),"0%%")'%(d0,d1),"accent":True},
        {"label":"完了モジュール","value":'=COUNTIF(G%d:G%d,"完了")'%(d0,d1),"accent":True},
        {"label":"上長承認済","value":'=COUNTIF(H%d:H%d,"承認")'%(d0,d1),"accent":True},
    ],2,3)
    kpi(sm,8,[
        {"label":"Stage1進捗(目標3週)","value":'=IFERROR(TEXT(AVERAGEIFS(I%d:I%d,B%d:B%d,"Stage1*"),"0%%"),"0%%")'%(d0,d1,d0,d1),"accent":True},
        {"label":"Stage2 進捗","value":'=IFERROR(TEXT(AVERAGEIFS(I%d:I%d,B%d:B%d,"Stage2*"),"0%%"),"0%%")'%(d0,d1,d0,d1)},
        {"label":"Stage3 進捗","value":'=IFERROR(TEXT(AVERAGEIFS(I%d:I%d,B%d:B%d,"Stage3*"),"0%%"),"0%%")'%(d0,d1,d0,d1)},
    ],2,3)
    # 週番号行（W1..W16・Stage1ゾーンW1-3を薄赤）
    sm.put(wk,9,"週→", font=SUB, size=9, halign="RIGHT", valign="MIDDLE")
    for w in range(NW):
        z = ZONE if w<3 else None
        sm.put(wk,10+w,"W%d"%(w+1), font=(RED if w<3 else SUB), bold=True, size=9, halign="CENTER", valign="MIDDLE", **({"bg":z} if z else {}))
    sm.row_px[wk]=16
    # ヘッダ行（左ラベル＋週=開始日。Stage1ゾーン薄赤）
    for j,h in enumerate(["ステージ","ID","モジュール","開始予定","終了予定","ステータス","承認","進捗%"]):
        sm.put(head,2+j,h, font=INK, bold=True, size=10, valign="MIDDLE", wrap=True, hrule=True)
    for w in range(NW):
        ex = {"bg":ZONE} if w<3 else {}
        sm.put(head,10+w,'=IF($C$4="","",$C$4+%d)'%(w*7), numfmt=DATEF, font=INK, bold=True, size=9, halign="CENTER", valign="MIDDLE", hrule=True, **ex)
    sm.row_px[head]=22
    # 既定オフセット（Stage1=W1-3 / Stage2=W4-9 / Stage3=W10-16）
    SPAN={"Stage1":(0,20),"Stage2":(21,62),"Stage3":(63,111)}
    BANDS={"Stage1":"Stage1｜基礎　▶ 目標：3週間（W1–W3）で完了",
           "Stage2":"Stage2｜応用　▶ W4–W9",
           "Stage3":"Stage3｜実践　▶ W10–W16（OJTで以降も継続）"}
    by_stage={"Stage1":[],"Stage2":[],"Stage3":[]}
    for i,m in enumerate(TR["CURRICULUM"]): by_stage[stage_label(m[7])[:6]].append(i)
    rr=head; mi=0
    for sk in ["Stage1","Stage2","Stage3"]:
        idxs=by_stage[sk]; N=len(idxs); sd,ed=SPAN[sk]; span=ed-sd+1
        rr+=1  # Stage見出し（他タブのsection()と同じ＝赤文字＋赤い下線・塗りなし）
        sm.fill(rr,2,rr,wlast, underline=True)
        sm.put(rr,2,BANDS[sk], font=RED, bold=True, size=13, valign="MIDDLE", underline=True)
        sm.row_px[rr]=32
        for j,i in enumerate(idxs):
            rr+=1; m=TR["CURRICULUM"][i]
            st=sd+int(j*span/max(1,N)); dur=max(3, span//max(1,N)); en=min(ed, st+dur-1)
            sm.put(rr,2,stage_label(m[7]), font=SUB, size=9, valign="MIDDLE", sep=True)
            sm.put(rr,3,m[0], font=RED, bold=True, size=10, valign="MIDDLE", sep=True)
            sm.put(rr,4,m[2], font=INK, size=10, valign="MIDDLE", wrap=True, sep=True)
            sm.put(rr,5,'=IF($C$4="","",$C$4+%d)'%st, numfmt=DATEF, font=INK, size=9, halign="CENTER", valign="MIDDLE", sep=True)
            sm.put(rr,6,'=IF($C$4="","",$C$4+%d)'%en, numfmt=DATEF, font=INK, size=9, halign="CENTER", valign="MIDDLE", sep=True)
            sm.put(rr,7,"未着手", font=INK, size=10, halign="CENTER", valign="MIDDLE", sep=True)
            sm.put(rr,8,"未承認", font=INK, size=10, halign="CENTER", valign="MIDDLE", sep=True)
            sm.put(rr,9,'=IFS(G%d="完了",1,G%d="着手中",0.5,TRUE,0)'%(rr,rr), numfmt=PCT, font=INK, bold=True, size=10, halign="CENTER", valign="MIDDLE", sep=True)
            if mi%2: sm.fill(rr,2,rr,9, bg=ZEBRA)  # 他タブと同じ極薄ゼブラ（左データ列のみ・週列は白で棒を見せる）
            sm.row_px[rr]=26; mi+=1
    # 入力規則：ステータス(G=7)・承認(H=8)
    sm.validations.append((d0,7,d1,7,["未着手","着手中","完了"]))
    sm.validations.append((d0,8,d1,8,["未承認","承認","差し戻し"]))
    sm.cfmts.append((d0,7,d1,7,"完了",OK_BG,OK_FG)); sm.cfmts.append((d0,7,d1,7,"着手中",WIP_BG,WIP_FG))
    sm.cfmts.append((d0,8,d1,8,"承認",OK_BG,OK_FG)); sm.cfmts.append((d0,8,d1,8,"差し戻し",NG_BG,NG_FG))
    # ガント棒（カスタム式・優先順：完了>着手中>予定>今週）
    rng=(d0,10,d1,wlast)
    base='AND(J$%d<>"",J$%d<=$F%d,J$%d+6>=$E%d'%(head,head,d0,head,d0)
    sm.cfmt_formulas.append((*rng,'=%s,$G%d="完了")'%(base,d0),DONE,None))
    sm.cfmt_formulas.append((*rng,'=%s,$G%d="着手中")'%(base,d0),WIP,None))
    sm.cfmt_formulas.append((*rng,'=%s)'%base,PLAN,None))
    sm.cfmt_formulas.append((*rng,'=AND(J$%d<>"",J$%d<=TODAY(),J$%d+6>=TODAY())'%(head,head,head),TODAY,None))
    sm.freeze=(head,4); sm.filter=(head,2,d1,9)

def build_youtube(sm,G):
    px=[120,300,200,260,70,300,90]
    for c,p in enumerate(px): sm.col_px[2+c]=p
    sm.put(1,8,hlink(G["研修ホーム"],"← 研修ホーム"), font=SUB, size=9, halign="RIGHT"); sm.row_px[1]=16
    section(sm,2,2,"YouTube教材ライブラリ",7)
    note(sm,3,2,7,"テーマ別の動画/教材。確度=「要確認」のものは配布前に内容と尺を実視聴で確認してください。",size=10,color=SUB)
    header=["テーマ","タイトル","チャンネル","URL","長さ","メモ","確度"]
    rows=[[a,b,c,'=HYPERLINK("%s","%s")'%(d,d),e,f,g] for (a,b,c,d,e,f,g) in TR["YOUTUBE"]]
    tbl(sm,5,2,header,rows,px,zebra=True,red_cols=[0],link_col=3)
    sm.freeze=(5,0); sm.filter=(5,2,5+len(rows),8)

def build_shortcuts(sm,G):
    px=[150,300,230,230]
    for c,p in enumerate(px): sm.col_px[2+c]=p
    sm.put(1,5,hlink(G["研修ホーム"],"← 研修ホーム"), font=SUB, size=9, halign="RIGHT"); sm.row_px[1]=16
    section(sm,2,2,"ショートカットキー一覧",4)
    note(sm,3,2,4,"Win/Mac/スプレッドシート共通の頻出ショートカット。スプシは Ctrl+/(⌘+/) で画面に全一覧が出ます。",size=10,color=SUB)
    header=["カテゴリ","操作","Windows","Mac"]
    tbl(sm,5,2,header,TR["SHORTCUTS"],px,zebra=True,red_cols=[0])
    sm.freeze=(5,0); sm.filter=(5,2,5+len(TR["SHORTCUTS"]),5)

def build_functions(sm,G):
    px=[150,150,300,280,320]
    for c,p in enumerate(px): sm.col_px[2+c]=p
    sm.put(1,7,hlink(G["研修ホーム"],"← 研修ホーム"), font=SUB, size=9, halign="RIGHT"); sm.row_px[1]=16
    section(sm,2,2,"スプレッドシート関数 一覧",5)
    note(sm,3,2,5,"実務で頻出のスプレッドシート関数。用途→構文→例の順。練習用データは「関数練習」タブにあります。",size=10,color=SUB)
    r=tbl(sm,5,2,["関数","カテゴリ","用途","構文","例"],TR["FUNCTIONS"],px,zebra=True,red_cols=[0],text_cols=[3,4]); r+=1
    section(sm,r,2,"関数ワーク（実践課題）",5); r+=1
    r=tbl(sm,r,2,["課題","内容","ヒント"],TR["FUNC_WORK"],[180,420,360],zebra=True,red_cols=[0],text_cols=[2]); r+=1
    section(sm,r,2,"応用：QUERY関数（スプレッドシート専用の強力関数）",5); r+=1
    tbl(sm,r,2,["課題","内容","式の例（「関数練習」タブで動かせる）"],TR["FUNC_QUERY"],[180,300,420],zebra=True,red_cols=[0],text_cols=[2])
    sm.freeze=(5,0)

def build_renshu(sm,G):
    sm.put(1,8,hlink(G["研修ホーム"],"← 研修ホーム"), font=SUB, size=9, halign="RIGHT")
    tbl(sm,1,1,TR["FUNC_SAMPLE"][0],TR["FUNC_SAMPLE"][1:],[44,90,110,110,90,120],zebra=True,red_cols=[0])
    r=2+len(TR["FUNC_SAMPLE"])
    section(sm,r+1,2,"関数練習の使い方",6)
    note(sm,r+2,2,6,"上の表(A:F)を使って「関数ワーク」タブのQUERY例を試せます。空セルに =QUERY(関数練習!A:F, ...) を貼って結果を確認しましょう。VLOOKUP/COUNTIF/SUMIF等もこのデータで練習できます。",size=10,color=INK)
    sm.freeze=(1,0)

def build_idattack(sm,G):
    px=[140,200,235,225,170,175,195,195,205,200]
    for c,p in enumerate(px): sm.col_px[2+c]=p
    sm.put(1,8,hlink(G["研修ホーム"],"← 研修ホーム"), font=SUB, size=9, halign="RIGHT"); sm.row_px[1]=16
    section(sm,2,2,"業界別 内定攻略・適性＆アウトルック",10)
    note(sm,3,2,10,"向いている学生／内定が狙えるレベル／準備に加え、内定難易度の目安・採用の増減・AI代替リスク・年収の上がり方まで。学生へのキャリア相談の材料に（難易度/年収は概観、配布前に最新を要確認）。フィルタで絞り込み可。",size=10,color=SUB)
    names=[r[0] for r in D["INDUSTRIES"]]
    rows=[]
    for i in range(len(names)):
        fit=FIT[i] if i<len(FIT) else ["","","","",""]
        o=OUT[i] if i<len(OUT) else {}
        rows.append([names[i]]+list(fit[:3])+[o.get("内定難易度",""),o.get("採用トレンド",""),o.get("AI代替リスク",""),o.get("年収の上がり方","")]+list(fit[3:5]))
    header=["業界","向いている学生","内定が狙えるレベル(学歴/ガクチカ)","内定への準備","内定難易度(目安)","採用トレンド(増減)","AI代替リスク","年収の上がり方","採用人数の特徴","転職しやすさ・市場価値"]
    n=len(rows); tbl(sm,5,2,header,rows,px,zebra=True,red_cols=[0])
    sm.freeze=(5,0); sm.filter=(5,2,5+n,11)

def build_ai(sm,G):
    sm.put(1,8,hlink(G["研修ホーム"],"← 研修ホーム"), font=SUB, size=9, halign="RIGHT"); sm.row_px[1]=16
    section(sm,2,2,"AI活用ガイド（特にClaude）— どこよりもAIを使い倒す",6)
    r=note(sm,3,2,6,"当社はAI活用を最優先で推進します。わからないことはまずAIに聞き、下書き・要約・リサーチ・壁打ちに積極活用。ただし最終確認は自分／機密・個人情報は入れない。",size=11,color=INK); r+=1
    section(sm,r,2,"行動原則",6); r+=1
    r=tbl(sm,r,2,["原則","内容"],TR["AI_PRINCIPLES"],[220,620],zebra=True,red_cols=[0]); r+=1
    section(sm,r,2,"プロンプトの型（この順で書くと精度が上がる）",6); r+=1
    r=tbl(sm,r,2,["要素","書き方","例"],TR["AI_FORMAT"],[180,330,330],zebra=True,red_cols=[0]); r+=1
    section(sm,r,2,"業務別プロンプト例（コピーして使う）",6); r+=1
    r=tbl(sm,r,2,["場面","プロンプト例"],TR["AI_USECASES"],[200,640],zebra=True,red_cols=[0]); r+=1
    section(sm,r,2,"便利な設定",6); r+=1
    r=tbl(sm,r,2,["設定","内容"],TR["AI_SETTINGS"],[220,620],zebra=True,red_cols=[0]); r+=1
    # ===== Cowork／Claude Code クイックスタート（やり方ガイド）=====
    section(sm,r,2,"Cowork／Claude Code クイックスタート（やり方ガイド）",6); r+=1
    r=note(sm,r,2,6,"Claudeには“3つの顔”がある。Chat＝相談・下書き／Cowork＝デスクトップで自走し成果物を作るエージェント（非エンジニア向け）／Code＝ターミナルで自走する開発者向け。新卒がまず武器にすべきはCowork。",size=11,color=INK); r+=1
    tools=[
      ["Chat（claude.ai）","ブラウザ／アプリで対話","相談・下書き・要約・学習・壁打ち"],
      ["Cowork","Claudeデスクトップアプリ（Mac/Win・有料 Pro 約$17/月〜）","フォルダのファイル仕事を“完成物”に。Excel/PPT/Word/PDFを実物で生成"],
      ["Code（Claude Code）","ターミナル／エディタ（開発者向け）","コード・スクリプト・自動化。最も高度な自走エージェント"],
    ]
    r=tbl(sm,r,2,["ツール","実行環境","いつ使う"],tools,[160,330,350],zebra=True,red_cols=[0],text_cols=[1,2]); r+=1
    section(sm,r,2,"Coworkの始め方（5ステップ）",6); r+=1
    steps=[
      ["1. アプリを開く","Claude Desktopを開き「Cowork」タブに切り替える"],
      ["2. フォルダを許可","作業フォルダを接続し、アクセス権限を許可する"],
      ["3. ゴールを指示","やってほしい作業を文章で渡す（例：このデータを月次集計して）"],
      ["4. 計画を承認","提示された手順を確認してから実行（削除など重要操作は必ず承認）"],
      ["5. 成果物を受領","完成ファイル＋作業サマリを受け取り、自分で最終確認する"],
    ]
    r=tbl(sm,r,2,["ステップ","内容"],steps,[200,640],zebra=True,red_cols=[0],text_cols=[1]); r+=1
    section(sm,r,2,"演習：Coworkで“集計エージェント”を作る（関数ワーク連携）",6); r+=1
    r=note(sm,r,2,6,"① 「関数練習」タブのデータ（求職者×企業×ステータス×売上）を用意 → ② Coworkに『月次集計レポート（承諾率・企業別件数・売上合計）をスプレッドシートで作って』と指示 → ③ 自分が「関数ワーク」タブのQUERYで出した手集計と突き合わせて検証 → ④ 数字が合えばSkillとして保存＝“自分専用の集計エージェント”として再利用。",size=10,color=INK); r+=1
    section(sm,r,2,"Skillで“自分のエージェント”を作る",6); r+=1
    r=note(sm,r,2,6,"Skill＝Coworkに“やり方”を教える再利用ワークフロー。毎回説明せずワンコマンドで同じ品質を呼べる。『Skill Creator』で自作・改善できる。例：紹介文ドラフト／面談メモ要約／月次集計を自分専用化。重要操作の承認（HITL）と、機密・個人情報を入れない原則は必ず守る。",size=10,color=INK); r+=1
    section(sm,r,2,"さらに上へ：Claude Code（応用・開発者向け）",6); r+=1
    r=note(sm,r,2,6,"サブエージェント並列／MCP連携（SF・会議・自社API）／1Mコンテキスト／定期実行(cron)など、Coworkの土台になっている最前線の機能を使える。詳細はモジュール『C11 Claude Code活用（応用）』のスライドへ。出典：総務省 情報通信白書／McKinsey／WEF／Anthropic（各スライドに明記）。",size=10,color=SUB); r+=1
    sm.freeze=(0,0)

def build_kpi(sm,G):
    W=[140,150,320,200,130,240]
    for c,p in enumerate(W): sm.col_px[2+c]=p
    sm.put(1,8,hlink(G["研修ホーム"],"← 研修ホーム"), font=SUB, size=9, halign="RIGHT"); sm.row_px[1]=16
    section(sm,2,2,"目標・KPI ／ 独り立ちまでの道のり（半年・3ステージ）",6)
    r=note(sm,3,2,6,"全モジュール(Stage1→2→3)を半年以内にクリアで“独り立ち”。各モジュールの完了条件＝①到達基準を満たす ②確認テスト90点以上 ③上長承認。現場実務と並行して進めます。",size=10,color=INK); r+=1
    r=note(sm,r,2,6,"★本当のゴールは『担当する求職者が入社後に活躍し“ありたい自分”でいられること』。内定承諾・売上はそのための手段・結果であり、目的ではない。",size=10,color=RED); r+=1
    stg=[["Stage1｜基礎(初期必修)","入社〜約1ヶ月","社会人の基礎(マナー/報連相/ツール/コンプラ/個人情報)","Week1の全モジュールをクリア＝実務開始の最低ライン"],
         ["Stage2｜応用","約1〜3ヶ月","思考(論点/仮説/問題解決/フェルミ)・分析・資料作成・Gmail/拡張・面談入門","Week2の全モジュールをクリア＝自分で動ける"],
         ["Stage3｜実践","約3〜6ヶ月","面談/クロージング/業界職種/リスク対応(インシデント・クレーム)","Week3＋実務KPI達成＝独り立ち"]]
    r=tbl(sm,r,2,["ステージ","時期","内容","完了の目安"],stg,W[:4],zebra=True,red_cols=[0]); r+=1
    section(sm,r,2,"実務KPI（初日に上長と設定）",6); r+=1
    r=note(sm,r,2,6,"半年で独り立ち＋売上 累計300万円が目標。面談数・紹介数・承諾数の具体値は単価に応じ初日に上長と設定し、下の月次トラッキングと進捗管理タブで追う。",size=10,color=SUB); r+=1
    kp=[["1ヶ月目","Stage1クリア","面談同席・準備サポート","—"],
        ["2〜3ヶ月目","Stage2クリア","面談・紹介を自分で回す","初の内定承諾を出す"],
        ["4〜6ヶ月目","Stage3クリア＝独り立ち","面談〜クロージングを自走","売上 累計300万円"]]
    r=tbl(sm,r,2,["時期","研修ゴール","行動目標","成果目標"],kp,W[:4],zebra=True,red_cols=[0]); r+=1
    section(sm,r,2,"月次トラッキング（本人記入）",6); r+=1
    months=[["%dヶ月目"%i,"","","","",""] for i in range(1,7)]
    tbl(sm,r,2,["月","面談数","紹介数","内定承諾数","売上(円)","メモ"],months,W,zebra=True,red_cols=[0])
    sm.freeze=(0,0)

def build_books(sm,G):
    px=[260,160,360,120]
    for c,p in enumerate(px): sm.col_px[2+c]=p
    sm.put(1,6,hlink(G["研修ホーム"],"← 研修ホーム"), font=SUB, size=9, halign="RIGHT"); sm.row_px[1]=16
    section(sm,2,2,"おすすめ課題図書（ビジネススキル）",4)
    note(sm,3,2,4,"思考力・問題解決・伝え方を伸ばす定番。新卒・中途を問わず、研修と並行して読了→要約を1枚で共有を推奨。",size=10,color=SUB)
    tbl(sm,5,2,["書名","著者","なぜ読む（一言）","テーマ"],TR["BOOKS"],px,zebra=True,red_cols=[0])
    sm.freeze=(5,0); sm.filter=(5,2,5+len(TR["BOOKS"]),5)

# ---- 業界×職種（既存）をライト設計で再描画 ----
def backlink(sm,col,G): sm.put(1,col,hlink(G["研修ホーム"],"← 研修ホーム"), font=SUB, size=9, halign="RIGHT"); sm.row_px[1]=16
def grp(items,idx=1):
    o,m=[],{}
    for r in items:
        d=r[idx]
        if d not in m: m[d]=[]; o.append(d)
        m[d].append(r)
    return [(d,m[d]) for d in o]

def build_imap(sm,G):
    px=[170,360,80,320]
    for c,p in enumerate(px): sm.col_px[2+c]=p
    backlink(sm,5,G)
    section(sm,2,2,"業界マップ（大分類→中分類の俯瞰）",4)
    r=note(sm,3,2,4,"人気の高い大分類を上から。詳細は「業界詳細」へ。",size=10,color=SUB); r+=1
    for dai,rows in grp(D["INDUSTRIES"]):
        section(sm,r,2,"%s（%d業界）"%(dai,len(rows)),4); r+=1
        data=[[x[0],x[2],x[8],x[4]] for x in rows]
        r=tbl(sm,r,2,["業界","一言でいうと","人気度","代表企業"],data,px,zebra=True,pop_col=2)
    sm.freeze=(0,0)

def build_idet(sm,G):
    px=[140,90,290,290,200,190,200,280,210,250,72,320]
    for c,p in enumerate(px): sm.col_px[2+c]=p
    backlink(sm,13,G)
    section(sm,2,2,"業界詳細（面談インプット用マスタ）",12)
    note(sm,3,2,12,"フィルタで大分類・人気度・成長性などを絞り込めます。市場規模は概数（配布前に最新値を要確認）。",size=10,color=SUB)
    header=["業界(中分類)","大分類","一言でいうと","ビジネスモデル・収益源","代表企業","主要職種","働き方の特徴","将来性・トレンド","市場規模","成長性","人気度","面談ポイント・よくある誤解"]
    rows=[]
    for i,r in enumerate(D["INDUSTRIES"]):
        m=MKT[i] if i<len(MKT) else {"市場規模":"","成長性":"","成長ランク":""}
        seika="［%s］ %s"%(m.get("成長ランク",""),m.get("成長性","")) if m.get("成長ランク") else m.get("成長性","")
        rows.append(list(r[:8])+[m.get("市場規模",""),seika]+list(r[8:]))
    n=len(rows); tbl(sm,5,2,header,rows,px,zebra=True,pop_col=10)
    sm.freeze=(5,0); sm.filter=(5,2,5+n,13)

def build_jmap(sm,G):
    px=[210,120,400]
    for c,p in enumerate(px): sm.col_px[2+c]=p
    backlink(sm,4,G)
    section(sm,2,2,"職種マップ（大分類→中分類）",3)
    r=note(sm,3,2,3,"営業は6軸で別物として捉える。詳細は「職種詳細」へ。",size=10,color=SUB); r+=1
    section(sm,r,2,"営業を読み解く6軸",3); r+=1
    r=tbl(sm,r,2,["軸","対比","ひとことで"],D["SALES_AXES"],px,zebra=True)
    for dai,rows in grp(D["JOBS"]):
        section(sm,r,2,"%s（%d職種）"%(dai,len(rows)),3); r+=1
        data=[[x[0],x[2],x[3]] for x in rows]
        r=tbl(sm,r,2,["職種","分類軸","仕事内容(要約)"],data,px,zebra=True)
    sm.freeze=(0,0)

def build_jdet(sm,G):
    px=[160,105,82,265,180,165,150,180,180,120,150,185,170,285]
    for c,p in enumerate(px): sm.col_px[2+c]=p
    backlink(sm,15,G)
    section(sm,2,2,"職種詳細（面談インプット用マスタ）",14)
    note(sm,3,2,14,"向いている人／向かない人に加え、未経験(新卒)就職の難易度・AI代替リスク・年収の上がり方まで。学生のキャリア相談の材料に（難易度/年収は概観・配布前に最新を要確認）。フィルタ可。",size=10,color=SUB)
    header=["職種","大分類","分類軸","仕事内容","求められる力","向いている人","向かない人","代表業界・配属","キャリアパス","採用の多さ・人気","未経験難易度","AI代替リスク","年収の上がり方","学生の誤解・面談で伝えること"]
    rows=[]
    for i,r in enumerate(D["JOBS"]):
        o=JOBOUT[i] if i<len(JOBOUT) else {}
        rows.append(list(r[:10])+[o.get("未経験難易度",""),o.get("AI代替リスク",""),o.get("年収の上がり方","")]+list(r[10:]))
    n=len(rows); tbl(sm,5,2,header,rows,px,zebra=True)
    sm.freeze=(5,0); sm.filter=(5,2,5+n,15)

def build_rank(sm,G):
    px=[46,210,180,46,210,180]
    for c,p in enumerate(px): sm.col_px[2+c]=p
    backlink(sm,7,G)
    section(sm,2,2,"人気ランキング・トレンド（2027/2026卒）",6)
    r=4
    section(sm,r,2,"最初に押さえる要点",6); r+=1
    r=mtbl(sm,r,2,["観点","内容"],[2,4],D["RANK_NOTES"],red_cols=[0])
    section(sm,r,2,"人気企業ランキング（出典・集計方法で順位は変わる）",6); r+=1
    def rk(row,col,title,data):
        sm.put(row,col,title, font=INK, bold=True, size=10, valign="MIDDLE", hrule=True)
        sm.fill(row,col,row,col+2,hrule=True)
        tbl(sm,row+1,col,["#","企業","業界"],data,[46,210,180],zebra=True,red_cols=[0])
        return row+1+len(data)
    a=rk(r,2,"マイナビ・日経 27卒 文系TOP10",D["RANK_MYNAVI_BUNKEI"]); b=rk(r,5,"マイナビ・日経 27卒 理系TOP10",D["RANK_MYNAVI_RIKEI"]); r=max(a,b)+2
    c=rk(r,2,"ワンキャリア 27卒 文系TOP10",D["RANK_ONECAREER_B"]); d=rk(r,5,"ワンキャリア 27卒 理系TOP10",D["RANK_ONECAREER_R"]); r=max(c,d)+2
    e=rk(r,2,"文化放送 27卒 総合TOP15",D["RANK_BUNKA"]); f=rk(r,5,"学情 27卒 総合TOP5",D["RANK_GAKUJO"]); r=max(e,f)+2
    section(sm,r,2,"業界人気のトレンド",6); r+=1
    r=mtbl(sm,r,2,["業界","動向","確度"],[2,3,1],D["TREND"],red_cols=[0])
    section(sm,r,2,"出典",6); r+=1
    r=mtbl(sm,r,2,["調査","URL"],[2,4],D["RANK_SOURCES"],link_col=1)
    note(sm,r,2,6,"注：数値は各調査の集計方法で異なる。一部順位は最新未確認のため配布時は各URLで補完。",size=9,color=SUB)
    sm.freeze=(2,0)

def build_tips(sm,G):
    px=[220,680]
    for c,p in enumerate(px): sm.col_px[2+c]=p
    backlink(sm,3,G)
    section(sm,2,2,"面談で押さえる横断ポイント",2)
    r=tbl(sm,4,2,["観点","内容"],D["TIPS"],px,zebra=True,red_cols=[0])
    section(sm,r,2,"用語集（学生に説明できるように）",2); r+=1
    tbl(sm,r,2,["用語","意味"],D["GLOSSARY"],px,zebra=True,red_cols=[0])
    sm.freeze=(0,0)

def build_deep(sm,G):
    px=[340,560]
    for c,p in enumerate(px): sm.col_px[2+c]=p
    backlink(sm,3,G)
    section(sm,2,2,"業界深掘りテンプレート（このシートを複製して使用）",2)
    r=note(sm,3,2,2,"このタブを複製→タブ名を「総合商社」等に変更し各章を埋める。まずは人気上位から。",size=10,color=INK); r+=1
    sm.put(r,2,"対象業界：＿＿＿＿＿＿＿＿", font=RED, bold=True, size=12); sm.row_px[r]=26; r+=2
    rows=[[s,""] for s in D["DEEP_SECTIONS"]]; start=r
    r=tbl(sm,r,2,["章立て","記入欄"],rows,px,zebra=False,red_cols=[0])
    for i in range(len(rows)): sm.row_px[start+1+i]=52
    sm.freeze=(0,0)


# ===== Sheets API リクエスト生成 =====
def cell(entry):
    if entry is None: return {}
    val,f=entry; cd={}
    if val not in ("",None):
        if isinstance(val,bool): cd["userEnteredValue"]={"boolValue":val}
        elif isinstance(val,(int,float)): cd["userEnteredValue"]={"numberValue":val}
        elif isinstance(val,str) and val.startswith("=") and not f.get("astext"): cd["userEnteredValue"]={"formulaValue":val}
        else: cd["userEnteredValue"]={"stringValue":str(val)}
    uf={}
    if f.get("bg"): uf["backgroundColor"]=rgb(f["bg"])
    tf={}
    if f.get("font"): tf["foregroundColor"]=rgb(f["font"])
    if f.get("bold"): tf["bold"]=True
    if f.get("size"): tf["fontSize"]=f["size"]
    if tf: uf["textFormat"]=tf
    if f.get("halign"): uf["horizontalAlignment"]=f["halign"]
    if f.get("valign"): uf["verticalAlignment"]=f["valign"]
    if f.get("wrap"): uf["wrapStrategy"]="WRAP"
    if f.get("numfmt"): uf["numberFormat"]=f["numfmt"]
    b={}
    if f.get("sep"): b["bottom"]={"style":"SOLID","color":rgb(RULE)}
    if f.get("hrule"): b["bottom"]={"style":"SOLID_MEDIUM","color":rgb(HRULE)}
    if f.get("underline"): b["bottom"]={"style":"SOLID_MEDIUM","color":rgb(RED)}
    if b: uf["borders"]=b
    if uf: cd["userEnteredFormat"]=uf
    return cd

def reqs_for(sm):
    R=[]
    rmax=max((r for (r,c) in sm.grid),default=1); cmax=max((c for (r,c) in sm.grid),default=1)
    # クリーンアップ先行：旧結合解除＋値/書式/入力規則を広域リセット（再描画前）
    R.append({"unmergeCells":{"range":{"sheetId":sm.id,"startRowIndex":0,"endRowIndex":max(rmax,300),"startColumnIndex":0,"endColumnIndex":max(cmax,26)}}})
    R.append({"repeatCell":{"range":{"sheetId":sm.id,"startRowIndex":0,"endRowIndex":max(rmax,200),"startColumnIndex":0,"endColumnIndex":max(cmax,26)},"cell":{},"fields":"userEnteredValue,userEnteredFormat,dataValidation"}})
    rows=[{"values":[cell(sm.grid.get((r,c))) for c in range(1,cmax+1)]} for r in range(1,rmax+1)]
    R.append({"updateCells":{"rows":rows,"fields":"userEnteredValue,userEnteredFormat","start":{"sheetId":sm.id,"rowIndex":0,"columnIndex":0}}})
    for (r1,c1,r2,c2) in sm.merges:
        R.append({"mergeCells":{"mergeType":"MERGE_ALL","range":{"sheetId":sm.id,"startRowIndex":r1-1,"endRowIndex":r2,"startColumnIndex":c1-1,"endColumnIndex":c2}}})
    for c,px in sm.col_px.items():
        R.append({"updateDimensionProperties":{"range":{"sheetId":sm.id,"dimension":"COLUMNS","startIndex":c-1,"endIndex":c},"properties":{"pixelSize":px},"fields":"pixelSize"}})
    for r,px in sm.row_px.items():
        R.append({"updateDimensionProperties":{"range":{"sheetId":sm.id,"dimension":"ROWS","startIndex":r-1,"endIndex":r},"properties":{"pixelSize":px},"fields":"pixelSize"}})
    fr,fc=sm.freeze
    R.append({"updateSheetProperties":{"properties":{"sheetId":sm.id,"gridProperties":{"hideGridlines":True,"frozenRowCount":fr,"frozenColumnCount":fc}},"fields":"gridProperties.hideGridlines,gridProperties.frozenRowCount,gridProperties.frozenColumnCount"}})
    for (r1,c1,r2,c2,opts) in sm.validations:
        R.append({"setDataValidation":{"range":{"sheetId":sm.id,"startRowIndex":r1-1,"endRowIndex":r2,"startColumnIndex":c1-1,"endColumnIndex":c2},
            "rule":{"condition":{"type":"ONE_OF_LIST","values":[{"userEnteredValue":o} for o in opts]},"showCustomUi":True,"strict":False}}})
    for (r1,c1,r2,c2,txt,bg,fg) in sm.cfmts:
        R.append({"addConditionalFormatRule":{"index":0,"rule":{"ranges":[{"sheetId":sm.id,"startRowIndex":r1-1,"endRowIndex":r2,"startColumnIndex":c1-1,"endColumnIndex":c2}],
            "booleanRule":{"condition":{"type":"TEXT_EQ","values":[{"userEnteredValue":txt}]},"format":{"backgroundColor":rgb(bg),"textFormat":{"foregroundColor":rgb(fg),"bold":True}}}}}})
    # カスタム式の条件付き書式（ガント等）。fg=None なら背景色のみ。index順に追加=先頭優先
    for k,(r1,c1,r2,c2,formula,bg,fg) in enumerate(sm.cfmt_formulas):
        fmtd={"backgroundColor":rgb(bg)}
        if fg: fmtd["textFormat"]={"foregroundColor":rgb(fg),"bold":True}
        R.append({"addConditionalFormatRule":{"index":k,"rule":{"ranges":[{"sheetId":sm.id,"startRowIndex":r1-1,"endRowIndex":r2,"startColumnIndex":c1-1,"endColumnIndex":c2}],
            "booleanRule":{"condition":{"type":"CUSTOM_FORMULA","values":[{"userEnteredValue":formula}]},"format":fmtd}}}})
    if sm.filter:
        r1,c1,r2,c2=sm.filter
        R.append({"setBasicFilter":{"filter":{"range":{"sheetId":sm.id,"startRowIndex":r1-1,"endRowIndex":r2,"startColumnIndex":c1-1,"endColumnIndex":c2}}}})
    return R


DESIRED=["研修ホーム","カリキュラム一覧","目標・KPI","週間プログラム","進捗管理","WBS","YouTube教材","ショートカット","関数ワーク","関数練習","AI活用ガイド","課題図書",
         "業界マップ","業界詳細","業界内定攻略","職種マップ","職種詳細","人気ランキング","面談メモ","深掘りテンプレ"]
RENAME={"00_使い方":"研修ホーム","01_業界マップ":"業界マップ","02_業界詳細":"業界詳細","03_職種マップ":"職種マップ",
        "04_職種詳細":"職種詳細","05_人気ランキング":"人気ランキング","06_面談活用メモ":"面談メモ","07_深掘りテンプレ":"深掘りテンプレ"}
BUILDERS={"研修ホーム":build_home,"カリキュラム一覧":build_curriculum,"週間プログラム":build_weekly,"進捗管理":build_progress,"WBS":build_wbs,
          "目標・KPI":build_kpi,"YouTube教材":build_youtube,"ショートカット":build_shortcuts,"関数ワーク":build_functions,
          "関数練習":build_renshu,"AI活用ガイド":build_ai,"業界内定攻略":build_idattack,"課題図書":build_books,
          "業界マップ":build_imap,"業界詳細":build_idet,"職種マップ":build_jmap,"職種詳細":build_jdet,
          "人気ランキング":build_rank,"面談メモ":build_tips,"深掘りテンプレ":build_deep}


def ensure_sheets(svc):
    def cur():
        m=svc.spreadsheets().get(spreadsheetId=SSID,fields="sheets(properties(sheetId,title,index))").execute()
        return {s["properties"]["title"]:s["properties"]["sheetId"] for s in m["sheets"]}
    c=cur()
    # 1) 旧名→新名にリネーム
    rn=[{"updateSheetProperties":{"properties":{"sheetId":c[o],"title":n},"fields":"title"}} for o,n in RENAME.items() if o in c and n not in c]
    if rn: svc.spreadsheets().batchUpdate(spreadsheetId=SSID,body={"requests":rn}).execute()
    c=cur()
    # 2) 不足タブを追加
    add=[{"addSheet":{"properties":{"title":t}}} for t in DESIRED if t not in c]
    if add: svc.spreadsheets().batchUpdate(spreadsheetId=SSID,body={"requests":add}).execute()
    c=cur()
    # 3) 並べ替え
    order=[{"updateSheetProperties":{"properties":{"sheetId":c[t],"index":i},"fields":"index"}} for i,t in enumerate(DESIRED)]
    svc.spreadsheets().batchUpdate(spreadsheetId=SSID,body={"requests":order}).execute()
    return cur()


def main():
    creds=Credentials.from_authorized_user_file(TOK)
    if not creds.valid: creds.refresh(Request())
    svc=build("sheets","v4",credentials=creds)
    G=ensure_sheets(svc)
    print("tabs ready:",len(G))
    for t in DESIRED:
        sm=SM(G[t]); BUILDERS[t](sm,G)
        svc.spreadsheets().batchUpdate(spreadsheetId=SSID,body={"requests":reqs_for(sm)}).execute()
        print("built:",t)
    print("DONE  https://docs.google.com/spreadsheets/d/%s/edit"%SSID)

if __name__=="__main__":
    main()
