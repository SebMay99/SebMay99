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
# Keep LINE_HEIGHT / (FONT_SIZE * ADVANCE) in step with --aspect in asciify.py,
# otherwise the portrait comes out stretched.
LINE_HEIGHT = 14.5
PADDING = 12
# Widest plausible advance for a monospace glyph, as a fraction of the size.
# Only used to size the canvas: the font's own metrics keep the columns aligned.
ADVANCE = 0.615

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART = os.path.join(ROOT, "tools", "art.txt")
INFO = os.path.join(ROOT, "tools", "info.txt")
BLOCK = os.path.join(ROOT, "tools", "block.txt")

THEMES = {
    "light_mode.svg": {
        "art": "#57606a",
        "user": "#1a7f37",
        "section": "#0969da",
        "key": "#8250df",
        "value": "#1f2328",
        "punct": "#8c959f",
        "rule": "#afb8c1",
        "dots": "#d1d9e0",
    },
    "dark_mode.svg": {
        "art": "#768390",
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


def merge(art, info):
    """Put the art column and the info column side by side, line by line."""
    art_width = max((len(line) for line in art), default=0)
    rows = []

    for i in range(max(len(art), len(info))):
        left = (art[i] if i < len(art) else "").ljust(art_width + GAP)
        rows.append([(left, "art")] + (info[i] if i < len(info) else []))

    return rows


def text_of(row):
    return "".join(text for text, _ in row)


def trim(lines):
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def render_svg(rows, colors):
    columns = max(len(text_of(row)) for row in rows)
    width = round(columns * FONT_SIZE * ADVANCE) + 2 * PADDING
    height = round(len(rows) * LINE_HEIGHT) + 2 * PADDING

    styles = "\n".join(
        "      .%s { fill: %s; }" % (name, color) for name, color in sorted(colors.items())
    )

    lines = []
    for index, row in enumerate(rows):
        if not text_of(row).strip():
            continue
        y = PADDING + LINE_HEIGHT * (index + 1) - 4
        spans = "".join(
            '<tspan class="%s">%s</tspan>' % (cls, escape(text)) for text, cls in row if text
        )
        lines.append('    <text x="%d" y="%.1f">%s</text>' % (PADDING, y, spans))

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
        styles=styles,
        lines="\n".join(lines),
    )


def main():
    art = trim(read(ART).splitlines())
    rows = merge(art, info_segments(parse_info(read(INFO))))

    write(BLOCK, "\n".join(text_of(row).rstrip() for row in rows) + "\n")

    for name, colors in THEMES.items():
        write(os.path.join(ROOT, name), render_svg(rows, colors))


if __name__ == "__main__":
    main()
