# OWNER: hank
"""gate_parity_check.py -- do SIBLING ACTIONS on the same resource, in the same
handler file, enforce the same caller gates?

    python tools/gate_parity_check.py
    python tools/gate_parity_check.py --file api/sd-data.js
    python tools/gate_parity_check.py --json
    python tools/gate_parity_check.py --selftest

── THE DEFECT IT IS BUILT FROM, AND IT IS A REAL ONE ─────────────────────────
H1 #877, fixed 2026-10-05 in `api/sd-data.js`. `resource === 'alf_family_contacts'`
has three actions. `action === 'read'` resolved a role set (ALF_FAMILY_READ_ROLES)
AND the caller's resident assignment from `alf_clients`, and 403'd a resident that
was not theirs. `action === 'family_mar'`, sixty lines below it IN THE SAME BLOCK,
did NEITHER -- it checked the family contact's CONSENT and shipped that resident's
medication administration record. Any authenticated session on the licence,
including a `med_aide` with no resident assigned at all, could pass any
`contact_id` and read the MAR.

WHY NO EXISTING CHECK SAW IT. Every control on this platform asks about ONE
branch: does it have a session check, does it scope by licence, does it refuse
cleanly. All of those answered YES for `family_mar`, because a check WAS present
-- `familyMarView()` -- it was just answering a different question. The missing
question is COMPARATIVE: two branches disclose the SAME resource and only one of
them asks who is asking. Nothing on this platform compared two branches to each
other, so the asymmetry was invisible to every automated layer and had to be
found by a human reading the handler.

── WHAT IT COMPARES, AND WHAT IT DELIBERATELY DOES NOT ───────────────────────
It flags a (file, resource) group where TWO OR MORE actions DISCLOSE the resource
and they disagree on whether a ROLE gate or an ASSIGNMENT gate is enforced.

A SHARED PRELUDE COUNTS FOR EVERY ACTION UNDER IT, and getting this wrong would
have made the tool useless. The real shape is an outer `if (resource === 'X' &&
(action === 'a' || action === 'b'))` whose first lines verify the session for
both, then inner `if (action === 'a')` blocks. A gate in the prelude genuinely
covers both siblings; only the inner halves are compared. Without this the tool
would flag every multi-action resource on the platform and be switched off in a
day.

WRITES ARE NOT COMPARED AGAINST READS. A write that refuses more than a read is
correct and extremely common -- management-only writes beside care-role reads are
the design, not a defect. Only branches that DISCLOSE are compared, and
disclosure is read off the handler: a PostgREST `select=` fetch on the resource,
or a 200 response carrying `data`.

IT IS A REPORT, NOT A GATE, and the honest reason is that the comparison is
lexical. It cannot tell a gate reached through a helper from no gate at all, and
it would refuse pushes on cases a human would wave through. Exit 1 means "look at
these"; it does not mean "this is a defect".

── WHAT IT CANNOT SEE, NAMED RATHER THAN IMPLIED ─────────────────────────────
1. A gate implemented inside a called function. `foo(session)` that refuses is
   invisible; this reads text, not a call graph. Direction of the error is
   FALSE POSITIVE -- it will say "no gate" when one exists one frame away.
2. A gate in a different FILE (middleware, a wrapper). Same direction.
3. Two actions that disclose DIFFERENT subsets of one resource, where a weaker
   gate is correct because the projection is narrower. #877's own `read` does
   exactly that with ALF_FAMILY_NARROW_COLS -- so a flagged pair may be a
   deliberate tiering. The finding says WHAT DIFFERS and never that it is wrong.
4. Resources dispatched through a generic map (`SDN_RESOURCES[resource]`) are
   read as ONE unit per action, because that is what the code is: one branch
   serving many resources. An asymmetry BETWEEN two generic maps is not checked.
5. Anything in a file it was not pointed at. The default file list is printed on
   every run, because a silent universe is how a sweep reports "clean" for a file
   it never opened.

── FAIL CLOSED ───────────────────────────────────────────────────────────────
An unreadable target file exits 2 COULD NOT RUN and says which file. It is never
folded into "no findings" -- PR 1.11.
"""
import io
import json
import os
import re
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The handler files that dispatch on (resource, action). Printed on every run.
DEFAULT_FILES = [
    'api/sd-data.js',
]

# .2 -- a FIXTURE WAS DELETED, so the criteria changed and the stamp moves.
# A lock that grows or shrinks without the version moving makes two different
# locks indistinguishable in a past report.
# .3 -- a whole second GROUPING was added (cross-resource), so the criteria
# changed and the stamp moves.
CRITERIA_VERSION = '2026-10-06.3'

