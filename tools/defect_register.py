"""defect_register.py -- a standing log of CONFIRMED defects, with a real denominator.

    python tools/defect_register.py --report
    python tools/defect_register.py --check
    python tools/defect_register.py --reseat   # rewrite SHAs a rebase moved
    python tools/defect_register.py --add --commit SHA --app X --layer product \\
        --severity high --method fault-injection --summary "..."

── WHY IT IS DELIBERATELY NOT A COMMIT LOG ─────────────────────────────────
`git log --grep '^fix('` returns thirty entries for 2026-09-10 alone, and most
of them are NOT product defects: harness corrections, checkers whose first real
run needed tightening, my own probe mistakes. Auto-ingesting those would make
the density figure large and meaningless, and the number would then be quoted.

So a record is ADDED DELIBERATELY and carries a judgement nobody can derive --
what LAYER it was in, how severe, and above all HOW IT WAS FOUND. The
mechanical half (date, files, lines, whether the commit exists) is derived from
git, because a field a human retypes is a field that goes wrong.

── THE NUMBER IS NOT THE SIGNAL, AND THIS FILE SAYS SO IN ITS OWN OUTPUT ───
A defect density needs a denominator, and this one uses real line counts. But a
density is a fact about what has been LOOKED AT, not about what is there. The
honest signal is CONSECUTIVE ZERO-NEW-FINDING SWEEPS BY DIFFERENT METHODS over
the same files -- which is why every record names its detection method and why
`--report` prints a method x app coverage matrix beside the density.

The evidence for that is one day old: on 2026-09-10 the mutation controls found
two defects in test code that reading the assertions had not, on the same files
in the same hour. One method returning zero means that method is exhausted.

── IT STARTS ON 2026-09-09 AND IS NOT BACKFILLED BEYOND THAT ───────────────
Every record here was verified by somebody who could attest to it. Reaching
further back would mean classifying commits nobody present can vouch for, and a
register padded with guesses is worse than a short one: its size would imply a
completeness it does not have.
"""
import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REG = os.path.join('docs', 'defect-density-register.json')

LAYERS = ('product', 'tooling', 'test')
SEVERITIES = ('critical', 'high', 'moderate', 'low')

# ── WHAT THE FOUR WORDS MEAN (added 2026-09-15, and the evidence is measured)
# `layer` and `injection_phase` each carry a paragraph explaining what they are.
# SEVERITY CARRIED NOTHING -- four words and no definitions -- and two blind
# review rounds measured what that costs.
#
# tools/blind_review.py withholds the recorded severity, takes a reviewer's own
# judgment first, and only then reveals. Across two rounds, 14 records:
# **6 AGREED, 8 DID NOT -- and the 8 split 4 MORE severe and 4 LESS.**
#
# THE SPLIT IS THE FINDING, NOT THE RATE. A one-sided split would be a
# CALIBRATION OFFSET -- two people using the same scale from different places,
# fixed by agreeing an anchor. An even split is DISPERSION: the same scale
# applied inconsistently because it has no definition to be consistent with.
# Those need opposite fixes and an agreement rate alone cannot tell them apart.
#
# So the definitions below are written against CONSEQUENCE IF THE DEFECT
# REACHES A USER, which is the question every other tier on this platform asks:
#
#   critical  Money moves wrongly, a record is destroyed with no recovery, or
#             an unauthorised party reaches data. Reachable on a real
#             deployment by a real caller, not only in principle.
#   high      A silent failure that shows SUCCESS, a control that does not
#             refuse what it exists to refuse, or a platform-wide defect whose
#             trigger is a condition that really occurs. Recoverable, but the
#             user is not told.
#   moderate  A visible wrong answer, a refusal a user cannot act on, or a
#             control that stopped testing what it claims to test. Somebody
#             notices.
#   low       A cosmetic or documentation defect, or a wrong number in a report
#             nobody gates on.
#
# ── THE 85 RECORDS THAT PREDATE THIS ARE **NOT** RE-TIERED ─────────────────
# Stated because it matters to anything that reads the field: every record
# before 2026-09-15 was assigned with no definition to assign against, so the
# corpus is MIXED. tools/defect_budget_policy.py weights by severity, which
# means its numbers span two vocabularies. Re-tiering 85 records is a
# governance decision with a real cost either way and is not one a definition
# comment gets to make silently.
SEVERITY_DEFINED_FROM = '2026-09-15'

# ── WHERE THE DEFECT WAS INJECTED (item 77, added 2026-09-14) ──────────────
# `detection_method` records how a defect was REMOVED. This records where it
# was PUT IN. Two different questions, and only both together make an
# injection-vs-removal matrix mean anything: "code review found 25 defects" is
# a raw count until you can also say which phase those 25 came from, and
# therefore which phase is worth attacking.
#
# DELIBERATELY ORTHOGONAL TO `layer`. Layer says WHERE the defect lives
# (product / tooling / test); phase says WHEN it entered. A test file can carry
# a coding defect or a design defect, and collapsing the two axes would make
# the matrix unreadable in exactly the way one label per app made
# CRITICALITY-TIERS.md stop discriminating.
#
# THE DISCRIMINATOR, written down so it decides cases instead of describing
# them -- ask in this order and stop at the first that answers:
#   requirement  fixing it changes WHAT the thing is supposed to do
#   design       the code faithfully implements a plan that could not work;
#                the fix needs a different structure, not a corrected line
#   coding       the plan was right, the expression is not
#   config       the fix is outside the source entirely -- a grant, an env var,
#                a migration nobody ran, a clone's own git config
#   unknown      none of the above honestly fits
#
# `unknown` IS A REAL ANSWER AND REQUIRES A NOTE, for the same reason
# `not-citable` does: a vocabulary with no honest escape hatch does not produce
# accurate data, it produces data pushed into the nearest bin. A bare
# `unknown` is a silence, not a decision.
# ── WHICH CHECKPOINT CAUGHT IT (item 63, added 2026-09-14) ────────────────
# `detection_method` says WHICH TECHNIQUE found a defect. This says WHAT KIND OF
# CHECKPOINT that technique is, which is the question behind "are we relying on
# people reading code, or on something that runs".
#
#   human-read         a person read it. No automated checkpoint covered it.
#   automated-checker  a checker, probe or mutation control found it.
#   monitoring         it was observed in RUNNING behaviour -- live verification
#                      or a user report. Nothing static could have seen it.
#   unknown            requires a note.
#
# DERIVED FROM detection_method BY A FIXED RULE, not judged per record -- the
# mapping is in CHECKPOINT_OF below and there is nothing to get wrong twice.
#
# THE LIMIT, AND IT IS THE WHOLE HONEST FRAME: this measures the checkpoint that
# DID catch each defect, not the one that SHOULD have. Those differ exactly
# where a gate ought to exist and does not, so this UNDER-COUNTS gaps by
# construction. It is the closest thing the register's existing fields can
# support, and calling it the other thing would be a fabrication.
#
# AND IT CANNOT SPLIT GATE FROM REPORT-ONLY. A record names the technique, never
# the tool, so "a checker found it" cannot be resolved into "a blocking gate
# found it". Adding a `found_by_tool` field is the next thing somebody should do
# and is deliberately not invented here.
# ── WHICH TOOL FOUND IT (added 2026-09-14) ────────────────────────────────
# Item 63 could say "a checker found it" and could NOT say whether that checker
# BLOCKS. A record named the technique and never the tool, so the one question
# behind the whole checkpoint split -- are we stopped before a push, or merely
# told afterwards -- was unanswerable. This is that field.
#
# REQUIRED exactly when the checkpoint is `automated-checker`, and REFUSED
# otherwise: a code review has no tool, and inviting one would produce a column
# of plausible-looking names nobody could check.
#
# `unknown` is allowed and is honest for the backfill: 2026-09-14's records
# name their tool in the summary or not at all, and inventing one for the rest
# would be exactly the manufactured agreement the citation field is careful to
# avoid. The report prints the unknown share above the split.
TOOL_UNKNOWN = 'unknown'


