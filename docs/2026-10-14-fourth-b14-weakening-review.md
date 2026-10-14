# REVIEW — the two open `[WEAKENING]` flags from hank b8 (`da7e88cf`) — 2026-10-14, fourth b14

**BOTH ARE SIGNED OFF AS FALSE POSITIVES.** Hank's own rebuttal in `da7e88cf`
was right in both cases, and this is the independent read it asked for rather
than a repetition of it: every claim below is checked against the file at
`file:line`, and in one case against the **production** code the test is about,
which the commit message does not cite.

**A flag reviewed by its author is not reviewed.** `da7e88cf` left both rows as
flags and said so — *"left as flags"* — which is the correct thing to do with a
triage prompt you cannot clear yourself.

```
CMD python -c "json.load(open('docs/scrutiny-flags.json'))" -> 483 flags, 108 at WEAKENING
    criteria_version 2026-10-06.1
```

---

## FLAG 1 — `api/role-vocabulary-agreement.test.js` — SIGNED OFF, false positive

**The flag:** shape *"a skip / exemption / allowlist entry ADDED"*, matched on
`+ 'skip is how a real app stops being checked', function () {`, sha
`28f7744e` (and again at `8775f616`).

**What is actually there — `api/role-vocabulary-agreement.test.js:320-333`:**

```js
test('every app WITHOUT an auth table is accounted for by name -- a silent '
  + 'skip is how a real app stops being checked', function () {        // :321
  const noTable = apps.filter(function (a) { return !AUTH_TABLE_BY_APP[a]; });
  assert.deepStrictEqual(noTable, ['stonedesk_sub'],                   // :328
    'unexpected app(s) with no auth table: ' ... 'which FAILS OPEN'); // :332
});
```

**VERDICT: the matched line is the TITLE of a negative control, and the arm it
titles makes the suite strictly harder to pass.** `deepStrictEqual` against a
one-element list refuses **any** new app that arrives without an auth table.
Nothing is exempted; an exemption is *detected*.

**THE DETECTOR IS NOT BEING STUPID, THOUGH, AND THAT IS WORTH SAYING.**
`['stonedesk_sub']` **is** a hard-coded allowlist — the shape is really present.
What the detector cannot see is the comparison operator: an allowlist under
`deepStrictEqual` fails when anything is added to reality, whereas an allowlist
under `includes()` silently absorbs it. **Same shape, opposite direction, and
only the operator distinguishes them.** That is a blind spot worth having
written down, and `docs/scrutiny-flags.json`'s own `blind_spots` list does not
currently name it.

**Corroborating detail the commit did not cite:** the arm's failure message
names the consequence of the state it refuses — *"credentialStillActive answers
NO_ACTIVE_CHECK and the request proceeds on the token alone, which FAILS
OPEN"* (`:331-332`). A weakening does not usually document the fail-open it
would cause.

---

## FLAG 2 — `api/sd-data-leg-bookings-toctou.test.js` — SIGNED OFF, false positive, and the exemption is sound on BOTH sides

**The flag:** two shapes on one file, sha `7da612f2` (and again at `8447c369`):
a *"bound or threshold ADDED"* matched on
`if (/_employee_auth\?.*&select=active&limit=1/.test(String(url))) {`, and a
*"skip / exemption / allowlist entry ADDED"* matched on
`section('5. cancelling a booking is exempt -- no check at all');`.

### 2a. The "bound added" hit is the test harness's fetch stub

`api/sd-data-leg-bookings-toctou.test.js:149`, inside the `global.fetch`
replacement that starts at `:142`:

```js
if (/_employee_auth\?.*&select=active&limit=1/.test(String(url))) {   // :149
  out.credentialChecks++;                                              // :150
```

It is a **URL match that routes a stubbed reply and increments a counter.** The
`limit=1` is not a threshold the production code gained — it is the shape of the
real query, at `api/_lib/auth.js:1125`:

```
CMD grep -rn "select=active&limit=1" --include=*.js api/
api/sd-data-leg-bookings-toctou.test.js:149
api/_lib/auth.js:1125
```

