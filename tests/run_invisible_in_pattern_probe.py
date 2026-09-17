"""tests/run_invisible_in_pattern_probe.py

Run:  python tests/run_invisible_in_pattern_probe.py

The control pair for tools/invisible_in_pattern_check.py.

A CHECKER THAT HAS NEVER BEEN SEEN TO FAIL IS A CHECKER WHOSE BEHAVIOUR NOBODY
KNOWS, and this one currently reports CLEAN across 653 files -- which is exactly
what a checker that cannot fire also reports. `checkblocks.py` always exited 0
and nothing noticed for months, because a check that always passes looks exactly
like a codebase that is always clean.

So both directions, on REAL files in a throwaway worktree, never in this clone:

    plant an invisible character inside a real regex  -> must EXIT 1 and NAME it
    leave the same file alone                         -> must EXIT 0
    break one of its own fixtures                     -> must EXIT 2, judging nothing

AND THE BOUNDARY ARM, which is the one that keeps two tools from becoming one:
a C0 backspace planted in a regex must leave THIS tool silent. C0 is
control_char_check.py's question and push-gate check 11's; a tool that answered
both would be the second copy the Guardian skill says to resolve on discovery,
and the overlap would be invisible until the two disagreed.

EVERY SABOTAGE ASSERTS IT LANDED before the checker is run. The patch here is a
string replace against a real file, which is precisely the shape
tools/sabotage_control_check.py exists to catch: when the anchor rots,
str.replace silently does nothing, the checker runs against an UNCHANGED file,
and "the checker exited 0" is then reported as the clean arm passing.
"""
# REQUIREMENT: a pattern containing an invisible or control character is refused,
#   because such a pattern can never match and reports clean forever
#
import io
import os
import subprocess
import sys

CONTROLS_FOR = ['invisible_in_pattern_check.py']

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True, encoding='utf-8', errors='replace').stdout.strip()
FAIL = []
ZWSP = chr(0x200B)
BS = chr(0x08)


def ok(name, cond, detail=''):
    print('  %s %s%s' % ('PASS ' if cond else 'FAIL ', name,
                         '' if cond else '\n        ' + str(detail)[:500]))
    if not cond:
        FAIL.append(name)


def git(cwd, *args):
    return subprocess.run(['git', '-C', cwd] + list(args),
                          capture_output=True, text=True, encoding='utf-8', errors='replace')


def run_tool(cwd, *args):
    r = subprocess.run([sys.executable,
                        os.path.join(cwd, 'tools', 'invisible_in_pattern_check.py')]
                       + list(args), capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=cwd)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def worktree(tag):
    """A detached worktree at HEAD, carrying THIS clone's copy of the tool.

    The tool is copied in rather than taken from HEAD on purpose: a control that
    only ever exercises the COMMITTED version cannot prove anything about the
    change being made, which is the one moment the control is for.
    """
    d = os.path.join(os.environ.get('TEMP', '/tmp'), 'invis-%s-%d' % (tag, os.getpid()))
    if os.path.isdir(d):
        git(REPO, 'worktree', 'remove', '--force', d)
    git(REPO, 'worktree', 'add', '-q', '--detach', d, 'HEAD')
    live = os.path.join(REPO, 'tools', 'invisible_in_pattern_check.py')
    io.open(os.path.join(d, 'tools', 'invisible_in_pattern_check.py'), 'w',
            encoding='utf-8', newline='').write(io.open(live, encoding='utf-8').read())
    return d


def drop(d):
    git(REPO, 'worktree', 'remove', '--force', d)
    git(REPO, 'worktree', 'prune')


def plant(wt, rel, anchor, replacement):
    """Patch a real file and PROVE the patch landed, or raise."""
    p = os.path.join(wt, rel)
    s = io.open(p, encoding='utf-8').read()
    if anchor not in s:
        raise AssertionError('the SABOTAGE did not land: anchor no longer in %s -- %r'
                             % (rel, anchor[:60]))
    s2 = s.replace(anchor, replacement, 1)
    if s2 == s:
        raise AssertionError('the SABOTAGE did not land: replace was a no-op in ' + rel)
    io.open(p, 'w', encoding='utf-8', newline='').write(s2)
    back = io.open(p, encoding='utf-8').read()
    if replacement not in back:
        raise AssertionError('the SABOTAGE did not land: not on disk in ' + rel)
    return p


