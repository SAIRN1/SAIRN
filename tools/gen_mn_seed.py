"""Build sql/sairnlaw_deadline_seed_minnesota.json.

Every quote below was read VERBATIM on 2026-08-26 from the Minnesota Rules of
Civil Procedure as published free and in full by the Office of the Revisor of
Statutes, which serves the RULES and the STATUTES from the same official site --
the first jurisdiction seeded where both bodies of law come from one free
official publisher, and all of it on a plain curl.

  revisor.mn.gov/court_rules/cp/id/6/    Rule 6   (Time)
  revisor.mn.gov/court_rules/cp/id/12/   Rule 12  (answer)
  revisor.mn.gov/court_rules/cp/id/33/   Rule 33  (interrogatories)
  revisor.mn.gov/court_rules/cp/id/34/   Rule 34  (production)
  revisor.mn.gov/court_rules/cp/id/36/   Rule 36  (admissions)
  revisor.mn.gov/statutes/cite/645.44    645.44 subd. 5 (holidays)

ACCESS NOTE: mncourts.gov returns 403 to plain fetches. NOTHING here needs it --
recorded only so a future session does not read that 403 as a blocker the way a
mass.gov or tncourts.gov 403 would be.
"""
import json

CP = "https://www.revisor.mn.gov/court_rules/cp/id/"
URL = {"6": CP + "6/", "12": CP + "12/", "33": CP + "33/", "34": CP + "34/", "36": CP + "36/"}
RETRIEVED = "2026-08-26"

# Per-rule currency from each rule's own printed amendment line. Rules 33, 34
# and 36 print no dated amendment line of their own on the Revisor page, so they
# take the date of the most recent general restyling that reached them --
# recorded as a DISCLOSED WEAKNESS on each row rather than presented as a real
# per-rule date. Rule 6.01 and Rule 12.01 both print "(Amended effective January
# 1, 2020.)" and are real.
EFF = {"6": "2020-01-01", "12": "2020-01-01",
       "33": "2020-01-01", "34": "2020-01-01", "36": "2020-01-01"}

WEAK_EFF = (
    " EFFECTIVE_FROM IS THE 2020 RESTYLING DATE, NOT A PER-RULE AMENDMENT DATE, and that is a disclosed "
    "weakness on this row. Rule 6.01 and Rule 12.01 each print their own \"(Amended effective January 1, "
    "2020.)\" line; this rule does not print a dated amendment line of its own on the Revisor page, so the "
    "restyling date is used. The consequence is bounded: a trigger before 2020-01-01 refuses when it might "
    "have computed, which is the SAFE direction, and no trigger after it is affected."
)

EXT = {
    "standard": "mn_rcp_6_01_e",
    "note": (
        "Amount and unit come from the standard, not this row. Minn. R. Civ. P. 6.01(e) adds THREE days for "
        "service by United States Mail, and ONE day for service by ANY MEANS OTHER THAN U.S. Mail "
        "accomplished after 5:00 p.m. local Minnesota time on the day of service -- otherwise nothing. "
        "THE SECOND LIMB IS A NEGATIVE CONDITION, NOT AN ALLOWLIST: it reaches facsimile, e-mail, the "
        "e-filing system, personal delivery and anything else, so applies_when is deliberately ABSENT on "
        "this row rather than listing methods. Listing them would narrow a rule that names none. Supply "
        "service_time as HH:MM in 24-hour form for any non-mail method; without it the engine refuses the "
        "extension visibly rather than choosing between 0 and 1. 17:00 exactly is NOT \"after 5:00 p.m.\"."
    ),
}

NO_EXT_SUMMONS = (
    " NO SERVICE EXTENSION. R. 6.01(e) extends a period run after \"the service of a notice or other "
    "document upon the party\"; the summons is served under Rule 4, not Rule 5. Same scope route as West "
    "Virginia, North Carolina, Washington, New Jersey, Virginia, Massachusetts and Missouri."
)

Q_12_01 = ("Defendant shall serve an answer within 21 days after service of the summons upon that defendant "
           "unless the court directs otherwise pursuant to Rule 4.043. A party served with a pleading stating "
           "a cross-claim against that party shall serve an answer thereto within 21 days after the service "
           "upon that party. The plaintiff shall serve a reply to a counterclaim in the answer within 21 days "
           "after service of the answer or, if a reply is ordered by the court, within 21 days after service "
           "of the order, unless the order otherwise directs. The service of a motion permitted under this "
           "rule alters these periods of time as follows unless a different time is fixed by order of the "
           "court: (1) If the court denies the motion or postpones its disposition until the trial on the "
           "merits, the responsive pleading shall be served within 14 days after service of notice of the "
           "court's action; (2) if the court grants a motion for a more definite statement, the responsive "
           "pleading shall be served within 14 days after the service of the more definite statement.")

