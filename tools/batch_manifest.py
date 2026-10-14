#!/usr/bin/env python
# OWNER: cc
# written 2026-10-13, batch b6, queue item 4
"""The batch manifest: chat writes the ids, the agent writes status and evidence.

    python tools/batch_manifest.py --new cc b6 --items 6   # chat's half
    python tools/batch_manifest.py --set 3 done --evidence "<path or sha>"
    python tools/batch_manifest.py --close --agent cc --batch b7
    python tools/batch_manifest.py --check                 # the validator
    python tools/batch_manifest.py --fixtures              # the criteria lock

Exit 0 clean, 1 findings, 2 COULD NOT RUN.

── THE SPLIT IS THE WHOLE POINT ────────────────────────────────────────────
A batch arrives as a numbered queue in prose, and the agent then reports on it
in prose. Nothing connects the two, so three things happen and all three have
happened here:

  * an item is SKIPPED and the report simply does not mention it;
  * an item is RENUMBERED between the brief and the report, so "item 8" means
    two different things in two documents;
  * an item is reported done with no re-runnable evidence, which is a claim.

So the ids are written ONCE, by chat, and are IMMUTABLE. The agent may only
move `status` and add `evidence`. The validator refuses a manifest whose ids
have been renumbered, duplicated, added to or removed -- measured against the
`id_lock`, a hash of the id list taken when the manifest was created.

── WHY A HASH AND NOT A COUNT ──────────────────────────────────────────────
A count catches an added or dropped item and misses the renumbering, which is
the failure that actually costs a reader -- "item 8" meaning two things is
worse than item 8 being absent, because absence is visible. The lock is over
the ORDERED id list, so a swap is caught too.

── EVIDENCE IS A POINTER, NOT AN ADJECTIVE ─────────────────────────────────
`done` requires evidence, and evidence must look like something re-runnable: a
path, a sha, a command, or a test count. "verified" and "works" are refused by
name. This cannot tell a true pointer from a false one and does not claim to;
it refuses the shapes that cannot be checked at all.

── A BATCH CANNOT BE CLOSED WITHOUT A PASSING DRIVE VERIFY ─────────────────
`--close` is the only thing that writes the `closed` block, and it refuses
unless `tools/drive_upload_verify.py --verify-only` passes for that agent and
batch: the handoff, report and digest are on the shared Drive, under the right
names, each first line naming that same agent and batch, bytes and sha256
matching local. The failure this stops is not hypothetical -- cc's b6 report
and digest were never uploaded, the batch was reported closed, and the next
session found b5's files as the newest cc files on the Drive.

Three properties of that gate, each paid for:

  * IT VERIFIES, IT DOES NOT UPLOAD. `--verify-only`, so closing cannot be the
    thing that performs the upload it is supposed to be checking. Run the
    upload yourself first; `--close` then asserts it really happened.
  * IT FAILS CLOSED WHEN THE VERIFIER IS ABSENT (PR 1.11). No
    `if os.path.isfile(...)` skip: a missing `drive_upload_verify.py` is exit 2
    COULD NOT RUN naming the tool, never a close. Same for an absent Drive
    mount, which the verifier itself reports as 2.
  * `closed` IS NOT A FIELD AN AGENT CAN TYPE. `validate()` refuses a `closed`
    block that does not carry the verify PASS, and refuses one over any item
    still `open` or `in-progress` -- so hand-writing `"closed": true` into the
    JSON is a finding rather than a shortcut.

NO HOOK. This is a command an agent runs and a validator that refuses, not a
wiring change; `--check` over every manifest in docs/ is the sweep that finds a
batch that stopped without closing.
"""
import hashlib
import io
import json
import os
import re
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
try:
    from checker_kit import EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN
except Exception:                                                # noqa: BLE001
    EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN = 0, 1, 2

CRITERIA_VERSION = '2026-10-13.1'
NL = chr(10)
DOCS = os.path.join(REPO, 'docs')

