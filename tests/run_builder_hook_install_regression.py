#!/usr/bin/env python
# OWNER: cc
"""tests/run_builder_hook_install_regression.py -- after an install, every
builder clone's installed hook copies are the LANDED tracked files, byte for
byte, and they enforce the scope the live manifests declare.

THE DRIFT CLASS THIS CLOSES (cc b66-b67). An installed copy can be wrong
while everything else looks right, in three different ways:

  * STALE. a367bd0c and 8c15c569 changed the hook after it had been
    installed, and the four copies kept enforcing the old version until a
    reinstall. In b67 cody's copy was held back on purpose.
  * NOT A COPY. The b66 Drive mirror was a text-mode copy that turned CRLF
    into LF, so a "copy" differed by 12 bytes and nothing compared the bytes.
  * RIGHT BYTES, WRONG SCOPE. The installed hook reads its scope at run time
    from that clone's docs/sairn-path-manifest.json and from
    ~/SAIRN-SESSION-LOCKS/hover-scope-manifest.json. Identical bytes reading
    an unreadable manifest enforce only the built-in floor, which the presence
    check reports as DEGRADED and nothing ASSERTS.

tools/builder_hook_presence.py compares git blob shas, which is the right
check for "is it the landed version". This test is the stricter, separate
question, asked after an install:

  R1  BYTES: each installed file equals `git show origin/main:tools/<f>`
      exactly. No newline normalisation; a byte copy is the contract.
  R2  SCOPE: each installed hook, IMPORTED FROM ITS INSTALLED PATH, computes
      the auditor dirs and the auditor-tracked list that the tracked tool
      computes from the SAME clone's manifests, and it read the live
      hover-scope manifest (not the floor).
  R3  BEHAVIOUR: on a fixed set of payloads, decide() of the installed copy
      equals decide() of the tracked tool, both refusals and allows.
  C1  CONTROL: R1's comparison flags a one-byte change, so a pass is not a
      comparison that cannot fail.

Exit: 0 all pass - 1 an arm FAILED - 2 COULD NOT RUN (no builder clones, no
origin/main copy, an import that fails).

    python tests/run_builder_hook_install_regression.py
"""
import importlib.util
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
try:
    import builder_hook_presence as P
    import builder_auditor_deny_hook as TRACKED
except Exception as e:                                          # noqa: BLE001
    print('COULD NOT RUN: the tracked tools did not import: %s' % e)
    sys.exit(2)

passed, failed = [0], []


def arm(name, ok, got=None):
    if ok:
        passed[0] += 1
        print('  ok   ' + name)
    else:
        failed.append(name)
        print('  FAIL %s%s' % (name, '' if got is None else '   got %r' % (got,)))


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    try:
        clones, absent = P.builders(REPO)
        ref, ref_from = P.reference(clones)
    except P.CouldNotRun as e:
        print('COULD NOT RUN: %s' % e)
        return 2
    print('BUILDER HOOK INSTALL REGRESSION -- %d clone(s), reference origin/main in %s'
          % (len(clones), ref_from))
    hover_manifest = TRACKED.HOVER_SCOPE_MANIFEST
    for name in sorted(clones):
        clone = clones[name]
        # R1 BYTES
        for f in P.FILES:
            p = os.path.join(clone, P.COPY_DIR, f)
            try:
                got = open(p, 'rb').read()
            except OSError as e:
                arm('R1 %s %s is installed' % (name, f), False, str(e))
                continue
            arm('R1 %s %s == origin/main byte for byte' % (name, f), got == ref[f][1],
                (len(got), len(ref[f][1])))
        # R2 SCOPE
        try:
            inst = load(os.path.join(clone, P.COPY_DIR, P.HOOK), 'installed_hook_%s' % name)
        except Exception as e:                                  # noqa: BLE001
            print('COULD NOT RUN: the installed hook in %s does not import: %s' % (name, e))
            return 2
        clone_manifest = os.path.join(clone, 'docs', 'sairn-path-manifest.json')
        want_dirs = tuple(sorted(set(TRACKED.BUILTIN_AUDITOR_DIRS)
                                 | set(TRACKED.manifest_auditor_paths(clone_manifest) or ())))
        want_tracked, _ = TRACKED.tracked_auditor_paths(hover_manifest, clone_manifest)
        arm('R2 %s installed hook reads THIS clone\'s path manifest' % name,
            os.path.normcase(os.path.abspath(inst.MANIFEST)) == os.path.normcase(os.path.abspath(clone_manifest)),
            inst.MANIFEST)
        arm('R2 %s auditor dirs match the live path manifest' % name, inst.AUDITOR_DIRS == want_dirs,
            (inst.AUDITOR_DIRS, want_dirs))
        arm('R2 %s auditor-tracked list matches the live hover-scope manifest' % name,
            inst.AUDITOR_TRACKED == want_tracked, (inst.AUDITOR_TRACKED, want_tracked))
        arm('R2 %s read the live hover-scope manifest (not the floor alone)' % name, inst.HOVER_MANIFEST_READ is True)
        # R3 BEHAVIOUR
        cwd = clone
        skill = os.path.join(clone, '.claude', 'skills', 'sairn-' + 'hov' + 'er-auditor', 'SKILL.md')
        cases = [
            {'tool_name': 'Edit', 'tool_input': {'file_path': skill}, 'cwd': cwd},
            {'tool_name': 'Edit', 'tool_input': {'file_path': os.path.join(clone, 'tools', 'hover_separation_ci.py')}, 'cwd': cwd},
            {'tool_name': 'Bash', 'tool_input': {'command': 'git checkout -- tools/hover_separation_ci.py'}, 'cwd': cwd},
            {'tool_name': 'Bash', 'tool_input': {'command': 'python tools/hover_separation_audit.py --help'}, 'cwd': cwd},
            {'tool_name': 'Edit', 'tool_input': {'file_path': os.path.join(clone, 'tools', 'tooling_inventory.py')}, 'cwd': cwd},
            {'tool_name': 'Bash', 'tool_input': {'command': 'git status'}, 'cwd': cwd},
        ]
        same = [bool(inst.decide(c)) == bool(TRACKED.decide(c)) for c in cases]
        arm('R3 %s installed decide() == tracked decide() on %d payloads' % (name, len(cases)), all(same), same)
        expect = [True, True, True, False, False, False]
        arm('R3 %s ...and the verdicts are the intended ones (3 refused, 3 allowed)' % name,
            [bool(inst.decide(c)) for c in cases] == expect, [bool(inst.decide(c)) for c in cases])
    # C1 CONTROL
    f = P.FILES[0]
    tampered = bytearray(ref[f][1])
    tampered[len(tampered) // 2] ^= 1
    arm('C1 a one-byte change is NOT equal (the R1 comparison can fail)', bytes(tampered) != ref[f][1])
    print('\n%d passed, %d failed' % (passed[0], len(failed)))
    if failed:
        print('FAILING: ' + '; '.join(failed))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
