---
name: sairn-code-guardian
description: >
  The permanent mechanical guardian for every SAIRN app. Trigger this skill automatically on
  every build session start, every file push, every code review, and every time the user says
  "check", "scan", "push", "fix", "audit", "is this ready", "before I push", or "something broke".
  This skill is SAIRN-aware — it knows the proxy rule, color system, bridge pattern, print rules,
  role gates, Unicode restrictions, regex safety, and all 11 universal patterns. It pulls files
  directly from GitHub, runs a full mechanical scan (12 checks, including Node ground-truth syntax
  validation and duplicate-global-identifier detection added after the June 2026 StoneDesk outage),
  auto-fixes every finding, and pushes clean code back — one automated flow. No manual grep. No
  line-by-line hunting. Zero syntax errors shipped, zero silently-overwritten functions, zero
  malformed regex literals, zero stale hardcoded model strings. This is the skill that caught the
  fabricor.html line 4605 bug, the StoneDesk multi-script-tag corruption (unterminated strings,
  an orphaned fragment that ate a <script> opening tag and left two functions executing as inert
  HTML text, a global function-name collision that silently misdirected a chat hook), and every
  bug like them. Always active. Never skipped.
---

# SAIRN Code Guardian

> *"Ship nothing broken. Know the rules before you write the first line. Fix before you push. Always."*

This skill is the permanent mechanical guardian for the entire SAIRN platform. It is domain-aware, SAIRN-specific, and automated. It does not rely on human review to catch mechanical bugs — it runs the scan itself, finds every violation, fixes every finding, and pushes clean code. It activates on every build and every push without being asked.

