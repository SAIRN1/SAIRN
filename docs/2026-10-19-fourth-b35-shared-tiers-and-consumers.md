# b35 — the shared resources tiered, two more route consumers, and one line for cc

**fourth / b35, 2026-10-19.** Follows `docs/2026-10-19-fourth-b34-routing-phase1.md`.

**§3 is the routed item and it is one line of `tools/criticality_tier_check.py`.
It is not applied here — `tools/` is cc's directory. The effect of applying it
was MEASURED, not asserted: it clears 8 findings and introduces 0.**

---

## 1. `sd_field_stops` vs `rt_stops` — the contradiction, resolved

### The deciding test, stated before it was run

It was written into the register's own gaps section in b34, so the answer could
not be fitted to the result afterwards:

> **Is a stored stop joined to a NAMED person?** If yes, `sd_field_stops` is a
> record of where an identifiable person was and it moves. If the stop carries
> no assignee at all, it is a bare address list and B is right — and then
> `rt_stops` is the first time StoneDesk's own data acquires that join.

### The answer, read at the write site

**Yes, twice over.** `fmSaveStop()` (`stonedesk.html:12879`):

```js
var person=document.getElementById('fm-s-person').value.trim();
var address=document.getElementById('fm-s-address').value.trim();
var dateStr=document.getElementById('fm-s-date').value;
if(!person||!address||!dateStr){ showToast('Person, address, and date are required'); return; }
var stop={ id:…, person:person, type:…, date:dateStr, time:…,
           address:address, customer:…, notes:…, status:'not-started', createdAt:… };
```

* `person` is **required** — the function refuses to save without it — and is
  pre-filled from `currentUser.name`.
* `address` is **required**.
* `customer` is a free-text **"Customer name"** input (`:8446`).
* **And it leaves the device:** `sd_field_stops` is in `SD_SYNCED` (`:2035`),
  so the row is pushed to the server. A local-only reading would have missed
  that half.

So the row carries **a named employee, a named customer, a street address, a
date and a time** — which is **strictly more than `rt_stops`**, whose schema has
no customer-name field at all.

### What moved, and what deliberately did not

**`sd_field_stops` moved B → A on confidentiality. `rt_stops` was re-read and
stands at A/A.** Only one of the two rows changed, which was the instruction and
is also the only defensible outcome: correcting both to match would have been
the retier-by-analogy the gaps bullet existed to refuse.

**Integrity stays B** on `sd_field_stops` — a lost stop costs a re-entry from
the job the visit belongs to, and no money and no regulated record sits on it.
The A is the confidentiality axis alone, derived as the worse of the two.

**The previous cell said so about itself:** *"Classified by the stated B rule
rather than individually read."* It was not wrong about its own evidence — it
was honest that it had none. The contradiction with `rt_stops` is what forced
the read.

---

## 2. The seven `shared.js` resources — tiered at their own write sites

All seven read in `api/sd-data.js`. **Two were flagged in advance as *not
obviously B* and both moved.**

| resource | Tier | Conf. | the deciding fact |
|---|---|---|---|
| `profile` | B | B | `business_profiles`, one row per shop per app. The shop's description of itself; nothing on it is about a person |
| `memory` | B | B | `ai_memories`, written through `aiScan.redactAiFields()`. `memory` **is** in `AI_SCANNED_TEXT` (`ai-scan-redaction.js:84`), so the redaction is real rather than nominal |
| **`employees`** | **A** | **A** | **compensation, and a money path across an app boundary** — see below |
| `slabs` | **A** | B | **a documented incident**, the third limb of the A rule: a blind upsert destroyed a `reservedFor` hold |
| `render_usage` | B | B | an integer per shop per month; no charge computes from it |
| `shared_knowledge` | B | B | a word list — *"Never raw message text"* (`sd-data.js:6221`) |
| **`employee_profile`** | **A** | **A** | a manager's written assessment of a named employee |

### `employees` — the sharpest finding is that the code already knew

`api/sd-data.js:2478` carries this comment, and it **predates** the row:

> *"this resource carries hourly_rate (payroll), so it's the first real
> server-side role check in this file. Sales/Install are refused outright;
> Owner/Manager may read, but Manager gets hourly_rate stripped — only Owner
> sees pay."*

**Nobody builds a per-role field-stripping gate for Tier B data.** The code had
been treating this as Tier A for months. The register was the only place that
did not know — and **the arm that would have said so was skipping the file.**

**And the integrity half crosses an app boundary**, which is the part a per-app
reading would miss: `stonedesk.html:43148` averages `hourly_rate` across the
shared roster and presents it as the shop's labour rate. A wrong rate in
SAIRNbiz's roster becomes a wrong labour cost in **StoneDesk's** Business
Intelligence, upstream of what a job is quoted at. That is the register's own
*pricing that feeds money* test, met across two apps.

### `employee_profile` — the read gate is the evidence

The write is Owner/Manager-only. **The read branch (`:3731`) is what decides
it:** it refuses `payload.all` to anyone outside those roles, and otherwise
serves only the caller's **own** profile, derived server-side from the verified
session token, **never from a client-supplied `employee_id`**. An app does not
derive the subject server-side to stop one employee reading a colleague's row
unless the row is about a person.

### One row is left with an open question on it

**`memory`'s B rests on `redactDocumentText()` normally returning
`complete: true`, and nobody has measured how often it returns `false`.** That
is written into the row rather than rounded off. It is the one thing that would
move it.

---

## 3. ROUTED TO cc — `tools/criticality_tier_check.py`, one line

**NOT APPLIED HERE. `tools/` is cc's directory.**

### The defect

`apps_with_registries()` skips `shared.js` by name:

