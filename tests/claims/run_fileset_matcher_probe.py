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

# ── THIS ARM ENCODED THE PRE-NARROWING CONTRACT (re-pointed 2026-10-06) ─────
# It required `file_verdict('FILES: a.py c.py', 'FILES: b.py c.py')` to be
# ('refuse', {'c.py'}). file_verdict() was deliberately NARROWED on 2026-09-30
# (H2 seq 418): a bare BASENAME is not a file identity, because the two hover
# auditors each keep their own `hover_log.py` outside this repo and the matcher
# hard-blocked them against each other on the filename alone. A path WITH a
# separator still refuses; a bare basename now returns 'unknown' so the caller
# falls through to the lexical matcher, which can still block.
#
# SO THE CODE IS RIGHT AND THE ARM WAS STALE. It is re-pointed to the real
# three-state contract and split in BOTH directions, because an arm that only
# checked the refuse side would pass on a matcher that refused everything.
arm('an intersecting PATH (with a separator) is REFUSE, and names the path',
    SC.file_verdict('FILES: x/a.py x/c.py', 'FILES: y/b.py x/c.py')
    == ('refuse', {'x/c.py'}),
    'got ' + repr(SC.file_verdict('FILES: x/a.py x/c.py',
                                  'FILES: y/b.py x/c.py')))

arm('a shared BARE BASENAME is UNKNOWN, not refuse -- two clones can each own '
    'a different file of that name, and it is not folded into CLEAR either',
    SC.file_verdict('FILES: a.py c.py', 'FILES: b.py c.py')
    == ('unknown', {'c.py'}),
    'got ' + repr(SC.file_verdict('FILES: a.py c.py', 'FILES: b.py c.py'))
    + ' -- "clear" here would silently drop a real signal, and "refuse" is the '
    'hover_log.py false block seq 418 removed')

arm('CONTROL: the narrowing is about the SEPARATOR and nothing else -- the same '
    'two sets with one path qualified refuse again',
    SC.file_verdict('FILES: a.py sub/c.py', 'FILES: b.py sub/c.py')
    == ('refuse', {'sub/c.py'}))

arm('CONTROL: a mixed intersection returns ONLY the strong paths, so the '
    'evidence named is evidence that holds',
    SC.file_verdict('FILES: c.py sub/d.py', 'FILES: c.py sub/d.py')
    == ('refuse', {'sub/d.py'}),
    'got ' + repr(SC.file_verdict('FILES: c.py sub/d.py',
                                  'FILES: c.py sub/d.py')))

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
                 'iolta clearance, wins hydration for the trust ledger')
# PAIR CHANGED 2026-09-29, AND THE OLD ONE WAS RIGHT TO STOP WORKING. It relied
# on the bigram `html tests`, which sairn_claim now EXEMPTS: that phrase appears
# in the claims of four different sessions, so the corpus says it is common
# vocabulary and a lexical block on it was the over-block this whole file
# documents. The control was therefore asserting an over-block THAT HAS BEEN
# FIXED one layer up -- a fixture describing a closed gap, not a defect in the
# change. `wins hydration` is used by two sessions, under the three-session
# threshold, so it still collides and the arm below still means what it says.
# If the exemption ever widens to cover this pair too, THIS ARM IS WHERE THAT
# BECOMES VISIBLE rather than the next arm silently passing for free.
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
# ── SAME RE-POINT AS SECTION 2, ON THE REAL CORPUS (2026-10-06) ─────────────
# This arm required 'refuse' for every intersecting pair and went red on the
# seq 418 narrowing: an intersection on a BARE BASENAME is now 'unknown', which
# falls through to the lexical matcher rather than hard-blocking. These pairs are
# lexically blocked anyway -- that is how they got into `inter` -- so NOTHING IS
# CLEARED by the narrowing here, and that is the property worth asserting.
_bad = [(a, b) for a, b in inter
        if SC.file_verdict(a['task'], b['task'])[0] == 'clear']
arm('NO lexically-blocked pair with intersecting files is ever CLEARED by the '
    'file matcher -- refuse or unknown, never clear',
    not _bad, '%d pair(s) cleared a real collision' % len(_bad))
