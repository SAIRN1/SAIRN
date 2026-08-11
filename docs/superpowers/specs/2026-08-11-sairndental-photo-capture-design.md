# SAIRNdental — Guided Photo-Capture (Public Booking) Design

**Status:** Design drafted 2026-08-11, pending review. Not yet implemented.

Concrete design for a guided photo-capture step in the public,
unauthenticated booking flow (`sairndental-book.html` +
`api/sairndental/public-book.js`). **Zero AI involvement** — this is
storage and display only; no `api/claude` call anywhere in this
feature, and no clinical interpretation of the photo's content by
anything but the dentist. Seven real design questions resolved
directly with Michael before writing this (one corrected mid-review —
recorded below with the correction, not silently overwritten).

## 0. Design questions, resolved

**Photo required — optional, not required.** Matches how every other
field beyond name/dob/phone/slot already works in this flow; a patient
who can't or won't attach a photo must still be able to submit a real
booking request.

**Photo count — up to 3 per request**, not 1. More context for the
dentist (e.g. multiple angles of a swelling or a broken tooth) at the
cost of a slightly more involved capture UI and a larger (but still
bounded, §2) payload.

**Compression budget — a new, more generous per-photo budget (~300KB
target), not the platform's existing ~64KB convention.** StoneDesk's
stone-photo uploader compresses hard to fit inside `api/sd-data.js`'s
generic 64KB write-payload check — but `public-book.js` talks directly
to Supabase, not through that checked path, and 64KB compressed down to
roughly 220px would likely be too low-resolution for a dentist to
genuinely assess a clinical concern. A new, explicit budget and a new,
explicit server-side size check (§2) are both required specifically
because this endpoint has no size protection today for any field.

**Capture-prompt content — generic and universal, not per-procedure-
type.** One fixed set of on-screen steps for every request. Zero
AI/logic needed to select wording, and no risk of a procedure-specific
prompt implying clinical guidance the practice never actually wrote.
Per-procedure-type prompts would be new content the practice would
need to author and maintain — real scope this request didn't ask for.

**Staff review location — a thumbnail added to the existing Pending
Requests panel, not a new dedicated panel.** (Corrected during review:
an earlier draft of this section briefly stated the opposite —
recording the correction here, not just silently fixing it, since it
shaped the "Staff side" section below.) The existing Pending Requests
panel already lists self-scheduled bookings awaiting confirmation —
exactly the review step this photo needs, with no new nav entry or
panel required. **A genuinely new, standalone per-patient photo-history
panel (independent of any single booking) was raised during this
review and deliberately deferred** — logged in `SAIRN-BACKLOG.md`
2026-08-11 as real, bigger, separately-valuable future scope, not
folded into this pass.

**EXIF/GPS metadata — stripped client-side, verified not assumed.**
Canvas-based re-encoding (already required for the compression budget)
mechanically drops all EXIF data, including GPS tags, as a structural
property of how `<canvas>` re-encoding works — the pixel data is
redrawn from scratch, no original file bytes (where EXIF lives) carry
into the output. Stated here as a real, testable claim (§4), not an
assumption.

**Text field — a short optional "anything you'd like the dentist to
know?" field, alongside the photos.** Genuinely useful context
adjacent to the photo capture; flagged as scope beyond the literal
photo-capture request when raised, approved explicitly rather than
folded in silently.

## 1. Flow change — `sairndental-book.html`

