r"""tests/run_hook_integrity_probe.py -- control pair for
tools/hook_integrity_check.py.

    python tests/run_hook_integrity_probe.py

CONTROLS_FOR = ['tools/hook_integrity_check.py']
LIVE_PROBE_CLASS = 'FIXTURE'

EVERY KNOWN-BAD ARM RUNS AGAINST A REAL GIT REPOSITORY, built and deleted here.
The check's whole substance is a three-way comparison between a working tree, a
commit and a manifest, so a fixture without real commits would exercise one third
of it and the two thirds that matter most are the ones a mock cannot supply.

THE THREE KNOWN-BADS THE TOOL EXISTS FOR, each of which must make it FAIL:

  a hook edited to a no-op          -- `exit 0` is a pass and a lobotomy alike
  a wiring line removed             -- the tool stays on disk, correct, unrun
  core.hooksPath pointed elsewhere  -- every file byte-perfect, every gate off

AND THE FALSE POSITIVE THAT THE FIRST REAL RUN ACTUALLY PRODUCED, which is here
because it is the failure mode that gets a check switched off rather than fixed:
a CRLF working tree against an LF blob is NOT drift. `git show` emits the stored
blob at LF while the working tree may hold CRLF, and this platform has recorded
three separate false alarms from exactly that in one session. The first version of
the check reported three tools as drifted in BOTH directions on a clean tree.
"""
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN = 0, 1, 2

TOOL = os.path.join(REPO, 'tools', 'hook_integrity_check.py')
if not os.path.isfile(TOOL):
    print('COULD NOT RUN: tools/hook_integrity_check.py is not on disk. This '
          'control tested nothing, which is a third state and not a pass.')
    sys.exit(EXIT_COULD_NOT_RUN)

NL = chr(10)
CR = chr(13)
passed = failed = 0


def ok(cond, label, detail=''):
    global passed, failed
    if cond:
        passed += 1
        print('  ok   %s' % label)
    else:
        failed += 1
        print('  FAIL %s' % label)
        if detail:
            print('       %s' % str(detail)[:600])


def rmtree(path):
    def onerror(fn, p, exc):
        try:
            os.chmod(p, stat.S_IWRITE)
            fn(p)
        except Exception:
            pass
    shutil.rmtree(path, onerror=onerror)


def g(cwd, *args):
    return subprocess.run(
        ['git', '-c', 'user.name=probe', '-c', 'user.email=probe@local',
         '-c', 'commit.gpgsign=false'] + list(args),
        cwd=cwd, capture_output=True, text=True, encoding='utf-8',
        errors='replace')


def write(path, text, crlf=False):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if crlf:
        text = text.replace(NL, CR + NL)
    io.open(path, 'w', encoding='utf-8', newline='').write(text)


SETTINGS = {
    'hooks': {
        'PreToolUse': [
            {'matcher': 'Bash', 'hooks': [
                {'type': 'command', 'command': 'python tools/gate_one.py'},
                {'type': 'command', 'command': 'python tools/gate_two.py'},
            ]},
        ],
        'SessionStart': [
            {'hooks': [{'type': 'command', 'command': 'python tools/start.py'}]},
        ],
    }
}


def build_fixture(crlf_tool=False):
    """A real repository with hooks, wiring, tools, a commit and a manifest."""
    d = tempfile.mkdtemp(prefix='sairn_hookint_')
    g(d, 'init', '-q', '-b', 'main')
    g(d, 'config', 'core.hooksPath', '.githooks')

    write(os.path.join(d, '.githooks', 'pre-push'),
          '#!/bin/sh' + NL + 'python tools/gate_one.py || exit 1' + NL)
    write(os.path.join(d, '.githooks', 'pre-commit'),
          '#!/bin/sh' + NL + 'python tools/scanner.py || exit 1' + NL)
    for t in ('gate_one.py', 'gate_two.py', 'start.py', 'scanner.py'):
        write(os.path.join(d, 'tools', t),
              '# ' + t + NL + 'print("real work")' + NL, crlf=crlf_tool)
    write(os.path.join(d, '.claude', 'settings.json'),
          json.dumps(SETTINGS, indent=1) + NL)
    # The checker itself has to live in the fixture: it hashes SELF_REL out of
    # the repo it is pointed at, and a fixture without it would exercise the
    # covers-itself path against an absent file rather than a present one.
    shutil.copyfile(TOOL, os.path.join(d, 'tools', 'hook_integrity_check.py'))
    shutil.copyfile(os.path.join(REPO, 'tools', 'checker_kit.py'),
                    os.path.join(d, 'tools', 'checker_kit.py'))
    os.makedirs(os.path.join(d, 'docs'), exist_ok=True)

    g(d, 'add', '.')
    g(d, 'commit', '-q', '-m', 'fixture')
    return d


