# SAIRNcash billing flow — re-derived against the code and the live deployment, 2026-10-16 (Cody, b20)

> ## STATUS DECIDED BY MICHAEL, 2026-10-16: **CODE-COMPLETE, BLOCKED ON BUSINESS SETUP.**
>
> **NOT "incomplete".** The LLC is not yet situated. **All three remaining
> items are ON HOLD BY DECISION, NOT BY OVERSIGHT, and NO FURTHER STRIPE WORK
> IS TO BE DONE until Michael says go** — that includes reading the Vercel
> environment, testing the key, and the billing-portal token design.
>
> **WHY THE WORD MATTERS AND IS NOT A LABEL.** "Incomplete" points an engineer
> at the repo, and **the repo is finished** — twelve suites green, three of
> them mutation probes that plant defects and require refusal. A status that
> sends somebody to look for missing code costs a session every time it is
> read, and this row has been read at least three times across b19 and b20.
> **"Blocked on business setup" points at the thing that is actually blocking,
> and tells the next session to stop rather than start.**

**The standing status WAS "incomplete". THAT WAS WRONG IN ONE DIRECTION AND
RIGHT IN ANOTHER, and the two halves have different owners.**

| | verdict |
|---|---|
| **The CODE** | **COMPLETE and tested.** Twelve suites, every one green at this commit. Nothing is missing in the repo. |
| **The DEPLOYMENT** | **BLOCKED ON THE LLC**, and narrower than the record said: `STRIPE_SECRET_KEY` is **PRESENT in production**, measured live today. |
| **The one design decision** | **ON HOLD, Michael's** — the billing-portal token. Not to be pursued. |

**WHAT THE STANDING RECORD SAYS, and the exact words that have gone stale.**
`docs/open-work/sairncash.md` carries: *"Stripe not configured —
`api/sairncash/checkout.js` returns `{"error":"Stripe not configured"}`"*.
**That string no longer exists anywhere as a response.** `api/_lib/stripe-config.js`
replaced the five independent per-file conditions with one, and every endpoint
now answers the single generic `Payments are not configured on this server`.
So the row is stale on its evidence as well as on its scope.

---

## 1. The code half — measured, not reviewed

Exit codes read from `echo "EXIT=$?"` on its own line, never from a pipeline.

```
EXIT=0  node api/sairncash/portal.test.js                 19 passed, 0 failed
EXIT=0  node api/sairncash/verify.test.js                  22 passed, 0 failed
EXIT=0  node api/sairncash/trial-start.test.js             10 passed, 0 failed
EXIT=0  node api/sairncash/trial-renew.test.js              4 passed
EXIT=0  node api/sairncash/trial-renew-idempotency.test.js 11 passed, 0 failed
EXIT=0  node api/sairncash/stripe-webhook.test.js
EXIT=0  node tests/sairncash_entitlement_gate.js           19 passed, 0 failed
EXIT=0  node tests/sairncash_plan_label.js                 10 passed, 0 failed
EXIT=0  node tests/sairncash_safe_harbor.js                35 passed, 0 failed
EXIT=0  python tests/sairncash_entitlement_fault_probe.py   0 failure(s)
EXIT=0  python tests/sairncash_fault_probe.py               0 failure(s)
EXIT=0  python tests/sairncash_entitlement_gate_probe.py    ALL 12 ARMS PASS,
                                                            8 mutations refused
```

**The three Python files are the ones that make the twelve JS numbers worth
something** — they plant defects and require the suites to refuse them. A green
suite with no mutation arm is a suite nobody has asked a question of.

**The endpoint set is complete for a subscription lifecycle:** `checkout.js`
(create session), `stripe-webhook.js` (provision on event), `verify.js`
(confirm and mint), `portal.js` (manage), `trial-start.js` / `trial-verify.js` /
`trial-renew.js` (the trial path), `ai.js` (the gated feature). **Nothing in
that list is a stub**, and `portal.test.js` asserts the capability table
difference directly: portal needs `[STRIPE_SECRET_KEY]`, checkout needs
`[STRIPE_SECRET_KEY, STRIPE_PRICE_ID]`, *"and that difference is deliberate."*

