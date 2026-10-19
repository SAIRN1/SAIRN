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

CRITERIA_VERSION = '2026-10-15.1'
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


# ── THE LABEL SET, AND WHY IT GREW THE WAY IT DID (cc b19, 2026-10-19) ─────
# MICHAEL'S DECISION was "the board's label list grows -- add explicit
# STATUS/DECISION-NEEDED/NEXT". MEASURED FIRST, and read out of this tuple
# rather than remembered: ALL of those were ALREADY here. What was missing,
# against the six live digests on the mount, is `IDENTITY` (hank's first line)
# and `DIGEST` (cc's and fourth's). Both are added.
#
# THE RUN-ON HAD ONE LIVE INSTANCE AND A BLANKET FIX WOULD HAVE BEEN WORSE.
# hank b17's CONTEXT body measured 4,673 characters, because CONTEXT sits at
# offset 1506 and the next RECOGNISED label at 6193, with three of hank's own
# section headings in between (`WHAT LANDED --`, `THE METHODOLOGY ITEM CAUGHT
# ITS OWN AUTHOR...`, `AND THREE SUITES WENT RED...`) -- each a real heading:
# own line, column 0, preceded by a blank line.
#
# BUT THE SAME SHAPE LIVES INSIDE FIELDS THAT ARE SUPPOSED TO CONTAIN IT.
# cody b23's CHANGED carries `ITEM 1 --`, `ITEM 2 --`, `A DEFECT RECORD WAS
# WRITTEN`; its NEXT carries `WHOEVER TAKES THE NEXT SWEEP REPAIR`, `HANK --`,
# `CC --`. All blank-line-preceded, all upper case, and all genuinely part of
# the field a reader wants. Terminating there would cut cody's CHANGED to one
# paragraph and call it the whole field.
#
# SO THE RULE IS SCOPED BY WHAT THE FIELD IS:
#   CONTEXT is a FIGURE field -- a few words -- so a blank-line-preceded
#   heading inside it is always the next section, and it terminates there.
#   STATUS and NEXT are PROSE fields that legitimately carry their author's
#   headings, so they still end only at a known label or at end of file, and
#   when one of them CONTAINS such a heading the fields dict says so. A bound
#   nobody can see is a bound that widens (b18's tolerance note, same shape).
LABELS = ('IDENTITY', 'DIGEST', 'STATUS', 'DECISION-NEEDED', 'CHANGED',
          'EVIDENCE-path', 'UNVERIFIED', 'NEXT', 'CONTEXT', 'SHA256',
          'END-OF-REPORT')

# A heading of the author's own: column 0, at least four characters of upper
# case before any lower case, and preceded by a blank line. The blank-line
# requirement is what separates it from a wrapped sentence that happens to
# begin with an emphasised word -- cody's digest has six of those and not one
# is preceded by a blank line.
OWN_HEADING_RE = re.compile(r'^[A-Z][A-Z0-9 /&\'’,.()-]{3,}$')


def own_headings(body_lines):
    """Indices of the author's own block headings within a field's lines."""
    # THE LENGTH GUARD GOES ON THE HEAD, NOT THE LINE, and the first version
    # of this function put it on the line -- which skipped every one of hank's
    # headings, because his are `WHAT LANDED -- <a paragraph>` on a single
    # line. Measured: CONTEXT stayed at 4,673 characters and the arm that was
    # supposed to catch it reported nothing, which is the fires-on-absence
    # direction this repo keeps paying for.
    out = []
    for i, line in enumerate(body_lines):
        s = line.strip()
        if not s:
            continue
        head = re.split(r'\s--\s|:', s, 1)[0].strip()
        if not (4 <= len(head) <= 60) or not OWN_HEADING_RE.match(head):
            continue
        if i == 0 or not body_lines[i - 1].strip():
            out.append(i)
    return out


def digest_fields(path):
    """{status, next, context, notes} from a digest's own labelled lines.

    Each value is the text after the label up to the next labelled line, so a
    STATUS that wraps is not truncated at the newline. A label that is absent
    yields '' and the caller says UNKNOWN -- it does not borrow another line.
    `notes` names any prose field that carries the author's own headings, which
    is reported rather than silently sliced.
    """
    out = {'status': '', 'next': '', 'context': '', 'notes': []}
    if not path:
        return out
    try:
        with io.open(path, encoding='utf-8', errors='replace') as fh:
            text = fh.read()
    except OSError:
        return out
    # A label starts a line and is followed by ':' or whitespace -- h2 writes
    # `CONTEXT:` and cc writes `CONTEXT `, and both are the same field.
    pat = re.compile(r'^(%s)\s*:?\s*' % '|'.join(LABELS), re.M)
    hits = [(m.group(1), m.start(), m.end()) for m in pat.finditer(text)]
    for i, (name, _s, e) in enumerate(hits):
        end = hits[i + 1][1] if i + 1 < len(hits) else len(text)
        key = {'STATUS': 'status', 'NEXT': 'next',
               'CONTEXT': 'context'}.get(name)
        if not key or out[key]:
            continue
        raw = text[e:end]
        lines = raw.split(chr(10))
        heads = own_headings(lines)
        if key == 'context' and heads:
            # THE FIGURE FIELD STOPS AT THE NEXT SECTION. hank's 4,673
            # characters become the forty that are actually the reading.
            cut = heads[0] if heads[0] > 0 else 1
            was = len(raw)
            raw = chr(10).join(lines[:cut])
            out['notes'].append(
                'CONTEXT ended at the digest\'s own next heading (%r): %d '
                'character(s) kept of the %d that ran to the next known label'
                % (lines[heads[0]].strip()[:60], len(raw), was))
        elif heads:
            out['notes'].append(
                '%s carries %d of the digest\'s own heading(s) (first: %r); '
                'the field is NOT cut there because a prose field legitimately '
                'contains them, but the 900-character display slice may land '
                'inside another section'
                % (name, len(heads), lines[heads[0]].strip()[:60]))
        out[key] = ' '.join(raw.split())
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


# ── THE LAG DETECTOR COULD NOT SEE A FROZEN MIRROR (fixed 2026-10-14, b14) ─
# b12 compared the beacon's `seq` against the newest `chain-tip-seq<N>` file
# BESIDE IT, in the same directory, and called that a lag detector. BOTH
# SOURCES LIVE IN THE SAME MIRROR, so when the whole directory stops being
# refreshed they go stale together and the detector reports no lag at all.
# Two readings of one frozen thing is one reading.
#
# ROUTED BY H2 b36, which diagnosed it in its own words: the chain-tip cell
# was "silently stale by 111 entries/6 days due to a frozen Drive-mount mirror
# the lag-detector cannot see". MEASURED HERE BEFORE CHANGING ANYTHING:
#
#   G:\My Drive\SAIRN-status\hover-chain-h2\   every file dated 2026-10-08
#     TIP-BEACON.md CHECKPOINT  seq 778, published_at 2026-10-08T15:08:48Z
#   SAIRN-digest-h2-b36.txt (refreshed every batch)   chain tip 889
#                                                     -> 111 behind
#   hover-chain-h1\  newest chain-tip-seq file  seq 1185, dated 2026-10-08
#   SAIRN-digest-h1-b36.txt   "Chain tip 1435"        -> 250 behind
#
# SO THE FIX IS A SOURCE THAT MOVES, plus freshness on the mirror itself:
#
#   1. THE DIGEST IS THE INDEPENDENT SOURCE. Each auditor uploads a fresh
#      digest every batch, into the same folder, and states its own chain tip
#      there. It is a different artefact written by a different action, which
#      is what the old second source was not.
#   2. THE MIRROR IS AGE-CHECKED DIRECTLY, by the newest mtime in its own
#      directory, so a frozen mirror is reported as FROZEN with its age rather
#      than inferred from a comparison that cannot see it.
#   3. BOTH NUMBERS ARE PRINTED WHEN THEY DISAGREE and the digest wins as the
#      reported tip, because the beacon is a checkpoint CLAIM and the digest
#      is the agent's own current statement.
#
# MIRROR_STALE_HOURS IS NOT A TUNED NUMBER and the margin is printed rather
# than trusted: auditor batches land several times a day (h1 and h2 both
# published b36 today) and this mirror is six days old, so anything from a day
# to several classifies today's data identically. Erring tight is the safe
# direction -- a mirror reported stale when it is merely quiet costs a line of
# output, where the opposite cost six days of a wrong number.
MIRROR_STALE_HOURS = 48.0

# ── THE MIRROR FROZE ONE FILE AT A TIME (fixed 2026-10-15, b15) ────────────
# b14's detector aged the mirror by its NEWEST file. Measured this morning
# against the real h1 mirror on the mount, not reasoned about:
#
#   hover-chain-h1\  TIP-BEACON.md           2026-10-14 21:50    10.4h
#                    hover-audit-log.jsonl   2026-10-08 09:58   165h
#                    chain-tip-seq1185.tsr   2026-10-08 09:58   165h
#
# and the board printed `mirror last written 10.4h ago (TIP-BEACON.md)`. That
# sentence is TRUE and the thing a reader takes from it is false: the beacon
# is a 1.2KB checkpoint CLAIM, and the two artefacts it is a claim ABOUT are a
# week old. A mirror exists to cross-check, and a cross-check needs every half
# of itself current -- so the age that decides FROZEN is the OLDEST
# load-bearing component, never the newest file in the directory. b14 fixed
# "the whole directory stopped" and left "one file in it kept moving", which
# is the same defect at a finer grain and reads MORE reassuring than silence.
#
# AND THE AGE BASIS IS A POSITIVE ALLOWLIST, which is the other half of the
# fix rather than tidiness. This batch makes the publisher write
# MIRROR-FRESHNESS.md into the mirror on every event, and an age-by-newest
# basis would have made that notice itself the proof the mirror was fresh --
# a detector refreshing its own subject, which is item 8 of the cross-domain
# disciplines one step later. Anything NOT on the allowlist cannot contribute
# freshness in either direction: it is counted and named as UNAGED, so a
# genuinely new auditor artefact surfaces as something to classify instead of
# silently voting the mirror current.
#
# WHAT EACH COMPONENT IS, and why only two of the four are load-bearing:
#   TIP-BEACON.md          the checkpoint claim           LOAD-BEARING
#   hover-audit-log.jsonl  the thing the claim is about   LOAD-BEARING
#   chain-tip-seq*.{msg,tsq,tsr}, chain-tip-timestamp.*
#                          the RFC-3161 countersignature  LOAD-BEARING
#   freetsa-*.pem/.crt     the TSA trust anchors          NOT AGED: they are
#                          long-lived certificates and would read as stale
#                          for ever, which would make every mirror frozen and
#                          the signal worthless.
#   MIRROR-FRESHNESS.md    written by THIS publisher      NEVER AGED
_MIRROR_BEACON = 'tip-beacon.md'
_MIRROR_LOG = 'hover-audit-log.jsonl'
_MIRROR_NOTICE = 'MIRROR-FRESHNESS.md'
_MIRROR_TS_RE = re.compile(r'^chain-tip-(?:seq\d+|timestamp)\.', re.IGNORECASE)
_MIRROR_TRUST_RE = re.compile(r'\.(?:pem|crt|cer|der)$', re.IGNORECASE)


