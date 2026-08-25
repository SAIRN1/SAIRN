"""Build sql/sairnlaw_deadline_seed_virginia.json.

Every quote below was read verbatim on 2026-08-25 from the complete Rules of
Supreme Court of Virginia published free at
https://www.vacourts.gov/static/courts/scv/rulesofcourt.pdf, and every
effective_from is the rule's OWN printed "Last amended by Order dated ...;
effective ..." line, extracted per rule by tools/va_rule_currency.py.
"""
import json

URL = "https://www.vacourts.gov/courts/scv/rules"
RETRIEVED = "2026-08-25"

# Per-rule currency, verified by tools/va_rule_currency.py with strict
# rule-to-next-rule scoping so no rule inherits its neighbour's date.
EFF = {
    "3:8": "2025-08-17",
    "4:8": "2024-01-20",
    "4:9": "2024-01-20",
    "4:11": "2021-03-01",
}

EXT = {
    "standard": "va_rule_1_7",
    "note": (
        "Amount and unit come from the standard, not this row. Va. Sup. Ct. R. 1:7 adds NOTHING for "
        "manual delivery, facsimile, electronic mail or same-day commercial delivery completed at or "
        "before 5:00 p.m., ONE day for any of those completed after 5:00 p.m. but before midnight, ONE "
        "day for a paper placed with a commercial delivery service before midnight for next-day "
        "delivery, and THREE days for mail. Supply service_time as HH:MM in 24-hour form for the four "
        "clock-dependent methods -- without it the engine refuses the extension visibly rather than "
        "choosing between 0 and 1."
    ),
}

NO_EXT_ORDER = (
    "NO SERVICE EXTENSION. R. 1:7 extends a period run after \"service of a paper upon counsel of "
    "record\". This period runs from the court's own entry of an order, which is not service of a paper "
    "on counsel, so nothing is added. Same distinction New Jersey draws between R. 4:6-1(b)'s "
    "motion-denied limb and its more-definite-statement limb."
)


def rule(rid, label, trigger, count, cite, quote, note, eff_key, ext=None):
    r = {
        "rule_id": rid,
        "jurisdiction": "va",
        "domain": "civil-litigation",
        "label": label,
        "trigger_event": trigger,
        "computation": "va_code_1_210",
        "authority": {
            "citation": cite,
            "url": URL,
            "quote": quote,
            "note": note,
            "retrieved_at": RETRIEVED,
        },
        "effective_from": EFF[eff_key],
        "effective_to": None,
        "version": 1,
        "supersedes": None,
    }
    if count is not None:
        r["count"] = {"value": count, "unit": "calendar_days", "direction": "forward"}
    if ext:
        r["service_extension"] = ext
    return r


def later_of(rid, label, tid, ev_a, n_a, lab_a, ev_b, n_b, lab_b, cite, quote, note, eff_key):
    return {
        "rule_id": rid,
        "jurisdiction": "va",
        "domain": "civil-litigation",
        "label": label,
        "trigger_event": {
            "id": tid,
            "resolve_periods": "later_of",
            "limbs": [
                {"event": ev_a, "count": {"value": n_a, "unit": "calendar_days"}, "label": lab_a},
                {"event": ev_b, "count": {"value": n_b, "unit": "calendar_days"}, "label": lab_b},
            ],
        },
        "computation": "va_code_1_210",
        "authority": {
            "citation": cite, "url": URL, "quote": quote, "note": note,
            "retrieved_at": RETRIEVED,
        },
        "effective_from": EFF[eff_key],
        "effective_to": None,
        "version": 1,
        "supersedes": None,
    }


Q_38A = ("A defendant must file pleadings in response within 21 days after service of the summons and "
         "complaint upon that defendant, or if service of the summons has been timely waived on request "
         "under Code § 8.01-286.1, within 60 days after the date when the request for waiver was sent, "
         "or within 90 days after that date if the defendant was addressed outside the Commonwealth.")

Q_48D = ("The party upon whom the interrogatories have been served must serve a copy of the answers, and "
         "objections if any, within 21 days after the service of the interrogatories, except that a "
         "defendant may serve answers or objections within 28 days after service of the complaint upon "
         "that defendant. The court may allow a shorter or longer time.")

Q_49B = ("The party upon whom the request is served must serve a written response within 21 days after "
         "the service of the request, except that a defendant may serve a response within 28 days after "
         "service of the complaint upon that defendant.")

