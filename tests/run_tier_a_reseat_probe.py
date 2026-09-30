r"""tests/run_tier_a_reseat_probe.py -- control pair for
tools/tier_a_review_gate.py --reseat-shas.

    python tests/run_tier_a_reseat_probe.py

CONTROLS_FOR = ['tools/tier_a_review_gate.py']
LIVE_PROBE_CLASS = 'FIXTURE'

WHY, AND IT IS A GAP MEASURED TWICE BY DISCHARGING REAL OBLIGATIONS. `--list`
reports a record whose recorded sha no longer resolves as **COULD-NOT-TELL --
rebased away without a reseat**, and there was no reseat. `--backfill-shas` does
NOT cover it: it fills a sha that is MISSING and reports "0 with no sha" while a
record sits there present-and-dangling. Present-and-dangling is a third state and
neither command owned it.

Hit on 2026-09-26T01:43:54Z (sha 59e85d77, real commit 9ff4b87f) and again on
2026-09-27T02:17:49Z (sha 191d2dce, real commit c123a925). Both were resolved BY
HAND, by matching the record's file list and subject against the log -- which is
the algorithm this command now performs, and which nobody should be performing by
hand twice.

THE DURABLE KEY IS THE FILE LIST, NOT THE SUBJECT. `defect_register.py --reseat`
matches on subject because its records store one. A review record does not: it
stores `files`, `resources`, `what` and `opened_at`. So the match is the CHANGED
FILE SET, narrowed by time, and the ambiguity rules below are what make that safe.

THE KNOWN-BAD CONTROLS, and every one must REFUSE:

  a record whose sha is REACHABLE            -> not touched at all
  a file list matching TWO commits           -> REFUSED as ambiguous, named
  a file list matching NO commit             -> REFUSED, named
  no --write                                 -> DRY RUN, nothing written
  a reseated record                           -> carries a marker, so a reseated
                                                sha and a stamped one are never
                                                indistinguishable
"""
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'tools'))

EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN = 0, 1, 2

TOOL = os.path.join(REPO, 'tools', 'tier_a_review_gate.py')
if not os.path.isfile(TOOL):
    print('COULD NOT RUN: tools/tier_a_review_gate.py is not on disk. This '
          'control tested nothing, which is a third state and not a pass.')
    sys.exit(EXIT_COULD_NOT_RUN)

NL = chr(10)
passed = failed = 0


def ok(cond, label, detail=''):
    global passed, failed
    if cond:
        passed += 1
        print('  ok   %s' % label)
    else:
        failed += 1
        print('  FAIL %s' % label)
        if detail:
            print('       %s' % str(detail)[:600])


def rmtree(path):
    def onerror(fn, p, exc):
        try:
            os.chmod(p, stat.S_IWRITE)
            fn(p)
        except Exception:
            pass
    shutil.rmtree(path, onerror=onerror)


def g(cwd, *args):
    return subprocess.run(
        ['git', '-c', 'user.name=probe', '-c', 'user.email=probe@local',
         '-c', 'commit.gpgsign=false'] + list(args),
        cwd=cwd, capture_output=True, text=True, encoding='utf-8',
        errors='replace')


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    io.open(path, 'w', encoding='utf-8', newline='\n').write(text)


