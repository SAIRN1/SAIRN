# The watchdog was watching itself into a loop — and nothing outside Vercel was watching it at all

**2026-09-15 (Hank).** Item 54 was commissioned as unbuilt. It is built — Fourth
landed it on 2026-09-14, with item 55's graduated response on top. What was
missing is the second half of the sentence: **who responds when the watchdog is
the sick one.** Asking that question against the live logs found three defects
in the running system, two of them self-inflicted and one of them silent.

---

## 1. What already existed, checked before anything was written

| piece | state |
|---|---|
| `api/_lib/heartbeat.js`, `api/cron-watchdog.js`, `sql/cron_heartbeat_schema.sql` | **BUILT 2026-09-14 (Fourth)**, item 54 |
| `api/_lib/cron-response.js` — the pre-decided response table | **BUILT 2026-09-14 (Fourth)**, item 55 |
| soft recovery (`retry`), escalation after *N* consecutive detections, alert-storm suppression | already there |
| `tools/cron_liveness_check.py` — reads the watchdog from **outside Vercel** | already there |

So the graduated pattern existed. What did not exist was an **independent
scheduler** to run the outside reader: that tool's own header said a
third-party monitor was "a spend-and-vendor decision rather than a code
change", and on that basis nobody built it.

---

## 2. Three live defects, found in production logs rather than by reading

`GET/POST /api/cron-watchdog`, 2026-09-15, four consecutive hours. All three
**real** jobs reported `ok` the entire time.

### 2.1 The watchdog was retrying itself, and Vercel said so

    21:15:29Z  {"action":"retry","job":"/api/cron-watchdog",
                "delivered":false,"detail":{"ok":false,"status":508}}

**508 is LOOP DETECTED.** `/api/cron-watchdog` is in its own `EXPECTED_JOBS` —
correctly, because it must leave a heartbeat for an outside reader — but nothing
stopped it from *responding* to its own row. `RESPONSE.FAILING.retry` is `true`,
so `retryJob()` POSTed the running function to itself.

### 2.2 A latch that could never clear — the worse half

Trace it from the code and it is a closed loop:

1. An alert cannot be delivered → `undelivered.length > 0` → the job writes its
   own outcome as **`failed`**.
2. Next hour it reads its own row, sees `last_outcome: failed`, and calls itself
   **`FAILING`**.
3. Which plans an alert. Which cannot be delivered. Which writes `failed`.

**Once it failed to deliver once, it was permanently FAILING regardless of the
platform's actual health.** The only thing it was reporting was a fault it was
causing itself.

### 2.3 And it defeated the alert-storm rule through a door nobody checked

`REALERT_SECONDS` suppresses a repeat alert for 6 hours — *when the status is
the same*. The self-status **flapped** (`PARTIAL → FAILING → FAILING → PARTIAL`),
because the outcome it wrote depended on what it had just failed to send. `same`
was false on every flap, so the suppression never applied and it re-alerted
every hour. **The exact storm that constant exists to prevent, arriving by a
route the design did not model.**

### 2.4 The silent one: it could not tell anybody anything

`SAIRN_OPS_EMAIL` is not set in production. Every alert the watchdog has ever
planned ended `"nobody was told"` — and that was visible **only inside a
per-job action detail**, under an HTTP 200 and a headline reading
`checked 4 job(s)`.

**A watchdog that detects perfectly and can notify nobody is the failure its own
header calls worse than having none**, "because the existence of a watchdog is
itself an assurance somebody is relying on." It had that defect while saying so.

---

## 3. The fixes

### A monitor does not act on itself

The self row **stays in the report and stays in the heartbeat** — that row is the
only evidence an outside reader has that the watchdog ran at all. What is removed
is the watchdog *responding* to it: no alert, no retry, no escalation, and
deliberately **no memo entry either**, because a streak counter on a job nothing
acts on reads to a later reader as a pending escalation.

It is reported as an explicit `self` action rather than dropped, so the exclusion
is visible instead of looking like a detector that stopped detecting. One change
fixes both 2.1 and 2.2.

### The channel is asked about every run, not only when there is something to send

`notify_channel: {configured, missing, escalation_has_own_address}` is now a
standing field in the watchdog's answer, and `ok` requires it. Waiting until a
real job fails to discover the channel is dead is the same defect as a backup
nobody restores: **the moment you need it is the moment you find out.**

`SAIRN_ESCALATION_EMAIL` is deliberately *not* in `missing` — `alertTo()` falls
back to `SAIRN_OPS_EMAIL`, so its absence changes *who* is told, not *whether*
anybody is, and folding it in would make a working channel read as broken.

### The outcome word, and why it is not `failed`