def tool_required(method):
    return checkpoint_of(method) == 'automated-checker'


CHECKPOINTS = ('human-read', 'automated-checker', 'monitoring', 'unknown')
CHECKPOINT_OF = {
    'code-review': 'human-read',
    'independent-review': 'human-read',
    'static-checker': 'automated-checker',
    'mutation-testing': 'automated-checker',
    'fault-injection': 'automated-checker',
    'probe-control': 'automated-checker',
    'traceability-matrix': 'automated-checker',
    'live-verification': 'monitoring',
    'user-report': 'monitoring',
}


def checkpoint_of(method):
    """The checkpoint kind for a detection method. Unknown methods are NOT
    silently bucketed -- a new method added to METHODS without a row here comes
    back 'unknown' and --check says so, rather than being folded into whichever
    bucket happened to look closest."""
    return CHECKPOINT_OF.get(method, 'unknown')


PHASES = ('requirement', 'design', 'coding', 'config', 'unknown')

# How good the phase call is. Same shape as citation_confidence, and for the
# same reason: most of these are read from a one-line summary rather than from
# the diff, and a register that cannot say so would be overstating itself.
#   stated    the record's own summary names the defective construct
#   inferred  the phase is a judgement about the summary, not a quote from it
PHASE_CONFIDENCES = ('stated', 'inferred')
# Every method that has actually found something on this platform. Named rather
# than free text, so the coverage matrix means something -- and extended
# deliberately when a genuinely new method finds its first defect.
METHODS = (
    'code-review', 'mutation-testing', 'fault-injection', 'static-checker',
    'live-verification', 'independent-review', 'traceability-matrix',
    'probe-control', 'user-report',
)

# ── THE STANDING-RULE CITATION, added 2026-09-13 ───────────────────────────
# `tools/fmea_prediction_check.py` has scored ZERO since the day it was written
# and says so in its own docstring: matching a saved risk draft to a defect that
# then happened is by RULE CITATION ONLY, because the first matcher scored 38%
# on three-word overlap AND EVERY ONE OF THOSE FIVE HITS WAS A FALSE POSITIVE.
# Its answer was blocked on this field, not on its own logic.
#
# THREE CONFIDENCES, NOT TWO, AND THE THIRD IS THE POINT. A register that could
# only say "cites rule X" would push every awkward record into a citation it
# does not really instantiate, and the FMEA scorer would then match on
# manufactured agreement -- the 38% arriving through the data instead of the
# matcher. So `not-citable` is a first-class answer, it requires a note saying
# why, and 6 of 54 records carry it.
CONFIDENCES = ('clean', 'arguable', 'not-citable')
RULES_DOC = os.path.join('docs', 'SAIRN-PROCESS-RULES.md')

# ── ITEM 75: COOK'S CRITIQUE, AND WHY THERE IS NO `root_cause` FIELD ────────
# "Complex systems contain changing mixtures of failures latent within them...
# Post-accident attribution to a 'root cause' is fundamentally wrong. Because
# overt failure requires multiple faults, there is no isolated 'cause' of an
# accident." -- Richard Cook, How Complex Systems Fail, points 4 and 7.
#
# A CAPA form with one ROOT CAUSE box and one CORRECTIVE ACTION box does not
# merely record less. It ASSERTS that fixing the named thing closes the door,
# and the closure is the part that is wrong: the other contributors are still
# there, still latent, and now carry a signed-off record saying the incident is
# handled. That is the shape this register would have grown into.
#
# So: a LIST, never a field. `root_cause` is refused by name in --check rather
# than merely absent, because absence is a thing somebody adds back.
#
# EVERY RECORD WITH FACTORS ALSO STATES WHAT IS STILL OPEN. A corrective action
# is evidence about one contributor; it is not evidence about recurrence, and
# the register must not be readable as if it were.
#
# A SINGLE FACTOR IS ALLOWED and must say why it is single. Cook's point is not
# that every defect has three causes -- it is that a one-line cause is a claim
# and claims get stated, not assumed. Forcing a second factor would fabricate
# one, which is worse.
FACTOR_KINDS = (
    'technical',            # the code did the wrong thing
    'process',              # the way the work was done allowed it
    'detection',            # why nothing caught it, given it was there
    'latent-condition',     # a standing condition that made it possible
)
ACTION_STATES = (
    'done',                 # something changed; `action` says what
    'planned',              # named, not yet done
    'declined',             # deliberately not acted on; `note` says why
    'not-actionable',       # no action would address it; `note` says why
)


def known_rules():
    """Section ids parsed out of the process rules themselves.

    DERIVED, NOT LISTED. A hand-kept vocabulary of rule ids is a second copy of
    the rules document, and this repo has corrected that exact shape in the
    Guardian App File Map seven times. A citation naming a section that does not
    exist is a finding; a citation naming one that was renumbered should fail
    loudly rather than sit there looking checked.

    Returns None when the document cannot be read -- the caller must treat that
    as COULD NOT CHECK, never as "every citation is fine" (PR 1.11).
    """
    p = os.path.join(REPO, RULES_DOC)
    if not os.path.isfile(p):
        return None
    try:
        src = io.open(p, encoding='utf-8').read()
    except Exception:
        return None
    ids = set(re.findall(r'^###\s+(\d+\.\d+)\s', src, re.M))
    ids.update(re.findall(r'^##\s+(Part \d+)\b', src, re.M))
    return ids or None


