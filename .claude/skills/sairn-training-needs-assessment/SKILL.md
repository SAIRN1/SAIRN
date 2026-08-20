---
name: sairn-training-needs-assessment
description: Implementation pattern for an employee training-needs / skills-gap assessment tool, built on the Hennessy-Hicks TNA (WHO-endorsed) importance/performance-gap methodology, with a two-perspective structure (employee self-assessment, soft framing; management assessment, analytical framing) and an optional non-branded DISC-style communication-style module. Trigger whenever the user wants "training needs assessment," "TNA," "skills gap analysis," "employee development check-in," "DISC," or "communication style assessment" for any SAIRN app. Extracted from SAIRNbuild's real build (2026-08-20, fully live-verified end to end including a real self-assessment write, management assessment write, comparison view, and team-overview aggregation) — this is the reusable technical pattern; per-app adaptation (role vocabulary, item-bank domain wording) is a judgment call each build makes explicitly, not something this skill decides for you.
---

# SAIRN Training Needs Assessment — real methodology, honest sourcing, privacy-gated

## Source the methodology for real before you build — don't reconstruct from memory

The Hennessy-Hicks Training Needs Analysis Questionnaire is a real, WHO-endorsed, free instrument: 30 items, each rated on two 7-point scales (importance to the job, current performance), with the gap between the two = the training need for that item. Verify this structure via live web research every time this skill is used — don't trust a prior session's paraphrase, and don't assume you remember the real item wording correctly.

**The verbatim original 30 healthcare item texts are hard to retrieve.** The SAIRNbuild build tried 5 different sources (WHO/Birmingham eprints PDF, pdf4pro transcription, academic PDFs, Scribd, AKU eCommons) and every one failed PDF text extraction. If the same thing happens: **do not fabricate items and label them "Hennessy-Hicks."** Instead, build on the verified real structure (30 items, dual 1-7 scales, gap = importance minus performance) with original item wording adapted for the target industry, and label it **"Hennessy-Hicks-style"** everywhere in the app's copy and code comments — never claim verbatim fidelity to an instrument you don't actually have the text of. The instrument's own documented customization rules (up to 8 of 30 items replaceable, up to 10 more addable) give real cover for adaptation, but going further than that (as SAIRNbuild did, rewording closer to all 30 for a non-healthcare industry) needs the same honest "-style" disclosure, not a claim of exact fidelity.

Confirmed real structure to build from: 5 domains (research/audit, communication/teamwork, clinical/field tasks, administration, management/supervisory — rename domains 1 and 3 per industry, e.g. SAIRNbuild used "Quality & Safety Oversight" and "Field & Technical Skills"), 6 items per domain is a reasonable even split if the exact original count-per-domain isn't available.

## The two-perspective structure

Two independent raters complete the same item bank about one employee:
- **Self** — the employee rates themselves. Soft, positive-reinforcement framing ("There's no wrong answer — the goal is figuring out where a bit of training or support would help you most. This does not affect your pay or job status."). Results shown to the employee use encouraging language ("Growth opportunity" / "Strength — keep it up"), never "deficiency" or "weakness."
- **Management** — a manager rates the same employee. Analytical framing ("Rate this employee's current skill level... based on what you've actually observed on the job. This feeds team-wide training planning — it is not a performance review.").

**Visibility judgment call — make it explicitly, don't silently assume:** SAIRNbuild's call (confirmed correct in practice) was that an employee sees BOTH their own self-view and any management assessment of them, side by side, always softly framed — transparency between the two views is the actual point of running both, and a hidden second assessment about someone is worse HR practice than a visible one. Management sees the unsoftened analytical view across the whole team. State this choice plainly in code comments when building for a new app, the same way every other ambiguous access-control decision on this platform gets logged, not guessed silently.

## Server-side privacy gate (the real boundary)

Bespoke read/write branch in `api/sd-data.js`, same shape as `sdn_clients`/`bld_bids`'s privacy gates — not the generic resource-loop pattern, because visibility here is subject-based, not assignee-based:

```js
// READ: non-management sees only rows about themselves (both perspectives);
// management sees every subject's rows.
if (resource === '<prefix>_tna' && action === 'read') {
  const session = verifySessionToken(tokenFromRequest(req), licHash, '<app_id>');
  if (!session) { res.status(401).json({ error: { code: 'NO_SESSION', ... } }); return; }
  // ...fetch all rows for this license...
  let out = rows;
  if (!MANAGEMENT_ROLES[session.role]) {
    out = out.filter(r => r.subject_employee_id === session.employee_id);
  }
  // ...
}

// WRITE: a 'self' row is ONLY ever writable by its own subject, regardless of
// role (even a management-role employee can't write someone else's self-view,
// and can't have their OWN self-view written for them by someone else).
// A 'management' row is only writable by a management-tier role.
if (resource === '<prefix>_tna' && action === 'write') {
  const session = verifySessionToken(tokenFromRequest(req), licHash, '<app_id>');
  if (!session) { res.status(401)... ; return; }
  const { subject_employee_id, perspective, responses } = payload;
  if (perspective === 'self') {
    if (subject_employee_id !== session.employee_id) { res.status(403)...; return; }
  } else if (!MANAGEMENT_ROLES[session.role]) {
    res.status(403)...; return;
  }
  // upsert on (license_hash, subject_employee_id, perspective)
}
```

Table shape (`sql/<app>_tna_schema.sql`):

