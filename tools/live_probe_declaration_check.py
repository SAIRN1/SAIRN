"""Can the RESIDUE AUDITOR'S OWN PARSER read this tool's declarations?

    python tools/live_probe_declaration_check.py            # working tree
    python tools/live_probe_declaration_check.py --staged   # pre-commit
    python tools/live_probe_declaration_check.py --selftest

── THE DEFECT CLASS, AND IT IS NOT "SOMEBODY FORGOT TO DECLARE" ─────────────
2026-09-30. tools/mech_gate_live_probe.py was written specifically to be judged by
tools/live_probe_residue_audit.py. It declared LIVE_PROBE_CLASS, it declared
LIVE_PROBE_RESIDUE, it called require_audit_licence before any request -- and the
auditor could not read it THREE SEPARATE WAYS:

  1. THE WRITE ACTION WAS POSITIONAL. `call('write', resource, ...)` into a
     helper. `action_literals()` matches `'action': 'write'` and
     `action = 'write'`, so the tool was ABSENT FROM THE WRITING-PROBE LIST
     ENTIRELY -- the audit reported 9 writers where there were 10, and a tool
     nobody counts is a tool nobody judges.
  2. THE RESIDUE DECLARATION WAS A MULTI-LINE CONCATENATION.
     `LIVE_PROBE_RESIDUE = ('a' 'b' 'c')` reads better and `RESIDUE_RE` matches
     ONE quoted literal, so the audit said "declares no LIVE_PROBE_RESIDUE"
     about a file that declares it in full.
  3. THE RESIDUE PATH DID NOT COME FIRST. The audit takes
     `residue.split()[0]` and requires that file to exist.

**EVERY ONE OF THOSE LOOKS IDENTICAL TO NOT DECLARING AT ALL.** That is the whole
problem: the auditor's "declares no X" finding cannot distinguish an author who
said nothing from an author who said it in a form the regex does not accept, and
the second author has no reason to suspect anything -- their file is correct.

── SO THIS CHECK ASKS A DIFFERENT QUESTION FROM THE AUDITOR ────────────────
The auditor asks **"is there a declaration?"**. This asks **"is the declaration
UNREADABLE?"** -- the name is present in the source and the auditor's own regex
captures nothing from it. Those are different findings with different fixes, and
folding them together is what made three correct files look negligent.

**IT IMPORTS THE AUDITOR'S PARSERS RATHER THAN RE-IMPLEMENTING THEM.** A second
copy of `RESIDUE_RE` would drift, and the day it drifted this check would bless a
declaration the auditor still cannot read -- which is the failure one level up.
If the auditor's regexes change, this check changes with them for free.

── PRE-COMMIT, AND WHY IT READS THE INDEX AND NOT THE WORKING TREE ─────────
`--staged` reads each file's STAGED content with `git show :<path>`. A pre-commit
hook that read the working tree would pass a commit whose staged version is
different, which is the `git add -p` case and is not exotic.
"""
import argparse
import io
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

EXIT_CLEAN = 0
EXIT_FINDING = 1
EXIT_COULD_NOT_RUN = 2

try:
    import live_probe_residue_audit as A
except Exception as e:                                    # pragma: no cover
    sys.stderr.write(
        'COULD NOT RUN: tools/live_probe_residue_audit.py would not import '
        '(%s), so its parsers are not available and NOTHING was checked. This '
        'check exists to use the auditor\'s own regexes and refuses to '
        'substitute its own.\n' % e)
    sys.exit(EXIT_COULD_NOT_RUN)

# Every declaration the auditor parses, paired with the regex it parses it with.
# Taken from the module, never retyped -- see the header.
DECLS = (
    ('LIVE_PROBE_CLASS', 'CLASS_RE'),
    ('LIVE_PROBE_RESIDUE', 'RESIDUE_RE'),
    ('LIVE_PROBE_TEARDOWN', 'TEARDOWN_RE'),
)
WRITEISH = re.compile(r"\baction\b|\bwrite\b|fetch_json|post_json|requests\.post",
                      re.I)


