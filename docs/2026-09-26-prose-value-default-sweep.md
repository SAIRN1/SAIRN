# A value parsed out of model prose, with a silent default — swept 2026-09-26

**Methodology sweep. One defect found and deleted the same day; nothing else on
the platform carries it.**

**HEADLINE: nine other sites extract a value from model output and every one of
them gets the fallback right, each in a different way. The class is real, it cost
one module, and the platform's existing practice already answers it — so what
this sweep produces is a stated convention and a MEASURED argument against
building a gate, not a new checker.**

Swept at `14bd1ff1`, 2026-09-26, across every root `*.html`, `api/*.js` and
`api/_lib/*.js` — 363 files.

---

## 1. The class, stated precisely enough to recognise

**It is not `.match()`. It is the fallback.**

A model returns prose. Code pulls a value out of it with a regex or a
`JSON.parse`. The pattern misses — because the model answered in a different
shape, or hedged, or the response was truncated. **The defect is a fallback that
substitutes something which will be USED as if it had been extracted.**

    // THE DEFECT
    var m = txt.match(/score[:\s]+(\d+)/i);
    var score = m ? parseInt(m[1]) : 5;        // <- 5 came from nowhere

    // THE CORRECT SHAPE
    var m = txt.match(/score[:\s]+(\d+)/i);
    var score = m ? parseInt(m[1], 10) : null; // <- a miss stays visible

`null`, `''`, `undefined` and an empty list are all correct: they make the miss
propagate to something that can refuse. A number, a plausible string, or a
constructed object is the defect, because **nothing downstream can tell it from a
real answer.**

### 1.1 The one instance, and what it cost

