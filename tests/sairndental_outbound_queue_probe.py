"""Mutation probe for tests/sairndental_outbound_queue.js.

A suite that has only ever been green is a suite whose behaviour nobody knows.
This breaks the queue in fifteen specific ways -- one per defect the suite
claims to hold -- and asserts it goes RED for every one, then restores every
touched file and verifies each byte-identical by sha256.

TWO MUTATIONS ARE IN A DIFFERENT FILE ON PURPOSE, and running them is what
found the arm they were meant to prove was checking the WRONG LINE. The queue
is only safe to retry because api/sd-data.js UPSERTS dnt_* writes on
(license_hash, id). The suite asserts that contract; its first version located
it with an indexOf() on the on_conflict call, which appears SIX times in that
file -- once per app sharing the generic write -- so it was asserting some
other app's line and stayed green while the dental one was broken. A contract
asserted but never violated is a contract nobody has tested.

Files are read and written as BYTES. api/sd-data.js is ~690 KB and does not
decode cleanly under this machine's locale codec; a text round-trip would
rewrite it and the sha256 check would fail for a reason that has nothing to do
with the mutation.

Run:  python tests/sairndental_outbound_queue_probe.py
"""
import hashlib
import os
import subprocess
import sys

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()
SUITE = os.path.join('tests', 'sairndental_outbound_queue.js')

APP = 'sairndental.html'
API = os.path.join('api', 'sd-data.js')

# (name, file, exact bytes to replace, replacement). An anchor that stops
# matching is reported as ANCHOR-n and FAILS the run, rather than silently
# probing nothing -- which is how a mutation suite rots without anyone noticing.
MUTATIONS = [
    # THE GUARD IS BROKEN WHOLE, and the first attempt at these two is worth
    # recording. Dropping `!refused` alone changes NOTHING observable -- a
    # refused row is never stored, so `kept` is already false -- so a probe
    # written that way came back SILENT and looked like a missing assertion
    # when it was really an unfalsifiable term. Dropping both terms is the
    # mutation that produces the real defect, and it makes two arms bite at
    # once: the refused row gets queued AND so does one this device could not
    # store.
    ("1. the CHARGE queue guard stops checking refused and kept", APP,
     "  var queued=(!syncResult&&!refused&&kept)?dntPendingAdd('dnt_charges',rec):false;",
     "  var queued=(!syncResult)?dntPendingAdd('dnt_charges',rec):false;"),
    ("2. the PAYMENT queue guard stops checking refused and kept", APP,
     "  var queued=(!syncResult&&!refused&&kept)?dntPendingAdd('dnt_payments',rec):false;",
     "  var queued=(!syncResult)?dntPendingAdd('dnt_payments',rec):false;"),
    ("3. dntPendingAdd appends instead of replacing by id", APP,
     "  if(i>=0)q[i]=entry;else q.push(entry);",
     "  q.push(entry);"),
    ("4. the flush generates a NEW id for every retry", APP,
     "      var ok=await sdnData('write',p.resource,p.rec);",
     "      p.rec.id=newId('CH');var ok=await sdnData('write',p.resource,p.rec);"),
    ("5. the flush deletes the local ledger row on a refusal", APP,
     "        p.status='refused';",
     "        st('dnt_charges_list',[]);p.status='refused';"),
    ("6. a refusal is left pending and retries forever", APP,
     "      if(dntWriteRefused(p.resource)){",
     "      if(false){"),
    ("7. the reentrancy guard is removed", APP,
     "  if(_dntFlushing||!pending.length)return {sent:0,refused:0,left:pending.length,ran:false};",
     "  if(!pending.length)return {sent:0,refused:0,left:pending.length,ran:false};"),
    ("8. an offline flush drops the rest of the queue instead of keeping it", APP,
     "      keep=keep.concat(pending.slice(i));",
     "      keep=keep.concat([]);"),
    ("9. an empty queue still hits the network", APP,
     "  if(_dntFlushing||!pending.length)return {sent:0,refused:0,left:pending.length,ran:false};",
     "  if(_dntFlushing)return {sent:0,refused:0,left:pending.length,ran:false};"),
    ("10. boot stops draining the queue", APP,
     "  dntFlushAndReport(true);\n  window.addEventListener('online',function(){dntFlushAndReport();});",
     "  window.addEventListener('online',function(){dntFlushAndReport();});"),
    ("11. the Refresh button reads before it uploads", APP,
     "    await dntFlushAndReport();\n    var result=await dntSyncFromServer();",
     "    var result=await dntSyncFromServer();\n    await dntFlushAndReport();"),
    ("12. the banner stops telling the person not to re-enter", APP,
     "      'Do not re-enter them -- a second entry would be counted twice.'+",
     "      'They are on this device.'+"),
    ("13. a quiet flush swallows a REFUSAL as well as an upload", APP,
     "  if(r.refused){",
     "  if(r.refused&&!quiet){"),
    # ── the cross-file one ────────────────────────────────────────────────
    # Anchored on the line ABOVE as well: the on_conflict call appears six
    # times in that file, once per app that shares the generic write, and an
    # anchor matching all six would mutate whichever came first.
    ("14. the server stops upserting and starts inserting", API,
     "      const locStamped = dntLocation.stampLocation(payload);\n"
     "      const r = await fetch(rest(resource + '?on_conflict=license_hash,' + idCol), {",
     "      const locStamped = dntLocation.stampLocation(payload);\n"
     "      const r = await fetch(rest(resource), {"),
    # ── ANCHOR WIDENED 2026-09-10, and the widening is the finding ──────────
    # This anchor stopped one token short of the thing that tells the two
    # SAIRNdental write branches apart, so when the VENDOR branch was added
    # with the identical Prefer header the anchor matched BOTH and the probe
    # reported ANCHOR-2 rather than mutating whichever came first. That refusal
    # is the probe working -- arm 14's comment already records why it must not
    # guess -- but it meant this arm proved nothing from the day the vendor
    # branch landed until it was read.
    #
    # `[idCol]` is what distinguishes them: the generic DNT_RESOURCES branch
    # uses idCol, the DNT_VENDOR_OBJECTS branch uses vIdCol. Anchoring on it
    # cannot match the vendor branch even if every other line is identical.
    ("15. the server keeps on_conflict but stops merging duplicates", API,
     "        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),\n"
     "        body: JSON.stringify({ license_hash: licHash, app_id: 'sairndental', [idCol]: String(payload.id),",
     "        headers: Object.assign({}, headers, { Prefer: 'return=representation' }),\n"
     "        body: JSON.stringify({ license_hash: licHash, app_id: 'sairndental', [idCol]: String(payload.id),"),
]


