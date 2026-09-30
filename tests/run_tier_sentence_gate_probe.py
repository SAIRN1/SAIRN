r"""tests/run_tier_sentence_gate_probe.py -- control pair for
tools/tier_sentence_gate.py.

    python tests/run_tier_sentence_gate_probe.py

CONTROLS_FOR = ['tools/tier_sentence_gate.py']
LIVE_PROBE_CLASS = 'FIXTURE'

THE CENTRAL ARM IS NOT A FIXTURE. It drives the gate against
`docs/CRITICALITY-TIERS.md` AS IT STOOD BEFORE `c97acbf9` -- the commit that
re-tiered `mech_checks` B -> A -- and requires it to report exactly that row, then
drives it against HEAD and requires 0. A check validated only on strings somebody
wrote for it has not been shown to catch the thing it exists for.

THE KNOWN-BAD CONTROLS, and every one must come back the way it says:

  a row asserting the clause over a resource with `amount`   -> MONEY-FIELD
  the same row QUOTING the clause beside a correction verb   -> QUOTED, not a finding
  a resource with no money-named field                       -> CLEAR
  a resource with no extractable write shape                 -> COULD-NOT-TELL
  a row that does not carry the clause at all                 -> not examined
  `quantity` and `rate`                                       -> NOT money
  the real register at HEAD                                   -> MONEY-FIELD 0
  the real register before c97acbf9                           -> MONEY-FIELD mech_checks
"""
import io
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
TOOL = os.path.join(REPO, 'tools', 'tier_sentence_gate.py')
sys.path.insert(0, os.path.join(REPO, 'tools'))
from checker_kit import EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN  # noqa: E402

if not os.path.isfile(TOOL):
    print('COULD NOT RUN: tools/tier_sentence_gate.py is not on disk. This control '
          'tested nothing, which is a third state and not a pass.')
    sys.exit(EXIT_COULD_NOT_RUN)

import tier_sentence_gate as G   # noqa: E402

NL = chr(10)
passed = failed = 0


def ok(cond, label, detail=''):
    global passed, failed
    if cond:
        passed += 1
        print('  ok   %s' % label)
    else:
        failed += 1
        print('  FAIL %s' % label)
        if detail:
            print('       %s' % str(detail)[:500])


def row(res, ev, tier='B'):
    return '| `%s` | **%s** | **B** | consequence | confidentiality | %s |' % (res, tier, ev)


def state(res, text):
    got = [r for r in (G.scan(text) or []) if r['resource'] == res]
    return (got[0] if got else None)


def git(*a):
    p = subprocess.run(['git', '-C', REPO] + list(a), capture_output=True,
                       text=True, encoding='utf-8', errors='replace', timeout=120)
    return p.returncode, p.stdout


print('CONTROL PAIR -- tools/tier_sentence_gate.py' + NL)
print('THE REAL HISTORICAL DEFECT -- not a fixture')

# ── THE ARM THAT MATTERS. The register before the mech_checks re-tier. ──────
rc, before = git('show', 'c97acbf9~1:docs/CRITICALITY-TIERS.md')
if rc != 0 or not before.strip():
    ok(False, 'the pre-c97acbf9 register could be read out of git -- WITHOUT it '
              'the central arm did not run, which is a could-not-tell and is '
              'reported as a failure rather than skipped', rc)
else:
    rows = G.scan(before) or []
    bad = [r for r in rows if r['state'] == 'MONEY-FIELD']
    ok(len(rows) > 50,
       'the pre-fix register parses and asserts the clause on %d rows, so the arm '
       'below is measured against a real population' % len(rows), len(rows))
    ok([r['resource'] for r in bad] == ['mech_checks'],
       'THE ARM THAT MATTERS: against the register AS IT STOOD BEFORE c97acbf9 the '
       'gate reports EXACTLY ONE row -- `mech_checks` -- and reports it for the '
       'right reason',
       [(r['resource'], r.get('fields')) for r in bad])
    if bad:
        ok(set(['amount', 'payee']) <= set(bad[0].get('fields') or []),
           '...and it names `amount` and `payee`, the two fields saveCheck() '
           'actually persists, rather than merely naming the row',
           bad[0].get('fields'))

# ── AND SILENT ONCE CORRECTED. A check that still fires after the fix is noise. ──
now = io.open(os.path.join(REPO, 'docs', 'CRITICALITY-TIERS.md'),
              encoding='utf-8', errors='replace').read()
rows_now = G.scan(now) or []
bad_now = [r for r in rows_now if r['state'] == 'MONEY-FIELD']
ok(bad_now == [],
   'and against HEAD it reports NOTHING -- the row it fired on was corrected, so '
   'the check goes quiet instead of becoming permanent noise',
   [(r['resource'], r.get('fields')) for r in bad_now])
