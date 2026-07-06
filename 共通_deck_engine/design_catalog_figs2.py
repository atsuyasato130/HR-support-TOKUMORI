#!/usr/bin/env python3
"""② 図解カタログ拡張＝F51-F80（+30パターン）。トンマナは figs1 と同一（温白×墨×赤・palt・Lato数字）。"""
import os
import math
import warnings

warnings.filterwarnings("ignore")
import html_to_slide as H

INK = "#15171C"; PAPER = "#FBFAF9"; RED = "#AF322C"; GRAY = "#8A8F98"
NEU = "#DCD9D4"; NEU2 = "#EDEBE7"; HL = "rgba(21,23,28,0.14)"
FONT = ('<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700;900'
        '&family=Lato:wght@400;700;900&display=swap" rel="stylesheet"/>')
BASE = ('*{margin:0;padding:0;box-sizing:border-box;}html,body{width:1280px;height:720px;overflow:hidden;}'
        'body{font-family:"Noto Sans JP",sans-serif;background:%s;color:%s;-webkit-font-smoothing:antialiased;}'
        '.jp{font-feature-settings:"palt";}.en{font-family:Lato,sans-serif;letter-spacing:.14em;text-transform:uppercase;}'
        '.num{font-family:Lato,sans-serif;}' % (PAPER, INK))

FIGS = []


def slide(num, cat, name, inner):
    return ('<!DOCTYPE html><html><head><meta charset="utf-8"/>' + FONT + f'<style>{BASE}</style></head><body>'
            f'<div style="position:relative;width:1280px;height:720px;padding:48px 72px;">'
            f'<div style="display:flex;align-items:center;gap:10px;">'
            f'<div class="en" style="font-size:12px;color:{RED};font-weight:900;">F{num:02d}</div>'
            f'<div style="width:1px;height:12px;background:{HL};"></div>'
            f'<div class="en" style="font-size:11px;color:{GRAY};">{cat}</div></div>'
            f'<div class="jp" style="font-size:26px;font-weight:900;margin-top:10px;">{name}</div>'
            f'<div style="position:absolute;left:72px;top:170px;width:1136px;height:470px;">{inner}</div>'
            f'</div></body></html>')


def add(cat, name, inner):
    FIGS.append((len(FIGS) + 51, cat, name, inner))


# ============ J. アイコン・特徴 ============
add("Icons ／ 特徴", "特徴3カラム（記号見出し）",
    f'<div style="display:flex;gap:60px;padding-top:44px;">' +
    "".join(f'<div style="flex:1;">'
            f'<div class="num" style="width:54px;height:54px;background:{RED if hi else INK};color:#fff;display:flex;'
            f'align-items:center;justify-content:center;font-size:22px;font-weight:900;">{m}</div>'
            f'<div class="jp" style="font-size:18px;font-weight:900;margin-top:20px;">{t}</div>'
            f'<div class="jp" style="font-size:14px;color:#5F6570;line-height:1.9;margin-top:12px;">{d}</div></div>'
            for m, t, d, hi in [("戦", "戦略を、科学で。", "Sackett等の学術知見とデータで選考を設計。勘に頼らない。", 0),
                                ("実", "実働まで、全部。", "スカウト・日程・面談。頭数でなく設計ごと代行する。", 1),
                                ("型", "型を、残す。", "FMTと運用設計を納品。抜けた後も回る仕組みに。", 0)]) + '</div>')

add("Icons ／ 特徴", "チェックリスト2列",
    f'<div style="display:flex;gap:80px;padding-top:36px;">' +
    "".join(f'<div style="flex:1;">' +
            "".join(f'<div style="display:flex;gap:16px;align-items:flex-start;border-bottom:1px solid {HL};padding:17px 0;">'
                    f'<div class="num" style="width:26px;height:26px;border-radius:50%;background:{RED};color:#fff;'
                    f'display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:900;flex:none;">✓</div>'
                    f'<div class="jp" style="font-size:15px;font-weight:700;padding-top:2px;">{t}</div></div>' for t in col) + '</div>'
            for col in [["採用戦略・ペルソナ設計", "スカウト文面のA/Bテスト", "媒体・エージェント活性化", "構造化面接の導入支援"],
                        ["日程調整・進行管理の代行", "承諾率を上げるクロージング", "週次KPIレポーティング", "自走用FMTの納品"]]) + '</div>')

add("Icons ／ 特徴", "ピクトグラム人型（比率）",
    f'<div style="padding-top:40px;"><div style="display:flex;gap:18px;">' +
    "".join(f'<svg width="64" height="150" viewBox="0 0 40 96"><circle cx="20" cy="14" r="11" fill="{RED if i<5 else NEU}"/>'
            f'<path d="M6,36 Q20,26 34,36 L34,66 L28,66 L28,94 L12,94 L12,66 L6,66 Z" fill="{RED if i<5 else NEU}"/></svg>'
            for i in range(10)) +
    f'</div><div class="jp" style="margin-top:34px;font-size:17px;font-weight:700;">中途入社の <span class="num" style="font-size:34px;font-weight:900;color:{RED};">47%</span> が「入社6ヶ月以内」に離職を検討'
    f'<span style="font-size:13px;color:{GRAY};font-weight:400;">　出典: en調査 2026</span></div></div>')

