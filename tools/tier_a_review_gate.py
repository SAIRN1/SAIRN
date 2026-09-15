"""The independent-review rule on Tier A code, as a gate rather than a habit.

    python tools/tier_a_review_gate.py                 # check the working tree
    python tools/tier_a_review_gate.py --diff-range A..B   # check a commit range
    python tools/tier_a_review_gate.py --open "why"    # record this session's obligation
    python tools/tier_a_review_gate.py --list          # what is open, and whose

Exit 0 clean, 1 a finding, 2 COULD NOT TELL -- never folded into either of the
other two (PR 1.11).

── WHY THIS EXISTS ─────────────────────────────────────────────────────────────
The rule has been real and unenforced the whole time. docs/SAIRN-OPEN-WORK-INDEX
.md carries it in prose on the rows somebody happened to remember --
"⚠ Independent review, per the standing rule that the session which wrote the
code shares its own blind spot", "the reviewer should be someone else" -- and
nothing anywhere checks it. Of the 77 records in the defect register, 7 name
`independent-review` as the detection method, so the practice works when it
happens. Nothing made it happen.

A rule enforced by remembering is enforced on the days people remember, which
are not the days it matters.

── WHAT IT CAN AND CANNOT DO, SAID PLAINLY ────────────────────────────────────
IT CANNOT read a review, judge one, or know whether the reviewer looked. Any
gate claiming otherwise would be lying about its own reach.

WHAT IT CAN DO is exactly two things, and they are the two failures this
platform has actually had:

  1. A Tier A change reaching origin with the obligation never recorded, so
     nobody downstream can tell a reviewed change from an unreviewed one.
  2. A record signed by its own author. "I reviewed my own work" is the one
     claim the rule exists to refuse, and it is mechanically checkable.

── HOW "TOUCHES TIER A CODE" IS DECIDED, and the first version was useless ────
It reads the DIFF, not the file. A Tier A resource counts as touched when its
name appears in the changed hunks -- added lines, removed lines, or the three
lines of context around them. The names come from docs/CRITICALITY-TIERS.md,
the register the tier decision already lives in, and never from a second copy.

THE OBVIOUS IMPLEMENTATION WAS WRITTEN FIRST AND MEASURED, and it is worth
recording because it read as correct: "a changed file counts if its CONTENT
names a Tier A resource." Run against the working tree it reported **78 Tier A
resources touched**, because api/sd-data.js contains every resource name on the
platform. A gate that answers "you touched everything" on every push says
nothing and would have been switched off inside a week. At hunk granularity the
same commit reports the seven sc_* resources it actually changed.

Comments count as naming a resource, deliberately: a hunk that discusses
sc_claims was edited by somebody thinking about sc_claims.

THE FALSE-POSITIVE DIRECTION IS STILL THE SAFE ONE -- an over-inclusive answer
costs one register entry, an under-inclusive one is a Tier A change that slips
through looking clean. What changed is that the answer is now specific enough to
act on.

TWO EXCLUSIONS, both narrow and both named rather than silent:
  * docs/ and sql/ -- a document or a migration naming a resource is not code
    serving it, and CRITICALITY-TIERS.md names every Tier A resource by
    definition, so including docs/ would make every push a Tier A push and the
    gate would mean nothing within a week.
  * this file, the register it reads, and the gate that calls it -- otherwise
    recording an obligation is itself a Tier A change requiring an obligation.
"""
import io
import json
import os
import re
import subprocess
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER = os.path.join(REPO, 'docs', 'CRITICALITY-TIERS.md')
REVIEWS = os.path.join(REPO, 'docs', 'tier-a-reviews.json')

# Files that can never themselves create an obligation. Kept tiny and explicit;
# a growing exclusion list is how a gate stops covering anything.
SELF = (
    'docs/tier-a-reviews.json',
    'tools/tier_a_review_gate.py',
    'tools/sairn_push_gate_hook.py',
    'tests/run_tier_a_review_gate_probe.py',
)


class CouldNotTell(Exception):
    pass


def session_name():
    """The clone directory, which is how the four sessions are distinguished
    everywhere else on this platform (SAIRN-ACTIVE-WORK-<name>.md). Imported in
    spirit from tools/sairn_claim.py rather than invented -- two different
    answers to "who am I" would make the self-review check meaningless."""
    base = os.path.basename(REPO)
    m = re.match(r'^SAIRN-(.+)$', base, re.I)
    return (m.group(1) if m else base).lower()


def tier_a_resources():
    """Read from the register. FAILS CLOSED: a register that cannot be parsed,
    or that yields no Tier A rows, is COULD NOT TELL and never an empty set --
    an empty set would make every push clean, which is the quietest possible
    way for this gate to stop working."""
    try:
        text = io.open(REGISTER, encoding='utf-8').read()
    except OSError as e:
        raise CouldNotTell('docs/CRITICALITY-TIERS.md could not be read: %s' % e)
    names = set()
    for line in text.split('\n'):
        m = re.match(r'^\|\s*`([a-z0-9_]+)`\s*\|\s*\*\*A\*\*\s*\|', line)
        if m:
            names.add(m.group(1))
    if not names:
        raise CouldNotTell(
            'docs/CRITICALITY-TIERS.md yielded ZERO Tier A rows. That is either '
            'a parse failure or a register that has lost its table; both mean '
            'this gate cannot answer, and an empty set would silently pass '
            'every push.')
    return names


