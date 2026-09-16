# Blind review worksheet -- judge BEFORE you see the recorded answer

**8 record(s).** The recorded `severity` has been removed from every one. The vocabulary is `critical`, `high`, `moderate`, `low` -- seeing the LIST is fine, seeing which one applies is the anchor this flow exists to remove.

For each record write YOUR OWN severity and a DEFEATER: what would have to be true for that severity to be wrong. A judgment with no defeater is refused, because recording a word is not judging and the reveal would re-anchor you for the next one anyway.

Submit as JSON: `[{"id": "...", "severity": "...", "defeater": "..."}, ...]`, then

    python tools/blind_review.py --submit <your-file.json>

---

## R01

- **commit:** 5d0f4459b552
- **date:** 2026-09-15
- **app:** PLATFORM
- **layer:** product
- **subject:** fix(cron): the watchdog was retrying ITSELF into an HTTP 508 and had latched itself FAILING -- plus the second scheduler item 54 was missing
- **summary:** SAIRN_OPS_EMAIL is not set in production, so every alert api/cron-watchdog.js has ever planned ended 'nobody was told' -- visible only inside a per-job action detail. The watchdog's own header calls a silently inert alerting system worse than having none, because the existence of a watchdog is itself an assurance somebody is relying on. Fixed by asking the channel question unconditionally every run and surfacing notify_channel on its own axis; setting the variable remains Michael's.
- **files:** .github/workflows/cron-liveness.yml, api/_lib/cron-response.js, api/cron-watchdog.js, api/cron-watchdog.test.js, docs/2026-09-15-item54-second-watchdog.md, docs/MASTER-PLAN.md, docs/SAIRN-OPEN-WORK-INDEX.md, docs/TOOLING-INVENTORY.md, docs/traceability-matrix.md, tests/run_cron_liveness_probe.py, tools/cron_liveness_check.py
- **lines_added:** 964
- **lines_removed:** 35
- **detection_method:** live-verification
- **injection_phase:** config
- **rules:** 1.11

---

## R02

- **commit:** 8f9a727f008c
- **date:** 2026-09-11
- **app:** PLATFORM
- **layer:** product
- **subject:** fix(platform): every write transport is bounded -- twelve had no timeout anywhere
- **summary:** twelve of fifteen write transports had no timeout on any path and two more bounded only a read, so a hung fetch left ~260 careful await-and-toast call sites silent forever
- **files:** SAIRN-ACTIVE-WORK-cody.md, docs/SAIRN-OPEN-WORK-INDEX.md, docs/traceability-matrix.md, sairnbiz.html, sairnbuild.html, sairncare.html, sairncode.html, sairndental.html, sairndesign.html, sairnfreedom.html, sairngrounds.html, sairnlaw.html, sairnlegacy.html, sairnmechanical.html, sairnscape.html, sairnsenior.html, sairnvet.html, stonedesk.html, tests/faults/grd_write_faults.js, tests/faults/transport_timeout_sweep.js, tests/public_catalog_no_false_empty.js, tests/refusal_not_empty.js, tests/run_write_path_scan_probe.py, tests/sairndental_outbound_queue.js, tests/sairndental_write_failure_voice.js
- **lines_added:** 935
- **lines_removed:** 23
- **detection_method:** static-checker
- **injection_phase:** design
- **rules:** 1.5

---

## R03

- **commit:** a7103a30fb94
- **date:** 2026-08-26
- **app:** sairnroofing
- **layer:** product
- **subject:** fix(sairnroofing): the photo rule now bites, ids are server-verified, and unavailable material stops posing as a met threshold
- **summary:** sairnroofing's photo requirement did not actually refuse, record ids were minted client-side rather than server-verified, and material that was UNAVAILABLE still counted toward a met threshold -- so a claim could present as fully evidenced on photos that were never required, ids the server never issued, and stock that was not there. rf_claim_photos is Tier A.
- **files:** api/_lib/roofing-damage-assessment-endpoint.test.js, api/_lib/roofing-damage-assessment.js, api/_lib/roofing-damage-assessment.test.js, api/_resources/extra-actions.test.js, api/sd-data.js, sairnroofing.html
- **lines_added:** 301
- **lines_removed:** 33
- **detection_method:** code-review
- **injection_phase:** design
- **rules:** 

---

## R04

- **commit:** e414b563f0f9
- **date:** 2026-09-13
- **app:** PLATFORM
- **layer:** product
- **subject:** feat(api): item 8 -- the three untested proxy guardrails, and garbage was buying the ceiling
- **summary:** sanitizeTools resolved a malformed max_uses to the CEILING, not the floor -- Number(x) || MAX_TOOL_USES_CEILING is falsy for 0, NaN, null and a non-numeric string, so each bought 5 billed web searches; and Number([2]) coerced an array to 2. Both are the trap cappedMaxTokens() type-checks against thirty lines away in the same file
- **files:** api/claude-guardrail-probes.test.js, api/claude.js, docs/SOUP-REGISTER.md
- **lines_added:** 401
- **lines_removed:** 5
- **detection_method:** fault-injection
- **injection_phase:** coding
- **rules:** 1.11

