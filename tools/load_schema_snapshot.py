"""Install a fresh db/schema_snapshot.json, and REFUSE a truncated one.

    python tools/load_schema_snapshot.py <path-to-candidate.json>
    python tools/load_schema_snapshot.py <path> --write
    python tools/load_schema_snapshot.py <path> --write --allow-shrink "12 tables dropped in the Sept cleanup"

WHY THIS EXISTS, AND IT IS A COORDINATION FIX RATHER THAN A CODE ONE.
The snapshot is a PASTED CAPTURE: a query is run in the Supabase editor, the
single JSON cell is copied, and somebody saves it. On 2026-09-12/13 that relay
was attempted through chat FOUR times and failed THREE:

  * twice the payload arrived EMPTY -- the instruction said "save this exact
    JSON" and there was nothing after the colon;
  * once a message announcing the file contained no file.

Every one was caught only because the receiving session checked. Nothing
structural was stopping a session from writing whatever it thought it had.

THE FAILURE THIS REFUSES IS NOT THE EMPTY ONE. An empty or malformed payload
fails loudly the moment anything parses it. THE DANGEROUS SHAPE IS A SHORT ONE
THAT STILL PARSES -- a capture that lost tables somewhere between the editor
and the file. Nothing downstream can tell that from a database that genuinely
lost those tables, and this platform has the exact consumer that turns it into
a confident wrong answer: tools/schema_snapshot_freshness.py reads an absence
as "this migration was never run" and will happily say so about 89 tables.
A truncated capture would manufacture that finding out of nothing.

So the rule is asymmetric on purpose. Tables APPEARING is ordinary. Tables
DISAPPEARING is the signature of a bad transfer and needs a human to say, in
words, why -- `--allow-shrink "<reason>"`, recorded in the output. Same
two-list discipline as the cache-purge guards: an exclusion is a decision with
a reason beside it, never a silence.

IT ALSO REFUSES A CAPTURE THAT IS NOT NEWER. A capture older than the one
already committed is either the wrong file or a paste of the current one, and
installing it silently rolls the record backwards.

WHAT IT DELIBERATELY DOES NOT DO: commit. Writing the file and publishing it
are separate acts, and a tool that did both would make `--write` an
irreversible step taken to "see what it says". Run it with no flags first --
that is the normal use -- read the delta, then add `--write`.

WHAT IT CANNOT SEE, said here rather than discovered later:
  * whether the capture is COMPLETE for the database. It compares one capture
    against the previous one; two consecutive truncated captures of the same
    size look stable;
  * whether the query was scoped to the right schemas. A capture of a subset
    that is internally consistent passes;
  * column-level loss. This is table-level only.

Exit 0 on a clean comparison (and, with --write, a successful write), 1 when it
refuses, 2 when the candidate or the current file cannot be read at all --
which is not a pass.
"""
import datetime
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CURRENT = os.path.join(REPO, 'db', 'schema_snapshot.json')

STAMP_RE = re.compile(r'^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2}):(\d{2})'
                      r'(?:\.\d+)?\s*(Z|[+-]\d{2}(?::?\d{2})?)?$')


def parse_stamp(s):
    """Naive-UTC datetime from the capture's stamp, or None.

    The offset is TWO digits in the capture (`+00`) and four in git's
    iso-strict. Requiring four is a real bug this platform shipped once, in
    schema_snapshot_freshness.py, where it made every verdict "undecidable" --
    an answer that looked exactly like the tool's previous correct refusal.
    """
    s = (s or '').strip()
    m = STAMP_RE.match(s)
    if not m:
        return None
    y, mo, d, hh, mm, ss, off = m.groups()
    dt = datetime.datetime(int(y), int(mo), int(d), int(hh), int(mm), int(ss))
    if off and off != 'Z':
        off = off.replace(':', '')
        sign = -1 if off[0] == '-' else 1
        dt -= datetime.timedelta(hours=sign * int(off[1:3]),
                                 minutes=sign * int(off[3:5] or 0))
    return dt


def tables(snap):
    """Table names only -- classified by the VALUE's shape, not by the name.

    ── THE LIMIT THIS USED TO HAVE WAS NOT HYPOTHETICAL, 2026-09-16 ─────────
    This read `not k.startswith('_')`, and its own docstring named the risk:
    `sql/` declares baseline tables whose names begin with an underscore, and
    it said none had ever been in a capture. TWO OF THEM ARE, AND HAVE BEEN
    SINCE THE 2026-08-26 CAPTURE: `_anon_grant_baseline_2026_08_26` and
    `_anon_nontable_baseline_2026_08_26`. They are real tables in `public`
    -- created by sql/anon_authenticated_grant_revoke_2026-08-26.sql -- and
    the hardening handoff that created them says in terms that they MUST STAY.
    The name rule classified both as metadata, so a truncated capture that
    lost them would have passed the shrink guard in silence. The one guard
    whose whole job is "tables must not disappear" could not see the two
    tables somebody wrote down as must-not-disappear.

    A CAPTURE'S SHAPE ANSWERS THIS AND A NAME CANNOT. Every table entry the
    query emits is a LIST of column names; the only two genuine metadata keys
    it emits are `_constraints` (an object) and `_generated_at` (a string).
    So the list test is both stricter and correct where the name test was
    neither, and it needs no allowlist to maintain.
    """
    return {k for k, v in snap.items() if isinstance(v, list)}


