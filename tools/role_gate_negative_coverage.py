"""tools/role_gate_negative_coverage.py -- which role gates would survive being
deleted, because no test ever drives them with a role they exclude?

    python tools/role_gate_negative_coverage.py                    # the SCREEN
    python tools/role_gate_negative_coverage.py --list
    python tools/role_gate_negative_coverage.py --ablate alf_facility   # the PROOF
    python tools/role_gate_negative_coverage.py --baseline   # after a real change

── THE DEFECT THIS EXISTS FOR ──────────────────────────────────────────────
api/sd-data.js's `alf_family_contacts` read had NO role gate at all until
2026-09-26: any authenticated SAIRNcare employee of any role could list every
family contact on the licence with phone, email and the full medication-consent
trail. Its suite, api/sd-data-family-contacts.test.js, was EIGHTEEN GREEN ARMS at
the time, and the reason none of them saw it is one line:

    verifySessionToken: function () { return { employee_id: 'owner-1',
                                               role: opts.role || 'owner' }; }

**EVERY ARM RAN AS `owner`.** The role was a parameter the harness defaulted and
no arm ever varied, so a completely ABSENT gate and a correct one produce
identical output. This tool asks the question those eighteen arms could not:
**if the gate were deleted, would anything go red?**

── WHAT IT MEASURES, AND WHY IT IS NOT "DO THE TESTS MENTION A ROLE" ───────
For each resource branch in api/sd-data.js that tests a role set:

  1. the ALLOWED roles, resolved from the `roleSet({...})` declaration itself --
     not from a list here, which would be a second copy of a fact the file owns;
  2. the EXCLUDED roles, being every role any set declares minus those;
  3. every (resource, role) pair the test suites actually DRIVE.

A gate is reported when a suite drives the resource but NEVER with an excluded
role. That is strictly stronger than "the suite mentions a role": a suite can pass
`role: 'owner'` on every arm, mention FORBIDDEN in a comment, and still be unable
to detect the gate's removal.

── WHAT IT CANNOT DO, AND THE FIRST ONE BIT ME ─────────────────────────────
IT CANNOT TELL A SUITE THAT DRIVES A RESOURCE FROM ONE THAT MENTIONS IT. The
first version matched any quoted lowercase string in a test file, so a resource
named in a COMMENT counted as exercised -- that reported 16 gates instead of 11,
and five of those were mentions. Only a `resource:` or `resource ===` position
counts now, which is the opposite error: a suite driving a resource through a
variable is invisible and its gate will be reported as uncovered. An over-report
is the safe direction here (it asks for an arm that already exists), and it is
stated rather than left for a reader to discover.

IT ALSO CANNOT SEE role gates outside api/sd-data.js -- api/*-auth.js files carry
their own, and this tool says nothing about them -- and it cannot judge whether a
gate is CORRECT. A gate excluding the wrong roles passes here as long as somebody
tests the exclusion it does implement.

── THE DEFAULT PASS IS A SCREEN; --ablate IS THE PROOF ─────────────────────
Three static rules were tried for step 3 and ALL THREE WERE WRONG -- see driven().
The screen over-reports on purpose. `--ablate <resource>` deletes that gate, runs
all 400 suites, and reports CAUGHT or SILENT: the property itself rather than a
pattern correlated with it. Settle any individual gate that way before believing
the screen about it, and never lower the pin on the strength of the screen alone.

A RATCHET, pinned to docs/role-gate-negative-coverage.json. The honest state is well
short of clean by the screen and a check that simply failed would sit permanently red.
**DO NOT WRITE THE CURRENT COUNT HERE** -- a figure in this docstring was `12 of 31`
after the table rule took it to 17, within the same commit that added the rule. The pin
file is the one place it lives; read it. An absent,
unparseable or `uncovered`-less pin is exit 2 COULD NOT TELL, never 0 -- and so is
finding zero role gates at all, because the gate shape moving must not read as
"everything is covered".
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SD = os.path.join(REPO, 'api', 'sd-data.js')
PIN = os.path.join(REPO, 'docs', 'role-gate-negative-coverage.json')

# ── A BRANCH ENDS WHERE THE NEXT ONE BEGINS, NOT AT A CHARACTER COUNT ───────
# THIS WAS `BRANCH_WINDOW = 3000` AND THE PROBE CAUGHT IT. A fixed window from
# `resource === 'x'` reaches into the NEXT branch and swallows ITS role gate, so a
# resource gated on ALF_MANAGEMENT_ROLES was reported as gated on
# `ALF_CARE_ROLES,ALF_MANAGEMENT_ROLES`. Union the two members and the ALLOWED set
# becomes every role, the EXCLUDED set becomes empty, and no test can ever be
# found driving an excluded role -- so the gate is reported uncovered NO MATTER
# WHAT ANY SUITE DOES. An arm that drove it correctly still failed.
#
# It is the same defect as the magic 4200-char window in
# tests/roofing_claim_gate_single_source.js, fixed the same way and for the same
# reason: a fixed length is a guess about a subject whose extent is knowable.
BRANCH_MARK = re.compile(r"resource === '([a-z0-9_]+)'")


class CouldNotTell(Exception):
    pass


def _read(path, what):
    if not os.path.isfile(path):
        raise CouldNotTell('%s does not exist, so %s could not be read'
                           % (os.path.relpath(path, REPO), what))
    return io.open(path, encoding='utf-8', errors='replace').read()


def role_sets(src):
    """{SET_NAME: {member roles}} from the roleSet() declarations themselves."""
    out = {}
    for m in re.finditer(r'const\s+([A-Z][A-Z0-9_]*ROLES)\s*=\s*roleSet\(\{([^}]*)\}\)', src):
        out[m.group(1)] = set(re.findall(r'([a-z_][a-z0-9_]*)\s*:\s*true', m.group(2)))
    if not out:
        raise CouldNotTell('no roleSet({...}) declaration matched in api/sd-data.js '
                           '-- the declaration shape moved and NOTHING was resolved. '
                           'This is not "no role sets".')
    return out


def gated_branches(src):
    """{resource: {role set names its branch tests}}.

    Each branch runs from its own `resource === '...'` to the NEXT one. See
    BRANCH_MARK: a fixed-length window swallowed the following branch's gate and
    made the resource unfalsifiable.
    """
    marks = [(m.start(), m.group(1)) for m in BRANCH_MARK.finditer(src)]
    out = {}
    for i, (pos, name) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(src)
        for g in re.finditer(r'!\s*([A-Z][A-Z0-9_]*ROLES)\s*\[\s*session\.role\s*\]',
                             src[pos:end]):
            out.setdefault(name, set()).add(g.group(1))
    if not out:
        raise CouldNotTell('no resource branch tested a role set -- the gate shape '
                           'moved and NOTHING was measured. This is not '
                           '"no role gates".')
    return out


def suite_files():
    out = []
    for pat in (('api', '*.test.js'), ('api', '_lib', '*.test.js'), ('tests', '*.js')):
        d = os.path.join(REPO, *pat[:-1])
        if not os.path.isdir(d):
            continue
        for n in sorted(os.listdir(d)):
            if n.endswith('.test.js') or (pat[0] == 'tests' and n.endswith('.js')):
                out.append(os.path.join(d, n))
    if not out:
        raise CouldNotTell('no test files found under api/ or tests/')
    return out


# A suite ASSERTS a role refusal. Required alongside a bare role literal -- see
# driven() for why a literal alone is not enough.
ROLE_REFUSAL = re.compile(r"""FORBIDDEN|NOT_AUTHORIS|NOT_AUTHORIZ|"""
                          r"""status(?:Code)?\s*,\s*403|403\s*,""")


# ── MASKING, SO A BOUNDARY IS FOUND IN CODE AND NOT IN PROSE ────────────────
# Two masks from one pass over the source, both the SAME LENGTH as the input so
# every offset still lines up with the original:
#
#   brace_mask -- strings, comments AND regex literals blanked. The ONLY text
#                 brace matching may look at. A `{` inside a message string is
#                 not a nesting level, and counting it closes a loop body one
#                 brace early; the mirror case (a stray `}` in a string) closes
#                 it late, which OVER-credits, and over-crediting is the
#                 direction that retires the check.
#   code       -- comments blanked, STRINGS KEPT. Everything this rule actually
#                 looks for lives inside a string -- `resource: 'alf_facility'`,
#                 `'FORBIDDEN'` -- so strings must survive. Comments must not:
#                 crediting a role named in prose turns a real gap into a pass,
#                 which is the 16-for-11 over-report in a worse place.
#
# A regex literal is detected by the standard expression-start heuristic. It can
# be wrong, and the consequence is a boundary that ends early (under-credit,
# safe) or late (over-credit, not safe) -- which is why an unterminated body is a
# hard NO CREDIT below rather than a body that runs to end of file.
_REGEX_START_BEFORE = set('(,=:[!&|?{};+-*%~^<>\n\t ')


def masks(s):
    """(brace_mask, code) -- same length as s. See the block comment above."""
    brace = list(s)
    code = list(s)
    i, n = 0, len(s)
    prev = '\n'  # what preceded the current position, ignoring whitespace

    def blank(a, b, keep_in_code):
        for k in range(a, b):
            if s[k] != '\n':
                brace[k] = ' '
                if not keep_in_code:
                    code[k] = ' '

    while i < n:
        c = s[i]
        if c in '\'"`':
            j, quote = i + 1, c
            while j < n:
                if s[j] == '\\':
                    j += 2
                    continue
                if s[j] == quote:
                    break
                j += 1
            blank(i, min(j + 1, n), keep_in_code=True)
            prev = 'x'
            i = min(j + 1, n)
            continue
        if c == '/' and i + 1 < n and s[i + 1] == '/':
            j = s.find('\n', i)
            j = n if j < 0 else j
            blank(i, j, keep_in_code=False)
            i = j
            continue
        if c == '/' and i + 1 < n and s[i + 1] == '*':
            j = s.find('*/', i + 2)
            j = n if j < 0 else j + 2
            blank(i, j, keep_in_code=False)
            i = j
            continue
        if c == '/' and prev in _REGEX_START_BEFORE:
            j = i + 1
            while j < n and s[j] != '\n':
                if s[j] == '\\':
                    j += 2
                    continue
                if s[j] == '/':
                    break
                j += 1
            if j < n and s[j] == '/':
                blank(i, j + 1, keep_in_code=True)
                prev = 'x'
                i = j + 1
                continue
        if not c.isspace():
            prev = c
        i += 1
    return ''.join(brace), ''.join(code)


def body_end(brace, open_idx):
    """Index just past the `}` matching the `{` at open_idx in `brace`, or None.

    None means the boundary COULD NOT BE FOUND, and every caller treats that as
    NO CREDIT. A scanner that fell back to end-of-file would credit every
    resource named in the rest of the suite to whatever roles the loop declared,
    which is the magic-window defect with an infinite window.
    """
    if open_idx is None or open_idx >= len(brace) or brace[open_idx] != '{':
        return None
    depth = 0
    for k in range(open_idx, len(brace)):
        if brace[k] == '{':
            depth += 1
        elif brace[k] == '}':
            depth -= 1
            if depth == 0:
                return k + 1
    return None


# A suite ARM asserts a role refusal. Required inside the loop body -- a role
# list plus a resource plus no refusal is the family-contacts shape exactly.
_LIST_DECL = re.compile(r"""const\s+([A-Za-z_$][\w$]*)\s*=\s*\[([^\]]*)\]\s*;""")
_STRINGS = re.compile(r"""['"]([a-z0-9_]+)['"]""")
_FOR_OF = re.compile(r"""for\s*\(\s*(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s+of\s+"""
                     r"""(\[[^\]]*\]|[A-Za-z_$][\w$]*)\s*\)\s*\{""")