# ── THE THREE SIGNALS ───────────────────────────────────────────────────────
# ROLE: the session's role is CONSULTED. `session.role` is the only way this
# platform asks the question, in every spelling it uses -- the usual form is
# `!!SOME_ROLES[session.role]`.
#
# `roleSet(` WAS IN THIS PATTERN AND HAD TO COME OUT, and the removal is the
# single reason this tool catches the defect it was built from. On the REAL
# pre-fix handler the set is DECLARED in the shared prelude --
# `const ALF_FAMILY_READ_ROLES = roleSet({ owner: true, ... })` at
# api/sd-data.js:11501, above both action branches -- and CONSULTED inside
# `read` only. With `roleSet(` as a role signal the prelude lit up, both
# siblings inherited role=True, and the asymmetry vanished: the ablation
# against the pre-fix file at 05cbc74d flagged THREE groups and
# `alf_family_contacts` was not one of them.
#
# A DECLARATION IS NOT A GATE. That is the distinction, and the fixture that
# first passed this tool did not contain it -- it put the declaration inside
# the gated branch, which no real handler in this file does. Fixture A3 is the
# production shape and exists so this cannot regress silently.
ROLE_RE = re.compile(r'session\.role')
# ASSIGNMENT: the platform has exactly one spelling for "is this caller's own
# row", and it is a column name, so it is safe to match literally.
ASSIGN_RE = re.compile(r'assigned_employee_id')
# DISCLOSURE: a PostgREST read (`select=`) on this resource, or a 200 answer
# carrying `data`. Either one means the branch hands data back.
SELECT_RE = re.compile(r'select=')
DATA_200_RE = re.compile(r"status\(200\)\.json\(\s*\{[^}]*\bdata\b")
# ── MUTATION, AND THIS LINE IS WHY THE FIRST LIVE RUN WAS NOISE ────────────
# The disclosure test alone marked almost every WRITE branch as disclosing,
# because an upsert on this platform carries `Prefer: return=representation`
# and answers `res.status(200).json({ ok: true, data: rows[0].data })`. So the
# tool compared writes against reads after the docstring promised it would
# not, and the first live run produced 36 groups of which most were
# "the write refuses more than the read" -- the design, reported as a finding.
#
# THE SELFTEST DID NOT CATCH IT, and that is the more useful half: fixture B2's
# write answered a bare `{ ok: true }`, which no real write branch in this file
# does. A fixture that is cleaner than production tests a handler that does not
# exist. B2 now returns a representation, the way the real ones do.
MUTATE_RE = re.compile(r"method:\s*'(?:POST|PATCH|PUT|DELETE)'|'rpc/")

# ── THE TABLE A BRANCH ACTUALLY READS, WHICH IS NOT ALWAYS ITS OWN RESOURCE ──
# Added 2026-10-06 for #894, the third instance of this class and the first the
# tool could not see. `alf_compliance_rules`/`evaluate` is keyed on one resource
# and reads `alf_staff_credentials`, the table a DIFFERENT branch owns and gates
# -- so grouping by the dispatch resource alone compared it against nothing.
#
# Every PostgREST read on this platform is spelled `rest('<table>?...')`, which
# is as lexically available as `select=` already was. The extension is a second
# GROUPING, not a second parser.
TABLE_RE = re.compile(r"rest\(\s*'([a-z0-9_]+)\?")


def read(path):
    """utf-8 with replacement. A decode error must not be a finding."""
    return io.open(path, encoding='utf-8', errors='replace').read()


def block_end(src, open_brace_idx):
    """Index just past the `}` matching the `{` at open_brace_idx.

    STRINGS AND COMMENTS ARE SKIPPED, because a brace inside a message or a URL
    would end the block early and silently shrink what the tool compared -- the
    same failure mode `_anchor_range()` was flagged for on the coding-rule gate.
    Returns len(src) if the brace never closes, which is a truncation the caller
    reports rather than guesses around.
    """
    i = open_brace_idx
    depth = 0
    n = len(src)
    while i < n:
        c = src[i]
        if c == '/' and i + 1 < n:
            nxt = src[i + 1]
            if nxt == '/':
                j = src.find('\n', i)
                i = n if j == -1 else j + 1
                continue
            if nxt == '*':
                j = src.find('*/', i + 2)
                i = n if j == -1 else j + 2
                continue
        if c in '\'"`':
            q = c
            i += 1
            while i < n:
                if src[i] == '\\':
                    i += 2
                    continue
                if src[i] == q:
                    i += 1
                    break
                i += 1
            continue
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return n


