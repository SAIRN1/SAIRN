"""tools/panel_depth.py -- how deep is a panel, measured, one signal at a time.

    python tools/panel_depth.py sairncode claims prebill hcc drg rac denial ar revenue
    python tools/panel_depth.py --lock-only          # run the fixture lock, judge nothing

WHY THIS EXISTS, AND IT IS A DEBT TWO DOCUMENTS RECORDED AND NEITHER PAID.

`docs/competitive-gap-audit-sairncode.md` (2026-09-23) says of the eight
enterprise RCM panels: *"SAIRNcode's existing panel set already covers real
enterprise RCM breadth ON PAPER ... that is exactly the sentence to be careful
with. Breadth of panel is not depth of function, and this audit measured the
presence of vocabulary and resources, not the sufficiency of any one workflow at
scale. A direct depth check on those eight panels is owed before pitching a large
hospital system, and it is not performed in this document."*

The 2026-09-26 cloud audit inherited that verdict and its own §6 says the same:
*"It does not verify ... the depth of SAIRNcode's eight enterprise RCM panels."*
So the question has been deferred twice by documents that each名 it as owed. This
is the instrument.

── WHAT IT MEASURES, AND WHAT IT REFUSES TO ──────────────────────────────────
Nine signals, each a fact about a named file. A panel that stores and renders
scores well on the shallow ones and badly on the deep ones, which is the whole
point: the shallow signals are what "vocabulary and resources are present" MEANS,
and they are exactly what the audits already had.

IT DOES NOT MEASURE WHETHER THE WORKFLOW IS SUFFICIENT AT HOSPITAL SCALE. That
is the question the audits actually deferred and no static instrument can answer
it -- it needs a real customer's volume and a real coder's judgement. What this
can do is separate "there is a table and a form" from "there is a rule, a server
that enforces it, and a test that drives it", which is a strictly weaker claim
and is stated as one everywhere it appears.

── TWO NUMBERS, NEVER ONE (cross-domain discipline 2) ────────────────────────
Every row carries PRESENT (how many of the nine signals were found) and
COULD-NOT-TELL (how many could not be decided because a source file was absent
or unreadable). They are never added together and never folded into a "depth
score", because a panel with 4 present / 5 unknown and one with 4 present / 0
unknown are different findings and a single figure hides which.

── THE FIXTURE LOCK (cross-domain discipline 1) ──────────────────────────────
The criteria are decided against hand-built fixtures BEFORE anything real is
judged, and the tool exits 2 with "nothing real was judged" if any fixture
misclassifies. FIXTURES WERE CORRECTED ONCE DURING DEVELOPMENT AND THE REASON IS
DECLARED, per that discipline's own rule: the `derived_verb` fixture originally
expected a file-wide match, which is wrong -- see the note on that signal.

── THE MISTAKE THIS TOOL WAS BUILT AROUND (cross-domain discipline 3) ────────
A first pass counted the domain verb `therapy_accumulator` with a file-wide grep
and credited ALL EIGHT panels with it, because the string appears twice in
api/_resources/sairncode.js and a count does not know which resource a line is
about. It belongs to `sc_claims` alone. That is the same failure as the
`debit|credit` keyword pass that classified a ledger on five COMMENT lines, and
it is why every signal here records the substring it matched on and why the verb
signal requires the resource name and the verb on the SAME line.

Exit 0 measured / 1 a signal could not be read at all / 2 fixture lock failed.
"""
import io
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# STAMPED, AND IT MOVED ONCE ALREADY. .1 was the version the fixture lock
# rejected (sig_panel matched a commented-out panel id) plus the version whose
# domain_verb credited five sibling resource names as verbs on the first real
# run. .2 is both fixes and the two fixtures added for them. A criteria change
# without a version change makes two runs incomparable while looking comparable.
CRITERIA_VERSION = '2026-09-26.2'


def read(rel):
    """(text, could_not_read_reason)."""
    p = os.path.join(REPO, rel)
    if not os.path.isfile(p):
        return None, 'absent: ' + rel
    try:
        return io.open(p, encoding='utf-8', errors='replace').read(), None
    except OSError as e:
        return None, '%s: %s' % (type(e).__name__, e)


