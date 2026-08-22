# StoneDesk Phase 1 — Slab Unification + Block/Bundle Lineage

**Design only. No code written. 2026-08-22.**

Scope confirmed by Michael after Step 1 verification overturned the original
premise: Phase 1 is not "migrate fungible SKU inventory to serialized slabs"
(slabs are already serialized, and always have been). Phase 1 is **unify two
parallel slab systems, kill a live fabricated-KPI defect, and add block/bundle
lineage above the existing slab→remnant chain.**

---

## 0. The headline: a live Guardian Check 0b violation on the flagship

Confirmed in a real browser, not read from source:

- `localStorage.getItem('sd_slab_tracker')` returns **`null`** — the Slabs
  panel's backing store is empty.
- `load()` falls through to an in-file `SEED` constant, so the panel renders
  **8 invented slabs** (SL-001 Calacatta Gold … SL-008 Emerald Pearl).
- KPIs computed from that seed report **Total Slabs 8 · Available 5 ·
  Allocated 2 · Inventory Value $4,420**. All four are fabricated.
- A genuinely real slab written through the production Bulk Slab Upload path
  (`sdSlabs.push()` + `saveSlabs()`, persisted to `sd_slabs`) is **invisible
  in the panel and excluded from every KPI** — Total Slabs stayed at 8.

This is user-facing today on the 100%-complete flagship. It is the same class
as every fabricated-KPI defect the 2026-08-18 sweep removed from SAIRNcode,
and it takes priority over the lineage work.

Note the failure mode precisely, because it generalises: **the panel did not
"show stale data" — it invented data when its real store was empty.** An empty
store rendering as an honest empty state would have been correct. Falling back
to a seed constant is what turned "no inventory" into "$4,420 of inventory."

---

## 1. Current state (verified, not assumed)

### Two systems, zero shared keys

| | `sd_slabs` — "the engine" | `sd_slab_tracker` — "the panel" |
|---|---|---|
| Record fields | `id`, `material`, `colorName`, `supplier`/`vendor`, `lotNumber`, `thickness`, `finish`, `lengthIn`, `widthIn`, `totalSqft`, `usableSqft`, `costPerSqft`, `yardLocation`, `externalBarcode`, `consignment`, `notes`, `status`, `photo_base64`, `reservedFor`, `addedAt`, `consumedAt`, `yieldPercent`, `isRemnant`, `parentSlabId` | `id`, `stone`, `vendor`, `size`, `thickness`, `finish`, `status`, `location`, `cost`, `job`, `notes` |
| Status values | `in-stock`, `consumed` | `Available`, `Allocated`, `Cut`, `Remnant` |
| Server sync | **yes** — `sd_slabs` table via the `slabs` resource | **no** — localStorage only |
| Real persisted data | yes | **none** — seed constant only |
| Remnant lineage | yes — `isRemnant` + `parentSlabId` | status label only, no lineage |
| Has a UI | **no** (management UI removed as dead code) | yes — the Slabs panel |
| Read by | Quote Builder slab picker, POS, Visualize-on-Your-Kitchen, low-stock dashboard alert, customer detail | the Slabs panel only |

The two shapes share **zero keys**. This is not a near-miss merge.

Prior sessions split these off a shared key after they clobbered each other,
and explicitly logged unification as unresolved
(`STONEDESK-SESSION72-HANDOFF.md`). This design resolves it.

### The real DDL (`sd_slabs`, from Supabase information_schema)

```
id            uuid         NOT NULL  default gen_random_uuid()
license_hash  text         NOT NULL
app_id        text         NOT NULL  default 'stonedesk'
slab_id       text         NOT NULL
data          jsonb        NOT NULL  default '{}'
created_at    timestamptz  NOT NULL  default now()
updated_at    timestamptz  NOT NULL  default now()
```

Plus, confirmed from the code that enforces them rather than from
`pg_constraint`: unique on `(license_hash, slab_id)`, and a
`sdslabs_data_size` CHECK capping `data` at **65536 bytes**.

### The constraint that decides the architecture

`BSU_PHOTO_BUDGET_BYTES = 55 * 1024`. A slab photo is compressed to fit
**55KB of the 64KB blob**. Existing non-photo fields consume roughly another
0.5KB. **Actual headroom for anything new is ~9KB per slab.**

