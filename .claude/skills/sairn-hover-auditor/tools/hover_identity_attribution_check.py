#!/usr/bin/env python
"""Does every WRITE action in a handler file record WHO performed it.

Own tool, own location (hover's own log directory, never a build-agent
file). Built 2026-10-06 (H1, batch G, item 2), separate from
hover_code_normalize.py: that tool strips naming/comment bias before a
HUMAN judges code; this tool is a MECHANICAL SCREEN that looks for one
specific, narrow structural pattern across many files without a human
reading any of them first -- the same relationship hover_money_on_row_sweep.py
has to a human money-on-row read. Built after finding api/legal-citator.js's
feedback action writes a record with no employee_id anywhere, while every
OTHER action in the same file (via auditLookup()) does capture one -- a
missing-attribution shape worth screening for across the whole api/*.js
population, not just the one file it was first noticed in.

WHAT IT LOOKS FOR, PER ACTION BRANCH:
  1. Find each `action === 'name'` (or `resource === 'x' && action === 'name'`)
     branch; its span runs to the next such branch or end of file.
  2. Inside the span, find a WRITE-shaped fetch: `method: 'POST'|'PATCH'|'PUT'`
     within the same fetch() call as a `body: JSON.stringify(ARG)`.
  3. Resolve ARG to its real object-literal text -- inline, or (if ARG is a
     bare identifier) by finding `const ARG = {...}` earlier in the SAME span.
  4. PASS if that object-literal text contains `.employee_id` anywhere (the
     session/caller-derived identity shape this platform uses throughout:
     granted_by: session.employee_id, witness_employee_id: caller.employee_id,
     etc). FLAG if it does not. COULD_NOT_TELL if ARG cannot be resolved to
     any object-literal text found in the span.
  5. A branch with no write-shaped fetch at all is SKIPPED -- nothing to
     check; a read action records nothing by definition.

CANNOT SEE, NAMED RATHER THAN SILENTLY ASSUMED CORRECT:
  - ONLY `session.employee_id` / `caller.employee_id` count as real
    attribution -- a file whose verified-session variable is named anything
    else (every file read so far names it `session` or `caller`, but that is
    an observed convention, not a guaranteed one) will under-report, landing
    on FLAG or COULD_NOT_TELL for a branch that is actually fine. The first
    version of this check matched ANY `.employee_id`, which wrongly PASSED
    api/sd-auth.js's bootstrap and login branches on `body.employee_id` --
    the CALLER-SUPPLIED target of the action, not the verified actor.
  - Attribution via an audit()/writeAuditLog() call elsewhere in the SAME
    branch counts as PASS even when the primary write itself carries no
    employee_id (api/sd-auth.js's set_active PATCHes {active, updated_at}
    only, but the same branch's audit() call names caller.employee_id in a
    separate table) -- found necessary after the first real run flagged
    set_active in every *-auth.js file that has it. This widens the search
    to the WHOLE branch, so a branch with a genuinely unrelated audit call
    elsewhere (not actually about THIS write) could still false-PASS; not
    observed in this platform's actual audit()-call convention, but not
    structurally ruled out either.
  - A write whose body is built by multi-step mutation (`rec.foo = ...;
    rec.bar = ...;`) rather than one object literal may resolve the WRONG
    text or COULD_NOT_TELL -- the resolver looks for `const ARG = {` only.
  - Branch boundaries are found by the SAME `action === 'x'` marker the
    dispatch itself uses; a file with a materially different dispatch shape
    (a lookup table instead of if-chains) will undercount branches, named by
    the tool printing how many branches it found, not asserted silently.
  - RESOURCE-NAME COLLISION ON resource === 'x' && action === 'y'
    DISPATCHERS -- FIXED 2026-10-06 batch I, item 5 (found batch H, seq 967).
    BRANCH_RE now captures and carries the resource name through every
    report line as 'resource/action', so api/sd-data.js's many branches
    sharing the bare action name 'write' are distinguishable. Still CANNOT
    SEE a dispatch shape that is neither `action === 'x'` nor `resource ===
    'x' && action === 'y'` in either order (a lookup-table dispatcher, for
    example) -- named, not assumed covered.
  - A field conventionally named something other than *_by / *_employee_id
    (there is no fixed list enforced) that still carries real attribution
    through a DIFFERENT shape is invisible to this screen if it does not
    contain the literal substring `.employee_id`.
"""
import os
import re
import sys