_FOR_EACH = re.compile(r"""([A-Za-z_$][\w$]*)\s*\.forEach\s*\(\s*(?:function\s*)?\(?\s*"""
                       r"""([A-Za-z_$][\w$]*)[^)]*\)?\s*(?:=>)?\s*\{""")
_RESOURCE_AT = re.compile(r"""resource\s*[:=]+\s*['"]([a-z0-9_]+)['"]""")


def _role_list(text, all_roles):
    """The declared roles in an array-literal body, or None if it names none.

    ── THE INTERSECTION, NOT THE SUBSET, AND THE BUG THAT PROVED IT (2026-09-27)
    This first required EVERY member to be a declared role, and that silently
    credited NOTHING on the very arm the rule was written for:

        const ALF_NON_MGMT = ['nursing', 'med_aide', 'caregiver', 'activities'];

    `caregiver` is a real SAIRNcare role -- sairncare.html offers it in both role
    dropdowns -- but it appears in NO roleSet({...}) declaration in api/sd-data.js,
    so it is absent from all_roles. One unrecognised member rejected the whole
    list and three real roles went uncredited. A subset test makes the rule only
    as complete as the role universe it is handed.

    So: credit the INTERSECTION and require it non-empty. A `for ... of RESOURCES`
    intersects to nothing and still contributes nothing, which is the case the
    subset test was protecting and it is protected either way.

    THE UNRECOGNISED MEMBER IS ITSELF A FINDING AND IS NOT SWALLOWED HERE. A role
    the app offers that no gate's allowed-set ever names can never appear in
    `excluded`, so no gate can ever be reported uncovered on it -- see
    unknown_roles() and the UNDECLARED ROLES block in main().
    """
    items = _STRINGS.findall(text)
    if not items:
        return None
    got = set(items) & all_roles
    return got or None


