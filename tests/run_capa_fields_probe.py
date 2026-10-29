"""Control for the contributing-factor fields in tools/defect_register.py (item 75).

Run: python tests/run_capa_fields_probe.py

WHY THESE FIELDS EXIST. Richard Cook, How Complex Systems Fail, points 4 and 7:
overt failure requires multiple faults, so post-accident attribution to a root
cause is fundamentally wrong. A CAPA form with one ROOT CAUSE box does not
merely record less -- it ASSERTS that fixing the named thing closes the door,
and the closure is the wrong part. The other contributors are still latent and
now carry a record saying the incident is handled.

WHAT THIS PROBE DEFENDS. Every rule below is a rule that can be silently
removed: delete the `root_cause` refusal and the field comes back; delete the
`recurrence_open` requirement and every record reads as closed; delete the
single-factor note and one cause becomes the default shape again. A validator
with no control is a validator that stops validating on the day somebody
simplifies it.

IN-PROCESS AND AGAINST THE REAL REPO. An earlier sweep ran these mutants in a
COPIED tree with no `.git`, so every commit failed to resolve and all twelve
mutants reported CAUGHT for a reason that had nothing to do with the rules --
a false green that looked exactly like a real one.
"""
import contextlib
import copy
import io
import json
import os
import shutil
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import defect_register as D                                      # noqa: E402

CONTROLS_FOR = ['defect_register.py']

fails = []
# ── THE MUTATED COPY LEFT THE TREE, 2026-10-15 ────────────────────────────
# This wrote `docs/_capa_probe_tmp.json` -- 2,461,216 bytes, a whole copy of
# the real defect register -- INSIDE the repository, and removed it in a
# `finally` at the bottom of the file. A `finally` does not run when the
# process is KILLED, and this probe is killed: it exceeds 180s. So every
# timed-out run left 2.46MB of untracked JSON in `docs/`, and that is the
# tree-dirtier b15's full-tree run could see but could not attribute.
# Measured today: `timeout 200 python tests/run_capa_fields_probe.py` ->
# rc 124, and `git status --porcelain` -> `?? docs/_capa_probe_tmp.json`.
#
# IT NOW LIVES OUTSIDE THE REPO. defect_register resolves its register as
# `os.path.join(REPO, REG)`, and os.path.join returns the second argument
# unchanged when it is absolute, so an absolute path here needs no change in
# the tool. A kill can no longer dirty any clone, which is a stronger
# guarantee than a cleanup path that has to be reached.
_TMP_DIR = tempfile.mkdtemp(prefix='capa_probe_')
TMP_FULL = os.path.join(_TMP_DIR, '_capa_probe_tmp.json')
BASE = json.load(io.open(os.path.join(REPO, D.REG), encoding='utf-8'))


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        fails.append(name)
    # FLUSHED PER ARM. stdout is block-buffered when this run is redirected to
    # a log, so the run killed at the 180s ceiling wrote a ZERO-BYTE log and a
    # hang was indistinguishable from a silent pass. Segmented verification
    # needs its segments legible while the run is still going.
    sys.stdout.flush()


def with_register(mutate):
    """cmd_check's exit code against a mutated copy of the real register."""
    reg = copy.deepcopy(BASE)
    mutate(reg)
    io.open(TMP_FULL, 'w', encoding='utf-8', newline='').write(
        json.dumps(reg, indent=1, ensure_ascii=False) + '\n')
    old, buf = D.REG, io.StringIO()
    D.REG = TMP_FULL
    try:
        with contextlib.redirect_stdout(buf):
            rc = D.cmd_check()
    finally:
        D.REG = old
    return rc, buf.getvalue()


def first_cf(reg):
    return next(r for r in reg['records'] if r.get('contributing_factors'))


def refuses(name, mutate, expect_text=None):
    rc, out = with_register(mutate)
    ok = rc != 0 and (expect_text is None or expect_text in out)
    check(name, ok, out[-400:])


def accepts(name, mutate):
    rc, out = with_register(mutate)
    check(name, rc == 0, out[-400:])


