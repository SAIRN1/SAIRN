"""Do the rows the cleanup files exist to delete still EXIST?

WHY. Live write-path verification on this platform leaves rows the product
cannot remove -- there is no delete path outside the sc_* family and
service_role's DELETE was revoked on every other table -- so each verification
run ends with a hand-written `delete from ...` file. There are more than fifteen
of them across eleven apps and the count keeps moving.

EVERY ONE OF THEM CARRIES `NOT RUN`, AND THAT LABEL IS A CLAIM ABOUT THE FILE,
NOT ABOUT THE DATABASE. It has already been wrong once: the open-work index
records `RF-VERIFY-PROBE-20260825` in dnt_referrals as NOT RUN while a live read
under the same licence returned nothing -- the row was already gone. A queue of
fifteen SQL files, an unknown number of which are moot, is a queue nobody can
prioritise and a set of labels nobody can trust.

WHAT IT DOES. Reads each cleanup file, pulls out every
`delete from public.<table> ... license_hash = '<sha256>' ... <col> = '<id>'`,
maps the hash back to a licence key by hashing the keys the repo actually
declares (derived, never guessed), and asks the live endpoint whether those ids
are still there.

READ ONLY. Every request is action:'read'. It never deletes and never writes;
it says which files still have something to do.

WHAT IT CANNOT SEE, said here rather than discovered later:
  * MOST RESOURCES NEED A SIGNED-IN EMPLOYEE SESSION, not just the licence key,
    and this tool has no credentials -- 28 of the statements it can otherwise
    fully resolve come back NO_SESSION. That is the dominant ceiling as of
    2026-09-10 and it is not a defect in the parsing: the file was read, the
    licence resolved, the table resolved to its app, and the API declined. A
    login path (the RF_EMP/RF_PIN convention in tools/rf_roundtrip_probe.py)
    would lift it for licences whose credentials we hold; it would not help for
    a real customer licence like RF-PINNACLE-2026, whose PIN we neither have nor
    should.
  * A table that is not a REGISTERED RESOURCE cannot be read through
    api/sd-data.js at all -- the *_employee_auth tables are the big group. Those
    come back COULD NOT READ, which is not a pass.
  * A licence_hash whose key is not declared in sql/*license*.sql is
    unresolvable, and is reported rather than skipped.
  * A delete keyed on something other than a literal id -- a LIKE pattern, a
    date range, a bare licence-wide delete -- has no id set to check, so the
    file is reported as UNCHECKABLE SHAPE. It may still have work to do.
  * A delete whose licence arrives through a plpgsql variable (`lh text := ...`
    inside a DO block, then `license_hash = lh`) has no licence literal in the
    WHERE and is UNCHECKABLE SHAPE. Every such file found so far targets a
    *_employee_auth table, which is unreadable anyway, so resolving the variable
    would not turn any of them into an answer.
  * A row present under a DIFFERENT licence than the file names is invisible,
    because a read is scoped to the licence used.

NOTHING IS CLEAN BY SUBTRACTION. The CLEAN count is the number of files that
returned an actual CLEAN verdict from an actual read -- it is never computed as
"everything left over". The first version of this file did compute it that way,
and reported three files as CLEAN in which no delete statement had been parsed
and no read had been performed: a false clean inside the tool written to catch
false labels. A file nothing could be checked in is COULD NOT READ.

Usage:
    python tools/cleanup_residue_check.py
    python tools/cleanup_residue_check.py --json
    python tools/cleanup_residue_check.py sql/one_file.sql

Exit 0 when every checkable file is clean, 1 when residue is present, 2 when
something could not be read -- which is not a pass and says so.
"""
import glob
import hashlib
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import sairn_http  # noqa: E402

URL = 'https://sairn.vercel.app/api/sd-data'

# A statement, not a line: these files wrap the WHERE across several lines and a
# line-based read would take the table from one delete and the id from the next.
DELETE_RE = re.compile(r'delete\s+from\s+public\.(\w+)(.*?);', re.S | re.I)
HASH_RE = re.compile(r"license_hash\s*=\s*'([0-9a-f]{64})'", re.I)
# The SAME scoping, written the other way. These files far more often hash the
# key in SQL than paste a digest, and reading only the literal form missed every
# one of them -- 26 of 29 files were unresolvable on the first run.
DIGEST_RE = re.compile(
    r"license_hash\s*=\s*encode\s*\(\s*digest\s*\(\s*'([^']+)'\s*,\s*'sha256'", re.I)
EQ_RE = re.compile(r"and\s+(\w+)\s*=\s*'([^']+)'", re.I)
IN_RE = re.compile(r"and\s+(\w+)\s+in\s*\(([^)]*)\)", re.I)


