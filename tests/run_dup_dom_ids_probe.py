"""Control pair for tools/dup_dom_ids_check.py.

THE CHECKER RETURNED CLEAN ON ITS FIRST RUN OVER ALL 22 APP FILES -- 7,752 ids,
0 duplicates -- WHICH IS EXACTLY WHEN A CHECKER IS LEAST TRUSTWORTHY. A tool
whose findings are clean has, by construction, never refused anything, so
nobody knows whether it CAN. Same standard
tools/discarded_verdict_check.py and the push-gate probes are held to.

Every arm below is a PAIR: one fixture where the checker MUST fire, and one
where it MUST stay silent. The silent half is the one usually left out, and it
is the half that matters for a tool meant to run over 7,752 ids -- a checker
that fires on everything is as useless as one that fires on nothing, and it is
the failure mode that gets the tool switched off.

THE FALSE-POSITIVE ARMS ARE THE REASON THIS FILE IS LONGER THAN THE CHECKER.
Every SAIRN app builds its tables by assigning innerHTML from JS template
strings, so the source of stonedesk.html contains hundreds of `id="..."`
occurrences that are NOT markup. A regex-based version of this checker would
report them and the real findings would be buried. Arms S1-S3 drive that
directly rather than trusting that html.parser handles CDATA.

Run:  python tests/run_dup_dom_ids_probe.py
Exit: 0 all arms pass, 1 any arm failed.
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO, 'tools', 'dup_dom_ids_check.py')

PASS = [0]
FAILED = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name)
    if cond:
        PASS[0] += 1
    else:
        FAILED.append(name)
        if detail:
            print('       ' + str(detail)[:600])


def run_tool(*paths):
    """-> (exit_code, stdout+stderr). Measured ALONE, never through a filter."""
    r = subprocess.run([sys.executable, TOOL] + list(paths),
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace', cwd=REPO)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def write(d, name, body):
    p = os.path.join(d, name)
    io.open(p, 'w', encoding='utf-8', newline='\n').write(body)
    return p


HEAD = '<!doctype html><html><head><title>t</title></head><body>\n'
TAIL = '\n</body></html>\n'

BASE = HEAD + '''
<div id="panel-one">one</div>
<div id="panel-two">two</div>
<input id="field-a">
<input id="field-b">
''' + TAIL

# The same document with ONE id declared twice, and nothing else changed. A
# fixture that differs in more than the planted defect cannot attribute a
# finding to it.
DUPE = BASE.replace('<div id="panel-two">two</div>',
                    '<div id="panel-one">two</div>')

# ── THE FALSE-POSITIVE FIXTURES ───────────────────────────────────────────
# S1: the real SAIRN shape. The duplicate exists ONLY inside a JS template
# string, which the browser never renders twice unless the JS renders twice --
# a different question this tool explicitly does not answer.
IN_SCRIPT = HEAD + '''
<div id="panel-one">one</div>
<tbody id="rows"></tbody>
<script>
  function render(list){
    document.getElementById('rows').innerHTML = list.map(function(x){
      return '<tr><td id="panel-one">' + x + '</td></tr>';
    }).join('');
  }
  var tpl = '<div id="rows"><span id="rows">dup inside a string</span></div>';
</script>
''' + TAIL

# S2: inside an HTML comment. Commented-out markup is not markup.
IN_COMMENT = HEAD + '''
<div id="panel-one">one</div>
<!-- <div id="panel-one">an old copy somebody left behind</div> -->
''' + TAIL

# S3: inside <style>, the other CDATA element.
IN_STYLE = HEAD + '''
<div id="panel-one">one</div>
<style>
  /* #panel-one { } and a literal id="panel-one" in a comment */
  #panel-one { color: red }
</style>
''' + TAIL

# Shapes the checker must NOT miss.
SELF_CLOSING = HEAD + '''
<input id="field-a" />
<input id="field-a" />
''' + TAIL

SINGLE_QUOTED = HEAD + """
<div id='panel-one'>one</div>
<div id="panel-one">two</div>
""" + TAIL

UNQUOTED = HEAD + '''
<div id=panel-one>one</div>
<div id="panel-one">two</div>
''' + TAIL

MIXED_CASE_ATTR = HEAD + '''
<div ID="panel-one">one</div>
<div id="panel-one">two</div>
''' + TAIL

EMPTY_IDS = HEAD + '''
<div id="">a</div>
<div id="">b</div>
<div id="  ">c</div>
<div id="real">d</div>
''' + TAIL

THREE_WAY = HEAD + '''
<div id="panel-one">a</div>
<div id="panel-one">b</div>
<div id="panel-one">c</div>
''' + TAIL

print('CONTROL PAIR -- tools/dup_dom_ids_check.py  (criteria read from the tool)')

D = tempfile.mkdtemp(prefix='dupids_probe_')
try:
    # ── P1: THE CORE PAIR ────────────────────────────────────────────────
    print('\nP1. THE CORE PAIR -- one planted duplicate, one clean document')

    p = write(D, 'planted.html', DUPE)
    rc, out = run_tool(p)
    check('PLANTED: a duplicated id FIRES -- exit 1', rc == 1, 'rc=%d\n%s' % (rc, out))
    check('...and the report NAMES the id and BOTH line numbers',
          'panel-one' in out and out.count('lines [') >= 1
          and '3' in out and '4' in out,
          out)

    p = write(D, 'clean.html', BASE)
    rc, out = run_tool(p)
    check('CLEAN: the same document without the duplicate is SILENT -- exit 0',
          rc == 0 and 'CLEAN' in out, 'rc=%d\n%s' % (rc, out))

    # ── P2: THE FALSE-POSITIVE SHAPES, WHICH ARE WHY THIS IS A PARSER ────
    print('\nP2. FALSE POSITIVES -- the shapes a regex gets wrong, driven')

    p = write(D, 'in_script.html', IN_SCRIPT)
    rc, out = run_tool(p)
    check('an id duplicated ONLY inside a <script> template string is SILENT '
          '-- the real SAIRN shape, and the one that would bury every finding',
          rc == 0, 'rc=%d\n%s' % (rc, out))

    p = write(D, 'in_comment.html', IN_COMMENT)
    rc, out = run_tool(p)
    check('an id duplicated ONLY inside an HTML comment is SILENT',
          rc == 0, 'rc=%d\n%s' % (rc, out))

    p = write(D, 'in_style.html', IN_STYLE)
    rc, out = run_tool(p)
    check('an id named ONLY inside <style> is SILENT',
          rc == 0, 'rc=%d\n%s' % (rc, out))

    # ── P3: SHAPES IT MUST NOT MISS. The silent direction is the dangerous
    #        one, so each of these is a FIRE arm.
    print('\nP3. SHAPES THE CHECKER MUST NOT MISS -- each must FIRE')

    for name, body, why in (
            ('self_closing.html', SELF_CLOSING,
             'a self-closing tag reaches handle_startendtag and NOT '
             'handle_starttag -- missing it under-counts, which is the silent '
             'direction'),
            ('single_quoted.html', SINGLE_QUOTED,
             "single-quoted against double-quoted: the browser sees one id, a "
             "naive `id=\"...\"` regex sees two different things"),
            ('unquoted.html', UNQUOTED, 'an unquoted attribute value'),
            ('mixed_case.html', MIXED_CASE_ATTR,
             'ID= against id=: HTML attribute names are case-insensitive'),
            ('three_way.html', THREE_WAY, 'three occurrences, not two')):
        p = write(D, name, body)
        rc, out = run_tool(p)
        check('FIRES on ' + name.replace('.html', '').replace('_', ' ')
              + ' -- ' + why, rc == 1 and 'panel-one' in out or
              (rc == 1 and 'field-a' in out), 'rc=%d\n%s' % (rc, out))

    rc, out = run_tool(write(D, 'three_way2.html', THREE_WAY))
    check('...and a THREE-way duplicate reports all three lines, not two',
          rc == 1 and out.count(',') >= 2, out)

    # ── P4: THINGS THAT ARE NOT DUPLICATES ───────────────────────────────
    print('\nP4. NOT DUPLICATES -- the over-eager direction')

    p = write(D, 'empty_ids.html', EMPTY_IDS)
    rc, out = run_tool(p)
    check('three EMPTY id attributes are NOT three duplicates of each other '
          '-- an empty id is not an id', rc == 0, 'rc=%d\n%s' % (rc, out))

    # ── P5: COULD NOT RUN IS A THIRD STATE ──────────────────────────────
    print('\nP5. COULD NOT RUN -- never folded into clean')

    rc, out = run_tool(os.path.join(D, 'does_not_exist.html'))
    check('a file that cannot be read exits 2, NOT 0, and says so',
          rc == 2 and 'COULD NOT READ' in out, 'rc=%d\n%s' % (rc, out))

    p1 = write(D, 'pair_clean.html', BASE)
    p2 = os.path.join(D, 'absent.html')
    rc, out = run_tool(p1, p2)
    check('...and ONE unreadable file among readable clean ones still exits 2 '
          '-- a partial scan is not a clean one',
          rc == 2, 'rc=%d\n%s' % (rc, out))

    # ── P6: THE REAL SCOPE, DERIVED ─────────────────────────────────────
    print('\nP6. SCOPE -- derived from git, not a hardcoded app list')

    rc, out = run_tool()
    check('the no-argument run scans the ROOT-level tracked html and says so',
          'root-level tracked' in out and 'files scanned:' in out,
          out[:400])
    scanned = 0
    for line in out.split('\n'):
        if 'files scanned:' in line:
            scanned = int(line.split(':')[1].strip())
    check('...and it scans MORE THAN ONE file, so a broken file list cannot '
          'read as a clean platform', scanned > 1, 'scanned=%d' % scanned)
    # ASSERTS ON THE FILE ROWS, NOT ON THE WHOLE OUTPUT, AND THE FIRST VERSION
    # DID NOT. `'archive/' not in out` is self-defeating: the SCOPE LINE the
    # tool prints contains the literal words "archive/ and subdirectories
    # excluded", so the arm failed on the tool correctly announcing the thing
    # the arm was checking for. A substring sweep over a report that describes
    # its own criteria will match the criteria.
    rows = [ln.strip() for ln in out.split('\n')
            if ln.startswith('  ') and '.html' in ln and 'scope' not in ln]
    check('...and archive/ is excluded by default -- duplicates in an '
          'abandoned branch snapshot would bury the live findings',
          rows and not any(r.startswith('archive/') for r in rows),
          '%d row(s), archive rows: %s'
          % (len(rows), [r for r in rows if r.startswith('archive/')][:5]))

    # ── P7: THE PLANTED-INTO-A-REAL-FILE ARM, ISOLATED ──────────────────
    # The strongest arm available without touching the clone: copy a REAL app
    # file into the scratch dir, plant one duplicate in it, and require the
    # checker to find it among the hundreds of genuine ids and the hundreds of
    # in-script decoys. The fixtures above are small and synthetic; this is the
    # same question asked at real scale.
    print('\nP7. PLANTED INTO A REAL APP FILE, COPIED OUT OF THE CLONE')

    src = os.path.join(REPO, 'sairnfreedom.html')
    if os.path.isfile(src):
        real = os.path.join(D, 'real_clean.html')
        shutil.copyfile(src, real)
        rc_clean, out_clean = run_tool(real)
        check('a real app file, unmodified, is CLEAN at full scale',
              rc_clean == 0, 'rc=%d\n%s' % (rc_clean, out_clean[-400:]))

        body = io.open(real, encoding='utf-8', errors='replace').read()
        # THE PLANT RECREATES THE EXACT DEFECT b4 FIXED IN THIS FILE: renaming
        # the accounts tbody back onto the officer roster's `ac-tbody`. Both
        # anchors are asserted to occur exactly once first, so the plant is
        # attributable and so this arm fails loudly if either id is renamed
        # again rather than silently planting nothing.
        #
        # THE FIRST VERSION PLANTED `cgtbody`, WHICH IS IN sairncare.html AND
        # NOT IN THIS FILE -- so the "duplicate" was a unique id and the
        # checker was right to stay silent. The arm went red because a plant
        # that plants nothing must not read as a tool that missed something.
        a_from, a_onto = 'id="acct-tbody"', 'id="ac-tbody"'
        n_from, n_onto = body.count(a_from), body.count(a_onto)
        check('both plant anchors occur EXACTLY ONCE in the real file, so the '
              'plant is attributable and a renamed id fails loudly',
              n_from == 1 and n_onto == 1,
              '%s=%d  %s=%d' % (a_from, n_from, a_onto, n_onto))
        if n_from == 1 and n_onto == 1:
            planted = os.path.join(D, 'real_planted.html')
            io.open(planted, 'w', encoding='utf-8', newline='').write(
                body.replace(a_from, a_onto))
            rc_p, out_p = run_tool(planted)
            check('...and recreating the exact ac-tbody collision b4 fixed '
                  'FIRES at full scale -- one duplicate among 400 ids and '
                  'hundreds of in-script decoys',
                  rc_p == 1 and 'ac-tbody' in out_p,
                  'rc=%d\n%s' % (rc_p, out_p[-500:]))
    else:
        check('SKIPPED P7: sairnfreedom.html not found in the clone', False,
              'the real-scale arm could not run, which is not a pass')

    # ── P8: THE CLONE WAS NOT TOUCHED ───────────────────────────────────
    print('\nP8. THIS PROBE LEFT THE CLONE ALONE')
    st = subprocess.run(['git', '-C', REPO, 'status', '--porcelain'],
                        capture_output=True, text=True, encoding='utf-8',
                        errors='replace').stdout
    check('no tracked file in the clone was modified by this probe -- every '
          'fixture lives in %TEMP% and the real file was COPIED, not edited',
          'sairnfreedom.html' not in st, st[:400])

finally:
    shutil.rmtree(D, ignore_errors=True)
    check('...and the fixture directory was removed', not os.path.isdir(D), D)

TOTAL = PASS[0] + len(FAILED)
if FAILED:
    print('\n%d of %d ARM(S) FAILED:' % (len(FAILED), TOTAL))
    for f in FAILED:
        print('  - %s' % f)
    sys.exit(1)
print('\nALL %d ARMS PASS' % TOTAL)
sys.exit(0)
