"""defect_register.py -- a standing log of CONFIRMED defects, with a real denominator.

    python tools/defect_register.py --report
    python tools/defect_register.py --check
    python tools/defect_register.py --reseat   # rewrite SHAs a rebase moved
    python tools/defect_register.py --add --commit SHA --app X --layer product \\
        --severity high --method fault-injection --summary "..."

── WHY IT IS DELIBERATELY NOT A COMMIT LOG ─────────────────────────────────
`git log --grep '^fix('` returns thirty entries for 2026-09-10 alone, and most
of them are NOT product defects: harness corrections, checkers whose first real
run needed tightening, my own probe mistakes. Auto-ingesting those would make
the density figure large and meaningless, and the number would then be quoted.

So a record is ADDED DELIBERATELY and carries a judgement nobody can derive --
what LAYER it was in, how severe, and above all HOW IT WAS FOUND. The
mechanical half (date, files, lines, whether the commit exists) is derived from
git, because a field a human retypes is a field that goes wrong.

── THE NUMBER IS NOT THE SIGNAL, AND THIS FILE SAYS SO IN ITS OWN OUTPUT ───
A defect density needs a denominator, and this one uses real line counts. But a
density is a fact about what has been LOOKED AT, not about what is there. The
honest signal is CONSECUTIVE ZERO-NEW-FINDING SWEEPS BY DIFFERENT METHODS over
the same files -- which is why every record names its detection method and why
`--report` prints a method x app coverage matrix beside the density.

The evidence for that is one day old: on 2026-09-10 the mutation controls found
two defects in test code that reading the assertions had not, on the same files
in the same hour. One method returning zero means that method is exhausted.

── IT STARTS ON 2026-09-09 AND IS NOT BACKFILLED BEYOND THAT ───────────────
Every record here was verified by somebody who could attest to it. Reaching
further back would mean classifying commits nobody present can vouch for, and a
register padded with guesses is worse than a short one: its size would imply a
completeness it does not have.
"""
import io
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REG = os.path.join('docs', 'defect-density-register.json')

LAYERS = ('product', 'tooling', 'test')
SEVERITIES = ('critical', 'high', 'moderate', 'low')
# Every method that has actually found something on this platform. Named rather
# than free text, so the coverage matrix means something -- and extended
# deliberately when a genuinely new method finds its first defect.
METHODS = (
    'code-review', 'mutation-testing', 'fault-injection', 'static-checker',
    'live-verification', 'independent-review', 'traceability-matrix',
    'probe-control', 'user-report',
)


