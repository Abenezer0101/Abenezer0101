"""Generate the cosmic banner.  python3 generate/build_cosmos.py

A night sky with an aurora, a twinkling starfield, and a fairy that flies a
looping path trailing sparkles.

Motion along a path uses SMIL <animateMotion> rather than CSS offset-path.
Both are lovely in a browser tab; only SMIL is dependable inside an <img>,
which is the only way a README can show any of this at all.

Star positions come from a seeded RNG so the file regenerates byte-identically
and a diff stays readable.
"""

import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
W, H = 900, 270
SEED = 20260919

# the fairy's route: in from the left, a dip, a rise, out to the right
FLIGHT = "M -40 150 C 150 60, 250 210, 420 130 S 660 40, 760 120 S 900 175, 960 110"
FLIGHT_SECONDS = 11
TRAIL = 14                     # sparkles strung out behind her


def stars(rnd, n=90):
    out = []
    for _ in range(n):
        x, y = rnd.uniform(4, W - 4), rnd.uniform(4, H - 4)
        # thin the field near the text so the words stay legible
        if 40 < x < 560 and 150 < y < 235 and rnd.random() < 0.82:
            continue
        r = round(rnd.choice([0.6, 0.7, 0.9, 1.1, 1.4, 1.8]), 2)
        dur = round(rnd.uniform(2.2, 6.0), 2)
        delay = round(rnd.uniform(0, 6.0), 2)
        dim = round(rnd.uniform(0.15, 0.4), 2)
        out.append((round(x, 1), round(y, 1), r, dur, delay, dim))
    return out


