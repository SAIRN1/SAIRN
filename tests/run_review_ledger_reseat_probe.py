"""Does the review-ledger re-seat repair a citation without corrupting a review?

    python tests/run_review_ledger_reseat_probe.py

THE ARM THAT MATTERS IS THE ONE-LITERAL-TWO-ROLES CASE, and it is not
hypothetical -- it is in the real ledger twice. `a49edd00` is a CITATION in one
record's `what` ("... a49edd00. ATTACK THESE SIX ...") and a QUOTATION in the
same record's `verdict` ("This record cites a49edd00 and no such commit exists in
the repo. The change is 5c781b99"). `ec9ef9af` is the same shape. A re-seat that
replaced the literal across the record -- which is what "re-seat the prose" most
naturally means, and what a first implementation does -- would repair the
citation and simultaneously make a reviewer's verified finding assert the
opposite of what they checked.

So the role is declared PER FIELD, and section 3 drives that case on a fixture
built to mirror it, with a mutation control that widens the replace back across
the record and demands the arm go red.

THE SECOND IS THE THIRD STATE. A prose sha declared in neither `cites` nor
`frozen_shas` is UNDECLARED: not a pass, and not a re-seat failure either. It
means "this citation has no recorded subject, so the next rebase strands it and
nothing can repair it" -- and the only moment the subject can be read is while
the commit is still alive, which is what --adopt is for.

EVERY CRITERION IS LOCKED AGAINST FIXTURES HERE, with the resolver injected, so
none of it was judged against the real ledger first
(docs/2026-09-13-cross-domain-disciplines.md item 1). Nothing in sections 1-4
touches git or the filesystem.
"""
import io
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import review_ledger_reseat as R                                   # noqa: E402

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        fails.append(name)


def resolver(live=(), reachable=(), subjects=None):
    """An injected resolver. `reachable` is the subset of `live` that is an
    ancestor of the base -- the distinction a dangling rebased object makes real,
    and the one this tool has to get right or it calls a stranded citation fine.
    """
    subjects = subjects or {}

    def resolve(spec):
        if 'sha' in spec:
            s = spec['sha']
            if s in reachable:
                return {'state': 'reachable', 'sha': s.ljust(40, '0')}
            if s in live:
                return {'state': 'dead', 'sha': s.ljust(40, '0')}
            return {'state': 'dead', 'sha': None}
        hits = subjects.get(spec.get('subject'), [])
        if len(hits) == 1:
            return {'state': 'reachable', 'sha': hits[0]}
        if len(hits) > 1:
            return {'state': 'ambiguous', 'sha': None}
        return {'state': 'none', 'sha': None}

    return resolve


def acts(rec, resolve):
    return [(a, lit, f) for a, lit, f, _d in R.plan_record(rec, resolve)]


print('review-ledger re-seat -- repair a citation, never a review')

# ── 1. WHAT COUNTS AS A SHA AT ALL ──────────────────────────────────────────
print('\n1. a hex run in prose is not automatically a citation')

rec = {'author_session': 'x', 'opened_at': 't',
       'what': 'a count of 4111111111111111 and 9999999999998 and a real dead0bee',
       'verdict': ''}
found = R.prose_shas(rec)
check('an all-digit run is NOT treated as a sha -- a card number and a count '
      'were both in the live drift report before this rule',
      set(found) == {'dead0bee'}, found)
check('...and the field it appears in is recorded, because the role depends on '
      'the sentence', found['dead0bee'] == ['what'], found)

rec2 = {'author_session': 'x', 'opened_at': 't',
        'what': 'aabbccdd here', 'verdict': 'aabbccdd there too'}
check('one literal in two fields is reported as two field entries',
      sorted(R.prose_shas(rec2)['aabbccdd']) == ['verdict', 'what'],
      R.prose_shas(rec2))

# ── 2. THE THREE STATES OF A DECLARED CITATION ──────────────────────────────
print('\n2. live / re-seatable / stuck -- and stuck is never a guess')

SUBJ = 'fix(thing): the one sentence that survives a rebase'
base = {'author_session': 'a', 'opened_at': 't1', 'verdict': 'Fixed in aaaaaaaa.'}


def withcites(**kw):
    r = dict(base)
    r.update(kw)
    return r


r_live = withcites(cites=[{'sha': 'aaaaaaaa', 'subject': SUBJ, 'in': ['verdict']}])
check('a citation whose sha is REACHABLE is live and nothing is proposed',
      acts(r_live, resolver(live=['aaaaaaaa'], reachable=['aaaaaaaa'])) ==
      [('live', 'aaaaaaaa', 'verdict')],
      acts(r_live, resolver(live=['aaaaaaaa'], reachable=['aaaaaaaa'])))

