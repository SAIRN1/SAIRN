#!/bin/sh
# H1 b41's OPEN QUESTION, driven live: does the scope gate's --pre-push leg
# refuse a REBASE-REPLAYED out-of-scope commit?
#
# H1 b41 confirmed that `git rebase`'s replay does not invoke
# .githooks/pre-commit, so commit-time enforcement is skipped for that shape.
# It explicitly did NOT test --pre-push ("remains the next thing to verify
# live") because testing it needs a push, and it would not push to a real
# remote. This script pushes to a LOCAL BARE repo, so there is a real push and
# no real remote.
#
# ISOLATED: a bare repo + a work clone under this session's scratchpad. No
# platform history is touched and nothing reaches origin.
#
# WHAT IS ISOLATED AND WHY: the sandbox's pre-push runs ONLY the scope gate,
# in the same read-stdin-once-and-replay shape the real hook uses. The real
# hook also drives register_feed_gate, copy_exactly_gate and
# sairn_push_gate_hook, none of which can run outside the platform repo. The
# question under test is the scope gate's own leg, so that is what the sandbox
# wires. Said out loud rather than left for a reader to notice.
set -e
SB="$(cd "$(dirname "$0")" && pwd)"
REPO=/c/Users/marsh/Documents/SAIRN-cc
rm -rf "$SB/bare" "$SB/work" 2>/dev/null || true
mkdir -p "$SB/bare" "$SB/work"

git init -q --bare "$SB/bare"
cd "$SB/work"
git init -q -b main .
git config user.email t@t; git config user.name t
git config commit.gpgsign false

# the real gate, verbatim
mkdir -p tools .githooks ".claude/skills/sairn-hover-auditor"
cp "$REPO/tools/hover_auditor_scope_gate.py" tools/
cp "$REPO/.claude/skills/sairn-hover-auditor/SKILL.md" \
   ".claude/skills/sairn-hover-auditor/SKILL.md"

cat > .githooks/pre-commit <<'EOF'
#!/bin/sh
ROOT=$(git rev-parse --show-toplevel)
GITDIR=$(git rev-parse --git-dir)
if [ -f "$GITDIR/sairn-hover-auditor-clone" ]; then
  python "$ROOT/tools/hover_auditor_scope_gate.py" --pre-commit || exit 1
fi
exit 0
EOF
cat > .githooks/pre-push <<'EOF'
#!/bin/sh
ROOT=$(git rev-parse --show-toplevel)
GITDIR=$(git rev-parse --git-dir)
REFS=$(cat)
if [ -f "$GITDIR/sairn-hover-auditor-clone" ]; then
  printf '%s\n' "$REFS" | python "$ROOT/tools/hover_auditor_scope_gate.py" --pre-push || exit 1
fi
exit 0
EOF
chmod +x .githooks/pre-commit .githooks/pre-push
git config core.hooksPath .githooks

# baseline commit BEFORE arming, so there is a history to diverge from
git add -A
git -c core.hooksPath=/dev/null commit -q -m base
touch "$(git rev-parse --git-dir)/sairn-hover-auditor-clone"
git remote add origin "$SB/bare"
git push -q --no-verify origin main
git fetch -q origin

echo "== A1 BASELINE: a plain commit of an out-of-scope path must be REFUSED =="
# NOT `git commit | head`: a pipeline's status is the LAST command's, so the
# first draft of this arm read head's 0 and reported ACCEPTED while the gate
# was refusing three lines above it. Status is captured directly.
echo x > README.md
git add README.md
set +e
git commit -q -m "out of scope" >"$SB/a1.txt" 2>&1
A1=$?
set -e
if [ $A1 -eq 0 ]; then
  echo "A1 RESULT: ACCEPTED  <-- the gate is not armed; every arm below is void"
else
  echo "A1 RESULT: REFUSED, exit $A1 (correct)"
  grep -m1 "REFUSED" "$SB/a1.txt" | sed 's/^/           /'
fi

