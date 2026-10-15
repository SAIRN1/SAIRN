#!/usr/bin/env python
# OWNER: cc
# written 2026-10-14, batch b12, queue item 2
"""Fail when a Markdown runbook's copy of a rule diverges from its code constant.

    python tools/runbook_constant_agreement.py
    python tools/runbook_constant_agreement.py --selftest
    python tools/runbook_constant_agreement.py --ablation

Exit 0 clean, 1 divergence, 2 COULD NOT RUN.

── THE SHAPE THIS EXISTS FOR, PAID FOR TWICE IN ONE DAY ────────────────────
A rule lives in one place in code and in two or three places in prose, and
nothing compares them. Both halves of cc's b11 were this:

  * `OVERRIDE_HINT` in the push gate was wrong for a month UNDERNEATH a design
    comment asserting it had been fixed. Fixing it did not fix the output,
    because a second hardcoded copy in `register_feed_gate.py` was what
    actually printed.
  * Step 4a -- the precondition on the ONLY irreversible step of the
    session-key rotation -- was missing from all three operator-facing copies
    while living in a code comment. `secrets_inventory._IRREVERSIBLE` now
    locks the code constant on every invocation. **NOTHING WATCHES THE
    MARKDOWN**, which is the half this tool closes.

A prose copy that omits the precondition is worse than no prose copy: it reads
as complete. And the prose copy is the one an operator actually follows at
3am.

── WHAT IS COMPARED, AND WHAT IS DELIBERATELY NOT ──────────────────────────
NOT the wording. Asserting the code constant's literal sentence against a
runbook would fail on every sane paraphrase, and a check that fires on good
edits gets deleted. What is compared is the set of things the operator must be
able to ACT on -- the census file to run, the threshold, the citation, the
fact that the loss is silent -- and that set is IMPORTED from
`secrets_inventory._IRREVERSIBLE` rather than restated here.

THAT IMPORT IS THE WHOLE POINT. A second list of needles in this file would be
a third copy of the rule, inside the tool built to stop third copies. When
somebody adds a sixth needle to the lock, this check starts requiring it in
the prose on the next run, with no edit here.

── WHY IT IS REPORT-ONLY AND NOT A PUSH GATE ───────────────────────────────
`docs/NHI-REGISTER.md:69` DIVERGES RIGHT NOW. It is fourth's file, the text is
routed in `docs/2026-10-14-cc-b11-routed.md`, and fourth has not landed it
yet. Wired blocking today, this would deny every push by every session on the
platform for one agent's open routed item -- which is precisely how a gate
gets switched off. So it is in `report_only_checks.REGISTRY`: it runs on every
push automatically, it says what it found, and it cannot deny. Promotion to
blocking is a separate decision once the register copy lands, on the same path
as push-gate checks 5 and 7.

Run by hand it exits 1 on divergence, so a person can chain it. That asymmetry
is the difference between a report and a gate.

── FAILS CLOSED WHEN ITS SOURCE IS ABSENT ──────────────────────────────────
If `secrets_inventory` will not import, this exits 2 COULD NOT RUN and names
the module. It does NOT skip: a check wrapped in `if import_worked:` reports a
pass it never performed, and nothing downstream can tell that from a real one.
"""
import argparse
import io
import os
import re
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)

try:
    from checker_kit import EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN
except Exception:                                                # noqa: BLE001
    EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN = 0, 1, 2

CRITERIA_VERSION = '2026-10-14.1'
NL = chr(10)

_IMPORT_WHY = ''
try:
    import secrets_inventory as SI
except Exception as _exc:                                        # noqa: BLE001
    SI = None
    _IMPORT_WHY = 'tools/secrets_inventory.py will not import: %s' % _exc


