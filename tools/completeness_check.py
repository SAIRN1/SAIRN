"""Item 38 -- a rule that is DECLARED and then not applied everywhere it must be.

    python tools/completeness_check.py            # the report
    python tools/completeness_check.py --fixtures # the blind lock alone
    python tools/completeness_check.py --json

── WHAT THIS IS FOR, AND WHY IT IS THE PAIR OF ITEM 90 RATHER THAN A COPY ──
Item 90 makes a class of bug impossible to WRITE: parse once at the boundary
and the rest of the code cannot hold an unvalidated value. That works where the
boundary can be moved. IT CANNOT REACH legacy code that never had a boundary,
and it cannot reach external input BEFORE it is parsed.

This is the fallback detector for what is left: a rule that EXISTS, is written
down, and is then applied at some of its sites and not others. No type can
force that, because the sites are not a type -- they are a list somebody has to
remember.

── THREE SHAPES, EACH NARROWED BY A REAL FALSE POSITIVE ────────────────────

S1  DECLARED AND NEVER CONSULTED. A role gate, tier or domain constant declared
    in a file and referenced nowhere else in it. A rule that gates nothing is
    either dead or a gate somebody forgot to wire, and the two look identical
    from outside. FOUND A REAL ONE on its first run -- see the header of the
    report.

S2  CONSULTED IN ONE DIRECTION ONLY. A rule checked on a READ path and on no
    WRITE path (or the reverse). This is the shape of a real defect this
    platform already fixed: DNT_FINANCIAL_RESOURCES and DNT_FINANCIAL_ROLES
    were checked on the read branch of api/sd-data.js and NOWHERE on the write
    branch, so a provider could POST a payment it would then take 403 reading
    back. A role permitted to create a record it may not read is not a tier.

S3  EXHAUSTIVENESS OVER A DECLARED DOMAIN. A dispatch chain over a value whose
    full set of values is declared in the same file, with a member that reaches
    no arm and no `else`.

── S3 REPORTS ZERO ON THIS TREE, AND THAT IS A MEASURED ZERO ───────────────
Said here rather than left to be assumed, because a checker that finds nothing
and a checker that does not run look the same. S3 was calibrated against FOUR
real candidates and every one of them was a FALSE POSITIVE:

  api/_lib/roofing-agreements.js  RESCISSION_UNITS   -- `business_days` reaches
      a terminal `else`, and validateRule() refuses any unit outside the three,
      so the domain is closed and the else is exhaustive.
  api/_lib/wip-accounting.js      DRAW_STATUSES      -- `status === 'requested'
      || status === 'approved'` is a PREDICATE ("is it outstanding"), not a
      dispatch. draft, received and rejected are correctly not outstanding.
  api/_lib/roofing-warranties.js  WARRANTY_STATUSES  -- the three unhandled
      statuses fall through DELIBERATELY to the deadline computation below.
  api/_lib/roofing-safety.js      EQUIPMENT_STATUSES -- one member, terminal
      else.

Each narrowing below was paid for by one of those, which is why S3 is a chain
of at least two `else if` arms on ONE variable with NO terminal `else` -- not
"a member of a declared set with no comparison anywhere", which reported
fourteen files and would have been switched off the same day. This repo's own
record for a first draft that over-reports is exactly that.

REPORT-ONLY. Nothing here gates a push.
"""
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import dependency_graph as G                                     # noqa: E402

SEP = chr(92)

# A constant whose NAME says it is a rule rather than a value. Deliberately
# name-driven: the alternative is every uppercase constant in the tree, and a
# check that reports a lookup table as an unapplied rule is noise.
RULE_NAME = re.compile(r'(ROLES|TIERS?|STATUSES|TYPES|UNITS|VENUES|METHODS|STAGES|'
                       r'ALLOW|DENY|PERMIT|GATED|AUTHORITY|SCOPES)')
DECL_ARRAY = re.compile(r"const\s+([A-Z][A-Z0-9_]*)\s*=\s*\[\s*"
                        r"((?:'[a-z_][a-z0-9_]*'\s*,\s*)*'[a-z_][a-z0-9_]*')\s*\]")
DECL_ANY = re.compile(r'const\s+([A-Z][A-Z0-9_]{2,})\s*=\s*[\[{]')
IF_HEAD = re.compile(r"if\s*\(\s*([A-Za-z_$][\w$.]{0,40})\s*===\s*'([a-z_][a-z0-9_]*)'\s*\)")

# A read path and a write path, as this tree actually spells them.
READ = re.compile(r"action\s*===\s*'read'|\.get\(|GET\b")
WRITE = re.compile(r"action\s*===\s*'(write|delete|soft_delete|set_active)'")


