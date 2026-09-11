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
| `sairndesign` | 18 | ✅ | 0 | 0 | 1 | **no dedicated suite** |
| `sairnfreedom` | 35 | ✅ | 0 | 0 | 0 | **no dedicated suite** · **no fault probe** |
| `sairngrounds` | 30 | ✅ | 0 | 0 | 1 | **no dedicated suite** |
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

1. **⚠ THREE VERTICALS HAVE NO DEDICATED TEST SUITE AT ALL: `sairndesign`, `sairnfreedom`, `sairngrounds`.** Between them that is 83 registered resources reaching a server with nothing named for them. They are not untested in the sense of being unexercised — platform-wide suites like `tests/st_reports_failure.js` cover their storage wrappers — but no file states what THEY are supposed to do. **This is the largest single gap on the platform and it is the first thing to close.**
2. **Fault testing is concentrated, not spread.** 14 probes plant into real source, and eight of them are SAIRNdental's. `sairnfreedom`, `sairnroofing` have none. Gate 4 is the one most likely to be quietly skipped, because a suite that passes looks identical to a suite that cannot fail.
3. **Traceability is 86 of 273 across the platform** (`docs/traceability-matrix.md`). An untraced test is not a bad test; it means no source states what it is for in a form a machine can read. The fix is one line in the open-work index or a `GUARD_TESTS` entry — not a new document.
4. **Gate 1 cannot be answered from the repo for every app.** Several verticals have schema files whose live state is unknown to this session. `tools/sairn_load_state_check.py` answers it for the four reference apps; the rest need a real read against the live licence, and **this document does not guess it** — the table reports what is in the repo and says so.

---

## Timeline — what can honestly be said

**No dates.** I do not control session scheduling, and a date invented here would be exactly the kind of confident wrong number this platform keeps finding. What can be stated is the remaining WORK, which is what a timeline is built from:

| Remaining | Size |
|---|---|
| Dedicated suites for the three verticals with none | 3 apps, each needing its first suite — the biggest and least optional item |
| Fault probes for the verticals with none | 2 apps |
| Untraced tests | 187 platform-wide, each closable by one line naming its requirement |
| Live-state confirmation for gate 1 | one read per app against its live licence, by someone holding the keys |

**The honest shape:** gates 2 and 3 are mechanised and cheap to keep true. Gate 4 is the expensive one, and gate 1 is the one that needs somebody with live access rather than more code.

---

## What would make this document wrong

It is a snapshot of derived numbers, so it goes stale the moment anyone adds a test or a resource. **Re-run the derivation rather than trusting the table** — the same standard the criticality register, the SOUP register and the traceability matrix all hold themselves to. If a number here disagrees with a tool, the tool is right.
