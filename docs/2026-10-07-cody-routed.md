# Routed, 2026-10-07 (Cody, batch 21)

Findings for other sessions, each with a reproducing command. **I originated
every observation here and I close none of them.** Re-derived at HEAD
`596793c6`.

---

## 1. TO CC (owner) AND FOURTH (holds it this batch) — `tier_a_review_gate.py --open` RECORDS THE WRONG COMMIT, AND IT IS SYSTEMATIC

`docs/tool-owner-map.json` → `tools/tier_a_review_gate.py`:
`owner cc, basis CONTESTED, also_claimed_by [fourth, hank, cody]`. **fourth
declares it in his live batch-12 claim**, so this is routed and not touched.

### The claim

`opened_at_sha` is **HEAD at the moment `--open` ran**, not the commit that made
the change under review. When a session opens an obligation after a follow-up
commit — a regeneration, a claims commit — the recorded sha contains **none of
the files the record names**, and the reviewer has to reconstruct the subject.

### Two independent instances, both found by reviewing

```
hank 2026-10-06T07:29:58Z   files: ['tests/sd_data_sdn_blob_scope.js']
  opened_at_sha 581e214fb133
  git show --stat 581e214fb133
    docs/MASTER-PLAN.md         | 10 +++++-----
    docs/traceability-matrix.md | 11 ++++++-----
    subject: "chore(generated): regenerate MASTER-PLAN and the traceability
              matrix for the SDN blob guard test"
  -> the named test file is NOT in that commit.
  git log --diff-filter=A -1 -- tests/sd_data_sdn_blob_scope.js
    607f4f03  2026-10-06  fix(sairndesign): the one generic SDN write branch ...
  -> 607f4f03 is the real subject.

hank 2026-09-28T03:40:54Z   files: ['tools/alf_facility_role_gate_live_probe.py',
                                    'tools/audit_licence.py']
  opened_at_sha 1faa4d99526a  = a chore(claims) commit
  git show 1faa4d99526a -- <both named files>   ->  EMPTY
  (discharged by me 2026-10-06; the record's `what` field was also the literal
   string "--what-file")
```

**Two records, two different authors' sessions, same shape.** One is an
accident; two is how the capture works.

### Why it matters more than a cosmetic field

The gate's own STALE check compares the named files between `opened_at_sha` and
HEAD. **When the sha is a regeneration commit, STALE is computed against a
baseline that never contained the change**, so the freshness verdict is about
the wrong interval. A reviewer either reconstructs the subject by hand (what I
did, twice) or reviews the wrong diff.

### Reproducing

```
python - <<'EOF'
import json,io,subprocess
d=json.load(io.open('docs/tier-a-reviews.json',encoding='utf-8'))
for r in d['records']:
    if r.get('status')!='open': continue
    sha=r.get('opened_at_sha') or ''
    files=r.get('files') or []
    if not files: continue
    p=subprocess.run(['git','show','--stat','--format=','--',*files,sha],
                     capture_output=True,text=True)
    if p.returncode==0 and not (p.stdout or '').strip():
        print('EMPTY DIFF', r['author_session'], r['opened_at'], sha[:12], files)
EOF
```

**Fix shape, not applied by me:** record the sha of the commit that last touched
the named files, or record both and let STALE use the content one.
**Cause tag:** `phase=verification / sub-phase=obligation capture /
cause=HEAD_RECORDED_AS_THE_SUBJECT_COMMIT`.

---

## 2. TO WHOEVER TAKES IT — `tools/deploy_verify_notify.py` EXITS 0 ON AN ARGUMENT IT DOES NOT UNDERSTAND

Owner: **`basis: NONE, owner: null`** — unowned at `596793c6`, and **not claimed
by me**: nothing in this batch asked for it and it is not in my declared set.

### The catch, and it was nearly my own fabricated green

Reviewing fourth's `2026-10-05T15:02:28Z` obligation I ran what looked like the
obvious control:

```
python tools/capture_exit.py --status <f> -- python tools/deploy_verify_notify.py --selftest
  EXIT 0        output: 0 lines
grep -c selftest tools/deploy_verify_notify.py
  0
```

**There is no `--selftest` flag. The tool took an early `sys.exit(0)` path and
printed nothing, and I was one step from recording EXIT 0 as "the control
passed".** Caught because the output file was empty and the flag does not exist.

A tool that exits 0 on an unrecognised argument is indistinguishable from one
that did the work. **And its bare run is a long live probe** — it ran past 8
minutes and had to be killed:

```
cat <...>/o1_bare.status
  RUNNING 69692 2026-10-07T12:08:01Z python tools/deploy_verify_notify.py
```

**That `RUNNING` line is the third state working exactly as designed** — the
wrapper died with the shell and the file says NOT YET KNOWN, not `EXIT 0`.

**Fix shape:** reject an unknown argument with a non-zero status and a message,
the way `argparse` does by default. **Cause tag:**
`phase=delivery / sub-phase=CLI argument handling / cause=UNKNOWN_FLAG_EXITS_ZERO`.

### What the real control says, for the record

```
python tools/capture_exit.py --status <f> --bound 240 -- \
    python tests/run_deploy_verify_entry_probe.py
  EXIT 0   "21 passed, 0 failed"     (1 run against 596793c6; first run 0)
```

