# -*- coding: utf-8 -*-
"""ITEM 6, PASS 2 -- show the command line complete, then read the exit code.

"A refusal is a claim about the command line until the command line is shown
complete." So each tool below gets a REAL, COMPLETE invocation, hand-written
from its OWN refusal text and pointed at REAL artefacts in this repo -- not a
guess and not a placeholder.

THREE BUCKETS, and the split is the answer rather than an excuse:

  ARG      the refusal names a missing ARGUMENT or FLAG. Completable from the
           repo. Driven here.
  CRED     the refusal names a missing CREDENTIAL or SECRET (a licence key, a
           PIN, CRON_SECRET). NOT completable: I will not manufacture a
           credential, and a fabricated one would prove nothing about the gate
           it is meant to reach. STILL-UNRUNNABLE BY DESIGN, and the tool is
           RIGHT to refuse -- this is the documented third state.
  FINDING  exit 2 is not about the command line at all. The tool ran, read the
           repo, and fails CLOSED because its own hand-written half does not
           cover what it found, or because a sub-measurement could not be made.
           Re-running with more arguments cannot change it; the repo has to.

EVERYTHING RUNS IN A THROWAWAY WORKTREE, because several of these WRITE.
"""
import io
import json
import os
import subprocess
import sys
import time

WT = sys.argv[1]
OUT = sys.argv[2]
BOUND = 240

# -- ARG: a complete command line, each argument a real thing in this repo.
ARG = [
    ('capture_exit.py', ['--', sys.executable, '-c', 'print(1)']),
    ('citation_drift_hook.py', ['docs/SAIRN-PROCESS-RULES.md']),
    ('citation_line_drift_check.py', ['--app', 'stonedesk.html', '--prefix', 'sd_']),
    ('claim_provenance.py', ['list']),
    ('dep_surface_check.py', ['--package', 'busboy', '--enumerate-only']),
    ('doc_sha_reseat.py', ['--check']),
    ('exit_status_attributable.py', ['--selftest']),
    ('extract_panels.py', ['stonedesk.html']),
    ('fmea_draft.py', ['tools/audit_event_type_check.py']),
    ('gate_caller_impact.py', ['--survey']),
    ('hedge_carry_check.py', ['--item', 'Close the seven open attribution gaps that do not depend on the migration, if they are genuinely independent.']),
    ('html_script_check.py', ['stonedesk.html']),
    ('index_duplicate_hook.py', ['docs/SAIRN-OPEN-WORK-INDEX.md']),
    ('known_red_check.py', ['--run']),
    ('ledger_append.py', ['--ledger', 'docs/BYPASS-LOG.jsonl']),
    ('line_endings.py', ['CLAUDE.md']),
    ('load_deadline_seed.py', ['--dry-run', 'maine']),
    ('load_schema_snapshot.py', ['db/schema_snapshot.json']),
    ('new_checker.py', ['b2_scratch_probe', 'a throwaway scaffold, dry run only', '--dry-run']),
    ('panel_depth.py', ['stonedesk.html', 'dashboard']),
    ('purge_evidence_gate.py', ['--audit']),
    ('register_feed_gate.py', ['--self-check']),
    ('rewrite_convergence_map.py', ['--verify']),
    ('sabotage.py', ['--list']),
    ('sairn_claim.py', ['list']),
    ('sairn_source_fetch.py', ['--list']),
    ('staged_parse_check.py', ['api/sd-data.js']),
    ('three_way_match_check.py', ['--structure-only']),
    ('tool_owner_header_check.py', ['tools/audit_event_type_check.py']),
    ('verify_review_gates.py', ['docs/MASTER-PLAN.md']),
    ('wait_for.py', ['--pid', str(os.getpid())]),
    ('bare_run_write_check.py', ['--repo', 'BARE_RUN_SCRATCH']),
]

CRED = [
    ('alf_facility_role_gate_live_probe.py', 'ALF_LICENSE'),
    ('audit_checkpoint_status.py', 'CRON_SECRET'),
    ('cron_liveness_check.py', 'CRON_SECRET'),
    ('credential_purge_check.py', 'a local credential file'),
    ('demo_credentials_check.py', '.demo-credentials.local.json'),
    ('law_billing_code_trim_live_probe.py', 'LAW_LICENSE + LAW_EMP + LAW_PIN'),
    ('leg_session_gate_live_probe.py', 'LEG_LICENSE'),
    ('load_compliance_seed.py', 'SAIRNCARE_LICENSE + a management session'),
    ('rf_claim_gate_live_probe.py', 'RF_EMP + RF_PIN + RF_NARROW_PIN'),
    ('rf_roundtrip_probe.py', 'RF_EMP + RF_PIN'),
    ('sc_tier_a_write_gate_live_probe.py', 'SC_LICENSE + SC_EMP + SC_PIN'),
    ('scp_session_gate_live_probe.py', 'SCP_LICENSE'),
    ('run_tlc.py', 'a JRE and tools/vendor/tla2tools.jar, both one-time per clone'),
]

