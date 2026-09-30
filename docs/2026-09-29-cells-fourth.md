# Register cells re-derived from HEAD: `locations` and `sv_herdhealth`

**Fourth, 2026-09-29.** Replacement text for two rows of `docs/CRITICALITY-TIERS.md`.
**This document is not the ledger and does not write to it.** `docs/CRITICALITY-TIERS.md`
is hank's and `docs/tier-a-reviews.json` is hank's; both cells are delivered here as
text to paste, per PR 2.1 — two sessions hand-editing one table row is the collision
that rule exists for.

**Everything below was read at HEAD in this clone. Nothing was copied from the
hover auditor's log, which a build agent must not read.** Where the brief I was
given does not match what the code does, the code wins and the difference is
stated rather than smoothed over.

---

## The brief did not match the code, and the mismatch is the finding

I was told: *"sv_herdhealth: the cell should quote the blast radius that a rename
relabels every record that references the renamed entity."*

**Re-derived from HEAD, that blast radius is `locations`, not `sv_herdhealth`,**
and the code says so itself in the branch that performs the write —
`api/sd-data.js:2865-2869`:

> this branch is an UPSERT on (license_hash, location_id), so renaming a yard
> silently relabels every slab ever attributed to it, on every screen, with no
> record that anything changed. Closing one does the same to its whole history.

`sv_herdhealth` has no rename affordance at all and nothing outside itself
references a herd. Both claims are checked below by line. So the two cells are
answered separately: `locations` gets the blast-radius basis it is missing, and
`sv_herdhealth` gets what is actually true of it, which is a different argument.

---

## 1. `locations` — `docs/CRITICALITY-TIERS.md:177`

### What the cell says now

| | |
|---|---|
| Availability | **B** |
| Integrity | **B** |
| Impact | A location record wrong |
| Confidentiality basis | No elevated confidentiality class — no PII, PHI, privileged communication, or financial-account detail on this row. Classified by the stated B rule rather than individually read |
| Integrity basis | Shared operational reference; `api/_lib/dnt-location.js` stamps location on writes elsewhere |

### What the code does — read directly

**Lines read.** `api/sd-data.js:1016` (`'locations': ['read','write']` in the
session-gate table), `:1302` (`'locations': 'stonedesk'` in the app map),
`:2853-2860` (the read branch), `:2861-2903` (the write branch),
`stonedesk.html:9251` (the read caller), `:9424-9452` (`sdLocAdd`),
`:9457-9477` (`sdLocToggle`), `api/_resources/stonedesk.js:118`,
`api/_lib/dnt-location.js:1-25`.

**The integrity basis is citing the wrong application.** `api/_lib/dnt-location.js`
is SAIRNdental's write-side location stamp — its own header, lines 1-8, says
"SAIRNdental multi-location: WRITE-SIDE CAPTURE ONLY" and that a costing pass
found *zero* matches for any location concept in SAIRNdental before it was
written. The `locations` resource in this row is StoneDesk's: table `sd_locations`,
`app_id: 'stonedesk'` (`api/sd-data.js:1302`, `:2891`). The two share a word and
nothing else. **A basis that names a different app's file is not evidence for
this row, and that is the auditor's flag confirmed by reading.**

**What the basis should say instead is stronger than what it says.** The write is
an UPSERT on `(license_hash, location_id)` (`:2887`), so:

- **A rename relabels history with no record of the change.** Every slab ever
  attributed to that yard now reads as the new name, on every screen, and
  nothing anywhere records that it used to be called something else. The code
  states this at `:2865-2869` as the reason the write became management-only.
- **There is no delete verb and none is planned** (`:2849-2852`). A closed yard
  is `active:false` and keeps its history; deleting one would leave every slab
  ever held there pointing at an id that resolves to nothing. The client honours
  the same rule — `sdLocToggle` at `stonedesk.html:9457` onward closes, never
  deletes -- the reason is stated at `:9453-9456`.
- **Read and write are split on purpose.** Read is open to any signed-in
  employee because a templater has to know which yard a slab is in to go and
  find it; write requires `CRM_MANAGEMENT_ROLES` and answers 403 otherwise
  (`:2872-2876`). Before 2026-09-03 the write was available to anyone holding
  the licence key.
