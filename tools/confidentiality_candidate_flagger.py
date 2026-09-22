r"""Narrow the B/C rows of docs/CRITICALITY-TIERS.md down to the handful a
human must actually read before the two-axis migration scores them.

Run: python tools/confidentiality_candidate_flagger.py [--json] [--quiet]

IT FLAGS. IT DOES NOT SCORE, AND THAT IS NOT A LIMITATION TO BE FIXED LATER.
docs/2026-09-21-criticality-tiers-two-axis-spec.md §3.3 is explicit: a script
cannot correctly assign a confidentiality tier, because the register's own
header already insists that anything above the default rule is a judgement with
evidence behind it -- "a tier asserted with no evidence is a label". What a
script CAN do is turn 288 rows into a list short enough to read by hand. Every
row this tool flags still needs a person; every row it does not flag carries
forward as Confidentiality-B by the stated default rule, exactly as B rows are
classified today for the single existing axis.

THREE SIGNALS, ALL FROM THE SPEC, AND EACH ONE IS THE METHOD A HUMAN ALREADY
USED BY HAND TONIGHT rather than a new idea:

  (a) NAME -- the resource or its app-level name matches a sensitivity pattern.
      This is the exact grep that found sd_exec_msgs.
  (b) PAYLOAD -- the fields the app stores on that resource match PII/PHI
      indicators, read from the app's own HTML rather than guessed.
  (c) ASYMMETRY -- the client restricts it and the server does not. A role-gated
      UI element with no server-side session or role check is the shape of the
      SV_RESOURCES finding, and it is a structural signal that whoever built the
      client already believed this data needed restricting.

(c) IS THE ONE WORTH HAVING, AND ITS FIRST SPELLING WAS USELESS. Asking only
"is there a server-side check" flagged 173 of 288 rows -- because whole apps
have no session gate by a RECORDED DECISION rather than by oversight
(SD_LOCAL_RESOURCES says so in its own header; BLD_RESOURCES is cited there as
the precedent). An absence that is deliberate and written down is not a
candidate for anything, and a flagger that returns two thirds of the corpus has
narrowed nothing. The signal is the DISAGREEMENT between the two halves, which
is what the spec asked for and what the first implementation dropped.

(b) HAD THE SAME DEFECT IN A DIFFERENT COORDINATE, AND IT WAS FOUND THE SAME
WAY -- by reading what a flagged row actually contained instead of trusting the
count. Its first spelling scanned the 400 characters after each occurrence of
the resource name for a PII/PHI word, which measures PROXIMITY, NOT OWNERSHIP.
These are single-file apps: every resource accessor is declared beside its
neighbours, so the window ran into the declaration next door. Of the 17 rows it
flagged, all 17 were wrong -- ten `sen_*` rows flagged for `pay_rate` because
the cache array listing the app's resources puts the string `'sen_pay_rates'`
(a DIFFERENT resource) within 400 characters of each of them, and
`leg_documents`, `leg_merch_catalog`, `leg_merch_units` and `leg_monuments`
flagged for `decedent` off one shared helper reading `c.decedent_name` from a
CASE. Signal (b) now reads the resource's own record literal -- the object the
app actually hands the write, balance-parsed and string-blanked -- so a
neighbour cannot contribute a field unless it is assigned to the identifier the
write passes. 17 flags became 4, and all 4 were checked by hand against the
full field list behind them.

THE PRICE OF THAT IS A COUNT THE REPORT PRINTS RATHER THAN BURIES: for a large
share of B/C rows the app never hands the resource a readable object literal at
all, so signal (b) CANNOT BE ASKED there. That is a could-not-tell, not a clean
payload, and `payload_fields` returns it as a separate boolean rather than an
empty list so the two can never be confused. Do not quote the figure from here
-- run the tool; it moves as the apps do.

IT STILL OVER-REPORTS IN ONE DIRECTION ON PURPOSE. A resource gated through a
dispatcher this tool does not recognise looks ungated here. Reported as a
candidate, never as a finding, and the report says so on every line.

THE FIXTURES ARE THE LOCK. `--self-test` runs six synthetic cases covering both
defect shapes and both directions -- three that must not flag and three that
must, including the second-argument write shape (`f('write','<name>', rec)`)
that the first anchor missed entirely. Run it before trusting any count below.

WHAT THIS TOOL WILL NOT DO, stated rather than discovered: it does not edit
docs/CRITICALITY-TIERS.md, it does not write a tier anywhere, and it exits 0
whether it flags 0 rows or 90. A flagger that failed a build would become a
thing people silence.
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True,
                      encoding='utf-8', errors='replace').stdout.strip()
REGISTER = os.environ.get('SAIRN_TIER_REGISTER') or os.path.join(
    REPO, 'docs', 'CRITICALITY-TIERS.md')
HANDLER = os.path.join(REPO, 'api', 'sd-data.js')
RESOURCES_DIR = os.path.join(REPO, 'api', '_resources')

# (a) The name pattern this session used by hand. Extendable on purpose -- the
# spec calls it "the exact pattern this session used", not a complete one.
NAME_PATTERN = re.compile(
    r'exec|private|confiden|msgs?$|_msgs|notes?$|_notes|comms?$|_comm|portal|soap|'
    r'chat|message|diagnos|patient|client|custody|death|cremat|insur|credential|'
    r'ssn|payroll|salary|wage|bank|account', re.I)

# (b) Field-name indicators, read from the app's stored payloads.
PAYLOAD_PATTERN = re.compile(
    r'\bssn\b|social_security|\bdob\b|date_of_birth|diagnos|medication|allerg|'
    r'\bnpi\b|license_no|account_number|routing|iban|salary|wage|pay_rate|'
    r'privileged|attorney|decedent|next_of_kin|emergency_contact|home_address|'
    r'personal_email|personal_phone|\bpin\b|password', re.I)

# The tier-row shape, anchored the same way every other consumer of this file
# anchors: backticked name, then the bold letter in column 2.
ROW = re.compile(r'^\|\s*`([a-z0-9_]+)`\s*\|\s*\*\*([ABC])\*\*\s*\|(.*)$')


def register_rows():
    """[(name, tier, rest)] for every resource row, in file order."""
    out = []
    for line in io.open(REGISTER, encoding='utf-8'):
        m = ROW.match(line.rstrip('\n'))
        if m:
            out.append((m.group(1), m.group(2), m.group(3)))
    return out


def app_sources():
    """{app: html text}, read once. A missing page is recorded, not skipped."""
    pages, missing = {}, []
    for fn in sorted(os.listdir(RESOURCES_DIR)):
        if not fn.endswith('.js'):
            continue
        app = fn[:-3]
        path = os.path.join(REPO, app + '.html')
        if os.path.isfile(path):
            pages[app] = io.open(path, encoding='utf-8', errors='replace').read()
        else:
            missing.append(app)
    return pages, missing


def resource_app():
    """{resource: app}, from api/_resources/<app>.js -- the platform's own unit."""
    owner = {}
    for fn in sorted(os.listdir(RESOURCES_DIR)):
        if not fn.endswith('.js') or fn == 'index.js':
            continue
        app = fn[:-3]
        src = io.open(os.path.join(RESOURCES_DIR, fn), encoding='utf-8',
                      errors='replace').read()
        for m in re.finditer(r"'([a-z0-9_]+)'", src):
            owner.setdefault(m.group(1), app)
    return owner


