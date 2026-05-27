# ═══════════════════════════════════════════════════════════════════
#  SAIRN Linter — AUTO-FIXES common issues before deployment
#  Runs after validator — fixes what it can, reports what it cannot
#  Michael L. Dibert · SAIRN Technologies · 2026
# ═══════════════════════════════════════════════════════════════════

import os, re, sys, glob

APP_FILES = sorted(glob.glob('*.html'))

if not APP_FILES:
    print("⚠️  No HTML files found — skipping lint")
    sys.exit(0)

print(f"SAIRN Linter — auto-fixing {len(APP_FILES)} apps")
print("=" * 60)

# ── AUTO-FIX RULES ────────────────────────────────────────────────
# These are applied to the script section of every app automatically

SCRIPT_FIXES = {
    # Contractions → full words
    "Let's":    "Let us",
    "let's":    "let us",
    "I'm":      "I am",
    "I'll":     "I will",
    "I've":     "I have",
    "I'd":      "I would",
    "you're":   "you are",
    "you'll":   "you will",
    "you've":   "you have",
    "you'd":    "you would",
    "we're":    "we are",
    "we'll":    "we will",
    "we've":    "we have",
    "that's":   "that is",
    "it's":     "it is",
    "there's":  "there is",
    "what's":   "what is",
    "here's":   "here is",
    "What's":   "What is",
    "Here's":   "Here is",
    "he's":     "he is",
    "she's":    "she is",
    "they're":  "they are",
    "they'll":  "they will",
    "don't":    "do not",
    "won't":    "will not",
    "can't":    "cannot",
    "isn't":    "is not",
    "doesn't":  "does not",
    "didn't":   "did not",
    "couldn't": "could not",
    "wouldn't": "would not",
    "shouldn't":"should not",
    "haven't":  "have not",
    "hasn't":   "has not",
    "weren't":  "were not",
    "aren't":   "are not",
    # Morning → Good day (high vibration policy)
    "Good morning!": "Good day!",
    "Good morning.": "Good day.",
    "Morning!":      "Hey!",
    "Morning —":     "Hey —",
    # Broken quote patterns
    "remove( active')":                 "remove('active')",
    "add( active')":                    "add('active')",
    "getElementById( userInput')":      "getElementById('userInput')",
    "getElementById( sairn-save-bar')": "getElementById('sairn-save-bar')",
    "if(role=== ai')":                  "if(role==='ai')",
}

# Regex fixes for broken contraction-quote patterns
REGEX_FIXES = [
    (r'([A-Za-z])"re\b',  r'\1 are'),
    (r'([A-Za-z])"ve\b',  r'\1 have'),
    (r'([A-Za-z])"ll\b',  r'\1 will'),
    (r'([A-Za-z])"t\b',   r'\1 not'),
    (r'([A-Za-z])"m\b',   r'\1 am'),
    (r'([A-Za-z])"s\b',   r'\1 is'),
    (r'([A-Za-z])"d\b',   r'\1 would'),
]

fixed_files = 0
total_fixes = 0

for fpath in APP_FILES:
    fname = os.path.basename(fpath)
    try:
        c = open(fpath, encoding='utf-8').read()
    except:
        continue

    script_start = c.find('<script>')
    if script_start < 0:
        continue

    html_part   = c[:script_start]
    script_part = c[script_start:]
    original    = script_part
    fix_count   = 0

    # Apply string fixes
    for bad, good in SCRIPT_FIXES.items():
        count = script_part.count(bad)
        if count > 0:
            script_part = script_part.replace(bad, good)
            fix_count += count

    # Apply regex fixes
    for pattern, replacement in REGEX_FIXES:
        new_script = re.sub(pattern, replacement, script_part)
        if new_script != script_part:
            fix_count += len(re.findall(pattern, script_part))
            script_part = new_script

    if script_part != original:
        new_c = html_part + script_part
        open(fpath, 'w', encoding='utf-8').write(new_c)
        fixed_files += 1
        total_fixes += fix_count
        print(f"  🔧 {fname} — {fix_count} auto-fix(es) applied")
    else:
        print(f"  ✅ {fname} — clean")

print()
print("=" * 60)
print(f"Linter complete — {total_fixes} fixes across {fixed_files} files")

# If any fixes were made, warn that validator should be re-run
if fixed_files > 0:
    print("⚠️  Files were modified — validator will re-run to confirm")
    sys.exit(2)  # Exit code 2 = fixed but need re-validation
else:
    print("✅ No fixes needed — all apps already clean")
    sys.exit(0)
