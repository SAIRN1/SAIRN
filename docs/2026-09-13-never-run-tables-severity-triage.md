# The 26 never-run tables — triaged before they are ranked

**2026-09-13 (CC).** `tools/schema_snapshot_freshness.py`, against a snapshot
captured **2026-09-13 18:39 UTC** — 3.7 hours old at the time of this pass, not
the stale 2026-09-11 capture the earlier never-run analysis had to be corrected
for. **85 tables declared in `sql/` are absent from the live schema; 26 of them
are queried by live `api/` code.**

The instruction was to triage severity **before** calling this urgent or
routine. That is what this is. **Nothing here was changed and no migration was
run** — none can be, from a session.

---

## The finding that decides the whole triage, and it is not about the tables

**There is no measurable customer traffic on this platform, so "is this table hit
by real customer licence traffic" cannot be answered YES for any of the 26 — and
that is a fact about the traffic, not about the tables.**

Measured from Vercel production runtime logs, the last 24 hours, grouped by
status and by path:

| status | count | what it actually is |
|---|---|---|
| 200 | 30 | **29 are the two hourly crons.** The other **one** is `/api/claude`. |
| 502 | 19 | both hourly crons, failing (see the urgent finding below) |
| 405 | 18 | `GET` against POST-only routes, all inside **one 10-second burst** at 12:20 — a route sweep, ours |

**Successful non-cron requests in 24 hours: one.** The 72-hour window tells the
same story: 13 of 64 routed endpoints were observed at all, and `/api/sd-data`'s
71 hits — the largest non-cron figure and the endpoint that serves 18 of these
26 tables — resolve to **405s from that GET sweep**, not resource reads.

**So no row below can be ranked by observed traffic.** Everything that follows
ranks by *what happens when someone does arrive*, which is the only question the
evidence can answer. Same limit as `sairn_reachability_check.py --activity`
reports for its own denominator, for the same reason: when almost everything
sees zero, one thing seeing zero is not evidence about that thing.

---

## Axis 1 — reachability class: who can reach it at all

Derived by grepping the shipped app HTML for the **endpoint** each table sits
behind, not for the table name. A client never names a table; it names a
resource or a route, which is why six of these look unreferenced and are not.

| class | tables | who reaches it |
|---|---|---|
| **PUBLIC, NO LICENCE** | `sd_quote_request_photos` | `api/stonedesk-public`, called by **`stonedesk-intake.html`** — a public page. Anyone on the internet. |
| **AUTH GATE** | `mech_credentials` | `api/mech-auth`, called by `sairnmechanical.html`. **If it is missing, nobody can log in to that app at all.** |
| **LICENCE-GATED FEATURE** | the other 24 | a signed-in employee inside a shipped panel |

**None of the 26 is sitting behind an unlaunched feature.** That was the
hypothesis worth testing and it did not survive: every one has a shipped caller
in a live app file. The six whose table name appears in no HTML
(`accounting_connections`, `accounting_consents`, `ledger_entries`,
`ledger_lines`, `sairn_style_profiles`, `sd_supplier_lead_times`,
`sairnscape_org_intel`, `sd_quote_request_photos`) reach their endpoints from
`stonedesk.html`, `sairnscape.html`, `sairnbiz.html` and `stonedesk-intake.html`
respectively.

---

## Axis 2 — failure loudness, which is the real severity driver here

Given Axis 1 answers "when they arrive", what matters is what a user sees. Two
shapes exist in the code, and they are not equivalent:

- **HARD** — `503 NOT_PROVISIONED`, with a message naming the SQL file to run.
  `api/sd-data.js` carries 166 of these. A user sees an error that says what to
  do.
- **SOFT** — `200 OK` with `{ data: [], provisioned: false }`. The failure is
  *recorded* in a flag, and it renders as **an ordinary empty list** unless the
  client reads that flag.

**Six of the 26 have only the SOFT shape near every query:**

| table | app | why it matters |
|---|---|---|
| **`ledger_entries`** | SAIRNbiz | **the sharpest of the six.** A LEDGER showing zero entries reads as "no transactions", not "not set up". `sairnbiz.html` reads a provisioned flag **twice** in the whole file. |
| `rf_bonding` | SAIRNroofing | read by hand and confirmed: `if (r.status === 404 \|\| r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }) }` |
| `rf_job_hazard_assessments` | SAIRNroofing | a safety record rendering as "none on file" |
| `rf_prequal_documents` | SAIRNroofing | |
| `rf_safety_equipment` | SAIRNroofing | |
| `rf_warranty_tiers` | SAIRNroofing | |

**`sairnroofing.html` reads a `provisioned` flag 18 times**, which is the best
sign in this table and the reason the five roofing rows are not ranked with the
ledger — but 18 reads against five soft-guarded resources plus everything else
roofing does is not proof that *these* five are among them. **That is the check
worth doing next, and it is a read, not a migration.**

**A caveat on this axis, stated rather than buried:** guard proximity was
measured with a ±45/65-line window around each table mention, so a HARD guard
belonging to an adjacent branch can be credited to its neighbour. The six above
are the trustworthy half of that measurement — they have **no** HARD guard
anywhere near them — and `rf_bonding` was then read by hand to confirm the
shape. The rows marked HARD should be read before being relied on.

---

## The verdict

**ROUTINE, not urgent — with two exceptions to look at first.**

Routine, because: no customer traffic reaches any of them today; every one has a
shipped caller so none is abandoned code; and the majority fail loudly with a
message naming the migration to run. This is provisioning debt with a known fix
(`sql/` files that are all `create table if not exists` and therefore safe to
re-run), not a live outage.

**Exception 1 — `mech_credentials`.** It is the auth gate for SAIRNmechanical,
and it is a credentials table, which puts it in PR §3.4's class. A demo of that
app fails at the login screen, before anything else can be shown.

**Exception 2 — the six SOFT-200 tables, and `ledger_entries` above all.** A
missing table that renders as an empty list is the fabricated-empty-state shape
this platform has recorded repeatedly. The fix is not necessarily the migration:
it is confirming the client honours `provisioned: false`.

---

## AND THE URGENT THING FOUND ON THE WAY IS NOT ANY OF THE 26

**Both hourly crons are failing in production right now, and have been for at
least 24 hours.**

```
/api/sairndental/send-reminder 502   send-reminder: dnt_appointments list failed 504 {"message":"Gateway Timeout"}
/api/alf-alerts                502   alf-alerts: facility sweep read failed, HTTP 504
```

**19 of 48 cron firings in the last 24 hours returned 502 — 40%.** The upstream
status is **504 from Supabase**, so this is not a missing table and not a code
change; it is the database not answering in time.

**Guardian check 30 exists because this exact cron sent ZERO reminders for
months** while returning 500 every hour on a misnamed env var. The failure mode
is loud in the logs and completely silent to anyone not reading them — which is
how the first one lasted months.

**This outranks all 26 tables and is a separate row.** It needs somebody who can
look at the Supabase side; nothing in this repo can fix a gateway timeout.

---

## How to re-derive any of this

```
python tools/schema_snapshot_freshness.py            # the 26, with the capture age
python tools/sairn_reachability_check.py --activity  # the traffic denominator
```

Production status and path counts: Vercel MCP `get_runtime_logs` with
`group_by='statusCode'` and `group_by='requestPath'`, `since='24h'`. **72h
returns; 7d timed out and 30d returned 400**, so three days is the practical
ceiling and every traffic statement here expires with it.