def line_of(src, idx):
    return src.count('\n', 0, idx) + 1


# An outer dispatch header. Three real spellings, all present in api/sd-data.js:
#   if (resource === 'x' && action === 'read')
#   if (resource === 'x' && (action === 'a' || action === 'b'))
#   if (MAP[resource] && action === 'read')
OUTER_RE = re.compile(
    r"if\s*\(\s*(?:resource\s*===\s*'(?P<res>[a-z0-9_]+)'"
    r"|(?P<map>[A-Z][A-Z0-9_]*)\s*\[\s*resource\s*\])"
    r"(?P<rest>[^{]*)\{", re.S)
ACTION_IN_RE = re.compile(r"action\s*===\s*'([a-z0-9_]+)'")
INNER_RE = re.compile(r"if\s*\(\s*action\s*===\s*'(?P<act>[a-z0-9_]+)'\s*\)\s*\{")


def units(path, src):
    """Every (resource, action) disclosure unit in one file.

    Each unit's text is its own body PLUS the shared prelude of the outer block
    it sits in -- see the module docstring for why the prelude has to count.
    """
    out = []
    for m in OUTER_RE.finditer(src):
        res = m.group('res') or ('%s[resource]' % m.group('map'))
        acts = ACTION_IN_RE.findall(m.group('rest') or '')
        brace = m.end() - 1
        end = block_end(src, brace)
        body = src[brace:end]
        inners = [(im.group('act'), im.start(), block_end(body, im.end() - 1))
                  for im in INNER_RE.finditer(body)]
        if inners:
            # ── THE PRELUDE IS PER-ACTION, NOT ONE SHARED STRING, and the
            # first version of this function got it wrong in a way that made
            # the tool miss the exact defect it was built from.
            #
            # Every inner action block ends in `return`, so for action N the
            # code that actually runs first is: everything in the outer body
            # BEFORE block N, minus blocks 1..N-1 (those were skipped). The
            # tail AFTER the last inner block belongs to NO action branch --
            # it is the fall-through, reached only by an action that matched
            # none of them.
            #
            # api/sd-data.js:11671 is why this matters. The WRITE path of
            # alf_family_contacts is that fall-through, and its gate --
            # `if (!ALF_MANAGEMENT_ROLES[session.role])` -- sits in the outer
            # body AFTER the family_mar block. Folding the whole body into one
            # shared prelude handed the write's role gate to `read` AND to
            # `family_mar`, both read role=True, the asymmetry disappeared, and
            # the ablation against the pre-fix file did not flag #877 at all.
            for idx, (a, s, e) in enumerate(inners):
                prelude = ''
                cut = 0
                for _a2, s2, e2 in inners[:idx]:
                    prelude += body[cut:s2]
                    cut = e2
                prelude += body[cut:s]
                out.append({
                    'file': path, 'resource': res, 'action': a,
                    'line': line_of(src, brace + s),
                    'text': prelude + body[s:e],
                    'own': body[s:e],
                    'shape': 'inner',
                })
        else:
            # A single-action outer block. If the header names exactly one
            # action, that is the unit; if it names several with no inner
            # branches, the whole body serves all of them identically and there
            # is no asymmetry to find.
            if len(acts) == 1:
                out.append({
                    'file': path, 'resource': res, 'action': acts[0],
                    'line': line_of(src, m.start()),
                    'text': body, 'own': body, 'shape': 'flat',
                })
    return out


COMMENT_LINE_RE = re.compile(r'^\s*(?://|\*|/\*)', re.M)


def decomment(text):
    """Drop whole-line comments before any signal is read off the text.

    PR 1.2 -- grep cannot tell code from text that DESCRIBES code -- and this
    handler is the worst case for it, because its comments quote the very
    identifiers the signals match. `api/sd-data.js:11485` is a comment reading
    *"alf_clients.assigned_employee_id, which is the same source"*, inside the
    alf_family_contacts prelude: with comments left in, every action under that
    block reported an assignment gate it did not have.

    WHOLE-LINE ONLY, on purpose. A trailing `// ...` after real code cannot
    manufacture a signal the code does not already carry, and stripping inline
    comments properly means a tokenizer. The residual error direction is a
    FALSE POSITIVE on a trailing comment that names a gate the line does not
    enforce, which is the safe direction for a report-only check.
    """
    return '\n'.join(l for l in text.split('\n')
                     if not COMMENT_LINE_RE.match(l))


