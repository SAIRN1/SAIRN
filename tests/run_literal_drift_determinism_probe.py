"""tools/literal_drift_check.py must produce the SAME output twice.

    python tests/run_literal_drift_determinism_probe.py

WHY THIS EXISTS. The near-duplicate section sorted a **set** of strings with
`key=len`. `sorted` is stable, so equal-length strings kept whatever order the
SET iterated them in -- and set iteration order for strings depends on
`PYTHONHASHSEED`, which the interpreter varies between processes. The checker
therefore answered differently on identical input, run to run, with nothing
wrong and nothing to see.

IT WAS WORSE THAN THE ROW THAT REPORTED IT SAID. `docs/SAIRN-OPEN-WORK-INDEX.md`
recorded it as *"same lines, same ratio, opposite A/B labels"* -- harmless.
Measured across seeds, the PAIR NUMBERING moves too: at one seed `pair 5` is
63-vs-52 chars at ratio 0.904, at another it is 63-vs-42 at 0.800. A different
finding under the same label. Anything citing a pair number, or diffing two runs
of this checker, was reading noise -- and diffing two runs is exactly what
`tools/comment_sensitivity_check.py` does, which is how it surfaced at all.

WHY A PROBE AND NOT JUST THE FIX. Non-determinism is invisible in a single run
by construction, so it cannot be noticed by using the tool -- only by comparing
two runs on purpose. A second `set()` or a second `key=len` would reintroduce it
silently, and this checker is wired into the promoted report-only registry, so
its output is read by a mechanism rather than only by a person.

THE ARMS ARE DIFFERENTIAL AND THE FIRST ONE IS THE MUTATION PROOF: the same
checker with the OLD sort restored must FAIL this probe. Without that arm,
"identical across seeds" is satisfied by a tool that prints nothing.

Exit 0 pass, 1 fail.
"""
import io
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO, 'tools', 'literal_drift_check.py')
# Apps chosen for two reasons, both measured: they actually PRODUCE
# near-duplicate pairs (a file with none would pass every arm here while
# proving nothing), and they are fast. sairnvet is the richest at 33 pairs in
# 1.2s; stonedesk has 17 but costs 6.7s and is left out deliberately.
APPS = ['sairnvet.html', 'sairncode.html']
SEEDS = ['1', '7', '12345']

fails = []


def check(cond, label):
    print('  %-5s %s' % ('ok' if cond else 'FAIL', label))
    if not cond:
        fails.append(label)


def run(tool, app, seed):
    env = dict(os.environ, PYTHONHASHSEED=seed)
    r = subprocess.run([sys.executable, tool, os.path.join(REPO, app)],
                       cwd=REPO, capture_output=True, text=True, env=env,
                       timeout=300)
    return r.stdout


def pair_count(out):
    return out.count('\n  pair ')


print('1. THE FIXTURE IS REAL -- these apps produce pairs to be unstable ABOUT')
for app in APPS:
    n = pair_count(run(TOOL, app, '1'))
    check(n > 0, '%s yields %d near-duplicate pair(s)' % (app, n))

print('')
print('2. MUTATION PROOF -- the OLD sort is detectably unstable')
# The defect is restored on a COPY, never in the tool itself. If this arm ever
# stops failing, either the interpreter stopped varying set order or this probe
# stopped looking -- and the second is far more likely.
src = io.open(TOOL, encoding='utf-8').read()
FIXED = 'sorted(set(t for _, t in prose), key=lambda t: (-len(t), t))'
OLD = 'sorted(set(t for _, t in prose), key=len, reverse=True)'
check(FIXED in src, 'the shipped tool carries the total-order sort')

