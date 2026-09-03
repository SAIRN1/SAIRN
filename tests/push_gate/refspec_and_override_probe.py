"""Probe the two push-gate defects found 2026-09-01 and fixed 2026-09-03.

  A. The gate diffed origin/main..HEAD no matter what the push command said, so
     `git push origin <sha>:main` was checked as if it pushed HEAD. An
     engine-only commit was DENIED for 13 New Hampshire rules sitting in a LATER
     seed commit it did not contain.
  B. SAIRN_SEED_GATE=off was read from os.environ only, which a PreToolUse hook
     cannot see when it is written as an inline prefix on the Bash command.

Driven by calling the hook's own functions and by feeding it a real PreToolUse
payload on stdin -- no network, no remote, and no dependence on the live
licence, so this runs identically in any clone at any time.

Every NEGATIVE arm matters more than the positive ones here: a fix to B that
also honours a quoted mention of the string would silently disable the whole
gate, and this repo's commit messages quote it in prose.
"""
import io
import json
import os
import subprocess
import sys
import tempfile

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()
sys.path.insert(0, os.path.join(REPO, 'tools'))
import sairn_push_gate_hook as H  # noqa: E402

FAIL = []


def check(name, got, want):
    if got == want:
        print("  PASS  %s" % name)
    else:
        print("  FAIL  %s\n          got:  %r\n          want: %r" % (name, got, want))
        FAIL.append(name)


# ── A1: pushed_tip parses the refspec shapes that actually occur ────────────
print("\nA1. pushed_tip() reads the ref the command really sends")
head = subprocess.run(['git', '-C', REPO, 'rev-parse', 'HEAD'],
                      capture_output=True, text=True).stdout.strip()
prev = subprocess.run(['git', '-C', REPO, 'rev-parse', 'HEAD~1'],
                      capture_output=True, text=True).stdout.strip()

check("bare `git push` -> HEAD", H.pushed_tip(REPO, 'git push'), 'HEAD')
check("`git push origin main` -> main", H.pushed_tip(REPO, 'git push origin main'), 'main')
check("`git push origin HEAD:main` -> HEAD",
      H.pushed_tip(REPO, 'git push origin HEAD:main'), 'HEAD')
check("THE 2026-09-01 CASE: `git push origin <sha>:main` -> that sha",
      H.pushed_tip(REPO, 'git push origin %s:main' % prev), prev)
check("flags are skipped, not taken as the remote",
      H.pushed_tip(REPO, 'git push --dry-run -u origin %s:main' % prev), prev)
check("`git push origin :branch` (a deletion) -> None",
      H.pushed_tip(REPO, 'git push origin :somebranch'), None)
check("an unresolvable ref falls back to HEAD, never worse than before",
      H.pushed_tip(REPO, 'git push origin no-such-ref-zzz:main'), 'HEAD')

# ── A2: the file list actually narrows to the pushed range ──────────────────
print("\nA2. outgoing_files() honours the tip, so a narrower push sees fewer files")
wide = H.outgoing_files(REPO, prev, head)
narrow = H.outgoing_files(REPO, prev, prev)
check("range base..HEAD is non-empty (fixture is valid)", bool(wide), True)
check("range base..base is empty -- the commit is not outgoing from itself",
      narrow, [])

# ── A3: export_sql_at reproduces sql/ as of a commit ────────────────────────
print("\nA3. export_sql_at() reads seeds from the commit, not the working tree")
d, note = H.export_sql_at(REPO, 'HEAD')
check("export produced a directory", bool(d) and os.path.isdir(d), True)
if d:
    exported = sorted(f for f in os.listdir(d) if f.endswith('.json'))
    on_disk = sorted(f for f in os.listdir(os.path.join(REPO, 'sql'))
                     if f.endswith('.json'))
    check("every committed seed json is present in the export",
          set(exported) <= set(on_disk) and len(exported) > 0, True)
    check("clean tree -> no divergence note", note, '')

bad, bad_note = H.export_sql_at(REPO, 'not-a-real-commit-zzz')
check("an unreadable tip returns no dir (caller falls back to the working tree)",
      bad, None)
check("...and says why rather than failing silently", bool(bad_note), True)


def seed_names_at(rev):
    out = subprocess.run(['git', '-C', REPO, 'ls-tree', '-r', '--name-only', rev, 'sql/'],
                         capture_output=True, text=True).stdout
    return sorted(os.path.basename(n) for n in out.split() if n.endswith('.json'))


# The arm that proves the export reads THE TIP and not HEAD. Comparing contents
# is not enough -- an implementation that lists HEAD's tree but reads blobs at
# the tip returns identical CONTENT and the wrong FILE SET, which is precisely
# the half that decides which apps get checked. So assert on the set, at a
# commit whose seed set genuinely differs from HEAD's.
here = seed_names_at('HEAD')
older = None
log = subprocess.run(['git', '-C', REPO, 'log', '--format=%H', '-n', '400', '--', 'sql/'],
                     capture_output=True, text=True).stdout.split()
