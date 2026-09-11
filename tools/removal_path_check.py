"""Which registered resources can the PRODUCT remove a record from, and which cannot.

    python tools/removal_path_check.py             # report, exit 1 on an unbaselined stuck resource
    python tools/removal_path_check.py --full      # every resource, classified
    python tools/removal_path_check.py --quiet     # exit code only

WHY THIS EXISTS. Every live write-path verification on this platform ends in a
hand-written `delete from`, and there are now 15+ such `sql/*_cleanup.sql`
files across 11 apps, *still growing*. The open-work row that counts them
treats each as a chore. It is not a chore, it is a symptom: **the API mostly
has no delete path at all**, so a row the product can create is a row only
Michael can remove, by hand, in the SQL editor.

MEASURED 2026-09-10, derived from `api/_resources/index.js` -- the registry the
API itself dispatches on, and the same source `cleanup_residue_check.py` had to
learn to use instead of the licence seed row:

  389 registered resources
   50 declare a removal verb (`delete` or `soft_delete`) in EXTRA_ACTIONS
  339 declare none

THE ONE MITIGATION THAT WOULD HAVE MADE 339 A SOFT NUMBER IS NOT THERE, and it
was the first thing checked rather than assumed. If these were *collection
rows* -- one row per licence holding a JSON array -- then removing an item would
be an ordinary write and the absence of a delete verb would barely matter. They
are not. The dominant write is
`POST <table>?on_conflict=license_hash,<id_col>`, one row per RECORD, upserted
by (licence, id): 117 such call sites against **three** single-row collection
upserts on the whole platform (`msb_sale_hours`, `sd_public_shop`,
`sd_shared_knowledge`). Writing the collection without an item does nothing --
each write touches only its own keyed row. So for a keyed resource with no
removal verb, a record genuinely cannot be removed through the product.

WHAT IS A LEGITIMATE REASON, AND IT IS A REAL ONE. Plenty of these are
**append-only by design**: signed agreements, claim photo evidence, audit logs,
credential history. For those the absence of a delete is the correct design and
needs a written reason, not a fix. 46 resources are labelled APPEND-ONLY in
their own registry comment, and that label is read here rather than re-decided.

HOW THE SHAPE IS DERIVED, and where it stops. For each resource this reads
`api/sd-data.js` -- the map that registers it, or its `resource === '<name>'`
branch -- and looks at the write call in that region:

  keyed        on_conflict=license_hash,<col>   one row per record
  single-row   on_conflict=license_hash         one row per licence, a collection
  insert-only  POST with no on_conflict         appends, never replaces
  UNRESOLVED   none of the above found

**UNRESOLVED IS REPORTED AS UNRESOLVED AND IS NOT A FINDING AND NOT A PASS.**
The resource name and the table name are not always the same -- `golf_zones`
writes to `grd_golf_zones` -- and some branches build the table from a
variable. A first version of this derivation called 73 resources UNKNOWN purely
because it matched table literals, which is the kind of number that gets quoted
as a defect count. Anything this cannot read, it says it cannot read.

THE BASELINE IS THE POINT, and it is copied from a precedent in this repo
rather than invented. `tools/removal_path_baseline.json` grandfathers every
stuck resource that existed on 2026-09-10. A checker that simply reported 339
would sit at exit 1 forever and could never gate anything -- which is exactly
the failure `preauth_oracle_check.py`'s own row already names about itself. So
this fails only on a resource that is **keyed, has no removal verb, and is not
in the baseline**: i.e. a NEW one. Same shape and same intent as
`employee_auth_guard_check.py`'s explicit pre-2026-08-29 list, which its own
header says is *"not fixed, only visible, and the list is meant to be burned
down rather than added to."*

IT REPORTS AND NEVER EDITS. Whether a resource SHOULD be deletable is a product
decision -- a dental practice must be able to delete a mistyped appointment; it
must not be able to delete a signed financial agreement. A tool that auto-filed
these would be guessing at exactly the part that matters.
"""
import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE = os.path.join(REPO, 'tools', 'removal_path_baseline.json')
REMOVAL_VERBS = ('delete', 'soft_delete')


def read(path):
    with io.open(path, encoding='utf-8', errors='replace') as fh:
        return fh.read()


