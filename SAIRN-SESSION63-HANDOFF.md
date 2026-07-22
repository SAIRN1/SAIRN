# SAIRN — Session 63 Handoff

This session covered three separate workstreams — SAIRNvet (continued), SAIRNcode (completed), and a brand-new on-prem agent system. Read this whole doc before continuing any of them; don't assume the old SAIRNvet-only handoff format tells the full story anymore.

## Verified current state (confirmed independently via GitHub API, not trusted from prior notes)
- Branch: **master** (main is stale/broken — hard Guardian check)
- Master HEAD commit: `fc092b74d0a78120c2aa5e79ec1f04f59b445da5`
- `sairnvet.html`: 565,921 bytes, blob sha `40b4c2f56abf05694a19b68bda9135b671725133` — nav↔panel reconciliation 54/54, zero broken links, zero orphans
- `sairncode.html`: 115,668 bytes, blob sha `7c534e57c71dbb70613a53051d5b148bfc6de38e`
- `api/claude.js`: unchanged, still proxy-only, still works
- Live URLs (all 4 confirmed working, all now credit "SAIRN Technologies™"): `sairn.vercel.app/stonedesk`, `/sairnbiz`, `/sairncode`, `/sairnvet`

## ⚠️ Gap — main/master divergence (still growing, still unresolved)
`main` is now **72 commits behind master**. Not touched all session. Same recommendation as every prior handoff: fast-forward `main` to `master`, or repoint Vercel's git integration to `master`, before this gets any worse.

## ⚠️ Gap — SAIRNbiz not yet audited
SAIRNbiz has never been through the panel-by-panel audit that SAIRNvet and SAIRNcode just got. Given the same fabricated-KPI pattern was found in both of those apps, assume SAIRNbiz likely has it too until checked. Not started this session — pure time constraint, not a finding either way.

---

## Workstream 1 — SAIRNvet (continued from Session 62)

12 panels done total across Sessions 59–63: wildliferehab, speciesref, conservation, compliance, clients, invoicing, billing, financials, reports, analytics, **staff, multisite** (these last two were done this session but never got their own handoff entry — noted here for the record). Commits `ac6226ca` (staff) and `36fa369c` (multisite).

**~18 panels remain** from the original 30-panel list. Same standard workflow as always (confirm master HEAD → fetch fresh → audit → real data model → Guardian checks → push → independently re-verify byte-for-byte → hook into both init blocks). No panel-specific findings to report this session since none were touched.

## Workstream 2 — SAIRNcode (fully completed this session)

**All 20 panels done.** This was a full first-pass audit of an app that had never been touched before — same fabricated-KPI pattern as SAIRNvet's original state, found independently and fixed with the same rigor.

Fixed, in order: revenue, denial, compliance, fraud, dashboard, prebill, hcc, drg, query, encoder, rac, telehealth, anesthesia, auth, ar, reports, providers (17 panels with real data-model conversions). `claims` was already honest and didn't need touching. `ai` (chat) and `settings` never had fabricated KPIs to begin with.

**Two findings worth flagging specifically, beyond the usual fake-KPI pattern:**
- **Two unfounded "Patent Pending" claims** (fraud panel: "Pattern Memory AI"; prebill panel: "AI Error Detection Engine") — neither was ever actually filed. Corrected to "Patent Candidate — Not Yet Filed," consistent with the investor deck's honest IP slide.
- **The Reports panel's 8 "Download CSV" buttons were completely dead** — they called `exportCSV('report1')` through `('report8')`, but no panel with those names exists, so `exportCSV()` silently did nothing on every click. Fixed to point at the 7 real panels; dropped the 8th ("Payer Scorecard") since no payer data exists anywhere in the app to back it.

**Dashboard now genuinely rolls up live** from the Claims table (DOM-read) plus the real Revenue/Denial/Fraud data models, and auto-refreshes whenever those panels' data changes.

Final sweep this session confirmed: JS syntax valid, 20/20 nav↔panel reconciliation, zero remaining patent claims, all 15 new `sc_`-prefixed localStorage models hooked into page load.

## Workstream 3 — On-prem agent system (new this session)

Built from scratch: lets a SAIRN app reach into a customer's systems behind their firewall, outbound-only, with a 30-day full-access trial that hard-paywalls after unless marked paid.

**Files (all in the repo now):**
- `sql/agent_schema.sql` — Supabase schema (`sairn_agents`, `sairn_agent_commands`)
- `api/agent/register.js`, `poll.js`, `result.js`, `enqueue.js` — the cloud-side endpoints
- `api/agent/stripe-webhook.js` — automatic trial→paid conversion on real Stripe payment, signature verified manually via Node's built-in `crypto` (no `stripe` npm package — this repo has zero npm dependencies and the signature check doesn't need a full SDK)
- `agent/sairn-agent.js` — the standalone program that runs on the customer's machine
- `agent/config.example.json`, `agent/README.md` — setup docs and the local operation whitelist pattern
- `scripts/create-agent.js`, `scripts/mark-agent-paid.js` — ops helpers

