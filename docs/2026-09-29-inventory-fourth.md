# Fourth — inventory and house-cleaning, 2026-09-29 (queue 11)

What is in flight, what is blocked and on whom, which of my own documents and
tool headers are now stale, and the gaps found this round that were not logged
anywhere until this file.

---

## 1. In flight — landed this round

| Artefact | What it is | Verification |
|---|---|---|
| `tools/purge_evidence_gate.py` + `tests/run_purge_evidence_probe.py` | Record `git fsck --unreachable` and object mtimes BEFORE any prune/gc/reflog-expire; audit every tool, test and hook for an unguarded one | 17 arms, 17 pass. Real repo: 878 files scanned, **0** executable unguarded, 35 disclosed (all `git worktree prune`) |
| `tools/rewrite_convergence_map.py` + `tests/run_rewrite_convergence_probe.py` + `docs/2026-09-29-rewrite-map-fourth.md` | Every hook and tool that can rewrite the tree or a commit, with its trigger, its write, and whether that write can re-trigger it — plus a chain simulation that fails when the composition has no fixed point | 9 arms, 9 pass. 12 actors, every anchor resolving exactly once |
| `tools/numeric_default_coalesce_scan.py` + `tests/run_numeric_coalesce_probe.py` | The class of the sairnbiz `sbCfg().ot` defect: a getter that substitutes a non-zero numeric default before validation can see the input | 13 arms, 13 pass, including an ablation that re-introduces `ot:c.ot||d.ot` into a copy of the real `sairnbiz.html` |
| `sairnbuild.html` two prefill fixes + `tests/sairnbuild_settings_prefill_coalesce.js` | A stored 0% default markup or retainage was replaced by 18% / 10% on the forms that consume it, while the settings screen went on showing 0% | 17 arms, 17 pass, with a known-bad control per site. All 4 script blocks `node --check` clean |
| `docs/2026-09-29-cells-fourth.md` | Replacement register text for `locations` and `sv_herdhealth`, re-derived from HEAD with lines recorded | Every cited line re-read and corrected — the first draft had six wrong line numbers |

## 2. Held deliberately, NOT committed

**`sql/restore_demo_pins_2026-09-29.sql` is on disk and uncommitted, and stays
that way.** The push gate refuses it with `MISSING_TABLE sairnvet_employee_auth`
against `db/schema_snapshot.json`. The table exists live — driven, not assumed:
`api/sv-auth.js:519,559` answers `503 NOT_PROVISIONED` when its auth table is
absent, and live it answered `401` on login and `403` on roster, both past the
table. **The snapshot is the stale thing, not the file.** It unblocks the moment
`sql/schema_snapshot_query.sql` is run in the Supabase editor and the single JSON
cell is saved as `db/schema_snapshot.json`. The gate is not overridden.

Re-verified this round: the file's hashes round-trip (`scryptSync` reproduces
both `pin_hash` values, `sha256` reproduces both `license_hash` values), and
`employee_auth_guard_check.py --changed` reports `writers checked: 1, guarded: 1,
UNGUARDED: 0` after the guard messages were re-flowed onto one line each.

## 3. Blocked, and on whom

| Item | Blocker | Held |
|---|---|---|
| **SAIRNcare controlled-substance witness** — `sql/sairncare_witness_schema.sql` | **hank**, `subject: hank`, `blocked by: same app: sairncare`. That session is RUNNING (CLAUDE_PID 58388, started when the lock says) | claimed `2026-09-29T17:21:49Z`, **6.6h** at the time of check |

Not started, per the standing rule that a claim overlap is flagged back rather
than worked around. It is the third consecutive round this item has been
blocked on the same session and the same app.

**Freed since the last round and NOT taken, deliberately:**

- `docs/2026-09-29-cells-fourth.md` — hank's block on `"cells docs fourth"`
  released. **Rechecked, CLEAR, and done this round.**
- `tools/sairn_sql_preflight.py` — cody released `cody-matcher`, so the file is
  free. **Not edited**, because the instruction for that item was to print the
  change text and name cody, and the instruction not to edit it was explicit.
  The exact change text is in the report; it is a five-minute edit on a word.

## 4. My own documents and tool headers that are stale — what they say vs what is true

