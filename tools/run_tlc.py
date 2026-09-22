"""Run TLC over the TLA+ specs in docs/spec -- item 78's missing half.

    python tools/run_tlc.py            # every spec, every configured behaviour
    python tools/run_tlc.py --list     # what would run, and what each expects

Exit 0  every run matched its EXPECTED outcome
Exit 1  a run did not match -- an invariant that should hold was violated,
        or one that should be violated held
Exit 2  COULD NOT RUN -- no java, or no tla2tools.jar. Never folded into 0.

── WHY THIS EXISTS ─────────────────────────────────────────────────────────
`docs/spec/RoleGates.tla` and `RateLimitConsume.tla` were written on
2026-09-14 and the open-work row said, honestly, "NOT MODEL-CHECKED: there is
no Java and no TLC on this machine (verified), so the spec has not been run
through a checker and is not described as verified."

WHAT NOBODY KNEW WAS THAT BOTH SPECS WERE BROKEN, and neither could have been
checked even with a checker present. The first real TLC run, 2026-09-22, found
one blocking defect in each:

  * RoleGates.tla       `NoApp == CHOOSE x : x \\notin Apps` -- an UNBOUNDED
                        CHOOSE. TLC cannot evaluate it and stopped while
                        computing initial states: 0 states generated.
  * RateLimitConsume.tla  `NoRead == -1` under `EXTENDS Naturals`, which has
                        no unary minus. The spec DID NOT PARSE.

Both are one-line fixes and both are now fixed. The point worth keeping is
that a companion checker reading the CODE cannot find either: it never
evaluates the spec. `tools/role_gate_invariants.js` was green throughout,
and correctly so -- it checks a different thing.

── NOT A GATE, AND DELIBERATELY ────────────────────────────────────────────
TLC needs a JVM and a 2.3MB jar that is NOT vendored in this repo. A check
that cannot run on a clone without network access has no business blocking a
push, so this is run by hand and reports. `tools/role_gate_invariants.js`
remains the thing that runs everywhere.

── WHAT A PASS HERE DOES AND DOES NOT MEAN ─────────────────────────────────
TLC checks the SPEC against ITSELF over a BOUNDED instance. It says the
invariants are consistent with the transitions for the constants supplied --
six of sixteen apps, two employees. It says NOTHING about whether the
JavaScript matches the spec; that is role_gate_invariants.js's job, and the
two are written separately on purpose.
"""

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = os.path.join(ROOT, 'docs', 'spec')
JAR = os.path.join(ROOT, 'tools', 'vendor', 'tla2tools.jar')

# (module, config, expectation, why)
# `violated` is a real expected outcome, not a tolerated failure: RacySpec
# exists to EXHIBIT the schedule that breaks the cap. A run where it held
# would mean the spec had stopped modelling the race.
RUNS = [
    ('MCRoleGates', 'MCRoleGates.cfg', 'holds',
     'the six role-gate invariants over the apps that export a complete set'),
    ('RateLimitConsume', 'RateLimitConsume_locked.cfg', 'holds',
     'the advisory-lock path must never exceed the cap'),
    ('RateLimitConsume', 'RateLimitConsume_racy.cfg', 'violated',
     'the count-then-insert path MUST break the cap -- that is the finding'),
    ('RateLimitConsume', 'RateLimitConsume_stale.cfg', 'violated',
     'a stale snapshot under REPEATABLE READ breaks it the same way'),
]


def java():
    """The JRE, from PATH or from the one place winget installs it."""
    if subprocess.run(['where', 'java'], capture_output=True,
                      shell=True).returncode == 0:
        return 'java'
    base = r'C:\Program Files\Eclipse Adoptium'
    if os.path.isdir(base):
        for d in sorted(os.listdir(base), reverse=True):
            cand = os.path.join(base, d, 'bin', 'java.exe')
            if os.path.isfile(cand):
                return cand
    return None


def main(argv):
    if '--list' in argv:
        for mod, cfg, expect, why in RUNS:
            print('  %-18s %-32s expect %-8s %s' % (mod, cfg, expect, why))
        return 0

    jv = java()
    if not jv:
        print('COULD NOT RUN -- no java on PATH and none under Eclipse Adoptium.')
        print('  winget install --id Microsoft.OpenJDK.17   (needs elevation)')
        return 2
    if not os.path.isfile(JAR):
        print('COULD NOT RUN -- %s is absent. It is NOT vendored (2.3MB).' % JAR)
        print('  curl -sSL -o tools/vendor/tla2tools.jar \\')
        print('    https://github.com/tlaplus/tlaplus/releases/latest/download/tla2tools.jar')
        return 2

    bad = []
    for mod, cfg, expect, why in RUNS:
        p = subprocess.run(
            [jv, '-XX:+UseParallelGC', '-cp', JAR, 'tlc2.TLC',
             # Termination is not a defect: LockedSpec ends when every request
             # is done, and TLC's default deadlock check calls that an error.
             '-deadlock', '-config', cfg, mod],
            cwd=SPEC, capture_output=True, text=True, encoding='utf-8',
            errors='replace')
        out = (p.stdout or '') + (p.stderr or '')
        held = 'Model checking completed. No error has been found.' in out
        violated = 'is violated' in out
        if not held and not violated:
            # A THIRD OUTCOME, kept separate. A spec that fails to parse or
            # blows up is not "violated" -- reporting it as one would have
            # hidden both of the defects found on 2026-09-22.
            print('  COULD NOT TELL  %-32s %s' % (cfg, out.strip().splitlines()[-1][:70]))
            bad.append((cfg, 'did not complete'))
            continue
        got = 'holds' if held else 'violated'
        mark = 'ok  ' if got == expect else 'WRONG'
        states = ''
        for line in out.splitlines():
            if 'states generated' in line and 'distinct' in line:
                states = line.strip()[:58]
        print('  %-5s %-32s %-8s %s' % (mark, cfg, got, states))
        if got != expect:
            bad.append((cfg, 'expected %s, got %s' % (expect, got)))

    print('')
    if bad:
        print('%d RUN(S) DID NOT MATCH:' % len(bad))
        for cfg, why in bad:
            print('   %s -- %s' % (cfg, why))
        return 1
    print('ALL %d RUNS MATCHED. The specs are consistent with themselves over '
          'the bounded\ninstance configured -- which is not a statement about '
          'the JavaScript.' % len(RUNS))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
