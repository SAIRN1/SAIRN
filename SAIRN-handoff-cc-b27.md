# SAIRN handoff — cc, batch b27, 2026-10-20

**Six items. Four closed, one half-closed and half-routed, one closed with a
re-capture Michael had to run. Everything is committed and pushed; the tree is
clean and nothing is half-finished.**

The one thing a fresh session should read first is **§4(a)** — `rt_routes`
carries a live constraint that `sql/rt_routes_schema.sql` says was removed, and
the file's own argument is that the constraint would break the route write.

---

## 1. Committed / pushed state

| | |
|---|---|
| Branch | `main` |
| Claim commit | `83ff25a4` — taken **before the first edit**, then re-taken with the Tier A item declared DEFERRED rather than reworded past the matcher |
| **Push range** | **`43d4919b..2111a2d1`, 13 commits** |
| Push | **LANDED, no force.** `git push` rc **0**. `git fetch` then `git rev-list --left-right --count origin/main...HEAD` → **0 0**. Clean tree, **zero stashes** |
| **Overrides** | **NONE.** No `SAIRN_SKIP`, no `SAIRN_GATE_EXEMPT`, no `SAIRN_SEED_GATE`, no `--force`. `docs/BYPASS-LOG.jsonl` gains **no row**. **Five gate refusals were answered at their cause** — see §3 |
| Claims held | **`cc`**, released after this handoff, the report and the digest land |
| Exclusions honoured | `api/`, `tests/`, every `.html`, `docs/CRITICALITY-TIERS.md` **untouched**. Nothing under `.claude/skills/sairn-hover-auditor/` read or written |
| Context at wrap | **47.5% of 1,000,000 — 475,176 tokens, measured** (`context_verify.py --digest-line`). Under the 80% trigger this batch wrote into `CLAUDE.md` |

**Read back from `origin/main`, not the working tree:** the migration and the
probe both exist; `tools/sabotage.py` has **2** of `def verdict`/`def tally`;
`CLAUDE.md` has the *Batch deliverables* heading; the skill has `## The digest`
and the 80% figure; `drive_upload_verify.py` has **10** `max_lines`
occurrences; `docs/fmea/` is **175** entries; the snapshot's `_generated_at` is
**2026-10-20 07:55:45**; the Tier A obligation is there, **open, owned by
fourth**. The user-store mirror of the skill is **identical to origin** after
`tr -d '\r'`.

## 2. What is CLOSED

**Item 1 — the harness false pass, recorded; the ran-check, built; CHECK 5d,
re-driven.** Concept first: *a probe must prove the path under test actually
executed before it reports a verdict.* `docs/defect-density-register.json` gains
one record, **tooling / moderate / probe-control, PR §1.11, five contributing
factors all `done`**. `tools/sabotage.py` gains `verdict()` — the only route to
a verdict, returns `INCONCLUSIVE` unless the subject appears in what the test
path **actually examined**, and refuses `INCONCLUSIVE` as an *input* — and
`tally()`, which lands an inconclusive row in its own bucket, never in passed or
failed, and prints `DO NOT QUOTE n/m`. **15 new arms, selftest exit 0.**
`tools/push_gate_path_scope_sabotage_probe.py` makes the harness durable, with
the plant committed `--no-verify` because **the plant is SETUP** and letting
another hook adjudicate it makes coverage depend on rules the probe is not
testing. **Re-driven: 5 of 5 decided and matched, 0 did not match, 0
INCONCLUSIVE, exit 0.**

**Item 2 — the twelve lost FMEA drafts, regenerated AND committed in one
action.** `docs/fmea` 162 → 174 (the tool counts 175; it includes one entry
`ls` does not, unexamined and noted rather than reconciled). The whole
distinction from b26 is that generate → `git add` → commit happened with no step
in between.

**Item 3 — the four unwritten deliverable rules have a home and one has
teeth.** `CLAUDE.md` gains *Batch deliverables*; the session-handoff skill gains
`## The digest`, **mirrored byte-identical to the user store in the same
action**; `drive_upload_verify.py` gains `--max-lines`, default 30 on the
digest, **lock 45/45 at criteria `2026-10-20.1`** with an ablation showing name,
first line, bytes and sha256 all pass on a 319-line digest. Driven end to end
against a temp directory: a 41-line digest is a finding **and still lands**,
exactly 30 passes, `--max-lines 0` passes it and says so, `--max-lines 5` caps
every kind. Three stale figures re-measured — see §4(d).

**Item 4 — the migration.** `sql/rt_stops_license_hash_composite_fk.sql`.
**Path only, as instructed.**

