#!/usr/bin/env python3
"""本編スライドの理想形さがし＝実コンテンツ（中途RPO）で12案（H01-H12）。
構成・密度・見出し文体を意図的に変える。極限シンプル基調（白・罫線最小・palt・Lato数字・赤1色）。
ユーザーが良/悪を選別 → 選ばれた型を本編の正式フォーマットに固定する。"""
import os
import warnings

warnings.filterwarnings("ignore")
import html_to_slide as H

INK = "#15171C"; PAPER = "#FFFFFF"; RED = "#AF322C"; GRAY = "#8A8F98"
NEU = "#DCD9D4"; NEU2 = "#EDEBE7"; HL = "rgba(21,23,28,0.12)"
FONT = ('<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700;900'
        '&family=Lato:wght@400;700;900&display=swap" rel="stylesheet"/>')
BASE = ('*{margin:0;padding:0;box-sizing:border-box;}html,body{width:1280px;height:720px;overflow:hidden;}'
        'body{font-family:"Noto Sans JP",sans-serif;background:%s;color:%s;-webkit-font-smoothing:antialiased;}'
        '.jp{font-feature-settings:"palt";}.en{font-family:Lato,sans-serif;letter-spacing:.14em;text-transform:uppercase;}'
        '.num{font-family:Lato,sans-serif;}' % (PAPER, INK))

SLIDES = []


def page(body):
    return ('<!DOCTYPE html><html><head><meta charset="utf-8"/>' + FONT +
            f'<style>{BASE}</style></head><body>'
            f'<div style="position:relative;width:1280px;height:720px;">{body}</div></body></html>')


def add(name, body):
    n = len(SLIDES) + 1
    tagged = body + (f'<div class="en" style="position:absolute;right:16px;bottom:12px;font-size:10px;'
                     f'color:{RED};font-weight:700;background:rgba(175,50,44,.07);padding:4px 10px;">H{n:02d}</div>')
    SLIDES.append((n, name, page(tagged)))


def foot(src="", pg="07"):
    s = f'<div class="jp" style="position:absolute;left:84px;bottom:44px;font-size:11px;color:{GRAY};">{src}</div>' if src else ""
    return s + f'<div class="num" style="position:absolute;right:84px;bottom:44px;font-size:12px;color:{GRAY};">{pg}</div>'


def kick(t):
    return f'<div class="jp" style="font-size:13px;color:{RED};font-weight:700;">{t}</div>'


# H01 数字主役（左に巨大数字・右に説明列）
add("数字主役・左右分割", f'''
<div style="padding:60px 84px;">{kick("採用市場")}
  <div style="display:flex;align-items:center;margin-top:40px;gap:80px;">
    <div style="flex:none;">
      <div class="num jp" style="font-size:210px;font-weight:900;line-height:1;letter-spacing:-.02em;">26<span style="font-size:80px;">倍</span></div>
      <div class="jp" style="font-size:16px;font-weight:700;margin-top:16px;">中小企業の採用難易度（大企業比）</div>
    </div>
    <div class="jp" style="font-size:15px;line-height:2.2;color:#3A3F47;border-left:1px solid {HL};padding-left:56px;">
      大卒有効求人倍率は、300人以下の企業で <b class="num">8.98倍</b>。<br>
      5,000人以上では <b class="num">0.34倍</b>。<br><br>
      同じ「採用活動」でも、<br>中小はそもそも26倍不利な土俵で戦っている。
    </div>
  </div>
</div>{foot("出典: リクルートワークス研究所 第42回(26卒)")}''')

# H02 図主役（棒グラフが主役・見出し小さめ）
add("図主役・チャート大", f'''
<div style="padding:60px 84px;">{kick("採用市場")}
  <div class="jp" style="font-size:28px;font-weight:900;margin-top:12px;">求人倍率は、企業規模で26倍ちがう</div>
  <div style="margin-top:64px;">''' +
    "".join(f'<div style="display:flex;align-items:center;margin-bottom:34px;">'
            f'<div class="jp" style="width:190px;font-size:16px;font-weight:700;color:{RED if hi else INK};">{l}</div>'
            f'<div style="flex:1;position:relative;height:44px;background:rgba(21,23,28,.04);">'
            f'<div style="position:absolute;left:0;top:0;height:44px;width:{p}%;background:{RED if hi else NEU};"></div>'
            f'<div class="num" style="position:absolute;left:calc({p}% + 16px);top:8px;font-size:20px;font-weight:900;color:{RED if hi else INK};">{v}</div></div></div>'
            for l, p, v, hi in [("300人以下", 90, "8.98倍", 1), ("1,000人以上", 13, "1.20倍", 0), ("5,000人以上", 4, "0.34倍", 0)]) +
    f'''</div>
</div>{foot("出典: リクルートワークス研究所 第42回(26卒)")}''')