def loop_driven(src, all_roles):
    """{resource: {roles}} from role checks written as a LOOP over a role list.

    ── THE POSITIVE-DETECTION GAP THIS CLOSES (2026-09-27) ────────────────────
    The literal rule below matches `role: 'x'` and `tokenFor('x')`. Real arms are
    written as a loop over a declared list:

        const ALF_NON_MGMT = ['nursing', 'med_aide', 'caregiver', 'activities'];
        for (const role of ALF_NON_MGMT) { ... call(hash, emp, role, ...) ... }

    There is no `role: 'nursing'` anywhere in that. So four arms that DO drive the
    excluded roles -- green, and CAUGHT under ablation -- left alf_facility
    reading `driven-as=owner`, and the tool went on demanding an arm that already
    existed. That is a FALSE NEGATIVE, not merely a noisy false alarm: the ratchet
    could never register the work.

    ── WHY THIS IS NOT ATTEMPT 1 AGAIN ───────────────────────────────────────
    Attempt 1 admitted a bare role literal in any file that asserted a refusal
    ANYWHERE. It moved uncovered 12 -> 7, and ablating the five it newly credited
    found TWO STILL SILENT: a suite can name `caregiver` and assert a 403 about
    two unrelated resources. FILE-WIDE ATTRIBUTION WAS THE DEFECT, not the idea
    of reading a variable.

    So this rule is BODY-SCOPED and needs all four of these at once:
      1. an array literal whose members are ALL role names (a `for ... of
         RESOURCES` contributes nothing);
      2. a for-of or .forEach over it, whose body boundary is found by BRACE
         MATCHING on masked code -- not a character count, and not end-of-file
         when the braces do not close;
      3. the loop variable used as an identifier inside that body;
      4. inside that same body, a role refusal asserted AND a `resource:` /
         `resource ===` literal. Only those resources are credited.

    Locked against synthetic fixtures in both directions BEFORE it was believed
    about this repo: tests/role_gate_loop_rule_probe.py. N2 there is attempt 1's
    exact failure; N4/N5/N6 are the boundary.

    STILL A SCREEN, NOT A VERDICT. It can only find the shapes it knows, and it
    cannot check that the loop variable is passed in the ROLE position rather than
    some other argument. `--ablate` remains the only sound measurement, and the
    pin must only ever be lowered on an ablation-CONFIRMED result.
    """
    brace, code = masks(src)
    lists = {}
    for m in _LIST_DECL.finditer(code):
        got = _role_list(m.group(2), all_roles)
        if got:
            lists[m.group(1)] = got

    out = {}
    heads = []
    for m in _FOR_OF.finditer(code):
        var, src_expr = m.group(1), m.group(2)
        roles = (_role_list(src_expr, all_roles) if src_expr.startswith('[')
                 else lists.get(src_expr))
        heads.append((m.end() - 1, var, roles))
    for m in _FOR_EACH.finditer(code):
        heads.append((m.end() - 1, m.group(2), lists.get(m.group(1))))

    for open_idx, var, roles in heads:
        if not roles:
            continue
        end = body_end(brace, open_idx)
        if end is None:
            # Boundary not found. NO CREDIT -- see body_end().
            continue
        body_code = code[open_idx:end]
        body_brace = brace[open_idx:end]
        # The loop variable must actually appear in code position in the body.
        if not re.search(r'\b%s\b' % re.escape(var), body_brace):
            continue
        if not ROLE_REFUSAL.search(body_code):
            continue
        for res in set(_RESOURCE_AT.findall(body_code)):
            out.setdefault(res, set()).update(roles)
    return out


