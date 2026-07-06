#!/usr/bin/env python3
"""管理SSのテスト集計をPython側で実行（GASを貼らずに私のトークンで集計）。

全Googleフォームの回答（respondentEmail / totalScore / 設問別 grade.correct）を読み取り、
管理SS（.admin_sheet_id）の以下タブを更新する:
  - 結果ログ        : 1回答=1行（誰が・いつ・どのテストを・何点・合否）
  - 進捗・成績      : 受講者ごとの進捗率/受験数/合格数/平均点/最終提出/未合格/遅延
  - モジュール別集計: テストごとの受験者数/合格者数/合格率/平均点
  - 設問別分析      : 設問ごとの正答率/回答数（弱点の特定）

前提: 全フォームでメール収集(VERIFIED)が有効（enable_form_email_collection 済）。
スコープ: token_sheets.json に forms.responses.readonly / spreadsheets。
"""
import datetime
import importlib.util
import json
import os
import re
import warnings

warnings.filterwarnings("ignore")
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

BASE = "/Users/atsuyasato/Claude AI"
TOK = os.path.join(BASE, "tokumori/agents/hr_support/config/token_sheets.json")
PASS = 0.9          # 合格ライン（満点比）
HORIZON = 90        # 想定完了日数（遅延判定）
LAG = 0.15          # 想定進捗からの遅れ許容（これ以上遅れたら遅延）

CAT = {"A": "自社・マインド", "B": "ビジネス基礎", "C": "PC・ツール",
       "D": "思考・分析", "E": "自己・対人", "F": "CA職種特化", "G": "リスク・コンプラ"}
EXTRA = {"F2": "業界・職種理解", "C3": "スプレッドシート関数"}


def creds():
    c = Credentials.from_authorized_user_file(TOK)
    if not c.valid:
        c.refresh(Request())
    return c


def pdate(s):
    s = str(s).strip()
    for f in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y"):
        try:
            return datetime.datetime.strptime(s, f).date()
        except ValueError:
            continue
    return None


def aggregate_wbs(sv, dr, roster_rows):
    """各メンバーのコピーSSのWBSタブを読み、本人ごとの 全体% / Stage別% / 完了数 / 着手中 を集計。"""
    out = []
    for r in roster_rows:
        nm = r[1] if len(r) > 1 else ""
        ml = (r[2] if len(r) > 2 else "").strip()
        url = r[5] if len(r) > 5 else ""
        mm = re.search(r"/spreadsheets/d/([A-Za-z0-9_-]+)", url or "")
        if not mm:
            continue
        sid = mm.group(1)
        try:
            vals = sv.spreadsheets().values().get(
                spreadsheetId=sid, range="WBS!B13:H").execute().get("values", [])
        except Exception:
            continue
        tot = ndone = nwip = 0
        prog_sum = 0.0
        stg = {"Stage1": [0.0, 0], "Stage2": [0.0, 0], "Stage3": [0.0, 0]}
        for row in vals:
            row = (list(row) + [""] * 7)[:7]  # B..H: ステージ,ID,モジュール,開始,終了,ステータス,承認
            stage, mid, status = row[0], row[1], row[5]
            if not mid:
                continue
            p = 1.0 if status == "完了" else (0.5 if status == "着手中" else 0.0)
            tot += 1
            prog_sum += p
            if status == "完了":
                ndone += 1
            elif status == "着手中":
                nwip += 1
            key = stage[:6]
            if key in stg:
                stg[key][0] += p
                stg[key][1] += 1
        if tot == 0:
            continue
        sp = lambda k: round(stg[k][0] / stg[k][1], 4) if stg[k][1] else 0
        try:
            mt = dr.files().get(fileId=sid, fields="modifiedTime").execute().get("modifiedTime", "")[:10]
        except Exception:
            mt = ""
        out.append([nm, ml, round(prog_sum / tot, 4),
                    sp("Stage1"), sp("Stage2"), sp("Stage3"), ndone, nwip, mt])
    return out


