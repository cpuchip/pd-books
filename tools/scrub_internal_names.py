r"""scrub_internal_names.py: take the names of our internal seats and tools out of the errata we publish.

    python tools/scrub_internal_names.py [--check]

found.json was written by the seats that did the work, so its evidence names them ("settled against the scan
by qwenniverse-fermion's scan check", "claudiverse judge.py"). A reader needs what was done, not who in our
fleet did it. The replacements below keep every fact (the scan, the leaf, the computation) and drop the names.
--check only reports what is left.
"""
import argparse
import glob
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Longest first: a phrase is replaced before any shorter phrase inside it.
REPLACE = [
    ("settled against the scan by qwenniverse-fermion's scan check", "settled against the scan"),
    ("settled against the scan by qwenniverse-fermion", "settled against the scan"),
    ("misprint verified on the page image by qwenniverse-fermion", "misprint verified on the page image"),
    ("qwenniverse-fermion, while reading page", "found while reading page"),
    ("claudiverse pilot (qwenniverse-fermion)", "our pilot pipeline"),
    ("confirmed by hand algebra (abacus)", "confirmed by hand algebra"),
    ("confirmed by abacus", "confirmed by a second reader"),
    ("Flagged by the claudiverse shelf:", "Flagged by our reading pipeline:"),
    ("claudiverse judge.py", "the computer-algebra checker"),
    ("claudiverse shelf (", "our reading pipeline ("),
    ("claudiverse pilot (", "our pilot pipeline ("),
    ("abacus's scan list", "the scan list"),
    ("awaiting abacus", "awaiting a second check"),
    ("abacus concurred", "a second reader concurred"),
    ("judge.py agreed", "the checker agreed"),
    ("judge.py", "the computer-algebra checker"),
]
LEFT = re.compile(r"\b(qwenniverse-fermion|qwenniverse|claudiverse|abacus|basecamp|judge\.py)\b")


def scrub(x):
    if isinstance(x, str):
        for old, new in REPLACE:
            x = x.replace(old, new)
        return x
    if isinstance(x, list):
        return [scrub(v) for v in x]
    if isinstance(x, dict):
        return {k: scrub(v) for k, v in x.items()}
    return x


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    left, changed = [], 0
    for f in sorted(glob.glob(os.path.join(ROOT, "books", "*", "found.json"))):
        raw = open(f, encoding="utf-8").read()
        data = json.loads(raw)
        new = scrub(data)
        if not a.check and new != data:
            # keep the file's own layout, so the diff shows only the words that changed
            second = raw.split("\n", 2)[1] if raw.count("\n") > 1 else ""
            indent = len(second) - len(second.lstrip(" ")) or None
            with open(f, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(json.dumps(new, ensure_ascii=False, indent=indent) + ("\n" if raw.endswith("\n") else ""))
            changed += 1
        for m in LEFT.finditer(json.dumps(new if not a.check else data, ensure_ascii=False)):
            left.append((os.path.basename(os.path.dirname(f)), m.group(0)))
    print(f"{changed} file(s) rewritten; {len(left)} internal name(s) left: {left[:10]}")
    return 1 if left else 0


if __name__ == "__main__":
    sys.exit(main())