# ── ACKNOWLEDGED, BY NAME AND WITH A REASON ───────────────────────────────
# One S3 candidate survives every narrowing and is still a FALSE POSITIVE,
# because the thing that makes it safe is CONTROL FLOW rather than syntax: the
# unhandled statuses fall through DELIBERATELY into the deadline computation
# below the chain, and `out.registration` is initialised before it. No regex
# can see that, and narrowing the shape further to exclude it would have
# excluded the real positives with it.
#
# So it is acknowledged BY NAME rather than silenced by a rule, the same shape
# report_only_checks.NOT_PROMOTED and docs/SPOF-REGISTER.md's ACCEPTED status
# already use. The count is PRINTED on every run: an acknowledgement nobody can
# see is a suppression.
#
# A new acknowledgement costs somebody a sentence. That is the price, and it is
# the right one -- the alternative is a checker whose only output is a finding
# everybody has learned to scroll past.
ACKNOWLEDGED = {
    ('S3', 'api/_lib/roofing-warranties.js', 'WARRANTY_STATUSES'):
        'READ 2026-09-14: not_registered, submitted and registration_rejected fall '
        'through the chain ON PURPOSE into the deadline computation below it, and '
        '`out.registration` is set to a real value before the chain runs. The chain '
        'is not a dispatch over the domain; it is an early exit for the two statuses '
        'that end the story.',
}


def js_files():
    out = []
    for dp, dn, fn in os.walk(os.path.join(REPO, 'api')):
        dn[:] = [d for d in dn if d not in ('node_modules', '.git')]
        for f in fn:
            if f.endswith('.js') and not f.endswith('.test.js'):
                out.append(os.path.join(dp, f))
    return sorted(out)


def s1_declared_never_consulted(body, path):
    """A rule declared and referenced nowhere else in its own file."""
    out = []
    for m in DECL_ANY.finditer(body):
        name = m.group(1)
        if not RULE_NAME.search(name):
            continue
        uses = len(re.findall(r'\b' + re.escape(name) + r'\b', body)) - 1
        if uses == 0:
            out.append({'shape': 'S1', 'file': path, 'rule': name,
                        'why': 'declared and consulted NOWHERE in its own file -- a rule '
                               'that gates nothing is either dead or a gate somebody '
                               'forgot to wire, and the two look identical from outside'})
    return out


def s2_one_direction_only(body, path):
    """A rule consulted on a read path and on no write path, or the reverse."""
    out = []
    if not (READ.search(body) and WRITE.search(body)):
        return out                       # no two directions in this file to be uneven about
    for m in DECL_ANY.finditer(body):
        name = m.group(1)
        if not RULE_NAME.search(name):
            continue
        on_read = on_write = 0
        for u in re.finditer(r'\b' + re.escape(name) + r'\b', body):
            if u.start() == m.start():
                continue
            ls = body.rfind(chr(10), 0, u.start()) + 1
            le = body.find(chr(10), u.end())
            line = body[ls:le if le > 0 else len(body)]
            if READ.search(line):
                on_read += 1
            if WRITE.search(line):
                on_write += 1
        if (on_read and not on_write) or (on_write and not on_read):
            out.append({'shape': 'S2', 'file': path, 'rule': name,
                        'why': 'consulted on the %s path and on no %s path -- the shape of '
                               'the real DNT_FINANCIAL_ROLES defect, where a provider could '
                               'POST a payment it would then take 403 reading back'
                               % ('read' if on_read else 'write',
                                  'write' if on_read else 'read')})
    return out