# H03 主張見出し＋左テキスト右図（非対称）
add("主張見出し＋左文右図", f'''
<div style="padding:60px 84px;">{kick("採用の限界")}
  <div class="jp" style="font-size:28px;font-weight:900;margin-top:12px;">頑張りでは埋まらない。選考の「構造」が先。</div>
  <div style="display:flex;gap:70px;margin-top:52px;">
    <div class="jp" style="width:380px;font-size:14.5px;line-height:2.1;color:#3A3F47;">
      面接の妥当性は、手法でほぼ決まる。<br><br>
      学歴で見抜ける定着・活躍は <b class="num" style="color:{RED};">0.10</b>。<br>
      よくある自由面接でも <b class="num">0.19</b>。<br><br>
      一方、質問を設計した<b>構造化面接は0.42</b>——学歴の約4倍当てになる。
    </div>
    <div style="flex:1;padding-top:8px;">''' +
    "".join(f'<div style="display:flex;align-items:center;margin-bottom:19px;">'
            f'<div class="jp" style="width:150px;font-size:13.5px;font-weight:700;color:{RED if hi else INK};">{l}</div>'
            f'<div style="flex:1;position:relative;height:26px;background:rgba(21,23,28,.04);">'
            f'<div style="position:absolute;left:0;top:0;height:26px;width:{p}%;background:{RED if hi else NEU};"></div>'
            f'<div class="num" style="position:absolute;left:calc({p}% + 10px);top:3px;font-size:14px;font-weight:700;">{v}</div></div></div>'
            for l, p, v, hi in [("実務テスト", 90, "0.54", 0), ("構造化面接", 70, "0.42", 1), ("自由面接", 32, "0.19", 0), ("学歴", 17, "0.10", 0)]) +
    f'''</div></div>
</div>{foot("出典: Sackett et al. 2022（妥当性係数）")}''')

# H04 高密度データ（KPIグリッド＋注記）
add("高密度・数値グリッド", f'''
<div style="padding:60px 84px;">{kick("提供価値")}
  <div class="jp" style="font-size:28px;font-weight:900;margin-top:12px;">構造を変えると、数字はここまで動く</div>
  <div style="display:grid;grid-template-columns:repeat(4,1fr);grid-gap:1px;background:{HL};margin-top:44px;border:1px solid {HL};">''' +
    "".join(f'<div style="background:#fff;padding:30px 26px;">'
            f'<div class="jp" style="font-size:13px;color:{GRAY};font-weight:700;">{l}</div>'
            f'<div class="num jp" style="font-size:46px;font-weight:900;margin-top:10px;color:{RED if hi else INK};">{v}</div>'
            f'<div class="jp" style="font-size:12px;color:{GRAY};margin-top:8px;">{n}</div></div>'
            for l, v, n, hi in [("母集団形成", "29倍", "最大・事例値", 1), ("内定承諾率", "+38%", "改善幅・方向値", 0),
                                ("人事の一次工数", "−89%", "AI・代行で削減", 0), ("採用期間", "−40%", "TTH短縮", 0)]) +
    f'''</div>
  <div class="jp" style="margin-top:22px;font-size:13px;color:{GRAY};line-height:1.8;">いずれも自社実績・モデルケースに基づく方向値であり、成果保証ではありません。<br>母集団は事例により +800〜2,600%（最大29倍）。承諾率改善は +20〜38%。</div>
</div>{foot("", "04")}''')

