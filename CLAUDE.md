# StoneDesk Development Guidelines

## SYNTAX RULE
**Run Node --check before touching any file. Zero errors before any changes. Zero errors before any push. Never bulk replace.**

Always:
1. Extract and test each script block with `node --check` individually
2. Fix one error at a time, then recheck
3. Verify zero errors before committing changes
4. Use targeted, precise edits - never bulk find-replace across the codebase

## Project Context
- Codebase: stonedesk.html (1.9MB single-file app)
- 113 total `<script>` blocks
- **Current Status: 95/106 scripts passing Node syntax validation (89.6%)**

## Known Issues
- Scripts 26, 34, 37, 58, 79, 80, 81, 89, 109, 111, 113 have syntax errors
- Most are multi-line string formatting or quote escaping issues
- Fix approach: Extract, identify, fix one line, retest, repeat

## Tech Stack
- Frontend: Vanilla JavaScript  
- Backend: SAIRN API Proxy (Claude integration)
- Deployment: Vercel

## Response Style
- No narration before or after actions — act, then report only the result
- No "let me check / good news / confirmed" commentary
- On error: state what failed and what's needed, nothing more

---
*Last Updated: 2026-07-22*
