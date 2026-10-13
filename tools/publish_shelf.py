"""publish_shelf.py: bring the claudiverse's shelf export into export/, merge our errata, validate.

    python tools/publish_shelf.py [--from lepton-claude:claudiverse/export] [--local DIR]

The export is generated on lepton (claudiverse scripts/export_shelf.py, from the pd-shelf world) and
committed here, so learn.cpuchip.net's build pins it like its other inputs (primer, #pd-books 5963).
This step adds each book's errata (tools/make_errata.py collect: the transcriber's marks, ours, the
candidates, each with its status and evidence) and refuses to write an export that fails a check:
  - every file carries schema_version, generated_from, node_types and edge_types;
  - ids are unique, and every id a file refers to exists (in the book, or in graph.json);
  - every node and link type is one of the enumerated ones;
  - no control characters in any string (a backslash eaten by a shell shows up as one);
  - no claude.ai session URL anywhere;
  - every figure a chapter's text_html shows is a file inside the export (images/<book>/...);
  - every erratum's status is one of ERRATA_STATUSES (listed in each book file), and erratum ids are
    unique across the export (each is prefixed with its book's id);
  - an erratum's chapter, when it has one, is a chapter of its book;
  - no book.macros key or value names Project Gutenberg.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from make_errata import collect  # noqa: E402

BAD = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
ERRATA_STATUSES = ["transcriber_marked", "candidate", "probable", "confirmed", "dismissed", "note"]


def site_erratum(book, e):
    """found.json keeps a status sentence; the site gets one of ERRATA_STATUSES, with the sentence moved
    into evidence, and an id prefixed with the book's id (G001 exists in more than one book)."""
    prose, kind = (e.get("status") or "").strip(), e.get("kind") or ""
    low = prose.lower()
    if kind == "transcriber-marked":
        status = "transcriber_marked"
    elif kind == "note" or e["id"].startswith("N"):
        status = "note"
    elif low.startswith("confirmed"):
        status = "confirmed"
    elif low.startswith("probable"):
        status = "probable"
    elif low.startswith("dismissed"):
        status = "dismissed"
    else:
        status = "candidate"
    out = {**e, "id": f"{book}/{e['id']}", "status": status}
    if prose and prose.lower() != status.replace("_", " "):
        out["evidence"] = f"Status: {prose}." + (f" {e['evidence']}" if e.get("evidence") else "")
    return out


ROMAN = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100}


def page_number(p):
    """An arabic page as its number, a roman one (front matter) as a number below every arabic page, else None."""
    p = str(p or "").strip().lower()
    if p.isdigit():
        return int(p)
    if p and set(p) <= set(ROMAN):
        v = [ROMAN[c] for c in p]
        return -1000 + sum(-a if a < b else a for a, b in zip(v, v[1:] + [0]))
    return None


def squash(s):
    return re.sub(r"\s+|\$|\\[()\[\]]", "", s or "")


def place_errata(d):
    """Each erratum's chapter (books #7833: the text pages show errata beside the text, never in it). The exercise its
    location names decides; else the chapters whose pages hold its page (all of them when it has none), narrowed
    to the ones whose text has the printed words. printed_in_text says whether the chapter's text_html holds the
    printed words, compared without spaces or math delimiters, so the page knows whether a search will find them."""
    sets = {s["id"]: s.get("chapter") for s in d.get("exercise_sets", [])}
    chapters = d.get("chapters", [])
    ranged = [c for c in chapters if c.get("pages") and None not in map(page_number, c["pages"])]
    texts = {c["id"]: squash(c.get("text_latex")) for c in chapters}
    for e in d.get("errata", []):
        chapter, location = None, str(e.get("location") or "")
        page = page_number(e.get("page"))
        printed = squash(e.get("printed"))
        m = re.match(r"Exercises?\s+(\S+?),", location)
        named = [f"{d['book']['id']}/ex-{n}" for n in ((m.group(1), m.group(1).lower()) if m else ())]
        if location.startswith("Answers"):  # the answers at the back are no chapter's text
            chapter = None
        elif any(sets.get(n) for n in named):  # Thompson's "Exercises XII" is set ex-xii
            chapter = next(sets[n] for n in named if sets.get(n))
        elif e.get("context"):  # a transcriber's mark: the words before it, then the printed text (which can be empty)
            key = squash(e["context"])[-(20 if printed else 30):] + printed
            hits = [c["id"] for c in chapters if key in texts[c["id"]]]
            chapter = hits[0] if len(hits) == 1 else None
        else:
            if page is not None and ranged:
                cands = [c for c in ranged if page_number(c["pages"][0]) <= page <= page_number(c["pages"][-1])]
            else:
                cands = chapters
            if printed:
                cands = [c for c in cands if printed in texts[c["id"]]] or (cands if len(cands) <= 2 else [])
            chapter = cands[0]["id"] if cands else None
        e["chapter"] = chapter
        text = next((squash(c.get("text_html")) for c in chapters if c["id"] == chapter), "")
        e["printed_in_text"] = bool(squash(e.get("printed")) and squash(e.get("printed")) in text)


def strings(x, path=""):
    if isinstance(x, str):
        yield path, x
    elif isinstance(x, dict):
        for k, v in x.items():
            yield from strings(v, f"{path}.{k}")
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from strings(v, f"{path}[{i}]")


