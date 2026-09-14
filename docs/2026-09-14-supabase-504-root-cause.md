# The Supabase 504s are one cause with three victims — and the fix IS in this repo

**2026-09-14 (Hank).** Asked to check whether the `api/claude` rate-limiter 504
shares a root cause with CC's cron 504 findings rather than being a second
issue. It does, and finding that changed the owner of the problem.

**The headline, and it corrects a standing row.**
`docs/SAIRN-OPEN-WORK-INDEX.md` records the cron failures as
*"Michael — nothing in this repo can fix a gateway timeout"* and *"needs
somebody on the Supabase side."* **That was a reasonable reading of a 504 and it
is wrong.** Both crons issue a query that cannot use an index, one of them
unbounded and growing daily. The database is not answering in time because it is
being asked to scan. **The fix is a filter and an index, in this repository.**

Nothing has been changed. See §6 for why I stopped at a report.

---

## 1. What was already known

CC, 2026-09-13: both hourly crons failing, **19 of 48 firings in 24 hours
(40%)**, upstream status 504 from Supabase.

- `GET /api/sairndental/send-reminder` → 502, logging
  `dnt_appointments list failed 504 {"message":"Gateway Timeout"}`
- `GET /api/alf-alerts` → 502, logging `facility sweep read failed, HTTP 504`

Mine, 2026-09-14: `api/claude`'s rate limiter logging
`atomic RPC failed, HTTP 504 -- falling back to the racy path`, on a completely
unrelated endpoint with a completely unrelated query.

Three symptoms, one status code, and no reason yet to think they were connected.

## 2. The timing says one window, not three faults

Every 504 in the observed period lands in the **same ~30 seconds after the top
of the hour**, which is when both crons fire:

| Time (UTC) | Endpoint | Result |
|---|---|---|
| 08:00:29 | send-reminder | 504 |
| 08:00:43 | alf-alerts | 504 |
| 09:00:43 | alf-alerts | 504 |
| 10:00:03 | api/claude (probe) | **clean** — before the crons started |
| 10:00:29 | send-reminder | 504 |
| 10:00:51 | api/claude (probe) | **504** — after the crons started |
| 10:01:34 | api/claude (probe) | clean |
| 10:01:37 | api/claude (probe) | clean |

**`api/claude` is collateral, not a third fault.** The same endpoint, the same
payload, 48 seconds apart, straddling the cron start: the one inside the window
timed out and the one outside did not. Its own two 504s ever — 2026-09-13
22:00:41 and 2026-09-14 10:00:51 — are both at `:00:4x`.

**Rate, re-measured over the last 12 hours** rather than carried from CC's
figure: 11 × 502 against 21 × 200 across 34 requests, which for 12 hourly
firings each is **send-reminder 6/12 (50%) and alf-alerts 5/12 (42%)**. CC's
40% over 24h yesterday; no better today.

## 3. Why the database cannot answer in time — read from the code

### `send-reminder`: a cross-tenant scan on two unindexed columns

`api/sairndental/send-reminder.js:128`

    dnt_appointments?status=eq.Confirmed
                    &start_time=gt.<now>&start_time=lte.<now+48h>
                    &select=license_hash,appointment_id,data,...

**There is no `license_hash` filter at all** — it deliberately sweeps every
tenant, which is correct for a reminder cron. But the only declared index on the
table is:

    idx_dntap_license on public.dnt_appointments(license_hash)

So it filters on `status` and `start_time`, and **neither is indexed**. The 48h
window bounds the *result*, not the *work*: the planner still has to scan the
table to find those rows.

### `alf-alerts`: the whole medication history, every hour, forever

