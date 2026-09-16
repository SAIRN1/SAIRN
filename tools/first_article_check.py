"""Item 47: has this artefact had a First Article Inspection, and is it STILL VALID?

    python tools/first_article_check.py
    python tools/first_article_check.py --worksheet <file>   # claims + arms, unmapped
    python tools/first_article_check.py --json
    python tools/first_article_check.py --self-check

Exit 0 when every recorded inspection is complete and current, 1 when one is
stale or incomplete or an artefact that needs one has none, 2 when the question
could not be answered. REPORT ONLY.

── WHAT FAI IS, AND WHY IT IS NOT THE REVIEW THAT ALREADY HAPPENED ─────────
An adversarial review asks "can a hostile reader find a bug". FAI asks a
different question: IS EVERY STATED REQUIREMENT VERIFIED, EXHAUSTIVELY. A thing
can survive a hostile reader and still carry a claim in its own header that
nothing checks. On this platform an artefact's requirements ARE the claims its
header makes about itself -- "fails closed", "refuses when X", "exit 2 when Y".

Run once on the first article, 100% against every stated requirement, before the
thing is trusted. Sampling comes after, not instead.

── THE HALF THIS TOOL IS, AND THE HALF IT DELIBERATELY IS NOT ──────────────
THE MAPPING FROM CLAIM TO ARM IS NOT AUTOMATED AND MUST NOT BE. Pairing a prose
claim to a prose arm label is word-overlap scoring, and on this platform that
returned 38% accuracy with FIVE false positives out of five. The 2026-09-14 FAI
refused to promote its extractor for exactly this reason and it was right to:
shipping a claim-counter whose count is not trustworthy is worse than shipping
nothing, because the count gets quoted.

So `--worksheet` prints the two lists and a HUMAN maps them. What this tool
mechanises is everything after that judgement, which is where a hand-written
inspection rots:

  COMPLETE   every claim in the record carries a disposition, and `unverified`
             is a disposition that FAILS rather than one that sits in a file.
  CURRENT    the artefact's bytes are hashed at inspection time. AN FAI IS
             EVIDENCE ABOUT THE BYTES IT WAS RUN ON and about nothing else --
             the day the file changes, the inspection stops being a statement
             about the file and nothing announces that. This does.
  REAL       every suite and report the record names exists, so a record cannot
             cite an arm file somebody deleted.

── FORWARD ONLY, AND SAID OUT LOUD RATHER THAN IMPLIED ─────────────────────
REQUIRED_FROM is a date. An artefact first committed on or after it needs a
record; everything older is reported as PRE-DATES THE REQUIREMENT and is not a
finding. That is not an amnesty -- it is the difference between a gate that can
be satisfied and one that reports 160 findings on its first run and is switched
off the same day. The pre-existing tools are uninspected and the count of them
is printed, so the debt is visible rather than absent.
"""
import argparse
import ast
import datetime
import hashlib
import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

from checker_kit import EXIT_COULD_NOT_RUN                       # noqa: E402

RECORD = os.path.join(REPO, 'docs', 'first-article-inspections.json')

# Every claim must carry one of these. `unverified` is deliberately present and
# deliberately fails: a disposition that can be recorded and ignored is how an
# open finding becomes a permanent entry nobody reads.
DISPOSITIONS = ('verified', 'accepted-risk', 'cannot-test', 'unverified')
FAILING = ('unverified',)


