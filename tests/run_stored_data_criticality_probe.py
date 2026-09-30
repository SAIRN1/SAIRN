"""tools/stored_data_criticality_check.py must DENY, not just agree.

`docs/STORED-DATA-CRITICALITY.md` is clean on the day it is written, so a gate
whose findings are clean has by construction never refused anything and nobody
knows whether it can. This file makes it refuse, arm by arm.

WRITTEN BEFORE THE TOOL AND THE DOCUMENT, deliberately, and the first run of
this file was RED with `MISSING` on both paths. A probe written after its
subject is a probe whose arms were shaped by what the subject already does.

── WHY A SECOND TABLE EXISTS AT ALL ────────────────────────────────────────
`docs/CRITICALITY-TIERS.md` tiers RESOURCES, and that is now a mechanical
ruling rather than a preference: `tools/criticality_tier_check.py` enforces a
bijection in both directions against `api/_resources/*.js`, and its own refusal
message says `The unit of this table is the registry.` So a device-local
`localStorage` key cannot have a row there -- adding one prints `NOT A RESOURCE`
and turns `tests/run_criticality_tier_probe.py` RED on main.

Two such keys carry an A-class risk anyway. `sen_evv_queue` is, while a device
is offline, the ONLY copy of wage-determining EVV clock events joined to a
client's home coordinate; `law_strike_log` is built to answer a Batson
challenge and one cache clear removes it. The register cannot hold them and the
existing venue with teeth -- an app's `notSynced` declaration plus
`tools/local_only_collection_check.py` -- records that a key is device-local and
carries NO TIER. So the platform could say *"this lives on one device"* and
could not say *"and losing it loses a wage-determining record."*

THE SEPARATE TABLE IS THE NARROW OPTION AND IT IS CHOSEN BECAUSE OF WHAT IT
DOES NOT TOUCH. Extending the register's unit to stored data changes the unit
for all 391 rows -- the mistake that register already made once, at app
granularity, and corrected. So the register's bijection is left exactly as it
is, and the new table's OWN checker refuses any row whose key IS a registered
resource. The two tables are disjoint by arm, not by intention.

── EVERY ARM MUTATES A COPY IN A THROWAWAY WORKTREE ────────────────────────
Never this clone. This repo established that a probe which edits tracked files
is indistinguishable from residue when it dies.

── EVERY ANCHOR IN THIS FILE IS DERIVED ────────────────────────────────────
Read the value out of the fixture, assert the read found exactly one thing, and
assert the mutation changed the bytes. `tests/run_criticality_tier_probe.py`
went stale twice on typed-in anchors (a hardcoded `| **10** |` among them) and
cody measured FOUR anchor-staleness incidents across this family in one day.
A mutation that planted nothing must fail LOUDLY about its ANCHOR and never
quietly about its subject.

Run: python tests/run_stored_data_criticality_probe.py
"""
# Declares, for tools/checker_control_check.py, which checker(s) this file is
# the control for. Attribution is DECLARED rather than inferred.
CONTROLS_FOR = ['stored_data_criticality_check.py']

import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REL_DOC = os.path.join('docs', 'STORED-DATA-CRITICALITY.md')
REL_TOOL = os.path.join('tools', 'stored_data_criticality_check.py')

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name + ('' if cond else '  ' + detail))
    if not cond:
        fails.append(name)


# ── FAIL CLOSED ON AN ABSENT SUBJECT (PR §1.11) ─────────────────────────────
# Not `if os.path.isfile(tool):`. A gate that skips when its subject is missing
# reports a pass it never performed, and nothing downstream can tell that from
# a real one. Name the path, say the check did not run, and fail.
_absent = [p for p in (REL_TOOL, REL_DOC) if not os.path.isfile(os.path.join(REPO, p))]
if _absent:
    print('COULD NOT RUN -- these do not exist, so NOTHING was verified:')
    for p in _absent:
        print('  MISSING  %s' % p)
    print('This is a FAILURE, not a skip. A probe that passes when its subject '
          'is absent is the defect this repo names five times.')
    sys.exit(2)