_weak = [(a, b) for a, b in inter
         if SC.file_verdict(a['task'], b['task'])[0] == 'unknown']
print('      of which BARE-BASENAME only %4d   unknown, still lexically blocked'
      % len(_weak))
arm('...and the ones demoted to unknown are STILL blocked by the lexical '
    'matcher, so the narrowing let nothing through',
    all(SC.block_reason(a.get('subject', ''), a.get('task', ''),
                        b.get('subject', ''), b.get('task', ''))
        for a, b in _weak),
    'a pair was demoted to unknown AND passes the lexical matcher -- that is a '
    'hole the seq 418 narrowing opened')
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
# ── THE PIN MOVED FROM 0 TO 23 ON 2026-09-29, DELIBERATELY ────────────────
# The arm above did exactly what it was built for. sairn_claim now exempts
# COMMON VOCABULARY -- a bigram or hyphenated token used by three or more
# sessions -- so a pair whose only lexical signal was `tests first` or
# `known-bad control` no longer blocks lexically. Twenty-three such pairs
# DECLARE AN INTERSECTING FILE, and for those the file set is now the only
# thing refusing. THAT IS THE FILE SET BECOMING LOAD-BEARING ON ITS OWN, which
# this arm's own comment calls fine and says somebody must know about.
#
# The number is pinned rather than the arm relaxed to `>= 0`: a floor would stop
# measuring, and the next movement in either direction is the thing worth
# seeing. If it FALLS, the exemption has widened past where files can catch it.
# ── THE EXACT PIN WAS MEASURING CORPUS GROWTH, NOT THE GAP (2026-10-06) ─────
# It went 0 -> 23 -> 24 and the arm's own failure message says "That is not a
# failure". THE PAIRS WERE READ, as that message instructs, and all 24 of them
# share ONE claim on one side -- cody's 2026-10-05 scpgate claim, which declares
# api/sd-data.js. Twenty-two of the 24 share exactly `api/sd-data.js`; the other
# two add or substitute docs/defect-density-register.json.
#
# SO THE NUMBER IS len(older claims that also declared api/sd-data.js) AND IT
# RISES EVERY TIME ANYBODY CLAIMS THAT FILE. An exact pin over a monotonically
# growing append-only record is guaranteed to go red for a reason that is not a
# finding, which is what happened twice. The arm's intent -- "if it FALLS, the
# exemption has widened past where files can catch it" -- is a FLOOR, and that is
# what it now is, with the count and the pairs printed so a RISE is still visible.
#
# AND THE PROPERTY WORTH PINNING EXACTLY IS A DIFFERENT ONE: every file-only
# refusal must rest on a separator-qualified path. A bare basename reaching this
# list would mean the seq 418 narrowing had been undone, and that IS a property
# of the matcher rather than of how many claims exist.
FILE_ONLY_FLOOR = 24
arm('FLOOR: the file set refuses at least %d pairs the lexical matcher misses '
    '-- a FALL means the lexical exemption widened past where files can catch it'
    % FILE_ONLY_FLOOR,
    len(only_file) >= FILE_ONLY_FLOOR,
    'this is now %d, BELOW the floor of %d. Read the pairs printed above: a '
    'fall is the direction that loses coverage.'
    % (len(only_file), FILE_ONLY_FLOOR))

_weak_only = [(a, b) for a, b in only_file
              if not all('/' in p for p in SC.file_verdict(a['task'],
                                                           b['task'])[1])]
arm('EXACT: every file-only refusal rests on a SEPARATOR-QUALIFIED path, so '
    'none of them is the bare-basename collision seq 418 removed',
    not _weak_only,
    '%d pair(s) refused on a bare basename alone -- the narrowing has been '
    'undone' % len(_weak_only))

_sessions = sorted(set(tuple(sorted((a.get('session'), b.get('session'))))
                       for a, b in only_file))
print('    file-only refusals involve %d distinct session pair(s): %s'
      % (len(_sessions), '; '.join('%s/%s' % s for s in _sessions)))
arm('the file-only refusals are not one session arguing with itself',
    all(s[0] != s[1] for s in _sessions),
    'a same-session pair reached a cross-session list')

print('\n%d failure(s)' % fails)
sys.exit(1 if fails else 0)