add("Icons ／ 特徴", "チップ群（対応領域）",
    f'<div style="padding-top:40px;line-height:3.2;">' +
    "".join(f'<span class="jp" style="display:inline-block;padding:12px 24px;font-size:15px;font-weight:700;margin:0 12px 12px 0;'
            + (f'background:{RED};color:#fff;' if hi else f'background:transparent;color:{INK};border:1.5px solid {NEU};')
            + f'">{t}</span>'
            for t, hi in [("ダイレクトスカウト", 1), ("媒体運用", 0), ("エージェント管理", 0), ("求人票制作", 0),
                          ("採用広報", 0), ("構造化面接", 1), ("日程調整", 0), ("内定者フォロー", 0),
                          ("クロージング", 1), ("採用ブランディング", 0), ("AI効率化", 0), ("FMT型化", 0)]) +
    f'<div class="jp" style="font-size:13px;color:{GRAY};margin-top:16px;">赤=特に強みのある領域</div></div>')

add("Icons ／ 特徴", "実績バッジ帯",
    f'<div style="display:flex;gap:1px;background:{HL};margin-top:60px;border:1px solid {HL};">' +
    "".join(f'<div style="flex:1;background:{PAPER};padding:36px 20px;text-align:center;">'
            f'<div class="en" style="font-size:10.5px;color:{RED};font-weight:700;">{e}</div>'
            f'<div class="jp" style="font-size:17px;font-weight:900;margin-top:10px;line-height:1.5;">{t}</div>'
            f'<div class="jp" style="font-size:12.5px;color:{GRAY};margin-top:8px;">{d}</div></div>'
            for e, t, d in [("Award", "経産省・横浜市<br>ビジコン受賞", "行政からの評価"), ("Clients", "取引300社", "業界・規模を問わず"),
                            ("Growth", "5期連続増収", "6期目・成長企業"), ("Reach", "SNS 25万人", "自社メディア網")]) + '</div>')

# ============ K. テキスト構成 ============
add("Text ／ 構成", "アジェンダ（目次）",
    f'<div style="padding-top:30px;width:860px;">' +
    "".join(f'<div style="display:flex;align-items:baseline;border-bottom:1px solid {HL};padding:20px 0;">'
            f'<div class="num" style="width:80px;font-size:24px;font-weight:900;color:{RED if hi else NEU};">{i:02d}</div>'
            f'<div class="jp" style="font-size:19px;font-weight:{900 if hi else 700};color:{INK if hi else "#4A4F57"};">{t}</div>'
            f'<div style="flex:1;"></div><div class="num" style="font-size:14px;color:{GRAY};">P.{p}</div></div>'
            for i, t, p, hi in [(1, "採用市場の構造変化", "03", 0), (2, "一般的な採用の限界", "07", 0),
                                (3, "とくもり採用代行のメソッド", "11", 1), (4, "サービス範囲とROI", "15", 0), (5, "導入プロセス", "20", 0)]) + '</div>')

add("Text ／ 構成", "引用・推薦コメント",
    f'<div style="padding:50px 60px 0;">'
    f'<div class="num" style="font-size:120px;font-weight:900;color:{RED};line-height:.6;">“</div>'
    f'<div class="jp" style="font-size:26px;font-weight:700;line-height:1.9;margin-top:10px;width:960px;">'
    f'採用を「お願いする」相手ではなく、<br>一緒に構造を作り直してくれるチームだった。</div>'
    f'<div style="display:flex;align-items:center;gap:18px;margin-top:36px;">'
    f'<div style="width:44px;height:1.5px;background:{RED};"></div>'
    f'<div class="jp" style="font-size:14px;color:{GRAY};">製造業（従業員120名）・人事責任者　※導入8ヶ月</div></div></div>')

add("Text ／ 構成", "FAQ 2列",
    f'<div style="display:grid;grid-template-columns:1fr 1fr;grid-gap:20px 56px;padding-top:30px;">' +
    "".join(f'<div style="border-top:2px solid {RED if i==0 else NEU};padding-top:16px;">'
            f'<div class="jp" style="font-size:15px;font-weight:900;"><span class="num" style="color:{RED};">Q.</span>　{q}</div>'
            f'<div class="jp" style="font-size:13.5px;color:#5F6570;line-height:1.8;margin-top:10px;"><span class="num" style="font-weight:900;">A.</span>　{a}</div></div>'
            for i, (q, a) in enumerate([("最低契約期間は？", "6ヶ月です（アドバイザリーのみ3ヶ月固定）。採用は仕組み化に時間を要するためです。"),
                                        ("何名体制で入りますか？", "専任PM＋実働チームの2〜4名。窓口はPMに一本化します。"),
                                        ("面接の合否も任せられる？", "合否判断は必ず貴社にお願いしています。判断材料の設計と整理は当社が行います。"),
                                        ("途中でプラン変更できる？", "可能です。月次で稼働をレビューし、翌月から変更できます。")])) + '</div>')

