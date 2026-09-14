# Item 39 — does anything check that a record required to survive actually did?

**Written 2026-09-14 (Fourth).** Scoped against the Class A set from
`docs/2026-09-13-irreversible-write-witnessing-scoping.md` — the resources whose
own registry files declare them APPEND-ONLY BY DESIGN — plus `sv_controlled`,
which is not declared append-only and simply cannot be unwound.

The question has two halves and they fail differently. **Does the record still
EXIST** after a cap, a trim or a migration; and **can it be RETRIEVED** by
somebody who has to produce it. A record that exists and cannot be produced is
lost in every sense that matters to an inspector.

---

## The platform's answer to the first half: there is one retention rule, and nothing consumes it

`api/sd-data.js:143`

    // Minimum data-retention any SAIRNcode practice may configure, in years.
    // ... a value written today is inherited by whatever purge mechanism is
    // built later -- a tampered or mistaken small number here becomes real,
    // irreversible medical-record loss years from now ...
    const SC_RETENTION_FLOOR_YEARS = 10;

It is referenced in exactly two places (`:11327`, `:11332`) and both are the same
validation on the settings write: a `retention_years` below ten is refused.

**There is no purge mechanism.** The comment is honest about writing for one that
does not exist yet — and the consequence is that the only retention number on the
platform is **a stored preference that nothing reads, checks against, or reports
on**. No job compares a record's age to it. Nothing verifies a record that should
have survived did.

**And it is one app.** Measured across the Class A set, anchoring the search on
the actual `create table` statement rather than on any file that mentions the
name — the first pass matched audit scripts instead of schemas and had to be
redone:

| Resource | Its CREATE TABLE lives in | Retention statement |
|---|---|---|
| `sv_audit_log` | `sql/sairnvet_data_schema.sql` | none |
| `sv_controlled` | `sql/sairnvet_data_schema.sql` | none |
| `dnt_payments` | `sql/sairndental_data_schema.sql` | none |
| `dnt_charges` | `sql/sairndental_data_schema.sql` | none |
| `dnt_credentials` | `sql/sairndental_credentials_schema.sql` | none |
| `dnt_vendor_orders` | `sql/sairndental_vendor_schema.sql` | none |
| `rf_certifications` | `sql/sairnroofing_certifications_schema.sql` | none |
| `rf_claim_photos` | `sql/sairnroofing_claims_schema.sql` | none |
| `rf_proposals` | `sql/sairnroofing_billing_schema.sql` | none |
| `alf_staff_credentials` | `sql/sairncare_compliance_schema.sql` | none |
| `mech_credentials` | `sql/mech_credentials_schema.sql` | none |

**Eleven of eleven.** Every one of these is a record somebody decided must be
permanent, and not one of them says for how long, to whom, or under what rule.

---

## The second half, hand-verified on one resource: a writer, a cap, and no reader

**`sv_audit_log` is SAIRNvet's controlled-substance DOSING AUDIT TRAIL** — the
record whose whole purpose is to be produced when somebody asks who dosed what.

`sairnvet.html:7761` `logDoseAudit()` is the only function that touches it. It
appends an entry, and then:

    if(log.length>500) log = log.slice(log.length-500);
    ok = st('sv_audit_log', log);

**A 500-entry cap, applied on every write, keeping the newest.**

### Three findings about it, and one of them is a NEGATIVE worth as much as the others

**1. THE CAP DOES NOT DELETE THE SERVER COPY — stated first because it is the
thing that would have made this urgent and it is not true.** `svSyncCollection()`
(`sairnvet.html:2216`) iterates `next` and pushes changed records. It computes no
removals and calls no delete verb. A record trimmed out of the local array simply
stops being pushed; the server row stands. This is the same shape StoneDesk got
wrong and had to fix — there, `sdSyncCollection()` had been wired for deletions,
which is precisely what turned a quota cap into a silent server-side deletion.
SAIRNvet never wired that, so the hazard does not exist here.

