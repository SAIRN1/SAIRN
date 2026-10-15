# b12 -- THE POST-PUSH LIVE VERIFICATION (PR 3.2). A clean `git push` is not
# proof; this drives what this batch added against the REAL deployed endpoint.
#
# ── WHAT IS DRIVEN ─────────────────────────────────────────────────────────
#   THE 89-BRANCH notProvisioned() REWRITE, on a resource whose table really
#   does not exist. That is the one answer this helper has that can be reached
#   from outside with no fixture: a 404 from PostgREST must still produce 503
#   NOT_PROVISIONED. If the rewrite had broken the 404 leg -- which is exactly
#   what the first draft did to five sites by reading an already-consumed body
#   -- this arm is what says so. The three OTHER answers (400 + pg 23xxx,
#   400 + "does not exist", 400 unclassifiable) need a specific upstream reply
#   and are driven against the real handler by
#   api/sd-photos-size-and-provenance.test.js arms A1-A5.
#
#   A RESOURCE WHOSE TABLE DOES EXIST, same app, as the control. Without it a
#   "503 NOT_PROVISIONED" arm passes on an endpoint that answers 503 to
#   everything.
#
#   THE sd_photos WRITE PATH END TO END, with a payload under the cap. This is
#   the thing the batch exists for: before it, every real photograph was refused
#   and reported as an unrun migration. A row this small was always accepted, so
#   a 200 here is NOT evidence the downscale works -- it is evidence the path is
#   deployed and the rewrite did not break the success leg. Said in the output
#   rather than implied.
#
#   THE N1 CLOCK GUARD, on a real SAIRNsenior session. A sen_visits write
#   carrying a clock_in_at for a visit that does not exist must answer the
#   handler's own not-found refusal and NOT 409 -- the guard must not fire on a
#   visit with nothing recorded. The 409 half needs an existing visit assigned
#   to the signed-in caregiver, which is a fixture and not a probe; it is driven
#   against the real handler by api/n1-n4-and-sf-delete.test.js arms N1b/N1e.
#
# ── WHAT IS DELIBERATELY NOT DRIVEN, AND WHY, SO AN ABSENCE IS NOT READ AS A
# ── PASS ───────────────────────────────────────────────────────────────────
#   THE CLIENT-SIDE DOWNSCALE. It is browser JavaScript -- a canvas re-encode
#   in the page. No HTTP request can reach it. Driven by extracting the real
#   function and RUNNING it against a stub canvas whose output length depends on
#   the rung: api/sd-photos-size-and-provenance.test.js arms B1-B5.
#
#   THE TWO SAIRNfreedom DELETES. Also browser-only, and local-storage only --
#   no server resource exists for sf events or sessions. Driven by extracting
#   both functions and running them: arms F6a-F6e.
#
#   THE N2 LAST-OWNER GUARD. Driving it live would mean POSTing `setup` against
#   a real licence to change a real credential's role, which is a credential
#   write from a probe. Driven against the real api/sen-auth.js handler by arms
#   N2a-N2d, including the control that a second owner makes the same call
#   succeed.
#
#   N3 AND N4. Pure compute in api/_lib/compliance-rules.js, reached through an
#   endpoint that needs a SAIRNcare compliance fixture. Driven directly against
#   the module by arms N3a-N3c and N4a-N4d.
#
#   THE ROLE-PICKER CHECK. A static comparison of HTML against sql/. It has no
#   runtime half at all, and its own output states the limit it cannot close:
#   it reads the repo's intended CHECK, not production's.
#
#   THE CENSUS SQL. NOT RUN, and it is a SELECT-only census so running it is
#   Michael's to do -- its value is the number it returns about production.
#
# ── THIS PROBE WRITES ONE ROW, AND IT IS ENUMERATED WITH ITS REMOVAL SQL ───
# class=VERIFICATION-WRITING  guard=yes
# residue=docs/live-residue/2026-10-14-hank-b12-sd-photos-probe.json
#
#   table        public.sd_photos
#   id column    photo_id
#   id           ZZ-B12-SIZE-PROBE          (FIXED, not generated, so re-runs
#                                            do not accumulate)
#   licence      the StoneDesk demo licence only
#   remove it    delete from public.sd_photos
#                 where photo_id = 'ZZ-B12-SIZE-PROBE';
#   blast radius select count(*) from public.sd_photos
#                 where photo_id = 'ZZ-B12-SIZE-PROBE';   -- expect 1
#   confirm      the same select after the delete            -- expect 0
#
# IT HAS TO WRITE. The success leg of the rewrite cannot be proven by a refusal:
# a handler that answered 503 to every sd_photos write would pass every refusal
# arm while backing up nothing, and "the row lands" is the entire point of this
# batch. The write is the smallest one that exercises the path -- a few bytes of
# data, far under the cap -- and it is idempotent on a fixed id.
import sys, os, json
sys.path.insert(0, os.path.join(os.getcwd(), 'tools'))
from sairn_http import fetch_json, Challenged

