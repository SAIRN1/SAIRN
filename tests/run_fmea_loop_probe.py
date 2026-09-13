"""Does the FMEA loop wired into `defect_register.py --add` actually answer?

    python tests/run_fmea_loop_probe.py

Item 26, the FMEA-prediction branch. The loop prints one of five answers about
each code file in a newly registered defect, and this drives all five plus the
fail-closed path. Nothing here touches the real register: `fmea_loop()` is
called directly with synthetic records, so the probe cannot leave a row behind.

── WHY THE FAIL-CLOSED ARM IS THE ONE THAT MATTERS ────────────────────────
The tempting shape for the wiring was `except ImportError: pass`, which is a
check that silently does not run -- PR 1.11, and the defect that disabled nine
of ten push-gate checks. Arm 6 removes the checker from the import path and
asserts the loop SAYS SO rather than printing nothing.

── AND ARM 0 IS THE SABOTAGE-APPLIED PROOF ────────────────────────────────
23 of 39 negative controls on this platform never verify their own sabotage
landed, so every arm below that mutates something asserts the mutation is real
before asserting the consequence.
"""
import contextlib
import io as _io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'tools'))
os.chdir(REPO)

import defect_register as dr          # noqa: E402
import fmea_prediction_check as fp    # noqa: E402

PASS = []
FAIL = []


def check(name, cond, detail=''):
    (PASS if cond else FAIL).append(name)
    print(('  ok   ' if cond else '  FAIL ') + name + (('\n        ' + detail) if (detail and not cond) else ''))


def loop_output(rec):
    buf = _io.StringIO()
    with contextlib.redirect_stdout(buf):
        dr.fmea_loop(rec)
    return buf.getvalue()


def rec(files, date='2026-09-13', rules=None):
    return {'files': files, 'date': date, 'rules': rules or ['1.1']}


# ── 0. the fixtures are real before anything is concluded from them ────────
print('--- 0. control: the drafts the later arms rely on actually exist ---')
drafts = fp.load_drafts()
targets = [d.get('target') for d in drafts]
check('there is at least one draft on disk to reason about', len(drafts) > 0,
      'docs/fmea/ is empty, so arms 3-5 would pass vacuously')
dated = [d for d in drafts if d.get('_asof')]
check('at least one draft carries a date', len(dated) > 0,
      'without _asof every draft is "newer than the defect" and arm 4 is vacuous')

# ── 1. a file with no draft is NAMED, not silently skipped ─────────────────
print('\n--- 1. NO DRAFT ---')
out = loop_output(rec(['api/some_file_with_no_draft.js']))
check('a code file with no draft is reported as NO DRAFT', 'NO DRAFT' in out, out)
check('and the message says how to make the next one scoreable',
      'fmea_draft.py' in out, out)

# ── 2. a commit of only worklogs and docs is not scored at all ─────────────
print('\n--- 2. not a code target ---')
out = loop_output(rec(['SAIRN-ACTIVE-WORK-hank.md', 'docs/SAIRN-OPEN-WORK-INDEX.md']))
check('a worklog-only commit is excluded rather than counted as a miss',
      'no code target' in out, out)
check('and it does NOT print NO DRAFT for a document',
      'NO DRAFT' not in out, out)

# ── 3/4. a real drafted target, on both sides of the draft date ────────────
print('\n--- 3. a drafted target whose draft PREDATES the defect ---')
target = None
for d in dated:
    if d.get('target') and not fp.NOT_A_CODE_TARGET.search(d['target']):
        target = d
        break
if target is None:
    check('a code-file draft with a date exists to test against', False,
          'every dated draft is a doc/worklog; arms 3-5 cannot run')
else:
    later = '2099-01-01'
    out = loop_output(rec([target['target']], date=later, rules=['9.9']))
    check('a defect AFTER the draft, citing a rule the draft does not, is a MISS',
          'MISSED' in out, out)
    check('and the miss names the file', target['target'] in out, out)

    print('\n--- 4. the same target, defect BEFORE the draft ---')
    out = loop_output(rec([target['target']], date='2000-01-01', rules=['9.9']))
    check('a defect the draft postdates is UNSCOREABLE, not a miss',
          'DRAFT NEWER' in out and 'MISSED' not in out, out)

    print('\n--- 5. a citation the draft DOES carry is a PREDICTED ---')
    cited = []
    for r in target.get('risks', []):
        c = r.get('cite', '')
        if 'SAIRN-PROCESS-RULES' in c:
            cited.append(c.rsplit(' ', 1)[-1])
    if not cited:
        check('the chosen draft cites at least one standing rule', False,
              'no risk in %s cites a rule, so PREDICTED cannot be reached'
              % target['_file'])
    else:
        out = loop_output(rec([target['target']], date=later, rules=[cited[0]]))
        check('a defect citing a rule the draft named comes back PREDICTED',
              'PREDICTED' in out, out)
        check('and it names which rule and which draft file',
              cited[0] in out and target['_file'] in out, out)

# ── 6. FAIL CLOSED when the checker is absent ──────────────────────────────
print('\n--- 6. the checker missing must SAY SO, never print nothing ---')
saved_mod = sys.modules.pop('fmea_prediction_check', None)
saved_path = list(sys.path)
sys.path[:] = [p for p in sys.path if 'tools' not in p.replace('\\', '/').split('/')]
import builtins                                                  # noqa: E402
real_import = builtins.__import__


def blocked_import(name, *a, **k):
    if name == 'fmea_prediction_check':
        raise ImportError('blocked by the probe')
    return real_import(name, *a, **k)


builtins.__import__ = blocked_import
try:
    # CONTROL: prove the sabotage applied before concluding anything from it.
    applied = False
    try:
        real_import('fmea_prediction_check')
    except ImportError:
        applied = True
    check('CONTROL APPLIED: the import really is blocked', applied,
          'the module still imports, so arm 6 proves nothing')
    out = loop_output(rec(['api/anything.js']))
    check('an absent checker reports COULD NOT RUN', 'COULD NOT RUN' in out, out)
    check('and refuses to be read as a "no draft" answer',
          'must not be read as one' in out, out)
finally:
    builtins.__import__ = real_import
    sys.path[:] = saved_path
    if saved_mod is not None:
        sys.modules['fmea_prediction_check'] = saved_mod

print('\n%d passed, %d failed' % (len(PASS), len(FAIL)))
sys.exit(1 if FAIL else 0)