def main():
    c = creds()
    sv = build("sheets", "v4", credentials=c)
    forms = build("forms", "v1", credentials=c)
    dr = build("drive", "v3", credentials=c)
    fmap = json.load(open(os.path.join(BASE, ".forms_map.json"), encoding="utf-8"))
    admid = open(os.path.join(BASE, ".admin_sheet_id")).read().strip()
    today = datetime.date.today()

    spec = importlib.util.spec_from_file_location("bs", os.path.join(BASE, "build_slides.py"))
    bs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bs)
    deck_name = {mid: name for mid, (t, fn, name) in bs.DECKS.items()}

    def mod_name(mid):
        return deck_name.get(mid) or EXTRA.get(mid, mid)

    # 名簿: メール→氏名 / メール→開始日（順序保持）
    ros = sv.spreadsheets().values().get(
        spreadsheetId=admid, range="受講者名簿!A2:G").execute().get("values", [])
    roster_mails = []
    name_by_mail, start_by_mail = {}, {}
    for r in ros:
        if len(r) >= 3 and r[2]:
            mail = r[2].strip().lower()
            roster_mails.append(mail)
            name_by_mail[mail] = r[1] if len(r) > 1 else ""
            start_by_mail[mail] = r[4] if len(r) > 4 else ""

    total_mod = len(fmap)
    logs = []
    per_mail = {}     # mail -> dict
    per_mod = {}      # mid -> dict
    qstats = {}       # (mid, title) -> [correct, total]
    n_resp = 0

    for mid, fid in fmap.items():
        try:
            form = forms.forms().get(formId=fid).execute()
        except Exception as e:
            print("  form get FAIL", mid, str(e)[:80])
            continue
        order, maxpts = [], 0
        for it in form.get("items", []):
            q = it.get("questionItem", {}).get("question")
            if not q:
                continue
            order.append((q.get("questionId"), it.get("title", "")))
            maxpts += q.get("grading", {}).get("pointValue", 0)
        if not maxpts:
            maxpts = 100
        nm = mod_name(mid)
        per_mod.setdefault(mid, {"taken": 0, "passed": 0, "scores": []})
        for qid, t in order:
            qstats.setdefault((mid, t), [0, 0])

        resp, tok = [], None
        while True:
            r = forms.forms().responses().list(formId=fid, pageToken=tok).execute()
            resp += r.get("responses", [])
            tok = r.get("nextPageToken")
            if not tok:
                break
        for rp in resp:
            n_resp += 1
            mail = (rp.get("respondentEmail") or "").strip().lower()
            ts = rp.get("totalScore", 0)
            sub = rp.get("lastSubmittedTime", "")[:19].replace("T", " ")
            pct = round(100 * ts / maxpts) if maxpts else 0
            passed = (ts / maxpts) >= PASS if maxpts else False
            logs.append([sub, mail, name_by_mail.get(mail, ""), mid, nm, ts, maxpts,
                         "合格" if passed else "不合格"])
            d = per_mail.setdefault(mail, {"passed": set(), "taken": set(), "scores": [], "last": ""})
            d["taken"].add(mid)
            if passed:
                d["passed"].add(mid)
            d["scores"].append(pct)
            if sub > d["last"]:
                d["last"] = sub
            m = per_mod[mid]
            m["taken"] += 1
            m["scores"].append(pct)
            if passed:
                m["passed"] += 1
            ans = rp.get("answers", {})
            for qid, t in order:
                a = ans.get(qid)
                if not a:
                    continue
                st = qstats[(mid, t)]
                st[1] += 1
                if a.get("grade", {}).get("correct"):
                    st[0] += 1

    # ---- 進捗・成績 ----
    prog_rows = []
    seen = set()
    for mail in roster_mails + [m for m in per_mail if m not in roster_mails]:
        if mail in seen:
            continue
        seen.add(mail)
        d = per_mail.get(mail, {"passed": set(), "taken": set(), "scores": [], "last": ""})
        npass, ntaken = len(d["passed"]), len(d["taken"])
        rate = round(npass / total_mod, 4) if total_mod else 0
        avg = round(sum(d["scores"]) / len(d["scores"]), 1) if d["scores"] else 0
        weak = "、".join(sorted(d["taken"] - d["passed"]))
        delay = "OK"
        sd = pdate(start_by_mail.get(mail, ""))
        if sd:
            elapsed = (today - sd).days
            expected = min(1.0, max(0, elapsed) / HORIZON)
            if rate < expected - LAG:
                delay = "⚠ 遅延"
        prog_rows.append([name_by_mail.get(mail, ""), mail, rate, ntaken, npass, avg,
                          d["last"], weak, delay])

    # ---- モジュール別集計 ----
    mod_rows = []
    for mid in fmap:
        m = per_mod.get(mid, {"taken": 0, "passed": 0, "scores": []})
        rate = round(m["passed"] / m["taken"], 4) if m["taken"] else 0
        avg = round(sum(m["scores"]) / len(m["scores"]), 1) if m["scores"] else 0
        mod_rows.append([mid, mod_name(mid), CAT.get(mid[0], ""),
                         m["taken"], m["passed"], rate, avg])

    # ---- 設問別分析（回答のあった設問のみ）----
    q_rows = []
    for (mid, t), (cor, tot) in qstats.items():
        if tot == 0:
            continue
        q_rows.append([mid, mod_name(mid), t, round(cor / tot, 4), tot])
    q_rows.sort(key=lambda r: (r[0], r[3]))  # モジュール→正答率昇順（弱点が上）

    logs.sort(key=lambda r: r[0], reverse=True)

    # ---- 書き込み（クリア→更新）----
    def clear(rng):
        sv.spreadsheets().values().clear(spreadsheetId=admid, range=rng).execute()

    def write(rng, rows):
        if rows:
            sv.spreadsheets().values().update(
                spreadsheetId=admid, range=rng, valueInputOption="USER_ENTERED",
                body={"values": rows}).execute()

    wbs_rows = aggregate_wbs(sv, dr, ros)

    for rng in ["結果ログ!A2:H1000", "進捗・成績!A2:I200",
                "モジュール別集計!A2:G100", "設問別分析!A2:E1000", "WBS進捗!A2:I200"]:
        clear(rng)
    write("結果ログ!A2", logs)
    write("進捗・成績!A2", prog_rows)
    write("モジュール別集計!A2", mod_rows)
    write("設問別分析!A2", q_rows)
    write("WBS進捗!A2", wbs_rows)

    print("COLLECT DONE")
    print("  回答総数      :", n_resp)
    print("  結果ログ行     :", len(logs))
    print("  受講者(進捗)   :", len(prog_rows))
    print("  モジュール集計 :", len(mod_rows))
    print("  設問別(回答有) :", len(q_rows))
    print("  WBS進捗(人)    :", len(wbs_rows))
    print("  管理SS        : https://docs.google.com/spreadsheets/d/%s/edit" % admid)
    if n_resp == 0:
        print("  ※ まだ回答ゼロ。受講者がテストを提出後に再実行すると各タブが自動で埋まります。")


if __name__ == "__main__":
    main()
