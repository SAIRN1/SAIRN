"""Report known npm advisories against the committed lockfile.

    python tools/npm_audit_check.py           # 0 clean, 1 findings, 3 could-not-tell
    python tools/npm_audit_check.py --quiet   # exit code only

WHY THIS EXISTS. On 2026-09-10 two moderate Dependabot alerts sat open for at
least a day, and the SOUP register recorded them as untriaged with this reason:
*"the alert detail needs the GitHub UI or an authenticated API call, and `gh` is
not installed in this clone."* **That reason was assumed and it was wrong.**
`npm audit` reads `package-lock.json` and the public npm registry; it needs no
GitHub credential at all. One command named both advisories, both were the same
package, and the fix was a lockfile-only bump.

So the blocker was never the missing tool -- it was that nothing ran the check
that did not need it. This is that check, wired as a report-only checker so it
runs after a push rather than when somebody remembers. Same argument the rest
of this repo's mechanisms make: a rule that depends on remembering is the
failure mode CLAUDE.md keeps recording.

EXIT 3 IS "COULD NOT TELL", AND THAT MATTERS MORE HERE THAN IN MOST CHECKERS,
because this one needs the network. npm unreachable, offline, a registry 5xx, a
proxy -- every one of those makes `npm audit` fail, and collapsing that into 0
would print a clean line over a check that did not run. That is the exact shape
of the post-push watcher that swallowed a 403 and said nothing. A missing `npm`
is also exit 3, not a pass.

WHAT IT DOES NOT DO. It does not fix anything and it does not judge
reachability. `npm audit` reports that a vulnerable version is in the tree, not
that this platform can reach the vulnerable code path -- the `qs` triage found
one of the two advisories was in `qs.parse`, which `stripe` never calls. Read
the advisory before acting on a line from this tool.
"""
import json
import os
import shutil
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEVERITY_ORDER = ('critical', 'high', 'moderate', 'low', 'info')


def npm_exe():
    """The npm executable, or None.

    ON WINDOWS npm IS `npm.cmd` AND `subprocess.run(['npm', ...])` RAISES
    FileNotFoundError. The first version of this file did exactly that, so it
    reported `SKIPPED: npm is not on PATH` on the machine this repo is
    developed on -- an honest exit 3 that would have been printed on every push
    in every clone forever, which is a checker that never checks. Caught by
    running it, not by reading it; `npm audit` works fine from the same shell.
    """
    for name in ('npm.cmd', 'npm.exe', 'npm') if os.name == 'nt' else ('npm',):
        found = shutil.which(name)
        if found:
            return found
    return None


def cannot_tell(why):
    print('SKIPPED: %s' % why)
    print('This is NOT a pass. `npm audit` needs the network and the npm '
          'registry; a failure here means the tree was not checked, which is '
          'not the same as the tree being clean.')
    return 3


def main(argv):
    quiet = '--quiet' in argv
    if not os.path.exists(os.path.join(REPO, 'package-lock.json')):
        return cannot_tell('no package-lock.json -- nothing to audit against')

    npm = npm_exe()
    if not npm:
        return cannot_tell('`npm` is not on PATH in this clone')
    try:
        r = subprocess.run([npm, 'audit', '--json'], cwd=REPO,
                           capture_output=True, text=True, timeout=180)
    except OSError as e:
        return cannot_tell('could not run `%s audit`: %s' % (npm, e))
    except subprocess.TimeoutExpired:
        return cannot_tell('`npm audit` did not finish within 180s')

    # npm audit exits 1 when it FINDS something, so a non-zero exit is not an
    # error -- the JSON body is what distinguishes "found advisories" from
    # "could not run". No parseable body means no audit happened.
    try:
        report = json.loads(r.stdout)
    except ValueError:
        detail = (r.stderr or r.stdout or '').strip().splitlines()
        return cannot_tell('`npm audit` produced no parseable JSON: %s'
                           % (detail[0] if detail else 'no output'))

    if 'error' in report and 'vulnerabilities' not in report:
        err = report['error']
        return cannot_tell('npm reported an error: %s'
                           % (err.get('summary') or err))

    vulns = report.get('vulnerabilities') or {}
    counts = ((report.get('metadata') or {}).get('vulnerabilities') or {})
    total = sum(counts.get(s, 0) for s in SEVERITY_ORDER)

    findings = []
    for name in sorted(vulns):
        v = vulns[name]
        advisories = [a for a in (v.get('via') or []) if isinstance(a, dict)]
        for a in advisories:
            findings.append(
                '  - %s %s@%s (%s) %s -- %s'
                % (a.get('severity', v.get('severity', '?')),
                   name, v.get('range', '?'),
                   'direct' if v.get('isDirect') else 'transitive',
                   a.get('url', ''), a.get('title', '')))
        if not advisories:
            findings.append('  - %s %s %s -- advisory detail not in the report'
                            % (v.get('severity', '?'), name, v.get('range', '?')))

    if not quiet:
        print('npm audit check')
        print('  advisories reported : %d across %d package(s)'
              % (total, len(vulns)))
        if findings:
            print('\n%d FINDING(S):' % len(findings))
            for f in findings:
                print(f)
            print('\nRead the advisory before acting: this reports that a '
                  'vulnerable VERSION is in the tree, not that the vulnerable '
                  'code path is reachable from this platform. Prefer '
                  '`npm update <pkg> --package-lock-only` where the fixed '
                  'version satisfies the existing range -- '
                  '`npm install <pkg>@<version>` adds a DIRECT dependency for '
                  'a package nothing here imports.')
        else:
            print('  CLEAN -- no known advisories against the committed lockfile.')
    return 1 if findings else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