def registry():
    """RESOURCE_NAMES, OWNER_BY_RESOURCE and EXTRA_ACTIONS, from the real registry.

    Read by EXECUTING the registry rather than parsing it, because that is what
    `api/sd-data.js` does -- `index.js` merges 17 per-app modules and refuses to
    load on a duplicate, and re-implementing that merge here would be a second
    source of truth for the one thing this must not be wrong about.
    """
    src = ("const r = require('./api/_resources/index.js');"
           "process.stdout.write(JSON.stringify({names: r.RESOURCE_NAMES,"
           " owner: r.OWNER_BY_RESOURCE, extra: r.EXTRA_ACTIONS}));")
    p = subprocess.run(['node', '-e', src], cwd=REPO, capture_output=True,
                       text=True)
    if p.returncode != 0 or not p.stdout.strip():
        raise RuntimeError('could not load api/_resources/index.js: %s'
                           % (p.stderr or '').strip()[:300])
    return json.loads(p.stdout)


MAP_RE = re.compile(r'const\s+([A-Z][A-Z0-9_]*_RESOURCES)\s*=\s*\{(.*?)\};', re.S)
PAIR_RE = re.compile(r"([a-z][a-z0-9_]*)\s*:\s*'([a-z_]+)'")
OBJ_PAIR_RE = re.compile(r"([a-z][a-z0-9_]*)\s*:\s*\{\s*idCol:\s*'([a-z_]+)'")
KEYED_Q = re.compile(r"on_conflict=license_hash,\s*'?\s*\+?\s*([a-zA-Z_]+)?")
SINGLE_Q = re.compile(r"on_conflict=license_hash'")


def shapes(api):
    """resource -> (shape, why) for everything derivable from sd-data.js."""
    out = {}

    # (a) the generic per-app maps: `{ res: 'res_id', ... }` and the newer
    #     `{ res: { idCol: 'res_id', label: '...' } }` form. Both are KEYED --
    #     the branch they gate upserts on (license_hash, idCol).
    for m in MAP_RE.finditer(api):
        name, body = m.group(1), m.group(2)
        region = api[m.end():m.end() + 6000]
        keyed = bool(KEYED_Q.search(region)) or 'on_conflict=' in region
        for res, idcol in PAIR_RE.findall(body) + OBJ_PAIR_RE.findall(body):
            if res in ('idCol', 'label'):
                continue
            out.setdefault(res, ('keyed' if keyed else 'UNRESOLVED',
                                 'in %s, id column %s' % (name, idcol)))

    # (b) bespoke branches, found by the resource's own dispatch line. The
    #     TABLE name is frequently not the resource name (golf_zones ->
    #     grd_golf_zones), so this anchors on the branch, never on the table.
    for m in re.finditer(r"resource === '([a-z][a-z0-9_]*)'", api):
        res = m.group(1)
        if res in out:
            continue
        region = api[m.start():m.start() + 2500]
        if SINGLE_Q.search(region):
            out[res] = ('single-row', 'one row per licence -- a write replaces '
                                      'the whole collection, so removal is a write')
        elif 'on_conflict=license_hash,' in region:
            out[res] = ('keyed', 'upserts on (license_hash, id)')
        elif re.search(r"method:\s*'POST'", region):
            out[res] = ('insert-only', 'POST with no on_conflict -- appends, '
                                       'never replaces')
        elif re.search(r"method:\s*'PATCH'", region):
            out[res] = ('keyed', 'PATCH by id')
    return out


