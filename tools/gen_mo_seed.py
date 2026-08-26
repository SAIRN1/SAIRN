"""Build sql/sairnlaw_deadline_seed_missouri.json.

Every quote below was read VERBATIM on 2026-08-26 from the Missouri Supreme
Court Rules as published free and in full by the Missouri courts, and every
effective_from is the rule page's OWN printed "Revised / Effective Date".

ACCESS NOTE, WORTH KEEPING: `courts.mo.gov/page.jsp?id=...` is behind a
Cloudflare bot challenge that neither curl nor headless Playwright clears -- it
returns a "Performing security verification" interstitial indefinitely. The
underlying `ClerkHandbooksP2RulesOnly.nsf/<id>` document URLs are NOT challenged
and return full text to an ordinary browser context. A challenge on page.jsp
means "wrong URL shape", NOT "rule unavailable". Third distinct access mechanism
after mass.gov (403 to everything but a browser) and tncourts.gov (JS challenge).
"""
import json

NSF = ("https://www.courts.mo.gov/courts/ClerkHandbooksP2RulesOnly.nsf/"
       "c0c6ffa99df4993f86256ba50057dcb8/")
URL = {
    "44.01": "https://www.courts.mo.gov/courts/ClerkHandbooksP2RulesOnly.nsf/0/59231e1c136ceb1086256ca60052133a?OpenDocument=",
    "43.01": NSF + "f54a7a01ed6d17e186256ca600521339",
    "55.25": NSF + "9f17d15f671cda9386256ca600521542?OpenDocument=",
    "57.01": NSF + "ccbd32559d4a216986256ca60052134f?OpenDocument=",
    "58.01": NSF + "eaf6abbe82915a0586256ca600521350?OpenDocument=",
    "59.01": NSF + "599c2f573b62fd0086256ca600521354",
}
RETRIEVED = "2026-08-26"

# Per-rule currency, read from each rule page's own printed
# "Revised / Effective Date". Real per rule, like Virginia and Massachusetts.
EFF = {
    "55.25": "1994-01-01",
    "57.01": "2021-12-01",
    "58.01": "2021-09-02",
    "59.01": "2022-07-01",
}

# ── The two service mechanisms, and why a row carries BOTH ────────────────
# Missouri splits by method, which no other seeded state does:
#   MAIL                      -> R. 44.01(d) adds three days to the period.
#   FAX / E-MAIL / E-FILING   -> R. 43.01(d) and R. 103.08(a) move WHEN SERVICE
#                                IS COMPLETE. No days are added at all.
# So a discovery row legitimately declares an extension AND a completion
# standard, and no METHOD appears under both. The endpoint validator enforces
# that non-overlap; see api/legal-deadlines.js.
EXT = {
    "standard": "mo_rule_44_01_d",
    "add": 3,
    "unit": "calendar_days",
    "applies_when": ["mail"],
    "note": (
        "Mo. R. Civ. P. 44.01(d) adds three days for service BY MAIL ONLY: \"the notice or paper is "
        "served by mail three days shall be added to the prescribed period\". \"Added to the prescribed "
        "period\", so the days lengthen the period and one rollover runs at the end -- NOT the federal "
        "after-expiry order. ELECTRONIC SERVICE GETS NOTHING HERE, and that is not an omission: it is "
        "handled by the separate service_completion standard on this row, which moves the date the "
        "period runs from instead. Do not widen applies_when to email or e-filing by analogy to "
        "Massachusetts or Tennessee -- Missouri deliberately does the opposite."
    ),
}

