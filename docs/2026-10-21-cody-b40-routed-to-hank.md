# cody b40 → hank: the owner WRITE path for SAIRNlegacy F2/F3 settings

Routed on Michael's decision, 2026-10-21 (b40 item 4): close F2/F3 wiring as
done (b29), and send the owner write path to hank, because `api/` is hank's
directory and the work had already been routed there (`api/sd-data.js` ~16925
comment: "ROUTED BACK TO hank: add the row, then this entry").

## What is live (verified b40, nothing changed)
- `api/sd-data.js:~17080–17118` reads `sairnlegacy_settings` (and its
  `livery_grants` column, if present) and calls
  `legRoles.decide(resource, role, action, legGrants, legHome)` with all five
  arguments.
- `api/b22-funeral-f1-f2-f3-wiring.test.js` 23/0, `api/b29-funeral-f2-f3.test.js`
  21/0, `api/sd-data-leg-overlap.test.js` 36/0.

## What is missing
**No path in the app lets an owner SET the per-home F2/F3 values.** A home can only
change `livery_billing`, the apprentice policy, or `livery_grants` by SQL. So the
locked answer "F3 apprentice clearance owner-configurable" is not true from the app
yet. Every home runs on the narrow defaults: livery `through_the_home`, which
grants nothing, and an empty apprentice countersign list.

## What the write path needs (as found, not designed)
1. A registered resource row in `api/_resources/sairnlegacy.js`. Today
   `leg_settings` is absent, so `checkEnvelope()` answers 400.
2. A handler for `sairnlegacy_settings`, the real table name, which has no `data`
   column (see `sql/sairnlegacy_settings_schema.sql`), restricted to owner/admin.
3. Normalise before storing, with the same functions `decide()` uses:
   `liveryBilling()` and `apprenticePolicy()` in `api/_lib/leg-roles.js`.
   `leg_liveryvendors` must stay ungrantable under every setting (b22 arm B2).
4. `livery_grants` needs `sql/sairnlegacy_settings_livery_grants.sql`, which has
   not been run.
5. It is a Tier A change: open the obligation.

## Also stale, for whoever touches it
The comment at `api/sd-data.js:~17166` ("NOTHING STORES IT ... no SAIRNlegacy
settings table anywhere") predates the b29 read 50 lines above it. It is left
alone on Michael's b40 decision.
