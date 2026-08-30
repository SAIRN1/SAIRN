# sairntech.com — shell + custom-work inquiry flow

**Written 2026-08-30 (CC). Scoping, not a build.** First item in the recommended
sequence, because it depends on nothing else and is the one place a failure
costs a real lead rather than a page view.

Companion to `2026-08-30-sairntech-corporate-site-scoping.md` (the three-funnels
pass) and `2026-08-30-sairntech-app-sellability-gate.md` (which blocks the
catalog, not this).

---

## 1. What "the shell" actually has to be

**The smallest thing that works.** A catalog of ~14 items does not need a CMS,
and this site is not a SAIRN app — no licence gate on the front door, public
crawling, real SEO, and a completely different performance profile from a 2 MB
single-file app behind a PIN.

**v1 shell:** static pages plus **one** endpoint (the inquiry). Home, a page per
offering, About/Engineering, contact. No account system, no cart, no database
schema for the site itself beyond what §5 needs.

**Deliberately not in v1:** user accounts, a cart, a CMS, a blog engine, search.
Each is addable; none is needed to take an inquiry, and every one of them is a
thing that must then be maintained. Per `sairn-minimalism`, the question is not
"what could the site have" but "what is the smallest thing that solves the stated
problem" — and the stated problem is *a real business can describe what they need
and get a reply.*

**One thing the shell must carry from day one:** the **About/Engineering** page,
because the skill pack lives there (§7) and because custom work is bought on
evidence of judgment, not on feature lists.

---

## 2. Success condition — say it before designing the form

**Not "form submitted." An inquiry a human can answer with a price.**

That single sentence decides every field. A field earns its place only if its
absence would make a quote impossible or a reply materially worse. Everything
else is friction, and friction on a lead-capture form is measured in lost
businesses.

**The corresponding failure**, and it is the real one: a well-designed form that
collects beautifully and **nobody answers**. See §6.

---

## 3. Fields

### Required — a quote is impossible without these

| Field | Why it earns its place |
|---|---|
| **Name** | Someone has to be replied to |
| **Email** | The reply channel. Validate format; do not verify-by-email before accepting — that loses leads |
| **Business / organisation** | Blank is a signal too (an individual, which is in scope) |
| **What do you need?** — free text, generous | The whole inquiry. Do not cap this at a tweet |
| **Budget range** — banded select | **The field everyone omits and the one that most determines whether a reply is possible.** Bands, not a number: under $2.5k / $2.5–10k / $10–25k / $25k+ / *not sure yet* |
| **Timeline** — banded select | ASAP / 1–3 months / 3–6 months / exploring |

**"Not sure yet" must be a real option on budget.** Forcing a number on someone
who genuinely does not know either loses the lead or produces a fabricated figure
that misleads the quote. An honest "not sure" is *information*.

### Optional — improves the reply, never blocks it

Phone · industry (free text, not a locked list — SAIRN's own industries keep
turning out to be more specific than expected) · existing systems in use ·
"anything you've already tried" · how they found us.

### Deliberately NOT collected

- **No file uploads in v1.** Attachments from strangers are a security and
  storage surface for very little gain at this stage.
- **No company size / revenue.** Reads as qualification and costs goodwill.
- **Nothing that looks like a credit application.**

---

## 4. Form or AI conversation — a real decision, not a preference

Both are viable and they fail differently.

**A form** is predictable, fast, accessible, works without JS, and produces
uniform records. It gets shallow answers from people who do not know how to
describe what they need — which is most of them.

**An AI intake conversation** asks follow-ups and produces genuinely better-scoped
inquiries. It is also a **public, brand-facing assistant talking to strangers**,
which brings a hard constraint from this platform's own history:

> **It must never state or imply a price.**

Precedent: SAIRNroofing's operations assistant was changed to refuse
claim-strategy questions outright because *"it was never given claim data, but
nothing stopped it answering a negotiation question from general knowledge, and
an app-branded answer of that shape was the real exposure."* An intake assistant
that says "that sounds like about ten thousand dollars" has made an offer under
the company's name. The refusal belongs in the **system prompt**, not in a
disclaimer under the chat box.

