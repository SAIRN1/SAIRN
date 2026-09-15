"""Item 61 -- every secret this platform reads, what it unlocks, and what
happens when it is ABSENT.

    python tools/secrets_inventory.py            # the report
    python tools/secrets_inventory.py --write    # regenerate docs/SECRETS-INVENTORY.md
    python tools/secrets_inventory.py --check    # the document still matches the code
    python tools/secrets_inventory.py --fixtures # the blind lock alone

── WHY AN INVENTORY IS THE PREREQUISITE AND NOT THE POINT ─────────────────
A list of environment variables is a `grep`. What makes this worth having is
the two columns a grep cannot produce:

  BLAST RADIUS -- how many PRODUCTION modules transitively depend on the
    variable, taken from tools/dependency_graph.py rather than recomputed here,
    so the two documents cannot disagree about the same number.

  ABSENCE BEHAVIOUR -- whether the code that reads it REFUSES when it is
    missing, or carries on. That is the question a secrets inventory exists to
    answer, because an unset credential that fails closed is an outage and an
    unset credential that fails open is a security incident, and they look
    identical in a list of names.

── THE CLASSIFICATION IS HAND-WRITTEN, THE NUMBERS ARE NOT ────────────────
Whether a variable is a CREDENTIAL or a CONFIG value is a judgement, and it is
the judgement the whole page turns on -- so it lives in SECRETS below and this
REFUSES TO RUN if a variable has no entry, or if an entry names a variable the
code no longer reads. Same shape as tools/tooling_inventory.py, which exists
for the same reason: a generated document with a hand-written half stays true
only if the hand-written half is forced.

A NEW SECRET THEREFORE BREAKS THIS TOOL UNTIL SOMEBODY CLASSIFIES IT. That is
the feature. The alternative is a row that appears with a blank cell and reads
as "nothing to say about this one".

── THE ABSENCE CHECK IS A HEURISTIC AND SAYS SO ───────────────────────────
It looks for a guard naming the variable that leads to a refusal in the same
file. It will be wrong in both directions:

  * a guard in a CALLER rather than the reading file reads as unguarded here;
  * a guard that tests the variable and then carries on anyway reads as
    guarded, because this cannot follow control flow.

So the third state is NO GUARD FOUND, not UNGUARDED -- it is a pointer to read
the file, never a verdict about it. A checker that turns "I could not tell"
into a finding is the same defect as one that turns it into a pass.
"""
import io
import os
import re
import sys
from collections import defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import dependency_graph as G                                     # noqa: E402

DOC = os.path.join(REPO, 'docs', 'SECRETS-INVENTORY.md')

