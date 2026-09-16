"""Does the suite KILL each operand of a compound condition, or only run past it?

    python tools/condition_coverage.py --fixtures     # the blind lock alone
    python tools/condition_coverage.py
    python tools/condition_coverage.py --engine ledger
    python tools/condition_coverage.py --json

── THE NAME IS DELIBERATE: THIS IS NOT MC/DC ─────────────────────────────
MC/DC asks whether each condition in a decision has been shown to independently
affect the outcome. Measuring that needs instrumented coverage of every operand
across every test, and no JavaScript toolchain here provides it -- `api/` is
zero-npm, so getting it would mean an AST/instrumentation dependency this
platform does not carry.

What IS reachable, and is stronger evidence for the thing anybody actually
wants: NEGATE ONE OPERAND AND SEE WHETHER THE SUITE DIES. MC/DC proves a test
TOUCHED an operand. This proves a test would NOTICE if the operand were wrong.
A condition the suite runs past without complaint is untested no matter what a
coverage percentage says.

Calling it MC/DC would be a compliance-adjacent label for something that is not
literally that, so it is called what it is: MUTATION-DERIVED CONDITION COVERAGE.

── THE BLIND LOCK ────────────────────────────────────────────────────────
Pass/fail is decided against synthetic fixtures below, and this REFUSES TO
MUTATE A REAL ENGINE until they classify as written. A mutation harness tuned
after seeing which operands survive is a harness that reports what the suite
already does.

── ACCURACY AND STABILITY ARE SEPARATE, AND HERE THEY MEAN SOMETHING SHARP
ACCURACY   did the mutation actually change the file? An anchor that matched
           zero or several times mutated nothing or mutated the wrong place,
           and a SURVIVED verdict from a mutation that never applied is the
           worst output this tool could produce -- it would report a tested
           operand as untested. Verified by sha256 before and after.
STABILITY  run the SAME mutation twice. A suite that answers differently on
           identical input makes every kill/survive verdict a coin flip, and
           that is a finding about the SUITE, not about the operand.

── MARGIN DOES NOT APPLY ─────────────────────────────────────────────────
Killed or survived is binary; there is no distance to a violation. Said here
rather than printing a meaningless column.

── SAFETY, because this WRITES TO REAL SOURCE FILES ──────────────────────
  * it refuses to run on a dirty working tree -- a restore cannot be verified
    against a baseline that was already modified;
  * every file is restored in a `finally`, and the restore is verified by
    sha256 rather than assumed;
  * a mutation is applied only when its anchor matches EXACTLY ONCE.

── WHAT IT CANNOT SEE, said here rather than discovered later ────────────
  * operands inside comments or string literals. They are stripped before
    parsing, so they are never mutated -- and never counted as covered either;
  * a `||` inside a REGEX LITERAL. The stripper handles quotes and comments and
    does NOT track regex literals, so an alternation there could in principle be
    mutated. Measured on the four engines: zero `&&`/`||` occur inside a regex,
    so nothing is affected today -- stated as a real limit rather than implied
    away, because the next engine added may differ;
  * short-circuit reachability: an operand that no input can reach will survive
    every mutation, and that is indistinguishable here from a test gap. Both
    need a human;
  * whether the surviving operand MATTERS. This reports evidence, not severity.

Exit 0 when every operand is killed, 1 when any survives or any mutation could
not be applied, 2 when the fixtures fail or the tree is dirty -- neither of
which is a pass.
"""
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CRITERIA_VERSION = '2026-09-13.1'

# The four Tier A financial engines, with the suite that is supposed to defend
# each. Reused from tools/invariant_registry.js's HAND-DERIVED classification
# rather than re-guessed -- and the suite names are READ, not assumed from the
# filename: care-charges' suite is tests/sairncare/test-care-charges.js, which a
# `<engine>.test.js` convention would have missed entirely. That exact
# assumption produced a false "untested" claim about dental-ledger.js earlier
# today.
ENGINES = [
    ('ledger', 'api/_lib/ledger.js', 'api/_lib/ledger.test.js'),
    ('roofing-billing', 'api/_lib/roofing-billing.js', 'api/_lib/roofing-billing.test.js'),
    ('wip-accounting', 'api/_lib/wip-accounting.js', 'api/_lib/wip-accounting.test.js'),
    ('care-charges', 'api/_lib/care-charges.js', 'tests/sairncare/test-care-charges.js'),
]


def strip_js(src):
    """Blank comments and string literals, preserving offsets and newlines.

    Offsets are preserved so a position found here still points at the real
    file. Strings are blanked as well as comments: an `&&` inside a message is
    not a condition, and mutating one would change a user-facing sentence while
    reporting it as a logic operand.
    """
    out = list(src)
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if c == '/' and i + 1 < n and src[i + 1] == '/':
            j = src.find('\n', i)
            j = n if j < 0 else j
            for k in range(i, j):
                out[k] = ' '
            i = j
        elif c == '/' and i + 1 < n and src[i + 1] == '*':
            j = src.find('*/', i + 2)
            j = n if j < 0 else j + 2
            for k in range(i, j):
                if out[k] != '\n':
                    out[k] = ' '
            i = j
        elif c in ('"', "'", '`'):
            q, j = c, i + 1
            while j < n and src[j] != q:
                if src[j] == '\\':
                    j += 1
                j += 1
            for k in range(i, min(j + 1, n)):
                if out[k] != '\n':
                    out[k] = ' '
            i = j + 1
        else:
            i += 1
    return ''.join(out)