def build_fixture():
    """A repo with real commits, and a review ledger whose shas are dangling.

    THE COMMITS ARE REAL AND SO IS THE REBASE. A fixture that wrote a fake sha
    into the ledger would exercise the string comparison and not the question --
    whether a rewritten commit can be found again from what the record kept.
    """
    d = tempfile.mkdtemp(prefix='sairn_reseat_')
    g(d, 'init', '-q', '-b', 'main')
    os.makedirs(os.path.join(d, 'tools'), exist_ok=True)
    # EVERY MODULE THE TOOL IMPORTS, not just the tool. The first run of this
    # probe failed on ModuleNotFoundError for sairn_session_identity and reported
    # it as "the record was NOT reseated" -- an import error wearing a behaviour
    # finding's clothes, which is the shape that makes a control lie about its
    # subject. Derived from the tool's own import lines rather than listed.
    gate_src = io.open(os.path.join(REPO, 'tools', 'tier_a_review_gate.py'),
                       encoding='utf-8').read()
    local = set(re.findall(r'^import ([a-z_][a-z0-9_]*)', gate_src, re.M))
    local |= set(re.findall(r'^from ([a-z_][a-z0-9_]*) import', gate_src, re.M))
    needed = {'tier_a_review_gate.py'}
    for m in sorted(local):
        cand = os.path.join(REPO, 'tools', m + '.py')
        if os.path.isfile(cand):
            needed.add(m + '.py')
    # and one hop out from those, since checker_kit imports siblings too
    for t in sorted(needed):
        body = io.open(os.path.join(REPO, 'tools', t), encoding='utf-8',
                       errors='replace').read()
        mods = set(re.findall(r'^import ([a-z_][a-z0-9_]*)', body, re.M))
        mods |= set(re.findall(r'^from ([a-z_][a-z0-9_]*) import', body, re.M))
        for m in mods:
            cand = os.path.join(REPO, 'tools', m + '.py')
            if os.path.isfile(cand):
                needed.add(m + '.py')
    for t in sorted(needed):
        shutil.copyfile(os.path.join(REPO, 'tools', t),
                        os.path.join(d, 'tools', t))
    write(os.path.join(d, 'seed.txt'), 'seed' + NL)
    g(d, 'add', '.')
    g(d, 'commit', '-q', '-m', 'seed')

    # ── The commit a record will point at, on a branch, then REBASED so its sha
    # really changes. This is the whole situation being repaired.
    g(d, 'checkout', '-q', '-b', 'side')
    write(os.path.join(d, 'app.html'), 'one' + NL)
    write(os.path.join(d, 'tests', 'app_arm.js'), 'arm' + NL)
    g(d, 'add', 'app.html', 'tests/app_arm.js')
    g(d, 'commit', '-q', '-m', 'the change a record was opened for')
    pre = g(d, 'rev-parse', 'HEAD').stdout.strip()

    g(d, 'checkout', '-q', 'main')
    write(os.path.join(d, 'unrelated.txt'), 'other session' + NL)
    g(d, 'add', 'unrelated.txt')
    g(d, 'commit', '-q', '-m', 'another session pushed first')
    g(d, 'checkout', '-q', 'side')
    g(d, 'rebase', '-q', 'main')
    post = g(d, 'rev-parse', 'HEAD').stdout.strip()
    g(d, 'checkout', '-q', 'main')
    g(d, 'merge', '-q', '--ff-only', 'side')

    # A SECOND commit touching the SAME file set, so one fixture record is
    # genuinely ambiguous. Without it the ambiguity arm would be theoretical.
    write(os.path.join(d, 'app.html'), 'two' + NL)
    write(os.path.join(d, 'tests', 'app_arm.js'), 'arm two' + NL)
    g(d, 'add', 'app.html', 'tests/app_arm.js')
    g(d, 'commit', '-q', '-m', 'the same two files again, later')

    # ── A COMMIT WITH A DISTINCT SUBJECT, REBASED AWAY, WHOSE DIFF TOUCHES
    #    FILES NO RECORD WILL NAME. This is the cross-check fixture: a record
    #    stamped with THIS sha but naming other files must be REFUSED, because
    #    following it to its rebased twin would preserve a mis-stamp.
    g(d, 'checkout', '-q', '-b', 'side2')
    write(os.path.join(d, 'docs_note.md'), 'a note' + NL)
    g(d, 'add', 'docs_note.md')
    g(d, 'commit', '-q', '-m', 'a documentation note and nothing else')
    disjoint_pre = g(d, 'rev-parse', 'HEAD').stdout.strip()
    g(d, 'checkout', '-q', 'main')
    write(os.path.join(d, 'unrelated2.txt'), 'yet another session' + NL)
    g(d, 'add', 'unrelated2.txt')
    g(d, 'commit', '-q', '-m', 'a third session pushed in between')
    g(d, 'checkout', '-q', 'side2')
    g(d, 'rebase', '-q', 'main')
    disjoint_post = g(d, 'rev-parse', 'HEAD').stdout.strip()
    g(d, 'checkout', '-q', 'main')
    g(d, 'merge', '-q', '--ff-only', 'side2')

    # ── A COMMIT THAT TOUCHED THREE FILES, one of which a record will name
    #    alone -- the FILE-SET SUBSET basis, which must not be applied by
    #    --write on its own.
    write(os.path.join(d, 'widget.py'), 'w' + NL)
    write(os.path.join(d, 'widget_probe.py'), 'p' + NL)
    write(os.path.join(d, 'widget_doc.md'), 'd' + NL)
    g(d, 'add', 'widget.py', 'widget_probe.py', 'widget_doc.md')
    g(d, 'commit', '-q', '-m', 'a three-file change a record will under-name')
    subset_target = g(d, 'rev-parse', 'HEAD').stdout.strip()
    subset_when = g(d, 'log', '-1', '--format=%cI').stdout.strip()

    reachable = g(d, 'rev-parse', 'HEAD').stdout.strip()
    return (d, pre, post, reachable, disjoint_pre, disjoint_post,
            subset_target, subset_when)


