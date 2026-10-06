#!/usr/bin/env python
"""run_doc_sha_reseat_probe.py -- the control on tools/doc_sha_reseat.py.

WHY A PROBE AND NOT JUST `--fixtures`. The tool's own criteria lock proves the
SUBSTITUTION RULE: which tokens are candidates and what they become. It cannot
prove the three FILE CLASSES, because those only show up when something is
written to disk -- and on the live clone every REWRITE target happened to be
under another session's claim on the day this landed, so the real run exercised
only the PROPOSE and GENERATED paths. A tool whose write path has never
executed is not a tool anybody should wire into a git hook.

So this drives all three classes against a temporary tree, and it drives the
REFUSALS as hard as the successes:

  A. the substitution rule, re-asserted through the real CLI rather than by
     importing the predicate -- a fixture that calls the same function the
     fixtures call is one opinion, not two
  B. REWRITE class: an unheld file IS rewritten, every occurrence, inside the
     backticks only
  C. GENERATED class: the file is NOT touched and the run says REGENERATE
  D. REPORT-ONLY class: an append-only log is NOT touched even when it cites a
     moved SHA
  E. the teeth: blind the rule and the answers must collapse
"""

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import doc_sha_reseat as D                                      # noqa: E402

SUBJECT = os.path.join(REPO, 'tools', 'doc_sha_reseat.py')
OLD = 'a' * 40
NEW = 'b' * 40

_fail = []


def ok(what, cond, detail=''):
    if cond:
        print('  ok   %s' % what)
    else:
        _fail.append(what)
        print('  FAIL %s%s' % (what, ('  [%s]' % detail) if detail else ''))


def run(tmp, args, stdin=''):
    """Run the real CLI with REPO redirected at a temp tree.

    SUBPROCESS AND NOT AN IMPORT, DELIBERATELY: the thing being judged is the
    program, and `main()` called in-process would share this file's already
    imported module state. The driver re-points REPO the way the tool itself
    computes it, which is the one thing a temp tree cannot inherit.
    """
    drv = os.path.join(tmp, '_drv.py')
    io.open(drv, 'w', encoding='utf-8').write(
        'import sys\n'
        'sys.path.insert(0, %r)\n' % os.path.join(REPO, 'tools') +
        'import doc_sha_reseat as D\n'
        'D.REPO = %r\n' % tmp +
        'D.claimed_elsewhere = lambda: set(%r)\n' % (HELD,) +
        'sys.exit(D.main(%r))\n' % (args,))
    return subprocess.run([sys.executable, drv], input=stdin,
                          capture_output=True, text=True, encoding='utf-8',
                          errors='replace', cwd=tmp)


HELD = []

print('A. the substitution rule, through the module the CLI uses')
src = 'fixed in `%s` and again `%s`' % (OLD[:8], OLD[:8])
subs = D.substitutions(src, {OLD: NEW})
ok('one distinct token yields ONE substitution, not one per occurrence',
   len(subs) == 1, subs)
ok('...and applying it replaces EVERY occurrence',
   D.apply_subs(src, subs) == 'fixed in `%s` and again `%s`'
   % (NEW[:8], NEW[:8]), D.apply_subs(src, subs))
ok('an unbackticked run is not a candidate',
   D.substitutions('plain %s here' % OLD[:8], {OLD: NEW}) == [])
ok('a token must be a prefix of OLD and never the reverse',
   D.substitutions('`%s`' % (OLD[:12]), {OLD[:6]: NEW}) == [])

print('\nB. REWRITE class -- an unheld file is written, in place, backticks only')
tmp = tempfile.mkdtemp(prefix='dsr_probe_')
try:
    os.makedirs(os.path.join(tmp, 'docs'))
    idx = os.path.join(tmp, 'docs', 'SAIRN-OPEN-WORK-INDEX.md')
    body = ('| row | fixed in `%s`, see `%s` |\n'
            'and a BARE %s which must not move\n' % (OLD[:8], OLD[:8], OLD[:8]))
    io.open(idx, 'w', encoding='utf-8', newline='').write(body)
    HELD = []
    r = run(tmp, ['--post-rewrite'], stdin='%s %s\n' % (OLD, NEW))
    after = io.open(idx, encoding='utf-8').read()
    ok('exit 0 -- a post-rewrite hook never fails the operation behind it',
       r.returncode == 0, 'exit=%d %s' % (r.returncode, r.stderr[-200:]))
    ok('BOTH backticked occurrences were re-seated',
       after.count('`%s`' % NEW[:8]) == 2, after)
    ok('and the BARE occurrence was left alone -- the backtick is the rule',
       ('bare %s' % OLD[:8]).lower() in after.lower().replace('a BARE', 'bare'),
       after)
    ok('the run names the file as MODIFIED AND NOT STAGED',
       'NOT STAGED' in r.stdout, r.stdout[-300:])
    ok('...and names the old->new pair it applied',
       '%s -> %s' % (OLD[:8], NEW[:8]) in r.stdout, r.stdout[-300:])

    print('\n   B2. the same file, now HELD by another session -- PROPOSE only')
    io.open(idx, 'w', encoding='utf-8', newline='').write(body)
    HELD = ['docs/SAIRN-OPEN-WORK-INDEX.md']
    r2 = run(tmp, ['--post-rewrite'], stdin='%s %s\n' % (OLD, NEW))
    ok('the file is byte-unchanged', io.open(idx, encoding='utf-8').read()
       == body, 'file was written while another session held it')
    ok('and the run says PROPOSED, naming the live claim as the reason',
       'PROPOSED' in r2.stdout and 'LIVE CLAIM' in r2.stdout,
       r2.stdout[-300:])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print('\nC. GENERATED class -- never patched, and the run says REGENERATE')
