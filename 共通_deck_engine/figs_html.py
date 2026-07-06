#!/usr/bin/env python3
"""build_slides の図（横棒/折れ線/2×2/フロー）を HTMLハイブリッドの“スマート図”にするHTML生成。
トークン T={RED,INK,SUB,PANEL,FAINT,RULE,HEAD,MONO}（色は#なしhex）を受け取り、1280xH のHTML文字列を返す。
引き算の美学：1図1赤アクセント・細線・等幅数値・余白。文字はネイティブでなく図内（=画像）だがデータから再生成可。"""

GRAY = "C8C2BC"  # 非強調バー/ドットの中立グレー（後方互換）
# グレー3段（研究：赤は主役1つ・残りは全てグレースケール）
G_DARK = "4A4D52"   # 濃いグレー（第2系列・強めの非強調）
G_MID = "8A8D93"    # 中グレー（演算子・補助ラベル）
G_LIGHT = "D8DADD"  # 淡いグレー（最下位スライス・背景寄り）


def _doc(inner, h, T):
    # T 指定の見出し/本文/数字フォントも必ず読み込む（consult=BIZ UDPGothic/Noto Sans JP 等）。後方互換でIBM Plexも。
    fams = []
    for k in ("HEAD", "BODY", "MONO"):
        f = T.get(k)
        if f and f not in fams:
            fams.append(f)
    for f in ("IBM Plex Sans JP", "IBM Plex Mono"):
        if f not in fams:
            fams.append(f)
    q = "&".join("family=" + f.replace(" ", "+") + ":wght@400;500;700" for f in fams)
    link = '<link href="https://fonts.googleapis.com/css2?' + q + '&display=swap" rel="stylesheet"/>'
    bg = T.get("BG", "ffffff")  # 図の地色をスライド地色に一致（純白との継ぎ目を防ぐ）
    return ('<!DOCTYPE html><html><head><meta charset="utf-8"/>' + link +
            '<style>*{margin:0;box-sizing:border-box;}html,body{width:1280px;height:%dpx;background:#%s;}'
            'svg{display:block;}</style></head><body>'
            '<svg width="1280" height="%d" viewBox="0 0 1280 %d">%s</svg></body></html>' % (h, bg, h, h, inner))


def _smooth(pts):
    if len(pts) < 3:
        return "M" + " L".join("%.1f,%.1f" % p for p in pts)
    d = "M%.1f,%.1f" % pts[0]
    for i in range(len(pts) - 1):
        p0 = pts[i - 1] if i > 0 else pts[i]
        p1 = pts[i]; p2 = pts[i + 1]; p3 = pts[i + 2] if i + 2 < len(pts) else p2
        c1x = p1[0] + (p2[0] - p0[0]) / 6.0; c1y = p1[1] + (p2[1] - p0[1]) / 6.0
        c2x = p2[0] - (p3[0] - p1[0]) / 6.0; c2y = p2[1] - (p3[1] - p1[1]) / 6.0
        d += " C%.1f,%.1f %.1f,%.1f %.1f,%.1f" % (c1x, c1y, c2x, c2y, p2[0], p2[1])
    return d


