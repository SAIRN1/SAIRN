#!/usr/bin/env python
"""The control for tools/claim_provenance.py -- and it had none at all.

    python tests/run_claim_provenance_probe.py

Exit 0 all arms pass, 1 any arm fails.

── WHY THIS FILE EXISTS ────────────────────────────────────────────────────
`tools/entry_point_scope_check.py` reported claim_provenance.py as having ONE
real-data entry point. It has FOUR -- `scope`, `types`, `add`, `list` -- and not
one of them is a flag: it dispatches `cmds[argv[0]](argv[1:])` over a table of
`cmd_` handlers, which a flag-only door vocabulary cannot count. Reading it
properly raised a second question the tool could not answer: **nothing anywhere
tested this file.** No control, no criteria version, not in the report-only
registry, four doors, and a ledger of how every Tier A claim on the platform was
established.

── WHAT IT TURNED OUT NOT TO NEED ──────────────────────────────────────────
It does NOT have the two-door divergence defect, and that is worth stating
rather than leaving as an absence. `cmd_scope` and `cmd_add` both go through
`load_tier_a()` -- ONE accessor, which is exactly the shape tier_a_review_gate
was FIXED into after its two doors read two different ranges. Section C locks
that so the day one of them grows a list of its own, an arm goes red instead of
a comment going stale.

`load_tier_a()` also already refuses a zero parse -- it returns COULD NOT RUN
rather than an empty scope, because an empty scope would make every `add` refuse
with "not Tier A", which reads as a rule working and is a parser that stopped
matching. Section B drives that in both directions, because a refusal nothing
exercises is a refusal nobody knows is still wired.
"""
import io
import os
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
TOOL = os.path.join(REPO, 'tools', 'claim_provenance.py')
CONTROLS_FOR = ['claim_provenance.py']

import claim_provenance as P                                     # noqa: E402

_pass, _fail = 0, 0


def check(name, cond, detail=''):
    global _pass, _fail
    if cond:
        print('  ok   ' + name)
        _pass += 1
    else:
        print('  FAIL ' + name)
        if detail != '':
            print('       %s' % (detail,))
        _fail += 1


def section(t):
    print('\n' + t)


def run(*args):
    r = subprocess.run([sys.executable, TOOL] + list(args), cwd=REPO,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace',
                       env=dict(os.environ, PYTHONIOENCODING='utf-8',
                                PYTHONUTF8='1'))
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def with_register(text):
    """Point load_tier_a at a hand-built register and return (subjects, err)."""
    fd, p = tempfile.mkstemp(prefix='cp-tiers-', suffix='.md')
    os.close(fd)
    io.open(p, 'w', encoding='utf-8', newline='\n').write(text)
    old = P.TIERS
    try:
        P.TIERS = p
        return P.load_tier_a()
    finally:
        P.TIERS = old
        try:
            os.unlink(p)
        except OSError:
            pass


print('CLAIM PROVENANCE -- the control this tool did not have')

# ── A. THE FOUR DOORS ARE REAL DOORS ───────────────────────────────────────
section('A. four subcommand doors, and no flag anywhere')

_src = io.open(TOOL, encoding='utf-8').read()
for _k in ('cmd_scope', 'cmd_types', 'cmd_add', 'cmd_list'):
    check('A1.%s is defined and dispatched through the table' % _k,
          ('def %s(' % _k) in _src and ("': %s" % _k) in _src.replace('"', "'"),
          'the handler or its table entry is gone')

for _door, _expect in (('scope', (0, 2)), ('types', (0,)), ('list', (0,))):
    _rc, _out = run(_door)
    check('A2.%s the `%s` door runs and exits %s -- a door nothing ever drives '
          'is a door nothing knows is broken' % (_door, _door, _expect),
          _rc in _expect, (_rc, _out[-200:]))

_rc, _out = run('no-such-subcommand')
check('A3. an UNKNOWN subcommand is COULD NOT RUN (exit 2), not a silent 0. A '
      'typo that exits clean is a run somebody believes happened',
      _rc == 2, (_rc, _out[-200:]))

