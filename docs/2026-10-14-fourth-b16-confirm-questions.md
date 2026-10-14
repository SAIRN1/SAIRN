# THE TEN QUESTIONS — plain English, one page, each a yes or no — 2026-10-14

**WHAT THIS IS.** Ten questions the software cannot answer about itself. They
came out of three access-control specs written on 2026-10-14 for SAIRNlegacy
(funeral homes), SAIRNvet (veterinary practices) and SAIRNlaw (law firms).
**Each one decides who can read or change something in the app, so each one is
answered yes or no, not discussed.**

**WHO ANSWERS WHAT.** Three are legal questions and go to counsel. Seven are
"how does your business actually work" questions and go to a funeral director
or a veterinary practice manager. **Nobody here can answer any of the ten by
reading the code**, which is why they are marked rather than guessed.

**WHAT HAPPENS WITH THE ANSWERS.** Each answer sets one row in a permission
table. A `yes` and a `no` both produce working software; **an unanswered
question produces software that guesses, and today it guesses "everyone can do
everything".**

---

## FOR COUNSEL — three legal questions

### C1 — SAIRNlegacy · the `prep` (embalming) role · YES or NO

**Is embalming a separate licence from funeral directing, such that the
software must treat "licensed embalmer" as its own permission level rather than
as ordinary staff?**

* **If YES:** `prep` becomes a licensed tier, like the veterinary app already
  does for prescribers, and only that tier may sign preparation records.
* **If NO:** `prep` is an ordinary task role and the director signs.

*Why we are asking:* the app currently has three roles — owner, director,
staff — and everybody who is not the owner or a director is "staff", with the
same access as the owner.

### C2 — SAIRNlegacy · `leg_cremations` · YES or NO

**Does a cremation authorisation require two named people to be recorded, or is
one authorised person enough?**

* **If YES:** the software asks for a second named approver before the record
  can be completed, the way the veterinary app already does for witnessed
  controlled-substance entries.
* **If NO:** one director's name is recorded and the record completes.

*Why we are asking:* this is the least reversible action in the app, and it
currently requires no particular role at all.

### C3 — SAIRNlaw · the proposed `paralegal` role · YES or NO

**May a paralegal PREPARE a trust-account disbursement for an attorney to
authorise, or must a lawyer both prepare and authorise it?**

* **If YES:** a paralegal may create the entry and an attorney or the owner
  authorises it — two steps, two people.
* **If NO:** the whole action is lawyer-only and the paralegal cannot start it.

*Why we are asking:* the trust ledger is the sharpest record in the app. Today
**every role can write to it**; only the reconciliation screen is restricted,
and that restriction is to the firm owner alone.

---

## FOR A FUNERAL DIRECTOR — five questions about how the business runs

### F1 — SAIRNlegacy · the proposed `arranger` role · YES or NO

**Is there a person who takes the arrangement conference and sells merchandise
who is NOT a licensed funeral director?**

* **If YES:** `arranger` becomes its own role — can build the invoice and sell
  merchandise, cannot sign what a director signs.
* **If NO:** the director does it and no new role is created.

*Also tell us what you call that person* — arranger, counselor, advisor,
pre-need counselor. The software will use your word.

### F2 — SAIRNlegacy · the proposed `office` role · YES or NO

**Does the person who does billing, insurance assignments and filing need to
see the death records and cremation records as well?**

* **If YES:** `office` reads those records and writes the money ones.
* **If NO:** `office` is money and filing only, and the records stay with the
  director.

*Also tell us the name you use* — office manager, administrator, bookkeeper.

### F3 — SAIRNlegacy · the proposed `apprentice` role · YES or NO

**Do apprentices (or interns, or trainees) log into the software themselves?**

* **If YES:** `apprentice` becomes a role that can read everything a director
  reads and sign nothing.
* **If NO:** they work on a director's screen and no role is created.

### F4 — SAIRNlegacy · the proposed `livery` role · YES or NO

**Are your drivers and pallbearer staff YOUR employees, with their own logins?**

* **If YES:** `livery` becomes a role that sees the schedule, the vehicles and
  the procession, and nothing else.
* **If NO** (they are a contracted service): no login, no role, and the
  question of what they can see disappears.

### F5 — SAIRNlegacy · `leg_liverybookings` and `leg_liveryvendors` · YES or NO

**Do you invoice the family for livery through the funeral home?**

* **If YES:** those two records are money records and only the owner, the
  director, the arranger and the office may change them.
* **If NO** (the livery company bills the family direct): they are scheduling
  records and more people can touch them safely.

---

## FOR A VETERINARY PRACTICE MANAGER OR OWNER — two questions

### V6 — SAIRNvet · the `manager` role (practice manager) · YES or NO

**Does your practice manager need to open clinical records — exam notes, lab
results, imaging — to do their job?**

* **If YES:** `manager` reads clinical records and cannot write them.
* **If NO:** `manager` is money, scheduling and staffing only.

*Why we are asking:* the software's own notes say a practice manager is not a
clinician, but a manager who cannot open a visit cannot answer a client's
question about that visit's bill. **We have spec'd "read yes, write no" as the
least surprising answer and it is the one most likely to be wrong.**

### V7 — SAIRNvet · the `tech` role · `sv_controlled` · YES or NO

**Under your state board's rules, may a veterinary technician RECORD a
controlled-substance administration that a veterinarian ordered?**

* **If YES:** `tech` may write the controlled register, and the veterinarian's
  name is recorded as the prescriber alongside the technician's as the
  administering person.
* **If NO:** only the owner or a veterinarian may write it, which is what the
  software does today.

*Why we are asking:* this is the one record in SAIRNvet that is already
restricted — to the owner and veterinarians — and in many practices the
technician is the person who actually gives the dose and writes it down.

---

## ONE MORE, NOT COUNTED IN THE TEN — for a law-firm administrator

**SAIRNlaw · the proposed `bookkeeper` role · YES or NO: is your bookkeeping
done by an employee, or by an outside firm?**

* **If an employee:** `bookkeeper` becomes a role — time, invoices and the
  operating account, and **not** the client files.
* **If outsourced:** it may need a scoped external login instead of an employee
  record, which is a different piece of work.

*It is listed separately because it is an org-chart question rather than one of
the ten access decisions, and because it is neither a legal question nor one a
funeral home or veterinary practice can answer.* **Today a firm with three
roles either gives its bookkeeper an attorney login — handing a non-lawyer
every client file — or gives a paralegal the trust ledger. The software offers
no third answer.**

---

## WHAT WE ARE NOT ASKING

* **Nothing about AI.** The AI wording package is a separate sheet and a
  separate conversation.
* **Nothing that needs a decision today.** Each answer unblocks one permission
  row; the rest of the work proceeds without it.
* **No role names from us where you have your own.** Where the app already uses
  your words — owner, director, attorney, paralegal, DVM, technician — we kept
  them. Everything we invented is marked above with "proposed".

**WHERE THE DETAIL LIVES, if anybody wants it:**
`docs/2026-10-14-fourth-b15-sairnlegacy-role-matrix.md`,
`docs/2026-10-14-fourth-b15-sairnvet-role-matrix.md` and
`docs/2026-10-14-fourth-b15-sairnlaw-role-matrix.md`. Those are written for
engineers; this sheet is the whole of what needs answering.