def strip_comments(src):
    """Code lines only. Discipline 3's worked example is a keyword pass that
    classified a file on five comment lines; every signal below that could be
    satisfied by prose runs on this."""
    out = []
    for line in src.split('\n'):
        s = line.strip()
        if s.startswith('//') or s.startswith('*') or s.startswith('/*') \
           or s.startswith('<!--') or s.startswith('--'):
            continue
        out.append(line)
    return '\n'.join(out)


# ── THE NINE SIGNALS ───────────────────────────────────────────────────────
# Each returns (True/False/None, evidence). None is COULD-NOT-TELL and is never
# False: a source file that is absent is not a finding that the panel lacks the
# thing, which is the fail-open direction this repo keeps correcting.
#
# SHALLOW (1-4) is what "the vocabulary and resources are present" already meant.
# DEEP (5-9) is the part the audits deferred.

def sig_panel(ctx, p):
    src = ctx.get('app')
    if src is None:
        return None, ctx['app_why']
    # CODE ONLY, AND THE FIXTURE LOCK IS WHY. The first version searched the raw
    # file and the lock's "a panel named ONLY in a comment" fixture caught it
    # BEFORE any real panel was judged -- which is the entire purpose of running
    # the lock first. A commented-out panel id is exactly the state this tool
    # exists to distinguish from a live one.
    needle = 'id="panel-%s"' % p
    return (needle in strip_comments(src)), needle


def sig_nav(ctx, p):
    src = ctx.get('app')
    if src is None:
        return None, ctx['app_why']
    needle = "showPanel('%s')" % p
    return (needle in strip_comments(src)), needle


def sig_registered(ctx, p):
    src = ctx.get('registry')
    if src is None:
        return None, ctx['registry_why']
    needle = "'%s_%s'" % (ctx['prefix'], p)
    return (needle in strip_comments(src)), needle


def sig_write(ctx, p):
    src = ctx.get('app')
    if src is None:
        return None, ctx['app_why']
    code = strip_comments(src)
    pats = ["%sData('write', '%s_%s'" % (ctx['client'], ctx['prefix'], p),
            "'write', '%s_%s'" % (ctx['prefix'], p)]
    for n in pats:
        if n in code:
            return True, n
    return False, pats[-1]


def sig_schema(ctx, p):
    d = os.path.join(REPO, 'sql')
    if not os.path.isdir(d):
        return None, 'absent: sql/'
    needle = '%s_%s' % (ctx['prefix'], p)
    for f in sorted(os.listdir(d)):
        if not f.endswith('.sql'):
            continue
        t, _ = read(os.path.join('sql', f))
        if t and re.search(r'create table[^;]{0,200}\b' + re.escape(needle) + r'\b',
                           t, re.I | re.S):
            return True, 'sql/%s (create table)' % f
    return False, 'no `create table ... %s` in sql/' % needle


def sig_server_named(ctx, p):
    """Is the resource NAMED server-side, or does it ride the generic handler?

    This is the sharpest of the nine. A resource whose name appears nowhere in
    the endpoint has no per-resource rule by construction -- it is stored and
    handed back, and any validation it has is whatever the generic branch does
    for everything."""
    src = ctx.get('endpoint')
    if src is None:
        return None, ctx['endpoint_why']
    needle = '%s_%s' % (ctx['prefix'], p)
    n = len(re.findall(r'\b' + re.escape(needle) + r'\b', strip_comments(src)))
    return (n > 0), '%d code mention(s) in %s' % (n, ctx['endpoint_rel'])


