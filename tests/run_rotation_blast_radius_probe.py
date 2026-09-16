"""Are rotation and scope kept apart -- and does either column actually discriminate?

    python tests/run_rotation_blast_radius_probe.py

Item 61. The documented failure is treating one control as the other, so the
arms here come in two kinds:

  THE SEPARATION ARMS. No function combines the columns, the intersection is a
  SET and not an average, and an identity can be BROAD-and-scheduled or
  BOUNDED-and-unrotated without either fact contaminating the other.

  THE DISCRIMINATION ARMS. A classifier that answers BROAD for everything, or
  PROCEDURE ONLY for everything, would pass every separation arm above while
  measuring nothing. Each classifier is driven in both directions on synthetic
  input, and then asserted to produce MORE THAN ONE ANSWER on the real register.

The criteria were revised once, .1 -> .2, after the first real run missed
`postgres` ("Owns all 380-odd objects in public"). Section 3 holds that
revision in both directions, and section 6 holds the rule that made it
allowable: the change moved a row from BOUNDED to BROAD, against this platform
rather than for it.
"""
import contextlib
import io
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import rotation_blast_radius as R                                # noqa: E402

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        fails.append(name)


def run(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = R.main(argv)
    return rc, buf.getvalue()


print('\n1. THE TOOL\'S OWN BLIND LOCK RUNS IN THE SUITE')
lines, bad = R.fixtures()
check('every fixture arm passes', bad == 0,
      [l for l in lines if l.startswith('  FAIL')])
check('the lock is not empty', len(lines) >= 15, len(lines))
rc, out = run(['--fixtures'])
check('--fixtures reads no register', 'no register read' in out and rc == 0)

print('\n2. THE ROTATION COLUMN DISCRIMINATES')
check('a recorded date is ATTESTED',
      R.rotation_state({'last_rotated': '2026-09-01', 'rotation': 'x'}) == 'ATTESTED')
check('a cadence is SCHEDULED',
      R.rotation_state({'last_rotated': '', 'rotation': 'rotated quarterly'}) == 'SCHEDULED')
check('CONTROL: a procedure with no cadence is PROCEDURE ONLY. "Stripe '
      'dashboard" is HOW, never WHEN',
      R.rotation_state({'last_rotated': '', 'rotation': 'Stripe dashboard'})
      == 'PROCEDURE ONLY')
check('CONTROL: nothing recorded is its own state, not folded into the others',
      R.rotation_state({'last_rotated': '', 'rotation': ''}) == 'NOTHING RECORDED')
check('CONTROL: somebody else\'s to rotate is NOT OURS -- neither counted '
      'against this platform nor counted clean',
      R.rotation_state({'last_rotated': '', 'rotation': 'not ours'}) == 'NOT OURS')
check('CONTROL: a date beats every other signal, because a date is evidence and '
      'the rest is intent',
      R.rotation_state({'last_rotated': '2026-01-01', 'rotation': 'not ours'})
      == 'ATTESTED')
check('CONTROL: the classifier gives more than one answer -- one that always '
      'said PROCEDURE ONLY would pass every arm above',
      len({R.rotation_state({'last_rotated': d, 'rotation': r})
           for d, r in (('2026-01-01', ''), ('', 'weekly'), ('', 'by hand'),
                        ('', ''), ('', 'not ours'))}) == 5)

print('\n3. THE SCOPE COLUMN DISCRIMINATES, AND THE .1 -> .2 MISS IS HELD')
check('FULL is broad', R.scope_state({'scope': 'FULL read/write on every table'}) == 'BROAD')
check('BYPASSRLS is broad -- read-only is not narrow when it is read-everything',
      R.scope_state({'scope': 'SELECT on every table plus BYPASSRLS'}) == 'BROAD')
check('THE MISS: owning every object in the schema is broad',
      R.scope_state({'scope': 'Owns all 380-odd objects in public'}) == 'BROAD')
check('CONTROL: a narrow scope is BOUNDED',
      R.scope_state({'scope': 'read one column of one table'}) == 'BOUNDED')
check('CONTROL: the .2 revision did not widen BROAD to everything -- owning ONE '
      'thing is still bounded',
      R.scope_state({'scope': 'owns the single table it writes'}) == 'BOUNDED')
check('CONTROL: the declared boundary case is BOUNDED and is named in the '
      'header, not silently decided',
      R.scope_state({'scope': 'live charge and refund authority on the account'})
      == 'BOUNDED')
check('CONTROL: an empty scope is BOUNDED rather than crashing, and that is a '
      'known weak spot -- an unstated scope is not a narrow one',
      R.scope_state({}) == 'BOUNDED')

print('\n4. A COMPROMISE TRIGGER IS NOT A SCHEDULE')
check('a compromise trigger is detected',
      R.has_compromise_trigger({'rotation': 'by hand. If leaked, revoke immediately'}))
check('CONTROL: a scheduled rotation is NOT a compromise trigger. They answer '
      'different questions and conflating them is the substitution this tool '
      'exists to refuse',
      not R.has_compromise_trigger({'rotation': 'rotated monthly, automated'}))
check('CONTROL: an identity with neither has neither',
      not R.has_compromise_trigger({'rotation': 'Stripe dashboard', 'scope': 'x'}))

print('\n5. THE TWO COLUMNS ARE NEVER COMBINED')
check('no function averages or scores them, by name',
      not any(n in dir(R) for n in ('posture_score', 'combined', 'overall',
                                    'security_score', 'risk_score')), dir(R))
SYN = [
    {'id': 'broad-scheduled', 'scope': 'FULL access',
     'rotation': 'rotated weekly, automated', 'last_rotated': ''},
    {'id': 'bounded-unrotated', 'scope': 'one row',
     'rotation': 'by hand', 'last_rotated': ''},
    {'id': 'broad-unrotated', 'scope': 'FULL access',
     'rotation': 'by hand', 'last_rotated': ''},
    {'id': 'bounded-scheduled', 'scope': 'one row',
     'rotation': 'rotated daily', 'last_rotated': ''},
]
rows = R.analyse(SYN)
by = {r['id']: r for r in rows}
check('BROAD-and-scheduled is possible -- rotation does not narrow a scope',
      by['broad-scheduled']['scope'] == 'BROAD'
      and by['broad-scheduled']['rotation'] == 'SCHEDULED', by['broad-scheduled'])
check('BOUNDED-and-unrotated is possible -- a narrow scope does not rotate '
      'anything', by['bounded-unrotated']['scope'] == 'BOUNDED'
      and by['bounded-unrotated']['rotation'] == 'PROCEDURE ONLY')
both = R.intersection(rows)
check('the intersection contains ONLY the one that is both',
      [r['id'] for r in both] == ['broad-unrotated'], [r['id'] for r in both])
check('CONTROL: it is the INTERSECTION and not the UNION. A union would be '
      '"either control is weak", which is three of these four and says nothing '
      '-- and a union dressed as an overlap is an average by another name',
      len(both) < len([r for r in rows if r['scope'] == 'BROAD'
                       or r['rotation'] in R.UNROTATED]),
      (len(both), [r['id'] for r in rows]))
check('CONTROL: the RUN uses the same function, so the tool and this probe '
      'cannot disagree about what the overlap is',
      R.intersection(R.analyse(SYN)) == both)
check('CONTROL: a register where nothing is both yields an EMPTY overlap, not '
      'a defaulted one', R.intersection([
          {'id': 'a', 'scope': 'BOUNDED', 'rotation': 'PROCEDURE ONLY'},
          {'id': 'b', 'scope': 'BROAD', 'rotation': 'ATTESTED'}]) == [])

print('\n6. THE REAL REGISTER')
idents = R.load_identities()
check('the register imports', idents is not None and len(idents) > 5,
      idents and len(idents))
class _Stub(object):
    """A register module that imports fine and carries nothing. The realistic
    failure is not an ImportError -- it is a rename or a refactor that leaves
    IDENTITIES gone while the module still loads."""


_real_mod = sys.modules.get('nhi_register')
try:
    sys.modules['nhi_register'] = _Stub()
    check('CONTROL: a register that loads but carries NO identities is None, '
          'not [] -- an empty list would report a platform with no credentials '
          'on it, which is the flattering wrong answer',
          R.load_identities() is None, R.load_identities())
    rc_none, out_none = run([])
    check('...and the RUN says COULD NOT READ and exits 2 rather than printing '
          '"0 of 0" as if that were clean',
          rc_none == 2 and 'COULD NOT READ' in out_none,
          (rc_none, out_none[:200]))
finally:
    if _real_mod is not None:
        sys.modules['nhi_register'] = _real_mod
    else:
        sys.modules.pop('nhi_register', None)
check('CONTROL: and the real register still loads afterwards, so the stub did '
      'not leak into the rest of this run', R.load_identities() is not None)
real = R.analyse(idents)
check('BOTH columns produce more than one answer on the real data -- a column '
      'with one value everywhere has measured nothing',
      len({r['scope'] for r in real}) > 1
      and len({r['rotation'] for r in real}) > 1,
      (sorted({r['scope'] for r in real}), sorted({r['rotation'] for r in real})))
check('CONTROL: neither column is unanimous in the BAD direction either, which '
      'would mean the criteria were set to catch everything',
      any(r['scope'] == 'BOUNDED' for r in real)
      and any(r['rotation'] != 'PROCEDURE ONLY' for r in real))
by_id = {r['id']: r for r in real}
check('the .2 criteria classify `postgres` as BROAD -- the row .1 missed. The '
      'revision moved a row AGAINST this platform, which is what distinguishes '
      'a correction from tuning to flatter the corpus',
      by_id.get('postgres', {}).get('scope') == 'BROAD', by_id.get('postgres'))
rev = R.CRITERIA_VERSION.rsplit('.', 1)[-1]
check('CRITERIA_VERSION records that at least one revision happened -- the '
      'suffix is past .1, and it is NOT pinned to a specific number here '
      'because pinning it makes the next honest revision fail this arm',
      rev.isdigit() and int(rev) >= 2, R.CRITERIA_VERSION)
src_rbr = io.open(os.path.join(REPO, 'tools', 'rotation_blast_radius.py'),
                  encoding='utf-8').read()
check('...and every revision is EXPLAINED in the source, with the direction it '
      'moved the number. A version bump with no reason is a version bump',
      src_rbr.count('-> .') >= 2 or src_rbr.count('.1 -> .2') >= 1,
      [l.strip()[:70] for l in src_rbr.splitlines() if '-> .' in l][:4])

print('\n7. THE RUN REFUSES TO REPORT A POSTURE')
rc, out = run([])
check('both numbers are printed, separately',
      'ROTATION  ' in out and 'SCOPE     ' in out, out[:600])
check('the run says in words that neither substitutes for the other',
      'NOT A SUBSTITUTE' in out, out[-900:])
check('UNATTESTED is not reported as "never rotated" -- the register says so '
      'about itself and this inherits it',
      'is not "never rotated"' in out.lower()
      or 'UNATTESTED IS NOT' in out, out[-700:])
check('a finding does not exit 0', rc != 0, rc)
check('the output is ASCII-safe for a cp1252 console',
      out == out.encode('ascii', 'replace').decode('ascii'),
      [l for l in out.splitlines()
       if l != l.encode('ascii', 'replace').decode('ascii')][:2])

print()
if fails:
    print('%d ARM(S) FAILED:' % len(fails))
    for f in fails:
        print('  - ' + f)
else:
    print('ALL ARMS PASS')
sys.exit(1 if fails else 0)