`api/sd-data.js` records that a slabs-specific 500KB override was already
tried in 2026-08-04, passed the API layer, and was rejected by Postgres with a
much less clear error. There is no per-resource override at the DB layer. The
ceiling is real and cannot be raised locally.

---

## 2. Unification design

### 2.1 `sd_slabs` becomes the single source of truth

The Slabs panel is repointed at `sdSlabs`. `sd_slab_tracker` is retired.

**The `SEED` constant is deleted outright, not made conditional.** A panel
whose store is empty shows an honest empty state — "No slabs in inventory yet.
Add one, or use Bulk Slab Upload." — and KPIs read `0` / `0` / `0` / `$0`.
Inventing inventory to make an empty screen look populated is the defect being
fixed; a `sdDemoCleared()`-style toggle would leave the same landmine behind a
flag.

### 2.2 No data migration is required, and that is a verified finding

`sd_slab_tracker` holds **no persisted records anywhere** — its key is absent
and its only content is a seed constant. There is no second dataset to
preserve, merge, or reconcile.

The one-time carry-forward path already in `load()` (which rescued
`stone`-shaped records from `sd_slabs` back in Session 72) **must be retained
for one release**, not deleted with the rest: any user whose browser still
holds tracker-shaped rows under `sd_slab_tracker` from before this design
needs them surfaced rather than silently dropped. Treat those rows as
**import candidates presented to the user**, never as auto-migrated
inventory — they were never real synced stock, and silently promoting fake or
half-entered rows into the real, server-synced, Quote-Builder-visible
inventory is a worse outcome than asking.

### 2.3 Field mapping (UI columns → engine fields)

The panel's columns are re-sourced; no data is transformed on disk.

| Panel column | Engine source |
|---|---|
| ID | `id` |
| Stone | `colorName` (fall back to `material` label) |
| Vendor | `supplier` \|\| `vendor` |
| Size / Finish | `lengthIn`×`widthIn` composed for display, + `finish` |
| Location | `yardLocation` |
| Status | `status` (see 2.4) |
| Cost | `costPerSqft` × `usableSqft`, shown as computed, not stored |
| Job | `reservedFor` |

`size` was a display string (`"120x60"`) in the tracker and is real numeric
`lengthIn`/`widthIn` in the engine. Composing the string for display is
lossless; parsing it back would not be, which is one more reason the engine
shape wins.

### 2.4 Status vocabulary — additive reconciliation

The engine ships `in-stock` and `consumed`. The target vocabulary is
`available / held / sold / cut / broken / lost`. These are reconciled
**additively**: existing values keep working, new values are added alongside.

| Existing | Target | Rule |
|---|---|---|
| `in-stock` | `available` | `in-stock` continues to be accepted and read as `available` |
| `in-stock` + `reservedFor` set | `held` | derived, not stored — a reserved slab is held |
| `consumed` | `cut` | `consumed` continues to be accepted and read as `cut` |
| — | `sold`, `broken`, `lost` | genuinely new, no existing rows carry them |

**No existing `status` string is rewritten on disk.** A reader normalises on
read (`in-stock`→`available`, `consumed`→`cut`). This is what makes the
unification reversible: revert the UI and every record still carries the value
the old engine wrote.

`Allocated` and `Remnant` from the tracker vocabulary do **not** become
statuses. `Allocated` is `reservedFor` being non-empty; `Remnant` is
`isRemnant === true`. Both are already modelled as their own fields, and
collapsing them into `status` would lose the ability to express "a remnant
that is currently reserved."

---

## 3. Block / bundle lineage layer

Zero matches exist today for `blockId`, `bundleId`, `block_id`, `bundle_id`.
This layer is genuinely new. The existing chain is slab→remnant only.

### 3.1 The decision: sibling tables, not the existing blob

**Block and bundle records, and slab history, live in new sibling resources.
Only two short foreign keys go into the existing slab blob.**

Given ~9KB of real headroom per slab, the alternatives fail concretely:

- **Block/bundle metadata denormalised into each slab's blob** — block origin,
  quarry, purchase order, arrival date, block photos duplicated across every
  slab cut from that block. Multiplies a fixed-ceiling problem by slab count,
  and updating one block fact means rewriting every slab in it.
