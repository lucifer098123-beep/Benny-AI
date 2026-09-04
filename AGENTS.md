# Benny-AI

Offline personal AI agent, named after the assistant's own model. Privacy-first, self-owning, grows by motherboard (model) upgrades.

## Core principle (the motherboard theory)
- Never weld learning into the model.
- Always keep memory + tools + security model-agnostic.
- Upgrade the model when hardware allows; nothing rebuilds.
- The model is the load-bearing engine, not scaffolding.

## Stack (v1 target)
- Ollama (localhost:11434) — model runtime
- Models: Llama 3.2 1B (router, resident) + Llama 3.2 3B (workhorse, resident) + Qwen3 8B (brain, lazy-load)
- Python 3.14 — agent core
- Hardware: 8GB RAM / Intel UHD / Windows 11 / CPU-only

## Architecture
Router(1B) → Workhorse(3B) → Brain(8B, lazy).
Tools (files/system/code/web) + free-floating memory + security + default-deny gatekeeper.

## Security
VeraCrypt AES-256 + hardware fingerprint (UUID/mobo/CPU) + auto-lock + tamper response + dead-man's switch + device binding + decoy data.

## Gatekeeper (EXTRA-HARD)
Default-deny, allowlist-only, localhost-lock, request classifier, response sanitizer, content-vibe guard (no slop / no belief absorption), approval gate, full audit log.

## Status
BODY BUILT (v0.1, pure Python stdlib, ₹0, runs on 8GB).
- Implemented: memory store (+recombination), files/system/code-exec/web tools, device-lock security, default-deny gatekeeper, pluggable brain (rule fallback + Gemini free-tier adapter), terminal TUI.
- Smoke test: `python scripts\smoke_test.py` → ALL PASSED.
- Zero third-party deps (psutil/wmi avoided; stdlib only).
- Brain wiring: `config/settings.json` `brain.mode` = none|gemini|rule. Gemini needs `GOOGLE_API_KEY` in env or `config/secrets.json` (gitignored). No key = rule brain (offline).
- Device binding is opt-in (`security.fingerprint.enabled`) — off for first-run freedom.
- Ollama models (1B/3B/8B) NOT pulled — RAM/disk and the 8B-hardware-wall discussed; use Gemini free tier as the smart ₹0 brain, small local model on the Victus later.

## Next
- Test the TUI live: `python -m benny` in project root.
- (Optional) add GOOGLE_API_KEY → flip `brain.mode` to gemini for the smart engine.
- Commit once user green-lights git (repo not yet created/committed).

