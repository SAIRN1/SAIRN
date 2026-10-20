#!/usr/bin/env python
# OWNER: cc
# written 2026-10-19, batch b24 item 5
"""Is this push inside the pushing population's declared scope?

    python tools/sairn_path_manifest.py --check <path> [<path> ...]
    python tools/sairn_path_manifest.py --check --agent cody <path> ...
    python tools/sairn_path_manifest.py --outgoing        # what this push ships
    python tools/sairn_path_manifest.py --fixtures        # the criteria lock

Exit 0 every path in scope, 1 at least one out of scope, 2 COULD NOT RUN.

── THE CONCEPT, IN ONE LINE ────────────────────────────────────────────────
A push is refused inside the clone when any path it ships falls outside the
pushing population's declared ownership, with the ownership read from one
COMMITTED MANIFEST rather than from a rule written into the hook.

── WHY THE MANIFEST IS DATA AND THIS FILE IS ONLY MECHANISM ────────────────
An ownership rule written into a hook is invisible to everybody who is not
reading Python, and it cannot be reviewed by the people it governs. The split
lives in docs/sairn-path-manifest.json, which is a committed file with its own
reasons in it; this module classifies against it and says which rule decided.

── WHAT IT IS AND WHAT IT HONESTLY IS NOT ──────────────────────────────────
It runs in the PUSHING clone. It cannot stop a push from a clone that does not
run it, it cannot stop a write made directly on the remote, and it is NOT a
security boundary -- anyone who can push can also edit the manifest. What it
closes is DRIFT AND ACCIDENT: a session editing another population's file
without noticing, which has happened in both directions on this platform.
Stated here because a mechanism described as stronger than it is gets cited as
proof of something it never checked.

── IT FAILS CLOSED ON ITS OWN INPUTS (PR 1.11) ─────────────────────────────
An unreadable or malformed manifest is exit 2 COULD NOT RUN, never a pass: a
scope check that cannot read the scope has not checked anything. An
unestablished identity is also exit 2 -- the question "is this path mine" has
no answer when "who am I" has none, and answering it as yes would make the
whole check a formality.

── `--history` WAS REMOVED, AND THAT IS A DECISION WITH A MEASUREMENT ──────
THE CONCEPT, IN ONE LINE: a mode that cannot attribute must not attribute, so
the per-population table is gone rather than reframed, and the knowledge that
produced it is kept here.

It existed to answer a fair question -- "a scope rule nobody measured against
the past is a rule that refuses the present on its first day" -- and it
answered it with a number nobody could act on. It took each commit's
population from the first build-agent name in the COMMIT SUBJECT.

WHY IT CANNOT BE FIXED RATHER THAN REMOVED, measured rather than argued:

  * THE SUBJECT IS NOT AN AUTHOR. b24's table reported `cody 50 path(s), 14
    REFUSED`. All 13 of those `.html` paths come from ONE commit, 50f67cfe,
    whose subject is "fix(contrast): 153 findings down to 3, app by app, and
    the 3 left are cody's file" -- fourth's commit, fourth's own files,
    entirely in scope, with `cody` appearing only as a possessive. 100% false
    positives for that population, and the DECISION-NEEDED it produced had to
    be withdrawn in b25.
  * THE AUTHOR FIELD IS NO BETTER. Every commit in this repository is authored
    by `Michael Dibert`, `SAIRN1` or `fx`. git carries no per-population
    signal at all, so switching fields replaces one wrong answer with another.
  * THE CLAIM FILES ARE DEFINITIVE AND DO NOT HELP. A commit touching exactly
    one `.claude/claims/<session>.json` is unambiguously that session's -- 237
    of the last 800 -- but those are claim and release commits and they carry
    no work paths. The work sits in the commits BETWEEN them, and attributing
    by interval is an inference, not a reading.

SO THE QUESTION IS ANSWERED A DIFFERENT WAY, by `--check --agent <who>` and
`--outgoing`, both of which classify PATHS and attribute nothing. The flag
still prints an explanation rather than an unknown-argument error, because a
removed flag that silently does nothing is the same defect one layer out.

── AND THE ONE DECISION THAT IS NOT MINE ───────────────────────────────────
The manifest's own `_the_deviation_michael_should_decide` records that cody
pushed 13 `.html` commits in two days under Michael's explicit assignment
while the split gives `.html` to fourth. `assigned_overrides` is the declared
route for that and it is EMPTY, so the refusal stands until somebody writes
one. Flagged rather than quietly permitted.
"""
import fnmatch
import io
import json
import os
import subprocess
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
try:
    from checker_kit import EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN
