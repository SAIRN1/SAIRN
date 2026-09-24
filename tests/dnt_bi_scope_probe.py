"""api/dnt-bi.test.js must go RED when the BI feed's patient scope is undone.

Run: python tests/dnt_bi_scope_probe.py

WHY THIS SUITE AND WHY NOW. dnt-bi is a machine-readable PHI feed: a token, a
dataset name, and rows straight out of a dental practice. It is Tier A and it
had no negative control, and the ordering defect this control was written
alongside is one nothing in forty existing arms could see -- the rows a caller
RECEIVES are identical whether the scope is resolved before or after the read.
The difference is entirely in WHAT WAS FETCHED, and only a control that asserts
the order can tell.

ONE PROPERTY PER MUTATION, and the last two go the other way. A feed that
returned nothing to everybody would satisfy every refusal arm here, so the
permissive direction gets its own mutations: a broad-read role must NOT be
narrowed, and a provider with no appointments must get an empty list rather
than a refusal.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('api', 'dnt-bi.test.js')
SRC = os.path.join('api', 'dnt-bi.js')
LIB = os.path.join('api', '_lib', 'dental-bi.js')

MUTATIONS = [
    # THE DEFECT THIS CONTROL WAS WRITTEN WITH, RESTORED. The scope block moves
    # back below the dataset read, so the whole practice is fetched and only
    # then narrowed -- and SCOPE_LOOKUP_FAILED fires with every row already
    # over the wire. The rows the caller sees do not change, which is exactly
    # why no existing arm could see it.
    ("1. the patient scope is resolved AFTER the protected dataset is read "
     "again -- the refusal fires with the PHI already fetched",
     SRC, "  let patientIds = null;\n  if (scope.kind === 'patient_ids') {",
     "  let patientIds = null;\n  if (false && scope.kind === 'patient_ids') {"),
    ("2. a FAILED scope lookup falls through instead of refusing, so an "
     "unknown patient list is treated as an empty one",
     SRC,
     "      res.status(502).json({ error: { code: 'SCOPE_LOOKUP_FAILED', message: 'Could not determine your patient list. Try again.' } });\n"
     "      return;\n    }\n    patientIds = {};",
     "      patientIds = {};\n    }\n    patientIds = patientIds || {};\n    if (false) {"),
    ("3. the provider_column scope stops filtering in the DATABASE, so an "
     "appointment blob for every provider is read to discard most of it",
     SRC,
     "  if (scope.kind === 'provider_column') path += '&' + scope.column + '=eq.' + enc(providerId);",
     "  if (false) path += '&' + scope.column + '=eq.' + enc(providerId);"),
    ("4. an UNLINKED provider gets an empty feed instead of 403 "
     "PROVIDER_NOT_LINKED -- a fabricated zero on a BI dashboard",
     SRC, "      res.status(403).json({ error: { code: 'PROVIDER_NOT_LINKED',",
     "      res.status(200).json(envelope(datasetName, role, includeIds, [], 0, 0, 0, true));\n"
     "      return;\n    }\n    if (false) {\n      res.status(403).json({ error: { code: 'PROVIDER_NOT_LINKED',"),
    ("5. the patient scope is never APPLIED, so a resolved list is computed "
     "and then ignored",
     SRC,
     "  if (scope.kind === 'patient_ids') {\n    raw = bi.applyPatientScope(datasetName, raw, patientIds);\n  }",
     "  if (false) {\n    raw = bi.applyPatientScope(datasetName, raw, patientIds);\n  }"),
    # ── WHAT IS NOT HERE, AND WHY, BECAUSE AN ABSENCE NOBODY STATES READS AS
    # COVERAGE. An arm breaking applyPatientScope's fail-closed default
    # (`allowedPatientIds || {}`) was written first and came back SILENT --
    # correctly. dnt-bi.js now always passes a real object on that path, so the
    # default is unreachable from this suite, and the property is covered where
    # it belongs: api/_lib/dental-bi.test.js:136-137 asserts {} and null both
    # yield zero rows. A control arm for a property its suite cannot reach
    # measures nothing and would have been a false green.
    ("6. the dataset read drops its license_hash filter -- another practice's "
     "rows on this practice's feed",
     SRC, "  let path = def.resource + '?license_hash=eq.' + enc(trow.license_hash);",
     "  let path = def.resource + '?select=data&x=eq.' + enc(trow.license_hash);"),
    # ── THE OTHER DIRECTION ────────────────────────────────────────────────
    # Six mutations above break a narrowing, and a feed that returned nothing
    # to everybody would pass all of them.
    ("7. a broad-read role is narrowed like a provider, so an owner's own "
     "dashboard silently loses rows",
     LIB, "  if (PATIENT_BROAD_READ_ROLES[role]) return { kind: 'none' };",
     "  if (false) return { kind: 'none' };"),
]

if __name__ == '__main__':
    # api/_lib/auth.js is staged 2026-09-24 because the file(s) above now
    # call roleSet() from it -- the platform-wide null-prototype role-map
    # sweep. The worktree is at HEAD, so an UNSTAGED DEPENDENCY of a staged
    # file dies at require() and the BASELINE goes red before any mutation
    # is planted. Same gap as an unstaged file. Full account: api/_lib/auth.js.
    sys.exit(run_probe(SUITE, MUTATIONS, stage=(SRC, os.path.join('api', '_lib', 'auth.js')),
                       title='negative control -- api/dnt-bi.test.js must refuse each way '
                             'the BI feed PHI scope can be undone'))
