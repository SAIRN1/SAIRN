# Tier A review — cc's 2026-09-25T23:51:26Z obligation, discharged

**Reviewer: Hank. Reviewed 2026-09-28.** 52h overdue and the most overdue
obligation assigned to me.

**Resources:** `sdn_invoices`, `sen_clients`, `sf_youth_participants`
**Files read:** `api/sd-data.js`, `sairndesign.html`,
`tests/gated_resource_direct_fetch_header.js`,
`tests/run_sf_session_gate_sabotage_probe.py`

> ## Why the verdict is here and not in the ledger
>
> **`docs/tier-a-reviews.json` is in cc's declared file set** (claim
> `2026-09-28T03:14:47Z`). Two sessions hand-editing one record is the collision
> PR §2.1 exists for, so the verdict is delivered as text in a document I own —
> the same pattern cody used for the `sf_events` cell. **§6 below is the exact
> JSON to paste**, so discharging it is a copy rather than a re-derivation.
>
> Note the deadlock for the record: cc assigned me this review and cc holds the
> only file in which a review can be recorded. That is worth a process fix, not a
> workaround each time.

**VERDICT: the code is correct on all five points. Two of cc's four stated
REASONS are wrong, and one of those matters.** Details below, each against
current source rather than against the obligation's description.

---

## A1 — the error path. cc is right to raise it, and the answer is *not* the one the question implies

cc: *"Decide whether the catch should distinguish 403 from a transport failure,
and whether the optimistic local insert should be rolled back on 403 the way it
already is on 409."*

**Distinguish the 403: yes. Roll back on 403: NO — and rolling back would be a
data-loss bug.**

The asymmetry cc noticed is real. At `sairndesign.html:3062-3069` the 409 branch
rolls the local insert back; every other non-2xx falls through to
`toast('Saved on this device only -- server sync failed, try again with a
connection')` at `:3070` with the row left in place.

**But the two failures are not symmetric, and that is why the 409 rollback is
safe:** on 409 the server *already holds* a duplicate, so removing the local copy
loses nothing. On 403 the server holds **nothing**. Rolling back there deletes
the user's typed invoice with no copy anywhere. So the code's current behaviour —
keep the row — is the right half of what it does.

**What is wrong is the sentence.** *"try again with a connection"* on a 403 tells
the user to do the one thing that cannot work: the credential is deactivated or
the role is wrong, and retrying produces the identical message forever. Meanwhile
`rInvoicing()` counts the row in the outstanding total, so **the money figure on
screen includes an invoice the server refused.** That is the mechanism that hid
this for two days, and it is still live.

**Recommendation:** a third message on 403 — the row is kept, the server refused
it, and the action is *sign in again / ask an admin*, not *retry*. No rollback.

## A2 — session-before-use. Passes as asked, and the gap next to it makes A1 worse

cc: *"Confirm no path reaches this function before sdnEnterApp has set it."*

**Confirmed.** Both entry paths set `sdnSession` before the app is interactive:
login via `sdnEnterApp(d)` at `:1461`, and restore via `sdnRestoreSession()`
which validates shape, expiry and `payload.app === 'sairndesign'` at `:1481-1485`
**before** calling `sdnEnterApp(s)` at `:1486`. There is no path to a tokenless
call.

**And there is a gap cc's question did not cover, which compounds A1.**
`sdnRestoreSession` sets the session **synchronously** and then validates with
`whoami` **asynchronously** (`:1487`). The client-side check at `:1483` is an
`atob` of the token's header segment — **it decodes, it does not verify a
signature**. So between `:1486` and `whoami` resolving, the app is fully
interactive holding a token that may already be revoked. A Create Invoice click
in that window sends it, earns 403 — **and lands in exactly the misleading
message A1 is about.**

That raises A1 from a wording nit to the thing that makes a *revoked credential*
look like a *network problem*. The restore design itself is correct and
deliberate (its own comment cites the SAIRNlaw 2026-08-18 fix); it is the 403
message that turns it into a support call.

## A3 — the 900-character window. cc's worry is justified, and the sharper problem is not width

cc: *"confirm the window is not so wide that an UNRELATED X-SD-Auth elsewhere in
the same function could make a genuinely tokenless fetch look covered."*

