---
name: sairn-code-scrubber
description: SAIRN-specific bug-pattern scanner. Encodes every recurring real bug class found across StoneDesk, SAIRNbiz, SAIRNvet, SAIRNcode, SAIRNgrounds, SAIRNscape, SAIRNbuild, SAIRNdesign, SAIRNlegacy, and SAIRNlaw during live development and testing. Use before any commit that touches data writes, dynamic SQL, cross-script JS, security/auth logic, or shared UI helpers.
---

# SAIRN Code Scrubber

Run this checklist on any file being touched before commit. Each item below is a bug class that has actually shipped in a SAIRN app and was later found live — not theoretical.

Items 1–15 are defects in APP code. **Item 16 is a defect in TEST code**, added 2026-09-02 because the platform hit it five times in one session across three apps. It is listed here rather than kept separate on purpose: a test that passes for the wrong reason does not merely fail to catch a bug, it certifies the bug — which makes it the most expensive class in this file. This preamble is amended rather than left saying "shipped in a SAIRN app", which would have stopped being true the moment item 16 was added.

**Items 17–21 added 2026-09-14**, and four of the five are defects in the TOOLS AND TESTS rather than in app code — which is now the majority of this file's recent growth and is worth saying out loud. The measured split over all 67 confirmed defects on 2026-09-14: **49% were caught only because a person read the code**, 51% by an automated checker, and **0% by monitoring**. A checklist a human runs is therefore still doing half the work here, so a bug class that lives in the checking apparatus itself is the one most likely to go unnoticed — there is nothing behind it.

## 1. Unquoted/mis-quoted object keys with spaces
JS object literal keys containing spaces MUST be quoted: `{'Sent to Client': 'bb'}` not `{Sent to Client: 'bb'}`. Unquoted breaks parsing silently in some contexts and produces duplicate map entries in others (one broken, one working) — grep any statusColors/lookup map literal for unquoted multi-word keys.

## 2. Postgres %L vs %I in dynamic SQL
In `format()` calls building dynamic SQL, %L is for string LITERALS, %I is for IDENTIFIERS (table names, column names, policy names). Using %L for a policy/table/column name produces invalid SQL syntax errors at runtime. Check every `format()` call in a DO-block or function against what each %-placeholder actually represents.

## 3. Print CSS scoping
A generic `@media print { .panel { display:block!important } }` rule will print EVERY panel plus modal backdrops when a user clicks a scoped "Print" button inside one specific modal/panel (e.g. a GPL or invoice). Any print-triggering button must have its own scoped print rule (`#specific-modal-id { ... }` only) tested by actually triggering print preview, not just reading the CSS.

## 4. Fire-and-forget unawaited writes
Any `xxxData('write', ...)` or equivalent async write call MUST be awaited and its result checked before showing a success toast. A write that fails silently while the UI shows "Saved" is a data-loss bug that looks fine in every manual click-through. Grep for write calls not preceded by `await` or not followed by a result check.

## 5. Bare/collided resource names across apps
Resource/table names shared by multiple apps on the same backend MUST be app-prefixed (grd_, scp_, sdn_, leg_, law_, etc.). A bare name like `irr_zones` used identically by two apps means whichever app's route is checked last silently overwrites/reads the wrong app's data, or gets zero routes at all. Before adding any new resource, grep the shared API file for the exact string across ALL apps, not just the one being worked on.

## 6. IIFE scope leaks
Variables/functions declared inside one `<script>(function(){ ... })()</script>` IIFE block are invisible to a different IIFE block in the same file. A function call that references something from another block fails silently or throws "not defined" before reaching otherwise-correct code. When adding a new script block, check whether it needs anything from an existing block and either merge scope or explicitly attach to `window`.

## 7. Client-side-only authorization
Any role/permission check that only exists in client-side JS (hiding a button, disabling an action in the UI) is bypassable via browser devtools/direct API call. Every write endpoint that has real authority implications (void, override, approve, delete, role change) MUST re-check the role server-side, reading the actual session/token — never trust a role value the client sends in the payload.

## 8. HTML-attribute-escaping vs JS-escaping mismatch
A helper like `H()` that HTML-escapes a string for safe display in an attribute does NOT make that string safe to use as a JS string literal inside an `onclick="..."` attribute — the browser decodes HTML entities back to their original characters before the JS parser sees them. A name like `O'Brien v. Smith` breaks the handler. Any free-text (not an id/enum) going into an onclick argument needs real JS-string escaping (backslash-escape quotes), not just HTML escaping.

## 9. Assumed API response shape
Never assume a nested object shape from an external API (e.g. `response.cluster.name`) without checking what the API actually returns first — it may be a plain string (a URL) instead of a nested object. Log/inspect one real response before writing code that destructures it, especially for third-party APIs.

## 10. Security toggles without re-authentication
Any action that changes a security posture (disabling MFA, changing a role, resetting a password) must require re-proving identity for that specific action (a fresh code, an Owner-only gate with audit log) — never allow it to succeed just because a session token is present. A stolen/leaked session token should not be enough to turn off a security control.

