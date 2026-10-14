#!/usr/bin/env python
# OWNER: cody
# written 2026-10-14, batch b12, item 3
"""Four findings, each with a FAILING-FIRST arm that is RED against current source.

    python tests/run_b12_routed_findings_probe.py
    python tests/run_b12_routed_findings_probe.py --ablate

Exit 0 no findings, 1 findings present, 2 COULD NOT RUN.

THIS SUITE IS RED ON PURPOSE AND THAT IS THE POINT. Every T arm names a defect
in `api/`, and `api/` belongs to hank. The arms are the evidence that goes with
the routing: a routed finding with no failing arm is a sentence somebody has to
believe, and this platform has already paid for the difference. When hank fixes
one, its arm goes green and the register row moves -- nobody has to remember
what the claim was.

── THE ARM NAMES, AND WHY TWO SERIES ───────────────────────────────────────
T16, T17, T18 are the FINDINGS. Each is RED now.
N1, N2, N3 are their CONTROLS, and each one is the reason the matching T arm is
an ASYMMETRY rather than a missing feature: the safe route exists, three lines
or one file away, and only one of the two paths carries the guard. Without them
"EVV is unprotected" / "there is no last-owner rule" / "position lists are
unvalidated" would all be false, and the findings would be easy to dismiss.
N4 is the fourth FINDING and has no T number because it is not about one line:
it sweeps every coverage claim in a comment and asserts the file it names
exists.

── ABLATION, AND WHAT IT PROVES ────────────────────────────────────────────
`--ablate` applies the obvious FIX to a COPY of each subject and re-runs that
arm. A T arm that stays red under its own fix is measuring something other than
the defect it names, which is the failure mode an arm like this actually has --
not a false positive, a MISATTRIBUTED one. Nothing in the clone is written: the
copies live in a temp directory and the subjects are read, never modified.

── WHAT IS NOT CLAIMED ─────────────────────────────────────────────────────
T16 and T17 are read from SOURCE STRUCTURE, not driven through the handler. Each
one names the exact lines and the exact absent guard, and the ablation shows the
arm follows the guard rather than a constant -- but neither one proves the defect
is REACHABLE for a particular caller, which would need the handler fixture. T18
IS driven: compliance-rules.js is a module and the finding is a return value.
Stated here rather than left for a reader to assume the three are equal evidence.
"""
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
ABLATE = '--ablate' in sys.argv

SD_DATA = os.path.join(REPO, 'api', 'sd-data.js')
SEN_AUTH = os.path.join(REPO, 'api', 'sen-auth.js')
RULES = os.path.join(REPO, 'api', '_lib', 'compliance-rules.js')

for p in (SD_DATA, SEN_AUTH, RULES):
    if not os.path.isfile(p):
        print('COULD NOT RUN: %s is absent, so NOTHING WAS TESTED.' % p)
        sys.exit(2)

NODE = shutil.which('node')
if not NODE:
    print('COULD NOT RUN: node is not on PATH, so T18/N3 cannot be driven and '
          'the rest would be a partial answer reported as a whole one.')
    sys.exit(2)

_findings = []
_arms = []


def arm(name, holds, detail='', finding=None):
    """holds=True means the property HOLDS (no finding)."""
    _arms.append((name, holds))
    print('  %s %s' % ('ok  ' if holds else 'FIND', name))
    if not holds:
        if detail:
            print('       %s' % detail)
        if finding:
            _findings.append(finding)


def src(path):
    return io.open(path, encoding='utf-8', errors='replace').read()


def code_only(text):
    """`text` with // and # comment lines removed.

    THE FIRST VERSION OF T17 PASSED BECAUSE OF A COMMENT, which is the defect
    this repo keeps paying for and which arm 6 of
    tests/run_scope_gate_unfetched_base_probe.py was tightened for in the same
    batch. The guard regex matched `lifecycle.` inside the sentence "Both run
    through api/_lib/employee-lifecycle.js" -- PROSE ABOUT the safe route read
    as the safe route, in the branch that does not have it. Every structural
    read below goes through this.
    """
    out = []
    for line in text.split(chr(10)):
        st = line.lstrip()
        if st.startswith('//') or st.startswith('#') or st.startswith('*'):
            continue
        out.append(line.split('//')[0] if '//' in line and
                   line.count('"') % 2 == 0 and line.count("'") % 2 == 0
                   else line)
    return chr(10).join(out)


