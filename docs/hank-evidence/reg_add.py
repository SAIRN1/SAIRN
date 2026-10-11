# -*- coding: utf-8 -*-
"""APPEND THREE RECORDS THROUGH THE TOOL.

docs/defect-density-register.json is declared in cody's batch24 FILES. Cody's
own stated discipline for it is "I only APPEND through the tool and I do not
edit it" -- which is exactly this, and is the file's designed use. No edit is
made to the register and none to tools/defect_register.py (cc's).
"""
import json
import subprocess
import sys

REPO = r'C:\Users\marsh\Documents\SAIRN-hank'

RECS = [
    # -- aba0e0a9 : the six argv tools -------------------------------------
    dict(
        commit='320ddabe', app='tooling', layer='tooling', severity='moderate',
        method='code-review', phase='coding', phase_confidence='stated',
        summary=(
            'Eight of 315 scripts under tools/ read sys.argv[1] with no length '
            'check, so a bare run raised IndexError and exited 1. On this '
            'platform EXIT 1 MEANS FINDINGS and exit 2 means COULD NOT RUN, so '
            'to anything reading an exit code a tool that needed an argument was '
            'indistinguishable from a tool that ran and found something. 67 other '
            'tools in the same directory already refuse in words, so the '
            'convention was established and these were the exceptions. Six are '
            'fixed here: checkblocks.py, div_balance_check.py, '
            'extract_scripts.py, js_code_only_diff.py, literal_drift_check.py, '
            'nav_panel_check.py. Measured by running all 315 scripts once each in '
            'a throwaway worktree and reading the captured exit codes -- the 8 and '
            'the 67 are counts from that sweep, not estimates.'),
        rule='1.11',
        rule_note=(
            'ARGUABLE. 1.11 is about a check that could not run reporting a PASS. '
            'This is the adjacent shape: a tool that could not run reporting the '
            'code that means FINDINGS. The third state exists and is reachable -- '
            '67 tools use it -- it was simply not used here, so the collapse is '
            'into the wrong occupied state rather than into a pass.'),
        injection_unknown=(
            'Each of the six was written as a one-shot helper invoked by hand, '
            'where a traceback IS adequate feedback to the person who just typed '
            'the command. There is no commit that removed a guard -- the guard was '
            'never written, and the audience changed from a person to a sweep with '
            'nothing revisiting the assumption.'),
        factors=[
            dict(kind='technical',
                 factor='sys.argv[1] read with no len(sys.argv) guard in six tools.',
                 action_status='done',
                 action=('A len(sys.argv) guard in each that writes COULD NOT RUN '
                         'plus a usage line to stderr and exits 2.')),
            dict(kind='detection',
                 factor=('Nothing compared a tool bare-run exit code against the '
                         'platform exit-code convention, so the defect was '
                         'invisible to every sweep that reads exit codes -- which '
                         'is every sweep.'),
                 action_status='done',
                 action=('tests/run_tool_usage_refusal_probe.py drives each subject '
                         'bare and asserts exit 2, a COULD NOT RUN string and no '
                         'traceback. Its population is LISTED, not scanned, so a '
                         'newly-added tool with the same defect is a new finding '
                         'rather than silently absorbed.')),
            dict(kind='process',
                 factor=('Two of the eight were not fixed and were put on ONE '
                         'routing list together, which read as deferral for both.'),
                 action_status='planned',
                 action=('va_rule_currency.py is taken at 1ae447cf; gh_push.py:182 '
                         'is routed to its real owner in '
                         'docs/2026-10-07-hank-routed.md section 1.')),
        ],
        recurrence_open=(
            'The probe pins SEVEN named tools. It does not and cannot tell whether '
            'a NINTH tool with the same defect is added tomorrow -- the population '
            'is deliberately listed rather than derived, so coverage of the class '
            'depends on somebody re-running the 315-script sweep. No gate does that '
            'on a cadence.')),

    # -- 469eec19 : the last seven attribution paths -----------------------
    dict(
        commit='4ec0d5d5', app='PLATFORM', layer='product', severity='moderate',
        method='code-review', phase='design', phase_confidence='stated',
        summary=(
            'The last 7 of 15 write branches in SAIRNcare, SAIRNsenior and '
            'SAIRNroofing that persisted a row recording no acting employee: five '
            'SAIRNsenior (sen_branches, sen_payer_contracts, sen_authorizations, '
            'sen_pay_rates, sen_franchise_agreements) and two SAIRNroofing '
            '(rf_claims/write, rf_schedule/set_status). AND THE SECOND DEFECT IS IN '
            'MY OWN EARLIER REFUSAL: the two roofing paths were left unattributed '
            'under ONE shared reason -- neither sends data, so stamping would '
            'REPLACE the stored blob and destroy carrier, claim_number and '
            'adjuster. That is true of ONE of them. rf_claims/write DOES send '
            'data: dataBlob at api/sd-data.js:7772, built from the whole payload '
            'through storedBlob, and took the same one-line stamp as the five. Only '
            'rf_schedule/set_status matched the stated reason and took a '
            'read-then-merge onto the row its own gate already reads. attr_scan.py '
            're-run at this state: UNATTRIBUTED 0 of 49. None of the fifteen '
            'depended on the audit-table migration -- that migration is about AUDIT '
            'tables and all fifteen of these are DATA tables.'),
        rule='not-citable',
        rule_note=(
            'NO STANDING SECTION NAMES EITHER HALF. The attribution half is the '
            'same shape as record 56bbce5e83d5, filed not-citable for the same '
            'reason: a row that works correctly and cannot answer who wrote it. '
            'The reused-refusal half is genuinely new -- cross-domain discipline 7 '
            'is its MIRROR (propagating a proven FIX without re-qualifying the '
            'target) and nothing covers propagating a proven REFUSAL. Written up as '
            'RULE E in docs/2026-10-07-hank-routed.md section 3 and ROUTED, because '
            'docs/METHODOLOGY.md is claimed by two other sessions.'),
        injection_unknown=(
            'These branches have never recorded an actor. There is no commit that '
            'removed one, and citing the commit that created each resource would '
            'name a feature as the injection of its own absent field. The '
            'reused-refusal half originates at 56bbce5e83d5, which is already in '
            'this register -- but that commit FIXED eight paths, and naming it as '
            'an injection would make a fix read as a regression.'),
        factors=[
            dict(kind='technical',
                 factor=('Seven write branches persisted a row with no acting '
                         'employee -- not a column, not a blob key, not an audit '
                         'row.'),
                 action_status='done',
                 action=('Six take { updatedBy: session.employee_id, '
                         'updatedByRole: session.role } as the LAST source of their '
                         'Object.assign, after storedBlob, so a caller-supplied '
                         'updatedBy that survives storedBlob is overwritten. '
                         'rf_schedule/set_status takes a read-then-merge onto '
                         'entry.data because a bare data: { updatedBy } would have '
                         'REPLACED the window and notes blob.')),
            dict(kind='process',
                 factor=('One data-loss refusal was written over TWO paths when it '
                         'was true of one, so a correct reason protected a case it '
                         'never covered.'),
                 action_status='done',
                 action=('Both re-read at HEAD against the actual row construction '
                         'and the actual DDL. RULE E records the general shape and '
                         'its mechanical form: a refusal covering more than one '
                         'item must cite, per item, the fact that makes the reason '
                         'true of THAT item.')),
            dict(kind='detection',
                 factor=('The existing source arm D1 matched only the '
                         'x.updatedBy = session.employee_id spelling, so seven of '
                         'fifteen stamps were behaviour-tested and NOT '
                         'source-pinned. Moving one to the FIRST Object.assign '
                         'source would have kept every behaviour arm green while '
                         'the payload silently won again.'),
                 action_status='done',
                 action=('Arms D2 (the six Object.assign stamps are the last '
                         'source, statement-bounded) and D3 (set_status spreads the '
                         'stored blob first and PATCHes the merged value). Mutation '
                         'proof: 16 passed / 4 failed, exit 1.')),
        ],
        recurrence_open=(
            'attr_scan.py is LEXICAL and covers only SAIRNcare, SAIRNsenior and '
            'SAIRNroofing. 0 of 49 is 0 of those three apps by that criterion -- '
            'the other apps have never been scanned this way, and an actor recorded '
            'through a helper or a shared prelude is invisible to it. Nothing '
            're-runs it on a cadence and no gate refuses a NEW write branch that '
            'records no actor. rf_schedule/set_status also accepts a narrow '
            'lost-update window that a status_changed_by column would remove -- '
            'that is a migration and is named, not done.')),

    # -- 1c8a395c : the seventh argv tool ----------------------------------
    dict(
        commit='1ae447cf', app='tooling', layer='tooling', severity='moderate',
        method='code-review', phase='coding', phase_confidence='stated',
        summary=(
            'tools/va_rule_currency.py, the seventh of the eight argv tools, and '
            'its refusal is not the one the other six needed. It reads '
            'path, wanted = sys.argv[1], sys.argv[2:]. A bare run raised '
            'IndexError and exited 1 -- the same third-state collapse. But given '
            'ONE argument it did NOT raise: wanted came back empty, the loop test '
            'name not in wanted matched nothing, and the tool printed NOTHING and '
            'exited 0. SILENT SUCCESS ON A RUN THAT EXAMINED NO RULE, '
            'indistinguishable from every rule is clean -- worse than the '
            'traceback, because a traceback at least stops somebody. A guard '
            'written for the bare case alone would have closed the louder half and '
            'left the quieter half exactly as it was. It is also the file with NO '
            'OWNER AT ALL in docs/tool-owner-map.json (basis NONE, owner null), '
            'which is why it sat on a routing list that could never route it.'),
        rule='1.11',
        rule_note=(
            'ARGUABLE, and more squarely than the sibling record for the other six. '
            'The one-argument path is a run that examined nothing and reported '
            'EXIT 0 -- a could-not-run folded into a PASS, which is 1.11 in its '
            'exact words. The bare path is the adjacent shape, folded into FINDINGS '
            'instead.'),
        injection_unknown=(
            'Written as a hand-invoked one-shot helper, like the other six. No '
            'commit removed a guard. The two-argument silent-success path has been '
            'reachable since the file was written and no run is recorded that hit '
            'it.'),
        factors=[
            dict(kind='technical',
                 factor=('Two required arguments, no guard on either, and the '
                         'second one failed SILENTLY with exit 0 rather than '
                         'raising.'),
                 action_status='done',
                 action=('A len(sys.argv) <= 2 guard that NAMES which argument is '
                         'missing and exits 2.')),
            dict(kind='process',
                 factor=('It was left unfixed on a routing list although the owner '
                         'map says it has NO OWNER -- so the listing was not '
                         'deferring the decision to chat, it was declining to make '
                         'one while looking like deferral, and it would have '
                         'recurred every batch for the same reason.'),
                 action_status='done',
                 action=('Claims-checked CLEAR and taken under this batch claim; '
                         'the move from NOT_MINE to SUBJECTS is stated in the '
                         'probe own header with the owner-map entry quoted.')),
            dict(kind='detection',
                 factor=('Arm B drives a BARE run, which the IndexError already '
                         'covered, so arm B alone would have gone green over the '
                         'silent-success path.'),
                 action_status='done',
                 action=('Arm C drives the tool with a real file and NO rule and '
                         'asserts exit 2 plus the named missing argument. Mutation '
                         'against the pre-fix file: 18 passed / 5 failed, exit 1, '
                         'and both C arms are among the five.')),
        ],
        recurrence_open=(
            'The silent-success shape -- a partially-supplied argument list that '
            'examines nothing and exits 0 -- was found by reading THIS file. No '
            'sweep looks for it anywhere else, and the 315-script sweep that found '
            'the eight tracebacks cannot see it at all, because it exits 0 and '
            'reads as green.')),
]


def main():
    worst = 0
    for r in RECS:
        argv = [sys.executable, 'tools/defect_register.py', '--add',
                '--commit', r['commit'],
                '--app', r['app'],
                '--layer', r['layer'],
                '--severity', r['severity'],
                '--method', r['method'],
                '--summary', r['summary'],
                '--rule', r['rule'],
                '--rule-note', r['rule_note'],
                '--phase', r['phase'],
                '--phase-confidence', r['phase_confidence'],
                '--injection-unknown', r['injection_unknown'],
                '--factors', json.dumps(r['factors']),
                '--recurrence-open', r['recurrence_open']]
        p = subprocess.run(argv, cwd=REPO, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT)
        out = p.stdout.decode('utf-8', 'replace')
        print('=== %s  exit=%d' % (r['commit'], p.returncode))
        print(out.strip()[:1500])
        print('')
        if p.returncode:
            worst = p.returncode
    return worst


if __name__ == '__main__':
    sys.exit(main())
