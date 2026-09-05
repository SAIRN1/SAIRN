"""Every resource an app WRITES to the server should also be READ back.

WHY THIS EXISTS. Twice on 2026-09-04/05 an app was found writing real business
records to Postgres and never reading any of them back, so the data was on the
server and unreachable: a second workstation, or the same one after a browser
data clear, opened an empty app.

  SAIRNbiz   -- 17 localStorage collections, ONE reached a server.
  SAIRNlaw   -- 20 resources written across 31 call sites, exactly one read
                (shared_knowledge). No hydrate function of any name existed.

Both were invisible for months. Neither was found by a tool; the first came
from reading an index row and the second from a hunch while closing it. This is
the tool, so the third one is found by a machine.

IT CATCHES ONE OF THOSE TWO, AND THE MEASUREMENT SAID SO RATHER THAN THE
INTENTION. Run against sairnlaw.html at the commit before its hydrate landed it
exits 1 and names all nineteen. Run against sairnbiz.html at the commit before
ITS backup landed it says nothing at all -- correctly, by its own rules, and
uselessly: SAIRNbiz was not writing to a server through a wrapper, it was
writing to localStorage and stopping. "Written to the server and never read
back" and "never written to the server at all" are different defects, and this
one only sees the first. The second needs a different check, comparing an app's
localStorage collections against the resources it registers; that is not built
and is not implied here.

It also catches the narrower shape that hid the SAIRNlaw case in plain sight: a
resource written by the client but never registered, which fails at the
allowlist on every save. A name written and neither read nor registered is the
loudest signal this can produce.

-- WHAT IT DOES --------------------------------------------------------------
Per app HTML file, it collects the resource names passed to a data wrapper as
'write' and as 'read', resolves the common LOOP shapes so a generic hydrate
counts as reading everything it iterates, and reports write names with no read.

-- WHAT IT CANNOT SEE, said here rather than discovered later ------------------
  * A write whose resource is a VARIABLE. Every current app passes a literal,
    but a future one need not, and such a write is invisible here.
  * A wrapper whose name does not end in `Data(`. The platform convention is
    sdnData/sbData/scData/etc.; anything else is not matched, and this is
    reported per file as SCANNED-BY-NAME so an absence is not read as a pass.
  * A read loop built from anything other than a flat array of strings, an
    array of pairs, or Object.keys(<object literal>). Anything else resolves
    to COULD NOT TELL for that file, which is NOT a pass -- the exit code says
    so.
  * Whether the read is ever CALLED. A hydrate that exists and is never invoked
    reads clean here. tools/sairn_reachability_check.py is the tool for that
    question, and this one says so rather than implying coverage it lacks.

FIRST RUN, MEASURED RATHER THAN ASSUMED: proven to go RED on sairnlaw.html at
the commit before its hydrate landed, and clean on it afterwards. A checker
that has only ever returned clean is a checker whose behaviour nobody knows.
"""
import os
import re
import sys

# Resources that are shared platform infrastructure rather than an app's own
# record set. They are written without a matching per-app read by design --
# shared_knowledge is a write-only topic sink, memory/profile are read through
# their own bespoke paths. Listing them by name, not by prefix: a silent
# category exclusion is how a real resource hides.
PLATFORM_RESOURCES = {
    'shared_knowledge', 'memory', 'profile', 'employees', 'render_usage',
    'employee_profile', 'style_profile', 'exec_context', 'supplier_lead_times',
}

WRITE_RE = re.compile(r"\w*Data\(\s*'write'\s*,\s*'(\w+)'")
READ_LIT_RE = re.compile(r"\w*Data\(\s*'read'\s*,\s*'(\w+)'")
READ_VAR_RE = re.compile(r"\w*Data\(\s*'read'\s*,\s*([A-Za-z_$][\w$]*)")
WRAPPER_RE = re.compile(r"function\s+(\w*Data)\s*\(")


def strip_comments(src):
    """Line comments only. Enough for this: every call site is code, and a
    commented-out example must not count as coverage."""
    return '\n'.join(l for l in src.split('\n') if not l.strip().startswith('//'))


def _literal_body(src, name, opener, closer):
    """The text of the array/object literal assigned to `name`, or None."""
    m = re.search(r'\b(?:var|let|const)\s+' + re.escape(name) + r'\s*=\s*' + re.escape(opener), src)
    if not m:
        return None
    start = src.index(opener, m.start())
    depth = 0
    for i in range(start, min(len(src), start + 40000)):
        if src[i] == opener:
            depth += 1
        elif src[i] == closer:
            depth -= 1
            if depth == 0:
                return src[start:i + 1]
    return None