COMPLETION = {
    "standard": "mo_rule_43_01_d",
    "note": (
        "Mo. R. Civ. P. 43.01(d): \"Service by facsimile transmission or electronic mail is complete "
        "upon transmission, except that a transmission made on a Saturday, Sunday, or legal holiday, or "
        "after 5:00 p.m. shall be complete on the next day that is not a Saturday, Sunday, or legal "
        "holiday.\" R. 103.08(a) states the same for service through the electronic filing system, "
        "expressly \"for the purposes of calculating the time for filing a response\". This moves the "
        "TRIGGER DATE, not the amount added, so a service_time is REQUIRED for these methods and the "
        "engine refuses outright without one -- unlike Virginia's R. 1:7 refusal, which can still return "
        "a date computed without an extension. Mail is deliberately NOT governed: R. 43.01(d) says "
        "\"Service by mail is complete upon mailing\", full stop."
    ),
}

Q_55_25A = ("A defendant shall file an answer within thirty days after the service of the summons and "
            "petition, except where service by mail is had, in which event a defendant shall file an "
            "answer within thirty days after the acknowledgment of receipt of summons and petition or "
            "return registered or certified mail receipt is filed in the case or within forty-five days "
            "after the first publication of notice if neither personal service nor service by mail is had.")

Q_55_25B = ("If a cross-claim is filed against a party, the party shall file answer thereto within thirty "
            "days after the same is filed. A reply shall be filed within thirty days after the filing of "
            "the pleading to which it is directed. If a reply is ordered by the court, it shall be filed "
            "within twenty days after the entry of the order unless the order otherwise directs.")

Q_55_25C = ("The filing of any motion provided for in Rule 55.27 alters the time fixed for filing any "
            "required responsive pleadings as follows, unless a different time is fixed by order of the "
            "court: If the court denies the motion or postpones its disposition until the trial on the "
            "merits, the responsive pleading shall be filed within ten days after notice of the court's "
            "action; if the court grants a motion for a more definite statement the responsive pleading "
            "shall be filed within ten days after the filing of the more definite statement. In either "
            "case the time for filing of the responsive pleading shall be no less than remains of the "
            "time which would have been allowed under this Rule if the motion had not been made.")

Q_57_01 = ("Responses shall be served within 30 days after the service of the interrogatories. A "
           "defendant, however, shall not be required to respond to interrogatories before the expiration "
           "of 45 days after the earlier of: (A) The date the defendant enters an appearance, or (B) The "
           "date the defendant is served with process. The court may allow a shorter or longer time.")

Q_58_01 = ("Responses shall be served within 30 days after the service of the request. A defendant, "
           "however, shall not be required to respond to the request before the expiration of 45 days "
           "after the earlier of: (A) The date the defendant enters an appearance; or (B) The date the "
           "defendant is served with process. The court may allow a shorter or longer time.")

Q_59_01 = ("Responses shall be served within 30 days after the service of the requests for admissions. A "
           "defendant or respondent, however, shall not be required to respond to requests for admissions "
           "before the expiration of 60 days after the earlier of the defendant: (A) Entering an "
           "appearance, or (B) Being served with process. The court may allow a shorter or longer time.")

# The floor that R. 55.25(c) puts under BOTH of its ten-day limbs. Recorded once
# and appended to both rows, because it is the same sentence governing both.
FLOOR_55_25C = (
    " NOT MODELLED, AND THE OMISSION RUNS EARLY: the subsection ends \"In either case the time for "
    "filing of the responsive pleading shall be no less than remains of the time which would have been "
    "allowed under this Rule if the motion had not been made.\" That is a floor measured against how "
    "much of the ORIGINAL 30-day period was left when the motion was filed -- a quantity this engine "
    "cannot see, because it depends on a date (when the motion was filed) that is not this rule's "
    "trigger. Since the rule takes whichever is LONGER, the ten-day date computed here is a FLOOR: the "
    "true deadline is this date or later, never earlier. So the omission reports EARLY, which is the "
    "safe direction. A caller must not read this date as proof the right to plead has expired."
)

NO_EXT_FILING = (
    " NO SERVICE EXTENSION AND NO COMPLETION RULE. R. 44.01(d) extends a period run after \"the service "
    "of a notice or other paper\"; this period runs from a FILING or from the court's own action, "
    "neither of which is service of a paper by a party."
)


