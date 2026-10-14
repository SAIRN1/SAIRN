#!/usr/bin/env python
# OWNER: cc
# written 2026-10-13, batch b7, queue item 2
"""Upload a batch's handoff, report and digest to the shared Drive -- then PROVE it.

    python tools/drive_upload_verify.py --agent cc --batch b7
    python tools/drive_upload_verify.py --agent cc --batch b7 --verify-only
    python tools/drive_upload_verify.py --audit
    python tools/drive_upload_verify.py --fixtures

Exit 0 clean, 1 findings, 2 COULD NOT RUN.

Every agent runs this for its three deliverables. It is ONE tool rather than a
paragraph in six dispatches because the failure it exists to stop has now
happened in three different shapes, each of which looked like success:

  * cc's b6 report and digest were never uploaded at all. The batch was
    reported closed. Nothing anywhere said otherwise, and the next session
    found the newest cc files on the Drive were b5's.
  * `SAIRN-handoff-cc-b6.md` IS on the Drive, 2,162 bytes, and its first line
    is `# cody b6 handoff (filename as requested)`. A correct filename over
    another agent's content is worse than an absent file: a coordinating
    session reads the name, trusts it, and routes cody's state as cc's.
  * h1's own uploads carry a digest at b20 and a handoff at b16, a mismatch
    inside one clone that nobody noticed because nothing compared them.

── THE FOUR THINGS IT CHECKS, AND WHY EACH ONE IS SEPARATE ─────────────────
1. THE NAME is `SAIRN-<kind>-<agent>-b<n>` with the extension that kind uses.
   A name is the only thing a coordinating session sees in a folder listing,
   so it is the first thing that has to be right.
2. THE FIRST LINE OF THE BYTES ON THE DRIVE names that same agent and that
   same batch. This is the check that catches the b6 handoff. A name is
   metadata and can be written by anybody; the first line is the content
   asserting its own identity. BOTH, or you cannot tell them apart.
3. BYTES AND SHA256 MATCH THE LOCAL FILE. A short write, a half-synced file
   and a stale copy from a previous batch all pass a name check and all pass
   an existence check. Length alone would miss a same-length corruption, and
   sha256 alone reads oddly in a report, so both are printed.
4. THE FOLDER LISTING CONTAINS IT, read fresh after the copy. `os.path.isfile`
   on the path you just wrote is close to a tautology; the listing is what the
   next session will actually read.

── WHAT THIS TOOL CANNOT TELL YOU, SAID OUT LOUD EVERY RUN ─────────────────
The destination is a Google Drive **sync mount**, not an API endpoint. A
matching read-back proves the bytes are in the sync set, under the right name,
with the right content. IT DOES NOT PROVE GOOGLE HAS ACKNOWLEDGED THE UPLOAD.
That is a could-not-tell, not a pass, and folding it into the pass is exactly
PR 1.11 one layer out -- so the tool prints the limit and names the one thing
that closes it: a Drive-side read from the chat turn, which goes through the
API rather than the mount.

── IT REFUSES TO OVERWRITE ANOTHER AGENT'S CONTENT ─────────────────────────
If the destination already exists and ITS first line names a different agent,
the copy is REFUSED. That is the b6 handoff exactly: the fix is a differently
named file, not a quiet overwrite of the only surviving copy of somebody
else's state. `--overwrite-foreign` exists, requires a reason, and says so.
"""
import hashlib
import io
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

# The shared Drive directory, same resolution as tools/compaction_brief.py.
# The env override exists so the probe can drive a temp directory; it is
# PRINTED whenever it is in use, because a tool that can be pointed somewhere
# harmless without saying so is a tool that passes without testing anything.
DRIVE_DEFAULT = os.path.join('G:', os.sep, 'My Drive', 'SAIRN-status')
DRIVE_FOLDER_ID = '14Xc5oT0xzSLa_rTSOSXWVK3Kko1Fbx09'

KINDS = {
    'handoff': '.md',
    'report': '.txt',
    'digest': '.txt',
}

