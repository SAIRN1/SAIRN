#!/usr/bin/env python
"""citation_resolve_check.py (hover2's own build, batch P item 9) -- refuses
a log append that cites a tool/script/file path not actually resolvable in
git, and separately re-checks the existing log for the same gap.

WHY THIS EXISTS. Item 8 this same batch found a real instance of exactly
the shape another hover instance's own item 8 named: hover2_code_normalize.py
was cited (seq626) as "built... in this role's own tooling directory" and
genuinely exists -- but only at the session-private log-repo path, never
landed under tools-hover2/ where origin/main (and any future audit or build
agent) could find it. The citation was true about intent, not about what a
second reader could verify.

TWO MODES, deliberately different scopes:

  --validate --ref "path1,path2,..." [--repo PATH] [--git-ref REF]
      For hover_log.py's OWN --ref field at append time (not free prose --
      scanning summary text for incidental illustrative filenames like
      "tests/a.py" would refuse legitimate entries on noise, which is the
      wrong failure mode for a GATE). Checks every comma-separated token
      that looks like a real path (contains '/' AND ends in one of
      .py/.js/.md/.json/.html/.sql/.txt) against `git ls-tree <git-ref>`.
      REFUSES (exit 1) if any such token does not resolve. Exit 0 if every
      path-shaped token resolves, or there were none to check (a bare
      commit sha, a seq number, a resource name -- --ref carries all of
      these and only the path-shaped subset is this tool's business).

  --recheck [--log PATH] [--repo PATH] [--git-ref REF]
      Re-derives the same raw mechanical count item 8 produced by hand:
      every path-shaped citation across the WHOLE log's summary/ref/source
      fields, checked against the given git ref. Prints checked/resolved/
      ambiguous/missing counts and the missing list. THIS IS A RAW COUNT,
      NOT A TRIAGED ONE -- most raw misses are scratchpad files, this
      role's own log-repo-only infrastructure, or third-party mentions, not
      defects (item 8's own handoff-worthy output named this explicitly).
      Exit 1 if raw missing > 0 (a human-triage prompt, not a verdict),
      exit 0 if raw missing == 0.

Usage:
  python citation_resolve_check.py --validate --ref "tools-hover2/x.py,seq720" [--repo PATH]
  python citation_resolve_check.py --recheck [--repo PATH]
  python citation_resolve_check.py --selftest
"""
import argparse
import os
import re
import subprocess
import sys
import json

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
# NOT os.path.join(HERE, ...) -- the real log lives OUTSIDE every git clone,
# under ~/.claude/projects/<project-dir>/hover-audit-log/ (this role's own
# memory note "hover-self-log-location"; the SAME class of bug this batch's
# item 6 fixed in tool_provenance_status.py, caught here by running this
# tool for real rather than assumed correct from the pattern).
DEFAULT_LOG = os.path.join(
    os.path.expanduser('~'), '.claude', 'projects',
    'C--Users-marsh-Documents-SAIRN-hover2', 'hover-audit-log',
    'hover-audit-log.jsonl')

PATH_EXTS = ('.py', '.js', '.md', '.json', '.html', '.sql', '.txt')
PATH_RE = re.compile(
    r'(?<![\w.])(\.?(?:[A-Za-z0-9_.\-]+/)*[A-Za-z0-9_\-]+\.(?:py|js|md|json|html|sql|txt))\b'
)


def git_tree(repo, git_ref):
    out = subprocess.run(['git', 'ls-tree', '-r', '--name-only', git_ref],
                          cwd=repo, capture_output=True, text=True, check=True)
    return set(out.stdout.splitlines())


def is_path_shaped(token):
    token = token.strip()
    return '/' in token and token.endswith(PATH_EXTS)


def validate_ref_field(ref_value, repo, git_ref):
    """Returns (ok: bool, checked: list, missing: list)."""
    tokens = [t.strip() for t in ref_value.split(',') if t.strip()]
    candidates = [t for t in tokens if is_path_shaped(t)]
    if not candidates:
        return True, [], []
    tree = git_tree(repo, git_ref)
    missing = [c for c in candidates if c not in tree]
    return (len(missing) == 0), candidates, missing


def extract_citations_from_text(blob):
    found = set()
    for m in PATH_RE.finditer(blob):
        found.add(m.group(1))
    return found


