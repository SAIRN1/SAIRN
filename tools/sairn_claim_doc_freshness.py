#!/usr/bin/env python
"""sairn_claim_doc_freshness.py -- item 23's freshness discipline pointed at
tools/sairn_claim.py's OWN documentation.

    python tools/sairn_claim_doc_freshness.py
    python tools/sairn_claim_doc_freshness.py --tool-src X --claude-md Y \\
        --claims-dir Z --status-dir W        (fixture overrides, for the probe)

REPORT-ONLY, NEVER GATES. Exit 0 every row verifies, 1 any row DRIFTED or its
anchor is gone, 2 nothing drifted but at least one row COULD NOT BE CHECKED --
a third state, never folded into pass (CLAUDE.md PR 1.11).

WHY THIS EXISTS. sairn_claim.py is the platform's most documentation-dense
tool: its docstring and comments carry dated factual rows -- what CLAUDE.md
says, how long a claim lives, where the status registry sits, which convention
the file-set matcher decides on -- and the tool PRINTS guidance derived from
them on every check. Every one of those rows is a claim with a tense, and
until now nothing re-referenced any of them against its SOURCE before the tool
trusted it. That is the exact shape of cross-domain discipline 8 ("nothing
announces the day a check stops testing anything") and of item 23's design
(docs/2026-09-13-claim-provenance-chain-design.md): freshness is a property of
the SUBJECT, measured against the source, with "could not check" kept apart
from "checked and fine".

WHAT A ROW IS. Each row names ONE checkable documentation claim inside
sairn_claim.py: the ANCHOR (the sentence as written there, asserted to appear
EXACTLY ONCE -- zero means the doc moved and this table went stale, two means
the anchor stopped identifying anything), the claim TYPE, WHEN the row was
written, and a CHECK that re-derives the claim from its source NOW. Every
check here is cheap enough to re-derive per run, which is the best case item
23 names: no staleness window is needed because the observation IS the run.
A row whose source cannot be read answers COULD-NOT-CHECK, never OK.

WHAT THIS DOES NOT DO. It does not judge the truth of sairn_claim.py's
incident history (those are records, not measurements -- a standing lesson has
no expiry), and it does not verify the tool's BEHAVIOUR (the claim tool's own
probes do that). It verifies that the documentation the tool trusts and
reprints still matches what the sources say today.
"""
import argparse
import io
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

OK, DRIFTED, CNC, ANCHOR_GONE = 'OK', 'DRIFTED', 'COULD-NOT-CHECK', 'ANCHOR-GONE'


def read(path):
    return io.open(path, encoding='utf-8').read()


# ── THE ROWS ────────────────────────────────────────────────────────────────
# anchor: must appear EXACTLY ONCE in the tool source. written: when the row
# was added here, so a future reader can tell the table's own age. type: what
# kind of claim it is, per item 23 -- the interval belongs to the type, and
# every type here is `re-derived-per-run`, the degenerate (best) interval.

def check_expiry_hours(ctx):
    """CLAUDE.md's stated claim lifetime must equal the tool's default."""
    # \s+ on both sides: the sentence wraps across a line break in CLAUDE.md
    # today, and a regex that demands single spaces reports the claim missing
    # the day a formatter rewraps it -- the stale-anchor shape, in a checker
    # built against stale anchors.
    m_doc = re.search(r'Expire after\s+(\d+(?:\.\d+)?)\s+hours', ctx['claude_md'])
    if not m_doc:
        return CNC, 'CLAUDE.md no longer states a claim expiry in the expected words'
    m_src = re.search(r"SAIRN_CLAIM_STALE_HOURS',\s*'(\d+(?:\.\d+)?)'", ctx['tool_src'])
    if not m_src:
        return CNC, 'the STALE_HOURS default is no longer readable from the tool source'
    doc_h, src_h = float(m_doc.group(1)), float(m_src.group(1))
    if doc_h != src_h:
        return DRIFTED, ('CLAUDE.md says %g hours, the tool defaults to %g -- one of '
                         'the two moved' % (doc_h, src_h))
    return OK, 'both say %g hours' % doc_h


