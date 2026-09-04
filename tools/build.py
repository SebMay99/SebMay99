"""Render the neofetch profile block.

Reads the ASCII art from tools/art.txt and the fields from tools/info.txt,
lays the fields out with dot leaders so every value ends on the same column,
and writes three things:

    tools/block.txt   plain text version of the block
    light_mode.svg    coloured block for the light GitHub theme
    dark_mode.svg     coloured block for the dark GitHub theme

The README embeds the two SVGs through a <picture> element. Rendering to SVG
instead of a fenced code block is what buys real colours: GitHub's syntax
highlighter will not reliably tint `Key: value` pairs that sit to the right of
ASCII art, but an SVG owns every glyph's colour.

Usage:
    python tools/build.py
"""

import os
import sys
from xml.sax.saxutils import escape

GAP = 4
MIN_DOTS = 2

FONT = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"
FONT_SIZE = 12
LINE_HEIGHT = 14.5

# The art gets its own, much smaller size so it can carry four times the
# columns in the same physical space. Keep ART_LINE_HEIGHT / (ART_FONT_SIZE *
# ADVANCE) in step with --aspect in asciify.py, otherwise the portrait comes
# out stretched. Blocks are drawn a touch taller than the line so consecutive
# rows meet instead of leaving seams.
ART_FONT_SIZE = 7
ART_LINE_HEIGHT = 7.0

PADDING = 12
# Pixel gutter between the two columns, since they no longer share a grid.
GUTTER = 22

# Ramp characters in asciify.py, mapped to the shade classes below.
SHADES = {"░": 0, "▒": 1, "▓": 2, "█": 3}
# Widest plausible advance for a monospace glyph, as a fraction of the size.
# Only used to size the canvas: the font's own metrics keep the columns aligned.
ADVANCE = 0.615

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART = os.path.join(ROOT, "tools", "art.txt")
INFO = os.path.join(ROOT, "tools", "info.txt")
BLOCK = os.path.join(ROOT, "tools", "block.txt")

THEMES = {
    "light_mode.svg": {
        # Four shades of ink for the portrait: light stipple through solid.
        "art0": "#ced5dd",
        "art1": "#9aa3ad",
        "art2": "#6a737d",
        "art3": "#3c434b",
        "user": "#1a7f37",
        "section": "#0969da",
        "key": "#8250df",
        "value": "#1f2328",
        "punct": "#8c959f",
        "rule": "#afb8c1",
        "dots": "#d1d9e0",
    },
    "dark_mode.svg": {
        "art0": "#3f4650",
        "art1": "#5f6b76",
        "art2": "#8a95a1",
        "art3": "#b7c2cd",
        "user": "#3fb950",
        "section": "#58a6ff",
        "key": "#a371f7",
        "value": "#c9d1d9",
        "punct": "#6e7681",
        "rule": "#484f58",
        "dots": "#373e47",
    },
}

TITLE = "Sebastian Mayorga - neofetch profile card"

