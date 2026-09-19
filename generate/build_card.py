"""Generate the profile card SVGs.  python3 generate/build_card.py

One source, two files: dark_mode.svg and light_mode.svg, served from the README
through a <picture> element so GitHub picks the right one per viewer.

The thing that makes a character grid hold inside SVG is NOT `white-space:pre`
and NOT xml:space="preserve" -- both get ignored often enough to be useless.
Every line is its own <tspan> with an explicit x and y. The renderer then has
no whitespace to collapse, because the position is stated rather than implied.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONT_PX, LINE_PX = 15, 19
# block-drawing glyphs fill their whole cell, so the art only tiles into a
# solid shape when its line height equals its font size -- any leading and the
# panther comes out striped
ART_PX, ART_LINE = 11, 11
PAD_X, PAD_Y = 18, 30
CHAR_W = 0.60          # monospace advance as a fraction of font size

ART = r"""
     ▄        ▄
     ██      ██                                         ▄█
     ▀█      █▀                                         ██
      ████████                                         ██▀
    ▄▄██████████▄▄                                   ▄███
  ▄████████████████████████▄▄▄▄▄▄ ▄▄▄▄▄▄▄█████████▄▄███▀
   ▀███▀████████████████████████████████████████████▀
            ▀▀██████████████████████████████████████
                 ███████████▀▀▀▀▀▀▀▀▀▀▀▀▀██████████
                    ██▀  ▀██              ▄██▀  ███
                   ▄██    ██             ▄██▀   ███
                   ██▀    ██             ███    ███
                  ▄██     ██▄             ▀██▄  ███
                  ▀█▀     ▀▀▀              ▀▀▀  ▀▀▀
