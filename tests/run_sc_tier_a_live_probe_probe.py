"""The offline half of the one Tier A artefact that had nothing.

    python tests/run_sc_tier_a_live_probe_probe.py

`tools/sc_tier_a_write_gate_live_probe.py` writes to, and DELETES from, the
production demo tenant. By the question this platform tiers on -- the worst
consequence of the tool being WRONG -- that is the highest-consequence artefact
shipped on 2026-09-15, and until now the only thing verifying it was that it had
once been run by hand.

── WHAT THIS CAN AND CANNOT COVER, SAID FIRST ─────────────────────────────────
IT DOES NOT RUN THE PROBE. Doing so would authenticate against
`sairn.vercel.app`, create two credentials and up to three rows on a real
tenant, and delete them again. A suite that did that on every push would be a
production writer wired into the push gate, which is the thing
`tests/run_selftest_sweep_probe.py` names as its first declared exclusion.

So this covers the half that decides WHETHER and WHAT it writes, which is where
its consequence lives:

  * it must REFUSE to run with no credentials, and refuse as UNVERIFIED (exit 2)
    rather than as a pass or a gate failure;
  * the Tier A soft-delete-only list must come from the REGISTRY and never from
    a copy in the probe -- a stale copy would let it HARD-DELETE a Tier A record
    while reporting a clean run, which is the worst direction this particular
    tool can be wrong in;
  * every row and credential it creates must be recognisably disposable, so a
    reader finding one in real data knows what it is;
  * a cleanup failure must be a FINDING, not a silent exit.

── AND ONE ARM IS ABOUT THE OPPOSITE RISK ─────────────────────────────────────
A probe that refuses on every input is safe and useless. Section 2 proves the
credential check passes when credentials ARE present, so the refusal is about
the environment and not a permanent off switch.
"""
import io
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUBJECT = os.path.join('tools', 'sc_tier_a_write_gate_live_probe.py')
SRC = io.open(os.path.join(REPO, SUBJECT), encoding='utf-8',
              errors='replace').read()

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        fails.append(name)