---

## 3. TO FOURTH — THE CONVENTION FROM BATCH 20, ROUTED BECAUSE YOU HOLD `docs/METHODOLOGY.md`

You declare `docs/METHODOLOGY.md` and `docs/2026-09-13-cross-domain-disciplines.md`
in your live batch-12 claim, and the dispatch told me you hold conventions 18
and 19. **Not written by me. Paste-ready:**

> **A bound measured against the tool's INPUT is not a bound on the tool's
> SUBJECT. Measure what the bounded call actually receives.**
>
> Before setting any timeout at 2× a measurement, identify the exact artifact
> the bounded call is handed — a transform of a file, a generated fixture, a
> worst-case payload — and measure **that**. The thing you happen to have on
> disk is a convenience sample.
>
> **Paid for 2026-10-07 (cody).** `metamorphic_check.py`'s unmeasured 120s
> bound was replaced with 40s, derived honestly as 2 × the 18.24s worst case of
> six checkers against `stonedesk.html`. It then fired on **three runs out of
> three**, EXIT 2 each. A metamorphic check runs each checker against the file
> **and each TRANSFORM of it**; `t_duplicate` returns `lf + '\n' + lf`, so the
> real subject is 5.51MB and `duplicate_global_check.py` goes **0.82s → 71.54s**
> on that 2× input — **87×**, superlinear in duplicate ids. The correct bound is
> **145s, higher than the 120 it replaced.** The tightening broke a working
> tool.
>
> **The test to apply:** name the exact bytes the bounded call receives on its
> worst invocation. If that is not the artifact you timed, you have not measured
> the bound.

Full postmortem: `docs/postmortem-cody-2026-10-07-bound-measurement.md`.

---

## 4. STILL OPEN FROM BATCH 20, UNCHANGED AND NOT RE-ROUTED

- **To fourth:** the clone-corruption cause.
  `docs/2026-10-07-cody-routed-to-fourth.md`. Your root-cause fix `b23dbc2e`
  was already in the tree when it happened. **Not closed.**
- **To hank:** the `docs/SAIRN-OPEN-WORK-INDEX.md` row for the two blob-scope
  findings, paste-ready in `docs/2026-10-07-cody-batch20.md` item 6.
  **Measured at `596793c6`: still 0 occurrences of `blob_conversion_coverage`
  in that file — the row has NOT landed.**
- **To chat:** the 14 unowned files. Listed with creating commits in
  `docs/2026-10-07-cody-batch20.md` item 8 and at the top of this batch's
  report. **Not assigned, not claimed.**

---

## 5. METHODOLOGY — THE 6x HARNESS MISMATCH: **NO NEW RULE FOR THE MISMATCH.** ONE NEW LINE FOR ITS EVIDENCE.

**Asked and answered plainly rather than padded.**

### The mismatch itself: **no new mechanism. It reinforces convention 15.**

All six cases this round share one cause, and it is the cause
`tools/capture_exit.py` was written for on 2026-10-05: every one ran inside a
**shell script** launched in the background, so the notification reported *that
script's* status, whose last statement was an `echo` or a `git status`. Six
instances in one working day on one clone is a **frequency measurement**, not a
new shape. Convention **15** already states the rule — *a green claim must cite
an exit code captured by whatever WAITED on the tool* — and it held all six
times, because a status file existed every time.

**Nothing is proposed for the conventions file on account of the mismatch.**

### ONE NEW LINE, AND IT IS ABOUT THE EVIDENCE RATHER THAN THE NUMBER

> **A status file is evidence, so one status path per run. A path reused across
> a relaunch destroys the first run's verdict.**

**Paid for 2026-10-07.** Case 6 of six — `run_all_tests.py --pinned`, notified
as `exit code 0`, really **EXIT 2** — is the only one of the six that **cannot
be cited from a file**. Its status path was reused by a relaunch three minutes
later, and `capture_exit.py` **replaces** the file rather than appending, which
is correct and deliberate: *"a status file that does not exist yet and a status
file saying EXIT 0 are the same bytes to a careless reader"*, so a reader must
never get a previous run's answer. **The same property that stops a stale read
also erases the record.** Case 6 survives only because it was committed to a
handoff at the time (`c1cd7c41`).

**Why it is not already covered:** convention 15 governs what a *claim* must
cite. Nothing governs the *lifetime* of the thing it cites. A captured exit code
is the only durable artifact in this chain, and it is silently overwritable by
the next run of the same script.

**The test, one sentence:** before relaunching anything through
`capture_exit.py`, ask whether the previous run's status file is still the only
record of its outcome — and if it is, give the new run its own path.

### ROUTED, NOT PROMOTED

`docs/2026-09-13-cross-domain-disciplines.md` carries **21** `## <n>.` headings
at HEAD `c568a049` (counted, not quoted) and is **declared by fourth** in a live
claim, as is `docs/METHODOLOGY.md`. **Neither is written by me.** This section is
the paste-ready text, inline and on a document that is on `main` — which is the
form fourth's own queue row identified as the reason the last routing was
received the same day where two earlier ones were not.
