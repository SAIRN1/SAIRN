"""Probe tools/local_only_collection_check.py against real history.

A checker that has only ever returned clean is a checker whose behaviour nobody
knows. This drives it against the two commits that motivated it, and against
synthetic files for each route it claims to resolve and each failure mode it
must still catch.

THE LOAD-BEARING ARMS ARE THE HISTORICAL ONES. sairnbiz.html at 48c122df^ and
sairnbuild.html at 1f1705e^ are the real files as they really were -- the two
apps whose "no server-side persistence" rows were closed by hand, and the case
tools/write_without_readback_check.py says in its own header that it CANNOT
see. If this does not go red on those, it would not have caught the defect it
exists for; and the fix landing is what has to change the answer, not a
rewording.

WHAT THE COUNTS DO AND DO NOT SAY. The SAIRNbiz index row says seventeen
localStorage collections. This finds ELEVEN, and the difference is not an
error: it counts RECORD COLLECTIONS -- keys the app itself reads with a list
default -- and not every key in localStorage. The eleven are a subset of the
seventeen and the arms below assert the subset, not the row's number.
"""
import os
import re
import subprocess
import sys
import tempfile

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()
TOOL = os.path.join(ROOT, 'tools', 'local_only_collection_check.py')

FAIL = []


def check(name, got, want):
    ok = got == want
    print('  %-6s %-58s got=%r' % ('ok' if ok else 'FAIL', name, got))
    if not ok:
        FAIL.append('%s: got %r, wanted %r' % (name, got, want))


def run(*paths):
    # utf-8 explicitly, not the locale codec: these app files carry box-drawing
    # characters in their comment banners and cp1252 cannot read them.
    r = subprocess.run([sys.executable, TOOL] + list(paths),
                       capture_output=True, text=True, cwd=ROOT,
                       encoding='utf-8', errors='replace')
    return r.returncode, r.stdout


def findings(out, section='KEPT ON THE DEVICE'):
    """The key names listed under one section of the report.

    Anchored on the whole header LINE. Splitting on the section name alone put
    the trailing `===` of the header itself between the parser and the keys, so
    every arm read back an empty set and eight of them "passed" or "failed" for
    a reason that had nothing to do with the tool.
    """
    m = re.search(r'^=== ' + re.escape(section) + r'.*?===\s*$', out, re.M)
    if not m:
        return set()
    rest = out[m.end():]
    end = re.search(r'^===', rest, re.M)
    body = rest[:end.start()] if end else rest
    keys = set(re.findall(r'^\s{6}([\w.-]+)\s*$', body, re.M))
    # The could-not-tell section names the key inline rather than on its own
    # line: "  app.html x_pics -- written near a server call in f(), but ..."
    keys |= set(re.findall(r'^\s{2}\S+\.html\s+([\w.-]+)\s+--', body, re.M))
    return keys


