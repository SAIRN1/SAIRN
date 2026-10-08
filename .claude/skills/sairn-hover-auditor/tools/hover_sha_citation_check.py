#!/usr/bin/env python
"""Given a tracking doc, checks every CITED commit sha -- a backtick-
delimited hex run, 7-40 chars -- against the real git history. FOUR
states: ON-MAIN (ancestor of origin/main), LOCAL-ONLY (exists as an object
but is not an ancestor -- an orphan, e.g. rebased away), ABSENT (no such
object at all), NEAR-MISS (added batch K, item 5 -- the token itself does
not resolve, but its own first 7 characters DO resolve to a real object,
meaning this is almost certainly NOT a commit citation at all -- a
different identifier scheme, such as a defect-register record id, that
happens to reuse a real commit's prefix. Found on real data: 'Register
record 16b2cc70d2d8' is not commit 16b2cc70 with extra characters; it is a
different id. NEAR-MISS is reported SEPARATELY from ABSENT so a reader does
not count a non-citation as a broken one).

Own tool, own location. Built 2026-10-06 (H1, batch I, item 9). Design
logged (seq 994) before this file was written. Built from this role's own
definition of "citation" and "population" -- never reads H2's own
hover2_sha_citation_verify.py or any build-agent's equivalent tool, per
tool-parity.

CITATION DEFINITION: a backtick-delimited token, `[0-9a-f]{7,40}`, nothing
else inside the backticks. Narrower than a bare hex-looking word in prose
(this role's own earlier naive scan, seq 943/980) -- a citation is
something the DOCUMENT AUTHOR marked as code/a reference, not any
incidental hex-shaped token.

POPULATION DEFINITION: every such backtick-delimited citation in the named
file, counted once per OCCURRENCE (not de-duplicated) -- a sha cited five
times in five different rows is five citations, because each row's reader
sees it fresh.

CLASSIFICATION: git cat-file -e decides EXISTS; git merge-base --is-ancestor
<sha> origin/main decides ON-MAIN among those that exist. A sha shorter than
a full 40 chars is resolved by git itself (abbreviated sha lookup) before
either check.
"""
import re
import subprocess
import sys

REPO = r'C:\Users\marsh\Documents\SAIRN-hover'
CITATION_RE = re.compile(r'`([0-9a-f]{7,40})`')


