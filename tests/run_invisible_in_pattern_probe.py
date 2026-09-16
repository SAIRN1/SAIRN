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


# The target is a REAL tracked file carrying a REAL regex literal. Chosen for
# being stable and unrelated to this tool, so a rot here is a rot in the anchor
# rather than a redesign of the subject.
TARGET = 'api/_lib/accounting-connector.js'
ANCHOR = r"/^\d{4}-\d{2}-\d{2}$/"
TOOL = 'tools/invisible_in_pattern_check.py'

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
    plant(wt, TARGET, ANCHOR,
          ANCHOR + "\n_PROBE_RE = 'x' if False else None\n_PROBE = (0,)\n"
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
    plant(wt, TARGET, ANCHOR,
          ANCHOR + "\n_PROBE_PATTERN = [/de%slete/i] if False else None\n" % BS)
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
    plant(wt, TOOL,
          "    ('a clean regex literal', 'f.js',\n     'assert.ok(/delete/i.test(src));', False),",
          "    ('a clean regex literal', 'f.js',\n     'assert.ok(/delete/i.test(src));', True),")
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
