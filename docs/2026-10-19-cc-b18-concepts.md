# cc b18 — the concept for each fix, stated BEFORE the code

**This file is committed before the commits that implement it**, deliberately,
so the ordering is provable from `git log` rather than asserted here. The ask
was to state what the fix should actually *do* before writing it, for the two
items where the temptation is to start editing: a cell that renders wrongly,
and a check whose subject is a renderer.

---

## Item 1 — the board's CONTEXT cells

**One line: a CONTEXT cell carries a measured percentage and nothing else — so
parse the figure out of whatever the digest says and print the figure, and when
no figure is parseable print UNKNOWN with the reason, never the prose that
happened to follow the label.**

What that rules out, and why each matters:

- **Not "truncate it shorter."** The current cell is already truncated — to 120
  characters in the section and 40 in the table — and truncation is what makes
  it *look* like a value. `46% WHAT LANDED -- fourth's b26, four ro` is a
  figure welded to a paragraph and cut mid-word; a shorter slice is a smaller
  weld.
- **Not "fix the digests."** Measured first:
  `digest_fields()` returns a CONTEXT body of **4,673 characters for hank b17
  and 10,717 for cody b22**, because the parse runs from the `CONTEXT` label to
  the next *recognised* label and those digests continue with unlabelled
  section headings of their own. The parse is behaving as written. The board
  is a **reader** of other agents' files and cannot require them to be shaped
  differently — a renderer that is only correct when its input is perfect is
  the board's problem, not theirs.
- **Not a silent repair.** If the body carries no percentage, the cell must say
  so with the reason, because a cell that quietly prints `0%` or an empty
  string is the fabricated-value shape this platform has a Guardian check for.

**The honest limit, stated now rather than after:** extracting a figure cannot
tell a *stale* figure from a current one. The cell already names its source
(`live status row` vs `digest bN`) and that stays the only thing distinguishing
them.

---

## Item 2 — "the rendering check uses markdown-it, not GitHub"

**One line: a claim about how a file renders must be measured against the
renderer that actually serves it — so drive the same fragment through GitHub's
own Markdown API and compare, and then either the b17 UNVERIFIED closes or the
b17 verdict was wrong and gets corrected in the same breath.**

What that rules out:

- **Not "read the GFM spec and reason about it."** The spec is evidence about
  what GitHub *should* do. The b17 measurement already agreed with the spec,
  and the thing left unverified was whether the real renderer agrees with
  both — which is exactly the gap a spec cannot close.
- **Not "add more local presets."** Two markdown-it presets already agree.
  A third library agreeing is a second copy of the same opinion, and
  convention 6 of `docs/2026-09-13-cross-domain-disciplines.md` is explicit
  that independence needs a *structurally different* method. GitHub's API is
  the different method: it is the render target itself.
- **Not asserting the flag belongs where the dispatch put it.** The dispatch
  attached this flag to `status_board_bridge_check.py`. **It does not live
  there** — the markdown-it measurement was b17 item 4, about
  `index_duplicate_check.py` and the open-work index's table rows. Said plainly
  rather than worked around, and the bridge check's *own* unverifieds (the
  90-second staleness tolerance, and the mount-is-not-the-API limit) are the
  ones that get hardened under item 2 instead.

**The result is a fork, and both branches are reportable:** agreement closes a
standing UNVERIFIED and retires hank's routed note for good; disagreement means
cc told hank his premise was false on the strength of a library, and the
correction goes in the digest's own DECISION-NEEDED rather than a footnote.