STATUSES = ('open', 'in-progress', 'done', 'blocked', 'not-taken', 'dropped')

# A batch may close over an item that will not happen -- `blocked`, `not-taken`
# and `dropped` each carry a reason -- but NOT over one that is simply still
# running. `open` and `in-progress` are the two that mean nobody decided.
UNSETTLED = ('open', 'in-progress')

# The verifier `--close` refuses without. Named once, so the absent-tool
# message and the gate cannot disagree about which file is missing.
DRIVE_VERIFY = os.path.join(TOOLS, 'drive_upload_verify.py')

# A status that asserts the work is finished has to point at something.
NEEDS_EVIDENCE = ('done',)
# A status that says the work will NOT happen has to say why, which is the same
# requirement wearing different clothes.
NEEDS_REASON = ('blocked', 'not-taken', 'dropped')

# Shapes that cannot be re-run by anybody. Refused BY NAME, because these are
# exactly what gets written when there is nothing to point at.
EMPTY_EVIDENCE = re.compile(
    r'(?i)^[\s\W]*(done|ok|fine|works?|verified|tested|passes|passed|complete|'
    r'completed|fixed|yes|n/?a)[\s\W]*$')

# Something re-runnable: a path, a sha, a command, a count.
POINTER = re.compile(
    r'(?:[\w./-]+\.(?:py|js|json|md|txt|sql|html))'      # a file
    r'|(?:\b[0-9a-f]{7,40}\b)'                            # a sha
    r'|(?:\bpython\b|\bnode\b|\bgit\b)'                   # a command
    r'|(?:\b\d+\s*(?:/|of|passed|failed|arms?|rows?)\b)')  # a count


def manifest_path(agent, batch):
    return os.path.join(DOCS, 'batch-manifest-%s-%s.json' % (agent, batch))


def id_lock(ids):
    """A hash over the ORDERED id list. Catches a renumber, not just a count."""
    return hashlib.sha256(
        (chr(31).join(str(i) for i in ids)).encode('utf-8')).hexdigest()[:16]


def new(agent, batch, ids, titles=None):
    titles = titles or {}
    doc = {
        '_what_this_is': (
            'The batch manifest. CHAT WRITES THE IDS AND THEY ARE IMMUTABLE; '
            'the agent may only move `status` and add `evidence`. '
            '`id_lock` is a hash over the ordered id list and '
            '`batch_manifest.py --check` refuses a manifest whose ids have '
            'been renumbered, duplicated, added to or removed.'),
        'agent': agent,
        'batch': batch,
        'id_lock': id_lock(ids),
        'items': [{'id': i, 'title': titles.get(i, ''), 'status': 'open',
                   'evidence': ''} for i in ids],
    }
    return doc


def load(agent, batch):
    p = manifest_path(agent, batch)
    if not os.path.isfile(p):
        return None, '%s does not exist' % os.path.relpath(p, REPO)
    try:
        return json.loads(io.open(p, encoding='utf-8').read()), ''
    except Exception as exc:                                     # noqa: BLE001
        return None, '%s could not be parsed: %s' % (
            os.path.relpath(p, REPO), exc)


def save(doc):
    io.open(manifest_path(doc['agent'], doc['batch']), 'w', encoding='utf-8',
            newline=NL).write(json.dumps(doc, indent=2) + NL)