# ── THE HAND-WRITTEN HALF ─────────────────────────────────────────────────
# KIND is the judgement: what does holding this value let somebody DO.
#   CREDENTIAL  -- possession grants access to data or money. A leak is an
#                  incident; a rotation is a coordinated event.
#   ENDPOINT    -- names WHERE something is, not permission to use it. Still
#                  load-bearing: everything stops without it.
#   TUNING      -- a threshold, a mode, a limit. Wrong values change behaviour
#                  and cost nothing to disclose.
#   ADDRESS     -- a URL or email the platform sends to or redirects to.
SECRETS = {
    'SUPABASE_SERVICE_ROLE_KEY': ('CREDENTIAL', 'the service-role key for the ONE Supabase project holding every app\'s data -- it bypasses RLS by design, so it is the single most consequential value on the platform'),
    'SUPABASE_URL': ('ENDPOINT', 'the one Supabase project every app reads and writes; not permission, but nothing works without it'),
    'SD_AUTH_SECRET': ('CREDENTIAL', 'signs and verifies EVERY app\'s employee session token -- one secret, no per-app key and no overlap window, so a rotation logs everyone out of everything at once'),
    'OIDC_CLIENT_SECRET': ('CREDENTIAL', 'the OIDC client secret; the only one of the four OIDC values whose exposure is a security event rather than a misconfiguration'),
    # ── CLASSIFIED 2026-09-15, AND WHY THE ANSWER CHANGED ────────────────────
    # These two blocked this tool from generating for several hours, and I
    # declined to classify them on the grounds that judging somebody else's
    # secret is a judgement about what holding it lets you do. THAT WAS RIGHT
    # WITH WHAT I HAD READ AND WRONG ONCE I READ THE CODE. api/_lib/ai-rate-limit.js
    # documents both at the switch, in its author's own words: they are the
    # per-tenant sub-budget and the contention floor inside the existing per-app
    # AI ceiling, Michael's decision of 2026-09-15. Numeric thresholds. They
    # name no secret, grant no access, and their absence falls back to a
    # documented default rather than to zero -- the file says so explicitly,
    # because "a zero share would cap every tenant at nothing the moment the
    # floor is crossed".
    #
    # So the classification is DERIVED from the author's own documentation, not
    # guessed, and no live claim covered them when this was written. TUNING is
    # the same kind OIDC_CLIENT_ID and the Firebase web values carry: wrong
    # values change behaviour, exposure is not a security event.
    'SAIRN_AI_TENANT_SHARE': ('TUNING', 'the per-tenant sub-budget inside the per-app daily AI ceiling -- how much of the app limit any ONE licence may hold once contention starts. Optional; defaults to half the app limit. An unparseable value falls back to that default rather than to zero, deliberately, because a zero share would cap every tenant at nothing the moment the floor is crossed'),
    'SAIRN_AI_CONTENTION_FLOOR': ('TUNING', 'the app-level usage below which no tenant is capped at all -- the sub-budget binds only under contention. Optional; defaults to half the app limit. Ten of the fourteen apps with seeded licences have exactly ONE tenant, so a hard cap below this floor would take capacity from somebody contending with nobody'),
    'OIDC_CLIENT_ID': ('TUNING', 'the OIDC client identifier -- public by design in the OIDC spec, listed because losing it breaks sign-in everywhere'),
    'OIDC_ISSUER_URL': ('ENDPOINT', 'the OIDC provider'),
    'OIDC_REDIRECT_URI': ('ADDRESS', 'where the OIDC provider sends the user back; a wrong value is a sign-in that dead-ends'),
    'ANTHROPIC_API_KEY': ('CREDENTIAL', 'billed AI access for every app that calls Claude'),
    'STRIPE_SECRET_KEY': ('CREDENTIAL', 'live charge and refund authority on the SAIRNcash Stripe account'),
    'STRIPE_WEBHOOK_SECRET': ('CREDENTIAL', 'verifies that a webhook really came from Stripe -- without it a forged POST is indistinguishable from a real payment event'),
    'SAIRNCASH_STRIPE_WEBHOOK_SECRET': ('CREDENTIAL', 'the SAIRNcash-specific webhook signing secret. NOTE the near-collision with STRIPE_WEBHOOK_SECRET above: two variables, two endpoints, names one prefix apart'),
    'STRIPE_PRICE_ID': ('TUNING', 'which Stripe price a checkout uses; its ABSENCE once made checkout.js answer "Stripe not configured" while the KEY was set the whole time, and four separate readers recorded that as evidence about the key -- see item 94'),
    'CRON_SECRET': ('CREDENTIAL', 'the bearer every scheduled job checks; possession lets anyone trigger a checkpoint, a sweep or a watchdog run'),
    'RESEND_API_KEY': ('CREDENTIAL', 'sends email as the platform'),
    'RESEND_FROM_EMAIL': ('ADDRESS', 'the sender address; the RESEND_FROM_ADDRESS typo that never existed cost a previous session hours'),
    'COURTLISTENER_API_TOKEN': ('CREDENTIAL', 'CourtListener API access for the legal citator'),
    'STABILITY_API_KEY': ('CREDENTIAL', 'billed image generation for StoneDesk rendering'),
    'DENTAL_BI_KEY': ('CREDENTIAL', 'the SAIRNdental BI export key'),
    'DENTAL_RATE_LIMIT_SALT': ('CREDENTIAL', 'salts the hashed identifiers the dental and StoneDesk public rate limiters key on -- leaking it makes the stored hashes reversible'),
    'STONEDESK_RATE_LIMIT_SALT': ('CREDENTIAL', 'the StoneDesk equivalent of DENTAL_RATE_LIMIT_SALT'),
    'ALF_PHARMACY_SECRET': ('CREDENTIAL', 'authenticates the pharmacy integration into the SAIRNcare eMAR'),
    'SAIRNCASH_ADMIN_SECRET': ('CREDENTIAL', 'lets a caller renew a SAIRNcash trial without paying'),
    'SAIRNCASH_FIREBASE_SERVICE_ACCOUNT': ('CREDENTIAL', 'full Firebase admin authority for SAIRNcash'),
    'SAIRNCASH_FIREBASE_API_KEY': ('TUNING', 'a Firebase WEB api key -- public by design, shipped to browsers, and listed so nobody spends an afternoon treating it as a leak'),
    'SAIRNCASH_FIREBASE_APP_ID': ('TUNING', 'Firebase client config; public by design'),
    'SAIRNCASH_FIREBASE_AUTH_DOMAIN': ('ENDPOINT', 'Firebase client config; public by design'),
    'SAIRNCASH_FIREBASE_DATABASE_URL': ('ENDPOINT', 'the SAIRNcash Firebase realtime database'),
    'SAIRNCASH_FIREBASE_MEASUREMENT_ID': ('TUNING', 'Firebase analytics id; public by design'),
    'SAIRNCASH_FIREBASE_MESSAGING_SENDER_ID': ('TUNING', 'Firebase client config; public by design'),
    'SAIRNCASH_FIREBASE_PROJECT_ID': ('TUNING', 'Firebase client config; public by design'),
    'SAIRNCASH_FIREBASE_STORAGE_BUCKET': ('ENDPOINT', 'Firebase storage bucket; public by design'),
    'QB_CLIENT_SECRET': ('CREDENTIAL', 'QuickBooks OAuth client secret'),
    'QB_CLIENT_ID': ('TUNING', 'QuickBooks OAuth client identifier'),
    'QB_REDIRECT_URI': ('ADDRESS', 'where QuickBooks sends the user back after consent'),
    'SAIRN_AI_DAILY_LIMIT': ('TUNING', 'per-licence daily AI call ceiling'),
    'SAIRN_AI_RATE_LIMIT_MODE': ('TUNING', 'whether the AI rate limiter enforces or observes'),
    'SAIRN_ANON_INVALID_LIMIT': ('TUNING', 'how many invalid anonymous attempts are tolerated'),
    'SAIRN_ANON_RATE_LIMIT_MODE': ('TUNING', 'whether the anonymous limiter enforces or observes'),
    'SAIRN_ANON_WINDOW_SECONDS': ('TUNING', 'the anonymous rate-limit window'),
    'SAIRN_APP_BOUNDARY': ('TUNING', 'whether /api/sd-data enforces the per-app resource boundary'),
    'SAIRN_CLAUDE_AUTH_MODE': ('TUNING', 'which auth mode /api/claude requires'),
    'SAIRN_CRON_JITTER_MS': ('TUNING', 'the bounded random delay before a scheduled job\'s first backend read; 0 disables it'),
    'SAIRN_BASE_URL': ('ADDRESS', 'the address the watchdog retries a failed job against'),
    'SAIRN_OPS_EMAIL': ('ADDRESS', 'where the cron watchdog sends an alert. MEASURED UNSET IN PRODUCTION 2026-09-14: every watchdog alert reported "SAIRN_OPS_EMAIL is not configured, so nobody was told"'),
    'SAIRN_ESCALATION_EMAIL': ('ADDRESS', 'where the watchdog escalates a repeated failure'),
    'SITE_URL': ('ADDRESS', 'the public site address used to build Stripe return URLs'),
    'VERCEL_URL': ('ADDRESS', 'the deployment address Vercel injects; the watchdog\'s fallback retry target'),
}