def literal_driven(src, all_roles):
    """{resource: {roles}} from the ORIGINAL strict literal rule.

    `role: 'x'` or `tokenFor('x')`, attributed to every `resource:` position in
    the same file. FILE-WIDE, and deliberately kept that way: it over-reports in
    the safe direction (it asks for an arm that may already exist), and the two
    attempts to tighten or loosen it both made the tool worse. See the module
    docstring for all three.
    """
    roles = set()
    for r in all_roles:
        if re.search(r"""role\s*[:=]\s*['"]%s['"]""" % re.escape(r), src) \
           or re.search(r"""(?:tokenFor|token|session|sessionFor|as)\(\s*['"]%s['"]"""
                        % re.escape(r), src):
            roles.add(r)
    if not roles:
        return {}
    out = {}
    for res in set(re.findall(r"""resource\s*[:=]\s*['"]([a-z0-9_]+)['"]""", src)):
        out[res] = set(roles)
    return out


_TABLE_DECL = re.compile(r"""const\s+([A-Za-z_$][\w$]*)\s*=\s*\[([\s\S]*?)\]\s*;""")
_TABLE_ROW = re.compile(r"""\[\s*['"]([a-z][a-z0-9_]*)['"]""")
_DESTRUCTURED = re.compile(r"""for\s*\(\s*(?:const|let|var)\s*\[\s*([A-Za-z_$][\w$]*)"""
                           r"""[^\]]*\]\s+of\s+([A-Za-z_$][\w$]*)\s*\)\s*\{""")