# ── MY FIRST VERSION OF THIS ARM WAS WRONG, NOT THE TOOL, and the corrected
# form is the STRONGER assertion. It expected `mech_checks` to vanish from the
# asserting population once the row was fixed. It does not: the corrected cell
# QUOTES the clause in order to say it was found false, so the gate still sees
# the row and classifies it QUOTED. Asserting QUOTED rather than absence proves
# the quotation exclusion works on the REAL corrected row and not only on a
# fixture -- which is what the exclusion is for.
mc = [r for r in rows_now if r['resource'] == 'mech_checks']
ok(len(mc) == 1 and mc[0]['state'] == 'QUOTED',
   '...and `mech_checks` is still SEEN at HEAD and classified QUOTED, because its '
   'corrected cell quotes the clause to say it was false -- the exclusion working '
   'on the real row, not on a fixture', mc)

# ── THE FIXTURES, both directions ─────────────────────────────────────────
print(NL + 'FIXTURES -- each shape in both directions')
s = state('mech_checks', row('mech_checks', 'neither money nor a regulated record'))
ok(s and s['state'] == 'MONEY-FIELD', 'a synthetic asserting row is MONEY-FIELD', s)

s = state('mech_checks', row('mech_checks',
          'RE-TIERED B -> A. The B sentence read &ldquo;neither money nor a '
          'regulated record&rdquo; and was false about it.'))
ok(s and s['state'] == 'QUOTED',
   'KNOWN-BAD THE OTHER WAY: the same row QUOTING the clause beside a correction '
   'verb is QUOTED -- a row saying the sentence was wrong is doing the opposite of '
   'asserting it', s)

s = state('leg_guestbook', row('leg_guestbook', 'neither money nor a regulated record'))
ok(s and s['state'] == 'CLEAR',
   'KNOWN-BAD THE OTHER WAY: `leg_guestbook` has no money-named field and comes '
   'back CLEAR, so the gate is not reporting every row that carries the sentence', s)

s = state('zz_no_such_resource',
          row('zz_no_such_resource', 'neither money nor a regulated record'))
ok(s and s['state'] == 'COULD-NOT-TELL',
   'a resource with NO extractable write shape is COULD-NOT-TELL and never CLEAR '
   '-- fail-open here would be PR 1.11 inside the gate meant to enforce the '
   'register', s)

ok(G.scan(row('mech_checks', 'Money. Confidentiality individually read.')) == [],
   'a row that does not carry the clause is not examined at all -- this gate is '
   'about the SENTENCE, not about the resource')

ok(not G.MONEY_RE.match('quantity') and not G.MONEY_RE.match('rate')
   and bool(G.MONEY_RE.match('amount')),
   'the money list excludes `quantity` and `rate` -- `leg_keepsakeorders` carries '
   'quantity with no price and `sb_hire` carries a POSTED RANGE, both correctly B '
   '-- and still includes `amount`, so the narrowing did not empty it')

# ── FAIL CLOSED ───────────────────────────────────────────────────────────
print(NL + 'FAIL CLOSED')
ok(G.scan('# a document with no resource rows at all' + NL) == [],
   'a document with no rows yields no findings -- and the CLI turns that into '
   'exit 2 rather than a clean line, asserted below')


def run(*args):
    p = subprocess.run([sys.executable, TOOL] + list(args), cwd=REPO,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace', timeout=1200,
                       env=dict(os.environ, PYTHONIOENCODING='utf-8'))
    return p.returncode, (p.stdout or '') + (p.stderr or '')


rc, out = run('--resource', 'zz_definitely_absent')
ok(rc == EXIT_COULD_NOT_RUN,
   'an absent --resource is exit 2, not 0 (got %d) -- "no row or does not assert '
   'the clause" is not a pass' % rc, out[-300:])

rc, out = run('--selftest')
ok(rc == EXIT_CLEAN and 'ALL ARMS PASS' in out,
   '--selftest exits 0 and every fixture arm passes (got %d)' % rc, out[-400:])

# ── THE FEASIBILITY ANSWER IS PRINTED, AND IT IS A MEASUREMENT ────────────
print(NL + 'THE FEASIBILITY ANSWER -- reported, not asserted')
rc, out = run()
print('  --   exit %d' % rc)
ok(rc in (EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN),
   'it exits one of the three defined codes', out[-300:])
ok('CAN THIS BLOCK? NO' in out,
   'and it answers the blocking question in its own output rather than leaving it '
   'to a reader', out[-1200:])
ok('NOT MET' in out or 'MET --' in out,
   'and states whether the coverage threshold is met', out[-900:])
ok('COULD-NOT-TELL' in out,
   'and names the unresolved resources rather than folding them into CLEAR',
   out[-900:])
ok('the regulated limb and the "no PII" clause are NOT screened here'
   in out.replace(NL, ' ').replace('  ', ' ')
   or 'are NOT screened here' in out,
   'and says what it does NOT screen beside the zero, so MONEY-FIELD 0 cannot be '
   'read as "the sentence is true everywhere"', out[-1200:])

print(NL + '%d passed, %d failed' % (passed, failed))
sys.exit(EXIT_FINDING if failed else EXIT_CLEAN)