def mirror_component(fn):
    """What role a filename plays in a chain mirror. -> (kind, load_bearing).

    kind is one of 'beacon', 'log', 'timestamp', 'trust-anchor', 'notice',
    'unclassified'. Only the first three carry freshness.
    """
    low = fn.lower()
    if fn == _MIRROR_NOTICE:
        return 'notice', False
    if low == _MIRROR_BEACON:
        return 'beacon', True
    if low == _MIRROR_LOG:
        return 'log', True
    if _MIRROR_TS_RE.match(fn):
        return 'timestamp', True
    if _MIRROR_TRUST_RE.search(fn):
        return 'trust-anchor', False
    return 'unclassified', False


def mirror_files(cdir):
    """(aged, unaged) PER FILE -- the detail table, not the verdict.

    aged is [(hours, name, kind)] oldest-first; unaged is [(name, kind)] for
    everything the allowlist declines to let vote.
    """
    aged, unaged = [], []
    now = time.time()
    for fn in _listdir(cdir):
        kind, load_bearing = mirror_component(fn)
        if not load_bearing:
            unaged.append((fn, kind))
            continue
        try:
            mt = os.path.getmtime(os.path.join(cdir, fn))
        except OSError:
            # NOT dropped. A component whose mtime cannot be read is a
            # could-not-tell, and folding it into "fine" is PR 1.11's shape.
            unaged.append((fn, kind + ' (mtime unreadable)'))
            continue
        aged.append((max(0.0, (now - mt) / 3600.0), fn, kind))
    aged.sort(reverse=True)                      # oldest first
    return aged, unaged


# ── A FAMILY'S AGE IS NOT ITS OLDEST FILE (caught in b15, before pushing) ──
# The first version of this aged the mirror by the oldest load-bearing FILE,
# and run against the real h1 mirror it reported `chain-tip-seq1098.tsr is
# 187h old`. That file is from 2026-10-07 and is SUPPOSED to be: the
# chain-tip-seq set is APPEND-ONLY -- each publish adds a new triple and never
# rewrites the old ones. An oldest-file basis would therefore pin every mirror
# FROZEN for ever, the moment its chain had any history at all, and a verdict
# that is always FROZEN is a verdict nobody reads.
#
# So the age is taken PER FAMILY and then the oldest FAMILY decides:
#   beacon    REWRITTEN every publish  -> its own mtime
#   log       REWRITTEN every publish  -> its own mtime
#   timestamp APPENDED TO              -> its NEWEST member, which is when
#                                         the family last gained anything
# Found by running it against the live mount rather than by reading it, which
# is b14's third lesson arriving one batch later on a different tool.
_MIRROR_APPEND_ONLY = ('timestamp',)


def mirror_components(cdir):
    """(aged, unaged) PER FAMILY -- what decides FROZEN.

    aged is [(hours, representative_file, kind)] oldest-first, one entry per
    load-bearing family. unaged is mirror_files()'s, unchanged.
    """
    per_file, unaged = mirror_files(cdir)
    best = {}
    for hours, fn, kind in per_file:
        if kind in _MIRROR_APPEND_ONLY:
            # the NEWEST member: smallest hours wins
            if kind not in best or hours < best[kind][0]:
                best[kind] = (hours, fn, kind)
        else:
            # rewritten each publish, so a second copy would be a surprise --
            # take the oldest and let it show.
            if kind not in best or hours > best[kind][0]:
                best[kind] = (hours, fn, kind)
    aged = sorted(best.values(), reverse=True)
    return aged, unaged


# ── THE REAL SENTENCES, READ RATHER THAN SPECIFIED ─────────────────────────
# A first version of this carried three tidy format-shaped patterns and
# matched NEITHER auditor, which would have been a parser that reports "the
# agent published no tip" about agents publishing it in every digest -- a
# silent zero dressed as a finding. What they actually write, measured:
#
#   h1 b36  "Chain tip 1435 (9 new entries this batch)"
#   h1 b37  "hover_log.py seq1436-1440"
#   h2 b36  "Chain hover_log.py --verify -> 893 entries, CHAIN INTACT
#            (888->893 this batch)"  and  "TIP-BEACON.md refreshed
#            seq838->seq889"
#
# So: find every number inside a CHAIN-CONTEXT sentence and take the MAXIMUM,
# then QUOTE the sentence it came from. The max is right because a chain only
# grows and a digest naturally names both the old tip and the new one. The
# quote is what makes it checkable -- a number with no sentence behind it is
# the thing this whole cell got wrong for six days.
_CHAIN_CONTEXT = re.compile(r'[^.;\n]*(?:chain|seq)[^.;\n]*', re.IGNORECASE)
# `seq838->seq889` GLUES THE NUMBER TO THE WORD, and a lookbehind excluding
# \w therefore matched neither end of it -- found by arm A22 driving the real
# sentence rather than a specified one. The word is separated from its number
# before scanning instead of widening the lookbehind, which would also admit
# the digits inside identifiers like `sha256`.
_SEQ_GLUE = re.compile(r'\b(seq|entry|entries|#)\s*(\d)', re.IGNORECASE)
# ONE DIGIT IS ALLOWED, deliberately. A chain legitimately has a tip of 5 early
# on, and arm A20 needs exactly that case to make the mirror AHEAD of the
# digest. The guards against noise are that a number must sit inside a
# chain-context sentence, that the MAXIMUM wins so a stray small number cannot
# beat a real tip, and that the sentence is QUOTED so a reader can check.
_NUM = re.compile(r'(?<![\w.])(\d{1,6})(?![\w.])')
# Numbers that are not chain sequences however they appear beside one. Years
# and batch numbers are the two that really occur in these sentences.
_NOT_A_SEQ = re.compile(r'^(?:19|20)\d{2}$')


def digest_chain_tip(token, ddir):
    """(seq, batch, why) -- the tip the agent states in its OWN newest digest.

    THE INDEPENDENT SOURCE. A digest is written by a different action from the
    mirror publish, so the two cannot freeze together -- which is the entire
    defect this replaces. Returns (None, batch, why) when the digest exists
    and says nothing about a chain, because "the agent published no tip" and
    "there is no digest" are different facts.
    """
    batch, path = newest_digest(token, ddir)
    if not path:
        return None, batch, 'no digest for %s on the Drive' % token
    try:
        with io.open(path, encoding='utf-8', errors='replace') as fh:
            text = fh.read()
    except OSError as exc:
        return None, batch, 'digest b%s unreadable: %s' % (batch,
                                                           str(exc)[:60])
    best, best_sentence = None, ''
    for sm in _CHAIN_CONTEXT.finditer(text):
        sentence = sm.group(0).strip()
        scan = _SEQ_GLUE.sub(lambda m: m.group(1) + ' ' + m.group(2), sentence)
        for nm in _NUM.finditer(scan):
            raw = nm.group(1)
            if _NOT_A_SEQ.match(raw):
                continue
            n = int(raw)
            if best is None or n > best:
                best, best_sentence = n, sentence
    if best is None:
        return None, batch, ('digest b%s mentions no chain or seq number at '
                             'all' % batch)
    return best, batch, ('from b%s: %s'
                         % (batch, ' '.join(best_sentence.split())[:150]))


def mirror_age_hours(cdir):
    """(hours, name) for the OLDEST LOAD-BEARING component, or (None, '').

    THE MIRROR IS AGED BY MTIME and not by the beacon's `published_at`. A
    published_at is a string the publisher wrote; an mtime is what the
    filesystem observed. When a mirror is abandoned they agree, and when
    somebody hand-edits the beacon they do not -- and the filesystem is the one
    that cannot be talked into a date.

    AND IT IS THE OLDEST, NOT THE NEWEST. See the component comment above: the
    real h1 mirror had a 10-hour beacon over a 165-hour log, and the newest-file
    basis printed the 10. The oldest load-bearing component is the age at which
    this mirror can still cross-check anything.
    """
    aged, _unaged = mirror_components(cdir)
    if not aged:
        return None, ''
    hours, name, _kind = aged[0]
    return hours, name


def digest_published_hours(token, ddir):
    """(hours, basename) since the agent's own newest digest was written, or
    (None, '').

    THE COMPARISON SUBJECT FOR "a mirror older than its own digest". The
    digest and the mirror are produced by two different actions, so a digest
    newer than the mirror means the auditor closed a batch WITHOUT
    republishing the chain -- a freeze that starts at a known moment and that
    an absolute 48h ceiling cannot see for two more days.
    """
    _batch, path = newest_digest(token, ddir)
    if not path:
        return None, ''
    try:
        mt = os.path.getmtime(path)
    except OSError:
        return None, ''
    return max(0.0, (time.time() - mt) / 3600.0), os.path.basename(path)


