---
name: sairn-code-scrubber
description: SAIRN-specific bug-pattern scanner. Encodes every recurring real bug class found across StoneDesk, SAIRNbiz, SAIRNvet, SAIRNcode, SAIRNgrounds, SAIRNscape, SAIRNbuild, SAIRNdesign, SAIRNlegacy, and SAIRNlaw during live development and testing. Use before any commit that touches data writes, dynamic SQL, cross-script JS, security/auth logic, or shared UI helpers.
---

# SAIRN Code Scrubber

Run this checklist on any file being touched before commit. Each item below is a bug class that has actually shipped in a SAIRN app and was later found live — not theoretical.

Items 1–15 are defects in APP code. **Item 16 is a defect in TEST code**, added 2026-09-02 because the platform hit it five times in one session across three apps. It is listed here rather than kept separate on purpose: a test that passes for the wrong reason does not merely fail to catch a bug, it certifies the bug — which makes it the most expensive class in this file. This preamble is amended rather than left saying "shipped in a SAIRN app", which would have stopped being true the moment item 16 was added.

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
