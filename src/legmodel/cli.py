"""Command line entry point for fitting and scoring.

    uv run legmodel score
    uv run legmodel score --variants baseline
    uv run legmodel compare special_pooled_plain special_pooled_term special_split
    uv run legmodel importance
    uv run legmodel parity
"""

from __future__ import annotations

import argparse
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="legmodel", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    score_cmd = sub.add_parser("score", help="run the rolling-origin scoring")
    score_cmd.add_argument(
        "--variants",
        nargs="+",
        default=None,
        help="variants to score (default: every registered variant)",
    )
    score_cmd.add_argument(
        "--definitions",
        nargs="+",
        default=None,
        help="definitions to score under (default: the adopted definition)",
    )
    score_cmd.add_argument(
        "--append",
        action="store_true",
        help="add these cells to the committed outputs instead of replacing them",
    )
    score_cmd.add_argument(
        "--no-write",
        action="store_true",
        help="print results without writing the committed outputs",
    )
    score_cmd.add_argument(
        "--schedule-change",
        action="store_true",
        help=(
            "declare that the fold schedule changed, so every figure is "
            "superseded rather than compared against the committed ones"
        ),
    )

    compare_cmd = sub.add_parser("compare", help="paired comparison of two variants")
    compare_cmd.add_argument(
        "variants",
        nargs="+",
        metavar="VARIANT",
        help="reference variant first, then each variant to compare to it",
    )
    compare_cmd.add_argument(
        "--definition",
        nargs="+",
        default=[None],
        help="definitions to run the comparison under (default: adopted)",
    )
    compare_cmd.add_argument(
        "--append",
        action="store_true",
        help="add these comparisons to the committed output instead of replacing it",
    )

    cd_cmd = sub.add_parser(
        "compare-definitions",
        help="compare two definitions on the intersection of their holdouts",
    )
    cd_cmd.add_argument(
        "definitions",
        nargs="+",
        metavar="DEFINITION",
        help="reference definition first, then each definition to compare to it",
    )
    cd_cmd.add_argument("--variant", default="baseline")
    cd_cmd.add_argument(
        "--append",
        action="store_true",
        help="add these comparisons to the committed output instead of replacing it",
    )

    sweep_cmd = sub.add_parser("sweep", help="sweep the write-in threshold")
    sweep_cmd.add_argument("--variant", default="baseline")
    sweep_cmd.add_argument(
        "--counts-only",
        action="store_true",
        help="report admitted races without scoring each threshold",
    )

    imp_cmd = sub.add_parser(
        "importance", help="marginal effect, contribution spread and drop-one cost"
    )
    imp_cmd.add_argument("--variant", default="baseline_money_logratio")
    imp_cmd.add_argument("--definition", default=None)
    imp_cmd.add_argument(
        "--no-write",
        action="store_true",
        help="print results without writing the committed report",
    )
    imp_cmd.add_argument(
        "--append",
        action="store_true",
        help="add this variant's rows to the committed report instead of replacing it",
    )

    folds_cmd = sub.add_parser("folds", help="print the rolling-origin fold schedule")
    folds_cmd.add_argument("--definition", default=None)

    sub.add_parser("parity", help="check baseline coefficients against mapoli")
    sub.add_parser("variants", help="list registered variants")
    sub.add_parser("definitions", help="list registered data definitions")
    tenure_cmd = sub.add_parser(
        "tenure", help="run the pre-declared incumbency-tenure experiment"
    )
    tenure_cmd.add_argument(
        "--no-write",
        action="store_true",
        help="run without changing committed model outputs",
    )

    finance_cmd = sub.add_parser(
        "target-finance", help="collect or verify future-target OCPF finance"
    )
    finance_cmd.add_argument("--horizon", choices=["60d", "14d"], required=True)
    finance_cmd.add_argument(
        "--dry-run",
        action="store_true",
        help="resolve candidates and report the exact cutoff without collecting",
    )
    finance_cmd.add_argument(
        "--cache-only",
        action="store_true",
        help="refuse any OCPF request that is not already cached",
    )
    forecast_cmd = sub.add_parser(
        "forecast", help="fit and publish an immutable election forecast snapshot"
    )
    forecast_cmd.add_argument("--horizon", choices=["60d", "14d"], required=True)
    forecast_score_cmd = sub.add_parser(
        "forecast-score", help="score a locked forecast against certified results"
    )
    forecast_score_cmd.add_argument("--horizon", choices=["60d", "14d"], required=True)
    forecast_score_cmd.add_argument("--results", type=Path, required=True)
    forecast_score_cmd.add_argument("--result-source", required=True)

    args = parser.parse_args(argv)

    if args.command == "score":
        from . import score

        score.run(
            args.variants,
            args.definitions,
            write=not args.no_write,
            append=args.append,
            schedule_change=args.schedule_change,
        )
    elif args.command == "compare":
        import pandas as pd

        from . import compare
        from . import config as config_module

        reference, *others = args.variants
        if not others:
            compare_cmd.error("name at least two variants")
        reports = []
        sensitivities = []
        for definition in args.definition:
            for other in others:
                result = compare.run(reference, other, definition, write=False)
                reports.append(result)
                sensitivities.append(result.attrs["sensitivity"])
                result.attrs = {}
                print()
        report = pd.concat(reports, ignore_index=True).round(6)
        if args.append:
            report = config_module.merge_cells(
                report,
                config_module.VARIANT_COMPARISON,
                ["definition", "left_variant", "right_variant"],
            )
        config_module.write_csv(report, config_module.VARIANT_COMPARISON)
        sensitivity = pd.concat(sensitivities, ignore_index=True).round(6)
        if args.append:
            sensitivity = config_module.merge_cells(
                sensitivity,
                config_module.VARIANT_COMPARISON_SENSITIVITY,
                ["definition", "left_variant", "right_variant"],
            )
        config_module.write_csv(
            sensitivity, config_module.VARIANT_COMPARISON_SENSITIVITY
        )
    elif args.command == "compare-definitions":
        import pandas as pd

        from . import compare_definitions, config

        reference, *others = args.definitions
        if not others:
            cd_cmd.error("name at least two definitions")
        reports = []
        sensitivities = []
        for other in others:
            result = compare_definitions.run(reference, other, args.variant)
            reports.append(result)
            sensitivities.append(result.attrs["sensitivity"])
            result.attrs = {}
            print()
        report = pd.concat(reports, ignore_index=True).round(6)
        if args.append:
            report = config.merge_cells(
                report,
                config.DEFINITION_COMPARISON,
                ["left_definition", "right_definition", "variant"],
            )
        config.write_csv(report, config.DEFINITION_COMPARISON)
        sensitivity = pd.concat(sensitivities, ignore_index=True).round(6)
        if args.append:
            sensitivity = config.merge_cells(
                sensitivity,
                config.DEFINITION_COMPARISON_SENSITIVITY,
                ["left_definition", "right_definition", "variant"],
            )
        config.write_csv(sensitivity, config.DEFINITION_COMPARISON_SENSITIVITY)
    elif args.command == "sweep":
        from . import config, sweep

        frame = sweep.run(args.variant, score_each=not args.counts_only)
        print()
        print(frame.round(4).to_string(index=False))
        config.write_csv(frame.round(6), config.THRESHOLD_SWEEP)
    elif args.command == "importance":
        from . import importance

        importance.run(
            args.variant,
            args.definition,
            write=not args.no_write,
            append=args.append,
        )
    elif args.command == "parity":
        from . import parity

        parity.run()
    elif args.command == "folds":
        from . import config, definitions, folds

        definition = (
            definitions.get(args.definition)
            if args.definition
            else definitions.adopted()
        )
        races, roster = config.load_races(), config.load_roster()
        admitted, _ = definitions.apply(definition, races, roster)
        # Measured against every date in the record, not only the dates this
        # definition admits races on, so a date it empties is reported rather
        # than absent.
        eligible = folds.fold_dates(races)
        summary = folds.summary(admitted, eligible)
        print(f"definition: {definition.name}")
        print(folds.schedule(admitted, eligible).to_string(index=False))
        print()
        print(
            f"{summary['n_folds']} folds: "
            f"{summary['n_general_dates']} general dates carrying "
            f"{summary['general_races']} races, "
            f"{summary['n_special_dates']} special dates carrying "
            f"{summary['special_races']} races"
        )
        print(
            f"{summary['holdout_races']} holdout races, "
            f"{summary['seed_races']} seed races before {folds.SEED_CUTOFF}, "
            f"smallest training fold {summary['smallest_training_fold']}"
        )
        if summary["skipped_dates"]:
            print(f"skipped dates: {', '.join(summary['skipped_dates'])}")
    elif args.command == "variants":
        from . import variants

        for name, spec in variants.all_variants().items():
            print(f"{name:<24} {spec.declared}")
            # Only what the variant actually declares. A variant running on the
            # library's priors at the default target acceptance says nothing
            # here, so a line that does appear is a deliberate choice.
            if spec.prior_declaration:
                print(f"{'':<24}   prior: {spec.prior_declaration}")
            if spec.target_accept is not None:
                print(f"{'':<24}   target_accept: {spec.target_accept}")
            if spec.tune is not None:
                print(f"{'':<24}   tune: {spec.tune}")
            if spec.as_of:
                print(f"{'':<24}   as of: {spec.as_of}")
            if spec.requires:
                print(f"{'':<24}   requires: {', '.join(spec.requires)}")
            # A composite's own `requires` is the intersection of its
            # components', so a restriction only one component carries would
            # not appear above. Each component states its own (margin-model
            # spec, "A component's restriction is disclosed").
            for value, component in sorted(getattr(spec, "components", {}).items()):
                restriction = (
                    ", ".join(component.requires) if component.requires else "none"
                )
                print(
                    f"{'':<24}   component {value} ({component.name}): "
                    f"restriction: {restriction}"
                )
    elif args.command == "definitions":
        import pandas as pd

        from . import definitions

        races, roster = None, None
        rows = []
        for definition in definitions.all_definitions().values():
            if races is None:
                from . import config

                races, roster = config.load_races(), config.load_roster()
            admitted, dropped = definitions.apply(definition, races, roster)
            rows.append(
                {
                    **definition.as_row(),
                    "adopted": definition.adopted,
                    "races": len(admitted),
                    "scoreable": int(admitted["scoreable"].sum()),
                    "specials": int(admitted["is_special"].sum()),
                    "dropped": len(dropped),
                }
            )
        frame = pd.DataFrame(rows)
        print(
            frame[
                [
                    "definition",
                    "response",
                    "write_in_threshold",
                    "no_dem",
                    "criteria",
                    "train_only",
                    "races",
                    "scoreable",
                    "specials",
                    "dropped",
                    "adopted",
                ]
            ].to_string(index=False)
        )
    elif args.command == "tenure":
        from . import tenure

        tenure.run(write=not args.no_write)
    elif args.command == "target-finance":
        from . import forecast_finance

        forecast_finance.run(
            args.horizon, dry_run=args.dry_run, cache_only=args.cache_only
        )
    elif args.command == "forecast":
        from . import forecast_run

        forecast_run.run(args.horizon)
    elif args.command == "forecast-score":
        from . import forecast_score

        forecast_score.run(args.horizon, args.results, args.result_source)
    else:
        parser.error(f"unknown command {args.command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