def s3_fall_through(body, path):
    """A dispatch chain over a declared domain with a member that reaches no arm
    and no terminal else. The two narrowings below are each paid for by a real
    false positive -- see the module docstring."""
    decls = {}
    for m in DECL_ARRAY.finditer(body):
        vals = set(re.findall(r"'([a-z_][a-z0-9_]*)'", m.group(2)))
        if len(vals) >= 3 and RULE_NAME.search(m.group(1)):
            decls[m.group(1)] = vals
    if not decls:
        return []
    out = []
    for m in IF_HEAD.finditer(body):
        var, arms, pos = m.group(1), [m.group(2)], m.end()
        while True:
            nxt = re.compile(r"\A[\s\S]{0,400}?\belse\s+if\s*\(\s*" + re.escape(var)
                             + r"\s*===\s*'([a-z_][a-z0-9_]*)'\s*\)").match(body[pos:pos + 600])
            if not nxt:
                break
            arms.append(nxt.group(1))
            pos += nxt.end()
        # ── WHICH LINE EXCLUDES WHICH FALSE POSITIVE, stated exactly, because
        # the first version of this comment credited two of them to the wrong
        # line -- and a guard that is believed to be doing work it is not is
        # how a redundant check survives and a real one gets deleted instead.
        #
        #   `status === 'a' || status === 'b'` (a PREDICATE -- "is this draw
        #   outstanding", api/_lib/wip-accounting.js DRAW_STATUSES) is excluded
        #   by IF_HEAD above: it matches only a BARE equality, so a disjunction
        #   never starts a chain at all.
        #
        #   A single-arm `if`, and any chain touching fewer than two members of
        #   a declared domain, is excluded by `len(hit) < 2` below. There is no
        #   separate arms-count guard: the first draft had one, and sabotaging
        #   it changed nothing because `len(hit) < 2` had already caught every
        #   case it claimed. It was deleted rather than left to look load-bearing.
        #
        #   One leftover member plus a terminal `else` is excluded immediately
        #   below (api/_lib/roofing-agreements.js RESCISSION_UNITS).
        #
        # A terminal `else` handles whatever is left, and one
        # unhandled member is exactly what an else is for.
        # roofing-agreements.js routes business_days there deliberately.
        has_else = bool(re.compile(r"\A[\s\S]{0,400}?\belse\s*\{").match(body[pos:pos + 600]))
        for name, vals in decls.items():
            hit = set(arms) & vals
            missing = sorted(vals - set(arms))
            if len(hit) < 2 or not missing:
                continue
            if has_else and len(missing) == 1:
                continue
            out.append({'shape': 'S3', 'file': path, 'rule': name, 'var': var,
                        'arms': sorted(hit), 'missing': missing,
                        'why': 'a dispatch chain on `%s` with no terminal else, and %d '
                               'declared value(s) reaching no arm at all' % (var, len(missing))})
    return out


# ── THE BLIND LOCK ────────────────────────────────────────────────────────
# Synthetic sources with hand-known answers, decided before the real tree was
# read, and every FALSE POSITIVE that calibrated S3 is kept as a fixture so the
# narrowing cannot be undone by accident.
FIXTURES = [
    # (name, source, shape, should_fire)
    ('S1 a rule declared and never used FIRES',
     "const MANAGEMENT_ROLES = { owner: true };\nconst BROAD_ROLES = { owner: true };\n"
     "if (BROAD_ROLES[r]) ok();", 'S1', True),
    ('S1 CONTROL: a rule that IS used stays quiet -- otherwise S1 reports every '
     'rule in the tree',
     "const BROAD_ROLES = { owner: true };\nif (BROAD_ROLES[r]) ok();", 'S1', False),
    ('S1 a constant whose name is not rule-shaped is not a rule',
     "const DEFAULT_LIMIT = { a: 1 };", 'S1', False),

    ('S2 a rule on the read path and no write path FIRES',
     "const FIN_ROLES = ['owner'];\n"
     "if (action === 'read' && FIN_ROLES.indexOf(role) === -1) deny();\n"
     "if (action === 'write') { save(); }", 'S2', True),
    ('S2 CONTROL: the same rule on BOTH paths stays quiet',
     "const FIN_ROLES = ['owner'];\n"
     "if (action === 'read' && FIN_ROLES.indexOf(role) === -1) deny();\n"
     "if (action === 'write' && FIN_ROLES.indexOf(role) === -1) deny();", 'S2', False),
    ('S2 a file with only ONE direction cannot be uneven and stays quiet',
     "const FIN_ROLES = ['owner'];\n"
     "if (action === 'read' && FIN_ROLES.indexOf(role) === -1) deny();", 'S2', False),

    ('S3 a chain with no terminal else and two unhandled members FIRES',
     "const JOB_STATUSES = ['draft', 'open', 'closed', 'void'];\n"
     "if (s === 'open') { a(); } else if (s === 'closed') { b(); }", 'S3', True),
    # THE FOUR NARROWINGS, each one a real false positive this tool produced
    # before it was narrowed. They are fixtures, not comments, so the narrowing
    # cannot be quietly undone.
    ('S3 NARROWING: a terminal else covers ONE remaining member '
     '(api/_lib/roofing-agreements.js RESCISSION_UNITS)',
     "const RESCISSION_UNITS = ['business_days', 'calendar_days', 'hours'];\n"
     "if (u === 'hours') { a(); } else if (u === 'calendar_days') { b(); } else { c(); }",
     'S3', False),
    ('S3 NARROWING: a single if with || is a PREDICATE, not a dispatch '
     '(api/_lib/wip-accounting.js DRAW_STATUSES)',
     "const DRAW_STATUSES = ['draft', 'requested', 'approved', 'received', 'rejected'];\n"
     "if (status === 'requested' || status === 'approved') { outstanding(); }", 'S3', False),
    ('S3 CONTROL: a terminal else does NOT excuse two unhandled members -- an '
     'else is for the leftover, not for half the domain',
     "const JOB_STATUSES = ['draft', 'open', 'closed', 'void'];\n"
     "if (s === 'open') { a(); } else if (s === 'closed') { b(); } else { c(); }", 'S3', True),
    ('S3 NARROWING: a SINGLE arm is a test, not a dispatch -- reporting it would '
     'flag every equality comparison in the tree',
     "const JOB_STATUSES = ['draft', 'open', 'closed', 'void'];" + chr(10) +
     "if (s === 'open') { a(); }", 'S3', False),
    ('S3 CONTROL: the SAME domain with a second arm and no else DOES fire, so the '
     'single-arm rule is not just switching the shape off',
     "const JOB_STATUSES = ['draft', 'open', 'closed', 'void'];" + chr(10) +
     "if (s === 'open') { a(); } else if (s === 'closed') { b(); }", 'S3', True),
    ('S3 a domain of fewer than three values is not a domain worth dispatching on',
     "const PAIR_TYPES = ['a', 'b'];\nif (t === 'a') { x(); } else if (t === 'b') { y(); }",
     'S3', False),
]