def _missing_parser():
    """Which of the auditor's attributes this check depends on are absent."""
    need = ['LIVE_HOST', 'WRITE_ACTIONS', 'action_literals'] + \
           [r for _, r in DECLS]
    return [n for n in need if not hasattr(A, n)]


def read_staged(rel):
    r = subprocess.run(['git', '-C', REPO, 'show', ':' + rel],
                       capture_output=True)
    if r.returncode != 0:
        return None
    return r.stdout.decode('utf-8', 'replace')


def staged_paths():
    r = subprocess.run(['git', '-C', REPO, 'diff', '--cached', '--name-only',
                        '--diff-filter=ACMR'], capture_output=True, text=True)
    return [p for p in r.stdout.split()
            if p.endswith(('.py', '.js'))
            and p.split('/')[0] in ('tools', 'tests', 'scripts')]


def tracked_paths():
    r = subprocess.run(['git', '-C', REPO, 'ls-files', 'tools', 'tests',
                        'scripts'], capture_output=True, text=True)
    return [p for p in r.stdout.split() if p.endswith(('.py', '.js'))]


# ── AN ASSIGNMENT, NOT A MENTION, AND THE FIRST REAL RUN PROVED WHY ─────────
# The first run reported FOUR findings and all four were prose: the auditor
# itself and tools/tooling_inventory.py both EXPLAIN this contract in their own
# docstrings, naming LIVE_PROBE_CLASS and LIVE_PROBE_RESIDUE, and both name the
# live host. Asking "does the name appear in the source" read every one of those
# explanations as a broken declaration.
#
# THAT IS THE SAME FALSE POSITIVE THE AUDITOR PRODUCED ON MY OWN FILE one day
# earlier -- it flagged a demo licence key that appeared only in the prose
# recording the incident. A checker that cannot tell prose from code will,
# sooner or later, report the document that describes it.
TRIPLE = re.compile(r"'''[\s\S]*?'''" + '|' + r'"""[\s\S]*?"""')
BLOCK_C = re.compile(r'/\*[\s\S]*?\*/')
LINE_C = re.compile(r'^[ \t]*(?:#|//)[^\n]*$', re.M)


def _code_only(src):
    """Source with docstrings and comments removed.

    THE SECOND FALSE POSITIVE, AND IT WAS THE AUDITOR'S OWN FILE. Its docstring
    shows the three legal values as INDENTED EXAMPLES -- an assignment on its own
    line to any regex, and prose to a reader. So an assignment test is not
    enough; the assignment has to be in CODE.

    THIS IS THE THIRD TIME THIS REPO HAS PAID FOR IT. The cross-tenant grader
    scored a comment as a driven row, the mech redaction probe scored its own
    explanatory prose, and the residue auditor flagged a demo licence key that
    appeared only in the sentence recording the incident. A shape scan that has
    not stripped comments first will eventually report the file's own account of
    itself.
    """
    out = TRIPLE.sub(' ', src)
    out = BLOCK_C.sub(' ', out)
    return LINE_C.sub(' ', out)


def _declares(src, name):
    """Is `name` ASSIGNED at the top level, in CODE rather than in prose?"""
    return re.search(r'^[ \t]*' + name + r'\s*=', _code_only(src),
                     re.M) is not None


