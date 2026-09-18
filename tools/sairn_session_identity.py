"""sairn_session_identity.py -- who is this clone, from a marker rather than a name.

    python tools/sairn_session_identity.py                 # print it
    python tools/sairn_session_identity.py --provision cc   # write it, once
    python tools/sairn_session_identity.py --self-check

Exit 0 when the identity is known, 2 when it is not -- never a guess.

── THE DEFECT THIS CLOSES (hover finding #258, HIGH) ───────────────────────
`session_name()` existed TWICE, byte-for-byte, in tools/tier_a_review_gate.py
and tools/sairn_claim.py, and both derived identity from the CLONE DIRECTORY:

    base = os.path.basename(REPO)
    m = re.match(r'^SAIRN-(.+)$', base, re.I)
    return (m.group(1) if m else base).lower()

So "who am I" was a property of a folder name. The review gate refuses a record
"whose reviewer is its own author" -- and that refusal was keyed on a string
anybody could change with a rename. A clone renamed `SAIRN-cody` would discharge
its own Tier A obligation and the gate would report an independent review.

THE SAME STRING ALSO DECIDES WHO HOLDS A CLAIM, so a rename silently reassigns
work in the other direction too.

── WHAT THIS CONTROL IS, AND WHAT IT HONESTLY IS NOT ───────────────────────
The identity now comes from a marker file inside `.git/`, written once at
provisioning. That is the convention `tools/hover_auditor_scope_gate.py` already
uses for the auditor clone, adopted rather than invented.

`.git/` is the right home for three reasons: it is NOT TRACKED, so the marker
cannot travel in a commit and cannot be reviewed into the wrong clone; it is
PER-CLONE, so five working copies of one repository have five identities; and it
SURVIVES A RENAME, which is the defect.

**IT IS NOT A CRYPTOGRAPHIC CONTROL AND MUST NOT BE DESCRIBED AS ONE.** Any
process that can rename the directory can also write the marker. What changes is
the BAR: identity stops being a side effect of a folder name -- something that
changes by accident, by a move, by a checkout into a differently-named
directory -- and becomes a deliberate act with a file to point at. The threat it
genuinely closes is DRIFT AND ACCIDENT. A hostile agent with filesystem access
is not in scope and no file-based marker could be.

── FAIL CLOSED, AND WHAT THAT COSTS ────────────────────────────────────────
A missing marker RAISES. It does not fall back to the directory name, because
a fallback would mean the spoofable path is still live and nothing would ever
tell you which one answered -- the check would report a pass it never performed
(PR 1.11).

THE COST IS REAL AND IS NOT HIDDEN: every clone must be provisioned once before
the claim tool and the review gate will run. That is one command per clone and
the error message is that command. It is the correct trade -- an identity the
tools cannot establish must stop them, not be guessed.
"""
import argparse
import io
import os
import re
import subprocess
import sys

MARKER = 'sairn-session'          # lives in .git/, so it is per-clone
VALID = re.compile(r'^[a-z][a-z0-9_-]{1,31}$')

EXIT_CLEAN = 0
EXIT_COULD_NOT_RUN = 2


class NoIdentity(Exception):
    """The identity could not be established. Never folded into a default."""