def recheck(log_path, repo, git_ref):
    tree = git_tree(repo, git_ref)
    all_citations = {}
    n_entries = 0
    with open(log_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            n_entries += 1
            e = json.loads(line)
            texts = []
            if e.get('summary'):
                texts.append(e['summary'])
            if e.get('ref'):
                texts.append(e['ref'])
            if e.get('source'):
                texts.append(str(e['source']))
            blob = ' '.join(texts)
            for p in extract_citations_from_text(blob):
                all_citations.setdefault(p, set()).add(e.get('seq'))

    basenames = {}
    for t in tree:
        basenames.setdefault(t.rsplit('/', 1)[-1], []).append(t)

    checked = sorted(all_citations.keys())
    missing, ambiguous = [], []
    for p in checked:
        if p in tree:
            continue
        bn = p.rsplit('/', 1)[-1]
        if '/' not in p and bn in basenames:
            ambiguous.append(p)
            continue
        missing.append(p)

    return {
        'entries': n_entries,
        'checked': len(checked),
        'resolved': len(checked) - len(missing) - len(ambiguous),
        'ambiguous': len(ambiguous),
        'missing': missing,
    }


def _selftest():
    import tempfile
    import shutil

    tmp = tempfile.mkdtemp(prefix='citresolve_')
    try:
        subprocess.run(['git', 'init', '-q'], cwd=tmp, check=True)
        subprocess.run(['git', 'config', 'user.email', 'x@example.invalid'], cwd=tmp, check=True)
        subprocess.run(['git', 'config', 'user.name', 'x'], cwd=tmp, check=True)
        # seed one committed file so HEAD exists
        with open(os.path.join(tmp, 'seed.txt'), 'w') as f:
            f.write('seed\n')
        subprocess.run(['git', 'add', 'seed.txt'], cwd=tmp, check=True)
        subprocess.run(['git', 'commit', '-q', '-m', 'seed'], cwd=tmp, check=True)

        # ARM 1: cite a path that has NEVER been committed -> must REFUSE.
        ok, checked, missing = validate_ref_field(
            'tools-hover2/never_committed.py,seq1', tmp, 'HEAD')
        assert ok is False, "uncommitted citation must refuse, got ok=True"
        assert 'tools-hover2/never_committed.py' in missing

        # ARM 2 (the real transition, not a fixture planted directly): create
        # the file for real, THEN commit it, THEN check the SAME citation
        # again -- must now PASS.
        os.makedirs(os.path.join(tmp, 'tools-hover2'), exist_ok=True)
        with open(os.path.join(tmp, 'tools-hover2', 'never_committed.py'), 'w') as f:
            f.write('# now real\n')
        subprocess.run(['git', 'add', 'tools-hover2/never_committed.py'], cwd=tmp, check=True)
        subprocess.run(['git', 'commit', '-q', '-m', 'land it'], cwd=tmp, check=True)
        ok2, checked2, missing2 = validate_ref_field(
            'tools-hover2/never_committed.py,seq1', tmp, 'HEAD')
        assert ok2 is True, "citation after real commit must pass, got missing=%r" % missing2

        # ARM 3: a --ref value with no path-shaped token at all (just a sha
        # and a seq) must pass trivially -- nothing to check is not a miss.
        ok3, checked3, missing3 = validate_ref_field('4ec0d5d5,seq720', tmp, 'HEAD')
        assert ok3 is True and checked3 == [], "non-path ref tokens must not be checked"

        # ARM 4: a bare filename with no directory (the --ref convention
        # elsewhere in this role's own log, e.g. "SKILL.md") is intentionally
        # NOT validated by --validate (ambiguous-vs-missing needs the full
        # basename index, which --recheck builds and --validate deliberately
        # does not, to stay a cheap per-append gate) -- confirm it is simply
        # not a candidate.
        assert is_path_shaped('SKILL.md') is False

        print("ALL SELFTEST CASES PASS")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--validate', action='store_true')
    ap.add_argument('--recheck', action='store_true')
    ap.add_argument('--ref', default='')
    ap.add_argument('--repo', default=DEFAULT_REPO)
    ap.add_argument('--log', default=DEFAULT_LOG)
    ap.add_argument('--git-ref', default='origin/main')
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args()

    if args.selftest:
        return _selftest()

    if args.validate:
        ok, checked, missing = validate_ref_field(args.ref, args.repo, args.git_ref)
        if not checked:
            print("OK: no path-shaped citation in --ref to check")
            return 0
        if ok:
            print("OK: %d path-shaped citation(s) all resolve on %s" % (len(checked), args.git_ref))
            return 0
        print("REFUSING: %d of %d path-shaped citation(s) do not resolve on %s" %
              (len(missing), len(checked), args.git_ref))
        for m in missing:
            print("  MISSING: %s" % m)
        return 1

    if args.recheck:
        r = recheck(args.log, args.repo, args.git_ref)
        print("entries=%d checked=%d resolved=%d ambiguous=%d missing=%d" %
              (r['entries'], r['checked'], r['resolved'], r['ambiguous'], len(r['missing'])))
        for m in r['missing']:
            print("  MISSING: %s" % m)
        return 1 if r['missing'] else 0

    ap.print_help()
    return 2


if __name__ == '__main__':
    sys.exit(main())