def append_only_labels():
    """Resources their own registry comment calls APPEND-ONLY.

    The label is READ, not re-decided -- but it is read carefully, and the
    careless version was wrong in the direction that matters.

    A comment block in these files often covers SEVERAL resources and
    distinguishes between them. SAIRNroofing's is the case that caught it:

        // ... rf_claims is a MUTABLE claim record (evolves over a 45-90 day
        // lifecycle); rf_claim_photos is APPEND-ONLY tagged evidence ...
          'rf_claims',
          'rf_claim_photos',

    Attributing the block wholesale labelled `rf_claims` -- a money record its
    own comment calls MUTABLE -- as append-only, which would have SILENTLY
    EXEMPTED it from this check. A false exemption is worse than a false
    finding: one gets read and argued with, the other never appears.

    So a multi-resource block only labels the names that appear in a CLAUSE
    containing "append-only". A single-resource block labels its one name.

    NAME THE RESOURCE IN THE SENTENCE, and this is the practical advice rather
    than a detail -- it cost a round trip on 2026-09-11. A comment block that
    LOOKS single-resource usually is not: the resource lists in these files run
    on for dozens of names with no further comment, so the block covers every
    name below it until the next comment. Writing
    "`dnt_payments` is APPEND-ONLY BY DESIGN because..." labels it;
    "APPEND-ONLY BY DESIGN because..." directly above the same line does not.
    That is deliberate -- the strictness is what stopped a MUTABLE money record
    inheriting its neighbour's exemption -- and naming the resource you are
    describing is better documentation anyway.
    """
    out, d = {}, os.path.join(REPO, 'api', '_resources')
    for f in sorted(os.listdir(d)):
        if not f.endswith('.js') or f == 'index.js' or '.test.' in f:
            continue
        comment, group = [], []

        def flush(comment, group):
            blob = ' '.join(comment)
            low = blob.lower()
            if not group or ('append-only' not in low and 'append only' not in low):
                return
            if len(group) == 1:
                out[group[0]] = blob[:220]
                return
            # Several names under one comment: attribute clause by clause.
            for clause in re.split(r'[;.]', blob):
                cl = clause.lower()
                if 'append-only' not in cl and 'append only' not in cl:
                    continue
                for name in group:
                    if name in cl:
                        out[name] = clause.strip()[:220]

        for line in read(os.path.join(d, f)).split('\n'):
            s = line.strip()
            if s.startswith('//'):
                if group:          # a comment after names starts a new block
                    flush(comment, group)
                    comment, group = [], []
                comment.append(s.lstrip('/ ').rstrip())
                continue
            m = re.match(r"^'([a-z][a-z0-9_]*)',?$", s)
            if m:
                group.append(m.group(1))
            elif s:
                flush(comment, group)
                comment, group = [], []
        flush(comment, group)
    return out


TIER_ROW = re.compile(r'^\|\s*`([a-z][a-z0-9_]*)`\s*\|\s*\*{0,2}([ABC])\*{0,2}\s*\|')


def tiers():
    """resource -> criticality tier, from docs/CRITICALITY-TIERS.md.

    READ, not re-decided. That register is hand-verified per resource and
    derived-checked by `tools/criticality_tier_check.py`; a second opinion on
    the tier computed here would be a second source of truth for the judgement
    that took two stages of work.

    It covers 382 resources against this tool's 389. The seven are the `shared`
    registry -- `employees`, `employee_profile`, `memory`, `profile`,
    `render_usage`, `slabs`, `exec_context` -- which that document scopes per
    app and so does not tier. They come back UNTIERED here rather than being
    quietly folded into a tier nobody assigned them.
    """
    path = os.path.join(REPO, 'docs', 'CRITICALITY-TIERS.md')
    if not os.path.exists(path):
        return {}
    out = {}
    for line in read(path).split('\n'):
        m = TIER_ROW.match(line.strip())
        if m:
            out.setdefault(m.group(1), m.group(2))
    return out


def classify():
    reg = registry()
    tier = tiers()
    api = read(os.path.join(REPO, 'api', 'sd-data.js'))
    sh = shapes(api)
    ao = append_only_labels()
    rows = []
    for name in sorted(reg['names']):
        verbs = reg['extra'].get(name) or []
        removal = next((v for v in verbs if v in REMOVAL_VERBS), None)
        shape, why = sh.get(name, ('UNRESOLVED', 'no map entry and no '
                                                 "resource === '%s' branch found"
                                                 % name))
        rows.append({
            'resource': name,
            'app': reg['owner'].get(name, '?'),
            'shape': shape,
            'why': why,
            'removal': removal,
            'append_only': name in ao,
            'append_only_note': ao.get(name, ''),
            'tier': tier.get(name, 'UNTIERED'),
        })
    return rows


def burn_down(rows, stuck):
    """The stuck set ordered by consequence, not by app size.

    The open-work row asks for the burn-down to be ordered by consequence.
    Crossing the stuck set with `docs/CRITICALITY-TIERS.md` is DERIVATION, not
    a product decision -- it says which of these matter most to fix, and says
    nothing about whether any of them SHOULD become deletable, which is exactly
    the judgement this tool refuses to make.

    A Tier A resource with no removal path is the sharp case: money moves
    wrongly, a regulated record is corrupted, or authentication is bypassed --
    and the wrong record cannot be taken back through the product.
    """
    order = {'A': 0, 'B': 1, 'C': 2, 'UNTIERED': 3}
    return sorted(stuck, key=lambda r: (order.get(r['tier'], 9), r['app'],
                                        r['resource']))