def chain_tip(token, ddir):
    """The audit-chain tip for an auditor. -> text.

    Reads THREE things and says which it is reporting: the agent's own newest
    digest (independent, refreshed every batch), the published beacon
    checkpoint, and the age of the mirror directory itself. See the comment
    above for the frozen-mirror defect this shape exists to stop.
    """
    cdir = os.path.join(ddir, 'hover-chain-%s' % token)
    d_seq, d_batch, d_why = digest_chain_tip(token, ddir)

    if not os.path.isdir(cdir):
        # NO MIRROR IS NOT NO ANSWER. The digest alone is a real reading and
        # is reported as such, labelled, rather than discarded because the
        # mirror that used to be preferred is absent.
        if d_seq is not None:
            return ('seq %d, from %s\'s OWN digest b%s -- NO MIRROR at %s, so '
                    'there is no beacon to cross-check it against'
                    % (d_seq, token, d_batch, os.path.basename(cdir)))
        return ('UNKNOWN -- no %s directory on the Drive, and %s'
                % (os.path.basename(cdir), d_why))

    age_h, age_file = mirror_age_hours(cdir)
    beacon = os.path.join(cdir, 'TIP-BEACON.md')
    seqs = [int(m.group('n')) for m in
            (SEQ_RE.match(fn) for fn in _listdir(cdir)) if m]
    newest_seq = max(seqs) if seqs else None

    cp, b_seq = None, None
    if os.path.isfile(beacon):
        try:
            with io.open(beacon, encoding='utf-8', errors='replace') as fh:
                text = fh.read()
            m = re.search(r'^CHECKPOINT:\s*(\{.*\})\s*$', text, re.M)
            if m:
                cp = json.loads(m.group(1))
                b_seq = cp.get('seq')
        except Exception:                                        # noqa: BLE001
            cp = None

    # The mirror's own best claim is the higher of its two internal readings;
    # they are NOT independent of each other and are no longer treated as if
    # they were.
    mirror_seq = max([s for s in (b_seq, newest_seq)
                      if isinstance(s, int)] or [None])

    frozen = age_h is not None and age_h > MIRROR_STALE_HOURS

    bits = []
    if d_seq is not None:
        bits.append('seq %d (%s\'s own digest b%s -- THE REPORTED TIP; %s)'
                    % (d_seq, token, d_batch, d_why))
    elif mirror_seq is not None and not frozen:
        bits.append('seq %s (the MIRROR, and the digest gives no tip: %s)'
                    % (mirror_seq, d_why))
    elif mirror_seq is not None:
        # ── NEITHER SOURCE IS USABLE, AND THAT IS A THIRD STATE ───────────
        # A first version of this printed the frozen mirror's seq and then
        # said "which is why the tip above comes from the digest" -- a false
        # sentence under a number from the other source. If the digest gives
        # no tip AND the mirror is frozen, there is nothing current to report
        # and saying so is the only honest output.
        return ('UNKNOWN -- NEITHER SOURCE IS CURRENT. The mirror at %s is '
                'FROZEN (newest file %s, %.0fh old, past the %.0fh line) and '
                'its last claim was seq %s; and %s. A frozen mirror\'s number '
                'is not reported as a tip, because that is exactly how this '
                'cell was wrong by 111 entries for six days.'
                % (os.path.basename(cdir), age_file, age_h,
                   MIRROR_STALE_HOURS, mirror_seq, d_why))
    else:
        return ('UNKNOWN -- neither source gives a tip. %s; and the mirror at '
                '%s carries no CHECKPOINT and no chain-tip-seq file.'
                % (d_why, os.path.basename(cdir)))

    if cp:
        bits.append('beacon claims seq %s, hash %s, published %s'
                    % (b_seq, str(cp.get('hash') or '')[:12],
                       cp.get('published_at') or 'UNKNOWN'))
    elif os.path.isfile(beacon):
        bits.append('TIP-BEACON.md is present but carries no parseable '
                    'CHECKPOINT line')
    else:
        bits.append('no TIP-BEACON.md in the mirror')

    # ── THE THREE THINGS THE OLD VERSION COULD NOT SAY ────────────────────
    if frozen:
        bits.append('MIRROR IS FROZEN: its OLDEST load-bearing component (%s) '
                    'is %.0fh old, past the %.0fh line -- the margin is '
                    'printed rather than trusted. A mirror this old cannot '
                    'cross-check anything, so nothing above rests on it'
                    % (age_file, age_h, MIRROR_STALE_HOURS))
    elif age_h is not None:
        bits.append('mirror oldest component %.1fh old (%s)'
                    % (age_h, age_file))

    # ── A MIRROR CAN FREEZE ONE FILE AT A TIME ────────────────────────────
    # The newest-file basis is still computed, and only so that the GAP
    # between it and the oldest can be reported. A beacon refreshed over a
    # week-old log is the shape that made this cell read `mirror last written
    # 10.4h ago` about a mirror whose chain had not moved since 2026-10-08.
    aged, unaged = mirror_components(cdir)
    note = partial_refresh_note(aged)
    if note:
        bits.append(note)

    # ── OLDER THAN ITS OWN DIGEST ─────────────────────────────────────────
    # An absolute ceiling cannot see a freeze until the ceiling passes. The
    # agent's own digest timestamps the moment it closed a batch, so a
    # component older than that digest is a batch closed WITHOUT republishing
    # the chain -- visible the same hour instead of two days later.
    d_age, d_name = digest_published_hours(token, ddir)
    if d_age is not None and aged:
        behind = [(h, n) for h, n, _k in aged if h > d_age + 1.0]
        if behind:
            bits.append('MIRROR OLDER THAN ITS OWN DIGEST: %s was published '
                        '%.1fh ago and %d of %d load-bearing family(s) '
                        'predate it, the worst by %.0fh (%s, %.0fh old) -- '
                        'the auditor closed a batch without republishing the '
                        'chain, and this fires on the hour it happens rather '
                        'than when the %.0fh ceiling catches up'
                        % (d_name, d_age, len(behind), len(aged),
                           behind[0][0] - d_age, behind[0][1], behind[0][0],
                           MIRROR_STALE_HOURS))
    if unaged:
        bits.append('%d file(s) in the mirror are UNAGED by design and vote '
                    'on nothing: %s'
                    % (len(unaged),
                       ', '.join('%s [%s]' % (n, k) for n, k in unaged[:6])))

    # ── THE WITHIN-MIRROR COMPARISON IS KEPT, AND DEMOTED ─────────────────
    # b12 called this the lag detector and it was the whole detector. It is a
    # real signal -- a beacon behind its own directory is a stale checkpoint
    # claim -- but both halves live in one mirror, so it can only ever catch a
    # publisher that wrote the files and forgot the beacon. It can never catch
    # the mirror freezing, which is what actually happened. Reported as what it
    # is: an INTERNAL inconsistency, not a tip comparison.
    if (isinstance(b_seq, int) and newest_seq is not None
            and newest_seq > b_seq):
        bits.append('INTERNALLY INCONSISTENT MIRROR: the beacon is %d behind '
                    'the newest chain-tip file beside it (seq %d) -- both are '
                    'in the same directory, so this catches a forgotten beacon '
                    'and never a frozen mirror'
                    % (newest_seq - b_seq, newest_seq))

    if d_seq is not None and mirror_seq is not None and d_seq > mirror_seq:
        bits.append('THE MIRROR IS %d ENTRIES BEHIND the digest (%s vs %d) -- '
                    'two readings of one frozen directory is one reading, '
                    'which is the defect this cell carried for six days'
                    % (d_seq - mirror_seq, mirror_seq, d_seq))
    elif d_seq is not None and mirror_seq is not None and mirror_seq > d_seq:
        bits.append('the MIRROR is AHEAD of the digest (%d vs %d), so the '
                    'digest is the stale one here -- reported rather than '
                    'resolved, because which is right is the auditor\'s call'
                    % (mirror_seq, d_seq))

    # ── BOTH NUMBERS, EVERY RUN, INCLUDING WHEN THEY AGREE ────────────────
    # b14 printed the two sources' numbers only on a DISAGREEMENT, so the
    # agreeing case published one number and a reader could not tell whether
    # the second source had been consulted at all or had simply been dropped.
    # On 2026-10-15 h1's two sources agreed at 1451 having been 1444 vs 1440
    # the night before, and nothing in the cell distinguished "cross-checked
    # and agreed" from "cross-check not performed". An absent disagreement is
    # not evidence of agreement unless something says both were read.
    note = seq_cross_check(mirror_seq, d_seq)
    if note:
        bits.append(note)

    return '; '.join(bits)


def partial_refresh_note(aged):
    """The 'one file kept moving' sentence, or ''. -> text.

    Its own function so --ablation can remove exactly this. The newest-file
    basis is computed HERE and only to report the gap, never to decide FROZEN.
    """
    if len(aged) > 1 and aged[0][0] - aged[-1][0] > MIRROR_STALE_HOURS:
        return ('PARTIALLY REFRESHED MIRROR: %s is %.0fh old while %s is only '
                '%.1fh old -- one component kept moving and the others did '
                'not, which reads more current than silence and is why the '
                'age above is the OLDEST and not the newest'
                % (aged[0][1], aged[0][0], aged[-1][1], aged[-1][0]))
    return ''


def seq_cross_check(mirror_seq, d_seq):
    """The 'both numbers were read' sentence, or '' when a disagreement has
    already said it. -> text.

    Its own function so --ablation can remove exactly this and nothing else.
    """
    if d_seq is not None and mirror_seq is not None and d_seq == mirror_seq:
        return ('MIRROR SEQ %d / DIGEST SEQ %d -- the two sources AGREE, and '
                'that is printed rather than left as the absence of a '
                'disagreement' % (mirror_seq, d_seq))
    if mirror_seq is None:
        return ('MIRROR SEQ none / DIGEST SEQ %s -- the mirror carries no '
                'CHECKPOINT and no chain-tip-seq file, so there was nothing '
                'to cross-check against'
                % ('none' if d_seq is None else str(d_seq)))
    return ''


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