def load(path, label):
    if not os.path.exists(path):
        return None, '%s does not exist: %s' % (label, path)
    try:
        raw = io.open(path, encoding='utf-8').read()
    except Exception as e:
        return None, '%s could not be read: %s' % (label, e)
    if not raw.strip():
        return None, ('%s is EMPTY. This is the shape the chat relay produced '
                      'twice on 2026-09-12/13 -- an instruction with no payload '
                      'after it.' % label)
    try:
        snap = json.loads(raw)
    except Exception as e:
        return None, ('%s is not valid JSON: %s. A capture cut off mid-transfer '
                      'usually lands here, which is the LOUD failure; the quiet '
                      'one is a short capture that still parses.' % (label, e))
    if not isinstance(snap, dict):
        return None, '%s parsed to %s, not an object' % (label, type(snap).__name__)
    return snap, None


def compare(cand, cur):
    """(problems, notes) -- problems refuse the load, notes are reported."""
    problems, notes = [], []

    ct, pt = tables(cand), tables(cur)
    gained, lost = sorted(ct - pt), sorted(pt - ct)

    cs, ps = parse_stamp(str(cand.get('_generated_at') or '')), \
        parse_stamp(str(cur.get('_generated_at') or ''))
    if cs is None:
        problems.append('the candidate has no usable _generated_at. Every '
                        'downstream verdict is scoped to that instant, so a '
                        'capture without one cannot be reasoned from.')
    elif ps is not None and cs <= ps:
        problems.append('the candidate is NOT NEWER than the committed capture '
                        '(%s vs %s). Either it is the wrong file or it is a '
                        'paste of the one already here.'
                        % (cand.get('_generated_at'), cur.get('_generated_at')))

    if lost:
        problems.append('%d table(s) present in the committed capture are '
                        'ABSENT from the candidate. That is the signature of a '
                        'truncated transfer, and it is indistinguishable from '
                        'tables genuinely dropped -- say which in words:\n'
                        '      %s' % (len(lost), ', '.join(lost)))

    notes.append('committed : %s  (%d tables)'
                 % (cur.get('_generated_at'), len(pt)))
    notes.append('candidate : %s  (%d tables)'
                 % (cand.get('_generated_at'), len(ct)))
    notes.append('gained    : %d%s'
                 % (len(gained), ('  ' + ', '.join(gained[:12])
                                  + (' ...' if len(gained) > 12 else '')) if gained else ''))
    notes.append('lost      : %d%s'
                 % (len(lost), ('  ' + ', '.join(lost[:12])
                                + (' ...' if len(lost) > 12 else '')) if lost else ''))
    return problems, notes


def main(argv):
    args = [a for a in argv if not a.startswith('--')]
    if not args:
        print(__doc__.strip().split('\n\n')[1])
        return 2
    path = args[0]
    write = '--write' in argv
    shrink_reason = None
    if '--allow-shrink' in argv:
        i = argv.index('--allow-shrink')
        shrink_reason = argv[i + 1] if i + 1 < len(argv) else ''
        if not (shrink_reason or '').strip():
            print('--allow-shrink needs a REASON in quotes. An override nobody '
                  'states is how a gate gets hollowed out.')
            return 2

    cand, err = load(path, 'the candidate')
    if err:
        print('REFUSED -- ' + err)
        return 2
    cur, err = load(CURRENT, 'db/schema_snapshot.json')
    if err:
        print('REFUSED -- ' + err)
        return 2

    problems, notes = compare(cand, cur)
    print('SCHEMA SNAPSHOT LOAD CHECK')
    for n in notes:
        print('  ' + n)

    if shrink_reason:
        problems = [p for p in problems if 'ABSENT from the candidate' not in p]
        print('\n  SHRINK ALLOWED BY HAND: %s' % shrink_reason)
        print('  Recorded here rather than assumed. Put it in the commit message too.')

    if problems:
        print('\nREFUSED. %d problem(s):' % len(problems))
        for p in problems:
            print('  * ' + p)
        print('\nNothing was written.')
        return 1

    if not write:
        print('\nOK to load. Nothing written -- re-run with --write to install it.')
        return 0

    # The candidate's OWN BYTES, not a re-serialisation. A capture is a record
    # of what the database said; round-tripping it through json.dumps would
    # silently reformat and reorder it, so a later `git diff` between two
    # captures would show churn that never happened in the database.
    raw = io.open(path, encoding='utf-8').read()
    io.open(CURRENT, 'w', encoding='utf-8', newline='\n').write(raw)
    print('\nWRITTEN to db/schema_snapshot.json (%d bytes, verbatim). NOT '
          'committed -- that is a separate, deliberate act.' % len(raw))
    print('Then re-run:  python tools/schema_snapshot_freshness.py')
    return 0


if __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.exit(main(sys.argv[1:]))