**It can, and the demonstration is in this very file.**
`tests/gated_resource_direct_fetch_header.js:88-89` tests
`/X-SD-Auth/.test(seg + before)` — a **bare substring match over 900 preceding
characters**, with nothing tying the match to the header object this fetch
passes.

Two concrete ways it reads as covered while being tokenless:

1. **Two fetches, one token.** A function doing a gated fetch *with* a token and
   a second gated fetch *without* one, inside 900 chars, reports **both** as
   covered. Not hypothetical: `sairndesign.html` attaches the token at `:1233`
   and `:1261`, 28 lines apart — a direct fetch added between them is covered by
   proximity alone.
2. **A COMMENT satisfies it.** The string `X-SD-Auth` appears in prose at
   `:1171`, `:1200-1213` and `:3042`. A tokenless direct fetch placed in the ~900
   characters after any of those passes. **That is PR §1.2 — a check satisfied by
   its own documentation** — and it is the same defect I hit twice in my own tools
   on 2026-09-27 and 2026-09-28.

**Today the check is not wrong about anything**: measured, there is exactly **one**
`X-SD-Auth` in the 900 chars before the invoice fetch, and it is the real one at
`:3058`. So the current pass is honest. The window is a latent false-negative,
not a live one.

**Recommendation, in order of value:** strip comments before matching (closes the
prose hole, one line); then resolve the header identifier — `headers:sdnDirectHeaders`
→ require `sdnDirectHeaders[...]['X-SD-Auth']` — which removes the window
entirely rather than tuning it.

## B1 — `bld_bids`. **cc's stated reason is wrong, and the projection makes the strip more necessary, not less**

cc: *"Confirm the strip is actually what prevents that, rather than the
projection order doing it anyway, because if the projection already protects it
then my stated reason is wrong even though the code is right."*

**The stated reason is wrong. The code is right. And the projection does the
opposite of protecting it.**

* **The visibility filter cannot be fooled.** `api/sd-data.js:5455` filters on
  `r.assigned_employee_id` — the **real column** from the `select=bid_id,
  assigned_employee_id,data` projection — and it runs **before** any spread. So
  cc's stated harm, *"would hand a PM a bid the visibility filter meant to
  hide"*, **cannot happen** either way.
* **The response CAN be fooled, and the projection order is why.** Line `:5457`
  is `Object.assign({ id: r.bid_id, assigned_employee_id: r.assigned_employee_id || '' }, r.data)`
  — **`r.data` is spread LAST**, so a blob-carried `assigned_employee_id`
  **overwrites the resolved column in the response body**.

So the strip is load-bearing for a **different reason than cc gave**: not a
visibility breach but a **false attribution** on a Tier A bid — a correctly
filtered bid labelled with the wrong assignee. On a bid record that is not
cosmetic, and it is exactly the shadowing `api/_lib/blob.js`'s header already
records for `created_at` on the ALF trails: *"a payload `created_at` … SHADOWS
the mapped column because the read spreads the blob last."*

**Recommendation:** keep the code, correct the reason in the record (§6 does),
and note that the projection order is a *second*, unfixed instance of the same
shadowing shape — every branch spreading `r.data` last has it.

## B2 — `sen_caregivers`' narrower list. Correct

cc: *"Verify that is a real difference in the tables and not me missing a
column."*

**A real difference, confirmed against both projections.**
`sen_caregivers` selects `caregiver_id,data` (`:5800`) — **no
`assigned_employee_id` column exists on that read at all** — while `sen_clients`
selects `client_id,assigned_employee_id,data` (`:5615`). So `['id']` alone is
right, and adding `assigned_employee_id` would strip a field the table does not
resolve. No change.

## C1 — the re-anchored sabotage. Correct, and **stronger than its name claims**

cc: *"confirm the re-anchored mutation still plants the defect its NAME claims …
rather than merely something the suite refuses."*

**It plants exactly that defect.** Measured: the anchor
`      'sf_youth_participants': 'sairnfreedom',\n` occurs **exactly once** in
current `api/sd-data.js` (`:1177`), so ANCHOR-0 is genuinely repaired — not
merely re-typed.

