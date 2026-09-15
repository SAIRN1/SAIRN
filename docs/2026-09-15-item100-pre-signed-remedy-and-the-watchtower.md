# Item 100 — the pre-signed remedy: can anything here ever revoke what it granted?

**2026-09-15 (Fourth).** Asked: does Lightning Network's pre-signed-penalty /
watchtower pattern have anything to say about SAIRN's billing surfaces — and in
particular the still-open Stripe billing-portal design?

**Answer: yes, and the platform already contains both the right pattern and the
wrong one. The one consumer app gets it right and says so in its own header. The
thirteen B2B verticals are on a mirror that nothing in this repo can write.**

Tool: `tools/entitlement_freshness_check.py`. Control:
`tests/entitlement_freshness_control.py` (10 arms, both directions, green).

---

## 1. What the Lightning pattern actually contributes

A payment channel hands a counterparty the ability to act — they hold a signed
state that lets them close the channel — while you have no way to force them to
behave. Three moves solve it, and only the third is the interesting one:

| Move | What it is | Why it is not enough alone |
|---|---|---|
| Sign the new state | Both parties agree on the balance | Says nothing about the old states they still hold |
| **Pre-sign the PENALTY** | Before handing over control, the remedy for cheating already exists, fully signed | Useless if nobody is watching when the cheat happens |
| **The WATCHTOWER** | A third party watches the chain and can broadcast the penalty **without the cheater's cooperation** | — |

**The load-bearing property is the last clause.** The remedy must not depend on
the party it is a remedy against, and it must not depend on you being awake. A
remedy that requires the counterparty to notify you is not a remedy; it is a
request.

**A SaaS paywall is the same shape with the names changed.** Stripe holds the
truth about whether somebody is still paying. The app hands out access. If the
only path from *"they stopped paying"* back to *"access removed"* runs through a
webhook that Stripe has to deliver — or through a human noticing — **then the
remedy depends on the counterparty and there is no watchtower.**

---

## 2. SAIRNcash gets this right, deliberately, and wrote down why

`api/sairncash/stripe-webhook.js` states its own position in its header, and it
is exactly the pattern:

> *"`api/sairncash/verify.js` already re-checks the real Stripe subscription on
> every app load, and that remains THE authority for whether someone may use the
> product. This webhook writes an ADVISORY MIRROR, never a grant … It cannot
> turn a non-subscriber into a subscriber. Nothing reads this node to decide
> access."*

Mapped onto the three moves:

- **The pre-signed remedy** is `verify.js` — the revocation path exists, is
  wired, and runs on every app load, before anyone has cancelled anything.
- **The watchtower** is that same re-check, and critically **it does not depend
  on the webhook arriving.** A dropped event costs promptness, not correctness.
- **The webhook is the optimisation, not the mechanism.** Its own header lists
  what it genuinely adds over polling: promptness, dunning visibility, an audit
  trail. Not entitlement.

That is the correct architecture and it is one file. It is also the in-house
precedent for everything in §3, which makes the gap there a *consistency*
problem rather than a research problem.

---

## 3. The B2B verticals are on a mirror nothing can write

Every B2B SAIRN app gates on `api/_lib/license.js`:

```js
out.active = String(row.status || '').trim().toLowerCase() === 'active';
out.stripe_subscription_id = row.stripe_subscription_id || null;
```

`row` is a `license_keys` row in Supabase. **Measured, not assumed** — the
figures below are `tools/entitlement_freshness_check.py`'s output:

| | count |
|---|---|
| In-repo **code** that reads `license_keys` | **34 files** |
| In-repo **code** that can WRITE it (POST/PATCH) | **0** |
| Hand-run **SQL** that writes it | 16 files, all seeds |

**There is no in-repo path from a lapsed subscription to an inactive licence.**
`status` is set by a human running a seed, once, and is never revisited by
anything. No cron does it — the four in `vercel.json` are
`sairndental/send-reminder`, `alf-alerts`, `audit-checkpoint` and
`cron-watchdog`, and none touches billing. The revocation remedy does not exist
yet, which is the thing Lightning insists you build *before* handing over
control rather than after.

