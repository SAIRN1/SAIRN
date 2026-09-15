"""Does the Tier A review gate refuse, or does it only print?

    python tests/run_tier_a_review_gate_probe.py

THE ARM THAT MATTERS IS SECTION 2. A gate whose whole subject is somebody not
being told is the worst possible place for a check that passes by accident, so
every refusal below is driven with a REAL diff and the clean case is driven too
-- an arm that only ever sees findings would pass against a tool that returns 1
unconditionally.

SECTION 3 IS THE FAIL-CLOSED HALF, and it is the reason this file exists rather
than a smoke test. The gate reads its resource list out of
docs/CRITICALITY-TIERS.md. If that parse ever stops working the obvious failure
is an EMPTY SET, and an empty set makes every push clean -- the quietest way for
this to stop working, and exactly PR 1.11's defect. The tool must answer 2, and
2 must not be reachable by returning "no findings".

SECTION 4 IS THE ONE RULE A MACHINE CAN ACTUALLY CHECK about a review: that the
reviewer is not the author. Driven against a real register file with a
self-signed record planted in it.

NOTHING HERE MUTATES A TRACKED FILE. Every fixture is a temporary directory or a
string; the gate's inputs are a diff and two paths, so there is no need to
sabotage the real repo to test it -- and a probe that edits docs/ on a platform
where four sessions share a branch is a probe that loses somebody's work.
"""
import io
import json
import os
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import tier_a_review_gate as g                                   # noqa: E402

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        fails.append(name)


def diff_for(path, *lines):
    """A minimal but REAL unified diff -- same shape git produces, because the
    parser walks `+++` headers and hunk bodies and a hand-rolled approximation
    would let a parser bug pass."""
    body = '\n'.join('+' + ln for ln in lines)
    return ('diff --git a/%s b/%s\n--- a/%s\n+++ b/%s\n@@ -1,0 +1,%d @@\n%s\n'
            % (path, path, path, path, len(lines), body))


RES = {'sc_claims', 'sc_ar', 'dnt_patients', 'law_trusttx'}

print('\n1. it reads the REAL register and finds real Tier A names')
try:
    real = g.tier_a_resources()
except g.CouldNotTell as e:
    real = set()
    check('the real register parses', False, e)
check('the real register yields Tier A rows (%d)' % len(real), len(real) > 50, len(real))
check('...including the SAIRNcode billing records', {'sc_claims', 'sc_ar'} <= real,
      sorted(real)[:8])
check('...and NOT a Tier B name', 'sc_dme' not in real, 'sc_dme is in the Tier A set')

print('\n2. attribution is by HUNK, not by file')
hit = g.touched_tier_a(diff_for('api/x.js', "const a = 'sc_claims';"), RES)
check('a hunk naming sc_claims attributes it', list(hit) == ['sc_claims'], hit)
check('...to the file the +++ header named', hit.get('sc_claims') == ['api/x.js'], hit)

none = g.touched_tier_a(diff_for('api/x.js', "const a = 'sb_ts';"), RES)
check('a hunk naming NO Tier A resource attributes nothing', none == {}, none)

sub = g.touched_tier_a(diff_for('api/x.js', "const a = 'sc_claims_archive';"), RES)
check('SUBSTRING CONTROL: sc_claims_archive does NOT count as sc_claims', sub == {}, sub)
pre = g.touched_tier_a(diff_for('api/x.js', "const a = 'zz_sc_claims';"), RES)
check('...nor does a prefixed name', pre == {}, pre)

docs = g.touched_tier_a(diff_for('docs/CRITICALITY-TIERS.md', '| `sc_claims` | **A** |'), RES)
check('docs/ is excluded, so the register itself is not a Tier A change', docs == {}, docs)
sql = g.touched_tier_a(diff_for('sql/x.sql', 'create table sc_claims (...)'), RES)
check('sql/ is excluded', sql == {}, sql)
# ── THE WORKLOG FALSE POSITIVE, 2026-09-15, AND BOTH DIRECTIONS OF IT ───────
# The gate refused a push whose ONLY Tier-A-naming file was a root-level
# SAIRN-ACTIVE-WORK-*.md -- a worklog describing dnt_rollup in prose. Its own
# reasoning already covered that ("a document naming a resource is not code
# serving it"); the rule was keyed on the docs/ PREFIX rather than on what the
# file is, and every session's worklog lives at the repo root by convention.
wl = g.touched_tier_a(
    diff_for('SAIRN-ACTIVE-WORK-fourth.md', 'built the sc_claims roll-up today'), RES)
