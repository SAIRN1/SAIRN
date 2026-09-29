#!/usr/bin/env python
"""hover_tool_index.py -- GENERATED index of this clone's own tools, from
the real files on disk and each one's own opening docstring line. Never
hand-maintained -- a hand-maintained list goes stale the moment a tool is
added and nobody remembers to update it, the same discipline
docs/TOOLING-INVENTORY.md already uses for the platform's own tools.

Adopted from H1's own stated practice ("before building a new tool, run
hover_tool_index.py -- checked, not assumed"), described in
.claude/skills/sairn-hover-auditor/SKILL.md's general prose (not one of
the two formally published interface specs) -- built here as a genuinely
independent, self-contained housekeeping habit rather than a parity
claim: it reads only THIS clone's own directory, needs no interface
contract with anything else, and the value (don't rebuild something that
already exists) holds regardless of how H1's own copy works internally.

    python hover_tool_index.py
    python hover_tool_index.py --selftest
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SELF_NAME = os.path.basename(__file__)


def first_docstring_line(path):
    """The opening summary line of a module's own triple-quoted docstring,
    or '(no docstring found)' if the file has none -- never guessed from
    the filename."""
    try:
        with io.open(path, encoding='utf-8') as f:
            text = f.read()
    except OSError as exc:
        return '(could not read: %s)' % exc
    # Skip a leading shebang / coding-declaration comment line (every real
    # tool in this directory starts with '#!/usr/bin/env python') -- found
    # necessary by running this against the real files, not assumed: the
    # fixture-only version of this test used bare docstrings with no
    # shebang and passed while the live run reported every real tool as
    # having "no docstring found".
    stripped = text.lstrip()
    while stripped.startswith('#'):
        nl = stripped.find('\n')
        stripped = stripped[nl + 1:].lstrip() if nl != -1 else ''
    for quote in ('"""', "'''"):
        if stripped.startswith(quote):
            rest = stripped[len(quote):]
            end = rest.find('\n')
            first_line = rest if end == -1 else rest[:end]
            # Strip a trailing closing-quote-on-the-same-line docstring
            # ('"""one liner"""') down to just the prose.
            if first_line.endswith(quote):
                first_line = first_line[:-len(quote)]
            return first_line.strip() or '(empty first line)'
    return '(no docstring found)'


def list_tools(directory=None, exclude=()):
    """[(filename, first_docstring_line)], sorted, for every *.py file in
    `directory` except this file itself and anything in `exclude`."""
    directory = directory or HERE
    out = []
    try:
        names = sorted(os.listdir(directory))
    except OSError as exc:
        return None, 'could not list %s: %s' % (directory, exc)
    for name in names:
        if not name.endswith('.py') or name == SELF_NAME or name in exclude:
            continue
        full = os.path.join(directory, name)
        if not os.path.isfile(full):
            continue
        out.append((name, first_docstring_line(full)))
    return out, ''


def main(argv):
    if '--selftest' in argv:
        return 0 if run_fixtures() else 1
    tools, problem = list_tools()
    if tools is None:
        print('COULD NOT RUN: %s' % problem)
        return 2
    print('HOVER2 TOOL INDEX -- %d tool(s) in %s (generated, not hand-maintained; '
         're-run this rather than trusting a remembered list):' % (len(tools), HERE))
    for name, line in tools:
        print('  %-32s %s' % (name, line))
    return 0


def run_fixtures():
    ok = [0]
    bad = []

    def ck(name, cond):
        if cond:
            ok[0] += 1
            print('  ok   ' + name)
        else:
            bad.append(name)
            print('  FAIL ' + name)

    import tempfile
    tmpdir = tempfile.mkdtemp()
    p1 = os.path.join(tmpdir, 'a.py')
    with io.open(p1, 'w', encoding='utf-8') as f:
        f.write('"""a one-line summary here.\n\nmore prose below."""\nimport os\n')
    p2 = os.path.join(tmpdir, 'b.py')
    with io.open(p2, 'w', encoding='utf-8') as f:
        f.write("'''single-quoted docstring works too'''\nx = 1\n")
    p3 = os.path.join(tmpdir, 'c.py')
    with io.open(p3, 'w', encoding='utf-8') as f:
        f.write('x = 1  # no docstring at all\n')
    # REGRESSION: found by running this live against this clone's own real
    # tools, not by inspection -- every one of them starts with a shebang
    # line before the docstring, and the first version of this function
    # reported "(no docstring found)" for all eight of them.
    p_shebang = os.path.join(tmpdir, 'd.py')
    with io.open(p_shebang, 'w', encoding='utf-8') as f:
        f.write('#!/usr/bin/env python\n"""a real tool\'s summary line."""\nimport sys\n')
    p4 = os.path.join(tmpdir, 'not_python.txt')
    with io.open(p4, 'w', encoding='utf-8') as f:
        f.write('should be ignored, not a .py file')

    ck('first_docstring_line() extracts the opening summary line of a '
       'triple-double-quoted docstring',
       first_docstring_line(p1) == 'a one-line summary here.')
    ck('first_docstring_line() handles a single-quoted (triple) docstring '
       'that closes on the same line',
       first_docstring_line(p2) == 'single-quoted docstring works too')
    ck('first_docstring_line() reports "(no docstring found)" honestly '
       'rather than guessing from the filename',
       first_docstring_line(p3) == '(no docstring found)')
    ck("first_docstring_line() skips a leading shebang line before the "
       "docstring -- the real-file shape every tool in this directory has, "
       "which the first version of this function got wrong",
       first_docstring_line(p_shebang) == "a real tool's summary line.")

    tools, problem = list_tools(tmpdir)
    ck('list_tools() finds exactly the .py files, ignoring non-.py files',
       not problem and [n for n, _l in tools] == ['a.py', 'b.py', 'c.py', 'd.py'])

    tools2, problem2 = list_tools(tmpdir, exclude={'b.py'})
    ck('list_tools() respects an explicit exclude set',
       [n for n, _l in tools2] == ['a.py', 'c.py', 'd.py'])

    missing, problem3 = list_tools(os.path.join(tmpdir, 'does-not-exist'))
    ck('list_tools() on a missing directory reports a problem, not an '
       'empty-but-clean result', missing is None and problem3)

    real_tools, real_problem = list_tools()
    ck('list_tools() against THIS clone\'s real directory finds hover_log.py '
       'and excludes this file itself',
       not real_problem
       and 'hover_log.py' in [n for n, _l in real_tools]
       and SELF_NAME not in [n for n, _l in real_tools])

    print('')
    if bad:
        print('%d of %d selftest arm(s) failed' % (len(bad), ok[0] + len(bad)))
        return False
    print('OK -- %d arms passed.' % ok[0])
    return True


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