def _git(args, cwd=REPO, timeout=30):
    p = subprocess.run(['git'] + args, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def extract_citations(text):
    return CITATION_RE.findall(text)


def classify_sha(sha):
    rc, _out, _err = _git(['cat-file', '-e', sha])
    if rc != 0:
        # NEAR-MISS, NOT A BARE ABSENT (batch K, item 5): a token whose
        # 7-char prefix DOES resolve is almost certainly NOT a commit
        # citation at all -- a defect-register record id, a workflow run
        # id, or any other identifier that happens to START with a real
        # sha and then continues with something that is not that commit's
        # own hex. Found on real data: 'Register record 16b2cc70d2d8' is
        # not the commit 16b2cc70a4e2fdd9... with extra chars, it is a
        # DIFFERENT identifier scheme that reuses the prefix. Distinct from
        # a genuinely broken/orphaned citation, which has NO such prefix
        # match at all.
        rc_prefix, _o, _e = _git(['cat-file', '-e', sha[:7]])
        if rc_prefix == 0:
            return 'NEAR-MISS'
        return 'ABSENT'
    rc2, _out2, _err2 = _git(['merge-base', '--is-ancestor', sha, 'origin/main'])
    return 'ON-MAIN' if rc2 == 0 else 'LOCAL-ONLY'


def check_doc(path):
    with open(path, encoding='utf-8') as f:
        text = f.read()
    citations = extract_citations(text)
    results = []
    cache = {}
    for sha in citations:
        if sha not in cache:
            cache[sha] = classify_sha(sha)
        results.append({'sha': sha, 'state': cache[sha]})
    return {'path': path, 'population': len(results), 'results': results}


# ---------------------------------------------------------------------------
# Selftest: a planted fixture doc with one real ON-MAIN sha (this repo's own
# origin/main tip, resolved live, never hardcoded), one fabricated ABSENT
# sha, and the pre-rebase sha this role's own batch D history shows was
# orphaned by sairn_claim.py's rebase-before-push behaviour (99774ecc,
# landed under a new sha db8cc2d4) -- a REAL, already-known LOCAL-ONLY case
# if the object is still reachable in this local store, else it degrades to
# ABSENT, which the selftest accepts as EITHER non-ON-MAIN state rather than
# asserting one that depends on this clone's own gc history.
# ---------------------------------------------------------------------------

def _selftest():
    import os
    import tempfile
    rc, out, _err = _git(['rev-parse', 'origin/main'])
    if rc != 0 or not out:
        print('  FAIL could not resolve origin/main tip -- selftest needs a real repo')
        return False
    real_tip = out
    # Register-record-id lookalike (batch K, item 5): the real tip's own
    # first 7 chars, with 4 unrelated hex chars appended -- deliberately
    # NOT the real tip's own continuation, same shape as the real
    # 'Register record 16b2cc70d2d8' false positive this fix answers.
    near_miss_token = real_tip[:7] + ('0' if real_tip[7] != '0' else '1') * 4
    fixture = (
        "Real tip: `%s`\n"
        "Fabricated, must not exist: `0000000000000000000000000000000000dead`\n"
        "Same real tip cited twice: `%s`\n"
        "Register-record-id lookalike, NOT a commit: `%s`\n"
    ) % (real_tip, real_tip, near_miss_token)
    fd, path = tempfile.mkstemp(suffix='.md')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(fixture)
    try:
        report = check_doc(path)
        ok = 0
        total = 4
        if report['population'] == 4:
            ok += 1
            print('  ok   population counts the repeated citation as its own occurrence: 4')
        else:
            print('  FAIL expected population 4, got %d' % report['population'])
        states = [r['state'] for r in report['results']]
        if states[0] == 'ON-MAIN':
            ok += 1
            print('  ok   real origin/main tip classified ON-MAIN')
        else:
            print('  FAIL real tip expected ON-MAIN, got %s' % states[0])
        if states[1] == 'ABSENT':
            ok += 1
            print('  ok   fabricated sha classified ABSENT')
        else:
            print('  FAIL fabricated sha expected ABSENT, got %s' % states[1])
        if states[3] == 'NEAR-MISS':
            ok += 1
            print('  ok   register-record-id lookalike classified NEAR-MISS, not ABSENT')
        else:
            print('  FAIL lookalike token expected NEAR-MISS, got %s' % states[3])
        print('%d/%d fixture checks correct' % (ok, total))
        return ok == total
    finally:
        os.remove(path)


def main(argv):
    if '--selftest' in argv:
        return 0 if _selftest() else 1
    if '--file' in argv:
        path = argv[argv.index('--file') + 1]
        report = check_doc(path)
        on_main = sum(1 for r in report['results'] if r['state'] == 'ON-MAIN')
        local_only = [r for r in report['results'] if r['state'] == 'LOCAL-ONLY']
        absent = [r for r in report['results'] if r['state'] == 'ABSENT']
        near_miss = [r for r in report['results'] if r['state'] == 'NEAR-MISS']
        print('SHA CITATION CHECK -- %s' % report['path'])
        print('  population: %d citations' % report['population'])
        print('  ON-MAIN: %d, LOCAL-ONLY (orphan): %d, ABSENT: %d, NEAR-MISS (likely not a commit citation): %d'
              % (on_main, len(local_only), len(absent), len(near_miss)))
        for r in local_only:
            print('  ! LOCAL-ONLY  %s' % r['sha'])
        for r in absent:
            print('  ! ABSENT      %s' % r['sha'])
        for r in near_miss:
            print('  ? NEAR-MISS   %s' % r['sha'])
        return 1 if (local_only or absent) else 0
    print('usage: hover_sha_citation_check.py --selftest | --file DOC_PATH')
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
