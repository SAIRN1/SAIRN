"""Generate docs/spec/MCRoleGates.{tla,cfg} from the REAL role sets.

    python tools/role_gate_mc_config.py          # write them
    python tools/role_gate_mc_config.py --check  # do they match the repo?

Exit 0  written, or (with --check) the committed files match what this would
        generate right now
Exit 1  --check found drift -- the apps moved and the model did not
Exit 2  COULD NOT RUN -- node is absent, or a module could not be read.
        Never folded into 0: an empty instance would model-check clean.

── WHY A GENERATOR AND NOT A HAND-WRITTEN MODEL ────────────────────────────
The constants are the whole value of the run. A model checked against invented
role sets proves something about the invented sets. These are read by REQUIRING
each api/*-auth.js -- the same source tools/role_gate_invariants.js reads -- so
the day an app's roles move, `--check` says the model is stale instead of the
model quietly continuing to pass about a platform that no longer exists.

── WHERE THE SETS COME FROM, AND THE TRAP IN READING THEM ──────────────────
Three provenances, kept apart deliberately:

  exported   the module says so itself via module.exports
  internal   declared as a top-level `const` and never exported. FOUR apps do
             this and an earlier version of this generator missed all four,
             reading only module.exports and concluding that 10 of 16 apps had
             no MANAGEMENT_ROLES. They have one; it was not exported.
  absent     the app genuinely has no such concept

THE ANCHOR IS `^const NAME = ` AT LINE START, and that is not fussiness.
`sb-auth.js`, `grd-auth.js`, `law-auth.js` and `scp-auth.js` each contain the
text MANAGEMENT_ROLES inside a comment reading "This app has no
MANAGEMENT_ROLES concept, and inventing one to serve a credential panel would
be a new authorisation tier introduced as a side effect of an unrelated
change." An unanchored scraper reads that as a declaration and invents exactly
the tier the comment refuses.

── WHY THE INSTANCE IS TEN APPS AND NOT SIXTEEN ────────────────────────────
Six apps have NO management concept: sairngrounds, sairnlaw, sairnbiz,
sairncode, sairnscape, stonedesk. The spec's Management-related invariants
(I3, I4, I5) cannot be stated for them without supplying a Management set, and
supplying one would either invent an authorisation tier or set it equal to
Provisioning -- which makes ProvisioningIsManagement TRUE BY CONSTRUCTION and
buys a green that means nothing.

So they are EXCLUDED and the exclusion is printed on every run. That is the
same distinction role_gate_invariants.js draws when it reports checks as
not-checkable rather than passing: a bound, not a pass.
"""

import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = os.path.join(ROOT, 'docs', 'spec')

# Read the modules in node, because the sets must be the ones the code would
# actually use -- executing beats parsing, and role_gate_invariants.js made the
# same call for the same reason.
READER = r'''
const fs=require('fs'), path=require('path'), vm=require('vm');
// With `node -e SCRIPT -- ROOT`, argv[0] is the node binary and argv[1] is
// the first argument after --. There is no script path in the list.
const ROOT=process.argv[1];
process.env.SUPABASE_URL=process.env.SUPABASE_URL||'https://fake.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY=process.env.SUPABASE_SERVICE_ROLE_KEY||'k';
process.env.SD_AUTH_SECRET=process.env.SD_AUTH_SECRET||'test-secret-do-not-use-in-prod';
const auth=require(path.join(ROOT,'api/_lib/auth.js'));
const RBA=auth.ROLES_BY_APP||{};
function internal(src,name){
  const m=new RegExp('^const '+name+' = (.+?);\\s*$','m').exec(src);
  if(!m) return null;
  try{ return vm.runInNewContext('('+m[1]+')'); }catch(e){ return null; }
}
const out={};
for(const f of fs.readdirSync(path.join(ROOT,'api')).filter(f=>/^[a-z-]+-auth\.js$/.test(f))){
  let m; try{ m=require(path.join(ROOT,'api',f)); }catch(e){ m={}; }
  const src=fs.readFileSync(path.join(ROOT,'api',f),'utf8');
  const app=(src.match(/^const APP = '([a-z]+)'/m)||[])[1];
  if(!app) continue;
  const pick=(exp,name)=>exp?{v:exp,from:'exported'}
    :(()=>{const i=internal(src,name);return i?{v:i,from:'internal'}:{v:null,from:'absent'};})();
  out[app]={
    provisioning:pick(m.PROVISIONING_ROLES,'PROVISIONING_ROLES'),
    management:pick(m.MANAGEMENT_ROLES,'MANAGEMENT_ROLES'),
    authenticated:pick(m.AUTHENTICATED_ROLES,'AUTHENTICATED_ROLES'),
    broadRead:pick(m.BROAD_READ_ROLES,'BROAD_READ_ROLES'),
    vocabulary:RBA[app]||null};
}
process.stdout.write(JSON.stringify(out));
'''

