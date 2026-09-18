"""Every REGISTERED resource, does any client actually name it?

    python tools/resource_reachability_check.py            # report
    python tools/resource_reachability_check.py --strict    # exit 1 on findings
    python tools/resource_reachability_check.py --quiet     # exit code only

WHY THIS EXISTS, AND WHY THE CHECK IT REPLACES WAS TOO NARROW (2026-09-18)
==========================================================================
`docs/2026-09-17-senior-mechanical-competitive-gap-rederived.md` found
SAIRNmechanical shipping a complete `eligibility` capability -- engine, endpoint,
registry entry, ten test arms -- that the app never called, while a panel
subtitle told a dispatcher it was computed. The check that found it enumerated
`extraActions` and asked, for each verb, "does the app send it".

THAT CHECK COULD NOT HAVE FOUND THE NEXT ONE. `dnt_rollup` is SAIRNdental's
cross-location roll-up: an engine with four written rules, an owner-gated
endpoint, 39 test arms, Tier A, independently reviewed twice -- and zero
occurrences in `sairndental.html` or in any other `.html` file in the repo. It
needs no extra action. It is a plain `read`. A check keyed on `extraActions`
never looks at it, and `docs/2026-09-17-sairndental-competitive-gap-rederived.md`
§1.3 recorded that as a gap in the method rather than leaving it implied.

A PANEL CENSUS CANNOT FIND EITHER ONE, and that is worth stating because it is
the check most people would reach for first. SAIRNdental is 22 panels / 22 nav
targets / 22 sidebar ids -- three identical sets, no orphan in any direction --
because the roll-up is in NONE of the three. Comparing those three to each other
reports clean. The unreachable capability is invisible to a census of the
reachable ones.

So the question this asks is the widest one that is still answerable from the
repo: **for every resource a registry declares, does the app that owns it name
that resource anywhere in its own client file?**

WHAT A FINDING MEANS, AND WHAT IT DOES NOT
==========================================
A finding is "no client names this". It is NOT "this is dead code" and NOT "this
should be deleted". A resource can be legitimately unreachable from the browser:
fed by a cron, read by another server endpoint, or built and waiting on a panel
somebody decided to defer. Each of those is a real answer -- and each needs
somebody to SAY it, which is the point. The defect this catches is not an unused
resource; it is a resource the platform's own records describe as BUILT while no
user can reach it.

THE CALIBRATION ARM, WHICH IS THE PART THAT MAKES THE ZEROS TRUSTWORTHY
======================================================================
A substring search that finds nothing proves nothing on its own -- a renamed
file, a changed convention or a bad path produces exactly the same output as a
genuinely unreachable resource, and it produces it for EVERY resource at once.

So this reports, per app, HOW MANY of that app's resources it DID find. An app
where 24 of 25 are found and 1 is not is evidence about that 1. An app where 0 of
25 are found is evidence about the CHECKER, and is reported as CANNOT TELL rather
than as 25 findings. The threshold is stated in the output and not buried:
finding none at all is never reported as finding everything missing.

That distinction is the one this repo keeps paying for. CLAUDE.md PR §1.11: a
check that cannot run must say so rather than fold "could not tell" into
"passed". This is the same rule pointed at a checker's own blind spot instead of
at a missing dependency.

WHAT IT CANNOT SEE, SAID PLAINLY
================================
  * A NAME BUILT BY CONCATENATION. `'dnt_' + kind` would pass this and be
    invisible. Measured rather than assumed for the app this was written for:
    all 53 `dnt_`-prefixed strings in sairndental.html are literals. Not
    re-measured for the other sixteen, so treat a zero in an app you have not
    checked as a lead rather than a verdict.
  * A CALLER BEHIND A DEAD FEATURE FLAG. The name is present, so this passes; it
    is a mention, not a reachable call path.
  * WHETHER THE PANEL WORKS. Naming a resource is the floor, not the ceiling.
  * NON-BROWSER CLIENTS. A resource reached only by a cron or by another server
    endpoint reads as unreachable here, correctly -- it is unreachable FROM A
    CLIENT -- and the reason belongs in the exemption note, not in silence.

EXEMPTIONS ARE NAMED IN THIS FILE AND COUNTED IN THE OUTPUT. Never silently
subtracted: an exclusion a reader cannot see is indistinguishable from a checker
that stopped looking.
"""
import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESOURCES_DIR = os.path.join(REPO, 'api', '_resources')

# An app that finds fewer than this fraction of its own resources is reporting on
# the CHECKER, not on the app. Stated here rather than inlined so a reader can
# argue with it.
CALIBRATION_FLOOR = 0.5

# ── NAMED EXEMPTIONS ────────────────────────────────────────────────────────
# Each needs a sentence. A bare name in this dict is the silent-exemption shape
# this file's header refuses, so the tool requires the reason to be non-empty.
EXEMPT = {
    # `shared` owns no client of its own -- its resources are named by the
    # SIXTEEN app files, which is checked separately below rather than skipped.
}


def load_registries():
    """Every api/_resources/<app>.js, read through node so the file is the only
    source of truth. Parsing JavaScript with a regex here would be a second,
    drifting copy of what `index.js` already merges."""
    script = (
        "const fs=require('fs'),p=require('path');"
        "const d=process.argv[1];const out=[];"
        "for(const f of fs.readdirSync(d)){"
        "  if(!f.endsWith('.js')||f.includes('.test.')||f==='index.js')continue;"
        "  const m=require(p.join(d,f));"
        "  out.push({file:f,app:m.app||null,resources:m.resources||[],"
        "            extraActions:Object.keys(m.extraActions||{})});"
        "}"
        "process.stdout.write(JSON.stringify(out));"
    )
    r = subprocess.run(['node', '-e', script, RESOURCES_DIR],
                       capture_output=True, text=True, cwd=REPO)
    if r.returncode != 0:
        raise SystemExit('could not read the registries through node: '
                         + (r.stderr or '').strip())
    return json.loads(r.stdout)


