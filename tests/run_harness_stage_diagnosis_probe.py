"""The shared harness must NAME the unstaged file when its baseline goes red.

Run: python tests/run_harness_stage_diagnosis_probe.py

Exit 0 when every arm passes, 1 otherwise.

# REQUIREMENT: when the baseline fails because the worktree is at HEAD and the
#   suite asserts something about a file THIS CLONE has changed but `stage`
#   does not carry, the harness must name that file -- and it must not name
#   files the suite never mentions, or the list becomes noise nobody reads

WHY THIS EXISTS, AND IT IS A PROCESS DEFECT RATHER THAN A CODE ONE. Two
sessions hit this hours apart on 2026-09-21/22 and made the same one-line fix
independently: cody staged `api/sd-data.js` into
`tests/session_gate_table_probe.py`, cc staged `sairnvet.html` into
`tests/sairnvet_controlled_export_probe.py`. Neither found the other's note,
because each wrote a comment beside their own call rather than a rule in the
harness. The harness's `stage` docstring already described the cause; what it
could not do is connect it to the SYMPTOM, which is a red baseline whose
failing arm is about the author's own change and therefore reads as a broken
suite.

── WHY A DIAGNOSIS AND NOT A REFUSAL ──────────────────────────────────────
The harness cannot know that a dirty file is the cause. A suite can be red
because it is genuinely red. So this prints a SUSPECT LIST and says it is a
guess, rather than refusing or auto-staging -- auto-staging would silently
change what a control measures, which is the one thing a control must not do.

── AND THE NEGATIVE ARM IS THE ONE THAT KEEPS IT USEFUL ───────────────────
A diagnostic that names every dirty file in the repo is one people learn to
skip. Arm 3 dirties a file the suite never mentions and requires that it does
NOT appear.
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sabotage_harness as H                                    # noqa: E402

REPO = H.REPO
fails = 0


def arm(name, cond, detail=''):
    global fails
    print(('ok    ' if cond else 'FAIL  ') + name)
    if not cond:
        fails += 1
        if detail:
            print('        ' + detail.replace('\n', '\n        '))


# ── A fake clone, so nothing here depends on what this repo is doing now ──
# _unstaged_suspects() reads `git status` and the suite's text out of H.REPO,
# so H.REPO is pointed at a throwaway git repo for the duration. Driving it
# against the real clone would make every arm depend on whatever happens to be
# uncommitted at the moment somebody runs this.
def with_fake_repo(files, dirty, fn):
    tmp = tempfile.mkdtemp(prefix='cc-stage-diag-')
    try:
        subprocess.run(['git', 'init', '-q', tmp], check=True,
                       capture_output=True)
        for rel, body in files.items():
            p = os.path.join(tmp, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            io.open(p, 'w', encoding='utf-8', newline='\n').write(body)
        subprocess.run(['git', '-C', tmp, 'add', '-A'], check=True,
                       capture_output=True)
        subprocess.run(['git', '-C', tmp, '-c', 'user.email=t@t', '-c',
                        'user.name=t', 'commit', '-q', '-m', 'base'],
                       check=True, capture_output=True)
        for rel, body in dirty.items():
            io.open(os.path.join(tmp, rel), 'w', encoding='utf-8',
                    newline='\n').write(body)
        saved = H.REPO
        H.REPO = tmp
        try:
            return fn(tmp)
        finally:
            H.REPO = saved
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


SUITE = 'tests/my_suite.js'
SUITE_BODY = ("// asserts the preamble in sairnvet.html and the gate in "
              "api/sd-data.js\nrequire('../sairnvet.html');\n")
FILES = {
    SUITE: SUITE_BODY,
    'sairnvet.html': 'old exporter\n',
    'api/sd-data.js': 'old gate\n',
    'docs/UNRELATED.md': 'nothing the suite mentions\n',
}

print('\n1. the file the suite NAMES and `stage` does not carry')
res = with_fake_repo(FILES, {'sairnvet.html': 'new exporter\n'},
                     lambda _t: H._unstaged_suspects(SUITE, ()))
arm('a dirty file the suite mentions is named', res == ['sairnvet.html'], repr(res))

print('\n2. ...and staging it takes it off the list')
res = with_fake_repo(FILES, {'sairnvet.html': 'new exporter\n'},
                     lambda _t: H._unstaged_suspects(SUITE, ('sairnvet.html',)))
arm('a STAGED dirty file is not reported', res == [], repr(res))

print('\n3. the negative arm -- a diagnostic that names everything is ignored')
res = with_fake_repo(FILES, {'docs/UNRELATED.md': 'changed\n'},
                     lambda _t: H._unstaged_suspects(SUITE, ()))
arm('a dirty file the suite never mentions is NOT named', res == [], repr(res))

print('\n4. both halves at once, which is the real shape')
res = with_fake_repo(FILES, {'sairnvet.html': 'new\n',
                             'api/sd-data.js': 'new\n',
                             'docs/UNRELATED.md': 'new\n'},
                     lambda _t: H._unstaged_suspects(SUITE, ()))
arm('two named files are both reported and the unmentioned one is not',
    res == ['api/sd-data.js', 'sairnvet.html'], repr(res))

print('\n5. a clean clone produces no list at all')
res = with_fake_repo(FILES, {}, lambda _t: H._unstaged_suspects(SUITE, ()))
arm('nothing dirty means nothing suspected', res == [], repr(res))

print('\n6. the SUITE itself is never suspected -- it is always staged')
res = with_fake_repo(FILES, {SUITE: SUITE_BODY + '// edited\n'},
                     lambda _t: H._unstaged_suspects(SUITE, ()))
arm('a dirty SUITE is not in its own suspect list', res == [], repr(res))

print('\n7. it cannot throw on a repo it cannot read')
try:
    saved = H.REPO
    H.REPO = os.path.join(tempfile.gettempdir(), 'cc-no-such-repo-xyz')
    res = H._unstaged_suspects(SUITE, ())
    ok = isinstance(res, list)
finally:
    H.REPO = saved
arm('an unreadable repo returns a list, never an exception', ok, repr(res))

# ── 8. END TO END, because the arms above test a helper and the thing that
#      matters is what a session SEES when the baseline goes red ───────────
print('\n8. end to end -- the message a session actually reads')
FIXDIR = os.path.join('tests', 'fixtures')
FIXSUITE = os.path.join(FIXDIR, 'harness_stage_diag_suite.js')
FIXSRC = os.path.join(FIXDIR, 'harness_stage_diag_src.js')
made = []
try:
    os.makedirs(os.path.join(REPO, FIXDIR), exist_ok=True)
    for rel, body in (
            (FIXSRC, "module.exports = { answer: 'OLD' };\n"),
            (FIXSUITE,
             "const s = require('./harness_stage_diag_src.js');\n"
             "if (s.answer !== 'NEW') { console.log('FAIL wrong answer'); "
             "process.exit(1); }\nconsole.log('ok');\n")):
        p = os.path.join(REPO, rel)
        if not os.path.exists(p):
            made.append(p)
        io.open(p, 'w', encoding='utf-8', newline='\n').write(body)
    # The src is committed as OLD and left dirty as NEW -- exactly the shape.
    io.open(os.path.join(REPO, FIXSRC), 'w', encoding='utf-8',
            newline='\n').write("module.exports = { answer: 'NEW' };\n")
    out, real = io.StringIO(), sys.stdout
    sys.stdout = out
    try:
        code = H.run_probe(FIXSUITE, [('x', FIXSRC, 'NEW', 'OLD')],
                           title='fixture', stage=())
    finally:
        sys.stdout = real
    text = out.getvalue()
    arm('the baseline goes red, as it must when the subject is not staged',
        code == 1 and 'baseline is red' in text, 'exit %s' % code)
    arm('...and the message NAMES the unstaged subject',
        FIXSRC.replace(os.sep, '/') in text.replace(os.sep, '/'),
        'the session is told the baseline is red and left to work out why:\n'
        + text[-600:])
    arm('...and says the list is a guess rather than a verdict',
        'If it is not, this list is noise' in text, text[-400:])
finally:
    for p in made:
        try:
            os.remove(p)
        except OSError:
            pass

print('\n%d failure(s)' % fails)
sys.exit(1 if fails else 0)