def show(path, html, registry=None):
    """Write a synthetic app (and optionally its registry) under `path`."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'w', encoding='utf-8').write(html)
    if registry is not None:
        app = os.path.splitext(os.path.basename(path))[0]
        d = os.path.join(os.path.dirname(path), 'api', '_resources')
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, app + '.js'), 'w', encoding='utf-8').write(registry)


def git_show(rev, path, dest):
    # BYTES, not text. A historical app file is whatever bytes it was, and
    # decoding it through the machine's locale codec fails outright on the
    # box-drawing characters these files use in their comment banners.
    r = subprocess.run(['git', 'show', '%s:%s' % (rev, path)],
                       capture_output=True, cwd=ROOT)
    if r.returncode != 0:
        return False
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    open(dest, 'wb').write(r.stdout)
    return True


# ═══════════════════════════════════════════════════════════════════════════
def historical(tmp):
    print('-- the two real incidents, before and after the commit that fixed them --')
    for app, commit, expect_before_min, expect_after in (
            ('sairnbiz', '48c122df', 10, {'sb_incidents'}),
            ('sairnbuild', '1f1705e', 29, set())):
        for side, rev in (('before', commit + '^'), ('after', commit)):
            base = os.path.join(tmp, side)
            got_html = git_show(rev, app + '.html', os.path.join(base, app + '.html'))
            check('%s %s: the file exists at that commit' % (app, side), got_html, True)
            if not got_html:
                continue
            # The registry is part of the fix, so it is taken from the same
            # commit -- reading today's registry against yesterday's HTML would
            # make the before-state look better than it was.
            git_show(rev, 'api/_resources/%s.js' % app,
                     os.path.join(base, 'api', '_resources', app + '.js'))
            rc, out = run(os.path.join(base, app + '.html'))
            found = findings(out)
            if side == 'before':
                check('%s BEFORE the fix: exits non-zero' % app, rc, 1)
                check('%s BEFORE the fix: at least %d local-only' % (app, expect_before_min),
                      len(found) >= expect_before_min, True)
            else:
                check('%s AFTER the fix: exactly the known-open remainder' % app,
                      found, expect_after)


# ═══════════════════════════════════════════════════════════════════════════
APP = """<html><script>
function st(k,v){localStorage.setItem(k,JSON.stringify(v));return true;}
function ld(k,d){var r=localStorage.getItem(k);return r?JSON.parse(r):d;}
function xData(a,r,p){return fetch('/api',{body:JSON.stringify({action:a,resource:r})});}
%s
</script></html>"""


def synthetic(tmp):
    print('-- one arm per route it claims to resolve --')

    # SAME NAME -- the SAIRNbiz convention.
    show(tmp + '/a/app.html', APP % """
function rows(){return ld('x_jobs',[]);}
function save(l){st('x_jobs',l);xData('write','x_jobs',l);}""", None)
    check('same-name resource counts as covered', findings(run(tmp + '/a/app.html')[1]), set())

    # PAIR LIST -- the SAIRNdental convention: [resource, storage key].
    show(tmp + '/b/app.html', APP % """
var SYNC=[['x_charges','x_charges_list']];
function rows(){return ld('x_charges_list',[]);}
function save(l){st('x_charges_list',l);}
function hydrate(){return xData('read','x_charges',{});}""", None)
    check('pair list [resource, key] counts as covered',
          findings(run(tmp + '/b/app.html')[1]), set())

    # PREFIX STRIPPED -- the StoneDesk convention: sd_slabs <-> 'slabs'.
    show(tmp + '/c/app.html', APP % """
function rows(){return ld('sd_slabs',[]);}
function save(l){st('sd_slabs',l);}
function hydrate(){return xData('read','slabs',{});}""", None)
    check('prefix-stripped resource counts as covered',
          findings(run(tmp + '/c/app.html')[1]), set())

    # SYNCED LIST -- the SAIRNbuild/SAIRNbiz generic write hook.
    show(tmp + '/d/app.html', APP % """
var SYNCED=['x_bids','x_costs'];
var _on={};SYNCED.forEach(function(k){_on[k]=true;});
function hook(key,r){if(!_on[key])return;xData('write',key,r);}
function a(){return ld('x_bids',[]);}
function b(){return ld('x_costs',[]);}
function s1(l){st('x_bids',l);}
function s2(l){st('x_costs',l);}""", None)
    check('membership in the synced list counts as covered',
          findings(run(tmp + '/d/app.html')[1]), set())

    # SIBLING SYNC -- the local write and the server call share a variable.
    show(tmp + '/e/app.html', APP % """
function sync(emps){return xData('write','employees',emps);}
function rows(){return ld('x_emps',[]);}
function save(emps){st('x_emps',emps);sync(emps);}""", None)
    check('a shared variable with a server call counts as covered',
          findings(run(tmp + '/e/app.html')[1]), set())

    # REGISTRY -- the route lives outside the HTML entirely.
    show(tmp + '/f/app.html', APP % """