# ── A FIGURE CELL MUST CONTAIN A FIGURE (cc b18 item 1, 2026-10-19) ────────
# The CONTEXT cell rendered up to 120 characters of whatever followed the
# digest's CONTEXT label, and for two of six agents that was a paragraph:
# MEASURED before the fix, `digest_fields()` returns a context body of
# 4,673 characters for hank b17 and 10,717 for cody b22, because the parse runs
# from the label to the next RECOGNISED label and those digests continue with
# unlabelled section headings of their own. The board then sliced that to 120
# and the table to 40, so hank's cell read
#
#     46% WHAT LANDED -- fourth's b26, four ro
#
# which is a real figure welded to a paragraph and cut mid-word. Truncating
# harder is a smaller weld, not a fix, and requiring the other agents to shape
# their digests differently is not available to a tool that READS their files.
#
# So the figure is PARSED OUT and the figure is what prints. When no figure is
# parseable the cell says UNKNOWN with the reason -- never a plausible 0%,
# which is the fabricated-value shape Guardian 0b exists for.
#
# WHAT THIS CANNOT DO, stated rather than discovered: extracting a figure
# cannot tell a STALE figure from a current one. The `source` half of the
# return is still the only thing that distinguishes "live status row, set
# <when>" from "digest bN", and it is printed beside every cell.
PCT_RE = re.compile(r'(\d{1,3}(?:\.\d+)?)\s*%')


def context_figure(body):
    """-> (figure, '') or ('', why_not). The FIRST percentage in a context body.

    FIRST, not largest: a context line's own reading comes before any figure it
    goes on to discuss (hank's 46% is followed by a paragraph containing other
    numbers), and `max` would pick whichever number in the prose happened to be
    biggest. A percentage over 100 is refused rather than printed, because a
    context reading is a share of a window and 4,673% is a parse accident.
    """
    for m in PCT_RE.finditer(body or ''):
        try:
            val = float(m.group(1))
        except ValueError:                                       # noqa: PERF203
            continue
        if 0.0 <= val <= 100.0:
            return m.group(0).replace(' ', ''), ''
    if not (body or '').strip():
        return '', 'the digest carries no CONTEXT line'
    return '', ('the digest\'s CONTEXT line carries no percentage in its first '
                '%d character(s)' % min(len(body), 400))


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
    body = dfields.get('context') or ''
    if body:
        fig, why = context_figure(body)
        if fig:
            # The body's LENGTH is reported when it was a paragraph, because a
            # reader who sees a clean 46% here deserves to know the source line
            # was 4,673 characters and this is the figure cut out of it.
            extra = ('' if len(body) <= 160 else
                     ', parsed out of a %d-character CONTEXT line'
                     % len(body))
            return fig, 'digest b%s%s' % (dbatch, extra)
        return ('UNKNOWN -- %s' % why), 'digest b%s' % dbatch
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
         # THE FIELD THE RACE GUARD READS. A clone running a lower revision
         # refuses to overwrite a board written by a higher one -- see
         # overwrite_refusal(). It is published rather than kept internal so
         # the guard reads the BOARD rather than trusting its own copy.
         '- **Written by publisher revision %s** -- a clone on a lower '
         'revision refuses to overwrite this file rather than reverting it'
         % PUBLISHER_REVISION,
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
            # A GLANCE COLUMN IS A FIGURE OR THE WORD UNKNOWN. Slicing an
            # UNKNOWN sentence to 40 characters gave `UNKNOWN -- the digest's
            # CONTEXT line car`, which is the same cut-mid-word shape the
            # figure fix just removed, one column over. The REASON belongs in
            # the per-agent section below, where it is printed whole.
            ('UNKNOWN' if r['context'].startswith('UNKNOWN')
             else r['context'][:40]), len(r['claims']),
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
        return False, 'write failed: %s' % str(exc)[:160], None
    finally:
        if tmp and os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
    back, why = DUV.read_bytes(path)
    if back is None:
        return (False,
                'written and then NOT READABLE: %s' % why[:120], None)
    if DUV.sha256_of(back) != DUV.sha256_of(data):
        return (False,
                ('read-back sha256 MISMATCH -- sent %d bytes sha %s, read %d '
                 'bytes sha %s. Reported NOT PUBLISHED rather than '
                 'published-with-a-caveat.'
                 % (len(data), DUV.sha256_of(data)[:12], len(back),
                    DUV.sha256_of(back)[:12])), None)
    # THE OBSERVED BYTES ARE RETURNED, not the sent ones. The manifest is
    # built from these, so it describes WHAT IS ON THE MOUNT rather than what
    # this process intended to put there. See build_manifest().
    #
    # THREE VALUES ON EVERY PATH, including the failures above. A function
    # returning two on one branch and three on another is the next
    # unpack-error, and this one is called from a loop that cannot see which
    # branch it took.
    return (True,
            'verified %d bytes sha %s' % (len(back), DUV.sha256_of(back)[:12]),
            back)


# ── CLOSING THE DRIVE-SIDE COULD-NOT-TELL AS FAR AS THE API ALLOWS ─────────
# b12 published this board and then read it back through the Drive connector,
# and the reported fileSize disagreed with the mount three times: 14600 vs
# 14514, then 2404 vs 2976, then 2952 vs 2976. b12 recorded that as a
# could-not-tell and did not resolve it.
#
# RESOLVED 2026-10-14 (cc b13), by waiting and re-reading rather than by
# reasoning:
#
#   mount  : 15586 bytes, sha256 deb328e9f16c2663...
#   Drive  : fileSize 15586, id 19GSUTWQLddPwZiLEUNfssAjrMxK4vVE1,
#            modifiedTime 2026-10-15T00:56:35Z
#
# IT CONVERGES. Every earlier mismatch was a metadata read taken SECONDS after
# a write, while the newest revision was still propagating -- the connector was
# reporting the PREVIOUS revision's size, not a different file. So the mismatch
# was a lag and never a corruption, and the honest statement is bounded: a
# size disagreement on a just-republished file is not evidence of a bad
# upload, and a size AGREEMENT on a settled file is real evidence.
#
# WHAT THE API CANNOT DO, so this is not oversold: read_file_content does not
# support text/markdown, so no chat turn can hash the Drive-side bytes. The
# ONLY field available is fileSize. A manifest makes that one field worth
# something: it publishes the sha256 AND the exact byte count of what is on
# the mount, so a later turn can compare Drive's fileSize against a published
# number instead of against a memory.
#
# A SIZE MATCH IS WEAKER THAN A HASH MATCH AND THE MANIFEST SAYS SO IN ITS OWN
# TEXT. A same-length corruption passes it. That is a third state, not a pass.
MANIFEST_NAME = 'SAIRN-board-MANIFEST.txt'


def build_manifest(observed, reason):
    """The manifest text, from the bytes READ BACK off the mount.

    `observed` is [(name, bytes_actually_on_the_mount)]. Built from the
    read-back and never from the rendered text: a manifest describing what the
    process MEANT to write would agree with itself after a truncated write,
    which is the one failure it exists to make visible.
    """
    L = ['SAIRN board manifest -- what is ON THE MOUNT, by sha256 and exact '
         'byte count',
         '',
         'Written by tools/sairn_board_publish.py (OWNER cc) on: %s' % reason,
         'Published at: %s (local)' % time.strftime('%Y-%m-%dT%H:%M:%S'),
         '',
         'WHY THIS FILE EXISTS. The Drive connector cannot read the CONTENT of',
         'a text/markdown file -- read_file_content does not support that mime',
         'type -- so no chat turn can hash the Drive-side bytes. The only field',
         'the API exposes is fileSize. These numbers make that one field worth',
         'something: compare Drive\'s reported fileSize for each name below',
         'against the byte count here.',
         '',
         'A SIZE MATCH IS WEAKER THAN A HASH MATCH, and that is stated rather',
         'than glossed: a same-length corruption passes a size comparison. It',
         'is a third state and not a pass.',
         '',
         'AND A SIZE DISAGREEMENT ON A JUST-REPUBLISHED FILE IS NOT A BAD',
         'UPLOAD. Measured 2026-10-14: the connector reported 14600 while the',
         'mount held 14514, and minutes later both read 15586 for the same',
         'file id. The connector reports the PREVIOUS revision while the newest',
         'is still propagating. Let it settle, then compare.',
         '',
         '%-64s %12s  %s' % ('name', 'bytes', 'sha256'),
         '%-64s %12s  %s' % ('-' * 64, '-' * 12, '-' * 64)]
    for name, data in observed:
        L.append('%-64s %12d  %s' % (name, len(data), DUV.sha256_of(data)))
    return NL.join(L) + NL


# ── THE MIRROR IS KEPT FRESH BY THE PUBLISHER, NOT BY MEMORY (b15) ─────────
# Michael's decision 2026-10-15: the frozen hover-chain-h2 mirror is REFRESHED
# rather than retired, and kept fresh by the publisher itself.
#
# WHAT THIS DOES AND DOES NOT DO, said plainly because the difference is the
# whole boundary. It writes ONE new publisher-owned file, MIRROR-FRESHNESS.md,
# into each mirror on every board event. It does NOT write TIP-BEACON.md, it
# does not write a chain-tip-seq file, it does not touch hover-audit-log.jsonl
# and it does not invent a seq. A build agent forging an entry into a
# tamper-evident chain would destroy the only thing that chain exists to
# prove, and "refreshed" cannot be allowed to mean that.
#
# SO THE REFRESH IS OF THE MIRROR AS A PUBLISHED ARTEFACT: b14's open item 12
# said the real cost of the freeze is that "while it sits there it is a
# tamper-evidence artefact a reader takes as current". A reader who opens the
# folder now finds a file, newer than everything else in it, that says in
# plain text how old each component is and what the auditor's own digest
# claims instead. That is the half a build agent can honestly do, and it
# happens on every event so nobody has to remember.
#
# ITS OWN NAME IS ON THE UNAGED ALLOWLIST (mirror_component) so it can never
# become the evidence that the mirror it describes is fresh. Arm A25 drives
# exactly that: write the notice into a frozen mirror and the mirror must
# still read FROZEN.
MIRROR_NOTICE_NAME = _MIRROR_NOTICE