FINDING = [
    ('allan_deviation_check.py', 'a sub-measurement was underpowered'),
    ('benford_check.py', 'every seed had too few values for its own bar'),
    ('checker_confidence.py', 'STABLE is UNKNOWN for every checker scored'),
    ('checker_estimate_fusion.py', 'the fusion inputs are not all available'),
    ('cleanup_residue_check.py', 'COULD NOT READ 27 of 27 -- not a pass'),
    ('defect_dispersion.py', 'report-only; a dimension could not be computed'),
    ('hover_eqa_escalation.py', 'hover2 carries no eqa_checkpoint field at all'),
    ('hover_separation_audit.py', '64.5% of commits are UNATTRIBUTED'),
    ('sairn_seam_check.py', 'a seam could not be resolved'),
    ('secrets_inventory.py', 'two secrets have no SECRETS entry -- fails closed on purpose'),
    ('service_role_tier_a_gate_check.py', 'UNGATED Tier A writers found'),
]

MISRUN = [
    ('restore_coherence_check.js', 'node'),
    ('row_count_baseline.js', 'node'),
]

rows = []


def drive(label, cmd, cwd, bucket, note=''):
    t0 = time.time()
    try:
        r = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=BOUND)
        code, out = r.returncode, r.stdout.decode('utf-8', 'replace')
    except subprocess.TimeoutExpired as e:
        code, out = 'TIMEOUT', (e.output or b'').decode('utf-8', 'replace')
    except Exception as e:                                      # noqa: BLE001
        code, out = 'ERROR', '%s: %s' % (type(e).__name__, e)
    el = round(time.time() - t0, 1)
    first = next((l.strip() for l in out.split('\n') if l.strip()), '(no output)')
    rows.append({'tool': label, 'bucket': bucket, 'code': code, 'secs': el,
                 'cmd': ' '.join(cmd[1:]), 'first': first[:200], 'note': note})
    print('%-42s %-8s %-9s %6.1fs  %s' % (label, bucket, code, el, first[:90]),
          flush=True)


print('== ARG -- the command line shown COMPLETE ==', flush=True)
scratch = os.path.join(os.path.dirname(OUT), 'bare_run_scratch')
for name, args in ARG:
    p = os.path.join(WT, 'tools', name)
    if not os.path.isfile(p):
        rows.append({'tool': name, 'bucket': 'ARG', 'code': 'ABSENT',
                     'secs': 0.0, 'cmd': '', 'first': 'not on disk', 'note': ''})
        print('%-42s ABSENT' % name, flush=True)
        continue
    a = list(args)
    if 'BARE_RUN_SCRATCH' in a:
        if not os.path.isdir(scratch):
            subprocess.run(['git', 'clone', '--local', '--no-hardlinks', '-q',
                            WT, scratch], capture_output=True)
        a = [scratch if x == 'BARE_RUN_SCRATCH' else x for x in a]
    drive(name, [sys.executable, '-u', os.path.join('tools', name)] + a, WT, 'ARG')

print('\n== MISRUN -- .js driven with node, which the sweep never did ==',
      flush=True)
for name, runner in MISRUN:
    drive(name, [runner, os.path.join('tools', name)], WT, 'MISRUN',
          'the 315-script sweep ran every file with PYTHON, so these two '
          'reported a Python SyntaxError on JavaScript')

print('\n== CRED -- NOT completable, and the tool is right to refuse ==',
      flush=True)
for name, what in CRED:
    rows.append({'tool': name, 'bucket': 'CRED', 'code': 2, 'secs': 0.0,
                 'cmd': '(not driven)', 'first': 'needs %s' % what,
                 'note': what})
    print('%-42s CRED     needs %s' % (name, what), flush=True)

print('\n== FINDING -- exit 2 is about the REPO, not the command line ==',
      flush=True)
for name, what in FINDING:
    rows.append({'tool': name, 'bucket': 'FINDING', 'code': 2, 'secs': 0.0,
                 'cmd': '(bare run is the correct invocation)',
                 'first': what, 'note': what})
    print('%-42s FINDING  %s' % (name, what), flush=True)

io.open(OUT, 'w', encoding='utf-8').write(json.dumps(rows, indent=1))

import collections
arg = [r for r in rows if r['bucket'] in ('ARG', 'MISRUN')]
c = collections.Counter(str(r['code']) for r in arg)
print('\n== COUNTS, over the %d DRIVEN with a complete command line ==' % len(arg))
print('  green        (exit 0) : %d' % c['0'])
print('  findings     (exit 1) : %d' % c['1'])
print('  still exit 2          : %d' % c['2'])
print('  other / timeout       : %s'
      % {k: v for k, v in c.items() if k not in ('0', '1', '2')})
print('  NOT DRIVEN -- credential or secret absent : %d'
      % len([r for r in rows if r['bucket'] == 'CRED']))
print('  NOT ABOUT THE COMMAND LINE -- a repo finding : %d'
      % len([r for r in rows if r['bucket'] == 'FINDING']))
print('  TOTAL accounted for : %d' % len(rows))
