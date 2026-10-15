#!/usr/bin/env python
# OWNER: cc
# written 2026-10-14, batch b12, queue item 1
"""Publish the six-agent SAIRN board to the shared Drive, event-driven.

    python tools/sairn_board_publish.py                 # publish + verify
    python tools/sairn_board_publish.py --dry-run       # render, write nothing
    python tools/sairn_board_publish.py --show          # the board, to stdout
    python tools/sairn_board_publish.py --selftest      # the failing-first arms
    python tools/sairn_board_publish.py --ablation      # what each layer alone catches

Exit 0 clean, 1 findings, 2 COULD NOT RUN.

NOBODY HAS TO REMEMBER TO RUN IT. `sairn_status.py set` calls publish_event()
after every status write, and `sairn_claim.py` reaches the same function
through `sairn_status.publish_claims()`, so a state change, a claim, a release
and a context reading all republish as a side effect of the thing the agent
was already doing. A board that depends on an agent remembering a second
command is a board that is stale exactly when it matters -- at the end of a
batch, when the agent is busy closing out.

── WHAT IT WRITES ──────────────────────────────────────────────────────────
  SAIRN-board.md            one file, all six agents, updated IN PLACE
  SAIRN-latest-<agent>.md   one per agent, under ~60 lines each

"IN PLACE AT A FIXED DRIVE FILE ID" IS A PROPERTY OF THE SYNC MOUNT, NOT OF
THIS TOOL, and the difference is worth stating because it is the one thing
here that cannot be checked locally. The destination is a Google Drive sync
mount. Writing new bytes to an existing PATH makes Drive update that file's
content and keep its id; creating the path anew mints a new id. So the id is
stable as long as nobody deletes the file -- and this tool CANNOT see the id.
The chat-turn connector can, and the id it returned for SAIRN-board.md is
recorded in the board's own header so a later turn can compare rather than
assume. That is a could-not-tell held open, not folded into the pass.

The Drive connector's own `update_file` was tried first and is NOT usable for
this: it changes title and parent only, never content. Hence the mount.

── EVERY FIELD IS DERIVED FROM A NAMED SOURCE, OR SAYS UNKNOWN ─────────────
  state, task, blocked_on, claims, timestamp   the live status registry row
                                               (~/SAIRN-SESSION-LOCKS/status),
                                               which is outside every clone
                                               and needs no fetch
  liveness                                     sairn_status.liveness(), the
                                               one copy of the recycled-pid
                                               defence -- never a second one
  CONTEXT %                                    the row's `context_pct` if the
                                               agent has set one, else the
                                               CONTEXT line of its newest
                                               digest, LABELLED with which
  batch                                        the newest digest on the Drive,
                                               AND the batch token in the live
                                               row -- printed as both when they
                                               disagree, because a row saying
                                               b12 over a digest saying b11 is
                                               the normal mid-batch state and
                                               collapsing them would hide it
  last digest summary                          the digest's own STATUS: line
  open items                                   the digest's own NEXT: line
  routed items                                 docs/*-routed-to-<agent>.md by
                                               filename convention, newest
                                               first, plus a count of the
                                               routing docs whose filename
                                               names no recipient
  chain tip                                    H1/H2: the TIP-BEACON.md
                                               CHECKPOINT in their published
                                               chain directory, with its
                                               published_at and its lag behind
                                               the newest chain-tip-seq file.
                                               Build agents have no audit
                                               chain; they get the shared
                                               origin/main tip, labelled as
                                               shared so it is not read as
                                               per-agent

A field that cannot be derived prints `UNKNOWN -- <why>`. There is no default
that reads like data.

── FAIL-OPEN, AND THAT IS A DELIBERATE ASYMMETRY ───────────────────────────
publish_event() never raises and never changes its caller's exit code. An
unwritable Drive mount must not be the reason an agent cannot record that it
is blocked. The failure is PRINTED on the caller's own output, so it is loud
without being fatal -- an agent that sees `BOARD NOT PUBLISHED` has been told.

The tool invoked directly is the opposite: it exits 1 on any finding and 2 on
could-not-run, because then publishing IS the task.

── VERIFIED AFTER WRITE, BY READING THE BYTES BACK ─────────────────────────
Every file is re-read from the destination and its sha256 compared to the
sha256 of what was sent. "write() returned" and "the bytes are on the mount"
are two claims and only one of them was checked. A mismatch is a finding, and
the board is reported NOT PUBLISHED rather than published-with-a-caveat.
"""
import argparse
import glob
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)

try:
    from checker_kit import EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN
except Exception:                                                # noqa: BLE001
    EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN = 0, 1, 2

CRITERIA_VERSION = '2026-10-14.1'
NL = chr(10)

# The Drive file id the chat-turn connector returned for SAIRN-board.md. It is
# recorded so a later turn can CHECK the id is unchanged rather than assume
# the mount kept it. Empty until the first publish has been read back through
# the connector; a placeholder that looked like an id would be worse.
# READ BACK THROUGH THE CONNECTOR, not assumed. 2026-10-14: the first publish
# created it at 23:37:11Z; the second publish left `id` unchanged and moved
# `modifiedTime` to 23:40:14Z. That pair is the evidence that writing the same
# PATH on the mount updates this file's CONTENT in place and keeps its id --
# the property the brief asked for and the one thing this tool cannot check
# for itself. If a future turn finds a different id here, the file was deleted
# and recreated and every link to it is dead.
BOARD_DRIVE_FILE_ID = '19GSUTWQLddPwZiLEUNfssAjrMxK4vVE1'

BOARD_NAME = 'SAIRN-board.md'
LATEST_NAME = 'SAIRN-latest-%s.md'
LATEST_MAX_LINES = 60

# IMPORTED, NOT RESTATED. drive_upload_verify owns the mount path, the agent
# alias table and the sha helper; a second copy of any of them is a second
# answer waiting to disagree. Import failure is COULD NOT RUN, never a
# fallback to a local guess -- PR 1.11.
_IMPORT_WHY = ''
try:
    import drive_upload_verify as DUV
except Exception as _exc:                                        # noqa: BLE001
    DUV = None
    _IMPORT_WHY = 'drive_upload_verify will not import: %s' % _exc
try:
    import sairn_status as ST
except Exception as _exc:                                        # noqa: BLE001
    ST = None
    _IMPORT_WHY = (_IMPORT_WHY + '; ' if _IMPORT_WHY else '') + \
        'sairn_status will not import: %s' % _exc

# Board label -> (drive token, candidate status-row names). The ROW NAME IS
# RESOLVED BY LOOKING, not by this order: hover writes its row as `hover` and
# its Drive files as `h1`, and that mapping has already been wrong once in a
# tool that assumed one spelling. Candidates come from DUV.ALIASES so there is
# one table of agent spellings on the platform.
BOARD_ORDER = ('hank', 'cc', 'cody', 'fourth', 'H1', 'H2')
BOARD_TOKEN = {'hank': 'hank', 'cc': 'cc', 'cody': 'cody',
               'fourth': 'fourth', 'H1': 'h1', 'H2': 'h2'}