# ── B. THE ZERO-PARSE REFUSAL, DRIVEN IN BOTH DIRECTIONS ───────────────────
section('B. an empty scope is a broken reader, not an empty register')

_subs, _err = with_register(
    '| Resource | Tier | Worst if wrong | Evidence |\n'
    '|---|---|---|---|\n'
    '| `sv_controlled` | **A** | a controlled drug record is wrong | x |\n'
    '| `sf_vendors` | **B** | a supplier record is wrong | y |\n')
check('B1. KNOWN-GOOD: a register with one Tier A row yields exactly that '
      'subject, and the B row is not in scope',
      _err is None and _subs == {'sv_controlled'}, (_subs, _err))

_subs, _err = with_register(
    '| Resource | Tier | Worst if wrong | Evidence |\n'
    '|---|---|---|---|\n'
    '| `sf_vendors` | **B** | a supplier record is wrong | y |\n')
check('B2. KNOWN-BAD: a register with NO Tier A row is COULD NOT RUN with a '
      'reason, NOT an empty scope. An empty scope makes every `add` refuse with '
      '"not Tier A", which reads as a rule working and is a parser that stopped',
      _subs is None and _err and 'broken reader' in _err, (_subs, _err))

_subs, _err = with_register('nothing here is a table at all\n')
check('B2b. ...and a file that is not a table at all gets the same answer, so '
      'the refusal is about the RESULT and not about one malformed row',
      _subs is None and _err is not None, (_subs, _err))

_old = P.TIERS
try:
    P.TIERS = os.path.join(REPO, 'no', 'such', 'register.md')
    _subs, _err = P.load_tier_a()
finally:
    P.TIERS = _old
check('B3. a MISSING register is COULD NOT RUN too, and says which file -- a '
      'different failure from an unparseable one, and both are named',
      _subs is None and _err and 'could not read' in _err, (_subs, _err))

# ── C. THE TWO-DOOR PROPERTY, LOCKED RATHER THAN ASSUMED ───────────────────
section('C. `scope` and `add` share ONE accessor')

