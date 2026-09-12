"""tests/run_schema_verdict_probe.py -- the never-run verdict is earned, not asserted.

    python tests/run_schema_verdict_probe.py

`tools/schema_snapshot_freshness.py` used to print both readings of an absent
table -- "never run" and "the snapshot is behind" -- and refuse to choose. On
2026-09-12 it gained the ability to choose where git can decide it: if the
CREATE statement was committed BEFORE the capture ran and the capture still
lacks the table, the snapshot-is-behind reading is excluded.

That is a verdict on 89 tables, 31 of them queried by live api/ code. A wrong
one sends somebody to run a migration that already ran, or worse, tells them a
missing table exists. So every input to it is pinned here.

THE ARM THAT MATTERS IS THE CONTROL, not the positive case. A verdict function
that returned 'never-run' unconditionally would agree with every real table in
this repo today -- all 89 genuinely resolve that way, so the live data cannot
distinguish a working rule from a stuck one. Section 4 plants the opposite case
on a throwaway git repo and demands 'undecidable'.

THIS PROBE EXISTS BECAUSE THE FIRST VERSION OF THE FEATURE WAS WRONG AND SAID
SO QUIETLY. `_parse_stamp` required a four-digit UTC offset; the capture stamps
a two-digit one (`+00`). Every stamp parsed as None, every table came back
"no usable date", and the tool printed 31 UNDECIDABLE lines -- which is exactly
what the OLD tool printed, so the regression was invisible in the shape of the
output. Section 1 is a permanent guard on that.
"""
import io
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
import schema_snapshot_freshness as S      # noqa: E402

fails = 0


def check(label, actual, expected):
    global fails
    if actual == expected:
        print('  PASS  %s' % label)
        return True
    fails += 1
    print('  FAIL  %s\n          expected %r\n          actual   %r' % (label, expected, actual))
    return False


# ── 1. STAMP PARSING, both real formats ────────────────────────────────────
print('1. stamp parsing')
cap = S._parse_stamp('2026-09-11 15:42:46.942345+00')
check('the capture format parses at all -- the bug that made every verdict undecidable',
      cap is not None, True)
check('and it parses to the right UTC instant',
      cap.strftime('%Y-%m-%d %H:%M:%S') if cap else None, '2026-09-11 15:42:46')
git_fmt = S._parse_stamp('2026-09-11T11:42:46-04:00')
check("git's iso-strict format parses too", git_fmt is not None, True)
check('OFFSETS ARE APPLIED, not ignored -- 11:42 in -04:00 IS 15:42 UTC, and a '
      'naive string compare of the two would be wrong by four hours',
      git_fmt, cap)
check('a Z suffix is UTC', S._parse_stamp('2026-09-11T15:42:46Z'), cap)
check('a bare timestamp with no offset is taken as given',
      S._parse_stamp('2026-09-11 15:42:46'), cap)
check('garbage returns None rather than a plausible date', S._parse_stamp('soon'), None)
check('empty returns None', S._parse_stamp(''), None)

# ── 2. THE VERDICT RULE, with dates injected ───────────────────────────────
print('2. the verdict rule')
real_introduced = S.create_introduced
SNAP = {'_generated_at': '2026-09-11 15:42:46.942345+00'}


def fake(dates):
    return lambda table, path: S._parse_stamp(dates.get(table))


S.create_introduced = fake({
    'older': '2026-09-02 12:00:00+00',       # CREATE predates the capture
    'newer': '2026-09-12 09:00:00+00',       # CREATE postdates it
    'undated': 'not a date',
})
created = {'older': 'sql/a.sql', 'newer': 'sql/b.sql', 'undated': 'sql/c.sql'}
v = S.verdicts(['older', 'newer', 'undated'], created, SNAP)
check('a CREATE older than the capture, still absent, is NEVER RUN',
      v['older'][0], 'never-run')
check('a CREATE NEWER than the capture is UNDECIDABLE -- the snapshot simply '
      'predates the file, which is ordinary and not a finding',
      v['newer'][0], 'undecidable')
check('an unparseable CREATE date is undecidable, never never-run',
      v['undated'][0], 'undecidable')
check('a capture with no _generated_at makes everything undecidable, rather '
      'than resolving on a missing field',
      S.verdicts(['older'], created, {})['older'][0], 'undecidable')
check('and the reason is carried with the verdict so it can be argued with',
      bool(v['older'][2]) and bool(v['newer'][2]), True)

