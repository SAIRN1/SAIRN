#!/usr/bin/env python
"""Ablate the b12-b14 tools/ layers whose tools have NO --ablation mode.

    python docs/ablation/b15_arms.py            # all of them
    python docs/ablation/b15_arms.py <name>     # one

WHY A DRIVER AND NOT FIVE HAND-RUN SWAPS. b14's second lesson: one of b13's
"ablations" was a one-off swap in a scratch script, gone when the terminal
closed, leaving the next reader only the claim. An ablation record has to be
RE-ESTABLISHABLE on every run. This file is that, for the five tools cc
changed in b12-b14 that have arms and no `--ablation` of their own.

HOW IT WORKS, and the one property that matters: each entry names a layer, an
`old` substring that must appear EXACTLY ONCE in the file at HEAD, and the
`new` substring that removes that one layer and nothing else. The driver
  1. asserts old occurs exactly once -- a swap that matched twice or zero
     times would silently ablate the wrong thing or nothing at all,
  2. runs the tool's own self-test and requires it to PASS,
  3. applies the swap, re-runs, and requires it to FAIL,
  4. restores the file BYTE-FOR-BYTE from the text it read, and re-runs,
     requiring a PASS again.

STEPS 2 AND 4 ARE NOT CEREMONY. b14's first lesson was a harness that
restored its subject but left the subject's STATE behind, so the same layer
read load-bearing in one run and UNPROVEN in the next. The pass/fail/pass
sandwich is what makes a contaminated run visible instead of silent, and the
restore is from bytes rather than from git so it works with the file dirty.

NOTHING HERE WRITES TO A TOOL PERMANENTLY. If this script is killed between
the swap and the restore the tool is left ablated, so it prints the path and
the exact restore instruction before it swaps.
"""
import io
import os
import subprocess
import sys

# docs/ablation/b15_arms.py -> repo root is two levels up.
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    '..', '..'))

NL = chr(10)