KINDS = ('CREDENTIAL', 'ENDPOINT', 'TUNING', 'ADDRESS')

# A guard is recognised by the variable name appearing in a negation or a
# missing-list near a refusal. Deliberately loose: the cost of a false GUARDED
# is that somebody reads a file they did not need to, and the cost of a false
# NO GUARD FOUND is the same. Neither is a verdict.
def aliases(body, name):
    """The local names the variable is read into.

    THE FIRST RUN OF THIS TOOL DID NOT DO THIS AND WAS THEREFORE WRONG ABOUT
    MOST OF THE TREE. It looked for `!process.env.NAME`, and almost nothing is
    written that way: api/sairncash/checkout.js does
    `const stripeKey = process.env.STRIPE_SECRET_KEY` and then `if (!stripeKey)`,
    so a correctly guarded live Stripe key came back NO GUARD FOUND -- along
    with all four OIDC variables. A column that is wrong about the majority
    case is a column people switch off, which is this repo's recorded fate for
    a first draft that over-reports.
    """
    out = {'process.env.' + name}
    for m in re.finditer(r'(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*process\.env\.'
                         + name + r'\b', body):
        out.add(m.group(1))
    return out


def guard_patterns(name, body=''):
    """A boolean TEST of the variable, in any of the three forms this tree uses.

    NEGATION       if (!stripeKey) { ... return; }        api/sairncash/checkout.js
    CONJUNCTION    !!(process.env.A && process.env.B)     api/_lib/auth.js
    MISSING LIST   [!process.env.X ? 'X' : null]          api/sairndental/send-reminder.js

    All three are real and in production. Matching only the first is what made
    the first run report four correctly-guarded OIDC variables and a
    correctly-guarded Stripe key as unguarded.
    """
    pats = []
    for tok in sorted(aliases(body, name)):
        t = re.escape(tok)
        pats.extend([
            r'!\s*' + t + r'\b',
            t + r'\s*(?:&&|\|\|)',
            r'(?:&&|\|\|)\s*' + t + r'\b',
            r'if\s*\([^)]{0,200}?' + t + r'\b',
        ])
    pats.append(r"['\"]" + re.escape(name) + r"['\"]")
    return pats