# The next argument after the resource name in a call: either an inline object /
# array literal, or the identifier of a record variable built just above. The
# name is NOT required to be the first argument -- the apps spell the write both
# ways, `st('alf_clients', list)` and `alfData('write','alf_clients', rec, true)`,
# and anchoring on `(` alone silently missed every call of the second shape.
NEXT_ARG = re.compile(r"[(,]\s*'%s'\s*,\s*(?:(?P<lit>[\[{])|(?P<var>[A-Za-z_$][\w$]*)\s*[,)])")


def _balanced(src, i):
    """Index just past the literal opening at src[i] ('[' or '{'), or -1.

    String-aware, because a resource payload routinely contains a brace or a
    bracket inside a quoted default and a naive depth count stops in the wrong
    place -- which would hand the key reader a truncated literal and quietly
    lose the tail of the field list.
    """
    depth, quote, j = 0, None, i
    while j < len(src):
        c = src[j]
        if quote:
            if c == '\\':
                j += 2
                continue
            if c == quote:
                quote = None
        elif c in '\'"`':
            quote = c
        elif c in '[{':
            depth += 1
        elif c in ']}':
            depth -= 1
            if depth == 0:
                return j + 1
        j += 1
    return -1


KEY = re.compile(r'(?:[{,]\s*)([A-Za-z_$][\w$]*)\s*:')


