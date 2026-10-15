# TIER A REVIEW — hank's `sd_photos` size fix, with T17

**fourth / b22, 2026-10-15. Subject: `e9d9c8192620` — "fix(sd_photos): every
real photograph missed the row cap, and the server blamed a migration".**

Reviewed against the real diff and the real working tree, not against the commit
message. **Every figure below names the command that produced it. Re-derive
anything you mean to quote, including out of this file.**

| | |
|---|---|
| commit | `e9d9c8192620b3b3fe017507ca9a1069b2d1ca0f`, authored 2026-10-14T19:24:03-04:00 |
| files | 5 — `api/_lib/ai-safeguards.js`, `api/_lib/ai-scan-redaction.js`, `api/sd-data.js`, `api/sd-photos-size-and-provenance.test.js`, `stonedesk.html` (`git show --stat --pretty=format: e9d9c819`) |
| size | 938 insertions / 92 deletions |
| premise | `docs/2026-10-14-fourth-b19-sd-photos-premise.md`, option (a) client-side downscale, Michael's decision |
| suite | **26 passed / 0 failed / 0 unproven**, `node api/sd-photos-size-and-provenance.test.js` → exit 0 (scratchpad `sdphotos_suite_b22.log`) |
| syntax | `node --check` clean on `api/sd-data.js`, `api/_lib/ai-safeguards.js`, `api/_lib/ai-scan-redaction.js` |

**This review covers the size fix and T17 only.** The same commit also carries
the `notProvisioned()` rewrite; that is reviewed separately in
`docs/2026-10-15-fourth-b22-not-provisioned-helper-review.md`, because its
findings are about a different 157-branch surface and folding them together
would bury both.

---

## 1. WHAT HOLDS, and it is the substance of the change

**The cap frame is right, and I checked the thing that would have made it
wrong.** `sd_photos` carries `octet_length(data::text) <= 65536` **per row**,
not per collection: `sdSyncCollection()` pushes `sdData('write', key, r)` **one
row per photo** (`stonedesk.html:2101`), and only for rows whose JSON actually
changed (`before[String(r.id)] === now` → skip, `:2100`). So a 44,000-character
image budget is a per-photograph budget and does not compound across the 200
locally-held photos. **If the collection had been blob-wrapped into one row —
which is exactly what `SD_SYNCED_OBJECT` does for `sd_negotiated_prices` and
`sd_pricing_rules` twenty lines earlier (`:2060-2071`) — the budget would have
blown at the second photo.** It is not, and that is the single assumption the
whole ladder rests on.

**The ladder measures.** `SD_PHOTO_LADDER` is 11 rungs from `[1600, 0.72]` to
`[320, 0.4]` and each rung's `c.toDataURL('image/jpeg', q)` has **its own
resulting length tested** against `SD_PHOTO_DATAURL_BUDGET`
(`stonedesk.html:26025-26040`). A no-fit returns `null` rather than the
original, and the comment says why. That is the right shape and it is the
opposite of the sibling slab path, which budgeted the decoded byte size and let
an oversized photo through (`stonedesk.html:8780-8789`, its own history).

**A failed push is still not reported as success.** `sdDataFailed` now toasts
the first failure in a burst and names the row-too-large case; the local write
has already happened, so the app is never worse off, and `st()` carries **zero
silent catches** — a `localStorage` quota failure goes to `sdStorageFailed()`
and `st()` returns `false` (`stonedesk.html:1978-1979`). The failure path's own
failure path is guarded.

**T17 is wired at the row, and this is the exact thing my own b21 F4 found
MISSING on the sibling.** `p.ai_source = 'claude:photo-qc'` is set **on the row
object** immediately before `saveSD3Data()` (`stonedesk.html:26191-26192`), so
it goes through `st()` → `sdSyncCollection()` → the server copy. **`rf_photos`
drops its equivalent because the handler rebuilds the record from three named
fields; `sd_photos` does not, because nothing rebuilds it.** `aiAnalysis` — and
only `aiAnalysis` — is in the redaction partition (`api/_lib/ai-scan-redaction.js:96`,
`sd_photos: ['aiAnalysis']`); `data` is deliberately absent, because redacting
a base64 payload corrupts the image. Correct, and correct for the stated reason.

**The NOT-HIGH-RISK classification is recorded with its argument, in the order
the argument runs.** `api/_lib/ai-safeguards.js:131-146` says the content would
justify high-risk, that `sd_photos` is not in `SD_SESSION_GATED` so an approval
gate would 403 every analysed photo on an app with no sign-in, and that
promoting the row is **a session decision first**. A classification whose
dissent is recorded inside it is not a classification I can overturn from
outside; it is a decision with its own premise attached.

---

## 2. F1 — THE FAILED-DOWNSCALE BRANCH PUTS THE ORIGINAL ON THE ROW, AND THE ROW IS STILL SYNCED

`stonedesk.html:26078`:

```js
data: small ? small.data : e.target.result,
```