```sql
create table if not exists public.<prefix>_tna_assessments (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default '<app_id>',
  subject_employee_id text not null,
  perspective text not null check (perspective in ('self','management')),
  assessor_employee_id text not null,
  responses jsonb not null default '{}'::jsonb,   -- { "item_1": {"importance":1-7,"performance":1-7}, ... }
  disc_responses jsonb,                            -- optional, self-perspective only
  disc_profile jsonb,                              -- computed { "D":n,"I":n,"S":n,"C":n,"primary":"D","secondary":"I" }
  submitted_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, subject_employee_id, perspective),
  constraint <prefix>tna_data_size check (octet_length(responses::text) <= 65536)
);
```

## Client-side function checklist

- `<prefix>Load()` — `bldData('read','<prefix>_tna',null,true)` equivalent, caches into a module-level `_tnaData`.
- `<prefix>MyRows()` — pulls `{self, management}` for the logged-in user out of `_tnaData`.
- `<prefix>Gap(resp)` / `<prefix>DomainAvgGap(responses, domainId)` — real computation, never fabricated.
- `<prefix>GapBadge(gap)` — soft label above ~1.5 gap ("Growth opportunity"), moderate label above ~0.5 ("Room to grow"), else "Strength" — tune thresholds per app if needed, but keep the three-tier shape.
- Self form: soft-framing intro banner, 30 items grouped by domain, two 1-7 `<select>`s per item, pre-fills existing values on edit.
- Management form: analytical-framing intro banner, employee picker sourced from the SAME roster-fetch function the app's other Assign-To/reassign features already use (don't build a second roster fetcher), same 30-item form.
- Team Overview: table of every roster employee, self/management completion status, real aggregated overall gap, "Assess" shortcut into the management form pre-selecting that employee.
- **A dedicated KPI/summary-refresh function, called from BOTH the initial panel-load path AND every save handler** — see the bug below for why this is its own numbered checklist item, not an afterthought.

## Optional DISC-style module — public domain, non-branded, ADA-safe

The underlying 4-factor model (Dominance/Influence/Steadiness/Conscientiousness) is public domain (Marston, 1928). Write **original item wording** — do not copy any licensed commercial DISC product's items, those are trademarked. ~16 statements (4 per dimension), 1-5 Likert ("not like me" to "very like me"), summed per dimension, highest = primary style, second = secondary. Self-report only — a manager filling out someone else's communication-style profile isn't a coherent action, don't build that path.

**Every screen this module appears on must carry an explicit non-diagnostic disclaimer**, e.g.: *"This is a workplace communication-style questionnaire, not a personality, psychological, or medical assessment — it has no bearing on employment decisions."* This is a framing choice to reduce ADA medical-inquiry risk, not a legal opinion — say so in the code comments, and flag to whoever's building that real employment counsel should review the live copy before any personnel use. Keep every item behaviorally worded (what someone does/prefers), never emotion- or health-state-worded — SAIRNbuild caught and reworded one TNA item ("managing your own workload and stress under deadline pressure" → "meeting deadlines and keeping multiple priorities on track") for exactly this reason during self-review; check the whole item bank for the same pattern before shipping.

## Two real bugs already found — don't repeat them

1. **A `*-auth.js`-only helper doesn't exist in `api/sd-data.js`.** `isMissingTable()` is defined per-file in `api/sd-auth.js`/`api/sdn-auth.js`/etc., not in `sd-data.js`. If a new resource's write branch needs to detect "table not provisioned yet," check `r.status === 404 || r.status === 400` directly against the fetch response, matching every other resource branch in that file — don't import or reference a helper that only exists in the auth files. `node --check` catches this immediately if run after every edit (per this project's own standing rule) — but it's cheaper to just know the file boundary going in.
2. **KPI/summary cards go stale after a save if the save handler doesn't explicitly re-render them.** The results view and the summary cards above it are two different render calls — a save handler that refreshes the data and re-renders the results view but forgets the summary cards leaves them showing pre-save state (e.g. "Not started" right after a successful save) until the user navigates away and back. Extract the summary-card render into its own function and call it from every save handler's post-save refresh, not just from the panel's initial load path. Live-verified as a real, user-visible bug on SAIRNbuild before this fix — caught by an actual end-to-end Playwright round-trip test, not by code review alone, which is itself the argument for always doing the real round-trip test (see below) rather than stopping at server-reachability checks.

## Verification standard — server-reachability is not enough

A clean `curl` against the new resource (confirms the allowlist gate and the privacy-gate branch are live) is necessary but not sufficient — it will not catch a client-side bug like #2 above. Once the migration is confirmed run, do the REAL round trip in a real browser session: log in, fill and save a full self-assessment, confirm the results view AND every summary card update correctly with no page reload, save a management assessment for the same employee, confirm the self-vs-management comparison view, confirm Team Overview aggregates correctly. This is what actually surfaced bug #2 on SAIRNbuild — a code-level review of the same diff did not catch it.

## What NOT to do

- **Don't claim verbatim Hennessy-Hicks item text** unless you've actually retrieved and can cite the real source — label adapted items "-style," always.
- **Don't let DISC drift into personality/clinical language** anywhere in the UI, even in results copy — behavioral-preference wording only, disclaimer on every screen it appears on.
- **Don't build a second roster-fetch function** for the management employee picker — reuse whatever the app's existing Assign-To/reassign feature already has.
- **Don't skip the app-scope argument on `verifySessionToken`** — this resource's role names may overlap with another app's (e.g. SAIRNbuild and SAIRNdesign both have 'owner'/'office') and the third argument is what prevents a cross-app token from passing.
- **Don't stop at a curl-based "server reachable" check and call it verified** — do the real interactive round trip once the migration is confirmed run, per the verification standard above.
- **Don't hide test data from a live-verification pass** — flag it in a `sql/<app>_visual_review_cleanup.sql`-style file with commented-out delete statements, same as every other test-data cleanup on this platform, and don't execute the deletes yourself unless asked.
