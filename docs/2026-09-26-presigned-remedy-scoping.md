# Item 100, scoped onto the one design that is still open — the checkout-minted billing-portal token

**2026-09-26 (cc).** Item 100's first pass
(`docs/2026-09-15-item100-pre-signed-remedy-and-the-watchtower.md`, Fourth) asked
whether Lightning's pre-signed-penalty / watchtower pattern says anything about
SAIRN's billing surfaces, and answered it for the **B2B licence gate**: the
remedy (`license_keys.status` writer) does not exist, the watchtower
(reconciliation that does not trust a webhook) does not exist, and
`!!stripe_subscription_id` is read as "paid" at three sites. All three are
recorded there and none is built.

This pass takes the *other* half of that document's §4 — the **billing portal**,
the moment control is handed over — and scopes the specific design that is still
open: **a checkout-minted, narrowly-scoped, pre-authorised token** that would
replace the bare subscription id the portal endpoint accepts today.

**Nothing is built here and nothing about Stripe was contacted.** Every claim
below is a read of this repo, cited to a file.

---

## 1. What is actually open, in the endpoint's own words

`api/sairncash/portal.js` does not hide the gap; it states it:

> It is not a perfect gate -- possession of a subscription id still gets you a
> portal for that subscription, so a leaked `sub_...` is a real credential. It is
> materially better than accepting a customer id, and it matches what the client
> already holds. Tightening it further needs a server-side session, which
> SAIRNcash does not have; recorded here rather than left to be discovered.

So the open design question is exactly: **what does the caller present, if not a
`sub_...`?** The header's own answer — a server-side session — is the thing
SAIRNcash structurally does not have: it is a guest-checkout product with no
login, which is *why* the Billing Portal exists in the first place (the same
header: there is no stripe.com page a guest purchaser can log into).

A checkout-minted token is the shape that fits a product with no login. It is
also, precisely, a pre-signed remedy — which is what brings item 100 to bear.

### Where the `sub_...` lives today, and why "leaked" is not hypothetical

`sairncash.html` reads it out of `localStorage.sairncash_sub` and posts it
(`sairncash.html:745`). `api/sairncash/verify.js`'s header records what that
storage was worth before per-load re-verification landed: *"a forged
`localStorage.sairncash_sub` grant[ed] permanent free access."* That defect was
about **forging** the record; the portal exposure is the other direction —
**reading** it. Any XSS, any shared browser profile, any support session where a
customer pastes their record, hands over a working billing credential.

---

## 2. Why a checkout-minted token is a pre-signed remedy, and what that forces

Lightning's contribution, per the first pass, is not cryptographic. It is an
ordering rule: **you do not hand the counterparty an instrument until the thing
that undoes it already exists and does not depend on the counterparty.**

A checkout-minted portal token is an instrument handed over in advance:

| Lightning | The proposed token |
|---|---|
| Pre-signed penalty transaction | The token, minted at checkout, redeemable later |
| Held by the counterparty | Held by the customer's browser / their email |
| Broadcast when needed | Presented to `api/sairncash/portal.js` |
| **Watchtower** — someone who acts when you are not looking | **Missing.** Nothing today can invalidate a minted token, because there is nothing to invalidate |

So the ordering rule says three things must exist **before** the first token is
minted, and the third is the one most likely to be skipped:

1. **A revocation path.** A row the token resolves against, with an `active`
   flag something can set to false. Without it, "narrowly scoped" describes the
   token's *reach*, not its *lifetime* — and a credential with no lifetime is
   the `sub_...` problem with extra steps.
2. **A way to see it being used.** Not an alarm; a timestamp. §3 is the whole
   argument for why this, and not an automatic reaction, is the right primitive.
3. **A decision about reuse, made on purpose.** §3.

---

## 3. THE INTENT-BLINDNESS CAVEAT — this is the section that changes the design

A token that treats its **second** presentation as evidence of theft is
**intent-blind**: the mechanism cannot tell a thief from the customer, and the
honest cases are not edge cases. Concretely, each of these burns a single-use
token with nobody doing anything wrong:

- **Second device.** The customer completes checkout on a laptop and later opens
  the link on their phone. This is the single most ordinary thing a paying
  customer does.
- **Password-manager autofill and browser prefetch.** A manager that fills and
  submits, or a browser that speculatively fetches a link on hover or from the
  address bar, spends the use before a human has seen the page.
- **Mail-security prefetch.** Corporate mail scanners and link-rewriting
  services fetch URLs in a message to check them. If the token ever travels by
  email — and a receipt is the obvious place to put it — **the scanner clicks
  first and the customer gets a dead link.** This is not a theoretical failure
  mode; it is the standard reason one-time email links break in business inboxes.
- **Forwarding to whoever actually handles the money.** A subscriber forwards the
  receipt to their bookkeeper or partner. The person who needs the billing portal
  is frequently not the person who bought the thing.
- **Retry after a failure.** The page 500s, the customer reloads. A use was
  spent on a request that rendered nothing.

### The harm is asymmetric, and it points the opposite way to intuition

The failure a single-use token prevents: someone who obtained the token can view
invoices, change a card, and cancel.