Q_411 = ("The matter is admitted unless, within 21 days after service of the request, or within such "
         "shorter or longer time as the court may allow, the party to whom the request is directed serves "
         "upon the party requesting the admission a written answer or objection addressed to the matter, "
         "signed by the party or by his attorney, but, unless the court shortens the time, a defendant is "
         "not required to serve answers or objections before the expiration of 28 days after service of "
         "the complaint upon him.")

rules = [
    rule("va-r-3-8a-answer-to-complaint",
         "Pleadings in response after service of the summons and complaint (Virginia)",
         "service_of_summons_and_complaint", 21,
         "Va. Sup. Ct. R. 3:8(a)", Q_38A,
         "TWENTY-ONE DAYS, matching the federal 21 and Washington's 20 far more closely than New "
         "Jersey's 35 or the 30 of North Carolina, West Virginia and Georgia. Read, not inherited. "
         "\"PLEADINGS IN RESPONSE\" IS NOT ONLY AN ANSWER: the rule expressly limits them to a demurrer, "
         "plea, motion to dismiss, motion for a bill of particulars, motion craving oyer, and a written "
         "motion asserting a preliminary defense under Code § 8.01-276, and each is responsive only to "
         "the counts it addresses. The same 21 days governs whichever is filed. "
         "NO SERVICE EXTENSION. R. 1:7 extends a period run after \"service of a paper upon counsel of "
         "record\"; the summons and complaint are served on the DEFENDANT, who has no counsel of record "
         "yet. Same scope route as West Virginia, North Carolina, Washington and New Jersey. "
         "R. 3:8(a1) separately bars serial pleading without leave of court -- a restriction on WHAT may "
         "be filed later, not a deadline, and not modelled.",
         "3:8"),

    rule("va-r-3-8a-answer-after-waiver-of-service-in-commonwealth",
         "Pleadings in response where service of the summons was waived, defendant addressed within Virginia",
         "sending_of_request_to_waive_service", 60,
         "Va. Sup. Ct. R. 3:8(a)", Q_38A,
         "SIXTY DAYS, AND THE CLOCK RUNS FROM THE DATE THE REQUEST WAS SENT, not from any response to "
         "it and not from service -- there is no service in this branch, which is the point of waiving "
         "it. The trigger is deliberately named sending_of_request_to_waive_service so a caller cannot "
         "supply a receipt date by accident. Waiver is under Code § 8.01-286.1. "
         "NO SERVICE EXTENSION: nothing was served, so R. 1:7 has nothing to extend.",
         "3:8"),

    rule("va-r-3-8a-answer-after-waiver-of-service-outside-commonwealth",
         "Pleadings in response where service of the summons was waived, defendant addressed outside Virginia",
         "sending_of_request_to_waive_service_addressed_outside_commonwealth", 90,
         "Va. Sup. Ct. R. 3:8(a)", Q_38A,
         "NINETY DAYS, thirty more than the in-Commonwealth branch, and the extra thirty turn on where "
         "the DEFENDANT WAS ADDRESSED -- not on where they live, not on where the request was mailed "
         "from. The rule's words are \"if the defendant was addressed outside the Commonwealth\". A "
         "separate row rather than a variant of the 60-day one because the engine cannot see an address "
         "and must not infer which branch applies. "
         "NO SERVICE EXTENSION: nothing was served.",
         "3:8"),

    rule("va-r-3-8b-answer-after-motions-overruled",
         "Answer after the court overrules all motions, demurrers and pleas (Virginia)",
         "entry_of_order_overruling_all_motions_demurrers_and_pleas", 21,
         "Va. Sup. Ct. R. 3:8(b)",
         "When the court has entered its order overruling all motions, demurrers and other pleas filed "
         "by a defendant as a responsive pleading, such defendant must, unless the defendant has already "
         "done so, file an answer within 21 days after the entry of such order, or within such other "
         "time as the court may prescribe.",
         "RUNS FROM ENTRY OF THE ORDER, not from its service or from notice of it. \"OVERRULING ALL\" IS "
         "LOAD-BEARING: the period starts only when every motion, demurrer and plea the defendant filed "
         "as a responsive pleading has been overruled, so an order disposing of some of them does not "
         "start it. The engine cannot see whether that is true of a given order and takes the caller's "
         "trigger date as the date it became true. "
         "\"OR WITHIN SUCH OTHER TIME AS THE COURT MAY PRESCRIBE\" -- an order the engine cannot see "
         "displaces this row entirely. " + NO_EXT_ORDER,
         "3:8"),

    rule("va-r-3-8b-answer-after-oyer-documents-filed",
         "Answer after the plaintiff files documents for which oyer was granted (Virginia)",
         "filing_of_documents_for_which_oyer_was_granted", 21,
         "Va. Sup. Ct. R. 3:8(b)",
         "If the court grants a motion craving oyer, unless the defendant has already filed an answer or "
         "another responsive pleading, the defendant must file an answer or another responsive pleading "
         "within 21 days after plaintiff files the document(s) for which oyer was granted, or within such "
         "other time as the court may prescribe.",
         "RUNS FROM THE PLAINTIFF'S FILING, not from the order granting oyer and not from service of the "
         "documents. Craving oyer is a Virginia-specific pleading with no analogue in any jurisdiction "
         "seeded so far; it demands production of a deed or other document the complaint relies on. "
         "NO SERVICE EXTENSION: R. 1:7 extends a period run after service of a paper on counsel of "
         "record, and this one runs from a FILING. "
         "\"OR WITHIN SUCH OTHER TIME AS THE COURT MAY PRESCRIBE\" displaces this row.",
         "3:8"),

    rule("va-r-3-8b-answer-after-jurisdiction-or-process-motion-overruled",
         "Answer after the court overrules a sole motion objecting to personal jurisdiction or defective process",
         "entry_of_order_overruling_motion_objecting_to_personal_jurisdiction_or_defective_process", 21,
         "Va. Sup. Ct. R. 3:8(b)",
         "If the court overrules a motion objecting to personal jurisdiction or defective process filed "
         "as a defendant's sole initial responsive pleading, then the defendant must file an answer or "
         "another responsive pleading within 21 days after entry of the court's order overruling the "
         "motion, or within such other time as the court may prescribe.",
         "\"SOLE INITIAL RESPONSIVE PLEADING\" IS THE WHOLE CONDITION, and it is why this is a separate "
         "row from the overruling-all-motions limb rather than an example of it. This limb reaches a "
         "defendant who filed NOTHING BUT the jurisdiction or process motion; a defendant who filed it "
         "alongside a demurrer falls under the first limb instead. Both happen to be 21 days, so the "
         "distinction changes no arithmetic today -- it is preserved because the rule draws it and a "
         "future amendment to either limb would silently corrupt the other if they were merged. " +
         NO_EXT_ORDER,
         "3:8"),

    rule("va-r-4-8d-interrogatory-answers",
         "Answers and objections to interrogatories (Virginia)",
         "service_of_interrogatories", 21,
         "Va. Sup. Ct. R. 4:8(d)", Q_48D,
         "TWENTY-ONE DAYS, the shortest first period of any state seeded (New Jersey 60, North Carolina "
         "30, Washington 30, and Virginia 21) and read from the rule rather than inferred from the "
         "answer period happening to be 21 as well. This row is the PLAIN limb, for a party who is not a "
         "defendant taking the 28-day floor -- see the -defendant-later-of-periods row for that. "
         "SERVICE EXTENSION APPLIES: interrogatories are served on counsel of record, squarely within "
         "R. 1:7. "
         "\"THE COURT MAY ALLOW A SHORTER OR LONGER TIME\" -- an order the engine cannot see.",
         "4:8", EXT),

    later_of("va-r-4-8d-interrogatory-answers-defendant-later-of-periods",
             "Answers and objections to interrogatories served on a defendant (Virginia)",
             "interrogatories_on_defendant",
             "service_of_interrogatories_on_defendant", 21, "21 days after service of the interrogatories",
             "service_of_summons_and_complaint_for_interrogatories", 28,
             "28 days after service of the complaint on that defendant",
             "Va. Sup. Ct. R. 4:8(d)", Q_48D,
             "A DEFENDANT GETS THE LATER OF THE TWO PERIODS. The rule's \"except that a defendant may "
             "serve answers or objections within 28 days after service of the complaint\" is a floor "
             "under the 21-day period, not a replacement for it: interrogatories served with the "
             "complaint leave 28 days, interrogatories served two months into the case still leave 21 "
             "from their own service. Same shape as New Jersey's 35/50 and North Carolina's 30/60, with "
             "Virginia's own numbers. "
             "21 AND 28 ARE ONLY SEVEN APART, the narrowest gap of any seeded later-of pair, which makes "
             "this the pair most likely to be got wrong by assuming the defendant limb always governs. "
             "It does not: it governs only for interrogatories served within the first week. "
             "NO SERVICE EXTENSION ON THIS ROW. The plain limb carries one and this one deliberately "
             "does not: no seeded rule combines resolve_periods with a service extension, the engine has "
             "never been exercised on that combination, and inventing the interaction here -- does the "
             "extension lengthen one limb or both, before or after the later-of resolves -- would be "
             "guessing at an order no rule text settles. A caller needing the extension on a defendant's "
             "interrogatories should compute the plain limb and compare by hand.",
             "4:8"),

    rule("va-r-4-9b-production-response",
         "Written response to a request for production (Virginia)",
         "service_of_request_for_production", 21,
         "Va. Sup. Ct. R. 4:9(b)(ii)", Q_49B,
         "TWENTY-ONE DAYS. Identical in number and in structure to R. 4:8(d)'s interrogatory period, "
         "including the same 28-day defendant floor -- Virginia is unusually consistent across its "
         "discovery rules where New Jersey's are not (35/50 for production against 60 flat for "
         "interrogatories). The consistency was verified rule by rule, not assumed from the first one. "
         "SERVICE EXTENSION APPLIES: the request is served on counsel of record. "
         "R. 4:9A governs production from NON-PARTIES by subpoena duces tecum and is NOT seeded; its "
         "objection period keys off \"less than fourteen (14) days after service of the subpoena\", a "
         "conditional shape that needs its own reading.",
         "4:9", EXT),

    later_of("va-r-4-9b-production-response-defendant-later-of-periods",
             "Written response to a request for production served on a defendant (Virginia)",
             "production_request_on_defendant",
             "service_of_request_for_production_on_defendant", 21, "21 days after service of the request",
             "service_of_summons_and_complaint_for_production", 28,
             "28 days after service of the complaint on that defendant",
             "Va. Sup. Ct. R. 4:9(b)(ii)", Q_49B,
             "A DEFENDANT GETS THE LATER OF THE TWO PERIODS, on the same 21/28 pair as interrogatories. "
             "The rule's wording here is \"except that a defendant may serve a response within 28 days\" "
             "-- permissive, like R. 4:8(d)'s, and unlike R. 4:11's \"is not required to serve ... "
             "before the expiration of 28 days\", which is a prohibition. All three resolve to the same "
             "later-of arithmetic and the difference in wording is recorded rather than flattened. "
             "NO SERVICE EXTENSION ON THIS ROW, for the reason given on the interrogatory sibling.",
             "4:9"),

    rule("va-r-4-11-admission-response",
         "Answer or objection to a request for admission (Virginia — unanswered matters are ADMITTED)",
         "service_of_request_for_admission", 21,
         "Va. Sup. Ct. R. 4:11(a)", Q_411,
         "TWENTY-ONE DAYS, AND SILENCE ADMITS. The rule is written as an automatic consequence -- \"The "
         "matter is admitted unless, within 21 days ... the party ... serves ... a written answer or "
         "objection\" -- so a missed date is not a sanctionable lapse but a substantive admission, the "
         "same structure Ohio Civ.R. 36(A)(1) carries and the reason this label says so out loud. "
         "SERVICE EXTENSION APPLIES: the request is served on counsel of record. "
         "\"OR WITHIN SUCH SHORTER OR LONGER TIME AS THE COURT MAY ALLOW\" -- an order the engine cannot "
         "see, and here it can make the period SHORTER, which the equivalent orders in the answer rules "
         "cannot.",
         "4:11", EXT),

    later_of("va-r-4-11-admission-response-defendant-later-of-periods",
             "Answer or objection to a request for admission served on a defendant (Virginia)",
             "admission_request_on_defendant",
             "service_of_request_for_admission_on_defendant", 21, "21 days after service of the request",
             "service_of_summons_and_complaint_for_admission", 28,
             "28 days after service of the complaint on that defendant",
             "Va. Sup. Ct. R. 4:11(a)", Q_411,
             "A DEFENDANT GETS THE LATER OF THE TWO PERIODS, but R. 4:11 PHRASES IT AS A PROHIBITION "
             "rather than a permission: \"a defendant is not required to serve answers or objections "
             "before the expiration of 28 days after service of the complaint upon him\". Same "
             "arithmetic as its two siblings, opposite grammar. "
             "\"UNLESS THE COURT SHORTENS THE TIME\" QUALIFIES THE 28-DAY FLOOR SPECIFICALLY, not the "
             "21-day period, and it is the only place in Virginia's seeded discovery rules where a court "
             "order is named as able to cut the defendant's floor. Not modelled -- the engine cannot see "
             "the order -- but a caller relying on the 28-day limb should confirm none was entered. "
             "NO SERVICE EXTENSION ON THIS ROW, for the reason given on the interrogatory sibling.",
             "4:11"),
]

