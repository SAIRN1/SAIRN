"""Who is doing what, RIGHT NOW, across every clone -- without a push/pull.

    python tools/sairn_status.py                 # the registry, joined
    python tools/sairn_status.py --json
    python tools/sairn_status.py set --state working --task "..."
    python tools/sairn_status.py set --state blocked --task "..." \\
                                     --blocked-on "Michael: run the migration"
    python tools/sairn_status.py set --state idle
    python tools/sairn_status.py --self-check

Exit 0 clean, 1 a finding, 2 COULD NOT TELL -- never folded into either of the
other two (PR 1.11). REPORT ONLY: it reads the registry and this session's own
section, and the ONLY thing it ever writes is that one section.

── THE GAP THIS FILLS WAS NAMED BY THE TOOL IT SITS BESIDE ──────────────────
`tools/session_lock_check.py`'s own header says it:

    Detects same-clone concurrent sessions ONLY. Does NOT detect two
    different clones independently converging on the same external task --
    that is a harder, TASK-REGISTRY-SHAPED problem and out of scope.

This is that task registry. The lock answers "is somebody else already in THIS
directory"; this answers "what is every agent on this machine actually doing".

`tools/dispatch_state.py` already joins `docs/SAIRN-OPEN-WORK-INDEX.md` against
`.claude/claims/*.json` and answers it well -- but BOTH of its inputs are in
git, so its answer is only as fresh as the last fetch. A claim that has not
been pushed is invisible to every other clone, which the claim tool itself
warns about. This registry is the live half: it lives outside every clone, on
the filesystem, and a write is visible to the next reader immediately.

── ONE FILE PER AGENT, NOT ONE FILE WITH SECTIONS, AND THAT IS THE WHOLE
── SAFETY ARGUMENT RATHER THAN A STORAGE DETAIL ─────────────────────────────
The scope said "one structured status file ... each agent writes only its own
section ... NO CROSS-AGENT WRITE CONTENTION BY CONSTRUCTION". The last four
words are the requirement, and a single file cannot meet them.

Updating one section of a shared file is a READ-MODIFY-WRITE. Two agents whose
reads interleave both write a whole file built from a snapshot that no longer
includes the other's change, and the later writer silently erases the earlier
one. Nothing is corrupt, nothing errors, and one agent's status simply is not
there -- which is the same silent-loss shape this platform polices everywhere
else. Locking would narrow the window; it would not remove it, and it would add
a lock that can be held by a dead process.

So the registry is a DIRECTORY, one file per session, and it is presented to
every reader as one registry. An agent's write touches a path no other agent
ever opens, so there is no window to narrow: the two writes cannot interact at
the filesystem level at all. `tests/run_sairn_status_probe.py` drives real
concurrent processes at it and asserts every write survives.

This is the same shape `.claude/claims/` and `~/SAIRN-SESSION-LOCKS/` already
use, for the same reason, and it is why those have never lost an entry.

── WRITES ARE ATOMIC, SO A READER NEVER SEES HALF A FILE ────────────────────
Write to a uniquely-named temp file in the same directory, then `os.replace()`,
which is atomic on the same filesystem on both Windows and POSIX. A reader
either sees the whole previous file or the whole new one. Copied deliberately
from `session_lock_check.write_lock()` rather than re-derived.

── LIVENESS IS IMPORTED, NEVER REIMPLEMENTED ────────────────────────────────
"Is this agent still running" is answered by `session_lock_check.owner_state()`,
imported. That function carries the recycled-pid defence -- a pid alone is not
identity, because a dead session's pid can be reissued to something unrelated
and read as alive, which three open-source projects have shipped. Its header
says so and it is the single source of truth for that judgement here. A second
copy would be a second opinion on the one thing this must not be wrong about.

── WHAT IT CANNOT DO, said plainly rather than discovered later ─────────────
It cannot tell whether two agents' task strings describe the SAME WORK -- that
is the judgement `dispatch_state.py` refuses to make and this refuses too; it
puts the rows side by side and names the overlap candidates by shared words,
for a human to read. It cannot see an agent that never writes a status. And it
is machine-local: `~/SAIRN-SESSION-LOCKS` is not shared between machines, which
is the same limit the lock files already have.
"""
import argparse
import glob
import io
import json
import os
import sys
import time
import uuid

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

