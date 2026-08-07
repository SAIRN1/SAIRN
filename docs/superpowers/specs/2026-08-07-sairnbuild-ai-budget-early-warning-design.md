# SAIRNbuild — AI Budget Early Warning (Job Costing addition)

**Status:** Design approved by Michael 2026-08-07. Not yet implemented —
no code written under this spec. Written after brainstorming surfaced
that the original "greenfield SAIRNbuild plan" framing was wrong:
SAIRNbuild is a live, 37-panel app with Job Costing, Lien Waivers, and
Change Orders already built. This spec covers only the one genuinely new
piece: threshold-based overrun detection added onto the existing, live
Job Costing panel (`panel-jobcost` in `sairnbuild.html`).

## 1. Problem

Job Costing already tracks `budget`/`committed`/`actual` per cost-code
line and shows a binary "Lines Over" KPI (committed > budget). There is
no graduated warning — a PM has no signal that a line is *trending*
toward overrun until it's already over. "AI Budget Early Warning" closes
that gap: three escalating thresholds (70/80/90%) computed on
`(committed + actual) / budget`, so risk is visible before the money
has fully moved, not after.

## 2. Non-goals (explicitly deferred, confirmed during brainstorming)

- **No AI/LLM call in the core feature.** Threshold detection is pure
  arithmetic on data Job Costing already has. Per tonight's own standing
  principle (sairn-adversarial-reviewer Persona 4): never spend an API
  call on what deterministic code already computes reliably.
- **No new Supabase table, no new persistence layer.** Fully live/
  ephemeral — recomputed from existing cost-line data on every render.
  A stored, timestamped breach-history audit trail is a real, legitimate
  future enhancement, explicitly out of scope for this pass — same
  discipline as deferring Vendor Catalog/Field Map tonight rather than
  bundling everything into one build.
- **No push notification / toast-on-new-tier-crossing.** Considered and
  rejected: doing that correctly requires remembering what tier was last
  shown per job, which reintroduces the persistence layer just ruled
  out. Dashboard visibility (see §4) delivers the real value (visible
  without hunting for it) without that cost.
- **Certified Payroll, Lien Waivers, Change Orders** — not touched by
  this spec. Lien Waivers and Change Orders are already built and live;
  Certified Payroll is a real gap but a separate, unscoped piece of work.

## 3. Computation

Per cost-code line (existing `budget`, `committed`, `actual` fields,
no schema change):

```
ratio = (committed + actual) / budget
tier  = ratio >= 0.90 ? 'critical'
      : ratio >= 0.80 ? 'warning'
      : ratio >= 0.70 ? 'watch'
      : null
```

`committed + actual`, not `actual` alone — this is the real
construction-industry standard and the only choice consistent with the
feature's own name: "early" means before the money moves (PO'd/
contracted), not after (invoiced). A line whose committed number later
gets renegotiated down is self-correcting — the ratio recomputes and the
tier clears on its own next render; no lingering state to manage,
consistent with the no-persistence decision in §2.

Job-level tier = the highest tier reached by any of that job's lines
(simple OR-rollup, not an average). Rationale: line-level detail is
where a PM can actually act ("Framing Labor hit 85%, look at this now");
job-level is a single at-a-glance risk flag for contexts where line
detail isn't the point (the Dashboard).

`critical` supersedes the existing "Lines Over" KPI (committed >
budget) — every over-100% line is already `>= 0.90`, so `critical`
count is a strict superset. **"Lines Over" is retired as a separate KPI**
in this change, replaced by the Critical count, to avoid two overlapping
signals on the same panel.

## 4. Surfacing

- **Job Costing panel** (existing, modified): each cost-code row in
  `#ctbody` gets a tier badge next to its Variance cell. The existing
  "Cost Code Roll-up" card (`#c-rollup`) gets the same badge per code.
  Wherever jobs are listed/filtered in this panel, each job shows its
  rolled-up tier flag.