def append(wt, rel, block):
    """Add a block to the END of a real file, and PROVE it landed, or raise.

    ── THERE IS NO ANCHOR HERE ON PURPOSE (2026-09-17) ─────────────────────
    Arms C and D do not need to break any particular line; they need a real
    tracked file, scanned by the real tool, to contain one planted pattern.
    An anchor was doing nothing for them except giving the probe a way to rot,
    and it DID rot -- see the note beside TARGET. The assertion the docstring
    promises is kept in full: the file is read back and the block must be in
    it, and the file must actually have grown.
    """
    p = os.path.join(wt, rel)
    before = io.open(p, encoding='utf-8').read()
    io.open(p, 'w', encoding='utf-8', newline='').write(before + block)
    back = io.open(p, encoding='utf-8').read()
    if block not in back or len(back) <= len(before):
        raise AssertionError('the SABOTAGE did not land: block not on disk in ' + rel)
    return p


# The target is a REAL tracked file, scanned by the real tool, and unrelated to
# it -- so a failure here is about the checker rather than about the subject.
#
# ── IT USED TO CARRY A TEXT ANCHOR, AND THE ANCHOR DIED (2026-09-17) ────────
# ANCHOR was the regex literal `/^\d{4}-\d{2}-\d{2}$/`, and 7099d99f -- "item
# 94: one module owns what a calendar date is, and all fourteen copies were
# wrong" -- removed it along with the other thirteen copies. ANCHORING ON A
# DUPLICATED CONSTRUCT IS ANCHORING ON SOMETHING WHOSE WHOLE FUTURE IS TO BE
# DEDUPLICATED, which is the part worth carrying forward: the refactor did not
# break this probe by accident, it did exactly what it was written to do.
#
# The probe's own guard is what reported it -- `plant()` raises rather than
# letting str.replace no-op, so arms C and D failed loudly instead of running
# the checker against an unmodified file and reporting the clean result as a
# pass. That is the shape tools/sabotage_control_check.py exists to catch and
# it worked; what it could not do was tell anybody which anchor to use next.
#
# AND THE TOOL THAT TRACKS STALE ANCHORS CANNOT SEE THIS FILE. Cross-checked
# 2026-09-17: tools/mutation_anchor_check.py walks probes that define a
# MUTATIONS list, and this probe has none -- it calls plant() directly. So its
# anchors were never in the 245 the checker verifies, and the one rot it had
# was invisible to the one tool built to find rots. Arms C and D now have no
# text anchor at all, which removes them from that gap rather than papering
# over it; arm E's anchor is REAL -- it is an assertion about the tool's own
# fixture table -- and is declared to mutation_anchor_check below.
TARGET = 'api/_lib/accounting-connector.js'
TOOL = 'tools/invisible_in_pattern_check.py'

# ── THE ONE REMAINING TEXT ANCHOR, DECLARED SO THE ANCHOR CHECKER SEES IT ───
# Arm E flips one of the tool's own blind-lock fixtures from False to True, and
# that anchor is REAL: it is an assertion about the fixture table, not a
# position to write at, so it cannot be replaced by an append.
#
# It is declared as MUTATIONS purely so tools/mutation_anchor_check.py counts
# it among the anchors it verifies match exactly once. That checker walks
# probes DEFINING THIS NAME, and this probe defined none -- which is why its
# only rot was invisible to the only tool built to find rots. Arm E reads the
# entry rather than repeating it, so the declaration cannot drift from the use.
MUTATIONS = [
    ("E. the blind lock's own fixture is flipped to disagree", TOOL,
     "    ('a clean regex literal', 'f.js',\n"
     "     'assert.ok(/delete/i.test(src));', False),",
     "    ('a clean regex literal', 'f.js',\n"
     "     'assert.ok(/delete/i.test(src));', True),"),
]

print('invisible_in_pattern_check -- the control pair')

# ── A. the blind lock stands on its own, judging nothing real ───────────────
print('\n--- A. the fixtures, in isolation ---')
rc, out = run_tool(REPO, '--fixtures')
ok('A1 --fixtures exits 0', rc == 0, 'rc=%d\n%s' % (rc, out))
ok('A2 and says it judged the fixtures BEFORE any real file', 'before any real file' in out, out)
ok('A3 and it opened no real file -- no census, no scan count',
   'files scanned' not in out, out)

