"""Prove the claim matcher blocks what matters and stops blocking what it
never should have.

WHY THIS EXISTS. Every change to this matcher makes the tool QUIETER, and a
gate made quieter without a test is a gate on its way to protecting nothing.
sairn_claim.py's own comment states the asymmetry it must keep: over-flagging
costs a five-second read, under-flagging costs four hours. So the arms below
weight the false-negative side deliberately -- every historical TRUE block is
re-run and must still block.

REWRITTEN 2026-09-04 for the phrase-or-name rule, which replaced "one shared
specific token blocks, where specific means not on a hand-maintained list of
English words". That was a blocklist against the whole language and the
language won six times: audit, gap, platform, triage, false, and finally
`name` -- which blocked the very change that fixed it. All six are cases
below and all six must be NOTES.

Pure function-level assertions on block_reason(). No files written, no claims
committed, nothing touching .claude/claims -- which matters because `list` and
`check` read that directory, so a probe that exercised the CLI could disturb a
real uncommitted claim.
"""
import importlib.util
import os
import subprocess
import sys

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True, encoding='utf-8', errors='replace').stdout.strip()
spec = importlib.util.spec_from_file_location(
    'sairnclaim', os.path.join(REPO, 'tools', 'sairn_claim.py'))
claim = importlib.util.module_from_spec(spec)
spec.loader.exec_module(claim)


def shared(a_subj, a_task, b_subj, b_task):
    return claim.tokens(a_subj, a_task) & claim.tokens(b_subj, b_task)


def verdict(a_subj, a_task, b_subj, b_task):
    if not shared(a_subj, a_task, b_subj, b_task):
        return 'clear'
    return 'BLOCK' if claim.block_reason(a_subj, a_task, b_subj, b_task) else 'note'


# (label, mine, theirs, expected)
CASES = [
    # ── MUST STILL BLOCK. These are the reason the tool exists. ────────────
    ('same app, same subject',
     ('sairnroofing', 'shared subcontractor compliance layer'),
     ('sairnroofing', 'subcontractor compliance panel wiring'), 'BLOCK'),
    ('the real 2026-08-30 duplication: same app, same gate',
     ('sairnfreedom', 'competitive scan'),
     ('sairnfreedom', 'competitive and patent scan'), 'BLOCK'),
    ('same app, adjacent phases -- arguably fair, and still blocks',
     ('sairnfreedom', 'phase 2'),
     ('sairnfreedom', 'phase 3'), 'BLOCK'),
    ('a shared two-word phrase is worth a read',
     ('sairnvet', 'audit fix'),
     ('stonedesk', 'audit fix'), 'BLOCK'),
    # STRONGER THAN THE OLD RULE, not weaker. An app name inside a compound
    # subject now matches -- this exact pair was a real 2026-09-04 collision
    # the old matcher would have missed, because it compared whole tokens and
    # `sairnbuild-sairnvet` is not `sairnvet`.
    ('an app named inside a compound subject still collides',
     ('sairnbuild-sairnvet', 'fail open read sweep'),
     ('sairnvet', 'panel audit'), 'BLOCK'),
    ('a shared FILE is a collision however the tasks are worded',
     ('platform', 'harden api/sd-data.js payload cap'),
     ('disclosure', 'api/sd-data.js resource list before licence check'), 'BLOCK'),
    ('a shared RESOURCE name likewise',
     ('backup', 'push bld_bids from the client'),
     ('privacy', 'assignment gate on bld_bids reads'), 'BLOCK'),
    ('a subject wholly inside another blocks, when it is more than one word',
     ('ld loader sairnbiz', 'corrupt vs absent'),
     ('ld loader sairnbiz sairncare', 'corrupt vs absent'), 'BLOCK'),

    # ── MUST NOT BLOCK. Every one is a real false block from the record. ───
    ('2026-09-01: blocked on the word "audit" alone',
     ('sairnvet', 'employee auth deactivation audit'),
     ('stonedesk', 'safehtml audit'), 'note'),
    ('2026-09-02: blocked on the word "gap" alone (x2 that night)',
     ('sairnroofing', 'crew field labour scheduling depth gap A2'),
     ('sairnsenior', 'caregiver training hours in-service gap A6'), 'note'),
    ('2026-09-02, the second one',
     ('sairnroofing', 'crew field labour scheduling depth gap A2'),
     ('sairndental', 'payer enrolment credentialing lifecycle gap B1'), 'note'),
    ('2026-09-02: a bare NAMESPACE must not swallow a specific subject',
     ('platform-schema-constraints', 'capture CHECK constraints in the snapshot'),
     ('platform', 'ai rate limit atomicity and scan tooling'), 'note'),
    ('2026-09-04: blocked on the word "triage" alone',
     ('sairnbuild-sairnvet', 'fail open read sweep and silent failure triage'),
     ('stonedesk', 'missing dom target triage 162 references'), 'note'),
    ('2026-09-04: blocked on the word "false" alone',
     ('storage-write-wrappers', 'four remaining wrappers return false to nobody'),
     ('sairndental', 'false sync disabled message swallows real refusals'), 'note'),
    ('2026-09-04: blocked on the word "name" -- while fixing this very defect',
     ('claim-matcher', 'require a shared phrase or a real name not one english word'),
     ('sd-data-auth-ordering', 'resource name disclosure before license validation'), 'note'),
    # DELIBERATELY FLIPPED 2026-09-04. This was a MUST-BLOCK under the old
    # rule, on the single word "warranty". It is the same shape as every false
    # block above -- different app, different file, one shared noun -- and the
    # new standard is a phrase or a real name, never one word. Still printed.
    ('two apps sharing one feature NOUN is a note, not a block',
     ('sairnroofing', 'warranty registration'),
     ('sairnbuild', 'warranty tracking'), 'note'),
    ('genuinely unrelated work shares nothing',
     ('sairnroofing', 'crew scheduling'),
     ('sairnlaw', 'grounded definitions in drafting'), 'clear'),
]