_ROLE_CALL = re.compile(r"""\(\s*['"]([a-z][a-z0-9_]*)['"]""")


def table_driven(src, all_roles, gated_names):
    """{resource: {roles}} from a loop over a RESOURCE TABLE with a fixed role.

    ── THE FALSE NEGATIVE THIS CLOSES (2026-09-29) ───────────────────────────
    `loop_driven` above reads a loop over a ROLE list with the resource named
    inside. The MIRROR shape was invisible to both existing rules:

        const ADMIN_REFUSALS = [
          ['alf_billing', 'read',  null, 'resident billing'],
          ['alf_staff',   'write', {id}, 'the staff roster'],
        ];
        for (const [resource, action, payload, why] of ADMIN_REFUSALS) {
          const { res } = await call('caregiver', { action, resource });
          assert.strictEqual(code(res), 'FORBIDDEN');
        }

    There is no `resource: 'alf_billing'` and no `tokenFor('caregiver')` in
    that, so `literal_driven` sees nothing; the array members are arrays rather
    than role names, so `loop_driven` sees nothing either.

    MEASURED 2026-09-28: api/sd-data-alf-caregiver-scope.test.js drives ELEVEN
    resources through exactly that table as `caregiver` -- a role every one of
    their gates excludes -- and FIVE of them sat in the NOT-DRIVEN bucket,
    whose own text reads "there is no suite to add an arm to". `--ablate
    alf_billing` then reported 3 of 3 gate blocks CAUGHT, by that very suite.
    The bucket was over-reporting by at least 31%.

    ── WHY THIS IS NOT ATTEMPT 1 AGAIN ───────────────────────────────────────
    Attempt 1 (module docstring) credited a bare role literal in any file that
    asserted a refusal anywhere; two of the five it newly credited were still
    SILENT under ablation. FILE-WIDE ATTRIBUTION was the defect. So this rule is
    BODY-SCOPED and needs all five at once, mirroring loop_driven:

      1. an array literal whose members are ARRAYS whose FIRST element is a
         KNOWN GATED RESOURCE -- a table of something else contributes nothing;
      2. a for-of over it with a DESTRUCTURED head, body boundary found by
         BRACE MATCHING on masked code, never end-of-file;
      3. the destructured resource variable used as an identifier in that body;
      4. a role refusal asserted inside that same body;
      5. a role LITERAL in a call position inside that same body.

    Locked against synthetic fixtures in both directions BEFORE it was believed
    about this repo: tests/run_role_gate_table_rule_probe.py, N1-N6.

    STILL A SCREEN, NOT A VERDICT. `--ablate` remains the only sound
    measurement and the pin is only ever lowered on an ablation-CONFIRMED
    result.
    """
    brace, code = masks(src)
    tables = {}
    for m in _TABLE_DECL.finditer(code):
        names = [n for n in _TABLE_ROW.findall(m.group(2)) if n in gated_names]
        if names:
            tables[m.group(1)] = set(names)
    if not tables:
        return {}

    out = {}
    for m in _DESTRUCTURED.finditer(code):
        var, table = m.group(1), m.group(2)
        names = tables.get(table)
        if not names:
            continue
        end = body_end(brace, m.end() - 1)
        if end is None:
            continue
        body_code = code[m.end() - 1:end]
        body_brace = brace[m.end() - 1:end]
        # NOT AS AN OBJECT KEY. `{ resource: 'alf_billing' }` contains the
        # word `resource` and drives nothing; the first draft accepted it and
        # arm N4 said so. The variable must appear in a VALUE position.
        #
        # AND THIS LINE SHIPPED WITH A LITERAL BACKSPACE ON ITS FIRST
        # WRITE -- the raw 0x08 byte where the two characters `\b` were
        # meant -- which made it match nothing and silently zeroed the
        # whole rule on the real file while every synthetic fixture still
        # passed. That is the exact defect this repo already records once,
        # reproduced here by a shell heredoc eating one backslash. Found
        # by the real-corpus arm returning [] when a hand trace of the
        # same five conditions returned all eight.
        #
        # AND THE NOTE ITSELF THEN CARRIED THE BYTE. Writing this comment
        # put two more raw 0x08 bytes on this very line, where the reader
        # sees nothing at all; the control-character push gate caught them
        # on 2026-09-29. A description of an invisible defect written in
        # the invisible defect is the same bug one layer up.
        if not re.search(r'\b' + re.escape(var) + r'\b(?!\s*:)', body_brace):
            continue
        if not ROLE_REFUSAL.search(body_code):
            continue
        roles = {r for r in _ROLE_CALL.findall(body_code) if r in all_roles}
        if not roles:
            continue
        for res in names:
            out.setdefault(res, set()).update(roles)
    return out


