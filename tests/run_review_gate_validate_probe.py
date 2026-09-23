"""--validate must answer "is the file sound", and --list must keep answering
"does the queue hold overdue work". The bug was that ONE exit code carried both.

    python tests/run_review_gate_validate_probe.py

── WHAT WENT WRONG, AND WHY A POSITIVE-ONLY ARM WOULD MISS IT ─────────────
docs/tier-a-reviews.json declared `["tools/tier_a_review_gate.py", "--list"]` as
its merge validator. tools/sairn_rebase_resolve.py refuses any merge whose
validator exits non-zero, printing "merged cleanly, and then its own validator
rejected the result". --list exits 1 when ANY obligation is past 24h.

So a correct union-by-identity merge of that ledger was REFUSED whenever the
queue happened to hold overdue work -- which is most of the time, and is not a
fact about the file being merged.

THE LOAD-BEARING ARM IS THE DIVERGENCE ONE: on the same fixture, with an
overdue obligation present, --list must exit 1 and --validate must exit 0. An
arm that only checked "--validate exits 0 on the real ledger" would pass today
and pass equally if --validate were a stub that returned 0 unconditionally.

CONTROLS_FOR is declared rather than inferred.
"""
CONTROLS_FOR = ['tier_a_review_gate.py']

import io
import json
import os
import subprocess
import sys
import tempfile
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO, 'tools', 'tier_a_review_gate.py')
LEDGER = os.path.join(REPO, 'docs', 'tier-a-reviews.json')

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name + ('' if cond else '  ' + detail))
    if not cond:
        fails.append(name)


def run(args, env_extra=None):
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    r = subprocess.run([sys.executable, TOOL] + args, cwd=REPO, env=env,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def with_ledger(obj, fn):
    """Run fn() with the real ledger temporarily replaced, then restore it.

    The bytes are captured and compared afterwards. A probe that edits a tracked
    file this repo trusts on sight has to prove it put it back -- the same rule
    run_criticality_tier_probe.py states for the register.
    """
    original = io.open(LEDGER, encoding='utf-8', newline='').read()
    try:
        io.open(LEDGER, 'w', encoding='utf-8', newline='').write(
            json.dumps(obj, indent=2, ensure_ascii=False) + '\n')
        return fn()
    finally:
        io.open(LEDGER, 'w', encoding='utf-8', newline='').write(original)
        restored = io.open(LEDGER, encoding='utf-8', newline='').read()
        check('the ledger was restored byte for byte', restored == original)


print('tier_a_review_gate --validate -- soundness and queue state are two questions\n')

real = json.load(io.open(LEDGER, encoding='utf-8'))
MP = real.get('merge_policy') or {}

# ── ARM 1: THE MERGE POLICY POINTS AT THE RIGHT QUESTION ──────────────────
check('the merge policy names --validate, not --list',
      MP.get('validator') == ['tools/tier_a_review_gate.py', '--validate'],
      repr(MP.get('validator')))

# ── ARM 2: THE CONTROL. The shipped ledger is sound. Without this, every
# ── refusal arm below is satisfied by a validator that refuses everything.
rc, out = run(['--validate'])
check('the shipped ledger VALIDATES', rc == 0, 'exit=%s %s' % (rc, out[-300:]))
check('...and it says so in a sentence a reader can check',
      'record(s), identities unique' in out, out[-200:])
check('...and it disclaims the question it does NOT answer',
      '--list' in out and 'queue is clear' in out, out[-300:])

# ── ARM 3: THE ONE THE BUG WAS. An overdue obligation must move --list and
# ── must NOT move --validate.
OLD = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(time.time() - 96 * 3600))
overdue = {
    'merge_policy': MP,
    'records': [{
        'author_session': 'probe-fixture',
        'opened_at': OLD,
        'owner_assigned_at': OLD,
        'reviewer_owner': 'nobody',
        'resources': ['sd_invoices'],
        'files': ['api/sd-data.js'],
        'what': 'a fixture obligation, deliberately older than the deadline',
        'status': 'open',
    }],
}


