"""tests/run_tiered_pricing_sabotage_probe.py -- does the tiered-pricing suite
REFUSE a wrong commission, or is it green over whatever the table says?

    python tests/run_tiered_pricing_sabotage_probe.py

REQUIREMENT: tests/tiered_pricing_commission.js must go RED for each defect
planted below.

── WHY THIS ONE, RATHER THAN TRUSTING A GREEN SUITE ───────────────────────
Every failure here is a WRONG NUMBER THAT LOOKS RIGHT. None of them throws,
none of them logs, and every one of them produces a quote and a commission
figure a rep will read and act on. That is the category a passing test suite
is least able to reassure anybody about, because the suite was written by the
same session that wrote the code.

── THE TWO WORTH READING BEFORE THE REST ──────────────────────────────────
MUTATION 3 makes an unusable agent override -- an empty settings field, which
is what `Number('')` turns into 0 -- silently become a 0% commission. A rep
paid nothing because somebody tabbed through a form looks identical to a rep
deliberately on 0%, and the person it happens to is the last to find out.

MUTATION 6 removes the snapshot so the history row recomputes the rate from
today's table. Nothing is wrong on the day it ships. It goes wrong the first
time anybody edits a rate, retroactively, across every quote ever written, and
there is then no copy of what the rep was actually told.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                      # noqa: E402

SUITE = os.path.join('tests', 'tiered_pricing_commission.js')
SRC = 'stonedesk.html'

MUTATIONS = [
    ("1. THE LADDER INVERTS: distributor -- the thinnest margin on the board "
     "at 22% off retail -- is paid MORE commission than a full-price retail "
     "kitchen. Nothing errors; the rep's incentive simply stops matching the "
     "shop's, and the quotes that pay worst become the ones worth chasing",
     SRC,
     "  distributor: { label: 'Distributor', mult: 0.78, commission: 0.015,",
     "  distributor: { label: 'Distributor', mult: 0.78, commission: 0.075,"),

    ("2. AN UNKNOWN TIER DEFAULTS TO RETAIL instead of being reported. A "
     "quote carrying a tier key nobody recognises is quietly paid at the "
     "retail rate, which on a distributor deal is five times what was agreed",
     SRC,
     "  if(!t) return { rate:null, source:'unknown tier \"'+String(tierKey)+'\"', ok:false };",
     "  if(!t) t = TIERS.retail;"),

    ("3. AN UNUSABLE AGENT OVERRIDE BECOMES 0%: the validation is dropped and "
     "Number('') -- an empty settings field -- is honoured as a deliberate "
     "zero commission. The rep paid nothing looks exactly like a rep on 0% on "
     "purpose, and is the last person to find out",
     SRC,
     "    if(isFinite(n) && n>=0 && n<=0.5){",
     "    if(true){ n = Number(over);"),

    ("4. THE MONEY GOES BACK TO FLOATS: the amount is computed in dollars "
     "rather than whole cents, so a perfectly ordinary 3% commission lands on "
     "129.63999999999999 -- a number that cannot represent the amount it "
     "claims to be, on something somebody is paid",
     SRC,
     "  return Math.round(cents*rate);\n}",
     "  return (cents*rate)/100;\n}"),

    ("5. A TIER KEY IS RENAMED AWAY: `contractor` becomes `trade_contractor`, "
     "so every quote already on disk carrying the old key resolves to "
     "undefined. It throws, or it gets defended with a `|| 1.0` that reprices "
     "a contractor's quote at full retail",
     SRC,
     "  contractor:  { label: 'Contractor',",
     "  trade_contractor:  { label: 'Contractor',"),

    ("6. THE SNAPSHOT IS DROPPED: the saved quote stops recording the rate it "
     "was written at. Nothing is wrong on the day it ships -- it goes wrong "
     "the first time anybody edits a rate, retroactively, across every quote "
     "ever written, with no copy of what the rep was actually told",
     SRC,
     "    commissionRate: (lastCalc.agentId ? lastCalc.commissionRate : null),\n    commissionCents: (lastCalc.agentId ? lastCalc.commissionCents : null),",
     ""),

    ("7. setTier STOPS REFUSING an unknown key, so currentTier can be set to "
     "something TIERS cannot resolve and every later read of tier.mult is a "
     "throw or a silent reprice",
     SRC,
     "  if (!TIERS[t]) { console.warn('setTier: unknown tier \"' + t + '\" ignored'); return; }",
     ""),

    ("8. THE SECOND TIER LIST COMES BACK: the AI-quote panel hardcodes four "
     "tiers again, so the two B2B levels are silently unpriceable on that "
     "path and nothing anywhere says so",
     SRC,
     '<select id="aiq-tier" style="width:100%;padding:9px 12px;border:1px solid var(--border);border-radius:8px;margin-top:4px;background:var(--bg);color:var(--text);font-size:13px"></select>',
     '<select id="aiq-tier" style="width:100%;padding:9px 12px;border:1px solid var(--border);border-radius:8px;margin-top:4px;background:var(--bg);color:var(--text);font-size:13px"><option value="retail">Retail</option><option value="contractor">Contractor</option><option value="builder">Builder</option><option value="designer">Designer</option></select>'),

    ("9. A TIER IS PRICED BUT UNREACHABLE: `distributor` keeps its rate and "
     "loses its pill, so the app has a wholesale price nobody can select and "
     "the sales team goes on quoting builder rates to distributors",
     SRC,
     "              <div class=\"tier-pill\" onclick=\"setTier('distributor',this)\">Distributor</div>\n",
     ""),
]

if __name__ == '__main__':
    sys.exit(run_probe(
        SUITE, MUTATIONS,
        title=('StoneDesk B2B pricing: the tier ladder and the commission it '
               'carries must move together, resolve to a rate that says where '
               'it came from, compute in whole cents, and never silently pay '
               '0% or reprice a quote already written'),
        stage=(SUITE, SRC)))