The failure a single-use token *causes*: **the paying customer cannot cancel.**
There is no login, no second route, and `sairncash.html`'s own fallback before
the portal existed was an `alert()` naming a page that does not exist
(`portal.js` header). A subscription that keeps billing and offers no working
route to stop is the worse outcome — worse for the customer, and the specific
shape consumer-protection rules are written about.

**So the failure-safe direction here is to let the token be reused, and to make
reuse VISIBLE rather than FATAL.** That is the opposite of the reflex, and it is
the reflex this section exists to stop.

### The platform already solved this, in the one place it has shipped the pattern

`api/sen-portal.js` + `sql/sairnsenior_portal_links_schema.sql` are a live
instance of exactly this design — *"a unique, revocable, scoped-to-exactly-one-
client bearer token … there is no login step, no PIN, no session"* — for
SAIRNsenior's family/client portal. Its columns are the answer:

| Column | What it decides |
|---|---|
| `link_token` unique, 256-bit random | Not guessable; the only thing presented |
| `client_id`, resolved FROM the token | *"there isn't one to edit"* (`sql/sairnsenior_portal_links_schema.sql:20`) — scope is server-side, never a parameter |
| `active` + `revoked_at` | **The pre-signed remedy.** Revocation exists before it is needed |
| `last_accessed_at` | **Reuse is OBSERVED, not counted and not punished** |
| *(no use counter, no expiry)* | Intent-blindness handled by not pretending to read intent |

That is the whole pattern, and note what is **absent**: no use limit, no
auto-expiry, no lockout. Reuse is recorded so a human can look; the only
automatic behaviour is none. A revoked link *stays in the table* so staff can see
the history — the same deactivate-never-delete discipline as every
`*_employee_auth` table.

**A SAIRNcash billing token should be that table with a `subscription_id`
instead of a `client_id`, and the burden of proof is on any deviation from it.**
The platform does not need to design this pattern; it needs to not re-litigate
it worse.

### One thing to check before assuming reuse is even safe today

The **Stripe-returned** portal URL is a separate object from any token SAIRN
would mint, and whether *it* is single-use is a fact about Stripe that nothing in
this repo records. It may not matter: `sairncash.html:741-748` mints a **fresh**
portal session on every click and navigates straight to it, so the current design
never reuses a Stripe URL.

**That is worth stating as a property the current code has and a change could
lose:** minting on demand is intent-blind-*safe* by construction. A
checkout-minted token that is also single-use would be a regression on an axis
today's code gets right by accident of shape.

---

## 4. What a design would have to settle, in order

Nothing below is built. The order is the point — it is Lightning's ordering rule
applied to this endpoint.

1. **The table, with `active`, before the first token is minted.** Mirror
   `sen_portal_links`. A token minted before a revocation path exists cannot be
   taken back, and the migration to add one runs on live subscribers.
2. **Resolve the subscription id FROM the token, never from the request.** This
   is the property `portal.js` already gets right one level up (it reads the
   customer off the subscription rather than trusting a `cus_...`) and is the
   only reason a token beats a `sub_...` at all. A token that is presented
   *alongside* a subscription id buys nothing.
3. **Reuse: multi-use, with `last_accessed_at`.** §3. If anybody argues for
   single-use, the thing to price is not the leak it prevents but the cancel it
   blocks.
4. **Rate-limit the endpoint.** `api/sairncash/portal.js` has no rate limit and
   is unauthenticated; the platform already carries `api/_lib/anon-rate-limit.js`
   and `api/_lib/ai-rate-limit.js`, so the mechanism is routine. A token makes
   guessing impractical; it does not make *enumeration attempts* free to serve.
5. **A test file, which does not exist.** `api/sairncash/` carries exactly five:
   `verify.test.js`, `stripe-webhook.test.js`, `trial-renew.test.js`,
   `trial-renew-idempotency.test.js`, `trial-start.test.js`. There is **no
   `portal.test.js`** — so the endpoint whose whole security design is "do not
   trust the caller's identifier" has no arm asserting it, and a future edit that
   accepted `req.body.customerId` would be caught by nothing. (`trial-verify.js`
   has none either; noted, not in scope here.)

---

## 5. What this does NOT claim

- **Nothing was contacted.** No Stripe call was made. This cannot tell you
  whether any subscription is currently in a wrong state.
- **No live breach is asserted.** The `sub_...` exposure is a design limit the
  endpoint already documents, not an incident. Whether SAIRNcash's Stripe
  environment is configured at all is a runtime fact `stripeConfig.status()`
  answers per-request and this document does not.
- **The token is not recommended over the alternatives**, only scoped. "Keep
  accepting `sub_...` and add a rate limit" is a coherent position; so is "mint
  on demand only, never pre-mint", which is what the client does today. What §3
  rules out is a *single-use* token, and it rules it out on customer-harm
  grounds rather than security ones.
- **`api/agent/stripe-webhook.js` is still not audited**, same as the first
  pass. Different table, different lifecycle.
- **This does not close item 100.** The three B2B items in the first pass's §4 —
  the `license_keys.status` writer, the watchtower, and the three
  `!!stripe_subscription_id` reads — are all still open and none is touched here.