DIGEST_RE = re.compile(r'^SAIRN-digest-(?P<agent>[A-Za-z0-9]+)-b(?P<n>\d+)\.txt$')
SEQ_RE = re.compile(r'^chain-tip-seq(?P<n>\d+)\.(?:msg|tsq|tsr)$')
ROUTED_RE = re.compile(r'-routed(?:-|$)')
BATCH_IN_TEXT = re.compile(r'(?<![0-9a-z])b(\d{1,3})(?![0-9a-z])')


# ── sources ────────────────────────────────────────────────────────────────

def drive_dir():
    """The mount, from the one owner of that fact."""
    return DUV.drive_dir()


def _listdir(path):
    try:
        return sorted(os.listdir(path))
    except OSError:
        return []


def status_rows():
    """{row_name: entry} plus a problem string, from sairn_status.read_all()."""
    entries, problem = ST.read_all()
    if problem:
        return {}, problem
    return {e.get('session'): e for e in (entries or [])}, ''


def resolve_row(label, rows):
    """The status row for a board label, found by trying every known spelling.

    -> (row_or_None, row_name_or_'', why_if_none)
    """
    token = BOARD_TOKEN[label]
    for sp in DUV.ALIASES.get(token, (token,)):
        if sp in rows:
            return rows[sp], sp, ''
    tried = ', '.join(DUV.ALIASES.get(token, (token,)))
    return None, '', ('no status row under any known spelling (tried: %s) -- '
                      'this agent has never written to the registry, which is '
                      'NOT the same as idle' % tried)


def newest_digest(token, ddir):
    """(batch_int, path) for the agent's highest-numbered digest, or (None, '').

    HIGHEST NUMBER, NOT NEWEST MTIME. A re-upload of an old digest changes its
    mtime and would otherwise walk the board backwards.
    """
    best, best_path = None, ''
    for fn in _listdir(ddir):
        m = DIGEST_RE.match(fn)
        if not m:
            continue
        agent = m.group('agent').lower()
        if agent != token and agent not in DUV.ALIASES.get(token, ()):
            continue
        n = int(m.group('n'))
        if best is None or n > best:
            best, best_path = n, os.path.join(ddir, fn)
    return best, best_path


def digest_fields(path):
    """{status, next, context} from a digest's own labelled lines.

    Each value is the text after the label up to the next labelled line, so a
    STATUS that wraps is not truncated at the newline. A label that is absent
    yields '' and the caller says UNKNOWN -- it does not borrow another line.
    """
    out = {'status': '', 'next': '', 'context': ''}
    if not path:
        return out
    try:
        with io.open(path, encoding='utf-8', errors='replace') as fh:
            text = fh.read()
    except OSError:
        return out
    labels = ('STATUS', 'DECISION-NEEDED', 'CHANGED', 'EVIDENCE-path',
              'UNVERIFIED', 'NEXT', 'CONTEXT', 'SHA256', 'END-OF-REPORT')
    # A label starts a line and is followed by ':' or whitespace -- h2 writes
    # `CONTEXT:` and cc writes `CONTEXT `, and both are the same field.
    pat = re.compile(r'^(%s)\s*:?\s*' % '|'.join(labels), re.M)
    hits = [(m.group(1), m.start(), m.end()) for m in pat.finditer(text)]
    for i, (name, _s, e) in enumerate(hits):
        end = hits[i + 1][1] if i + 1 < len(hits) else len(text)
        body = ' '.join(text[e:end].split())
        key = {'STATUS': 'status', 'NEXT': 'next', 'CONTEXT': 'context'}.get(name)
        if key and not out[key]:
            out[key] = body
    return out