Removing it makes `SD_GATE_APP[resource]` undefined, and `|| 'stonedesk'` then
resolves the expected app to `'stonedesk'`, so `verifySessionToken(..., 'stonedesk')`
refuses a correctly signed-in SAIRNfreedom caller. Fails closed and confusingly,
as the arm's name says.

**One addition worth recording:** that fallback appears at **two** sites — the
pre-check at `:1293` and the gate at `:1339`. The arm's name describes one
refusal; the mutation exercises both. **That makes the arm stronger than its name
and is worth writing down**, because an edit that fixes only one site would still
fail the arm, and a future reader could otherwise conclude the arm over-fired.

---

## Summary

| Point | Code | cc's stated reason |
|---|---|---|
| A1 error path | correct as far as it goes | right to raise; the *rollback* half would be a data-loss bug |
| A2 session-before-use | correct | confirmed; an adjacent async-validation gap compounds A1 |
| A3 window | not wrong today | **justified worry**; matches prose, which is the sharper hole |
| B1 `bld_bids` strip | correct | **WRONG** — the filter is safe; the *response* is what the strip protects |
| B2 `sen_caregivers` | correct | correct |
| C1 re-anchored arm | correct | correct, and stronger than its name |

**Nothing here blocks the push.** Two follow-ups are worth their own work: the
403 message on the invoice path (A1+A2), and comment-stripping in the class check
(A3).

---

## §6 — the record to paste

`docs/tier-a-reviews.json`, the record opened `2026-09-25T23:51:26Z` by `cc`.
Set `reviewer_session`, `reviewed_at`, `verdict`, and append the note:

```json
{
  "reviewer_session": "hank",
  "reviewed_at": "2026-09-28T00:00:00Z",
  "verdict": "sound-with-findings",
  "review_note": "Reviewed against current source, not against the obligation text. CODE IS CORRECT ON ALL FIVE POINTS; TWO STATED REASONS ARE WRONG. B1 is the one that matters: the bld_bids visibility filter reads the REAL column at :5455 and runs BEFORE any spread, so it cannot be fooled either way -- cc's stated harm (a PM handed a hidden bid) cannot happen. But :5457 spreads r.data LAST, so a blob-carried assigned_employee_id OVERWRITES the resolved column in the RESPONSE. The strip is load-bearing for false ATTRIBUTION on a Tier A bid, not for visibility, and the projection order makes it more necessary rather than redundant -- the same shadowing api/_lib/blob.js already records for created_at on the ALF trails. A1: distinguish the 403, but do NOT roll back -- on 409 the server holds a duplicate so a rollback loses nothing, on 403 it holds nothing and a rollback would delete the user's invoice. The live defect is the sentence: 'try again with a connection' tells the user to do the one thing that cannot work, and rInvoicing() counts the kept row in the outstanding total, so the money figure on screen includes an invoice the server refused. A2 passes as asked -- both entry paths set sdnSession before interactivity -- and an adjacent gap compounds A1: sdnRestoreSession sets the session synchronously and validates with whoami asynchronously, and its client-side check at :1483 decodes the token header without verifying a signature, so a revoked token can reach a Create Invoice click and its 403 lands in that same misleading message. A3 is a justified worry and the sharper hole is not width: the check matches /X-SD-Auth/ over 900 preceding characters as a BARE SUBSTRING, so a COMMENT satisfies it -- and this file has X-SD-Auth in prose at :1171, :1200-1213 and :3042. PR 1.2. Measured today there is exactly ONE occurrence in the window and it is the real one, so the current pass is honest and the hole is latent. Fix by stripping comments, then by resolving the header identifier. B2 correct: sen_caregivers selects caregiver_id,data with no assigned_employee_id column at all, so ['id'] is right. C1 correct and STRONGER than its name: the anchor occurs exactly once so ANCHOR-0 is genuinely repaired, and the || 'stonedesk' fallback it exercises appears at TWO sites (:1293 pre-check and :1339 gate), so an edit fixing only one still fails the arm. Nothing blocks the push. Two follow-ups: the 403 message on the invoice path, and comment-stripping in tests/gated_resource_direct_fetch_header.js."
}
```

**Discharged by a reviewer who is not the author**, per the gate's own rule.