def git(*a):
    r = subprocess.run(['git', '-C', REPO] + list(a), capture_output=True, text=True, encoding='utf-8', errors='replace')
    return r.stdout.strip() if r.returncode == 0 else None


def load():
    p = os.path.join(REPO, REG)
    if not os.path.isfile(p):
        return {'started': '2026-09-09',
                'note': 'Confirmed defects only. See tools/defect_register.py '
                        'for why this is not a commit log and why the density '
                        'is not the signal.',
                'records': []}
    return json.load(io.open(p, encoding='utf-8'))


def save(d):
    p = os.path.join(REPO, REG)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    io.open(p, 'w', encoding='utf-8', newline='').write(
        json.dumps(d, indent=2, sort_keys=False) + '\n')


# ── WHERE THE DEFECT CAME IN, AS A COMMIT (item 66's prerequisite) ────────
# IBNR -- estimating how many defects exist that nobody has found -- needs a LAG
# DISTRIBUTION: injection date to discovery date. `injection_phase` says when in
# the LIFECYCLE; this says when in TIME, and the two are different fields.
#
# OPTIONAL, WITH A REQUIRED REASON WHEN OMITTED. Exactly the shape of
# `--rule not-citable`, and for the same reason: MANDATORY WOULD PRODUCE
# GUESSES, and silently optional would leave it empty, which is what happened to
# detection_method before item 2/24 measured 1 of 52.
#
# CHEAP AT RECORD TIME AND ONLY THEN. Whoever fixes a defect has just read the
# code and usually knows, or finds it with one `git log -S`. It is NOT honestly
# backfillable -- reconstructing an injection point by blame months later
# produces a lag distribution built from guesses, which is worse than no
# distribution at all. The 67 records that predate this field say so in their
# own reason string rather than carrying an invented sha.
def lag_days(inj_date, fix_date):
    """Whole days between two YYYY-MM-DD strings, or None if either is unusable."""
    import datetime
    try:
        a = datetime.date(*[int(x) for x in str(inj_date)[:10].split('-')])
        b = datetime.date(*[int(x) for x in str(fix_date)[:10].split('-')])
    except Exception:                                          # noqa: BLE001
        return None
    return (b - a).days


def derive(sha):
    """The mechanical half, from git. A field a human retypes goes wrong."""
    full = git('rev-parse', sha)
    if not full:
        return None
    date = git('log', '-1', '--format=%cI', full)
    subject = git('log', '-1', '--format=%s', full)
    stat = git('show', '--numstat', '--format=', full) or ''
    files, added, removed = [], 0, 0
    for line in stat.split('\n'):
        parts = line.split('\t')
        if len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit():
            added += int(parts[0])
            removed += int(parts[1])
            files.append(parts[2])
    return {'commit': full[:12], 'date': (date or '')[:10], 'subject': subject,
            'files': files, 'lines_added': added, 'lines_removed': removed}


def app_lines():
    """The denominator, measured rather than estimated."""
    out = {}
    for f in (git('ls-files', '*.html') or '').split('\n'):
        if f.strip() and '/' not in f:
            p = os.path.join(REPO, f)
            try:
                out[os.path.splitext(f)[0]] = sum(
                    1 for _ in io.open(p, encoding='utf-8', errors='replace'))
            except IOError:
                pass
    return out


def cmd_add(argv):
    def opt(name, required=True):
        if name in argv:
            return argv[argv.index(name) + 1]
        if required:
            print('missing %s' % name)
            sys.exit(2)
        return ''

    sha, app = opt('--commit'), opt('--app')
    layer, sev, method = opt('--layer'), opt('--severity'), opt('--method')
    summary = opt('--summary')
    # REQUIRED, not optional, and that is the whole fix. The field was absent
    # for 54 records because nothing ever asked for it, and `--check` cannot
    # demand of old records what `--add` never collected. Pass
    # `--rule not-citable` when no standing rule names the shape -- with a
    # `--rule-note` saying so. Refusing to record a defect because no rule fits
    # would be worse than the gap this closes.
    rule = opt('--rule')
    note = opt('--rule-note', required=False)
    # REQUIRED, like --rule and for the same reason: a field that is optional
    # at the moment of recording is a field that stays empty, and --check
    # cannot demand of a record what --add never collected. Pass
    # `--phase unknown` with a `--phase-note` when none of the four honestly
    # fits; refusing to record a defect because no phase fits would be worse
    # than the gap this closes.
    # REQUIRED when a tool did the finding, REFUSED when one did not.
    found_by = opt('--found-by-tool', required=False)
    inj = opt('--injection-commit', required=False)
    inj_unknown = opt('--injection-unknown', required=False)
    if bool(str(inj).strip()) == bool(str(inj_unknown).strip()):
        print('pass EXACTLY ONE of --injection-commit <sha> or '
              '--injection-unknown "<why>". Both, or neither, is how this field '
              'would quietly become empty -- which is what happened to '
              'detection_method before it was measured at 1 of 52.'); return 2
    phase = opt('--phase')
    phase_note = opt('--phase-note', required=False)
    if phase not in PHASES:
        print('--phase must be one of %s' % (PHASES,)); return 2
    if phase == 'unknown' and not str(phase_note).strip():
        print('--phase unknown requires --phase-note. A bare unknown is a '
              'silence, not a decision.'); return 2
    # `stated` is a claim that the SUMMARY names the defective construct, so it
    # is checked against the summary rather than taken on trust.
    phase_conf = opt('--phase-confidence', required=False) or 'inferred'
    if phase_conf not in PHASE_CONFIDENCES:
        print('--phase-confidence must be one of %s' % (PHASE_CONFIDENCES,)); return 2
    if layer not in LAYERS:
        print('--layer must be one of %s' % (LAYERS,)); return 2
    if sev not in SEVERITIES:
        print('--severity must be one of %s' % (SEVERITIES,)); return 2
    if method not in METHODS:
        print('--method must be one of %s' % (METHODS,)); return 2
    if tool_required(method) and not str(found_by).strip():
        print('--found-by-tool is required for %r, because it maps to '
              'automated-checker and the whole point of the field is to say '
              'WHICH checker -- pass %r if the record genuinely does not know.'
              % (method, TOOL_UNKNOWN)); return 2
    if not tool_required(method) and str(found_by).strip():
        print('--found-by-tool is not accepted for %r: %s found it, not a tool. '
              'A column of plausible names nobody can check is worse than an '
              'empty one.' % (method, checkpoint_of(method))); return 2
    if rule == 'not-citable':
        rules, conf = [], 'not-citable'
    else:
        rules, conf = [rule], ('arguable' if note else 'clean')
        known = known_rules()
        if known is None:
            # PR 1.11. The vocabulary comes from a document; if that document
            # cannot be read the citation CANNOT BE CHECKED, and accepting it
            # would record an unverified claim as a verified one.
            print('COULD NOT READ %s, so --rule cannot be validated. Not '
                  'recording an unchecked citation.' % RULES_DOC); return 2
        if rule not in known:
            print('--rule %r is not a section in %s. Known: %s'
                  % (rule, RULES_DOC, ', '.join(sorted(known)))); return 2
    if conf != 'clean' and not note:
        print('--rule-note is required unless the citation is clean'); return 2
    d = derive(sha)
    if not d:
        print('no such commit: %s' % sha); return 2
    inj_rec = None
    if str(inj).strip():
        di = derive(inj)
        if not di:
            print('no such injection commit: %s -- a sha that does not resolve '
                  'is not a lag, it is a guess with a hash on it.' % inj); return 2
        inj_rec = {'commit': di['commit'], 'date': di['date'],
                   'subject': di['subject']}
        lag = lag_days(di['date'], d['date'])
        if lag is not None and lag < 0:
            print('the injection commit (%s) is NEWER than the fix (%s). One of '
                  'the two shas is wrong; a negative lag would poison the '
                  'distribution this field exists to build.'
                  % (di['date'], d['date'])); return 2
        inj_rec['lag_days'] = lag
    reg = load()
    key = (d['commit'], summary)
    if any((r['commit'], r['summary']) == key for r in reg['records']):
        print('already registered: %s' % d['commit']); return 0
    rec = dict(d)
    rec.update({'app': app, 'layer': layer, 'severity': sev,
                'detection_method': method, 'summary': summary,
                'rules': rules, 'citation_confidence': conf,
                'injection_phase': phase, 'phase_confidence': phase_conf,
                'found_by_tool': (str(found_by).strip() or None),
                'injection': inj_rec or {'unknown_reason': str(inj_unknown).strip()}})
    if note:
        rec['citation_note'] = note
    if phase_note:
        rec['phase_note'] = phase_note
    reg['records'].append(rec)
    reg['records'].sort(key=lambda r: (r['date'], r['commit']))
    save(reg)
    print('registered %s (%s, %s, %s)' % (d['commit'], app, sev, method))
    fmea_loop(rec)
    return 0


