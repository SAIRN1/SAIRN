# HANDOFF — fourth / ted, batch b42, 2026-10-20

**READ THIS FILE ONLY.** It is the whole state. **4 of 6 DONE, 2 BLOCKED BY
OTHER SESSIONS' CLAIMS** (one of them half done). Everything done is on
`origin/main` and live; no force. Wrapped at **~50% real context**
(`tools/context_verify.py --digest-line`), with nothing half-finished.

**EVERY FIGURE NAMES THE COMMAND OR FILE THAT PRODUCED IT. Re-derive anything
you mean to quote.**

**THREE THINGS TO READ FIRST:**

1. **Two items are blocked by claims, flagged back and not routed around.**
   Timesheet day seven + start/end: `api/sd-data.js:16290` refuses any
   `hours` that is not exactly 6 values, and **cody b29 holds that file** — a
   client-only day seven would make every saved week fail its server sync.
   `sairnSyncAll` (`stonedesk.html:19938`): **hank b27 holds `stonedesk.html`**.
   §6.
2. **The push gate refused b42 once, and the route was your decision, not a
   skip.** The off-by-one fix had to change two cody-owned tests that pinned
   the buggy bound. The permission classifier blocked me from editing the shared
   `docs/sairn-path-manifest.json`, and then from a side-branch landing. **You
   chose "declare override"**, so I added a 5-line text insertion to
   `assigned_overrides` (`aab71bb0`) with a REMOVE condition. Every gate ran.
3. **Two existing test arms were defending the off-by-one.** One asserted
   *"168 is the hours in a week and is reachable"*. The hours are reachable,
   but overtime at a threshold of 168 is not (29 CFR 778.103/.105). The arm is
   rewritten with the old reasoning quoted in place. §3.

**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-fourth\fc1f8565-6013-48a4-b66b-d27902506016.jsonl`
(the same session as b41, continued)

**Working files:**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\fc1f8565-6013-48a4-b66b-d27902506016\scratchpad\b42\`
— `drive_ids.py`, `drive_queue.py`, `drive_dental2.py`, `drive_dental_b41.py`
(**re-runnable; pass a base URL to drive the live origin**), the count-asserted
`fix_*.py` patches, `add_defect.py` (all four records), `land.sh` (no-force
land loop that refuses a conflicted register), `29cfr778.txt`.

**NO SQL THIS BATCH.**

---

## 1. COMMITTED / PUSHED STATE

| | | command |
|---|---|---|
| `HEAD` vs `origin/main` | **0 / 0** after `land.sh` | `git rev-list --left-right --count origin/main...HEAD` |
| fixes | `da64a94b` sairnbiz ids · `6494262c` sbOtThreshold · `ebe472e1` sairncode queue · `cf1e3cd1` sairndental | `git log --author=fx --oneline` |
| register | `8be661b3` · `743713bc` · `4fb743c1` · `c61763d0` (+ `41821b80` re-seat) | one record per fix |
| gates | `aab71bb0` — the approved `assigned_overrides` entry + scrutiny flags | — |
| on origin | **every b42 sha is an ancestor** | `git merge-base --is-ancestor` |
| live | the changes are in the deployed pages, and **every b42 drive passes against `https://sairn.vercel.app/`**: ids 11/11, queue 11/11, dental 8/8, b41 credential suite 37/37 | `tools/sairn_http.py`; `scratchpad/b42/drive_*.py <url>` |
| manifest | **4 done, 2 blocked**, validates | `python tools/batch_manifest.py --check --agent fourth --batch b42` |
| force / blanket override | **NONE** | — |

**Two register rebase conflicts**, both resolved the same way. I took
upstream's register, skipped my record commit, and **re-added the record
with the tool**. A conflicted register was never staged.

## 2. CLAIMS HELD

**`fourth`: released at the end of this batch.** Held: `sairnbiz.html`,
`sairncode.html`, `sairndental.html`, the register, the manifest, the
deliverables, and (added mid-batch) the two `tests/` files. Declared
negatives: `stonedesk.html` (hank), `api/sd-data.js` (cody), `tools/`,
`CLAUDE.md`, `.claude/skills/`, `tier-a-reviews.json`. **The second claim
string (with the tests) never published.** Its push was refused by the same
gate, so the tests were covered only by the in-repo `assigned_overrides`
entry.

## 3. ITEMS 1–2 — sairnbiz