def sha256(path):
    h = hashlib.sha256()
    with io.open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def first_commit_date(rel):
    """YYYY-MM-DD of the commit that ADDED this path, or TODAY if not committed.

    NOT None, and not "older than everything". A file that is staged but not yet
    committed will be committed today, so today is the honest answer -- and it
    keeps the guard once the requirement date is in the past, because today is
    then >= required_from and the file still needs an inspection. Returning a
    sentinel that reads as OLD would let a brand-new tool skip the requirement
    by not being committed yet, which is exactly when an inspection is due.

    The first version returned None and treated it as NEWER THAN EVERYTHING,
    which was right in spirit and wrong in practice: it reported a finding
    against every new tool between `git add` and `git commit`, i.e. during the
    only minutes somebody is looking at it. A check that fires while you work
    and clears when you commit is one you learn to scroll past.
    """
    r = subprocess.run(['git', 'log', '--diff-filter=A', '--format=%ad',
                        '--date=short', '--', rel],
                       cwd=REPO, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    lines = [x.strip() for x in r.stdout.split('\n') if x.strip()]
    return lines[-1] if lines else datetime.date.today().isoformat()


def header_claims(src):
    """Sentences from the module docstring that READ LIKE A REQUIREMENT.

    A WORKSHEET, NOT AN ANSWER. This is the extractor the 2026-09-14 inspection
    refused to promote, kept deliberately crude and never used to COUNT
    anything: it feeds `--worksheet` so a person has the candidate list in front
    of them, and the record they write is the artefact this tool checks.
    """
    try:
        doc = ast.get_docstring(ast.parse(src)) or ''
    except Exception:                                            # noqa: BLE001
        return []
    # BOX-DRAWING RULES MANGLE SENTENCES INTO FRAGMENTS, and the 2026-09-14
    # inspection named exactly that as why its extractor could not be promoted.
    # A whole-line filter is not enough: this repo writes `-- HEADING --` with
    # the rule characters on BOTH sides of real text, so they are stripped in
    # place and the heading survives as its own short fragment instead of being
    # glued onto the sentence after it.
    lines = []
    for raw in doc.split('\n'):
        stripped = re.sub('[─━═]+', ' ', raw)
        if re.match(r'^\s*[=-]{4,}\s*$', stripped):
            continue
        lines.append(stripped.rstrip())
    text = ' '.join(lines)
    out = []
    for s in re.split(r'(?<=[.;])\s+', text):
        s = ' '.join(s.split())
        if len(s) < 12:
            continue
        if re.search(r'\b(exit|refus|fail|never|always|must|only|not\b|'
                     r'report only|cannot|guarantee)\b', s, re.I):
            out.append(s)
    return out


def arm_labels(paths):
    """First string literal of every check()/ck() call in the named suites."""
    out = []
    for p in paths:
        full = p if os.path.isabs(p) else os.path.join(REPO, p)
        if not os.path.exists(full):
            continue
        try:
            tree = ast.parse(io.open(full, encoding='utf-8',
                                     errors='replace').read(), full)
        except Exception:                                        # noqa: BLE001
            continue
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id in ('check', 'ck') and node.args):
                a = node.args[0]
                if isinstance(a, ast.Constant) and isinstance(a.value, str):
                    out.append((os.path.basename(p), a.value))
                elif isinstance(a, ast.BinOp):      # 'text %s' % x
                    try:
                        out.append((os.path.basename(p),
                                    ast.literal_eval(a.left)))
                    except Exception:                            # noqa: BLE001
                        pass
    return out