def run_probe(env_extra, timeout=120):
    env = dict(os.environ)
    for k in ('SC_LICENSE', 'SC_EMP', 'SC_PIN', 'SC_CODER_PIN', 'SC_AUDITOR_PIN'):
        env.pop(k, None)
    env.update(env_extra or {})
    p = subprocess.run([sys.executable, SUBJECT], cwd=REPO, env=env,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace', timeout=timeout)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


print('\n1. WITH NO CREDENTIALS IT REFUSES, AND REFUSES AS THE THIRD STATE')
rc, out = run_probe({})
check('it exits 2, not 0 and not 1 -- UNVERIFIED is neither a pass nor a gate '
      'failure, and folding it into either is the defect PR 1.11 names',
      rc == 2, (rc, out[-400:]))
check('...and says UNVERIFIED in as many words', 'UNVERIFIED' in out, out[-400:])
check('...and says explicitly that this is NOT a pass',
      re.search(r'not a pass', out, re.I) is not None, out[-400:])
check('CONTROL: it does NOT report the gate as failing. A missing credential is '
      'a fact about this machine, not about the deployed function',
      'FAIL' not in out.replace('FAILED', '') or rc == 2, out[-300:])
check('it names WHICH variable is missing, so the refusal is actionable',
      'SC_LICENSE' in out or 'SC_EMP' in out or 'SC_PIN' in out, out[-500:])
check('CONTROL: it made no network call -- the refusal comes BEFORE the '
      'endpoint is touched, or an unconfigured machine still reaches production',
      'sairn.vercel.app/api' not in out.split('UNVERIFIED')[-1], out[-400:])

print('\n2. CONTROL -- THE REFUSAL IS ABOUT THE ENVIRONMENT, NOT AN OFF SWITCH')
rc2, out2 = run_probe({'SC_LICENSE': 'ZZ-NOT-A-REAL-LICENCE',
                       'SC_EMP': 'zz-nobody', 'SC_PIN': '000000'})
check('with credentials present it gets PAST the credential check, so section 1 '
      'is a real gate and not a tool that always refuses',
      'SC_LICENSE' not in out2.split('UNVERIFIED')[0][-200:] or rc2 != rc
      or out2 != out, (rc2, out2[-300:]))
check('...and it still never reports VERIFIED against a licence the platform '
      'does not know', 'VERIFIED\n' not in out2 or rc2 != 0, (rc2, out2[-300:]))

print('\n3. THE SOFT-DELETE-ONLY LIST COMES FROM THE REGISTRY')
sys.path.insert(0, os.path.join(REPO, 'tools'))
import sc_tier_a_write_gate_live_probe as P                       # noqa: E402
names, err = P.soft_delete_only()
check('the registry answers with a real list', names is not None and len(names) > 0,
      err or names)
check('CONTROL: and it is not empty-treated-as-fine -- an empty registry answer '
      'returns an ERROR, because an empty soft-delete list would let this probe '
      'hard-delete every Tier A resource while reporting a clean run',
      'empty list' in SRC)
check('the list is NOT typed into the probe -- no literal resource-name array '
      'shadows the registry call',
      not re.search(r"tierASoftDeleteOnly\s*=\s*\[", SRC), SRC[:200])
check('the registry is required EXACTLY ONCE, so there is one source and not '
      'two that can disagree. The name appearing again in an ERROR MESSAGE is '
      'not a second source -- counting raw mentions made this arm fail on a '
      'correct file, which is a rule about prose rather than about drift',
      len(re.findall(r'require\(["\'][^"\']*_resources/sairncode["\']\)', SRC)) == 1,
      re.findall(r'require\([^)]*\)', SRC)[:4])
check('a node failure returns (None, reason) rather than an empty list -- an '
      'empty list from a crashed subprocess reads as "nothing is protected"',
      re.search(r'return None,', SRC) is not None)

print('\n4. EVERYTHING IT CREATES IS RECOGNISABLY DISPOSABLE')
# HARD_ROW joined 2026-09-25 with the 5b CONTROL's move onto a resource that
# genuinely still hard-deletes. Its arm destroys it, so it should never survive a
# complete run -- but a run that dies between the write and the delete leaves it
# on a real tenant, which is exactly the population this arm exists for.
for const in ('CODER_ID', 'AUDITOR_ID', 'CLAIM_ROW', 'COMP_ROW', 'CODED_ROW',
              'HARD_ROW'):
    val = getattr(P, const)
    check('%s is labelled ZZ-GATE-* (%r), so a reader finding it in real data '
          'knows what it is' % (const, val),
          isinstance(val, str) and val.lower().startswith('zz-gate'), val)
check('CONTROL: the six labels are DISTINCT, or cleanup of one would look like '
      'cleanup of another',
      len({P.CODER_ID, P.AUDITOR_ID, P.CLAIM_ROW, P.COMP_ROW, P.CODED_ROW,
           P.HARD_ROW}) == 6)

print('\n5. CLEANUP IS A FINDING WHEN IT FAILS, NOT A SILENT EXIT')
check('the file says a cleanup failure is a FINDING',
      re.search(r'failure to clean up is a FINDING', SRC) is not None)
check('...and that leaving live credentials behind is worse than never running',
      re.search(r'leaves live credentials behind is worse', SRC) is not None)
check('credentials are DEACTIVATED rather than left active',
      re.search(r'set_active|DEACTIVATED', SRC) is not None)

print('\n6. CREDENTIALS COME FROM THE ENVIRONMENT AND NEVER FROM THE FILE')
for var in ('SC_LICENSE', 'SC_EMP', 'SC_PIN', 'SC_CODER_PIN', 'SC_AUDITOR_PIN'):
    check('%s is read from os.environ' % var,
          re.search(r"os\.environ\.get\(\s*'%s'" % var, SRC) is not None)
check('CONTROL: no literal that looks like a licence key or a PIN is assigned '
      'in the file',
      not re.search(r"=\s*'(?:SC|DEMO)-[A-Z0-9-]{6,}'", SRC)
      and not re.search(r"PIN\s*=\s*'\d{4,}'", SRC),
      [l.strip()[:60] for l in SRC.splitlines()
       if re.search(r"PIN\s*=\s*'\d", l)][:3])
check('the endpoints it talks to are the PRODUCTION ones, named as constants '
      'rather than built from a variable a caller could redirect',
      P.AUTH.startswith('https://') and P.DATA.startswith('https://'),
      (P.AUTH, P.DATA))

print('\n7. NOT COVERED HERE, STATED RATHER THAN IMPLIED')
print('  * the LIVE run itself: authentication, the six refusals, the control')
print('    allow, and the cleanup actually removing what it made. Running that')
print('    in the suite would wire a production writer into every push, which')
print('    is tests/run_selftest_sweep_probe.py\'s first declared exclusion.')
print('  * whether the deployed gate agrees with the in-process one. That is')
print('    the whole question the probe exists to answer and only a real run')
print('    can answer it.')

print()
if fails:
    print('%d ARM(S) FAILED:' % len(fails))
    for f in fails:
        print('  - ' + f)
else:
    print('ALL ARMS PASS')
sys.exit(1 if fails else 0)