# Overridable for probes ONLY, exactly as session_lock_check.LOCK_DIR is, and
# for the same reason: a control must never be able to touch the real registry.
# Nothing in production sets it.
STATUS_DIR = os.environ.get(
    'SAIRN_STATUS_DIR',
    os.path.join(os.path.expanduser('~'), 'SAIRN-SESSION-LOCKS', 'status'))

STATES = ('working', 'blocked', 'review', 'idle', 'handoff')

EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN = 0, 1, 2

# How long a status may go untouched before it is reported as STALE when
# liveness cannot be determined. Matches session_lock_check.STALE_SECONDS,
# which Michael confirmed at 2 hours on 2026-08-24 -- one number, not two.
STALE_SECONDS = 2 * 60 * 60


def _lockmod():
    """session_lock_check, or None if it will not import.

    NOT A SILENT FALLBACK. Every caller reports UNKNOWN liveness with the
    reason, and UNKNOWN falls back to the age test rather than to "alive" --
    the direction that cannot make a dead agent look busy or a live one look
    free.
    """
    try:
        import session_lock_check
        return session_lock_check
    except Exception:                                            # noqa: BLE001
        return None


def clone_name():
    """This clone's short name, from the directory, never from a hardcoded list.

    `Documents\\SAIRN-hank` -> `hank`. CLAUDE.md named four clones for weeks
    after a fifth existed, so nothing here counts or enumerates them.
    """
    base = os.path.basename(REPO)
    return base[len('SAIRN-'):] if base.startswith('SAIRN-') else base


def path_for(name):
    return os.path.join(STATUS_DIR, name + '.json')


# Windows does not let a rename land on a path another process has open, so the
# replace and the read both need a short retry. Measured by the probe, not
# assumed -- see write_status() and read_one().
_RETRIES = 6
_BACKOFF = 0.02


# ── THE SIX-SECOND WINDOW, AND WHY CLAIMS LIVE HERE TOO (2026-09-22) ───────
# MEASURED, from the claim records themselves:
#
#   cody  criticality-tiers  claimed 22:12:27Z  FILES: ['docs/CRITICALITY-TIERS.md']
#   hank  tier-batch         claimed 22:12:33Z  FILES: ['docs/CRITICALITY-TIERS.md']
#
# Six seconds apart, both DECLARING THE SAME FILE, and both proceeded. Seven
# rows of docs/CRITICALITY-TIERS.md were then re-tiered twice, independently,
# to the same verdict -- reassuring about the verdicts, pure waste as work.
#
# THE MATCHER WAS NOT AT FAULT AND THAT IS THE WHOLE POINT. sairn_claim.py
# decides on the declared file set and would have refused instantly. It could
# not see cody's claim because a claim is published by COMMITTING AND PUSHING
# it, and hank's check read a fetch that predated cody's push landing. The
# window is a git round-trip wide and no amount of matcher precision closes it.
#
# THIS REGISTRY IS ALREADY OUTSIDE GIT, already written locally, already read
# with no fetch. So a session's ACTIVE CLAIMS are published here at claim time
# as well -- the same fact, on the fast path, visible to every other clone the
# moment the file is replaced. The git copy stays authoritative and unchanged;
# this is an EARLY WARNING, not a second source of truth.
#
# OWNERSHIP-PER-KEY IS PRESERVED EXACTLY. A session writes only its own row,
# which is the property that makes this registry safe to write without
# locking, and `claims` is just another key inside that row.
def publish_claims(name, claims):
    """Write `claims` onto this session's OWN row. Returns True on success.

    A LIBRARY CALL RATHER THAN A SUBCOMMAND, deliberately: the caller is
    sairn_claim.py, the payload contains task prose with backticks and pipes
    in it, and this platform has lost text to shell command substitution four
    times in two days. Nothing here goes near a shell.

    FAILS SOFT AND SAYS SO. Every caller must treat False as "the early
    warning is unavailable" and carry on with the git-published claims, which
    are what the tool has always used. An unwritable registry must never be
    the reason a session cannot claim work.
    """
    try:
        p = path_for(name)
        prev = {}
        if os.path.exists(p):
            with io.open(p, encoding='utf-8') as fh:
                prev = json.load(fh)
        prev['claims'] = list(claims or [])
        prev['claims_updated'] = time.strftime('%Y-%m-%dT%H:%M:%S')
        prev.setdefault('session', name)
        write_status(name, prev)
        return True
    except Exception:                                            # noqa: BLE001
        return False