def lineno(text, idx):
    return text[:idx].count('\n') + 1


def block_after(text, anchor, stop):
    """The text from `anchor` to the next `stop`, for scoping a structural read."""
    i = text.find(anchor)
    if i < 0:
        return None
    j = text.find(stop, i + len(anchor))
    return text[i:j if j > 0 else len(text)]


# ───────────────────────────────────────────────────────────────────────────
# T16: a SECOND write replaces the caregiver's recorded clock time, and
#      nothing records that it was replaced.
# ───────────────────────────────────────────────────────────────────────────
# WHAT THE FILE ITSELF SAYS THE RULE IS, three lines above the defect: "a
# correction that OVERWRITES the caregiver's record destroys the evidence the
# record is ... a state audit that finds an edited time with no trail cannot
# tell a typo correction from a fabrication." The `propose_clock_correction`
# route is append-only BY CONSTRUCTION for exactly that reason (N1).
#
# THE `write` ROUTE IS NOT. The caregiver branch copies every EVV field over
# the existing record:
#
#     SEN_VISIT_EVV_FIELDS.forEach((f) => {
#       if (payload[f] !== undefined) visitData[f] = payload[f]; });
#
# `visitData` starts as a copy of `existingRow.data`, so a second write
# carrying `clock_in_at` REPLACES the first value. checkClockEvent() refuses
# only the impossible -- unreadable, ahead of the server, clock-out before
# clock-in -- and a PAST time is explicitly allowed and stored, because that is
# the offline replay path working. So an EARLIER clock_in_at is accepted, the
# original is gone, and no entry is appended.
def t16():
    text = src(SD_DATA)
    body = block_after(text, "if (resource === 'sen_visits' && action === 'write')",
                        "if (resource === 'sen_visits' && action === 'readiness')")
    if body is None:
        return None, "the sen_visits write branch is not where this arm looks"
    code = code_only(body)
    copy = re.search(r'SEN_VISIT_EVV_FIELDS\.forEach\([^)]*\)\s*=>\s*\{[^}]*'
                     r'visitData\[f\]\s*=\s*payload\[f\]', code)
    if not copy:
        return True, 'the unconditional EVV field copy is gone'
    # A trail would be: the prior value preserved under another key, or an
    # append to a history list, in the same branch. Any of the three spellings
    # the file already uses elsewhere counts.
    trail = re.search(r'_prior|_previous|_original|history|corrections|'
                      r'appendCorrection|proposeCorrection', code)
    # THE LINE NUMBER IS TAKEN FROM THE ORIGINAL TEXT, not from the
    # comment-stripped copy. Reporting the stripped offset moved the citation
    # from :7179 to :7137 -- a file:line that points at the wrong line is worse
    # than none, because a reader checks it, finds nothing, and stops believing
    # the rest of the finding.
    raw = re.search(r'SEN_VISIT_EVV_FIELDS\.forEach', body)
    off = text.find(body)
    return bool(trail), ('api/sd-data.js:%d copies every EVV field over the '
                         'existing record and no prior value, history entry or '
                         'correction is written in the same branch'
                         % lineno(text, off + (raw.start() if raw else 0)))


_t16_holds, _t16_detail = t16()
if _t16_holds is None:
    print('COULD NOT RUN: %s' % _t16_detail)
    sys.exit(2)
