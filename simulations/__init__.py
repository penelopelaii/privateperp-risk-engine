"""Research simulations.

Each module stresses one assumption behind the engine's recommendations and
prints a small summary table. They are scripts, not library code, and are run
from the repository root::

    python -m simulations.jump_risk

Scenario parameters live in ``simulations/scenarios/*.json`` so a run is
reproducible from a file rather than from edited constants.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCENARIO_DIR = Path(__file__).parent / "scenarios"


def load_scenario(name: str) -> dict[str, Any]:
    """Load a scenario definition by file stem from ``simulations/scenarios``."""
    path = SCENARIO_DIR / f"{name}.json"
    if not path.exists():
        available = sorted(p.stem for p in SCENARIO_DIR.glob("*.json"))
        raise FileNotFoundError(f"Unknown scenario {name!r}. Available: {available}")
    return json.loads(path.read_text())


__all__ = ["SCENARIO_DIR", "load_scenario"]
