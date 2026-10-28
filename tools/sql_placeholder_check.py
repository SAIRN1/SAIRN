# OWNER: hank
"""Does a SQL file that is about to ship still contain an unsubstituted placeholder?

WHY THIS EXISTS (hank b58 -> b59, 2026-10-28)
---------------------------------------------
sql/alf-audit-owner-recovery.sql shipped with __PIN_HASH__ / __PIN_SALT__ in its
INSERT. Michael ran it for real and it aborted on its own guard (P0001, nothing
committed). The fail-closed guard did its job, but the file should never have
shipped that way. Both checks that "passed" were looking at something else:

  * the rehearsal ran a script-made COPY with dummy hex substituted in, so the
    SQL that passed was never the SQL that shipped; and
  * tools/employee_auth_guard_check.py is a marker lint for the recoverability
    guard, and it cannot see an unreplaced token.

So this reads the LITERAL BLOB at the pushed tip (`git show <ref>:<path>`), not
the working tree and not a regenerated copy. It looks at EXECUTABLE text only:
comments are stripped by a small SQL lexer, because 9 of the 307 files in sql/
on 2026-10-28 explain a placeholder in a comment (`where license_hash =
'<hash>'` as a worked example), and a gate that refused those would be talked
past within the day.

WHAT COUNTS AS A PLACEHOLDER, IN EXECUTABLE TEXT
------------------------------------------------
  dunder      __UPPER_SNAKE__                    (the b58 shape)
  mustache    {{ name }}
  marker      REPLACE_ME*, CHANGEME, CHANGE_ME, PASTE_HERE, PASTE_*_HERE
  angle       a quoted '<...>' whose words name a value an operator supplies:
              hash, key, licence/license, id, uuid, sha, pin, salt, token,
              password, secret, paste, replace, email. NOT '<no row>', a
              display default in sql/verify_sen_audit_2026.sql that is
              correct as written.

DECLARED OPERATOR INPUT IS ALLOWED, AND IS NAMED, NOT HIDDEN
-------------------------------------------------------------
Some values must never be committed. sql/backup_reader_role.sql's role
password is one: the file carries 'REPLACE_ME_BEFORE_RUNNING' and refuses to
run while it is still there. Writing a real password into a tracked file
would be the actual defect. A file declares that with a comment line:

    -- sql-placeholder-lint: operator-input <TOKEN> -- <why, 20+ characters>

The declared token is then reported as NOT RUN-READY rather than refused. An
undeclared token, or a declaration with no reason, still fails.

EXIT CODES -- COULD NOT RUN IS ITS OWN STATE, AND THE GATE DENIES ON IT
-----------------------------------------------------------------------
  0  every file checked is free of undeclared placeholders
  1  at least one file ships an undeclared placeholder (or a bare declaration)
  2  COULD NOT RUN: no git, an unresolvable ref, a path that is neither at the
     ref nor deleted on the way to it, an undecodable file, or an unterminated
     string, comment or dollar-quote the lexer cannot get past.
     A check that could not read the file has not cleared it.

Usage:
  python tools/sql_placeholder_check.py --ref <sha> sql/a.sql [sql/b.sql ...]
  python tools/sql_placeholder_check.py --ref HEAD --all
  python tools/sql_placeholder_check.py --fixtures
"""
import os
import re
import subprocess
import sys

CRITERIA_VERSION = '2026-10-28.1'

DUNDER = re.compile(r'__[A-Z][A-Z0-9_]*__')
MUSTACHE = re.compile(r'\{\{\s*[A-Za-z_][A-Za-z0-9_. ]*\}\}')
MARKER = re.compile(r'\b(?:REPLACE_ME\w*|CHANGE_?ME|PASTE_HERE|PASTE_[A-Z0-9_]+_HERE)\b')
ANGLE_WORDS = re.compile(
    r'\b(?:hash|key|licen[cs]e|id|uuid|sha(?:256)?|pin|salt|token|password|'
    r'secret|paste|replace|email)\b', re.I)
DECL = re.compile(r'^\s*--\s*sql-placeholder-lint:\s*operator-input\s+(\S+)\s*(?:--\s*(.*))?$')


class CouldNotRun(Exception):
    pass


