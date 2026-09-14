"""tier_a_bypass_check.py -- can external input reach a Tier A resource
without passing the verification path that resource is supposed to have?

    python tools/tier_a_bypass_check.py
    python tools/tier_a_bypass_check.py --json

── WHAT THIS IS AND IS NOT ────────────────────────────────────────────────
It is a BYPASS-RISK POINTER, not a gate and not a verdict. It answers one
mechanical question per HTTP handler: does this file name a Tier A resource,
and does it contain a refusal keyed to an identity check. It cannot tell
whether the refusal actually covers the write -- that needs somebody to read
the ordering, which is the whole shape of the 2026-09-04 deferred-refusal bug
(`api/sd-sub-data-auth-ordering.test.js`) where the gate existed and ran too
late.

So the output is THREE STATES and never two:

  GATED           a Tier A resource is named AND an identity check and a
                  refusal are both present
  NO GATE FOUND   a Tier A resource is named and NEITHER an identity check
                  nor a refusal appears anywhere in the file
  COULD NOT TELL  one of the two is present and the other is not

COULD NOT TELL IS THE INTERESTING COLUMN, not a rounding error. It is where a
file checks an identity and never refuses, or refuses on something that is not
an identity -- both are real shapes and both need a human.

── WHY "TIER A" COMES FROM THE REGISTER AND NOT FROM A GUESS ─────────────
docs/CRITICALITY-TIERS.md tiers by RESOURCE and says why: the first version
tiered whole apps and 21 of 22 came out Tier A, at which point it had stopped
discriminating. The Tier A names are parsed out of that document, so this tool
cannot invent its own opinion about what is critical. If the document cannot be
read, this REFUSES -- an audit that silently treats nothing as Tier A reports a
clean platform.

── THE LIMIT THAT MATTERS MOST ───────────────────────────────────────────
A resource NAME appearing in a handler does not prove the handler writes it,
and a handler that writes it through a helper this cannot see will be missed
entirely. This over-reports in one direction and under-reports in the other,
which is why it prints a read-list rather than a count to drive to zero.

REPORT ONLY. Exit 0 with findings, 2 when it could not look.
"""
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import jscomments                                             # noqa: E402

TIERS = os.path.join('docs', 'CRITICALITY-TIERS.md')

# An identity being established. Deliberately broad: a false GATED is worse
# than a false COULD NOT TELL, so anything that plausibly authenticates counts.
IDENTITY = re.compile(
    r'validateLicenseKey|requireSession|assertSession|resolveSession|'
    r'getSession|verifySession|employee_id|license_hash|licenseHash|'
    r'CRON_SECRET|cronToken|authorization|x-api-key', re.I)

# A refusal actually being issued.
REFUSAL = re.compile(
    r'status\(\s*40[13]\s*\)|status\(\s*405\s*\)|statusCode\s*=\s*40[13]|'
    r'NO_LICENSE|UNAUTHORIZED|FORBIDDEN|not authorised|not authorized', re.I)


def read(rel):
    p = os.path.join(REPO, rel.replace('/', os.sep))
    if not os.path.isfile(p):
        return None
    return io.open(p, encoding='utf-8', errors='replace').read()


def tier_a_resources():
    """Every resource the register marks Tier A. None -> could not read."""
    src = read(TIERS)
    if src is None:
        return None
    names = set()
    for line in src.split('\n'):
        if not line.startswith('|'):
            continue
        cells = line.split('|')
        if len(cells) < 4:
            continue
        name = cells[1].strip().strip('`*').strip()
        tier = cells[2].strip().strip('*').strip()
        if tier == 'A' and re.match(r'^[a-z][a-z0-9_]{2,}$', name):
            names.add(name)
        # The rollup rows list Tier A resources inline after "RE-TIERED --".
        m = re.search(r'RE-TIERED\s*&mdash;\s*(.+)$', line)
        if m:
            for n in re.findall(r'`([a-z][a-z0-9_]{2,})`', m.group(1)):
                names.add(n)
    return names


def handlers():
    out = []
    for root, dirs, files in os.walk(os.path.join(REPO, 'api')):
        dirs[:] = [d for d in dirs if d not in ('node_modules', '_lib', '_resources')]
        for f in sorted(files):
            if not f.endswith('.js') or f.endswith('.test.js'):
                continue
            rel = os.path.relpath(os.path.join(root, f), REPO).replace(os.sep, '/')
            out.append(rel)
    return out