def main(argv):
    quiet, full = '--quiet' in argv, '--full' in argv
    burn = '--burn-down' in argv
    rows = classify()
    baseline = {}
    if os.path.exists(BASELINE):
        baseline = json.loads(read(BASELINE)).get('grandfathered', {})

    # THE VERDICT DELIBERATELY DOES NOT DEPEND ON THE DERIVED SHAPE, and that
    # is a correction to this tool's own first version. Shape came out
    # UNRESOLVED for 87 resources -- `api/sd-data.js` dispatches through at
    # least four styles (a name->idCol map, a name->{idCol,label} map, a
    # `resource === 'x'` branch, and `name: true` behaviour sets) and the table
    # name is often not the resource name. Gating on shape meant 87 resources
    # got no verdict at all for a reason that is about this parser, not about
    # the product.
    #
    # So the gate is the AUTHORITATIVE fact -- whether the registry declares a
    # removal verb -- and shape is supporting evidence. Two shapes are excluded
    # because they genuinely need no delete verb, and both are read rather than
    # guessed:
    #   single-row  -- one row per licence; a write replaces the whole
    #                  collection, so removing an item IS a write. Exactly
    #                  three on the platform, and the `on_conflict=license_hash`
    #                  literal that proves it is unambiguous.
    #   append-only -- the resource's own registry comment says so.
    stuck = [r for r in rows
             if not r['removal'] and r['shape'] != 'single-row'
             and not r['append_only']]
    unresolved = [r for r in rows if r['shape'] == 'UNRESOLVED' and not r['removal']]
    findings = [r for r in stuck if r['resource'] not in baseline]

    if not quiet:
        print('removal path check')
        print('  registered resources            : %d' % len(rows))
        print('  declare delete or soft_delete   : %d'
              % sum(1 for r in rows if r['removal']))
        for label in ('keyed', 'single-row', 'insert-only', 'UNRESOLVED'):
            n = sum(1 for r in rows if r['shape'] == label)
            print('  shape %-24s  : %d' % (label, n))
        print('  append-only by their own registry comment: %d'
              % sum(1 for r in rows if r['append_only']))
        print('  NO REMOVAL PATH (excl. single-row and append-only): %d'
              % len(stuck))
        print('    grandfathered in the baseline : %d'
              % sum(1 for r in stuck if r['resource'] in baseline))
        if unresolved:
            print('  shape UNRESOLVED and no removal verb: %d -- the SHAPE '
                  'could not be read; these are still judged on their removal '
                  'verb, which is authoritative' % len(unresolved))
        from collections import Counter
        tc = Counter(r['tier'] for r in stuck)
        print('  by criticality tier            : %s'
              % ', '.join('%s=%d' % (t, tc[t])
                          for t in ('A', 'B', 'C', 'UNTIERED') if tc[t]))
        if full:
            print('\n--- every resource ---')
            for r in rows:
                print('  %-16s %-30s %-12s %-11s %-9s %s'
                      % (r['app'], r['resource'], r['shape'],
                         r['removal'] or '-', r['tier'],
                         'append-only' if r['append_only'] else ''))
        if burn:
            print('\n--- BURN-DOWN ORDER: no removal path, by consequence ---')
            print('    Tier A first. This says which matter most to FIX; it '
                  'says nothing\n    about whether any of them SHOULD become '
                  'deletable.')
            last = None
            for r in burn_down(rows, stuck):
                if r['tier'] != last:
                    print('\n  == Tier %s (%d) ==' % (r['tier'], tc[r['tier']]))
                    last = r['tier']
                print('    %-16s %s' % (r['app'], r['resource']))
        if findings:
            print('\n%d FINDING(S) -- keyed, no removal path, and NOT in the '
                  'baseline:' % len(findings))
            for r in findings:
                print('  - %s (%s) %s' % (r['resource'], r['app'], r['why']))
            print('\nA record written to one of these cannot be removed through '
                  'the product -- only by hand in the SQL editor, which is what '
                  'the 15+ sql/*_cleanup.sql files are. Decide which it is and '
                  'say so: give it a removal verb, or add it to '
                  'tools/removal_path_baseline.json with a REASON. "Append-only '
                  'by design" is a real reason; "nobody has needed it yet" is a '
                  'real reason too, and both beat silence.')
        else:
            print('  CLEAN -- every keyed resource with no removal path is '
                  'accounted for in the baseline.')
    return 1 if findings else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