def sig_domain_verb(ctx, p):
    """A verb BEYOND generic CRUD, attributed to THIS resource.

    FIXTURE CORRECTED HERE, AND THE REASON IS THE POINT. The first version
    grepped the registry file for any extra verb and credited every resource in
    it -- all eight panels came back True off two occurrences of
    `therapy_accumulator`, which belongs to sc_claims alone. The fixture that
    expected that was WRONG rather than inconvenient, so it was changed. The
    criterion now requires the resource name and the verb on the SAME line, and
    ignores the three generic verbs every resource gets."""
    src = ctx.get('registry')
    if src is None:
        return None, ctx['registry_why']
    GENERIC = {'delete', 'soft_delete', 'tombstones', 'read', 'write'}
    res = '%s_%s' % (ctx['prefix'], p)
    # A SIBLING RESOURCE NAME IS NOT A VERB, and the first run of this tool on
    # real data reported `sc_prebill: sc_drg, sc_eligibility, sc_fraud, sc_hcc,
    # sc_pctc` -- because SC_TIER_A_SOFT_DELETE_ONLY puts several resource names
    # on one line, and a quoted-string scan cannot tell a neighbour from a verb.
    # Same family as the file-wide `therapy_accumulator` error this signal was
    # already written to avoid: an attribution that is nearly right. Anything
    # carrying the app's own resource prefix is excluded by name.
    pfx = ctx['prefix'] + '_'
    for line in strip_comments(src).split('\n'):
        if res not in line:
            continue
        verbs = [v for v in re.findall(r"'([a-z_]{3,})'", line)
                 if v not in GENERIC and v != res and not v.startswith(pfx)]
        if verbs:
            return True, '%s: %s' % (res, ', '.join(sorted(set(verbs))))
    return False, '%s carries only generic CRUD verbs' % res


def sig_verb_sent(ctx, p):
    """A declared domain verb is only depth if a client sends it. An undeclared
    handler is unreachable; a declared-but-unsent one is the SAIRNmechanical
    `eligibility` defect -- engine, endpoint, registry and tests, and no
    caller."""
    has, ev = sig_domain_verb(ctx, p)
    if has is None:
        return None, ev
    if not has:
        return False, 'no domain verb to send'
    app = ctx.get('app')
    if app is None:
        return None, ctx['app_why']
    code = strip_comments(app)
    verbs = ev.split(': ', 1)[1].split(', ')
    sent = [v for v in verbs if ("'%s'" % v) in code]
    return (len(sent) > 0), ('sent: ' + ', '.join(sent)) if sent \
        else ('DECLARED AND NEVER SENT: ' + ', '.join(verbs))


def sig_suite(ctx, p):
    needle = '%s_%s' % (ctx['prefix'], p)
    hits = []
    for base in ('tests', 'api'):
        d = os.path.join(REPO, base)
        if not os.path.isdir(d):
            continue
        for root, _dirs, files in os.walk(d):
            for f in files:
                if not (f.endswith('.test.js') or (base == 'tests' and f.endswith(('.js', '.py')))):
                    continue
                rel = os.path.relpath(os.path.join(root, f), REPO).replace('\\', '/')
                t, _ = read(rel)
                if t and needle in t:
                    hits.append(rel)
    return (len(hits) > 0), '%d file(s), e.g. %s' % (len(hits), hits[0]) if hits \
        else 'no test file names %s' % needle


def sig_tiered(ctx, p):
    src = ctx.get('tiers')
    if src is None:
        return None, ctx['tiers_why']
    needle = '%s_%s' % (ctx['prefix'], p)
    return (needle in src), needle


SIGNALS = [
    ('panel', 'SHALLOW', sig_panel, 'a panel div exists'),
    ('nav', 'SHALLOW', sig_nav, 'something navigates to it'),
    ('registered', 'SHALLOW', sig_registered, 'the resource is registered'),
    ('write', 'SHALLOW', sig_write, 'the client writes to it'),
    ('schema', 'DEEP', sig_schema, 'a real SQL table, not localStorage only'),
    ('server_named', 'DEEP', sig_server_named, 'named server-side, so it can have a rule'),
    ('domain_verb', 'DEEP', sig_domain_verb, 'a verb beyond generic CRUD'),
    ('verb_sent', 'DEEP', sig_verb_sent, '...and a client actually sends it'),
    ('suite', 'DEEP', sig_suite, 'a test file names it'),
]


