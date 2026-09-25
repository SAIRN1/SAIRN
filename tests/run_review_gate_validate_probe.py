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

# ── ARM 5b: THE VOCABULARY IS RE-DERIVED FROM THE WRITERS, MECHANICALLY ─────
# Added 2026-09-24 by the reviewer (hank), because arm 5's fixture HARDCODES
# the three statuses -- the very literal-instead-of-read-from-the-writer shape
# the author's own point (3) asked a reviewer to hunt. STATUSES in the tool is
# also a hand-maintained tuple with a comment naming its writers. A FOURTH
# writer added later would drift past both, and --validate would refuse a real
# ledger DURING A REBASE, which is precisely the failure this change fixed.
# So the writer set is read out of the tool's source here: every literal
# passed to _discharge() plus the 'status': 'open' the --open path writes.
def statuses_rederived_from_writers():
    src = io.open(os.path.join(REPO, 'tools', 'tier_a_review_gate.py'),
                  encoding='utf-8', errors='replace').read()
    import re as _re
    # A _discharge() call can span lines and hold nested parens (the
    # reviewed-by-record one does both), so the span is walked with a paren
    # balance rather than matched with a bracket-free regex -- the first
    # version of this arm used one and re-derived only the single-line call,
    # which would have "confirmed" a two-status vocabulary.
    written = set()
    for m in _re.finditer(r'\b_discharge\(', src):
        i, depth = m.end(), 1
        while i < len(src) and depth:
            if src[i] == '(':
                depth += 1
            elif src[i] == ')':
                depth -= 1
            i += 1
        span = src[m.end():i - 1]
        lits = _re.findall(r"['\"]([a-z][a-z-]*)['\"]", span)
        if lits:
            written.add(lits[-1])   # the status is _discharge's LAST argument
    written.discard('rec')
    if _re.search(r"['\"]status['\"]\s*:\s*['\"]open['\"]", src):
        written.add('open')
    declared = set(_re.findall(r"['\"]([a-z-]+)['\"]",
                               _re.search(r'^STATUSES\s*=\s*\(([^)]*)\)', src,
                                          _re.M).group(1)))
    check('the writer statuses re-derived from source are non-empty and '
          'include a discharge form -- else this arm is matching nothing',
          len(written) >= 2 and any(s.startswith('reviewed') for s in written),
          sorted(written))
    check('STATUSES equals the statuses the writers actually assign -- a '
          'fourth writer or a dropped one fails HERE, not mid-rebase',
          written == declared,
          'written=%s declared=%s' % (sorted(written), sorted(declared)))


statuses_rederived_from_writers()


# ── --resources: NAMING THE SUBJECTS OF A JUDGEMENT THAT HAS NO DIFF ────────
# 2026-09-25. The gate attributes obligations from a DIFF and excludes docs/
# and .md by design -- CRITICALITY-TIERS.md names every Tier A resource, so
# attributing its diff would make every push a Tier A push. Correct, and it
# leaves one hole: a TIER PROMOTION lives only in that document, changes no
# code, and is therefore the judgement with the widest blast radius on the
# platform and the one thing that can never be reviewed. Two promotions
# landed unreviewable on 2026-09-25 before this flag existed. The refusal
# message had been saying "say which resource or rule and why" since it was
# written, with no way to say it.
def resources_flag():
    real = json.load(io.open(LEDGER, encoding='utf-8'))
    before = len(real.get('records') or [])

    rc_, out_ = run(['--open', 'x', '--resources', 'definitely_not_a_resource'])
    check('--resources REFUSES a name that is not Tier A -- the flag says '
          'WHICH known resource a judgement is about, it cannot make one',
          rc_ == 1 and 'not Tier A' in out_, 'rc=%s' % rc_)
    check('...and writes NOTHING when it refuses',
          len(json.load(io.open(LEDGER, encoding='utf-8')).get('records') or [])
          == before)

    rc_, out_ = run(['--open', 'x', '--resources', 'sen_branches',
                     '--range', 'HEAD~1..HEAD'])
    check('--resources and --range together are REFUSED rather than one '
          'silently winning -- they answer the same question two ways',
          rc_ == 1 and 'Pick one' in out_, 'rc=%s' % rc_)

    def go():
        rc2, out2 = run(['--open', 'a tier promotion with no diff to attribute',
                         '--resources', 'sen_branches,dnt_cred_rules'])
        check('--resources RECORDS an obligation naming exactly those '
              'resources', rc2 == 0 and 'sen_branches' in out2
              and 'dnt_cred_rules' in out2, 'rc=%s %s' % (rc2, out2[-160:]))
        recs = json.load(io.open(LEDGER, encoding='utf-8'))['records']
        new = recs[-1]
        check('...and the record goes through the SAME writer as every other '
              'obligation -- owner stamped, status open, rules present',
              new.get('status') == 'open' and 'reviewer_owner' in new
              and new.get('rules') == [] and 'owner_assigned_at' in new, new)
        check('...and its files[] names the register, so a reviewer can see '
              'the judgement has no code behind it',
              new.get('files') == ['docs/CRITICALITY-TIERS.md'], new.get('files'))
        check('...and the resources are exactly the two named, not a superset '
              'scraped from the document',
              sorted(new.get('resources') or []) == ['dnt_cred_rules',
                                                     'sen_branches'],
              new.get('resources'))

    with_ledger({'merge_policy': MP, 'records': []}, go)

    check('CONTROL: after the fixture is restored the real ledger is the '
          'length it started at -- the arms above added nothing to it',
          len(json.load(io.open(LEDGER, encoding='utf-8')).get('records') or [])
          == before)


resources_flag()

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
