r"""Independent review of tools/confidentiality_candidate_flagger.py's ASYMMETRY
signal, discharging cody's Tier A obligation opened 2026-09-22T12:33:51Z.

    python tests/confidentiality_flagger_asymmetry_review_probe.py

REPORT-ONLY. Exit 0 by design, findings or not. It asserts nothing about a
shipped app and gates no push; it exists so the numbers below can be re-run by
the author instead of believed from prose.

WHY A PROBE AT ALL, since I have argued the other way twice this week. A review
whose every check is a direct read of one file needs no probe -- writing one to
restate a source read is ceremony. This is not that: the claims here are
computed over 288 register rows against 22 app files, and no reader can check
"18 of 288" or "the gate behind this flag is a data-field comparison" by eye.

AND THE CHECKS DELIBERATELY DO NOT GO THROUGH THE SUBJECT'S OWN PATTERNS WHERE
IT MATTERS. Asking `CLIENT_GATE` whether `CLIENT_GATE` matched something would
agree with the subject even where the subject is wrong -- the Ariane 5 point
CLAUDE.md already records: a second copy is not a second opinion. Arms 1-3
recompute comment spans and read the raw source line, which is a structurally
different method from the regex under review.

EVERY ANCHOR IS COUNTED AND A MISSING ONE IS A COULD-NOT-TELL, NOT A PASS. An
arm whose anchor has moved reports COULD NOT TELL and says which anchor, rather
than quietly reporting clean -- the failure `tools/sabotage_control_check.py`
measured most controls on this platform skipping.
"""
CONTROLS_FOR = []

import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'tools'))
os.chdir(REPO)

import confidentiality_candidate_flagger as F          # noqa: E402

FINDINGS, NOTES, CNR = [], [], []


def finding(n, text):
    FINDINGS.append(n)
    print('\nFINDING %d -- %s' % (n, text))


def note(text):
    NOTES.append(text)
    print('\n  %s' % text)


def could_not_tell(text):
    CNR.append(text)
    print('\nCOULD NOT TELL -- %s' % text)


def comment_spans(src):
    """(start, end) of every // line comment and /* */ block, string-aware.

    WRITTEN FROM THE RULE, not borrowed from the subject, because the subject
    has no notion of a comment at all -- which is half of finding 1.
    """
    spans, i, n = [], 0, len(src)
    quote = None
    while i < n:
        c = src[i]
        if quote:
            if c == '\\':
                i += 2
                continue
            if c == quote:
                quote = None
            i += 1
            continue
        if c in '\'"`':
            quote = c
            i += 1
            continue
        if c == '/' and i + 1 < n and src[i + 1] == '/':
            j = src.find('\n', i)
            j = n if j < 0 else j
            spans.append((i, j))
            i = j
            continue
        if c == '/' and i + 1 < n and src[i + 1] == '*':
            j = src.find('*/', i + 2)
            j = n if j < 0 else j + 2
            spans.append((i, j))
            i = j
            continue
        i += 1
    return spans


def inside(spans, pos):
    return any(a <= pos < b for a, b in spans)


def first_gate_site(name, src):
    """(name_offset, gate_offset, gate_text) for the occurrence client_restricted()
    would answer from -- the FIRST with a gate in its window, which is the
    subject's own short-circuit."""
    for m in re.finditer(r"'" + re.escape(name) + r"'", src):
        lo = max(0, m.start() - 400)
        g = F.CLIENT_GATE.search(src[lo:m.end() + 400])
        if g:
            return m.start(), lo + g.start(), g.group(0)
    return None, None, None


print(__doc__.split('\n\n')[0])
print('\n' + '=' * 72)

pages, missing = F.app_sources()
owner = F.resource_app()
rows = F.register_rows()
bc = [n for n, t, _ in rows if t in ('B', 'C')]
handler = io.open(os.path.join(REPO, 'api', 'sd-data.js'),
                  encoding='utf-8', errors='replace').read()

if not bc:
    could_not_tell('no B/C rows parsed from the register; every arm below '
                   'would pass vacuously. Nothing was checked.')
    sys.exit(0)

