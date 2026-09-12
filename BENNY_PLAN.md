# BENNY — Offline Personal Agent (v1)

> Named after the digital model that helped architect it.
> A privacy-first, offline, self-owning assistant that grows by upgrading its "motherboard," never by rebuilding.

---

## 0. The Mission

Build a personal offline AI agent that:
- Runs **100% offline** by default (only whitelisted, user-approved internet queries).
- **Learns its user** deeply over time (memory + recombination engine).
- **Automates tasks** via tools (files, system, code, web).
- **Never leaks data** — hard security layer (encryption + fingerprint + auto-lock + gatekeeper).
- **Costs ₹0** to build and run on current hardware.
- Is built to **grow** — every layer is model-agnostic so a "motherboard" (model) upgrade instantly supercharges everything without a rebuild.

---

## 1. The Motherboard Theory (Core Principle)

```
weak motherboard → capped system, even with a beast processor
outdated base model → ties down everything built on top of it

THE RULE:
  1. NEVER weld learning into the model (no weir-aware fine-tuning).
  2. ALWAYS keep memory + tools + security model-agnostic.
  3. Upgrade the model ("motherboard") when hardware allows.
  4. Nothing on top ever rebuilds — it just leaps forward with a new engine.
```

The model is the load-bearing engine (motherboard), not scaffolding. The memory/tools/security are the data + software that survive every swap.

---

## 2. Hardware Baseline (v1 target)

```
RAM:            8GB (7,974 MB usable)
GPU:            Intel UHD (1GB VRAM) — CPU-only inference
OS:             Windows 11
Disk:           Internal SSD (encrypted vault partition)
```

---

## 3. The Stack

| # | Piece | What | Notes |
|---|-------|------|-------|
| 1 | **GitHub Copilot API** | model runtime | `api.githubcopilot.com`, OpenAI-compatible, authed via `gh` token |
| 2 | **Models** | 2-tier ladder | see below |
| 3 | **Python 3.14** | agent core | present, verified `3.14.3` |

### 3.1 The Model Ladder (speed-first, context-aware)

> Updated 2026-09-10: Ollama + the 1B/3B/8B ladder was retired. The user is
> always online, so a local model on 8GB is a pure RAM tax with weaker
> reasoning. The Copilot API serves models that are smarter AND leave RAM free.

| Role | Model | Size | Where it runs | Use |
|------|-------|------|---------------|-----|
| Router | rule-based | ~0 | local, instant | classify routine vs heavy (length + reasoning keywords) |
| Workhorse | gpt-4o-mini | cloud | Copilot API | 80% of tasks, decisive + low-verbosity |
| Brain | gpt-4.1 | cloud | Copilot API | complex/deep reasoning on longer or hard questions |

```
RESIDENT:  nothing — no local model, all 8GB RAM stays yours
LAZY:      heavy model (gpt-4.1) only on requests that need it
```

### 3.2 Future Motherboard Upgrades

```
P1 NOW:          gpt-4o-mini workhorse + gpt-4.1 brain (cloud, ₹0, 8GB free)
P2 2027 (Victus RTX 3050 6GB / 16GB): evaluate local Qwen3 14B on GPU —
                only if it beats cloud on quality-per-RAM for the use cases
P3 future:       30B MoE / Gemma 4 26B locally, cloud stays the fallback

memory/security/tools carry over 1:1 on every upgrade.
```

---

## 4. Architecture

```
                ┌─────────────────────────────┐
 user input ──▶ │  AGENT CORE (python, light)  │
                │  ├─ ROUTER      (rule-based)  → classify light vs heavy
                │  ├─ WORKHORSE   (gpt-4o-mini) → most tasks
                │  ├─ BRAIN       (gpt-4.1)     → complex
                │  ├─ TOOLS       (files/sys/code/web)
                │  ├─ MEMORY      (free-floating JSON)
                │  ├─ GATEKEEPER  (network, default-deny)
                │  └─ SECURITY    (fingerprint/autolock/tamper)
                └────────────┬────────────────────┘
                             │
                    ┌────────▼────────┐
                    │  TOOL EXECUTION │ → files, system, code, web
                    └────────────────┘
```

**Speed model:** token output + reasoning passes, not just hardware. Goal:
- trivial → few tokens, no thinking (fast)
- moderate → 1-2 tools, concise (fast)
- complex → thinking on, worth the wait (understandably slow)

---

## 5. Tools (all 4, model-agnostic)

1. **Files/Disk** — find, organize, clean, report sizes.
2. **System** — processes, disk health, monitoring.
3. **Code Exec** — sandboxed script run + debug (safe execution).
4. **Web** — whitelisted queries only, via the gatekeeper.

---

## 6. Memory System (Free-Floating — NEVER in the model)

```
What:   JSON files storing conversation history, learned patterns, preferences.
Growth: recombination engine + retroactive reinterpretation:
        - each new insight reinterprets old data (exponential, not linear)
        - "HI!! vs hi............" → emotional-context layer
        - repeated tasks cached → muscle-memory speed

Rule:   Memory lives OUTSIDE the model (model-agnostic, swappable).
        It is the bricks, the model is the workers/crane.
```

---

## 7. Security Layer

### 7.1 Encryption — VeraCrypt (proven, free, ₹0)
- AES-256, audited 5x (OCAP, iSec, NCC Group, Fraunhofer/BSI, Quarkslab), 14 years, zero crypto breaks.
- Weak points are ALWAYS human (password choice, behavior) — our custom layer covers those.

