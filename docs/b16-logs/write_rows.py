# -*- coding: utf-8 -*-
import io, json

p = 'docs/known-red-suites.json'
d = json.loads(io.open(p, encoding='utf-8').read())
SHA = '5039a033'
ENV = {
    "where": "live-clone", "pinned": False,
    "tool": "the suite itself, invoked alone, one process",
    "sha": SHA,
    "basis": "DRIVEN ALONE IN THE LIVE CLONE in cody b16, exit code read from "
             "`echo \"EXIT=$?\"` on its own line, never from a pipeline. Each "
             "repair had its SUBJECT read before the fix rather than only its "
             "last output lines, and the floor arms carry a committed ablation "
             "at docs/b16-logs/ablate_floor_layers.py.",
}


def put(section, row):
    f = row['file']
    for s in ('entries', 'recovered', 'not_red'):
        d[s] = [r for r in d[s] if r.get('file') != f]
    d[section].append(row)


put('recovered', {
    "file": "tests/claims/run_registry_claim_probe.py", "exit_code": 0,
    "recovered": "2026-10-15", "recovered_by": "cody", "owner": "cody",
    "environment": dict(ENV),
    "why": "FIXED AT CAUSE in cody b16 item 1: EXIT 0, 31 arms, 0 failures "
           "(8 were red). THE VERDICT WAS A WORD, NOT A LINE. Nine arms "
           "asserted 'BLOCKED' in / not in the tool's WHOLE output, and eight "
           "went red for a reason with nothing to do with registry claims: a "
           "LIVE claim from another session carried the word inside its own "
           "free-text task string -- fourth's read \"(2) BLOCKED AND NOT TAKEN "
           "-- ...\". Those arms were reading another agent's PROSE as this "
           "tool's verdict. tools/sairn_claim.py:660 records the SAME class one "
           "level down ('blocked' in clause matched inside UNBLOCKED, the "
           "opposite verdict), so repeating it over the tool's OUTPUT was that "
           "defect wearing a different hat. FIXED WITH A SHARED HELPER rather "
           "than nine more substring tests: blocked_lines(out) matches only a "
           "line STARTING 'BLOCKED -- ' (the real verdict, "
           "tools/sairn_claim.py:2219), and decided(out) is its PAIRED CONTROL "
           "because 'no line starts with BLOCKED' is also satisfied by an empty "
           "output or a tool that died before deciding. NO tools/ FILE EDITED.",
})

put('recovered', {
    "file": "tests/run_irreversible_class_probe.py", "exit_code": 0,
    "recovered": "2026-10-15", "recovered_by": "cody", "owner": "cody",
    "environment": dict(ENV),
    "why": "FIXED AT CAUSE in cody b16 item 1: EXIT 0, 15 arms. AND THE OLD "
           "ARM'S OWN DIAGNOSIS WOULD HAVE BEEN WRONG, which is the finding. "
           "Its failure text invited exactly one conclusion -- 'if the "
           "name-based half now catches shared libraries, re-read whether this "
           "class is still needed' -- and DRIVEN, that conclusion is FALSE. It "
           "leaked live state TWO ways at once: (1) G.check() reads the real "
           "docs/tier-a-reviews.json, whose open obligations change whenever "
           "any session opens or discharges one, and today it answered 'TIER A "
           "CODE CHANGED AND ONLY PART OF IT IS RECORDED ... already covered: "
           "invoices, leg_aftercare' -- today's backlog, not this gap; (2) "
           "range_diff(sha~1, sha) takes the WHOLE commit, and the most recent "
           "commit touching api/_lib/auth.js also touched api/_lib/leg-roles.js "
           "and others that DO name Tier A resources, so the arm asked about "
           "auth.js and measured a twenty-resource change. BOTH CLOSED: the "
           "obligation file is a FIXTURE with no records and the diff is "
           "RESTRICTED to the one path. With both controlled the gate answers "
           "exit 0 -- 'No file in this change names a Tier A resource on a "
           "changed line' -- SO THE GAP IS REAL and the class is still needed. "
           "A non-empty-diff PRECONDITION was added so the arm cannot pass over "
           "nothing. NO tools/ FILE EDITED; G.REVIEWS is monkey-patched and "
           "restored in a finally.",
})