# ── THE COPY LIVES IN tools/, AND THE FIRST VERSION DID NOT ────────────────
# Written to a tempfile.mkdtemp() at first, where it died on
# `ModuleNotFoundError: No module named 'comment_quote_check'` -- the tool
# imports siblings via `sys.path.insert(0, dirname(__file__))`. It printed ZERO
# lines at every seed, so "identical across seeds" was true of nothing, and the
# arm reported the defect as undetectable. **Had the comparison been written
# the other way round it would have reported PASS** -- a control that exercises
# nothing, which is the exact class this probe exists to guard against,
# committed inside the probe guarding against it.
#
# It is removed in the `finally`, and the name is prefixed `zz_tmp_` so a
# stranded copy is obvious rather than plausible.
broken = os.path.join(REPO, 'tools', 'zz_tmp_broken_literal_drift.py')
try:
    io.open(broken, 'w', encoding='utf-8', newline='').write(src.replace(FIXED, OLD))
    sanity = run(broken, APPS[0], '1')
    check(pair_count(sanity) > 0,
          'the reverted COPY actually runs -- it reports %d pair(s), so a '
          'difference between seeds would be visible' % pair_count(sanity))
    outs = {s: run(broken, APPS[0], s) for s in SEEDS}
    distinct = len({v for v in outs.values()})
    check(distinct > 1,
          'with the old sort restored, %s gives %d distinct outputs across '
          'seeds %s -- the probe can see the defect'
          % (APPS[0], distinct, '/'.join(SEEDS)))
finally:
    if os.path.exists(broken):
        os.remove(broken)
check(not os.path.exists(broken), 'and the reverted copy was removed')

print('')
print('3. THE SHIPPED TOOL IS BYTE-IDENTICAL ACROSS SEEDS')
for app in APPS:
    outs = {s: run(TOOL, app, s) for s in SEEDS}
    same = len({v for v in outs.values()}) == 1
    check(same, '%s: identical output at seeds %s' % (app, '/'.join(SEEDS)))
    if not same:
        a, b = outs[SEEDS[0]].splitlines(), outs[SEEDS[1]].splitlines()
        for i in range(max(len(a), len(b))):
            x = a[i] if i < len(a) else '(none)'
            y = b[i] if i < len(b) else '(none)'
            if x != y:
                print('        first difference at line %d' % (i + 1))
                print('        seed %s: %s' % (SEEDS[0], x[:96]))
                print('        seed %s: %s' % (SEEDS[1], y[:96]))
                break

print('')
print('4. NO SORT OVER A SET IS LEFT KEYED ON LENGTH ALONE')
# A cheap structural tripwire for the same mistake reappearing somewhere else in
# the file. It is DELIBERATELY narrow -- it looks for the exact shape that bit,
# not for every conceivable nondeterminism -- because arm 3 is the real check
# and this one only makes a regression obvious at the point it is written.
#
# ── SEARCHED WITH COMMENTS STRIPPED, PER PROCESS RULES SECTION 1.2 ─────────
# The first version searched the raw source and FAILED A CORRECT FILE, because
# the fix's own comment quotes `key=len` while explaining why it is wrong. The
# rule -- "grep cannot tell code from text that describes code" -- was written
# down on 2026-09-11 after it happened twice in one day; this is the third,
# written by somebody who had read the rule an hour earlier. It now lives at
# docs/SAIRN-PROCESS-RULES.md section 1.2, moved out of CLAUDE.md 2026-09-12.
# The direction is the loud one -- a correct file failing -- which is why it was
# caught immediately rather than passing quietly.
code = '\n'.join(l for l in src.splitlines() if not l.lstrip().startswith('#'))
check('key=len' not in code,
      'no bare `key=len` remains in CODE (a tie between equal-length strings '
      'falls back to iteration order)')
check('key=len' in src,
      "...and the raw source still mentions it, in the comment that explains "
      "why -- so this arm is proven to be reading a stripped copy rather than "
      "passing because the string vanished")

print('')
if fails:
    print('%d FAILING CHECK(S)' % len(fails))
    for f in fails:
        print('  %s' % f)
    sys.exit(1)
print('ALL CHECKS PASS')
