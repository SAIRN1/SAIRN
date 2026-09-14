# Case studies behind sairn-hover-auditor's method

Full narratives for the precedents cited in `SKILL.md`. SKILL.md carries the
rule each precedent produced; this file carries the story, so the file
Claude loads by default stays navigable while the reasoning behind each rule
is still on record somewhere, not compressed away. Added 2026-09-14 in three
batches: SOX/PCAOB, Knight Capital, IOLTA, Madoff, IRS first; then Trail of
Bits, Stanford's medical-record auditor, and Boeing 737 MAX/FAA ODA; then
SpaceX/NASA Commercial Crew (the contrast case to Boeing) and the
calibration industry (ISO/IEC 17025, ILAC-G24) -- all three batches once the
earlier research (NASA IV&V, SUBSAFE, WADA, seL4, Pnueli, AI Safety via
Debate, risk-limiting audits, Registered Reports) had already pushed
SKILL.md large enough that further detail belonged in its own file rather
than bloating the one every invocation loads.

## SOX / PCAOB -- public-company audit law

Sarbanes-Oxley (2002) was Congress's direct response to Enron and
WorldCom -- both frauds that auditors either missed or, in Arthur Andersen's
case, helped obscure while also selling the audited company consulting
services. Two structural fixes SOX made, both already independently present
in this role's own design before this file cited them, which is the point of
citing them: the precedent is confirmation, not new ground.

**The independence rule.** SOX Section 201 bans an auditor from providing
most non-audit consulting services to a client it audits, because Arthur
Andersen's Enron engagement proved that an auditor with a second financial
relationship to the thing it certifies cannot be trusted to certify it
honestly, no matter how good any individual auditor's intentions are. This
role's core rule -- never write, edit, or push platform code, only report --
is the same fix for the same failure mode, arrived at independently from a
different incident (Barings Bank) before this citation existed. Two
unrelated fields converging on the identical structural answer is stronger
evidence the rule is actually load-bearing, not a specific to accounting.

**PCAOB inspections.** SOX created the Public Company Accounting Oversight
Board specifically to inspect the AUDIT FIRMS, not just the companies they
audit -- because the Andersen failure was a failure of the auditor, and
nothing before PCAOB checked auditors themselves on a standing basis. That
is the precedent for chat periodically spot-verifying this role's own
findings rather than trusting the self-log's account of itself: an auditor
that is never itself audited is exactly the blind spot PCAOB exists to
close, one level up from what this role already does to the four build
agents.

**The rotation contrast, named rather than smoothed over.** SOX Section 203
requires the LEAD AUDIT PARTNER to rotate off an engagement after five
years, on a fixed, known, public calendar -- because a long, stable auditor-
client relationship is itself a risk factor: familiarity erodes skepticism
even without any deliberate lapse. This role's rotation is the structural
opposite on purpose: unpredictable rather than calendared, specifically so a
build agent can never learn the pattern and route around it. Both are real
answers to the same underlying problem (a fixed auditor's judgment eroding
over time), solved by opposite mechanisms because the two situations differ
in a way that matters: SOX's auditors are named humans whose employer
benefits from a comfortable long client relationship, and rotating them
breaks that comfort. This role has no such incentive to erode toward, so a
fixed calendar would only buy predictability with no corresponding safety
gain -- unpredictability is the version of the same fix that fits an
auditor a subject could otherwise learn to anticipate.

## Knight Capital -- $440 million lost in 45 minutes, August 1 2012

A real, well-documented software deployment failure, not a hypothetical.
Knight Capital Group deployed new trading software to 8 servers. The deploy
succeeded on 7. On the 8th, an old, dormant flag-toggling function called
"Power Peg" -- retired years earlier, left in place rather than deleted
because it "might still be needed" -- was never removed, and the new code
reused the same flag the old dormant function still responded to. When the
flag was set for the new feature, the 8th server's dead code woke up and
began executing, firing roughly 4 million erroneous orders into live markets
in 45 minutes before anyone stopped it. Knight Capital lost $440 million and
the firm effectively ceased to exist within days.

Three separate, real lessons, not one:

1. **Dead code left "dormant, might still be needed" is not inert -- it is
   a landmine with the pin still in.** It sat harmless for years specifically
   because nothing ever set that flag again, right up until something did.
   This is the exact shape items 32 and 34 already name on this platform
   (unreachable code, dormant panels) -- Knight Capital is the real dollar
   figure behind why "it's not currently called, so it's not currently a
   risk" is the wrong read. A hindsight-hunting pass should treat confirmed-
   dormant code as a standing, not a closed, question.