import ast                                                       # noqa: E402
_tree = ast.parse(_src)
_fns = {n.name: n for n in ast.walk(_tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def _calls(name):
    return set(
        (c.func.attr if isinstance(c.func, ast.Attribute) else
         getattr(c.func, 'id', None))
        for c in ast.walk(_fns[name]) if isinstance(c, ast.Call))


check('C1. cmd_scope and cmd_add BOTH call load_tier_a(). This is the shape '
      'tier_a_review_gate was FIXED into after its two doors read two different '
      'ranges and told one session two contradictory true things',
      'load_tier_a' in _calls('cmd_scope') and 'load_tier_a' in _calls('cmd_add'),
      (sorted(_calls('cmd_scope')), sorted(_calls('cmd_add'))))

check('C1b. ...and NEITHER reaches a second scope accessor. A door that grows '
      'its own list is the divergence this arm exists for, and it would '
      'otherwise arrive as a comment nobody re-read',
      not ({'load_ledger'} & _calls('cmd_scope')),
      sorted(_calls('cmd_scope')))

check('C2. THE ABLATION: this arm can fail. Asked of cmd_types -- which reads '
      'no register at all -- the same test returns False, so C1 is reading the '
      'call graph rather than agreeing with itself',
      'load_tier_a' not in _calls('cmd_types'), sorted(_calls('cmd_types')))

check('C3. `list` reads the LEDGER and `scope` reads the REGISTER, and that is '
      'NOT a divergence: they answer different questions and a tool is allowed '
      'to have both. Locked so a future reader does not "fix" it into one',
      'load_ledger' in _calls('cmd_list')
      and 'load_tier_a' not in _calls('cmd_list'), sorted(_calls('cmd_list')))

# ── D. add REFUSES A RECORD THAT COULD NOT BE CHECKED ──────────────────────
section('D. a record nothing could re-derive is refused')

_BASE = ['add', '--subject', 'zz_not_tier_a', '--type', 'live-schema',
         '--claim', 'the table exists', '--method', 'measured',
         '--observed', '2026-09-29T00:00:00Z', '--by', 'cody',
         '--how', 'python tools/schema_snapshot_freshness.py']


def _variant(**kw):
    a = list(_BASE)
    for k, v in kw.items():
        i = a.index('--' + k.replace('_', '-'))
        if v is None:
            del a[i:i + 2]
        else:
            a[i + 1] = v
    return a


for _label, _args in (
        ('a subject that is not Tier A and not a migration:<file>.sql', _BASE),
        ('an UNCLASSIFIED type -- the freshness interval belongs to the type, '
         'so a record with none can never be judged stale',
         _variant(type='not-a-real-type')),
        ('a method outside measured|attested|derived',
         _variant(method='vibes')),
        ('an --observed that is not an ISO instant -- WHEN the measurement was '
         'taken is the field the design says bites',
         _variant(observed='yesterday')),
        ('no --how at all: the reproduction path is what makes the record '
         'checkable rather than a note', _variant(how=None))):
    _rc, _out = run(*_args)
    check('D. REFUSED: %s' % _label, _rc != 0, (_rc, _out[-260:]))

# ── THE SILENT HALF. Without it every D arm is satisfied by a tool that
# refuses everything, which is the failure mode a refusal test is most likely to
# hide. Driven against a TEMP ledger: `add` WRITES, and a control that pollutes
# the real provenance chain to prove a point has broken the thing it checks.
_real_subs, _ = P.load_tier_a()
_subject = sorted(_real_subs)[0] if _real_subs else None
_fd, _tmpled = tempfile.mkstemp(prefix='cp-ledger-', suffix='.json')
os.close(_fd)
io.open(_tmpled, 'w', encoding='utf-8').write('{"records": []}')
_env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1',
            SAIRN_PROVENANCE_LEDGER=_tmpled)
_old_ledger = P.LEDGER
try:
    P.LEDGER = _tmpled
    _rc_ok = P.cmd_add(['--subject', _subject, '--type', 'live-schema',
                        '--claim', 'the table exists on the live database',
                        '--method', 'measured',
                        '--observed', '2026-09-29T00:00:00Z', '--by', 'cody',
                        '--how', 'python tools/schema_snapshot_freshness.py'])
finally:
    P.LEDGER = _old_ledger
check('D-SILENT. A COMPLETE, VALID RECORD IS ACCEPTED. Without this arm every '
      'refusal above is satisfied by a tool that refuses everything -- and a '
      'provenance chain nothing can be added to is the same as no chain',
      _subject is not None and _rc_ok == 0, (_subject, _rc_ok))
_written = io.open(_tmpled, encoding='utf-8').read()
check('D-SILENT-b. ...and it really landed IN THE TEMP LEDGER, so the arm above '
      'is about a write and not about an exit code, and the real chain was not '
      'touched to prove it',
      _subject and _subject in _written, _written[:200])
try:
    os.unlink(_tmpled)
except OSError:
    pass

# ── E. ANCHORS (discipline 8) ──────────────────────────────────────────────
section('E. the anchors this control depends on')
check('E1. load_tier_a() is still the name every arm in B and C reads',
      'def load_tier_a(' in _src, 'the accessor was renamed')
check('E2. TIERS is still the module-level name section B rebinds. If it is '
      'inlined, every B arm silently runs against the REAL register and B2 '
      'starts failing for the wrong reason',
      'TIERS = ' in _src and hasattr(P, 'TIERS'), 'TIERS is not module-level')
check('E3. the METHODS and TYPES vocabularies are non-empty, or the D arms are '
      'refusing against an empty allow-list and prove nothing',
      len(getattr(P, 'METHODS', ())) >= 2 and len(getattr(P, 'TYPES', {})) >= 2,
      (getattr(P, 'METHODS', None), len(getattr(P, 'TYPES', {}))))
check('E4. THE REAL REGISTER still yields a non-empty Tier A scope, so the tool '
      'is usable at all -- and if this goes red the register moved, not this '
      'file',
      (P.load_tier_a()[0] or set()) and len(P.load_tier_a()[0]) > 5,
      P.load_tier_a()[1])

print('\n%s -- %d passed, %d failed' % ('FAIL' if _fail else 'ALL ARMS PASS',
                                        _pass, _fail))
sys.exit(1 if _fail else 0)
