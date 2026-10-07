# OWNER: cc
# OWNER-INTENDED BARE-RUN WRITER. A bare run of this tool WRITES, and that is
# its interface rather than a defect: see tools/bare_run_writers.py for the
# path it writes and why. tools/bare_run_write_check.py reads that list and
# does not flag the tools on it. If this tool stops being a generator, take it
# off the list in the same change -- an allowlist nobody re-derives is how a
# real defect hides inside a convention.
"""Build sql/sairnlaw_deadline_seed_massachusetts.json.

Every quote below was read VERBATIM on 2026-08-25 from the Massachusetts Rules
of Civil Procedure as published free and in full by the Trial Court Law
Libraries at mass.gov, and every effective_from is the rule page's OWN printed
"EFFECTIVE DATE" line.

ACCESS NOTE -- CORRECTED 2026-10-07 (cc), AND THE OLD TEXT IS NAMED RATHER THAN
DELETED. This docstring used to read "every mass.gov URL returns HTTP 403 to
curl and to plain fetches ... Do not conclude a Massachusetts rule is
unpublished from a 403." That was measured false on 2026-08-27: a BARE curl, no
user-agent and no Accept header, got 200 and the full rule text from
/civil-procedure-rule-6-time (253,869 B) and -rule-5-service (293,422 B). The
correction was written into the OUTPUT's own readme that day and never back
into this file, so the generator and the seed it generates disagreed for six
weeks about a measurable fact, and this docstring was the stale copy.

The GENERAL lesson the old paragraph drew is still worth keeping and is not
Massachusetts-specific: on a court site a 403 usually means "not a browser",
never "page does not exist". North Carolina's nccourts.gov has NOT been
re-tested and still stands as written; New Jersey's njcourts.gov is the live
case and a worse one, serving an anti-bot interstitial at HTTP 200.

    python tools/gen_ma_seed.py             # write the seed
    python tools/gen_ma_seed.py --check     # compare, write nothing
    python tools/gen_ma_seed.py --selftest  # can --check still FAIL?
"""
import json
import sys

def _emit_or_check(path, text, check=None):
    """Write `text` to `path`, or under `--check` compare and write NOTHING.

    READ-ONLY MODE, added 2026-10-07 (cc). This generator was one of 17 found
    to WRITE TO THE TREE on a bare run, measured by running each tool in an
    isolated worktree and asking `git status --porcelain` afterwards. Writing
    is this tool's job -- that is not the finding. The finding was that there
    was no way to ASK what it would write without letting it write.

    EXIT CODES: 0 identical, 1 drifted, 2 could not tell. A target that cannot
    be read is a third state and is never reported as drift, because "I could
    not compare" and "they differ" send a reader to different places.
    """
    import io as _io
    import os as _os
    import sys as _sys
    # `check` is a parameter and not only an argv sniff so that _selftest can
    # drive BOTH branches without touching sys.argv -- a selftest that has to
    # mutate global argv to reach the branch it tests is a second bug waiting.
    if check is None:
        check = '--check' in _sys.argv
    if not check:
        with _io.open(path, 'w', encoding='utf-8', newline='') as _fh:
            _fh.write(text)
        print('wrote ' + path)
        return 0
    if not _os.path.isfile(path):
        print('COULD NOT COMPARE: %s does not exist. This is not drift -- it '
              'is a missing target.' % path)
        return 2
    try:
        cur = _io.open(path, encoding='utf-8').read()
    except Exception as _e:
        print('COULD NOT COMPARE: %s is unreadable (%s). Not drift.'
              % (path, _e))
        return 2
    if cur == text:
        print('IDENTICAL: %s matches what this generator would write. '
              'Nothing written.' % path)
        return 0
    print('DRIFTED: %s differs from what this generator would write. '
          'Nothing written.' % path)
    print('  on disk  : %d bytes' % len(cur))
    print('  would be : %d bytes' % len(text))
    return 1