add("Text ／ 構成", "課題→原因→打ち手",
    f'<div style="display:flex;align-items:stretch;gap:0;padding-top:44px;">' +
    "".join((f'<div style="flex:1;border:1.5px solid {c};padding:28px;{extra}">'
             f'<div class="en" style="font-size:11px;font-weight:700;color:{c2};">{e}</div>'
             f'<div class="jp" style="font-size:17px;font-weight:900;margin-top:12px;color:{tc};">{t}</div>'
             f'<div class="jp" style="font-size:13.5px;margin-top:10px;line-height:1.8;color:{dc};">{d}</div></div>'
             + (f'<svg width="44" height="180" style="align-self:center;flex:none;"><line x1="4" y1="90" x2="32" y2="90" stroke="{GRAY}" stroke-width="2"/><path d="M32,82 L44,90 L32,98Z" fill="{GRAY}"/></svg>' if i < 2 else ""))
            for i, (e, t, d, c, c2, tc, dc, extra) in enumerate([
                ("Problem", "応募が来ない", "媒体掲載も紹介依頼も、待つだけでは母集団が形成できない。", NEU, GRAY, INK, "#5F6570", ""),
                ("Cause", "「攻め」の設計不在", "スカウト・タゲ設計・訴求の仮説検証が回っていない。", NEU, GRAY, INK, "#5F6570", ""),
                ("Solution", "実働ごと代行", "設計×実働×週次改善をワンチームで回し、母集団を資産化。", RED, "#E5B4B0", "#fff", "rgba(255,255,255,.85)", f"background:{RED};")])) + '</div>')

add("Text ／ 構成", "定義カード（用語）",
    f'<div style="padding-top:40px;width:900px;">'
    f'<div style="display:flex;align-items:baseline;gap:22px;">'
    f'<div class="en" style="font-size:34px;font-weight:900;">RPO</div>'
    f'<div class="jp" style="font-size:13.5px;color:{GRAY};">Recruitment Process Outsourcing</div></div>'
    f'<div style="width:56px;height:3px;background:{RED};margin:20px 0;"></div>'
    f'<div class="jp" style="font-size:17px;line-height:2.1;color:#3A3F47;">採用業務の一部または全部を、外部の専門チームが代行すること。'
    f'単なる事務代行ではなく、<b style="color:{INK};">戦略設計から実働・改善まで</b>を一気通貫で担う形が成果に直結する。</div>'
    f'<div class="jp" style="font-size:13px;color:{GRAY};margin-top:18px;">類義: 採用代行 ／ 対比: 人材紹介（成果報酬・紹介のみ）</div></div>')

add("Text ／ 構成", "沿革タイムライン（縦）",
    f'<div style="padding:20px 0 0 60px;position:relative;">'
    f'<div style="position:absolute;left:71px;top:30px;bottom:10px;width:2px;background:{NEU};"></div>' +
    "".join(f'<div style="display:flex;align-items:flex-start;gap:34px;margin-bottom:26px;position:relative;">'
            f'<div class="num" style="width:70px;text-align:right;font-size:16px;font-weight:900;color:{RED if hi else GRAY};padding-top:2px;">{y}</div>'
            f'<div style="width:14px;height:14px;border-radius:50%;background:{RED if hi else PAPER};border:2.5px solid {RED if hi else NEU};margin-top:5px;flex:none;"></div>'
            f'<div class="jp"><b style="font-size:15.5px;">{t}</b><div style="font-size:13px;color:{GRAY};margin-top:4px;">{d}</div></div></div>'
            for y, t, d, hi in [("2021", "創業", "人材紹介事業からスタート", 0), ("2023", "採用代行（RPO）開始", "紹介で見えた「企業側の構造課題」へ", 0),
                                ("2024", "経産省・横浜市ビジコン受賞", "採用×データの事業モデルが評価", 0),
                                ("2025", "取引300社を突破", "業界・地域を問わず横展開", 0), ("2026", "AI×学術の採用OSへ", "とくもり採用代行として体系化", 1)]) + '</div>')

# ============ L. データ応用 ============
add("Data ／ 応用", "ダンベル（2時点差分）",
    '<div style="padding-top:44px;">' +
    "".join(f'<div style="display:flex;align-items:center;margin-bottom:34px;">'
            f'<div class="jp" style="width:190px;font-size:14.5px;font-weight:700;">{l}</div>'
            f'<div style="flex:1;position:relative;height:22px;">'
            f'<div style="position:absolute;left:{a}%;right:{100-b}%;top:9px;height:4px;background:{NEU};"></div>'
            f'<div style="position:absolute;left:{a}%;top:2px;width:18px;height:18px;border-radius:50%;background:{PAPER};border:3px solid {GRAY};margin-left:-9px;"></div>'
            f'<div style="position:absolute;left:{b}%;top:2px;width:18px;height:18px;border-radius:50%;background:{RED};margin-left:-9px;"></div>'
            f'<div class="num" style="position:absolute;left:{a}%;top:-26px;margin-left:-16px;font-size:13px;color:{GRAY};">{av}</div>'
            f'<div class="num" style="position:absolute;left:{b}%;top:28px;margin-left:-16px;font-size:14px;font-weight:900;color:{RED};">{bv}</div>'
            f'</div></div>'
            for l, a, b, av, bv in [("書類通過率", 30, 58, "34%", "61%"), ("面接設定率", 44, 68, "48%", "72%"), ("内定承諾率", 40, 78, "45%", "83%")]) +
    f'<div class="jp" style="font-size:12.5px;color:{GRAY};">○ 導入前 → <span style="color:{RED};">●</span> 導入後（6ヶ月）</div></div>')