C = chr(92) + '*'          # a TLA+ comment marker, built not escaped


def members(v):
    """A role set is written either as an array or as a {role: true} map."""
    if v is None:
        return None
    if isinstance(v, dict):
        return sorted(k for k, on in v.items() if on)
    return sorted(v)


def mv(x):
    # A TLA+ model value must be an identifier; ten real role names carry dots
    # (post.govern, finance.write, ...). Cosmetic, and printed on every run.
    return x.replace('.', '_').replace('-', '_')


def tset(xs):
    return '{' + ', '.join(mv(x) for x in xs) + '}'


def tfun(pairs, dom):
    # CASE, not [k |-> v]. The latter is a RECORD whose keys are strings, so
    # applying it to a model value fails with "attempted to apply record to a
    # non-string value" -- which it did, before this was corrected.
    parts = ['a = %s -> %s' % (mv(k), tset(v)) for k, v in pairs]
    return '[a \\in %s |->\n    CASE ' % dom + '\n      [] '.join(parts) + ']'


def read_sets():
    p = subprocess.run(['node', '-e', READER, '--', ROOT], cwd=ROOT,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    if p.returncode != 0 or not p.stdout.strip():
        raise RuntimeError((p.stderr or 'node produced nothing').strip()[:300])
    return json.loads(p.stdout)


def build(raw):
    apps, excluded = [], []
    for a in sorted(raw):
        v = raw[a]
        prov = members(v['provisioning']['v'])
        mgmt = members(v['management']['v'])
        voc = members(v['vocabulary'])
        if prov and mgmt and voc:
            apps.append((a, prov, mgmt,
                         members(v['authenticated']['v']),
                         members(v['broadRead']['v']), voc,
                         v['management']['from']))
        else:
            missing = [n for n, got in (('provisioning', prov),
                                        ('management', mgmt),
                                        ('vocabulary', voc)) if not got]
            excluded.append((a, ', '.join(missing)))

    roles = sorted({r for x in apps for r in x[1] + x[2] + (x[3] or []) + x[5]})
    names = [x[0] for x in apps]
    stated = [x[0] for x in apps if x[3]]
    vals = {
        'MCApps': tset(names),
        'MCRoles': tset(roles),
        'MCEmployees': tset(['e1', 'e2']),
        'MCProvisioning': tfun([(x[0], x[1]) for x in apps], 'MCApps'),
        'MCManagement': tfun([(x[0], x[2]) for x in apps], 'MCApps'),
        'MCAuthenticated': tfun([(x[0], x[3] or x[5]) for x in apps], 'MCApps'),
        'MCBroadRead': tfun([(x[0], x[4] or x[5]) for x in apps], 'MCApps'),
        'MCVocabulary': tfun([(x[0], x[5]) for x in apps], 'MCApps'),
        'MCStatedAuthenticated': tset(stated),
    }
    ids = ['NoApp'] + sorted(
        set(re.findall(r'\b[A-Za-z_][A-Za-z0-9_]*\b', ' '.join(vals.values())))
        - {'a', 'in', 'CASE', 'MCApps'})
    return apps, excluded, roles, vals, ids


def render(apps, excluded, roles, vals, ids):
    head = [
        'GENERATED by tools/role_gate_mc_config.py -- do not hand-edit.',
        'Regenerate after any change to an app\'s role sets; --check reports drift.',
        '',
        'TLC cannot take a function literal in a .cfg, so the constants live here',
        'as OPERATORS and the .cfg SUBSTITUTES them. RoleGates.tla is untouched by',
        'the act of checking it.',
        '',
        'THE VALUES ARE REAL -- read by requiring each api/*-auth.js and taking the',
        'set the code would use, exported or internal. Not retyped.',
        '',
        'THIS INSTANCE IS %d OF 16 APPS, and the other six are a BOUND, not a pass:'
        % len(apps),
    ]
    for a, why in excluded:
        head.append('    %-16s no %s' % (a, why))
    head += [
        '',
        'Those six have NO management concept -- four of them say so in as many',
        'words, and add that inventing one "would be a new authorisation tier',
        'introduced as a side effect of an unrelated change". Supplying one here',
        'to widen the instance would either invent that tier or set Management =',
        'Provisioning, which makes ProvisioningIsManagement true BY CONSTRUCTION',
        'and buys a green that means nothing.',
        '',
        'Role names carrying a dot are renamed with underscores because a model',
        'value must be an identifier. No semantic content:',
    ]
    for r in sorted(x for x in roles if mv(x) != x):
        head.append('    %-22s -> %s' % (r, mv(r)))

    L = ['---- MODULE MCRoleGates ----']
    L += [(C + ' ' + t).rstrip() for t in head]
    L += ['EXTENDS RoleGates', '', C + ' Declared so TLC treats these as MODEL '
          'VALUES; the .cfg assigns each to itself.', 'CONSTANTS']
    for i in range(0, len(ids), 6):
        L.append('    ' + ', '.join(ids[i:i + 6]) + (',' if i + 6 < len(ids) else ''))
    L.append('')
    for k in ('MCApps', 'MCRoles', 'MCEmployees', 'MCProvisioning',
              'MCManagement', 'MCAuthenticated', 'MCBroadRead', 'MCVocabulary',
              'MCStatedAuthenticated'):
        L += ['%s == %s' % (k, vals[k]), '']
    L.append('====')

    G = [C + ' GENERATED -- values live in MCRoleGates.tla.',
         'SPECIFICATION Spec', 'INVARIANT Safety', 'CONSTANTS']
    for n in ('Apps', 'Roles', 'Employees', 'Provisioning', 'Management',
              'Authenticated', 'BroadRead', 'Vocabulary', 'StatedAuthenticated'):
        G.append('    %s <- MC%s' % (n, n))
    for i in ids:
        G.append('    %s = %s' % (i, i))
    return '\n'.join(L) + '\n', '\n'.join(G) + '\n'


def main(argv):
    try:
        raw = read_sets()
    except Exception as e:
        print('COULD NOT RUN -- the auth modules could not be read: %s' % e)
        return 2
    apps, excluded, roles, vals, ids = build(raw)
    if not apps:
        print('COULD NOT RUN -- no app yielded a complete set. An empty '
              'instance model-checks clean and would mean nothing.')
        return 2
    tla, cfg = render(apps, excluded, roles, vals, ids)
    tp = os.path.join(SPEC, 'MCRoleGates.tla')
    cp = os.path.join(SPEC, 'MCRoleGates.cfg')

    if '--check' in argv:
        drift = []
        for path, want in ((tp, tla), (cp, cfg)):
            got = (open(path, encoding='utf-8', newline='').read()
                   if os.path.isfile(path) else None)
            if got != want:
                drift.append(os.path.basename(path))
        if drift:
            print('DRIFT: %s no longer match the apps. Regenerate:' % ', '.join(drift))
            print('    python tools/role_gate_mc_config.py')
            return 1
        print('OK: the model matches the role sets the apps export today.')
        return 0

    open(tp, 'w', encoding='utf-8', newline='\n').write(tla)
    open(cp, 'w', encoding='utf-8', newline='\n').write(cfg)
    print('wrote %s and .cfg' % os.path.basename(tp))
    print('  modelled : %d apps' % len(apps))
    by = {}
    for x in apps:
        by[x[6]] = by.get(x[6], 0) + 1
    print('  MANAGEMENT_ROLES provenance: %s'
          % ', '.join('%s %d' % (k, v) for k, v in sorted(by.items())))
    print('  excluded : %d -- %s' % (len(excluded),
                                     ', '.join(a for a, _ in excluded)))
    print('  roles    : %d' % len(roles))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