for sha in log:
    if seed_names_at(sha) and seed_names_at(sha) != here:
        older = sha
        break
if older is None:
    print("  SKIP  no historical commit with a different seed set -- arm not run")
else:
    d2, _ = H.export_sql_at(REPO, older)
    got = sorted(f for f in os.listdir(d2)) if d2 else None
    check("export at an OLDER commit yields that commit's seed set, not HEAD's",
          got, seed_names_at(older))
    check("...and that set really is different from HEAD's (fixture is valid)",
          got != here, True)

# ── B: the override, reachable and not over-eager ───────────────────────────
print("\nB. override_in_command() -- the escape hatch that did not exist")
POS = [
    ("inline prefix, the documented spelling", 'SAIRN_SEED_GATE=off git push origin main'),
    ("quoted value", 'SAIRN_SEED_GATE="off" git push origin main'),
    ("single-quoted value", "SAIRN_SEED_GATE='off' git push origin main"),
    ("export then push", 'export SAIRN_SEED_GATE=off; git push origin main'),
    ("after &&", 'git fetch && SAIRN_SEED_GATE=off git push origin main'),
    ("case-insensitive value", 'SAIRN_SEED_GATE=OFF git push origin main'),
]
for name, cmd in POS:
    check("honoured: " + name, H.override_in_command(cmd), True)

NEG = [
    ("THE DANGEROUS ONE: the string quoted inside a commit message",
     'git commit -m "note about SAIRN_SEED_GATE=off" && git push origin main'),
    ("quoted in a single-quoted message",
     "git commit -m 'see SAIRN_SEED_GATE=off in the docs' && git push"),
    ("a value that is not off", 'SAIRN_SEED_GATE=on git push origin main'),
    ("mentioned mid-word, no assignment", 'git push  # SAIRN_SEED_GATE=offset'),
    ("no mention at all", 'git push origin main'),
]
for name, cmd in NEG:
    check("ignored: " + name, H.override_in_command(cmd), False)

# ── B2: end to end through the real PreToolUse entry point ──────────────────
# The unit above proves the matcher. This proves the hook WIRES it: a payload
# that would otherwise reach the checks exits 0 immediately with no deny.
print("\nB2. the hook itself honours an inline override on a real payload")


def run_hook(command):
    payload = json.dumps({"tool_input": {"command": command}})
    p = subprocess.run([sys.executable, os.path.join(REPO, 'tools', 'sairn_push_gate_hook.py')],
                       input=payload, capture_output=True, text=True, timeout=180, cwd=REPO)
    denied = '"permissionDecision": "deny"' in p.stdout
    return p.returncode, denied


rc, denied = run_hook('echo not a push')
check("a non-push command is ignored entirely", (rc, denied), (0, False))

# THE ARM MUST USE A COMMAND THE GATE REALLY REFUSES. The first version of this
# probe asserted that `SAIRN_SEED_GATE=off git push origin HEAD:main` was
# allowed -- which it is with or without the override, because HEAD is already
# on origin/main and nothing is outgoing. It passed while the override was
# unwired, and the negative control caught that the arm was vacuous.
#
# So: plant untracked SQL and use the combined commit+push shape, which denies
# deterministically with no network and no commit of its own.
probe_sql = os.path.join(REPO, 'sql', 'zz_probe_override_arm.sql')
CMD = 'git add sql/zz_probe_override_arm.sql && git commit -m probe && git push origin HEAD:main'
try:
    with open(probe_sql, 'w') as f:
        f.write('-- probe fixture, never committed\nselect 1;\n')
    rc, denied = run_hook(CMD)
    check("fixture is valid: the un-overridden push really is denied",
          (rc, denied), (0, True))
    rc, denied = run_hook('SAIRN_SEED_GATE=off ' + CMD)
    check("the same push with an inline override is ALLOWED", (rc, denied), (0, False))
    rc, denied = run_hook('git commit -m "mentions SAIRN_SEED_GATE=off" && ' + CMD)
    check("a quoted mention in a commit message does NOT disable the gate",
          (rc, denied), (0, True))
finally:
    if os.path.exists(probe_sql):
        os.remove(probe_sql)

# ── C: check 1 is actually GIVEN the exported dir ───────────────────────────
# The arms above prove the export is correct. This proves the hook HANDS IT TO
# THE CHECKER -- a link that is invisible from the outside, because check 1's
# real outcome depends on a live licence call this probe must not make.
#
# Done by running the hook inside a THROWAWAY git repo whose tools/ holds a stub
# checker that records its own argv. The hook resolves both the repo and the
# checker from the cwd, so nothing in the real clone is touched or stubbed.
print("\nC. check 1 receives --sql-dir pointing at the exported tip")


