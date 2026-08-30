# SAIRNvet audit gap, re-derived against the file

**The flagged number was ~44 panels "not yet audited." The real number is 9.**
Not because work was missed, but because 44 is the **Session 58** figure and four
later sessions worked it down. Re-derived from `sairnvet.html` as it stands on
`origin/main`, not from any handoff count.

---

## 1. The handoff chain already answered most of it

| Handoff | "Remaining panels not yet audited" |
|---|---|
| SESSION 58 | **44** |
| SESSION 59 | 30 |
| SESSION 60 | 25 |
| SESSION 61 | 24 |
| SESSION 62 | **20** |

Session 62 is the newest SAIRNvet handoff on disk. So the flagged 44 was four
handoffs stale before this pass began — exactly the failure mode CLAUDE.md
describes for counters, and the reason the instruction was to re-derive rather
than trust.

## 2. Of Session 62's twenty, eleven are now done

The documented audit signature for this app is a real data model: an
`sv_<name>` localStorage store plus a `render<Name>()` function that computes
KPIs from it. Checked mechanically against the current file:

| S62 panel | `sv_` store | render fn | |
|---|---|---|---|
| panel-staff | `sv_staff` | `renderStaff` | done |
| panel-multisite | `sv_multisite` | `renderMultisite` | done |
| panel-documents | `sv_documents` | `renderDocuments` | done |
| panel-referrals | `sv_referrals` | `renderReferrals` | done |
| panel-petinsurance | `sv_petinsurance` | `renderPetInsurance` | done |
| panel-portal | `sv_portal` | `renderPortal` | done |
| panel-boarding | `sv_boarding` | `renderBoarding` | done |
| panel-wellness | `sv_wellness` | `renderWellness` | done |
| panel-mobilevet | `sv_mobilevet` | `renderMobileVet` | done |
| panel-communications | `sv_comms` | `renderComms` | done |
| panel-reminders | `sv_reminders` | `renderReminders` | done |

The file now carries **45** `sv_*` stores and **42** render functions.

## 3. The nine that are genuinely still unaudited

`settings`, and the eight species-patient panels: `companion-patients`,
`equine-patients`, `large-patients`, `exotic-patients`, `avian-patients`,
`reptile-patients`, `aquatic-patients`, `zoo-patients`.

**All nine are static shells.** Verified directly rather than inferred — each
panel's `<table id="X-table">` appears exactly twice in the whole file (the `id`
attribute and one `exportTableCSV(...)` call) and **zero times in any
`getElementById`**. Nothing populates them.

| Panel | KPIs | fabricated $ | static rows |
|---|---|---|---|
| settings | 4 | 0 | 3 |
| companion-patients | 4 | **$156K** | 2 |
| equine-patients | 4 | **$1,640** | 2 |
| large-patients | 4 | **$198K** | 2 |
| exotic-patients | 4 | **$89K** | 2 |
| avian-patients | 4 | **$76K** | 2 |
| reptile-patients | 4 | **$52K** | 2 |
| aquatic-patients | 4 | **$18K** | 2 |
| zoo-patients | 4 | **$64K** | 2 |

Representative, `companion-patients`: `287 Active Patients`, `1,204 Visits YTD`,
`94% Vaccination Compliance`, `$156K Revenue YTD`, and two invented rows — Max
the Golden Retriever and Whiskers the Persian. No function computes any of it.
Textbook Guardian Check 0b.

**Each also ships an Export CSV button** wired to the fabricated table, so a
customer can export the invented rows as though they were records.

## 4. Session 62's own prediction was wrong, and this is the useful part

That handoff said financial fabrication had been *"found and fixed in every
money-touching panel reached so far,"* and advised that the remainder are
*"mostly clinical/operational, so watch for the same pattern … rather than
assuming dollar-figure fabrication specifically."*

**Eight of the nine remaining panels carry a fabricated dollar figure.** The
species panels were classified as clinical because of their names; every one of
them ends its KPI row with revenue. A reader who took that guidance literally
would have deprioritised exactly the panels that still show invented money.

## 5. Two smaller corrections to the handoff

**Nav/panel is 55/55, not 54/54.** Session 62's step 9 says *"Reconcile
nav↔panel counts (must stay 54/54) before pushing."* The current file has **55**
panel divs and **55** `svNav('…')` targets, fully reconciled — one panel has been
added since. Anyone enforcing 54 would now fail a correct file.

**`zoo-patients` is not purely static.** It has a real, wired AI feature —
`getZooProtocol()` reads `zoo-species` / `zoo-weight` / `zoo-procedure` through
`getElementById` and writes into `zoo-result`. That part works. Its KPI row and
patient table are fabricated like the others, so it is one real feature bolted
onto a fabricated shell rather than a shell outright.

## 6. Recommended order

1. **The seven pure species shells** — `companion`, `equine`, `large`,
   `exotic`, `avian`, `reptile`, `aquatic`. Identical shape, so one data model
   (`sv_patients` already exists and `renderPatients` already exists) filtered by
   species covers all seven. This is one piece of work, not seven.
2. **`zoo-patients`** — same treatment, preserving `getZooProtocol()`.
3. **`settings`** — different shape, no money, lowest risk. Last.

The eight-panel group sharing one store is the reason the remaining gap is much
smaller in effort than in panel count.

## 7. What was not done

- **No panel was fixed.** This pass re-derives the gap; it does not close it.
- **Nothing was verified in a browser.** All findings are from the source plus
  the mechanical checks above. The fabricated KPIs are certain (no computing
  function exists); what a customer actually sees on each panel is not.
- **The eleven counted "done" were verified by signature** — the presence of a
  matching store and render function — **not by re-auditing their content.** A
  panel could carry a store, a render function, and still have a defect. That is
  a weaker claim than "audited clean," and is stated that way on purpose.
