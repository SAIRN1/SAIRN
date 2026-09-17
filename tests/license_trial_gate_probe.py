"""Mutation probe for api/license-trial-gate.test.js.

Written at the same time as the suite, not months later, because that suite's
two most important arms are AS-IS tripwires -- they assert the gate is
UNREACHABLE today -- and an as-is assertion that has never been watched go red
is indistinguishable from one that cannot.

Nine mutations across four files, restored and sha256-verified.

Run:  python tests/license_trial_gate_probe.py
"""
import hashlib
import json
import os
import re
import subprocess
import sys

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True, encoding='utf-8', errors='replace').stdout.strip()
SUITE = os.path.join('api', 'license-trial-gate.test.js')

LIB = os.path.join('api', '_lib', 'license.js')
DATA = os.path.join('api', 'sd-data.js')
RENDER = os.path.join('api', 'sd-render.js')
STORE = os.path.join('api', '_lib', 'sd-store.js')
SNAP = os.path.join('db', 'schema_snapshot.json')

# ── THE SNAPSHOT IS MUTATED AS JSON, NOT AS TEXT (2026-09-14) ───────────
# THIRD TIME THESE TWO ANCHORS DIED, and the file already documents the
# first two. 2026-09-11 re-captured db/schema_snapshot.json pretty-printed
# and killed the one-line anchors; the anchors were rewritten for the
# pretty-printed shape; and it has now been re-captured COMPACT --
# `"license_keys": [ "id", ...` on one line -- so both died again.
#
# Chasing the formatting a fourth time would be the same bet. A JSON
# transform cannot rot on whitespace because it has no text anchor at all:
# it says WHAT to change rather than what the bytes around it look like.
# The probe restores the original bytes in its `finally`, so the
# re-serialisation never reaches a commit.
#
# Each one RAISES if the thing it meant to change is not there, because a
# transform that silently no-ops is exactly the failure the text anchors
# kept having -- just harder to notice.
def _snap_add_trial_column(doc):
    cols = doc['license_keys']
    if 'trial_ends_at' in cols:
        raise AssertionError('trial_ends_at is ALREADY in the snapshot -- this '
                             'arm can no longer prove the gate notices it '
                             'appearing, and the absence assertion it guards '
                             'may now be wrong')
    return dict(doc, license_keys=['trial_ends_at'] + cols)


def _snap_rename_sentinel(doc):
    cols = doc['license_keys']
    # stripe_subscription_id is what the SUITE reads. Renaming app_id left
    # the guard satisfied and this arm came back SILENT once already.
    if 'stripe_subscription_id' not in cols:
        raise AssertionError('stripe_subscription_id is no longer a license_keys '
                             'column, so this arm is renaming something the '
                             'suite does not read')
    return dict(doc, license_keys=['zz_subscription_id' if c == 'stripe_subscription_id'
                                   else c for c in cols])


