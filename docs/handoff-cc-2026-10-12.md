# SAIRN-PLATFORM — 2026-10-12/13 — cc batch W (b4, resume) handoff

**Written by:** cc, in `Documents\SAIRN-cc`, on `main`.
**HEAD at open:** `4024ab44` (tree dirty: 1 modified, 1 untracked).
**HEAD at close:** `71a61f4c`, ahead 0 / behind 0 of `origin/main`.
*(This read `2697518e` when first written. The push that landed this
handoff was itself refused by the Tier A gate — for resource names that
appear only in the report and digest beside it — and the four commits that
answer that refusal come after the close the first draft recorded.)*
**Companion files:** `SAIRN-report-cc-b4.txt` (full account),
`SAIRN-digest-cc-b4.txt` (one line per item, questions for Michael).

---

## READ THIS FIRST — every SAIRN app is down

`sairn.vercel.app` returns **HTTP 402 Payment Required on every route**,
measured with `tools/sairn_http.py` while doing the push protocol's
live-verification step:

```
402  https://sairn.vercel.app/
402  https://sairn.vercel.app/stonedesk
402  https://sairn.vercel.app/sairnbuild
402  https://sairn.vercel.app/api/sd-data
```

402 from Vercel is a disabled project — a billing or spend-limit state. It is
not a failed deploy, not a code fault, and no commit can repair it. Every
customer-facing URL on the platform is serving nothing, including the API
proxy every app depends on. **Only Michael can fix this.**

**Do not report any fix as live-verified until this is back.** A 402 is
UNVERIFIED, the same rule as a 403 (PR §3.2) — not verified-good and not
verified-bad.

---

## The clone was disarmed at pickup

`.claude/settings.json` in the working tree carried `"hooks": {}` against **23
committed hook commands** — every PreToolUse gate, every PostToolUse check,
the SessionStart suite, the PreCompact handoff reminder. The indentation was
PowerShell's, so a `ConvertTo-Json` round trip had rewritten the file and
dropped the nested object.

It was safe to restore rather than a judgement call because the untracked
`.hooks.bak` beside it was **byte-identical to `HEAD`** after `tr -d '\r'` —
so the backup proved nothing was ever meant to change. Restored with `git
checkout --`, wiring re-counted at 23 commands, `.bak` removed only after the
comparison.

**Three sessions have now hit this** (hank in b20, fourth in its released
claim, cc here). If your tree shows `M .claude/settings.json` and you did not
edit it, read the diff before anything else.

---

## What landed

Every commit below is on `origin/main`, verified with `git log origin/main`.

| SHA | What |
|---|---|
| `3b99c19c` | `fix(hover separation)` — **not this session's commit**; unpushed at pickup, carried through and recorded |
| `86189e37` | **`fix(bld_draws)` — the AUTH_BYPASS, seq664**, client and server |
| `9b0bfd51` | `fix(claim matcher)` — the declared FILES set is the primary mode |
| `dd1bcbe2` | `chore(tier A)` — the obligation, plus the phantom-limb fixture rename |
| `aff7f8ce` / `0cbd7a84` | claim taken / two expired claims released |
| `5ae06f11` · `9d55424e` · `2697518e` · `1c4ccfb6` | register records and three SHA re-seats across five rebases |
| `2a1189d2` · `ad04aa57` · `1c4ccfb6` | five Drive handoffs declared, across three separate push refusals |
| `cc6d3c52` | `fix(register feed gate)` — D9 on the third gate |
| `9d435023` | `feat(defect register)` — `--supersede`, the writer the field never had |
| `22e11a16` | `chore(register)` — two records |
| `acab264c` | `docs(handoff)` — this file, the report and the digest |
| `23d0f73c` | **`fix(tier A gate)`** — a batch REPORT at the repo root was being read as code serving a Tier A resource. It refused the push carrying this handoff |
| `7b9ee1c2` | `chore(derived + external files)` — MASTER-PLAN regenerated; all 17 Drive handoffs declared at once instead of one per refusal |
| `71a61f4c` | `chore(register)` — the record for that false positive |

---

## The bld_draws bypass, in one paragraph

`wip` and `release_retainage` on `bld_draws` were gated behind a sairnbuild
session and owner/office. **`read` and `write` on the same table** fell through
to the generic `BLD_RESOURCES` loop and took the licence key alone — so a
caller with the key and no session could read every draw's retainage figures
and, worse, POST `action:'write'` with a `data` blob of its own choosing. That
write is a merge-duplicates upsert which replaces `data` entirely, so one
unauthenticated request could author a release that never happened, inflate
one, or set `retainage_released` back to zero, defeating
`bld_release_retainage_atomic`'s CAS, the no-reduce rule in
`api/_lib/wip-accounting.js` and the append-only trail at once, with no
employee recorded.