# ── the registry ───────────────────────────────────────────────────────────
#
# One entry per RULE, not per file. `copies` is every operator-facing Markdown
# page that restates it. `anchor` locates the passage inside a large document
# so a needle found 2,000 lines away in an unrelated section cannot pass the
# check -- the exact false pass a whole-file `in` test would give.
#
# `routed_to` is set only where the divergence is a KNOWN OPEN ITEM owned by
# another session. It changes nothing about the verdict -- the row still FAILS
# -- it just names who has it, so a reader is not sent to re-diagnose
# something already routed.
REGISTRY = [
    {
        'rule': 'SD_AUTH_SECRET_PREVIOUS rotation, step 4a '
                '(the precondition on the only irreversible step)',
        'needles': lambda: _needles_from_irreversible(
            'SD_AUTH_SECRET_PREVIOUS'),
        'code_at': 'tools/secrets_inventory.py '
                   '_IRREVERSIBLE[\'SD_AUTH_SECRET_PREVIOUS\']',
        'copies': [
            {'path': 'docs/SECRETS-INVENTORY.md',
             'anchor': 'SD_AUTH_SECRET_PREVIOUS',
             'note': 'generated from the same constant, so a failure here '
                     'means the page was not regenerated'},
            {'path': 'docs/NHI-REGISTER.md',
             'anchor': 'REVOKE: set a new SD_AUTH_SECRET',
             'routed_to': 'fourth -- exact text in '
                          'docs/2026-10-14-cc-b11-routed.md',
             'note': 'independent prose, not generated from anything. This '
                     'is the copy an operator follows.'},
        ],
    },
]

# How much of the document around the anchor counts as "the passage". Lines
# rather than characters, because the register's rows are one very long line
# each and a character window would cut one in half.
WINDOW_LINES = 40


def _needles_from_irreversible(var):
    """[(label, needle)] -- IMPORTED from the lock, never restated here.

    Raises on a missing key rather than returning an empty list: no needles
    would make every copy pass, which is the silent-success direction.
    """
    entry = SI._IRREVERSIBLE.get(var)
    if not entry:
        raise KeyError(
            'secrets_inventory._IRREVERSIBLE has no entry for %r, so there is '
            'nothing to compare the runbooks against. Reported as COULD NOT '
            'RUN rather than as a clean pass -- an empty needle list makes '
            'every prose copy pass.' % var)
    return list(entry)


# ── the comparison ─────────────────────────────────────────────────────────

def _norm(text):
    """Whitespace-collapsed, lowercased. Markdown wraps; code constants do not."""
    return ' '.join(text.split()).lower()


def passage(path, anchor):
    """(text, why). The window around `anchor` in `path`, or ('', why)."""
    full = os.path.join(REPO, path)
    if not os.path.isfile(full):
        return '', 'the file does not exist at %s' % path
    try:
        with io.open(full, encoding='utf-8', errors='replace') as fh:
            lines = fh.read().split(NL)
    except OSError as exc:
        return '', 'unreadable: %s' % str(exc)[:90]
    low = [_norm(l) for l in lines]
    a = _norm(anchor)
    for i, l in enumerate(low):
        if a in l:
            lo = max(0, i - 2)
            hi = min(len(lines), i + WINDOW_LINES)
            return _norm(NL.join(lines[lo:hi])), ''
    return '', ('the anchor %r is not in the file at all. That is a finding, '
                'not a skip: an anchor that no longer matches is how a check '
                'stops testing anything without saying so.' % anchor[:60])


def check_entry(entry):
    """[finding dicts] for one rule across all its prose copies."""
    out = []
    needles = entry['needles']()
    for copy in entry['copies']:
        text, why = passage(copy['path'], copy['anchor'])
        if not text:
            out.append({'rule': entry['rule'], 'path': copy['path'],
                        'verdict': 'CANNOT COMPARE', 'detail': why,
                        'missing': [], 'copy': copy})
            continue
        missing = [(label, needle) for label, needle in needles
                   if _norm(needle) not in text]
        out.append({'rule': entry['rule'], 'path': copy['path'],
                    'verdict': 'DIVERGES' if missing else 'AGREES',
                    'detail': '', 'missing': missing, 'copy': copy})
    return out