def blind_population():
    """Gated resources NO rule could attribute a role to, as its own count.

    THE THIRD BUCKET IS NOT THE BLIND ONE, AND CONFLATING THEM IS HOW THIS
    TOOL OVERSTATED ITSELF. "NOT DRIVEN by any suite at all" is a claim about
    the WORLD -- nothing exercises this resource. What the screen can actually
    establish is a claim about ITSELF: no rule it owns could attribute a role.
    Those were the same number until 2026-09-29, and they were not the same
    fact: five of sixteen were driven by a table rule that did not exist yet.

    So the blind population is counted and PRINTED on every run, beside the
    buckets rather than inside them, and it shrinks when a rule is added rather
    than when the world changes.
    """
    src = _read(SD, 'the role gates')
    sets = role_sets(src)
    gated = gated_branches(src)
    all_roles = set()
    for v in sets.values():
        all_roles |= v
    drv = driven(all_roles)
    return {r for r in gated if not drv.get(r)}


def render_blind_line(blind):
    """The one-line disclosure printed on every run."""
    return ('BLIND TO THIS SCREEN: %d gated resource(s) that NO rule here could '
            'attribute a role to. That is a fact about the rules, not about the '
            'world -- `--ablate <resource>` is the only thing that settles it.'
            % len(blind))


def file_driven(src, all_roles):
    """{resource: {roles}} for ONE suite's source text -- both rules, unioned.

    Separate from driven() so the fixture probe can drive it on synthetic text.
    A rule that can only be exercised against the real repo cannot distinguish
    "the rule is right" from "the repo happens to suit it".

    THREE RULES NOW: the strict literal one, the role-LIST loop, and the
    resource-TABLE loop (table_driven). The third needs the gated-name set to
    decide whether an array is a resource table at all, which is why it is
    passed separately rather than inferred.
    """
    out = {}
    try:
        gated_names = set(gated_branches(_read(SD, 'the role gates')))
    except CouldNotTell:
        gated_names = set()
    parts = (literal_driven(src, all_roles), loop_driven(src, all_roles),
             table_driven(src, all_roles, gated_names))
    for part in parts:
        for res, roles in part.items():
            out.setdefault(res, set()).update(roles)
    return out


def driven(all_roles):
    """{resource: {roles any suite drives it with}} across every suite."""
    out = {}
    for p in suite_files():
        s = io.open(p, encoding='utf-8', errors='replace').read()
        if 'role' not in s:
            continue
        for res, roles in file_driven(s, all_roles).items():
            out.setdefault(res, set()).update(roles)
    return out


def analyse():
    src = _read(SD, 'the role gates')
    sets = role_sets(src)
    gated = gated_branches(src)
    all_roles = set()
    for v in sets.values():
        all_roles |= v
    drv = driven(all_roles)

    uncovered, covered, undriven = [], [], []
    for res in sorted(gated):
        allowed = set()
        for name in gated[res]:
            allowed |= sets.get(name, set())
        excluded = all_roles - allowed
        got = drv.get(res)
        if not got:
            # NOT the same finding, and the label is weaker than it reads. What
            # is established here is that NO RULE THIS TOOL OWNS could attribute
            # a role -- which is a fact about the rules, not about the world.
            # It is counted apart rather than folded in, and the blind line in
            # main() says out loud that this same set is the screen's blind
            # spot. The old comment here asserted "there is no suite to add an
            # arm to", and on 2026-09-29 a table rule that did not exist yet
            # found suites for five of sixteen.
            undriven.append((res, sorted(gated[res])))
            continue
        if got & excluded:
            covered.append((res, sorted(got & excluded)))
        else:
            uncovered.append((res, sorted(gated[res]), sorted(got)))
    return sets, gated, uncovered, covered, undriven