REPO = r'C:\Users\marsh\Documents\SAIRN-hover'

# RESOURCE NAME NOW CAPTURED, NOT DISCARDED (fixed 2026-10-06 batch I,
# item 5): the first version matched an optional resource prefix but threw
# it away, so on a resource === 'x' && action === 'y' dispatcher with many
# resources sharing one action name ('write' on api/sd-data.js), every
# report line read identically and none of them were individually
# actionable -- the aggregate counts were real, the per-branch list was not.
# Named at the time (seq 967), fixed here using the same capture-group shape
# already proven correct in hover_cross_resource_gate_check.py's own
# BRANCH_RE, built independently for a different tool a batch earlier.
BRANCH_RE = re.compile(
    r"(?:resource\s*===\s*'(\w+)'\s*&&\s*action\s*===\s*'(\w+)'"
    r"|action\s*===\s*'(\w+)'\s*&&\s*resource\s*===\s*'(\w+)'"
    r"|action\s*===\s*'(\w+)'(?!\s*&&\s*resource))"
)
WRITE_METHOD_RE = re.compile(r"method\s*:\s*'(POST|PATCH|PUT)'")
STRINGIFY_RE = re.compile(r"JSON\.stringify\(\s*(\w+|\{)")
# SESSION/CALLER-DERIVED ONLY, NOT ANY `.employee_id` (fixed after the first
# real run on sd-auth.js passed bootstrap and login too -- both reference
# `body.employee_id`, the CALLER-SUPPLIED target of the action, which is a
# different and spoofable thing from the VERIFIED actor's own identity).
# Every file read so far names its verified-session variable exactly
# `session` or `caller` (verifySessionToken()/activeCaller()'s own return
# value) -- never re-derived per file, named as a real limitation below.
IDENT_SIGNAL_RE = re.compile(r"\b(?:session|caller)\.employee_id\b")

# VALUE-POSITION ONLY (batch K, item 3): session/caller.employee_id
# immediately after ':' (an object-literal property value, Object.assign's
# OWN argument included) or '=' (an assignment target, including bracket
# mutation: obj[key] = session.employee_id). Added after finding TWO real
# false positives in the ORIGINAL two-pass-path design: api/sd-data.js's
# alf_mar/write stamps marData[actorKey] = session.employee_id (a mutation
# on an object already built, not a literal and not an audit() call), and
# rf_invoices/add_payment builds `stamped = Object.assign({}, entry,
# {recorded_by: session.employee_id, ...})` -- an intermediate variable that
# flows BY REFERENCE into the final JSON.stringify body this tool resolves,
# so the literal payload text alone never shows the attribution.
# DELIBERATELY NARROWER than a bare whole-branch scan (already tried once,
# already rejected -- see check_branch()'s own comment on the
# api/dnt-auth.js false positive, a FUNCTION-ARGUMENT reference with
# neither ':' nor '=' before it): requiring the ':' or '=' immediately
# before the reference means a lookup argument like
# loadEmployee(caller.employee_id) still does not match.
#
# ONE OPTIONAL WRAPPING CALL ALLOWED, 2026-10-07 (H1 batch O, item 4), after
# a real false positive was found and reproduced: api/sd-data.js's
# sd_customers/soft_delete and sd_quote_requests/soft_delete both stamp
# `_deleted_by: String(session.employee_id || '')` -- a type-coercion
# wrapper sitting between the ':' and the real reference, which the
# original regex's "[:=]\s*(?:session|caller)\." (no wrapper tolerance at
# all) could not see, so both branches FLAGGED despite genuinely
# attributing the write. (This was first guessed, WRONGLY, as a
# branch-span-truncation bug in an earlier round; re-investigated by
# printing find_branches()'s real spans before touching the code, which
# showed the full real span WAS captured intact -- the defect was in this
# regex, not in span extraction. Corrected rather than left on the wrong
# diagnosis.) `(?:\w+\(\s*)?` allows exactly one bare identifier-call
# wrapper (String(, Number(, etc.) between the ':'/'=' and the reference,
# while still requiring that ':'/'=' to anchor it -- a bare function
# argument like loadEmployee(caller.employee_id), with no ':'/'=' anywhere
# before loadEmployee, still does not match, so the original dnt-auth.js
# exclusion this regex exists for is unaffected.
ATTRIBUTION_VALUE_RE = re.compile(r"[:=]\s*(?:\w+\(\s*)?(?:session|caller)\.employee_id\b")


