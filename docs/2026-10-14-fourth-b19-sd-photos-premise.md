# The `sd_photos` premise, measured from source before anything acts on it

**fourth, batch b19, 2026-10-14. SOURCE ONLY — no SQL was run, no endpoint was
called, no browser was opened.** Every figure below is read from a file at a
named line or computed arithmetically from two such figures. **What needs the
database to settle is in §5 under UNVERIFIED and is not folded into anything
else.**

**WHY THIS IS A SEPARATE DOCUMENT AND WHY IT COMES BEFORE THE FIX.** My b18
spec (`docs/2026-10-14-ai-safeguards-spec.md` §7.6.1) asserted a provenance gap
on `sd_photos` and then added, as its own caveat, that *"it is possible that no
`sd_photos` row has ever landed and that the failure has been reporting itself
as an unprovisioned table."* **That caveat makes the main finding conditional,
and nobody had measured which way the condition falls.** Acting on the spec
while the condition is open means either fixing a provenance gap on rows that do
not exist, or fixing a size failure that was filed as a footnote. **So the
premise gets measured first.**

---

## 1. THE THREE MEASUREMENTS

### 1.1 The row-size cap — **65,536 bytes on `data::text`**

```
CMD sed -n '334,344p' sql/stonedesk_data_schema.sql
  334  create table if not exists public.sd_photos (
  ...
  339    data jsonb not null default '{}'::jsonb,
  ...
  343    constraint sd_photos_data_size check (octet_length(data::text) <= 65536)
```

**It is not a `sd_photos` peculiarity.** `grep -n "octet_length" sql/stonedesk_
data_schema.sql` shows the same 65,536-byte constraint on `sd_invoices`,
`sd_drawings`, `sd_remakes`, `sd_fin_jobs`, `sd_pricing_rules`,
`sd_negotiated_prices`, `sd_order_history`, `sd_inventory` and more — **a
house convention applied uniformly across the StoneDesk tables.** That matters
for the routing: the cap is almost certainly correct for every one of those
*except* the one table whose rows carry an image.

### 1.2 What the client puts in that column — **the whole base64 data URL, unmodified**

```
CMD sed -n '25988p' stonedesk.html
  25988  const validFiles = files.filter(f => f.type.startsWith('image/') && f.size <= 10*1024*1024);

CMD sed -n '25999p' stonedesk.html
  25999          data: e.target.result,
```

`e.target.result` is the `FileReader` result for the accepted file. **There is no
downscale, no re-encode, no thumbnailing and no strip anywhere between the read
and the sync** — `grep` over `stonedesk.html` for a strip/omit of `data` before
the write returns nothing relevant. The field goes onto the row as captured, and
`sdSyncCollection` pushes **the whole changed row**.

So the accepted input is **up to 10,485,760 bytes of binary**, and what lands in
`data` is that binary **base64-encoded**, which is a 4/3 expansion plus a
`data:image/jpeg;base64,` prefix.

### 1.3 The arithmetic — **the cap is exceeded by any image over roughly 48 KB**

```
cap on data::text                                   65,536 bytes
minus the data-URL prefix 'data:image/jpeg;base64,'     −23
minus the other seven fields' JSON overhead (id, job,
  cat, name, size, date, plus braces/quotes/commas)    ≈ −300
                                                   ─────────────
base64 characters available                         ≈ 65,213
binary bytes that fit  (× 3/4)                      ≈ 48,909
```

**~48.9 KB of image.** A phone photo is 2–5 MB. **The client accepts files up to
10 MB — a factor of roughly 214 above what the row can hold at the ceiling, and
every real photograph is above the threshold.** The only images that fit are
tiny: a small icon, a heavily compressed screenshot.

### 1.4 What happens to the rejection — **it is reported as the wrong thing**

```
CMD sed -n '14263p' api/sd-data.js
  14263  if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED',
         message: 'StoneDesk data tables are not set up yet — run sql/stonedesk_data_schema.sql in Supabase first.' } }); return; }
```

A Postgres CHECK violation arrives as **400**. That branch folds 400 in with
404 and answers **`503 NOT_PROVISIONED` — "tables are not set up yet"**. **The
table exists and is correctly provisioned; the row is too big.** The diagnosis
is not merely unhelpful, it points the reader at a migration they have already
run.