except Exception:                                                # noqa: BLE001
    EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN = 0, 1, 2

CRITERIA_VERSION = '2026-10-19.1'
MANIFEST = os.path.join('docs', 'sairn-path-manifest.json')

# The verdicts. Each names the RULE that decided, because "refused" with no
# rule is an argument nobody can settle.
OWNED = 'OWNED'                  # the pusher's own declared prefix
SELF = 'SELF-NAMED'             # carries the pusher's own session name
LEDGER = 'SHARED-LEDGER'        # declared union-merge, every population appends
UNOWNED = 'UNOWNED'             # no population claims it; allowed, reported
FOREIGN = 'FOREIGN'             # another population's declared area
AUDITOR = 'AUDITOR'            # the hover auditor's scope. Denied to all four.

ALLOWED = (OWNED, SELF, LEDGER, UNOWNED)


def load_manifest(repo=None):
    """-> (manifest, why). A malformed manifest is a could-not-run."""
    p = os.path.join(repo or REPO, MANIFEST)
    if not os.path.isfile(p):
        return None, ('%s is not in this clone, so NOTHING is known about who '
                      'owns what. A scope check with no scope has not checked '
                      'anything.' % MANIFEST)
    try:
        m = json.load(io.open(p, encoding='utf-8'))
    except ValueError as e:
        return None, '%s is not valid JSON (%s)' % (MANIFEST, e)
    for k in ('populations', 'auditor_paths', 'self_named', 'shared_ledgers',
              'populations_in_scope'):
        if k not in m:
            return None, ('%s has no %r key, so the manifest is a different '
                          'shape from the one this reads. Refusing rather '
                          'than guessing which half is missing.'
                          % (MANIFEST, k))
    return m, ''


def _norm(path):
    """A repo-relative path in one spelling.

    ── `lstrip('./')` WAS THE FIRST VERSION AND IT IS A REAL TRAP ───────────
    `str.lstrip` takes a SET OF CHARACTERS, not a prefix, so
    `'.claude/claims/cc.json'.lstrip('./')` is `'claims/cc.json'` -- the
    leading dot of a dot-directory is eaten and every `.claude/` and
    `.githooks/` path stopped matching. Caught by the fixtures within the
    minute: four arms went UNOWNED, including the auditor boundary, which is
    the one arm whose silent failure would have mattered most.
    """
    p = str(path).replace('\\', '/')
    while p.startswith('./'):
        p = p[2:]
    return p.lstrip('/')


def _under(path, prefix):
    """Is `path` inside `prefix`? Prefixes end in / and globs are globs."""
    p = _norm(path)
    if prefix.endswith('/'):
        return p.startswith(prefix)
    if '*' in prefix or '?' in prefix:
        return fnmatch.fnmatch(p, prefix)
    return p == prefix


def classify(path, agent, manifest):
    """-> (verdict, rule_text). Pure: no filesystem, no git.

    ORDER MATTERS AND IS NOT ARBITRARY. The auditor test runs FIRST, before
    any allowance, because a path inside the auditor's scope must be refused
    even if it would otherwise match a self-named pattern or a ledger -- an
    allowance that could reach into the auditor's clone would be the boundary
    failing in the one direction the separation exists to stop.
    """
    p = _norm(path)
    for a in manifest['auditor_paths']:
        if _under(p, a):
            return AUDITOR, ('%s is the hover auditor\'s scope and no build '
                             'population may push into it -- including to arm '
                             'its gates, which is the same boundary problem '
                             'running the other way' % a)
    # SELF-NAMED next, and only ever against the pusher's OWN name.
    for pat in manifest['self_named']:
        if '%s' in pat and _under(p, pat % agent):
            return SELF, ('matches %r, which carries this session\'s own name'
                          % (pat % agent))
    for led in manifest['shared_ledgers']:
        if _under(p, led):
            return LEDGER, ('%s is a declared shared ledger -- union merge, '
                            'every population appends by design' % led)
    pops = manifest['populations']
    mine = (pops.get(agent) or {}).get('owns') or []
    for pre in mine:
        if _under(p, pre):
            return OWNED, 'inside %r, which %s owns' % (pre, agent)
    over = (manifest.get('assigned_overrides') or {}).get(agent) or []
    for pre in over:
        if _under(p, pre):
            return OWNED, ('inside %r, assigned to %s by a declared override '
                           'in the manifest' % (pre, agent))
    for other, spec in sorted(pops.items()):
        if other == agent:
            continue
        for pre in (spec.get('owns') or []):
            if _under(p, pre):
                return FOREIGN, ('inside %r, which %s owns and %s does not. '
                                 'If this is assigned work, declare it in the '
                                 'manifest\'s assigned_overrides rather than '
                                 'pushing past this.' % (pre, other, agent))
    return UNOWNED, ('no population declares this path. Allowed on purpose -- '
                     'see the manifest\'s own note on why this is not an '
                     'allowlist -- and reported so the set stays visible.')