put('recovered', {
    "file": "tests/sairnlegacy_fault_probe.py", "exit_code": 0,
    "recovered": "2026-10-15", "recovered_by": "cody", "owner": "cody",
    "environment": dict(ENV),
    "why": "FIXED AT CAUSE in cody b16 item 4, AND THE TENANCY CLAIM IS "
           "REFUTED. b15's triage flagged arm 8 -- 'app_id is taken from the "
           "client again' -- as a possible live tenancy defect, urgently, "
           "because that is what its last output line says. IT IS A MUTATION "
           "LABEL, NOT A FINDING: the arm PLANTS app_id: body.app_id || "
           "'sairnlegacy' and asserts the suite catches it. MEASURED AGAINST "
           "THE LIVE CODE: api/sd-data.js:16006 stamps the server's own literal "
           "app_id: 'sairnlegacy'; there is NO app_id taken from body.* or "
           "payload.* anywhere in the handler; 116 app_id writes are string "
           "literals. THE ARM FAILED ON ANCHOR ROT IN ITS TRAILING CONTEXT: the "
           "anchor carried two further lines ending in an INLINE "
           "res.status(503).json({ error: { code: 'NOT_PROVISIONED' ...}), and "
           "that branch has since been extracted into await notProvisioned(res, "
           "r, ...). Measured by binary search on the anchor: 205 of 295 "
           "characters matched, diverging exactly where notProvisioned() now "
           "begins. The anchor is cut back to the ONE LINE the mutation "
           "changes, verified unique in the file. ONE GENUINE CLIENT-SOURCED "
           "app_id DOES EXIST AND IS NOT THIS ONE: memApp at "
           "api/sd-data.js:1930, written at :2359 for the `memory` resource -- "
           "and it is GATED, not loose: MEMORY_APPS allowlists it with a 400 on "
           "an unknown app, and :2113 sets gateApp = memApp so the session must "
           "verify FOR THAT APP. Deliberate cross-app design, documented in the "
           "handler's own comment. ROUTED TO HANK AS A READ, NOT A DEFECT.",
})

put('recovered', {
    "file": "tests/run_tier_a_review_gate_sabotage_probe.py", "exit_code": 0,
    "recovered": "2026-10-15", "recovered_by": "cody", "owner": "cody",
    "environment": dict(ENV),
    "why": "RE-AIMED IN cody b16 item 1, AND THE 'FAIL-OPEN GAP' IT REPORTED "
           "DOES NOT EXIST. Arm 8 reported 'not caught' in b15, which reads as "
           "a fail-open in tools/tier_a_review_gate.py. DRIVEN ON A SABOTAGED "
           "COPY, the planted harm never reaches anything: the old mutation "
           "changed reviewer_roster_detail()'s OSError limb from 'return None, "
           "[], []' to 'return [], [], []', and measured -- "
           "reviewer_roster_detail() -> ([], [], []) DEGRADED, "
           "eligible_reviewers() -> None STILL CLOSED, assign_owner() -> (None, "
           "'the eligible-reviewer roster could not be read ... first-come. Fix "
           "the roster') -- because eligible_reviewers() normalises a roster of "
           "fewer than two names to None on its own "
           "(tools/tier_a_review_gate.py:1430): one name cannot review "
           "anything, so an empty one cannot either. THE DEFECT CLASS IS "
           "DEFENDED IN TWO PLACES and the old mutation removed only the first. "
           "A mutation whose harm is absorbed downstream is not an undetected "
           "defect; it is an arm asserting that an unreachable defence is "
           "missing, and reporting it in the voice of a real gap. RE-AIMED at "
           "the second defence -- 'return names if len(names) >= 2 else None' "
           "-> 'return names' -- which IS the 'roster with nobody on it' the "
           "label names, and which tests/run_tier_a_review_gate_probe.py's own "
           "arm catches. Anchor verified unique. NOTE: the b15 run of this probe "
           "also reported a dirty-tree failure naming 2 files already modified "
           "before it started; re-driven on a clean tree that failure is GONE, "
           "so it was this session's own in-flight edits, not a probe defect. "
           "THE RE-AIMED ARM ITSELF IS NOT YET DRIVEN END-TO-END -- see "
           "UNPROVEN in SAIRN-report-cody-b16.txt.",
})