- **A refusal and an outage are not the same answer, and the client already
  knows it.** `sdLocAdd` rolls the local record back on a 403 and keeps it on a
  network failure (`stonedesk.html:9444-9449`), because nothing will ever make
  a refused write land.
- **An unnamed yard is refused rather than papered over** (`:2880-2886`): a slab
  attributed to `LOC1759...` is attributed to nothing a human can read.

**On confidentiality, the current cell is right but for a reason it does not
give.** The payload is `{id, name, address, active, created_at}`
(`stonedesk.html:9427-9429`) — so the row *does* carry a street address. It is a
**business** address, the yard's own, not a person's, which is why B is correct.
The existing text reaches B by "the stated B rule rather than individually read",
which would have reached the same answer whether an address was there or not.

### Replacement row

```
| `locations` | **B** | **B** | A location record wrong relabels history silently | No elevated confidentiality class. READ, not inferred: the payload is `{id, name, address, active, created_at}` (`stonedesk.html:9427-9429`), so the row DOES carry a street address -- the yard's own business address, not a person's, which is why this stays B rather than rising | UPSERT on `(license_hash, location_id)` (`api/sd-data.js:2887`), so a RENAME silently relabels every slab ever attributed to that yard, on every screen, with no record that anything changed -- the code says so at `:2865-2869` and that is why the write is management-only (`CRM_MANAGEMENT_ROLES`, 403 otherwise, `:2872-2876`; open to any licence key before 2026-09-03). NO DELETE VERB and none planned (`:2849-2852`): a closed yard is `active:false` and keeps its history, because deleting one would leave every slab ever held there pointing at an id resolving to nothing. Read stays open to every employee -- a templater must know which yard a slab is in. An unnamed yard is REFUSED (`:2880-2886`) rather than rendered as a raw id. Held at B and not raised to A because the blast radius is a wrong LABEL on operational records, recoverable by renaming back; no money figure and no regulated record moves. **The previous basis cited `api/_lib/dnt-location.js`, which is SAIRNdental's write-side stamp (its own header, lines 1-8) and has nothing to do with `sd_locations`/`app_id: 'stonedesk'` (`:1302`, `:2891`) -- a different app's file is not evidence for this row** |
```

---

## 2. `sv_herdhealth` — `docs/CRITICALITY-TIERS.md:587`

### What the cell says now

| | |
|---|---|
| Availability | **B** |
| Integrity | **B** |
| Impact | Operational data lost or wrong |
| Confidentiality basis | No elevated confidentiality class — no PII, PHI, privileged communication, or financial-account detail on this row. Classified by the stated B rule rather than individually read |
| Integrity basis | Operational data lost or wrong: neither money nor a regulated record. Classified by the stated B rule rather than individually read |

### What the code does — read directly

**Lines read.** `sairnvet.html:2262` (the resource list), `:5297` (the comment
routing herd-level work here), `:6326-6338` (`getHerds`, including the demo
seed), `:6340-6342` (`saveHerds`), `:6344-6372` (`renderHerdHealth` and its four
KPIs), `:6374-6398` (`openHerdEdit` — the full editable field set),
`:6405-6421` (`saveHerdEdit`), `:6423-6431` (`removeHerd`), `:6433-6443`
(`addHerd`), `api/sd-data.js:12514` (`sv_herdhealth: 'herdhealth_id'`),
`api/_resources/sairnvet.js:82`.

**The rename blast radius does not exist here, and I checked both halves.**

1. **There is no rename affordance.** `openHerdEdit` (`:6374-6398`) renders
   inputs for `headCount`, `lastVisit`, `status`, `vaccinationCompliance` and
   `scc` — and nothing else. The herd name appears only in the heading,
   `'Editing: '+escHtml(h.herd)` (`:6381`), as text. `saveHerdEdit`
   (`:6405-6421`) writes back only those five fields. The name can be set once
   at `addHerd` (`:6442`) and never changed.
