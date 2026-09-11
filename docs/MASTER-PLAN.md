# Master plan — where every vertical actually stands, and what "finished" means

**Written 2026-09-10 (Fourth).** Michael's ask: an accurate current status across every vertical, plus an honest combined finish-line definition — *built AND tiered AND traceable AND fault-tested* — because nobody had written down what that combined end state looks like.

**What this is NOT.** `docs/2026-09-10-verification-programme-plan.md` (Cody) is the SCOPE and ORDER of the four-part verification programme. This is the STATUS against it, per vertical, plus the definition of done. Two documents, two questions; this one cites that one rather than restating it.

**Every number below is derived, not asserted** — from `api/_resources/*.js`, `docs/traceability-matrix.md`, and the test files on disk. Re-derive rather than trust it: this platform has a standing rule about that, and this document is exactly the kind that goes stale.

---

## The finish line, defined

A vertical is **FINISHED** when all four are true of it. Each is checkable by something that already exists, which is the point — a definition nobody can verify is a wish.

| # | Gate | Checkable by | What "done" means |
|---|---|---|---|
| 1 | **BUILT** | `api/_resources/<app>.js` + its `sql/*_schema.sql` run on the live licence | Its business records reach a server. Not "the code exists" — the migration is run and a real write has been observed |
| 2 | **TIERED** | `tools/criticality_tier_check.py` | Every registered resource has a tier, and every Tier A carries individually-written evidence |
| 3 | **TRACEABLE** | `tools/traceability_matrix.py --check` | Every test names a requirement a reader can check, so an auditor can tell what would be lost by deleting it |
| 4 | **FAULT-TESTED** | a mutation probe that plants a real defect in that app's source and proves a guard catches it | The guards are known to DENY, not merely to pass. A guard that has never been red is not known to be a guard |

**Gate 1 is the only one with a live dependency** — an unrun migration makes a vertical not-built however good its code is. Gates 2–4 are repo-verifiable.

---

## Status, per vertical

`res` = registered resources · `suites` = test files named for that app · `traced` = of those, how many the matrix can tie to a stated requirement · `fault` = probes that plant a real defect into that app's source.

| Vertical | res | Tiered | suites | traced | fault | Gaps |
|---|---|---|---|---|---|---|
| `sairnbiz` | 10 | ✅ | 5 | 4 | 1 | — |
| `sairnbuild` | 32 | ✅ | 3 | 1 | 1 | — |
| `sairncare` | 13 | ✅ | 13 | 0 | 1 | **nothing traced** |
| `sairncash` | 0 | ✅ | 2 | 0 | 0 | — |
| `sairncode` | 28 | ✅ | 8 | 2 | 1 | — |
| `sairndental` | 24 | ✅ | 25 | 8 | 8 | — |
| `sairndesign` | 18 | ✅ | 1 | 1 | 1 | — |
| `sairnfreedom` | 35 | ✅ | 2 | 2 | 1 | — |
| `sairngrounds` | 30 | ✅ | 1 | 1 | 1 | — |
| `sairnlaw` | 19 | ✅ | 46 | 12 | 3 | — |
| `sairnlegacy` | 36 | ✅ | 1 | 1 | 1 | — |
| `sairnmechanical` | 6 | ✅ | 5 | 1 | 1 | — |
| `sairnroofing` | 27 | ✅ | 26 | 1 | 0 | **no fault probe** |
| `sairnscape` | 12 | ✅ | 1 | 0 | 1 | **nothing traced** |
| `sairnsenior` | 15 | ✅ | 10 | 2 | 2 | — |
| `sairnvet` | 41 | ✅ | 4 | 2 | 3 | — |
| `stonedesk` | 36 | ✅ | 37 | 19 | 3 | — |

**Platform totals: 382 registered resources, 186 dedicated suites, 53 of them traced, 14 fault probes that plant into real source.**

---

## The gaps, in the order they deserve attention

1. **~~Three verticals with no dedicated test suite~~ — ALL THREE CLOSED 2026-09-10.** `sairnfreedom`, `sairndesign` and `sairngrounds` each now have a first suite and a fault probe. **The gap that replaced it is smaller and sharper:** each of those suites is a SOURCE-AGREEMENT suite. None of them makes a live write, so gate 1 is still the open one for all three.

  **⚠ And one finding from building them is worth more than the suites: a by-name guard that iterates the REGISTRY can be switched off by removing the resource from the registry.** The first version of both suites did exactly that — the fault probe's arm reported no failure because the test had stopped existing, not because the suite tolerated the defect. They now read Tier A from `docs/CRITICALITY-TIERS.md` instead. **Any other guard on this platform that derives its own subject from the thing it is guarding has the same hole.**