add("Data ／ 応用", "ドットプロット（分布）",
    f'<div style="padding-top:50px;">' +
    "".join(f'<div style="display:flex;align-items:center;margin-bottom:36px;">'
            f'<div class="jp" style="width:190px;font-size:14.5px;font-weight:700;">{l}</div>'
            f'<div style="flex:1;position:relative;height:20px;border-bottom:1px solid {NEU};">' +
            "".join(f'<div style="position:absolute;left:{x}%;top:4px;width:12px;height:12px;border-radius:50%;background:{NEU};opacity:.8;"></div>' for x in xs) +
            f'<div style="position:absolute;left:{me}%;top:0;width:20px;height:20px;border-radius:50%;background:{RED};margin-left:-4px;"></div>'
            f'</div></div>'
            for l, xs, me in [("業界平均帯", [12, 18, 25, 31, 38, 44], 45), ("一般RPO帯", [30, 36, 42, 50, 55], 52), ("とくもり事例", [58, 64, 70], 83)]) +
    f'<div class="jp" style="font-size:12.5px;color:{GRAY};">内定承諾率の分布（●=代表値）。とくもり事例は n が小さい点に留意。</div></div>')


def radar_svg():
    cx, cy, r = 230, 210, 160
    axes = ["戦略", "実働", "学術", "速度", "価格"]
    def pt(i, k):
        a = -math.pi / 2 + i * 2 * math.pi / 5
        return (cx + r * k * math.cos(a), cy + r * k * math.sin(a))
    grid = ""
    for k in (0.33, 0.66, 1.0):
        pts = " ".join(f"{x:.0f},{y:.0f}" for x, y in (pt(i, k) for i in range(5)))
        grid += f'<polygon points="{pts}" fill="none" stroke="{NEU}" stroke-width="1"/>'
    for i in range(5):
        x, y = pt(i, 1.0)
        grid += f'<line x1="{cx}" y1="{cy}" x2="{x:.0f}" y2="{y:.0f}" stroke="{NEU}" stroke-width="1"/>'
        lx, ly = pt(i, 1.22)
        grid += f'<text x="{lx:.0f}" y="{ly:.0f}" font-size="14" font-weight="700" fill="{INK}" text-anchor="middle" font-family="Noto Sans JP">{axes[i]}</text>'
    ours = [1.0, 0.95, 1.0, 0.8, 0.75]; them = [0.45, 0.75, 0.3, 0.6, 0.65]
    p1 = " ".join(f"{x:.0f},{y:.0f}" for x, y in (pt(i, ours[i]) for i in range(5)))
    p2 = " ".join(f"{x:.0f},{y:.0f}" for x, y in (pt(i, them[i]) for i in range(5)))
    return (f'<svg width="470" height="430">{grid}'
            f'<polygon points="{p2}" fill="rgba(21,23,28,.08)" stroke="{GRAY}" stroke-width="1.5"/>'
            f'<polygon points="{p1}" fill="rgba(175,50,44,.14)" stroke="{RED}" stroke-width="2.5"/></svg>')


add("Data ／ 応用", "レーダー（5軸比較）",
    f'<div style="display:flex;align-items:center;gap:60px;padding-top:6px;">{radar_svg()}'
    f'<div class="jp" style="font-size:14.5px;line-height:2.4;color:#3A3F47;">'
    f'<span style="color:{RED};font-weight:900;">■ とくもり採用代行</span><br><span style="color:{GRAY};">■ 一般的なRPO</span><br><br>'
    f'戦略・学術で差が最大。<br>実働は同水準以上、価格は中位。</div></div>')

add("Data ／ 応用", "積み上げエリア（構成推移）",
    f'<div style="padding-top:24px;"><svg width="1000" height="330">'
    f'<polygon points="60,290 60,240 295,225 530,190 765,150 1000,90 1000,290" fill="{RED}" opacity=".85"/>'
    f'<polygon points="60,240 295,225 530,190 765,150 1000,90 1000,40 765,95 530,140 295,190 60,215" fill="{NEU}"/>'
    f'<polygon points="60,215 295,190 530,140 765,95 1000,40 1000,15 765,70 530,115 295,170 60,200" fill="{NEU2}"/>'
    f'<line x1="60" y1="290" x2="1000" y2="290" stroke="{INK}" stroke-opacity=".25"/></svg>'
    f'<div style="display:flex;justify-content:space-between;width:1000px;padding:6px 40px 0 40px;" class="num">' +
    "".join(f'<div style="font-size:13px;color:{GRAY};">{q}</div>' for q in ["24Q3", "24Q4", "25Q1", "25Q2", "25Q3"]) +
    f'</div><div class="jp" style="margin-top:12px;font-size:13px;color:{GRAY};"><span style="color:{RED};">■</span> スカウト経由　■ 媒体　<span style="color:#C9C6C0;">■</span> その他 — スカウト比率が主力チャネルに</div></div>')