**Recommendation: form for v1, AI as a v2 enhancement layered on top of the same
record.** The form is a day of work with no new failure modes; the assistant is a
week plus an ongoing brand-safety surface. Build the thing that captures the lead
first, then improve the quality of what it captures.

**If the AI route is chosen later**, three non-negotiables: never a price, always
a visible "just send me the form instead" escape, and the structured record is
written from the conversation — the transcript is not the record.

---

## 5. What happens after submit — the part that actually matters

Three things must happen, and **two of them are the record**:

1. **Persist it.** Supabase, append-only, with a status field. This is the
   record of the lead.
2. **Notify.** Email to a real monitored address via Resend — the path is already
   verified and proven on `notifications.sairntech.com` with provider-issued send
   ids. Use `RESEND_FROM_EMAIL`; **`RESEND_FROM_ADDRESS` is the name that never
   existed and silently broke two apps for months.**
3. **Acknowledge.** An immediate confirmation to the submitter **stating the
   response time** (§6).

**The email is the notification, not the record.** An inbox is where leads go to
be lost, and this platform has a whole skill about a write that reports success
while failing. Which produces the hard rule:

> **If the database write fails, the submission fails and the user is told —
> loudly, with the address to email directly.** Never show "thanks, we'll be in
> touch" over a lost inquiry. A fire-and-forget write behind a success toast is
> the exact silent-failure pattern `sairn-silent-failure-sweep` exists for.

**Status lifecycle:** `new → acknowledged → quoted → won / lost / no-reply`.
Minimal, but it makes "how many did we not answer" a query instead of a feeling.

---

## 6. Response time — state it, then keep it

**An unanswered inquiry is worse than no form**, because it converts interest
into a bad impression.

- **Put the SLA on the form and in the acknowledgement**, in the submitter's
  terms: *"We reply within two business days."* If it is really five, say five.
- **Alert on breach.** A `new` record older than the SLA should surface
  somewhere a human looks. The platform already has scheduled-check patterns.
- **Do not promise a quote in the acknowledgement** — promise a *reply*. Some
  inquiries need a conversation before a number, and some need a decline.

---

## 7. The About/Engineering page carries the skill pack

Custom work has the weakest cold-start story of the three offerings — no product
to try, no price to compare. **It is bought on evidence of judgment.**

The strongest available evidence is already public: the Claude Code plugin
marketplace under SAIRN Technologies LLC, now backed by **nine SAIRN-original
skills** vetted against a real shipping gate. A prospect reads a public
engineering artifact very differently from a marketing page.

**Recommendation stands from the scoping pass: credibility asset, not a catalog
product.** Link it from About/Engineering. Nearly free, and it does more for the
inquiry flow's conversion than anything on the inquiry page itself.

---

## 8. PII and retention — decide before the table exists

An inquiry describing someone's business in detail is **commercially sensitive to
them**. Same discipline this platform applies to winner SSNs and DD-214 evidence:
decide up front, not after the table has rows in it.

- **Collected:** name, email, optional phone, organisation, free-text business
  description.
- **Access:** whoever answers inquiries. Not public, not in any client-side
  bundle, not in an analytics payload.
- **Retention:** a stated period — suggest **24 months** from last contact, then
  purge or anonymise. Written down and shown in a privacy note.
- **Encryption at rest** and no inquiry content in logs.
- **A privacy note the form links to**, saying what is collected and why. Short.

---

## 9. Open questions for Michael

1. **Response-time SLA** — the number that goes on the form (§6).
2. **Where inquiries land** — which monitored address, and who owns the reply.
3. **Budget bands** — the ranges above are a starting proposal, not researched
   against real pricing, which is unscoped.
4. **Form vs AI intake for v1** — recommendation is form; the AI route needs the
   never-a-price constraint accepted explicitly.
5. **Is an individual (non-business) inquiry in scope?** The offering says
   "businesses or individuals," which the form should reflect rather than
   assuming a company name exists.

## 10. Not covered here

Visual design and brand. Copy. Pricing and the budget bands' real ranges. SEO.
Accessibility, which for a public commercial site is a materially higher bar than
an internal tool and deserves its own pass. Anything about the catalog or ebook
funnels — the catalog is blocked behind the sellability gate and the ebooks
behind a counsel review.
