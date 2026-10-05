# SAIRNscape `customers` — customer PII on a licence key alone. PROVEN LIVE, FIX ROUTED, NOT APPLIED

**2026-10-05 (Cody). THE FINDING IS PROVEN. THE FIX IS NOT APPLIED, AND THE
REASON IS NOT TECHNICAL** — the two-line change lives in `api/sd-data.js`, which
cc holds under a live claim (`2026-10-05T11:12:09Z`) and which I was told to stay
off this batch. Everything needed to apply it in one paste is below.

---

## WHAT WAS PROVEN, AND IT WAS PROVEN WITH A CONTROL

Driven against the deployed endpoint with `SCP-DEMO-2026` and **no session
token at all**:

| request | result |
|---|---|
| `read` `customers` | **200**, and it returned a row carrying `name`, `email`, `phone` and `address` |
| `write` `customers`, payload `{}` | **400 `customer payload.id is required`** |
| **CONTROL** `read` `invoices`, same bare key | **403 `FORBIDDEN — A valid employee session is required — sign in first`** |
| **CONTROL** `read` `scp_quotes`, same bare key | **403 `FORBIDDEN`** |

**THE WRITE PROBE WROTE NOTHING, AND THAT IS WHY IT WAS SHAPED THAT WAY.**
`api/sd-data.js:4769` refuses a payload with no `id` with a 400 **before any
store call**, so an empty payload reaches the handler body and stops there. A
**400 means the gate did not fire** — if the session gate covered this resource
the answer would have been the 403 the two controls got, which is checked
rather than assumed. SAIRNscape has no delete path, so writing a real probe row
would have been permanent; this proves reachability and leaves no residue.

**THE CONTROLS ARE THE POINT.** Without them a 200 could mean the platform has
no session gate at all. The same key, the same endpoint and the same verb get
403 on two sibling resources, so the gate exists, works, and does not cover
this one.

---

## WHY IT IS UNGATED, AND IT IS NOT AN OVERSIGHT IN THE GATE

Read directly out of the source, not inferred:

- `SD_GATE_APP` (`api/sd-data.js:1199`) carries exactly **two** SAIRNscape
  entries: `'invoices': 'sairnscape'` and `'scp_quotes': 'sairnscape'`.
- `SD_SESSION_GATED` (`:817`) carries the same two: `'invoices'` and
  `'scp_quotes'`, both `['read', 'write']`.
- `customers` is in neither list.

`api/sd-data-scp-session-gate.test.js` says why in its own header: *"All twelve
SAIRNscape resources dispatched on the licence hash alone … **Two of the twelve
are Tier A on INTEGRITY**: `invoices` (money) and `scp_quotes`."* **The sweep
that armed this gate was scoped to Tier A, and it was right to be.**

**SO THE ROOT CAUSE IS IN THE REGISTER, NOT IN THE GATE.**
`docs/CRITICALITY-TIERS.md` carries SAIRNscape's `customers` as **B / B**, and
its confidentiality cell was CORRECTED at some point to read *"A CUSTOMER's
NAME, PHONE, EMAIL AND STREET ADDRESS"* — the false no-PII sentence is gone.
**The basis was corrected and the TIER was not, and the tier is what the gating
sweep reads.** A correction that stops at the prose cell does not reach the
mechanism.

That is the same shape as open-work row 98 (`mech_docs` write on a licence key
alone, severity high, unowned for three days) and it is why this one needs
re-tiering as well as gating.

---

## THE FIX — TWO LINES, AND THE CLIENT HALF NEEDS NO CHANGE

### (a) `api/sd-data.js` — the gate

In `SD_SESSION_GATED`, beside the existing SAIRNscape pair at `:1147-1148`:

```js
      'invoices': ['read', 'write'],
      'scp_quotes': ['read', 'write'],
      'customers': ['read', 'write'],          // <- ADD
```

In `SD_GATE_APP`, beside the existing pair at `:1281-1282`:

```js
      'invoices': 'sairnscape',
      'scp_quotes': 'sairnscape',
      'customers': 'sairnscape',               // <- ADD
```

