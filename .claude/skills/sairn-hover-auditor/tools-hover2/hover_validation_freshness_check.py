#!/usr/bin/env python
"""hover_validation_freshness_check.py (hover2's own build) -- item 4 of the
2026-09-29 six-item paste: "Both tools drifted again after your
revalidation." Prior sweeps (seq 306, seq 296) did this comparison by hand,
ad hoc, once. This is the reusable version, meant to be run at the START of
every rotation round from here on -- the standing step the paste asked for.

WHAT IT CHECKS: for every tool THIS instance (hover2) independently
validated in H1's ledger (tool_provenance_validations.jsonl, validator_session
== 'hover2', author_session == 'hover', reproduced == true), compare the
tool's content AS OF the recorded validation date against its CURRENT
content on disk in H1's clone. Multiple recorded events for the same tool
collapse to the LATEST one (max date, last-in-file tiebreak) -- that is the
validation whose freshness matters now.

METHOD, same as seq 306's ad hoc sweep, now fixed in code: the ledger
records a DATE only, not a time, so "as of the validation date" resolves to
the nearest commit in H1's own hover-audit-log git repo at or before
23:59:59 on that date for that path. sha256 of that commit's blob content
is compared against sha256 of the CURRENT on-disk file (not HEAD -- the
live working tree, since that is what a caller would actually read today).
Day-granularity is a real, disclosed precision limit, not hidden.

THREE OUTCOMES PER TOOL, never two:
  UNCHANGED    -- content sha256 matches; nothing to do.
  CHANGED      -- content sha256 differs; due for revalidation.
  COULD NOT DETERMINE -- no commit found at/before the validation date for
                  this path (never committed by then, or the tool was
                  renamed), or the current file is missing. NEVER folded
                  into UNCHANGED -- an unfound historical state is not
                  evidence of no change, and a comparator that treats it
                  that way is exactly the known-bad control below.

FAIL CLOSED, PR SS1.11: an unreadable ledger, or H1's directory not being a
git repo, is COULD NOT RUN (exit 2) -- never reported as "nothing changed".

Exit: 0 all UNCHANGED; 1 something CHANGED or COULD NOT DETERMINE (due for
attention); 2 COULD NOT RUN.

STANDING-STEP DESIGN, the second half of item 4: this tool is meant to run
once at the start of every rotation round, before the round's --rotation-
batch entry is logged. THIS IS NOT MECHANICALLY GATED THE WAY ITEM 2's
lint-token requirement is -- item 2 said "design a mechanical marker";
item 4 said "make it a standing step" and "state how a round that skips it
would show in your log", which is a lighter, descriptive ask, not a refusal
gate. The honest answer to that question: a round that skips this step
shows in the log as a --rotation-batch (or plain rotation) check entry
whose immediately preceding sibling entries in this same log do NOT include
a hover_validation_freshness_check.py run for that round -- visible by
absence on a `--tail`/sequential read, the same way an un-synthesized
background Agent launch was visible by absence before the launch-note
discipline was added (see SKILL.md, "A real gap found on direct
instruction, 2026-09-17"). This is a WEAKER guarantee than item 2's
mechanical refusal -- it can be missed by a reader who does not check for
it -- and that asymmetry is disclosed here rather than overstated as
equivalent enforcement.

Run:
  python hover_validation_freshness_check.py            # report + revalidation-due list
  python hover_validation_freshness_check.py --selftest # fixtures only, no real ledger/git touched
"""
import hashlib
import io
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HOVER1_DIR = os.environ.get(
    'HOVER1_AUDIT_LOG_DIR',
    r'C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-hover\hover-audit-log')
LEDGER_NAME = 'tool_provenance_validations.jsonl'
MY_SESSION = 'hover2'
OTHER_AUTHOR = 'hover'


def _sha256_bytes(data):
    """CRLF-normalized before hashing -- PR primer's own standing rule: 'A
    CRLF-vs-LF difference is not drift.' Git stores blobs LF-internal and
    converts on checkout per core.autocrlf; comparing a checked-out working
    file's raw bytes against `git show`'s blob output would otherwise read
    every line-ending-only checkout as CHANGED. Normalize both sides the
    same way before hashing, so a real content change is what's left."""
    return hashlib.sha256(data.replace(b'\r\n', b'\n')).hexdigest()