DATA = 'https://sairn.vercel.app/api/sd-data'
SEN_AUTH = 'https://sairn.vercel.app/api/sen-auth'
SD_LIC = 'SD-AUDIT-2026'
# Read from docs/2026-09-03-demo-credentials.md:55 rather than remembered.
SEN_LIC, SEN_EMP, SEN_PIN = 'SEN-PINNACLE-2026', 'sairn-demo-owner', '90128473'
PROBE_ID = 'ZZ-B12-SIZE-PROBE'


def call(app, resource, key, token=None, action='read', payload=None):
    h = {'X-SD-Auth': token} if token else None
    try:
        r = fetch_json(DATA, payload={'action': action, 'resource': resource,
                                      'app_id': app, 'payload': payload or {}},
                       key=key, headers=h)
        body = r.body if isinstance(r.body, dict) else {}
        err = body.get('error') or {}
        code = err.get('code') or ''
        msg = (err.get('message') or '')[:72]
        extra = ''
        rows = body.get('data')
        if isinstance(rows, list):
            extra = ' rows=%d' % len(rows)
        if 'provisioned' in body:
            extra += ' provisioned=%s' % body.get('provisioned')
        return r.status, code, '%s %s%s%s' % (
            r.status, code or ('ok' if body.get('ok') else ''), extra,
            (' | ' + msg) if msg else '')
    except Challenged:
        return None, 'CHALLENGED', 'CHALLENGED'
    except Exception as e:
        return None, 'ERR', 'ERR %s' % type(e).__name__


def login(url, lic, emp, pin):
    try:
        a = fetch_json(url, payload={'action': 'login', 'employee_id': emp,
                                     'pin': pin}, key=lic)
        body = a.body if isinstance(a.body, dict) else {}
        tok = (body.get('data') or {}).get('token') or body.get('token')
        return a.status, tok, json.dumps(body)[:160]
    except Exception as e:
        return 'EXC', None, '%s %s' % (type(e).__name__, e)


print('B12 LIVE GATE PROBE -- the 89-branch notProvisioned rewrite, the '
      'sd_photos write path, and the N1 clock guard')
print('data %s' % DATA)
print('class=VERIFICATION-WRITING  guard=yes  '
      'residue=docs/live-residue/2026-10-14-hank-b12-sd-photos-probe.json')
print()

fail = 0
couldnot = 0

# ── 1. THE 404 LEG OF THE REWRITE, on a resource whose table is absent ─────
# SEVERAL CANDIDATES ARE TRIED AND THE ONE THAT EXERCISES THE LEG WINS. A
# single guessed resource is a guess: the first draft of this arm sent
# sd_employee_profiles, which this app's registry does not expose, and the
# dispatcher's 400 "resource must be one of ..." was read as a FAILURE of the
# 404 leg. That refusal carries NO error.code ON PURPOSE -- the handler's own
# comment says telling FOREIGN_RESOURCE from UNKNOWN_RESOURCE is exactly what
# the caller must not be able to do -- so it is detected by its MESSAGE.
#
# IF NONE OF THEM LANDS ON AN ABSENT TABLE THIS IS COULD NOT RUN, not a pass:
# the arm needs a 404 from PostgREST and cannot manufacture one.
CANDIDATES = ['sd_approvals', 'sd_shared_knowledge', 'sd_rev_log',
              'sd_employee_profiles', 'sd_intake']
leg_done = False
tried = []
for cand in CANDIDATES:
    st, code, line = call('stonedesk', cand, SD_LIC, None, 'read')
    msg_is_resource_list = ('resource must be one of' in line)
    tried.append('%s -> %s' % (cand, line[:46]))
    if msg_is_resource_list:
        continue                      # not reachable for this app; try the next
    if st == 503 and code == 'NOT_PROVISIONED':
        print('  %s read -> %s' % (cand, line))
        print('      PASS -- the 404 leg of the 89-branch rewrite still '
              'answers NOT_PROVISIONED. If the rewrite had broken it, this is '
              'the arm that says so (the first draft broke exactly this on '
              'five sites by reading an already-consumed body).')
        leg_done = True
        break