def _selftest():
    """Can `--check` still FAIL? Four arms, on a tempfile, never on the seed.

    THE DEFECT THIS GUARDS is cross-domain-disciplines item 8: a generator's
    `--check` compares a document to its own output, so the day the comparison
    stops working it reports IDENTICAL forever and nothing announces it. An
    exit 0 from `--check` is evidence only if the same comparison has just been
    seen to return 1 and 2.

    No arm touches sql/. Arm 2 perturbs a COPY by one byte -- which is also the
    smallest difference the comparison must not miss.
    """
    import contextlib
    import io
    import os
    import tempfile
    d = tempfile.mkdtemp(prefix='gen-ma-selftest-')
    p = os.path.join(d, 'target.json')
    body = '{"a": 1}\n'
    arms = []
    # Captured, not let through. Each arm's own message names the TEMP PATH,
    # which changes every run, so letting it through would make three runs of
    # a deterministic selftest print three different things -- and "3 identical
    # runs" is the evidence this batch reports. The verdicts are what matter
    # and they are asserted below.
    _sink = io.StringIO()
    _cap = contextlib.redirect_stdout(_sink)
    _cap.__enter__()

    open(p, 'w', encoding='utf-8', newline='').write(body)
    arms.append(('identical -> 0, and the target is not rewritten',
                 (_emit_or_check(p, body, check=True),
                  open(p, encoding='utf-8', newline='').read()),
                 (0, body)))

    arms.append(('ONE BYTE different -> 1, and the target is not rewritten',
                 (_emit_or_check(p, '{"a": 2}\n', check=True),
                  open(p, encoding='utf-8', newline='').read()),
                 (1, body)))

    os.remove(p)
    arms.append(('a missing target -> 2 COULD NOT COMPARE, never 1 drift',
                 (_emit_or_check(p, body, check=True), os.path.isfile(p)),
                 (2, False)))

    arms.append(('the write branch really does write',
                 (_emit_or_check(p, body, check=False),
                  open(p, encoding='utf-8', newline='').read()),
                 (0, body)))

    os.remove(p)
    os.rmdir(d)
    _cap.__exit__(None, None, None)
    lines, passed = [], 0
    for name, got, want in arms:
        ok = got == want
        passed += ok
        lines.append('  %-4s %s' % ('PASS' if ok else 'FAIL', name))
        if not ok:
            lines.append('       wanted %r, got %r' % (want, got))
    return passed, len(arms) - passed, lines


_KNOWN_FLAGS = ('--check', '--selftest')

# ── AN UNRECOGNISED FLAG MUST NOT MEAN "WRITE" (2026-10-07, cc) ─────────────
# Same defect, same day, different file: tools/role_gate_mc_config.py
# recognised one flag and fell through to the write path for everything else,
# so `--help` regenerated two spec files. This generator had the identical
# shape, over a LEGAL DEADLINE SEED. The guard runs before anything is built
# and before any open(..., 'w'), and it is placed here rather than in a shared
# helper because there is no shared helper and inventing one mid-batch is a new
# tool. Routed as a methodology rule, not left as three local fixes.
_unknown = [a for a in sys.argv[1:] if a not in _KNOWN_FLAGS]
if _unknown:
    print('COULD NOT RUN -- argument not recognised: %s' % _unknown[0])
    print('Nothing was written. Recognised: %s' % ', '.join(_KNOWN_FLAGS))
    sys.exit(2)

if '--selftest' in sys.argv:
    _p, _f, _lines = _selftest()
    print('selftest: %d/%d arm(s) pass -- can --check still FAIL?'
          % (_p, _p + _f))
    for _ln in _lines:
        print(_ln)
    sys.exit(1 if _f else 0)


BASE = "https://www.mass.gov/rules-of-civil-procedure/"
URL = {
    "6": BASE + "civil-procedure-rule-6-time",
    "12": BASE + "civil-procedure-rule-12-defenses-and-objections-when-and-how-presented-by-pleading-or-motion-motion-for-judgment-on-pleadings",
    "33": BASE + "civil-procedure-rule-33-interrogatories-to-parties",
    "34": BASE + "civil-procedure-rule-34-producing-documents-electronically-stored-information-and-tangible-things-or-entering-onto-land-for-inspection-and-other-purposes",
    "36": BASE + "civil-procedure-rule-36-requests-for-admission",
}
RETRIEVED = "2026-08-25"

