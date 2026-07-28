---
name: sairn-app-builder
description: Playbook for turning a SAIRN web app (single-file HTML like stonedesk.html / sairncode.html) into a real DOWNLOADABLE desktop application a customer installs and runs — an actual signed installer, not a web link. Trigger whenever the user wants to "build a downloadable app," "desktop app," "installer," ".exe / .dmg / .msi / .AppImage," "package the app," "make it installable," "ship it as an app," "Electron / Tauri / PWA," code signing, notarization, or auto-update. Covers framework choice, wrapping SAIRN's existing HTML+license-key apps, the build→sign→notarize→distribute→auto-update pipeline, offline behavior, and the toolchain prerequisites. Companion to sairn-client-facing-design (how it looks) and sairn-infra-debugger (backend/deploy).
---

# SAIRN App Builder — downloadable desktop apps

The bar: a customer double-clicks an installer, gets a native window with the SAIRN app inside, no browser chrome, no "unknown publisher" scare, and it updates itself. Everything below exists to clear that bar. Do NOT rebuild the UI — SAIRN apps are already complete single-file HTML apps; a downloadable app *wraps* one, it doesn't recreate it.

## Step 0 — the one decision that determines everything: which shell

SAIRN apps are self-contained HTML files whose only backend is the hosted proxy (`sairn.vercel.app/api/*`) and `localStorage`/license-key state. That makes them ideal to wrap. Pick the shell by these criteria — don't default blindly:

| | **Tauri** (recommended for "small download") | **Electron** (recommended for "ship today") | **PWA** (installable web) |
|---|---|---|---|
| Installer size | ~3–10 MB | ~85–150 MB | 0 (browser installs it) |
| Needs on THIS machine | **Rust toolchain (currently MISSING)** + WebView2 (present on Win11) | **Node only (present)** | nothing |
| Backend in shell | Rust | Node.js | none |
| Auto-update | built-in updater | `electron-updater` | service-worker |
| Real signed installer | yes (.msi/.exe, .dmg, .AppImage) | yes | no (no OS install artifact) |
| Best when | you want a tiny, fast, professional download | you need it working this session, or need Node APIs in the shell | you just want "Add to home screen" with zero packaging |

**Default recommendation for SAIRN:** **Tauri** for the real product (tiny, signs cleanly, auto-updates, looks premium). **Electron** if the user wants it running *today* (Node is already installed; Rust is not). **PWA** only if they explicitly want browser-installable with no installer file. State the trade-off and let the user choose before scaffolding anything.

## Step 1 — toolchain prerequisites (verify BEFORE scaffolding, this machine is Windows x64)

- **Always:** Node + npm (present), git (present).
- **Tauri path also needs:** Rust (`rustup`/`cargo` — currently MISSING; `winget install Rustlang.Rustup` or rustup.rs) and Microsoft **WebView2** runtime (preinstalled on Win11). Verify with `cargo --version` before starting.
- **Electron path:** nothing beyond Node.
- **Signing (both):** Windows needs an **Authenticode code-signing certificate** (OV or EV; EV clears SmartScreen instantly, OV builds reputation over time). macOS needs an **Apple Developer ID** cert + notarization. Cross-OS installers can only be *signed* on their own OS (or via a CI runner per-OS) — you cannot notarize macOS from Windows.

Run a capability check first and report what's present vs. missing, rather than assuming.

## Step 2 — the wrap (don't recreate — embed the existing HTML)

- Copy the target `*.html` (e.g. `stonedesk.html`) into the shell's frontend dir as the loaded entry point. It already contains all CSS/JS inline — no bundler needed.
- **Keep the hosted backend.** The app still calls `https://sairn.vercel.app/api/sd-data`, `/api/claude`, etc. over HTTPS from the webview. Do NOT ship secrets in the bundle — the service-role key stays server-side; the app authenticates with the **license key** exactly as the web version does (`Authorization: Bearer <license_key>`).
- **CSP:** the app's injected CSP `connect-src` must include the hosted origin (`https://sairn.vercel.app`). In a `tauri://`/`file://` webview the page origin changes, so verify fetches to the proxy aren't blocked — allow the SAIRN origins explicitly.
- **localStorage persists** inside the webview per-app, so license key + cached profile/memory/slabs survive restarts, same as the browser.

## Step 3 — build → sign → distribute → auto-update (the part amateurs skip)

1. **Build** the per-OS artifact (Tauri: `cargo tauri build`; Electron: `electron-builder`). Targets: Windows `.msi`/`.exe`, macOS `.dmg`, Linux `.AppImage`/`.deb`.
2. **Code sign** — this is non-negotiable for a professional download. Unsigned Windows apps trigger SmartScreen "unknown publisher"; unsigned/un-notarized macOS apps are blocked by Gatekeeper. Sign with the Authenticode/Developer-ID cert. **macOS also requires notarization** (`notarytool`) + stapling.
3. **Distribute** — host the signed installer (Vercel static, GitHub Releases, or S3). Give a stable download URL per-OS.
4. **Auto-update** — wire the updater (Tauri updater signature / `electron-updater`) to an update manifest so installed apps pull new versions. Without this, downloaded copies rot.

## Step 4 — offline & entitlement behavior (decide explicitly)

- What works with no network? UI renders; `localStorage`-backed panels work; anything hitting `/api/*` (AI chat, cross-device sync, license validation) fails. Decide the graceful-degrade story per feature rather than letting it throw.
- **License/entitlement:** the app validates the license against `license_keys` via the endpoint (same as web). Offline, it should fall back to a cached last-known-good entitlement with a grace window — never hard-lock a paying customer because their wifi dropped, and never trust the cache forever. This is where Pattern 13's entitlement gate meets the desktop reality.

## Verification discipline (same rigor as the web apps)

- The wrapped HTML still gets the triad before packaging: `node tools/checkblocks.cjs <app>.html`, `div_balance_check.py`, `nav_panel_check.py` — a broken build ships a broken app.
- **Smoke-test the packaged app, not just the dev build:** launch the actual installed binary, confirm the window loads, the license key round-trips through `/api/sd-data` (200s), and AI chat returns a real response — a `dev`-mode success is not proof the *signed installer* works.
- Screenshot the running native window (Playwright can't drive Electron/Tauri directly the way it drives a browser — use the framework's own screenshot/e2e harness, e.g. WebDriver for Tauri, Spectron-successor/Playwright-Electron for Electron).

## What NOT to do

- **Don't rebuild the UI** — wrap the existing single-file HTML. Recreating panels loses everything already built and verified.
- **Don't ship an unsigned installer** to a customer — "unknown publisher" destroys trust faster than any design flaw. If a cert isn't ready, say so and treat signing as a release blocker, not a nicety.
- **Don't bundle secrets** — no service-role key, no `ANTHROPIC_API_KEY`, no `sb_secret_` in the app. The bundle is fully inspectable by the user; keep the trust boundary at the hosted proxy + license key.
- **Don't pick Electron reflexively because it's familiar** — for a *downloadable* SAIRN app, a 100 MB Electron download vs. a 6 MB Tauri download is a real first-impression difference. Choose by the criteria table, not habit.
- **Don't claim it's "done" from a dev-server run** — done means: signed installer built, installed on a clean machine, launched, license + AI verified live, auto-update wired.