# H05 事例ストーリー（1社を深く）
add("事例ストーリー1社", f'''
<div style="padding:60px 84px;">{kick("導入事例 ・ 製造業（香川・120名）")}
  <div class="jp" style="font-size:28px;font-weight:900;margin-top:12px;">「応募が来ない」工場が、8ヶ月で変わった</div>
  <div style="display:flex;gap:60px;margin-top:48px;">
    <div style="width:430px;" class="jp">
      <div style="font-size:14.5px;line-height:2.1;color:#3A3F47;">
        地方×製造×交代勤務。3年間、紹介会社頼みで年2名がやっと。<br><br>
        当社はスカウト設計と求人票の全面改稿から着手。<b>現場社員の1日</b>を主役にした訴求へ切り替え、応募単価を可視化しながら週次で回した。</div>
      <div style="margin-top:24px;font-size:13px;color:{GRAY};">実施：スカウト運用／求人票改稿／構造化面接の導入／週次KPI</div>
    </div>
    <div style="flex:1;">''' +
    "".join(f'<div style="display:flex;align-items:baseline;justify-content:space-between;border-bottom:1px solid {HL};padding:20px 0;">'
            f'<div class="jp" style="font-size:14.5px;font-weight:700;">{l}</div>'
            f'<div><span class="num" style="font-size:15px;color:{GRAY};">{a}</span>'
            f'<span class="num" style="font-size:15px;color:{GRAY};margin:0 12px;">→</span>'
            f'<span class="num" style="font-size:26px;font-weight:900;color:{RED if hi else INK};">{b}</span></div></div>'
            for l, a, b, hi in [("年間母集団", "36名", "107名", 1), ("面接設定率", "48%", "72%", 0), ("内定承諾率", "22%", "34%", 0), ("採用人数", "2名", "10名", 1)]) +
    f'''</div></div>
</div>{foot("社内実績・n=1の事例値。成果を保証するものではありません。", "16")}''')

# H06 ステートメント（主張1文だけ）
add("ステートメント1文", f'''
<div style="padding:60px 84px;">{kick("メソッド")}
  <div style="position:absolute;left:84px;top:280px;width:1100px;">
    <div class="jp" style="font-size:46px;font-weight:900;line-height:1.75;">採用がうまい会社は、頑張っていない。<br><span style="color:{RED};">仕組みが</span>頑張っている。</div>
  </div>
  <div class="jp" style="position:absolute;left:84px;bottom:100px;font-size:15px;color:{GRAY};">とくもり採用代行は、この「仕組み」ごと納品します。</div>
</div>{foot("", "11")}''')

# H07 対比（従来 vs とくもり・実質NOT/BUT）
add("対比2面", f'''
<div style="padding:60px 84px;">{kick("メソッド")}
  <div class="jp" style="font-size:28px;font-weight:900;margin-top:12px;">「人手を借りる」のではなく、「構造を買う」</div>
  <div style="display:flex;gap:1px;background:{HL};margin-top:44px;">
    <div style="flex:1;background:#fff;padding:40px 44px;">
      <div class="jp" style="font-size:14px;font-weight:900;color:{GRAY};">よくあるRPO</div>''' +
    "".join(f'<div class="jp" style="font-size:14.5px;color:{GRAY};padding:14px 0;border-bottom:1px solid {HL};">{t}</div>'
            for t in ["言われた業務を代行する", "担当者のスキルに依存", "契約が切れたら元に戻る"]) +
    f'''</div>
    <div style="flex:1;background:{INK};padding:40px 44px;">
      <div class="jp" style="font-size:14px;font-weight:900;color:#E5B4B0;">とくもり採用代行</div>''' +
    "".join(f'<div class="jp" style="font-size:14.5px;color:#fff;font-weight:700;padding:14px 0;border-bottom:1px solid rgba(255,255,255,.14);">{t}</div>'
            for t in ["ボトルネックを特定して設計する", "学術×データの再現手法", "FMTを納品し、社内で回る状態で卒業"]) +
    f'''</div></div>
</div>{foot("", "12")}''')