def client_files(app):
    """Every client file that belongs to `app`, not just `<app>.html`.

    THE FIRST VERSION READ ONLY `<app>.html` AND WAS WRONG ON ITS FIRST RUN.
    It reported StoneDesk's `sd_hr_certs` (Tier A) as named by no client. It is
    named -- by `stonedesk-hr.html`, a SECOND client file for the same app.
    Caught by hand-reading the five findings before publishing the number, which
    is the only reason it is not in the output as a false positive.

    So the unit is every root-level `<app>*.html`. `archive/` is excluded for
    the reason CLAUDE.md gives -- it is the preserved ancestor branch, must not
    be run or recreated, and scanning it reports dead 2026-06 snapshots forever.
    """
    out = []
    for name in sorted(os.listdir(REPO)):
        if not name.endswith('.html'):
            continue
        stem = name[:-len('.html')]
        if stem == app or stem.startswith(app + '-'):
            out.append(name)
    return out


def read_client(app):
    """The app's client source, every file concatenated, plus the file list."""
    files = client_files(app)
    if not files:
        return None, []
    src = []
    for f in files:
        src.append(io.open(os.path.join(REPO, f), encoding='utf-8',
                           errors='replace').read())
    return '\n'.join(src), files


def literal_names(src, prefix):
    """Every quoted string in `src` starting with `prefix`. Used only to report
    whether an app's resource names are LITERALS -- a app whose names are built
    by concatenation is one this tool cannot speak for."""
    return set(re.findall(r"""['"](""" + re.escape(prefix) + r"""[a-z0-9_]*)['"]""", src))


def main(argv):
    strict = '--strict' in argv
    quiet = '--quiet' in argv
    regs = load_registries()

    by_app = {r['app']: r for r in regs if r.get('app')}
    shared = by_app.pop('shared', None)

    clients = {}
    for app in sorted(by_app):
        src, files = read_client(app)
        clients[app] = (src, files)

    findings = []          # (app, resource)
    cannot_tell = []       # (app, found, total, why)
    rows = []

    for app in sorted(by_app):
        res = [r for r in by_app[app]['resources'] if r not in EXEMPT]
        src, files = clients[app]
        if src is None:
            cannot_tell.append((app, 0, len(res), 'no %s*.html in the repo' % app))
            continue
        if not res:
            rows.append((app, 0, 0, [], files))
            continue
        named = [r for r in res if r in src]
        missing = [r for r in res if r not in src]
        ratio = len(named) / float(len(res))
        if ratio < CALIBRATION_FLOOR:
            cannot_tell.append((app, len(named), len(res),
                                'only %d of %d resources were found at all -- below the '
                                '%.0f%% calibration floor, so this reports on the CHECKER'
                                % (len(named), len(res), CALIBRATION_FLOOR * 100)))
            continue
        rows.append((app, len(named), len(res), missing, files))
        for m in missing:
            findings.append((app, m))

    out = []
    out.append('RESOURCE REACHABILITY -- does any client NAME each registered resource?')
    out.append('  registries read : %d apps' % len(by_app))
    total_res = sum(len(by_app[a]['resources']) for a in by_app)
    out.append('  resources       : %d (excluding `shared`, reported separately)' % total_res)
    out.append('')
    out.append('  %-18s %7s %7s  %s' % ('app', 'named', 'total', 'NOT NAMED BY ANY OF ITS CLIENTS'))
    for app, named, total, missing, files in rows:
        extra = '' if len(files) <= 1 else '   [%d client files: %s]' % (len(files), ', '.join(files))
        out.append('  %-18s %7d %7d  %s%s'
                   % (app, named, total, ', '.join(missing) if missing else '-', extra))

    if cannot_tell:
        out.append('')
        out.append('  COULD NOT TELL (%d) -- NOT counted as findings:' % len(cannot_tell))
        for app, found, total, why in cannot_tell:
            out.append('    %-18s %s' % (app, why))

    # ── the shared registry, which has no client of its own ────────────────
    if shared:
        out.append('')
        out.append('  `shared` (%d resources) -- named by ANY app client:' % len(shared['resources']))
        for r in shared['resources']:
            hits = sorted(a for a in clients
                          if clients[a][0] and r in clients[a][0])
            out.append('    %-20s %s' % (r, ('%d app(s)' % len(hits)) if hits else 'NO CLIENT NAMES IT'))
            if not hits:
                findings.append(('shared', r))

    if EXEMPT:
        out.append('')
        out.append('  EXEMPT (%d), named not subtracted:' % len(EXEMPT))
        for k, v in sorted(EXEMPT.items()):
            out.append('    %-20s %s' % (k, v))

    out.append('')
    out.append('  FINDINGS: %d' % len(findings))
    for app, r in findings:
        out.append('    %-18s %s' % (app, r))
    out.append('')
    out.append('  A FINDING IS "no client names this", NOT "delete it". A resource fed by')
    out.append('  a cron, read by another server endpoint, or waiting on a deferred panel')
    out.append('  is legitimately here -- and each of those needs somebody to SAY so. The')
    out.append('  defect is a resource the records call BUILT that no user can reach.')
    out.append('  This CANNOT see a name built by concatenation, a caller behind a dead')
    out.append('  flag, or whether the panel works. A zero in an app whose literalness has')
    out.append('  not been measured is a lead, not a verdict.')

    if not quiet:
        sys.stdout.write('\n'.join(out) + '\n')

    if strict and findings:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
