r"""The three missing EVV fields must be CAPTURED, and the payroll engine must be CALLED.

Run: python tests/sen_evv_payroll_wiring_probe.py

TWO THINGS THAT LOOK LIKE ONE. api/_lib/sen-evv-readiness.js has been reading
`visit.service_type`, `client.member_id` and `caregiver.state_caregiver_id`
since 2026-08-27 and reporting all three MISSING on every visit, in its own
words: "SAIRNsenior does not capture one yet." The checker was right and the
forms had no such field. A reader of the readiness report could not tell "the
agency has not filled this in" from "the app cannot store it".

And api/_lib/sen-payroll.js is new, which makes it the same risk the IOLTA
reconciler and the KX accumulator both realised tonight: a correct engine that
nothing calls. THREE INSTANCES OF THAT SHAPE IN ONE SESSION is why this probe
exists at all -- a unit suite cannot see an absent caller.

WHAT THE ARMS ASSERT:

  1-3  each of the three federal-element fields makes the ROUND TRIP: a form
       control exists, the save path writes it onto the record, and the edit
       path reads it back. A field that saves but never reloads silently
       blanks itself on the next edit, which is worse than not having it.
  4    service_type is a SCHEDULING field server-side, not an EVV one. The
       person being paid for a visit must not also choose which service was
       billed -- that is the whole point of the field-level split in
       sql/sairnsenior_visits_schema.sql.
  5-6  the payroll verb is registered and the handler calls the engine.
  7    sairnsenior.html calls it, not in a comment.
  8    a FLOOR reaches the screen as "at least", not as a total.
  9    a failed call is not rendered as a period in which nobody earned
       anything -- indistinguishable from a real empty period, and only one of
       them means somebody is unpaid.

AND SIX MUTATION ARMS put each defect back.

COMMENTS ARE STRIPPED BEFORE EVERY CODE SEARCH, and arm 0 drives the stripper
with fixtures in both directions: the broken state MENTIONED all three field
names in comments, so a raw-text search would have passed on it.
"""
import io
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(REPO, 'sairnsenior.html')
HANDLER = os.path.join(REPO, 'api', 'sd-data.js')
REGISTRY = os.path.join(REPO, 'api', '_resources', 'sairnsenior.js')

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        fails.append(name)


def strip_comments(js):
    """Blank // and /* */ spans, string-aware, preserving length."""
    out = list(js)
    i, n = 0, len(js)
    while i < n:
        c = js[i]
        if c in '\'"`':
            q, i = c, i + 1
            while i < n:
                if js[i] == '\\':
                    i += 2
                    continue
                if js[i] == q:
                    i += 1
                    break
                i += 1
            continue
        if c == '/' and i + 1 < n and js[i + 1] == '/':
            while i < n and js[i] != '\n':
                out[i] = ' '
                i += 1
            continue
        if c == '/' and i + 1 < n and js[i + 1] == '*':
            j = js.find('*/', i + 2)
            j = n if j == -1 else j + 2
            for k in range(i, j):
                if out[k] != '\n':
                    out[k] = ' '
            i = j
            continue
        i += 1
    return ''.join(out)


def raw_of(p):
    return io.open(p, encoding='utf-8', errors='replace').read()


# (record field, form control id, the expression that reads it back on edit)
ROUND_TRIPS = [
    ('service_type', 'vs-service-type', r"\$\('vs-service-type'\)\.value=''"),
    ('member_id', 'cl-member-id', r"\$\('cl-member-id'\)\.value=c\.member_id"),
    ('state_caregiver_id', 'cg-state-id',
     r"\$\('cg-state-id'\)\.value=c\.state_caregiver_id"),
]


def round_trip(raw, code, field, control, readback):
    """The control exists in the MARKUP, the save path writes the field, and
    the edit path reads it back. All three or the field is decoration."""
    has_control = ("id=\"%s\"" % control) in raw
    writes = re.search(r'\b' + re.escape(field) + r'\s*:', code) is not None
    reads = re.search(readback, code) is not None
    return has_control and writes and reads


def service_type_is_scheduling(h):
    """It must be in the SCHEDULE allow-list and NOT in the EVV one."""
    sched = re.search(r'SEN_VISIT_SCHEDULE_FIELDS\s*=\s*\[(.*?)\]', h, re.S)
    evv = re.search(r'SEN_VISIT_EVV_FIELDS\s*=\s*\[(.*?)\]', h, re.S)
    if not sched or not evv:
        return False
    return "'service_type'" in sched.group(1) and "'service_type'" not in evv.group(1)


def verb_registered(reg):
    return "'payroll'" in reg


HANDLER_BRANCH = re.compile(r"action\s*===\s*'payroll'")
HANDLER_CALL = re.compile(r"senPayroll\s*\.\s*computePayroll\s*\(")
CLIENT_CALL = re.compile(r"senData\s*\(\s*'payroll'\s*,\s*'sen_visits'")


def handler_calls(h):
    return bool(HANDLER_BRANCH.search(h)) and bool(HANDLER_CALL.search(h))


def client_calls(app):
    return bool(CLIENT_CALL.search(app))