fails = 0
for label, mine, theirs, expected in CASES:
    got = verdict(mine[0], mine[1], theirs[0], theirs[1])
    ok = got == expected
    fails += 0 if ok else 1
    print('%-5s %-8s (want %-5s)  %s' % ('ok' if ok else 'FAIL', got, expected, label))
    if not ok:
        print('        shared: %s' % sorted(shared(mine[0], mine[1], theirs[0], theirs[1])))
        print('        reason: %s' % claim.block_reason(mine[0], mine[1], theirs[0], theirs[1]))

# ── the reason must name the EVIDENCE, not a token ─────────────────────────
# "same app: sairnvet" tells a session what to check. "overlap on: name" is
# what six sessions had to argue with, and arguing with a gate is how it gets
# hollowed out.
print()
REASONS = [
    ('same subject', ('sairnroofing', 'a'), ('sairnroofing', 'b')),
    ('same app: sairnvet', ('sairnbuild-sairnvet', 'x'), ('sairnvet', 'y')),
    ('same file or resource: api/sd-data.js',
     ('platform', 'api/sd-data.js cap'), ('other', 'api/sd-data.js gate')),
    ('shared phrase: "audit fix"', ('sairnvet', 'audit fix'), ('stonedesk', 'audit fix')),
]
for want, mine, theirs in REASONS:
    got = claim.block_reason(mine[0], mine[1], theirs[0], theirs[1])
    ok = got == want
    fails += 0 if ok else 1
    print('%-5s reason is %-38s (want %s)' % ('ok' if ok else 'FAIL', repr(got), want))

# ── app names come from the repo, so they cannot drift from reality ────────
print()
apps = claim.app_names()
for must in ('stonedesk', 'sairnvet', 'sairnbuild', 'sairnbiz'):
    ok = must in apps
    fails += 0 if ok else 1
    print('%-5s %s is discovered from the repo, not hardcoded' % ('ok' if ok else 'FAIL', must))
# An English word must never be mistaken for an app.
for never in ('audit', 'gap', 'name', 'false', 'triage'):
    ok = never not in apps
    fails += 0 if ok else 1
    print('%-5s "%s" is not an app name' % ('ok' if ok else 'FAIL', never))

# ── the retired list is inert, and must stay inert ─────────────────────────
# It is kept as the record of what was tried. If anything starts reading it
# again, the blocklist-against-English approach is back.
print()
src = open(os.path.join(REPO, 'tools', 'sairn_claim.py'), encoding='utf-8').read()
uses = [ln for ln in src.split('\n')
        if 'GENERIC_TOKENS' in ln and not ln.strip().startswith('#')
        and 'GENERIC_TOKENS = {' not in ln]