MUTATIONS = [
    # THE TRIPWIRE, which is the whole reason this suite exists. If it does not
    # bite, the "column is absent" assertion proves nothing and the day somebody
    # adds the column nothing says so. The anchor was WRONG on the first run --
    # and it was only noticed because a dead anchor is reported, not skipped.
    #
    # ── AND IT WENT WRONG A SECOND TIME, THE OTHER WAY (2026-09-12) ──────────
    # The comment here used to read "the snapshot keeps each table's columns on
    # ONE line, not pretty-printed". That stopped being true on 2026-09-11 when
    # db/schema_snapshot.json was re-captured (3d603dd0) in a PRETTY-PRINTED
    # form: one column per line, eight-space indent. Both SNAP anchors below
    # died in the same commit and arms 1 and 2 stopped mutating anything.
    #
    # WHAT SAVED IT IS THE DESIGN, NOT LUCK. main() reports ANCHOR-0 and fails
    # rather than skipping, so a re-capture that silently disarmed the only
    # tripwire on a live security gate announced itself on the next full run.
    # Recorded because the lesson generalises past this file: RE-CAPTURING A
    # DATA FILE CAN CHANGE ITS FORMATTING, and every text anchor into that file
    # is a consumer nobody thinks of as one. This probe was the only text
    # anchor into the snapshot in the repo -- checked on 2026-09-12; every
    # other consumer parses it as JSON and was unaffected.
    ("1. the column APPEARS in the live schema snapshot",
     SNAP, _snap_add_trial_column, None),
    # The sentinel the SUITE checks is stripe_subscription_id, not app_id --
    # renaming app_id left the guard satisfied and this arm came back SILENT.
    # A control has to break the thing the assertion reads.
    #
    # The trailing ",\n  ...\"plan\"" is load-bearing and not decoration:
    # "stripe_subscription_id" alone appears 3 times in the snapshot, so a bare
    # anchor would be ambiguous and main() requires a count of exactly 1.
    ("2. the snapshot stops looking like license_keys at all",
     SNAP, _snap_rename_sentinel, None),
    ("3. the licence normaliser stops defaulting the field to null",
     LIB, "  out.trial_ends_at = row.trial_ends_at || null;",
     "  out.trial_ends_at = row.trial_ends_at;"),
    # Renaming the key to zz_trial_ends_at was SILENT for an obvious reason
    # once seen: the assertion matches /trial_ends_at:\s*null,/ and the renamed
    # key still CONTAINS that substring. The value is what has to change.
    ("4. the null DEFAULT is removed from the invalid-licence shape",
     LIB, "    trial_ends_at: null,", "    trial_ends_at: undefined,"),
    # One per handler: the correction has to survive in all three, because a
    # reader lands in whichever file they happen to be in.
    ("5. sd-data.js loses the correction and reads as enforcement again",
     DATA, "  // `trial_ends_at` IS NOT A COLUMN on license_keys -- measured twice by two",
     "  // trial_ends_at is checked here."),
    ("6. sd-render.js loses the correction",
     RENDER, "  // `trial_ends_at` IS NOT A COLUMN on license_keys -- measured twice by two",
     "  // trial_ends_at is checked here."),
    ("7. sd-store.js loses the correction",
     STORE, "  // `trial_ends_at` IS NOT A COLUMN on license_keys -- measured twice by two",
     "  // trial_ends_at is checked here."),
    # The filename appears on a different line than the one first targeted,
    # so removing that line left the assertion satisfied. Target the mention.
    ("8. sd-data.js stops pointing at the suite that pins this",
     DATA, "  // plan to expire. api/license-trial-gate.test.js pins this AS-IS -- the day",
     "  // plan to expire. Nothing pins this -- the day"),
    # ── A RENAME KILLED THIS ONE, AND IT IS THE ARM THAT MATTERS MOST ───────
    # The anchor was the literal line `if (!isPaid && lic.trial_ends_at && ...`.
    # `isPaid` was split into knownPaid/knownNotPaid/cannot-tell (the three-state
    # fix at sd-render.js:164-177), the line no longer existed byte-for-byte, and
    # this arm reported ANCHOR-0 from then on -- so the one mutation that asks
    # "does deleting the whole licensing gate get noticed" was never actually
    # run. It reported, rather than skipping, which is the only reason it was
    # found; a probe that treats a dead anchor as a pass would have been
    # reporting nine-of-nine green over a gate nothing was testing.
    #
    # A REGEX, NOT THE LINE, for the same reason arms 1 and 2 became JSON
    # transforms: say what to change, not what the bytes around it look like.
    # This one survives the indentation, the trailing comparison and the CRLF
    # question, and main() still requires exactly one match -- a second copy
    # appearing in this file is itself something to look at.
    ("9. the gate itself is deleted from sd-render.js",
     RENDER, re.compile(r'if \(knownNotPaid && lic\.trial_ends_at &&[^\n]*\{'),
     "if (false) {"),
]


