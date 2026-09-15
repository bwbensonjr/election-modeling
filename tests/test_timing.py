"""The `ballot_timing` categorical: its levels, and their fold-independence.

Two things are worth a test here. A special election must never be described
as a midterm electorate -- that miscoding is the defect the categorical exists
to remove, and it is silent if it comes back. And the level set must not be
inferred from the races a fold happens to hold, because a fold that inferred
three levels would build a design matrix that rejects the holdout race
carrying the fourth.
"""

from __future__ import annotations

import pandas as pd
import pytest

from legmodel import variants

LEVELS = variants.CATEGORICAL_LEVELS["ballot_timing"]


def races() -> pd.DataFrame:
    """One race of each timing kind, plus a special in a presidential year."""
    rows = [
        # (election_date, election_year, is_special, pres_elec, expected)
        ("2016-11-08", 2016, False, True, "presidential"),
        ("2014-11-04", 2014, False, False, "midterm_dem_pres"),
        ("2018-11-06", 2018, False, False, "midterm_gop_pres"),
        ("2015-03-31", 2015, True, False, "special"),
        # A special held in a presidential year but on its own date. It carries
        # pres_elec = False like every other special, so a rule reading the
        # calendar would call it a midterm.
        ("2016-03-01", 2016, True, False, "special"),
        # And one in a Republican president's year, for the same reason.
        ("2017-10-17", 2017, True, False, "special"),
    ]
    return pd.DataFrame(
        [
            {
                "election_id": f"r{i}",
                "election_date": date,
                "election_year": year,
                "is_special": special,
                "pres_elec": presidential,
                "expected": expected,
                "incumbent_status": "No_Incumbent",
                "PVI_N": 1.0 * i,
                "response": 1.0 * i,
            }
            for i, (date, year, special, presidential, expected) in enumerate(rows)
        ]
    )


def test_each_race_takes_the_level_its_ballot_and_president_imply():
    frame = races()
    assert list(variants.ballot_timing_levels(frame)) == list(frame["expected"])


def test_a_special_in_a_presidential_year_is_not_given_a_midterm_level():
    frame = races()
    specials = frame[frame["is_special"]]
    levels = variants.ballot_timing_levels(specials)
    assert set(levels) == {"special"}
    assert not levels.isin(["midterm_dem_pres", "midterm_gop_pres"]).any()


def test_prepare_carries_the_level_and_its_indicators():
    prepared = variants.prepare(races())
    assert list(prepared["ballot_timing"]) == list(races()["expected"])
    for level, indicator in variants.CATEGORICAL_INDICATORS["ballot_timing"][
        "levels"
    ].items():
        assert list(prepared[indicator]) == [
            int(value == level) for value in races()["expected"]
        ]


def test_presidential_is_the_reference_and_has_no_indicator():
    spec = variants.CATEGORICAL_INDICATORS["ballot_timing"]
    assert spec["reference"] == "presidential"
    assert LEVELS[0] == "presidential"
    assert "presidential" not in spec["levels"]
    assert len(variants.expand("ballot_timing")) == len(LEVELS) - 1


def test_the_level_set_does_not_depend_on_the_fold():
    """A frame holding one level still produces every indicator column."""
    frame = races()
    only_presidential = frame[frame["expected"] == "presidential"]
    prepared = variants.prepare(only_presidential)
    for indicator in variants.expand("ballot_timing"):
        assert indicator in prepared.columns
        assert prepared[indicator].sum() == 0


def test_the_derivation_produces_only_declared_levels():
    """`prepare` refuses a level it was not told about, so the two must agree."""
    assert set(variants.ballot_timing_levels(races())) <= set(LEVELS)
    with pytest.raises(ValueError) as excinfo:
        variants.prepare(races().assign(election_year=1998))
    assert "1998" in str(excinfo.value)


def test_the_predictor_is_knowable_before_the_election():
    variants.check_knowable("ballot_timing")
    declared = variants.DERIVED["ballot_timing"]["from"]
    assert not set(declared) & variants.OUTCOME_COLUMNS


def test_a_variant_declaring_the_categorical_validates():
    frame = races()
    variant = variants.Variant(
        name="probe_timing",
        predictors=("PVI_N", "incumbent_status", "ballot_timing"),
    )
    variant.validate(frame.columns, frame)
    assert "timing_special" in variant.formula
    assert "ballot_timing" in variant.declared