# Agent token in a filename -> other spellings of the same agent that are
# acceptable in a first line. The auditors' Drive tokens are NOT their session
# names (hover writes h1, hover2 writes h2), so this is a table measured from
# the real directory rather than a format string. Same table as
# compaction_brief.py's AGENTS, read the other way round.
ALIASES = {
    'cc': ('cc',),
    'hank': ('hank',),
    'cody': ('cody',),
    'fourth': ('fourth', 'ted'),
    'h1': ('h1', 'hover'),
    'h2': ('h2', 'hover2'),
}

NAME_RE = re.compile(
    r'^SAIRN-(?P<kind>handoff|report|digest)-(?P<agent>[A-Za-z0-9]+)'
    r'-(?P<batch>b\d+)(?P<ext>\.md|\.txt)$')


def drive_dir():
    return os.environ.get('SAIRN_DRIVE_DIR') or DRIVE_DEFAULT


def expected_name(kind, agent, batch):
    return 'SAIRN-%s-%s-%s%s' % (kind, agent, batch, KINDS[kind])


def sha256_of(data):
    return hashlib.sha256(data).hexdigest()


def read_bytes(path):
    """-> (bytes, '') or (None, why). Binary, so no newline translation."""
    try:
        with open(path, 'rb') as fh:
            return fh.read(), ''
    except OSError as exc:
        return None, str(exc)


def first_line(data):
    """The first line of raw bytes, decoded leniently, CR and BOM stripped.

    LENIENT ON PURPOSE. A first line that cannot be decoded is still a first
    line and the identity check should report what it found rather than
    raising -- a crash here reads as a tool failure rather than a bad file.
    """
    if data is None:
        return ''
    head = data.split(b'\n', 1)[0]
    txt = head.decode('utf-8', 'replace')
    return txt.lstrip('﻿').rstrip('\r').strip()


def names_agent_and_batch(line, agent, batch):
    """-> (ok, why). Does this first line assert this agent and this batch?

    Word-bounded, because `cc` is two letters and appears inside ordinary
    words. The agent may be spelled with any of its aliases; the batch must be
    the exact token, so `b7` does not satisfy `b17` and `b17` does not satisfy
    `b7`.
    """
    low = line.lower()
    spellings = ALIASES.get(agent, (agent,))
    hit = None
    for sp in spellings:
        if re.search(r'(?<![0-9a-z])%s(?![0-9a-z])' % re.escape(sp.lower()),
                     low):
            hit = sp
            break
    if hit is None:
        return False, ('the first line does not name %s (tried: %s). It reads: '
                       '%r' % (agent, ', '.join(spellings), line[:90]))
    if not re.search(r'(?<![0-9a-z])%s(?![0-9a-z])' % re.escape(batch.lower()),
                     low):
        return False, ('the first line names %s but NOT batch %s. It reads: '
                       '%r' % (hit, batch, line[:90]))
    return True, 'names %s and %s' % (hit, batch)


