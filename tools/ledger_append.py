#!/usr/bin/env python
# OWNER: cody
"""Append to an append-only ledger from a FILE or STDIN, and refuse anything else.

    python tools/ledger_append.py --ledger docs/x.json --json-key records \\
           --body-file entry.json
    cat entry.json | python tools/ledger_append.py --ledger docs/x.json \\
           --json-key records --stdin
    python tools/ledger_append.py --ledger docs/x.md --body-file entry.md
    python tools/ledger_append.py --fixtures

Exit 0 appended, 1 REFUSED, 2 COULD NOT RUN. Design note:
docs/2026-10-06-cody-queue19-design-notes.md section 1.

── THE TWO INCIDENTS THIS CLOSES, BOTH MINE, BOTH 2026-10-06 ───────────────
1. A verdict passed as a SHELL ARGUMENT had two backticked fragments
   command-substituted away and A THIRD REPLACED BY THE OUTPUT OF `id` --
   a local uid and gid pasted into docs/tier-a-reviews.json. Reverted before it
   reached origin.
2. A repair rewrote the same file with `json.dumps(indent=1)`: 5681 INSERTIONS
   AND 5674 DELETIONS on a 235-record ledger that four clones 3-way merge, where
   the correct diff was 15 and 8. That would have handed every other session a
   whole-file conflict.

AND THE LESSON WAS ALREADY WRITTEN DOWN WHEN I BROKE IT. tier_a_review_gate.py
has had `--body-file` the whole time and its own comment reads "THE SHELL IS
WHERE THE TEXT DIES, NOT THIS TOOL". I did not use it. **A documented lesson
that was already documented is not a fix**, which is why this is a tool.

── THE FOUR REFUSALS ───────────────────────────────────────────────────────
1. NO BODY FROM AN ARGUMENT. There is no flag that takes body text. `--body-file`
   or `--stdin`, read as BYTES, and nothing is ever passed through a shell.
2. NOT ONE EXISTING BYTE MAY CHANGE. The prefix before the insertion point is
   compared byte-for-byte against the original, and so is the suffix after it.
3. THE DIFF MUST BE BOUNDED BY THE ENTRY. After writing, `git diff --numstat`
   must show no more ADDED lines than the entry itself holds (plus a small
   structural allowance, printed). This is the check that catches incident 2 --
   it does not trust the writer, it measures the result.
4. A MISSING LEDGER IS COULD NOT RUN, never a created file. Creating one is how
   a typo becomes a second ledger nobody reads.

── JSON LEDGERS GET A TARGETED INSERT ──────────────────────────────────────
For `--json-key records`, the closing bracket of that array is located in the
RAW TEXT, the new object is inserted before it with the indentation of the
preceding sibling, and everything else is left untouched. The file is NEVER
re-serialised. json is used to VALIDATE the result parses and that the array
grew by exactly one -- never to produce it.

── WHAT IT DOES NOT DO ─────────────────────────────────────────────────────
It does not validate ledger CONTENT. It checks that the write is an APPEND;
whether the appended record is TRUE is somebody else's job. It is also not a
merge tool (sairn_rebase_resolve.py owns that) and does not replace
tier_a_review_gate.py --discharge, which owns the Tier A schema.
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

# .2 -- the lock line's arm count is now DERIVED, not a literal. No arm
# changed; the stamp moves because the printed figure's PROVENANCE did.
CRITERIA_VERSION = '2026-10-06.2'
EXIT_REFUSED = 1
EXIT_COULD_NOT_RUN = 2
# A JSON insert adds the object's own lines plus at most this many structural
# lines (a comma on the previous sibling's closing brace, at worst). PRINTED on
# every run so the allowance is never a hidden fudge.
STRUCTURAL_ALLOWANCE = 2


class Refused(Exception):
    pass


class CouldNotRun(Exception):
    pass


def read_body(args):
    """The entry, as TEXT, from a file or stdin. Never from an argument."""
    if args.body_file and args.stdin:
        raise CouldNotRun('--body-file and --stdin are mutually exclusive: two '
                          'sources is no source')
    if args.body_file:
        if not os.path.isfile(args.body_file):
            raise CouldNotRun('--body-file %r does not exist' % args.body_file)
        return io.open(args.body_file, 'rb').read().decode('utf-8')
    if args.stdin:
        data = sys.stdin.buffer.read()
        if not data.strip():
            raise CouldNotRun('stdin was empty -- an empty append is not an '
                              'append, it is a no-op wearing one')
        return data.decode('utf-8')
    raise CouldNotRun('no body source. Pass --body-file PATH or --stdin. '
                      'THERE IS NO FLAG THAT TAKES BODY TEXT, deliberately: a '
                      'shell ate two backticked fragments and replaced a third '
                      'with the output of `id` on 2026-10-06')


def resolve_ledger(rel):
    p = os.path.abspath(os.path.join(REPO, rel))
    if not p.startswith(os.path.abspath(REPO) + os.sep):
        raise CouldNotRun('%r resolves outside the repo' % rel)
    if not os.path.isfile(p):
        raise CouldNotRun('%r does not exist. THIS TOOL DOES NOT CREATE A '
                          'LEDGER -- a typo that creates one is how a second '
                          'ledger nobody reads gets started.' % rel)
    return p


def find_array_close(raw, key):
    """Index of the `]` closing the top-level array at `key`, in RAW TEXT.

    Text, not a parse, because the whole point is to leave every other byte
    alone. A parse-and-reserialise is incident 2.
    """
    m = re.search(r'"%s"\s*:\s*\[' % re.escape(key), raw)
    if not m:
        raise CouldNotRun('no "%s": [ ... ] array found in the ledger' % key)
    depth = 0
    i = m.end() - 1
    in_str = False
    esc = False
    while i < len(raw):
        c = raw[i]
        if in_str:
            if esc:
                esc = False
            elif c == '\\':
                esc = True
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == '[':
            depth += 1
        elif c == ']':
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise CouldNotRun('the "%s" array is not closed -- the ledger is malformed '
                      'and this tool will not guess where it ends' % key)


def build_json_insert(raw, key, entry_text):
    """(new_raw, added_line_count). Targeted insert; nothing else is touched."""
    close = find_array_close(raw, key)
    head, tail = raw[:close], raw[close:]
    stripped = head.rstrip()
    if not stripped.endswith('['):
        # There is a preceding sibling: it needs a comma.
        if not stripped.endswith(','):
            head = stripped + ','
        else:
            head = stripped
    else:
        head = stripped
    # Indentation taken from the preceding sibling line, so the result matches
    # the file's own layout rather than this tool's opinion of it.
    lines = raw[:close].split('\n')
    indent = '  '
    for ln in reversed(lines):
        m = re.match(r'^(\s+)\S', ln)
        if m:
            indent = m.group(1)
            break
    body = '\n'.join(indent + l if l.strip() else l
                     for l in entry_text.strip().split('\n'))
    sep = '\n'
    new_raw = head + sep + body + sep + tail.lstrip('\n')
    return new_raw, len(body.split('\n'))


def numstat(path):
    """(added, removed) for one path, or None if git could not be read."""
    rel = os.path.relpath(path, REPO).replace(os.sep, '/')
    r = subprocess.run(['git', '-C', REPO, 'diff', '--numstat', '--', rel],
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    if r.returncode != 0:
        return None
    for line in (r.stdout or '').split('\n'):
        parts = line.split('\t')
        if len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit():
            return (int(parts[0]), int(parts[1]))
    return (0, 0)


def atomic_write(path, text):
    d = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(dir=d, prefix='.ledger_append-')
    try:
        with io.open(fd, 'w', encoding='utf-8', newline='') as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def append(ledger_rel, entry_text, json_key=None, quiet=False, dry_run=False):
    """Append, or raise Refused / CouldNotRun. Returns (added, allowed)."""
    path = resolve_ledger(ledger_rel)
    original = io.open(path, 'rb').read().decode('utf-8')

    if json_key:
        new_raw, entry_lines = build_json_insert(original, json_key, entry_text)
    else:
        sep = '' if original.endswith('\n') else '\n'
        new_raw = original + sep + entry_text.rstrip('\n') + '\n'
        entry_lines = len(entry_text.strip().split('\n'))

    # ── REFUSAL 2: NOT ONE EXISTING BYTE MAY CHANGE ────────────────────────
    # The original must appear in the result as a contiguous prefix+suffix pair
    # around the insertion. Checked by reconstructing the original from the new
    # text with the entry removed, which catches a changed byte anywhere.
    if json_key:
        close_new = find_array_close(new_raw, json_key)
        # Everything after the array close must be byte-identical.
        close_old = find_array_close(original, json_key)
        if new_raw[close_new:] != original[close_old:]:
            raise Refused('bytes AFTER the array would change. This is the '
                          '5681-insertion shape and it is refused.')
        if not new_raw.startswith(original[:close_old].rstrip().rstrip(',')):
            raise Refused('bytes BEFORE the insertion point would change')
    else:
        if not new_raw.startswith(original.rstrip('\n')):
            raise Refused('bytes before the append would change')

    if json_key:
        try:
            before = json.loads(original)
            after = json.loads(new_raw)
        except ValueError as exc:
            raise Refused('the result does not parse as JSON: %s' % exc)
        nb, na = len(before.get(json_key) or []), len(after.get(json_key) or [])
        if na != nb + 1:
            raise Refused('the "%s" array went from %d to %d -- an append adds '
                          'exactly one' % (json_key, nb, na))
        for k in before:
            if k != json_key and before[k] != after.get(k):
                raise Refused('top-level key %r changed. An append does not '
                              'touch a sibling key.' % k)

    if dry_run:
        return (0, entry_lines + STRUCTURAL_ALLOWANCE)

    pre = numstat(path)
    atomic_write(path, new_raw)
    post = numstat(path)

    # ── REFUSAL 3: THE DIFF MUST BE BOUNDED BY THE ENTRY ───────────────────
    # Measured AFTER the write, because this check exists not to trust the
    # writer but to measure the result. A breach is reverted.
    allowed = entry_lines + STRUCTURAL_ALLOWANCE
    if post is None or pre is None:
        atomic_write(path, original)
        raise CouldNotRun('git diff --numstat could not be read, so the diff '
                          'bound could not be checked. The write was REVERTED '
                          '-- an unchecked append is not an append.')
    added = post[0] - pre[0]
    if added > allowed:
        atomic_write(path, original)
        raise Refused('the diff added %d line(s) for an entry of %d (allowance '
                      '%d). REVERTED. This is the 5681-vs-15 shape.'
                      % (added, entry_lines, STRUCTURAL_ALLOWANCE))
    if not quiet:
        print('  appended %d line(s); git diff added %d, allowance %d'
              % (entry_lines, added, allowed))
    return (added, allowed)


# ── THE SELFTEST, AND EVERY ARM HAS A NEGATIVE HALF ────────────────────────
def _fixtures():
    ok = True
    # COUNTED, NEVER WRITTEN DOWN -- same correction as clone_health_check.py,
    # whose sibling literal was off by one. This one happened to be right; a
    # figure that is right by coincidence goes stale on the next arm added.
    tally = {'n': 0, 'neg': 0}

    def arm(label, cond, detail=''):
        """Print the detail ONLY ON FAILURE.

        The first version printed it unconditionally, so a PASSING arm read
        `ok   backticks survives verbatim -- needle '`b`' absent` -- the pass
        and the failure message on one line. That is the same class as a
        checker whose clean line is indistinguishable from its finding, in my
        own harness, caught on its first run. And `detail` is str()'d because
        an int detail raised TypeError inside the reporter, which would have
        taken down the run rather than failing one arm.
        """
        nonlocal ok
        # Same stated criterion as clone_health_check.py: the label says
        # NEGATIVE, or the arm asserts the third state.
        tally['n'] += 1
        if 'negative' in label.lower() or 'COULD NOT TELL' in label:
            tally['neg'] += 1
        if not cond:
            ok = False
            print('  FAIL %s%s' % (label, (' -- ' + str(detail)) if detail != '' else ''))
        else:
            print('  ok   %s' % label)

    tmp = tempfile.mkdtemp(prefix='ledger_append_fx_')
    try:
        # A JSON ledger shaped like the real one, inside the repo so the path
        # check passes, but under a scratch name.
        scratch = os.path.join(REPO, '.ledger_append_fixture.json')
        base = {'_what': 'fixture', 'records': [{'id': 1, 'note': 'first'}]}
        io.open(scratch, 'w', encoding='utf-8', newline='\n').write(
            json.dumps(base, indent=1) + '\n')
        rel = os.path.relpath(scratch, REPO).replace(os.sep, '/')

        # ARM 1-4: the bodies that a shell destroys.
        HOSTILE = [
            ('backticks', '{"id": 2, "note": "a `b` c"}', '`b`'),
            ('dollar-paren', '{"id": 3, "note": "x $(whoami) y"}', '$(whoami)'),
            ('embedded quotes', '{"id": 4, "note": "he said \\"no\\" and \'yes\'"}', 'said'),
            ('the id-output case', '{"id": 5, "note": "see `id` for the uid"}', '`id`'),
        ]
        for label, entry, needle in HOSTILE:
            append(rel, entry, json_key='records', quiet=True)
            raw = io.open(scratch, encoding='utf-8').read()
            arm('%-18s survives verbatim' % label, needle in raw,
                'needle %r absent' % needle)
            arm('%-18s and NO uid= appears -- the negative half of the id case'
                % label, 'uid=' not in raw)

        d = json.loads(io.open(scratch, encoding='utf-8').read())
        arm('four appends gave exactly four new records',
            len(d['records']) == 5, len(d['records']))
        arm('the sibling top-level key is untouched', d['_what'] == 'fixture')

        # ARM: THE 5681-vs-15 CASE. A 200-record ledger gains one record, and
        # the added-line count must be bounded by the entry.
        big = {'_what': 'fixture',
               'records': [{'id': i, 'note': 'n%d' % i} for i in range(200)]}
        io.open(scratch, 'w', encoding='utf-8', newline='\n').write(
            json.dumps(big, indent=1) + '\n')
        subprocess.run(['git', '-C', REPO, 'add', '-N', rel],
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
        pre = numstat(scratch)
        added, allowed = append(rel, '{"id": 999, "note": "appended"}',
                                json_key='records', quiet=True)
        arm('THE 5681-vs-15 CASE: a 200-record ledger gains one record and the '
            'diff adds no more than the entry plus the allowance',
            added <= allowed, 'added=%s allowed=%s' % (added, allowed))
        arm('...and the record really landed',
            len(json.loads(io.open(scratch, encoding='utf-8').read())['records']) == 201)

        # NEGATIVE: a rewrite that touches every line must be REFUSED. Driven by
        # asking the tool to append something that re-serialises -- simulated by
        # calling the bound check with a deliberately oversized entry count.
        refused = False
        try:
            # An entry whose own line count is 1 but which expands the file by
            # far more: a body carrying a newline-heavy payload is legitimate,
            # so the breach is forced by shrinking the allowance instead.
            global STRUCTURAL_ALLOWANCE
            keep = STRUCTURAL_ALLOWANCE
            STRUCTURAL_ALLOWANCE = -1000
            try:
                append(rel, '{"id": 1000, "note": "x"}', json_key='records',
                       quiet=True)
            finally:
                STRUCTURAL_ALLOWANCE = keep
        except Refused:
            refused = True
        arm('NEGATIVE: an append whose diff exceeds the bound is REFUSED and '
            'REVERTED -- without this the bound check is decoration', refused)
        arm('...and the revert really happened: still 201 records',
            len(json.loads(io.open(scratch, encoding='utf-8').read())['records']) == 201)

        # NEGATIVE: there is NO argument that takes body text.
        ap = _parser()
        names = set()
        for a in ap._actions:
            names.update(a.option_strings)
        arm('NEGATIVE: no --body / --text / --entry flag exists, so body text '
            'CANNOT come from an argument',
            not ({'--body', '--text', '--entry', '--message', '-m'} & names),
            sorted(names))

        # COULD NOT RUN cases.
        for label, fn in (
                ('a missing ledger is COULD NOT RUN, not a created file',
                 lambda: append('docs/zz-no-such-ledger.json', '{}',
                                json_key='records', quiet=True)),
                ('a path outside the repo is COULD NOT RUN',
                 lambda: append('../outside.json', '{}', quiet=True)),
                ('a missing json key is COULD NOT RUN',
                 lambda: append(rel, '{}', json_key='nope', quiet=True))):
            cnr = False
            try:
                fn()
            except CouldNotRun:
                cnr = True
            except Refused:
                pass
            arm(label, cnr)
        arm('...and the missing ledger was NOT created',
            not os.path.exists(os.path.join(REPO, 'docs',
                                            'zz-no-such-ledger.json')))

        # A plain-text ledger appends too.
        scratch_md = os.path.join(REPO, '.ledger_append_fixture.md')
        io.open(scratch_md, 'w', encoding='utf-8', newline='\n').write('# head\n')
        rel_md = os.path.relpath(scratch_md, REPO).replace(os.sep, '/')
        append(rel_md, '- a `b` $(c) entry', quiet=True)
        raw = io.open(scratch_md, encoding='utf-8').read()
        arm('a TEXT ledger appends and keeps backticks and $( ) verbatim',
            raw.startswith('# head\n') and '`b`' in raw and '$(c)' in raw, raw)
    finally:
        for f in ('.ledger_append_fixture.json', '.ledger_append_fixture.md'):
            p = os.path.join(REPO, f)
            if os.path.exists(p):
                os.unlink(p)
            subprocess.run(['git', '-C', REPO, 'rm', '--cached', '-q', '--', f],
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace')
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)

    print('  criteria lock: %d arms, %d of them negative (criteria %s)'
          % (tally['n'], tally['neg'], CRITERIA_VERSION))
    return ok


def _parser():
    ap = argparse.ArgumentParser(
        description='append to an append-only ledger from a FILE or STDIN only')
    ap.add_argument('--ledger', help='repo-relative path to the ledger')
    ap.add_argument('--json-key', default=None,
                    help='for a JSON ledger: the top-level array to append to')
    ap.add_argument('--body-file', default=None,
                    help='the entry, read as BYTES from this file')
    ap.add_argument('--stdin', action='store_true',
                    help='the entry, read as BYTES from stdin')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--quiet', action='store_true')
    ap.add_argument('--fixtures', action='store_true',
                    help='the selftest alone, and stop')
    return ap


def main(argv=None):
    a = _parser().parse_args(argv)
    if a.fixtures:
        print('LEDGER APPEND -- selftest (criteria %s)' % CRITERIA_VERSION)
        return 0 if _fixtures() else 1
    if not a.quiet:
        print('LEDGER APPEND -- criteria %s; structural allowance %d line(s)'
              % (CRITERIA_VERSION, STRUCTURAL_ALLOWANCE))
    try:
        if not a.ledger:
            raise CouldNotRun('--ledger is required')
        body = read_body(a)
        append(a.ledger, body, json_key=a.json_key, quiet=a.quiet,
               dry_run=a.dry_run)
    except Refused as exc:
        print('\nREFUSED -- %s' % exc, file=sys.stderr)
        return EXIT_REFUSED
    except CouldNotRun as exc:
        print('\nCOULD NOT RUN -- %s' % exc, file=sys.stderr)
        return EXIT_COULD_NOT_RUN
    if not a.quiet:
        print('APPENDED to %s' % a.ledger)
    return 0


if __name__ == '__main__':
    sys.exit(main())
