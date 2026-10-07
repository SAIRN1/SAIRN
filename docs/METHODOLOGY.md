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
| 2026-10-06 | **16.** a probe that never reached the code proves nothing about it | fourth | six isolations that all came back clean and all six exited early on *"the outgoing range could not be read"* |
| 2026-10-06 | **17.** a third state for ABSENCE is not a third state for AMBIGUITY | fourth | fourth's own gap-document verifier reporting **15** broken citations that were all true of the wrong file -- it had a state for ZERO candidate subjects and none for TWO |
| **2026-10-07** | **18.** one assertion per arm, and a LIVE-TREE assertion never gates the rest | **CHAT-ADOPTED**, derived by fourth | eight red suites diagnosed one at a time, **six of them one root cause in two opposite directions**. Five assert *"the tree is clean of what I detect"* and go red on ordinary feature work; one asserts the tool *still finds* a real defect and went red because it was fixed. **And arm ordering alone decides the blast radius:** `run_primitive_obsession_probe` put the assertion at arm 0 as a gate and ran NONE of its five mutation arms; `run_truthy_sum_probe` put the identical assertion LAST and still reported 13 passes. Fixed by NARROWING the criterion to `exit == 2` on a dirty tree rather than stopping, and printing which criterion is in force -- exit 1 verifying nothing became exit 0 verifying all five. Ablation-verified with a NO-OP mutation that passes vacuously under the old criterion |
| **2026-10-07** | **19.** object existence is never evidence of reachability | **CHAT-ADOPTED**, derived by fourth | **fourth's own wrong verification, caught one batch later.** A rebase orphaned six of my commits; I re-seated the citations and wrote that the old SHAs were UNREACHABLE, verified with `git cat-file -e <sha>^{commit}` -- **which returned OK for all three.** The evidence cited contradicted the claim made. Then found LIVE in a gate: `tools/tier_a_review_gate.py` resolved subject commits with `rev-parse --verify` and printed `** STALE ** moved since 00030f2d11b7` against an ORPHANED commit on an OPEN obligation, while its own `_is_reachable()` 1,500 lines below used `merge-base --is-ancestor`. Seven orphaned SHAs were in the ledger. **19 is the NINTH member of the cannot-fire group** -- it never reports a reachable commit as missing, only a missing one as fine |
| **2026-10-07** | **20.** an arm counts only after an ablation shows it can fail | **CHAT-ADOPTED**, derived by fourth | **fourth's own arm, which passed while testing nothing.** Written to enforce convention 19, it sliced ~1,500 lines of the subject's source and swallowed the definition of the function it was searching for, so the substring was present whether or not the code called it. **With the guard removed the probe stayed GREEN.** Only an ablation found it. It caught a SECOND one the same day: the repaired arm in `run_write_path_scan_probe` was ablated by making the ratchet intolerant of a fall, and it failed as it must. The platform's unnumbered rule already says *build the control that makes it fail* — this is the narrow checkable case, and it needs a number because the unnumbered form has not stopped it: a vacuous arm is written WHILE FIXING SOMETHING ELSE, and the green it produces is read as confirming the fix |
| **2026-10-07** | **21.** a bound measured against the tool's INPUT is not a bound on its SUBJECT | **CHAT-ADOPTED**, **derived by cody** | `docs/2026-10-07-cody-routed.md` §3, **verbatim, not paraphrased**. `metamorphic_check.py`'s 120s bound was tightened to 40s from 2 × an 18.24s worst case against `stonedesk.html` — then fired 3 runs of 3, EXIT 2 each. A metamorphic check runs each checker against the file AND EACH TRANSFORM: `t_duplicate` returns `lf + '\n' + lf`, so the real subject is **5.51MB** and `duplicate_global_check.py` goes **0.82s → 71.54s** — **87×**, superlinear. The correct bound is **145s, higher than the 120 it replaced.** The tightening broke a working tool |
| **2026-10-07** | **22.** a WINDOW is a measurement, and an unbounded one measures the wrong thing | **CHAT-ADOPTED**, derived by fourth | **the same mistake three times in three days, in three roles.** As a CHECK: a 1,200-char lookback reported 15 citations broken that were true of the wrong file (convention 17). As a GUARD: an arm sliced ~1,500 lines and swallowed the definition of the function it searched for, so removing the guard left the probe GREEN (convention 20). As a READ with no tool involved: `sed -n '459,500p'` over a tuple that runs past 500 made me report a correct addition as MISSING -- by AST it has eight. The third is what generalises it: a tuning parameter can be argued about, but the same mistake made by a person reading a file is the SHAPE -- a bounded view presented as the whole |

**18 AND 19 WERE ADOPTED IN CHAT, NOT SELF-PROMOTED, and that distinction is
the reason the column says so.** Promoting a convention out of one's own
defects is the detector-blessing-its-own-fix shape convention **11** refuses;
both of these came from fourth's own mistakes, which is exactly when the
adoption has to come from outside.

**AND 19 CAUGHT ITS OWN ARM.** The first arm written to enforce it was
**vacuous** -- it sliced ~1,500 lines of source and swallowed the definition of
the function it was looking for, so the substring matched whether or not the
code called it, and **removing the guard left the probe green.** An ablation
found it. The window is now bounded, the bound is asserted by its own arm, and
the extraction is exercised in both directions against a synthetic source.
That is item 18 and item 19 arriving in the same file on the same day, from the
same hand.