add("Data ／ 応用", "コホート表（残存率）",
    f'<div style="padding-top:26px;"><div style="display:flex;padding-left:170px;" class="jp">' +
    "".join(f'<div style="width:150px;text-align:center;font-size:13px;color:{GRAY};font-weight:700;padding-bottom:8px;">{m}</div>' for m in ["入社時", "3ヶ月", "6ヶ月", "12ヶ月"]) + '</div>' +
    "".join(f'<div style="display:flex;align-items:center;margin-bottom:5px;">'
            f'<div class="jp" style="width:170px;font-size:13.5px;font-weight:700;">{l}</div>' +
            "".join((f'<div style="width:150px;height:56px;margin-right:5px;background:rgba(175,50,44,{v/130:.2f});'
                     f'display:flex;align-items:center;justify-content:center;">'
                     f'<span class="num" style="font-size:15px;font-weight:700;color:{"#fff" if v>=75 else INK};">{v}%</span></div>') if v is not None else
                    f'<div style="width:150px;height:56px;margin-right:5px;background:rgba(21,23,28,.03);"></div>'
                    for v in row) + '</div>'
            for l, row in [("2024下期 入社", [100, 88, 76, 71]), ("2025上期 入社", [100, 94, 90, None]), ("2025下期 入社(支援後)", [100, 97, None, None])]) +
    f'<div class="jp" style="font-size:12.5px;color:{GRAY};margin-top:12px;">定着支援導入後のコホートで残存率が改善。</div></div>')

add("Data ／ 応用", "小型ゲージ×4",
    f'<div style="display:flex;gap:56px;padding-top:44px;justify-content:center;">' +
    "".join(f'<div style="text-align:center;">'
            f'<div style="position:relative;width:150px;height:150px;border-radius:50%;'
            f'background:conic-gradient({RED if hi else INK} 0deg {int(p*3.6)}deg, {NEU2} {int(p*3.6)}deg 360deg);">'
            f'<div style="position:absolute;inset:14px;border-radius:50%;background:{PAPER};display:flex;align-items:center;justify-content:center;">'
            f'<span class="num" style="font-size:32px;font-weight:900;color:{RED if hi else INK};">{p}<span style="font-size:16px;">%</span></span></div></div>'
            f'<div class="jp" style="font-size:13.5px;font-weight:700;margin-top:14px;">{l}</div></div>'
            for p, l, hi in [(94, "契約継続率", 1), (87, "PM即応率(当日)", 0), (76, "書類通過率", 0), (61, "面談転換率", 0)]) + '</div>')

add("Data ／ 応用", "スコアボード（順位表）",
    f'<div style="margin-top:26px;border-top:2px solid {INK};">' +
    "".join(f'<div style="display:flex;align-items:center;border-bottom:1px solid {HL};{"background:rgba(175,50,44,.06);" if hi else ""}">'
            f'<div class="num" style="width:70px;padding:16px 0;text-align:center;font-size:20px;font-weight:900;color:{RED if hi else GRAY};">{r}</div>'
            f'<div class="jp" style="flex:2;font-size:15px;font-weight:{900 if hi else 700};">{l}</div>'
            f'<div class="num" style="flex:1;text-align:right;font-size:15px;font-weight:700;padding-right:24px;">{v}</div>'
            f'<div class="num" style="width:110px;text-align:right;font-size:13.5px;color:{RED if "+" in d else GRAY};padding-right:10px;">{d}</div></div>'
            for r, l, v, d, hi in [(1, "ダイレクトスカウト", "324名", "+118%", 1), (2, "求人媒体（5社計）", "218名", "+42%", 0),
                                   (3, "リファラル", "96名", "+88%", 0), (4, "人材紹介", "68名", "−12%", 0), (5, "SNS・オウンド", "36名", "+9%", 0)]) +
    f'<div class="jp" style="font-size:12.5px;color:{GRAY};padding-top:12px;">チャネル別 年間母集団と前年比。</div></div>')

# ============ M. 戦略フレーム ============
add("Frame ／ 戦略", "SWOT 2×2",
    f'<div style="display:grid;grid-template-columns:1fr 1fr;grid-gap:14px;padding-top:20px;">' +
    "".join(f'<div style="border-top:3px solid {c};background:rgba(21,23,28,.025);padding:22px 26px;min-height:190px;">'
            f'<div style="display:flex;align-items:baseline;gap:12px;"><div class="en" style="font-size:22px;font-weight:900;color:{c};">{e}</div>'
            f'<div class="jp" style="font-size:13.5px;font-weight:700;color:{GRAY};">{jp}</div></div>'
            f'<div class="jp" style="font-size:13.5px;line-height:1.9;margin-top:12px;color:#3A3F47;">{b}</div></div>'
            for e, jp, b, c in [("S", "強み", "・現場で戦える商品力<br>・経営陣の営業力", INK), ("W", "弱み", "・採用の専任者が不在<br>・選考が属人化", GRAY),
                                ("O", "機会", "・競合の採用も鈍化<br>・地方人材の流動化", RED), ("T", "脅威", "・大手の給与レンジ上昇<br>・応募単価の高騰", GRAY)]) + '</div>')