echo ""
echo "== A2 the violation enters history via --no-verify (H1 b41 mechanism 1) =="
git commit -q --no-verify -m "out of scope, via --no-verify"
echo "A2 RESULT: commit $(git rev-parse --short HEAD) exists, carrying README.md"

echo ""
echo "== A3 a divergent upstream, then rebase: does pre-commit fire on replay? =="
git checkout -q --orphan upstream-sim
git rm -rq --cached . 2>/dev/null || true
rm -f README.md
mkdir -p tools .githooks ".claude/skills/sairn-hover-auditor"
cp "$REPO/tools/hover_auditor_scope_gate.py" tools/
cp "$REPO/.claude/skills/sairn-hover-auditor/SKILL.md" \
   ".claude/skills/sairn-hover-auditor/SKILL.md"
cat .githooks/pre-commit > /dev/null 2>&1 || true
git add -A
git -c core.hooksPath=/dev/null commit -q -m upstream
git checkout -q main
if git rebase upstream-sim >/dev/null 2>&1; then
  echo "A3 RESULT: REBASE SUCCEEDED, NO REFUSAL -- pre-commit did not fire on the replay"
  echo "           replayed sha $(git rev-parse --short HEAD) still carries:"
  git show --name-only --format= HEAD | sed 's/^/             /'
else
  echo "A3 RESULT: the rebase was REFUSED"
fi

echo ""
echo "== A4 THE OPEN QUESTION: push the replayed range. Does pre-push refuse? =="
git push origin main:refs/heads/probe 2>&1 | sed 's/^/    /' || true
if git --git-dir="$SB/bare" rev-parse --verify -q refs/heads/probe >/dev/null; then
  echo "A4 RESULT: THE PUSH LANDED -- pre-push did NOT refuse. THE GAP IS TOTAL."
else
  echo "A4 RESULT: THE PUSH WAS REFUSED -- enforcement moved to push time, not absent."
fi

echo ""
echo "== A5 CONTROL: an IN-SCOPE change must still push, or A4 proves nothing =="
# THE FIRST DRAFT OF THIS CONTROL WAS VOID AND SAYING SO IS THE POINT. It
# pushed `clean` as a NEW branch off the orphan upstream-sim, so the gate
# correctly checked EVERY commit reachable from it -- including the sandbox's
# own setup commit, which adds tools/ and .githooks/. The refusal was right
# and said nothing about the in-scope file. The base is published FIRST (with
# --no-verify, which is the sandbox arranging its own fixture and not the
# thing under test), so the outgoing range is exactly one in-scope commit.
git checkout -q -b clean upstream-sim
git push -q --no-verify origin clean:refs/heads/clean
git fetch -q origin
echo "# note" >> ".claude/skills/sairn-hover-auditor/SKILL.md"
git add ".claude/skills/sairn-hover-auditor/SKILL.md"
git commit -q -m "in scope: the auditor's own skill file"
BEFORE=$(git --git-dir="$SB/bare" rev-parse refs/heads/clean)
git push origin clean:refs/heads/clean 2>&1 | tail -3 | sed 's/^/    /' || true
AFTER=$(git --git-dir="$SB/bare" rev-parse refs/heads/clean)
if [ "$AFTER" != "$BEFORE" ]; then
  echo "A5 RESULT: IN-SCOPE PUSH LANDED (correct) -- A4's refusal is about the PATH, not about pushing"
else
  echo "A5 RESULT: AN IN-SCOPE PUSH WAS ALSO REFUSED -- the gate refuses everything and A4 is void"
fi