def run(repo, *args):
    p = subprocess.run([sys.executable,
                        os.path.join(repo, 'tools', 'hook_integrity_check.py'),
                        '--repo', repo] + list(args),
                       cwd=repo, capture_output=True, text=True,
                       encoding='utf-8', errors='replace',
                       env=dict(os.environ, PYTHONIOENCODING='utf-8'))
    return p.returncode, (p.stdout or '') + (p.stderr or '')


def armed_fixture(crlf_tool=False):
    """A fixture whose manifest is generated AND committed, so it is clean."""
    d = build_fixture(crlf_tool=crlf_tool)
    run(d, '--regenerate')
    run(d, '--regenerate')          # converge the self hash, as the tool says
    g(d, 'add', '.')
    g(d, 'commit', '-q', '-m', 'manifest')
    return d


print('CONTROL PAIR -- tools/hook_integrity_check.py' + NL)

# ══ BASELINE ═══════════════════════════════════════════════════════════════
print('BASELINE -- an armed fixture is SILENT')
d = armed_fixture()
try:
    rc, out = run(d)
    ok(rc == EXIT_CLEAN,
       'THE ARM THAT MATTERS MOST: a repository whose manifest was generated and '
       'committed is clean (exit %d). A check that fires here is one nobody '
       'runs, and then it is not running on the day a hook is edited.' % rc,
       out[-700:])
    ok('covers itself: yes' in out,
       'and it reports that it covers ITSELF -- a manifest checker outside its '
       'own manifest is one edit away from blessing everything', out[-300:])
    ok('DERIVED from the sources' in out,
       'and says the tool list is DERIVED, so a hook invoking something new is '
       'covered without this file being edited', out[-300:])
    ok('WHAT A CLEAN RUN DOES NOT SAY' in out,
       'and a clean run states its own limit: unchanged is not correct',
       out[-300:])

    # ── THE FALSE POSITIVE THE FIRST REAL RUN PRODUCED ────────────────────
    print(NL + 'DIRECTION -- a CRLF working tree is NOT drift')
    for t in ('gate_one.py', 'scanner.py'):
        p = os.path.join(d, 'tools', t)
        body = io.open(p, encoding='utf-8', newline='').read()
        write(p, body.replace(CR + NL, NL), crlf=True)
    rc, out = run(d)
    ok(rc == EXIT_CLEAN,
       'two tools rewritten with CRLF endings and NOTHING is reported (exit %d). '
       '`git show` emits the LF blob while the tree holds CRLF, and this platform '
       'has recorded three false alarms from that in one session. The first '
       'version of this check reported three tools as drifted in BOTH directions '
       'on a clean tree.' % rc, out[-700:])
finally:
    rmtree(d)

# ══ KNOWN-BAD 1 -- A HOOK EDITED TO A NO-OP ════════════════════════════════
print(NL + 'KNOWN-BAD 1 -- a hook edited to a no-op')
d = armed_fixture()
try:
    write(os.path.join(d, '.githooks', 'pre-push'), '#!/bin/sh' + NL + 'exit 0' + NL)
    rc, out = run(d)
    ok(rc == EXIT_FINDING,
       'an UNCOMMITTED lobotomy is reported (exit %d)' % rc, out[-600:])
    ok('pre-push' in out and 'WORKING TREE AND HEAD' in out,
       'and it names the hook and says the difference is uncommitted', out[-500:])

    g(d, 'add', '.')
    g(d, 'commit', '-q', '-m', 'silently neuter the push gate')
    rc, out = run(d)
    ok(rc == EXIT_FINDING,
       'AND COMMITTING IT DOES NOT MAKE IT CLEAN (exit %d) -- this is the case a '
       'tree-vs-HEAD check alone would bless, because after the commit the tree '
       'and HEAD agree perfectly' % rc, out[-600:])
    ok('MANIFEST WAS NOT REGENERATED' in out,
       'and it names the manifest as the expectation that did not move',
       out[-500:])