def read_claims(exclude=None):
    """[(session, claim_dict)] from every OTHER session's row.

    Returns [] on any failure -- an unreadable registry is an absent early
    warning, never a refusal. A row with no `claims` key is a session running
    a build of sairn_claim.py that does not publish yet, which is the ordinary
    state during a rollout and is not an error.
    """
    out = []
    # NO try/except AROUND THE GLOB, and that is measured rather than assumed.
    # One was written here and then removed: glob.glob() returns [] for a
    # directory that does not exist rather than raising, so nothing this
    # function is actually given could reach the handler. The negative control
    # planted a `raise` in it and ran SILENT -- a guard indistinguishable from
    # its own absence, which is PR 1.1 and is the second one of mine this
    # session has deleted rather than kept for comfort. The reachable guard is
    # the per-file one below, and that is the one the arms hold.
    names = sorted(glob.glob(os.path.join(STATUS_DIR, '*.json')))
    for full in names:
        sess = os.path.splitext(os.path.basename(full))[0]
        if exclude and sess == exclude:
            continue
        try:
            with io.open(full, encoding='utf-8') as fh:
                row = json.load(fh)
        except Exception:                                        # noqa: BLE001
            continue
        for c in (row.get('claims') or []):
            if isinstance(c, dict):
                out.append((sess, c))
    return out


def write_status(name, payload):
    """Atomic: temp file in the same directory, then os.replace().

    The temp name carries a uuid so two writes by the SAME agent -- the one
    case where two writers legitimately share a path -- cannot collide on the
    temp file either. Last write wins, and neither can leave a torn file.

    ── THE WINDOWS HALF, FOUND BY THE CONCURRENCY PROBE AND NOT BY READING ───
    `os.replace` is atomic everywhere, but on Windows it FAILS with
    PermissionError when another process currently has the destination open --
    including a reader that opened it a microsecond earlier. Driving four
    processes at one section left ELEVEN orphaned `.tmp-` files and crashed the
    losing writers with a traceback, because the first version called replace
    once and let the exception out.

    So: retry a few times with a short backoff, and on final failure REPORT it
    and raise a clean error rather than a traceback. The temp file is removed
    in a finally either way -- a write that failed must not leave litter that
    looks like a write in flight for ever.

    This is a real property of the platform, not a flake to paper over: a
    registry every agent writes to on every status change will hit it.
    """
    os.makedirs(STATUS_DIR, exist_ok=True)
    final = path_for(name)
    tmp = final + '.tmp-' + uuid.uuid4().hex[:8]
    try:
        with io.open(tmp, 'w', encoding='utf-8', newline='\n') as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False, sort_keys=True)
        last = None
        for attempt in range(_RETRIES):
            try:
                os.replace(tmp, final)
                return final
            except OSError as e:
                last = e
                time.sleep(_BACKOFF * (attempt + 1))
        raise IOError(
            'could not replace %s after %d attempts (%s). On Windows this '
            'means another process held the file open the whole time; the '
            'status was NOT written and nothing here pretends it was.'
            % (final, _RETRIES, last))
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


def read_one(full):
    """(entry, error). A TRANSIENT OPEN FAILURE IS NOT A CORRUPT FILE.

    ── FOUND BY THE PROBE, AND IT WOULD HAVE BEEN A FALSE ALARM IN PRODUCTION ─
    A reader looping over the registry while four agents wrote to it hit
    PermissionError on 5 of 2,867 reads -- the Windows counterpart of the
    replace-side race: for the instant a rename is landing, an opener of the
    destination is refused. The file is not damaged; it is momentarily
    unopenable.

    The first version treated any exception as `unreadable`, so a perfectly
    healthy agent would have been reported UNREADABLE and the whole run pushed
    to exit 2, at random, roughly twice in a thousand reads. A registry that
    cries wolf twice a day is one nobody reads.

    So an OPEN failure is retried; only a file that still will not open, or one
    that opens and does not parse, is a finding. The two are reported with
    different words, because "I could not open it" and "its contents are
    wrong" are different facts about a different agent's health.
    """
    last = None
    for attempt in range(_RETRIES):
        try:
            with io.open(full, encoding='utf-8') as fh:
                raw = fh.read()
            break
        except OSError as e:
            last = e
            time.sleep(_BACKOFF * (attempt + 1))
    else:
        return None, ('could not be opened after %d attempts (%s) -- this is '
                      'an ACCESS problem, not a damaged file'
                      % (_RETRIES, str(last)[:90]))
    try:
        d = json.loads(raw)
    except Exception as e:                                       # noqa: BLE001
        return None, 'does not parse as JSON: %s' % str(e)[:110]
    if not isinstance(d, dict):
        return None, 'parsed, but is not a JSON object'
    return d, None


