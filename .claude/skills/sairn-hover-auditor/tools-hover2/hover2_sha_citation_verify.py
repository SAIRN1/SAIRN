#!/usr/bin/env python
"""hover2_sha_citation_verify.py -- mechanical SHA-citation verifier, hover2's
own, independent of H1's identity-attribution tool (citation_class_check.py,
which checks LINE-ANCHOR content at a recorded blob sha; this tool checks
whether a cited SHA is a real object that resolves ON origin/main at all --
a cheaper, different question, asked of any tracking doc, not just the
hover log).

INPUT: a path to any tracking doc. Every backtick-wrapped lowercase-hex
token 7-40 chars (`` `[0-9a-f]{7,40}` ``, the format this repo's docs use for
commit citations -- confirmed against SAIRN-OPEN-WORK-INDEX.md before
writing this regex, not assumed) is a citation claim: "this SHA exists."

PER CITATION (not deduped -- a sha repeated five times is five claims a
reader will trust five times, so five get checked and five get counted):
  1. `git rev-parse --quiet --verify <sha>` -- does it resolve to ANY real
     object in this repo's object store at all. Fails closed: ambiguous
     short shas and garbage both come back as a miss, never a false pass.
  2. If it resolves and `git cat-file -t` says `commit`: is it an ancestor
     of origin/main (`git merge-base --is-ancestor`)? A commit that exists
     but lives only on some other branch or a rebased-away tip is NOT
     verified here -- "exists on origin/main" is the literal ask.
  3. If it resolves but is not a commit (blob/tree -- this repo's hover
     logs cite blob shas elsewhere), it is reported EXISTS-NOT-A-COMMIT
     and counted as unverified for this tool's purpose, named rather than
     silently folded into either bucket, because reachability-from-main is
     not a question a blob sha answers.

Three-state output per citation: VERIFIED, MISS (does not resolve at all),
EXISTS-NOT-ON-MAIN (resolves, is a commit, not an ancestor of origin/main),
EXISTS-NOT-A-COMMIT (resolves, is not a commit). Only VERIFIED counts toward
"X of Y verified." The other three are each named in the miss list with
their own reason -- never collapsed into one undifferentiated "miss," same
discipline as the UNVERIFIABLE-NO-SHA class next door in citation_class_check.

FAILS CLOSED if git itself is unusable (not a repo, origin/main unresolvable):
prints which check could not run and exits 2. A tool that cannot reach
origin/main and silently checked local HEAD instead would be reporting a
pass it never performed -- the exact shape CLAUDE.md PR 1.11 names.

Usage:
  python hover2_sha_citation_verify.py <path-to-tracking-doc> [--repo PATH]
  python hover2_sha_citation_verify.py --selftest
"""
import argparse
import os
import re
import subprocess
import sys
import tempfile

CITATION = re.compile(r'`([0-9a-f]{7,40})`')


def run(args, cwd):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True)


def resolve_origin_main(repo):
    """Fails closed: returns None (never a stand-in ref) if origin/main
    cannot be resolved, so the caller can refuse rather than silently
    checking something else."""
    r = run(['git', 'rev-parse', '--quiet', '--verify', 'origin/main'], repo)
    if r.returncode != 0 or not r.stdout.strip():
        return None
    return r.stdout.strip()


def check_repo_usable(repo):
    r = run(['git', 'rev-parse', '--git-dir'], repo)
    if r.returncode != 0:
        return "not a git repository: %s" % repo
    return None


