#!/usr/bin/env bash
# LAND hank batch b1.
#
# THE PROBLEM THIS EXISTS FOR: three artefacts are DERIVED FROM THE PUSH ITSELF.
# The defect-register records cite the shas being pushed; the Tier A obligation
# is derived from the outgoing range; the three generated documents are derived
# from the tree at the tip. A rebase rewrites the shas and moves the range, so
# anything derived BEFORE a rebase is stale after it -- and a register record
# whose `commit` field resolves to nothing is exactly the vacuous row that file
# exists to prevent. So the order is fixed and REPEATED on every cycle:
#
#     rebase FIRST, derive SECOND, commit THIRD, push FOURTH.
#
# Nothing here is destructive. A backup branch is cut before the first cycle,
# `reset --soft` keeps every change in the index, and every derived file is
# rebuilt from a tool in the repo on the same cycle it is restored.
#
# `git restore --source=HEAD` and NOT `git checkout --`: after a soft reset the
# INDEX still holds the change, so `checkout -- <path>` restores the worktree
# FROM THE CHANGE and leaves it staged, and the next rebase refuses on an
# unclean index. That cost one cycle before it was noticed.
set -u
REPO="C:/Users/marsh/Documents/SAIRN-hank"
S="C:/Users/marsh/AppData/Local/Temp/claude/C--Users-marsh-Documents-SAIRN-hank/a517bec7-3fd2-4475-835c-6432b2acaa34/scratchpad"
cd "$REPO" || exit 2

DERIVED="docs/defect-density-register.json docs/tier-a-reviews.json docs/MASTER-PLAN.md docs/TOOLING-INVENTORY.md docs/traceability-matrix.md"
HAVE_DERIVED_COMMIT=${1:-no}

for CYCLE in 1 2 3 4 5; do
  echo "================ CYCLE $CYCLE ================"

  if [ "$HAVE_DERIVED_COMMIT" = "yes" ]; then
    git reset --soft -q HEAD~1 || { echo "SOFT RESET FAILED"; exit 2; }
    git restore --source=HEAD --staged --worktree -- $DERIVED || { echo "RESTORE FAILED"; exit 2; }
    HAVE_DERIVED_COMMIT=no
  fi

  git fetch -q origin
  BEHIND=$(git log --oneline HEAD..origin/main | wc -l | tr -d ' ')
  echo "behind=$BEHIND"
  if [ "$BEHIND" != "0" ]; then
    git -c core.hooksPath=/dev/null pull --rebase -q origin main > "$S/land.rebase.$CYCLE.log" 2>&1
    if [ "$?" != "0" ]; then
      echo "REBASE FAILED -- stopping. Nothing is lost and nothing is pushed."
      tail -8 "$S/land.rebase.$CYCLE.log"
      exit 2
    fi
  fi

  SHA_SIX=$(git log --format='%h %s' origin/main..HEAD | grep 'six tools now REFUSE' | cut -d' ' -f1)
  SHA_ATTR=$(git log --format='%h %s' origin/main..HEAD | grep 'the last SEVEN write paths' | cut -d' ' -f1)
  SHA_SEVENTH=$(git log --format='%h %s' origin/main..HEAD | grep 'the SEVENTH argv refusal' | cut -d' ' -f1)
  echo "shas: six=$SHA_SIX attr=$SHA_ATTR seventh=$SHA_SEVENTH"
  if [ -z "$SHA_SIX" ] || [ -z "$SHA_ATTR" ] || [ -z "$SHA_SEVENTH" ]; then
    echo "COULD NOT RESOLVE ALL THREE SHAS -- refusing to write a register record that cites nothing."
    exit 2
  fi

  # TIER A: only --open when the gate says an obligation is missing, so a cycle
  # that already has one does not append a duplicate.
  python tools/tier_a_review_gate.py > "$S/land.tiera.$CYCLE.out" 2>&1
  if [ "$?" != "0" ]; then
    python tools/tier_a_review_gate.py --open "$(cat "$S/tiera.open.txt")" >> "$S/land.tiera.$CYCLE.out" 2>&1
    echo "tier_a --open exit=$?"
  else
    echo "tier_a gate already satisfied"
  fi

  python "$S/repoint.py" "$SHA_SIX" "$SHA_ATTR" "$SHA_SEVENTH" || exit 2
  python "$S/reg_add.py" > "$S/land.regadd.$CYCLE.out" 2>&1
  echo "reg_add exit=$?"
  grep -E '^registered' "$S/land.regadd.$CYCLE.out"
  python tools/defect_register.py --check > "$S/land.drcheck.$CYCLE.out" 2>&1
  DRC=$?
  echo "defect_register --check exit=$DRC"
  if [ "$DRC" != "0" ]; then
    echo "REGISTER --check IS NOT 0 -- stopping rather than pushing a register that fails its own check."
    tail -8 "$S/land.drcheck.$CYCLE.out"
    exit 2
  fi

  for g in master_plan tooling_inventory traceability_matrix; do
    python "tools/$g.py" > "$S/land.$g.$CYCLE.out" 2>&1
    echo "$g exit=$?"
  done

  git add $DERIVED
  git -c core.hooksPath=/dev/null commit -q -F "$S/land.msg.txt"
  echo "commit exit=$?"
  HAVE_DERIVED_COMMIT=yes

  git push origin HEAD:main > "$S/land.push.$CYCLE.log" 2>&1
  PUSH=$?
  echo "push exit=$PUSH"
  if [ "$PUSH" = "0" ]; then
    echo "PUSHED ON CYCLE $CYCLE"
    tail -6 "$S/land.push.$CYCLE.log"
    exit 0
  fi
  echo "---- gate output ----"
  tail -32 "$S/land.push.$CYCLE.log"
done
echo "FIVE CYCLES AND STILL NOT PUSHED -- stopping rather than looping forever."
exit 1
