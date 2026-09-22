"""The file set is the primary check, and the lexical matcher is a warning.

    python tests/claims/run_fileset_matcher_probe.py

Exit 0 when every arm passes, 1 otherwise.

── WHAT THIS GUARDS, AND WHY IT IS NOT A LOOSENING ────────────────────────────
Every rule in `block_reason()` answers "do these two strings talk about the same
thing". That is a PROXY. The thing it stands in for is "would these two sessions
edit the same file", and since 2026-09-21 claims carry `FILES: <paths>` in the
task text, which makes the real question answerable.

MEASURED over every cross-session pair among the claims that declare files --
318 pairs, run through the tool's own block_reason():

    153 pairs BLOCK today
     43 of those have INTERSECTING file sets   <- real, must still block
    110 of those have DISJOINT file sets       <- 72%, false, now cleared

The 110 include `shared phrase: "html tests"` between a SAIRNlegacy hydration
claim and a SAIRNlaw trust-clearance claim, and `same app: sairnlegacy` between
a hydration claim and one whose declared files are three api/ test files in
other apps entirely -- the claim that blocked two sessions three times each in
one night.

── THE THIRD STATE IS THE PART THAT KEEPS IT SAFE ─────────────────────────────
  both declare files, INTERSECT   -> refuse   (stronger than any word rule)
  both declare files, DISJOINT    -> no block (the lexical hit is printed)
  either declares nothing         -> UNKNOWN, and the lexical matcher decides
                                     byte-for-byte as before

774 of the 805 recorded claims declare no files. Every one keeps the behaviour
it has today, and the arms below drive that rather than asserting it.

── IT IS NOT STRICTER ANYWHERE, AND SAYING SO IS THE POINT ────────────────────
The first draft of this file asserted that a shared declared path now blocks
where no lexical rule fires. MEASURED over all 318 cross-session pairs: the
file set refuses ZERO pairs the lexical matcher does not already refuse. It
cannot, in practice -- `idents()` already blocks on a shared filename token and
`bigrams()` catches the path's words even across a backslash/forward-slash
difference. So this change adds no blocking power. It removes 110 false blocks
and it names the real evidence when it keeps one.

That matters for what comes next rather than for today: if anybody narrows the
lexical matcher later, the file set becomes the only thing holding those 43
real blocks, and the arm at the end of section 4 is what will say so. This
file's sibling probe is right that a gate made quieter without a test is on its
way to protecting nothing -- the answer is the corpus measurement, not a
strictness claim that does not survive being checked.
"""
import importlib.util
import io
import itertools
import json
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
spec = importlib.util.spec_from_file_location(
    'sairn_claim', os.path.join(REPO, 'tools', 'sairn_claim.py'))
SC = importlib.util.module_from_spec(spec)
spec.loader.exec_module(SC)

fails = 0


def arm(name, cond, detail=''):
    global fails
    print(('ok    ' if cond else 'FAIL  ') + name)
    if not cond:
        fails += 1
        if detail:
            print('        ' + detail)


# ─────────────────────────────────────────────────────────────────────────
print('\n1. declared_files() -- and None is NOT the empty set')

arm('a FILES list is parsed into its paths',
    SC.declared_files('FILES: api/sd-data.js tools/x.py -- and a note')
    == {'api/sd-data.js', 'tools/x.py'},
    repr(SC.declared_files('FILES: api/sd-data.js tools/x.py -- and a note')))

arm('a task with NO FILES declaration returns None, not an empty set',
    SC.declared_files('review the grader, read only') is None,
    'an empty set would mean "declared, touches nothing" and would send this '
    'to CLEAR; None means "no evidence" and must fall back to the lexical rule')

arm('...and None is distinguishable from a declaration in the code path',
    SC.declared_files('FILES: a.py') is not None
    and SC.declared_files('no files here') is None)

arm('backslashes are normalised, so one clone cannot miss another clone\'s path',
    SC.declared_files(r'FILES: docs\tier-a-reviews.json')
    == {'docs/tier-a-reviews.json'})

arm('the declaration stops at the " -- " separator and does not eat the prose',
    SC.declared_files('FILES: a.py -- rewrite b.py entirely') == {'a.py'},
    'got ' + repr(SC.declared_files('FILES: a.py -- rewrite b.py entirely'))
    + ' -- prose after the separator is commentary, and treating a file named '
    'there as declared would re-block work the claim does not hold')

arm('a FILES: label with no parseable path is None, not an empty set',
    SC.declared_files('FILES: the three sairnsenior suites') is None,
    'a prose "files" list gives no paths to intersect, so it is no evidence '
    'at all -- and this exact shape is live in the record today')

# ─────────────────────────────────────────────────────────────────────────
print('\n2. file_verdict() -- three states, and the third is not a pass')

arm('disjoint declared sets are CLEAR',
    SC.file_verdict('FILES: a.py', 'FILES: b.py')[0] == 'clear')

arm('intersecting declared sets are REFUSE, and name the shared path',
    SC.file_verdict('FILES: a.py c.py', 'FILES: b.py c.py')
    == ('refuse', {'c.py'}))

