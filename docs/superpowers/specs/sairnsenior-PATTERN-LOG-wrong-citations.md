# SAIRNsenior — pattern log: wrong citations

**Standing document, not a round.** Started 2026-08-31 after round 30. Append
here whenever a citation turns out to be wrong; do not bury it in a round.

**Round 30 said North Dakota was "the third wrong-citation incident". That was
wrong — it is the fourth, and only because two earlier ones had been forgotten
by the time round 30 was written.** That is precisely the argument for keeping a
log instead of counting from memory each time.

---

## The incidents

| # | Round | State | The citation used | What it actually was | How it was caught |
|---|---|---|---|---|---|
| 1 | 4 | **Tennessee** | 0720-11 | not the home care rule | scan of the fetched text |
| 2 | 15 | **Maine** | `title22ch1666` | **Appointment of Receivers** — right host, wrong chapter | the page loaded and read wrong |
| 3 | 20 / 26 | **North Dakota** | NDCC 23-17.5 | **Health Care Provider Cooperative Agreements [Repealed]** | reading the chapter |
| 4 | 25 | **South Dakota** | SDCL 34-12 | *Regulation of Hospitals and Related Institutions* — licenses institutions, **not home health** | reading the Title 34 chapter list |
| 5 | 30 | **North Dakota** *(resolution of #3)* | — | the live chapter is **NDCC 23-17.3, Home Health Agency Licensure** | reading the Title 23 chapter index |

**Not an incident, and recorded here so it is not miscounted again:**

- **Missouri, round 4 → corrected round 9.** 19 CSR 30-26 **really is** *Home
  Health Agencies*. The claim that it was a wrong citation **was itself wrong**;
  the actual failure was a scan that searched only for hour patterns, found none,
  and reported "nothing relevant". **A negative from a single pattern is a
  negative about that pattern.**

---

## What the five have in common

**Four of the five fetched cleanly.** Not one was caught by an HTTP status. A
wrong citation returns 200 and real legal text, which is why it survives longer
than a broken route: **a 404 argues with you, a wrong chapter agrees with you.**

**Three of the five were only caught by reading the parent index** — the title's
chapter list or the subchapter's section list — rather than by reading the
document that had been fetched. South Dakota is the expensive case: **eleven
endpoint forms were debugged across rounds 21–23 against a chapter that does not
regulate home health at all.** The transport was being fixed while the citation
was wrong.

**Two of the five were repealed chapters still serving text.** A repeal notice is
easy to read past when you were expecting substantive content.

## The rules that follow

1. **Confirm the citation from the parent index before investing in the
   transport.** Fetch the title's chapter list first. It is one request and it
   would have saved rounds 21–25 outright.
2. **Read the chapter heading you actually got, not the one you asked for.**
   Three incidents announce themselves in the first line of the document.
3. **A chapter name is not evidence.** Round 26 established the converse of this
   for *"Home Health Services"* chapters that turned out to be county finance
   (South Dakota 34-3A), public provision (West Virginia art. 2C) and repealed
   cooperative agreements (North Dakota 23-17.5). **Three chapters whose name
   promised licensure and delivered something else.**
4. **Check for `[Repealed]` and for an empty section list** — and, per round 28,
   **do not trust the index on that either**: Idaho's Chapter 24 renders zero
   sections and has eleven, and its Chapter 56 is labelled `[Repealed]` and is
   live. **Ask the section endpoint, with a known-bad control to prove the
   endpoint is honest.**
5. **When a state renumbers, every prior citation to it is suspect.** South
   Carolina moved its health regulations from **Chapter 61 to Chapter 60**
   (Chapter 61 is now *Department of Environmental Services*), so earlier
   `S.C. Reg. 61-⟨n⟩` health citations need re-checking. New Mexico repealed its
   whole home health chapter on **2024-07-01**, so any pre-July-2024 NM citation
   is stale.
6. **Log it here the same session it is found.** Round 30 got the count wrong
   from memory two rounds after the previous incident.
