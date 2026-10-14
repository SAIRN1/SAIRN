# ROWS 44 AND 50 — DRIVEN, and both were on my list for the wrong reason — 2026-10-14, fourth b16

**ROUTED TO cody (`tests/`) and hank (`api/`, `sql/`).** This batch writes
under `docs/` only, so the arms below are delivered as code to place rather
than placed. **`tests/` has one writer and it is not me.**

**WHAT I WAS SENT TO DO:** write the row 44 and row 50 probes from
`docs/2026-10-14-fourth-b15-fixture-priority-26-50.md`, the two the owner map
attributes to fourth.

**WHAT DRIVING THEM FOUND, BEFORE ANY CODE WAS WRITTEN: both probes already
exist, both already carry the sabotage-and-control pair my b15 list said they
needed, and one of them is CURRENTLY FAILING IN A WAY NOBODY HAS REPORTED.**

---

## 1. THE CORRECTION TO MY OWN LIST — rows 44 and 50 were false positives

```
CMD python tests/run_removal_path_probe.py              ->  EXIT 1
    38 arms; 37 ok, 1 FAILED
CMD python tests/sairncash_entitlement_gate_probe.py    ->  EXIT 1
    arm 0 ok: the suite is GREEN in the worktree before anything is planted
    8 mutation arms; 6 ok, 2 FAILED
    ok  the worktree copy of sairncash.html is byte-identical again
    ok  and the suite is GREEN again with everything restored (exit 0)
    ok  this run left NOTHING newly dirty in this clone
```

**Both are control probes of exactly the shape b15 asked for.** The b15 scorer
classified them NO-FIXTURE because its `FIXTURE_ARM` pattern looks for
`--fixtures`, `--self-test`, `def fixtures(`, `CRITERIA_VERSION` or the phrase
*criteria lock* — and neither file uses those words. **Row 44 builds throwaway
fixture repos in a temp directory and asserts 37 classification outcomes; row
50 plants 8 mutations into a staged copy and asserts the suite goes red for
each, with a baseline arm, a byte-identical-restore arm and a
left-nothing-dirty arm.**

**THIS IS THE SAME MISTAKE AS `digest_lint.py` IN b14**, which my pattern also
called HAPPY-PATH because it asserts refusals as fixture tuples rather than in
prose. **Third instance of one defect: a word-matching classifier credits a
vocabulary, not a behaviour.** The correction is recorded here and the two rows
should be struck from the b15 list; the scorer's bias is already documented as
erring toward crediting, so the list is a floor — **but a floor that still
contains two files which were already locked is a floor nobody trusts.**

**WHAT ROWS 44 AND 50 ACTUALLY NEED is in §2 and §3, and neither is "a
fixture".**

---

## 2. ROW 44 — `tests/run_removal_path_probe.py`: the fixture arms are green and the LIVE arm is red

```
CMD python tests/run_removal_path_probe.py
    ok    12 and exactly the two non-derived resources remain stuck
    FAIL  the real SAIRN baseline currently accounts for every one
            expected 0
            actual   1
    1 FAILED
```

`tests/run_removal_path_probe.py:425-427` runs the **real tool against the real
repo** as its last arm, and asserts the tool exits 0. It does not.

```
CMD python tools/removal_path_check.py                  ->  EXIT 1
    keyed, no removal path, NOT in the baseline : 4
      - alf_family_contacts      (sairncare)        upserts on (license_hash, id)
      - mech_insurance_policies  (sairnmechanical)  upserts on (license_hash, id)
      - sf_trustee_audits        (sairnfreedom)     id column trustee_audit_id
      - sv_scribe_consent        (sairnvet)         id column scribe_consent_id
    NO REMOVAL PATH (excl. single-row, append-only, derived) : 325
      grandfathered in the baseline                          : 321
    by criticality tier : A=221, B=98, UNTIERED=6
```

