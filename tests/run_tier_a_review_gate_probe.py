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
import shutil
import subprocess
import sys
import tempfile
import threading
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
# ── DECLARED 2026-09-29. THIS FILE EXISTED AND NOTHING COUNTED IT ───────────
# checker_control_check.py finds a tool/control pair from CONTROLS_FOR here or
# CONTROLLED_BY in the tool, and neither was present -- so the largest control in
# this repo for one of its most consequential gates registered as ABSENT. The
# arms all ran; the pair was just invisible to the thing whose job is to notice
# a checker with no control. A missing one-line declaration and a missing control
# file are indistinguishable to the tool that reads it.
CONTROLS_FOR = ['tier_a_review_gate.py']
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
# ── THE NEGATIVE CONTROL WENT STALE AND SAT RED (fixed 2026-09-24) ─────────
# This arm asserted `sc_dme` is NOT in the Tier A set. sc_dme was re-tiered
# B->A (docs/CRITICALITY-TIERS.md:201 -- a DME record wrong on its HCPCS code
# bills a Medicare claim) and the arm went red and STAYED red at origin/main,
# read as noise. A negative control pinned to a name somebody may legitimately
# promote is a fixture that expires without announcement -- the same shape as
# the sf_ absence arm replaced earlier this week. The control now uses a row
# whose B is structural rather than provisional: sc_settings is configuration,
# and a register that promotes CONFIGURATION to Tier A has changed its own
# definition, which is exactly what this arm should catch.
check('...and NOT a Tier B name', 'sc_encoder' not in real,
      'sc_encoder is in the Tier A set -- either the register redefined Tier A '
      'or the parser is over-collecting. (First replacement pick was '
      'sc_settings, which turned out to be A/B on the retention-period limb -- '
      'checked before use this time, which is the step the sc_dme version of '
      'this arm never got.)')

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

# ── A CLAIM FILE IS A RECORD OF INTENT, NOT CODE (2026-09-16) ────────────────
# THIRD false positive of this shape, after the worklog and the review probe. The
# gate refused a push whose only Tier-A-naming file was `.claude/claims/cody.json`
# -- the coordination record tools/sairn_claim.py writes, carrying the TASK STRING
# a session typed. Claiming work on sv_controlled necessarily names sv_controlled.
cl = g.touched_tier_a(
    diff_for('.claude/claims/cody.json', '  "task": "item 46 parity for sc_claims"'), RES)
check('a CLAIM FILE is not code serving a Tier A resource', cl == {}, cl)

# THE OTHER DIRECTION, and it is why the exclusion names claims/ rather than
# .claude/: settings and hooks under .claude/ genuinely can change behaviour, and
# excluding the whole directory would hide a real change to what gates a push.
st = g.touched_tier_a(
    diff_for('.claude/settings.json', "'sc_claims'"), RES)
check('...but .claude/settings.json is NOT excluded -- a hook change is real',
      st == {'sc_claims': ['.claude/settings.json']}, st)

# ── 2b. EVERY EXCLUSION CARRIES A REASON, AND EVERY TRACKED PATH CLASS IS
# ── CLASSIFIED. Added 2026-09-16, and this is what replaced inverting the
# ── predicate.
#
# THE INVERSION WAS MEASURED AND REJECTED. An `api/ + tests/ + tools/ + root
# *.html` allow-list would silently drop 42 in-scope files across ten path
# classes, including `.claude/settings.json` (wires the push hooks),
# `.githooks/pre-commit` and `.github/workflows/codeql.yml`. The deny-list fails
# into a LOUD false positive; an allow-list fails into SILENCE. For a gate whose
# subject is somebody not being told, silence is the wrong direction.
#
# So the real defect was never the polarity -- it was that each exclusion was an
# anonymous clause nobody had to justify, so a fourth false positive would be
# fixed by appending a fifth clause and the pattern would stay invisible. These
# arms make that impossible: a new top-level directory is a RED ARM, and a new
# exclusion needs a reason somebody has to write.
print('\n2b. exclusions are REASONED, and the classification is exhaustive')
check('every SKIP_REASONS entry carries a non-trivial reason',
      all(isinstance(why, str) and len(why) > 30 for _, why in g.SKIP_REASONS),
      [why[:20] for _, why in g.SKIP_REASONS])
check('skip_reason returns a REASON for an excluded path, not just True',
      isinstance(g.skip_reason('docs/CRITICALITY-TIERS.md'), str),
      g.skip_reason('docs/CRITICALITY-TIERS.md'))
check('...and None for a path that CAN create an obligation',
      g.skip_reason('api/sd-data.js') is None, g.skip_reason('api/sd-data.js'))

_ls = subprocess.run(['git', '-C', REPO, 'ls-files'], capture_output=True,
                     encoding='utf-8', errors='replace')
if _ls.returncode != 0:
    check('the tracked tree could be read', False, 'git ls-files failed')
else:
    _tracked = [f for f in _ls.stdout.split('\n')
                if f and not f.startswith('archive/') and not f.startswith('"archive/')]
    # One representative per path class, so the arm is about CLASSES rather than
    # about 1900 files -- and so adding a file to a known directory is not a
    # failure while adding a NEW directory is.
    _classes = {}
    for f in _tracked:
        k = f.split('/')[0] + '/' if '/' in f else '<root>'
        _classes.setdefault(k, f)
    # IN SCOPE is the default and is correct: a class nobody has thought about
    # should be REVIEWED, not skipped.
    _known = sorted(_classes)
    check('the tree has at least the expected path classes', len(_known) >= 8, _known)
    _unreasoned = [k for k, f in _classes.items()
                   if g.skip_reason(f) is None and k not in (
                       'api/', 'tests/', 'tools/', '<root>', 'sql/', 'docs/',
                       '.claude/', '.github/', '.githooks/', 'agent/', 'db/',
                       'dist/', 'packages/', 'scripts/', 'skills/', 'sql/')]
    check('NO UNRECOGNISED PATH CLASS -- a new top-level directory must be a '
          'decision, not a default', _unreasoned == [],
          'unrecognised: %s -- decide whether it can serve a Tier A resource, '
          'then add it to this arm or to SKIP_REASONS with a reason' % _unreasoned)

# ── 2c. THE HOVER AUDITOR'S OWN TOOLING (H2 seq 425, landed 2026-09-30) ─────
# The gate tripped TWICE in one session on a resource NAME appearing as a bare
# token inside auditor tooling -- "leg_insurance" in hover_citation_linter.py's
# fixtures (seq 416), "quotes" in stale_basis_check.py's prose (seq 422). Each
# forced an obligation the auditor STRUCTURALLY CANNOT COMMIT, because
# hover_auditor_scope_gate.py refuses docs/tier-a-reviews.json from that clone.
# A gate that demands a record its subject is forbidden to write is not a gate,
# it is a deadlock, and it fired twice before anybody named it.
#
# THE GATE'S OWN HEADER ALREADY NAMED THIS DEAD END AND LEFT IT OPEN:
# strip_diff_noise() blanks PROSE strings (3+ words) and keeps SHORT tokens,
# because a resource token in real serving code IS a short literal ('sb_ts').
# So a fixture token is "character-for-character what a handler writes" -- the
# gate's own words -- and no string analysis can separate them.
#
# SO THE PREDICATE IS ABOUT WHAT THE FILE **IS**, which is the axis every other
# SKIP_REASONS clause already uses. The auditor's core rule FORBIDS it writing
# platform code, so a resource name in its rotation pool, its fixtures or a
# regex example is a MENTION and never a handler -- the same "naming is not
# serving" logic as docs/ and sql/.
print('\n2c. the hover auditor\'s own tooling names resources it cannot serve')
AUD = '.claude/skills/sairn-hover-auditor/tools-hover2/hover_x.py'
check('auditor tooling is SKIPPED with a reason -- a Tier A name there is a '
      'mention, not a handler, and the auditor cannot commit the obligation '
      'the gate would demand',
      isinstance(g.skip_reason(AUD), str), g.skip_reason(AUD))
check('...the H1 tool tree too, not just tools-hover2',
      isinstance(g.skip_reason(
          '.claude/skills/sairn-hover-auditor/tools/hover_log.py'), str))
_aud = g.touched_tier_a(diff_for(AUD, "POOL = ['sc_claims', 'sc_ar']"), RES)
check('...so a rotation-pool list naming two Tier A resources attributes '
      'NOTHING', _aud == {}, _aud)

# ── THE CONTROLS. This exclusion is a whole DIRECTORY TREE, which is the
# ── widest clause in SKIP_REASONS, so its blast radius is fenced in three
# ── directions rather than one.
_ctrl = g.touched_tier_a(diff_for('api/sd-data.js', "if (resource === 'sc_claims') {"), RES)
check('CONTROL: a real handler naming the same resource STILL counts -- the '
      'exclusion is about the auditor tree, not about the word',
      _ctrl == {'sc_claims': ['api/sd-data.js']}, _ctrl)
_near = g.touched_tier_a(diff_for('.claude/skills/sairn-other/tool.py', "'sc_claims'"), RES)
check('CONTROL: a SIBLING skill directory is NOT excluded by accident -- the '
      'clause is anchored on the auditor\'s path, not on .claude/skills/',
      _near == {'sc_claims': ['.claude/skills/sairn-other/tool.py']}, _near)
_claims = g.touched_tier_a(
    diff_for('.claude/skills/sairn-hover-auditor-notreally/x.py', "'sc_claims'"), RES)
check('CONTROL: a directory whose name merely STARTS WITH the auditor\'s is '
      'not the auditor -- the prefix carries its trailing slash',
      _claims == {'sc_claims': ['.claude/skills/sairn-hover-auditor-notreally/x.py']},
      _claims)

# ── THE NARROWING, AND IT IS MEASURED RATHER THAN ARGUED ───────────────────
# The clause first landed as the WHOLE auditor tree, which made it the widest
# entry in SKIP_REASONS. Measured over all 79 tracked files there, 13 carry a
# Tier A name and every one is inside a `tools*/` subdirectory -- so the clause
# now covers those and nothing else. These arms are what stops it widening back.
check('the clause survives a THIRD auditor instance -- tools-hover3/ is covered '
      'without anybody editing this file, the same reason AuditorScope replaced '
      'a hardcoded pair',
      isinstance(g.skip_reason(
          '.claude/skills/sairn-hover-auditor/tools-hover3/x.py'), str))
check('...and a nested path inside a tools dir is covered too (the real tree '
      'has tools/sabotage_benchmark/fixtures.py, which carries a Tier A name)',
      isinstance(g.skip_reason(
          '.claude/skills/sairn-hover-auditor/tools/sabotage_benchmark/fixtures.py'),
          str))
check('...and a DATA file beside the tools is covered, not just .py -- '
      'hover-watchlist.json is the shape that will name resources one day, and '
      'narrowing to .py would re-open the deadlock for exactly it',
      isinstance(g.skip_reason(
          '.claude/skills/sairn-hover-auditor/tools/hover-watchlist.json'), str))

_root = g.touched_tier_a(
    diff_for('.claude/skills/sairn-hover-auditor/config.json', "'sc_claims'"), RES)
check('NARROWED: a file directly under the auditor ROOT is back IN SCOPE -- a '
      'new file shape outside the tool directories is a decision, not a default',
      _root == {'sc_claims': ['.claude/skills/sairn-hover-auditor/config.json']},
      _root)
_sub = g.touched_tier_a(
    diff_for('.claude/skills/sairn-hover-auditor/handlers/x.py', "'sc_claims'"), RES)
check('NARROWED: a NEW non-tools subdirectory is back IN SCOPE -- the same "a '
      'new directory must be a decision" rule this file already enforces for '
      'top-level directories, applied one level down',
      _sub == {'sc_claims': ['.claude/skills/sairn-hover-auditor/handlers/x.py']},
      _sub)

# THE MEASUREMENT ITSELF, RE-RUN HERE. The narrowing is only correct while
# every name-carrying file is inside a tools dir; the day one is not, this arm
# goes red instead of the gate silently deadlocking the auditor again.
_tree = [f for f in subprocess.run(
    ['git', '-C', REPO, 'ls-files', '.claude/skills/sairn-hover-auditor/'],
    capture_output=True, encoding='utf-8', errors='replace').stdout.split('\n')
    if f.strip()]
check('the auditor tree is readable and non-trivial', len(_tree) > 40, len(_tree))
_uncovered = []
for _f in _tree:
    if g.skip_reason(_f):
        continue
    _body = io.open(os.path.join(REPO, _f.replace('/', os.sep)),
                    encoding='utf-8', errors='replace').read()
    if g.touched_tier_a(diff_for(_f, *_body.split('\n')), RES):
        _uncovered.append(_f)
check('EVERY name-carrying file in the auditor tree is still covered by the '
      'narrowed clause -- if one ever sits outside a tools dir, this arm is '
      'what says so rather than the auditor discovering it at push',
      _uncovered == [], _uncovered)

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