def build_ctx(app):
    """Everything the signals read, loaded once, with a reason per failure."""
    app_rel = '%s.html' % app
    reg_rel = 'api/_resources/%s.js' % app
    end_rel = 'api/sd-data.js'
    tier_rel = 'docs/CRITICALITY-TIERS.md'
    a, a_why = read(app_rel)
    r, r_why = read(reg_rel)
    e, e_why = read(end_rel)
    t, t_why = read(tier_rel)
    PREFIX = {'sairncode': 'sc', 'sairndental': 'dnt', 'sairnmechanical': 'mech',
              'sairnroofing': 'rf', 'sairnsenior': 'sen', 'stonedesk': 'sd'}
    CLIENT = {'sairncode': 'sc', 'sairndental': 'dnt', 'sairnmechanical': 'mech',
              'sairnroofing': 'rf', 'sairnsenior': 'sen', 'stonedesk': 'sd'}
    return {'app': a, 'app_why': a_why, 'registry': r, 'registry_why': r_why,
            'endpoint': e, 'endpoint_why': e_why, 'endpoint_rel': end_rel,
            'tiers': t, 'tiers_why': t_why,
            'prefix': PREFIX.get(app, app[:3]), 'client': CLIENT.get(app, app[:3])}


# ── THE FIXTURE LOCK ───────────────────────────────────────────────────────
# Hand-built contexts, in isolation, never beside real output. A lock that rides
# alongside live data can be satisfied by the data.
FIXTURES = [
    # (name, ctx-overrides, panel, signal, expected)
    ('a panel div that exists',
     {'app': '<div class="panel" id="panel-claims">'}, 'claims', 'panel', True),
    ('a panel named ONLY in a comment does not count',
     {'app': '// id="panel-claims" used to be here\n'}, 'claims', 'panel', False),
    ('nav in a comment does not count',
     {'app': "  // showPanel('claims') was removed\n"}, 'claims', 'nav', False),
    ('an absent app file is COULD-NOT-TELL, not False',
     {'app': None, 'app_why': 'absent: x.html'}, 'claims', 'panel', None),
    ('a domain verb on the resource line counts',
     {'registry': "map['sc_claims'] = ['delete', 'therapy_accumulator'];"},
     'claims', 'domain_verb', True),
    # THE CORRECTED FIXTURE. Expecting True here was the original criterion and
    # it was WRONG, not inconvenient: the verb is on another resource's line.
    ('a domain verb on a DIFFERENT resource line does NOT count',
     {'registry': "map['sc_claims'] = ['delete'];\nmap['sc_other'] = ['therapy_accumulator'];"},
     'claims', 'domain_verb', False),
    ('generic CRUD verbs alone are not a domain verb',
     {'registry': "map['sc_claims'] = ['soft_delete', 'tombstones'];"},
     'claims', 'domain_verb', False),
    # ADDED AFTER THE FIRST REAL RUN, which is the honest order: the lock did not
    # predict this shape and the real data produced it. Several resource names on
    # one line -- the SC_TIER_A_SOFT_DELETE_ONLY list -- read as five verbs.
    ('SIBLING RESOURCE NAMES ON THE SAME LINE ARE NOT VERBS',
     {'registry': "const L = ['sc_prebill', 'sc_drg', 'sc_hcc', 'sc_fraud'];"},
     'prebill', 'domain_verb', False),
    ('a declared verb nobody sends is False, not True',
     {'registry': "map['sc_claims'] = ['delete', 'therapy_accumulator'];",
      'app': 'function x(){ return 1; }'}, 'claims', 'verb_sent', False),
    ('a declared verb the client sends is True',
     {'registry': "map['sc_claims'] = ['delete', 'therapy_accumulator'];",
      'app': "scData('therapy_accumulator', 'sc_claims', {});"},
     'claims', 'verb_sent', True),
    ('server_named counts CODE mentions only',
     {'endpoint': "// sc_prebill is handled generically\nvar x = 1;"},
     'prebill', 'server_named', False),
    ('server_named is True when the endpoint really names it',
     {'endpoint': "if (resource === 'sc_claims') { validate(); }"},
     'claims', 'server_named', True),
]


