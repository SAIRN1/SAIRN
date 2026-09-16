"""The control for tools/retry_policy_audit.py (item 81).

Run: python tests/run_retry_policy_probe.py

The tool's blind lock runs on synthetic fixtures. This runs on the REAL tree and
pins the things a fixture cannot: that the two false-positive classes which
killed the two earlier attempts at item 81 are still zero on real files, that
every live finding is a construct a reader can confirm, and that the tokenizer
is the one shared module rather than a private copy.

THE HISTORY THIS DEFENDS AGAINST, both attempts retracted rather than published:
  1. a regex that matched the word "retry" IN A COMMENT and in its author's own
     citations -- 24 of 25 api/ files, a figure that was prose;
  2. this tool's own first run, which called 24 constructs retries when they
     were iteration, pagination, queue drains and polls. A loop that CONTAINS a
     remote call is not a loop that RE-ISSUES one.
"""
import io
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import jscomments                                                # noqa: E402
import retry_policy_audit as A                                   # noqa: E402

CONTROLS_FOR = ['retry_policy_audit.py']

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        fails.append(name)


ok, rows, problems = A.blind_lock()
check('the blind lock is LOCKED before any real file is opened', ok, problems)
check('...and it covers both directions, not just the positives',
      any(str(r.get('fixture', '')).startswith('NEG:') for r in rows)
      and any('policy' in r for r in rows), len(rows))

files, excluded = A.live_files(False)
findings = []
for f in files:
    try:
        src = io.open(os.path.join(REPO, f), encoding='utf-8',
                      errors='replace').read()
    except Exception:
        continue
    got, _sk = A.scan_source(src)
    for g in got:
        g['file'] = f
        findings.append(g)

print('retry policy control -- %d live file(s), %d finding(s)\n'
      % (len(files), len(findings)))

# ── 1. THE TOKENIZER IS THE SHARED ONE ─────────────────────────────────────
# Seven hand-rolled comment strippers disagreed in this repo and three were
# destroying 90% of their input. A private copy here would be an eighth.
src = io.open(os.path.join(REPO, 'tools', 'retry_policy_audit.py'),
              encoding='utf-8').read()
check('the audit imports jscomments rather than rolling its own stripper',
      'import jscomments' in src and 'def strip_comments' not in src)
check('...and it blanks STRING BODIES too, which is the half that kills the '
      'first false-positive class',
      'blank_string_bodies' in src)

# ── 2. THE TWO RETRACTED FALSE-POSITIVE CLASSES ARE ZERO ON REAL FILES ─────
# Class 1: a comment. Re-derived here by counting how many findings survive
# when the source is NOT stripped -- if stripping made no difference the tool
# would be reading comments and nobody would know.
naive_total, stripped_total = 0, 0
for f in files[:80]:
    try:
        raw = io.open(os.path.join(REPO, f), encoding='utf-8',
                      errors='replace').read()
    except Exception:
        continue
    naive_total += len(A.constructs(raw))
    stripped_total += len(A.constructs(
        jscomments.blank_string_bodies(jscomments.strip_comments(raw))))
check('stripping actually removes constructs the raw text would have offered '
      '-- the tokenizer is doing work, not decorating',
      naive_total > stripped_total,
      'raw %d vs stripped %d' % (naive_total, stripped_total))

# Class 2: iteration, pagination and drains must not be reported. Every live
# finding must carry a role that re-issues a call.
bad_roles = sorted(set(f['role'] for f in findings)
                   - {'RETRY', 'CATCH-RETRY', 'POLL', 'AGENT-LOOP'})
check('no live finding carries an ITERATE or PAGINATE role -- those are '
      'filtered, not reported', bad_roles == [], bad_roles)

# ── 3. EVERY LIVE FINDING IS CONFIRMABLE BY READING ITS SOURCE ─────────────
# The line it names must really open a loop or catch, and the body must really
# contain one of the declared remote calls. A finding a reader cannot confirm
# is the shape both retracted attempts produced.
for f in findings:
    raw = io.open(os.path.join(REPO, f['file']), encoding='utf-8',
                  errors='replace').read()
    code = jscomments.blank_string_bodies(jscomments.strip_comments(raw))
    line = code.split('\n')[f['line'] - 1] if f['line'] <= code.count('\n') + 1 else ''
    check('%s:%d really opens a %s' % (f['file'], f['line'], f['kind']),
          f['kind'] in line, repr(line[:100]))
    # AND THE BODY REALLY CONTAINS A DECLARED REMOTE CALL. Re-extracted here
    # from the file rather than trusted from the finding, so a classifier that
    # attached the wrong body would disagree with this.
    got = [c for c in A.constructs(code)
           if c['body'] and code[:c['start']].count('\n') + 1 == f['line']]
    check('%s:%d body really contains a declared remote call'
          % (f['file'], f['line']),
          bool(got) and bool(A.REMOTE.search(got[0]['body'])),
          (got[0]['body'][:120] if got else 'no construct re-extracted'))

# ── 4. THE POLICY LABELS ARE DISTINGUISHABLE, NOT ONE LABEL FOR EVERYTHING ─
# If the classifier collapsed, every fixture arm would still pass; the labels
# would simply all be the same. The fixture set spans four policies and four
# roles, so the lock proves the vocabulary is used.
policies = set(r.get('policy') for r in rows if 'policy' in r)
roles = set(r.get('role') for r in rows if 'role' in r)
check('the lock exercises more than one POLICY label', len(policies) >= 3, policies)
check('the lock exercises more than one ROLE label', len(roles) >= 2, roles)

# ── 5. NO CONTROL CHARACTERS, because this file shipped TWO ────────────────
# Both `\b` escapes in AI_CALL and in the fetch guard arrived as literal 0x08
# through a shell heredoc, and a pattern with a raw backspace can never match.
# The repo already has a checker for exactly this; it is run here so the class
# cannot come back quietly.
p = subprocess.run([sys.executable, os.path.join(REPO, 'tools',
                                                 'control_char_check.py'),
                    'tools/retry_policy_audit.py'],
                   capture_output=True, text=True, encoding='utf-8',
                   errors='replace', cwd=REPO,
                   env=dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1'))
check('no raw control byte in the audit source -- two backspaces shipped in '
      'this file and a backspace where \\b was meant can never match',
      p.returncode == 0, p.stdout[-300:])
check('...and the pattern that held one matches its own example',
      bool(A.AI_CALL.search('await callClaude(messages)')), A.AI_CALL.pattern)

print('\n%d failure(s)' % len(fails))
for f in fails:
    print('  - ' + f)
sys.exit(1 if fails else 0)