# ── the layers ─────────────────────────────────────────────────────────────
# Each: (name, file, self-test argv, old, new, what the layer is, which arms
# must go red). The arm names are the literal labels in each tool, so a
# reader can grep for them rather than taking this file's word.
CASES = (
    ('bare-run-unattributable',
     'tools/bare_run_write_check.py', ['--selftest'],
     "    return key.startswith('LOCKS:status/')",
     "    return False",
     'a change under the shared status registry is UNATTRIBUTABLE -- five '
     'other sessions write it continuously and a snapshot cannot see who '
     'wrote -- so it is printed on a third channel and never counted as a '
     'finding',
     'A8, A8b (A8c is the CONTROL and must stay green: without it A8 would '
     'pass on a tool that called everything unattributable)'),

    ('status-line-no-default-window',
     'tools/sairn_status_line.py', ['--fixtures'],
     "    return None, 'unrecognized model %r' % ident",
     "    return 200000, 'default'",
     'a model KNOWN_WINDOWS does not name yields no window at all and '
     'renders `ctx ??%`, rather than a percentage over a 200K denominator '
     'the session was never bounded by -- the b8 incident, where Sonnet 5 '
     'fell through to 200K and rendered a figure nearly 5x too alarming',
     'the unrecognized-model arms and the Sonnet-5-at-144K incident lock'),

    ('secrets-irreversible-runbook',
     'tools/secrets_inventory.py', ['--fixtures'],
     "    for var, checks in sorted(_IRREVERSIBLE.items()):",
     "    for var, checks in sorted({}.items()):",
     'every invocation asserts that SD_AUTH_SECRET_PREVIOUS\'s own '
     'description still names the census SQL, the legacy_rows = 0 '
     'threshold, the code citation and the SILENT permanent loss -- '
     'anchored on consequence rather than on the literal string "4a", '
     'which is the anchor that rotted',
     'the five _IRREVERSIBLE arms for SD_AUTH_SECRET_PREVIOUS'),

    ('red-suite-notice-not-couldnotrun',
     'tools/red_suite_register_check.py', ['--selftest'],
     "        notices.append(" + NL + "            'no --from-run log",
     "        could_not_run.append(" + NL + "            'no --from-run log",
     'declining the optional whole-tree pass is a NOTICE on an exit-0 run, '
     'not a COULD NOT RUN -- those are different claims and conflating them '
     'made every ordinary run exit 2',
     'cases 1, 6 and 10 -- 10 is the one that matters: a notice must never '
     'hide a real finding'),

    ('suite-lock-liveness',
     'tools/run_all_tests.py', ['--selftest'],
     "            state, why = lock_owner(raw)",
     "            state, why = ('unknown', 'ablated')",
     'acquire_lock tests whether the recorded pid is ALIVE before reclaiming. '
     'Removing it restores the age-only rule, which reclaimed a LIVE run\'s '
     'lock past 15 minutes -- measured on a real run: pid 17876 still alive '
     'at 16.1, 29.9, 54.0, 73.7, 93.4 and 134.9 minutes against a 15.0-minute '
     'ceiling, on a run that took 235 minutes end to end',
     'L1 and the 10-hour arm beside it'),

    ('suite-lock-owner-scoped-release',
     'tools/run_all_tests.py', ['--selftest'],
     "    if pid != os.getpid():" + NL + "        say('REFUSING to release pid",
     "    if False:" + NL + "        say('REFUSING to release pid",
     'release_lock removes the lock only when THIS process wrote it. '
     'Unconditional, it is what tests/run_suite_lock_probe.py:81 uses to '
     '"start from a known state" -- and that probe is PART of this suite, so '
     'every full run deleted its own lock partway through and spent the rest '
     'unprotected. Observed: the lock vanished at 10:45 on a run that started '
     '08:12 and exited 12:07',
     'L4'),

    # ── THIS ONE PUTS THE PRE-b15 VALUE BACK, not a wider band ────────────
    # The first recipe widened _FLOOR_LITERAL_SLACK to 0.99 and reported
    # UNPROVEN -- correctly, and it was measuring the wrong thing. F1 fails
    # when the literal is too LOW; widening the band only makes F1 unable to
    # fail, which is not the defect. The LAYER is the raised literal and F1 is
    # its arm, so the ablation restores the literal that was really there and
    # watches F1 go red. That is the failing-first proof in its proper
    # direction.
    ('floor-literal-stale-370',
     'tools/run_all_tests.py', ['--selftest'],
     "_MIN_TEST_FILES_FLOOR = 800",
     "_MIN_TEST_FILES_FLOOR = 370",
     'the last-resort floor literal tracks the real tracked count, and F1 '
     'fails when it falls more than 15% below it. 370 against a measured 811 '
     'is 441 files that could have been deleted with the ratchet file gone '
     'and nothing announcing it -- and the ratchet\'s own comment asked twice '
     'for a human cadence that never existed',
     'F1'),

    ('subject-sha-width-none-not-zero',
     'tools/tier_a_review_gate.py', ['--selftest'],
     "    except Exception:                                            "
     "# noqa: BLE001" + NL + "        return None",
     "    except Exception:                                            "
     "# noqa: BLE001" + NL + "        return 0",
     '_extra_file_count returns None, never 0, when git cannot say how many '
     'files beyond the record\'s set the anchored commit touched. Writing 0 '
     'would publish "this commit changed exactly the record\'s files" -- a '
     'claim nobody checked, which is PR 1.11 in a JSON field',
     'the None-not-0 arm, and the --list render that prints WIDTH UNKNOWN '
     'rather than nothing'),

    ('reseat-window-author-time',
     'tools/tier_a_review_gate.py', ['--selftest'],
     "            + chr(31) + '%aI' + chr(31) + '%cI', '--name-only']",
     "            + chr(31) + '%cI' + chr(31) + '%cI', '--name-only']",
     'the 6-hour weak-basis reseat window is measured against the commit\'s '
     'AUTHOR time. A rebase rewrites committer time and leaves author time '
     'alone, and every commit in this clone has been rebased -- measured, 102 '
     'of 200 recent commits have the two differing and 13 of 500 differ by '
     'more than the window itself, worst 13.4h. Wrong in BOTH directions: a '
     'record opened six minutes after its commit reads 10h away and is '
     'REFUSED, and every commit swept into one rebase lands in the same '
     'committer minute so a DIFFERENT commit can fall inside the window',
     'the four b15 reseat-window arms'),

    # ── THE LAYER IS AT TWO CALL SITES AND THE FIRST RECIPE ONLY HIT ONE ──
    # Ablating `subprocess.run(..., env=CHILD_ENV)` alone reported UNPROVEN,
    # because the three fixtures drive drive_verify's RUNNER seam and the
    # runner half was still passing CHILD_ENV. Same trap as b14's
    # `fail-closed-target`, where one layer implemented twice survived either
    # half being removed -- except inverted: here the arms see only the half
    # the first recipe left alone. The layer is "the child gets a utf-8
    # environment", it is written in two places, and an ablation of it has to
    # remove both. The real subprocess path then has NO arm of its own, which
    # is recorded as a finding rather than papered over with a tautology.
    ('batch-manifest-child-env',
     'tools/batch_manifest.py', ['--fixtures'],
     "        return runner(cmd, CHILD_ENV)",
     "        return runner(cmd, None)",
     'drive_upload_verify.py is spawned with PYTHONIOENCODING=utf-8 and '
     'PYTHONUTF8=1, because this process reconfiguring its OWN streams does '
     'nothing for a subprocess -- the child encodes at cp1252 and dies on '
     'the first em-dash in the handoff line it quotes, and cmd_close reports '
     'that crash as the Drive verify FAILING',
     'the three CHILD_ENV fixtures'),
)