def check(paths, agent, manifest):
    """-> (rows, n_refused). rows are (path, verdict, rule)."""
    rows = [(p,) + classify(p, agent, manifest) for p in paths]
    return rows, sum(1 for _p, v, _r in rows if v not in ALLOWED)


# `--history` is kept here AFTER its removal on purpose: an old
# invocation must not have its count argument classified as a path,
# which is the very defect b25 fixed one flag over.
FLAGS_WITH_VALUES = ('--agent', '--history')


def paths_from_argv(argv):
    """The paths given after `--check`. Pure, so it can be locked.

    ── A FLAG'S VALUE IS NOT A PATH (fixed b25) ─────────────────────────────
    This was inline and collected everything after `--check` that did not
    start with `--`, which SWALLOWED THE VALUE OF `--agent`. Driven on the
    real tool: `--check --agent cody sairnroofing.html` classified a path
    literally named `cody` and reported 4 paths where 3 were given.

    THE PUSH VERDICT WAS STILL RIGHT, WHICH IS WHY IT SURVIVED. `cody`
    matched no prefix so it read UNOWNED and the three real paths were still
    refused -- so the exit code was correct and the OUTPUT carried a row
    about a file nobody named. A wrong line in a refusal a reader is meant to
    act on is worse than a wrong exit code, because the exit code is the part
    somebody re-derives.
    """
    if '--check' not in argv:
        return []
    out, skip = [], False
    for a in argv[argv.index('--check') + 1:]:
        if skip:
            skip = False
            continue
        if a in FLAGS_WITH_VALUES:
            skip = True
            continue
        if a.startswith('--'):
            continue
        out.append(a)
    return out


def session():
    """-> (agent, why). From the per-clone marker, never the folder name."""
    try:
        import sairn_session_identity as sid
        return sid.session_name(), ''
    except Exception as e:                                       # noqa: BLE001
        return None, str(e).splitlines()[0]


def outgoing(repo=None, base='origin/main'):
    """Paths this push would ship. -> (paths, why)."""
    cwd = repo or REPO
    try:
        r = subprocess.run(['git', 'diff', '--name-only', '%s...HEAD' % base],
                           cwd=cwd, capture_output=True, text=True,
                           encoding='utf-8', errors='replace', timeout=120)
    except Exception as e:                                       # noqa: BLE001
        return None, 'git diff failed (%s)' % type(e).__name__
    if r.returncode != 0:
        return None, ('git diff against %s failed, so what this push ships is '
                      'UNKNOWN -- that is not an empty list' % base)
    return [l.strip() for l in (r.stdout or '').splitlines() if l.strip()], ''