def ledger(pre, reachable, disjoint_pre=None, subset_when=None):
    extra = []
    if disjoint_pre:
        # 4. THE CROSS-CHECK RECORD. Its sha resolves and has a unique subject
        #    twin on main, and that twin's diff touches NONE of the files named
        #    here. Subject-twin matching ALONE would reseat this onto the wrong
        #    commit -- which is what it did to two real records before the
        #    cross-check existed.
        extra.append(
            {'author_session': 'cc', 'opened_at': '2026-09-27T00:00:00Z',
             'opened_at_sha': disjoint_pre, 'status': 'open',
             'resources': ['mis_stamped'],
             'files': ['app.html', 'tests/app_arm.js'],
             'what': 'stamped with whatever HEAD was, not with the work',
             'reviewer_owner': 'hank', 'reviewer_session': None,
             'reviewed_at': None, 'verdict': None, 'rules': []})
    if subset_when:
        # 5. THE SUBSET RECORD. It under-names a three-file commit and its sha
        #    does not resolve, so only containment can find it.
        extra.append(
            {'author_session': 'cc', 'opened_at': subset_when, 'status': 'open',
             'opened_at_sha': 'f' * 40,
             'resources': ['widget'], 'files': ['widget.py'],
             'what': 'named one file out of three',
             'reviewer_owner': 'hank', 'reviewer_session': None,
             'reviewed_at': None, 'verdict': None, 'rules': []})
    return {
        'records': [
            # 1. DANGLING, one match by file set -> reseatable
            {'author_session': 'cc', 'opened_at': '2026-09-27T00:00:00Z',
             'opened_at_sha': pre, 'status': 'open',
             'resources': ['app_thing'],
             'files': ['app.html', 'tests/app_arm.js'],
             'what': 'the change a record was opened for',
             'reviewer_owner': 'hank', 'reviewer_session': None,
             'reviewed_at': None, 'verdict': None, 'rules': []},
            # 2. REACHABLE -> must not be touched
            {'author_session': 'cc', 'opened_at': '2026-09-27T00:00:00Z',
             'opened_at_sha': reachable, 'status': 'open',
             'resources': ['other_thing'], 'files': ['app.html'],
             'what': 'already fine', 'reviewer_owner': 'hank',
             'reviewer_session': None, 'reviewed_at': None, 'verdict': None,
             'rules': []},
            # 3. DANGLING, file set matches NOTHING -> refused
            {'author_session': 'cc', 'opened_at': '2026-09-27T00:00:00Z',
             'opened_at_sha': '0' * 40, 'status': 'open',
             'resources': ['ghost'], 'files': ['never_existed.html'],
             'what': 'no such commit', 'reviewer_owner': 'hank',
             'reviewer_session': None, 'reviewed_at': None, 'verdict': None,
             'rules': []},
        ] + extra
    }


def run(d, *args):
    p = subprocess.run([sys.executable, os.path.join(d, 'tools',
                                                     'tier_a_review_gate.py')]
                       + list(args), cwd=d, capture_output=True, text=True,
                       encoding='utf-8', errors='replace',
                       env=dict(os.environ, PYTHONIOENCODING='utf-8'))
    return p.returncode, (p.stdout or '') + (p.stderr or '')


print('CONTROL PAIR -- tier_a_review_gate.py --reseat-shas' + NL)

(d, pre, post, reachable, disjoint_pre, disjoint_post, subset_target,
 subset_when) = build_fixture()
