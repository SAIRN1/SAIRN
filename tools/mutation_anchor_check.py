"""Does every mutation probe's anchor still match its target EXACTLY ONCE?

WHY. A mutation probe reintroduces a defect, asserts the suite goes red, and
restores the file. Its anchor is an exact string. When the target is refactored
the anchor stops matching, and the arm stops testing:

  * MATCHES ZERO TIMES -- loud. tests/dnt_vendor_write_confirmation_probe.py arm
    4 expected an `}else if(storeKey){` that a refactor had collapsed into a flat
    `if`. Its own harness reported ANCHOR-0 and failed. Nobody fixed it for a
    day, but it was saying so.
  * MATCHES MORE THAN ONCE -- also loud, and already the reason one arm in that
    same file carries a note: an anchor shared by two writers probed neither.

BOTH OF THOSE ARE CAUGHT BY EACH PROBE'S OWN HARNESS, WHEN IT RUNS. This tool
exists because that is a weaker guarantee than it sounds:

  * a probe only checks its own anchors, and only when something runs it. Four of
    the six could not be swept at all on 2026-09-11 because they declare their
    target differently -- so "they pass in the full suite" was the strongest
    claim available, which is not the same as "their anchors were verified";
  * an anchor that has drifted onto DIFFERENT code while still matching exactly
    once is invisible to the uniqueness check. That is not detectable here
    either -- said plainly below rather than implied away.

WHAT IT DOES. PARSES every tests/*_probe.py that defines MUTATIONS -- with ast,
never importing it -- resolves the target file for each arm, and counts the
anchor. It does not import because IMPORTING A PROBE RUNS IT: most have no
`if __name__ == "__main__"` guard, so an import mutates a live source file,
shells out to node, and restores it at the end. The first version of this tool
did import, hung, was killed mid-probe, and left api/_lib/dental-guardian.js
modified on disk. A read-only checker must not be able to change the thing it
inspects. Two declaration shapes
exist in this repo and both are handled rather than normalised, because
rewriting six probes to suit a checker is the tail wagging the dog:

    (name, old, new)          -> the module-level TARGET
    (name, FILE, old, new)    -> FILE, as given

WHAT IT CANNOT SEE, said here rather than discovered later:
  * an anchor pointing at the WRONG branch while matching exactly once. On
    2026-09-11 that cost a real arm: a six-space anchor sat on the
    missing-fields branch of dntPushOne() instead of the refused branch it was
    named for, matched once, and reported SILENT for weeks. Uniqueness is the
    only half a string match can check;
  * whether the mutation actually makes the suite fail -- that is the probe's
    own job, and it needs to run the suite. This never runs anything and never
    writes anything;
  * a probe that builds its MUTATIONS list at run time rather than declaring it.

Usage:
    python tools/mutation_anchor_check.py
    python tools/mutation_anchor_check.py --json

Exit 0 when every anchor matches exactly once, 1 when one does not, 2 when a
probe could not be read at all -- which is not a pass.
"""
import ast
import glob
import io
import re
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def literal(node):
    """The constant value of an AST node, or None if it is not a plain literal."""
    try:
        return ast.literal_eval(node)
    except Exception:
        return None


def read_probe(path):
    """(module-level string assignments, MUTATIONS entries) by PARSING, never importing.

    THIS TOOL IMPORTED THE PROBES ON ITS FIRST RUN AND THAT WAS A REAL HAZARD,
    not a style point. Most probes in tests/ have no `if __name__ == "__main__"`
    guard, so importing one RUNS it: it mutates a live source file, shells out to
    node, and restores the file at the end. The first run of this checker hung on
    that and was killed mid-probe, which left `api/_lib/dental-guardian.js`
    modified on disk with an injected `if (r.zz_probe_field) return "probe";`.
    Restored by hand, verified clean, and the tool rewritten to parse instead.

    A read-only checker must not be able to change the thing it inspects.
    """
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
                    muts.append([literal(x) if not isinstance(x, ast.Name) else ('@' + x.id)
                                 for x in el.elts])
            continue
        v = literal(node.value)
        if isinstance(v, str):
            consts[tgt.id] = v
        elif (isinstance(node.value, ast.Call) and
              isinstance(node.value.func, ast.Attribute) and
              node.value.func.attr == 'join'):
            # os.path.join('a', 'b') -- resolved as a relative path. A ROOT
            # argument is dropped: every path here is resolved against REPO
            # anyway, and ROOT is not a literal this parser can see.
            parts = [literal(x) for x in node.value.args]
            parts = [x for x in parts if isinstance(x, str)]
            if parts:
                consts[tgt.id] = os.path.join(*parts)
    return consts, muts


def resolve(consts, entry):
    """(target_path, old) for one MUTATIONS entry, or (None, old) if unresolved."""
    if len(entry) >= 4:
        target, old = entry[1], entry[2]
    else:
        target, old = consts.get('TARGET'), entry[1]
    if isinstance(target, str) and target.startswith('@'):
        target = consts.get(target[1:])      # the entry named a module constant
    if not isinstance(target, str) or not isinstance(old, str):
        return None, old
    p = target if os.path.isabs(target) else os.path.join(REPO, target)
    return (p if os.path.exists(p) else None), old



