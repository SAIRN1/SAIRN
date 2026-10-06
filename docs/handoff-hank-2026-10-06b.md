# Hank handoff — 2026-10-06, batch 10 (resumed after compaction)

**Written at a point where nothing is half-finished.** Everything below is either
pushed to `origin/main` or named as open with the exact next step.

**Tree at writing:** `git status` clean, ahead 0 / behind 0 of `origin/main`,
HEAD `78324f56` plus the documentation commit that carries this file.

**Transcript / working files:**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-hank\16753c01-e018-4c71-af08-342c1baa72e6\scratchpad`
— every `capture_exit` status file, every captured run, the three one-off
scripts (`reg_add.py`, `reg_add2.py`, `fix_repo_root.py`, `add_row.py`) and the
**unusable** `cite_enclosure_sweep.py` described in the inventory §5.

**Full detail:** `docs/2026-10-06-inventory-hank-batch10.md`.

---

## PUSHED — what landed, and the evidence for each

| what | commit | evidence |
|---|---|---|
| #894 `alf_compliance_rules`/`evaluate` role gate | `16b2cc70` (landed before this session resumed) | 16 arms, 3 runs, EXIT 0; **mutation-checked: 3/13 red against `16b2cc70^`** |
| `gate_parity_check.py` cross-resource grouping | `e7adad94` (ditto) | selftest 9 arms, 3 runs, EXIT 0; real-file diff proves `alf_staff_credentials` clean at HEAD and flagged pre-fix |
| duplicate `PURPOSES` key refuses | `19c872e0` | injected duplicate → **EXIT 2** naming the key and both lines; probe 5 arms, 3 runs, EXIT 0 |
| the orphaned SHA this session created | `3521f8c6`-lineage | `03d03cf7` → `16b2cc70`, confirmed by subject + reachability + `git log -S` |
| the three probes' `__file__` fallback | `6a4ee580` | **seen red first: 16/3 pre-fix, arm B returning `C:\Users\marsh` from all three**; 22/0 after, 3 runs |
| panel-auditor + agents README | `104ab3ff` | see **AGENT LIMITS** below |
| two defect-register records | `19c872e0`, `6a4ee580` cited | 458 records, **0 unreachable** |

**Every green above states its runs.** Nothing here was run once.

---

## AGENT LIMITS — record this, it bounds what the next session can assume

1. **`disallowedTools` / `isolation` frontmatter is NOT CONFIRMED ENFORCED.** A
   live test was run and did not establish enforcement. `panel-auditor` now
   relies on its `tools:` **allowlist**, not on a denial list. Do not write a
   safety argument on the frontmatter.
2. **Subagents had NO Bash session-wide.** Not a scoping decision — the
   capability was absent.
3. **`suite-driver` and `sweep-runner` are UNUSABLE this session.** Both are
   defined with Bash. Anything needing a real exit code ran in the main loop
   through `tools/capture_exit.py`.

---

## OPEN — with the exact next step, per item

### 1. `alf_staff` / `read` is ungated — `docs/SAIRN-OPEN-WORK-INDEX.md:64`
`api/sd-data.js:10144` verifies the session and gates on **nothing else**, then
returns the whole blob per row. `docs/CRITICALITY-TIERS.md:256` rates it **A/A**.
**NEXT STEP:** this is a product decision — which role set belongs on it — and
this batch was told not to make those unilaterally. It is the same open decision
as the seven role sets in `ROLE-SET-SWEEP-HANK-2026-10-06` (`:68`). Ask Michael,
then apply `ALF_CRED_READ_ROLES` or a new set in one change with a test.

### 2. The five platform-work items still routed and not fixed
`docs/SAIRN-OPEN-WORK-INDEX.md` lines `:77`, `:78`, `:79`, `:80`, `:81` —
anchors `HOVER-H2-551-556-564`, `HOVER-H2-557`, `HOVER-H1-906-909` (cody's),
`HOVER-H1-905-910` (fourth's), `HOVER-H1-915`. **NEXT STEP:** two are routed to
other sessions BY NAME and are not hank's to take. Of the three that are,
`employee_id` case-sensitivity (`:77`) is the one with real blast radius — 14
verticals, deactivation defeatable by re-creating a credential in another case.
Start there with a driving probe, not a read.

### 3. Tier A review obligations — BLOCKED, flagged back, not reworded past
**23 of the 31 open obligations are eligible to hank.** The most overdue is
cody's `2026-09-27T02:06:03Z`, **234h**. **ONE WAS DISCHARGED THIS BATCH** —
fourth's `2026-09-26T19:12:42Z`, verdict SOUND, at `2026-10-06T16:44:25Z`.
**NEXT STEP:** `docs/tier-a-reviews.json` is CODY'S under a live claim whose task
text is *"Tier A discharge most-overdue-first"*, verbatim. cc and fourth both
declined on the same ground this cycle. Re-check with `sairn_claim.py list`; if
cody's claim has expired or been released, take the 234h record with
`--discharge --takeover` and nothing else changes.

### 4. 51 unresolvable SHA citations in the open-work index
Measured at `78324f56`: **385** distinct sha-shaped citations, **10** real
objects unreachable from HEAD, **41** not objects in this clone at all. **These
are two different problems and must not be merged** — an unfetched commit from
another clone and a typo are indistinguishable from here. **NEXT STEP:** cc holds
the root cause (`tools/doc_sha_reseat.py`, extending `.githooks/post-rewrite`)
and correctly PROPOSES rather than applies for this file, which is hank's. Wait
for that tool, then run it in propose mode and adjudicate the 41 by hand. Do not
hand-repoint rows; that is what produced the backlog.

Re-measure rather than quoting the figures:

    python - <<'PY'
    import io,re,subprocess
    src=io.open('docs/SAIRN-OPEN-WORK-INDEX.md',encoding='utf-8').read()
    shas=sorted(set(re.findall(r'`([0-9a-f]{7,40})`',src)))
    notobj=[];unreach=[]
    for s in shas:
        p=subprocess.run(['git','cat-file','-t',s],capture_output=True)
        if p.returncode!=0 or p.stdout.strip()!=b'commit': notobj.append(s); continue
        if subprocess.run(['git','merge-base','--is-ancestor',s,'HEAD'],
                          capture_output=True).returncode!=0: unreach.append(s)
    print(len(shas),'cited;',len(unreach),'unreachable;',len(notobj),'not an object')
    PY

**REACHABILITY, NOT EXISTENCE.** `git cat-file -t` answers `commit` for a
dangling object, so a presence check reports every rebase-orphaned SHA as sound.
That is the whole trick and it is why the backlog was invisible.

### 5. The unchecked-clone-root class is NOT swept
Only `probe_public_book_guardian.py`, `rf_claim_gate_live_probe.py` and
`rf_roundtrip_probe.py` are fixed. **Any other tool deriving a clone root from
`__file__`, or from an unanchored `rev-parse`, is fooled by the home repository
in the same way.** `tools/git_discovery_anchoring_check.py` covers the
unanchored half; **the unchecked-fallback half has no sweep.** **NEXT STEP:**
extend that checker rather than writing a second one — it already owns the
hazard and a parallel tool is a second thing to drift. The acceptance test
exists: `tests/run_worktree_root_home_repo_probe.py` arm B2.

### 6. Two methodology rules awaiting intake
`docs/2026-10-06-hank-routed-to-fourth.md` **§5**, rules **A** and **B**.
**NEXT STEP:** fourth's batch-11 claim names "METHODOLOGY intake from
cody/cc/hank". Nothing to do but leave them routed. **Do not self-promote them
into `docs/METHODOLOGY.md`** even though that file is in hank's claim — that is
the thing being avoided.

### 7. `sc_anesthesia_base_units` — CLOSED, with one gap named
All 12 line citations re-derived correct at HEAD; the three IMPOSSIBLE cites
(`4904`/`4905`/`4906` inside a function cited as starting at `:4914`) are gone
and survive only in the row's own account of the error. **The gap the row itself
names is still open:** nothing cross-checks two citations in the same sentence
against each other — the drift tool compares each cite against a write site and
never a cite against a cite. **NEXT STEP:** I attempted a general sweep for that
shape and it is **not usable** (113 flags, and the one case I could adjudicate is
a false positive — it cannot tell a MENTION from a CLAIM, scrubber item 24). It
is in the scratchpad and **none of its flags is routed to anybody.** A usable
version needs a verdict that can say *"this is narration"*, not a narrower match.

---

## CLAIMS HELD

**`hank` / `platform`, still active, NOT released.** Task text is the batch-10
string; `FILES` covers `api/sd-data.js`, `tests/sd_data_alf_compliance_staff_scope.js`,
`tools/gate_parity_check.py`, `tools/tooling_inventory.py`,
`docs/TOOLING-INVENTORY.md`, the three probes, `.claude/agents`,
`docs/CRITICALITY-TIERS.md`, `docs/SAIRN-OPEN-WORK-INDEX.md`,
`docs/METHODOLOGY.md` and this batch's docs.

**Three conflicts declared and none reworded past:**

- `docs/tier-a-reviews.json` is **CODY'S**. One record was written before that
  claim was visible — the discharge of fourth's 237h obligation, through
  `--discharge --takeover`, on a file whose own `merge_policy` is union-by-identity
  and refuses when both sides change one record differently. Not written again.
- `tools/capture_exit.py` is **CODY'S** — adopted as a CALLER, not edited.
- `docs/2026-09-13-cross-domain-disciplines.md` is **FOURTH'S** — the methodology
  rules are routed there rather than promoted.

**`tools/worktree_root.py`, named in the claim's FILES, was never created** and
is not needed: the derivation is eight lines and a shared helper would have to be
imported, which cannot happen before the root is known.

---

## WHAT THIS BATCH WOULD TELL THE NEXT SESSION IF IT COULD SAY ONE THING

**Re-derive the dispatch from HEAD before starting it.** Resuming after a
compaction, the twelve-item list said six things that were no longer true: two
items were already landed, one was half-landed, one subject file had never been
created, one "already fixed" row was genuinely fixed and needed only
verification, and one "already converted" tool was converted *and still wrong in
the branch nobody checked*. Five of six were only visible from the log and the
code; none was visible from the dispatch text.
