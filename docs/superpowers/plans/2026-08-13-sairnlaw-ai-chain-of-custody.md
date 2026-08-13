# SAIRNlaw AI Chain of Custody (Phase 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every AI interaction in SAIRNlaw a real, matter-linked, database-immutable audit record, with a required human-review gate before any AI output can be attested as used in a filing.

**Architecture:** Correction from the design spec, found during planning — `sql/sairnlaw_audit_log_schema.sql` and `api/law-auth.js`'s existing `audit_read` action already implement exactly the real, database-enforced immutable audit log this feature needs (grant `select,insert`, `revoke update,delete` on `service_role`, confirmed live once already). Building a brand-new table and a brand-new API file would duplicate that infrastructure, not add a second one — this plan instead **extends** the existing `sairnlaw_audit_log` table (new event types) and the existing `api/law-auth.js` endpoint (four new actions), reusing its already-audited `writeAuditLog()` helper, license/session verification, and PostgREST plumbing verbatim. No new table, no new API file.

**Tech Stack:** Vanilla JS client (`sairnlaw.html`), Vercel serverless function (`api/law-auth.js`), Supabase/Postgres.

## Global Constraints

- **No new table, no new API file.** Every server-side addition in this plan is either a migration to the existing `sairnlaw_audit_log` table or a new action inside the existing `api/law-auth.js`. This is a deliberate, disclosed deviation from the design spec's literal "new `law_ai_log` table" language — the spec's actual requirement (real, server-side, immutable, matter-linked logging) is fully satisfied by extending proven infrastructure instead.
- **Real immutability, not an honor system.** The four new event types (`ai_interaction`, `ai_reviewed`, `ai_rejected`, `ai_used_in_filing`) are rows in the same `sairnlaw_audit_log` table already governed by `grant select, insert ... to service_role; revoke update, delete ... from service_role;`. No new grant/revoke statements are needed — the existing ones already cover every row in this table regardless of `event_type`.
- **`employee_id`/`role` are always server-derived from the verified session token**, never accepted from the request body — this is what makes the log non-repudiable (a rep cannot claim an interaction happened under someone else's name).
- **Review/reject/filing-attestation actions are restricted to `owner`/`attorney` roles.** `paralegal` may trigger AI interactions (which get logged same as anyone) but may not review, reject, or attest — matches the real crisis this feature answers (licensed attorneys, not paralegals, are the ones sanctioned).
- **`audit_read` (the existing general Security & Audit page action) is NOT modified to include the new event types.** Its `detail` column renders raw `JSON.stringify()` in a generic security-events table — dumping full AI prompt/response text (which may contain privileged client matter detail) into that generic view would be a real, new information-exposure surface. The new event types get their own dedicated, more narrowly-scoped `ai_list` action instead. `audit_read`'s `coverage.covered` text gets one line added disclosing that AI interactions are now tracked separately (honesty update only, matches this file's own established "coverage returned with the data so a UI can't overstate itself" discipline).
- **Server-side state-machine enforcement, not just client-side.** `ai_reject`/`ai_used_in_filing` independently re-derive the target entry's current status server-side before allowing the transition — never trust the client's belief about an entry's current state.
- **No DB migration is executed by the agent implementing this plan.** This environment has no `SUPABASE_URL`/service key, no `psql`, no `supabase` CLI (confirmed precedent, SAIRNdesign/SAIRNlegacy builds) — Task 1 writes the SQL file; a human runs it in Supabase's SQL editor before Tasks 2-6 can be live-verified end-to-end.
- Prompt/response text is capped at 20,000 characters each before insert (truncated with a trailing marker if exceeded) — defensive cap, matching this platform's general payload-size discipline (see `api/sd-data.js`'s 64KB cap and its own CHECK-constraint backstop).
- Never bulk find-replace. Every edit below is a targeted, unique-context change.

---

## File Structure

| File | Responsibility for this feature |
|---|---|
| `sql/sairnlaw_ai_chain_of_custody.sql` (new) | Extends `sairnlaw_audit_log`'s `event_type` check constraint with 4 new values. No new table, no new grants (existing ones already cover it). |
| `api/law-auth.js` | Four new actions: `ai_log` (insert), `ai_list` (read + derive status), `ai_review`/`ai_reject`/`ai_used_in_filing` (state-transition events). One line added to `audit_read`'s `coverage.covered`. |
| `sairnlaw.html` | `sendAI()` instrumentation (Task 4), required matter picker on `#achat` (Task 4), new "AI Chain of Custody" panel + nav entry (Task 5). |

Line numbers below are as of this plan's base commit and will drift as earlier tasks land — every edit is anchored to unique surrounding code, not the raw number.

---

### Task 1: SQL migration — extend the existing immutable audit log

**Files:**
- Create: `sql/sairnlaw_ai_chain_of_custody.sql`

**Interfaces:**
- Produces: 4 new valid `event_type` values on `sairnlaw_audit_log` (`ai_interaction`, `ai_reviewed`, `ai_rejected`, `ai_used_in_filing`) — consumed by Task 2/3's server code and by nothing else. No schema/table/grant changes — the existing `grant select, insert ... revoke update, delete ...` statements already apply.

- [ ] **Step 1: Write the migration**

Create `sql/sairnlaw_ai_chain_of_custody.sql`:

