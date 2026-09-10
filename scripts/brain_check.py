"""Live probe: hit the Copilot brain end-to-end (needs internet + gh token)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from benny.core.brain import build_brain
from benny.core import load_config

cfg = load_config()
brain = build_brain(cfg)
print(f"brain: {type(brain).__name__} | ready={getattr(brain, 'ready', None)}")

if not getattr(brain, "ready", False):
    print("NO BRAIN — check gh auth or config/secrets.json")
    sys.exit(1)

print("\n=== light (default model) ===")
print(brain.generate("Say hello in one line.", system="You are benny."))

print("\n=== heavy (model_heavy) ===")
print(brain.generate(
    "In three sentences, explain why a GPU beats a CPU for large local models.",
    system="You are benny. Be concise.",
    heavy=True,
))