tmp = tempfile.mkdtemp(prefix='dsr_probe_')
try:
    os.makedirs(os.path.join(tmp, 'docs'))
    gen = os.path.join(tmp, 'docs', 'traceability-matrix.md')
    body = 'generated row citing `%s`\n' % OLD[:8]
    io.open(gen, 'w', encoding='utf-8', newline='').write(body)
    HELD = []
    r = run(tmp, ['--post-rewrite'], stdin='%s %s\n' % (OLD, NEW))
    ok('the generated file is byte-unchanged',
       io.open(gen, encoding='utf-8').read() == body,
       'a generated output was patched -- the next run would discard it')
    ok('the run says REGENERATE rather than reporting a fix',
       'REGENERATE' in r.stdout, r.stdout[-300:])
    ok('...and still names the stale pair, because it means the SOURCE is '
       'stale', '%s -> %s' % (OLD[:8], NEW[:8]) in r.stdout, r.stdout[-300:])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print('\nD. REPORT-ONLY class -- an append-only log is never re-seated')
tmp = tempfile.mkdtemp(prefix='dsr_probe_')
try:
    os.makedirs(os.path.join(tmp, 'docs'))
    log = os.path.join(tmp, 'SAIRN-ACTIVE-WORK-probe.md')
    body = 'on that day I landed `%s`\n' % OLD[:8]
    io.open(log, 'w', encoding='utf-8', newline='').write(body)
    HELD = []
    r = run(tmp, ['--post-rewrite'], stdin='%s %s\n' % (OLD, NEW))
    ok('the log is byte-unchanged',
       io.open(log, encoding='utf-8').read() == body,
       'an append-only log was rewritten')
    ok('and the run lists it as REPORT-ONLY by name',
       'SAIRN-ACTIVE-WORK-probe.md' in r.stdout, r.stdout[-300:])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print('\nE. teeth -- blind the rule and these answers must collapse')
real = io.open(SUBJECT, encoding='utf-8').read()
ANCHOR = "TOKEN = re.compile(r'`([0-9a-f]{7,12})`')"
ok('the sabotage anchor is present in the subject EXACTLY ONCE, so the '
   'mutation below cannot be hitting a different line',
   real.count(ANCHOR) == 1, real.count(ANCHOR))
tmp = tempfile.mkdtemp(prefix='dsr_sab_')
try:
    os.makedirs(os.path.join(tmp, 'tools'))
    os.makedirs(os.path.join(tmp, 'docs'))
    broken = real.replace(ANCHOR, "TOKEN = re.compile(r'(ZZZZZZZ)')")
    io.open(os.path.join(tmp, 'tools', 'doc_sha_reseat.py'), 'w',
            encoding='utf-8', newline='').write(broken)
    idx = os.path.join(tmp, 'docs', 'SAIRN-OPEN-WORK-INDEX.md')
    io.open(idx, 'w', encoding='utf-8', newline='').write(
        'fixed in `%s`\n' % OLD[:8])
    drv = os.path.join(tmp, '_sab.py')
    io.open(drv, 'w', encoding='utf-8').write(
        'import sys\n'
        'sys.path.insert(0, %r)\n' % os.path.join(tmp, 'tools') +
        'import doc_sha_reseat as D\n'
        'D.REPO = %r\n' % tmp +
        'D.claimed_elsewhere = lambda: set()\n'
        "sys.exit(D.main(['--post-rewrite']))\n")
    r = subprocess.run([sys.executable, drv], input='%s %s\n' % (OLD, NEW),
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace', cwd=tmp)
    ok('the blinded tool re-seats NOTHING -- the finding really does come '
       'from the token rule and not from anywhere else',
       'RE-SEATED' not in r.stdout,
       'blinded subject still reported a re-seat: %s' % r.stdout[-300:])
    # THIS ARM WAS WRITTEN WRONG FIRST AND THE TOOL WAS RIGHT. It asserted
    # "Nothing to do", on the assumption that a blinded token rule would
    # simply find no candidates and report an empty result. What actually
    # happens is better: the tool's OWN criteria lock classifies the 12
    # hand-built fixtures first, two of them fail under the mutation, and it
    # exits 2 COULD NOT RUN with "NOTHING REAL WAS READ OR WRITTEN" before
    # touching a document. So the lock is this tool's ablation detector, and
    # an empty result is not even reachable through this mutation. The arm now
    # asserts the real behaviour -- a quiet empty answer would be the WEAKER
    # outcome and asserting it would have been an arm that passes on the worse
    # of two designs.
    ok('and it REFUSES at its own criteria lock rather than reporting an '
       'empty result -- exit 2, before any document is read',
       r.returncode == 2 and 'CRITERIA LOCK FAILED' in r.stdout
       and 'NOTHING REAL WAS READ OR WRITTEN' in r.stdout,
       'exit=%d %s' % (r.returncode, r.stdout[-200:]))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print('')
if _fail:
    print('%d failure(s)' % len(_fail))
    for f in _fail:
        print('  - %s' % f)
    sys.exit(1)
print('ALL ARMS PASS')
sys.exit(0)