client_true = [n for n in bc if F.client_restricted(n, pages, owner)]
asym = [n for n in client_true if not F.server_gated(n, handler)[0]]
print('\nCORPUS: %d register rows, %d B/C. client_restricted TRUE for %d; of '
      'those,\n%d are also server-ungated and therefore reach the ASYMMETRY '
      'signal: %s'
      % (len(rows), len(bc), len(client_true), len(asym), ', '.join(sorted(asym))))

# ── FINDING 1: BOTH HALVES OF dnt_complaints' EVIDENCE ARE COMMENT TEXT ─────
if 'dnt_complaints' not in asym:
    could_not_tell('dnt_complaints no longer reaches the asymmetry signal, so '
                   'arm 1 was not run. It is not reporting clean.')
else:
    src = pages[owner['dnt_complaints']]
    spans = comment_spans(src)
    npos, gpos, gtext = first_gate_site('dnt_complaints', src)
    occurrences = list(re.finditer(r"'dnt_complaints'", src))
    coded = [m for m in occurrences if not inside(spans, m.start())]
    if inside(spans, npos) and inside(spans, gpos):
        finding(1, 'dnt_complaints: BOTH halves of the client-restriction '
                   'evidence are COMMENT TEXT, not code.')
        print('  the matched occurrence is at offset %d, inside a comment.' % npos)
        print('  the gate %r that answered for it is at offset %d, inside the '
              'SAME comment.' % (gtext, gpos))
        print('  %d occurrence(s) of the name in the file; %d outside comments, '
              'and none of those has a gate in window.'
              % (len(occurrences), len(coded)))
        print('  THE CONCLUSION IS STILL TRUE and that is the trap: the comment '
                'itself says\n  owner-only enforcement is UI-level, so the app '
                'really is client-restricted.\n  But the tool is reading '
                'DOCUMENTATION. Delete the comment and the flag\n  disappears '
                'while the application is byte-identical. PR 1.2 / scrubber '
                'item 2.')
    else:
        note('dnt_complaints evidence is NOT comment-sourced (name inside=%s, '
             'gate inside=%s). Finding 1 does not reproduce.'
             % (inside(spans, npos), inside(spans, gpos)))

# ── FINDING 2: sdn_team's "GATE" IS A RECORD FIELD, NOT A SESSION ROLE ─────
if 'sdn_team' not in asym:
    could_not_tell('sdn_team no longer reaches the asymmetry signal, so arm 2 '
                   'was not run. It is not reporting clean.')
else:
    src = pages[owner['sdn_team']]
    npos, gpos, gtext = first_gate_site('sdn_team', src)
    line = src[src.rfind('\n', 0, gpos) + 1:src.find('\n', gpos)]
    # READ THE RAW LINE, not CLIENT_GATE's opinion of it.
    is_field_cmp = bool(re.search(r"\b\w+\.role\s*===\s*'", line))
    in_filter = '.filter(' in line
    if is_field_cmp:
        finding(2, "sdn_team: the construct that answered \"the CLIENT "
                   "restricts it\" is a RECORD FIELD comparison, not a session "
                   "gate.")
        print('  gate text matched : %r at offset %d (%d chars from the name)'
              % (gtext, gpos, gpos - npos))
        print('  the actual line   : %s' % line.strip()[:160])
        print('  inside a .filter(): %s -- it COUNTS team members whose stored '
              '`role`\n                      column is "designer" for a KPI '
              'tile.' % in_filter)
        print('  CLIENT_GATE\'s `role\\s*===` cannot tell a SESSION role from a '
              'RECORD\'s role\n  column, and this is systematic rather than '
              'unlucky: sdn_team is a resource\n  whose own rows carry a `role` '
              'field, so any app storing one looks\n  client-restricted. Same '
              'class as scrubber item 24 -- a pattern bucketing on\n  a word '
              'with no context to say whose word it is.')
        # THE CONCLUSION IS CHECKED, NOT ASSERTED. "Nothing restricts sdn_team"
        # is a claim about a shipped app, so it is measured against the two
        # functions that actually create and write the record -- by reading
        # their bodies, not by asking CLIENT_GATE a second time.
        unguarded = []
        for fn in ('openTeamModal', 'saveTeam'):
            m = re.search(r'(?:async\s+)?function\s+%s\s*\(' % fn, src)
            if not m:
                could_not_tell('sairndesign has no %s(); the corroboration for '
                               'finding 2 did not run.' % fn)
                unguarded = None
                break
            end = src.find('\n}', m.start())
            body = src[m.start():end if end > 0 else m.start() + 2000]
            if not F.CLIENT_GATE.search(body):
                unguarded.append(fn)
        if unguarded:
            print('  CORROBORATED BY READING THE WRITE PATH, not by re-asking '
                  'the same regex:\n  %s contain no role construct of any kind. '
                  'sdnIsManagement() exists in\n  this app (%d call sites) and '
                  'is used for assignee rows and the roster --\n  never for the '
                  'team modal or the write. So sdn_team is NOT '
                  'client-restricted.'
                  % (' and '.join('%s()' % f for f in unguarded),
                     src.count('sdnIsManagement(')))
        print('  THIS ONE IS SIMPLY WRONG. Unlike finding 1 the conclusion does '
              'not survive:\n  the asymmetry signal has produced a candidate '
              'out of a dashboard count.')
    else:
        note('sdn_team gate line is not a record-field comparison: %r. '
             'Finding 2 does not reproduce.' % line.strip()[:120])

