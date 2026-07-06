#!/usr/bin/env python3
"""A2「社会人マインドセット」コピー(.a2_hybrid_id)の図解スライドをハイブリッド化。

各図解(曲線/比較)= HTML/SVGの高品質画像、文字(kicker/タイトル/POINT/フッター)= ネイティブ編集可能テキスト。
対象: s22 複利の成長 / s23 忘却曲線 / s24 復習の効果 / s26 ダニング / s20 量と質。
"""
import os
import uuid
import warnings

warnings.filterwarnings("ignore")
from googleapiclient.discovery import build

import build_slides as bs
import html_to_slide as H
from build_slides import IN, MX, CW
from build_hybrid_dunning import FIG as FIG_DUNNING

FONTS = ('<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@500;700;900&'
         'family=IBM+Plex+Mono:wght@500&display=swap" rel="stylesheet"/>')
STYLE = ('<style>*{margin:0;box-sizing:border-box;}html,body{width:1280px;height:300px;background:#fff;'
         'font-family:"Noto Sans JP",sans-serif;}svg{display:block;}'
         '.lab{font-size:19px;font-weight:700;fill:#1A1714;}.sub{font-size:15px;fill:#7C736D;font-family:"IBM Plex Mono",monospace;}'
         '.v{font-size:17px;font-weight:700;}.sm{font-size:16px;font-weight:700;}</style>')


def svg(inner):
    return ('<!DOCTYPE html><html><head><meta charset="utf-8"/>' + FONTS + STYLE +
            '</head><body><svg width="1280" height="300" viewBox="0 0 1280 300">' + inner + '</svg></body></html>')


AX = ('<line x1="80" y1="252" x2="1205" y2="252" stroke="#D9D2CE" stroke-width="2"/>'
      '<line x1="80" y1="30" x2="80" y2="252" stroke="#D9D2CE" stroke-width="2"/>')


def fig_forget():
    inner = AX + (
        '<path d="M90,44 C150,100 210,122 290,131 C370,142 430,152 500,160 C600,170 660,176 720,181 C840,191 980,202 1080,208" fill="none" stroke="#AF322C" stroke-width="4.5" stroke-linecap="round"/>'
        '<circle cx="90" cy="44" r="5" fill="#AF322C"/><circle cx="290" cy="131" r="5" fill="#AF322C"/><circle cx="500" cy="160" r="5" fill="#AF322C"/><circle cx="720" cy="181" r="5" fill="#AF322C"/><circle cx="1080" cy="208" r="5" fill="#AF322C"/>'
        '<text x="100" y="38" class="v" fill="#AF322C">100%</text><text x="290" y="123" class="v" fill="#AF322C" text-anchor="middle">58%</text>'
        '<text x="500" y="152" class="v" fill="#AF322C" text-anchor="middle">44%</text><text x="720" y="173" class="v" fill="#AF322C" text-anchor="middle">34%</text><text x="1080" y="200" class="v" fill="#AF322C" text-anchor="middle">21%</text>'
        '<text x="290" y="274" class="sub" text-anchor="middle">20分後</text><text x="500" y="274" class="sub" text-anchor="middle">1時間後</text><text x="720" y="274" class="sub" text-anchor="middle">1日後</text><text x="1080" y="274" class="sub" text-anchor="middle">1週間後</text>'
        '<text x="70" y="48" class="sub" text-anchor="end">100%</text><text x="70" y="252" class="sub" text-anchor="end">0%</text>'
        '<text x="40" y="145" class="lab" text-anchor="middle" transform="rotate(-90 40 145)">保持率</text>')
    return svg(inner)