def declared_licences():
    """sha256(key) -> key, for every licence key that appears anywhere in sql/.

    DERIVED, NEVER GUESSED. The cleanup files carry the key in a comment, but a
    comment is prose; the hash in the WHERE clause is what the database sees, so
    the mapping is built by hashing every key the repo mentions and matching the
    digest. A wrong guess cannot survive that -- the hash either matches or it
    does not.

    WIDENED ON THE FIRST RUN, and the miss is why. The first version read only
    `values (...)` rows out of sql/*license*.sql and resolved NEITHER of the two
    hashes these files actually use: SC-PINNACLE-2026 is declared in
    demo_owner_credentials_2026-09-03.sql, not in a file with "license" in its
    name, and RF-PINNACLE-2026 likewise. 18 keys found that way, 0 of the hashes
    resolved; by shape across all of sql/, 100 keys and both resolve. Matching on
    the digest is what makes the wider net safe -- a string that looks like a key
    and is not simply never matches anything.
    """
    keys = set()
    for f in glob.glob(os.path.join(REPO, 'sql', '*.sql')):
        src = open(f, encoding='utf-8', errors='replace').read()
        keys |= set(re.findall(r"'([A-Z]{2,6}-[A-Z0-9-]{3,})'", src))
    return {hashlib.sha256(k.encode()).hexdigest(): k for k in keys}


def _resource_list(src):
    """The names inside a registry file's `resources: [ ... ]`, comments stripped."""
    src = '\n'.join(l for l in src.split('\n') if not l.strip().startswith('//'))
    m = re.search(r'resources\s*:\s*\[', src)
    if not m:
        return []
    i, depth = src.index('[', m.start()), 0
    for j in range(i, len(src)):
        if src[j] == '[':
            depth += 1
        elif src[j] == ']':
            depth -= 1
            if depth == 0:
                break
    return re.findall(r"'([\w.-]+)'", src[i:j + 1])


def resource_apps():
    """table -> [app ...], read from api/_resources/*.js.

    REPLACES resolving the app from the licence's seed row, which failed for
    every roofing file: RF-PINNACLE-2026 is a real customer licence provisioned
    outside this repo, so no `values (...)` row for it exists anywhere in sql/
    and the lookup returned "an unknown app" for nine files. The table is the
    better key -- it is the registry the API itself dispatches on, so a table
    that resolves here is registered BY CONSTRUCTION and one that does not is
    genuinely unreadable through sd-data.js.

    A list rather than a single app because `shared.js` exists; a table carried
    by more than one registry is reported rather than silently resolved to
    whichever file happened to be read first.
    """
    out = {}
    for f in sorted(glob.glob(os.path.join(REPO, 'api', '_resources', '*.js'))):
        if f.endswith('.test.js') or os.path.basename(f) == 'index.js':
            continue
        src = open(f, encoding='utf-8', errors='replace').read()
        m = re.search(r"app\s*:\s*'([\w-]+)'", src)
        app = m.group(1) if m else os.path.basename(f)[:-3]
        for t in _resource_list(src):
            out.setdefault(t, [])
            if app not in out[t]:
                out[t].append(app)
    return out


def targets(path):
    """[(table, license_hash, license_key, {id values}) ...] for one cleanup file.

    At most one of license_hash / license_key is set -- the two are the same
    scoping written differently, and whichever the file used is the one returned.
    """
    src = open(path, encoding='utf-8', errors='replace').read()
    # Comments carry example DELETEs and prose; strip them or a commented-out
    # statement is read as a real one.
    src = '\n'.join(l for l in src.split('\n') if not l.strip().startswith('--'))
    out = []
    for table, where in DELETE_RE.findall(src):
        h = HASH_RE.search(where)
        d = DIGEST_RE.search(where)
        ids = set()
        for col, val in EQ_RE.findall(where):
            if col.lower() != 'license_hash':
                ids.add(val)
        for _col, vals in IN_RE.findall(where):
            ids |= set(re.findall(r"'([^']+)'", vals))
        out.append((table, h.group(1) if h else None,
                    d.group(1) if d else None, ids))
    return out


