"""tools/discarded_verdict_crossfile.py -- the CROSS-MODULE half of the
discarded-verdict question, asked once so it does not have to be re-derived.

    python tools/discarded_verdict_crossfile.py              # survey api/
    python tools/discarded_verdict_crossfile.py --root <dir> # survey a copy

── WHY THIS IS A SEPARATE TOOL AND NOT A FLAG ON ITS SIBLING ─────────────
`tools/discarded_verdict_check.py` finds a refusal computed and dropped
INSIDE one file, and its open-work row states the reason it stops there:

    "Fix shape: resolve require() targets and follow exported names -- worth
     doing only if a real instance of the cross-file shape turns up, since a
     speculative version would add false positives to a check whose value is
     that it currently has none."

That condition is respected. This does not extend that check, is not wired
into any routine run, and adds nothing to its output. It is a SURVEY that
answers "has an instance turned up", so the answer is a measurement rather
than an opinion, and re-measuring costs one command instead of an afternoon.

── THE ANSWER, AS OF 2026-09-04 ──────────────────────────────────────────
ZERO, in both shapes, across 80 verdict-shaped exported functions in
non-test `api/` code. That is a genuinely good result for the platform and
it is the reason the cross-module pass was NOT built.

**A zero from a scanner nobody has watched fire is not a result**, so the
negative control is part of the deliverable rather than a thing that was done
once and forgotten: `tests/run_discarded_verdict_crossfile_probe.py` copies
`api/`, plants one of each shape, and requires both to be found. If the
control ever stops firing, the zero above means nothing.

── THE TWO SHAPES ────────────────────────────────────────────────────────
  BARE    `await lib.fn(a, b);` as an expression statement -- the verdict is
          computed and never looked at. This is the shape all four
          `api/_lib/courtlistener.js` sites had, one file over.
  UNREAD  `const verdict = lib.fn(a, b);` where `verdict` is never mentioned
          again in the file. The answer is held and still never consulted --
          which is what `logDoseAudit`'s seventeen callers did within a file
          on the same day.

── LIMITS, STATED SO A CLEAN RUN CANNOT BE READ AS A GUARANTEE ───────────
* A function is "verdict-shaped" only if it RETURNS AN OBJECT LITERAL whose
  keys include one of VERDICT_KEYS. A verdict returned as a bare boolean, or
  assembled into a variable and returned by name, is invisible here.
* Exports are matched textually (`module.exports = {...}` and `exports.x =`).
  A re-exported or dynamically attached name is missed.
* "Never read again" is a whole-file text search for the identifier, not a
  scope-aware one. It is deliberately conservative: a shadowed name in an
  unrelated function counts as a read and suppresses the report. This tool
  under-reports on purpose -- see its sibling's row for what a noisy check
  costs.
* Test files are excluded. Assert helpers legitimately call a verdict function
  as a statement, and including them produced nine results that were all noise.
"""
import io
import os
import re
import sys

VERDICT_KEYS = ('limited', 'allowed', 'ok', 'denied', 'blocked', 'forbidden',
                'problem', 'refused', 'error', 'valid', 'permitted')


def js_files(root, include_tests=False):
    out = []
    api = os.path.join(root, 'api')
    for base, dirs, files in os.walk(api):
        dirs[:] = [d for d in dirs if d != 'node_modules']
        for f in sorted(files):
            if not f.endswith('.js'):
                continue
            if not include_tests and f.endswith('.test.js'):
                continue
            out.append(os.path.join(base, f))
    return out


def read(path):
    return io.open(path, encoding='utf-8', errors='replace').read()


def fn_body(src, name):
    """The brace-balanced body of `function name(` or `const name = (…) =>`."""
    patterns = [r'(?:async\s+)?function\s+' + re.escape(name) + r'\s*\(',
                r'(?:const|let|var)\s+' + re.escape(name) + r'\s*=\s*(?:async\s*)?\(']
    for pattern in patterns:
        m = re.search(pattern, src)
        if not m:
            continue
        i = src.find('{', m.end())
        if i < 0:
            continue
        depth = 0
        for j in range(i, len(src)):
            if src[j] == '{':
                depth += 1
            elif src[j] == '}':
                depth -= 1
                if depth == 0:
                    return src[i:j + 1]
    return None


def verdict_keys(body):
    if not body:
        return None
    for m in re.finditer(r'return\s*\{([^}]{0,400})', body):
        blob = m.group(1)
        keys = [k for k in VERDICT_KEYS
                if re.search(r'(^|[\s,{])' + k + r'\s*:', blob)]
        if keys:
            return sorted(set(keys))
    return None


def exported_verdicts(root):
    """{exported name: [modules that export it with a verdict shape]}"""
    names = {}
    for path in js_files(root, include_tests=True):
        src = read(path)
        rel = os.path.relpath(path, root).replace('\\', '/')
        found = set()
        m = re.search(r'module\.exports\s*=\s*\{([^}]*)\}', src, re.S)
        if m:
            found |= set(re.findall(r'([A-Za-z_$][\w$]*)\s*(?:,|:|$)', m.group(1)))
        found |= set(re.findall(r'(?:module\.)?exports\.([A-Za-z_$][\w$]*)\s*=', src))
        for name in found:
            keys = verdict_keys(fn_body(src, name))
            if keys:
                names.setdefault(name, []).append(rel)
    return names


BARE = re.compile(r'^(?:await\s+)?([A-Za-z_$][\w$]*)(?:\.([A-Za-z_$][\w$]*))?\s*\([^;]*\);\s*$')
ASSIGN = re.compile(r'^(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:await\s+)?'
                    r'([A-Za-z_$][\w$]*)(?:\.([A-Za-z_$][\w$]*))?\s*\(')


def survey(root):
    names = exported_verdicts(root)
    hits = []
    for path in js_files(root):
        rel = os.path.relpath(path, root).replace('\\', '/')
        lines = read(path).split('\n')
        for i, line in enumerate(lines, 1):
            s = line.strip()
            if s.startswith('//') or s.startswith('*'):
                continue
            m = BARE.match(s)
            if m:
                name = m.group(2) or m.group(1)
                owners = [o for o in names.get(name, []) if o != rel]
                if owners:
                    hits.append(('BARE', rel, i, s, owners[0]))
            m = ASSIGN.match(s)
            if m:
                var, name = m.group(1), (m.group(3) or m.group(2))
                owners = [o for o in names.get(name, []) if o != rel]
                if owners and not re.search(
                        r'(?<![\w$.])' + re.escape(var) + r'(?![\w$])',
                        '\n'.join(lines[i:])):
                    hits.append(('UNREAD', rel, i, s, owners[0]))
    return names, hits


def main(argv):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if '--root' in argv:
        root = argv[argv.index('--root') + 1]
    names, hits = survey(root)
    print('VERDICT_SHAPED_EXPORTS:%d' % len(names))
    for kind, rel, line_no, text, owner in hits:
        print('  %-7s %s:%d  %s  (exported by %s)'
              % (kind, rel, line_no, text[:80], owner))
    print('BARE_STATEMENT_CROSS_FILE:%d'
          % len([h for h in hits if h[0] == 'BARE']))
    print('ASSIGNED_NEVER_READ_CROSS_FILE:%d'
          % len([h for h in hits if h[0] == 'UNREAD']))
    print('NOTE: a clean run means no hit matched these two SHAPES. It is not '
          'a guarantee -- see the limits in this file\'s header.')
    return 0


if __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.exit(main(sys.argv[1:]))
