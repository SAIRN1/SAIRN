"""tests/run_secrets_inventory_probe.py -- item 61's absence column can be
shown to FIRE on a genuinely unguarded read and to STAY QUIET on a guarded one.

    python tests/run_secrets_inventory_probe.py

THE COLUMN THAT MATTERS IS "ABSENCE", and its two failure modes are opposite
and both fatal:

  * TOO PERMISSIVE -- a heuristic that counts any guard anywhere as a guard on
    THIS variable reports the whole tree as covered, which is a security page
    that says nothing. Section 2 pins that a guard on a DIFFERENT variable does
    not count.
  * TOO STRICT -- the first run of this tool looked only for
    `!process.env.NAME`, and almost nothing in this tree is written that way.
    It reported four correctly-guarded OIDC variables and a correctly-guarded
    live Stripe key as unguarded. **A column wrong about the majority case is a
    column people switch off.** Section 3 pins the alias form, the conjunction
    form and the one-hop-into-a-required-module form against the real files
    that use each.

And the honesty arm: the hand-written classification must be FORCED. Section 4
pins that an unclassified variable makes the tool refuse rather than print a
row with a blank cell.
"""
import io
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import secrets_inventory as S                                    # noqa: E402

# THIS FILE IS THE CONTROL FOR secrets_inventory.py, declared rather than
# inferred. BOTH DIRECTIONS:
#   FIRES   2c/3a-3e -- a guarded secret is recognised in all four real forms,
#           and 3e goes red the moment any CREDENTIAL loses its guard.
#   SILENT  2a/2b -- a guard on a DIFFERENT variable, and a test with no
#           refusal behind it, are correctly NOT counted as guards.
CONTROLS_FOR = ['secrets_inventory.py']

failures = []


def check(label, ok, detail=''):
    print(('  PASS ' if ok else '  FAIL ') + label + (('   ' + str(detail)) if detail else ''))
    if not ok:
        failures.append(label)


print('1. the blind lock')
check('1a  every synthetic source classifies as written', S.run_fixtures() == [],
      S.run_fixtures())
p = subprocess.run([sys.executable, os.path.join(REPO, 'tools', 'secrets_inventory.py'),
                    '--fixtures'], capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=REPO)
check('1b  the lock runs on its own and passes', p.returncode == 0, 'exit %d' % p.returncode)

print('2. TOO PERMISSIVE -- a guard is a guard on THIS variable or it is nothing')
check('2a  a guard on a different variable does not count',
      S._guard_verdict("if (!process.env.OTHER) { return; }\nconst k = process.env.MY_KEY;",
                       'MY_KEY') is False)
check('2b  a test with no refusal anywhere does not count -- reading the value '
      'in an if() and carrying on is not a guard',
      S._guard_verdict("const k = process.env.MY_KEY;\nif (k) { use(k); }", 'MY_KEY') is False)
check('2c  CONTROL: the obvious guarded form IS recognised, or 2a and 2b would '
      'pass on a checker that never says guarded',
      S._guard_verdict("if (!process.env.MY_KEY) { res.status(500); return; }", 'MY_KEY') is True)

print('3. TOO STRICT -- the three forms this tree actually uses')
# Each of these is checked against the REAL file that uses that form, not
# against a synthetic sample, because the failure being guarded against is
# precisely a heuristic that works on samples and not on the repo.
rows = {r['name']: r for r in S.analyse()}


def covered(name):
    r = rows[name]
    return bool(r['guarded'] or r['guarded_via'])


check('3a  ALIAS form -- api/sairncash/checkout.js reads STRIPE_SECRET_KEY into '
      '`stripeKey`; the first version of this tool called that unguarded',
      covered('STRIPE_SECRET_KEY'), rows['STRIPE_SECRET_KEY'])
check('3b  CONJUNCTION form -- api/_lib/auth.js tests all four OIDC values in '
      'one !!(a && b && c && d)',
      all(covered(n) for n in ('OIDC_CLIENT_ID', 'OIDC_CLIENT_SECRET',
                               'OIDC_ISSUER_URL', 'OIDC_REDIRECT_URI')))
check('3c  MISSING-LIST form -- api/sairndental/send-reminder.js names the '
      'variable as a string in a missing[] list before refusing',
      covered('RESEND_API_KEY') and covered('SUPABASE_SERVICE_ROLE_KEY'))
check('3d  ONE HOP -- checkout.js does not test STRIPE_SECRET_KEY itself; item '
      '94 moved that into api/_lib/stripe-config.js, and a tool that punished '
      'the refactor which FIXED a real confusion would lose its audience',
      any('stripe-config' in m for _, m in rows['STRIPE_SECRET_KEY']['guarded_via'])
      or bool(rows['STRIPE_SECRET_KEY']['guarded']),
      rows['STRIPE_SECRET_KEY']['guarded_via'])
