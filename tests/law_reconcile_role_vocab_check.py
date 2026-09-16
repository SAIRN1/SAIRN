"""A role allow-list must not name a role the app does not have.

    python tests/law_reconcile_role_vocab_check.py

Exit 0  every key in LAW_RECONCILE_ROLES is a real SAIRNlaw role
Exit 1  a key names a role SAIRNlaw does not have
Exit 2  COULD NOT TELL -- the literal or the vocabulary could not be read, which
       is not a pass and is never folded into one

── THE DEFECT, WHICH SHIPPED AND WAS INVISIBLE FROM EVERY SIDE ────────────────
`api/sd-data.js` gated `law_trust_reconcile` on

    const LAW_RECONCILE_ROLES = { owner: true, admin: true };

SAIRNlaw's roles are owner / attorney / paralegal. There is no `admin` -- the
key came in by copy from SAIRNcode, whose vocabulary is admin/coder/biller/
auditor. `verifySessionToken` refuses any token whose role is outside the app's
own list, so that key could never be reached by a request: reconciliation was
OWNER-ONLY IN PRACTICE while the code read "management", the 403 said
"management", and `sairnlaw.html` offered the Trust Accounting tab to every
signed-in role.

AN ALLOW-LIST ENTRY THAT CAN NEVER MATCH IS INDISTINGUISHABLE, AT THE CALL
SITE, FROM A DELIBERATE EXCLUSION. It does not throw, it does not log, and it
does not fail a request. The gate just silently narrows and the narrowing reads
as policy. That is why this is checked statically -- there is no request that
can reveal it, so no test that makes requests ever will.

── WHAT THIS DOES NOT CHECK, SAID OUT LOUD RATHER THAN IMPLIED ────────────────
One allow-list, in one file. Not every role literal on the platform. A sweep is
the obviously tempting generalisation and it needs to know which app each
literal is gated on, which is not derivable from the literal -- guessing it
would produce a checker that is confidently wrong about apps it misattributed,
which is worse than one that is narrow and says so. If a second gate of this
shape is found, add it to GATES below by hand, with its app.
"""
import io
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (label, file, the `const NAME = { ... };` to read, the app whose vocabulary
#  governs it). The app is stated, never inferred -- see the docstring.
GATES = [
    ('law_trust_reconcile', 'api/sd-data.js', 'LAW_RECONCILE_ROLES', 'sairnlaw'),
]

VOCAB_FILE = 'api/_lib/auth.js'


def fail(msg):
    print('COULD NOT TELL: ' + msg)
    print('This is exit 2. Nothing was checked, and that is not a pass.')
    sys.exit(2)


def read(rel):
    p = os.path.join(REPO, rel)
    if not os.path.isfile(p):
        fail('%s does not exist.' % rel)
    return io.open(p, encoding='utf-8').read()


def vocabulary(app):
    """ROLES_BY_APP from the source of truth, never a second copy kept here."""
    src = read(VOCAB_FILE)
    m = re.search(r'const\s+ROLES_BY_APP\s*=\s*\{(.*?)\n\};', src, re.S)
    if not m:
        fail('could not find `const ROLES_BY_APP = {...};` in %s. The shape of '
             'the source of truth changed and this check no longer reads it.'
             % VOCAB_FILE)
    row = re.search(r'^\s*%s\s*:\s*\[([^\]]*)\]' % re.escape(app),
                    m.group(1), re.M)
    if not row:
        fail('%s has no %s entry in ROLES_BY_APP.' % (VOCAB_FILE, app))
    roles = re.findall(r"'([^']+)'|\"([^\"]+)\"", row.group(1))
    out = [a or b for a, b in roles]
    if not out:
        fail('ROLES_BY_APP.%s parsed to an EMPTY list. An empty vocabulary '
             'would make every key below look phantom, which is a finding this '
             'check would have invented.' % app)
    return out


def allow_list(rel, name):
    src = read(rel)
    hits = re.findall(r'const\s+%s\s*=\s*\{([^}]*)\}\s*;' % re.escape(name), src)
    if not hits:
        fail('could not find `const %s = {...};` in %s. The anchor no longer '
             'matches, so this check tested NOTHING -- which is the failure '
             'mode it was written against, arriving from the other direction.'
             % (name, rel))
    if len(hits) > 1:
        fail('%s is declared %d times in %s. Which one gates the resource is '
             'not decidable from here.' % (name, len(hits), rel))
    keys = re.findall(r'([A-Za-z_][A-Za-z0-9_]*)\s*:', hits[0])
    if not keys:
        fail('%s in %s parsed to NO keys. An empty allow-list cannot be '
             'checked against a vocabulary.' % (name, rel))
    return keys


def main():
    findings = []
    for label, rel, name, app in GATES:
        vocab = vocabulary(app)
        keys = allow_list(rel, name)
        phantom = [k for k in keys if k not in vocab]
        print('%-22s %s = %s' % (label, name, keys))
        print('%-22s %s roles = %s' % ('', app, vocab))
        if phantom:
            findings.append(
                '%s: %s names %s, which %s does not have. The gate is NARROWER '
                'than it reads, and nothing at runtime will say so.'
                % (rel, name, ', '.join(phantom), app))
    print('')
    if findings:
        print('FAILED: %d role allow-list(s) name a role the app cannot issue.'
              % len(findings))
        for f in findings:
            print('    ' + f)
        return 1
    print('OK: %d allow-list(s), every key is a role the app can actually issue.'
          % len(GATES))
    return 0


if __name__ == '__main__':
    sys.exit(main())