check('a root-level WORKLOG is not code serving a Tier A resource', wl == {}, wl)

md = g.touched_tier_a(diff_for('SAIRN-BACKLOG.md', 'sc_claims is still open'), RES)
check('...nor is any other root-level .md', md == {}, md)

MD = g.touched_tier_a(diff_for('README.MD', "'sc_claims'"), RES)
check('...and the test is case-insensitive on the extension', MD == {}, MD)

# THE OTHER DIRECTION, and it is the one that matters. Excluding prose must not
# start excluding code: a file whose NAME merely contains ".md" is not markdown,
# and a real handler must still count.
notmd = g.touched_tier_a(diff_for('api/sc-md-export.js', "'sc_claims'"), RES)
check('a .js whose name CONTAINS "md" is still code', notmd == {'sc_claims': ['api/sc-md-export.js']}, notmd)

still = g.touched_tier_a(diff_for('api/x.js', "'sc_claims'"), RES)
check('...and an ordinary handler still counts, so the exclusion did not widen',
      still == {'sc_claims': ['api/x.js']}, still)

own = g.touched_tier_a(diff_for('tools/tier_a_review_gate.py', "'sc_claims'"), RES)
check('the gate\'s own files are excluded, or recording an obligation would '
      'itself create one', own == {}, own)

ctx = g.touched_tier_a(
    'diff --git a/api/x.js b/api/x.js\n--- a/api/x.js\n+++ b/api/x.js\n'
    '@@ -1,3 +1,3 @@\n const a = 1;\n-const b = 2;\n+const b = 3;\n'
    " const c = 'law_trusttx';\n", RES)
check('a resource in the CONTEXT of a hunk counts -- an edit three lines from '
      'law_trusttx is an edit about law_trusttx',
      list(ctx) == ['law_trusttx'], ctx)