## 11. Invisible/low-contrast UI elements
Reused header/nav button styles (e.g. white-on-translucent) can become invisible when reused on a different background (a light modal/card). Any button style being reused in a new visual context needs an actual screenshot check, not just a markup/logic review — markup can look completely correct while being invisible to a real user.

## 12. Missing GRANT privileges on new tables
A newly created Supabase table does not automatically inherit the privileges the app's service role needs. `CREATE TABLE` followed by an app trying to read/write immediately can produce 42501 permission denied even though the table exists and RLS is configured correctly. New table migrations should end with explicit `GRANT`/`REVOKE` statements, not rely on default privilege propagation.

## 13. UTC-midnight date bugs
`new Date().toISOString().slice(0,10)` gives the UTC date, not the user's local date — this is wrong for "today" anywhere west of UTC in the evening (a real bug at 9pm Eastern shows tomorrow's date). Any "today" calculation needs a real local-date helper, not a UTC-based one-liner.

## 14. Modals not closing on navigation
If a modal is opened and the user navigates to a different panel without clicking the modal's own close button, a `nav()` function that only toggles panel/sidebar classes (not modal classes) leaves the modal visually floating over whatever loads next. Any shared navigation function should close all open `.modal.on` elements as part of switching panels, in one shared choke point — not per-modal.

## 15. AI chat placeholder removed by DOM position, not by identity
A chat-style AI feature that shows a "Thinking..." placeholder while awaiting a response, then removes it via `querySelectorAll('.ama')` + take-the-last-element, silently misattributes the answer (or leaves a permanently stuck placeholder) the moment two questions are in flight at once — whichever request resolves first removes the OTHER request's placeholder, not its own. Shipped this exact way in three apps (`sairnbiz.html`, `sairnscape.html`, `sairngrounds.html` — the third found only by a fresh adversarial-review pass, since the other two had already been fixed and nobody had re-checked the third for the same class). Fix: the placeholder-adding function must `return` the DOM node it creates; the caller holds that specific reference and removes exactly that node in both the success and error handlers, never "the last one in the DOM." Any new AI/chat feature added to any app needs this pattern from the start, not retrofitted after a live report.

## 16. An assertion that passes for the wrong reason
A test that passes for the wrong reason does not merely fail to catch a bug -- it CERTIFIES the bug, and a green suite is then evidence for the wrong conclusion. Found FIVE times in one session (2026-09-02) across SAIRNlaw, SAIRNdental and SAIRNsenior, in two distinct shapes. Every one was found by deliberately breaking the code and watching the suite, never by reading the test.

**Shape A -- the assertion matches PROSE ABOUT the code instead of the code.** Three cases, all false FAILURES, all from running a regex over a window of a file that also contains commentary:
- a `no delete grant` check split the schema file on its grant statements and searched the remainder for the word `delete` -- and matched the file's own comment explaining why there is no delete grant;
- a `no margin or profit is computed` check ran from the SECOND occurrence of the function name (its call site) straight into the panel's user-facing disclosure, which contains the words *"no margin or profit figure is computed here"* -- the test failed on the sentence written to say the thing it was checking for;
- a `the rule's own carve-out is quoted in the engine` check missed because the quote is line-wrapped across `//` comment lines, so the single-line regex could not see it.

**THE RULE: assert against EXTRACTED CODE, never against a window of a file that also contains commentary about that code.** Pull the function body out by brace-balance and match inside it. Where the target genuinely is prose (a disclosure that must appear on screen), scope the match to that element and say in the test that prose is what is being asserted. Where a quote is wrapped, match across the wrapping rather than assuming one line.

**Shape B -- the assertion tests EXISTENCE where the requirement is USE.** Two cases, both false PASSES, which is the dangerous direction:
- a lookup table replaced a stale ternary; the test asserted the table EXISTED. Reverting the call site to the old ternary while leaving the table declared passed 32/32;
- a rollup had to bucket unassigned rows separately; the test asserted the totals added up and that an `Unassigned` row existed. Attributing every unassigned CLIENT to the first branch still totalled correctly, and an `Unassigned` row still appeared because an unassigned CAREGIVER made one -- passed 28/28.

**THE RULE: assert the thing is CONSULTED, not that it is declared; and assert rows land in the right bucket, not that the buckets sum.** `total === expected` is satisfied by every possible misallocation. Assert the per-bucket contents. Where a mechanism replaces an older one, assert the old one is ABSENT at the call site as well as that the new one is present.

**AND THE STANDING PRACTICE THAT CAUGHT ALL FIVE:** before trusting a new suite, break the behaviour it exists to protect -- one deliberate edit per claim -- and confirm the suite goes red and names the right thing. Restore the file and verify it is byte-identical afterwards. A suite that has never been seen to fail is a suite whose behaviour nobody knows.