Q_33_01 = ("The party upon whom the interrogatories have been served shall serve separate written answers or "
           "objections to each interrogatory within 30 days after service of the interrogatories, except that "
           "a defendant may serve answers or objections within 45 days after service of summons and complaint "
           "upon that defendant. The court, on motion and notice and for good cause shown, may enlarge or "
           "shorten the time.")

Q_34_02 = ("Time to Respond. The party upon whom the request is served must serve a written response within 30 "
           "days after the party is served (or deemed served pursuant to Rule 26.04(b)). The court may allow "
           "a shorter or longer time.")

Q_36_01 = ("The matter is admitted unless within 30 days after service of the request, or within such shorter "
           "or longer time as the court may allow, the party to whom the request is directed serves upon the "
           "party requesting the admission a written answer or objection addressed to the matter, signed by "
           "the party or by the party's attorney; but, unless the court shortens the time, a defendant shall "
           "not be required to serve answers or objections before the expiration of 45 days after service of "
           "the summons and complaint upon that defendant.")


def rule(rid, label, trigger, count, cite, quote, note, eff_key, ext=None):
    r = {
        "rule_id": rid,
        "jurisdiction": "mn",
        "domain": "civil-litigation",
        "label": label,
        "trigger_event": trigger,
        "count": {"value": count, "unit": "calendar_days", "direction": "forward"},
        "computation": "mn_rcp_6_01",
        "authority": {"citation": cite, "url": URL[eff_key], "quote": quote, "note": note,
                      "retrieved_at": RETRIEVED},
        "effective_from": EFF[eff_key],
        "effective_to": None, "version": 1, "supersedes": None,
    }
    if ext:
        r["service_extension"] = ext
    return r


def later_of(rid, label, tid, ev_a, n_a, lab_a, ev_b, n_b, lab_b, cite, quote, note, eff_key):
    return {
        "rule_id": rid, "jurisdiction": "mn", "domain": "civil-litigation", "label": label,
        "trigger_event": {
            "id": tid, "resolve_periods": "later_of",
            "limbs": [
                {"event": ev_a, "count": {"value": n_a, "unit": "calendar_days"}, "label": lab_a},
                {"event": ev_b, "count": {"value": n_b, "unit": "calendar_days"}, "label": lab_b},
            ],
        },
        "computation": "mn_rcp_6_01",
        "authority": {"citation": cite, "url": URL[eff_key], "quote": quote, "note": note,
                      "retrieved_at": RETRIEVED},
        "effective_from": EFF[eff_key],
        "effective_to": None, "version": 1, "supersedes": None,
    }


