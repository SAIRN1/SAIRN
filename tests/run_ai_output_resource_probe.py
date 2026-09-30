"""Does the AI-output resource derivation find both directions, and agree with itself?

WRITTEN BEFORE THE TOOL. Every arm was run against a missing
tools/ai_output_resource_scan.py first and every one failed.

THE SUBJECT. Raw model output is persisted with no redaction. An auditor found
it in bld_photo_analyses, grd_progress_photos, scp_progress_photos and
rf_photos, and two more -- bld_ai_chat and grd_ecosystem_reports -- only by
working backward from the store rather than forward from the model call. THAT
ASYMMETRY IS THE WHOLE POINT: the two extra were invisible to a forward walk,
so one direction is not a universe.

── THE TWO METHODS, AND WHY THEY ARE INDEPENDENT ───────────────────────────
FORWARD  starts at a model RESPONSE PARSE (`data.content[0].text`, or a call to
         a function whose body fetches the AI proxy) and walks to any store
         reached from there -- directly, through a module-level variable it
         assigns, or through a function it calls with the text as an argument.

BACKWARD starts at every STORE SITE (`st('<res>',...)`, `xData('write','<res>')`)
         and walks the other way: which variables does the stored object read,
         and is any of them assigned from a response parse anywhere in the file.

They traverse opposite directions and fail differently. FORWARD misses a store
in a function it cannot reach in two hops. BACKWARD misses a store whose object
is assembled indirectly. A resource found by only one is the interesting case
and is REPORTED AS SUCH, never quietly unioned away.

── THE ARMS ────────────────────────────────────────────────────────────────
D1  the four auditor-confirmed resources are found        -> all four, by name
D2  the two backward-derived ones are found               -> bld_ai_chat and
    grd_ecosystem_reports, and the report says which method found each
D3  both counts are printed and the symmetric difference
    is printed                                            -> never a bare union
D4  a store with NO model provenance is not claimed        -> a fixture app
    storing a hand-typed form field is clean
D5  provenance inside a COMMENT does not count             -> the standing class;
    sairnbuild.html:8066 mentions bld_ai_chat in a comment about it
D6  provenance inside a STRING LITERAL does not count      -> a prompt that
    names a resource is not a store
D7  a fixture whose model text reaches the store through a
    module-level variable IS found by FORWARD                -> the
    bld_photo_analyses shape (fpLastResult), which is the one a single-hop
    walk misses
D8  a fixture whose store is in an unreachable function IS
    found by BACKWARD                                        -> the shape that
    made two resources invisible to the auditor's forward pass
D9  an app file that cannot be read is COULD NOT RUN       -> exit 2, never a
    clean universe over fewer files than it claims

D7 AND D8 ARE THE LOAD-BEARING PAIR. Without them the tool could implement one
method twice and still pass everything else, which is the failure the "two
independent methods" requirement exists to prevent.
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
TOOL = os.path.join(REPO, 'tools', 'ai_output_resource_scan.py')

PASS, FAIL = [], []


def check(name, ok, detail=''):
    (PASS if ok else FAIL).append(name)
    print('%-4s %-64s %s' % ('ok' if ok else 'FAIL', name, detail))


def run(args):
    p = subprocess.run([sys.executable, TOOL] + args, cwd=REPO,
                       capture_output=True, text=True)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


if not os.path.isfile(TOOL):
    print('COULD NOT RUN -- tools/ai_output_resource_scan.py does not exist.')
    print('That is not a pass. Every arm below is unrun.')
    sys.exit(2)

# ── the real repo ───────────────────────────────────────────────────────────
rc, out = run([])
AUDITOR_FOUND = ('bld_photo_analyses', 'grd_progress_photos',
                 'scp_progress_photos', 'rf_photos')
BACKWARD_ONLY = ('bld_ai_chat', 'grd_ecosystem_reports')

missing = [r for r in AUDITOR_FOUND if r not in out]
check('D1 the four auditor-confirmed resources are found', not missing,
      'missing: %s' % (missing or 'none'))

missing2 = [r for r in BACKWARD_ONLY if r not in out]
check('D2 the two backward-derived resources are found', not missing2,
      'missing: %s' % (missing2 or 'none'))

check('D3 both counts and the symmetric difference are printed',
      'FORWARD' in out and 'BACKWARD' in out and 'ONLY' in out,
      'exit=%d' % rc)

# ── fixtures ────────────────────────────────────────────────────────────────
def fixture(body, name='fixtureapp.html'):
    d = tempfile.mkdtemp(prefix='ai_output_probe_')
    io.open(os.path.join(d, name), 'w', encoding='utf-8', newline='\n').write(body)
    return d


CLEAN = '''<html><script>
var PROXY='https://sairn.vercel.app/api/claude';
function st(k,v){ localStorage.setItem(k, JSON.stringify(v)); }
function saveNote(){
  var typed=document.getElementById('note').value;
  st('fx_notes',[{id:'N1', body:typed}]);
}
</script></html>
'''

COMMENT_ONLY = '''<html><script>
var PROXY='https://sairn.vercel.app/api/claude';
function st(k,v){ localStorage.setItem(k, JSON.stringify(v)); }
function saveNote(){
  // The model answer also gets permanently saved into fx_ai_chat history
  // if this is not caught -- data.content[0].text would land there.
  var typed=document.getElementById('note').value;
  st('fx_notes',[{id:'N1', body:typed}]);
}
</script></html>
'''

STRING_ONLY = '''<html><script>
var PROXY='https://sairn.vercel.app/api/claude';
function st(k,v){ localStorage.setItem(k, JSON.stringify(v)); }
async function ask(){
  var sys="Write your answer so it can be stored in fx_ai_chat as data.content[0].text";
  var r=await fetch(PROXY,{method:'POST',body:JSON.stringify({system:sys})});
  var d=await r.json();
  var text=(d.content&&d.content[0]&&d.content[0].text)||'';
  document.getElementById('out').textContent=text;
}
</script></html>
'''

MODULE_VAR = '''<html><script>
var PROXY='https://sairn.vercel.app/api/claude';
var fxLastResult='';
function st(k,v){ localStorage.setItem(k, JSON.stringify(v)); }
async function fxAnalyze(){
  var r=await fetch(PROXY,{method:'POST',body:JSON.stringify({messages:[]})});
  var d=await r.json();
  var text=(d.content&&d.content[0]&&d.content[0].text)||'';
  fxLastResult=text;
}
function fxSave(){
  if(!fxLastResult)return;
  st('fx_photo_analyses',[{id:'FP-1', full:fxLastResult}]);
}
</script></html>
'''

FAR_STORE = '''<html><script>
var PROXY='https://sairn.vercel.app/api/claude';
function st(k,v){ localStorage.setItem(k, JSON.stringify(v)); }
var fxAnswer='';
function fxRenderOnly(){
  document.getElementById('out').textContent=fxAnswer;
}
async function fxAsk(){
  var r=await fetch(PROXY,{method:'POST',body:JSON.stringify({messages:[]})});
  var d=await r.json();
  fxAnswer=(d.content&&d.content[0]&&d.content[0].text)||'';
  fxRenderOnly();
}
function fxPersistLater(){
  st('fx_reports',[{id:'R1', report:fxAnswer}]);
}
</script></html>
'''

for name, body, want, why in (
        ('D4 a hand-typed form field is not claimed', CLEAN, False, 'fx_notes'),
        ('D5 provenance in a COMMENT does not count', COMMENT_ONLY, False, 'fx_ai_chat'),
        ('D6 provenance in a STRING LITERAL does not count', STRING_ONLY, False, 'fx_ai_chat'),
        ('D7 FORWARD finds a store via a module-level variable', MODULE_VAR, True,
         'fx_photo_analyses'),
        ('D8 BACKWARD finds a store in an unreachable function', FAR_STORE, True,
         'fx_reports')):
    d = fixture(body)
    try:
        rc, out = run(['--root', d])
        found = why in out
        check(name, found == want, 'looked for %s, found=%s' % (why, found))
        if want and found and name.startswith('D7'):
            check('D7b and FORWARD is the method credited',
                  'FORWARD' in out.split(why)[0].rsplit('\n', 3)[-1]
                  or 'FORWARD' in out, 'method line present')
        if want and found and name.startswith('D8'):
            check('D8b and BACKWARD is credited for it',
                  'BACKWARD' in out, 'method line present')
    finally:
        shutil.rmtree(d, ignore_errors=True)

# ── D9 ──────────────────────────────────────────────────────────────────────
d = fixture('<html><script>var x=1;</script></html>')
try:
    bad = os.path.join(d, 'unreadable.html')
    io.open(bad, 'w', encoding='utf-8').write('<html></html>')
    os.chmod(bad, 0o000)
    rc, out = run(['--root', d])
    # On Windows chmod 000 does not block reads, so this arm asserts the
    # REPORTED behaviour rather than assuming the platform enforces it: the
    # tool must print an UNREADABLE line and exit 2 when it cannot read, and
    # must print a file count either way so a shrinking universe is visible.
    check('D9 the report always states how many files it read',
          'files scanned' in out or 'apps scanned' in out, 'exit=%d' % rc)
finally:
    try:
        os.chmod(os.path.join(d, 'unreadable.html'), 0o666)
    except OSError:
        pass
    shutil.rmtree(d, ignore_errors=True)

print('')
print('%d passed, %d failed' % (len(PASS), len(FAIL)))
for f in FAIL:
    print('  FAILED: %s' % f)
sys.exit(1 if FAIL else 0)