```python
for f in sorted(os.listdir(RESOURCES)):
    if not f.endswith('.js') or f.endswith('.test.js'):
        continue
    app = f[:-3]
    if app in ('index', 'shared'):     # <-- this line
        continue
```

**`index.js` belongs in that list — it is the merger, not a registry.
`shared.js` does not — it is a registry with seven real resources on it.**

### It fails open in BOTH directions, which is worse than it reads

1. **It never demands a row.** The completeness arm that catches
   `sairnsenior/sen_period_closings` reported **clean** over all seven for as
   long as they had no row — including over `employees`, which is Tier A on
   both axes.
2. **It rejects the rows when you write them.** Writing the seven rows raised
   **seven `NOT A RESOURCE` findings** plus one `GONE` for the rollup line.

So the register could not be made correct without the fix. That is the part
that makes this a blocker rather than a tidy-up.

### The fix

```python
    if app == 'index':
        continue
```

### It was MEASURED, not asserted

Run in an isolated worktree over the b35 register
(`scratchpad/b35/simulate_cc_fix.py`), before and after:

```
BEFORE   APPS_WITH_REGISTRIES 18   RESOURCES_REGISTERED 394   PROBLEMS 11
AFTER    APPS_WITH_REGISTRIES 19   RESOURCES_REGISTERED 401   PROBLEMS  3

CLEARED by the fix   : 8
   - GONE            shared has a rollup line and no resource registry
   - NOT A RESOURCE  profile / memory / employees / slabs /
                     render_usage / shared_knowledge / employee_profile
INTRODUCED by the fix: 0
```

The 3 that remain are **pre-existing and not fourth's**: two `sairnscape`
rollup COUNT drifts and `sairnsenior/sen_period_closings` having no row.

**The `### shared` section and its rollup line are already written**, so the
one-line change lands on a consistent register rather than on seven fresh
findings. Nothing else is needed.

### Two things worth deciding at the same time, not assumed

* **Is `routes` right as its own registry file?** b34 created
  `api/_resources/routes.js` specifically to dodge this skip. With the skip
  gone, `shared.js` would have been a legitimate home. Leaving `routes` where
  it is costs nothing and keeps the two cross-app registries separately
  rollup-able — but it is now a choice rather than a workaround, and it should
  be recorded as one.
* **Should the skip be a property rather than a name list?** A file opting out
  via its own `module.exports` would not go stale the way a hard-coded tuple
  does. Not proposed, just named — it is cc's call and cc's file.

---

## 4. Consumers three and four

**The point of these two is not that there are more of them. It is that each
one's data shape is different, and the module did not change.**

| | assignee | where the address lives | storage |
|---|---|---|---|
| StoneDesk (b34) | `person` on the stop | **on the stop itself** | localStorage |
| SAIRNgrounds (b34) | `crew` string | on the **property** | localStorage |
| **SAIRNscape (b35)** | `crew` string | on the **customer** | localStorage |
| **SAIRNroofing (b35)** | **`crew` ARRAY** | on the **job** | **server-first** |

### SAIRNscape — one line of concept, then the build

**`scp_schedule` rows are `{id, customer_id, freq, next, crew, status}`; the
address lives on the CUSTOMER record, reached through `customer_id`.**

A *Route order for a crew's day* card on the Scheduling panel, calling
`scpData('optimize','rt_routes')`.

### SAIRNroofing — the one that was actually worth having

**`rf_schedule` rows are `{schedule_id, job_id, scheduled_date, status,
crew:[names…], notes}`; the address lives on the JOB, and `crew` is an ARRAY.**

Two things are genuinely different and both are named in the code:

* **There is no single assignee on the record.** A roofing day belongs to
  several people. The ordering unit is therefore **one named person across the
  days they appear on** — which is the right unit regardless, since a route is
  driven by a person, not by a crew.
* **The app is server-first.** `rfSchedule` is populated by `rfLoadSchedule()`
  with role-scoped visibility already applied, so the card reads the in-memory
  list rather than issuing a second query that could return a different set.

### Both driven in a real browser, every answer path

| path | SAIRNscape | SAIRNroofing |
|---|---|---|
| `unavailable` | names the reason, *"schedule is unchanged"* | same |
| `drive-matrix` | reordered, *"saves about 8 min"* | reordered, *"saves about 11 min"* |
| **`saved_seconds: null`** | **"drive-time saving not computed"** | same — **never "0 min"** |
| `great-circle` | labelled, with the drive-time reason | labelled |
| no answer | *"Nothing was changed"* | *"did not run — Not signed in"* |
| order length ≠ stops sent | — | **refused, schedule unchanged** |

**And the exclusion path in both:** a visit whose customer (scape) or job
(roofing) has **no address** is **listed by name as excluded**, never silently
dropped. Roofing's crew-array flattening was confirmed too: three days with
`['Ana Reyes','Tom Cole']` and `['Ana Reyes']` produced exactly two picker
entries, deduped and sorted.

`checkblocks`: **sairnscape 7/0**, **sairnroofing 3/0**.

---

## 5. UNCHANGED, AND NOT CLAIMED

* **`api/sd-data.js` was not touched.** cody still holds it; the `rt_routes`
  handler branch from b34 §3 is still the only thing between this and a working
  endpoint, and it is still unapplied. **All four consumers remain unreachable
  at runtime.**
* **`sql/rt_routes_schema.sql` has still not been run.** Neither table exists.
* **Nothing live was verified.** Unchanged from b34 and for the same measured
  reason: the licence gate answers 401 ahead of resource dispatch, so a probe
  cannot tell a registered resource from a nonsense one.
* **SAIRNmechanical is queued for the next batch**, as instructed.
* **`tools/` was not touched.** §3 is routed, not applied.