# ── THE FMEA LOOP, ASKED AT THE ONLY MOMENT THE ANSWER CHANGES ─────────────
# Item 26, the FMEA-prediction branch, wired 2026-09-13.
#
# tools/fmea_prediction_check.py's own docstring says its cadence is the defect
# register growing: "it recurs because the answer changes every time the defect
# register grows." Nothing was asking it at that moment. Run by hand it reports
# over the whole corpus and, today, correctly says nothing is scoreable yet --
# a standing 25-line report that a person has to remember to run, about a
# question that only becomes answerable one record at a time.
#
# So the question is asked HERE, about THIS record, while somebody is looking:
#   * was there a draft for the file, and did it PREDATE the defect;
#   * if so, did a risk in it cite the same standing rule;
#   * if not, say which file has no draft, because that is the gap that keeps
#     the corpus unscoreable and it is invisible from anywhere else.
#
# IT NEVER CHANGES THE EXIT CODE. --add succeeded or it did not; whether the
# defect was foreseen is a separate fact and folding it into the return value
# would make a registration fail for the wrong reason.
#
# ── AND IT FAILS LOUD WHEN THE CHECKER IS ABSENT, per PR 1.11 ─────────────
# The tempting shape is `try: import ... except ImportError: pass`, which is a
# check that silently does not run and is indistinguishable from one that ran
# and found nothing. It says which module was missing and that the loop did NOT
# close, and it says it every time.
def fmea_loop(rec):
    print('')
    print('  FMEA LOOP -- was this one foreseen?')
    try:
        sys.path.insert(0, os.path.join(REPO, 'tools'))
        import fmea_prediction_check as fp
    except Exception as e:                                     # noqa: BLE001
        print('    COULD NOT RUN: tools/fmea_prediction_check.py did not import'
              ' (%s). The loop did NOT close for this record -- this is not a'
              ' "no draft" answer and must not be read as one.' % e)
        return
    try:
        drafts = fp.load_drafts()
    except Exception as e:                                     # noqa: BLE001
        print('    COULD NOT RUN: the drafts under docs/fmea/ could not be read'
              ' (%s). Not a pass.' % e)
        return

    by_target = {}
    for dr in drafts:
        by_target.setdefault(dr.get('target'), []).append(dr)

    # A worklog or a doc cannot carry a code defect a draft could have
    # predicted -- the checker's own NOT_A_CODE_TARGET rule, reused rather than
    # re-typed so the two cannot drift apart.
    files = [f for f in rec.get('files', []) if not fp.NOT_A_CODE_TARGET.search(f)]
    if not files:
        print('    no code target in this commit (%d file(s), all worklogs or'
              ' docs) -- nothing a draft could have predicted'
              % len(rec.get('files', [])))
        return

    for f in files:
        cands = by_target.get(f) or []
        if not cands:
            print('    NO DRAFT: %s -- `python tools/fmea_draft.py %s --save`'
                  ' would make the next defect here scoreable' % (f, f))
            continue
        older = [c for c in cands if c.get('_asof') and c['_asof'] <= rec['date']]
        if not older:
            print('    DRAFT NEWER than the defect: %s -- unscoreable by'
                  ' construction, it cannot predict what already happened' % f)
            continue
        hit = None
        for c in older:
            how, risk = fp.matched(c, rec)
            if how:
                hit = (how, c, risk)
                break
        if hit:
            print('    PREDICTED: %s -- %s, from %s' % (f, hit[0], hit[1]['_file']))
        else:
            print('    MISSED: %s -- %d draft(s) predate it and none cites %s'
                  % (f, len(older), ', '.join(rec.get('rules') or ['(no rule)'])))


def subject_index():
    """subject -> [sha]. Built once, because a record that lost its SHA to a
    rebase kept its message: `git rebase` rewrites the hash and preserves the
    subject, which is precisely why the subject is the durable half."""
    out = git('log', '--format=%H%x1f%s', 'HEAD') or ''
    idx = {}
    for line in out.split('\n'):
        if '\x1f' not in line:
            continue
        sha, subj = line.split('\x1f', 1)
        idx.setdefault(subj, []).append(sha)
    return idx