SHAPES = {'S1': s1_declared_never_consulted,
          'S2': s2_one_direction_only,
          'S3': s3_fall_through}


def run_fixtures():
    bad = []
    for name, src, shape, want in FIXTURES:
        got = bool(SHAPES[shape](G.strip_js(src), '<fixture>'))
        if got != want:
            bad.append((name, want, got))
    return bad


def analyse():
    findings = []
    for p in js_files():
        rel = os.path.relpath(p, REPO).replace(SEP, '/')
        body = G.strip_js(io.open(p, encoding='utf-8', errors='replace').read())
        for fn in (s1_declared_never_consulted, s2_one_direction_only, s3_fall_through):
            findings.extend(fn(body, rel))
    return findings


def main(argv):
    bad = run_fixtures()
    print('COMPLETENESS -- item 38: a rule declared, then not applied everywhere')
    if bad:
        print('  !! THE SHAPES FAILED THEIR OWN FIXTURES. NOTHING WAS ANALYSED.')
        for name, want, got in bad:
            print('     wanted %r, got %r -- %s' % (want, got, name))
        return 2
    print('  blind lock: %d synthetic sources classify as written, including the four'
          % len(FIXTURES))
    print('              narrowings each paid for by a real false positive.')
    if '--fixtures' in argv:
        return 0

    findings = analyse()
    acked = [f for f in findings
             if (f['shape'], f['file'], f['rule']) in ACKNOWLEDGED]
    findings = [f for f in findings
                if (f['shape'], f['file'], f['rule']) not in ACKNOWLEDGED]
    if '--json' in argv:
        print(json.dumps(findings, indent=2, sort_keys=True))
        return 0

    by = {}
    for f in findings:
        by.setdefault(f['shape'], []).append(f)
    for shape, label in (('S1', 'DECLARED AND NEVER CONSULTED'),
                         ('S2', 'CONSULTED IN ONE DIRECTION ONLY'),
                         ('S3', 'EXHAUSTIVENESS OVER A DECLARED DOMAIN')):
        rows = by.get(shape, [])
        print()
        print('  %s -- %s: %d' % (shape, label, len(rows)))
        if not rows:
            # A MEASURED ZERO, NOT A SILENCE. A checker that finds nothing and a
            # checker that did not run look identical from outside, and this
            # platform has shipped the second while reading it as the first.
            print('     none. This shape RAN over %d files and found nothing --'
                  % len(js_files()))
            print('     a measured zero, not a check that did not run.')
            continue
        for r in rows:
            print('     %s  %s' % (r['file'], r['rule']))
            print('        %s' % r['why'])
            if r.get('missing'):
                print('        arms: %s   unreachable: %s'
                      % (', '.join(r['arms']), ', '.join(r['missing'])))
    print()
    print('  ACKNOWLEDGED FALSE POSITIVES: %d -- printed every run, because an'
          % len(acked))
    print('  acknowledgement nobody can see is a suppression:')
    for f in acked:
        print('     %s  %s  (%s)' % (f['file'], f['rule'], f['shape']))
        print('        %s' % ACKNOWLEDGED[(f['shape'], f['file'], f['rule'])])
    stale = [k for k in ACKNOWLEDGED
             if not any((f['shape'], f['file'], f['rule']) == k for f in acked)]
    if stale:
        # An acknowledgement for a finding that no longer occurs is an excuse
        # outliving the thing it excused, which is how a suppression list
        # silently grows past what anyone checked.
        print('  STALE ACKNOWLEDGEMENT(S) -- the finding no longer occurs, remove them:')
        for k in stale:
            print('     %s' % (k,))
    print()
    print('  REPORT ONLY -- nothing here gates a push. Every finding is a POINTER')
    print('  to read the file: a rule can legitimately apply in one direction, and')
    print('  this cannot read intent, only sites.')
    return 1 if findings else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
