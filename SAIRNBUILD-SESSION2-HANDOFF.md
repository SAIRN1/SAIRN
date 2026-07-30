# SAIRNbuild — Session 2 Handoff

## 1. Verified state

- `main` HEAD (pushed): `8033407534c6bfb2f2e6dd91169d5daa97efaa6b`
- **`sairnbuild.html` has UNCOMMITTED work in the tree** — the Change Orders
  panel, built and passing every check, never committed (the commit was
  interrupted). See §3. This is the first thing to deal with.
- Live at `https://sairn.vercel.app/sairnbuild` (routed in `vercel.json`).
- Re-verify `main` and `origin/main` match before extending anything.

## 2. Where SAIRNbuild stands

Scope is final in `SAIRNBUILD-SCOPE.md` (`9a99b89`), all four open decisions
resolved: `bld_*` table + localStorage prefix, `BLD-` licence prefix, build
order `dashboard → jobs → jobcost → changeorders`, Bids deferred out of v1
(v1 = 16 panels).

**Built and committed (3 of 16):**

| Panel | Commit |
|---|---|
| App shell, gate, PIN, Dashboard, Job Board, demo seed, Vercel route | `8c49663` |
| Seed correction — J-2602 now renders a real negative margin | `4d017fb` |
| Job Costing | `b9a6c52` |
| Responsive layer (shared CSS, not a panel) | `8033407` |

**Built but NOT committed (4th):** Change Orders — see §3.

**Licence is provisioned and working.** `BLD-PINNACLE-2026` returns `200`
from `/api/sd-data` (was `401` earlier the same day). The gate accepts it,
PIN passes, and the Crew read now resolves to a real array. It returns `[]`
for an honest reason worth knowing: all 8 employee rows for that tenant were
deliberately voided earlier (status set non-Active), and the read filters
`status=eq.Active`. So the empty Crew panel is correct data, not a failure.

## 3. FIRST THING: commit Change Orders

The panel is written into `sairnbuild.html`, passes everything, and is
uncommitted. Either commit it as-is or review it first — but do not start new
work on top of an uncommitted panel.

What it does: 5 KPIs, job + status filters, per-order table with rejection
reasons inline, add/edit modal, contract-impact roll-up, CSV export. Seeded
across all four states (accepted / sent / draft / rejected).

**The load-bearing decision in it:** only **accepted** change orders move
contract value. `acceptedCOFor()` / `revisedValue()` are the single place
that rule lives, and `marginPct()` now divides by revised value. Counting
draft/sent COs as revenue would inflate contract value and flatter every
margin on the Dashboard. It is stated in the UI too, not just in code.

Because of that, contract value was updated everywhere it is read, so no two
panels can disagree: `rDash()` headline, Job Board contract column (with an
"incl. $X in COs" note), Avg Contract KPI, and the jobs CSV — which now
carries Original Contract, Accepted COs and Revised Contract as separate
columns rather than silently replacing the signed figure.

Verification already run on the uncommitted file: checkblocks 1/1,
div_balance 239/239, duplicate_global 51/51 distinct 0 dupes, panel_nesting
4/4 safe 0 trapped, zero duplicate ids. Dead-button audit A=0 B=0 C1=0 C2=0
D1=0 D2=0, E=1 (hand-checked false positive, see §4).

**Not yet live-verified** — it was never deployed, because it was never
committed. Do that after committing.

## 4. Open decision — the audit tool's E check

This is where the session stopped, mid-discussion. Nothing was changed.

**A correction to carry forward:** I earlier told Michael the E check was
"0-for-7 on true positives" and suggested cutting it. That was wrong — it
lumped together two separate scans with opposite records:

**Half (a) — explicit unbuilt-feature phrases** (`coming next build`,
`coming soon`, `not yet implemented`, `TODO`, `FIXME`, `work in progress`…)

- SAIRNbiz: 6 × "coming next build" — **true positives**, real unbuilt features
- SAIRNbuild: 1 × "work in progress" — false positive, construction domain term

→ **6 true / 1 false. Earns its place.**

**Half (b) — bare `placeholder` scan**

- StoneDesk: 3 — false, CSS `::placeholder` selectors
- SAIRNvet: 4 — false, honest prose + a correctly-named `placeholderId` var

→ **0 true / 7 false. Has never found anything.**

**Recommendation on the table (not yet approved):** keep half (a), drop
`work in progress` from its pattern list (collides with the construction/
accounting term WIP, and is the only thing half (a) has ever gotten wrong),
and cut half (b) entirely.

**Two questions were put to Michael and are unanswered:**
1. Cut half (b), or keep it as a deliberately noisy prompt for a human read?
2. Drop `work in progress` from the list, or keep it and accept SAIRNbuild's
   one standing false positive?