def read_all():
    """([entry], problem). `problem` is set ONLY when the whole read failed.

    A single unreadable file is an entry with `unreadable` set -- NAMED, never
    dropped. One agent writing garbage must not make the other four invisible,
    and silently skipping it would report a busy platform as quieter than it is.
    """
    if not os.path.isdir(STATUS_DIR):
        return None, ('no status directory at %s -- the registry has never '
                      'been written to, so this did NOT check anything'
                      % STATUS_DIR)
    out = []
    try:
        names = sorted(os.listdir(STATUS_DIR))
    except OSError as e:
        return None, 'could not list %s: %s' % (STATUS_DIR, e)
    for fn in names:
        if not fn.endswith('.json'):
            continue      # .tmp-* files are a write in flight, not an entry
        full = os.path.join(STATUS_DIR, fn)
        d, err = read_one(full)
        if err:
            out.append({'session': fn[:-5], 'unreadable': err, 'path': full})
            continue
        d['session'] = d.get('session') or fn[:-5]
        d['path'] = full
        d['age_seconds'] = max(0.0, time.time() - os.path.getmtime(full))
        out.append(d)
    return out, None


def liveness(entry):
    """(state, why) for the agent that wrote this entry.

    ALIVE / DEAD / UNKNOWN comes from session_lock_check.owner_state(), which
    owns the recycled-pid defence. UNKNOWN then falls back to AGE, and says
    which of the two answered -- a verdict whose basis is invisible is one
    nobody can argue with.
    """
    if entry.get('unreadable'):
        return 'UNREADABLE', entry['unreadable']
    mod = _lockmod()
    if mod is not None:
        try:
            state, why = mod.owner_state(entry)
            if state == mod.ALIVE:
                return 'LIVE', why
            if state == mod.SELF:
                return 'LIVE (this session)', why
            if state == mod.DEAD:
                return 'DEAD', why
        except Exception as e:                                   # noqa: BLE001
            pass
    age = entry.get('age_seconds')
    if age is None:
        return 'UNKNOWN', 'no liveness signal and no file age'
    if age > STALE_SECONDS:
        return 'STALE', ('liveness could not be determined and the status has '
                         'not moved in %.1f hours' % (age / 3600.0))
    return 'RECENT', ('liveness could not be determined; the status was '
                      'written %.0f minutes ago' % (age / 60.0))


# ── the join, which is dispatch_state's logic pointed at a live input ───────

STOP = set('''a an and are as at be but by for from in into is it its of on or
the to with this that these those work on item items items. session sessions
continue continued next then also plus new fix fixed build built check checks
run runs add added'''.split())


def words(text):
    out = set()
    for w in ''.join(c.lower() if (c.isalnum() or c == '_') else ' '
                     for c in str(text or '')).split():
        if len(w) > 3 and w not in STOP:
            out.add(w)
    return out


def overlaps(entries):
    """Pairs of LIVE agents whose task strings share vocabulary.

    CANDIDATES, NOT A VERDICT, and the distinction is the same one
    dispatch_state.py makes about itself: whether two task strings describe the
    same WORK is a judgement, and the word-overlap version of that judgement
    scored 38% with five false positives out of five when this platform last
    measured it. This narrows what a human has to read. It decides nothing.
    """
    live = [e for e in entries
            if not e.get('unreadable') and e.get('state') != 'idle'
            and liveness(e)[0].startswith(('LIVE', 'RECENT'))]
    pairs = []
    for i, a in enumerate(live):
        for b in live[i + 1:]:
            shared = words(a.get('task')) & words(b.get('task'))
            if shared:
                pairs.append((a['session'], b['session'], sorted(shared)))
    return pairs


