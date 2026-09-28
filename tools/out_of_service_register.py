"""A control taken out of service is a COVERAGE GAP. Count it or lose it.

Run:  python tools/out_of_service_register.py
      python tools/out_of_service_register.py --json

── WHY ─────────────────────────────────────────────────────────────────────
On 2026-09-28 FOUR live probes were taken out of service in a single change.
tools/audit_licence.py started refusing a non-audit licence, and the audit
licences three of those probes need did not exist. That was the right trade -- a
residue risk on a demo-facing licence for a coverage gap -- but it WAS a trade,
and nothing counted it.

A guard that silently disables four probes has removed four probes' worth of
evidence and reported only that it was installed. The next run of everything
else is greener than the week before, for a reason nobody wrote down.

── WHAT IT DECIDES ─────────────────────────────────────────────────────────
  * every entry in docs/out-of-service-controls.json carries reason, owner,
    what unblocks it and a date -- an entry missing any of those is a finding,
    because "blocked" with no route out is a silence wearing a status;
  * the COUNT has not risen above `ceiling`;
  * no entry has aged past `max_age_days`;
  * and -- the half that cannot be gamed by editing the register -- **an
    out-of-service probe with NO entry is a finding**. Today that is detected
    for one shape: a VERIFICATION live probe whose audit licence is not one that
    exists. Other shapes are not detected and the report says so.

THE COUNT IS PUBLISHED EVERY RUN, clean or not. A register whose number is only
visible when it fails is a number nobody watches.

── WHAT IT CANNOT SEE, so the gap is a decision rather than an omission ────
* A control commented out inside a suite. Nothing here reads assertions.
* A probe that runs, fails, and is being ignored. That is a different failure and
  a worse one; this tool is about controls that do not run at all.
* Whether the coverage_lost sentence is TRUE. It is prose, and an honest one is
  worth more than a field this tool could check.
"""
import argparse
import datetime
import io
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from checker_kit import (EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN,  # noqa: E402
                         REPO, read, finish)

CRITERIA_VERSION = '2026-09-28.1'
REGISTER = os.path.join(REPO, 'docs', 'out-of-service-controls.json')
REQUIRED_FIELDS = ('id', 'subject', 'kind', 'out_since', 'owner', 'reason',
                   'coverage_lost', 'unblocked_by', 'blocked_on')


def today(argv):
    """The clock comes from --today or from the system, and WHICH is printed.

    A staleness check whose date nobody can see is one nobody can reproduce.
    """
    if '--today' in argv:
        return argv[argv.index('--today') + 1], 'given'
    return datetime.date.today().isoformat(), 'system clock'


