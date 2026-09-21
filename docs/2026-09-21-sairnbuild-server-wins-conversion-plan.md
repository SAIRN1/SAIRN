# SAIRNbuild — how server-wins hydration has to be done here, and why it is not the same job

**Status: PLAN ONLY. Nothing in `sairnbuild.html` was changed to write this.**
Michael held sairnbuild back from the 2026-09-21 conversion on the stated
grounds that *"st() pushes to the server itself via `bldSyncCollection()`,
suppressed during hydration by a `bldSeeding` flag that `bldHydrateAll` sets
and `bldHydrateBids` does NOT — that asymmetry has to be READ and settled as
part of the conversion rather than inherited."* This is that reading.

**The first thing it produced was a correction to the reason for holding it.**

---

## 1. The asymmetry is real but it is NOT the one that was written down

The held-reason says `bldHydrateBids` fails to suppress the server push and
therefore echoes hydrated rows back. **Measured: it does not, because
`bld_bids` is not hooked to `st()` at all.**

- `BLD_SYNCED` holds **30** collection keys, and `bld_bids` **is not one of
  them** — checked by parsing the literal, not by reading around it.
- `_bldSyncOn` is built from `BLD_SYNCED`, and `bldSyncCollection()` returns
  immediately on `!_bldSyncOn[key]`.
- So `st('bld_bids', local)` at `sairnbuild.html:2535` pushes nothing, and
  `bldHydrateBids` needs no suppression.
- `bld_bids` reaches the server through **two explicit calls** instead —
  `bldData('write','bld_bids',rec,true)` at 4536 and 4552 — with a real
  employee session token, because `api/sd-data.js`'s `bld_bids` branch is one
  of the two bespoke session-gated branches in this app.

**So the asymmetry is the opposite shape from the one assumed:** it is not that
one hydrate forgot to suppress; it is that this app has **two different sync
mechanisms**, and only one of them runs through `st()`. A conversion that
treats both hydrates identically will be wrong about one of them.

## 2. What sairnbuild already has that the seven converted apps do not

`bld_sync_pending` (`sairnbuild.html:2404`), and it changes the design.

| | the seven converted apps | sairnbuild |
|---|---|---|
| what is recorded | `<app>_synced_ids` — ids that **have** landed | `bld_sync_pending` — ids whose push **failed** |
| written when | a write returns non-null | a write returns null (`bldPendingMark`) |
| cleared when | never | the write later succeeds (`bldPendingClear`) |
| bounded | no | yes — `BLD_PENDING_MAX` 500, with an `__overflow` flag |
| retried | no | once per sign-in, after hydration (`sairnbuild.html:2815`) |

These are complements, and **sairnbuild's is the more useful one.** The
converted apps' carve-out protects a record whose **first** push never landed.
`bld_sync_pending` knows about **any** unpushed change, including an update to
a record that synced successfully months ago.

**That distinction is not academic — it is exactly the hole fourth's review
found in SAIRNlaw.** `saveInvoice()` sets `invoiced=true` locally, the entry
write is refused, and the id is already in `law_synced_ids` from the entry's
original save, so the first-push carve-out does not apply and the next hydrate
reverts the flag. A pending-set carve-out would have protected it.

**RECOMMENDATION: do not bolt `bld_synced_ids` onto this app.** Derive the
carve-out from `bld_sync_pending` instead:

```
overwrite an id held on both sides UNLESS that id is in bld_sync_pending[key]
```

and — separately, and only if Michael wants it — consider whether the other
seven should gain a pending-set of their own. That is a platform change, not
part of converting this app, and it is the shape that closes fourth's finding
properly rather than by fixing one message.

## 3. Three things that must be fixed BEFORE the merge is changed

Server-wins writes more often than additive merge does, so each of these gets
more exposure the moment the conversion lands.

**(a) `bldHydrateAll` has no `try/finally` around the suppression.**
`sairnbuild.html:2506`:

```js
bldSeeding = true;
st(key, local);
bldSeeding = false;
```

