# The five logged mistakes, reviewed — one was live, four were not, and reviewing them found two more

**2026-10-05 (Cody).** `docs/2026-10-05-cody-queue13-report.md` §9 logged five of
my own mistakes. The instruction was to review each, confirm whether any
produced a live defect beyond what is already fixed, and close out the ones that
did not.

**ANSWER: ONE of the five reached `origin/main` and it is now repaired. Four
never left this session.** And the review itself turned up **two more** that the
original five did not cover, both of which DID reach main — so the honest count
for the day is **seven, of which three were live.**

---

## THE FIVE, EACH CHECKED AGAINST WHAT ACTUALLY SHIPPED

### 1. A register field EATEN BY THE SHELL — **LIVE, REPAIRED, CLOSED**

`` `changed` `` was written inside bash backticks in a double-quoted `printf`,
the shell ran it as a command substitution, printed `changed: command not found`
to the terminal, and the record landed with a gap exactly where its subject
belonged.

**This one reached `origin/main`.** It was repaired in place the same session
and the incident is written into the field itself rather than only into the
commit message.

**VERIFIED CLOSED TODAY** — the field now reads whole, and
`tools/defect_register.py --check` passes at 437 records. **NOT a product
defect**: the damage was to one record's prose in a register, so nothing
computed from it was wrong, only less readable. Severity is honestly LOW and I
recorded it at that.

**AND THE GENERALISATION IS NOT CLOSED.** `tools/eaten_substitution_check.py`
exists for exactly this and its subject is **commit MESSAGES, not JSON field
values**, so it could not have caught this one and still cannot. That is a scope
gap in a real tool, not a mistake of mine, and it is named in §7 of the
inventory rather than fixed here.

### 2. Two of my own fixture arms GREEN on a dead rule — **NOT LIVE, closed**

A shape-A fixture resolves its write set through a different inline regex and
never touches `WRITE_VAR_RE`; a generic read that *resolves* never touches
`READ_VAR_RE`.

**Never shipped.** `tools/dead_rule_sweep.py --tool write_without_readback_check.py`
reported both rules DEAD while my arms were green, I replaced the fixtures, and
the commit that landed carries the corrected ones. **Nothing was published with
the wrong arms.**

**Re-verified today:** that tool reports 7 of 7 rules exercised, 0 dead.

### 3. A driver TRUNCATED ITS OWN EVIDENCE to 500 characters — **NOT LIVE, closed**

The Gate-1 driver stored only the last 500 characters of each tool run, so
`missing` for SAIRNscape was cut off mid-list.

**Never shipped and never published.** It was caught before the figures were
written down, the driver was fixed to keep the whole stdout, and the sweep was
re-run from scratch. The published figures came from the second run.

**But it is the one of the five I would still call a near miss**, because the
truncated read was *plausible*: "1 missing table" is a believable answer and
nothing about it looked short. The driver is a scratch script and not a tracked
tool, so there is no test to add; what changed is that it keeps full output.

### 4. An idempotency check counted COMMENTS as statements — **NOT LIVE, closed**

A `create table` count flagged 5 of 18 schema files as not fully idempotent.
Every one of the 18 contains a comment with the words `create table if not` /
`exists` split across two lines, which the count read as a second statement.

**Never shipped.** Caught by reading the two flagged files directly before
publishing, and the Gate-1 document records the false flag rather than the
figure. **Had it shipped, Michael would have been told to hand-edit five files
that are already safe to re-run.**

**AND IT RECURRED IN THE SAME FAMILY HOURS LATER, WHICH IS THE PART WORTH
KEEPING.** Making `declared_tables()`'s prefix optional made a comment reading
*"see create table if not exists in the other file"* yield the table name `in`.
**Same class, same day, different tool.** That one was caught by a probe arm
rather than by eye, and the comment stripper landed in the same commit as the
widening. See item 7 below.