print('\n3. FAIL CLOSED -- an unreadable register is 2, never "no findings"')
tmp = tempfile.mkdtemp(prefix='tier-a-review-probe-')
real_register, real_reviews = g.REGISTER, g.REVIEWS
try:
    g.REGISTER = os.path.join(tmp, 'missing.md')
    code, lines = g.check(diff_for('api/x.js', "'sc_claims'"))
    check('a MISSING register exits 2, not 0', code == 2, '%s %s' % (code, lines))
    check('...and says it is not a pass',
          any('NOT a pass' in ln for ln in lines), lines)

    empty = os.path.join(tmp, 'empty.md')
    io.open(empty, 'w', encoding='utf-8').write('# no table here\n')
    g.REGISTER = empty
    code, lines = g.check(diff_for('api/x.js', "'sc_claims'"))
    check('a register with ZERO Tier A rows exits 2 rather than clearing every push',
          code == 2, '%s %s' % (code, lines))
    check('...and names the empty-set trap rather than just erroring',
          any('silently pass' in ln or 'ZERO Tier A rows' in ln for ln in lines), lines)

    g.REGISTER = real_register
    g.REVIEWS = os.path.join(tmp, 'missing.json')
    code, lines = g.check(diff_for('api/x.js', "'sc_claims'"))
    check('a MISSING review register exits 2', code == 2, '%s %s' % (code, lines))

    bad = os.path.join(tmp, 'bad.json')
    io.open(bad, 'w', encoding='utf-8').write('{ not json')
    g.REVIEWS = bad
    code, _ = g.check(diff_for('api/x.js', "'sc_claims'"))
    check('unparseable JSON exits 2', code == 2, code)

    noRecs = os.path.join(tmp, 'norecs.json')
    io.open(noRecs, 'w', encoding='utf-8').write('{"records": "not a list"}')
    g.REVIEWS = noRecs
    code, _ = g.check(diff_for('api/x.js', "'sc_claims'"))
    check('a register with no records LIST exits 2', code == 2, code)

    print('\n4. the one rule a machine can check: the reviewer is not the author')
    selfsigned = os.path.join(tmp, 'self.json')
    io.open(selfsigned, 'w', encoding='utf-8').write(json.dumps({'records': [
        {'author_session': 'cc', 'reviewer_session': 'cc', 'status': 'reviewed',
         'resources': ['sc_claims']}]}))
    g.REVIEWS = selfsigned
    code, lines = g.check(diff_for('api/x.js', "'sc_claims'"))
    check('a self-signed record is a FINDING (1)', code == 1, '%s %s' % (code, lines))
    check('...and the message says so in those words',
          any('SELF-SIGNED' in ln for ln in lines), lines)

    code, lines = g.check(diff_for('api/x.js', "'sb_ts'"))
    check('CONTROL: a self-signed record is a finding even on a push that '
          'touches NO Tier A code -- it is already in the file',
          code == 1, '%s %s' % (code, lines))

    crossed = os.path.join(tmp, 'crossed.json')
    io.open(crossed, 'w', encoding='utf-8').write(json.dumps({'records': [
        {'author_session': 'cc', 'reviewer_session': 'hank', 'status': 'reviewed',
         'resources': ['sc_claims']}]}))
    g.REVIEWS = crossed
    code, _ = g.check(diff_for('api/x.js', "'sb_ts'"))
    check('CONTROL: a record reviewed by a DIFFERENT session is not a finding',
          code == 0, code)

    print('\n5. an open obligation clears the push, and only a covering one')
    covering = os.path.join(tmp, 'open.json')
    io.open(covering, 'w', encoding='utf-8').write(json.dumps({'records': [
        {'author_session': g.session_name(), 'reviewer_session': None,
         'status': 'open', 'opened_at': 'x', 'resources': ['sc_claims']}]}))
    g.REVIEWS = covering
    code, _ = g.check(diff_for('api/x.js', "'sc_claims'"))
    check('an OPEN obligation naming the touched resource clears it', code == 0, code)

    code, lines = g.check(diff_for('api/x.js', "'dnt_patients'"))
    check('...and does NOT clear a push touching a DIFFERENT Tier A resource',
          code == 1, '%s %s' % (code, lines))

    other = os.path.join(tmp, 'other.json')
    io.open(other, 'w', encoding='utf-8').write(json.dumps({'records': [
        {'author_session': 'somebody-else', 'reviewer_session': None,
         'status': 'open', 'opened_at': 'x', 'resources': ['sc_claims']}]}))
    g.REVIEWS = other
    code, _ = g.check(diff_for('api/x.js', "'sc_claims'"))
    check('ANOTHER session\'s open obligation does not clear MY push', code == 1, code)

    closed = os.path.join(tmp, 'closed.json')
    io.open(closed, 'w', encoding='utf-8').write(json.dumps({'records': [
        {'author_session': g.session_name(), 'reviewer_session': 'hank',
         'status': 'reviewed', 'opened_at': 'x', 'resources': ['sc_claims']}]}))
    g.REVIEWS = closed
    code, _ = g.check(diff_for('api/x.js', "'sc_claims'"))
    check('a DISCHARGED obligation does not cover a NEW Tier A change -- the '
          'next change needs its own', code == 1, code)
finally:
    g.REGISTER, g.REVIEWS = real_register, real_reviews
    try:
        for f in os.listdir(tmp):
            os.remove(os.path.join(tmp, f))
        os.rmdir(tmp)
    except OSError:
        pass

print('\n6. --discharge: somebody ELSE closes it, and the refusal is at WRITE time')
# ── THIS SECTION EXISTS BECAUSE I BROKE THE REAL REGISTER TESTING IT ────────
# --discharge was added after Hank reviewed Fourth's obligation (ce7764fa, two
# real findings) and the record still said `open`, because the gate had shipped
# with no way to close. While checking the new command I ran it against the LIVE
# register and recorded cc as the reviewer of work HANK had reviewed, with a
# placeholder verdict. Both were false. Both were reverted, in the open.
#
# So every arm below drives a TEMPORARY register. A probe that exercises a WRITE
# command against the real file is a probe that can forge a review record, and on
# this platform that is the one record that must not be forgeable.
tmp2 = tempfile.mkdtemp(prefix='tier-a-discharge-probe-')
real_reviews2 = g.REVIEWS
seq = [0]