def render_mirror_notice(token, ddir, reason):
    """The publisher-owned freshness statement for one chain mirror. -> text.

    Returns '' when there is no mirror directory: a notice invented beside a
    directory that does not exist would be the publisher creating the thing it
    reports on.
    """
    cdir = os.path.join(ddir, 'hover-chain-%s' % token)
    if not os.path.isdir(cdir):
        return ''
    aged, unaged = mirror_components(cdir)
    per_file, _u = mirror_files(cdir)
    age_h, age_file = mirror_age_hours(cdir)
    d_age, d_name = digest_published_hours(token, ddir)
    L = ['# MIRROR FRESHNESS -- hover-chain-%s' % token,
         '',
         'WRITTEN BY `tools/sairn_board_publish.py` (a BUILD agent tool), not '
         'by %s.' % token,
         'It describes this directory and asserts nothing about the chain. '
         'The beacon,',
         'the log and the timestamp files in here are %s\'s and are never '
         'written by' % token,
         'this tool -- so a fresh timestamp on THIS file is not evidence of '
         'anything',
         'about them, and this filename is excluded from every freshness '
         'basis the',
         'board computes.',
         '',
         'observed_at : %s (local)'
         % time.strftime('%Y-%m-%dT%H:%M:%S'),
         'observed_by : sairn_board_publish.py, event: %s' % reason,
         '']
    if age_h is None:
        L.append('NO LOAD-BEARING COMPONENT FOUND. This directory holds no '
                 'TIP-BEACON.md, no')
        L.append('hover-audit-log.jsonl and no chain-tip-* file, so there is '
                 'nothing here to')
        L.append('age and nothing to cross-check a digest against.')
    else:
        verdict = ('FROZEN -- past the %.0fh line' % MIRROR_STALE_HOURS
                   if age_h > MIRROR_STALE_HOURS
                   else 'within the %.0fh line' % MIRROR_STALE_HOURS)
        L.append('VERDICT: oldest load-bearing component is %.1fh old (%s) '
                 '-- %s' % (age_h, age_file, verdict))
        L.append('')
        L.append('FAMILY ages, OLDEST FIRST -- the oldest family decides. The '
                 'chain-tip-* set is')
        L.append('APPEND-ONLY, so its age is its NEWEST member; the beacon '
                 'and the log are')
        L.append('rewritten every publish, so each is aged by its own mtime.')
        for h, n, k in aged:
            L.append('  %7.1fh  %-12s via %s' % (h, k, n))
        L.append('')
        L.append('every load-bearing file, for reference (old members of an '
                 'append-only set are')
        L.append('EXPECTED to be old and are not a finding):')
        for h, n, k in per_file:
            L.append('  %7.1fh  %-28s [%s]' % (h, n, k))
    if unaged:
        L.append('')
        L.append('UNAGED BY DESIGN -- these vote on nothing:')
        for n, k in unaged:
            L.append('  %-28s [%s]' % (n, k))
    L.append('')
    if d_age is not None:
        L.append('%s\'s own newest digest (%s) was published %.1fh ago.'
                 % (token, d_name, d_age))
        stale = [(h, n) for h, n, _k in aged if h > d_age + 1.0]
        if stale:
            L.append('%d of %d FAMILY(s) PREDATE that digest -- a batch was '
                     'closed without' % (len(stale), len(aged)))
            L.append('republishing the chain. Worst: %s, %.0fh old.'
                     % (stale[0][1], stale[0][0]))
        else:
            L.append('No component predates it.')
    else:
        L.append('No digest for %s on the mount, so there is nothing to '
                 'compare these ages against.' % token)
    L.append('')
    L.append('To make this directory genuinely current, %s runs its own '
             'publisher:' % token)
    L.append('  python .claude/skills/sairn-hover-auditor/tools/'
             'hover_tip_beacon.py --publish')
    L.append('and re-uploads hover-audit-log.jsonl and the chain-tip-* '
             'files beside it.')
    L.append('')
    return NL.join(L) + NL


# ── THE PUBLISHER RACE (cc b19 item 2, from b18's own NEXT note) ───────────
# MEASURED IN b18: cc's clone published a corrected board at 08:34; FOURTH'S
# CLONE REPUBLISHED AT 08:55 with its own pre-fix copy of this file, and the
# broken cells came back with no error anywhere. It resolved itself when other
# clones pulled, which is luck rather than a mechanism.
#
# AND THE DATA WAS NOT STALE -- THE CODE WAS. Every clone renders from the same
# registry outside git, so fourth's rows were as fresh as cc's: a
# last-write-wins check on row timestamps would have let that publish straight
# through. What differed was the publisher each clone was running. So the guard
# compares TWO things, and the first is the one a timestamp check would miss.
#
# REFUSE, NOT MERGE. Merging two renderings of six agents' state produces a
# board describing no moment that ever existed.
#
# AND REFUSING MUST NOT BREAK THE CALLER: publishing is a side effect of a
# status or claim write, so the write still succeeds and the board is reported
# NOT PUBLISHED with the command that fixes it.
#
# THE LIMIT, STATED HERE: a clone running a publisher older than this revision
# neither writes the field nor reads it, so it cannot be stopped by this. The
# guard protects every clone from this revision forward, and the push is what
# distributes it.
PUBLISHER_REVISION = '2026-10-19.1'
REV_RE = re.compile(r'publisher revision\s+([0-9]{4}-[0-9]{2}-[0-9]{2}\.[0-9]+)')
ROW_WRITTEN_RE = re.compile(r'row written ([0-9]{4}-[0-9]{2}-[0-9]{2}T'
                            r'[0-9]{2}:[0-9]{2}:[0-9]{2})')


def _rev_tuple(text):
    """'2026-10-19.10' -> (2026, 10, 19, 10). Compared as numbers, because
    '2026-10-19.10' < '2026-10-19.9' as strings and that would invert the
    guard exactly once a revision reached double digits."""
    try:
        date, serial = str(text).rsplit('.', 1)
        y, m, d = date.split('-')
        return (int(y), int(m), int(d), int(serial))
    except Exception:                                            # noqa: BLE001
        return None