def fig_compound():
    inner = AX + (
        '<path d="M90,247 L1190,247" fill="none" stroke="#C7BFB9" stroke-width="2.5" stroke-dasharray="7 6"/>'
        '<path d="M90,247 C500,250 800,251 1190,252" fill="none" stroke="#CFC7C1" stroke-width="2.5"/>'
        '<path d="M90,247 C300,243 380,236 500,224 C640,210 720,160 850,128 C980,98 1080,68 1190,55" fill="none" stroke="#AF322C" stroke-width="5" stroke-linecap="round"/>'
        '<circle cx="1190" cy="55" r="6" fill="#AF322C"/>'
        '<text x="1180" y="44" class="v" fill="#AF322C" text-anchor="end">37.8倍</text>'
        '<text x="1185" y="235" class="sm" fill="#8A827C" text-anchor="end">現状維持 ×1.0</text>'
        '<text x="900" y="120" class="sm" fill="#AF322C" text-anchor="end">毎日 +1%</text>'
        '<text x="430" y="268" class="sm" fill="#B0742A">毎日 −1% → ×0.03</text>'
        '<text x="90" y="274" class="sub">開始</text><text x="640" y="274" class="sub" text-anchor="middle">6ヶ月</text><text x="1190" y="274" class="sub" text-anchor="end">1年</text>'
        '<text x="40" y="145" class="lab" text-anchor="middle" transform="rotate(-90 40 145)">成長</text>')
    return svg(inner)


def fig_review():
    inner = AX + (
        '<path d="M90,44 C170,120 260,165 380,190 C560,222 800,238 1150,244" fill="none" stroke="#C0B8B2" stroke-width="3"/>'
        '<text x="1150" y="236" class="sm" fill="#8A827C" text-anchor="end">復習なし</text>'
        '<path d="M90,44 C140,78 190,96 240,102 L240,58 C320,80 400,92 470,98 L470,64 C600,82 720,90 820,92 L820,70 C950,80 1060,82 1180,80" fill="none" stroke="#AF322C" stroke-width="5" stroke-linecap="round"/>'
        '<text x="240" y="50" class="sm" fill="#AF322C" text-anchor="middle">↑復習</text><text x="470" y="56" class="sm" fill="#AF322C" text-anchor="middle">↑復習</text><text x="820" y="62" class="sm" fill="#AF322C" text-anchor="middle">↑復習</text>'
        '<circle cx="1180" cy="80" r="6" fill="#AF322C"/><text x="1175" y="72" class="v" fill="#AF322C" text-anchor="end">定着</text>'
        '<text x="90" y="274" class="sub">学習直後</text><text x="470" y="274" class="sub" text-anchor="middle">1週間後</text><text x="1180" y="274" class="sub" text-anchor="end">1ヶ月後</text>'
        '<text x="70" y="48" class="sub" text-anchor="end">100%</text><text x="70" y="252" class="sub" text-anchor="end">0%</text>'
        '<text x="40" y="145" class="lab" text-anchor="middle" transform="rotate(-90 40 145)">保持率</text>')
    return svg(inner)


def fig_quantity():
    body = ('<!DOCTYPE html><html><head><meta charset="utf-8"/>' + FONTS +
            '<style>*{margin:0;box-sizing:border-box;}html,body{width:1280px;height:300px;background:#fff;font-family:"Noto Sans JP",sans-serif;color:#1A1714;}'
            '.wrap{display:flex;height:300px;align-items:center;justify-content:center;gap:34px;padding:0 40px;}'
            '.c{flex:1;max-width:480px;border:1px solid #E6E3E1;border-radius:14px;padding:22px 26px;}'
            '.c.win{border-color:#AF322C;box-shadow:0 10px 26px rgba(175,50,44,.13);}'
            '.tag{font-family:"IBM Plex Mono",monospace;font-size:14px;color:#7C736D;letter-spacing:.06em;}'
            '.c.win .tag{color:#AF322C;font-weight:700;}'
            '.row{display:flex;align-items:baseline;gap:10px;margin-top:8px;}'
            '.dab{font-size:30px;font-weight:900;}.arrow{font-size:20px;color:#AF322C;}'
            '.hit{font-size:46px;font-weight:900;color:#1A1714;}.c.win .hit{color:#AF322C;}'
            '.unit{font-size:16px;font-weight:700;}.avg{font-family:"IBM Plex Mono",monospace;font-size:14px;color:#7C736D;margin-top:6px;}'
            '.vs{font-family:"Shippori Mincho B1",serif;font-size:26px;font-weight:800;color:#AF322C;}'
            '.win-badge{display:inline-block;margin-top:8px;background:#AF322C;color:#fff;font-size:12px;font-weight:700;border-radius:999px;padding:3px 12px;}</style>'
            '</head><body><div class="wrap">'
            '<div class="c"><div class="tag">完璧主義</div><div class="row"><span class="dab">10打数</span><span class="arrow">→</span><span class="hit">10</span><span class="unit">安打</span></div><div class="avg">打率 100%（失敗ゼロ）</div></div>'
            '<div class="vs">＜</div>'
            '<div class="c win"><div class="tag">挑戦量</div><div class="row"><span class="dab">100打数</span><span class="arrow">→</span><span class="hit">11</span><span class="unit">安打</span></div><div class="avg">打率 11%（失敗だらけ）</div><span class="win-badge">安打の絶対数で勝つ</span></div>'
            '</div></body></html>')
    return body


