# Platform-wide sweep: unclosed functions and tags exposing raw HTML

**Scope:** all **19** HTML files in the repo, every inline script block in each.

**Result: zero occurrences found. Nothing was fixed, because nothing needed
fixing.** Five checks ran clean, one check produced two hits that were both
false positives on inspection, and one method failed outright and is reported as
failed rather than dressed up as findings.

**One thing I could not do, stated up front:** the instruction referenced "the
one instance already found." **I could not locate it.** It is not in any commit
touching a `.html` file since 2026-08-29 (only three exist — `f9a671d`,
`510d8ce`, `062755b`, none of them a markup fix), not in any doc in `docs/`, and
not in any of the four `SAIRN-ACTIVE-WORK-*.md` files. **So this sweep is not
reconciled against a known-positive case, and that matters:** a scanner that has
never been shown a real instance of the bug it hunts is unproven, not clean. If
that instance was found in a browser session or in another clone, point me at it
— if my scanners miss it, they have a blind spot worth more than this report.

---

## What ran, and what each check can actually see

### 1. Unclosed function — `node --check`, every block, every file

| | |
|---|---|
| Scope | 161 inline script blocks across 19 files |
| Result | **161 / 161 pass** |

A genuinely unclosed function is a syntax error, so this check is exhaustive
rather than heuristic: it cannot miss one. Per-file counts —
`stonedesk` 126/126, `sairnmechanical` 6/6, `sairnscape` 5/5, `sairngrounds`
3/3, six files at 2/2, nine at 1/1.

Worth stating because it is the half of the bug class that *can* be settled
absolutely: **there is no unclosed function anywhere on the platform.**

### 2. Static markup tag balance — all container tags, not just `<div>`

**All 19 files balanced.** Counted opens against closes for every non-void tag
after stripping `<script>`, `<style>` and comments.

`stonedesk.html` initially reported `rect 0/2` and `svg 1/2`. **Both were my
scanner's fault, not the file's:** the favicon at `:36` is a
`data:image/svg+xml,<svg …>` URI living *inside an `href` attribute*, so its
tags are attribute text and not markup; and I had `rect` in the void-element
list while the file closes it explicitly at `:2927` and `:2930`, so closes were
counted and opens were not. Corrected, the file is balanced. Recorded because a
checker that reports its own bugs as defects is worse than no checker.

### 3. HTML markup assigned to `textContent` / `innerText`

**0 occurrences.** This is the purest form of the symptom — assign markup to
`textContent` and the customer sees literal `<div>` on screen. Scanned every
such assignment in all 19 files for a string literal containing an HTML tag.

### 4. Double-escaped entities (`&amp;lt;`)

**0 occurrences.** Double escaping renders as visible literal tags. None exist.

### 5. The escaper itself

Every app that defines `H()` defines it identically and correctly:

    function H(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;')
      .replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');}

`&` is replaced **first**, which is the ordering bug that produces double
escaping when it is got wrong. It is not got wrong anywhere.

### 6. AI reply rendering — the largest customer-visible markup surface

The shared `addMsg(t, role)` used by SAIRNbiz, SAIRNdesign, SAIRNlaw,
SAIRNgrounds and SAIRNscape sets `d.textContent = t`. Plain text in, plain text
out: no injection, and no raw markup exposure.

### 7. Unterminated attribute quote — 2 hits, **both false positives**

Flagged `stonedesk.html:9902` and `:13423`. Both are ordinary concatenation
where the literal ends mid-attribute and the quote closes in the next literal:

    '<span class="badge ' + (tier.mult …
    '<span title="' + (warn ? … : '') + '" style="…

Not defects. Reported rather than silently dropped, because the count "2" would
otherwise look like two unfixed bugs.

## The method that failed, reported as failed

I also scanned for a tag opener with no `>` following it — the literal
"unclosed tag." It returned **1192 hits and every one I checked was noise.** The
apps build markup by concatenation, so `'<div style="background:' + colour +
'">'` legitimately ends a literal in the middle of a tag, thousands of times.

**The check is unusable as written and is not counted in the results above.**
Recording it because the alternative — quietly dropping it — leaves the next
person to rediscover that this exact approach does not work. A structural
checker that over-reports trains people to ignore it, which is the same lesson
`e6fda06` wrote into `sairn-differential-review` §10b from a different direction.

## Why an unclosed container tag is not, on its own, the bug

Worth stating because it shaped the scan. An unclosed `<div>` inside an
`innerHTML` assignment does **not** expose raw HTML — the browser auto-closes it
at the end of the host element and the customer sees nothing wrong. That is why
checks 3, 4 and 7 target the mechanisms that genuinely put literal markup on
screen, rather than counting unbalanced fragments.

An earlier version of this sweep did count them, produced dozens of `{'div': 1}`
results across seven apps, and every one was a fragment legitimately closed by a
later `+=` or by its caller. Those are not in this report.

## Honest coverage limits

- **Literals only.** Every scanner reads string literals. A fragment whose tags
  arrive through a variable is invisible to all of them. That is a
  false-negative direction — the safe one for a checker, but it is not zero.
- **No browser was involved.** Every claim is from source. The symptom is by
  definition a *rendering* outcome, and the only instrument that settles a
  rendering question is a rendered page. This is the auth-gated blind spot
  `sairn-guardian-v2` names in its own Known Scope Limitation, and it applies
  squarely here.
- **Unreconciled.** See the note at the top. Without the known instance, "zero
  found" means "zero found by these six checks," not "zero exist."