# The boundary. A CREATE committed in the same second as the capture must not
# be called never-run: the migration could have run between the two.
S.create_introduced = fake({'tie': '2026-09-11 15:42:46+00'})
check('a CREATE stamped at the exact capture instant is UNDECIDABLE, not never-run',
      S.verdicts(['tie'], {'tie': 'sql/t.sql'}, SNAP)['tie'][0], 'undecidable')
S.create_introduced = real_introduced

# ── 3. create_introduced IGNORES THE NAME IN A COMMENT ─────────────────────
# The table name appears in headers, grant lines and prose. Dating the
# declaration from one of those would date it too early -- which in this tool
# means calling a table NEVER RUN on the strength of a comment.
print('3. the CREATE date comes from the CREATE, not from prose naming it')
tmp = tempfile.mkdtemp(prefix='schemaverdict-')
run = lambda *a: subprocess.run(a, cwd=tmp, capture_output=True, text=True)
run('git', 'init', '-q')
run('git', 'config', 'user.email', 'probe@local')
run('git', 'config', 'user.name', 'probe')
os.makedirs(os.path.join(tmp, 'sql'))
p = os.path.join(tmp, 'sql', 'x.sql')


def commit(text, when):
    io.open(p, 'w', encoding='utf-8', newline='\n').write(text)
    subprocess.run(['git', 'add', '-A'], cwd=tmp, capture_output=True, text=True)
    subprocess.run(['git', 'commit', '-q', '-m', 'x'], cwd=tmp, capture_output=True,
                   text=True, env=dict(os.environ, GIT_AUTHOR_DATE=when,
                                       GIT_COMMITTER_DATE=when))


# First commit: the name exists ONLY in a comment. Second: the real CREATE.
commit('-- widget_events will be added here later\nselect 1;\n',
       '2026-01-01T00:00:00+00:00')
commit('-- widget_events will be added here later\n'
       'create table if not exists widget_events (id text);\n',
       '2026-06-15T00:00:00+00:00')

real_repo = S.REPO
S.REPO = tmp
got = S.create_introduced('widget_events', 'sql/x.sql')
check('the date is the CREATE commit, NOT the earlier comment mentioning the name',
      got.strftime('%Y-%m-%d') if got else None, '2026-06-15')
check('a table with no CREATE in that file returns None rather than a guess',
      S.create_introduced('nothing_here', 'sql/x.sql'), None)

# ── 4. THE CONTROL THAT MATTERS ────────────────────────────────────────────
# Every one of the 89 real absences resolves to never-run, so the live repo
# cannot tell a working rule from one stuck on 'never-run'. This is the case
# the real data does not contain.
print('4. CONTROL -- a CREATE newer than the capture, end to end through git')
# APPEND, do not replace. The first draft overwrote the file, which deleted the
# widget_events CREATE -- so the discriminating arm below came back
# 'undecidable' for the honest reason that there was no longer a CREATE to
# date. A fixture that destroys its own control tests nothing.
commit('-- widget_events will be added here later\n'
       'create table if not exists widget_events (id text);\n'
       'create table if not exists late_arrival (id text);\n',
       '2026-12-25T00:00:00+00:00')
late = S.verdicts(['late_arrival'], {'late_arrival': 'sql/x.sql'}, SNAP)
check('a genuinely newer CREATE reaches "undecidable" through the real git path',
      late['late_arrival'][0], 'undecidable')
check('and the older one in the same repo still reaches "never-run" -- so the '
      'rule discriminates rather than returning one answer',
      S.verdicts(['widget_events'], {'widget_events': 'sql/x.sql'}, SNAP)['widget_events'][0],
      'never-run')
S.REPO = real_repo

# ── 5. THE LIVE FILE, stated as a measurement rather than an expectation ───
print('5. the live repo')
import json
out = subprocess.run([sys.executable, 'tools/schema_snapshot_freshness.py', '--json'],
                     cwd=real_repo, capture_output=True, text=True)
d = json.loads(out.stdout)
check('the checker still exits 1 while tables are absent -- it does not pass vacuously',
      out.returncode, 1)
check('every table it calls never-run-and-queried is also in the queried set',
      set(d['never_run_and_queried']) <= set(d['missing_and_queried']), True)
check('and every verdict is one of the two known values',
      sorted({v['verdict'] for v in d['verdicts'].values()}) in
      (['never-run'], ['undecidable'], ['never-run', 'undecidable']), True)
print('    MEASURED NOW: %d absent, %d queried by api/, %d of those never-run'
      % (len(d['verdicts']), len(d['missing_and_queried']),
         len(d['never_run_and_queried'])))

print(('FAILED  ' if fails else 'ok  ') + 'schema-verdict: %d failed' % fails)
sys.exit(1 if fails else 0)