---

## 2. The live half — one measurement, and it is the whole finding

**NON-MUTATING BY CONSTRUCTION. Nothing below could create a Stripe object, and
§3 is why that constraint shaped the probe rather than being a note on it.**

Via `tools/sairn_http.py` against `https://sairn.vercel.app`:

| request | answer |
|---|---|
| `OPTIONS /api/sairncash/checkout` | **204** |
| `GET /api/sairncash/checkout` | **405** |
| `GET /api/sairncash/portal` | **405** `{"error":"POST only"}` |
| `GET /api/sairncash/verify` | **405** |
| `GET /api/sairncash/stripe-webhook` | **405** `{"error":{"message":"Method not allowed — POST only"}}` |
| `GET /api/sairncash/trial-start` | **405** `{"error":{"message":"POST only"}}` |
| **`POST /api/sairncash/verify`, EMPTY BODY** | **400** `{"error":"Missing sessionId or subscriptionId"}` |

**THE LAST ROW IS THE MEASUREMENT.** `api/sairncash/verify.js` checks
configuration at `:45` and only then validates the payload at `:56`. A **400
"Missing sessionId or subscriptionId" proves the configuration check PASSED** —
it is not the 500 `Payments are not configured on this server`. `verify`'s
capability row is `['STRIPE_SECRET_KEY']`.

> **`STRIPE_SECRET_KEY` IS PRESENT IN PRODUCTION as of 2026-10-16.**

**AND THE EXACT MISTAKE THIS PLATFORM ALREADY PAID FOR IS AVAILABLE HERE IN
REVERSE, SO IT IS NAMED BEFORE IT IS MADE.** `api/_lib/stripe-config.js` exists
because `checkout`'s *"Stripe not configured"* — fired by a missing
`STRIPE_PRICE_ID` — was read as evidence about the KEY by four separate
readers. **`verify`'s 400 is evidence about the KEY and about nothing else.** It
says **nothing** about `STRIPE_PRICE_ID`, which only `checkout` requires.

**SO THE REMAINING GAP IS NARROWED, NOT CLOSED:**

* On **2026-09-17**, `POST /api/sairncash/checkout` returned **500 "Payments are
  not configured on this server"** (`docs/2026-09-17-sairncash-stripe-readiness.md`),
  so **at least one** of the pair was absent then.
* Today the **key is present**.
* `verify` and `portal` both need only the key, so **neither can see
  `STRIPE_PRICE_ID`**.
* **Therefore `STRIPE_PRICE_ID` is the live suspect — and it is NOT PROVEN.**
  Either variable could have changed between the two dates. Stated as a
  narrowing, not a conclusion.

**PRESENT IS NOT WORKING, and `stripe-config.js` says so in its own header:**
production's key on 2026-09-14 was set and was an **expired `sk_test_`** key,
and every call died at Stripe. **`ready: true` means the variables are present
and nothing more.** Today's 400 is a statement about presence. Nothing here
shows the key authenticates.

**AND THAT IS NOT CHECKABLE FROM OUTSIDE EITHER, which is worth knowing rather
than attempting.** A `POST /api/sairncash/verify` carrying a bogus
`subscriptionId` would reach `stripe.subscriptions.retrieve` — a read, not a
write — but `verify.js` catches every failure into one `500 "Could not verify
the subscription"` (`:204`). **An expired key and a non-existent subscription
land on the same response**, so the probe cannot separate them. It was not run:
an outward call for an ambiguous answer is a cost with no finding.

---

## 3. THE READINESS DOC'S OWN PROBE IS SAFE ONLY IF THE THING IT TESTS FOR IS STILL TRUE