# Recorded but NOT run here, each with the reason. A deferred ablation named
# with its recipe is a different thing from one nobody thought of.
DEFERRED = (
    ('sf-events-exactly-once', 'tools/citation_anchor_rot_check.py',
     '(no substring swap -- see why below)', '(no substring swap)',
     'NO LONGER DEFERRED AND NO LONGER DEFERRABLE, corrected 2026-10-16 '
     '(cc b16). The subject of this recipe, tools/sf_events_anchor_check.py, '
     'was DELETED on 2026-10-15 -- citation_anchor_rot_check.py supersedes '
     'it, both tools agreeing on 8 anchors / 8 resolving exactly once / 0 '
     'not on the day of the retirement. Leaving the old recipe here would '
     'have printed a runnable-looking substring swap against a path that no '
     'longer exists, which is item 8 (nothing announces the day a check '
     'stops testing anything) arriving inside the ablation record itself. '
     'THE ABLATION IS NOT LOST, IT MOVED AND GOT STRONGER: the exactly-once '
     'rule now lives behind the module-level hook _COUNT_IS_FINDING at '
     'citation_anchor_rot_check.py:79 precisely so it can be REMOVED rather '
     'than rewritten, and `python tools/citation_anchor_rot_check.py '
     '--ablation` drives it per ARM. A1-zero-count and A2-two-counts are '
     'the two arms this recipe was trying to reach. Run THAT, not this.'),
)


def run(file_rel, argv):
    """-> (exit_code, tail). The tool's own self-test, in the real clone."""
    p = subprocess.run([sys.executable, os.path.join(REPO, file_rel)] + argv,
                       cwd=REPO, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT,
                       env=dict(os.environ, PYTHONIOENCODING='utf-8',
                                PYTHONUTF8='1'))
    txt = p.stdout.decode('utf-8', 'replace')
    tail = [ln for ln in txt.split(NL) if ln.strip()][-1:] or ['(no output)']
    return p.returncode, tail[0].strip()[:150]


def one(name, file_rel, argv, old, new, what, arms):
    path = os.path.join(REPO, file_rel)
    print('')
    print('  %s' % name)
    print('    layer : %s' % what)
    print('    arms  : %s' % arms)
    src = io.open(path, encoding='utf-8', newline='').read()
    n = src.count(old)
    if n != 1:
        print('    COULD NOT RUN -- the old substring occurs %d time(s), not '
              'exactly 1. A swap that matched twice would ablate the wrong '
              'thing and a swap that matched nothing would ablate nothing '
              'and report a load-bearing layer. Nothing was changed.' % n)
        return 'COULD-NOT-RUN'
    rc0, t0 = run(file_rel, argv)
    if rc0 != 0:
        print('    COULD NOT RUN -- baseline is exit %d (%s), so any change '
              'below could not be attributed to this layer. Nothing was '
              'changed.' % (rc0, t0))
        return 'COULD-NOT-RUN'
    print('    baseline        exit 0  %s' % t0)
    print('    (if this is killed now: restore %s from git)' % file_rel)
    try:
        io.open(path, 'w', encoding='utf-8', newline='').write(
            src.replace(old, new, 1))
        rc1, t1 = run(file_rel, argv)
    finally:
        io.open(path, 'w', encoding='utf-8', newline='').write(src)
    rc2, t2 = run(file_rel, argv)
    print('    ablated         exit %d  %s' % (rc1, t1))
    print('    restored        exit %d  %s' % (rc2, t2))
    if rc2 != 0:
        print('    CONTAMINATED -- the restore did not bring the baseline '
              'back, so this measurement says nothing. Check the file.')
        return 'CONTAMINATED'
    if rc1 == 0:
        print('    NOTHING CAUGHT IT -- this layer is UNPROVEN: it can be '
              'removed today and not one arm notices.')
        return 'UNPROVEN'
    print('    LOAD-BEARING')
    return 'LOAD-BEARING'


def main(argv):
    only = argv[0] if argv else None
    print('b15 ablation driver -- the b12-b14 tools/ layers whose tools have')
    print('no --ablation mode of their own. Pass/fail/pass per layer; a')
    print('restore that does not bring the baseline back is CONTAMINATED and')
    print('the measurement is discarded rather than reported.')
    results = {}
    for case in CASES:
        if only and case[0] != only:
            continue
        results[case[0]] = one(*case)
    print('')
    print('  DEFERRED, with the recipe recorded so it is not lost:')
    for name, f, _o, _n, why in DEFERRED:
        print('    %-24s %s' % (name, f))
        print('      %s' % why)
    print('')
    unproven = [k for k, v in results.items() if v == 'UNPROVEN']
    broken = [k for k, v in results.items()
              if v in ('CONTAMINATED', 'COULD-NOT-RUN')]
    print('  %d measured: %d load-bearing, %d UNPROVEN, %d could-not-tell'
          % (len(results), sum(1 for v in results.values()
                               if v == 'LOAD-BEARING'),
             len(unproven), len(broken)))
    if unproven:
        print('  UNPROVEN: %s' % ', '.join(unproven))
    if broken:
        print('  COULD NOT TELL: %s -- NOT folded into either count'
              % ', '.join(broken))
    return 1 if (unproven or broken) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