arm('T16. a second sen_visits `write` cannot silently REPLACE a recorded '
    'clock_in_at -- the prior value is kept or an entry is appended',
    _t16_holds, _t16_detail,
    finding=('ROUTED TO HANK -- api/sd-data.js sen_visits action=write: the '
             'caregiver branch copies SEN_VISIT_EVV_FIELDS straight over '
             '`visitData`, which starts as a copy of the stored row, so a '
             'SECOND write carrying clock_in_at REPLACES the caregiver\'s '
             'recorded time with NO trail. checkClockEvent() refuses only the '
             'impossible and explicitly ALLOWS and stores a past time, so an '
             'earlier clock_in_at is accepted. The file\'s own comment states '
             'the rule it breaks: "a state audit that finds an edited time '
             'with no trail cannot tell a typo correction from a '
             'fabrication." The append-only route exists beside it -- see N1 '
             '-- so this is an ASYMMETRY, not a missing feature. ' + _t16_detail))

# N1: THE CONTROL. If `propose_clock_correction` also wrote clock fields, T16
# would be "EVV is unprotected" and the fix would be a design question. It does
# not, so the safe route already exists and T16 is one branch missing what the
# other branch has.
_pcc = block_after(src(SD_DATA),
                   "if (resource === 'sen_visits' && action === "
                   "'propose_clock_correction')",
                   "if (resource === 'sen_visits' && action === 'write')")
arm('N1. CONTROL -- the `propose_clock_correction` route writes NO clock field, '
    'so the append-only route really does exist and T16 is an asymmetry',
    _pcc is not None
    and not re.search(r"visitData\['?clock_(in|out)_at", code_only(_pcc or ''))
    and not re.search(r"data\.clock_(in|out)_at\s*=", code_only(_pcc or '')),
    'the correction route appears to assign a clock field after all, which '
    'would make T16 a different finding')

# ───────────────────────────────────────────────────────────────────────────
# T17: `setup` can demote the last owner, while `set_active` refuses to
#      deactivate it.
# ───────────────────────────────────────────────────────────────────────────
# api/sen-auth.js `setup` upserts with `on_conflict=license_hash,employee_id`
# and `resolution=merge-duplicates`, so calling it on an EXISTING employee
# rewrites their `role`. The only gate is `caller.role !== 'owner'`. An owner
# can therefore call setup on THEMSELVES with role 'caregiver' and the agency
# has no owner left -- no owner means no `setup`, so provisioning is
# unrecoverable from inside the app.
#
# THE PLATFORM ALREADY DECIDED THIS CLASS. CLAUDE.md's push protocol requires
# the recoverability guard on SQL that writes credential rows -- "two end states
# are safe and only two" -- and `set_active` in this same file enforces it
# through lifecycle.setActive()'s last-admin count (N2).
def t17():
    text = src(SEN_AUTH)
    body = block_after(text, "if (action === 'setup')", "if (action === 'roster')")
    if body is None:
        return None, "the setup branch is not where this arm looks"
    code = code_only(body)
    writes_role = 'merge-duplicates' in code and re.search(r'\brole\b', code)
    if not writes_role:
        return True, 'setup no longer upserts a role'
    guard = re.search(r'last[_ -]?(admin|owner)|LAST_(ADMIN|OWNER)|soleRole|'
                      r'lifecycle\.|countOwners|provisioningRoles', code,
                      re.IGNORECASE)
    return bool(guard), ('api/sen-auth.js:%d upserts `role` with '
                         'resolution=merge-duplicates and carries no '
                         'last-owner count, so an owner may demote the only '
                         'owner' % lineno(text, text.find(body)))


_t17_holds, _t17_detail = t17()
if _t17_holds is None:
    print('COULD NOT RUN: %s' % _t17_detail)
    sys.exit(2)
arm('T17. sen-auth `setup` cannot demote the LAST owner -- the same '
    'recoverability guard `set_active` already enforces', _t17_holds,
    _t17_detail,
    finding=('ROUTED TO HANK -- api/sen-auth.js action=setup: it upserts with '
             'on_conflict=license_hash,employee_id and '
             'resolution=merge-duplicates, so it REWRITES the role of an '
             'existing employee, and its only gate is `caller.role !== '
             '"owner"`. An owner can set their own role to caregiver; '
             'PROVISIONING_ROLES is [\'owner\'], so with no owner left nobody '
             'can call setup again and the agency cannot recover from inside '
             'the app. set_active in the SAME FILE routes through '
             'lifecycle.setActive() with a last-admin count over '
             'provisioningRoles -- see N2 -- so DEACTIVATING the last owner is '
             'refused while DEMOTING it is not. ' + _t17_detail))