def sh(cwd, *a):
    return subprocess.run(list(a), cwd=cwd, capture_output=True, text=True)


sandbox = tempfile.mkdtemp(prefix='sairn-gate-probe-')
try:
    os.makedirs(os.path.join(sandbox, 'sql'))
    os.makedirs(os.path.join(sandbox, 'tools'))
    sh(sandbox, 'git', 'init', '-q', '-b', 'main')
    sh(sandbox, 'git', 'config', 'user.email', 'probe@example.invalid')
    sh(sandbox, 'git', 'config', 'user.name', 'probe')
    with open(os.path.join(sandbox, 'tools', 'sairn_load_state_check.py'), 'w') as f:
        # The stub records what it SAW, not just what it was told. The exported
        # dir is removed by the hook's atexit cleanup the moment it exits, so
        # inspecting it afterwards is impossible -- the first version of this
        # arm tried and read an empty path. Capturing from inside the checker is
        # also the stronger assertion: it is the reader's actual view.
        f.write("import sys, json, os\n"
                "d = sys.argv[sys.argv.index('--sql-dir') + 1] if '--sql-dir' in sys.argv else None\n"
                "seen = sorted(os.listdir(d)) if d and os.path.isdir(d) else None\n"
                "body = None\n"
                "if seen:\n"
                "    body = json.load(open(os.path.join(d, seen[0])))\n"
                "open(sys.argv[0] + '.argv', 'w').write(json.dumps(\n"
                "    {'argv': sys.argv[1:], 'seen': seen, 'body': body}))\n"
                "sys.exit(2)\n")  # exit 2 = could-not-tell, so the hook allows
    with open(os.path.join(sandbox, 'README'), 'w') as f:
        f.write('base\n')
    sh(sandbox, 'git', 'add', '-A')
    sh(sandbox, 'git', 'commit', '-q', '-m', 'base')
    base_sha = sh(sandbox, 'git', 'rev-parse', 'HEAD').stdout.strip()
    sh(sandbox, 'git', 'update-ref', 'refs/remotes/origin/main', base_sha)

    # A seed file whose path matches SEED_PATTERNS, so check 1 fires.
    seed_rel = 'sql/sairnlaw_deadline_seed_probe.json'
    with open(os.path.join(sandbox, seed_rel), 'w') as f:
        json.dump({"rules": [], "holiday_calendars": []}, f)
    sh(sandbox, 'git', 'add', '-A')
    sh(sandbox, 'git', 'commit', '-q', '-m', 'add probe seed')
    seed_sha = sh(sandbox, 'git', 'rev-parse', 'HEAD').stdout.strip()

    payload = json.dumps({"tool_input": {"command": "git push origin HEAD:main"}})
    p = subprocess.run([sys.executable, os.path.join(REPO, 'tools', 'sairn_push_gate_hook.py')],
                       input=payload, capture_output=True, text=True, cwd=sandbox, timeout=180)
    argv_file = os.path.join(sandbox, 'tools', 'sairn_load_state_check.py.argv')
    check("check 1 ran at all (fixture is valid)", os.path.exists(argv_file), True)
    rec = json.load(open(argv_file)) if os.path.exists(argv_file) else {}
    check("the checker was given --sql-dir", '--sql-dir' in rec.get('argv', []), True)
    check("...pointing at a real directory holding the PUSHED seed",
          rec.get('seen'), ['sairnlaw_deadline_seed_probe.json'])
    check("...whose content is the blob at the pushed tip",
          rec.get('body'), {"rules": [], "holiday_calendars": []})
    check("a could-not-tell result still allows the push", p.returncode, 0)
    check("...and says so rather than passing silently",
          'COULD NOT TELL' in p.stdout, True)

    # The narrowing, end to end: pushing the EARLIER commit must not run check 1
    # at all, because that commit contains no seed. This is the 2026-09-01 case.
    os.remove(argv_file)
    payload = json.dumps({"tool_input": {
        "command": "git push origin %s:main" % base_sha}})
    subprocess.run([sys.executable, os.path.join(REPO, 'tools', 'sairn_push_gate_hook.py')],
                   input=payload, capture_output=True, text=True, cwd=sandbox, timeout=180)
    check("THE 2026-09-01 CASE, end to end: pushing the pre-seed commit does not "
          "run the seed check even though the seed sits in HEAD",
          os.path.exists(argv_file), False)
finally:
    import shutil
    shutil.rmtree(sandbox, ignore_errors=True)

print("\n%d failure(s)" % len(FAIL))
if FAIL:
    for f in FAIL:
        print("  - " + f)
sys.exit(1 if FAIL else 0)
