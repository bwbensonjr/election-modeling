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


# --- predictor-versus-predictor collinearity ---------------------------------


def pair(a, b, name="probe_pair") -> tuple:
    frame = pd.DataFrame({"a": a, "b": b})
    return variants.Variant(name=name, predictors=("a", "b")), frame


def test_an_exactly_collinear_pair_is_refused_naming_both():
    variant, frame = pair([0, 1, 0, 1, 1], [-1, 0, -1, 0, 0])
    with pytest.raises(variants.CollinearPredictorError) as excinfo:
        variants.check_collinear(variant, frame, fold="2014-11-04")
    message = str(excinfo.value)
    assert "'a'" in message and "'b'" in message
    assert "2014-11-04" in message


def test_an_affine_pair_of_continuous_predictors_is_refused():
    values = [1.0, 2.5, 3.7, 9.1, 4.4, 8.8]
    variant, frame = pair(values, [-2.0 * v + 7.0 for v in values])
    with pytest.raises(variants.CollinearPredictorError):
        variants.check_collinear(variant, frame)


def test_a_pair_separated_by_one_race_is_fit():
    """One race is enough to identify the two effects, however badly."""
    variant, frame = pair([0, 0, 1, 1, 1], [0, 0, 1, 1, 0])
    variants.check_collinear(variant, frame)


def test_a_constant_column_is_skipped_rather_than_refused():
    """An unobserved categorical level is disclosed, not refused (D3)."""
    variant, frame = pair([0, 0, 0, 0], [0, 1, 1, 0])
    variants.check_collinear(variant, frame)


def test_a_continuous_predictor_does_not_refuse_everything_beside_it():
    """Grouping on near-unique values would make every level a singleton."""
    variant, frame = pair(
        [float(i) for i in range(40)], [i % 2 for i in range(40)]
    )
    variants.check_collinear(variant, frame)


def test_the_check_runs_over_expanded_columns_not_declared_names():
    frame = pd.DataFrame(
        {
            "incumbent_status": ["Dem_Incumbent", "GOP_Incumbent"] * 4,
            "twin": [1, 0] * 4,
            "election_year": [2016] * 8,
            "pres_elec": [True] * 8,
            "is_special": [False] * 8,
        }
    )
    variant = variants.Variant(
        name="probe_expanded", predictors=("incumbent_status", "twin")
    )
    with pytest.raises(variants.CollinearPredictorError) as excinfo:
        variants.check_collinear(variant, variants.prepare(frame))
    assert "incumbent_dem" in str(excinfo.value)


def test_the_national_env_pair_is_the_shape_that_is_refused():
    """`national_env` is `pres_elec - 1` on any all-Democratic-president window."""
    frame = pd.DataFrame(
        {
            "election_id": [f"r{i}" for i in range(6)],
            "election_year": [2012, 2012, 2014, 2014, 2013, 2013],
            "pres_elec": [True, True, False, False, False, False],
            "is_special": [False, False, False, False, True, True],
            "incumbent_status": ["No_Incumbent"] * 6,
            "PVI_N": [1.0, -2.0, 3.0, -4.0, 5.0, -6.0],
            "response": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        }
    )
    variant = variants.get("baseline_national_env")
    with pytest.raises(variants.CollinearPredictorError) as excinfo:
        variants.check_grouping(variant, variants.prepare(frame), fold="2015-11-03")
    assert "national_env" in str(excinfo.value)
    assert "pres_elec" in str(excinfo.value)