**BOTH, IN ONE EDIT.** The file's own comment at `:1283` states the rule and
names the day it was broken: *"a resource gated with no entry here resolves
expectedApp to `'stonedesk'`, so every signed-in SAIRNscape crew lead is refused
FORBIDDEN 'sign in first' whatever they do."* One list without the other is an
outage, not a gate.

**`customers` IS THE RESOURCE NAME AND `scp_customers` IS THE TABLE.** The test
file's own NAME TRAP section says it: SAIRNscape claimed the bare names before
the `scp_` convention existed. **A gate written against `'scp_customers'` would
gate nothing at all, silently**, and every refusal arm would still pass against
some other resource.

### (b) The client — ALREADY DONE, and checked rather than assumed

`sairnscape.html:2107`:

```js
try { var tok = sessionStorage.getItem(SCP_SESSION_KEY); if (tok) headers['X-SD-Auth'] = tok; } catch (e) {}
```

Every `scpData()` call goes through that one helper and attaches the header
unconditionally whenever a token exists — **there is no per-call `withSession`
flag to forget**, which is exactly what had to be repaired in `sairndesign.html`
before its gate could be armed. Both login paths (`scpDoLogin`,
`scpDoBootstrap`) write the token to `sessionStorage` before
`scpApplyLoggedIn → scpInit → scpSyncFromServer` runs, so a fresh login's first
read already carries it.

**That is the half that breaks apps** — arming a gate before the client can send
a token answers 403 "sign in first" to every correctly signed-in employee, and
this platform has recorded it three times. It does not apply here, and the
existing test's arms already read the shipped page rather than trusting that
sentence.

### (c) `docs/CRITICALITY-TIERS.md` — the root cause

SAIRNscape `customers` confidentiality **B → A**. The integrity axis is
genuinely B (a customer record is operational; the money lives on `invoices` and
`scp_quotes`) — **the tier moves because the worse axis moves**, which is the
rule `sd_sms_log` is already carried under in the same document. The
confidentiality cell already states the basis; only the letter is wrong.

**Without (c), (a) is a patch and the next gating sweep makes the same
decision again**, because the next sweep will also read Tier A.

### (d) The test arms

`api/sd-data-scp-session-gate.test.js` is not in cc's claim and I could have
written them — **I did not, deliberately.** Arms asserting `customers` is gated
are RED until (a) lands, and this repo's own record is that a suite with
permanently-red arms gets scrolled past and then the real failure beside it does
too. **They belong in the same commit as the gate**, and the file's existing
arms are the template: the load-bearing one is **set equality between
`SD_SESSION_GATED` and the `expectedApp` map**, not a hardcoded list, so adding
`customers` to one and not the other fails without anybody writing a new arm.

### (e) Live verification, after it lands

```
read  customers with SCP-DEMO-2026 and NO X-SD-Auth   -> must be 403 FORBIDDEN
write customers with SCP-DEMO-2026 and NO X-SD-Auth   -> must be 403 FORBIDDEN
                                                          (NOT the 400 it gives today)
read  customers signed in at /api/scp-auth            -> must still be 200
```

**The 400-becomes-403 transition on the write path is the assertion that
matters**, because 400 is what proves the request currently reaches the handler.
A fix verified only on the read path leaves the write path unproven, and the
write path is the one that stores a name, a phone number and a street address.

---

## WHAT I DID NOT DO, AND WHY

- **Did not edit `api/sd-data.js`.** cc holds it under a live claim and it is on
  this batch's explicit stay-off list. `sairn_claim.py check` refuses on a
  declared-FILES collision, 0.1h old, and the tool's own instruction is to flag
  it back rather than take it.
- **Did not edit `docs/CRITICALITY-TIERS.md`.** Same claim, same refusal — and
  cc is working a register cell in that file right now.
- **Did not prove the FIX live**, because the fix is not applied. The finding is
  proven live; the remedy is not. Those are different claims and the difference
  is this paragraph.
- **Did not write the open-work index row.** cc holds the index.

**This document is the whole change in pasteable form so that whoever holds
those files can land it without re-deriving any of it.**