# ── THE NOTE FIELD APPENDS. IT USED TO EAT WHAT WAS ALREADY THERE ───────────
# `--note` REPLACED the whole field on every `set` that passed it -- no append,
# no diff, no confirmation, no warning -- and on 2026-09-22 that destroyed two
# notes addressed to other sessions, which were restored from memory rather
# than from the tool. Recorded as tool-bugs item 12.
#
# THE FIRST ACCOUNT OF THE BUG WAS WRONG AND THE CORRECTION IS WHY THIS COMMENT
# IS HERE: it was reported as "any `set` loses the note, including a bare
# `--state idle`". It never did. payload() carries every unpassed field forward,
# driven against a scratch registry via SAIRN_STATUS_DIR -- NOTE ONE survives
# `set --state idle` and dies only when `--note` is passed again. So the loss
# always needed an author who passed `--note`. Probe arm 13e pins the
# carry-forward half so this change cannot introduce the bug that was wrongly
# reported.
#
# WHY APPEND AND NOT WARN-AND-CONFIRM (Michael's ruling, 2026-09-22): this tool
# runs inside a fast, silent workflow and must stay cheap enough to run every
# few minutes. A confirmation prompt stalls a session on something that should
# just work. `--note-replace` carries the rare full replacement, and is also the
# sanctioned way to PRUNE -- so pruning is a thing somebody decides, never a
# side effect of writing.
#
# NOTHING IS EVER DROPPED TO CONTROL GROWTH. A cap that discards the oldest
# entries would be the same silent destruction one layer down, so an oversized
# note WARNS the author and keeps every byte. The risk it warns about is real
# and specific: `report()` prints `note[:100]`, so a message appended under
# 40KB of history has been written and delivered nowhere.
NOTE_SEP = '\n\n--- appended %s UTC ---\n'
NOTE_WARN_CHARS = 16000


def note_entry(text):
    return (NOTE_SEP % time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime())) + text


def resolve_note(args, prev):
    """The stored note for this write. Callers have already validated the flags.

    Three cases and no fourth: neither flag given carries the previous value
    forward unchanged; `--note-replace` is the stored value outright; `--note`
    is appended to whatever was there.
    """
    replace = getattr(args, 'note_replace', None)
    if replace is not None:
        return replace
    if args.note is None:
        return prev.get('note')
    old = prev.get('note') or ''
    return (old.rstrip() + note_entry(args.note)) if old.strip() else args.note


def check_note_flags(args):
    """(message, exit_code) when the note flags are unusable, else (None, None).

    REFUSES RATHER THAN GUESSES in both ambiguous cases. An empty `--note` is
    the dangerous one: it reads like a wipe, it would append nothing, and
    silently doing either is how this field lost data in the first place.
    """
    replace = getattr(args, 'note_replace', None)
    if args.note is not None and replace is not None:
        return ('--note and --note-replace were both passed and they mean '
                'opposite things. Refusing rather than picking one: --note '
                'APPENDS, --note-replace REPLACES the whole field.'), EXIT_COULD_NOT_RUN
    if args.note is not None and not args.note.strip():
        return ('--note was passed with nothing in it. It APPENDS, so this '
                'would add nothing -- and it is not a way to clear the field '
                'either. To actually clear it, say so: --note-replace ""'), EXIT_COULD_NOT_RUN
    return None, None


def payload(args, existing=None):
    mod = _lockmod()
    pid = sig = None
    if mod is not None:
        try:
            pid, sig, _why = mod.self_identity()
        except Exception:                                        # noqa: BLE001
            pass
    prev = existing or {}
    return {
        'session': args.session or clone_name(),
        'clone': REPO,
        'state': args.state or prev.get('state') or 'working',
        'task': args.task if args.task is not None else prev.get('task', ''),
        'item': args.item if args.item is not None else prev.get('item'),
        'blocked_on': (args.blocked_on if args.blocked_on is not None
                       else prev.get('blocked_on')),
        'note': resolve_note(args, prev),
        'updated': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'claude_pid': pid,
        'claude_start': sig,
        'pid': os.getpid(),
    }