def detect_undeclared(declared_subjects):
    """VERIFICATION probes whose audit licence does not exist.

    Read from tools/audit_licence.py's measured KNOWN_AUDIT_KEYS rather than a
    second list here -- two copies of "which licences exist" is two things to
    drift, and that tuple already carries its own measurement date.
    """
    try:
        from audit_licence import KNOWN_AUDIT_KEYS
    except Exception as e:                                    # pragma: no cover
        return None, ('tools/audit_licence.py could not be imported (%s), so '
                      'the undeclared-probe half DID NOT RUN. That is a third '
                      'state, not a clean one.' % e)
    out = subprocess.run(['git', 'ls-files', 'tools/*.py', 'tests/*.py'],
                         cwd=REPO, capture_output=True, text=True,
                         encoding='utf-8', errors='replace')
    if out.returncode != 0:
        return None, '`git ls-files` failed, so the probe universe is unknown.'
    found = []
    for f in [x.strip() for x in out.stdout.split('\n') if x.strip()]:
        try:
            src = read(os.path.join(REPO, f))
        except (IOError, OSError):
            continue
        if "LIVE_PROBE_CLASS = 'VERIFICATION'" not in src:
            continue
        if 'require_audit_licence' not in src:
            continue
        # Which licence family does it take? The env var name is the anchor.
        m = re.search(r"os\.environ\.get\(['\"]([A-Z]+)_LICENSE['\"]", src)
        if not m:
            continue
        fam = m.group(1)
        if any(k.startswith(fam + '-AUDIT') for k in KNOWN_AUDIT_KEYS):
            continue
        if f in declared_subjects:
            continue
        found.append('%s is a VERIFICATION probe guarded to a %s-AUDIT licence '
                     'that does not exist, and it has NO entry in the register. '
                     'An out-of-service control nobody declared is '
                     'indistinguishable from one that is running and finding '
                     'nothing.' % (f, fam))
    return found, None


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--today', default=None)
    args = ap.parse_args(argv)

    if not os.path.isfile(REGISTER):
        print('COULD NOT RUN: %s is missing. An absent register is not an empty '
              'one -- it is a question nobody can answer.'
              % os.path.relpath(REGISTER, REPO))
        return EXIT_COULD_NOT_RUN
    try:
        reg = json.loads(read(REGISTER))
    except ValueError as e:
        print('COULD NOT RUN: %s does not parse (%s).'
              % (os.path.relpath(REGISTER, REPO), e))
        return EXIT_COULD_NOT_RUN

    entries = reg.get('entries') or []
    ceiling = reg.get('ceiling')
    max_age = reg.get('max_age_days')
    if ceiling is None or max_age is None:
        print('COULD NOT RUN: the register declares no ceiling or no '
              'max_age_days, so there is nothing for a rise to be measured '
              'against.')
        return EXIT_COULD_NOT_RUN

    now, clock = today(argv)
    findings, could_not_run = [], []

    for e in entries:
        missing = [k for k in REQUIRED_FIELDS if not str(e.get(k) or '').strip()]
        if missing:
            findings.append('entry %r is missing %s -- "blocked" with no route '
                            'out is a silence wearing a status.'
                            % (e.get('id') or '(no id)', ', '.join(missing)))
            continue
        try:
            d0 = datetime.date.fromisoformat(e['out_since'])
            age = (datetime.date.fromisoformat(now) - d0).days
        except ValueError:
            findings.append('entry %r has an unreadable out_since %r'
                            % (e['id'], e['out_since']))
            continue
        if age > max_age:
            findings.append('%s has been out of service %d days, past the '
                            'stated limit of %d. Owner %s, blocked on %s.'
                            % (e['id'], age, max_age, e['owner'], e['blocked_on']))

    if len(entries) > ceiling:
        findings.append('THE COUNT HAS RISEN: %d entries against a ceiling of '
                        '%d. Raising the ceiling is a decision somebody makes '
                        'out loud, not a side effect of adding an entry.'
                        % (len(entries), ceiling))

    undeclared, err = detect_undeclared({e.get('subject') for e in entries})
    if err:
        could_not_run.append(err)
    else:
        findings.extend(undeclared)

    print('OUT-OF-SERVICE CONTROL REGISTER')
    print('  criteria        : %s' % CRITERIA_VERSION)
    print('  date            : %s  (%s)' % (now, clock))
    print('  OUT OF SERVICE  : %d   (ceiling %d, max age %d days)'
          % (len(entries), ceiling, max_age))
    for e in entries:
        try:
            age = (datetime.date.fromisoformat(now)
                   - datetime.date.fromisoformat(e.get('out_since', ''))).days
            age = '%dd' % age
        except ValueError:
            age = '?'
        print('    %-4s %-14s %-46s blocked on: %s'
              % (age, e.get('kind', '?'), (e.get('subject') or '?')[:46],
                 e.get('blocked_on', '?')))
    print()
    print('  THE COUNT IS PUBLISHED EVERY RUN, clean or not -- a register whose')
    print('  number is only visible when it fails is one nobody watches.')
    print('  NOT A COMPLETE LIST: a control commented out inside a suite is')
    print('  invisible here, and so is one that runs, fails and is ignored.')

    if args.json:
        print(json.dumps({'criteria': CRITERIA_VERSION, 'date': now,
                          'count': len(entries), 'ceiling': ceiling,
                          'max_age_days': max_age, 'entries': entries,
                          'findings': findings,
                          'could_not_run': could_not_run}, indent=2))

    return finish(findings, could_not_run=could_not_run, clean_line=(
        '\n%d control(s) out of service, all declared, none past %d days, count '
        'at or under the ceiling of %d.' % (len(entries), max_age, ceiling)))


if __name__ == '__main__':
    sys.exit(main())