| Where | Says | Is |
|---|---|---|
| `db/schema_snapshot.json` | `_generated_at 2026-09-13 18:39:55+00`, and `sairnvet_employee_auth` absent | **16 days old.** The table exists live, proven by two response codes. Everything using `--live` against this snapshot is reading a fortnight-old database |
| `docs/CRITICALITY-TIERS.md:177`, the `locations` integrity basis | "`api/_lib/dnt-location.js` stamps location on writes elsewhere" | **Wrong application.** That file is SAIRNdental's write-side stamp (its own header, lines 1-8). This row is StoneDesk's `sd_locations`, `app_id: 'stonedesk'`. Replacement text in `docs/2026-09-29-cells-fourth.md`; the file is hank's so it is text, not an edit |
| `docs/CRITICALITY-TIERS.md:587`, the `sv_herdhealth` bases | "Classified by the stated B rule rather than individually read" — twice | Now **individually read**. B still holds, but on a reading rather than on a blanket rule, and the one field that would move it (`scc`, somatic cell count) is named. Replacement text in the same doc |
| `tools/credential_purge_check.py` header | Explains that the forensics were destroyed by the same command that fixed the problem | Still true, and it was the only defence. **`docs/credential-purge-log.json` records a VERDICT (count searched, zero or not), not the evidence.** `tools/purge_evidence_gate.py` is the artefact that records the fsck output and the object mtimes, and the two are not interchangeable — one answers *was it clean*, the other answers *when did this arrive* |
| `docs/TOOLING-INVENTORY.md` | did not list the three tools above | Regenerated with this push. It is generated, not hand-written |

## 5. Gaps found this round and not logged anywhere before this file

### 5a. Seventeen remaining falsy-coalesce sites, registered by file

`tools/numeric_default_coalesce_scan.py --config-only` reports 19 sites whose
enclosing function reads a settings store. **Two were mine and are fixed.** The
other seventeen, with what a typed or stored 0 actually does at each — and an
honest split between the one I judge a real defect and the rest:

**GENUINE, and NOT fixed because the fix is a product decision I should not make
alone — `sairnbuild.html`, `t.duration`, SIX consumer sites** (`:3809`, `:3830`,
`:3864`, `:3873`, `:3896`, `:3956`, all `(t.duration||1)*86400000`):

- The store keeps 0: `:4003` reads `parseFloat($('tm-duration').value)||0`.
- The edit form shows **blank**: `:3993` reads `t.duration||''`.
- The schedule computes **one day**: the six sites above.

So one stored value has three different answers on three screens. A zero-day
task is the standard convention for a **milestone**, so 0 is very likely a
legitimate value rather than a typo — but deciding that, and deciding how a
zero-length bar renders on a Gantt, is a product call. Registered with the
deciding question rather than answered: **is a 0-day task a milestone, or is it
unset?** Everything follows from that and nothing should be built before it.

**NOT a defect, driven and dismissed — `tests/faults/faultkit.js:115`,
`opts.failFrom || 1`.** `state.calls` is incremented *before* the comparison
(`:117-118`), so calls are 1-based and `failFrom` 0 and 1 produce identical
behaviour. The shape is there; the consequence is not.

**LOW, no user-typed value involved:**

| Site | Shape | Why it is low |
|---|---|---|
| `sairnbuild.html:2184`, `sairngrounds.html:1572`, `stonedesk.html:2823` | toast duration `d\|\|3000` / `dur\|\|3000` | A caller passing 0 means "no delay" and gets the normal delay. Not a stored setting, not user-typed |
| `sairnmechanical.html:293`, `stonedesk.html:2852` | `maxTokens \|\| 1500` | A 0-token request has no meaning |
| `sairnbuild.html:7660` | FRED API `limit \|\| 13` | Internal request parameter |
| `stonedesk.html:10334` | `(d.topCustomers[0].quote\|\|1)` | It is a **divisor**. The `\|\|1` is a divide-by-zero guard and is correct |
| `stonedesk.html:29857` ×2 | `item.qty \|\| 1` | A 0-quantity line renders as 1. Real but minor, and `stonedesk.html` is cody's (`cody-slab`) |
| `tools/sairn_load_state_check.py:343` | `r.get("version") or 1` | A stored schema version 0 becomes 1. No version 0 exists |

