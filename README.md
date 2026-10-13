# pd-books

Public-domain math and physics books we read closely, each kept as acquired with the errata we
collect beside it. The aim is a list of corrections other readers (and Project Gutenberg itself) can
use, with the evidence for each one attached.

    books/<slug>/source/       the files exactly as acquired, with SHA256SUMS
    books/<slug>/book.json     title, author, edition, source file and URL
    books/<slug>/found.json    errata we found ourselves, and candidates, each with its evidence
    books/<slug>/evidence/     what settled an entry (a crop of a scanned page, for one)
    books/<slug>/errata.yaml   generated: the source's transcriber-marked errata plus found.json
    export/                    the books as data for learn.cpuchip.net (chapters, excerpts,
                               equations, problems with checked answers, and how the books relate)
    tools/make_errata.py       builds errata.yaml from the source, so the list cannot drift from it
    tools/publish_shelf.py     brings the export in and refuses one that fails its checks

## Kinds of erratum

- `transcriber-marked`: Project Gutenberg's proofreaders marked a misprint in the original as
  `\DPtypo{printed}{corrected}` in the source.
- `found-by-us`: a misprint we found and confirmed, with the computation or algebra that shows it.
- `transcription`: the transcription differs from the printed page and the book itself is right,
  settled against a scan named in the entry.
- `candidate`: reported, not yet confirmed.

## How errata are found

The problems in each book are read into records (the problem and the printed answer, quoted exactly from
the source) by a language-model pipeline, and every answer is then checked by computation: exact
rational arithmetic and 50-digit sampling at seeded points, with a proof where the degree allows it. A
record whose answer fails the check is classified by a second model. A transcription slip is confirmed
on a scan of the printed page, and a misprint by the computation that shows it; until then the entry is
a candidate. An entry says who found it and how it was confirmed. [How this was
built](docs/how-this-was-built.md) names the agents who did this work and the rules they kept.

## Licence

- The files under `books/*/source/` are unmodified Project Gutenberg files. They carry the Project
  Gutenberg License and trademark text, and redistributing them follows that license.
- Everything else that is data (errata, evidence, the export) is dedicated to the public domain under
  CC0 1.0 (`LICENSE-CC0`), so anyone can fold the corrections into their own copy with no conditions.
- `export/images/` holds the books' own figures, taken from each book's Project Gutenberg files (a PDF or
  EPS figure rendered to PNG). The figures are in the public domain in the USA, as the books are.
- The tools are under the MIT License (`LICENSE-MIT`).
