# Item 97 cold review, and the resource-map class the array scanner cannot see

**2026-09-15 (Fourth).** Two things, and the second came out of the first.

1. An independent cold read of item 97 (SAIRNcode's seven Tier A records moved
   from a destroying `delete` to `soft_delete`), against three named questions.
2. The pinned-list-drift technique applied to a **fresh target** — object-literal
   resource maps — which produced a negative result worth publishing.

---

## 1. The cold read: all three questions come back clean

I had not touched SAIRNcode today, which is the point of asking me.

### Q1 — does the read filter exclude marked rows on all seven, and only those seven?

**Yes, by construction rather than by a second list.**
`api/sd-data.js:11827` is `scIsSoftDeleteOnly(resource) ? '&data->>_deleted_at=is.null' : ''`,
and `scIsSoftDeleteOnly` reads `tierASoftDeleteOnly` imported from
`api/_resources/sairncode.js` — the same array the registry derives
`extraActions` from. There is no second copy to drift.

**And it is the only read path.** `isSc(resource)` gates one branch
(`api/sd-data.js:11814`). The three bespoke `resource === 'sc_…'` branches
(`sc_settings` ×2, `sc_auth_requests`) are all inside the WRITE action, and none
of them is among the seven. So there is no route that returns an sc_* row
without passing the filter.

**The other 21 are deliberately unfiltered**, and the file says why: they
hard-delete, so no row of theirs ever carries the marker, and adding the clause
would be a predicate that can only ever be true.

### Q2 — did repointing the seven client call sites miss one?

**No.** Measured, not read: 27 delete-ish call sites in `sairncode.html`, cross-
checked against the registry in both directions.

| | result |
|---|---|
| Call sites whose verb disagrees with the registry | **0** |
| Of the seven, sites still calling `delete` | **0** |
| Of the seven, resources with no call site at all | **0** |

### …and the question behind Q2, which is whether the filter is ever reached

My first pass looked for `scData('read', 'sc_…')` and found **none**, which
would have meant the server filter was correct and unreached. **That was wrong,
and the correction matters:** the client reads these through
`scSyncOneResource(resource)` at login, where the resource is a *variable*, so a
literal-string grep cannot see it. It reads the server list and, when non-empty,
**overwrites localStorage with it** — so a soft-deleted row genuinely does not
come back on another device. The fix is not cosmetic.

That made the next question obvious, and it is the one level deeper than Q2
asked: **is every one of the seven actually in the sync map?** A resource missing
from `SC_RESOURCE_STORAGE_KEYS` would never re-read from the server at all.

**All seven are present, and the map matches the registry exactly — 28 ↔ 28,
neither direction short.**

### Q3 — is the register ↔ list agreement enforced in both directions?

**Yes, and I drove it rather than reading it.** `tests/sairncode_gates.js:305`
asserts sorted set-equality between the register's Tier A `sc_*` rows and
`tierASoftDeleteOnly`, with a control arm proving the register parse is non-empty
so the comparison cannot pass vacuously.

Driven in a throwaway worktree, three ways:

| Planted drift | Suite |
|---|---|
| **A** — drop `sc_denial_events` from the code list | RED |
| **B** — add a NON-Tier-A name (`sc_dme`) to the code list | RED |
| **C** — tier `sc_dme` **A in the register** and change no code | RED |

Direction C is the one usually only claimed. A tier decision recorded in the
register cannot silently fail to reach the gate.

**Nothing found. Recorded as a clean review rather than a null result** — the
three questions were the right ones and the answers are all specific.

---

## 2. The fresh target: object-literal resource maps

`tools/pinned_list_drift_check.py` scans for literal **arrays** of resource
names, and its own closing note lists what it does not claim to cover. It does
not mention object literals, and `SC_RESOURCE_STORAGE_KEYS` — the map Q2's
deeper question turned on — is one.

**Measured: 35 object literals across the repo are keyed by three or more
registered resource names.** The ten per-app ones were compared against their
registries in both directions:

| Map | App | map / registry |
|---|---|---|
| `SV_RESOURCES` | sairnvet | 41 / 41 ✅ |
| `LEG_RESOURCES` | sairnlegacy | 36 / 36 ✅ |
| `SF_RESOURCES` | sairnfreedom | 35 / 35 ✅ |
| `SC_RESOURCE_STORAGE_KEYS` | sairncode | 28 / 28 ✅ |
| `SDN_RESOURCES` | sairndesign | 18 / 18 ✅ |
| `SB_RESOURCES` | sairnbiz | 13 / 13 ✅ |
| `BLD_RESOURCES` | sairnbuild | 30 / 32 |
| `SD_LOCAL_RESOURCES` | stonedesk | 21 / 36 |
| `DNT_RESOURCES` | sairndental | 17 / 25 |
| `LAW_RESOURCES` | sairnlaw | 15 / 19 |

### The four "drifts" are all partial ON PURPOSE, and reporting them as findings would have been wrong

Every missing name has its own bespoke branch. `bld_bids` and `bld_tna` are
named in `sairnbuild.html`'s own header as the only two with server sync before
the backup work; `dnt_settings`, `dnt_appointments` and `dnt_rollup` each have a
dedicated handler; StoneDesk's map is called `SD_LOCAL_RESOURCES` and the file
says the other fifteen have no delete path.

`pinned_list_drift_check.py`'s header warned about exactly this: *"Most partial
lists on this platform are partial ON PURPOSE with a reason written beside
them."* **Membership is the wrong question.**

### The invariant that IS right, and it holds

The envelope gate accepts a resource **because it is in the registry**, so
something downstream has to serve it. A registered resource served by neither
the generic map nor a bespoke branch is a 400 from an unreachable branch — the
failure `checkEnvelope`'s own header records having been found the hard way.

    registered resources        : 393
    served by a generic map     : 243
    served by a bespoke branch  : 145
    served by a registry list   :  28

    SERVED BY NOTHING VISIBLE   :   0

**Zero of 393.** Published because the method is new even though the result is
clean: a negative result from a check nobody had run is information, and the next
person should not have to re-derive it to find out.

**One thing recorded and not raised as a finding:** 20 resources are served by
BOTH a generic map and a bespoke branch. That is not wrong — the bespoke branch
returns first — but it is the shape where ORDER decides behaviour, and a bespoke
branch moved below its generic map would change what runs with no other symptom.
Named here so the next reader does not have to re-derive it.

---

## 3. What this does NOT claim

- **Nothing was run against a live database.** The read filter is verified by
  construction and by the suites; that a soft-deleted row is absent from a real
  PostgREST response has not been observed here.
- **The coverage figure counts branches that EXIST, not branches that are
  CORRECT.** A resource served by a branch that refuses everything would count
  as served.
- **The 35-map census is of object literals keyed by resource names.** Maps
  keyed by something else — roles, table names, verbs, file paths — have the
  same failure shape and are outside this pass, the same exclusion
  `pinned_list_drift_check.py` names for itself.