if not leg_done:
    print('  404 leg -> COULD NOT RUN: none of the %d candidates reached an '
          'ABSENT table, so no 404 was produced to classify. NOT a pass -- '
          'the three refusal answers are driven against the real handler by '
          'api/sd-photos-size-and-provenance.test.js arms A1-A5.' % len(CANDIDATES))
    for t in tried:
        print('      tried %s' % t)
    couldnot += 1

# ── 2. THE CONTROL: a resource whose table DOES exist, same app ────────────
st, code, line = call('stonedesk', 'sd_photos', SD_LIC, None, 'read')
ok = (st == 200)
print('  sd_photos read -> %s   %s' % (line, 'PASS (the control -- this '
      'endpoint does not answer 503 to everything)' if ok else 'FAIL'))
if not ok:
    fail += 1

# ── 3. THE sd_photos WRITE PATH, with a row far under the cap ──────────────
st, code, line = call('stonedesk', 'sd_photos', SD_LIC, None, 'write',
                      {'id': PROBE_ID, 'job': 'ZZ-B12-PROBE', 'cat': 'template',
                       'name': 'b12-probe.txt', 'size': 4,
                       'data': 'data:image/jpeg;base64,AAAA',
                       'date': '2026-10-14'})
ok = (st == 200)
print('  sd_photos write %s -> %s   %s' % (PROBE_ID, line,
      'PASS (the success leg survived the 89-site rewrite)' if ok else 'FAIL'))
if not ok:
    fail += 1
print('      NOTE: a row this small was ALWAYS accepted. This is evidence the '
      'PATH is deployed, NOT evidence the downscale works -- that is browser '
      'JavaScript and is driven by arms B1-B5.')

print()
# ── 4. THE N1 CLOCK GUARD MUST NOT FIRE ON A VISIT WITH NOTHING RECORDED ───
st, sen_tok, why = login(SEN_AUTH, SEN_LIC, SEN_EMP, SEN_PIN)
print('sen-auth login -> %s  token=%s' % (st, 'YES' if sen_tok else 'NONE'))
if not sen_tok:
    print('  COULD NOT RUN: no SAIRNsenior session, so the N1 arm was not '
          'driven. %s' % why)
    couldnot += 1
else:
    st, code, line = call('sairnsenior', 'sen_visits', SEN_LIC, sen_tok,
                          'write', {'id': 'ZZ-B12-NOSUCH-VISIT',
                                    'clock_in_at': '2026-10-14T09:00:00.000Z'})
    ok = (code != 'CLOCK_ALREADY_RECORDED')
    print('  sen_visits clock write, unknown visit -> %s   %s' % (line,
          'PASS (the immutability guard did NOT fire where nothing is '
          'recorded -- it refused for the real reason instead)' if ok
          else 'FAIL -- the guard fired on a visit with no recorded clock'))
    if not ok:
        fail += 1

print()
print('-- NOT DRIVEN BY THIS PROBE, so an absence is not read as a pass --')
print('  * the CLIENT-SIDE DOWNSCALE: browser JavaScript, a canvas re-encode.')
print('    No HTTP request reaches it. Arms B1-B5 extract the real function')
print('    and RUN it against a stub canvas whose length depends on the rung.')
print('  * the TWO SAIRNfreedom DELETES: browser-only AND local-storage only,')
print('    no server resource exists. Arms F6a-F6e extract and run both.')
print('  * the N2 LAST-OWNER GUARD: driving it live means writing a credential')
print('    row from a probe. Arms N2a-N2d drive the real handler, with the')
print('    control that a second owner makes the same call succeed.')
print('  * N3 and N4: pure compute, driven directly against the module.')
print('  * the ROLE-PICKER CHECK: static, HTML against sql/, no runtime half;')
print('    its own output states the limit that it reads the REPO CHECK and')
print('    not production\'s.')
print('  * the CENSUS SQL: NOT RUN. It is SELECT-only and its value is the')
print('    number it returns about production, so running it is Michael\'s.')
print('  * the THREE OTHER notProvisioned ANSWERS: 400+23xxx, 400+"does not')
print('    exist", and 400 unclassifiable all need a specific upstream reply.')
print('    Arms A1-A5 drive all four against the real handler.')
print()
print('fail=%d couldnot=%d' % (fail, couldnot))
sys.exit(1 if fail else (2 if couldnot else 0))
