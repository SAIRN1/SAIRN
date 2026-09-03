# Patent verification — six items, checked against the real code

**For:** patent attorney review.
**Verified as of commit `2bc6fb0` (2026-09-02).** A verification report with
 no tree attached reads as timeless and is not: item 4 below went from
 "not built" to built roughly an hour after it was written. **Re-check this
 line against `git log` before relying on any item.** Every claim names its
 file so that re-check is cheap.

**Item 2 has since been corrected to BUILT** (2026-09-02, later the same day),
by the same mechanism §4 used and for the same reason. **Item 4's caveat is now
the document's rule, not its exception:** two of six items changed status
within hours of being verified. Re-check both against the tree.

> **NO MEASURED PROMPT SIZE EXISTS YET, and no number in this document should
> be read as one.** Every token figure here and in the code is `chars ÷ 4`.
> `api/claude.js` now *reads* Anthropic's `usage` block and
> `sql/sairn_ai_usage_columns_2026-09-02.sql` adds the two columns that would
> store it — but **that migration has not been confirmed as run in Supabase**,
> and 99 `/api/claude` calls in the last 24 hours carry no size in any log
> this session could reach. The instrumentation is in place; the measurement
> is not. See item 5, which is the same gap seen from the metering side.

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

> **CORRECTED 2026-09-02, later the same day — this item is now BUILT.** It
> read "Not built" and that was accurate when written. It was then built
> deliberately, as `[0039]`, rather than discovered. The original finding is
> kept below the correction rather than deleted, for the same reason §4's is:
> *when* a thing was built is itself a fact counsel may need, and the gap this
> closed is the clearest statement of what the construct is for.

### Built, as of `sdBuildInferenceContext()` in `stonedesk.html`

There is now a named construct that assembles inference context as a
**structured object**, and the string that goes over the wire is one field of
it (`.system`) rather than the whole of it. Verified against the code:

- **Named fields.** `sdCtxProfileFields()` returns business-profile data as a
  list of `{key, label, value, pos, drop, tokens}` — `company_name`, `ein`,
  `city`, `state`, `headcount`, `revenue_range`, `owner_name`, `ai_notes` —
  replacing eight chained `+` operators. Absent values yield absent fields.
- **Scored, ranked selection.** `sdCtxScoreMemories()` scores every candidate
  memory on two axes and ranks them: **relevance** to the message actually
  being answered (term overlap, normalised by the square root of the query's
  term count) at weight **0.65**, and **recency** (exponential decay,
  **30-day half-life**) at weight **0.35**. Selection is best-first, not
  `slice(0, 10)`. **With no query the ranking degenerates to pure recency**,
  which is exactly the previous order — asserted in the test suite so the old
  behaviour is a floor rather than something that changed silently.
- **A token budget.** `SD_CONTEXT_BUDGET_TOKENS = 3000` bounds the assembled
  system prompt, which was previously unbounded. The bound is measured off the
  rendered string and re-measured after every drop, not summed from per-part
  estimates.
- **A defined merge/drop policy.** Inferred is cut before declared and
  machine-written before human-written: memories lowest-scored first, then
  observed style directives, then profile fields in a declared rank order
  (shop notes → revenue → EIN → owner → headcount → city/state). The base
  prompt, the shop's name and the declared style note are never droppable;
  when even that core will not fit, the object reports `over: true` rather
  than sending an oversized request quietly.
- **Withholding is disclosed.** When memories are held back — by the budget or
  by the ten-memory cap — the prompt says so and tells the model not to treat
  the list as complete. The previous `slice(0, 10)` withheld memories 11–20
  from a twenty-memory shop and said nothing.
- **Tested:** `tests/composite_context.js`, **63 assertions**, extracted from
  the real `stonedesk.html` rather than restated. **Mutation-tested against
  seven separate mutations** (drop the date guard, reorder the drop policy,
  remove the disclosure, remove the future-clamp, restore the hardcoded city
  default, make the shop name droppable, zero the relevance weight) — **each
  one fails at least one assertion.**

**Two fabricated facts were removed in the course of this, and counsel should
know they existed**, because they were in the prompt of every AI call the app
made:

