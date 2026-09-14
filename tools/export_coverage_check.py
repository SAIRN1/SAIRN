"""export_coverage_check.py -- a Class A record with no way to produce a FILE.

    python tools/export_coverage_check.py
    python tools/export_coverage_check.py --json
    python tools/export_coverage_check.py --check

── ITEM 39c, AND THE HALF OF THE QUESTION A TOOL CAN ANSWER ──────────────
Item 39 asks whether a record required to survive can be RETRIEVED by somebody
who has to produce it. Fourth answered it for `sv_audit_log` by hand and left
nine Class A resources UNASSESSED, naming the method: derive the backing
variable from the key rather than counting key-string references.

That method was run for all nine (`docs/2026-09-14-class-a-retrievability.md`)
and it splits cleanly in two:

  * CAN A PERSON SEE IT ON SCREEN -- answered by tracing a backing variable to
    a renderer reachable from a nav root. **A tool cannot do this reliably and
    this one does not try.** Two detectors were written and both were wrong in
    opposite directions: binding on the key string alone missed
    `alf_staff_credentials` entirely (its renderer reads `_crRecords` and never
    names the key), and binding transitively bound most of SAIRNdental, because
    a generic sync layer names every key and everything it touches inherits it.
    Read the document; its answers were hand-verified against the source.

  * CAN A PERSON PRODUCE IT AS A FILE -- this is enumerable, and it is what
    this tool checks. Two apps carry an explicit export registry and the other
    two carry no export machinery at all, so "is this resource in its app's
    export registry" has a definite answer per resource.

── WHY THE FILE HALF IS THE HALF WORTH GATING ────────────────────────────
An inspector, an auditor or a subpoena asks for a RECORD, not a screenshot. A
panel that renders the rows answers "can staff look it up"; it does not answer
"can this practice hand over what it was asked for". Those are different
questions and only the second one has a deadline attached.

── THE CLASS A SET IS PARSED, NOT LISTED HERE ────────────────────────────
It comes from the table in
`docs/2026-09-13-irreversible-write-witnessing-scoping.md` -- the resources
whose own registry files declare them append-only by design. If that table
stops parsing, this exits 2 rather than reporting a clean sweep over an empty
set. A hardcoded copy here would be a second list to drift.

REPORT ONLY. Exit 0, 2 when it could not look. With `--check`, exit 1 when a
Class A resource in an app that HAS an export registry is missing from it --
which is a gap in a mechanism that already exists, not a missing feature.
"""
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(REPO, 'docs',
                      '2026-09-13-irreversible-write-witnessing-scoping.md')

# A row of the Class A table: | `appname` | `res_a`, `res_b`, prose |
ROW = re.compile(r'^\|\s*`([a-z]+)`\s*\|(.+?)\|\s*$', re.M)
RES = re.compile(r'`([a-z]+_[a-z_]+)`')

# An export registry entry names the resource it reads. SAIRNroofing writes it
# as `resource:'rf_x', action:'read'`; SAIRNdental keys its registry by a short
# label, so the resource is reached through the accessor its `rows:` calls --
# the short key is resolved against the app's own sync-pair table.
ROOFING_ENTRY = re.compile(r"resource:\s*'([a-z_]+)'\s*,\s*action:\s*'read'")
PAIR = re.compile(r"\[\s*'([a-z_]+)'\s*,\s*'([a-z_]+)'\s*\]")
# The registry itself: an object whose entries carry BOTH a column list and a
# row source. Anything with only one of those is not an export.
REGISTRY_ENTRY = re.compile(r"^\s{2}([a-z_]+):\{label:.*?columns:", re.M | re.S)
CSV = re.compile(r'text/csv|createObjectURL')


def class_a():
    """(app, resource) pairs, parsed from the scoping document's own table."""
    if not os.path.isfile(SOURCE):
        return None, 'the Class A source document is missing: ' + SOURCE
    raw = io.open(SOURCE, encoding='utf-8', errors='replace').read()
    out = []
    for app, rest in ROW.findall(raw):
        for res in RES.findall(rest):
            out.append((app, res))
    # sv_controlled is named in the prose immediately below the table, not in
    # it -- the document says so explicitly. Taken from that sentence rather
    # than assumed, and its absence is an error rather than a silent nine.
    if re.search(r'`sv_controlled`\s*[-—]', raw):
        out.append(('sairnvet', 'sv_controlled'))
    if len(out) < 8:
        return None, ('the Class A table parsed to %d resources, which is fewer '
                      'than the document has ever held -- the table shape '
                      'changed and this check has stopped reading it' % len(out))
    return out, None