def build():
    rnd = random.Random(SEED)
    sky = stars(rnd)

    p = [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
         f'viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
         f'aria-label="A night sky with an aurora and a fairy trailing sparkles">']

    p.append("<defs>")
    p.append('<radialGradient id="sky" cx="50%" cy="10%" r="95%">'
             '<stop offset="0%" stop-color="#241a5e"/>'
             '<stop offset="55%" stop-color="#0d0c2b"/>'
             '<stop offset="100%" stop-color="#04040e"/></radialGradient>')
    p.append('<linearGradient id="au1" x1="0" y1="0" x2="1" y2="0">'
             '<stop offset="0%" stop-color="#2de6c0" stop-opacity="0"/>'
             '<stop offset="40%" stop-color="#2de6c0" stop-opacity=".55"/>'
             '<stop offset="70%" stop-color="#6d7bff" stop-opacity=".45"/>'
             '<stop offset="100%" stop-color="#6d7bff" stop-opacity="0"/></linearGradient>')
    p.append('<linearGradient id="au2" x1="0" y1="0" x2="1" y2="0">'
             '<stop offset="0%" stop-color="#c46bff" stop-opacity="0"/>'
             '<stop offset="45%" stop-color="#c46bff" stop-opacity=".40"/>'
             '<stop offset="100%" stop-color="#2de6c0" stop-opacity="0"/></linearGradient>')
    p.append('<filter id="soft" x="-40%" y="-140%" width="180%" height="380%">'
             '<feGaussianBlur stdDeviation="13"/></filter>')
    p.append('<filter id="glow" x="-180%" y="-180%" width="460%" height="460%">'
             '<feGaussianBlur stdDeviation="3.4" result="b"/>'
             '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')
    p.append(f'<path id="flight" d="{FLIGHT}" fill="none"/>')
    p.append("</defs>")

    p.append("<style>")
    p.append(".tw{animation:tw var(--d) ease-in-out infinite;animation-delay:var(--t)}")
    p.append("@keyframes tw{0%,100%{opacity:var(--o)}50%{opacity:1}}")
    p.append("#a1{animation:drift1 19s ease-in-out infinite}")
    p.append("#a2{animation:drift2 25s ease-in-out infinite}")
    p.append("@keyframes drift1{0%,100%{transform:translate(0,0) scaleY(1)}"
             "50%{transform:translate(26px,-9px) scaleY(1.18)}}")
    p.append("@keyframes drift2{0%,100%{transform:translate(0,0) scaleY(1)}"
             "50%{transform:translate(-32px,7px) scaleY(.86)}}")
    p.append(".wing{animation:flap .22s ease-in-out infinite;transform-origin:0 0}")
    p.append("@keyframes flap{0%,100%{transform:scaleX(1) scaleY(1)}50%{transform:scaleX(.45) scaleY(1.1)}}")
    p.append(".name{font:700 25px system-ui,-apple-system,'Segoe UI',sans-serif;fill:#f2f0ff;"
             "letter-spacing:-.01em}")
    p.append(".tag{font:400 13.5px system-ui,-apple-system,'Segoe UI',sans-serif;fill:#b9b4e8}")
    p.append("@media (prefers-reduced-motion:reduce){"
             ".tw,#a1,#a2,.wing{animation:none}}")
    p.append("</style>")

    p.append(f'<rect width="{W}" height="{H}" rx="14" fill="url(#sky)"/>')

    # aurora, behind everything
    p.append('<g filter="url(#soft)" opacity=".75">')
    p.append('<path id="a1" fill="url(#au1)" d="M -60 96 C 180 40, 380 132, 600 74 '
             'S 880 34, 980 88 L 980 132 C 860 92, 640 130, 480 128 '
             'S 140 104, -60 140 Z"/>')
    p.append('<path id="a2" fill="url(#au2)" d="M -60 150 C 200 104, 340 186, 560 140 '
             'S 860 106, 980 148 L 980 186 C 820 152, 600 190, 420 178 '
             'S 120 166, -60 194 Z"/>')
    p.append("</g>")

    # starfield
    p.append('<g fill="#ffffff">')
    for x, y, r, dur, delay, dim in sky:
        p.append(f'<circle class="tw" cx="{x}" cy="{y}" r="{r}" '
                 f'style="--d:{dur}s;--t:{delay}s;--o:{dim}" opacity="{dim}"/>')
    p.append("</g>")

    # the sparkle trail: the same flight, started progressively later, so the
    # dots string out behind her instead of clustering
    p.append('<g fill="#ffe9a8" filter="url(#glow)">')
    for i in range(TRAIL):
        lag = round(0.10 + i * 0.085, 3)
        r = round(2.5 - i * 0.14, 2)
        op = round(0.85 - i * 0.055, 3)
        p.append(f'<circle r="{r}" opacity="{op}">'
                 f'<animateMotion dur="{FLIGHT_SECONDS}s" repeatCount="indefinite" '
                 f'begin="-{lag}s"><mpath xlink:href="#flight"/></animateMotion>'
                 f'<animate attributeName="opacity" dur="{FLIGHT_SECONDS}s" '
                 f'repeatCount="indefinite" begin="-{lag}s" '
                 f'values="0;{op};{op};0" keyTimes="0;.08;.85;1"/></circle>')
    p.append("</g>")

    # the fairy herself. The wings sit OUTSIDE the glow filter -- run through
    # it they blur into the halo and she reads as a passing spark instead.
    p.append('<g>')
    p.append('<animateMotion dur="%ds" repeatCount="indefinite" rotate="auto">'
             '<mpath xlink:href="#flight"/></animateMotion>' % FLIGHT_SECONDS)
    p.append('<circle cx="0" cy="0" r="11" fill="#ffe9a8" opacity=".22" filter="url(#glow)"/>')
    p.append('<g class="wing" fill="#b8f6ff" opacity=".92">'
             '<ellipse cx="-7" cy="-9.5" rx="12" ry="6" transform="rotate(-34 -7 -9.5)"/>'
             '<ellipse cx="-7" cy="9.5" rx="12" ry="6" transform="rotate(34 -7 9.5)"/>'
             '<ellipse cx="-4" cy="-5" rx="7.5" ry="3.6" transform="rotate(-18 -4 -5)" opacity=".8"/>'
             '<ellipse cx="-4" cy="5" rx="7.5" ry="3.6" transform="rotate(18 -4 5)" opacity=".8"/></g>')
    p.append('<ellipse cx="0" cy="0" rx="4.4" ry="2.9" fill="#fff6d5" filter="url(#glow)"/>')
    p.append("</g>")

    p.append(f'<text class="name" x="40" y="196">Abenezer Bekele</text>')
    p.append(f'<text class="tag" x="40" y="220">I build data tools, then try hard to break them.</text>')
    p.append("</svg>")
    return "\n".join(p)


if __name__ == "__main__":
    out = ROOT / "assets" / "cosmos.svg"
    out.write_text(build(), encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)}  ({out.stat().st_size:,} bytes)")
