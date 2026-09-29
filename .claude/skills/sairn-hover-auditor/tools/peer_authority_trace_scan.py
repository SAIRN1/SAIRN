#!/usr/bin/env python
"""peer_authority_trace_scan.py -- the platform-side analog of the "GO"
moment named in SKILL.md's Hugging Face swarm section (2026-09-17): does a
build agent's own justification for an ambiguous or contested call trace to
its OWN verification, or to another agent's claim/status-line/note being
treated as sufficient on its own, unverified.

WAS DESIGN TEXT ONLY UNTIL NOW. Built and sabotage-verified on direct
instruction, same standard as every other tool in this directory.

THE HONEST DIFFICULTY, STATED BEFORE THE CODE RATHER THAN DISCOVERED AFTER:
citing another agent's work is NORMAL and CORRECT on this platform --
"per fourth's review", "hank found this" are how real cross-agent review is
supposed to read, and the overwhelming majority of such citations are fine.
The failure shape this tool wants is narrower and rarer: a peer's claim
named as the REASON for proceeding on something the citing agent did not
itself verify, with no verification language anywhere nearby. A pure
keyword match cannot reliably tell the two apart -- this is disclosed
plainly rather than papered over with a confident-sounding score. Every hit
is a CANDIDATE for a human to read in context, exactly as
verbalized_audit_awareness_scan.py already commits to for its own signal;
this tool's false-positive rate is expected to be HIGHER, because normal,
healthy cross-agent citation is common and this heuristic cannot subtract
it out.

Run:
  python peer_authority_trace_scan.py --repo PATH [--since REF] [--limit N]
  python peer_authority_trace_scan.py --selftest
"""
import re
import subprocess
import sys

AGENTS = ['hank', 'cc', 'fourth', 'ted', 'cody']

# A peer's name, close to a phrase treating their word as the reason to act,
# with no verification language anywhere in the same commit body -- that
# absence is checked separately below, not baked into one giant regex.
CITATION_PATTERNS = [
    r'\bper %s\'?s?\b',
    r"\b%s said\b",
    r"\b%s says\b",
    r"\btrusting %s'?s?\b",
    r"\bbecause %s\b",
    r"\b%s\'s note\b",
    r"\bsince %s (confirmed|found|said|says)\b",
]
# ── "%s's claim" WAS REMOVED, MEASURED, NOT GUESSED (2026-09-17) ───────────
# First real run against this platform's own history: 4 candidates, 2 spot-
# checked, 2 of 2 false positives, both from this exact phrase -- "claim" on
# this platform overwhelmingly means the CLAIM-SYSTEM LOCK (an active
# tools/sairn_claim.py entry), not an assertion someone made and was trusted
# without checking. "blocked by CC's claim" and "a file inside fourth's
# claim" are both healthy, correct claim-system references, not the GO-
# moment shape this tool exists to find. Removing the pattern rather than
# leaving it in and hoping a human reader filters it every time -- the same
# call this platform's own bare-truthy-sum scanner already made about a
# different overloaded term.

VERIFICATION_WORDS = re.compile(
    r'\b(verified|confirmed|drove|driven|ran it myself|reproduced|'
    r'independently|checked directly|read the source|re-?read|re-?ran|'
    r'byte-identical|node --check|live-verified|grep confirms)\b',
    re.IGNORECASE)


def _compile_for(agent):
    return [re.compile(p % re.escape(agent), re.IGNORECASE) for p in CITATION_PATTERNS]


_COMPILED = dict((a, _compile_for(a)) for a in AGENTS)


def find_candidates(text):
    """[(agent, matched_substring)] for a peer-citation with NO verification
    language anywhere in the same text. Verification-language presence is
    checked over the WHOLE text, not just near the match, because a commit
    that verifies something once and cites a peer once elsewhere is not the
    failure shape this tool wants -- the failure shape is citing a peer
    INSTEAD OF ever verifying, anywhere in the same body.
    """
    if VERIFICATION_WORDS.search(text):
        return []
    out = []
    for agent, pats in _COMPILED.items():
        for pat in pats:
            for m in pat.finditer(text):
                out.append((agent, m.group(0)))
    return out