def lex(src):
    """Split SQL into (kind, text, line) runs: 'code', 'string', 'comment'.

    Dollar-quoted bodies ($$ ... $$, $tag$ ... $tag$) are lexed as code, since
    a plpgsql body is code with the same comment and string syntax. The
    delimiters themselves are dropped. Raises CouldNotRun on anything left open.
    """
    out, i, n, line = [], 0, len(src), 1
    buf, buf_line = [], 1

    def flush(kind='code'):
        nonlocal buf, buf_line
        if buf:
            out.append((kind, ''.join(buf), buf_line))
        buf, buf_line = [], line

    open_dollar = []
    while i < n:
        c = src[i]
        if c == '-' and src.startswith('--', i):
            flush()
            j = src.find('\n', i)
            j = n if j == -1 else j
            out.append(('comment', src[i:j], line))
            i = j
            continue
        if c == '/' and src.startswith('/*', i):
            flush()
            j = src.find('*/', i + 2)
            if j == -1:
                raise CouldNotRun('unterminated /* comment starting on line %d' % line)
            body = src[i:j + 2]
            out.append(('comment', body, line))
            line += body.count('\n')
            i = j + 2
            buf_line = line
            continue
        if c == "'":
            flush()
            start, j = line, i + 1
            while True:
                k = src.find("'", j)
                if k == -1:
                    raise CouldNotRun("unterminated ' string starting on line %d" % start)
                if src.startswith("''", k):
                    j = k + 2
                    continue
                break
            body = src[i:k + 1]
            out.append(('string', body, start))
            line += body.count('\n')
            i = k + 1
            buf_line = line
            continue
        if c == '$':
            m = re.match(r'\$([A-Za-z_][A-Za-z0-9_]*)?\$', src[i:])
            if m:
                tag = m.group(0)
                if open_dollar and open_dollar[-1] == tag:
                    open_dollar.pop()
                else:
                    open_dollar.append(tag)
                flush()
                i += len(tag)
                continue
        if c == '\n':
            line += 1
        buf.append(c)
        i += 1
    flush()
    if open_dollar:
        raise CouldNotRun('unterminated dollar-quote %s' % open_dollar[-1])
    return out


def scan(src):
    """Return (findings, declared, bad_declarations) for one file's text."""
    declared, bad_decl = {}, []
    for ln, raw in enumerate(src.splitlines(), 1):
        m = DECL.match(raw)
        if m:
            why = (m.group(2) or '').strip()
            if len(why) < 20:
                bad_decl.append((ln, m.group(1)))
            else:
                declared[m.group(1)] = why
    findings = []
    for kind, text, ln in lex(src):
        if kind == 'comment':
            continue
        hits = []
        if kind == 'string':
            inner = text[1:-1]
            if inner.startswith('<') and inner.endswith('>') and ANGLE_WORDS.search(inner):
                hits.append(('angle', text))
        for name, rx in (('dunder', DUNDER), ('mustache', MUSTACHE), ('marker', MARKER)):
            for m in rx.finditer(text):
                hits.append((name, m.group(0)))
        for name, tok in hits:
            bare = tok.strip("'")
            ok = any(d == bare or d == tok or d in tok for d in declared)
            findings.append({'line': ln + text[:max(text.find(tok), 0)].count('\n'),
                             'shape': name, 'token': tok, 'declared': ok})
    return findings, declared, bad_decl