def run(registry=None):
    """(exit_code, lines). Never raises on a registry problem -- reports it."""
    registry = registry if registry is not None else REGISTRY
    out = ['runbook_constant_agreement  (criteria %s)' % CRITERIA_VERSION,
           '%d rule(s), %d prose copy/copies.'
           % (len(registry), sum(len(e['copies']) for e in registry)), '']
    rows = []
    for entry in registry:
        try:
            rows += check_entry(entry)
        except Exception as exc:                                 # noqa: BLE001
            out.append('COULD NOT RUN -- %r: %s' % (entry['rule'][:50], exc))
            return EXIT_COULD_NOT_RUN, out
    bad = [r for r in rows if r['verdict'] != 'AGREES']
    for r in rows:
        out.append('  %-14s %-28s %s' % (r['verdict'], r['path'],
                                         r['rule'][:60]))
        if r['detail']:
            out.append('      %s' % r['detail'])
        for label, needle in r['missing']:
            out.append('      MISSING: %s' % label)
            out.append('        the operator cannot act on it without: %r'
                       % needle)
        rt = (r['copy'] or {}).get('routed_to')
        if r['verdict'] != 'AGREES' and rt:
            out.append('      ALREADY ROUTED, and this row still FAILS: %s'
                       % rt)
        if r['verdict'] != 'AGREES' and (r['copy'] or {}).get('note'):
            out.append('      %s' % r['copy']['note'])
    out.append('')
    if bad:
        out.append('  %d of %d prose copy/copies DIVERGE from the code '
                   'constant.' % (len(bad), len(rows)))
        out.append('  The code constant is authoritative: %s'
                   % registry[0]['code_at'])
        out.append('  A prose runbook that omits the precondition on an '
                   'irreversible step reads as COMPLETE, which is why this is '
                   'a finding and not a style note.')
        return EXIT_FINDING, out
    out.append('  every prose copy carries everything the code constant '
               'requires. The needles are imported from the lock, so adding '
               'one there starts requiring it here with no edit.')
    return EXIT_CLEAN, out


# ── failing-first arms ─────────────────────────────────────────────────────
#
# Each arm builds a fixture tree where the thing it names IS wrong, and the
# check must report it. An arm that only sees the real repo tells you about
# today's tree, not about the check.

_ARMS = []


def arm(name, defect):
    def deco(fn):
        _ARMS.append((name, defect, fn))
        return fn
    return deco


def _fixture(tmp, body, anchor='ANCHOR LINE', needles=None):
    """A one-rule registry pointed at a throwaway Markdown file."""
    rel = 'fixture.md'
    with io.open(os.path.join(tmp, rel), 'w', encoding='utf-8',
                 newline='\n') as fh:
        fh.write(body)
    needles = needles or (('the census SQL', 'legacy_ciphertext_census'),
                          ('the threshold', 'legacy_rows = 0'))
    return [{
        'rule': 'fixture rule',
        'needles': lambda: list(needles),
        'code_at': 'the fixture',
        'copies': [{'path': rel, 'anchor': anchor}],
    }]


def _with_repo(tmp, fn):
    """Run fn with REPO pointed at a temp tree, then restore."""
    global REPO
    old = REPO
    REPO = tmp
    try:
        return fn()
    finally:
        REPO = old


@arm('A1-missing-needle', 'a runbook that omits the precondition passes')
def _a1(tmp):
    reg = _fixture(tmp, 'ANCHOR LINE\nset PREVIOUS, change the key, clear it.\n')
    code, lines = _with_repo(tmp, lambda: run(reg))
    return (code == EXIT_FINDING and 'DIVERGES' in NL.join(lines)), NL.join(lines)


@arm('A2-complete-passes', 'a runbook that DOES carry it is reported as '
                           'diverging -- a check that fails on good input '
                           'gets deleted')
def _a2(tmp):
    reg = _fixture(tmp, 'ANCHOR LINE\nrun sql/legacy_ciphertext_census.sql '
                        'and require legacy_rows = 0 first.\n')
    code, lines = _with_repo(tmp, lambda: run(reg))
    return (code == EXIT_CLEAN and 'AGREES' in NL.join(lines)), NL.join(lines)


@arm('A3-dead-anchor', 'an anchor that no longer matches reports a clean pass '
                       'instead of a finding -- the way a check silently '
                       'stops testing anything')
def _a3(tmp):
    reg = _fixture(tmp, 'a document that says nothing about any of this\n',
                   anchor='ANCHOR LINE')
    code, lines = _with_repo(tmp, lambda: run(reg))
    return (code == EXIT_FINDING
            and 'not in the file at all' in NL.join(lines)), NL.join(lines)


@arm('A4-absent-file', 'a prose copy that has been deleted or moved is a pass')
def _a4(tmp):
    reg = _fixture(tmp, 'x\n')
    reg[0]['copies'][0]['path'] = 'no-such-file.md'
    code, lines = _with_repo(tmp, lambda: run(reg))
    return (code == EXIT_FINDING
            and 'does not exist' in NL.join(lines)), NL.join(lines)


@arm('A5-window-bound', 'a needle found 2,000 lines away in an unrelated '
                        'section satisfies the check')