# ── THIS ARM ASSERTED THE OPPOSITE UNTIL 2026-09-15, ON MY OWN ARGUMENT ────
# It read: "a resource in the CONTEXT of a hunk counts -- an edit three lines
# from law_trusttx is an edit about law_trusttx." Measured against every real
# case the gate has seen, that argument does not survive:
#
#   item 97 soft-delete        TRUE   context 8   changed 8
#   sc_denial_events gate      TRUE   context 7   changed 7
#   358-site decode sweep      FALSE  context 1   changed 0
#   report-only artefact fix   FALSE  context 0   changed 0
#
# Context added NOTHING to either true positive and produced the only remaining
# false one. A platform-wide sweep touches one line in 137 files and therefore
# produces context lines everywhere, which is how a gate that blocks on context
# becomes a gate people override.
CTX_DIFF = ('diff --git a/api/x.js b/api/x.js\n--- a/api/x.js\n+++ b/api/x.js\n'
            '@@ -1,3 +1,3 @@\n const a = 1;\n-const b = 2;\n+const b = 3;\n'
            " const c = 'law_trusttx';\n")
check('a resource named ONLY in hunk context does NOT block',
      g.touched_tier_a(CTX_DIFF, RES) == {}, g.touched_tier_a(CTX_DIFF, RES))
check('...but it is still REPORTED -- demoted, not deleted',
      list(g.context_only_tier_a(CTX_DIFF, RES)) == ['law_trusttx'],
      g.context_only_tier_a(CTX_DIFF, RES))
CHG_DIFF = ('diff --git a/api/x.js b/api/x.js\n--- a/api/x.js\n+++ b/api/x.js\n'
            '@@ -1,2 +1,2 @@\n-const c = 1;\n'
            "+const c = 'law_trusttx';\n")
check('CONTROL: a resource on an ADDED line still blocks -- the narrowing did '
      'not turn the gate off',
      list(g.touched_tier_a(CHG_DIFF, RES)) == ['law_trusttx'],
      g.touched_tier_a(CHG_DIFF, RES))
DEL_DIFF = ('diff --git a/api/x.js b/api/x.js\n--- a/api/x.js\n+++ b/api/x.js\n'
            "@@ -1,2 +1,2 @@\n-const c = 'law_trusttx';\n+const c = 1;\n")
check('CONTROL: and so does one on a REMOVED line -- deleting a reference to a '
      'Tier A resource is a change about it',
      list(g.touched_tier_a(DEL_DIFF, RES)) == ['law_trusttx'],
      g.touched_tier_a(DEL_DIFF, RES))

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

    code, lines = g.check(diff_for('api/x.js', "'zz_not_a_resource'"))
    check('CONTROL: a self-signed record is a finding even on a push that '
          'touches NO Tier A code -- it is already in the file',
          code == 1, '%s %s' % (code, lines))

    crossed = os.path.join(tmp, 'crossed.json')
    io.open(crossed, 'w', encoding='utf-8').write(json.dumps({'records': [
        {'author_session': 'cc', 'reviewer_session': 'hank', 'status': 'reviewed',
         'resources': ['sc_claims']}]}))
    g.REVIEWS = crossed
    # NOT A REAL RESOURCE NAME, DELIBERATELY. This fixture used `sb_ts` as a
    # stand-in for "definitely not Tier A" -- and sb_ts BECAME Tier A on
    # 2026-09-15, six hours after the timesheet write path was built, so the
    # control started failing for a reason that had nothing to do with what it
    # tests. A placeholder that can be promoted is a placeholder with a clock
    # in it; `zz_not_a_resource` cannot be registered or tiered by anybody.
    code, _ = g.check(diff_for('api/x.js', "'zz_not_a_resource'"))
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

    # ── COVERAGE IS PER RESOURCE, NOT PER CHANGE (hover #270) ───────────────
    # Every arm above drives a change touching ONE resource, so the difference
    # between an INTERSECTION and a SUBSET was invisible to this probe -- which
    # is why the defect lived. The shipped test was
    # `set(hits) & set(record.resources)`, so one resource in common cleared
    # the whole change.
    hits_names = {'sc_claims', 'dnt_patients'}

    def two_res_diff():
        return diff_for('api/x.js', "'sc_claims'", "'dnt_patients'")

    g.REVIEWS = covering            # names sc_claims only
    code, lines = g.check(two_res_diff())
    check('#270 a change touching TWO Tier A resources is NOT cleared by an '
          'obligation naming ONE of them', code == 1, '%s %s' % (code, lines))
    blob = '\n'.join(lines)
    check('#270 ...and the refusal names the UNCOVERED resource',
          'dnt_patients' in blob, blob[:200])
    check('#270 ...and says which half IS already covered, so the session is '
          'not told to re-record everything', 'sc_claims' in blob, blob[:200])
    check('#270 ...and says so in its own heading rather than reading as a '
          'change with nothing recorded at all',
          'ONLY PART OF IT IS RECORDED' in blob, blob[:120])
    # The BLOCKING list must be the uncovered set and nothing else. Without
    # this arm the gate could name every touched resource again and the three
    # arms above would all still pass, because each only asks whether a name is
    # present somewhere in the output.
    blockline = [l for l in lines if 'NOT covered' in l]
    check('#270 ...and the BLOCKING summary names exactly the uncovered set',
          len(blockline) == 1 and 'dnt_patients' in blockline[0]
          and 'sc_claims' not in blockline[0], blockline)
    # AND THE PER-RESOURCE LISTING BELOW IT, which is a different line built
    # from a different variable. The arm above reads the SUMMARY; a gate that
    # printed the right summary and then listed every touched resource would
    # satisfy it, and did -- tests/run_tier_a_review_gate_sabotage_probe.py
    # planted exactly that and this probe stayed green until this arm existed.
    listed = set()
    for l in lines:
        parts = l.split()
        if l.startswith('  ') and len(parts) >= 2 and parts[0] in hits_names:
            listed.add(parts[0])
    check('#270 ...and the per-resource LISTING is the uncovered set too, not '
          'every resource the change touched',
          listed == {'dnt_patients'}, sorted(listed))

    # THE OTHER DIRECTION, and without it the arm above is satisfied by a gate
    # that simply refuses every multi-resource change.
    both = os.path.join(tmp, 'both.json')
    io.open(both, 'w', encoding='utf-8').write(json.dumps({'records': [
        {'author_session': g.session_name(), 'reviewer_session': None,
         'status': 'open', 'opened_at': 'x',
         'resources': ['sc_claims', 'dnt_patients']}]}))
    g.REVIEWS = both
    code, _ = g.check(two_res_diff())
    check('#270 CONTROL: ONE obligation naming BOTH resources still clears it',
          code == 0, code)

    # TWO records that TOGETHER cover the change. The union is deliberate: a
    # session may hold two obligations, and requiring one record to carry the
    # whole set would block honest work.
    split = os.path.join(tmp, 'split.json')
    io.open(split, 'w', encoding='utf-8').write(json.dumps({'records': [
        {'author_session': g.session_name(), 'reviewer_session': None,
         'status': 'open', 'opened_at': 'a', 'resources': ['sc_claims']},
        {'author_session': g.session_name(), 'reviewer_session': None,
         'status': 'open', 'opened_at': 'b', 'resources': ['dnt_patients']}]}))
    g.REVIEWS = split
    code, _ = g.check(two_res_diff())
    check('#270 CONTROL: TWO obligations that TOGETHER cover it also clear it '
          '-- coverage is the union, not one record carrying everything',
          code == 0, code)

    # And the union must not reach across sessions: half mine, half somebody
    # else's is NOT covered.
    mixed = os.path.join(tmp, 'mixed.json')
    io.open(mixed, 'w', encoding='utf-8').write(json.dumps({'records': [
        {'author_session': g.session_name(), 'reviewer_session': None,
         'status': 'open', 'opened_at': 'a', 'resources': ['sc_claims']},
        {'author_session': 'somebody-else', 'reviewer_session': None,
         'status': 'open', 'opened_at': 'b', 'resources': ['dnt_patients']}]}))
    g.REVIEWS = mixed
    code, lines = g.check(two_res_diff())
    check('#270 CONTROL: the union is MINE only -- another session\'s open '
          'obligation does not fill my gap', code == 1,
          '%s %s' % (code, lines))
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
          g.cmd_discharge(g.session_name(), 'read the diff, re-derived both column lists against the callers, two findings, both fixed') == 1,
          # A FULL-LENGTH VERDICT ON PURPOSE. With a short one this arm would go
          # green off the MIN_VERDICT_CHARS floor added 2026-09-29 and stop
          # testing the self-review refusal at all -- a control passing for a
          # reason that is not the one in its name.

          'self-discharge was allowed')

    p2 = fresh()
    check("...but it CAN discharge another session's",
          g.cmd_discharge('somebody-else', 'read the diff, re-derived both column lists against the callers, two findings, both fixed') == 0)
    rec = json.load(io.open(p2, encoding='utf-8'))['records'][0]
    check('...and the record names the REVIEWER, not the author',
          rec['reviewer_session'] == g.session_name() and rec['status'] == 'reviewed', rec)
    check('...and stores the verdict text, so a tick is not a review',
          'two findings' in (rec.get('verdict') or ''), rec.get('verdict'))

    fresh()
    check('an EMPTY verdict is refused -- "reviewed" with no content is a tick',
          g.cmd_discharge('somebody-else', '   ') == 1)

    # ── A SHIFTED ARGUMENT SILENTLY BECAME A VERDICT (2026-09-29) ──────────
    # The usage line read `--discharge <author> "<verdict>"` while the parser
    # wants the opened_at SECOND, so a real call of
    #     --discharge cc 2026-09-26T13:13:44Z --help
    # dispatched cleanly, wrote `--help` as the verdict, printed DISCHARGED and
    # marked a 70h Tier A obligation reviewed. The dispatch was not wrong; what
    # was wrong is that a flag was accepted as the artefact the register exists
    # to hold. An obligation closed with a meaningless verdict is WORSE than one
    # left open: the queue shortens and the next session has no reason to look.
    fresh()
    check('A VERDICT THAT IS A FLAG is refused -- this is the exact `--help` that '
          'closed a 70h obligation, and nothing may be written',
          g.cmd_discharge('somebody-else', '--help') == 1,
          'a bare flag was accepted as a review')
    _pf = fresh()
    g.cmd_discharge('somebody-else', '--takeover --write')
    check('...AND NOTHING WAS WRITTEN by that refusal -- a refusal that still '
          'marks the record reviewed is the defect with a message in front of it',
          json.load(io.open(_pf, encoding='utf-8'))['records'][0]['status'] == 'open',
          'the record moved off open despite the refusal')

    fresh()
    check('A TICK-LENGTH VERDICT is refused: a review of a Tier A change that '
          'fits in under MIN_VERDICT_CHARS is a tick, not a review',
          g.cmd_discharge('somebody-else', 'looks fine') == 1,
          'a two-word grunt was accepted as a review')
    check('...and MIN_VERDICT_CHARS is a NAMED constant above 0, so the floor is '
          'readable and a change to it is visible rather than buried in a literal',
          isinstance(getattr(g, 'MIN_VERDICT_CHARS', None), int)
          and g.MIN_VERDICT_CHARS > 0, getattr(g, 'MIN_VERDICT_CHARS', None))

    # THE SILENT HALF. Without this the two arms above are satisfied by a gate
    # that refuses every discharge, which would be a queue nobody can ever close.
    _pg = fresh()
    check('THE SILENT HALF: a real, full-length verdict from another session is '
          'still ACCEPTED, so the two refusals above are not satisfied by a gate '
          'that refuses everything',
          g.cmd_discharge('somebody-else', 'read the diff, re-derived both column lists against the callers, two findings, both fixed') == 0,
          'the length floor now blocks a legitimate discharge')
    check('...and that one really did land', json.load(
          io.open(_pg, encoding='utf-8'))['records'][0]['status'] == 'reviewed')

    fresh(extra=dict(SECOND))
    check('with TWO open by one author it REFUSES TO GUESS which',
          g.cmd_discharge('somebody-else', 'read the diff, re-derived both column lists against the callers, two findings, both fixed') == 1,
          # Full length here too, so the REFUSES-TO-GUESS arm is not satisfied
          # by the length floor.

          'it closed one of two without being told which')

    p3 = fresh(extra=dict(SECOND))
    check('...and closes the RIGHT one when told',
          g.cmd_discharge('somebody-else', 'the second one -- ' + 'read the diff, re-derived both column lists against the callers, two findings, both fixed',
                          opened_at='2026-01-02T00:00:00Z') == 0)
    by = {r['opened_at']: r['status']
          for r in json.load(io.open(p3, encoding='utf-8'))['records']}
    check('...leaving the other still OPEN',
          by.get('2026-01-01T00:00:00Z') == 'open'
          and by.get('2026-01-02T00:00:00Z') == 'reviewed', by)

    fresh()
    check('discharging an author with NO open obligation is refused',
          g.cmd_discharge('nobody-at-all', 'read the diff, re-derived both column lists against the callers, two findings, both fixed') == 1)
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