arm('either side declaring nothing is UNKNOWN, never CLEAR',
    SC.file_verdict('FILES: a.py', 'no declaration here')[0] == 'unknown'
    and SC.file_verdict('no declaration', 'FILES: a.py')[0] == 'unknown'
    and SC.file_verdict('neither', 'declares')[0] == 'unknown',
    'an unknown folded into clear is this platform\'s most-recorded defect '
    'shape, and it would silently disable the matcher for every claim that '
    'does not use the convention')

# ─────────────────────────────────────────────────────────────────────────
print('\n3. the INTEGRATION -- driven through cmd_check, not asserted')
# block_reason() is unchanged by this work, so a probe that only drove it
# would test nothing about the change. The decision moved to the call site.


class Args(object):
    def __init__(self, subject, task):
        self.subject = subject
        self.task = task.split()
        self.no_fetch = True


def check_against(their_subject, their_task, my_subject, my_task):
    """Run the REAL cmd_check with exactly one other session's claim present.

    Returns (exit_code, printed_output). Nothing on disk is touched: load_all
    and session_name are replaced for the duration, so this cannot disturb an
    uncommitted claim the way driving the CLI would.
    """
    saved_load, saved_me = SC.load_all, SC.session_name
    # load_all() yields claims directly -- it does NOT return (rows, note).
    # The first spelling here assumed a tuple and cmd_check crashed on
    # `'list' object has no attribute 'get'`, which is the right way for a
    # wrong fixture to fail: loudly, at the first use, rather than by driving
    # something that merely resembles the real loader.
    SC.load_all = lambda from_origin=False: [{
        'session': 'other', 'subject': their_subject, 'task': their_task,
        'status': 'active', 'claimed_at': '2026-09-22T00:00:00Z',
        'claimed_at_epoch': SC.time.time() - 60, 'released_at': None,
    }]
    SC.session_name = lambda: 'me'
    out, real = io.StringIO(), sys.stdout
    sys.stdout = out
    try:
        code = SC.cmd_check(Args(my_subject, my_task))
    finally:
        sys.stdout = real
        SC.load_all, SC.session_name = saved_load, saved_me
    return code, out.getvalue()


# THE TWO CASES THE CHANGE WAS ASKED FOR, taken VERBATIM in shape from the
# corpus rather than invented. The first draft used two strings I expected to
# collide; block_reason() returned None for them, so the arm below would have
# passed without the change being exercised at all. These two are a real pair
# from the record -- a SAIRNlegacy hydration claim and a SAIRNlaw trust
# clearance claim -- whose only commonality is the bigram "html tests".
BOILERPLATE_A = ('FILES: sairnlegacy.html sairndesign.html '
                 'tests/server_wins_hydration.js -- server wins hydration in two apps')
BOILERPLATE_B = ('FILES: sairnlaw.html tests/sairnlaw_trust_clearance.js -- '
                 'iolta clearance, html tests for the trust ledger')
arm('CONTROL: those two really DO collide lexically, so the next arm is real',
    SC.block_reason('a', BOILERPLATE_A, 'b', BOILERPLATE_B) is not None,
    'no lexical rule fires, so a passing arm below would prove nothing')
code, out = check_against('sairnlaw-iolta-clearance', BOILERPLATE_B,
                          'sairnlegacy-sairndesign-hydration', BOILERPLATE_A)
# NOT `code == 0`. cmd_check returns 4 for "--no-fetch, so every verdict above
# is as of the last fetch" -- a statement about FRESHNESS, not a block. The
# first spelling of this arm conflated the two and reported a working change as
# broken, which is the same class as reading a non-zero exit as a failure
# without asking what the code means.
arm('two claims sharing boilerplate words but ZERO shared files do NOT block',
    'BLOCKED' not in out and 'CLEAR' in out,
    'exit %s\n%s' % (code, out[:500]))
arm('...and the lexical hit is still REPORTED, not hidden',
    'LEXICAL ONLY' in out,
    'the warning was dropped entirely -- a matcher that goes quiet without '
    'saying so is the failure this replaces, not an improvement on it\n' + out[:400])

SHARED_A = 'FILES: api/sd-data.js tests/a.js -- wire the session gate'
SHARED_B = 'FILES: api/sd-data.js sql/b.sql -- land three staged fixes'
code, out = check_against('hover-three-fixes', SHARED_B, 'gate-work', SHARED_A)
arm('two claims with a GENUINELY shared file still BLOCK',
    code != 0 and 'BLOCKED' in out, 'exit %s\n%s' % (code, out[:400]))
arm('...and the block names the shared PATH as its evidence',
    'same declared FILES: api/sd-data.js' in out,
    'the reason did not name the file, so a reader cannot tell a real '
    'collision from a word match\n' + out[:400])

