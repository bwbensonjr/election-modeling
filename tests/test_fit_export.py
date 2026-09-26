from types import SimpleNamespace

import numpy as np
import pandas as pd
import xarray as xr

from legmodel import fit, variants


class PredictModel:
    response_component = SimpleNamespace(term=SimpleNamespace(name="response"))

    def __init__(self, predictions):
        self.predictions = predictions

    def predict(self, idata, **kwargs):
        return SimpleNamespace(
            posterior_predictive=xr.Dataset(
                {
                    "response": (
                        ("chain", "draw", "observation"),
                        self.predictions,
                    )
                }
            )
        )


def test_parameter_draws_align_with_predictive_chain_draw_order():
    coefficient = np.array([[1.0, 2.0], [3.0, 4.0]])
    predictions = (coefficient * 10).reshape(2, 2, 1)
    idata = SimpleNamespace(
        posterior=xr.Dataset({"incumbent_dem": (("chain", "draw"), coefficient)})
    )
    fitted = fit.Fit(
        variants.get("baseline_no_timing"),
        PredictModel(predictions),
        idata,
        SimpleNamespace(seed=42),
    )
    races = pd.DataFrame(
        [
            {
                "PVI_N": 0.0,
                "incumbent_status": "No_Incumbent",
                "pres_elec": False,
            }
        ]
    )

    parameter = fitted.parameter_draws(["incumbent_dem"])["incumbent_dem"]
    predictive = fitted.predict_draws(races)[:, 0]

    np.testing.assert_array_equal(parameter, [1.0, 2.0, 3.0, 4.0])
    np.testing.assert_array_equal(predictive, parameter * 10)