# Per-rule currency, read from each rule page's own printed EFFECTIVE DATE.
# Real per rule, like Virginia -- NOT the blanket date New Jersey and North
# Carolina both carry and disclose.
EFF = {
    "6": "2023-12-01",
    "12": "2008-07-01",
    "33": "2009-08-01",
    "34": "2016-08-01",
    "36": "1974-07-01",
}

EXT = {
    "standard": "ma_rcp_6d",
    "add": 3,
    "unit": "calendar_days",
    "applies_when": ["mail", "email", "electronic", "efiling_service_provider"],
    "note": (
        "Mass. R. Civ. P. 6(d) adds three days for service by mail AND by electronic means -- "
        "\"by mail, by e-mail pursuant to Rule 5(b)(1), or otherwise electronically, including through "
        "the Electronic Filing Service Provider pursuant to Rule 7(b) of the Massachusetts Rules of "
        "Electronic Filing\". THE ELECTRONIC LIMB IS THE OPPOSITE OF FRCP 6(d), which stopped "
        "extending for electronic service in 2016, and wider than North Carolina's 6(e), which reaches "
        "mail and only mail. Do not narrow this by analogy to either. \"Added to the prescribed "
        "period\", so the days lengthen the period and one rollover runs at the end."
    ),
}

NO_EXT_RULE4 = (
    "NO SERVICE EXTENSION. R. 6(d) extends a period run after \"the service of a notice or other "
    "papers upon the party\", which is Rule 5 service between parties; a summons and complaint go out "
    "under Rule 4. Same scope route as West Virginia, North Carolina, Washington, New Jersey and "
    "Virginia."
)

Q_12A1 = ("After service upon him of any pleading requiring a responsive pleading, a party shall serve "
          "such responsive pleading within 20 days unless otherwise directed by order of the court.")

Q_12A2 = ("The service of a motion permitted under this rule alters this period of time as follows, "
          "unless a different time is fixed by order of the court: (i) if the court denies the motion "
          "or postpones its disposition until the trial on the merits, the responsive pleading shall be "
          "served within 10 days after notice of the court's action; (ii) if the court grants a motion "
          "for a more definite statement, the responsive pleading shall be served within 10 days after "
          "the service of the more definite statement.")

Q_33A3 = ("The party upon whom the interrogatories have been served shall serve answers and objections, "
          "if any, within 45 days after the service of the interrogatories. The court may, on motion "
          "with or without notice, specify a shorter or longer time. Unless otherwise specified, "
          "further answers to interrogatories shall be served within 30 days of the entry of the order "
          "to answer further. ... The party upon whom the interrogatories have been served shall serve "
          "the answers or objections either within 30 days from the date of service of the final "
          "request or prior to the filing of an application for a final judgment for relief or "
          "dismissal, whichever is later.")

Q_33A4 = ("In the event that answers or objections have not been received and after the expiration of "
          "40 days from the date of service of the final request for answers, or such further time as "
          "the parties may agree upon in writing or the court may allow, the interrogating party may "
          "file a written application for entry of final judgment for relief or dismissal. The period "
          "of time set forth in the previous sentence shall be deemed to include the three day period "
          "allowed pursuant to Rule 6(d).")

Q_34B2A = ("The party upon whom the request is served shall serve a written response within 30 days "
           "after the service of the request, except that a defendant may serve a response within 45 "
           "days after service of the summons and complaint upon that defendant. The court may allow a "
           "shorter or longer time.")

Q_36A = ("The matter is admitted unless, within 30 days after service of the request, or within such "
         "shorter or longer time as the court may allow, the party to whom the request is directed "
         "serves upon the party requesting the admission either (1) a written statement signed by the "
         "party under the penalties of perjury specifically (i) denying the matter or (ii) setting "
         "forth in detail why the answering party cannot truthfully admit or deny the matter; or (2) a "
         "written objection addressed to the matter, signed by the party or his attorney, but, unless "
         "the court shortens the time, a defendant shall not be required to serve answers or objections "
         "before the expiration of 45 days after service of the summons and complaint upon him.")


