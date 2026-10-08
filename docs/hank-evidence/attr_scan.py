# READ-ONLY BY CONSTRUCTION: this file opens api/sd-data.js once, for reading,
# and writes nothing anywhere. There is no io.open(..., 'w') and no subprocess.
# MY OWN READ of H1's routed 10-resource attribution finding -- not a re-run of
# their tool, which I have not seen.
#
# THE QUESTION, stated before the answer so the criteria cannot drift to fit it:
# for every WRITE branch belonging to SAIRNcare (alf_), SAIRNsenior (sen_) or
# SAIRNroofing (rf_ / sub_), does the row it persists carry the identity of the
# EMPLOYEE WHO WROTE IT -- taken from the session, not from the payload?
#
# AN ACTOR FIELD IS ONE OF THESE, and the list is written down rather than
# pattern-guessed: a column or blob key assigned from session.employee_id, or a
# writeAuditLog call naming the session. A caller-supplied value does NOT count
# and is reported separately, because a field the caller can set describes the
# request rather than the answer.
import io
import re

SRC = io.open(r'C:\Users\marsh\Documents\SAIRN-hank\api\sd-data.js',
              encoding='utf-8').read()
LINES = SRC.split('\n')

PREFIX = {'alf_': 'SAIRNcare', 'sen_': 'SAIRNsenior',
          'rf_': 'SAIRNroofing', 'sub_': 'SAIRNroofing'}

OPEN = re.compile(r"^\s*if \(resource === '([a-z0-9_]+)'\s*&&\s*"
                  r"(?:\(?\s*)?action === '(\w+)'")

# Session-derived actor. `session.employee_id` is the only way this platform
# names the acting employee; `caller.employee_id` is the auth endpoints' name
# for the same thing.
ACTOR = re.compile(r'(?:session|caller|employeeCaller|grdSession)\.employee_id')
# A write that PERSISTS something: a POST or PATCH through rest().
PERSIST = re.compile(r"method: '(POST|PATCH|PUT)'")
AUDIT = re.compile(r'writeAuditLog\(')
# A caller-supplied actor -- reported, never counted as attribution.
PAYLOAD_ACTOR = re.compile(r'(?:recorded_by|created_by|updated_by|updatedBy|'
                           r'verified_by|captured_by_id)\s*[:=]\s*(?:payload|body)\.')


def blocks():
    hits = [(i, m) for i, l in enumerate(LINES, 1) for m in [OPEN.match(l)] if m]
    for n, (i, m) in enumerate(hits):
        end = hits[n + 1][0] - 1 if n + 1 < len(hits) else len(LINES)
        yield i, m.group(1), m.group(2), '\n'.join(LINES[i - 1:end])


rows = []
for line, res, action, body in blocks():
    pre = next((p for p in PREFIX if res.startswith(p)), None)
    if pre is None:
        continue
    # NO ACTION ALLOWLIST. The first version of this scan filtered to eleven
    # action names I thought of, found 8 where H1 reported 10, and the
    # difference was MY OWN FILTER -- an allowlist of what I expected rather
    # than the population. Every branch that PERSISTS is in scope, whatever it
    # is called. recurring-bug-class 24: a bucketing pattern must account for
    # 100% of its input.
    if not PERSIST.search(body):
        continue
    rows.append({
        'app': PREFIX[pre], 'res': res, 'action': action, 'line': line,
        'actor': bool(ACTOR.search(body)),
        'audit': bool(AUDIT.search(body)),
        'payload_actor': bool(PAYLOAD_ACTOR.search(body)),
    })

print('WRITE BRANCHES THAT PERSIST, in the three apps: %d' % len(rows))
print('')
print('%-14s %-28s %-14s %-7s %-6s %-6s %s'
      % ('app', 'resource', 'action', 'line', 'actor', 'audit', 'verdict'))
print('-' * 104)
gap = []
for r in sorted(rows, key=lambda x: (x['app'], x['res'], x['action'])):
    ok = r['actor'] or r['audit']
    v = 'attributed' if ok else '** NO ACTOR RECORDED **'
    if not ok:
        gap.append(r)
    if r['payload_actor']:
        v += '  (and a CALLER-SUPPLIED actor field is present)'
    print('%-14s %-28s %-14s :%-6d %-6s %-6s %s'
          % (r['app'], r['res'], r['action'], r['line'],
             r['actor'], r['audit'], v))
print('')
print('UNATTRIBUTED: %d of %d' % (len(gap), len(rows)))
by = {}
for r in gap:
    by.setdefault(r['app'], []).append('%s/%s :%d' % (r['res'], r['action'], r['line']))
for a in sorted(by):
    print('  %-14s %d  %s' % (a, len(by[a]), ', '.join(by[a])))
print('')
print('LIMITS, printed rather than filed: this is LEXICAL. An actor recorded')
print('through a helper, or in a shared prelude above the branch, is invisible')
print('to it -- so the error direction is FALSE POSITIVE, it says "no actor"')
print('when one may be a frame away. Every row above must be read before it is')
print('called a defect, and the fix list below was read.')