# ── THE ONE DELIVERABLE ─────────────────────────────────────────────────────
def verify_one(kind, agent, batch, local_path, directory, upload=True,
               overwrite_foreign=False, out=None):
    """-> list of findings for one deliverable. Empty means clean."""
    say = out.append if out is not None else (lambda _s: None)
    bad = []
    want = expected_name(kind, agent, batch)
    got_name = os.path.basename(local_path)

    # 1. THE NAME.
    m = NAME_RE.match(got_name)
    if not m:
        bad.append('%s: the local filename %r is not SAIRN-<kind>-<agent>-'
                   '<batch> with a .md or .txt extension. Expected %r.'
                   % (kind, got_name, want))
    else:
        if m.group('kind') != kind:
            bad.append('%s: %r calls itself a %s file.'
                       % (kind, got_name, m.group('kind')))
        if m.group('agent') != agent:
            bad.append('%s: %r names agent %r, but this run is for %r. A '
                       'deliverable filed under another agent\'s token is how '
                       'one session\'s state gets read as another\'s.'
                       % (kind, got_name, m.group('agent'), agent))
        if m.group('batch') != batch:
            bad.append('%s: %r names batch %r, but this run is for %r.'
                       % (kind, got_name, m.group('batch'), batch))
        if m.group('ext') != KINDS[kind]:
            bad.append('%s: a %s carries %s, not %s (%r).'
                       % (kind, kind, KINDS[kind], m.group('ext'), got_name))

    # 2. THE LOCAL FILE HAS TO EXIST. This is the b6 case: nothing was there.
    local, why = read_bytes(local_path)
    if local is None:
        bad.append('%s: %s could not be read (%s). THE DELIVERABLE DOES NOT '
                   'EXIST, which is a finding about the batch and not about '
                   'this tool.' % (kind, local_path, why))
        return bad
    if not local.strip():
        bad.append('%s: %s is empty (%d bytes). An empty file uploads cleanly '
                   'and says nothing.' % (kind, local_path, len(local)))
        return bad

    local_line = first_line(local)
    ok, why = names_agent_and_batch(local_line, agent, batch)
    if not ok:
        bad.append('%s (local): %s' % (kind, why))

    dest = os.path.join(directory, want)

    # 3. REFUSE TO OVERWRITE ANOTHER AGENT'S CONTENT.
    if upload and os.path.isfile(dest):
        existing, _why = read_bytes(dest)
        exline = first_line(existing)
        if exline:
            foreign = None
            for other, spellings in ALIASES.items():
                if other == agent:
                    continue
                for sp in spellings:
                    if re.search(
                            r'(?<![0-9a-z])%s(?![0-9a-z])' % re.escape(sp),
                            exline.lower()):
                        foreign = sp
                        break
                if foreign:
                    break
            mine, _w = names_agent_and_batch(exline, agent, batch)
            if foreign and not mine:
                if not overwrite_foreign:
                    bad.append(
                        '%s: REFUSED TO UPLOAD. %s already exists on the Drive '
                        'and its first line names %r, not %s: %r. Overwriting '
                        'it destroys the only copy of another session\'s '
                        'state. Upload under a different name, or pass '
                        '--overwrite-foreign --why "<reason>" and say so out '
                        'loud.' % (kind, want, foreign, agent, exline[:90]))
                    return bad
                say('  OVERWRITE-FOREIGN used on %s (first line named %r)'
                    % (want, foreign))

    # 4. UPLOAD.
    if upload:
        try:
            with open(dest, 'wb') as fh:
                fh.write(local)
        except OSError as exc:
            bad.append('%s: could not write %s (%s)' % (kind, dest, exc))
            return bad

    # 5. THE FOLDER LISTING, read fresh.
    try:
        listing = os.listdir(directory)
    except OSError as exc:
        bad.append('%s: the Drive folder %s could not be listed (%s), so the '
                   'upload is UNVERIFIED rather than good.'
                   % (kind, directory, exc))
        return bad
    if want not in listing:
        bad.append('%s: %r is NOT in the %d-entry listing of %s. The write '
                   'reported success and the folder does not have it.'
                   % (kind, want, len(listing), directory))
        return bad

    # 6. READ IT BACK.
    remote, why = read_bytes(dest)
    if remote is None:
        bad.append('%s: %r is in the listing but could not be read back (%s).'
                   % (kind, want, why))
        return bad
    if len(remote) != len(local):
        bad.append('%s: %r is %d bytes on the Drive and %d bytes locally -- a '
                   'difference of %d. A truncated file is in the listing, '
                   'carries the right name, and is not the deliverable.'
                   % (kind, want, len(remote), len(local),
                      len(remote) - len(local)))
    lsha, rsha = sha256_of(local), sha256_of(remote)
    if lsha != rsha:
        bad.append('%s: %r has sha256 %s on the Drive and %s locally. Same '
                   'name, different content.' % (kind, want, rsha[:16], lsha[:16]))

    # 7. THE FIRST LINE OF THE BYTES ON THE DRIVE, not of the local copy.
    rline = first_line(remote)
    ok, why = names_agent_and_batch(rline, agent, batch)
    if not ok:
        bad.append('%s (on the Drive): %s' % (kind, why))

    if not bad:
        say('  PASS %-34s %7d bytes  sha256 %s  first line: %r'
            % (want, len(remote), rsha[:16], rline[:60]))
    return bad