LEDGER = os.path.join(d, 'docs', 'tier-a-reviews.json')
try:
    # ── NO ARM LABEL CARRIES A SHA, AND THAT IS NOT COSMETIC (2026-09-29).
    # Three labels here used to interpolate the fixture's shas, which are NEW ON
    # EVERY RUN. A both-ways mutation harness pairs arms BY LABEL, so three
    # value-only arms -- including this one, which compares two shas and cannot
    # depend on any wording -- were uncomparable across runs and came back as
    # "did not run". An arm nobody can pair across two runs cannot be
    # mutation-tested at all. The shas moved into the DETAIL, which prints only
    # on failure and is not part of the arm's identity.
    ok(pre != post,
       'FIXTURE VALIDITY: the rebase really changed the sha, so the record is '
       'genuinely dangling rather than merely written wrong',
       'pre %s -> post %s' % (pre[:8], post[:8]))
    ok(g(d, 'cat-file', '-t', pre).returncode == 0
       or True, 'the pre-rebase sha may or may not still be a dangling object -- '
       'either way it is NOT an ancestor of main, which is the question')
    anc = g(d, 'merge-base', '--is-ancestor', pre, 'main').returncode
    ok(anc != 0,
       'and it is NOT reachable from main -- RESOLVABLE IS NOT REACHABLE, which '
       'is the distinction defect_register.py records learning the hard way')

    # ── DRY RUN FIRST ──────────────────────────────────────────────────────
    print(NL + 'DIRECTION -- dry run writes nothing')
    write(LEDGER, json.dumps(ledger(pre, reachable), indent=1))
    before = io.open(LEDGER, encoding='utf-8').read()
    rc, out = run(d, '--reseat-shas')
    after = io.open(LEDGER, encoding='utf-8').read()
    ok(after == before,
       'the ledger is byte-identical after a run with no --write (exit %d)' % rc,
       out[-500:])
    ok('DRY RUN' in out.upper(),
       'and it says so rather than looking like it acted', out[-400:])

    # ── THE THREE OUTCOMES, NAMED ──────────────────────────────────────────
    print(NL + 'DIRECTION -- one reseatable, one reachable, one refused')
    ok(post[:12] in out,
       'the reseatable record is matched to the REWRITTEN commit',
       'expected %s in the output; tail: %s' % (post[:12], out[-600:]))
    ok('never_existed.html' in out or 'ghost' in out,
       'the record whose file set matches NOTHING is named, not skipped in '
       'silence', out[-700:])
    ok(reachable[:12] not in out.replace(post[:12], ''),
       'and the REACHABLE record is not proposed for anything -- a reseat that '
       'touched a healthy record would rewrite history nobody asked about',
       out[-700:])

    # ── KNOWN-BAD: AMBIGUITY MUST REFUSE ───────────────────────────────────
    print(NL + 'KNOWN-BAD -- a file set matching TWO commits is REFUSED')
    amb = ledger(pre, reachable)
    # Both app.html-and-arm commits match this file set, so the answer is two.
    amb['records'][0]['files'] = ['app.html', 'tests/app_arm.js']
    amb['records'][0]['what'] = 'ambiguous on purpose'
    # ── AND THE SHA MUST NOT RESOLVE, OR THIS ARM STOPS TESTING AMBIGUITY.
    # When the subject-twin basis landed, this fixture's dangling-but-resolvable
    # sha let a STRONGER basis answer first and the arm went green while
    # asserting nothing about ambiguity. A control that a later, correct change
    # silently disarms is exactly the item-8 shape, caught here by the arm
    # failing rather than by anybody noticing.
    amb['records'][0]['opened_at_sha'] = 'a' * 40
    write(LEDGER, json.dumps(amb, indent=1))
    rc, out = run(d, '--reseat-shas', '--write')
    doc = json.loads(io.open(LEDGER, encoding='utf-8').read())
    ok('AMBIGUOUS' in out.upper() or 'more than one' in out.lower(),
       'it says the match is ambiguous', out[-700:])
    # ── AND THE SAME THING WITHOUT PINNING A SENTENCE (2026-09-29).
    # A both-ways mutation removed the ambiguity refusal and exactly ONE arm
    # caught it -- the one above, which asserts on the WORD "ambiguous". The
    # behavioural arm below it could not: with that branch gone the record fell
    # through to the SUBSET refusal, which refused it too, so the sha was
    # unchanged and the behaviour arm still passed. The only difference was the
    # REASON, and the reason lived in prose. `--json` now emits a stable reason
    # CODE per refusal, so this arm survives any rewording of the sentence and
    # still fails if a different refusal fires.
    rcj, outj = run(d, '--reseat-shas', '--json')
    i = outj.find('{')
    codes = []
    if i >= 0:
        try:
            payload = json.loads(outj[i:outj.rindex('}') + 1])
            codes = [x.get('code') for x in payload.get('refused', [])]
        except Exception as exc:
            codes = ['PARSE FAILED: %s' % exc]
    ok('AMBIGUOUS_EXACT_SET' in codes,
       'THE SAME FACT AS A CODE RATHER THAN A SENTENCE: --json reports the '
       'refusal as AMBIGUOUS_EXACT_SET, so this arm cannot be broken by '
       'rewording the message and cannot be satisfied by a DIFFERENT refusal '
       'firing -- which is exactly what a mutation showed the prose arm could '
       'not distinguish', codes)
    ok(doc['records'][0]['opened_at_sha'] == 'a' * 40,
       'AND THE SHA IS UNCHANGED -- picking one of two candidates would be a '
       'guess written into a ledger an auditor follows', out[-500:])

    # ── THE HAPPY PATH, WITH --write, and the marker ────────────────────────
    print(NL + 'DIRECTION -- --write reseats, and marks what it reseated')
    lg = ledger(pre, reachable)
    lg['records'][0]['what'] = 'the change a record was opened for'
    # Disambiguate by naming the subject too, which is the second key.
    write(LEDGER, json.dumps(lg, indent=1))
    rc, out = run(d, '--reseat-shas', '--write')
    doc = json.loads(io.open(LEDGER, encoding='utf-8').read())
    r0 = doc['records'][0]
    if r0['opened_at_sha'] != pre:
        ok(r0['opened_at_sha'] == post,
           'the dangling sha is replaced with the REWRITTEN commit', r0)
        ok(r0.get('opened_at_sha_reseated') is True,
           'and the record carries a RESEATED marker, so a reseated sha and one '
           'stamped at open time are never indistinguishable -- the same rule '
           'backfill_shas already follows for its own reconstruction', r0)
        ok(doc['records'][1]['opened_at_sha'] == reachable,
           'and the reachable record is untouched', doc['records'][1])
    else:
        ok(False, 'the reseatable record was NOT reseated even with --write',
           out[-900:])

    # ══ THE SUBJECT TWIN, AND THE CROSS-CHECK THAT STOPS IT BEING WRONG ══
    print(NL + 'SUBJECT TWIN -- the strongest basis, and the check that bounds it')
    lg = ledger(pre, reachable, disjoint_pre, subset_when)
    write(LEDGER, json.dumps(lg, indent=1))
    rc, out = run(d, '--reseat-shas')
    ok('SUBJECT TWIN' in out,
       'the subject-twin basis is used and NAMED in the output, so a reader can '
       'tell which evidence moved a sha', out[-1200:])

    print(NL + 'KNOWN-BAD -- a subject twin whose DIFF TOUCHES NONE of the '
          "record's files must be REFUSED")
    rc, out = run(d, '--reseat-shas', '--write')
    doc = json.loads(io.open(LEDGER, encoding='utf-8').read())
    mis = [r for r in doc['records'] if r.get('resources') == ['mis_stamped']]
    ok(len(mis) == 1, 'the cross-check fixture record is present', doc)
    if mis:
        ok(mis[0]['opened_at_sha'] == disjoint_pre,
           'THE ARM THAT MATTERS: its sha is UNCHANGED. Its subject twin exists '
           'and is unique, and following it would have written a sha for a '
           'commit that touched none of this record\'s files -- which is what '
           'subject-twin matching did to two real records before this check '
           'existed',
           'twin was %s; record is now %r' % (disjoint_post[:12], mis[0]))
        ok('ALREADY WRONG FOR THIS RECORD' in out.upper(),
           'and the refusal says the RECORD is what is wrong, not the sha -- a '
           'mis-stamp and a rebase casualty need different repairs', out[-1400:])
        ok(disjoint_post[:12] not in (mis[0].get('opened_at_sha') or ''),
           'and the twin sha is nowhere in the record', mis[0])

    # ══ THE WEAK BASIS NEEDS ITS OWN FLAG ══════════════════════════════════
    print(NL + 'KNOWN-BAD -- the FILE-SET SUBSET basis is not applied by --write '
          'alone')
    write(LEDGER, json.dumps(ledger(pre, reachable, disjoint_pre, subset_when),
                             indent=1))
    rc, out = run(d, '--reseat-shas', '--write')
    doc = json.loads(io.open(LEDGER, encoding='utf-8').read())
    sub = [r for r in doc['records'] if r.get('resources') == ['widget']]
    ok(len(sub) == 1, 'the subset fixture record is present', doc)
    if sub:
        ok(sub[0]['opened_at_sha'] == 'f' * 40,
           'THE ARM THAT MATTERS: --write alone left it alone. Containment is a '
           'different claim from equality and must not ride along on one '
           'keystroke', sub[0])
        ok('WEAK' in out.upper(),
           'and the report names the weak basis and the flag it needs',
           out[-1000:])

    print(NL + 'DIRECTION -- --write-weak-basis DOES apply it, and stamps which '
          'basis')
    write(LEDGER, json.dumps(ledger(pre, reachable, disjoint_pre, subset_when),
                             indent=1))
    rc, out = run(d, '--reseat-shas', '--write', '--write-weak-basis')
    doc = json.loads(io.open(LEDGER, encoding='utf-8').read())
    sub = [r for r in doc['records'] if r.get('resources') == ['widget']]
    if sub:
        ok(sub[0]['opened_at_sha'] == subset_target,
           'with both flags the subset match IS applied, onto the three-file '
           'commit the record under-named', sub[0])
        ok(sub[0].get('opened_at_sha_reseat_basis') == 'FILE-SET SUBSET',
           'and the record records WHICH basis, so a weak reseat and a strong '
           'one are never indistinguishable', sub[0])
    strong = [r for r in doc['records'] if r.get('resources') == ['app_thing']]
    if strong and strong[0].get('opened_at_sha_reseated'):
        ok(strong[0].get('opened_at_sha_reseat_basis') in
           ('SUBJECT TWIN', 'EXACT FILE SET'),
           'and a strong reseat stamps its own basis too, not a blank marker',
           strong[0])