def floor_reaches_the_screen(app):
    return ('is_floor' in app
            and re.search(r"d\.is_floor\s*\?", app) is not None
            and re.search(r"c\.is_floor\s*\?\s*'at least '", app) is not None)


def failure_is_not_an_empty_period(app):
    """A failed call must not render as a run in which nobody earned anything."""
    return re.search(r"if\s*\(\s*!d\s*\)\s*\{[\s\S]{0,400}?Nothing was computed", app) is not None


print('SAIRNsenior EVV capture + payroll wiring -- the fields must round-trip '
      'and the engine must be reached\n')

for p in (APP, HANDLER, REGISTRY):
    if not os.path.isfile(p):
        print('COULD NOT RUN: no %s. Nothing was verified.' % p)
        sys.exit(3)

RAW_APP, RAW_H, RAW_REG = raw_of(APP), raw_of(HANDLER), raw_of(REGISTRY)
APP_CODE, H_CODE, REG_CODE = (strip_comments(RAW_APP), strip_comments(RAW_H),
                              strip_comments(RAW_REG))

# ── ARM 0: THE STRIPPER ─────────────────────────────────────────────────
check('0a. a call that exists ONLY in a comment does NOT count as wired',
      not client_calls(strip_comments(
          "// senData('payroll','sen_visits',{})\nvar x=1;\n")),
      'the pre-repair file mentioned all of these in comments')
check('0b. ...and a real call DOES count',
      client_calls(strip_comments("senData('payroll','sen_visits',{},true);\n")))
check('0c. ...and a `//` inside a string does not eat the line',
      'var y=2;' in strip_comments("var u='https://x/y'; var y=2;\n"))

# ── ARMS 1-3: THE THREE FEDERAL FIELDS ROUND-TRIP ───────────────────────
for field, control, readback in ROUND_TRIPS:
    check('%s is captured, saved AND read back on edit' % field,
          round_trip(RAW_APP, APP_CODE, field, control, readback),
          'a field that saves but never reloads silently blanks itself on the '
          'next edit, which is worse than not having it')

# ── ARM 4: THE SPLIT ────────────────────────────────────────────────────
check('4. service_type is a SCHEDULING field server-side, never an EVV one',
      service_type_is_scheduling(H_CODE),
      'in the EVV set, the person being PAID for the visit would also choose '
      'which service was billed')

# ── ARMS 5-9: PAYROLL IS REACHED AND HONEST ─────────────────────────────
check('5. the payroll verb is REGISTERED', verb_registered(REG_CODE))
check('6. the handler branch CALLS the engine', handler_calls(H_CODE))
check('7. sairnsenior.html actually CALLS it (not in a comment)',
      client_calls(APP_CODE))
check('8. a FLOOR reaches the screen as "at least", not as a total',
      floor_reaches_the_screen(APP_CODE))
check('9. a failed call is NOT rendered as a period in which nobody earned '
      'anything',
      failure_is_not_an_empty_period(APP_CODE),
      'an empty run and a failed run look identical, and only one of them '
      'means somebody is unpaid')

# ── MUTATIONS ───────────────────────────────────────────────────────────
MUTATIONS = [
    ('10. dropping the service_type control is REFUSED',
     RAW_APP, lambda s: s.replace('id="vs-service-type"', 'id="gone-"', 1),
     lambda raw, code: round_trip(raw, code, 'service_type', 'vs-service-type',
                                  ROUND_TRIPS[0][2])),
    ('11. saving member_id but never reading it back is REFUSED',
     RAW_APP, lambda s: s.replace("$('cl-member-id').value=c.member_id",
                                  "$('cl-member-id').value=''", 1),
     lambda raw, code: round_trip(raw, code, 'member_id', 'cl-member-id',
                                  ROUND_TRIPS[1][2])),
    ('12. moving service_type into the EVV field set is REFUSED',
     RAW_H, lambda s: s.replace(
         "'scheduled_end', 'service_type']", "'scheduled_end']", 1).replace(
         "'services_notes', 'status']", "'services_notes', 'status', 'service_type']", 1),
     lambda raw, code: service_type_is_scheduling(code)),
    ('13. reverting the client payroll call to a comment is REFUSED',
     RAW_APP, lambda s: CLIENT_CALL.sub("/* senData('payroll','sen_visits'", s, 1),
     lambda raw, code: client_calls(code)),
    ('14. removing the handler branch is REFUSED',
     RAW_H, lambda s: HANDLER_BRANCH.sub("action === 'never_'", s, 1),
     lambda raw, code: handler_calls(code)),
    ('15. presenting a FLOOR as a total is REFUSED',
     RAW_APP, lambda s: s.replace("c.is_floor?'at least '", "false?'at least '", 1),
     lambda raw, code: floor_reaches_the_screen(code)),
]
for label, raw, mutate, predicate in MUTATIONS:
    m = mutate(raw)
    if m == raw:
        check(label, False,
              'THE MUTATION PLANTED NOTHING -- its anchor no longer matches, so '
              'this arm is not testing what it says it tests. Fix the anchor, '
              'not the subject.')
        continue
    check(label, not predicate(m, strip_comments(m)),
          'the mutated file still passed the check it was built to break')

print('\n%d failure(s)' % len(fails))
for f in fails:
    print('  - ' + f)
sys.exit(1 if fails else 0)
