# SAIRN handoff — cc, batch b24, 2026-10-19

**Subject:** the tier checker's name list becomes a module-declared property;
the Tier A review of `rt_routes`/`rt_stops`; two open-work rows corrected from
source; the context red-flag threshold becomes per-population; a path manifest
and pre-push scope check. Written at a point where nothing is half-finished.

---

## 1. Committed / pushed state

| | |
|---|---|
| Branch | `main` |
| Start of batch | `5ce4a9d8`, pull already up to date, clean 0/0, zero stashes |
| Claim commit | `ba62b227`-equivalent for this batch — taken **before the first edit**, which b23 did not do |
| **Work commit** | **`38bbd455`** — `feat(scope): a name list becomes a property, a threshold becomes a population, and a push learns its own scope` |
| Gate requirements | `caf61be0` — the inventory entry, the Tier A obligation, the gate's own rows |
| Gate bookkeeping | `91f9d7d3`, `46cce6f8` |
| Push | **LANDED, no force.** `HEAD == origin/main`, **0 ahead / 0 behind**, clean, zero stashes — confirmed by `git fetch` then `git rev-list --left-right --count origin/main...HEAD`, i.e. read from the remote rather than from the local ref. |
| Overrides used | **none.** No `SAIRN_SKIP`, no `SAIRN_GATE_EXEMPT`, no `SAIRN_SEED_GATE`. `docs/BYPASS-LOG.jsonl` gains no row. **Three gates refused and all three were satisfied, not skipped** (`external-files`, `tier-a`, `derived-docs`). |
| Claims held | **`cc`** — held at the time of writing, released after this handoff, the report and the digest land. Declared files: `tools/`, `docs/sairn-path-manifest.json`, `docs/tier-a-reviews.json`, `docs/SAIRN-OPEN-WORK-INDEX.md`, this batch's docs. |
| Instructed exclusions honoured | `api/` **not touched**. `tests/` **not touched**. No `.html` file touched. `~/.claude/settings.json` **not touched** — item 4 changed only `tools/sairn_status_line.py`, and item 5 used the pre-push hook that already exists. |

**Read back out of origin** rather than off disk:
`origin/main:tools/criticality_tier_check.py` carries `declared_app`,
`registry_property_arms` and the derived arm count;
`origin/main:tools/sairn_status_line.py` carries `RED_AT_DEFAULT = 70`,
`RED_AT_BUILD = 80` and `red_at`;
`origin/main:docs/sairn-path-manifest.json` has 4 populations, 3 auditor
paths, 14 ledgers and an **empty** `assigned_overrides`;
`origin/main:tools/sairn_push_gate_hook.py` names `path-scope` 7 times; and
the `rt_routes` record reads `status: reviewed`, `reviewer_session: cc`.

## 2. What is CLOSED

**Item 1 — the tier checker. CLOSED.** The skip is now a property each module
declares (`app:` in its own `module.exports`), not a name list. **18 → 19
registries, 394 → 401 resources, 14 → 6 problems; 8 cleared, 0 introduced**,
computed by differencing the finding sets. Lock 6/6 → **12/12**, with the
printed count now derived rather than `len(FIXTURE_CASES)`. Fourth's two
questions decided: the skip is a property, and `routes` **stays** its own
registry file — now a choice rather than a workaround.