def resolve(rec, idx):
    """(sha, how) -- how is 'sha', 'subject', 'ambiguous' or None.

    ── A REBASED SHA IS NOT A RECORD POINTING AT NOTHING (2026-09-11) ────────
    This used to fail outright on any SHA that would not resolve, and the
    register then sat permanently red: 5 problems when it was first noticed,
    12 hours later, growing because the cause is STRUCTURAL rather than
    anybody's mistake. `--add` derives the SHA from the commit in front of it,
    and with four clones pushing, most commits are rebased onto somebody
    else's work before they reach origin. The SHA recorded is the pre-rebase
    one; the commit it named never existed on `main`.

    That matters more than a stale field. This tool is one of the promoted
    report-only checkers, so **every post-push sweep in every clone carried a
    finding**, which is exactly how a report-only checker earns the reputation
    that gets it switched off before it is ever promoted to a gate.

    So the SHA is treated as what it actually is -- a convenience pointer --
    and the record's identity is its SUBJECT, which survives the rebase. A
    record still FAILS when neither resolves, because that is the real case
    this check exists for: a register pointing at nothing, whose length reads
    as evidence. An AMBIGUOUS subject fails too rather than picking one, since
    guessing which of two commits a record meant is the thing a register must
    never do.
    """
    if git('rev-parse', '--verify', rec['commit'] + '^{commit}'):
        return rec['commit'], 'sha'
    hits = idx.get(rec.get('subject') or '\x00absent', [])
    if len(hits) == 1:
        return hits[0][:12], 'subject'
    if len(hits) > 1:
        return None, 'ambiguous'
    return None, None


def cmd_check(argv=()):
    """Every record must still resolve. A register pointing at nothing is worse
    than none, because its length reads as evidence."""
    reg = load()
    bad, reseat = [], []
    could_not_check = 0
    known = known_rules()
    idx = subject_index()
    for r in reg['records']:
        sha, how = resolve(r, idx)
        if how == 'subject':
            reseat.append((r['commit'], sha, r['subject']))
        elif how == 'ambiguous':
            bad.append('%s -- its subject matches more than one commit, so the '
                       'record cannot be re-seated without guessing: %r'
                       % (r['commit'], r['subject']))
        elif how is None:
            bad.append('%s -- neither the commit nor its subject is in this '
                       'repo: %r' % (r['commit'], r.get('subject')))
        # THE VOCABULARY CHECKS RUN REGARDLESS. They used to sit after a
        # `continue`, so the moment a SHA went stale the rest of that record
        # stopped being checked at all -- a second, quieter hole underneath the
        # loud one, and it would have outlived the fix for the loud one.
        if r['detection_method'] not in METHODS:
            bad.append('%s -- unknown detection method %r'
                       % (r['commit'], r['detection_method']))
        # ITEM 63. A method with no CHECKPOINT_OF row would silently come back
        # 'unknown' and quietly shrink whichever bucket the asymmetry figure is
        # read from. The vocabulary and the mapping have to stay in step.
        elif checkpoint_of(r['detection_method']) == 'unknown':
            bad.append('%s -- detection method %r has no CHECKPOINT_OF row, so '
                       'it would fall into `unknown` and distort the checkpoint '
                       'split' % (r['commit'], r['detection_method']))
        if r['layer'] not in LAYERS or r['severity'] not in SEVERITIES:
            bad.append('%s -- layer/severity outside the vocabulary' % r['commit'])
        # ── THE INJECTION POINT, same rule as --add ──────────────────────
        ij = r.get('injection')
        if not isinstance(ij, dict):
            bad.append('%s -- no injection block. Every record carries either a '
                       'commit or a stated reason it has none.' % r['commit'])
        elif ij.get('commit'):
            if ij.get('lag_days') is not None and ij['lag_days'] < 0:
                bad.append('%s -- negative discovery lag (%s days): the '
                           'injection commit is newer than the fix'
                           % (r['commit'], ij['lag_days']))
        elif not str(ij.get('unknown_reason') or '').strip():
            bad.append('%s -- injection unknown with no reason. A bare unknown '
                       'is a silence, not a decision.' % r['commit'])
        # ── THE TOOL THAT FOUND IT, same rule as --add so a hand-edited
        # record cannot carry a shape --add would have refused.
        fbt = r.get('found_by_tool')
        if tool_required(r['detection_method']) and not str(fbt or '').strip():
            bad.append('%s -- found by an automated checker with no '
                       'found_by_tool' % r['commit'])
        if not tool_required(r['detection_method']) and str(fbt or '').strip():
            bad.append('%s -- carries found_by_tool %r but %s found it'
                       % (r['commit'], fbt, checkpoint_of(r['detection_method'])))
        # ── THE INJECTION PHASE, checked the same way and for the same reason ─
        ph = r.get('injection_phase')
        phc = r.get('phase_confidence')
        if ph not in PHASES:
            bad.append('%s -- injection_phase %r is outside %s'
                       % (r['commit'], ph, (PHASES,)))
        elif ph == 'unknown' and not str(r.get('phase_note') or '').strip():
            bad.append('%s -- injection_phase unknown with no note. A bare '
                       'unknown is a silence, not a decision.' % r['commit'])
        if phc not in PHASE_CONFIDENCES:
            bad.append('%s -- phase_confidence %r is outside %s'
                       % (r['commit'], phc, (PHASE_CONFIDENCES,)))
        # ── THE CITATION, checked the same way and for the same reason ──────
        conf = r.get('citation_confidence')
        rules = r.get('rules')
        if conf not in CONFIDENCES:
            bad.append('%s -- citation_confidence %r is outside %s'
                       % (r['commit'], conf, (CONFIDENCES,)))
        elif conf == 'not-citable':
            if rules:
                bad.append('%s -- not-citable but carries rules %r'
                           % (r['commit'], rules))
            if not str(r.get('citation_note') or '').strip():
                bad.append('%s -- not-citable with no note. A bare refusal to '
                           'cite is a silence, not a decision.' % r['commit'])
        else:
            if not rules:
                bad.append('%s -- %s citation with no rule' % (r['commit'], conf))
            if conf == 'arguable' and not str(r.get('citation_note') or '').strip():
                bad.append('%s -- arguable citation with no note saying what is '
                           'arguable about it' % r['commit'])
            if known is None:
                could_not_check += 1
            else:
                for rid in (rules or []):
                    if rid not in known:
                        bad.append('%s -- cites %r, which is not a section in %s'
                                   % (r['commit'], rid, RULES_DOC))
        # ── ITEM 75: THE CONTRIBUTING FACTORS, AND WHAT IS STILL OPEN ────
        if 'root_cause' in r:
            bad.append('%s -- carries a `root_cause` field. There is no single '
                       'root cause of a failure in a system like this, and a '
                       'field with that name asserts one: fix the named thing '
                       'and the record reads as closed while every other '
                       'contributor is still there. Use contributing_factors, '
                       'which is a list.' % r['commit'])
        cf = r.get('contributing_factors')
        if cf is not None:
            if not isinstance(cf, list) or not cf:
                bad.append('%s -- contributing_factors is present but not a '
                           'non-empty list' % r['commit'])
            else:
                for i, f in enumerate(cf):
                    where = '%s factor %d' % (r['commit'], i + 1)
                    if not isinstance(f, dict) or not str(f.get('factor') or '').strip():
                        bad.append('%s -- no factor text' % where)
                        continue
                    if f.get('kind') not in FACTOR_KINDS:
                        bad.append('%s -- kind %r is outside %s'
                                   % (where, f.get('kind'), (FACTOR_KINDS,)))
                    st = f.get('action_status')
                    if st not in ACTION_STATES:
                        bad.append('%s -- action_status %r is outside %s'
                                   % (where, st, (ACTION_STATES,)))
                    elif st in ('done', 'planned') and not str(f.get('action') or '').strip():
                        bad.append('%s -- action_status %r with no action. A '
                                   'status without the thing that was done is '
                                   'the CAPA box this field replaces.'
                                   % (where, st))
                    elif st in ('declined', 'not-actionable') and not str(
                            f.get('note') or '').strip():
                        bad.append('%s -- action_status %r with no note. '
                                   'Deciding not to act is a decision and gets '
                                   'written down.' % (where, st))
                # A SINGLE FACTOR IS ALLOWED AND MUST SAY WHY IT IS SINGLE.
                if len(cf) == 1 and not str(r.get('single_factor_note') or '').strip():
                    bad.append('%s -- one contributing factor and no '
                               'single_factor_note. One cause is a CLAIM about '
                               'a system, not the default shape of one, so it '
                               'is stated rather than assumed.' % r['commit'])
                # AND WHAT THE ACTIONS DO NOT CLOSE.
                if not str(r.get('recurrence_open') or '').strip():
                    bad.append('%s -- contributing factors with no '
                               'recurrence_open. A corrective action is '
                               'evidence about one contributor and never about '
                               'recurrence; without this the record reads as '
                               'closed.' % r['commit'])

    seen = set()
    for r in reg['records']:
        k = (r['commit'], r['summary'])
        if k in seen:
            bad.append('%s -- duplicate record' % r['commit'])
        seen.add(k)
    # REPORTED, NOT SILENT, AND NOT A FAILURE. A re-seated record is sound --
    # the commit is really there under a new hash -- but a reader deserves to
    # know the register's SHAs have drifted from `main`, and `--reseat` is one
    # command away. Saying nothing here would trade a false alarm for a silent
    # rot, which is the swap this repo keeps recording against itself.
    if reseat:
        print('RE-SEATABLE (%d): the SHA was rewritten by a rebase and the '
              'subject still resolves.' % len(reseat))
        for old, new, subj in reseat:
            print('    %s -> %s  %s' % (old, new, subj[:66]))
        print('    Not a failure. Run `python tools/defect_register.py '
              '--reseat` to write them back.')
    # ── ONE ENTITY, ONE SPELLING (2026-09-14) ──────────────────────────────
    # `SAIRNBIZ` and `sairnbiz` sat in this file as two apps, splitting one
    # entity in half. Nothing noticed, because every per-app figure simply
    # reported both. It surfaced while measuring whether there is enough data
    # for a PER-ENTITY baseline (item 51) -- where a silent split is not a
    # cosmetic problem, it halves the very count the baseline is computed from.
    seen_apps = {}
    for r in reg['records']:
        seen_apps.setdefault(str(r.get('app', '')).lower(), set()).add(r.get('app'))
    for low, spellings in sorted(seen_apps.items()):
        if len(spellings) > 1:
            bad.append('the app %r appears under %d spellings %s -- one entity '
                       'with two names is two entities to every per-app figure '
                       'in this file' % (low, len(spellings), sorted(spellings)))

    if bad:
        print('FAIL: %d register problem(s)' % len(bad))
        for b in bad:
            print('  ' + b)
        return 1
    if could_not_check:
        # PR 1.11, in this file's own output. The citations were NOT validated,
        # and saying "OK" here would be reporting a check that did not run.
        print('COULD NOT CHECK %d citation(s): %s is unreadable, so the rule '
              'vocabulary is unknown. This is not a pass.'
              % (could_not_check, RULES_DOC))
        return 2
    # ── ITEM 75 COVERAGE, PRINTED AND NOT ENFORCED ─────────────────────────
    # The field is new, so requiring it on all 77 records would mean
    # back-filling contributing factors for defects nobody is going to
    # re-investigate -- which is how a CAPA form fills up with guesses. The
    # count is printed so the gap is visible rather than absent.
    with_cf = [r for r in reg['records'] if r.get('contributing_factors')]
    n_factors = sum(len(r['contributing_factors']) for r in with_cf)
    print('    contributing factors: %d of %d record(s) carry them, %d factors '
          'in total (%.1f per record). NOT required -- back-filling a cause '
          'nobody re-investigated is how a CAPA form fills with guesses.'
          % (len(with_cf), len(reg['records']), n_factors,
             (n_factors / float(len(with_cf))) if with_cf else 0.0))
    cited = sum(1 for r in reg['records'] if r.get('rules'))
    print('OK: %d record(s), every commit resolves and every field is in '
          'vocabulary.%s' % (len(reg['records']),
                             ' %d by subject.' % len(reseat) if reseat else ''))
    print('    standing-rule citations: %d cited, %d deliberately not-citable, '
          'every id checked against %s'
          % (cited, len(reg['records']) - cited, RULES_DOC))
    return 0