def waterfall_html(items, T, H=410):
    """ウォーターフォール（ブリッジ）。items=[(label, value, kind)] kind='abs'(0基準の小計/合計棒)/'pos'/'neg'(浮遊デルタ)。
    正＝上向き・負＝下向き（think-cell流）。abs=主役色、デルタ=グレー。データラベルを各棒に直貼り・段間を点線で接続。"""
    n = max(1, len(items)); top = 46; bottom = H - 56; plot = bottom - top
    seq = []; cum = 0.0; maxv = 0.0
    for label, v, kind in items:
        v = float(v)
        if kind == "abs":
            lo, hi, ce = 0.0, v, v
        elif kind == "neg":
            hi, lo = cum, cum + v; ce = lo
        else:
            lo, hi = cum, cum + v; ce = hi
        cum = ce; seq.append((label, lo, hi, kind, v, ce)); maxv = max(maxv, hi, lo)
    sc = plot / (maxv if maxv > 0 else 1)
    gap = (1280 - 120) // n; barw = min(170, gap - 44); x0 = 60
    s = ""
    for i, (label, lo, hi, kind, v, ce) in enumerate(seq):
        cx = x0 + i * gap + gap // 2; yhi = bottom - hi * sc; ylo = bottom - lo * sc
        col = T["RED"] if kind == "abs" else (GRAY if v < 0 else G_DARK)
        s += '<rect x="%d" y="%.0f" width="%d" height="%.0f" fill="#%s"/>' % (cx - barw // 2, min(yhi, ylo), barw, abs(ylo - yhi), col)
        vlabel = ("%d" % v) if kind == "abs" else ("%+d" % v)
        s += '<text x="%d" y="%.0f" font-family="%s" font-size="18" font-weight="700" fill="#%s" text-anchor="middle">%s</text>' % (cx, min(yhi, ylo) - 9, T["MONO"], T["INK"], vlabel)
        s += '<text x="%d" y="%.0f" font-family="%s" font-size="14" fill="#%s" text-anchor="middle">%s</text>' % (cx, bottom + 26, T["HEAD"], T["SUB"], label)
        if i < len(seq) - 1:
            yc = bottom - ce * sc
            s += '<line x1="%d" y1="%.0f" x2="%d" y2="%.0f" stroke="#%s" stroke-width="1.3" stroke-dasharray="4,3"/>' % (cx + barw // 2, yc, cx + gap - barw // 2, yc, T["BORDER"])
    return _doc(s, H, T)


def bar_html(items, T, H=380):
    """items=[(label, frac0_1, valtext, highlight_bool)] 横棒（スマート）。"""
    n = max(1, len(items)); top = 34; step = (H - 60) // n; bh = min(42, step - 24)
    barx = 320; barmax = 1280 - barx - 160; gutter = barx - 54
    s = ""
    for i, it in enumerate(items):
        label, frac, val, hi = (list(it) + [0, "", False])[:4]
        y = top + i * step
        col = T["RED"] if hi else GRAY
        lc = T["RED"] if hi else T["INK"]
        w = max(6, int(barmax * max(0.0, min(1.0, float(frac)))))
        emw = sum(0.55 if ord(c) < 128 else 1.0 for c in str(label)) or 1.0  # ラベルをガター幅にフィット
        lfs = max(12, min(21, int(gutter / emw)))
        s += ('<text x="40" y="%d" font-family="%s" font-size="%d" font-weight="700" fill="#%s">%s</text>'
              '<rect x="%d" y="%d" width="%d" height="%d" rx="7" fill="#%s"/>'
              '<rect x="%d" y="%d" width="%d" height="%d" rx="7" fill="#%s"/>'
              '<text x="%d" y="%d" font-family="%s" font-size="19" font-weight="500" fill="#%s">%s</text>'
              % (int(y + bh * 0.72), T["HEAD"], lfs, lc, label,
                 barx, y, barmax, bh, T["PANEL"],
                 barx, y, w, bh, col,
                 barx + w + 16, int(y + bh * 0.74), T["MONO"], lc, val))
    return _doc(s, H, T)


def line_html(xlabels, series, T, ylab=None, H=370):
    """xlabels=[..]; series=[{name,ys:[0-1],vals,hi}] 滑らかな折れ線（スマート）。"""
    n = len(xlabels)
    plx = 96; ply = 28; plw = 1280 - plx - 60; plh = H - 96
    xs = [plx + (plw * i // max(1, n - 1)) for i in range(n)]
    def yp(v): return ply + (1 - max(0.0, min(1.0, float(v)))) * plh
    s = ('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#%s" stroke-width="1.5"/>'
         % (plx, ply + plh, plx + plw, ply + plh, T["RULE"]))
    for sr in series:
        ys = sr["ys"]; hi = sr.get("hi"); col = T["RED"] if hi else GRAY
        pts = [(xs[i], yp(ys[i])) for i in range(min(n, len(ys)))]
        if len(pts) > 1:
            s += '<path d="%s" fill="none" stroke="#%s" stroke-width="%s" stroke-linecap="round" stroke-linejoin="round"/>' % (
                _smooth(pts), col, "3.4" if hi else "2")
        if hi:
            for i, (px, py) in enumerate(pts):
                s += '<circle cx="%.1f" cy="%.1f" r="5" fill="#%s"/>' % (px, py, col)
                vals = sr.get("vals")
                if vals and i < len(vals) and vals[i]:
                    s += '<text x="%.1f" y="%.1f" font-family="%s" font-size="17" font-weight="500" fill="#%s" text-anchor="middle">%s</text>' % (
                        px, py - 14, T["MONO"], col, vals[i])
    for i, lab in enumerate(xlabels):
        if lab:
            s += '<text x="%.1f" y="%d" font-family="%s" font-size="15" fill="#%s" text-anchor="middle">%s</text>' % (
                xs[i], H - 18, T["MONO"], T["SUB"], lab)
    if ylab:
        s += '<text x="38" y="%d" font-family="%s" font-size="16" font-weight="700" fill="#%s" text-anchor="middle" transform="rotate(-90 38 %d)">%s</text>' % (
            int(ply + plh / 2), T["HEAD"], T["INK"], int(ply + plh / 2), ylab[0] if isinstance(ylab, (list, tuple)) else ylab)
    return _doc(s, H, T)


def quad_html(xlab, ylab, quads, T, H=460):
    """quads=[(head,desc,hi)] を TL,TR,BL,BR で。2×2マトリクス。
    軸ラベルは外側のガター帯（縦=左/横=下）に逃がし見切れを防止。推奨象限(hi)に淡赤フィル＝1アクセント。"""
    gx = 96; gy = 30; gw = 1280 - gx - 64; gh = H - gy - 60   # 下56px帯/左gx帯=ガター
    cw = gw // 2; ch = gh // 2
    cells = [(gx, gy), (gx + cw, gy), (gx, gy + ch), (gx + cw, gy + ch)]
    s = ""
    for idx, q in enumerate(quads[:4]):
        if (list(q) + ["", "", False])[2]:  # hi=推奨象限に淡赤フィル
            hx, hy = cells[idx]
            s += '<rect x="%d" y="%d" width="%d" height="%d" fill="#%s" fill-opacity="0.55"/>' % (
                hx, hy, cw, ch, T.get("LRED", "F3E3E0"))
    s += ('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#%s" stroke-width="1.5"/>'
          '<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#%s" stroke-width="1.5"/>'
          % (gx, gy, gx, gy + gh, T["RULE"], gx, gy + gh, gx + gw, gy + gh, T["RULE"]))
    s += '<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#%s" stroke-width="1"/>' % (gx + cw, gy, gx + cw, gy + gh, T["FAINT"])
    s += '<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#%s" stroke-width="1"/>' % (gx, gy + ch, gx + gw, gy + ch, T["FAINT"])
    for idx, (hx, hy) in enumerate(cells):
        if idx >= len(quads):
            break
        head, desc, hi = (list(quads[idx]) + ["", "", False])[:3]
        hc = T["RED"] if hi else T["INK"]
        s += '<text x="%d" y="%d" font-family="%s" font-size="22" font-weight="700" fill="#%s">%s</text>' % (
            hx + 26, hy + 48, T["HEAD"], hc, head)
        s += '<text x="%d" y="%d" font-family="%s" font-size="15" fill="#%s">%s</text>' % (
            hx + 26, hy + 76, T["BODY"], T["SUB"], desc[:26])
    s += '<text x="%d" y="%d" font-family="%s" font-size="16" letter-spacing="1" fill="#%s" text-anchor="middle">%s</text>' % (
        gx + gw // 2, H - 20, T["MONO"], T["SUB"], xlab)
    s += '<text x="%d" y="%d" font-family="%s" font-size="16" letter-spacing="1" fill="#%s" text-anchor="middle" transform="rotate(-90 %d %d)">%s</text>' % (
        42, gy + gh // 2, T["MONO"], T["SUB"], 42, gy + gh // 2, ylab)
    return _doc(s, H, T)


def flow_html(steps, T, accent=None, H=300):
    """steps=[(badge,label,desc)] 横並びのステップ図（スマート・中核1枚に赤枠）。"""
    n = max(1, len(steps))
    gap = 26; cardw = (1280 - 80 - gap * (n - 1)) // n
    s = '<defs><marker id="fa" markerWidth="9" markerHeight="9" refX="6" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 Z" fill="#%s"/></marker></defs>' % T["CON"] if T.get("CON") else \
        '<defs><marker id="fa" markerWidth="9" markerHeight="9" refX="6" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 Z" fill="#C7BFB9"/></marker></defs>'
    con = T.get("CON", "C7BFB9")
    cy = 44; chh = H - 90
    for i, st in enumerate(steps):
        badge, label, desc = (list(st) + ["", "", ""])[:3]
        x = 40 + i * (cardw + gap)
        acc = (accent == i) if accent is not None else (i == n // 2 and n > 2)
        bd = T["RED"] if acc else T["RULE"]
        nc = T["RED"] if acc else T["SUB"]
        s += ('<g transform="translate(%d,%d)">'
              '<rect x="0" y="0" width="%d" height="%d" rx="8" fill="#fff" stroke="#%s" stroke-width="%s"/>'
              '<text x="22" y="44" font-family="%s" font-size="22" font-weight="500" fill="#%s">%s</text>'
              '<line x1="22" y1="60" x2="50" y2="60" stroke="#%s" stroke-width="2"/>'
              '<text x="22" y="104" font-family="%s" font-size="20" font-weight="700" fill="#%s">%s</text>'
              '<text x="22" y="140" font-family="%s" font-size="14" fill="#%s"><tspan x="22" dy="0">%s</tspan><tspan x="22" dy="22">%s</tspan></text>'
              '</g>'
              % (x, cy, cardw, chh, bd, ("1.8" if acc else "1"),
                 T["MONO"], nc, badge,
                 nc,
                 T["HEAD"], T["INK"], label,
                 T["HEAD"], T["SUB"], desc[:14], desc[14:28]))
        if i < n - 1:
            ax = x + cardw
            s += '<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#%s" stroke-width="1.5" marker-end="url(#fa)"/>' % (
                ax + 3, cy + chh // 2, ax + gap - 4, cy + chh // 2, con)
    return _doc(s, H, T)


# ===== 概念図（図解ファースト用） =====

def pyramid_html(levels, T, H=430):
    """levels=[(label, desc)] 上→下。階層・優先順位。頂点のみ赤アクセント。"""
    n = max(1, len(levels)); cx = 640; topW = 150; baseW = 1040; y0 = 36; total = H - 110
    dw = (baseW - topW) / n; bh = total / n
    s = ""
    for i, lv in enumerate(levels):
        label, desc = (list(lv) + ["", ""])[:2]
        wt = topW + i * dw; wb = topW + (i + 1) * dw
        yt = y0 + i * bh; yb = yt + bh - 8
        fill = "#" + T["RED"] if i == 0 else "#" + T["PANEL"]
        tc = "#fff" if i == 0 else "#" + T["INK"]
        s += '<polygon points="%.0f,%.0f %.0f,%.0f %.0f,%.0f %.0f,%.0f" fill="%s" stroke="#%s" stroke-width="1"/>' % (
            cx - wt / 2, yt, cx + wt / 2, yt, cx + wb / 2, yb, cx - wb / 2, yb, fill, T["BORDER"] if i else T["RED"])
        s += '<text x="%d" y="%.0f" font-family="%s" font-size="20" font-weight="700" fill="%s" text-anchor="middle">%s</text>' % (
            cx, yt + bh / 2 + 2, T["HEAD"], tc, label)
        if desc:
            s += '<text x="%d" y="%.0f" font-family="%s" font-size="13" fill="%s" text-anchor="middle">%s</text>' % (
                cx, yt + bh / 2 + 24, T["BODY"], ("rgba(255,255,255,0.85)" if i == 0 else "#" + T["SUB"]), desc[:34])
    return _doc(s, H, T)


def relation_html(center, nodes, T, H=440):
    """center=中心ラベル, nodes=[label,...] 周囲。関係・エコシステム。中心のみ赤。"""
    cx, cy = 640, H // 2 - 10; rx, ry = 400, H // 2 - 70; n = max(1, len(nodes))
    import math as _m
    s = ""
    pos = []
    for i in range(n):
        ang = _m.pi / 2 - i * (2 * _m.pi / n)
        pos.append((cx + rx * _m.cos(ang), cy - ry * _m.sin(ang)))
    for (x, y) in pos:
        s += '<line x1="%d" y1="%d" x2="%.0f" y2="%.0f" stroke="#%s" stroke-width="2"/>' % (cx, cy, x, y, T["RULE"])
    for i, (x, y) in enumerate(pos):
        s += ('<circle cx="%.0f" cy="%.0f" r="58" fill="#fff" stroke="#%s" stroke-width="1.5"/>'
              '<text x="%.0f" y="%.0f" font-family="%s" font-size="17" font-weight="700" fill="#%s" text-anchor="middle">%s</text>'
              % (x, y, T["BORDER"], x, y + 6, T["HEAD"], T["INK"], nodes[i]))
    s += ('<circle cx="%d" cy="%d" r="80" fill="#%s"/>'
          '<text x="%d" y="%d" font-family="%s" font-size="20" font-weight="700" fill="#fff" text-anchor="middle">%s</text>'
          % (cx, cy, T["RED"], cx, cy + 7, T["HEAD"], center))
    return _doc(s, H, T)


def timeline_html(phases, T, H=300):
    """phases=[(label, sub)] フェーズ/ロードマップ。最後を赤(到達)に。"""
    n = max(1, len(phases)); y = H // 2; x0 = 90; x1 = 1190; step = (x1 - x0) // max(1, n - 1)
    s = '<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#%s" stroke-width="3"/>' % (x0, y, x1, y, T["RULE"])
    for i, ph in enumerate(phases):
        label, sub = (list(ph) + ["", ""])[:2]
        x = x0 + i * step; last = (i == n - 1)
        col = T["RED"] if last else T["SUB"]
        s += '<circle cx="%d" cy="%d" r="%d" fill="#%s"/>' % (x, y, 13 if last else 10, col)
        s += '<text x="%d" y="%d" font-family="%s" font-size="19" font-weight="700" fill="#%s" text-anchor="middle">%s</text>' % (
            x, y - 34, T["HEAD"], T["INK"], label)
        if sub:
            s += '<text x="%d" y="%d" font-family="%s" font-size="14" fill="#%s" text-anchor="middle">%s</text>' % (
                x, y + 44, T["BODY"], T["SUB"], sub[:18])
    return _doc(s, H, T)


def ladder_html(steps, T, H=430):
    """steps=[(label, sub)] 下→上に昇る段（キャリア段階）。最上段(到達)を赤に。"""
    n = max(1, len(steps)); gap = 20; sw = (1200 - gap * (n - 1)) // n
    base = H - 40; rise = (H - 90) // n
    s = ""
    for i, st in enumerate(steps):
        label, sub = (list(st) + ["", ""])[:2]
        x = 40 + i * (sw + gap); h = rise * (i + 1); y = base - h
        top = (i == n - 1)
        fill = "#" + T["RED"] if top else "#" + T["PANEL"]
        tc = "#fff" if top else "#" + T["INK"]
        sc = "rgba(255,255,255,0.85)" if top else "#" + T["SUB"]
        s += '<rect x="%d" y="%d" width="%d" height="%d" rx="8" fill="%s" stroke="#%s" stroke-width="1"/>' % (
            x, y, sw, h, fill, T["BORDER"] if not top else T["RED"])
        s += '<text x="%d" y="%d" font-family="%s" font-size="18" font-weight="700" fill="%s" text-anchor="middle">%s</text>' % (
            x + sw // 2, y + 38, T["HEAD"], tc, label)
        if sub:
            s += '<text x="%d" y="%d" font-family="%s" font-size="13" fill="%s" text-anchor="middle">%s</text>' % (
                x + sw // 2, y + 62, T["BODY"], sc, sub[:14])
    return _doc(s, H, T)


def before_after_html(before, after, T, H=330):
    """before/after=(title, sub)。対比。Before=ゴースト、After=赤。"""
    bt, bs = (list(before) + ["", ""])[:2]; at, as_ = (list(after) + ["", ""])[:2]
    cw = 470; cy = 40; chh = H - 150; lx = 110; rx = 700
    s = ('<defs><marker id="ba" markerWidth="10" markerHeight="10" refX="5" refY="5" orient="auto">'
         '<path d="M0,0 L10,5 L0,10 Z" fill="#%s"/></marker></defs>' % T["RED"])
    s += ('<rect x="%d" y="%d" width="%d" height="%d" rx="8" fill="#%s" stroke="#%s"/>'
          '<text x="%d" y="%d" font-family="%s" font-size="13" letter-spacing="2" fill="#%s">BEFORE</text>'
          '<text x="%d" y="%d" font-family="%s" font-size="24" font-weight="700" fill="#%s">%s</text>'
          '<text x="%d" y="%d" font-family="%s" font-size="15" fill="#%s">%s</text>'
          % (lx, cy, cw, chh, T["PANEL"], T["BORDER"],
             lx + 28, cy + 44, T["MONO"], T["FAINT"],
             lx + 28, cy + chh // 2 + 4, T["HEAD"], T["SUB"], bt,
             lx + 28, cy + chh // 2 + 34, T["BODY"], T["SUB"], bs[:22]))
    s += '<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#%s" stroke-width="3" marker-end="url(#ba)"/>' % (
        lx + cw + 20, cy + chh // 2, rx - 20, cy + chh // 2, T["RED"])
    s += ('<rect x="%d" y="%d" width="%d" height="%d" rx="8" fill="#fff" stroke="#%s" stroke-width="1.6"/>'
          '<text x="%d" y="%d" font-family="%s" font-size="13" letter-spacing="2" fill="#%s">AFTER</text>'
          '<text x="%d" y="%d" font-family="%s" font-size="24" font-weight="700" fill="#%s">%s</text>'
          '<text x="%d" y="%d" font-family="%s" font-size="15" fill="#%s">%s</text>'
          % (rx, cy, cw, chh, T["RED"],
             rx + 28, cy + 44, T["MONO"], T["RED"],
             rx + 28, cy + chh // 2 + 4, T["HEAD"], T["INK"], at,
             rx + 28, cy + chh // 2 + 34, T["BODY"], T["SUB"], as_[:22]))
    return _doc(s, H, T)


def cycle_html(nodes, T, H=430):
    """nodes=[label,...]（3-4）反復サイクル（PDCA等）。各ノード円＋曲線矢印。"""
    import math as _m
    cx, cy = 640, H // 2 - 5; r = H // 2 - 70; n = max(1, len(nodes))
    s = ('<defs><marker id="cy" markerWidth="9" markerHeight="9" refX="5" refY="4.5" orient="auto">'
         '<path d="M0,0 L9,4.5 L0,9 Z" fill="#%s"/></marker></defs>' % T["SUB"])
    pos = []
    for i in range(n):
        ang = _m.pi / 2 - i * (2 * _m.pi / n)
        pos.append((cx + r * _m.cos(ang), cy - r * _m.sin(ang)))
    for i in range(n):
        x1, y1 = pos[i]; x2, y2 = pos[(i + 1) % n]
        s += '<path d="M%.0f,%.0f A%d,%d 0 0 1 %.0f,%.0f" fill="none" stroke="#%s" stroke-width="2.5" marker-end="url(#cy)"/>' % (
            x1 + (x2 - x1) * 0.12, y1 + (y2 - y1) * 0.12, r, r, x1 + (x2 - x1) * 0.82, y1 + (y2 - y1) * 0.82, T["RULE"])
    for i, (x, y) in enumerate(pos):
        acc = (i == 0)
        s += ('<circle cx="%.0f" cy="%.0f" r="62" fill="%s" stroke="#%s" stroke-width="1.5"/>'
              '<text x="%.0f" y="%.0f" font-family="%s" font-size="18" font-weight="700" fill="%s" text-anchor="middle">%s</text>'
              % (x, y, "#" + T["RED"] if acc else "#fff", T["RED"] if acc else T["BORDER"],
                 x, y + 6, T["HEAD"], "#fff" if acc else "#" + T["INK"], nodes[i]))
    return _doc(s, H, T)


def venn_html(data, T, H=430):
    """data=(左ラベル, 右ラベル, 重なりラベル) 2円ベン図。重なり=赤強調。"""
    left, right, overlap = (list(data) + ["", "", ""])[:3]
    cx = 640; cy = H // 2; r = 158; off = 100
    s = ('<circle cx="%d" cy="%d" r="%d" fill="#%s" fill-opacity="0.08" stroke="#%s" stroke-width="2"/>'
         '<circle cx="%d" cy="%d" r="%d" fill="#%s" fill-opacity="0.10" stroke="#%s" stroke-width="2"/>'
         % (cx - off, cy, r, T["SUB"], T["SUB"], cx + off, cy, r, T["RED"], T["RED"]))
    s += '<text x="%d" y="%d" font-family="%s" font-size="21" font-weight="700" fill="#%s" text-anchor="middle">%s</text>' % (cx - off - 70, cy + 6, T["HEAD"], T["INK"], left)
    s += '<text x="%d" y="%d" font-family="%s" font-size="21" font-weight="700" fill="#%s" text-anchor="middle">%s</text>' % (cx + off + 70, cy + 6, T["HEAD"], T["INK"], right)
    if overlap:
        s += '<text x="%d" y="%d" font-family="%s" font-size="17" font-weight="700" fill="#%s" text-anchor="middle">%s</text>' % (cx, cy + 6, T["HEAD"], T["RED"], overlap)
    return _doc(s, H, T)


def funnel_html(data, T, H=410):
    """data=[(label, frac0_1, val, hi)] 上から細るファネル（選考/採用フロー）。最下段=赤。"""
    n = max(1, len(data)); topw = 940; cx = 640; y0 = 24; bh = (H - 60) // n - 12
    s = ""
    for i, it in enumerate(data):
        label, frac, val, hi = (list(it) + ["", 1.0, "", False])[:4]
        w = max(130, int(topw * float(frac)))
        wn = max(90, int(topw * float(data[i + 1][1]))) if i < n - 1 else max(70, int(w * 0.62))
        y = y0 + i * (bh + 12)
        fill = T["RED"] if (hi or i == n - 1) else GRAY  # 赤は主役1段のみ・他はグレー
        s += '<polygon points="%d,%d %d,%d %d,%d %d,%d" fill="#%s"/>' % (
            cx - w // 2, y, cx + w // 2, y, cx + wn // 2, y + bh, cx - wn // 2, y + bh, fill)
        s += '<text x="%d" y="%d" font-family="%s" font-size="18" font-weight="700" fill="#fff" text-anchor="middle">%s</text>' % (cx, y + bh // 2 + 3, T["HEAD"], label)
        if val:
            s += '<text x="%d" y="%d" font-family="%s" font-size="16" font-weight="500" fill="#%s">%s</text>' % (cx + w // 2 + 24, y + bh // 2 + 5, T["MONO"], T["SUB"], val)
        if i < n - 1:  # 段間の遷移率（CVR）を左側に
            try:
                cvr = int(round(float(data[i + 1][1]) / float(frac) * 100))
                s += '<text x="%d" y="%d" font-family="%s" font-size="14" fill="#%s" text-anchor="middle">↓ %d%%</text>' % (
                    cx - w // 2 - 64, y + bh + 6, T["MONO"], T["SUB"], cvr)
            except (ZeroDivisionError, ValueError, TypeError):
                pass
    return _doc(s, H, T)


def donut_html(data, T, H=410, center=None):
    """data=[(label, frac0_1, hi)] 構成比ドーナツ＋凡例。先頭/hi=赤。center=(big,small) でリング中央に主要数値。"""
    import math as _m
    cx = 380; cy = H // 2; r = 120; sw = 36; C = 2 * _m.pi * r; off = 0.0
    pal = [T["RED"], G_DARK, GRAY, G_MID, G_LIGHT]  # 赤は主役1つ・残りはグレー段階
    s = '<circle cx="%d" cy="%d" r="%d" fill="none" stroke="#%s" stroke-width="%d"/>' % (cx, cy, r, T["RULE"], sw)
    for i, it in enumerate(data):
        label, frac, hi = (list(it) + ["", 0, False])[:3]
        ln = C * float(frac); col = T["RED"] if (hi or i == 0) else pal[i % len(pal)]
        s += '<circle cx="%d" cy="%d" r="%d" fill="none" stroke="#%s" stroke-width="%d" stroke-dasharray="%.1f %.1f" stroke-dashoffset="%.1f" transform="rotate(-90 %d %d)" stroke-linecap="butt"/>' % (
            cx, cy, r, col, sw, ln, C - ln, -off, cx, cy)
        off += ln
    for i, it in enumerate(data):
        label, frac, hi = (list(it) + ["", 0, False])[:3]
        col = T["RED"] if (hi or i == 0) else pal[i % len(pal)]
        yy = cy - 16 * len(data) + i * 38
        s += ('<rect x="660" y="%d" width="16" height="16" rx="4" fill="#%s"/>'
              '<text x="688" y="%d" font-family="%s" font-size="17" fill="#%s">%s</text>'
              '<text x="1180" y="%d" font-family="%s" font-size="17" font-weight="500" fill="#%s" text-anchor="end">%d%%</text>'
              % (yy, col, yy + 14, T["HEAD"], T["INK"], label, yy + 14, T["MONO"], T["SUB"], int(round(float(frac) * 100))))
    if center:
        big, small = (list(center) + ["", ""])[:2]
        s += ('<text x="%d" y="%d" font-family="%s" font-size="30" font-weight="700" fill="#%s" text-anchor="middle">%s</text>'
              % (cx, cy - 2, T["HEAD"], T["INK"], big))
        if small:
            s += ('<text x="%d" y="%d" font-family="%s" font-size="14" fill="#%s" text-anchor="middle">%s</text>'
                  % (cx, cy + 24, T["BODY"], T["SUB"], small))
    return _doc(s, H, T)


def seating_html(seats, T, door="入口", H=430):
    """seats=[(label, nx, ny, top)] nx/ny=0-1。会議室の席次。上座(top)を赤縁。"""
    rx, ry, rw, rh = 220, 36, 840, H - 110
    s = '<rect x="%d" y="%d" width="%d" height="%d" rx="8" fill="#%s" stroke="#%s" stroke-width="1.4"/>' % (
        rx, ry, rw, rh, T["PANEL"], T["INK"])
    if door:  # door="" のときは入口を描かない（乗り物の席次など）
        dw = 150
        s += ('<rect x="%d" y="%d" width="%d" height="26" rx="6" fill="#%s"/>'
              '<text x="%d" y="%d" font-family="%s" font-size="13" font-weight="700" fill="#fff" text-anchor="middle">%s</text>'
              % (rx + rw // 2 - dw // 2, ry + rh - 10, dw, T["INK"], rx + rw // 2, ry + rh + 9, T["HEAD"], door))
    sw, sh = 168, 64
    for st in seats:
        label, nx, ny, top = (list(st) + ["", 0.5, 0.5, False])[:4]
        x = rx + int(nx * rw) - sw // 2; y = ry + int(ny * rh) - sh // 2
        s += ('<rect x="%d" y="%d" width="%d" height="%d" rx="8" fill="%s" stroke="#%s" stroke-width="%s"/>'
              '<text x="%d" y="%d" font-family="%s" font-size="15" font-weight="700" fill="#%s" text-anchor="middle">%s</text>'
              % (x, y, sw, sh, "#" + T["LRED"] if top else "#fff", T["RED"] if top else T["BORDER"], "1.8" if top else "1",
                 x + sw // 2, y + sh // 2 + 5, T["HEAD"], T["RED"] if top else T["INK"], label))
    return _doc(s, H, T)


# ===== 参考PDF（送客サービス案内）由来の再利用フォーマット =====

def platform_html(center, left, right, T, H=440):
    """二面プラットフォーム/仲介図。center=(title,[subline...]) 中央基盤=赤枠、
    left/right=(actor, [(label,dir)... or "label"...])。dir '>'=基盤へ流入 '<'=アクターへ流出（文字列は交互）。
    人材紹介の二面ネットワーク・求職者⇄企業 等。ラベルは短く。"""
    ctitle, csubs = (list(center) + ["", []])[:2]
    if isinstance(csubs, str):
        csubs = [csubs]
    cy = H // 2
    cx0, cw = 470, 340
    cbh = H - 110
    cby = (H - cbh) // 2
    aw, ah = 196, 150
    ay = cy - ah // 2
    lx = 48
    rx = 1280 - 48 - aw
    s = (f'<defs><marker id="pf" markerWidth="10" markerHeight="10" refX="7" refY="5" orient="auto">'
         f'<path d="M0,0 L10,5 L0,10 Z" fill="#{T["CON"]}"/></marker></defs>')
    s += (f'<rect x="{cx0}" y="{cby}" width="{cw}" height="{cbh}" rx="8" fill="#fff" '
          f'stroke="#{T["RED"]}" stroke-width="1.8"/>'
          f'<text x="{cx0+cw//2}" y="{cby+54}" font-family="{T["HEAD"]}" font-size="23" '
          f'font-weight="700" fill="#{T["INK"]}" text-anchor="middle">{ctitle}</text>'
          f'<line x1="{cx0+cw//2-36}" y1="{cby+70}" x2="{cx0+cw//2+36}" y2="{cby+70}" '
          f'stroke="#{T["RED"]}" stroke-width="2"/>')
    for i, sub in enumerate(csubs[:4]):
        s += (f'<text x="{cx0+cw//2}" y="{cby+108+i*30}" font-family="{T["BODY"]}" font-size="15" '
              f'fill="#{T["SUB"]}" text-anchor="middle">{sub}</text>')
    for ax, act in ((lx, left[0]), (rx, right[0])):
        s += (f'<rect x="{ax}" y="{ay}" width="{aw}" height="{ah}" rx="8" fill="#{T["PANEL"]}" '
              f'stroke="#{T["BORDER"]}" stroke-width="1"/>'
              f'<text x="{ax+aw//2}" y="{ay+ah//2+7}" font-family="{T["HEAD"]}" font-size="21" '
              f'font-weight="700" fill="#{T["INK"]}" text-anchor="middle">{act}</text>')

    def draw_arrows(items, x_actor_edge, x_center_edge, num0):
        out = ""
        k = max(1, len(items))
        ys = [cy] if k == 1 else [cy - 70 + j * (140 // (k - 1)) for j in range(k)]
        ax_in = min(x_actor_edge, x_center_edge) + 10
        ax_out = max(x_actor_edge, x_center_edge) - 10
        actor_is_left = x_actor_edge < x_center_edge
        for j, it in enumerate(items[:3]):
            if isinstance(it, (list, tuple)):
                lab, d = (list(it) + ["", ">"])[:2]
            else:
                lab, d = it, (">" if j % 2 == 0 else "<")
            yy = int(ys[j])
            toward_center = (d == ">")
            if (toward_center and actor_is_left) or ((not toward_center) and not actor_is_left):
                x1, x2 = ax_in, ax_out
            else:
                x1, x2 = ax_out, ax_in
            out += (f'<line x1="{x1}" y1="{yy}" x2="{x2}" y2="{yy}" stroke="#{T["CON"]}" '
                    f'stroke-width="1.5" marker-end="url(#pf)"/>')
            out += (f'<text x="{(ax_in+ax_out)//2}" y="{yy-13}" font-family="{T["BODY"]}" '
                    f'font-size="13" fill="#{T["SUB"]}" text-anchor="middle">{lab}</text>')
            bx = ax_in - 2
            out += (f'<circle cx="{bx}" cy="{yy}" r="11" fill="#{T["RED"]}"/>'
                    f'<text x="{bx}" y="{yy+4}" font-family="{T["MONO"]}" font-size="12" '
                    f'font-weight="500" fill="#fff" text-anchor="middle">{num0+j}</text>')
        return out

    larr = left[1] if len(left) > 1 else []
    rarr = right[1] if len(right) > 1 else []
    s += draw_arrows(larr, lx + aw, cx0, 1)
    s += draw_arrows(rarr, cx0 + cw, rx, len(larr[:3]) + 1)
    return _doc(s, H, T)


def formula_html(equation, parts, T, H=430):
    """KPI数式分解。equation='A × B = C'（'='以降=到達指標を赤に）、parts=[(boxlabel,[bullets..][,lead]),..]（1-2項）。
    lead=bullet見出し（任意・既定'改善施策の一例'。フェルミ等は'仮定の例'/'検算のコツ'等に差替え）。"""
    ops = ("×", "＝", "x", "*", "·", "+", "-", "/", "÷")
    if "=" in equation:
        lhs, rhs = equation.split("=", 1)
        lhs_svg = ""
        for tok in lhs.strip().split(" "):
            if tok in ops:  # 演算子は薄グレー＝因子を主役に
                lhs_svg += f'<tspan fill="#{G_MID}"> {tok} </tspan>'
            else:
                lhs_svg += f'<tspan fill="#{T["INK"]}">{tok}</tspan>'
        eqsvg = lhs_svg + f'<tspan fill="#{G_MID}"> = </tspan><tspan fill="#{T["RED"]}">{rhs.strip()}</tspan>'
    else:
        eqsvg = f'<tspan fill="#{T["INK"]}">{equation}</tspan>'
    s = (f'<text x="640" y="92" font-family="{T["HEAD"]}" font-size="46" font-weight="700" '
         f'text-anchor="middle">{eqsvg}</text>')
    m = len(parts)
    centers, bw = ([640], 560) if m == 1 else ([358, 922], 470)
    palette = [T.get("LRED", "F3E3E0"), T["PANEL"]]
    for i, pt in enumerate(parts[:2]):
        boxlabel, bullets, lead = (list(pt) + ["", [], "改善施策の一例"])[:3]
        cx = centers[i]; bx = cx - bw // 2
        s += (f'<line x1="{cx-bw//2+30}" y1="138" x2="{cx+bw//2-30}" y2="138" '
              f'stroke="#{T["RULE"]}" stroke-width="1.5"/>'
              f'<line x1="{cx}" y1="138" x2="{cx}" y2="162" stroke="#{T["RULE"]}" stroke-width="1.5"/>')
        by, bh = 170, 64
        s += (f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="8" fill="#{palette[i % len(palette)]}"/>'
              f'<text x="{cx}" y="{by+bh//2+8}" font-family="{T["HEAD"]}" font-size="23" '
              f'font-weight="700" fill="#{T["INK"]}" text-anchor="middle">{boxlabel}</text>')
        byy = by + bh + 42
        s += (f'<text x="{bx+6}" y="{byy}" font-family="{T["HEAD"]}" font-size="15" '
              f'font-weight="700" fill="#{T["INK"]}">{lead}</text>')
        for j, b in enumerate(bullets[:4]):
            s += (f'<text x="{bx+12}" y="{byy+30+j*30}" font-family="{T["BODY"]}" font-size="15" '
                  f'fill="#{T["SUB"]}">・{b}</text>')
    return _doc(s, H, T)


def converge_html(start, channels, end, T, H=430):
    """多チャネル収束。start=起点ラベル、channels=[ラベル..]（3-5）、end=到達点(赤)。複数施策→1ゴール。"""
    if isinstance(start, (list, tuple)):
        start = start[0]
    if isinstance(end, (list, tuple)):
        end = end[0]
    cy = H // 2
    lx, lw, lh = 40, 220, 132; ly = cy - lh // 2
    px, pw = 360, 430; py, ph = 36, H - 72
    mx = px + pw + 50
    rx, rw, rh = 1040, 200, 132; ry = cy - rh // 2
    s = (f'<defs><marker id="cv" markerWidth="10" markerHeight="10" refX="7" refY="5" orient="auto">'
         f'<path d="M0,0 L10,5 L0,10 Z" fill="#{T["CON"]}"/></marker></defs>')
    s += (f'<rect x="{lx}" y="{ly}" width="{lw}" height="{lh}" rx="8" fill="#fff" '
          f'stroke="#{T["BORDER"]}" stroke-width="1.4"/>'
          f'<text x="{lx+lw//2}" y="{cy+6}" font-family="{T["HEAD"]}" font-size="20" '
          f'font-weight="700" fill="#{T["INK"]}" text-anchor="middle">{start}</text>')
    s += (f'<line x1="{lx+lw}" y1="{cy}" x2="{px-6}" y2="{cy}" stroke="#{T["CON"]}" '
          f'stroke-width="1.6" stroke-dasharray="2 4" marker-end="url(#cv)"/>')
    s += f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="8" fill="#{T["PANEL"]}"/>'
    n = max(1, len(channels[:6])); rowh = ph // n
    ys = []
    for j, ch in enumerate(channels[:6]):
        ry0 = py + j * rowh + rowh // 2; ys.append(ry0)
        s += (f'<circle cx="{px+30}" cy="{ry0}" r="5" fill="#{T["RED"] if j == 0 else T["SUB"]}"/>'
              f'<text x="{px+50}" y="{ry0+6}" font-family="{T["HEAD"]}" font-size="18" '
              f'fill="#{T["INK"]}">{ch}</text>')
    for ry0 in ys:
        s += (f'<path d="M{px+pw} {ry0} C{px+pw+28} {ry0} {mx-14} {cy} {mx} {cy}" '
              f'fill="none" stroke="#{T["RULE"]}" stroke-width="1.4"/>')
    s += (f'<line x1="{mx}" y1="{cy}" x2="{rx-6}" y2="{cy}" stroke="#{T["CON"]}" '
          f'stroke-width="1.6" stroke-dasharray="2 4" marker-end="url(#cv)"/>')
    s += (f'<rect x="{rx}" y="{ry}" width="{rw}" height="{rh}" rx="8" fill="#{T["RED"]}"/>'
          f'<text x="{rx+rw//2}" y="{cy+6}" font-family="{T["HEAD"]}" font-size="20" '
          f'font-weight="700" fill="#fff" text-anchor="middle">{end}</text>')
    return _doc(s, H, T)


def process_html(steps, T, H=320):
    """期間ラベル付きプロセス。steps=[(title,desc,conn)..] conn=次工程への矢印ラベル（最終は無視）。番号丸・最終=赤。"""
    n = max(1, len(steps)); cy = 96; r = 30
    x0, x1 = 90, 1190
    xs = [x0] if n == 1 else [x0 + i * ((x1 - x0) // (n - 1)) for i in range(n)]
    s = (f'<defs><marker id="pr" markerWidth="9" markerHeight="9" refX="6" refY="4.5" orient="auto">'
         f'<path d="M0,0 L9,4.5 L0,9 Z" fill="#{T["CON"]}"/></marker></defs>')
    for i in range(n - 1):
        xa, xb = xs[i] + r + 6, xs[i + 1] - r - 6
        s += (f'<line x1="{xa}" y1="{cy}" x2="{xb}" y2="{cy}" stroke="#{T["CON"]}" '
              f'stroke-width="1.5" marker-end="url(#pr)"/>')
        conn = (list(steps[i]) + ["", "", ""])[2]
        if conn:
            s += (f'<text x="{(xa+xb)//2}" y="{cy-12}" font-family="{T["MONO"]}" font-size="14" '
                  f'fill="#{T["SUB"]}" text-anchor="middle">{conn}</text>')
    for i, st in enumerate(steps):
        title, desc = (list(st) + ["", "", ""])[:2]
        x = xs[i]; last = (i == n - 1)
        s += (f'<circle cx="{x}" cy="{cy}" r="{r}" fill="{("#"+T["RED"]) if last else "#fff"}" '
              f'stroke="#{T["RED"] if last else T["BORDER"]}" stroke-width="{1.8 if last else 1.4}"/>'
              f'<text x="{x}" y="{cy+6}" font-family="{T["MONO"]}" font-size="17" font-weight="500" '
              f'fill="{"#fff" if last else "#"+T["INK"]}" text-anchor="middle">{i+1:02d}</text>')
        s += (f'<text x="{x}" y="{cy+r+34}" font-family="{T["HEAD"]}" font-size="17" font-weight="700" '
              f'fill="#{T["RED"] if last else T["INK"]}" text-anchor="middle">{title}</text>')
        if desc:
            s += (f'<text x="{x}" y="{cy+r+60}" font-family="{T["BODY"]}" font-size="13" '
                  f'fill="#{T["SUB"]}" text-anchor="middle"><tspan x="{x}" dy="0">{desc[:13]}</tspan>'
                  f'<tspan x="{x}" dy="18">{desc[13:26]}</tspan></text>')
    return _doc(s, H, T)


def gridmatrix_html(cols, rows, cells, T, H=420):
    """カテゴリ網羅グリッド。cols=列ヘッダ[]、rows=行ヘッダ[]、cells=行×列の2D（str/[..]/'' 空＝未対応）。"""
    nc = max(1, len(cols)); nr = max(1, len(rows))
    hx, hw = 24, 150
    gx = hx + hw + 8
    gy, th = 18, 44
    gw = 1280 - gx - 24
    gh = H - (gy + th) - 16
    cw = gw // nc; ch = gh // nr
    s = ""
    for c in range(nc):
        s += (f'<text x="{gx + c*cw + cw//2}" y="{gy+28}" font-family="{T["HEAD"]}" font-size="16" '
              f'font-weight="700" fill="#{T["RED"]}" text-anchor="middle">{cols[c]}</text>')
    for rr in range(nr):
        ry = gy + th + rr * ch
        s += (f'<text x="{hx+4}" y="{ry+ch//2+6}" font-family="{T["HEAD"]}" font-size="16" '
              f'font-weight="700" fill="#{T["INK"]}">{rows[rr]}</text>')
        for c in range(nc):
            cxp = gx + c * cw
            val = cells[rr][c] if (rr < len(cells) and c < len(cells[rr])) else ""
            filled = bool(val)
            s += (f'<rect x="{cxp+4}" y="{ry+4}" width="{cw-8}" height="{ch-8}" rx="8" '
                  f'fill="{"#fff" if filled else "#"+T["PANEL"]}" '
                  f'stroke="#{T["RULE"] if filled else T["PANEL"]}" stroke-width="1"/>')
            if filled:
                items = list(val) if isinstance(val, (list, tuple)) else [val]
                items = items[:3]
                for k, it in enumerate(items):
                    yy = ry + ch // 2 - (len(items) - 1) * 11 + k * 22 + 5
                    s += (f'<text x="{cxp+cw//2}" y="{yy}" font-family="{T["BODY"]}" font-size="14" '
                          f'fill="#{T["INK"]}" text-anchor="middle">{it}</text>')
            else:
                s += (f'<text x="{cxp+cw//2}" y="{ry+ch//2+5}" font-family="{T["BODY"]}" font-size="15" '
                      f'fill="#{T["FAINT"]}" text-anchor="middle">–</text>')
    return _doc(s, H, T)


def directions_html(origin, items, T, H=430):
    """方向図：起点(赤ドット)から複数方向へ矢印→右に説明チップを縦整列。
    origin=起点ラベル、items=[(tag, desc, accent_bool)]（縦/横/斜め・成長/拡張の方向など）。accent=赤。"""
    ox, oy = 170, H // 2
    chip_x = 720; chip_w = 1280 - chip_x - 56
    n = max(1, len(items[:4])); chh = 92
    gap = (H - 80) // n
    s = (f'<defs>'
         f'<marker id="dr" markerWidth="10" markerHeight="10" refX="7" refY="5" orient="auto">'
         f'<path d="M0,0 L10,5 L0,10 Z" fill="#{T["CON"]}"/></marker>'
         f'<marker id="drr" markerWidth="10" markerHeight="10" refX="7" refY="5" orient="auto">'
         f'<path d="M0,0 L10,5 L0,10 Z" fill="#{T["RED"]}"/></marker></defs>')
    for i, it in enumerate(items[:4]):
        tag, desc, acc = (list(it) + ["", "", False])[:3]
        cy = 40 + chh // 2 + i * gap
        mk = "drr" if acc else "dr"
        col = T["RED"] if acc else T["CON"]
        s += (f'<line x1="{ox+12}" y1="{oy}" x2="{chip_x-8}" y2="{cy}" stroke="#{col}" '
              f'stroke-width="{2 if acc else 1.5}" marker-end="url(#{mk})"/>')
        s += (f'<rect x="{chip_x}" y="{cy-chh//2}" width="{chip_w}" height="{chh}" rx="8" '
              f'fill="#fff" stroke="#{T["RED"] if acc else T["BORDER"]}" stroke-width="{1.6 if acc else 1}"/>')
        s += (f'<text x="{chip_x+28}" y="{cy-6}" font-family="{T["HEAD"]}" font-size="22" '
              f'font-weight="700" fill="#{T["RED"] if acc else T["INK"]}">{tag}</text>')
        s += (f'<text x="{chip_x+28}" y="{cy+22}" font-family="{T["BODY"]}" font-size="15" fill="#{T["SUB"]}">'
              f'<tspan x="{chip_x+28}" dy="0">{desc[:24]}</tspan>'
              f'<tspan x="{chip_x+28}" dy="20">{desc[24:48]}</tspan></text>')
    s += (f'<circle cx="{ox}" cy="{oy}" r="11" fill="#{T["RED"]}"/>'
          f'<text x="{ox}" y="{oy+40}" font-family="{T["HEAD"]}" font-size="16" font-weight="700" '
          f'fill="#{T["INK"]}" text-anchor="middle">{origin}</text>')
    return _doc(s, H, T)
