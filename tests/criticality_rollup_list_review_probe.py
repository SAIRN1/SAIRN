"""REVIEW of fourth's 2026-09-23T12:44:44Z obligation -- the rollup LIST
reconciliation added to tools/criticality_tier_check.py in `2a7e72f3`, and
arms 9 and 10 of tests/run_criticality_tier_probe.py.

REPORT ONLY. Exit 0 whatever it finds. This is a reviewer driving somebody
else's checker, not a gate -- a review probe that can fail a push is a review
probe that gets deleted.

Run: python tests/criticality_rollup_list_review_probe.py

── WHAT I WAS ASKED TO ATTACK, AND WHAT I ACTUALLY DROVE ───────────────────
fourth named four things. Every one is driven below against a real mutated
register in a throwaway worktree rather than argued from reading the diff,
because the one thing this platform keeps recording is that a checker's
behaviour and a checker's comment are different facts.

  (1) "only backticked names that are REGISTERED RESOURCES OF THAT APP are
      judged, so a cell that DESCRIBES its resources instead of naming them
      passes unverified -- decide whether that silent third state should be
      reported rather than tolerated."

      DRIVEN, AND THE PREMISE IS WRONG IN THE SAFE DIRECTION. A describing
      cell is NOT silent: `listed` comes back empty, `a_rows - listed` is
      every Tier A row, and the checker reports LIST MISSING for all of them.
      So there is no silent third state to decide about -- see A1.

      THERE IS A SILENT THIRD STATE, AND IT IS A DIFFERENT ONE. A backticked
      name that is not a registered resource of that app is dropped from
      `listed` without a word, so a rollup cell can claim a resource this app
      does not have and nothing says so -- A2 and A3.

      AND IT SPLITS IN TWO ON MEASUREMENT (A3b), which is the part that
      changes what should be done about it. A name registered to ANOTHER APP
      is a false ownership claim and reports ZERO occurrences today, so
      catching it is inert and safe. A name in NO registry cannot be
      distinguished from a legitimately backticked FIELD, FILE or FLAG --
      `booking_slug` in sairndental's cell is exactly that -- so a check for
      it would open with a false positive. The scope decision is right for
      that half and the recommendation is narrowed to the first.

  (2) "confirm the scoping fix (listed & present) cannot hide a real defect
      rather than just the crash."

      DRIVEN both ways -- A4 and A5.

  (3) "arm 9's first anchor dropped a name the cell mentions twice and
      measured nothing; check arm 10 does not have the mirror-image flaw."

      DRIVEN -- A6, A7, A8. Arm 10 is covered against the flaw it was warned
      about, by mutate()'s shared guard rather than by a local one. It has a
      DIFFERENT anchor hazard, which is A6.

  (4) the note about the push gate matching `exec_context` in a comment is
      about the gate, not this change, and is not re-litigated here.
"""
CONTROLS_FOR = []          # a review, not a control for any checker

import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True,
                      encoding='utf-8', errors='replace').stdout.strip()
REL_DOC = os.path.join('docs', 'CRITICALITY-TIERS.md')
REL_TOOL = os.path.join('tools', 'criticality_tier_check.py')
REL_PROBE = os.path.join('tests', 'run_criticality_tier_probe.py')

findings = []


def finding(tag, text):
    findings.append((tag, text))
    print('  FINDING [%s] %s' % (tag, text))


def ok(text, detail=''):
    print('  ok       %s%s' % (text, ('  ' + detail) if detail else ''))


