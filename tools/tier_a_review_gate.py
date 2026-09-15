"""The independent-review rule on Tier A code, as a gate rather than a habit.

    python tools/tier_a_review_gate.py                 # check the working tree
    python tools/tier_a_review_gate.py --diff-range A..B   # check a commit range
    python tools/tier_a_review_gate.py --open "why"    # record this session's obligation
    python tools/tier_a_review_gate.py --list          # what is open, and whose
    python tools/tier_a_review_gate.py --discharge <author> "<verdict>"

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

THE EXCLUSIONS, each narrow, each a predicate about what a file IS rather than a
filename somebody has to remember to add, and each named here rather than left
silent. Deliberately not counted: this list has grown twice and a number in
prose would be wrong the third time.

  * a REPORT-ONLY REVIEW ARTEFACT -- see is_report_only_artefact(), which also
    records why this is NOT "exclude tests/". A file that cannot fail cannot be
    a guard, so changing it cannot weaken one; and a review of a Tier A module
    necessarily names that module, so refusing it blocks the artefact that
    discharges the obligation being demanded.
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
    """Run git and return its stdout as text, or raise CouldNotTell.

    ── ENCODING IS EXPLICIT, AND THIS IS A REAL DEFECT THAT WAS HERE (2026-09-15).
    # `text=True` alone decodes with the LOCALE default, which is cp1252 on this
    platform -- and this repo's diffs are full of box-drawing characters and
    em-dashes. Two clones hit this within an hour of each other and diagnosed the
    symptom DIFFERENTLY, which is worth keeping: one saw stdout come back
    TRUNCATED, the other saw the decode raise on the subprocess reader THREAD and
    leave `r.stdout` as None, which then crashed `.split('\\n')`. Both are the
    same cause and both are fixed by naming the codec.

    ── AND THE RETURN LINE FAILED OPEN, WHICH THE ENCODING FIX DID NOT CLOSE ──
    `return r.stdout if r.returncode == 0 else ''` collapses THREE outcomes into
    two: a real empty diff and a git command that FAILED both became `''`. An
    empty diff means NO TIER A RESOURCE WAS TOUCHED, which is a PASS. So any git
    failure produced a clean push, in a BLOCKING gate, on the check whose entire
    subject is somebody not being told (PR 1.11).

    That is the half worth the extra lines. The crash was the loud version of a
    failure mode that was otherwise completely silent, and fixing only the
    encoding converts a visible crash into an invisible pass.

    `errors='replace'` rather than `'strict'`: a lone undecodable byte must not
    take a blocking gate down, and a replacement character cannot create or hide
    a resource NAME, which is the only thing the caller looks for.
    """
    try:
        r = subprocess.run(['git'] + list(args), cwd=REPO, capture_output=True,
                           encoding='utf-8', errors='replace')
    except Exception as e:                      # noqa: BLE001 -- any launch failure
        raise CouldNotTell('could not run `git %s`: %r' % (' '.join(args), e))
    if r.returncode != 0:
        raise CouldNotTell('`git %s` exited %d: %s'
                           % (' '.join(args), r.returncode,
                              (r.stderr or '').strip()[:200]))
    if r.stdout is None:
        raise CouldNotTell('`git %s` produced no readable output' % ' '.join(args))
    return r.stdout


def _strip_code_noise(text, lang):
    """Comments and string literals blanked, so a predicate about CODE is not
    answered by PROSE. Written char-by-char rather than with regexes because the
    regex version of exactly this has already shipped a defect on this platform
    -- a literal backspace inside a heredoc'd `\\b` -- and because a string
    containing a comment marker breaks the regex version silently."""
    out = []
    i, n = 0, len(text)
    in_s = None          # the quote character currently open, or None
    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ''
        if in_s:
            if c == '\\':
                i += 2
                continue
            if c == in_s:
                in_s = None
            out.append(' ')
            i += 1
            continue
        if lang == 'js' and c == '/' and nxt == '*':
            j = text.find('*/', i + 2)
            i = n if j == -1 else j + 2
            continue
        if lang == 'js' and c == '/' and nxt == '/':
            j = text.find('\n', i)
            i = n if j == -1 else j
            continue
        if lang == 'py' and c == '#':
            j = text.find('\n', i)
            i = n if j == -1 else j
            continue
        if c in ('"', "'", '`'):
            in_s = c
            out.append(' ')
            i += 1
            continue
        out.append(c)
        i += 1
    return ''.join(out)


def is_report_only_artefact(path, content):
    """Is this a REVIEW ARTEFACT rather than code that serves a resource?

    ── WHY THIS PREDICATE EXISTS (2026-09-15) ──────────────────────────────
    Second recorded false positive of the same shape. The first was a WORKLOG
    (`SAIRN-ACTIVE-WORK-fourth.md`), fixed by excluding markdown. The second was
    `tests/dnt_rollup_review_probe.js` -- an independent review of somebody
    else's Tier A module, report-only by design, which the gate refused because
    a review of dnt_rollup necessarily NAMES dnt_rollup.

    A review artefact that serves nothing cannot be reviewed for correctness;
    there is no behaviour in it to review. Refusing it does not protect
    anything, and the failure is self-perpetuating: the gate blocks the very
    artefact that discharges the obligation it is asking for.

    ── WHY THIS IS NOT "EXCLUDE tests/" ────────────────────────────────────
    That would be the dangerous direction and it is worth being explicit. A
    test is often the ONLY thing pinning a Tier A behaviour, and weakening one
    is exactly the blind-spot case the review rule exists for. Excluding
    `tests/` wholesale would let a session delete assertions from a Tier A suite
    and push it as clean.

    ── THE PREDICATE, AND WHY IT IS THIS ONE ───────────────────────────────
    A file that CANNOT FAIL cannot be a guard, so changing it cannot weaken
    one. Three conditions, all required:

      1. it lives under `tests/` -- not beside a handler in `api/`;
      2. with comments and strings stripped, it makes NO assertion;
      3. with comments and strings stripped, every exit it takes is the literal
         0 -- so no input can make it report a failure.

    Condition 3 is the load-bearing one and it is deliberately strict.
    `tests/failsafe/countersign_coverage_probe.py` is report-only in intent but
    ends `sys.exit(main())`, whose value is not visibly constant -- so it is NOT
    excluded by this and would still raise an obligation. That is the safe
    direction, it is a known consequence rather than an oversight, and the fix
    if it ever matters is for that file to exit a literal.

    THE EXCLUSION SHRINKS THE RULE RATHER THAN GROWING A LIST, which this
    file's own header warns about: one predicate about what a file IS, not a
    filename somebody has to remember to add.
    """
    p = path.replace('\\', '/')
    if not p.startswith('tests/'):
        return False
    lang = 'py' if p.endswith('.py') else ('js' if p.endswith('.js') else None)
    if lang is None:
        return False
    code = _strip_code_noise(content, lang)
    # 2. no assertion of any kind.
    if re.search(r'(?<![A-Za-z0-9_])assert(?![A-Za-z0-9_])', code):
        return False
    # 3. every exit is a literal zero, and there is at least one -- a file with
    #    no exit at all is not evidence of anything and is left to the gate.
    exits = re.findall(r'(?:process|sys)\s*\.\s*exit\s*\(([^)]*)\)', code)
    if not exits:
        return False
    return all(a.strip() == '0' for a in exits)


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
            # ── AND A REPORT-ONLY REVIEW ARTEFACT, ADDED 2026-09-15 ────────
            # Second false positive of this shape, after the worklog above.
            # `tests/dnt_rollup_review_probe.js` is an independent review of
            # somebody else's Tier A module and was refused because a review of
            # dnt_rollup necessarily names dnt_rollup. See
            # is_report_only_artefact() for the predicate and, more importantly,
            # for why this is NOT "exclude tests/", which would let a session
            # delete assertions from a Tier A suite and push it as clean.
            #
            # READ FROM THE WORKING TREE, not from the diff: the question is
            # what the file IS after this change, and the diff carries only the
            # hunks. A file deleted by this change is not on disk and is not
            # excluded, which is correct -- deleting a guard is a change worth
            # reviewing.
            skip = (cur in SELF
                    or cur.startswith('docs/')
                    or cur.startswith('sql/')
                    or cur.lower().endswith('.md'))
            if not skip and cur.replace('\\', '/').startswith('tests/'):
                try:
                    body = io.open(os.path.join(REPO, cur), encoding='utf-8',
                                   errors='replace').read()
                except OSError:
                    body = None
                if body is not None and is_report_only_artefact(cur, body):
                    skip = True
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


def _discharge(records, author, verdict, session):
    """Shared by both discharge paths so the self-review refusal cannot be true
    on one and forgotten on the other."""
    rec = records[0]
    rec['status'] = 'reviewed'
    rec['reviewer_session'] = session
    rec['reviewed_at'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    rec['verdict'] = verdict.strip()
    print('DISCHARGED -- %s reviewed the obligation %s opened %s, on %s'
          % (session, author, rec.get('opened_at'), ', '.join(rec['resources'])))


def cmd_discharge(author, verdict, opened_at=None):
    """Close somebody ELSE'S obligation.

    ── IT DID NOT EXIST FOR THE FIRST TWO HOURS, AND THAT WAS A REAL DEFECT ────
    The gate shipped with --open and --list and NO WAY TO CLOSE. Within the hour
    Hank did the review -- ce7764fa, two real findings against Fourth's
    dnt_rollup work, citing the obligation by name -- and the record still said
    `open`, because there was nothing to run. The reviewer had done the harder
    half and the register could not show it. A list of obligations that only
    ever grows is one people stop reading.

    THE SELF-REVIEW REFUSAL IS ENFORCED HERE, AT WRITE TIME, and not only by the
    check that reads the file afterwards. Refusing to WRITE a self-signed record
    and refusing to PASS one are different controls: with only the second, the
    file can hold the claim until somebody notices. Both now.
    """
    session = session_name()
    if session == author:
        sys.stderr.write(
            'REFUSED: %s cannot discharge an obligation authored by %s. The rule '
            'is that a Tier A change is reviewed by a session OTHER than the one '
            'that wrote it, because the author shares the blind spot that '
            'produced the code. That is the one thing this gate exists to '
            'refuse.\n' % (session, author))
        return 1
    if not verdict.strip():
        sys.stderr.write('--discharge needs a verdict sentence. "reviewed" with '
                         'no content is a tick, not a review.\n')
        return 1
    data = load_reviews()
    hit = open_records(data, author)
    if opened_at:
        hit = [r for r in hit if r.get('opened_at') == opened_at]
    if not hit:
        sys.stderr.write('No OPEN obligation authored by %r%s. `--list` shows '
                         'what is open and whose.\n'
                         % (author, (' opened at %r' % opened_at) if opened_at else ''))
        return 1
    if len(hit) > 1:
        # REFUSES TO GUESS. Two obligations by one author are two different
        # reviews, and closing the wrong one would record a review of work
        # nobody looked at -- which is worse than leaving both open.
        sys.stderr.write('%r has %d open obligations and this closes ONE. '
                         'Refusing to guess which:\n' % (author, len(hit)))
        for r in hit:
            sys.stderr.write('  %s  %s\n'
                             % (r.get('opened_at'), ', '.join(r.get('resources') or [])))
        sys.stderr.write('Pass the opened_at as the second argument to pick one.\n')
        return 1
    _discharge(hit, author, verdict, session)
    save_reviews(data)
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
    if '--discharge' in argv:
        rest = argv[argv.index('--discharge') + 1:]
        if len(rest) >= 3 and re.match(r'^\d{4}-\d{2}-\d{2}T', rest[1]):
            return cmd_discharge(rest[0], ' '.join(rest[2:]), opened_at=rest[1])
        if len(rest) >= 2:
            return cmd_discharge(rest[0], ' '.join(rest[1:]))
        sys.stderr.write('--discharge <author-session> [opened_at] <verdict '
                         'sentence>\n')
        return 1
    if '--list' in argv:
        return cmd_list()
    # READING THE DIFF CAN FAIL, AND THAT IS A THIRD ANSWER. It used to be a
    # silent empty string, which this gate reads as "no Tier A resource touched"
    # -- a pass. Exit 2 keeps could-not-tell separate from both a finding and a
    # clean run, the same way check() has always treated an unreadable register.
    try:
        if '--diff-range' in argv:
            rng = argv[argv.index('--diff-range') + 1]
            base, _, tip = rng.partition('..')
            text = range_diff(base, tip or 'HEAD')
        elif '--stdin-diff' in argv:
            text = sys.stdin.read()
        else:
            text = working_diff()
    except CouldNotTell as e:
        sys.stderr.write('COULD NOT TELL -- the diff could not be read, so NOTHING '
                         'WAS CHECKED. This is NOT a pass:\n  %s\n' % e)
        return 2
    code, lines = check(text)
    out = sys.stderr if code else sys.stdout
    for ln in lines:
        out.write(ln + '\n')
    return code


def _guarded(argv):
    """An unexpected exception must NOT leave here as exit 1.

    ── THE HALF THE ENCODING FIX DID NOT REACH, AND THE WORSE HALF ─────────────
    tools/sairn_push_gate_hook.py maps this tool's exit codes:

        returncode == 1  ->  deny("this push changes code serving a Tier A
                                   resource and no independent-review
                                   obligation is recorded for it")
        returncode == 2  ->  "COULD NOT TELL -- this is NOT a pass"

    An uncaught Python exception ALSO exits 1. So when the decode defect above
    crashed this tool on a real push, the hook did not report a crash -- IT MADE
    A SPECIFIC, CREDIBLE, FALSE ACCUSATION, naming a review obligation that did
    not exist for a change touching no Tier A resource. Re-running the identical
    range against the fixed tool returns "No file in this change names a Tier A
    resource", exit 0. Verified by running the PRE-FIX file from a scratch copy
    against that same range: AttributeError, exit 1.

    A gate that cries wolf in the vocabulary of a genuine finding is worse than
    one that crashes visibly: a crash gets fixed, a false finding gets believed
    and worked around. Every unexpected exception now becomes exit 2, which the
    hook already treats as not-a-pass WITHOUT inventing a reason.

    The FINDING path still exits 1. Nothing about what this gate refuses has
    changed -- only what it is allowed to claim when it does not know.
    """
    try:
        return main(argv)
    except SystemExit:
        raise
    except Exception as e:                      # noqa: BLE001 -- deliberate
        import traceback
        sys.stderr.write(
            'COULD NOT TELL -- the Tier A review gate raised an unexpected '
            'exception, so NOTHING WAS CHECKED. This is NOT a pass, and it is '
            'NOT a finding either:\n  %s: %s\n' % (type(e).__name__, e))
        traceback.print_exc(file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(_guarded(sys.argv[1:]))
