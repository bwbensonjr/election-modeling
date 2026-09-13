"""Command line entry point for the precinct data pipeline.

Stages are ordered by dependency and can be run individually or together:

    uv run maprecinct fetch all
    uv run maprecinct normalize
    uv run maprecinct districts
    uv run maprecinct pvi
    uv run maprecinct training
    uv run maprecinct races
    uv run maprecinct validate
    uv run maprecinct all
"""

from __future__ import annotations

import argparse
import sys


def _fetch(scope: str, force: bool = False) -> None:
    from . import bulk, elections

    if scope in ("presidential", "all"):
        bulk.fetch_many(
            elections.presidential_elections(),
            "presidential",
            "fetch_failures_presidential.csv",
            force=force,
        )
    if scope in ("legislative", "all"):
        bulk.fetch_many(
            elections.legislative_elections(),
            "legislative",
            "fetch_failures_legislative.csv",
            force=force,
        )


def _normalize() -> None:
    from . import build, elections, reconcile

    build.build_presidential()
    build.build_legislative()
    reconcile.reconcile_many(
        elections.presidential_elections(), "reconcile_presidential.csv"
    )
    reconcile.reconcile_many(
        elections.legislative_elections(), "reconcile_legislative.csv"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="maprecinct", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    fetch_cmd = sub.add_parser("fetch", help="retrieve precinct results")
    fetch_cmd.add_argument("scope", choices=["presidential", "legislative", "all"])
    fetch_cmd.add_argument("--force", action="store_true", help="refetch even if cached")

    sub.add_parser("normalize", help="normalize cached results and reconcile totals")
    sub.add_parser("districts", help="derive precinct-to-district mappings")
    sub.add_parser("pvi", help="compute precinct PVI for every required dataset")
    sub.add_parser("training", help="assemble the race-precinct training table")
    sub.add_parser("races", help="roll the training table up to one row per race")
    sub.add_parser("validate", help="run the PVI and training validations")
    sub.add_parser("all", help="run every stage in order")

    args = parser.parse_args(argv)

    if args.command == "fetch":
        _fetch(args.scope, args.force)
    elif args.command == "normalize":
        _normalize()
    elif args.command == "districts":
        from . import districts

        districts.build_and_write()
    elif args.command == "pvi":
        from . import pvi

        pvi.build_all()
    elif args.command == "training":
        from . import training

        training.build_and_write()
    elif args.command == "races":
        from . import races

        races.build_and_write()
    elif args.command == "validate":
        from . import races, validate, validate_training

        validate.run()
        validate_training.run()
        races.validate_rollup()
    elif args.command == "all":
        from . import districts, pvi, races, training, validate, validate_training

        _fetch("all")
        _normalize()
        districts.build_and_write()
        pvi.build_all()
        training.build_and_write()
        races.build_and_write()
        validate.run()
        validate_training.run()
        races.validate_rollup()
    else:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