def validate(doc):
    """-> list of findings. Empty means clean."""
    bad = []
    items = doc.get('items')
    if not isinstance(items, list) or not items:
        return ['the manifest carries no items at all, so it asserts nothing']
    ids = [i.get('id') for i in items]

    seen = set()
    dups = []
    for i in ids:
        if i in seen:
            dups.append(i)
        seen.add(i)
    if dups:
        bad.append('DUPLICATE id(s): %s. Two items with one id means a report '
                   'referring to that number names both and neither.'
                   % ', '.join(str(d) for d in sorted(set(dups), key=str)))

    lock = doc.get('id_lock')
    if not lock:
        bad.append('no id_lock, so whether the ids have been renumbered CANNOT '
                   'BE CHECKED. That is not a pass -- a manifest without the '
                   'lock is exactly the state this validator exists to refuse.')
    elif id_lock(ids) != lock:
        bad.append('THE IDS HAVE CHANGED since this manifest was created. '
                   'id_lock=%s, the ids now hash to %s. Chat writes the ids '
                   'and they are immutable; the agent may only move status and '
                   'add evidence. Current ids: %s'
                   % (lock, id_lock(ids), ', '.join(str(i) for i in ids)))

    for it in items:
        where = 'item %s' % it.get('id')
        st = it.get('status')
        ev = (it.get('evidence') or '').strip()
        if st not in STATUSES:
            bad.append('%s has status %r, which is outside %s'
                       % (where, st, list(STATUSES)))
            continue
        if st in NEEDS_EVIDENCE and not ev:
            bad.append('%s is %r with NO evidence. A finished item has to point '
                       'at something somebody else can re-run.' % (where, st))
        elif st in NEEDS_REASON and not ev:
            bad.append('%s is %r with nothing in `evidence` saying why. '
                       '"Not done" needs a reason for the same reason "done" '
                       'needs a pointer.' % (where, st))
        elif ev and EMPTY_EVIDENCE.match(ev):
            bad.append('%s offers %r as evidence, which is an adjective rather '
                       'than a pointer. A path, a sha, a command or a count.'
                       % (where, ev[:40]))
        elif st in NEEDS_EVIDENCE and ev and not POINTER.search(ev):
            bad.append('%s has evidence with nothing re-runnable in it (%r). '
                       'A path, a sha, a command, or a count.'
                       % (where, ev[:60]))

    bad += validate_closed(doc, items)
    return bad


def validate_closed(doc, items):
    """-> findings about the `closed` block. Empty means clean OR absent.

    An open batch has no `closed` block and that is not a finding -- this is
    about what a PRESENT one has to carry. `--close` is the only writer; these
    are the shapes a hand-edit produces.
    """
    closed = doc.get('closed')
    if closed is None:
        return []
    bad = []
    if not isinstance(closed, dict):
        return ['`closed` is %r rather than the block `--close` writes. '
                '"closed": true is a typed assertion with nothing behind it; '
                'the block carries the drive-verify evidence that makes it '
                'checkable.' % (closed,)]
    if closed.get('drive_verify') != 'PASS':
        bad.append('the manifest is marked closed and `closed.drive_verify` is '
                   '%r, not "PASS". A batch cannot be closed without a passing '
                   '%s -- that is the check that catches a handoff, report or '
                   'digest that was never uploaded.'
                   % (closed.get('drive_verify'),
                      os.path.basename(DRIVE_VERIFY)))
    if not (closed.get('verified_by') or '').strip():
        bad.append('the manifest is marked closed with no `closed.verified_by` '
                   'command, so the verify CANNOT BE RE-RUN by a reader. A '
                   'pass nobody can reproduce is a claim.')
    unsettled = [str(it.get('id')) for it in items
                 if it.get('status') in UNSETTLED]
    if unsettled:
        bad.append('the manifest is marked closed while item(s) %s are still '
                   '%s. A closed batch may carry a blocked or dropped item -- '
                   'each of those says why -- but not one that nobody decided.'
                   % (', '.join(unsettled), ' / '.join(UNSETTLED)))
    return bad