# ── THE CRITERIA LOCK: AN ARM, A NEGATIVE CONTROL AND AN ABLATION ──────────
def run_fixtures():
    print('SAIRN PATH MANIFEST -- criteria lock %s' % CRITERIA_VERSION)
    bad = total = 0

    def ck(name, got, want):
        nonlocal bad, total
        total += 1
        ok = (got == want)
        if not ok:
            bad += 1
        print('  %s %-74s got %r' % ('ok  ' if ok else 'FAIL', name, got))

    M = {
        'populations': {'hank': {'owns': ['api/']},
                        'cody': {'owns': ['tests/']},
                        'cc': {'owns': ['tools/', '.githooks/']},
                        'fourth': {'owns': ['docs/', '*.html']}},
        'assigned_overrides': {},
        'auditor_paths': ['.claude/skills/sairn-hover-auditor/'],
        'self_named': ['SAIRN-handoff-%s-*', 'SAIRN-report-%s-*',
                       '.claude/claims/%s.json', 'docs/*-%s-b*'],
        'shared_ledgers': ['docs/defect-density-register.json', 'docs/fmea/'],
        'populations_in_scope': ['hank', 'cc', 'cody', 'fourth'],
    }

    def v(path, agent):
        return classify(path, agent, M)[0]

    # ── THE ARM: an in-scope push passes. ──────────────────────────────────
    ck('IN SCOPE: cc pushing tools/x.py is OWNED', v('tools/x.py', 'cc'), OWNED)
    ck('...hank pushing api/sd-data.js is OWNED',
       v('api/sd-data.js', 'hank'), OWNED)
    ck('...cody pushing tests/x.js is OWNED', v('tests/x.js', 'cody'), OWNED)
    ck('...fourth pushing docs/x.md is OWNED', v('docs/x.md', 'fourth'), OWNED)
    ck('...fourth pushing stonedesk.html is OWNED -- the glob, not a prefix',
       v('stonedesk.html', 'fourth'), OWNED)

    # ── THE NEGATIVE CONTROL: out of scope is REFUSED. Without this the arms
    # above would pass on a check that allows everything.
    ck('OUT OF SCOPE: cc pushing api/sd-data.js is FOREIGN',
       v('api/sd-data.js', 'cc'), FOREIGN)
    ck('...cody pushing stonedesk.html is FOREIGN -- the measured deviation, '
       'and it stands until an override is declared',
       v('stonedesk.html', 'cody'), FOREIGN)
    ck('...hank pushing tools/x.py is FOREIGN', v('tools/x.py', 'hank'),
       FOREIGN)
    ck('...and the refusal NAMES the owner and the route, rather than just '
       'saying no', ('hank owns' in classify('api/x.js', 'cc', M)[1]
                     and 'assigned_overrides' in classify('api/x.js', 'cc', M)[1]),
       True)

    # ── THE AUDITOR BOUNDARY, AND IT OUTRANKS EVERY ALLOWANCE. ─────────────
    for a in ('hank', 'cc', 'cody', 'fourth'):
        ck('AUDITOR: %s pushing into the hover auditor\'s scope is refused'
           % a, v('.claude/skills/sairn-hover-auditor/tools/x.py', a), AUDITOR)
    ck('...and it outranks SELF-NAMED, which is the ordering that matters: a '
       'path that is both must still be refused',
       v('.claude/skills/sairn-hover-auditor/SAIRN-handoff-cc-b1.md', 'cc'),
       AUDITOR)

    # ── THE TWO ALLOWANCE CLASSES, each only for its own owner. ────────────
    ck('SELF-NAMED: cc pushing SAIRN-handoff-cc-b24.md is allowed',
       v('SAIRN-handoff-cc-b24.md', 'cc'), SELF)
    ck('...and cc pushing HANK\'s handoff is NOT -- the pattern is filled '
       'with the PUSHER\'s name, so it cannot be widened by renaming a folder',
       v('SAIRN-handoff-hank-b20.md', 'cc'), UNOWNED)
    ck('...cc pushing .claude/claims/cc.json is allowed',
       v('.claude/claims/cc.json', 'cc'), SELF)
    ck('...and .claude/claims/hank.json is not cc\'s',
       v('.claude/claims/hank.json', 'cc'), UNOWNED)
    ck('...cc pushing docs/2026-10-19-cc-b24-notes.md is allowed BY NAME '
       'even though docs/ is fourth\'s',
       v('docs/2026-10-19-cc-b24-notes.md', 'cc'), SELF)
    ck('...but docs/some-other-design.md is still fourth\'s',
       v('docs/some-other-design.md', 'cc'), FOREIGN)
    ck('SHARED LEDGER: any population may append to the defect register',
       (v('docs/defect-density-register.json', 'cc'),
        v('docs/defect-density-register.json', 'hank')), (LEDGER, LEDGER))
    ck('...and the ledger list is INDIVIDUAL paths, so a sibling in docs/ is '
       'NOT swept in with it', v('docs/not-a-ledger.json', 'cc'), FOREIGN)

    # ── A MIXED PUSH IS REFUSED WHOLE. ─────────────────────────────────────
    mixed = ['tools/ok.py', 'SAIRN-report-cc-b24.txt', 'api/sneaky.js']
    rows, n = check(mixed, 'cc', M)
    ck('A MIXED PUSH IS REFUSED WHOLE: two in-scope paths do not license the '
       'third', n, 1)
    ck('...and the in-scope paths are still classified rather than dropped, '
       'so the reader sees the whole push',
       [r[1] for r in rows], [OWNED, SELF, FOREIGN])

    # ── THE ABLATION: remove the manifest ENTRY and the check goes red. ────
    # Not "remove the file" -- that is the could-not-run path and is tested
    # below. This removes ONE population's ownership and measures what that
    # entry alone was holding.
    abl = json.loads(json.dumps(M))
    abl['populations']['hank']['owns'] = []
    ck('ABLATION: with hank\'s api/ ownership removed from the manifest, cc '
       'pushing api/sd-data.js is no longer FOREIGN -- so that entry is what '
       'was refusing it, and nothing else',
       classify('api/sd-data.js', 'cc', abl)[0], UNOWNED)
    ck('ABLATION CONTROL: the same removal does NOT change cc\'s own verdict '
       'on its own file, so the ablation moved one thing',
       classify('tools/x.py', 'cc', abl)[0], OWNED)
    abl2 = json.loads(json.dumps(M))
    abl2['auditor_paths'] = []
    ck('ABLATION: with the auditor paths removed, the auditor refusal stops '
       'firing -- that list is the only thing holding it',
       classify('.claude/skills/sairn-hover-auditor/tools/x.py', 'cc',
                abl2)[0], UNOWNED)

    # ── FAILS CLOSED ON ITS OWN INPUTS. ────────────────────────────────────
    import tempfile
    sandbox = tempfile.mkdtemp(prefix='pathman-')
    m, why = load_manifest(sandbox)
    ck('a MISSING manifest is a could-not-run with a reason, not a pass',
       (m, 'has not checked anything' in why), (None, True))
    os.makedirs(os.path.join(sandbox, 'docs'))
    io.open(os.path.join(sandbox, MANIFEST), 'w', encoding='utf-8',
            newline='\n').write('{ not json')
    m, why = load_manifest(sandbox)
    ck('...and a MALFORMED one is too', (m, 'not valid JSON' in why),
       (None, True))
    io.open(os.path.join(sandbox, MANIFEST), 'w', encoding='utf-8',
            newline='\n').write('{"populations": {}}')
    m, why = load_manifest(sandbox)
    ck('...and one of a DIFFERENT SHAPE is refused rather than half-read',
       (m, 'different shape' in why), (None, True))
    ck('AN UNKNOWN AGENT OWNS NOTHING, so every owned path reads FOREIGN '
       'rather than defaulting open', v('tools/x.py', 'nobody'), FOREIGN)

    # ── THE ARGV COLLECTION (b25). A FLAG'S VALUE IS NOT A PATH. ───────────
    # ARM: the real invocation that exposed it.
    ck('`--check --agent cody a.html` gives ONE path, not two -- the agent '
       'name is a flag VALUE and was being classified as a file',
       paths_from_argv(['--check', '--agent', 'cody', 'a.html']), ['a.html'])
    # NEGATIVE CONTROL: without this, the arm above would pass on a collector
    # that simply dropped the first argument.
    ck('...and the flag AFTER the paths is handled too, so the fix is not '
       'position-dependent',
       paths_from_argv(['--check', 'a.html', '--agent', 'cody']), ['a.html'])
    ck('...a bare --check collects nothing rather than guessing',
       paths_from_argv(['--check']), [])
    ck('...no --check at all collects nothing',
       paths_from_argv(['--outgoing']), [])
    ck('...and a VALUELESS flag is still skipped without eating a path',
       paths_from_argv(['--check', '--outgoing', 'a.html']), ['a.html'])
    # ABLATION: the pre-b25 expression, stated as an arm so the regression
    # has to argue with it.
    ck('ABLATION: the pre-b25 collector returns the agent name AS A PATH, '
       'which is what put a row about a file nobody named into a refusal',
       [a for a in ['--agent', 'cody', 'a.html'] if not a.startswith('--')],
       ['cody', 'a.html'])

    # ── --history IS REMOVED AND ITS ARGUMENT MUST STILL NOT BE A PATH (b26)
    # The flag is kept in FLAGS_WITH_VALUES after its removal precisely so an
    # old invocation does not classify its count. Without this arm, a later
    # tidy-up that drops the name from that tuple would reintroduce the b25
    # defect one flag over, silently.
    ck('a removed flag\'s VALUE is still not a path -- `--check --history 200 '
       'a.html` gives one path, not two',
       paths_from_argv(['--check', '--history', '200', 'a.html']), ['a.html'])
    ck('...and `--history` is still named in FLAGS_WITH_VALUES, which is what '
       'makes the arm above true', '--history' in FLAGS_WITH_VALUES, True)

    print('  %d/%d arms classify correctly' % (total - bad, total))
    return EXIT_FINDING if bad else EXIT_CLEAN