## 17. A sabotage control that silently no-ops when its anchor moves
A negative control proves a checker can FIRE by planting a defect and asserting the checker goes red. Almost all of them do it with `src.replace(anchor, ...)` — and **`str.replace` returns the string unchanged when the anchor is not found**. Rename the thing the anchor points at and the control runs the checker against an UNMODIFIED file, forever, saying nothing. **MEASURED 2026-09-13: 24 of 40 probes that patch a real source file never verify the patch landed** — read the live figure from `python tools/sabotage_control_check.py`, never from a document, because it moved three times in one evening.

The loud outcome is an arm failing against a tool that works, which is how it was noticed. **THE QUIET ONE IS WHY IT MATTERS: an arm written as "expect no findings" keeps PASSING on a file nobody touched, and reports green forever.**

**THE RULE: a control asserts its own sabotage APPLIED before it asserts anything about the checker.** Compare the bytes, or use a helper that RAISES when the anchor is absent — never call `str.replace` directly in a probe. And restore by comparing byte-for-byte afterwards, **after `tr -d ''`**: a CRLF-vs-LF difference is not drift, and mistaking one for drift produced three false alarms in a single session on 2026-09-03.

## 18. A control character typed literally instead of as an escape
`\b` typed into a heredoc becomes byte `0x08`, a literal BACKSPACE, and a regex containing it **can never match**. An assertion built on it passes unconditionally forever. **This has now happened FOUR times**, most recently at `api/sv-auth.test.js:301`, where `!/\bdelete\b/i.test(SRC)` became `!/[BS]delete[BS]/i.test(SRC)` — so the test *"NOTHING in this endpoint deletes a credential row"* had always passed without checking anything, on a DEA-relevant path.

**THE RULE: never build a regex through a shell heredoc.** Write the script to a file, or construct the escape with `chr(92)` so no raw byte can exist. `python tools/control_char_check.py` finds them; it is promoted to push-gate check 11. **And when you find one, check what the corrected pattern actually matches before fixing it** — a vacuous green becoming a real red is a different, larger job than a one-line repair.

**AND IT HAPPENED AGAIN WHILE THIS ENTRY WAS BEING WRITTEN — the fourth time.** The heredoc that added this section turned its own `\\b` into three literal `0x08` bytes, inside the paragraph explaining that exact failure. `control_char_check` caught it before the commit. **That is the argument for the rule in its strongest possible form: knowing about this class does not protect you from it — only building the escape with `chr(92)`, or never using a heredoc, does.**

## 19. A helper called with its arguments in the wrong order
A checker or adapter that takes two same-typed parameters — `(expected, actual)`, `(engine, invariant)`, `(needle, haystack)` — silently does nothing useful when they are swapped, because both sides are strings and nothing complains. The financial invariant runner reported `ledger.validateEntry` as **2000/2000 STABLE while MISCLASSIFIED**: the adapter asked for `debits_cents`, the engine returns `debit_total`, and `undefined === undefined` is true on every case. **A vacuous perfect score.**

**THE RULE: a comparison whose two sides can both be `undefined` must assert they are DEFINED before it asserts they are equal.** And report accuracy and stability as two numbers, never one — a single figure hides which of the two failed, and here the very next row failed the opposite way.

## 20. A seam that agrees on the number and disagrees on the unit
Two modules pass a value across a boundary and both are internally correct; what neither owns is the SCALE. Cents against dollars, minutes against milliseconds, a rate against a percentage. Nothing throws, the arithmetic is plausible, and the answer is wrong by exactly 100 or 60 or 1000. Related to item 19 but distinct: the arguments are in the right order and the shapes match — **only the unit is unstated, so no type check and no shape assertion can see it.**

**THE RULE: put the unit in the NAME at every seam** — `amount_cents`, `window_seconds`, `rate_bp` — and assert a boundary value that would be visibly absurd at the wrong scale, not a round number that looks reasonable either way. A test using `100` cannot tell cents from dollars; one using `1870.93` can.

## 21. Money compared as a floating-point number
`Math.abs(a - b) > TOLERANCE` on money, with the tolerance at `0.00`, **refuses correct values**. Two partial deliveries of `$1,870.93` and `$1,957.54` sum to `3828.4700000000003`, so a `$3,828.47` bill against a `$3,828.47` purchase order came out `4.5e-13` apart and was REFUSED — printing *"billed $3828.47 against $3828.47 actually received"*, two identical figures and a refusal nobody could act on. Found 2026-09-14 in SAIRNbiz's three-way match, by an independent review that RAN the shipped function rather than reading it.

`api/_lib/ledger.js` already states the rule in its own header: *"a ledger that decides balance with a float comparison will one day refuse a correct entry or accept a wrong one."* This was the first of the two, which is the safe direction and is still a gate people route around.

**THE RULE: convert to integer cents at the boundary and compare integers.** Convert the TOLERANCE too rather than assuming it is zero, so a future non-zero tolerance does not become a second place somebody has to remember. And return `0`, never `NaN`, for a non-finite input — **NaN compares false against everything including the tolerance, so a corrupt row would silently MATCH.**
