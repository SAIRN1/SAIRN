# Hank handoff — 2026-10-12, batch 20 (b4)

HEAD at close: **`a53f7747`**, `ahead 0 / behind 0` of `origin/main`.
Everything below is pushed. Silent mode throughout.

---

## READ THIS FIRST: the resume check found two things nobody was told about

**1. EVERY ENFORCEMENT HOOK IN THIS CLONE WAS DISARMED, AND `git status` LOOKED
NORMAL.** `.claude/settings.json` had been rewritten with an **empty `hooks`
object** — 22 hook commands across PreToolUse, PostToolUse, PreCompact,
SessionStart and UserPromptSubmit, all gone. The file's indentation is
PowerShell's `ConvertTo-Json` house style, and `ConvertTo-Json` defaults to
`-Depth 2`: a read-modify-write round trip through it silently truncates
anything nested deeper, which is every hook. Two `.bak` files sat beside it,
both byte-identical to the committed version, so whatever did it knew enough to
back up and not enough to check the result.

Restored from `HEAD` (the committed version already carried `outputStyle` and
`enabledPlugins`, so nothing was lost). Verified by `tools/hook_integrity_check.py`
reporting the wiring back at `PreToolUse=7, PostToolUse=7, SessionStart=6,
UserPromptSubmit=1`.

**Nothing warned.** A clone with no hooks passes every local check, pushes
through a `pre-push` that is not installed in it, and reports clean. If you
inherit a clone and have not personally seen `hook_integrity_check` print a
wiring line this session, run it before trusting anything.