def audit(record, required_from, candidates):
    """(rows, findings). One row per recorded inspection, plus the uninspected."""
    rows, findings = [], []
    recorded = {}
    for e in record.get('inspections', []):
        recorded[e['artefact']] = e
        full = os.path.join(REPO, e['artefact'])
        row = {'artefact': e['artefact'], 'inspected': e.get('inspected'),
               'inspector': e.get('inspector'), 'itemised': 'claims' in e}
        if not os.path.exists(full):
            row['state'] = 'ARTEFACT GONE'
            findings.append('%s: the inspected file no longer exists'
                            % e['artefact'])
            rows.append(row)
            continue
        now = sha256(full)
        row['current'] = (now == e.get('sha256'))
        if not row['current']:
            row['state'] = 'STALE'
            findings.append('%s: inspected at %s..., the file is now %s... -- '
                            'an FAI is evidence about the bytes it ran on'
                            % (e['artefact'], str(e.get('sha256'))[:12], now[:12]))
        for ref in [e.get('report')] + list(e.get('suites') or []):
            if ref and not os.path.exists(os.path.join(REPO, ref.split(' ')[0])):
                findings.append('%s: cites %s, which does not exist'
                                % (e['artefact'], ref))
        claims = e.get('claims')
        if claims is None:
            row.setdefault('state', 'RECORDED, NOT ITEMISED')
            row['claims_total'] = (e.get('summary') or {}).get('claims_total')
            row['unverified'] = (e.get('summary') or {}).get('unverified')
        else:
            bad = [c for c in claims if c.get('status') not in DISPOSITIONS]
            open_ = [c for c in claims if c.get('status') in FAILING]
            missing = [c for c in claims if not str(c.get('by') or '').strip()]
            row['claims_total'] = len(claims)
            row['unverified'] = len(open_)
            for c in bad:
                findings.append('%s: claim has an unknown disposition %r'
                                % (e['artefact'], c.get('status')))
            for c in open_:
                findings.append('%s: UNVERIFIED claim -- %s'
                                % (e['artefact'], str(c.get('claim'))[:90]))
            for c in missing:
                findings.append('%s: claim %r carries no `by`, so the '
                                'disposition points at nothing'
                                % (e['artefact'], str(c.get('claim'))[:60]))
            # EVERY VERIFIED CLAIM MUST NAME AN ARM THAT STILL EXISTS. An arm
            # renamed or deleted leaves the disposition pointing at nothing
            # while the record still reads `verified` -- the same shape as an
            # anchor that stopped matching, applied to an inspection. This is
            # NOT the word-overlap matching this tool refuses to do: it is an
            # exact substring of a label quoted in the record, which the
            # inspector copied, and it caught a paraphrase on the first run.
            labels = set(l for _p, l in arm_labels(e.get('suites') or []))
            for c in claims:
                if c.get('status') != 'verified':
                    continue
                quoted = [q for q in str(c.get('by')).split("'") if len(q) > 25]
                if quoted and not any(any(q[:40] in l for l in labels)
                                      for q in quoted):
                    findings.append(
                        '%s: claim %r is marked verified but names no arm label '
                        'present in its suites -- the disposition points at '
                        'nothing' % (e['artefact'], str(c.get('claim'))[:60]))
            row.setdefault('state', 'CURRENT' if row.get('current') else 'STALE')
        rows.append(row)

    needs, predates = [], []
    for rel in candidates:
        if rel in recorded:
            continue
        d = first_commit_date(rel)
        if d >= required_from:
            needs.append((rel, d))
        else:
            predates.append(rel)
    for rel, d in needs:
        findings.append('%s: first committed %s, on or after the FAI '
                        'requirement date %s, and has no inspection record'
                        % (rel, d, required_from))
    return rows, findings, needs, predates


def _fixtures():
    return {
        'claims_src': '"""Exits 2 when it cannot run. It never guesses."""\n',
        'suite_src': ('check("the first arm", True)\n'
                      'ck("the second arm", True)\n'
                      'check("built %s label" % x, True)\n'),
    }


