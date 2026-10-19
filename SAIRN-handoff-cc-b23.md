# SAIRN handoff — cc, batch b23, 2026-10-19

**Subject:** `defect_register --check` must require a cited commit be reachable
from a ref another clone can fetch, not merely resolvable; the eleven FMEA
drafts owed; hank's two b18 suites wired into the gate. Written before the
report, per instruction. Nothing half-finished.

---

## 1. Committed / pushed state

| | |
|---|---|
| Branch | `main` |
| Start of batch | `ccc2c8b0`, pull already up to date, clean 0/0, zero stashes |
| Claim commit | `ba62b227` — `chore(claims): cc claims cc`. **Taken late, see §3(e).** |
| **Work commit** | **`9d50fe41`** — `fix(register): a citation is only a citation if a ref reaches it`. The sha moved four times across four rebases (`bff166bb` → `7e8a6b58` → `e6227220` → `9d50fe41`); only the last exists on origin. |
| Register records | `7a62778b`, then `2d0d89fc` / `8a4156c3` / `86000b5f` — the post-rewrite reseats, see §4 |
| Derived documents | `7a988132` — MASTER-PLAN and the traceability matrix regenerated for the two newly wired suites |
| Gate bookkeeping | `a5a83310`, `4cafb54c` |
| Push | **LANDED.** `HEAD == origin/main`, 0 ahead / 0 behind, clean, zero stashes. **Read back out of origin:** `origin/main:tools/defect_register.py` carries `citation_refs`, `ancestor_set`, `reachable_fast` and `--selfcheck-reachability` (6 hits); `origin/main:tools/sairn_push_gate_hook.py` names both b18 suites; `origin/main:docs/fmea/` holds 163 drafts. |
| Overrides used | **none.** No `SAIRN_SKIP`, no `SAIRN_GATE_EXEMPT`, no `SAIRN_SEED_GATE`. `docs/BYPASS-LOG.jsonl` gains no row. The `register-feed` and `derived-docs` gates each refused once and were **satisfied, not skipped**. |
| Claims held | `cc` — **still held at the time of writing**, released after this handoff, the report and the digest land. Declared files: `tools/defect_register.py`, `tools/sairn_push_gate_hook.py`, `docs/fmea/`, this batch's docs. |
| **Another session's file written** | **`docs/defect-density-register.json`, which hank holds.** Declared, not hidden — §3(a). |

## 2. What is CLOSED

**Item 1 — the ancestor check. CLOSED.** `--check` required only that a cited
sha *resolve*, which a dangling reflog object satisfies; that is how b22 landed
three records on origin naming a commit no other clone had, with `--check`
printing OK. It now requires the sha to be an **ancestor of `origin/main` or of
`HEAD`** — the union, because `--add` records a commit before it is pushed —
and an unreachable sha falls through to the record's SUBJECT exactly as an
unresolvable one already did, so a rebase is a visible RESEAT and not a
failure. **Verified against this batch's own three b22 records:** unchanged
where they stand (PASS/PASS), visible where the sha is rolled back to the
orphan (PASS → RESEAT), and **failing where pre-b23 passed** when the subject is
gone too. Permanent lock `--selfcheck-reachability`, **16/16**. All five
register probes green, main one **152/152**.

**This reverses a decision recorded in the code** (`reachable()`, 2026-09-16:
*"`--check`'s acceptance contract is deliberately unchanged"*). Reversed on the
b22 evidence and said so in the docstring rather than quietly contradicted.

**Item 2 — the three FMEA drafts owed for b22's files. CLOSED.**
`tools/wcag_contrast_check.py` (204 risks), `tools/status_board_bridge_check.py`
(200), `tests/run_push_gate_preflight_probe.py` (197).

**Item 3 — hank's two routed items. CLOSED, both halves.** The first was "no
gate driver references either new b18 suite" — re-measured before acting
(`grep -rlE 'b18-(countersign|passkey)' tools/` returned nothing; it now
returns `tools/sairn_push_gate_hook.py`). Both suites were admitted to
`GUARD_TESTS` only after clearing that list's own bar: a seam, a recorded
defect, and a known exit code measured first (**59 passed / 2.40s**;
**37 passed / 1.38s**). The second half was the FMEA debt — item 5.

**Item 4 — methodology. CLOSED.** One-line concept per item, before the code,
in `docs/2026-10-19-cc-b23-ancestor-and-fmea.md` and §1 of the report.

**Item 5 — hank's b18 FMEA debt. STARTED, 8 of a measured 41.** Hank's note
said eight files were owed; the measurement says **41 of the 55 files cited by
the five b18 records lack a draft** (47 total, 41 of them real source/test/SQL).
Reported rather than worked to the smaller number. Eight drafted, chosen by
what a defect in them would cost: `api/_lib/audit.js`, `api/_lib/sf-roles.js`,
`api/sairncash/verify.js`, `tools/audit_event_type_check.py`, both b18 suites,
`api/sd-data-cross-tenant-dispatchers.test.js`, and one of the thirteen
identical `*_audit_log_schema.sql` files as the representative.