A throw inside `st()` skips the third line and leaves `bldSeeding` **true for
the rest of the session** — the entire app's backup silently suppressed.
Confirmed worse here than in the apps that had it: `bldHydrateAll()` has **no
`.catch`**, and neither does its caller at 2813, so the throw also skips the
post-hydrate retry of everything in `bld_sync_pending`. One throw therefore
(i) stops all backup, (ii) strands the pending queue, and (iii) reports
nothing. This is the shape `sairnfreedom`'s own comment records being fixed in
`sairnvet` twice and `stonedesk` once, and which `sairnbiz` had too until
2026-09-21. **Fix it as its own change, before any conversion.**

**(b) `__overflow` has to make the carve-out FAIL CLOSED.**
`bldPendingMark` stops recording at 500 ids and sets `o.__overflow = true`
instead — deliberately, and it says so. But a carve-out that reads the pending
set as authoritative would then treat every id past the cap as *not pending*
and therefore *overwritable*, which is the destructive direction, during
exactly the long outage that filled the list. **When `__overflow` is set, the
merge must not overwrite anything in that resource**, and must say so — the
same three-state discipline as the unreadable synced map in the other seven
(PR §1.11). This is a decision, not a detail: the alternative is to raise the
cap, which does not remove the case.

**(c) `bld_bids` is outside every mechanism being built.**
It is not in `BLD_SYNCED`, so it gets no pending tracking and would get no
bootstrap. Its hydrate would be converted with no carve-out at all unless it is
given one. Either bring it into the pending mechanism or convert it explicitly
with its own reasoning — **do not let it inherit the shape silently**, which is
how the four SAIRNsenior hydrates ended up with one written reason between
them.

## 4. The bootstrap question, which is different here

The one-time read-only bootstrap in the seven marks every locally-held id as
seeded. With a **pending-set** carve-out there is nothing to seed: the absence
of an id from `bld_sync_pending` already means "no known unpushed change",
which is the correct default for pre-existing data and needs no migration pass.

**That is a genuine simplification and it should be checked rather than
assumed.** `bld_sync_pending` only started being written on 2026-09-04, and the
same comment records that **every push this feature ever attempted had failed
before that date** because `sql/sairnbuild_data_schema.sql` had never been run.
So a device that has not signed in since then may hold records that never
reached the server and are **not** in the pending list. For those, "absent from
pending" means "unpushed", not "safe to overwrite" — the exact inversion the
carve-out exists to prevent.

**So a bootstrap IS still needed here, and it is a different one:** a one-time
pass that marks every currently-held id as pending-unknown, or a recorded
attestation that the retry at 2815 has run to completion at least once on that
device. Decide which before writing it.

## 5. Order of work

1. **(a)** — the `try/finally`, with its own negative control. Independent of
   the conversion and worth landing alone.
2. Decide **(b)** — what `__overflow` means to the merge.
3. Decide **(c)** — whether `bld_bids` joins the pending mechanism.
4. Decide the §4 bootstrap shape.
5. Only then: route both hydrates through one `bldServerWinsMerge()` with the
   two named seams the other seven use (`bldHydrateLoad`, `bldHydrateStore`),
   where the store seam wraps `bldSeeding` **with the finally from step 1**.
6. Add `sairnbuild` to `APPS` in `tests/server_wins_hydration.js` and remove it
   from `PENDING`; the suite's arm fails if it is converted and left listed.
   The same-rule arm will require its merge to be byte-identical to the other
   seven modulo names — **which the pending-set carve-out will break**. That is
   a real conflict and it is the last thing to settle: either the shared rule
   grows a pending-set everywhere, or sairnbuild declares a justified variant
   and the arm learns about it. **Do not resolve it by weakening the arm.**

## 6. What this plan does not claim

It has not been driven. Everything above is read from the file and from the
literal values parsed out of it — `BLD_SYNCED` membership, the absence of a
`.catch`, the two explicit `bld_bids` write sites, the pending cap. No mutation
was planted and no behaviour was exercised, because nothing was changed. The
first conversion step should begin by driving the current behaviour, not by
trusting this document.

**And sairncare is NOT covered here at all.** It stays held pending Michael's
call on the MAR: "the server copy wins" on a medication administration record
is a clinical-documentation decision about whose entry survives a
disagreement, and it is not a sync question with a technical answer.