def classify(u):
    t = decomment(u['text'])
    own = decomment(u['own'])
    u['role'] = bool(ROLE_RE.search(t))
    u['assign'] = bool(ASSIGN_RE.search(t))
    # The unit's OWN body decides whether it mutates -- not the prelude,
    # which is shared and may legitimately contain a write for a sibling.
    u['mutates'] = bool(MUTATE_RE.search(own))
    u['discloses'] = bool(
        (SELECT_RE.search(t) or DATA_200_RE.search(t)) and not u['mutates'])
    # TABLES READ FROM THE UNIT'S OWN BODY, NOT THE PRELUDE. A prelude read is
    # shared by every sibling and so cannot be an asymmetry between them; a
    # read in one branch and not another is exactly what this is looking for.
    u['tables'] = sorted(set(TABLE_RE.findall(own)))
    return u


def findings(all_units):
    """Groups where two or more DISCLOSING siblings disagree on a gate."""
    groups = {}
    for u in all_units:
        groups.setdefault((u['file'], u['resource']), []).append(u)
    out = []
    for (f, res), us in sorted(groups.items()):
        disc = [u for u in us if u['discloses']]
        if len(disc) < 2:
            continue
        roles = set(u['role'] for u in disc)
        assigns = set(u['assign'] for u in disc)
        if len(roles) == 1 and len(assigns) == 1:
            continue
        gated = [u for u in disc if u['role'] or u['assign']]
        bare = [u for u in disc if not (u['role'] or u['assign'])]
        out.append({
            'file': f, 'resource': res,
            'differs_on': ([] if len(roles) == 1 else ['role'])
                          + ([] if len(assigns) == 1 else ['assignment']),
            'gated': [{'action': u['action'], 'line': u['line'],
                       'role': u['role'], 'assign': u['assign']} for u in gated],
            'ungated': [{'action': u['action'], 'line': u['line'],
                         'role': u['role'], 'assign': u['assign']} for u in bare],
            'all': [{'action': u['action'], 'line': u['line'],
                     'role': u['role'], 'assign': u['assign']} for u in disc],
        })
    return out


def cross_findings(all_units):
    """Branches on DIFFERENT resources that read ONE table and disagree on a gate.

    THIS IS #894 AND THE TOOL COULD NOT SEE IT BEFORE. `findings()` groups by
    the resource a branch is DISPATCHED on; this groups by the table a branch
    READS. `alf_compliance_rules`/`evaluate` read `alf_staff_credentials` with
    no role gate while `alf_staff_credentials`/`read` scoped every narrow role
    to its own row -- two code paths, one table, different answers, and nothing
    compared them.

    ONLY CROSS-RESOURCE PAIRS ARE REPORTED HERE. A same-resource disagreement is
    already `findings()`' job and reporting it twice would make one defect look
    like two.

    THE OWNING BRANCH IS NAMED WHEN THERE IS ONE -- the unit whose dispatch
    resource IS the table -- because the owner's gate is the one a reader should
    compare against rather than an arbitrary other caller.
    """
    by_table = {}
    for u in all_units:
        if not u['discloses']:
            continue
        for tbl in u['tables']:
            by_table.setdefault((u['file'], tbl), []).append(u)
    out = []
    for (f, tbl), us in sorted(by_table.items()):
        if len({u['resource'] for u in us}) < 2:
            continue
        roles = set(u['role'] for u in us)
        assigns = set(u['assign'] for u in us)
        if len(roles) == 1 and len(assigns) == 1:
            continue
        owner = [u for u in us if u['resource'] == tbl]
        out.append({
            'file': f, 'table': tbl,
            'owner_branch': ('%s/%s' % (owner[0]['resource'], owner[0]['action'])
                             if owner else None),
            'differs_on': ([] if len(roles) == 1 else ['role'])
                          + ([] if len(assigns) == 1 else ['assignment']),
            'readers': [{'resource': u['resource'], 'action': u['action'],
                         'line': u['line'], 'role': u['role'],
                         'assign': u['assign'],
                         'owns_table': u['resource'] == tbl} for u in us],
        })
    return out