def extract_citations(doc_path):
    with open(doc_path, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()
    out = []
    for lineno, line in enumerate(lines, start=1):
        for m in CITATION.finditer(line):
            out.append((lineno, m.group(1)))
    return out


def classify(sha, repo, origin_main):
    r = run(['git', 'rev-parse', '--quiet', '--verify', sha], repo)
    if r.returncode != 0 or not r.stdout.strip():
        return ('MISS', 'does not resolve to any object')
    full = r.stdout.strip()
    t = run(['git', 'cat-file', '-t', full], repo)
    if t.returncode != 0:
        return ('MISS', 'resolved but cat-file -t failed: %s' % t.stderr.strip())
    kind = t.stdout.strip()
    if kind != 'commit':
        return ('EXISTS-NOT-A-COMMIT', 'object is a %s, not a commit' % kind)
    anc = run(['git', 'merge-base', '--is-ancestor', full, origin_main], repo)
    if anc.returncode == 0:
        return ('VERIFIED', None)
    return ('EXISTS-NOT-ON-MAIN', 'commit exists but is not an ancestor of origin/main')


def verify_doc(doc_path, repo):
    err = check_repo_usable(repo)
    if err:
        return {'ok': False, 'error': err}
    origin_main = resolve_origin_main(repo)
    if origin_main is None:
        return {'ok': False,
                'error': 'origin/main could not be resolved -- refusing rather '
                         'than checking local HEAD or any other ref instead'}
    citations = extract_citations(doc_path)
    results = []
    for lineno, sha in citations:
        state, reason = classify(sha, repo, origin_main)
        results.append({'line': lineno, 'sha': sha, 'state': state, 'reason': reason})
    verified = sum(1 for r in results if r['state'] == 'VERIFIED')
    return {
        'ok': True,
        'doc': doc_path,
        'origin_main': origin_main,
        'total_citations': len(results),
        'verified': verified,
        'results': results,
    }


def report(result):
    if not result['ok']:
        print("COULD NOT RUN: %s" % result['error'])
        return 2
    print("doc: %s" % result['doc'])
    print("origin/main: %s" % result['origin_main'])
    print("%d of %d citations verified" % (result['verified'], result['total_citations']))
    misses = [r for r in result['results'] if r['state'] != 'VERIFIED']
    if misses:
        print("--- %d miss(es) ---" % len(misses))
        for r in misses:
            print("  line %d  `%s`  %s  (%s)" % (r['line'], r['sha'], r['state'], r['reason']))
    else:
        print("no misses")
    return 0


# ---------------------------------------------------------------------------
# selftest: one fixture doc with a real sha (this repo's own origin/main
# tip, resolved live -- never hardcoded, a hardcoded sha goes stale the
# first time main moves) and one fabricated sha that cannot resolve. The
# tool must tell them apart: 1 of 2 verified, the fake one named as the miss.
# ---------------------------------------------------------------------------
def selftest():
    repo = os.path.dirname(os.path.abspath(__file__))
    while repo != os.path.dirname(repo):
        if os.path.isdir(os.path.join(repo, '.git')):
            break
        repo = os.path.dirname(repo)
    else:
        print("SELFTEST FAIL: could not locate enclosing git repo")
        return 1

    err = check_repo_usable(repo)
    if err:
        print("SELFTEST FAIL: %s" % err)
        return 1
    origin_main = resolve_origin_main(repo)
    if origin_main is None:
        print("SELFTEST FAIL: origin/main not resolvable, cannot build fixture")
        return 1

    real_sha = origin_main[:10]
    fake_sha = 'deadbeefcafe0123456789'[:12]
    # guard against the astronomically unlikely case the fake collides
    r = run(['git', 'rev-parse', '--quiet', '--verify', fake_sha], repo)
    if r.returncode == 0:
        print("SELFTEST FAIL: fixture fake sha unexpectedly resolved -- pick another")
        return 1

    fixture = (
        "# fixture tracking doc\n"
        "| real | `%s` | should verify |\n"
        "| fake | `%s` | should miss |\n"
    ) % (real_sha, fake_sha)

    with tempfile.NamedTemporaryFile('w', suffix='.md', delete=False) as f:
        f.write(fixture)
        fixture_path = f.name

    try:
        result = verify_doc(fixture_path, repo)
        if not result['ok']:
            print("SELFTEST FAIL: verify_doc errored: %s" % result['error'])
            return 1
        if result['total_citations'] != 2:
            print("SELFTEST FAIL: expected 2 citations extracted, got %d"
                  % result['total_citations'])
            return 1
        if result['verified'] != 1:
            print("SELFTEST FAIL: expected exactly 1 of 2 verified, got %d"
                  % result['verified'])
            return 1
        states = {r['sha']: r['state'] for r in result['results']}
        if states.get(real_sha) != 'VERIFIED':
            print("SELFTEST FAIL: real sha %s was not VERIFIED (got %s)"
                  % (real_sha, states.get(real_sha)))
            return 1
        if states.get(fake_sha) != 'MISS':
            print("SELFTEST FAIL: fake sha %s was not MISS (got %s)"
                  % (fake_sha, states.get(fake_sha)))
            return 1
        print("SELFTEST PASS: distinguished real (%s, VERIFIED) from fake "
              "(%s, MISS) -- 1 of 2, as expected" % (real_sha, fake_sha))
        return 0
    finally:
        os.unlink(fixture_path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('doc', nargs='?')
    ap.add_argument('--repo', default=None)
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())

    if not args.doc:
        print("usage: hover2_sha_citation_verify.py <doc-path> [--repo PATH] | --selftest")
        sys.exit(2)

    repo = args.repo or os.getcwd()
    if not os.path.isfile(args.doc):
        print("COULD NOT RUN: doc not found: %s" % args.doc)
        sys.exit(2)

    result = verify_doc(args.doc, repo)
    sys.exit(report(result))


if __name__ == '__main__':
    main()