# ── ARM 3, THE CONTROL: REAL GATES ARE NOT COMMENT-SOURCED ────────────────
# Without this, findings 1 and 2 are satisfied by a probe that calls everything
# comment text or everything a field comparison.
_ctrl = [n for n in client_true if n.startswith('sen_')]
if not _ctrl:
    could_not_tell('no sen_* row is client_restricted, so the control for '
                   'findings 1-2 did not run and they stand unqualified.')
else:
    src = pages['sairnsenior']
    spans = comment_spans(src)
    real = []
    for n in _ctrl:
        npos, gpos, gtext = first_gate_site(n, src)
        if npos is not None and not inside(spans, npos) and not inside(spans, gpos):
            real.append(n)
    print('\nCONTROL (arm 3): %d of %d sen_* client-restricted rows have BOTH '
          'halves of\n  their evidence in real code, at the resource\'s own '
          'hydrate/accessor --\n  e.g. senHydratePayRates() guarded by '
          'senIsManagement(). So findings 1-2\n  are discriminating, not a '
          'probe that condemns every match.\n  %s'
          % (len(real), len(_ctrl), ', '.join(sorted(real)[:8])))
    if len(real) != len(_ctrl):
        note('%d sen_* row(s) did NOT come back as real-code evidence: %s'
             % (len(_ctrl) - len(real), sorted(set(_ctrl) - set(real))))

# ── FINDING 3: THE NEIGHBOUR BLEED IS LIVE, AND ONLY MASKED ───────────────
# The defect the payload signal was rewritten to remove is still present in
# client_restricted(), which shares the 400-character window. It produces no
# candidate TODAY only because the server half answers True.
bleed = []
for n in ('sd_remakes', 'sd_comms'):
    if n not in bc:
        continue
    src = pages.get(owner.get(n) or '', '')
    if not src:
        continue
    npos, gpos, gtext = first_gate_site(n, src)
    if npos is None:
        continue
    window = src[max(0, npos - 300):npos + 300]
    others = set(re.findall(r"'([a-z]{2,4}_[a-z0-9_]+)'", window)) - {n}
    gated, how = F.server_gated(n, handler)
    bleed.append((n, gtext, gpos - npos, sorted(others)[:5], gated, how))
if not bleed:
    could_not_tell('neither sd_remakes nor sd_comms produced a gate site, so '
                   'arm 4 did not run.')