def self_check():
    f = _fixtures()
    fails = []

    def ck(name, cond, detail=''):
        print(('  ok   ' if cond else '  FAIL ') + name
              + ('' if cond else '\n         ' + str(detail)[:300]))
        if not cond:
            fails.append(name)

    cl = header_claims(f['claims_src'])
    ck('the worksheet extracts requirement-shaped sentences from the docstring',
       len(cl) == 2, cl)
    ck('...and a docstring with no requirement words yields none',
       header_claims('"""A helper."""\n') == [], header_claims('"""A helper."""\n'))

    import tempfile
    tmp = tempfile.mkdtemp(prefix='fai_')
    sp = os.path.join(tmp, 'suite.py')
    io.open(sp, 'w', encoding='utf-8').write(f['suite_src'])
    labels = [l for _p, l in arm_labels([sp])]
    ck('arm labels are read from check() and ck() alike',
       'the first arm' in labels and 'the second arm' in labels, labels)
    ck('...and a label built with %% is read from its literal half rather than '
       'dropped', 'built %s label' in labels, labels)

    # ── THE AUDIT, EVERY DISPOSITION IN BOTH DIRECTIONS ──────────────────
    art = os.path.join(tmp, 'thing.py')
    io.open(art, 'w', encoding='utf-8').write('# v1\n')

    def rec(claims, sha=None, artefact='thing.py'):
        return {'inspections': [{'artefact': artefact, 'inspected': '2026-09-15',
                                 'inspector': 'fixture',
                                 'sha256': sha or sha256(art),
                                 'claims': claims}]}

    real_repo = globals()['REPO']
    try:
        globals()['REPO'] = tmp
        _r, fnd, _n, _p = audit(rec([{'claim': 'c', 'status': 'verified',
                                      'by': 'A1'}]), '2099-01-01', [])
        ck('a complete, current record produces NO finding', fnd == [], fnd)

        _r, fnd, _n, _p = audit(rec([{'claim': 'c', 'status': 'unverified',
                                      'by': '-'}]), '2099-01-01', [])
        ck('an UNVERIFIED claim is a finding -- a disposition that can be '
           'recorded and ignored is not a disposition',
           any('UNVERIFIED claim' in x for x in fnd), fnd)

        _r, fnd, _n, _p = audit(rec([{'claim': 'c', 'status': 'accepted-risk',
                                      'by': 'AR-4'}]), '2099-01-01', [])
        ck('an ACCEPTED RISK is not a finding -- a claim that cannot have a '
           'test is different from one that has none', fnd == [], fnd)

        _r, fnd, _n, _p = audit(rec([{'claim': 'c', 'status': 'verified',
                                      'by': ''}]), '2099-01-01', [])
        ck('a disposition pointing at NOTHING is a finding',
           any('carries no `by`' in x for x in fnd), fnd)

        _r, fnd, _n, _p = audit(rec([{'claim': 'c', 'status': 'probably fine',
                                      'by': 'A1'}]), '2099-01-01', [])
        ck('an unknown disposition is a finding, not silently accepted',
           any('unknown disposition' in x for x in fnd), fnd)

        # STALENESS -- the arm this whole tool exists for.
        good = rec([{'claim': 'c', 'status': 'verified', 'by': 'A1'}])
        io.open(art, 'w', encoding='utf-8').write('# v2 -- one byte changed\n')
        _r, fnd, _n, _p = audit(good, '2099-01-01', [])
        ck('a file that CHANGED since inspection is STALE -- an FAI is evidence '
           'about the bytes it ran on', any('STALE' in x or 'evidence about the '
                                            'bytes' in x for x in fnd), fnd)
        _r2, fnd2, _n2, _p2 = audit(rec([{'claim': 'c', 'status': 'verified',
                                          'by': 'A1'}]), '2099-01-01', [])
        ck('...and re-inspecting the new bytes clears it, so STALE is not '
           'permanent', fnd2 == [], fnd2)

        _r, fnd, _n, _p = audit({'inspections': [
            {'artefact': 'gone.py', 'inspected': '2026-09-15',
             'sha256': 'x', 'claims': []}]}, '2099-01-01', [])
        ck('a record for a file that no longer exists is a finding',
           any('no longer exists' in x for x in fnd), fnd)

        # A VERIFIED CLAIM NAMING AN ARM NOBODY CAN FIND. Both directions,
        # because a check that always found the arm would pass the first half
        # and a check that never did would pass the second.
        io.open(sp, 'w', encoding='utf-8').write(
            'check("the arm that really exists and is long enough to quote", 1)\n')
        rec2 = {'inspections': [{'artefact': 'thing.py', 'inspected': '2026-09-15',
                                 'sha256': sha256(art), 'suites': ['suite.py'],
                                 'claims': [{'claim': 'c', 'status': 'verified',
                                             'by': "probe: 'the arm that really "
                                                   "exists and is long enough to "
                                                   "quote'"}]}]}
        _r, fnd, _n, _p = audit(rec2, '2099-01-01', [])
        ck('a verified claim quoting an arm that EXISTS is not a finding',
           fnd == [], fnd)
        rec2['inspections'][0]['claims'][0]['by'] = (
            "probe: 'an arm label nobody ever wrote anywhere in this suite'")
        _r, fnd, _n, _p = audit(rec2, '2099-01-01', [])
        ck('a verified claim quoting an arm that does NOT exist is a finding -- '
           'the disposition points at nothing',
           any('points at nothing' in x for x in fnd), fnd)

        # ── THE PRE-DEPLOYMENT HALF, which nothing else exercises ────────
        # On today's tree no artefact needs an inspection yet, so this branch
        # has never run on real data. A guard that has never run is a guard
        # nobody knows works, and this IS the half item 63 flagged as missing.
        empty = {'inspections': []}
        real_fcd = globals()['first_commit_date']
        try:
            globals()['first_commit_date'] = lambda rel: '2026-01-01'
            _r, fnd, needs, pre = audit(empty, '2026-09-16', ['tools/old.py'])
            ck('an artefact committed BEFORE the requirement date is not a '
               'finding', fnd == [] and needs == [] and pre == ['tools/old.py'],
               (fnd, needs, pre))

            globals()['first_commit_date'] = lambda rel: '2026-09-16'
            _r, fnd, needs, pre = audit(empty, '2026-09-16', ['tools/new.py'])
            ck('an artefact committed ON the requirement date with no record '
               'IS a finding -- the boundary is inclusive',
               any('has no inspection record' in x for x in fnd), fnd)

            # AN UNCOMMITTED FILE IS DATED TODAY, not "older than everything".
            # Both directions, because the whole value of the choice is that it
            # is quiet before the requirement date and loud after it.
            globals()['first_commit_date'] = lambda rel: '2026-09-15'
            _r, fnd, needs, pre = audit(empty, '2026-09-16', ['tools/uncommitted.py'])
            ck('an UNCOMMITTED artefact dated today is quiet while the '
               'requirement date is still in the future -- a check that fires '
               'between `git add` and `git commit` is one people scroll past',
               fnd == [] and needs == [], (fnd, needs))
            globals()['first_commit_date'] = lambda rel: '2026-09-20'
            _r, fnd, needs, pre = audit(empty, '2026-09-16', ['tools/uncommitted.py'])
            ck('...and the SAME uncommitted artefact IS a finding once that '
               'date has passed, so nothing skips the requirement by staying '
               'uncommitted',
               any('has no inspection record' in x for x in fnd), fnd)
            ck('first_commit_date returns a DATE for an uncommitted path, never '
               'a sentinel that sorts as old',
               real_fcd('tools/definitely_not_a_real_file_xyz.py')
               == datetime.date.today().isoformat(),
               real_fcd('tools/definitely_not_a_real_file_xyz.py'))

            globals()['first_commit_date'] = lambda rel: '2026-09-16'
            rec3 = {'inspections': [{'artefact': 'thing.py',
                                     'inspected': '2026-09-16',
                                     'sha256': sha256(art), 'claims': [
                                         {'claim': 'c', 'status': 'verified',
                                          'by': 'A1'}]}]}
            _r, fnd, needs, pre = audit(rec3, '2026-09-16', ['thing.py'])
            ck('...and an artefact that HAS a record is not reported as '
               'needing one', needs == [] and fnd == [], (needs, fnd))
        finally:
            globals()['first_commit_date'] = real_fcd
    finally:
        globals()['REPO'] = real_repo

    print('\n%d failure(s)' % len(fails))
    return 1 if fails else 0