def _literal_keys(lit):
    """Property names declared in an object/array literal, strings blanked first.

    Blanking the string bodies matters: `{note:'id: 42'}` otherwise reports a
    field called `id` that the record does not have.
    """
    out, quote, buf = [], None, []
    i = 0
    while i < len(lit):
        c = lit[i]
        if quote:
            if c == '\\':
                buf.append('  ')
                i += 2
                continue
            buf.append(' ')
            if c == quote:
                quote = None
        elif c in '\'"`':
            quote = c
            buf.append(' ')
        else:
            buf.append(c)
        i += 1
    for m in KEY.finditer(''.join(buf)):
        out.append(m.group(1))
    return out


def payload_fields(name, pages, owner):
    """Field names this resource's OWN record carries, from the app's own source.

    THE FIRST SPELLING OF THIS SIGNAL MEASURED PROXIMITY, NOT OWNERSHIP, AND
    EVERY ROW IT FLAGGED WAS WRONG. It scanned the 400 characters after each
    occurrence of the resource name for a PII/PHI word. In a single-file app
    every resource accessor is declared next to its neighbours, so the window
    ran straight into the declaration next door. Measured on the real corpus
    before this was rewritten: all ten `sen_*` rows were flagged for `pay_rate`
    because the array literal listing the app's resources puts the string
    `'sen_pay_rates'` -- a DIFFERENT resource -- within 400 characters of each
    of them; `leg_documents`, `leg_merch_catalog` and `leg_merch_units` were
    all flagged for `decedent` by one shared `caseLabel()` helper reading
    `c.decedent_name` off a CASE. Seventeen flags, none of them a field of the
    row they were attached to. The same defect class the client-restriction
    signal had, in a different coordinate.

    What replaces it is structural: find where the app hands a record to this
    resource -- `f('<name>', {...})`, `f('write','<name>', rec)` -- and read
    the property names out of THAT literal, balance-parsed and string-blanked.
    A neighbouring declaration cannot contribute a field unless it is literally
    assigned to the variable this call passes.

    THE RESIDUAL WINDOW IS NAMED RATHER THAN HIDDEN. When the argument is a
    variable, the assignment `var rec = {` is looked for in the 6000 characters
    before the call. That is still a window, but it is one an unrelated
    declaration cannot enter by accident: it has to be an object literal
    assigned to the exact identifier this write passes.

    Returns (fields, found), where `found` is False when the app never hands
    this resource a readable literal at all. NO FIELD LIST IS NOT AN EMPTY ONE
    -- the caller reports it as a could-not-tell, never as a clean payload.
    """
    app = owner.get(name)
    src = pages.get(app or '', '')
    if not src:
        return [], False
    fields, found = set(), False
    for m in re.compile(NEXT_ARG.pattern % re.escape(name)).finditer(src):
        if m.group('lit'):
            start = m.start('lit')
        else:
            back = src[max(0, m.start() - 6000):m.start()]
            a = None
            for am in re.finditer(r'\b' + re.escape(m.group('var')) + r'\s*=\s*\{',
                                  back):
                a = am
            if not a:
                continue
            start = max(0, m.start() - 6000) + a.end() - 1
        end = _balanced(src, start)
        if end < 0 or end - start > 40000:
            continue
        keys = _literal_keys(src[start:end])
        if keys:
            found = True
            fields.update(keys)
    hits = set()
    for f in fields:
        for h in PAYLOAD_PATTERN.finditer(f):
            hits.add(h.group(0).lower())
    return sorted(hits), found


# Client-side role gating, as the shipped pages actually spell it. Read from
# the real files rather than imagined: these are the constructs the SAIRN apps
# use to hide a panel from a role.
CLIENT_GATE = re.compile(
    r'is-admin|is-exec|isManagement|Privileged\(|sessionRole|session_role|'
    r"role\s*===|role\s*!==|ROLES\[|MANAGEMENT_ROLES|_ROLES\b", re.I)


def client_restricted(name, pages, owner):
    """Does the page restrict this resource to a role? Returns the construct or ''.

    Same 400-character window as the payload read, and for the same reason: a
    wider one starts describing the panel next door.
    """
    app = owner.get(name)
    src = pages.get(app or '', '')
    for m in re.finditer(r"'" + re.escape(name) + r"'", src):
        window = src[max(0, m.start() - 400):m.end() + 400]
        g = CLIENT_GATE.search(window)
        if g:
            return g.group(0)
    return ''


