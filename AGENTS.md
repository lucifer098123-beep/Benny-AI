# Benny-AI

Private personal AI agent, named after the assistant's own model. Privacy-first, self-owning, grows by motherboard (model) upgrades.

## Core principle (the motherboard theory)
- Never weld learning into the model.
- Always keep memory + tools + security model-agnostic.
- Upgrade the model when hardware allows; nothing rebuilds.
- The model is the load-bearing engine, not scaffolding.

## Stack (v1 target)
- **Brain: GitHub Copilot API** (`api.githubcopilot.com`) — OpenAI-compatible, authenticated by the user's own `gh` token. Models: `gpt-4o-mini` (routine) + `gpt-4.1` (heavy). No local inference, no RAM tax, ₹0.
- Python 3.14 — agent core
- Hardware: 8GB RAM / Intel UHD / Windows 11 / CPU-only
- Offline fallbacks: rule brain (no token) or Gemini adapter (optional key)

## Architecture
Router (rule-based: cheap model for routine, heavy for deep requests) → CopilotBrain.
Tools (files/system/code/web) + free-floating memory + security + default-deny gatekeeper.

## Security
VeraCrypt AES-256 + hardware fingerprint (UUID/mobo/CPU) + auto-lock + tamper response + dead-man's switch + device binding + decoy data.

## Gatekeeper (EXTRA-HARD)
Default-deny, allowlist-only, localhost-lock, request classifier, response sanitizer, content-vibe guard (no slop / no belief absorption), approval gate, full audit log. The only outbound path by default is the brain's own model endpoint (fixed in code).

## Status
BODY BUILT (v0.1) + BRAIN LIVE (v0.2, Copilot). Pure Python stdlib, ₹0, runs on 8GB.
- Implemented: memory store (+recombination), files/system/code-exec/web tools, device-lock security, default-deny gatekeeper, pluggable brain (rule fallback + Copilot primary + Gemini adapter), terminal TUI.
- Smoke test: `python scripts\smoke_test.py` → ALL PASSED. Live probe: `python scripts\brain_check.py` → light + heavy both answer.
- Zero third-party deps (psutil/wmi avoided; stdlib only).
- Brain wiring: `config/settings.json` `brain.mode` = copilot|gemini|rule. Copilot token comes from `gh auth token` (keyring), env `GITHUB_TOKEN`, or `config/secrets.json` `github_token` (gitignored).
- Command routing: with a real brain online, only explicit short commands hit the tool handlers (ram / remember / help / prune / fetch…); free-form questions go straight to the model — words like "memory" or "file" inside a question never hijack the conversation.
- Ollama removed (2026-09-10): always-online usage makes a local model a pure RAM tax; the Copilot brain is smarter and leaves all 8GB free. Revisit local models only if a no-internet mode is ever required.

## Webface (browser face, 2026-09-12)
- `webface/` = serene-tech browser UI (aurora backdrop + breathing Siri-style orb). Pure stdlib `http.server`, localhost-only (`127.0.0.1:7749`), zero deps, engine untouched — it's a front door, not a rebuild.
- Run: `scripts\run-webface.cmd` (boots + opens browser) or `python -m webface`.
- Same Agent the TUI uses: device-lock auth on boot, `agent.respond()` per message, memory counter + level badge + latency chips live in the topbar.
- Security stance: gatekeeper auto-answers NO (`ask_callback=False`) — no silent network. An in-UI approval gate is the v2 upgrade alongside a markdown renderer + conversation history.
- Verified: boot + auth, GET / (orb + aurora present), CSS (breathe/morph keyframes), JS, favicon, POST /chat round-trip (mem counter + level + latency returned), py_compile + zero-third-party check green.

## Gemini-style menu + sessions + model port (2026-09-16, webface v0.3)
- **UI rebuilt to Gemini's interaction model** on the serene-tech soul: top bar (hamburger + mini orb + active-chat title + level/mem/lat/eyes chips) replaces the old rail. Slide-out drawer (`transform: translateX(-102%)`, 240ms cubic-bezier, scrim, Esc/✕/scrim close, focus returns to hamburger). `prefers-reduced-motion` snaps it.
- **Session history:** per-session JSON in `webface/data_sessions/` — wait, actual folder is `data/webface_sessions/<12-hex>.json` (uuid hex, persisted across restarts, gitignored under `data/`). Routes: `GET /sessions` (newest-first list), `POST /session` (new), `POST /session?del=<id>` (delete), `GET /session?id=` (messages). "New chat" button POSTs + resets to greeting; list hides empty sessions; active highlighted; hover-reveal delete row; boot restores newest session. Server auto-creates a session on a `/chat` without `session_id` and returns it.
- **Multi-turn context:** `agent.respond(text, history=...)` + `_with_history()` — last 10 turns replayed to the brain per message (session `messages` carry `{role, content, ts}`).
- **Model port (API-key brain swap):** `OpenAIBrain` (generic OpenAI-compatible `/chat/completions`: endpoint + token + model). `build_brain(mode)` now supports `openai|nvidia` (plus existing `copilot|gemini|rule`). `engine.swap_brain(...)` hot-swaps live, persists brain fields to `config/settings.json` + `api_key` to `config/secrets.json` (gitignored), then rebuilds. UI: drawer footer status strip + collapsible **model port** panel showing mode/model/heavy/endpoint/brain-online/vision badges + form (model / endpoint / api-key with eye toggle) → `POST /brain`. Model line stays pluggable — motherboard theory intact.
- **`GET /brain`** → current brain status. **`/health`** now also returns `vision` + `model`.
- Verification: `py_compile` clean; boot test POST `/chat` round-trip returned real benny reply (authority OK) with session create; Playwright headless swept the whole flow (menu open → new chat → send → real reply rendered → session list shows titled rows) with **zero console/page/request errors**. Also fixed the launcher race: `scripts/run-webface.cmd` now polls `/health` (30×1s) BEFORE opening the browser (was "127.0.0.1 refused to connect"). Test sessions + memory episodes purged after QA.

## Eyes + soul (2026-09-12, webface v0.2)
- **Vision lane PROVEN LIVE:** benny looks at an image/gif and describes it — `meta/llama-3.2-11b-vision-instruct` on build.nvidia's free NIM API (`benny/core/vision.py`, VisionBrain). Zero deps, ₹0 key already in `config/secrets.json` (gitignored). Verified: attaches a photo → returns "Yes, there is a car in this image" in ~3.5s through the webface `/see` route.
- **Persona layer:** `persona/identity.md` + `persona/user.md` + `persona/emoji.md` — the full soul: how benny talks, deep read on the user, and the emoji vault (incl. the lost/rare emoji). Loaded into every system prompt on top of the un-editable `config/identity.json` core. Motherboard theory intact: persona is a layer, never a weld.
- **GIF reactions:** `webface/static/gifs/` reaction pack — mood-mapped, served from benny's own box (localhost-only, nothing fetched). Drop files per the README manifest (grin.gif, laugh.gif, t_t.gif, kudos.gif…). Restraint rule: one per punchline.
- **Deploy note:** `meta/llama-3.2-90b-vision-instruct` in nvidia's official sample times out under load — 11b is the real worker. The API's model catalog goes stale (410/404 on dead IDs) — always probe live before wiring a model.

## Next
- Run the live TUI: `python -m benny`.
- (Optional) tune `config/settings.json` brain models or level routing.
- Brain ladder for the Victus (2027, RTX 3050 / 16GB): stays on cloud until a local model beats it on quality-per-RAM.
- Pushed to GitHub: `lucifer098123-beep/Benny-AI` (private).