def _a5(tmp):
    far = NL.join(['filler'] * (WINDOW_LINES + 50))
    reg = _fixture(tmp, 'ANCHOR LINE\nnothing useful here.\n' + far
                   + NL + 'run sql/legacy_ciphertext_census.sql, legacy_rows = 0'
                   + NL)
    code, lines = _with_repo(tmp, lambda: run(reg))
    return (code == EXIT_FINDING and 'DIVERGES' in NL.join(lines)), NL.join(lines)


@arm('A6-paraphrase-survives', 'a rewording of the surrounding prose is '
                               'reported as divergence, so the check punishes '
                               'ordinary editing')
def _a6(tmp):
    reg = _fixture(tmp, 'ANCHOR LINE\nBefore you clear anything: the census '
                        'in sql/legacy_ciphertext_census.sql must come back '
                        'with legacy_rows = 0 on every table.\n')
    code, lines = _with_repo(tmp, lambda: run(reg))
    return (code == EXIT_CLEAN), NL.join(lines)


@arm('A7-wrapped-markdown', 'a needle broken across a Markdown line wrap is '
                            'reported missing')
def _a7(tmp):
    reg = _fixture(tmp, 'ANCHOR LINE\nrequire legacy_rows\n= 0 and run\n'
                        'sql/legacy_ciphertext_census.sql\n')
    code, lines = _with_repo(tmp, lambda: run(reg))
    return (code == EXIT_CLEAN), NL.join(lines)


@arm('A8-empty-needles', 'a rule whose needle list came back empty passes '
                         'every copy -- silent success')
def _a8(tmp):
    reg = _fixture(tmp, 'ANCHOR LINE\nnothing.\n')

    def boom():
        raise KeyError('no entry')
    reg[0]['needles'] = boom
    code, lines = _with_repo(tmp, lambda: run(reg))
    return (code == EXIT_COULD_NOT_RUN
            and 'COULD NOT RUN' in NL.join(lines)), NL.join(lines)


@arm('A9-needles-are-imported', 'the needle list is a second hand-written '
                                'copy in this file rather than the lock\'s')
def _a9(tmp):
    # Add a needle to the LOCK and require the real registry to start
    # demanding it. If this file carried its own list, nothing would change.
    var = 'SD_AUTH_SECRET_PREVIOUS'
    old = SI._IRREVERSIBLE[var]
    SI._IRREVERSIBLE[var] = tuple(old) + (
        ('a needle that exists only in the lock',
         'zzz-not-in-any-runbook-zzz'),)
    try:
        got = [n for _l, n in REGISTRY[0]['needles']()]
    finally:
        SI._IRREVERSIBLE[var] = old
    return ('zzz-not-in-any-runbook-zzz' in got), 'needles: %d' % len(got)


def _run_arms(verbose=True):
    passed = failed = 0
    fails = []
    for name, defect, fn in _ARMS:
        tmp = tempfile.mkdtemp(prefix='runbook-arm-')
        try:
            ok, detail = fn(tmp)
        except Exception as exc:                                 # noqa: BLE001
            ok, detail = False, 'arm raised: %s' % exc
        finally:
            _rm(tmp)
        if ok:
            passed += 1
            if verbose:
                print('  PASS  %-24s catches: %s' % (name, defect))
        else:
            failed += 1
            fails.append((name, defect, str(detail)[:300]))
            if verbose:
                print('  FAIL  %-24s did NOT catch: %s' % (name, defect))
                print('        %s' % str(detail)[:300])
    return passed, failed, fails


def _rm(path):
    for root, dirs, files in os.walk(path, topdown=False):
        for f in files:
            try:
                os.remove(os.path.join(root, f))
            except OSError:
                pass
        for d in dirs:
            try:
                os.rmdir(os.path.join(root, d))
            except OSError:
                pass
    try:
        os.rmdir(path)
    except OSError:
        pass


def selftest():
    print('runbook_constant_agreement --selftest  (criteria %s)'
          % CRITERIA_VERSION)
    print('%d arm(s), each driven against a fixture where the named thing IS '
          'wrong.' % len(_ARMS))
    print('BOTH DIRECTIONS: four arms require a FINDING on bad prose, three '
          'require a CLEAN pass on good prose. A check that only ever fires '
          'is as useless as one that never does -- it gets deleted.')
    print('')
    p, f, fails = _run_arms()
    print('')
    print('  %d/%d arms fire on the defect they name' % (p, len(_ARMS)))
    if f:
        print('  %d ARM(S) DID NOT FIRE -- unproven, not proven absent.' % f)
        return EXIT_FINDING
    return EXIT_CLEAN