def ablate(resource):
    """Delete `resource`'s role gate(s), run every suite, report CAUGHT or SILENT.

    ── THE ONLY SOUND MEASUREMENT IN THIS FILE ─────────────────────────────────
    The static pass above is a SCREEN: it asks whether a suite names an excluded
    role, which is a proxy for the real question. This asks the real question --
    delete the gate and see whether anything goes red. Three static rules were
    tried and all three were wrong (see driven()); this one cannot be, because it
    is the property itself rather than a pattern that correlates with it.

    IT COSTS A FULL SUITE RUN PER GATE, which is why it is on demand and not the
    default. It restores the file and asserts byte-identity before returning --
    a mutation tool that can leave a repo mutated is worse than no tool, and this
    one edits the platform's largest dispatcher.
    """
    src = io.open(SD, encoding='utf-8', errors='replace').read()
    marks = [(m.start(), m.group(1)) for m in BRANCH_MARK.finditer(src)]
    blocks = []
    for i, (pos, name) in enumerate(marks):
        if name != resource:
            continue
        end = marks[i + 1][0] if i + 1 < len(marks) else len(src)
        for g in re.finditer(r' *if \(!([A-Z][A-Z0-9_]*ROLES)\[session\.role\]\) \{\n'
                             r'(?:[^\n]*\n)*?[ ]*\}\n', src[pos:end]):
            blocks.append((pos + g.start(), pos + g.end(), g.group(1)))
    if not blocks:
        sys.stderr.write('COULD NOT TELL -- no role gate found for %r. Either the '
                         'name is wrong or the gate shape moved; this is not '
                         '"the gate is untested".\n' % resource)
        return 2

    suites = []
    for pat in (('api',), ('api', '_lib'), ('tests',)):
        d = os.path.join(REPO, *pat)
        if not os.path.isdir(d):
            continue
        for n in sorted(os.listdir(d)):
            if n.endswith('.test.js') or (pat[0] == 'tests' and n.endswith('.js')):
                suites.append(os.path.join(d, n))

    def run_all():
        bad = set()
        for f in suites:
            try:
                r = subprocess.run(['node', f], capture_output=True, timeout=300)
                if r.returncode != 0:
                    bad.add(os.path.relpath(f, REPO).replace(os.sep, '/'))
            except Exception:
                bad.add(os.path.relpath(f, REPO).replace(os.sep, '/') + ' (error)')
        return bad

    print('ABLATING %s -- %d gate block(s): %s'
          % (resource, len(blocks), ', '.join(b[2] for b in blocks)))
    print('baseline over %d suites (this takes a while) ...' % len(suites))
    base = run_all()
    print('baseline failures: %d' % len(base))

    rc = 0
    try:
        for start, end, rs in blocks:
            mutated = src[:start] + src[end:]
            io.open(SD, 'w', encoding='utf-8', newline='\n').write(mutated)
            chk = subprocess.run(['node', '--check', SD], capture_output=True)
            if chk.returncode != 0:
                # NOT a pass. A mutation that will not parse has tested nothing,
                # and reporting it as CAUGHT would be the worst possible answer.
                print('  %-24s COULD NOT TELL -- the mutation does not parse' % rs)
                rc = max(rc, 2)
                io.open(SD, 'w', encoding='utf-8', newline='\n').write(src)
                continue
            newly = sorted(run_all() - base)
            if newly:
                print('  %-24s CAUGHT by %d suite(s): %s'
                      % (rs, len(newly), ', '.join(newly[:3])))
            else:
                print('  %-24s *** SILENT *** deleting this gate failed NOTHING'
                      % rs)
                rc = max(rc, 1)
            io.open(SD, 'w', encoding='utf-8', newline='\n').write(src)
    finally:
        io.open(SD, 'w', encoding='utf-8', newline='\n').write(src)
    # Byte-identity, asserted rather than assumed.
    if io.open(SD, encoding='utf-8', errors='replace').read() != src:
        sys.stderr.write('RESTORE FAILED -- %s is not byte-identical. FIX THIS '
                         'BEFORE ANYTHING ELSE.\n' % SD)
        return 2
    print('restored byte-identical')
    return rc


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--ablate', metavar='RESOURCE',
                    help='delete that resource\'s role gate(s), run every suite and '
                         'report CAUGHT or SILENT. The only sound measurement here; '
                         'exit 1 if any gate is SILENT, 2 if it could not be told')
    ap.add_argument('--list', action='store_true', help='print every uncovered gate')
    ap.add_argument('--baseline', action='store_true',
                    help='rewrite the pin to the CURRENT numbers. Only correct after '
                         'a real arm is added, never to make a run pass')
    args = ap.parse_args(argv)

    if args.ablate:
        return ablate(args.ablate)

    try:
        sets, gated, uncovered, covered, undriven = analyse()
    except CouldNotTell as e:
        sys.stderr.write('COULD NOT TELL -- %s\n' % e)
        sys.stderr.write('This is the THIRD STATE and is NOT a clean run.\n')
        return 2

    print('ROLE-GATE NEGATIVE COVERAGE (api/sd-data.js)')
    print('%d role set(s) declared, %d resource branch(es) gated on one.'
          % (len(sets), len(gated)))
    print('')
    print('UNCOVERED -- a suite drives it, never with a role the gate excludes: %d'
          % len(uncovered))
    print('COVERED   -- some suite drives it with an excluded role:             %d'
          % len(covered))
    print('NOT DRIVEN by any suite at all (a different gap, counted apart):     %d'
          % len(undriven))

    # ── THE BLIND POPULATION, COUNTED AND PRINTED ON EVERY RUN ──────
    # The three buckets above are claims about the WORLD. This one is a
    # claim about the SCREEN ITSELF, and they were conflated until
    # 2026-09-29: five resources sat under "NOT DRIVEN by any suite at
    # all" because no RULE here could attribute a role to them, and a
    # table rule that did not exist yet found all five. A bucket that
    # cannot tell "nothing drives it" from "I cannot see what drives
    # it" overstates the world using a fact about itself.
    print('')
    print('  ' + render_blind_line(set(r for r, _g in undriven)))
    print('')
    if args.list or uncovered:
        for res, gs, got in uncovered:
            print('   %-26s gate=%-34s driven-as=%s'
                  % (res, ','.join(gs)[:34], ','.join(got)))
    if args.list and undriven:
        print('')
        print('   NOT DRIVEN:')
        for res, gs in undriven:
            print('   %-26s gate=%s' % (res, ','.join(gs)))
    print('')
    print('AN UNCOVERED GATE WOULD SURVIVE BEING DELETED. That is the whole claim --')
    print('not that the gate is wrong, but that nothing would notice its absence.')
    print('api/sd-data-family-contacts.test.js was 18 green arms over a resource with')
    print('NO GATE AT ALL, because every arm ran as owner.')
    print('')

    if args.baseline:
        io.open(PIN, 'w', encoding='utf-8', newline='\n').write(json.dumps({
            '_what': 'Pinned role-gate negative coverage. Written by '
                     'tools/role_gate_negative_coverage.py --baseline. A ratchet: '
                     '`uncovered` must never rise. Lower it by adding an arm that '
                     'drives the resource with a role its gate excludes. '
                     'BUT A RISE IS NOT ALWAYS A REGRESSION: adding a RULE moves '
                     'resources out of not_driven and into uncovered without the '
                     'world changing, because the screen could not see them '
                     'before. That happened on 2026-09-29 -- the resource-table '
                     'rule took uncovered 12 -> 17 and not_driven 16 -> 11 in one '
                     'commit, and nothing about the gates changed. Across a rule '
                     'change the two pins are not comparable; the commit that '
                     're-pins has to say which it was.',
            'uncovered': len(uncovered),
            'covered': len(covered),
            'not_driven': len(undriven),
            'gated_total': len(gated),
            'uncovered_resources': [u[0] for u in uncovered],
        }, indent=2, sort_keys=True) + '\n')
        print('wrote %s' % os.path.relpath(PIN, REPO))
        return 0

    if not os.path.isfile(PIN):
        sys.stderr.write('COULD NOT TELL -- %s does not exist, so nothing was '
                         'compared. Run --baseline once to pin the measured state.\n'
                         % os.path.relpath(PIN, REPO))
        return 2
    try:
        pin = json.load(io.open(PIN, encoding='utf-8'))
    except ValueError as e:
        sys.stderr.write('COULD NOT TELL -- %s will not parse (%s). NOTHING WAS '
                         'COMPARED.\n' % (os.path.relpath(PIN, REPO), e))
        return 2
    was = pin.get('uncovered')
    if not isinstance(was, int):
        sys.stderr.write('COULD NOT TELL -- the pin carries no integer `uncovered`.\n')
        return 2

    if len(uncovered) > was:
        print('REGRESSION -- uncovered role gates rose from %d to %d.' % (was, len(uncovered)))
        print('Either add an arm driving the new gate with a role it excludes, or say')
        print('why it does not need one and re-pin with --baseline in the same commit.')
        return 1
    if len(uncovered) < was:
        print('IMPROVED -- uncovered fell from %d to %d. Re-pin:' % (was, len(uncovered)))
        print('   python tools/role_gate_negative_coverage.py --baseline')
        return 0
    print('OK -- no worse than pinned (%d uncovered).' % was)
    print('A RATCHET IS NOT A PASS. %d gate(s) would still survive deletion.'
          % len(uncovered))
    return 0


if __name__ == '__main__':
    sys.exit(main())
