"""Which tool stages EVERYTHING, instead of the files it means to commit?

Run:  python tools/staging_discipline_scan.py
      python tools/staging_discipline_scan.py --json

── WHY ─────────────────────────────────────────────────────────────────────
`git add -A` cannot tell a file you meant to commit from one that happens to be
in the tree. On this repo that has cost three incidents:

  * conflict markers committed into tools/tooling_inventory.py and two generated
    documents, from a retry loop that ran `git add -A` during a rebase;
  * the same thing again, hours later, in the same session;
  * a GitHub personal access token swept into a commit from a
    regenerate-after-rebase step. The push gate caught it, which is luck.

And then a fourth, which is why this exists rather than a rule: `push_retry.py`
-- THE TOOL WRITTEN TO REPLACE THOSE HAND-WRITTEN LOOPS -- used `git add -A` in
its own regenerate step, forty lines below its own header quoting that exact line
as the hazard. Nothing swept for it. It was found by reading the file for an
unrelated reason.

── WHAT IT FLAGS ───────────────────────────────────────────────────────────
A `git add` that stages by BREADTH rather than by name:

    git add -A          git add --all       git add .
    git add -u          git add --update    git commit -a / --all

── WHAT IT IS NOT ──────────────────────────────────────────────────────────
REPORT-ONLY, and it must stay that way. Some of these are correct: a probe that
builds a sandbox repo and commits the whole thing has no list to name, and
`git add -u` inside a resolver that has just rewritten a known set is a different
risk from `git add -A` in a retry loop. A gate here would be cleared by rewording
the comment above the line rather than by changing what it stages.

So this counts and names. The judgement stays with a reader.

── COMMENT-AWARE, AND THAT IS THE WHOLE DIFFICULTY ─────────────────────────
Five text-reading gates on this platform have matched documentation as if it were
code: the SQL preflight on a literal beginning with `--`, the Tier A gate on the
word "quotes" in a docstring about quote characters, the fail-open scanner
counting its own docstring six times, the claim matcher on a blocker clause, and
the live-probe audit on a licence key named in prose.

**`push_retry.py` is the exact trap.** Its header QUOTES the defective loop it
replaces, so a naive grep finds `git add -A` there and reports a tool that is
now correct. Its docstring must NOT match; its code must. The control below
drives both directions against that real file at two points in its history.

WORD BOUNDARIES, because `git add -A` and `git added` and `git add -Alpha` are
three different strings, and a substring match conflates them.

WHAT IT CANNOT SEE, said here rather than discovered later:
  * a staging command built at run time from a variable;
  * `git add` issued through a helper that takes the flag as an argument;
  * a shell script invoked from a tool it does not read;
  * whether a flagged line is CORRECT, which is the judgement it declines to
    make and the reason it is report-only.
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from checker_kit import (EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN,  # noqa: E402
                         REPO, read, finish)

CRITERIA_VERSION = '2026-09-29.1'

SCAN_DIRS = ('tools/', 'tests/', 'scripts/', '.githooks/')
SCAN_EXT = ('.py', '.js', '.sh', '')     # '' catches extension-less hooks

# THE SHAPES. Anchored on `git add` / `git commit` and then a breadth flag as a
# WHOLE WORD -- `-A` must not match `-Alpha`, and `.` must be the entire
# argument rather than any path containing a dot.
BREADTH = [
    (re.compile(r'\bgit\s+add\s+(?:[^\n;&|]*\s)?-A(?![\w-])'), 'git add -A'),
    (re.compile(r'\bgit\s+add\s+(?:[^\n;&|]*\s)?--all(?![\w-])'), 'git add --all'),
    (re.compile(r'\bgit\s+add\s+(?:[^\n;&|]*\s)?-u(?![\w-])'), 'git add -u'),
    (re.compile(r'\bgit\s+add\s+(?:[^\n;&|]*\s)?--update(?![\w-])'), 'git add --update'),
    (re.compile(r'\bgit\s+add\s+\.(?![\w/.-])'), 'git add .'),
    (re.compile(r'\bgit\s+commit\s+(?:[^\n;&|]*\s)?-a(?![\w-])'), 'git commit -a'),
    (re.compile(r'\bgit\s+commit\s+(?:[^\n;&|]*\s)?--all(?![\w-])'), 'git commit --all'),
]
# The same shapes as an ARGUMENT LIST, which is how a python tool actually
# issues them: ['git', 'add', '-A'].
ARGLIST = [
    (re.compile(r'''["']add["']\s*,\s*["']-A["']'''), 'git add -A'),
    (re.compile(r'''["']add["']\s*,\s*["']--all["']'''), 'git add --all'),
    (re.compile(r'''["']add["']\s*,\s*["']-u["']'''), 'git add -u'),
    (re.compile(r'''["']add["']\s*,\s*["']--update["']'''), 'git add --update'),
    (re.compile(r'''["']add["']\s*,\s*["']\.["']'''), 'git add .'),
    (re.compile(r'''["']commit["']\s*,\s*["']-a["']'''), 'git commit -a'),
]


def strip_comments(src, path):
    """Blank comments, PRESERVING LENGTH so line numbers still land.

    Python and shell get a quote-aware `#` scan; JS delegates to the canonical
    stripper. A blanked comment becomes spaces rather than disappearing, because
    a finding that names the wrong line is a finding nobody can check.
    """
    if path.endswith('.js'):
        from checker_kit import strip_comments as js_strip
        out = js_strip(src)
        # The JS stripper does not promise length preservation; if it did not,
        # fall back to the raw text and say so by returning None.
        return out if len(out) == len(src) else None
    SP, NL, BS = ' ', chr(10), chr(92)
    QUOTES = ("'", '"')
    out, i, n, quote = [], 0, len(src), None
    while i < n:
        c = src[i]
        if quote:
            if c == BS and i + 1 < n:
                out.append(src[i:i + 2]); i += 2; continue
            if c == quote:
                quote = None
            out.append(c); i += 1; continue
        if c in QUOTES:
            quote = c; out.append(c); i += 1; continue
        if c == '#':
            j = src.find(NL, i)
            end = n if j < 0 else j
            out.append(SP * (end - i)); i = end; continue
        out.append(c); i += 1
    return ''.join(out)


def scan_text(src, path):
    """[(line, shape, excerpt)] for every breadth-staging call in CODE."""
    masked = strip_comments(src, path)
    hits = []
    if masked is None:
        return None                      # could not mask -> caller decides
    # A DOCSTRING IS NOT A COMMENT to the tokenizer, and push_retry.py's hazard
    # quote lives in one. Blank triple-quoted blocks too, length-preserved.
    def _blank(txt):
        # NEWLINES SURVIVE. Replacing them with spaces collapses the line count
        # and every finding after the first docstring lands on the wrong line --
        # which is how the first run of this tool reported `git add -A` against
        # `import sys`. Length AND line structure both have to be preserved.
        return ''.join(ch if ch == chr(10) else ' ' for ch in txt)
    TQ = [chr(34) * 3, chr(39) * 3]
    for q in TQ:
        pos = 0
        while True:
            a = masked.find(q, pos)
            if a < 0:
                break
            b = masked.find(q, a + 3)
            if b < 0:
                break
            b += 3
            masked = masked[:a] + _blank(masked[a:b]) + masked[b:]
            pos = b
    # ── A BACKTICKED PHRASE IS PROSE, NOT A CALL ────────────────────────
    # Found by this tool's own control on its first run. push_retry.py's REFUSAL
    # MESSAGES quote the hazard inside string literals -- "`git add -A` would
    # stage the conflict markers" -- and a string literal is code to the
    # comment-stripper, correctly, because `subprocess.run(['git','add','-A'])`
    # lives in string literals too.
    #
    # The discriminator is the BACKTICKS. Nothing that is actually run is
    # wrapped in them; they are markdown in a sentence a human reads. Narrow
    # enough to state, and driven in both directions by the fixtures: a
    # backticked mention is not a site, and os.system("git add -A") still is.
    #
    # This is the sixth text-reading gate on this platform to meet the
    # prose-as-code problem, and the first to meet it in its own control before
    # publishing a number.
    def _backticked(text, a, b):
        BT = chr(96)
        return (a > 0 and text[a - 1] == BT) and (b < len(text) and text[b] == BT)

    for pats in (BREADTH, ARGLIST):
        for rx, shape in pats:
            for m in rx.finditer(masked):
                if _backticked(masked, m.start(), m.end()):
                    continue
                line = masked[:m.start()].count(chr(10)) + 1
                raw = src.split(chr(10))[line - 1].strip()
                hits.append((line, shape, raw[:110]))
    hits.sort()
    # de-duplicate: one line can match both the shell and arglist form
    out, seen = [], set()
    for line, shape, raw in hits:
        if line in seen:
            continue
        seen.add(line)
        out.append((line, shape, raw))
    return out


def candidates():
    r = subprocess.run(['git', '-C', REPO, 'ls-files'] + list(SCAN_DIRS),
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    if r.returncode != 0:
        return None
    out = []
    for f in r.stdout.split('\n'):
        f = f.strip()
        if not f or '__pycache__' in f:
            continue
        ext = os.path.splitext(f)[1]
        if ext in SCAN_EXT:
            out.append(f)
    return sorted(out)


def main(argv=None):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args(argv)

    cands = candidates()
    if cands is None:
        print('COULD NOT RUN: `git ls-files` failed, so the universe is unknown. '
              'An empty scan and a clean repo look identical and this refuses to '
              'be either.', file=sys.stderr)
        return EXIT_COULD_NOT_RUN
    if not cands:
        print('COULD NOT RUN: no candidate file matched %s. The scan found '
              'nothing to read, which is not the same as finding nothing.'
              % ' '.join(SCAN_DIRS), file=sys.stderr)
        return EXIT_COULD_NOT_RUN

    findings, unreadable, checked = [], [], 0
    per_file = {}
    for rel in cands:
        src = read(os.path.join(REPO, rel))
        if src is None:
            unreadable.append('%s could not be read' % rel)
            continue
        if 'git' not in src:
            checked += 1
            continue
        hits = scan_text(src, rel)
        if hits is None:
            unreadable.append('%s could not be comment-masked without moving its '
                              'line numbers, so it was NOT scanned' % rel)
            continue
        checked += 1
        if hits:
            per_file[rel] = hits
            for line, shape, raw in hits:
                findings.append('%s:%d  %-16s %s' % (rel, line, shape, raw))

    print('STAGING DISCIPLINE SCAN')
    print('  criteria                  : %s' % CRITERIA_VERSION)
    print('  CHECKED / UNIVERSE        : %d / %d file(s) under %s'
          % (checked, len(cands), ' '.join(SCAN_DIRS)))
    print('  files staging by breadth  : %d' % len(per_file))
    print('  call sites                : %d' % len(findings))
    print()
    for rel in sorted(per_file):
        print('  %s' % rel)
        for line, shape, raw in per_file[rel]:
            print('      :%-5d %-16s %s' % (line, shape, raw))
    print()
    print('  REPORT-ONLY, and deliberately. Some of these are correct -- a probe')
    print('  that builds a sandbox repo has no file list to name. This tool')
    print('  counts and names; whether a site is right is a read, not a verdict.')
    print('  IT CANNOT SEE a staging command built at run time, one issued')
    print('  through a helper, or a shell script it does not read.')

    if args.json:
        print(json.dumps({'criteria': CRITERIA_VERSION, 'checked': checked,
                          'universe': len(cands), 'findings': findings,
                          'could_not_run': unreadable}, indent=2))

    # REPORT-ONLY: findings do not fail the run. An unreadable file does --
    # that is a could-not-check, and this tool's whole subject is a check that
    # quietly did not happen.
    if unreadable:
        for u in unreadable:
            print('COULD NOT RUN: ' + u, file=sys.stderr)
        return EXIT_COULD_NOT_RUN
    return EXIT_CLEAN


if __name__ == '__main__':
    sys.exit(main())
