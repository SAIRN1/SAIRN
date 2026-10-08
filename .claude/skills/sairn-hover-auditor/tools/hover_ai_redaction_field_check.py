#!/usr/bin/env python
"""hover_ai_redaction_field_check.py -- does the register's Evidence text
account for every field api/_lib/ai-scan-redaction.js actually redacts
AI-generated text in.

H1 batch S item 9. Batch R item 1 found that many Tier A resources are
dispatched through a GENERIC, resource-agnostic read/write block in
api/sd-data.js with no per-resource field branching at all -- and that
the real per-resource field logic for those resources is delegated to
separate helper functions keyed by resource name, named but not built as
a future candidate. AI_SCANNED_TEXT[resource] in
api/_lib/ai-scan-redaction.js is exactly that: a parallel per-resource
field registry this role's existing hover_hidden_state.py (which only
reads api/sd-data.js) has never once looked at.

METHOD, same shape as hover_hidden_state.py, applied to a different
source:
  1. AI_SCANNED_TEXT[resource]: ['field', ...] parsed directly from
     api/_lib/ai-scan-redaction.js's own object literal.
  2. Every resource's Evidence-column text, read from
     docs/CRITICALITY-TIERS.md -- ALL TIERS, not only A, because a
     disclosure-redaction question is a confidentiality concern that does
     not require the resource to also be money/regulated-A.
  3. A resource present in (1) but with NO ROW AT ALL in the register is
     its own, separate finding (the same denominator-gap shape as
     hover_completeness_probe.py's `shared`-app finding) -- it is not
     folded into the field-naming question below, because "we never
     tiered this resource" and "we tiered it but didn't name the field"
     are different gaps.
  4. For a resource WITH a row, each AI_SCANNED_TEXT field not named
     (case/underscore/camelCase-insensitive) anywhere in its Evidence
     text is a candidate.

NOT A SECURITY VERDICT. redactAiFields() already DOES redact these
fields -- the question is whether the register's own stated reasoning
accounts for the fact that the field exists and carries model-generated
text, same framing as hover_hidden_state.py's own docstring.

Read-only.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def discover_repo():
    for cand in (os.environ.get('HOVER_PROBE_REPO'),
                 r'C:\Users\marsh\Documents\SAIRN-hover'):
        if cand and os.path.isdir(os.path.join(cand, '.git')):
            return cand
    return None


def parse_ai_scanned_text(repo):
    path = os.path.join(repo, 'api', '_lib', 'ai-scan-redaction.js')
    if not os.path.isfile(path):
        return {}, 'api/_lib/ai-scan-redaction.js not found'
    with open(path, encoding='utf-8') as f:
        src = f.read()
    m = re.search(r"const AI_SCANNED_TEXT\s*=\s*\{(.*?)\n\};", src, re.S)
    if not m:
        return {}, 'AI_SCANNED_TEXT object literal not found'
    code_only = '\n'.join(re.sub(r'//.*$', '', line) for line in m.group(1).splitlines())
    out = {}
    for entry_m in re.finditer(r"([a-z][a-z0-9_]+)\s*:\s*\[([^\]]*)\]", code_only):
        name, fields_raw = entry_m.groups()
        fields = re.findall(r"'([a-zA-Z_][a-zA-Z0-9_]*)'", fields_raw)
        out[name] = fields
    return out, None


# Same row shape hover_hidden_state.py and hover_ai_redaction_field_check.py
# both key off -- but ANY tier (A/B/C), not only A.
ROW_RE = re.compile(
    r"^\|\s*`([a-z][a-z0-9_]+)`\s*\|\s*\*?\*?(A|B|C)\*?\*?\s*\|"
    r"\s*\*?\*?(A|B)\*?\*?\s*\|([^|]*)\|([^|]*)\|(.*)\|\s*$", re.M)


def all_resource_rows(repo):
    path = os.path.join(repo, 'docs', 'CRITICALITY-TIERS.md')
    if not os.path.isfile(path):
        return {}, 'docs/CRITICALITY-TIERS.md not found'
    with open(path, encoding='utf-8') as f:
        src = f.read()
    out = {}
    for m in ROW_RE.finditer(src):
        name, tier, conf, lost, read_by_wrong, evidence = m.groups()
        # FOUND HAND-VERIFYING THIS TOOL'S OWN FIRST REAL RUN: mech_docs'
        # entire detailed AI-redaction discussion lives in the "read by
        # the wrong person" column, not Evidence -- the register's
        # authors do not consistently put the load-bearing prose in the
        # same column every row. Checking Evidence alone (the convention
        # hover_hidden_state.py also uses) produced a false flag here.
        # Union all three free-text columns rather than Evidence alone.
        combined = ' '.join(x.strip() for x in (lost, read_by_wrong, evidence))
        out[name] = {'tier': tier, 'evidence': combined}
    return out, None


def _words(name):
    parts = re.findall(r'[A-Z]?[a-z0-9]+', name)
    return set(p.lower() for p in parts if len(p) > 1)


def run(repo):
    ai_fields, err1 = parse_ai_scanned_text(repo)
    if err1:
        return {'error': err1}
    rows, err2 = all_resource_rows(repo)
    if err2:
        return {'error': err2}
    report = {'resources_checked': len(ai_fields), 'no_register_row': [],
              'unnamed_fields': {}}
    for name, fields in ai_fields.items():
        row = rows.get(name)
        if not row:
            report['no_register_row'].append(name)
            continue
        ev_words = _words(row['evidence'].replace('`', ''))
        unnamed = [f for f in fields if not (_words(f) & ev_words)]
        if unnamed:
            report['unnamed_fields'][name] = {'tier': row['tier'], 'fields': unnamed}
    return report


def main(argv):
    repo = discover_repo()
    if not repo:
        print('COULD NOT RUN: no known hover-visible clone found on disk.')
        return 2
    report = run(repo)
    if report.get('error'):
        print('COULD NOT RUN: %s' % report['error'])
        return 2
    print('AI_SCANNED_TEXT resources checked: %d' % report['resources_checked'])
    if report['no_register_row']:
        print('NO REGISTER ROW AT ALL (denominator gap, same shape as the shared-app finding):')
        for n in report['no_register_row']:
            print('  %s' % n)
    if report['unnamed_fields']:
        print('CANDIDATE unnamed AI-redacted fields:')
        for name, info in sorted(report['unnamed_fields'].items()):
            print('  %-24s tier=%s  %s' % (name, info['tier'], ', '.join(info['fields'])))
    if not report['no_register_row'] and not report['unnamed_fields']:
        print('No gaps found -- every AI_SCANNED_TEXT resource has a register row naming its redacted field(s).')
    if '--json' in argv:
        print(json.dumps(report, indent=1))
    return 1 if (report['no_register_row'] or report['unnamed_fields']) else 0


def _selftest():
    import tempfile
    failures = []

    def chk(label, cond):
        print(('ok  ' if cond else 'FAIL') + '  ' + label)
        if not cond:
            failures.append(label)

    with tempfile.TemporaryDirectory() as td:
        os.makedirs(os.path.join(td, '.git'))
        os.makedirs(os.path.join(td, 'api', '_lib'))
        os.makedirs(os.path.join(td, 'docs'))
        with open(os.path.join(td, 'api', '_lib', 'ai-scan-redaction.js'), 'w') as f:
            f.write(
                "const AI_SCANNED_TEXT = {\n"
                "  // example comment: fa_fake: ['ignored'] should not be read\n"
                "  fa_photos: ['ai_analysis', 'summary_text'],\n"
                "  fa_orphan: ['notes'],\n"
                "};\n"
                "module.exports = { AI_SCANNED_TEXT };\n")
        with open(os.path.join(td, 'docs', 'CRITICALITY-TIERS.md'), 'w') as f:
            f.write(
                "| `fa_photos` | B | B | lost | wrong-person | model prose over a jobsite photo, the ai_analysis field |\n")
        # Case 1: planted directly.
        report = run(td)
        chk('fa_orphan (no row at all) is a denominator gap',
            'fa_orphan' in report['no_register_row'])
        chk('fa_photos.ai_analysis IS named in evidence (not flagged)',
            'ai_analysis' not in report['unnamed_fields'].get('fa_photos', {}).get('fields', []))
        chk('fa_photos.summary_text is NOT named in evidence (flagged)',
            'summary_text' in report['unnamed_fields'].get('fa_photos', {}).get('fields', []))
        chk("comment-embedded 'fa_fake' is not parsed as a real resource",
            'fa_fake' not in report.get('no_register_row', []) and 'fa_fake' not in report.get('unnamed_fields', {}))

        # Case 2: the real transition -- the register is edited to add the
        # missing field name for fa_photos.summary_text, and the SAME
        # resource that was flagged now clears, nothing else changes.
        with open(os.path.join(td, 'docs', 'CRITICALITY-TIERS.md'), 'w') as f:
            f.write(
                "| `fa_photos` | B | B | lost | wrong-person | model prose over a jobsite photo, the ai_analysis and summary_text fields |\n")
        report2 = run(td)
        # Regression lock for the real bug this tool's own first live run
        # found: mech_docs' whole AI-redaction discussion lived in the
        # "read by wrong person" column, not Evidence -- a field named
        # ONLY in that column must not be flagged.
        with open(os.path.join(td, 'docs', 'CRITICALITY-TIERS.md'), 'a') as f:
            f.write(
                "| `fa_wrongcol` | B | B | lost | the raw_text field is discussed only here | n/a |\n")
        with open(os.path.join(td, 'api', '_lib', 'ai-scan-redaction.js'), 'w') as f:
            f.write(
                "const AI_SCANNED_TEXT = {\n"
                "  fa_photos: ['ai_analysis', 'summary_text'],\n"
                "  fa_orphan: ['notes'],\n"
                "  fa_wrongcol: ['raw_text'],\n"
                "};\nmodule.exports = { AI_SCANNED_TEXT };\n")
        report2b = run(td)
        chk("a field named only in the 'read by wrong person' column is NOT a false flag",
            'fa_wrongcol' not in report2b['unnamed_fields'])
        chk('after the register is edited to name summary_text, fa_photos clears (real transition)',
            'fa_photos' not in report2['unnamed_fields'])
        chk('fa_orphan is STILL a gap -- the transition only touched fa_photos',
            'fa_orphan' in report2['no_register_row'])

    print()
    print('SELFTEST %s (%d/%d)' % ('PASS' if not failures else 'FAIL', 7 - len(failures), 7))
    return 0 if not failures else 1


if __name__ == '__main__':
    argv = sys.argv[1:]
    if '--selftest' in argv:
        sys.exit(_selftest())
    sys.exit(main(argv))
