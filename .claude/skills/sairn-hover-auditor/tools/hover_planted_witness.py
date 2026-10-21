#!/usr/bin/env python
"""hover_planted_witness.py -- the WITNESS GATE in front of every recall number
this role reports from hover_planted_bug_recall.SEEDS. Built H1 b74, item 4.

THE RULE IT ENFORCES. A recall number says "the detector found X of the N planted
bugs". That is only a statement about the detector if each planted bug IS a bug;
otherwise a miss may be the detector being right and a hit may be luck. So
before any recall number is trusted, every non-clean seed must have a WITNESS
TEST -- witness/planted_witness.js RUNS the fragment against an in-memory
PostgREST that moves between its read and its write, and observes the class
invariant being violated -- and every clean seed must read NO_BUG_OBSERVED under
the identical scenario. The witness never consults a detector.

WHAT THE GATE CHECKS, each of it a failure when it does not hold:
  1. COVERAGE   the set of seed ids with a witness scenario equals the set of ids
                in SEEDS. A seed added without a witness fails the gate; so does
                a witness for a seed that no longer exists.
  2. RUNS       no seed returns HARNESS_ERROR or NO_WITNESS_DEFINED.
  3. VERDICT    every easy / hard / hard2 seed reads BUG_WITNESSED and every
                clean seed reads NO_BUG_OBSERVED, each with its control arm ok.
  4. RACE       with HOVER_WITNESS_SABOTAGE=no-interleave (the calls run one
                after the other, the in-flight state change never fires) every
                money-toctou / lost-update-counter / revocation-clobber witness
                must flip to NO_BUG_OBSERVED, while the zero-row, client-trusted
                and filter-injection witnesses must NOT flip (they do not depend
                on interleaving). A witness that still "finds" a lost update
                with no concurrency was measuring something else.
  5. STABLE     the witness is run twice and must answer identically.

EXIT CODES. 0 = gate PASSED. 1 = gate FAILED (a planted bug lacks a working
witness -- do NOT trust a recall number drawn from this set). 2 = COULD NOT RUN
(node missing, harness unreadable) -- NEVER folded into a pass.

WHAT IT DOES NOT SHOW, said here so it is not inferred: a witness shows the
FRAGMENT misbehaves against PostgREST semantics as modelled in pgrest_emulator.js,
GIVEN the helper contracts each result lists under `assumed`. It does not show
production behaves that way, and a witness for a hard/hard2 seed has not been
shown to flip when THAT seed is fixed -- only the six clean twins, and five
per-seed fixed variants in the selftest (one each for the money, zero-row,
revocation, filter-injection and lost-update classes), are fixed counterparts.
The client-trusted-role class has its clean twin and nothing more.

Run:
  python hover_planted_witness.py --check          # the gate, with the table
  python hover_planted_witness.py --selftest
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
WITNESS_JS = os.path.join(HERE, 'witness', 'planted_witness.js')
EXIT_OK = 0
EXIT_FAIL = 1
EXIT_COULD_NOT_RUN = 2

RACE_CLASSES = ('money-toctou', 'lost-update-counter', 'revocation-clobber')


def _seeds():
    sys.path.insert(0, HERE)
    import hover_planted_bug_recall as P
    return P.SEEDS


def _run_node(seed_dir, sabotage=''):
    node = shutil.which('node')
    if not node:
        raise RuntimeError('node is not on PATH')
    env = dict(os.environ)
    env.pop('HOVER_WITNESS_SABOTAGE', None)
    if sabotage:
        env['HOVER_WITNESS_SABOTAGE'] = sabotage
    r = subprocess.run([node, WITNESS_JS, seed_dir], capture_output=True,
                       text=True, encoding='utf-8', env=env, timeout=120)
    if r.returncode != 0:
        raise RuntimeError('witness exited %d: %s' % (r.returncode, r.stderr.strip()[:300]))
    return json.loads(r.stdout)


def _write_seeds(seed_dir, seeds):
    meta = []
    for sid, cls, _tier, kind, code in seeds:
        with open(os.path.join(seed_dir, sid + '.js'), 'w', encoding='utf-8', newline='\n') as f:
            f.write(code)
        meta.append({'id': sid, 'cls': cls, 'kind': kind})
    with open(os.path.join(seed_dir, 'meta.json'), 'w', encoding='utf-8') as f:
        json.dump(meta, f)


def evaluate(seeds, normal, sabotaged):
    """Pure. (passed, problems, rows) from the two witness runs."""
    problems, rows = [], []
    ids = [s[0] for s in seeds]
    handled = set(normal.get('handled', []))
    for sid in ids:
        if sid not in handled:
            problems.append('COVERAGE: seed %s has NO witness scenario' % sid)
    for sid in sorted(handled - set(ids)):
        problems.append('COVERAGE: a witness exists for %s, which is not a seed' % sid)
    by_norm = {r['id']: r for r in normal.get('results', [])}
    by_sab = {r['id']: r for r in sabotaged.get('results', [])}
    for sid, cls, _t, kind, _c in seeds:
        r = by_norm.get(sid, {})
        v = r.get('verdict')
        want = 'NO_BUG_OBSERVED' if kind == 'clean' else 'BUG_WITNESSED'
        ok = (v == want and r.get('control_ok') is True)
        if v in ('HARNESS_ERROR', 'NO_WITNESS_DEFINED', None):
            problems.append('RUNS: %s -> %s %s' % (sid, v, r.get('error', '')))
        elif v != want:
            problems.append('VERDICT: %s (%s/%s) expected %s, witnessed %s'
                            % (sid, cls, kind, want, v))
        elif r.get('control_ok') is not True:
            problems.append('CONTROL: %s verdict ok but its control arm did not hold' % sid)
        s = by_sab.get(sid, {})
        sv = s.get('verdict')
        if kind != 'clean':
            if cls in RACE_CLASSES and sv != 'NO_BUG_OBSERVED':
                problems.append('RACE: %s still reads %s with no interleaving -- '
                                'the witness is not measuring the race' % (sid, sv))
            if cls not in RACE_CLASSES and sv != 'BUG_WITNESSED':
                problems.append('RACE: %s reads %s with no interleaving, but it '
                                'should not depend on concurrency' % (sid, sv))
        rows.append((sid, cls, kind, v, r.get('control_ok'), sv, ok))
    return (not problems), problems, rows


def gate(seeds=None):
    """(status, lines): 'PASS' | 'FAIL' | 'COULD_NOT_RUN'. The one entry point
    hover_planted_bug_recall calls before it will call a number trusted."""
    seeds = seeds if seeds is not None else _seeds()
    tmp = tempfile.mkdtemp(prefix='h1-witness-')
    try:
        _write_seeds(tmp, seeds)
        a = _run_node(tmp)
        b = _run_node(tmp)
        sab = _run_node(tmp, 'no-interleave')
    except Exception as e:
        shutil.rmtree(tmp, ignore_errors=True)
        return 'COULD_NOT_RUN', ['COULD NOT RUN: %s -- this is not a pass; no '
                                  'recall number from the planted set may be '
                                  'called trusted' % e]
    shutil.rmtree(tmp, ignore_errors=True)
    ok, problems, rows = evaluate(seeds, a, sab)
    if a != b:
        ok = False
        problems.append('STABLE: two identical runs of the witness answered '
                        'differently -- a witness that is not deterministic '
                        'proves nothing')
    lines = ['%-6s %-28s %-6s %-16s ctl  no-race' % ('seed', 'class', 'kind', 'witnessed')]
    for sid, cls, kind, v, c, sv, rowok in rows:
        lines.append('%-6s %-28s %-6s %-16s %-4s %s%s'
                     % (sid, cls, kind, v, 'ok' if c else 'NO', sv,
                        '' if rowok else '   <-- NOT WORKING'))
    n_planted = sum(1 for s in seeds if s[3] != 'clean')
    n_ok = sum(1 for r in rows if r[2] != 'clean' and r[6])
    lines.append('WITNESSED %d of %d planted bug(s); %d clean twin(s) read clean'
                 % (n_ok, n_planted, sum(1 for r in rows if r[2] == 'clean' and r[6])))
    lines.extend(problems)
    return ('PASS' if ok else 'FAIL'), lines


def selftest():
    ok_n = [0]
    bad_n = [0]

    def ck(name, cond):
        if cond:
            ok_n[0] += 1
            print('  ok   %s' % name)
        else:
            bad_n[0] += 1
            print('  FAIL %s' % name)

    seeds = list(_seeds())
    status, lines = gate(seeds)
    ck('W1 the gate PASSES on the real seed set (%s)' % lines[-1 if status == 'PASS' else 0][:80],
       status == 'PASS')
    ck('W2 every planted seed is witnessed: 18 of 18, 6 clean twins read clean',
       any('WITNESSED 18 of 18 planted' in l and '6 clean' in l for l in lines))

    # A seed with NO scenario must fail the gate, loudly.
    extra = seeds + [('zz-9', 'money-toctou', 1, 'easy', 'async function settle(){}')]
    st, ln = gate(extra)
    ck('W3 a seed added WITHOUT a witness fails the gate (COVERAGE)',
       st == 'FAIL' and any('COVERAGE' in l and 'zz-9' in l for l in ln))

    # A planted seed that is not actually a bug must fail the gate. Four
    # per-seed FIXED variants, one per class, each the real seed with the
    # defect closed: the witness must read them clean.
    fixed = {
        'mt-1': """