add("Frame ／ 戦略", "3C（円3つ）",
    f'<div style="position:relative;width:760px;height:430px;margin:0 auto;">' +
    "".join(f'<div style="position:absolute;{pos};width:290px;height:290px;border-radius:50%;background:{bg};border:1.5px solid {bd};'
            f'display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;">'
            f'<div class="en" style="font-size:13px;font-weight:900;color:{c2};">{e}</div>'
            f'<div class="jp" style="font-size:16px;font-weight:900;margin-top:6px;color:{tc};">{t}</div>'
            f'<div class="jp" style="font-size:12.5px;color:{dc};margin-top:8px;line-height:1.7;">{d}</div></div>'
            for e, t, d, pos, bg, bd, c2, tc, dc in [
                ("Customer", "候補者", "何を基準に<br>会社を選ぶか", "left:235px;top:0", "rgba(21,23,28,.04)", NEU, GRAY, INK, GRAY),
                ("Competitor", "競合", "同職種の<br>給与・訴求", "left:60px;top:150px", "rgba(21,23,28,.04)", NEU, GRAY, INK, GRAY),
                ("Company", "自社", "選ばれる理由の<br>再設計", "left:410px;top:150px", "rgba(175,50,44,.08)", RED, RED, RED, "#8A5450")]) + '</div>')

add("Frame ／ 戦略", "ロードマップ（3ホライズン）",
    f'<div style="display:flex;gap:26px;align-items:flex-end;padding-top:36px;">' +
    "".join(f'<div style="flex:1;">'
            f'<div style="background:{c};color:{tc};padding:24px;height:{h}px;display:flex;flex-direction:column;justify-content:flex-end;">'
            f'<div class="en" style="font-size:11px;font-weight:700;opacity:.7;">{e}</div>'
            f'<div class="jp" style="font-size:17px;font-weight:900;margin-top:6px;">{t}</div>'
            f'<div class="jp" style="font-size:13px;margin-top:8px;opacity:.85;line-height:1.7;">{d}</div></div>'
            f'<div class="num jp" style="text-align:center;font-size:13px;color:{GRAY};padding-top:12px;">{q}</div></div>'
            for e, t, d, q, h, c, tc in [
                ("Horizon 1", "止血と土台", "母集団の再建・選考の構造化", "〜3ヶ月", 190, NEU2, INK),
                ("Horizon 2", "伸ばす", "承諾率改善・チャネル最適化", "4〜9ヶ月", 260, NEU, INK),
                ("Horizon 3", "自走する", "FMT納品・社内移管・内製化", "10〜12ヶ月", 330, RED, "#fff")]) + '</div>')

add("Frame ／ 戦略", "ジャーニー（感情曲線）",
    f'<div style="padding-top:16px;"><svg width="1080" height="300">'
    f'<line x1="40" y1="150" x2="1040" y2="150" stroke="{NEU}" stroke-dasharray="5,5"/>'
    f'<path d="M40,170 C160,120 240,90 340,110 C440,130 500,230 620,240 C740,250 800,140 900,90 C960,60 1000,55 1040,50" fill="none" stroke="{RED}" stroke-width="3.5"/>'
    f'<circle cx="620" cy="240" r="9" fill="{INK}"/><circle cx="1040" cy="50" r="9" fill="{RED}"/>'
    f'<text x="620" y="278" font-size="13.5" font-family="Noto Sans JP" font-weight="700" fill="{INK}" text-anchor="middle">選考連絡が遅く感情が底に</text>'
    f'<text x="1000" y="34" font-size="13.5" font-family="Noto Sans JP" font-weight="700" fill="{RED}" text-anchor="end">オファー面談で最高点</text></svg>'
    f'<div style="display:flex;justify-content:space-between;width:1000px;padding:4px 40px 0;" class="jp">' +
    "".join(f'<div style="font-size:13px;color:{GRAY};">{s}</div>' for s in ["認知", "応募", "一次面接", "選考中", "最終", "オファー"]) + '</div></div>')