def run(wt, extra=()):
    r = subprocess.run([sys.executable, os.path.join(wt, REL_TOOL)] + list(extra),
                       cwd=wt, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    return r.returncode, (r.stdout or '') + (r.stderr or '')


print('stored-data criticality -- the checker must refuse a table that has '
      'stopped describing the platform\n')

wt = tempfile.mkdtemp(prefix='sairn-stored-')
shutil.rmtree(wt, ignore_errors=True)
add = subprocess.run(['git', '-C', REPO, 'worktree', 'add', '-q', '--detach', wt, 'HEAD'],
                     capture_output=True, text=True, encoding='utf-8', errors='replace')
if add.returncode != 0:
    print('SKIPPED: could not create a worktree -- nothing was verified.')
    print(add.stderr.strip()[:300])
    sys.exit(3)

DOC = os.path.join(wt, REL_DOC)
try:
    # ── THE SUBJECT IS THE WORKING TREE, NOT HEAD ──────────────────────────
    # The worktree is created at HEAD so the mutations have a clean, isolated
    # place to happen -- but what a run of this probe should judge is the doc
    # and the tool AS THEY ARE ON DISK. A probe that reads HEAD passes on the
    # committed version of a file the author has since broken, and reports RED
    # about a missing file on the very first run of a tests-first build. So both
    # are copied over the worktree's copies, and the copy is asserted to have
    # landed rather than assumed.
    for rel in (REL_DOC, REL_TOOL):
        dst = os.path.join(wt, rel)
        if not os.path.isdir(os.path.dirname(dst)):
            os.makedirs(os.path.dirname(dst))
        shutil.copyfile(os.path.join(REPO, rel), dst)
        assert os.path.isfile(dst), 'copy did not land: %s' % rel

    ORIGINAL = io.open(DOC, encoding='utf-8', newline='').read()

    # ── ARM 1: THE CONTROL, FIRST ──────────────────────────────────────────
    # So a refusal in a later arm cannot be confused with a checker that
    # refuses everything it is shown.
    rc, out = run(wt)
    check('the shipped table PASSES', rc == 0, out[-500:])
    check('...and it reports what it counted', 'STORED_DATA_ROWS:' in out)
    check('...and it reports the criteria lock on the real run',
          'criteria lock:' in out,
          'a self-test that only runs when asked is a control with a shorter name')
    check('...and it does NOT claim the tiers are correct',
          'It does not say the tier is right' in out,
          'a checker that implies more reach than it has is worse than none')
    check('...and it says out loud that it is NOT a completeness check',
          'not a completeness check' in out,
          'this tool cannot enumerate every localStorage key on the platform, '
          'and a reader who assumes it did would read a silence as coverage')

    def mutate(new_text, label, marker, want_rc=1):
        # ONE SITE, EVERY ARM: A MUTATION THAT PLANTED NOTHING IS A FAILURE
        # ABOUT THE ANCHOR, NOT ABOUT THE SUBJECT.
        assert new_text != ORIGINAL, (
            'ANCHOR STALE: %r produced a document identical to the original, so '
            'nothing was planted and the arm below would be measuring an '
            'unmutated table. Re-derive the anchor from the fixture rather than '
            'typing it.' % label)
        io.open(DOC, 'w', encoding='utf-8', newline='').write(new_text)
        rc2, out2 = run(wt)
        check(label, rc2 == want_rc and marker in out2,
              'exit=%s (wanted %s) marker_present=%s' % (rc2, want_rc, marker in out2))
        io.open(DOC, 'w', encoding='utf-8', newline='').write(ORIGINAL)

    def one_row(key):
        needle = '| `%s` |' % key
        hits = [l for l in ORIGINAL.split('\n') if l.startswith(needle)]
        assert len(hits) == 1, ('fixture invalid: %r matches %d rows, not 1 -- '
                                'widen the anchor rather than letting replace() '
                                'pick' % (needle, len(hits)))
        return hits[0]

    # Both rows read out of the fixture, never typed. If either row is renamed
    # or removed this assert fires about the ANCHOR.
    EVV = one_row('sen_evv_queue')
    STRIKE = one_row('law_strike_log')

    # ── ARM 2: A ROW WHOSE KEY IS A REGISTERED RESOURCE ────────────────────
    # THE BOUNDARY ARM, and the reason this table can exist without touching
    # the register's bijection. If a key is in some app's `resources` array it
    # belongs in docs/CRITICALITY-TIERS.md and having it in BOTH is how two
    # tables start disagreeing about one thing.
    #
    # The registered name is READ OUT OF THE REGISTRY, not typed -- a typed one
    # would go stale the day that resource is renamed and this arm would then
    # be measuring a nonexistent key rather than an overlap.
    def a_registered_name():
        src = io.open(os.path.join(wt, 'api', '_resources', 'sairnsenior.js'),
                      encoding='utf-8').read()
        m = re.search(r'resources:\s*\[(.*?)\]', src, re.S)
        assert m, 'fixture invalid: no resources array in api/_resources/sairnsenior.js'
        body = re.sub(r'(?m)//.*$', '', m.group(1))
        names = re.findall(r"""['"]([a-z][a-z0-9_]{2,60})['"]""", body)
        assert names, 'fixture invalid: resources array parsed to zero names'
        return names[0]

    REGISTERED = a_registered_name()
    mutate(ORIGINAL.replace(EVV, EVV.replace('`sen_evv_queue`', '`%s`' % REGISTERED, 1), 1),
           'a row whose key IS a registered resource is refused', 'IS A RESOURCE')

    # ── ARM 3: A GHOST KEY ─────────────────────────────────────────────────
    # A tier for a key that does not exist in the app it names. `sd_owner_pin`
    # is the real instance of this shape -- one repo-wide reference, inside its
    # own keep-list, no writer and no reader -- and a table that tiered it
    # would be protecting nothing while looking like it protected something.
    mutate(ORIGINAL.replace(EVV, EVV.replace('`sen_evv_queue`',
                                             '`sen_no_such_key_at_all`', 1), 1),
           'a key that appears nowhere in the app it names is refused', 'GHOST KEY')

    # ── ARM 4: A TIER OUTSIDE A/B/C ────────────────────────────────────────
    # The tier cell is read positionally, so a malformed one must refuse rather
    # than be coerced. Anchored on the row's OWN integrity cell, re-read here.
    _tier = re.match(r'^\| `law_strike_log` \| `[^`]+` \| \*\*([ABC])\*\* \|', STRIKE)
    assert _tier, ('fixture invalid: law_strike_log row does not match the '
                   'two-axis shape this arm mutates -- %r' % STRIKE[:160])
    mutate(ORIGINAL.replace(STRIKE,
                            STRIKE.replace('**%s**' % _tier.group(1), '**Z**', 1), 1),
           'a tier outside A/B/C is refused', 'BAD TIER')

    # ── ARM 5: A TIER A ROW WITH NO EVIDENCE ───────────────────────────────
    # The same rule the register carries: a tier asserted with no evidence is a
    # label. The evidence cell is the LAST one, and it is emptied rather than
    # deleted so the cell COUNT stays right and the arm tests the evidence rule
    # instead of accidentally testing the shape rule.
    def blank_last_cell(row):
        assert row.endswith(' |'), 'fixture invalid: row does not end in a pipe'
        parts = row.rstrip()[:-1].rsplit('|', 1)
        assert len(parts) == 2 and parts[1].strip(), (
            'fixture invalid: last cell already empty, so this arm would plant '
            'nothing -- %r' % row[-120:])
        return parts[0] + '|  |'

    mutate(ORIGINAL.replace(EVV, blank_last_cell(EVV), 1),
           'a Tier A row with no citation in its evidence cell is refused',
           'NO EVIDENCE')

    # ── ARM 6: NO DECLARATION VENUE ────────────────────────────────────────
    # The venue cell is the whole point of this table over the register: for a
    # device-local key the only existing mechanism is the app's `notSynced`
    # declaration, and UNDECLARED is an ALLOWED value that must be SAID. What
    # is refused is a venue cell that says neither -- a silence where the
    # finding goes.
    _venue = re.match(r'^(\| `sen_evv_queue` \|(?:[^|]*\|){5})([^|]*)(\|.*)$', EVV)
    assert _venue, ('fixture invalid: the sen_evv_queue row does not have the '
                    '8-cell shape this arm indexes into -- %r' % EVV[:200])
    assert _venue.group(2).strip(), 'fixture invalid: venue cell is already empty'
    mutate(ORIGINAL.replace(EVV, _venue.group(1) + ' see the notes below '
                            + _venue.group(3), 1),
           'a venue cell naming no recognised venue is refused', 'NO VENUE')

    # ── ARM 6b: A VENUE CELL THAT CLAIMS A DECLARATION THERE ISN'T ─────────
    # The venue column is only worth a column if the claim in it is checkable
    # against the app's real `notSynced` list. Both shipping rows are UNDECLARED
    # and that is TRUE; a row that said `notSynced` would be asserting a
    # declaration nothing verifies, which is the exact shape 41 register rows
    # carried when they claimed a gate that did not exist.
    #
    # THE VENUE MUST LEAD THE CELL, which is why this plants it at the front.
    # An earlier version of venue_token scanned the venue list in declaration
    # order and read the real UNDECLARED cell as notSynced -- because that cell
    # names notSynced to explain there is none -- so it refused an honest row as
    # a false claim. Position is the criterion and both readings are locked in
    # the tool's fixtures.
    mutate(ORIGINAL.replace(EVV, _venue.group(1) + ' `notSynced` in '
                            '`api/_resources/sairnsenior.js` ' + _venue.group(3), 1),
           'a venue cell claiming a notSynced declaration that does not exist '
           'is refused', 'VENUE FALSE')

    # ── ARM 7: THE HEADER MUST STATE ITS UNIT OUT LOUD ─────────────────────
    # The open-work row that authorised this table named this as a condition:
    # tiering a new unit "must be said out loud in the header, because tiering
    # the wrong unit is the mistake the register already made once". So the
    # sentence is load-bearing and the checker refuses a table that drops it.
    #
    # THE SENTENCE IS READ OUT OF THE TOOL, NOT TYPED HERE. Typing it would put
    # the same string in three files and make this arm go green the day somebody
    # tightened the tool's constant -- which is what happened on the first run:
    # the short prefix `The unit of this table is` also matches the register's
    # own refusal message, which the table quotes verbatim, so the anchor found
    # two lines and this assert fired about the ANCHOR rather than the subject.
    _us = re.search(r"^UNIT_SENTENCE = '([^']+)'$",
                    io.open(os.path.join(wt, REL_TOOL), encoding='utf-8').read(),
                    re.M)
    assert _us, 'fixture invalid: the tool declares no UNIT_SENTENCE constant'
    _unit = [l for l in ORIGINAL.split('\n') if _us.group(1) in l]
    assert len(_unit) == 1, ('fixture invalid: the tool\'s UNIT_SENTENCE %r '
                             'appears %d times in the table, not 1 -- an arm '
                             'that removes one of two occurrences plants '
                             'nothing' % (_us.group(1), len(_unit)))
    mutate(ORIGINAL.replace(_unit[0], '', 1),
           'a table that does not state its own unit is refused', 'NO UNIT STATED')

    # ── ARM 8: AN ESCAPED PIPE IS CONTENT ──────────────────────────────────
    # Not a column boundary. The register's own index row tripped exactly this,
    # and `|| 0` inside a cell leaked a 6-cell row into 8 three times in one
    # session. Planting an escaped pipe must NOT change the cell count, so this
    # arm expects a PASS -- it is the one arm whose success is exit 0.
    io.open(DOC, 'w', encoding='utf-8', newline='').write(
        ORIGINAL.replace(EVV, EVV.replace('cap 200', r'cap 200 \| FIFO', 1), 1))
    rc8, out8 = run(wt)
    check('an ESCAPED pipe inside a cell is content, not a boundary',
          rc8 == 0 and 'STORED_DATA_ROWS:2' in out8,
          'exit=%s -- counting it as a boundary turns one row into nine cells '
          'and every positional read after it is wrong' % rc8)
    io.open(DOC, 'w', encoding='utf-8', newline='').write(ORIGINAL)

    # ── ARM 9: THE PAIRED POSITIVE ─────────────────────────────────────────
    # Without this, every arm above is satisfied by a tool that returns 1 on
    # anything. Independence convention §6: assert the refusals AND assert the
    # thing being refused is still being counted.
    rc9, out9 = run(wt)
    check('THE PAIRED POSITIVE: both real rows are still parsed and counted',
          rc9 == 0 and 'STORED_DATA_ROWS:2' in out9,
          'exit=%s out=%s' % (rc9, out9[-300:]))
    check('...and both keys are named in the output',
          'sen_evv_queue' in out9 and 'law_strike_log' in out9)

    # ── ARM 10: FAIL CLOSED WITH THE REGISTRY GONE ─────────────────────────
    # The boundary arm depends on api/_resources being readable. If it is not,
    # the tool cannot tell an overlap from a clean table -- so it must exit 2
    # COULD NOT RUN and never 0. A gate wrapped in `if isfile(...)` does not
    # skip one check, it reports a pass it never performed.
    RES = os.path.join(wt, 'api', '_resources')
    HIDDEN = RES + '-hidden'
    os.rename(RES, HIDDEN)
    try:
        rc10, out10 = run(wt)
        check('with api/_resources GONE it exits 2 COULD NOT RUN, never 0',
              rc10 == 2 and 'COULD NOT RUN' in out10,
              'exit=%s -- fail-open here is a reported pass that never happened'
              % rc10)
        check('...and it names the path it could not read',
              'api/_resources' in out10)
    finally:
        os.rename(HIDDEN, RES)

    # ── ARM 11: THE CRITERIA LOCK IS LOAD-BEARING ──────────────────────────
    # Break one fixture expectation in the TOOL and the tool must refuse to
    # judge anything real. Discipline §1: criteria locked against synthetic
    # fixtures before they are pointed at real data, and a lock that cannot
    # fail is decoration.
    TOOLP = os.path.join(wt, REL_TOOL)
    tsrc = io.open(TOOLP, encoding='utf-8', newline='').read()
    assert 'CRITERIA_VERSION' in tsrc, ('fixture invalid: the tool declares no '
                                        'CRITERIA_VERSION, so its lock is not '
                                        'versioned')
    _fx = re.search(r"\('venue', '(notSynced[^']*)', True,", tsrc)
    assert _fx, ('fixture invalid: no positive venue fixture of the expected '
                 'shape in the tool -- re-derive this anchor')
    broken = tsrc.replace("('venue', '%s', True," % _fx.group(1),
                          "('venue', '%s', False," % _fx.group(1), 1)
    assert broken != tsrc, 'ANCHOR STALE: the fixture edit planted nothing'
    io.open(TOOLP, 'w', encoding='utf-8', newline='').write(broken)
    rc11, out11 = run(wt)
    check('a failing criteria lock is exit 2 and judges NOTHING real',
          rc11 == 2 and 'CRITERIA LOCK FAILED' in out11
          and 'NOTHING REAL WAS JUDGED' in out11,
          'exit=%s out=%s' % (rc11, out11[-300:]))
    check('...and a failing lock does NOT also print a clean row count',
          'STORED_DATA_ROWS:' not in out11,
          'a verdict printed beside a broken lock is the verdict a reader keeps')
    io.open(TOOLP, 'w', encoding='utf-8', newline='').write(tsrc)

finally:
    subprocess.run(['git', '-C', REPO, 'worktree', 'remove', '--force', wt],
                   capture_output=True, text=True)
    shutil.rmtree(wt, ignore_errors=True)

print()
if fails:
    print('%d ARM(S) FAILED: %s' % (len(fails), ', '.join(fails)))
else:
    print('ALL ARMS PASS -- the checker refuses each shape above and still '
          'counts the two real rows.')
sys.exit(1 if fails else 0)