def rule(rid, label, trigger, count, cite, quote, note, eff_key, ext=None):
    r = {
        "rule_id": rid,
        "jurisdiction": "ma",
        "domain": "civil-litigation",
        "label": label,
        "trigger_event": trigger,
        "count": {"value": count, "unit": "calendar_days", "direction": "forward"},
        "computation": "ma_rcp_6a",
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
    return r


def later_of(rid, label, tid, ev_a, n_a, lab_a, ev_b, n_b, lab_b, cite, quote, note, eff_key):
    return {
        "rule_id": rid,
        "jurisdiction": "ma",
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
        "computation": "ma_rcp_6a",
        "authority": {
            "citation": cite, "url": URL[eff_key], "quote": quote, "note": note,
            "retrieved_at": RETRIEVED,
        },
        "effective_from": EFF[eff_key],
        "effective_to": None,
        "version": 1,
        "supersedes": None,
    }


rules = [
    rule("ma-r-12-a1-answer-to-complaint",
         "Answer to a complaint after service of the summons and complaint (Massachusetts)",
         "service_of_summons_and_complaint", 20,
         "Mass. R. Civ. P. 12(a)(1)", Q_12A1,
         "TWENTY DAYS, the shortest answer period of any jurisdiction seeded except Washington's 20, "
         "and shorter than the federal 21, Virginia's 21, the 30 of North Carolina, West Virginia and "
         "Georgia, and New Jersey's 35. Read from the rule, not inferred from a neighbour. "
         "RULE 12(a)(1) IS WRITTEN GENERALLY -- \"any pleading requiring a responsive pleading\" -- so "
         "it governs the answer to a complaint AND the response to a counterclaim or crossclaim. The "
         "two are separate rows here because they differ on the ONE thing the engine must get right: "
         "how the pleading was served. This row is the Rule 4 branch. " + NO_EXT_RULE4 + " "
         "\"UNLESS OTHERWISE DIRECTED BY ORDER OF THE COURT\" -- an order the engine cannot see "
         "displaces this row entirely.",
         "12"),

    rule("ma-r-12-a1-responsive-pleading-to-pleading-served-under-rule-5",
         "Responsive pleading to a counterclaim, crossclaim or other pleading served under Rule 5 (Massachusetts)",
         "service_of_pleading_requiring_responsive_pleading", 20,
         "Mass. R. Civ. P. 12(a)(1)", Q_12A1,
         "THE SAME 20 DAYS AS THE ANSWER TO A COMPLAINT, AND THE SAME SENTENCE OF THE RULE -- the "
         "difference is service, not period. A counterclaim or crossclaim is served on a party already "
         "in the case under Rule 5, which is exactly what R. 6(d) reaches, so THE EXTENSION APPLIES "
         "HERE where it does not on the answer to the complaint. Splitting one rule into two rows on "
         "this basis is the same treatment West Virginia's 12(a)(1)(A)/(B) pair gets; Massachusetts "
         "writes it as one sentence, so the split is ours and is recorded rather than implied.",
         "12", EXT),

    rule("ma-r-12-a2i-responsive-pleading-after-motion-denied",
         "Responsive pleading after the court denies a Rule 12 motion or postpones it to trial (Massachusetts)",
         "notice_of_court_action_denying_or_postponing_rule_12_motion", 10,
         "Mass. R. Civ. P. 12(a)(2)(i)", Q_12A2,
         "TEN DAYS, AND IT RUNS FROM NOTICE OF THE COURT'S ACTION -- not from entry of the order, and "
         "not from service of anything by a party. That is a real difference from Virginia's R. 3:8(b), "
         "whose equivalent period runs from ENTRY, and the trigger is named for notice so a caller "
         "cannot supply an entry date by accident. "
         "THIS IS A RE-TRIGGER IN SUBSTANCE: R. 12(a)(2) says the motion \"alters this period of time\", "
         "replacing the 20-day period rather than adding to it. It is seeded as its own row with its "
         "own trigger rather than as a retrigger clause, because the engine's retrigger mechanism "
         "substitutes a trigger DATE within one rule and this is cleaner read as a separate period. "
         "NO SERVICE EXTENSION: R. 6(d) extends a period run after service of a notice or paper BY A "
         "PARTY; notice of the court's own action is neither. "
         "TEN DAYS IS NOT SHORT ENOUGH FOR THE EXCLUSION -- R. 6(a) excludes intermediate weekends and "
         "holidays only when the period is \"less than 7 days\", so all ten days count.",
         "12"),

    rule("ma-r-12-a2ii-responsive-pleading-after-more-definite-statement",
         "Responsive pleading after service of a more definite statement (Massachusetts)",
         "service_of_more_definite_statement", 10,
         "Mass. R. Civ. P. 12(a)(2)(ii)", Q_12A2,
         "TEN DAYS FROM SERVICE OF THE MORE DEFINITE STATEMENT, which is a paper served by a party "
         "under Rule 5 -- so unlike its sibling limb (i), which runs from notice of the court's action, "
         "THIS ONE DOES TAKE THE R. 6(d) EXTENSION. The two limbs sit in the same sentence of the same "
         "subsection and differ on exactly this point; they are separate rows for that reason and not "
         "for tidiness. Same distinction New Jersey draws inside R. 4:6-1(b).",
         "12", EXT),

    rule("ma-r-33-a3-interrogatory-answers",
         "Answers and objections to interrogatories (Massachusetts)",
         "service_of_interrogatories", 45,
         "Mass. R. Civ. P. 33(a)(3)", Q_33A3,
         "FORTY-FIVE DAYS -- THE LONGEST FIRST INTERROGATORY PERIOD OF ANY JURISDICTION SEEDED (New "
         "Jersey 60 is longer only on its production rule; Virginia 21, North Carolina 30, Washington "
         "30). Read from the rule. "
         "MASSACHUSETTS HAS NO DEFENDANT FLOOR ON INTERROGATORIES, and that is the finding worth "
         "keeping: R. 34(b)(2)(A) and R. 36(a) BOTH give a defendant 45 days from service of the "
         "complaint, and R. 33 gives none. Four of the five states seeded with discovery rows carry a "
         "defendant floor on all three devices; Massachusetts carries it on two of three. A later_of "
         "row for interrogatories would invent a period the rule does not grant, so there is none. "
         "SERVICE EXTENSION APPLIES: interrogatories are served under Rule 5. "
         "\"THE COURT MAY ... SPECIFY A SHORTER OR LONGER TIME\" -- an order the engine cannot see.",
         "33", EXT),

    rule("ma-r-33-a3-answers-after-final-request",
         "Answers after service of a final request for answers to interrogatories (Massachusetts)",
         "service_of_final_request_for_answers", 30,
         "Mass. R. Civ. P. 33(a)(3)", Q_33A3,
         "THIRTY DAYS FROM SERVICE OF THE FINAL REQUEST. THE RULE'S OTHER LIMB IS DELIBERATELY NOT "
         "MODELLED AND THE OMISSION IS SAFE: the full text is \"either within 30 days from the date of "
         "service of the final request OR prior to the filing of an application for a final judgment "
         "for relief or dismissal, WHICHEVER IS LATER.\" The second limb turns on whether and when the "
         "other side files an application -- an event the engine cannot see and that may never happen. "
         "Because the rule takes the LATER of the two, the 30-day date is a FLOOR: the true deadline is "
         "this date or later, never earlier. So computing the 30-day limb alone reports EARLY, never "
         "late, which is the safe direction. A caller must not read this date as a guarantee that the "
         "right to answer has expired -- it has not, until an application is actually filed. "
         "SERVICE EXTENSION APPLIES: the final request is served under Rule 5.",
         "33", EXT),

    rule("ma-r-33-a4-application-for-final-judgment",
         "Earliest date to apply for final judgment for failure to answer interrogatories (Massachusetts)",
         "service_of_final_request_for_answers_for_application", 40,
         "Mass. R. Civ. P. 33(a)(4)", Q_33A4,
         "FORTY DAYS, AND THE RULE FORBIDS THE SERVICE EXTENSION IN ITS OWN WORDS: \"The period of time "
         "set forth in the previous sentence shall be deemed to include the three day period allowed "
         "pursuant to Rule 6(d).\" The three days are ALREADY INSIDE the 40. Adding them again would "
         "extend a deadline the rule does not extend, so this row carries NO service_extension at all "
         "-- deliberately, not by omission. THIS IS THE FIRST SEEDED ROW ANYWHERE IN THIS ENGINE WHERE "
         "A RULE EXPRESSLY ABSORBS ITS OWN SERVICE EXTENSION; do not 'fix' it by adding one. "
         "IT IS ALSO NOT A DEADLINE BUT AN EARLIEST DATE -- the period must EXPIRE before the "
         "interrogating party MAY file. Nothing is lost by filing later. The label says so, because a "
         "date presented as a deadline when it is a floor invites the opposite mistake. "
         "\"OR SUCH FURTHER TIME AS THE PARTIES MAY AGREE UPON IN WRITING OR THE COURT MAY ALLOW\" -- "
         "an agreement or order the engine cannot see displaces this row.",
         "33"),

    rule("ma-r-34-b2A-production-response",
         "Written response to a request for production (Massachusetts)",
         "service_of_request_for_production", 30,
         "Mass. R. Civ. P. 34(b)(2)(A)", Q_34B2A,
         "THIRTY DAYS. This row is the PLAIN limb, for a party who is not a defendant taking the "
         "45-day floor -- see the -defendant-later-of-periods row for that. "
         "NOTE THE ASYMMETRY WITH R. 33, which is 45 days with NO defendant floor: Massachusetts is "
         "NOT internally consistent across its discovery rules the way Virginia is (21/21/21). Each "
         "rule was read on its own; none of these numbers was carried from a sibling. "
         "SERVICE EXTENSION APPLIES: the request is served under Rule 5. "
         "R. 34(c) governs production from NON-PARTIES via Rule 45 and is NOT seeded.",
         "34", EXT),

    later_of("ma-r-34-b2A-production-response-defendant-later-of-periods",
             "Written response to a request for production served on a defendant (Massachusetts)",
             "production_request_on_defendant",
             "service_of_request_for_production_on_defendant", 30, "30 days after service of the request",
             "service_of_summons_and_complaint_for_production", 45,
             "45 days after service of the summons and complaint on that defendant",
             "Mass. R. Civ. P. 34(b)(2)(A)", Q_34B2A,
             "A DEFENDANT GETS THE LATER OF THE TWO PERIODS. \"except that a defendant may serve a "
             "response within 45 days after service of the summons and complaint\" is a floor under the "
             "30-day period, not a replacement for it: a request served with the complaint leaves 45 "
             "days, a request served three months into the case still leaves 30 from its own service. "
             "30/45 IS THE SAME PAIR GEORGIA USES (O.C.G.A. 9-11-36(a)(2)), and Georgia's is the pair "
             "that was once encoded as an ordinary later_of and shipped a date FIFTEEN DAYS EARLY -- "
             "which is exactly why resolve_periods exists and why this row uses it. "
             "NO SERVICE EXTENSION ON THIS ROW. The plain limb carries one and this one deliberately "
             "does not: no seeded rule combines resolve_periods with a service extension, the engine "
             "has never been exercised on that combination, and inventing the interaction here -- does "
             "the extension lengthen one limb or both, before or after the later-of resolves -- would "
             "be guessing at an order no rule text settles. Compute the plain limb and compare by hand.",
             "34"),

    rule("ma-r-36-a-admission-response",
         "Answer or objection to a request for admission (Massachusetts — unanswered matters are ADMITTED)",
         "service_of_request_for_admission", 30,
         "Mass. R. Civ. P. 36(a)", Q_36A,
         "THIRTY DAYS, AND SILENCE ADMITS. The rule is written as an automatic consequence -- \"The "
         "matter is admitted unless, within 30 days after service of the request ... the party ... "
         "serves ...\" -- so a missed date is not a sanctionable lapse but a substantive admission, the "
         "same structure Ohio Civ.R. 36(A)(1) and Va. Sup. Ct. R. 4:11(a) carry, and the reason this "
         "label says so out loud. This row is the PLAIN limb. "
         "SERVICE EXTENSION APPLIES: the request is served under Rule 5. "
         "\"OR WITHIN SUCH SHORTER OR LONGER TIME AS THE COURT MAY ALLOW\" -- an order the engine "
         "cannot see, and here it can make the period SHORTER.",
         "36", EXT),

    later_of("ma-r-36-a-admission-response-defendant-later-of-periods",
             "Answer or objection to a request for admission served on a defendant (Massachusetts)",
             "admission_request_on_defendant",
             "service_of_request_for_admission_on_defendant", 30, "30 days after service of the request",
             "service_of_summons_and_complaint_for_admission", 45,
             "45 days after service of the summons and complaint on that defendant",
             "Mass. R. Civ. P. 36(a)", Q_36A,
             "A DEFENDANT GETS THE LATER OF THE TWO PERIODS, on the same 30/45 pair as production, but "
             "R. 36(a) PHRASES IT AS A PROHIBITION rather than a permission: \"a defendant shall not be "
             "required to serve answers or objections before the expiration of 45 days after service of "
             "the summons and complaint upon him\". Same arithmetic as its production sibling, opposite "
             "grammar -- the identical pairing Virginia has between R. 4:9(b)(ii) and R. 4:11(a). "
             "\"UNLESS THE COURT SHORTENS THE TIME\" QUALIFIES THE 45-DAY FLOOR SPECIFICALLY, not the "
             "30-day period. Not modelled -- the engine cannot see the order -- but a caller relying on "
             "the 45-day limb should confirm none was entered. THE STAKES ARE HIGHER HERE THAN ON THE "
             "PRODUCTION ROW because silence admits. "
             "NO SERVICE EXTENSION ON THIS ROW, for the reason given on the production sibling.",
             "36"),
]

doc = {
    "_readme": [
        "MASSACHUSETTS CIVIL DEADLINE RULES -- 11 rows, Rules 12, 33, 34 and 36.",
        "",
        "== SOURCE ==============================================================",
        "Read verbatim on 2026-08-25 from the Massachusetts Rules of Civil",
        "Procedure, published free and in full by the Trial Court Law Libraries,",
        "Massachusetts Court System, at mass.gov. No paywall and no redirect to a",
        "commercial publisher -- the failure mode that blocked Kentucky outright",
        "and gated Arizona out is absent here.",
        "",
        # The 2026-08-27 correction. It was applied to the OUTPUT by hand and
        # never back into this generator, so for six weeks `--check` reported
        # DRIFT and a regeneration would have reinstated the superseded
        # paragraph -- i.e. re-published, as current, a 403 claim that had been
        # measured false. The correction is kept VERBATIM, including the
        # original wording it quotes, because the Suffolk-county reasoning
        # further down this readme was written against that wording.
        "ACCESS -- CORRECTED 2026-08-27. THIS PARAGRAPH USED TO SAY THE OPPOSITE, AND",
        "ACTING ON THE OLD VERSION WASTES A BROWSER-AUTOMATION SETUP. It read: 'every",
        "mass.gov URL returns HTTP 403 to curl and to plain fetches, including its",
        "/doc/.../download PDF links, while a real browser gets 200 ... Re-reads need",
        "Playwright or equivalent.' THAT IS NO LONGER TRUE FOR THE RULE PAGES.",
        "",
        "Re-tested 2026-08-27 on a BARE curl -- no user-agent, no Accept header:",
        "  /rules-of-civil-procedure/civil-procedure-rule-6-time     200, 253,869 B",
        "  /rules-of-civil-procedure/civil-procedure-rule-5-service  200, 293,422 B",
        "Full rule text, no browser needed. The bare index path",
        "mass.gov/rules-of-civil-procedure 404s, but that is a URL that does not exist",
        "rather than a block -- do NOT read it as the old 403 returning.",
        "",
        "THE GENERAL LESSON THE OLD PARAGRAPH DREW IS STILL WORTH KEEPING even though",
        "its Massachusetts example expired: on a court site a 403 usually means 'not a",
        "browser', never 'page does not exist'. North Carolina's nccourts.gov was the",
        "other example and has NOT been re-tested here, so it still stands as written.",
        "NEW JERSEY IS NOW THE LIVE CASE OF THIS SHAPE, and a worse one -- njcourts.gov",
        "serves an anti-bot interstitial at HTTP 200. See its seed readme.",
        "",
        "The original wording follows, kept because the Suffolk-county reasoning below",
        "was written against it. Same shape",
        "as North Carolina's nccourts.gov. Re-reads need Playwright or equivalent.",
        "",
        "== effective_from IS REAL ON EVERY ROW =================================",
        "Each rule page prints its own EFFECTIVE DATE and amendment history:",
        "  R. 6 -> 2023-12-01   R. 12 -> 2008-07-01   R. 33 -> 2009-08-01",
        "  R. 34 -> 2016-08-01  R. 36 -> 1974-07-01",
        "Virginia's situation, not New Jersey's or North Carolina's blanket date.",
        "",
        "== THE HOLIDAY QUESTION IS ANSWERED IN THE RULE'S OWN TEXT =============",
        "Mass. R. Civ. P. 6(a) says 'legal holiday' includes those days specified",
        "in Mass. G.L. c. 4, s. 7 -- an EXPRESS cross-reference, like Washington's",
        "CR 6(a) -> RCW 1.16.050 and unlike Texas, Arizona and Kentucky. So",
        "Massachusetts does NOT join the bundled lawyer's question.",
        "",
        "== BUT THE HOLIDAY LIST IS COUNTY-SCOPED, WHICH IS NEW =================",
        "Cl. 18 makes Evacuation Day (17 March) and Bunker Hill Day (17 June)",
        "legal holidays 'with respect to SUFFOLK COUNTY ONLY'. A calendar is keyed",
        "by jurisdiction and year and cannot express that, so the statewide list is",
        "encoded and the Suffolk gap is DISCLOSED on every Massachusetts result.",
        "Including them would roll thirteen counties LATE; omitting them can only",
        "run EARLY in Suffolk -- and since the same clause requires Suffolk offices",
        "to stay open on both days, the omission may simply be correct. Suffolk",
        "County is BOSTON. See JURISDICTION_COVERAGE in api/_lib/deadline-engine.js.",
        "",
        "== R. 6(d) EXTENDS FOR ELECTRONIC SERVICE, UNLIKE THE FEDERAL RULE =====",
        "Three days for mail AND for e-mail, other electronic service, and the",
        "Electronic Filing Service Provider. FRCP 6(d) stopped extending for",
        "electronic service in 2016 and North Carolina's 6(e) never did. Four",
        "method names are accepted: mail, email, electronic, efiling_service_provider.",
        "",
        "== ONE ROW REFUSES THE EXTENSION BY THE RULE'S OWN WORDS ===============",
        "R. 33(a)(4)'s 40-day period 'shall be deemed to include the three day",
        "period allowed pursuant to Rule 6(d)'. The three days are already inside",
        "the 40, so that row carries no service_extension. First row in the engine",
        "where a rule absorbs its own extension. Do not 'fix' it.",
        "",
        "== WHAT IS DELIBERATELY NOT SEEDED =====================================",
        "No appellate rows (Mass. R. App. P. is a separate body of rules with its",
        "own time rule and needs its own read). No backward rows -- R. 6(a) defines",
        "only a period that begins to run AFTER an act, and says nothing about",
        "counting backward from a hearing. No Rule 45 non-party subpoena rows. No",
        "interrogatory defendant-floor row, because R. 33 grants no such floor.",
    ],
    "rules": rules,
}

out = "sql/sairnlaw_deadline_seed_massachusetts.json"
ids = [r["rule_id"] for r in rules]
assert len(ids) == len(set(ids)), "duplicate rule_id"
_text = json.dumps(doc, indent=1, ensure_ascii=False) + "\n"
_rc = _emit_or_check(out, _text)
# ── THE VERDICT HAS TO REACH THE EXIT CODE (2026-10-07, cc) ────────
# The first version assigned `_rc` and never used it, so `--check`
# printed DRIFTED and exited 0 -- a wrong number that looks
# authoritative, which is the exact defect this platform keeps
# paying for. Only the --check path exits here: the normal write
# path still falls through to the summary prints below it.
if '--check' in sys.argv:
    sys.exit(_rc)
print("wrote", out, "with", len(rules), "rules")
for r in rules:
    print("  ", r["rule_id"], "eff", r["effective_from"])
