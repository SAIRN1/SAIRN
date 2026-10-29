# cc b73: Tier A review of cody b64's re-entry guards

The obligation was opened 2026-10-29T13:40:41Z. It covers commits
`c654f115` (six handlers) and `046e3f4f` (41 handlers).

**VERDICT: PASS, with one LOW finding routed to cody.**

## What was checked, and how

For every handler the obligation names outside sairncode, I read the guard
check, the hold set, the release and every `await`, in source order. The
extractor reads each function body brace by brace and skips strings and
comments. It is at
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-cc\a046cdf7-9eaf-4291-b1ac-b9b8bb34da67\scratchpad\holds.py`
in the session scratchpad and was not committed.

The handlers checked this way: sairncare (saveCsCount, saveCredEntry,
saveOpAudit), sairndental (addProvider, addCredential, saveCoverageRule,
respondToComplaint), sairngrounds (dcCreateInvoiceAndSchedule,
sendIrrZoneToQuote, sendBoqToQuote, sendWfToQuote, dcCreateQuote,
genEcosystemReport), sairnlaw (saveDraftAsDocument), sairnlegacy
(confirmPayment, saveCremation) and stonedesk (posCompleteSale, saveQuote,
sdSlabsImportLegacy).

- **Every release is in a `finally`, or in a promise `.finally`.** So it runs
  whether the write resolves, rejects or throws.
- **No `await` comes between a guard check and its hold set.** If one did, two
  presses could both pass the check.
- **The first press is never refused.** Every hold starts false (or 0), and is
  set only after the check.
- **An `await` that follows a release is never the duplicate-producing
  write.**
  - saveCredEntry and saveOpAudit close their modal synchronously before
    `await crRefresh()` / `await rOpAudit()`.
  - In sairnlegacy confirmPayment, the `leg_invoices` write at :3622 comes
    after `closePaymentModal()`, which is synchronous, so no second Confirm
    can reach it.
- **The promise-style handlers release correctly.**
  - In alfFamilySave, `.finally` covers the promise and a `catch` covers a
    synchronous throw before the promise exists.
  - mechCredAdd and mechAssetAdd wrap the call in `new Promise(done =>
    done(...))`, so a synchronous throw becomes a rejection and `.finally`
    still runs.
- **sairncode is sound.**
  - `scSaveBusy` and `scHoldWhile` (:3995-4004) set the hold, then
    `try { return await write() } finally { release }`.
  - All 24 `scSaveBusy('<key>')` checks pair with a `scHoldWhile('<key>')` in
    the same function, and each key equals its function name.
  - The only `await` between a check and its hold is the hold's own `await`
    (24 of 24, measured by script). addClaimEntry (c654f115) uses its own
    `scClaimSaving`, which is released in `finally`.
- **The suites were driven, not read.** All eight `tests/*_save_reentry.js`
  suites exit 0 at fcc8bcaf: sairncare, sairncode, sairndental, sairngrounds,
  sairnlaw, sairnlegacy, sairnmechanical, stonedesk.

## The finding: LOW, routed to cody

**sairndental.html:3104 increments the hold outside the `try`.**

    dntCredWriting++;rCredentials(null);
    var syncResult=null;
    try{syncResult=await sdnData('write','dnt_credentials',rec);}finally{dntCredWriting--;}

- If `rCredentials(null)` throws synchronously, `dntCredWriting` is never
  decremented.
- Before b64, the only effect was that the board kept showing "pending",
  through `dntCredIsPending`.
- Since b64, the new guard at :3044 (`if(dntCredWriting>0) ... return`) turns
  that into **every later credential add being refused until reload**. That
  breaks the obligation's own criterion: "no first press is ever refused".
- The increment line dates from cf1e3cd1 (2026-10-20). b64's guard is what
  makes it matter.
- **How likely is it?** rCredentials returns early when its tbody is missing,
  so I did not find a concrete throw path. That is why it is LOW, not a FAIL.
- **What the test misses:** the b64 "released on synchronous throw" arm throws
  from the write stub, inside the `try`. It never exercises this line.
- **The fix:** move `rCredentials(null)` inside the `try`, or increment inside
  it. Add an arm that makes `rCredentials` throw once and then asserts that a
  second add is accepted.

**Cause tag (recurring-bug-classes):** a hold acquired outside the
try/finally that releases it. The release is guaranteed only for code inside
the `try`.

## Out of scope, noted only

These are not part of b64's change and are not in this verdict.

- mechCredAdd and mechAssetAdd (sairnmechanical) have no `.catch`. A rejected
  `mechData` releases the hold but shows the user nothing, and leaves an
  unhandled rejection.
- This predates b64: the old `.then` had no catch either. It is a
  silent-failure shape, so it is cody's to decide on.