def overwrite_refusal(board_path, incoming):
    """-> (refuse, why). Would writing `incoming` revert a newer board?

    Pure apart from reading the existing file. Returns (False, '') whenever it
    cannot tell -- an unreadable or absent board is not evidence of a race,
    and refusing to publish because the mount is empty would be a new way to
    have no board at all.
    """
    try:
        existing = io.open(board_path, encoding='utf-8', errors='replace').read()
    except OSError:
        return False, ''
    mine = _rev_tuple(PUBLISHER_REVISION)
    m = REV_RE.search(existing)
    theirs = _rev_tuple(m.group(1)) if m else None
    if mine and theirs and theirs > mine:
        return True, ('the board on the mount was written by publisher '
                      'revision %s and this clone is running %s. A lower '
                      'revision replacing a higher one is the b18 race: a '
                      'stale clone silently reverting a fix.'
                      % (m.group(1), PUBLISHER_REVISION))
    # ROW RECENCY, per agent. The board prints each row's own `row written`
    # stamp; if the published board shows a row NEWER than the one this
    # process just read, this clone's registry read is behind.
    old_rows = ROW_WRITTEN_RE.findall(existing)
    new_rows = ROW_WRITTEN_RE.findall(incoming)
    if old_rows and new_rows:
        newest_old, newest_new = max(old_rows), max(new_rows)
        if newest_old > newest_new:
            return True, ('the board on the mount renders a status row '
                          'written %s and the newest row this clone can see '
                          'is %s -- the registry read behind it is stale, so '
                          'publishing would walk the board backwards.'
                          % (newest_old, newest_new))
    return False, ''


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
    # The mirror freshness notices ride the SAME write-and-read-back path as
    # the board, so a notice that did not land is a FAIL line rather than an
    # assumption. Mirrors that do not exist contribute nothing.
    for _lbl, _tok in (('H1', 'h1'), ('H2', 'h2')):
        notice = render_mirror_notice(_tok, ddir, reason)
        if notice:
            files.append(('hover-chain-%s/%s' % (_tok, MIRROR_NOTICE_NAME),
                          notice))
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
    # ── THE RACE GUARD, BEFORE A SINGLE BYTE IS WRITTEN (cc b19 item 2) ────
    refuse, why = overwrite_refusal(os.path.join(ddir, BOARD_NAME), board)
    if refuse:
        return EXIT_FINDING, [
            'BOARD NOT PUBLISHED -- this clone would have REVERTED a newer '
            'board.', '  %s' % why,
            '  Your status or claim write SUCCEEDED; only the Drive board was '
            'left alone.',
            '  Fix: git pull --rebase origin main, then re-run any status '
            'command to republish.']
    bad = []
    observed = []
    for name, text in files:
        ok, why, data = write_verified(os.path.join(ddir, name), text)
        out.append('  %-26s %s  %s' % (name, 'OK  ' if ok else 'FAIL', why))
        if not ok:
            bad.append(name)
        else:
            observed.append((name, data))
    if bad:
        out.insert(0, 'BOARD NOT PUBLISHED -- %d of %d file(s) failed: %s'
                      % (len(bad), len(files), ', '.join(bad)))
        return EXIT_FINDING, out
    # ── THE MANIFEST, FROM THE READ-BACK BYTES ─────────────────────────────
    # Written LAST and from `observed`, which is what came back off the mount
    # rather than what was rendered. It is itself written through
    # write_verified, so the file carrying the hashes is hashed too -- a
    # manifest nobody checked is a second unverified claim about the first.
    mok, mwhy, mdata = write_verified(os.path.join(ddir, MANIFEST_NAME),
                                      build_manifest(observed, reason))
    out.append('  %-26s %s  %s' % (MANIFEST_NAME, 'OK  ' if mok else 'FAIL',
                                   mwhy))
    if not mok:
        out.insert(0, 'BOARD PUBLISHED BUT ITS MANIFEST DID NOT -- the %d '
                      'file(s) are on the mount and verified, and the sizes a '
                      'Drive-side read would be compared against are NOT '
                      'published. Reported rather than called clean.'
                      % len(files))
        return EXIT_FINDING, out
    out.insert(0, 'board published and read back: %d file(s) + manifest in %s'
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


@arm('A3-stale-beacon', 'a TIP-BEACON checkpoint behind its own directory is '
                        'printed as the current tip')
def _a3(sdir, ddir):
    # ANCHOR UPDATED 2026-10-14 (b14). The message this arm matched said
    # "BEACON IS 89 BEHIND the newest chain-tip file", and that comparison was
    # DEMOTED rather than deleted: both of its halves live in one mirror, so it
    # can catch a publisher who forgot the beacon and can never catch the
    # mirror freezing -- which is what actually happened for six days. The
    # signal is kept and relabelled as an INTERNAL inconsistency, and this arm
    # now asserts that wording, so the arm and the sentence cannot drift apart
    # without one of them failing.
    cd = os.path.join(ddir, 'hover-chain-h2')
    _write(os.path.join(cd, 'chain-tip-seq99.msg'), 'x')
    txt = _board_for(sdir, ddir)[0]
    return ('INTERNALLY INCONSISTENT MIRROR' in txt
            and '89 behind' in txt), txt


@arm('A17-frozen-mirror', 'a mirror whose beacon and chain-tip files AGREE '
                          'while the whole directory is six days old is '
                          'reported as current -- the defect H2 b36 routed, '
                          'where two readings of one frozen thing read as a '
                          'clean cross-check')
def _a17(sdir, ddir):
    # The digest carries a tip so the run reaches the reporting path. With no
    # digest tip AND a frozen mirror there is nothing current at all, which is
    # A19's case and a different sentence.
    _write(os.path.join(ddir, 'SAIRN-digest-h2-b7.txt'),
           'DIGEST h2 b7\nSTATUS: Chain tip 893 this batch.\n'
           'NEXT: n.\nCONTEXT 40% used\n')
    cd = os.path.join(ddir, 'hover-chain-h2')
    old = time.time() - 154 * 3600
    for fn in _listdir(cd):
        os.utime(os.path.join(cd, fn), (old, old))
    txt = _board_for(sdir, ddir)[0]
    return ('MIRROR IS FROZEN' in txt and '154h old' in txt
            and '48h line' in txt), txt


@arm('A18-digest-is-the-source', 'the tip comes from the mirror even when the '
                                 'agent states a newer one in its own digest')
def _a18(sdir, ddir):
    _write(os.path.join(ddir, 'SAIRN-digest-h2-b7.txt'),
           'DIGEST h2 b7\nSTATUS: Chain hover_log.py --verify -> 893 '
           'entries, CHAIN INTACT (888->893 this batch).\n'
           'NEXT: n.\nCONTEXT 40% used\n')
    txt = _board_for(sdir, ddir)[0]
    return ('seq 893' in txt and 'own digest b7' in txt
            and 'THE REPORTED TIP' in txt
            and 'MIRROR IS 883 ENTRIES BEHIND' in txt), txt


@arm('A19-frozen-and-silent', 'a frozen mirror\'s number is reported as a tip '
                              'when the digest gives none -- there is nothing '
                              'current and the only honest output is UNKNOWN')
def _a19(sdir, ddir):
    cd = os.path.join(ddir, 'hover-chain-h2')
    old = time.time() - 200 * 3600
    for fn in _listdir(cd):
        os.utime(os.path.join(cd, fn), (old, old))
    txt = _board_for(sdir, ddir)[0]
    return ('NEITHER SOURCE IS CURRENT' in txt
            and 'is not reported as a tip' in txt), txt


@arm('A20-mirror-ahead', 'a mirror AHEAD of the digest is silently resolved '
                         'one way instead of reported')
def _a20(sdir, ddir):
    _write(os.path.join(ddir, 'SAIRN-digest-h2-b7.txt'),
           'DIGEST h2 b7\nSTATUS: chain tip 5 after a rollback.\n'
           'NEXT: n.\nCONTEXT 40% used\n')
    txt = _board_for(sdir, ddir)[0]
    return ('MIRROR is AHEAD of the digest' in txt
            and 'the auditor\'s call' in txt), txt


@arm('A21-tip-quotes-its-sentence', 'a chain tip is printed as a bare number '
                                    'with no sentence behind it, which is how '
                                    'this cell was wrong for six days')
def _a21(sdir, ddir):
    _write(os.path.join(ddir, 'SAIRN-digest-h1-b7.txt'),
           'DIGEST h1 b7\nSTATUS: Chain tip 1435 (9 new entries this batch).\n'
           'NEXT: n.\nCONTEXT 40% used\n')
    txt = _board_for(sdir, ddir)[0]
    return ('seq 1435' in txt
            and 'Chain tip 1435 (9 new entries this batch)' in txt), txt


@arm('A22-real-sentence-shapes', 'the parser matches NEITHER auditor\'s real '
                                 'wording, so it reports "no tip published" '
                                 'about agents who publish one every batch')
def _a22(sdir, ddir):
    # THE MEASURED TEXT, not a specified format. A first version of this
    # parser carried three tidy patterns and matched none of these.
    cases = [
        ('Chain tip 1435 (9 new entries this batch), verified genesis-to-tip',
         1435),
        ('Chain hover_log.py --verify -> 893 entries, CHAIN INTACT '
         '(888->893 this batch)', 893),
        ('hover-audit-log.jsonl +5 entries (seq889-893: b35 closeout)', 893),
        ('TIP-BEACON.md refreshed seq838->seq889', 889),
        ('chain entries #1436-#1440', 1440),
    ]
    bad = []
    for sentence, want in cases:
        d = tempfile.mkdtemp(prefix='tipsent-', dir=ddir)
        _write(os.path.join(d, 'SAIRN-digest-h2-b1.txt'),
               'DIGEST h2 b1\nSTATUS: %s\n' % sentence)
        got = digest_chain_tip('h2', d)[0]
        if got != want:
            bad.append((sentence[:48], want, got))
    return (not bad), ('%d of %d real sentences mis-parsed: %s'
                       % (len(bad), len(cases), bad))


def _age_files(cdir, names, hours):
    old = time.time() - hours * 3600
    for fn in names:
        p = os.path.join(cdir, fn)
        if os.path.isfile(p):
            os.utime(p, (old, old))


@arm('A23-partial-refresh', 'a mirror whose BEACON kept moving over a '
                            'week-old log and week-old timestamp files reads '
                            'as current, because the age came off the NEWEST '
                            'file -- the real h1 state on 2026-10-15, where '
                            'the board printed "mirror last written 10.4h '
                            'ago" about a chain frozen since 2026-10-08')
def _a23(sdir, ddir):
    _write(os.path.join(ddir, 'SAIRN-digest-h1-b7.txt'),
           'DIGEST h1 b7\nSTATUS: Chain tip 1451 (11 new entries this '
           'batch), verified.\nNEXT: n.\nCONTEXT 40% used\n')
    cd = os.path.join(ddir, 'hover-chain-h1')
    _write(os.path.join(cd, 'hover-audit-log.jsonl'), '{"seq": 1451}\n')
    # THE MEASURED SHAPE: beacon 10.4h, log and timestamps 165h.
    _age_files(cd, ['hover-audit-log.jsonl', 'chain-tip-seq10.msg'], 165.0)
    _age_files(cd, ['TIP-BEACON.md'], 10.4)
    txt = _board_for(sdir, ddir)[0]
    # The FROZEN line must name the 165h component, not the 10.4h beacon --
    # that substitution is the entire defect and asserting only the words
    # would pass with the newest-file basis still in place.
    return ('PARTIALLY REFRESHED MIRROR' in txt
            and 'MIRROR IS FROZEN' in txt
            and 'OLDEST load-bearing component (hover-audit-log.jsonl) is '
                '165h old' in txt
            and 'while TIP-BEACON.md is only 10.4h old' in txt), txt


@arm('A28-append-only-history', 'a FULLY REFRESHED mirror reads FROZEN for '
                                'ever because the oldest chain-tip-seq triple '
                                'in it is from last week -- that set is '
                                'APPEND-ONLY and its old members are supposed '
                                'to be old. Caught in b15 by running the fix '
                                'against the live h1 mount, which reported '
                                '`chain-tip-seq1098.tsr is 187h old` about a '
                                'mirror that had just been republished')
def _a28(sdir, ddir):
    _write(os.path.join(ddir, 'SAIRN-digest-h1-b7.txt'),
           'DIGEST h1 b7\nSTATUS: Chain tip 1459 (8 new entries this batch), '
           'verified.\nNEXT: n.\nCONTEXT 40% used\n')
    cd = os.path.join(ddir, 'hover-chain-h1')
    _write(os.path.join(cd, 'hover-audit-log.jsonl'), '{"seq": 1459}\n')
    # HISTORY: two old triples that will never be rewritten again.
    for seq, hrs in ((1098, 200.0), (1159, 190.0)):
        for ext in ('msg', 'tsq', 'tsr'):
            fn = 'chain-tip-seq%d.%s' % (seq, ext)
            _write(os.path.join(cd, fn), 'x')
            _age_files(cd, [fn], hrs)
    # AND A REPUBLISH JUST NOW: new triple, fresh beacon, fresh log.
    for ext in ('msg', 'tsq', 'tsr'):
        _write(os.path.join(cd, 'chain-tip-seq1459.%s' % ext), 'x')
    txt = _board_for(sdir, ddir)[0]
    h1cell = txt.split('## H1')[-1].split('## H2')[0] if '## H1' in txt else txt
    return ('MIRROR IS FROZEN' not in h1cell
            and 'PARTIALLY REFRESHED MIRROR' not in h1cell
            and 'MIRROR SEQ 1459 / DIGEST SEQ 1459' in h1cell), h1cell


@arm('A24-older-than-its-digest', 'a mirror that stopped moving while the '
                                  'auditor kept closing batches is silent '
                                  'until the 48h ceiling catches up -- the '
                                  'digest timestamps the moment the freeze '
                                  'started and an absolute ceiling cannot')
def _a24(sdir, ddir):
    _write(os.path.join(ddir, 'SAIRN-digest-h2-b7.txt'),
           'DIGEST h2 b7\nSTATUS: Chain tip 901 this batch.\n'
           'NEXT: n.\nCONTEXT 40% used\n')
    cd = os.path.join(ddir, 'hover-chain-h2')
    # BOTH WELL INSIDE THE 48h CEILING, on purpose: the ceiling must not be
    # what fires here, or the arm would pass with this layer deleted.
    _age_files(cd, _listdir(cd), 10.0)
    _age_files(ddir, ['SAIRN-digest-h2-b7.txt'], 1.0)
    txt = _board_for(sdir, ddir)[0]
    return ('MIRROR OLDER THAN ITS OWN DIGEST' in txt
            and 'MIRROR IS FROZEN' not in txt), txt


@arm('A25-notice-cannot-refresh', 'the publisher\'s OWN freshness notice '
                                  'becomes the evidence that the mirror it '
                                  'describes is fresh -- a detector '
                                  'refreshing its own subject')
def _a25(sdir, ddir):
    # The digest carries a tip so the run reaches the reporting path rather
    # than A19's "neither source is current" early return.
    _write(os.path.join(ddir, 'SAIRN-digest-h2-b7.txt'),
           'DIGEST h2 b7\nSTATUS: Chain tip 901 this batch.\n'
           'NEXT: n.\nCONTEXT 40% used\n')
    cd = os.path.join(ddir, 'hover-chain-h2')
    _age_files(cd, _listdir(cd), 200.0)
    _write(os.path.join(cd, MIRROR_NOTICE_NAME), 'written just now\n')
    txt = _board_for(sdir, ddir)[0]
    frozen = 'FROZEN' in txt
    unaged = ('%s [notice]' % MIRROR_NOTICE_NAME) in txt
    # AND IT MUST NOT BE NAMED AS THE FRESH HALF of a partial refresh: that
    # is what fires if the allowlist stops excluding it while the oldest
    # basis still holds, and it isolates the allowlist from the basis.
    not_the_fresh_half = MIRROR_NOTICE_NAME not in txt.split(
        'PARTIALLY REFRESHED MIRROR')[-1][:200] or 'PARTIALLY' not in txt
    return (frozen and unaged and not_the_fresh_half), txt


@arm('A26-both-seqs-when-they-agree', 'the two sources are printed only on a '
                                      'DISAGREEMENT, so an agreeing cell '
                                      'cannot be told apart from one where '
                                      'the cross-check never ran -- h1 agreed '
                                      'at 1451 on 2026-10-15 having been 1444 '
                                      'vs 1440 the night before')
def _a26(sdir, ddir):
    _write(os.path.join(ddir, 'SAIRN-digest-h1-b7.txt'),
           'DIGEST h1 b7\nSTATUS: Chain tip 10 this batch.\n'
           'NEXT: n.\nCONTEXT 40% used\n')
    txt = _board_for(sdir, ddir)[0]
    return ('MIRROR SEQ 10 / DIGEST SEQ 10' in txt
            and 'the two sources AGREE' in txt), txt


@arm('A27-notice-published', 'the mirror sits on the Drive with nothing in it '
                             'saying how old it is, so a reader who opens the '
                             'folder takes a frozen tamper-evidence artefact '
                             'as current -- b14 open item 12')
def _a27(sdir, ddir):
    old = ST.STATUS_DIR
    ST.STATUS_DIR = sdir
    try:
        code, lines = publish(reason='A27', ddir=ddir)
    finally:
        ST.STATUS_DIR = old
    p = os.path.join(ddir, 'hover-chain-h2', MIRROR_NOTICE_NAME)
    if not os.path.isfile(p):
        return False, 'no notice written (code %s): %s' % (code, lines[:2])
    body = io.open(p, encoding='utf-8').read()
    return ('WRITTEN BY `tools/sairn_board_publish.py`' in body
            and 'FAMILY ages, OLDEST FIRST' in body
            and 'APPEND-ONLY, so its age is its NEWEST member' in body
            and 'hover_tip_beacon.py --publish' in body), body


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
        ok, why, _data = write_verified(path, 'the real content\n')
    finally:
        DUV.read_bytes = real
    return (not ok and 'MISMATCH' in why), why


@arm('A6-unreadable-destination', 'a destination that cannot be written is '
                                  'reported as a successful publish')
def _a6(sdir, ddir):
    gone = os.path.join(ddir, 'no-such-dir', 'x.md')
    ok, why, _data = write_verified(gone, 'content\n')
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


@arm('A15-manifest-published', 'the sizes a Drive-side read would be compared '
                               'against are never published, so fileSize is a '
                               'number with nothing to check it against')
def _a15(sdir, ddir):
    old = ST.STATUS_DIR
    ST.STATUS_DIR = sdir
    try:
        code, _lines = publish(reason='selftest', ddir=ddir)
    finally:
        ST.STATUS_DIR = old
    p = os.path.join(ddir, MANIFEST_NAME)
    if not os.path.isfile(p):
        return False, 'no manifest written (publish exit %d)' % code
    body = io.open(p, encoding='utf-8').read()
    # Every published name must appear with a byte count that matches the file
    # actually on the mount. A manifest that disagrees with the mount makes a
    # Drive-side size comparison worse than useless -- it would report a
    # mismatch that is the manifest's fault.
    for name in [BOARD_NAME] + [LATEST_NAME % a for a in BOARD_ORDER]:
        real = os.path.getsize(os.path.join(ddir, name))
        if ('%-64s %12d' % (name, real)) not in body:
            return False, ('manifest does not carry %s at its real size %d'
                           % (name, real))
    return ('A SIZE MATCH IS WEAKER THAN A HASH MATCH' in body
            and 'same-length corruption' in body), 'manifest %d bytes' % len(body)


@arm('A16-manifest-from-readback', 'the manifest records what the process '
                                   'MEANT to write, so it agrees with itself '
                                   'after a truncated write')
def _a16(sdir, ddir):
    # THE DEFECT THIS STANDS FOR, and the reason the manifest is built from
    # `observed` rather than from the rendered text. A mount that silently
    # truncates would otherwise produce a manifest whose numbers describe the
    # untruncated original -- so the one Drive-side check available would
    # compare a real short file against a published long number and be read as
    # a propagation lag, which is exactly the thing b12 could not rule out.
    real = DUV.read_bytes
    target = os.path.join(ddir, BOARD_NAME)

    def truncating(p):
        data, why = real(p)
        if data is not None and os.path.abspath(p) == os.path.abspath(target):
            return data[:len(data) // 2], why
        return data, why
    DUV.read_bytes = truncating
    old = ST.STATUS_DIR
    ST.STATUS_DIR = sdir
    try:
        code, lines = publish(reason='selftest', ddir=ddir)
    finally:
        DUV.read_bytes = real
        ST.STATUS_DIR = old
    # The read-back check must catch the short read FIRST -- so the board is
    # reported NOT PUBLISHED and no manifest describing it is written at all.
    return (code == EXIT_FINDING
            and 'BOARD NOT PUBLISHED' in NL.join(lines)
            and not os.path.isfile(os.path.join(ddir, MANIFEST_NAME))), \
        'exit %d' % code


@arm('A29-context-prose', 'a CONTEXT cell renders the PARAGRAPH that followed '
                          'the label instead of the figure in it')
def _a17(sdir, ddir):
    # THE REAL SHAPE, taken from hank b17 and cody b22: the digest's CONTEXT
    # label is followed by a figure and then by unlabelled prose, so
    # digest_fields() returns thousands of characters and the cell printed the
    # first 120 of them. Measured on the live mount before the fix: 4,673 and
    # 10,717 characters.
    d = json.load(io.open(os.path.join(sdir, 'cc.json'), encoding='utf-8'))
    d.pop('context_pct')                   # force the digest fallback
    _write(os.path.join(sdir, 'cc.json'), json.dumps(d))
    prose = ('46% WHAT LANDED -- fourth\'s b26, four routed fixes, each '
             'failing-first with an ablation. H3 (critical, money): the '
             'paid-period freeze was ERASABLE BY THE ROLE THAT RUNS PAYROLL '
             'through a 200, because the handler trusted a client flag. '
             'Numbers that must not be mistaken for the reading: 2026, 144, '
             '99, 1000000.')
    _write(os.path.join(ddir, 'SAIRN-digest-cc-b7.txt'),
           'DIGEST cc b7\nSTATUS: s.\nNEXT: n.\nCONTEXT %s\n' % prose)
    txt = _board_for(sdir, ddir)[0]
    # The figure prints, the prose does not, and the cell says where the
    # figure was cut from.
    ok = ('**CONTEXT:** 46%' in txt
          and 'WHAT LANDED' not in txt
          and 'ERASABLE' not in txt
          and 'parsed out of a' in txt)
    return ok, txt


@arm('A30-context-no-figure', 'a CONTEXT line with no percentage renders as '
                              'prose, or worse as a plausible 0%')
def _a18(sdir, ddir):
    d = json.load(io.open(os.path.join(sdir, 'cc.json'), encoding='utf-8'))
    d.pop('context_pct')
    _write(os.path.join(sdir, 'cc.json'), json.dumps(d))
    _write(os.path.join(ddir, 'SAIRN-digest-cc-b7.txt'),
           'DIGEST cc b7\nSTATUS: s.\nNEXT: n.\nCONTEXT not measured this '
           'batch -- no tool available here exposes the per-turn usage sum\n')
    txt = _board_for(sdir, ddir)[0]
    # H1's real wording, which has no figure in it at all. UNKNOWN with the
    # reason; never 0%, and never the sentence itself in a figure column.
    ok = ('UNKNOWN -- the digest\'s CONTEXT line carries no percentage' in txt
          and 'CONTEXT:** 0%' not in txt
          and 'no tool available here' not in txt)
    return ok, txt


@arm('A31-context-runs-on', 'a CONTEXT field runs past its own section into '
                            'the next one, so the board stores thousands of '
                            'characters of the wrong section')
def _a31(sdir, ddir):
    # HANK b17's REAL SHAPE: CONTEXT, a blank line, then his own all-caps
    # heading with a paragraph welded to it on ONE line -- which is why the
    # first version of own_headings() (length guard on the LINE) caught
    # nothing and reported a clean parse over a 4,673-character field.
    d = json.load(io.open(os.path.join(sdir, 'cc.json'), encoding='utf-8'))
    d.pop('context_pct')
    _write(os.path.join(sdir, 'cc.json'), json.dumps(d))
    body = (
        'DIGEST cc b7', '', 'STATUS: s.', '', 'CONTEXT: 46%', '',
        'WHAT LANDED -- four routed fixes, each failing-first with an '
        'ablation, and a paragraph long enough that a line-length guard '
        'would skip it entirely.', '',
        'AND THREE SUITES WENT RED -- all three fixed and named here.', '',
        'NEXT: n.')
    _write(os.path.join(ddir, 'SAIRN-digest-cc-b7.txt'), NL.join(body) + NL)
    f = digest_fields(os.path.join(ddir, 'SAIRN-digest-cc-b7.txt'))
    txt = _board_for(sdir, ddir)[0]
    ok = (f['context'].strip() == '46%'
          and 'WHAT LANDED' not in f['context']
          and any('ended at the digest' in n for n in f['notes'])
          and '**CONTEXT:** 46%' in txt)
    return ok, '%r / notes=%r' % (f['context'][:60], f['notes'][:1])


@arm('A32-prose-field-not-cut', 'a PROSE field is cut at the author\'s own '
                                'heading, losing content the board is meant '
                                'to show')
def _a32(sdir, ddir):
    # THE CONTROL FOR A31, and the reason the rule is scoped by field. cody
    # b23's CHANGED carries ITEM 1/ITEM 2 and its NEXT carries HANK --/CC --;
    # terminating there would cut the field to one paragraph and call it whole.
    body = ('DIGEST cc b7', '', 'STATUS: the first paragraph.', '',
            'ITEM 1 -- a heading of my own inside STATUS, which belongs to it.',
            '', 'NEXT: the first next paragraph.', '',
            'HANK -- a heading of my own inside NEXT, which belongs to it.',
            '', 'CONTEXT: 40%')
    _write(os.path.join(ddir, 'SAIRN-digest-cc-b7.txt'), NL.join(body) + NL)
    f = digest_fields(os.path.join(ddir, 'SAIRN-digest-cc-b7.txt'))
    ok = ('ITEM 1' in f['status']            # kept, not cut
          and 'HANK' in f['next']
          and any('carries' in n and 'NOT cut' in n for n in f['notes']))
    return ok, 'status=%r next=%r' % (f['status'][:50], f['next'][:50])


@arm('A33-stale-clone-reverts', 'a clone running an OLDER publisher overwrites '
                                'a newer board and silently reverts a fix')
def _a33(sdir, ddir):
    # b18's race, driven. The board on the mount was written by a HIGHER
    # revision than this process is running; publishing must refuse.
    p = os.path.join(ddir, BOARD_NAME)
    _write(p, NL.join([
        '# SAIRN board -- all six agents, one file', '',
        '- **Published at:** 2026-10-19T09:00:00 (local)',
        '- **Written by publisher revision 2099-01-01.1** -- a clone on a '
        'lower revision refuses to overwrite this file', '']) + NL)
    refuse, why = overwrite_refusal(p, 'whatever this clone would write')
    before = io.open(p, encoding='utf-8').read()
    old = ST.STATUS_DIR
    ST.STATUS_DIR = sdir
    try:
        code, lines = publish(reason='selftest', ddir=ddir)
    finally:
        ST.STATUS_DIR = old
    after = io.open(p, encoding='utf-8').read()
    ok = (refuse and 'revision 2099-01-01.1' in why
          and code == EXIT_FINDING
          and 'would have REVERTED a newer board' in NL.join(lines)
          and 'git pull' in NL.join(lines)
          and after == before)             # and it really did not write
    return ok, 'refuse=%s exit=%s untouched=%s' % (refuse, code,
                                                   after == before)


@arm('A34-rev-compare-is-numeric', 'revision 10 is treated as OLDER than '
                                   'revision 9 because the compare is textual')
def _a34(sdir, ddir):
    # The one that inverts the guard exactly once a serial reaches two digits.
    hi, lo = _rev_tuple('2026-10-19.10'), _rev_tuple('2026-10-19.9')
    ok = (hi is not None and lo is not None and hi > lo
          and '2026-10-19.10' < '2026-10-19.9')   # the textual trap, asserted
    return ok, 'hi=%r lo=%r' % (hi, lo)


@arm('A35-fresh-board-publishes', 'the race guard refuses a publish it should '
                                  'have allowed, so no board is ever written')
def _a35(sdir, ddir):
    # THE CONTROL. A guard that refuses everything is worse than the race.
    p = os.path.join(ddir, BOARD_NAME)
    _write(p, NL.join([
        '# SAIRN board', '',
        '- **Published at:** 2026-10-19T09:00:00 (local)',
        '- **Written by publisher revision 2000-01-01.1** -- older than mine',
        '- **state:** working (liveness LIVE, row written '
        '2000-01-01T00:00:00, 0.0h old)', '']) + NL)
    refuse_old, _w = overwrite_refusal(p, 'rendered by this clone')
    os.unlink(p)
    refuse_absent, _w2 = overwrite_refusal(p, 'rendered by this clone')
    old = ST.STATUS_DIR
    ST.STATUS_DIR = sdir
    try:
        code, _lines = publish(reason='selftest', ddir=ddir)
    finally:
        ST.STATUS_DIR = old
    ok = (not refuse_old and not refuse_absent and code == EXIT_CLEAN
          and os.path.isfile(p))
    return ok, ('older=%s absent=%s exit=%s'
                % (refuse_old, refuse_absent, code))


@arm('A36-stale-rows-walk-back', 'a clone whose registry read is BEHIND the '
                                 'published board overwrites it anyway')
def _a36(sdir, ddir):
    # The second half of the guard: same publisher revision, older data.
    p = os.path.join(ddir, BOARD_NAME)
    _write(p, NL.join([
        '# SAIRN board', '',
        '- **Written by publisher revision %s** -- same as mine'
        % PUBLISHER_REVISION,
        '- **state:** working (liveness LIVE, row written '
        '2099-01-01T00:00:00, 0.0h old)', '']) + NL)
    incoming = ('- **state:** working (liveness LIVE, row written '
                '2026-10-19T09:00:00, 0.0h old)')
    refuse, why = overwrite_refusal(p, incoming)
    ok = refuse and 'walk the board backwards' in why
    return ok, why[:140]


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
    ('mirror-freshness',
     'chain_tip ages the mirror DIRECTORY by its own newest mtime, so a frozen '
     'mirror is reported as frozen instead of inferred from a comparison whose '
     'two halves are both inside it',
     lambda: _patch('mirror_age_hours', lambda cdir: (None, ''))),
    # ── b15: the four layers that split "the directory froze" from "one
    # file in it kept moving", plus the publisher-owned refresh ───────────
    ('mirror-oldest-component',
     'mirror_age_hours ages the mirror by its OLDEST load-bearing component. '
     'The b14 behaviour -- restored exactly here -- was the NEWEST file, which '
     'printed 10.4h about a chain frozen since 2026-10-08 because the beacon '
     'alone had been rewritten',
     lambda: _patch('mirror_age_hours', _newest_file_age)),
    ('mirror-allowlist',
     'mirror_component lets only the beacon, the log and the chain-tip files '
     'carry freshness, so the publisher\'s own notice cannot become the '
     'evidence that the mirror it describes is current',
     lambda: _patch('mirror_component', lambda fn: ('everything', True))),
    ('append-only-family',
     'mirror_components ages the APPEND-ONLY chain-tip-* set by its NEWEST '
     'member, so a mirror with history does not read FROZEN for ever. Removing '
     'this restores the oldest-FILE basis, which called a just-republished h1 '
     'mirror 187h old',
     lambda: _patch('_MIRROR_APPEND_ONLY', ())),
    ('partial-refresh-note',
     'chain_tip says WHICH component kept moving and which did not, instead '
     'of reporting one age and leaving the gap invisible',
     lambda: _patch('partial_refresh_note', lambda aged: '')),
    ('digest-publish-age',
     'the mirror\'s components are compared against the agent\'s OWN newest '
     'digest, so a freeze is visible the hour it starts rather than when the '
     '48h ceiling catches up',
     lambda: _patch('digest_published_hours', lambda token, ddir: (None, ''))),
    ('seq-cross-check',
     'both source numbers are printed when they AGREE, so an agreeing cell '
     'can be told apart from one where the cross-check never ran',
     lambda: _patch('seq_cross_check', lambda mirror_seq, d_seq: '')),
    ('mirror-notice',
     'the publisher writes MIRROR-FRESHNESS.md into each mirror on every '
     'event, so a reader who opens a frozen chain directory is told it is '
     'frozen without running anything',
     lambda: _patch('render_mirror_notice',
                    lambda token, ddir, reason: '')),
    ('digest-tip-source',
     'chain_tip reads the agent\'s own newest digest as an INDEPENDENT source '
     '-- a different artefact written by a different action, which is what the '
     'within-mirror second source never was',
     lambda: _patch('digest_chain_tip',
                    lambda token, ddir: (None, None, 'ablated'))),
    ('seq-glue',
     'the tip parser separates `seq838` into word and number before scanning, '
     'which is the shape H2 actually writes',
     lambda: _patch('_SEQ_GLUE', re.compile(r'(?!x)x'))),
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
    ('manifest',
     'publish writes a manifest of the sha256 and exact byte count of what is '
     'ON THE MOUNT, so the one field a Drive-side read exposes for markdown '
     '-- fileSize -- has a published number to be compared against',
     lambda: _patch_no_manifest()),
)


def _patch_no_manifest():
    """Remove the manifest and nothing else."""
    old = globals()['build_manifest']

    def nothing(observed, reason):
        raise RuntimeError('manifest ablated')
    globals()['build_manifest'] = nothing
    return lambda: globals().__setitem__('build_manifest', old)


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
        return False, 'write failed: %s' % str(exc)[:160], None
    # THE SAME 3-TUPLE SHAPE AS write_verified, and the third value is what
    # the ablation is about: this stub hands back WHAT IT MEANT TO WRITE
    # instead of what it read off the mount, so a manifest built from it
    # agrees with itself after a truncated write. That is the arm.
    return True, 'not checked', text.encode('utf-8')


def _newest_file_age(cdir):
    """mirror_age_hours as b14 wrote it: the NEWEST file in the directory,
    whatever it is. Restored verbatim rather than paraphrased, so the ablation
    measures the real prior behaviour and not a convenient stand-in."""
    best, name = None, ''
    for fn in _listdir(cdir):
        try:
            mt = os.path.getmtime(os.path.join(cdir, fn))
        except OSError:
            continue
        if best is None or mt > best:
            best, name = mt, fn
    if best is None:
        return None, ''
    return max(0.0, (time.time() - best) / 3600.0), name


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
