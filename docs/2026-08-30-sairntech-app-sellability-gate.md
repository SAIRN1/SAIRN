# The app sellability gate — what must pass before an app appears on the catalog

**Written 2026-08-30 (CC).** A catalog card is an external claim about an app,
repeated once per app, and `sairn-decision-gate` already fires before *"claiming
production / complete / live to anyone outside the team."* This is that gate,
made concrete, so each app is checked against a fixed standard rather than a
fresh judgment call.

**Run per app. Every check is pass/fail with named evidence — not an impression.
Any FAIL means the app is not listed, or is listed only under the disclosure
route in §3.**

**Worked example throughout: SAIRNlaw**, which fails on a check that nothing
about its polish or completeness would reveal.

---

## Why a checklist rather than a judgment call

SAIRNlaw's own approved-external-claim document has been **rewritten at five
consecutive gates**, each time because the *specific* half of the claim — which
jurisdictions, how many rules — had gone stale while the *invariant* half stayed
true. That file's own conclusion is the reason this checklist exists:

> "this document is the point-in-time claim a human makes. The app is the live
> one. When they disagree, the app is right and this file is stale."

**A catalog card is a point-in-time claim published to strangers and left up.**
It has every failure mode that document has, with none of the internal readership
that kept catching it. So the gate cannot be "does this look ready" — it has to
be a list of things that are checkable now and re-checkable later.

---

## The eight checks

### Check 1 — The app exists on `main` and serves at its route

**Fail if:** the file is not in `git ls-files` on `main`, or the live route does
not return the app.

**Evidence required:** the `git ls-files` line, and a real `curl` of the
production route showing a 200 and the app's own content.

**This is not theoretical.** `SAIRNmechanical` was listed in Guardian's App File
Map for months as a live app. The file has **never been on `main`** — it exists
only on an unmerged branch, and `sairn.vercel.app/sairnmechanical` returns
**404**. It was found by curling every app route during an audit, because
*nothing had ever checked that the mapped filenames exist.* A catalog would have
published that as a product.

**SAIRNfreedom fails this outright** — researched, nothing built.

### Check 2 — No pre-launch blocker is open against it

**Fail if:** the app has any recorded blocker whose stated justification is
"internal only," "no real customer yet," or equivalent.

**This is the SAIRNlaw check, and it is the whole reason for this document.**

SAIRNlaw's claim document carries a **pre-launch blocker**:
`law_deadline_rules` and `law_holidays` have **no authenticated write path** —
`api/legal-deadlines.js` `add_rule` and `add_holidays` accept a bearer licence
key alone. A session *is* resolved but used only for the `verified_by`
attribution, never enforced, so an unauthenticated write succeeds and stores
`verified_by: null`. Proven live with a payload built to fail validation:
`{"action":"add_rule","rule":{}}` returns **400 INVALID_RULE, not 401**.

Anything holding the licence key can overwrite any of the 119 primary-source
rules the entire product claim rests on, and the provenance column will read
null.

**The blocker's own deferral reasoning is what makes it a listing gate:**

> "Do not treat 'internal licences only' as a durable state. It is true on
> 2026-08-29 and is the only reason this is deferred. The first real SAIRNlaw
> prospect makes it false, and nothing in the codebase will announce that."

**A catalog listing IS the first real prospect.** Publishing the card is the
event that invalidates the only justification for leaving the hole open. That is
a self-inflicted problem, and it is invisible from the app's UI, its test suite,
and its polish.

**Generalised rule:** *any* deferral justified by "no external users yet" is
automatically triggered by listing. Search the app's docs for that reasoning
before listing it, not after.

### Check 3 — An approved claim sentence exists, is dated, and matches the app today

**Fail if:** there is no approved external claim, or it was written before the
last material change to coverage.

**Evidence:** the claim document, its date, and a check of its *specific* half
against live data — not against the last handoff.

SAIRNlaw's claim went **four phases stale** once, describing five jurisdictions
and 64 rules when the app had eleven and 119. The catalog card must render the
specific half **from live data** wherever possible, exactly as that document
concluded the app itself should.

### Check 4 — Guardian v2 passes, with coverage disclosed

**Fail if:** Check 0a (syntax) fails, or Check 0b finds a fabricated KPI, or the
app has known-dormant panels that were never audited.

**Evidence:** the pass output **and** the coverage disclosure — which sweeps ran,
what they found, which panels were excluded and why. A pass with no disclosure is
not a pass; that is the standard Guardian's own 0b-coverage rule sets.

