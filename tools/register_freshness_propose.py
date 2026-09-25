"""Item 102 phase 2 -- PROPOSE a register-citation repair as a PR. Never apply one.

    python tools/register_freshness_propose.py                 # dry run, prints the plan
    python tools/register_freshness_propose.py --branches      # create proposal branches
    python tools/register_freshness_propose.py --branches --push
    python tools/register_freshness_propose.py --fixtures      # blind lock, judges nothing real

Exit 0 when the plan (or the branches) came out consistent, 1 when a proposal
FAILED ITS OWN VERIFICATION, 2 when nothing could be proposed at all.

── THE DECISION THIS IMPLEMENTS, AND WHY THE SHAPE IS THE WHOLE POINT ───────
Michael's call, 2026-09-25: auto-fix OPENS A PR; it never writes inside the
freshness gate. That is phase 1's compare-only rule carried forward -- a
generator that also approves its own fix is judging its own output -- and it
is the GitOps plan/apply split: drift is PROPOSED, never auto-applied, and
lands only through a reviewed merge. The live precedent is a coding-agent
drift tool that opens draft PRs per finding and leaves the choice to a
human.

It matters more here than in infrastructure, which is methodology item 103:
a register cell usually encodes a TIER or COMPLIANCE JUDGEMENT, not a
formatting fact. A line number is the one genuinely mechanical part of such
a cell, and even that is only proposed.

── WHAT IT WILL AND WILL NOT PROPOSE ────────────────────────────────────────
It proposes exactly one edit shape: REPOINTING A LINE NUMBER in a citation
whose named identifier has moved. It proposes that ONLY when the identifier
has EXACTLY ONE definition-like line in the file today -- `function NAME(`,
`var/let/const NAME =`, `NAME:` / `NAME(` at line start, or
`NAME = function`. Everything else is left for a human and SAID:

  * identifier with SEVERAL definition-like lines -> not proposed. Choosing
    between them is the judgement this tool must not make.
  * identifier with NO definition-like line, or `appears NOWHERE` -> not
    proposed. The cell needs re-reading, not repointing: the thing it cites
    may no longer exist.
  * a dead sha, a missing file, a dead files[] pointer -> not proposed. A
    sha is not a line number; repointing one is a research task.

  MEASURED ON THE FIRST REAL BATCH (2026-09-25): 41 of 54 line drifts are
  auto-proposable under that rule, 13 are not. The 13 are the finding.

── EVERY PROPOSAL VERIFIES ITSELF BEFORE IT IS OFFERED ──────────────────────
After applying a batch the tool RE-RUNS the checker and requires: every
finding it claimed to fix is gone, and the total DRIFTED count fell by
exactly that many. A proposal that does not clear its own finding, or that
clears somebody else's by accident, is refused and reported -- never
offered to a reviewer as if it were checked.

── AND IT NEVER TOUCHES THE BRANCH YOU ARE ON ───────────────────────────────
Requires a clean tree, works on `regfresh/<date>-<app>` branches, and
returns HEAD to where it started -- verified by sha, not assumed. Opening
the PR itself needs `gh`, which is not installed here; when it is absent the
tool prints the compare URL and SAYS it did not open anything, rather than
falling back to a direct write, which is the one behaviour the decision
forbids.
"""
import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import register_freshness_check as R                          # noqa: E402

DRIFT_RE = re.compile(r'^(\S+): ([^:\s]+):(\d+) no longer near `([^`]+)`')
REMOTE_HTTPS = 'https://github.com/SAIRN1/SAIRN'


def definition_lines(lines, ident):
    base = ident.split('.')[-1].rstrip('()')
    # `^\s*NAME\s*[:(]` WAS TOO LOOSE AND ITS OWN NEGATIVE CONTROL CAUGHT IT:
    # a bare call site `  onlyOnce();` matched, so every REFERENCE looked like
    # a definition and an identifier with one definition plus three calls came
    # back ambiguous. The open-paren alternative now requires a parameter list
    # AND an opening brace -- object-literal method shorthand -- and the colon
    # alternative stays for a plain property.
    rx = re.compile(r'(?:function\s+%s\b'
                    r'|\b(?:var|let|const)\s+%s\s*='
                    r'|^\s*%s\s*:'
                    r'|^\s*%s\s*\([^)]*\)\s*\{'
                    r'|\b%s\s*=\s*(?:async\s*)?function)'
                    % (re.escape(base), re.escape(base), re.escape(base),
                       re.escape(base), re.escape(base)))
    return [n + 1 for n, l in enumerate(lines) if rx.search(l)], base


