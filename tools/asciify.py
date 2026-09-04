"""Turn a photo into the ASCII art column of the neofetch block.

The ramp runs light to dark and is applied inverted: bright pixels become
spaces, dark pixels become dense glyphs. With a light backdrop behind the
subject that leaves the background empty, so the portrait reads as a
silhouette in both the light and the dark GitHub theme.

Usage:
    python tools/asciify.py tools/photo.png tools/art.txt
    python tools/asciify.py photo.jpg tools/art.txt --width 48 --crop 85,20,375,320

Tips: leave some background around the head so the silhouette reads, keep the
width around 50 (below ~44 the eyes stop resolving), and raise --contrast if
the face turns into a solid block.
"""

import argparse

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

# Light to dark. The first character is what the background collapses to.
RAMP = " .,:;i1tfLCG08@"

# Cell width divided by cell height in the rendered SVG: a 13px monospace glyph
# advances about 7.5px and build.py stacks lines every 16px. Change one and the
# portrait comes out stretched, so change both.
CELL_ASPECT = 0.47

# Head crop of the GitHub avatar, as left,top,right,bottom.
DEFAULT_CROP = "85,20,375,320"


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("photo")
    parser.add_argument("output")
    parser.add_argument("--width", type=int, default=52, help="columns of art")
    parser.add_argument("--crop", default=DEFAULT_CROP, help="left,top,right,bottom or none")
    parser.add_argument("--contrast", type=float, default=1.3)
    parser.add_argument("--sharpen", type=float, default=180, help="unsharp mask percent, 0 is off")
    parser.add_argument("--aspect", type=float, default=CELL_ASPECT)
    parser.add_argument("--ramp", default=RAMP)
    parser.add_argument(
        "--cutoff",
        type=float,
        default=6.0,
        help="percent clipped from each end by autocontrast",
    )
    return parser.parse_args()


def prepare(args):
    image = Image.open(args.photo)

    if args.crop.lower() not in ("", "none"):
        image = image.crop(tuple(int(n) for n in args.crop.split(",")))

    if args.sharpen:
        image = image.filter(ImageFilter.UnsharpMask(radius=4, percent=int(args.sharpen), threshold=2))

    image = ImageOps.autocontrast(image.convert("L"), cutoff=args.cutoff)
    return ImageEnhance.Contrast(image).enhance(args.contrast)


def to_ascii(image, width, aspect, ramp):
    height = max(1, round(width * image.height / image.width * aspect))
    resized = image.resize((width, height), Image.LANCZOS)
    last = len(ramp) - 1

    rows = []
    for y in range(height):
        row = [ramp[round(resized.getpixel((x, y)) / 255 * last)] for x in range(width)]
        rows.append("".join(row).rstrip())
    return rows


def trim(rows):
    while rows and not rows[0].strip():
        rows.pop(0)
    while rows and not rows[-1].strip():
        rows.pop()
    return rows


def main():
    args = parse_args()

    # The ramp is written light to dark, so reverse it: pixel 0 (black) has to
    # land on the densest glyph and pixel 255 (white) on the leading space.
    rows = trim(to_ascii(prepare(args), args.width, args.aspect, args.ramp[::-1]))

    with open(args.output, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(rows) + "\n")


if __name__ == "__main__":
    main()