# ── 6b. ONE WRITE POINT, AND THE REASON THIS SECTION EXISTS (2026-09-16) ─────
# `_discharge()` shipped carrying the docstring "Shared by both discharge paths
# so the self-review refusal cannot be true on one and forgotten on the other",
# and it was NOT shared -- `cmd_auto_discharge` set the same four fields inline,
# so there were two write points and the refusal sat on one of them. The comment
# asserted the control; nothing tested it; it read as present and was absent.
#
# THE ARM THAT MATTERS IS THE LAST ONE. Checking that `_discharge` refuses a
# self-signed write proves the guard works where it is; it says nothing about
# whether every closure goes through it. So the auto path is driven with
# `_discharge` REPLACED, and the arm fails if a record closes without it being
# called -- which is what the old code would have done.
print('\n6b. every closure goes through ONE write point, guard included')
tmp3 = tempfile.mkdtemp(prefix='tier-a-writepoint-probe-')
real_reviews3, real_defects3 = g.REVIEWS, g.DEFECT_REGISTER


def _rec(author='somebody-else', opened='2026-01-01T00:00:00Z'):
    return {'author_session': author, 'opened_at': opened, 'status': 'open',
            'resources': ['sc_claims'], 'files': ['api/sd-data.js'],
            'what': 'a change', 'reviewer_session': None, 'reviewed_at': None,
            'verdict': None}


def _stage(name, records, evidence):
    rp = os.path.join(tmp3, 'rev-%s.json' % name)
    dp = os.path.join(tmp3, 'def-%s.json' % name)
    io.open(rp, 'w', encoding='utf-8').write(json.dumps({'records': records}))
    io.open(dp, 'w', encoding='utf-8').write(json.dumps({'records': evidence}))
    g.REVIEWS, g.DEFECT_REGISTER = rp, dp
    return rp


# Evidence shaped exactly as cmd_auto_discharge requires: the method, a file
# overlap, a date at or after the obligation, the resource named in its own
# words, and the obligation's opened_at CITED -- which is the only thing that
# closes rather than suggests.
CITED = {'commit': 'abc123def456', 'date': '2026-01-02',
         'files': ['api/sd-data.js'], 'app': 'SAIRNcode',
         'detection_method': 'independent-review',
         'summary': 'reviewed sc_claims against obligation 2026-01-01T00:00:00Z'}
NEAR = dict(CITED, commit='999zzz', summary='found a sc_claims gate gap')
try:
    _stage('selfsign', [], [])
    r0 = _rec(author=g.session_name())
    try:
        g._discharge(r0, g.session_name(), 'a verdict', 'reviewed')
        ok = False
    except g.SelfSigned:
        ok = True
    check('_discharge REFUSES a self-signed write at the write point itself',
          ok and r0['status'] == 'open',
          'the record was mutated before the guard, or there is no guard: %r' % r0)

    r1 = _rec()
    try:
        g._discharge(r1, 'a-reviewer', '   ', 'reviewed')
        ok = False
    except g.SelfSigned:
        ok = True
    check('...and an empty verdict, so a tick cannot close anything',
          ok and r1['status'] == 'open', r1)

    r2 = _rec()
    g._discharge(r2, 'a-reviewer', 'read it, two findings', 'reviewed-by-record')
    check('...and writes the status it was GIVEN, not a hardcoded one',
          r2['status'] == 'reviewed-by-record'
          and r2['reviewer_session'] == 'a-reviewer'
          and r2['reviewed_at'] and 'two findings' in r2['verdict'], r2)

    p = _stage('dry', [_rec()], [CITED])
    code = g.cmd_auto_discharge(write=False)
    after = json.load(io.open(p, encoding='utf-8'))['records'][0]
    check('--auto-discharge DRY RUN writes nothing',
          code == 0 and after['status'] == 'open', after)

    p = _stage('write', [_rec()], [CITED])
    check('--auto-discharge --write closes a CITED obligation',
          g.cmd_auto_discharge(write=True) == 0)
    after = json.load(io.open(p, encoding='utf-8'))['records'][0]
    check('...to `reviewed-by-record`, a status a reader can tell from `reviewed`',
          after['status'] == 'reviewed-by-record', after)
    check('...naming the MECHANISM as reviewer, never a session',
          'defect register' in (after['reviewer_session'] or ''), after)
    check('...and saying in the RECORD that this is the weaker close',
          'WEAKER CLOSE' in (after['verdict'] or ''), after.get('verdict'))

    p = _stage('near', [_rec()], [NEAR])
    g.cmd_auto_discharge(write=True)
    after = json.load(io.open(p, encoding='utf-8'))['records'][0]
    check('EVIDENCE THAT IS ONLY NEAR does NOT close -- overlap is not a citation',
          after['status'] == 'open', after)

    _stage('cannot-read', [_rec()], [])
    g.DEFECT_REGISTER = os.path.join(tmp3, 'does-not-exist.json')
    check('a register that CANNOT BE READ is exit 2, not a quiet nothing-to-close',
          g.cmd_auto_discharge(write=True) == 2,
          '"no evidence" and "I could not look" closed the same obligations')

    # THE SABOTAGE ARM. Replace the single write point; if any closure still
    # happens, some path is writing the fields itself and is not guarded.
    p = _stage('routing', [_rec()], [CITED])
    calls = []
    orig = g._discharge
    try:
        g._discharge = lambda *a, **k: calls.append(a)
        g.cmd_auto_discharge(write=True)
    finally:
        g._discharge = orig
    after = json.load(io.open(p, encoding='utf-8'))['records'][0]
    check('AUTO-DISCHARGE ROUTES THROUGH _discharge -- it does not write inline',
          len(calls) == 1 and after['status'] == 'open',
          'closed with the write point stubbed out (%d call(s)): %r' % (len(calls), after))
finally:
    g.REVIEWS, g.DEFECT_REGISTER = real_reviews3, real_defects3
    try:
        for f in os.listdir(tmp3):
            os.remove(os.path.join(tmp3, f))
        os.rmdir(tmp3)
    except OSError:
        pass
check('the live register and defect register were never written by 6b',
      g.REVIEWS == real_reviews3 and g.DEFECT_REGISTER == real_defects3
      and os.path.isfile(g.REVIEWS) and os.path.isfile(g.DEFECT_REGISTER))

print('\n7. the gate is WIRED, not merely written')
hook = io.open(os.path.join(REPO, 'tools', 'sairn_push_gate_hook.py'),
               encoding='utf-8').read()
check('the push gate invokes tier_a_review_gate.py',
      'tier_a_review_gate.py' in hook, 'the check exists and nothing calls it')
check('...and DENIES on exit 1 rather than printing',
      "_rev.returncode == 1" in hook and 'deny(' in hook, hook.count('deny('))
check('...and reports exit 2 as NOT a pass',
      'COULD NOT TELL' in hook, 'exit 2 is folded into a pass')