rules = [
    rule("mn-r-12-01-answer-to-summons",
         "Answer after service of the summons (Minnesota)",
         "service_of_summons", 21,
         "Minn. R. Civ. P. 12.01", Q_12_01,
         "TWENTY-ONE DAYS, matching the federal 21 and Virginia's 21 rather than Massachusetts' and "
         "Washington's 20 or Missouri's 30. Read from the rule. "
         "MINNESOTA MEASURES FROM SERVICE OF THE SUMMONS ALONE -- \"within 21 days after service of the "
         "SUMMONS upon that defendant\" -- where most seeded states say \"summons and complaint\". Minnesota "
         "commences an action by service rather than by filing, so the trigger is named for the summons and "
         "not widened to a phrase the rule does not use. "
         "\"UNLESS THE COURT DIRECTS OTHERWISE PURSUANT TO RULE 4.043\" -- an order the engine cannot see "
         "displaces this row." + NO_EXT_SUMMONS,
         "12"),

    rule("mn-r-12-01-answer-to-crossclaim",
         "Answer to a cross-claim (Minnesota)",
         "service_of_pleading_stating_crossclaim", 21,
         "Minn. R. Civ. P. 12.01", Q_12_01,
         "TWENTY-ONE DAYS AFTER SERVICE, and unlike the answer to the summons this one IS served under Rule "
         "5 on a party already in the case, so THE EXTENSION APPLIES. Splitting one sentence of one rule into "
         "two rows on that basis is the same treatment West Virginia's 12(a)(1)(A)/(B) pair and "
         "Massachusetts' R. 12(a)(1) got. "
         "Note this is the opposite of MISSOURI, whose R. 55.25(b) measures a cross-claim answer from the "
         "cross-claim being FILED and therefore takes no extension at all. Two neighbouring rules, same "
         "period, opposite result on the extension.",
         "12", EXT),

    rule("mn-r-12-01-reply-to-counterclaim",
         "Reply to a counterclaim (Minnesota)",
         "service_of_answer_containing_counterclaim", 21,
         "Minn. R. Civ. P. 12.01", Q_12_01,
         "TWENTY-ONE DAYS AFTER SERVICE OF THE ANSWER containing the counterclaim -- not after the "
         "counterclaim is filed, and not after any order. The rule provides a separate 21 days from service "
         "of an ORDER where a reply is ordered by the court; that is its own row. "
         "SERVICE EXTENSION APPLIES: the answer is served under Rule 5.",
         "12", EXT),

    rule("mn-r-12-01-reply-ordered-by-court",
         "Reply ordered by the court (Minnesota)",
         "service_of_order_requiring_reply", 21,
         "Minn. R. Civ. P. 12.01", Q_12_01,
         "TWENTY-ONE DAYS AFTER SERVICE OF THE ORDER -- and note it runs from SERVICE of the order, not from "
         "its ENTRY. Missouri's equivalent (R. 55.25(b)) runs from ENTRY and takes no extension; Minnesota's "
         "runs from service and does. The distinction is the whole reason these are separate rows across the "
         "two states, and it is recorded rather than flattened. "
         "\"UNLESS THE ORDER OTHERWISE DIRECTS\" -- an order the engine cannot see displaces this row.",
         "12", EXT),

    rule("mn-r-12-01-responsive-pleading-after-motion-denied",
         "Responsive pleading after the court denies a Rule 12 motion or postpones it to trial (Minnesota)",
         "service_of_notice_of_court_action_denying_or_postponing_motion", 14,
         "Minn. R. Civ. P. 12.01", Q_12_01,
         "FOURTEEN DAYS, AND IT RUNS FROM SERVICE OF NOTICE of the court's action. That wording matters: "
         "Missouri's and Massachusetts' equivalents run from NOTICE of the court's action without the word "
         "\"service\", which is why those rows take no extension -- notice of a court's own act is not "
         "service of a paper by a party. Minnesota says \"within 14 days after SERVICE OF NOTICE of the "
         "court's action\", so a paper is served and THE EXTENSION APPLIES. Read from the rule, not carried. "
         "FOURTEEN DAYS IS NOT SHORT ENOUGH TO MATTER ANYWAY -- R. 6.01(a)(1) counts every intermediate day "
         "regardless of length, and 6.01(a)(2)'s sub-7-day exclusion is opt-in and not granted here.",
         "12", EXT),

    rule("mn-r-12-01-responsive-pleading-after-more-definite-statement",
         "Responsive pleading after service of a more definite statement (Minnesota)",
         "service_of_more_definite_statement", 14,
         "Minn. R. Civ. P. 12.01", Q_12_01,
         "FOURTEEN DAYS AFTER SERVICE of the more definite statement, which is a paper served by a party "
         "under Rule 5, so the extension applies. Its sibling limb runs from service of NOTICE of the "
         "court's action; both take the extension here, which is NOT true in Missouri or Massachusetts, "
         "where the two limbs diverge. Same sentence, three states, three answers.",
         "12", EXT),

    rule("mn-r-33-01b-interrogatory-answers",
         "Answers and objections to interrogatories (Minnesota)",
         "service_of_interrogatories", 30,
         "Minn. R. Civ. P. 33.01(b)", Q_33_01,
         "THIRTY DAYS. This row is the PLAIN limb, for a party who is not a defendant taking the 45-day "
         "floor -- see the -defendant-later-of-periods row. "
         "SERVICE EXTENSION APPLIES: interrogatories are served under Rule 5. "
         "\"THE COURT ... MAY ENLARGE OR SHORTEN THE TIME\" -- an order the engine cannot see." + WEAK_EFF,
         "33", EXT),

    later_of("mn-r-33-01b-interrogatory-answers-defendant-later-of-periods",
             "Answers and objections to interrogatories served on a defendant (Minnesota)",
             "interrogatories_on_defendant",
             "service_of_interrogatories_on_defendant", 30, "30 days after service of the interrogatories",
             "service_of_summons_and_complaint_for_interrogatories", 45,
             "45 days after service of the summons and complaint on that defendant",
             "Minn. R. Civ. P. 33.01(b)", Q_33_01,
             "A DEFENDANT GETS THE LATER OF THE TWO PERIODS. \"except that a defendant may serve answers or "
             "objections within 45 days after service of summons and complaint\" is a floor under the 30-day "
             "period, not a replacement for it. "
             "30/45 IS THE SAME PAIR GEORGIA, MASSACHUSETTS AND MISSOURI USE for two of their three discovery "
             "devices -- and Georgia's is the pair that was once encoded as an ordinary later_of and shipped "
             "a date FIFTEEN DAYS EARLY, which is why resolve_periods exists and why this row uses it. "
             "BOTH LIMBS RUN FROM CALLER-SUPPLIED DATES, not from a computed one, so Minnesota does NOT hit "
             "the Maryland chained-floor gap where Md. R. 2-424's floor runs from the date another rule makes "
             "a pleading due. "
             "NO SERVICE EXTENSION ON THIS ROW. The plain limb carries one and this one deliberately does "
             "not: no seeded rule combines resolve_periods with an extension, the engine has never been "
             "exercised on that combination, and inventing the interaction -- does it lengthen one limb or "
             "both, before or after the later-of resolves -- would be guessing at an order no rule text "
             "settles. Compute the plain limb and compare by hand." + WEAK_EFF,
             "33"),

    rule("mn-r-34-02c1-production-response",
         "Written response to a request for production (Minnesota)",
         "service_of_request_for_production", 30,
         "Minn. R. Civ. P. 34.02(c)(1)", Q_34_02,
         "THIRTY DAYS, AND MINNESOTA GRANTS NO DEFENDANT FLOOR ON PRODUCTION. That is the finding on this "
         "row and the reason it is a plain single-trigger row with no later_of sibling: R. 33.01(b) and "
         "R. 36.01 both give a defendant 45 days from service of the summons and complaint, and R. 34.02 "
         "gives none. Massachusetts has the identical 2-of-3 asymmetry (its R. 33 is the one without a "
         "floor); Missouri and Wisconsin have a floor on all three. A later_of row here would invent a "
         "period the rule does not grant. "
         "\"OR DEEMED SERVED PURSUANT TO RULE 26.04(b)\" IS NOT MODELLED. The rule measures from when the "
         "party \"is served (or deemed served pursuant to Rule 26.04(b))\", and Rule 26.04(b) has not been "
         "read. The caller supplies an actual service date; if a deemed-service date would be LATER, this "
         "row reports EARLY, which is the safe direction. Read 26.04(b) before relying on this row for a "
         "matter where service was constructive. "
         "SERVICE EXTENSION APPLIES: the request is served under Rule 5." + WEAK_EFF,
         "34", EXT),

    rule("mn-r-36-01-admission-response",
         "Answer or objection to a request for admission (Minnesota — unanswered matters are ADMITTED)",
         "service_of_request_for_admission", 30,
         "Minn. R. Civ. P. 36.01", Q_36_01,
         "THIRTY DAYS, AND SILENCE ADMITS -- \"The matter is admitted unless within 30 days after service of "
         "the request ... the party ... serves ... a written answer or objection\". Same self-executing "
         "structure as Ohio Civ.R. 36(A)(1), Va. R. 4:11(a), Mass. R. 36(a) and Mo. R. 59.01, and the reason "
         "this label says so out loud. This row is the PLAIN limb. "
         "SERVICE EXTENSION APPLIES: the request is served under Rule 5. "
         "\"OR WITHIN SUCH SHORTER OR LONGER TIME AS THE COURT MAY ALLOW\" -- an order the engine cannot "
         "see, and here it can make the period SHORTER." + WEAK_EFF,
         "36", EXT),

    later_of("mn-r-36-01-admission-response-defendant-later-of-periods",
             "Answer or objection to a request for admission served on a defendant (Minnesota)",
             "admission_request_on_defendant",
             "service_of_request_for_admission_on_defendant", 30, "30 days after service of the request",
             "service_of_summons_and_complaint_for_admission", 45,
             "45 days after service of the summons and complaint on that defendant",
             "Minn. R. Civ. P. 36.01", Q_36_01,
             "A DEFENDANT GETS THE LATER OF THE TWO PERIODS, on the same 30/45 pair as interrogatories -- and "
             "unlike MISSOURI, whose admissions floor is SIXTY where its other two are 45. Minnesota is "
             "internally consistent on the two devices that have a floor; Missouri is not. Each number was "
             "read from its own rule. "
             "R. 36.01 PHRASES IT AS A PROHIBITION -- \"a defendant shall NOT BE REQUIRED to serve answers or "
             "objections before the expiration of 45 days\" -- where R. 33.01(b) phrases it as a permission "
             "(\"a defendant MAY serve\"). Same arithmetic, opposite grammar, recorded rather than flattened. "
             "\"UNLESS THE COURT SHORTENS THE TIME\" QUALIFIES THE 45-DAY FLOOR SPECIFICALLY, not the 30-day "
             "period. THE STAKES ARE HIGHER HERE THAN ON THE INTERROGATORY SIBLING because silence ADMITS. "
             "NO SERVICE EXTENSION ON THIS ROW, for the reason given on the interrogatory sibling." + WEAK_EFF,
             "36"),
]

