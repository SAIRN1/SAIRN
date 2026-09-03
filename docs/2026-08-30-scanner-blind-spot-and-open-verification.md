# Two queue items, one answer: the scanner blind spot and the open browser verifications

> ## ⚠ THE BLOCKER IN THIS FILE IS GONE. THE SEED HAS BEEN RUN.
>
> This document says `sql/stonedesk_recovery_admin_seed.sql` **"has never been
> run"** and treats that as the thing blocking three verifications. **That was
> true on 2026-08-30 and stopped being true within a day.** Re-verified against
> the live API on 2026-09-03, not inferred from any document:
>
> ```
> POST /api/sd-auth  Bearer SD-AUDIT-2026  {"action":"login","employee_id":"sd-recovery-admin","pin":"40318627"}
>   -> 200 {"ok":true,"role":"admin","employee_id":"sd-recovery-admin"}
> ```
>
> Three controls, because one success proves less than a success plus refusals:
> a bogus licence returns `INVALID_LICENSE`; the **wrong PIN** on the same real
> employee returns `INVALID_CREDENTIALS`, so the PIN is genuinely being verified
> rather than the endpoint accepting anything; an unknown employee id returns the
> **same generic** message, so there is no user enumeration. The roster read shows
> `sd-recovery-admin`, role `admin`, `active: true`, alongside `audit-owner` and
> three others.
>
> **The three items this file said were blocked were closed on 2026-08-31** — see
> `docs/2026-08-31-stonedesk-authenticated-verification.md`, which used exactly
> this credential.
>
> **And the question the seed's own step 3 existed to settle is answered:**
> `{"action":"read","resource":"sd_hr_employees"}` returns
> `{"ok":true,"data":[],"provisioned":true}` — **`sql/sd_hr_schema.sql` is live.**
>
> Left as written below rather than edited. The reasoning about the blind spot is
> still the reference and is unaffected; only the *"is it run yet"* claim went
> stale, and rewriting the sentence would delete the evidence that a
> committed-but-never-loaded artefact is a real and recurring failure shape.

Both questions resolve to the same action, so they are written up together.

---

## Item 1 — is the literal-only scanner blind spot worth closing?

**Recommendation: do not build a new static tool. Close it with one DOM
assertion inside the `sairn-visual-review` pass that already exists.**

### The blind spot, stated precisely

Every markup scanner run tonight reads **string literals**. Markup whose tags
arrive through a variable is invisible to all of them:

    var tag = cond ? '<div>' : '<span>';
    el.innerHTML = tag + content + '</div>';

The usual defence is "it fails in the false-negative direction, which is safe."
That is true and it is not the strongest argument. **The stronger one is that
the blind spot is much narrower than it looks.**

### Why it is narrower than it looks

Three mechanisms actually put literal markup on a customer's screen. Two of them
are **not** hidden by dynamic tags at all:

| Mechanism | Hidden by the blind spot? |
|---|---|
| Markup assigned to `textContent` / `innerText` | **No.** Detected on the *assignment target*, regardless of where the content came from. |
| Double-escaped entities | **No.** A property of the escaper function, which is a literal. `H()` is identical and correct in every app. |
| Unterminated attribute quote | **Yes** — but only if the quote character itself comes from a variable. |

And the fourth candidate is not a mechanism at all: **an unclosed container tag
inside `innerHTML` does not expose raw HTML** — the browser auto-closes it at the
end of the host element. That finding is what pulled dozens of false `{'div': 1}`
hits out of the sweep.

So the blind spot hides exactly one narrow case, and that case is normally
prevented by `H()` escaping the quote before it can reach a variable.

### The argument that actually settles it

**None of tonight's real findings came from a markup scanner.** Three
unreachable features, six discarded fetch injections, eight dormant hooks,
eleven colliding element ids — every one was found by tracing *execution*, not
by scanning *markup*. Investing in a better markup scanner optimises the axis
that has produced nothing.

### What to do instead — one line, in a pass that already runs

`sairn-visual-review` already launches each app in Playwright, already logs in
past the PIN gate, and already visits every panel. It reviews **screenshots by
eye**, which is exactly the wrong instrument for this: a literal `<div>` in body
text is easy to miss visually and trivial to assert against the DOM.

Add one assertion to its method — after each panel loads, walk the rendered DOM
for a text node containing a literal `<` followed by a tag name. That closes the
blind spot **completely for every path the pass exercises**, including markup
built entirely from variables, because it observes output rather than source.

Cost: one step in a pass that already pays the expensive parts (browser, login,
navigation). No new tool, no new maintenance surface, no second thing to keep in
sync.

**Verdict: acceptable and disclosed as a static limit; closed for real by the
browser pass.** Not worth a new static analyser.

---

## Item 2 — are the auth-gated blind spot instances resolved?

Guardian v2 §"Known Scope Limitation: Auth-Gated Content" states the remedy
plainly: *"Always run `sairn-visual-review` (or an equivalent real-login test) at
least once per major change, not just code-level checks, on anything
auth-gated."*

Measured against that, of the four instances raised tonight: **one is closed,
three are open.**

| # | Instance | Status |
|---|---|---|
| 1 | `/stonedesk-hr` link — new tabs do not inherit sessionStorage | **CLOSED** |
| 2 | Three features unreachable behind a `display:none` stub | **OPEN** |
| 3 | Raw-HTML exposure sweep | **OPEN** (disclosed limit; zero found) |
| 4 | Six fetch patches discarding their injections | **OPEN** (fix proven, effect unverified) |

**1 — closed, and closed the right way.** The comment at `stonedesk.html:28296`
records it was *"Tested live 2026-08-30 rather than reasoned from spec, and the
result was worse than expected — the child tab read null even WITHOUT
rel='noopener'."* That is the real-login test Guardian asks for, and reasoning
from spec would have produced the wrong fix. The class was then swept
platform-wide and is clean.

**2 — open, and it is the one that matters.** Document Upload, Feature 9 Compare
and the multi-modal camera path each inject their only trigger into
`#sairn-intake-actions`, which exists solely as a `display:none` stub. Evidence
is source plus live HTTP: no markup caller, no un-hiding code, injection into a
hidden parent. That is a strong prediction and **it is not a confirmation.**
Precisely the shape Guardian's limitation describes.

**3 — open by disclosure rather than by doubt.** Six static checks found zero,
and the symptom is by definition a rendering outcome. It also remains
**unreconciled**: the originally-reported instance could not be located in any
commit, doc or work log, so a known-positive has never been shown to the
scanners.

**4 — the fix is proven; the effect is not.** A four-case harness and an
end-to-end chain proof both ran: forwarding via `apply` delivers zero injection
layers, via `call` delivers all three. What is unverified is the product
outcome — that Session Memory now actually carries context between turns, and
that the Tone setting now visibly changes a reply.

### One pass closes all three

Items 2, 3 and 4 are all waiting on the same thing: **one Playwright session
with a real login.** Click the three panels (confirms or refutes #2), assert no
text node contains literal markup (closes #1 above and #3), and send two chat
turns with the tone setting changed between them (confirms #4).

**The blocker is a credential, and it is already written.**
`sql/stonedesk_recovery_admin_seed.sql` is committed and **has never been run** —
verified live, `401 INVALID_CREDENTIALS`, with a bogus-key control proving the
licence is real and the row simply absent. It exists specifically so a
verification pass does not need `SD-PINNACLE-2026`, which holds real customer
accounts.

**Running that seed unblocks all three open items at once.** It needs the
Supabase SQL editor, and the three blocks must be run separately — the
precondition counts first, then the insert, then the confirm.
