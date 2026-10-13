# H1 -> hank: leg_bookings has the same TOCTOU race leg_merch_units was fixed for

Written 2026-10-13, batch b26. First found b25 (seq1370), re-confirmed
unchanged this batch before routing.

## The gap, exact file:line

`sairnlegacy.html:2999-3006`, `bookingConflict()`:

```js
function bookingConflict(facilityId,startIso,endIso,excludeId){
  var s=new Date(startIso).getTime(),e=new Date(endIso).getTime();
  return bookings().find(function(b){
    if(b.id===excludeId||b.facility_id!==facilityId||b.status==='Cancelled')return false;
    var bs=new Date(b.start_time).getTime(),be=new Date(b.end_time).getTime();
    return s<be&&bs<e; // real interval-overlap test
  })||null;
}
```

`bookings()` reads `ld('leg_bookings',[])` -- the LOCAL client-side
store, not a live server read. `saveBooking()` (line 3031) calls this
and hard-blocks on a conflict, but the check runs against whatever is
cached locally at that moment.

## Why this is the identical shape to a fix already built elsewhere

`api/sd-data.js`'s `leg_merch_units` reservation-lock (2026-08-10,
documented in its own comment there) exists specifically because the
identical class of race was found and fixed: two staff on two devices,
each holding a stale local copy, can each pass their own client-side
check and both write a conflicting result. That fix uses a conditional
`PATCH ... &data->>status=eq.Available` so only ONE of two simultaneous
writers can win server-side, and the loser gets a real `409
ALREADY_RESERVED`.

`leg_bookings` has no equivalent. The generic `LEG_RESOURCES` write path
(confirmed single dict occurrence, `api/sd-data.js:14734`, no dedicated
branch for `leg_bookings`) is a blind `merge-duplicates` upsert with no
server-side overlap check at all. Two staff on two devices can each
pass `bookingConflict()` against their own stale local copy and both
successfully save overlapping bookings for the same facility.

## What a fix would look like

Not this role's to build, but the shape is already proven in this same
file: a dedicated `leg_bookings` read/write branch (same pattern as
`bld_draws`'s or `leg_merch_units`'s own carve-outs) that re-checks the
real overlap against the LIVE server-side rows before writing, and
refuses with a `409`-style conflict rather than silently merging two
overlapping bookings.

## Severity, restated from b25

MODERATE (Tier B) -- a double-booked chapel or viewing-room slot during
a funeral service is a real scheduling failure for a grieving family,
though likely lower-frequency than the merch-unit race given typical
booking volume.