def cmd_check(agent=None, batch=None):
    import glob
    paths = ([manifest_path(agent, batch)] if agent and batch
             else sorted(glob.glob(os.path.join(DOCS, 'batch-manifest-*.json'))))
    if not paths:
        print('COULD NOT RUN: no batch manifest found in docs/. Nothing was '
              'checked, which is not the same as nothing being wrong.')
        return EXIT_COULD_NOT_RUN
    rc = EXIT_CLEAN
    print('BATCH MANIFEST -- criteria %s' % CRITERIA_VERSION)
    for p in paths:
        rel = os.path.relpath(p, REPO)
        if not os.path.isfile(p):
            print('  %s -- ABSENT' % rel)
            rc = EXIT_COULD_NOT_RUN
            continue
        try:
            doc = json.loads(io.open(p, encoding='utf-8').read())
        except Exception as exc:                                 # noqa: BLE001
            print('  %s -- COULD NOT PARSE: %s' % (rel, exc))
            rc = EXIT_COULD_NOT_RUN
            continue
        findings = validate(doc)
        counts = {}
        for it in doc.get('items') or []:
            counts[it.get('status')] = counts.get(it.get('status'), 0) + 1
        print('  %s -- %d item(s): %s' % (
            rel, len(doc.get('items') or []),
            ', '.join('%s %d' % (k, v) for k, v in sorted(counts.items()))))
        for f in findings:
            print('    ! %s' % f)
        if findings and rc == EXIT_CLEAN:
            rc = EXIT_FINDING
    return rc


def cmd_set(agent, batch, item_id, status, evidence):
    doc, why = load(agent, batch)
    if doc is None:
        print('COULD NOT RUN: %s' % why)
        return EXIT_COULD_NOT_RUN
    hit = None
    for it in doc['items']:
        if str(it.get('id')) == str(item_id):
            hit = it
            break
    if hit is None:
        print('no item %r in %s. THE IDS ARE CHAT\'S AND THIS TOOL WILL NOT '
              'ADD ONE -- that is the renumbering this manifest exists to '
              'prevent. Ids present: %s'
              % (item_id, manifest_path(agent, batch),
                 ', '.join(str(i.get('id')) for i in doc['items'])))
        return EXIT_FINDING
    if status not in STATUSES:
        print('status %r is outside %s' % (status, list(STATUSES)))
        return EXIT_FINDING
    hit['status'] = status
    if evidence is not None:
        hit['evidence'] = evidence
    findings = validate(doc)
    if findings:
        print('REFUSED -- the manifest would not validate after that change:')
        for f in findings:
            print('  ! %s' % f)
        print('Nothing was written.')
        return EXIT_FINDING
    save(doc)
    print('item %s -> %s' % (item_id, status))
    if evidence:
        print('  evidence: %s' % evidence[:120])
    return EXIT_CLEAN


# ── THE CLOSE GATE ──────────────────────────────────────────────────────────
def drive_verify(agent, batch, runner=None):
    """Run the Drive verify for this agent and batch. -> (rc, output).

    FAILS CLOSED WHEN THE VERIFIER IS ABSENT, by name, with no isfile skip:
    `COULD NOT RUN` is a third state and folding it into a pass is the single
    most expensive defect shape on this platform (PR 1.11).
    """
    if not os.path.isfile(DRIVE_VERIFY):
        return EXIT_COULD_NOT_RUN, (
            'COULD NOT RUN: %s is absent, so whether this batch\'s handoff, '
            'report and digest are on the Drive CANNOT BE CHECKED. The batch '
            'is NOT closed. "Could not tell" is not "passed".'
            % os.path.relpath(DRIVE_VERIFY, REPO))
    cmd = [sys.executable, DRIVE_VERIFY, '--agent', agent, '--batch', batch,
           '--verify-only']
    if runner is not None:                    # the probe drives this
        return runner(cmd)
    import subprocess
    p = subprocess.run(cmd, cwd=REPO, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT)
    return p.returncode, p.stdout.decode('utf-8', 'replace')


