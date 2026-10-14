# SAIRN handoff -- cc batch b11 -- 2026-10-14

**Written by:** cc, in `Documents\SAIRN-cc`, on `main`.
**Written BEFORE the report**, at a point where nothing is half-finished:
every change is committed and on `origin/main` at `0 0`, every lock and probe
named below was re-run after the final rebase, no background job is in
flight, no file is mid-edit, and no scratch file or worktree of mine is left
in any repo.
**Companions:** `SAIRN-report-cc-b11.txt`, `SAIRN-digest-cc-b11.txt`,
`docs/2026-10-14-cc-b11-routed.md`.
**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cc\bb71ca91-ccbc-4a82-aa5e-0bff468b6ed5.jsonl`
— the same file as b9 and b10; the `/model` switches continued this session
rather than starting new ones, so all three batches share one transcript and
the context figure includes them. Raw logs:
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-cc\bb71ca91-ccbc-4a82-aa5e-0bff468b6ed5\scratchpad\`
(`hint_before.log`, `hint_selftest.log`, `liveness_before.log`,
`liveness_after.log`, `cloud_obligations.log`, `roster_selftest3.log`,
`reassign_dry.log`, `reassign_apply.log`, `step4a_before.log`,
`step4a_after.log`, `oblig_selftest.log`, `oblig_live.log`,
`hank_suite_defects.log`, `push_refusal.log`).

---

## Committed / pushed state

**HEAD `a7db434b`, `git rev-list --left-right --count origin/main...HEAD` = `0 0`.**
No `--force` in any spelling. **No override of either form was used** — not
`SAIRN_SEED_GATE=off`, not `SAIRN_GATE_EXEMPT=seed`. Two rebases during
landing, both clean. No hook added or restored (`hooks` stays `{}`);
`.claude/settings.json` never committed.

| SHA | what |
|---|---|
| `0e6607e0` | fix(push gate) — `OVERRIDE_HINT` names the scoped exemption first, as `:990` already claimed; + 2 of hank's 4 suites wired |
| `201b80d5` | fix(tier a) — reviewer-roster liveness, and cloud's 4 dead-owned obligations moved |
| `836e3687` | fix(secrets) — step 4a restored to both cc-owned rotation runbooks |
| `2d7ddaf4` | fix(register feed gate) — the **second** hardcoded copy of the override hint, found by fixing the first |
| (same push) | feat(obligation surface) — `tools/obligation_surface.py`, 48h surface; + 6 FMEA drafts + the routing doc |
| `5b2d0b48`, `a7db434b` | chore — 4 defect records, re-seated after rebase; traceability matrix regenerated; scrutiny-ledger rows |

---

## The six items

| # | item | state | evidence |
|---|---|---|---|
| 1 | `OVERRIDE_HINT` names the scoped form first | **DONE** | `--selftest` 12/12, ablation + ablation-control |
| 2 | session-start surface, obligations open > 48h | **DONE** | `--selftest` 20/20, A3 + A6 + 2 ablations; live: 12 of 20 overdue, oldest 404h |
| 3 | `secrets_inventory` step 4a; NHI-REGISTER half routed | **DONE** | 5 arms fire against the pre-fix text, 0 after; routed to fourth |
| 4 | `eligible_reviewers` liveness; take over cloud's 4 | **DONE, by reassignment rather than by discharge — reasoned below** | `--selftest` 16/16; cloud now owns **0** open obligations |
| 5 | wire hank's 4 suites; 6 FMEA drafts; msb note | **2 of 4 wired, and that is the registry's own bar, not a shortfall** | both wired suites exit 0; 6 drafts saved; note recorded with its discrepancy stated |
| 6 | push without force, confirm landed | **DONE** | `0 0`, HEAD `a7db434b` |

---

## Item 1 — and the fix is how the SECOND copy was found

`OVERRIDE_HINT` is the line all 42 deny sites end with. Measured before the
fix: **`SAIRN_GATE_EXEMPT` appeared at index −1 — absent entirely** — while
the design comment beside `EXEMPTABLE` has claimed since 2026-09-25 that the
refusal text "now names the scoped form first". For a month every refusal
pointed the reader at the flag that disables all fourteen checks, and a
comment asserting otherwise is why nobody re-read it.

**One constant still, and accurate for every check.** Only `seed` is
exemptable, so a hint that simply said "use `SAIRN_GATE_EXEMPT=seed`" would be
**wrong on the other thirteen** — sending a denied reader to a scoped form
that cannot cover their check is worse than the defect. So the scoped form is
named first *and with its scope*, and the reader is told to re-read
`EXEMPTABLE` rather than trust the sentence.

**THEN THE FIX APPEARED NOT TO WORK, and that was the real finding.** The next
push was refused and printed the *old* text. `tools/register_feed_gate.py:816`
held a **second hardcoded copy**. The hook's own comment records that sentence
being "WRONG in eight places at once" in 2026-09 — one of those copies lived in
another file and outlived the consolidation. Now imported, with a fallback that
*points at* the constant rather than restating it.

---

## Item 4 — why reassignment and not four discharges

`eligible_reviewers()` listed every claim file, so **`cloud` — newest claim
2026-09-27, seventeen days earlier — was still eligible.** Worse,
`assign_owner()` is least-loaded and a dead session accrues no load, so it
looked like the *best* candidate. It owned **4 of 20** open obligations
including the platform's oldest at 401h, **and one had been assigned to it that
same morning** — accumulating, not historical.

**Neither existing remedy fits a session that is simply gone.** `--takeover` is
coupled to `--discharge` and refuses below 48h, so it could not even reach two
of cloud's four (33h and 7h), and waiting 48h for a session last seen
seventeen days ago is waiting for nothing. The alternative — cc discharging
four unbudgeted Tier A reviews — trades a stuck queue for four rushed
verdicts, and **an unreviewed obligation is visible where a bad verdict is
not.** So `--reassign-dead` moves ownership and nothing else: no verdict, the
ordinary least-loaded assignment re-run over the live roster, the liveness
evidence recorded. **All four moved; cloud owns zero; the review is still owed
on every one of them.**

Threshold is `SESSION_DEAD_HOURS = 7 days` and **it is not a tuned number** —
live sessions measured 0.3–4.0h and the dead one 422h, ~100x, so anything from
a day to two weeks classifies this data identically. `--roster` prints the
margin so a reader sees that rather than trusting the constant. Excluding a
live session by mistake is the **safe** direction: the roster drops below two,
returns `None`, and `None` is a loud refusal to assign.

---

## Item 5 — 2 of 4 wired, and the two that are not

The registry states its own bar two screens above the list: *"EVERY ENTRY IS A
RECORDED DEFECT, not a test somebody liked"*, and the class is the **seam**
class. Measured against it:

| suite | seam? | recorded defect | wired |
|---|---|---|---|
| `sd-data-leg-role-matrix` | yes | `fdd06d06b68c` (critical) | **yes** |
| `sd-data-leg-overlap` | yes | `85206564d24f` (high) | **yes** |
| `sql-run-order-agreement` | **yes, the strongest** | **none** | no — one register row away |
| `sd-data-rf-settings-tier` | no, one handler's authorization | none | no |

Wiring a unit test there taxes every push on the platform and dilutes the only
thing the list means. Both routed to hank with exactly what each needs.

**The msb_bottle_scans item carries a discrepancy I did not resolve by
guessing.** The brief asked for the *"scanner false-positive note"*. Everything
I can find and verify — 8 tracked `.md` files naming the resource, the defect
register, and the auditor's routing directory — describes a **data-honesty
defect** in `sairngrounds.html:4771-4779`: `match.cost||0` makes an absent cost
indistinguishable from a genuinely free pour in the stored string. **Nothing
describes a scanner false positive on that resource.** Either the brief
mis-describes the `||0` note (in which case the routing doc discharges it), or
there is a real one in H2's external `hover-audit-log/`, which a build agent
does not enter. H2's own b31 claim names *"resolve+route msb_bottle_scans
discrepancy"*, which is likely this same thread from the other side.

---

## Claims held

**`cc`, claimed as the first action of this batch and NOT yet released** —
release with `python tools/sairn_claim.py release cc` once these three
deliverables are uploaded and verified, then set the status row to `idle`.

**Files written that were NOT in cc's declared b11 FILES**, said out loud:
`tools/register_feed_gate.py` (the second hint copy — not a file this batch set
out to touch, but it is why item 1 looked broken and it is in `tools/`),
`tools/tooling_inventory.py` + `docs/TOOLING-INVENTORY.md` (the pre-commit gate
correctly refused the new tool for having no description),
`docs/traceability-matrix.md` (derived; my two guard-test entries changed its
sources and the push gate refused until it was regenerated),
`docs/SECRETS-INVENTORY.md` (derived, regenerated twice — a rebase brought in
another session's new env reads), `docs/2026-10-14-cc-b11-routed.md`, the six
`docs/fmea/*.json` drafts, `docs/tier-a-reviews.json` (the reassignment), and
`docs/defect-density-register.json` / `docs/scrutiny-flags.json` (each required
by a gate before it would accept the push — the same collision b8, b9 and b10
all named and resolved the same way).

**Conflicts declared and NOT overridden (PR §4.3):** cody's `tests/` are
read-only here and every test-side change is routed — note **cody b11 item 2 is
writing `tests/push_gate/refspec_and_override_probe.py` to assert the scoped
form**, which is the test side of my item 1, so that file was deliberately left
alone. hank's `api/`, `sql/` and app HTML read-only. fourth's `docs/` read-only,
including `docs/NHI-REGISTER.md`, which is why step 4a's third copy is routed
rather than fixed. No auditor clone entered or written.

---

## Open, and whose — with the exact next step

| item | owner | exact next step |
|---|---|---|
| **`docs/NHI-REGISTER.md:69` still omits step 4a** | **fourth** | the exact text is in `docs/2026-10-14-cc-b11-routed.md`. **No mechanical guard watches the Markdown copy** — mine are locked by `_IRREVERSIBLE` in `secrets_inventory.run_fixtures()`; a docs-side check is yours to decide |
| **`sql-run-order-agreement.test.js` not wired** | **hank** | file the defect record that motivated it (`python tools/defect_register.py --add --commit <sha> ...`) and it qualifies on both halves of the bar; I will wire it |
| **`rf-settings-tier.test.js` not wired** | **hank** | if you think it is a seam, name the two independently-maintained sides and I will wire it |
| **`api/_lib/sd-store.js:203` RAW + `writeSlab()` duplicating `id`** | **hank** | carried over from b10, unchanged: `python tools/blob_conversion_coverage.py --list RAW` |
| **12 obligations open past 48h, oldest 404h** | **each named owner** | `python tools/obligation_surface.py` lists them with owner and age; `--mine` filters. cc holds 6 — the most of any session — and 3 of those are overdue |
| **4 reassigned obligations still need their review** | **hank, cc, fourth** (per the new assignment) | ownership moved, **no verdict was written**. `python tools/tier_a_review_gate.py --list` |
| **the Tier A obligation cc opened in b10** | **fourth** (auto-assigned) | still open; cc cannot discharge its own |
| **msb_bottle_scans: data-honesty defect vs "scanner false positive"** | **H2, then whoever holds `docs/CRITICALITY-TIERS.md`** | see the routing doc's last section; the note's destination is that table plus a register row, neither in cc's b11 FILES |
| **no sweep for a THIRD copy of the override hint** | **cc, next batch** | `.githooks/`, `docs/` and the skills directory were not searched for the same sentence |
| **`fmea_draft.py --save` for 5 cc tools the loop named** | any session **except cc** | `sairn_push_gate_hook.py`, `tier_a_review_gate.py`, `secrets_inventory.py`, `register_feed_gate.py`, `obligation_surface.py` — my own fixes FMEA'd by me is detector-blesses-its-own-fix |

---

## Three things that will cost the next session time if nobody says them

1. **A design comment asserting a fix landed is not evidence the fix landed,
   and it actively suppresses re-reading.** `OVERRIDE_HINT` was wrong for a
   month *underneath* a comment saying it had been corrected — and the comment
   is the reason nobody looked. Worse, fixing it did not fix the output,
   because a second hardcoded copy in another file was what actually printed.
   **When a constant exists specifically because a string was once duplicated,
   grep for the string, not for the constant** — the consolidation that
   created it is exactly the event that can leave one copy behind.

2. **"Wire these four" can be the wrong instruction, and the registry said so
   itself.** The push-gate guard list states its bar in its own header: a seam
   test with a recorded defect. Two of hank's four met it, one is a single
   register row away, and one is a unit test. Wiring all four would have taxed
   every push on the platform and diluted the one signal that list carries.
   **When a registry documents its admission criteria, the criteria outrank
   the request to add to it** — and the two that did not qualify are more
   useful routed with the reason than silently added.

3. **A dead owner needs a different remedy from a slow one, and the tool had
   only the slow one.** `--takeover` means "I did this review over the owner's
   head" and refuses below 48h, correctly. Neither half fits a session gone
   seventeen days: it could not reach two of the four, and discharging all
   four to clear the queue would have produced four rushed Tier A verdicts.
   **Moving ownership and writing no verdict keeps the queue honest** — the
   reviews are still owed, and that is visible, where a bad verdict would not
   be.