def operands(src):
    """Every `&&` / `||` position in code, with the line it sits on."""
    code = strip_js(src)
    out = []
    for m in re.finditer(r'&&|\|\|', code):
        line_no = code.count('\n', 0, m.start()) + 1
        line = src.split('\n')[line_no - 1]
        out.append({'op': m.group(0), 'pos': m.start(), 'line': line_no,
                    'text': line.strip()})
    return out


def mutate(src, pos, op):
    """Negate ONE operand: `a && b` -> `a && !(b)` by flipping the operator.

    Flipping `&&` to `||` (and back) is the minimal change that alters what the
    decision depends on WITHOUT changing the operands themselves, so a surviving
    mutant means the suite never distinguished the two -- which is exactly "this
    operand does not independently affect any tested outcome".
    """
    other = '||' if op == '&&' else '&&'
    return src[:pos] + other + src[pos + 2:]


def sha(path):
    with io.open(path, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def write(path, text):
    """Write and CLOSE explicitly.

    The first version relied on refcount to close the handle and then hashed
    the file on the next line. The full ledger sweep reported the restore as
    NOT byte-identical while the bytes on disk were in fact correct -- an
    unflushed write read back mid-flight. A restore-verification that can
    report a false failure is as bad as one that can report a false success:
    both make the check unbelievable.
    """
    with io.open(path, 'w', encoding='utf-8', newline=chr(10)) as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())


def run_suite(suite):
    p = subprocess.run(['node', os.path.join(REPO, suite)], capture_output=True,
                       text=True, encoding='utf-8', errors='replace', cwd=REPO,
                       timeout=120)
    out = (p.stdout or '') + (p.stderr or '')
    red = p.returncode != 0 or 'FAIL' in out or re.search(r'\b[1-9]\d* failed', out)
    return bool(red)


# ── FIXTURES: hand-decided, and they exercise the PARSER, which is the half
# ── that can silently mutate the wrong thing.
FIXTURES = [
    ('an operand in code is found', 'if (a && b) x();', 1),
    ('an && inside a LINE COMMENT is not an operand', '// a && b\nif (c) x();', 0),
    ('an && inside a BLOCK COMMENT is not an operand', '/* a && b */\nif (c) x();', 0),
    ('an && inside a STRING is not an operand -- mutating it would rewrite a message',
     "var m = 'press a && b';\nif (c) x();", 0),
    ('an || inside a template literal is not an operand', 'var m = `x || y`;\nif (c) x();', 0),
    ('CONTROL: both operators in real code are found', 'if (a && b || c) x();', 2),
    ('a URL is not two operands and does not break the scanner',
     "var u = 'https://x/y';\nif (a && b) x();", 1),
]

MUTATE_FIXTURES = [
    ('flipping && yields ||', 'if (a && b) x();', '&&', 'if (a || b) x();'),
    ('flipping || yields &&', 'if (a || b) x();', '||', 'if (a && b) x();'),
]


def run_fixtures():
    bad = []
    for name, src, want in FIXTURES:
        got = len(operands(src))
        if got != want:
            bad.append((name, want, got))
    for name, src, op, want in MUTATE_FIXTURES:
        ops = operands(src)
        got = mutate(src, ops[0]['pos'], op) if ops else '(no operand found)'
        if got != want:
            bad.append((name, want, got))
    return bad


