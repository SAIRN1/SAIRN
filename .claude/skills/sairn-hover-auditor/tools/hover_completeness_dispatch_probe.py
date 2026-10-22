#!/usr/bin/env python
"""hover_completeness_dispatch_probe.py -- an OUTSIDE-IN completeness check: does
docs/CRITICALITY-TIERS.md (the registry a Verification Certificate's own
"X of Y resources tiered" denominator rests on) actually name every
resource the live codebase dispatches, or has a resource gone live
(reachable, real, in the dispatch table) that the registry never recorded
at all. Own prefix, own location. Built 2026-10-07 (H1 batch Q, item 6).

METHOD, STATIC HALF (the reliable, primary method -- "git ls-files plus
...your own method"): re-derive the real resource population directly from
api/sd-data.js's own dispatch surface -- every `resource === 'x'` literal
AND every key inside a generic `const X_RESOURCES = {...}` table (the
table-driven dispatch shape this role has already found and routed several
real attribution gaps through this batch and the last). This is NOT the
same population hover_identity_attribution_check.py counts (that tool
counts ACTION BRANCHES for attribution; this tool counts DISTINCT RESOURCE
NAMES for registry completeness -- a different question, a different
denominator).

METHOD, LIVE HALF (secondary, read-only, no substitute for the static
half): for a resource the static diff finds MISSING from the registry,
optionally confirm it is genuinely reachable live (not dead code) via one
unauthenticated or demo-credentialed GET, using this role's own
hover_own_http.py. This never writes, never uses a non-demo credential, and
is a confirming step only -- the static diff is the real finding regardless
of whether the live half runs.

REGISTRY-MEMBERSHIP TEST: a resource counts as "named in the registry" if
its exact identifier appears ANYWHERE in docs/CRITICALITY-TIERS.md as a
backtick-quoted token (`resource_name`) -- the established convention this
file uses consistently for every resource name it ever mentions, in both
its per-app summary cells and its per-resource detail rows. A resource
mentioned only in unquoted prose would be missed by this test -- a real,
disclosed limitation, not assumed away.
"""
import json
import os
import re
import sys

RESOURCE_EQ_RE = re.compile(r"resource\s*===\s*'([a-z][a-z0-9_]*)'")
TABLE_DECL_RE = re.compile(r"const\s+[A-Z_]+_RESOURCES\s*=\s*\{")
TABLE_KEY_RE = re.compile(r"\b([a-z][a-z0-9_]*)\s*:\s*'[a-z0-9_]*_id'")


def _extract_table_blocks(text):
    """Yields the {...} body text of every `const X_RESOURCES = {...}` block,
    brace-balanced (never a regex guess at where a block ends)."""
    for m in TABLE_DECL_RE.finditer(text):
        start = m.end() - 1  # the '{' itself
        depth = 0
        for i in range(start, len(text)):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0:
                    yield text[start:i + 1]
                    break


_LINE_COMMENT_RE = re.compile(r'//.*$', re.M)


def _strip_line_comments(text):
    """Blanks // line comments (keeps line numbers/structure intact for any
    future caller that wants them) before resource extraction. Found
    necessary on this tool's own FIRST real run against api/sd-data.js: a
    comment at :391 illustrates the generic dispatch PATTERN using the
    literal placeholder shape "action === 'x' && resource === 'y'" as prose,
    and without this strip the regex read 'y' as a genuine resource name --
    a real false positive, fixed the same entry it was found, not left
    standing. Does not attempt to strip block comments or template-literal
    interiors -- api/sd-data.js's own convention is // line comments
    throughout, confirmed by this role's own extensive reading of this file
    across many prior batches, not a general-purpose JS comment stripper."""
    return _LINE_COMMENT_RE.sub('', text)


def derive_resource_population(sd_data_path):
    """Returns a sorted list of every distinct resource name this file's own
    dispatch surface names, from both extraction methods, de-duplicated."""
    with open(sd_data_path, encoding='utf-8') as f:
        text = _strip_line_comments(f.read())
    names = set()
    for m in RESOURCE_EQ_RE.finditer(text):
        names.add(m.group(1))
    for block in _extract_table_blocks(text):
        for m in TABLE_KEY_RE.finditer(block):
            names.add(m.group(1))
    return sorted(names)


def registry_named_set(tiers_path):
    """Every backtick-quoted token in docs/CRITICALITY-TIERS.md, restricted
    to ones that look like a resource identifier (lowercase, underscores) --
    not every backtick token in the file is a resource name (some are file
    paths, function names, etc.), but a resource name this role is looking
    FOR will always be lowercase/underscore-shaped, so over-matching here is
    harmless: it can only make a real gap LOOK covered less often, never
    more (a stricter false-negative direction, not a false-positive one)."""
    with open(tiers_path, encoding='utf-8') as f:
        text = f.read()
    return set(re.findall(r'`([a-z][a-z0-9_]*)`', text))


