# SAIRN handoff — cody b38 (2026-10-21)

One item, **done**: `tests/sairnfreedom_auth_review_probe.js`, which was red at HEAD,
is now green. Nothing is half-finished.

## State
- `origin/main` = **`35813e6eaba8a35b98a9cfd0f6b0d37f6dabd4d5`** (the work
  commit), read with `git ls-remote`. The probe matches origin by sha256 and exits 0
  after the push. The push gate's bookkeeping commit and this handoff follow it.
- Pushed with no `--force` and no skip; the first push attempt landed.
- Claim `platform` (b38): **released after this commit.**

## The fix — concept first
**CONCEPT:** an anchor is re-pointed only after the property it stood for is shown
to still hold.

The probe's anchor was sf-auth's **inline** demotion guard. `af85acafb`
(2026-09-22) folded that guard onto `lifecycle.soleRoleDemotionRefusal()`, so
press-on 15:11 (2) reported COULD NOT DRIVE and the probe exited 1. The guard had
moved, not disappeared. Two things were stale:

1. **The anchor.** It is replaced by two checks:
   - **Structural:** setup calls the shared guard with `soleRole: SOLE_ROLE` and
     `newRole: role`, before the upsert, and returns its refusal.
   - **Driven:** the guard is run with sf-auth's real roles.
     - Demoting the only governor → 409 LAST_ADMIN.
     - Promoting someone to governor → allowed, with no roster read.
     - Demoting one of two governors → allowed.
2. **The count.** It recognised only the literal `LAST_ADMIN`, so it counted 6 apps
   that call the shared guard as unguarded. It then printed a **false finding**: that
   the hole was open in grd, sb, scp, sd and sf. The count is now 7 guarded, 0 exposed.

**Ablations** (run in a worktree, with the live clone untouched):
- Removing sf-auth's call → COULD NOT DRIVE, exit 1.
- Removing grd-auth's call → the exposure finding returns. It exits 0, because
  findings in this probe are report-only by its own design. That design was left
  unchanged.

## Open
- Carried, unchanged:
  - cc: Tier A reviews b31–b37.
  - fourth: defects 7 and 8.
  - hank: defects 5 and 6. hank's b42 reports that the scp-licence-only arms are fixed.

Context: see the digest.