---

## R05

- **commit:** f98c1b08d3fc
- **date:** 2026-09-14
- **app:** sairncash
- **layer:** product
- **subject:** feat(tools): item 40 -- and it found a LIVE unauthenticated route into a customer's billing
- **summary:** api/sairncash/portal.js returns a Stripe Billing Portal URL -- card on file, invoice history, the power to cancel -- to an UNAUTHENTICATED POST carrying only a subscription id, which Stripe puts in dashboards, webhooks, emails and CSV exports and never treated as a secret. The file refuses a cus_ id for exactly this reason and then accepts a sub_ id of comparable entropy. NOT EXPLOITABLE TODAY and the reason is an accident, not a control: production's STRIPE_SECRET_KEY is present but is an EXPIRED sk_test_ key, so every call dies before reaching a customer. The day a working key is installed, nothing announces it -- the same re-read-trigger failure that left the SOUP register claiming the key was unset
- **files:** docs/2026-09-14-tier-a-bypass-audit.md, docs/MASTER-PLAN.md, docs/SOUP-REGISTER.md, docs/TOOLING-INVENTORY.md, docs/traceability-matrix.md, tests/run_tier_a_bypass_probe.py, tools/tier_a_bypass_check.py, tools/tooling_inventory.py
- **lines_added:** 489
- **lines_removed:** 18
- **detection_method:** code-review
- **injection_phase:** design
- **rules:** 

---

## R06

- **commit:** cac3edd5c19f
- **date:** 2026-09-15
- **app:** sairnlaw
- **layer:** product
- **subject:** fix(sairnlaw,platform): the advisory lock was doing nothing under REPEATABLE READ -- on attorney trust money, and in two other places
- **summary:** law_check_and_insert_disbursement holds an advisory lock while summing the trust balance and then inserting, with nothing requiring READ COMMITTED. pg_advisory_xact_lock serialises ACQUISITION and not the SNAPSHOT, so under REPEATABLE READ two concurrent disbursements against one client each sum a balance from before the other committed, both pass the sufficiency check, and both insert -- an overdrawn IOLTA client trust ledger with the lock held correctly throughout. Not exploitable on the current deployment, which uses the default isolation; one ALTER ROLE statement away, and that statement reads as a hardening change.
- **files:** docs/2026-09-15-advisory-lock-isolation-sweep.md, docs/MASTER-PLAN.md, docs/SAIRN-OPEN-WORK-INDEX.md, docs/TOOLING-INVENTORY.md, docs/traceability-matrix.md, sql/cl_rate_limit_consume_fn_2026-09-04.sql, sql/sairnlaw_trusttx_functions.sql, tests/run_advisory_lock_isolation_probe.py, tools/advisory_lock_isolation_check.py, tools/report_only_checks.py
- **lines_added:** 990
- **lines_removed:** 22
- **detection_method:** static-checker
- **injection_phase:** design
- **rules:** 

---

## R07

- **commit:** 5b98fd27209b
- **date:** 2026-09-10
- **app:** sairndental
- **layer:** product
- **subject:** fix(sairndental): a dropped socket, a hang and a partial response were all silent
- **summary:** A dropped socket produced NO toast at all, because a rejection never reaches a .then(ok => ...) handler -- and two callers attach none, so it was an unhandled rejection
- **files:** sairndental.html, tests/dnt_vendor_write_confirmation.js, tests/faults/dnt_vendor_write_faults.js
- **lines_added:** 187
- **lines_removed:** 76
- **detection_method:** fault-injection
- **injection_phase:** coding
- **rules:** 1.5

---

## R08

- **commit:** a58af8caae0b
- **date:** 2026-09-14
- **app:** sairnbiz
- **layer:** product
- **subject:** fix(sairnbiz): the three-way match refused CORRECT bills -- money decided in floats
- **summary:** sbThreeWayMatch decided money equality in floating point against a tolerance of exactly 0.00, so two partial deliveries of 1870.93 and 1957.54 against a 3828.47 PO summed to 3828.4700000000003 and a correct bill was REFUSED with the message 'billed $3828.47 against $3828.47 actually received' -- two identical figures and a refusal nobody could act on
- **files:** sairnbiz.html, tests/sairnbiz_bill_cannot_settle_unmatched.js
- **lines_added:** 109
- **lines_removed:** 7
- **detection_method:** independent-review
- **injection_phase:** coding
- **rules:** 1.11

