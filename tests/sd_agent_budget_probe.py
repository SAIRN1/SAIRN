"""api/sd-agent-budget.test.js must REFUSE, not merely agree.

Run: python tests/sd_agent_budget_probe.py

A SUITE WRITTEN THE SAME HOUR AS THE FIX HAS NEVER REFUSED ANYTHING. This one
guards the budget on the most expensive AI endpoint on the platform -- one
request drives up to MAX_ITERATIONS model calls -- and every mutation below is
a change somebody could plausibly make while tidying, each of which restores
part of the pre-fix state:

  * the limiter leaves the loop and moves to the handler, so a ten-call request
    costs one unit. That is the accounting error the per-call design exists to
    prevent, and it is the single most likely "simplification";
  * the refusal stops stopping -- consulted, answer discarded, loop continues.
    The same call-and-ignore shape that made a cache purge look wired;
  * the check moves AFTER the model call, so a refusal still costs the call it
    was meant to prevent;
  * the partial conversation is dropped from the 429, turning a named partial
    answer back into a loss;
  * `degraded` stops travelling, so an allow that is the absence of a decision
    reads as a decision.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('api', 'sd-agent-budget.test.js')
AGENT = os.path.join('api', 'sd-agent.js')

MUTATIONS = [
    ("1. the budget leaves the loop entirely -- the pre-fix state, and a "
     "ten-call request costs nothing",
     AGENT,
     "    const rl = await checkAiRateLimit(AGENT_APP_ID, (lic && lic.license_hash) || null);",
     "    const rl = { allowed: true, degraded: false };"),

    ("2. the refusal is CONSULTED and its answer discarded -- the loop runs on, "
     "and review reads the call as protection",
     AGENT,
     "    if (rl && !rl.allowed) {",
     "    if (false) {"),

    ("3. the check moves AFTER the model call, so a refusal still costs the "
     "call it existed to prevent",
     AGENT,
     "    const rl = await checkAiRateLimit(AGENT_APP_ID, (lic && lic.license_hash) || null);\n"
     "    if (rl && rl.degraded) degraded = true;",
     "    const response0 = await callClaude(messages);\n"
     "    const rl = await checkAiRateLimit(AGENT_APP_ID, (lic && lic.license_hash) || null);\n"
     "    if (rl && rl.degraded) degraded = true;"),

    ("4. the 429 drops the partial conversation -- a named partial answer "
     "becomes a loss",
     AGENT,
     "        conversation: outcome.conversation,\n        completed_calls: outcome.completed_calls",
     "        completed_calls: outcome.completed_calls"),

    ("5. completed_calls stops being reported, so the caller cannot tell how "
     "much was done before the budget ran out",
     AGENT,
     "        completed_calls: outcome.completed_calls\n      });",
     "      });"),

    ("6. DEGRADED stops travelling -- an allow that is the absence of a "
     "decision reads as a decision",
     AGENT,
     "    if (rl && rl.degraded) degraded = true;",
     "    if (false) degraded = true;"),

    ("7. the refusal answers 200 instead of 429, which is the truncated "
     "success this whole shape exists to refuse",
     AGENT,
     "      res.status(429).json({\n        error: { code: 'AI_RATE_LIMIT',",
     "      res.status(200).json({\n        error: { code: 'AI_RATE_LIMIT',"),
]

if __name__ == '__main__':
    sys.exit(run_probe(
        SUITE, MUTATIONS,
        title='sd-agent budget -- the suite must refuse a loop that has stopped '
              'paying for its own model calls',
        # The fix is not committed yet; the worktree is at HEAD. See the
        # harness note on `stage`.
        stage=[AGENT]))