# ── FIXTURES. The pre-fix #877 shape must FLAG, the post-fix shape must NOT,
#    and the three ways a correct handler can look different must NOT either.
#    Locked here rather than measured on the live file, because the live file is
#    now FIXED and a check validated only against clean code has been validated
#    against nothing.
FIX_877_AFTER = """
    if (resource === 'alf_family_contacts' &&
        (action === 'read' || action === 'write' || action === 'family_mar')) {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairncare');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION' } }); return; }
      const ALF_FAMILY_READ_ROLES = roleSet({ owner: true, billing: true, nursing: true });
      if (action === 'read') {
        const famBroad = !!ALF_FAMILY_READ_ROLES[session.role];
        if (!famBroad) {
          const ar = await fetch(rest('alf_clients?assigned_employee_id=eq.' + x + '&select=client_id'));
        }
        const cr = await fetch(rest('alf_family_contacts?select=' + famCols));
        res.status(200).json({ ok: true, data: rows });
        return;
      }
      if (action === 'family_mar') {
        const marBroad = !!ALF_FAMILY_READ_ROLES[session.role];
        if (!marBroad) {
          const mar_ar = await fetch(rest('alf_clients?assigned_employee_id=eq.' + x + '&select=client_id'));
        }
        const cr = await fetch(rest('alf_family_contacts?contact_id=eq.' + id + '&select=' + famCols));
        res.status(200).json({ ok: true, data: view });
        return;
      }
    }
"""

# ── THE PRODUCTION SHAPE, AND THE ONLY PRE-FIX FIXTURE THERE IS ────────────
# Copied from the real api/sd-data.js at 05cbc74d, trimmed: the role SET is
# DECLARED in the shared prelude (`:11501`) and CONSULTED inside `read` only.
#
# THERE USED TO BE A SECOND, TIDIER FIXTURE HERE AND IT IS DELETED RATHER THAN
# KEPT ALONGSIDE THIS ONE (2026-10-06). It put the declaration INSIDE the gated
# branch, which no handler in api/sd-data.js does -- and because it was the arm
# that ran first, it PASSED while the tool was blind to the real defect. The
# ablation against the actual pre-fix file flagged three groups and
# alf_family_contacts was not one of them.
#
# A FIXTURE NO REAL CODE MATCHES IS A TEST OF A SYSTEM THAT DOES NOT EXIST, and
# keeping it beside the true one would have left the green arm that misled this
# tool in place as evidence. Two of this tool's three defects were exactly this
# shape; the third (fixture B2's bare `{ ok: true }` write) was corrected the
# same way, by making the fixture carry what every real write here carries.
FIX_877_BEFORE = """
    if (resource === 'alf_family_contacts' &&
        (action === 'read' || action === 'write' || action === 'family_mar')) {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairncare');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION' } }); return; }
      const ALF_FAMILY_READ_ROLES = roleSet({ owner: true, billing: true, nursing: true });
      const ALF_FAMILY_NARROW_COLS = 'contact_id,resident_id,name';
      if (action === 'read') {
        const famBroad = !!ALF_FAMILY_READ_ROLES[session.role];
        if (!famBroad) {
          const ar = await fetch(rest('alf_clients?assigned_employee_id=eq.' + x + '&select=client_id'));
        }
        const cr = await fetch(rest('alf_family_contacts?select=' + famCols));
        res.status(200).json({ ok: true, data: rows });
        return;
      }
      if (action === 'family_mar') {
        const cr = await fetch(rest('alf_family_contacts?contact_id=eq.' + id + '&select=' + famCols));
        const view = famLib.familyMarView({ contact: contact, entries: entries });
        res.status(200).json({ ok: true, data: view });
        return;
      }
    }
"""

# ── #894: ONE TABLE, TWO RESOURCES, TWO ANSWERS. Trimmed from the real
# api/sd-data.js before the 2026-10-06 fix. `alf_compliance_rules`/`evaluate` is
# dispatched on one resource and READS `alf_staff_credentials`, which a different
# branch owns and gates. Grouping by the dispatch resource compared it against
# nothing at all, which is why the tool built from #877 could not see #894.
CROSS_894_BEFORE = """
    if (resource === 'alf_compliance_rules' && action === 'evaluate') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairncare');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION' } }); return; }
      const cr = await fetch(rest('alf_staff_credentials?license_hash=eq.' + enc(licHash)
        + '&record_type=eq.training_hours&select=staff_id,data'), { headers });
      res.status(200).json({ ok: true, data: result });
      return;
    }
    if (resource === 'alf_staff_credentials' && action === 'read') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairncare');
      const r = await fetch(rest('alf_staff_credentials?license_hash=eq.' + enc(licHash)
        + '&select=entry_id,staff_id,data'), { headers });
      if (!ALF_CRED_READ_ROLES[session.role]) {
        out = out.filter((x) => x.staff_id === session.employee_id);
      }
      res.status(200).json({ ok: true, data: out });
      return;
    }
"""

