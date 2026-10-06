"""Live probe of the guardian refusal, against an UNKNOWN slug on purpose.

The guardian check runs before resolveSlug, so a minor with no guardian must be
refused 400 GUARDIAN_REQUIRED and never reach the 404. Using a slug that cannot
exist means nothing is written to any real practice at any point.
"""
import json
import os
import sys
import urllib.request
import urllib.error

# ── THE WORKTREE ROOT, ASKED OF GIT AND THEN CHECKED (2026-10-06) ──────────
# This line hardcoded the absolute path of one clone, so running this probe
# from any other clone imported THAT clone's tools. Nothing would have failed;
# the answer would have been about the wrong tree.
#
# `git rev-parse --show-toplevel` IS THE SOURCE, per instruction -- and it is
# ANCHORED AND VERIFIED, because unanchored it is a trap in this repository
# specifically: the HOME directory is itself a git repository, so discovery
# walks UP from any directory beneath it and SUCCEEDS with exit 0 about the
# wrong repo. tools/git_discovery_anchoring_check.py exists for that hazard and
# it has already produced a fail-open in another tool's probe.
#
# So: anchor with `-C <this file's own directory>`, then CHECK the answer
# actually contains this file. If git is absent, fails, or answers about a tree
# this file is not in, fall back to the __file__ root and SAY SO on stderr --
# a silent fallback would be the same defect one level down.
def _repo_root():
    here = os.path.dirname(os.path.abspath(__file__))
    fallback = os.path.dirname(here)
    try:
        import subprocess
        p = subprocess.run(['git', '-C', here, 'rev-parse', '--show-toplevel'],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if p.returncode == 0:
            root = p.stdout.decode('utf-8', 'replace').strip()
            if root and os.path.isfile(os.path.join(root, 'tools',
                                                    os.path.basename(__file__))):
                return root
            sys.stderr.write(
                'worktree root: git answered %r, which does not contain this '
                'file -- falling back to the path derived from __file__\n'
                % root)
        else:
            sys.stderr.write('worktree root: git rev-parse exited %d -- '
                             'falling back to __file__\n' % p.returncode)
    except Exception as _e:                                      # noqa: BLE001
        sys.stderr.write('worktree root: git rev-parse unavailable (%s) -- '
                         'falling back to __file__\n' % type(_e).__name__)
    return fallback


sys.path.insert(0, os.path.join(_repo_root(), 'tools'))
import sairn_http  # noqa: E402

URL = 'https://sairn.vercel.app/api/sairndental/public-book'


def post(body):
    h = dict(sairn_http.DEFAULT_HEADERS)
    h['Content-Type'] = 'application/json'
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), method='POST', headers=h)
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            return r.status, json.loads(r.read().decode('utf-8', 'replace'))
    except urllib.error.HTTPError as e:
        raw = e.read().decode('utf-8', 'replace')
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {'_raw': raw[:240]}
    except Exception as e:
        return 'ERR', {'_exc': '%s: %s' % (type(e).__name__, e)}


base = {"slug": "__probe_no_such_practice__", "provider_id": "x",
        "procedure_type_id": "y", "start_time": "2026-10-01T15:00:00Z"}
minor = dict(base, patient={"name": "P", "dob": "2015-01-01", "phone": "5555555555"})
withg = dict(base, patient={"name": "P", "dob": "2015-01-01", "phone": "5555555555"},
             guardian={"name": "A Parent", "phone": "5555555556"})
adult = dict(base, patient={"name": "P", "dob": "1980-01-01", "phone": "5555555555"})
nameonly = dict(base, patient={"name": "P", "dob": "2015-01-01", "phone": "5555555555"},
                guardian={"name": "A Parent"})

checks = []


def code(r):
    return (r[1].get('error') or {}).get('code') if isinstance(r[1], dict) else None


r = post(minor)
checks.append(('minor, NO guardian -> 400 GUARDIAN_REQUIRED', r[0] == 400 and code(r) == 'GUARDIAN_REQUIRED', r))
r = post(nameonly)
checks.append(('minor, guardian NAME but no contact -> 400', r[0] == 400 and code(r) == 'GUARDIAN_REQUIRED', r))
r = post(withg)
checks.append(('minor WITH guardian -> gets past the check (404 unknown slug)', r[0] == 404 and code(r) == 'UNKNOWN_SLUG', r))
r = post(adult)
checks.append(('adult, no guardian -> gets past the check (404 unknown slug)', r[0] == 404 and code(r) == 'UNKNOWN_SLUG', r))

bad = 0
for name, ok, res in checks:
    print(('  OK   ' if ok else '  FAIL ') + name + '  -> ' + str(res[0]) + ' ' + str(code(res)))
    if not ok:
        bad += 1
        print('        ' + json.dumps(res[1])[:220])
print('\n%d/%d live checks passed' % (len(checks) - bad, len(checks)))
sys.exit(1 if bad else 0)