def inspect(rel, src):
    """Findings for one file. Empty when the auditor can read everything it says."""
    out = []
    if A.LIVE_HOST not in src:
        return out                      # not a live tool at all
    # ── 1. AN UNREADABLE DECLARATION IS NOT A MISSING ONE ───────────────────
    for name, rname in DECLS:
        if not _declares(src, name):
            continue                    # genuinely absent -- the auditor's job
        if not getattr(A, rname).search(src):
            out.append({
                'file': rel, 'kind': 'UNPARSEABLE-DECLARATION', 'name': name,
                'why': '%s appears in the source and %s captures nothing from '
                       'it. The auditor will report "declares no %s", which is '
                       'indistinguishable from an author who said nothing. The '
                       'usual cause is a parenthesised multi-line '
                       'concatenation where the regex wants ONE quoted literal.'
                       % (name, rname, name)})
    # ── 2. A WRITE THE AUDITOR CANNOT SEE ───────────────────────────────────
    # Only asked of a file that already declares itself a live probe: a file with
    # no LIVE_PROBE_CLASS is not claiming to be judged, and guessing at one is
    # how this check would start inventing findings.
    if _declares(src, 'LIVE_PROBE_CLASS') and WRITEISH.search(src):
        acts = A.action_literals(src) & A.WRITE_ACTIONS
        cls = A.CLASS_RE.search(src)
        cls = cls.group(1) if cls else ''
        if cls == 'VERIFICATION' and not acts:
            out.append({
                'file': rel, 'kind': 'WRITE-INVISIBLE-TO-THE-AUDITOR',
                'name': 'action literal',
                'why': 'this declares LIVE_PROBE_CLASS = VERIFICATION and does '
                       'something write-shaped, and action_literals() finds no '
                       'write action LITERAL. The auditor will leave it out of '
                       'the writing-probe list entirely, so none of the four '
                       'obligations is checked against it. The usual cause is a '
                       'write action passed POSITIONALLY into a helper; name it '
                       "with `action = 'write'` on its own line."})
    # ── 3. A RESIDUE PATH THE AUDITOR WILL LOOK FOR AND NOT FIND ────────────
    rm = A.RESIDUE_RE.search(src)
    if rm:
        val = rm.group(1).strip()
        first = val.split()[0] if val.split() else ''
        if val and not val.lower().startswith('none') \
                and not os.path.exists(os.path.join(REPO, first)):
            out.append({
                'file': rel, 'kind': 'RESIDUE-PATH-NOT-FIRST-OR-NOT-REAL',
                'name': 'LIVE_PROBE_RESIDUE',
                'why': 'the auditor takes residue.split()[0] and requires that '
                       'file to exist; the first token here is %r, which is not '
                       'a path in this repo. Put the standing path FIRST, or '
                       'start the declaration with "none -- <why>".' % first})
    return out


