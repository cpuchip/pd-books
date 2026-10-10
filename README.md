# pd-books

Public-domain books we read closely, each kept as acquired with its errata collected beside it.
Started 2026-10-09 on Michael's word: "With these open-source books, if we find errata ourselves
lets create a books repo and put the original source and the collected errata!"

    books/<slug>/source/       the files exactly as acquired, with SHA256SUMS
    books/<slug>/book.json     title, author, edition, source file and URL
    books/<slug>/found.json    errata we found ourselves, and candidates, each with its evidence
    books/<slug>/evidence/     what settled an entry (a crop of a scanned page, for one)
    books/<slug>/errata.yaml   GENERATED: the source's transcriber-marked errata plus found.json
    tools/make_errata.py       builds errata.yaml from the source (so the list cannot drift)

Kinds of erratum: `transcriber-marked` (Project Gutenberg's proofreaders marked the original's
misprint in the source as \DPtypo{printed}{corrected}), `found-by-us` (confirmed, with the
computation or algebra that shows it), `transcription` (the transcription differs from the printed
page, settled against a scan named in the entry; the book itself is right), and `candidate`
(reported, not yet confirmed).

The sources are unmodified Project Gutenberg files and carry the Project Gutenberg License and
trademark text; redistributing them follows that license. The errata files are ours.

Visibility: private until Michael decides (the books are public domain; the errata are meant to
be useful to others).