# ── THE THREE DELIVERABLES ──────────────────────────────────────────────────
def cmd_verify(agent, batch, paths, upload=True, overwrite_foreign=False,
               why=''):
    directory = drive_dir()
    print('DRIVE UPLOAD VERIFY -- criteria %s' % CRITERIA_VERSION)
    print('  agent %s   batch %s   %s'
          % (agent, batch, 'UPLOAD + VERIFY' if upload else 'VERIFY ONLY'))
    print('  folder : %s' % directory)
    if os.environ.get('SAIRN_DRIVE_DIR'):
        print('  NOTE: SAIRN_DRIVE_DIR IS SET, so this run did NOT touch the '
              'real shared Drive. A pass here is a pass about a temp '
              'directory.')
    else:
        print('  folder id (for a Drive-side read): %s' % DRIVE_FOLDER_ID)

    if not os.path.isdir(directory):
        print('')
        print('COULD NOT RUN: %s is not a directory. The Google Drive mount is '
              'absent, so NOTHING WAS UPLOADED AND NOTHING WAS CHECKED. That '
              'is a third state and it is not a pass.' % directory)
        return EXIT_COULD_NOT_RUN
    if overwrite_foreign and not why.strip():
        print('')
        print('COULD NOT RUN: --overwrite-foreign requires --why "<reason>". '
              'Destroying another session\'s only copy of its state is a '
              'decision, and a decision with no reason recorded is a '
              'mechanism.')
        return EXIT_COULD_NOT_RUN

    out = []
    findings = []
    for kind in ('handoff', 'report', 'digest'):
        findings += verify_one(kind, agent, batch, paths[kind], directory,
                               upload=upload,
                               overwrite_foreign=overwrite_foreign, out=out)
    print('')
    for line in out:
        print(line)
    if findings:
        print('')
        print('%d FINDING(S):' % len(findings))
        for f in findings:
            print('  ! %s' % f)
        print('')
        print('NOT UPLOADED-AND-VERIFIED. Do not mark this batch closed.')
        return EXIT_FINDING

    print('')
    print('PASS: all three deliverables for %s %s are on the Drive under the '
          'right name, with a first line naming %s and %s, and with bytes and '
          'sha256 matching local.' % (agent, batch, agent, batch))
    print('LIMIT, and it is not folded into that pass: the destination is a '
          'Drive SYNC MOUNT. This proves the bytes are in the sync set; it does '
          'NOT prove Google acknowledged them. Close that with a Drive-side '
          'read of folder %s from the chat turn, which goes through the API '
          'rather than the mount.' % DRIVE_FOLDER_ID)
    return EXIT_CLEAN