Eighteen lines above it, the function's own comment states the rule this line
breaks: *"a downscaler that silently returns the original is how an oversized
row reaches the server looking like a downscaled one."* The downscaler is
innocent — it returns `null`. **The caller is what passes the original
through**, and then `sdPhotos.unshift(photo)` → `saveSD3Data()` →
`sdSyncCollection()` hands that row to `sdData('write', 'sd_photos', r)` like
any other.

**It is not silent, and that is the mitigation that holds:** `downscaled: null`
and `dims: null` are on the row, the toast fires, and `src_bytes` records the
original length. A reader can tell. **But three things follow that the change
does not say:**

* **The toast's claim is the one thing that can be false.** *"Photo kept on this
  device only"* is asserted **before** the write that would make it true. The
  row is up to ~13.3 MB of base64 for a 10 MB input (`f.size <= 10*1024*1024`,
  `:26052`, unchanged by this commit), and the typical whole-origin
  `localStorage` quota is 5–10 MB. `st()` reports that failure honestly rather
  than swallowing it — so the user gets *"kept on this device only"* and then a
  storage failure for the same photograph. Two messages, one event, and they
  disagree.
* **The server gets a request that cannot succeed.** The outcome the toast
  promises is delivered by the server refusing the row, not by the client
  declining to send it. After this commit that refusal is a **400 ROW_REFUSED**
  naming the 64 KB cap — better than the old 503, and a second toast from
  `sdDataFailed`'s burst.
* **It re-fires once more, later.** `sdSyncCollection` pushes only changed rows,
  so the oversized row is pushed once on insert and then skipped. **Except that
  `photoAiAnalyze()` sets `p.aiAnalysis` and `p.ai_source` on the same row and
  calls `saveSD3Data()` again (`:26176-26192`)** — the row has changed, so it is
  pushed a second time and refused a second time.

**NEXT STEP, and it is small:** on `!small`, either keep the row out of the sync
set (an explicit `backup: false` that `sdSyncCollection` skips, the same shape
as the idless-row skip it already has at `:2098`) or keep a thumbnail as `data`
and say so. Today the code keeps the version that **cannot** be backed up, while
its own comment at `:26073-26077` argues the opposite: *"the version that is
backed up must be the version that exists."*

**WHY THIS IS NOT THEORETICAL.** `small === null` is not only the
"no rung fits" case — it is also `img.onerror`, a null 2D context, and any
`toDataURL` throw. Mobile Safari has historically capped canvas area, which
makes the failure most likely on exactly the device this feature is for: a phone
photographing a job.

---

## 3. F2 — THE BUDGET IS COUNTED IN CHARACTERS AND THE CONSTRAINT IS COUNTED IN OCTETS

`out.length` is UTF-16 code units; `octet_length(data::text)` is bytes of the
serialised JSON. For the base64 data URL the two are the same — base64 is ASCII.
**They are not the same for the rest of the row**, and the rest of the row is
what the 21,536-byte margin is for:

* `name: file.name` — a filename, arbitrary Unicode, **unbounded**. A long
  non-ASCII filename costs up to 4 bytes per character.
* `aiAnalysis` — 3–5 sentences of model prose, which may carry non-ASCII
  (em dashes, degree signs, accented place names), plus JSON escaping.

**This is a bounded risk, not a defect, and I am recording the bound rather than
the worry:** 65,536 − 44,000 = **21,536 bytes** for everything else, against a
realistic `aiAnalysis` of ~600 characters. The margin is roughly 30× the
expected need. **But nothing measures it**, and the one field in it with no
length limit at all is the one supplied by the operating system. **Next step, if
anything: cap `name` at a stated length on the row** — the full filename is not
what the QC note is for.

---

## 4. WHAT I DID NOT CHECK, said rather than left implicit

* **The downscale was not driven in a browser.** `sdDownscalePhoto` needs a real
  `Image`, `canvas` and `toDataURL`; I reviewed it by reading and by checking
  the suite's coverage of it. **The claim "an 11-rung ladder gets a phone photo
  under 44,000 characters" is hank's measurement, uncorroborated here.** What I
  did verify is that the code checks rather than assumes, which is the property
  that makes the claim self-correcting.
* **`stonedesk.html` was not re-extracted block by block.** I did not change it,
  and Check 0a over a 2.0 MB single-file app is not in this review's scope. Its
  owner is the session that edited it.
* **The `sdCapLocal('sd_photos', …, 200)` interaction with removal propagation**
  is pre-existing and documented in place (`:26088-26096`); unchanged by this
  commit and not re-litigated here.

---

## 5. VERDICT

**The size fix is sound and the premise it was built on is the one I wrote.**
The cap is framed per-row correctly, the ladder measures instead of predicting,
`null` is a real answer, and the failure reaches a human. **T17 is genuinely on
the row** and is the clean counter-example to the `rf_photos` rebuild my b21 F4
found.

**Two findings, both in the caller rather than in the mechanism:** F1, the
failed-downscale branch stores and syncs the original while the toast says it
will not be backed up; F2, the margin is counted in the wrong unit for the one
unbounded field in it. **Neither is a reason to hold the change.** F1 should
land before the next StoneDesk release, because it is the branch that fires on
a phone.
