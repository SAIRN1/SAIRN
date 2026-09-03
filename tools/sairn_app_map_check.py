#!/usr/bin/env python
"""sairn_app_map_check.py -- derive the truth about which apps exist, and diff
Guardian's App File Map against it.

WHY THIS EXISTS. Guardian v2's App File Map is a hand-maintained table, and it
has now been wrong FIVE times about its own contents -- including twice about the
SAME app in OPPOSITE directions:

  2026-07-26  missing SAIRNhr / SAIRNacc rows (later found to be speculative)
  2026-08-09  carried a planned SAIRNfuneral row for an app shipped as SAIRNlegacy
  2026-08-13  removed the two speculative rows
  2026-08-19  missing SAIRNcash and SAIRNgrounds -- real, live, deployed apps
  2026-08-27  asserted SAIRNmechanical as live when the file was on no branch
  2026-08-30  asserted SAIRNmechanical as MISSING two days after it was recovered

The file's own comment names the cause: "the map is a claim about the repo, not
derived from it, so it drifts exactly like any other unverified claim." Five
corrections is enough evidence. This derives the verifiable half.

WHAT IT DOES NOT DO, deliberately. It does not rewrite the map. Two columns --
brand colour and app_id -- are real decisions that cannot be derived from the
filesystem, and a tool that regenerated the whole table would destroy them. It
diffs the derivable columns and reports drift. **A human still edits the map.**

THE THREE SOURCES OF TRUTH, in order of authority:
  1. `git ls-files '*.html'`   -- does the file exist on this branch at all
  2. `vercel.json`             -- is it routed
  3. a live HTTP request       -- does the route actually serve

Source 3 is the one that caught SAIRNmechanical, because 1 and 2 can both be
satisfied by a file nobody deployed, and 3 can pass while 1 fails if the CDN is
serving an older build. Disagreement between them IS the finding.

Usage:
  python tools/sairn_app_map_check.py              # offline: files + routes only
  python tools/sairn_app_map_check.py --live       # + curl every route
  python tools/sairn_app_map_check.py --live --json

Exit codes: 0 clean / 1 drift found / 2 error
"""
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import sairn_http  # noqa: E402


REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(REPO, '.claude', 'skills', 'sairn-guardian-v2', 'SKILL.md')
BASE = 'https://sairn.vercel.app'
TIMEOUT = 15

# Files that are real pages but are NOT standalone apps with their own map row.
# Kept as an explicit list rather than a pattern: a new companion page should be
# a deliberate addition here, not something a regex silently swallows.
COMPANION_PAGES = {
    'stonedesk-hr.html',            # HR onboarding, a second page of StoneDesk
    'sairndental-book.html',        # public booking page for SAIRNdental
    'sairndental-complaint.html',   # public complaint page for SAIRNdental
}