# AND THE RESULT THAT MAKES THE COLUMN WORTH READING: after all three forms are
# handled, NO CREDENTIAL is left unexplained. If that ever stops being true it
# is either a real finding or a regression in the heuristic, and either way
# somebody should look.
unguarded_creds = [n for n, r in rows.items()
                   if r['kind'] == 'CREDENTIAL' and not (r['guarded'] or r['guarded_via'])]
check('3e  no CREDENTIAL is left with NO GUARD FOUND -- if this goes red it is '
      'either a real unguarded secret or a regression here, and both are worth '
      'stopping for', unguarded_creds == [], unguarded_creds)

print('4. the hand-written half is FORCED, not optional')
saved = dict(S.SECRETS)
try:
    S.SECRETS.pop('CRON_SECRET')
    probs = S.vocabulary_problems(S.analyse())
    check('4a  a variable the code reads with no classification makes the tool '
          'REFUSE -- a new secret breaks this on purpose',
          any('UNCLASSIFIED' in p and 'CRON_SECRET' in p for p in probs), probs[:2])
finally:
    S.SECRETS.clear()
    S.SECRETS.update(saved)
S.SECRETS['NO_SUCH_VARIABLE_ANYWHERE'] = ('TUNING', 'a fixture')
try:
    probs = S.vocabulary_problems(S.analyse())
    check('4b  ...and an entry naming a variable nothing reads is reported as '
          'STALE, so the classification cannot rot in the other direction',
          any('STALE ENTRY' in p for p in probs), probs[:2])
finally:
    S.SECRETS.pop('NO_SUCH_VARIABLE_ANYWHERE')
check('4c  CONTROL: with the real map, there are no vocabulary problems at all',
      S.vocabulary_problems(S.analyse()) == [], S.vocabulary_problems(S.analyse())[:3])

print('5. the document and the code cannot silently disagree')
r = subprocess.run([sys.executable, os.path.join(REPO, 'tools', 'secrets_inventory.py'),
                    '--check'], capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=REPO)
check('5a  --check passes against the committed document', r.returncode == 0,
      (r.stdout or '')[-200:])
doc = io.open(os.path.join(REPO, 'docs', 'SECRETS-INVENTORY.md'), encoding='utf-8').read()
check('5b  the document states what it CANNOT see, including that it reads the '
      'CODE and not the deployment',
      'cannot see' in doc.lower() and 'not the deployment' in doc.lower())
check('5c  ...and that the absence column is a HEURISTIC with a third state, '
      'rather than a verdict', 'NO GUARD FOUND' in doc and 'HEURISTIC' in doc.upper())
check('5d  no CREDENTIAL value is printed anywhere in the document -- an '
      'inventory that leaks what it inventories is worse than none',
      'sk_live' not in doc and 'sk_test' not in doc and 'eyJ' not in doc)

# -- FIRES, ASSERTED ON THE TOOL'S OWN EXIT CODE --------------------------
# Everything above proves the guard heuristic classifies correctly. This proves
# the CHECKER REPORTS: pointed at a document that no longer matches the code,
# --check must exit 1. A tool that notices drift and exits 0 is one nothing
# downstream can chain, which is why tools/checker_control_check.py counts an
# exit-code comparison as evidence of firing.
print('6. FIRES and SILENT on the same entry point')
import contextlib                                                # noqa: E402
import tempfile                                                  # noqa: E402
_tmp = tempfile.mkdtemp(prefix='secrets-drift-')
_doc = os.path.join(_tmp, 'SECRETS-INVENTORY.md')
io.open(_doc, 'w', encoding='utf-8', newline=chr(10)).write('# not the real document' + chr(10))
_real_doc = S.DOC
try:
    S.DOC = _doc
    _buf = io.StringIO()
    with contextlib.redirect_stdout(_buf):
        _rc = S.main(['--check'])
    check('6a  FIRES: pointed at a document that does not match the code, --check '
          'exits 1 and says to regenerate',
          _rc == 1 and 'no longer matches' in _buf.getvalue(), 'exit %s' % _rc)
    S.DOC = os.path.join(_tmp, 'absent.md')
    _buf2 = io.StringIO()
    with contextlib.redirect_stdout(_buf2):
        _rc2 = S.main(['--check'])
    check('6b  a MISSING document is exit 2, COULD NOT RUN -- not folded into '
          'either a pass or a finding',
          _rc2 == 2 and 'COULD NOT RUN' in _buf2.getvalue(), 'exit %s' % _rc2)
finally:
    S.DOC = _real_doc
_buf3 = io.StringIO()
with contextlib.redirect_stdout(_buf3):
    _rc3 = S.main(['--check'])
check('6c  SILENT: against the real committed document the same entry point '
      'exits 0 -- the pair is what makes 6a evidence rather than an observation',
      _rc3 == 0, 'exit %s' % _rc3)

print('\n%d arm(s) failed' % len(failures))
for f in failures:
    print('  ' + f)
sys.exit(1 if failures else 0)
