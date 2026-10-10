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
  - every erratum's status is one of ERRATA_STATUSES (listed in each book file), and erratum ids are
    unique across the export (each is prefixed with its book's id).
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
    out["found_by_public"] = found_by_public(kind, status, e)
    return out


def found_by_public(kind, status, e):
    """One sentence for a reader: how the erratum was found and what settled it, with no tool or seat names."""
    scan = "scan" in f"{e.get('evidence', '')} {e.get('found_by', '')} {e.get('status', '')}".lower()
    if status == "transcriber_marked":
        return "Marked by Project Gutenberg's proofreaders in the transcription."
    if status == "note":
        return "A note on the text."
    if status == "dismissed":
        return "Reported, then dismissed after checking."
    if status in ("candidate", "probable"):
        return "Found by checking every answer by computation; not yet confirmed against the printed page."
    if kind == "transcription":
        return "Found by checking every answer by computation; a scan of the printed page shows the book is right and the transcription differs."
    if scan:
        return "Found by checking every answer by computation, and confirmed against a scan of the printed page."
    return "Found by checking every answer by computation, and confirmed by the computation shown."


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
        own = [x["id"] for key in ("chapters", "excerpts", "equations", "exercise_sets", "problems", "errata") for x in d.get(key, [])]
        if len(own) != len(set(own)):
            errs.append(f"{f.name}: duplicate ids")
        refs = [r for c in d["chapters"] for key in ("concepts", "excerpts", "equations", "exercise_sets") for r in c[key]]
        refs += [x["chapter"] for key in ("excerpts", "equations") for x in d[key]]
        refs += [p["set"] for p in d["problems"] if p.get("set")] + [r for p in d["problems"] for r in p["same_problem_in"]]
        missing = sorted({r for r in refs if r and r not in known})
        if missing:
            errs.append(f"{f.name}: {len(missing)} references to unknown ids, e.g. {missing[:3]}")
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
            d["errata"] = [site_erratum(f.stem, e) for e in entries]  # [] for a book with none
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