`api/alf-alerts.js:69`

    async function loadMar(licHash, dayStr) {
      ... rest('alf_mar?license_hash=eq.' + enc(licHash)
               + '&select=entry_id,resident_id,entry_type,data')

**`dayStr` is never used in the query.** It appears exactly once, at line 95,
filtering *in JavaScript after the rows have crossed the wire*:

    administrations.filter((a) => a.day === dayStr)

The function's own comment says it pulls *"the active, reviewed medication
orders and the day's administrations"*. It pulls **every `alf_mar` row that
licence has ever written**, and throws away all but one day of it. `alf_mar` is
an append-only medication administration record: it grows every day and never
shrinks, so **this query gets slower every day and will not stop**. Its indexes
are `license_hash`, `(license_hash, resident_id)` and
`(license_hash, assigned_employee_id)` — none on `entry_type`, none on
`created_at`, which are the two columns a bounded version would need.

**This also explains the shape of the failure better than a Supabase incident
does.** An outage is intermittent and indifferent to the clock. A scan that
grows daily produces exactly what is observed: a rising failure rate, clustered
at the moment two heavy sweeps collide, that takes other queries down with it.

## 4. The test, not another observation

Five 504s at the top of the hour is a pattern; it is not evidence of causation,
and a sixth would not have been either. So a **paired probe** fires the same
request twice in one hour — once at `:00:50`, inside the window, once at
`:05:30`, outside it. One degrades and the other does not, or the hypothesis is
wrong and says so.

**The first version of that probe returned immediately and tested nothing.** Its
wait loop asked `if t.minute > minute: return`, so starting at `:28` fired both
shots four seconds apart, both outside the window — two data points and zero
evidence. It was caught only because each shot prints its own timestamp. Fixed
to wait on a real future datetime; recorded here because a control that
silently does not run is the failure this platform is already burning down in
23 of 39 negative controls.

> **RESULT: `PENDING` at the time of writing.** This section must be updated
> with the two log lines before the finding in §3 is treated as confirmed. §3
> stands on the code regardless — the query text and the index list are facts —
> but the *causal* claim in §2 is not confirmed until this pair comes back.

## 5. What the fix looks like

Neither of these needs Supabase support.

**`send-reminder`** — an index matching the query:

    create index if not exists idx_dntap_due
      on public.dnt_appointments (status, start_time);

**`alf-alerts`** — two scoped reads instead of one unbounded one. Standing
orders are not time-bounded and must still be read in full; administrations are:

    alf_mar?license_hash=eq.<h>&entry_type=eq.medication_order&select=...
    alf_mar?license_hash=eq.<h>&entry_type=eq.administration
           &created_at=gte.<start of day, with a margin>&select=...

plus `create index ... on public.alf_mar (license_hash, entry_type, created_at)`.

**One caution that decides whether this is safe.** The JavaScript filter uses
`a.day`, a field **inside the JSON**, not `created_at`. Those are different
clocks: an administration recorded just after midnight for the previous day
carries `data.day = yesterday` and `created_at = today`. Filtering on
`created_at` is a *superset* of what the JS filter then narrows, so the day
margin has to be generous enough that no administration for today can have been
created before the cutoff. Getting that margin wrong **drops a late-medication
alert**, which is the whole point of the cron.

## 6. Why I stopped here

**`alf_mar` is a medication administration record in a regulated app, and this
cron is the thing that notices a late dose.** Changing which rows the alerting
logic can see is a Tier A change on a safety-adjacent path, and the correct
margin in §5 is a judgement about how SAIRNcare records administrations, not
something to infer from a schema. A wrong guess here does not throw an error —
it silently stops alerting on a real late medication, which is the exact
silent-failure shape this platform exists to catch.

So: root cause identified, fix specified, nothing edited.

## 7. What this does NOT claim

- **The causal link is timing plus code, not a Supabase-side measurement.** I
  cannot see query plans, table sizes or database load from here. An alternative
  reading — a Supabase-side job at the top of every hour — is not excluded by
  what is above, though it does not explain why the two heaviest queries on the
  platform are the ones that fail.
- **`alf_mar`'s actual row count is unknown.** The unbounded *shape* is read
  from the code; that it is *already large enough to time out* is inferred from
  the failures, not measured.
- **n is small.** Eight 504s over three hours, plus 11 over twelve, plus one
  probe pair. The 12h rates in §2 are real counts, not projections.
- **`api/claude`'s own RPC has not been shown to be slow.** It is fast enough
  outside the window; nothing here says it would survive a busier platform.
