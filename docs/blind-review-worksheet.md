# Blind review worksheet -- judge BEFORE you see the recorded answer

**6 record(s).** The recorded `severity` has been removed from every one. The vocabulary is `critical`, `high`, `moderate`, `low` -- seeing the LIST is fine, seeing which one applies is the anchor this flow exists to remove.

For each record write YOUR OWN severity and a DEFEATER: what would have to be true for that severity to be wrong. A judgment with no defeater is refused, because recording a word is not judging and the reveal would re-anchor you for the next one anyway.

Submit as JSON: `[{"id": "...", "severity": "...", "defeater": "..."}, ...]`, then

    python tools/blind_review.py --submit <your-file.json>

---

## R01

- **commit:** d6b3f6e929ec
- **date:** 2026-09-13
- **app:** PLATFORM
- **layer:** product
- **subject:** fix(dental,grounds,scape): stamping is not storage, and a stamp that fails must not lose the save
- **summary:** the _m stamp call sat INSIDE the storage try in st()/scpSt() across dental, grounds and scape, so a stamping failure skipped the write and told the user the browser's storage was full -- a false reason and a lost save
- **files:** SAIRN-ACTIVE-WORK-cody.md, docs/SAIRN-OPEN-WORK-INDEX.md, docs/traceability-matrix.md, sairndental.html, sairngrounds.html, sairnscape.html, tests/run_truthy_sum_probe.py, tests/sairn_storage_wrapper_honesty.js, tools/truthy_sum_baseline.json
- **lines_added:** 174
- **lines_removed:** 14
- **detection_method:** fault-injection
- **injection_phase:** coding
- **rules:** 1.5

---

## R02

- **commit:** 72fa70003224
- **date:** 2026-09-14
- **app:** PLATFORM
- **layer:** test
- **subject:** fix(tests): the trial-gate tripwire died in a snapshot re-capture for the third time
- **summary:** a negative control whose PRECONDITION was another session's unfixed defect expired the moment they fixed it -- check11_probe asserted the tree still carried a control byte in a file inside fourth's claim; it plants its own now
- **files:** SAIRN-ACTIVE-WORK-cody.md, docs/SAIRN-OPEN-WORK-INDEX.md, docs/traceability-matrix.md, tests/license_trial_gate_probe.py, tests/push_gate/check11_probe.py, tests/push_gate/missing_checker_probe.py, tests/run_mutation_anchor_probe.py, tools/mutation_anchor_check.py
- **lines_added:** 200
- **lines_removed:** 20
- **detection_method:** code-review
- **injection_phase:** design
- **rules:** 1.3

---

## R03

- **commit:** bfe591a24c6a
- **date:** 2026-09-10
- **app:** sairngrounds
- **layer:** product
- **subject:** fix(sairngrounds,tools): forty-three writes, no timeout, and a weather message said otherwise
- **summary:** cmSavePoints() read nothing from its push while all three callers toasted Point captured unconditionally, so a course point that never reached the server was announced as captured
- **files:** SAIRN-ACTIVE-WORK-cody.md, docs/SAIRN-OPEN-WORK-INDEX.md, docs/traceability-matrix.md, sairngrounds.html, tests/faults/grd_write_faults.js, tests/run_write_path_scan_probe.py, tools/write_path_fault_scan.py
- **lines_added:** 785
- **lines_removed:** 12
- **detection_method:** code-review
- **injection_phase:** coding
- **rules:** 1.5

---

## R04

- **commit:** 8dfde7be2b1b
- **date:** 2026-09-13
- **app:** PLATFORM
- **layer:** tooling
- **subject:** test(push-gate): my reason for leaving check 3 uncovered was wrong, and it was cheap to test
- **summary:** FAIL-OPEN in the blocking push gate: check 3 is wrapped in if os.path.isfile(pf), so with tools/sairn_sql_preflight.py absent a missing-table SQL push is allowed in silence and the gate never says it stopped checking
- **files:** SAIRN-ACTIVE-WORK-cody.md, docs/SAIRN-OPEN-WORK-INDEX.md, docs/traceability-matrix.md, tests/push_gate/check2_and_check5_probe.py, tests/push_gate/check3_probe.py
- **lines_added:** 339
- **lines_removed:** 11
- **detection_method:** fault-injection
- **injection_phase:** design
- **rules:** 1.11

---

## R05

- **commit:** d85b98efecb8
- **date:** 2026-09-11
- **app:** PLATFORM
- **layer:** tooling
- **subject:** fix(tools): the second half of the sweep -- three checkers reported clean while scanning nothing
- **summary:** report_only_checks.py reported a clean platform after scanning zero apps: an empty target list skipped the per-app loop entirely, so 132 checker runs could vanish into a report byte-identical to a clean sweep
- **files:** SAIRN-ACTIVE-WORK-fourth.md, docs/2026-09-10-self-referential-guard-sweep.md, docs/SAIRN-OPEN-WORK-INDEX.md, docs/traceability-matrix.md, tests/run_all_tests_floor_probe.py, tests/run_report_only_checks_probe.py, tools/preauth_oracle_check.py, tools/report_only_checks.py, tools/run_all_tests.py, tools/write_without_readback_check.py
- **lines_added:** 602
- **lines_removed:** 15
- **detection_method:** code-review
- **injection_phase:** design
- **rules:** 1.1

---

## R06

- **commit:** 3ffb0603784b
- **date:** 2026-09-14
- **app:** PLATFORM
- **layer:** tooling
- **subject:** fix(tools): the sabotage detector counted replaces that touch no file -- 19 unguarded was really 8
- **summary:** the sabotage-control detector counted any file containing a write and a .replace, so datetime.replace(tzinfo=), output-string scrubs and path-separator normalisation were reported as unverified sabotage -- 19 unguarded was really 8
- **files:** tools/sabotage_control_check.py
- **lines_added:** 127
- **lines_removed:** 1
- **detection_method:** code-review
- **injection_phase:** design
- **rules:** 1.2