### 7.2 Custom Security Layer (Python)
```
FINGERPRINT / DEVICE BINDING:
  ├─ system UUID (E73745B4-16AD-EA11-8104-BCE92FBF9F6F on this HP)
  ├─ motherboard serial (PJUVLF21WDVT9L)
  └─ CPU processor ID (BFEBFBFF000706E5)
  → vault auto-unlocks ONLY on this laptop; same model = different IDs = locked.

ACTIVITY-BASED LOCKING:
  ├─ screen lock → lock vault
  ├─ idle timeout → lock vault
  └─ lid close / sleep / drive removed → lock vault
  → you cannot forget to lock it.

TAMPER RESPONSE:
  ├─ failed attempts logged
  ├─ auto-lock after N failures
  ├─ decoy data on forced entry (plausible deniability)
  └─ auto-wipe on extreme tamper

DEAD-MAN'S SWITCH:
  └─ vault wipes if it doesn't check in within a set window.

COLD-BOOT / EVIL-MAID mitigation:
  └─ full shutdown before leaving laptop (not sleep), secure boot.
```

---

## 8. GATEKEEPER — Network Control (EXTRA-HARD, default-deny)

### 8.1 The stance
```
DEFAULT: BLOCK EVERYTHING.
The AI is NEVER trusted with the network.
Every byte in/out requires user awareness + approval.
```

### 8.2 Hardware/logical isolation
```
- brain talks to its model endpoint over an https call (endpoint fixed in code)
- agent runs in sandboxed process
- only network path = the brain endpoint + the tiny controlled proxy (web tool)
- OS firewall backs it up
```

### 8.3 Allowlist (content filter)
```
Every outbound request matches a predefined pattern:
  - domain allowlist (exact + regex)
  - https-only (no http)
  - no IP-address URLs
  - no redirects to unapproved domains
  - content-type must match expected

Allowed examples (you curate):
  search, weather, docs, news (curated domains), download (exact URL, always-ask)
```

### 8.4 Request + response filter (anti-slop / anti-injection / anti-absorption)
```
BEFORE fetch:
  - topic classification
  - domain reputation score (your maintain list)
  - content-type whitelist

AFTER fetch (response filter):
  - raw HTML sanitized (no scripts/trackers)
  - only clean text extracted (LLM never sees whole page)
  - length caps (no infinite feeds into context)
  - fetch DATA vs OPINION separated; framing stripped/flagged
```

### 8.5 Content-vibe guard (your explicit asks)
```
No brain-rot media slop:
  - you define "do not ingest" categories
  - political propaganda, engagement-bait, unverified claims, manipulative framing

No belief-absorption:
  - model is a frozen reasoning engine (can't absorb worldview)
  - only curated memory "learns," and it's yours to purge
  - jarvis reports data; you decide meaning
```

### 8.6 Human-in-the-loop + audit
```
- EVERY outbound attempt logged (timestamp, domain, query)
- approval gate: auto-allow (trusted) / ask-me (new) / deny (default)
- you can add/remove domains + purge memory any time
- nothing happens silently on the network
```

---

## 9. Status of the Design (from the architecture session)

```
✅ architecture (brain/memory/tools/gatekeeper)
✅ security (fingerprint/autolock/tamper/encryption)
✅ encryption choice (VeraCrypt AES-256, proven)
✅ hardware (internal drive, ₹0)
✅ model ladder (Copilot: gpt-4o-mini + gpt-4.1, motherboard theory)
✅ toolset (all 4: files/system/code/web)
✅ gatekeeper (extra-hard, default-deny, sanitized, audited)
✅ growth plan (model-agnostic upgrades, memory carries 1:1)
✅ brain live (Copilot API, 2026-09-10; Ollama retired, user is always online)

⏳ BUILD COMPLETE (v0.1) + BRAIN LIVE (v0.2) — remaining work is tuning and new features.
```

---

## 10. Growth / Roadmap

```
PHASE 1 (NOW, 8GB CPU):
  - build full system on 3B/8B
  - all layers model-agnostic
  - start accumulating real memory about the user

PHASE 1.5 (2026-09-12): WEBFACE SHIPPED
  - serene-tech browser face (aurora + breathing orb), localhost-only, stdlib
  - run: scripts\run-webface.cmd  |  python -m webface
  - v2: in-UI gatekeeper approval modal, markdown renderer, history

PHASE 2 (2027, Victus RTX 3050 / 16GB):
  - motherboard swap → Qwen3 14B on GPU
  - nothing rebuilds, everything leaps forward

PHASE 3 (future):
  - 30B MoE / Gemma 4 26B
  - memory carried 1:1 from day one
```

---

## 11. Deliverable (v1 definition of done)

```
A working, private, offline agent on this laptop:
 - talks via terminal
 - executes files/system/code/web tools (agent-agnostic)
 - learns + remembers via free-floating memory
 - protected by VeraCrypt + fingerprint + autolock + tamper + dead-man
 - network locked behind default-deny gatekeeper
 - total cost ₹0, ~8.5GB download
```

---

## 12. Notes / Honest Truths

- The cloud brain (gpt-4o-mini / gpt-4.1) is the current **motherboard**; local 8B+ models become interesting again only on GPU hardware that beats cloud on quality-per-RAM (the 2027 Victus).
- The model cannot "become sentient" or absorb belief systems by itself — it's a frozen engine; the only thing that learns is curated external memory.
- Using the Copilot API is perfect for a personal, private agent. Don't wrap it into a public product or reseller API later — that violates the access terms.
- The cloud brain keeps all 8GB RAM free (no local inference resident), and the rule-based router keeps 80% of interactions snappy and cheap.