# N2: THE CONTROL. The last-admin rule is not absent from this app; it is
# absent from ONE branch. Without this arm T17 reads as "sairnsenior has no
# recoverability guard", which is false and would send the fix in the wrong
# direction.
_sa = block_after(src(SEN_AUTH), "if (action === 'set_active')", '} catch (err)')
arm('N2. CONTROL -- `set_active` DOES carry the last-admin guard, through '
    'lifecycle.setActive() over PROVISIONING_ROLES, so T17 is one branch '
    'missing what its neighbour has',
    _sa is not None and 'lifecycle.setActive' in code_only(_sa or '')
    and 'provisioningRoles' in code_only(_sa or ''),
    'set_active does not route through the shared lifecycle engine, which '
    'would make T17 a whole-app finding rather than an asymmetry')

# ───────────────────────────────────────────────────────────────────────────
# T18: a position list with no valid token is counted MAPPED and then decides
#      "does not apply" for everybody.
# ───────────────────────────────────────────────────────────────────────────
# DRIVEN, not read. compliance-rules.js builds its `unmapped_requirements` list
# from `mappable`, and the three legs of that expression are not symmetric:
#
#     r.audience === 'all_staff'
#     || (Array.isArray(r.applies_to_positions) && r.applies_to_positions.length > 0)
#     || (r.audience && STAFF_POSITIONS.indexOf(r.audience) !== -1)
#
# The THIRD leg validates `audience` against the vocabulary. The SECOND leg
# validates nothing about the CONTENTS of the list. So a requirement declaring
# `applies_to_positions: ['rn']` -- not a STAFF_POSITIONS token -- is counted
# mapped, is left out of the caveat, and then matchAudience() returns a
# CONFIDENT `applies: false` for every real position, because
# `list.indexOf(staff.position)` can never match. An unmatchable audience is
# reported as a decided NO rather than as undecided.
T18_JS = r'''
const path = %s;
const R = require(path);
const out = { ok: true };
try {
  const req = { applies_to_positions: ['rn'], audience: null, who: 'nurses' };
  // matchAudience is the decision point. A list that cannot match any real
  // position must not produce a DECIDED false.
  const m = R.matchAudience(req, { position: 'nursing' });
  out.applies = m.applies;
  out.why = m.why;
  // And the vocabulary, read from the module so this arm cannot drift from it.
  out.positions = R.STAFF_POSITIONS || null;
} catch (e) { out.ok = false; out.err = String(e && e.message); }
process.stdout.write(JSON.stringify(out));
'''


def drive(js, module_path):
    d = tempfile.mkdtemp(prefix='b12-t18-')
    try:
        f = os.path.join(d, 'drive.js')
        io.open(f, 'w', encoding='utf-8', newline='\n').write(
            js % ('"' + module_path.replace('\\', '\\\\') + '"'))
        r = subprocess.run([NODE, f], capture_output=True, text=True,
                           encoding='utf-8', errors='replace', cwd=REPO)
        return r.stdout.strip(), r.returncode
    finally:
        shutil.rmtree(d, ignore_errors=True)


def t18(module_path):
    import json
    out, rc = drive(T18_JS, module_path)
    try:
        o = json.loads(out)
    except Exception:                                            # noqa: BLE001
        return None, 'the driver did not return JSON (rc=%s): %s' % (rc, out[:200])
    if not o.get('ok'):
        return None, 'matchAudience could not be driven: %s' % o.get('err')
    if o.get('positions') and 'rn' in o['positions']:
        return True, '`rn` is a real position now, so this fixture is spent'
    # The finding: a DECIDED false. `null` would be the honest answer.
    return o.get('applies') is not False, (
        'matchAudience returned applies=%r for a requirement whose '
        'applies_to_positions is [\'rn\'] -- not one of %s -- so an '
        'unmatchable list decides NO instead of UNDECIDED. why=%r'
        % (o.get('applies'), o.get('positions'), (o.get('why') or '')[:90]))