finally:
    rmtree(d)

# ══ KNOWN-BAD 2 -- A WIRING LINE REMOVED ═══════════════════════════════════
print(NL + 'KNOWN-BAD 2 -- a wiring line removed from settings.json')
d = armed_fixture()
try:
    doc = json.loads(io.open(os.path.join(d, '.claude', 'settings.json'),
                             encoding='utf-8').read())
    removed = doc['hooks']['PreToolUse'][0]['hooks'].pop(0)
    write(os.path.join(d, '.claude', 'settings.json'),
          json.dumps(doc, indent=1) + NL)
    rc, out = run(d)
    ok(rc == EXIT_FINDING,
       'removing one PreToolUse command is reported (exit %d). The tool is still '
       'on disk and still correct; it simply never runs, which is the quietest '
       'failure available' % rc, out[-600:])
    ok('WIRING PreToolUse CHANGED' in out and 'REMOVED' in out,
       'and it names the event AND prints the removed line, so a reader does not '
       'have to diff to learn which control went dark', out[-600:])
    ok('gate_one.py' in out,
       'and the removed line it prints is the real one (%s)'
       % (removed.get('command')), out[-600:])
finally:
    rmtree(d)

# ══ KNOWN-BAD 3a -- A FRESH CLONE, WHICH ARMS NOTHING ══════════════════════
# THE STATE EVERY CLONE OF THIS REPOSITORY STARTS IN. core.hooksPath is local git
# config, not tracked content, so cloning installs all four hook files
# byte-perfect and git reads NONE of them. Found on 2026-09-29 by pointing this
# check at a real clone of origin/main. The fixture below is that clone: every
# file present, every hash matching, nothing armed.
print(NL + 'KNOWN-BAD 3a -- a FRESH CLONE arms nothing and must FAIL')
d = armed_fixture()
try:
    g(d, 'config', '--unset', 'core.hooksPath')
    rc, out = run(d)
    ok(rc == EXIT_FINDING,
       'an UNARMED clone is a FAILURE, not a pass (exit %d). Every hook file is '
       'present and every hash matches -- they are simply not armed, which is '
       'the failure with the least evidence on it' % rc, out[-700:])
    ok('NOT SET' in out.upper() and 'NO HOOKS AT ALL' in out.upper(),
       'and it says GIT IS RUNNING NO HOOKS AT ALL rather than reporting a path '
       'mismatch, which is a different cause with a different fix', out[-700:])
    ok('install_git_hooks.py' in out,
       'and it names the exact command that arms them -- the first version of '
       'this finding printed the REPOINTED sentence for both causes and would '
       'have sent a reader hunting a malicious change when nobody had run the '
       'installer', out[-700:])
    # AND THE CONTENT HALF MUST STILL BE CLEAN, so the finding is the arming and
    # nothing else. A dozen mismatches would bury the one that matters.
    ok(out.count('!') <= 3,
       'and it is the ONLY finding -- the content half stays clean, so the '
       'signal is the arming rather than noise around it', out[-700:])
finally:
    rmtree(d)

# ══ KNOWN-BAD 3 -- core.hooksPath POINTED ELSEWHERE ════════════════════════
print(NL + 'KNOWN-BAD 3 -- core.hooksPath pointed somewhere else')
d = armed_fixture()
try:
    os.makedirs(os.path.join(d, 'elsewhere'), exist_ok=True)
    g(d, 'config', 'core.hooksPath', 'elsewhere')
    rc, out = run(d)
    ok(rc == EXIT_FINDING,
       'repointing core.hooksPath is reported (exit %d) even though EVERY HOOK '
       'FILE IS BYTE-PERFECT. Nothing in any diff shows this and all four gates '
       'are off at once' % rc, out[-600:])
    ok('core.hooksPath' in out and 'least evidence' in out,
       'and it says why this one is the worst of the three: the files are intact, '
       'so there is nothing to notice', out[-600:])
