r"""Does every mutation control's anchor still match its target EXACTLY ONCE?

    python -m testint.check_mutation_anchor --config testint.config.json

Exit 0 when every anchor matches once, 1 when one does not, **2 when a control
could not be read at all** -- which is not a pass and is never collapsed into 0.

── THE FAILURE ───────────────────────────────────────────────────────────────
A mutation control reintroduces a defect, asserts the suite goes red, and
restores the file. Its anchor is an exact string. When the target is refactored:

  * **the anchor matches ZERO times** -- the control mutates nothing, asserts
    nothing, and passes. One real control sat that way for a day while its own
    harness printed `ANCHOR-0`;
  * **it matches MORE THAN ONCE** -- the control mutates whichever came first,
    so it is probing a site nobody chose. One real file carries a note about
    exactly that: an anchor shared by two writers probed neither.

Both are caught by each control's own harness -- **when it runs**. That is a
weaker guarantee than it sounds: a control only checks its own anchors, only
when something runs it, and several refuse to run against a dirty tree. This
check answers the question for the whole fleet in one pass, without running
anything.

── IT NEVER IMPORTS A CONTROL, AND THAT IS NOT A STYLE POINT ─────────────────
Most controls have no `if __name__ == "__main__"` guard, so **importing one runs
it**: it mutates a live source file, shells out, and restores the file at the
end. The first version of the tool this generalises did import. It hung, was
killed mid-run, and left a real source file modified on disk with an injected
line. A read-only checker must not be able to change the thing it inspects.

So: Python controls are read with `ast`. Everything else declares its mutations
in a sidecar the tool reads as data. Neither path executes anything.

── HOW A CONTROL DECLARES ITSELF ─────────────────────────────────────────────
**Python** -- a module-level list, read without importing:

    TARGET = 'src/app.py'
    MUTATIONS = [
        ('name', 'the exact anchor text', 'what to replace it with'),
        ('name', 'other/file.py', 'anchor', 'replacement'),
    ]

**Any language** -- a sidecar named after the control, `<control>.mutations.json`:

    {"target": "src/app.js",
     "mutations": [{"name": "arm1", "anchor": "if (ok) {", "replacement": "if (1) {"}]}

A control this tool cannot read is reported as **COULD NOT READ** and sets exit
2. It is never counted as clean, because "we could not check it" and "it is
fine" are the two answers this whole suite exists to keep apart.

── WHAT IT CANNOT SEE, said here rather than discovered later ────────────────
  * an anchor pointing at the WRONG branch while matching exactly once.
    Uniqueness is the only half a string match can check, and a real arm sat on
    the wrong branch of a function for weeks while matching once and reporting
    silent;
  * whether the mutation actually makes the suite fail. That is the control's
    own job and it needs to run the suite. This runs nothing and writes nothing.
"""
import ast
import io
import json
import os
import sys

from .config import ConfigError, load


def _literal(node):
    try:
        return ast.literal_eval(node)
    except Exception:                                    # noqa: BLE001
        return None


def read_python_control(path):
    """(module-level string constants, mutation entries) by PARSING, never importing."""
    tree = ast.parse(io.open(path, encoding='utf-8', errors='replace').read(), path)
    consts, muts = {}, []
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        tgt = node.targets[0]
        if not isinstance(tgt, ast.Name):
            continue
        if tgt.id == 'MUTATIONS' and isinstance(node.value, (ast.List, ast.Tuple)):
            for el in node.value.elts:
                if isinstance(el, (ast.Tuple, ast.List)):
                    muts.append([
                        ('@' + x.id) if isinstance(x, ast.Name) else _literal(x)
                        for x in el.elts])
            continue
        v = _literal(node.value)
        if isinstance(v, str):
            consts[tgt.id] = v
        elif (isinstance(node.value, ast.Call)
              and isinstance(node.value.func, ast.Attribute)
              and node.value.func.attr == 'join'):
            parts = [_literal(x) for x in node.value.args]
            parts = [x for x in parts if isinstance(x, str)]
            if parts:
                consts[tgt.id] = os.path.join(*parts)
    return consts, muts