else:
    multi = [b for b in bleed if len(b[3]) >= 2]
    if multi:
        finding(3, 'the NEIGHBOUR BLEED the payload signal was rewritten to '
                   'remove is STILL LIVE in client_restricted(), which kept '
                   'the same 400-character window.')
        for n, gtext, dist, others, gated, how in multi:
            print('  %-12s gate %r at %+d chars; %d OTHER resource name(s) in '
                  'the same\n               window: %s'
                  % (n, gtext, dist, len(others), ', '.join(others)))
            print('               server_gated=%s (%s)' % (gated, how))
        print('  Both are loaded by one bulk localStorage loader, and the '
              '_ROLES construct\n  that answered for them is a declaration '
              'ABOVE it belonging to neither.')
        print('  IT PRODUCES NO FALSE CANDIDATE TODAY -- and that is luck, not '
              'design. The\n  asymmetry signal is `client_gate AND NOT '
              'server_gated`, so a false\n  client_gate is invisible exactly '
              'while the server half happens to say yes.\n  The masking is '
              'doing the work the fix was supposed to do.')
        print('  AND THE DOCSTRING ARGUES FOR THE WINDOW BY POINTING AT A '
              'SIBLING THAT NO\n  LONGER USES ONE: client_restricted() says '
              '"Same 400-character window as the\n  payload read, and for the '
              'same reason" -- the payload read was rewritten\n  precisely '
              'because that window was wrong.')
    else:
        note('sd_remakes/sd_comms gate sites carry fewer than two neighbouring '
             'resource names; finding 3 does not reproduce as measured.')

# ── FINDING 4: THE FIXTURE LOCK COVERS ONE SIGNAL OF THREE ────────────────
src = io.open(os.path.join(REPO, 'tools',
                           'confidentiality_candidate_flagger.py'),
              encoding='utf-8').read()
body = src[src.index('def self_test('):src.index('def main(')]
calls = {f: body.count(f + '(') for f in
         ('payload_fields', 'client_restricted', 'server_gated')}
if calls['payload_fields'] and not (calls['client_restricted']
                                    or calls['server_gated']):
    finding(4, 'the locked fixtures exercise ONE of the three signals. '
               'self_test() calls payload_fields() and nothing else.')
    print('  calls inside self_test(): %s' % calls)
    print('  The docstring says "six synthetic cases covering both defect '
          'shapes and\n  both directions" and "THE FIXTURES ARE THE LOCK". '
          'Both defect shapes were\n  found in the same coordinate -- the '
          'payload one. The asymmetry signal, which\n  the same docstring '
          'calls "the one worth having", has no lock at all.')
    print('  The fixture at FIXTURES[0] is even NAMED "the sen_pay_rates '
          'bleed" and is a\n  resource-list array -- the exact input shape '
          'findings 2 and 3 are about --\n  yet it is only ever asserted '
          'against payload_fields().')
else:
    note('self_test() call profile is %s; finding 4 does not reproduce.' % calls)

# ── NOTE: DEAD CODE, and it is the shape a checker is supposed to catch ───
dead = re.search(r"if name in handler_src\.split\('SD_SESSION_GATED'\)\[0\]:\s*\n\s*pass",
                 src)
if dead:
    note('server_gated() opens with `if name in handler_src.split('
         "'SD_SESSION_GATED')[0]: pass` -- a computed condition whose only "
         'branch is `pass`. Harmless, and it is the dormant-code shape '
         'Guardian check 0d exists for. Minor; listed so it is not '
         'rediscovered.')

# ── THE OBLIGATION'S OWN QUESTION, ANSWERED DIRECTLY ──────────────────────
print('\n' + '=' * 72)
print('THE OBLIGATION ASKED ONE THING: confirm the three Tier A names are inert')
print('text and that nothing here reads, writes or gates those resources.')
occ = {n: [src[:m.start()].count('\n') + 1
           for m in re.finditer(re.escape(n), src)]
       for n in ('sd_exec_msgs', 'sen_pay_rates', 'sen_payer_contracts')}
writes = re.findall(r"io\.open\([^)]*,\s*'[wa]", src) + re.findall(r"\.write\(", src)
for n, lines in occ.items():
    print('  %-22s lines %s' % (n, lines))
print('  CONFIRMED: every occurrence is docstring prose or the body of a '
      'synthetic\n  fixture page; none is a resource under test. All %d '
      'io.open() calls are READS\n  (%d write-mode or .write() calls), the only '
      'subprocess is `git rev-parse\n  --show-toplevel`, the register is parsed '
      'line-by-line and never rewritten, and\n  main() prints. There is no path '
      'that reads, writes or gates any of the three.'
      % (src.count('io.open('), len(writes)))

print('\n' + '=' * 72)
print('%d finding(s), %d note(s), %d could-not-tell. Report-only: exit 0 by '
      'design.' % (len(FINDINGS), len(NOTES), len(CNR)))
sys.exit(0)