def git(*a):
    r = subprocess.run(['git', '-C', REPO] + list(a), capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def load():
    p = os.path.join(REPO, REG)
    if not os.path.isfile(p):
        return {'started': '2026-09-09',
                'note': 'Confirmed defects only. See tools/defect_register.py '
                        'for why this is not a commit log and why the density '
                        'is not the signal.',
                'records': []}
    return json.load(io.open(p, encoding='utf-8'))


def save(d):
    p = os.path.join(REPO, REG)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    io.open(p, 'w', encoding='utf-8', newline='').write(
        json.dumps(d, indent=2, sort_keys=False) + '\n')


def derive(sha):
    """The mechanical half, from git. A field a human retypes goes wrong."""
    full = git('rev-parse', sha)
    if not full:
        return None
    date = git('log', '-1', '--format=%cI', full)
    subject = git('log', '-1', '--format=%s', full)
    stat = git('show', '--numstat', '--format=', full) or ''
    files, added, removed = [], 0, 0
    for line in stat.split('\n'):
        parts = line.split('\t')
        if len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit():
            added += int(parts[0])
            removed += int(parts[1])
            files.append(parts[2])
    return {'commit': full[:12], 'date': (date or '')[:10], 'subject': subject,
            'files': files, 'lines_added': added, 'lines_removed': removed}


def app_lines():
    """The denominator, measured rather than estimated."""
    out = {}
    for f in (git('ls-files', '*.html') or '').split('\n'):
        if f.strip() and '/' not in f:
            p = os.path.join(REPO, f)
            try:
                out[os.path.splitext(f)[0]] = sum(
                    1 for _ in io.open(p, encoding='utf-8', errors='replace'))
            except IOError:
                pass
    return out


def cmd_add(argv):
    def opt(name, required=True):
        if name in argv:
            return argv[argv.index(name) + 1]
        if required:
            print('missing %s' % name)
            sys.exit(2)
        return ''

    sha, app = opt('--commit'), opt('--app')
    layer, sev, method = opt('--layer'), opt('--severity'), opt('--method')
    summary = opt('--summary')
    if layer not in LAYERS:
        print('--layer must be one of %s' % (LAYERS,)); return 2
    if sev not in SEVERITIES:
        print('--severity must be one of %s' % (SEVERITIES,)); return 2
    if method not in METHODS:
        print('--method must be one of %s' % (METHODS,)); return 2
    d = derive(sha)
    if not d:
        print('no such commit: %s' % sha); return 2
    reg = load()
    key = (d['commit'], summary)
    if any((r['commit'], r['summary']) == key for r in reg['records']):
        print('already registered: %s' % d['commit']); return 0
    rec = dict(d)
    rec.update({'app': app, 'layer': layer, 'severity': sev,
                'detection_method': method, 'summary': summary})
    reg['records'].append(rec)
    reg['records'].sort(key=lambda r: (r['date'], r['commit']))
    save(reg)
    print('registered %s (%s, %s, %s)' % (d['commit'], app, sev, method))
    return 0


def subject_index():
    """subject -> [sha]. Built once, because a record that lost its SHA to a
    rebase kept its message: `git rebase` rewrites the hash and preserves the
    subject, which is precisely why the subject is the durable half."""
    out = git('log', '--format=%H%x1f%s', 'HEAD') or ''
    idx = {}
    for line in out.split('\n'):
        if '\x1f' not in line:
            continue
        sha, subj = line.split('\x1f', 1)
        idx.setdefault(subj, []).append(sha)
    return idx


def resolve(rec, idx):
    """(sha, how) -- how is 'sha', 'subject', 'ambiguous' or None.

    ── A REBASED SHA IS NOT A RECORD POINTING AT NOTHING (2026-09-11) ────────
    This used to fail outright on any SHA that would not resolve, and the
    register then sat permanently red: 5 problems when it was first noticed,
    12 hours later, growing because the cause is STRUCTURAL rather than
    anybody's mistake. `--add` derives the SHA from the commit in front of it,
    and with four clones pushing, most commits are rebased onto somebody
    else's work before they reach origin. The SHA recorded is the pre-rebase
    one; the commit it named never existed on `main`.

    That matters more than a stale field. This tool is one of the promoted
    report-only checkers, so **every post-push sweep in every clone carried a
    finding**, which is exactly how a report-only checker earns the reputation
    that gets it switched off before it is ever promoted to a gate.

    So the SHA is treated as what it actually is -- a convenience pointer --
    and the record's identity is its SUBJECT, which survives the rebase. A
    record still FAILS when neither resolves, because that is the real case
    this check exists for: a register pointing at nothing, whose length reads
    as evidence. An AMBIGUOUS subject fails too rather than picking one, since
    guessing which of two commits a record meant is the thing a register must
    never do.
    """
    if git('rev-parse', '--verify', rec['commit'] + '^{commit}'):
        return rec['commit'], 'sha'
    hits = idx.get(rec.get('subject') or '\x00absent', [])
    if len(hits) == 1:
        return hits[0][:12], 'subject'
    if len(hits) > 1:
        return None, 'ambiguous'
    return None, None


def cmd_check(argv=()):
    """Every record must still resolve. A register pointing at nothing is worse
    than none, because its length reads as evidence."""
    reg = load()
    bad, reseat = [], []
    idx = subject_index()
    for r in reg['records']:
        sha, how = resolve(r, idx)
        if how == 'subject':
            reseat.append((r['commit'], sha, r['subject']))
        elif how == 'ambiguous':
            bad.append('%s -- its subject matches more than one commit, so the '
                       'record cannot be re-seated without guessing: %r'
                       % (r['commit'], r['subject']))
        elif how is None:
            bad.append('%s -- neither the commit nor its subject is in this '
                       'repo: %r' % (r['commit'], r.get('subject')))
        # THE VOCABULARY CHECKS RUN REGARDLESS. They used to sit after a
        # `continue`, so the moment a SHA went stale the rest of that record
        # stopped being checked at all -- a second, quieter hole underneath the
        # loud one, and it would have outlived the fix for the loud one.
        if r['detection_method'] not in METHODS:
            bad.append('%s -- unknown detection method %r'
                       % (r['commit'], r['detection_method']))
        if r['layer'] not in LAYERS or r['severity'] not in SEVERITIES:
            bad.append('%s -- layer/severity outside the vocabulary' % r['commit'])
    seen = set()
    for r in reg['records']:
        k = (r['commit'], r['summary'])
        if k in seen:
            bad.append('%s -- duplicate record' % r['commit'])
        seen.add(k)
    # REPORTED, NOT SILENT, AND NOT A FAILURE. A re-seated record is sound --
    # the commit is really there under a new hash -- but a reader deserves to
    # know the register's SHAs have drifted from `main`, and `--reseat` is one
    # command away. Saying nothing here would trade a false alarm for a silent
    # rot, which is the swap this repo keeps recording against itself.
    if reseat:
        print('RE-SEATABLE (%d): the SHA was rewritten by a rebase and the '
              'subject still resolves.' % len(reseat))
        for old, new, subj in reseat:
            print('    %s -> %s  %s' % (old, new, subj[:66]))
        print('    Not a failure. Run `python tools/defect_register.py '
              '--reseat` to write them back.')
    if bad:
        print('FAIL: %d register problem(s)' % len(bad))
        for b in bad:
            print('  ' + b)
        return 1
    print('OK: %d record(s), every commit resolves and every field is in '
          'vocabulary.%s' % (len(reg['records']),
                             ' %d by subject.' % len(reseat) if reseat else ''))
    return 0


def cmd_reseat():
    """Write re-seated SHAs back. A separate command on purpose: `--check` is
    read-only, and a checker that edits the thing it checks is not a checker."""
    reg = load()
    idx = subject_index()
    n = 0
    for r in reg['records']:
        sha, how = resolve(r, idx)
        if how == 'subject':
            print('  %s -> %s  %s' % (r['commit'], sha, r['subject'][:66]))
            r['commit'] = sha
            n += 1
    if not n:
        print('nothing to re-seat -- every SHA resolves as recorded.')
        return 0
    # DELIBERATELY NOT RE-SORTED. The sort key is (date, commit), so re-seating
    # twelve SHAs reorders the file and produces a 157-line diff for a 12-line
    # change -- measured, not guessed, because the first version did sort and
    # that is what it produced. A repair nobody can review is a repair nobody
    # checks.
    #
    # THE KNOWN CONSEQUENCE, SAID RATHER THAN DISCOVERED LATER: the next
    # `--add` DOES sort, so it normalises the order this left behind and its
    # diff is correspondingly large. That is the right place for the churn --
    # an add is a deliberate content change somebody is already reviewing,
    # while a re-seat is a mechanical repair that must stay legible.
    save(reg)
    print('re-seated %d record(s).' % n)
    return 0


def cmd_report():
    reg = load()
    recs = reg['records']
    lines = app_lines()
    print('DEFECT REGISTER -- %d confirmed record(s) since %s'
          % (len(recs), reg.get('started', '?')))
    print('')
    print('BY LAYER')
    for L in LAYERS:
        n = len([r for r in recs if r['layer'] == L])
        print('  %-9s %d' % (L, n))
    print('')
    print('BY SEVERITY')
    for S in SEVERITIES:
        n = len([r for r in recs if r['severity'] == S])
        print('  %-9s %d' % (S, n))
    print('')
    print('BY DETECTION METHOD -- the column that matters')
    for M in METHODS:
        n = len([r for r in recs if r['detection_method'] == M])
        if n:
            print('  %-20s %d' % (M, n))
    print('')
    print('PRODUCT DEFECTS PER 1,000 LINES, against a MEASURED denominator')
    print('  %-22s %8s %8s %s' % ('app', 'lines', 'defects', 'per 1k'))
    prod = [r for r in recs if r['layer'] == 'product']
    for app in sorted(lines):
        n = len([r for r in prod if r['app'] == app])
        if not n:
            continue
        print('  %-22s %8d %8d %6.2f'
              % (app, lines[app], n, 1000.0 * n / max(1, lines[app])))
    total_lines = sum(lines.values())
    print('  %-22s %8d %8d %6.2f'
          % ('ALL APPS', total_lines, len(prod),
             1000.0 * len(prod) / max(1, total_lines)))
    print('')
    print('COVERAGE -- which methods have found something in which app')
    apps = sorted({r['app'] for r in recs})
    for app in apps:
        ms = sorted({r['detection_method'] for r in recs if r['app'] == app})
        print('  %-22s %s' % (app, ', '.join(ms)))
    print('')
    print('READ THIS BEFORE QUOTING ANY NUMBER ABOVE.')
    print('  * A density is a fact about what has been LOOKED AT, not about')
    print('    what is there. An app with no records is an app nobody has')
    print('    swept, not a clean one.')
    print('  * The honest signal is CONSECUTIVE ZERO-NEW-FINDING SWEEPS BY')
    print('    DIFFERENT METHODS over the same files. One method returning')
    print('    zero means that method is exhausted. On 2026-09-10 the mutation')
    print('    controls found two defects in test code that reading the')
    print('    assertions had not, on the same files in the same hour.')
    print('  * The denominator counts LINES OF APP HTML. It does not count')
    print('    api/, sql/ or tools/, so a product defect in an endpoint is')
    print('    registered but not divided by anything. That is a known')
    print('    limitation, not an oversight.')
    return 0


def main(argv):
    if '--add' in argv:
        return cmd_add(argv)
    if '--check' in argv:
        return cmd_check(argv)
    if '--reseat' in argv:
        return cmd_reseat()
    return cmd_report()


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
