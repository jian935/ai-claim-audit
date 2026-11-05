#!/usr/bin/env python3
"""Generate the README demo gif and its static poster frame.

    python scripts/make_demo.py

DEVELOPMENT-ONLY. Requires Pillow. This script is NOT part of the skill runtime:
audit_claims.py / run_evals.py / eval_extras.py / check_docs.py stay zero-dependency,
and CI never calls this file. Outputs are committed so nobody needs Pillow to
read the README.

The claim shown in the demo is deliberately fabricated; the gif says so in its
footer. No measured number from evals/ appears in the animation.
"""

from __future__ import annotations

import math
import shutil
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
PORTFOLIO = Path("E:/ps/交付文件/作品集/ai-claim-audit")

W, H = 960, 540
N_FRAMES = 24
FRAME_MS = 500  # 12 s loop, short enough for a README first screen

BG = (251, 252, 254)
CARD = (255, 255, 255)
LINE = (230, 235, 242)
INK = (31, 41, 55)
MUTED = (122, 130, 144)
ACCENT = (91, 110, 225)
ACCENT_SOFT = (238, 241, 253)
WARN = (180, 105, 95)
WARN_SOFT = (251, 241, 239)
GOOD = (63, 138, 114)
WHITE = (255, 255, 255)

FONT_DIR = Path("C:/Windows/Fonts")
REGULAR = FONT_DIR / "msyh.ttc"
BOLD = FONT_DIR / "msyhbd.ttc"
MONO = FONT_DIR / "consola.ttf"

CLAIM = "模型准确率达到 94%，下周上线。"
REWRITE = "在 <待补：n 条、来源、口径> 上测得 94%；该结果尚不能推广到线上流量。"
COMMAND_PREFIX = 'python scripts/audit_claims.py --text "'
STAGES = ["① 贴一句带数字的声明", "② 本地预检 · 确定性 6 项",
          "③ 审计表 · 这个数回答不了什么", "④ 给一句更弱的改写"]


@lru_cache(maxsize=None)
def f(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size)


def reveal(text: str, i: int, start: int, span: int) -> str:
    """Typewriter reveal between frames [start, start+span)."""
    if i < start:
        return ""
    if i >= start + span:
        return text
    return text[: max(1, math.ceil((i - start + 1) / span * len(text)))]


def skeleton(stage: int, final: bool) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    d.text((48, 20), "ai-claim-audit  ·  30s demo", font=f(REGULAR, 14), fill=MUTED)
    d.text((W - 48, 20), "jian935", font=f(MONO, 14), fill=ACCENT, anchor="ra")
    d.line([(48, 46), (W - 48, 46)], fill=LINE, width=1)

    d.text((48, 62), "审「已经写出去的数字」", font=f(BOLD, 29), fill=INK)
    d.text((48, 104), "贴一句声明，得到这个数回答不了哪些问题", font=f(REGULAR, 17), fill=MUTED)

    # Stage chips stay put so the eye does not jump between frames.
    x = 48
    for idx, label in enumerate(STAGES):
        on = idx == min(stage, 3)
        col = ACCENT if on else MUTED
        d.rounded_rectangle([x, 140, x + 12, 152], radius=3,
                            fill=col if on else LINE)
        d.text((x + 20, 137), label, font=f(REGULAR, 15), fill=col)
        x += 246

    # Static containers
    d.rounded_rectangle([48, 172, W - 48, 234], radius=10, fill=CARD, outline=LINE, width=1)
    d.rounded_rectangle([48, 288, W - 48, 404], radius=10, fill=CARD, outline=LINE, width=1)
    d.rounded_rectangle([48, 436, W - 48, 492], radius=10,
                        fill=ACCENT_SOFT if final else CARD, outline=LINE, width=1)

    d.line([(48, 508), (W - 48, 508)], fill=LINE, width=1)
    d.text((48, 516), "npx skills add jian935/ai-claim-audit",
           font=f(MONO, 14), fill=ACCENT if final else MUTED)
    d.text((W - 48, 516), "示例声明为编造 · 命中 ≠ 造假 · 只验证陈述出来的证据",
           font=f(REGULAR, 12), fill=MUTED, anchor="ra")
    return img