echo ""
echo "== A6 THE REAL SHAPE: the replayed commit onto an EXISTING remote branch =="
# A4 pushed to a NEW branch, so the gate took its `rsha == ZERO` path --
# "checking every commit reachable from X" -- which is DIFFERENT CODE from the
# `rsha..lsha` range it uses for an existing branch. That is the path a real
# `git push origin main` takes, so A4 alone does not answer the question for
# the real case. This arm does.
git checkout -q main
# publish main's PRE-violation state so the remote branch exists and the push
# below is a range push rather than a new branch
git branch -q -f realmain upstream-sim
git push -q --no-verify origin realmain:refs/heads/realmain
git fetch -q origin
B6=$(git --git-dir="$SB/bare" rev-parse refs/heads/realmain)
git push origin main:refs/heads/realmain 2>&1 | grep -E "REFUSED|path\(s\) are outside|hover scope gate:|rejected|error:" | sed 's/^/    /' || true
A6=$(git --git-dir="$SB/bare" rev-parse refs/heads/realmain)
if [ "$A6" != "$B6" ]; then
  echo "A6 RESULT: THE RANGE PUSH LANDED -- pre-push does NOT cover the real shape."
else
  echo "A6 RESULT: THE RANGE PUSH WAS REFUSED -- the rsha..lsha path covers it too."
fi

echo ""
echo "== A7 THE NEW SECOND GUARD: does post-rewrite NAME the replayed paths? =="
# The fix b16 adds. Same isolation note as the pre-push arms: the sandbox's
# post-rewrite runs ONLY the scope-gate leg, because the real hook's other two
# consumers (defect_register, doc_sha_reseat) cannot run outside the platform
# repo. The question is whether git FIRES this hook on a rebase and whether
# the gate reads the map it is handed.
cat > .githooks/post-rewrite <<'EOF'
#!/bin/sh
ROOT=$(git rev-parse --show-toplevel)
GITDIR=$(git rev-parse --git-dir)
MAP=$(cat)
if [ -f "$GITDIR/sairn-hover-auditor-clone" ]; then
  printf '%s\n' "$MAP" | python "$ROOT/tools/hover_auditor_scope_gate.py" --post-rewrite
fi
exit 0
EOF
chmod +x .githooks/post-rewrite
cp "$REPO/tools/hover_auditor_scope_gate.py" tools/
git checkout -q -B replay2 upstream-sim
echo y > OUTSIDE.md
git add OUTSIDE.md
git commit -q --no-verify -m "second out-of-scope commit"
git checkout -q -b up2 upstream-sim
echo z > ".claude/skills/sairn-hover-auditor/other.md"
git add ".claude/skills/sairn-hover-auditor/other.md"
git commit -q --no-verify -m "divergent"
git checkout -q replay2
git rebase up2 > "$SB/a7.txt" 2>&1 || true
if grep -q "OUT-OF-SCOPE PATHS IN A REWRITTEN COMMIT" "$SB/a7.txt"; then
  echo "A7 RESULT: THE NOTICE FIRED and named:"
  grep -E "^      [A-Za-z.]" "$SB/a7.txt" | head -4 | sed 's/^/        /'
  grep -E "rewritten commit\(s\) examined|THE PUSH WILL BE REFUSED" "$SB/a7.txt" | head -2 | sed 's/^/        /'
else
  echo "A7 RESULT: NO NOTICE -- git did not fire post-rewrite, or the gate said nothing"
  tail -4 "$SB/a7.txt" | sed 's/^/        /'
fi

echo ""
echo "== A8 CONTROL: an IN-SCOPE rewrite must produce the CLEAN line, not silence =="
git checkout -q -B replay3 upstream-sim
echo q > ".claude/skills/sairn-hover-auditor/inscope.md"
git add ".claude/skills/sairn-hover-auditor/inscope.md"
git commit -q -m "in scope only"
git rebase up2 > "$SB/a8.txt" 2>&1 || true
if grep -q "OUT-OF-SCOPE PATHS" "$SB/a8.txt"; then
  echo "A8 RESULT: THE NOTICE FIRED ON AN IN-SCOPE REWRITE -- A7 is void"
elif grep -q "all in scope" "$SB/a8.txt"; then
  echo "A8 RESULT: CLEAN, AND SAID SO:"
  grep "all in scope" "$SB/a8.txt" | sed 's/^/        /'
else
  echo "A8 RESULT: SILENT -- a clean rewrite is indistinguishable from the hook not running"
  tail -3 "$SB/a8.txt" | sed 's/^/        /'
fi
