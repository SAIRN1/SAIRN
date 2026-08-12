"""
Given a subagent-driven-development plan file, cross-checks every task
against its actual logged review outcome in the plan's SDD ledger
(.superpowers/sdd/<plan-basename>/progress.md) and flags any task marked
"complete" with no real review evidence behind it.

Built directly in response to a real incident this session
(STONEDESK-SESSION80-HANDOFF.md, Section 3): a controller tool-use error
spawned an unconstrained agent that implemented Tasks 3-6 of a plan and
pushed straight to production with no task review ever run. The code
compiled and deployed cleanly -- which is exactly why nothing caught it
until an honest self-check did. "It compiles and deploys" is not evidence
a review happened (see sairn-precommit-gate's 2026-08-12 addition). This
tool makes that check mechanical instead of relying on someone remembering
to look.

What counts as "review evidence" in a ledger line for a task: the line
must contain "Task N:" AND at least one of a small set of phrases that
only appear when a real review (or a final, deliberate adjudication of
one) actually ran -- not just an assertion that the task is done. See
REVIEW_EVIDENCE_PHRASES below; this is intentionally a narrow, literal
list rather than a loose heuristic, so it fails toward "flag it" on
anything ambiguous rather than toward a false "clean" ledger.

Usage:
  python tools/verify_review_gates.py <plan_file.md> [ledger_file.md]

If ledger_file is omitted, this looks for it at the conventional SDD
workspace path relative to the plan file's own directory structure:
  <repo-root>/.superpowers/sdd/<plan-basename-without-.md>/progress.md
(same convention subagent-driven-development's sdd-workspace script uses).
That default will usually NOT be found automatically for a plan built in
a git worktree, since the ledger lives inside that worktree's own
.superpowers/ directory, not the main checkout -- pass the ledger path
explicitly in that case. This tool intentionally does not guess across
worktrees; a wrong guess here is worse than requiring an explicit path.
"""
import sys
import os
import re


REVIEW_EVIDENCE_PHRASES = [
    'review clean',
    'addressed',
    'fix round',
    'final review',
    're-review',
    'parked',
    'blocked',
    'no new breakage',
]


def parse_plan_tasks(plan_text):
    """Returns [(task_num:int, title:str), ...] from '### Task N: Title' headers."""
    tasks = []
    for m in re.finditer(r'^###\s+Task\s+(\d+)\s*:\s*(.+?)\s*$', plan_text, re.MULTILINE):
        tasks.append((int(m.group(1)), m.group(2).strip()))
    return tasks


def parse_ledger_task_lines(ledger_text):
    """Returns {task_num: [line, line, ...]} for every 'Task N: ...' line found."""
    by_task = {}
    for line in ledger_text.splitlines():
        m = re.match(r'^Task\s+(\d+)\s*:', line.strip())
        if not m:
            continue
        n = int(m.group(1))
        by_task.setdefault(n, []).append(line.strip())
    return by_task


def has_review_evidence(lines):
    joined = ' '.join(lines).lower()
    return any(phrase in joined for phrase in REVIEW_EVIDENCE_PHRASES)


def claims_complete(lines):
    return any('complete' in line.lower() for line in lines)


def default_ledger_path(plan_path):
    plan_base = os.path.splitext(os.path.basename(plan_path))[0]
    # Walk up from the plan file looking for a repo root marker (.git), then
    # apply the sdd-workspace convention from there.
    d = os.path.dirname(os.path.abspath(plan_path))
    while d and not os.path.isdir(os.path.join(d, '.git')):
        parent = os.path.dirname(d)
        if parent == d:
            d = None
            break
        d = parent
    if not d:
        return None
    candidate = os.path.join(d, '.superpowers', 'sdd', plan_base, 'progress.md')
    return candidate if os.path.isfile(candidate) else None


def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/verify_review_gates.py <plan_file.md> [ledger_file.md]")
        sys.exit(2)
    plan_path = sys.argv[1]
    if not os.path.isfile(plan_path):
        print(f"ERROR: plan file not found: {plan_path}")
        sys.exit(2)

    with open(plan_path, encoding='utf-8', errors='replace') as f:
        plan_text = f.read()

    if len(sys.argv) >= 3:
        ledger_path = sys.argv[2]
    else:
        ledger_path = default_ledger_path(plan_path)

    tasks = parse_plan_tasks(plan_text)
    print(f"PLAN:{plan_path}")
    print(f"TASKS_IN_PLAN:{len(tasks)}")

    if not ledger_path or not os.path.isfile(ledger_path):
        print(f"LEDGER:NOT_FOUND (looked at: {ledger_path!r})")
        print("RESULT:CANNOT_VERIFY -- pass the ledger path explicitly as the 2nd argument")
        sys.exit(2)

    print(f"LEDGER:{ledger_path}")
    with open(ledger_path, encoding='utf-8', errors='replace') as f:
        ledger_text = f.read()

    by_task = parse_ledger_task_lines(ledger_text)

    gaps = []
    for num, title in tasks:
        lines = by_task.get(num, [])
        if not lines:
            gaps.append((num, title, "no ledger entry at all"))
            continue
        completed = claims_complete(lines)
        reviewed = has_review_evidence(lines)
        if completed and not reviewed:
            gaps.append((num, title, "marked complete with no review-evidence phrase in its ledger lines"))
        elif not completed and not reviewed:
            # Has ledger activity but neither a completion nor review evidence --
            # likely mid-flight, not a silent gap, but still worth surfacing.
            print(f"IN_PROGRESS (no completion/review evidence yet): Task {num}: {title}")

    for num, title, reason in gaps:
        print(f"GAP: Task {num}: {title} -- {reason}")

    if gaps:
        print(f"RESULT:FAIL -- {len(gaps)} task(s) with no real review record")
        sys.exit(1)
    else:
        print("RESULT:PASS -- every task has a logged review outcome")
        sys.exit(0)


if __name__ == '__main__':
    main()
