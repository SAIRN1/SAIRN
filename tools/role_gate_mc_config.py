# OWNER-INTENDED BARE-RUN WRITER. A bare run of this tool WRITES, and that is
# its interface rather than a defect: see tools/bare_run_writers.py for the
# path it writes and why. tools/bare_run_write_check.py reads that list and
# does not flag the tools on it. If this tool stops being a generator, take it
# off the list in the same change -- an allowlist nobody re-derives is how a
# real defect hides inside a convention.
"""Generate docs/spec/MCRoleGates.{tla,cfg} from the REAL role sets.

    python tools/role_gate_mc_config.py             # write them
    python tools/role_gate_mc_config.py --check     # do they match the repo?
    python tools/role_gate_mc_config.py --selftest  # does the arg guard hold?
    python tools/role_gate_mc_config.py --help

Exit 0  written, or (with --check) the committed files match what this would
        generate right now, or --help, or --selftest passed
Exit 1  --check found drift -- the apps moved and the model did not, or
        --selftest found an arm failing
Exit 2  COULD NOT RUN -- node is absent, a module could not be read, or AN
        ARGUMENT WAS NOT RECOGNISED. Never folded into 0: an empty instance
        would model-check clean.

── WHY AN UNRECOGNISED FLAG EXITS 2 AND WRITES NOTHING ─────────────────────
Until 2026-10-07 this tool recognised exactly one flag, `--check`, and every
other argument fell through to the WRITE path. `--help` -- the one argument a
reader types to find out what a tool does before running it -- therefore
REGENERATED both spec files. That is the fail-open shape stated in
CLAUDE.md/PR §1.11 wearing a different hat: the tool did not do nothing and did
not refuse, it did the most side-effecting thing it has, in response to an
instruction it had not understood.

The guard runs BEFORE `read_sets()`, so an unrecognised argument costs no node
invocation and cannot reach `open(..., 'w')`. There is no mode in which this
tool both prints "not recognised" and writes.

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


USAGE = """Generate docs/spec/MCRoleGates.{tla,cfg} from the REAL role sets.

    python tools/role_gate_mc_config.py             write both files
    python tools/role_gate_mc_config.py --check     compare, do not write
    python tools/role_gate_mc_config.py --selftest  prove the arg guard holds
    python tools/role_gate_mc_config.py --help      this text, and no write

Exit 0 wrote / matched / help / selftest passed, 1 drift or arm failed,
2 COULD NOT RUN -- including an argument this tool does not recognise."""

# Every argument this tool understands. A flag absent from here is NOT a
# synonym for "write"; see the docstring. Adding a mode means adding its
# literal here in the same change, which is the point of a closed list.
KNOWN_FLAGS = ('--check', '--selftest', '--help', '-h')

# The ONE knob the selftest's ablation turns, and the only reader of it is
# classify_argv. Set to '1' it restores the pre-2026-10-07 fall-through so the
# arms below can be seen to FAIL; an arm never observed failing is not an arm.
ABLATE_ENV = 'SAIRN_ROLE_GATE_ABLATE_ARGV_GUARD'


def classify_argv(argv, ablate=None):
    """-> ('check'|'write'|'help'|'selftest',) or ('unknown', the argument).

    Pure: no disk, no node, no environment beyond the ablation knob. It is
    separate from main so the selftest can assert on the DECISION rather than
    on a side effect it would have to clean up.
    """
    if ablate is None:
        ablate = os.environ.get(ABLATE_ENV) == '1'
    unknown = [a for a in argv if a not in KNOWN_FLAGS]
    if unknown and not ablate:
        return ('unknown', unknown[0])
    if '--help' in argv or '-h' in argv:
        return ('help',)
    if '--selftest' in argv:
        return ('selftest',)
    if '--check' in argv:
        return ('check',)
    return ('write',)


def selftest(ablate=None):
    """Six arms. Returns (passed, failed, lines).

    Arms 1-5 assert on classify_argv. Arm 6 is end-to-end -- it calls main()
    with an unrecognised flag and then asserts NOTHING WAS WRITTEN -- and it
    runs against a throwaway spec directory rather than the repo's, so that
    under ablation (where it MUST fail) the failure is a file appearing in a
    temp directory and never a regenerated committed file.
    """
    import contextlib
    import io
    import tempfile
    arms, lines = [], []

    arms.append(('unknown flag is not a write instruction',
                 classify_argv(['--bogus'], ablate), ('unknown', '--bogus')))
    arms.append(('--help is recognised and is not a write',
                 classify_argv(['--help'], ablate), ('help',)))
    arms.append(('--check still means check',
                 classify_argv(['--check'], ablate), ('check',)))
    arms.append(('a bare run still writes',
                 classify_argv([], ablate), ('write',)))
    # The real 2026-10-07 defect was a TYPO-shaped argument, not an exotic one.
    arms.append(('a near-miss of a real flag is unknown, not the flag',
                 classify_argv(['--cheque'], ablate), ('unknown', '--cheque')))

    tmp = tempfile.mkdtemp(prefix='rgmc-selftest-')
    # Captured rather than let through: the inner run's own refusal text on
    # stdout reads as THIS run refusing, which is a worse lie than silence.
    inner = io.StringIO()
    with contextlib.redirect_stdout(inner):
        rc = main(['--bogus'], spec=tmp, _in_selftest=True, _ablate=ablate)
    wrote = sorted(os.listdir(tmp))
    for f in wrote:
        os.remove(os.path.join(tmp, f))
    os.rmdir(tmp)
    arms.append(('end to end: unknown flag exits 2 and writes no file',
                 (rc, wrote), (2, [])))
    inner_first = (inner.getvalue().splitlines() or [''])[0]

    for name, got, want in arms:
        ok = got == want
        lines.append('  %-4s %s' % ('PASS' if ok else 'FAIL', name))
        if not ok:
            lines.append('       wanted %r, got %r' % (want, got))
    lines.append('       (inner run said: %s)' % inner_first)
    passed = sum(1 for _, g, w in arms if g == w)
    return passed, len(arms) - passed, lines


def main(argv, spec=None, _in_selftest=False, _ablate=None):
    spec = spec or SPEC
    mode = classify_argv(argv, _ablate)

    if mode[0] == 'unknown':
        print('COULD NOT RUN -- argument not recognised: %s' % mode[1])
        print('Nothing was written. Recognised: %s' % ', '.join(KNOWN_FLAGS))
        print('    python tools/role_gate_mc_config.py --help')
        return 2
    if mode[0] == 'help':
        print(USAGE)
        return 0
    if mode[0] == 'selftest':
        if _in_selftest:                      # no recursion, by construction
            print('COULD NOT RUN -- --selftest cannot call itself.')
            return 2
        passed, failed, lines = selftest(_ablate)
        print('arg guard selftest: %d/%d arm(s) pass' % (passed, passed + failed))
        for ln in lines:
            print(ln)
        if _ablate or os.environ.get(ABLATE_ENV) == '1':
            print('ABLATED (%s=1): the pre-2026-10-07 fall-through is restored, '
                  'so arms 1, 5 and 6 are EXPECTED to fail.' % ABLATE_ENV)
        return 1 if failed else 0

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
    tp = os.path.join(spec, 'MCRoleGates.tla')
    cp = os.path.join(spec, 'MCRoleGates.cfg')

    if mode[0] == 'check':
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