**2. BATCH 19's TWO FIXES HAD NEVER REACHED `origin/main`.** `ea891f0e`
(sf_officers) and `a8956a6f` (scp) were committed locally and never pushed — and
hover2's b9 handoff, written against `origin/main`, reports **"sf_officers …
STILL UNFIXED, untouched"** and `dnt_appointments_write_gate_repro.py →
REPRODUCES`. Both statements were true of the branch and false of the work. A
commit that is not pushed is indistinguishable from work that was never done,
and an auditor reading the branch will say so in writing. Both are now on
`origin/main` as `56e040c3` and `0442646c`.

There was no `docs/handoff-hank-2026-10-11.md`. This is the first handoff since
`docs/handoff-hank-2026-10-08.md`.

---

## What landed

| sha | what |
|---|---|
| `56e040c3` | **sf_officers** gated — batch 19's commit, finally pushed |
| `0442646c` | **scp** three resources gated — batch 19's commit, finally pushed |
| `b7f6fb54` | **sf_sessions / sf_shifts / sf_tickets / sf_rentals** gated, plus the `dnt_appointments` write-ownership gate, plus the SAIRNfreedom hydrate-before-sign-in silent failure |
| `fdb80dbe` | `hook_integrity_check.py --wiring-only`, comparison LIFTED not copied |
| `ea976892` | the Tier A obligation for the nine gated resources, assigned to **cc** |
| `16245537` | **seq958** credential-grant attribution across 14 `api/*-auth.js`, **seq681** SAIRNcash Firebase mint |
| `71b8f7c8` | MASTER-PLAN and traceability matrix regenerated |
| `7a3b24c9` | **the ghost-field scan was being silenced by its own probe and by the write-up of its own failure** |
| `ec0146fe` `3a31d8df` `a53f7747` | four defect-register records |

---

## THE FIVE THINGS THE NEXT SESSION ACTUALLY NEEDS

### 1. The SQL is the fix, and none of it has been run

`16245537` wired credential-grant attribution into all 17 `api/*-auth.js`. **It
records nothing in 16 of 17 apps**, and the push says so rather than claiming a
fix. Measured by `python tools/audit_event_type_check.py`, exit 1:

| app | table | state |
|---|---|---|
| SAIRNlaw | `sairnlaw_audit_log` | **WORKS** — exists, CHECK permits `pin_setup` |
| StoneDesk + sub | `stonedesk_audit_log` | exists, **CHECK REJECTS `pin_setup`** → **STEP 0b** |
| SAIRNcode | `sairncode_audit_log` | exists, **CHECK REJECTS `pin_setup`** → **STEP 0a** |
| the other 13 | `sairn*_audit_log` | **table does not exist** → **STEPS 1–13** |

So `api/sd-auth.js`'s and `api/sc-auth.js`'s attribution — written 2026-10-07,
and held up in that document as the pattern to copy — **has been failing at the
database every day since it landed**. `attributed: false` is what their callers
have been getting.

Everything needed is printed in `docs/2026-10-07-hank-migration-sql-for-michael.md`,
whose "AFTER THE SQL: THE CODE HALF" section is now correct rather than saying
"none of it is done". The 13 DDLs are also `sql/*_audit_log_schema.sql` now,
extracted byte-for-byte — not tidying: `audit_event_type_check.py` reads CHECK
constraints out of `sql/*.sql`, so while they lived only in markdown the
thirteen new callers were **clean by absence**.

**This is Michael's to run. It is the single highest-value outstanding item in
this handoff.**

### 2. Five Tier A SAIRNfreedom resources are still ungated, by decision

Derived, not guessed: `SF_RESOURCES` carries 36 resources; 22 are now gated;
**nine** of the other 18 were Tier A by `docs/CRITICALITY-TIERS.md`'s own
letters. Four were gated — the ones with a money or statutory figure on the
row. Five were not, and are NAMED in both gate suites so the asymmetry is
visible:

`sf_district_imports` (register:353), `sf_events` (:358), `sf_permit_flags`
(:367), `sf_products` (:368), `sf_vehicles` (:380).

`api/sd-data-sf-session-gate.test.js` says in its own words that widening the
gate is a **product decision**. The batch named four and their client write
sites; it did not name those five. **Somebody has to decide, and it is not a
bug report.**

### 3. None of the gates was proven live

No bare-key call was driven against a real SAIRNfreedom or SAIRNscape licence
for any of the nine resources, unlike the 2026-10-05 `customers` entry which
carries one with a control. The evidence is the register letters, the two-list
derivation, the client write sites read at HEAD, and the repro exit codes.
**Source level only, and the commits say so.**

Likewise the gates add **no role check**. Any signed-in session of any role can
still write every one of these rows, and the three client-side trapdoor guards
over `sf_officers` (`sairnfreedom.html:2849`, `:2860-2869`, `:2878-2885`) are
still client-side. `sf_officers_provisioning_bypass_repro.py` exits 0 FIXED with
its own third condition reading `role/capability check present: False` — that is
the repro's documented semantics (any one condition clearing is a fix), not a
mis-score, but it is the remaining gap in one line.

### 4. The ghost-field probe was not broken, and the diagnosis in the ledger was wrong in an instructive way

`tests/run_ghost_field_read_probe.py` had been red since 2026-10-06 with five
failing arms, four of them planted-key controls. The ledger entry said *"EITHER
the scan's vocabulary narrowed OR those planted keys were removed from the
fixtures."* **Neither.** The scan's spelled universe had WIDENED to swallow its
own test material:

* the probe holds its payloads (`actual_start`, `ghost_window_anchor`) as
  **Python string literals**, and `code_only()` strips `#` comments while
  **keeping strings**, deliberately, because a string key is a real spelling;
* `docs/known-red-suites.json`'s own `why` field — **the write-up of this
  failure** — quoted both names, and `.json` is read as data with no stripping
  at all.

Both names were "spelled somewhere in the repo", both stopped being ghosts, the
scan went correctly silent, and the probe failed against a working scan. **The
explanation of the failure was one of the two things sustaining it.**

Fixed with `SPELLING_BLIND` — two named paths, printed in the scan's own
`excluded:` list every run, refusing to run if either path stops existing. The
probe gained a **DELTA arm** (31 → 32 findings per mutation) because its
exit-code arm was vacuous: the shipped tree already exits 1. Probe now 19/19,
scan findings unchanged at 31 before and after, so the repair added no false
positives. Entry moved to `recovered` in the ledger with the real diagnosis.

### 5. The push gate is being blocked by other sessions' files, repeatedly

`SAIRN_SEED_GATE=off` was used **three times** this batch and every use is in
`docs/BYPASS-LOG.jsonl`. Each time the only live refusal was
`external_file_index_check` naming **another session's** Drive handoff
(`handoff-h2-2026-10-11b.md`, `handoff-fourth-2026-10-11.md`,
`handoff-h2-2026-10-12b.md`). The two honest remedies were both wrong for me to
take: committing another role's handoff reaches into their record, and
hand-editing `docs/external-files-index.json` contradicts its own
`_derived_not_hand_written` rule.

The index is **CLEAN now** (`external_file_index_check` exit 0, 12 INDEXED, 0
UNINDEXED) because cody and hover2 landed rows eight through eleven during the
batch. But the pattern will repeat on every batch: **each session's new Drive
handoff blocks every other session's next push until its owner indexes it.** A
recursive/transient declaration on `G:\My Drive\SAIRN-status` would hide real
handoffs and is not the answer; something else is needed, and it is not mine.

---

## Also open

* **`sen_caregivers` (hover2 seq965)** is assigned to **hank** by cody as a Tier
  A review obligation (`docs/tier-a-reviews.json`, opened 2026-10-12T11:21:02Z).
  **Not started.** The precedent fix shape (`ALF_CRED_READ_ROLES`-equivalent
  scoped set, from the already-fixed seq963) is sitting next door.
* **`api/law-auth.js` keeps a divergent stored audit shape** —
  `{employee_id, role, detail:{by}}`, a `detail` nested inside `detail` — against
  the family's `{target, granted_role}`. Normalising it rewrites the shape of
  rows **already in a live legal-sector audit table**. That is a data decision
  somebody should sign, not a side effect of an unrelated fix. Reported, not
  changed.
* **The scrutiny ledger carries a false positive I deliberately did not edit**:
  `api/sd-data-dental-provider-scope.test.js` is flagged WEAKENING on "a skip /
  exemption / allowlist entry ADDED", matching the line
  `+ 'in anyone, which is why the read exempts them)', async () => {` — which is
  **prose inside a test name**. The matcher reads English in a string literal as
  structure. The matcher is in another session's declared file.
* **`tools/bare_run_write_check.py` exists and fails closed** (exit 2 without a
  scratch clone, "there is no safe default"). A full sweep was **not run** this
  batch.
* **The secret-absent overwrite class is MEASURED and CLOSED, but the
  measurement is not mechanical.** Exactly two tools read a credential and write
  a file — `audit_checkpoint_status.py` and `cron_liveness_check.py` — and both
  carry the guard and the distinct no-secret exit. Five more tools make a
  network call and write a file; none reads a credential, so none is in the
  class. **Nothing re-derives that when a third tool is added.**

---

## The repro board at `a53f7747`

| repro | exit | reading |
|---|---|---|
| `sf_officers_provisioning_bypass_repro.py` | **0** | FIXED (gate); role check still absent |
| `dnt_appointments_write_gate_repro.py` | **0** | CLEAN, both conditions true |
| `sairncash_verify_token_mint_repro.py` | **0** | NO FINDING |
| `scp_session_gate_repro.py --all` | 1 | **10 of 22** reproduce — the five resources `UNGATED_REST` names on purpose, each with its columns read out of the schema |

## The suites

```
api/auth-setup-attribution.test.js            8 passed   17/17 attributed   exit 0
api/sairncash/verify.test.js                 22 passed   (6 arms new)       exit 0
api/sd-data-sf-session-gate.test.js                                         exit 0
api/sd-data-session-gate.test.js       pair count 86 -> 94, MEASURED        exit 0
api/sf-session-gate.test.js  api/sd-data-scp-session-gate.test.js           exit 0
api/sd-data-dental-provider-scope.test.js  api/..-ledger-validation.test.js exit 0
api/auth-license-app-scope.test.js  api/sd-auth-last-admin.test.js          exit 0
api/sf-auth.test.js  api/sv-auth.test.js  api/_lib/firebase-mint.test.js    exit 0
api/sd-sub-data-auth-ordering.test.js                                       exit 0
api/law-auth-custody-matter-attribution.test.js                             exit 0
tests/run_ghost_field_read_probe.py          19 passed, 0 failed            exit 0
tools/audit_event_type_check.py --selftest   11 passed (D1-D5 new)          exit 0
tools/audit_event_type_check.py    exit 1 -- THE THREE STEP 0 CHECKs, pre-existing
tools/defect_register.py --check             514 records, every sha resolves exit 0
tools/tier_a_review_gate.py --validate       242 records                    exit 0
tools/external_file_index_check.py           0 UNINDEXED                    exit 0
node --check on every changed api/*.js                                      exit 0
sairnfreedom.html / sairncash.html inline blocks, HTML-parser-extracted      exit 0
```

---

## One convention candidate, text only

**A CHECKER'S UNIVERSE MUST EXCLUDE THE ARTEFACTS THAT DESCRIBE ITS OWN
FINDINGS — AND ANY CHANGE THAT MOVES A PATTERN BEHIND A SHARED HELPER MUST
EXTEND THE CHECKER THAT RESOLVED THE OLD SHAPE, IN THE SAME PUSH.**

Paid for three times in this one batch:

1. The ghost-field probe's own payloads entered the universe it tests.
2. The red-suite ledger's write-up of that failure did the same, through a file
   extension the existing `*.md` rule did not cover.
3. Moving fourteen `api/*-auth.js` files onto `auditPinSetup()` would have
   removed all fourteen from `audit_event_type_check.py`'s field of view **while
   its printed total went on looking the same** — the fix closing one gap would
   have opened a blind spot, silently, in the same push.

The existing convention 8 says *nothing announces the day a check stops testing
anything*. This names the two specific ways it happens on this platform and
makes both actionable at the moment of the change rather than on a cadence: a
checker that reads the whole repo will eventually read the description of its
own findings, and a refactor that centralises a pattern removes it from every
lexical checker keyed to the old shape.

Routed to whoever owns `docs/2026-09-13-cross-domain-disciplines.md`. **Not
added by me** — the numbering of that file has been wrong twice from two
sessions adding an item in the same hour.

---

## Housekeeping

* Claim: **none held.** `sairn_claim.py claim` **REFUSED** (cody's declared
  FILES include `api/sd-data.js`; hover2's claim shares `external-files`).
  Proceeded on the coordinator's explicit written line assignment, with the
  override declared in the shared status registry rather than hidden — and the
  registry's own PID check reported **cody, cc and fourth all DEAD** at the time.
  My `sd-data.js` regions (`:1089`+, `:15400`+) do not overlap cody's
  (`:1037-1069`, `:13798-13806`). No conflict occurred.
* `.claude/settings.json.bak` and `.claude/settings.json.hooks.bak` are left on
  disk, untracked. Both are byte-identical to the committed `settings.json`;
  they are evidence of the disarming, not work.
* `docs/tier-a-reviews.json`: my own obligation cited `64a1e5e899c0`, orphaned by
  four push-race rebases. Repointed to `b7f6fb54` with
  `opened_at_sha_was` / `_reseated` / `_reseat_basis`. `--reseat-shas` classified
  it WEAK and would also have repointed **three other sessions' records** on that
  weak basis; declined, one record touched.
