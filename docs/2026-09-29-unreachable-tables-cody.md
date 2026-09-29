# "Tables no code can ask for" — all 22 are false alarms, and the checker has two extraction defects

**2026-09-29 (Cody).** `tools/schema_provisioning_check.py` reported 22 tables
that "the schema builds and no code can ask for": **sairncode 15 of 15,
sairngrounds 4, sairnscape 3.** Every one was read individually against
`api/sd-data.js` and `api/_resources/*.js`.

**None is an orphan. None is an unreachable route. All 22 are category (iii),
false alarms of the checker** — and they come from two *different* defects in one
function, which is why a single fix would not have caught both.

**Nothing is proposed for deletion.** Dropping a table is a production data
decision for Michael, and there is nothing here that would justify raising it.

---

## DEFECT 1 — it compares TABLE names against RESOURCE names

`sairngrounds` and `sairnscape` deliberately map one to the other in
`api/sd-data.js`:

| app | registered resource | table the handler reaches |
|---|---|---|
| sairngrounds | `properties` | `grd_properties` |
| sairngrounds | `jobs` | `grd_jobs` |
| sairngrounds | `quotes` | `grd_quotes` |
| sairngrounds | `golf_zones` | `grd_golf_zones` |
| sairnscape | `customers` | `scp_customers` |
| sairnscape | `schedule` | `scp_schedule` |
| sairnscape | `invoices` | `scp_invoices` |

Every one of the seven is live: the handler builds the PostgREST path from the
prefixed table name while the registry admits the unprefixed resource name. The
checker sees `grd_properties` in the schema, does not see `grd_properties` in the
registry, and concludes no code can ask for it. **Code asks for it on every
page load.**

## DEFECT 2 — its registry reader knows one spelling and `sairncode` uses the other

```python
m = re.search(r'resources\s*:\s*\[', src)
if not m:
    return set()
```

`api/_resources/sairncode.js` declares `const RESOURCES = [ ... ]` and exports it
as `module.exports = { resources: RESOURCES }`. The literal `resources: [` never
appears, so the reader returns an **empty set** — and the tool then printed

    registered      : 0 checkable
    NOT REGISTERED  : 15 (the schema builds these and no code can ask for them)

for an app with **28 registered resources**, consumed by
`const SC_RESOURCES = require('./_resources/sairncode').resources;` in
`api/sd-data.js`. All 15 schema tables are inside those 28.

**The two halves of that output contradict each other and neither is flagged.**
"0 checkable" is a could-not-read and it was printed as a measurement; the
15-table finding was derived from it. An empty parse produced a confident
finding — which is the zero-item-corpus failure, in a tool that was answering a
provisioning question.

---

## The classification asked for, one line each

| table | class | why |
|---|---|---|
| `sc_anesthesia`, `sc_ar`, `sc_auth`, `sc_compliance`, `sc_denial`, `sc_drg`, `sc_encoder`, `sc_fraud`, `sc_hcc`, `sc_prebill`, `sc_providers`, `sc_query`, `sc_rac`, `sc_revenue`, `sc_telehealth` | **(iii) false alarm** | all 15 are inside the 28 names `SC_RESOURCES` exports; the reader missed the `const RESOURCES` spelling |
| `grd_properties`, `grd_jobs`, `grd_quotes`, `grd_golf_zones` | **(iii) false alarm** | registered as `properties` / `jobs` / `quotes` / `golf_zones`; the handler adds the prefix |
| `scp_customers`, `scp_schedule`, `scp_invoices` | **(iii) false alarm** | registered as `customers` / `schedule` / `invoices`; same mapping |

---

## Registered as a checker defect, not as a platform finding

**`tools/schema_provisioning_check.py` is inside cc's and hank's live `platform`
and `hank` claims**, so the fix is not made here. Both defects are recorded so
whoever holds it next does not re-derive them:

1. `registered()` must read the module's **exported** `resources`, not a literal
   `resources: [` — the `const NAME = [...]` + `module.exports` form is in use
   today and returns silently empty.
2. An **empty** registry read must be `COULD NOT RUN`, never `0 checkable`
   followed by a NOT-REGISTERED finding derived from it.
3. The table↔resource comparison needs the handler's mapping, or the
   NOT-REGISTERED verdict must be demoted to *"no resource of this NAME"* —
   which is a true statement and not the one the current wording makes.

**My own runner inherited the same class**, and it is stated rather than
quietly corrected: the authenticated re-run in item 3 extracted resource names
with a bare `'([a-z0-9_]+)'` sweep and picked up `write`, `read`, `default`,
`jobs`, `schedule` and `invoices` from surrounding code, producing spurious
`400 resource must be one of…` rows. Those rows are artefacts of my extraction,
not findings, and the item-3 report says so beside them.