def cmd_set(args):
    name = args.session or clone_name()
    if args.state and args.state not in STATES:
        print('--state must be one of %s' % (STATES,))
        return EXIT_COULD_NOT_RUN
    # CHECKED BEFORE THE FILE IS READ, so a refusal cannot leave a half-write.
    _why, _rc = check_note_flags(args)
    if _why:
        print(_why)
        return _rc
    # BLOCKED WITHOUT A BLOCKER IS A SILENCE, NOT A STATUS. The whole value of
    # this registry to Michael is knowing what is waiting on him; a `blocked`
    # row that does not say on what is a row he cannot act on.
    existing = None
    p = path_for(name)
    if os.path.exists(p):
        try:
            with io.open(p, encoding='utf-8') as fh:
                existing = json.load(fh)
        except Exception:                                        # noqa: BLE001
            existing = None
    body = payload(args, existing)
    if body['state'] == 'blocked' and not str(body.get('blocked_on') or '').strip():
        print('state=blocked requires --blocked-on "<what is it waiting on>". '
              'A blocked row nobody can act on is a silence wearing a status.')
        return EXIT_COULD_NOT_RUN
    # ── AND A ROW THAT IS NOT BLOCKED MUST NOT CARRY A BLOCKER (2026-09-18) ──
    # `blocked_on` is CARRIED FORWARD by payload() when the flag is not passed,
    # which is right for `task` and wrong for this: moving from blocked to
    # working means the block cleared, and nothing said so. The registry then
    # prints "BLOCKED ON: <something that is over>" under a row whose state says
    # working, and every reader has to guess which half is current.
    #
    # THIS HAS NOW HAPPENED TWICE AND THE SECOND TIME WAS NOT MINE. On
    # 2026-09-17 my own row carried a resolved push-block until I passed
    # `--blocked-on ""` by hand. On 2026-09-18 cc's row was still reporting
    # itself blocked on a claim of mine I had RELEASED, while its state read
    # working -- so a real session was advertising a block that did not exist,
    # to four other sessions, for hours.
    #
    # CLEARED RATHER THAN REFUSED, deliberately. Refusing the write would make
    # the common `set --state working --task "..."` fail for a reason the caller
    # did not ask about, and a status tool that is annoying to run is a status
    # tool nobody runs. The clearing is ANNOUNCED so it is not silent either.
    if body['state'] != 'blocked' and str(body.get('blocked_on') or '').strip():
        if args.blocked_on is None:
            print('  CLEARED a stale blocked_on: state is %r, so the block it '
                  'named is over.\n    was: %s'
                  % (body['state'], str(body['blocked_on'])[:120]))
            body['blocked_on'] = None
        else:
            print('  NOTE: state is %r and a blocked_on was passed explicitly. '
                  'Kept, because you asked for it -- but only state=blocked is '
                  'read as "waiting on somebody".' % body['state'])
    written = write_status(name, body)
    print('status written: %s' % written)
    print('  %s  %s  %s' % (body['session'], body['state'],
                            (body['task'] or '(no task)')[:90]))
    # ── THE WRITE IS RE-READ, NOT ASSUMED ───────────────────────────────────
    # The whole failure this field is famous for is a writer seeing a normal
    # success line while the content was gone. "It exited 0" and "it stored
    # what I sent" are two claims and only one of them was checked. So the
    # appended text is confirmed FROM DISK and echoed back, and a mismatch is
    # COULD NOT RUN rather than a quiet pass.
    if args.note is not None or getattr(args, 'note_replace', None) is not None:
        sent = args.note if args.note is not None else args.note_replace
        stored = ''
        try:
            with io.open(written, encoding='utf-8') as fh:
                stored = (json.load(fh) or {}).get('note') or ''
        except Exception as exc:                                 # noqa: BLE001
            print('  COULD NOT RE-READ the row just written (%s), so this '
                  'write is UNVERIFIED rather than confirmed.' % exc)
            return EXIT_COULD_NOT_RUN
        if sent and sent not in stored:
            print('  THE NOTE DID NOT LAND. The file was written and does not '
                  'contain what was sent. Reporting COULD NOT RUN rather than '
                  'success -- this is exactly the silent loss this field has '
                  'already cost real messages to.')
            return EXIT_COULD_NOT_RUN
        print('  note %s and CONFIRMED by re-reading the file: %s'
              % ('REPLACED' if args.note is None else 'APPENDED',
                 (sent or '(cleared)').strip()[:120]))
        if len(stored) > NOTE_WARN_CHARS:
            print('  PRUNE THIS NOTE. It is %d characters and every reader '
                  'prints only the first 100, so anything appended now is '
                  'stored and delivered nowhere.' % len(stored))
            print('    NOTHING WAS DROPPED to tell you this -- dropping the '
                  'oldest entries would be the same silent loss one layer '
                  'down. Prune deliberately:')
            print('      python tools/sairn_status.py set '
                  '--note-replace "<what is still live>"')
    if body['blocked_on']:
        print('  blocked on: %s' % body['blocked_on'])
    if body['claude_pid'] is None:
        print('  NOTE: CLAUDE_PID is not in this environment, so other readers '
              'will fall back to file age for liveness rather than to a real '
              'process check.')
    return EXIT_CLEAN


