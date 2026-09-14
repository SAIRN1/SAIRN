# Item 40 — can external input reach a Tier A resource without its verification path?

**2026-09-14 (Hank).** A bypass-risk audit, not a new universal gate.

**One finding, and it is on billing.** It is **not exploitable today**, and the
reason is an expired Stripe test key rather than anything the code does — see
§1. The rest of this is the tool, its limits, and what it is not.

---

## 1. THE FINDING: `api/sairncash/portal.js` is unauthenticated

**A POST with a valid `sub_…` id returns a working Stripe Billing Portal URL for
that subscriber** — card on file, invoice history, and the power to cancel. The
endpoint requires no licence key, no session, and no proof whatsoever that the
caller is that customer.

### ⚠️ Second correction: the author already knew, and I said they did not

**I wrote that "the same argument applies one level up and was not applied."
That is wrong, and it is the second thing I got wrong about this finding.** The
file's own header says it, in terms:

> *"It is not a perfect gate — possession of a subscription id still gets you a
> portal for that subscription, so a leaked `sub_…` is a real credential. It is
> materially better than accepting a customer id, and it matches what the client
> already holds. Tightening it further needs a server-side session, which
> SAIRNcash does not have; **recorded here rather than left to be discovered**."*

So this is **a consciously accepted risk with a stated reason**, not an
oversight. I read the file, quoted the paragraph above it, and still
characterised it as a gap. That is exactly the failure mode of reviewing a diff
without reading what the author already wrote down.

### What is actually left, once the accepted risk is subtracted

1. **It was recorded in a file header and nowhere else.** *"Recorded here rather
   than left to be discovered"* is true of the file and false of the platform:
   it never reached `docs/SAIRN-OPEN-WORK-INDEX.md` or the SOUP register, so it
   was invisible to anyone not reading that one file — **which is the same
   information-leakage shape as item 94, one level up.** An accepted risk that
   only one file knows about is indistinguishable from an unnoticed one.
2. **The bound was never checked.** The header reasons about entropy and client
   storage; nobody established what actually stops exploitation today, which
   turns out to be an expired key rather than anything argued.
3. **The expired `sk_test_` key in a production environment variable**, which is
   new and is not in anyone's notes.

The underlying property stands and is worth stating plainly for the index, since
the header's phrasing is softer than the consequence: **a leaked `sub_…` id is
full access to that customer's billing** — card on file, invoice history, the
power to cancel — and Stripe puts those ids in dashboards, webhook payloads,
emails and CSV exports.

### Reachability — and a correction to my own first claim

```
POST /api/sairncash/portal  {"subscriptionId":"sub_…does_not_exist…"}
  -> 500 {"error":"Could not open the billing portal"}     <- the CATCH branch
```

The `if (!stripeKey)` guard **did not fire**, so `STRIPE_SECRET_KEY` is set.

**I reported from that alone that the finding was live. It is not, and the
correction is mine.** The response body is identical for a bad subscription id
and a bad key, because the handler swallows both — so the probe could not
distinguish them and I read one as the other. The production log settled it:

```
SAIRNcash portal error: Expired API Key provided: sk_test_…
```

**A present but EXPIRED TEST key.** Every Stripe call dies before reaching a
customer, so **the bypass is not exploitable today.**

**What that does and does not change.** The endpoint is still unauthenticated by
design, and that is the defect. What bounds it is an expired key in a production
environment variable — **an accident of deployment, not a control** — and the
day a working key is installed the bound disappears with nothing to announce it.
That is the identical re-read-trigger failure described below.

**And a second finding falls out of the log line: a `sk_test_` key is sitting in
a production environment variable.** That is its own misconfiguration,
independent of this endpoint.

### And that contradicts the SOUP register, which said the blast radius was zero

`docs/SOUP-REGISTER.md` recorded `STRIPE_SECRET_KEY` as unconfigured, with an
explicit instruction: *"Re-read this entry at that moment."* **That moment
passed unnoticed**, because the only visible signal — `checkout.js` answering
`{"error":"Stripe not configured"}` — **stayed the same for a different
reason**: its guard is `if (!stripeKey || !priceId)` and what is missing is
`STRIPE_PRICE_ID`.

**Two endpoints, one env var, two different answers, and only the narrower guard
tells the truth.** A status message is a claim about the guard that produced it,
not about the environment. The register is corrected.

### What bounds it today, stated honestly

A `sub_…` id is held in the customer's own `localStorage` and sent from their
own browser, so it is not public. Exploitation needs an id obtained some other
way — device access, a support screenshot, an export, an intercepted request.
**That is a real bound and it is not an authorization control.**

### Not fixed here, and why

The fix is a design decision: what should prove that a caller owns a
subscription? An emailed magic link, the SAIRNcash licence key, a signed token
minted at checkout — they differ in cost and in what they do to a real customer
flow. **Disabling the endpoint breaks the only working route a customer has to
cancel**, which is the problem it was built to solve. Left for Michael.

---

## 2. The tool: `tools/tier_a_bypass_check.py`

Per handler: does it name a Tier A resource **in code**, and does it contain
both an identity check and a refusal.

Three states, never two — **`COULD NOT TELL` is the interesting column**, where
a file checks an identity and never refuses, or refuses on something that is not
an identity.

Tier A names are parsed out of `docs/CRITICALITY-TIERS.md` so the tool cannot
invent its own opinion about what is critical, and it **refuses** if that
document is missing or parses to zero — an audit that treats nothing as Tier A
reports a clean platform.

`tests/run_tier_a_bypass_probe.py`, 12 arms.

### Its first run was 0% precision, and that is recorded rather than quietly fixed

Matching raw source, it produced exactly two findings and **both were prose**:
`api/greeting.js` on the word *quotes* inside `'slabs, quotes and jobs'`, and
`api/sairncash/portal.js` on *invoices* in a header comment. PR §1.2 —
*"grep cannot tell code from text that describes code"* — already written down,
and several Tier A resources here are ordinary English words, so this is the
norm and not an edge case.

Comments are now stripped through `tools/jscomments.py`: **16 candidate files
→ 7 real, 9 dropped as prose-only**, and the dropped list is printed rather
than vanishing.

**The finding in §1 did not come from the tool.** The tool put the file in front
of me for the wrong reason and I read it. That is worth saying plainly: it is a
pointer that worked by accident, not a detector that fired.

### The limit it did NOT fix

`api/greeting.js` still reads `COULD NOT TELL` on *quotes*, because that match
is in a **string literal**, not a comment. Filtering string literals would be
wrong — a PostgREST path *is* a string literal — so the false positive stays,
named here so a later reader does not mistake it for a regression.

---

## 3. What this audit does NOT establish

- **`GATED` is not a clearance.** The tool cannot tell whether the refusal runs
  *before* the write. That is the deferred-refusal shape
  `api/sd-sub-data-auth-ordering.test.js` exists for — the gate was there and it
  ran too late.
- **A name is not a write**, and a handler that writes a Tier A resource through
  a helper this cannot see is **missed entirely**. Seven of the nine prose-only
  drops were `*-auth.js` files that genuinely do gate and reference their
  resources through `api/_resources/` — so the tool's real coverage is narrower
  than 7 of 67.
- **Only HTTP handlers under `api/` were examined.** Anything reaching a Tier A
  resource by another route — a cron, a migration, a support script, the browser
  writing to `localStorage` — is outside what was looked at.
- **One finding is not a clean platform.** This is a read-list, not a number to
  drive to zero.
