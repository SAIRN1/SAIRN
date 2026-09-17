# SAIRNcash Stripe: re-verified 2026-09-17, still NOT live — and the billing flow was not built

**Asked for:** close the remaining SAIRNcash billing flow gap, *"verify the Stripe
test-mode account is actually active before building against it — flag if not."*

**Answer: it is not active. Flagged, and nothing was built against it.**

---

## What was measured, live, on 2026-09-17

Against the deployed endpoints, not inferred from `sql/` or from the open-work
index. The index's Stripe rows are dated **2026-09-05** and a status claim is
only true as of the read behind it, so they were re-derived rather than quoted.

| Endpoint | Result | What that means |
|---|---|---|
| `POST /api/sairncash/checkout` | **500** `Payments are not configured on this server` | The guard in `api/_lib/stripe-config.js` fired. At least one of `STRIPE_SECRET_KEY` / `STRIPE_PRICE_ID` is **absent**. |
| `POST /api/sairncash/verify` `{subscriptionId}` | **500** `Could not verify the subscription` | Not the guard — this is the **catch block**. The call reached Stripe and Stripe rejected it. |
| `POST /api/sairncash/verify` `{sessionId}` | **500** same | Same, by the other identifier, so it is not one code path. |
| `POST /api/sairncash/trial-start` | **200**, real token, `expiresAt 2026-10-17` | The non-Stripe half **works**. |
| `POST /api/sairncash/trial-verify` | **200** `{"valid": false}` on a bogus token | Works, and refuses correctly. |

**The two 500s are different failures and the distinction is the finding.**
`checkout` never reaches Stripe — its variables are missing. `verify` *does*
reach Stripe and dies there, which is the shape `api/_lib/stripe-config.js`
already warns about in its own words: *"PRESENT IS NOT WORKING… Production's
`STRIPE_SECRET_KEY` on 2026-09-14 was set, and was an EXPIRED `sk_test_` key."*
Twelve days on, that is still what the endpoint behaves like.

**So there is no test-mode account to build against.** Not a missing variable
that could be filled in, and not a code defect: a key that Stripe itself
refuses, plus a price id that was never set.

---

## Why nothing was built

`docs/SAIRN-OPEN-WORK-INDEX.md` carries a decision, **2026-09-05, Michael's**,
in terms that leave no room to read around them:

> **DO NOT TREAT THIS AS AN OPEN BUG — DECIDED 2026-09-05.** Stripe is not set
> up under the new LLC because **that entity is still being formed.** The key
> will start working when the LLC and Stripe are both ready, and not before.
> **Nobody should spend time diagnosing it, and nothing here should be 'fixed'
> to route around it.**

Building a billing flow against an integration that cannot be exercised would
produce code whose first real run is its first test, on the path that takes
money. The verification was the deliverable here, and it came back negative.

**This is not "blocked on a small thing."** It is blocked on the LLC, which is
not a technical dependency.

---

## What is NOT blocked, if the intent was to move SAIRNcash forward

Stated so the flag is useful rather than just a refusal. Each of these is
reachable today and none of them touches Stripe:

* **The entitlement gate has no suite.** The open-work row for the 2026-09-15
  Gate 4 work says so in its own next-action column — the endpoints got a fault
  probe, the app file did not.
* **A trial cannot be cancelled or removed through any endpoint.**
  `sql/sairncash_verification_trial_cleanup.sql` names this as a structural gap
  and explains why it was flagged rather than fixed: a trial lifecycle is a
  product decision (does a cancelled trial disappear, or stay recorded as
  cancelled?), and it is not a like-for-like port of the `set_active` work done
  on StoneDesk and SAIRNcode. **That decision is still unmade.**
* **`tests/sairncash_fault_probe.py` is credited to no app** in
  `docs/MASTER-PLAN.md`, so SAIRNcash's `fault` column reads 0 while a real
  probe exists. The row already records this as correct-by-the-rule rather than
  a gap in the probe.

None was started: each is a different piece of work from the one claimed, and
the claim held here was for the billing flow.

---

## ⚠ Debris I created, disclosed with its identifiers

Probing `trial-start` against production **created a real trial**, because that
endpoint is not read-only and the request I sent was shaped to succeed:

```
email       probe@example.test
customerId  4026f5a7-3a6a-485a-9acb-da479281d4e3
expiresAt   2026-10-17T13:28:28.774Z
```

Confirmed real by `trial-verify`, which answered `{"valid": true, "daysLeft": 30}`
and issued a Firebase token.

**The mistake was not probing production — it was not reading the verb first.**
Whether Stripe is configured is answered entirely by `checkout` and `verify`,
both read-only. `trial-start` was probed to find out what still worked without
Stripe, and the malformed request I sent *before* it had already answered that
(`400 Valid email required` proves the endpoint is up and validating).

No endpoint can delete a trial, so cleanup is SQL only. The delete is appended
to `sql/sairncash_verification_trial_cleanup.sql` **by exact email**, not folded
into that file's `%@sairncash-verification.example` pattern — `probe@example.test`
does not match it, and a reader who ran only the pattern would reasonably
believe the table was clean.

---

## What would change this verdict

One command, and it is Michael's to run when the LLC is ready:

```
POST https://sairn.vercel.app/api/sairncash/checkout   {"email":"..."}
```

* `500 Payments are not configured on this server` → still not set up.
* `500 Could not verify the subscription` from `/verify` → key present, Stripe
  refusing it. **Present is not working.**
* A `200` with a Checkout Session URL → test mode is live and the billing flow
  can be built against it.

Do not take a green env-var check as the answer. `api/_lib/stripe-config.js`
returns `ready: true` when the **variables are present** and says in its own
header that it cannot know whether they work — that needs a real API call, and
the call above is it.