An unconfigured channel is a **standing configuration state, not a run that went
wrong** — and writing `failed` for it is precisely what created the latch in 2.2.
It writes `partial`: it detected correctly and it cannot notify, which is
literally part of the work done. It is still **not `ok`**. An undelivered alert
about a *real* job is still `failed`.

---

## 4. The second watchdog — `.github/workflows/cron-liveness.yml`

**The "spend-and-vendor decision" is out of date in the cheapest possible
direction.** This repository already runs two scheduled GitHub Actions workflows
(`codeql.yml`, `nightly-backup.yml`). A third costs nothing and runs on a
genuinely different scheduler from Vercel's.

It runs the existing `tools/cron_liveness_check.py` — **reused, not reinvented** —
hourly at `:45`, thirty minutes after the Vercel watchdog's `:15` and clear of
the `:07` and `:37` the two real jobs fire on.

**The graduated response, and the part that is deliberately *not* graduated:**

1. **READ.** Clean → done, no noise.
2. **SOFT** — *only* on exit 1, a finding about the jobs. Poke the watchdog to
   run now, wait, read again. One hourly sample can catch a job mid-deploy, and
   failing the build on a single sample is how a monitor earns the reputation
   that gets it muted.
3. **HARD** — still not clean → **fail the job.** GitHub mails the repository
   owner on a failed scheduled workflow, and that channel depends on **neither
   `SAIRN_OPS_EMAIL`, nor Resend, nor Vercel running** — the three things that
   were broken together.

**Exit 2 — could-not-tell — gets no soft attempt.** A missing secret, an
unreachable endpoint, `NOT_PROVISIONED`, zero jobs checked: none of those improve
by asking again, and retrying them only delays the report.

**Without `CRON_SECRET` it fails rather than skips.** A monitoring workflow that
goes green because it was not configured is the defect this platform names most
often.

---

## 5. The controls

`tests/run_cron_liveness_probe.py` — **34 arms, 0 failures.**
`api/cron-watchdog.test.js` — **67 arms, 0 failures** (was 55).

- **The self-exclusion is tested in the pure half**, where the file's own design
  says the decision belongs. Including a **control that the old behaviour is
  unchanged with no `selfJob`** — without it, the three arms after it would pass
  just as happily against a `planResponse` that had stopped acting on anything.
- **The latch is driven for five consecutive runs** — the production shape
  exactly — asserting no escalation and an empty memo.
- **"Not a mute button":** a report containing both the self row and a dead
  `alf-alerts` still alerts and retries on `alf-alerts`.
- **Both directions on the channel**, plus the arm that would otherwise be
  missing: a payload with **no `notify_channel` at all is COULD NOT TELL**, not
  OK. An older deployment that cannot answer is not the same as a healthy one.
- **TEETH on the reader:** neutering the channel check makes a dead channel
  report OK again — anchor asserted present, mutation asserted applied.
- **THE WORKFLOW'S VERDICT IS EXECUTED, NOT READ.** Section C extracts the real
  `run:` script out of the real YAML and drives it as shell across every exit-code
  combination. A verdict written in YAML that nobody runs is a verdict nobody has
  ever seen fire. **The arm that matters most: no exit code recorded at all → it
  must FAIL, not pass** — the shape where the monitor goes green because it broke.

---

## 6. Not established / not done

- **`sql/cron_heartbeat_schema.sql` is still recorded as NOT RUN** and I did not
  verify that against the database. The watchdog is answering with real job rows
  in production, which is only consistent with the table existing — so the
  record and the observed behaviour disagree, and **the record is the thing I
  could not check.**
- **`SAIRN_OPS_EMAIL` is Michael's to set.** Until then the watchdog will report
  `ok:false` with `notify_channel.configured:false`, which is the honest answer
  and is the point — it is now *visible* rather than buried.
- **Two Actions secrets are needed** for the new workflow: `CRON_SECRET`
  (required — it fails without it) and `SAIRN_WATCHDOG_URL` (optional).
- **Between this push and the next Vercel deploy, `cron_liveness_check.py` will
  report COULD NOT TELL**, because the live endpoint does not yet emit
  `notify_channel`. That is the fail-closed direction and it resolves on deploy.
- **GitHub Actions is not an uptime vendor.** Scheduled workflows can be delayed
  under load and are disabled on a repository idle for 60 days. A second
  *independent* scheduler is a real improvement over one watching itself; it is
  not a *guaranteed* one, and both the tool and the workflow say so in their own
  headers.
- **The self-exclusion means nothing in Vercel now responds to a sick watchdog.**
  That is deliberate — a sick watchdog cannot be its own second opinion — but it
  means the GitHub workflow is now load-bearing rather than an extra net.
