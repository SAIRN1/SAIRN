# SAIRN handoff: cc, batch b67, 2026-10-28

**All six items are closed.** One part is deliberately held: cody's clone runs
the b66 hook until cody's live b59 claim releases. See section 1.

| | |
|---|---|
| Landed | Tier A discharge `1455a09e` · #1756 fix `c2b3a90b` and `78fb2cae` (+ register / manifest / derived-doc chores) · deny-hook scope + watchdog `972fc7e8`, `fd275b3c`. See the digest for the final tip. No `--force`, no override, no skip. |
| Claims | `sairnsenior` and `platform` (b67), released with this handoff. |
| Context | see the digest's CONTEXT line (measured). |
| Transcript | `C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cc\52164776-0b08-422d-94e1-7a56daf3eaaa.jsonl` |

## 1. Builders blocked from WRITING the auditor clones' tracked tools (items 1 and 2)

This closes the b66 DECISION-NEEDED on Michael's ruling.

**Where the scope comes from.** `tools/builder_auditor_deny_hook.py` reads
`~/SAIRN-SESSION-LOCKS/hover-scope-manifest.json` `allowed_prefixes` live: the
list the auditor clones' own deny-list reads. It applies that over a built-in
floor:
- `tools/hover_auditor_scope_gate.py`
- `tools/hover_separation_audit.py`
- `tools/hover_separation_ci.py`
- `tools/hover_routing_gap_check.py`
- `tests/run_hover_routing_gap_probe.py`

**What is excluded, and why:**
- The **shared ledgers**. The defect register is on hover's list, but every
  builder must write it.
- Directories.
- Paths already in full scope.

**What the scope is.** It is **write-only**. Reading and running these files
stays allowed, because the push gate runs the detect layer.

**Refused:**
- an Edit/Write target;
- a write target of a mutating command or redirect;
- an explicit git pathspec rewrite, with ancestors gated on whether the file
  is dirty;
- a patch target;
- code text whose write call targets the path.

Selftest: 94 arms. Each layer was ablated, and its own arms fail without it.

**Baseline replay before landing (item 2).**
- 5,874 real builder calls were replayed, from each agent's last three
  transcripts. The new scope added **13** refusals.
- **11 were real writes**:
  - cc's Edits of the scope gate and the separation audit;
  - cody's `git stash push tools/hover_separation_audit.py`;
  - cc's `git show HEAD:x > tools/hover_auditor_scope_gate.py`.
- **2 were false positives**: cody heredocs that rewrote the path manifest and
  only named hover paths as data. Those two drove the narrowing to "the path
  is inside the write call".
- A filtered re-replay on the final code covered 83 calls naming a tracked
  file. It refused 8, all real writes, and both heredocs are now allowed.

**Live on cc** (`git status` empty after; all three are in
`deny-blocks.log`):
- Edit on `tools/hover_separation_ci.py`: REFUSED.
- `git checkout --` on it: REFUSED.
- `python -c "os.replace(..., it)"`: REFUSED.
- `python tools/hover_separation_ci.py --help`: allowed, exit 0.

**Rollout.**
- hank and fourth are refreshed: copies only, with `settings.local.json`
  byte-identical on all four clones.
- **cody is HELD at the b66 copy** (`--install --only cc,hank,fourth`). cody's
  live b59 claim is "M1 hover_separation", and the new copy would refuse cody
  mid-edit in `tools/hover_separation_audit.py`. Under the ruling that work is
  no longer a builder's.
- The presence check reports cody STALE at every session start until this
  runs:

      python tools/builder_hook_presence.py --install

- The shared log also shows cody refused at 23:18Z under the b66 scope, for a
  command naming `claims/hover`.

## 2. H1 #1756: caregiver devices kept colleagues' cached PII (item 3)

**The fault.** #965 was server-only, and `senServerWinsMerge` only adds and
replaces rows.

**The fix in `sairnsenior.html`:**
- `senData` keeps the read envelope's `roster_scope` and `hr_fields_visible`
  in `senLastScope`.
- `senHydrateCaregivers` then calls `senPurgeCaregiversOutOfScope`:
  - scope `own` drops every row the server did not return, and those ids leave
    the synced map;
  - `hr_fields_visible: false` drops `bgcheck_date`, `state_caregiver_id` and
    `notes`.
