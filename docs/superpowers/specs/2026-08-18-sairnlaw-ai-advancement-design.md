# SAIRNlaw — AI-Advancement Rollout (5-Capability Standard)

**Status:** Design drafted 2026-08-18, pending review. Not yet implemented.

Checked what's already built before proposing anything new, same discipline
as SAIRNbiz (`docs/superpowers/specs/2026-08-18-sairnbiz-ai-advancement-rollout.md`)
and SAIRNcode's Aug-5 rollout. Unlike those two apps, SAIRNlaw is NOT mostly
done — only 1 of 5 capabilities exists today.

## 0. Real current state (verified 2026-08-18 against the live file, not memory)

**Agentic follow-up: built, live, already privilege-conscious.**
Commits `4b0953d`/`92f3b55`/`38deb21`/`a9ba25a` (2026-08-08/10) added a
tool-calling dispatcher with two read-only tools, `get_matters` and
`get_deadlines`. The system prompt (`sairnlaw.html:1469`,
`LAW_FIRM_DATA_RULE`) is explicit and narrow: the AI can see matter
numbers/names/client names/practice area/status/responsible attorney/
opposing parties, and pending deadlines — and is explicitly told it does
**not** have trust balances, invoices, time entries, matter notes,
deadline notes, or billing records, with an instruction to say so plainly
rather than guess if asked. This is a real, deliberate least-privilege
boundary already in place — the reference pattern for whatever else gets
built here, not something to redesign.

**Predictive business intelligence, voice input, shared company-knowledge
layer: do not exist.** Confirmed by direct search, not inferred from
absence of a commit message: zero `SpeechRecognition` references, zero
`shared_knowledge` references, zero KPI/rate-style computed elements
anywhere in the file (`grep` for `kpi-value`/`kpi-card` returns nothing —
this app doesn't even use that class name; its dashboard KPIs are
`.kpi`/`.kval`, and all four — Open Matters, Deadlines This Week, Trust
Balance, Unbilled Hours — are raw counts/sums, no rate or trend
computed from them anywhere).

**AR measurement: no genuine fit, confirmed by a full panel sweep** (all
16 panel titles checked, not assumed): Client/Matter Intake, Matter/Case
Management, Calendaring & Deadlines, Trust Accounting, Time Tracking &
Billing, Document Management, AI Drafting & Review, Client Portal, Staff
Certifications, Accounting, Personal Injury Module, Legal Research
Citator, AI Chain of Custody, Security & Audit. Personal Injury —the one
panel name that could plausibly involve physical documentation — is
"case value estimation, medical records/lien tracking, settlement
calculation" (`sairnlaw.html:823`), not a measurement/dimension
workflow. Same exclusion as SAIRNvet/SAIRNbiz/SAIRNcode, same reasoning.

**Real bug found along the way, unrelated to what's missing:** the AI
Assistant panel's own static disclosure copy (`sairnlaw.html:325-327` and
`:336`) still says the assistant "has no access to this firm's real
matters, deadlines, trust balances, or billing data" and "cannot look up
this firm's actual matters, deadlines" — both now **false**. The
tool-calling work shipped Aug 8/10 gave it real matters+deadlines access;
this hardcoded copy was never updated to match. For a privileged-data
app, UI copy *understating* what the AI can see is still a real accuracy
problem — a user deciding what's safe to ask shouldn't be working from
stale information, even if the stale version happens to be more
conservative than reality. Fixing this is small and independent of
everything else below.

## 1. Scope of this pass

1. **Fix the stale disclosure copy** (§0's bug) — update both spots to
   accurately describe the real, narrow tool access (matters + deadlines,
   nothing financial/notes) instead of claiming zero access.
2. **Voice input** — low risk, no privilege concern (browser-local
   `SpeechRecognition`, never leaves the device except as whatever text
   the user would have typed anyway). Wire to the AI Assistant chat input
   and likely Matter/Case Management's note fields, same "hands busy"
   framing as every other app. Ported from an existing app's module, not
   built from scratch.
3. **Predictive business intelligence** — real gap, needs a metric
   decision (§3, open question) before building. Candidate: extend the
   existing honest Dashboard KPIs with a computed rate/trend, same
   "extend what's already real" pattern used everywhere else on this
   platform (e.g. SAIRNcode's appeal-success-rate, SAIRNbiz's invoice
   insights) — not a new data source, arithmetic over data already on
   the Dashboard/Deadlines/Matters panels.
4. **Shared company-knowledge layer** — real gap, but the existing
   pattern this platform normally ports (extract 5+ letter words from
   whatever the user just asked, share firm-wide as "trending topics")
   is **not safe to port as-is here** — see §2.
5. **AR measurement** — excluded, no build (§0).

## 2. The privilege problem with shared-knowledge, and a concrete fix

Every other app's shared-knowledge layer (SAIRNcode's
`recordScSharedTopics()` is the most recent, `sairncode.html:2989`ish)
works by regex-extracting words from the user's own question text and
sharing the resulting word-frequency map firm/practice-wide via the
generic `shared_knowledge` resource. For a business-metrics app, a
"trending topic" being e.g. `denial`, `telehealth`, `authorization` is
harmless — those are category words, not identifying facts.

For SAIRNlaw, the same mechanism applied to a real question like *"how do
I handle the Ostrander embezzlement defense"* would extract `ostrander`,
`embezzlement`, `defense` and surface them firm-wide as a "frequently
discussed" signal — visible to every employee at the firm, including
paralegals or attorneys with no reason to know that matter exists,
independent of any formal ethical wall the firm may have in place. That's
a real disclosure outside the need-to-know boundary, not a hypothetical.

**The fix already exists in this file's own UI, unused for this purpose.**
The AI Assistant's own chat form already requires picking a matter before
asking anything — `sairnlaw.html:338-339`, `<select id="aimatter">`,
with `<option value="general">General (not matter-specific)</option>` as
the one non-matter option. This is a distinction the app already forces
the user to make on every single question. Proposal: shared-knowledge
extraction only ever runs on questions submitted against `general` — any
question tied to a real matter number never feeds the shared-knowledge
layer at all, full stop. No new UI, no new user decision — just gating
the existing extraction call on a field that's already mandatory.

This still isn't zero-risk (a user could mis-select "general" for a
matter-specific question), but it's a real, structural reduction using a
boundary the app already enforces, not a cosmetic warning label.

## 3. Open questions — resolved 2026-08-18 (Michael)

1. **Predictive-insights metric: deadline-miss rate**, confirmed. Deadlines
   that passed their due date while still open, vs. total — built on top
   of `get_deadlines`' existing live-urgency computation.
2. **Shared-knowledge: build the general-only-gated version.** Extraction
   only ever runs on questions submitted with `aimatter` set to
   `general` — a matter-specific question never feeds it, full stop.
3. **Voice input: chat + Matter notes**, confirmed. Wire `ainp` (AI
   Assistant chat) and Matter/Case Management's note-taking fields.

## 4. Build order

1. Fix the stale AI Assistant disclosure copy (§0) — small, independent,
   ships first.
2. Voice input (chat + matter notes) — lowest risk, no data-model change.
3. Predictive insights (deadline-miss rate KPI) — pure computation over
   existing deadline data, no new resource.
4. Shared-knowledge (general-only-gated) — the one with a real design
   constraint from §2, built last so the gating logic can be verified
   against real matter-selector behavior already wired by then.