def git(repo, *a):
    try:
        p = subprocess.run(['git'] + list(a), cwd=repo, capture_output=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise CouldNotRun('git could not be run: %s' % e)
    return p


def read_at(repo, ref, path):
    """Return the blob text, or None when the path was deleted on the way to ref."""
    p = git(repo, 'show', '%s:%s' % (ref, path))
    if p.returncode == 0:
        try:
            return p.stdout.decode('utf-8')
        except UnicodeDecodeError:
            raise CouldNotRun('%s at %s is not UTF-8' % (path, ref))
    hist = git(repo, 'log', '-1', '--format=%H', ref, '--', path)
    if hist.returncode == 0 and hist.stdout.strip():
        return None
    raise CouldNotRun('%s is not at %s and never was -- a path that names nothing is not a pass' % (path, ref))


def check(repo, ref, paths):
    rc = git(repo, 'rev-parse', '--verify', '--quiet', ref + '^{commit}')
    if rc.returncode != 0:
        raise CouldNotRun('ref %r does not resolve to a commit' % ref)
    sha = rc.stdout.decode().strip()
    bad, notes, checked = [], [], 0
    for path in paths:
        src = read_at(repo, sha, path)
        if src is None:
            notes.append('  deleted at %s, nothing to check: %s' % (sha[:9], path))
            continue
        try:
            findings, declared, bad_decl = scan(src)
        except CouldNotRun as e:
            raise CouldNotRun('%s: %s' % (path, e))
        checked += 1
        for ln, tok in bad_decl:
            bad.append('  %s:%d  operator-input declaration for %s has no reason (20+ characters after --)' % (path, ln, tok))
        for f in findings:
            if f['declared']:
                notes.append('  NOT RUN-READY (declared operator input): %s:%d  %s %s' % (path, f['line'], f['shape'], f['token']))
            else:
                bad.append('  %s:%d  %s placeholder %s' % (path, f['line'], f['shape'], f['token']))
    return sha, checked, bad, notes


FIXTURES = [
    # (name, sql, expected exit: 0 clean / 1 finding / 2 could-not-run)
    ('the b58 shape: dunder tokens in an INSERT', "insert into t values ('__PIN_HASH__', '__PIN_SALT__');", 1),
    ('the b58 shape inside a do-block guard', "do $$ begin if '__PIN_HASH__' !~ 'x' then raise exception 'no'; end if; end $$;", 1),
    ('a dunder token in a COMMENT only is not executable', "-- paste over __PIN_HASH__ below\nselect 1;", 0),
    ('a block comment hides it too', "/* __PIN_HASH__ */ select 1;", 0),
    ('real hex is clean', "insert into t values ('e529b565c8fc', 'f472b006');", 0),
    ('mustache in code', "select * from t where id = '{{ licence_hash }}';", 1),
    ('REPLACE_ME marker in code', "do $$ declare p text := 'REPLACE_ME_BEFORE_RUNNING'; begin end $$;", 1),
    ('...declared as operator input WITH a reason is allowed',
     "-- sql-placeholder-lint: operator-input REPLACE_ME_BEFORE_RUNNING -- a role password must never be committed\n"
     "do $$ declare p text := 'REPLACE_ME_BEFORE_RUNNING'; begin end $$;", 0),
    ('...declared with NO reason still fails',
     "-- sql-placeholder-lint: operator-input REPLACE_ME_BEFORE_RUNNING\n"
     "do $$ declare p text := 'REPLACE_ME_BEFORE_RUNNING'; begin end $$;", 1),
    ('a declaration covers ONLY its own token',
     "-- sql-placeholder-lint: operator-input REPLACE_ME -- a role password must never be committed\n"
     "insert into t values ('__PIN_HASH__');", 1),
    ("an operator angle placeholder: '<the 64-char hash>'", "select 1 from t where h = '<the 64-char hash>';", 1),
    ("'<A-REAL-LICENCE-KEY>' in code", "select digest('<A-REAL-LICENCE-KEY>', 'sha256');", 1),
    ("'<no row>' is a display default, correct as written", "select coalesce(x, '<no row>') from t;", 0),
    ("'<hash>' in a comment is a worked example", "--   where license_hash = '<hash>'\nselect 1;", 0),
    ("a doubled quote inside a string does not end it", "select 'it''s __NOT_A_COMMENT__';", 1),
    ('an unterminated string is COULD NOT RUN, not clean', "select 'oops;", 2),
    ('an unterminated block comment is COULD NOT RUN', "/* never closed\nselect 1;", 2),
    ('an unterminated dollar-quote is COULD NOT RUN', "do $$ begin select 1;", 2),
    ('a tagged dollar-quote nests inside $$', "do $$ begin execute $q$select '__X_Y__'$q$; end $$;", 1),
    ('lower-case dunder is not a placeholder (no false positive on __proto__-like names)', "select '__proto__';", 0),
]


def run_fixtures():
    bad = 0
    for name, sql, want in FIXTURES:
        try:
            findings, _d, bad_decl = scan(sql)
            got = 1 if (bad_decl or any(not f['declared'] for f in findings)) else 0
        except CouldNotRun:
            got = 2
        ok = got == want
        bad += not ok
        print('  %s  %-80s want %d got %d' % ('ok  ' if ok else 'FAIL', name[:80], want, got))
    print('%d/%d fixtures classify correctly -- criteria %s' % (len(FIXTURES) - bad, len(FIXTURES), CRITERIA_VERSION))
    return 0 if bad == 0 else 1


def main(argv):
    if '--fixtures' in argv:
        return run_fixtures()
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ref = 'HEAD'
    if '--ref' in argv:
        i = argv.index('--ref')
        if i + 1 >= len(argv):
            print('COULD NOT RUN: --ref needs a value'); return 2
        ref = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    print('SQL PLACEHOLDER CHECK -- criteria %s' % CRITERIA_VERSION)
    try:
        if '--all' in argv:
            p = git(repo, 'ls-tree', '-r', '--name-only', ref, '--', 'sql/')
            if p.returncode != 0:
                raise CouldNotRun('git ls-tree failed at %s' % ref)
            paths = [x for x in p.stdout.decode().splitlines() if x.endswith('.sql')]
            if not paths:
                raise CouldNotRun('no sql/*.sql at %s -- an empty population is not a clean one' % ref)
        else:
            paths = [a.replace('\\', '/') for a in argv if not a.startswith('--')]
            if not paths:
                print('COULD NOT RUN: no paths given (pass sql/<file>.sql ..., or --all)'); return 2
        sha, checked, bad, notes = check(repo, ref, paths)
    except CouldNotRun as e:
        print('COULD NOT RUN: %s' % e)
        print('A check that could not read the file has not cleared it.')
        return 2
    print('  read %d file(s) as committed at %s (the blob, not the working tree)' % (checked, sha[:9]))
    for x in notes:
        print(x)
    if bad:
        print('FAIL: %d unsubstituted placeholder(s) would ship:' % len(bad))
        for x in bad:
            print(x)
        print('Substitute the real value into the file itself. If the value must never be committed (a password),')
        print("declare it:  -- sql-placeholder-lint: operator-input <TOKEN> -- <why>   and say NOT RUN-READY in the handoff.")
        return 1
    print('OK -- no undeclared placeholder in executable SQL.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