2. **A deploy that reports success must be verified against every real
   target, not trusted on the deploy tool's own say-so.** Knight Capital's
   deploy tooling did not fail loudly on server 8 -- it reported success, the
   same way it did on the other 7, because from the deploy tool's own
   vantage point nothing had gone wrong. The failure was only visible by
   checking what was ACTUALLY running on that one machine, which nobody did
   before markets opened. Applied here: a process pass checking whether a
   landed fix is confirmed live should mean confirmed on every clone that
   matters (all four, not just origin/main showing the commit), the same
   distinction between "the push succeeded" and "the fix is actually running
   everywhere it needs to be."
3. **Never treat "roll back to the previous version" as automatically
   safe.** This is the part most retellings drop, and it is the sharpest
   lesson for an emergency-override design specifically. Knight's own
   incident response tried to roll back -- and made it WORSE, because the
   previous version on that one server was not actually the clean baseline
   everyone assumed it was; the rollback path itself carried assumptions
   nobody had re-verified under pressure. An emergency override (this
   platform's item 86, "battleshort" -- borrowed from the term for
   deliberately bypassing a safety interlock in a genuine emergency) needs a
   target that has been verified safe, not a target that is merely familiar
   or was working recently. "Rollback" is a claim, the same as any other
   claim this role holds to "prove it, don't assume it" -- and Knight
   Capital is the case where the claim was false and the emergency response
   compounded the failure instead of stopping it.

## IOLTA three-way reconciliation -- attorney trust accounting

IOLTA (Interest on Lawyers' Trust Accounts) governs attorney client trust
accounts in most US states, and the standard practice bar associations
require -- because trust money is exactly the asset class where "the totals
match" is not sufficient proof of correctness -- is a THREE-WAY
RECONCILIATION, not a two-way one:

1. The bank statement (what the bank says is in the account).
2. The trust ledger (what the firm's own books say should be in the
   account, in total).
3. The sum of every individual client/matter's own allocation within that
   ledger (what each client is individually owed, added up).

The reason a third record is required, not optional: (1) and (2) can agree
perfectly -- the bank balance exactly matches the ledger total -- while (3)
is still wrong, because an error that moves money between two clients'
individual allocations (crediting client A's matter with money that
actually belongs to client B) changes nothing about the total. The total
balances. The account is still wrong, and a specific client is being
shortchanged while the books look clean. A bar association audit checks all
three specifically because two-way reconciliation cannot see this failure
mode at all -- it is invisible to a total-only comparison by construction,
the same shape as item 53's "fatal pairs" being invisible to single-point
analysis.

Directly relevant here because SAIRNlaw's `law_trusttx` IS attorney client
trust money, already Tier A on this platform for exactly this reason. The
real, actionable question this precedent raises for `sbThreeWayMatch` and
`api/_lib/ledger.js`: does either verify PER-CLIENT allocation sums, or only
whole-ledger totals? A three-way-match name is not the same claim as a
three-way RECONCILIATION in the IOLTA sense unless the third leg is
genuinely independent per-entity attribution, not just a third total.

This also independently confirms, from a completely different field, a
decision Michael already made on this platform: routing `sb_po`/`sb_recv`
to a different owner than the one who disburses funds is the same principle
IOLTA states directly -- the person who can move money out of an account
must not be the same person who reconciles that account, and a named,
accountable sign-off on the reconciliation is part of the control, not a
formality on top of it.

## Madoff -- the audit that looped back through its own subject

Bernie Madoff's fraud ran for decades in part because his own "independent"
verification structurally wasn't. Two real, separate lessons from how it was
eventually caught (Harry Markopolos) versus how it kept passing everyone
else's review for years:

1. **"Independent" verification that still loops back through the subject's
   own numbers is not independent.** Madoff's auditor was a three-person
   firm (one active accountant, one nearly-retired partner, one secretary)
   auditing a fund managing tens of billions of dollars -- and much of what
   got "verified" was verified against statements and records Madoff's own
   operation produced, just read by a different party. A reformatted or
   re-summarized view of the same source the subject controls is not a
   second source. Applied to item 23 (claim provenance) specifically: when
   a claim is verified, the evidence path has to actually reach something
   the subject did not produce or control -- a different system's log, a
   live-driven test against real code, a third party's record -- not merely
   a different-looking presentation of the one thing the subject already
   supplied.
2. **Scale mismatch is its own red flag, independent of any specific
   number being wrong.** What actually triggered outside scrutiny (from a
   competing firm, not a regulator) was noticing the sheer scale mismatch:
   a three-person operation could not plausibly be providing genuine
   oversight of a fund that size, regardless of what any individual number
   said. Applied here as a standing self-check, not a one-time observation:
   as the SAIRN platform grows (more apps, more Tier A resources, more
   commits per session), periodically confirm this role's own checking
   capacity -- one auditor, rotating attention across four build agents --
   is still proportionate to what it is checking, the same way a "3-person
   firm auditing something GM-sized" was visible as wrong from the outside
   without reading a single number.

## IRS -- highest-volume auditor in the United States

The IRS ran roughly 582,944 individual audits in a recent measured year,
which makes its selection methodology the largest real-world dataset for
how risk-weighted case selection actually performs over time, and it
surfaces a structural limitation risk-weighting alone cannot fix.

1. **A purely risk-weighted selection process can never measure its own
   false-negative rate, because it never looks where its own model says
   low-risk.** If audits are chosen only by a risk score, and the risk
   score is wrong about some category of low-scored return, nothing in that
   process will ever discover the error -- the very cases most likely to
   reveal the model's blind spot are the ones the model itself excludes
   from being looked at. The IRS's actual, documented answer is NOT to
   audit only high-risk returns: a portion of audits are selected by
   genuinely random, unweighted selection specifically to measure the risk
   model's own accuracy against a baseline the model had no say in
   choosing. Applied here: this role's rotation should periodically run a
   genuinely random, unweighted deep pass -- on a fixed cycle, not picked by
   the priority rules -- and track ITS finding rate against the
   weighted/prioritized passes' finding rate over time. A gap between the
   two rates over enough rounds is the actual calibration signal for
   whether the priority weighting (Tier A first, freshest commits, evidence
   margin) is finding real problems more often than chance, or just
   creating the appearance of thoroughness.
2. **Two distinct axes, not one.** The IRS's DIF (Discriminant Information
   Function) scoring compares a given return against the statistical NORM
   for that return's own category (a small business's expenses against
   other small businesses in the same category, not against a salaried
   employee's return) -- a peer-category-norm axis, structurally distinct
   from a longitudinal, single-subject axis like WADA's athlete passport.
   Applied here alongside Individual baseline tracking (an agent's own
   history), not instead of it: also check a claim against what is normal
   for that TYPE of task -- a one-line doc fix is a different reference
   class than a Tier-A rewrite, and an anomaly is "does this look unusual
   for this KIND of work," not only "does this look unusual for THIS
   agent."
