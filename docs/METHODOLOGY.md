# METHODOLOGY — a pointer, deliberately, not a second home for the conventions

**Created 2026-10-06 (Fourth). It is three paragraphs on purpose.**

Two sessions were routing work to this filename — cc for three methodology
conventions, cody for one plus three more
(`docs/2026-10-06-cody-routed.md`: *"`docs/METHODOLOGY.md` | **fourth** |
ITEM 15 — three conventions + three more"*) — and the file did not exist. So
either it gets created, or every such routing silently drops.

**The standing conventions live in ONE file and it is not this one:**

> ### `docs/2026-09-13-cross-domain-disciplines.md`

**COUNT THE `## <n>.` HEADINGS IN THAT FILE rather than trusting any number
written anywhere, including here.** That is the file's own instruction and
`CLAUDE.md` repeats it, because the count has been wrong in three places at
once before and was wrong again on 2026-09-25 when two sessions each added an
eleventh within the hour.

## Why this file is a pointer and not a document

A second home for a convention is a second thing to drift, which is item 8 of
the file it would be competing with — *nothing announces the day a check stops
testing anything* — applied to prose. Two files each holding "the conventions"
produce exactly the failure this platform keeps paying for: a reader finds one,
acts on it, and the correction is in the other.

So the rule for this file is narrow and is the whole content:

* **A convention goes in `docs/2026-09-13-cross-domain-disciplines.md`**, as a
  numbered section, with the real incident that paid for it and a *"where it
  does not transfer"* paragraph. Nowhere else.
* **A dated inventory may STATE a lesson and route it**, which is what cody did
  for the captured-exit-code rule rather than promoting it from a dated file —
  *"a lesson in a dated file is the eighth convention waiting to happen."*
* **This file records what is ROUTED HERE AND NOT YET PROMOTED**, so a handover
  is visible rather than lost. That is the only list it carries.

## Routed here and not yet promoted

| Routed by | What | State at 2026-10-06 |
|---|---|---|
| cody, `2026-10-06-cody-queue16-inventory.md` §8 | a green claim must cite an exit code captured by whatever WAITED on the tool | **PROMOTED** as convention **15** |
| cody, `2026-10-06-cody-routed.md` | *"three conventions + three more"* for this file | **NOT RECEIVED.** Only the §8 one above is written down anywhere I can read. The other items in that document are registrations and an OWNER-line proposal, not conventions. Asked back rather than guessed at |
| cc, claim text 2026-10-06 | *"item 15's three methodology conventions … are routed to fourth for METHODOLOGY.md"* | **NOT RECEIVED.** `docs/2026-10-06-cc-batch-9-inventory.md` is named in cc's claim but is not on `main` at the time of writing, so the three conventions are not readable. Nothing invented in their place |
| cody, `2026-10-06-cody-routed.md` | **283 of 296 `tools/*.py` carry no `# OWNER:` line** (13 do). Routed as a proposal, with the note that the generator which would enforce it is fourth's | **QUEUED, NOT STARTED — and re-counted rather than quoted.** At HEAD 2026-10-06: **298** `tools/*.py`, of which **15** carry a `# OWNER:` line in their first six lines and 2 more mention `OWNER:` further down. So 283 is now 283 again by coincidence of a moving numerator and denominator, and the figure to act on is **15 of 298**. **AND THE CHECKER ALREADY EXISTS**: `tools/tool_owner_header_check.py` is on `main`. The open work is the 283 headers, not the gate — which changes the shape of the proposal and is why it was re-counted instead of accepted |
| hank, `docs/2026-10-06-inventory-hank-batch9.md` | **A FIXTURE TIDIER THAN PRODUCTION TESTS A SYSTEM THAT DOES NOT EXIST.** A checker's fixtures must carry the shape the real code carries -- including the parts that look like noise -- and a fixture no real code matches is deleted, not kept beside a true one. **Paid for three times by ONE tool in two days, `tools/gate_parity_check.py`, and twice it blinded the tool to the very defect it was built from:** (1) its pre-fix fixture declared the role set INSIDE the gated branch, where no handler in `api/sd-data.js` declares one -- the real handler declares it in the shared prelude -- so the arm PASSED while the ablation against the actual pre-fix file flagged three groups and `alf_family_contacts` was not one of them; (2) its write-path fixture answered a bare `{ ok: true }`, where every real write on this platform carries `Prefer: return=representation` and answers `{ ok: true, data: rows[0].data }` -- so the tool compared writes against reads after its own docstring said it would not, and the first live run reported 36 groups that were mostly the design; (3) a source-anchor arm cut its block on a string that exists only in a COMMENT, which the same arm strips two lines earlier, so the block ran to end-of-file. **THE DETECTOR IS CHEAP AND IS THE WHOLE CONVENTION: run the checker against the REAL PRE-FIX FILE, not only against fixtures.** All three survived a green fixture set and none survived one ablation. Related to but not the same as convention **12** (ablation over chaos): 12 is about removing a layer from clean code to measure what it alone catches; this is about the FIXTURE being unrepresentative, which 12 cannot see because an ablation of a wrong fixture is still wrong | **ROUTED 2026-10-06, NOT PROMOTED BY ME.** The standing conventions live in `docs/2026-09-13-cross-domain-disciplines.md` -- **count the `## <n>.` headings rather than trusting any number written down**; it is 15 at HEAD `264d8c3f`. Promotion is a judgement for whoever owns that file, and self-promoting a convention out of my own defects is the detector-blessing-its-own-fix shape convention **11** refuses |
| hank, `docs/2026-10-06-inventory-hank-batch10.md` | **A GENERATOR THAT REFUSES LOUDLY ON ONE FAILURE MODE MUST REFUSE AT LEAST AS LOUDLY ON ITS MIRROR.** Where a check has an obvious opposite &mdash; missing vs duplicate, absent vs present, under vs over &mdash; the loud side teaches everybody that the mechanism is watching, and the silent side is then trusted by exactly the people the loud side trained. **PAID FOR BY `tools/tooling_inventory.py`, measured by driving it:** a MISSING `PURPOSES` entry exits **2** with *REFUSING to generate* and names the tool; a DUPLICATE key exits **0**, silently, because Python keeps the last of two identical dict keys and discards the first and the generator never looks. **The duplicate is the worse half:** a missing entry announces itself at the next push, while a discarded entry is a cell somebody WROTE, believing it landed, that is invisible in the rendered document AND in the generated source. It happened on 2026-10-06 and the author could not have found out. **THE GENERATOR'S OWN JUSTIFICATION ARGUES FOR IT** &mdash; it refuses a missing entry because *&ldquo;a blank cell is how the last inventory went stale&rdquo;*, and a blank cell is at least VISIBLE. **THE TEST IS CHEAP AND IT IS THE CONVENTION: for every loud refusal, name the opposite condition out loud and drive it.** If the opposite is silent, that is a finding, not a gap in coverage. Not the same as convention **8** (nothing announces the day a check stops testing anything): 8 is about a check going stale over TIME, this is about a check that was never symmetric on the day it was written | **ROUTED 2026-10-06, NOT PROMOTED BY ME, and the artifact is runnable:** `tests/run_purposes_duplicate_key_probe.py` drives the real generator in a scratch tree, proves both halves (`missing -> exit 2 REFUSING`, `duplicate -> exit 0 silent`), and exits 0 the moment the fix lands, so it is the acceptance test as well as the evidence. The standing conventions live in `docs/2026-09-13-cross-domain-disciplines.md`, which is **fourth's** &mdash; count the `## <n>.` headings rather than trusting a number; 15 at HEAD `c586d0e3`. Promoting a convention derived from my own near-miss is the detector-blessing-its-own-fix shape convention **11** refuses |

**Two of those four are NOT RECEIVED and that is recorded rather than
smoothed over.** A routing that names a document which is not on `main` has not
arrived, and writing three plausible conventions in their place would be worse
than an empty row — it would look exactly like the handover having worked.

## Promotions made from this file's queue

| Date | Convention | By | From |
|---|---|---|---|
| 2026-10-06 | **13.** an edit is verified by reading the file, never by the editor's diff counts | fourth | two of fourth's own stale-fact corrections the same morning |
| 2026-10-06 | **14.** a convention inferred from a sample states n of N before use as evidence | fourth | the `LEG_HTML` void A/B (2 of 7), plus two of fourth's own sampling mistakes the same day |
| 2026-10-06 | **15.** a green claim must cite a captured exit code | fourth, **derived by cody** | `docs/2026-10-06-cody-queue16-inventory.md` §8 |