def selftest():
    bad = []

    def ck(name, cond):
        print(('  ok   ' if cond else '  FAIL ') + name)
        if not cond:
            bad.append(name)

    host = A.LIVE_HOST
    ok_src = (
        "LIVE_PROBE_CLASS = 'VERIFICATION'\n"
        "LIVE_PROBE_RESIDUE = 'docs/live-residue/README.md -- one row, audit licence only'\n"
        "URL = 'https://%s/api/sd-data'\n"
        "action = 'write'\n" % host)
    ck('a readable declaration set produces NOTHING', not inspect('x.py', ok_src))

    # THE THREE REAL FAILURES, each on its own.
    multi = ok_src.replace(
        "LIVE_PROBE_RESIDUE = 'docs/live-residue/README.md -- one row, audit licence only'",
        "LIVE_PROBE_RESIDUE = ('README.md -- one row, '\n"
        "                      'audit licence only')")
    f = inspect('x.py', multi)
    ck('FAILURE 2: a multi-line concatenation is UNPARSEABLE-DECLARATION, not '
       '"missing"', any(x['kind'] == 'UNPARSEABLE-DECLARATION' for x in f))

    positional = ok_src.replace("action = 'write'", "call('write', 'mech_docs')")
    f = inspect('x.py', positional)
    ck('FAILURE 1: a positional write action is WRITE-INVISIBLE-TO-THE-AUDITOR',
       any(x['kind'] == 'WRITE-INVISIBLE-TO-THE-AUDITOR' for x in f))

    notfirst = ok_src.replace(
        "'docs/live-residue/README.md -- one row, audit licence only'",
        "'one row per table, see docs/live-residue/README.md'")
    f = inspect('x.py', notfirst)
    ck('FAILURE 3: a residue path that is not the FIRST token is reported',
       any(x['kind'] == 'RESIDUE-PATH-NOT-FIRST-OR-NOT-REAL' for x in f))

    # AND THE DIRECTIONS IT MUST NOT FIRE IN.
    ck('a file that never names the live host is ignored entirely',
       not inspect('x.py', "LIVE_PROBE_RESIDUE = ('a' 'b')\n"))
    ck('a GENUINELY ABSENT declaration is NOT reported here -- that is the '
       "auditor's finding and duplicating it would make two tools disagree "
       'about one fact',
       not [x for x in inspect('x.py',
                               "URL = 'https://%s/x'\n" % host)
            if x['kind'] == 'UNPARSEABLE-DECLARATION'])
    ck('a residue declaration starting with "none" needs no path',
       not [x for x in inspect('x.py', ok_src.replace(
           "'docs/live-residue/README.md -- one row, audit licence only'",
           "'none -- it upserts one row on the audit licence'"))
            if x['kind'].startswith('RESIDUE-PATH')])
    ck('a LOADER with no write literal is not reported -- only VERIFICATION is '
       'held to the obligations',
       not [x for x in inspect('x.py', ok_src.replace(
           "'VERIFICATION'", "'LOADER'").replace("action = 'write'",
                                                 "call('write', 'x')"))
            if x['kind'] == 'WRITE-INVISIBLE-TO-THE-AUDITOR'])
    print('')
    return EXIT_FINDING if bad else EXIT_CLEAN


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--staged', action='store_true',
                    help='read STAGED content -- the pre-commit mode')
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args(argv)

    gone = _missing_parser()
    if gone:
        sys.stderr.write(
            'COULD NOT RUN: tools/live_probe_residue_audit.py no longer exposes '
            '%s, so this check cannot use the auditor\'s own parser and will NOT '
            'substitute its own. Nothing was checked -- this is not a pass.\n'
            % ', '.join(gone))
        return EXIT_COULD_NOT_RUN

    if args.selftest:
        print('live_probe_declaration_check --selftest\n')
        return selftest()

    findings, scanned, unreadable = [], 0, 0
    if args.staged:
        paths = staged_paths()
        for rel in paths:
            src = read_staged(rel)
            if src is None:
                unreadable += 1
                continue
            scanned += 1
            findings += inspect(rel, src)
    else:
        paths = tracked_paths()
        for rel in paths:
            try:
                src = io.open(os.path.join(REPO, rel), encoding='utf-8',
                              errors='replace').read()
            except OSError:
                unreadable += 1
                continue
            scanned += 1
            findings += inspect(rel, src)

    print('LIVE PROBE DECLARATION READABILITY -- can the auditor parse what this '
          'tool says?')
    print('  mode                        : %s'
          % ('STAGED (pre-commit)' if args.staged else 'working tree'))
    print('  candidate files             : %d' % len(paths))
    print('  read                        : %d' % scanned)
    print('  UNREADABLE BY THIS CHECK    : %d' % unreadable)
    print('')
    print('  DECLARATIONS THE AUDITOR CANNOT PARSE: %d' % len(findings))
    for x in findings:
        print('    %s  [%s] %s' % (x['file'], x['kind'], x['name']))
        print('        %s' % x['why'])

    print('')
    print('  BLIND TO THIS CHECK, counted rather than implied:')
    print('    * A GENUINELY ABSENT declaration is NOT reported here. That is the '
          'auditor\'s own finding,')
    print('      and reporting it twice would let two tools disagree about one '
          'fact.')
    print('    * A write reached through a DYNAMICALLY BUILT action name is '
          'invisible to')
    print('      action_literals(), so it is invisible here too -- this check '
          'inherits every blind')
    print('      spot the auditor has, on purpose, because it uses the auditor\'s '
          'parsers.')
    print('    * %d file(s) could not be read at all and are not counted clean.'
          % unreadable)
    if args.staged:
        print('    * STAGED MODE SEES ONLY WHAT IS STAGED. A live tool already '
              'committed with an')
        print('      unreadable declaration is not in this run\'s population; the '
              'working-tree mode is.')
    print('')
    return EXIT_FINDING if findings else EXIT_CLEAN


if __name__ == '__main__':
    sys.exit(main())