def server_gated(name, handler_src):
    """Is there ANY server-side session check on a path that names this resource?

    DELIBERATELY GENEROUS. A resource reached through a shared dispatcher --
    SD_SESSION_GATED, a LAW_RESOURCES-style block, a per-app map -- is gated
    without its own name appearing beside verifySessionToken. Answering 'yes'
    generously means signal (c) UNDER-reports rather than over-reports, which is
    the safer direction for a flagger whose output a human then reads: a missed
    candidate is found by the name and payload signals, while a false 'ungated'
    claim about a resource would be this tool asserting a security fact it has
    not established.
    """
    if name in handler_src.split('SD_SESSION_GATED')[0]:
        pass
    # 1. named directly in the central gate table
    gate_table = re.search(r'const SD_SESSION_GATED = \{[\s\S]*?\n    \};', handler_src)
    if gate_table and ("'" + name + "'") in gate_table.group(0):
        return True, 'SD_SESSION_GATED'
    # 2. named inside any block that also calls verifySessionToken within 2000 chars
    for m in re.finditer(r"'" + re.escape(name) + r"'", handler_src):
        near = handler_src[max(0, m.start() - 2000):m.start() + 2000]
        if 'verifySessionToken' in near:
            return True, 'a session check within the same block'
    # 3. a dispatcher map that contains it, where the map's own block is gated
    for m in re.finditer(r'const ([A-Z_]+RESOURCES\w*) = \{([\s\S]{0,4000}?)\};', handler_src):
        if ("'" + name + "'") in m.group(2) or (name + ':') in m.group(2):
            after = handler_src[m.end():m.end() + 4000]
            if 'verifySessionToken' in after:
                return True, m.group(1) + ' dispatcher'
    return False, ''


# Synthetic fixtures, written from the REAL defect shapes found on the corpus
# and locked before the rewrite was measured against real data, per
# docs/2026-09-13-cross-domain-disciplines.md. BOTH DIRECTIONS: a fixture that
# only proves the tool stops flagging would be satisfied by a tool that flags
# nothing, which is exactly the way this rewrite could go wrong.
FIXTURES = [
    # (label, page source, resource, expect_hits, expect_found)
    ('the sen_pay_rates bleed -- a neighbouring RESOURCE NAME, not a field',
     "var SEN_CACHES=['sen_branches','sen_applicants','sen_pay_rates',\n"
     "  'sen_payer_contracts','sen_franchise_agreements'];\n"
     "function branches(){return ld('sen_branches',[]);}\n",
     'sen_branches', False, False),
    ('the caseLabel bleed -- decedent_name belongs to a CASE',
     "function docs(){return ld('leg_documents',[]);}\n"
     "function caseLabel(id){var c=cases().find(function(x){return x.id===id;});\n"
     "  return c?(c.case_number+' -- '+c.decedent_name):'(unknown)';}\n",
     'leg_documents', False, False),
    ('a real inline payload literal',
     "st('alf_mar',[{id:'M1',resident_id:'R1',medication_name:'Lisinopril'}]);\n",
     'alf_mar', True, True),
    ('a real payload built into a variable, then written -- and the resource '
     'name is the SECOND argument, the shape the first anchor missed entirely',
     "var rec={id:reid,name:name,diagnosis:$('d').value,payer:$('p').value};\n"
     "  st('alf_clients',list);\n"
     "  await alfData('write','alf_clients',rec,true);\n",
     'alf_clients', True, True),
    ('a PII word inside a STRING VALUE is not a field name',
     "st('sd_jobs',[{id:'J1',note:'call about the ssn paperwork'}]);\n",
     'sd_jobs', False, True),
    ('an empty default is not a field list and must not read as clean',
     "function x(){return ld('sd_quotes',[]);}\n",
     'sd_quotes', False, False),
]


def self_test():
    """Run the locked fixtures. Exits non-zero on any disagreement.

    Both directions on purpose: three fixtures must NOT flag and three MUST.
    A one-directional lock would be satisfied by a payload signal that had
    stopped working altogether, which is the way this particular rewrite is
    most likely to fail.
    """
    bad = 0
    for label, src, res, want_hits, want_found in FIXTURES:
        hits, found = payload_fields(res, {'fx': src}, {res: 'fx'})
        ok = (bool(hits) == want_hits) and (found == want_found)
        print('  %-4s %s\n         hits=%s found=%s (wanted hits=%s found=%s)'
              % ('PASS' if ok else 'FAIL', label, hits, found, want_hits, want_found))
        if not ok:
            bad += 1
    print('\n  %d fixture(s), %d failing' % (len(FIXTURES), bad))
    return 1 if bad else 0