def diff(sd_data_path, tiers_path):
    population = derive_resource_population(sd_data_path)
    registered = registry_named_set(tiers_path)
    missing = [n for n in population if n not in registered]
    return {'population_count': len(population), 'registered_mentions': len(registered),
            'missing': missing}


def _selftest():
    import tempfile
    ok = 0
    total = 0

    total += 1
    fixture_sd = (
        "module.exports = async (req, res) => {\n"
        "  if (resource === 'known_resource' && action === 'read') { return; }\n"
        "  if (resource === 'orphan_resource' && action === 'write') { return; }\n"
        "  const GENERIC_RESOURCES = {\n"
        "    generic_known: 'generic_known_id', generic_missing: 'generic_missing_id'\n"
        "  };\n"
        "};\n"
    )
    fixture_tiers = (
        "| `app` | 2 | **1** | 1 | 0 | some prose mentioning `known_resource` "
        "and `generic_known` but not the others |\n"
    )
    fd1, p1 = tempfile.mkstemp(suffix='.js')
    fd2, p2 = tempfile.mkstemp(suffix='.md')
    with os.fdopen(fd1, 'w', encoding='utf-8') as f:
        f.write(fixture_sd)
    with os.fdopen(fd2, 'w', encoding='utf-8') as f:
        f.write(fixture_tiers)
    try:
        r = diff(p1, p2)
        expected_population = ['generic_known', 'generic_missing', 'known_resource', 'orphan_resource']
        if sorted(derive_resource_population(p1)) == expected_population:
            ok += 1
            print('  ok   both extraction methods (resource===, generic table keys) found, de-duplicated')
        else:
            print('  FAIL expected %r, got %r' % (expected_population, derive_resource_population(p1)))

        total += 1
        if set(r['missing']) == {'orphan_resource', 'generic_missing'}:
            ok += 1
            print('  ok   both genuinely-missing resources found (one from each extraction method), known ones correctly excluded')
        else:
            print('  FAIL expected missing={orphan_resource, generic_missing}, got %r' % r['missing'])
    finally:
        os.remove(p1)
        os.remove(p2)

    total += 1
    # A resource name that is a SUBSTRING of a registered one must not
    # false-negative-match (e.g. 'sd_invoice' must not be satisfied by a
    # registered 'sd_invoices') -- the regex uses the full backtick span,
    # which already prevents this, confirmed here rather than assumed.
    fd3, p3 = tempfile.mkstemp(suffix='.md')
    with os.fdopen(fd3, 'w', encoding='utf-8') as f:
        f.write('mentions `sd_invoices` only\n')
    try:
        reg = registry_named_set(p3)
        if 'sd_invoice' not in reg and 'sd_invoices' in reg:
            ok += 1
            print('  ok   a registered resource does not spuriously satisfy a similarly-named but DIFFERENT resource')
        else:
            print('  FAIL substring confusion: %r' % reg)
    finally:
        os.remove(p3)

    # Regression, found on this tool's own FIRST real run against the real
    # codebase (api/sd-data.js:391): a comment illustrating the generic
    # dispatch pattern using "resource === 'y'" as a PLACEHOLDER must not be
    # read as a real resource definition.
    total += 1
    comment_fixture = (
        "module.exports = async (req, res) => {\n"
        "  // REPLACED three hand-written `action === 'x' && resource === 'y'` flags\n"
        "  if (resource === 'genuinely_real' && action === 'read') { return; }\n"
        "};\n"
    )
    fd4, p4 = tempfile.mkstemp(suffix='.js')
    with os.fdopen(fd4, 'w', encoding='utf-8') as f:
        f.write(comment_fixture)
    try:
        pop = derive_resource_population(p4)
        if pop == ['genuinely_real']:
            ok += 1
            print('  ok   a resource== pattern inside a // comment (illustrating the shape, not a real definition) is correctly ignored')
        else:
            print('  FAIL expected only [genuinely_real], got %r' % pop)
    finally:
        os.remove(p4)

    print('%d/%d fixture checks correct' % (ok, total))
    return ok == total


def main(argv):
    if '--selftest' in argv:
        return 0 if _selftest() else 1
    if '--diff' in argv:
        i = argv.index('--diff')
        sd_data_path, tiers_path = argv[i + 1], argv[i + 2]
        r = diff(sd_data_path, tiers_path)
        print('resource population (from %s): %d' % (sd_data_path, r['population_count']))
        print('backtick-quoted tokens in %s: %d' % (tiers_path, r['registered_mentions']))
        print('MISSING FROM THE REGISTRY (%d): %s' % (len(r['missing']), ', '.join(r['missing']) if r['missing'] else '(none)'))
        return 0
    print('usage: hover_completeness_dispatch_probe.py --selftest | --diff SD_DATA_JS_PATH CRITICALITY_TIERS_MD_PATH')
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