A new step, `step-photo`, inserted between the existing `step-details`
(patient info: name/dob/phone/email) and `step-done`. The "Request
This Appointment" button moves from `step-details` (which becomes a
"Continue" button, no submission) to the end of the new photo step.
`step-photo` contains:
- Fixed instructional text (e.g. "Find good lighting, hold the camera
  steady, and get close to the area of concern.") — same wording for
  every request (§0).
- Up to 3 "Add Photo" tiles, each backed by
  `<input type="file" accept="image/*" capture="environment">`. A
  selected file is compressed client-side (§2) and rendered as a
  thumbnail with a remove (×) control. A 4th tile never appears once 3
  photos are attached.
- One optional text field, `bk-notes` (short, single-line or small
  textarea), for the "anything you'd like the dentist to know?" note.
- The real submit button (renamed from "Request This Appointment",
  same handler concept as today's `submitBooking()`), working
  identically whether 0 or 3 photos and whether the note is filled in
  or blank — nothing in this step is a hard blocker (§0).

`submitBooking()`'s POST body to `BOOK_API` gains two new optional
fields: `photos` (array of compressed data-URL strings, `[]` if none)
and `patient_notes` (string, `''` if blank).

## 2. Client-side compression + server-side size enforcement

**Compression:** each selected photo is drawn onto an off-screen
`<canvas>` and re-encoded via a downscale + JPEG-quality-reduction
ladder targeting a ~300KB budget for the base64 string length (same
technique as StoneDesk's `bsuCompressUnderBudget`, different target —
see that function, `stonedesk.html:6456`, for the proven ladder shape:
progressively smaller max-dimension + lower quality steps, measured
against the actual base64 string length since that's what the JSON
payload cost really is, not the decoded byte size).

**Server-side size check — new, since none exists today.**
`public-book.js` currently has zero payload-size protection for any
field (it talks directly to Supabase, bypassing `api/sd-data.js`'s
generic 64KB check entirely). A client that skips or tampers with the
compression step could otherwise push an arbitrarily large payload
through a fully unauthenticated endpoint. New check, run immediately
after the existing required-field validation and before any database
read/write: reject (400, `PHOTOS_TOO_LARGE`) if the combined base64
length of all `photos` entries exceeds ~1.2MB (headroom above 3 ×
~400KB, allowing some margin above the client's 300KB target without
allowing a genuinely abusive payload through). Also reject (400,
`INVALID_PHOTO`) if any `photos` entry isn't a well-formed
`data:image/...;base64,...` string — never attempt to write malformed
data into the appointment record.

## 3. Data model — no new resource, no SQL migration

`photos` (array of data-URL strings) and `patient_notes` (string) are
new keys inside the same `dnt_appointments` JSONB `data` object
`public-book.js` already constructs (`appointmentData.photos`,
`appointmentData.patient_notes`) — the identical no-SQL-migration
pattern used for the email-reminders and fee-schedule features. No new
table, no new `sd-data.js` resource entry, no promoted column (neither
field needs an index, uniqueness, or a fast server-side lookup).

## 4. Staff side — `sairndental.html`

The existing Pending Requests panel (`rPending()`) gains, per row:
photo thumbnails (if `a.photos` is a non-empty array — click to view
full-size) and the patient note (if `a.patient_notes` is non-empty,
shown inline as plain escaped text). A request with no photos or no
note renders exactly as it does today — nothing new appears for the
common case. No new panel, no new nav entry (§0, corrected).

## 5. Error handling

- **Client, non-image file selected:** some browsers allow a file past
  `accept="image/*"` regardless. Validate `File.type` starts with
  `image/` before attempting to draw it to canvas; show a real inline
  message ("That doesn't look like an image — try again.") and don't
  add a broken tile.
- **Client, compression can't reach the 300KB target even at the most
  aggressive ladder step:** same "best effort" behavior as
  `bsuCompressUnderBudget` — submit the smallest attempt achieved
  rather than blocking the patient, but the server-side size check
  (§2) still enforces the hard ~1.2MB combined ceiling regardless, so
  a pathological image can't slip through just because the client gave
  up early.
- **Server, payload over the size ceiling:** 400 `PHOTOS_TOO_LARGE`,
  checked before any DB call — never a partial write, never a vague
  500. Client shows the real message ("Photos are too large — try
  retaking with better lighting or removing a photo.").
- **Server, malformed photo data:** 400 `INVALID_PHOTO`, same
  fail-fast-before-any-DB-call placement.
- **Existing 409 `SLOT_TAKEN` race:** unchanged — photos/notes are
  just additional fields in the same appointment write `public-book.js`
  already guards with the Postgres `EXCLUDE` constraint; if the slot
  was taken, nothing is written (photos included) and the patient sees
  the existing message, same as today.
- **Existing network-failure path (`submitBooking()`'s try/catch):**
  unchanged — the whole booking, photos and note included, rides in
  one POST already covered by the existing "Could not connect" retry
  message.
- **Staff side, malformed/missing `a.photos`:** `rPending()`'s render
  must treat a missing, non-array, or empty `photos` field as "no
  photos" and render nothing extra — never throw on an unexpected
  shape.

## 6. Non-goals (explicit scope cuts, this pass)

- No AI interpretation of photo content anywhere (hard constraint).
- No per-procedure-type capture instructions (§0).
- No required photo (§0).
- No photo editing/cropping UI beyond the capture-and-compress step.
- No standalone per-patient photo-history panel — logged as a real,
  separate, deferred feature in `SAIRN-BACKLOG.md` (§0).

## 7. Testing

- **EXIF-strip verification (the real test for §0's privacy claim):**
  run a real photo with known EXIF GPS tags through the compression
  function, inspect the resulting data URL's decoded bytes for the
  absence of an EXIF `APP1` segment/GPS IFD — confirms the claim
  directly rather than trusting canvas re-encoding's general
  reputation for stripping metadata.
- **Compression budget test:** representative sample images (a few
  different real-world sizes/qualities) each land at or under the
  ~300KB base64-length target after the ladder runs, matching
  `bsuCompressUnderBudget`'s own verification style.
- **Size-ceiling enforcement test (server):** submit a combined
  `photos` payload over ~1.2MB, confirm a clean 400 `PHOTOS_TOO_LARGE`
  and — critically — confirm no appointment record was created at all
  (no orphaned/partial write).
- **Malformed-photo rejection test (server):** submit a `photos` entry
  that isn't a valid data URL, confirm 400 `INVALID_PHOTO`, not a
  crash or a 500.
- **Optional-field regression test:** submit a booking with `photos:
  []` and `patient_notes: ''` (today's exact behavior, pre-feature),
  confirm it still succeeds identically — this feature must not break
  the existing required-field-only booking path.
- **Max-count test:** confirm the UI never allows a 4th photo tile to
  appear.
- **Non-image file test (client):** attempt to select a non-image
  file, confirm the real inline rejection message and no tile added.
- **Staff-side render test:** Pending Requests panel with (a) a
  request that has photos and a note, (b) a request with neither
  (today's normal case), (c) a request with a malformed `photos` field
  — confirms graceful handling of all three, no thrown error on (c).
- **Existing-behavior regression:** confirm the pre-existing 409
  `SLOT_TAKEN` and 400 missing-required-field paths in `public-book.js`
  are unchanged by this feature's additions.
- Standard structural checks (`checkblocks.py`, `div_balance_check.py`,
  `duplicate_global_check.py` on `sairndental.html`; `node --check` on
  every modified/new `.js` file) + Push Protocol on every file touched.
