# SAIRN handoff -- cc batch b13 -- 2026-10-14

**Written by:** cc, in `Documents\SAIRN-cc`, on `main`.
**Written BEFORE the report**, at a point where nothing is half-finished:
every change is committed and on `origin/main` at `0 0`, the tree is clean,
zero stashes, every selftest and ablation named below was re-run after the
final rebase, no background job is in flight and no file is mid-edit.
**Companions:** `SAIRN-report-cc-b13.txt`, `SAIRN-digest-cc-b13.txt`,
`SAIRN-latest-cc.md`.
**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cc\5521d10f-06f8-4089-8534-150e3e3c8d84.jsonl`
— the same session as b12, so the CONTEXT figure includes both batches.
Scratch: `...\5521d10f-06f8-4089-8534-150e3e3c8d84\scratchpad\`
(`apply_signoff.py`, `file_defects_b13.py`, `find_fmea_gaps.py`, the commit
message files).

---

## Committed / pushed state

**HEAD `f8e0b5e0`, `git rev-list --left-right --count origin/main...HEAD` =
`0 0`, tree clean, zero stashes.** No `--force` in any spelling. **No override
of any form** — `docs/BYPASS-LOG.jsonl` has 97 rows and **none dated
2026-10-15**, so neither `SAIRN_SEED_GATE=off`, `SAIRN_GATE_EXEMPT=seed` nor
`SAIRN_SKIP` was used. Two rebases during landing, one with a real conflict in
`docs/tier-a-reviews.json` resolved by `tools/sairn_rebase_resolve.py` (256
ancestor + 0 upstream-only + 1 local-only = 257, then validated by
`tier_a_review_gate.py --validate`). No hook added or restored;
`.claude/settings.json` never committed.

| SHA | what |
|---|---|
| `0d33f659` | fix(claims,citation) — the audit counted a session 18 days gone; a citation pointed at the wrong function |
| `ccd7350e` | feat(anchor rot) — the check fourth specced, plus the F3 arm re-pointed |
| `10209464` | feat(gate driver) — hank's three seams wired; the exit-3 channel stopped inventing a reason; 9 FMEA drafts |
| `cf989dad` | fix(board) — the fileSize mismatch resolved as a propagation lag; the manifest |
| `0154a8e3`, `383ec52a` | chore — two defect records, re-seated after the rebase |
| `c3c66331` | chore — MASTER-PLAN + traceability matrix regenerated, Tier A obligation recorded |
| `35f3863c`, `f8e0b5e0` | chore — scrutiny-ledger rows, before and after the rebase |

**Five gate refusals during landing, every one satisfied rather than
overridden:** register-feed twice (the second because the rebase moved the
shas the records cited), tier-a, derived-docs, and one non-fast-forward. The
gate denied twice in one push and printed **both** reasons rather than
stopping at the first.

**No live deployed-URL check, and that is not a skipped step:** this batch
changed no `api/`, `sql/` or app file. `tests/` and `tools/` and `docs/` only.

---

## The six items

| # | item | state | evidence |
|---|---|---|---|
| 1 | WEAKENING-FLAGS sign-off, four JSON blocks | **DONE** | `scrutiny_ledger_check.py` exit 0 CLEAN; all four shas verified present in the *checkable* set, not just in the file |
| 2 | the b11 citation; the claim liveness mismatch | **DONE** | repro'd first, arm failed first (6/7, exit 1), then 7/7 |
| 3 | F3 arm re-pointed; anchor-rot tool built | **DONE** | 35/35; new tool 12/12, and its own A7 was wrong on first run |
| 4 | three hank suites wired; FMEA drafts | **DONE** | `GUARD_TESTS` 17, no dupes; 31/31 arms; 9 drafts |
| 5 | board read-back; H2's scratch file | **DONE / NOT FOUND** | mismatch resolved as a lag, 15586 == 15586; the scratch file does not exist anywhere cc may look |
| 6 | push without force, confirm landed | **DONE** | `0 0`, HEAD `f8e0b5e0` |

---

## Item 1 — applied where the auditor's own gate would not let it write

h1 b34 did the verification and `tools/hover_auditor_scope_gate.py` **refused
its commit**: `docs/` is platform territory, outside the auditor's scope. The
edit was reverted before any push and the work was routed instead. That
separation working as designed is why this is a cc commit.

cody authored the three rebuttals and **may not sign its own work** — the same
rule `tier_a_review_gate.py` enforces — so cc applied them. One of the three
was **re-derived rather than re-read**: h1 `ast.parse`'d both revisions of
`check4_probe.py` and counted `ast.Assert`/`ast.Raise`/`sys.exit` nodes itself
(2→2, 1→1, 7→7), matching cody's numbers without taking them.

**The round-trip was measured before anything was written.** `json.dumps` at
`indent=1` reproduces the file's 201,532 bytes exactly (indent=2 → 221,809;
indent=4 → 262,365), so a load/modify/dump leaves all 726 other rows
untouched. The applier **refuses rather than reformats** if that stops being
true, refuses if a `(path, sha)` does not match exactly one row, and refuses
if a row already carries an `independent_review` — overwriting somebody else's
sign-off is not additive.

**"CLEAN" on its own would not have told you these four were examined.** The
check reports **411 rows it could not check** because their shas do not
resolve in this clone. All four signed shas DO resolve and none is in that
list — verified separately with `git cat-file -e <sha>^{commit}`.

---

## Item 2 — one record, three answers

    .claude/claims/cloud.json     "status": "active", "released_at": null
    sairn_claim.py list           cloud absent entirely
    sairn_claim.py list --all     [EXPIRED ] cloud  sairngrounds

`cloud` last claimed 2026-09-27. The stored field is written once and never
revisited; liveness is **computed** by `is_active()`. Measured across the real
1,373-claim record: **5 rows store active, 4 really are.**

**The arm was written first and proved to fail on the code as it was** — the
selection extracted into `audit_active_by()`, then driven against the pre-fix
raw-field version: A2 FAILS, 6/7, exit 1, *"THE AUDIT IS NOT COUNTING WHAT IT
SAYS IT COUNTS."* After: 7/7. New `python tools/sairn_claim.py selftest`, on
**fixtures** rather than the live record — an arm whose verdict depends on
whether cloud is dead today goes green on its own when somebody tidies the
record. **A4 stops the obvious wrong fix:** an old claim whose session is
still ALIVE must still count, because "older than four hours" is the
pre-2026-09-23 rule that read a 9.96-hour build's own claim as abandoned.

**Today the inflation is one and does not cross `MANY_ACTIVE=4`**, so the
verdict was unchanged — which is the reason to fix it, not to leave it. And
the section it feeds is literally about this population ("another session
reads a phantom block"), so it was describing the phantom using the phantom's
own field. The gap is now **printed beside** the count.

**A third tool had it**, found while repro'ing the second and fixed here
rather than routed, because b12's whole lesson was that a fix in one place
does not reach the others: `sairn_claim_doc_freshness.py:139` built its
denominator from the raw field — "2 of 5" where 4 was true. Now 2 of 4, and it
**fails closed** on an import error rather than falling back.

**The citation:** `sairngrounds.html:4771-4779` is `msbParseScanResult()`'s
return and the brand-legibility guard. The `match.cost||0` arithmetic is
`:4788` and the write site is `:4810`. The **quoted code was right and the
numbers pointed elsewhere** — PR §1.3 exactly, and the hardest kind of wrong
citation to notice.

---

## Item 3 — and the finding is that the new tool's own A7 was already wrong

The F3 arm asserted `'does not name cc'`; `drive_upload_verify` split that
message in two on 2026-10-13 and the old phrasing survived only on the **NO
AGENT NAMED** branch, while the fixture takes **WRONG AGENT**. Re-pointed at
the label the split created, with the agent names asserted separately so a
reword cannot rot it again without also losing the distinction. 35/35.

**`tools/citation_anchor_rot_check.py`.** fourth's measurement: the
`sf_events` row carried seven line citations into `sairnfreedom.html` and
**all seven were wrong** — every function real, only the numbers moved.

**Its A7 failed on its first run, 6 of 7.** Diagnosed:

    git show 924085fb:sairnfreedom.html | grep -c '<the anchor>'   ->  1
    grep -c '<the anchor>' sairnfreedom.html  (HEAD)               ->  0
    git log --oneline 924085fb..HEAD -- sairnfreedom.html
      31406a87  fix(N1-N4,F6): ... and a delete that lied

fourth's anchor resolved **exactly once** when fourth wrote it. hank's
`31406a87` refactored that one-liner into a block, and the quoted form now
survives only inside an elided comment at `:5228`. **So the anchor went to
zero within hours — loudly, as a count of 0, which is the entire point of the
form.** Nobody did anything wrong.

So A7 is **two arms**: frozen at `924085fb` (both document and app extracted
from that revision) so it pins fourth's work permanently, and A7b at HEAD
asserting only what cannot rot. A7b deliberately does **not** assert "exactly
1 finding" — that would be a rotting citation inside the rot checker.

**First live measurement, the one the spec said would be the measurement:**
7 anchors, 1 rotted, and **521 surviving `file:line` citations** (198
qualified + 323 bare) in that document, counted and judged none.

---

## Item 4 — and wiring the third suite exposed the channel lying

`GUARD_TESTS` is 17, no duplicates, every file present. All three run to a
known exit code **before** wiring: 26/0/0 exit 0, 21/0/0 exit 0, and **exit 3**.

**`api/role-picker-vs-check-constraint.test.js` exits 3** because 11 of 17
apps have no `check (role in (...))` to compare their picker against. The
runner would have printed *"SKIPPED as not applicable on this platform —
exit 3"* about a test that exits 3 on **every** platform. **A could-not-run
stating the wrong reason is worse than one stating none:** a reader dismisses
a platform skip and investigates a missing constraint.

`exit3_reason()` now quotes the test's own line and attributes it, or admits
no reason was given and names the absence as the thing to fix. Nine arms,
31/31 — including one requiring the platform claim to be **gone** for a
non-platform 3, and one requiring a **genuine** platform skip to still read
correctly, because a fix that loses the case the channel was built for is a
worse trade than the defect.

**FMEA: the dispatch said five and the measured number is nine.** Derived from
git, not from a list: 15 files lack a draft, **6 of them are cc's own** and
stay routed (detector-blesses-its-own-fix). The 9 that are not cc's are
drafted. One came back with **zero risks** — reported rather than treated as a
clean bill, because that is a statement about the drafter's detectors.

---

## Item 5 — resolved by waiting, and one thing not found

    mount : 15586 bytes, sha256 deb328e9f16c2663...
    Drive : fileSize 15586, id 19GSUTWQLddPwZiLEUNfssAjrMxK4vVE1

**It converges, same id.** Every b12 mismatch (14600/14514, 2404/2976,
2952/2976) was a metadata read taken seconds after a write while the newest
revision was still propagating. A **lag**, never a corruption — and the
statement is bounded both ways.

`read_file_content` does not support `text/markdown`, so **no chat turn can
hash the Drive-side bytes.** The only field is `fileSize`. So publish now
writes `SAIRN-board-MANIFEST.txt` with the sha256 and exact byte count of
every file — **built from the read-back bytes, not the rendered text**, which
is A16: a manifest describing what the process *meant* to write would agree
with itself after a truncated write, and the one available Drive-side check
would then compare a real short file against a published long number and be
read as a lag. 16/16 arms, 11 ablation layers, all load-bearing.

**H2's `scratch_handoff_h2_b34_NOTAPUSH.md`: NOT FOUND, NOT DELETED.** Five
searches, not one `ls`: repo root, `git status --untracked-files=all`,
`git ls-files`, `git log --all -- <path>`, and the three other build clones
plus the home directory. All empty. The one remaining location is
`Documents\SAIRN-hover2`, which a build agent must not enter — **the same
mis-routing shape b12 resolved for H1's five stale root `.txt` pairs.**

---

## Claims held

**`cc`, claimed as the first action of this batch.** Released after this
handoff, the report and the digest are written and uploaded, then the status
row set to `idle`:

    python tools/sairn_claim.py release cc
    python tools/sairn_status.py set --state idle

**Files written that were NOT in cc's declared b13 FILES**, said out loud:
`tools/sairn_claim_doc_freshness.py` (the third tool with the liveness
defect), `tests/run_drive_upload_verify_probe.py` (cody's territory — claim
verified RELEASED, not assumed, and the dispatch named the arm),
`docs/MASTER-PLAN.md` and `docs/traceability-matrix.md` and
`docs/tier-a-reviews.json` and `docs/defect-density-register.json` and
`docs/scrutiny-flags.json` (each demanded by a gate before it would accept the
push). The tool is `tools/citation_anchor_rot_check.py`, not the
`tools/anchor_rot_check.py` named in the claim — the spec said the name was
cc's call and the longer one says which form it owns.

**Conflicts declared and NOT overridden (PR §4.3):** hank's `api/`, `sql/` and
app HTML read-only — the three suites were wired by registering them, not by
editing them. No auditor clone entered or written; item 1's work came through
a routing doc and item 5's file was searched for only where a build agent may
look. `docs/CRITICALITY-TIERS.md` is **read and reported on, never edited** —
the rot finding is routed, not fixed, because a table row is rebuilt whole
(PR §2.1) and that is fourth's cell.

---

## Open, and whose — with the exact next step

| item | owner | exact next step |
|---|---|---|
| **the Tier A review of `citation_anchor_rot_check.py`** | **fourth** (auto-assigned; only fourth may discharge, or anyone after 48h with `--takeover`) | `python tools/tier_a_review_gate.py --list`. The obligation names the three things to review hardest rather than asking for a general look — read it, not this row |
| **`sf_events` anchor at count 0** | **fourth**, or whoever holds `docs/CRITICALITY-TIERS.md` | `python tools/citation_anchor_rot_check.py docs/CRITICALITY-TIERS.md`. The dead anchor is `if(ev && ev.sessionId) st(K_SESSIONS, getSessions().filter(`; the live code is `sairnfreedom.html:5241-5243`. **Rebuild the row whole** (PR §2.1), never by splitting on a pipe |
| **521 `file:line` citations in that document, staleness UNMEASURED** | **unowned — needs a decision** | fourth refused to extrapolate from the sf_events 7-of-7 and so does this. `citation_line_drift_check.py` owns that form and needs `--app` and `--prefix` per target, so it is one run per app, not one sweep |
| **cody's `check4_probe.py` write-up says "named ARM labels 3 → 4"** | **cody** | the file defines only ARM 1 and ARM 2 in both revisions. Does not reopen the verdict; h1 found it and it is now recorded in the ledger's `method` field. One line to correct |
| **nothing enumerates the consumers of the raw `status` field** | **cc, next batch** | three found one at a time across three batches, each by accident. `grep -n "get('status') == 'active'"` outside `sairn_claim.py` is the sweep nobody has run |
| **exit 3 carries two meanings** | **cross-session decision, not cc's** | recorded as a PLANNED factor on `10209464`'s register row. Entries already rely on 3; splitting it is not a one-session change. The runner no longer guesses which meaning applied |
| **`scratch_handoff_h2_b34_NOTAPUSH.md`** | **H2, or Michael** | cc searched five ways and it is absent from every location a build agent may look. If it is in `Documents\SAIRN-hover2`, only H2 or Michael can clear it |
| **FMEA drafts for cc's own tools** | any session **except cc** | now eight: `sairn_push_gate_hook.py`, `tier_a_review_gate.py`, `secrets_inventory.py`, `register_feed_gate.py`, `obligation_surface.py`, `sairn_board_publish.py`, `runbook_constant_agreement.py`, `citation_anchor_rot_check.py`, plus `.githooks/pre-push` |
| **`docs/NHI-REGISTER.md:69` still omits step 4a** | **fourth** | unchanged from b11/b12, and now DETECTED rather than remembered: `python tools/runbook_constant_agreement.py`. Promote it to blocking once the register copy lands |
| **11 apps UNPROVEN on the role-picker seam** | **hank** | `node api/role-picker-vs-check-constraint.test.js` names them every run. Each needs a `check (role in (...))` in a `sql/` file naming its `employee_auth` table, or a recorded reason it has none |
| **obligations open past 48h** | **each named owner** | `python tools/obligation_surface.py --mine`. Not re-measured this batch |

---

## Three things that will cost the next session time if nobody says them

1. **A citation can be correct when written and dead the same day, and the
   anchor form is what makes that visible.** fourth re-anchored seven
   citations by hand on 2026-10-14; hank refactored one of the quoted lines
   hours later and the anchor went to zero. **Both sessions did their jobs
   correctly and the document still went stale** — which is why the answer is
   mechanical and not a freshness stamp. fourth's own spec says it best: a
   stamp is the thing a reader checks *instead* of checking, so a wrong stamp
   is worse than no stamp. The corollary bit this batch too: **a regression
   fixture pinned to a live document rots with the document.** Freeze the
   fixture at the revision it was measured against, and in the live arm assert
   only what cannot change.

2. **"Wire these three" and "draft five" are both counts, and counts in a
   dispatch go stale.** One of the three suites exits 3, and wiring it is what
   exposed the runner asserting a platform cause it had no evidence for — the
   defect was in the *channel*, discoverable only by putting a new kind of
   member through it. And the five undrafted files measured as nine once
   derived from git instead of from a list, six more of which are cc's own and
   must stay routed. **Derive the population, then report the discrepancy
   against what was asked** — doing exactly five would have meant choosing
   four to leave out and saying nothing.

3. **A defect whose number happens not to cross a threshold today is still a
   defect, and this platform keeps finding the same one.** The raw-`status`
   read has now been fixed in three tools across three batches — 13-of-2 in
   `claim_activity_check.py` on 2026-09-28, then `sairn_claim.py`'s own audit
   and `sairn_claim_doc_freshness.py` here — and **every one was found by
   accident while doing something else.** The fix is cheap; the finding is
   not. When a tool writes up a defect class at its own call site, as
   `claim_activity_check.py` did, **the write-up is a sweep waiting to be
   run** — and nobody ran it for sixteen days.
