# Hank handoff — 2026-10-13, batch 20 (b5)

Written **before** the report, at a point where nothing is half-finished: every
item is either committed or explicitly open below, the bare-run sweep has
finished and its scratch clone is gone, and no file is mid-edit.

**Committed, not yet pushed at the time of writing** — the single push is item
12 and happens after this file. Verify with `git log --oneline origin/main`
rather than from this line.

| sha | item | what |
|---|---|---|
| `35e53203` | — | the b5 claim (pushed already: a claim nobody can see is not a claim) |
| `d78d62e7` | — | b4's trailing bypass-log rows |
| `59b6f2ae` | 2 | **seq965 reviewed → two more defects found and fixed**, obligation discharged |
| `e04c2c21` | 8 | **SAIRNvet's backup was read-dead on every pre-login page load**, + the coupling suite |
| `446e615f` | 5,6,7,10,11 | the fired tripwire, the fifth gate mechanism, audit-shape pinning, Tier A routing, sf_officers design, sd-data inventory |
| `fee040c9` | 9 | bare-run sweep routed |

---

## Claims held

**`sairnsenior`**, claimed `35e53203`, `CLEAR` — no blocking overlap. It must be
**released** at close:

```
python tools/sairn_claim.py release sairnsenior
```

One declared-file addition was made out loud rather than quietly:
`sairnsenior.html` was **not** in the claim's FILES and the item-2 review
required it. No other live claim holds it (fourth's b7 set is disjoint; cody's
b4 set was released 18h before). Under-declaring one's own file set is the same
defect as rewording past the matcher, so it is recorded in `59b6f2ae`'s message.

---

## Hooks — item 1, and this is the thing a fresh session will get wrong

`.claude/settings.json` in this clone has **`hooks: {}`**, deliberately, per
Michael: the hooks were causing agent compaction. It was **23 hook commands**
before.

**NEVER restore them. NEVER commit this file — cc owns its merges.** It shows as
`M .claude/settings.json` and must stay unstaged. Both `.bak` files are
untouched, as instructed.

**Every `git rebase` in this clone will refuse** with `cannot rebase: You have
unstaged changes`. The pattern that works, used throughout this batch:

```
cp .claude/settings.json "$SCRATCH/settings.hooks-empty.json"
git checkout -q -- .claude/settings.json      # park it
git fetch origin main -q && git rebase origin/main
cp "$SCRATCH/settings.hooks-empty.json" .claude/settings.json   # put it back
```

**Confirmed, as item 1 asked: `tools/hook_integrity_check.py` is NOT wired into
any gate that fails on empty hooks.**

* It is wired **only** at SessionStart in `.claude/settings.json`, now empty.
* `tools/sairn_push_gate_hook.py` never invokes it — `grep -c hook_integrity_check` = **0**.
* It is explicitly in `report_only_checks.py`'s `NOT_PROMOTED` list at
  **`tools/report_only_checks.py:2758`**, with the reason "NOT A REGISTRY
  CANDIDATE BECAUSE IT IS ALREADY WIRED… SessionStart is the right event and a
  push is the wrong one".
* Driven both ways to be sure: `session_surface_check` 0, `hank_session_start_check`
  0, `invocation_path_scan` **1 with hooks armed AND 1 with hooks empty** — a
  pre-existing failure, not caused by the change, and itself `NOT_PROMOTED`.

**ONE STALE CLAIM, REPORTED NOT EDITED** (the brief said report file:line and do
not edit): **`tools/report_only_checks.py:2758-2762`** states that
hook_integrity_check "runs at SessionStart (`.claude/settings.json:171`)". In
this clone it now runs nowhere. The sentence is false here and true in the other
clones, which is the awkward part.

---

## OPEN — what the next session needs, with the exact next step

### 1. Live verification is IMPOSSIBLE. The whole deployment is PAUSED.

**Item 3 could not be done, and the reason is bigger than the item.** Every path
on `sairn.vercel.app` answers **402 with a Vercel "Deployment Paused" page** —
`/api/sd-data`, `/stonedesk.html`, `/api/sairncash/firebase-config` and `/`
itself, all driven through `tools/sairn_http.py`.

The probe is committed at `docs/hank-evidence/b5_live_bare_key_probe.py` with
its output beside it. Fifteen cases, all 402, **including the ungated controls**
— which is what proves it is the deployment and not the gates.

**Next step: Michael. This is a production outage, not a batch item.** Until it
clears:

* no gate on this platform can be proven live;
* `CLAUDE.md`'s post-push rule ("live-verify the specific fix against the real
  deployed URL") **cannot be satisfied by anybody**, and a 402 means UNVERIFIED
  exactly as a 403 does;
* `tools/deploy_verify_notify.py` would see 402 on every push.

**Nothing in b4 or b5 has been proven live. Every commit says so.**

### 2. `api/` Tier A: three open obligations and I can discharge NONE of them

All three are **authored by hank**, and the gate refuses a self-review at write
time — which is the one thing it exists to refuse.

| opened_at | reviewer | sha state | next step |
|---|---|---|---|
| `2026-09-27T03:42:29Z` | fourth | **ORPHANED** | re-seat the sha first; fourth cannot fetch that commit |
| `2026-10-06T06:14:34Z` | cody | **ORPHANED** | same |
| `2026-10-12T01:51:33Z` | cc | REACHABLE | ready to review as-is |