def cmd_close(agent, batch, runner=None):
    doc, why = load(agent, batch)
    if doc is None:
        print('COULD NOT RUN: %s' % why)
        return EXIT_COULD_NOT_RUN
    print('BATCH MANIFEST CLOSE -- %s %s -- criteria %s'
          % (agent, batch, CRITERIA_VERSION))

    # 1. The manifest itself, before anything about the Drive.
    findings = validate(doc)
    if findings:
        print('REFUSED -- the manifest does not validate, so the question of '
              'whether it may close does not arise:')
        for f in findings:
            print('  ! %s' % f)
        return EXIT_FINDING
    unsettled = [str(it.get('id')) for it in doc['items']
                 if it.get('status') in UNSETTLED]
    if unsettled:
        print('REFUSED -- item(s) %s are still %s. Give each one a terminal '
              'status with its evidence or reason first; `--close` does not '
              'decide them for you.'
              % (', '.join(unsettled), ' / '.join(UNSETTLED)))
        return EXIT_FINDING

    # 2. THE GATE. The deliverables are on the Drive, or this is not a close.
    rc, out = drive_verify(agent, batch, runner=runner)
    print('')
    print('  %s --agent %s --batch %s --verify-only  -> exit %d'
          % (os.path.relpath(DRIVE_VERIFY, REPO), agent, batch, rc))
    for line in (out or '').splitlines():
        print('  | %s' % line)
    print('')
    if rc == EXIT_COULD_NOT_RUN:
        print('NOT CLOSED: the Drive verify COULD NOT RUN (exit 2). That is '
              'not a failure of this batch and it is not a pass either -- '
              'nothing about the uploads was established.')
        return EXIT_COULD_NOT_RUN
    if rc != EXIT_CLEAN:
        print('NOT CLOSED: the Drive verify reported findings (exit %d). The '
              'handoff, report and digest are not all on the Drive under the '
              'right name with matching bytes. Fix the upload, not this file.'
              % rc)
        return EXIT_FINDING

    shas = re.findall(r'PASS\s+(SAIRN-\S+)\s+\d+ bytes\s+sha256 ([0-9a-f]+)',
                      out or '')
    doc['closed'] = {
        'drive_verify': 'PASS',
        'verified_by': 'python %s --agent %s --batch %s --verify-only'
                       % (os.path.relpath(DRIVE_VERIFY, REPO).replace(
                           os.sep, '/'), agent, batch),
        'criteria': CRITERIA_VERSION,
        'deliverables': ['%s sha256 %s' % (n, s) for n, s in shas],
    }
    findings = validate(doc)
    if findings:                      # belt: the written state must validate
        print('REFUSED -- the closed manifest would not validate:')
        for f in findings:
            print('  ! %s' % f)
        print('Nothing was written.')
        return EXIT_FINDING
    save(doc)
    print('CLOSED: %s %s. %d deliverable(s) verified on the Drive:'
          % (agent, batch, len(shas)))
    for d in doc['closed']['deliverables']:
        print('  %s' % d)
    return EXIT_CLEAN


