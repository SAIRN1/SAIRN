---
name: sairn-context-budget
description: Work correctly against data that does not fit — large files, long outputs, paginated exports, and a session window that ends. The core rule is that a TRUNCATED READ IS INDISTINGUISHABLE FROM A COMPLETE ONE and will become a confident wrong claim unless something forces the check. Trigger before reading or fetching any file over ~1MB, before quoting a count from any export or command output, before writing a large file, when piping output through head/tail/grep, when a tool result is persisted to disk instead of returned, and before a long session ends. Every incident below is a real SAIRN case where partial data was reported as whole.
allowed-tools: Read Grep Glob Bash
---

# SAIRN Context Budget

**Installed 2026-08-30.** Rebuilt as a SAIRN original from the settled
list in `docs/2026-08-30-skill-rebuild-classification.md`. Every factual claim
machine-verified against this codebase before install.

**Renamed from `token-budget-advisor`, deliberately.** The generic skill is
about managing a token allowance. SAIRN's actual, repeated, documented failure
is narrower and worse: **partial data arriving silently and being reported as
complete.** The rename is the finding. It was classified "build last, moat is
tacit" — the moat turned out to be written down in five places already, just
never collected.

---

## The one rule

**A truncated read looks exactly like a complete one.** No error, no warning,
often an HTTP 200. Every incident below is that same shape, and in each one a
confident number or claim was produced from partial data.

The defence is never "be careful". It is **an independent check on the size or
completeness of what came back**, run before the data is used.

---

## 1. A large file can return HTTP 200 and no content

GitHub's Contents API **silently fails on files over ~1MB** — 200 response,
empty `content` field, no error. Found 2026-07-26 against `stonedesk.html`:
**2,049,441 bytes, decoded to 0 bytes, zero warning.**

Guardian's scan procedure now says the opposite of what it originally said, and
carries the check: use `raw.githubusercontent.com` for anything large, then
`wc -c` the result and compare against the size the directory listing reported.

**The general form:** after any fetch of something big, assert the size before
parsing it. A zero-byte or suspiciously-small result is the expected failure,
not an unlikely one.

## 2. A truncated export becomes a documented fact

`full_crud_truncate_sweep_2026-08-24.sql` records it: *"Michael's SQL client had
a row limit; the first export (100 rows) was confirmed truncated by
cross-checking against tables already known to exist."*

That truncated export produced a count of **~78** tables holding a DELETE grant.
The real live count was **135** — a **57-table gap**, recorded in
`unused_delete_grant_revoke_2026-08-24.sql` — and the wrong number had already
been written into `docs/SAIRN-OPEN-WORK-INDEX.md` as though it described the
database.

**Both files carry the incident, and that is itself the point:** the second one
quotes the first because the same root cause was found *independently* by
another session. One truncated export produced wrong numbers in two places
before either noticed.

**The tell that caught it:** a count landing suspiciously near a round number
(100, 50, 1000) is a cap, not a measurement. Re-run with an explicit high limit,
or count server-side with `count(*)` rather than counting returned rows.

## 3. Writing large data truncates too, and the write reports success

A bash heredoc write of a multi-megabyte file containing multi-byte Unicode
**truncated a 2MB file to 1.7KB with no error.** Caught only because file size
was re-checked immediately after writing.

Rule: never heredoc-write a large or Unicode-bearing file — use the file tools
or a Python binary write — and **`wc -c` after every large write**, before
trusting it.

## 4. Your own pipe is the most likely truncator

**2026-08-30, first person.** Running the platform's missing-DOM-target check,
I piped it through `tail -6` and reported **6 missing targets**. The real count
was **163**. I had truncated my own output and reported the truncation as the
finding.

Caught only by re-running against a baseline and noticing both numbers were
identical — which is the check that should have run first.

**Rule:** `head`, `tail`, `| head -n`, and result-limit parameters are display
conveniences. **Never quote a count that came through one.** Read the tool's own
summary line (`MISSING_TARGETS:163`, `TOTAL_BLOCKS:128`) or count without a
limit, then truncate for display only.

## 5. A persisted tool result is not a read result

When a command's output is too large it may be **written to a file instead of
returned** — this session had a 114.8 KB output persisted that way, with only a
2 KB preview shown.

A preview is not the data. Either grep the persisted file for the specific thing
needed, or narrow the command and re-run. **Do not answer from the preview** and
do not assume the visible portion is representative — it is the first 2 KB, not
a sample.

## 6. Narrow the command, do not widen the read

The cheapest fix for almost all of the above is asking a smaller question.

- `grep -c` when the answer is a count; don't read the file to count by eye.
- Read the specific line range, not the file, when the location is known.
- Let a purpose-built tool emit its own summary line and read that.
- One targeted query beats one broad export plus manual filtering, and it
  cannot be truncated in the same way.

`sairn-perf-profiler`'s rule applies here too: **never state a number you did
not measure.** The corollary is that a number you measured *through a truncating
pipe* is one you did not measure.

## 7. The session window ends, and context does not persist

*"Chat/session context does not persist reliably across long sessions or tool
switches"* — Guardian's own words, and the reason the handoff convention exists
at all.

Two consequences that are not optional:

- **Write the handoff before capacity runs low, not when it does.** A handoff
  is not written until it is **committed in the same action** — a local-only
  handoff is invisible to every other clone.
- **Durable findings go in the repo, not the transcript.** A conclusion that
  exists only in a session's context is gone at the next compaction. This is
  the same reason a fix that ships without a written trace costs a future
  session a re-scope.

## 8. Size ceilings are a budget problem before they are a design problem

`sairn-software-architect` carries a file-size ceiling, and `stonedesk.html` at
~2.2 MB is past it. That matters here because **every large file is a truncation
risk on every read** — it is why the Contents API incident happened to that file
specifically, and why the HR module was built as a separate page rather than
appended to it.

When a file is large enough to be awkward to read, that is evidence about the
file, not just about the reader.

---

## Before quoting any number or claiming any read was complete

1. Size-checked after fetching or writing anything large (`wc -c`), against an
   expected value.
2. No count quoted that passed through `head`, `tail`, or a result limit.
3. Counts near 100/1000 treated as caps until disproved.
4. Persisted/oversized tool output grepped or re-run narrowly — never answered
   from the preview.
5. Where a tool prints its own total, that total is what is quoted.
6. Anything that must survive the session is committed, not left in context.

---

## What this does NOT cover

- **Model context-window sizing or cost estimation.** The skill it replaces was
  about a token allowance; this one is about truncation. If the question is
  literally "how many tokens is this", that is a counting problem, not this.
- **Chunking strategies for long documents.** Rule 6 says narrow the question
  instead; where chunking is genuinely required, that design is unspecified
  here.
- **Database or API pagination correctness.** Rule 2 covers a truncated export
  being mistaken for a whole one; it does not tell you how to paginate.
- **The 2MB single-file ceiling as an architecture problem** — rule 8 notes it
  only as a truncation risk. `sairn-software-architect` owns the design call.

**Precedence.** Replaces `token-budget-advisor`, and the rename is deliberate —
see the header. Adjacent: `sairn-perf-profiler` (never state a timing you did
not measure — same discipline, different quantity) and `sairn-session-handoff`
(rule 7's obligation, in full).
