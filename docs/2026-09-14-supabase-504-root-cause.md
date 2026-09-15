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

> **RESULT: INCONCLUSIVE — and the reason is a flaw in the test, not in the
> hypothesis.** Both shots came back clean: `11:00:50` in-window and `11:05:32`
> out, neither logging `atomic RPC failed`.
>
> **That is not a refutation, because the window did not exist that hour.**
> Checked before drawing any conclusion: **zero 502s across the whole 25-minute
> span containing 11:00** — both crons succeeded. There was nothing to land in.
>
> **THE DESIGN CONDITIONED ON SOMETHING THAT HAPPENS IN ABOUT HALF OF HOURS AND
> DID NOT RECORD WHETHER IT HAD HAPPENED.** The crons fail 5–6 times in 12; a
> single-hour test can therefore only answer on a coin flip, and I did not build
> in the one variable that says whether the coin came up — the cron outcome for
> that same hour. Asked the right question with an underpowered instrument.

**What the two hours together do say, stated at the strength it deserves:**

| Hour | Crons that hour | `api/claude` in-window |
|---|---|---|
| 10:00 | **failed** (send-reminder 504 at 10:00:29) | **timed out** at 10:00:51 |
| 11:00 | **succeeded** (zero 502s) | **clean** at 11:00:50 |

Two hours, consistent in both directions, and the 11:00 hour is a **negative
control I did not previously have** — window absent, no timeout. It is n=2 and
it is not confirmation. Three more shots at `:00:50` are running, each to be
paired with that hour's cron outcome; an hour with no cron 502 yields **no
data** and is counted neither way.

### 4a. Two more hours, and the collateral-damage claim does not survive them

| Hour | send-reminder | alf-alerts | `api/claude` at `:00:5x` |
|---|---|---|---|
| 10:00 | **504** | **504** | **timed out** |
| 11:00 | ok | ok | clean |
| 12:00 | **504** | ok | clean |
| 13:00 | ok | **504** | clean |

**Both specific forms of the hypothesis are now refuted.**

- *"Any cron 504 saturates the database"* — refuted at **12:00**: send-reminder
  timed out and `api/claude` 25 seconds later was clean.
- *"`alf-alerts` specifically is the heavy one that takes others down"* —
  refuted at **13:00**: `alf-alerts` timed out and `api/claude` **13 seconds
  later** was clean. This was the narrower claim I had reported as 3-for-3 on
  three hours of data; the fourth hour broke it, which is what a fourth hour is
  for.

The only surviving form is *"it takes BOTH sweeps failing together"*, and that
rests on **one** observation — the 10:00 hour. At n=1 it is not distinguishable
from coincidence, and it should not be repeated as a finding.

### 4b. The experiment is closed. The answer is negative.

Shot 3 fired at `14:00:58`. **Both crons succeeded that hour, so it yields NO
DATA** — counted neither way, per the runner's own rule rather than as a
convenient reading after the fact.

| Hour | Cron outcome | `api/claude` | Verdict |
|---|---|---|---|
| 10:00 | both failed | **504** | the single supporting observation |
| 11:00 | both ok | clean | no data |
| 12:00 | send-reminder failed | clean | **refutes "any cron"** |
| 13:00 | alf-alerts failed | clean | **refutes "alf-alerts specifically"** |
| 14:00 | both ok | clean | no data |

**Five hours, two of them informative, and both of the informative ones point
against.** `api/claude`'s two 504s are not explained by cron contention and are
not explained by anything else here either. Whatever they are, they are rare —
two occurrences in about a dozen requests — and the endpoint answers 200 through
them because the limiter fails open by design.

**What I would do next if this is picked up again, and deliberately did not do
now:** stop probing `api/claude` and instrument the RPC instead. The 504 is a
timeout on one Supabase function call; its duration is not recorded anywhere, so
there is nothing to correlate against. Two occurrences over two days is too thin
a signal to chase with more sampling, and more sampling is what the last five
hours already were.

**So `api/claude`'s two 504s are not explained.** What remains true is narrower
and still worth acting on: each cron's own failure rate, and the unbounded query
behind one of them. **§3 is unaffected** — the query text, the missing `dayStr`
filter and the index list are facts about the code, and `alf-alerts` failing 5
times in 12 hours is measured, not inferred. The fix in §5 was justified as
*"so it stops taking other crons down with it"*, and **that justification is
gone while the fix itself still stands on `alf-alerts`' own numbers.** Recorded
rather than quietly re-motivated.

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