- `'City: ' + (p.city || 'Westlake') + ', Ohio'` — **both halves hardcoded**.
  A shop that had not filled in a city was described to the model as being in
  Westlake; a shop that *had* filled one in was still stamped Ohio. The model
  was then asked for advice on pricing, labour and permitting for the wrong
  state.
- `'Headcount: ' + (p.headcount || 1)` — asserted a one-person shop whenever
  headcount was unset.

Both are now absent-when-unknown.

**What this does not do**, so counsel is not left to infer it: the construct is
StoneDesk's. Other apps still have their own separate prompt builders, and
nothing here is shared across them yet. **The token figures are estimates**
(chars ÷ 4) and are labelled as such in the code — see item 5 and the note
below on why no measured figure exists yet.

### Original finding, accurate until `[0039]`

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

> **CORRECTED 2026-09-02, later the same day.** This item read "Not built" and
> was accurate when written. It stopped being accurate roughly an hour later,
> when commit **`e634c8d`** landed a real per-user style profile. The original
> finding is kept below the correction rather than deleted, because *when* a
> thing was built is itself a fact counsel may need. **This is exactly why this
> document now carries a "verified as of" commit at the top — a verification
> report with no tree attached reads as timeless and is not.**

### Built, as of `e634c8d` (2026-09-02)

Verified against the code, not the commit message:

- **Observed, not asked for.** `api/_lib/style-profile.js` derives a profile
  from what the user actually writes. `analyse()` returns per-message counts
  across real dimensions: word and sentence counts, questions, imperative
  openings (a 30-verb list), bullets, numbered lists, markdown, caps emphasis,
  **hedges** (`maybe|perhaps|i think|sort of|…`), **courtesies**
  (`please|thanks|sorry|could you|…`), abbreviations, a length bucket
  (`terse` / `short` / `medium` / long), and up to **12** frequent non-stopword
  terms.
- **Gated on evidence.** `MIN_SAMPLES = 5` — nothing is applied until at least
  five messages have been seen.
- **Persisted server-side.** `sql/sairn_style_profiles_schema.sql` creates
  `public.sairn_style_profiles`, **unique on `(license_hash, employee_id)`**,
  registered as a resource in `api/_resources/stonedesk.js` with a read/write
  branch in `api/sd-data.js`.
- **Per-user, with a stated limit.** `employee_id` comes from the session
  token, and the schema's own header records that a caller can only read or
  write **their own** profile. It also records the boundary honestly: because
  `license_hash` is per-app-licence, the same human working under two licences
  has two profiles.
- **Applied to the prompt.** `stonedesk.html:25648` calls
  `renderStyleDirectives(_sdStyleProfile, style)` and folds the result into the
  system prompt, alongside — not replacing — the three-valued preference
  described below.
- **Client and server implement the same analysis and that duplication is
  tested rather than trusted.** `api/_lib/style-profile.test.js` — **28
  assertions pass**; `tests/style_profile_parity.js` — **19 assertions pass,
  client and server agree.**

**What this does not do**, so counsel is not left to infer it: it does not
generate text in the user's voice, and it does not cross licences or apps. It
observes how a user writes and conditions the assistant's response style.

### Original finding, accurate until `e634c8d`

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
| 2 | Composite Inference Context | **Built as of `[0039]` (2026-09-02)** — `sdBuildInferenceContext()`: named profile fields, memories scored on relevance (0.65) + recency (0.35, 30-day half-life) instead of `slice(0,10)`, a 3,000-token bound on the assembled system prompt, and a declared drop order with disclosure. 63 assertions, 7 mutations. **Was "not built" earlier the same day** — see the correction in §2. StoneDesk only; other apps still concatenate |
| 3 | Intelligence-extraction pipeline | **Half built** — server endpoint and table real and verified; the client write path is unreachable and has produced zero data |
| 4 | User style profiles | **Built as of `e634c8d` (2026-09-02)** — observed from the user's own messages, gated at 5 samples, persisted per `(license_hash, employee_id)`, applied to the prompt, client/server parity tested. **Was "not built" earlier the same day** — see the correction in §4 |
| 5 | Token-deduction concurrency | **Not built** — no balance, no deduction; the counter that exists is non-atomic and ships non-blocking |
| 6 | StoneDesk risk-detection defaults | **Built** — hardcoded 12 h / 24 h / 30-day thresholds and a fixed −20/−30/−15 health score; thresholds not user-configurable |