def check_active_work_instruction(ctx):
    """The docstring quotes CLAUDE.md's read-all-N instruction; CLAUDE.md must
    still carry it, and the N must still match the number of BUILD clones in
    CLAUDE.md's own table -- the word "four" goes stale in both documents the
    day a fifth build agent is added, and nothing else watches for that."""
    m = re.search(r'Read all (\w+) `?SAIRN-ACTIVE-WORK', ctx['claude_md'])
    if not m:
        return DRIFTED, ('CLAUDE.md no longer carries the read-all instruction the '
                         'tool docstring quotes')
    word = m.group(1).lower()
    words = {'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7}
    n_claimed = words.get(word)
    if n_claimed is None:
        return CNC, 'CLAUDE.md counts the files as %r, which this cannot read' % word
    build_rows = re.findall(r'\|[^|\n]*\|[^|\n]*SAIRN-[a-z0-9]+[^|\n]*\|[^|\n]*'
                            r'SAIRN-ACTIVE-WORK-[a-z0-9]+\.md[^|\n]*\|[^|\n]*\|'
                            r'\s*build\s*\|', ctx['claude_md'])
    if not build_rows:
        return CNC, 'the clone table is no longer parseable for build rows'
    if len(build_rows) != n_claimed:
        return DRIFTED, ('CLAUDE.md says read all %d, its own clone table lists %d '
                         'build rows' % (n_claimed, len(build_rows)))
    return OK, '%d files claimed, %d build clones in the table' % (n_claimed, len(build_rows))


def check_registry_outside_git(ctx):
    """The tool's comment rests on the registry being OUTSIDE every clone --
    "already outside git ... already read with no fetch". If STATUS_DIR ever
    resolves inside the repo, that premise is dead and the fast advisory path
    is as stale as the slow one."""
    d = ctx.get('status_dir')
    if not d:
        return CNC, 'the status directory could not be resolved'
    d_abs = os.path.normcase(os.path.abspath(d))
    repo_abs = os.path.normcase(os.path.abspath(ctx['repo']))
    if d_abs == repo_abs or d_abs.startswith(repo_abs + os.sep):
        return DRIFTED, ('STATUS_DIR resolves INSIDE the repo (%s) -- the '
                         '"outside git, no fetch needed" premise is false' % d)
    return OK, 'registry at %s, outside %s' % (d, ctx['repo'])


def check_files_convention(ctx):
    """"claims now carry FILES: <paths> in the task string" (2026-09-21) is a
    LIVE convention the matcher decides on, not a rule the tool can enforce --
    so it is observed, not assumed. Active claims that have all stopped
    carrying it mean the strongest overlap signal is silently starved."""
    cdir = ctx.get('claims_dir')
    if not cdir or not os.path.isdir(cdir):
        return CNC, 'no claims directory to observe'
    import json
    active = []
    for fn in sorted(os.listdir(cdir)):
        if not fn.endswith('.json'):
            continue
        try:
            doc = json.load(io.open(os.path.join(cdir, fn), encoding='utf-8'))
        except Exception:                                        # noqa: BLE001
            return CNC, '%s is unreadable, so the observation would be partial' % fn
        for c in doc.get('claims', []):
            if c.get('status') == 'active':
                active.append(c.get('task') or '')
    if not active:
        return CNC, 'no active claims right now -- nothing to observe, which is not a pass'
    carrying = sum(1 for t in active if 'FILES:' in t)
    if carrying == 0:
        return DRIFTED, ('%d active claim(s), NONE carry FILES: -- the convention '
                         'the file-set matcher decides on is not being fed' % len(active))
    return OK, '%d of %d active claim(s) carry FILES:' % (carrying, len(active))


ROWS = [
    {'id': 'expiry-hours', 'type': 'cross-document', 'written': '2026-09-24',
     'anchor': "Expire after",
     'anchor_in': 'claude',   # this row's anchor lives in CLAUDE.md
     'check': check_expiry_hours},
    {'id': 'active-work-instruction', 'type': 'cross-document', 'written': '2026-09-24',
     'anchor': 'read all four SAIRN-ACTIVE-WORK files',
     'anchor_in': 'tool',
     'check': check_active_work_instruction},
    {'id': 'registry-outside-git', 'type': 'premise-live', 'written': '2026-09-24',
     'anchor': 'tools/sairn_status.py is already outside git, already written locally',
     'anchor_in': 'tool',
     'check': check_registry_outside_git},
    {'id': 'files-convention', 'type': 'convention-observed', 'written': '2026-09-24',
     'anchor': 'claims now carry `FILES: <paths>`',
     'anchor_in': 'tool',
     'check': check_files_convention},
]


def resolve_status_dir():
    try:
        sys.path.insert(0, os.path.join(REPO, 'tools'))
        import sairn_status
        return sairn_status.STATUS_DIR
    except Exception:                                            # noqa: BLE001
        return None


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--tool-src', default=os.path.join(REPO, 'tools', 'sairn_claim.py'))
    ap.add_argument('--claude-md', default=os.path.join(REPO, 'CLAUDE.md'))
    ap.add_argument('--claims-dir', default=os.path.join(REPO, '.claude', 'claims'))
    ap.add_argument('--status-dir', default=None)
    ap.add_argument('--repo', default=REPO)
    args = ap.parse_args(argv)

    ctx = {'repo': args.repo, 'claims_dir': args.claims_dir,
           'status_dir': args.status_dir if args.status_dir else resolve_status_dir()}
    try:
        ctx['tool_src'] = read(args.tool_src)
    except OSError as e:
        print('COULD NOT RUN: the tool source is unreadable (%s). Nothing was '
              'checked.' % e)
        return 2
    try:
        ctx['claude_md'] = read(args.claude_md)
    except OSError as e:
        print('COULD NOT RUN: CLAUDE.md is unreadable (%s). Nothing was checked.' % e)
        return 2

    print('sairn_claim.py DOCUMENTATION FRESHNESS -- report only, never gates')
    print('re-referenced against the SOURCE on every run; "could not check" is '
          'a third state\n')
    drift = cnc = 0
    for row in ROWS:
        hay = ctx['tool_src'] if row['anchor_in'] == 'tool' else ctx['claude_md']
        n = hay.count(row['anchor'])
        if n != 1:
            # Zero: the documented sentence is gone or reworded -- the doc this
            # table describes has moved and the table is what went stale.
            # More than one: the anchor stopped identifying a single claim.
            print('  %-14s %-24s the anchor appears %d time(s), not 1 -- this '
                  'table no longer matches the document it describes'
                  % (ANCHOR_GONE, row['id'], n))
            drift += 1
            continue
        state, detail = row['check'](ctx)
        print('  %-14s %-24s %s' % (state, row['id'], detail))
        if state == DRIFTED:
            drift += 1
        elif state == CNC:
            cnc += 1
    print('\n%d row(s): %d drifted, %d could not be checked'
          % (len(ROWS), drift, cnc))
    if drift:
        return 1
    if cnc:
        print('NOT A CLEAN BILL: at least one row could not be checked against '
              'its source.')
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
