# SAIRN handoff — cc, batch b22, 2026-10-19

**Subject:** the contrast baseline's hyphenated-stem blind spot; the bridge
check's uppercase `--agent` false CLEAN; the preflight probe's stale injection
anchor; re-driving H1's b61 claim; the paste paragraph for the other three
build agents. Written before the report, per instruction.

---

## 1. Committed / pushed state

| | |
|---|---|
| Branch | `main` |
| Start of batch | `809176fc`, pull already up to date, clean 0/0, zero stashes |
| Claim commit | `cc3b0e24` — `chore(claims): cc claims cc` |
| **Work commit** | **`a61abc5a`** — `fix(filters): three selections that silently picked the wrong set and reported clean over it`. Rebased once while the remote moved, so the sha ran `634f7d70` → `a61abc5a`; only the last exists on origin. |
| Register commit | `b9eb68d2` — three records, one per defect. **Its message cites `634f7d70`**, the pre-rebase sha; a commit message cannot be reseated, the records themselves were. |
| Gate bookkeeping | `03fd98e9` |
| Reseat fix | `c3b3f658` — see §3(a); origin had briefly landed a register citing a commit that exists in no other clone |
| Push | **LANDED.** `HEAD == origin/main`, 0 ahead / 0 behind, clean, zero stashes. Read back **out of origin**: `origin/main:tools/wcag_contrast_check.py` carries `is_product_stem`, `origin/main:tools/status_board_bridge_check.py` carries `selects`, `origin/main:tests/run_push_gate_preflight_probe.py` carries `source.rfind(anchor)`, and `origin/main:docs/wcag-contrast-baseline.json` is `total 8, written_by cc, files_scanned 22`. `a61abc5a` is an ancestor of `origin/main`. |
| Overrides used | **none.** No `SAIRN_SKIP`, no `SAIRN_GATE_EXEMPT`, no `SAIRN_SEED_GATE`. `docs/BYPASS-LOG.jsonl` gains no row. The `register-feed` gate refused the first push and was **satisfied, not skipped** — three real records. |
| Claims held | **none at the time of writing** — released after this handoff, the report and the digest land. While the batch ran: `cc` on `tools/wcag_contrast_check.py`, `docs/wcag-contrast-baseline.json`, `tools/status_board_bridge_check.py`, `tests/run_push_gate_preflight_probe.py` and this batch's docs. |

Files changed by `a61abc5a`:

```
tools/wcag_contrast_check.py              is_product_stem() + derived provenance;
                                          lock 41/41 -> 58/58
tools/status_board_bridge_check.py        selects() used by BOTH call sites;
                                          lock 39/39 -> 45/45
tests/run_push_gate_preflight_probe.py    anchor on the LAST occurrence;
                                          13 passed, 0 failed
docs/wcag-contrast-baseline.json          17 files -> 22, total 0 -> 8
docs/2026-10-19-cc-b22-case-and-stems.md                  new, all four items
docs/2026-10-19-context-line-paragraph-for-dispatches.md  new, item 5
```

## 2. What is CLOSED

**Item 1 — the contrast baseline could not see five of its own products.
CLOSED.** `product_files()` excluded any root stem containing a hyphen, which
removed the five sub-apps rather than narrowing the list to products. Now a
prefix rule over the whole stem. `--static --all` 17 files → **22**; the **8**
findings (6 `sairndental-book`, 2 `sairndental-complaint`) are recorded;
both files now pass the gate at exit 0 with their debt printed per app.
**The ratchet is intact** — a NEW below-AA rule planted in a copy of a
now-baselined file still denies at exit 1.

**Item 2 — uppercase `--agent` skipped the nonce check and printed CLEAN.
CLOSED.** One `selects()` now answers the selection question for both the row
filter and the nonce gate; the CLEAN summary derives from a `nonce_checked`
count instead of from a nonce having been supplied; an `--agent` matching
nothing is `COULD NOT RUN` exit 2 instead of CLEAN over an empty set. H1's
never-written-nonce negative control is permanent and synthetic, and
**ablated**: the pre-b22 expression scores 36/42.

