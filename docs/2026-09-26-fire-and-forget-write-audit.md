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

    python tools/sync_write_result_check.py

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

## What this pass did NOT do

- **It changed no code.** Findings 2, 4 and 5 are real and are left for their
  own change; `stonedesk.html` was read, not edited. Finding 2 is being fixed
  as the batching bug.
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