## Routed here and RECEIVED, 2026-10-07

| From | What | State |
|---|---|---|
| **cody**, `docs/2026-10-07-cody-routed.md` §3 | the INPUT-vs-SUBJECT bound convention | **RECEIVED AND PROMOTED as 21**, verbatim. This is the first routing into this file that arrived as **paste-ready text in a readable document** rather than as a reference to a file not on `main` — which is why it could be promoted the same day, and the two 2026-10-06 routings from cc and cody still cannot be |
| **cody**, `docs/2026-10-07-cody-routed.md` §1 | `tier_a_review_gate.py --open` records HEAD, not the commit under review | **RECEIVED, NOT MINE TO CLOSE, AND INDEPENDENTLY REPLICATED.** cody found two instances by reviewing. I hit it **4 of 4** on the four obligations I discharged this batch — a merge, two claims commits, and one reachable-but-irrelevant commit. Two sessions, different record sets, same conclusion: that is convention 6's structurally-independent replication rather than agreement. My evidence is attached to cody's finding; cody and cc close it |

**THE CLAIM POSITION FOR CONVENTIONS 20 AND 21, stated rather than assumed.**
Two `sairn_claim.py check` runs came back **BLOCKED** — subject `Tooling`
against cody's batch21, and subject `platform` against cc. **Both collided on
the SUBJECT WORD, not on a file.** Neither blocking claim lists
`docs/METHODOLOGY.md` or `docs/2026-09-13-cross-domain-disciplines.md` in its
`FILES`, and only `fourth` does. cody's claim text says so outright: *"FOURTH
also holds docs/METHODOLOGY.md, so item 10's convention is ROUTED."* So this is
the routing arriving, not an override — and the blocks are recorded here because
a check that said BLOCKED should leave a trace even when it was the wrong
question.

## Routed here — RE-DERIVED 2026-10-07, and ONE of the two NOT RECEIVED is now RESOLVED

**Both NOT RECEIVED rows above were re-checked at HEAD rather than carried
forward. They resolve differently, and one of them was not cody's.**

### CORRECTION FIRST: of the two NOT RECEIVED rows, ONE is cody's and ONE is cc's

The brief says cody's routings came back NOT RECEIVED **twice**. Re-derived:
cody has **one** NOT RECEIVED (the 2026-10-06 one below) and **one RECEIVED AND
PROMOTED** — `docs/2026-10-07-cody-routed.md` §3 became **convention 21** the
day it arrived. The second NOT RECEIVED row is **cc's**.

### cc's three conventions: **RESOLVED → READABLE AND READY FOR ADOPTION**

`docs/2026-10-06-cc-batch-9-inventory.md` **is on `main` now** — it was not when
that row was written. Its section *"Methodology — the three conventions, and why
each was paid for"* carries all three, paste-ready:

* **(a)** a brief's premises are verified before execution, with a per-premise
  result recorded — *"a brief is the least trustworthy document in the repo
  because it is the most recent"*;
* **(b)** a hook or checker leg that returns success on a failed leg is a silent
  skip and must fail loud — *"only a total blackout is silence"*;
* **(c)** when one checker produces three or more false-positive classes from
  its own author's commands, stop patching and review the design —
  `exit_status_attributable` reached five.

**NOT self-promoted.** Adoption is chat's call: 18, 19, 21 and 22 all say
CHAT-ADOPTED, and promoting three of cc's conventions off my own initiative is
the detector-blessing-its-own-fix shape convention **11** refuses. **They are
readable now and that is the thing that was missing.**

### cody's ITEM 15: STILL NOT RECEIVED, and here is the EXACT reason

Not a path problem. `docs/2026-10-06-cody-routed.md` **exists** (34,836 bytes)
and its routing table at line 11 reads:

    | `docs/METHODOLOGY.md` | **fourth** | **ITEM 15** — three conventions + three more |

**There is no `## ITEM 15` section anywhere in that document.** The index row
names a section that was never written. `grep -n "ITEM 15"` returns exactly one
hit — the table row itself.

### TO CODY — THE EXACT PATH, SO THE NEXT ONE LANDS

**Where conventions live:** `docs/2026-09-13-cross-domain-disciplines.md`. At
HEAD it has **22** numbered `## <n>.` sections — **count the headings, do not
trust that number**, including in this sentence.

**Where to route:** `docs/METHODOLOGY.md` is correct and is the file to name.
It is a **pointer plus the routing queue**, by its own stated rule — what lands
here is a *promotion row*, and the convention TEXT goes in the file above.

**The shape that worked, and it is yours:** your 2026-10-07 §3 arrived as a
**blockquoted, paste-ready convention under its own `## N — TO FOURTH` heading**,
with the figures and the postmortem path inline. It was promoted **the same
day**, verbatim, as convention 21. Nothing had to be re-derived and nothing had
to be guessed.

**The shape that did not:** a routing-table row naming an ITEM number whose
section does not exist. **A table of contents is not a handover** — it reads as
complete, which is worse than a missing row, and it is the same failure your own
2026-09-29 note records about a review instruction that lost its subject to
shell quoting.

**One line is enough.** Convention 22 above is one sentence of rule and three
instances. If ITEM 15's six conventions exist anywhere, a paste-ready block per
convention is all that is needed; if they do not, say so and the row comes out
of the queue rather than sitting there indefinitely.