3. **A real, earned operational number, not a stated-up-front guess.** The
   IRS reports an actual measured "audits resulting in no change" rate as
   one honest signal of how well-targeted its selection actually is (a high
   no-change rate on audits that did happen means the targeting missed).
   The honest, measured version of that for this role is a running tally of
   Debate outcomes specifically -- confirmed (the agent's explanation did
   not hold, finding stands) versus explained-away (a real, sufficient
   explanation surfaced, finding downgraded) -- tracked over time from the
   self-log itself, not asserted from memory. That ratio is this role's own
   calibration number, and it should be queried from `hover_log.py --tail`
   against real entries, the same standard applied to every other number in
   this file.

## Trail of Bits -- 246 findings, 23 real smart-contract audits

Trail of Bits' own published retrospective across 23 real audit engagements
and 246 real findings is one of the few genuinely quantified datasets on
what automated tooling actually catches versus what a human adversarial
reviewer catches, because the same 246 findings were classified both ways
after the fact.

**Roughly half of real findings are unlikely to ever be caught by any
automated tool, no matter how sophisticated the tool becomes.** Not "current
tools miss half" -- the classification was about the SHAPE of the finding,
not the maturity of any specific scanner: business-logic errors, subtle
economic incentive misalignments, and context-dependent reasoning failures
that require understanding what the code is FOR, not just what it does. A
finding a test suite is structurally unable to express is not a finding a
better test suite would have caught either. This is the real, quantified
grounding for treating "the tests pass" as weak evidence -- not a stylistic
preference for skepticism, a measured fact about what test-passing can and
cannot prove.