### 3.1 And the sharper half: presence is not state

Three sites decide the paid tier like this:

```js
const isPaid = !!lic.stripe_subscription_id;
```

`api/_lib/sd-store.js:60`, `api/sd-data.js:533`, `api/sd-render.js:137`.

**A cancelled subscription keeps its id forever.** `sub_...` is the receipt that
a subscription once existed; it is never evidence that it exists now. This one
is worse than the stale-mirror problem because **even a perfectly reconciled
mirror would not fix it** — the expression never asks the mirror anything. It
asks whether a string is non-empty.

The columns are real: `db/schema_snapshot.json`, captured live 2026-09-02, lists
`license_keys` as `id, key, app_id, shop_name, customer_email,
stripe_customer_id, stripe_subscription_id, plan, status, created_at,
updated_at`.

### 3.2 Why this is LATENT and not a live breach — stated plainly

**B2B Stripe is not configured.** `api/sd-data.js` records it at the gate:
*"Stripe is not configured, so nobody is on a paid plan to expire."* No licence
carries a subscription id today, so there is no cancelled subscription leaking
access right now, and **nothing in this document says a customer currently has
access they should not.**

What it says is narrower and is the whole point of item 100: **the shape is
already in the code, and it is cheap now and expensive later.** The day the
first `stripe_subscription_id` is written into a row, that row is permanently
paid from the application's point of view, and the fix at that moment is a
migration plus three call sites plus a reconciliation job on a live billing
system with real customers on it. The pre-signed-remedy discipline exists
precisely because the remedy is cheap to build before you need it and expensive
to build during.

The neighbouring trial gate is a worked example of how long this shape can sit
unnoticed: `trial_ends_at` **is not a column**, so the 402 `TRIAL_EXPIRED` next
to `isPaid` has never once been reached, and the comment above it says a
sentence describing that as an edge case *"is why nobody looked for four
months."*

---

## 4. What the billing-portal design has to settle before it ships

The portal (`api/sairncash/portal.js`) is the moment control is handed over: a
customer who holds a portal link can cancel, downgrade or change their card
without the app being involved at all. That is the hand-over the pre-signed
remedy is *for*. Three things must exist **before** it is pointed at a B2B
licence, in this order:

1. **The revocation path, written and tested, before it is needed.** Something
   in `api/` that can set `license_keys.status`. Today nothing can. This is the
   pre-signed penalty and it is the part that must not wait for an incident.
2. **A watchtower that does not trust the webhook.** A scheduled reconciliation
   that reads the subscription from Stripe by id and writes the licence to
   match. `vercel.json` already runs four crons, so the mechanism is routine;
   what is missing is the job. SAIRNcash achieves the same property differently
   — per-load re-verification — and either is fine. Depending on webhook
   delivery is not.
3. **Replace `!!stripe_subscription_id` with a state read at all three sites.**
   Otherwise 1 and 2 are both correct and the gate still never revokes.

**Recorded and not built here.** Each of the three is a real change to a live
paywall; §3.2 is the reason there is no urgency, and the reason to write it down
now is that the cost of doing it later is the whole argument. Nothing about the
portal's own security design is criticised here — its header already makes the
right call about not trusting a client-supplied customer id, and says out loud
where it stops.

---

## 5. What this does NOT claim

- **Nothing was contacted.** The tool reads this repo. It has never spoken to
  Stripe and cannot tell you whether any licence is currently wrong — only
  whether a mechanism exists that could ever make it right.
- **A writer existing would not prove the writer is correct**, or that it ever
  runs. Presence of a mechanism is the floor being measured, not its quality.
- **SQL seeds are deliberately not counted as writers.** A hand-run migration is
  a human remembering, which is exactly what a watchtower replaces. They are
  printed so a reader can see the field is set *somewhere*.
- **`api/agent/stripe-webhook.js` was not audited here.** It writes
  `sairn_agents`, a different table with a different lifecycle, and whether
  anything grants from it is a separate question this pass did not ask.
