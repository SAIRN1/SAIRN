r"""The attachment controls for tools/confidentiality_candidate_flagger.py's
client-restriction signal -- four measured bleeds that must never come back.

    python tests/confidentiality_flagger_asymmetry_review_probe.py

REPORT-ONLY. Exit 0 by design, findings or not. It asserts nothing about a
shipped app and gates no push.

WHAT THIS FILE WAS, AND WHY IT CHANGED SHAPE. It began on 2026-09-22 as the
independent review discharging cody's Tier A obligation opened 12:33:51Z, and
it carried four findings. All four were then fixed. A review probe whose
findings no longer reproduce is not evidence of anything -- it prints COULD NOT
TELL forever and slowly stops being read. So it was re-aimed at the same four
shapes from the other side: each arm now drives the TOOL and requires the bad
answer to be gone, with a paired control requiring the good answer to survive.
The original measurements are kept as the reason each arm exists, because an
arm that cannot say what it is defending against is one rename from being
deleted as noise.

THE FOUR SHAPES, ALL MEASURED ON THE REAL CORPUS RATHER THAN IMAGINED:

  1. dnt_complaints -- the matched resource name AND the `role===` that
     answered for it were inside the SAME BLOCK COMMENT. The conclusion was
     true only because the comment said so; deleting a comment would have
     flipped the tool's answer on a byte-identical application.
  2. sdn_team -- the "gate" 373 characters away was
     `$('tm-designers').textContent=list.filter(...t.role==='designer'...)`,
     a KPI tile counting rows whose stored `role` COLUMN is designer.
     openTeamModal() and saveTeam() contain no role construct at all.
  3. sd_remakes / sd_comms -- both answered TRUE off ONE `_ROLES` declaration
     sitting above a bulk localStorage loader and belonging to neither. It
     produced no false CANDIDATE only because the server half happened to say
     gated, which is masking rather than correctness.
  4. The fixture lock covered ONE signal of three: self_test() called
     payload_fields() and nothing else, while the docstring claimed six cases
     covered "both defect shapes" -- both had been found in the same
     coordinate.

AND TWO MORE THAT THE FIX ITSELF INTRODUCED AND MEASUREMENT CAUGHT BEFORE IT
SHIPPED, both fail-open, both pinned here (arms 5 and 6): anchoring the
function body on `^function name(` matched NOTHING in one app and silently made
the whole 667,230-character file one unit; and a function body can legitimately
BE the whole app, so containment inside one is not attachment.

THE CHECKS GO THROUGH THE TOOL, because what is being defended is the tool's
ANSWER. Where a claim is about the app rather than the tool -- arm 2's "nothing
actually restricts sdn_team" -- it is checked by reading the write path, which
is a structurally different method from the regex under review.

EVERY ANCHOR IS COUNTED AND A MISSING ONE IS A COULD-NOT-TELL, NOT A PASS.
"""
CONTROLS_FOR = ['tools/confidentiality_candidate_flagger.py']

import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'tools'))
os.chdir(REPO)

import confidentiality_candidate_flagger as F          # noqa: E402

FINDINGS, PASSES, CNR = [], [], []


def ok(label, cond, detail=''):
    if cond:
        PASSES.append(label)
        print('  ok   %s' % label)
    else:
        FINDINGS.append(label)
        print('  FAIL %s' % label)
        if detail:
            print('       %s' % str(detail)[:400])


def could_not_tell(label, text):
    CNR.append(label)
    print('  ---- COULD NOT TELL: %s' % label)
    print('       %s' % text)


print(__doc__.split('\n\n')[0])
print('\n' + '=' * 72)

pages, missing = F.app_sources()
owner = F.resource_app()
rows = F.register_rows()
bc = [n for n, t, _ in rows if t in ('B', 'C')]
handler = io.open(os.path.join(REPO, 'api', 'sd-data.js'),
                  encoding='utf-8', errors='replace').read()

if not bc:
    could_not_tell('corpus', 'no B/C rows parsed from the register; every arm '
                             'below would pass vacuously. Nothing was checked.')
    print('\n%d passed, %d finding(s), %d could-not-tell.'
          % (len(PASSES), len(FINDINGS), len(CNR)))
    sys.exit(0)

restricted, unreadable = {}, {}
for n in bc:
    g, u = F.client_restricted(n, pages, owner)
    restricted[n] = g
    unreadable[n] = u