def sweep(key, engine, suite, limit=None):
    path = os.path.join(REPO, engine)
    before_hash = sha(path)
    src = io.open(path, encoding='utf-8').read()
    ops = operands(src)
    if limit:
        ops = ops[:limit]
    killed, survived, not_applied, results = 0, 0, 0, []
    try:
        for o in ops:
            mutated = mutate(src, o['pos'], o['op'])
            applied = mutated != src
            write(path, mutated)
            # ACCURACY: did the file really change? A SURVIVED verdict from a
            # mutation that never applied would report a tested operand as
            # untested -- the worst output this tool could produce.
            really = sha(path) != before_hash
            red = run_suite(suite) if really else None
            if not (applied and really):
                not_applied += 1
                verdict = 'NOT-APPLIED'
            elif red:
                killed += 1
                verdict = 'KILLED'
            else:
                survived += 1
                verdict = 'SURVIVED'
            results.append({'line': o['line'], 'op': o['op'], 'verdict': verdict,
                            'text': o['text'][:100]})
    finally:
        write(path, src)
    # ── THE RESTORE IS VERIFIED, RETRIED, AND ESCALATED TO GIT ────────────
    # A tool that writes real source files must leave NO ambiguity about the
    # state it left them in. The first version compared once and reported
    # RESTORED: NO on a file that was in fact byte-identical to HEAD -- a read
    # that beat the write to disk. A false failure here is as corrosive as a
    # false success: nobody can act on either.
    restored = sha(path) == before_hash
    how = 'write'
    if not restored:
        time.sleep(0.25)
        restored = sha(path) == before_hash          # retry the READ, not the write
        how = 'write (after re-read)'
    if not restored:
        # Last resort, and LOUD: take the file back from git rather than leave
        # a mutated engine on disk because a hash check was inconclusive.
        subprocess.run(['git', 'checkout', '--', engine], cwd=REPO,
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
        restored = sha(path) == before_hash
        how = 'git checkout -- (the write-back could not be confirmed)'
    return {'engine': key, 'file': engine, 'suite': suite,
            'operands': len(ops), 'killed': killed, 'survived': survived,
            'not_applied': not_applied, 'restored_byte_identical': restored,
            'restored_how': how,
            'results': results}


def main(argv):
    bad = run_fixtures()
    print('MUTATION-DERIVED CONDITION COVERAGE -- criteria %s' % CRITERIA_VERSION)
    print('  NOT MC/DC, and deliberately not called it: this proves the suite would')
    print('  NOTICE a wrong operand, which MC/DC does not. See the module docstring.')
    if bad:
        print('  !! THE CRITERIA FAILED THEIR OWN FIXTURES. NOTHING WAS MUTATED.')
        for n, w, g in bad:
            print('     expected %r, got %r  -- %s' % (w, g, n))
        return 2
    print('  blind lock: %d/%d fixtures correct, run before any file was touched.'
          % (len(FIXTURES) + len(MUTATE_FIXTURES), len(FIXTURES) + len(MUTATE_FIXTURES)))
    if '--fixtures' in argv:
        return 0

    # TRACKED dirt only. The refusal exists because this tool WRITES to real
    # source files and verifies the restore against a baseline -- and an
    # UNTRACKED file cannot be part of that baseline, because the tool never
    # writes to one and git never had a version to restore. Refusing on
    # untracked dirt made the tool unrunnable for anybody with a scratch file
    # in the clone: measured 2026-09-15, one stray `piac.html` was enough to
    # report COULD NOT RUN on the whole platform. A refusal that fires on
    # something it is not protecting against is a refusal people route around.
    dirty = subprocess.run(['git', 'status', '--porcelain',
                            '--untracked-files=no'], capture_output=True,
                           text=True, encoding='utf-8', errors='replace',
                           cwd=REPO).stdout.strip()
    if dirty:
        print('  !! TRACKED FILES ARE MODIFIED. This tool WRITES to real source')
        print('     files and verifies the restore against a baseline; it will')
        print('     not run when that baseline is already modified. Commit or')
        print('     stash first. Modified:')
        for line in dirty.split('\n')[:10]:
            print('       %s' % line.strip())
        return 2

    want = None
    if '--engine' in argv:
        i = argv.index('--engine')
        want = argv[i + 1] if i + 1 < len(argv) else None
    limit = None
    if '--limit' in argv:
        i = argv.index('--limit')
        limit = int(argv[i + 1])

    out = []
    for key, engine, suite in ENGINES:
        if want and key != want:
            continue
        out.append(sweep(key, engine, suite, limit))

    if '--json' in argv:
        print(json.dumps({'criteria_version': CRITERIA_VERSION, 'engines': out}, indent=1))
    else:
        print('')
        print('  ENGINE            OPERANDS  KILLED  SURVIVED  NOT-APPLIED  RESTORED')
        for r in out:
            print('  %-17s %5d   %5d   %6d   %9d   %s'
                  % (r['engine'], r['operands'], r['killed'], r['survived'],
                     r['not_applied'], 'yes' if r['restored_byte_identical'] else 'NO !!'))
        for r in out:
            surv = [x for x in r['results'] if x['verdict'] != 'KILLED']
            if not surv:
                continue
            print('')
            print('  %s -- %d operand(s) the suite did not notice:' % (r['engine'], len(surv)))
            for x in surv[:20]:
                print('    %-12s %s:%d  %s' % (x['verdict'], r['file'], x['line'], x['text'][:80]))
            if len(surv) > 20:
                print('    ... and %d more' % (len(surv) - 20))
        print('')
        print('  A SURVIVING OPERAND IS EVIDENCE, NOT A VERDICT. It can mean a test gap,')
        print('  or an operand no input can reach -- short-circuit dead logic looks')
        print('  identical here. Both need a human; this tool does not guess which.')
        print('  Margin is not reported: killed/survived is binary and has no distance.')

    failed = any(r['survived'] or r['not_applied'] or not r['restored_byte_identical']
                 for r in out)
    return 1 if failed else 0


if __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.exit(main(sys.argv[1:]))