**2. NOTHING IN THE PRODUCT CAN READ IT.** `grep` for the key in `sairnvet.html`
returns five lines and all five are accounted for: two comments (`:2043`,
`:9242`), the `SV_SYNCED` membership (`:2047`), and the writer's own read and
write (`:7764`, `:7782`). **The only code that reads the dosing audit trail is
the function that appends to it.**

Confirmed by a structurally different method rather than a second grep for the
same string, because a key-string search and a second key-string search share a
blind spot exactly: enumerating the app's panels and nav targets finds
`panel-controlled` and `panel-controlled-table` for the controlled-substance
register and **no panel, no nav item and no export for the dosing trail**.
SAIRNvet has no generic collection exporter either — `SV_SYNCED` is read in only
two places, the sync-on map and the hydrate loop.

**Stated precisely, because the stronger claim would be false:** the rows are
retrievable by a direct authenticated API call against the generic `SV_RESOURCES`
read branch. They are not retrievable *through the product*, by the person who
would be asked for them, in the situation where they would be asked.

**3. THE OLDEST ENTRIES ARE BOTH UN-BACKED-UP AND FIRST TO BE TRIMMED, and that
compound is the real finding.** The file says the first half itself:

> ENTRIES WRITTEN BEFORE TODAY HAVE NO id AND ARE NOT BACKED UP. They stay on the
> device and are readable exactly as before

That is a defensible decision and the reasoning given for it is right —
back-filling ids into an existing audit trail would be rewriting it, which is the
one thing an audit trail must not have done to it. **What nobody wrote down is
the consequence of pairing it with the cap.** The cap keeps the NEWEST 500. The
un-backed-up entries are the OLDEST. So the entries that exist in exactly one
place are precisely the ones the next 500 writes will push out of it, and when
they go there is no second copy — not because anything deleted them, but because
the only copy was in a quota-bounded browser store.

`svSyncCollection()` does count and warn about idless records rather than
skipping them silently, which is better than StoneDesk's equivalent. It warns to
`console.warn`. Nobody in a clinic is reading the browser console.

---

## What is NOT claimed here, and the denominator

**Nine of the eleven Class A resources are UNASSESSED for retrievability, not
clean.** A reference count against the storage-key string cannot answer the
question for a resource rendered from a backing variable — the panel reads
`svControlled`, not `'sv_controlled'` — and a first pass that used that count as
a proxy produced a table that looked like a finding and was not. The correct
method is the one CC's cap-attribution work already established: derive
`backing variable -> key` from every `st(key, var)` site and then ask whether the
variable reaches a renderer. Only SAIRNvet stores these through that idiom; the
other four apps write their Class A resources through the API directly, so the
question there is about the panel and not about a local cap, and it was not done.

**No live customer impact is claimed.** Whether any provisioned SAIRNvet licence
has dosing entries at all was not checked.

**Nothing was changed.** No cap was raised, no panel was built, no retention
value was written.

---

## Sizing, and the one thing that is not a technical decision

| # | Work | Size |
|---|---|---|
| 39a | A reader for `sv_audit_log` — a panel that lists the dosing trail, hydrated from the server rather than from the 500-entry local slice, so the record can be produced at all | **M** |
| 39b | The idless-backup warning goes somewhere a person sees, not `console.warn`. It already counts correctly; it just says it where nobody is | **S** |
| 39c | Finish the retrievability question for the other nine, by the backing-variable method rather than by key-string count | **S** |

**And the part that is a business decision, held out rather than guessed at: how
long must each of these survive, and under whose rule?** DEA dosing records,
dental charges and payments, staff credentials and roofing certifications are
governed by different retention periods in different jurisdictions, and
`SC_RETENTION_FLOOR_YEARS` shows the house style for this — a floor with the
reasoning written beside it. **Until somebody states a period, "does the record
survive its retention period" is not a checkable question**, and building a
checker against an unstated period would be the checker inventing the rule it
enforces. That is the decision to take first; 39a and 39b stand on their own
without it.
