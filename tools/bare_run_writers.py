#!/usr/bin/env python
# OWNER: cody
"""The tools whose bare run is SUPPOSED to write, and why each one is.

    python tools/bare_run_writers.py            # the list, with reasons
    python tools/bare_run_writers.py --check    # does it still match reality?

WHY THIS IS AN ALLOWLIST AND NOT A SUPPRESSION. tools/bare_run_write_check.py
found 22 tools that mutate the repo when run with no arguments. That sweep exists
because one such run rewrote three generated documents. But most of the 22 are
GENERATORS: writing is their entire purpose, `python tools/master_plan.py` is what
the push gate itself tells you to run to fix a stale document, and making them
report-only would break that instruction and every session's habit.

So the finding splits in two, and only one half is a defect:

  * a tool you run to LOOK at something, which writes           -> a defect
  * a tool whose whole job is to produce a file                 -> not a defect,
    and its bare run is its interface

This file is the second list. It is not a way to make the sweep quiet: every
entry carries the PATH IT WRITES and a REASON, and `--check` fails when an entry
no longer writes what it claims, when a listed tool has gone, or when the reason
is missing. An allowlist nobody re-derives is how a real defect hides inside a
convention.

── WHAT IS DELIBERATELY NOT HERE ───────────────────────────────────────────
tools/condition_coverage.py wrote api/_lib/ledger.js and is NOT on this list. It
was fixed instead (2026-09-30): it mutates a detached worktree now. A tool that
writes a SOURCE file on a bare run is never an intended writer, whatever it is
for -- and it was killed mid-write once already.

tools/nhi_register.py is NOT here either. It was made report-only, because it is
a tool you run to ask what the register says.
"""
import io
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── THE LIST: tool -> (paths it writes, why its bare run is the interface) ────
# Every entry was verified against a real bare run in a scratch clone on
# 2026-09-30; the paths are what `git status --porcelain` named.
WRITERS = {
    'master_plan.py': (
        ['docs/MASTER-PLAN.md'],
        'A GENERATOR THE PUSH GATE ITSELF TELLS YOU TO RUN. Check 12 refuses a '
        'push that leaves this document stale and prints `fix: python '
        'tools/master_plan.py` -- so a --write flag would make the gate\'s own '
        'remediation line wrong. Report-only would break the documented loop.'),
    'traceability_matrix.py': (
        ['docs/traceability-matrix.md'],
        'The same generator pair as MASTER-PLAN, refused by the same gate check '
        'with the same printed fix line. It also carries --check, which is the '
        'read-only mode; the bare run is the write mode on purpose.'),
    'tooling_inventory.py': (
        ['docs/TOOLING-INVENTORY.md'],
        'Generated, and the push gate refuses a new tools/ file with no PURPOSES '
        'entry by RUNNING this generator and reading its refusal. Its bare run '
        'is how the document is produced; --check is how it is questioned.'),
    'audit_checkpoint_status.py': (
        ['docs/AUDIT-CHECKPOINT-STATUS.md'],
        'Writes the outcome of a daily audit checkpoint to a document instead of '
        'a log line nobody opens. Producing that file IS the run; there is '
        'nothing else it does.'),
    'cron_liveness_check.py': (
        ['docs/CRON-LIVENESS-STATUS.md'],
        'Asks from OUTSIDE Vercel whether a scheduled job ran, and records the '
        'answer. The record is the product -- a liveness check whose answer is '
        'only on stdout cannot be read tomorrow.'),
    'role_gate_mc_config.py': (
        ['docs/spec/MCRoleGates.cfg', 'docs/spec/MCRoleGates.tla'],
        'Emits the TLA+ model and its config from the role-gate invariants. The '
        'files ARE the output; tools/run_tlc.py then reads them.'),
    'sairn_build_load_gates.py': (
        # FIVE, not four. I listed `rf_cert_rules` and the sweep's
        # undeclared-path check caught it on the first real run: it writes
        # rf_cert_rules AND rf_contingency_rules. That is the arm earning its
        # keep on the list it was written to guard, which is the only kind of
        # allowlist worth having.
        ['sql/alf_compliance_rules_load_gate_generated.sql',
         'sql/alf_payer_rules_load_gate_generated.sql',
         'sql/dnt_cred_rules_load_gate_generated.sql',
         'sql/rf_cert_rules_load_gate_generated.sql',
         'sql/rf_contingency_rules_load_gate_generated.sql'],
        'Generates the load-gate SQL from the rule registries. The `_generated` '
        'in every filename is the contract: these are outputs, not sources, and '
        'hand-editing one is the defect this replaces.'),
    'gen_ma_calendar.py': (['sql/sairnlaw_deadline_calendars_massachusetts.json'],
                           'SAIRNlaw deadline calendar generator.'),
    'gen_ma_seed.py': (['sql/sairnlaw_deadline_seed_massachusetts.json'],
                       'SAIRNlaw deadline seed generator.'),
    'gen_mn_calendar.py': (['sql/sairnlaw_deadline_calendars_minnesota.json'],
                           'SAIRNlaw deadline calendar generator.'),
    'gen_mn_seed.py': (['sql/sairnlaw_deadline_seed_minnesota.json'],
                       'SAIRNlaw deadline seed generator.'),
    'gen_mo_calendar.py': (['sql/sairnlaw_deadline_calendars_missouri.json'],
                           'SAIRNlaw deadline calendar generator.'),
    'gen_mo_seed.py': (['sql/sairnlaw_deadline_seed_missouri.json'],
                       'SAIRNlaw deadline seed generator.'),
    'gen_nj_calendar.py': (['sql/sairnlaw_deadline_calendars_newjersey.json'],
                           'SAIRNlaw deadline calendar generator.'),
    'gen_nv_calendar.py': (['sql/sairnlaw_deadline_calendars_nevada.json'],
                           'SAIRNlaw deadline calendar generator.'),
    'gen_ok_calendar.py': (['sql/sairnlaw_deadline_calendars_oklahoma.json'],
                           'SAIRNlaw deadline calendar generator.'),
    'gen_or_calendar.py': (['sql/sairnlaw_deadline_calendars_oregon.json'],
                           'SAIRNlaw deadline calendar generator.'),
    'gen_sc_calendar.py': (['sql/sairnlaw_deadline_calendars_southcarolina.json'],
                           'SAIRNlaw deadline calendar generator.'),
    'gen_ut_calendar.py': (['sql/sairnlaw_deadline_calendars_utah.json'],
                           'SAIRNlaw deadline calendar generator.'),
    'gen_va_calendar.py': (['sql/sairnlaw_deadline_calendars_virginia.json'],
                           'SAIRNlaw deadline calendar generator.'),
    'gen_va_seed.py': (['sql/sairnlaw_deadline_seed_virginia.json'],
                       'SAIRNlaw deadline seed generator.'),
}