# ── THE ARM THAT WAS VOID, KEPT AS THE CORRECTION IT TURNED INTO ─────────
# This began as "a shared declared file BLOCKS even when no lexical rule
# fires", with a control asserting no lexical rule fired. THE CONTROL FAILED:
# block_reason() answered `same file or resource: tools/zzz_unique_alpha.py`,
# because idents() already blocks on a shared filename token. The strictness
# the arm was written to prove does not exist, and the arm would have passed
# anyway -- on the lexical block, not on the file set.
#
# So it is replaced by what is TRUE and measurable: a path spelled with
# different separators in the two claims is recognised as ONE file, and the
# refusal NAMES that path instead of whatever bigram happened to match. That is
# precision, not strictness, and precision is what a reader acts on.
SLASHED_A = r'FILES: docs\tier-a-reviews.json -- discharge the alpha obligation'
SLASHED_B = 'FILES: docs/tier-a-reviews.json -- discharge the zeta obligation'
arm('the same path spelled with different separators is ONE file',
    SC.file_verdict(SLASHED_A, SLASHED_B) == ('refuse', {'docs/tier-a-reviews.json'}),
    repr(SC.file_verdict(SLASHED_A, SLASHED_B)))
code, out = check_against('zeta', SLASHED_B, 'alpha', SLASHED_A)
arm('...and the block names THAT PATH rather than the bigram that matched',
    'same declared FILES: docs/tier-a-reviews.json' in out,
    'block_reason alone answers ' + repr(
        SC.block_reason('a', SLASHED_A, 'b', SLASHED_B))
    + ', which is true and tells a reader nothing about which file collided\n'
    + out[:400])

# THE THIRD STATE, driven end to end.
NOFILES = 'review the leg_invoices obligation, read only'
WITHFILES = 'FILES: docs/tier-a-reviews.json -- discharge the leg_invoices obligation'
arm('CONTROL: those two DO collide lexically',
    SC.block_reason('a', NOFILES, 'b', WITHFILES) is not None)
code, out = check_against('their-review', NOFILES, 'my-review', WITHFILES)
arm('when ONE side declares no files, the lexical matcher still BLOCKS',
    code != 0 and 'BLOCKED' in out,
    'the fallback was lost, so every claim not using the FILES convention '
    'stopped being matched at all\n' + out[:400])

# ─────────────────────────────────────────────────────────────────────────
print('\n4. the REAL corpus -- the 43 genuine collisions must still refuse')
rows = []
for p in sorted(glob.glob(os.path.join(REPO, '.claude', 'claims', '*.json'))):
    with io.open(p, encoding='utf-8') as fh:
        rows.extend(json.load(fh).get('claims', []))
withf = [c for c in rows if SC.declared_files(c.get('task'))]
pairs = [(a, b) for a, b in itertools.combinations(withf, 2)
         if a.get('session') != b.get('session')]
lex = [(a, b) for a, b in pairs
       if SC.block_reason(a.get('subject', ''), a.get('task', ''),
                          b.get('subject', ''), b.get('task', ''))]
inter = [(a, b) for a, b in lex
         if SC.declared_files(a['task']) & SC.declared_files(b['task'])]
disj = [(a, b) for a, b in lex
        if not (SC.declared_files(a['task']) & SC.declared_files(b['task']))]
print('    claims declaring files      %4d' % len(withf))
print('    cross-session pairs         %4d' % len(pairs))
print('    lexical blocks              %4d' % len(lex))
print('      files INTERSECT           %4d   still refused' % len(inter))
print('      files DISJOINT            %4d   now cleared' % len(disj))
arm('every lexically-blocked pair with intersecting files still refuses',
    all(SC.file_verdict(a['task'], b['task'])[0] == 'refuse' for a, b in inter),
    'a real collision was cleared')
arm('every lexically-blocked pair with disjoint files clears',
    all(SC.file_verdict(a['task'], b['task'])[0] == 'clear' for a, b in disj))
arm('the corpus is not degenerate -- BOTH outcomes occur in real data',
    len(inter) > 0 and len(disj) > 0,
    'if one side is empty this measurement proves nothing about the split')

# ── THE HONEST BOUND ON WHAT THIS CHANGE DID ─────────────────────────────
# Zero today. If this ever becomes non-zero, the file set has started holding
# blocks the lexical matcher no longer makes -- which is fine, and is exactly
# the situation in which somebody must know that the two checks have stopped
# agreeing. It is pinned so the change is visible rather than discovered.
only_file = [(a, b) for a, b in pairs
             if SC.file_verdict(a['task'], b['task'])[0] == 'refuse'
             and not SC.block_reason(a.get('subject', ''), a.get('task', ''),
                                     b.get('subject', ''), b.get('task', ''))]
print('    refused by FILES alone      %4d   (no lexical rule fires)' % len(only_file))
arm('PINNED: the file set currently refuses NOTHING the lexical matcher misses',
    len(only_file) == 0,
    'this is now %d. That is not a failure -- it means the two checks have '
    'stopped agreeing and the file set is load-bearing on its own. Read the '
    'pairs, then update this arm deliberately.' % len(only_file))

print('\n%d failure(s)' % fails)
sys.exit(1 if fails else 0)