**Item 3 — preflight probe RED 3/13. CLOSED, 13 passed 0 failed.** Its
injection anchored on the FIRST of two occurrences and the first is inside a
string literal on a real code line in the hook, added after the probe was
written. Anchors on the LAST occurrence now, and **refuses** when the anchor is
absent.

**Item 4 — H1's b61 claim re-driven. DONE, and the answer is a correction.**
The verdict was right and its stated reason was wrong. See §4.

**Item 5 — the paste paragraph. DONE, not run on anyone's session.**
`docs/2026-10-19-context-line-paragraph-for-dispatches.md`, and reproduced
verbatim in §5 below.

**Item 6 — push. DONE.** See §1.

## 3. What is OPEN, and why

**(a) `defect_register.py --check` passes on a commit that exists only in a
local reflog. ROUTED, NOT FIXED — it is a different check from the three this
batch was sent at.**

Found by causing it. `.githooks/post-rewrite` fired on the b22 rebase and did
exactly its job: it rewrote the three records from `634f7d70` to `a61abc5a`
using git's own old→new map. **It wrote the working tree. Nothing committed
it**, so the push that followed landed the pre-rebase citation — origin/main
briefly carried three records citing a commit that exists in no clone but
this one's reflog. Fixed in `c3b3f658`.

`--check` passed the whole time **in this clone**, because it asks whether the
cited commit *resolves* rather than whether it is an *ancestor of
origin/main*. An orphan kept alive by a reflog resolves. In any other clone the
same records would have failed on an absent commit.

*The fix:* `--check` should require `git merge-base --is-ancestor <sha>
origin/main`, with a could-not-tell when `origin/main` is not fetched — not a
pass. And something should notice a post-rewrite reseat that is sitting
uncommitted, because a correct repair nobody commits is invisible.

**(b) No FMEA draft exists for any of the three files changed.** The register
printed this three times, once per record:
`python tools/fmea_draft.py <file> --save` would make the next defect in each
of them scoreable. Not done — three drafts is its own piece of work, and
hank's b19 note already says FMEA drafts are owed for eight other files.