def _run(cmd, cwd):
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, timeout=30)
    except Exception as exc:
        return None, 'could not run %r: %s' % (cmd, exc)
    if p.returncode != 0:
        return None, (p.stderr or b'').decode('utf-8', 'replace').strip()
    return p.stdout, None


def nearest_commit_at_or_before(repo_dir, path, date_str):
    """SHA of the newest commit touching `path` at or before 23:59:59 on
    date_str, or None if none exists. date_str is 'YYYY-MM-DD'."""
    out, err = _run(
        ['git', 'log', '--until=%sT23:59:59' % date_str, '-1',
         '--format=%H', '--', path],
        repo_dir)
    if out is None:
        return None, err
    sha = out.decode('utf-8', 'replace').strip()
    return (sha or None), None


def blob_sha256_at_commit(repo_dir, commit, path):
    out, err = _run(['git', 'show', '%s:%s' % (commit, path)], repo_dir)
    if out is None:
        return None, err
    return _sha256_bytes(out), None


def current_file_sha256(repo_dir, path):
    full = os.path.join(repo_dir, path)
    if not os.path.isfile(full):
        return None, 'no such file on disk: %s' % full
    with open(full, 'rb') as f:
        return _sha256_bytes(f.read()), None


def latest_events_by_tool(rows):
    """{tool: event} keeping the LATEST recorded validation per tool (by
    date, last-in-file tiebreak), restricted to hover2-validating-hover
    reproduced=true events."""
    by_tool = {}
    for r in rows:
        if r.get('validator_session') != MY_SESSION:
            continue
        if r.get('author_session') != OTHER_AUTHOR:
            continue
        if r.get('reproduced') is not True:
            continue
        tool = r.get('tool')
        date = r.get('date') or ''
        if tool is None:
            continue
        prev = by_tool.get(tool)
        if prev is None or date >= prev.get('date', ''):
            by_tool[tool] = r
    return by_tool


def check_one(repo_dir, tool, date_str):
    commit, err = nearest_commit_at_or_before(repo_dir, tool, date_str)
    if err:
        return 'COULD_NOT_RUN', err
    if commit is None:
        return 'COULD_NOT_DETERMINE', 'no commit found at/before %s for %s' % (date_str, tool)
    hist_sha, err = blob_sha256_at_commit(repo_dir, commit, tool)
    if err:
        return 'COULD_NOT_DETERMINE', 'commit %s found but content unreadable: %s' % (commit, err)
    cur_sha, err = current_file_sha256(repo_dir, tool)
    if err:
        return 'COULD_NOT_DETERMINE', err
    if hist_sha == cur_sha:
        return 'UNCHANGED', 'validated %s (commit %s), still %s' % (date_str, commit[:8], cur_sha[:12])
    return 'CHANGED', 'validated %s (commit %s = %s), now %s' % (
        date_str, commit[:8], hist_sha[:12], cur_sha[:12])


# A known-bad comparator, kept only as a fixture for the selftest control
# below: treats "no historical commit found" as UNCHANGED instead of
# COULD_NOT_DETERMINE. This is exactly the failure this tool exists to
# refuse -- an unfound historical state is not evidence of no change.
def _broken_check_one(repo_dir, tool, date_str):
    commit, err = nearest_commit_at_or_before(repo_dir, tool, date_str)
    if err or commit is None:
        return 'UNCHANGED', 'BROKEN: no commit found, defaulting to unchanged'
    hist_sha, _ = blob_sha256_at_commit(repo_dir, commit, tool)
    cur_sha, _ = current_file_sha256(repo_dir, tool)
    return ('UNCHANGED' if hist_sha == cur_sha else 'CHANGED'), ''


