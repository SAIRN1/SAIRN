# The clock-corrections queue, driven in a REAL BROWSER DOM

**2026-10-15, hank b14, item 1 — "DOM path proven beyond a vm where the tooling
allows".**

## What the tooling allows, measured first

    node -e "require.resolve('playwright')"   -> MODULE_NOT_FOUND
    node -e "require.resolve('jsdom')"        -> MODULE_NOT_FOUND
    python -c "import html5lib"               -> no html5lib
    npx playwright --version                  -> refuses: missing packages, no install

**So the standing functional-verification tool is not installed in this clone
and installing it is not a change this batch may make.** What IS available is
the Chrome tooling, and it reaches something better than a local harness: **the
page Vercel is actually serving.** No credentials were entered — the real
render functions were driven against injected fixture rows, which is exactly
what the vm arms do, with the difference that the DOM is a real one and
`button.disabled` is read as a **property of a real element** rather than as a
regex over a markup string.

Deployment confirmed before driving anything:

    GET https://sairn.vercel.app/sairnsenior.html  -> 200, 390,823 bytes
    'function renderCorrectionsView' present       -> true

## Run 1 — the queue renders and the control is real

| measured | value |
|---|---|
| `senPendingCorrections` / `renderCorrectionsView` / `vsCorrectionsBadgeText` / `vsApproveCorrection` / `senLastErrText` | all `function` |
| `#vs-view-corrections` in the real DOM | present |
| `#vs-tab-corrections` in the real DOM | present |
| correction submitted by **somebody else** → buttons rendered | 1 |
| its `textContent` | `Approve` |
| its `.disabled` | **`false`** |
| both the recorded and the submitted time in the rendered text | true |
| correction submitted by **this user** → button text | `You submitted this one` |
| its `.disabled` | **`true`** |
| the reason visible on screen | true |
| nothing pending → rendered text length | 283 characters, not a blank panel |
| badge, nothing pending | `Clock Corrections` |
| badge, two pending across two visits | `Clock Corrections (2)` |
| `senPendingCorrections().length` | 2 |

**`.disabled === true` is the arm that a vm could not give honestly.** The
local suite asserts `/disabled/.test(html)`, which is a string containing the
word; this is the browser's own view of the element.

## Run 2 — the refusal reaches the screen

`vsApproveCorrection('V1', 0)` driven with the transport forced to the real
server's refusal shape (403 `SELF_APPROVAL_REFUSED`), and the error line read
back out of the live DOM:

    #vs-corr-err present   true
    #vs-corr-err text      "This correction was submitted by "E1" and cannot be
                            approved by the same person. ANOTHER scheduler or
                            manager has to approve it."
    senLastErrCode('sen_visits')  SELF_APPROVAL_REFUSED

**It is the server's own words, not a paraphrase** — which is the whole reason
`senLastErr` was added to `senData()` in this batch. Before it, the function
returned a bare `null` on every failure and the Approve button would have been a
silent no-op on its single most common refusal.

## What this does NOT prove, stated rather than implied

* **No real session, no real row, no real approval.** The approval path was
  driven with the transport replaced; `approve_clock_correction` has never run
  against the live database. The server half is proven against the real handler
  locally (18 arms) and that is a different thing from a production round trip.
* **No screenshot.** The checks are DOM assertions, so a picture would add
  nothing a reader could verify, and `.disabled` is not visible in one anyway.
* **The tab was opened by this session and closed again**; nothing was left
  behind and no site permission beyond the page load was used.
* **A real scheduler's view depends on `senHydrateVisits()` having run** — the
  queue reads local rows. A scheduler whose hydrate has not completed sees an
  empty queue that is not empty, and that is in the handoff as an open item.
