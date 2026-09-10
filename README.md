# Benny-AI

A private, personal agent that grows by motherboard (model) upgrades — never by rebuilding.

## State (read this first if you come back later)

- **Body: DONE** (v0.1) — memory (recombination engine) + 4 tools (files/system/code-exec/web) + security (device-lock) + default-deny gatekeeper + pluggable brain + terminal TUI.
- **Brain: LIVE on GitHub Copilot** (v0.2) — the user's own GitHub Copilot plan drives an OpenAI-compatible `/chat/completions` endpoint (`api.githubcopilot.com`) authenticated with the same token `gh` CLI uses. No extra key, no signup. Models confirmed on this plan: `gpt-4.1` (heavy), `gpt-4o`, `gpt-4o-mini` (default), `gpt-3.5-turbo`.
- Two-model router: routine requests → `gpt-4o-mini` (fast), long/deep-reasoning requests → `gpt-4.1` (brain).
- Falls back to a rule brain (offline, no smarts) if no token is found; Gemini adapter still ships if you ever want it.
- ₹0, pure Python stdlib, zero third-party deps. 8GB-friendly: no local model resident, so RAM stays free.
- Run it: `python -m benny`
- Test it: `python scripts\smoke_test.py` (core) + `python scripts\brain_check.py` (live Copilot probe)

## Token resolution (CopilotBrain)

Order: `config/secrets.json` → env `GITHUB_TOKEN` → `gh auth token` (OS keyring). No config needed if `gh` is already authenticated.