check('RESOLVABLE IS NOT REACHABLE: a dangling rebased object still resolves, '
      'and calling that live is how a stranded citation goes unrepaired',
      acts(r_live, resolver(live=['aaaaaaaa'], reachable=[],
                            subjects={SUBJ: ['b' * 40]})) ==
      [('reseat', 'aaaaaaaa', 'verdict')])

check('dead + a subject matching exactly one commit is RESEAT',
      acts(r_live, resolver(subjects={SUBJ: ['b' * 40]})) ==
      [('reseat', 'aaaaaaaa', 'verdict')])

check('dead + a subject matching MORE THAN ONE commit is STUCK, not a pick',
      acts(r_live, resolver(subjects={SUBJ: ['b' * 40, 'c' * 40]})) ==
      [('stuck', 'aaaaaaaa', 'verdict')])
check('dead + a subject matching NO commit is STUCK',
      acts(r_live, resolver(subjects={})) == [('stuck', 'aaaaaaaa', 'verdict')])

r_nosubj = withcites(cites=[{'sha': 'aaaaaaaa', 'in': ['verdict']}])
stuck = R.plan_record(r_nosubj, resolver(subjects={SUBJ: ['b' * 40]}))
check('dead + NO recorded subject is STUCK, and the detail says so rather than '
      'reporting a failed lookup', stuck[0][0] == 'stuck'
      and 'NO subject was recorded' in stuck[0][3], stuck)

# ── 3. THE ARM THAT MATTERS ─────────────────────────────────────────────────
print('\n3. one literal, two roles, in one record -- the real a49edd00 shape')

TWO_ROLES = {
    'author_session': 'cc', 'opened_at': 't2',
    'what': 'Sixteen resources were writable on the key alone. a49edd00.',
    'verdict': ('FIRST, THE CITATION. This record cites a49edd00 and no such '
                'commit exists in the repo. The change is 5c781b99, found by '
                'message.'),
    'cites': [{'sha': 'a49edd00', 'subject': SUBJ, 'in': ['what']}],
    'frozen_shas': [{'literal': 'a49edd00', 'in': ['verdict'],
                     'why': 'the finding is ABOUT this pointer'}],
}
got = acts(TWO_ROLES, resolver(live=['5c781b99'], reachable=['5c781b99'],
                              subjects={SUBJ: ['5c781b99' + '0' * 32]}))
check('the citation in `what` is RESEAT and the quotation in `verdict` is '
      'FROZEN -- two verdicts for one literal in one record',
      ('reseat', 'a49edd00', 'what') in got
      and ('frozen', 'a49edd00', 'verdict') in got, got)
# The fixture's verdict also NAMES the live replacement ("The change is
# 5c781b99"), and that is a third, correct verdict rather than noise: a reviewer
# writing the answer into their prose has created a citation nobody declared, so
# the next rebase strands THAT one. Asserted rather than tolerated.
check('...and the replacement sha the reviewer typed into their own prose is '
      'itself UNDECLARED -- the fix for one dead citation quietly created the '
      'next one, which is why --adopt exists',
      ('undeclared', '5c781b99', 'verdict') in got, got)

rec3 = json.loads(json.dumps(TWO_ROLES))
R.apply_reseat(rec3, 'a49edd00', ['what'], '5c781b99' + '0' * 32)
check('THE ARM THAT MATTERS: `what` is repaired',
      '5c781b99' in rec3['what'] and 'a49edd00' not in rec3['what'], rec3['what'])
check('...AND `verdict` IS UNTOUCHED, so the reviewer\'s finding still says what '
      'they verified. A record-wide replace would make it deny its own report.',
      rec3['verdict'] == TWO_ROLES['verdict'], rec3['verdict'])
check('the `cites` entry moved too, and remembers what it was',
      rec3['cites'][0]['sha'] == '5c781b99'
      and rec3['cites'][0]['reseated_from'] == ['a49edd00'], rec3['cites'])

# MUTATION CONTROL: widen the replace back across the record and the arm above
# must go red. Without this, "verdict is untouched" passes on any fixture whose
# verdict happens not to contain the literal.
mut = json.loads(json.dumps(TWO_ROLES))
for f in R.PROSE_FIELDS:
    if mut.get(f):
        mut[f] = mut[f].replace('a49edd00', '5c781b99')
check('MUTANT: a record-wide replace DOES corrupt the verdict -- so the arm '
      'above is measuring that, not a fixture accident',
      mut['verdict'] != TWO_ROLES['verdict']
      and 'cites 5c781b99 and no such commit exists' in mut['verdict'],
      mut['verdict'])

check('the cited LENGTH is preserved -- a record that cited 8 characters gets 8',
      len(R.apply_reseat(json.loads(json.dumps(TWO_ROLES)), 'a49edd00',
                         ['what'], 'f' * 40)) == 8)
LONG = {'author_session': 'a', 'opened_at': 't', 'what': 'x ' + 'a' * 40,
        'cites': [{'sha': 'a' * 40, 'subject': SUBJ, 'in': ['what']}]}