2. **Nothing outside this resource references a herd.** Grepping `.herd` and
   `herd:` across `sairnvet.html` returns seven sites and every one is inside
   `sv_herdhealth`'s own code: the two seed rows (`:6333-6334`), the table cell
   (`:6353`), the edit heading (`:6381`), two toast messages (`:6420`, `:6430`)
   and the insert (`:6442`). No other resource stores a herd name or a herd id.

So a rename would relabel exactly one row, the one being renamed, and it is not
reachable anyway. **Quoting the `locations` blast radius on this row would be a
byte-identical copy of a proven pattern into a target whose scale and references
are different — the seventh cross-domain discipline, and the reason it exists.**

**What IS true of this row, and is missing from the current cell.** The basis
says "neither money nor a regulated record … classified by the stated B rule
rather than individually read." Read individually, one field is closer to a
regulated figure than that sentence allows: **`scc` is somatic cell count**, the
milk-quality measure a dairy is held to for saleability, captured in thousands
per millilitre (`:6387`, the "Somatic Cell Count (thousands, dairy only)"
input), averaged at `:6361-6362` and published as a KPI at `:6370`.
`vaccinationCompliance` is the same shape — a percentage bounded `0..100` at the
input (`:6386`), averaged at `:6359-6360`, published at `:6369`.

**I am not raising the tier on that, and the reason is the honest one.** Nothing
in this app submits either figure anywhere: there is no report, no export and no
regulator path — `renderHerdHealth` averages them onto the screen and that is
the end of the chain. A number that only ever appears on its own dashboard is
operational, so **B stands.** What changes is that it now stands on a read rather
than on a rule, and the one field that would move it — if an SCC figure ever
became something the app *submits* — is named so the next reader does not have
to rediscover it.

**One thing worth recording separately, because it is not a tier question.**
Both KPI averages filter on `typeof … === 'number'` (`:6359`, `:6361`) and the
demo seed sets both fields to `null` (`:6333-6334`), so a fresh install shows
`—` rather than a fabricated average. That is correct and deliberate, and it is
the shape a fabricated-KPI check would otherwise flag.

### Replacement row

```
| `sv_herdhealth` | **B** | **B** | Operational data lost or wrong | No elevated confidentiality class -- READ, not inferred: the row is `{id, herd, species, headCount, lastVisit, status, vaccinationCompliance, scc}` (`sairnvet.html:6333-6334`, `:6442`). A herd is a business, not a person; no PII, PHI, privileged communication or financial-account detail | INDIVIDUALLY READ 2026-09-29, and the B holds on a reading rather than on the blanket rule. `scc` is somatic cell count, the milk-quality figure a dairy is held to for saleability (`:6387`), and `vaccinationCompliance` is a bounded percentage (`:6386`); both are averaged (`:6359-6362`) and published as KPIs (`:6369-6370`). **Neither is submitted anywhere** -- no report, no export, no regulator path; the chain ends at the dashboard, which is why this is operational and not a regulated record. If an SCC figure ever becomes something the app SUBMITS, this row rises. **No rename blast radius, checked both ways:** the herd name is not editable at all (`openHerdEdit` `:6374-6398` exposes only headCount, lastVisit, status, compliance and scc; `saveHerdEdit` `:6405-6421` writes only those), and no resource outside `sv_herdhealth` stores a herd name or id -- all seven `.herd`/`herd:` sites in `sairnvet.html` are inside its own code. Copying the `locations` rename basis here would be a byte-identical pattern transplanted into a target with different scale and references |
```

---

## What this document does NOT do

- **It does not write to `docs/CRITICALITY-TIERS.md`.** That file is hank's
  (`hank-queue13` and `queue22 item 6` both name it). The two rows above are
  text to paste.
- **It does not write to `docs/tier-a-reviews.json`.** Also hank's. Neither row
  is Tier A, so neither needs a review obligation opened; if the SCC submission
  path named above is ever built, that changes.
- **It does not record a verdict on the auditor's wording.** I could not read
  the auditor's log and did not try. What is recorded is what the code says,
  and where the brief I was handed disagreed with the code, the disagreement is
  written down rather than resolved in the brief's favour.
