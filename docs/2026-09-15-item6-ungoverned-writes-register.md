# Item 6 — the ungoverned-write register that did not exist, and the per-site judgment

**2026-09-15 (Fourth).** Item 6 has been "still being triaged" across several
sessions. **The reason is that there was no list.** Nothing on disk enumerated
the sites, so each session re-derived a population, triaged a few, and left no
register for the next one.

This is the register, derived rather than typed, with a judgment against every
site.

---

## First: the count in the item's own name is not a count of writes

The item is carried as "41 ungoverned writes". **No population of 41 writes
exists.** Two different measurements are close enough to be conflated and are
not the same thing:

| Measurement | Tool | Count today | What it is |
|---|---|---|---|
| Write call sites reading their result on the success path only, or not at all | `tools/write_path_fault_scan.py` | **26** (25 after this pass) | **writes** — this is the population item 6 is about |
| Unguarded property reads that throw | `tools/missing_dom_target_check.py` | **41** | **reads**, in StoneDesk's DOM layer — a different item |

**The 41 is the DOM one.** Recorded here so the next session does not spend the
time I did looking for a 41-write list that was never there, and so the item can
be carried against a number a tool will reproduce.

---

## The register: 26 sites, and only three needed a change

`tools/write_path_fault_scan.py` says of itself, correctly, that it "is NOT a
list of defects". Every site below was read in context with its enclosing
function.

### Class 1 — `record*SharedTopics`: 9 sites, ACCEPTED BY DESIGN

`sairnbiz:4897`, `sairnbuild:8591`, `sairncode:12478`, `sairndesign:1789`,
`sairnlaw:2554`, `sairnlegacy:2200`, `sairngrounds:4993`, `sairnscape:3514`,
`stonedesk:23176`.

All nine write `shared_knowledge` with a list of words. StoneDesk's carries the
comment `// fire-and-forget, non-blocking` already.

**Judgment: correct as written, and fixing them would be a regression.** A
failed shared-topics write loses a vocabulary hint. Blocking a user's action on
it, or toasting about it, would make a cosmetic feature interrupt real work.
**Nine of twenty-six are accepted, not outstanding**, and the item's count should
say so.

### Class 2 — sync engines with `.then` and no `.catch`: 6 sites, CLOSED ONE LAYER DOWN

`bldSyncCollection` (2363), `bldRetryPending` (2443), `sfSyncCollection` (1762),
`sdSyncCollection` (2043, 2078), `mechPushOne` (1759).

These read the result on the success path and have no `.catch`, so the scan
flags them. **A rejected promise here would be an unhandled rejection — and the
transport contract now makes it unreachable.** `tests/faults/transport_timeout_sweep.js`
asserts, for all fifteen apps, that *"a TIMEOUT resolves to the failure value,
never a rejection"*, and that every transport's catch returns a value rather
than re-throwing.

**Judgment: not outstanding, and the reason is worth writing down** — this class
was closed by work aimed at something else entirely. It is also fragile in a
specific way: the day a transport starts rejecting, six `.then`-only sites become
unhandled rejections at once. The guard that keeps this true is that sweep's
arm, not anything at these sites.

### Class 3 — `.then`-only on a real record: 5 sites, REAL BUT LOW

`sairnmechanical:1949` (`mech_credentials`), `sairnmechanical:2098`
(`mech_site_assets`), `sairnsenior:5175` / `5212` (`sen_settings`),
`stonedesk:30231` / `30251` (`sd_crm`).

Same shape as class 2 but on business records rather than a sync engine, and
each already inspects `saved` on the success path. **Judgment: real, low, and
NOT MINE TO CHANGE** — SAIRNmechanical, SAIRNsenior and StoneDesk are other
sessions' territory tonight. Listed with their resources so whoever holds them
can take them without re-deriving.

### Class 4 — the three that were genuinely wrong

| Site | Verdict |
|---|---|
| **`sairndesign:2148` `saveRoomDimensions`** | **FALSE FLAG.** The result IS awaited into `syncResult` and drives a toast. The scan mis-flagged it; no change made, and saying so is the point of reading rather than counting |
| **`sairnscape:2934` `scpSendDesignToQuote`** | **REAL, AND FIXED IN THIS PASS** — see below |
| **`stonedesk:24252` `saveSD3Data`** | **REAL, and StoneDesk is claimed.** `try { sdData('write','sd_customers', c); } catch (e) {}` — a bare catch that swallows, on the CUSTOMER record. Flagged, not touched |

---

## The one fixed: a quote reported as sent that was on one device only

`sairnscape.html:2934`, `scpSendDesignToQuote()`. Two writes, one sentence:

```js
scpData('write','scp_quotes',qrec);          // un-awaited, unchecked
rec.quote_id=qrec.id;
var syncResult=await scpSaveDesignRecord(rec);   // awaited, drives the toast
...
scpToast(syncResult ? 'Sent to Quoting as draft Q-…' : '… locally — the design
         record itself did not sync …');
```

**Whenever the design synced and the quote did not**, the button flipped to
"Sent to Quoting (Q-…)", `rec.quote_id` was set locally, and the quote existed
on that device alone — while the toast reported the *design's* outcome as though
it were the quote's. `scp_quotes` is what a customer gets priced from.

Fixed: the quote's write is awaited into its own `quoteSynced`, and the message
names **which** write failed. Three outcomes, because "both reached the server",
"the quote did not" and "the design did not" are three different things to do
next, and the old sentence could only say the third.

`tools/write_path_fault_scan.py`: **26 → 25**.

---

## What the register says the item actually is

| | sites |
|---|---|
| Accepted by design (`shared_knowledge`) | **9** |
| Closed one layer down by the transport contract | **6** |
| Real, low, in another session's app | **5** |
| False flag | **1** |
| Real and fixed here | **1** |
| Real and flagged, app claimed | **1** |
| Not individually read (remaining `then-only` in the same two classes) | **3** |

**The honest state of item 6 is not "41 outstanding".** It is 15 sites that are
correct as written or closed elsewhere, 6 that are real and belong to sessions
who hold those apps, one fixed, and one flagged. Carried as a single number it
read as a large open surface; enumerated, it is small and mostly other people's.

---

## What this does NOT claim

- **Three `then-only` sites were not individually read** — they fall in the same
  two classes as sites that were, and saying "not read" is better than implying
  a judgment I did not make.
- **The transport-contract argument for class 2 rests on one suite.** If
  `transport_timeout_sweep.js` stops asserting that transports resolve rather
  than reject, six sites become unhandled rejections and nothing at those sites
  would say so.
- **No live verification.** `scp_quotes` was fixed and syntax-checked; that the
  new message appears against a real failed write has not been observed.