def main(argv):
    names = tier_a_resources()
    if names is None:
        print('COULD NOT CHECK: %s is not in this clone, so there is no list of '
              'Tier A resources. An audit that treats nothing as Tier A reports '
              'a clean platform. Not a pass.' % TIERS)
        return 2
    if not names:
        print('COULD NOT CHECK: %s parsed to ZERO Tier A resources. Zero '
              'targets is not a clean sweep -- the document format has probably '
              'changed under this parser.' % TIERS)
        return 2

    files = handlers()
    if not files:
        print('COULD NOT CHECK: no handlers found under api/. Not a pass.')
        return 2

    rows = []
    dropped = []
    for rel in files:
        src = read(rel)
        if src is None:
            continue
        # ── COMMENTS STRIPPED FIRST, AND BOTH COUNTS KEPT (PR 1.2) ─────────
        # The first version matched raw source and its only two findings were
        # BOTH prose: api/greeting.js on the word "quotes" inside
        # 'slabs, quotes and jobs', and api/sairncash/portal.js on "invoices"
        # in a header comment. Two findings, two false positives -- a 0%
        # precision run, and the rule against it is already written down.
        # Several Tier A resources are ordinary English words (`quotes`,
        # `invoices`), so this is not an edge case here, it is the norm.
        code = jscomments.strip_comments(src)
        hit = sorted(n for n in names if re.search(r'\b' + re.escape(n) + r'\b', code))
        prose_only = sorted(n for n in names
                            if re.search(r'\b' + re.escape(n) + r'\b', src)
                            and n not in hit)
        if not hit:
            if prose_only:
                dropped.append((rel, prose_only))
            continue
        ident = bool(IDENTITY.search(code))
        refuse = bool(REFUSAL.search(code))
        state = ('GATED' if (ident and refuse)
                 else 'NO GATE FOUND' if not (ident or refuse)
                 else 'COULD NOT TELL')
        rows.append({'file': rel, 'state': state, 'identity': ident,
                     'refusal': refuse, 'tier_a': hit[:6], 'n_tier_a': len(hit)})

    counts = {}
    for r in rows:
        counts[r['state']] = counts.get(r['state'], 0) + 1

    if '--json' in argv:
        print(json.dumps({'tier_a_known': len(names), 'handlers': len(files),
                          'rows': rows, 'counts': counts}, indent=1))
        return 0

    print('TIER A BYPASS CHECK -- report only, nothing was written')
    print('  Tier A resources known to %s : %d' % (TIERS, len(names)))
    print('  handlers under api/ (not tests, not _lib): %d' % len(files))
    print('  of those, naming a Tier A resource IN CODE: %d' % len(rows))
    print('  dropped as PROSE ONLY (comment text, not a reference): %d' % len(dropped))
    for rel, ns in dropped:
        print('      %-42s %s' % (rel[:42], ','.join(ns)))
    print('')
    for state in ('NO GATE FOUND', 'COULD NOT TELL', 'GATED'):
        sel = [r for r in rows if r['state'] == state]
        if not sel:
            continue
        print('  %s (%d)' % (state, len(sel)))
        for r in sel:
            flags = ('identity:%s refusal:%s'
                     % ('y' if r['identity'] else 'n', 'y' if r['refusal'] else 'n'))
            print('    %-42s %-24s %s' % (r['file'][:42], flags,
                                          ','.join(r['tier_a'][:3])))
        print('')
    print('  READ THE FIRST TWO GROUPS. GATED is not a clearance: this cannot')
    print('  tell whether the refusal runs BEFORE the write, which is exactly')
    print('  the deferred-refusal shape api/sd-sub-data-auth-ordering.test.js')
    print('  exists for -- the gate was there and it ran too late.')
    print('')
    print('  AND A NAME IS NOT A WRITE. A handler that merely mentions a Tier A')
    print('  table is listed here, and one that writes it through a helper this')
    print('  cannot see is MISSED ENTIRELY. Over-reports one way, under-reports')
    print('  the other -- a read-list, never a number to drive to zero.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
