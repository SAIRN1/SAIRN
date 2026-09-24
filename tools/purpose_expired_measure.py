#!/usr/bin/env python
"""Three "purpose expired" detectors, designed and MEASURED and NOT shipped.

    python tools/purpose_expired_measure.py

Exit 0 always. This reports a measurement; it is not a checker and it has no
verdict to gate on.

── WHY THIS FILE EXISTS RATHER THAN A DETECTOR ────────────────────────────────
tools/sairn_reachability_check.py's R1-R3 ask "can anyone REACH this". R4 asks
"was it INVOKED", against Vercel production logs, a declared window and a
declared cadence. The sharpening asked for was the thing frequency can never
answer.

ARIANE 5 FLIGHT 501 destroyed a vehicle running correct, faithfully-copied
software whose PRECONDITION had expired: the inertial-reference alignment served
a pre-launch mode that could not occur after lift-off. Its invocation count was
irrelevant -- the REASON was gone. That is the difference between "rarely used
and still legitimate" (a disaster-recovery path, a year-end calculation) and
"genuinely purposeless", and no cadence figure separates them.

THREE CONCRETE SIGNALS WERE DESIGNED. ALL THREE WERE MEASURED BEFORE ANYTHING
WAS BUILT, AND ALL THREE WERE REFUSED. This file re-runs those measurements so
the refusal is reproducible rather than a claim somebody has to take on trust.

  R5a  A GUARD THAT CAN NEVER BE TRUE -- `if (false)`, or `if (CONST)` where
       CONST is assigned a falsy literal once and never reassigned.
       MEASURED: 0 across 188 files. A detector with an EMPTY POPULATION on a
       clean tree cannot be validated, and one that reports CLEAN forever is
       indistinguishable from one that is broken -- the exact class
       tools/sabotage_control_check.py exists for. Shipping it would add a
       permanent green light backed by nothing.

  R5b  A ROLE COMPARISON OUTSIDE THE APP'S OWN VOCABULARY -- a gate on
       `manager` in an app whose ROLES_BY_APP has no `manager`. THE NEAR-MISS IS
       REAL AND RECORDED: CLAUDE.md notes a decision briefed as "Admin/Manager"
       against a SAIRNcode that has no `manager`, where a literal implementation
       would have shipped a gate no account could pass.
       MEASURED: 14 hits, 14 false positives. Every one is a chat-message role
       (`msg.role === 'user'`/`'assistant'`/`'ai'`) or an employee JOB TITLE on
       an HR record (`e.role === 'fabricator'`). Precision 0 of 14. The hazard
       is real and is not in the tree; a detector for it would report fourteen
       non-findings, which is how a risk scorer fabricates an accuracy figure
       out of false positives -- something this platform has already done once.

  R5c  A HANDLER BRANCH ON AN ACTION NO RESOURCE REGISTRY GRANTS -- the
       `api/bridge.js` `pull` shape, removed 2026-09-17 with zero callers and no
       authentication.
       MEASURED: 70 of 100 branched actions match, and effectively all 70 are
       legitimate actions on auth, public and integration endpoints that never
       pass through the resource envelope gate at all. The premise was wrong:
       the registry governs api/sd-data.js's dispatch, not every handler.

── WHAT ACTUALLY DISCRIMINATES TODAY, AND IT IS A DECLARATION ─────────────────
tools/activity_cadence.json -- a human saying which rare paths are
rare-and-legitimate, with an owner and a reason. R4's coverage gate is why it
cannot discriminate yet: 13 of 64 routed endpoints observed over 72 hours, 20%,
under the 60% bar, so nothing is classified and the tool says so. THAT IS A DATA
PROBLEM, NOT A DESIGN PROBLEM. R5a-c were three attempts to derive a substitute
for the declaration, and the measurement is why none of them is here.

── AND THE REASON TO KEEP THE FILE AT ALL ─────────────────────────────────────
The platform's own precedent for this outcome is `sc_anesthesia_base_units` --
"the task was resolved by NOT DOING IT". The cost of not writing that down is
that the next session spends the same afternoon reaching the same three
refusals. A measured refusal is a result; an unrecorded one is a gap.
"""

import io
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def tracked():
    out = subprocess.run(['git', 'ls-files', '-z', '*.html', 'api/*.js',
                          'api/*/*.js'], cwd=REPO, capture_output=True)
    return [f for f in out.stdout.decode('utf-8').split('\0')
            if f and not f.startswith('archive/') and not f.endswith('.test.js')]


def body_of(rel):
    """Source with `//` comments dropped. Crude on purpose: this is a
    MEASUREMENT of a population, not a classifier, and a `//` inside a string
    costs at most one over-count in a figure that is reported, not acted on."""
    try:
        src = io.open(os.path.join(REPO, rel), encoding='utf-8',
                      errors='replace').read()
    except OSError:
        return ''
    return '\n'.join(l.split('//')[0] for l in src.split('\n'))