**(c) hank's two items routed to cc are still NOT started and were not in this
batch's claim.** No gate driver references either new b18 suite (`grep -rlE
'b18-(countersign|passkey)' tools/` returns nothing), and FMEA drafts are owed
for eight new/changed files. Carried forward from b21 unchanged.

**(d) The 8 contrast findings themselves are debt, not fixed.** Routed to
fourth. See §6.

## 4. Item 4 in full — the verdict was right, the reason was wrong

`--agent H1 --nonce H1-NONCE-1792420981`, both cases, exit 1, identical
output: the nonce is not in H1's registry row.

**But the old finding text said flatly** *"the WRITE did not land -- this is a
finding about `sairn_status.py`, not about the board."* Measured: that nonce is
absent from the row **and present on the Drive mount** in
`SAIRN-handoff-H1-b61.md` and `SAIRN-report-H1-b61.txt`. The write landed.
H1's row has moved on three batches and now reads `h1 b64: repro for cc, nonce
intentionally absent from this task string`.

A row holds **one** task string, so the check cannot distinguish *never
written* from *written and since superseded*. It now names both causes and
prints the row's own `updated` stamp, which is the one piece of evidence that
separates them. Three new arms lock it, one an ablation that fails on the
pre-b22 wording.

**So: the b61 bridge claim is not re-verifiable.** The row it concerned has
been overwritten and no tool can recover a superseded task string. What IS
verified is the live bridge **now**, both directions:

| invocation | exit | result |
|---|---:|---|
| `--agent H1 --nonce <never-written>` | 1 | FINDING |
| `--agent h1 --nonce <same>` | 1 | FINDING — byte-identical |
| `--agent H2 --nonce H2B63-9a2f84dd` | 0 | CLEAN, nonce crossed both ends on 1 row |
| `--agent h2 --nonce <same>` | 0 | CLEAN — byte-identical |
| `--agent zzz` | 2 | COULD NOT RUN, names the valid names |

The H2 rows are the positive direction on live data — hover2's real current
nonce — without which the tool could pass by refusing everything.

## 5. Item 5 — the paragraph, verbatim, for Michael to paste

> **Context figure — run these two before you write your digest.** The digest's
> `CONTEXT` line is no longer something you type: push-gate CHECK 5c (gate id
> `context-digest`) re-derives it from your own transcript and **denies** a push
> carrying a digest of your own session whose line is not a measurement. Run, in
> this order, once per session:
>
> ```
> python tools/context_verify.py --provision-window 1000000
> python tools/context_verify.py --digest-line
> ```
>
> Paste the second command's output verbatim as your digest's `CONTEXT` line.
> **Step one is not optional and skipping it is not a formality:** the window
> inference is a *floor*, so on a fresh session it reported cc at 70.9% of
> 200,000 while the session was a 1M one at 14.2% — wrong by five times, in the
> alarming direction. Until your session declares its window, the row reads
> AMBIGUOUS, both candidate percentages print, and `--digest-line` refuses to
> emit a figure rather than emitting the ceiling. The declaration is keyed to
> your **session**, not your clone, so a new session declares again. The gate's
> refusal names both commands, so you cannot get stuck — but you will lose a
> push if you find out at the end of the batch.

`1000000` is right for an Opus 1M session, which all four build clones have
been on; `200000` otherwise. The tool refuses a declaration **smaller** than a
prompt it has observed and cannot catch one that is too large, which is why it
is scoped to one session. **Nothing is to be run in hover or hover2** — both
are outside `context_verify.py` by the separation boundary and CHECK 5c returns
COULD_NOT_TELL on their digests rather than refusing them.

## 6. Exact next step, per item

| item | next step |
|---|---|
| 1 | **fourth:** fix the 8, not the instrument. Six are `#fff` on `var(--p)` or `var(--pd)` on `var(--pt)` in `sairndental-book.html` / `sairndental-complaint.html` — the same shape b29 fixed in `sairndental.html` by darkening the brand surface. Then `--static --all --baseline-write` should take `total` back to near zero. The remaining two are `#fff` on `var(--danger)` at 3.76:1 and `var(--pd)` on `#fff` at 4.10:1, both inline on buttons in `-book`. |
| 2 | Nothing owed. If you want a stronger guarantee, the one gap named in the register's `recurrence-open` is that the fixtures reproduce `live()`'s selection logic rather than calling `live()`, which needs a registry and a mount — so a future `live()` that stops calling `selects()` at one site is caught only by the manual live drive. |
| 3 | Nothing owed on the probe. The register's `recurrence-open` names the residual: the new refusal fires when the anchor is ABSENT, not when it matches the wrong occurrence; a third occurrence appearing before the real one is caught only because `compile()` would raise again, which is luck rather than a control. |
| 4 | A verdict about b61 specifically would need a nonce from b61's own row, which no longer exists. If H1 wants a verified bridge claim, write a nonce in the CURRENT row and re-drive — the b64 row is already set up as a repro and the never-written direction is confirmed. |
| 5 | Michael pastes §5 into hank, cody and fourth's next dispatches. |
| (a) | Harden `defect_register.py --check` to require ancestry of `origin/main` rather than mere resolvability, with a could-not-tell when origin is unfetched. Needs a claim; nobody holds `tools/defect_register.py`. |
| (b) | `python tools/fmea_draft.py tools/wcag_contrast_check.py --save` and the same for the other two files. |
| (c) | hank's two routed items need a claim first; still unclaimed. |

## 7. Transcript

```
C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cc\c44c9acc-c450-453e-8559-c42a7fd16504.jsonl
```

Out-of-band evidence, this session's scratch — **session-local, not a durable
record.** Every figure in the report is re-derivable by the command named
beside it, which is the record that survives.

```
C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-cc\c44c9acc-c450-453e-8559-c42a7fd16504\scratchpad\
  ablate/pre_fix.py, ablate/ablate_out.txt   selects() ablated to the pre-b22
                                             expression: 36/42, six arms fail
  ratchet/sairndental-complaint.html         the planted NEW finding that still denies
```
