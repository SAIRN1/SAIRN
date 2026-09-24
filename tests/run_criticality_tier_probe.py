"""tools/criticality_tier_check.py must DENY, not just agree.

The register is clean today, and a gate whose findings are clean has by
construction never refused anything -- so nobody knows whether it can.

REWRITTEN 2026-09-10 when the register moved from app-level to RESOURCE-level
tiering. The old arms anchored on app rows (`sairnvet.html` being Tier B, then
`stonedesk-catalog.html` being UNTIERED) and BOTH failed loudly as those rows
changed during the day, which is the probe working -- but the rows themselves
are gone now, so the arms are rebuilt against the structure rather than moved
again.

EVERY ARM MUTATES A COPY IN A THROWAWAY WORKTREE, never this clone. Deliberate:
this repo established that a probe which edits tracked files is
indistinguishable from residue when it dies, and the register is a file a reader
would trust on sight.

── EVERY ANCHOR IN THIS FILE IS DERIVED, AND THAT IS NOT A PREFERENCE ──────
THIS FILE HAS GONE STALE TWICE, both times because somebody correctly
re-tiered a row. The arms anchored on app rows in 2026-09-10; arm 6 anchored
on a hardcoded `| **10** |` and went red on 2026-09-22 when StoneDesk's A
count moved to 12. A count is a FACT ABOUT THE TABLE, so an arm that types it
beside the table is asserting that nobody will do the work this register
exists to record.

AND THE FAMILY IS WIDER THAN THIS FILE. Measured by cody, 2026-09-23: FOUR
anchor-staleness incidents in ONE day -- 14fa1a4d (session_gate_table_probe),
395d4040 (route-record ANCHOR-2), e9797e02 (arm 6 here) and f48e7d57 (arm 4
here, landed after the first note was written). TWO OF THE FOUR ARE IN THIS
FILE. The family also carries tool-bugs item 11, ec64365a. My own note said
three in two days and understated it in both dimensions.

So the standing rule for anything added here: READ the value out of the
fixture, ASSERT the read found exactly one thing, and ASSERT the mutation
changed the bytes. An arm that plants nothing must fail LOUDLY about its
ANCHOR and never quietly about its subject -- a red arm nobody can act on is
how a probe stops being read at all.

Run: python tests/run_criticality_tier_probe.py
"""
# Declares, for tools/checker_control_check.py, which checker(s) this file is
# the control for. Attribution is DECLARED rather than inferred because three
# inference models were each wrong within an hour of being written.
CONTROLS_FOR = ['criticality_tier_check.py']

import io
import re
import os
import shutil
import subprocess
import sys
import tempfile

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True, encoding='utf-8', errors='replace').stdout.strip()
REL_DOC = os.path.join('docs', 'CRITICALITY-TIERS.md')
REL_TOOL = os.path.join('tools', 'criticality_tier_check.py')

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name + ('' if cond else '  ' + detail))
    if not cond:
        fails.append(name)


def run(wt):
    r = subprocess.run([sys.executable, os.path.join(wt, REL_TOOL)],
                       cwd=wt, capture_output=True, text=True, encoding='utf-8', errors='replace')
    return r.returncode, (r.stdout or '') + (r.stderr or '')


print('criticality tiers -- the checker must refuse a register that has stopped '
      'describing the platform\n')

wt = tempfile.mkdtemp(prefix='sairn-crit-')
shutil.rmtree(wt, ignore_errors=True)
add = subprocess.run(['git', '-C', REPO, 'worktree', 'add', '-q', '--detach', wt, 'HEAD'],
                     capture_output=True, text=True, encoding='utf-8', errors='replace')
if add.returncode != 0:
    print('SKIPPED: could not create a worktree -- nothing was verified.')
    print(add.stderr.strip()[:300])
    sys.exit(3)