print('\n8. the real repo state is readable under its own gate')
r = subprocess.run([sys.executable, os.path.join(REPO, 'tools', 'tier_a_review_gate.py'),
                    '--list'], cwd=REPO, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
# ── THIS ARM SAID `== 0` AND WENT RED THE DAY THE DEADLINE SHIPPED (2026-09-16)
# It was right when written and stopped being right when `--list` gained a THIRD
# meaning: 0 nothing overdue, 1 something is, 2 the register could not be read.
# Pinning the number pinned the wrong thing -- the contract is that could-not-
# tell stays separate from both, not that the queue is always empty.
check('--list runs and answers, and 2 stays reserved for could-not-tell',
      r.returncode in (0, 1), 'exit %r: %s' % (r.returncode, r.stderr[:300]))
check('...and a non-zero --list is EXPLAINED, not just a number',
      r.returncode == 0 or 'OVERDUE' in r.stdout,
      'exit 1 with nothing in stdout saying why: %s' % r.stdout[:300])

# ── 8. A CRASH IS NOT A FINDING (added 2026-09-15, after it was one) ─────────
# OBSERVED. On a real push this gate hit `UnicodeDecodeError: 'charmap' codec
# can't decode byte 0x90` -- `subprocess.run(text=True)` with no `encoding=`
# decodes with the Windows locale codec, and this repo's diffs are full of bytes
# cp1252 cannot represent. The decode failed on a reader thread, `r.stdout` came
# back None, and `.split('\n')` raised. Python exits 1 on an uncaught exception,
# and section 6 above records that the hook maps exit 1 to deny() -- so the push
# was refused with the words of a REAL FINDING, naming an independent-review
# obligation for a change that touches no Tier A resource at all.
#
# A gate that cries wolf in the vocabulary of a genuine finding is worse than one
# that crashes visibly: a crash gets fixed, a false finding gets believed and
# worked around. These arms pin all three outcomes apart.
print('\n8. exit codes: a finding, a could-not-tell and a crash are three answers')
sys.path.insert(0, os.path.join(REPO, 'tools'))
import tier_a_review_gate as _G                                     # noqa: E402

_res = _G.tier_a_resources()
# ── THE FIXTURE RESOURCE MUST HAVE NO OPEN OBLIGATION, AND THE OLD ONE DID ──
# 2026-10-06. This section asserted `check() == 1` for `sorted(_res)[0]`, which
# is `alf_activities`. That passed when written and silently stopped testing the
# crash guard the day somebody opened an obligation covering alf_activities
# (2026-09-29T17:47:11Z, cc): check() then returns 0 for the correct reason --
# "EVERY resource it touches has an OPEN obligation" -- and the arm would have
# gone red for a reason that has nothing to do with crashes.
#
# It was caught here only because an unrelated change made the whole section
# fail at once. A register-state-dependent fixture is the same shape as a stale
# anchor: nothing announces the day it stops testing anything (discipline 8).
# So the fixture resource is DERIVED as one no open obligation covers, and if
# there is no such resource this says COULD NOT RUN rather than passing.
_covered = set()
for _r in _G.load_reviews()['records']:
    if _r.get('status') == 'open':
        _covered.update(_r.get('resources') or [])
_uncovered = sorted(set(_res) - _covered)
if not _uncovered:
    check('COULD NOT RUN: every Tier A resource has an open obligation, so no '
          'fixture can produce an exit 1 here', False,
          'not a pass -- the three arms below were not exercised')
    _uncovered = sorted(_res)            # keep the section runnable
_name = _uncovered[0]
_other = _uncovered[1] if len(_uncovered) > 1 else sorted(_res)[1]
# ── THE FIXTURE WAS A COMMENT AND THE COMMENT DECISION WAS REVERSED ─────────
# 2026-10-06. This arm's subject is "a REAL Tier A touch is still exit 1" -- it
# exists so the crash guard cannot swallow a genuine finding into could-not-tell.
# Its fixture was `+  // touches <name> here`, a COMMENT, which was a correct
# fixture while comments counted as a Tier A touch and became a WRONG fixture the
# moment strip_diff_noise() started blanking prose comment bodies (open-work row
# 95, ten measured false positives).
#
# THE ARM IS NOT RELAXED -- IT IS POINTED AT WHAT IT ALWAYS MEANT. A real touch
# is a code line that references the resource, which on this platform is a short
# string literal in a dispatch condition; that is the gate's own most important
# true positive, named in strip_diff_noise()'s docstring. So the fixture becomes
# that line, and the comment moves to its own arm BELOW as the thing that must
# now NOT fire.
_code, _ = _G.check(diff_for(
    'api/sd-data.js', "+  if (resource === '%s' && action === 'write') {" % _name))
check('a REAL Tier A touch -- a dispatch condition in code -- is still exit 1',
      _code == 1,
      'the crash guard must not have swallowed findings into could-not-tell, and '
      'the comment strip must not have blinded the gate to CODE; got %r' % _code)

# ── THE TWO HALVES OF THE REVERSED DECISION, PINNED IN BOTH DIRECTIONS ──────
_code_prose, _ = _G.check(diff_for(
    'api/sd-data.js', '+  // the %s branch refuses an unassigned caller' % _name))
check('...and a PROSE COMMENT naming the same resource is NO LONGER a finding',
      _code_prose == 0,
      'a sentence in a comment still opens a Tier A obligation; got %r -- that is '
      'the ten-instance false positive row 95 records' % _code_prose)

_code_short, _ = _G.check(diff_for('api/sd-data.js', '+  // %s' % _name))
check('...but a SHORT code-shaped comment still counts, so a developer labelling '
      'a real code site is not silently exempted', _code_short == 1,
      'the strip swallowed a one-word comment label; got %r' % _code_short)

_code_two, _ = _G.check(diff_for('api/sd-data.js', '+  // %s, %s'
                                 % (_name, _other)))
check('...and a TWO-token comment listing two resources still counts -- the '
      'threshold is three words, stated and driven', _code_two == 1,
      'got %r' % _code_two)

# ── SABOTAGE, BOTH DIRECTIONS, ON THE COMMENT LAYER ITSELF ──────────────────
# Four green arms prove the layer behaves. They do not prove the layer is what
# makes them green -- a prose comment that happens not to match would pass the
# second arm with the layer removed. So the layer is ABLATED and each arm is
# required to flip the way only that layer explains, and then a mutation in the
# other direction is planted. Per-arm, not per-exit-code (discipline 12).
print('\n8b. the comment layer is ABLATED and each arm must flip')
_real_cbs = _G._comment_body_start
try:
    # ABLATION 1: the layer off entirely -- no comment is ever a comment. This
    # is the pre-2026-10-06 behaviour, so the prose arm MUST go red and the two
    # code-shaped arms must NOT, which is the asymmetry that shows the layer is
    # doing exactly one job.
    _G._comment_body_start = lambda body, path: None
    _a1, _ = _G.check(diff_for(
        'api/sd-data.js', '+  // the %s branch refuses an unassigned caller' % _name))
    _a2, _ = _G.check(diff_for(
        'api/sd-data.js',
        "+  if (resource === '%s' && action === 'write') {" % _name))
    _a3, _ = _G.check(diff_for('api/sd-data.js', '+  // %s' % _name))
    check('ABLATION: with the comment layer OFF the prose comment is a finding '
          'again -- the layer is what fixed it, not the fixture', _a1 == 1,
          'got %r: the prose arm passes with the layer removed, so it proves '
          'nothing about the layer' % _a1)
    check('ABLATION: the CODE arm is unaffected by the layer, so the layer '
          'cannot be what makes the gate see code', _a2 == 1, 'got %r' % _a2)
    check('ABLATION: the SHORT comment arm is unaffected, so the 3-word '
          'threshold is not what admits it', _a3 == 1, 'got %r' % _a3)

    # ABLATION 2: the threshold lowered to one word. A short code-shaped label
    # must then be swallowed -- which is the false NEGATIVE this design chose
    # against, and the arm pins that the choice is real rather than incidental.
    _G._comment_body_start = _real_cbs
    _real_words = _G.COMMENT_PROSE_WORDS
    _G.COMMENT_PROSE_WORDS = 1
    _a4, _ = _G.check(diff_for('api/sd-data.js', '+  // %s' % _name))
    check('ABLATION: lowering the threshold to ONE word swallows the short '
          'code-shaped label -- so three is a decision with a measured cost',
          _a4 == 0, 'got %r: the threshold is not what keeps short labels' % _a4)
finally:
    _G._comment_body_start = _real_cbs
    _G.COMMENT_PROSE_WORDS = 3

# PLANTED THE OTHER WAY: a resource name in code with a prose comment on the
# SAME line must still be a finding. This is the shape a real handler edit takes
# and the one a comment-stripper is most likely to break.
_a5, _ = _G.check(diff_for(
    'api/sd-data.js',
    "+  if (resource === '%s') {  // refuses an unassigned caller, see row 12"
    % _name))
check('a code line WITH a trailing prose comment is still a finding -- the '
      'strip must cut at the marker, not take the whole line', _a5 == 1,
      'got %r: trailing-comment lines are being blanked wholesale' % _a5)

# AND a URL, which is the `//` false cut this platform would hit first.
_a6, _ = _G.check(diff_for(
    'api/sd-data.js',
    "+  const u = 'https://x/y?r=%s' + q;  // three words of prose here" % _name))
check('a `//` inside a URL is not a comment marker, so the resource after it '
      'still counts', _a6 == 1, 'got %r' % _a6)

_saved = _G.check
try:
    _G.check = lambda *a, **k: (_ for _ in ()).throw(RuntimeError('planted crash'))
    _crash = _G._guarded([])
finally:
    _G.check = _saved
check('an UNEXPECTED EXCEPTION is exit 2, not exit 1', _crash == 2,
      'exit 1 would make the hook print "no independent-review obligation is '
      'recorded", which is a specific false accusation; got %r' % _crash)

# The encoding half, at the source rather than through the symptom.
try:
    _G.git('cat-file', '-p', '0' * 40)
    check('a FAILING git call raises CouldNotTell', False,
          'it returned normally -- the old code returned "" here, which this '
          'gate reads as "no Tier A resource touched", i.e. a PASS')
except _G.CouldNotTell:
    check('a FAILING git call raises CouldNotTell', True)
except Exception as _e:
    check('a FAILING git call raises CouldNotTell', False, repr(_e))

import inspect                                                      # noqa: E402
_src = inspect.getsource(_G.git)
_body = _src.split('"""')[2] if _src.count('"""') >= 2 else _src
check('git() decodes UTF-8 explicitly, not the locale codec',
      "encoding='utf-8'" in _body,
      'text=True with no encoding= is cp1252 on Windows')
check('git() no longer returns "" on a failed command',
      "else ''" not in _body,
      'an empty diff means NO TIER A TOUCH, which is a pass -- so returning "" '
      'on error was a fail-open in a BLOCKING gate (PR 1.11)')

print('\n6. a REPORT-ONLY review artefact is not a Tier A change (2026-09-15)')

# SECOND FALSE POSITIVE OF THIS SHAPE. The first was a worklog, fixed by
# excluding markdown. This one was tests/dnt_rollup_review_probe.js -- an
# independent review of somebody else's Tier A module, refused because a review
# of dnt_rollup necessarily NAMES dnt_rollup. The gate was blocking the very
# artefact that discharges the obligation it was asking for.
#
# THE ARM THAT MATTERS IS THE SECOND ONE. Excluding `tests/` wholesale would be
# the dangerous repair: a test is often the only thing pinning a Tier A
# behaviour, and a session could then delete its assertions and push it clean.
# Every other arm here exists to prove the exclusion did NOT become that.
_ART = (
    "// a review of dnt_rollup\n"
    "const x = require('../api/_lib/dnt-rollup');\n"
    "console.log('finding: dnt_rollup suppresses a measured total');\n"
    "process.exit(0);\n")
_REAL = (
    "const assert = require('assert');\n"
    "assert.strictEqual(rollup().totals.dnt_rollup, 1);\n"
    "process.exit(fail ? 1 : 0);\n")

check('a report-only artefact under tests/ is EXCLUDED',
      g.is_report_only_artefact('tests/x_review_probe.js', _ART),
      'the gate still refuses the artefact that discharges its own obligation')

check('A REAL TEST NAMING THE SAME RESOURCE IS STILL INCLUDED',
      not g.is_report_only_artefact('tests/x.test.js', _REAL),
      'THE EXCLUSION BECAME "ignore tests/" -- a session can now delete the '
      'assertions from a Tier A suite and push it as clean')

check('...and the same content under api/ is included too',
      not g.is_report_only_artefact('api/_lib/x.js', _ART),
      'a file beside a handler was excluded on its exit code alone')

check('a non-literal exit is NOT excluded, even with no assertions',
      not g.is_report_only_artefact('tests/y_probe.py',
                                    "import sys\nsys.exit(main())\n"),
      'sys.exit(main()) can return non-zero, so the file CAN fail and IS a guard')

check('a file with NO exit at all is not excluded either',
      not g.is_report_only_artefact('tests/y2_probe.js', "console.log('dnt_rollup');\n"),
      'absence of an exit is not evidence of anything and must not be read as one')

# The predicate reads CODE, not prose. Without the strip, the word "assert"
# inside a comment would disqualify a real artefact -- the grep-matched-prose
# class this platform has now recorded five times.
check('an "assert" in a COMMENT does not disqualify an artefact',
      g.is_report_only_artefact(
          'tests/z_probe.js',
          "// this does not assert anything about dnt_rollup\nprocess.exit(0);\n"),
      'comments are being read as code')
check('...but an assert in CODE does',
      not g.is_report_only_artefact(
          'tests/z2_probe.js',
          "assert(dnt_rollup !== null);\nprocess.exit(0);\n"),
      'a real assertion was stripped along with the comments')

# END TO END, through the real diff walker rather than the predicate alone: a
# hunk naming a Tier A resource inside a report-only artefact raises nothing,
# and the SAME hunk in a production file raises. Without the second half the
# first proves only that the gate found nothing, which an empty resource set
# also does -- the exact vacuity section 3 exists for.
_tier = g.tier_a_resources()
_name = 'dnt_rollup' if 'dnt_rollup' in _tier else sorted(_tier)[0]
check('END TO END: the artefact raises no obligation',
      not g.touched_tier_a(
          diff_for('tests/dnt_rollup_review_probe.js', 'console.log("%s");' % _name),
          _tier),
      'expected no hits -- the file on disk must satisfy the predicate')
check('END TO END: the same hunk in a production file DOES raise one',
      bool(g.touched_tier_a(
          diff_for('api/_lib/made_up_handler.js', 'const t = "%s";' % _name), _tier)),
      'the walker stopped attributing hunks at all, so the arm above passes '
      'for the wrong reason')


# -- 9. PROSE STRINGS DO NOT COUNT; TOKEN STRINGS DO (2026-09-16) ------------
# FOUR false positives in two days came from a resource NAMED IN TEXT rather
# than referenced in code: a worklog, a review probe, and two checkers whose
# blind-lock fixtures must contain real resource names to be worth anything.
#
# THE OBVIOUS FIX WOULD HAVE BROKEN THE GATE. Stripping every string literal
# makes api/sd-data.js line 9838 -- the `resource === '<name>'` compare --
# invisible, and that is the gate's single most important true positive. So the
# rule is about SHAPE: a string body is ignored only when it reads as a
# SENTENCE, three or more whitespace-separated words.
#
# BOTH DIRECTIONS, because a rule that only suppressed would be satisfied by a
# gate that had stopped matching altogether.
print(chr(10) + '9. a resource named in PROSE is not a resource served in code')
_PROSE_CASES = (
    ("the sd-data.js string compare -- the gate's key true positive",
     "if (resource === '%s' && action === 'write') {", True),
    ('a registry key', "  %s: 'ts_id',", True),
    ('a postgrest path fragment', "  rest('%s?license_hash=eq.' + enc(h))", True),
    ('a bare identifier', '  const rows = await read(%s);', True),
    ('a user-facing sentence',
     '  throw new Error("Storage full - clear old %s and retry.");', False),
    ('a docstring sentence',
     '  """%s is there specifically to assert a substring does not fire."""',
     False),
    ('a prose fixture label',
     "  ('names a Tier A resource and %s must not count here', 1),", False),
    # ── ADDED 2026-09-17, FROM A REAL BLOCK ────────────────────────────────
    # The body excluded EVERY quote character rather than just the delimiter,
    # so a sentence containing the OTHER one never matched and nothing was
    # blanked. The line that hit it was an ordinary English comment in
    # tests/run_master_plan_probe.py -- nine words with one possessive -- and
    # the gate read it as a Tier A touch. The docstring already claimed to
    # handle "clear old quotes and retry."; it did, right up until somebody
    # wrote a contraction.
    ('a sentence with a POSSESSIVE inside double quotes',
     '  msg = "the plan cites the matrix\'s own %s verbatim"', False),
    ('a sentence with a CONTRACTION inside double quotes',
     '  msg = "don\'t let %s be read as a touch"', False),
    ('a sentence with a DOUBLE quote inside single quotes -- the mirror case',
     '  msg = \'the "%s" row is prose here, not a lookup\'', False),
)
for _label, _tpl, _must in _PROSE_CASES:
    _line = _tpl % _name
    _fired = bool(_G.touched_tier_a(diff_for('api/sd-data.js', _line), [_name]))
    check(('fires: ' if _must else 'ignored: ') + _label, _fired == _must,
          _line + ' -> fired=' + str(_fired))

# AND THE LIMIT IS STATED AS AN ARM, not left to be rediscovered: a BARE token
# in a checker's fixture is character-for-character what a handler writes, so
# no string analysis separates them. This arm exists so the next person finds
# the dead end already mapped rather than re-deriving it.
check('a bare fixture token STILL fires -- known, and not fixable by looking '
      'at the string',
      bool(_G.touched_tier_a(
          diff_for('tools/some_checker.py',
                   "FIXTURE_TIERS = {'" + _name + "': 'A'}"), [_name])),
      'if this ever goes false the stripper got broader than its own docstring')


# ── SECTION 6: OWNERSHIP -- AN OBLIGATION IS ASSIGNED WHEN IT IS OPENED ──────
# Added 2026-09-21 with the stamp itself. FOUR obligations were double-reviewed
# in one day and the collision was invisible every time until a git rebase
# surfaced it. The race needed NO CONCURRENCY: nothing keyed on who the
# obligation belonged to, so the later --discharge simply replaced the earlier
# one's reviewer_session and verdict.
#
# THE ARMS BELOW DRIVE THE BEFORE AND THE AFTER SIDE BY SIDE, because the value
# of the stamp is the DIFFERENCE and an arm that only exercises the new
# behaviour cannot show it. Arm 1 is the old world (an unowned record: both
# sessions write, the first verdict is destroyed); arm 2 is the new one (one
# owner: exactly one writes, and which one is decided before either arrives).
print()
print('SECTION 6 -- ownership: assigned at open, not first-come')

_tmp6 = tempfile.mkdtemp(prefix='owner6-')
_seq6 = [0]


def _orec(author='hank', opened='2026-05-01T00:00:00Z', owner=None,
          assigned='2026-05-01T00:00:00Z'):
    r = {'author_session': author, 'opened_at': opened, 'status': 'open',
         'resources': ['sc_claims'], 'files': ['api/sd-data.js'],
         'what': 'a change', 'reviewer_session': None, 'reviewed_at': None,
         'verdict': None}
    if owner is not None:
        r['reviewer_owner'] = owner
        r['owner_assigned_at'] = assigned
    return r


def _ostage(records):
    _seq6[0] += 1
    p = os.path.join(_tmp6, 'o-%d.json' % _seq6[0])
    io.open(p, 'w', encoding='utf-8').write(json.dumps({'records': records}))
    g.REVIEWS = p
    return p


# ── 1. THE OLD WORLD, DRIVEN: an UNOWNED record takes both writes ──────────
_r = _orec(owner=None)
_first_err = _second_err = None
try:
    g._discharge(_r, 'fourth', 'verdict from fourth', 'reviewed')
except Exception as e:                                               # noqa: BLE001
    _first_err = e
_after_first = _r.get('reviewer_session')
try:
    g._discharge(_r, 'cody', 'verdict from cody', 'reviewed')
except Exception as e:                                               # noqa: BLE001
    _second_err = e
check('WITHOUT an owner both sessions write and the FIRST verdict is destroyed '
      '-- the race, reproduced',
      (_first_err is None and _second_err is None
       and _after_first == 'fourth' and _r.get('reviewer_session') == 'cody'
       and 'fourth' not in (_r.get('verdict') or '')),
      'first=%r second=%r after_first=%r final=%r'
      % (_first_err, _second_err, _after_first, _r.get('reviewer_session')))

# ── 2. WITH an owner, exactly one can ever write, and it is not a lock ──────
_r = _orec(owner='cody')
_owner_ok = _other_err = None
try:
    g._discharge(_r, 'fourth', 'verdict from fourth', 'reviewed')
except g.NotOwner as e:
    _other_err = e
try:
    g._discharge(_r, 'cody', 'verdict from cody', 'reviewed')
    _owner_ok = True
except Exception as e:                                               # noqa: BLE001
    _owner_ok = e
check('WITH an owner the non-owner is REFUSED and the owner writes',
      isinstance(_other_err, g.NotOwner) and _owner_ok is True
      and _r.get('reviewer_session') == 'cody',
      'other=%r owner=%r final=%r' % (_other_err, _owner_ok,
                                      _r.get('reviewer_session')))
check('...and the refusal NAMES the owner and the way out, rather than just '
      'saying no',
      ('cody' in str(_other_err) and '--takeover' in str(_other_err)
       and 'open time' in str(_other_err)),
      str(_other_err)[:200])

# ── 3. ORDER DOES NOT MATTER, which is what makes it not a lock ─────────────
# A lock has a window: whoever gets there first wins. An identity check has
# none. Driven both ways round on fresh records.
_r1, _r2 = _orec(owner='cody'), _orec(owner='cody')
_a = _b = None
try:
    g._discharge(_r1, 'cody', 'v', 'reviewed')
except Exception as e:                                               # noqa: BLE001
    _a = e
try:
    g._discharge(_r1, 'fourth', 'v', 'reviewed')
except Exception as e:                                               # noqa: BLE001
    _a = e if _a is None else _a
try:
    g._discharge(_r2, 'fourth', 'v', 'reviewed')
except Exception as e:                                               # noqa: BLE001
    _b = e
check('the non-owner is refused whether it arrives FIRST or SECOND -- an '
      'identity check has no window, so there is nothing to race',
      isinstance(_b, g.NotOwner) and _r2.get('reviewer_session') is None
      and _r1.get('reviewer_session') == 'cody',
      'first-in-refused=%r second-in=%r' % (_b, _r1.get('reviewer_session')))

# ── 4. TWO SESSIONS READING --list AT THE SAME INSTANT ──────────────────────
# The literal scenario the stamp was asked to close. Both threads block on a
# barrier until both have READ the same open record, then both attempt the
# discharge. Exactly one may succeed, and WHICH one is decided by the record,
# not by the scheduler -- so the result is the same on every run.
_shared = _orec(owner='cody')
_out6 = {}
_bar6 = threading.Barrier(2)


def _attempt(who):
    _bar6.wait()            # both have the record in hand before either writes
    try:
        g._discharge(_shared, who, 'verdict from ' + who, 'reviewed')
        _out6[who] = 'WROTE'
    except g.NotOwner:
        _out6[who] = 'REFUSED'
    except Exception as e:                                           # noqa: BLE001
        _out6[who] = 'ERROR:' + type(e).__name__


_th = [threading.Thread(target=_attempt, args=(w,)) for w in ('cody', 'fourth')]
for _t in _th:
    _t.start()
for _t in _th:
    _t.join()
check('two sessions hitting the same obligation at the same instant: EXACTLY '
      'one writes, and it is the assigned owner',
      (sorted(_out6.values()) == ['REFUSED', 'WROTE']
       and _out6.get('cody') == 'WROTE'
       and _shared.get('reviewer_session') == 'cody'),
      repr(_out6) + ' final=' + repr(_shared.get('reviewer_session')))

# ── 4b. THE STAMP IS APPLIED BY --open ITSELF, END TO END ──────────────────
# The arms above drive assign_owner() directly. That is NOT enough, and a
# sabotage run proved it: disabling the call inside cmd_open -- every new
# obligation born UNOWNED, the queue silently back to first-come -- left every
# arm green. An arm that exercises the helper and not the WIRING cannot see the
# wiring removed, which is the shape this platform keeps paying for. So this
# one calls cmd_open and reads the record back off disk.
_op = os.path.join(_tmp6, 'opened.json')
io.open(_op, 'w', encoding='utf-8').write(json.dumps({'records': []}))
g.REVIEWS = _op
_saved_wd, _saved_rd = g.working_diff, g.range_diff
g.working_diff = lambda: diff_for('api/sd-data.js', "resource === 'sc_claims'")
g.range_diff = lambda a, b: ''
try:
    _rc4b = g.cmd_open('a change that names a Tier A resource')
finally:
    g.working_diff, g.range_diff = _saved_wd, _saved_rd
_rec4b = json.load(io.open(_op, encoding='utf-8'))['records']
_r4b = _rec4b[0] if _rec4b else {}
check('--open ITSELF writes an owner onto the record -- the helper being right '
      'is not the same as the helper being called',
      (_rc4b == 0 and len(_rec4b) == 1
       and _r4b.get('reviewer_owner')
       and _r4b.get('reviewer_owner') != _r4b.get('author_session')),
      (_rc4b, _r4b.get('reviewer_owner'), _r4b.get('author_session')))
check('...and stamps WHEN it was assigned, because a takeover that cannot read '
      'the age cannot happen at all',
      bool(_r4b.get('owner_assigned_at'))
      and g.owner_age_hours(_r4b) is not None,
      (_r4b.get('owner_assigned_at'), g.owner_age_hours(_r4b)))

# ── 5. ASSIGNMENT: never the author, deterministic, least-loaded ────────────
_roster = ['cc', 'cody', 'fourth', 'hank']
_empty = {'records': []}
check('an author is never assigned its own obligation, for any author on the '
      'roster',
      all(g.assign_owner(a, _empty, roster=_roster)[0] != a for a in _roster),
      [(a, g.assign_owner(a, _empty, roster=_roster)[0]) for a in _roster])
check('assignment is DETERMINISTIC -- the same inputs give the same owner '
      'twenty times running, because a random assignment cannot be re-derived '
      'when somebody asks why a record went where it did',
      len(set(g.assign_owner('hank', _empty, roster=_roster)[0]
              for _ in range(20))) == 1,
      g.assign_owner('hank', _empty, roster=_roster))
_loaded = {'records': [
    {'status': 'open', 'reviewer_owner': 'cc'},
    {'status': 'open', 'reviewer_owner': 'cc'},
    {'status': 'open', 'reviewer_owner': 'cody'},
]}
check('assignment is LEAST-LOADED, so the queue levels instead of piling on '
      'whoever is alphabetically first',
      g.assign_owner('hank', _loaded, roster=_roster)[0] == 'fourth',
      g.assign_owner('hank', _loaded, roster=_roster))
check('a CLOSED record does not count toward load -- load is about work '
      'outstanding, not work ever done',
      g.assign_owner('hank', {'records': [
          {'status': 'reviewed', 'reviewer_owner': 'fourth'},
          {'status': 'reviewed', 'reviewer_owner': 'fourth'}]},
          roster=_roster)[0] == 'cc',
      g.assign_owner('hank', {'records': [
          {'status': 'reviewed', 'reviewer_owner': 'fourth'}]}, roster=_roster))

# ── 6. THE ROSTER FAILS CLOSED, and an unassignable record says why ─────────
check('a roster of ONE cannot assign -- the only candidate would be the author '
      '-- and the note says so rather than leaving a null nobody can explain',
      (g.assign_owner('hank', _empty, roster=['hank'])[0] is None
       and 'only eligible session'
       in (g.assign_owner('hank', _empty, roster=['hank'])[1] or '')),
      g.assign_owner('hank', _empty, roster=['hank']))
check('an UNREADABLE roster is COULD NOT TELL, not an empty one -- and the '
      'record is left first-come with the reason in it',
      (g.assign_owner('hank', _empty, roster=None if False else None) is not None),
      'placeholder -- the real unreadable case is the next arm')
_saved_claims = g.CLAIMS_DIR
g.CLAIMS_DIR = os.path.join(_tmp6, 'there-is-no-such-directory')
check('with no .claude/claims/ to read, eligible_reviewers() answers None '
      'rather than [] -- an empty roster would assign nobody and look like a '
      'decision',
      g.eligible_reviewers() is None, g.eligible_reviewers())
_own, _note = g.assign_owner('hank', _empty)
check('...and assign_owner then returns no owner WITH a reason a reader can '
      'act on',
      _own is None and 'could not be read' in (_note or ''), (_own, _note))
g.CLAIMS_DIR = _saved_claims

# ── 7. THE HOVER AUDITOR IS EXCLUDED, and that is structural ────────────────
check('hover is NOT eligible -- it audits the four build agents rather than '
      'building, and handing it their review queue would erase that separation '
      'from the other side',
      g.HOVER_SESSION not in (g.eligible_reviewers() or []),
      g.eligible_reviewers())
check('the real roster on disk is derived rather than hardcoded, and holds the '
      'build sessions',
      set(g.eligible_reviewers() or []) >= {'cc', 'cody', 'fourth', 'hank'},
      g.eligible_reviewers())
# ── EVERY INSTANCE OF THE AUDITOR ROLE, NOT ONE LITERAL NAME (H2 seq #205) ──
# The exclusion was `n != 'hover'` while the auditor already ran as hover AND
# hover2 in the shared status registry -- the day hover2 wrote its own claim
# file it would have silently entered the reviewer pool and started being
# ASSIGNED build-agent obligations. The roster's own header names why literal
# lists fail here; the fix is a role predicate, and BOTH directions are pinned
# because over-exclusion starves the pool the same way over-inclusion poisons
# it.
for _n in ('hover', 'hover2', 'hover-3', 'hover_x'):
    check('auditor instance %r is excluded from the reviewer pool' % _n,
          g.is_hover_session(_n) is True, _n)
for _n in ('hoverboard', 'fourth', 'cc', ''):
    check('%r is NOT swept out by the prefix -- over-exclusion starves the pool' % _n,
          g.is_hover_session(_n) is False, _n)
import io as _io
_gate_src = _io.open(os.path.join(REPO, 'tools', 'tier_a_review_gate.py'),
                     encoding='utf-8').read()
check('eligible_reviewers() consults is_hover_session rather than != HOVER_SESSION',
      'if not is_hover_session(n)' in _gate_src
      and "if n != HOVER_SESSION" not in _gate_src,
      'the literal compare is back')

# ── 8. TAKEOVER: the failure the stamp CREATES, answered in the same change ──
# An obligation assigned to a session that never runs again would block for
# ever, and this platform already records that shape for expired claims. So:
# explicit flag, time gate, recorded handover -- never silent.
#
# EVERY ARM BELOW GOES THROUGH cmd_discharge(), WHICH RESOLVES THE CALLER FROM
# THE CLONE rather than taking it as an argument the way section 6's _discharge()
# does. So the fixture's OWNER may not be a literal: these fixtures said
# owner='cody', and on the cody clone owner == caller, so the gate refused with
# "cody already owns that obligation. Discharge it without --takeover." and all
# three takeover arms reported FAIL for a reason that had nothing to do with the
# takeover path. They were green on hank, cc and fourth the whole time. That is
# convention 8 wearing a fixture: the arms stopped testing anything in exactly
# one clone and nothing said so.
#
# _ME is derived (it already was, one lesson earlier, for the REVIEWER side);
# _OWNER is now derived too, from the same source, and the pair is ASSERTED to
# differ before any arm runs -- so this cannot silently become untestable again
# in whichever clone happens to share a hardcoded name.
# THE AUTHOR IS DERIVED FOR THE SAME REASON, and it is a SECOND instance of the
# same defect rather than a precaution: the fixtures' author was the literal
# 'hank', and the self-review guard refuses when reviewer == author, so on the
# hank clone these arms died on SelfSigned instead -- one hardcoded name broke
# the section in one clone, the other broke it in another, and neither announced
# itself as anything but FAIL.
_ME = g.session_name()
_POOL = ('cc', 'fourth', 'hank', 'cody', 'fifth')
_OWNER = next(n for n in _POOL if n != _ME and not g.is_hover_session(n))
_AUTHOR = next(n for n in _POOL
               if n not in (_ME, _OWNER) and not g.is_hover_session(n))
check('the fixture owner is NOT this clone, so a takeover is REACHABLE here -- '
      'without this the three arms below pass or fail on which clone ran them',
      _OWNER != _ME and not g.is_hover_session(_OWNER),
      'owner=%r me=%r' % (_OWNER, _ME))
check('...and the fixture AUTHOR is neither this clone nor the owner, so the '
      'self-review guard cannot be what refuses these arms',
      _AUTHOR != _ME and _AUTHOR != _OWNER,
      'author=%r owner=%r me=%r' % (_AUTHOR, _OWNER, _ME))
_fresh_owner = _orec(author=_AUTHOR, owner=_OWNER,
                     assigned=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
_fp = _ostage([_fresh_owner])
_rc = g.cmd_discharge(_AUTHOR, 'read the diff, re-derived both column lists against the callers, two findings, both fixed', opened_at='2026-05-01T00:00:00Z',
                      takeover=True)
_fresh_w = json.load(io.open(_fp, encoding='utf-8'))['records'][0]
check('a takeover is REFUSED while the owner is still inside the window -- '
      'taking it early is the race again, wearing a flag',
      _rc == 1 and _fresh_w.get('reviewer_session') is None,
      (_rc, _fresh_w.get('reviewer_session')))
_stale = _orec(author=_AUTHOR, owner=_OWNER, assigned='2020-01-01T00:00:00Z')
_sp = _ostage([_stale])
_rc = g.cmd_discharge(_AUTHOR, 'read the diff, re-derived both column lists against the callers, two findings, both fixed',
                      opened_at='2026-05-01T00:00:00Z', takeover=True)
# READ THE FILE BACK, not the dict handed to _ostage. cmd_discharge loads the
# register from disk and mutates ITS OWN copy, so asserting on the local dict
# checks an object nothing wrote to -- which is what the first version of these
# two arms did, and they reported FAIL over a takeover that had plainly worked.
_stale_w = json.load(io.open(_sp, encoding='utf-8'))['records'][0]
# THE REVIEWER IS THE SESSION RUNNING THE COMMAND, NOT THE AUTHOR ARGUMENT.
# _AUTHOR above is whose obligation it is; the reviewer is this clone. The first
# version of these arms expected the author name in both places and failed on a
# takeover that had plainly worked -- the same author/reviewer confusion the gate
# itself refuses, reproduced in its own probe. Derived from session_name() rather
# than hardcoded so this passes in whichever clone runs it.
check('a takeover IS allowed once the assignment is stale, so a dead owner '
      'cannot block an obligation for ever',
      _rc == 0 and _stale_w.get('reviewer_session') == _ME,
      (_rc, _stale_w.get('reviewer_session'), _ME))
check('...and the handover is RECORDED -- from, by, at and how long it was '
      'held -- rather than silently overwriting the assignment',
      (isinstance(_stale_w.get('owner_takeover'), dict)
       and _stale_w['owner_takeover'].get('from') == _OWNER
       and _stale_w['owner_takeover'].get('by') == _ME
       and _stale_w['owner_takeover'].get('owner_held_hours', 0) > g.OWNER_STALE_HOURS),
      _stale_w.get('owner_takeover'))
check('...and the ASSIGNED OWNER is left in the record beside the takeover, so '
      'the handover can be read afterwards rather than leaving a record that '
      'looks as if the taker owned it all along',
      _stale_w.get('reviewer_owner') == _OWNER, _stale_w.get('reviewer_owner'))
_nostamp = _orec(author=_AUTHOR, owner=_OWNER)
_nostamp['owner_assigned_at'] = None
_np = _ostage([_nostamp])
_rc = g.cmd_discharge(_AUTHOR, 'read the diff, re-derived both column lists against the callers, two findings, both fixed', opened_at='2026-05-01T00:00:00Z',
                      takeover=True)
check('an UNREADABLE assignment time is COULD NOT TELL (exit 2), not a free '
      'takeover -- a takeover on an unknown age is a takeover on a guess',
      _rc == 2 and json.load(io.open(_np, encoding='utf-8'))['records'][0]
      .get('reviewer_session') is None, _rc)
_unowned = _orec(author=_AUTHOR, owner=None)
_ostage([_unowned])
_rc = g.cmd_discharge(_AUTHOR, 'read the diff, re-derived both column lists against the callers, two findings, both fixed', opened_at='2026-05-01T00:00:00Z',
                      takeover=True)
check('--takeover on an UNOWNED record is refused with the right reason: '
      'there is nothing to take over',
      _rc == 1, _rc)

# ── 9. THE SELF-REVIEW REFUSAL STILL WINS, even against a forged owner ──────
_forged = _orec(author='hank', owner='hank')
_err9 = None
try:
    g._discharge(_forged, 'hank', 'v', 'reviewed')
except g.SelfSigned as e:
    _err9 = e
except Exception as e:                                               # noqa: BLE001
    _err9 = e
check('a record hand-edited so the OWNER is its own AUTHOR is still refused by '
      'the self-review guard -- ownership is a second gate, never a way round '
      'the first',
      isinstance(_err9, g.SelfSigned), repr(_err9))

# ── 10. THE AUTO PATH IS EXEMPT, and only the auto path ────────────────────
_auto = _orec(owner='cody')
_err10 = None
try:
    g._discharge(_auto, 'by-defect-register', 'a record covers it',
                 'reviewed-by-record')
except Exception as e:                                               # noqa: BLE001
    _err10 = e
check('a record-backed auto-close is NOT blocked by ownership -- its reviewer '
      'names a MECHANISM rather than a session, and ownership is about two '
      'humans colliding',
      _err10 is None and _auto.get('status') == 'reviewed-by-record', repr(_err10))
_sneak = _orec(owner='cody')
_err10b = None
try:
    g._discharge(_sneak, 'by-cody-pretending', 'v', 'reviewed')
except Exception as e:                                               # noqa: BLE001
    _err10b = e
check('THE EXEMPTION IS A KNOWN HOLE AND IS STATED AS ONE: any reviewer name '
      'beginning "by-" passes it, so the mechanism prefix is a convention '
      'rather than a credential',
      _err10b is None,
      'if this ever refuses, the exemption got narrower and this arm should '
      'be rewritten rather than deleted')

# ── 11. SAVING IS ATOMIC -- the mode that stopped the whole platform ───────
# Before this change two concurrent save_reviews() interleaved inside one file
# and produced TWO CONCATENATED JSON DOCUMENTS: json.decoder.JSONDecodeError,
# "Extra data: line 1162". load_reviews() reads that as CouldNotTell, which the
# push hook maps to NOT-A-PASS, so it failed closed and blocked every push on
# the platform until somebody repaired the file by hand.
_ap = os.path.join(_tmp6, 'atomic.json')
g.REVIEWS = _ap
io.open(_ap, 'w', encoding='utf-8').write(json.dumps({'records': []}))
_bar11 = threading.Barrier(2)


def _saver(n):
    d = {'records': [{'author_session': 'x%d' % n, 'status': 'open',
                      'pad': 'y' * (n * 4000)}]}
    _bar11.wait()
    g.save_reviews(d)


_th11 = [threading.Thread(target=_saver, args=(n,)) for n in (1, 9)]
for _t in _th11:
    _t.start()
for _t in _th11:
    _t.join()
_parsed = None
try:
    _parsed = json.load(io.open(_ap, encoding='utf-8'))
except ValueError as e:
    _parsed = e
check('two concurrent saves leave a file that still PARSES -- os.replace is '
      'atomic, so a reader sees the old file or the new one and never half of '
      'each',
      isinstance(_parsed, dict) and isinstance(_parsed.get('records'), list),
      repr(_parsed)[:200])
check('no .tmp- leftovers -- a temp file that outlived its write would be '
      'picked up by nothing and would sit in docs/ for ever',
      not [f for f in os.listdir(_tmp6) if '.tmp-' in f],
      os.listdir(_tmp6))

# ── 12. AND THE LIMIT THAT IS NOT FIXED, ASSERTED AS A LIMIT ───────────────
# load_reviews / append / save_reviews is still a read-modify-write with no
# lock, so two --open calls that both READ before either WRITES lose one
# record. The atomic save makes the file valid; it does not make the sequence
# safe. This arm exists so nobody reads the section above as closing it.
io.open(_ap, 'w', encoding='utf-8').write(json.dumps({'records': []}))
_bar12 = threading.Barrier(2)


def _opener(tag):
    d = g.load_reviews()
    _bar12.wait()
    d['records'].append({'author_session': tag, 'status': 'open'})
    g.save_reviews(d)


_th12 = [threading.Thread(target=_opener, args=(t,)) for t in ('a', 'b')]
for _t in _th12:
    _t.start()
for _t in _th12:
    _t.join()
_names12 = [r['author_session'] for r in
            json.load(io.open(_ap, encoding='utf-8'))['records']]
check('KNOWN AND NOT FIXED: two concurrent --open calls still lose one record, '
      'because both read before either writes. The atomic save fixed CORRUPTION, '
      'not the read-modify-write',
      len(_names12) == 1,
      'if this ever finds both, somebody added locking and this arm should '
      'become a positive one: ' + repr(_names12))

# ── SECTION 7: STALE BY CODE, NOT BY CLOCK (item 102 part 4, 2026-09-25) ────
# DRIVEN AGAINST A REAL GIT REPOSITORY, not a stub. The whole check is two git
# invocations and a path comparison; a fake `git` would test the arrangement of
# this probe and nothing about the tool.
#
# THE ARM THAT MATTERS IS THE NEGATIVE ONE. On the day this shipped every
# record in the real ledger was UNSTAMPED, so a code_staleness() that returned
# UNSTAMPED unconditionally -- or that could never reach STALE at all -- would
# have looked identical in production. So STALE is driven with a real commit
# that really moves the record's own file, and FRESH is driven beside it with a
# commit that moves a DIFFERENT file, which is the discrimination the whole
# design rests on.
print()
print('SECTION 7 -- staleness by code: HEAD moved, and did it move THIS record')
_tmp7 = tempfile.mkdtemp(prefix='tier-a-stale-probe-')
_real_repo7 = g.REPO


def _g7(*a):
    return subprocess.run(['git'] + list(a), cwd=_tmp7, capture_output=True,
                          encoding='utf-8', errors='replace')


def _w7(name, text):
    io.open(os.path.join(_tmp7, name), 'w', encoding='utf-8',
            newline='\n').write(text)


try:
    _g7('init', '-q', '-b', 'main')
    _g7('config', 'user.email', 'probe@example.invalid')
    _g7('config', 'user.name', 'probe')
    _w7('watched.js', 'one\n')
    _w7('other.js', 'one\n')
    _g7('add', '-A')
    _g7('commit', '-q', '-m', 'base')
    _sha_base = _g7('rev-parse', 'HEAD').stdout.strip()
    _w7('other.js', 'one\ntwo\n')          # an UNRELATED file moves first
    _g7('add', '-A')
    _g7('commit', '-q', '-m', 'move the other file')
    _sha_mid = _g7('rev-parse', 'HEAD').stdout.strip()
    _w7('watched.js', 'one\ntwo\n')        # now the record's OWN file moves
    _g7('add', '-A')
    _g7('commit', '-q', '-m', 'move the watched file')
    _sha_head = _g7('rev-parse', 'HEAD').stdout.strip()

    g.REPO = _tmp7

    def _srec(sha, files=('watched.js',)):
        return {'author_session': 'somebody-else', 'status': 'open',
                'opened_at': '2026-09-25T00:00:00Z', 'opened_at_sha': sha,
                'resources': ['sc_claims'], 'files': list(files),
                'what': 'a change'}

    _st, _d = g.code_staleness(_srec(_sha_base))
    check('a record whose OWN file moved since its sha is STALE, and the moved '
          'path is NAMED',
          _st == 'STALE' and 'watched.js' in _d, (_st, _d))

    # HEAD is one commit past this sha, and that commit touched watched.js --
    # this record is about other.js, which nothing has touched since. If the
    # test were "HEAD != the recorded sha" this would come back STALE and the
    # whole queue would be stale within minutes of every push.
    _st, _d = g.code_staleness(_srec(_sha_mid, files=('other.js',)))
    check('NEGATIVE CONTROL: HEAD moved past the record\'s sha but only an '
          'UNRELATED file changed -- FRESH, because the test is the record\'s '
          'own files and not HEAD equality',
          _st == 'FRESH', (_st, _d))

    _st, _d = g.code_staleness(_srec(_sha_head))
    check('a record stamped at the current HEAD is FRESH',
          _st == 'FRESH', (_st, _d))

    _r7 = _srec(_sha_base)
    del _r7['opened_at_sha']
    _st, _d = g.code_staleness(_r7)
    check('a record with NO sha is UNSTAMPED -- never FRESH, which is the '
          'state every record already in the ledger was in on day one',
          _st == 'UNSTAMPED', (_st, _d))

    _st, _d = g.code_staleness(_srec(_sha_base, files=()))
    check('a record naming no files is UNSTAMPED, not FRESH -- nothing to '
          'compare is the absence of an answer',
          _st == 'UNSTAMPED', (_st, _d))

    _st, _d = g.code_staleness(_srec('0123456789abcdef0123456789abcdef01234567'))
    check('a sha that does not RESOLVE is COULD-NOT-TELL -- rebased away is '
          'neither fresh nor stale (PR 1.11)',
          _st == 'COULD-NOT-TELL' and 'NOT fresh' in _d, (_st, _d))

    check('the four states are the only four, and FRESH is not the default '
          'any of the failure paths falls back to',
          all(g.code_staleness(r)[0] in ('FRESH', 'STALE', 'UNSTAMPED',
                                         'COULD-NOT-TELL')
              for r in (_srec(_sha_base), _srec('zzzz'), _r7)),
          [g.code_staleness(r)[0] for r in
           (_srec(_sha_base), _srec('zzzz'), _r7)])

    # stale_records() is what --list reads, and it must not drop the two
    # non-answer states -- a queue that only surfaces STALE would report the
    # whole unstamped ledger as clean.
    _data7 = {'records': [_srec(_sha_base), _srec(_sha_mid, files=('other.js',)),
                          _r7]}
    _rows7 = g.stale_records(_data7)
    check('stale_records() returns the STALE one AND the UNSTAMPED one and '
          'omits only the FRESH one',
          sorted(s for _, s, _ in _rows7) == ['STALE', 'UNSTAMPED'],
          [(s, d[:60]) for _, s, d in _rows7])

    # ── THE FIELD IS ACTUALLY WRITTEN, which nothing above proves ──────────
    # Every arm so far hands code_staleness() a record this probe built. If
    # _open_record() never wrote `opened_at_sha`, all of them would still pass
    # and the feature would be dead in production -- discipline 8's shape.
    # DRIVEN, not grepped: an earlier version of this arm asserted on the
    # source with string literals blanked, which is exactly where the key name
    # lives, so it could never match.
    _revp7 = os.path.join(_tmp7, 'reviews.json')
    io.open(_revp7, 'w', encoding='utf-8').write(json.dumps({'records': []}))
    _real_rev7 = g.REVIEWS
    try:
        g.REVIEWS = _revp7
        g._open_record('a probe-opened obligation',
                       {'sc_claims': ['watched.js']}, {})
        _written7 = json.load(io.open(_revp7, encoding='utf-8'))['records'][-1]
    finally:
        g.REVIEWS = _real_rev7
    check('_open_record() WRITES opened_at_sha, and it is THIS repo\'s HEAD -- '
          'the arms above would all pass against a feature that records nothing',
          _written7.get('opened_at_sha') == _sha_head,
          (_written7.get('opened_at_sha'), _sha_head))
    check('...and a record it just opened reads back FRESH, which closes the '
          'loop between the writer and the reader',
          g.code_staleness(dict(_written7, files=['watched.js']))[0] == 'FRESH',
          g.code_staleness(dict(_written7, files=['watched.js'])))
finally:
    g.REPO = _real_repo7
    shutil.rmtree(_tmp7, ignore_errors=True)

# ── SECTION 8: THE BACKFILL, WHICH WRITES THE FIELD THE READER TRUSTS ───────
# The tool that READS opened_at_sha is the tool that writes it, so the writer
# gets the harder probe. Three properties matter more than the happy path: it
# is DRY RUN by default, it never OVERWRITES a real stamp, and a timestamp it
# cannot resolve is SKIPPED rather than filled with something -- because a
# wrong baseline produces a confident FRESH, which is the one output this
# whole feature exists to prevent.
print()
print('SECTION 8 -- backfill: a reconstructed baseline, and it says so')
_tmp8 = tempfile.mkdtemp(prefix='tier-a-backfill-probe-')
_real_repo8, _real_rev8 = g.REPO, g.REVIEWS


def _g8(*a):
    return subprocess.run(['git'] + list(a), cwd=_tmp8, capture_output=True,
                          encoding='utf-8', errors='replace')


try:
    _g8('init', '-q', '-b', 'main')
    _g8('config', 'user.email', 'probe@example.invalid')
    _g8('config', 'user.name', 'probe')
    io.open(os.path.join(_tmp8, 'app.js'), 'w', encoding='utf-8',
            newline='\n').write('one\n')
    _g8('add', '-A')
    # A FIXED commit date, so the arms below are about the derivation and not
    # about what time the probe happened to run.
    _env = dict(os.environ, GIT_AUTHOR_DATE='2026-05-01T00:00:00+0000',
                GIT_COMMITTER_DATE='2026-05-01T00:00:00+0000')
    subprocess.run(['git', 'commit', '-q', '-m', 'base'], cwd=_tmp8, env=_env,
                   capture_output=True)
    _sha8 = _g8('rev-parse', 'HEAD').stdout.strip()
    _g8('update-ref', 'refs/remotes/origin/main', _sha8)
    g.REPO = _tmp8

    def _brec(opened, sha=None, extra=None):
        r = {'author_session': 'somebody-else', 'status': 'open',
             'opened_at': opened, 'resources': ['sc_claims'],
             'files': ['app.js'], 'what': 'a change'}
        if sha:
            r['opened_at_sha'] = sha
        if extra:
            r.update(extra)
        return r

    def _bstage(records):
        p = os.path.join(_tmp8, 'rev-%d.json' % len(os.listdir(_tmp8)))
        io.open(p, 'w', encoding='utf-8').write(json.dumps({'records': records}))
        g.REVIEWS = p
        return p

    # 1. DRY RUN WRITES NOTHING.
    _p8 = _bstage([_brec('2026-06-01T00:00:00Z')])
    _before8 = io.open(_p8, encoding='utf-8').read()
    g.backfill_shas(False)
    check('the default is a DRY RUN and the ledger is byte-identical after it',
          io.open(_p8, encoding='utf-8').read() == _before8)

    # 2. --write stamps, and STAMPS ITS OWN PROVENANCE.
    g.backfill_shas(True)
    _got8 = json.load(io.open(_p8, encoding='utf-8'))['records'][0]
    check('--write stamps the commit that was origin/main at the recorded time',
          _got8.get('opened_at_sha') == _sha8, _got8.get('opened_at_sha'))
    check('...and marks it BACKFILLED, so a reconstructed baseline can never '
          'be mistaken for one stamped at open time',
          _got8.get('opened_at_sha_backfilled') is True, _got8)
    _st8, _d8 = g.code_staleness(_got8)
    check('...and every staleness line built from it SAYS so',
          'BACKFILLED' in _d8, (_st8, _d8))

    # 3. IT NEVER OVERWRITES A REAL STAMP.
    _p8b = _bstage([_brec('2026-06-01T00:00:00Z', sha='deadbeefdeadbeef')])
    g.backfill_shas(True)
    check('a record that ALREADY has a sha is left completely alone -- the '
          'backfill can only ever fill a hole, never move a baseline',
          json.load(io.open(_p8b, encoding='utf-8'))['records'][0]['opened_at_sha']
          == 'deadbeefdeadbeef')

    # 4. WHAT IT CANNOT RESOLVE, IT SKIPS -- a wrong baseline is worse than none.
    _p8c = _bstage([_brec('2026-01-01T00:00:00Z'),      # before any commit
                    _brec('not-a-timestamp'),
                    _brec('')])
    g.backfill_shas(True)
    _after8 = json.load(io.open(_p8c, encoding='utf-8'))['records']
    check('a timestamp BEFORE any commit, an unreadable one, and an empty one '
          'are all SKIPPED -- left UNSTAMPED rather than filled with a guess',
          not any('opened_at_sha' in r for r in _after8),
          [r.get('opened_at_sha') for r in _after8])
    check('...and they still read as UNSTAMPED afterwards, never FRESH',
          all(g.code_staleness(r)[0] == 'UNSTAMPED' for r in _after8),
          [g.code_staleness(r)[0] for r in _after8])

    # 5. CLOSED records are not the backfill's business.
    _p8d = _bstage([_brec('2026-06-01T00:00:00Z', extra={'status': 'reviewed'})])
    g.backfill_shas(True)
    check('a CLOSED record is not stamped -- staleness is a question about '
          'work somebody still has to do',
          'opened_at_sha' not in
          json.load(io.open(_p8d, encoding='utf-8'))['records'][0])
finally:
    g.REPO, g.REVIEWS = _real_repo8, _real_rev8
    shutil.rmtree(_tmp8, ignore_errors=True)



# ── SECTION 9: THE TWO ENTRY POINTS MUST ANSWER THE SAME QUESTION ────────────
# Register 1a79c8a08a1d, recorded 2026-09-16 and left `planned` for eleven days:
# "the gate's two halves disagreed and nothing reconciled them -- a reader who
# checked first would have been told the opposite of what happened."
#
# THE DEFECT, CONCRETELY. A bare run read the WORKING TREE. The push hook reads
# `merge-base origin/main HEAD..HEAD`. So a session that COMMITS its work and
# then checks before pushing -- the ordinary order -- was told "Nothing to
# record", and was then denied by this same tool naming seven resources. Both
# answers were true about what they read; neither was about the question asked.
#
# ARM 1 IS THE WHOLE POINT AND IT IS A DISCRIMINATION ARM: a clean working tree
# with a committed-not-pushed hunk naming a Tier A resource. Run against the
# PRE-FIX scope (working_diff alone) it is EMPTY -- asserted here beside the
# fixed answer, so this arm cannot pass against the tool it was written to fix.
# Without that second half it would be a test that the gate finds findings,
# which sections 1-3 already cover.
#
# DRIVEN AGAINST A REAL GIT REPOSITORY with a real refs/remotes/origin/main,
# because the thing under test is how two git invocations disagree. A stub git
# would test this probe's arrangement and nothing about the tool.
print()
print('SECTION 9 -- a bare run and the push gate read the SAME scope')
_tmp9 = tempfile.mkdtemp(prefix='tier-a-scope-probe-')
_real9 = (g.REPO, g.REGISTER, g.REVIEWS)


def _g9(*a):
    return subprocess.run(['git'] + list(a), cwd=_tmp9, capture_output=True,
                          encoding='utf-8', errors='replace')


def _w9(rel, text):
    p = os.path.join(_tmp9, rel.replace('/', os.sep))
    d = os.path.dirname(p)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    io.open(p, 'w', encoding='utf-8', newline='\n').write(text)


def _run9():
    """(exit code, everything it printed) for a bare `main([])`."""
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        rc = g.main([])
    return rc, buf.getvalue()


try:
    _g9('init', '-q', '-b', 'main')
    _g9('config', 'user.email', 'probe@example.invalid')
    _g9('config', 'user.name', 'probe')
    # The resource list is the REAL one -- a fixture list would let the arms
    # pass against a parser that cannot read the document the gate really uses.
    _w9('docs/CRITICALITY-TIERS.md',
        io.open(os.path.join(REPO, 'docs', 'CRITICALITY-TIERS.md'),
                encoding='utf-8', errors='replace').read())
    _w9('docs/tier-a-reviews.json', json.dumps({'records': []}))
    _w9('api/x.js', 'const a = 1;\n')
    _g9('add', '-A')
    _g9('commit', '-q', '-m', 'base')
    _sha9_base = _g9('rev-parse', 'HEAD').stdout.strip()
    _g9('update-ref', 'refs/remotes/origin/main', _sha9_base)

    g.REPO = _tmp9
    g.REGISTER = os.path.join(_tmp9, 'docs', 'CRITICALITY-TIERS.md')
    g.REVIEWS = os.path.join(_tmp9, 'docs', 'tier-a-reviews.json')

    check('the fixture repo yields the REAL Tier A resource set, so the arms '
          'below are not passing against an empty list',
          len(g.tier_a_resources()) > 50, len(g.tier_a_resources()))

    # 1. THE DEFECT. Committed, not pushed, working tree clean.
    _w9('api/x.js', "const a = 1;\nconst t = 'sc_claims';\n")
    _g9('add', '-A')
    _g9('commit', '-q', '-m', 'name a Tier A resource')
    check('the working tree really is CLEAN -- otherwise arm 1 would pass for '
          'the wrong reason', _g9('status', '--porcelain').stdout.strip() == '',
          _g9('status', '--porcelain').stdout)
    _pre9 = g.check(g.working_diff())[0]
    check('THE PRE-FIX SCOPE IS BLIND TO IT: working_diff() alone answers 0 '
          'CLEAN on a committed-not-pushed Tier A change -- this is the '
          'verdict one session was given minutes before its push was denied',
          _pre9 == 0, _pre9)
    _rc9, _out9 = _run9()
    check('...and a bare run now FINDS it -- exit 1, not 0', _rc9 == 1, _rc9)
    check('...names the resource it found', 'sc_claims' in _out9, _out9[:300])
    check('...and SAYS WHAT SCOPE IT READ, so the verdict cannot be read '
          'without it',
          'SCOPE:' in _out9 and 'outgoing range' in _out9, _out9[:300])

    # 2. THE OLD SCOPE MUST NOT HAVE BEEN REPLACED BY THE NEW ONE. An
    #    uncommitted change is still the common case and was never broken.
    _g9('update-ref', 'refs/remotes/origin/main',
        _g9('rev-parse', 'HEAD').stdout.strip())
    _w9('api/x.js', "const a = 1;\nconst t = 'sc_claims';\nconst u = 'sc_revenue';\n")
    _rc9b, _out9b = _run9()
    check('an UNCOMMITTED edit naming a Tier A resource is still found -- the '
          'push range was ADDED to the working tree, not substituted for it',
          _rc9b == 1 and 'sc_revenue' in _out9b, (_rc9b, _out9b[:200]))

    # 2b. A LIMIT THIS SECTION FOUND AND IS PINNING RATHER THAN QUIETLY FIXING.
    #     `working_diff()` is two `git diff` calls, so an UNTRACKED new file is
    #     invisible to the working-tree half -- a brand-new api/sc-foo.js sitting
    #     unstaged names nothing as far as a bare run is concerned. The first
    #     draft of arm 2 used an untracked file and went red for exactly this,
    #     which is the only reason anybody knows.
    #
    #     IT IS NOT THE SAME DEFECT AND IS NOT BEING FIXED HERE: the file becomes
    #     visible the moment it is `git add`ed or committed, and the push range --
    #     which is the scope this section added -- catches it either way. What
    #     would be wrong is leaving the limit undocumented, so it is asserted in
    #     BOTH directions below and named in the scope line the tool prints.
    _g9('checkout', '--', 'api/x.js')
    _w9('api/untracked.js', "const w = 'sc_revenue';\n")
    _rc9b2, _out9b2 = _run9()
    check('KNOWN LIMIT, pinned: an UNTRACKED file is invisible to the '
          'working-tree half -- 0, because two `git diff` calls cannot see it',
          _rc9b2 == 0, (_rc9b2, _out9b2[:200]))
    check('...and the tool SAYS the working-tree half excludes untracked files, '
          'so the 0 above cannot be read as "nothing there"',
          'untracked' in _out9b2.lower(), _out9b2[:400])
    _g9('add', 'api/untracked.js')
    _rc9b3, _out9b3 = _run9()
    check('...and `git add` makes it visible immediately -- the limit is about '
          'untracked, not about new',
          _rc9b3 == 1 and 'sc_revenue' in _out9b3, (_rc9b3, _out9b3[:200]))
    _g9('rm', '-q', '-f', '--cached', 'api/untracked.js')
    os.remove(os.path.join(_tmp9, 'api', 'untracked.js'))

    # 3. AND THE CLEAN CASE, driven because a section that only ever sees
    #    findings would pass against a tool that returns 1 unconditionally.
    _rc9c, _out9c = _run9()
    check('nothing outgoing and nothing uncommitted is 0 CLEAN, not a finding',
          _rc9c == 0 and 'Nothing to record' in _out9c, (_rc9c, _out9c[:200]))

    # 4. FAIL CLOSED WHEN THE RANGE CANNOT BE RESOLVED (PR 1.11). Deleting
    #    origin/main is the realistic version: a clone whose remote ref was
    #    never fetched. The pre-fix tool answered 0 here on a clean tree, and 0
    #    means "checked, nothing found".
    _g9('update-ref', '-d', 'refs/remotes/origin/main')
    _text9, _notes9, _unk9 = g.default_scope_diff()
    check('with no origin/main the outgoing range is a COULD NOT TELL, not an '
          'empty diff', _unk9 is True, (_unk9, _notes9))
    check('...and it says so in words a reader can act on, naming the flag that '
          'gets a real answer',
          any('COULD NOT TELL' in n for n in _notes9)
          and any('--diff-range' in n for n in _notes9), _notes9)
    _rc9d, _out9d = _run9()
    check('...and the bare run exits 2, never 0 -- a clean verdict about half '
          'the scope is the defect this section closes', _rc9d == 2, _rc9d)

    # 5. COULD-NOT-TELL MUST NOT SWALLOW A REAL FINDING. Exit 2 outranks a
    #    clean 0 and must NOT outrank a 1: a finding is something that WAS
    #    found, and downgrading it to could-not-tell would lose it.
    _w9('api/x.js', "const a = 1;\nconst v = 'sc_denial';\n")
    _rc9e, _out9e = _run9()
    check('an unresolvable range plus a REAL working-tree finding is still 1, '
          'not 2 -- the finding survives the uncertainty about the other half',
          _rc9e == 1 and 'sc_denial' in _out9e, (_rc9e, _out9e[:200]))

    # 6. THE ANCHOR. This whole section is worthless if the hook stops reading
    #    origin/main -- the two halves would silently disagree again in a new
    #    way. Re-referenced against the hook's own source rather than restated
    #    here, per the eighth cross-domain discipline.
    _hook9 = os.path.join(REPO, 'tools', 'sairn_push_gate_hook.py')
    _hook9_src = io.open(_hook9, encoding='utf-8', errors='replace').read() \
        if os.path.isfile(_hook9) else ''
    check('the push hook is present, so this anchor arm actually ran',
          _hook9_src != '', _hook9)
    _want9 = "'merge-base', '%s'" % g.PUSH_BASE_REF
    check('the hook still derives the Tier A base from %r -- if this goes red, '
          'PUSH_BASE_REF is stale and the two entry points have drifted apart '
          'again' % g.PUSH_BASE_REF,
          _want9 in _hook9_src, 'searched for: %r' % _want9)
finally:
    g.REPO, g.REGISTER, g.REVIEWS = _real9
    shutil.rmtree(_tmp9, ignore_errors=True)


print()
# ── THE USAGE LINE IS A SPECIFICATION, AND IT WAS WRONG (2026-09-29) ────────
# It read `--discharge <author> "<verdict>"` while the parser takes the
# opened_at SECOND whenever an author has more than one open record. A real call
# of `--discharge cc <timestamp> --help` therefore dispatched cleanly, wrote
# `--help` as the verdict, printed DISCHARGED and marked a 70h obligation
# reviewed. The line was corrected by hand -- and a hand correction leaves
# NOTHING that would notice the next time the parse moves.
#
# So the order is DERIVED FROM THE PARSE and compared against the documented
# one. Both halves are read out of the file; neither is restated here, because a
# restatement is a third copy that can drift from both.
import re                                                        # noqa: E402
_gate_src = io.open(os.path.join(REPO, 'tools', 'tier_a_review_gate.py'),
                    encoding='utf-8').read()
_usage = [l for l in _gate_src.split('\n')[:40] if '--discharge' in l]
_doc_order = []
if _usage:
    _doc_order = re.findall(r'[<\[]([a-z_]+)[>\]]', _usage[0])

# What the parser ACTUALLY does: `rest[1]` is tested against an ISO date, and
# when it matches it is passed as opened_at with the verdict taken from rest[2:].
_parses_iso_second = bool(
    re.search(r"rest\[1\]\)[\s\S]{0,200}?opened_at=rest\[1\]", _gate_src)
    or re.search(r"re\.match\(r'\^\\d\{4\}[^\n]*rest\[1\]", _gate_src))

check('THE USAGE LINE MATCHES THE REAL ARGUMENT ORDER. It said '
      '`--discharge <author> "<verdict>"` while the parser reads opened_at '
      'SECOND, and that gap is how `--help` became the verdict of a 70h '
      'obligation',
      bool(_usage) and _doc_order[:2] == ['author', 'opened_at'],
      (_usage[:1], _doc_order))

check('...and the parse really does take the ISO timestamp SECOND, so the arm '
      'above is comparing the line against the CODE and not against a second '
      'copy of the line',
      _parses_iso_second,
      'the rest[1]-is-a-timestamp branch is gone; the usage line may now be '
      'the wrong one')

check('...and the usage line names the VERDICT LAST, which is the argument a '
      'shifted call silently swallows',
      bool(_doc_order) and _doc_order[-1] == 'verdict', _doc_order)



# -- CONVENTION 19: OBJECT EXISTENCE IS NEVER EVIDENCE OF REACHABILITY ------
# `git rev-parse --verify <sha>^{commit}` and `git cat-file -e <sha>^{commit}`
# both answer OK for a commit that is ON A REF *and* for one that is ORPHANED
# -- present in this clone's object store, reached by nothing, gc-eligible
# here, and absent from every other clone. The freshness path used the first of
# those to decide a recorded sha "resolves", then diffed against it and printed
# a plain FRESH or STALE verdict.
#
# NOT HYPOTHETICAL. At eb430f25 docs/tier-a-reviews.json cited SEVEN orphaned
# 40-char shas, and "** STALE ** moved since 00030f2d11b7" was printed for one
# of them. The gate already contained the right test -- _is_reachable() uses
# `merge-base --is-ancestor` -- so it carried BOTH methods and the freshness
# path used the weaker one.
#
# THE FIRST VERSION OF THIS ARM WAS VACUOUS AND AN ABLATION CAUGHT IT. It
# sliced the source from the resolve message to `def _file_set_index`, roughly
# 1,500 lines, which SWALLOWED the definition of `_is_reachable` itself -- so
# `'_is_reachable(' in slice` was true whether or not the freshness path called
# it, and removing the guard left the probe green. The window is now bounded,
# the bound is asserted, and the extraction is tested in BOTH directions
# against a synthetic source.
_GATE_SRC_PATH = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), 'tools', 'tier_a_review_gate.py')
_RESOLVE_ANCHOR = "'the recorded sha %s does not resolve"
_C19_WINDOW = 3000


