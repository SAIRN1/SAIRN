#!/usr/bin/env python
"""register_citation_check.py -- every explicit path:line citation in
docs/CRITICALITY-TIERS.md, verified to anchor at HEAD (2026-09-30,
directed item 7). A register cell whose citation no longer anchors is the
exact drift shape the sf_national_categories :4909 correction just paid
for -- this makes the whole register's citation health one mechanical
report instead of a per-row discovery.

Reuses citation_class_check's classify() verbatim (25 fixture-locked
checks of its own): a citation is REPORTED here when it is neither HOLDS
nor NOT-A-REPO-PATH at HEAD. This tool passes no source_shas and no ts,
so a failing citation surfaces as UNVERIFIABLE-NO-SHA -- read that as
"does not anchor at HEAD" in this tool's output; at-derivation innocence
is not this tool's question. Rows are attributed by the first `name`
cell of the markdown table row the citation sits in.

Exit: 0 clean, 1 failing citations found, 2 could not run.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import citation_class_check as cc  # noqa: E402

REGISTER = 'docs/CRITICALITY-TIERS.md'
ROW_NAME = re.compile(r'^\|\s*`([\w.]+)`\s*\|')
# A bare backticked line number, no filename -- the register's own shorthand
# for "the resource's own app file" (sf_national_categories :4909 is this
# shape exactly). Never bare without backticks: an un-backticked ':4909' in
# prose is not distinguishable from a footnote or a time-of-day fragment.
BARE_LINE = re.compile(r'`:(\d{2,6})`')


def _app_map(repo):
    """{resource: app} derived from api/_resources/*.js, reusing the exact
    derivation hover_cold_scan_pool.py already built and fixture-locks --
    imported, never re-implemented (the app-map lesson applies to this
    tool too: a second hand-copy is a second place for it to go stale)."""
    sys.path.insert(0, HERE)
    import hover_cold_scan_pool as hcsp  # noqa: E402
    return hcsp.resource_app_map(repo)


def scan(repo=cc.REPO, register=REGISTER):
    """[(resource, register_line, path, line, cls, head_best)] for every
    citation that does not anchor at HEAD. Bare `:NNNN` citations resolve
    to <app>.html via the resource's own app-map entry; a resource with no
    app-map entry (a prose row, an unrecognized name) is reported as its
    own UNRESOLVABLE class rather than silently skipped."""
    reg_path = os.path.join(repo, register)
    if not os.path.isfile(reg_path):
        return None
    try:
        app_map = _app_map(repo)
    except Exception:
        app_map = {}
    out = []
    lines = open(reg_path, encoding='utf-8', errors='replace').readlines()
    for i, row in enumerate(lines, 1):
        m = ROW_NAME.match(row)
        resource = m.group(1) if m else None
        row_label = resource if resource else '(prose, line %d)' % i
        if cc.FILELINE.search(row):
            for path, ln, cls, sent, hb in cc.classify(
                    {'summary': row.rstrip('\n')}, repo=repo, detail=True):
                if cls in ('HOLDS', 'NOT-A-REPO-PATH'):
                    continue
                out.append((row_label, i, path, ln, cls, hb))
        for bm in BARE_LINE.finditer(row):
            ln = int(bm.group(1))
            app = app_map.get(resource) if resource else None
            if not app:
                out.append((row_label, i, '(bare, no app resolved)', ln,
                            'UNRESOLVABLE', None))
                continue
            path = '%s.html' % app
            # Splice the resolved path INTO the row's own text in place of
            # the bare `:NNNN`, rather than a bare synthetic sentence --
            # every other real anchor candidate in the row (field names,
            # function names) has to stay present for classify() to test
            # against, or a bare citation with no OTHER candidates would
            # trivially bounds-only HOLD regardless of what is really there.
            spliced = row[:bm.start()] + ('`%s:%d`' % (path, ln)) \
                + row[bm.end():]
            for p2, ln2, cls, sent, hb in cc.classify(
                    {'summary': spliced.rstrip('\n')}, repo=repo,
                    detail=True):
                if p2 != path or ln2 != ln:
                    continue
                if cls in ('HOLDS', 'NOT-A-REPO-PATH'):
                    continue
                out.append((row_label, i, path, ln2, cls, hb))
    return out


def _fixtures():
    import tempfile
    import shutil
    import subprocess
    ok, bad = [0], [0]

    def ck(name, cond):
        (ok if cond else bad)[0] += 1
        print('  %s %s' % ('ok  ' if cond else 'FAIL', name))

    d = tempfile.mkdtemp(prefix='register_cite_fx_')
    try:
        def g(*a):
            subprocess.run(['git'] + list(a), cwd=d, capture_output=True,
                           check=True,
                           env=dict(os.environ, GIT_AUTHOR_NAME='fx',
                                    GIT_AUTHOR_EMAIL='f@x',
                                    GIT_COMMITTER_NAME='fx',
                                    GIT_COMMITTER_EMAIL='f@x'))
        g('init', '-q')
        app = ['# pad'] * 9 + ['def frobnicate():', '    return 1']
        open(os.path.join(d, 'app.py'), 'w').write('\n'.join(app) + '\n')
        os.makedirs(os.path.join(d, 'docs'))
        reg = [
            '| Resource | Tier |',
            '|---|---|',
            '| `good_row` | frobnicate() writes at `app.py:10` |',
            '| `bad_row` | frobnicate() writes at `app.py:99` |',
        ]
        open(os.path.join(d, 'docs', 'REG-FX.md'), 'w').write(
            '\n'.join(reg) + '\n')
        g('add', '-A'); g('commit', '-q', '-m', 'fx')
        got = scan(repo=d, register='docs/REG-FX.md')
        ck('a citation anchoring at HEAD is NOT reported',
           all(r[0] != 'good_row' for r in got))
        ck('a citation failing at HEAD IS reported, attributed to its row',
           any(r[0] == 'bad_row' and r[2] == 'app.py' and r[3] == 99
               for r in got))
        ck('a missing register returns None (could-not-run), never an '
           'empty clean list', scan(repo=d, register='docs/NOPE.md') is None)

        # ── BARE :NNNN citations (queue-3 item 6) ───────────────────────
        os.makedirs(os.path.join(d, 'api', '_resources'))
        open(os.path.join(d, 'api', '_resources', 'fxapp.js'), 'w').write(
            "module.exports = {\n  app: 'fxapp',\n  resources: ["
            "'good_bare', 'bad_bare', 'no_content_bare'],\n};\n")
        app_body = ['# pad'] * 9 + [
            "  var frobKey='fxapp_frob';",     # :10
        ] + ['# pad'] * 9
        open(os.path.join(d, 'fxapp.html'), 'w').write(
            '\n'.join(app_body) + '\n')
        reg2 = [
            '| Resource | Evidence |',
            '|---|---|',
            "| `good_bare` | writes `frobKey` at `:10` |",
            "| `bad_bare` | writes `frobKey` at `:99` |",
            "| `unmapped_bare` | writes something at `:10` |",
        ]
        open(os.path.join(d, 'docs', 'REG-BARE.md'), 'w').write(
            '\n'.join(reg2) + '\n')
        g('add', '-A'); g('commit', '-q', '-m', 'bare fx')
        got2 = scan(repo=d, register='docs/REG-BARE.md')
        ck('a bare :NNNN citation resolves via the resource-to-app map and '
           'anchors correctly -- NOT reported',
           all(r[0] != 'good_bare' for r in got2))
        ck('a bare :NNNN citation that fails at the resolved app file IS '
           'reported, with the resolved path filled in',
           any(r[0] == 'bad_bare' and r[2] == 'fxapp.html' and r[3] == 99
               for r in got2))
        ck('a resource absent from the app map reports UNRESOLVABLE, never '
           'silently skipped',
           any(r[0] == 'unmapped_bare' and r[4] == 'UNRESOLVABLE'
               for r in got2))
    finally:
        shutil.rmtree(d, ignore_errors=True)
    print('%d ok, %d failed' % (ok[0], bad[0]))
    return bad[0] == 0


def main(argv):
    if '--selftest' in argv:
        return 0 if _fixtures() else 1
    if not _fixtures():
        print('REFUSED: fixtures failed -- nothing real was scanned.')
        return 2
    rows = scan()
    if rows is None:
        print('COULD NOT RUN: %s not found under %s' % (REGISTER, cc.REPO))
        return 2
    if not rows:
        print('CLEAN: every explicit path:line citation in %s anchors at '
              'HEAD.' % REGISTER)
        return 0
    print('%d register citation(s) do not anchor at HEAD:' % len(rows))
    for resource, regline, path, ln, cls, hb in rows:
        print('  %-28s reg:%-4d cites %s:%-6d %-20s head-best=%s'
              % (resource, regline, path, ln, cls, hb))
    return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