**Item 2 — the Tier A review. DISCHARGED**, `reviewer_session: cc` against
fourth's `2026-10-19T18:12:04Z`. Verdict: sound on confidentiality as designed,
with one HIGH finding that cannot be closed here because the code that would
close it has not landed. The landing obligation for the `api/sd-data.js`
handler is an **open-work row** (not a `--open` record, because `--open` opens
an obligation for the *current* session's changes).

**Item 3 — the two index rows. CORRECTED from source.** The `dnt_rollup`
measurement is now right, and the malformed row's stray pipe is gone. Shards
regenerated, `open_work_shard.py` **CLEAN at 818 rows**. One part I could not
reproduce is in §3(d) below.

**Item 4 — the red-flag threshold. CLOSED.** Build agents 80, every other
population **unchanged at 70**, keyed on the per-clone marker. Lock 26/26 →
**38/38**, with an ablation on the value (5 arms fail) and an ablation on the
**identity alone** (the same 75% transcript is still red under `hover`).

**Item 5 — the path manifest and pre-push scope check. CLOSED.** Gate id
`path-scope`, `WIRED`, 11 skippable gates. Lock **31/31**. Driven end to end in
a provisioned worktree: an out-of-scope `api/` edit is **refused**, the same
push shows its 12 in-scope paths, an auditor-scope edit is **refused by the
AUDITOR rule**, and emptying `auditor_paths` makes the refusal stop — the
ablation.

**Item 6 — push. CLOSED.** See §1.

## 3. What is OPEN, and why

**(a) The HIGH finding from the Tier A review — `rt_stops.license_hash` has no
tie to its route's.** `rt_stops` carries both `license_hash` and
`route_id references rt_routes(id)` and the schema has **no composite FK, no
check, no trigger** requiring them to agree. `idx_rtstops_license` exists so a
reader can scope by that column, so a stop written with licence A under a route
of licence B is visible in A's scope while belonging to B's itinerary.
`api/_lib/routes.js` never touches `license_hash` and neither consumer sends
one, so **only the unlanded handler can get this right and nothing will catch
it if it does not.** Recorded as an open-work row with the deciding test
written down before it can be run.

**(b) The MODERATE finding — Tier A addresses egress to Google, undisclosed and
unbounded.** `driveMatrix` POSTs every stop address to
`routes.googleapis.com`; `X-Goog-FieldMask` limits what comes back, nothing
limits what goes out, and `stops.length < 2` is a floor with no ceiling. Not a
code defect — a drive-time optimiser must send addresses somewhere — what is
missing is the **disclosure and a stated bound**.

**(c) DECISION-NEEDED: cody and `.html`.** cody pushed `.html` repeatedly under
Michael's explicit assignment while the split gives `.html` to fourth.
`assigned_overrides` is the declared route and it is **empty**, so **cody
pushing `.html` is refused today**. Flagged, not decided.

**(d) The contradiction in item 3 I could not reproduce.** Measured: the paired
row's pipe count is already 8 and its claims do not conflict with its
neighbour's. What *is* wrong is the first row's stray literal pipe — hank's b21
diagnosis exactly — and that is what I fixed. The row numbers in the routing
notes are file line numbers that have drifted (449 → 453), so I identified the
pair by **content** rather than by number. **I did not invent a contradiction
to satisfy the instruction.**

**(e) Two stale justifications now pointing the wrong way, both fourth's.**
`api/_resources/routes.js`'s header argues the file exists *because* of the
name list item 1 removed, and quotes the tuple. The register's `routes` cell
carries the same stale citation **and** still says `sd_field_stops` is at B/B
and FLAGGED, which fourth's own b35 superseded. Routed, not edited.

**(f) `tests/run_criticality_tier_probe.py` is RED, 8 failed, pre-existing.**
Baseline measured by writing origin's own copy of the tool back in a
`try/finally` and driving the probe: identically 8, same arms. It already has
four rows in `docs/known-red-suites.json`.

**(g) Three pre-existing near-duplicate index pairs** at lines 147/148, 258/260
and one more — none at the lines I touched, all in hank's and cody's rows.

**(h) Six remaining tier-checker problems**, all in `docs/CRITICALITY-TIERS.md`
which fourth holds: four `COUNT` drifts, one `LIST MISSING`, one `NO TIER`.

**(i) Carried from b23, still not started:** nothing notices an uncommitted
post-rewrite reseat, and nothing checks a probe for having become too slow to
run.

## 4. The FMEA position

**11 drafts done in b23, 33 remain.** 16 of the 55 files cited by hank's five
b18 records now have a draft; 39 do not, 33 of those being real source/test/SQL
rather than evidence logs. `docs/fmea/` holds **163** drafts in total.

**Where I stop next:** twelve of the 33 are the identical
`*_audit_log_schema.sql` files, one of which is already drafted as the
representative. **The open judgement is whether to draft the other twelve at
all, not which** — they are one shape repeated and the marginal value is low.
The next real work is the remaining ~21 non-schema files, highest-value first
by what a defect would cost: the per-app `*-auth.js` modules. Regenerate the
list by intersecting the five b18 records' `files` arrays against
`ls docs/fmea`.

## 5. Exact next step, per open item

| item | next step |
|---|---|
| (a) | **cody, at landing:** derive `rt_stops.license_hash` from the ROUTE ROW, not from the request, and say which in the commit. **fourth:** the structural fix is `foreign key (route_id, license_hash) references rt_routes(id, license_hash)` over a `unique(id, license_hash)` on the parent. A reviewer who is not cody discharges the landing obligation. |
| (b) | **fourth:** one sentence in the `routes` register cell naming the egress and the processor, and a cap on stop count in `api/_lib/routes.js` — which is hank's file, so it is two owners and one finding. |
| (c) | **Michael:** either write `assigned_overrides: {"cody": ["*.html"]}` into `docs/sairn-path-manifest.json`, or move the `.html` assignment back to fourth. Until one of those, cody's next `.html` push is refused in cody's own clone. |
| (d) | If a contradiction really exists between that pair, it needs the row numbers as the writer meant them. `tools/open_work_shard.py` can address rows by shard; file line numbers cannot be trusted across a day. |
| (e) | **fourth:** rewrite the `routes.js` header's justification from workaround to choice, and correct the `routes` cell's `sd_field_stops` clause to A/A. |
| (f) | **cody** owns `docs/known-red-suites.json`: confirm the four existing rows still describe the 8 failing arms, since my change moved one arm's quoted output string. |
| (g) | **hank / cody:** three near-duplicate pairs, one subject each. A reader cannot tell which row is current. |
| (h) | **fourth:** `python tools/criticality_tier_check.py --fix-rollup-list` inserts exactly the `LIST MISSING` name; the four COUNT drifts are hand edits to the rollup cells. |
| (i) | Both need a claim; nobody holds `.githooks/post-rewrite` or a timing control. The pattern to copy for the second is `SUITE_BOUND` in `tools/guard_ablation.py`, which already treats a timeout as COULD NOT RUN rather than as an exit code. |

## 6. Two slips of mine, recorded because neither cost anything

**Backticks in a CLI body get executed, for the second time this week.** The
first `--open` went through a shell and `app:` vanished out of attack item (1),
leaving a sentence with no subject. **And the first repair was worse than the
defect:** a `json.dumps` round-trip rewrote all 7,000 lines of
`docs/tier-a-reviews.json` for one phrase — the diff-size hazard PR §2.1 names,
one file type over. Reverted; the record re-opened by passing the text as an
argv element, and every backticked span verified by reading the stored record
back. The append is **22 lines added, 0 removed**.

**Two defects inside item 5, both caught by the fixtures within the minute and
both written into the code where they happened:** `path.lstrip('./')` takes a
*set of characters*, so every dot-directory lost its leading dot and the
**AUDITOR boundary silently stopped matching**; and `--history` passed
`%%H%%x1f%%s` to git literally, so the report printed an **empty table under a
confident heading**.

## 7. Transcript

```
C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cc\c44c9acc-c450-453e-8559-c42a7fd16504.jsonl
```

Out-of-band evidence, this session's scratch — **session-local, not a durable
record.** Every figure in the report is re-derivable by the command named
beside it.

```
...\scratchpad\b24\
  verdict.txt      the Tier A review verdict as submitted
  open.txt         the obligation text, passed as argv rather than through a shell
  hook_foreign.txt the pre-push hook refusing an out-of-scope api/ path
  hook_aud.txt     ...and refusing an auditor-scope path
  t_before.txt / t_after.txt   the tier checker's 14 and 6 findings
```
