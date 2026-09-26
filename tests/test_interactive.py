import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from legmodel import definitions, forecast, forecast_run, interactive


def targets():
    rows = []
    for district, display, pvi in (
        ("Tenth Bristol", "10th Bristol", 2.0),
        ("Eighteenth Essex", "18th Essex", 10.0),
    ):
        row = {
            "election_date": "2026-11-03",
            "office": "State Representative",
            "district": district,
            "district_display": display,
            "dem_candidate_id": f"d-{display}",
            "dem_candidate_name": f"Dem {display}",
            "dem_candidate_municipality": "Example",
            "dem_candidate_incumbent": False,
            "comparison_candidate_id": f"r-{display}",
            "comparison_candidate_name": f"Rep {display}",
            "comparison_candidate_party": "Republican",
            "comparison_candidate_municipality": "Example",
            "comparison_candidate_incumbent": False,
            "incumbent_status": "No_Incumbent",
            "PVI_N": pvi,
            "pvi_year": 2024,
            "redistricting_cycle": 2021,
            "pvi_coverage": 1.0,
            "pvi_provenance": "exact",
            "ballot_timing": "midterm_gop_pres",
            "money_complete_60d": district == "Tenth Bristol",
            "money_complete_14d": False,
            "candidate_source": "primary",
            "candidate_source_digest": "abc",
            "candidate_data_as_of": "2026-09-14",
            "pvi_source": "precinct",
            "pvi_source_digest": "def",
            "comparison_rule": "pre-election",
            "comparison_review_status": "not required",
            "dem_nominee_basis": "primary",
            "dem_nominee_review_status": "not required",
            "comparison_nominee_basis": "primary",
            "comparison_nominee_review_status": "not required",
        }
        row["target_id"] = forecast.target_id(
            row["election_date"], row["office"], row["district"]
        )
        rows.append(row)
    return pd.DataFrame(rows)


def finance_snapshot():
    rows = []
    for target_index, target_row in targets().iterrows():
        for role in ("dem", "opp"):
            available = target_index == 0
            rows.append(
                {
                    "target_id": target_row["target_id"],
                    "role": role,
                    "horizon": "60d",
                    "cutoff": "2026-09-04",
                    "available": available,
                    "receipts": 100.0 if available else pd.NA,
                    "expenditures": 50.0 if available else pd.NA,
                }
            )
    return pd.DataFrame(rows)


class FakeFit:
    def __init__(self, component, seed):
        self.component = component
        self.seed = seed
        self.diagnostics = SimpleNamespace(
            as_row=lambda: {"seed": seed, "diagnostics_passed": True}
        )

    def predict_draws(self, target):
        point = target["PVI_N"].to_numpy(dtype=float)
        return np.vstack([point - 1, point, point + 1])

    def parameter_draws(self, terms):
        values = {
            "incumbent_dem": np.array([2.0, 2.0, 2.0]),
            "incumbent_gop": np.array([-2.0, -2.0, -2.0]),
            "money_logratio_wide": np.array([0.5, 0.5, 0.5]),
        }
        return {term: values[term] for term in terms}


def fake_fit(component, training, fold, definition, seed):
    return FakeFit(component, seed)


def bundle_inputs():
    target = targets()
    finance = finance_snapshot()
    official, _, support, metadata = forecast_run.generate(
        target,
        finance,
        "60d",
        "forecast_60d",
        definitions.adopted().name,
        fit_provider=fake_fit,
    )
    snapshot = {
        **metadata,
        "code_commit": "abc123",
        "target_digest": "sha256:target",
        "finance_digest": "sha256:finance",
        "training_digest": "sha256:training",
    }
    return target, finance, official, snapshot, support


def build_fixture():
    return interactive.build_contents(
        "60d", *bundle_inputs(), fit_provider=fake_fit
    )


def test_bundle_covers_money_and_fallback_components():
    contents = build_fixture()
    manifest = interactive.validate_contents(contents)

    assert len(manifest["races"]) == 2
    assert set(manifest["components"]) == {
        "baseline_money_logratio_no_timing_wide",
        "baseline_no_timing",
    }
    money = manifest["components"]["baseline_money_logratio_no_timing_wide"]
    fallback = manifest["components"]["baseline_no_timing"]
    assert "money_logratio_wide" in money["scenario_terms"]
    assert all(not term.startswith("money_") for term in fallback["scenario_terms"])


def test_bundle_rejects_locked_summary_mismatch():
    target, finance, official, snapshot, support = bundle_inputs()
    official.loc[0, "point_margin"] += 1

    with pytest.raises(interactive.InteractiveBundleError, match="point_margin"):
        interactive.build_contents(
            "60d",
            target,
            finance,
            official,
            snapshot,
            support,
            fit_provider=fake_fit,
        )


def test_bundle_validation_rejects_digest_and_draw_count():
    contents = build_fixture()
    manifest = json.loads(contents["manifest.json"])
    race_path = manifest["races"][0]["asset"]

    changed = dict(contents)
    changed[race_path] += b" "
    with pytest.raises(interactive.InteractiveBundleError, match="digest"):
        interactive.validate_contents(changed)

    race = json.loads(contents[race_path])
    race["draws"].pop()
    changed = dict(contents)
    changed[race_path] = interactive.json_bytes(race)
    manifest["assets"][race_path] = forecast_run.bytes_digest(changed[race_path])
    changed["manifest.json"] = interactive.json_bytes(manifest)
    with pytest.raises(interactive.InteractiveBundleError, match="draw count"):
        interactive.validate_contents(changed)


def test_bundle_publish_is_create_once(tmp_path):
    contents = build_fixture()
    directory = tmp_path / "interactive"
    assert interactive.publish_contents(contents, directory) == "created"
    assert interactive.publish_contents(contents, directory) == "verified"

    changed = dict(contents)
    manifest = json.loads(changed["manifest.json"])
    manifest["definition"] = "different"
    changed["manifest.json"] = interactive.json_bytes(manifest)
    with pytest.raises(interactive.InteractiveBundleError, match="overwrite"):
        interactive.publish_contents(changed, directory)


def test_forecast_web_cli_routes_horizon_and_dirty_run_is_refused(monkeypatch):
    from legmodel import cli

    called = []
    with monkeypatch.context() as cli_patch:
        cli_patch.setattr(interactive, "run", lambda horizon: called.append(horizon))
        assert cli.main(["forecast-web", "--horizon", "60d"]) == 0
    assert called == ["60d"]

    monkeypatch.setattr(forecast_run, "clean_worktree", lambda: False)
    with pytest.raises(interactive.InteractiveBundleError, match="clean worktree"):
        interactive.run("60d")


def test_shared_golden_scenarios_match_python_reference():
    path = Path(__file__).parent / "fixtures" / "interactive_scenarios.json"
    fixture = json.loads(path.read_text())
    terms = {name: np.asarray(values) for name, values in fixture["terms"].items()}
    for case in fixture["cases"]:
        actual = interactive.scenario_draws(
            np.asarray(fixture["published_draws"]),
            case["published_incumbency"],
            case["scenario_incumbency"],
            terms,
            case["published_money_logratio"],
            case["scenario_money_logratio"],
            case["money_predictor"],
        )
        np.testing.assert_allclose(actual, case["expected_draws"], rtol=0, atol=1e-12)
        for name, expected in case["expected_summary"].items():
            assert interactive.summarize(actual)[name] == pytest.approx(expected)