def divergence():
    rc_list, out_list = run(['--list'])
    rc_val, out_val = run(['--validate'])
    check('an OVERDUE obligation makes --list exit 1 (unchanged, and it should)',
          rc_list == 1, 'exit=%s' % rc_list)
    check('THE FIX: the same file VALIDATES, exit 0 -- soundness is not queue state',
          rc_val == 0, 'exit=%s %s' % (rc_val, out_val[-300:]))
    check('...and --list still prints the overdue marker a human reads',
          'OVERDUE' in out_list, out_list[-200:])


with_ledger(overdue, divergence)

# ── ARM 4: --validate MUST STILL REFUSE A FILE THAT IS GENUINELY BROKEN.
# ── Otherwise the fix has simply disarmed the merge validator.
def refuses(label, obj, marker):
    def go():
        rc_, out_ = run(['--validate'])
        check('REFUSED: ' + label, rc_ == 2 and marker in out_,
              'exit=%s marker=%s' % (rc_, marker in out_))
    with_ledger(obj, go)


refuses('a record missing the merge identity',
        {'merge_policy': MP,
         'records': [{'author_session': 'x', 'status': 'open'}]},
        'merge identity')

refuses('two records sharing one identity -- a union merge cannot separate them',
        {'merge_policy': MP,
         'records': [
             {'author_session': 'a', 'opened_at': OLD, 'status': 'open'},
             {'author_session': 'a', 'opened_at': OLD, 'status': 'reviewed'},
         ]},
        'cannot tell them apart')

refuses('a status outside the vocabulary',
        {'merge_policy': MP,
         'records': [{'author_session': 'a', 'opened_at': OLD, 'status': 'closed'}]},
        'outside')

# ── ARM 5: THE VOCABULARY IS THE WRITERS', NOT A GUESS. This arm exists
# ── because the first version of --validate typed ('open', 'discharged') and
# ── refused 109 of 127 real records on its first run.
def accepts_real_statuses():
    def go():
        rc_, _ = run(['--validate'])
        check('every status a writer in the tool can set is ACCEPTED', rc_ == 0,
              'exit=%s' % rc_)
    with_ledger({'merge_policy': MP,
                 'records': [
                     {'author_session': 'a', 'opened_at': '2026-09-01T00:00:00Z', 'status': 'open'},
                     {'author_session': 'b', 'opened_at': '2026-09-01T00:00:01Z', 'status': 'reviewed'},
                     {'author_session': 'c', 'opened_at': '2026-09-01T00:00:02Z', 'status': 'reviewed-by-record'},
                 ]}, go)


accepts_real_statuses()

# ── ARM 6: AN UNREADABLE LEDGER IS COULD-NOT-RUN, NOT SOUND. ──────────────
def broken_json():
    original = io.open(LEDGER, encoding='utf-8', newline='').read()
    try:
        io.open(LEDGER, 'w', encoding='utf-8', newline='').write('{ not json')
        rc_, out_ = run(['--validate'])
        check('an unparseable ledger is exit 2 COULD NOT RUN, never 0',
              rc_ == 2, 'exit=%s' % rc_)
    finally:
        io.open(LEDGER, 'w', encoding='utf-8', newline='').write(original)
        check('the ledger was restored after the unparseable arm',
              io.open(LEDGER, encoding='utf-8', newline='').read() == original)


broken_json()

# ── AND THIS CLONE IS CLEAN AFTERWARDS ────────────────────────────────────
r = subprocess.run(['git', '-C', REPO, 'status', '--porcelain', '--',
                    'docs/tier-a-reviews.json'],
                   capture_output=True, text=True, encoding='utf-8', errors='replace')
check("this clone's own ledger is untouched", (r.stdout or '').strip() == '',
      (r.stdout or '').strip())

print('\n%s  run_review_gate_validate_probe: %d failed'
      % ('FAILED' if fails else 'ok', len(fails)))
sys.exit(1 if fails else 0)