**Why 19 checks, not 8:** on June 16, 2026, all three existing SAIRN quality skills (this Guardian's original 8 checks, sairn-runtime-validator, sairn-ultra-scan) passed a build of stonedesk.html that was completely broken in the browser — every AI button did nothing, the entire SOP-printing feature was dead, and a chat-rendering hook was silently misdirected to the wrong feature. The root causes were a multi-hundred-line unterminated string, a stray script tag pasted mid-block, an orphaned HTML fragment that ate a `<script>` opening tag (leaving two real functions executing as inert page text with zero console errors), a global function-name collision, two malformed-but-valid regex literals, and two stale hardcoded model strings. Checks 9-12 were built to catch those. Then, on the same day, after a round of fixes that passed Checks 9-12 was pushed live, the page crashed anyway with a hard SyntaxError — the same `APP_ID` constant had been declared in two separate `<script>` tags, which Check 9 cannot catch because it validates each script block in isolation, not the combined global scope a real browser builds across all of them. Check 13 was built for that, and a same-day platform audit found the identical bug in all 11 of 11 B2B apps. Later the same day, after Checks 9-13 all passed clean, the user reported seeing raw JavaScript rendered as visible text on the live page — three separate times in one file. Each time, a prior edit had deleted a `<script>` opening tag or inserted a stray `</body>` mid-file, leaving real working JS (a demo-data seeder, a range-bar renderer, an admin-formula editor) sitting outside any script wrapper. None of this throws a console error, because there's nothing to parse as JS — the browser just prints it as text. Check 14 was built for that gap. A platform-wide sweep then found Check 9 was also blind to 8 call sites silently downgrading the AI model tier via mismatched `app_id` values — Check 15 was built for that. Finally, after delivering a generated warranty terms document and then raising its prices $100 per package at the user's request, the matching prices hardcoded in the live app's `onclick` handlers were never updated, since nothing connects a generated document to the app's source — Check 16 was built for that drift, and Check 18 was built because none of Checks 9-17 verify that a function's body actually matches the markup it's meant to operate on -- they confirm the file parses and doesn't crash, not that the logic is wired to the right elements. The very next fix for Check 18's own bug then shipped a NEW bug -- a leftover `pinEl` reference after the variable was removed -- caught only by the user's live console error, not by re-reading the edit. Check 19 exists because that miss, and a separate hour-long stall reasoning in prose about which of three duplicate `nav()`/`showPage()` functions "should" win, were both solved in seconds once the code was actually executed instead of read. None of these were syntax errors a regex scan reliably catches, and none were caught until a human read browser console output and manually traced the file line by line, or until the user caught a business-logic mismatch by eye. Checks 9-19 exist so that tracing never has to happen by hand again -- and Check 19 specifically exists so that "I read it and it looks right" is never the final word on a logic fix again.

---

## Trigger Conditions — Always Active On:

- Every new SAIRN app build (runs at start AND before push)
- Every file push to GitHub
- Every code review request
- Any broken app or unexpected behavior report
- User says: "scan", "check", "push", "fix", "audit", "something broke", "before I push", "is this ready", "syntax error", "not loading", "patch not working"
- After any Supabase patch injection
- After any major feature addition to an existing app

---

## The Guardian Protocol — 6 Phases (0 through 5)

Run all 6 phases in order. Never skip a phase. Never push until Phase 5 passes.

---

### PHASE 0 — Skill Inventory Check (run once per session, before Phase 1)

**Added June 16, 2026.** `sairn-code-guardian` itself existed only in this sandbox's local `/mnt/skills/user/` for an unknown number of sessions before it was ever pushed to GitHub's `skills/` folder — meaning any session that started fresh without that local copy present would have silently run with 8 checks (or zero, if the skill directory itself was empty) and no warning that anything was missing. A skill that exists but isn't loaded is indistinguishable from a skill that doesn't exist, from the perspective of the bugs it would have caught.

Before any build, scan, or push work begins, check BOTH locations and reconcile:

```python
import os, json, urllib.request

# 1. What's available locally in this sandbox right now
local_skills = []
if os.path.isdir('/mnt/skills/user'):
    local_skills = sorted(os.listdir('/mnt/skills/user'))

# 2. What's actually persisted on GitHub
PAT = "[user's PAT]"
REPO = "SAIRN1/SAIRN"
req = urllib.request.Request(
    f"https://api.github.com/repos/{REPO}/contents/skills",
    headers={"Authorization": f"token {PAT}", "User-Agent": "Python"}
)
try:
    with urllib.request.urlopen(req) as r:
        github_skills = sorted(item['name'] for item in json.loads(r.read()) if item['type'] == 'dir')
except urllib.error.HTTPError as e:
    github_skills = [] if e.code == 404 else None  # None = couldn't check, flag this

print("Local only (not backed up to GitHub):", set(local_skills) - set(github_skills or []))
print("GitHub only (not loaded in this sandbox):", set(github_skills or []) - set(local_skills))
```

**If a skill exists in GitHub's `skills/` folder but not locally:** pull it down and read it before proceeding — it may contain checks, rules, or context this session would otherwise silently miss.

**If a skill exists locally but not on GitHub:** flag this to the user explicitly rather than assuming it's intentional. Push it once confirmed, so the next session (which may start with a different or empty local skill directory) doesn't lose it.

**Report this reconciliation result before doing anything else in the session.** A one-line "skills in sync" or an explicit list of what's missing from where — never silently proceed as if the two locations are guaranteed to match.

---

### PHASE 1 — Pull & Inventory

Before any scan, pull the target file from GitHub using the Python urllib method (never curl for large files — shell arg limit at ~646KB):

```python
import base64, json, urllib.request

PAT = "[user's PAT]"
REPO = "SAIRN1/SAIRN"
FILENAME = "[target file]"

# Step 1: Get current SHA
req = urllib.request.Request(
    f"https://api.github.com/repos/{REPO}/contents/{FILENAME}",
    headers={"Authorization": f"token {PAT}", "User-Agent": "Python"}
)
with urllib.request.urlopen(req) as r:
    meta = json.loads(r.read())
    sha = meta['sha']
    content = base64.b64decode(meta['content']).decode('utf-8', errors='replace')

with open(f'/home/claude/{FILENAME}', 'w') as f:
    f.write(content)

print(f"Pulled: {FILENAME} | Lines: {len(content.splitlines())} | SHA: {sha}")
```

Report: filename, line count, SHA, file size. This is the baseline.

---

### PHASE 2 — The 12-Point Mechanical Scan

Run all 17 checks simultaneously on the pulled file. Every check reports: PASS, WARN, or FAIL with exact line numbers. Checks 9-17 (added June 2026) require Node to be available in the execution environment for Check 9 specifically; if Node is unavailable, Check 9 reports WARN rather than silently skipping, and Checks 10-17 still run normally since they are pure Python (Checks 16 and 17 require additional inputs beyond the single app file — see their individual sections). Check 13, Check 14, and Check 15 in particular should always be run, even if Check 9 passed cleanly — a clean Check 9 says nothing about cross-script-tag collisions, content sitting entirely outside any script tag, or app_id values silently downgrading the model tier, all three of which caused real production issues in StoneDesk despite a clean Check 9 result. Check 17 should be applied as a default checklist on every customer-facing legal document, not only when explicitly requested.

---

#### CHECK 1 — JS String Integrity (Orphaned HTML)

**The bug this catches:** The fabricor.html line 4605 bug — HTML tags escaping out of `win.document.write()` strings into raw JS scope, causing `Unexpected token '<'`.

**What to scan for:**
- Any line that begins with `</` or `<` that is NOT inside a JS string or template literal
- Orphaned closing tags after `win.document.write(...)` calls
- `document.write(` calls where the opening quote has no matching closing quote on the same or continued line
- HTML entities (`</body>`, `</html>`, `</script>`) sitting outside string delimiters

**Python scan pattern:**
```python
import re

def check_js_string_integrity(lines):
    findings = []
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        # Orphaned HTML: line starts with < but is not inside a string context
        if re.match(r'^</?\w', stripped) and not re.search(r'["\'].*</?\w.*["\']', line):
            # Check if it's inside a document.write call continuation
            if "document.write" not in line and "innerHTML" not in line and not stripped.startswith("<!--"):
                findings.append((i, "ORPHANED HTML outside JS string", stripped[:80]))
    return findings
```

**FAIL condition:** Any match → block push, auto-fix by merging orphaned HTML into preceding `document.write()` call.

---

#### CHECK 2 — Unicode Box-Drawing Character Scan

**The rule:** NEVER use Unicode box-drawing characters (─ │ ╔ ═ ╗ ╚ ╝ ║ ┌ ┐ └ ┘ ├ ┤ ┬ ┴ ┼) inside JavaScript. They crash the JS parser silently on some engines and caused 27,000+ character removal across the SAIRN suite in the June 2026 audit.

**What to scan for:**
```python
BOX_CHARS = set('─│╔═╗╚╝║┌┐└┘├┤┬┴┼╠╣╦╩╬▀▄█▌▐░▒▓')

def check_unicode_box_chars(lines):
    findings = []
    in_js = False
    for i, line in enumerate(lines, 1):
        # Simple heuristic: flag any box char in a .js file or inside <script> tags
        for ch in line:
            if ch in BOX_CHARS:
                findings.append((i, f"UNICODE BOX CHAR '{ch}' in JS scope", line.strip()[:80]))
                break
    return findings
```

**Auto-fix:** Replace all box chars with ASCII equivalents: `─` → `---`, `│` → `|`, `═` → `===`, `╔╗╚╝` → `+`. Replace `// ─────` style comments with `// ===` or `// ---`.

**FAIL condition:** Any box char found in JS → auto-fix and re-scan.

---

#### CHECK 3 — Regex Literal Newline Safety

**The rule:** Always escape newlines in JavaScript regex as `\\n` not literal newlines. The pattern `.replace(/\n\n/g` must always be written as `.replace(/\\n\\n/g` or buttons will silently break.

**What to scan for:**
```python
def check_regex_newlines(lines):
    findings = []
    for i, line in enumerate(lines, 1):
        # Find regex literals with unescaped literal newline references
        if re.search(r'/[^/]*\n[^/]*/[gimsuy]*', line):
            findings.append((i, "LITERAL NEWLINE inside regex literal", line.strip()[:80]))
        # Find common incorrect pattern
        if re.search(r'replace\s*\(\s*/\\n', line) and '\\\\n' not in line:
            # Check if it's a single backslash-n (should be double)
            if re.search(r'replace\s*\(\s*/\bn\b', line):
                findings.append((i, "POSSIBLY UNESCAPED \\n in regex — verify \\\\n", line.strip()[:80]))
    return findings
```

**FAIL condition:** Any literal newline inside a regex literal → auto-fix to `\\n`.

---

#### CHECK 4 — Direct Anthropic API Call Scanner (Proxy Violation)

**The rule — PERMANENT:** ALL Claude API calls must route through `https://sairn.vercel.app/api/claude`. NEVER call `api.anthropic.com` directly from the browser. Every fetch must include `app_id` and `is_demo: true`.

**What to scan for:**
```python
FORBIDDEN_ENDPOINTS = [
    'api.anthropic.com',
    'anthropic.com/v1',
    'claude.ai/api',
]

REQUIRED_PROXY = 'sairn.vercel.app/api/claude'
REQUIRED_FIELDS = ['app_id', 'is_demo']

def check_proxy_compliance(content):
    findings = []
    for endpoint in FORBIDDEN_ENDPOINTS:
        if endpoint in content:
            lines_found = [i+1 for i, l in enumerate(content.splitlines()) if endpoint in l]
            findings.append(f"DIRECT ANTHROPIC CALL at lines {lines_found} — must use proxy")
    
    if 'fetch(' in content and REQUIRED_PROXY in content:
        # Verify app_id and is_demo are present near proxy calls
        proxy_blocks = [i+1 for i, l in enumerate(content.splitlines()) if REQUIRED_PROXY in l]
        for line_num in proxy_blocks:
            block = '\n'.join(content.splitlines()[max(0,line_num-5):line_num+10])
            if 'app_id' not in block:
                findings.append(f"PROXY CALL at line {line_num} missing app_id")
            if 'is_demo' not in block:
                findings.append(f"PROXY CALL at line {line_num} missing is_demo")
    
    return findings
```

**FAIL condition:** Any direct `api.anthropic.com` call → BLOCK push immediately. This is a hard stop. Fix before anything else.

---

#### CHECK 5 — Print Render Compliance

**The rule:** Every SAIRN app must use `print-color-adjust: exact` and `-webkit-print-color-adjust: exact` on any colored sections. Always include a visible Print/Save PDF button. Dark accent sections (covers, pricing heroes, footers) are allowed but MUST have print-color-adjust so they render correctly on white paper.

**What to scan for:**
```python
PRINT_TRIGGERS = ['background:#', 'background-color:', 'background: #', 'bg-']
PRINT_FIX = 'print-color-adjust'
WEBKIT_FIX = '-webkit-print-color-adjust'

def check_print_compliance(content):
    findings = []
    has_colored_sections = any(t in content for t in PRINT_TRIGGERS)
    has_print_adjust = PRINT_FIX in content
    has_webkit_adjust = WEBKIT_FIX in content
    has_print_button = any(t in content.lower() for t in ['print', 'save pdf', 'window.print'])
    
    if has_colored_sections and not has_print_adjust:
        findings.append("MISSING print-color-adjust:exact — colored sections will not print correctly")
    if has_colored_sections and not has_webkit_adjust:
        findings.append("MISSING -webkit-print-color-adjust:exact — Chrome/Safari print broken")
    if not has_print_button:
        findings.append("WARN: No print/PDF button found — consider adding one per print-first design rule")
    
    return findings
```

**FAIL condition:** Colored sections without print-color-adjust → auto-inject into the relevant CSS block.

---

#### CHECK 6 — SAIRN Bridge Sync Validator

**The rule — PERMANENT:** Every B2B app (StoneDesk, SAIRNhr, SAIRNacc, SAIRNbuild, SAIRNlaw, SAIRNscape) must include: (1) SAIRN Suite launcher panel linking to companion apps, (2) "Sync All Apps" button pushing data to the bridge at `sairn.vercel.app/api/bridge`, (3) CSV export buttons (jobs/payroll/GL format).

**B2B apps that require bridge:** StoneDesk, SAIRNhr, SAIRNacc, SAIRNbuild, SAIRNlaw, SAIRNscape, SAIRNfuneral

**Consumer apps — bridge NOT required:** SAIRNtype, Lingual, Health, Money, Legal, Study, Roam, Senior (NEXUS apps)

```python
B2B_APPS = ['stonedesk', 'fabricor', 'saairnhr', 'sairnacc', 'sairnbuild', 'sairnlaw', 'sairnscape', 'sairnfuneral']
BRIDGE_URL = 'sairn.vercel.app/api/bridge'
BRIDGE_REQUIREMENTS = ['api/bridge', 'Sync All Apps', 'CSV']

def check_bridge_sync(filename, content):
    findings = []
    is_b2b = any(app in filename.lower() for app in B2B_APPS)
    if not is_b2b:
        return []  # NEXUS apps skip this check
    
    for req in BRIDGE_REQUIREMENTS:
        if req not in content:
            findings.append(f"B2B BRIDGE MISSING: '{req}' not found — required for all B2B apps")
    
    return findings
```

**FAIL condition:** Any B2B app missing bridge touchpoints → flag for manual addition (cannot auto-fix without business logic context).

---

#### CHECK 7 — Role Gate Audit

**The rule:** Every SAIRN B2B app with user roles must gate protected routes at the API level. Required roles: `owner`, `admin`, `manager`, `sales`, `installer`, `viewer`. The Compensation module is always gated: owner/admin see all, manager sees team, sales sees own, installer/viewer blocked.

**What to scan for:**
```python
ROLE_KEYWORDS = ['owner', 'admin', 'manager', 'sales', 'installer', 'viewer']
GATE_PATTERNS = ['role', 'pin', 'auth', 'access', 'permission', 'guard']

def check_role_gates(content):
    findings = []
    has_roles = any(r in content.lower() for r in ROLE_KEYWORDS)
    has_gates = any(g in content.lower() for g in GATE_PATTERNS)
    has_compensation = any(t in content.lower() for t in ['commission', 'compensation', 'payroll', 'salary'])
    
    if has_compensation:
        # Verify compensation is gated
        comp_gated = 'role' in content.lower() and ('commission' in content.lower() or 'compensation' in content.lower())
        if not comp_gated:
            findings.append("COMPENSATION MODULE may be ungated — owner/admin/manager/sales/installer gates required")
        
        # Check for installer block
        if 'installer' not in content.lower():
            findings.append("WARN: 'installer' role not referenced — verify installer is blocked from compensation view")
    
    if has_roles and not has_gates:
        findings.append("ROLES defined but no gate pattern found — verify role-based access is enforced")
    
    return findings
```

**FAIL condition:** Compensation module without role gates → hard flag, cannot ship.

---

#### CHECK 8 — Color Compliance (No Blue Violations)

**The rule — FINAL COLOR MAP:**
- StoneDesk = Money Green `#16C762` / Dark `#0A3D1F` / Light `#F0FEF6` / Accent `#5CFF9D`
- SAIRNdesign = Indigo `#6366F1` — **OWNS ALL BLUE/BLUE-ADJACENT**
- SAIRNhr = Violet `#7C3AED`
- SAIRNacc = Teal `#0D9488`
- SAIRNbuild = Amber `#F59E0B`
- SAIRNlaw = Forest Green `#15803D`
- SAIRNcode = Slate `#475569`
- SAIRNscape = Sky Green `#22C55E`

**Forbidden:** Any blue or blue-adjacent color (`#3B82F6`, `#2563EB`, `#1D4ED8`, `#60A5FA`, `blue`, `#0000FF`, `#00F`, `#4F46E5` used outside SAIRNdesign) in any app that is NOT SAIRNdesign.

```python
BLUE_COLORS = [
    '#3B82F6', '#2563EB', '#1D4ED8', '#60A5FA', '#93C5FD', '#BFDBFE',
    '#4F46E5', '#3730A3', '#0000FF', '#0000ff', '#00F',
    'color:blue', 'color: blue', 'background:blue', 'background: blue',
]
BLUE_OWNER = 'sairndesign'

def check_color_compliance(filename, content):
    findings = []
    is_design_app = BLUE_OWNER in filename.lower()
    if is_design_app:
        return []  # SAIRNdesign owns blue — skip
    
    for color in BLUE_COLORS:
        if color.lower() in content.lower():
            lines_found = [i+1 for i, l in enumerate(content.splitlines()) if color.lower() in l.lower()]
            findings.append(f"BLUE COLOR VIOLATION: '{color}' found at lines {lines_found} — only SAIRNdesign uses blue")
    
    # Check that the app uses its correct brand color
    # (informational — warn if neither brand color nor a known SAIRN color is present)
    known_colors = ['#16C762', '#6366F1', '#7C3AED', '#0D9488', '#F59E0B', '#15803D', '#475569', '#22C55E', '#0A3D1F']
    if not any(c in content for c in known_colors):
        findings.append("WARN: No recognized SAIRN brand color found — verify correct app color is applied")
    
    return findings
```

**FAIL condition:** Blue in non-SAIRNdesign app → flag all instances. Auto-suggest the correct app color.

---

#### CHECK 9 — Node Ground-Truth Syntax Validation

**Added after the StoneDesk outage (June 16, 2026).** Checks 1-8 above are regex-based static scans. They missed a multi-hundred-line unterminated string in `win.document.write(...)`, a stray `<script>` tag pasted inside an already-open script block, `document.addEventListener('DOMContentLoaded', function);` (the bare `function` keyword passed instead of a reference), and two entire functions (`showSOPs`, `printAllSOPs`) sitting completely outside any `<script>` tag due to an orphaned fragment eating the opening tag. All of these are syntactically real bugs that Check 1's single-line orphaned-HTML pattern cannot catch because they span many lines or involve no orphaned HTML at all on the offending line itself.

**The rule:** Before any push, extract every inline `<script>...</script>` block and run `node --check` on each one individually — this mirrors exactly how a browser parses separate script tags, and is ground truth rather than a heuristic.

**What to scan for:** any block that fails `node --check`, with the exact error and offending line surfaced.

```python
import re, subprocess, tempfile, os

def extract_script_blocks(content):
    # Global non-greedy match (not a line-by-line scanner) — correctly handles
    # adjacent </script><script> tags. Negative lookbehind for a backslash
    # before </script> avoids false-splitting on SAIRN's escaped print-popup
    # pattern: win.document.write('...<script>...<\/script>').
    blocks = []
    pattern = re.compile(
        r'<script(?![^>]*\bsrc=)[^>]*>(.*?)(?<!\\)</script>',
        re.DOTALL | re.IGNORECASE
    )
    for m in pattern.finditer(content):
        code = m.group(1)
        start_line = content.count('\n', 0, m.start(1)) + 1
        end_line = content.count('\n', 0, m.end(1)) + 1
        blocks.append((start_line, end_line, code))
    return blocks

def check_node_groundtruth(content, node_path='node'):
    findings = []
    blocks = extract_script_blocks(content)
    if not blocks:
        return findings
    with tempfile.TemporaryDirectory() as tmpdir:
        for idx, (start, end, code) in enumerate(blocks):
            fpath = os.path.join(tmpdir, f'block_{idx}.js')
            with open(fpath, 'w', encoding='utf-8') as f:
                f.write(code)
            try:
                result = subprocess.run([node_path, '--check', fpath],
                                         capture_output=True, text=True, timeout=10)
            except FileNotFoundError:
                findings.append(f"WARN: Node unavailable — ground-truth check skipped")
                return findings
            if result.returncode != 0:
                err = re.search(r'(SyntaxError: .+)', result.stderr)
                findings.append(f"CRITICAL: parse failure in block lines {start}-{end}: "
                                 f"{err.group(1) if err else result.stderr.strip()[:200]}")
    return findings
```

**FAIL condition:** Any block fails to parse → BLOCK push immediately. This is the highest-priority check in the entire scan, since a parse failure in one script tag can silently prevent unrelated script tags from executing correctly depending on what DOM setup they depended on.

---

#### CHECK 10 — Duplicate Global Identifier Detector

**Added after the StoneDesk outage.** Multiple inline `<script>` tags in one HTML document share a single global scope for plain `function name(){}` declarations and `window.name = function` assignments. StoneDesk had `tryInstall` declared twice (a markdown-render hook installer and an unrelated confidence-bar hook installer) — the second silently won, so the first feature's `setTimeout(tryInstall, ...)` call ended up running the second feature's code instead. No error was thrown anywhere, because calling a function that exists — just the wrong one — is not an error.

**The rule:** Before any push, find every top-level `function name(){}` and `window.name = function` declaration across the whole file. Two or more declarations of the same name is at minimum a WARN; if the name is load-bearing (`callClaude`, `doLogin`, `showPage`, `showToast`, `showApp`, `dbLoadAll`, `applyRoleGates`, `applyExecRole`, `initAI`) or the surviving definition looks like an empty stub, it's CRITICAL. The known exceptions are `fetch`, `addMsg`, and `open` — SAIRN deliberately re-wraps these many times to layer features (the "onion wrapper" pattern: `var _orig = window.fetch; window.fetch = function(...){ ...; return _orig.apply(this, arguments); }`), so these are only flagged if a later reassignment fails to chain to a saved `_orig` reference.

**Known false positive to watch for when reviewing findings by hand:** a function declared and immediately exported right next to itself (`function selRole(el){...} window.selRole = selRole;`) is the standard safe pattern, not a collision — only flag when 2+ DISTINCT function bodies of the same name exist.

```python
import re

LOAD_BEARING_NAMES = {'callClaude','doLogin','showPage','showToast','showApp',
                       'dbLoadAll','applyRoleGates','applyExecRole','initAI'}
WRAPPER_TOLERANT_NAMES = {'fetch', 'addMsg', 'open'}

def find_all_function_declarations(content):
    occurrences = {}
    lines = content.split('\n')
    func_pattern = re.compile(r'^(\s*)(?:async\s+)?function\s+(\w+)\s*\(')
    window_pattern = re.compile(r'^(\s*)window\.(\w+)\s*=\s*(?:async\s+)?function')
    for i, line in enumerate(lines):
        for pattern in (func_pattern, window_pattern):
            m = pattern.match(line)
            if m:
                indent, name = m.groups()
                occurrences.setdefault(name, []).append((i + 1, len(indent)))
    return occurrences

def check_duplicate_globals(content):
    findings = []
    occs = find_all_function_declarations(content)
    for name, locs in occs.items():
        lines_only = sorted(set(l for l, _ in locs))
        if len(lines_only) < 2:
            continue  # single declaration (+ maybe its own export) — not a collision
        zero_indent = sum(1 for _, ind in locs if ind == 0)
        is_collision = zero_indent >= 2 or (zero_indent >= 1 and len(locs) >= 2)
        if not is_collision:
            continue
        severity = 'CRITICAL' if name in LOAD_BEARING_NAMES else 'WARN'
        findings.append(f"{severity}: '{name}' declared {len(lines_only)}x at lines "
                         f"{lines_only} — only the LAST is live, all earlier are dead code")
    return findings
```

**FAIL condition:** Any load-bearing name with an unchained duplicate → BLOCK push. Other duplicates → flag and consolidate before next push, but does not block.

---

#### CHECK 11 — Regex Literal Sanity Check

**Added after the StoneDesk outage.** Catches regex literals that are syntactically valid JavaScript (so Check 9's Node parser will not flag them) but semantically broken. StoneDesk's `renderMarkdown` had `/**([^*]+)**/g` and `/*([^*]+)*/g` — both intended to match markdown bold/italic, but `/*` is the start of a JS block comment, not a regex, so JavaScript silently swallows everything until the next `*/` anywhere later in the file. It also had `/^(d+). (.+)$/` — missing the backslash before `d`, so it matched the literal letter "d" instead of `\d` (a digit), compiling fine but matching nothing useful.

```python
import re

def check_regex_literals(content):
    findings = []
    lines = content.split('\n')
    comment_trap = re.compile(r'(?<![\/\*])/\*\*?\(')
    missing_backslash = re.compile(
        r'\.(?:replace|match|test|exec)\s*\(\s*/\^?\(?(d|w|s)\+\)?[^/]*?/[gimsuy]*'
    )
    for i, line in enumerate(lines):
        if comment_trap.search(line):
            findings.append(f"CRITICAL line {i+1}: regex opens with '/*' — JS parses this "
                             f"as a block comment start, not a regex. Escape: /\\*\\*(...)")
        m = missing_backslash.search(line)
        if m:
            findings.append(f"HIGH line {i+1}: bare '{m.group(1)}' in regex where "
                             f"'\\{m.group(1)}' was intended — matches literal letter, not class")
    return findings
```

**FAIL condition:** Any comment-trap regex → BLOCK push (can silently corrupt unrelated downstream code via the swallowed comment). Missing-backslash → fix before push, does not block.

---

#### CHECK 12 — Stale/Hardcoded Model String Detector

**Added after the StoneDesk outage.** Catches client-side `fetch()` calls to the SAIRN proxy that hardcode a Claude model identifier instead of letting the proxy (`api/claude.js`) choose the model from `app_id`/`is_demo` per the PERMANENT proxy pattern. StoneDesk had two call sites sending `model:'claude-sonnet-4-20250514'` directly. This bug class is invisible to Checks 1-11: it's not a syntax error, not a duplicate, not a malformed regex — it fails at the network/API layer the moment that model is deprecated upstream, which can be weeks after the code shipped clean.

```python
import re

PROXY_URL_FRAGMENT = 'sairn.vercel.app/api/claude'

def check_hardcoded_model_strings(content):
    findings = []
    lines = content.split('\n')
    model_pattern = re.compile(r'model\s*:\s*[\'"]([\w.\-]+)[\'"]')
    for i, line in enumerate(lines):
        m = model_pattern.search(line)
        if not m:
            continue
        nearby = '\n'.join(lines[max(0,i-15):i+15])
        if PROXY_URL_FRAGMENT not in nearby:
            continue
        findings.append(f"HIGH line {i+1}: hardcoded model '{m.group(1)}' sent to SAIRN proxy — "
                         f"remove and let the proxy choose the model, matching every other call site")
    return findings
```

**FAIL condition:** Any hardcoded model string → fix before push (not a hard stop, since it works until the model is deprecated, but must be tracked and resolved).

---

#### CHECK 13 — Cross-Script-Block Variable Redeclaration

**Added June 16, 2026, after Checks 9-12 still let a real bug ship to production.** `var APP_ID = 'stonedesk';` was declared in two separate `<script>` tags in StoneDesk. Check 9 (Node ground-truth) validates each script block in ISOLATION and passed cleanly on both — the collision only exists once a browser combines multiple `<script>` tags into one shared global scope, which a per-block Node `--check` cannot simulate. In a real browser: two `var X` declarations of the same name silently merge with no error in normal (non-strict) script context, but if EITHER block opens with `'use strict'`, or either declaration uses `let`/`const` instead of `var`, redeclaring a name that already exists in the shared global scope is a **hard SyntaxError that aborts the entire script tag at parse time, before a single line of it runs.** This is exactly what crashed StoneDesk live — `Identifier 'APP_ID' has already been declared` — which then cascaded into a dozen unrelated "X is not defined" errors for every function that was meant to be registered by scripts that never got to execute.

A full platform audit the same day found this exact `APP_ID`/`PROXY`/`BRIDGE` collision, in some combination of `var`/`var` (silently fragile) or `var`/`const` (unconditionally fatal), in **all 11 of 11 SAIRN B2B apps** — traced to a platform-wide patch session (the "SAIRN Intelligence Network" / "SAIRN CORE" block) that re-declared constants every app already had from its earlier "SAIRN CLAUDE ENGINE" block, instead of reusing them.

```python
import re

VAR_DECL_PATTERN = re.compile(r'^\s*(var|const|let)\s+(\w+)\s*=')
STRICT_MODE_PATTERN = re.compile(r'^\s*[\'"]use strict[\'"]\s*;?\s*$')

def find_top_level_var_declarations(content):
    """
    Returns dict: name -> list of (line_number, script_block_index, decl_kind,
    block_is_strict) for every var/const/let declared at TRUE top level of a
    <script> tag -- using REAL BRACE-DEPTH TRACKING relative to that script
    tag's own opening, not leading whitespace. This deliberately differs from
    Check 10's duplicate-function detector, which abandoned brace counting
    because a syntax error anywhere upstream would desync a naive counter for
    everything downstream -- exactly the failure mode Check 10 exists to
    catch. Check 13 doesn't have that problem: it only ever runs on a file
    that has ALREADY passed Check 9, so brace counting is safe here. (An
    earlier version of Check 13 used leading-whitespace as its top-level
    proxy and produced 13 false positives on StoneDesk alone -- every var
    sitting inside a column-0-indented `(function(){ ... })();` "install
    once" IIFE wrapper, a very common SAIRN pattern, looked top-level by
    indentation but is genuinely scoped to its own IIFE.)
    """
    occurrences = {}
    lines = content.split('\n')
    script_block_idx = -1
    block_is_strict = False
    depth = 0
    for i, line in enumerate(lines):
        if re.search(r'<script(?![^>]*\bsrc=)[^>]*>', line, re.IGNORECASE):
            script_block_idx += 1
            block_is_strict = False
            depth = 0  # depth resets per script tag
        if STRICT_MODE_PATTERN.match(line):
            block_is_strict = True
        m = VAR_DECL_PATTERN.match(line)
        if m:
            kind, name = m.groups()
            if depth == 0:
                occurrences.setdefault(name, []).append((i + 1, script_block_idx, kind, block_is_strict))
        depth += line.count('{') - line.count('}')
        if depth < 0:
            depth = 0
    return occurrences

def check_cross_block_variable_collisions(content):
    findings = []
    decls = find_top_level_var_declarations(content)
    for name, occs in decls.items():
        block_indices = set(o[1] for o in occs)
        if len(block_indices) < 2:
            continue  # same block -- that's Check 9's job
        any_strict = any(o[3] for o in occs)
        any_let_or_const = any(o[2] in ('let', 'const') for o in occs)
        severity = 'CRITICAL' if (any_strict or any_let_or_const) else 'WARN'
        findings.append((severity, name, [o[0] for o in occs]))
    return findings
```

**Verification note:** because the brace-depth tracking here is "good enough, not perfect" (it doesn't distinguish a block-statement `{` from an object-literal `{`), always spot-check 2-3 findings by hand before bulk-fixing, the same as every other Guardian check. In practice, on real SAIRN files this has produced zero false positives once IIFE-scoping was handled correctly — the remaining risk is theoretical, not something that's actually bitten this skill yet.

**Fix pattern:** do NOT blindly delete every duplicate. Check what's genuinely unique in each colliding block first (the StoneDesk fix kept a new `NET_URL` constant from the second block while removing only the redundant `APP_ID`/`PROXY`/`BRIDGE`; the sairnbuild fix had to handle 3 separate blocks, each needing slightly different treatment based on what else in that block actually used the colliding name). Confirm with a plain grep which block's declaration is actually load-order-safe to keep (a `const` from a later block can't be referenced by code earlier in the file, so if an earlier block calls something that needs the value before the later block has run, you cannot simply delete the earlier declaration — verify this before fixing, every time).

**FAIL condition:** Any CRITICAL finding → BLOCK push, this is a guaranteed live crash, not a maybe. WARN findings (plain `var`/`var`, no strict mode anywhere involved) don't block but should still be consolidated — they're one future `'use strict'` patch away from becoming the same crash with zero warning.

---

#### CHECK 14 — Orphaned Content Outside Script Tags

**Added June 16, 2026, after the same bug class shipped THREE separate times in one session despite Checks 1-13 all passing.** Every prior check assumes it's already looking at real `<script>` content — none of them check the gaps *between* tags. StoneDesk had three distinct stretches of real, working JavaScript (a demo-data seeder, a range-bar/empty-state renderer, an admin-formula editor) sitting completely outside any `<script>` wrapper, because an edit somewhere deleted an opening `<script>` tag or inserted a stray `</body>` mid-file. None of this throws a console error — the browser just renders the function bodies and JSON literals as literal visible text on the page, which only shows up as "I see code on my screen" from the user, not as a stack trace Claude can grep for.

**The rule:** Before any push, scan two signals: (1) any bare `</body>` that isn't the true final closing tag at end-of-file — a mid-file `</body>` is almost always a sign of a duplicated/misplaced tail section; (2) any stretch of content between a `</script>` and the next `<script>` that matches JS syntax markers (`function name(`, `var`/`const`/`let` declarations, `document.addEventListener`, `window.x = function`, `win.document.write/close`, IIFE closers `})();`) — real HTML between script tags is normal and expected, but JS-shaped text there means a wrapper went missing.

```python
import re

def find_premature_body_close(content):
    findings = []
    real_close_pattern = re.compile(r'</body>\s*</html>\s*$', re.IGNORECASE)
    is_real_eof_close = bool(real_close_pattern.search(content.rstrip()))
    for m in re.finditer(r'(?:^|\n)\s*</body>\s*\n', content, re.IGNORECASE):
        line_no = content.count('\n', 0, m.start()) + 1
        tail = content[m.end():].strip()
        if is_real_eof_close and not tail:
            continue  # this IS the real one, nothing follows it
        findings.append(f"CRITICAL line {line_no}: premature </body> with content "
                         f"still remaining after it — likely orphaned content below "
                         f"with no <script> wrapper, or a duplicated tail section")
    return findings

def find_orphaned_content_outside_script(content):
    findings = []
    lines = content.split('\n')
    in_script = False
    gap_lines = []
    js_markers = re.compile(
        r'^\s*(?:async\s+)?function\s+\w+\s*\(|'
        r'^\s*(?:var|const|let)\s+\w+\s*=|'
        r'^\s*document\.addEventListener|'
        r'^\s*window\.\w+\s*=\s*(?:async\s+)?function|'
        r'^\s*win\.document\.(write|close)|'
        r'^\s*\}\)\(\);|'
        r'^\s*\(function\s*\(\)\s*\{'
    )
    for i, line in enumerate(lines, 1):
        opens = bool(re.search(r'<script(?:\s[^>]*)?>', line, re.IGNORECASE))
        closes = bool(re.search(r'</script>', line, re.IGNORECASE))
        was_in = in_script
        if opens and not closes:
            in_script = True
        elif closes and not opens:
            in_script = False
            gap_lines = []
            continue
        if not was_in and not in_script and js_markers.match(line):
            gap_lines.append((i, line.strip()[:80]))
        if (opens or in_script) and gap_lines:
            findings.append({'start_line': gap_lines[0][0], 'end_line': gap_lines[-1][0],
                              'sample': gap_lines[0][1], 'count': len(gap_lines)})
            gap_lines = []
    if gap_lines:
        findings.append({'start_line': gap_lines[0][0], 'end_line': gap_lines[-1][0],
                          'sample': gap_lines[0][1], 'count': len(gap_lines)})
    return findings
```

**Known limitation, accepted rather than over-engineered:** a JS string-literal fragment that happens to start with an HTML-looking tag (e.g. the tail end of a `win.document.write('...</body></html>')` call, orphaned on its own line by a different nearby bug) will NOT be caught by the gap scan, since it starts with `<` and looks like harmless HTML. This is rare debris, not the core failure mode — if Check 9 (Node ground-truth) or Check 13 already flagged the surrounding area, hand-trace that specific spot rather than expecting Check 14 to catch every variant.

**FAIL condition:** Any premature `</body>` finding → BLOCK push, fix immediately by re-wrapping the orphaned content in `<script>...</script>` (verify with Check 9 afterward). Any orphaned-JS-marker finding → BLOCK push, same fix.

---

#### CHECK 15 — App ID Value Mismatch (Silent B2B-Tier Downgrade)

**Added June 16, 2026.** Check 4 already verifies `app_id` is *present* on every proxy call — it never verifies the *value* is the app's real canonical name. `api/claude.js` does an exact-match lookup against a `B2B_APPS` Set to decide Sonnet-vs-Haiku tier, demo rate limit (50/day vs 15/day), and max_tokens ceiling. StoneDesk had 8 call sites sending suffixed values (`'doc_analysis'`, `'followup_gen'`, `'memory_builder'`, `'simplify'`, `'compare'`, `APP_ID + '_vision'`, `'stonedesk_'+role`, `'stonedesk_email_triage'`) instead of plain `'stonedesk'`. Several of these were hidden behind a correct `app_id:"stonedesk"` key earlier in the same object literal — JS object literals silently let the LAST duplicate key win, so the wrong value was the one actually sent, with zero error anywhere. The result: those 8 features quietly ran on Haiku instead of Sonnet, with a tighter token cap and a stricter rate limit, indistinguishable from "working" unless someone compared response quality call-by-call.

**The rule:** Every `app_id` value sent to the SAIRN proxy must exactly match the file's own canonical app name (e.g. `stonedesk.html` → `'stonedesk'`, never a suffixed or different value). Check the LAST `app_id` key if an object literal has more than one, since that's the one JS actually sends.

```python
import re

def check_app_id_mismatch(content, canonical_app_id):
    findings = []
    # Find every JSON.stringify({...}) or object literal passed to the proxy,
    # extract ALL app_id keys within it, keep only the LAST (JS dup-key rule)
    obj_pattern = re.compile(r'\{[^{}]*?app_id\s*:\s*[^,}]+[^{}]*?\}', re.DOTALL)
    for m in obj_pattern.finditer(content):
        block = m.group(0)
        line_no = content.count('\n', 0, m.start()) + 1
        app_id_keys = re.findall(r'app_id\s*:\s*([^,}]+)', block)
        if not app_id_keys:
            continue
        last_value = app_id_keys[-1].strip().strip('"\'')
        if last_value == canonical_app_id:
            continue
        if last_value.startswith(canonical_app_id) or last_value.startswith('APP_ID'):
            findings.append(f"CRITICAL line {line_no}: app_id resolves to '{last_value}', "
                             f"not canonical '{canonical_app_id}' — proxy's B2B_APPS lookup is "
                             f"exact-match, this call silently downgrades to Haiku tier with "
                             f"tighter rate limits")
    return findings
```

**Verification note:** the regex is intentionally permissive (it can't fully parse nested JS objects), so always confirm each finding by hand before fixing — look at the actual object literal and identify which `app_id` key is genuinely last in source order, not just last in the regex match.

**FAIL condition:** Any mismatch → fix before push (not a hard crash, but a real product-quality regression that's invisible without comparing model tier — treat as high priority, same urgency as Check 12's stale model strings).

---

#### CHECK 16 — Price Consistency Between Generated Documents and Live App

**Added June 16, 2026.** A dollar amount changed in a generated sales/legal document (StoneDesk's extended warranty packages were raised $100 each at the user's request: $149→$249, $349→$449, $699→$799) and the change was applied to the document only — the live app's `onclick="addWarrantyToJob('Basic Protection',149,1)"` calls were never touched, because the document and the app source are two separate files that nothing automatically keeps in sync. This is a price quietly living in two places and drifting apart, the same root-cause shape as Check 13's variable collision or Check 15's app_id mismatch, just at the business-logic layer instead of the code layer.

**The rule:** Whenever a price, term length, or package detail changes in a generated customer-facing document (warranty terms, pricing sheet, sales deck, SOP), check whether the same number is hardcoded anywhere in the live app (HTML onclick attributes, JS constants, pricing config objects) for the matching package/plan/item name. If it is, flag it — don't assume the document and the app were updated together just because they were edited in the same session.

```python
import re

def extract_dollar_terms_from_doc_text(text):
    """name -> price, from headings/labels like 'Basic Protection — $249'."""
    findings = {}
    for m in re.finditer(r'([A-Za-z][A-Za-z\s]{2,40}?)\s*[—\-]\s*\$(\d[\d,]*)', text):
        name = re.sub(r'^\d+\.\s*', '', m.group(1)).strip()
        findings[name] = int(m.group(2).replace(',', ''))
    return findings

def extract_dollar_terms_from_app_js(content, fn_name):
    """name -> [prices], from onclick="fnName('Label', NUMBER, ...)" call sites."""
    findings = {}
    pattern = re.compile(rf"{re.escape(fn_name)}\(\s*['\"]([^'\"]+)['\"]\s*,\s*(\d+)")
    for m in pattern.finditer(content):
        findings.setdefault(m.group(1).strip(), []).append(int(m.group(2)))
    return findings

def check_price_consistency(doc_text, app_content, app_fn_name):
    doc_prices = extract_dollar_terms_from_doc_text(doc_text)
    app_prices = extract_dollar_terms_from_app_js(app_content, app_fn_name)
    findings = []
    for doc_name, doc_price in doc_prices.items():
        matched = next((a for a in app_prices
                         if a.lower() in doc_name.lower() or doc_name.lower() in a.lower()), None)
        if matched and doc_price not in app_prices[matched]:
            findings.append(f"PRICE DRIFT: document '{doc_name}' = ${doc_price}, "
                             f"app's {app_fn_name}('{matched}',...) uses ${app_prices[matched][0]}")
    return findings
```

**Verification note:** name matching is intentionally fuzzy (substring match on package name), so confirm each finding by hand — a generic name like "Basic" could coincidentally substring-match something unrelated in a larger file. This check requires both the document's extracted text and the app's source as separate inputs; it doesn't run as part of the single-file Phase 2 scan and should be triggered explicitly any time a generated document with prices is delivered alongside (or shortly after) edits to a live app's pricing.

**FAIL condition:** Any drift → ask the user which value is correct before changing either side. Do not assume the document is right and silently patch the app, or vice versa — the user may have intentionally changed only one side.

---

#### CHECK 17 — Legal Document Defensibility Baseline

**Added June 16, 2026.** A first-draft warranty terms document (StoneDesk's three extended-warranty packages) was generated complete and well-organized, but needed two follow-up rounds before it was safe to call a customer-facing legal document: one to add multi-state defensibility (severability, governing-law, state-rights disclosure, removing an unenforceable blanket damages waiver), and the user had to ask for both rounds explicitly. This is a checklist, not a regex scan — legal adequacy can't be pattern-matched — but the checklist itself should be applied automatically on the FIRST draft of any customer-facing legal document, not only when asked.

**Triggers:** any generated warranty terms, Terms of Service, Acceptable Use Policy, Data Privacy Addendum, SOP that customers sign, or similar document intended to be presented to or signed by an end customer (not internal SAIRN business documents, which don't need this).

**The baseline checklist — apply by default, every time:**

1. **State-rights disclosure.** Include language equivalent to "this warranty gives you specific legal rights; you may also have other rights which vary by state" — standard under federal Magnuson-Moss Warranty Act practice for written consumer warranties, and broadly safe to include regardless of which state the customer is in.
2. **No blanket damages waiver.** Never write an unconditional "we are not liable for any incidental or consequential damages" with no qualifier — several states refuse to enforce this as written. Always pair it with "to the extent permitted by the law of the state where [the installation/service] is located" or an equivalent carve-out, and note that the limitation does not apply where state law prohibits it.
3. **Severability clause.** Include a clause stating that if any provision is found unenforceable under applicable state law, that provision is limited or severed, and the rest of the document remains in force. Without this, one bad clause can risk the whole document.
4. **Governing law tied to a variable, not a fixed state.** Default to "the law of the state where the installation/service/customer is located" rather than naming SAIRN's home state (Ohio) outright — naming one fixed state in a document meant to be used nationally creates exactly the cross-state risk this checklist exists to avoid.
5. **No unauthorized-repair clause that voids unrelated coverage.** If the document includes a clause voiding coverage when a customer or third party performs unauthorized repairs, scope the voiding to the specific affected area/damage, not the entire remaining warranty — broad voiding clauses are a common point states strike down or narrow.
6. **Plain, conspicuous language.** Several states require warranty terms to be "clear and conspicuous." Avoid dense legalese where a plain-language sentence says the same thing; this also makes the document easier for Michael's customers to actually read and trust.
7. **Template/review footer.** Every generated legal document includes a visible note that it is a template and should be reviewed by an attorney licensed in the state(s) where the business operates before use. This is not optional and is not a hedge to skip once the user seems satisfied — it stays in every version, including final ones, until the user explicitly confirms attorney review has happened.

**FAIL condition:** Any customer-facing legal document delivered without items 1, 2, 3, 4, and 7 above → treat as an incomplete first draft, not a finished deliverable, regardless of whether the user asked for multi-state coverage. Apply the checklist proactively; don't wait for the user to ask a second time the way this session required.

---

#### CHECK 18 — Last-Def-Wins Function Body Mismatch (silent logic break, not a crash)

**Added June 16, 2026.** SAIRNbiz's login screen showed PIN tiles and 4 separate digit boxes (`id="p0"`..`"p3"`), but entering any correct PIN never logged in. Two `function doLogin() {...}` declarations existed in separate `<script>` blocks -- not a Check 13 crash (no SyntaxError, each block is syntactically independent `var`-style function redeclaration, which is legal JS), but the SECOND one silently won and called `findPinInput()`, a helper that only ever looked for single-input element ids (`pin-in`, `auth-password`, etc.) that did not exist anywhere in the actual markup. The first, dead `doLogin()` correctly read the 4-digit boxes but never ran. Login could never succeed, with no console error at all -- the function executed fine, it just always read an empty string. A second, compounding bug in the same file: `DEFAULT_PINS` listed keys `hr`/`staff`, but the live role tiles called `selectRole('manager')`/`selectRole('employee')` -- two of four roles' PINs silently fell back to a hardcoded `'1234'` default instead of their real configured PIN, working only by coincidence for Owner/Admin.

**Why Checks 9-17 all missed this:** Check 9 (syntax) passes -- both `doLogin` bodies are valid JS. Check 10 (duplicate globals) WARNS on the redeclaration but treats it as cosmetic/low-priority by default, since most duplicate-global findings in this codebase ARE cosmetic. Check 13 (cross-block collision) only fires on `const`/`let` hard crashes, and `function` redeclaration via `var`-style hoisting is not a SyntaxError. None of the 17 checks verify that a function's BODY actually does what the surrounding markup needs -- they verify the file parses and doesn't crash, not that last-def-wins picked the version that's actually correct.

**What to check, specifically:**
1. When Check 10 finds a duplicate function name, do not treat it as automatically low-priority. Pull BOTH bodies and read them. If they do meaningfully different things (not just trivial formatting differences), determine which one actually wins (last `<script>` block in document order) and verify THAT one is the complete/correct implementation -- not the one that happens to be more thorough or "looks more finished."
2. For any login/auth/PIN-check function specifically: confirm the input-reading code (`document.getElementById(...)`, `.value`, `querySelector(...)`) actually matches real ids/selectors present in the surrounding HTML markup, not ids that sound plausible or were used in an earlier draft of the UI.
3. For any role-keyed config object (`DEFAULT_PINS`, `ROLE_LABELS`, `PINS`, etc.), grep every `onclick`/`selectRole(...)`/`data-role` call site in the markup and confirm every role string actually used in the HTML has a matching key in the config object. A silent fallback default (`|| '1234'`) hides this exact class of bug -- treat any such fallback in role/PIN logic as a flag to verify, not a safe default.
4. This check applies with extra weight to LOGIN flows specifically, since a broken login is a total-failure bug (the user cannot do anything else in the app) but produces zero console errors and zero visual sign of what's wrong -- it just "does nothing," which looks identical to a slow network call or a missing click handler from the outside.

**FAIL condition:** any duplicate function name where the LAST (winning) definition references DOM ids/selectors not present in the actual rendered markup, or any role-keyed config object missing a key for a role string actually used in an `onclick`/`data-role` call site in the same file.

---

#### CHECK 19 — Execute, Don't Eyeball (mandatory before declaring ANY fix verified)

**Added June 16, 2026.** Two real failures in one session, both from the same root cause: reading code and reasoning about what it "should" do, instead of actually running it.

Failure 1: a `doLogin()` fix removed `var pinEl = findPinInput();` but left `if (pinEl) pinEl.value = '';` three lines later. This was read by eye multiple times and judged "fixed" before being pushed -- the dangling reference was only caught after the user reported a live `ReferenceError` from their own browser console, which is the exact failure this check exists to prevent from reaching the user at all.

Failure 2: an hour was spent reading `nav()`/`showPage()`/`window.nav` assignments across multiple script blocks, reasoning in prose about which one "should" win and whether `.ni` vs `.nav-item` class mismatches "should" matter, with no actual resolution -- until the code was executed in a real DOM (Node + jsdom) for ten seconds, which immediately proved the function worked exactly as intended. The bug, if one even existed, was never in the code being stared at.

**The rule:** after ANY edit to a function, and before pushing or telling the user something is fixed, do not rely on re-reading the function body to confirm correctness if execution is possible. Specifically:

1. **Syntax-only checks are not behavior checks.** `check_node_groundtruth` / Check 9 proves a file parses. It does NOT prove a function does the right thing when called. Never report a fix as verified on the strength of a clean syntax check alone if the bug being fixed was a logic/runtime bug, not a syntax error.
2. **Grep for the exact variable name across the ENTIRE edited function body, every time a variable is removed or renamed.** `if (pinEl)` three lines after deleting `var pinEl = ...` is exactly the class of mistake eyeballing misses and `grep -c 'pinEl' <body>` catches in one second. Do this as a mechanical, non-optional last step on every edit that removes or renames a variable.
3. **When a question is "does this function behave correctly when called with X," answer it by calling the function, not by reading it and predicting the answer.** A minimal Node+jsdom harness (load the file with `runScripts:'dangerously'`, call the function, inspect the resulting DOM state) takes under a minute to write and removes all ambiguity. Prose reasoning about hoisting order, which of three duplicate functions "wins," or what a class mismatch "should" do is a sign to stop reasoning and start executing.
4. **This is not optional for "I'm fairly confident" cases.** The nav() investigation involved real, correct technical reasoning at every step (hoisting rules, override order, CSS specificity) -- and still cost an hour with no answer, because confidence from reading code is not the same as confirmation from running it. Default to executing whenever a function's runtime behavior is in question, not just when reading hasn't resolved it after N minutes.

**FAIL condition:** declaring a fix "verified," "clean," or "should work now" based on re-reading the edited code, when the original bug was a behavioral/logic bug (not a pure syntax error) and execution was possible but skipped.

---

Run when a Supabase patch has been injected or when the app connects to Supabase.

**What to verify:**
```python
SUPABASE_CHECKS = {
    'client_init': ['supabase.createClient', 'SUPABASE_URL', 'SUPABASE_KEY'],
    'rls_awareness': ['RLS', 'row level security', 'auth.uid()'],
    'error_handling': ['.catch(', 'try {', 'if (error)'],
    'no_key_exposure': [],  # anon key in frontend is OK; service_role key is NOT
}

FORBIDDEN_IN_FRONTEND = ['service_role', 'SERVICE_ROLE']

def check_supabase(content):
    findings = []
    has_supabase = 'supabase' in content.lower()
    if not has_supabase:
        return []
    
    # Hard stop: service_role key in frontend
    for forbidden in FORBIDDEN_IN_FRONTEND:
        if forbidden in content:
            findings.append(f"CRITICAL SECURITY: '{forbidden}' key found in frontend — NEVER expose this key. Use anon key only.")
    
    # Verify error handling on Supabase calls
    has_from = '.from(' in content
    has_error_handling = 'if (error)' in content or '.catch(' in content or 'try {' in content
    if has_from and not has_error_handling:
        findings.append("Supabase .from() calls found without visible error handling — add try/catch or if(error) checks")
    
    # Warn if RLS not mentioned (may be intentional but worth flagging)
    if has_from and 'rls' not in content.lower() and 'auth.uid' not in content.lower():
        findings.append("WARN: Supabase queries present but no RLS reference found — verify Row Level Security is configured in Supabase dashboard")
    
    return findings
```

---

### PHASE 4 — File Naming Enforcer

**The rule:** Every file delivered for GitHub upload must have a descriptive suffix so Michael knows exactly what to do with it. Never plain names.

**Check on every file output:**
```python
REQUIRED_SUFFIX_PATTERNS = ['UPLOAD TO GITHUB', 'UPLOAD', 'PUSH TO', 'DEPLOY']

def check_file_naming(filename):
    findings = []
    # Only applies to deliverable HTML/JS/CSS files, not scripts or temp files
    if filename.endswith(('.html', '.js', '.css', '.jsx', '.ts', '.tsx')):
        has_suffix = any(p in filename.upper() for p in REQUIRED_SUFFIX_PATTERNS)
        if not has_suffix:
            findings.append(f"FILE NAME '{filename}' missing action suffix — rename to '{filename.replace('.html', '')} UPLOAD TO GITHUB.html'")
    return findings
```

---

### PHASE 5 — Push Protocol

Only push when ALL checks pass (or all FAILs are resolved). Use the Python urllib push method — never curl for large files.

```python
def push_to_github(pat, repo, filename, local_path, sha, commit_message):
    with open(local_path, 'rb') as f:
        content = base64.b64encode(f.read()).decode('utf-8')
    
    payload = json.dumps({
        "message": commit_message,
        "content": content,
        "sha": sha
    }).encode('utf-8')
    
    req = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/contents/{filename}",
        data=payload,
        method="PUT",
        headers={
            "Authorization": f"token {pat}",
            "Content-Type": "application/json",
            "User-Agent": "Python"
        }
    )
    
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
        return data['commit']['sha'], data['commit']['html_url']
```

**Commit message format:**
```
fix: [what was fixed] — Guardian scan [N] issues resolved
```
or
```
feat: [what was added] — Guardian scan PASS all 8 checks
```

---

## Scan Report Format

After every scan, output a clean Guardian Report before any fixes:

```
=== SAIRN CODE GUARDIAN SCAN ===
File: [filename]
Lines: [count] | Size: [KB] | SHA: [first 8 chars]

CHECK 1 — JS String Integrity:     [PASS / FAIL: N findings]
CHECK 2 — Unicode Box Chars:       [PASS / FAIL: N findings]
CHECK 3 — Regex Newline Safety:    [PASS / FAIL: N findings]
CHECK 4 — Proxy Compliance:        [PASS / FAIL: N findings]  ← HARD STOP IF FAIL
CHECK 5 — Print Render:            [PASS / WARN / FAIL]
CHECK 6 — Bridge Sync:             [PASS / SKIP (NEXUS) / FAIL]
CHECK 7 — Role Gates:              [PASS / WARN / FAIL]
CHECK 8 — Color Compliance:        [PASS / WARN / FAIL]
CHECK 9 — Node Ground-Truth:       [PASS / FAIL: N findings]  ← HARD STOP IF FAIL
CHECK 10 — Duplicate Globals:      [PASS / WARN / FAIL]        ← HARD STOP IF load-bearing name unchained
CHECK 11 — Regex Literal Sanity:   [PASS / FAIL: N findings]  ← HARD STOP IF comment-trap found
CHECK 12 — Stale Model Strings:    [PASS / WARN: N findings]
CHECK 13 — Cross-Block Var Collision: [PASS / FAIL: N findings] ← HARD STOP IF CRITICAL (real browser crash)
CHECK 14 — Orphaned Content Outside Script: [PASS / FAIL: N findings] ← HARD STOP IF FAIL (text renders on live page)
CHECK 15 — App ID Value Mismatch:  [PASS / FAIL: N findings]  ← fix before push (silent Haiku downgrade)
CHECK 16 — Price Consistency (doc vs app): [PASS / FAIL: N findings / SKIP no doc to compare] ← ask user before fixing either side
CHECK 17 — Legal Doc Defensibility:  [PASS / FAIL: N items missing] ← applies only to customer-facing legal documents
CHECK 18 — Last-Def-Wins Logic Mismatch: [PASS / FAIL: N findings] ← HARD STOP IF login/auth function affected (silent total-failure bug)
CHECK 19 — Execute Don't Eyeball:    [PASS / FAIL: N functions only eyeballed, not executed] ← mandatory before reporting any logic/runtime fix as verified
BONUS    — Supabase Schema:        [PASS / SKIP / FAIL]

TOTAL FINDINGS: [N critical] [N warnings] [N info]
STATUS: [CLEAR TO PUSH / FIX REQUIRED / HARD STOP]
================================
```

Then list every finding with exact line numbers, severity, and fix applied.

Then push.

---

## SAIRN Universal Pattern Checklist

Before closing any build session, verify all 11 universal patterns from "the first" are present in every B2B app:

| # | Pattern | Check |
|---|---|---|
| 1 | Role-based PIN auth | `pin`, `role`, `9999` or equivalent |
| 2 | Structured intake form | Form elements with labeled fields |
| 3 | Live calculation engine | Real-time formula updates |
| 4 | Line item breakdown | Itemized cost/detail display |
| 5 | Range bar benchmarking | Visual range/comparison bars |
| 6 | Smart flags | Conditional warning/alert system |
| 7 | Save + history | LocalStorage or Supabase save pattern |
| 8 | Print with signature lines | `window.print()` + sig-row elements |
| 9 | Clean client view | Separate view hiding internal pricing |
| 10 | Admin formula editor | Editable formula/config panel |
| 11 | CSV stress test | CSV import/export functionality |
| 12 | Weather Command Engine | Present in: SAIRNscape, SAIRNbuild, StoneDesk, SAIRNdesign, SAIRNlaw ONLY |

**Pattern 12 inclusion rule:**
- INCLUDE weather: SAIRNscape, SAIRNbuild, StoneDesk, SAIRNdesign, SAIRNlaw
- EXCLUDE weather: SAIRNcode, SAIRNhr, SAIRNacc, SAIRNvet, SAIRNvetGlobal, SAIRNcare, ALL NEXUS apps
- Test: *Do crews go outside to do this work?* Yes = include. No = skip.

---

## Hard Rules — Never Violated

These are absolute stops. No exception. No override.

| Rule | Violation Action |
|---|---|
| No direct `api.anthropic.com` calls | BLOCK push immediately |
| No `service_role` key in frontend | BLOCK push immediately |
| No blue in non-SAIRNdesign apps | Flag all instances before push |
| No Unicode box chars in JS | Auto-fix, re-scan, then push |
| No dark backgrounds (print rule) | Flag, suggest light alternative |
| No file delivered without action suffix | Rename before presenting |
| No Compensation module without role gates | Flag, cannot ship |
| Bridge required in all B2B apps | Flag missing touchpoints |
| Every inline `<script>` block must pass `node --check` | BLOCK push immediately |
| No unchained duplicate of a load-bearing function name | BLOCK push immediately |
| No regex literal starting with `/*` or `/**` (JS comment trap) | BLOCK push immediately |
| No hardcoded model string in a SAIRN-proxy fetch call | Flag, fix before next push |

---

## GitHub Workflow Reference

**Always use Python urllib for files over ~100KB. Never curl for large files.**

```
Pull → Scan (8 checks) → Fix → Verify fix → Push → Confirm SHA
```

**PAT storage:** Michael's PAT is provided at session start. Never hardcode in delivered files. Never log to output. Use only in-session for GitHub API calls.

**Repo:** `SAIRN1/SAIRN`
**Branch:** `main` (default)

---

## Activation Summary

The Guardian activates automatically when:
1. A SAIRN file is being built or modified
2. A GitHub push is requested
3. Something is broken and needs diagnosis
4. A Supabase patch has been injected
5. A new app build session begins
6. User says any variant of: check, scan, push, fix, audit, broken, not loading, syntax error

The Guardian does not wait to be asked. It runs. It reports. It fixes. It pushes.

*No SAIRN app ships without passing all 12 checks.*

---

## A Note On False Positives (Checks 9-13)

Checks 1-8 are exact pattern matches with very low false-positive rates. Checks 9-13 involve more judgment, and during development against the real StoneDesk corruption, each one produced at least one false positive that had to be tracked down and fixed in the detection logic itself before the check could be trusted:

- **Check 9** initially mis-split blocks on escaped `<\/script>` sequences inside JS strings (fixed with a negative lookbehind) and on adjacent `</script><script>` tags handled by a line-by-line scanner instead of a single global regex pass (fixed by switching to `re.finditer`).
- **Check 10** initially flooded with hundreds of false positives from local variables (`var x`, `const r`) declared inside different, properly-scoped functions, because an early version used a brace-depth counter to decide "global" — and that counter drifted off-true the moment it crossed an actual unterminated string elsewhere in the file (the exact bug Check 9 exists to find), silently hiding the real `doLogin` and `tryInstall` collisions in the process. The fix was to stop trusting brace-depth as the primary signal and use indentation plus explicit `window.X = X` export tracking instead.
- **Check 10** also initially flagged the safe "declare then immediately export" pattern (`function selRole(){...} window.selRole = selRole;`) as a 2x collision; fixed by requiring 2+ DISTINCT function bodies before counting an export as evidence of a collision.
- **Check 13** initially used leading-whitespace as its "is this top-level" signal (deliberately copying Check 10's approach) and produced 13 false positives on StoneDesk alone — every `var` sitting inside a column-0-indented `(function(){ ... })();` "install once" IIFE wrapper looked top-level by indentation but is genuinely scoped to its own IIFE, never colliding with anything outside it. The fix was the OPPOSITE of Check 10's: switch TO real brace-depth tracking, which is safe here specifically because Check 13 only ever runs on a file that has already passed Check 9 (no syntax errors to desync the counter) — the exact precondition that made brace-depth tracking unsafe for Check 10 doesn't apply to Check 13.

If a future finding from Checks 9-13 looks wrong, the right move is the same one used here: verify against the actual source at the cited line number, and if it's a genuine new false-positive class, fix the detection logic and document the fix inline the way the four above are documented — don't just suppress the finding silently.