def read_rows(resource, key, app):
    body = json.dumps({'action': 'read', 'resource': resource,
                       'app_id': app, 'payload': {}}).encode('utf-8')
    try:
        r = sairn_http.fetch(URL, method='POST', data=body, headers={
            'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key})
        d = json.loads(r.body.decode('utf-8', 'replace'))
    except sairn_http.Challenged:
        return None, 'CHALLENGED'
    except Exception as e:
        try:
            d = json.loads(e.read().decode('utf-8', 'replace'))
        except Exception:
            return None, str(e)[:60]
        return None, (d.get('error') or {}).get('code') or 'refused'
    if not d.get('ok'):
        return None, (d.get('error') or {}).get('code') or 'not ok'
    return (d.get('data') or []), None


def main(argv):
    files = [a for a in argv[1:] if a.endswith('.sql')]
    if not files:
        files = sorted(glob.glob(os.path.join(REPO, 'sql', '*cleanup*.sql')))
        # Counted for what it DOES, not what it is named -- the index row makes
        # the same point about this file.
        extra = os.path.join(REPO, 'sql', 'sairnlaw_remove_probe_rule_2026-08-25.sql')
        if os.path.exists(extra):
            files.append(extra)

    lic = declared_licences()
    apps = resource_apps()
    report = []
    for f in files:
        name = os.path.basename(f)
        rows = targets(f)
        if not rows:
            # NOT clean. Nothing was parsed, so nothing was checked, and a file
            # nobody could check is exactly the label this tool exists to doubt.
            # Worth separating the two reasons: a file whose deletes are all
            # commented out is not runnable AS IT STANDS, which is a different
            # thing to do about it than a file this parser simply missed.
            why = ('every `delete from` in it is commented out -- proposed, not runnable'
                   if DELETE_RE.search(open(f, encoding='utf-8', errors='replace').read())
                   else 'no `delete from public.<table>` statement parsed at all')
            report.append((name, 'COULD NOT READ', [('NO DELETE FOUND', why)]))
            continue
        states = []
        for table, h, dkey, ids in rows:
            if h:
                key = lic.get(h)
                if not key:
                    states.append(('LICENCE UNKNOWN', '%s: hash %s... matches no declared key'
                                   % (table, h[:12])))
                    continue
            elif dkey:
                key = dkey
            else:
                states.append(('UNCHECKABLE SHAPE',
                               '%s: no literal licence in the WHERE' % table))
                continue
            if not ids:
                states.append(('UNCHECKABLE SHAPE', '%s: delete is not keyed on a literal id' % table))
                continue
            owners = apps.get(table)
            if not owners:
                states.append(('COULD NOT READ', '%s is not a registered resource for any app'
                               % table))
                continue
            if len(owners) > 1:
                states.append(('COULD NOT READ', '%s is registered by %d apps (%s) -- ambiguous'
                               % (table, len(owners), ', '.join(owners))))
                continue
            app = owners[0]
            data, err = read_rows(table, key, app)
            if err:
                if err == 'NO_SESSION':
                    err = ('reading it needs a signed-in employee session, not just the '
                           'licence key -- no credentials were supplied for %s' % app)
                states.append(('COULD NOT READ', '%s: %s' % (table, err)))
                continue
            present = set()
            for x in data:
                if isinstance(x, dict):
                    for v in x.values():
                        if isinstance(v, (str, int)) and str(v) in ids:
                            present.add(str(v))
            if present:
                states.append(('RESIDUE PRESENT', '%s: %d of %d target id(s) still there -- %s'
                               % (table, len(present), len(ids), ', '.join(sorted(present)[:4]))))
            else:
                states.append(('CLEAN', '%s: none of %d target id(s) present' % (table, len(ids))))
        # A file is CLEAN only if EVERY statement in it returned CLEAN. One
        # unreadable statement makes the whole file unanswered, not mostly-fine.
        worst = ('RESIDUE PRESENT' if any(s == 'RESIDUE PRESENT' for s, _ in states)
                 else 'CLEAN' if states and all(s == 'CLEAN' for s, _ in states)
                 else 'COULD NOT READ')
        report.append((name, worst, states))

    # Counted from the verdicts themselves. Never by subtraction -- that is what
    # printed three unchecked files as CLEAN.
    residue = sum(1 for _, w, _ in report if w == 'RESIDUE PRESENT')
    clean = sum(1 for _, w, _ in report if w == 'CLEAN')
    unread = sum(1 for _, w, _ in report if w == 'COULD NOT READ')

    if '--json' in argv:
        print(json.dumps([{'file': n, 'state': w, 'detail': [list(x) for x in d]}
                          for n, w, d in report], indent=1))
    else:
        print('CLEANUP RESIDUE -- READ ONLY, nothing was written')
        print('  files seen    : %d' % len(report))
        print('  RESIDUE       : %d  (these still have work to do)' % residue)
        print('  COULD NOT READ: %d  (NOT a pass -- nothing was answered here)' % unread)
        print('  CLEAN         : %d  (read live; the delete would match nothing)' % clean)
        for n, w, d in report:
            if w == 'CLEAN':
                continue
            print('\n  %-52s %s' % (n, w))
            for state, why in d:
                print('      %-18s %s' % (state, why))
        print('\n  CLEAN files, nothing to run:')
        for n, w, _ in report:
            if w == 'CLEAN':
                print('      %s' % n)
        print('\nA CLEAN result means the ids this file names are not present under the')
        print('licence it names. It does NOT mean the file was run -- the rows may never')
        print('have been written, or a previous run removed them. Either way there is')
        print('nothing left for it to delete.')

    if unread:
        return 2
    return 1 if residue else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
