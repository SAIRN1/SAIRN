"""Is a known credential value still anywhere in any clone's object store?

Run:  python tools/credential_purge_check.py
      python tools/credential_purge_check.py --record     # write the dated result

── WHY A DATED RECORD, AND NOT JUST A VERDICT ──────────────────────────────
2026-09-28: a session purged a GitHub token from this clone, re-verified by
content hash, and reported ZERO. 2026-09-29: the same search found ONE
unreachable blob in the same clone.

The two readings cannot both be explained without knowing WHEN. And the evidence
that would have answered it -- the object's mtime and the reflog entry that kept
it alive -- was destroyed by the `reflog expire --expire-unreachable=now` and
`gc --prune=now` that fixed the problem. THE FIX AND THE FORENSICS ARE THE SAME
COMMAND, and the fix has to win.

So this writes `docs/credential-purge-log.json`: one dated line per run, per
clone, with the object COUNT it searched. Next time the question is asked, the
answer is "it was zero here, on this date, over this many objects" rather than
"somebody said zero once".

THE COUNT IS PART OF THE RECORD AND NOT DECORATION. A run that searched 5,596
objects and a run that searched 95,560 both report zero, and only one of them
means much -- the 2026-09-28 run and the 2026-09-29 run differed by a size
filter, and nothing recorded that either.

── NO VALUE, NO FRAGMENT, ANYWHERE ─────────────────────────────────────────
The subject is identified by the SHA-256 of its contents. Nothing prints the
value, a prefix of it, or a byte of a matching blob -- only object ids, counts
and names. The record file carries the hash of the hash's own subject file path,
never the secret.

── WHAT IT CANNOT SEE ──────────────────────────────────────────────────────
* A value that was rotated. It searches for what is on disk NOW; a token that
  has already been replaced leaves this check looking clean while the old one
  may still be live somewhere else.
* Any repository outside Documents/SAIRN*.
* A packfile on a remote. Unreachable-but-present here says nothing about origin,
  and the push gate is the thing that kept it off origin in the first place.
* WHEN a blob arrived, unless a previous dated record exists to bracket it --
  which is the entire reason this file exists.
"""
import argparse
import hashlib
import glob
import io
import json
import os
import subprocess
import sys

EXIT_CLEAN = 0
EXIT_FINDING = 1
EXIT_COULD_NOT_RUN = 2

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECORD = os.path.join(REPO, 'docs', 'credential-purge-log.json')
CLONE_GLOB = os.path.join(os.path.dirname(os.path.dirname(REPO)), 'Documents',
                          'SAIRN*')


def subject_files():
    """Local, untracked files whose contents are the thing being searched for.

    NEVER a list of secrets: a list of PATHS. If none exist, that is reported as
    COULD NOT RUN rather than as a clean sweep -- a search for nothing finds
    nothing, and the two are indistinguishable in the output.
    """
    out = []
    d = os.path.join(REPO, '.claude')
    if os.path.isdir(d):
        for f in sorted(os.listdir(d)):
            if f.startswith('github_pat') or 'token' in f or 'secret' in f:
                out.append(os.path.join(d, f))
    cred = os.path.join(REPO, '.demo-credentials.local.json')
    if os.path.isfile(cred):
        out.append(cred)
    return out


def digests(paths):
    """{sha256: path} for each subject. The value never leaves this function."""
    out = {}
    for p in paths:
        try:
            raw = io.open(p, 'rb').read().strip()
        except Exception:                                      # noqa: BLE001
            continue
        if raw:
            out[hashlib.sha256(raw).hexdigest()] = p
    return out


def scan_clone(clone, wanted, max_size):
    """(objects_searched, [(digest, object_id)]) or (None, None) if unreadable.

    EVERY BLOB, not only small ones, unless max_size is given. The 2026-09-29
    run used a 4096-byte filter and the 2026-09-28 run did not; neither recorded
    which, so the two counts were not comparable and the difference looked like
    a change in the world.
    """
    r = subprocess.run(['git', '-C', clone, 'cat-file', '--batch-all-objects',
                        '--batch-check=%(objectname) %(objecttype) %(objectsize)'],
                       capture_output=True, text=True, errors='replace')
    if r.returncode != 0:
        return None, None
    blobs = []
    for line in r.stdout.split(chr(10)):
        p = line.split()
        if len(p) == 3 and p[1] == 'blob':
            try:
                size = int(p[2])
            except ValueError:
                continue
            if max_size is None or size <= max_size:
                blobs.append(p[0])
    hits = []
    CH = 500
    for i in range(0, len(blobs), CH):
        chunk = blobs[i:i + CH]
        pr = subprocess.run(['git', '-C', clone, 'cat-file', '--batch'],
                            input=(chr(10).join(chunk) + chr(10)).encode(),
                            capture_output=True)
        out, pos = pr.stdout, 0
        for name in chunk:
            nl = out.find(b'\n', pos)
            if nl < 0:
                break
            hdr = out[pos:nl].split()
            if len(hdr) < 3:
                break
            try:
                size = int(hdr[2])
            except ValueError:
                break
            body = out[nl + 1:nl + 1 + size]
            d = hashlib.sha256(body.strip()).hexdigest()
            if d in wanted:
                hits.append((d, name))
            pos = nl + 1 + size + 1
    return len(blobs), hits