def run_lock():
    fn = {name: f for name, _t, f, _d in SIGNALS}
    base = {'app': '', 'app_why': None, 'registry': '', 'registry_why': None,
            'endpoint': '', 'endpoint_why': None, 'endpoint_rel': 'api/sd-data.js',
            'tiers': '', 'tiers_why': None, 'prefix': 'sc', 'client': 'sc'}
    bad = []
    for name, over, panel, sig, expect in FIXTURES:
        ctx = dict(base)
        ctx.update(over)
        got, _ev = fn[sig](ctx, panel)
        if got is not expect:
            bad.append('%s -- %s expected %r, got %r' % (name, sig, expect, got))
    return bad


def main(argv):
    print('PANEL DEPTH -- criteria %s' % CRITERIA_VERSION)
    bad = run_lock()
    print('  fixture lock: %d/%d classify correctly'
          % (len(FIXTURES) - len(bad), len(FIXTURES)))
    if bad:
        print('  NOTHING REAL WAS JUDGED. The criteria are wrong before they '
              'reach any data:')
        for b in bad:
            print('    ' + b)
        return 2
    if '--lock-only' in argv:
        print('  --lock-only: the lock passed and nothing real was judged, '
              'deliberately.')
        return 0
    args = [a for a in argv if not a.startswith('--')]
    if len(args) < 2:
        print('  usage: python tools/panel_depth.py <app> <panel> [panel ...]')
        return 2
    app, panels = args[0], args[1:]
    ctx = build_ctx(app)
    print('')
    print('%s -- %d panel(s). SHALLOW 1-4 is what "the vocabulary is present" '
          'already meant; DEEP 5-9 is the part the audits deferred.'
          % (app, len(panels)))
    print('')
    hdr = '%-10s %-9s %-9s  %s' % ('panel', 'PRESENT', 'UNKNOWN', 'missing DEEP signals')
    print(hdr)
    print('-' * len(hdr))
    rows, unread = [], 0
    for p in panels:
        res = {}
        for name, tier, f, _d in SIGNALS:
            got, ev = f(ctx, p)
            res[name] = (got, ev, tier)
            if got is None:
                unread += 1
        present = len([1 for g, _e, _t in res.values() if g is True])
        unknown = len([1 for g, _e, _t in res.values() if g is None])
        missing_deep = [n for n, (g, _e, t) in res.items() if t == 'DEEP' and g is False]
        rows.append((p, present, unknown, res))
        print('%-10s %-9s %-9s  %s'
              % (p, '%d/%d' % (present, len(SIGNALS)), str(unknown),
                 ', '.join(missing_deep) or '-'))
    print('')
    print('EVIDENCE, one row per signal per panel -- every line names what it '
          'was read from, because a count that cannot say where it came from is '
          'how a keyword pass classified a ledger on five comment lines.')
    for p, _pr, _un, res in rows:
        print('  %s' % p)
        for name, tier, _f, desc in SIGNALS:
            got, ev, _t = res[name]
            mark = {True: 'yes', False: 'NO ', None: '???'}[got]
            print('    %-13s %-8s %s  [%s]' % (name, tier, mark, ev))
    print('')
    print('READ THIS BEFORE QUOTING ANY FIGURE ABOVE.')
    print('  * PRESENT and UNKNOWN are TWO NUMBERS and are never added. A panel')
    print('    at 4 present / 5 unknown and one at 4 present / 0 unknown are')
    print('    different findings and one figure hides which.')
    print('  * THIS DOES NOT MEASURE SUFFICIENCY AT SCALE, which is the')
    print('    question the audits actually deferred. It separates "a table and')
    print('    a form" from "a rule, a server that enforces it, and a test that')
    print('    drives it". That is strictly weaker and is not a substitute.')
    print('  * A DEEP signal reading NO is not a defect. Some panels correctly')
    print('    have no domain verb because there is no second fact to compute.')
    print('    The figure is a shape, not a score, and there is no threshold.')
    print('  * `suite` counts files that NAME the resource. A file can name it')
    print('    and assert nothing about it; this cannot see that.')
    return 1 if unread else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