**This is the methodology item, and it came out of declining to run a command.**

`docs/2026-09-17-sairncash-stripe-readiness.md` records its live check as
`POST https://sairn.vercel.app/api/sairncash/checkout {"email":"..."}` and it was
safe when it ran, because the configuration guard fired first and **no Stripe
object was created.**

**`checkout.js` validates NOTHING before calling Stripe.** `email` is optional
(`:49`, `(req.body && req.body.email) || undefined`) and the session is created
at `:60`. So the same command, run today:

* if `STRIPE_PRICE_ID` is still absent → 500, no side effect, **and the probe
  was safe**;
* if `STRIPE_PRICE_ID` has since been added → **a real Stripe Checkout Session
  is created on a live payments account**, and the probe was not safe.

> **A PROBE WHOSE SAFETY DEPENDS ON THE ANSWER IT IS TRYING TO OBTAIN CANNOT BE
> RE-RUN TO CHECK WHETHER THE ANSWER HAS CHANGED.** The one state in which it is
> safe is the state it is testing for.

That is why `verify` with an empty body was used instead: its refusal is a
**validation** refusal that sits after the config check and before any outward
call, so it discriminates the same variable **in both directions** with no side
effect either way. **A config probe should be aimed at the endpoint with the
narrowest capability row and a validation gate in front of its outward call** —
and `stripe-config.js`'s capability table is what makes that choice derivable
instead of lucky.

**ROUTED, NOT TAKEN:** the readiness doc's prescribed command should carry this
warning. Re-writing another session's dated document to add my caveat is not
mine to do; this section is the caveat and it cites that document by name.

---

## 4. So what is actually missing — three items, three owners

**ALL THREE ARE ON HOLD AS OF 2026-10-16. The "next step" column records what
the step WOULD be when the hold lifts; it is not a queue to work.**

| # | what | owner | next step WHEN THE HOLD LIFTS |
|---|---|---|---|
| 1 | **`STRIPE_PRICE_ID` presence in the Vercel project is UNKNOWN** and cannot be determined from outside without creating a Stripe object | **Michael** | Read the Vercel env list for the project. One look settles it; no probe can. **HELD.** |
| 2 | **Whether the present `STRIPE_SECRET_KEY` actually authenticates.** Present ≠ working — it was an expired `sk_test_` once already | **Michael** | A single Stripe dashboard look, or one authenticated API call from outside this platform. **HELD.** |
| 3 | **The billing-portal token design.** `docs/2026-09-26-presigned-remedy-scoping.md`, scoped by cc, nothing built | **Michael** | Decide: mint a token, or keep `sub_...` plus a rate limit. **A single-use token is ruled OUT on customer-harm grounds** — that scoping already ran. **HELD.** |

**NONE OF THE THREE IS A CODE DEFECT**, and that is the change from the standing
record. The code half of this feature is finished and has mutation-tested
coverage; the feature is blocked on two environment facts and one product
decision.

---

## 5. What this does NOT claim

* **No POST to `checkout` or `portal` was sent.** Creating a Stripe Checkout
  Session is an outward-facing side effect on a live payments account and was
  not authorised.
* **No Stripe dashboard was opened, no Vercel environment was read.** The env
  question is answered by looking, and looking is Michael's.
* **`STRIPE_PRICE_ID` is not asserted absent.** §2 narrows the suspect; the
  readiness doc's 2026-09-17 result is the only direct evidence either variable
  was ever missing, and it does not say which.
* **The AI-assistant outage row is untouched.** It is held deliberately by a
  2026-09-05 decision and this pass makes no new claim about it.
* **No `api/`, `sql/` or `tools/` file was edited.** The twelve suites and
  `tools/sairn_http.py` were RUN.
* **The standing open-work rows are not re-worded.** Re-writing another
  session's row to carry my verdict is the edit this platform has least
  tolerance for; this document is the correction and the rows cite the apps, so
  a reader of either arrives here.