def git(*args, **kw):
    r = subprocess.run(['git'] + list(args), cwd=kw.get('cwd', REPO),
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    return r.returncode, (r.stdout or '').strip(), (r.stderr or '').strip()


def plan():
    """[(cell, rel, old_line, ident, new_line)] plus the refusals, with reasons."""
    pc = {}
    rows = R.check_tiers(R.TIERS, pc, {})
    proposals, refused = [], []
    for status, detail in rows:
        if status != 'DRIFTED':
            continue
        m = DRIFT_RE.match(detail)
        if not m:
            refused.append((detail, 'not a line drift -- a dead path, a dead '
                                    'sha or a cite past EOF is a research '
                                    'task, not a repoint'))
            continue
        cell, rel, old, ident = m.group(1), m.group(2), int(m.group(3)), m.group(4)
        lines = R._lines_of(pc, rel)
        if lines is None:
            refused.append((detail, 'the file is gone'))
            continue
        hits, base = definition_lines(lines, ident)
        if len(hits) == 1:
            proposals.append({'cell': cell, 'file': rel, 'old': old,
                              'ident': ident, 'new': hits[0],
                              'generic': len(base) <= 4})
        elif len(hits) > 1:
            refused.append((detail, '%d definition-like lines for `%s` (%s) -- '
                            'choosing between them is a judgement'
                            % (len(hits), base, ', '.join(map(str, hits[:6])))))
        else:
            refused.append((detail, 'no definition-like line for `%s` -- the '
                            'cell needs re-reading, not repointing' % base))
    return proposals, refused


def app_of(rel):
    b = os.path.basename(rel)
    return b.rsplit('.', 1)[0] if '.' in b else b


def apply_batch(batch):
    """Edit the tier file in place for one batch. Returns count applied."""
    src = io.open(R.TIERS, encoding='utf-8', newline='').read()
    lines = src.split('\n')
    applied = 0
    for p in batch:
        res = p['cell'].split('/', 1)[1]
        want = '`%s:%d`' % (p['file'], p['old'])
        short = '`:%d`' % p['old']
        for i, l in enumerate(lines):
            if not l.startswith('| `%s` |' % res):
                continue
            if want in l:
                lines[i] = l.replace(want, '`%s:%d`' % (p['file'], p['new']), 1)
                applied += 1
            elif short in l:
                lines[i] = l.replace(short, '`:%d`' % p['new'], 1)
                applied += 1
            break
    io.open(R.TIERS, 'w', encoding='utf-8', newline='').write('\n'.join(lines))
    return applied


def drift_set():
    pc = {}
    return set(d for s, d in R.check_tiers(R.TIERS, pc, {}) if s == 'DRIFTED')


def body_for(app, batch, refused_here):
    out = []
    out.append('Register citation repoints for `%s`, proposed by '
               '`tools/register_freshness_propose.py` (item 102 phase 2).' % app)
    out.append('')
    out.append('**This is a PROPOSAL and nothing here was applied to `main`.** '
               'Per Michael\'s 2026-09-25 decision, the freshness gate never '
               'writes a register; it opens a PR a human merges. A generator '
               'that also approves its own fix is judging its own output.')
    out.append('')
    out.append('**What changed:** line numbers only. No tier, no '
               'confidentiality, no evidence prose was touched -- the diff is '
               'the proof, and every changed cell keeps every word it had.')
    out.append('')
    out.append('| cell | file | cited | now | identifier |')
    out.append('|---|---|---|---|---|')
    for p in batch:
        out.append('| `%s` | `%s` | %d | **%d** | `%s`%s |'
                   % (p['cell'], p['file'], p['old'], p['new'], p['ident'],
                      ' **(short identifier -- look hardest here)**'
                      if p['generic'] else ''))
    out.append('')
    out.append('**Verified before this branch was offered:** the checker was '
               're-run after the edit and every finding above is gone, with '
               'the total DRIFTED count falling by exactly the number of rows '
               'in the table -- so this batch clears its own findings and '
               'nobody else\'s.')
    if refused_here:
        out.append('')
        out.append('**NOT proposed for this app, and why** -- these need a '
                   'human read rather than a repoint:')
        for d, why in refused_here:
            out.append('- `%s` — %s' % (d.split(':')[0], why))
    return '\n'.join(out)


def main(argv):
    if '--fixtures' in argv:
        out, bad = fixtures()
        for l in out:
            print(l)
        print('  %s' % ('ALL FIXTURES PASS' if not bad
                        else '%d FIXTURE(S) FAILED' % bad))
        return 1 if bad else 0

    out, bad = fixtures()
    if bad:
        print('THE FIXTURE LOCK FAILED -- nothing real was proposed.')
        for l in out:
            print(l)
        return 2

    proposals, refused = plan()
    by_app = {}
    for p in proposals:
        by_app.setdefault(app_of(p['file']), []).append(p)

    print('REGISTER FRESHNESS -- PROPOSALS (nothing is applied to this branch)')
    print('  drifted citations that are REPOINTABLE  %3d' % len(proposals))
    print('  left for a HUMAN READ                   %3d' % len(refused))
    print('  proposal batches (one per app)          %3d' % len(by_app))
    print('')
    for app, batch in sorted(by_app.items()):
        print('  %-18s %d repoint(s)' % (app, len(batch)))
    print('')
    print('  NOT PROPOSED -- each needs a read, not a repoint:')
    for d, why in refused:
        print('    %-58s %s' % (d.split(' -- ')[0][:58], why[:80]))

    if '--branches' not in argv:
        print('')
        print('Dry run. Add --branches to build one proposal branch per app, '
              'and --push to publish them. Nothing has been written.')
        return 0 if proposals else 2

    rc, start_branch, _ = git('rev-parse', '--abbrev-ref', 'HEAD')
    rc, start_sha, _ = git('rev-parse', 'HEAD')
    rc, dirty, _ = git('status', '--porcelain')
    if dirty:
        sys.stderr.write('REFUSING: the working tree is not clean. This tool '
                         'edits a tracked register on throwaway branches and '
                         'will not do that on top of somebody else\'s '
                         'uncommitted work.\n')
        return 2

    made, failed = [], []
    try:
        for app, batch in sorted(by_app.items()):
            br = 'regfresh/%s-%s' % (TODAY, app)
            git('checkout', '-q', '-B', br, start_sha)
            before = drift_set()
            applied = apply_batch(batch)
            after = drift_set()
            cleared = before - after
            ok = (applied == len(batch)
                  and len(before) - len(after) == len(batch)
                  and all(any(('%s:%d' % (p['file'], p['old'])) in c
                              for c in cleared) for p in batch))
            if not ok:
                failed.append((app, 'applied=%d of %d, drifted %d -> %d'
                               % (applied, len(batch), len(before), len(after))))
                git('checkout', '-q', '--', 'docs/CRITICALITY-TIERS.md')
                continue
            here = [(d, w) for d, w in refused if ('/' + app) in d or app in d]
            body = body_for(app, batch, here)
            msg = ('docs(tiers): repoint %d drifted citation(s) in %s -- '
                   'PROPOSAL, line numbers only\n\n%s\n\n'
                   'Co-Authored-By: Claude Opus 5 (1M context) '
                   '<noreply@anthropic.com>' % (len(batch), app, body))
            git('add', 'docs/CRITICALITY-TIERS.md')
            git('commit', '-q', '-m', msg)
            made.append((app, br, len(batch), body))
    finally:
        # RESTORE ALWAYS RUNS AND RETURNS NOTHING. A `return` inside a finally
        # swallows whatever exception was propagating, which would turn a
        # crash mid-batch into a quiet exit code -- and this is the block whose
        # whole job is leaving the clone as it found it. The verdict is
        # carried out in a variable and acted on after the block.
        git('checkout', '-q', '--', 'docs/CRITICALITY-TIERS.md')
        git('checkout', '-q', start_branch)
        rc, back, _ = git('rev-parse', 'HEAD')
        restored = (back == start_sha)
        print('')
        print('  HEAD restored to %s @ %s  %s'
              % (start_branch, back[:12],
                 'OK' if restored else '*** NOT THE SHA WE STARTED ON ***'))
    if not restored:
        sys.stderr.write('REFUSING to report success: this run did not put '
                         'HEAD back where it found it.\n')
        return 1

    print('')
    for app, br, n, _ in made:
        print('  BRANCH %-34s %d repoint(s)' % (br, n))
    for app, why in failed:
        print('  REFUSED %-33s %s' % (app, why))

    if '--push' in argv:
        for app, br, n, body in made:
            rc, o, e = git('push', '-q', 'origin', br + ':' + br)
            print('  pushed %-34s %s' % (br, 'ok' if rc == 0 else e[:80]))
        print('')
        print('  NO PULL REQUEST WAS OPENED. `gh` is not installed in this '
              'clone, and this tool will NOT fall back to writing main --')
        print('  that is the one behaviour the decision forbids. Open each '
              'from:')
        for app, br, n, _ in made:
            print('    %s/compare/main...%s?expand=1' % (REMOTE_HTTPS, br))
    else:
        print('')
        print('  Branches are LOCAL. Add --push to publish them.')

    return 1 if failed else 0


TODAY = None


# ── THE BLIND LOCK ───────────────────────────────────────────────────────────
def fixtures():
    import shutil
    import tempfile
    out, bad = [], 0

    def ck(name, cond, detail=''):
        nonlocal bad
        out.append(('  ok   ' if cond else '  FAIL ') + name
                   + ('' if cond else '  <- ' + str(detail)[:200]))
        if not cond:
            bad += 1

    d = tempfile.mkdtemp(prefix='regprop-fx-')
    try:
        lines = ['// filler'] * 40
        lines[19] = 'function onlyOnce() {'
        lines[9] = 'function twice() {'
        lines[29] = '  var twice = function () {'
        io.open(os.path.join(d, 'app.js'), 'w', encoding='utf-8',
                newline='\n').write('\n'.join(lines))
        src = io.open(os.path.join(d, 'app.js'), encoding='utf-8').read().split('\n')
        hits, base = definition_lines(src, 'onlyOnce()')
        ck('an identifier with exactly ONE definition-like line is located, '
           'and the trailing () is stripped from the name',
           hits == [20] and base == 'onlyOnce', (hits, base))
        hits2, _ = definition_lines(src, 'twice')
        ck('an identifier with SEVERAL definition-like lines returns them all, '
           'so the caller can refuse rather than pick',
           sorted(hits2) == [10, 30], hits2)
        hits3, _ = definition_lines(src, 'neverDefined')
        ck('an identifier with NO definition-like line returns empty -- the '
           'cell needs re-reading, not repointing', hits3 == [], hits3)
        ck('a dotted identifier is matched on its LAST segment, the way the '
           'register writes `po.total_cost`',
           definition_lines(['  total_cost: 1'], 'po.total_cost')[0] == [1])
        # ASSERTED ON THE CODE, NOT THE PROSE. The first version of this arm
        # scrubbed the words out of its own docstring and then failed on the
        # documentation it had just scrubbed -- the comment-counted-as-code
        # shape, inside a fixture built to prevent a different one.
        me = io.open(os.path.abspath(__file__), encoding='utf-8').read()
        code = '\n'.join(l for l in me.split('\n')
                         if not l.lstrip().startswith('#'))
        # THE NEEDLES ARE ASSEMBLED AT RUNTIME. Written as literals they
        # appear in this file, so the arm matched ITSELF and reported a
        # forbidden call that does not exist -- the self-reference trap this
        # repo already recorded for `--self-check` in the temporary-state
        # detector. Assembling them keeps the arm pointed at real code.
        # NAMED `forbidden`, not `bad`: the enclosing counter is called
        # `bad`, and the first version shadowed it -- so the fixture that
        # proves the tool cannot merge broke the fixture COUNTER instead,
        # and the run died formatting a list as an integer.
        forbidden = ["git('" + 'merge' + "'",
                     "'--" + 'force' + "'",
                     "'origin', '" + 'main' + "'"]
        found = [b for b in forbidden if b in code]
        ck('THE TOOL NEVER MERGES, never force-pushes, and never pushes main',
           not found, ', '.join(found))
        ck('NEGATIVE CONTROL: the definition pattern does not match a bare '
           'CALL site, or every reference would look like a definition',
           definition_lines(['  onlyOnce();'], 'onlyOnce')[0] == [])
    finally:
        shutil.rmtree(d, ignore_errors=True)
    return out, bad


if __name__ == '__main__':
    import datetime
    TODAY = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')
    sys.exit(main(sys.argv[1:]))