**Owners:** `stonedesk.html` — cody (`cody-slab`). `sairnmechanical.html` — cc
(`mechredact`). `sairnbuild.html` — mine this round. `sairngrounds.html`,
`tests/faults/faultkit.js`, `tools/sairn_load_state_check.py` — unclaimed.

### 5b. The raw count would have been a false alarm, and that is the finding about the tool

The unrestricted scan reports **297** sites. **Fifty-three of them are `|| 1`**
(a quantity or a page number), and `|| 640` / `|| 480` are canvas dimensions.
Publishing 297 as a defect count would have been a fabricated figure of exactly
the kind Guardian's fabrication check exists for. The number that means
something is 19, and it means something only because "the enclosing function
reads a settings store" is a second, independent property.

**Three defects in my own scanner were found by its own controls before any
number shipped**, and all three are the standing classes:

1. **A whole-file field search.** Resolving a named default like `e.rate` by
   grepping the entire file for `rate:` attached a number from an unrelated
   object a thousand lines away — and then printed it as derived. Now resolved
   only from a single object-literal declaration of that same variable, or
   reported as an unresolved **lead** and not counted.
2. **A single-pass comment/string stripper mis-aligned on an odd backtick inside
   a comment.** `stonedesk.html:31807` is a comment containing
   `` `(x.hrs||0)*(x.rate||28)` ``; a backtick opened on an earlier comment line
   ran through this line's `//`, and the scanner reported **a comment as a
   defect**. Comments are now stripped first, unconditionally, before strings.
3. **`archive/` was in scope** — verbatim dumps of abandoned branches, 30-odd
   findings no user can reach. Excluded, and the exclusion is printed in every
   report rather than implied.

### 5c. Two defects in the purge-evidence gate, same shape, found the same way

The first version matched text over comment-stripped lines and produced **40
findings on this repo, all 40 wrong**: 37 were `git worktree prune`, which
removes administrative files and destroys no object, and 3 were prose inside
docstrings and a tool-description table. It now walks the Python AST and reads
only the string constants inside calls that actually execute a subprocess.

**And then a fourth**, found by asking why the count dropped to zero: **most
probes in this repo do not call `subprocess` directly** — they define a local
`def git(repo, *args)` helper. The AST walk was blind to fifteen files for that
reason. A detector blind to the way the repo actually writes the call is a
detector that reports zero forever.

### 5d. The `sv_herdhealth` brief did not match the code

I was handed the gist that the `sv_herdhealth` cell should quote a rename blast
radius. Re-derived from HEAD, **that blast radius is `locations`** — and the code
says so itself at `api/sd-data.js:2865-2869`. `sv_herdhealth` has no rename
affordance (`openHerdEdit` exposes five fields and the name is not one of them)
and nothing outside it references a herd (all seven `.herd`/`herd:` sites in
`sairnvet.html` are inside its own code). Copying the `locations` basis onto that
row would have been a byte-identical transplant of a proven pattern into a target
with different scale and references — the seventh cross-domain discipline, and
the reason it exists. Recorded in `docs/2026-09-29-cells-fourth.md`.

### 5e. One thing I did badly this round

I edited `sairnbuild.html` after `check sairnbuild.html` said CLEAR, but **the
path was not in my claim text**, so for the length of that edit the file was
modified by a session no other clone could see holding it. `check` is not a
claim. The claim was released and re-made with the path included, and the
re-claim initially failed to reach origin because the tree was dirty — which is
the tool being right: a claim that does not reach origin is invisible, and it
said so rather than reporting success.

---

## 6. What the next session should pick up

1. **Run `sql/schema_snapshot_query.sql`** and save the JSON as
   `db/schema_snapshot.json`. It unblocks the PIN restore file and un-staleens
   every `--live` preflight on the platform.
2. **Decide the `t.duration` question** — milestone or unset — then fix the
   three-way disagreement in `sairnbuild.html` in one pass.
3. **`sql/sairncare_witness_schema.sql`** the moment hank releases sairncare.
4. **`tools/sairn_sql_preflight.py`** — the snapshot-age line, change text ready,
   file now free.