def main(argv):
    # The box-drawing rules this repo writes in every header are not cp1252, and
    # the locale default on this platform IS cp1252. Without this a bare run
    # crashes on its own worksheet output -- the stdout half of the same defect
    # e1040ea5 fixed across 358 subprocess calls.
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:                                            # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('--worksheet')
    ap.add_argument('suites', nargs='*',
                    help='suite files to list arm labels from, for --worksheet')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--quiet', action='store_true')
    ap.add_argument('--self-check', action='store_true', dest='selfcheck')
    args = ap.parse_args(argv)

    if args.selfcheck:
        return self_check()

    if args.worksheet:
        p = args.worksheet
        full = p if os.path.isabs(p) else os.path.join(REPO, p)
        if not os.path.exists(full):
            print('COULD NOT RUN: %s does not exist' % p)
            return EXIT_COULD_NOT_RUN
        src = io.open(full, encoding='utf-8', errors='replace').read()
        print('FIRST ARTICLE WORKSHEET -- %s' % p)
        print('  sha256 %s' % sha256(full))
        print('')
        print('  THE TWO LISTS ARE NOT MATCHED HERE AND MUST NOT BE. Pairing a')
        print('  prose claim to a prose arm label is word-overlap scoring, and')
        print('  on this platform that scored 38% with five false positives')
        print('  out of five. Map them by reading, then record the mapping.')
        print('')
        print('  CANDIDATE CLAIMS from the module docstring (%d):'
              % len(header_claims(src)))
        for i, c in enumerate(header_claims(src), 1):
            print('    C%-3d %s' % (i, c[:150]))
        suites = [a for a in args.suites if a != p]
        labels = arm_labels(suites)
        print('')
        print('  ARMS in the suites named on the command line (%d):' % len(labels))
        for i, (sp, l) in enumerate(labels, 1):
            print('    A%-3d [%s] %s' % (i, sp, l[:120]))
        if not suites:
            print('    (name the suite files as extra arguments to list them)')
        return 0

    try:
        record = json.load(io.open(RECORD, encoding='utf-8'))
    except Exception as e:                                       # noqa: BLE001
        print('COULD NOT RUN: %s is missing or unreadable (%s: %s).'
              % (os.path.relpath(RECORD, REPO), type(e).__name__, e))
        print('A pre-deployment gate with no record cannot tell an uninspected')
        print('artefact from a first run, so it refuses rather than passing.')
        return EXIT_COULD_NOT_RUN

    required_from = record.get('required_from')
    if not required_from:
        print('COULD NOT RUN: the record names no `required_from` date, so')
        print('"needs an inspection" has no definition and every answer would')
        print('be arbitrary.')
        return EXIT_COULD_NOT_RUN

    r = subprocess.run(['git', 'ls-files', 'tools/*.py'], cwd=REPO,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    candidates = [x.strip() for x in r.stdout.split('\n') if x.strip()]
    rows, findings, needs, predates = audit(record, required_from, candidates)

    if args.json:
        print(json.dumps({'required_from': required_from, 'rows': rows,
                          'findings': findings,
                          'needs_inspection': needs,
                          'predates_requirement': len(predates)}, indent=1))
        return 1 if findings else 0

    if not args.quiet:
        print('FIRST ARTICLE INSPECTION -- item 47, report only')
        print('  required of anything first committed on or after %s'
              % required_from)
        print('  %d artefact(s) pre-date that and are UNINSPECTED -- visible '
              'debt,' % len(predates))
        print('  not an amnesty and not a finding.')
        print('')
        for row in rows:
            print('  %-46s %s' % (row['artefact'], row.get('state', '?')))
            print('      inspected %s by %s, %s claim(s), %s unverified%s'
                  % (row.get('inspected'), row.get('inspector'),
                     row.get('claims_total'), row.get('unverified'),
                     '' if row.get('itemised') else ' (transcribed, not itemised here)'))
        print('')
        if findings:
            print('  FINDINGS (%d):' % len(findings))
            for x in findings:
                print('    ! %s' % x)
        else:
            print('  Every recorded inspection is complete and current, and')
            print('  nothing committed since %s is missing one.' % required_from)
        print('')
        print('  THE CLAIM-TO-ARM MAPPING IS HUMAN AND IS NOT CHECKED HERE.')
        print('  This verifies that a mapping EXISTS, that it disposes of every')
        print('  claim, and that it still describes the bytes on disk. Whether')
        print('  the arm somebody named actually tests the claim they named it')
        print('  for is a judgement, and automating it scored 38% with five')
        print('  false positives out of five.')
    return 1 if findings else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