Do not change `tools/sairn_dead_button_audit.py` until those are answered.

## 5. Standing constraints for this build

Carried from the scope doc and from bugs this project has already been
burned by. Each of these exists because it was violated somewhere:

- **One licence resolver**, never inlined at a call site (`bldLicenseKey()`).
  StoneDesk had that logic copy-pasted six times across three spellings.
- **No client-side Supabase.** All data access goes through `/api/sd-data`
  with the licence as a bearer token. `anon` is locked out of every table by
  design; StoneDesk and SAIRNbiz both had to abandon direct client calls.
- **Every KPI computed, never hardcoded.** SAIRNbiz shipped a `$498,000`
  literal next to a real computation.
- **Conditional severity colours.** A bad number must never render in the
  "good" colour — SAIRNbiz shipped −40% margin in green.
- **KPIs describe the filtered scope**, and the CSV exports exactly the rows
  on screen. Shared `*Scope()` helpers exist so numbers, table and export
  cannot disagree.
- **Save functions carry forward unrendered fields.** SAIRNbiz's `saveEmp()`
  wiped employee benefits exactly that way.
- **Save functions refresh dependent panels.** Costs and accepted COs both
  feed margin; without the refresh the Dashboard shows a stale figure.
- **Seed guards check `null` explicitly**, not falsiness — `JSON.parse('[]')`
  is truthy, so a `|| SEED` guard silently re-seeds an emptied list. Found
  live in StoneDesk's remnant module.

## 6. Known tooling caveats — do not mistake these for defects

- **`nav_panel_check.py` always FAILs on SAIRNbuild.** It is hardcoded to
  StoneDesk's `class="sb-btn"` + `sbNav()` convention; SAIRNbuild follows
  SAIRNbiz's `class="sb"` + `nav()`. The same script fails **all 20**
  sairnbiz panels and **all 80** sairnvet panels identically. Reconcile nav
  by hand instead: panels, `sb-` buttons and `nav()` targets must match
  1:1:1, plus zero duplicate ids.
- **Responsive CSS is "valid and deployed, rendered behaviour UNVERIFIED."**
  Do not upgrade that wording without a real device or a working viewport
  resize. Both media queries were confirmed parsed into the CSSOM (24 rules,
  expected selectors) and the unconditional `.tw` table wrapper was verified
  working live — but `resize_window` reported success while `innerWidth`
  stayed 2124 and `matchMedia` stayed false, the silent no-op documented in
  `sairn-visual-review`'s Environment Requirement. Flag it if a way to get a
  true 390px render check becomes available.
- **A method error worth not repeating:** the phone-width audit was done by
  setting `document.body.style.width`, which constrains layout but does NOT
  change the viewport, so media queries never evaluated. The structural
  findings held regardless (fixed 220px sidebar, hard 5-col `.krow`, 25px/38px
  touch targets, zero media queries), but any claim about media-query
  behaviour from that method is unfounded.

## 7. Next steps

1. **Commit Change Orders** (§3), then live-verify it against
   `sairn.vercel.app/sairnbuild`.
2. **Resolve the E-check questions** (§4), then patch
   `tools/sairn_dead_button_audit.py` if approved.
3. **Continue the build order.** Dashboard, Job Board, Job Costing and Change
   Orders are the four highest-pain panels and the pattern is now proven; the
   remaining 12 are additive. `SAIRNBUILD-SCOPE.md` §2 has the full list.
4. Nothing is blocked on Michael any more — the licence row was the last
   blocker and it is provisioned.

## 8. Other apps — all closed, do not reopen without reason

- **StoneDesk** — 3 deferred-architecture items all closed this session
  (`ad7efe4` remnant double-render, `13e95e9` identity consolidation,
  `84a2925` template dedup). Audit clean, Guardian green.
- **SAIRNbiz** — 4 CRITICAL + 6 visual-review findings closed; `syncEmps()`
  migrated onto `/api/sd-data` and proven end to end through the real UI.
- **SAIRNcode / SAIRNvet** — closed.
- Two carried notes: 8 void employee rows in the `Headless Check Co` tenant
  are removable only via the Supabase dashboard, and SAIRNbiz has no
  employee-removal path (status is the only lever). Neither is a bug
  introduced here.

## 9. Verification reminder

Guardian v2 before every push (`node --check` via checkblocks, div balance,
duplicate ids, nav reconciliation), `sairn_dead_button_audit.py` clean on
A/B/C2/D1, and every change live-verified against the deployed URL rather
than assumed from a clean push. Re-verify any claim in this document,
including this one.
