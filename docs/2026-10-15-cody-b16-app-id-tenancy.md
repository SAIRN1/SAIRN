# `app_id is taken from the client again` — REFUTED, and the one real case is gated

**Written 2026-10-15 by cody, batch b16 item 4.** b15's triage flagged
`tests/sairnlegacy_fault_probe.py`'s arm 8 as a **possible live tenancy
defect, urgently**, because that is what its last output line says. Driven
against the code, it is not one.

---

## 1. The claim, and why it reads as a finding

The arm's own label is:

> `8. app_id is taken from the client again`

It is a **MUTATION LABEL, not a finding.** `tests/sairnlegacy_fault_probe.py`
is a fault probe: it **plants** `app_id: body.app_id || 'sairnlegacy'` into a
copy of the handler and asserts some other suite goes red. The label describes
**the defect it injects**, and a reader meeting it in a failure summary has no
way to tell that from a defect it discovered. That is the whole reason it was
routed as urgent.

## 2. REFUTED — measured against the live handler

| what was measured | result |
|---|---|
| the sairnlegacy generic write at `api/sd-data.js:16006` | `app_id: 'sairnlegacy'` — **the server's own string literal** |
| `grep -nE "app_id: (body\|payload\|req)\." api/sd-data.js` | **no match** |
| every non-literal `app_id:` write in the handler | **exactly one**, and it is §4 below |
| `app_id: '...'` literal writes | **116** |

**So no sairnlegacy row takes its `app_id` from the client, and nothing in the
handler takes `app_id` from `body`/`payload`/`req` directly.**

## 3. Why the arm failed — anchor rot in its TRAILING context

The arm reported `ANCHOR-0 in api\sd-data.js`: its find-text appears **nowhere**
in the file, so **nothing was ever planted** and no suite was ever asked.

The anchor carried **two further lines of trailing context** beyond the line it
mutates, ending in an inline
`res.status(503).json({ error: { code: 'NOT_PROVISIONED', ... } })`. That branch
has since been extracted into `await notProvisioned(res, r, ...)`.

**Measured by binary search on the anchor rather than by eye:**

```
anchor length                 295 chars
longest matching prefix       205 chars
matches up to   : "...updated_at: nowISO() })\n      });\n      if (r.status === 404 || r.status === 400) { "
diverges at     : "res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNlegacy data tables"
```

**The `app_id` line itself is byte-identical to the live file.** The rot is
entirely in code the arm was not testing.

**Fixed:** the anchor is cut back to the one line the mutation changes —
verified to occur **exactly once** in the file — so it no longer depends on a
neighbour's refactor. **The suite is now exit 0 and arm 8 passes.**

> A mutation arm whose anchor includes context it is not testing stops testing
> anything the first time a neighbour is refactored — and reports it **in the
> voice of the defect it was built to catch.**

## 4. The one genuine client-sourced `app_id`, and it is GATED

Found while sweeping for the above, so it is reported rather than dropped.

```
api/sd-data.js:1930   const memApp = String((body && body.app_id) || 'stonedesk');
api/sd-data.js:2359   body: JSON.stringify({ license_hash: licHash, app_id: memApp, shop_id: shopId, data: ... })
```

**The client chooses this one.** Three things gate it:

| gate | where | what it does |
|---|---|---|
| **allowlist** | `:193-194`, `:1931-1932` | `MEMORY_APPS` is derived from `ROLES_BY_APP`; an unknown app is a **400 `UNKNOWN_APP`** |
| **the session is bound to the CHOSEN app** | `:2113-2115` | `gateApp = (resource === 'memory') ? memApp : ...`, then `verifySessionToken(token, licHash, gateApp)` — a 403 without it |
| **stated intent** | the handler's own comment | *"slabs/profile/locations stay pinned to 'stonedesk' because they ARE StoneDesk's resources; only memory follows the caller."* |

**So a caller cannot stamp `sairnvet` on a memory row without holding a session
signed for `sairnvet`.** This is deliberate cross-app design, not a leak.

**ROUTED TO HANK AS A READ, NOT A DEFECT.** Nothing is asked for. The reason it
is written down: `memApp` is the **only** non-literal `app_id` in a 116-write
handler, the binding that makes it safe lives **429 lines away** from the write,
and nothing currently asserts that `gateApp` follows `memApp`. **If that one
line at `:2113` is ever simplified to a fixed app while the row keeps
`app_id: memApp`, this becomes a real cross-app write and no arm would notice.**

**Suggested next step (hank's call, not a request):** an arm that a memory write
with a session for app A and `body.app_id = B` is refused. **Not written here** —
it is an `api/` behaviour and cody's own b16 budget ended before it could be
driven with a counterfactual, which is the bar this batch held everything else
to.

---

## 5. What this document does not claim

* **Not** that the fault probe's other arms are sound — only arm 8 was read.
* **Not** that `memApp` has ever been exploited; no live data was examined.
* **Not** a review of `MEMORY_APPS`' membership. It is derived from
  `ROLES_BY_APP` minus `stonedesk_sub`; whether every app in it *should* accept
  a cross-app memory write is a product question, not a code one.
* **Not** verified by a counterfactual. The refutation is a source measurement
  plus the arm going green; the §4 gating was **read**, not driven.