`stonedesk.html`'s orphaned `vmAnalyze()`, deleted 2026-09-26 (`@REGISTER
module=vein-matching-ai`):

    var scoreMatch=txt.match(/(\d+)\s*\/\s*10|score[:\s]+(\d+)/i);
    var score=scoreMatch?(parseInt(scoreMatch[1]||scoreMatch[2])||5):5;

Rendered as a 60px filled circle headed **"Vein Match Score"** with a verdict
beside it — *"Good match — will work"* at 5. Three things make it the worst
version of this class rather than an average one:

1. **The default is inside the vocabulary of real answers.** 5 on a 1–10 scale is
   not a sentinel; it is a middling score, and a middling score is the single
   most believable wrong answer.
2. **`||5` sits INSIDE the parse as well as outside it.** `parseInt('0')` is
   falsy, so a genuine score of 0 — the strongest possible "do not cut these
   slabs together" — also became 5. **The two failure modes converge on the same
   number**, which is why one `||` was doing more damage than it looked.
3. **It was rendered with colour.** `score>=8` green, `>=6` amber, else red. A
   fabricated 5 arrives amber, and amber reads as *measured and middling* rather
   than as *absent*.

It never ran: zero callers, and no host panel ever existed. **That is luck, not
design**, and it is the reason this sweep exists rather than an incident report.

---

## 2. THE SWEEP — method, then result

Two passes, because a hand-read alone cannot claim coverage and a scanner alone
cannot judge.

**Pass 1, mechanical.** Every `.match(` / `.exec(` / `JSON.parse(` / `new
RegExp(` in the 363 files, then every ternary or `||` fallback within three lines
of it, keeping only fallbacks that are **not** in `{null, undefined, '', "", [],
{}, 0, false, true}`. Comment lines excluded — the deleted code is quoted inside
its own tombstone, so a scan that reads comments finds the defect it was written
to retire (PR §1.2, and it happened on the first run of this scan).

**Pass 2, hand-read.** Every hit from pass 1, plus every `.match(` on a variable
named for a model response (`txt`, `text`, `reply`, `raw`, `content`,
`completion`, `answer`, `result`) regardless of what followed it — because pass
1 can only see a fallback that is *written*, and a site with no fallback at all
is a different question this sweep also had to answer.

### 2.1 Result: no live instance

**Ten sites extract a value from model output. All ten handle a miss correctly,
and they do it five different ways** — which is itself the finding, because it
means the convention below is describing existing practice rather than imposing
something new.

| Site | Shape | Fallback |
|---|---|---|
| `sairncare.html:2441-2444` | `(text.match(…)||[])[1]` × 4, then `if(name&&…)` per field | **`undefined`**, and every use is guarded, so a miss leaves the field **empty**. Status line: *"review before saving, nothing here is final yet"* |
| `sairnsenior.html:2517-2520` | identical to the above, ×4 | same |
| `sairndental.html:5229` | `grab()` helper: `m?m[1].trim():''`, and `'not visible'` → `''` | **`''`** |
| `sairnroofing.html:5330` | per-field `RegExp`, `m?m[1].trim():''`, `/^unknown$/i` → `''` | **`''`**, plus *"review the values before saving"*. Also the one site that passes a **real** `pendingPhotoMediaType` rather than hardcoding jpeg |
| `sairngrounds.html:4755-4757` | `brandM?brandM[1].trim():null`, `fillM?Number(fillM[1]):null` | **`null`**, AND an explicit refusal downstream: *"No confident brand read — nothing logged automatically. Retake the photo"* |
| `sairnfreedom.html:4209` | JSON extracted from prose, then a **four-part validity test** | **refuses outright** — see §2.2 |
| `stonedesk.html:21121` | `JSON.parse`, then a secondary string extraction on failure | `[]`, and `if (questions.length === 0) return;` — **renders nothing** |
| `stonedesk.html:42786` | `m ? m[1] : 'Unknown'` on `MATCH: Yes|Partial|No` | **a NAMED THIRD VALUE** — see §2.3 |
| `sairnlaw.html:6191-6192` | two independent probes that must agree | **`null` on disagreement** — see §2.2 |
| *(deleted)* `stonedesk.html` `vmAnalyze()` | `… : 5` | **the defect.** Gone |

### 2.2 The two sites worth copying rather than merely passing

**`sairnfreedom.html:4209` is the strongest handling of this class on the
platform**, and it is stronger than the convention in §3 asks for, because it
moves the judgement into the model's own answer instead of inferring it from a
parse failure. The system prompt is
*`{"percent": <integer 0-100>, "confident": <true|false>}`* with **"Never guess a
number when confident is false"**, and the client refuses on any of four
conditions — no JSON, `confident !== true`, `percent` not a number, or out of
range:

> *"The fill level could not be determined from that photograph, so nothing was
> recorded. … There is no manual entry to fall back on — that is the binding
> decision, not a missing feature."*

**A parse miss and a model that knows it is unsure are different events, and only
the second can be asked for.** This site asks.

**`sairnlaw.html:6191-6192` is the other one, and it is not even LLM output** —
it parses a PDF's raw bytes — but the rule it states is the one this whole class
turns on:

> *"Page count: two independent probes. They must agree, or we report neither."*
> *"Disagreement between the two leaves pageCount null on purpose. A wrong page
> count on a rule with a hard page limit is worse than no page count."*

That last sentence is the class's own argument in one line.

### 2.3 The one hit that needed a judgment call — and it is NOT a defect

`stonedesk.html:42786`, the Progress Check panel:

    var m = r.match(/MATCH:\s*(Yes|Partial|No)/i);
    _pcMatchStatus = m ? m[1] : 'Unknown';

`'Unknown'` is **outside** the extracted vocabulary and it is **persisted** —
`match_status` is written into `progress_photos` on the server. That is enough to
stop and read rather than wave through. Three things clear it:

1. **The default cannot be mistaken for a verdict.** `'Unknown'` is a sentinel in
   a way `5` is not. This is the difference the whole class rests on.
2. **It is rendered as itself.** `badgeColor[p.match_status] || '#6B7280'` puts it
   in **grey**, and `escHtml(p.match_status || '?')` prints the word. A reader
   sees "Unknown", not a colour implying a judgement.
3. **Nothing aggregates it.** `git grep match_status` returns four lines: the
   schema comment, the write, and the two render lines. **No count, no filter, no
   dashboard** — so an Unknown cannot quietly shrink a "matches scope" figure,
   which is the one way an honest sentinel still does damage.

**And the model's full answer is on screen beside it** (`resultEl.textContent =
r`), so a human can always see what was actually said. **Verdict: correct
handling, and the shape to copy when an empty value is not available — a named
third value, rendered as itself, aggregated by nothing.** Recorded rather than
"fixed" so the next sweep does not re-open it.

---

## 3. THE CONVENTION, which is what this sweep produces instead of a checker

**When a value is extracted from model output, a parse miss must produce
something that cannot be mistaken for an extracted value.** Three acceptable
answers, in order of preference:

1. **Empty** — `null`, `''`, `undefined` — with every downstream use guarded, so
   the miss shows up as a blank field a human fills in. Five sites do this.
2. **A named third value, rendered as itself, aggregated by nothing** — when the
   storage column cannot hold empty. One site does this (§2.3).
3. **An outright refusal that says nothing was recorded** — when a partial answer
   would be worse than none. Two sites do this, and one of them says why in a
   sentence worth reusing: *a wrong number on a rule with a hard limit is worse
   than no number.*

**And the stronger move where the shape allows it: ask the model for its own
confidence and refuse on it, rather than inferring uncertainty from your own
regex failing.** A parse miss and a model that knows it is unsure are different
events; only the second is a measurement.

**Never:** a value inside the vocabulary of real answers. Never a midpoint. And
never a `||` inside the parse as well as outside it — that is how a genuine `0`
and a total failure end up at the same number.

---

## 4. A GATE IS NOT RECOMMENDED, AND THE ARGUMENT IS MEASURED

The obvious next step is a checker. **It should not be built, and the reason is a
number rather than a preference.**

Pass 1's scanner produced **28 candidates across 363 files. Zero are the defect.
One (§2.3) was worth a human read.** So precision against "this is the defect" is
**0/28**, and against "worth reading" is **1/28 ≈ 4%**. Twenty-three of the
twenty-eight are test-harness fakes of the form
`body: opts.body ? JSON.parse(opts.body) : null` — a fallback in a *stub*, which
is correct code and would be noise on every push forever.

**The precision cannot be fixed by tightening the regex, and that is the real
finding.** The defect signature is not *"a ternary with a non-empty default near
a `.match(`"* — it is *"the ternary's condition is the result of extracting from
a variable that holds MODEL OUTPUT, and the default is then used as if
extracted."* Deciding whether a variable holds model output is **data flow, not
pattern matching**: `txt` in `vmAnalyze` and `txt` in a dozen innocent string
helpers are the same token. A checker that cannot make that distinction is a
checker whose output somebody switches off — which this repo has recorded
happening, and which is worse than no checker because the register would then
claim the class is monitored.

**What holds the class instead, honestly stated:**

- **§3's convention, in review.** Weak on its own, and it is not on its own:
  every one of the ten existing sites already complies, so the practice is the
  norm rather than a rule nobody follows.
- **The sweep is repeatable.** The scanner lives at
  `<scratchpad>/prose_scan.py` and is deliberately **not** committed as a tool,
  because a 4%-precision scanner in `tools/` acquires an inventory entry, a
  promotion decision and a maintenance cost it cannot earn. Re-run it by hand
  when an AI feature lands.
- **The strongest control is upstream and already proven**: ask the model for a
  confidence flag and refuse on it (§2.2). That turns a parse problem into a
  protocol, and a protocol is testable.

**Cross-reference, and a boundary:** hank's 2026-09-26 sweep covers the
**unreachable-failure-path / wrong-field-always-same-answer** class
(`tools/unreachable_failure_path_scan.py`, not on disk at the time of writing).
That is a *different* defect — a branch that cannot be reached, or a field read
that always returns the same thing. **This one is a branch that IS reached and
returns a fabricated value.** They meet only in that both are invisible to
`node --check`.

---

## 5. What this sweep did NOT do

- **It did not check server-side model-output parsing beyond `api/*.js` and
  `api/_lib/*.js` shallowly.** Nested `api/**` subdirectories were not walked.
- **It did not examine prompts for whether the format they ask for is one the
  model reliably produces.** Every site above is judged on what it does when the
  format is absent, not on how often it is absent — and nobody has measured that
  rate for any of them. **That measurement is the honest next question** and it
  needs real responses, not a scan.
- **It did not check the six other SAIRN apps' AI panels for extraction sites
  that use no regex at all** — a panel that renders the model's prose straight
  through has no parse to get wrong and is out of scope by construction, but
  "renders it straight through" was assumed from the absence of a `.match(`
  rather than confirmed per panel.
- **It did not change any code.** The one instance was already deleted, in a
  separate commit, for its own reasons.

## 6. Decay

The ten-site table is a hand-read at one commit. **Any new AI panel adds a row
and nothing will prompt for it** — that is the gap a gate would have closed and
the cost of not building one, stated plainly rather than left as a gap in the
argument. Re-run the scan when an AI feature lands, and read §3 before writing
the fallback rather than after.