finally:
    rmtree(d)

# ══ FAIL CLOSED ════════════════════════════════════════════════════════════
print(NL + 'FAIL CLOSED -- unknown is never a pass')
d = armed_fixture()
try:
    man = os.path.join(d, 'docs', 'hook-manifest.json')
    os.remove(man)
    rc, out = run(d)
    ok(rc == EXIT_COULD_NOT_RUN,
       'NO MANIFEST is exit 2, not 0 (got %d) -- with nothing to compare against, '
       'a check reports clean for every possible state of the hooks' % rc,
       out[-500:])

    write(man, 'not json at all' + NL)
    rc, out = run(d)
    ok(rc == EXIT_COULD_NOT_RUN,
       'an UNPARSEABLE manifest is exit 2 (got %d)' % rc, out[-500:])

    run(d, '--regenerate')
    run(d, '--regenerate')
    os.remove(os.path.join(d, '.claude', 'settings.json'))
    rc, out = run(d)
    ok(rc == EXIT_COULD_NOT_RUN,
       'and an ABSENT settings.json is exit 2 (got %d) -- the wiring is half the '
       'control, and an unreadable half is not a clean whole' % rc, out[-500:])
finally:
    rmtree(d)

# ══ THE SELF-COVERAGE HOLE, ASSERTED AS A COULD-NOT-CHECK ══════════════════
print(NL + 'DIRECTION -- a manifest with no self hash says so')
d = armed_fixture()
try:
    man = os.path.join(d, 'docs', 'hook-manifest.json')
    doc = json.loads(io.open(man, encoding='utf-8').read())
    doc.pop('self', None)
    write(man, json.dumps(doc, indent=1) + NL)
    rc, out = run(d)
    ok(rc == EXIT_COULD_NOT_RUN,
       'a manifest that does not record the checker\'s own hash is COULD NOT RUN '
       '(exit %d), not a quiet clean' % rc, out[-500:])
    ok('NOT covering itself' in out and 'covers itself: NO' in out,
       'and it says so in both the summary and the findings', out[-600:])
finally:
    rmtree(d)

# ══ REGENERATE NAMES EVERY CHANGE ══════════════════════════════════════════
print(NL + 'DIRECTION -- --regenerate names each change and never runs silently')
d = armed_fixture()
try:
    write(os.path.join(d, '.githooks', 'pre-commit'),
          '#!/bin/sh' + NL + 'python tools/scanner.py --strict || exit 1' + NL)
    rc, out = run(d, '--regenerate')
    ok(rc == EXIT_CLEAN, '--regenerate exits 0 (got %d)' % rc, out[-400:])
    ok('pre-commit' in out and '->' in out,
       'and it NAMES the hook whose hash moved, with the old and new values -- '
       'the manifest changing without a human seeing what changed would make it '
       'a rubber stamp', out[-500:])
    rc, out = run(d, '--regenerate')
    ok('nothing moved' in out,
       'and a second run on an unchanged tree says nothing moved rather than '
       'printing an empty change list', out[-400:])
finally:
    rmtree(d)

# ══ THE REAL REPO, reported not asserted ═══════════════════════════════════
print(NL + 'THE REAL CLONE -- reported, not asserted')
p = subprocess.run([sys.executable, TOOL], cwd=REPO, capture_output=True,
                   text=True, encoding='utf-8', errors='replace',
                   env=dict(os.environ, PYTHONIOENCODING='utf-8'))
print('  --   this clone right now: exit %d. NOT AN ASSERTION -- an uncommitted '
      'hook edit is a legitimate state mid-session, and asserting clean here '
      'would make the control red for a reason that is not a defect.'
      % p.returncode)
ok(p.returncode in (EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN),
   'it exits one of the three defined codes (got %d)' % p.returncode,
   (p.stdout or '')[-400:])

print(NL + '%d passed, %d failed' % (passed, failed))
sys.exit(EXIT_FINDING if failed else EXIT_CLEAN)