# ── B. the clean direction, on the real tree ────────────────────────────────
print('\n--- B. the real tree, untouched ---')
rc, out = run_tool(REPO)
ok('B1 the repo is clean today', rc == 0, 'rc=%d\n%s' % (rc, out[-600:]))
ok('B2 and it says how many files it looked at', 'files scanned' in out, out[-400:])
ok('B3 and it PRINTS its exclusions rather than dropping them quietly',
   'not scanned' in out, out[-400:])
ok('B4 the census runs even on a clean pass, so a zero is a real zero',
   'CENSUS' in out, out[-400:])

# ── C. plant one, and it must fire AND name it ──────────────────────────────
print('\n--- C. an invisible character inside a real regex ---')
wt = worktree('flag')
try:
    append(wt, TARGET,
           "\n_PROBE_RE = 'x' if False else None\n_PROBE = (0,)\n"
           + "_PROBE_PATTERN = [/de%slete/i] if False else None\n" % ZWSP)
    rc, out = run_tool(wt)
    ok('C1 it exits 1', rc == 1, 'rc=%d\n%s' % (rc, out[-800:]))
    ok('C2 and names the file', TARGET in out.replace('\\', '/'), out[-800:])
    ok('C3 and names the codepoint', 'U+200B' in out, out[-800:])
    ok('C4 and says it is inside a pattern, not merely present',
       'INSIDE A PATTERN' in out, out[-800:])
finally:
    drop(wt)

# ── D. THE BOUNDARY. C0 belongs to the other tool and must stay there ───────
print('\n--- D. a C0 backspace is NOT this tool\'s finding ---')
wt = worktree('c0')
try:
    append(wt, TARGET,
           "\n_PROBE_PATTERN = [/de%slete/i] if False else None\n" % BS)
    rc, out = run_tool(wt)
    ok('D1 this tool stays silent on C0', rc == 0, 'rc=%d\n%s' % (rc, out[-800:]))
    # AND THE OTHER HALF: the C0 tool must actually catch what this one declined.
    # Without this, "silent" is indistinguishable from "nobody checks C0 at all",
    # which is the gap the division of labour is supposed to close rather than open.
    r = subprocess.run([sys.executable, os.path.join(wt, 'tools', 'control_char_check.py')],
                       capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=wt)
    ok('D2 and control_char_check DOES catch it -- the split leaves no hole',
       r.returncode == 1 and '0x08' in (r.stdout or ''),
       'rc=%d\n%s' % (r.returncode, (r.stdout or '')[-500:]))
finally:
    drop(wt)

# ── E. a broken fixture judges NOTHING, and says so ─────────────────────────
print('\n--- E. the blind lock refuses rather than judging real files ---')
wt = worktree('lock')
try:
    plant(wt, *MUTATIONS[0][1:])
    rc, out = run_tool(wt)
    ok('E1 it exits 2 -- could-not-run, not a finding and not a pass',
       rc == 2, 'rc=%d\n%s' % (rc, out[-800:]))
    ok('E2 and says nothing real was judged', 'NOTHING REAL WAS JUDGED' in out, out[-800:])
    ok('E3 and it did NOT go on to scan the tree', 'files scanned' not in out, out[-800:])
    ok('E4 and it names which fixture disagreed', 'a clean regex literal' in out, out[-800:])
finally:
    drop(wt)

# ── F. the known-benign real occurrence stays silent ────────────────────────
print('\n--- F. the deliberate CSV BOM in sairnroofing.html ---')
rc, out = run_tool(REPO, os.path.join(REPO, 'sairnroofing.html'))
ok('F1 a correct BOM written into a CSV is not a finding', rc == 0,
   'rc=%d\n%s' % (rc, out[-600:]))
ok('F2 but it is still COUNTED, so it is not invisible to the reader either',
   'ZWNBSP / BOM' in out, out[-600:])

print('')
if FAIL:
    print('invisible_in_pattern: %d ARM(S) FAILED -- %s' % (len(FAIL), ', '.join(FAIL)))
    sys.exit(1)
print('invisible_in_pattern: all arms pass')
