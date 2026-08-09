---
name: sairn-code-scrubber
description: SAIRN-specific bug-pattern scanner. Encodes every recurring real bug class found across StoneDesk, SAIRNbiz, SAIRNvet, SAIRNcode, SAIRNgrounds, SAIRNscape, SAIRNbuild, SAIRNdesign, SAIRNlegacy, and SAIRNlaw during live development and testing. Use before any commit that touches data writes, dynamic SQL, cross-script JS, security/auth logic, or shared UI helpers.
---

# SAIRN Code Scrubber

Run this checklist on any file being touched before commit. Each item below is a bug class that has actually shipped in a SAIRN app and was later found live — not theoretical.

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
