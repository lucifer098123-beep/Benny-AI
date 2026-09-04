# Benny-AI

A private, offline personal agent — the **body** is done, the **brain** is queued.

## State (read this first if you come back later)

- **Body: DONE** (v0.1, commit `0a10465`) — memory (recombination engine) + 4 tools (files/system/code-exec/web) + security (device-lock) + default-deny gatekeeper + pluggable brain + terminal TUI.
- **Brain: QUEUED** — the only missing piece. Plug it in without rebuilding anything:
  - any time → Gemini free-tier (mode `gemini`, needs `GOOGLE_API_KEY`)
  - Jan 2027 → local 4-8B model on the Victus (RTX 3050 / 16GB)
- ₹0, runs on 8GB, pure Python stdlib, zero third-party deps.
- Run it: `python -m benny`
- Test it: `python scripts\smoke_test.py`