def main():
    targets = sorted({t for _, t, _, _ in MUTATIONS})
    orig = {t: open(os.path.join(ROOT, t), 'rb').read() for t in targets}
    before = {t: hashlib.sha256(v).hexdigest() for t, v in orig.items()}

    base = subprocess.run(['node', SUITE], cwd=ROOT, capture_output=True)
    results = [('0. the suite is green on the unmodified files',
                'GREEN' if base.returncode == 0 else 'RED-BEFORE-MUTATION')]
    try:
        for name, target, old, new in MUTATIONS:
            src = orig[target]
            # A CALLABLE MUTATES THE PARSED DOCUMENT. See the transforms
            # above for why the snapshot arms stopped using text anchors.
            if callable(old):
                try:
                    mutated = json.dumps(old(json.loads(src.decode('utf-8'))),
                                         indent=1).encode('utf-8')
                except AssertionError as e:
                    results.append((name, 'STALE'))
                    print('    %s: %s' % (name, e))
                    continue
                if mutated == src:
                    results.append((name, 'NO-OP'))
                    continue
                open(os.path.join(ROOT, target), 'wb').write(mutated)
                r = subprocess.run(['node', SUITE], cwd=ROOT, capture_output=True)
                results.append((name, 'BITES' if r.returncode != 0 else 'SILENT'))
                open(os.path.join(ROOT, target), 'wb').write(src)
                continue
            # A COMPILED PATTERN is the third anchor kind. Same contract as the
            # literals below -- exactly one match or the arm reports ANCHOR-n
            # and fails; it is only the matching that is looser.
            if isinstance(old, re.Pattern):
                text = src.decode('utf-8')
                n = len(old.findall(text))
                if n != 1:
                    results.append((name, 'ANCHOR-%d' % n))
                    continue
                open(os.path.join(ROOT, target), 'wb').write(
                    old.sub(new.replace('\\', '\\\\'), text, count=1).encode('utf-8'))
                r = subprocess.run(['node', SUITE], cwd=ROOT, capture_output=True)
                results.append((name, 'BITES' if r.returncode != 0 else 'SILENT'))
                open(os.path.join(ROOT, target), 'wb').write(src)
                continue
            # CRLF-aware: three of these four files are stored CRLF in the
            # working tree, and a \n-only anchor silently matches nothing.
            hit = None
            for nl in ('\n', '\r\n'):
                ob = old.replace('\r\n', '\n').replace('\n', nl).encode('utf-8')
                if src.count(ob) == 1:
                    hit = (ob, new.replace('\r\n', '\n').replace('\n', nl).encode('utf-8'))
                    break
            if not hit:
                results.append((name, 'ANCHOR-%d' % src.count(
                    old.replace('\r\n', '\n').encode('utf-8'))))
                continue
            open(os.path.join(ROOT, target), 'wb').write(src.replace(hit[0], hit[1], 1))
            r = subprocess.run(['node', SUITE], cwd=ROOT, capture_output=True)
            results.append((name, 'BITES' if r.returncode != 0 else 'SILENT'))
            open(os.path.join(ROOT, target), 'wb').write(src)
    finally:
        for t in targets:
            open(os.path.join(ROOT, t), 'wb').write(orig[t])

    for name, verdict in results:
        print('  %-8s %s' % (verdict, name))
    print()
    ok = True
    for t in targets:
        after = hashlib.sha256(open(os.path.join(ROOT, t), 'rb').read()).hexdigest()
        ok = ok and after == before[t]
        print('%-28s restored byte-identical: %s  %s' % (t, after == before[t], before[t][:16]))
    bad = [n for n, v in results if v not in ('BITES', 'GREEN')]
    print('PROBES THAT DID NOT BITE:', bad if bad else 'none')
    return 1 if (bad or not ok) else 0


if __name__ == '__main__':
    sys.exit(main())