FIGS = {
    21: ("図解 ・ 複利の成長", "毎日1%成長の“指数関数”",
         "1.01の365乗≒37.8、0.99の365乗≒0.03。毎日のわずかな差が複利で“指数関数的”に開く。", fig_compound),
    22: ("図解 ・ 忘却曲線", "エビングハウスの忘却曲線",
         "学んだ事は1日で約7割忘れる（エビングハウス, 1885）。だから“即実行・当日復習・記録”で記憶を定着させる。", fig_forget),
    23: ("図解 ・ 復習の効果", "復習で忘却はゆるやかになる",
         "復習しないと1ヶ月で約1割しか残らない。直後・1日後・1週間後・1ヶ月後に復習すると忘却がゆるやかになり長期記憶に定着する（分散学習）。", fig_review),
    25: ("図解 ・ 自己認知", "ダニング＝クルーガー効果の曲線",
         "能力が低いほど自信過剰（馬鹿の山）→学ぶほど無知に気づき急落（絶望の谷）→経験で回復。谷で辞めないことが本物。", lambda: FIG_DUNNING),
    19: ("図解 ・ 量と質", "量と質：まず打席に立て",
         "打率（失敗の少なさ）でなく“安打の絶対数”で評価される。100打数11安打＞10打数10安打。", fig_quantity),
}


def main():
    c = H.creds()
    slides = build("slides", "v1", credentials=c)
    dr = build("drive", "v3", credentials=c)
    nid = open(os.path.join(H.BASE, ".a2_hybrid_id")).read().strip()
    pres = slides.presentations().get(presentationId=nid).execute()
    sl = pres["slides"]
    imgW = CW
    imgH = CW * 300 // 1280

    for idx, (kicker, title, point, figfn) in FIGS.items():
        s = sl[idx]
        sid = s["objectId"]
        png = H.render_png_fromstr(figfn(), 1280, 300, 2)
        fid = H.upload_drive(dr, png)
        url = "https://drive.google.com/uc?export=download&id=%s" % fid
        dels = [{"deleteObject": {"objectId": e["objectId"]}} for e in s.get("pageElements", [])]
        dk = bs.Deck(total=1, nonce="hb" + uuid.uuid4().hex[:4]); dk.page = idx + 1
        dk.mark(sid); dk.kicker(sid, kicker); dk.head_title(sid, title)
        dk.reqs.append({"createImage": {"objectId": dk._id("im"), "url": url,
            "elementProperties": {"pageObjectId": sid,
                "size": {"width": {"magnitude": imgW, "unit": "EMU"}, "height": {"magnitude": imgH, "unit": "EMU"}},
                "transform": {"scaleX": 1, "scaleY": 1, "translateX": MX, "translateY": int(1.55 * IN), "unit": "EMU"}}}})
        dk.callout(sid, "POINT", point)
        dk.footer(sid, "A2 社会人マインド")
        bs.safe_bu(slides, nid, dels + dk.reqs)
        print("  hybrid化: slide %d (%s)" % (idx + 1, title))

    print("DONE:", "https://docs.google.com/presentation/d/%s/edit" % nid)


if __name__ == "__main__":
    main()