def rule(rid, label, trigger, count, cite, quote, note, eff_key, ext=None, completion=None):
    r = {
        "rule_id": rid,
        "jurisdiction": "mo",
        "domain": "civil-litigation",
        "label": label,
        "trigger_event": trigger,
        "count": {"value": count, "unit": "calendar_days", "direction": "forward"},
        "computation": "mo_rule_44_01_a",
        "authority": {
            "citation": cite, "url": URL[eff_key], "quote": quote, "note": note,
            "retrieved_at": RETRIEVED,
        },
        "effective_from": EFF[eff_key],
        "effective_to": None,
        "version": 1,
        "supersedes": None,
    }
    if ext:
        r["service_extension"] = ext
    if completion:
        r["service_completion"] = completion
    return r


def later_of(rid, label, tid, ev_a, n_a, lab_a, ev_b, n_b, lab_b, cite, quote, note, eff_key):
    return {
        "rule_id": rid,
        "jurisdiction": "mo",
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
        "computation": "mo_rule_44_01_a",
        "authority": {
            "citation": cite, "url": URL[eff_key], "quote": quote, "note": note,
            "retrieved_at": RETRIEVED,
        },
        "effective_from": EFF[eff_key],
        "effective_to": None,
        "version": 1,
        "supersedes": None,
    }


# The defendant-floor limb in all three discovery rules runs from "the EARLIER
# of" two events. resolve_periods limbs take ONE event each, so the earlier-of
# cannot be resolved inside the limb -- the caller supplies the earlier date and
# the event is NAMED so it cannot be supplied by accident. Recorded on every row
# that uses it, because getting it wrong runs LATE.
EARLIER_OF_WARNING = (
    " THE DEFENDANT LIMB RUNS FROM \"THE EARLIER OF\" TWO EVENTS AND THE ENGINE CANNOT RESOLVE THAT "
    "ITSELF. The rule measures the floor from the earlier of the date the defendant entered an "
    "appearance and the date the defendant was served with process. A resolve_periods limb takes one "
    "event, so the limb is named "
    "\"earlier_of_defendant_appearance_or_service_of_process\" and the CALLER must supply the EARLIER "
    "of the two dates. THE ERROR DIRECTION IF THE LATER DATE IS SUPPLIED IS LATE, which is the "
    "direction that misses a filing -- so the event name is deliberately unmissable rather than a "
    "generic one. Compare Virginia's sending_of_request_to_waive_service, named on the same reasoning."
)

