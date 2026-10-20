# SAIRN handoff — cc, batch b26, 2026-10-20

**STOPPED ON INSTRUCTION.** Two items closed, one item's work was **generated
and then lost by my own cleanup** and is not committed, two items not started.
Nothing is half-finished in the tree: the only uncommitted thing was the
`--history` removal and it is committed and pushed.

---

## 1. Committed / pushed state

| | |
|---|---|
| Branch | `main` |
| Claim commit | `79396e86` — taken **before the first edit** |
| **Work commit** | **`ab25e4c5`** (as landed) — `decide(path-manifest): --history is REMOVED, because a mode that cannot attribute must not attribute` |
| Push | **LANDED, no force.** `git fetch` then `git rev-list --left-right --count origin/main...HEAD` → **0 0**. Clean tree, zero stashes. |
| Read back from origin | `origin/main:tools/sairn_path_manifest.py` has **0** occurrences of `def cmd_history` and **1** of the removal notice. |
| Overrides | **none.** No `SAIRN_SKIP`, no `SAIRN_GATE_EXEMPT`, no `SAIRN_SEED_GATE`; `docs/BYPASS-LOG.jsonl` gains no row. No gate refused this push. |
| Claims held | **`cc`**, released after this handoff, the report and the digest land. |
| Exclusions honoured | `api/`, `tests/`, every `.html`, `~/.claude/settings.json` **untouched**. |

## 2. What is CLOSED

**The b24 argv bug was ALREADY FIXED in b25 — verified, not assumed.**
`origin/main` carries `paths_from_argv()`, the lock is **39/39**, and the drive
is clean: `--check --agent cody sairnroofing.html sairnscape.html
stonedesk.html` → *"REFUSED: 3 of 3"*, no phantom row. Nothing was needed this
batch; re-fixing it would have been work on a closed item.