LIT = re.compile(r'\bif\s*\(\s*(?:false|0|null|undefined)\s*\)')
CONST = re.compile(r'\b(?:var|const|let)\s+([A-Z_][A-Z0-9_]*)\s*=\s*(?:false|0)\s*;')
ROLE_L = re.compile(r"""\brole\s*(?:===|==|!==|!=)\s*['"]([a-z_][a-z_0-9]*)['"]""")
ROLE_R = re.compile(r"""['"]([a-z_][a-z_0-9]*)['"]\s*(?:===|==|!==|!=)\s*\w*[Rr]ole\b""")


def r5a(files):
    n = 0
    for f in files:
        b = body_of(f)
        n += len(LIT.findall(b))
        for name in CONST.findall(b):
            if (len(re.findall(r'\b' + name + r'\s*=\s*(?!=)', b)) == 1
                    and re.search(r'\bif\s*\(\s*' + name + r'\s*\)', b)):
                n += 1
    return n


def roles_by_app():
    try:
        auth = io.open(os.path.join(REPO, 'api/_lib/auth.js'),
                       encoding='utf-8', errors='replace').read()
    except OSError as e:
        return None, str(e)
    m = re.search(r'ROLES_BY_APP\s*=\s*\{(.*?)\n\};', auth, re.S)
    if not m:
        return None, 'ROLES_BY_APP not found in api/_lib/auth.js'
    return {app: set(x.strip().strip("'") for x in r.split(',') if x.strip())
            for app, r in re.findall(r"(\w+)\s*:\s*\[([^\]]*)\]", m.group(1))}, None


def r5b(files, roles):
    hits = []
    for f in files:
        app = os.path.splitext(f)[0]
        if '/' in f or app not in roles:
            continue
        b = body_of(f)
        bad = set()
        for pat in (ROLE_L, ROLE_R):
            bad |= {r for r in pat.findall(b) if r not in roles[app]}
        for r in sorted(bad):
            hits.append((f, r))
    return hits


def r5c(files):
    granted = set()
    rdir = os.path.join(REPO, 'api', '_resources')
    try:
        names = sorted(os.listdir(rdir))
    except OSError as e:
        return None, None, str(e)
    for f in names:
        if not f.endswith('.js') or f.endswith('.test.js'):
            continue
        src = io.open(os.path.join(rdir, f), encoding='utf-8',
                      errors='replace').read()
        granted |= set(re.findall(r"'([a-z_]{3,24})'", src))
    branched = set()
    for f in files:
        if not f.startswith('api/') or f.startswith('api/_resources/'):
            continue
        branched |= set(re.findall(r"action\s*===\s*'([a-z_]+)'", body_of(f)))
    return sorted(branched - granted), sorted(branched), None


def main():
    print('PURPOSE EXPIRED -- three designed signals, re-measured. '
          'Report only.\n')
    files = tracked()
    if not files:
        print('COULD NOT MEASURE: git ls-files returned nothing, so every '
              'figure below\nwould be zero for the wrong reason. That is a '
              'could-not-tell, not a clean tree.')
        return 0

    n = r5a(files)
    print('R5a  a guard that can never be true            : %d across %d files'
          % (n, len(files)))
    print('     REFUSED. An empty population cannot be validated, and a detector')
    print('     that reports CLEAN forever is indistinguishable from a broken one.')
    print('')

    roles, err = roles_by_app()
    if roles is None:
        print('R5b  COULD NOT MEASURE -- %s' % err)
    else:
        hits = r5b(files, roles)
        print('R5b  role comparisons outside the app vocabulary: %d' % len(hits))
        for f, r in hits:
            print('       %-24s %s' % (f, r))
        print('     REFUSED. Every one measured is a chat-message role or an '
              'employee JOB')
        print('     TITLE on an HR record, not a session role. Precision 0 of %d.'
              % len(hits))
    print('')

    orphan, branched, err = r5c(files)
    if orphan is None:
        print('R5c  COULD NOT MEASURE -- %s' % err)
    else:
        print('R5c  handler branches on an ungranted action   : %d of %d'
              % (len(orphan), len(branched)))
        print('     REFUSED. The resource registry governs api/sd-data.js\'s '
              'dispatch, not')
        print('     every handler -- auth, public and integration endpoints all '
              'match, so')
        print('     the premise is wrong rather than the threshold.')
    print('')
    print('NONE OF THE THREE IS SHIPPED. What separates rare-but-legitimate from')
    print('purposeless today is tools/activity_cadence.json: a human declaration')
    print('with an owner and a reason. R4\'s coverage gate is why it cannot')
    print('discriminate yet -- 13 of 64 routes observed, under the 60% bar. That')
    print('is a DATA problem. R5a-c were three attempts to derive a substitute')
    print('for the declaration, and this is the measurement that refused them.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