def _matching_paren_text(text, open_idx):
    """text[open_idx] is '{'. Return the text up to and including its match."""
    depth = 0
    for i in range(open_idx, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return text[open_idx:i + 1]
    return text[open_idx:]  # unbalanced -- return what there is, caller sees it's odd


EXPORTS_RE = re.compile(r"module\.exports\s*=\s*async\s*(?:function\s*\*?\s*\w*\s*)?\([^)]*\)\s*(?:=>)?\s*\{")


def _handler_body_end(text):
    """End of the `module.exports = async (req, res) => { ... }` body, or
    None if that shape is not found. FOUND ONCE THIS TOOL WAS WRONG WITHOUT
    IT: the last action branch's span used to run to end-of-file, silently
    swallowing any helper function defined below the handler (e.g.
    requireWitness() in api/sairncare-witness.js) into the LAST branch's
    text -- that helper's own unrelated writes then decided the last
    branch's verdict. Clipping every span to the real handler body fixes it
    at the source rather than special-casing the last branch."""
    m = EXPORTS_RE.search(text)
    if not m:
        return None
    brace_idx = text.index('{', m.start())
    body = _matching_paren_text(text, brace_idx)
    return brace_idx + len(body)  # absolute end position of the matched '}'


RESOURCE_CONTEXT_RE = re.compile(r"resource\s*===\s*'(\w+)'")


def _nearest_resource_context(text, pos, contexts):
    """contexts is a sorted [(ctx_pos, name)] list from RESOURCE_CONTEXT_RE.
    Returns the resource name whose context position is the closest one at
    or before pos, or None. FIXES THE OUTER-SHARED-BLOCK SHAPE (batch J,
    item 6): resource === 'sd_customers' && (action === 'read' || action
    === 'write' || ...) { if (action === 'write') {...} } -- the inner
    action==='write' branch has no resource of its OWN in its marker text,
    but IS inside a block whose own resource check appeared just before
    it. Without this, those inner branches stayed bare ('write' alone,
    colliding with every other resource's own 'write')."""
    best = None
    for ctx_pos, name in contexts:
        if ctx_pos <= pos:
            best = name
        else:
            break
    return best


def find_branches(text):
    """Returns [(action_name, start, end)] spans covering the dispatch
    function's body, split at each action === 'x' marker found. Spans never
    extend past the end of the module.exports handler body, if that shape
    is found -- see _handler_body_end()'s own comment for why this matters."""
    contexts = [(m.start(), m.group(1)) for m in RESOURCE_CONTEXT_RE.finditer(text)]
    marks = []
    for m in BRANCH_RE.finditer(text):
        if m.group(1):          # resource === 'x' && action === 'y'
            resource, action = m.group(1), m.group(2)
        elif m.group(4):        # action === 'y' && resource === 'x'
            action, resource = m.group(3), m.group(4)
        else:                   # action === 'y' alone, no resource ON THIS
            # MARKER -- try the nearest preceding resource === 'x' context
            # (the outer-shared-block shape) before giving up and leaving
            # it bare.
            action = m.group(5)
            resource = _nearest_resource_context(text, m.start(), contexts)
        name = '%s/%s' % (resource, action) if resource else action
        marks.append((m.start(), name))
    handler_end = _handler_body_end(text)
    hard_end = handler_end if handler_end is not None else len(text)
    spans = []
    for i, (pos, name) in enumerate(marks):
        natural_end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        end = min(natural_end, hard_end) if pos < hard_end else natural_end
        spans.append((name, pos, end))
    return spans


def resolve_write_payload(span_text, arg):
    """arg is either '{' (inline) or an identifier. Return the object-literal
    text, or None if it cannot be resolved within this span."""
    if arg == '{':
        # Caller already knows the brace position within span_text; this
        # path is handled by the caller passing the brace index directly.
        return None
    const_re = re.compile(r"\bconst\s+" + re.escape(arg) + r"\s*=\s*\{")
    m = const_re.search(span_text)
    if not m:
        return None
    brace_idx = span_text.index('{', m.start())
    return _matching_paren_text(span_text, brace_idx)


AUDIT_CALL_RE = re.compile(r"\b(?:audit|writeAuditLog)\s*\(")


def _matching_paren_text_round(text, open_idx):
    """text[open_idx] is '('. Return text up to and including its match."""
    depth = 0
    for i in range(open_idx, len(text)):
        if text[i] == '(':
            depth += 1
        elif text[i] == ')':
            depth -= 1
            if depth == 0:
                return text[open_idx:i + 1]
    return text[open_idx:]


def _audit_call_has_attribution(span_text):
    """True if any audit()/writeAuditLog() call in this branch has
    `.employee_id` INSIDE ITS OWN ARGUMENTS -- not just somewhere else in the
    branch. See check_branch()'s own comment for why whole-branch substring
    search was tried and specifically rejected (api/dnt-auth.js's setup
    branch calls loadEmployee(caller.employee_id) as an unrelated lookup,
    which is not an attribution record)."""
    for m in AUDIT_CALL_RE.finditer(span_text):
        open_idx = span_text.index('(', m.start())
        call_text = _matching_paren_text_round(span_text, open_idx)
        if IDENT_SIGNAL_RE.search(call_text):
            return True
    return False


NAMED_FUNCTION_RE = re.compile(r"(?:async\s+)?function\s+[A-Za-z_]\w*\s*\([^)]*\)\s*\{")


def _strip_named_helper_functions(span_text):
    """Remove NAMED function declarations (function patchEmployee(...){...},
    async function loadEmployee(...){...}) from a branch's span before write
    detection. FOUND NECESSARY, NOT SPECULATIVE: a shared helper declared
    textually between two action branches (e.g. check_license then bootstrap)
    is swept into the PRECEDING branch's span by marker-to-marker splitting,
    and the helper's own generic write (api/alf-auth.js's patchEmployee(),
    body: JSON.stringify(Object.assign({updated_at:...}, patch))) then drove
    a COULD_NOT_TELL for a branch (check_license) that never itself writes
    anything -- confirmed by direct read, twice, before this fix. Anonymous
    inline callbacks (`function(x){...}`, no name) are deliberately NOT
    stripped -- those ARE the branch's own logic (a .filter()/.map() body),
    not a shared helper."""
    out = span_text
    while True:
        m = NAMED_FUNCTION_RE.search(out)
        if not m:
            return out
        brace_idx = out.index('{', m.start())
        body = _matching_paren_text(out, brace_idx)
        out = out[:m.start()] + out[m.start() + len(m.group()) - 1 + len(body):]


def check_branch(name, span_text):
    span_text = _strip_named_helper_functions(span_text)
    writes = []
    for sm in STRINGIFY_RE.finditer(span_text):
        # Is there a method: POST/PATCH/PUT within 400 chars before this
        # JSON.stringify call (same fetch() options object, in practice)?
        window = span_text[max(0, sm.start() - 400):sm.start()]
        if not WRITE_METHOD_RE.search(window):
            continue
        arg = sm.group(1)
        if arg == '{':
            brace_idx = sm.end() - 1
            payload_text = _matching_paren_text(span_text, brace_idx)
        else:
            payload_text = resolve_write_payload(span_text, arg)
        writes.append((arg, payload_text))
    if not writes:
        return {'action': name, 'verdict': 'SKIP', 'reason': 'no write-shaped fetch found'}
    # ── ATTRIBUTION VIA A SEPARATE AUDIT CALL COUNTS, BUT ONLY INSIDE THE
    # AUDIT CALL'S OWN ARGUMENTS (fixed TWICE on this exact question) ───────
    # First real run: api/sd-auth.js's set_active PATCHes {active, updated_at}
    # only, no employee_id -- but the SAME branch calls audit() with
    # employee_id: caller.employee_id in its OWN arguments, a dedicated audit
    # table naming who performed it. Widening the search to the WHOLE branch
    # fixed that. SECOND real run (this same batch): that widening then
    # false-PASSed api/dnt-auth.js's setup branch, which calls
    # `loadEmployee(caller.employee_id)` -- a LOOKUP of the CALLER's own
    # active status, nothing to do with attributing the write -- while the
    # actual provisioning write two lines later still has no employee_id at
    # all. A whole-branch substring search cannot tell "used as an
    # attribution value" from "used as a lookup argument". THE FIX: only
    # text inside a resolved write payload OR inside an audit()/
    # writeAuditLog() call's OWN arguments counts; a bare reference anywhere
    # else in the branch does not.
    # PASS PATH 1: the write's OWN resolved payload carries the signal
    # (accounting.js's inline granted_by: session.employee_id,
    # sairncare-witness.js's var-referenced witness_employee_id).
    any_payload_attributed = any(
        payload_text is not None and IDENT_SIGNAL_RE.search(payload_text)
        for _arg, payload_text in writes)
    # PASS PATH 2: a SEPARATE audit()/writeAuditLog() call, ITS OWN
    # arguments only (api/sd-auth.js's set_active).
    # PASS PATH 3 (batch K, item 3): a VALUE-POSITION assignment or object-
    # literal property anywhere in the branch (api/sd-data.js's
    # alf_mar/write mutation, rf_invoices/add_payment's Object.assign) --
    # see ATTRIBUTION_VALUE_RE's own comment for why this is safe against
    # reopening the dnt-auth.js false positive.
    branch_has_attribution = (any_payload_attributed
                               or _audit_call_has_attribution(span_text)
                               or bool(ATTRIBUTION_VALUE_RE.search(span_text)))
    if branch_has_attribution:
        return {'action': name, 'verdict': 'PASS',
                'writes': [{'arg': a, 'verdict': 'PASS'} for a, _ in writes]}
    results = []
    for arg, payload_text in writes:
        if payload_text is None:
            results.append({'arg': arg, 'verdict': 'COULD_NOT_TELL',
                             'reason': 'write body argument %r not resolvable to an object literal in this span, and no .employee_id found in any audit() call in the branch either' % arg})
        else:
            results.append({'arg': arg, 'verdict': 'FLAG',
                             'reason': 'no .employee_id reference in the write payload or in any audit() call in this branch'})
    # COULD_NOT_TELL only matters when NO write in the branch resolved; if at
    # least one write resolved to real FLAG text, that is the stronger signal
    # (a write we COULD read plainly lacks attribution) over an unrelated
    # unresolved write elsewhere in the same branch.
    order = {'FLAG': 0, 'COULD_NOT_TELL': 1}
    worst = min(results, key=lambda r: order[r['verdict']])
    return {'action': name, 'verdict': worst['verdict'], 'writes': results}


def check_file(path):
    with open(path, encoding='utf-8') as f:
        text = f.read()
    spans = find_branches(text)
    results = [check_branch(name, text[start:end]) for name, start, end in spans]
    return {'path': path, 'branches_found': len(spans), 'results': results}


def summarize(report):
    flags = [r for r in report['results'] if r['verdict'] == 'FLAG']
    ctt = [r for r in report['results'] if r['verdict'] == 'COULD_NOT_TELL']
    passes = [r for r in report['results'] if r['verdict'] == 'PASS']
    skips = [r for r in report['results'] if r['verdict'] == 'SKIP']
    return flags, ctt, passes, skips


# ---------------------------------------------------------------------------
# Selftest fixtures -- built from the real shapes this tool was built to
# classify, not invented in the abstract.
# ---------------------------------------------------------------------------

FIXTURE_FLAG = """
module.exports = async (req, res) => {
  if (action === 'feedback') {
    const logRec = { license_hash: lic.license_hash, treatment_id: treatmentId, action: fbAction, note: note };
    const r = await fetch(url, { method: 'POST', headers: headers, body: JSON.stringify(logRec) });
    return;
  }
};
"""

FIXTURE_PASS_INLINE = """
module.exports = async (req, res) => {
  if (action === 'consent') {
    const w = await fetch(url, { method: 'POST', headers: headers,
      body: JSON.stringify({ license_hash: licHash, granted_by: session.employee_id, granted_on: today }) });
    return;
  }
};
"""

FIXTURE_PASS_VAR = """
module.exports = async (req, res) => {
  if (action === 'set_policy') {
    const rec = { license_hash: licHash, require_two_person: body.require_two_person, updated_by: caller.employee_id };
    const r = await fetch(url, { method: 'POST', headers: headers, body: JSON.stringify(rec) });
    return;
  }
};
"""

FIXTURE_SKIP_READ = """
module.exports = async (req, res) => {
  if (action === 'status') {
    const r = await fetch(url, { headers: headers });
    return;
  }
};
"""

FIXTURE_COULD_NOT_TELL = """
module.exports = async (req, res) => {
  if (action === 'mutate') {
    let rec = {};
    rec.license_hash = licHash;
    rec.employee_id_is_set_elsewhere = true;
    const r = await fetch(url, { method: 'PATCH', headers: headers, body: JSON.stringify(rec) });
    return;
  }
};
"""


FIXTURE_PASS_MUTATION = """
module.exports = async (req, res) => {
  if (action === 'mutate_attributed') {
    let rec = storedBlob(payload, ['id']);
    rec[actorKey] = session.employee_id;
    const r = await fetch(url, { method: 'PATCH', headers: headers, body: JSON.stringify(rec) });
    return;
  }
};
"""

FIXTURE_FLAG_UNRELATED_MUTATION = """
module.exports = async (req, res) => {
  if (action === 'mutate_unrelated') {
    let rec = {};
    rec.status = payload.status;
    rec.updated_at = nowISO();
    const r = await fetch(url, { method: 'PATCH', headers: headers, body: JSON.stringify(rec) });
    return;
  }
};
"""

# Built from the real false positive found and reproduced 2026-10-07 (H1
# batch O, item 4): api/sd-data.js's sd_customers/soft_delete and
# sd_quote_requests/soft_delete both wrap the attribution in String(...)
# before stamping it, and the original ATTRIBUTION_VALUE_RE (no wrapping-call
# tolerance at all) FLAGGED both despite the write genuinely attributing the
# actor.
FIXTURE_PASS_WRAPPED_MUTATION = """
module.exports = async (req, res) => {
  if (action === 'soft_delete') {
    const marked = Object.assign({}, stored, { _deleted_at: nowISO(), _deleted_by: String(session.employee_id || '') });
    const r = await fetch(url, { method: 'PATCH', headers: headers, body: JSON.stringify({ data: marked }) });
    return;
  }
};
"""


def _write_tmp(content):
    import tempfile
    fd, path = tempfile.mkstemp(suffix='.js')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(content)
    return path


def _selftest():
    cases = [
        ('FLAG-expected: feedback-shaped write, no employee_id', FIXTURE_FLAG, 'FLAG'),
        ('PASS-expected: inline write with granted_by: session.employee_id', FIXTURE_PASS_INLINE, 'PASS'),
        ('PASS-expected: var-referenced write with updated_by: caller.employee_id', FIXTURE_PASS_VAR, 'PASS'),
        ('SKIP-expected: read-only branch, no write at all', FIXTURE_SKIP_READ, 'SKIP'),
        ('COULD_NOT_TELL-expected: write body built by mutation, not one literal', FIXTURE_COULD_NOT_TELL, 'COULD_NOT_TELL'),
        ('PASS-expected: bracket-mutation attribution, rec[actorKey] = session.employee_id', FIXTURE_PASS_MUTATION, 'PASS'),
        ('COULD_NOT_TELL-expected: a mutation that sets unrelated fields, no employee_id anywhere', FIXTURE_FLAG_UNRELATED_MUTATION, 'COULD_NOT_TELL'),
        ('PASS-expected: wrapped mutation, _deleted_by: String(session.employee_id || \'\')', FIXTURE_PASS_WRAPPED_MUTATION, 'PASS'),
    ]
    ok = 0
    for desc, content, expected in cases:
        path = _write_tmp(content)
        try:
            report = check_file(path)
            got = report['results'][0]['verdict'] if report['results'] else 'NO_BRANCH_FOUND'
            status = 'ok  ' if got == expected else 'FAIL'
            if got == expected:
                ok += 1
            print('  %s %-70s -> %s (expected %s)' % (status, desc, got, expected))
        finally:
            os.remove(path)
    print('%d/%d fixtures correct' % (ok, len(cases)))
    return ok == len(cases)


def main(argv):
    if '--selftest' in argv:
        return 0 if _selftest() else 1
    if '--file' in argv:
        path = argv[argv.index('--file') + 1]
        report = check_file(path)
        flags, ctt, passes, skips = summarize(report)
        print('%s -- %d action branch(es) found' % (report['path'], report['branches_found']))
        print('  PASS %d, FLAG %d, COULD_NOT_TELL %d, SKIP %d' % (len(passes), len(flags), len(ctt), len(skips)))
        for r in flags:
            print('  ! FLAG  %-20s %s' % (r['action'], [w.get('reason') for w in r['writes'] if w['verdict'] == 'FLAG']))
        for r in ctt:
            print('  ? CNT   %-20s %s' % (r['action'], [w.get('reason') for w in r['writes'] if w['verdict'] == 'COULD_NOT_TELL']))
        return 1 if (flags or ctt) else 0
    print('usage: hover_identity_attribution_check.py --selftest | --file PATH')
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