ok = not uses
fails += 0 if ok else 1
print('%-5s GENERIC_TOKENS is referenced by no code (%s)'
      % ('ok' if ok else 'FAIL', uses or 'none'))
ok = not hasattr(claim, 'blocks_alone')
fails += 0 if ok else 1
print('%-5s the old blocks_alone() entry point is gone' % ('ok' if ok else 'FAIL'))


print()
print('=== phrase evidence: unordered, and across the subject/task boundary ===')
print('    (2026-09-15 -- both halves produced a FALSE CLEAR on a live claim)')


def _r(ms, mt, ts, tt):
    return claim.block_reason(ms, mt, ts, tt)


def arm(name, cond, detail=''):
    global fails
    fails += 0 if cond else 1
    print('%-5s %s%s' % ('ok' if cond else 'FAIL', name,
                         '' if cond else '\n      ' + str(detail)[:300]))


# THE LIVE CASE. Hank probed `recombination crlf lf false alarm` against Cody's
# active `... CRLF recombination ...` and got CLEAR, with BOTH `crlf` and
# `recombination` shared as tokens. argv[0] is the subject, so the pair that
# would have matched straddled the subject/task split AND was reversed.
arm('a reversed phrase matches -- "crlf recombination" vs "recombination crlf"',
    _r('recombination', 'crlf lf false alarm',
       'cody', 'date recombination, CRLF recombination, item 78') is not None,
    'the live false CLEAR of 2026-09-15 is back')

arm('...and specifically as PHRASE evidence, not by some other route',
    'phrase' in (_r('recombination', 'crlf lf false alarm',
                    'cody', 'date recombination, CRLF recombination') or ''),
    _r('recombination', 'crlf lf false alarm', 'cody', 'date recombination, CRLF recombination'))

# The boundary half on its own: one word of subject can form no pair by itself,
# so a subject+task that reads as one sentence must be joined before pairing.
arm('a pair spanning the subject/task boundary is seen',
    _r('soc2', 'readiness', 'cody', 'enforcement audit, SOC2 readiness, incident response') is not None,
    'the CLI splits one typed sentence into subject+task; pairs must span it')

# A pair may span a comma -- a claim is a comma-separated list of subjects and
# the words either side are as adjacent as any other pair.
arm('a pair spanning a comma is seen',
    _r('alpha', 'beta, gamma delta', 'other', 'beta gamma') is not None)

# ── THE CONTROLS, and these are the ones that matter ──────────────────────
# A matcher that blocks everything passes every arm above. Measured over 20,000
# sampled cross-session claim pairs when this shipped: the pair fix moved
# blocking from 494 to 496 -- two extra, both defensible on a read.
arm('CONTROL: two unrelated claims sharing ONE ordinary word still do not block',
    _r('stonedesk', 'drawing tool cutout fix',
       'sairnvet', 'controlled substance witness fix') is None,
    'sharing "fix" alone must never block -- that is what six sessions argued with')

arm('CONTROL: sharing two NON-adjacent words still does not block',
    _r('alpha', 'one two three four', 'beta', 'four nine one') is None,
    'evidence is an adjacent PAIR, not any two words in common')

arm('CONTROL: a genuinely empty comparison is None, not a match',
    _r('', '', '', '') is None)

# ── THE RESIDUAL, PINNED AS OPEN ──────────────────────────────────────────
# `triage plan staleness checker` vs an active `triage staleness tool` is the
# same work and still answers CLEAR: no adjacent pair exists in either
# direction, and checker/tool are synonyms no matcher can know.
#
# THIS ARM ASSERTS THE GAP IS STILL OPEN, deliberately. The obvious fix --
# blocking on a corpus-rare shared token -- was implemented, measured and
# REMOVED: it took blocking from 496 to 570 over the same sample, on words like
# `instead`, `into`, `load` and `commits`. If somebody closes this gap, this arm
# goes red and they must read block_reason()'s note and replace it with an arm
# that pins the NEW rule's false-positive rate. A gap silently closed by a noisy
# heuristic is how a blocking gate becomes one sessions learn to override.
arm('KNOWN OPEN: a synonym with an intervening word still reports CLEAR',
    _r('triage', 'plan staleness checker', 'cody', 'triage staleness tool') is None,
    'this gap was closed -- read block_reason()s note, then replace this arm '
    'with one measuring the new rules false-positive rate over the corpus')

print('\n%d failure(s)' % fails)
sys.exit(1 if fails else 0)