# ── --audit ─────────────────────────────────────────────────────────────────
def cmd_audit():
    """Every SAIRN-<kind>-<agent>-b<n> in the folder whose NAME and FIRST LINE
    disagree. Reports; never renames and never deletes."""
    directory = drive_dir()
    print('DRIVE NAME-vs-CONTENT AUDIT -- criteria %s' % CRITERIA_VERSION)
    print('  folder : %s' % directory)
    if not os.path.isdir(directory):
        print('COULD NOT RUN: %s is not a directory. Nothing was audited.'
              % directory)
        return EXIT_COULD_NOT_RUN
    try:
        listing = sorted(os.listdir(directory))
    except OSError as exc:
        print('COULD NOT RUN: %s could not be listed (%s).' % (directory, exc))
        return EXIT_COULD_NOT_RUN

    checked = 0
    bad = []
    unreadable = []
    for name in listing:
        m = NAME_RE.match(name)
        if not m:
            continue
        checked += 1
        data, why = read_bytes(os.path.join(directory, name))
        if data is None:
            unreadable.append('%s could not be read (%s)' % (name, why))
            continue
        line = first_line(data)
        ok, reason = names_agent_and_batch(
            line, m.group('agent'), m.group('batch'))
        if not ok:
            bad.append('%s -- %s' % (name, reason))

    print('  CHECKED / LISTING : %d / %d entries' % (checked, len(listing)))
    print('  (an entry whose name is not SAIRN-<kind>-<agent>-b<n> is OUTSIDE '
          'this audit and is neither pass nor fail -- it is unchecked, and the '
          'two numbers above are how you can tell.)')
    print('')
    for u in unreadable:
        print('  COULD NOT TELL  %s' % u)
    for b in bad:
        print('  DISAGREES       %s' % b)
    if not bad and not unreadable:
        print('  every named file\'s first line names the agent and batch its '
              'name claims.')
    print('')
    if unreadable:
        print('%d file(s) could not be read, so this audit is INCOMPLETE.'
              % len(unreadable))
        return EXIT_COULD_NOT_RUN
    if bad:
        print('%d file(s) carry one agent\'s name over another\'s content, or '
              'the wrong batch. REPORTED, NOT RENAMED -- a tool that renames '
              'somebody else\'s upload is guessing which half is right.'
              % len(bad))
        return EXIT_FINDING
    return EXIT_CLEAN


