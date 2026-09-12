r"""Does each checker give the SAME answer twice on the same input?

    python -m testint.check_determinism --config testint.config.json
    python -m testint.check_determinism --self-test

Exit 0 when every checker is stable, 1 when one is not, 3 could-not-run.

── THE FAILURE ───────────────────────────────────────────────────────────────
One checker sorted a **set** of strings with `key=len`. `sorted` is stable, so
equal-length strings kept whatever order the set iterated them in -- and set
iteration order for strings depends on the interpreter's hash seed, which is
randomised per process. Across six seeds it produced **six different reports on
the same file**, with the finding numbering shifted so `pair 5` was a different
finding each time.

It went unnoticed for weeks. Noticing requires comparing two runs, and **nothing
compares two runs unless it sets out to** -- which is what this does.

It matters most exactly where it is least visible: a checker wired into an
automatic post-push report is read by a mechanism, not a person, so its output
moving is invisible until somebody diffs two reports for an unrelated reason.

── HOW IT WORKS, AND THE TWO WAYS THIS MEASUREMENT LIES ──────────────────────
Each checker is run at several `PYTHONHASHSEED` values and its stdout compared
byte for byte. Two failure modes of the METHOD are guarded explicitly, because
both were hit while building it:

  1. **A checker that cannot run is perfectly stable.** A command that dies on
     an import error prints nothing at every seed, and "identical across seeds"
     is then true of nothing. So a checker producing NO output at all is
     reported as COULD NOT RUN, never as stable.
  2. **One input is not coverage.** With the real defect present, the original
     checker gave six distinct outputs on one file and was perfectly stable on
     two others. If your checkers take a target, list several in `targets` --
     a single-target sweep would have cleared it.

`--self-test` proves the method can see what it hunts: it writes a script that
is genuinely seed-dependent, runs it through the same path, and fails if the
result comes back stable. **Without that, a sweep reporting NONE is
indistinguishable from a sweep that is broken.**

── CONFIG ────────────────────────────────────────────────────────────────────
    "checkers": ["tools/*_check.py"],
    "determinism": {
        "seeds":   ["1", "7", "12345"],
        "targets": ["src/a.js", "src/b.js"],
        "timeout": 600
    }

`targets` is optional: a checker that takes no argument is run bare.
"""
import io
import os
import subprocess
import sys
import tempfile

from .config import ConfigError, load

DEFAULT_SEEDS = ['1', '7', '12345']


def run_once(cmd, cwd, seed, timeout):
    env = dict(os.environ, PYTHONHASHSEED=seed)
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                           env=env, timeout=timeout)
    except Exception as e:                               # noqa: BLE001
        return None, str(e)
    return p.stdout, None


def sweep(cmd, cwd, seeds, timeout):
    """('stable'|'varies'|'no-output'|'error', detail)."""
    outs, err = [], None
    for s in seeds:
        out, e = run_once(cmd, cwd, s, timeout)
        if e:
            return 'error', e
        outs.append(out)
    if not any(o.strip() for o in outs):
        # GUARD 1. A command that prints nothing is identical at every seed and
        # tells you nothing. Reporting that as stable is how a broken sweep
        # reports success.
        return 'no-output', 'produced no stdout at any seed'
    n = len(set(outs))
    return ('stable' if n == 1 else 'varies'), '%d distinct output(s)' % n


def self_test():
    """Prove the method can DETECT a seed-dependent program.

    A sweep that returns NONE is worth nothing unless it has been shown to see
    the thing it hunts. This writes a script whose output really does depend on
    set iteration order, runs it through the same code path, and fails loudly if
    it comes back stable.
    """
    d = tempfile.mkdtemp()
    p = os.path.join(d, 'zz_seed_dependent.py')
    io.open(p, 'w', encoding='utf-8', newline='\n').write(
        'items = {"aa", "bb", "cc", "dd", "ee", "ff", "gg", "hh"}\n'
        '# sorted() is STABLE, so equal-length strings keep set iteration order.\n'
        'for x in sorted(items, key=len):\n'
        '    print(x)\n')
    verdict, detail = sweep([sys.executable, p], d, ['1', '7', '12345', '99999'], 60)
    ok = verdict == 'varies'
    print('SELF-TEST -- can this method see a seed-dependent program?')
    print('  planted a program whose output depends on set iteration order')
    print('  verdict: %-10s %s' % (verdict, detail))
    print('  %s' % ('DETECTED -- the method works' if ok else
                    'NOT DETECTED -- this sweep is blind and its NONE means nothing'))
    try:
        os.remove(p)
        os.rmdir(d)
    except OSError:
        pass
    return 0 if ok else 1


def run(cfg):
    checkers = cfg.checkers()
    if not checkers:
        return None, 'no checkers matched the config -- nothing was inspected'
    opts = cfg._data.get('determinism') or {}
    seeds = opts.get('seeds') or DEFAULT_SEEDS
    targets = opts.get('targets') or [None]
    timeout = opts.get('timeout') or 600
    rows = []
    for c in checkers:
        for t in targets:
            cmd = [sys.executable, c] + ([os.path.join(cfg.root, t)] if t else [])
            verdict, detail = sweep(cmd, cfg.root, seeds, timeout)
            rows.append({'checker': cfg.rel(c), 'target': t or '-',
                         'verdict': verdict, 'detail': detail})
    return {'rows': rows, 'seeds': seeds, 'targets': len(targets)}, None


def main(argv):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:                                    # noqa: BLE001
        pass
    if '--self-test' in argv:
        return self_test()
    cfgpath = 'testint.config.json'
    if '--config' in argv:
        cfgpath = argv[argv.index('--config') + 1]
    try:
        cfg = load(cfgpath)
        result, why = run(cfg)
    except ConfigError as e:
        print('COULD NOT RUN: %s' % e)
        return 3
    if result is None:
        print('COULD NOT RUN: %s' % why)
        print('A check with nothing to look at has not passed.')
        return 3

    rows = result['rows']
    varies = [r for r in rows if r['verdict'] == 'varies']
    silent = [r for r in rows if r['verdict'] in ('no-output', 'error')]
    print('DETERMINISM CHECK -- same input, %d hash seeds: %s'
          % (len(result['seeds']), '/'.join(result['seeds'])))
    print('  checker runs      : %d  (%d checker(s) x %d target(s))'
          % (len(rows), len(rows) // max(1, result['targets']), result['targets']))
    print('  VARIES            : %d  (the same input gives different answers)'
          % len(varies))
    print('  COULD NOT RUN     : %d  (no output at any seed -- NOT stable)'
          % len(silent))
    print('')
    for r in varies:
        print('  VARIES   %-46s %-22s %s' % (r['checker'], r['target'], r['detail']))
    for r in silent:
        print('  NO OUTPUT %-45s %-22s %s' % (r['checker'], r['target'], r['detail']))
    if not varies and not silent:
        print('  Every checker gave byte-identical output at every seed.')
        print('')
        print('  That is only worth something if this method can SEE the defect.')
        print('  Prove it: python -m testint.check_determinism --self-test')
    print('')
    print('One input is not coverage: with the original defect present, the '
          'checker varied on')
    print('one file and was perfectly stable on two others. List several '
          'targets.')
    return 1 if (varies or silent) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
