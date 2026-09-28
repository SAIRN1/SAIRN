# CC self-audit — skill log, tool inventory, methodology registry

**2026-09-28.** Asked for: anything superseded, unused, never validated, or
missing a check I found I needed this week. Derived from `git`, the claim
history, `docs/tier-a-reviews.json`, the report-only registry and the tooling
inventory — never from a summary. Fixed what I own; the rest is named with its
owner.

---

## 1. FIXED — the tool built to catch unmeasured checkers was itself unmeasured

`tools/checker_denominator.py` was written this session to catch a checker whose
coverage falls silently. Its own first audit found it **unregistered, unwired
and unprobed**. Registered in `report_only_checks.REGISTRY` in the same push,
with its real 12.3 s runtime and its first baseline as evidence.

This is the platform's most-repeated shape and it landed inside an hour of the
tool existing. Recording it rather than quietly registering it is the point.

## 2. FIXED — a claim left active for 22 hours after the work finished

`cc-1790477581`, the SAIRNcash safe-harbor claim, opened
**2026-09-27T02:53:01Z** and never released. The work landed the same day. For
22 hours every other clone saw `sairncash.html`, `tests/sairncash_safe_harbor.js`
and `tools/push_retry.py` as taken by a session that had moved on.

**The claim tool cannot catch this** — it has no idea when work ends. What
catches it is `tools/sairn_self_state.py`, which this audit ran, and which is
not on any cadence. Released as `b0f6eb42`.

## 3. FIXED — the duplicate-description refusal, twice in one session

The inventory generator refused twice today because a tool gained a REGISTRY
entry while keeping its PURPOSES line: `probe_anchor_freshness.py` this morning
and `checker_denominator.py` this evening. **Both refusals were correct** — two
descriptions of one tool are two sources that can disagree.

It is now written into the file as a comment where each line was deleted: **this
is the shape to expect whenever an unwired tool becomes a wired one**, so the
third time is a lookup rather than a rediscovery.

---

## 4. NOT FIXED, AND NOT MINE TO FIX — 7 Tier A obligations I authored, all past deadline

`docs/tier-a-reviews.json`, read 2026-09-28. **30 obligations open across all
four build sessions. Seven were authored by `cc`. Every one is past the
register's own 24-hour deadline**, and **none has a reviewer assigned** —
`reviewer_session` is set only at discharge, so an open row names nobody.

| opened | age | resources |
|---|---|---|
| 2026-09-24T23:40:40Z | 75 h | `law_clients`, `law_deadlines`, `law_trusttx`, `quotes` |
| 2026-09-25T23:51:26Z | 51 h | `sdn_invoices`, `sen_clients`, `sf_youth_participants` |
| 2026-09-26T01:04:07Z | 50 h | `sdn_timeentries`, `sf_accounts`, `sf_members`, `sf_vehicle_service` |
| 2026-09-26T01:43:54Z | 49 h | `alf_clients`, `alf_incidents`, `alf_mar`, `law_matters`, `rf_claim_p…` |
| 2026-09-26T13:13:44Z | 37 h | `alf_claim_routes`, `alf_incidents`, `alf_mar`, `alf_op_audits`, … |
| 2026-09-26T13:38:34Z | 37 h | `sv_audit_log` |
| 2026-09-27T01:29:46Z | 25 h | `sc_anesthesia_base_units` |

**I cannot discharge these** — the whole point of a Tier A review is that the
author is not the reviewer, and self-discharging is the failure the review
ledger exists to prevent.

**The subjects are the argument for somebody taking them:** medication
administration records, an audit log, trust accounting and anaesthesia base
units.

**AND THE PLATFORM-WIDE NUMBER IS THE REAL FINDING.** 30 open across four
authors — `hank` 9, `fourth` 8, `cc` 7, `cody` 6 — against a deadline of 24
hours that **none of them is meeting**. A deadline nothing enforces and everyone
misses is not a deadline; it is a field. Either the cadence is wrong or the
enforcement is missing, and deciding which is not a one-session call.

## 5. NOT FIXED — `overrun_inversion_scan.py` has no external probe

It carries a 9-arm internal selftest locked against synthetic sources in both
directions, which is the lighter standard this platform accepts for a
report-only checker. It has **no `tests/run_*_probe.py`**, so nothing drives it
from outside its own assumptions. Stated rather than left for the next audit.

## 6. NOT FIXED — 59 of 63 registry checkers publish no denominator

`checker_denominator.py` covers four. The other 59 report clean numbers about
populations nobody has counted — which is precisely the condition that let two
anchor checkers run for days over disjoint halves of one population. Extending
it is one `universe`/`checked` pair per tool.

## 7. NOT FIXED — 16 anchor findings unmasked and left

Fixing `mutation_anchor_check.py`'s permanent exit 2 revealed 15 vanished
anchors and one ambiguous, in 8 probe files. Most target `api/sd-data.js`, which
another session holds. Filed rather than fixed.

---

## 8. The methodology registry — what this week added, and what it did not

`docs/2026-09-13-cross-domain-disciplines.md` is the standing registry. **Two
things this week are candidates and neither is added here**, because adding a
discipline is a platform decision and not a session's to take unilaterally:

- **Publish the denominator.** A checker must state how many candidates exist,
  how many it read, and how many it could not — and the unreadable ones must be
  NAMED, not absent. Earned by the zero-overlap incident. Implemented in
  `checker_denominator.py`; the *rule* is not registered.
- **A refusal must be counted, not just returned.** Three separate tools this
  week folded a could-not-tell into a pass by accident — `app_files()` returning
  `[]`, `resolve()` returning `(None, old)` for a resolved target, and a KPI
  filtering `null > 0`. The existing PR §1.11 covers the *state*; what recurs is
  the **consumer** silently dropping it.

**What IS registered, correctly, and got used four times this week:** class 26
(a fixture or anchor that expires on legitimate growth) and the new class 27
(a cap on a ratio that turns an overrun into completion) in
`.claude/skills/sairn-code-scrubber/SKILL.md`.

---

## 9. What this audit cannot see

- **Whether any of the work was good.** It checks that each claim left a trace,
  that obligations are named, and that tools are wired. `sairn_self_state.py`
  says the same thing about itself in its own words.
- **Attribution.** Every clone commits as one git identity, so only commits
  touching this session's own claim file or worklog are attributable — 136 of
  them in the window. Everything else is unattributed by construction.
- **Whether a worklog entry is true.** It compares vocabulary, not facts, and
  reports `UNCHECKABLE` rather than accusing when a claim is all stop-words.
- **The NO-LOG rows.** `sairn_self_state.py` lists 16 older claims with no
  matching worklog entry in the window. They are a matcher limitation as much as
  a finding, and separating the two would need a read per row.