def main():
    targets = sorted({m[1] for m in MUTATIONS})
    orig = {}
    before = {}
    for t in targets:
        p = os.path.join(ROOT, t)
        orig[t] = open(p, 'rb').read()
        before[t] = hashlib.sha256(orig[t]).hexdigest()

    baseline = subprocess.run(['node', SUITE], cwd=ROOT, capture_output=True)
    results = [("0. the suite is green on the unmodified files",
                'GREEN' if baseline.returncode == 0 else 'RED-BEFORE-MUTATION')]

    try:
        for name, target, old, new in MUTATIONS:
            src = orig[target]
            n = src.count(old.encode('utf-8'))
            if n != 1:
                results.append((name, 'ANCHOR-%d' % n))
                continue
            open(os.path.join(ROOT, target), 'wb').write(
                src.replace(old.encode('utf-8'), new.encode('utf-8'), 1))
            r = subprocess.run(['node', SUITE], cwd=ROOT, capture_output=True)
            results.append((name, 'BITES' if r.returncode != 0 else 'SILENT'))
            open(os.path.join(ROOT, target), 'wb').write(src)
    finally:
        # Restored even if the run dies mid-way. A probe that leaves a mutated
        # app or a mutated API on disk is worse than no probe.
        for t in targets:
            open(os.path.join(ROOT, t), 'wb').write(orig[t])

    for name, verdict in results:
        print('  %-8s %s' % (verdict, name))
    print()
    ok = True
    for t in targets:
        after = hashlib.sha256(open(os.path.join(ROOT, t), 'rb').read()).hexdigest()
        same = after == before[t]
        ok = ok and same
        print('%-24s restored byte-identical: %s  %s' % (t, same, before[t][:16]))
    # ── TWO DIFFERENT PROBLEMS, REPORTED AS TWO (2026-09-10) ────────────────
    # Both fail the run, and both should. But they send the reader to opposite
    # places, and lumping them under one heading cost real time once already:
    #
    #   SILENT   the mutation landed and the suite stayed green. THE CODE IS
    #            UNPROTECTED -- go and write the assertion.
    #   ANCHOR-n the mutation never landed, because the anchor matched n places
    #            instead of one. THE PROBE IS STALE -- the code may be perfectly
    #            well covered, and nothing here has been measured either way.
    #            Widen the anchor until it is unique; do NOT let it guess.
    #
    # Arm 15 spent an unknown stretch reported as "DID NOT BITE" while the
    # actual state was ANCHOR-2 -- a stale anchor reading like a coverage hole.
    silent = [n for n, v in results if v == 'SILENT']
    stale = [(n, v) for n, v in results if v.startswith('ANCHOR-')]
    other = [n for n, v in results if v not in ('BITES', 'GREEN', 'SILENT')
             and not v.startswith('ANCHOR-')]
    print('MUTATIONS THAT WENT UNNOTICED (the code is unprotected):',
          silent if silent else 'none')
    print('ANCHORS THAT NO LONGER MATCH EXACTLY ONCE (the probe is stale, '
          'nothing was measured):',
          ['%s -> %s' % (n, v) for n, v in stale] if stale else 'none')
    if other:
        print('OTHER:', other)
    return 1 if (silent or stale or other or not ok) else 0


if __name__ == '__main__':
    sys.exit(main())