def reseat_base():
    """The ref reachability is measured against, and its name for the report.

    origin/main when it exists -- that is what every other clone will fetch and
    what an auditor following a SHA will actually have. HEAD when it does not,
    which is the case in a fresh worktree or a clone with no remote.

    Returns (ref, None) or (None, why). A refusal rather than a default: with no
    ref to compare against, EVERY record would look unreachable and this would
    re-seat the whole register on the strength of not being able to look.
    """
    for ref in ('origin/main', 'HEAD'):
        if git('rev-parse', '--verify', ref):
            return ref, None
    return None, 'neither origin/main nor HEAD could be read'


def reachable(sha, base):
    """Is this commit an ancestor of `base`?

    ── RESOLVABLE IS NOT REACHABLE (2026-09-16) ─────────────────────────────
    `resolve()` calls a SHA good the moment `rev-parse --verify` accepts it, and
    that is the RIGHT contract for `--check`: a record pointing at a real object
    is not a register pointing at nothing.

    IT IS THE WRONG QUESTION FOR A RE-SEAT. A rebase rewrites a commit and
    leaves the original behind as a DANGLING object -- it still resolves, for as
    long as it takes the reflog to expire, so `--reseat` skipped it and the
    record went on naming a commit that is not on the branch. Found on
    2026-09-16 when the register-feed gate refused a push twice: it asks whether
    a commit BEING PUSHED has a record, the register asked whether a recorded
    SHA is a valid object, and four records satisfied the second while failing
    the first.

    With four clones rebasing onto one branch that is the normal case rather
    than an edge one, so the repair command now asks the question the repair is
    for. `--check`'s acceptance contract is deliberately unchanged.
    """
    # `git()` returns '' on success-with-no-output and None on a non-zero exit.
    # `merge-base --is-ancestor` prints NOTHING and signals through the exit
    # code alone, so the test is `is not None` -- `bool()` would read every
    # ancestor as not-an-ancestor, which is the inverted answer and would
    # re-seat the entire register.
    return git('merge-base', '--is-ancestor', sha, base) is not None