**Item 5, second half — the register status check, re-derived rather than
quoted.** **One PARTIAL, three LANDED**, unchanged from b26: label growth
PARTIAL (3 of 4 factors `done`); publisher stale-clone LANDED (read from
**origin**, `PUBLISHER_REVISION 2026-10-19.1`, `would_revert()`, the refusal
text); wcag hyphenated-stem LANDED (`--selftest` **58/58** today); bridge nonce
LANDED (`--fixtures` **45/45** today, all four factors `done`). One correction
to b26's write-up: **three** records share `a61abc5ae46e` and `detection_method`
identifies the row, not the sha.

**Item 6 — pushed, no force, confirmed 0 0 against origin.**

## 3. The five gate refusals, each answered at its cause

Not one was skipped. This is the record of what the gates caught.

| gate | what it refused | what satisfied it |
|---|---|---|
| **pre-commit tool entry** | a new `tools/*.py` with no `PURPOSES` entry | two entries written in `tools/tooling_inventory.py` |
| **tool owner** | the probe had no `# OWNER:` line | `# OWNER: cc` added; selftest still 10/10 |
| **derived-docs** | `docs/TOOLING-INVENTORY.md` stale | regenerated; 360→361 tools, UNWIRED 91→92 |
| **credential-sql** | `MISSING_TABLE rt_routes`, `rt_stops` | **the snapshot was re-captured** — §4(a) |
| **tier-a** | the capture names nearly every Tier A resource | `tier_a_review_gate.py --open`, assigned to fourth |

**`credential-sql` could not have been skipped even if I had wanted to**, and
that is worth knowing: that `deny()` carries **no gate id**, and
`gate_skip.py --gates` lists `credential-sql` among **four gates DECLARED BUT
NOT WIRED** — a skip for it is granted and then ignored.

## 4. What is OPEN, and why

**(a) `rtroutes_saved_sane` IS ON THE DATABASE AND THE REPO SAYS IT WAS
REMOVED. The highest-value finding in the batch and it is not cc's to fix.**
The capture's `_constraints.rt_routes` carries four constraints including
`rtroutes_saved_sane CHECK ((saved_seconds IS NULL) OR (saved_seconds >= 0))`.
`sql/rt_routes_schema.sql:14` says, as fourth's b38 reconciliation *"to what
Michael actually ran"*, that it **"was REMOVED before the run, deliberately."**
It is not removed. That file's own argument at :90-102 is that
`api/_lib/routes.js` returns a **negative** saving un-clamped on purpose, with a
test arm asserting it is negative, and it states the consequence: *"With the
constraint in place Postgres would have rejected the ENTIRE upsert and the route
write would have failed."* **So the first negative saving to reach the live
database fails the whole upsert, and the repo documents that as impossible.**

**(b) TWENTY-THREE TABLES LIVE `api/` CODE QUERIES HAVE NEVER BEEN CREATED.**
`schema_snapshot_freshness.py` still exits 1 after the re-capture — **for a
different reason, which is the point**. Staleness is closed (capture 0.2h old at
measurement). What it now reports: **484 created in `sql/`, 461 in the snapshot,
43 absent, 23 of those queried by `api/`**, each resolving to NEVER RUN rather
than to a behind-the-times capture. Supersedes the 430/26 figures cody routed.

**(c) THE SIX b37 TIER A VERDICTS WERE NOT APPENDED.** Not blocked by a claim —
blocked by **attribution**. All 275 records are OBLIGATIONS; there is no record
shape for a verdict that discharges nothing; `--discharge` writes the
**discharging** session as reviewer and cc did not perform fourth's review. The
obvious target is a trap and is named as one: `hank 2026-10-19T19:19:42Z`, owner
fourth, resources **exactly the six**, files `api/bridge.js`'s dispatch, with
hank's own `what` declaring the resource list misleading. **`git diff` on
`docs/tier-a-reviews.json` carried no verdict of mine; the only thing cc wrote
there is an OBLIGATION the gate demanded**, and §5 of the notes explains why
those are different operations.