```sql
-- sql/sairnlaw_ai_chain_of_custody.sql
-- SAIRNlaw AI Chain of Custody (Phase 1) — extends the existing immutable
-- audit log (sql/sairnlaw_audit_log_schema.sql) with 4 new event types,
-- rather than creating a second, parallel audit table. That file's own
-- grant/revoke statements (`grant select, insert ... to service_role;
-- revoke update, delete ... from service_role;`) already govern every row
-- in this table regardless of event_type -- no new grant is needed here.
--
-- Event shapes (all live in the existing jsonb `detail` column):
--   ai_interaction  { prompt, response, matter_id, tools_used: [names] }
--     -- the record of one real sendAI() exchange. employee_id/role (top-
--     -- level columns, already on this table) identify who triggered it.
--   ai_reviewed     { log_entry_id }
--     -- log_entry_id references the id of the ai_interaction row being
--     -- reviewed. employee_id/role identify the reviewer.
--   ai_rejected     { log_entry_id, reason }
--     -- reason is required at the application layer (enforced in
--     -- api/law-auth.js, not by a DB constraint -- this table's `detail`
--     -- column has no per-event-type shape validation, matching every
--     -- other event type already in this table).
--   ai_used_in_filing { log_entry_id }
--     -- the attorney's formal attestation that they verified this output
--     -- before relying on it in a filing. Only ever inserted after a
--     -- prior ai_reviewed event for the same log_entry_id exists --
--     -- enforced server-side (api/law-auth.js), not by a DB constraint.
--
-- An entry's CURRENT status is derived, not stored: the most recent of
-- {ai_reviewed, ai_rejected, ai_used_in_filing} whose detail->>'log_entry_id'
-- matches a given ai_interaction row's id, or 'unreviewed' if none exists.
-- This is a real event-sourcing model, not a mutable status column -- it
-- means the full review history (including a correction, if one is ever
-- needed) is itself part of the immutable record, not overwritten.
--
-- Safe to re-run.

alter table sairnlaw_audit_log drop constraint if exists sairnlaw_audit_log_event_type_check;
alter table sairnlaw_audit_log add constraint sairnlaw_audit_log_event_type_check
  check (event_type in (
    'login_success', 'login_failed', 'lockout',
    'pin_bootstrap', 'pin_setup',
    'mfa_enrolled', 'mfa_verified', 'mfa_failed',
    'sso_login', 'sso_link',
    'citator_lookup',
    'ai_interaction', 'ai_reviewed', 'ai_rejected', 'ai_used_in_filing'
  ));

-- Query pattern this feature relies on (ai_list, api/law-auth.js): fetching
-- all ai_interaction rows plus all status-event rows for a license, most
-- recent status event per log_entry_id wins. No new index is added this
-- pass -- (license_hash, created_at desc) already exists from the base
-- schema and is sufficient at expected single-firm volume; add a
-- dedicated index on detail->>'log_entry_id' if this becomes a real
-- bottleneck, not preemptively.
```

- [ ] **Step 2: Hand off for manual execution**

This SQL is NOT run by this task. Note in the task report that a human must run `sql/sairnlaw_ai_chain_of_custody.sql` in Supabase's SQL editor before Task 6's live end-to-end verification can pass — Tasks 2-5's code can still be written and committed without it having run yet (the constraint only matters at insert time).

- [ ] **Step 3: Commit**

```bash
git add sql/sairnlaw_ai_chain_of_custody.sql
git commit -m "docs: SAIRNlaw AI Chain of Custody -- SQL migration extending sairnlaw_audit_log event types"
```

---

### Task 2: Server — capture (`ai_log`) and read (`ai_list`) actions

**Files:**
- Modify: `api/law-auth.js` (`ACTIONS` array; new action handlers placed right after the existing `audit_read` handler)