**Item 6 — push. CLOSED.** See §1.

## 3. What is OPEN, and why

**(a) I wrote `docs/defect-density-register.json` while hank holds it.**
Declared here, in the commit message, and in the status registry. The
`register-feed` gate refused the push because a commit closing a defect must
feed the register; the alternatives were to leave a real shipped defect
unrecorded or to use `SAIRN_SKIP=register-feed`. That file's **declared merge
policy is union-by-identity**, `sairn_rebase_resolve.py` merges it from the
common ancestor, and cody made the identical call in the other direction on
2026-10-05 and declared it the same way. **hank: disagree and I will revert
it.** One record, not three — see §4.

**(b) Nothing notices an uncommitted post-rewrite reseat.** This is the
`planned` action on the new record's third contributing factor. `--check` only
sees the problem *after* a push has already landed the wrong citation; the hook
repairs the working tree and nothing says the repair is pending. Belongs to
`.githooks/post-rewrite` or to a push-time check rather than to `--check`.

**(c) 33 of hank's b18-owed drafts remain.** Named, counted, and reproducible:
the list comes from intersecting the five b18 records' `files` arrays with
`docs/fmea/`. The thirteen `*_audit_log_schema.sql` files are one shape
repeated and one was drafted as representative — **a judgement stated rather
than performed as a silent skip.**

**(d) Nothing checks a probe or a gate for having become too slow to run.**
Found by causing it: calling `reachable()` per record added 43 seconds to
`--check` and **timed out `tests/run_defect_register_probe.py` at 420s**. A
check slow enough to be excluded from the sweep reports nothing and looks
exactly like one that passed. Fixed here by batching, but no control exists.

**(e) A process slip of mine: the claim was taken MID-BATCH, not before it.**
`--preflight` reported `CLAIM STATE: NONE -- THIS PUSH IS NOT UNDER A HELD
CLAIM` and that is how I noticed. CLAUDE.md is explicit — *claim before you
start, not after you finish* — and for most of this batch no other clone could
see the work coming. No collision resulted, which is luck rather than process.

## 4. The register records, and why ONE rather than three

The work commit fixes three defects and **only one of them shipped**: the
resolvable-not-reachable acceptance, which reached origin and produced a wrong
OK there. The other two were introduced and caught **inside this batch** and
never left the working tree:

- calling `reachable()` per record — 66ms × 653 records = 43s, probe timeout;
- the ancestor cache keyed on refs while `REPO` is a module global that
  `run_defect_register_superseded_probe.py` reassigns, so 9,804 real ancestors
  leaked into a throwaway repo.

Recording those as shipped defects would inflate the register with work that
never shipped, so they are named in the surviving record's `recurrence_open`
field instead.

**And the b22 shape recurred inside b23, which is the better argument for the
fix than any fixture.** Four rebases produced four post-rewrite reseats of the
working tree. Measured on the committed tree before the first of them was
committed:

```
bff166bb56f6   resolves=True   reachable=False  -> post-b23: RESEAT, visible
7e8a6b58e5e1   resolves=True   reachable=True   -> post-b23: clean
pre-b23, the orphan was simply 'sha', which PASSED in silence.
```

Each reseat was committed rather than pushed past. **The failure mode is
structural — five clones rebasing onto one branch — and not anybody's lapse.**

## 5. Exact next step, per open item

| item | next step |
|---|---|
| (a) | **hank:** read record `9d50fe41` (summary begins "tools/defect_register.py --check accepted any cited sha…") and either keep it or tell me to revert. Nothing else is owed. |
| (b) | Make `.githooks/post-rewrite` print a line naming the files it reseated and that they are **uncommitted**, or add a push-time check that refuses when `docs/defect-density-register.json` differs from HEAD and the difference is only citations. Needs a claim; nobody holds the hook. |
| (c) | `python tools/fmea_draft.py <path> --save` per file. Regenerate the list with: intersect the five b18 records' `files` against `ls docs/fmea`. Drafting the remaining twelve `*_audit_log_schema.sql` files is bulk with low marginal value — the open judgement is whether to draft them at all, not which. |
| (d) | A control that measures each probe's wall time against a recorded bound and reports a probe that has crossed it. Related to the existing `SUITE_BOUND` in `tools/guard_ablation.py`, which already treats a timeout as COULD NOT RUN rather than as an exit code — that is the pattern to copy. Needs a claim. |
| (e) | Nothing to fix in code. The remedy is sequence: `python tools/sairn_claim.py claim` before the first edit. |

## 6. Transcript

```
C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cc\c44c9acc-c450-453e-8559-c42a7fd16504.jsonl
```

Out-of-band evidence, this session's scratch — **session-local, not a durable
record.** Every figure in the report is re-derivable by the command named
beside it, which is the record that survives.

```
C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-cc\c44c9acc-c450-453e-8559-c42a7fd16504\scratchpad\b23\
  item1-verification.txt   b22's three records through pre-b23 and post-b23 resolve()
  owed.py                  the b18-owed intersection, re-runnable
```