CROSS_894_AFTER = """
    if (resource === 'alf_compliance_rules' && action === 'evaluate') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairncare');
      if (!session) { res.status(401).json({ error: { code: 'NO_SESSION' } }); return; }
      const cr = await fetch(rest('alf_staff_credentials?license_hash=eq.' + enc(licHash)
        + '&record_type=eq.training_hours&select=staff_id,data'), { headers });
      if (!ALF_CRED_READ_ROLES[session.role]) {
        opts.staff = (opts.staff || []).filter(
          (x) => String(x.staff_id) === String(session.employee_id));
      }
      res.status(200).json({ ok: true, data: result });
      return;
    }
    if (resource === 'alf_staff_credentials' && action === 'read') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairncare');
      const r = await fetch(rest('alf_staff_credentials?license_hash=eq.' + enc(licHash)
        + '&select=entry_id,staff_id,data'), { headers });
      if (!ALF_CRED_READ_ROLES[session.role]) {
        out = out.filter((x) => x.staff_id === session.employee_id);
      }
      res.status(200).json({ ok: true, data: out });
      return;
    }
"""

SHARED_PRELUDE_OK = """
    if (resource === 'zz_thing' && (action === 'read' || action === 'summary')) {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'app');
      if (!ZZ_ROLES[session.role]) { res.status(403).json({ error: {} }); return; }
      if (action === 'read') {
        const r = await fetch(rest('zz_thing?select=data'));
        res.status(200).json({ ok: true, data: rows });
        return;
      }
      if (action === 'summary') {
        const r = await fetch(rest('zz_thing?select=data'));
        res.status(200).json({ ok: true, data: sum });
        return;
      }
    }
"""

WRITE_IS_NOT_A_READ = """
    if (resource === 'zz_other' && (action === 'read' || action === 'write')) {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'app');
      if (action === 'read') {
        const r = await fetch(rest('zz_other?select=data'));
        res.status(200).json({ ok: true, data: rows });
        return;
      }
      if (action === 'write') {
        if (!ZZ_WRITE_ROLES[session.role]) { res.status(403).json({ error: {} }); return; }
        const r = await fetch(rest('zz_other?on_conflict=license_hash,zz_id'), {
          method: 'POST',
          headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
          body: JSON.stringify(b)
        });
        res.status(200).json({ ok: true, data: rows[0].data });
        return;
      }
    }
"""

BRACE_IN_STRING = """
    if (resource === 'zz_brace' && (action === 'read' || action === 'peek')) {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'app');
      if (action === 'read') {
        const msg = 'a } inside a string must not end this block';
        const b = !!ZZ_ROLES[session.role];
        const r = await fetch(rest('zz_brace?select=data'));
        res.status(200).json({ ok: true, data: rows });
        return;
      }
      if (action === 'peek') {
        const b = !!ZZ_ROLES[session.role];
        const r = await fetch(rest('zz_brace?select=data'));
        res.status(200).json({ ok: true, data: rows });
        return;
      }
    }
"""