**Live example of what this catches:** StoneDesk's Slabs panel rendered **8
invented slabs** and computed four KPIs from them whenever its real store was
empty. The panel looked finished.

### Check 5 — Reference data is loaded and matches the repo

**Fail if:** the app has per-licence reference tables and
`tools/sairn_load_state_check.py` reports MISSING, STALE or EXTRA.

**Why this is a listing gate and not a maintenance item:** a seed-file change is
**inert until a loader runs**. `LAW-PINNACLE-2026` computed federal answer
deadlines **three days late for a day** because two committed corrections were
never loaded, and it was found by accident. Selling an app whose rules are stale
against its own repo is selling a wrong answer with a citation attached.

### Check 6 — Auth, roles and the credential lifecycle are real

**Fail if:** any write path with authority implications is reachable without a
session, or without the role it claims to require.

**Evidence:** a live probe per sensitive branch, using a payload built to fail
validation so nothing is written — a **401/403 rather than a 400 validator
error** is the pass.

**Live examples of the failure this catches:** `dnt_cred_rules` was owner-only in
intent and any-signed-in-employee in fact, because a comment said no role gate
was possible *"since SAIRNdental has no employee auth"* — auth was added and
nobody came back. And `grd_boq_rates` returns a **400 payload error** to a bearer
key with no session, where `rf_contingency_rules` correctly returns **401**.

### Check 7 — No unexamined regulatory surface the app implies it covers

**Fail if:** the app's positioning implies compliance coverage that has not been
researched.

**SAIRNfreedom is the worked example even though it fails Check 1 anyway.** Its
gaming compliance is researched to primary source; its **liquor licensing was
entirely unexamined** until today, and the two turned out to be *coupled* —
OAC 4301:1-1-53(D)–(E) makes a Chapter 2915 bingo violation simultaneously a
liquor-permit exposure. An app marketed as "compliance for lodges" that covers
one and not the other is making a claim it cannot support.

**The rule:** list what the app covers, and make the card say what it does not.
Every research document on this platform has an UNVERIFIED section; a product
card needs the same honesty in one line.

### Check 8 — Support reality: who answers, and how fast

**Fail if:** nobody owns inbound support for the app, or the response time is
unstated.

Listing creates an obligation the moment someone buys. This is the only check
here that is not about the code, and it is the one most likely to be skipped.

---

## The verdict, and the middle route

Each app gets one of three, recorded with a date and the evidence:

| Verdict | Meaning |
|---|---|
| **SELLABLE** | All eight pass. Card may be published |
| **SELLABLE WITH DISCLOSURE** | All pass except Check 7's completeness, and the gap is stated **on the card** in plain words |
| **NOT LISTED** | Any of Checks 1, 2, 4, 5, 6 fails |

**Checks 1, 2, 4, 5 and 6 are hard fails and cannot be disclosed around.** You
cannot caveat your way past an app that does not exist, an open pre-launch
blocker, a fabricated KPI, stale rule data, or a missing auth gate.

**Check 7 is the disclosure route** — an honestly-scoped product with a stated
boundary is sellable. That is how every SAIRN research document already works.

**Check 3 and Check 8 must pass but are cheap to fix**, so a fail there is a
"not yet" rather than a "no."

---

## Current standing, as of 2026-08-30

Recorded because the gate is worthless without at least one worked application.
**This is a preliminary read against known facts, not a completed run** — a real
run needs the live probes each check names.

| App | Standing | Blocking check |
|---|---|---|
| **SAIRNfreedom** | **NOT LISTED** | Check 1 — nothing built |
| **SAIRNmechanical** | **NOT LISTED** | Check 1 — never on `main`, route 404s |
| **SAIRNlaw** | **NOT LISTED** | **Check 2 — open pre-launch blocker whose sole justification is that no external customer exists** |
| All others | **UNASSESSED** | The gate has not been run. Do not read "not listed here" as "sellable" |

---

## Re-checking, because a pass is a point-in-time claim too

A card published once stays up. Every check here has a tense.

- **Re-run before any material coverage change is announced**, and on a schedule
  otherwise.
- **Check 5 is the one that decays fastest** — reference data drifts every time a
  seed is corrected and not loaded. That check is already automated
  (`tools/sairn_load_state_check.py`) and should gate the card, not just the
  push.
- **Check 2 requires re-reading the app's own docs**, because a new blocker can
  be filed at any time by any session — including one that does not know the app
  is listed.

**The failure this section exists to prevent** is the one SAIRNlaw's claim
document already suffered five times: the invariant half stays true, the specific
half quietly stops being true, and nobody notices because the page still reads
well.