**Security model:** the agent only ever executes operations by NAME, never raw SQL/commands/paths from the cloud side. The mapping from operation name to actual local query/path lives only in that customer's own `config.json`. A compromised cloud caller can only trigger what that customer's IT already pre-approved locally.

**Proven working end-to-end tonight** — not just code that looks right on paper. Michael walked through the actual setup live: Supabase table creation, permission grants, provisioning a real agent, editing `config.json`, and running `node sairn-agent.js`, which registered successfully and reported "Trial plan — 30 day(s) remaining." Confirmed real: agent ID `2b7245f8-932d-4634-903e-c1d938837622` and a second one, `b59e579f-0fff-4bf4-9665-547c27d6e3c4` (both in the live Supabase table).

**Known limitations (from the README, still accurate):**
- Only `sql_query` and `file_read` operation kinds implemented; `http_call` is stubbed
- ~8–10 second delivery latency (Vercel serverless execution limits), not instant push
- `enqueue.js` has no per-customer session auth yet beyond knowing a valid `agent_id` — fine for a single-customer pilot, needs hardening before multiple customers run in parallel
- Stripe webhook is built and unit-tested (signature verification logic specifically), but the *checkout-session-creation* step that sets `client_reference_id`/`metadata.agent_id` isn't built — that lives wherever Michael's existing Stripe integration creates sessions, not touched this session
- Not yet packaged as an installable Windows/Linux service

## Non-repo artifacts from this session (⚠️ these do NOT persist — flag to Michael)
The investor pitch deck (`SAIRN-Investor-Overview.pptx`/`.pdf`, 17 slides, portrait print versions) and the `SAIRN-Live-Product-Links.pdf` URL sheet were built as chat file outputs, not pushed to GitHub. **The sandbox they were built in resets between conversations — if Michael hasn't already downloaded them, they're gone once this chat ends.** If he needs them again, they'll need to be rebuilt from scratch in a new session (the full content/design decisions are described earlier in this conversation's history, but the actual files are not recoverable from the repo).

## Standard workflow for continuing (proven across ~50 panels now, two full apps)
1. Confirm master HEAD unchanged since last known commit before touching anything.
2. Fetch the target file fresh via GitHub raw content API — don't trust local cache from a prior turn.
3. Extract the target panel's HTML block by finding `<div id="X"` through the next `<div id="`.
4. Audit for: fabricated/mismatched KPIs, dead buttons calling nonexistent targets, unfounded legal/IP claims, missing ids, fake success toasts.
5. Design a real data model: app-prefixed localStorage, click-to-edit or add/remove pattern, KPIs computed live from the actual list — never re-fabricate a number; drop it or make it an optional field starting at "—"/0 if it can't be honestly computed.
6. Check for id/function-name collisions against the live file before writing (`grep -c` for each new id/function name — must be 0).
7. Run scoped Guardian-equivalent checks (`node --check`, no Unicode box chars, no `alert()`, no duplicate ids, div-tag balance, single `<script>` block).
8. Reconcile nav↔panel counts before pushing.
9. Push via GitHub REST API blob→tree→commit→ref (never `git push` directly).
10. Independently re-fetch from GitHub after push and diff against the local pushed copy — must be byte-identical.
11. Hook new `render<n>()` calls into every init/load path that exists in that specific app (SAIRNvet has two PIN-gated init blocks; SAIRNcode has one `window.addEventListener('load', ...)` handler).

## Model/effort workflow (new, from this session)
Michael runs Claude Code on Sonnet 5 High as default and wants to keep it there. Escalate only when warranted, in three tiers: Sonnet 5 Max for moderately hard tasks, Opus 4.8 for hard debugging/security-critical code, opusplan (Opus plans, Sonnet builds) for big architecture decisions. Flag proactively — he doesn't want to have to remember to ask.

## Iron Laws — unchanged, all followed this session
GitHub REST API only (blob→tree→commit→ref, never `git push` directly) · no Unicode box-drawing chars in JS · no dark backgrounds · no `alert()` (showToast only) · all new localStorage keys app-prefixed · Claude calls through proxy only · Guardian-equivalent scan before every push · Chat stops rather than compacts — produce handoff instead.

## Deploy
Local machine: `C:\Users\marsh` (confirmed this session — NOT a `Documents\SAIRN` subfolder, the repo root is the home directory itself), plain CMD (never PowerShell):
```
git fetch origin
git reset --hard origin/master
npx vercel --prod --force
```
Answer "yes" to the "deploying your home directory" prompt — expected for this setup, not a warning sign.
