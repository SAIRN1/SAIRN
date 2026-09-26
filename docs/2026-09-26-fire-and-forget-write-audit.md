# The fire-and-forget write audit — task #19's second half, run and triaged

**Run 2026-09-26 (Hank).** Task #19's data-overwrite work already landed
tombstones and last-write-wins. This is the other recurring class: **a server
write whose result nobody reads.**

## The tool already existed, and that is the first finding

`tools/sync_write_result_check.py` was built for exactly this and is in
`docs/TOOLING-INVENTORY.md` as *"a SERVER WRITE whose result nobody reads …
this finds the call sites that never look."* **Nothing here is a new checker.**
What was missing was the **pass** — the tool had never been run platform-wide
with every finding triaged and written down, so its DISCARDED count was a
number nobody had turned into decisions.

That is the difference this document is: five findings, five verdicts.

## The sweep

**A CAPTURE, AS OF THE TRIAGE RUN, AND SUPERSEDED.** The numbers below are what
the tool said when the five findings were decided — kept because the verdicts
below are verdicts on *these* five. They are **not** current state: the discharge
section at the foot of this document changed three of them. Run the tool.

    python tools/sync_write_result_check.py     # as of the triage run

    WRITES_CONSUMED:333
    WRITES_DISCARDED:5
    WRITES_UNREADABLE:0
    WRITES_BENIGN_SINK:9   (shared_knowledge -- fire-and-forget on purpose)

**333 of 338 real writes read their result.** The platform is in good shape on
this class; the five that do not are individually below. The tool's own closing
note is kept in view rather than paraphrased:

> A RETURNED write is NOT a pass for the feature — it moves the decision to the
> caller, and this tool does not follow callers. A READ write is not a pass
> either: binding a result and never testing it scores READ here and is the next
> shape along.

**So 333 is a ceiling, not a clean bill.** The next pass worth running is the
one this tool says it cannot do: follow the returned writes into their callers,
and check that a bound result is actually TESTED rather than merely assigned.

## The five, each decided

### 1. `sairngrounds.html:2899` — `grdData('write','grd_rounds',round)` — **ACCEPTED, and already argued at the site**

The comment above it makes the case and it holds: a per-hole round write fires
continuously, a handler here would drown the cart-order toasts *"which are the
ones somebody is waiting on"*, and **"the user must not be told" was decided
while "nothing should be recorded" never was** — so `grdData()`'s own catch logs
every failure path including a timeout. The result is discarded; the failure is
not. No change.

### 2. `stonedesk.html:24956` — inside `saveSD3Data()` — **REAL, and it is also a second bug**

```js
if (c && c.id) { try { sdData('write', 'sd_customers', c); } catch (e) {} }
```

This site is **both** findings at once. It is fire-and-forget — a customer row
that never reaches the server leaves no trace — **and** it sits inside a loop
over every customer, so one call to `saveSD3Data()` fires one write per
customer. `saveSD3Data` has **16 call sites**, and the function's own comment
says it must not wait on a round trip.

**Raised separately as the batching bug.** The two fixes are the same edit:
batching the loop into one write gives exactly one result to read.

### 3. `stonedesk.html:29954` — `saveSDProfile()` — **ACCEPTED, and the justification CHECKED**

The comment says the same defect was live in `writeSDMemory()`, is fixed there,
and this copy is *"left as-is deliberately, so the shape stays visible next to
the note rather than being half-fixed in dead code nobody reviews."*

**The "dead code" half is the load-bearing claim, so it was verified rather than
believed: `saveSDProfile` appears EXACTLY ONCE in `stonedesk.html` — its own
definition. No caller.** The acceptance stands. If a caller ever appears, this
becomes finding 2's shape on the business profile.

### 4. `stonedesk.html:38841` — `slabSyncOne()` — **REAL, UNDOCUMENTED, and the sharpest of the five**

```js
try{ await sdData('write','slabs',slab); }catch(e){}
```

**Nine references, so it is live.** `slabs` is a **session-gated** resource — it
is in `SD_SESSION_GATED` with `read`, `write`, `reserve` and `release` — which
means a tokenless or refused call answers 403, and this site swallows it whole.
A slab hold, release or status change that never reached the server leaves the
yard's own record and the server's record disagreeing, with nothing said. That
is the reserve/release path a salesperson acts on.

**No decision is recorded at this site at all**, which is the difference between
it and findings 1 and 3.

### 5. `stonedesk.html:38929` — `sdLineageSyncOne()` — **REAL, UNDOCUMENTED**

```js
try{ await sdData('write', resource, rec); }catch(e){}
```

Four references, live. Lineage is the slab's movement history — the thing the
app's own comment calls *"reconstructable without inferring it from the slab's
current state."* A dropped lineage write breaks exactly that property, and
silently: the current state still looks right, and the history that would have
contradicted it is simply absent.

## DISCHARGED 2026-09-26 (Hank) — findings 4 and 5 fixed, and finding 2's fix was itself broken in three places

