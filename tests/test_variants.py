"""Grouping granularity and composite routing.

Both are refusals: things the harness must decline to fit rather than fit
wrongly. A refusal that silently stops firing is invisible in the published
outputs, which is what makes them worth a test.
"""

from __future__ import annotations

import pandas as pd
import pytest

from legmodel import variants


def races() -> pd.DataFrame:
    """Two election dates inside one calendar year, plus a prior year."""
    rows = [
        ("2016-03-01", 2016, True),
        ("2016-03-01", 2016, True),
        ("2016-11-08", 2016, False),
        ("2016-11-08", 2016, False),
        ("2014-11-04", 2014, False),
    ]
    return pd.DataFrame(
        [
            {
                "election_id": f"r{i}",
                "election_date": date,
                "election_year": year,
                "is_special": special,
                "PVI_N": 1.0 * i,
                "response": 1.0 * i,
            }
            for i, (date, year, special) in enumerate(rows)
        ]
    )


def grouped(group: str) -> variants.Variant:
    return variants.Variant(
        name=f"probe_{group}",
        predictors=("PVI_N",),
        group_effects=(group,),
        priors={variants.group_term(group): variants.group_intercept_prior()},
    )


# --- grouping granularity ----------------------------------------------------


def test_a_year_grouping_is_refused_under_date_folds():
    frame = races()
    with pytest.raises(variants.CoarseGroupingError) as excinfo:
        grouped("election_year").validate(frame.columns, frame)
    message = str(excinfo.value)
    assert "election_year" in message
    assert "election_date" in message


def test_a_date_grouping_validates():
    frame = races()
    grouped("election_date").validate(frame.columns, frame)


def test_the_grain_check_is_skipped_without_the_frame():
    """`fit.py` validates per fold with columns only and must not trip here."""
    grouped("election_year").validate(races().columns)


def test_a_year_grouping_passes_when_no_year_spans_two_dates():
    """The check is about the data, not the column's name."""
    frame = races()
    frame = frame[frame["election_date"] != "2016-03-01"]
    grouped("election_year").validate(frame.columns, frame)


def test_registered_year_variants_group_on_the_election_date():
    for name in ("baseline_year", "baseline_year_pres"):
        assert variants.get(name).group_effects == ("election_date",)


# --- derived flags -----------------------------------------------------------


def test_not_special_is_available_to_requires():
    frame = races()
    variant = variants.Variant(
        name="gen_only", predictors=("PVI_N",), requires=("not_special",)
    )
    variant.validate(frame.columns)
    kept = variants.restrict(variant, frame)
    assert len(kept) == 3
    assert not kept["is_special"].astype(bool).any()


def test_an_unknown_requirement_is_still_refused():
    variant = variants.Variant(
        name="bad", predictors=("PVI_N",), requires=("no_such_column",)
    )
    with pytest.raises(variants.UnknownPredictorError):
        variant.validate(races().columns)


# --- composite routing -------------------------------------------------------


def composite(components=None, route_on="is_special") -> variants.CompositeVariant:
    general = variants.Variant(
        name="c_general", predictors=("PVI_N",), requires=("not_special",)
    )
    special = variants.Variant(name="c_special", predictors=("PVI_N", "is_special"))
    return variants.CompositeVariant(
        name="c",
        components={False: general, True: special}
        if components is None
        else components,
        route_on=route_on,
    )


def test_every_race_routes_to_exactly_one_component():
    frame = variants.with_flags(races())
    routed = composite().route(frame)
    assert {k: len(v) for k, v in routed.items()} == {False: 3, True: 2}
    assert sum(len(v) for v in routed.values()) == len(frame)
    ids = pd.concat(list(routed.values()))["election_id"]
    assert ids.is_unique


def test_a_race_matching_no_component_is_named_not_dropped():
    frame = variants.with_flags(races())
    one_sided = variants.CompositeVariant(
        name="one_sided",
        components={False: variants.Variant(name="g", predictors=("PVI_N",))},
        route_on="is_special",
    )
    with pytest.raises(variants.CompositeRoutingError) as excinfo:
        one_sided.route(frame)
    assert "no component" in str(excinfo.value)


def test_routing_on_an_absent_column_is_refused():
    with pytest.raises(variants.CompositeRoutingError):
        composite(route_on="nope").route(variants.with_flags(races()))


def test_validate_refuses_an_absent_routing_column():
    frame = races()
    with pytest.raises(variants.UnknownPredictorError) as excinfo:
        composite(route_on="nope").validate(frame.columns, frame)
    assert "nope" in str(excinfo.value)


def test_validate_refuses_a_single_component_composite():
    frame = races()
    one = variants.CompositeVariant(
        name="one",
        components={False: variants.Variant(name="g", predictors=("PVI_N",))},
        route_on="is_special",
    )
    with pytest.raises(variants.UnknownPredictorError):
        one.validate(frame.columns, frame)


def test_a_composite_requires_only_what_both_components_do():
    """A restriction one component carries must not exclude the other's races."""
    assert composite().requires == ()


def test_the_registered_split_arm_is_shaped_as_declared():
    split = variants.get("special_split")
    assert split.is_composite
    assert split.route_on == "is_special"
    assert split.components[False].requires == ("not_special",)
    assert split.components[True].requires == ()
    assert "is_special" in split.components[True].predictors
    assert "is_special" not in split.components[False].predictors


def test_the_pooled_arms_differ_by_exactly_one_term():
    plain = variants.get("special_pooled_plain")
    term = variants.get("special_pooled_term")
    assert set(plain.predictors) < set(term.predictors)
    assert set(term.predictors) - set(plain.predictors) == {"is_special"}


def test_the_plain_arm_matches_the_baseline():
    assert variants.get("special_pooled_plain").predictors == (
        variants.get("baseline").predictors
    )