put('recovered', {
    "file": "tests/run_floor_layers_probe.py", "exit_code": 0,
    "recovered": "2026-10-15", "recovered_by": "cody", "owner": "cody",
    "environment": dict(ENV),
    "why": "NEW FILE in cody b16 item 2, closing docs/ABLATION-RECORDS.md "
           "FINDING 2: EXIT 0, 9 arms. cc measured all THREE of b12's "
           "test-file-floor layers as UNPROVEN by removing each from "
           "tools/run_all_tests.py and running cody's OLD "
           "tests/run_all_tests_floor_probe.py against each mutant -- all three "
           "stayed green, because that probe predates b12 and was never asked "
           "about the ratchet. tests/ is cody's, so cc routed them. NOW ARMED, "
           "AND THE ABLATION PROVES IT: docs/b16-logs/ablate_floor_layers.py "
           "drives each layer's removal against a COPIED tool tree and reports "
           "3 of 3 CAUGHT, with the unmutated copy green first. "
           "tracked-intersection was taken FIRST because it is the urgent one "
           "-- FINDING 2b: unarmed IN-RUN and DESTRUCTIVE ACROSS RUNS, since "
           "cc's harness wrote a floor of 812 then 813 against a real 808 while "
           "cody's probe still exited 0, and the harm lands on the NEXT run. "
           "Arm T2 is that across-runs half specifically; T3 is the paired "
           "positive that a rise WITHIN the tracked count still lands; T4 is "
           "fail-closed when the tracked count is unmeasurable. TWO DEFECTS IN "
           "MY OWN ABLATION HARNESS WERE FOUND BY DRIVING IT, both recorded in "
           "the files: (1) it shadowed tools/ with PYTHONPATH and the probe's "
           "own sys.path.insert won, so every 'mutant' run imported the REAL "
           "tool and all three layers reported NOT CAUGHT against arms that "
           "were fine -- an ablation that cannot remove the fix reports the arms "
           "broken and the fix unnecessary in one stroke; fixed with a single "
           "declared injection point, SAIRN_B16_RUN_ALL_TESTS. (2) R1 does NOT "
           "catch the ratchet layer: removing 'MIN_TEST_FILES = "
           "_read_floor()[0]' leaves _read_floor() intact, so an arm calling it "
           "directly stays green. THE LAYER IS THE WIRING, so arm R4 was added "
           "on the module CONSTANT, and the harness now lays out tools/ + docs/ "
           "in the copy so the copy's own _FLOOR_PATH resolves. R3 is reported "
           "NOT APPLICABLE under an injected copy rather than failing. Arm S is "
           "STRUCTURAL (AST, not a text anchor) and says so: its enclosing "
           "function runs the whole suite, so a behavioural drive per arm is "
           "not practical. NO tools/ FILE AND NO REAL FLOOR FILE WRITTEN -- "
           "cc's harness poisoned docs/test-file-floor.json and changed a later "
           "layer's verdict between runs, which is why every fixture here is "
           "per-arm and restored in a finally.",
})

d['_b16_2026_10_15_cody'] = (
    "FIVE ROWS: FOUR SUITES FIXED AT CAUSE AND ONE NEW -- AND THREE OF THE FOUR "
    "'DEFECTS' TURNED OUT TO BE PROBES READING THEIR OWN SUBJECT WRONG, WHICH IS "
    "THE RESULT OF THIS BATCH. b15 triaged 39 real failures and routed 34; b16 "
    "took the first cluster by READING EACH SUBJECT rather than its last output "
    "line, and that is what separated these. (1) run_registry_claim_probe: nine "
    "arms matched the WORD 'BLOCKED' in the tool's whole output and another "
    "session's claim prose contained it -- fixed with a line-anchored helper and "
    "a paired control. (2) run_irreversible_class_probe: the arm leaked the live "
    "obligation file AND the whole commit's scope, and its own failure text "
    "invited the WRONG conclusion that the gap it pins had closed; driven "
    "hermetically the gap is REAL. (3) sairnlegacy_fault_probe arm 8: flagged in "
    "b15 as a possible live tenancy defect because its label says 'app_id is "
    "taken from the client again' -- that is a MUTATION LABEL, the live handler "
    "stamps a literal at api/sd-data.js:16006, and the arm failed on anchor rot "
    "in its TRAILING context where notProvisioned() was extracted. REFUTED. (4) "
    "run_tier_a_review_gate_sabotage_probe arm 8: reported a fail-open that does "
    "not exist, because eligible_reviewers() normalises a short roster to None "
    "on its own; re-aimed at the defence that would really bite. AND ONE NEW "
    "FILE: run_floor_layers_probe closes cc's FINDING 2 with 9 arms and a 3-of-3 "
    "ablation, tracked-intersection first. BATCH STOPPED AT 70 PERCENT CONTEXT "
    "ON INSTRUCTION: 30 of the 34 triaged failures, the 16 CHANGED rows, the 9 "
    "RECOVERED rows, the run_capa_fields cleanup, the _rm_ro de-dup and the "
    "b14-b15 ablation backfill are NOT STARTED and are routed with an exact next "
    "step each in SAIRN-handoff-cody-b16.md. entries %d, recovered %d, not_red "
    "%d." % (len(d['entries']), len(d['recovered']), len(d['not_red'])))

io.open(p, 'w', encoding='utf-8', newline='\n').write(
    json.dumps(d, indent=1, ensure_ascii=False) + '\n')
print('entries %d, recovered %d, not_red %d'
      % (len(d['entries']), len(d['recovered']), len(d['not_red'])))