BLANK = ("blank", "", "")


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def write(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def parse_info(text):
    """Turn info.txt into (kind, label, value) rows.

    Blank line           -> spacer
    Line starting with @ -> section header
    label|value          -> field
    """
    items = []
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            items.append(BLANK)
        elif line.startswith("@"):
            items.append(("header", line[1:].strip(), ""))
        elif "|" in line:
            label, value = line.split("|", 1)
            items.append(("field", label.strip(), value.strip()))
        else:
            sys.exit("info.txt:%d: expected '@header', 'label|value' or a blank line" % number)
    return items


def prefix(label):
    return "- %s: " % label


def info_width(items):
    widths = [
        len(prefix(label)) + 1 + len(value) + MIN_DOTS
        for kind, label, value in items
        if kind == "field"
    ]
    return max(widths, default=0)


def info_segments(items):
    """Lay the fields out as coloured segments, values right-aligned."""
    width = info_width(items)
    rows = []

    for index, (kind, label, value) in enumerate(items):
        if kind == "blank":
            rows.append([])
            continue

        if kind == "header":
            # The first header is the user@host line, the rest are section rules.
            if index == 0:
                segments = [(label, "user")]
                used = len(label)
            else:
                segments = [("- ", "punct"), (label, "section")]
                used = 2 + len(label)
            segments.append((" " + "-" * max(1, width - used - 1), "rule"))
            rows.append(segments)
            continue

        head = prefix(label)
        dots = "." * max(MIN_DOTS, width - len(head) - 1 - len(value))
        rows.append(
            [
                ("- ", "punct"),
                ("%s:" % label, "key"),
                (" %s " % dots, "dots"),
                (value, "value"),
            ]
        )

    return rows


def text_of(row):
    return "".join(text for text, _ in row)


def trim(lines):
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def art_runs(line):
    """Group a line of art into runs of one shade, so each gets its own colour.

    Colouring the shades separately is what puts tone in the portrait: the glyph
    carries the coverage and the fill carries the brightness, which together
    read as many more levels than four flat characters would.
    """
    runs = []
    for char in line:
        shade = SHADES.get(char)
        cls = "art%d" % shade if shade is not None else "art0"
        if runs and runs[-1][1] == cls:
            runs[-1][0].append(char)
        else:
            runs.append(([char], cls))
    return [("".join(chars), cls) for chars, cls in runs]


def text_line(x, y, segments):
    spans = "".join(
        '<tspan class="%s">%s</tspan>' % (cls, escape(text)) for text, cls in segments if text
    )
    return '    <text x="%.1f" y="%.1f">%s</text>' % (x, y, spans)


def render_svg(art, info, colors):
    """Draw the art and the info as two independent text columns.

    They do not share a font size on purpose. The art is a picture, so it gets a
    small size and many columns; the info has to stay readable, so it keeps a
    normal one. Laying them out as separate blocks at fixed x positions also
    means the art's glyph metrics cannot shift the info column.
    """
    art_columns = max((len(line) for line in art), default=0)
    art_x_width = art_columns * ART_FONT_SIZE * ADVANCE
    info_columns = max((len(text_of(row)) for row in info), default=0)

    info_x = PADDING + art_x_width + GUTTER
    width = round(info_x + info_columns * FONT_SIZE * ADVANCE) + PADDING
    height = round(
        max(len(art) * ART_LINE_HEIGHT, len(info) * LINE_HEIGHT)
    ) + 2 * PADDING

    styles = "\n".join(
        "      .%s { fill: %s; }" % (name, color) for name, color in sorted(colors.items())
    )

    lines = []
    for index, line in enumerate(art):
        if not line.strip():
            continue
        y = PADDING + ART_LINE_HEIGHT * (index + 1)
        lines.append(text_line(PADDING, y, art_runs(line)))

    for index, row in enumerate(info):
        if not text_of(row).strip():
            continue
        y = PADDING + LINE_HEIGHT * (index + 1) - 4
        lines.append(text_line(info_x, y, row))

    # The art uses block-element characters, so state the encoding rather than
    # leaving a consumer to guess it.
    return """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" \
viewBox="0 0 {width} {height}" role="img" aria-labelledby="title">
  <title id="title">{title}</title>
  <style>
    text {{
      font-family: {font};
      font-size: {size}px;
      white-space: pre;
      dominant-baseline: alphabetic;
    }}
    .art0, .art1, .art2, .art3 {{ font-size: {art_size}px; }}
{styles}
  </style>
  <g xml:space="preserve">
{lines}
  </g>
</svg>
""".format(
        width=width,
        height=height,
        title=escape(TITLE),
        font=FONT,
        size=FONT_SIZE,
        art_size=ART_FONT_SIZE,
        styles=styles,
        lines="\n".join(lines),
    )


def main():
    art = trim(read(ART).splitlines())
    info = info_segments(parse_info(read(INFO)))

    art_width = max((len(line) for line in art), default=0)
    merged = []
    for i in range(max(len(art), len(info))):
        left = (art[i] if i < len(art) else "").ljust(art_width + GAP)
        right = text_of(info[i]) if i < len(info) else ""
        merged.append((left + right).rstrip())
    write(BLOCK, "\n".join(merged) + "\n")

    for name, colors in THEMES.items():
        write(os.path.join(ROOT, name), render_svg(art, info, colors))


if __name__ == "__main__":
    main()
