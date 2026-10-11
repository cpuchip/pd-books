# How this was built

Michael Stufflebeam owns this repository and rules on it. The errata, the export and the tools were made by a
team of AI agents, each a Claude Code session with its own charter, working with him. The errata and the commit
messages name these agents (the "seats"). The names stay in on purpose (decision 84), so anyone can see how each
correction was found and use the same method on another book.

## The pipeline

The books are read by the claudiverse, an instance of [pg-ai-stewards](https://github.com/cpuchip/pg-ai-stewards)
that uses only Anthropic models. pg-ai-stewards keeps the agents, their work queue and their spending as rows in
Postgres, so every model call behind an entry has a recorded cost.

For each book (the Thompson entries came from an earlier pilot that used Claude Sonnet 5.5 as the reader):

1. Claude Haiku 5.5 reads each exercise set into records: the problem and the printed answer, quoted exactly from
   the source, with the mathematics written out for a computer-algebra system. A gate flags any record whose
   quotes are not in the book.
2. Our computer-algebra checker (judge.py) checks every answer: exact rational arithmetic and 50-digit sampling at
   seeded points, with a proof where the degree allows one.
3. Claude Opus 5.5 reads each record the checker flags, with the set's text, and classifies it: a reading mistake
   (corrected and checked again), a limit of the checker, a transcription slip, a misprint in the book, or unclear.
4. A seat confirms a transcription slip on a scan of the edition, and the entry names the scan and the leaf.
   A misprint in the book is confirmed by the computation that shows it; the Boyden misprints were also read
   on the scanned page. Until then an entry is a candidate.

Problems with one numeric answer also get worked calculator steps. Haiku drafts the key sequence, and stu32-calc
(the STU-32 calculator's core, run in a container) executes it. A sequence reaches `export/` only when the core's
value matches the printed answer and an independent 50-digit computation, and the records checker from
[stu32-tutor](https://github.com/cpuchip/stu32-tutor) accepts it. Each one names the commits of the core it ran on.

## The seats

Michael decides what goes upstream (the transcription slips in Wentworth and Boyden were sent to Project
Gutenberg with his approval). The seats did the work:

- **qwenniverse-fermion** runs the claudiverse, wrote the reading pipeline and the tools here, and read the scans
  that settle the Wentworth and Boyden entries.
- **abacus** keeps the list of candidates whose page needs reading, and confirms entries as a second reader.
- **tutor** builds stu32-calc and the records checker, and found one of the Thompson entries while testing
  stu32-calc.
- **primer** builds learn.cpuchip.net, the site `export/` is made for.
- **basecamp** coordinates the seats and relays Michael's rulings.

## The numbers

Michael's rulings are numbered ("decision 84") and recorded by abacus. An export commit names the commit of the
pipeline that produced it ("claudiverse 412d176"); that repository is private, and the hash records which version
of the pipeline made the data.

## The rules the work kept

- Every quote is checked against the source before a record is used.
- Every answer is checked by computation before Opus is asked to classify it.
- A correction is filed with its evidence: the computation, or the scanned page that shows it.
- Checks are tested against planted faults before they are trusted.
