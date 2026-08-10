# SAIRNcash Pivot Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lay the real foundation the SAIRNcash pivot spec
(`docs/superpowers/specs/2026-08-10-sairncash-pivot-design.md`) depends
on before any tax/retirement-estimator or Bridge-integration work
begins: (1) unify SAIRNtype's scattered, untracked source into one
real, git-tracked, deployable project, and (2) fix the two real
silent-failure bugs the audit found — `handleWaitlist()`'s fake success
and `isSubscribed()`'s forgeable client-only timer. Both are the exact
bug class this session has been hunting across every other app; neither
ships in SAIRNcash's foundation.

**Explicitly deferred to a later plan, not this one:** the tax/
retirement estimator itself, Bridge income/expense pull, the "does not
file taxes" copy and trial-notice UI from spec §3 (those need the
foundation below to exist first — building product copy and new
features on top of unversioned, partially-forged-access source would
repeat exactly the mistake the spec's audit flagged).

## Global Constraints

- No AI-keyboard feature code (Ghost Complete, Tone Shift, Smart Reply,
  File Manager, Voice Mode, Compose Mode) is carried forward — dropped
  per spec §1, not migrated then deleted later.
- The unified source becomes `sairncash.html` in `SAIRN1/SAIRN`
  (matches this platform's single-file-per-app convention) plus its
  own `api/sairncash/` subdirectory for the Stripe routes — kept
  separate from the shared `api/claude.js`/`api/sd-data.js` used by
  the license-key-based apps, since SAIRNcash's subscribers aren't
  SAIRN B2B license holders.
- `node --check` on every new/modified `api/**/*.js` file. Standard
  syntax checks (`checkblocks.py`, `div_balance_check.py`,
  `duplicate_global_check.py`) on `sairncash.html`.
- Real Stripe **test-mode** keys for all verification in this plan —
  never live keys during development.
- Per this session's standing rule: any SQL migration is written by me,
  run by Michael in Supabase's SQL editor — I have no DB execution
  access.

---

### Task 1: Unify and version-control the SAIRNcash source

**Files:**
- Create: `sairncash.html` (from `~/Downloads/SAIRNtype_UNIVERSE.html`,
  rebranded, AI-keyboard modes stripped per Global Constraints)
- Create: `api/sairncash/checkout.js`, `api/sairncash/verify.js` (from
  `~/Downloads/SAIRNtype_PRO (1)/sairntype_stripe/api/{checkout,verify}.js`
  — real, correct Stripe integration, confirmed in the audit; ported
  with path updates only, no logic rewrite needed here)

- [ ] **Step 1: Confirm Vercel environment prerequisites before writing any code**

Check (via the Vercel dashboard or `mcp__claude_ai_Vercel` tools) that
`STRIPE_SECRET_KEY`, `STRIPE_PRICE_ID`, and `SITE_URL` exist in the
shared Vercel project's environment variables. The audit found no
existing usage of `STRIPE_SECRET_KEY`/`STRIPE_PRICE_ID` anywhere in
the currently-tracked `api/*.js` — StoneDesk's own Stripe references
(`sd-data.js`/`sd-render.js`) only check a pre-existing
`stripe_subscription_id` flag, they don't create Checkout Sessions.
Do not assume these keys exist; if missing, that's a manual
Vercel-dashboard step for Michael, surfaced explicitly before Task 1
continues.

- [ ] **Step 2: Port the front end, stripped and rebranded**

Copy `SAIRNtype_UNIVERSE.html` to `sairncash.html`. Remove: the
Ghost Complete / Tone Shift / Smart Reply / File Manager / Voice Mode
/ Compose Mode panels and their backing JS (`switchMode`,
`renderActions`, voice-recognition code at `initVoice()`/
`startListening()`/etc., file-drop analysis at `readEntry()`/
`analyzeFiles()`), the investor "Business Plan" page section, and the
`$988B market`/`82% margin` marketing stats row (fabricated-KPI-
adjacent — real numbers for a different product's projections, not
SAIRNcash's). Keep: the paywall/checkout flow, the app-shell chrome,
the chat-panel plumbing (retargeted to tax/retirement questions in a
later plan), `handleWaitlist()`/`isSubscribed()` (fixed in Tasks 2-3
below, not left as-is).

- [ ] **Step 3: Port the Stripe backend**

Copy `checkout.js`/`verify.js` into `api/sairncash/`. Update
`sairncash.html`'s fetch calls from `/api/checkout`/`/api/verify` to
`/api/sairncash/checkout`/`/api/sairncash/verify`. No logic changes in
this step — the audit already confirmed these two files are correct.

- [ ] **Step 4: Syntax-check**

```
node --check api/sairncash/checkout.js
node --check api/sairncash/verify.js
python tools/checkblocks.py sairncash.html
python tools/div_balance_check.py sairncash.html
python tools/duplicate_global_check.py sairncash.html
```
Expected: 0 failures across all five.

- [ ] **Step 5: Commit**

```
git add sairncash.html api/sairncash/checkout.js api/sairncash/verify.js
git commit -m "feat: SAIRNcash foundation -- unify and version-control the pivoted SAIRNtype source

..."
```

---

### Task 2: Fix `isSubscribed()` — use the real Stripe expiry, close the forgeable-access gap

**Files:** Modify `sairncash.html` (ported `isSubscribed()`/`saveSub()`/
`getSub()` from `SAIRNtype_UNIVERSE.html:1129-1131`)

- [ ] **Step 1: Write the implementation**

Replace the arbitrary 35-day local timer with the real `expiresAt`
`/api/verify` already returns (confirmed present in `verify.js`'s
response, currently discarded by the client):

```js
function getSub() { try { return JSON.parse(localStorage.getItem('sairn_sub') || 'null'); } catch { return null; } }
function saveSub(d) { localStorage.setItem('sairn_sub', JSON.stringify(d)); }
function isSubscribed() {
  const s = getSub();
  if (!s || !s.valid || !s.expiresAt) return false;
  return Date.now() < new Date(s.expiresAt).getTime();
}
```

This alone closes the "expired sub still grants access" half of the
gap. It does NOT close the other half -- a user can still forge
`localStorage.sairn_sub` with a future `expiresAt` for free access,
since there is still no per-load server round-trip. Close that too:

```js
// Re-verify against the real subscription state periodically, not just
// once at checkout -- a forged localStorage.sairn_sub with a future
// expiresAt would otherwise grant free access indefinitely. Checked
// once per app load (not per-request -- that would be excessive load
// for a financial-planning app where session length is naturally
// longer than a quick lookup), and re-saves the real server response,
// so a genuinely cancelled subscription is caught within one session.
async function reverifySubscription() {
  const s = getSub();
  if (!s || !s.subscriptionId) return isSubscribed();
  try {
    const res = await fetch('/api/sairncash/verify', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({subscriptionId: s.subscriptionId})});
    const data = await res.json();
    if (data.valid) { saveSub(data); return true; }
    localStorage.removeItem('sairn_sub');
    return false;
  } catch(e) {
    // Network failure -- fall back to the last known real expiresAt
    // rather than hard-locking out a legitimately subscribed user who
    // is just offline. Still bounded by the real expiry, not a fake
    // local timer.
    return isSubscribed();
  }
}
```

Note: this requires `verify.js` (Task 1) to accept a `subscriptionId`
lookup path in addition to its current `sessionId` lookup (checkout
return only provides a `sessionId`; a returning user's stored session
has a `subscriptionId`, not a `sessionId`). Add a
`stripe.subscriptions.retrieve(subscriptionId)` branch to
`api/sairncash/verify.js` alongside the existing
`checkout.sessions.retrieve` branch, keyed on which field the request
body contains.

`initApp()` (`SAIRNtype_UNIVERSE.html:1173`) calls `await
reverifySubscription()` in place of the current `isSubscribed()` check,
so this re-verification happens on every real app load, not just once
at checkout.

- [ ] **Step 2: Syntax-check**

```
python tools/checkblocks.py sairncash.html
python tools/div_balance_check.py sairncash.html
node --check api/sairncash/verify.js
```

- [ ] **Step 3: Verification (Stripe test mode)**

1. Complete a real test-mode checkout, confirm access granted and
   `sairn_sub.expiresAt` matches Stripe's real `current_period_end`.
2. Forge `localStorage.sairn_sub` with `valid:true` and a future
   `expiresAt` but no real `subscriptionId` — confirm
   `reverifySubscription()` on next load either fails closed (no
   `subscriptionId` to check) or, if a `subscriptionId` is also forged,
   confirm the `/api/sairncash/verify` round-trip rejects it (Stripe
   has no record of a fabricated subscription ID) and access is
   revoked.
3. Cancel the real test subscription directly in the Stripe dashboard,
   reload the app, confirm access is revoked within that same session
   (not after a stale local timer).

- [ ] **Step 4: Commit**

```
git add sairncash.html api/sairncash/verify.js
git commit -m "fix: SAIRNcash -- isSubscribed() uses real Stripe expiry, re-verifies server-side per load

..."
```

---

### Task 3: Fix `handleWaitlist()` — real persistence, no fabricated success

**Files:**
- Create: `api/sairncash/waitlist.js`
- Create: `sql/sairncash_waitlist_schema.sql`
- Modify: `sairncash.html` (`handleWaitlist()`)

- [ ] **Step 1: Write the migration**

```sql
-- sql/sairncash_waitlist_schema.sql
create table if not exists public.sairncash_waitlist (
  id         uuid primary key default gen_random_uuid(),
  email      text not null,
  created_at timestamptz not null default now(),
  unique (email)
);
alter table public.sairncash_waitlist enable row level security;
drop policy if exists "svc only sairncash_waitlist" on public.sairncash_waitlist;
create policy "svc only sairncash_waitlist" on public.sairncash_waitlist
  for all using (false) with check (false);
grant select, insert on public.sairncash_waitlist to service_role;
```

- [ ] **Step 2: Write the server route**

```js
// api/sairncash/waitlist.js
module.exports = async (req, res) => {
  if (req.method !== 'POST') { res.status(405).json({error:{message:'POST only'}}); return; }
  const email = req.body && req.body.email;
  if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { res.status(400).json({error:{message:'Valid email required'}}); return; }
  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!SUPABASE_URL || !SERVICE_KEY) { res.status(500).json({error:{message:'Server configuration error'}}); return; }
  try {
    const r = await fetch(SUPABASE_URL + '/rest/v1/sairncash_waitlist?on_conflict=email', {
      method: 'POST',
      headers: { apikey: SERVICE_KEY, Authorization: 'Bearer ' + SERVICE_KEY, 'Content-Type': 'application/json', Prefer: 'resolution=merge-duplicates' },
      body: JSON.stringify({ email: email })
    });
    if (r.status === 404 || r.status === 400) { res.status(503).json({error:{code:'NOT_PROVISIONED', message:'Waitlist table not set up yet -- run sql/sairncash_waitlist_schema.sql in Supabase first.'}}); return; }
    if (!r.ok) { res.status(502).json({error:{message:'Could not join waitlist -- try again'}}); return; }
    res.status(200).json({ ok: true });
  } catch (e) {
    res.status(502).json({error:{message:'Could not join waitlist -- try again'}});
  }
};
```

- [ ] **Step 3: Fix the client**

```js
async function handleWaitlist() {
  const inp = document.getElementById('waitlistEmail');
  const btn = document.querySelector('.waitlist-btn');
  if (!inp.value.includes('@')) { inp.style.borderColor='var(--spark)'; setTimeout(()=>inp.style.borderColor='',1500); return; }
  const email = inp.value.trim();
  btn.disabled = true; btn.textContent = 'Joining...';
  try {
    const res = await fetch('/api/sairncash/waitlist', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({email})});
    const data = await res.json().catch(()=>null);
    if (!res.ok || !data || !data.ok) {
      btn.disabled = false; btn.textContent = 'Claim early access';
      showToast((data && data.error && data.error.message) || 'Could not join waitlist -- try again');
      return;
    }
    btn.textContent = "✓ You're in!";
    btn.style.background = 'var(--pulse)'; btn.style.color = '#0A0B14';
    inp.value = '';
    setTimeout(() => { btn.disabled = false; btn.textContent = 'Claim early access'; btn.style.background = ''; btn.style.color = ''; }, 3000);
  } catch (e) {
    btn.disabled = false; btn.textContent = 'Claim early access';
    showToast('Could not join waitlist -- check your connection and try again');
  }
}
```

The success state now only shows after a real, confirmed server write
— not unconditionally on any `@`-containing input.

- [ ] **Step 4: Syntax-check**

```
node --check api/sairncash/waitlist.js
python tools/checkblocks.py sairncash.html
python tools/div_balance_check.py sairncash.html
```

- [ ] **Step 5: Verification**

Before the migration runs: confirm `NOT_PROVISIONED` is returned
cleanly (no crash) and the client shows the real error, not a
fabricated success. After Michael runs the migration: submit a real
email, confirm `{ok:true}`, confirm the row exists via a direct
`select * from sairncash_waitlist` (Michael) or by re-submitting the
same email and confirming the `on_conflict` merge doesn't error
(idempotent, no duplicate-email crash).

- [ ] **Step 6: Commit**

```
git add sairncash.html api/sairncash/waitlist.js sql/sairncash_waitlist_schema.sql
git commit -m "fix: SAIRNcash -- handleWaitlist() persists for real instead of a fabricated success toast

..."
```

---

### Task 4: Push, live-verify, update the spec status

- [ ] **Step 1:** Full local re-check of all changed files
  (`checkblocks.py`/`div_balance_check.py`/`duplicate_global_check.py`
  on `sairncash.html`; `node --check` on all three new `api/sairncash/`
  files).
- [ ] **Step 2:** Push.
- [ ] **Step 3:** Live-verify `sairn.vercel.app/sairncash` loads, the
  paywall renders, and (Stripe test mode) the full
  checkout → verify → `isSubscribed()`/`reverifySubscription()` path
  works against the deployed functions, not just local code.
- [ ] **Step 4:** Re-run Task 2 Step 3's forged-`localStorage` test and
  Task 3 Step 5's waitlist test against the live deployment
  specifically — a clean push is not proof the live app reflects the
  fix (standing project rule).
- [ ] **Step 5:** Update
  `docs/superpowers/specs/2026-08-10-sairncash-pivot-design.md`'s
  status and §4 (both fixes now marked resolved, with commit SHAs),
  matching this session's own SAIRN-BACKLOG.md resolution pattern.

---

**Not started. Awaiting explicit go-ahead before any code in Tasks 1-4
is written**, per standing project practice (spec → plan → confirmed
go → execute).
