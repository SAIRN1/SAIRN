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

## Model Selection
- Default: Sonnet 5 High for all routine work (implementation, debugging, most fixes)
- Proactively recommend switching to Opus 4.8 for: hard debugging with an unclear root cause, or security-critical code
- Proactively recommend opusplan mode for: architecture/design decisions (new systems, schema design, anything with real tradeoffs to weigh)
- Once the Opus/opusplan-level work is done, proactively recommend switching back to Sonnet 5 High for the routine implementation that follows — don't stay on Opus by default
- State the recommendation clearly (e.g. "This looks like a hard-debugging case — worth switching to Opus 4.8") rather than silently staying on whatever model is currently active

---
*Last Updated: 2026-07-23*