def report(entries, as_json):
    if as_json:
        print(json.dumps({'status_dir': STATUS_DIR,
                          'entries': entries,
                          'liveness': {e['session']: liveness(e)[0]
                                       for e in entries},
                          'overlap_candidates': overlaps(entries)}, indent=2))
        return
    print('SAIRN STATUS REGISTRY -- live, outside git, no push/pull needed')
    print('  %s' % STATUS_DIR)
    print('  %d session(s) have reported' % len(entries))
    print('')
    for e in sorted(entries, key=lambda x: x['session']):
        state, why = liveness(e)
        if e.get('unreadable'):
            print('  %-10s UNREADABLE -- %s' % (e['session'], e['unreadable']))
            print('             NAMED rather than dropped: one agent writing '
                  'garbage must not\n             make the others invisible.')
            continue
        print('  %-10s %-18s %s' % (e['session'], e.get('state', '?'), state))
        print('             %s' % ((e.get('task') or '(no task)')[:100]))
        if e.get('blocked_on'):
            print('             BLOCKED ON: %s' % e['blocked_on'])
        if e.get('note'):
            print('             note: %s' % str(e['note'])[:100])
        print('             updated %s, %s' % (e.get('updated', '?'), why[:90]))
    pairs = overlaps(entries)
    print('')
    if pairs:
        print('  OVERLAP CANDIDATES (%d) -- shared words between LIVE agents:'
              % len(pairs))
        for a, b, shared in pairs:
            print('    %s <-> %s : %s' % (a, b, ', '.join(shared)))
    else:
        print('  No two live agents share task vocabulary.')
    print('')
    print('  THIS DOES NOT DECIDE ANYTHING. Shared words are not shared work --')
    print('  that judgement scored 38% with five false positives out of five')
    print('  the last time this platform automated it. Read the rows.')


def self_check(verbose=True):
    """Fixtures with known answers, run BEFORE any real file is classified."""
    bad = []
    cases = [
        ({'task': 'the removal path check and its fixture arm'},
         {'task': 'removal path baseline burn-down'}, True),
        ({'task': 'sairnvet dosing audit trail'},
         {'task': 'sairnbiz timesheet roster'}, False),
        # The stop-list earns its place: two agents both saying "continue the
        # next item" share nothing real, and without it every pair overlaps.
        ({'task': 'continue work on the next item'},
         {'task': 'continue work on the next item'}, False),
    ]
    for a, b, want in cases:
        got = bool(words(a['task']) & words(b['task']))
        if verbose:
            print('    %-46s shared=%-5s %s'
                  % (a['task'][:46], got, 'ok' if got == want else
                     'EXPECTED %s' % want))
        if got != want:
            bad.append((a['task'], got, want))
    return bad