async function settle(client, id) {
  const r = await fetch(client.rest('ledger?id=eq.' + id + '&select=balance'));
  const row = await r.json();
  const w = await fetch(client.rest('ledger?id=eq.' + id + '&balance=eq.' + row[0].balance), {
    method: 'PATCH', headers: { Prefer: 'return=representation' },
    body: JSON.stringify({ balance: row[0].balance - 100 })
  });
  const rows = await w.json();
  if (!Array.isArray(rows) || rows.length === 0) throw new Error('CAS lost');
}
""",
        'zr-1': """
async function setPlanStatus(url, headers, agentId, planStatus) {
  const res = await fetch(url + '/rest/v1/sairn_agents?id=eq.' + encodeURIComponent(agentId), {
    method: 'PATCH', headers: { ...headers, Prefer: 'return=representation' },
    body: JSON.stringify({ plan_status: planStatus })
  });
  const rows = await res.json();
  if (!Array.isArray(rows) || rows.length === 0) throw new Error('matched ZERO rows');
}
""",
        'rc-1': """
const rows = await (await fetch(U + '/rest/v1/sairn_agents?token_hash=eq.' + th + '&select=id,status')).json();
const agent = rows[0];
if (agent.status === 'revoked') { res.status(403).json({ error: 'revoked' }); return; }
const w = await fetch(U + '/rest/v1/sairn_agents?id=eq.' + agent.id + '&status=neq.revoked', {
  method: 'PATCH', headers: { ...H, Prefer: 'return=representation' }, body: JSON.stringify({ status: 'active' })
});
if ((await w.json()).length === 0) { res.status(403).json({ error: 'revoked in flight' }); return; }
""",
        'fi-1': """