rules = [
    # ── R. 55.25(a): three branches, three different triggers ──────────────
    rule("mo-r-55-25a-answer-after-personal-service",
         "Answer after personal service of the summons and petition (Missouri)",
         "service_of_summons_and_petition", 30,
         "Mo. R. Civ. P. 55.25(a)", Q_55_25A,
         "THIRTY DAYS, the middle of the seeded range (Washington and Massachusetts 20, federal and "
         "Virginia 21, New Jersey 35) and read from the rule rather than inferred. "
         "R. 55.25(a) HAS THREE BRANCHES WITH THREE DIFFERENT TRIGGERS and they are three rows here, "
         "because the engine must never guess which manner of service was used. This is the personal-"
         "service branch. " + NO_EXT_FILING.replace("this period runs from a FILING or from the court's "
         "own action, neither of which is service of a paper by a party.",
         "the summons and petition are served under Rule 54, not Rule 43, so neither mechanism reaches "
         "this row. Same scope route as West Virginia, North Carolina, Washington, New Jersey, Virginia "
         "and Massachusetts."),
         "55.25"),

    rule("mo-r-55-25a-answer-after-service-by-mail",
         "Answer where service was by mail, running from the filing of the receipt (Missouri)",
         "filing_of_acknowledgment_or_return_receipt_of_summons_and_petition", 30,
         "Mo. R. Civ. P. 55.25(a)", Q_55_25A,
         "THIRTY DAYS, BUT THE CLOCK RUNS FROM A FILING, NOT FROM SERVICE. The rule's words are "
         "\"within thirty days after the acknowledgment of receipt of summons and petition or return "
         "registered or certified mail receipt IS FILED IN THE CASE\". The trigger is named for the "
         "FILING so a caller cannot supply the mailing date or the receipt date by accident -- either "
         "would compute EARLY. "
         "NOTE THE TRAP THIS ROW EXISTS TO AVOID: this is the branch where service WAS by mail, and it "
         "still takes NO three-day extension under R. 44.01(d), because the period does not run after "
         "service of a paper -- it runs after a filing. A row that carried the extension here would add "
         "three days the rule does not give and compute LATE.",
         "55.25"),

    rule("mo-r-55-25a-answer-after-publication",
         "Answer where neither personal service nor service by mail was had (Missouri)",
         "first_publication_of_notice", 45,
         "Mo. R. Civ. P. 55.25(a)", Q_55_25A,
         "FORTY-FIVE DAYS, fifteen more than the other two branches, and it runs from the FIRST "
         "publication -- not the last, and not the completion of publication. The rule reaches this "
         "branch only \"if neither personal service nor service by mail is had\", a condition the "
         "engine cannot verify, so it is a separate row rather than a variant. " + NO_EXT_FILING,
         "55.25"),

    # ── R. 55.25(b): three more, all running from FILINGS or an ORDER ──────
    rule("mo-r-55-25b-answer-to-crossclaim",
         "Answer to a cross-claim (Missouri)",
         "filing_of_crossclaim", 30,
         "Mo. R. Civ. P. 55.25(b)", Q_55_25B,
         "THIRTY DAYS AFTER THE CROSS-CLAIM IS FILED -- \"within thirty days after the same is FILED\". "
         "Missouri measures this from filing where most seeded states measure it from service: North "
         "Carolina's Rule 12(a)(1) says \"within 30 days after service upon him\", and Massachusetts' "
         "R. 12(a)(1) says \"after service upon him of any pleading\". The difference is not cosmetic -- "
         "it decides whether the three-day mail extension can ever apply, and here it cannot." +
         NO_EXT_FILING,
         "55.25"),

    rule("mo-r-55-25b-reply-to-pleading",
         "Reply to a pleading requiring one (Missouri)",
         "filing_of_pleading_to_which_reply_is_directed", 30,
         "Mo. R. Civ. P. 55.25(b)", Q_55_25B,
         "THIRTY DAYS AFTER THE FILING of the pleading the reply answers. Same filing-not-service "
         "measurement as the cross-claim row, and the same consequence." + NO_EXT_FILING,
         "55.25"),

    rule("mo-r-55-25b-reply-ordered-by-court",
         "Reply ordered by the court (Missouri)",
         "entry_of_order_requiring_reply", 20,
         "Mo. R. Civ. P. 55.25(b)", Q_55_25B,
         "TWENTY DAYS, AND IT IS THE ONLY TWENTY-DAY PERIOD IN THE MISSOURI SEED. It runs from ENTRY of "
         "the order, not from notice of it -- the opposite of R. 55.25(c)'s limbs, which run from "
         "NOTICE of the court's action. Both distinctions sit in the same rule and are recorded rather "
         "than flattened. "
         "\"UNLESS THE ORDER OTHERWISE DIRECTS\" -- an order the engine cannot see displaces this row." +
         NO_EXT_FILING,
         "55.25"),

    # ── R. 55.25(c): the two motion limbs, both with the unmodelled floor ──
    rule("mo-r-55-25c-responsive-pleading-after-motion-denied",
         "Responsive pleading after the court denies a Rule 55.27 motion or postpones it to trial (Missouri)",
         "notice_of_court_action_denying_or_postponing_rule_55_27_motion", 10,
         "Mo. R. Civ. P. 55.25(c)", Q_55_25C,
         "TEN DAYS FROM NOTICE OF THE COURT'S ACTION -- not from entry of the order. Its sibling in "
         "R. 55.25(b) runs from ENTRY; this one runs from NOTICE. The triggers are named accordingly. "
         "TEN DAYS IS NOT SHORT ENOUGH FOR THE EXCLUSION: R. 44.01(a) excludes intermediate weekends and "
         "holidays only when the period is \"less than seven days\", so all ten days count." +
         NO_EXT_FILING + FLOOR_55_25C,
         "55.25"),

    rule("mo-r-55-25c-responsive-pleading-after-more-definite-statement",
         "Responsive pleading after the filing of a more definite statement (Missouri)",
         "filing_of_more_definite_statement", 10,
         "Mo. R. Civ. P. 55.25(c)", Q_55_25C,
         "TEN DAYS AFTER THE MORE DEFINITE STATEMENT IS FILED. Massachusetts' equivalent limb runs from "
         "SERVICE of the more definite statement and therefore DOES take that state's extension; "
         "Missouri's runs from the FILING and takes nothing. Two neighbouring rules, same sentence "
         "structure, opposite result on the extension -- read per state." + NO_EXT_FILING +
         FLOOR_55_25C,
         "55.25"),

    # ── Discovery: the plain limbs carry BOTH service mechanisms ───────────
    rule("mo-r-57-01-c1-interrogatory-answers",
         "Answers and objections to interrogatories (Missouri)",
         "service_of_interrogatories", 30,
         "Mo. R. Civ. P. 57.01(c)(1)", Q_57_01,
         "THIRTY DAYS. This row is the PLAIN limb, for a party who is not a defendant taking the 45-day "
         "floor -- see the -defendant-later-of-periods row. "
         "THIS ROW CARRIES BOTH SERVICE MECHANISMS AND THAT IS CORRECT, NOT A DUPLICATE. Missouri "
         "splits by method: service by MAIL adds three days under R. 44.01(d), while service by "
         "FACSIMILE, ELECTRONIC MAIL or the E-FILING SYSTEM adds nothing and instead moves the date "
         "service was COMPLETE under R. 43.01(d) and R. 103.08(a). No method appears under both, and "
         "the endpoint validator refuses any row where one does. "
         "\"THE COURT MAY ALLOW A SHORTER OR LONGER TIME\" -- an order the engine cannot see.",
         "57.01", EXT, COMPLETION),

    later_of("mo-r-57-01-c1-interrogatory-answers-defendant-later-of-periods",
             "Answers and objections to interrogatories served on a defendant (Missouri)",
             "interrogatories_on_defendant",
             "service_of_interrogatories_on_defendant", 30, "30 days after service of the interrogatories",
             "earlier_of_defendant_appearance_or_service_of_process_for_interrogatories", 45,
             "45 days after the earlier of the defendant's appearance and service of process",
             "Mo. R. Civ. P. 57.01(c)(1)", Q_57_01,
             "A DEFENDANT GETS THE LATER OF THE TWO PERIODS. \"A defendant, however, shall not be "
             "required to respond to interrogatories before the expiration of 45 days\" is a floor under "
             "the 30-day period, not a replacement for it. "
             "FORTY-FIVE HERE AND SIXTY ON ADMISSIONS -- MISSOURI IS NOT INTERNALLY CONSISTENT, and "
             "carrying one across to the other would be wrong. R. 57.01 and R. 58.01 both give 45; "
             "R. 59.01 gives 60. Each was read on its own." + EARLIER_OF_WARNING +
             " NO SERVICE EXTENSION OR COMPLETION RULE ON THIS ROW. The plain limb carries both and this "
             "one deliberately carries neither: no seeded rule combines resolve_periods with either "
             "mechanism, the engine has never been exercised on that combination, and inventing the "
             "interaction -- does an extension lengthen one limb or both, and does a completion shift "
             "move one trigger or the comparison itself -- would be guessing at an order no rule text "
             "settles. Compute the plain limb and compare by hand.",
             "57.01"),

    rule("mo-r-58-01-c1-production-response",
         "Written response to a request for production (Missouri)",
         "service_of_request_for_production", 30,
         "Mo. R. Civ. P. 58.01(c)(1)", Q_58_01,
         "THIRTY DAYS, with the same 45-day defendant floor as interrogatories -- the two discovery "
         "rules genuinely match here, verified rule by rule rather than assumed from the first. "
         "Both service mechanisms apply, split by method, as on the interrogatory row. "
         "\"THE COURT MAY ALLOW A SHORTER OR LONGER TIME\" -- an order the engine cannot see.",
         "58.01", EXT, COMPLETION),

    later_of("mo-r-58-01-c1-production-response-defendant-later-of-periods",
             "Written response to a request for production served on a defendant (Missouri)",
             "production_request_on_defendant",
             "service_of_request_for_production_on_defendant", 30, "30 days after service of the request",
             "earlier_of_defendant_appearance_or_service_of_process_for_production", 45,
             "45 days after the earlier of the defendant's appearance and service of process",
             "Mo. R. Civ. P. 58.01(c)(1)", Q_58_01,
             "A DEFENDANT GETS THE LATER OF THE TWO PERIODS, on the same 30/45 pair as interrogatories "
             "and NOT the 30/60 pair admissions uses." + EARLIER_OF_WARNING +
             " NO SERVICE EXTENSION OR COMPLETION RULE ON THIS ROW, for the reason given on the "
             "interrogatory sibling.",
             "58.01"),

    rule("mo-r-59-01-d1-admission-response",
         "Answer or objection to a request for admission (Missouri — unanswered matters are ADMITTED)",
         "service_of_request_for_admission", 30,
         "Mo. R. Civ. P. 59.01(d)(1)", Q_59_01,
         "THIRTY DAYS, AND SILENCE ADMITS: R. 59.01(a)(2) provides that \"a failure to timely respond to "
         "requests for admissions in compliance with this Rule 59.01 shall result in each matter being "
         "admitted\", and R. 59.01(a)(1) requires the request itself to carry that warning in boldface "
         "capitals. Same self-executing structure as Ohio Civ.R. 36(A)(1), Va. R. 4:11(a) and Mass. "
         "R. 36(a), and the reason this label says so out loud. "
         "A CARVE-OUT THE ENGINE CANNOT SEE: in cases under Chapter 517 RSMo the automatic admission "
         "does NOT apply -- the court may instead grant more time or order the requests re-served. This "
         "row computes the date either way; what changes is the consequence of missing it, which is a "
         "question of law and not of arithmetic. "
         "Both service mechanisms apply, split by method.",
         "59.01", EXT, COMPLETION),

    later_of("mo-r-59-01-d1-admission-response-defendant-later-of-periods",
             "Answer or objection to a request for admission served on a defendant (Missouri)",
             "admission_request_on_defendant",
             "service_of_request_for_admission_on_defendant", 30, "30 days after service of the requests",
             "earlier_of_defendant_appearance_or_service_of_process_for_admission", 60,
             "60 days after the earlier of the defendant's appearance and service of process",
             "Mo. R. Civ. P. 59.01(d)(1)", Q_59_01,
             "SIXTY DAYS, NOT FORTY-FIVE, AND THIS IS THE ROW MOST LIKELY TO BE GOT WRONG BY ANALOGY. "
             "Interrogatories and production both give a defendant 45 days; admissions give 60. Reading "
             "45 here would compute EARLY on the floor limb -- and because silence ADMITS under this "
             "rule, an early date on an admissions deadline is the most consequential error in the "
             "Missouri seed. Each number was read from its own rule." + EARLIER_OF_WARNING +
             " NO SERVICE EXTENSION OR COMPLETION RULE ON THIS ROW, for the reason given on the "
             "interrogatory sibling.",
             "59.01"),
]

