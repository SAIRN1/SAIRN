# StoneDesk public storefront — the migration is ready to run, and here is the proof it is correct

**2026-09-12 (CC).** Closes the verification half of the
`SAIRN-OPEN-WORK-INDEX.md` row *"The entire public storefront has NO TABLES"*.
**The run itself is still Michael's** — see *What I could not do* at the bottom,
stated plainly rather than left to be inferred from an absence.

## 1. The finding is still true today, from two independent sources

The original finding is from 2026-09-04 and was made from endpoint probes alone.
Both checks below were run on 2026-09-12, eight days later, and they do not share
a mechanism.

**Live probe** (`tools/sairn_http.py`, browser-shaped headers — a bare `curl`
would have been answered with a Vercel challenge and that is not an answer):

| request | answer |
|---|---|
| `POST /api/stonedesk-public` `{action:catalog}` | `503 UNAVAILABLE` |
| `POST /api/stonedesk-public` `{action:quote_request}` | `503 UNAVAILABLE` |
| `POST /api/stonedesk-track` `{action:view}` | `503 NOT_PROVISIONED` |

`UNAVAILABLE` is `checkAndIncrementRateLimit()` failing closed on a counter it
cannot read — i.e. `sd_public_rate_limits` is not there. `NOT_PROVISIONED` is
`stonedesk-track.js`'s own name for a PostgREST 404/400 on `sd_order_links`.

**The schema snapshot**, re-captured 2026-09-11 (`3d603dd0`) and therefore *not*
the stale capture the original finding could have been accused of resting on.
All five tables absent, plus `sd_quote_request_photos` from the sibling
migration. `tools/schema_snapshot_freshness.py` lists all six.

**This matters because the two could have disagreed.** A 503 alone is consistent
with an outage; an absence from a snapshot alone is consistent with a stale
capture. They agree, and neither explanation survives the other.

## 2. Every column the code needs exists in the file — checked, not assumed

The expensive failure mode for a hand-run migration is not "it did not run", it
is "it ran and one column is spelled differently". So every consumer was read
and every column, filter, `on_conflict` target and grant verb was traced to a
declaration in `sql/stonedesk_public_surface_schema.sql`.

| consumer | table | columns used | verdict |
|---|---|---|---|
| `api/_lib/stonedesk-public.js` `resolveShopSlug` | `sd_public_shop` | filter `shop_slug`, `published`; select `license_hash, shop_slug, data` | all declared |
| `api/_lib/stonedesk-public.js` limiter | `sd_public_rate_limits` | filter `ip_hash`, `window_start`; select `count`; upsert `on_conflict=ip_hash,window_start` | `unique (ip_hash, window_start)` present, so the conflict target resolves |
| `api/stonedesk-public.js` quote | `sd_quote_requests` | insert `license_hash, app_id, request_id, status, data` | all declared |
| `api/stonedesk-track.js` view/create/revoke/list | `sd_order_links` | `link_token, id, license_hash, job_id, label, active, link_id, app_id, created_at, last_accessed_at, revoked_at` | all eleven declared |
| `api/stonedesk-track.js` view/create | `sd_customers` | filter `license_hash`, `customer_id`; select `data`, `customer_id` | all declared |
| `api/sd-data.js` staff branches | `sd_public_shop` | upsert `on_conflict=license_hash`, writes `shop_slug, published, data, updated_at` | `unique (license_hash)` present |
| `api/sd-data.js` staff branches | `sd_customers` | upsert `on_conflict=license_hash,customer_id`, writes `updated_at` | `unique (license_hash, customer_id)` present |
| `api/sd-data.js` staff branches | `sd_quote_requests` | `PATCH` by `license_hash` + `request_id`, writes `status, data, updated_at` | `unique (license_hash, request_id)` present |

**Zero mismatches.** Two things worth naming because they are the ones that
usually bite:

- **The `update` grant is there.** All five tables carry
  `grant select, insert, update`. PostgREST resolves `Prefer:
  resolution=merge-duplicates` at plan time and needs `update` even on a row
  that does not exist yet — the exact verb whose absence took `sairncash_waitlist`
  down on 2026-08-26.
