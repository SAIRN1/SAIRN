# SAIRN handoff — cc, batch b25, 2026-10-19

**WRAPPED UP ON INSTRUCTION at 81.0% real context, mid-batch.** One item was
finished to a clean stopping point; five were not started. Nothing is
half-finished and nothing is left uncommitted.

---

## 1. Committed / pushed state

| | |
|---|---|
| Branch | `main` |
| Start | `b2c28034`, clean, zero stashes |
| Claim commit | `5ac8f8ad` — `chore(claims): cc claims cc`, taken **before the first edit** |
| **Work commit** | **`ef623db0`** — `fix(path-manifest): a flag's value is not a path, and the proxy it exposed is withdrawn` |
| Register | `b44d4f1e` + three post-rewrite reseats (`497745c9`, `cf187713`, `26e87a89`) |
| Push | **LANDED, no force.** `git fetch` then `git rev-list --left-right --count origin/main...HEAD` → **0 0**, read from the remote. Clean tree, zero stashes. |
| Overrides | **none.** No `SAIRN_SKIP`, no `SAIRN_GATE_EXEMPT`, no `SAIRN_SEED_GATE`; `docs/BYPASS-LOG.jsonl` gains no row. The `register-feed` gate refused once and was **satisfied, not skipped**. |
| Claims held | **`cc`**, released after this handoff, the report and the digest land. |
| Exclusions honoured | `api/`, `tests/`, every `.html`, and `~/.claude/settings.json` **untouched**. |
| Read back from origin | `origin/main:tools/sairn_path_manifest.py` carries `paths_from_argv`; `origin/main:docs/sairn-path-manifest.json` has `assigned_overrides: {}` — still empty, deliberately, see §3. |

## 2. What is CLOSED

**Item 1 — the override, and the answer is that NO ENTRY SHOULD EXIST.** The
instruction was an entry "covering only cody's already-pushed `.html`
commits". **Measured: cody has pushed zero `.html` files.** All 13 `.html`
paths behind b24's "cody 50 paths, 14 REFUSED" come from **one** commit,
`50f67cfe`, author `fx`, subject *"fix(contrast): 153 findings down to 3, app
by app, and the 3 left are **cody's file**"* — fourth's commit, fourth's own
files, entirely in scope, with `cody` appearing only as a possessive. So
b24's figure was **100% false positives for that population**, the
DECISION-NEEDED it produced is **withdrawn**, and writing an override would
have widened cody's manifest on the strength of a measurement error — the
opposite of the instruction's own "do not widen cody's manifest".

**The refusal is re-driven and still correct**, which was the second half of
item 1: `--agent cody stonedesk.html` → `FOREIGN`, exit 1, *"inside '*.html',
which fourth owns and cody does not"*; `--agent cody tests/x.js` → `OWNED`,
exit 0.

**And the drive exposed a real defect in my own b24 tool, now fixed.**
`--check` collected every argument after itself that did not start with `--`,
**swallowing the value of `--agent`**: `--check --agent cody a.html`
classified a path literally named `cody` and reported four paths where three
were given. **The push verdict was still right, which is why it survived** —
`cody` matched no prefix, read UNOWNED, the three real paths were still
refused. A wrong line inside a refusal somebody is meant to act on is worse
than a wrong exit code, because the exit code is the part a reader
re-derives. Extracted as `paths_from_argv()`, pure and locked: **31 → 37
arms**, with the real invocation as the arm, a flag-after-paths negative
control so the fix is not position-dependent, and an **ablation** showing the
pre-b25 expression returning the agent name as a path.

Recorded in the register as `538af8d5`/`ef623db0`, **injection commit named as
my own b24 `38bbd455`**, so the discovery lag is one batch and measured.

## 3. What is OPEN, and why

**(a) `--history`'s attribution is unsound and the mode is unchanged.** It
attributes by searching the commit **subject** for an agent name. It cannot be
fixed by switching to the author field: **measured, every commit in this repo
is authored by `Michael Dibert`, `SAIRN1` or `fx`**, so git carries no
per-population signal at all. The claims files are definitive but only for
claim/release commits — 237 of the last 800 — and those carry no work paths.
Left open rather than half-changed during a wrap-up. It is the `planned`
action on the new record's third contributing factor.

**(b) `assigned_overrides` stays `{}`** — not because the question is
unresolved but because there is nothing for an entry to cover. If cody is
assigned `.html` work in future, the entry is written **then**, naming that
work.

**(c) Items 2–5 were NOT STARTED.** Sabotage-testing CHECK 5d from a scratch
clone for all four populations plus an auditor path; the currency sweep and
the Agents.md consolidation status; the register status of the four named
items; and the next 11 FMEA drafts. No partial artefacts exist for any of
them — nothing to revert and nothing uncommitted.

**(d) Carried, still not started:** nothing notices an uncommitted
post-rewrite reseat (it happened **three times** in this batch's own push loop
and each was committed by hand), and nothing checks a probe for having become
too slow to run. Plus the b24 carry-overs: the `rt_stops.license_hash` landing
obligation for cody, the egress disclosure for fourth, and the two stale
justifications in fourth's files.

**(e) `tools/sairn_path_manifest.py` has no FMEA draft.** The register said so
on this very record. One command, not done.

## 4. Exact next step, per open item

| item | next step |
|---|---|
| (a) | Decide between **removing** `--history` and **reframing** it as a per-path ownership census that attributes nothing. The measurement is done: subject-matching is ~100% wrong for at least one population and the author field is uniform. Do not keep a table whose numbers cannot be acted on. |
| (b) | Nothing, unless cody is assigned `.html` work. Then: one entry, naming the assignment. |
| (c) item 2 | `git worktree add` a scratch clone, provision it as each population in turn with `tools/sairn_session_identity.py --provision`, plant one out-of-scope path per population plus one under `.claude/skills/sairn-hover-auditor/`, drive `echo "" \| python tools/sairn_push_gate_hook.py --pre-push` for each, and remove the worktree. The two-direction drive already exists for `cc`; the other three and the auditor path are what is missing. |
| (c) item 3 | The currency sweep needs the other builders' lists before the shared `~/.claude` and `tools/` items can be edited, which is what the instruction said. cc-owned items can be swept first and independently. |
| (c) item 4 | Four register lookups: board STATUS/NEXT label growth, publisher stale-clone version check, wcag hyphenated-stem baseline (b22, believed landed — `--selftest` 58/58), bridge nonce case (b22, believed landed — `--fixtures` 45/45). The last two need a register *status* read, not a re-drive. |
| (c) item 5 | `python tools/fmea_draft.py <path> --save`, 11 files. Regenerate the owed list by intersecting the five b18 records' `files` arrays against `ls docs/fmea`. **33 remain, 12 of them identical `*_audit_log_schema.sql` files with one already drafted as the representative** — the open judgement is whether to draft those twelve at all. |
| (d) | Each needs a claim; nobody holds `.githooks/post-rewrite` or a timing control. For the second, copy `SUITE_BOUND` in `tools/guard_ablation.py`, which already treats a timeout as COULD NOT RUN rather than as an exit code. |
| (e) | `python tools/fmea_draft.py tools/sairn_path_manifest.py --save` |

## 5. Transcript

```
C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cc\c44c9acc-c450-453e-8559-c42a7fd16504.jsonl
```

Scratch, session-local and not a durable record:
`...\scratchpad\b25-rec.txt` (the register summary as submitted).
Every figure above is re-derivable by the command named beside it.
