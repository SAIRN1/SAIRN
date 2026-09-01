"""Live-verify push-gate check 4 the same way checks 1-3 were verified:
a planted violation must BLOCK, a clean push must be ALLOWED.

Driven from Python so nothing depends on Bash command text, and every arm
asserts on the refusal REASON, not just the exit code -- three of tonight's
probe arms returned the right code for the wrong reason.
"""
import subprocess, os, sys, re

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()
EP = 'api/legal-deadlines.js'


def run(*a, **k):
    return subprocess.run(list(a), cwd=REPO, capture_output=True, text=True, **k)


def clean_tree():
    return run('git', 'status', '--porcelain').stdout.strip()


assert clean_tree() == '', 'probe needs a clean tree, got:\n' + clean_tree()
start = run('git', 'rev-parse', 'HEAD').stdout.strip()
R = {}


def dry_push():
    r = run('git', 'push', '--dry-run', 'origin', 'HEAD:main')
    err = r.stderr or ''
    return {
        'exit': r.returncode,
        'blocked_by_seam': 'does not forward every input its engine reads' in err,
        'blocked_by_sql': 'no live schema snapshot' in err,
        'rejected_by_remote': 'fetch first' in err or 'rejected' in err,
        'names_field': 'service_methods' in err,
    }


# ---- ARM 1: CLEAN api change must be allowed by check 4 ----
p = os.path.join(REPO, 'api', '_lib', 'zz_probe_clean.js')
open(p, 'w').write('// probe: a new lib nothing calls\nmodule.exports = {};\n')
run('git', 'add', 'api/_lib/zz_probe_clean.js')
run('git', 'commit', '-q', '-m', 'PROBE clean api change')
R['clean_api_change'] = dry_push()
run('git', 'reset', '--mixed', start)
os.remove(p)

# ---- ARM 2: PLANTED seam violation must block ----
path = os.path.join(REPO, EP)
src = open(path, encoding='utf-8').read()
patched = re.sub(r'\n\s*service_methods\s*:[^\n]*\n', '\n', src, count=1)
assert patched != src, 'fixture invalid'
open(path, 'w', encoding='utf-8').write(patched)
run('git', 'add', EP)
run('git', 'commit', '-q', '-m', 'PROBE seam violation')
R['planted_violation'] = dry_push()
run('git', 'reset', '--mixed', start)
run('git', 'checkout', '--', EP)

R['restored'] = (clean_tree() == '')
R['head_restored'] = (run('git', 'rev-parse', 'HEAD').stdout.strip() == start)

for k, v in R.items():
    print('%-20s %s' % (k, v))
print()
ok = (R['planted_violation']['blocked_by_seam'] and R['planted_violation']['names_field']
      and not R['clean_api_change']['blocked_by_seam']
      and R['restored'] and R['head_restored'])
print('CHECK 4 VERIFIED (planted blocks by seam + names the field, clean not blocked by seam):', ok)
sys.exit(0 if ok else 1)