def analyse():
    nodes, edges, _ = G.build(include_env=True, with_tests=False)
    rad = G.blast(edges, nodes)
    readers = defaultdict(set)
    for a, bs in edges.items():
        for b in bs:
            if b.startswith('env:'):
                readers[b[4:]].add(a)

    bodies = {}

    def body_of(f):
        if f not in bodies:
            bodies[f] = G.strip_js(io.open(os.path.join(REPO, f), encoding='utf-8',
                                           errors='replace').read())
        return bodies[f]

    rows = []
    for name in sorted(readers):
        files = sorted(readers[name])
        guarded, via, unknown = [], [], []
        for f in files:
            body = body_of(f)
            refuses = re.search(r'\b(return|throw|res\.status)\b', body) is not None
            hit = any(re.search(p, body) for p in guard_patterns(name, body))
            if hit and refuses:
                guarded.append(f)
                continue
            # ── ONE HOP INTO A REQUIRED MODULE, because that is where this
            # platform is actively MOVING its guards. api/sairncash/checkout.js
            # reads STRIPE_SECRET_KEY and does not test it: item 94 moved the
            # whole "is Stripe configured" question into
            # api/_lib/stripe-config.js the same week. Without this hop the
            # inventory would report the refactor that FIXED a real confusion
            # as if it had removed a guard -- a checker punishing the thing it
            # should be rewarding, which is how a checker loses its audience.
            #
            # ONE HOP, NOT TRANSITIVE, and that is deliberate: two hops away
            # the claim "this file is guarded" stops being something a reader
            # can check quickly, and a guard nobody can find is not much better
            # than no guard.
            found = None
            for dep in sorted(edges.get(f, ())):
                if dep.startswith('env:'):
                    continue
                dbody = body_of(dep)
                if any(re.search(p, dbody) for p in guard_patterns(name, dbody)) and \
                   re.search(r'\b(return|throw|res\.status)\b', dbody):
                    found = dep
                    break
            if found:
                via.append((f, found))
            else:
                unknown.append(f)
        rows.append({
            'name': name,
            'kind': SECRETS[name][0] if name in SECRETS else None,
            'note': SECRETS[name][1] if name in SECRETS else None,
            'blast': rad.get('env:' + name, 0),
            'readers': files,
            'guarded': guarded,
            'guarded_via': via,
            'no_guard_found': unknown,
        })
    return rows


def vocabulary_problems(rows):
    seen = {r['name'] for r in rows}
    bad = []
    for r in rows:
        if r['kind'] is None:
            bad.append('UNCLASSIFIED  %s is read by %d file(s) and has no entry in SECRETS. '
                       'A new secret breaks this tool on purpose.'
                       % (r['name'], len(r['readers'])))
        elif r['kind'] not in KINDS:
            bad.append('BAD KIND      %s has kind %r; the vocabulary is %s'
                       % (r['name'], r['kind'], ', '.join(KINDS)))
    for name in sorted(SECRETS):
        if name not in seen:
            bad.append('STALE ENTRY   %s is classified here and nothing under api/ reads it -- '
                       'renamed, removed, or mistyped' % name)
    return bad