def fresh(author='somebody-else', opened='2026-01-01T00:00:00Z', extra=None):
    recs = [{'author_session': author, 'opened_at': opened, 'status': 'open',
             'resources': ['sc_claims'], 'reviewer_session': None,
             'reviewed_at': None, 'verdict': None}]
    if extra:
        recs.append(extra)
    seq[0] += 1
    path = os.path.join(tmp2, 'r-%d.json' % seq[0])
    io.open(path, 'w', encoding='utf-8').write(json.dumps({'records': recs}))
    g.REVIEWS = path
    return path


SECOND = {'author_session': 'somebody-else', 'opened_at': '2026-01-02T00:00:00Z',
          'status': 'open', 'resources': ['sc_ar'], 'reviewer_session': None,
          'reviewed_at': None, 'verdict': None}
try:
    fresh(author=g.session_name())
    check('a session CANNOT discharge its own obligation',
          g.cmd_discharge(g.session_name(), 'looks fine to me') == 1,
          'self-discharge was allowed')

    p2 = fresh()
    check("...but it CAN discharge another session's",
          g.cmd_discharge('somebody-else', 'read it, two findings, both fixed') == 0)
    rec = json.load(io.open(p2, encoding='utf-8'))['records'][0]
    check('...and the record names the REVIEWER, not the author',
          rec['reviewer_session'] == g.session_name() and rec['status'] == 'reviewed', rec)
    check('...and stores the verdict text, so a tick is not a review',
          'two findings' in (rec.get('verdict') or ''), rec.get('verdict'))

    fresh()
    check('an EMPTY verdict is refused -- "reviewed" with no content is a tick',
          g.cmd_discharge('somebody-else', '   ') == 1)

    fresh(extra=dict(SECOND))
    check('with TWO open by one author it REFUSES TO GUESS which',
          g.cmd_discharge('somebody-else', 'a verdict') == 1,
          'it closed one of two without being told which')

    p3 = fresh(extra=dict(SECOND))
    check('...and closes the RIGHT one when told',
          g.cmd_discharge('somebody-else', 'the second one',
                          opened_at='2026-01-02T00:00:00Z') == 0)
    by = {r['opened_at']: r['status']
          for r in json.load(io.open(p3, encoding='utf-8'))['records']}
    check('...leaving the other still OPEN',
          by.get('2026-01-01T00:00:00Z') == 'open'
          and by.get('2026-01-02T00:00:00Z') == 'reviewed', by)

    fresh()
    check('discharging an author with NO open obligation is refused',
          g.cmd_discharge('nobody-at-all', 'a verdict') == 1)
finally:
    g.REVIEWS = real_reviews2
    try:
        for f in os.listdir(tmp2):
            os.remove(os.path.join(tmp2, f))
        os.rmdir(tmp2)
    except OSError:
        pass
check('the live register was never written by this section',
      g.REVIEWS == real_reviews2 and os.path.isfile(g.REVIEWS), g.REVIEWS)

print('\n7. the gate is WIRED, not merely written')
hook = io.open(os.path.join(REPO, 'tools', 'sairn_push_gate_hook.py'),
               encoding='utf-8').read()
check('the push gate invokes tier_a_review_gate.py',
      'tier_a_review_gate.py' in hook, 'the check exists and nothing calls it')
check('...and DENIES on exit 1 rather than printing',
      "_rev.returncode == 1" in hook and 'deny(' in hook, hook.count('deny('))
check('...and reports exit 2 as NOT a pass',
      'COULD NOT TELL' in hook, 'exit 2 is folded into a pass')

print('\n8. the real repo state is clean under its own gate')
r = subprocess.run([sys.executable, os.path.join(REPO, 'tools', 'tier_a_review_gate.py'),
                    '--list'], cwd=REPO, capture_output=True, text=True, timeout=120)
check('--list runs and exits 0', r.returncode == 0, r.stderr[:300])

print()
if fails:
    print('%d ARM(S) FAILED:' % len(fails))
    for f in fails:
        print('  - ' + f)
else:
    print('ALL ARMS PASS')
sys.exit(1 if fails else 0)