**Z1, ids (`da64a94b`).** One series per device, a sequential counter within
it. **RED 2/11:** 50 invoices minted in one millisecond got **one** id, and
the same happened to 50 employees. Editing one employee then matched 50
records, and a second device minted ids the first already held. These ids are
load-bearing: the invoice id is the GL `source_id`, the employee id is the
server upsert key `(customer_email, employee_id)`, and hydrate merges rows by
id. **Now** ids look like `<prefix>-<series>-<000001>`, with one random series
per device (VAT Art. 226(2) allows "one or more series"). The counter is read
and written synchronously, it never drops below the highest number already
stored, and ids already present are skipped. **GREEN 11/11** local and live,
covering same-ms ×50, reload, lost counter and second device. **One residual,
stated in the code:** two tabs minting in the same instant share the counter.

**Off-by-one (`6494262c`).** `n>168` became `n>=168`. 29 CFR **778.103** says
"each hour worked in excess of the maximum" and **778.105** says a workweek
"is a fixed and regularly recurring period of 168 hours", so a threshold of
168 can never produce an overtime hour. **RED 11/12 → GREEN 12/12.** All 18
sairnbiz suites pass.

## 4. ITEM 3 — sairncode queue line (`ebe472e1`)

**RED on the LIVE page, 4/11:** with 1 auto-assigned, 2 rejected, 1 accepted
and 1 pending, the line read *"4 other items cleared every check"*. **Now**
items route into three groups: cleared (auto-assigned only), decided (shown
in a new *Decided by a coder* table), and the queue. An unrecognised status
fails closed into the queue. **GREEN 11/11** local and live, and b41's
(B)(7) drive is still 27/27.

## 5. ITEM 4 — sairndental (`cf1e3cd1`)

**RED on the LIVE page, 4/8**, covering all three defects:
- a slow older answer overwrote a newer one (a stale "5" replaced the
  current "1"), and an older success overwrote a newer failure;
- **Guardian A3:** an older null repainted the side panels;
- `addCredential` blanked a real board during the write.

**Now** every ask carries a sequence number and **only the latest
renders**; older answers are dropped across all three panels. "Pending"
means the latest ask hasn't settled or a write is in flight, so the panel
can't get stuck on "Checking". **GREEN 8/8** local and live, and b41's suite
is 37/37 live.

## 6. WHAT IS OPEN — EXACT NEXT STEP PER ITEM

1. **Timesheet day seven + start/end (item 2's second half) — BLOCKED on
   cody b29 (`api/sd-data.js`).** Server half: at `api/sd-data.js:16290`
   accept `hours.length === 7` (keep accepting 6 for stored rows), loop to
   7, and validate an optional `times: [{start:'HH:MM', end:'HH:MM'}|null ×7]`
   (both or neither per day; `hours[i]` ≤ span, where end ≤ start crosses
   midnight). Client half (fourth, after the server change lands):
   - add `ts-d6` (Sun) plus start/end inputs at `sairnbiz.html` modal `:582`;
   - update `tsReadDays()`/`openTsModal()`, `rTS()` (`.repeat(6)`), the CSV
     header, and the `days[]` labels;
   - adjust `tests/sairnbiz_timesheet_hours.js`, which pins six days.
   Once day seven lands, also tighten `sbOtThreshold` to the record's real
   maximum. **With six days, thresholds 145–167 are still unreachable but
   honoured.**
2. **`sairnSyncAll` toasts success on a 4xx (`stonedesk.html:19938`) —
   BLOCKED on hank b27.** Next: reproduce with a forced 403 stub, so a fetch
   that resolves `ok:false` still counts as success. Then make any `!r.ok`
   count as failure, keep the item unsynced, and prove it with the forced 4xx.
3. **Vendor ids** (`saveVendor`, `"V"+Date.now()` last 4) have the same
   defect as Z1 but were out of scope. Use `sbNextId('V', v)`.
4. **Remove the `assigned_overrides` fourth entry** once cody has reviewed
   the two test arms (`docs/sairn-path-manifest.json`).
5. **Carried from b41:** sairndesign B6–B8; one real `cert` write to the real
   endpoint; cody's register record `ce15ddaa6a3c`; `hcc`/`drg` server-side.

## 7. PROVED vs LEFT UNPROVEN

**PROVED:** each fix was reproduced RED (three of them on the live page) and
then driven GREEN locally and on the live origin. All 18 sairnbiz suites pass.
Every sha is on origin, with no force.

**UNPROVEN:** no server I/O for any drive (fetch is stubbed). The two-tab
counter race is unmitigated. No suite in `tests/` covers the coded-items or
credential panels; the drives live in the scratchpad.