- **Dashboard panel** (existing, modified): one new KPI — count of jobs
  currently at `warning` or `critical` (deliberately **excluding**
  `watch`-only jobs, so this stays an "act now" count, not noise from
  jobs that are merely worth keeping an eye on). Computed the same live
  way as everything else on Dashboard — no new state, no new fetch.

## 5. Role gating

- **Job-level tier + dollar/percentage figures**: PM/owner/exec only —
  matches the existing financial-data role gating already used
  elsewhere in the platform (same pattern as StoneDesk's exec
  dashboard). No new role/permission concept introduced.
- **Line-level cost-code detail**: visible to whoever already has
  access to that job's Job Costing panel today. No new restriction.

## 6. Colors — new, not reused from existing semantic colors

**Real constraint found during design, not asserted after the fact:**
`sairnbuild.html`'s current `:root` has `--warn` set to the *same* value
as `--p` (both `#F59E0B`, brand amber):

```css
:root{--p:#F59E0B;--pd:#B45309;--pt:#FFFBEB;--pb:#FCD34D;--bg:#F8FAFC;
--card:#fff;--border:#E2E8F0;--text:#0F172A;--muted:#64748B;
--danger:#EF4444;--warn:#F59E0B;--ok:#22C55E;--sh:0 1px 4px rgba(0,0,0,.08);}
```

Reusing `--warn`/`--p`/`--danger` for the new tiers would make a warning
badge visually indistinguishable from ordinary brand-colored UI chrome
elsewhere in the app, or from the existing danger state. Three new CSS
custom properties, each a genuinely different hue family from amber
(~38°) and from each other — not just a different hex value that reads
the same at a glance:

```css
--tier-watch:    #2563EB;  /* blue    — hue ~221°, informational, low severity */
--tier-warning:  #7C3AED;  /* violet  — hue ~262°, distinct from both blue and amber/red */
--tier-critical: #991B1B;  /* dark maroon red — hue ~0° but ~40% darker/less saturated
                                than --danger (#EF4444); keeps the near-universal
                                red=most-severe convention (breaking that convention
                                for the top tier would cost more clarity than the
                                hue-family overlap risks) while remaining clearly
                                distinguishable from --danger at a glance — verify
                                this visually against --danger before shipping,
                                not just by hex-value difference */
```

Watch (blue) and Warning (violet) are in hue families with zero overlap
with amber or red. Critical intentionally stays in the red family
(convention: red = most severe, breaking that would likely reduce
clarity more than the hue-proximity to `--danger` costs) but is
substantially darker/less saturated than `--danger` — flagged explicitly
here as the one tier color that needs a real visual side-by-side check
against `--danger` during implementation, not just a hex-distance
assumption.

## 7. Optional secondary feature (ships only if wanted, not core)

On-demand "Explain this" button, shown only on a `warning`/`critical`
job — **not** automatic on every render (keeps the core feature's
zero-API-call property intact; avoids unplanned Claude cost). On click,
sends the real computed line-level data for that job only (cost codes,
budget/committed/actual/ratio — nothing else) through the existing
`sairn.vercel.app/api/claude` proxy, with a system prompt grounding it
strictly in the provided numbers (same anti-fabrication discipline as
tonight's SAIRNgrounds Ecosystem Health Report — told explicitly not to
invent anything beyond what's given). Output: plain-language summary of
which cost codes are driving the overrun and by how much.

## 8. Testing

- Real interaction test (not just code review): seed/use a real job with
  cost-code lines at various ratios, confirm each tier's badge appears
  at the right boundary (69%→none, 70%→watch, 80%→warning, 90%→critical,
  120%→still critical, not a separate "over" state), confirm the
  Dashboard KPI counts only warning+critical jobs, confirm "Lines Over"
  KPI is actually removed (not just visually hidden) and nothing else
  still reads from it.
- Guardian v2 pass (syntax, dup IDs/globals, div-balance, dead-button,
  no forbidden patterns) before any push, same as every other change
  tonight.
- If the optional §7 narrative feature is built: verify it actually
  refuses to fabricate when given incomplete data (e.g. a job with only
  one cost-code line) rather than padding out a generic-sounding
  explanation — same check applied to every other AI-output feature
  built tonight.