const r = await fetch(U + '/rest/v1/law_trusttx?matter_id=eq.' + encodeURIComponent(req.body.matter_id), { headers: H });
""",
        'lu-1': """
const cur = await (await fetch(sb.rest('cl_citing_treatments?id=eq.' + id + '&select=' + f), { headers: sb.headers })).json();
const current = (cur[0] && cur[0][f]) || 0;
const w = await fetch(sb.rest('cl_citing_treatments?id=eq.' + id + '&' + f + '=eq.' + current), {
  method: 'PATCH', headers: Object.assign({}, sb.headers, { Prefer: 'return=representation' }),
  body: JSON.stringify({ [f]: current + 1 })
});
if (!(await w.json()).length) throw new Error('lost the race');
""",
    }
    for sid, code in fixed.items():
        s2 = [(a, b, c, d, (code if a == sid else e)) for a, b, c, d, e in seeds]
        st2, ln2 = gate(s2)
        ck('W4-%s a FIXED variant of %s makes the gate FAIL on exactly that seed '
           '(the witness can tell the planted bug from its fix)' % (sid, sid),
           st2 == 'FAIL' and any(('VERDICT: %s' % sid) in l for l in ln2)
           and sum(1 for l in ln2 if l.startswith(('VERDICT', 'CONTROL', 'RUNS'))) == 1)

    # node missing -> COULD NOT RUN, never a pass.
    saved = os.environ.get('PATH', '')
    try:
        os.environ['PATH'] = os.path.dirname(sys.executable)
        st3, ln3 = gate(seeds)
    finally:
        os.environ['PATH'] = saved
    ck('W5 with node absent the gate answers COULD_NOT_RUN, never PASS',
       st3 == 'COULD_NOT_RUN' and 'not a pass' in ln3[0])

    print('%d ok, %d failed' % (ok_n[0], bad_n[0]))
    return EXIT_OK if not bad_n[0] else EXIT_FAIL


def main(argv):
    if '--selftest' in argv:
        return selftest()
    if '--check' in argv or not argv:
        status, lines = gate()
        for l in lines:
            print(l)
        print('WITNESS GATE: %s' % status)
        return {'PASS': EXIT_OK, 'FAIL': EXIT_FAIL}.get(status, EXIT_COULD_NOT_RUN)
    print('usage: --check | --selftest')
    return EXIT_COULD_NOT_RUN


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