def sh(args):
    r = subprocess.run(args, cwd=REPO, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write((r.stderr or r.stdout).strip() + '\n')
        sys.exit(2)
    return r.stdout


def tracked_html():
    """Source 1: what is actually on this branch, root level only.

    SPLIT ON NEWLINES, NOT WHITESPACE. The first version used .split(), and this
    repo contains files like `docs/HOW TO UPLOAD TO GITHUB (1).html` -- whose
    name has spaces. Whitespace-splitting shredded one path into the tokens
    `HOW`, `TO`, `UPLOAD`, `TO`, `GITHUB`, `(1).html`, each of which was then
    reported as an unmapped, unrouted app. 60 "app files" and 91 findings, from
    a repo with 19. A checker that over-reports gets switched off, so this is a
    correctness bug and not a cosmetic one -- the same class as the regex
    over-matches found twice on 2026-08-30.
    """
    out = sh(['git', 'ls-files', '*.html']).splitlines()
    return sorted(f.strip() for f in out if f.strip() and '/' not in f.strip())


def routes():
    """Source 2: html destinations in vercel.json -> the source path."""
    p = os.path.join(REPO, 'vercel.json')
    if not os.path.exists(p):
        return {}
    cfg = json.load(open(p, encoding='utf-8'))
    out = {}
    for r in cfg.get('rewrites', []) + cfg.get('routes', []):
        dest = r.get('destination') or r.get('dest') or ''
        src = r.get('source') or r.get('src') or ''
        if dest.endswith('.html'):
            out.setdefault(os.path.basename(dest), src)
    return out


def map_rows():
    """Guardian's hand-maintained table. Struck-through rows (~~Name~~) are
    parsed too -- a row someone crossed out is still a claim about the repo."""
    if not os.path.exists(SKILL):
        return {}
    rows = {}
    for line in open(SKILL, encoding='utf-8'):
        m = re.match(r'^\|\s*~*\s*([A-Za-z][\w]*)\s*~*\s*\|\s*([^|]+?)\s*\|'
                     r'\s*(#[0-9A-Fa-f]{3,8}|[^|]*?)\s*\|\s*([^|]*?)\s*\|', line)
        if not m:
            continue
        name, filecell, colour, app_id = m.groups()
        if name.lower() in ('app', 'name') or set(filecell) <= set('-: '):
            continue
        fm = re.search(r'([\w-]+\.html)', filecell)
        rows[name] = {
            'file': fm.group(1) if fm else None,
            'file_cell': filecell.strip(),
            'colour': colour.strip(),
            'app_id': app_id.strip(),
        }
    return rows


def live(path):
    """Source 3: does the route actually serve? Returns an int status, or a
    string describing why we could not tell -- NEVER a silent False, because
    'could not check' and 'returned 404' are different findings."""
    # 'sairn-app-map-check' was an honest User-Agent and Vercel's bot mitigation
    # reads it as exactly what it says -- an automated client. On 2026-09-02 that
    # meant --live returned 403 for every route and the map read as an outage.
    # Browser-shaped now, via the one module that knows why.
    req = urllib.request.Request(BASE + path, method='GET',
                                 headers=sairn_http.with_browser_ua(
                                     {'X-SAIRN-Check': 'app-map'}))
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception as e:                                  # noqa: BLE001
        return 'UNREACHABLE (%s)' % type(e).__name__


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--live', action='store_true',
                    help='also request every route (the check that caught '
                         'SAIRNmechanical)')
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()

    files = tracked_html()
    rts = routes()
    rows = map_rows()
    apps = [f for f in files if f not in COMPANION_PAGES]

    findings = []
    table = []

    # --- every tracked app file, checked forward
    for f in apps:
        slug = f[:-5]
        route = rts.get(f)
        mapped = next((n for n, r in rows.items() if r['file'] == f), None)
        rec = {'file': f, 'route': route, 'mapped_as': mapped, 'live': None}
        if args.live and route:
            rec['live'] = live('/' + route.strip('^$').lstrip('/'))
        table.append(rec)

        if not route:
            findings.append('NO ROUTE: %s is tracked but vercel.json does not '
                            'route it -- it cannot be reached.' % f)
        if not mapped:
            findings.append("NOT IN MAP: %s exists on this branch and is not in "
                            "Guardian's App File Map. Every Guardian pass that "
                            "said 'all apps' excluded it." % f)
        if args.live and route and rec['live'] != 200:
            findings.append('LIVE FAIL: %s -> %s returned %s'
                            % (f, route, rec['live']))

    # --- every map row, checked backward. This is the SAIRNmechanical direction.
    for name, r in rows.items():
        if not r['file']:
            findings.append('MAP ROW HAS NO FILE: %s -- cell reads %r'
                            % (name, r['file_cell']))
            continue
        if r['file'] not in files:
            findings.append('MAP CLAIMS A FILE THAT IS NOT ON THIS BRANCH: '
                            '%s -> %s. This is the 2026-08-27 failure exactly.'
                            % (name, r['file']))

    # --- colour collisions, since the map has flagged these before
    seen = {}
    for name, r in rows.items():
        c = (r['colour'] or '').upper()
        if re.match(r'^#[0-9A-F]{6}$', c):
            if c in seen:
                findings.append('COLOUR COLLISION: %s and %s both %s'
                                % (seen[c], name, c))
            seen[c] = name

    if args.json:
        print(json.dumps({'apps': table, 'findings': findings,
                          'companion_pages': sorted(COMPANION_PAGES)}, indent=2))
    else:
        print('  %-30s %-22s %-16s %s' % ('FILE', 'ROUTE', 'MAPPED AS', 'LIVE'))
        for rec in table:
            print('  %-30s %-22s %-16s %s'
                  % (rec['file'], rec['route'] or '-- NONE --',
                     rec['mapped_as'] or '-- NOT MAPPED --',
                     rec['live'] if rec['live'] is not None else '(not checked)'))
        print('\n  %d app files, %d map rows, %d companion pages excluded'
              % (len(apps), len(rows), len(COMPANION_PAGES)))
        if not args.live:
            print('  NOTE: run with --live to request every route. Files and '
                  'routes can both be right while nothing is deployed.')
        print()
        if findings:
            print('DRIFT (%d):' % len(findings))
            for f in findings:
                print('  - ' + f)
        else:
            print('CLEAN -- map, branch and routes agree.')

    return 1 if findings else 0


if __name__ == '__main__':
    sys.exit(main())