**(d) Reported and not fixed, all three in other sessions' files:** two
AMBIGUOUS sabotage anchors in `tests/claims/run_registry_claim_sabotage_probe.py`
(tests/ is cody's); `tools/report_only_checks.py` has no entry for the new probe,
so it is **UNWIRED** and nothing runs it (hank holds that file); and
`defect_register.py --check` **still exits 1 on `ce15ddaa6a3c`** — cody's record
citing a sha that exists nowhere in the repo, **already on origin before this
batch**, verified with `git cat-file -t` and `git log --all --grep`.

**And that last one has a consequence worth naming separately, because it is a
coupling nobody designed:** `--reseat` re-runs `--check` after writing and
**reverts every re-seat it just made if the check fails for ANY reason**. It
printed *"RE-SEAT REVERTED … nothing was kept"* twice this batch. So one
session's unresolvable record **blocks every other session's correct repair** —
my own record's sha is still the pre-rebase `aabc1c659b5b` and resolves only by
subject. The revert-on-failure instinct is right in general and wrong at this
granularity: it should revert the re-seat that broke the check, not the ones
that fixed something.

**(e) TWO DIGEST CEILINGS, NOT RECONCILED, and it is Michael's call.**
150 words in `tools/digest_lint.py` versus 30 lines in the dispatches. Measured
over four agents' newest digests: hank b23 **30 lines / 356 words**, fourth b38
**13 / 541**, cody b26 **239 / 2011**, cc b26 **10 / 213**. **Not one meets 150
words.** `AGENTS.md` now states both with the measurements. Retiring the 150 was
not a sweep's decision to make.

**(f) Michael's "33 remain" for the FMEA drafts is NOT REPRODUCIBLE** from
anything in the repo. The register's own measure is **203 defect records with NO
DRAFT AT ALL** and **897 distinct files**; b26's "37 owed from the five b18
records" cannot be re-derived either — exactly **one** record's subject names
b18. Say which measure 33 came from.

**(g) Two cc breaches of its own new rule, named in `CLAUDE.md` rather than
hidden:** b25 wrapped at 81.9%, b26 at 89.0%, against an 80% trigger.

**(h) Carried, unchanged from b26:** nothing notices an uncommitted
post-rewrite reseat; nothing checks a probe for having become too slow; the
egress disclosure and the two stale justifications in fourth's files.

## 5. Exact next step, per open item

| item | next step |
|---|---|
| (a) | **Michael decides, and the fork is real.** Either `ALTER TABLE public.rt_routes DROP CONSTRAINT rtroutes_saved_sane;` in its own `sql/` file — which is what that schema file's header demands for any further change — to match the module's deliberate design; or keep it and clamp in `api/_lib/routes.js`, which re-introduces the 2026-06-18 defect the `saved_seconds` comment exists to prevent. **Not an option: leaving the file claiming the constraint is gone.** `sql/rt_routes_schema.sql` is fourth's. |
| (b) | `python tools/schema_snapshot_freshness.py` and read the 23 — **do not copy a list out of this file**. Each needs its schema file run or its `api/` caller retired. |
| (c) | fourth's, with the question to answer first: *which obligation, if any, does a review of six `docs/CRITICALITY-TIERS.md` ROWS discharge?* Possibly **none** — fourth's own b37 header says the ledger and the review are different artefacts — in which case the verdicts belong in `docs/CRITICALITY-TIERS.md`, and **three of the six say that row's grounds are wrong**. Routed in full in the status registry and in §5 of `docs/2026-10-20-cc-b27-notes.md`. |
| (d) | One `report_only_checks.py` entry from hank; cody re-aims the two anchors or declares their count; **cody reseats or supersedes `ce15ddaa6a3c`** — until then every session's `--check` exits 1 for a reason none of them caused. |
| (e) | One decision from Michael. Until it lands, write to **30 lines** and expect `digest_lint` to report over-length. |
| (f) | One sentence from Michael naming the measure. |
| (g) | Nothing to fix; the rule is now written down and gated for the digest half. |
| (h) | Each needs a claim. For the probe-timing control, copy `SUITE_BOUND` in `tools/guard_ablation.py`, which already treats a timeout as COULD NOT RUN. |

## 6. A note on the rebase, because it cost the most time

Origin moved **five times** during this batch; the clone was 19 behind at the
first push attempt. Two things to carry forward. **A `git add` of a CONFLICTED
file stages the conflict markers** — it did, the register became invalid JSON,
and the register-feed gate correctly reported *"could not be read, so this gate
has checked NOTHING."* Recovered with `git checkout --merge` to recreate the
conflict, then `sairn_rebase_resolve.py`. And **`$?` after a pipeline is the
LAST stage's status**: a `git push ... | tail` loop printed `PUSH-LANDED` over a
failed push. Both are the same shape as the defect this batch recorded.

**Generated documents and ledgers resolve differently and must not be merged the
same way:** `docs/TOOLING-INVENTORY.md` → take upstream whole and **re-run the
generator**; `docs/defect-density-register.json` → `sairn_rebase_resolve.py`
from the common ancestor; reseat-only commits that conflict → **`--skip`**, the
post-rewrite hook reseats afresh at the end.

## 7. Transcript

```
C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cc\e8c8a554-64ac-4e82-acb7-1b611602b98b.jsonl
```

Scratch, session-local, **not** a durable record — b26 lost twelve FMEA drafts
to exactly that assumption, which is why this batch's probe is a file in
`tools/` and not a scratchpad script:

```
...\scratchpad\snapshot_candidate.json   the pasted capture, before loading
...\scratchpad\rb.sh                     the rebase driver, per-file-kind
```