def check(export):
    errs = []
    files = [export / "books.json", export / "graph.json"] + sorted((export / "books").glob("*.json"))
    docs = {}
    for f in files:
        d = json.loads(f.read_text(encoding="utf-8"))
        docs[f] = d
        for k in ("schema_version", "generated_from", "node_types", "edge_types"):
            if k not in d:
                errs.append(f"{f.name}: no {k}")
        for p, s in strings(d):
            if BAD.search(s):
                errs.append(f"{f.name}{p}: control character")
            if "claude.ai/code/session" in s:
                errs.append(f"{f.name}{p}: a session URL")
    for b in docs[export / "books.json"].get("books", []):
        for k, v in (b.get("macros") or {}).items():
            if re.search(r"(?i)gutenberg", k + v) or k.startswith("\\PG"):
                errs.append(f"books.json: {b.get('id')} macros {k} names Project Gutenberg")
    graph = docs[export / "graph.json"]
    ids = [n["id"] for n in graph["nodes"]]
    if len(ids) != len(set(ids)):
        errs.append(f"graph.json: {len(ids) - len(set(ids))} duplicate node ids")
    known = set(ids)
    for n in graph["nodes"]:
        if n["type"] not in graph["node_types"]:
            errs.append(f"graph.json: node type {n['type']!r}")
    for ln in graph["links"]:
        if ln["type"] not in graph["edge_types"]:
            errs.append(f"graph.json: link type {ln['type']!r}")
        if ln["source"] not in known or ln["target"] not in known:
            errs.append(f"graph.json: link {ln['source']} -> {ln['target']} to an unknown node")
    for f, d in docs.items():
        if f.parent.name != "books":
            continue
        for x in d.get("errata", []):
            if x.get("status") not in ERRATA_STATUSES:
                errs.append(f"{f.name}: erratum {x.get('id')} has status {x.get('status')!r}")
            if not str(x.get("id", "")).startswith(d["book"]["id"] + "/"):
                errs.append(f"{f.name}: erratum id {x.get('id')} is not prefixed with the book id")
            if x.get("chapter") and x["chapter"] not in {c["id"] for c in d["chapters"]}:
                errs.append(f"{f.name}: erratum {x.get('id')} names chapter {x['chapter']!r}, not one of the book's")
        for k, v in (d["book"].get("macros") or {}).items():
            if re.search(r"(?i)gutenberg", k + v) or k.startswith("\\PG"):
                errs.append(f"{f.name}: book.macros {k} names Project Gutenberg")
        own = [x["id"] for key in ("chapters", "excerpts", "equations", "exercise_sets", "problems", "errata") for x in d.get(key, [])]
        if len(own) != len(set(own)):
            errs.append(f"{f.name}: duplicate ids")
        refs = [r for c in d["chapters"] for key in ("concepts", "excerpts", "equations", "exercise_sets") for r in c[key]]
        refs += [x["chapter"] for key in ("excerpts", "equations") for x in d[key]]
        refs += [p["set"] for p in d["problems"] if p.get("set")] + [r for p in d["problems"] for r in p["same_problem_in"]]
        missing = sorted({r for r in refs if r and r not in known})
        if missing:
            errs.append(f"{f.name}: {len(missing)} references to unknown ids, e.g. {missing[:3]}")
        figs = {s for c in d["chapters"] for s in re.findall(r"<(?:img|embed)\b[^>]*\bsrc=\"([^\"]+)\"", c.get("text_html") or "")}
        bad = sorted(s for s in figs if s.startswith(("/", "http")) or ".." in s or not (export / s).is_file())
        if bad:
            errs.append(f"{f.name}: {len(bad)} figures not in the export, e.g. {bad[:3]}")
    return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="remote", default="lepton-claude:claudiverse/export")
    ap.add_argument("--local", help="an export directory already on this box")
    a = ap.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(a.local) if a.local else Path(tmp) / "export"
        if not a.local:
            subprocess.run(["scp", "-q", "-r", a.remote, str(Path(tmp))], check=True)
        for f in sorted((src / "books").glob("*.json")):
            book_dir = ROOT / "books" / f.stem
            d = json.loads(f.read_text(encoding="utf-8"))
            entries = collect(book_dir)[1] if (book_dir / "book.json").exists() else []
            d["errata_statuses"] = ERRATA_STATUSES
            # a \DPtypo in the preamble is the macro's definition (Wentworth's T001: printed "", corrected "#1")
            entries = [e for e in entries if not (e.get("kind") == "transcriber-marked" and "#" in str(e.get("corrected")))]
            d["errata"] = [site_erratum(f.stem, e) for e in entries]  # [] for a book with none
            place_errata(d)
            f.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
            print(f"{f.stem}: {len(d['problems'])} problems, {len(d['excerpts'])} excerpts, "
                  f"{len(d['equations'])} equations, {len(d.get('errata', []))} errata")
        errs = check(src)
        if errs:
            print("REFUSED:", *errs[:20], sep="\n  ")
            sys.exit(1)
        dest = ROOT / "export"
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest)
    print(f"export/ written and checked ({sum(1 for _ in dest.rglob('*.json'))} files)")


if __name__ == "__main__":
    main()
