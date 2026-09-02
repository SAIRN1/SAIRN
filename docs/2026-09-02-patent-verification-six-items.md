# Patent verification — six items, checked against the real code

**For:** patent attorney review.
**Standard applied:** accuracy over completeness. "Not built" is recorded as
"not built" wherever that is what the code says. Every claim below names the
file and, where it matters, the line, so counsel can verify it independently
rather than take this document's word.

**One caveat about this document's own provenance, stated first because it
bounds everything after it.** I have no record of the original six-item brief.
It is not in this repository — none of its distinctive terms ("Composite
Inference Context", "intelligence-extraction pipeline", "token-deduction
concurrency") appear in any tracked file, and the only patent document present
is `docs/2026-08-30-sairnfreedom-competitive-and-patent-scan.md`, which is a
prior-art scan of a different subject. This report answers the six items **as
restated to me**. If the original brief carried specific claim language or
framing, that framing is not reflected here.

---

## 1. Real database / storage structure

**Built, and it is a hybrid — which matters, because the two halves have very
different durability properties.**

- **Server side:** Supabase (PostgreSQL, reached over PostgREST). **233
  distinct tables** are declared across `sql/*.sql`. The dominant pattern is a
  narrow relational envelope plus a `jsonb` payload: a table carries
  `license_hash`, `app_id`, an entity id, a few indexed/queryable columns, and
  a `data jsonb` column holding the rest. **66 schema files declare a `data
  jsonb` column.** Example: `sql/sairnroofing_billing_schema.sql` —
  `rf_invoices` has real columns for `invoice_number`, `status`, `issue_date`,
  and a `data jsonb` for line items, tax and terms.
- **Tenancy** is by `license_hash` on essentially every table, not by a user id.
- **Access** is exclusively through per-app API endpoints in `api/`, with a
  registry of addressable resources under `api/_resources/`. Clones hold no
  generic `information_schema` access; there is no ORM and no direct client
  connection to Postgres.
- **Client side:** the customer-facing apps are single-file HTML documents and
  a large amount of application state lives in **browser `localStorage`**, not
  on the server. In SAIRNvet, for example, every panel's store is a
  `localStorage` key (`sv_*`); the same is true of SAIRNbiz (`sb_*`).

**The honest characterisation:** this is not one storage architecture. It is a
server-synced relational-plus-jsonb store for the resources that have been
wired to the API, and browser-local storage for everything that has not. Which
half a given feature uses is a per-feature fact, not a platform-wide one.

---

## 2. "Composite Inference Context"

**Not built. No construct of that name exists, and no abstraction plays that
role.**

Searched the whole tracked tree. There are exactly three matches for
"composite" and none is relevant: one comment in `api/sd-data.js:404` about a
**composite database index**, and product rows for **composite dental resin**
in `sairndental.html`.

**What actually exists** is a per-app, hand-written string builder. In
StoneDesk, `buildSDSystemPrompt()` (`stonedesk.html:25429`) concatenates four
blocks and returns a string:

1. a hardcoded base system prompt;
2. `profileBlock` — business profile fields (company, EIN, city, headcount,
   revenue range, owner, free-text shop notes) when a profile is loaded;
3. `memBlock` — **the first 10 entries** of `_sdMemories`, under the heading
   "WHAT YOU KNOW ABOUT THIS SHOP (from past sessions)";
4. `styleNote` — one of three canned sentences (see item 4).

At the call site (`stonedesk.html:25531`) a mode string and, conditionally, a
network-intelligence line are appended before the result is sent as `system`.

**There is no context object, no scoring or ranking of candidate context, no
relevance selection, and no cross-source merge policy.** Memory selection is
`slice(0, 10)` on insertion order. The composition is one function in one
app's HTML file; other apps have their own separate equivalents.

---

## 3. Intelligence-extraction pipeline

**Partially built. The server half is real and working; the client half that
would feed it has never been able to run.**

- **Real and live:** `api/network.js` and the `network_insights` table.
  `GET /api/network?app=stonedesk` returns `200 {"ok":true,"insights":[]}`.
  Write access was verified on 2026-09-01 by a real `POST`, which returned
  `200 {"ok":true}`. The endpoint enforces structurally that only short bare
  identifiers (`^[a-z0-9_]{1,64}$`) may be stored for `type` and `pattern`, so
  free text — and therefore PII, names and prices — cannot be written at all.
  Aggregation requires **at least 3 occurrences** within a **30-day** window
  before a pattern is returned, which is a stated anonymity floor rather than a
  formatting choice.
- **Not functioning:** the only thing that would ever call the write path,
  `sendNetworkInsight()` (`stonedesk.html:25187`), has exactly one call site,
  and that call site sits inside a `window.sendMessage` patch whose fourth line
  reads `document.getElementById('userInput')` — **an id that occurs zero times
  in the markup**. The function returns immediately on every invocation. **No
  signal has ever been collected.** The empty `insights: []` above is that
  fact, not an absence of patterns.
- The corresponding read path (`loadNetworkIntelligence()`) *does* run on every
  page load, caches for an hour, and its result is consumed only by the same
  dead function.
- **Adjacent, separate:** `api/org-intel.js` (SAIRNscape) — its own header
  records that `org_id` is a plain user-typed string, **not a validated or
  hashed credential**. `sd_shared_knowledge` exists as a declared table.

**The honest characterisation:** the mechanism is designed and the server side
demonstrably works; the extraction step is not connected in the shipping
client, and has produced no data.

---

## 4. User style profiles

**Not built.**

No `style_profile`, `writingStyle`, `tone_profile`, `user_style` or
`voice_profile` exists anywhere in the tracked tree.

The only thing bearing the word "style" in the inference path is
`stonedesk.html:25452`:

    const style = (p && p.preferences && p.preferences.ai_style) || 'direct';

which selects between **three fixed sentences** — "Be direct and concise.",
"Provide detailed explanations.", or a conversational variant. It is a
**stored user preference with three values**, defaulting to `direct`. Nothing
observes, derives, learns or updates it, and it is per-shop-profile rather than
per-user.

---

## 5. Token-deduction concurrency handling

**Not built, in two distinct senses — and the second is the one that matters
for any claim about metering.**

**(a) There is no token balance and nothing is deducted.** No
`token_balance`, `tokens_remaining`, `credit_balance` or equivalent exists.
Nothing is decremented anywhere.

**(b) What does exist is a counter, and it is not concurrency-safe.**
`api/_lib/ai-rate-limit.js` implements a per-`app_id` sliding-window limiter
against `sairn_ai_rate_limit_log`. Its own header is candid about its status
and so is this report:

- It is keyed on **`app_id`, not on a user or a licence** — it counts calls per
  application, platform-wide.
- It **ships in observe mode**: it records every call and logs when a limit
  *would* have been exceeded, without blocking. Enforcement is off unless
  `SAIRN_AI_RATE_LIMIT_MODE=enforce` is set. Default limit 200/day.
- It **fails open**: if Supabase is unreachable or the table is missing, the
  call is allowed.
- **The critical structural point.** The sequence at
  `api/_lib/ai-rate-limit.js:69-93` is: `SELECT count` → then `INSERT`. These
  are two separate HTTP requests with no transaction, no row lock, no atomic
  increment, and no uniqueness constraint serialising them. **Two concurrent
  invocations both read the same count and both proceed.** In a serverless
  deployment where concurrency is the normal case, the limit is therefore
  approximate by construction. The file's comment explains the count-then-record
  ordering as making "a limit of 200 permit exactly 200 calls", which holds
  only for strictly sequential traffic.

**The honest characterisation:** there is no metering system to describe. There
is a best-effort, non-blocking, non-atomic per-app call counter that is
explicitly documented as not reliably capping usage or cost.

---

## 6. StoneDesk's real risk-detection defaults

**Built, and simple. Hardcoded rule thresholds, not a model, not a learned
score.**

`runAlertScan()` (`stonedesk.html:21219`) applies two rules:

| Condition | Threshold | Level |
|---|---|---|
| Quote pending approval | ≥ 24 h | red |
| Quote pending approval | ≥ 12 h | yellow |
| Warranty past expiry | days left < 0 | red |
| Warranty nearing expiry | ≤ 30 days | yellow |

A per-customer **health score** (`stonedesk.html:21470`) starts at **100** and
subtracts:

- **−20** if the record has not been updated in **> 14 days**
- **−30** if status is `quoted` and it was created **> 24 h** ago
- **−15** if any balance is owed

floored at 0, then banded: **≥ 80 "Healthy", ≥ 50 "Needs Attention", otherwise
"At Risk"**.

**The thresholds are not user-configurable.** `saveAlertSettings()`
(`stonedesk.html:21885`) persists only an email address, a phone number, and
six **on/off toggles** selecting which alert types fire — `quote24h`,
`overdue`, `quote12h`, `warrExpiry`, `complete`, `newCust` — to
`sd_alert_settings` in `localStorage`. No numeric threshold is exposed to the
user or stored.

---

## Summary for counsel

| # | Item | Status |
|---|---|---|
| 1 | Database / storage structure | **Built** — hybrid: Postgres/jsonb via per-app API, plus substantial browser `localStorage` |
| 2 | Composite Inference Context | **Not built** — no such construct; a per-app string concatenation exists instead |
| 3 | Intelligence-extraction pipeline | **Half built** — server endpoint and table real and verified; the client write path is unreachable and has produced zero data |
| 4 | User style profiles | **Not built** — a three-valued stored preference, nothing learned or derived |
| 5 | Token-deduction concurrency | **Not built** — no balance, no deduction; the counter that exists is non-atomic and ships non-blocking |
| 6 | StoneDesk risk-detection defaults | **Built** — hardcoded 12 h / 24 h / 30-day thresholds and a fixed −20/−30/−15 health score; thresholds not user-configurable |