function rows(){return ld('x_plots',[]);}
function save(l){st('x_plots',l);}""",
         "module.exports = { resources: [ 'x_plots' ] };")
    check('a registered resource counts as covered',
          findings(run(tmp + '/f/app.html')[1]), set())

    print('-- one arm per failure mode it must still catch --')

    # THE DEFECT ITSELF.
    show(tmp + '/g/app.html', APP % """
function rows(){return ld('x_incidents',[]);}
function save(l){st('x_incidents',l);}
function other(l){st('x_jobs',l);xData('write','x_jobs',l);}
function j(){return ld('x_jobs',[]);}""", None)
    rc, out = run(tmp + '/g/app.html')
    check('a collection with no route at all is REPORTED', findings(out), {'x_incidents'})
    check('...and the exit code says so', rc, 1)

    # A WORD IN A REGISTRY COMMENT MUST NOT CLEAR A KEY. This was a real
    # defect: reading every quoted lowercase word in the registry file cleared
    # StoneDesk's sd_jobs on the word 'jobs' inside a sentence.
    show(tmp + '/h/app.html', APP % """
function rows(){return ld('x_jobs',[]);}
function save(l){st('x_jobs',l);}""",
         "// this app has 'x_jobs' in prose, deliberately\n"
         "module.exports = { resources: [ 'x_other' ] };")
    check('a resource named only in a registry COMMENT does not clear a key',
          findings(run(tmp + '/h/app.html')[1]), {'x_jobs'})

    # A SEED BESIDE A SERVER CALL IS NOT A SYNC. Also real: an earlier version
    # cleared three SAIRNbuild keys because bldSeedRows() writes them next to
    # a server call.
    show(tmp + '/i/app.html', APP % """
function seed(){st('x_synced',[1]);xData('write','x_synced',[1]);st('x_orphan',[2]);}
function a(){return ld('x_synced',[]);}
function b(){return ld('x_orphan',[]);}""", None)
    check('a key seeded beside a server call is NOT cleared by it',
          findings(run(tmp + '/i/app.html')[1]), {'x_orphan'})

    # AN ADJACENT-BUT-UNRELATED WRITE IS A COULD NOT TELL, NOT A PASS.
    show(tmp + '/j/app.html', APP % """
function saveBoth(){var cust=ld('x_cust',[]);var pics=ld('x_pics',[]);
  st('x_cust',cust);xData('write','x_cust',cust);st('x_pics',pics);}""", None)
    rc, out = run(tmp + '/j/app.html')
    check('an unrelated neighbouring write is a COULD NOT TELL',
          findings(out, 'COULD NOT TELL'), {'x_pics'})
    check('...and a could-not-tell exits non-zero too', rc, 1)

    # DEVICE STATE IS NOT A BUSINESS COLLECTION.
    show(tmp + '/k/app.html', APP % """
function s(){st('x_license_key','K');st('x_session_token','T');st('x_ui',{});}""", None)
    rc, out = run(tmp + '/k/app.html')
    check('licence/session/ui keys are not reported as collections',
          findings(out), set())

    # THE SETTER IS DISCOVERED, NOT ASSUMED. An app that does not call it st()
    # must still be checked -- hardcoding the name would pass three apps clean
    # while checking nothing.
    show(tmp + '/l/app.html', """<html><script>
function scpSt(k,v){localStorage.setItem(k,JSON.stringify(v));return true;}
function scpLd(k,d){var r=localStorage.getItem(k);return r?JSON.parse(r):d;}
function rows(){return scpLd('y_quotes',[]);}
function save(l){scpSt('y_quotes',l);}
</script></html>""", None)
    rc, out = run(tmp + '/l/app.html')
    check('a differently-named setter is still found and checked',
          findings(out), {'y_quotes'})
    check('...and the report names the setter it found',
          'scpSt' in out, True)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        historical(tmp)
        print()
        synthetic(tmp)
    print()
    if FAIL:
        print('%d ARM(S) FAILED' % len(FAIL))
        for f in FAIL:
            print('   ' + f)
        return 1
    print('local_only_probe: all arms pass')
    return 0


if __name__ == '__main__':
    sys.exit(main())