**Interfaces:**
- Consumes: `writeAuditLog` (already imported), `verifySessionToken`/`tokenFromRequest` (already imported), `rest()`/`enc()`/`headers`/`licHash`/`audit()` (already defined in the module closure, per `audit_read`'s own usage).
- Produces: `action:'ai_log'` (POST body: `{matter_id, prompt, response, tools_used}`, session required, any role) and `action:'ai_list'` (POST body: `{limit}`, session required, `owner`/`attorney` only) — consumed by Task 4 (`ai_log`) and Task 5 (`ai_list`).

- [ ] **Step 1: Register the two new actions**

Find (around line 104-108):

```js
const ACTIONS = [
  'check_license', 'bootstrap', 'login', 'setup',
  'mfa_setup', 'mfa_enable', 'mfa_verify', 'mfa_reset',
  'sso_start', 'sso_callback', 'audit_read'
];
```

Replace with:

```js
const ACTIONS = [
  'check_license', 'bootstrap', 'login', 'setup',
  'mfa_setup', 'mfa_enable', 'mfa_verify', 'mfa_reset',
  'sso_start', 'sso_callback', 'audit_read',
  'ai_log', 'ai_list', 'ai_review', 'ai_reject', 'ai_used_in_filing'
];
// AI Chain of Custody roles (2026-08-13): licensed attorneys, not
// paralegals, are the ones sanctioned for AI-generated fake citations --
// review/reject/filing-attestation are restricted accordingly. Any
// authenticated role may trigger an AI interaction (ai_log) -- everyone's
// usage gets logged the same way, only the review/attestation actions are
// role-gated.
const AI_COC_REVIEW_ROLES = { owner: true, attorney: true };
const AI_PROMPT_RESPONSE_CAP = 20000;
```

- [ ] **Step 2: Update `audit_read`'s coverage disclosure**

Find (around line 450-454):

```js
        coverage: {
          covered: ['authentication events', 'two-factor enrollment and verification', 'single sign-on', 'credential provisioning', 'citator research lookups'],
          not_covered: ['trust/IOLTA transactions', 'document access', 'matter changes'],
          not_covered_reason: 'Those features store their data in the browser only and never reach the server, so the server cannot observe or attest to them. Server-side auditing of those actions requires them to become server-backed first — a separate, real piece of work that has not been done.'
        }
```

Replace with:

```js
        coverage: {
          // AI interactions (2026-08-13) are tracked in this same table but
          // deliberately NOT included in this general endpoint's own
          // results (see ai_list below) -- their detail payload carries
          // real prompt/response text, which may contain privileged client
          // matter content, and does not belong in this page's generic
          // JSON.stringify(detail) rendering. Disclosed here so this page
          // stays honest about the fact that coverage without implying
          // this view shows it.
          covered: ['authentication events', 'two-factor enrollment and verification', 'single sign-on', 'credential provisioning', 'citator research lookups', 'AI interactions (see AI Chain of Custody, not shown on this page)'],
          not_covered: ['trust/IOLTA transactions', 'document access', 'matter changes'],
          not_covered_reason: 'Those features store their data in the browser only and never reach the server, so the server cannot observe or attest to them. Server-side auditing of those actions requires them to become server-backed first — a separate, real piece of work that has not been done.'
        }
```

- [ ] **Step 3: Add the `ai_log` and `ai_list` handlers**

Find (the end of `audit_read`'s handler block — around line 455-458, right before `if (action === 'sso_start') {`):

```js
      });
      return;
    }

    if (action === 'sso_start') {
```

Replace with:

```js
      });
      return;
    }

    // ── AI CHAIN OF CUSTODY (2026-08-13) ────────────────────────────────
    // Extends sairnlaw_audit_log (see sql/sairnlaw_ai_chain_of_custody.sql)
    // rather than a new table -- the existing grant/revoke on that table
    // already makes every row here immutable at the database level.
    if (action === 'ai_log') {
      const caller = verifySessionToken(tokenFromRequest(req), licHash, APP);
      if (!caller) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in required' } }); return; }
      const prompt = String(body.prompt || '').slice(0, AI_PROMPT_RESPONSE_CAP);
      const response = String(body.response || '').slice(0, AI_PROMPT_RESPONSE_CAP);
      if (!prompt || !response) { res.status(400).json({ error: { message: 'prompt and response are both required' } }); return; }
      const matter_id = body.matter_id ? String(body.matter_id) : 'general';
      const tools_used = Array.isArray(body.tools_used) ? body.tools_used.map(String) : [];
      await audit('ai_interaction', { employee_id: caller.employee_id, role: caller.role, detail: { prompt, response, matter_id, tools_used } });
      res.status(200).json({ ok: true });
      return;
    }

    if (action === 'ai_list') {
      const caller = verifySessionToken(tokenFromRequest(req), licHash, APP);
      if (!caller || !AI_COC_REVIEW_ROLES[caller.role]) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only an Owner or Attorney can view the AI Chain of Custody log' } });
        return;
      }
      const limit = Math.min(Math.max(parseInt(body.limit, 10) || 200, 1), 1000);
      const r = await fetch(rest('sairnlaw_audit_log?license_hash=eq.' + enc(licHash) +
        '&event_type=in.(ai_interaction,ai_reviewed,ai_rejected,ai_used_in_filing)' +
        '&select=id,employee_id,role,event_type,detail,created_at&order=created_at.desc&limit=' + limit), { headers });
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      const all = rows || [];
      const interactions = all.filter(function (e) { return e.event_type === 'ai_interaction'; });
      const statusEvents = all.filter(function (e) { return e.event_type !== 'ai_interaction'; });
      // Most recent status event per log_entry_id wins -- statusEvents is
      // already ordered newest-first (order=created_at.desc above), so the
      // FIRST match found per id in this loop is the current status.
      const statusById = {};
      statusEvents.forEach(function (e) {
        var lid = e.detail && e.detail.log_entry_id;
        if (lid && !statusById[lid]) statusById[lid] = e;
      });
      const entries = interactions.map(function (e) {
        var statusEvent = statusById[e.id];
        var status = 'unreviewed';
        if (statusEvent) {
          if (statusEvent.event_type === 'ai_reviewed') status = 'reviewed';
          else if (statusEvent.event_type === 'ai_rejected') status = 'rejected';
          else if (statusEvent.event_type === 'ai_used_in_filing') status = 'used_in_filing';
        }
        return {
          id: e.id, employee_id: e.employee_id, role: e.role, created_at: e.created_at,
          matter_id: e.detail && e.detail.matter_id, prompt: e.detail && e.detail.prompt,
          response: e.detail && e.detail.response, tools_used: (e.detail && e.detail.tools_used) || [],
          status: status,
          reject_reason: (statusEvent && statusEvent.event_type === 'ai_rejected') ? statusEvent.detail.reason : null,
          reviewed_by: statusEvent ? statusEvent.employee_id : null,
          reviewed_at: statusEvent ? statusEvent.created_at : null
        };
      });
      res.status(200).json({ ok: true, entries: entries });
      return;
    }

    if (action === 'sso_start') {
```

- [ ] **Step 4: Verify no syntax errors**

Run: `node --check api/law-auth.js`
Expected: no output (clean exit).

- [ ] **Step 5: Manual verification (curl, real server round trip)**

Requires a real, active SAIRNlaw license key and a logged-in session token (obtain via the app's real login flow, or from a prior session's test credentials if already documented for this environment). If neither is available in this environment, hand-trace the code instead: confirm `ai_log` requires a valid session (any role), confirm `ai_list` requires `owner`/`attorney` and 403s for `paralegal`, confirm the `entries` mapping correctly derives `status` from the newest matching status event.

```bash
curl -s -X POST https://sairn.vercel.app/api/law-auth \
  -H "Content-Type: application/json" -H "Authorization: Bearer <license_key>" -H "X-SD-Auth: <session_token>" \
  -d '{"action":"ai_log","prompt":"Draft a demand letter","response":"Here is a draft...","matter_id":"general","tools_used":[]}'
# Expected: {"ok":true}

curl -s -X POST https://sairn.vercel.app/api/law-auth \
  -H "Content-Type: application/json" -H "Authorization: Bearer <license_key>" -H "X-SD-Auth: <session_token>" \
  -d '{"action":"ai_list","limit":10}'
# Expected: {"ok":true,"entries":[{... status:"unreviewed" ...}]}
```

- [ ] **Step 6: Commit**

```bash
git add api/law-auth.js
git commit -m "feat: SAIRNlaw AI Chain of Custody -- ai_log (capture) and ai_list (read) actions"
```

---

### Task 3: Server — review workflow (`ai_review`/`ai_reject`/`ai_used_in_filing`)

**Files:**
- Modify: `api/law-auth.js` (new action handlers, right after Task 2's `ai_list` handler)

**Interfaces:**
- Consumes: `AI_COC_REVIEW_ROLES` (Task 2). Same shared closure variables as Task 2.
- Produces: `action:'ai_review'`/`'ai_reject'`/`'ai_used_in_filing'` (POST body: `{log_entry_id}`, plus `{reason}` for `ai_reject`) — consumed by Task 5's review-queue UI.

- [ ] **Step 1: Add a shared status-lookup helper and the three action handlers**

Find (the end of Task 2's `ai_list` handler, right before `if (action === 'sso_start') {`):

```js
      res.status(200).json({ ok: true, entries: entries });
      return;
    }

    if (action === 'sso_start') {
```

Replace with:

```js
      res.status(200).json({ ok: true, entries: entries });
      return;
    }

    // Re-derives one entry's current status server-side -- never trusts the
    // client's belief about it. Returns { interactionExists, status } —
    // status is 'unreviewed'/'reviewed'/'rejected'/'used_in_filing', same
    // rule as ai_list above, just scoped to a single log_entry_id instead
    // of a full-license listing.
    async function aiCurrentStatus(logEntryId) {
      const interactionR = await fetch(rest('sairnlaw_audit_log?license_hash=eq.' + enc(licHash) +
        '&id=eq.' + enc(logEntryId) + '&event_type=eq.ai_interaction&select=id&limit=1'), { headers });
      const interactionRows = await interactionR.json();
      if (!interactionR.ok) { const e = new Error('lookup failed'); e.detail = interactionRows; throw e; }
      if (!Array.isArray(interactionRows) || !interactionRows.length) return { interactionExists: false, status: null };
      const eventsR = await fetch(rest('sairnlaw_audit_log?license_hash=eq.' + enc(licHash) +
        '&event_type=in.(ai_reviewed,ai_rejected,ai_used_in_filing)&select=event_type,detail,created_at&order=created_at.desc&limit=200'), { headers });
      const events = await eventsR.json();
      if (!eventsR.ok) { const e = new Error('lookup failed'); e.detail = events; throw e; }
      const match = (events || []).find(function (e) { return e.detail && String(e.detail.log_entry_id) === String(logEntryId); });
      if (!match) return { interactionExists: true, status: 'unreviewed' };
      const status = match.event_type === 'ai_reviewed' ? 'reviewed' : (match.event_type === 'ai_rejected' ? 'rejected' : 'used_in_filing');
      return { interactionExists: true, status: status };
    }

    if (action === 'ai_review') {
      const caller = verifySessionToken(tokenFromRequest(req), licHash, APP);
      if (!caller || !AI_COC_REVIEW_ROLES[caller.role]) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only an Owner or Attorney can review AI Chain of Custody entries' } });
        return;
      }
      const logEntryId = body.log_entry_id ? String(body.log_entry_id) : null;
      if (!logEntryId) { res.status(400).json({ error: { message: 'log_entry_id is required' } }); return; }
      let current;
      try { current = await aiCurrentStatus(logEntryId); } catch (e) { return upstream(res, e.detail); }
      if (!current.interactionExists) { res.status(404).json({ error: { code: 'NOT_FOUND', message: 'No such AI interaction' } }); return; }
      if (current.status !== 'unreviewed') { res.status(409).json({ error: { code: 'ALREADY_REVIEWED', message: 'This entry is already ' + current.status } }); return; }
      await audit('ai_reviewed', { employee_id: caller.employee_id, role: caller.role, detail: { log_entry_id: logEntryId } });
      res.status(200).json({ ok: true });
      return;
    }

    if (action === 'ai_reject') {
      const caller = verifySessionToken(tokenFromRequest(req), licHash, APP);
      if (!caller || !AI_COC_REVIEW_ROLES[caller.role]) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only an Owner or Attorney can review AI Chain of Custody entries' } });
        return;
      }
      const logEntryId = body.log_entry_id ? String(body.log_entry_id) : null;
      const reason = String(body.reason || '').trim().slice(0, 2000);
      if (!logEntryId) { res.status(400).json({ error: { message: 'log_entry_id is required' } }); return; }
      if (!reason) { res.status(400).json({ error: { message: 'A reason is required to reject an AI interaction' } }); return; }
      let current;
      try { current = await aiCurrentStatus(logEntryId); } catch (e) { return upstream(res, e.detail); }
      if (!current.interactionExists) { res.status(404).json({ error: { code: 'NOT_FOUND', message: 'No such AI interaction' } }); return; }
      if (current.status !== 'unreviewed') { res.status(409).json({ error: { code: 'ALREADY_REVIEWED', message: 'This entry is already ' + current.status } }); return; }
      await audit('ai_rejected', { employee_id: caller.employee_id, role: caller.role, detail: { log_entry_id: logEntryId, reason: reason } });
      res.status(200).json({ ok: true });
      return;
    }

    if (action === 'ai_used_in_filing') {
      const caller = verifySessionToken(tokenFromRequest(req), licHash, APP);
      if (!caller || !AI_COC_REVIEW_ROLES[caller.role]) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only an Owner or Attorney can attest to AI Chain of Custody entries' } });
        return;
      }
      const logEntryId = body.log_entry_id ? String(body.log_entry_id) : null;
      if (!logEntryId) { res.status(400).json({ error: { message: 'log_entry_id is required' } }); return; }
      let current;
      try { current = await aiCurrentStatus(logEntryId); } catch (e) { return upstream(res, e.detail); }
      if (!current.interactionExists) { res.status(404).json({ error: { code: 'NOT_FOUND', message: 'No such AI interaction' } }); return; }
      if (current.status !== 'reviewed') { res.status(409).json({ error: { code: 'NOT_REVIEWED', message: 'This entry must be reviewed and approved before it can be marked used in a filing' } }); return; }
      await audit('ai_used_in_filing', { employee_id: caller.employee_id, role: caller.role, detail: { log_entry_id: logEntryId } });
      res.status(200).json({ ok: true });
      return;
    }

    if (action === 'sso_start') {
```

- [ ] **Step 2: Verify no syntax errors**

Run: `node --check api/law-auth.js`
Expected: no output (clean exit).

- [ ] **Step 3: Manual verification**

Same environment caveat as Task 2 Step 5 — use real curl calls if credentials are available, otherwise hand-trace: confirm `ai_review` 409s on an already-reviewed entry; confirm `ai_reject` 400s with no `reason`; confirm `ai_used_in_filing` 409s (`NOT_REVIEWED`) on an `unreviewed` entry and succeeds on a `reviewed` one; confirm `paralegal` gets 403 on all three.

- [ ] **Step 4: Commit**

```bash
git add api/law-auth.js
git commit -m "feat: SAIRNlaw AI Chain of Custody -- ai_review/ai_reject/ai_used_in_filing state-machine actions"
```

---

### Task 4: Client — capture every `sendAI()` exchange, required matter picker

**Files:**
- Modify: `sairnlaw.html` (`sendAI()` ~L1530-1614; `#achat`/`#ainp` panel ~L335-336; `fillMatterSelects()` ~L1306-1315)

**Interfaces:**
- Produces: a new client function `lawLogAiInteraction(prompt, response, toolsUsed)` calling `action:'ai_log'` — consumed only by `sendAI()` in this same task.
- Consumes: `lawAuth(action, payload, withSession)` (already exists, `sairnlaw.html:1062`), `fillMatterSelects()` (already exists).

- [ ] **Step 1: Add the required matter picker to `#achat`**

Find (around line 335-336):

```html
    <div class="achat" id="achat"><div style="color:var(--muted);text-align:center;padding:40px 0;">Ask for drafting help or general legal-practice explanations. It cannot look up this firm's actual matters, deadlines, trust balances, or billing -- check those panels directly.</div></div>
    <div class="air"><input id="ainp" placeholder="Draft, explain, or ask a general question (no access to this firm's live data)..." onkeydown="if(event.key==='Enter')sendAI()"><button class="btn bp" onclick="sendAI()">Send</button></div>
```

Replace with:

```html
    <div class="achat" id="achat"><div style="color:var(--muted);text-align:center;padding:40px 0;">Ask for drafting help or general legal-practice explanations. It cannot look up this firm's actual matters, deadlines, trust balances, or billing -- check those panels directly.</div></div>
    <div style="display:flex;gap:8px;align-items:center;margin-bottom:6px">
      <label for="aimatter" style="font-size:12px;color:var(--muted);white-space:nowrap">Matter (required for the record):</label>
      <select id="aimatter" style="flex:1"><option value="">-- Select a matter --</option><option value="general">General (not matter-specific)</option></select>
    </div>
    <div class="air"><input id="ainp" placeholder="Draft, explain, or ask a general question (no access to this firm's live data)..." onkeydown="if(event.key==='Enter')sendAI()"><button class="btn bp" onclick="sendAI()">Send</button></div>
```

- [ ] **Step 2: Add `aimatter` to `fillMatterSelects()`'s list**

Find (around line 1306-1315):

```js
function fillMatterSelects(){
  var opts=matters().map(function(m){return '<option value="'+m.id+'">'+H(m.matter_number)+' -- '+H(m.matter_name)+'</option>';}).join('');
  var needsBlank={dlfilter:1};
  ['mmatter','dlmatter','dlfilter','trmatter','ttmatter','ivmatter',
   'docmatter','draftmatter','portalmatter','pimatter'].forEach(function(id){
    var el=$(id);if(!el)return;
    var cur=el.value;
    el.innerHTML=(needsBlank[id]?'<option value="">All matters</option>':'')+opts;
    if(cur)el.value=cur;
  });
```

Replace with:

```js
function fillMatterSelects(){
  var opts=matters().map(function(m){return '<option value="'+m.id+'">'+H(m.matter_number)+' -- '+H(m.matter_name)+'</option>';}).join('');
  var needsBlank={dlfilter:1};
  ['mmatter','dlmatter','dlfilter','trmatter','ttmatter','ivmatter',
   'docmatter','draftmatter','portalmatter','pimatter'].forEach(function(id){
    var el=$(id);if(!el)return;
    var cur=el.value;
    el.innerHTML=(needsBlank[id]?'<option value="">All matters</option>':'')+opts;
    if(cur)el.value=cur;
  });
  // AI Chain of Custody (2026-08-13): aimatter keeps its own two fixed
  // leading options (blank + 'General') that the generic needsBlank/opts
  // pattern above doesn't produce, so it's populated separately rather
  // than added to that shared array.
  var aim=$('aimatter');
  if(aim){
    var cur2=aim.value;
    aim.innerHTML='<option value="">-- Select a matter --</option><option value="general">General (not matter-specific)</option>'+opts;
    if(cur2)aim.value=cur2;
  }
```

- [ ] **Step 3: Add the logging helper and instrument `sendAI()`**

Find (around line 1529-1534):

```js
function askAI(q){$('ainp').value=q;sendAI();}
async function sendAI(){
  var inp=$('ainp'),q=(inp.value||'').trim();
  if(!q)return;
  if(lawAiBusy){toast('Please wait for the current response first');return;}
  lawAiBusy=true;
```

Replace with:

```js
function askAI(q){$('ainp').value=q;sendAI();}
// AI Chain of Custody (2026-08-13): fire-and-forget from sendAI()'s point of
// view -- a logging failure must never block or hide the AI response the
// rep already received (same "best-effort" posture writeAuditLog() itself
// documents), but it IS surfaced honestly via toast, not silently
// swallowed, matching this platform's established saveOk-style discipline
// rather than an empty catch(e){}.
function lawLogAiInteraction(prompt,response,toolsUsed){
  lawAuth('ai_log',{prompt:prompt,response:response,matter_id:$('aimatter')?$('aimatter').value:'general',tools_used:toolsUsed||[]},true)
    .then(function(r){ if(!r.ok) toast('AI interaction was not logged to the Chain of Custody record — ' + (r.msg||'try again')); })
    .catch(function(){ toast('AI interaction was not logged to the Chain of Custody record — network error'); });
}
async function sendAI(){
  var inp=$('ainp'),q=(inp.value||'').trim();
  if(!q)return;
  var matterSel=$('aimatter');
  if(matterSel && !matterSel.value){ toast('Select a matter (or "General") before sending — required for the AI Chain of Custody record'); return; }
  if(lawAiBusy){toast('Please wait for the current response first');return;}
  lawAiBusy=true;
```

- [ ] **Step 4: Log after a real exchange completes**

Find (around line 1608-1614):

```js
    var rep2=(data2.content&&data2.content[0]&&data2.content[0].text)||'No response text returned.';
    thinking.textContent=rep2;
    aiHist.push({role:'assistant',content:rep2});
  }catch(e){thinking.textContent='Could not connect to Claude. Check your connection and try again.';}
  finally{lawAiBusy=false;}
  chat.scrollTop=chat.scrollHeight;
}
```

Replace with:

```js
    var rep2=(data2.content&&data2.content[0]&&data2.content[0].text)||'No response text returned.';
    thinking.textContent=rep2;
    aiHist.push({role:'assistant',content:rep2});
    lawLogAiInteraction(q,rep2,[toolUse.name]);
  }catch(e){thinking.textContent='Could not connect to Claude. Check your connection and try again.';}
  finally{lawAiBusy=false;}
  chat.scrollTop=chat.scrollHeight;
}
```

**Note for the implementer:** the no-tool-use path (the `if(!toolUse){...return;}` branch a few lines earlier, around line 1586-1592) ALSO needs its own `lawLogAiInteraction(q, rep, [])` call before its `return;` — every real exchange must be logged, not just the tool-use path. Read the actual current function body first (Tasks 1-3 haven't changed this file, so it should match what's shown in this task's brief exactly) and add the matching call there too, mirroring this step's pattern with an empty tools array.

- [ ] **Step 5: Run node --check equivalent**

This is an HTML file with inline `<script>` blocks — if `tools/checkblocks.py`-equivalent tooling exists for `sairnlaw.html` (check for a `tools/*.py` script parametrized by filename, or adapt `stonedesk.html`'s `tools/checkblocks.py` to point at `sairnlaw.html` if it accepts a filename argument), run it and confirm zero failed blocks. If no such tooling exists for this file, extract each touched `<script>` block and run `node --check` on it directly.

- [ ] **Step 6: Manual verification (browser console)**

Open `sairnlaw.html`, log in with a real session, navigate to the AI panel:

```js
document.getElementById('aimatter').options.length >= 2;  // -> true (blank + General, plus real matters if any exist)
sendAI();  // with #ainp empty and #aimatter blank -- should just return (no request), per Step 1's !q guard
document.getElementById('ainp').value = 'test';
document.getElementById('aimatter').value = '';
sendAI();  // -> toast: "Select a matter..." -- blocked
document.getElementById('aimatter').value = 'general';
sendAI();  // -> real request fires; after it resolves, an ai_log call should have fired (check Network tab for a law-auth POST with action:'ai_log')
```

Expected: matches every comment.

- [ ] **Step 7: Commit**

```bash
git add sairnlaw.html
git commit -m "feat: SAIRNlaw AI Chain of Custody -- log every sendAI() exchange, required matter picker"
```

---

### Task 5: Client — AI Chain of Custody review panel

**Files:**
- Modify: `sairnlaw.html` (new nav entry + panel HTML, near the existing Security & Audit panel ~L882-923; `nav()` ~L1267-1289; new render/action functions near `rSecurity()`/`secLoadAudit()` ~L3007-3107)

**Interfaces:**
- Consumes: `action:'ai_list'`/`'ai_review'`/`'ai_reject'`/`'ai_used_in_filing'` (Tasks 2-3), `H()` (existing escape helper), `fdatetime()` (existing, used by `secLoadAudit()`), `lawAuth()`.
- Produces: nothing consumed elsewhere — this is the terminal UI layer for this feature.

- [ ] **Step 1: Add the nav entry**

Find (around line 296-298):

```html
      <button class="sb" id="sb-citator" onclick="nav('citator')"><span class="sico">&#128220;</span>Citator (Phase A)</button>
```

Replace with:

```html
      <button class="sb" id="sb-citator" onclick="nav('citator')"><span class="sico">&#128220;</span>Citator (Phase A)</button>
      <button class="sb" id="sb-aicoc" onclick="nav('aicoc')"><span class="sico">&#128737;&#65039;</span>AI Chain of Custody</button>
```

- [ ] **Step 2: Add the panel shell**

Find (around line 858-860, right before the citator panel opens):

```html
<div class="panel" id="panel-citator">
```

Replace with:

```html
<div class="panel" id="panel-aicoc">
  <div class="ph"><div><div class="ptitle">AI Chain of Custody</div><div class="psub">Every AI interaction, matter-linked and logged server-side the moment it happens. Nothing here can be edited or deleted -- there is no such code path.</div></div></div>
  <div class="card"><div class="cb">
    <button class="btn bo" onclick="aicocLoad()">Refresh</button>
    <div id="aicoc-list" style="margin-top:12px"></div>
  </div></div>
</div>
<div class="panel" id="panel-citator">
```

- [ ] **Step 3: Wire `nav()`**

Find (around line 1287-1288):

```js
  if(id==='citator')rCitator();
  if(id==='security')rSecurity();
```

Replace with:

```js
  if(id==='citator')rCitator();
  if(id==='security')rSecurity();
  if(id==='aicoc')aicocLoad();
```

- [ ] **Step 4: Add the render + action functions**

Find (the start of `secLoadAudit()` — around line 3082):

```js
function secLoadAudit(){
```

Replace with:

```js
var AICOC_STATUS_LABEL={unreviewed:'Unreviewed',reviewed:'Reviewed',rejected:'Rejected',used_in_filing:'Used in Filing'};
function aicocLoad(){
  var box=$('aicoc-list');
  box.innerHTML='<div style="color:var(--muted);font-size:13px">Loading…</div>';
  lawAuth('ai_list',{limit:200},true).then(function(r){
    if(!r.ok){box.innerHTML='<div style="color:var(--muted);font-size:13px">'+H(r.msg||'Could not load the AI Chain of Custody log.')+'</div>';return;}
    var rows=r.data.entries||[];
    if(!rows.length){box.innerHTML='<div style="color:var(--muted);font-size:13px">No AI interactions logged yet.</div>';return;}
    var mmap={};matters().forEach(function(m){mmap[m.id]=m.matter_number+' -- '+m.matter_name;});
    box.innerHTML=rows.map(function(e){
      var matterLabel=e.matter_id==='general'?'General':(mmap[e.matter_id]||e.matter_id||'General');
      var statusColor=e.status==='rejected'?'var(--danger)':(e.status==='used_in_filing'?'var(--ok)':(e.status==='reviewed'?'var(--brand)':'var(--warn)'));
      var actions='';
      if(e.status==='unreviewed'){
        actions='<button class="btn bp" style="margin-right:6px" onclick="aicocReview(\''+e.id+'\')">Approve</button>'
          +'<button class="btn bo" onclick="aicocReject(\''+e.id+'\')">Reject</button>';
      } else if(e.status==='reviewed'){
        actions='<button class="btn bp" onclick="aicocMarkFiled(\''+e.id+'\')">Mark Used in Filing</button>';
      } else if(e.status==='rejected'){
        actions='<div style="font-size:12px;color:var(--muted)">Rejected: '+H(e.reject_reason||'')+'</div>';
      }
      return '<div class="card" style="margin-bottom:10px"><div class="cb">'
        +'<div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;margin-bottom:6px">'
        +'<div style="font-size:12px;color:var(--muted)">'+H(fdatetime(e.created_at))+' &middot; '+H(e.employee_id||'--')+(e.role?' ('+H(e.role)+')':'')+' &middot; '+H(matterLabel)+'</div>'
        +'<div style="font-size:11px;font-weight:700;color:'+statusColor+'">'+H(AICOC_STATUS_LABEL[e.status]||e.status)+'</div>'
        +'</div>'
        +'<div style="font-size:12px;color:var(--muted);font-style:italic;margin-bottom:6px">'+H(e.prompt||'')+'</div>'
        +'<div style="font-size:13px;white-space:pre-wrap;max-height:140px;overflow-y:auto;background:var(--pt);padding:8px 10px;border-radius:6px;margin-bottom:8px">'+H(e.response||'')+'</div>'
        +actions
        +'</div></div>';
    }).join('');
  });
}
function aicocReview(id){
  lawAuth('ai_review',{log_entry_id:id},true).then(function(r){
    if(!r.ok){toast(r.msg||'Could not approve this entry');return;}
    toast('Marked reviewed');aicocLoad();
  });
}
function aicocReject(id){
  var reason=prompt('Reason for rejecting this AI output (required):');
  if(!reason||!reason.trim())return;
  lawAuth('ai_reject',{log_entry_id:id,reason:reason.trim()},true).then(function(r){
    if(!r.ok){toast(r.msg||'Could not reject this entry');return;}
    toast('Marked rejected');aicocLoad();
  });
}
function aicocMarkFiled(id){
  if(!confirm('Confirm: you personally verified this AI output before relying on it in a filing?'))return;
  lawAuth('ai_used_in_filing',{log_entry_id:id},true).then(function(r){
    if(!r.ok){toast(r.msg||'Could not mark this entry as used in filing');return;}
    toast('Marked used in filing');aicocLoad();
  });
}
function secLoadAudit(){
```

- [ ] **Step 5: Run node --check equivalent**

Same as Task 4 Step 5 — confirm zero syntax errors on the touched script block(s).

- [ ] **Step 6: Manual verification (browser console)**

With at least one `unreviewed` entry present (from Task 4's verification):

```js
nav('aicoc');
document.getElementById('aicoc-list').children.length > 0;  // -> true, at least one entry card rendered
// Click Approve on that entry (or call aicocReview('<its id>') directly with the real id from ai_list's response)
// After it resolves: that entry's card should now show "Mark Used in Filing" instead of Approve/Reject.
```

Expected: matches every comment — the full unreviewed → reviewed → used_in_filing flow is reachable through the UI, and a rejected entry shows its reason with no further actions available.

- [ ] **Step 7: Commit**

```bash
git add sairnlaw.html
git commit -m "feat: SAIRNlaw AI Chain of Custody -- review panel (approve/reject/mark used in filing)"
```

---

### Task 6: Full verification sweep, live-verify, and push

**Files:** none (verification only)

- [ ] **Step 1: Full local syntax sweep**

`node --check api/law-auth.js` (clean). Whatever HTML-script-block checker applies to `sairnlaw.html` (per Task 4/5 Step 5) — zero failures.

- [ ] **Step 2: Confirm the migration has been run**

Ask whoever is present to confirm `sql/sairnlaw_ai_chain_of_custody.sql` has been run in Supabase's SQL editor (per Task 1's hand-off note) — required before this task's live checks can pass. If it hasn't been run yet, stop here and report that as the blocker rather than proceeding to push with an unverified server layer.

- [ ] **Step 3: Run the full Guardian review before commit/push**

Invoke the `sairn-guardian-v2` skill's full Check 0 + numbered checks against the diff, per CLAUDE.md's standing Push Protocol. Pay particular attention to: Check 25/26 (every value written into `aicoc-list`'s `innerHTML` — `e.prompt`, `e.response`, `e.reject_reason`, `matterLabel`, `e.employee_id`, `e.role` — must go through `H()`, matching this file's own established convention); Check 28 (every new server action re-verifies `expectedApp==='sairnlaw'` via `verifySessionToken`, and `ai_list`/`ai_review`/`ai_reject`/`ai_used_in_filing` all check `AI_COC_REVIEW_ROLES`, not just session validity).

- [ ] **Step 4: Combined end-to-end manual verification**

Real DB-backed, not simulated — requires the migration from Step 2 to actually be live:
1. Log a real `sendAI()` exchange with a real matter selected. Confirm a new row lands in `sairnlaw_audit_log` with `event_type='ai_interaction'` (via a direct Supabase table read, or via `ai_list`'s response).
2. Confirm a SECOND SAIRNlaw license/session cannot see the first license's entries via `ai_list` (the `license_hash` scoping) — this is the same class of check the platform's own prior cross-app-collision incident was caught with; don't just trust the code.
3. Attempt `UPDATE`/`DELETE` against `sairnlaw_audit_log` directly (e.g. via the Supabase SQL editor, as the human who ran the migration) and confirm both genuinely fail at the database level with a permission error — not just "the UI doesn't expose a button."
4. Confirm `ai_reject` with no `reason` in the body returns 400.
5. Confirm `ai_used_in_filing` on a still-`unreviewed` entry returns 409 `NOT_REVIEWED`.
6. Confirm a `paralegal`-role session gets 403 from `ai_list`/`ai_review`/`ai_reject`/`ai_used_in_filing`.
7. Confirm a Send with no matter selected is blocked client-side with a real message (Task 4 Step 6).

- [ ] **Step 5: Push**

```bash
git push origin main
```

- [ ] **Step 6: Live-verify against production**

Repeat Step 4's checks against `sairn.vercel.app/sairnlaw` directly (real login, not a local file). Confirm the deployed file hash matches the pushed commit (normalize line endings before comparing — CRLF/LF, not content, was the cause of a known false-positive deploy-mismatch class this session).

- [ ] **Step 7: Write the session handoff**

Use the `sairn-session-handoff` skill to record this feature's landing. Since this is the first SAIRNlaw-specific session in a while, check whether SAIRNlaw has its own `SAIRNLAW-SESSION-N-HANDOFF.md` numbering series already (per this project's per-app-prefix naming convention) or whether this should be the first one — re-derive from the repo, don't assume.

---

## Self-Review Notes

- **Spec coverage:** every requirement from the design spec is covered — real server-side immutable logging (Tasks 1-2, via extended existing infrastructure rather than new), required matter picker (Task 4), review queue with reject-reason requirement (Task 5), the filing-gate attestation restricted to `reviewed` entries only (Task 3 server-side, Task 5 client-side), role restriction to owner/attorney for the review workflow (Tasks 3 and 5), server-derived (never client-supplied) `employee_id`/`role` for non-repudiation (Task 2's `ai_log`, using `caller.employee_id`/`caller.role` from the verified session, never `body.employee_id`). The architecture correction (extend existing `sairnlaw_audit_log`/`api/law-auth.js` instead of building new) is disclosed explicitly in Global Constraints, not silently substituted for the spec's literal wording.
- **Placeholder scan:** no TBD/TODO, no "add appropriate handling" — every step shows real code matching the actual current file content (re-read immediately before writing this plan) or a real runnable check with a stated expected result. Task 4 Step 4's note about the second `sendAI()` branch needing its own logging call is an explicit instruction with a concrete pattern to mirror, not a vague "handle this too."
- **Type/name consistency:** `ai_log`/`ai_list`/`ai_review`/`ai_reject`/`ai_used_in_filing` action names, the `AI_COC_REVIEW_ROLES`/`AI_PROMPT_RESPONSE_CAP` constants, and the `log_entry_id`/`matter_id`/`tools_used`/`reason` field names are spelled identically everywhere they're produced (Tasks 2-3, server) and consumed (Tasks 4-5, client). `lawLogAiInteraction()` (Task 4) and `aicocLoad()`/`aicocReview()`/`aicocReject()`/`aicocMarkFiled()` (Task 5) match the `ai_*` action names they call exactly.