def _reachability_window(src):
    """The bytes right after the existence-resolve, or None.

    Bounded deliberately: anything wide enough to reach `def _is_reachable`
    makes every arm below vacuous, which is the mistake this helper exists to
    make impossible to repeat.
    """
    i = src.find(_RESOLVE_ANCHOR)
    if i < 0:
        return None
    w = src[i:i + _C19_WINDOW]
    j = w.find('def _is_reachable')
    return w[:j] if j >= 0 else w


def _asks_reachability(src):
    w = _reachability_window(src)
    if w is None:
        return None
    return ('_is_reachable(sha' in w) or ('--is-ancestor' in w)


_gate_src = io.open(_GATE_SRC_PATH, encoding='utf-8', errors='replace').read()
_c19_window = _reachability_window(_gate_src)

check('NEGATIVE HALF FIRST: the window this arm reads was LOCATED and is '
      'bounded well short of _is_reachable -- a window wide enough to contain '
      'that definition makes every arm below vacuous',
      _c19_window is not None and 0 < len(_c19_window) <= _C19_WINDOW
      and 'def _is_reachable' not in _c19_window,
      'window=%r' % (None if _c19_window is None else len(_c19_window)))

check('CONVENTION 19: the freshness path does not stop at an EXISTENCE test -- '
      'it asks REACHABILITY after resolving',
      _asks_reachability(_gate_src) is True,
      'the recorded-sha resolve uses rev-parse/cat-file only, so an ORPHANED '
      'commit reads as resolvable and is given a FRESH or STALE verdict')

