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

## Next
- Run the live TUI: `python -m benny`.
- (Optional) tune `config/settings.json` brain models or level routing.
- Brain ladder for the Victus (2027, RTX 3050 / 16GB): stays on cloud until a local model beats it on quality-per-RAM.
- Pushed to GitHub: `lucifer098123-beep/Benny-AI` (private).