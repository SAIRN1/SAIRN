# ═══════════════════════════════════════════════════════════════════
#  SAIRN Validator — runs on every GitHub push
#  Blocks deployment if any app has a JavaScript syntax error
#  Michael L. Dibert · SAIRN Technologies · 2026
# ═══════════════════════════════════════════════════════════════════

import os, re, sys, glob

# Find every HTML app file dynamically — grows with the platform
APP_FILES = sorted(glob.glob('*.html'))

if not APP_FILES:
    print("⚠️  No HTML files found — skipping validation")
    sys.exit(0)

print(f"SAIRN Validator — checking {len(APP_FILES)} apps")
print("=" * 60)

ERRORS   = []
WARNINGS = []

for fpath in APP_FILES:
    fname = os.path.basename(fpath)
    try:
        c = open(fpath, encoding='utf-8').read()
    except Exception as e:
        ERRORS.append(f"{fname}: Could not read file — {e}")
        continue

    script_start = c.find('<script>')
    if script_start < 0:
        WARNINGS.append(f"{fname}: No <script> tag found")
        continue

    script = c[script_start:]

    file_errors   = []
    file_warnings = []

    # ── CRITICAL CHECKS (block deployment) ───────────────────────

    # 1. Broken apostrophes in double-quoted JS strings
    broken_apos = re.findall(r'"[a-zA-Z]+\'[a-zA-Z]', script)
    if broken_apos:
        file_errors.append(f"Broken apostrophes in JS strings: {broken_apos[:3]}")

    # 2. Broken contractions where apostrophe became double-quote
    broken_quote = re.findall(r'[A-Za-z]"[a-z]{1,3}\b', script)
    if broken_quote:
        file_errors.append(f"Broken contraction quotes: {broken_quote[:3]}")

    # 3. Odd number of backticks (unclosed template literal)
    backtick_count = script.count('`')
    if backtick_count % 2 != 0:
        file_errors.append(f"Odd backtick count ({backtick_count}) — unclosed template literal")

    # 4. Smart/curly quotes in JS (copy-paste from Word/docs)
    smart_quotes = re.findall(r'[\u2018\u2019\u201c\u201d]', script)
    if smart_quotes:
        file_errors.append(f"Smart/curly quotes found — use straight quotes only")

    # 5. Missing opening quotes (common typo pattern)
    missing_open = []
    for pattern in ["remove( active')", "add( active')", "getElementById( "]:
        if pattern in script:
            missing_open.append(pattern)
    if missing_open:
        file_errors.append(f"Missing opening quotes: {missing_open}")

    # 6. "Morning" references (high vibration policy)
    morning_refs = re.findall(r'[Gg]ood morning|Morning —|Morning!|"morning"', c)
    if morning_refs:
        file_errors.append(f"'Morning' references found — use 'Good day' instead: {morning_refs[:3]}")

    # ── WARNING CHECKS (allow deployment but notify) ──────────────

    # 7. showPage function must exist
    if 'function showPage' not in script:
        file_warnings.append("showPage function not found")

    # 8. sendMessage or send function must exist
    if 'function sendMessage' not in script and 'function send(' not in script:
        file_warnings.append("sendMessage/send function not found")

    # 9. API URL must be correct
    if 'sairn.vercel.app/api/claude' not in script:
        file_warnings.append("API URL not found — may not call Claude")

    # 10. GUIDED_FLOWS should exist
    if 'GUIDED_FLOWS' not in script:
        file_warnings.append("GUIDED_FLOWS not found — no guided flows")

    # 11. loadFirstMessage should exist
    if 'loadFirstMessage' not in script:
        file_warnings.append("loadFirstMessage not found — no greeting")

    # 12. showSaveBar should exist
    if 'showSaveBar' not in script:
        file_warnings.append("showSaveBar not found — no save/share")

    # Report
    if file_errors:
        ERRORS.append((fname, file_errors, file_warnings))
        print(f"  ❌ {fname}")
        for e in file_errors:
            print(f"     ERROR: {e}")
        for w in file_warnings:
            print(f"     WARN:  {w}")
    elif file_warnings:
        print(f"  ⚠️  {fname} — {len(file_warnings)} warning(s)")
        for w in file_warnings:
            print(f"     {w}")
    else:
        print(f"  ✅ {fname}")

print()
print("=" * 60)
if ERRORS:
    print(f"❌ DEPLOYMENT BLOCKED — {len(ERRORS)} file(s) have errors")
    print("Fix all errors above before pushing again.")
    sys.exit(1)
else:
    print(f"✅ ALL {len(APP_FILES)} APPS VALIDATED — deployment approved")
    sys.exit(0)