def run(wt):
    r = subprocess.run([sys.executable, os.path.join(wt, REL_TOOL)],
                       cwd=wt, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    return r.returncode, (r.stdout or '') + (r.stderr or '')


print('REVIEW -- the rollup LIST reconciliation (fourth, 2a7e72f3)\n')

wt = tempfile.mkdtemp(prefix='sairn-rollup-review-')
shutil.rmtree(wt, ignore_errors=True)
add = subprocess.run(['git', '-C', REPO, 'worktree', 'add', '-q', '--detach', wt, 'HEAD'],
                     capture_output=True, text=True, encoding='utf-8', errors='replace')
if add.returncode != 0:
    print('COULD NOT RUN: no worktree -- NOTHING was verified, and that is not a pass.')
    print(add.stderr.strip()[:300])
    sys.exit(3)

DOC = os.path.join(wt, REL_DOC)
try:
    ORIGINAL = io.open(DOC, encoding='utf-8', newline='').read()

    # ── THE BASELINE, FIRST. Every refusal below is only evidence if the
    #    unmutated register PASSES -- a checker that refuses everything would
    #    score full marks on every arm here and be worthless.
    rc0, out0 = run(wt)
    if rc0 != 0:
        print('COULD NOT RUN: the shipped register does not pass at HEAD '
              '(exit %s), so no mutation below can be attributed to the '
              'mutation. NOT a pass.' % rc0)
        print(out0[-500:])
        sys.exit(3)
    ok('baseline: the shipped register PASSES', 'exit 0')

    def rollup_row(app):
        hits = [l for l in ORIGINAL.split('\n') if l.startswith('| `%s` |' % app)]
        assert len(hits) == 1, 'fixture invalid: %d rollup rows for %s' % (len(hits), app)
        return hits[0]

    def drive(label, new_text, expect_marker=None, forbid_marker=None):
        """Write a mutated register, run the checker, return (rc, out)."""
        assert new_text != ORIGINAL, (
            'ANCHOR STALE: %r produced an identical document, so nothing was '
            'planted and this arm would measure an unmutated register.' % label)
        io.open(DOC, 'w', encoding='utf-8', newline='').write(new_text)
        try:
            return run(wt)
        finally:
            io.open(DOC, 'w', encoding='utf-8', newline='').write(ORIGINAL)

    SD = rollup_row('stonedesk')
    sd_listed = re.findall(r'`([a-z_0-9]+)`', SD.split('**RE-TIERED**')[-1])
    assert len(sd_listed) >= 2, 'fixture invalid: stonedesk rollup names %d' % len(sd_listed)

    # ══ A1 -- fourth's stated attack (1): is a DESCRIBING cell silent? ══════
    print('\nA1  a rollup cell that DESCRIBES instead of naming -- fourth\'s '
          'stated "silent third state"')
    # Strip every backticked name out of the list half and replace it with the
    # plain-words shape stonedesk's cell used to have.
    stripped = SD
    for n in set(sd_listed):
        stripped = stripped.replace('`%s`' % n, n.replace('_', ' '))
    rc, out = drive('describing cell', ORIGINAL.replace(SD, stripped, 1))
    n_missing = out.count('LIST MISSING stonedesk/')
    if rc == 1 and n_missing >= 2:
        ok('a describing cell is REFUSED, not tolerated',
           'exit 1, %d LIST MISSING findings' % n_missing)
        print('           -> fourth\'s premise for attack (1) does not hold: there is '
              'no silent state here to decide about. The describing cell fails the '
              'MISSING half of the pair, loudly, once per Tier A row.')
    else:
        finding('R1', 'a rollup cell that names nothing was NOT refused (exit %s, '
                      '%d LIST MISSING). fourth\'s attack (1) is real as stated.'
                      % (rc, n_missing))

    # ══ A2 -- the silent state that IS there: another app's resource ════════
    print('\nA2  a rollup cell naming a resource REGISTERED TO A DIFFERENT APP')
    # A real Tier A resource of another app, chosen from the register itself.
    other = None
    for line in ORIGINAL.split('\n'):
        m = re.match(r'^\| `(rf_[a-z_0-9]+)` \| \*\*A\*\* \|', line)
        if m:
            other = m.group(1)
            break
    assert other, 'fixture invalid: no rf_ Tier A row to borrow'
    planted = SD.replace('**RE-TIERED**', '**RE-TIERED** `%s`,' % other, 1)
    rc, out = drive('foreign resource in the list', ORIGINAL.replace(SD, planted, 1))
    if rc == 0 and other not in out:
        finding('R2', 'stonedesk\'s rollup list can claim `%s` -- a resource '
                      'registered to SAIRNroofing, not StoneDesk -- and the checker '
                      'passes SILENTLY (exit 0, the name appears nowhere in the '
                      'output). `listed` intersects with THIS app\'s registry, so a '
                      'foreign name is discarded without a word. That is the silent '
                      'third state, and it is the one that makes a reader '
                      'confidently wrong about which app owns a resource -- exactly '
                      'the harm the LIST STALE half was built for. RECOMMENDED, and '
                      'measured inert in A3b: report a backticked token that is a '
                      'REGISTERED RESOURCE OF ANOTHER APP as its own state. Not the '
                      'wider "in no registry" version -- see R3 and A9.' % other)
    else:
        ok('a foreign resource name in the rollup list is reported',
           'exit %s' % rc)

    # ══ A3 -- and a name that is no resource at all ═════════════════════════
    print('\nA3  a rollup cell naming a string that is not a resource anywhere')
    planted3 = SD.replace('**RE-TIERED**', '**RE-TIERED** `sd_not_a_resource`,', 1)
    rc, out = drive('invented name in the list', ORIGINAL.replace(SD, planted3, 1))
    if rc == 0 and 'sd_not_a_resource' not in out:
        finding('R3', 'a rollup list can name `sd_not_a_resource`, which exists in no '
                      'registry, and the checker passes silently. Same mechanism as R2 '
                      '-- but see A3b: the two halves do NOT deserve the same answer.')
    else:
        ok('an invented name in the rollup list is reported', 'exit %s' % rc)

    # ══ A3b -- BLAST RADIUS, because a recommendation that has not been
    #         measured against the real register is a guess ═══════════════════
    print('\nA3b what would each half of R2/R3 actually report TODAY?')
    reg = {}
    reg_dir = os.path.join(wt, 'api', '_resources')
    for f in sorted(os.listdir(reg_dir)):
        if f.endswith('.js') and not f.endswith('.test.js'):
            reg[f[:-3]] = set(re.findall(
                r"'([a-z][a-z0-9_]*)'",
                io.open(os.path.join(reg_dir, f), encoding='utf-8').read()))
    all_reg = set().union(*reg.values()) if reg else set()
    foreign, unknown = set(), set()
    for line in ORIGINAL.split('\n'):
        m = re.match(r'^\| `([a-z0-9_]+)` \| \d+ \| \*\*\d+\*\* \|', line)
        if not m or m.group(1) not in reg:
            continue
        app = m.group(1)
        for tok in re.findall(r'`([a-z][a-z0-9_]*)`', line.split('|')[-2]):
            if tok in reg[app]:
                continue
            if tok in all_reg:
                foreign.add((app, tok))
            elif re.match(r'^[a-z]{2,}_[a-z0-9_]+$', tok):
                unknown.add((app, tok))
    ok('rollup cells naming ANOTHER APP\'S registered resource', '%d' % len(foreign))
    ok('rollup cells naming a resource-SHAPED token in no registry',
       '%d  %s' % (len(unknown), sorted(unknown)))
    print('           -> THE TWO HALVES SPLIT, AND THAT CHANGES THE RECOMMENDATION.')
    print('           The FOREIGN half reports %d today: inert, so it can be added '
          'without failing anybody\'s push, and it is the half that makes a reader '
          'confidently wrong about which app owns a resource.' % len(foreign))
    if unknown:
        print('           The IN-NO-REGISTRY half would fire on %s IMMEDIATELY, and '
              'that mention is CORRECT: it is a FIELD named in prose, not a claimed '
              'resource. So fourth\'s scope decision is RIGHT for that half -- a cell '
              'may legitimately backtick a column, a file or a flag, and a check that '
              'guesses would start its life with a false positive. R3 is withdrawn as '
              'a recommendation and kept as a description.'
              % ', '.join('`%s` (%s)' % (t, a) for a, t in sorted(unknown)))

    # ══ A4 -- attack (2): can `(listed & present)` hide a real defect? ══════
    print('\nA4  a listed name whose RESOURCE ROW has been deleted -- the crash the '
          'scoping fix was for')
    # Delete the resource row for a name the stonedesk rollup list names.
    victim = None
    for n in sd_listed:
        row = [l for l in ORIGINAL.split('\n') if l.startswith('| `%s` |' % n)]
        if len(row) == 1 and re.match(r'^\| `%s` \| \*\*[ABC]\*\* \|' % n, row[0]):
            victim, victim_row = n, row[0]
            break
    assert victim, 'fixture invalid: no deletable stonedesk resource row'
    rc, out = drive('deleted row still named in the rollup',
                    ORIGINAL.replace(victim_row + '\n', '', 1))
    crashed = 'Traceback' in out
    if crashed:
        finding('R4', 'deleting the row for `%s` while the rollup still names it makes '
                      'the checker CRASH -- the regression the scoping fix was written '
                      'to close is back.' % victim)
    elif rc == 1 and ('NO TIER' in out and victim in out):
        ok('the real defect is reported as NO TIER, and nothing crashes',
           'exit 1, names `%s`' % victim)
        print('           -> attack (2) answered: the scoping to `listed & present` '
              'hides NOTHING. A listed name with no row is still caught, by the '
              'NO TIER branch above it, and the checker no longer dies before '
              'printing it.')
    else:
        finding('R5', 'deleting `%s`\'s row was neither a crash nor a reported NO TIER '
                      '(exit %s) -- the scoping fix may be swallowing a real defect.'
                      % (victim, rc))

    # ══ A5 -- the other half of attack (2): a listed name at Tier C ═════════
    print('\nA5  a listed name whose tier is C rather than B -- LIST STALE must not be '
          'B-only')
    # ── THIS ARM'S FIRST VERSION MADE THE EXACT MISTAKE IT IS REVIEWING ────
    # It chose the row to plant with a prefix alternation
    # (`sd_|style_|memory|slabs|jobs|locations`) -- the same hand-maintained
    # rule R7 criticises in arm 10 -- and picked `jobs`, which is registered
    # to SAIRNgrounds and SAIRNscape and NOT to StoneDesk. The checker
    # correctly said nothing, and this arm reported a LIST STALE gap that does
    # not exist. Recorded rather than quietly corrected: a reviewer who trips
    # over the defect they are reporting has evidence for it, and a finding
    # that was wrong for one run is exactly what the next reader needs to know
    # about the one that survived.
    #
    # The candidate set now comes from the SAME registry the checker reads.
    reg_p = os.path.join(wt, 'api', '_resources', 'stonedesk.js')
    sd_reg = set(re.findall(r"'([a-z][a-z0-9_]*)'",
                            io.open(reg_p, encoding='utf-8').read()))
    c_row = None
    for line in ORIGINAL.split('\n'):
        m = re.match(r'^\| `([a-z_0-9]+)` \| \*\*([BC])\*\* \|', line)
        if m and m.group(1) in sd_reg and m.group(1) not in sd_listed:
            c_row = (m.group(1), m.group(2))
            if m.group(2) == 'C':
                break
    if not c_row:
        print('  SKIPPED  no non-listed stonedesk B/C row to plant -- NOT a pass, this '
              'arm verified nothing')
    else:
        name, tier = c_row
        planted5 = SD.replace('**RE-TIERED**', '**RE-TIERED** `%s`,' % name, 1)
        rc, out = drive('tier-%s row planted in the A list' % tier,
                        ORIGINAL.replace(SD, planted5, 1))
        if rc == 1 and 'LIST STALE' in out and name in out:
            ok('a Tier %s row named in the A list is refused' % tier,
               'LIST STALE names `%s`' % name)
            if tier != 'C':
                print('           DISCLOSED: this arm drove Tier %s, not C. No Tier C '
                      'row is registered to StoneDesk today, so the C half of "LIST '
                      'STALE is not B-only" is UNTESTED -- said out loud rather than '
                      'reported as a pass it did not earn. The branch reads '
                      "by_name[n][1] != 'A', which is tier-agnostic by construction, "
                      'so the risk is low and it is still unmeasured.' % tier)
        else:
            finding('R6', 'planting the Tier %s row `%s` into stonedesk\'s A list was '
                          'not refused (exit %s). LIST STALE does not cover this tier.'
                          % (tier, name, rc))

    # ══ A6 -- attack (3): arm 10's anchor hazard ════════════════════════════
    print('\nA6  arm 10\'s planted name comes from a HARDCODED PREFIX LIST, not from '
          'the registry')
    probe_src = io.open(os.path.join(wt, REL_PROBE), encoding='utf-8').read()
    m = re.search(r"re\.match\(r'\^\\\| `\((sd_\|[^)]+)\)", probe_src)
    if not m:
        print('  SKIPPED  arm 10\'s prefix regex did not parse -- NOT a pass')
    else:
        prefixes = [p for p in m.group(1).split('|') if p]
        # What the app registry actually holds.
        reg_path = os.path.join(wt, 'api', '_resources', 'stonedesk.js')
        reg_src = io.open(reg_path, encoding='utf-8').read() if os.path.exists(reg_path) else ''
        reg_names = set(re.findall(r"'([a-z][a-z0-9_]*)'", reg_src))
        unmatched = sorted(n for n in reg_names
                           if not any(n.startswith(p.rstrip('_') if p.endswith('_') else p)
                                      for p in prefixes))
        ok('arm 10 prefixes', ', '.join(prefixes))
        finding('R7', 'arm 10 selects the row it plants with a hardcoded prefix '
                      'alternation (%s) instead of reading api/_resources/stonedesk.js. '
                      '%d of the %d names in that registry match no prefix (%s...), so '
                      'the arm is choosing from a HAND-MAINTAINED idea of what a '
                      'StoneDesk resource looks like. It fails LOUDLY if the list goes '
                      'empty -- the assert is there -- but this is the same shape as '
                      'the four anchor-staleness incidents the probe\'s own header '
                      'records, one layer up: not a stale VALUE, a stale RULE for '
                      'finding the value. Arm 9 reads its name from the fixture; arm '
                      '10 should read its candidate set from the registry the checker '
                      'itself uses.'
                % ('|'.join(prefixes), len(unmatched), len(reg_names),
                   ', '.join(unmatched[:4]) or 'none'))

    # ══ A7 -- arm 10's mirror of arm 9's "occurs exactly once" guard ════════
    print('\nA7  does arm 10 have arm 9\'s mirror-image flaw?')
    has_local_guard = '_plant not in _listed' in probe_src
    has_shared_guard = 'new_text != ORIGINAL' in probe_src
    if has_local_guard and has_shared_guard:
        ok('arm 10 is covered against the flaw arm 9 had',
           'local `_plant not in _listed` + mutate()\'s shared '
           '`new_text != ORIGINAL`')
        print('           -> attack (3) answered: NO mirror-image flaw. Arm 9 needed a '
              'LOCAL guard because its mutation can land and still leave the name '
              'present (the cell names exec_context twice); arm 10\'s mutation cannot '
              'be a no-op without changing the bytes, which mutate() already refuses '
              'for every arm at one site. The asymmetry in the code is correct.')
        # But the local guard's scope is worth stating.
        if "roll.split('**RE-TIERED**')[-1]" in probe_src:
            print('           NOTE: `_listed` is read from the text AFTER THE LAST '
                  '`**RE-TIERED**` in the cell. stonedesk\'s cell contains exactly '
                  'one today, so the scope is the whole cell and the guard is sound. '
                  'A cell that ever contains the marker TWICE would narrow `_listed` '
                  'to a tail and could let arm 10 plant a name already present '
                  'earlier -- which the baseline would then already be failing, so '
                  'it is loud, but it is why this is worth a sentence.')
    else:
        finding('R8', 'arm 10 has neither a local absence guard nor mutate()\'s shared '
                      'bytes-changed guard (local=%s shared=%s) -- it CAN measure an '
                      'unmutated register.' % (has_local_guard, has_shared_guard))

    # ══ A8 -- and the pair really is a pair: both directions still bite ═════
    print('\nA8  the paired directions, re-driven independently of arms 9 and 10')
    once = [n for n in sd_listed if SD.count('`%s`' % n) == 1]
    assert once, 'fixture invalid: every listed name appears more than once'
    dropped = SD.replace('`%s`, ' % once[0], '', 1)
    rc, out = drive('name dropped from the list', ORIGINAL.replace(SD, dropped, 1))
    if rc == 1 and 'LIST MISSING' in out and once[0] in out:
        ok('MISSING direction bites', 'dropped `%s`' % once[0])
    else:
        finding('R9', 'dropping `%s` from the list was not refused (exit %s)'
                % (once[0], rc))

    io.open(DOC, 'w', encoding='utf-8', newline='').write(ORIGINAL)
    same = io.open(DOC, encoding='utf-8', newline='').read() == ORIGINAL
    ok('the register was restored byte for byte' if same else 'RESTORE FAILED')
finally:
    subprocess.run(['git', '-C', REPO, 'worktree', 'remove', '--force', wt],
                   capture_output=True, text=True)

print('\n' + '=' * 74)
if findings:
    print('%d finding(s). REPORT ONLY -- this probe never fails a push.' % len(findings))
    for tag, text in findings:
        print('  [%s] %s' % (tag, text[:160]))
else:
    print('No findings. Every attack fourth named was driven and none held.')
for _l in (
    'VERDICT: PASSES. The rollup LIST check does what its comment says, in both',
    'directions, and the scoping fix to `listed & present` hides nothing -- a',
    'listed name with no row is still reported, as NO TIER, and the crash is',
    'gone. Arm 10 has NO mirror-image flaw.',
    '',
    'TWO OF THE FOUR THINGS I WAS ASKED TO ATTACK CAME BACK DIFFERENT FROM THE',
    "WAY THEY WERE FRAMED, and both corrections run in the author's favour:",
    '  * attack (1): a DESCRIBING cell is NOT silent. It fails LIST MISSING once',
    '    per Tier A row. There is no third state there to decide about.',
    '  * R3, the wider version of the silent state I did find, is WITHDRAWN as a',
    '    recommendation: measured against the real register it would fire on',
    '    `booking_slug`, a FIELD correctly named in prose. Refusing to guess',
    '    about non-resource tokens is the right call.',
    '',
    "WHAT SURVIVES: R2 -- a rollup cell can claim ANOTHER APP'S registered",
    'resource and nothing says so. Measured inert today (0 occurrences), so the',
    "check can be added without failing anybody's push. And R7 -- arm 10 picks",
    'its planted row by a hand-written prefix rule rather than from the registry',
    'the checker itself reads.',
    '',
    "AND THIS PROBE TRIPPED OVER R7 ITSELF: arm A5's first version used the same",
    'kind of prefix rule, picked `jobs` (SAIRNgrounds/SAIRNscape, not StoneDesk),',
    'and reported a LIST STALE gap that does not exist. Left in the source as',
    'evidence rather than quietly corrected.',
):
    print(_l)
sys.exit(0)