def app_exports(app):
    """(set_of_exported_resources, has_registry) for one app file."""
    p = os.path.join(REPO, app + '.html')
    if not os.path.isfile(p):
        return None, None
    code = io.open(p, encoding='utf-8', errors='replace').read()
    if not CSV.search(code):
        return set(), False          # no export machinery at all
    found = set(ROOFING_ENTRY.findall(code))
    if found:
        return found, True
    # Registry keyed by short label: resolve each key through the accessor its
    # rows: function calls, then through the app's sync-pair table.
    pairs = dict((b, a) for a, b in PAIR.findall(code))   # localkey -> resource
    keys = REGISTRY_ENTRY.findall(code)
    if not keys:
        return set(), False
    for k in keys:
        at = code.find('\n  ' + k + ':{label:')
        body = code[at:at + 1200]
        for fn in re.findall(r'rows:function\(\)\{return\s+([A-Za-z_$][\w$]*)\(', body):
            a = code.find('function ' + fn + '(')
            if a < 0:
                continue
            acc = code[a:a + 200]
            for m in re.finditer(r"ld\(\s*'([a-z_]+)'", acc):
                if m.group(1) in pairs:
                    found.add(pairs[m.group(1)])
    return found, True


def main(argv):
    pairs, why = class_a()
    if pairs is None:
        print('COULD NOT CHECK: %s' % why)
        print('ZERO TARGETS IS NOT A CLEAN SWEEP.')
        return 2
    rows, unreadable = [], []
    cache = {}
    for app, res in pairs:
        if app not in cache:
            cache[app] = app_exports(app)
        exported, has_registry = cache[app]
        if exported is None:
            unreadable.append(app)
            continue
        rows.append({'app': app, 'resource': res,
                     'exported': res in exported,
                     'app_has_registry': bool(has_registry)})
    if unreadable:
        print('COULD NOT CHECK: no app file for %s' % ', '.join(sorted(set(unreadable))))
        return 2

    gaps = [r for r in rows if not r['exported'] and r['app_has_registry']]
    nomech = [r for r in rows if not r['exported'] and not r['app_has_registry']]
    if '--json' in argv:
        print(json.dumps({'rows': rows, 'gaps': gaps, 'no_machinery': nomech},
                         indent=1))
        return 0

    head = ('EXPORT COVERAGE OF THE CLASS A SET -- can the record be produced '
            'as a FILE')
    if '--check' in argv:
        print('%s : %d resource(s), %d exportable, %d gap(s) in an app that '
              'already has a registry, %d in an app with no export machinery '
              '(NOT gated)' % (head, len(rows), len([r for r in rows if r['exported']]),
                               len(gaps), len(nomech)))
        if not gaps:
            return 0
        # `  - ` PREFIX, DELIBERATELY. report_only_checks.by_exit keeps only
        # lines starting `  - ` or `FAIL`; everything else is collapsed to the
        # bare string "exit 1". Four named resources are the useful part and
        # they would have been thrown away by the registry that runs this --
        # the same wired-by-something-it-does-not-emit class that left
        # literal_drift_check.py reporting nothing for weeks. An arm holds it.
        for r in gaps:
            print('  - %-14s %-24s its app HAS an export registry and this '
                  'resource is not in it' % (r['app'], r['resource']))
        return 1

    print(head)
    print('  Class A resources parsed from the scoping doc : %d' % len(rows))
    print('')
    for r in sorted(rows, key=lambda x: (x['app'], x['resource'])):
        mark = 'EXPORTABLE' if r['exported'] else (
            'NOT IN REGISTRY' if r['app_has_registry'] else 'NO EXPORT MACHINERY')
        print('  %-14s %-24s %s' % (r['app'], r['resource'], mark))
    print('')
    print('  THIS IS HALF THE QUESTION AND THE OTHER HALF IS NOT MECHANICAL.')
    print('  Whether a person can SEE these rows on screen is a backing-variable')
    print('  trace that two detectors got wrong in opposite directions; the')
    print('  hand-verified answers are in')
    print('  docs/2026-09-14-class-a-retrievability.md. A resource marked')
    print('  EXPORTABLE here is still only exportable BY WHOEVER THE GATE LETS')
    print('  -- the registries carry per-role scoping and this does not read it.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