**And this is not one site.** `grep -n "status === 404 || r.status === 400"
api/sd-data.js` returns **twelve** matching branches across the file, plus a
second StoneDesk-worded one at `:14642`. **Every resource whose rows can exceed
its cap inherits the same misattribution**, so this is a pattern and not a typo.

### 1.5 How loudly the client reports it — **console only. No toast, no banner.**

```
CMD api/sd-data.js      -> 503
CMD stonedesk.html  sdData(): `_sdLastStatus[resource] = res.status;`
                             `_sdReadFailed[resource] = true;`
                             `sdDataFailed(action, resource, 'the server answered ' + res.status)`
                             `return null;`
CMD stonedesk.html  sdDataFailed(): one `console.warn(...)` and nothing else
CMD stonedesk.html  sdSyncCollection(): on `saved === null`,
    `console.warn('StoneDesk backup: "'+key+'" record '+r.id+' did NOT reach the
     server. It is saved on this device only.')`
```

**The platform's own machinery is better than average here and still not enough.**
`sdData` distinguishes three states deliberately — its comments say *"401/403 is
'you may not have this', which is a different fact from 'there is none of this'"*
and *"a 404, a 500 or a 502 is 'we could not ask', which is a third fact again"*
— and `sdSyncCollection`'s comment states the principle exactly: *"silence would
make a backup that is not happening look like one that is."*

**But both reports are `console.warn`.** `sdDataFailed` has no other body. **No
toast, no banner, no badge, nothing in the UI.** The user sees the photo in the
panel with its `🧠 Done` badge, because the local write already succeeded, and
nothing anywhere tells them the server copy does not exist.

---

## 2. WHICH HALF IS THE URGENT DEFECT

**THE SIZE FAILURE. Not the provenance gap. And the margin is not close.**

| | the size failure | the provenance gap |
|---|---|---|
| **who it affects** | **every photo over ~48.9 KB — i.e. every real photograph** | only photos that are *small enough to land*, which today is nearly none |
| **what is lost** | **the backup. The row does not exist on the server at all** | a provenance field on a row that does exist |
| **how it presents** | **a success in the UI and a `console.warn` nobody reads** | the text renders unlabelled |
| **what the error says** | *"tables are not set up yet"* — **a wrong diagnosis pointing at a migration already run** | n/a |
| **reversible?** | the local copy survives, so no data is destroyed — **but the backup's whole purpose is the device being lost** | fully reversible by a later stamp |
| **blast radius beyond `sd_photos`** | the 400→503 misattribution is in **twelve branches** of `api/sd-data.js` | one resource |

**AND THE TWO ARE NOT INDEPENDENT, WHICH IS THE PART THAT CHANGES THE ORDER OF
WORK.** The provenance gap is **live only for rows that land**, and today that
is the near-empty set of sub-48 KB images. **So the b18 spec's §7.6.1 was
describing a defect that is, for almost all real photos, latent behind a second
one.** The moment the size failure is fixed — by any route — **every photo
begins landing and the provenance gap becomes universal on the same day.**

**Therefore: fix the size failure first, and land T17's `ai_source` stamp in
the same change or before it.** Fixing size alone converts a latent provenance
gap into a live one at full volume. That sequencing is the actionable output of
this measurement and it is the opposite of what the b18 spec's ordering implied.

**One thing I will not overstate:** the provenance gap is **not** zero today. A
small enough image does land, with `aiAnalysis` carrying raw model text and no
`ai_source` — so T17 is a real arm against a real (if rare) row, not a
hypothetical. **It is live but low-volume; the size failure is live and
total.**

---

## 3. ROUTED TO hank — four items, in this order

**`api/`, `sql/` and `*.html` are hank's. This document writes none of them.**

1. **DECIDE WHERE THE IMAGE LIVES, and it is a design call, not a constant
   bump.** Raising `65536` lets multi-megabyte base64 blobs into a `jsonb`
   column that every read of that resource pulls back — the cap is a house
   convention on a dozen tables and it is right for all of them except this
   one. **The three options, with the argument for each stated so the decision
   is visible rather than inherited:** (a) **downscale client-side** before
   `data:` is set — a 1024px JPEG at q0.7 is comfortably under 48 KB and the
   analysis is a QC note, not forensics, so the information loss is probably
   acceptable; (b) **separate the blob from the row** — object storage or a
   dedicated table with the row holding a key, which is the shape the rest of
   the platform would want eventually; (c) **raise the cap for `sd_photos`
   only**, with a number chosen against a measured photo-size distribution and
   not against the 10 MB client limit. **I recommend (a) as the smallest change
   that makes the backup real, with (b) named as the direction of travel.** It
   is hank's call and I am not making it.
2. **STOP THE 400→503 MISATTRIBUTION.** A 400 is not a 404. Separate them in
   the `sd_photos` branch at minimum, and preferably in all twelve: a CHECK
   violation should answer something the reader can act on — *"this record is
   too large to back up"* — not *"run the migration"*. **This is independently
   worth doing even if item 1 takes a week**, because it converts a wrong
   diagnosis into a right one at no behavioural cost.
3. **MAKE THE FAILURE VISIBLE TO A HUMAN.** `sdDataFailed` is a single
   `console.warn`. The function already receives `action`, `resource` and
   `why`; a toast or a persistent panel marker is a small change in one place.
   **The platform's own comment — *"silence would make a backup that is not
   happening look like one that is"* — is the argument, and it is already
   written in the file.**
4. **THEN T17.** `ai_source: 'claude:photo-qc'` per the b18 spec §7.6.1, landing
   with or before item 1 for the reason in §2.

**ROUTED TO cody — one arm, and it must fail today:** a `sd_photos` write whose
`data` field exceeds the cap must **not** produce `503 NOT_PROVISIONED`. That is
the failing-first form of item 2 and it is checkable without a database by
driving the branch's status mapping directly.

---

## 4. WHAT THIS CORRECTS IN MY OWN b18 SPEC

**§7.6.1's caveat was right to exist and wrong in its weighting.** It filed the
size constraint as *"ONE THING THIS SPEC DOES NOT CLAIM, because it was not
run"*, beneath a provenance finding presented as the main event. **Measured, the
subordinate clause is the live defect and the main finding is mostly latent
behind it.**

**The caveat did say the right thing in its last sentence** — *"if the row never
lands, the provenance gap is latent rather than live, and the size failure is
the more urgent half"* — **so b18 named the correct conclusion as a
possibility and then ordered the document the other way round.** That is the
error worth recording: a conditional stated honestly and then not resolved
leaves the reader to act on the ordering rather than on the condition.

**No edit to §7.6.1's content is needed and none is made** — its facts hold.
**What it needs is this document cited beside it**, which §5 of the b19 handoff
does.

---

## 5. UNVERIFIED — what needs the database, named and not folded into anything above

**Everything in §1–§4 is read from source. These four need SQL or a live
request, and none of them is assumed:**

1. **Whether `public.sd_photos` exists in the live database at all.** The
   schema file creates it `if not exists`; whether anybody has run that file
   against production is not a source fact. **If the table is absent, the 404
   leg of that branch is firing and `NOT_PROVISIONED` is the CORRECT answer** —
   which would make item 2 above a misdiagnosis of a misdiagnosis. **I consider
   this unlikely** (the resource is wired end to end, in `SD_SYNCED`, in
   `SD_LOCAL_RESOURCES`, and in `api/_resources/stonedesk.js`) **and I cannot
   rule it out from source.**
2. **Whether any `sd_photos` row has ever landed.** `select count(*) from
   public.sd_photos` settles it in one line. **If the count is zero, the
   provenance gap has never been live and §2's ordering is not merely
   preferable but mandatory.**
3. **The real distribution of `octet_length(data::text)` on rows that DID
   land.** That is the number item 1(c) would need, and it is the difference
   between a guess at a new cap and a measurement.
4. **Whether the 503 has ever been seen by a user as "tables are not set up
   yet".** Server logs, not source.

**One more limit, stated because it bounds §1.3 rather than §5:** the ~300-byte
JSON overhead in the arithmetic is an estimate from the row's field list, not a
measurement of a real row. **The threshold is therefore ~48.9 KB ± a few
hundred bytes, which does not change any conclusion** — a 2 MB photo misses the
cap by a factor of 40 either way — but the number should not be quoted as
exact.
