# AI-facing fabricated facts — platform sweep, 2026-09-03

**Result: the platform is clean of the pattern, and that statement is worth
exactly as much as the scanner behind it — so the scanner was proven against
both real instances before the sweep was run.**

Tool: `tools/sairn_ai_fact_scan.py`. Run `--prove` before trusting any clean
result from it.

---

## Why this sweep happened

Two findings a day apart, in two apps, by two sessions, same class:

- **StoneDesk `[0039]`** (CC, 2026-09-02). `buildSDSystemPrompt()` put
  `'City: ' + (p.city || 'Westlake') + ', Ohio'` and
  `'Headcount: ' + (p.headcount || 1)` into the system prompt of **every** AI
  call. A shop with no city recorded was described to the model as being in
  Westlake; **a shop in Dallas that HAD filled one in was still stamped Ohio**,
  then asked for advice on pricing, labour and permitting for the wrong state.
- **SAIRNbiz `get_payroll_anomalies`** (Cody, 2026-09-03). The tool description
  told Claude, as fact, *"benefits cost is always $0 in this app"*, *"no
  enrollment UI exists to write a real value"*, *"no payroll-run history is
  persisted anywhere"*. All three were true when written and false by the time
  they shipped.

Michael named it a tracked pattern and asked for a platform-wide sweep.

## The two shapes, and why the difference matters

| | Shape A | Shape B |
|---|---|---|
| Form | a stale **assertion** baked into a literal | a fabricated **fallback** inside an interpolation |
| Example | *"no payroll-run history is persisted anywhere"* | `(p.city \|\| 'Westlake')` |
| Says | the same wrong thing to every customer | something **specific and false about this customer** |
| Found by | reading the string | nothing, if your scanner assumes an interpolation means the value is live |

**Shape B is the dangerous one**, and the first version of this scan would have
missed it entirely. It skipped any sentence containing `'+`, on the reasoning
that an interpolation meant the value came from real data. That reasoning is
exactly backwards for a fallback: the variable next to it is what makes it look
derived. The skip is gone and fallbacks are now the primary target.

**That miss is the reason `--prove` exists.** It replays both commits out of git
and asserts the scan flags what each one fixed, and that the fixed revision is
clean:

```
  ok    CAUGHT  StoneDesk 0039 fabricated city/headcount fallbacks (line 26268)
  ok    CLEAN   StoneDesk 0039 fabricated city/headcount fallbacks after its fix
  ok    CAUGHT  SAIRNbiz payroll-anomalies stale assertions (line 1077)
  ok    CLEAN   SAIRNbiz payroll-anomalies stale assertions after its fix
```

A checker that has only ever returned clean is unproven, not proven. Same
standard the 2026-08-30 raw-HTML sweep was held to, and it failed that standard
at the time — it could not locate a real instance of the bug it hunted, and said
so rather than reporting a clean result.

## Precision was tuned down from 58 hits to 16, deliberately

The first working version returned **58 Shape B hits of which roughly five were
even AI-facing** — the rest were badge classes, error strings and `innerHTML`
defaults. A checker that over-reports ten to one gets ignored, and an ignored
checker protects nothing. Two exclusions did almost all the work:

1. **A fallback that announces itself as absent is the opposite of this bug.**
   `'(name not recorded)'`, `'no diagnosis on file'`, `'unknown'`, `'Error: …'`
   all tell the model the value is missing — which is precisely what
   `'Westlake'` failed to do.
2. **A line building markup is rendering to a screen, not talking to a model.**

Both exclusions are false-negative-direction, and the `--prove` run is what
stops them being tuned until nothing is caught.

## Results — 21 app files scanned

### Shape A — 5 hits, all TRUE against current code

Every one was verified against the source rather than accepted from the string.

| App | Tool | Claim | Verdict |
|---|---|---|---|
| SAIRNbiz | `get_payroll_anomalies` | benefits are enrolled and costed; prior runs are persisted but this tool does not read them | **TRUE** — rewritten 2026-09-03, describes current behaviour |
| SAIRNbiz | `get_hiring_cost_impact` | a new hire has no enrolment on file, so the $520/month default is used | **TRUE** |
| SAIRNcash | `get_attention_digest` | *"SAIRNcash has no field anywhere that records an actual set-aside amount, only the recommended figure"* | **TRUE** — grep finds only computed `resQuarterly` / "Recommended quarterly set-aside"; no stored actual |
| SAIRNlaw | `define_legal_term` | *"This is the ONLY source of legal-term definitions available to you — you have no other"* | **TRUE** — the app registers exactly three tools (`get_matters`, `get_deadlines`, `define_legal_term`) and only the third defines anything |

### Shape B — 11 hits, 0 defects

Nine are false positives the exclusions did not reach: `localStorage` defaults
(`|| 'never'`, `|| '[]'`), UI status text (`|| 'Shape set.'`), and a FRED API
`limit || 13`. None reaches a model.

Two are real fallbacks in AI-facing text and **both are honest**:

- `sairncare.html:2254` — `(r.name || '(name not recorded)')`. Discloses.
- `sairnfreedom.html:5405` — `(p.name || 'our post')`. Generic, not a false
  specific.

**No fabricated identity, location or count survives anywhere on the platform.**
CC's StoneDesk instance was the only one of its kind and it is fixed.

## One real fabrication found, outside the AI surface, NOT fixed here

`stonedesk.html:28015`, in `sdTSExport()`:

```js
rows.push([x.emp, x.date, x.inn, x.out, x.hrs.toFixed(1), x.job || "",
           ("$" + Math.round((x.hrs || 0) * (x.rate || 28)).toLocaleString())]);
```

An employee with no pay rate on file silently becomes **$28/hour**, and the
result is written into a column headed **"Pay Est."** in a CSV a shop owner
opens in a spreadsheet. Same family as `headcount || 1` — a plausible number
standing where a missing one should be — but it lands in a document rather than
a prompt, so no AI-focused check would ever have found it. The scanner flagged
it only because an unrelated AI call sits ten lines above.

Two smaller things on the same lines: the download is hardcoded
`timesheets-pinnacle-<date>.csv` for every customer, and the labour-intelligence
AI call directly above sends the raw timesheet array, so **the $28 does not
reach the model** — the exposure is the spreadsheet only.

**Not fixed here because StoneDesk is CC's active claim** (`stonedesk — thh
material aware benchmark rates`, held at time of writing). Handed over rather
than edited underneath them.

## Honest limits of this sweep

- It sees strings it can **recognise** as AI-facing: tool descriptions, schema
  descriptions, literals opening with `You are`, and concatenation within 40
  lines of a prompt-builder marker. **A prompt assembled somewhere it cannot see
  is invisible to it.** False-negative direction, stated rather than discovered.
- It **cannot** tell a legitimate default from a fabricated one. `(role ||
  'user')` and `(city || 'Westlake')` are the same shape; only a human can
  separate them, which is why the tool prints candidates rather than verdicts.
- "Clean" here means **clean by these two shapes**, on the 21 `*.html` app files
  in this repo, at this commit. It is not a statement about `api/**`, which was
  not scanned.