Full table and the eleven non-`api/` records:
**`docs/2026-10-13-hank-tier-a-routing.md`**. Three DANGLING records there
belong to fourth, cody and cc respectively and are listed with the files to
re-point against.

**b4's "6 UNSTAMPED" was wrong**: zero are UNSTAMPED; five carry an unfollowable
sha (3 DANGLING, 2 ORPHANED), and the repair differs between the two.

### 3. `sf_officers` server-side guards — design landed, code waits on Michael

**`docs/2026-10-13-hank-sf-officers-server-guard-design.md`**. No code, per the
brief. The design's own conclusion is the next step:

* **the sole-holder rule is a UNIQUENESS CONSTRAINT** → a partial unique index,
  because read-then-write loses to two concurrent writes and an outgoing plus
  incoming Commander is exactly that;
* **SPEC 1c is a WHOLE-TABLE INVARIANT** → the handler, copying
  `dnt_appointments`' decide-against-the-server's-row shape with a fail-closed
  pre-read;
* **both are independent of the role-matrix answer** and should land first. A
  role restriction does not remove either guard — a Commander can deactivate the
  last provisioner as easily as anyone.

The index recommendation carries a cost that must not be skipped: it puts the
capability list in two places, so **it is worse than the status quo without a
test asserting the predicate names exactly the `sole:true` ids**.

**The brief's line numbers had moved ~67 lines.** Current: `activeProvisioners()`
`:2916`, SPEC 1c `:2927-2940`, sole-holder `:2942-2956`. Re-derive again before
writing code.

### 4. Routed to cc — 13 bare-run write findings

**`docs/2026-10-13-hank-bare-run-routing.md`**, log at
`docs/hank-evidence/b5_bare_run_write_check.out`. All 13 are `tools/*.py`, so
all 13 are cc's. Sharpest: **three checkers edit another session's
`status/<session>.json` in the shared registry merely by being run**
(`idempotency_check.py` → hover.json, `register_freshness_check.py --help` →
fourth.json, `shape_antipattern_check.py` → hover2.json). That registry is what
every clone reads to decide whether somebody else is working.

**34 of 313 tools timed out at 25s and are UNCLASSIFIED.** The sweep is
conclusive for 279. Do not quote 13 without that denominator.

### 5. Routed to whoever owns the conventions file

A convention candidate, text only, in the report. Short form: **a checker's
universe must exclude the artefacts that describe its own findings, and any
change that moves a pattern behind a shared helper must extend the checker that
resolved the old shape in the same push.** b5 paid for it three more times — my
own sweep had four separate detector bugs, each of which would have cleared a
real defect. Not added to
`docs/2026-09-13-cross-domain-disciplines.md` by me: that file's numbering has
been wrong twice from two sessions adding an item in the same hour.

### 6. Not touched, by instruction

Michael holds b4 Q1/Q2/Q3 and the five unlocked `sf_*` tables
(`sf_district_imports`, `sf_events`, `sf_permit_flags`, `sf_products`,
`sf_vehicles`). **The migration SQL doc was NOT run and NOT edited.**

---

## What b5 found that nobody asked for

**Three defects, all in code that had just been fixed or just been written:**

1. **The seq965 redaction landed on the roster and nowhere else.** The
   compliance panel (`sairnsenior.html:5722`) and the CSV export (`:5745`) both
   rendered a "Background Check" column that the server now strips — so every
   row read *no background check on file*, on the one column a state surveyor
   asks about, and the export put it in a file that leaves the building. Found
   by grepping every render rather than reading the branch the finding named.

2. **SAIRNvet's backup was read-dead for every page load that began at the
   sign-in pane** — all 46 resources, because `api/sd-data.js:13552` gates them
   all and `svHydrateAll()` ran only at parse time. Broader than the
   SAIRNfreedom instance that defined the class (22 of 36). And the file's own
   comment at `:10018` asserted the opposite, which is how it survived.

3. **A deliberate tripwire had been firing, honestly, for as long as the gate it
   watches had existed.** `api/sd-data-cross-tenant-dispatchers.test.js`'s
   `app: null` section reported 14 arms UNREACHED on 401 — and six Tier A
   SAIRNgrounds resources therefore had **no tenant-isolation coverage at all**
   for that whole period. Not because anyone disabled it: because a correct
   tripwire was read as a known-red suite. 405/14 → **419/0**.

**And a fifth gate mechanism nobody had catalogued.** `GRD_SESSION_RESOURCES` at
`api/sd-data.js:4343-4366` — a named set plus `hasOwnProperty`, pre-dispatch,
covering 21 SAIRNgrounds resources. Invisible to every scan keyed on the other
four. My own inventory called those six `NO GATE FOUND` and my own sweep called
sairngrounds ungated; both were wrong and both are corrected. **It was found by
a red suite, not by reading the file.**

---

## Transcript

`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-hank\08b87893-ec2b-4bd5-99bb-70843fa2df93\`

Scratchpad in the same directory under `scratchpad/`; it is `%TEMP%` and is
cleared without warning, so anything cited by a committed document was copied to
`docs/hank-evidence/` — the live probe and the bare-run log both are.