""".strip("\n").split("\n")

# (key, value) -- None is a blank line, a bare string is a rule/heading
INFO = [
    ("@", "abenezer0101"),
    "rule",
    ("Studying", "CIS, Georgia State University"),
    ("Focus", "data tools, pipelines, analytics"),
    ("Method", "build it, then try hard to break it"),
    None,
    ("Languages.Programming", "Python, SQL, JavaScript"),
    ("Languages.Markup", "HTML, CSS, Markdown, TOML"),
    ("Tools", "SQLite, Flask, Playwright, Git"),
    ("Environment", "Linux"),
    None,
    ("Projects.minidb", "a SQL engine, diffed against SQLite"),
    ("Projects.assay", "a data gate that audits its own rules"),
    ("Projects.pdf-study-kit", "PDF to flashcards and a quiz"),
    ("Projects.portfolio", "27 dashboards, apps and data tools"),
    None,
    ("Contact.Email", "abenezerkoru10b@gmail.com"),
    ("Contact.GitHub", "github.com/Abenezer0101"),
    None,
    ("status", "open to internship + new-grad roles"),
]

THEMES = {
    "dark":  dict(bg="#161b22", fg="#c9d1d9", key="#ffa657", val="#a5d6ff",
                  dim="#616e7f", art="#58a6ff", ok="#3fb950"),
    "light": dict(bg="#ffffff", fg="#1f2328", key="#953800", val="#0a3069",
                  dim="#6e7781", art="#0969da", ok="#1a7f37"),
}

KEY_W = max(len(k) for k, _ in [i for i in INFO if isinstance(i, tuple)]) + 1


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def plain(item):
    """The rendered width of an info row, in characters."""
    if item is None:
        return 0
    if item == "rule":
        return 46
    k, v = item
    if k == "@":
        return len(v) + 7
    if k == "status":
        return len(v) + 2
    return KEY_W + 2 + len(v)


PANTHER = Path(__file__).resolve().parent.parent / "assets" / "panther.svg"
ART_BOX = (300, 272)          # rendered size of the panther, in px


def panther_fragment(scale, dx, dy):
    """Lift the panther's own style and shapes into this card.

    Its class names are namespaced on the way in, because `.blk` and `.blu`
    would otherwise collide with anything this file defines later.
    """
    src = PANTHER.read_text(encoding="utf-8")
    style = re.search(r"<style>(.*?)</style>", src, re.S).group(1)
    body = src[src.index('<g id="beast">'): src.rindex("</svg>")]
    for name in ("blk", "blu", "wht", "eye"):
        style = style.replace(f".{name}{{", f".p-{name}{{")
        body = body.replace(f'class="{name}"', f'class="p-{name}"')
    style = style.replace("#beast", "#p-beast").replace("#jaw", "#p-jaw")
    style = style.replace("#throat", "#p-throat")
    for ident in ("beast", "jaw", "throat", "upperteeth"):
        body = body.replace(f'id="{ident}"', f'id="p-{ident}"')
    return style, f'<g transform="translate({dx},{dy}) scale({scale})">{body}</g>'


PANTHER_STYLE, _frag = panther_fragment(ART_BOX[0] / 420, 0, 0)
PANTHER_BODY = _frag.replace("translate(0,0)", "translate(@@DX@@,@@DY@@)")


def build(theme):
    c = THEMES[theme]
    art_w, art_h = ART_BOX
    info_x = PAD_X + art_w + 34
    info_w = int(max(plain(i) for i in INFO) * FONT_PX * CHAR_W)
    rows = sum(1 for i in INFO) + 1

    width = info_x + info_w + PAD_X + 8
    height = PAD_Y + max(art_h, rows * LINE_PX) + 26

    out = [
        "<?xml version='1.0' encoding='UTF-8'?>",
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}px" height="{height}px" '
        f'font-size="{FONT_PX}px" font-family="ConsolasFallback,Consolas,'
        '\'DejaVu Sans Mono\',Menlo,monospace" '
        'role="img" aria-label="Abenezer Bekele — profile card">',
        "<style>",
        "@font-face{src:local('Consolas'),local('Consolas Bold');"
        "font-family:'ConsolasFallback';font-display:swap;size-adjust:109%;}",
        f".k{{fill:{c['key']};}} .v{{fill:{c['val']};}} .d{{fill:{c['dim']};}}",
        f".a{{fill:{c['art']};}} .ok{{fill:{c['ok']};}}",
        "text,tspan{white-space:pre;}",
        PANTHER_STYLE,
        "</style>",
        f'<rect width="{width}px" height="{height}px" fill="{c["bg"]}" rx="15"/>',
    ]

    art_top = PAD_Y + max(0, (rows * LINE_PX - art_h) // 2) - 14
    out.append(PANTHER_BODY.replace("@@DX@@", str(PAD_X + 6)).replace("@@DY@@", str(art_top)))

    out.append(f'<text fill="{c["fg"]}" x="{info_x}" y="{PAD_Y}">')
    y = PAD_Y
    for item in INFO:
        if item is None:
            y += LINE_PX
            continue
        if item == "rule":
            out.append(f'<tspan class="d" x="{info_x}" y="{y}">{"-" * 46}</tspan>')
            y += LINE_PX
            continue
        k, v = item
        if k == "@":
            out.append(f'<tspan x="{info_x}" y="{y}">'
                       f'<tspan class="k">{esc(v)}</tspan>'
                       f'<tspan class="d">@</tspan>'
                       f'<tspan class="k">github</tspan></tspan>')
        elif k == "status":
            out.append(f'<tspan x="{info_x}" y="{y}">'
                       f'<tspan class="d">$ </tspan>'
                       f'<tspan class="ok">{esc(v)}</tspan></tspan>')
        else:
            dots = "." * (KEY_W - len(k))
            out.append(f'<tspan x="{info_x}" y="{y}">'
                       f'<tspan class="k">{esc(k)}</tspan>'
                       f'<tspan class="d">{dots}: </tspan>'
                       f'<tspan class="v">{esc(v)}</tspan></tspan>')
        y += LINE_PX
    out.append("</text>")
    out.append("</svg>")
    return "\n".join(out)


if __name__ == "__main__":
    for theme in THEMES:
        p = ROOT / f"{theme}_mode.svg"
        p.write_text(build(theme), encoding="utf-8")
        print(f"wrote {p.name}  ({p.stat().st_size:,} bytes)")