- **`sd_public_shop` has two unique constraints doing different jobs.**
  `unique (license_hash)` is the upsert target; the partial
  `idx_sdps_slug ... where shop_slug is not null` is what makes a taken slug a
  409, which `sd-data.js` already maps to `SLUG_TAKEN`. Neither substitutes for
  the other.

`python tools/sairn_sql_preflight.py --live db/schema_snapshot.json` reports the
file **clean, 5 tables**. All five storefront test suites pass
(`intake_form_public_surface`, `public_catalog_no_false_empty`,
`stonedesk-public.test`, `stonedesk-track.test`, `_lib/stonedesk-public.test`).

## 3. One file, not two — checked, because I first thought otherwise

`api/stonedesk-public.js` also writes `sd_quote_request_photos`, which lives in
`sql/stonedesk_intake_photos_2026-09-03.sql` and is *also* absent. That looked
like a second required file hiding behind the first.

**It is not, and the check is why.** `stonedesk-catalog.html` renders slab and
remnant photos but posts none; the only surface that posts photos is
`stonedesk-intake.html`, which is gated behind `INTAKE_FORM_LIVE = false`. So the
photo write is unreachable today. The photos migration stays where it belongs —
the separate index row that already owns it, gated by that flag.

Recorded because the near-miss is the useful part: a quote request carrying
photos against an unrun photos table does **not** fail loudly. It logs, returns
`photos_saved: 0`, and accepts the lead. A customer's kitchen photos would
vanish while the shop got the enquiry.

## 4. Confirming the run is now mechanical

`tools/stonedesk_storefront_live_check.py` — report-only, no credentials, exit 1
today and exit 0 once the tables exist.

**It confirms three of five, and says so on every run including a passing one.**
Unauthenticated probes cannot reach `sd_quote_requests` (the quote action stops
at the slug lookup) or `sd_customers` (the track action stops at the link
lookup). A tool that printed "PROVISIONED" off three tables would be the
confident-wrong-answer shape this platform keeps finding.

It also distinguishes **NOT ASKED** from **ABSENT**. The limiter runs before the
slug lookup and fails closed, so while the counter is down the catalog probe
never asks about `sd_public_shop` at all. The first version printed that as
ABSENT — a not-asked rendered as a measured absence, which is the same defect
class as a failed read rendered as an empty list, found by reading the tool's own
output rather than its code. Only a measured `LIVE` can produce exit 0.

Its negative control is the live world: it reports ABSENT today, correctly, so it
is not a check that passes vacuously.

## What Michael needs to do

1. Run `sql/stonedesk_public_surface_schema.sql` in the Supabase SQL editor.
   Additive and idempotent.
2. `python tools/stonedesk_storefront_live_check.py` — expect exit 0.
3. Re-run `sql/schema_snapshot_query.sql`, **save** the JSON cell as
   `db/schema_snapshot.json`, commit it, then
   `python tools/schema_snapshot_freshness.py`. This is what settles the
   remaining two tables. The save-and-commit step is the one that went missing
   on 2026-09-10.

## What I could not do, and why

**I cannot run the migration from this session.** There is no
`SUPABASE_SERVICE_ROLE_KEY`, no `DATABASE_URL`, no `.env` anywhere in the clone,
and no `psql` or `supabase` CLI on the machine — checked, not assumed. The
service key exists only in Vercel's environment. Supabase's REST API executes no
DDL, so there is no route to it through any endpoint this platform exposes. The
index row's owner column has said **Michael** since 2026-09-04 and that is
correct.

## Unrelated, found in passing and deliberately not fixed

`sairn_sql_preflight.py --live` reports exactly one finding across the whole
repo: **`rf_draws.rfdraw_released_not_negative` is declared in `sql/` and is not
present on the live table.** SAIRNroofing, a money table, a constraint about a
released draw amount not going negative. Nothing to do with this row; not
touched, not investigated. Naming it here so it is not lost.