**Roughly 44% of actual cryptocurrency losses trace to access-control or
private-key-compromise failures**, measured across real, dollar-denominated
hacks -- yet Trail of Bits' own retrospective notes that traditional smart-
contract audits historically under-invest attention there relative to
financial/economic-logic review, because access-control code often reads as
"boilerplate" rather than as the load-bearing surface it actually is. A
scope mismatch between where audit attention naturally goes and where real
damage actually originates, measured rather than assumed.

**Why the full methodology still isn't adopted wholesale, said plainly.**
Trail of Bits' practice is exhaustive, maximum-depth, ONE-TIME review before
a deploy, because a deployed smart contract is immutable -- pre-launch is
the only window a defect can ever be caught in before it becomes permanent.
That specific shape (maximum depth once, before an irreversible event) is
correct for that domain and would be a mismatch applied here: SAIRN's code
is patchable, a defect found next week is still fixable next week, and the
actual analog for continuous, unscheduled, ongoing verification against
code that keeps changing is NASA IV&V or SUBSAFE, not a pre-launch audit
firm. Citing Trail of Bits' statistics is not the same as importing Trail
of Bits' cadence.

## Stanford -- two-agent clinical order auditing, deployed not theoretical

A real, currently-deployed system (not a research paper's hypothetical)
audits blood-culture ordering decisions inside live electronic medical
records using two AI agents in sequence: the first proposes a judgment, and
the second is structurally REQUIRED to either quote specific supporting
evidence from the actual patient record or explicitly reject the first
agent's reasoning -- a bare verdict with no cited evidence is not an
accepted output shape at all, and the second agent must flag its own
reasoning explicitly whenever it cannot locate support for it in the
record.

The transferable discipline, not the medical specifics: **a verdict without
a citable, specific piece of evidence behind it is not a finding, it is an
assertion wearing a finding's shape.** "Confirmed" and "clean" are
conclusions; the actual finding is the diff line, the log entry, the test
output, or the commit hash the conclusion rests on, and a report should
never require the auditor to go back and re-derive what was actually looked
at. This is the direct extension of item 23's claim-provenance standard
applied reflexively -- not only to what this role checks in others' work,
but to what this role asserts about its own.

## Boeing 737 MAX / FAA ODA -- boundary erosion, not a single bad call

The FAA's Organization Designation Authorization (ODA) program lets
manufacturers self-certify most aircraft systems under FAA oversight, to
manage the FAA's own limited engineering capacity against the volume of
certification work modern aircraft require. MCAS -- the flight-control
software implicated in the two 2018-2019 737 MAX crashes that killed 346
people -- was, correctly, kept under DIRECT FAA oversight rather than
delegated to Boeing's self-certification when the ODA program was
structured, specifically because it was flight-critical. The same reasoning
Tier A already applies on this platform: some categories of risk are too
consequential to delegate away from direct, external verification.

**What actually happened is the finding, and it is a different SHAPE of
failure than a single wrong decision.** Between late 2016 and early 2017,
oversight of MCAS was delegated away from direct FAA review incrementally,
in a sequence of individually small hand-offs, until it was functionally
close to 100% self-certified by Boeing by the time of the crashes. No single
person or meeting decided "MCAS will now be fully self-certified" -- each
individual step looked like a reasonable, bounded delegation at the moment
it was made, and the cumulative effect only became visible in hindsight, as
a pattern across many small decisions rather than inside any one of them.
This is "boundary erosion": a category correctly walled off from delegation
at the start, that drifts across that wall not through a violation of the
rule but through nobody re-checking whether the rule was still actually
being followed as circumstances (schedule pressure, resourcing, trust built
over successful prior deliveries) changed around it.

**Motive, not just honest error.** Internal Boeing communications that
surfaced after the crashes show a documented effort to avoid classifying
MCAS as a "new system" specifically because that classification would have
triggered additional certification scrutiny and cost -- the company
reviewing its own risk category had a real, structural incentive to
under-classify, not merely an ordinary chance of an honest mistake. Any
process that lets a subject assign or influence its own risk tier carries
this same incentive, structurally, regardless of that subject's individual
honesty.

**The number, cited honestly as data rather than imported as a target.**
Public reporting and subsequent Congressional investigation put Boeing's
share of MCAS's actual certification work at roughly 96% self-performed by
the time of the crashes -- real evidence of how far a delegated verification
arrangement can drift from its original design intent before independent
oversight becomes nominal rather than actual, useful here as a concrete
answer to "how bad can boundary erosion actually get" rather than as a
mechanism this role tries to replicate.

## SpaceX / NASA Commercial Crew -- the contrast case, same industry

Added specifically as a check against citing only failures: does the same
broad mechanism (risk-prioritized sampling plus full verification reserved
for the highest tier) ever go right, in the same industry Boeing's MCAS
failure came from? Yes, currently, with real caveats attached.

**The working version of the same design.** NASA's Safety Technical Review
Board (part of the Commercial Crew Program's oversight structure) runs a
documented, risk-prioritized sampling approach for routine hazard reports
and material/process verification, while reserving full, independent
verification specifically for mission-critical software and the
highest-criticality hardware -- structurally the same two-tier shape this
role already uses (a sampled fast pass, full deep-pass verification
reserved for Tier A). This is not a novel design being proposed here; it is
a live, currently-operating precedent in the same broad domain that
produced the MCAS failure.

**Why the outcome differs, and it is not because NASA samples less than
Boeing's ODA arrangement did.** The load-bearing difference is that NASA's
Safety Technical Review Board retained genuine, exercised authority over
WHAT gets sampled and how, and never allowed full independent verification
on the highest-criticality software to erode toward a self-certified
default the way FAA's ODA oversight of MCAS did between 2016 and 2017. Both
programs delegate routine verification. Only one of them kept the authority
over that delegation real rather than letting it become a formality over
time.

**The honest correction, stated because it would be dishonest not to.**
NASA's own Office of Inspector General and the Government Accountability
Office have both published real findings against this exact program:
documented review-timeliness problems (verification not keeping pace with
the contractor's own development schedule), an internally undefined
risk-tolerance threshold that has not been precisely pinned down even by
NASA's own account, and genuine schedule pressure -- the commercial partner
controls the pace of development, and NASA's review process has to keep up
with that pace rather than set it independently. This case is evidence that
a well-designed two-tier verification structure CAN hold under real
operational pressure over years, not evidence that it has been tested by an
actual failure and survived one the way, for instance, a near-miss caught
in time would be. The distinction matters and should not be collapsed into
a simpler "it worked" claim.

## Calibration industry -- ISO/IEC 17025 and ILAC-G24

The international standard governing how measuring-instrument calibration
labs operate (ISO/IEC 17025) and its companion guidance on setting
re-calibration intervals (ILAC-G24) are a genuinely mature, decades-refined
discipline for exactly the problem this role also has: how often should a
given thing be re-checked, and how should degrading performance be
reported honestly.

**AS-FOUND versus AS-LEFT, and why conflating them is a documented,
recurring failure mode in the calibration industry itself.** Every proper
calibration report states the instrument's AS-FOUND condition -- how far it
had actually drifted from spec before anyone touched it -- as a distinct,
preserved figure from its AS-LEFT condition after any adjustment was made.
ILAC-G24 and ISO/IEC 17025 both exist partly because many providers,
historically, reported only the as-left (post-adjustment, looks-fine) state
and never recorded how bad the as-found state actually was -- which erases
the only evidence that would let anyone later ask "how much was this
actually drifting, and for how long, before someone caught it."

**The staircase method (ILAC-G24) -- a real, specific algorithm for
setting an individual interval from individual history, not a general
instinct.** Rather than a fixed re-calibration interval applied to every
instrument of a given type, the staircase method adjusts each instrument's
OWN interval from its own track record: three consecutive verifications
that come back within tolerance extend the interval before the next
verification by approximately 25%, up to a cap of twice the original
baseline interval; a verification that comes back marginal or outside
tolerance shortens the interval back down. An instrument that has
repeatedly proven stable earns less frequent checking, within a bounded
ceiling; one that shows any sign of drift is checked again sooner. This is
a real, decades-tested, bounded algorithm for exactly the shape WADA's
biological-passport principle gestures at more generally -- individual
history should inform individual check frequency -- with an actual formula
behind it rather than only a direction to "check occasionally."

**Severity by ratio, not by a pass/fail line.** A calibration standard
never reports an out-of-tolerance instrument as a single binary
fail -- 0.1% past tolerance and 40% past tolerance are both "failed" under
a binary read, and that collapse discards exactly the information that
decides how urgently it matters. The report states how far past tolerance
the reading actually was. Applied to a drift or statistical finding here:
state the ratio -- how far past an agent's own baseline, how far past a
stated bound -- rather than reducing it to a single severity word the way
a pass/fail line would.