def cmd_reseat():
    """Write re-seated SHAs back. A separate command on purpose: `--check` is
    read-only, and a checker that edits the thing it checks is not a checker."""
    reg = load()
    idx = subject_index()
    base, why = reseat_base()
    if base is None:
        print('COULD NOT RE-SEAT: %s.' % why)
        print('  Nothing was written. With no ref to measure reachability')
        print('  against, every record would look unreachable and this would')
        print('  re-seat the whole register on the strength of not looking.')
        return 2
    print('reachability measured against %s' % base)
    n = 0
    for r in reg['records']:
        sha, how = resolve(r, idx)
        # A SHA THAT RESOLVES BUT IS NOT ON THE BRANCH is exactly the case a
        # re-seat exists for, and it was the one case this skipped.
        if how == 'sha' and not reachable(r['commit'], base):
            hits = idx.get(r.get('subject') or '\x00absent', [])
            if len(hits) == 1:
                sha, how = hits[0][:12], 'dangling'
            else:
                print('  %s  DANGLING and %s -- left alone'
                      % (r['commit'],
                         'AMBIGUOUS by subject' if hits else 'no subject match'))
                continue
        if how in ('subject', 'dangling'):
            print('  %s -> %s  %s%s'
                  % (r['commit'], sha, r['subject'][:58],
                     '   (was dangling)' if how == 'dangling' else ''))
            r['commit'] = sha
            n += 1
    if not n:
        print('nothing to re-seat -- every SHA resolves AND is reachable '
              'from %s.' % base)
        return 0
    # DELIBERATELY NOT RE-SORTED. The sort key is (date, commit), so re-seating
    # twelve SHAs reorders the file and produces a 157-line diff for a 12-line
    # change -- measured, not guessed, because the first version did sort and
    # that is what it produced. A repair nobody can review is a repair nobody
    # checks.
    #
    # THE KNOWN CONSEQUENCE, SAID RATHER THAN DISCOVERED LATER: the next
    # `--add` DOES sort, so it normalises the order this left behind and its
    # diff is correspondingly large. That is the right place for the churn --
    # an add is a deliberate content change somebody is already reviewing,
    # while a re-seat is a mechanical repair that must stay legible.
    save(reg)
    print('re-seated %d record(s).' % n)
    return 0