def make_frame(i: int) -> Image.Image:
    stage = 0 if i < 5 else 1 if i < 9 else 2 if i < 14 else 3 if i < 19 else 4
    final = i >= 19
    img = skeleton(stage, final)
    d = ImageDraw.Draw(img)

    # ① claim types in
    typed = reveal(CLAIM, i, 0, 5)
    if typed:
        d.text((66, 190), typed, font=f(REGULAR, 21), fill=INK)

    # ② local pre-check command
    if i >= 5:
        # Consolas has no CJK glyphs: split the shell (mono) from the Chinese
        # claim (YaHei) so the command never shows tofu blocks.
        mono, cjk = f(MONO, 15), f(REGULAR, 15)
        x = 48.0
        d.text((x, 248), COMMAND_PREFIX, font=mono, fill=MUTED)
        x += d.textlength(COMMAND_PREFIX, font=mono)
        d.text((x, 247), CLAIM, font=cjk, fill=MUTED)
        x += d.textlength(CLAIM, font=cjk)
        d.text((x, 248), '"', font=mono, fill=MUTED)
        if i >= 7:
            d.rounded_rectangle([48, 268, 236, 282], radius=4, fill=ACCENT_SOFT)
            d.text((58, 267), "零依赖 · 无网络 · 可复现", font=f(REGULAR, 12), fill=ACCENT)

    # ③ audit rows appear one by one; these are the real C01/C10 findings for
    # this exact sentence (see examples/audit_report.md, Q01).
    if i >= 9:
        draw_row(d, 300, "C01", "分母与样本量", "S2",
                 "分母是什么？在多少条上测的？", WARN)
    if i >= 11:
        draw_row(d, 350, "C10", "可复现性", "S3",
                 "陌生人拿到仓库，能跑出同一个数吗？", WARN)
    if i >= 13:
        d.text((W - 66, 380), "6 项语义裁决 → 强制核对清单",
               font=f(REGULAR, 13), fill=ACCENT, anchor="ra")

    # ④ weaker rewrite
    if i >= 14:
        d.text((66, 442), "更弱的改写", font=f(BOLD, 13), fill=ACCENT)
        text = reveal(REWRITE, i, 14, 5)
        if text:
            d.text((66, 462), text, font=f(REGULAR, 16), fill=INK)

    if final:
        # Draw the tick as lines: CJK fonts render U+2713 as an emoji-like box.
        d.ellipse([W - 84, 60, W - 60, 84], fill=GOOD)
        d.line([(W - 78, 72), (W - 74, 77), (W - 66, 66)],
               fill=WHITE, width=2, joint="curve")

    if i == 22:
        img = Image.blend(img, Image.new("RGB", (W, H), WHITE), 0.55)
    elif i == 23:
        img = Image.blend(img, Image.new("RGB", (W, H), WHITE), 0.9)
    return img


def draw_row(d: ImageDraw.ImageDraw, y: int, cid: str, name: str,
             sev: str, question: str, colour: tuple[int, int, int]) -> None:
    d.rounded_rectangle([66, y, 66 + 52, y + 26], radius=5, fill=WARN_SOFT)
    d.text((92, y + 3), cid, font=f(MONO, 15), fill=colour, anchor="ma")
    d.text((132, y + 3), name, font=f(BOLD, 16), fill=INK)
    d.rounded_rectangle([300, y + 2, 336, y + 24], radius=4, fill=BG, outline=LINE)
    d.text((318, y + 4), sev, font=f(MONO, 12), fill=MUTED, anchor="ma")
    d.text((352, y + 4), question, font=f(REGULAR, 16), fill=INK)


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    frames = [make_frame(i) for i in range(N_FRAMES)]

    # One shared palette avoids per-frame colour flicker in GIF viewers.
    palette = frames[0].quantize(colors=128, method=Image.Quantize.MEDIANCUT)
    quantised = [fr.quantize(palette=palette, dither=Image.Dither.NONE)
                 for fr in frames]

    gif = ASSETS / "demo.gif"
    quantised[0].save(
        gif, save_all=True, append_images=quantised[1:],
        duration=[FRAME_MS] * N_FRAMES, loop=0, optimize=True, disposal=2,
    )

    poster = ASSETS / "demo.png"
    frames[19].save(poster, optimize=True)

    if PORTFOLIO.is_dir():
        shutil.copy2(gif, PORTFOLIO / "demo.gif")
        shutil.copy2(poster, PORTFOLIO / "demo.png")

    print(f"wrote {gif} ({gif.stat().st_size:,} bytes, {N_FRAMES} frames, "
          f"{N_FRAMES * FRAME_MS / 1000:.0f}s loop)")
    print(f"wrote {poster} ({poster.stat().st_size:,} bytes)")
    print("claim in the demo is fabricated and labelled as such in the footer")


if __name__ == "__main__":
    main()