def _git_dir(start=None):
    """Absolute path to this clone's .git directory, or None."""
    cwd = start or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        r = subprocess.run(['git', 'rev-parse', '--git-dir'], cwd=cwd,
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace', timeout=20)
    except Exception:                                            # noqa: BLE001
        return None
    if r.returncode != 0:
        return None
    p = r.stdout.strip()
    if not p:
        return None
    return p if os.path.isabs(p) else os.path.abspath(os.path.join(cwd, p))


def marker_path(start=None):
    g = _git_dir(start)
    return os.path.join(g, MARKER) if g else None


def session_name(start=None):
    """This clone's session name, from the marker. RAISES when it is absent.

    The one implementation. tools/sairn_claim.py and
    tools/tier_a_review_gate.py both call this rather than carrying a copy --
    two answers to "who am I" would make the self-review refusal meaningless,
    and they already had two.
    """
    p = marker_path(start)
    if not p:
        raise NoIdentity(
            'not inside a git clone (git rev-parse --git-dir failed), so there '
            'is no per-clone marker to read and no identity to report')
    if not os.path.isfile(p):
        raise NoIdentity(
            'THIS CLONE IS NOT PROVISIONED. %s does not exist, and the session '
            'name is NOT guessed from the directory -- that is the defect this '
            'replaced (hover #258: a rename let a clone discharge its own Tier '
            'A obligation). Provision it once:\n'
            '    python tools/sairn_session_identity.py --provision <name>\n'
            'where <name> is one of the session names already used by this '
            'platform.' % p)
    try:
        raw = io.open(p, encoding='utf-8').read().strip()
    except OSError as e:
        raise NoIdentity('%s exists but could not be read (%s)' % (p, e))
    if not VALID.match(raw):
        raise NoIdentity(
            '%s holds %r, which is not a valid session name. A marker that is '
            'present but unreadable is a third state and is not an identity.'
            % (p, raw[:40]))
    return raw


def provision(name, start=None, force=False):
    name = (name or '').strip().lower()
    if not VALID.match(name):
        raise NoIdentity('%r is not a valid session name (lower case, 2-32 '
                         'chars, [a-z0-9_-], starting with a letter)' % name)
    p = marker_path(start)
    if not p:
        raise NoIdentity('not inside a git clone, so there is nowhere to write '
                         'the marker')
    if os.path.isfile(p) and not force:
        existing = io.open(p, encoding='utf-8').read().strip()
        if existing == name:
            return p, existing, False
        raise NoIdentity(
            'this clone is ALREADY provisioned as %r and you asked for %r. '
            'Re-provisioning changes who every future claim and every future '
            'review is attributed to, so it is refused rather than done '
            'quietly. Pass --force if that is genuinely what you mean.'
            % (existing, name))
    io.open(p, 'w', encoding='utf-8', newline='\n').write(name + '\n')
    return p, name, True


# ── self-check: the three arms the finding asked for ────────────────────────

def self_check():
    import tempfile
    import shutil
    ok = True

    def ck(label, cond, detail=''):
        nonlocal ok
        print('  %-4s %s%s' % ('ok' if cond else 'FAIL', label,
                               '' if cond else '   <- %s' % (detail,)))
        if not cond:
            ok = False

    print('SESSION IDENTITY -- self-check (hover finding #258)')
    tmp = tempfile.mkdtemp(prefix='sairn_ident_')
    try:
        # A throwaway repo named after NOBODY, so a directory-derived
        # implementation could not accidentally produce the right answer.
        work = os.path.join(tmp, 'totally-unrelated-name')
        os.makedirs(work)
        subprocess.run(['git', 'init', '-q'], cwd=work, capture_output=True)

        print('\n1. MISSING MARKER FAILS CLOSED -- it does not fall back to the '
              'directory name')
        raised = False
        try:
            session_name(work)
        except NoIdentity:
            raised = True
        ck('an unprovisioned clone RAISES rather than guessing', raised)

        print('\n2. THE PLANTED VALUE IS ACTUALLY USED -- proving the marker is '
              'the source and the directory is not')
        provision('cody', work)
        ck("a clone in a directory called 'totally-unrelated-name' reports "
           "'cody'", session_name(work) == 'cody', session_name(work))
        # The directory-derived implementation this replaced, run on the same
        # path, for the contrast. If these ever agreed the arm would prove
        # nothing.
        legacy = os.path.basename(work)
        legacy = (re.match(r'^SAIRN-(.+)$', legacy, re.I) or [None, legacy])
        legacy = (legacy[1] if isinstance(legacy, list) else legacy.group(1)).lower()
        ck('CONTROL: the OLD directory-derived answer differs -- %r vs %r'
           % (legacy, 'cody'), legacy != 'cody')

        print('\n3. RENAME SURVIVES -- the defect itself')
        renamed = os.path.join(tmp, 'SAIRN-hank')
        shutil.move(work, renamed)
        ck("renamed to 'SAIRN-hank', the identity is still 'cody'",
           session_name(renamed) == 'cody', session_name(renamed))
        ck('CONTROL: the old implementation WOULD have said hank, which is the '
           'spoof', 'hank' == re.match(r'^SAIRN-(.+)$',
                                       os.path.basename(renamed), re.I)
           .group(1).lower())

        print('\n4. RE-PROVISIONING IS REFUSED, not done quietly')
        refused = False
        try:
            provision('cc', renamed)
        except NoIdentity:
            refused = True
        ck('changing an existing identity requires --force', refused)
        ck('...and the identity is unchanged after the refusal',
           session_name(renamed) == 'cody')

        print('\n5. A PRESENT BUT UNREADABLE MARKER IS A THIRD STATE')
        io.open(os.path.join(_git_dir(renamed), MARKER), 'w',
                encoding='utf-8').write('NOT A VALID NAME!!\n')
        raised = False
        try:
            session_name(renamed)
        except NoIdentity:
            raised = True
        ck('a marker holding junk RAISES rather than returning it', raised)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print('\n' + ('  all arms pass' if ok else '  ARMS FAILED'))
    return EXIT_CLEAN if ok else EXIT_COULD_NOT_RUN


def main(argv=None):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('--provision', metavar='NAME', default=None)
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--self-check', dest='selfcheck', action='store_true')
    args = ap.parse_args(argv)
    if args.selfcheck:
        return self_check()
    try:
        if args.provision:
            p, name, wrote = provision(args.provision, force=args.force)
            print('%s %s as %r' % ('wrote' if wrote else 'already', p, name))
            return EXIT_CLEAN
        print(session_name())
        return EXIT_CLEAN
    except NoIdentity as e:
        sys.stderr.write('NO IDENTITY: %s\n' % e)
        return EXIT_COULD_NOT_RUN


if __name__ == '__main__':
    sys.exit(main())