def _print_rows(rows, agent):
    width = max([len(r[0]) for r in rows] + [4])
    for p, verdict, rule in rows:
        mark = '    ' if verdict in ALLOWED else '  ! '
        print('%s%-*s  %-14s %s' % (mark, width, p, verdict, rule))
    refused = [r for r in rows if r[1] not in ALLOWED]
    print('')
    if refused:
        print('REFUSED: %d of %d path(s) are outside %s\'s declared scope. A '
              'push is refused WHOLE -- the in-scope paths do not license the '
              'rest.' % (len(refused), len(rows), agent))
    else:
        print('IN SCOPE: all %d path(s) are inside %s\'s declared scope, or '
              'are self-named, a shared ledger, or unowned.'
              % (len(rows), agent))


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if '--fixtures' in argv or '--selftest' in argv:
        return run_fixtures()
    # THE LOCK FIRST, as everywhere else here: a classifier whose own criteria
    # are broken refuses or permits on arithmetic nobody checked.
    if run_fixtures() != EXIT_CLEAN:
        print('')
        print('COULD NOT RUN: the criteria lock failed, so no verdict about a '
              'real push is trustworthy.')
        return EXIT_COULD_NOT_RUN
    print('')

    # ── --history WAS REMOVED, AND THAT IS THE DECISION (b26) ──────────────
    # See the module docstring. A named flag that now does nothing would be
    # worse than its absence, so it is answered rather than ignored.
    if '--history' in argv:
        print('REMOVED: --history was removed in b26 and the reason is in the '
              'module docstring. It attributed each commit to a population by '
              'searching the COMMIT SUBJECT for an agent name, and MEASURED, '
              'git carries no per-population signal in this repo at all -- '
              'every commit is authored by "Michael Dibert", "SAIRN1" or '
              '"fx". Its b24 table reported cody at 14 REFUSED and all 13 of '
              'those .html paths were ONE commit belonging to fourth, whose '
              'subject named cody possessively: 100% false positives for that '
              'population, and it produced a DECISION-NEEDED that had to be '
              'withdrawn.')
        print('')
        print('What to use instead, and it answers the question this was asked '
              'for without attributing anything:')
        print('    python tools/sairn_path_manifest.py --check --agent <who> '
              '<path> ...')
        print('    python tools/sairn_path_manifest.py --outgoing')
        return EXIT_COULD_NOT_RUN

    agent = (argv[argv.index('--agent') + 1] if '--agent' in argv else None)
    if agent is None:
        agent, why = session()
        if agent is None:
            print('COULD NOT RUN: this clone\'s session identity could not be '
                  'established, so "is this path mine" has no answer: %s' % why)
            return EXIT_COULD_NOT_RUN
    m, why = load_manifest()
    if m is None:
        print('COULD NOT RUN: %s' % why)
        return EXIT_COULD_NOT_RUN
    if agent not in (m.get('populations_in_scope') or []):
        print('NOT IN SCOPE OF THIS MANIFEST: %r is not one of the build '
              'populations (%s), so this check does not apply to it and is '
              'not reporting a pass about it.'
              % (agent, ', '.join(m['populations_in_scope'])))
        return EXIT_CLEAN

    if '--outgoing' in argv:
        paths, why = outgoing()
        if paths is None:
            print('COULD NOT RUN: %s' % why)
            return EXIT_COULD_NOT_RUN
        if not paths:
            print('IN SCOPE: this push ships no files.')
            return EXIT_CLEAN
    else:
        paths = paths_from_argv(argv)
        if not paths:
            print('COULD NOT RUN: pass --check <path> ... or --outgoing. '
                  'Nothing was checked.')
            return EXIT_COULD_NOT_RUN

    print('PATH MANIFEST -- criteria %s, agent %s' % (CRITERIA_VERSION, agent))
    rows, n = check(paths, agent, m)
    _print_rows(rows, agent)
    return EXIT_FINDING if n else EXIT_CLEAN


if __name__ == '__main__':
    sys.exit(main())