def selftest():
    print('gate_parity_check selftest -- criteria %s\n' % CRITERIA_VERSION)
    cases = [

        ('A1. THE REAL PRE-FIX #877 SHAPE IS FLAGGED -- the role SET DECLARED '
         'in the SHARED PRELUDE and CONSULTED inside `read` only, which is what '
         'the handler actually looked like. The earlier fixture put that '
         'declaration inside the gated branch, matched no real handler, PASSED, '
         'and left this tool blind to the defect it was built from; it is '
         'deleted rather than kept beside this one',
         FIX_877_BEFORE, True, 'alf_family_contacts'),
        ('A2. the POST-FIX shape is NOT flagged. WITHOUT THIS ARM the check '
         'could flag every multi-action resource and A1 would still pass',
         FIX_877_AFTER, False, 'alf_family_contacts'),
        ('B1. a gate in the SHARED PRELUDE counts for both siblings and is NOT '
         'flagged -- the single most common correct shape on this platform',
         SHARED_PRELUDE_OK, False, 'zz_thing'),
        ('B2. a WRITE that refuses more than its sibling read is NOT flagged -- '
         'management-only writes beside care-role reads are the design',
         WRITE_IS_NOT_A_READ, False, 'zz_other'),
        # BOTH actions here are gated identically; the ONLY difference is that
        # `read` has a `}` inside a string ABOVE its role gate. A parser that
        # ends the block on that brace drops the gate out of the unit, read
        # looks ungated, and the pair is flagged -- a false positive the parser
        # manufactured. The first version of this fixture gated only `read`,
        # so it was testing the comparison and not the parser, and it failed
        # for the right reason: a flag WAS correct there.
        ('C1. a `}` inside a STRING does not end a block early. Both actions '
         'carry the same gate, so any flag here is a false positive the parser '
         'invented out of a brace in a message',
         BRACE_IN_STRING, False, 'zz_brace'),
    ]
    npass = nfail = 0
    # ── THE CROSS-RESOURCE ARMS, added 2026-10-06. They use their own runner
    #    because the verdict comes from cross_findings(), a different grouping,
    #    and folding them into the same loop would let a same-resource flag
    #    satisfy a cross-resource arm.
    cross_cases = [
        ('X1. #894 IS FLAGGED: one table read by TWO resources, gated in the '
         'owning branch and not in the other. This is the shape the tool built '
         'from #877 could not see, because it grouped by the resource a branch '
         'is DISPATCHED on and never by the table a branch READS',
         CROSS_894_BEFORE, True, 'alf_staff_credentials'),
        ('X2. ...and the POST-FIX shape is NOT flagged. WITHOUT THIS ARM the '
         'cross pass could flag every table two branches happen to touch and '
         'X1 would still pass',
         CROSS_894_AFTER, False, 'alf_staff_credentials'),
        ('X3. a SAME-resource disagreement is NOT reported by the cross pass -- '
         'findings() already owns it, and reporting one defect twice makes it '
         'look like two',
         FIX_877_BEFORE, False, 'alf_family_contacts'),
    ]
    for label, src, want_flag, tbl in cross_cases:
        us = [classify(u) for u in units('fixture.js', src)]
        fs = [f for f in cross_findings(us) if f['table'] == tbl]
        got = bool(fs)
        if got == want_flag:
            npass += 1
            print('  ok   ' + label)
        else:
            nfail += 1
            print('  FAIL ' + label)
            print('       wanted flag=%s got flag=%s; cross=%s'
                  % (want_flag, got,
                     [(x['table'], x['differs_on']) for x in cross_findings(us)]))

    for label, src, want_flag, res in cases:
        us = [classify(u) for u in units('fixture.js', src)]
        fs = [f for f in findings(us) if f['resource'] == res]
        got = bool(fs)
        if got == want_flag:
            npass += 1
            print('  ok   ' + label)
        else:
            nfail += 1
            print('  FAIL ' + label)
            print('       wanted flag=%s got flag=%s; units=%s'
                  % (want_flag, got,
                     [(u['action'], u['role'], u['assign'], u['discloses'])
                      for u in us if u['resource'] == res]))

    # A UNIT-DETECTION ARM, because every arm above would also pass if the
    # parser found NOTHING at all in the clean fixtures. Zero units is not a
    # clean verdict.
    us = [classify(u) for u in units('fixture.js', FIX_877_AFTER)]
    if len(us) == 2 and all(u['discloses'] for u in us):
        npass += 1
        print('  ok   D1. the parser actually FINDS the two disclosing units in '
              'the clean fixture -- without this arm, "no findings" and "parsed '
              'nothing" are the same answer')
    else:
        nfail += 1
        print('  FAIL D1. the clean fixture must yield 2 disclosing units, got '
              '%d (%s)' % (len(us), [(u['action'], u['discloses']) for u in us]))

    print('\n%d passed, %d failed' % (npass, nfail))
    return 1 if nfail else 0