print('CAPA field control -- Cook points 4 and 7\n')
try:
    # ── THE BASELINE. Without this every "CAUGHT" below could be a validator
    #    that refuses everything, which would pass all ten refusal arms.
    accepts('the shipped register PASSES', lambda reg: None)

    check('the register really carries contributing factors, or every arm '
          'below is about a field nobody uses',
          any(r.get('contributing_factors') for r in BASE['records']),
          'no record carries contributing_factors')
    check('...on a real incident, with more than one factor -- a single-factor '
          'record would not exercise Cook\'s point at all',
          len(first_cf(BASE)['contributing_factors']) > 1,
          len(first_cf(BASE).get('contributing_factors') or []))

    # ── THE FIELD THAT MUST NOT EXIST ──────────────────────────────────────
    refuses('a `root_cause` field is REFUSED BY NAME, not merely absent',
            lambda reg: first_cf(reg).__setitem__('root_cause', 'the socket dropped'),
            'root_cause')

    # ── WHAT THE ACTIONS DO NOT CLOSE ──────────────────────────────────────
    refuses('factors with no recurrence_open are refused -- a corrective '
            'action is evidence about one contributor, never about recurrence',
            lambda reg: first_cf(reg).pop('recurrence_open'))
    refuses('...and a blank one is the same as none',
            lambda reg: first_cf(reg).__setitem__('recurrence_open', '   '))
    # "yes" is PRESENT, so the two arms above never saw it -- and seven real
    # records carried exactly that until 2026-10-29. --check has to refuse a
    # value that names nothing, not only an absent one.
    refuses('...and a bare "yes" is refused by --check -- present is not the '
            'same as naming a residual',
            lambda reg: first_cf(reg).__setitem__('recurrence_open', 'yes'),
            'recurrence_open is 3 characters')
    accepts('...while a SENTENCE saying the path cannot recur, and why, is '
            'accepted -- the floor refuses silence, not a closed verdict',
            lambda reg: first_cf(reg).__setitem__(
                'recurrence_open', 'Nothing on this path can recur: the only '
                'writer was deleted in the same commit.'))

    # ── ONE FACTOR IS A CLAIM, NOT A DEFAULT ───────────────────────────────
    def one_factor(reg, note=None):
        r = first_cf(reg)
        r['contributing_factors'] = [r['contributing_factors'][0]]
        if note:
            r['single_factor_note'] = note

    refuses('one contributing factor with no single_factor_note is refused',
            lambda reg: one_factor(reg))
    accepts('...and one factor WITH a note is accepted -- the rule is that a '
            'single cause gets STATED, not that it is forbidden',
            lambda reg: one_factor(reg, 'only one contributor was identified '
                                        'and this is why'))

    # ── THE VOCABULARY AND THE ACTION ──────────────────────────────────────
    refuses('a factor kind outside the vocabulary is refused',
            lambda reg: first_cf(reg)['contributing_factors'][0]
            .__setitem__('kind', 'vibes'))
    refuses('an action_status outside the vocabulary is refused',
            lambda reg: first_cf(reg)['contributing_factors'][0]
            .__setitem__('action_status', 'maybe'))
    refuses('status `done` with no action is refused -- a status without the '
            'thing that was done is the CAPA box this field replaces',
            lambda reg: first_cf(reg)['contributing_factors'][0]
            .__setitem__('action', ''))

    def declined(reg, note=None):
        f = first_cf(reg)['contributing_factors'][0]
        f['action_status'] = 'declined'
        f.pop('note', None)
        if note:
            f['note'] = note

    refuses('status `declined` with no note is refused -- deciding not to act '
            'is a decision and gets written down',
            lambda reg: declined(reg))
    accepts('...and `declined` WITH a note is accepted',
            lambda reg: declined(reg, 'deliberately not acted on, because'))

    # ── SHAPE ──────────────────────────────────────────────────────────────
    refuses('an empty factor list is refused',
            lambda reg: first_cf(reg).__setitem__('contributing_factors', []))
    refuses('a factor list that is not a list is refused -- a string here is '
            'the single root cause wearing the new field name',
            lambda reg: first_cf(reg).__setitem__('contributing_factors',
                                                  'the socket dropped'))
    refuses('a factor with no text is refused',
            lambda reg: first_cf(reg)['contributing_factors'][0]
            .__setitem__('factor', '  '))

    # ── AND THE REAL RECORD SAYS WHAT IS STILL OPEN, IN WORDS ──────────────
    # Not just non-empty: the point of the field is that it names a residual,
    # so an entry reading "n/a" would satisfy a length check and nothing else.
    single_kind = []
    for r in BASE['records']:
        if not r.get('contributing_factors'):
            continue
        # THIS ARM PINNED A PHRASE AND IT WAS WRONG TO. It required the
        # literal 'NOT CLOSED', which is how I happen to write these; another
        # session states the residual in its own words -- "Nothing stops the
        # next reader...", "Nothing validates..." -- which satisfies the
        # property better than a magic phrase does. A checker that demands one
        # wording is a WORD LIST, which is the thing this platform refuses
        # everywhere else, and it would have pushed the next author toward
        # copying a string rather than saying what is open.
        #
        # The real property is: it states a residual, and does not dismiss one.
        _open = ' '.join(str(r['recurrence_open']).split())
        _dismissals = ('none', 'n/a', 'na', 'nothing further', 'closed',
                       'no residual', 'fully closed', 'complete')
        check('%s: recurrence_open states a residual rather than dismissing one'
              % r['commit'],
              len(_open) > 60 and _open.strip().lower().rstrip('.') not in _dismissals,
              _open[:140])
        # REPORTED, NOT FAILED -- and the demotion is the point. This arm
        # required more than one KIND, and `defect_register.py` requires no
        # such thing. It failed on another session's record whose three
        # factors are all technical and whose LATENT CONDITION is stated in
        # `recurrence_open` instead ("every other svData caller is still
        # unguarded"), which is a defensible place to put what the action does
        # not close.
        #
        # A probe that fails another author's record for a rule the TOOL does
        # not enforce is a probe about my preferences. If single-kind records
        # should be refused, that belongs in cmd_check where every author sees
        # it -- and that is a decision about how everyone records a defect,
        # not one to impose from a control on one session's habit.
        kinds = set(f.get('kind') for f in r['contributing_factors'])
        if len(kinds) == 1:
            single_kind.append((r['commit'], sorted(kinds)))
finally:
    shutil.rmtree(_TMP_DIR, ignore_errors=True)

print('\n%d failure(s)' % len(fails))
# The count, printed rather than enforced, so the habit stays visible.
if single_kind:
    print('')
    print('  %d record(s) carry factors of ONE kind only -- reported, '
          'not failed:' % len(single_kind))
    for _c, _k in single_kind:
        print('    %s  %s' % (_c, _k))

for f in fails:
    print('  - ' + f)
sys.exit(1 if fails else 0)
