"""Provenance tagging."""

from __future__ import annotations

from risk_engine.v1.provenance import Provenance, contains_assumed_inputs, merge, uniform


def test_measured_only_is_not_flagged():
    assert not contains_assumed_inputs({"sigma": Provenance.MEASURED})


def test_fitted_synthetic_counts_as_non_empirical():
    """Fitted to invented data is not a weaker form of measured; it is a different thing."""
    assert contains_assumed_inputs({"alpha": Provenance.FITTED_SYNTHETIC})


def test_any_assumption_flags_the_whole_evaluation():
    assert contains_assumed_inputs(
        {"sigma": Provenance.MEASURED, "phi_1": Provenance.ASSUMED}
    )


def test_inferred_from_v0_is_flagged():
    assert contains_assumed_inputs({"sigma": Provenance.INFERRED_FROM_V0})


def test_merge_prefers_later_sources():
    merged = merge(
        {"sigma": Provenance.ASSUMED}, {"sigma": Provenance.MEASURED, "x": Provenance.ASSUMED}
    )
    assert merged == {"sigma": Provenance.MEASURED, "x": Provenance.ASSUMED}


def test_uniform_tags_every_name():
    assert uniform(["a", "b"], Provenance.ASSUMED) == {
        "a": Provenance.ASSUMED,
        "b": Provenance.ASSUMED,
    }


def test_empty_provenance_is_not_flagged():
    assert not contains_assumed_inputs({})