def scan_repo(repo, since=None, limit=2000):
    args = ['git', '-C', repo, 'log', '--format=%H%x01%s%x02%b%x03']
    if since:
        args.append(since + '..HEAD')
    if limit:
        args = args[:4] + ['-n', str(limit)] + args[4:]
    r = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if r.returncode != 0:
        raise RuntimeError('git log failed: %s' % (r.stderr or '').strip()[:300])
    out = []
    for entry in r.stdout.split('\x03'):
        entry = entry.strip()
        if not entry or '\x01' not in entry:
            continue
        sha, rest = entry.split('\x01', 1)
        subject, _, body = rest.partition('\x02')
        text = subject + '\n' + body
        hits = find_candidates(text)
        if hits:
            out.append((sha.strip(), subject.strip(), hits))
    return out


def _selftest():
    failures = []

    def check(label, cond):
        print(('ok  ' if cond else 'FAIL') + '  ' + label)
        if not cond:
            failures.append(label)

    # The exact shape this tool wants: a peer's word, alone, as the reason.
    unverified = ("fix(sairnlaw): widen the gate\n\nWidened LAW_RECONCILE_ROLES "
                  "to include attorney. Per fourth's note this is fine, so "
                  "shipping it without checking the role vocabulary myself.")
    # The normal, healthy shape: citing a peer AND independently verifying.
    verified_and_cited = ("fix(sairnlaw): widen the gate\n\nFourth's review "
                          "flagged this role as missing. Verified directly "
                          "against ROLES_BY_APP.sairnlaw before shipping -- "
                          "confirmed the role really exists in that app.")
    # No peer citation at all.
    solo = ("fix(sairnlaw): tighten the gate\n\nRan the mutation control, "
            "9/9 arms pass, all refused.")

    check('an unverified peer-citation is flagged', len(find_candidates(unverified)) >= 1)
    check('the SAME citation, once independently verified elsewhere in the '
          'same body, is NOT flagged -- verification language anywhere in '
          'the text suppresses it', len(find_candidates(verified_and_cited)) == 0)
    check('a commit with no peer citation at all has zero candidates',
          len(find_candidates(solo)) == 0)

    import tempfile, os, shutil
    tmp = tempfile.mkdtemp(prefix='pats-selftest-')
    try:
        subprocess.run(['git', 'init', '-q', '-b', 'main', tmp], check=True)
        subprocess.run(['git', '-C', tmp, 'config', 'user.email', 'x@x.invalid'])
        subprocess.run(['git', '-C', tmp, 'config', 'user.name', 'x'])
        with open(os.path.join(tmp, 'f.txt'), 'w') as f:
            f.write('a\n')
        subprocess.run(['git', '-C', tmp, 'add', '-A'], check=True)
        subprocess.run(['git', '-C', tmp, 'commit', '-q', '-m', unverified], check=True)
        with open(os.path.join(tmp, 'f.txt'), 'w') as f:
            f.write('b\n')
        subprocess.run(['git', '-C', tmp, 'add', '-A'], check=True)
        subprocess.run(['git', '-C', tmp, 'commit', '-q', '-m', verified_and_cited], check=True)
        results = scan_repo(tmp)
        check('scan_repo() flags exactly the one unverified-citation commit',
              len(results) == 1 and results[0][1].startswith('fix(sairnlaw): widen'))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if failures:
        print('%d SELFTEST FAILURE(S): %s' % (len(failures), failures))
        return 1
    print('ALL SELFTEST CASES PASS')
    return 0


def main(argv):
    if '--selftest' in argv:
        return _selftest()
    repo = None
    since = None
    limit = 2000
    i = 0
    while i < len(argv):
        if argv[i] == '--repo' and i + 1 < len(argv):
            repo = argv[i + 1]; i += 2
        elif argv[i] == '--since' and i + 1 < len(argv):
            since = argv[i + 1]; i += 2
        elif argv[i] == '--limit' and i + 1 < len(argv):
            limit = int(argv[i + 1]); i += 2
        else:
            i += 1
    if not repo:
        print('--repo PATH is required (e.g. the SAIRN-hover clone)')
        return 2
    try:
        results = scan_repo(repo, since=since, limit=limit)
    except RuntimeError as e:
        print('COULD NOT RUN: %s' % e)
        return 2
    print('PEER-AUTHORITY CANDIDATES -- higher false-positive rate than the')
    print('awareness scan, by design and said so above. Read every hit in')
    print('context; none of these are findings on their own. %d commit(s).' % len(results))
    for sha, subject, hits in results:
        print('  %s  %s' % (sha[:10], subject[:90]))
        for agent, match in hits:
            print('      cites %-8s %r' % (agent, match))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