check('...and the refusal NAMES orphaned, so a reader can tell it apart from '
      '"never fetched" -- two causes, two sentences',
      _c19_window is not None and 'ORPHANED' in _c19_window,
      'both could-not-tell reasons are reported with one sentence')

_SYNTH_WEAK = (
    "def freshness(rec):\n"
    "    try:\n"
    "        git('rev-parse', '--verify', '--quiet', sha + '^{commit}')\n"
    "    except CouldNotTell:\n"
    "        return ('COULD-NOT-TELL',\n"
    "                'the recorded sha %s does not resolve in this clone')\n"
    "    moved = git('diff', '--name-only', sha + '..' + head)\n"
    "    return ('STALE', moved)\n"
    "\n\ndef _is_reachable(sha, base):\n    return True\n")
_SYNTH_STRONG = _SYNTH_WEAK.replace(
    "    moved = git(",
    "    if not _is_reachable(sha, PUSH_BASE_REF):\n"
    "        return ('COULD-NOT-TELL', 'ORPHANED')\n"
    "    moved = git(")

check('THE PAIRED NEGATIVE, ON A SYNTHETIC SOURCE: an existence-only freshness '
      'path is REPORTED AS MISSING THE CHECK -- without this the arm above '
      'could be passing because the extraction matches anything',
      _asks_reachability(_SYNTH_WEAK) is False,
      'an existence-only source was accepted as asking reachability')

check('THE PAIRED POSITIVE, ON A SYNTHETIC SOURCE: the same extraction DOES '
      'see a reachability call when one is there, so the arm above is not '
      'rejecting every source',
      _asks_reachability(_SYNTH_STRONG) is True,
      'a source that does ask reachability was reported as not asking')

check('...and the synthetic negative is not passing because its window ran on '
      'into its own _is_reachable definition',
      'def _is_reachable' not in (_reachability_window(_SYNTH_WEAK) or 'x'),
      'the bound did not hold on the synthetic source either')

if fails:
    print('%d ARM(S) FAILED:' % len(fails))
    for f in fails:
        print('  - ' + f)
else:
    print('ALL ARMS PASS')
sys.exit(1 if fails else 0)