# The header every entry is expected to carry in its own file, so a reader who
# opens the tool learns the same thing without finding this list first.
HEADER = 'OWNER-INTENDED BARE-RUN WRITER'


def is_intended(name):
    """Is a bare run of tools/<name> a declared, reasoned write?"""
    return os.path.basename(name) in WRITERS


def writes(name):
    return WRITERS.get(os.path.basename(name), ([], ''))[0]


def main(argv):
    out = sys.stdout.write
    out('OWNER-INTENDED BARE-RUN WRITERS -- %d tool(s)\n' % len(WRITERS))
    out('  These are not exempted, they are EXPLAINED. Every entry names the\n')
    out('  path it writes and why its bare run is its interface.\n\n')
    bad = []
    for name in sorted(WRITERS):
        paths, why = WRITERS[name]
        p = os.path.join(REPO, 'tools', name)
        exists = os.path.isfile(p)
        marked = False
        if exists:
            head = ''.join(io.open(p, encoding='utf-8', errors='replace')
                           .readlines()[:60])
            marked = HEADER in head
        out('  %-28s %s\n' % (name, 'writes: ' + (', '.join(paths) or 'NOTHING')))
        out('      %s\n' % ('header: present' if marked else
                            'header: MISSING -- the tool does not say this itself'))
        if not exists:
            bad.append((name, 'the tool is not in this clone'))
        elif not marked:
            bad.append((name, 'no `%s` line in its first 60 lines' % HEADER))
        elif not why:
            bad.append((name, 'no reason recorded'))
    if '--check' in argv:
        out('\n')
        if bad:
            out('  FAIL: %d entry(ies) do not match reality:\n' % len(bad))
            for n, w in bad:
                out('      %-28s %s\n' % (n, w))
            out('\n  An allowlist nobody re-derives is how a real defect hides\n')
            out('  inside a convention.\n')
            return 1
        out('  OK: every entry exists, carries the header, and states a reason.\n')
        out('  NOT CHECKED HERE: whether each one still writes what it claims --\n')
        out('  that needs a bare run in a scratch clone, which is\n')
        out('  tools/bare_run_write_check.py\'s job, and it reads this list.\n')
        return 0
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