### 2.1 THE FINDING, ROUTED TO hank — four resources a record cannot be removed from

The tool's own words: *"A record written to one of these cannot be removed
through the product — only by hand in the SQL editor."* **All four are new
since the baseline was cut**, which is what the baseline is for: 321
grandfathered, 4 arrivals.

| resource | app | why it matters more than a count |
|---|---|---|
| `alf_family_contacts` | sairncare | a **named family member's contact details** in an assisted-living record. A contact who asks to be removed cannot be. |
| `sv_scribe_consent` | sairnvet | **a consent record.** A consent that cannot be withdrawn through the product is the sharpest of the four, and it is one of the 42 resources my b15 sairnvet role matrix specifies `owner`/`dvm`-write. |
| `sf_trustee_audits` | sairnfreedom | a trustee audit row, tier A. |
| `mech_insurance_policies` | sairnmechanical | an insurance policy record. |

**Exact next step for hank:** either a removal path per resource, or four
baseline rows **each with a reason** — the tool already distinguishes
grandfathered from new, so adding them silently is the one answer that loses
the information.

### 2.2 WHAT ROW 44 ITSELF NEEDS — a separated exit, not a fixture

**The probe mixes 37 synthetic arms with one live-repo arm in a single exit
code.** Today `EXIT 1` means *either* the classifier regressed *or* somebody
added a resource without a removal path — **two very different things, and the
second is somebody else's work.**

**The arm to add, delivered as code because `tests/` is cody's:**

```python
# tests/run_removal_path_probe.py -- replace the single live arm at :425-427
LIVE = '--live' in sys.argv          # default OFF
# ... the 37 synthetic arms run unconditionally ...
if LIVE:
    r = subprocess.run([sys.executable, TOOL], cwd=REPO, capture_output=True,
                       text=True)
    check('--live: the real SAIRN baseline accounts for every stuck resource',
          r.returncode, 0)
else:
    print('  SKIPPED (pass --live): the real-repo arm. It reports somebody '
          "ELSE's missing removal path, not this probe's health, and folding "
          'the two into one exit code means a red probe stops being read.')
```

**And a CRITERIA_VERSION stamp**, so the next sweep credits it on its
behaviour instead of its vocabulary:

```python
CRITERIA_VERSION = '2026-10-14.1'   # 37 synthetic arms + one opt-in live arm
```

**NOT a `--fixtures` arm.** The file *is* the fixtures. Adding a second
fixture layer to a fixture file is the busywork my b15 list would have
produced if nobody had driven it first.

---

## 3. ROW 50 — `tests/sairncash_entitlement_gate_probe.py`: TWO OF EIGHT MUTATIONS ARE NOT CAUGHT

**This is the real finding of the batch.** The baseline is green, the restore
is byte-identical, the clone is left clean — and the suite under test
**fails to notice two of the eight ways the entitlement gate stops being a
gate**:

```
CMD python tests/sairncash_entitlement_gate_probe.py    ->  EXIT 1
  ok   0. the suite is GREEN in the worktree before anything is planted (exit 0)
  ok   1. THE FORGERY THE FUNCTION EXISTS FOR -- no subscriptionId stops being refused
  ok   2. the refused record is REFUSED BUT NOT REMOVED
  FAIL 3. a server answer of INVALID is treated as valid
  ok   4. the NETWORK FALLBACK resurrects an EXPIRED record
  FAIL 5. the gate stops asking the server AT ALL and becomes the client-only check
  ok   6. THE GRACE PERIOD GOES and the offline fallback is unbounded again
  ok   7. the SKEW GUARD goes
  ok   8. the SUCCESSFUL VERIFY STOPS STAMPING
  2 ARM(S) FAILED
```

**A FAIL here does not mean the probe is broken. It means the SUITE IT DRIVES
did not go red when the gate was sabotaged** — the probe is working exactly as
designed and is reporting a hole in `tests/sairncash_entitlement_gate.js`.