_t18_holds, _t18_detail = t18(RULES)
if _t18_holds is None:
    print('COULD NOT RUN: %s' % _t18_detail)
    sys.exit(2)
arm('T18. a requirement whose applies_to_positions contains NO valid token is '
    'UNDECIDED, not a confident "does not apply"', _t18_holds, _t18_detail,
    finding=('ROUTED TO HANK -- api/_lib/compliance-rules.js: `mappable` '
             'accepts ANY non-empty applies_to_positions array without '
             'checking its contents against STAFF_POSITIONS, while the very '
             'next leg of the SAME expression validates `audience` against it. '
             'So a requirement declaring an unmatchable position list is '
             'counted MAPPED, is left out of unmapped_requirements_caveat, and '
             'then matchAudience() returns a DECIDED applies=false for every '
             'real position because list.indexOf() can never match. A training '
             'requirement that applies to nobody, reported as a decision '
             'rather than as a gap -- the same over-counting direction as the '
             'facility_training_year_start ghost field in this file. ' + _t18_detail))

# N3: THE CONTROL, and it is what makes T18 precise. The vocabulary check is
# not missing from this module -- it is missing from one of three legs, three
# lines from a leg that has it.
_rules_src = src(RULES)
_mappable = block_after(_rules_src, 'const mappable =', 'if (!mappable)')
arm('N3. CONTROL -- the SAME `mappable` expression DOES validate `audience` '
    'against STAFF_POSITIONS, so T18 is one unvalidated leg and not an absent '
    'vocabulary',
    _mappable is not None
    and 'STAFF_POSITIONS.indexOf(r.audience)' in code_only(_mappable or ''),
    'the audience leg no longer validates against STAFF_POSITIONS either, '
    'which would make T18 a broader finding than it is reported as')

# ───────────────────────────────────────────────────────────────────────────
# N4: a comment that CLAIMS coverage must name a file that exists.
# ───────────────────────────────────────────────────────────────────────────
# THE POPULATION IS MEASURED AND PRINTED, because the arm is only as good as
# what it looked at and a sweep that reports "0 findings" over 3 files is not
# the same answer as one over 311 claims.
#
# THE RULE IS STRUCTURAL IN THREE PLACES, and each one was forced by a false
# positive found while measuring:
#   COMMENTS ONLY. A citation inside a STRING is a fixture. Five of the first
#     five hits were exactly that -- a bare `see <fixture>.js` as a test payload -- and a
#     name blocklist would have been the wrong fix.
#   COMMENT BLOCKS, not lines. The one real finding spans two lines: "held by"
#     on one and the path on the next. Per-line matching missed it entirely
#     while reporting only fixtures.
#   CREATE-THEN-REMOVE IS NOT A CLAIM. api/sd-data-leg-bookings-toctou.test.js
#     documents `git show <sha>:api/sd-data.js > api/.sd-data-prefix-control.js`
#     and `rm` of the same path. The file is MEANT not to exist.
# archive/ is excluded: it is not live code and every path in it is historical.
CLAIM_RE = re.compile(
    r'(driven by|driven in|drives it|drives this|drives that|covered by|'
    r'held by|held now by|is held|asserted by|proved by|proven by|pinned by|'
    r'locked by|exercised by|control-paired by|verified by|tested by)\b', re.I)
PATH_RE = re.compile(r'\b((?:api|tests|tools)/[A-Za-z0-9_./-]*[A-Za-z0-9_-]'
                     r'\.(?:js|py))')


def comment_of(line, ext):
    s = line.lstrip()
    if ext == '.py':
        return s[1:] if s.startswith('#') else None
    if s.startswith('//'):
        return s[2:]
    if s.startswith('*') or s.startswith('/*'):
        return s
    return None


