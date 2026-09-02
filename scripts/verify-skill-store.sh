#!/usr/bin/env bash
# scripts/verify-skill-store.sh
# Detects drift between the three places a SAIRN skill can live. Read-only —
# reports, never repairs, because a silent auto-repair is how the original
# drift went unnoticed for a day.
#
# THE LAYOUT (established 2026-08-25)
#   canonical : C:/SAIRN/skills/sairn/<name>/      real content, outside every
#                                                  git working tree. What
#                                                  Claude Code actually loads.
#   global    : ~/.claude/skills/<name>            symlink -> canonical
#   repo      : .claude/skills/<name>/             real, TRACKED content.
#                                                  The version-controlled copy
#                                                  and the reviewable one.
#
# WHY NOT ~/.agents/skills/sairn/, which was the obvious precedent:
#   the ENTIRE home directory is inside a git working tree —
#   `git -C ~/.agents/skills rev-parse --show-toplevel` prints C:/Users/marsh,
#   the stale checkout of this repo that is already flagged for retirement.
#   Putting the canonical store there would have reproduced the exact
#   anti-pattern the move was meant to escape, and `git clean -xdn` in that
#   checkout confirmed it: "Would remove .agents/skills/sairn/".
#   C:/SAIRN is outside every working tree; verified, not assumed.
#
# STILL EXPOSED, and not fixable from here: ~/.claude/skills/ IS that stale
# checkout's tracked .claude/skills/ directory — the user-level skill store
# and the checkout are literally the same path. A `git restore` or
# `git checkout .` in C:/Users/marsh would overwrite the symlinks below with
# 33-commit-old skill content. Only retiring that checkout closes it; see the
# open row in docs/SAIRN-OPEN-WORK-INDEX.md. Losing the symlinks is loud and
# cheap to rebuild (re-run the ln loop); losing canonical content is not,
# which is why canonical moved out and the symlink farm stayed.
#
# WHY THE REPO COPY IS NOT ALSO A SYMLINK — checked, not assumed:
#   git stores a symlink as mode 120000 whose blob is the literal target path,
#   and this machine has core.symlinks=false, so a fresh checkout writes a
#   one-line TEXT FILE containing an absolute C:/Users/... path instead of a
#   directory. Symlinking the repo copies would delete 21 skills' tracked
#   content, hardcode a machine-local path into the repo, and break
#   .claude/skills/ in every other clone. Verified in a scratch repo before
#   this layout was chosen.
#
# The cost of that decision is exactly what this script exists to catch:
# repo and canonical are two real copies and can drift.
#
# Usage:  bash scripts/verify-skill-store.sh
# Exit:   0 = clean, 1 = drift found

set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

REPO="$PWD/.claude/skills"
CANON="/c/SAIRN/skills/sairn"
GLOBAL="$HOME/.claude/skills"
fail=0

[ -d "$REPO" ]  || { echo "FAIL: no repo skills dir at $REPO"; exit 1; }
[ -d "$CANON" ] || { echo "FAIL: no canonical store at $CANON"; exit 1; }

# 1. Same set of skills in repo and canonical.
only_repo=$(comm -23 <(ls -1 "$REPO" | sort) <(ls -1 "$CANON" | sort))
only_canon=$(comm -13 <(ls -1 "$REPO" | sort) <(ls -1 "$CANON" | sort))
[ -n "$only_repo" ]  && { echo "DRIFT: in repo, missing from canonical:"; echo "$only_repo" | sed 's/^/  /'; fail=1; }
[ -n "$only_canon" ] && { echo "DRIFT: in canonical, missing from repo:";  echo "$only_canon" | sed 's/^/  /'; fail=1; }

# 2. Identical content, both directions (catches an edit to either copy).
#
# COMPARED AFTER NORMALISING LINE ENDINGS -- corrected 2026-09-01.
#
# This used `cmp -s`, a RAW byte compare, and was therefore PERMANENTLY RED.
# The repo is checked out CRLF (git autocrlf) and the canonical store holds LF,
# so every file that has ever been synced differs by exactly its line endings
# and nothing else. Measured at the time of this fix: sairn-guardian-v2
# (76561 vs 75344 bytes) and sairn-contract-drafter (11970 vs 11727) both
# reported "content differs" and both were byte-identical once normalised.
#
# That is not a cosmetic complaint. This script ALSO reports real findings --
# ten skills present in the repo and missing from canonical, twelve global
# entries that are copies rather than symlinks -- and a check that is red no
# matter what buries them. A tool people learn to skim is a tool that stops
# working, which is the same lesson as the reachability checker having to end
# its own output with "needs a read before you believe it".
#
# Fifth CRLF false alarm of this session; CLAUDE.md's own note says to treat it
# as a known instrument error rather than rediscover it a sixth time.
norm_cmp() {
  # Returns 0 when the two files match ignoring CR. Uses tr rather than dos2unix
  # so it works in a bare Git-Bash with no extra tooling installed.
  [ "$(tr -d '\r' < "$1" | sha256sum | cut -d' ' -f1)" = \
    "$(tr -d '\r' < "$2" | sha256sum | cut -d' ' -f1)" ]
}
files=0
for s in $(ls -1 "$REPO"); do
  [ -d "$CANON/$s" ] || continue
  for f in $(cd "$REPO/$s" && find . -type f); do
    files=$((files+1))
    norm_cmp "$REPO/$s/$f" "$CANON/$s/$f" || { echo "DRIFT: content differs: $s/$f"; fail=1; }
  done
  for f in $(cd "$CANON/$s" && find . -type f); do
    [ -f "$REPO/$s/$f" ] || { echo "DRIFT: only in canonical: $s/$f"; fail=1; }
  done
done

# 3. Every global entry is a symlink INTO the canonical store.
#    A real directory here means someone hand-copied and it will go stale.
#    A target under Documents/ means it points into a git working tree.
for s in $(ls -1 "$REPO"); do
  if [ ! -L "$GLOBAL/$s" ]; then
    echo "DRIFT: $GLOBAL/$s is not a symlink (real dir = a copy that will go stale)"; fail=1; continue
  fi
  tgt=$(readlink "$GLOBAL/$s")
  case "$tgt" in
    "$CANON"/*) ;;
    *Documents*) echo "DRIFT: $s points into a git working tree: $tgt"; fail=1 ;;
    *)           echo "DRIFT: $s points outside the canonical store: $tgt"; fail=1 ;;
  esac
  [ -f "$GLOBAL/$s/SKILL.md" ] || { echo "DRIFT: $s does not resolve to a SKILL.md"; fail=1; }
done

# 4. The repo copy is what is committed.
if ! git diff --quiet -- .claude/skills/ 2>/dev/null; then
  echo "NOTE: uncommitted changes under .claude/skills/ — commit before syncing to canonical"
fi

echo "---"
echo "skills: $(ls -1 "$REPO" | wc -l) | files compared: $files"
[ "$fail" -eq 0 ] && echo "CLEAN — repo, canonical and global agree" || echo "DRIFT FOUND — see above"

# To resync AFTER reviewing what drifted and deciding which side is right:
#   rm -rf /c/SAIRN/skills/sairn && mkdir -p /c/SAIRN/skills/sairn
#   cp -r .claude/skills/* /c/SAIRN/skills/sairn/
# Deliberately not automated here. Picking a winner is a judgment call.

exit $fail
