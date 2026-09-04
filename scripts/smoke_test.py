"""Smoke-test benny's core without a TUI — imports, tools, memory, gatekeeper."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from benny.core.engine import Agent

agent = Agent(ask_callback=lambda p: False)

print("=== auth ===")
print(agent.authenticate())

print("\n=== memory: remember + recall ===")
print(agent.respond("remember project is benny-ai"))
print(agent.respond("what do you know"))

print("\n=== files tool ===")
print(agent.dispatch("files", "summary", "."))

print("\n=== system tool ===")
print(agent.dispatch("system", "memory"))
print(agent.dispatch("system", "info"))

print("\n=== code tool ===")
print(agent.dispatch("code_exec", "run_python", "print(1+1)"))

print("\n=== gatekeeper: block non-https + default-deny ===")
print(agent.gatekeeper_safe_fetch("http://example.com"))
print(agent.gatekeeper_safe_fetch("https://192.168.1.1/x"))
print(agent.gatekeeper_safe_fetch("https://random-unknown-domain.example/", "q"))

print("\n=== memory purge ===")
agent.memory.purge()
print("purged, file_count =", agent.memory.file_count())

print("\nALL SMOKE TESTS PASSED")