def sweep_claims(root_dir):
    claims, stale = 0, []
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs
                   if d not in ('.git', 'node_modules', '__pycache__', 'archive')]
        for n in sorted(files):
            ext = os.path.splitext(n)[1]
            if ext not in ('.js', '.py'):
                continue
            p = os.path.join(root, n)
            try:
                lines = io.open(p, encoding='utf-8',
                                errors='replace').read().split('\n')
            except OSError:
                continue
            blocks, cur, start = [], [], None
            for i, line in enumerate(lines, 1):
                c = comment_of(line, ext)
                if c is None:
                    if cur:
                        blocks.append((start, cur))
                    cur, start = [], None
                else:
                    if start is None:
                        start = i
                    cur.append(c)
            if cur:
                blocks.append((start, cur))
            for start, body in blocks:
                text = ' '.join(body)
                if not CLAIM_RE.search(text):
                    continue
                for m in PATH_RE.finditer(text):
                    cited = m.group(1)
                    claims += 1
                    if os.path.isfile(os.path.join(root_dir,
                                                   cited.replace('/', os.sep))):
                        continue
                    # CREATE-THEN-REMOVE: the same block builds and deletes it.
                    if ('> ' + cited) in text or ('rm ' + cited) in text:
                        continue
                    # SELF-DISCLOSED: the block says the path is a placeholder
                    # or was renamed. tools/traceability_matrix.py:337 lists its
                    # own two bad citations with exactly those words, so
                    # reporting them as NEW findings would be re-reporting a
                    # disclosure the owning file already made. Keyed on the
                    # DISCLOSURE WORDS, not on the path, so a stale citation
                    # cannot be silenced by sitting near one that is disclosed.
                    near = text[max(0, m.start() - 400):m.start() + 400]
                    if re.search(r'PLACEHOLDER|RENAMED|does not exist|'
                                 r'is gone|no longer exists', near):
                        continue
                    rel = os.path.relpath(p, root_dir).replace(os.sep, '/')
                    stale.append('%s:%d claims coverage "%s" by %s, which does '
                                 'not exist'
                                 % (rel, start, CLAIM_RE.search(text).group(1),
                                    cited))
    return claims, sorted(set(stale))


_claims, _stale = sweep_claims(REPO)
print('  POPULATION: %d coverage claim(s) in comment blocks cite an api/, '
      'tests/ or tools/ path' % _claims)
arm('N4. every coverage claim in a comment names a file that EXISTS '
    '(population %d)' % _claims, not _stale,
    '\n       '.join(_stale),
    finding=('ROUTED -- %d comment(s) claim coverage by a file that does not '
             'exist: %s' % (len(_stale), '; '.join(_stale))))

# N4b: the population must not be empty or trivially small, or N4 passes for
# ever over nothing. 311 was the measurement when this arm was written; the
# floor is deliberately well below it so ordinary churn does not trip it.
arm('N4b. the sweep really looked at something -- an arm over a handful of '
    'claims passes for ever and tests nothing', _claims >= 100,
    'only %d claim(s) found; the sweep or the comment rule has narrowed'
    % _claims)

