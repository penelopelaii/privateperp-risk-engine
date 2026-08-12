"""Where each number came from.

The engine's parameters are overwhelmingly assumed rather than measured, and the
specification requires that this travels with the answer instead of living only
in documentation. Two of roughly thirty parameters are fitted, and both are
fitted to data this repository fabricated -- hence ``FITTED_SYNTHETIC`` being a
distinct value from ``MEASURED`` rather than a flavour of it.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from enum import Enum


class Provenance(str, Enum):
    """How a parameter's value was arrived at."""

    MEASURED = "measured"
    """Observed from the venue or the market."""

    FITTED_SYNTHETIC = "fitted_synthetic"
    """Fitted to data this repository invented. Internally consistent, not empirical."""

    ASSUMED = "assumed"
    """A declared judgement."""

    INFERRED_FROM_V0 = "inferred_from_v0"
    """Produced by the v0 compatibility adapter from a coarser input."""


NON_EMPIRICAL = frozenset(
    {Provenance.FITTED_SYNTHETIC, Provenance.ASSUMED, Provenance.INFERRED_FROM_V0}
)


def contains_assumed_inputs(provenance: Mapping[str, Provenance]) -> bool:
    """Return whether any parameter is something other than a measurement.

    Expected to be ``True`` for every evaluation this repository can currently
    produce. The flag exists so that it can become ``False`` one parameter at a
    time as real data arrives.
    """
    return any(value in NON_EMPIRICAL for value in provenance.values())


def merge(*sources: Mapping[str, Provenance]) -> dict[str, Provenance]:
    """Combine provenance maps, with later sources winning on conflict."""
    merged: dict[str, Provenance] = {}
    for source in sources:
        merged.update(source)
    return merged


def uniform(names: Iterable[str], value: Provenance) -> dict[str, Provenance]:
    """Tag every name with the same provenance."""
    return {name: value for name in names}