def cmd_hook():
    """SessionStart: put the registry in front of the agent, and never block.

    The scope was that EVERY agent reads this at session start. A line in
    CLAUDE.md asking them to is enforced by remembering, which this platform's
    own tooling says is enforced on the days people remember -- and those are
    not the days it matters. So it is a hook, beside the lock and the claim
    hook that already run there.

    IT FAILS OPEN, ALWAYS AND DELIBERATELY. A session must start whatever went
    wrong in here; a status registry that can prevent work is worse than no
    registry. That is the opposite of the fail-CLOSED rule this repo applies to
    CHECKS, and the difference is the consequence: a check that cannot run must
    not report a pass, but an advisory that cannot run must not stop the work.
    `sairn_claim_hook.py` makes the same call for the same reason and says so.

    COULD-NOT-READ IS STILL SAID OUT LOUD. Failing open is not failing silent:
    an empty or unreadable registry emits the sentence saying it is unknown
    rather than emitting nothing, because nothing reads as "nobody is working".
    """
    lines = []
    try:
        entries, problem = read_all()
        if entries is None:
            lines.append('SHARED STATUS REGISTRY: %s' % problem)
            lines.append('Treat that as UNKNOWN, not as "nobody else is '
                         'working". Write yours with: python '
                         'tools/sairn_status.py set --state working --task "..."')
        elif not entries:
            lines.append('SHARED STATUS REGISTRY: it exists and is EMPTY. That '
                         'is indistinguishable from a registry nothing writes '
                         'to -- not evidence that nobody is working.')
        else:
            live = []
            for e in sorted(entries, key=lambda x: x['session']):
                state, why = liveness(e)
                if e.get('unreadable'):
                    live.append('  %-9s UNREADABLE -- %s'
                                % (e['session'], e['unreadable'][:70]))
                    continue
                live.append('  %-9s %-8s %-6s %s'
                            % (e['session'], e.get('state', '?'), state.split()[0],
                               (e.get('task') or '(no task)')[:78]))
                if e.get('blocked_on'):
                    live.append('            BLOCKED ON: %s'
                                % str(e['blocked_on'])[:78])
            lines.append('SHARED STATUS REGISTRY -- what every agent on this '
                         'machine says it is doing, live, no fetch needed:')
            lines.extend(live)
            pairs = overlaps(entries)
            if pairs:
                lines.append('')
                lines.append('OVERLAP CANDIDATES -- shared words between live '
                             'agents. NOT a verdict; read the rows:')
                for a, b, shared in pairs:
                    lines.append('  %s <-> %s : %s' % (a, b, ', '.join(shared)))
        lines.append('')
        lines.append('WRITE YOUR OWN ROW when your work changes: python '
                     'tools/sairn_status.py set --state working --task "..." '
                     '(or --state blocked --blocked-on "...").')
        print(json.dumps({
            'hookSpecificOutput': {'hookEventName': 'SessionStart',
                                   'additionalContext': '\n'.join(lines)},
            'suppressOutput': True}))
    except Exception:                                            # noqa: BLE001
        pass
    return EXIT_CLEAN


def main(argv=None):
    if argv is None and len(sys.argv) > 1 and sys.argv[1] == '--hook':
        return cmd_hook()
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd')
    s = sub.add_parser('set')
    s.add_argument('--state', default=None)
    s.add_argument('--task', default=None)
    s.add_argument('--item', default=None)
    s.add_argument('--blocked-on', dest='blocked_on', default=None)
    s.add_argument('--note', default=None,
                   help='APPEND to this session\'s note, stamped with the time')
    s.add_argument('--note-replace', dest='note_replace', default=None,
                   help='REPLACE the whole note. Also the sanctioned way to '
                        'prune it -- pruning is decided, never a side effect')
    s.add_argument('--session', default=None)
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--self-check', action='store_true', dest='selfcheck')
    ap.add_argument('--session', default=None)
    args = ap.parse_args(argv)

    if args.cmd == 'set':
        return cmd_set(args)

    if args.selfcheck:
        bad = self_check()
        print('\n%d case(s) wrong' % len(bad))
        return EXIT_CLEAN if not bad else EXIT_FINDING

    # THE BLIND LOCK RUNS FIRST. If the overlap rule fails its own fixtures,
    # nothing is classified -- the same shape dispatch_state.py uses, and for
    # the same reason: a rule that has stopped working produces a clean, empty
    # and completely wrong answer.
    bad = self_check(verbose=False)
    if bad:
        print('COULD NOT RUN -- the overlap rule failed its own fixtures, so '
              'nothing was joined:')
        for t, got, want in bad:
            print('  %r -> %s, expected %s' % (t, got, want))
        return EXIT_COULD_NOT_RUN

    entries, problem = read_all()
    if entries is None:
        print('COULD NOT RUN: %s' % problem)
        return EXIT_COULD_NOT_RUN
    if not entries:
        # AN EMPTY REGISTRY IS NOT "NOBODY IS WORKING". It is indistinguishable
        # from a registry nothing writes to, and reading it as all-clear is the
        # exact failure this whole file exists to prevent.
        print('COULD NOT RUN: the status directory exists but holds no entries '
              '(%s).\nThat is NOT "nobody is working" -- it is '
              'indistinguishable from a registry\nnothing is writing to. Run '
              '`python tools/sairn_status.py set --state working --task "..."`'
              % STATUS_DIR)
        return EXIT_COULD_NOT_RUN

    report(entries, args.json)
    unreadable = [e for e in entries if e.get('unreadable')]
    return EXIT_COULD_NOT_RUN if unreadable else EXIT_CLEAN


if __name__ == '__main__':
    sys.exit(main())