doc = {
    "_readme": [
        "MISSOURI CIVIL DEADLINE RULES -- 14 rows, Rules 55.25, 57.01, 58.01 and 59.01.",
        "",
        "== SOURCE ==============================================================",
        "Read verbatim on 2026-08-26 from the Missouri Supreme Court Rules,",
        "published free and in full by the Missouri courts. No paywall, no terms",
        "gate, no redirect to a commercial publisher -- the failure modes that",
        "blocked Kentucky and Tennessee and gated Arizona are all absent.",
        "",
        "ACCESS: courts.mo.gov/page.jsp is behind a Cloudflare bot challenge that",
        "neither curl nor headless Playwright clears. The underlying",
        "ClerkHandbooksP2RulesOnly.nsf/<id> document URLs are NOT challenged. A",
        "challenge on page.jsp means 'wrong URL shape', not 'rule unavailable'.",
        "",
        "The STATUTE side is the best of any state seeded: revisor.mo.gov is the",
        "official Revisor, free, HTTP 200 to plain curl, with per-section version",
        "history and effective dates.",
        "",
        "== effective_from IS REAL ON EVERY ROW =================================",
        "  R. 55.25 -> 1994-01-01   R. 57.01 -> 2021-12-01",
        "  R. 58.01 -> 2021-09-02   R. 59.01 -> 2022-07-01",
        "",
        "== MISSOURI SPLITS SERVICE BY METHOD, WHICH NO OTHER SEEDED STATE DOES ==",
        "MAIL                    -> R. 44.01(d) adds THREE DAYS to the period.",
        "FAX / E-MAIL / E-FILING -> R. 43.01(d) and R. 103.08(a) add NOTHING and",
        "                           instead move WHEN SERVICE WAS COMPLETE, which",
        "                           moves the date the period runs from.",
        "So the three plain discovery rows carry BOTH a service_extension and a",
        "service_completion, and no method appears under both. That is correct and",
        "not a duplicate; the endpoint validator refuses any row where a method",
        "does appear under both.",
        "",
        "A service_time (HH:MM, 24-hour) is REQUIRED for fax, e-mail and e-filing",
        "service, and the engine REFUSES OUTRIGHT without one -- a harder refusal",
        "than Virginia's, because an unknown completion date means an unknown",
        "period START, so there is no date to return at all.",
        "",
        "== THE NUMBERS ARE NOT INTERNALLY CONSISTENT ===========================",
        "Interrogatories and production give a defendant a 45-day floor.",
        "Admissions give SIXTY. Reading 45 onto the admissions row would compute",
        "EARLY, and silence ADMITS under R. 59.01, so that is the single most",
        "consequential error available in this seed.",
        "",
        "== THE DEFENDANT FLOOR RUNS FROM 'THE EARLIER OF' TWO EVENTS ===========",
        "All three discovery rules measure the floor from the earlier of the",
        "defendant's appearance and service of process. A resolve_periods limb",
        "takes one event, so the caller supplies the EARLIER date and the event is",
        "named unmissably. Supplying the later date computes LATE.",
        "",
        "== WHAT IS DELIBERATELY NOT SEEDED =====================================",
        "No appellate rows. No backward rows -- R. 44.01(a) defines only a period",
        "that begins to run AFTER an act. No R. 44.01(c) motion-notice rows yet,",
        "though its five-day and one-day periods are the ones that would actually",
        "exercise the 'less than seven days' exclusion and are the obvious next",
        "addition. R. 55.25(c)'s 'no less than remains of the time' floor is not",
        "modelled and is disclosed on both rows it governs; it runs EARLY.",
    ],
    "rules": rules,
}

out = "sql/sairnlaw_deadline_seed_missouri.json"
ids = [r["rule_id"] for r in rules]
assert len(ids) == len(set(ids)), "duplicate rule_id"
with open(out, "w", encoding="utf-8") as f:
    json.dump(doc, f, indent=1, ensure_ascii=False)
    f.write("\n")
print("wrote", out, "with", len(rules), "rules")
for r in rules:
    marks = []
    if r.get("service_extension"):
        marks.append("ext")
    if r.get("service_completion"):
        marks.append("completion")
    print("  ", r["rule_id"], "eff", r["effective_from"], ("[" + "+".join(marks) + "]") if marks else "")