# H08 プロセス横断（番号ステップ・実物文脈）
add("導入プロセス5段", f'''
<div style="padding:60px 84px;">{kick("導入の流れ")}
  <div class="jp" style="font-size:28px;font-weight:900;margin-top:12px;">ご契約から2週間で、採用が動き出す</div>
  <div style="display:flex;justify-content:space-between;margin-top:70px;">''' +
    "".join((f'<div style="width:190px;">'
             f'<div class="num" style="font-size:14px;font-weight:900;color:{RED if hi else GRAY};">{d}</div>'
             f'<div style="height:3px;background:{RED if hi else NEU2};margin:14px 0 18px;"></div>'
             f'<div class="jp" style="font-size:16.5px;font-weight:900;">{t}</div>'
             f'<div class="jp" style="font-size:13px;color:{GRAY};margin-top:8px;line-height:1.8;">{de}</div></div>')
            for d, t, de, hi in [("当日", "ヒアリング", "現状KPIと課題の把握", 0), ("次回", "要件整理", "詳細提案・ROI試算", 0),
                                 ("最短1週", "ご契約", "条件合意・キックオフ設定", 0), ("2週間", "Kick Off", "チーム組成・アカウント整備", 0),
                                 ("3週目〜", "採用活動開始", "スカウト配信・選考が稼働", 1)]) +
    f'''</div>
  <div class="jp" style="margin-top:60px;font-size:14px;color:#3A3F47;">最低契約は6ヶ月。<b>「回る構造」の納品までが契約範囲</b>です。</div>
</div>{foot("", "20")}''')

# H09 テキストのみ理想形（長さの違う3ポイント・ドット無し）
add("テキストのみ3点", f'''
<div style="padding:60px 84px;">{kick("本日お伝えしたいこと")}
  <div style="margin-top:56px;width:1000px;">''' +
    "".join(f'<div style="display:flex;gap:40px;padding:30px 0;border-top:1px solid {HL};">'
            f'<div class="num" style="font-size:17px;font-weight:900;color:{RED};width:44px;padding-top:6px;">{i:02d}</div>'
            f'<div class="jp"><div style="font-size:21px;font-weight:900;">{t}</div>'
            f'<div style="font-size:14px;color:{GRAY};margin-top:10px;line-height:1.9;">{d}</div></div></div>'
            for i, t, d in [(1, "市場はもう元に戻らない", "中小の採用難易度は大企業の26倍。「待ち」の採用は構造的に不利になった。"),
                            (2, "打ち手は、すでに科学されている", ""),
                            (3, "任せて、型を残す", "実働を代行しながらFMTを納品。6ヶ月後、社内で回る状態でお返しする——ここが他社との違い。")]) +
    f'''</div>
</div>{foot("", "02")}''')

# H10 表（プラン・クリーン表）
BADGE = ('　<span style="font-size:11px;color:#fff;background:' + RED +
         ';padding:3px 10px;font-weight:900;">人気</span>')
add("プラン表クリーン", f'''
<div style="padding:60px 84px;">{kick("料金プラン")}
  <div class="jp" style="font-size:28px;font-weight:900;margin-top:12px;">課題と予算にあわせて、4つのプラン</div>
  <div style="margin-top:40px;border-top:2px solid {INK};">
    <div style="display:flex;border-bottom:1.5px solid {INK};" class="jp">
      <div style="flex:1.6;padding:14px 8px;font-size:12.5px;font-weight:900;color:{GRAY};">プラン</div>
      <div style="flex:1;padding:14px 8px;font-size:12.5px;font-weight:900;color:{GRAY};text-align:right;">月額（税別）</div>
      <div style="flex:1;padding:14px 8px;font-size:12.5px;font-weight:900;color:{GRAY};text-align:right;">稼働</div>
      <div style="flex:2.4;padding:14px 8px 14px 40px;font-size:12.5px;font-weight:900;color:{GRAY};">向いている会社</div></div>''' +
    "".join(f'<div style="display:flex;align-items:center;border-bottom:1px solid {HL};{"background:rgba(175,50,44,.04);" if hi else ""}" class="jp">'
            f'<div style="flex:1.6;padding:19px 8px;font-size:16px;font-weight:900;">{n}{BADGE if hi else ""}</div>'
            f'<div class="num" style="flex:1;padding:19px 8px;font-size:18px;font-weight:900;text-align:right;color:{RED if hi else INK};">{p}<span style="font-size:12px;color:{GRAY};">万円</span></div>'
            f'<div class="num jp" style="flex:1;padding:19px 8px;font-size:14px;text-align:right;color:{GRAY};">{h}</div>'
            f'<div style="flex:2.4;padding:19px 8px 19px 40px;font-size:13.5px;color:#3A3F47;">{d}</div></div>'
            for n, p, h, d, hi in [("ライト", "20", "50h/月", "実働だけ任せたい。予算優先。", 0),
                                   ("ベーシック", "35", "100h/月", "実行主体を任せ、戦略は伴走してほしい。", 1),
                                   ("アドバイザリー", "50", "設計のみ", "設計だけプロに。実行は内製。※3ヶ月固定", 0),
                                   ("プレミアム", "80", "フル", "採用チームごと外部に持ちたい。", 0)]) +
    f'''</div>
  <div class="jp" style="margin-top:18px;font-size:12.5px;color:{GRAY};">最低契約6ヶ月（アドバイザリーは3ヶ月）。御社専用のお見積りは別途。</div>
</div>{foot("", "18")}''')