# ── THE CRITERIA LOCK ───────────────────────────────────────────────────────
def run_fixtures():
    print('BATCH MANIFEST -- criteria lock %s' % CRITERIA_VERSION)
    bad = 0
    total = 0

    def check(label, got, want):
        # COUNTED, not hardcoded. This said `total = 21` and a count written
        # beside the thing it counts goes stale the next time a fixture is
        # added -- which is this change.
        nonlocal bad, total
        total += 1
        okk = (bool(got) == bool(want))
        if not okk:
            bad += 1
        print('  %s %-62s findings=%s' % ('ok  ' if okk else 'FAIL', label,
                                          len(got) if isinstance(got, list)
                                          else got))

    base = new('cc', 'fix', [1, 2, 3])
    check('a fresh manifest validates', validate(base), False)

    d = json.loads(json.dumps(base))
    d['items'][0]['status'] = 'done'
    d['items'][0]['evidence'] = 'tools/gate_skip.py, 14/14 fixtures'
    check('done WITH a re-runnable pointer validates', validate(d), False)

    d = json.loads(json.dumps(base))
    d['items'][0]['status'] = 'done'
    check('done with NO evidence is a finding', validate(d), True)

    for word in ('verified', 'works', 'done', 'tested', 'n/a'):
        d = json.loads(json.dumps(base))
        d['items'][0]['status'] = 'done'
        d['items'][0]['evidence'] = word
        check('done with %r as evidence is a finding' % word, validate(d), True)

    d = json.loads(json.dumps(base))
    d['items'][0]['status'] = 'done'
    d['items'][0]['evidence'] = 'it all went fine in the end'
    check('done with prose carrying no pointer is a finding', validate(d), True)

    d = json.loads(json.dumps(base))
    d['items'][0]['status'] = 'blocked'
    check('blocked with no reason is a finding', validate(d), True)
    d['items'][0]['evidence'] = 'hank holds docs/tier-a-reviews.json in his b5 FILES'
    check('blocked WITH a reason validates', validate(d), False)

    # THE TWO THE BRIEF NAMED.
    d = json.loads(json.dumps(base))
    d['items'][2]['id'] = 9
    check('RENUMBERED ids are a finding', validate(d), True)
    check('...and the finding names the lock mismatch',
          any('IDS HAVE CHANGED' in f for f in validate(d)), True)

    d = json.loads(json.dumps(base))
    d['items'][2]['id'] = 2
    check('DUPLICATE ids are a finding', validate(d), True)
    check('...and the finding says duplicate',
          any('DUPLICATE' in f for f in validate(d)), True)

    d = json.loads(json.dumps(base))
    d['items'].append({'id': 4, 'status': 'open', 'evidence': ''})
    check('an ADDED item is a finding -- the agent does not write ids',
          validate(d), True)

    d = json.loads(json.dumps(base))
    d['items'].pop()
    check('a REMOVED item is a finding', validate(d), True)

    d = json.loads(json.dumps(base))
    d['items'][0]['id'], d['items'][1]['id'] = (d['items'][1]['id'],
                                                d['items'][0]['id'])
    check('a SWAPPED pair is a finding -- which a COUNT would have missed, and '
          'is why the lock is over the ordered list', validate(d), True)

    d = json.loads(json.dumps(base))
    del d['id_lock']
    check('NO id_lock is a finding, not a pass', validate(d), True)

    d = json.loads(json.dumps(base))
    d['items'][0]['status'] = 'invented'
    check('a status outside the vocabulary is a finding', validate(d), True)

    d = json.loads(json.dumps(base))
    d['items'] = []
    check('an EMPTY manifest is a finding -- it asserts nothing', validate(d),
          True)

    # ── THE CLOSE GATE, in both directions ─────────────────────────────────
    def settled():
        s = json.loads(json.dumps(base))
        for n, it in enumerate(s['items']):
            it['status'] = 'done'
            it['evidence'] = 'tools/thing_%d.py, 3/3 arms' % n
        return s

    d = settled()
    check('a settled manifest with NO closed block validates -- an open batch '
          'is not a finding', validate(d), False)

    d = settled()
    d['closed'] = True
    check('"closed": true, typed by hand, is a finding', validate(d), True)

    d = settled()
    d['closed'] = {'drive_verify': 'PASS', 'verified_by': 'python tools/x.py'}
    check('a closed block carrying the verify PASS and a command validates',
          validate(d), False)

    d = settled()
    d['closed'] = {'verified_by': 'python tools/x.py'}
    check('closed with NO drive_verify is a finding', validate(d), True)

    d = settled()
    d['closed'] = {'drive_verify': 'SKIPPED', 'verified_by': 'python x.py'}
    check('closed with drive_verify SKIPPED is a finding -- a skip is not a '
          'pass', validate(d), True)

    d = settled()
    d['closed'] = {'drive_verify': 'PASS', 'verified_by': ''}
    check('closed with no re-runnable verified_by command is a finding',
          validate(d), True)

    for st in UNSETTLED:
        d = settled()
        d['items'][1]['status'] = st
        d['items'][1]['evidence'] = ''
        d['closed'] = {'drive_verify': 'PASS', 'verified_by': 'python x.py'}
        check('closed over an item still %r is a finding' % st, validate(d),
              True)

    d = settled()
    d['items'][1]['status'] = 'blocked'
    d['items'][1]['evidence'] = 'docs/by-design-register.json is in fourth b11'
    d['closed'] = {'drive_verify': 'PASS', 'verified_by': 'python x.py'}
    check('...but closed over a BLOCKED item that says why validates',
          validate(d), False)

    # The absent-verifier leg, by pointing the constant at nothing. This is
    # the PR 1.11 shape and the only fixture here that can prove the gate
    # does not quietly skip.
    global DRIVE_VERIFY
    keep = DRIVE_VERIFY
    try:
        DRIVE_VERIFY = os.path.join(TOOLS, 'no_such_verifier.py')
        rc, out = drive_verify('cc', 'fix')
        check('an ABSENT drive_upload_verify.py is exit 2 COULD NOT RUN, not '
              'a skip', rc == EXIT_COULD_NOT_RUN and 'COULD NOT RUN' in out,
              True)
        check('...and the message names the file that is missing',
              'no_such_verifier.py' in out, True)
    finally:
        DRIVE_VERIFY = keep

    print('  %d/%d fixtures classify correctly' % (total - bad, total))
    return EXIT_FINDING if bad else EXIT_CLEAN


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)

    def opt(name, default=None):
        return argv[argv.index(name) + 1] if name in argv else default

    if '--fixtures' in argv:
        return run_fixtures()
    if '--new' in argv:
        i = argv.index('--new')
        agent, batch = argv[i + 1], argv[i + 2]
        n = int(opt('--items', '0') or 0)
        if n <= 0:
            print('COULD NOT RUN: --items <n> is required and must be > 0.')
            return EXIT_COULD_NOT_RUN
        p = manifest_path(agent, batch)
        if os.path.isfile(p):
            print('REFUSED: %s already exists. Re-creating it would rewrite '
                  'the id_lock, which is the one thing this file exists to '
                  'make immutable.' % os.path.relpath(p, REPO))
            return EXIT_FINDING
        doc = new(agent, batch, list(range(1, n + 1)))
        save(doc)
        print('wrote %s with ids 1-%d, id_lock=%s'
              % (os.path.relpath(p, REPO), n, doc['id_lock']))
        return EXIT_CLEAN
    if '--set' in argv:
        i = argv.index('--set')
        return cmd_set(opt('--agent', 'cc'), opt('--batch', 'b6'),
                       argv[i + 1], argv[i + 2], opt('--evidence'))
    if '--close' in argv:
        # THE LOCK FIRST here too: closing a batch on broken criteria is the
        # one verdict in this file nobody re-reads.
        if run_fixtures() != EXIT_CLEAN:
            print('')
            print('COULD NOT RUN: the criteria lock failed, so no batch is '
                  'closed by this run.')
            return EXIT_COULD_NOT_RUN
        print('')
        agent, batch = opt('--agent'), opt('--batch')
        if not agent or not batch:
            print('COULD NOT RUN: --close needs --agent <name> and --batch '
                  'b<n>. Neither is guessed from the folder name.')
            return EXIT_COULD_NOT_RUN
        return cmd_close(agent, batch)
    # THE LOCK FIRST, as everywhere else in this repo.
    if run_fixtures() != EXIT_CLEAN:
        print('')
        print('COULD NOT RUN: the criteria lock failed, so no verdict about a '
              'real manifest is trustworthy.')
        return EXIT_COULD_NOT_RUN
    print('')
    return cmd_check(opt('--agent'), opt('--batch'))


if __name__ == '__main__':
    sys.exit(main())