DOC = os.path.join(wt, REL_DOC)
try:
    ORIGINAL = io.open(DOC, encoding='utf-8', newline='').read()

    # ── ARM 1: THE CONTROL, FIRST, so a refusal later cannot be confused with
    #    a checker that refuses everything.
    rc, out = run(wt)
    check('the shipped register PASSES', rc == 0, out[-400:])
    check('...and it reports what it counted', 'RESOURCES_REGISTERED:' in out)
    check('...and it does NOT claim the tiers are correct',
          'It does not say the tier is right' in out,
          'a checker that implies more reach than it has is worse than none')

    def mutate(new_text, label, marker):
        # ── ONE SITE, EVERY ARM: A MUTATION THAT PLANTED NOTHING IS A
        # ── FAILURE ABOUT THE ANCHOR, NOT ABOUT THE SUBJECT ──────────────
        # Arm 6 read `roll.replace('| **10** |', ...)`. When StoneDesk's A
        # count moved to 12 the replace matched NOTHING, the document written
        # here was byte-identical to the original, the checker passed --
        # correctly, it had nothing to complain about -- and the arm reported
        # FAIL because the marker never appeared. A red arm about the wrong
        # thing is how a probe stops being read.
        #
        # one_row() already refuses an anchor that matches zero or many ROWS.
        # This is the other half and it covers every arm at once, including
        # arms not written yet: whatever an arm did to the text, the text has
        # to have CHANGED.
        assert new_text != ORIGINAL, (
            'ANCHOR STALE: %r produced a document identical to the original, '
            'so nothing was planted and the arm below would be measuring an '
            'unmutated register. Re-derive the anchor from the fixture rather '
            'than typing it.' % label)
        io.open(DOC, 'w', encoding='utf-8', newline='').write(new_text)
        rc2, out2 = run(wt)
        check(label, rc2 == 1 and marker in out2,
              'exit=%s marker_present=%s' % (rc2, marker in out2))
        io.open(DOC, 'w', encoding='utf-8', newline='').write(ORIGINAL)

    def one_row(needle):
        hits = [l for l in ORIGINAL.split('\n') if l.startswith(needle)]
        assert len(hits) == 1, ('fixture invalid: %r matches %d rows, not 1 -- widen '
                                'the anchor rather than letting replace() pick'
                                % (needle, len(hits)))
        return hits[0]

    # ── ARM 2: A REGISTERED RESOURCE WITH NO ROW ───────────────────────────
    # The one that matters most: a resource is added and nobody states its
    # worst case. It must not pass by not being mentioned.
    inv = one_row('| `sd_invoices` |')
    mutate(ORIGINAL.replace(inv + '\n', '', 1),
           'a registered resource with NO ROW is refused', 'NO TIER')

    # ── ARM 3: A ROW FOR SOMETHING THAT IS NOT A RESOURCE ──────────────────
    # The unit of the table is the registry. A row for an unregistered key
    # would make the counts mean two things at once.
    mutate(ORIGINAL.replace(inv, '| `zz_not_a_resource` | **A** | nothing | nothing |\n'
                            + inv, 1),
           'a row for something not in any registry is refused', 'NOT A RESOURCE')

    # ── ARM 4: A TIER OUTSIDE THE VOCABULARY ───────────────────────────────
    # One scheme, taken from the SOUP register. A row inventing HIGH or P1 is
    # how a second scheme starts.
    mutate(ORIGINAL.replace(inv, inv.replace('| **A** |', '| **CRITICAL** |', 1), 1),
           'a tier outside A/B/C is refused', 'BAD TIER')

    # ── ARM 5: A TIER A ROW WITH NOTHING TO CHECK IT AGAINST ───────────────
    # THE LINE THAT KEEPS THE A TIER HONEST. B and C are classified by the
    # stated rule; A is hand-verified. That difference has to be enforceable
    # rather than promised, or A degrades into rule-guessing.
    parts = inv.rsplit('|', 2)
    stripped = parts[0] + '|  |'
    mutate(ORIGINAL.replace(inv, stripped, 1),
           'a Tier A row with an EMPTY evidence cell is refused', 'NO EVIDENCE')

    # ── ARM 6: A ROLLUP THAT DISAGREES WITH ITS OWN DETAIL ─────────────────
    # ── THE HARDCODED 10 WENT STALE AND THIS ARM WENT RED (2026-09-22) ────
    # It read `roll.replace('| **10** |', '| **3** |')`. StoneDesk's Tier A
    # count was 10 when that was written; sd_exec_msgs and sd_negotiated_prices
    # were re-tiered afterwards and it is 12. The replace matched NOTHING, the
    # mutated document was byte-identical to the original, the checker passed
    # -- correctly, it had nothing to complain about -- and the arm reported
    # FAIL because the marker never appeared.
    #
    # RED IS THE SAFE DIRECTION AND IT IS STILL WRONG: the arm was failing for
    # a reason that has nothing to do with the property it guards, so a reader
    # learns to expect one red arm here, which is how a probe stops being read
    # at all. And it is the SECOND thing in this file to go stale by somebody
    # else correctly re-tiering a row -- the count is a fact about the table,
    # so it must be DERIVED from the table rather than typed beside it.
    #
    # The mutation now reads whatever the A count is and writes a different
    # number, and it ASSERTS the edit landed. A mutation that plants nothing
    # must be a loud failure about the ANCHOR, never a quiet one about the
    # subject.
    # ── THE HAZARD I NAMED WAS NOT THE HAZARD (cody, routed 2026-09-23) ───
    # My note asked whether this takes the wrong cell if a row grows more
    # `| **N** |`-shaped cells. MEASURED BY CODY: 0 of 404 backticked rows
    # carry more than one, and the Status cell's bolded PROSE cannot match --
    # the pattern needs a pipe-delimited span of pure digits. Bolding the B or
    # C count is harmless too, because the A count is still leftmost.
    #
    # WHAT ACTUALLY BREAKS IT IS BOLDING CELL 1, the registered-resources
    # count, which puts a pure-number bold cell BEFORE the A count. Driven on
    # the real stonedesk row:
    #
    #   | `stonedesk` |   36  | **12** | ...   the bare pattern takes 12  (right)
    #   | `stonedesk` | **36**| **12** | ...   the bare pattern takes 36  (WRONG)
    #
    # 36 is the resources count. The arm would then plant 43 against a row
    # whose A count is 12, the checker would refuse it for the right reason by
    # accident, and the arm would pass while testing something else.
    #
    # SO THE A CELL IS ANCHORED TO THE ONE BEFORE IT rather than to being
    # first. `| N | **N** |` is the A count BY POSITION -- the bolded number
    # immediately after a plain number -- and under the hazard above it matches
    # NOTHING and the assert fires. Loud about the anchor, never quiet about
    # the subject, which is this file's standing rule for its own reason.
    #
    # AND THE MATCH MUST BE UNIQUE. Measured across the real table: 16 rollup
    # rows, and the shape occurs exactly once in every one of them. A second
    # occurrence means the row is not what this arm thinks it is.
    roll = one_row('| `stonedesk` |')
    _m6 = re.findall(r'\| \d+ \| \*\*\d+\*\* \|', roll)
    assert len(_m6) == 1, (
        'fixture invalid: the stonedesk rollup row carries %d cells shaped '
        '`| N | **N** |` and this arm needs exactly one. Either the row lost '
        'its A-count cell or something before it was bolded -- either way the '
        'arm is not testing what it says it tests: %r' % (len(_m6), roll))
    m6 = re.search(r'\| \d+ \| \*\*(\d+)\*\* \|', roll)
    a_count = int(m6.group(1))
    wrong = a_count + 7           # any number the rows cannot support
    # The pair is matched for POSITION and only the bolded half is rewritten,
    # so the resources count it is anchored to is left exactly as it was.
    rolled = roll.replace(m6.group(0),
                          m6.group(0).replace('**%d**' % a_count,
                                              '**%d**' % wrong, 1), 1)
    assert rolled != roll, 'the rollup mutation did not land'
    mutate(ORIGINAL.replace(roll, rolled, 1),
           'a rollup count that contradicts the rows is refused (A=%d -> %d)'
           % (a_count, wrong), 'COUNT')

    # ── ARM 7: A HALF-TIERED APP ───────────────────────────────────────────
    # A resource row under an app whose rollup says NOT YET RE-TIERED. Without
    # this, a partly-done app reads as an untouched one.
    mutate(ORIGINAL.replace(roll, roll.replace('**RE-TIERED**', '**NOT YET RE-TIERED**', 1), 1),
           'resource rows under a NOT-YET-RE-TIERED app are refused', 'HALF DONE')

    # ── ARM 8: AN APP NOBODY HAS EVEN SAID "NOT YET" ABOUT ─────────────────
    # Caught a real gap in the register's own first draft: sairncash had a
    # registry and no rollup line.
    cash = one_row('| `sairncash` |')
    mutate(ORIGINAL.replace(cash + '\n', '', 1),
           'an app with a registry and NO ROLLUP LINE is refused', 'NO ROLLUP')

    # ── ARMS 9 AND 10: THE ROLLUP LIST, BOTH DIRECTIONS (added 2026-09-23) ──
    # The list half of a rollup row was unguarded from the day this file was
    # written until today, and a sweep found it drifted in SIX of sixteen apps
    # while every COUNT was correct. These two arms exist so that cannot go
    # unnoticed again -- and they are PAIRED deliberately, because a check that
    # only catches a forgotten name would pass a list that names a row which is
    # no longer A, which is the direction that makes a reader confidently wrong.
    #
    # BOTH ANCHORS ARE DERIVED FROM THE FIXTURE. This file records four
    # anchor-staleness incidents in one day, two of them in this file, so the
    # names below are read out of the stonedesk rollup rather than typed.
    _listed = re.findall(r'`([a-z_0-9]+)`', roll.split('**RE-TIERED**')[-1])
    assert len(_listed) >= 2, (
        'fixture invalid: the stonedesk rollup names %d resources and these arms '
        'need at least 2. If that cell went back to describing its resources in '
        'plain words instead of naming them, these arms are not testing what they '
        'say -- and neither is the checker.' % len(_listed))

    # ARM 9 -- a Tier A row the list forgot.
    #
    # THE NAME MUST OCCUR EXACTLY ONCE IN THE CELL, and the first version of
    # this arm did not check that. It dropped `exec_context`, which the cell's
    # trailing note names a SECOND time in prose, so the set the checker builds
    # still contained it, the register still passed, and the arm reported FAIL
    # about the checker when the fault was its own anchor. Caught on the first
    # run. Same family as the four anchor-staleness incidents this file records
    # -- a probe that mutates a name appearing twice is measuring nothing.
    _once = [n for n in _listed if roll.count('`%s`' % n) == 1]
    assert _once, (
        'fixture invalid: every resource named in the stonedesk rollup appears '
        'more than once in that cell, so dropping any one of them leaves the '
        'name present and this arm would assert against an unchanged set')
    _drop = _once[0]
    # ── THE DROP MUST WORK ON THE LAST NAME TOO (repaired 2026-09-23, hank) ──
    # This was `roll.replace('`name`, ', '', 1)` -- name, comma, space -- which
    # is how every name in the list is written EXCEPT THE LAST ONE. The arm
    # went red the day somebody's edit made the first exactly-once name the
    # final element: `sd_crm` had no trailing `, `, the replace planted
    # nothing, and the assert below fired. THAT IS THE GUARD WORKING -- a
    # mutation that planted nothing failing about its ANCHOR rather than
    # quietly about its subject -- and the anchor was the thing that was
    # wrong. Found while re-running this control over an unrelated register
    # edit; it was red at HEAD before that edit and is not caused by it.
    #
    # Three spellings tried in order: mid-list, last-in-list, and alone.
    _rolled9 = roll
    for _pat in ('`%s`, ' % _drop, ', `%s`' % _drop, '`%s`' % _drop):
        if _pat in _rolled9:
            _rolled9 = _rolled9.replace(_pat, '', 1)
            break
    assert _rolled9 != roll, 'the list mutation did not land for `%s`' % _drop
    assert '`%s`' % _drop not in _rolled9, (
        '`%s` survived the drop, so the arm is not testing a missing name' % _drop)
    mutate(ORIGINAL.replace(roll, _rolled9, 1),
           'a Tier A row MISSING from the rollup list is refused (dropped `%s`)' % _drop,
           'LIST MISSING')

    # ARM 10 -- a name in the list that is no longer Tier A. The planted name is
    # read out of the RESOURCE ROWS, so it is a real B row of this app rather
    # than an invented string the checker would ignore as prose.
    _b = [l for l in ORIGINAL.split('\n')
          if re.match(r'^\| `(sd_|stonedesk_|exec_|style_|jobs|locations|memory|slabs)[a-z_0-9]*` \| \*\*B\*\* \|', l)]
    assert _b, ('fixture invalid: no Tier B stonedesk row found to plant, so arm 10 '
                'would be asserting against nothing')
    _plant = re.match(r'^\| `([a-z_0-9]+)`', _b[0]).group(1)
    assert _plant not in _listed, (
        'fixture invalid: %r is already in the rollup list, so planting it would '
        'change nothing' % _plant)
    mutate(ORIGINAL.replace(roll, roll.replace('**RE-TIERED**',
                                               '**RE-TIERED** `%s`,' % _plant, 1), 1),
           'a rollup list naming a row that is NOT Tier A is refused (planted `%s`)' % _plant,
           'LIST STALE')

    # ── ARMS 11-14: THE FIXER, DRIVEN (2026-09-24) ────────────────────────
    # `--fix-rollup-list` exists because arm 9's finding kept being TRUE. The
    # LIST MISSING arm landed 2026-09-23 and caught the same omission five
    # times in the following day: every catch real, every fix correct, and
    # nothing about the fifth different from the first, because promoting a
    # row leaves a derived sentence somewhere else for a human to retype.
    #
    # A FIXER IS A WRITER AND GETS THE HARDER CONTROLS, not the same ones. It
    # is not enough that the check passes afterwards -- a fixer that rewrote
    # the whole cell, or the whole file, would also make the check pass. So
    # these arms assert what it did NOT touch as hard as what it did.
    def run_fix(wt_):
        r = subprocess.run([sys.executable, os.path.join(wt_, REL_TOOL),
                            '--fix-rollup-list'],
                           cwd=wt_, capture_output=True, text=True,
                           encoding='utf-8', errors='replace')
        return r.returncode, (r.stdout or '') + (r.stderr or '')

    # ARM 11 -- on a register with nothing missing it writes NOTHING. A fixer
    # that reformats a correct file on every run makes every unrelated diff
    # unreadable, which is how a tool stops being run.
    rc11, out11 = run_fix(wt)
    check('the fixer is a NO-OP on a register that is already right',
          rc11 == 0 and io.open(DOC, encoding='utf-8', newline='').read() == ORIGINAL,
          'exit=%s bytes_changed=%s' % (rc11, io.open(DOC, encoding='utf-8', newline='').read() != ORIGINAL))
    check('...and it says so rather than printing nothing',
          'Nothing to insert' in out11, out11[-200:])

    # ARM 12 -- the real one: drop a name, run the fixer, and the document must
    # come back BYTE-IDENTICAL. Not "the check passes" -- that is the weaker
    # claim, and every one of this repo's regenerate-the-file incidents would
    # have satisfied it.
    #
    # THE NAME IS CHOSEN SEPARATELY FROM ARM 9's AND THE REASON IS A REAL
    # FAILURE. Arm 9 takes the first exactly-once name and falls back to
    # dropping the bare `name` when neither `name`, nor , `name` matches. On
    # this register that picked `sd_crm`, which is inside a bold annotation --
    # so the drop removed the NAME and left the annotation, and no correct
    # fixer could round-trip that: it re-inserts alphabetically and the bytes
    # differ. The arm was red about the fixer and the fault was the fixture.
    # A byte-identical claim is only meaningful over a PLAIN list member, so
    # this picks one and fails loudly about its anchor if the register has
    # none left.
    #
    # AND IT MUST BE A REAL TIER A ROW, not merely a backticked token. `_listed`
    # is a raw backtick scrape of the cell, so it also contains prose tokens --
    # the first run of this arm picked `val` out of an annotation, dropped it,
    # and the register still PASSED, because the checker only judges names that
    # are registered resources of the app. The arm then failed about the fixer
    # for doing nothing to a document that had nothing wrong with it. Same
    # family as arm 9's own `exec_context` near-miss: a mutation that is not a
    # mutation of the SUBJECT.
    _a_rows = set(re.findall(r'^\| `([a-z_0-9]+)` \| \*\*A\*\* \|',
                             ORIGINAL, re.M))
    _plain = [n for n in _once
              if n in _a_rows
              and (('`%s`, ' % n) in roll or (', `%s`' % n) in roll)]
    assert _plain, (
        'fixture invalid: the stonedesk rollup has no plain list member -- every '
        'exactly-once name carries an annotation, so a dropped name cannot be '
        'restored byte-identically by ANY fixer and this arm would be asserting '
        'something false about a correct tool')
    _fixdrop = _plain[0]
    _rolled12 = roll
    for _pat in ('`%s`, ' % _fixdrop, ', `%s`' % _fixdrop):
        if _pat in _rolled12:
            _rolled12 = _rolled12.replace(_pat, '', 1)
            break
    assert '`%s`' % _fixdrop not in _rolled12, (
        '`%s` survived the drop, so arm 12 is not testing a missing name' % _fixdrop)
    _fix_doc = ORIGINAL.replace(roll, _rolled12, 1)
    assert _fix_doc != ORIGINAL, 'ANCHOR STALE: arm 12 planted nothing'
    io.open(DOC, 'w', encoding='utf-8', newline='').write(_fix_doc)
    rc12a, _ = run(wt)
    check('arm 12 precondition: the mutated register is REFUSED before the fix',
          rc12a == 1, 'exit=%s -- if this passes, the fix below proves nothing' % rc12a)
    rc12, out12 = run_fix(wt)
    _after = io.open(DOC, encoding='utf-8', newline='').read()
    check('the fixer restores a dropped Tier A name BYTE FOR BYTE (`%s`)' % _fixdrop,
          rc12 == 0 and _after == ORIGINAL,
          'exit=%s identical=%s :: %s' % (rc12, _after == ORIGINAL, out12[-300:]))
    check('...and it names what it inserted rather than working silently',
          'INSERTED' in out12 and _fixdrop in out12, out12[-200:])
    rc12b, _ = run(wt)
    check('...and the checker itself now passes the fixed register', rc12b == 0)
    io.open(DOC, 'w', encoding='utf-8', newline='').write(ORIGINAL)

    # ARM 13 -- THE FIXER MUST NOT DELETE. LIST STALE is the other half of the
    # same arm and it is NOT derivable: a name listed whose row says B may
    # mean the row is wrong, not the list. Arm 10's mutation, run through the
    # fixer, must come out still planted and still refused.
    _stale_doc = ORIGINAL.replace(roll, roll.replace(
        '**RE-TIERED**', '**RE-TIERED** `%s`,' % _plant, 1), 1)
    assert _stale_doc != ORIGINAL, 'ANCHOR STALE: arm 13 planted nothing'
    io.open(DOC, 'w', encoding='utf-8', newline='').write(_stale_doc)
    run_fix(wt)
    _after13 = io.open(DOC, encoding='utf-8', newline='').read()
    rc13, out13 = run(wt)
    check('the fixer does NOT delete a LIST STALE name -- that one is a '
          'judgement and stays refused (`%s`)' % _plant,
          '`%s`' % _plant in _after13 and rc13 == 1 and 'LIST STALE' in out13,
          'still_present=%s exit=%s' % ('`%s`' % _plant in _after13, rc13))
    io.open(DOC, 'w', encoding='utf-8', newline='').write(ORIGINAL)

    # ARM 14 -- THE MUTATION CONTROL ON THE FIXER'S OWN GUARD. Drop a name AND
    # strip every backticked resource out of that cell, so there is no list to
    # insert into. The fixer must REFUSE and name the app; inserting into a
    # cell that describes its resources in prose would be inventing a list.
    _prose = roll
    for _n in sorted(_listed):
        _prose = _prose.replace('`%s`, ' % _n, '').replace(', `%s`' % _n, '').replace('`%s`' % _n, '')
    assert _prose != roll, 'ANCHOR STALE: arm 14 stripped nothing'
    io.open(DOC, 'w', encoding='utf-8', newline='').write(ORIGINAL.replace(roll, _prose, 1))
    _before14 = io.open(DOC, encoding='utf-8', newline='').read()
    rc14, out14 = run_fix(wt)
    check('the fixer REFUSES a rollup cell with no list in it, and says which app',
          rc14 == 1 and 'REFUSED' in out14 and 'stonedesk' in out14,
          'exit=%s :: %s' % (rc14, out14[-300:]))
    check('...and it wrote nothing at all while refusing',
          io.open(DOC, encoding='utf-8', newline='').read() == _before14)
    io.open(DOC, 'w', encoding='utf-8', newline='').write(ORIGINAL)

    check('the register was restored byte for byte after every arm',
          io.open(DOC, encoding='utf-8', newline='').read() == ORIGINAL)