**The `--history` decision: REMOVED and documented.** Concept stated first:
*a mode that cannot attribute must not attribute.* Three measurements made the
choice rather than a preference — the subject is not an author (b24's "cody 14
REFUSED" was one commit of fourth's, 100% false positives); the author field is
no better (every commit here is `Michael Dibert`, `SAIRN1` or `fx`); and the
claims files are definitive but carry no work paths (237 of the last 800
commits, all claim/release). The flag still **prints the reason and exits 2**
rather than erroring, because a removed flag that silently does nothing is the
same defect one layer out. `--history` stays in `FLAGS_WITH_VALUES` **with an
arm saying why**: an old invocation must not have its count classified as a
path, which is the b25 defect one flag over.

**Item 1 — CHECK 5d sabotage-tested, 5/5.** From a scratch worktree, each
population provisioned by its own `.git/sairn-session` marker, one out-of-scope
path planted and committed per population plus one auditor path, each driven
through the **real pre-push hook**. All five **REFUSED in-clone**, with the
planted path named and the deciding rule named:

| population | planted | verdict |
|---|---|---|
| hank | `tools/zz_b26_probe.txt` | REFUSED, FOREIGN |
| cc | `api/zz_b26_probe.js` | REFUSED, FOREIGN |
| cody | `stonedesk_zz_b26_probe.html` | REFUSED, FOREIGN |
| fourth | `tests/zz_b26_probe.js` | REFUSED, FOREIGN |
| cc | `.claude/skills/sairn-hover-auditor/tools/zz_b26.py` | REFUSED, **AUDITOR** |

**AND THE FIRST RUN OF THAT HARNESS REPORTED A FALSE PASS, WHICH IS THE BEST
FINDING IN THE BATCH.** It reported hank as **ALLOWED**. The cause was not
CHECK 5d: the **pre-commit** hook had refused the plant (`tools/*.py` with no
inventory entry), so the commit never happened, and the harness then drove the
pre-push hook over a **clean tree** and read that pass as a result. *A probe
reporting a verdict on a test it never ran.* Hardened: the harness now asserts
its plant is in the outgoing range before driving the hook and reports **COULD
NOT RUN** otherwise, and hank's plant was changed to a `.txt` so an unrelated
rule cannot swallow it. **The 4/5 figure from the first run must not be
quoted — it was 4 real passes and one untested case.**

## 3. Item 4 — register status for the four named items

| item | status | evidence |
|---|---|---|
| **board STATUS/NEXT label growth** | **PARTIAL** | `56d267e3b169`, moderate. The CONTEXT cell is fixed and has arms. Its own `recurrence_open` says: *"The STATUS and NEXT fields are parsed the same way and still swallow unlabelled prose; they are bounded by their own 900-character slices, so they degrade quietly rather than wrongly."* One of its four factors is `planned`: the board is a reader of six other agents' files and its parse assumes only the nine labels it knows. |
| **publisher stale-clone version check** | **LANDED** | `fb0c90c8` — *"parse(labels)+guard(race): a field ends where its section ends, and a stale clone refuses to revert a newer board"*. The guard is in; the residual parse gap is the PARTIAL row above, not this one. |
| **wcag hyphenated-stem baseline** | **LANDED** | `a61abc5ae46e`, high, code-review. `product_files()` is a prefix rule, 18→19 registries by b24's own measure, and `--selftest` is **58/58**. One factor is `planned`: nothing refuses a baseline whose `files_scanned` is narrower than the gate's universe. |
| **bridge nonce case** | **LANDED** | `a61abc5ae46e`, high, **hover-audit** (H1's b63 finding). All four factors `done`; `--fixtures` **45/45**, including the permanent never-written-nonce control and its ablation at 36/42. |

## 4. What is OPEN, and why

**(a) ITEM 5's TWELVE FMEA DRAFTS WERE GENERATED AND THEN LOST. Zero are
committed.** They were written to `docs/fmea/` (count 162 → 174), and a later
`git worktree remove` failed on a permission error while my shell's cwd was
inside the worktree being removed; the `git worktree prune` / status sequence
that followed ran against the main repo and the untracked drafts are gone —
`docs/fmea` is back to **162** and `git status` shows none. **No information is
lost: every draft is regenerable by one command.** Reported as lost rather than
counted as done.

The eleven intended, chosen by what a defect would cost — and note that the
first list I computed included four `docs/hank-evidence/*.log` files, which was
a filter bug of mine (`docs/hover-evidence/` was excluded, `docs/hank-evidence/`
was not); an FMEA draft for a log file is worthless and they were replaced:
`api/auth-setup-attribution.test.js`, `api/b17-trust-lock-hard.test.js`,
`api/sairncash/verify.test.js`, `api/sd-data-law-role-matrix.test.js`,
`api/sd-data-leg-session-gate.test.js`, `api/sd-data-sf-role-matrix.test.js`,
`api/sd-data-sf-session-gate.test.js`, `sairncash.html`, `api/alf-auth.js`,
`api/leg-auth.js`, `api/sf-auth.js`, plus `tools/sairn_path_manifest.py` as a
twelfth.

**(b) ITEM 2 — the currency sweep and the Agents.md status report — NOT
STARTED.** No partial artefacts.

**(c) The b26 defect record was NOT written.** The `--history` removal is a
decision, not a defect closure, and no gate demanded one; but the sabotage
harness's false pass **is** a defect in a control and deserves a record. Not
written.

**(d) Carried, unchanged:** nothing notices an uncommitted post-rewrite reseat;
nothing checks a probe for having become too slow to run; cody's
`rt_stops.license_hash` landing obligation; the egress disclosure and the two
stale justifications in fourth's files.

**(e) `b24`'s `assigned_overrides` item stays WITHDRAWN** per instruction — no
entry, and not to be revisited unless a real cody `.html` push appears.

## 5. Exact next step, per open item

| item | next step |
|---|---|
| (a) | Re-run the twelve, one command each: `python tools/fmea_draft.py <path> --save`. The list is in §4(a) verbatim. **Commit them in the same action as generating them** — that is the whole lesson here. Regenerate the owed set by intersecting the five b18 records' `files` arrays against `ls docs/fmea`, and **exclude `docs/hank-evidence/` as well as `docs/hover-evidence/`**. 37 owed before this batch, 12 of them identical `*_audit_log_schema.sql` files with one already drafted as the representative; the open judgement is whether to draft those twelve at all. |
| (b) | The sweep's own instruction says the shared `~/.claude` and `tools/` items wait for the other builders' lists. cc-owned items can be swept independently and first. |
| (c) | One record for the harness false pass: `tooling`, `moderate`, `probe-control`, citing PR §1.11 — a control that reported a verdict on a test it never ran. The fix (assert the plant) is `done`; the `recurrence_open` is that no other probe in the repo asserts its own plant landed. |
| (d) | Each needs a claim. For the probe-timing control, copy `SUITE_BOUND` in `tools/guard_ablation.py`, which already treats a timeout as COULD NOT RUN rather than as an exit code. |
| (e) | Nothing. |

## 6. Transcript

```
C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cc\c44c9acc-c450-453e-8559-c42a7fd16504.jsonl
```

Scratch, session-local and **not** a durable record — and the lost drafts above
are the reminder of why:

```
...\scratchpad\b26\sabotage.py          the hardened harness
...\scratchpad\b26\sabotage-out.txt     5/5, the run quoted in §2
```