**Two things fix it, and the second is not optional.** A session is now
required; and the three release-owned fields are **carried over from the stored
row**, never taken from the caller. Stripping them would blank a real release
on the next ordinary draw save, because `sairnbuild.html` echoes them back
through this same generic write. The pre-read fails closed.

**Control, measured both ways:** section 5 of
`api/_lib/sairnbuild-retainage-endpoint.test.js` — 35/0 with the fix, **30/5
against the stashed pre-fix handler**, the five failures being the bypass
itself. A sixth arm (another tenant's draw) passes both ways and is reported as
such: licence scoping was never the hole.

**The product question is open — see Q2.**

---

## Open, and whose

| Item | Owner | Note |
|---|---|---|
| **Platform 402** | **Michael** | Nothing in the repo is wrong |
| `bld_draws` role scope | **Michael** | Q2 below |
| External-file gate pattern allowance | whoever owns `tools/external_file_index_check.py` | **Five** refusals in one session, six files, none of them cc's; **two** of them denied the compound command that would have fixed them. In the end every `.md` under the directory was declared at once (17), which shortens the loop and does not close it |
| Tier A obligation on `bld_bids`/`bld_draws` | **hank** | Assigned by the gate; only hank can discharge it (or anybody after 48h with `--takeover`) |
| `E9` of `run_defect_register_probe.py` | whoever owns that probe | Red before and after this batch; its throwaway worktree is built from the LIVE register, so another session's rebase leftovers decide its colour. NOT edited to pass |
| Convention 25, `METHODOLOGY.md` Rule E | fourth (files were its in FILES) | Removed from this batch's scope rather than reworded (PR §4.3). fourth's claim has since been released, so the files are free — but they are not in this batch's claim either |
| 8 of 11 `sd-data.js` ownership rows, 4 `ai-scan-redaction.js` candidates | unassigned | Not in this batch's declared FILES, not started |
| `leg_invoices` fixture in `run_fileset_matcher_probe.py` **section 3** | whoever owns that probe | Will re-open a phantom Tier A obligation on the next edit to that file. This batch's own new fixture was renamed to avoid it |

---

## Things that cost this batch real time, so they do not cost yours

1. **Reach for `tools/sairn_rebase_resolve.py` on the FIRST ledger conflict.**
   It does union-by-identity from the common ancestor — the merge policy
   `docs/defect-density-register.json` declares about itself. Taking origin's
   copy whole works and throws away every record you wrote; that cost two
   rounds here before the tool was used.

2. **Issue the push as its own top-level command.** Not inside a script, and
   not in an `&&` chain with the edit that clears a gate. A nested `git push`
   gives the pre-push hook no ref lines (that is the D9 refusal fixed this
   batch), and the PreToolUse half of a gate can deny the **whole** compound
   command — at which point nothing in it ran, including the fix.

3. **No backticks in a CLI body.** Two backquoted fragments — the command that
   was refused and the reason it was refused with — were executed by bash and
   vanished out of a register summary, leaving holes exactly where the evidence
   had been. Caught only by reading the record back. Records are now added
   through a Python `argv` list so no shell sees the text.

4. **`git diff --numstat` before every commit to a generated document.** A
   one-string correction to the register produced **26,701 insertions /
   26,576 deletions** because `json.dumps` reformatted the file. Reverted and
   redone through the tool that owns the format.

5. **The parked-stash count in a brief is a claim.** The brief said "hank's
   5"; there were seven. Each stash was read by file list before being
   dropped, and hank's own register stash — `stash@{5}`, not a scrutiny row —
   was preserved.

---

## Questions only Michael can answer

**Q1. The platform.** `sairn.vercel.app` is 402 on every route including
`/api/sd-data`. Billing or spend limit? No live verification of anything is
possible until it is back.

**Q2. `bld_draws` role scope.** Should the draw schedule be management-only, as
SAIRNroofing's `rf_draws` is for the same resource? Today any signed-in
SAIRNbuild employee can read and save a draw, because the Draw Requests panel
is not role-gated client-side. This batch deliberately did **not** change that
inside a security fix: management-only on the server alone would 403 every
field role's save with a silent `console.warn`. If the answer is yes, the UI
needs gating in the same change.

**Q3. The external-file gate.** Approve a pattern allowance for handoff-shaped
names under `G:/My Drive/SAIRN-status`? It is declared non-transient, so every
handoff written there blocks the next push from every clone until it is named
by hand — three refusals in this session alone, and the third blocked the
command that would have cleared it. The gate's real teeth (an undeclared
**tool** or **script**) would be untouched.

---

*No overrides. `SAIRN_SEED_GATE=off` was never used; every gate that refused
this push was satisfied rather than bypassed.*