**`WRITES_DISCARDED` is 2, down from 5.** Re-run
`python tools/sync_write_result_check.py`; do not quote the figure from here.
The two that remain are findings 1 and 3, the two ACCEPTED ones — the record now
matches the decisions rather than trailing them.

Held by **`tests/stonedesk_write_result_consumption.js`** (18 arms, three
mutation controls and one ablation). Every arm was seen RED against the
unfixed file before the fix went in.

### Findings 4 and 5

Both now test their result, return a boolean, and **name the record in the
failure log**. `sdData()` already warned, but it names the RESOURCE — six of
`slabSyncOne`'s seven callers discard the return value, so without the id the
log cannot say WHICH slab the yard and the server disagree about. The arm that
checks this was tightened after an ablation showed it passing on the transport's
generic warning alone, i.e. passing for the pre-fix body.

**AND FINDING 4 HAD A SECOND HALF THE AUDIT MISSED, which is worse than the
first.** `pcToggleSlab()` has tested `ok === false` since the public catalog
shipped, to show *"Saved on this device only — the catalog on the web has NOT
changed"*. `slabSyncOne` returned `undefined` on every path, so **that warning
could never fire**: a publish that failed said *"Slab published to the
catalog"*. Not a missing warning — a warning that reads as present and cannot
happen. It is reachable now.

### Finding 2's fix was landed, and it broke three things silently

The batching edit was right about the trip count and wrong about the result.
`sdData()` returns `j.data`; the `write_batch` response has **no `data` key** —
its answer IS the envelope, `{ok, written, refused, skipped_without_id}`. So the
client saw `undefined` on every SUCCESSFUL batch:

1. **It warned on every save that DID reach the server.** `if (!r || r.ok !==
   true)` was true on success, so the log said the customer list was lost every
   time it was not.
2. **The `refused` branch was unreachable**, so a customer deleted on another
   device was never dropped locally — the exact resurrection
   `tests/customer_delete_does_not_resurrect.js` exists to prevent, arriving by
   a second route.
3. **`sdMarkSynced` is scoped to `action === 'write'`**, so sd_customers ids
   stopped entering the synced map. That map is the server-wins carve-out's only
   input, and an ABSENT id reads as *"never pushed"* — so the rule simply
   stopped applying to customers. It failed in the SAFE direction, which is why
   nothing showed.

`sdData()` now returns the envelope for that one named action, and marks the ids
the server says it WROTE (never a `refused` one — marking it would tell
hydration to overwrite a record the server never received).

### AND TWO SUITES WERE RED ON `main` WITH NOTHING SAYING SO

Both confirmed pre-existing by stashing every change here and re-running. This
is the sixth and seventh time this repo has recorded it.

- **`tests/faults/sd_write_faults.js` (17/1).** It pinned `sdData('write',
  'sd_customers'`, which the batching edit replaced. That assertion sits FIRST
  in its arm, so it **short-circuited before the assertion below it** — which
  had also started failing, because the same edit deleted the *"must not wait on
  a network round trip"* sentence that arm exists to protect. **A stale pin hid
  a live one, and one failure count looked like one problem.** The sentence is
  restored in the present tense; the phrase pin now matches unwrapped prose, so
  re-flowing a paragraph cannot silently disarm it again.
- **`tests/customer_delete_does_not_resurrect.js` (11/3).** Two arms — including
  the section 1 MUTANT, the one that proves the suite can see a resurrection at
  all — failed `sdSyncedBootstrap is not defined`: the file's hand-listed sandbox
  dependency list never gained the 2026-09-21 server-wins helpers. Its `st` stub
  was also write-only, so `sdServerWinsMerge` read an empty local list and
  answered `null`, which **disarms the mutant rather than failing it**. The third
  arm pinned the per-record `write`; its negative half (*the deleted id is not
  pushed back*) had been **passing vacuously** ever since, because
  `!written.includes('C-1')` is trivially true of a list nothing enters.

## What this pass did NOT do

- **The sweep itself changed no code.** Findings 2, 4 and 5 were left for their
  own change; `stonedesk.html` was read, not edited. The section above is that
  change, run afterwards, and it is separated from the sweep on purpose.
- **It did not follow RETURNED writes into their callers**, and the tool says
  it cannot. Two writes in `stonedesk-hr.html` and one each in several apps are
  scored RETURNED, which moves the decision rather than making it.
- **It did not check whether a READ result is TESTED.** 333 writes bind or
  consume a result; how many of those actually branch on it is a different
  sweep, and the tool names it as the next shape along.
- **It did not look at `api/` server-side writes at all.** This tool scans app
  HTML transports. A discarded write inside a handler is the same class and is
  not covered here.

## Where this sits

- `tools/sync_write_result_check.py` — the checker. Already existed; not
  modified by this pass.
- `tools/optimistic_success_scan.py` — the adjacent class: a SUCCESS message
  shown before the thing succeeded. Its inventory entry records that its hit
  count is not a defect count.
- `tools/discarded_verdict_check.py` — the mirror image: a REFUSAL that is
  computed and ignored. Different direction, different fix.