finally:
    subprocess.run(['git', '-C', REPO, 'worktree', 'remove', '--force', wt],
                   capture_output=True, text=True, encoding='utf-8', errors='replace')
    shutil.rmtree(wt, ignore_errors=True)

here = subprocess.run(['git', '-C', REPO, 'status', '--porcelain', '--', REL_DOC],
                      capture_output=True, text=True, encoding='utf-8', errors='replace').stdout.strip()
check('this clone\'s own register is untouched', here == '', here)


# -- THE READER ITSELF, DRIVEN DIRECTLY. Added 2026-09-14. -----------------
# Every arm above runs the whole tool in a worktree, which is right for "does
# it deny". It cannot see WHICH NAMES the tool decided were registered, and
# that is exactly where the defect was: apps_with_registries() matched any line
# of the shape 'name', anywhere in the file, so it scraped the notSynced array
# -- the list of keys that DELIBERATELY never reach a server.
#
# And the answer depended on COMMENT PLACEMENT. sairnvet declares three
# local-only keys together; two carry trailing comments and were invisible, the
# third has its comment on the lines above and was scraped. The checker then
# reported "sairnvet/sv_audit_backed is registered and has no row" -- a finding
# produced entirely by where somebody put a //.
sys.path.insert(0, os.path.join(REPO, 'tools'))
import criticality_tier_check as C            # noqa: E402