def declared_read_sets(src, writes):
    """Resource lists the app declares for a generic read loop.

    THE VARIABLE AT A READ CALL SITE IS ALMOST ALWAYS A FUNCTION PARAMETER --
    `LEG_SYNC_RESOURCES.map(function (key) { return sdnData('read', key); })`,
    or a for-loop index into a list of pairs, or a second hop through a helper
    like scSyncOneResource(resource). Following that properly needs dataflow
    this does not have, and guessing at it would be worse than saying so.

    So it works from the other end: any array or object literal whose entries
    OVERLAP THE APP'S OWN WRITE SET by at least two names is treated as a
    declared read set. The overlap requirement is what keeps an unrelated
    constant list out -- a list of colours or panel ids shares nothing with the
    resources this app writes.

    NAME CASE IS NOT PART OF THE TEST, and that was measured rather than
    assumed. An earlier version required SCREAMING_CASE and reported all 30 of
    SAIRNgrounds' resources as never read back -- a false positive, because
    grdSyncFromServer() builds its list in a local `var resources=[[...]]`
    inside the function. A checker that cries wolf on a whole app is worse than
    none.

    THE RESIDUAL RISK, in the direction that matters: a list that is NOT a read
    set but happens to contain two or more of the app's resource names would be
    counted as coverage that does not exist. That is why the set NAMES are
    printed on every run -- so a wrong resolution is visible rather than
    implied.

    Returns (names, sets_found).
    """
    names, found = set(), []
    for m in re.finditer(r'\b(?:var|let|const)\s+(\w+)\s*=\s*([\[{])', src):
        var, opener = m.group(1), m.group(2)
        body = _literal_body(src, var, opener, ']' if opener == '[' else '}')
        if not body:
            continue
        if opener == '[':
            entries = set(re.findall(r"'(\w+)'", body))
            pairs = re.findall(r"\[\s*'(\w+)'\s*,\s*'\w+'\s*\]", body)
            if pairs:
                entries = set(pairs)
        else:
            entries = set(re.findall(r"[{,]\s*'?(\w+)'?\s*:", body))
        overlap = entries & writes
        if len(overlap) >= 2:
            names |= overlap
            found.append(var)
    return names, found


def read_coverage(src, writes):
    """(names read, unresolved reasons, declared sets used).

    A variable read whose set cannot be resolved is a REASON, never silent
    coverage.
    """
    names = set(READ_LIT_RE.findall(src))
    var_reads = set(READ_VAR_RE.findall(src))
    declared, found = declared_read_sets(src, writes)
    reasons = []
    if var_reads:
        if declared:
            names |= declared
        else:
            reasons.append('a generic read loop exists (%s) but no declared list '
                           'overlaps this app\'s write set' % ', '.join(sorted(var_reads)))
    return names, reasons, found


def audit(path):
    src = strip_comments(open(path, encoding='utf-8', errors='replace').read())
    writes = set(WRITE_RE.findall(src)) - PLATFORM_RESOURCES
    if not writes:
        return None
    reads, reasons, declared = read_coverage(src, writes)
    wrappers = sorted(set(WRAPPER_RE.findall(src)))
    return {
        'file': os.path.basename(path),
        'writes': writes,
        'reads': reads,
        'missing': sorted(writes - reads),
        'reasons': reasons,
        'declared': declared,
        'wrappers': wrappers,
    }


def main(argv):
    targets = argv[1:] or sorted(f for f in os.listdir('.') if f.endswith('.html'))
    results = [r for r in (audit(t) for t in targets) if r]
    bad, unsure = [], []
    print('SCANNED-BY-NAME: only calls to a wrapper matching \\w*Data( are seen.')
    print('%-24s %-7s %-7s %s' % ('app', 'writes', 'read', 'declared read set(s)'))
    for r in sorted(results, key=lambda x: x['file']):
        print('%-24s %-7d %-7d %s' % (r['file'], len(r['writes']),
                                      len(r['writes'] & r['reads']),
                                      ', '.join(r['declared']) or '(literal reads only)'))
        if r['missing']:
            bad.append(r)
        if r['reasons']:
            unsure.append(r)

    print('\n=== WRITTEN AND NEVER READ BACK ===')
    if not bad:
        print('  none')
    for r in bad:
        print('  %s' % r['file'])
        for n in r['missing']:
            print('      %s' % n)

    print('\n=== COULD NOT TELL -- NOT A PASS ===')
    if not unsure:
        print('  none')
    for r in unsure:
        for why in r['reasons']:
            print('  %-24s %s' % (r['file'], why))

    print('\nNOTE: this cannot tell whether a read is ever CALLED. A hydrate that')
    print('      exists and is never invoked reads clean here -- see')
    print('      tools/sairn_reachability_check.py for that question.')
    return 1 if (bad or unsure) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