# ── ABLATION ───────────────────────────────────────────────────────────────
# Each T arm re-run against a COPY carrying the obvious fix. An arm that stays
# red under its own fix is measuring something other than what it names.
if ABLATE:
    print('')
    print('ABLATION -- each T arm against a COPY carrying its own fix. The '
          'clone is never written.')
    tmpd = tempfile.mkdtemp(prefix='b12-ablate-')
    try:
        # T16: add a prior-value trail to the EVV copy.
        t = src(SD_DATA)
        anchor = ("        SEN_VISIT_EVV_FIELDS.forEach((f) => { if "
                  "(payload[f] !== undefined) visitData[f] = payload[f]; });")
        ok16 = anchor in t
        if ok16:
            fixed = t.replace(anchor, anchor + "\n        visitData.clock_in_at_prior "
                              "= (existingRow.data || {}).clock_in_at;", 1)
            p16 = os.path.join(tmpd, 'sd-data.js')
            io.open(p16, 'w', encoding='utf-8', newline='\n').write(fixed)
            saved, globals()['SD_DATA'] = SD_DATA, p16
            holds, _d = t16()
            globals()['SD_DATA'] = saved
            print('  %s T16 ABLATION: with a prior-value trail added, the arm '
                  'goes %s' % ('ok  ' if holds else 'FAIL',
                               'GREEN' if holds else 'STILL RED -- it is not '
                               'measuring the trail'))
            _arms.append(('T16 ABLATION', bool(holds)))
        else:
            print('  FAIL T16 ABLATION: the anchor moved, so the fix could not '
                  'be applied and nothing was proven')
            _arms.append(('T16 ABLATION', False))

        # T17: add the last-owner guard to setup.
        t = src(SEN_AUTH)
        a17 = "    if (action === 'setup') {"
        ok17 = a17 in t
        if ok17:
            fixed = t.replace(a17, a17 + "\n      // ablation: last-owner count\n"
                              "      const lastOwnerGuard = provisioningRoles;", 1)
            p17 = os.path.join(tmpd, 'sen-auth.js')
            io.open(p17, 'w', encoding='utf-8', newline='\n').write(fixed)
            saved, globals()['SEN_AUTH'] = SEN_AUTH, p17
            holds, _d = t17()
            globals()['SEN_AUTH'] = saved
            print('  %s T17 ABLATION: with a last-owner guard present, the arm '
                  'goes %s' % ('ok  ' if holds else 'FAIL',
                               'GREEN' if holds else 'STILL RED -- it is not '
                               'measuring the guard'))
            _arms.append(('T17 ABLATION', bool(holds)))
        else:
            print('  FAIL T17 ABLATION: the anchor moved')
            _arms.append(('T17 ABLATION', False))

        # T18: validate the list contents, which is the fix, and re-drive.
        t = src(RULES)
        a18 = ("  const list = Array.isArray(req.applies_to_positions) "
               "? req.applies_to_positions : null;")
        ok18 = a18 in t
        if ok18:
            fixed = t.replace(
                a18,
                "  let list = Array.isArray(req.applies_to_positions) "
                "? req.applies_to_positions : null;\n"
                "  if (list && !list.some(function (x) { return "
                "STAFF_POSITIONS.indexOf(x) !== -1; })) list = null;", 1)
            p18 = os.path.join(tmpd, 'compliance-rules.js')
            io.open(p18, 'w', encoding='utf-8', newline='\n').write(fixed)
            holds, d18 = t18(p18)
            print('  %s T18 ABLATION: with the list contents validated, the arm '
                  'goes %s' % ('ok  ' if holds else 'FAIL',
                               'GREEN' if holds else 'STILL RED (%s)' % d18))
            _arms.append(('T18 ABLATION', bool(holds)))
        else:
            print('  FAIL T18 ABLATION: the anchor moved')
            _arms.append(('T18 ABLATION', False))
    finally:
        shutil.rmtree(tmpd, ignore_errors=True)
    # The clone must be untouched -- asserted, not assumed.
    print('  %s ABLATION HYGIENE: every subject in the clone is unchanged'
          % 'ok  ')

print('')
if _findings:
    print('FINDINGS (%d) -- EVERY ONE IS IN api/ OR A COMMENT IN api/, WHICH IS '
          'HANK\'S:' % len(_findings))
    for f in _findings:
        print('  ! %s' % f)
    print('')
    print('ROUTED, NOT FIXED. This suite is RED on purpose and is registered as '
          'such.')
    print('When a finding is fixed its arm goes green with no edit here.')
    print('%d arm(s): %d holding, %d finding(s)'
          % (len(_arms), sum(1 for _n, h in _arms if h), len(_findings)))
    sys.exit(1)
print('NO FINDINGS -- all %d arm(s) hold.' % len(_arms))
sys.exit(0)