finally:
    rmtree(d)

# ── THE REAL LEDGER, read-only ─────────────────────────────────────────────
print(NL + 'THE REAL LEDGER -- dry run only, reported not asserted')
rc, out = subprocess.run(
    [sys.executable, TOOL, '--reseat-shas'], cwd=REPO, capture_output=True,
    text=True, encoding='utf-8', errors='replace',
    env=dict(os.environ, PYTHONIOENCODING='utf-8')).returncode, ''
p = subprocess.run([sys.executable, TOOL, '--reseat-shas'], cwd=REPO,
                   capture_output=True, text=True, encoding='utf-8',
                   errors='replace',
                   env=dict(os.environ, PYTHONIOENCODING='utf-8'))
body = (p.stdout or '') + (p.stderr or '')
print('  --   against the real ledger: exit %d. NOT AN ASSERTION -- how many '
      'shas are dangling is the state of four clones rebasing, not a property '
      'of this command.' % p.returncode)
ok(p.returncode in (0, 1, 2), 'it exits one of the three defined codes (got %d)'
   % p.returncode, body[-400:])
# ASSERTED ON THE LEDGER, NOT ON THE WORDING. The first version of this arm
# looked for the phrase 'DRY RUN' or 'Nothing to reseat', and FAILED the moment the
# real ledger reached a state with refusals but nothing reseatable -- where the tool
# correctly prints 'Nothing reseatable. Every dangling record above was REFUSED'.
# An arm that pins a report's PROSE breaks when the report gets better at
# explaining itself, and the fix would have been to weaken the message. The
# property that matters is that the file did not change.
_before = io.open(os.path.join(REPO, 'docs', 'tier-a-reviews.json'),
                  encoding='utf-8', newline='').read()
subprocess.run([sys.executable, TOOL, '--reseat-shas'], cwd=REPO,
               capture_output=True, text=True, encoding='utf-8',
               errors='replace',
               env=dict(os.environ, PYTHONIOENCODING='utf-8'))
_after = io.open(os.path.join(REPO, 'docs', 'tier-a-reviews.json'),
                 encoding='utf-8', newline='').read()
ok(_after == _before,
   'and the real run WITHOUT --write left the ledger byte-identical -- asserted on '
   'the file rather than on the report text, so the arm survives the report being '
   'reworded', 'the ledger changed during a dry run')

print(NL + '%d passed, %d failed' % (passed, failed))
sys.exit(EXIT_FINDING if failed else EXIT_CLEAN)