doc = {
    "_readme": [
        "MINNESOTA CIVIL DEADLINE RULES -- 11 rows, Rules 12.01, 33.01, 34.02 and 36.01.",
        "",
        "== SOURCE ==============================================================",
        "Read verbatim on 2026-08-26 from the Minnesota Rules of Civil Procedure,",
        "published free and in full by the OFFICE OF THE REVISOR OF STATUTES, which",
        "serves the RULES and the STATUTES from the same official site -- the first",
        "jurisdiction seeded where both come from one free official publisher, and",
        "all of it on a plain curl. No paywall, no challenge, no terms gate.",
        "",
        "mncourts.gov returns 403 to plain fetches. NOTHING here needs it; recorded",
        "only so a future session does not read that 403 as a blocker.",
        "",
        "== DAYS ARE DAYS, AND THE EXCLUSION IS OPT-IN PER RULE =================",
        "R. 6.01(a)(1) counts EVERY intermediate day. R. 6.01(a)(2) allows a",
        "sub-7-day exclusion ONLY IF a rule expressly provides one. So the",
        "computation standard declares NO short_period_exclusion_days at all --",
        "not 7 (NJ/NC/WA/MA/MO), not 11 (TN/AZ/WI). Setting 7 by neighbour analogy",
        "would push every short Minnesota deadline LATER than the rule provides.",
        "No seeded row here expressly provides the exclusion.",
        "",
        "== BACKWARD IS EXPRESSLY DEFINED ======================================",
        "R. 6.01(c): the next day is found \"backward when measured before an",
        "event\". Real, unlike NJ/NC/WA/MA/MO/WI. No backward row is seeded even so.",
        "",
        "== THE EXTENSION IS A NEGATIVE CONDITION, NOT AN ALLOWLIST =============",
        "R. 6.01(e): THREE days for U.S. Mail; ONE day for ANY MEANS OTHER THAN",
        "U.S. Mail accomplished after 5:00 p.m. So no row carries applies_when --",
        "listing methods would narrow a rule that names none. 17:00 exactly is NOT",
        "\"after 5:00 p.m.\" (the clean Virginia boundary, unlike Wisconsin's",
        "ambiguous \"between 5 p.m. and midnight\"), and there is no midnight",
        "ceiling. A non-mail method needs a service_time or the extension refuses.",
        "",
        "== WHAT IS DELIBERATELY NOT SEEDED =====================================",
        "No appellate rows. No backward rows. No hours-based rows -- R. 6.01(a)(3)",
        "states periods in HOURS and this engine has no hours unit. No R. 45",
        "non-party rows. And NO production defendant-floor row, because R. 34.02",
        "grants none, where R. 33.01(b) and R. 36.01 both do.",
        "",
        "== TWO DISCLOSED WEAKNESSES ===========================================",
        "(1) Rules 33, 34 and 36 print no dated amendment line of their own, so",
        "their effective_from is the 2020 restyling date rather than a real",
        "per-rule date. A pre-2020 trigger refuses when it might have computed --",
        "the SAFE direction. Rules 6.01 and 12.01 print real dates.",
        "(2) R. 34.02's \"or deemed served pursuant to Rule 26.04(b)\" is not",
        "modelled; 26.04(b) was not read. If a deemed-service date would be later,",
        "this reports EARLY.",
    ],
    "rules": rules,
}

out = "sql/sairnlaw_deadline_seed_minnesota.json"
ids = [r["rule_id"] for r in rules]
assert len(ids) == len(set(ids)), "duplicate rule_id"
with open(out, "w", encoding="utf-8") as f:
    json.dump(doc, f, indent=1, ensure_ascii=False)
    f.write("\n")
print("wrote", out, "with", len(rules), "rules")
for r in rules:
    print("  ", r["rule_id"], "eff", r["effective_from"],
          "[ext]" if r.get("service_extension") else "")