# H11 引用＋数字（顧客の声）
add("引用＋結果数字", f'''
<div style="padding:60px 84px;">{kick("導入企業の声")}
  <div style="display:flex;gap:90px;margin-top:60px;align-items:center;">
    <div style="width:640px;">
      <div class="num" style="font-size:90px;font-weight:900;color:{RED};line-height:.5;">“</div>
      <div class="jp" style="font-size:24px;font-weight:700;line-height:1.95;margin-top:8px;">スカウトの返信が来るたび、<br>「うちでも採れるんだ」と<br>チームの空気が変わった。</div>
      <div style="display:flex;align-items:center;gap:16px;margin-top:30px;">
        <div style="width:40px;height:1.5px;background:{RED};"></div>
        <div class="jp" style="font-size:13px;color:{GRAY};">IT（大阪・80名）・代表取締役</div></div>
    </div>
    <div style="flex:1;text-align:center;border-left:1px solid {HL};padding-left:70px;">
      <div class="num jp" style="font-size:100px;font-weight:900;line-height:1;">97<span style="font-size:40px;">件</span></div>
      <div class="jp" style="font-size:14px;color:{GRAY};margin-top:14px;">導入初月の応募数<br>（それまで月3件）</div>
    </div>
  </div>
</div>{foot("社内実績・事例値。", "17")}''')

# H12 サマリー＋CTA帯
add("サマリー＋次アクション", f'''
<div style="padding:60px 84px;">{kick("まとめ")}
  <div class="jp" style="font-size:28px;font-weight:900;margin-top:12px;">ご提案は、シンプルです</div>
  <div style="margin-top:44px;width:1040px;">''' +
    "".join(f'<div style="display:flex;align-items:baseline;gap:32px;padding:18px 0;">'
            f'<div class="jp" style="width:300px;font-size:17px;font-weight:900;">{t}</div>'
            f'<div class="jp" style="flex:1;font-size:14px;color:{GRAY};line-height:1.9;">{d}</div></div>'
            for t, d in [("① 現状を数値で見る", "ファネル各段の転換率を可視化（30分・無償）"),
                         ("② 効く1〜2箇所に集中", "全部やらない。ROIが最大の打ち手から着手"),
                         ("③ 6ヶ月で型を残す", "実働しながらFMT納品。内製で回る状態で卒業")]) +
    f'''</div>
  <div style="margin-top:40px;background:{INK};padding:26px 40px;display:flex;justify-content:space-between;align-items:center;width:1040px;">
    <div class="jp" style="color:#fff;font-size:18px;font-weight:900;">まず、現状のKPIを一緒に見ませんか。</div>
    <div class="en" style="color:#E5B4B0;font-size:12px;font-weight:700;">30min Session →</div></div>
</div>{foot("", "22")}''')


def main():
    paths = []
    for n, name, html in SLIDES:
        p = "/tmp/body_%02d.html" % n
        open(p, "w", encoding="utf-8").write(html)
        paths.append(p)
    print("slides:", len(paths))
    pid, url = H.insert_many(paths, title="TOKUMORI ｜ 本編スライド理想形さがし（H01-H12）",
                             slide_id=os.environ.get("SLIDE_ID"), dpi=3)
    print("BODY SAMPLES:", url)


if __name__ == "__main__":
    main()
