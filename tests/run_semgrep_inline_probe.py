#!/usr/bin/env python
"""Probe: tools/run_semgrep.py scans the apps' INLINE JavaScript, and says
what it does not cover.

    python tests/run_semgrep_inline_probe.py

Exit 0 all arms pass, 1 any arm fails, 3 SKIPPED (semgrep not installed --
sections A and B still run; only the live arm C is skipped, and says so).

THE DEFECT (cody b62). The SAIRN rules are `languages: [javascript,
typescript]`, so Semgrep only targets .js/.ts files, and every app is an .html
whose code is inline <script> (extract mode was removed in Semgrep 1.65.0).
24 apps were never scanned, and nothing said so: a file Semgrep never targets
is in neither `results` nor `errors`, and the tool read only `errors`.

  A. inline_js() keeps inline JS and blanks the rest, LINE FOR LINE, and leaves
     out <script src> and non-JS types (JSON, templates).
  B. an unreadable app is returned as could-not-scan, never dropped.
  C. LIVE: the real SAIRN rule, run on a twin of a fixture page, reports the
     violation at the .html's own line -- red on any version of the tool that
     scans .html files directly with these rules (it finds nothing).
"""
import os
import shutil
import subprocess
import sys
import tempfile

CONTROLS_FOR = ['tools/run_semgrep.py']

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import run_semgrep as S  # noqa: E402

bad = 0


def arm(label, cond, detail=''):
    global bad
    print(('  ok   ' if cond else '  FAIL ') + label
          + ('' if cond else '\n         %s' % str(detail)[-400:]))
    if not cond:
        bad += 1


PAGE = '\n'.join([
    '<!doctype html><html><head>',                         # 1
    '<script src="https://cdn.example/x.js"></script>',     # 2
    '<script type="application/json">{"verifySessionToken": 1}</script>',  # 3
    '</head><body><p>verifySessionToken(a, b) in prose</p>',  # 4
    '<script>',                                             # 5
    'function gate(req, licHash) {',                        # 6
    '  return verifySessionToken(tokenFromRequest(req), licHash);',  # 7
    '}',                                                    # 8
    '</script></body></html>',                              # 9
]) + '\n'


def main():
    print('RUN_SEMGREP -- inline app JavaScript')
    print('\nA. inline_js()')
    if not hasattr(S, 'inline_js'):
        arm('run_semgrep has inline_js() (the apps are scanned at all)', False,
            'no inline_js -- the tool scans no inline script')
        print('\n  %d ARM(S) FAILED' % bad)
        return 1
    js = S.inline_js(PAGE)
    lines = js.split('\n')
    arm('the twin has exactly as many lines as the page', js.count('\n') == PAGE.count('\n'))
    arm('the inline call stays on line 7', 'verifySessionToken(tokenFromRequest' in lines[6], lines[6])
    arm('markup prose is blanked (line 4)', not lines[3].strip(), lines[3])
    arm('a JSON <script type> is not treated as JavaScript (line 3)', not lines[2].strip(), lines[2])
    arm('a <script src> tag carries no inline code (line 2)', not lines[1].strip(), lines[1])

    print('\nB. unreadable apps')
    real_tracked, real_open = S.tracked, open
    d = tempfile.mkdtemp(prefix='semgrep-probe-')
    try:
        S.tracked = lambda *p: ['no-such-app-b62.html'] if p == ('*.html',) else []
        twins, unreadable = S.extract_apps(d)
        arm('an app that cannot be read is listed as could-not-scan, not skipped',
            not twins and len(unreadable) == 1 and 'no-such-app-b62.html' in unreadable[0],
            (twins, unreadable))
        S.tracked = lambda *p: None
        twins, unreadable = S.extract_apps(d)
        arm('no app list at all is a could-not-scan too', unreadable and not twins, unreadable)
    finally:
        S.tracked = real_tracked
        shutil.rmtree(d, ignore_errors=True)

    print('\nC. live, the real SAIRN rule')
    exe = S.semgrep_bin()
    if not exe:
        print('  SKIPPED: semgrep is not installed -- section C did not run.')
        print('\n  %s' % ('A AND B PASS, C SKIPPED' if not bad else '%d ARM(S) FAILED' % bad))
        return 1 if bad else 3
    d = tempfile.mkdtemp(prefix='semgrep-probe-')
    try:
        page = os.path.join(d, 'app.html')
        twin = os.path.join(d, 'app.html.inline.js')
        open(page, 'w', encoding='utf-8').write(PAGE)
        open(twin, 'w', encoding='utf-8').write(S.inline_js(PAGE))
        out = os.path.join(d, 'out.json')

        def scan(target):
            subprocess.run([exe, 'scan', '--config', S.RULES, '--json', '-o', out,
                            '--metrics=off', '--no-git-ignore', target],
                           cwd=d, env=S.env(), capture_output=True)
            import json
            return json.load(open(out, encoding='utf-8')).get('results', [])
        on_page = scan(page)
        arm('CONTROL: the rule run on the .html itself finds NOTHING -- the gap '
            'this probe exists for', on_page == [], on_page)
        on_twin = scan(twin)
        arm('on the twin it finds the violation, at the page\'s own line 7',
            len(on_twin) == 1 and on_twin[0]['start']['line'] == 7,
            [(r['check_id'], r['start']['line']) for r in on_twin])
    finally:
        shutil.rmtree(d, ignore_errors=True)

    print('\n  %s' % ('ALL ARMS PASS' if not bad else '%d ARM(S) FAILED' % bad))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