- It acts only on a successful read that carries the declaration. A failed
  read or an unprovisioned store deletes nothing.
- **Disclosed edge:** a manager's unpushed caregiver row on a device that a
  caregiver then signs into is dropped there.

**Tests.**
- `tests/sairnsenior_caregiver_scope_purge.js`: 13/13. Ablating the purge call
  fails 5.
- The 7 existing sairnsenior suites and the 22-mutation delegation probe are
  green.
- 3/3 script blocks pass `node --check`.

**Caught on the way.** The `api/b17-lift-list-check.test.js` L1 guard went
STALE ×5. The cause was my comment inside `senData`: its brace matcher reads an
apostrophe as a string opener and lost `senData`. I fixed the comment and the
guard is 7/7. The cause is noted in the comment itself.

**Live.**
- The deployed `sairnsenior.html` equals the repo copy.
- The purge test passes **against the served file**.
- A no-session read answers 401 NO_SESSION.

**UNVERIFIED live:** an authenticated caregiver device run. Reading the stored
audit credentials (in the b64 session's scratchpad) was denied by the
permission layer, so this was not driven.

**Paperwork.**
- `sairnsenior.html` and the test are declared as cc's assigned b67 paths in
  the path manifest (`_assigned_overrides_why_cc_b67`).
- The register record is at `c2b3a90b`.

## 3. The carried obligation to cody (item 4)

**Which obligation it was.** The digest's "cody b57 obligation" is **cody's
b57 Tier A record** with cc as reviewer: `mechBackup`, `sairnmechanical.html`.
It is *not* in cc's own b57 handoff. That one carries a different cody item,
`d6b37bb1` lock/profile drift, routed to cody in b50 and still cody's.

**Discharged** as SOUND-WITH-GAPS (low):
- The code is in `8259a6dd`. `a5401d2d` is a pre-rebase copy that exists only
  in cody's clone.
- Both review questions hold. The local save never waits on the push; cc
  spot-checked saveDoc `:1848` before `:1863`. `provisioned:false` stays
  silent.

**Routed to cody**, each found by ablation in temp copies:
- (a) No test asserts that the local write comes before the push.
- (b) "Truthy on success" is untested.
- (c) The unprovisioned fixture uses the wrong shape.
- (d) The saveDoc toast can wait up to 15 s, so a double-click saves a
  duplicate.

`mech_docs_redaction_wiring_probe.py` is broken at HEAD by cody's own b58
`sd-data.js` commits (`10e914b1`, `4a8920f5`). It passes at `8259a6dd`.

## 4. tools/sairn_watchdog.py (item 5): built, not operated

**What it reads:**
- the shared status registry;
- each build agent's latest handoff, chosen by batch NUMBER;
- that handoff's digest NEXT line.

**What it flags:**
- **OVERLAP**: active claims whose files intersect, including a directory
  prefix.
- **STALE-CLAIM**: the handoff says released, but a claim made before it is
  still active.
- **NEXT-DRIFT**: working but not updated since the handoff; or, labelled
  HEURISTIC, a task that shares no word with the stated NEXT.

**Output and failure behaviour.**
- It writes `~/SAIRN-SESSION-LOCKS/watchdog-findings.json`.
- Claims with no files are listed as uncheckable, never silently clean.
- An unreadable row or a missing handoff is COULD-NOT-CHECK, exit 2.
- 14 arms, each criterion ablated.

**Not wired and not run on live data**, as instructed.

## 5. OPEN

| Item | Owner | Next |
|---|---|---|
| Refresh cody's hook copy | cc or anyone | `python tools/builder_hook_presence.py --install` once cody's b59 claim releases |
| The hover_separation work in cody's live b59 claim | Michael / cody | That file is now auditor-tracked, so it goes to hover or needs a ruling |
| mechBackup test gaps (a)-(d); redaction probe broken by b58 | cody | Add the arms; fix the probe |
| Authenticated caregiver-device live run of #1756 | cc | Needs credentials this session could not read |
| H1 `block_log()` CRLF (from b66) | H1 | `O_BINARY` |
| Review the hover b92 obligation | cc | After hover lands test_965 |
