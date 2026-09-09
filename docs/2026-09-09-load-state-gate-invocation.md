# Load-state gates: the invocation decision

**Written 2026-09-09 (Fourth) for index row "Load-state gates: every per-licence
reference table now has a read-only check that its live content matches the
seed".** That row's own words are *"Needs a decision on invocation, not more
tooling"*, and this document exists to make that decision answerable in one
read rather than by re-deriving the tooling.

Everything below was checked against the files today, not carried from the row.

---

## 1. What actually exists

`tools/sairn_load_state_check.py` — one tool, four apps, read-only.

| `--app` | Tables checked | Licence key from |
|---|---|---|
| `sairnlaw` (default) | deadline rules + calendars, read from every `sql/sairnlaw_deadline_*.json` | `SAIRNLAW_LICENSE_KEY` |
| `sairncare` | `alf_compliance_rules`, `alf_payer_rules` | `SAIRNCARE_LICENSE_KEY` |
| `sairndental` | `dnt_cred_rules` | `SAIRNDENTAL_LICENSE_KEY` |
| `sairnroofing` | `rf_cert_rules`, `rf_contingency_rules` | `SAIRNROOFING_LICENSE_KEY` |

It reads the seed files **at run time**, which is the whole reason the generated
SQL gates were retired: a generated gate that must be regenerated after every
seed edit reproduces, inside the gate, the exact silent failure the gate exists
to catch. `tools/sairn_build_load_gates.py` still exists and its own header says
SUPERSEDED — DO NOT BUILD ON THIS.

**One correction to the index row itself.** It names
`tools/deadline_load_state_check.py` as canonical for SAIRNlaw. **There is no
such file.** The canonical tool is `tools/sairn_load_state_check.py` — the same
one, for all four apps. The row is right about the decision and wrong about the
filename; a session following it would go looking for a tool that does not
exist.

## 2. What invokes it today — exactly one thing, and it is narrower than it sounds

`tools/sairn_push_gate_hook.py`, CHECK 1. It runs on a `git push`, looks at the
commits **actually being sent**, and only acts if one of them touches a path
matching the seed patterns:

    sql/sairnlaw_deadline_*.json
    sql/sairncare_(compliance|payer_rules)_seed*.json
    sql/sairndental_credentials_seed*.json
    sql/sairnroofing_(certifications|contingency)_seed*.json

If no outgoing commit touches one of those, **the check does not run at all**,
and correctly so — it costs nothing on the overwhelming majority of pushes.

**So the coverage today is precisely: "a seed change is not allowed to ship
while the live licence still holds the old value."** That is the shape of the
LAW-PINNACLE-2026 incident that motivated the whole thing, and it is genuinely
closed.

## 3. What is therefore still uncovered — the actual gap

Every route to drift that does **not** pass through a seed-file push:

1. **A loader that half-completed.** The seed and the code agree; the licence
   holds part of the load. Nothing pushes, so nothing checks.
2. **A licence provisioned later from a stale load** — a new customer keyed off
   a copy that was current when it was made and is not now.
3. **A hand edit in the Supabase SQL editor.** The only path that can change
   live reference content with no repo event at all.
4. **Drift that predates the gate** (it went in 2026-08-29). Nothing has ever
   swept the four licences from a cold start.
5. **A clone with no licence key.** The hook allows-with-a-loud-note when it
   cannot reach a verdict. That is documented as *not a pass*, but it is still
   an allow, and it depends on a human reading the note.

Item 5 is the one worth staring at: the gate's coverage is a function of which
environment variables happen to be set in whichever clone did the push.

## 4. Two things the row lists that are NOT invocation problems

- **`sc_anesthesia_base_units` has no gate because it has no seed file in the
  repo.** This is a source-of-truth gap. No scheduling decision touches it; the
  fix is to export the live table into a seed file, and that is a separate,
  small piece of work.
- **`version` is uniformly `1` and carries no signal.** The gates compare
  content subtractively and work without it. Leaving it alone is correct;
  making it meaningful is a different project.

## 5. The options, with their real costs

**(a) GitHub Actions on a schedule.** Actions is already live in this repo
(`.github/workflows/codeql.yml`). A daily matrix over the four apps is perhaps
thirty lines. **The cost is the reason not to do it:** it requires putting four
real customer licence keys into GitHub repository secrets. That is a new place
secrets live, and this project's standing rule is that a secret only ever goes
into its real destination.

**(b) A Vercel cron endpoint.** This is the only place the licence keys
*already are*. `vercel.json` already carries two crons
(`/api/sairndental/send-reminder`, `/api/alf-alerts`), and
`api/sairndental/send-reminder.js` already shows the house pattern: refuse
unless `Authorization` equals `Bearer ${CRON_SECRET}`, checked first. Adding a
third path introduces **no new secret anywhere**. The cost is that the checker
is Python and the runtime is JS, so the comparison logic has to be reimplemented
or the endpoint has to call the same PostgREST reads directly.

**(c) A session-start hook in each clone**, alongside the existing claim hook.
Free, no new secrets, and it runs in the environment where the keys are already
configured. But it only fires when somebody is working, adds network latency to
every session start, and a check nobody reads at 2am is close to no check.

**(d) Leave it push-triggered and accept the gap**, with the gap written down
rather than implied.

## 6. Recommendation

**(b), scoped to one endpoint and one alert, and (d) explicitly until then.**

The deciding argument is not scheduling — it is that (b) is the only option
where the credentials do not move. Every other option either copies four
customer licence keys somewhere new, or depends on a human being at a keyboard.

Concretely: one `/api/load-state-check` behind `CRON_SECRET`, daily, that runs
the four comparisons and is **loud only on drift**. A daily "all clean" email
becomes background noise inside a week and then a drift notice looks like it.

**Two things to decide before anyone builds it**, because they are judgment, not
implementation:

1. **Where does the alarm go?** An endpoint that finds drift and logs it to
   Vercel's runtime logs has moved the problem, not solved it. It needs a
   destination somebody actually reads.
2. **Does it gate anything, or only report?** Reporting only is the safe
   start, and it matches how `run_all_tests` was wired in after a push. A gate
   that can refuse a customer request over a reference-table mismatch is a much
   bigger decision and should not be bundled with this one.

Until (b) exists, the honest statement of coverage is: **a seed change cannot
ship unloaded; a quiet licence is never checked.** That belongs in the index row
verbatim, because the row currently reads as though the class is closed.