# ── THE CRITERIA LOCK ───────────────────────────────────────────────────────
def run_fixtures():
    print('DRIVE UPLOAD VERIFY -- criteria lock %s' % CRITERIA_VERSION)
    bad = 0
    total = 0

    def check(label, got, want):
        nonlocal bad, total
        total += 1
        if bool(got) != bool(want):
            bad += 1
            print('  LOCK FAILED  %s -- got %r, wanted %r' % (label, got, want))

    # The first-line predicate, in BOTH directions. Written out rather than
    # generated, because a generated fixture shares the generator's bug.
    good = [
        ('# SAIRN handoff -- cc batch b7 -- 2026-10-13', 'cc', 'b7'),
        ('REPORT cc b7', 'cc', 'b7'),
        ('DIGEST cc b7', 'cc', 'b7'),
        ('# h1 batch b20 handoff', 'h1', 'b20'),
        ('# hover2 b11 handoff', 'h2', 'b11'),          # alias spelling
        ('# ted batch b11 handoff', 'fourth', 'b11'),   # alias spelling
    ]
    bad_cases = [
        # THE b6 DEFECT, as a fixture: cody's content under cc's batch.
        ('# cody b6 handoff (filename as requested)', 'cc', 'b6'),
        ('REPORT cody b6', 'cc', 'b6'),
        # right agent, wrong batch -- and the b7/b17 pair in both directions,
        # because a substring match would pass one of them.
        ('REPORT cc b6', 'cc', 'b7'),
        ('REPORT cc b17', 'cc', 'b7'),
        ('REPORT cc b7', 'cc', 'b17'),
        # the agent token inside a word is not the agent.
        ('REPORT accc b7', 'cc', 'b7'),
        ('occasional notes b7', 'cc', 'b7'),
        # names the batch and no agent at all.
        ('STATUS b7 all green', 'cc', 'b7'),
        ('', 'cc', 'b7'),
    ]
    for line, ag, ba in good:
        check('first line ACCEPTS %r' % line[:40],
              names_agent_and_batch(line, ag, ba)[0], True)
    for line, ag, ba in bad_cases:
        check('first line REJECTS %r for %s %s' % (line[:40], ag, ba),
              names_agent_and_batch(line, ag, ba)[0], False)

    # The name predicate, in both directions.
    for name, ok in (
            ('SAIRN-handoff-cc-b7.md', True),
            ('SAIRN-report-cc-b7.txt', True),
            ('SAIRN-digest-h1-b20.txt', True),
            ('handoff-cc-2026-10-13.md', False),      # the OLD cc convention
            ('SAIRN-handoff-cc-b7.txt', True),        # matches shape; ext
            ('SAIRN-addendum-h2-b11.txt', False),     # a kind we do not own
            ('SAIRN-report-cc.txt', False),           # no batch
            ('SAIRN-report-cc-7.txt', False),         # batch without the b
    ):
        check('NAME_RE on %r' % name, NAME_RE.match(name), ok)
    # The extension is a SEPARATE finding from the shape, so prove the shape
    # accepts the wrong extension and the kind table is what rejects it.
    check('handoff extension is .md', KINDS['handoff'] == '.md', True)
    check('report extension is .txt', KINDS['report'] == '.txt', True)

    # first_line on raw bytes: CRLF, BOM, no trailing newline, binary noise.
    check('first_line strips CR', first_line(b'REPORT cc b7\r\nx') ==
          'REPORT cc b7', True)
    check('first_line strips BOM',
          first_line(b'\xef\xbb\xbfREPORT cc b7\n') == 'REPORT cc b7', True)
    check('first_line on a single line, no newline',
          first_line(b'REPORT cc b7') == 'REPORT cc b7', True)
    check('first_line does not raise on undecodable bytes',
          first_line(b'\xff\xfe\x00REPORT') != '', True)

    # The ALIASES table has to agree with compaction_brief.py's AGENTS table,
    # or two tools disagree about who h1 is. Re-derived, not asserted.
    try:
        import compaction_brief as cb
        drive_tokens = sorted(set(v['digest'] for v in cb.AGENTS.values()))
        check('ALIASES covers every Drive token compaction_brief knows (%s)'
              % ', '.join(drive_tokens),
              all(t in ALIASES for t in drive_tokens), True)
        for session, toks in cb.AGENTS.items():
            tok = toks['digest']
            check('%s is an accepted spelling of %s' % (session, tok),
                  session in ALIASES.get(tok, ()), True)
    except Exception as exc:                                     # noqa: BLE001
        bad += 1
        total += 1
        print('  LOCK FAILED  compaction_brief.AGENTS could not be read (%s), '
              'so whether the two tools agree about the auditors\' tokens '
              'CANNOT BE CHECKED. That is not a pass.' % exc)

    print('  %d/%d fixtures classify correctly' % (total - bad, total))
    if bad:
        print('  THE CRITERIA ARE BROKEN. No verdict about a real upload is '
              'trustworthy until these pass.')
        return EXIT_FINDING
    return EXIT_CLEAN


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)

    def opt(name, default=None):
        return argv[argv.index(name) + 1] if name in argv else default

    if '--fixtures' in argv:
        return run_fixtures()

    # THE LOCK FIRST, as everywhere else in this repo: a tool whose own
    # criteria are broken reports a pass it never performed.
    rc = run_fixtures()
    if rc != EXIT_CLEAN:
        print('')
        print('COULD NOT RUN: the criteria lock failed.')
        return EXIT_COULD_NOT_RUN
    print('')

    if '--audit' in argv:
        return cmd_audit()

    agent = opt('--agent')
    batch = opt('--batch')
    if not agent or not batch:
        print('COULD NOT RUN: --agent <name> and --batch b<n> are both '
              'required. They are not guessed from the folder name: a clone '
              'renamed SAIRN-cody would answer "cody" and file cc\'s state '
              'under cody.')
        return EXIT_COULD_NOT_RUN
    if not re.match(r'^b\d+$', batch):
        print('COULD NOT RUN: --batch %r is not b<n>.' % batch)
        return EXIT_COULD_NOT_RUN
    if agent not in ALIASES:
        print('COULD NOT RUN: --agent %r is not one of %s. The Drive token for '
              'the auditors is h1/h2, not hover/hover2.'
              % (agent, ', '.join(sorted(ALIASES))))
        return EXIT_COULD_NOT_RUN

    base = opt('--from', REPO)
    paths = {}
    for kind in KINDS:
        paths[kind] = opt('--%s' % kind) or os.path.join(
            base, expected_name(kind, agent, batch))
    return cmd_verify(agent, batch, paths,
                      upload='--verify-only' not in argv,
                      overwrite_foreign='--overwrite-foreign' in argv,
                      why=opt('--why', '') or '')


if __name__ == '__main__':
    sys.exit(main())