def load_reviews():
    try:
        data = json.load(io.open(REVIEWS, encoding='utf-8'))
    except OSError as e:
        raise CouldNotTell('docs/tier-a-reviews.json could not be read: %s' % e)
    except ValueError as e:
        raise CouldNotTell('docs/tier-a-reviews.json is not valid JSON: %s' % e)
    if not isinstance(data, dict) or not isinstance(data.get('records'), list):
        raise CouldNotTell('docs/tier-a-reviews.json has no `records` list')
    return data


def save_reviews(data):
    io.open(REVIEWS, 'w', encoding='utf-8', newline='\n').write(
        json.dumps(data, indent=2, ensure_ascii=False) + '\n')


def git(*args):
    r = subprocess.run(['git'] + list(args), cwd=REPO,
                       capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ''


def touched_tier_a(diff_text, resources):
    """resource -> [files whose CHANGED HUNKS name it].

    Walks a unified diff and attributes every hunk line to the file its header
    named. Only hunk bodies are scanned -- the rest of the file is not part of
    this change, and reading it is what made the first version of this report
    78 resources for a one-line edit to api/sd-data.js.
    """
    hits = {}
    cur = None
    skip = False
    for line in diff_text.split('\n'):
        if line.startswith('+++ '):
            path = line[4:].strip()
            if path == '/dev/null':
                cur, skip = None, True
                continue
            cur = (path[2:] if path[:2] in ('a/', 'b/') else path).replace('\\', '/')
            # docs/ and sql/ are excluded by design: a document or a migration
            # naming a resource is not code serving it, and CRITICALITY-TIERS.md
            # names every Tier A resource by definition, so including docs/ would
            # make every push a Tier A push and the gate would mean nothing.
            #
            # ── AND ANY .md ANYWHERE, ADDED 2026-09-15 ──────────────────────
            # This gate refused a push whose only Tier-A-naming file was
            # `SAIRN-ACTIVE-WORK-fourth.md` -- a WORKLOG, describing dnt_rollup
            # and dnt_patients in prose. The reasoning three lines above already
            # covers that case exactly: a document naming a resource is not code
            # serving it. It was missed only because the rule was keyed on the
            # `docs/` PREFIX rather than on what the file IS, and every session's
            # worklog lives at the repo root by convention.
            #
            # THIS SHRINKS THE RULE RATHER THAN GROWING THE LIST, which matters
            # because this file's own header warns that "a growing exclusion list
            # is how a gate stops covering anything". One principled predicate --
            # markdown is prose, never a request handler -- replaces what would
            # otherwise be four root-level filenames plus the next one somebody
            # adds. It cannot under-cover: no `.md` file has ever served a
            # resource at runtime on this platform.
            skip = (cur in SELF
                    or cur.startswith('docs/')
                    or cur.startswith('sql/')
                    or cur.lower().endswith('.md'))
            continue
        if cur is None or skip:
            continue
        if line.startswith('diff --git') or line.startswith('--- '):
            continue
        if not (line[:1] in ('+', '-', ' ') or line.startswith('@@')):
            continue
        for name in resources:
            # Word-bounded. `sc_ar` must not match `sc_archive`, and this
            # platform has already been bitten once by a substring search --
            # `esign` matching 47 occurrences of `design`.
            if re.search(r'(?<![a-z0-9_])' + re.escape(name) + r'(?![a-z0-9_])', line):
                fs = hits.setdefault(name, [])
                if cur not in fs:
                    fs.append(cur)
    return hits


def working_diff():
    """Everything not yet in HEAD, staged or not. -U3 rather than -U0 because a
    resource name three lines from an edit is what the edit was about."""
    return git('diff', '-U3', 'HEAD') + '\n' + git('diff', '-U3', '--cached', 'HEAD')


def range_diff(base, tip):
    return git('diff', '-U3', base, tip)


def open_records(data, session=None):
    out = []
    for r in data['records']:
        if r.get('status') != 'open':
            continue
        if session is not None and r.get('author_session') != session:
            continue
        out.append(r)
    return out


def self_signed(data):
    """A record whose reviewer is its own author. The one claim the rule exists
    to refuse, and the only part of a review a machine can check."""
    bad = []
    for r in data['records']:
        rev = r.get('reviewer_session')
        if rev and rev == r.get('author_session'):
            bad.append(r)
    return bad


def check(diff_text, verbose=True):
    """Returns (exit_code, lines)."""
    lines = []
    try:
        resources = tier_a_resources()
        data = load_reviews()
    except CouldNotTell as e:
        return 2, ['COULD NOT TELL -- this is NOT a pass:', '  ' + str(e)]

    # 1. SELF-SIGNED RECORDS. Checked first and on EVERY run, not only when the
    #    push touches Tier A code: a self-signed record already in the file is a
    #    finding whatever this particular push contains.
    bad = self_signed(data)
    if bad:
        lines.append('SELF-SIGNED REVIEW -- a session recorded itself as the reviewer '
                     'of its own change. That is the one claim this rule exists to refuse:')
        for r in bad:
            lines.append('  %s reviewed by %s  (%s)'
                         % (r.get('author_session'), r.get('reviewer_session'),
                            ', '.join(r.get('resources') or []) or 'no resources listed'))
        return 1, lines

    hits = touched_tier_a(diff_text, resources)
    if not hits:
        if verbose:
            lines.append('No file in this change names a Tier A resource. '
                         'Nothing to record.')
        return 0, lines

    session = session_name()
    covering = [r for r in open_records(data, session)
                if set(hits) & set(r.get('resources') or [])]
    if covering:
        if verbose:
            lines.append('Tier A code changed: %s' % ', '.join(sorted(hits)))
            lines.append('An OPEN review obligation covers it (%s, opened %s). '
                         'Recording it is this session\'s job; discharging it is '
                         'somebody else\'s.'
                         % (session, covering[0].get('opened_at', '?')))
        return 0, lines

    lines.append('TIER A CODE CHANGED WITH NO RECORDED REVIEW OBLIGATION.')
    lines.append('')
    for name in sorted(hits):
        lines.append('  %-22s %s' % (name, ', '.join(sorted(set(hits[name])))[:110]))
    lines.append('')
    lines.append('The standing rule is that a Tier A change is reviewed by a session')
    lines.append('OTHER than the one that wrote it -- the author shares the blind spot')
    lines.append('that produced the code. Until now that rule lived in prose on')
    lines.append('whichever open-work rows somebody remembered to annotate.')
    lines.append('')
    lines.append('THIS DOES NOT ASK YOU TO GET REVIEWED BEFORE PUSHING. It asks you to')
    lines.append('RECORD that the obligation exists, so the next session can see an')
    lines.append('unreviewed Tier A change instead of having to guess:')
    lines.append('')
    lines.append('    python tools/tier_a_review_gate.py --open "what you changed and why"')
    lines.append('')
    lines.append('Another session discharges it later; this gate refuses any record')
    lines.append('whose reviewer is its own author.')
    return 1, lines


def cmd_open(why):
    resources = tier_a_resources()
    text = working_diff()
    base = git('merge-base', 'origin/main', 'HEAD').strip()
    if base:
        # Unpushed commits count. The obligation is about the work being SENT,
        # not only about whatever happens to be uncommitted when --open runs.
        text += '\n' + range_diff(base, 'HEAD')
    hits = touched_tier_a(text, resources)
    if not hits:
        sys.stderr.write('Nothing in this change names a Tier A resource, so there '
                         'is no obligation to record. If you believe there is, say '
                         'which resource and why -- an entry naming no resource '
                         'cannot be discharged by anybody.\n')
        return 1
    data = load_reviews()
    rec = {
        'author_session': session_name(),
        'opened_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'resources': sorted(hits),
        'files': sorted(set(f for fs in hits.values() for f in fs)),
        'what': why,
        'status': 'open',
        'reviewer_session': None,
        'reviewed_at': None,
        'verdict': None,
    }
    data['records'].append(rec)
    save_reviews(data)
    print('RECORDED -- %s owes an independent review on: %s'
          % (rec['author_session'], ', '.join(rec['resources'])))
    print('Commit docs/tier-a-reviews.json with the change it covers.')
    return 0


def cmd_list():
    try:
        data = load_reviews()
    except CouldNotTell as e:
        sys.stderr.write(str(e) + '\n')
        return 2
    rows = open_records(data)
    if not rows:
        print('No open Tier A review obligations.')
        return 0
    print('%d open Tier A review obligation(s):' % len(rows))
    for r in rows:
        print('  %-8s %s  %s' % (r.get('author_session'), r.get('opened_at'),
                                 ', '.join(r.get('resources') or [])))
        print('           %s' % (r.get('what') or '')[:110])
    return 0


def main(argv):
    if '--open' in argv:
        i = argv.index('--open')
        why = argv[i + 1] if len(argv) > i + 1 else ''
        if not why.strip():
            sys.stderr.write('--open needs a sentence saying what changed. An entry '
                             'nobody can read is not a record.\n')
            return 1
        try:
            return cmd_open(why.strip())
        except CouldNotTell as e:
            sys.stderr.write('COULD NOT TELL: %s\n' % e)
            return 2
    if '--list' in argv:
        return cmd_list()
    if '--diff-range' in argv:
        rng = argv[argv.index('--diff-range') + 1]
        base, _, tip = rng.partition('..')
        text = range_diff(base, tip or 'HEAD')
    elif '--stdin-diff' in argv:
        text = sys.stdin.read()
    else:
        text = working_diff()
    code, lines = check(text)
    out = sys.stderr if code else sys.stdout
    for ln in lines:
        out.write(ln + '\n')
    return code


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
