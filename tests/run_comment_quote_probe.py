"""Probe tools/comment_quote_check.py, by attacking it.

WHY THE TOOL EXISTS. Twice on 2026-09-10, hours apart, a probe searched a source
file for a literal and matched the fix's own COMMENT rather than its code, and
failed a correct file. That direction is loud. THE SILENT DIRECTION IS THE ONE
NOTHING WOULD CATCH: an assertion of PRESENCE goes green when the only surviving
mention of the thing is a comment describing the feature that was deleted.

WHY THIS PROBE ATTACKS RATHER THAN CONFIRMS. The tool currently reports ZERO
undeclared findings against the real repo. A checker that finds nothing is
indistinguishable from a checker that looks at nothing -- the exact shape this
platform keeps finding -- so every arm below plants a defect on a throwaway
fixture and asserts the tool SEES it, then removes the defect and asserts it
goes quiet again.

ARM 4 IS THE ONE THAT MATTERS. It is the failure the tool was built for and the
one no human was going to notice: a presence assertion satisfied entirely by a
comment.

ARM 5 IS ABOUT THE TOOL'S OWN FIRST BUG, kept as a permanent regression guard.
Its comment stripper blanked from any `//` to end of line, so every `https://`
in the target swallowed the rest of its line and real code was reported as
comment -- the tool committing the error it hunts. A URL-heavy fixture is now
asserted to stay clean.

Run: python tests/run_comment_quote_probe.py
"""
# Declares, for tools/checker_control_check.py, which checker(s) this file is
# the control for. Attribution is DECLARED rather than inferred because three
# inference models were each wrong within an hour of being written.
CONTROLS_FOR = ['comment_quote_check.py']

import io
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO, 'tools', 'comment_quote_check.py')
sys.path.insert(0, os.path.join(REPO, 'tools'))
import comment_quote_check as C  # noqa: E402

failures = []


def check(name, ok, detail=''):
    print('  %-4s %-62s %s' % ('PASS' if ok else 'FAIL', name, detail))
    if not ok:
        failures.append(name)


print('COMMENT-QUOTE CHECK PROBE -- every arm plants a defect and demands it be seen\n')

# ── 1. the stripper, directly
S = C.strip_comments
check('1a  an HTML comment is blanked', 'secret' not in S('<!-- secret -->'), '')
check('1b  a // comment is blanked', 'secret' not in S('var a=1; // secret'), '')
check('1c  a /* */ comment is blanked', 'secret' not in S('var a=1; /* secret */ var b=2;'), '')
check('1d  CONTROL: real code survives', 'keepMe' in S('function keepMe(){}'), '')
# THE TOOL'S OWN FIRST BUG.
check('1e  a URL is NOT treated as a comment start',
      'afterTheUrl' in S("var u='https://x.example/a'; var afterTheUrl=1;"),
      'the // in https:// must not swallow the line')
check('1f  CONTROL: and a real comment AFTER a URL still goes',
      'gone' not in S("var u='https://x.example/a'; // gone"), '')
check('1g  a // inside a string literal is not a comment',
      'kept' in S("var s='a // b'; var kept=1;"), '')
# Offsets must be preserved or positions stop being comparable.
src = '<!-- xx -->code'
check('1h  offsets are preserved', len(S(src)) == len(src), '%d == %d' % (len(S(src)), len(src)))

# ── 1i-1q  REGEX LITERALS (2026-09-24). The tool was wrong in BOTH directions
# and its own disclosure said only one of them, in the wrong direction: it
# claimed an unparsed regex "can over-strip ... biases toward reporting MORE
# code as comment, which is the safe direction". Measured across 753 tracked
# js/html files, the real split was 2,178 characters over-stripped in 54 files
# AND 328,210 characters UNDER-stripped in 27 -- real comments handed to every
# caller as code, which is the unsafe direction it said it did not have.
check('1i  a QUOTE inside a regex literal does not swallow the comment after it',
      'gone' not in S('const Q = /"/;  // gone\n'),
      'a double quote in a regex opened a bogus string span, and the scanner '
      'walked past the real comment looking for a closing quote')
check('1j  ...the single-quote form too',
      'gone' not in S("const Q = /'/;  // gone\n"), '')
check('1k  ...and a character class holding both',
      'gone' not in S('const RX = /[\'"]/;  // gone\n'), '')
check('1l  a BACKTICK inside a regex does not swallow the REST OF THE FILE. '
      'api/_lib/style-profile.js:71 is the real instance -- one backtick in a '
      'markdown-detection regex, and every comment below it reached callers '
      'as code',
      'gone' not in S('const RX = /`[^`]+`/m.test(s);\n// gone\nconst k = 1;\n')
      and 'const k' in S('const RX = /`[^`]+`/m.test(s);\n// gone\nconst k = 1;\n'),
      '')
check('1m  an ESCAPED SLASH inside a regex is not read as a comment opener. '
      '`replace(/\\//g, ...)` puts two slashes side by side and the whole rest '
      'of the line was being blanked -- this is the over-strip half, and it is '
      'in api/_lib/auth.js',
      'kept' in S("s.replace(/\\//g, '_'); var kept = 1;"), '')
check('1n  CONTROL: a // inside a regex is still not a comment',
      'kept' in S('const r = /a\\/\\/b/; var kept = 1;'), '')
check('1o  CONTROL: DIVISION is not mistaken for a regex. Reading `a / b` as a '
      'literal would skip to the next slash and under-strip again, which is '
      'the failure being fixed, reintroduced by the fix',
      'gone' not in S('const a = b / c;  // gone\nconst d = e / f;  // also\n'),
      '')