add("Frame ／ 戦略", "RACI（役割分担）",
    f'<div style="margin-top:28px;border-top:2px solid {INK};">'
    f'<div style="display:flex;border-bottom:1.5px solid {INK};" class="jp">'
    f'<div style="flex:2.2;padding:12px 8px;font-size:13px;font-weight:900;color:{GRAY};">タスク</div>' +
    "".join(f'<div style="flex:1;padding:12px 0;text-align:center;font-size:13px;font-weight:900;color:{GRAY};">{h}</div>' for h in ["とくもり", "貴社人事", "現場"]) + '</div>' +
    "".join(f'<div style="display:flex;border-bottom:1px solid {HL};align-items:center;">'
            f'<div class="jp" style="flex:2.2;padding:14px 8px;font-size:14px;font-weight:700;">{t}</div>' +
            "".join(f'<div style="flex:1;text-align:center;">'
                    f'<span class="en" style="display:inline-block;width:34px;height:34px;line-height:34px;font-size:14px;font-weight:900;'
                    + (f'background:{RED};color:#fff;' if v == "R" else (f'border:1.5px solid {INK};color:{INK};' if v == "A" else f'color:{GRAY};'))
                    + f'">{v}</span></div>' for v in row) + '</div>'
            for t, row in [("スカウト運用", ["R", "A", "I"]), ("求人票・訴求設計", ["R", "A", "C"]), ("一次面接", ["C", "R", "A"]), ("最終面接・合否", ["I", "A", "R"]), ("週次KPIレビュー", ["R", "A", "I"])]) +
    f'<div class="jp" style="font-size:12px;color:{GRAY};padding-top:10px;">R=実行　A=承認　C=相談　I=共有</div></div>')

add("Frame ／ 戦略", "フライホイール",
    f'<div style="position:relative;width:430px;height:430px;margin:0 auto;">'
    f'<svg width="430" height="430" style="position:absolute;">'
    f'<circle cx="215" cy="215" r="150" fill="none" stroke="{NEU}" stroke-width="2"/>' +
    "".join(f'<path d="M {215+150*math.cos(a):.0f},{215+150*math.sin(a):.0f} l {14*math.cos(a+2.2):.0f},{14*math.sin(a+2.2):.0f} M {215+150*math.cos(a):.0f},{215+150*math.sin(a):.0f} l {14*math.cos(a+4.1):.0f},{14*math.sin(a+4.1):.0f}" stroke="{GRAY}" stroke-width="2" fill="none"/>'
            for a in (0.5, 2.6, 4.7)) + '</svg>'
    f'<div style="position:absolute;inset:150px;border-radius:50%;background:{RED};display:flex;align-items:center;justify-content:center;text-align:center;">'
    f'<span class="jp" style="color:#fff;font-size:14px;font-weight:900;">採用が<br>回る構造</span></div>' +
    "".join(f'<div style="position:absolute;{pos};width:170px;text-align:center;" class="jp">'
            f'<b style="font-size:14.5px;">{t}</b><div style="font-size:12px;color:{GRAY};margin-top:4px;">{d}</div></div>'
            for t, d, pos in [("母集団が増える", "スカウト×媒体の複線化", "left:130px;top:-8px"),
                              ("体験が良くなる", "CX設計・即レス運用", "right:-58px;top:250px"),
                              ("承諾・定着が増える", "評判が母集団に還流", "left:-58px;top:250px")]) + '</div>')

add("Frame ／ 戦略", "市場マップ（TAM/SAM/SOM）",
    f'<div style="display:flex;align-items:center;gap:70px;padding-top:10px;">'
    f'<div style="position:relative;width:430px;height:430px;">'
    f'<div style="position:absolute;left:0;bottom:0;width:430px;height:430px;border-radius:50%;background:rgba(21,23,28,.05);border:1px solid {NEU};"></div>'
    f'<div style="position:absolute;left:70px;bottom:0;width:290px;height:290px;border-radius:50%;background:rgba(21,23,28,.07);border:1px solid {NEU};"></div>'
    f'<div style="position:absolute;left:140px;bottom:0;width:150px;height:150px;border-radius:50%;background:{RED};display:flex;align-items:center;justify-content:center;">'
    f'<span class="en" style="color:#fff;font-weight:900;font-size:15px;">SOM</span></div>'
    f'<div class="en" style="position:absolute;left:200px;top:16px;font-size:13px;font-weight:900;color:{GRAY};">TAM</div>'
    f'<div class="en" style="position:absolute;left:200px;top:130px;font-size:13px;font-weight:900;color:{GRAY};">SAM</div></div>'
    f'<div class="jp" style="font-size:14.5px;line-height:2.5;color:#3A3F47;">'
    f'<b class="en">TAM</b>　国内 中途採用市場　<b class="num">1.2兆円</b><br>'
    f'<b class="en">SAM</b>　中小・RPO適合層　<b class="num">2,400億円</b><br>'
    f'<b class="en" style="color:{RED};">SOM</b>　<span style="color:{RED};font-weight:900;">3年目標シェア　<span class="num">36億円</span></span></div></div>')

# ============ N. ストーリー ============
add("Story ／ 物語", "課題ビッグテキスト（問い）",
    f'<div style="padding-top:70px;">'
    f'<div class="en" style="font-size:12px;color:{RED};font-weight:700;">The Question</div>'
    f'<div class="jp" style="font-size:44px;font-weight:900;line-height:1.7;margin-top:24px;">'
    f'「いい人が来ない」のは、<br>本当に<span style="border-bottom:5px solid {RED};padding-bottom:4px;">母集団のせい</span>でしょうか。</div>'
    f'<div class="jp" style="font-size:15px;color:{GRAY};margin-top:30px;">— 多くの場合、ボトルネックは選考の構造にあります。</div></div>')

