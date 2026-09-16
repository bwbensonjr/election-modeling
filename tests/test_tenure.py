import pandas as pd

from legmodel import cli, compare, score, tenure, variants


def comparison_result(left, right):
    report = pd.DataFrame(
        [
            {
                "left_variant": left,
                "right_variant": right,
                "segment_type": "general_election",
                "segment_value": "all",
            }
        ]
    )
    report.attrs["sensitivity"] = pd.DataFrame(
        [{"left_variant": left, "right_variant": right}]
    )
    return report


def test_tenure_command_scores_frozen_operational_pairs_without_writing(monkeypatch):
    scored = []
    compared = []

    def fake_score(variant_names, definition_names, write, append):
        scored.append((variant_names, definition_names, write, append))

    def fake_compare(left, right, definition, write):
        compared.append((left, right, definition, write))
        return comparison_result(left, right)

    monkeypatch.setattr(score, "run", fake_score)
    monkeypatch.setattr(compare, "run", fake_compare)

    assert cli.main(["tenure", "--no-write"]) == 0
    assert scored == [
        (
            tenure.OPERATIONAL_VARIANTS,
            [variants.TENURE_REPLACEMENT_DEFINITION],
            False,
            False,
        )
    ]
    assert compared == [
        (
            "forecast_14d",
            "forecast_tenure_replacement_14d",
            "two_party_or_strongest",
            False,
        ),
        (
            "forecast_60d",
            "forecast_tenure_replacement_60d",
            "two_party_or_strongest",
            False,
        ),
    ]


def test_legacy_tenure_command_remains_addressable(monkeypatch):
    called = []
    monkeypatch.setattr(tenure, "run_legacy", lambda write: called.append(write))
    assert cli.main(["tenure", "--legacy", "--no-write"]) == 0
    assert called == [False]
