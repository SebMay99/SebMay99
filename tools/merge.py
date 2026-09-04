"""Pega el arte ASCII (izquierda) con el bloque de info (derecha) sin romper la alineacion.

Uso:
    python tools/merge.py tools/art.txt tools/info.txt > tools/bloque.txt
    python tools/merge.py tools/art.txt tools/info.txt tools/bloque.txt

El resultado va entre ```asciidoc y ``` dentro del README.
"""

import sys

GAP = 4


def read_lines(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read().splitlines()


def merge(art, info):
    width = max((len(line) for line in art), default=0)
    rows = max(len(art), len(info))
    for i in range(rows):
        left = art[i] if i < len(art) else ""
        right = info[i] if i < len(info) else ""
        yield (left.ljust(width) + " " * GAP + right).rstrip()


def main():
    if len(sys.argv) < 3:
        sys.exit("uso: merge.py <art.txt> <info.txt> [salida.txt]")

    merged = list(merge(read_lines(sys.argv[1]), read_lines(sys.argv[2])))

    if len(sys.argv) > 3:
        with open(sys.argv[3], "w", encoding="utf-8", newline="\n") as handle:
            handle.write("\n".join(merged) + "\n")
        return

    sys.stdout.reconfigure(encoding="utf-8")
    print("\n".join(merged))


if __name__ == "__main__":
    main()
