#!/usr/bin/env python
# OWNER: cody
# written 2026-10-15, batch b15, item 5
# REQUIREMENT: every arm landed in batches b13 and b14 must have an ABLATION
#   that can be RE-RUN -- remove the fix, confirm the arm fails, restore,
#   confirm it passes -- because an arm whose failure path has never been
#   driven is an assertion, and an arm whose failure path was driven once by a
#   script that no longer exists is an assertion with a story attached.
r"""The ablation record for the b13 and b14 arms, re-runnable.

    python tests/run_b13_b14_ablation_record.py
    python tests/run_b13_b14_ablation_record.py --list

Exit 0 every ablation behaved · 1 one did not · 3 COULD NOT RUN.

── WHY THIS FILE EXISTS AT ALL ─────────────────────────────────────────────
b13 and b14 DID drive a counterfactual per arm, and both reports list them.
Every one of those runs happened in a THROWAWAY scratchpad script. The claim
"this arm's failure path was driven" therefore rested on a report sentence and
on a file in a temp directory that expires -- which is the same shape as the
hand-driven compliance comment those batches were sent to fix: a real activity
that left no artefact. 51 of those scratch files were still sitting in a temp
directory when b15 started, and the permission layer would not delete them.

So the ablations are a COMMITTED SUITE now. Each one states the fix it removes,
the arm it expects to change state, and the direction. Nothing is asserted
about an arm whose mutation did not apply.

── THE TWO DIRECTIONS, AND BOTH ARE REAL ABLATIONS ─────────────────────────
GREEN-ARM ablation: the arm passes today, so REMOVING the fix must make it
FAIL. That is the ordinary shape.
RED-ARM ablation: the arm is red ON PURPOSE because the defect it names is
routed to another session and not yet fixed. "Remove the fix" is not available
-- there is no fix yet. The equivalent and the only honest substitute is to
APPLY the fix and require the arm to go GREEN, which proves the arm measures
that defect and is not red for an unrelated reason. Each entry says which
direction it is in, and the direction is part of the record.

── EVERY MUTATION IS APPLIED TO A COPY. api/ IS NEVER WRITTEN ──────────────
api/ is hank's and tools/ is cc's. Where a suite reads an api/ module, the
whole api/ tree is copied and the copy is mutated, and the suite is pointed at
it through an injection point it already declares. Where the mutation is in a
tests/ file, the TEST is copied with its REPO constant pinned back at the live
clone. The live clone is read, never written, and `git status --porcelain` is
checked before and after every ablation -- a dirty tree is a COULD NOT RUN,
not a result.
"""
import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TIMEOUT = 300

fails = []
unproven = []


def ok(name):
    print('  ok   ' + name)


def bad(name, detail=''):
    fails.append(name)
    print('  FAIL ' + name + ('\n         ' + str(detail)[:460] if detail else ''))


def cannot(name, why):
    unproven.append(name)
    print('  UNPROVEN ' + name + '\n         ' + str(why)[:400])


def could_not_run(why):
    print('COULD NOT RUN: %s Nothing was verified.' % why)
    sys.exit(3)


