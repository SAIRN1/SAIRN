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
import re
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

# ── THE STANDING-RULE CITATION, added 2026-09-13 ───────────────────────────
# `tools/fmea_prediction_check.py` has scored ZERO since the day it was written
# and says so in its own docstring: matching a saved risk draft to a defect that
# then happened is by RULE CITATION ONLY, because the first matcher scored 38%
# on three-word overlap AND EVERY ONE OF THOSE FIVE HITS WAS A FALSE POSITIVE.
# Its answer was blocked on this field, not on its own logic.
#
# THREE CONFIDENCES, NOT TWO, AND THE THIRD IS THE POINT. A register that could
# only say "cites rule X" would push every awkward record into a citation it
# does not really instantiate, and the FMEA scorer would then match on
# manufactured agreement -- the 38% arriving through the data instead of the
# matcher. So `not-citable` is a first-class answer, it requires a note saying
# why, and 6 of 54 records carry it.
CONFIDENCES = ('clean', 'arguable', 'not-citable')
RULES_DOC = os.path.join('docs', 'SAIRN-PROCESS-RULES.md')


def known_rules():
    """Section ids parsed out of the process rules themselves.

    DERIVED, NOT LISTED. A hand-kept vocabulary of rule ids is a second copy of
    the rules document, and this repo has corrected that exact shape in the
    Guardian App File Map seven times. A citation naming a section that does not
    exist is a finding; a citation naming one that was renumbered should fail
    loudly rather than sit there looking checked.

    Returns None when the document cannot be read -- the caller must treat that
    as COULD NOT CHECK, never as "every citation is fine" (PR 1.11).
    """
    p = os.path.join(REPO, RULES_DOC)
    if not os.path.isfile(p):
        return None
    try:
        src = io.open(p, encoding='utf-8').read()
    except Exception:
        return None
    ids = set(re.findall(r'^###\s+(\d+\.\d+)\s', src, re.M))
    ids.update(re.findall(r'^##\s+(Part \d+)\b', src, re.M))
    return ids or None


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
    # REQUIRED, not optional, and that is the whole fix. The field was absent
    # for 54 records because nothing ever asked for it, and `--check` cannot
    # demand of old records what `--add` never collected. Pass
    # `--rule not-citable` when no standing rule names the shape -- with a
    # `--rule-note` saying so. Refusing to record a defect because no rule fits
    # would be worse than the gap this closes.
    rule = opt('--rule')
    note = opt('--rule-note', required=False)
    if layer not in LAYERS:
        print('--layer must be one of %s' % (LAYERS,)); return 2
    if sev not in SEVERITIES:
        print('--severity must be one of %s' % (SEVERITIES,)); return 2
    if method not in METHODS:
        print('--method must be one of %s' % (METHODS,)); return 2
    if rule == 'not-citable':
        rules, conf = [], 'not-citable'
    else:
        rules, conf = [rule], ('arguable' if note else 'clean')
        known = known_rules()
        if known is None:
            # PR 1.11. The vocabulary comes from a document; if that document
            # cannot be read the citation CANNOT BE CHECKED, and accepting it
            # would record an unverified claim as a verified one.
            print('COULD NOT READ %s, so --rule cannot be validated. Not '
                  'recording an unchecked citation.' % RULES_DOC); return 2
        if rule not in known:
            print('--rule %r is not a section in %s. Known: %s'
                  % (rule, RULES_DOC, ', '.join(sorted(known)))); return 2
    if conf != 'clean' and not note:
        print('--rule-note is required unless the citation is clean'); return 2
    d = derive(sha)
    if not d:
        print('no such commit: %s' % sha); return 2
    reg = load()
    key = (d['commit'], summary)
    if any((r['commit'], r['summary']) == key for r in reg['records']):
        print('already registered: %s' % d['commit']); return 0
    rec = dict(d)
    rec.update({'app': app, 'layer': layer, 'severity': sev,
                'detection_method': method, 'summary': summary,
                'rules': rules, 'citation_confidence': conf})
    if note:
        rec['citation_note'] = note
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
    could_not_check = 0
    known = known_rules()
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
        # ── THE CITATION, checked the same way and for the same reason ──────
        conf = r.get('citation_confidence')
        rules = r.get('rules')
        if conf not in CONFIDENCES:
            bad.append('%s -- citation_confidence %r is outside %s'
                       % (r['commit'], conf, (CONFIDENCES,)))
        elif conf == 'not-citable':
            if rules:
                bad.append('%s -- not-citable but carries rules %r'
                           % (r['commit'], rules))
            if not str(r.get('citation_note') or '').strip():
                bad.append('%s -- not-citable with no note. A bare refusal to '
                           'cite is a silence, not a decision.' % r['commit'])
        else:
            if not rules:
                bad.append('%s -- %s citation with no rule' % (r['commit'], conf))
            if conf == 'arguable' and not str(r.get('citation_note') or '').strip():
                bad.append('%s -- arguable citation with no note saying what is '
                           'arguable about it' % r['commit'])
            if known is None:
                could_not_check += 1
            else:
                for rid in (rules or []):
                    if rid not in known:
                        bad.append('%s -- cites %r, which is not a section in %s'
                                   % (r['commit'], rid, RULES_DOC))
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
    if could_not_check:
        # PR 1.11, in this file's own output. The citations were NOT validated,
        # and saying "OK" here would be reporting a check that did not run.
        print('COULD NOT CHECK %d citation(s): %s is unreadable, so the rule '
              'vocabulary is unknown. This is not a pass.'
              % (could_not_check, RULES_DOC))
        return 2
    cited = sum(1 for r in reg['records'] if r.get('rules'))
    print('OK: %d record(s), every commit resolves and every field is in '
          'vocabulary.%s' % (len(reg['records']),
                             ' %d by subject.' % len(reseat) if reseat else ''))
    print('    standing-rule citations: %d cited, %d deliberately not-citable, '
          'every id checked against %s'
          % (cited, len(reg['records']) - cited, RULES_DOC))
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
    # ── TWO FIGURES, NOT ONE (2026-09-13) ──────────────────────────────────
    # This printed a single ALL APPS rate: every product defect divided by
    # EVERY tracked app line, including the files nobody has ever swept. One
    # number was being asked to answer two different questions -- "how dense
    # are the defects where we have looked" and "how much have we looked at" --
    # and the second answer was silently folded into the first as a smaller
    # rate. A file with no records is a file nobody has swept, not a clean one;
    # the caveat below has always said so while the arithmetic said otherwise.
    #
    # The swept figure is the real signal. The unswept figure is a COUNT, and
    # deliberately not a rate: dividing by lines nobody has examined would be
    # the same mistake in the other direction.
    # ── AND THE NUMERATOR HAS TO MATCH THE DENOMINATOR ─────────────────────
    # Found by checking the first version of this very block: `len(prod)` counts
    # every product defect, INCLUDING those filed against app 'PLATFORM', which
    # is not a file and contributes no lines. The old ALL APPS rate divided
    # those by the whole-repo line count and the new swept rate divided them by
    # the swept subset -- both dividing a defect by lines it does not live in.
    # The caveat below has said "registered but not divided by anything" since
    # this tool shipped while the arithmetic did exactly that.
    #
    # They get their own line, with no rate, for the same reason the unswept
    # files do: a count with no honest denominator is reported as a count.
    swept = sorted(a for a in lines if any(r['app'] == a for r in prod))
    unswept = sorted(a for a in lines if a not in swept)
    swept_lines = sum(lines[a] for a in swept)
    unswept_lines = sum(lines[a] for a in unswept)
    in_files = [r for r in prod if r['app'] in lines]
    no_denom = [r for r in prod if r['app'] not in lines]
    print('  %-22s %8d %8d %6.2f   <- SWEPT: the real signal'
          % ('SWEPT FILES (%d)' % len(swept), swept_lines, len(in_files),
             1000.0 * len(in_files) / max(1, swept_lines)))
    print('  %-22s %8d %8s %6s   <- UNMEASURED, not a rate'
          % ('UNSWEPT FILES (%d)' % len(unswept), unswept_lines, '--', '--'))
    if unswept:
        print('     %s' % ', '.join(unswept))
    if no_denom:
        print('  %-22s %8s %8d %6s   <- NO DENOMINATOR: not app HTML'
              % ('OFF-FILE (%s)' % ', '.join(sorted({r['app'] for r in no_denom})),
                 '--', len(no_denom), '--'))
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
    print('  * WHICH IS WHY THERE ARE TWO FIGURES AND NOT ONE. The swept rate')
    print('    is the signal; the unswept line count is coverage owed, stated')
    print('    as a COUNT because dividing by lines nobody has examined would')
    print('    manufacture a reassuring rate out of an absence of work.')
    print('  * FIVE OF THE FILES COUNTED ARE SATELLITE PAGES, not apps --')
    print('    stonedesk-hr, stonedesk-intake, stonedesk-catalog,')
    print('    sairndental-book, sairndental-complaint. 2,647 lines, ~2%% of')
    print('    the denominator. Real files, really unswept; named so the')
    print('    unswept count is not read as five whole applications.')
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