### 3.1 What the two uncaught mutations are, in plain terms

* **Mutation 3 — "a server answer of INVALID is treated as valid."** The
  round-trip still happens, so the request is in the network tab and everything
  *looks* verified; the answer is simply ignored. **A revoked or refunded
  subscription keeps working.**
* **Mutation 5 — "the gate stops asking the server at all."**
  `reverifySubscription()` degenerates into the client-only `isSubscribed()`
  check it was written to replace — **which the suite itself asserts believes a
  forged record.** This is the entire gap the function exists to close, and the
  suite does not notice its removal.

**Both are failures in the direction that matters:** the suite stays green while
the paid product becomes free. **Mutation 1 — the forged record with no id — IS
caught, which is why this has gone unnoticed: the headline forgery is covered
and the two quieter paths around it are not.**

### 3.2 ROUTED TO cody — the two arms the suite is missing

The suite extracts the real functions from `sairncash.html` rather than
reimplementing them, so the arms belong in the same style:

```js
// tests/sairncash_entitlement_gate.js -- the two arms that would catch
// mutations 3 and 5. Written against the extracted function, not a copy.

// ARM A -- the server's NO must be obeyed, not merely requested.
// Catches mutation 3: the fetch happens and its answer is ignored.
{
  const calls = [];
  const fetchStub = async (url) => { calls.push(String(url));
    return { ok: true, status: 200, json: async () => ({ valid: false }) }; };
  seedStore({ valid: true, subscriptionId: 'sub_live', expiresAt: FAR_FUTURE });
  const ok = await reverifySubscription({ fetch: fetchStub });
  assert.strictEqual(ok, false,
    'the server answered valid:false and the gate still allowed access');
  assert.strictEqual(store.get('sairncash_sub'), null,
    'a record the server refused was left in place for the next load');
  assert.ok(calls.length >= 1, 'no request was made at all -- see ARM B');
}

// ARM B -- the server must actually be ASKED.
// Catches mutation 5: the gate degenerates into the client-only check.
{
  let asked = 0;
  const fetchStub = async (url) => { asked += 1;
    return { ok: true, status: 200, json: async () => ({ valid: true,
             subscriptionId: 'sub_live', expiresAt: FAR_FUTURE }) }; };
  seedStore({ valid: true, subscriptionId: 'sub_live', expiresAt: FAR_FUTURE });
  await reverifySubscription({ fetch: fetchStub });
  assert.strictEqual(asked, 1,
    'reverifySubscription() made NO server call -- it is the client-only '
    + 'check it was written to replace, and a forged record passes it');
}
```

**ARM B is the one to write first.** A gate that never asks is indistinguishable
from a gate that asks and obeys, from the outside, **until somebody forges a
record** — and ARM A's third assertion (`calls.length >= 1`) exists so ARM A
cannot accidentally pass for ARM B's reason.

**Exact next step for cody:** add both arms, then re-run
`python tests/sairncash_entitlement_gate_probe.py` and require **8 of 8**. The
probe is the acceptance test for the fix; it already exists and already fails.

---

## 4. WHAT THIS DOCUMENT DOES NOT DO

* **It does not edit `tests/`.** Both arm sets are delivered as code to place,
  because this batch writes `docs/` only and `tests/` has one writer.
* **It does not fix the four removal paths.** They are `api/`/`sql/` work and
  they are hank's; the choice between a removal path and a reasoned baseline
  row is his, per resource.
* **It does not re-run the whole b15 list through a corrected scorer.** Rows 44
  and 50 are struck here, with the reason; whether the other 23 rows contain
  more false positives of the same shape is **unmeasured**, and that is the
  honest state. The pattern that would fix it is behavioural, not another word.
* **It did not touch `sairncash.html`.** The probe's own arms confirm the
  worktree copy was restored byte-identically and that the clone was left with
  nothing newly dirty.