2. **Fault testing is concentrated, not spread.** 14 probes plant into real source, and eight of them are SAIRNdental's. `sairnfreedom`, `sairnroofing` have none. Gate 4 is the one most likely to be quietly skipped, because a suite that passes looks identical to a suite that cannot fail.
3. **Traceability is 86 of 273 across the platform** (`docs/traceability-matrix.md`). An untraced test is not a bad test; it means no source states what it is for in a form a machine can read. The fix is one line in the open-work index or a `GUARD_TESTS` entry — not a new document.
4. **Gate 1 is PARTLY ANSWERED as of 2026-09-10 — see the gate 1 section below.** Seven migrations are confirmed run, attested directly by Michael, and the two largest are confirmed only in PART: `stonedesk_data_schema.sql` covers the 21 backup tables and not StoneDesk's original schema, and `sairndental_vendor_schema.sql` covers the vendor tables only. **SAIRNlaw, SAIRNbiz, SAIRNbuild and StoneDesk's original schema remain unverified and are named as such** rather than left to read as fine by omission.

---

## Gate 1 — live migration status

**This is the one gate that is ATTESTED, not derived.** Everything else in this
document is read from the repo; whether a migration has actually been run against
a live licence cannot be. So this section names who confirmed it and when, and it
does not extend past what they said.

### Confirmed RUN — Michael, directly, 2026-09-10

| SQL file | Covers | Scope of the confirmation |
|---|---|---|
| `sql/stonedesk_data_schema.sql` | `stonedesk` | The 21 backup tables. **Not** StoneDesk's original schema |
| `sql/sairnvet_data_schema.sql` | `sairnvet` | Its data schema |
| `sql/sairnfreedom_data_schema.sql` | `sairnfreedom` | Its data schema |
| `sql/sairnfreedom_license_seed.sql` | `sairnfreedom` | Its licence seed |
| `sql/sairndental_vendor_schema.sql` | `sairndental` | The **vendor** tables only |
| `sql/sairnmechanical_records_schema.sql` | `sairnmechanical` | Its records schema |
| `sql/license_keys_grant_review_2026-09-05.sql` | platform | The `license_keys` grant review, run end to end |

### Still UNVERIFIED, and named rather than assumed

**The confirmation above covers 2026-09-10 only.** Anything applied in an earlier
session needs its own check — from that session's records or a fresh live read.
Named explicitly, because an app absent from both lists reads as "probably fine":

- **SAIRNlaw** — its deadline engine runs on live per-licence tables, and
  `tools/sairn_load_state_check.py --app sairnlaw` can answer it with a key
- **SAIRNbiz** — though ONE live write through its path was observed on
  2026-09-10 (`syncEmps()` returned 200 with `written: 1`), which proves the
  `employees` table exists and is writable; that is narrower than "its schemas
  are run"
- **StoneDesk's ORIGINAL schema** — distinct from the 21 backup tables above
- **SAIRNbuild**
- **Every app not named in either list**, which is most of them

### How to close this gate without guessing

`tools/sairn_load_state_check.py --app <app> --key <key>` answers it for the four
reference apps from any clone. For the rest it is one read per app by somebody
holding the licence keys. **A table cell here must never be filled from
inference** — an app whose code looks complete tells you nothing about whether
its migration ran, and that gap is precisely what this gate exists to close.


---

## Timeline — what can honestly be said

**No dates.** I do not control session scheduling, and a date invented here would be exactly the kind of confident wrong number this platform keeps finding. What can be stated is the remaining WORK, which is what a timeline is built from:

| Remaining | Size |
|---|---|
| Dedicated suites for the three verticals with none | 3 apps, each needing its first suite — the biggest and least optional item |
| Fault probes for the verticals with none | 2 apps |
| Untraced tests | 187 platform-wide, each closable by one line naming its requirement |
| Live-state confirmation for gate 1 | **7 migrations confirmed 2026-09-10**; the rest is one read per app against its live licence, by someone holding the keys |

**The honest shape:** gates 2 and 3 are mechanised and cheap to keep true. Gate 4 is the expensive one, and gate 1 is the one that needs somebody with live access rather than more code.

---

## What would make this document wrong

It is a snapshot of derived numbers, so it goes stale the moment anyone adds a test or a resource. **Re-run the derivation rather than trusting the table** — the same standard the criticality register, the SOUP register and the traceability matrix all hold themselves to. If a number here disagrees with a tool, the tool is right.