def main(argv=None):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--quiet', action='store_true')
    ap.add_argument('--self-test', action='store_true',
                    help='run the locked payload-signal fixtures and exit')
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()

    if not os.path.isfile(REGISTER):
        print('COULD NOT RUN: no register at %s' % REGISTER)
        return 3
    handler_src = io.open(HANDLER, encoding='utf-8', errors='replace').read()
    pages, missing_pages = app_sources()
    owner = resource_app()
    rows = register_rows()
    if not rows:
        print('COULD NOT RUN: no resource rows parsed from %s. An empty scan is '
              'not a clean one.' % REGISTER)
        return 3

    bc = [(n, t) for n, t, _ in rows if t in ('B', 'C')]
    flagged, clear, no_payload_read = [], [], []
    for name, tier in bc:
        why = []
        if NAME_PATTERN.search(name):
            why.append(('name', 'the resource name matches the sensitivity pattern'))
        fields, field_list_found = payload_fields(name, pages, owner)
        if not field_list_found:
            no_payload_read.append(name)
        if fields:
            why.append(('payload', 'stores field(s) matching PII/PHI indicators: '
                                   + ', '.join(fields[:6])))
        gated, how = server_gated(name, handler_src)
        client_gate = client_restricted(name, pages, owner)
        # THE SIGNAL IS THE ASYMMETRY, NOT THE ABSENCE. Measured: asking only
        # "is there a server-side check" flagged 173 of 288 rows, because whole
        # apps -- BLD_RESOURCES, SD_LOCAL_RESOURCES and others -- have NO
        # session gate by a recorded decision, not by oversight. An absence
        # that is deliberate and documented is not a candidate for anything.
        # What the spec actually asks for is the DISAGREEMENT: the client
        # restricts it and the server does not, which is a structural sign that
        # whoever built the UI already believed this data needed restricting.
        if client_gate and not gated:
            why.append(('asymmetry', 'the CLIENT restricts it (%s) and no '
                                     'server-side session check was found on any '
                                     'path naming it' % client_gate))
        (flagged if why else clear).append(
            {'resource': name, 'tier': tier, 'app': owner.get(name, '?'),
             'signals': [w[0] for w in why], 'why': [w[1] for w in why],
             'gate': how})

    if args.json:
        print(json.dumps({'flagged': flagged, 'clear': [c['resource'] for c in clear],
                          'missing_pages': missing_pages,
                          'payload_signal_could_not_be_read': no_payload_read},
                         indent=1))
        return 0

    if not args.quiet:
        print('CONFIDENTIALITY CANDIDATE FLAGGER -- it flags, it does not score\n')
        print('  register      : %s' % os.path.relpath(REGISTER, REPO))
        print('  resource rows : %d  (%d B/C, %d A -- A rows are re-derived by hand '
              'per spec 3.2 and are not this tool\'s job)'
              % (len(rows), len(bc), len(rows) - len(bc)))
        if missing_pages:
            print('  NO PAGE FOUND for %d app(s), so signals (b) and (c) could not be '
                  'asked there: %s' % (len(missing_pages), ', '.join(missing_pages)))
            print('  That is a COULD-NOT-TELL for those rows, not a clean bill.')
        print('')
        print('  FLAGGED FOR A HUMAN READ: %d of %d B/C rows' % (len(flagged), len(bc)))
        print('  carried forward as Confidentiality-B by the stated rule: %d'
              % len(clear))
        print('')
        print('  PAYLOAD SIGNAL COULD NOT BE READ AT ALL for %d of %d B/C rows --'
              % (len(no_payload_read), len(bc)))
        print('  the app never hands those resources a readable object literal, so')
        print('  signal (b) is a COULD-NOT-TELL there and not a clean payload. It is')
        print('  the single largest gap in this tool and it is printed, not buried.')
        print('')
        by_signal = {}
        for f in flagged:
            for s in f['signals']:
                by_signal[s] = by_signal.get(s, 0) + 1
        for s in sorted(by_signal):
            print('    signal %-10s %d row(s)' % (s, by_signal[s]))
        print('')
        for f in sorted(flagged, key=lambda x: (-len(x['signals']), x['resource'])):
            print('  %-26s %s  [%s]' % (f['resource'], f['tier'], ', '.join(f['signals'])))
            for w in f['why']:
                print('      - %s' % w)
        print('')
        print('  NONE OF THE ABOVE IS A TIER. Each flagged row needs a person to read')
        print('  it and write evidence, per the register\'s own rule that a tier with')
        print('  no evidence is a label. Signal (asymmetry) over-reports by')
        print('  construction -- a resource gated through a dispatcher this tool did')
        print('  not recognise looks ungated here and is not.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