- **Full status history in the blob** — history is unbounded by nature. A slab
  that is received, moved between bays four times, reserved, released,
  reserved again, consumed, and spawns two remnants accumulates a dozen-plus
  events. At ~150 bytes each that is 2KB+ of a 9KB budget, growing forever,
  with a hard failure at the end of it. A record that gets *more* likely to
  fail the longer it is used is the wrong shape.
- **Sibling tables** — block facts stored once, history unbounded without
  threatening the slab record, and (decisively) **queryable**. Vein-matching
  across a job asks "give me every slab from block X" — answerable with an
  indexed sibling row, not answerable by scanning per-row jsonb.

What goes into the existing slab blob is exactly two optional string fields,
roughly 60 bytes total:

```
blockId   : 'BLK…' | absent
bundleId  : 'BND…' | absent
```

Both optional. A slab with neither is a valid slab — which is what every
existing row is today, and what a directly-purchased remnant will always be.

### 3.2 New resources

Following the established `sc_pctc` / `sc_dme` pattern exactly: one row per
entry, `license_hash`-scoped, jsonb `data`, registered in
`api/_resources/shared.js` (StoneDesk-scoped naming, `sd_` prefix) with a
handler branch in `api/sd-data.js`, plus a checked-in SQL file — which
`sd_slabs` itself notably lacks and should get retroactively.

- **`sd_blocks`** — one row per quarry block. Fields: `id`, `quarryName`,
  `blockNumber`, `material`, `origin`, `purchaseOrder`, `arrivedAt`, `notes`,
  `photo_base64` (same 55KB compression path).
- **`sd_bundles`** — one row per bundle. Fields: `id`, `blockId`, `bundleNumber`,
  `slabCount`, `thickness`, `finish`, `receivedAt`, `notes`.
- **`sd_slab_history`** — one row per event. Fields: `id`, `slabId`, `at`,
  `event` (`received`/`moved`/`reserved`/`released`/`consumed`/`remnant_spawned`/
  `status_changed`/`sold`/`broken`/`lost`), `from`, `to`, `employeeId`, `note`.

Lineage is then: **block → bundle → slab → remnant**, with the existing
`parentSlabId` chain untouched and extended rather than replaced. A remnant
inherits `blockId`/`bundleId` from its parent at spawn time — which is exactly
what makes vein-matching survive consumption, the stated goal.

### 3.3 Why history is a table and not an array in the blob

Stated separately because it is the decision most likely to be "simplified"
later by someone who sees an empty table and thinks an array would do: the
array works fine until a slab has been handled enough times to matter, and
then it fails at the DB layer on the records with the most operational
history — the busiest, most valuable slabs, and the ones whose provenance
someone is most likely to be auditing when it breaks.

---

## 4. Reversibility — the explicit mechanism

Three changes, three distinct rollback stories. None is "fails closed" alone.

### 4.1 Unification (panel repoint + SEED removal) — UI-layer revert

**Risk to real data: none.** Verified: the tracker key holds nothing, so
nothing is deleted, transformed, or overwritten. The engine's records are read
in their existing shape with no on-disk mutation — status normalisation
happens on read.

**Rollback:** `git revert` of the panel commit restores the previous panel
verbatim, including its seed. No data step, no migration to unwind, no user
action. The only thing lost by reverting is the fix.

**Proving it before relying on it:** the release ships with the engine's
`sd_slabs` untouched. If the new panel is wrong, reverting returns to exactly
today's state — a panel showing fabricated data, which is bad, but is not
*worse* than today, and no real slab has been altered to get there.

### 4.2 Block/bundle layer — additive, with a stop-writing rollback

**Additive by construction.** Existing slab records gain two optional keys;
nothing existing is renamed, retyped, or removed. Every current reader
(Quote Builder picker, POS, visualizer, low-stock, customer detail) reads
`id`/`material`/`colorName`/`status`/`usableSqft`/`reservedFor` and is
untouched by the addition — unknown keys are ignored by all of them.

**Rollback, in order of severity:**
1. **Stop writing.** Revert the UI commit. `blockId`/`bundleId` remain on
   whatever rows already carry them and are simply not read. Slabs continue
   to function exactly as they do today. This is the expected rollback and it
   requires no data change at all.
2. **Strip the keys.** If the shape itself proves wrong, a one-pass client-side
   sweep removes `blockId`/`bundleId` from each slab and re-syncs. Safe
   because both are optional and no logic depends on their presence.