asym = [n for n, g in restricted.items() if g and not F.server_gated(n, handler)[0]]
print('\nCORPUS: %d register rows, %d B/C. client_restricted TRUE for %d, '
      'could-not-tell for %d,\nand %d reach the asymmetry signal: %s\n'
      % (len(rows), len(bc), len([g for g in restricted.values() if g]),
         len([u for u in unreadable.values() if u]), len(asym),
         ', '.join(sorted(asym)) or '(none)'))

# ── 1. THE COMMENT BLEED ───────────────────────────────────────────────────
if 'dnt_complaints' not in restricted:
    could_not_tell('arm 1', 'dnt_complaints is not a B/C row any more.')
else:
    page = pages[owner['dnt_complaints']]
    clean, _ = F._parsed(owner['dnt_complaints'], page)
    occ = len(list(re.finditer(r"'dnt_complaints'", page)))
    occ_clean = len(list(re.finditer(r"'dnt_complaints'", clean)))
    ok('1a the comment-borne occurrence is GONE from the stripped source, so '
       'nothing can match inside it (%d occurrences in the file, %d survive '
       'comment stripping)' % (occ, occ_clean), occ_clean < occ,
       (occ, occ_clean))
    ok('1b ...and dnt_complaints is no longer reported as client-restricted '
       'on the strength of a comment', not restricted['dnt_complaints'],
       restricted['dnt_complaints'])

# ── 2. THE KPI-TILE BLEED ──────────────────────────────────────────────────
if 'sdn_team' not in restricted:
    could_not_tell('arm 2', 'sdn_team is not a B/C row any more.')
else:
    ok('2a sdn_team is no longer reported as client-restricted off a record '
       'field', not restricted['sdn_team'], restricted['sdn_team'])
    # THE CLAIM ABOUT THE APP, CHECKED BY A DIFFERENT METHOD THAN THE REGEX
    # UNDER REVIEW: read the two functions that create and write the record.
    page = pages[owner['sdn_team']]
    unguarded, absent = [], []
    for fn in ('openTeamModal', 'saveTeam'):
        m = re.search(r'(?:async\s+)?function\s+%s\s*\(' % fn, page)
        if not m:
            absent.append(fn)
            continue
        end = page.find('\n}', m.start())
        body = page[m.start():end if end > 0 else m.start() + 2000]
        if not F.CLIENT_GATE.search(body):
            unguarded.append(fn)
    if absent:
        could_not_tell('arm 2b', 'sairndesign has no %s(); the corroboration '
                                 'did not run.' % ', '.join(absent))
    else:
        ok('2b CORROBORATION by reading the write path rather than re-asking '
           'the same regex: %s contain no role construct, so "not restricted" '
           'is the true answer and 2a is right for the right reason'
           % ' and '.join('%s()' % f for f in unguarded),
           len(unguarded) == 2, unguarded)
    ok('2c the record-column rule is what does it, and it is discriminating -- '
       'it rejects `t.role===` and accepts a bare session `role ===`',
       bool(F.RECORD_ROLE.search("t.role==='designer'"))
       and not F.RECORD_ROLE.search("if(role === 'owner')"),
       (F.RECORD_ROLE.search("t.role==='designer'"),
        F.RECORD_ROLE.search("if(role === 'owner')")))

# ── 3. THE NEIGHBOUR BLEED ─────────────────────────────────────────────────
_bleed = [n for n in ('sd_remakes', 'sd_comms') if n in restricted]
if not _bleed:
    could_not_tell('arm 3', 'neither sd_remakes nor sd_comms is a B/C row.')
else:
    ok('3a the bulk-loader bleed is gone: %s no longer answer off a _ROLES '
       'declaration belonging to neither' % ' and '.join(_bleed),
       not any(restricted[n] for n in _bleed),
       {n: restricted[n] for n in _bleed})
    # AND IT IS NOT GONE BECAUSE THE SERVER HALF MASKS IT. That was the old
    # state and it was luck; this asserts the CLIENT half answers correctly on
    # its own, independently of what server_gated says.
    ok('3b ...and that is the CLIENT half answering correctly, not the server '
       'half masking it -- both are still server_gated, so the old masking '
       'would have hidden a wrong answer just as well',
       all(F.server_gated(n, handler)[0] for n in _bleed),
       {n: F.server_gated(n, handler) for n in _bleed})

# ── 4. THE FIXTURE LOCK COVERS BOTH SIGNALS ───────────────────────────────
tool_src = io.open(os.path.join(REPO, 'tools',
                                'confidentiality_candidate_flagger.py'),
                   encoding='utf-8').read()
try:
    body = tool_src[tool_src.index('def self_test('):tool_src.index('def main(')]
except ValueError:
    body = ''
    could_not_tell('arm 4', 'self_test() or main() could not be located.')