check('1p  CONTROL: nor after a closing paren',
      'gone' not in S('const a = (x) / 2;  // gone\n'), '')
check('1q  CONTROL: an UNTERMINATED slash is not a regex -- a JS literal '
      'cannot span a newline, so running past one would be the runaway this '
      'guards against',
      'gone' not in S('const a = 1 / 2\n// gone\n'), '')


def run(tmp):
    """Run the tool with REPO pointed at a fixture directory."""
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'
    env['PYTHONUTF8'] = '1'
    shim = os.path.join(tmp, 'runner.py')
    io.open(shim, 'w', encoding='utf-8', newline='\n').write(
        'import sys\n'
        'sys.path.insert(0, %r)\n' % os.path.join(REPO, 'tools') +
        'import comment_quote_check as C\n'
        'C.REPO = %r\n' % tmp +
        'C.EXPECTED_COMMENT_ASSERTIONS = {}\n'
        'sys.exit(C.main(["x"]))\n')
    p = subprocess.run([sys.executable, shim], capture_output=True, text=True,
                       encoding='utf-8', errors='replace', env=env)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


def fixture(app_body, test_body):
    tmp = tempfile.mkdtemp(prefix='cq_probe_')
    os.makedirs(os.path.join(tmp, 'tests'))
    io.open(os.path.join(tmp, 'app.html'), 'w', encoding='utf-8', newline='\n').write(app_body)
    io.open(os.path.join(tmp, 'tests', 't.js'), 'w', encoding='utf-8', newline='\n').write(test_body)
    return tmp


READ = ("const fs = require('fs');\nconst path = require('path');\n"
        "const src = fs.readFileSync(path.join(__dirname, '..', 'app.html'), 'utf8');\n")

# ── 2. the loud direction: a literal that lives only in a comment
tmp = fixture('<!-- the old wording was "server sync off" -->\n<script>var x=1;</script>\n',
              READ + "if (src.indexOf('server sync off') !== -1) { throw 1; }\n")
rc, out = run(tmp)
check('2a  a comment-only literal is reported', 'COMMENT-ONLY, undeclared  : 1' in out, '')
check('2b  and the exit code is non-zero', rc == 1, 'exit %d' % rc)
shutil.rmtree(tmp, ignore_errors=True)

# ── 3. NEGATIVE CONTROL: the same literal in CODE is not reported
tmp = fixture('<script>var msg = "server sync off";</script>\n',
              READ + "if (src.indexOf('server sync off') !== -1) { throw 1; }\n")
rc, out = run(tmp)
check('3a  CONTROL: a literal that IS in code is silent',
      'COMMENT-ONLY, undeclared  : 0' in out, '')
check('3b  CONTROL: and exits 0', rc == 0, 'exit %d' % rc)
shutil.rmtree(tmp, ignore_errors=True)

# ── 4. THE SILENT DIRECTION -- the reason this tool exists
# A guard was deleted from the code; only the comment describing it remains. The
# probe asserts the guard is PRESENT and would pass. Nothing else catches this.
tmp = fixture('<!-- removed 2026-01-01: used to call requireOwnerRole() here -->\n'
              '<script>function save(){ writeRow(); }</script>\n',
              READ + "if (src.indexOf('requireOwnerRole()') === -1) { throw 1; }\n")
rc, out = run(tmp)
check('4a  a PRESENCE assertion satisfied only by a comment is reported',
      'COMMENT-ONLY, undeclared  : 1' in out, 'the green-on-a-deleted-guard case')
check('4b  and it names the literal', 'requireOwnerRole()' in out, '')
shutil.rmtree(tmp, ignore_errors=True)

# ── 5. REGRESSION GUARD on the tool's own first bug
tmp = fixture('<script>\nvar u = "https://cdn.example/lib.js";\nfunction realCode(){ return 1; }\n</script>\n',
              READ + "if (src.indexOf('function realCode') === -1) { throw 1; }\n")
rc, out = run(tmp)
check('5a  code on a line after a URL is NOT called a comment',
      'COMMENT-ONLY, undeclared  : 0' in out,
      'the bug that made the tool report a third of stonedesk.html as documentation')
shutil.rmtree(tmp, ignore_errors=True)

# ── 6. scoping: only the variable bound to the RAW file counts
# A probe that strips comments ITSELF is doing the right thing and must not be
# flagged for it -- tests/sairndental_write_failure_voice.js already did this
# before the rule existed.
tmp = fixture('<!-- the old wording was "server sync off" -->\n<script>var x=1;</script>\n',
              READ + "const codeOnly = src.split('\\n').filter(l => l.trim().slice(0,2) !== '//').join('\\n');\n"
                     "if (codeOnly.indexOf('server sync off') !== -1) { throw 1; }\n")
rc, out = run(tmp)
check('6a  a search against a comment-stripped copy is NOT flagged',
      'COMMENT-ONLY, undeclared  : 0' in out, 'searching codeOnly, not src')
shutil.rmtree(tmp, ignore_errors=True)

# ── 7. the real repo is clean, and that claim is only worth making because of
#       arms 2-6 above.
rc, out = subprocess.run(
    [sys.executable, TOOL], capture_output=True, text=True, encoding='utf-8',
    errors='replace', cwd=REPO,
    env=dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1')
), None
check('7a  the real repo has zero UNDECLARED comment-only assertions',
      rc.returncode == 0, 'exit %d' % rc.returncode)
check('7b  and it did inspect something -- a checker that looks at nothing '
      'also exits 0', 'assertions inspected' in rc.stdout and
      'assertions inspected      : 0' not in rc.stdout, '')

print('\n%d arm(s) failed' % len(failures))
for f in failures:
    print('  %s' % f)
sys.exit(1 if failures else 0)