# ── THE BLIND LOCK ────────────────────────────────────────────────────────
# Decided against synthetic sources with hand-known answers, before the real
# tree was read. The two that matter are the two directions the guard heuristic
# can be wrong in, plus the CONTROL that it is not simply always saying yes.
FIXTURES = [
    ('a guard on the variable that refuses IS recognised',
     "if (!process.env.MY_KEY) { res.status(500); return; }\nconst k = process.env.MY_KEY;",
     'MY_KEY', True),
    ('a variable named in a missing[] list before a refusal IS recognised',
     "var missing = [!process.env.MY_KEY ? 'MY_KEY' : null].filter(Boolean);\n"
     "if (missing.length) { res.status(500); return; }",
     'MY_KEY', True),
    ('a bare read with no guard and no refusal anywhere is NOT recognised',
     "const k = process.env.MY_KEY;\nconsole.log(k);",
     'MY_KEY', False),
    ('CONTROL: a guard on a DIFFERENT variable is not a guard on this one -- '
     'otherwise every file containing any guard reads as covered',
     "if (!process.env.OTHER_KEY) { return; }\nconst k = process.env.MY_KEY;",
     'MY_KEY', False),
    ('a guard inside a COMMENT is not a guard',
     "// if (!process.env.MY_KEY) return;\nconst k = process.env.MY_KEY;\nreturn k;",
     'MY_KEY', False),
]


def _guard_verdict(src, name):
    body = G.strip_js(src)
    refuses = re.search(r'\b(return|throw|res\.status)\b', body) is not None
    hit = any(re.search(p, body) for p in guard_patterns(name, body))
    return bool(hit and refuses)


def run_fixtures():
    bad = []
    for label, src, name, want in FIXTURES:
        got = _guard_verdict(src, name)
        if got != want:
            bad.append((label, want, got))
    return bad


def render(rows):
    NL = chr(10)
    out = []
    out.append('# Secrets inventory -- what each one unlocks, and what happens when it is absent')
    out.append('')
    out.append('**GENERATED by `python tools/secrets_inventory.py --write`. Do not hand-edit the '
               'numbers.** The CLASSIFICATION is hand-written and lives in `SECRETS` inside that '
               'tool, which **refuses to run** if a variable the code reads has no entry -- so a '
               'new secret breaks the tool until somebody decides what it is. Run `--check` to '
               'find out whether this page still matches the code.')
    out.append('')
    out.append('## Why an inventory is the prerequisite and not the point')
    out.append('')
    out.append('A list of environment variable names is a `grep`. The two columns worth having '
               'are the ones a grep cannot produce:')
    out.append('')
    out.append('- **Blast radius** -- how many PRODUCTION modules transitively depend on it, '
               'taken from `tools/dependency_graph.py` rather than recomputed here, so this page '
               'and `docs/SPOF-REGISTER.md` cannot disagree about the same number.')
    out.append('- **Absence behaviour** -- whether the code that reads it REFUSES when it is '
               'missing. **An unset credential that fails closed is an outage; one that fails '
               'open is a security incident, and they look identical in a list of names.**')
    out.append('')
    out.append('## The absence column is a HEURISTIC, and the third state is real')
    out.append('')
    out.append('It looks for a guard naming the variable, in the same file, alongside a refusal. '
               'It is wrong in both directions: a guard in a CALLER reads as unguarded here, and '
               'a guard that tests the variable and then carries on anyway reads as guarded, '
               'because this cannot follow control flow. So the third state is **NO GUARD '
               'FOUND**, not *UNGUARDED* -- a pointer to read the file, never a verdict about it.')
    out.append('')
    counts = {}
    for r in rows:
        counts[r['kind']] = counts.get(r['kind'], 0) + 1
    out.append('## Totals')
    out.append('')
    out.append('| Kind | Count | What holding it lets somebody do |')
    out.append('|---|---|---|')
    out.append('| **CREDENTIAL** | %d | Access to data or money. A leak is an incident; a '
               'rotation is a coordinated event |' % counts.get('CREDENTIAL', 0))
    out.append('| **ENDPOINT** | %d | Names WHERE something is, not permission to use it -- and '
               'nothing works without it |' % counts.get('ENDPOINT', 0))
    out.append('| **ADDRESS** | %d | A URL or address the platform sends to or redirects to |'
               % counts.get('ADDRESS', 0))
    out.append('| **TUNING** | %d | A threshold, a mode, a limit. Wrong values change behaviour '
               'and cost nothing to disclose |' % counts.get('TUNING', 0))
    out.append('| | **%d** | |' % len(rows))
    out.append('')
    out.append('## The inventory')
    out.append('')
    out.append('Sorted by blast radius, because that is the order in which these matter.')
    out.append('')
    out.append('| Variable | Kind | Blast | Readers | Absence | What it unlocks |')
    out.append('|---|---|---|---|---|---|')
    for r in sorted(rows, key=lambda r: (-r['blast'], r['name'])):
        covered = len(r['guarded']) + len(r['guarded_via'])
        if not covered:
            absence = '**NO GUARD FOUND**'
        elif r['no_guard_found']:
            absence = 'guarded in %d of %d' % (covered, len(r['readers']))
        elif r['guarded_via']:
            absence = 'refuses (via %s)' % ', '.join(
                sorted({os.path.basename(m) for _, m in r['guarded_via']}))
        else:
            absence = 'refuses'
        out.append('| `%s` | %s | %d | %d | %s | %s |'
                   % (r['name'], r['kind'], r['blast'], len(r['readers']), absence, r['note']))
    out.append('')
    out.append('## What this cannot see')
    out.append('')
    out.append('- **Whether a variable is actually SET in production.** This reads the code, not '
               'the deployment. The one place that is known is in the table: `SAIRN_OPS_EMAIL` '
               'was measured unset on 2026-09-14, because every cron-watchdog alert said so in '
               'its own error text.')
    # THE EXCLUSION IS NOT EMPTY, AND SAYING SO IS THE POINT (2026-09-14).
    # "We do not scan tools/" and "a tool holds the service-role key" are
    # different statements, and only the first was written down. Recounted the
    # same day: 47 in api/, exactly the rows above.
    out.append('- Secrets read anywhere other than `process.env` under `api/`. '
               '**Recounted 2026-09-14: 47 in `api/`, exactly the rows above, '
               'so this page is complete for its scope. `tools/` reads 11 more, '
               '8 of them synthetic fixture names (`A`, `MY_KEY`, `X`) inside '
               "checkers' own tests.** The exclusion is not empty though: "
               '**`tools/restore_coherence_check.js` accepts `SAIRN_TARGET_KEY` '
               'and falls back to `SUPABASE_SERVICE_ROLE_KEY`** -- the widest '
               'credential on the platform, held by a tool this page cannot '
               'see.')
    out.append('- **Whether a CREDENTIAL is scoped to one app or grants the whole platform.** '
               '`SUPABASE_SERVICE_ROLE_KEY` is the sharpest case and its row says so; a general '
               'answer needs per-app isolation work, not this page.')
    out.append('')
    return NL.join(out) + NL