### 5. A word boundary on BOTH ENDS broke `not touch` matching NOT TOUCHING — **NOT LIVE, closed**

**Never shipped.** Caught by driving all eight documented wordings before
committing; the shipped rule anchors on the front only and arm E4 of
`tests/run_claim_matcher_probe.py` pins the reason.

**Re-verified today:** 30 arms, 0 failed.

---

## TWO THE ORIGINAL FIVE DID NOT COVER, AND BOTH REACHED main

### 6. THE GATE-1 FIGURES WERE PUBLISHED AS COUNTS AND THEY WERE FLOORS — **LIVE**

`docs/2026-10-05-gate1-live-migration-signed-in.md` states *"113 (app, schema
file) pairs"*, *"402 declared tables"*, *"24 MISSING"* and *"18 SQL files for
Michael"*, with no disclosure that the sweep's glob was
`sql/<app-prefix>*schema*.sql` and therefore read **113 of 147** schema files.

**That document is on `origin/main` and a reader has no way to tell from it.**
Corrected in `docs/2026-10-05-gate1-missing-table-triage.md`: 134 files, 430
declared, 295 provisioned, **26** missing, **20** SQL files.

**THE DOCUMENT'S OWN CLOSING SECTION MAKES IT WORSE, NOT BETTER.** It lists
what it does not establish and the list is accurate — and "the sweep read every
schema file" is not on it, because I did not know it was a claim I was making.
**An unstated assumption does not appear in a limits section**, which is the
one kind of gap a limits section cannot close.

**Severity: the figures understated the work owed, so the error direction was
"more missing than reported" — not "clean when it was not".** That is the less
dangerous direction and it is still a published count that was a floor.

### 7. MAKING A PATTERN WIDER MADE COMMENTS REACHABLE — **caught before it landed, but it is item 4's class recurring**

Covered in item 4 above. Recorded as its own entry rather than folded in,
because the two have different detection stories: item 4 was caught by eye and
this one by an arm written in the same change. **The arm is the difference and
it is the reason this one is not in the "live" column.**

---

## WHAT THE REVIEW CHANGES ABOUT THE TALLY

| | logged | reviewed |
|---|---|---|
| mistakes | 5 | **7** |
| reached `origin/main` | 1 (stated) | **3** |
| still open | 0 (stated) | **0** — item 6's correction is published |
| fixed in a tool rather than only in prose | 2 | **4** |

**THE PATTERN ACROSS ALL SEVEN IS NOT CARELESSNESS, IT IS SCOPE.** Five of the
seven are a reader, a counter or a matcher applied to a corpus wider than the
sample it was written against:

- fixtures from 2 pilot documents, run over 22 (gap ledger)
- a `create table` count written for one comment style, run over 18 files
- a prefix-requiring regex written for one spelling, run over 147 files
- a glob written for one filename convention, run over 147 files
- a word boundary written for one marker, run over eight

**And in every case the failure was QUIET.** Not one of them raised an error:
they returned a smaller number, a shorter list, or a green arm. That is the
eighth cross-domain discipline and the measurement I should take from this day
is that **I verified each tool against its own fixtures and did not verify the
fixtures against the corpus.**

The one mechanical change that follows: **a sweep must print its own coverage.**
Files read against files on disk, documents parsed against documents matching,
rules exercised against rules compiled. Three of the five scope mistakes above
would have been one printed line each. That is recorded in the provisioning
defect's `recurrence_open` as NOT built, because the sweeps that need it are
driver scripts rather than tracked tools and inventing a home for it here would
be the wrong fix.

---

## WHAT THIS REVIEW DOES NOT ESTABLISH

- **That seven is the count.** It is the count of mistakes I noticed and wrote
  down. Items 6 and 7 were found by reviewing the five, which is evidence the
  list grows when looked at rather than evidence it is now complete.
- **That the four non-live ones could not have shipped.** Three were caught by
  something mechanical and one by reading. The one caught by reading is item 4,
  and it recurred the same day.