_names, _err = C.resource_names(
    os.path.join(REPO, 'api', '_resources', 'sairnvet.js'))
check('the reader parses sairnvet at all', _err is None and _names, str(_err))
for _k in ('sv_audit_backed', 'sv_settings', 'sv_examrooms_turnover'):
    check('notSynced key %-22s is NOT a registered resource' % _k,
          _names is not None and _k not in _names,
          'notSynced is the list of things that never reach a server; counting '
          'one is the opposite of what registered means')
check('THE PAIRED POSITIVE: real resources ARE still counted, so the fix is not '
      'just a narrower reader that sees nothing',
      _names is not None and 'sv_controlled' in _names and len(_names) > 30,
      '%s names' % (len(_names) if _names else 0))

# ALL THREE FILE SHAPES PARSE. The first version of the narrowed reader knew
# only the multi-line array and reported the other two as a changed file shape,
# which was loud and wrong.
for _app, _why in (('sairnvet', 'multi-line array'),
                   ('sairncash', 'resources: [] -- explicitly empty, a real answer'),
                   ('sairncode', 'resources: RESOURCES -- a reference to a const')):
    _n, _e = C.resource_names(
        os.path.join(REPO, 'api', '_resources', _app + '.js'))
    check('%-11s parses (%s)' % (_app, _why), _e is None, str(_e))

# AND AN UNPARSEABLE FILE IS AN ERROR, NOT AN EMPTY APP -- returning zero names
# would make every resource in it vanish from the check and the app would read
# CLEAN, which is the fail-open direction from a completeness checker.
_n, _e = C.resource_names(os.path.join(REPO, 'tools', 'criticality_tier_check.py'))
check('a file with no resources array is an ERROR, not an app with no resources',
      _n is None and _e, 'returned %r / %r' % (_n, _e))

print('\n%s  run_criticality_tier_probe: %d failed'
      % ('FAILED' if fails else 'ok', len(fails)))
sys.exit(1 if fails else 0)