# ── ablation ───────────────────────────────────────────────────────────────

_ABLATIONS = (
    ('anchor-window',
     'passage() bounds the search to a window around the anchor instead of '
     'reading the whole file',
     lambda: _patch('passage', _whole_file_passage)),
    ('dead-anchor-is-a-finding',
     'a missing anchor is a finding rather than an empty pass',
     lambda: _patch('passage', _anchor_miss_is_clean)),
    ('whitespace-normalisation',
     '_norm collapses Markdown line wrapping before comparing',
     lambda: _patch('_norm', lambda text: text.lower())),
    ('needle-import',
     'the needle list comes from the lock rather than from a copy here',
     lambda: _patch_local_needles()),
)


def _patch(name, replacement):
    old = globals()[name]
    globals()[name] = replacement
    return lambda: globals().__setitem__(name, old)


def _whole_file_passage(path, anchor):
    full = os.path.join(REPO, path)
    if not os.path.isfile(full):
        return '', 'the file does not exist at %s' % path
    try:
        with io.open(full, encoding='utf-8', errors='replace') as fh:
            return _norm(fh.read()), ''
    except OSError as exc:
        return '', 'unreadable: %s' % str(exc)[:90]


def _anchor_miss_is_clean(path, anchor):
    text, why = _real_passage(path, anchor)
    if not text and 'anchor' in why:
        # The defect: an anchor that no longer matches returns the whole file,
        # which then satisfies every needle that appears anywhere in it.
        return _whole_file_passage(path, anchor)
    return text, why


@arm('A10-needles-nonempty', 'the real registry resolves to an EMPTY needle '
                             'list, which would pass every prose copy')
def _a10(tmp):
    got = REGISTRY[0]['needles']()
    return (len(got) >= 3), '%d needles' % len(got)


def _patch_local_needles():
    old = REGISTRY[0]['needles']
    REGISTRY[0]['needles'] = lambda: [('a local copy', 'legacy_rows = 0')]
    return lambda: REGISTRY[0].__setitem__('needles', old)


def ablation():
    print('runbook_constant_agreement --ablation  (criteria %s)'
          % CRITERIA_VERSION)
    print('ONE layer removed at a time; every arm re-run. WHICH arms go quiet')
    print('is the measurement, not the exit code.')
    print('')
    bp, bf, _ = _run_arms(verbose=False)
    print('  baseline: %d pass / %d fail' % (bp, bf))
    if bf:
        print('  ABLATION NOT RUN -- the baseline is not clean, so nothing '
              'below could be attributed to the removed layer.')
        return EXIT_COULD_NOT_RUN
    print('')
    naked = []
    for name, what, patcher in _ABLATIONS:
        restore = patcher()
        try:
            _p, f, fails = _run_arms(verbose=False)
        finally:
            restore()
        if f == 0:
            naked.append(name)
            print('  %-28s NOTHING CAUGHT IT -- UNPROVEN.' % name)
        else:
            print('  %-28s %d arm(s) fail without it: %s'
                  % (name, f, ', '.join(n for n, _d, _w in fails)))
        print('    %s' % what)
    print('')
    if naked:
        print('  %d LAYER(S) UNPROVEN: %s' % (len(naked), ', '.join(naked)))
        return EXIT_FINDING
    print('  every layer is load-bearing.')
    return EXIT_CLEAN


_real_passage = passage


def main(argv=None):
    ap = argparse.ArgumentParser(
        description='Fail when a Markdown runbook diverges from its code '
                    'constant.')
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--ablation', action='store_true')
    args = ap.parse_args(argv)
    if SI is None:
        print('COULD NOT RUN -- %s' % _IMPORT_WHY)
        print('  This check depends on another tool and FAILS CLOSED when it '
              'is absent rather than skipping (PR 1.11). Nothing was '
              'compared, and this is not a pass.')
        return EXIT_COULD_NOT_RUN
    if args.selftest:
        return selftest()
    if args.ablation:
        return ablation()
    code, lines = run()
    for ln in lines:
        print(ln)
    return code


if __name__ == '__main__':
    sys.exit(main())
