# SAIRNlegacy — Merchandise Reservation Atomic Lock

**Status:** Design approved 2026-08-10. Not yet implemented.

Closes `SAIRN-BACKLOG.md`'s "SAIRNlegacy merchandise reservation needs a
real server-side lock" entry (logged 2026-08-09, highest priority in that
backlog) — real risk of the same physical casket/urn getting promised to
two grieving families.

## 1. Current state (verified against live code, not the backlog text)

`confirmReserve()` (`sairnlegacy.html:1891`) re-checks `u.status` against
the **local** `merchUnits()` snapshot, then calls the generic
`leg_merch_units` write route (`api/sd-data.js:1653-1669`) — a blind
upsert (`on_conflict=license_hash,merch_unit_id`,
`resolution=merge-duplicates`). That route already exists (added
2026-08-07) and is reachable — the backlog's "no server route yet" is
stale. The real gap is narrower than the backlog implied: the route has
no conditional logic. Two devices, each holding a stale local
`Available`, can both pass their own check and both successfully upsert
`status:'Reserved'` with different `reserved_for_case_id` — the second
write silently wins, no error to either party.

## 2. Design decision

Add a resource+transition-specific atomic branch to the *existing*
`leg_merch_units` write route: when `payload.status === 'Reserved'`, use
a conditional `PATCH` (`WHERE merch_unit_id=X AND data->>status=eq.
Available`) instead of the blind upsert. If the row isn't in that state
at write time, PostgREST returns 0 affected rows — mapped to a real 409
`ALREADY_RESERVED` the client surfaces honestly, instead of a silent
overwrite.

**No schema migration required.** The condition is expressed directly in
the PostgREST filter against the existing `data` jsonb column — no new
column, index, or constraint. This is the one architectural reason #1 is
smaller than #2: nothing needs to run in Supabase's SQL editor first.

**Scope stays narrow, on purpose:** only the `Available -> Reserved`
transition gets the gate. `releaseUnit()` (back to `Available`) and
`markUnitSold()` (`Reserved -> Sold`, or any status `-> Sold`) keep the
existing blind-upsert semantics — neither has the same two-grieving-
families contention shape the backlog flagged, and gating them wasn't
part of what was reported. If a future audit finds a real race on
`markUnitSold()` too, that's a separate, deliberately-scoped follow-up.

## 3. Server change (`api/sd-data.js`)

Inside the existing `if (LEG_RESOURCES[resource] && action === 'write')`
block (`api/sd-data.js:1653`), before the generic upsert: if
`resource === 'leg_merch_units' && payload.status === 'Reserved'`, PATCH
`leg_merch_units?license_hash=eq.<licHash>&merch_unit_id=eq.<id>&data->>status=eq.Available`
with `{ data: payload, updated_at: now }`. Empty result array (0 rows
matched — either already reserved/sold, or the row never finished its
initial sync) → 409 `ALREADY_RESERVED`. Non-empty → 200 with the updated
row, same response shape every other write already returns.

## 4. Client change (`sairnlegacy.html`)

`confirmReserve()` (`sairnlegacy.html:1891-1906`) needs to distinguish
"rejected for a real reason (409)" from "network/local-only fallback" —
`sdnData()` (`sairnlegacy.html:1261`) collapses every non-2xx response
to `null`, and it has ~40 other call sites across this file that all
depend on that exact truthy/falsy contract. Changing `sdnData()` itself
is out of scope and unnecessary risk for this fix. Instead,
`confirmReserve()` makes its own direct `fetch(DATA_API, ...)` call for
this one write (same request shape `sdnData()` builds, inlined) so it
can read the real response body/status without touching the shared
helper or any of its other callers. On a 409, show the real rejection
reason ("This unit was just reserved or sold by someone else — pick a
different unit") and refresh the merchandise panel. On any other
failure, keep today's "Reserved on this device only" fallback message.

## 5. Testing

- Pure logic: two concurrent PATCH requests against a freshly-seeded
  `Available` unit (via curl, no browser needed) — confirm exactly one
  returns the updated row and the other returns 409.
- Live interaction: reserve a real unit through the UI, confirm success;
  attempt to reserve the same unit again, confirm the honest rejection
  message (not a silent second "success").
- No-regression: `releaseUnit()` and `markUnitSold()` still work exactly
  as before (untouched code paths).
