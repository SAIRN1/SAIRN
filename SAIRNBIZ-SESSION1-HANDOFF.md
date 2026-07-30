# SAIRNbiz — Session 1 Handoff

First SAIRNbiz-specific handoff. Prior sessions touched this file only
incidentally (`ce43609`'s scanner-portability fix, `9b55f40`'s color
collision resolution) — this is the first session that actually opened
and worked SAIRNbiz itself, via `sairn-adversarial-reviewer` and
`sairn-visual-review` passes.

## 1. Verified current state

- `main` HEAD (local and pushed): `bb984c6bca6d3f37dfa948f3118e75cc70b9c761`
- Local checks re-run fresh at this HEAD: `checkblocks.py` 2/2,
  `div_balance_check.py` 715/715 balanced, `duplicate_global_check.py`
  54/0 duplicates, `panel_nesting_check.py` 20/20 safe, 0 trapped.
  **`key_collision_check.py` and `missing_dom_target_check.py` are
  confirmed blind on this file** — both return `0` because SAIRNbiz
  routes storage/DOM access through wrapper functions (`st()`/`ld()`/
  `$()`) that neither scanner's regex recognizes. A `0` from either is
  not evidence of cleanliness; documented in `sairn-portfolio-triage`'s
  Scanner Portability section, not fixed this session.

## 2. NEW backlog item — Supabase schema mismatch, NOT fixed

**`syncEmps()` has likely never actually succeeded in production.**
Discovered while live-verifying the sync-status-badge fix (§3 below):
calling the real `syncSupabase()` against the live Supabase project
triggered a genuine, reproducible failure:

```
Supabase: Could not find the 'department' column of 'employees' in the schema cache
```

This is a real infrastructure gap, not a code bug in SAIRNbiz's own
logic — `syncEmps()`'s payload (`employee_id, first_name, last_name,
role, department, employment_type, hourly_rate, start_date, phone,
email, status, source_app, updated_at`) does not match the actual
`employees` table schema currently live in the Supabase project at
`SB_URL` (`ejrlrrkvhtllxbbypdjb.supabase.co`). Deliberately **not fixed
blind this session** — the full real schema of that table isn't known
from SAIRNbiz's code alone, and guessing at a fix without seeing the
actual table definition risks either papering over the symptom (e.g.
silently dropping the `department` field) or breaking whatever else
already depends on that table's current real shape. This needs someone
to actually look at the Supabase dashboard's schema for `employees`
before touching `syncEmps()`'s payload.

**Downstream implication:** before this session's fix (§3), this failure
was invisible — the old hardcoded "Synced" badge and the fire-and-forget
upsert call meant a user would never have known sync was silently
failing every time. As of this session, the badge and toast now honestly
reflect the real failure (correctly staying "Not Synced" / showing
"Sync failed"), so the gap is now *visible* even though it isn't yet
*fixed*. Whoever picks this up next should start from the Supabase
dashboard's actual `employees` table columns, not from SAIRNbiz's
assumed payload shape.

## 3. This session's work — sairn-adversarial-reviewer + sairn-visual-review passes

First-ever adversarial-review and visual-review passes specifically on
SAIRNbiz. Found and fixed all 4 CRITICAL findings from the adversarial
pass, plus 3 of the correctness/visual findings from two visual-review
passes. 2 findings remain open (see §4).

**4 CRITICAL findings — all fixed, all live-verified:**
| Finding | Commit |
|---|---|
| `saveEmp()` silently destroyed benefits data on every edit | `1fd6a63` |
| `runPayroll()` fabricated "ACH transfers initiated" claim | `483f192` |
| `genReport('pl')` fabricated hardcoded P&L figures | `b3c57ef` |
| PIN Settings form was a complete no-op (`sb_cfg` never read) | `5305768` |

**3 of 6 visual-review findings fixed, all live-verified:**
| Finding | Commit |
|---|---|
| Payroll's Benefits Cost / Total Labor Cost inflated 8x (double `*emps.length`) | `0fa5fc6` |
| Company Profile's "StoneDesk: Synced" badge was hardcoded, contradicted real "Last Sync: Never" | `d10de33` |
| `genReport()`'s 'payroll'/'tax' types were hollow placeholders | `bb984c6` |

**Also resolved this session:** SAIRNhr/SAIRNvet color collision in
`sairn-guardian-v2`'s App File Map (`9b55f40`) — SAIRNhr moved to
`#2563EB` since it's not yet a real file, SAIRNvet (real, live) kept
`#7C3AED`. SAIRNcare/SAIRNacc (`#0D9488` collision) still pending, same
reasoning applies whenever either is actually touched.

**Also cleaned up:** a confirmed-stale duplicate copy at
`Desktop/SAIRN/sairnbiz.html` was deleted per explicit user decision —
older KPI labels, missing employee `ben{}` fields, different
invoice/tax data than the canonical git-tracked root copy.

## 4. Open items — not yet fixed

1. **Supabase schema mismatch** (§2 above) — newly found this session,
   explicitly not fixed blind. Needs the real Supabase `employees` table
   schema before `syncEmps()`'s payload can be safely corrected.
2. **Dashboard Net Margin (-40%) rendered in "good" green** — `.kt`
   subtext span never gets the `.d` (danger) class applied conditionally
   in `rDash()`. Same root cause likely affects other panels too (Hiring
   and AR showed the same static-green pattern during visual review,
   though only Hiring is formally named as its own item below — AR's
   "Collection Rate 54%" was noted as reinforcing evidence, not a
   separately fixed/tracked item).
3. **Hiring's "Avg Days Open" (60d) rendered in "good" green** despite
   being ~3x worse than its own stated 21d industry benchmark — same
   root cause as item 2.
4. **Expenses' "This Month" and "Total Recorded" KPIs always show the
   identical number** — `rExps()` computes the total once into `m` and
   assigns it to both, with no real month-vs-all-time distinction.
   Currently invisible because all seed data falls in one month; will
   silently produce a wrong "Total Recorded" once expense history spans
   multiple months.

## 5. Standard verification reminder

Verify `main` HEAD and `origin/main` match, re-run the local checks in
§1, and live-verify against `sairn.vercel.app/sairnbiz` before trusting
any specific claim above — including this one. In particular: re-confirm
`key_collision_check.py`/`missing_dom_target_check.py` are still the
scanners that need generalizing for wrapper-function indirection before
trusting a `0` from either against this file.