def main(argv=None):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('--record', action='store_true',
                    help='append the dated result to docs/credential-purge-log.json')
    ap.add_argument('--max-size', type=int, default=None,
                    help='only blobs at or below this size; DEFAULT IS EVERY BLOB')
    ap.add_argument('--asof', default=None,
                    help='the date to stamp the record with (YYYY-MM-DD). '
                         'REQUIRED with --record: this tool does not read the '
                         'clock, so a record can never be stamped with a date '
                         'nobody chose.')
    args = ap.parse_args(argv)

    subjects = subject_files()
    if not subjects:
        sys.stderr.write(
            'COULD NOT RUN: no local credential file was found to search FOR.\n'
            'A search for nothing finds nothing, and that is indistinguishable '
            'from a clean object store in the output -- so this refuses rather '
            'than reporting zero.\n')
        return EXIT_COULD_NOT_RUN
    wanted = digests(subjects)
    if not wanted:
        sys.stderr.write('COULD NOT RUN: every candidate file was empty or '
                         'unreadable.\n')
        return EXIT_COULD_NOT_RUN

    clones = []
    for c in sorted(glob.glob(CLONE_GLOB)):
        if os.path.isdir(os.path.join(c, '.git')):
            clones.append(c)
    if not clones:
        sys.stderr.write('COULD NOT RUN: no clone matched %s.\n' % CLONE_GLOB)
        return EXIT_COULD_NOT_RUN

    print('CREDENTIAL PURGE CHECK')
    print('  subjects searched for : %d local file(s), identified by SHA-256 of '
          'their contents' % len(wanted))
    print('  size filter           : %s'
          % ('EVERY blob' if args.max_size is None
             else 'blobs <= %d bytes' % args.max_size))
    print()
    rows, total, findings, unreadable = [], 0, [], []
    for c in clones:
        n, hits = scan_clone(c, wanted, args.max_size)
        name = os.path.basename(c)
        if n is None:
            unreadable.append(name)
            print('  %-30s COULD NOT READ its object store' % name)
            continue
        total += n
        rows.append({'clone': name, 'objects': n, 'hits': len(hits)})
        print('  %-30s %7d blob(s)   HITS: %d' % (name, n, len(hits)))
        for _, oid in hits:
            findings.append('%s %s' % (name, oid))
            print('       object %s  (id only -- no value, no fragment)' % oid[:12])
    print()
    print('  TOTAL blobs searched: %d across %d clone(s)' % (total, len(rows)))

    if args.record:
        if not args.asof:
            sys.stderr.write(
                'COULD NOT RUN: --record needs --asof YYYY-MM-DD. This tool does '
                'not read the clock, so a dated record can never carry a date '
                'nobody chose -- the whole point of the log is that the date is '
                'trustworthy.\n')
            return EXIT_COULD_NOT_RUN
        try:
            log = json.load(io.open(RECORD, encoding='utf-8'))
        except Exception:                                      # noqa: BLE001
            log = {'note': 'One dated result per run. The OBJECT COUNT is part '
                           'of the record: two runs that both report zero over '
                           'very different universes are not the same evidence.',
                   'runs': []}
        log['runs'].append({
            'asof': args.asof,
            'size_filter': args.max_size,
            'subjects': len(wanted),
            'clones': rows,
            'total_objects': total,
            'hits': len(findings),
        })
        io.open(RECORD, 'w', encoding='utf-8', newline='').write(
            json.dumps(log, indent=2) + chr(10))
        print('  recorded in docs/credential-purge-log.json (%d run(s) on file)'
              % len(log['runs']))

    if unreadable:
        return EXIT_COULD_NOT_RUN
    return EXIT_FINDING if findings else EXIT_CLEAN


if __name__ == '__main__':
    sys.exit(main())
