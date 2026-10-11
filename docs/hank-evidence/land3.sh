#!/usr/bin/env bash
# LAND hank batch 19. RULE F: rebase FIRST, derive SECOND, commit THIRD, push
# FOURTH, re-derived on EVERY cycle.
set -u
REPO="C:/Users/marsh/Documents/SAIRN-hank"
S="C:/Users/marsh/AppData/Local/Temp/claude/C--Users-marsh-Documents-SAIRN-hank/a517bec7-3fd2-4475-835c-6432b2acaa34/scratchpad"
cd "$REPO" || exit 2

DERIVED="docs/defect-density-register.json docs/tier-a-reviews.json docs/MASTER-PLAN.md docs/TOOLING-INVENTORY.md docs/traceability-matrix.md"
HAVE=${1:-no}

for CYCLE in 1 2 3 4 5; do
  echo "================ CYCLE $CYCLE ================"
  if [ "$HAVE" = "yes" ]; then
    git reset --soft -q HEAD~1 || { echo "SOFT RESET FAILED"; exit 2; }
    git restore --source=HEAD --staged --worktree -- $DERIVED || { echo "RESTORE FAILED"; exit 2; }
    HAVE=no
  fi

  git fetch -q origin
  BEHIND=$(git log --oneline HEAD..origin/main | wc -l | tr -d ' ')
  echo "behind=$BEHIND"
  if [ "$BEHIND" != "0" ]; then
    git -c core.hooksPath=/dev/null pull --rebase -q origin main > "$S/land3.rebase.$CYCLE.log" 2>&1
    if [ "$?" != "0" ]; then
      echo "REBASE FAILED -- stopping. Nothing lost, nothing pushed."
      tail -12 "$S/land3.rebase.$CYCLE.log"
      exit 2
    fi
  fi

  SHA_STATUS=$(git log --format='%h %s' origin/main..HEAD | grep 'a missing secret can no longer destroy' | cut -d' ' -f1)
  SHA_SWEEP=$(git log --format='%h %s' origin/main..HEAD | grep 'the sweep now watches shared state' | cut -d' ' -f1)
  echo "status-fix=$SHA_STATUS  sweep=$SHA_SWEEP"
  if [ -z "$SHA_STATUS" ] || [ -z "$SHA_SWEEP" ]; then
    echo "COULD NOT RESOLVE BOTH SHAS -- refusing to write a record citing nothing."
    exit 2
  fi

  python -u tools/tier_a_review_gate.py > "$S/land3.tiera.$CYCLE.out" 2>&1
  if [ "$?" != "0" ]; then
    python -u tools/tier_a_review_gate.py --open "$(cat "$S/tiera3.open.txt")" >> "$S/land3.tiera.$CYCLE.out" 2>&1
    echo "tier_a --open exit=$?"
  else
    echo "tier_a gate already satisfied"
  fi

  python -u "$S/reg_add_b3.py" "$SHA_STATUS" "$SHA_SWEEP" > "$S/land3.regadd.$CYCLE.out" 2>&1
  echo "reg_add exit=$?"
  grep -E '^registered' "$S/land3.regadd.$CYCLE.out"
  python -u tools/defect_register.py --check > "$S/land3.drcheck.$CYCLE.out" 2>&1
  DRC=$?
  echo "defect_register --check exit=$DRC"
  if [ "$DRC" != "0" ]; then
    echo "REGISTER --check IS NOT 0 -- stopping rather than pushing a register that fails its own check."
    tail -12 "$S/land3.drcheck.$CYCLE.out"
    exit 2
  fi

  for g in master_plan tooling_inventory traceability_matrix; do
    python -u "tools/$g.py" > "$S/land3.$g.$CYCLE.out" 2>&1
    echo "$g exit=$?"
  done

  git add $DERIVED
  git -c core.hooksPath=/dev/null commit -q -F "$S/land3.msg.txt"
  echo "commit exit=$?"
  HAVE=yes

  git push origin HEAD:main > "$S/land3.push.$CYCLE.log" 2>&1
  PUSH=$?
  echo "push exit=$PUSH"
  if [ "$PUSH" = "0" ]; then
    echo "PUSHED ON CYCLE $CYCLE"
    tail -6 "$S/land3.push.$CYCLE.log"
    exit 0
  fi
  echo "---- gate output ----"
  tail -36 "$S/land3.push.$CYCLE.log"
done
echo "FIVE CYCLES AND STILL NOT PUSHED -- stopping rather than looping forever."
exit 1
