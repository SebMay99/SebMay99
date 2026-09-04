"""Render the neofetch block and drop it into README.md.

Reads the ASCII art from tools/art.txt and the fields from tools/info.txt,
lays the fields out with dot leaders so every value ends on the same column,
pastes both columns together and rewrites the first ```asciidoc block in
README.md with the result. tools/block.txt keeps a copy of the raw block.

Usage:
    python tools/build.py
"""

import os
import re
import sys

GAP = 4
MIN_DOTS = 2
FENCE = "```"
LANG = "asciidoc"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART = os.path.join(ROOT, "tools", "art.txt")
INFO = os.path.join(ROOT, "tools", "info.txt")
BLOCK = os.path.join(ROOT, "tools", "block.txt")
README = os.path.join(ROOT, "README.md")

BLANK = ("blank", "", "")


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def write(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def parse_info(text):
    """Turn info.txt into (kind, label, value) rows.

    Blank line          -> spacer
    Line starting with @ -> section header
    label|value         -> field
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


def info_width(items):
    widths = [
        len(prefix(label)) + 1 + len(value) + MIN_DOTS
        for kind, label, value in items
        if kind == "field"
    ]
    return max(widths, default=0)


def prefix(label):
    return "- %s: " % label


def render_info(items):
    """Right-align every value against a shared edge, neofetch style."""
    width = info_width(items)
    lines = []

    for index, (kind, label, value) in enumerate(items):
        if kind == "blank":
            lines.append("")
        elif kind == "header":
            # The first header is the user@host line; the rest are section rules.
            head = label if index == 0 else "- %s" % label
            lines.append("%s %s" % (head, "-" * max(1, width - len(head) - 1)))
        else:
            head = prefix(label)
            dots = "." * max(MIN_DOTS, width - len(head) - 1 - len(value))
            lines.append("%s%s %s" % (head, dots, value))

    return lines


def merge(art, info):
    width = max((len(line) for line in art), default=0)
    for i in range(max(len(art), len(info))):
        left = art[i] if i < len(art) else ""
        right = info[i] if i < len(info) else ""
        yield (left.ljust(width) + " " * GAP + right).rstrip()


def trim(lines):
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def replace_block(readme, block):
    opening = FENCE + LANG
    pattern = re.compile(
        "^%s[^\n]*\n.*?^%s[ \t]*$" % (re.escape(opening), re.escape(FENCE)),
        re.DOTALL | re.MULTILINE,
    )
    fenced = "%s\n%s\n%s" % (opening, block, FENCE)

    if not pattern.search(readme):
        sys.exit("README.md: no %s block to replace" % opening)
    return pattern.sub(lambda _: fenced, readme, count=1)


def main():
    art = trim(read(ART).splitlines())
    info = render_info(parse_info(read(INFO)))
    block = "\n".join(merge(art, info))

    write(BLOCK, block + "\n")
    write(README, replace_block(read(README), block))


if __name__ == "__main__":
    main()