3. **Drop the tables.** `sd_blocks` / `sd_bundles` / `sd_slab_history` are new
   and referenced by nothing else. Dropping them cannot orphan an existing
   slab, because the relationship is stored slab-side as a plain string, not
   as a DB foreign key. A dangling `blockId` pointing at a dropped table
   degrades to "no block info," not to an error.

**The old shape stays intact and queryable throughout.** At no point does a
slab record stop being a valid pre-Phase-1 slab record.

### 4.3 The one genuinely irreversible act, named

Deleting the `SEED` constant. It cannot be un-deleted by a data rollback
because it was never data — it is source. `git revert` restores it, which is
the only reversal needed, and the only reason to want it back would be a
demo script that relies on fake inventory. **If such a demo path exists it
must be found before this ships**, and if it does, it belongs behind an
explicit "load demo data" button that writes real rows to `sd_slabs` — never
behind an empty-store fallback that cannot be distinguished from real stock.

---

## 5. Migration path for real data

The only real slab data is whatever sits in `sd_slabs` today. It requires
**no transformation** — the panel is moving to it, not it to the panel.

- No field is renamed, retyped, or dropped.
- Status normalisation is read-side only.
- Records written before Phase 1 and after are the same shape, minus two
  optional keys the older ones simply lack.
- Nothing is invented. A slab with no `blockId` displays no block, not a
  placeholder block.

**Test-data note:** the `SLAB-VERIFY-001` record created during Step 1
verification was written with `saveSlabs()` only and **never** through
`slabSyncOne()`, so it exists solely in the local test browser's localStorage
and never reached Supabase. No production cleanup is required. Confirmed
rather than assumed.

---

## 6. Sequencing recommendation

The fabricated-KPI defect is live and the lineage layer is not urgent. Split:

- **Phase 1a — the honesty fix.** Repoint the panel at `sd_slabs`, delete
  `SEED`, build the real empty state, compute KPIs from real data, retain the
  tracker-row import prompt. Small, revert-able, closes the Check 0b violation
  and Finding 3 together. No new tables, no new resources, no SQL.
- **Phase 1b — the lineage layer.** Three new resources, three SQL files, the
  two optional slab keys, the block/bundle UI. Larger, independently
  revert-able, and it lands on a panel that is already telling the truth.

Shipping 1b first would build lineage on top of a panel that displays invented
inventory, and every screenshot of the new feature would contain fabricated
slabs.

---

## 7. Open items, flagged not assumed

1. **`sd_slabs` has no checked-in SQL file.** The table exists in Supabase and
   is now documented above from `information_schema`, but the repo has no
   `sql/sd_slabs*.sql`. It should get one retroactively as part of 1a so the
   constraint set stops living only in an API comment.
2. **A demo/seed path may exist elsewhere.** `SAFE_DEMO_KEYS` includes
   `sd_slab_tracker`, and `sdDemoCleared()` gates the seed. Before deleting
   `SEED`, confirm whether any sales-demo flow depends on it — §4.3.
3. **`slabOpenConsume()` dead code** with mismatched `-b` ids — deferred per
   Michael, not folded into this migration.
4. **The seed-fallback pattern is not isolated to slabs — it is pervasive.**
   Counted, not estimated: `stonedesk.html` contains **29 `SEED` constants**
   and **56 occurrences of the `sdDemoCleared() ? [] : SEED` fallback**. The
   Slabs panel is one instance of a pattern used across the file.

   This does **not** mean 55 more live defects. The `sdDemoCleared()` guard
   exists precisely to suppress seeds once a user clears demo data, so most
   sites are probably behaving as intended. What the slab case proves is that
   the guard is **not sufficient on its own**: a user who never explicitly
   cleared demo data, on a panel whose real store is empty, sees invented
   records rendered as real and gets KPIs computed from them.

   The distinguishing question per site is: *can this panel's real store be
   empty while `sdDemoCleared()` is false, and does the panel compute a
   number from what it shows?* Where both are true, it is the same defect.

   That sweep is **out of scope for Phase 1** and should not be folded into
   this migration — but it is a real, sized finding that deserves its own
   task, and it is the strongest available argument for the sixth Guardian
   lesson Michael already flagged. StoneDesk is very unlikely to be the only
   app with this shape.