def git_tip():
    """(short_sha, why). The shared chain every build agent lands on."""
    try:
        p = subprocess.Popen(
            ['git', '-C', REPO, 'rev-parse', '--short', 'origin/main'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate(timeout=30)
        if p.returncode != 0:
            return '', 'git rev-parse failed: %s' % err.decode(
                'utf-8', 'replace').strip()[:90]
        return out.decode('utf-8', 'replace').strip(), ''
    except Exception as exc:                                     # noqa: BLE001
        return '', 'git would not run: %s' % str(exc)[:90]


def chain_tip(token, ddir):
    """The audit-chain tip for an auditor, read from its published beacon.

    -> text. Reports the beacon's OWN published_at and how far it lags the
    newest chain-tip-seq file beside it, because a beacon is a checkpoint
    claim and a stale one is the exact thing a reader would otherwise take as
    current. Both numbers or neither.
    """
    cdir = os.path.join(ddir, 'hover-chain-%s' % token)
    if not os.path.isdir(cdir):
        return 'UNKNOWN -- no %s directory on the Drive' % os.path.basename(cdir)
    beacon = os.path.join(cdir, 'TIP-BEACON.md')
    seqs = [int(m.group('n')) for m in
            (SEQ_RE.match(fn) for fn in _listdir(cdir)) if m]
    newest_seq = max(seqs) if seqs else None
    if not os.path.isfile(beacon):
        return ('UNKNOWN -- no TIP-BEACON.md; newest chain-tip file is seq %s'
                % (newest_seq if newest_seq is not None else 'none'))
    try:
        with io.open(beacon, encoding='utf-8', errors='replace') as fh:
            text = fh.read()
    except OSError as exc:
        return 'UNKNOWN -- TIP-BEACON.md unreadable: %s' % str(exc)[:70]
    m = re.search(r'^CHECKPOINT:\s*(\{.*\})\s*$', text, re.M)
    if not m:
        return 'UNKNOWN -- TIP-BEACON.md carries no CHECKPOINT line'
    try:
        cp = json.loads(m.group(1))
    except Exception as exc:                                     # noqa: BLE001
        return 'UNKNOWN -- CHECKPOINT line does not parse: %s' % str(exc)[:70]
    seq = cp.get('seq')
    bits = ['seq %s' % seq,
            'hash %s' % str(cp.get('hash') or '')[:12],
            'beacon published %s' % (cp.get('published_at') or 'UNKNOWN')]
    if newest_seq is not None and isinstance(seq, int) and newest_seq > seq:
        bits.append('BEACON IS %d BEHIND the newest chain-tip file (seq %d) -- '
                    'the beacon is a checkpoint claim, not the live tip'
                    % (newest_seq - seq, newest_seq))
    return '; '.join(bits)


def routed_for(label):
    """(newest_paths, ambiguous_count) -- routing docs addressed to this agent.

    BY FILENAME CONVENTION, and that is said out loud rather than presented as
    a complete list: `docs/<date>-<from>-routed-to-<to>.md` names its
    recipient, and plenty of real routing docs do not. The ones that do not
    are COUNTED rather than dropped, so a reader can see the convention's
    coverage instead of trusting a list built from half of it.
    """
    docs = os.path.join(REPO, 'docs')
    mine, ambiguous = [], 0
    pat = re.compile(r'-routed-to-%s(?:[-.]|$)' % re.escape(label.lower()))
    for fn in _listdir(docs):
        if not fn.endswith('.md') or not ROUTED_RE.search(fn):
            continue
        low = fn.lower()
        if pat.search(low):
            mine.append(fn)
        elif '-routed-to-' not in low:
            ambiguous += 1
    mine.sort(reverse=True)          # the names are date-prefixed
    return mine, ambiguous


def context_for(row, dfields, dbatch):
    """(text, source). The live reading wins; the digest is the fallback."""
    live = (row or {}).get('context_pct')
    if live not in (None, ''):
        # THE AGE OF THE NUMBER, NOT THE AGE OF THE ROW. A context reading set
        # an hour ago under a row written a minute ago reads as current and is
        # not; the two stamps are different facts and both are printed.
        return ('%s%%' % live,
                'live status row, set %s'
                % ((row or {}).get('context_set') or 'at an unrecorded time'))
    if dfields.get('context'):
        return dfields['context'][:120], 'digest b%s' % dbatch
    return ('UNKNOWN -- the agent has set no context_pct and its newest digest '
            'carries no CONTEXT line'), 'none'


def claims_of(row):
    """[(app, task_head)] from the row's published claims, or []."""
    out = []
    # `subject`, which is sairn_claim's own field name for the app or area a
    # claim covers. Read from the publisher's spelling rather than a guessed
    # one -- `app` was the guess, and it rendered every claim as `?`.
    for c in ((row or {}).get('claims') or []):
        if isinstance(c, dict):
            out.append((str(c.get('subject') or c.get('app') or '?'),
                        ' '.join(str(c.get('task') or '').split())[:110]))
    return out


def collect(ddir=None):
    """[row dicts] for the board, plus a list of problems. Never raises."""
    problems = []
    if DUV is None or ST is None:
        return None, [_IMPORT_WHY or 'a required module would not import']
    ddir = ddir or drive_dir()
    if not os.path.isdir(ddir):
        problems.append('the Drive mount %s is not a directory -- every '
                        'Drive-sourced field below will read UNKNOWN' % ddir)
    rows, prob = status_rows()
    if prob:
        problems.append('status registry: %s' % prob)
    sha, why = git_tip()
    shared_tip = ('git origin/main %s (SHARED -- the same value for all four '
                  'build agents by construction, not a per-agent chain)' % sha
                  ) if sha else 'UNKNOWN -- %s' % why
    out = []
    for label in BOARD_ORDER:
        token = BOARD_TOKEN[label]
        row, row_name, why_no_row = resolve_row(label, rows)
        dbatch, dpath = newest_digest(token, ddir)
        dfields = digest_fields(dpath)
        ctx, ctx_src = context_for(row, dfields, dbatch)
        live_b = None
        if row:
            hay = '%s %s' % (row.get('task') or '',
                             ' '.join(t for _a, t in claims_of(row)))
            ms = BATCH_IN_TEXT.findall(hay)
            if ms:
                live_b = max(int(x) for x in ms)
        routed, ambiguous = routed_for(label)
        state = 'UNKNOWN'
        live_state = ''
        if row and row.get('unreadable'):
            state = 'UNREADABLE -- %s' % row['unreadable']
        elif row:
            state = str(row.get('state') or 'UNKNOWN')
            try:
                live_state = ST.liveness(row)[0]
            except Exception as exc:                             # noqa: BLE001
                live_state = 'UNKNOWN (%s)' % str(exc)[:50]
        out.append({
            'label': label,
            'token': token,
            'row_name': row_name,
            'row_missing': why_no_row,
            'state': state,
            'liveness': live_state,
            'task': ' '.join(str((row or {}).get('task') or '').split())[:220],
            'blocked_on': ' '.join(
                str((row or {}).get('blocked_on') or '').split())[:200],
            'updated': (row or {}).get('updated') or '',
            'age_h': (round((row or {}).get('age_seconds', 0) / 3600.0, 1)
                      if row and 'age_seconds' in row else None),
            'claims': claims_of(row),
            'context': ctx,
            'context_source': ctx_src,
            'digest_batch': dbatch,
            'digest_status': dfields['status'],
            'digest_next': dfields['next'],
            'live_batch': live_b,
            'routed': routed,
            'routed_ambiguous': ambiguous,
            'chain': (chain_tip(token, ddir) if label in ('H1', 'H2')
                      else shared_tip),
        })
    # ── AN AGENT NOBODY LISTED IS A FINDING, NOT AN OMISSION ───────────────
    # CLAUDE.md named four clones for weeks after a fifth was pushing commits.
    # The board covers six by name; anything else that has a status row or a
    # digest is NAMED here rather than silently left off.
    known = set()
    for label in BOARD_ORDER:
        known.add(BOARD_TOKEN[label])
        known.update(DUV.ALIASES.get(BOARD_TOKEN[label], ()))
    extra_rows = sorted(n for n in rows if n not in known)
    extra_digests = sorted({m.group('agent').lower() for m in
                            (DIGEST_RE.match(fn) for fn in _listdir(ddir)) if m}
                           - known)
    return out, problems, extra_rows, extra_digests


# ── rendering ──────────────────────────────────────────────────────────────

def _cell(text, dash='(none)'):
    return text if str(text).strip() else dash


def render_board(rows, problems, extra_rows, extra_digests, reason, ddir):
    L = ['# SAIRN board -- all six agents, one file',
         '',
         'Generated by `tools/sairn_board_publish.py` (OWNER cc, criteria %s) '
         'as a side effect of a status, claim or context change. Nobody runs '
         'it by hand and nobody has to remember to.' % CRITERIA_VERSION,
         '',
         '- **Published at:** %s (local)' % time.strftime('%Y-%m-%dT%H:%M:%S'),
         '- **Trigger:** %s' % reason,
         '- **Status registry:** `%s` -- outside every clone, no fetch needed'
         % ST.STATUS_DIR,
         '- **Drive mount:** `%s` (folder id `%s`)' % (ddir, DUV.DRIVE_FOLDER_ID),
         '- **This file\'s Drive id:** %s' % (
             '`%s` -- compare it, do not assume it' % BOARD_DRIVE_FILE_ID
             if BOARD_DRIVE_FILE_ID else
             'NOT YET READ BACK through the connector. The mount keeps a '
             'file\'s id when its CONTENT is replaced and mints a new one when '
             'the path is created afresh, and this tool cannot see either.'),
         '']
    if problems:
        L += ['> **THIS RUN COULD NOT READ EVERYTHING.** Fields sourced from '
              'what failed read UNKNOWN below; none of them defaulted to '
              'something that looks like data.', '']
        L += ['> - %s' % p for p in problems] + ['']
    if extra_rows or extra_digests:
        L += ['> **AN AGENT IS PRESENT THAT THIS BOARD DOES NOT COVER.** The '
              'six names are fixed in the generator; anything else with a '
              'status row or a digest is named here rather than dropped.', '']
        if extra_rows:
            L += ['> - status rows: %s' % ', '.join(extra_rows)]
        if extra_digests:
            L += ['> - Drive digests: %s' % ', '.join(extra_digests)]
        L += ['']
    L += ['## At a glance', '',
          '| agent | state | liveness | batch | CONTEXT | claims | blocked on | row age |',
          '|---|---|---|---|---|---|---|---|']
    for r in rows:
        batch = ('b%s' % r['digest_batch']) if r['digest_batch'] else 'UNKNOWN'
        if r['live_batch'] and r['digest_batch'] and \
                r['live_batch'] != r['digest_batch']:
            batch = 'b%s live / last digest b%s' % (r['live_batch'],
                                                    r['digest_batch'])
        L.append('| **%s** | %s | %s | %s | %s | %d | %s | %s |' % (
            r['label'], _cell(r['state'], 'UNKNOWN'),
            _cell(r['liveness'], '-'), batch,
            r['context'][:40], len(r['claims']),
            _cell(r['blocked_on'], '-'),
            ('%sh' % r['age_h']) if r['age_h'] is not None else '-'))
    L += ['', 'CONTEXT is the agent\'s own reading. Its source is named per '
              'agent below -- a live row and a figure copied out of a digest '
              'written hours ago are not the same claim.', '']
    for r in rows:
        L += ['---', '', '## %s' % r['label'], '']
        if r['row_missing']:
            L += ['**No live status row.** %s' % r['row_missing'], '']
        else:
            L += ['- **state:** %s (liveness %s, row written %s, %s)' % (
                r['state'], _cell(r['liveness'], 'UNKNOWN'),
                _cell(r['updated'], 'UNKNOWN'),
                ('%sh old' % r['age_h']) if r['age_h'] is not None
                else 'age unknown')]
            L += ['- **task:** %s' % _cell(r['task'])]
            if r['blocked_on']:
                L += ['- **BLOCKED ON:** %s' % r['blocked_on']]
        L += ['- **CONTEXT:** %s  _(source: %s)_' % (r['context'],
                                                     r['context_source'])]
        L += ['- **chain tip:** %s' % r['chain']]
        if r['claims']:
            L += ['- **claims held (%d):**' % len(r['claims'])]
            L += ['    - `%s` -- %s' % (a, t) for a, t in r['claims']]
        else:
            L += ['- **claims held:** none published on its row. An empty '
                  '`claims` key is also what a session running an older '
                  '`sairn_claim.py` looks like -- `.claude/claims/%s.json` in '
                  'git is the authority.' % r['token']]
        L += ['- **last digest (b%s):** %s' % (
            r['digest_batch'] if r['digest_batch'] else '?',
            _cell(r['digest_status'][:700], 'UNKNOWN -- no digest found'))]
        L += ['- **open items (that digest\'s own NEXT):** %s'
              % _cell(r['digest_next'][:700], 'UNKNOWN -- no NEXT line')]
        if r['routed']:
            L += ['- **routed to it (by filename, newest 5 of %d):**'
                  % len(r['routed'])]
            L += ['    - `docs/%s`' % fn for fn in r['routed'][:5]]
        else:
            L += ['- **routed to it:** no `docs/*-routed-to-%s*.md` file'
                  % r['label'].lower()]
        if r['routed_ambiguous']:
            L += ['    - plus **%d routing doc(s) whose filename names no '
                  'recipient** -- not attributed to anybody here rather than '
                  'guessed' % r['routed_ambiguous']]
        L += ['']
    L += ['---', '',
          '## What this board does not tell you', '',
          '- **It is as fresh as the last status, claim or context change.** '
          'Six agents each republish the whole board on their own events, so '
          'any one agent going quiet leaves ITS rows stale while the file\'s '
          'own timestamp keeps moving. Read each agent\'s row age, not the '
          'header.',
          '- **The bytes are verified on the mount, not in Google\'s index.** '
          'A read-back proves the file is in the sync set with the right '
          'sha256. It does not prove Drive has acknowledged it. That is a '
          'could-not-tell, and the thing that closes it is a Drive-side read '
          'from a chat turn, which goes through the API instead of the mount.',
          '- **`claims` here is the fast path.** `.claude/claims/*.json` on '
          '`origin/main` stays authoritative.',
          '- **Build agents have no audit chain.** Their chain-tip cell is the '
          'shared `origin/main` tip and is identical across all four by '
          'construction.',
          '']
    return NL.join(L) + NL


def render_latest(r, reason):
    """The per-agent file. Under LATEST_MAX_LINES lines, and that is CHECKED."""
    L = ['# SAIRN latest -- %s' % r['label'],
         '',
         'Written by cc\'s `tools/sairn_board_publish.py` on a %s. Full board: '
         '`SAIRN-board.md`.' % reason,
         '',
         '- **state:** %s (liveness %s, row %s)' % (
             _cell(r['state'], 'UNKNOWN'), _cell(r['liveness'], 'UNKNOWN'),
             _cell(r['updated'], 'UNKNOWN')),
         '- **task:** %s' % _cell(r['task'])]
    if r['blocked_on']:
        L += ['- **BLOCKED ON:** %s' % r['blocked_on']]
    L += ['- **CONTEXT:** %s  _(source: %s)_' % (r['context'],
                                                 r['context_source']),
          '- **chain tip:** %s' % r['chain'],
          '']
    L += ['## Last digest (b%s) -- its own STATUS line' % (
        r['digest_batch'] if r['digest_batch'] else '?'), '',
        _cell(r['digest_status'][:900], 'UNKNOWN -- no digest found on the Drive'),
        '',
        '## Open items -- that digest\'s own NEXT line', '',
        _cell(r['digest_next'][:900], 'UNKNOWN -- that digest carries no NEXT line'),
        '']
    L += ['## Routed to it', '']
    if r['routed']:
        L += ['- `docs/%s`' % fn for fn in r['routed'][:6]]
        if len(r['routed']) > 6:
            L += ['- (%d older, see the board)' % (len(r['routed']) - 6)]
    else:
        L += ['- none matching `docs/*-routed-to-%s*.md`' % r['label'].lower()]
    if r['routed_ambiguous']:
        L += ['- plus %d routing doc(s) naming no recipient in the filename, '
              'not attributed here' % r['routed_ambiguous']]
    L += ['', '## Claims held', '']
    if r['claims']:
        L += ['- `%s` -- %s' % (a, t[:150]) for a, t in r['claims']]
    else:
        L += ['- none on its registry row; `.claude/claims/%s.json` in git is '
              'the authority' % r['token']]
    L += ['',
          '_Mount read-back verified by sha256. That does NOT prove Google '
          'acknowledged the upload -- only a Drive-side API read does._', '']
    text = NL.join(L) + NL
    return text


# ── write + verify ─────────────────────────────────────────────────────────

def write_verified(path, text):
    """(ok, why). Write, then read the bytes back and compare sha256."""
    data = text.encode('utf-8')
    tmp = None
    try:
        d = os.path.dirname(path) or '.'
        fd, tmp = tempfile.mkstemp(prefix='.board-', dir=d)
        with os.fdopen(fd, 'wb') as fh:
            fh.write(data)
        os.replace(tmp, path)
        tmp = None
    except Exception as exc:                                     # noqa: BLE001
        return False, 'write failed: %s' % str(exc)[:160]
    finally:
        if tmp and os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
    back, why = DUV.read_bytes(path)
    if back is None:
        return False, 'written and then NOT READABLE: %s' % why[:120]
    if DUV.sha256_of(back) != DUV.sha256_of(data):
        return False, ('read-back sha256 MISMATCH -- sent %d bytes sha %s, '
                       'read %d bytes sha %s. Reported NOT PUBLISHED rather '
                       'than published-with-a-caveat.'
                       % (len(data), DUV.sha256_of(data)[:12], len(back),
                          DUV.sha256_of(back)[:12]))
    return True, 'verified %d bytes sha %s' % (len(data),
                                               DUV.sha256_of(data)[:12])


def publish(reason='manual run', ddir=None, dry_run=False, quiet=False):
    """(exit_code, lines). The whole job: collect, render, write, verify."""
    out = []
    got = collect(ddir)
    if got[0] is None:
        return EXIT_COULD_NOT_RUN, ['COULD NOT RUN -- %s' % got[1][0]]
    rows, problems, extra_rows, extra_digests = got
    ddir = ddir or drive_dir()
    board = render_board(rows, problems, extra_rows, extra_digests, reason, ddir)
    files = [(BOARD_NAME, board)]
    for r in rows:
        text = render_latest(r, reason)
        n = text.count(NL)
        if n > LATEST_MAX_LINES:
            # TRUNCATED LOUDLY, never silently. The brief's ceiling is a real
            # constraint and a file that quietly blew through it would be the
            # ceiling not existing.
            keep = text.split(NL)[:LATEST_MAX_LINES - 2]
            text = NL.join(keep + [
                '', '_TRUNCATED at %d lines (was %d) to hold the ~%d-line '
                'ceiling -- the full text is in SAIRN-board.md._'
                % (LATEST_MAX_LINES, n, LATEST_MAX_LINES), ''])
            out.append('  note: SAIRN-latest-%s.md truncated %d -> %d lines'
                       % (r['label'], n, text.count(NL)))
        files.append((LATEST_NAME % r['label'], text))
    if dry_run:
        out.append('DRY RUN -- nothing written. Would write %d file(s) to %s:'
                   % (len(files), ddir))
        for name, text in files:
            out.append('  %-26s %6d bytes  %3d lines'
                       % (name, len(text.encode('utf-8')), text.count(NL)))
        return EXIT_CLEAN, out
    if not os.path.isdir(ddir):
        return EXIT_COULD_NOT_RUN, [
            'COULD NOT RUN -- no Drive mount at %s. The board was NOT '
            'published and nothing here reports otherwise.' % ddir]
    bad = []
    for name, text in files:
        ok, why = write_verified(os.path.join(ddir, name), text)
        out.append('  %-26s %s  %s' % (name, 'OK  ' if ok else 'FAIL', why))
        if not ok:
            bad.append(name)
    if bad:
        out.insert(0, 'BOARD NOT PUBLISHED -- %d of %d file(s) failed: %s'
                      % (len(bad), len(files), ', '.join(bad)))
        return EXIT_FINDING, out
    out.insert(0, 'board published and read back: %d file(s) in %s'
                  % (len(files), ddir))
    if problems:
        out.append('  %d source(s) could not be read this run; the affected '
                   'fields say UNKNOWN in the file:' % len(problems))
        out += ['    - %s' % p for p in problems]
        return EXIT_FINDING, out
    return EXIT_CLEAN, out


# ── the event-driven entry point ───────────────────────────────────────────

def publish_event(reason, quiet=False):
    """Called BY sairn_status after a write. FAIL-OPEN. Never raises.

    -> True if the board was published and verified, False otherwise. The
    caller's exit code must not depend on this: an unwritable Drive mount
    cannot be allowed to stop an agent recording that it is blocked. The
    failure is PRINTED so it is loud without being fatal.

    SAIRN_BOARD_PUBLISH=off disables it, and says so when it does -- a
    silently disabled publisher is a board that stops updating with nothing
    anywhere saying why.
    """
    if os.environ.get('SAIRN_BOARD_PUBLISH', '').lower() in ('off', '0', 'no'):
        print('  BOARD PUBLISH DISABLED by SAIRN_BOARD_PUBLISH -- the Drive '
              'board was NOT updated by this change.')
        return False
    try:
        code, lines = publish(reason=reason)
    except Exception as exc:                                     # noqa: BLE001
        print('  BOARD NOT PUBLISHED -- the publisher raised (%s). Your '
              'status/claim write succeeded; the Drive board is stale.'
              % str(exc)[:140])
        return False
    if code == EXIT_CLEAN:
        if not quiet:
            print('  drive board republished (%s)' % reason)
        return True
    print('  BOARD NOT PUBLISHED or published with findings -- your '
          'status/claim write succeeded, the Drive board may be stale:')
    for ln in lines:
        print('  %s' % ln)
    return False


# ── failing-first arms ─────────────────────────────────────────────────────
#
# EVERY ARM IS DRIVEN AGAINST A DELIBERATELY BAD INPUT AND MUST FAIL ON IT.
# An arm that only ever sees good data is indistinguishable from an arm that
# tests nothing, and this platform has shipped five of those. Each arm below
# names the real defect shape it stands for.

def _fixture_dirs(tmp):
    sdir = os.path.join(tmp, 'status')
    ddir = os.path.join(tmp, 'drive')
    os.makedirs(sdir)
    os.makedirs(ddir)
    return sdir, ddir


def _write(path, text):
    with io.open(path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)


def _good_fixture(sdir, ddir):
    """A fixture where every field IS derivable. The arms break it one way."""
    for name, state in (('hank', 'working'), ('cc', 'working'),
                        ('cody', 'idle'), ('fourth', 'working'),
                        ('hover', 'idle'), ('hover2', 'working')):
        _write(os.path.join(sdir, name + '.json'), json.dumps({
            'session': name, 'state': state, 'task': 'fixture b7 task',
            'updated': '2026-10-14T00:00:00', 'context_pct': 40,
            'claims': [{'app': name, 'task': 'fixture claim'}]}))
    for tok in ('hank', 'cc', 'cody', 'fourth', 'h1', 'h2'):
        _write(os.path.join(ddir, 'SAIRN-digest-%s-b7.txt' % tok),
               'DIGEST %s b7\nSTATUS: fixture status line.\n'
               'NEXT: fixture next line.\nCONTEXT 40%% used\n' % tok)
    for tok in ('h1', 'h2'):
        cd = os.path.join(ddir, 'hover-chain-%s' % tok)
        os.makedirs(cd)
        _write(os.path.join(cd, 'TIP-BEACON.md'),
               'CHECKPOINT: {"count": 10, "hash": "abc123def456", '
               '"published_at": "2026-10-14T00:00:00Z", "seq": 10}\n')
        _write(os.path.join(cd, 'chain-tip-seq10.msg'), 'x')


def _board_for(sdir, ddir):
    """Render the board against a fixture, with STATUS_DIR pointed at it."""
    old = ST.STATUS_DIR
    ST.STATUS_DIR = sdir
    try:
        got = collect(ddir)
        if got[0] is None:
            return '', got[1]
        rows, problems, er, ed = got
        return render_board(rows, problems, er, ed, 'selftest', ddir), problems
    finally:
        ST.STATUS_DIR = old


def _latest_for(sdir, ddir, label):
    old = ST.STATUS_DIR
    ST.STATUS_DIR = sdir
    try:
        rows = collect(ddir)[0] or []
        for r in rows:
            if r['label'] == label:
                return render_latest(r, 'selftest')
        return ''
    finally:
        ST.STATUS_DIR = old


_ARMS = []


def arm(name, defect):
    def deco(fn):
        _ARMS.append((name, defect, fn))
        return fn
    return deco


@arm('A1-missing-row', 'an agent that has NEVER written a status row is '
                       'reported as idle instead of as absent')
def _a1(sdir, ddir):
    os.remove(os.path.join(sdir, 'hank.json'))
    txt = _board_for(sdir, ddir)[0]
    return ('No live status row' in txt
            and 'never written to the registry' in txt), txt


@arm('A2-unknown-context', 'a missing CONTEXT reads as a number rather than '
                           'as UNKNOWN')
def _a2(sdir, ddir):
    d = json.load(io.open(os.path.join(sdir, 'cc.json'), encoding='utf-8'))
    d.pop('context_pct')
    _write(os.path.join(sdir, 'cc.json'), json.dumps(d))
    _write(os.path.join(ddir, 'SAIRN-digest-cc-b7.txt'),
           'DIGEST cc b7\nSTATUS: s.\nNEXT: n.\n')
    txt = _board_for(sdir, ddir)[0]
    return ('UNKNOWN -- the agent has set no context_pct' in txt), txt


@arm('A3-stale-beacon', 'a TIP-BEACON checkpoint behind the real chain is '
                        'printed as the current tip')
def _a3(sdir, ddir):
    cd = os.path.join(ddir, 'hover-chain-h2')
    _write(os.path.join(cd, 'chain-tip-seq99.msg'), 'x')
    txt = _board_for(sdir, ddir)[0]
    return ('BEACON IS 89 BEHIND' in txt), txt


@arm('A4-unlisted-agent', 'a seventh agent with a status row is silently '
                          'left off the board')
def _a4(sdir, ddir):
    _write(os.path.join(sdir, 'newguy.json'),
           json.dumps({'session': 'newguy', 'state': 'working'}))
    txt = _board_for(sdir, ddir)[0]
    return ('THIS BOARD DOES NOT COVER' in txt and 'newguy' in txt), txt


@arm('A5-readback-mismatch', 'a write that did not land is reported as '
                             'published')
def _a5(sdir, ddir):
    path = os.path.join(ddir, 'probe.md')
    real = DUV.read_bytes

    def lying(p):
        if os.path.basename(p) == 'probe.md':
            return b'not what was sent', ''
        return real(p)
    DUV.read_bytes = lying
    try:
        ok, why = write_verified(path, 'the real content\n')
    finally:
        DUV.read_bytes = real
    return (not ok and 'MISMATCH' in why), why


@arm('A6-unreadable-destination', 'a destination that cannot be written is '
                                  'reported as a successful publish')
def _a6(sdir, ddir):
    gone = os.path.join(ddir, 'no-such-dir', 'x.md')
    ok, why = write_verified(gone, 'content\n')
    return (not ok and 'write failed' in why), why


@arm('A7-fail-open', 'a broken publisher takes its CALLER down with it, so an '
                     'agent cannot record that it is blocked')
def _a7(sdir, ddir):
    real = globals()['publish']

    def exploding(**kw):
        raise RuntimeError('fixture explosion')
    globals()['publish'] = exploding
    try:
        res = publish_event('selftest')
    finally:
        globals()['publish'] = real
    return (res is False), 'publish_event returned %r without raising' % res


@arm('A8-latest-ceiling', 'a per-agent file silently exceeds the ~60-line '
                          'ceiling')
def _a8(sdir, ddir):
    # THE REAL PATH TO AN OVERLONG FILE IS A LIST, NOT A LONG FIELD, and the
    # ablation is what established that. A 1,800-character STATUS is one line
    # and the renderer caps it at 900 characters anyway, so a long-field
    # fixture left `latest-ceiling` UNPROVEN -- the layer could be deleted and
    # no arm noticed. The uncapped list is `claims`: an agent holding 60 of
    # them renders 60 lines. That is the shape the ceiling exists for.
    d = json.load(io.open(os.path.join(sdir, 'cc.json'), encoding='utf-8'))
    d['claims'] = [{'app': 'cc', 'task': 'claim number %d' % i}
                   for i in range(60)]
    _write(os.path.join(sdir, 'cc.json'), json.dumps(d))
    old = ST.STATUS_DIR
    ST.STATUS_DIR = sdir
    try:
        code, lines = publish(reason='selftest', ddir=ddir)
    finally:
        ST.STATUS_DIR = old
    body = NL.join(lines)
    nlines = 0
    p = os.path.join(ddir, LATEST_NAME % 'cc')
    if os.path.isfile(p):
        nlines = io.open(p, encoding='utf-8').read().count(NL)
    # ASSERTED AGAINST A LITERAL, NOT AGAINST LATEST_MAX_LINES. An arm that
    # checks the file against the same constant the code used is a tautology:
    # raise the constant and the arm still passes while the file doubles. The
    # ablation found exactly that -- `latest-ceiling` could be removed and no
    # arm noticed. 60 is the brief's own number, written here on purpose.
    return (0 < nlines <= 60 and code in (EXIT_CLEAN, EXIT_FINDING)), \
        '%d lines (ceiling asserted at a literal 60), exit %d: %s' % (
            nlines, code, body[:160])


@arm('A9-no-mount', 'a missing Drive mount is reported as a publish rather '
                    'than as COULD NOT RUN')
def _a9(sdir, ddir):
    code, lines = publish(reason='selftest',
                          ddir=os.path.join(ddir, 'absent'))
    return (code == EXIT_COULD_NOT_RUN
            and 'NOT published' in NL.join(lines)), NL.join(lines)[:200]


@arm('A10-digest-label-bleed', 'a digest with no NEXT line borrows the next '
                               'labelled block as its open items')
def _a10(sdir, ddir):
    _write(os.path.join(ddir, 'SAIRN-digest-cody-b7.txt'),
           'DIGEST cody b7\nSTATUS: real status.\n'
           'UNVERIFIED: this is not the next line.\nCONTEXT 1% used\n')
    txt = _board_for(sdir, ddir)[0]
    return ('UNKNOWN -- no NEXT line' in txt
            and 'this is not the next line' not in txt), txt


@arm('A11-older-digest-wins', 'a re-uploaded old digest walks an agent\'s '
                              'batch backwards because mtime beat the number')
def _a11(sdir, ddir):
    _write(os.path.join(ddir, 'SAIRN-digest-cc-b3.txt'),
           'DIGEST cc b3\nSTATUS: ancient.\nNEXT: ancient next.\n')
    os.utime(os.path.join(ddir, 'SAIRN-digest-cc-b3.txt'), None)
    txt = _board_for(sdir, ddir)[0]
    return ('ancient' not in txt and 'b7' in txt), txt


@arm('A12-blocked-visible', 'a blocked agent\'s blocker is not on the board')
def _a12(sdir, ddir):
    d = json.load(io.open(os.path.join(sdir, 'fourth.json'), encoding='utf-8'))
    d['state'] = 'blocked'
    d['blocked_on'] = 'a credential only Michael has'
    _write(os.path.join(sdir, 'fourth.json'), json.dumps(d))
    txt = _board_for(sdir, ddir)[0]
    return ('a credential only Michael has' in txt
            and 'BLOCKED ON' in txt), txt


@arm('A13-claim-subject', 'a mirrored claim renders as `?` because the board '
                          'guessed a field name the publisher does not use')
def _a13(sdir, ddir):
    d = json.load(io.open(os.path.join(sdir, 'cc.json'), encoding='utf-8'))
    d['claims'] = [{'subject': 'tools', 'task': 'the real claim text'}]
    _write(os.path.join(sdir, 'cc.json'), json.dumps(d))
    txt = _board_for(sdir, ddir)[0]
    return ('`tools` -- the real claim text' in txt), txt


@arm('A14-claims-survive-set', 'a status change wipes the mirrored claims, so '
                               'an agent holding a claim shows zero')
def _a14(sdir, ddir):
    # DRIVEN THROUGH sairn_status.payload() RATHER THAN THE BOARD, because the
    # defect is there and an arm against the board would pass on a fixture
    # whose claims nothing had wiped yet. The pre-fix payload() built a fresh
    # dict and dropped all three claim keys; this fails on that version.
    class _A(object):
        session = task = item = blocked_on = note = note_replace = None
        state = 'working'
        context = None
    prev = {'claims': [{'subject': 'tools', 'task': 't'}],
            'claims_updated': '2026-10-14T00:00:00',
            'claims_heartbeat': 1.0}
    got = ST.payload(_A(), prev)
    return (got.get('claims') == prev['claims']
            and got.get('claims_heartbeat') == 1.0), \
        'payload kept %s' % sorted(k for k in got if k.startswith('claim'))


def _run_arms(verbose=True, only=None):
    """(passed, failed, [failures]). Each arm gets a fresh fixture."""
    passed = failed = 0
    fails = []
    for name, defect, fn in _ARMS:
        if only and name not in only:
            continue
        tmp = tempfile.mkdtemp(prefix='board-arm-')
        try:
            sdir, ddir = _fixture_dirs(tmp)
            _good_fixture(sdir, ddir)
            ok, detail = fn(sdir, ddir)
        except Exception as exc:                                 # noqa: BLE001
            ok, detail = False, 'arm raised: %s' % exc
        finally:
            _rmtree(tmp)
        if ok:
            passed += 1
            if verbose:
                print('  PASS  %-26s catches: %s' % (name, defect))
        else:
            failed += 1
            fails.append((name, defect, str(detail)[:300]))
            if verbose:
                print('  FAIL  %-26s did NOT catch: %s' % (name, defect))
                print('        %s' % str(detail)[:300])
    return passed, failed, fails


def _rmtree(path):
    for root, dirs, files in os.walk(path, topdown=False):
        for f in files:
            try:
                os.remove(os.path.join(root, f))
            except OSError:
                pass
        for d in dirs:
            try:
                os.rmdir(os.path.join(root, d))
            except OSError:
                pass
    try:
        os.rmdir(path)
    except OSError:
        pass


def selftest():
    print('sairn_board_publish --selftest  (criteria %s)' % CRITERIA_VERSION)
    print('%d arm(s), each driven against a DELIBERATELY BAD fixture.'
          % len(_ARMS))
    print('')
    passed, failed, fails = _run_arms()
    print('')
    print('  %d/%d arms fire on the defect they name' % (passed, len(_ARMS)))
    if failed:
        print('  %d ARM(S) DID NOT FIRE -- the layer each one stands for is '
              'UNPROVEN, not proven absent:' % failed)
        for n, d, why in fails:
            print('    %s -- %s' % (n, d))
        return EXIT_FINDING
    print('')
    print('  A POSITIVE CONTROL IS NOT A SECOND PASS. The arms above prove '
          'each layer fires on bad input. `--ablation` is the other half: it '
          'removes ONE named layer at a time from a CLEAN fixture and '
          'measures what that layer alone catches.')
    return EXIT_CLEAN


# ── ablation ───────────────────────────────────────────────────────────────
#
# PER ARM, NOT PER EXIT CODE. Removing a layer and watching the exit code
# change tells you something failed; it does not tell you WHICH check was the
# only thing standing between the board and a wrong field. Each entry below
# disables exactly one layer and re-runs every arm.

_ABLATIONS = (
    ('row-absence',
     'resolve_row reports a missing row instead of returning an empty dict '
     'that renders as idle',
     lambda: _patch('resolve_row', lambda label, rows: ({}, 'fake', ''))),
    ('context-unknown',
     'context_for says UNKNOWN instead of printing a plausible 0%',
     lambda: _patch('context_for',
                    lambda row, dfields, dbatch: ('0%', 'ablated'))),
    ('beacon-lag',
     'chain_tip reports how far the beacon lags the real chain',
     lambda: _patch('chain_tip',
                    lambda token, ddir: 'seq 10; hash abc; beacon published x')),
    ('unlisted-agent',
     'collect names an agent the board does not cover',
     lambda: _patch_board_extra()),
    ('readback',
     'write_verified compares the bytes back off the destination',
     lambda: _patch('write_verified', _unverified_write)),
    ('digest-label-bounds',
     'digest_fields stops a field at the next label instead of running on',
     lambda: _patch('digest_fields', _loose_digest_fields)),
    ('highest-batch',
     'newest_digest picks the highest batch number rather than the newest file',
     lambda: _patch('newest_digest', _mtime_newest_digest)),
    ('latest-ceiling',
     'publish truncates a per-agent file to the line ceiling',
     lambda: _patch_no_ceiling()),
    ('claim-subject',
     'claims_of reads sairn_claim\'s own `subject` field',
     lambda: _patch('claims_of', lambda row: [
         (str(c.get('app') or '?'), str(c.get('task') or ''))
         for c in ((row or {}).get('claims') or []) if isinstance(c, dict)])),
    ('claims-survive-set',
     'sairn_status.payload carries the mirrored claim keys through a status '
     'change instead of rebuilding the row without them',
     lambda: _patch_payload_drops_claims()),
)


def _patch_payload_drops_claims():
    """Restore the pre-fix payload(): a fresh dict, claim keys dropped."""
    old = ST.payload

    def dropping(args, existing=None):
        got = old(args, existing)
        for k in ('claims', 'claims_updated', 'claims_heartbeat'):
            got.pop(k, None)
        return got
    ST.payload = dropping
    return lambda: setattr(ST, 'payload', old)


def _unverified_write(path, text):
    """write_verified with the read-back REMOVED and nothing else.

    It still writes, and still reports a write that threw -- so this ablation
    isolates the read-back alone rather than taking the write with it. Without
    it, the `readback` row would break three arms and tell you nothing about
    which layer each one was really testing.
    """
    try:
        with io.open(path, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
    except Exception as exc:                                     # noqa: BLE001
        return False, 'write failed: %s' % str(exc)[:160]
    return True, 'not checked'


def _patch(name, replacement):
    """Swap a module-level function out; returns the restore thunk."""
    old = globals()[name]
    globals()[name] = replacement
    return lambda: globals().__setitem__(name, old)


def _patch_board_extra():
    old = globals()['collect']

    def no_extra(ddir=None):
        got = old(ddir)
        if got[0] is None:
            return got
        rows, problems, _er, _ed = got
        return rows, problems, [], []
    globals()['collect'] = no_extra
    return lambda: globals().__setitem__('collect', old)


def _patch_no_ceiling():
    old = globals()['LATEST_MAX_LINES']
    globals()['LATEST_MAX_LINES'] = 10 ** 6
    return lambda: globals().__setitem__('LATEST_MAX_LINES', old)


def _loose_digest_fields(path):
    """digest_fields without the next-label boundary -- runs to end of file."""
    out = {'status': '', 'next': '', 'context': ''}
    if not path:
        return out
    try:
        text = io.open(path, encoding='utf-8', errors='replace').read()
    except OSError:
        return out
    for label, key in (('STATUS', 'status'), ('NEXT', 'next'),
                       ('CONTEXT', 'context')):
        m = re.search(r'^%s\s*:?\s*' % label, text, re.M)
        if m:
            out[key] = ' '.join(text[m.end():].split())
        elif key == 'next':
            # The defect this ablation stands for: no NEXT, so borrow STATUS.
            m2 = re.search(r'^UNVERIFIED\s*:?\s*', text, re.M)
            if m2:
                out[key] = ' '.join(text[m2.end():].split())
    return out


def _mtime_newest_digest(token, ddir):
    best, best_path, best_m = None, '', -1.0
    for fn in _listdir(ddir):
        m = DIGEST_RE.match(fn)
        if not m:
            continue
        agent = m.group('agent').lower()
        if agent != token and agent not in DUV.ALIASES.get(token, ()):
            continue
        full = os.path.join(ddir, fn)
        try:
            mt = os.path.getmtime(full)
        except OSError:
            continue
        if mt > best_m:
            best, best_path, best_m = int(m.group('n')), full, mt
    return best, best_path


def ablation():
    print('sairn_board_publish --ablation  (criteria %s)' % CRITERIA_VERSION)
    print('ONE layer removed at a time from clean code; every arm re-run. The')
    print('number that matters is WHICH ARMS go quiet, not the exit code.')
    print('')
    base_pass, base_fail, _ = _run_arms(verbose=False)
    print('  baseline: %d pass / %d fail' % (base_pass, base_fail))
    if base_fail:
        print('  ABLATION NOT RUN -- the baseline is not clean, so any change')
        print('  below could not be attributed to the removed layer.')
        return EXIT_COULD_NOT_RUN
    print('')
    naked = []
    for name, what, patcher in _ABLATIONS:
        restore = patcher()
        try:
            p, f, fails = _run_arms(verbose=False)
        finally:
            restore()
        if f == 0:
            naked.append(name)
            print('  %-22s NOTHING CAUGHT IT -- removing this layer broke no '
                  'arm. It is UNPROVEN.' % name)
            print('    %s' % what)
        else:
            print('  %-22s %d arm(s) fail without it: %s'
                  % (name, f, ', '.join(n for n, _d, _w in fails)))
            print('    %s' % what)
    print('')
    if naked:
        print('  %d LAYER(S) ARE UNPROVEN: %s' % (len(naked), ', '.join(naked)))
        print('  Each one can be deleted today without a single arm noticing, '
              'which means nothing here demonstrates it does anything.')
        return EXIT_FINDING
    print('  Every layer is load-bearing: removing any one of them breaks at '
          'least one arm, and each arm names the real defect it stands for.')
    return EXIT_CLEAN


# ── cli ────────────────────────────────────────────────────────────────────

def main(argv=None):
    ap = argparse.ArgumentParser(
        description='Publish the six-agent SAIRN board to the shared Drive.')
    ap.add_argument('--dry-run', action='store_true',
                    help='render and report sizes; write nothing')
    ap.add_argument('--show', action='store_true',
                    help='print the board to stdout instead of publishing')
    ap.add_argument('--reason', default='manual run',
                    help='what triggered this publish (recorded in the file)')
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--ablation', action='store_true')
    args = ap.parse_args(argv)

    if DUV is None or ST is None:
        print('COULD NOT RUN -- %s' % _IMPORT_WHY)
        print('  This check depends on another tool and FAILS CLOSED when it '
              'is absent rather than skipping (PR 1.11).')
        return EXIT_COULD_NOT_RUN
    if args.selftest:
        return selftest()
    if args.ablation:
        return ablation()
    if args.show:
        got = collect()
        if got[0] is None:
            print('COULD NOT RUN -- %s' % got[1][0])
            return EXIT_COULD_NOT_RUN
        rows, problems, er, ed = got
        sys.stdout.write(render_board(rows, problems, er, ed,
                                      args.reason, drive_dir()))
        return EXIT_FINDING if problems else EXIT_CLEAN
    code, lines = publish(reason=args.reason, dry_run=args.dry_run)
    for ln in lines:
        print(ln)
    return code


if __name__ == '__main__':
    sys.exit(main())