def cmd_report():
    reg = load()
    recs = reg['records']
    lines = app_lines()
    print('DEFECT REGISTER -- %d confirmed record(s) since %s'
          % (len(recs), reg.get('started', '?')))
    print('')
    print('BY LAYER')
    for L in LAYERS:
        n = len([r for r in recs if r['layer'] == L])
        print('  %-9s %d' % (L, n))
    print('')
    print('BY SEVERITY')
    for S in SEVERITIES:
        n = len([r for r in recs if r['severity'] == S])
        print('  %-9s %d' % (S, n))
    print('')
    print('BY DETECTION METHOD -- the column that matters')
    for M in METHODS:
        n = len([r for r in recs if r['detection_method'] == M])
        if n:
            print('  %-20s %d' % (M, n))
    print('')
    # ── WHICH CHECKPOINT CAUGHT IT (item 63) ───────────────────────────────
    known = [r for r in recs
             if isinstance(r.get('injection'), dict) and r['injection'].get('commit')
             and r['injection'].get('lag_days') is not None]
    print('DISCOVERY LAG -- injection to fix')
    print('  records with an injection commit : %d of %d' % (len(known), len(recs)))
    if not known:
        print('  NO LAG DISTRIBUTION EXISTS YET, so no IBNR reserve is offered.')
        print('  That is the honest state and not a missing feature -- see')
        print('  docs/2026-09-14-ibnr-scoping.md. Backfilling these by blame')
        print('  would build the distribution out of guesses.')
    else:
        lags = sorted(r['injection']['lag_days'] for r in known)
        mid = lags[len(lags) // 2]
        print('  lag in days: min %d, median %d, max %d' % (lags[0], mid, lags[-1]))
        print('  DO NOT QUOTE THIS AS A RESERVE. It is the lag of the defects')
        print('  that were FOUND; the ones still hiding are by definition absent')
        print('  from it, which is the whole reason IBNR needs a fitted tail')
        print('  rather than a median.')
    print('')
    print('WHICH CHECKPOINT CAUGHT IT')
    ck = {}
    for r in recs:
        k = checkpoint_of(r['detection_method'])
        ck[k] = ck.get(k, 0) + 1
    for k in CHECKPOINTS:
        if ck.get(k):
            print('  %-19s %3d   (%.0f%%)' % (k, ck[k], 100.0 * ck[k] / len(recs)))
    auto = [r for r in recs if checkpoint_of(r['detection_method']) == 'automated-checker']
    if auto:
        named = [r for r in auto
                 if str(r.get('found_by_tool') or '').strip()
                 and r['found_by_tool'] != TOOL_UNKNOWN]
        print('')
        print('  of the %d automated catches, the TOOL is named in %d'
              % (len(auto), len(named)))
        print('  BLOCKING vs REPORT-ONLY is the question behind this split, and')
        print('  it needs the tool classification -- run')
        print('  `python tools/tooling_inventory.py` and read the class column')
        print('  for the names below. It is deliberately NOT recomputed here: a')
        print('  second copy of that classification is a second thing to drift.')
        by = {}
        for r in named:
            by[r['found_by_tool']] = by.get(r['found_by_tool'], 0) + 1
        for t in sorted(by, key=lambda k: -by[k])[:10]:
            print('      %-38s %d' % (t, by[t]))
    print('')
    print('  THIS IS THE CHECKPOINT THAT DID CATCH EACH DEFECT, NOT THE ONE')
    print('  THAT SHOULD HAVE. Those differ exactly where a gate ought to exist')
    print('  and does not, so this UNDER-COUNTS gaps by construction.')
    print('  AND `monitoring` BEING %d IS A SELECTION EFFECT, NOT A RESULT: a'
          % ck.get('monitoring', 0))
    print('  defect nobody found is not in this register, so escape rate cannot')
    print('  be measured here at all.')
    print('')
    # ── INJECTION x REMOVAL (item 77) ──────────────────────────────────────
    # UNKNOWN AND INFERRED ARE PRINTED FIRST, ABOVE THE MATRIX, and that
    # ordering is the same decision fmea_prediction_check.py makes when it puts
    # NO DRAFT above the hit rate. A matrix read without them looks like
    # knowledge; read with them it is a matrix over the records somebody could
    # actually place, which is a different and smaller claim.
    unk = [r for r in recs if r.get('injection_phase') == 'unknown']
    inferred = [r for r in recs if r.get('phase_confidence') == 'inferred']
    print('WHERE DEFECTS WERE INJECTED -- read these two lines FIRST')
    print('  injection_phase = unknown       : %d of %d' % (len(unk), len(recs)))
    print('  phase called INFERRED, not stated: %d of %d   <- most of the '
          'matrix below rests on a judgement about a one-line summary, not on '
          'a quote from it' % (len(inferred), len(recs)))
    print('')
    print('BY INJECTION PHASE')
    for P in PHASES:
        n = len([r for r in recs if r.get('injection_phase') == P])
        if n:
            print('  %-12s %d' % (P, n))
    print('')
    print('INJECTION x REMOVAL -- the matrix the phase field exists for')
    used = [M for M in METHODS if any(r['detection_method'] == M for r in recs)]
    print('  %-12s %s' % ('', ' '.join('%-6s' % M[:6] for M in used)))
    for P in PHASES:
        row = [len([r for r in recs
                    if r.get('injection_phase') == P and r['detection_method'] == M])
               for M in used]
        if sum(row):
            print('  %-12s %s' % (P, ' '.join('%-6d' % n for n in row)))
    print('  DO NOT QUOTE A CELL ALONE. The columns are how a defect was '
          'FOUND, which is a fact about where people looked, not about where '
          'defects are.')
    print('')
    print('PRODUCT DEFECTS PER 1,000 LINES, against a MEASURED denominator')
    print('  %-22s %8s %8s %s' % ('app', 'lines', 'defects', 'per 1k'))
    prod = [r for r in recs if r['layer'] == 'product']
    for app in sorted(lines):
        n = len([r for r in prod if r['app'] == app])
        if not n:
            continue
        print('  %-22s %8d %8d %6.2f'
              % (app, lines[app], n, 1000.0 * n / max(1, lines[app])))
    # ── TWO FIGURES, NOT ONE (2026-09-13) ──────────────────────────────────
    # This printed a single ALL APPS rate: every product defect divided by
    # EVERY tracked app line, including the files nobody has ever swept. One
    # number was being asked to answer two different questions -- "how dense
    # are the defects where we have looked" and "how much have we looked at" --
    # and the second answer was silently folded into the first as a smaller
    # rate. A file with no records is a file nobody has swept, not a clean one;
    # the caveat below has always said so while the arithmetic said otherwise.
    #
    # The swept figure is the real signal. The unswept figure is a COUNT, and
    # deliberately not a rate: dividing by lines nobody has examined would be
    # the same mistake in the other direction.
    # ── AND THE NUMERATOR HAS TO MATCH THE DENOMINATOR ─────────────────────
    # Found by checking the first version of this very block: `len(prod)` counts
    # every product defect, INCLUDING those filed against app 'PLATFORM', which
    # is not a file and contributes no lines. The old ALL APPS rate divided
    # those by the whole-repo line count and the new swept rate divided them by
    # the swept subset -- both dividing a defect by lines it does not live in.
    # The caveat below has said "registered but not divided by anything" since
    # this tool shipped while the arithmetic did exactly that.
    #
    # They get their own line, with no rate, for the same reason the unswept
    # files do: a count with no honest denominator is reported as a count.
    swept = sorted(a for a in lines if any(r['app'] == a for r in prod))
    unswept = sorted(a for a in lines if a not in swept)
    swept_lines = sum(lines[a] for a in swept)
    unswept_lines = sum(lines[a] for a in unswept)
    in_files = [r for r in prod if r['app'] in lines]
    no_denom = [r for r in prod if r['app'] not in lines]
    print('  %-22s %8d %8d %6.2f   <- SWEPT: the real signal'
          % ('SWEPT FILES (%d)' % len(swept), swept_lines, len(in_files),
             1000.0 * len(in_files) / max(1, swept_lines)))
    print('  %-22s %8d %8s %6s   <- UNMEASURED, not a rate'
          % ('UNSWEPT FILES (%d)' % len(unswept), unswept_lines, '--', '--'))
    if unswept:
        print('     %s' % ', '.join(unswept))
    if no_denom:
        print('  %-22s %8s %8d %6s   <- NO DENOMINATOR: not app HTML'
              % ('OFF-FILE (%s)' % ', '.join(sorted({r['app'] for r in no_denom})),
                 '--', len(no_denom), '--'))
    print('')
    print('COVERAGE -- which methods have found something in which app')
    apps = sorted({r['app'] for r in recs})
    for app in apps:
        ms = sorted({r['detection_method'] for r in recs if r['app'] == app})
        print('  %-22s %s' % (app, ', '.join(ms)))
    print('')
    print('READ THIS BEFORE QUOTING ANY NUMBER ABOVE.')
    print('  * A density is a fact about what has been LOOKED AT, not about')
    print('    what is there. An app with no records is an app nobody has')
    print('    swept, not a clean one.')
    print('  * WHICH IS WHY THERE ARE TWO FIGURES AND NOT ONE. The swept rate')
    print('    is the signal; the unswept line count is coverage owed, stated')
    print('    as a COUNT because dividing by lines nobody has examined would')
    print('    manufacture a reassuring rate out of an absence of work.')
    print('  * FIVE OF THE FILES COUNTED ARE SATELLITE PAGES, not apps --')
    print('    stonedesk-hr, stonedesk-intake, stonedesk-catalog,')
    print('    sairndental-book, sairndental-complaint. 2,647 lines, ~2%% of')
    print('    the denominator. Real files, really unswept; named so the')
    print('    unswept count is not read as five whole applications.')
    print('  * The honest signal is CONSECUTIVE ZERO-NEW-FINDING SWEEPS BY')
    print('    DIFFERENT METHODS over the same files. One method returning')
    print('    zero means that method is exhausted. On 2026-09-10 the mutation')
    print('    controls found two defects in test code that reading the')
    print('    assertions had not, on the same files in the same hour.')
    print('  * The denominator counts LINES OF APP HTML. It does not count')
    print('    api/, sql/ or tools/, so a product defect in an endpoint is')
    print('    registered but not divided by anything. That is a known')
    print('    limitation, not an oversight.')
    return 0


def main(argv):
    if '--add' in argv:
        return cmd_add(argv)
    if '--check' in argv:
        return cmd_check(argv)
    if '--reseat' in argv:
        return cmd_reseat()
    return cmd_report()


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