## 5a. The `alf-alerts` fix, live-verified — and the half that mattered

Shipped in `43a06d9d` at about 13:30Z. The 14:00 firing is the first on the new
code:

    14:00:43 GET /api/alf-alerts 200
      alf-alerts: Resend send OK for license_hash 6dd308f1… (1 late) -- resend_id dd95d5a3…

**The 200 is the weaker half and is not yet attributable** — `alf-alerts` also
succeeded at 12:00 on the old code, so one clean firing proves nothing about the
failure rate. Three or more consecutive clean firings would.

**`(1 late)` is the half that mattered.** The whole risk of bounding that read
was that the time window would silently stop the sweep seeing administrations,
turning a medication-alert cron into one that reports nothing wrong. It found a
genuinely late dose on real data and emailed the facility. That is the property
the unit arms assert in a fixture, confirmed against production.

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

## 8. Re-measured 2026-09-15T17:12Z — the failure rate is now ZERO, and the last 502 predates one of the two fixes

§5a set the criterion itself and deliberately refused to claim the fix worked on
one clean firing: *"Three or more consecutive clean firings would."* That is
discharged, by a much wider margin than three.

**MEASURED, not inferred, from Vercel production runtime logs:**

| Window (back from 2026-09-15T17:12Z) | `send-reminder` 502s | `alf-alerts` 502s |
|---|---|---|
| 24h | **0** (of 24 firings) | **0** (of 24 firings) |
| 26h | **0** | **0** |
| 28h | **0** | **0** |
| 30h | 1 | 1 |
| 48h | 9 | 6 |

Both crons fired **24 of 24** times in the last 24 hours. Across the whole
project in that window there is **not one 502 and not one log line containing
`504`** — the only 5xx at all is 2× 503 on `/api/sd-data`.

**THE LAST FAILURE OF EACH IS PINNED TO AN HOUR:** `send-reminder` at
**12:00Z** and `alf-alerts` at **13:00Z on 2026-09-14** — the same two rows §4a
already recorded. Nothing since. **28 consecutive clean hours.**

**THE ZERO IS CONTROLLED RATHER THAN ASSERTED, because an empty result and a
broken filter look identical** — the platform defect this repo names most often.
Three controls, all run:

- The **same query shape** with the **same `statusCode=502` filter** returns
  rows at 30h and 48h and zero at 28h. The filter demonstrably works; the
  boundary is in the data, not in the query.
- `statusCode=503` returns the 2 known `/api/sd-data` rows.
- A full-text `failed` query returns 24 `send-reminder` and 48 `cron-watchdog`
  rows — those are the benign per-run summary line at
  `send-reminder.js:197` (`... failed 0`), which is what a *successful* firing
  logs, not a failure.

**ATTRIBUTION IS NOT ESTABLISHED AND THE TIMING IS AWKWARD FOR THE OBVIOUS
READING.** `43a06d9d` (the `alf-alerts` bound) deployed ~13:26Z and
`b162c871` (CC's schedule spread to :07/:37) at ~16:14Z. **Both of the last
failures precede `b162c871` entirely, and `alf-alerts`' last failure precedes
its own fix by 26 minutes.** So the recovery is *consistent* with both fixes and
*proven* by neither: a change on the Supabase side at the same time is not
excluded, and §7's alternative reading survives this measurement unchanged.

**THE PENDING MIGRATION QUESTION, STATED RATHER THAN DECIDED.**
`sql/dnt_appointments_due_index.sql` and `sql/alf_mar_sweep_index.sql` are
recorded as NOT RUN, and **I did not verify that against the database — I have
no route to it from here, so that is a reading of the record, not a check.**
If they are still unrun, then `send-reminder` has gone 28 hours clean on the
*same unindexed query*, which weakens the observed-failure-rate justification
for the index without touching the code fact underneath it: the query in
`send-reminder.js:128` still carries no matching index, and a table that grows
will time out again. **The right conclusion is that the index is no longer
URGENT, not that it is unnecessary** — and if Michael did run them, that is a
third candidate cause for the recovery and the cleanest one.

**WHAT WOULD SETTLE IT** is the one thing §4b already said: instrument the RPC
duration. Zero failures gives nothing to correlate, so there is even less signal
to chase now than there was then. **This section closes the verification
obligation `43a06d9d` and `b162c871` carried. It does not reopen the
investigation.**