def main(argv):
    if '--selftest' in argv:
        return selftest()
    as_json = '--json' in argv
    files = []
    if '--file' in argv:
        files = [argv[argv.index('--file') + 1]]
    else:
        files = list(DEFAULT_FILES)

    all_units = []
    for rel in files:
        p = os.path.join(REPO, rel)
        if not os.path.isfile(p):
            print('COULD NOT RUN: %s does not exist. This is NOT "no findings" '
                  '-- the file this check is about was never opened.' % rel)
            return 2
        try:
            src = read(p)
        except Exception as e:                                   # noqa: BLE001
            print('COULD NOT RUN: %s is unreadable (%s: %s). NOT a pass.'
                  % (rel, type(e).__name__, e))
            return 2
        all_units.extend(classify(u) for u in units(rel, src))

    fs = findings(all_units)
    xs = cross_findings(all_units)
    if as_json:
        print(json.dumps({'criteria': CRITERIA_VERSION, 'files': files,
                          'units': len(all_units), 'findings': fs,
                          'cross_findings': xs}, indent=1))
        return 1 if (fs or xs) else 0

    print('GATE PARITY -- sibling actions on one resource -- criteria %s'
          % CRITERIA_VERSION)
    print('FILES READ (printed because a silent universe reports clean for a '
          'file it never opened):')
    for rel in files:
        print('    %s' % rel)
    print('  disclosure units found : %d' % len(all_units))
    print('  resources with >1      : %d'
          % len([1 for k, v in _groups(all_units).items()
                 if len([u for u in v if u['discloses']]) > 1]))
    print('')

    if not fs and not xs:
        print('No (file, resource) group has two disclosing actions that '
              'disagree on a role or assignment gate, and no table is read by '
              'two resources that disagree.')
        print('')
        _limits()
        return 0

    if xs:
        print('CROSS-RESOURCE -- one TABLE read by branches on DIFFERENT '
              'resources, disagreeing on a gate (#894 is this shape):')
        for x in xs:
            print('! %s  table %s  differs on: %s%s'
                  % (x['file'], x['table'], ', '.join(x['differs_on']),
                     ('   [owner: %s]' % x['owner_branch'])
                     if x['owner_branch'] else '   [NO branch owns this table]'))
            for r in x['readers']:
                print('    %-34s :%-6d role=%-5s assignment=%-5s%s'
                      % (r['resource'] + '/' + r['action'], r['line'],
                         r['role'], r['assign'],
                         '  <- OWNS THE TABLE' if r['owns_table'] else ''))
            print('')

    for f in fs:
        print('! %s  %s  differs on: %s'
              % (f['file'], f['resource'], ', '.join(f['differs_on'])))
        for u in f['all']:
            print('    action %-14s :%-6d role=%-5s assignment=%s'
                  % (u['action'], u['line'], u['role'], u['assign']))
        print('')
    print('%d same-resource group(s) and %d cross-resource table(s) flagged. '
          'REPORT ONLY -- a flagged pair may be a '
          'deliberate tiering (a narrower projection can justify a weaker '
          'gate). The finding says WHAT DIFFERS, never that it is wrong.'
          % (len(fs), len(xs)))
    print('')
    _limits()
    return 1


def _groups(all_units):
    g = {}
    for u in all_units:
        g.setdefault((u['file'], u['resource']), []).append(u)
    return g


def _limits():
    print('LIMITS, on every run rather than in a document nobody opens:')
    print('  * LEXICAL. A gate reached through a helper or living in another')
    print('    file is invisible, so the error direction is FALSE POSITIVE --')
    print('    it says "no gate" when one may be a frame away.')
    print('  * Generic-map branches (MAP[resource]) are ONE unit per action,')
    print('    because that is what the code is. Asymmetry BETWEEN maps is')
    print('    not checked.')
    print('  * Writes are never compared against reads. A write that refuses')
    print('    more is the design on this platform, not a defect.')
    print('  * A role check that WIDENS reads the same as one that RESTRICTS.')
    print('    rf_claims `read` consults MANAGEMENT_ROLES only to let managers')
    print('    see every row; its siblings do not, and that reads as an')
    print('    asymmetry when it is the opposite of one.')
    print('  * An assignment gate reached through a named helper is invisible.')
    print('    rfAuth.ownsRow(session, claim) is the live example.')
    print('  * CROSS-RESOURCE IS NOW CHECKED (2026-10-06) and was the one')
    print('    limit here that had already cost something: #894 was invisible')
    print('    to the same-resource grouping. A second pass groups by the')
    print('    TABLE a branch READS, taken from rest(table?...). WHAT IT STILL')
    print('    CANNOT SEE: a table reached through a helper that builds the')
    print('    URL, an RPC, or a read in a DIFFERENT FILE -- all three err')
    print('    toward a MISS here rather than a false positive, which is the')
    print('    opposite direction from every other limit above and is the')
    print('    reason this pass is not evidence of absence.')
    print('  MEASURED ON FIRST LIVE RUN, 2026-10-05: 3 groups flagged on')
    print('  api/sd-data.js at HEAD and ALL THREE triaged as correct-by-design')
    print('  (rf_claims, rf_schedule, alf_payer_rules). The same run against')
    print('  the PRE-FIX file flags 4, the extra one being alf_family_contacts')
    print('  -- the defect this was built from. So: it catches the real one,')
    print('  and its current precision on this file is 0 of 3. Both numbers,')
    print('  not one.')


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
