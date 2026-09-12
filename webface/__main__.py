"""python -m webface — launch the browser face."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from webface.server import main  # noqa: E402

if __name__ == "__main__":
    main()