def git(*args):
    r = subprocess.run(['git', '-C', REPO] + list(args), capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
    return r.returncode, (r.stdout or '').strip()


def run(cmd, cwd=None, env=None):
    """Run one program and return (exit code, combined output)."""
    try:
        r = subprocess.run(cmd, cwd=cwd or REPO, capture_output=True, text=True,
                           encoding='utf-8', errors='replace', timeout=TIMEOUT,
                           env=env)
    except subprocess.TimeoutExpired:
        return 'TIMEOUT', ''
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def arm_state(out, needle):
    """'ok' / 'FAIL' / 'UNPROVEN' / None for the arm whose text contains needle."""
    for line in out.split('\n'):
        if needle in line:
            s = line.strip()
            for tag in ('ok', 'FAIL', 'UNPROVEN', 'PASS'):
                if s.startswith(tag):
                    return 'ok' if tag == 'PASS' else tag
    return None


# ── THE ABLATIONS ──────────────────────────────────────────────────────────
# `batch`   which batch landed the arm
# `suite`   the file driven
# `arm`     a substring of the arm's own printed name -- never a line number
# `fix`     (find, replace) applied to `target`, or None for the api-tree form
# `target`  'suite' (copy the test, pin REPO) or 'api' (copy api/, mutate it)
# `want`    'FAIL' for a green arm losing its fix, 'ok' for a red arm gaining it
ABLATIONS = [
    {
        'id': 'b14.1a', 'batch': 'b14', 'direction': 'green-arm',
        'suite': 'tests/run_two_axis_tier_parser_probe.py',
        'arm': 'the NEW six-cell shape parses, raises no row-level problem',
        'what': 'the HEADLINE document-scope exclusion is REMOVED from '
                'row_problems(), which is the b14 fix',
        'target': 'suite',
        'fix': ("ROW_PROBLEMS = tuple(sorted(_labels - SYNTHETIC_APP_LABELS - DOCUMENT_LABELS))",
                "ROW_PROBLEMS = tuple(sorted(_labels - SYNTHETIC_APP_LABELS))"),
        'want': 'FAIL',
    },
    {
        'id': 'b14.1b', 'batch': 'b14', 'direction': 'green-arm',
        'suite': 'tests/run_two_axis_tier_parser_probe.py',
        'arm': 'the HEADLINE problem arm 2 sets aside is STILL RAISED',
        'what': 'the fixture is given a matching headline, so the signal arm 2 '
                'sets aside is no longer raised at all',
        'target': 'suite',
        'fix': ("## `fixtureapp` -- all 2 registered resources\n",
                "## `fixtureapp` -- all 2 registered resources\n\n2 resources, 1 A, 1 B, 0 C\n"),
        'want': 'FAIL',
    },
    {
        'id': 'b14.3a', 'batch': 'b14', 'direction': 'green-arm',
        'suite': 'tests/sairnlegacy_reservation_lock.js',
        'arm': "every overlap-spec'd resource's precondition is actually "
               'SATISFIED',
        'what': 'the hardcoded `resource === leg_bookings` is restored, which '
                'is the PRE-FIX state that reported an unattributable 35/36',
        'target': 'suite',
        'fix': ("      const writePayload = ovSpec\n        ? { id: 'X', [ovSpec.groupField]: 'GRP-X',",
                "      const writePayload = resource === 'leg_bookings'\n        ? { id: 'X', facility_id: 'FAC-X',"),
        'want': 'FAIL',
    },
    {
        'id': 'b14.3b', 'batch': 'b14', 'direction': 'green-arm',
        'suite': 'tests/sairnlegacy_reservation_lock.js',
        'arm': 'the overlap SPECS map is NOT EMPTY',
        'what': 'the SPECS map is emptied, which is the state where the '
                'derivation covers nothing and the counts silently drop',
        'target': 'suite',
        'fix': ("const LEG_OVERLAP = require(path.join(ROOT, 'api/_lib/leg-overlap.js'));",
                "const LEG_OVERLAP = { SPECS: {} };"),
        'want': 'FAIL',
    },
    {
        'id': 'b14.4a', 'batch': 'b14', 'direction': 'green-arm',
        'suite': 'tests/sairncare_compliance_window_boundary.test.js',
        'arm': 'ON the anniversary the window ROLLS',
        'what': 'the anniversary comparison is made INCLUSIVE, so the window '
                'is decremented on the anniversary instead of rolling',
        'target': 'api', 'module': 'api/_lib/compliance-rules.js',
        'env': 'SAIRN_B15_COMPLIANCE_RULES',
        'fix': ("    if (on.slice(4) < mmdd) year -= 1;",
                "    if (on.slice(4) <= mmdd) year -= 1;"),
        'want': 'FAIL',
    },
    {
        'id': 'b14.4b', 'batch': 'b14', 'direction': 'green-arm',
        'suite': 'tests/sairncare_compliance_window_boundary.test.js',
        'arm': 'the window opens 2026-02-28',
        'what': 'the leap-day normalisation is removed, so a 2024-02-29 hire '
                'publishes an impossible 2026-02-29',
        'target': 'api', 'module': 'api/_lib/compliance-rules.js',
        'env': 'SAIRN_B15_COMPLIANCE_RULES',
        'fix': ("      from = isRealDate(norm) ? norm : from;",
                "      from = from;"),
        'want': 'FAIL',
    },
    {
        'id': 'b14.4c', 'batch': 'b14', 'direction': 'green-arm',
        'suite': 'tests/sairncare_compliance_window_boundary.test.js',
        'arm': 'yields meets === null, NOT false',
        'what': 'the day-zero withholding is removed, so a shortfall on the '
                'day the window opens is reported as a flat false',
        'target': 'api', 'module': 'api/_lib/compliance-rules.js',
        'env': 'SAIRN_B15_COMPLIANCE_RULES',
        'fix': ("        && win.window_days_elapsed === 0;",
                "        && false;"),
        'want': 'FAIL',
    },
    {
        'id': 'b15.1a', 'batch': 'b15', 'direction': 'green-arm',
        'suite': 'tests/run_criticality_tier_probe.py',
        'arm': 'the register was restored byte for byte',
        'what': '_rm_ro is moved back BELOW the module-level finally: that '
                'calls it, which is the NameError b15 fixed -- and the point '
                'is that the error lands in the CLEANUP and discards every '
                'verdict above it',
        'target': 'suite',
        'fix': None,          # handled specially: delete the definition
        'special': 'drop_rm_ro',
        'want': None,         # the suite dies before any arm prints
        'want_exit_not': 0,
    },
    {
        'id': 'b15.1b', 'batch': 'b15', 'direction': 'green-arm',
        'suite': 'tests/gated_resource_direct_fetch_header.js',
        'arm': 'the SAIRNdesign invoice-create direct fetch is among the sites',
        'what': 'the anchor is reverted to the bare identifier on the RAW '
                'source, which is the rot b15 fixed -- it matched a COMMENT '
                'and parsed 17 names instead of 66',
        'target': 'suite',
        'fix': ("const SRC_NO_COMMENTS = stripComments(API);\nconst gStart = SRC_NO_COMMENTS.indexOf('const SD_SESSION_GATED = {');\nconst gEnd = SRC_NO_COMMENTS.indexOf('const SD_GATE_APP = {');",
                "const SRC_NO_COMMENTS = API;\nconst gStart = SRC_NO_COMMENTS.indexOf('SD_SESSION_GATED');\nconst gEnd = SRC_NO_COMMENTS.indexOf('SD_GATE_APP');"),
        'want': None,
        'want_exit_not': 0,
    },
    {
        'id': 'b15.3', 'batch': 'b15', 'direction': 'RED-arm (fix APPLIED)',
        'suite': 'tests/sd_data_blob_scope_ten_routed_sites.js',
        'arm': 'site 5 remnants',
        'what': 'the conversion is APPLIED to one site -- data: payload becomes '
                'data: storedBlob(payload, []) -- and that site\'s arm must go '
                'GREEN. There is no fix to remove: the defect is routed to '
                'hank and the arm is red on purpose',
        'target': 'api', 'module': 'api/sd-data.js',
        'env': 'SAIRN_B15_SD_DATA',
        'fix': ("remnant_id: String(payload.id), data: payload, updated_at: nowISO()",
                "remnant_id: String(payload.id), data: storedBlob(payload, []), updated_at: nowISO()"),
        'want': 'ok',
    },
]


def _pin_repo(text, ext):
    """Pin the copied test's REPO/ROOT constant back at the live clone."""
    lit = json.dumps(REPO.replace(os.sep, '/'))
    if ext == '.py':
        a = "REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))"
        if a in text:
            return text.replace(a, 'REPO = ' + lit, 1), None
        return text, 'no REPO constant of the expected shape'
    a = "const ROOT = path.join(__dirname, '..');"
    if a in text:
        return text.replace(a, 'const ROOT = ' + lit + ';', 1), None
    return text, 'no ROOT constant of the expected shape'


def drive_suite(path_abs, env=None, cwd=None):
    cmd = ([sys.executable, '-u', path_abs] if path_abs.endswith('.py')
           else ['node', path_abs])
    return run(cmd, cwd=cwd, env=env)


def baseline(suite):
    """The suite as committed: its exit code and output."""
    return drive_suite(os.path.join(REPO, suite.replace('/', os.sep)))


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--list', action='store_true',
                    help='print the ablation table and exit')
    args = ap.parse_args(argv)

    if args.list:
        print('%-8s %-12s %-54s %s' % ('id', 'direction', 'suite', 'arm'))
        for a in ABLATIONS:
            print('%-8s %-12s %-54s %s'
                  % (a['id'], a['direction'][:12], a['suite'], a['arm'][:46]))
        return 0

    # THE TREE MUST BE CLEAN. A modified tracked file fails clean-tree probes
    # after it, so an ablation run on a dirty tree measures the dirt.
    rc, dirt = git('status', '--porcelain')
    if rc != 0:
        could_not_run('git status failed in %s.' % REPO)
    tracked = [l for l in dirt.split('\n')
               if l.strip() and not l.startswith('??')]
    if tracked:
        could_not_run('the working tree has MODIFIED TRACKED FILES, so every '
                      'arm below could be measuring the dirt rather than the '
                      'mutation:\n         ' + '\n         '.join(tracked[:8]))

    print('ABLATION RECORD -- b13/b14 arms, re-runnable  (criteria 2026-10-15.1)')
    print('%d ablation(s). api/ is COPIED and never written; tests are copied '
          'with REPO pinned.\n' % len(ABLATIONS))

    api_copy = None
    tmp = tempfile.mkdtemp(prefix='sairn-b15-ablate-')
    try:
        for a in ABLATIONS:
            suite_abs = os.path.join(REPO, a['suite'].replace('/', os.sep))
            if not os.path.isfile(suite_abs):
                cannot('%s %s' % (a['id'], a['arm'][:60]),
                       '%s does not exist' % a['suite'])
                continue

            # ── STEP 1: the suite AS COMMITTED. The arm must be in the state
            #    the record claims, or the ablation is measuring something else.
            base_rc, base_out = baseline(a['suite'])
            base_state = arm_state(base_out, a['arm'])
            if base_state is None:
                cannot('%s %s' % (a['id'], a['arm'][:60]),
                       'the arm was not found in the suite\'s own output, so '
                       'the ablation has no subject. Its name may have changed '
                       '-- re-read the suite rather than trusting this row.')
                continue
            expect_base = 'FAIL' if a['want'] == 'ok' else 'ok'
            if a.get('want') is None:
                expect_base = 'ok'
            if base_state != expect_base:
                bad('%s BASELINE (%s): the arm is %s as committed and this '
                    'record expects %s' % (a['id'], a['arm'][:48], base_state,
                                           expect_base),
                    'exit=%s' % base_rc)
                continue

            # ── STEP 2: apply the mutation to a COPY ───────────────────────
            env = dict(os.environ)
            run_path = suite_abs
            mutated_ok = True
            why = ''
            if a['target'] == 'suite':
                src = io.open(suite_abs, encoding='utf-8').read()
                ext = os.path.splitext(a['suite'])[1]
                if a.get('special') == 'drop_rm_ro':
                    m = re.search(r'\ndef _rm_ro\(fn, path, _exc\):.*?\n        pass\n',
                                  src, re.S)
                    if not m:
                        mutated_ok, why = False, '_rm_ro definition not found'
                    else:
                        new = src[:m.start()] + '\n' + src[m.end():] + m.group(0)
                elif a['fix'] and a['fix'][0] in src:
                    new = src.replace(a['fix'][0], a['fix'][1], 1)
                else:
                    mutated_ok, why = False, 'the fix anchor was not found'
                if mutated_ok:
                    new, perr = _pin_repo(new, ext)
                    if perr:
                        mutated_ok, why = False, perr
                if mutated_ok:
                    run_path = os.path.join(tmp, 'ablate_' + a['id'].replace('.', '_') + ext)
                    io.open(run_path, 'w', encoding='utf-8', newline='\n').write(new)
            else:
                if api_copy is None:
                    api_copy = os.path.join(tmp, 'api')
                    shutil.copytree(os.path.join(REPO, 'api'), api_copy,
                                    ignore=shutil.ignore_patterns('__pycache__'))
                rel = a['module'].split('/', 1)[1].replace('/', os.sep)
                mod_abs = os.path.join(api_copy, rel)
                pristine = io.open(os.path.join(REPO, a['module'].replace('/', os.sep)),
                                   encoding='utf-8').read()
                if a['fix'][0] not in pristine:
                    mutated_ok, why = False, 'the fix anchor was not found in ' + a['module']
                else:
                    io.open(mod_abs, 'w', encoding='utf-8', newline='\n').write(
                        pristine.replace(a['fix'][0], a['fix'][1], 1))
                    env[a['env']] = mod_abs

            if not mutated_ok:
                cannot('%s %s' % (a['id'], a['arm'][:60]),
                       'THE MUTATION DID NOT APPLY (%s), so nothing was '
                       'ablated. This is not a pass: the fix it removes may '
                       'have been reworded.' % why)
                continue

            mut_rc, mut_out = drive_suite(run_path, env=env)
            mut_state = arm_state(mut_out, a['arm'])

            # ── STEP 3: did the arm change state in the direction claimed ──
            if a.get('want') is None:
                moved = (mut_rc != 0 and mut_rc != base_rc) or mut_state == 'FAIL' \
                        or mut_state is None
                if moved:
                    ok('%s (%s) -- %s: removing the fix breaks the suite '
                       '(exit %s -> %s)' % (a['id'], a['direction'], a['arm'][:44],
                                            base_rc, mut_rc))
                else:
                    bad('%s (%s): removing the fix changed nothing -- exit %s '
                        'both ways, arm still %s. The arm does not measure '
                        'this fix.' % (a['id'], a['direction'], mut_rc, mut_state),
                        mut_out[-400:])
            elif mut_state == a['want']:
                ok('%s (%s) -- %s: %s -> %s, as the record claims'
                   % (a['id'], a['direction'], a['arm'][:44], base_state, mut_state))
            else:
                bad('%s (%s): the arm went %s -> %s and this record expects %s. '
                    '%s' % (a['id'], a['direction'], base_state, mut_state,
                            a['want'], a['what']),
                    mut_out[-420:])

            # ── STEP 4: RESTORE AND RE-CONFIRM. The mutation lived in a copy,
            #    so restoring is proving the ORIGINAL still passes and that the
            #    live clone was never written.
            re_rc, re_out = baseline(a['suite'])
            re_state = arm_state(re_out, a['arm'])
            if re_state == base_state and re_rc == base_rc:
                ok('   ...restored: the committed suite is unchanged (%s, exit %s)'
                   % (re_state, re_rc))
            else:
                bad('   ...RESTORE CHECK FAILED for %s: the committed suite now '
                    'reports %s at exit %s, was %s at exit %s. The ablation may '
                    'have written outside its copy.'
                    % (a['id'], re_state, re_rc, base_state, base_rc))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    rc, dirt2 = git('status', '--porcelain')
    tracked2 = [l for l in dirt2.split('\n')
                if l.strip() and not l.startswith('??')]
    if tracked2:
        bad('THE TREE IS DIRTY AFTER THIS RUN -- an ablation wrote outside its '
            'copy', '\n'.join(tracked2[:8]))
    else:
        ok('the live clone has no modified tracked file after every ablation')

    print('')
    if unproven:
        print('%d UNPROVEN: %s' % (len(unproven), '; '.join(unproven)))
    if fails:
        print('%d failure(s)' % len(fails))
        for f in fails:
            print('  - ' + f)
        return 1
    if unproven:
        return 3
    print('ok  every ablation behaved as its record claims')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