doc = {
    "_readme": [
        "VIRGINIA CIVIL DEADLINE RULES -- 12 rows, Rules 3:8, 4:8, 4:9 and 4:11.",
        "",
        "== SOURCE ==============================================================",
        "Read verbatim on 2026-08-25 from the complete Rules of Supreme Court of",
        "Virginia, published free and in full by the Commonwealth at",
        "vacourts.gov/static/courts/scv/rulesofcourt.pdf. No paywall and no",
        "redirect to a commercial publisher -- the failure mode that blocked",
        "Kentucky outright and gated Arizona out is simply absent here.",
        "",
        "== effective_from IS REAL ON EVERY ROW, WHICH IS NEW ====================",
        "New Jersey and North Carolina both carry a blanket 1969-09-08 and both",
        "disclose it as a weakness. Virginia does not need one: the published",
        "Rules print a per-rule 'Last amended by Order dated ...; effective ...'",
        "line, 314 of them, and every rule seeded here has its own. Extracted by",
        "tools/va_rule_currency.py, which scopes strictly from one rule heading to",
        "the next so no rule can inherit its neighbour's date.",
        "  R. 3:8  -> 2025-08-17   R. 4:8 -> 2024-01-20",
        "  R. 4:9  -> 2024-01-20   R. 4:11 -> 2021-03-01",
        "",
        "== THE COMPUTATION IS A STATUTE, THE INVERSE OF NEW JERSEY =============",
        "Va. Code 1-210 governs, and it reaches time fixed by 'an act of the",
        "General Assembly OR rule of court'. N.J. R. 1:3-1 reaches time fixed 'by",
        "rule or court order' and NOT by statute. The two were read independently",
        "and neither was assumed from the other. Virginia also has NO short-period",
        "exclusion anywhere -- checked against the full Rules text, not assumed.",
        "",
        "== COVERAGE DISCLOSURE RIDES ON EVERY RESULT ===========================",
        "Virginia court closures beyond the statewide Va. Code 2.2-3300 list are",
        "not modelled and cannot be: 1-210(F) and 2.2-3300's own final sentence",
        "make Governor- and President-appointed closing days legal holidays, and",
        "17.1-207 lets each clerk close for locality holidays, Christmas Eve and",
        "judge-authorized health or safety threats. Omitting them can only report",
        "a date EARLIER than the true deadline, never later, so the engine",
        "DISCLOSES rather than refuses -- see JURISDICTION_COVERAGE in",
        "api/_lib/deadline-engine.js. Kentucky is refused because its gap runs the",
        "other way.",
        "",
        "== R. 1:7 IS THE FIRST TIME-OF-DAY EXTENSION IN THE ENGINE =============",
        "0 days at or before 5:00 p.m., 1 day after it, for the same method. The",
        "four clock-dependent methods REFUSE VISIBLY without a service_time rather",
        "than choosing between 0 and 1. Six method names are accepted:",
        "manual_delivery, facsimile, electronic_mail, commercial_delivery_same_day,",
        "commercial_delivery_next_day, mail. A bare 'commercial_delivery' does not",
        "qualify -- the rule splits it by the service actually bought.",
        "",
        "== WHAT IS DELIBERATELY NOT SEEDED =====================================",
        "No appellate rows (Parts Five and Five A, where R. 1:7 is carved down to",
        "briefs in opposition only). No R. 4:9A non-party subpoena rows. No",
        "backward rows, though 1-210(A) does define the backward direction. No",
        "statutory-period rows, because R. 1:7's own scope is rules and court",
        "directions only.",
    ],
    "rules": rules,
}

out = "sql/sairnlaw_deadline_seed_virginia.json"
ids = [r["rule_id"] for r in rules]
assert len(ids) == len(set(ids)), "duplicate rule_id"
with open(out, "w", encoding="utf-8") as f:
    json.dump(doc, f, indent=1, ensure_ascii=False)
    f.write("\n")
print("wrote", out, "with", len(rules), "rules")
for r in rules:
    print("  ", r["rule_id"], "eff", r["effective_from"])