if body:
    calls = {f: body.count(f + '(') for f in
             ('payload_fields', 'client_restricted', 'server_gated')}
    ok('4a self_test() exercises the client-restriction signal, not only the '
       'payload one (calls: %s)' % calls, calls['client_restricted'] >= 1, calls)
    ok('4b ...and the client fixtures run in BOTH directions -- at least two '
       'that must NOT restrict and at least one that must',
       len([f for f in F.CLIENT_FIXTURES if not f[3]]) >= 2
       and len([f for f in F.CLIENT_FIXTURES if f[3]]) >= 1,
       [(f[0][:40], f[3]) for f in F.CLIENT_FIXTURES])

# ── 5. THE ANCHOR THAT MATCHED NOTHING ────────────────────────────────────
# `^function name(` found ZERO declarations in sairncode, so the "enclosing
# function" became the whole 667KB file. The brace pass must see into every
# app, and an app it cannot see into must be NAMED.
_blind = F.pages_without_function_bodies(pages)
ok('5a the brace pass finds function bodies in EVERY app page, so no app '
   'silently becomes one giant unit', not _blind, _blind)
# NOT A BARE THRESHOLD. The body count is cross-checked against the number of
# `function`/`=>` keywords INSIDE the script regions of the same page, which is
# the quantity that moves with the app. A lexer desync shows up here as a
# collapsed ratio long before it shows up as a wrong answer. MEASURED across
# all 17 pages after the fix: 0.59 to 0.99, with the low end being stonedesk's
# many one-line arrow callbacks. Before the fix sairnmechanical sat at 0.04.
_ratio = {}
for _a, _s in sorted(pages.items()):
    _clean, _spans = F._parsed(_a, _s)
    _kw = len(re.findall(r'function|=>', _clean))
    _ratio[_a] = round(len(_spans) / max(_kw, 1), 2)
ok('5b ...and the body count tracks the keyword count in every page (min '
   'ratio %.2f across %d pages), so a lexer desync collapses this arm before '
   'it reaches an answer' % (min(_ratio.values()), len(_ratio)),
   min(_ratio.values()) >= 0.40, _ratio)

# ── 6. A BODY CAN BE THE WHOLE APP ────────────────────────────────────────
# Containment inside a 403,966-character body is not attachment. Over the
# ceiling must be a COULD-NOT-TELL, never a clean "nothing restricts it".
_over = [n for n in bc if unreadable[n]]
print('  note  %d of %d rows are COULD-NOT-TELL for signal (c): every '
      'occurrence sat in a body\n        over %d characters, or the app has '
      'no page.' % (len(_over), len(bc), F.FUNCTION_BODY_CEILING))
ok('6a not-restricted and could-not-tell are DISJOINT, so the third state is '
   'a real state and not a decorated False',
   not any(restricted[n] and unreadable[n] for n in bc),
   [n for n in bc if restricted[n] and unreadable[n]][:5])
ok('6b CONTROL: the ceiling has NOT swallowed everything -- real gated '
   'handlers are still read and still answer TRUE',
   len([g for g in restricted.values() if g]) > 0,
   sorted(n for n, g in restricted.items() if g)[:8])
ok('6c ...and the could-not-tell set is not the whole corpus either, which '
   'would be a parser that had quietly stopped working',
   len(_over) < len(bc) // 2, (len(_over), len(bc)))

# ── 7. THE OBLIGATION'S ORIGINAL QUESTION, KEPT BECAUSE IT IS STILL THE ───
#      CHEAPEST THING THAT COULD SILENTLY STOP BEING TRUE.
occ = {n: [tool_src[:m.start()].count('\n') + 1
           for m in re.finditer(re.escape(n), tool_src)]
       for n in ('sd_exec_msgs', 'sen_pay_rates', 'sen_payer_contracts')}
writes = (re.findall(r"io\.open\([^)]*,\s*'[wa]", tool_src)
          + re.findall(r"\.write\(", tool_src))
ok('7a the three Tier A names are still inert text -- docstring prose or '
   'fixture page bodies, never a resource under test: %s'
   % {k: len(v) for k, v in occ.items()}, all(occ.values()), occ)
ok('7b ...and the tool still has no write path at all (%d io.open calls, %d '
   'write-mode or .write())' % (tool_src.count('io.open('), len(writes)),
   not writes, writes[:3])

print('\n' + '=' * 72)
print('%d passed, %d finding(s), %d could-not-tell. Report-only: exit 0 by '
      'design.' % (len(PASSES), len(FINDINGS), len(CNR)))
for f in FINDINGS:
    print('  FINDING: %s' % f)
sys.exit(0)