**A harness that did NOT match that URL would let the credential check fall
through to the generic reply queue and silently consume one of the test's own
stubbed replies** — so this line is load-bearing for the suite's accuracy, in
the strengthening direction. Hank's one-line rebuttal (*"the harness's
credential-check URL match"*) is correct and this is the evidence for it.

### 2b. "Cancelling is exempt" is a real exemption — in the PRODUCTION code — and the test asserts it by CALL COUNT

**The exemption exists at `api/sd-data.js:14967`:**

```js
if (resource === 'leg_bookings' && payload.status !== 'Cancelled') {   // :14967
```

documented immediately above it at `api/sd-data.js:14955-14958` — *"CANCELLING
IS EXEMPT BY DESIGN … a gate that refused a cancellation because the booking it
is cancelling overlaps something would be the fix causing the harm."*

**The test asserts it the hard way, `api/sd-data-leg-bookings-toctou.test.js:358-368`:**

```js
ok(r.calls.length === 1 && r.calls[0].method === 'POST',               // :364
   '...with ONE upstream call and no check, so it can never be refused for '
   + 'overlapping the thing it is cancelling -- ' ...);
```

**A `200` cannot tell an exemption from a check that happened to pass. A call
count of exactly one can.** That is the distinction hank's commit claimed, and
it is in the file.

### 2c. THE PART NEITHER THE FLAG NOR THE COMMIT CHECKED — the read side — and it holds

An exemption on the write path is only safe if the read path agrees. **It does,
at `api/sd-data.js:14987`:**

```js
if (d.status === 'Cancelled') return false;    // a cancelled row holds nothing
```

So a `Cancelled` row is **skipped on write and ignored on read**. The one abuse
I went looking for — write a live-looking booking with `status: 'Cancelled'` to
dodge the overlap check, then have it block the facility — **cannot happen**:
the row that dodged the check is also invisible to every later check.

**And both sides are asserted, which is what makes this a sign-off rather than a
shrug:**

```
CMD grep -n "section(" api/sd-data-leg-bookings-toctou.test.js
  :332  4. a row does not conflict with itself, and a cancelled row holds nothing
  :358  5. cancelling a booking is exempt -- no check at all
```

Section 4 drives a **held** row with `status: 'Cancelled'` (`:345`) and asserts
it does not clash; section 5 drives a **submitted** `Cancelled` payload and
asserts no check happens. **Two literals in two files must agree — `:14967` and
`:14987` — and there is an arm on each.**

---

## WHAT I AM ADDING TO THE RECORD, rather than only agreeing

1. **The WEAKENING level's measured precision gets worse, which is an argument
   FOR keeping it.** `da7e88cf` quotes the tool's own output: *"2 of 3 FALSE on
   the only real push it had seen"*. These two were also false, so on the
   evidence available it is now **4 false of 5 reviewed** (2 of 3 from the
   tool's own figure, which I did not re-derive, plus 2 of 2 here). **That is
   still not a reason to narrow it:** both of these took a reader about ten
   minutes, and the one shape it would have to stop matching to clear them —
   the word "skip" in an arm title — is also how a real skip reads.
2. **One blind spot to add to `docs/scrutiny-flags.json`'s own list** — *"an
   allowlist compared with `deepStrictEqual` and an allowlist compared with
   `includes()` are the same shape and opposite directions; this reads the
   entry, not the operator."* **Not written by me:** that file is written by the
   push gate and hank's batch, and a reviewer editing the file whose flags he is
   clearing is the shape I just signed off two findings against. **Routed to
   hank.**
3. **Nothing here closes the two rows.** `docs/scrutiny-flags.json`'s
   `merge_policy` and the gate own that file; this document is the review it was
   waiting for, and the rows should be marked reviewed by whoever may write
   there — citing this file.

## WHAT THIS REVIEW DOES NOT SAY

* **It does not say the TOCTOU fix is complete.** `api/sd-data.js:14949-14953`
  describes a residual millisecond-wide interleave between the SELECT and the
  upsert, and says so in those terms. I checked the exemption, not the race.
* **It does not say the suite is green.** I read it; I did not run it.
  `api/sd-data-leg-bookings-toctou.test.js` is cody's to drive.
* **It does not review the other 106 WEAKENING rows.** Two were open from
  `da7e88cf`; two were reviewed.