check('...and a 40-character citation gets 40, not a 12-character stub',
      R.apply_reseat(LONG, 'a' * 40, ['what'], 'b' * 40) == 'b' * 40)

# ── 4. THE OTHER TWO VERDICTS ───────────────────────────────────────────────
print('\n4. undeclared, conflict, orphan -- reported, never resolved silently')

und = {'author_session': 'a', 'opened_at': 't', 'what': 'landed in deadbeef.'}
u = R.plan_record(und, resolver(live=['deadbeef'], reachable=['deadbeef']))
check('a live prose sha declared NOWHERE is UNDECLARED, not a pass -- it has no '
      'recorded subject, so the next rebase strands it',
      u == [('undeclared', 'deadbeef', 'what', u[0][3])] and 'resolves today' in u[0][3], u)
u2 = R.plan_record(und, resolver())
check('...and an UNDECLARED sha that is ALREADY dead says that instead, because '
      'nothing recorded what it was', 'ALREADY DEAD' in u2[0][3], u2)

conf = {'author_session': 'a', 'opened_at': 't', 'verdict': 'x aaaaaaaa y',
        'cites': [{'sha': 'aaaaaaaa', 'subject': SUBJ, 'in': ['verdict']}],
        'frozen_shas': [{'literal': 'aaaaaaaa', 'in': ['verdict'], 'why': 'w'}]}
c = R.plan_record(conf, resolver(subjects={SUBJ: ['b' * 40]}))
check('declared as BOTH cited and frozen in the SAME field is CONFLICT, and it '
      'is refused rather than resolved in either direction',
      ('conflict', 'aaaaaaaa', 'verdict') in [(a, l, f) for a, l, f, _ in c], c)
check('...and a CONFLICT record proposes no reseat for that field',
      ('reseat', 'aaaaaaaa', 'verdict') not in
      [(a, l, f) for a, l, f, _ in c], c)

orph = {'author_session': 'a', 'opened_at': 't', 'what': 'nothing here',
        'cites': [{'sha': 'aaaaaaaa', 'subject': SUBJ, 'in': ['what']}]}
o = R.plan_record(orph, resolver(subjects={SUBJ: ['b' * 40]}))
check('a `cites` entry naming a field the literal is NOT in is ORPHAN -- the '
      'prose was edited without the field moving, which is the drift this '
      'whole field exists to stop',
      o[0][0] == 'orphan', o)

# ── 5. THE SHELL FAILS CLOSED ───────────────────────────────────────────────
print('\n5. no ref to measure against is COULD NOT RUN, never a re-seat')

saved = R.git
try:
    R.git = lambda *a: None
    raised = False
    try:
        R.base_ref()
    except R.CouldNotRun as e:
        raised = 'NOTHING was changed' in str(e)
    check('with neither origin/main nor HEAD readable, base_ref REFUSES -- '
          'otherwise every citation looks dead and the whole ledger gets '
          're-seated on the strength of not being able to look', raised)
finally:
    R.git = saved

# ── 6. IT RUNS, AND ITS EXIT CODES ARE THE THREE IT DOCUMENTS ───────────────
print('\n6. the real ledger, read-only')

r = subprocess.run([sys.executable, os.path.join(REPO, 'tools',
                                                 'review_ledger_reseat.py')],
                   capture_output=True, text=True, encoding='utf-8',
                   errors='replace', cwd=REPO)
check('--check exits 0, 1 or 2 and nothing else', r.returncode in (0, 1, 2),
      r.returncode)
check('...and it names the ref reachability was measured against, rather than '
      'leaving a reader to assume', 'measured against' in (r.stdout or ''),
      (r.stdout or '')[:200])
check('the dead opened_at_sha stamps are reported as OUT OF SCOPE with the '
       'reason, not silently skipped -- opened_at_sha is the author\'s HEAD at '
       'open, a different fact from the commit a message match would find',
      'OUT OF SCOPE' in (r.stdout or '') or 'dead stamp' in (r.stdout or ''),
      (r.stdout or '')[-600:])

before = io.open(os.path.join(REPO, 'docs', 'tier-a-reviews.json'),
                 encoding='utf-8').read()
subprocess.run([sys.executable, os.path.join(REPO, 'tools',
                                             'review_ledger_reseat.py')],
               capture_output=True, text=True, cwd=REPO)
after = io.open(os.path.join(REPO, 'docs', 'tier-a-reviews.json'),
                encoding='utf-8').read()
check('a bare run WRITES NOTHING -- a checker that edits the thing it checks is '
      'not a checker', before == after)

print('')
if fails:
    print('%d ARM(S) FAILED:' % len(fails))
    for f in fails:
        print('  - ' + f)
    sys.exit(1)
print('ALL ARMS PASS')