def report(hover1_dir=None, ledger_path=None):
    hover1_dir = hover1_dir or HOVER1_DIR
    ledger_path = ledger_path or os.path.join(hover1_dir, LEDGER_NAME)
    if not os.path.isdir(hover1_dir):
        print('COULD NOT RUN: H1 directory not found: %s' % hover1_dir)
        return 2
    # --show-toplevel, not --is-inside-work-tree: the latter answers TRUE
    # for any directory nested under SOME ancestor repo (confirmed live --
    # the whole AppData\Local\Temp tree reads as "inside a work tree" on
    # this machine), which would silently pass a directory that is not
    # itself a repo at all. Require the toplevel to equal hover1_dir itself.
    out, err = _run(['git', 'rev-parse', '--show-toplevel'], hover1_dir)
    if out is None:
        print('COULD NOT RUN: %s is not a git repo (%s)' % (hover1_dir, err))
        return 2
    toplevel = os.path.normcase(os.path.normpath(out.decode().strip()))
    target = os.path.normcase(os.path.normpath(hover1_dir))
    if toplevel != target:
        print('COULD NOT RUN: %s is not itself a git repo root (nearest '
              'repo root is %s)' % (hover1_dir, toplevel))
        return 2
    if not os.path.isfile(ledger_path):
        print('COULD NOT RUN: ledger not found: %s' % ledger_path)
        return 2
    rows = []
    with io.open(ledger_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                print('COULD NOT RUN: unparseable ledger line: %s' % exc)
                return 2

    by_tool = latest_events_by_tool(rows)
    if not by_tool:
        print('no hover2-validated-hover-authored reproduced=true events found')
        return 0

    changed = []
    could_not = []
    unchanged = []
    for tool, ev in sorted(by_tool.items()):
        status, detail = check_one(hover1_dir, tool, ev.get('date', ''))
        if status == 'COULD_NOT_RUN':
            print('COULD NOT RUN: %s -- %s' % (tool, detail))
            return 2
        line = '  %-40s %-20s %s' % (tool, status, detail)
        print(line)
        if status == 'CHANGED':
            changed.append(tool)
        elif status == 'COULD_NOT_DETERMINE':
            could_not.append(tool)
        else:
            unchanged.append(tool)

    print('')
    print('%d unchanged, %d CHANGED (due for revalidation), %d COULD NOT DETERMINE'
          % (len(unchanged), len(changed), len(could_not)))
    if changed or could_not:
        return 1
    return 0


def selftest():
    import shutil
    import tempfile
    bad = []
    total = [0]

    def ck(name, cond):
        total[0] += 1
        if not cond:
            bad.append(name)
        print('  %s   %s' % ('ok' if cond else 'FAIL', name))

    tmp = tempfile.mkdtemp(prefix='hvfc_')
    try:
        subprocess.run(['git', 'init', '-q'], cwd=tmp, check=True)
        subprocess.run(['git', 'config', 'user.email', 'x@x.com'], cwd=tmp, check=True)
        subprocess.run(['git', 'config', 'user.name', 'x'], cwd=tmp, check=True)

        def commit_file(name, content, date):
            with open(os.path.join(tmp, name), 'w', encoding='utf-8') as f:
                f.write(content)
            subprocess.run(['git', 'add', name], cwd=tmp, check=True)
            env = dict(os.environ,
                       GIT_AUTHOR_DATE='%sT12:00:00' % date,
                       GIT_COMMITTER_DATE='%sT12:00:00' % date)
            subprocess.run(['git', 'commit', '-q', '-m', 'c %s' % date],
                            cwd=tmp, env=env, check=True)

        commit_file('a.py', 'version one\n', '2026-09-01')
        commit_file('a.py', 'version two\n', '2026-09-15')
        # current on-disk content == the 2026-09-15 commit -- UNCHANGED case
        # (a.py's live content already equals its latest committed version)

        st, detail = check_one(tmp, 'a.py', '2026-09-20')
        ck('validated after the last real change reads UNCHANGED', st == 'UNCHANGED')

        st, detail = check_one(tmp, 'a.py', '2026-09-05')
        ck('validated BEFORE a later real change reads CHANGED', st == 'CHANGED')

        st, detail = check_one(tmp, 'never_existed.py', '2026-09-20')
        ck('a path never committed by the validation date reads COULD NOT '
           'DETERMINE, never UNCHANGED', st == 'COULD_NOT_DETERMINE')

        # KNOWN-BAD CONTROL: the broken comparator must disagree with the
        # real one on exactly the never-existed case.
        bst, _ = _broken_check_one(tmp, 'never_existed.py', '2026-09-20')
        ck('KNOWN-BAD CONTROL: a comparator defaulting "no commit found" to '
           'UNCHANGED disagrees with the real COULD_NOT_DETERMINE verdict',
           bst == 'UNCHANGED' and st == 'COULD_NOT_DETERMINE')

        # Mutate current on-disk content without a new commit -- simulates
        # a real uncommitted local edit since the validation was recorded.
        with open(os.path.join(tmp, 'a.py'), 'w', encoding='utf-8') as f:
            f.write('version two but hand-edited after validation\n')
        st, detail = check_one(tmp, 'a.py', '2026-09-20')
        ck('an uncommitted on-disk edit since the validation date reads '
           'CHANGED against the live file, not just against HEAD', st == 'CHANGED')

        # latest_events_by_tool: two events for the same tool, keep the LATEST.
        rows = [
            {'validator_session': 'hover2', 'author_session': 'hover',
             'reproduced': True, 'tool': 'a.py', 'date': '2026-09-01'},
            {'validator_session': 'hover2', 'author_session': 'hover',
             'reproduced': True, 'tool': 'a.py', 'date': '2026-09-15'},
        ]
        by_tool = latest_events_by_tool(rows)
        ck('latest_events_by_tool(): two events for one tool keep the LATER date',
           by_tool['a.py']['date'] == '2026-09-15')

        rows2 = rows + [
            {'validator_session': 'hover', 'author_session': 'hover2',
             'reproduced': True, 'tool': 'b.py', 'date': '2026-09-20'},
            {'validator_session': 'hover2', 'author_session': 'hover',
             'reproduced': False, 'tool': 'c.py', 'date': '2026-09-20'},
            {'validator_session': 'hover2', 'author_session': 'hover2',
             'reproduced': True, 'tool': 'd.py', 'date': '2026-09-20'},
        ]
        by_tool2 = latest_events_by_tool(rows2)
        ck('an event validated BY hover (not hover2) is excluded', 'b.py' not in by_tool2)
        ck('a reproduced=false event is excluded (attempted, not confirmed)',
           'c.py' not in by_tool2)
        ck('a self-validation (author==validator==hover2) is excluded',
           'd.py' not in by_tool2)
        ck('the genuine a.py event is still present', 'a.py' in by_tool2)

        # report(): COULD NOT RUN paths.
        rc = report(hover1_dir=os.path.join(tmp, 'does-not-exist'))
        ck('report(): a missing H1 directory is COULD NOT RUN (exit 2)', rc == 2)

        notgit = tempfile.mkdtemp(prefix='hvfc_notgit_')
        try:
            with open(os.path.join(notgit, LEDGER_NAME), 'w') as f:
                f.write('{}\n')
            rc = report(hover1_dir=notgit)
            ck('report(): a non-git H1 directory is COULD NOT RUN (exit 2)', rc == 2)
        finally:
            shutil.rmtree(notgit, ignore_errors=True)

        missing_ledger_dir = tempfile.mkdtemp(prefix='hvfc_noledger_')
        try:
            subprocess.run(['git', 'init', '-q'], cwd=missing_ledger_dir, check=True)
            rc = report(hover1_dir=missing_ledger_dir)
            ck('report(): a missing ledger file is COULD NOT RUN (exit 2)', rc == 2)
        finally:
            shutil.rmtree(missing_ledger_dir, ignore_errors=True)

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print('')
    if bad:
        print('%d ok, %d FAILED: %s' % (total[0] - len(bad), len(bad), bad))
        return 1
    print('%d ok, 0 failed' % total[0])
    return 0


def main(argv):
    if '--selftest' in argv:
        return selftest()
    return report()


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