def read_sidecar(path):
    """(target, entries) from `<control>.mutations.json`, or (None, None)."""
    side = os.path.splitext(path)[0] + '.mutations.json'
    if not os.path.isfile(side):
        return None, None
    d = json.load(io.open(side, encoding='utf-8'))
    out = []
    for m in d.get('mutations', []):
        out.append([m.get('name'), m.get('target') or d.get('target'),
                    m.get('anchor'), m.get('replacement')])
    return d.get('target'), out


def resolve(consts, entry, root, default_target=None):
    """(target_path, anchor) for one entry, or (None, anchor) when unresolved."""
    if len(entry) >= 4:
        target, anchor = entry[1], entry[2]
    else:
        target, anchor = consts.get('TARGET', default_target), entry[1]
    if isinstance(target, str) and target.startswith('@'):
        target = consts.get(target[1:])
    if not isinstance(target, str) or not isinstance(anchor, str):
        return None, anchor
    p = target if os.path.isabs(target) else os.path.join(root, target)
    return (p if os.path.isfile(p) else None), anchor


def run(cfg):
    controls = cfg.probes()
    if not controls:
        return None, 'no controls matched the config -- nothing was inspected'
    rows, unread = [], []
    for path in controls:
        consts, entries, default_target = {}, None, None
        if path.endswith('.py'):
            try:
                consts, entries = read_python_control(path)
            except SyntaxError as e:
                unread.append((cfg.rel(path), 'does not parse: %s' % e))
                continue
            if not entries:
                entries = None
        if not entries:
            default_target, entries = read_sidecar(path)
        if not entries:
            continue                     # not a declaring control; not a finding
        for entry in entries:
            name = entry[0] if entry and entry[0] else '(unnamed)'
            target, anchor = resolve(consts, entry, cfg.root, default_target)
            if target is None or not isinstance(anchor, str):
                unread.append((cfg.rel(path),
                               '%s: target or anchor could not be resolved' % name))
                continue
            body = io.open(target, encoding='utf-8', errors='replace').read()
            rows.append({'control': cfg.rel(path), 'arm': name,
                         'target': cfg.rel(target), 'count': body.count(anchor),
                         'anchor': anchor})
    return {'rows': rows, 'unread': unread, 'controls': len(controls)}, None


def main(argv):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:                                    # noqa: BLE001
        pass
    cfgpath = 'testint.config.json'
    if '--config' in argv:
        cfgpath = argv[argv.index('--config') + 1]
    try:
        cfg = load(cfgpath)
        result, why = run(cfg)
    except ConfigError as e:
        print('COULD NOT RUN: %s' % e)
        return 3
    if result is None:
        print('COULD NOT RUN: %s' % why)
        print('A check with nothing to look at has not passed.')
        return 3

    rows = result['rows']
    zero = [r for r in rows if r['count'] == 0]
    many = [r for r in rows if r['count'] > 1]
    print('MUTATION ANCHOR CHECK -- nothing was executed, nothing was written')
    print('  controls scanned  : %d' % result['controls'])
    print('  anchors checked   : %d' % len(rows))
    print('  ANCHOR-0          : %d  (the arm mutates nothing and passes)' % len(zero))
    print('  AMBIGUOUS (>1)    : %d  (the arm probes a site nobody chose)' % len(many))
    print('  COULD NOT READ    : %d  (NOT a pass -- see below)' % len(result['unread']))
    print('')
    for r in zero + many:
        print('  %-44s %s -> %s x%d' % (r['control'], r['arm'], r['target'], r['count']))
        print('      anchor: %r' % r['anchor'][:88])
    for path, why in result['unread']:
        print('  COULD NOT READ  %-40s %s' % (path, why))
    if not (zero or many or result['unread']):
        print('  Every anchor matches its target exactly once.')
    print('')
    print('Uniqueness is the only half a string match can check: an anchor on the '
          'WRONG branch')
    print('that still matches once reports clean. Read the arm, not just the count.')
    if result['unread']:
        return 2
    return 1 if (zero or many) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