add("Story ／ 物語", "対比ステートメント（NOT/BUT）",
    f'<div style="display:flex;gap:1px;background:{HL};margin-top:50px;">'
    f'<div style="flex:1;background:{PAPER};padding:44px;">'
    f'<div class="en" style="font-size:13px;font-weight:900;color:{GRAY};">Not</div>'
    f'<div class="jp" style="font-size:26px;font-weight:900;color:{GRAY};margin-top:16px;line-height:1.7;text-decoration:line-through;text-decoration-color:rgba(21,23,28,.3);">人手を貸す<br>アウトソーシング</div></div>'
    f'<div style="flex:1;background:{INK};padding:44px;">'
    f'<div class="en" style="font-size:13px;font-weight:900;color:#E5B4B0;">But</div>'
    f'<div class="jp" style="font-size:26px;font-weight:900;color:#fff;margin-top:16px;line-height:1.7;">採用の構造を<br>作り直すパートナー</div></div></div>')

add("Story ／ 物語", "3ステップ・ナラティブ",
    f'<div style="padding-top:24px;">' +
    "".join(f'<div style="display:flex;align-items:center;gap:36px;border-bottom:1px solid {HL};padding:22px 0;">'
            f'<div class="num" style="font-size:56px;font-weight:900;color:{RED if hi else NEU};width:90px;">{i}</div>'
            f'<div class="jp" style="width:270px;font-size:19px;font-weight:900;">{t}</div>'
            f'<div class="jp" style="flex:1;font-size:14px;color:#5F6570;line-height:1.8;">{d}</div></div>'
            for i, t, d, hi in [("1", "現状を数値で裸にする", "ファネル各段の転換率を可視化し、どこで落ちているかを特定。", 0),
                                ("2", "ボトルネックだけ直す", "全部やらない。効果が最大の1〜2箇所に実働を集中。", 1),
                                ("3", "回る仕組みを残す", "FMT・運用設計を納品し、内製で回る状態で卒業。", 0)]) + '</div>')

add("Story ／ 物語", "数式（A×B=C）",
    f'<div style="display:flex;align-items:center;justify-content:center;gap:34px;padding-top:80px;">'
    f'<div style="text-align:center;border:1.5px solid {NEU};padding:34px 40px;">'
    f'<div class="jp" style="font-size:18px;font-weight:900;">母集団の質×量</div><div class="jp" style="font-size:12.5px;color:{GRAY};margin-top:6px;">スカウト・媒体設計</div></div>'
    f'<div class="num" style="font-size:44px;font-weight:900;color:{GRAY};">×</div>'
    f'<div style="text-align:center;border:1.5px solid {NEU};padding:34px 40px;">'
    f'<div class="jp" style="font-size:18px;font-weight:900;">選考の転換率</div><div class="jp" style="font-size:12.5px;color:{GRAY};margin-top:6px;">構造化面接・CX</div></div>'
    f'<div class="num" style="font-size:44px;font-weight:900;color:{GRAY};">=</div>'
    f'<div style="text-align:center;background:{RED};padding:34px 46px;">'
    f'<div class="jp" style="font-size:20px;font-weight:900;color:#fff;">採用成功</div><div class="jp" style="font-size:12.5px;color:rgba(255,255,255,.8);margin-top:6px;">再現可能な構造</div></div></div>')

add("Story ／ 物語", "サマリー1枚（3ポイント＋帯）",
    f'<div style="padding-top:20px;">' +
    "".join(f'<div style="display:flex;gap:26px;align-items:baseline;padding:14px 0;">'
            f'<div class="num" style="font-size:15px;font-weight:900;color:{RED};width:40px;">0{i}</div>'
            f'<div class="jp" style="font-size:17px;font-weight:900;width:340px;">{t}</div>'
            f'<div class="jp" style="flex:1;font-size:13.5px;color:{GRAY};line-height:1.8;">{d}</div></div>'
            for i, t, d in [(1, "市場はもう戻らない", "中小の採用難易度は大企業の約26倍。「待ち」は構造的に不利。"),
                            (2, "打ち手は科学されている", "構造化面接0.42 vs 学歴0.10。何が効くかは既に分かっている。"),
                            (3, "実働ごと任せて、型を残す", "設計×実働×週次改善。6ヶ月で「回る構造」を納品する。")]) +
    f'<div style="margin-top:26px;background:{INK};padding:24px 34px;display:flex;justify-content:space-between;align-items:center;">'
    f'<div class="jp" style="color:#fff;font-size:17px;font-weight:900;">まずは30分、現状のKPIを一緒に見ませんか。</div>'
    f'<div class="en" style="color:#E5B4B0;font-size:12px;font-weight:700;">Book a Session →</div></div></div>')


def main():
    paths = []
    for num, cat, name, inner in FIGS:
        html = slide(num, cat, name, inner)
        p = "/tmp/figcat2_%02d.html" % num
        open(p, "w", encoding="utf-8").write(html)
        paths.append(p)
    print("figs:", len(paths))
    pid, url = H.insert_many(paths, title="TOKUMORI ｜ ② 図解カタログ拡張（F51-F80）",
                             slide_id=os.environ.get("SLIDE_ID"), dpi=3)
    print("FIG CATALOG 2:", url)


if __name__ == "__main__":
    main()