def mutates_repo_path(body):
    """True if this probe opens a REPO/ROOT-derived path for binary writing.

    Parsed, never grepped: see the note at the call site for why that matters.
    """
    try:
        tree = ast.parse(body)
    except SyntaxError:
        return False
    repo_names = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Attribute)
                and node.value.func.attr == 'join'
                and node.value.args
                and isinstance(node.value.args[0], ast.Name)
                and node.value.args[0].id in ('REPO', 'ROOT')):
            repo_names.add(node.targets[0].id)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, 'id', None)
        if name != 'open' or len(node.args) < 2:
            continue
        mode = node.args[1]
        if not (isinstance(mode, ast.Constant) and mode.value == 'wb'):
            continue
        tgt = node.args[0]
        if isinstance(tgt, ast.Name) and tgt.id in repo_names:
            return True
    return False


def main(argv):
    rows, unreadable = [], []
    cache = {}
    for path in sorted(glob.glob(os.path.join(REPO, 'tests', '**', '*_probe.py'), recursive=True)):
        rel = os.path.relpath(path, REPO).replace(os.sep, '/')
        try:
            consts, muts = read_probe(path)
        except Exception as e:
            unreadable.append((rel, '%s: %s' % (type(e).__name__, str(e)[:60])))
            continue
        if not muts:
            continue               # not a mutation probe; nothing to check
        for entry in muts:
            target, old = resolve(consts, entry)
            if not target:
                unreadable.append((rel, 'arm %r: target unresolved' % str(entry[0])[:40]))
                continue
            if target not in cache:
                cache[target] = io.open(target, encoding='utf-8', errors='replace').read()
            n = cache[target].count(old)
            rows.append({'probe': rel,
                         'target': os.path.relpath(target, REPO).replace('\\', '/'),
                         'arm': str(entry[0])[:70], 'matches': n})

    # -- SECOND SECTION: a probe that mutates a tracked file IN PLACE must
    # refuse an import. Same family as a stale anchor -- both are a probe
    # being unsafe to touch in a way nothing announces. See the docstring
    # for the live incident that produced this.
    unguarded = []
    for path in sorted(glob.glob(os.path.join(REPO, 'tests', '**', '*_probe.py'),
                                 recursive=True)):
        rel = os.path.relpath(path, REPO).replace('\\\\', '/')
        body = io.open(path, encoding='utf-8', errors='replace').read()
        # DETECTED BY PARSING, NOT BY GREP, AND THE THIRD VERSION IS THE FIRST
        # CORRECT ONE. v1 flagged any `open(x, "wb")` and caught six probes that
        # write only into a temp worktree -- the safe pattern. v2 narrowed to a
        # target built from REPO/ROOT and then flagged THIS TOOL'S OWN PROBE,
        # because that probe contains the unsafe pattern as a FIXTURE STRING.
        # A checker matching a quoted example instead of live code is the exact
        # class tools/comment_quote_check.py exists for -- third instance in two
        # days, and this time in the tool written the same week. ast cannot see
        # inside a string literal, so parsing removes the class rather than
        # patching the symptom.
        in_place = mutates_repo_path(body)
        if not in_place:
            continue
        guarded = any(m in body for m in (
            "__name__ == '__main__'",
            '__name__ == "__main__"',
            "__name__ != '__main__'"))
        if not guarded:
            unguarded.append(rel)

    bad = [r for r in rows if r['matches'] != 1]
    by_probe = {}
    for r in rows:
        by_probe.setdefault(r['probe'], []).append(r)

    if '--json' in argv:
        print(json.dumps({'arms': rows, 'unreadable': unreadable}, indent=1))
    else:
        print('MUTATION ANCHOR CHECK -- report only, nothing was run and nothing written')
        print('  probes with a MUTATIONS list : %d' % len(by_probe))
        print('  anchors checked              : %d' % len(rows))
        print('  anchors NOT matching exactly once: %d' % len(bad))
        print('  could not read               : %d  (NOT a pass)' % len(unreadable))
        for p in sorted(by_probe):
            arms = by_probe[p]
            b = sum(1 for a in arms if a['matches'] != 1)
            print('    %-46s arms=%-3d bad=%d' % (p, len(arms), b))
        for r in bad:
            print('\n  %s' % r['probe'])
            print('      ANCHOR-%d in %s' % (r['matches'], r['target']))
            print('      %s' % r['arm'])
            print('      zero means the target was refactored; more than one means the'
                  ' arm probes whichever came first, i.e. neither on purpose.')
        for p, why in unreadable:
            print('\n  COULD NOT READ  %s' % p)
            print('      %s' % why)
        print('')
        print('  probes that mutate in place and do NOT refuse an import: %d'
              % len(unguarded))
        for u in unguarded:
            print('      %s' % u)
        if unguarded:
            print('      An import RUNS these, and an interrupted import leaves the')
            print('      mutation on disk. Add at the top:')
            print('          if __name__ != "__main__": raise RuntimeError(...)')
        print('\n  NOTE: this checks that an anchor matches ONCE. It cannot tell whether')
        print('  it matches the RIGHT code -- an anchor that drifts onto a different')
        print('  branch stays unique and stays invisible here. See the module docstring.')

    if unreadable:
        return 2
    return 1 if (bad or unguarded) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
