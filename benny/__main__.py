"""Benny — terminal entrypoint. Talks to you, learns, never leaks."""
from __future__ import annotations

import sys
from pathlib import Path

# allow `python -m benny` from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from benny.core.engine import Agent  # noqa: E402


def _ask_human(prompt: str) -> bool:
    while True:
        ans = input(f"{prompt} [y/N] ").strip().lower()
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no", ""):
            return False
        print("answer y or n")


def main():
    agent = Agent(ask_callback=_ask_human)
    ok, msg = agent.authenticate()
    if not ok:
        print(f"SECURITY: {msg}")
        sys.exit(1)
    print(f"benny v{__import__('benny').__version__} ready. ({msg})")
    print("type 'help' to see commands, 'quit' to exit.")
    while True:
        try:
            user = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye.")
            break
        if not user:
            continue
        if user.lower() in ("quit", "exit", "q"):
            print("bye.")
            break
        print(f"benny> {agent.respond(user)}")


if __name__ == "__main__":
    main()