def main(argv):
    bad = run_fixtures()
    print('SECRETS INVENTORY -- item 61')
    if bad:
        print('  !! THE GUARD HEURISTIC FAILED ITS OWN FIXTURES. NOTHING WAS ANALYSED.')
        for label, want, got in bad:
            print('     wanted %r, got %r -- %s' % (want, got, label))
        return 2
    print('  blind lock: %d synthetic sources classify as written, run before the '
          'real tree was read.' % len(FIXTURES))
    if '--fixtures' in argv:
        return 0

    rows = analyse()
    problems = vocabulary_problems(rows)
    if problems:
        print('  REFUSING: the hand-written half does not cover the code.')
        for p in problems:
            print('    ' + p)
        return 2

    text = render(rows)
    if '--write' in argv:
        io.open(DOC, 'w', encoding='utf-8', newline=chr(10)).write(text)
        print('  wrote %s (%d variables)' % (os.path.relpath(DOC, REPO), len(rows)))
        return 0
    if '--check' in argv:
        if not os.path.exists(DOC):
            print('  COULD NOT RUN: %s does not exist. That is not a clean check.'
                  % os.path.relpath(DOC, REPO))
            return 2
        cur = io.open(DOC, encoding='utf-8').read().replace(chr(13), '')
        if cur != text:
            print('  FAIL: %s no longer matches the code. Regenerate with --write.'
                  % os.path.relpath(DOC, REPO))
            return 1
        print('  OK: %s matches the code.' % os.path.relpath(DOC, REPO))
        return 0

    creds = [r for r in rows if r['kind'] == 'CREDENTIAL']
    unguarded = [r for r in rows if not (r['guarded'] or r['guarded_via'])]
    widest = max(rows, key=lambda r: r['blast']) if rows else None
    print('  %d variable(s) read under api/: %d CREDENTIAL, %d other.'
          % (len(rows), len(creds), len(rows) - len(creds)))
    if widest:
        print('  widest: %s (blast %d)' % (widest['name'], widest['blast']))
    if unguarded:
        print('  NO GUARD FOUND in any reading file. READ THESE -- this is a pointer,')
        print('  not a verdict, and the heuristic is wrong in both directions:')
        for r in sorted(unguarded, key=lambda r: (-r['blast'], r['name'])):
            print('    %-38s %-11s blast %-3d  %s'
                  % (r['name'], r['kind'], r['blast'], ', '.join(r['readers'][:2])))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
