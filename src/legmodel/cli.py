"""Command line entry point for fitting and scoring.

    uv run legmodel score
    uv run legmodel score --variants baseline
    uv run legmodel compare baseline baseline_special
    uv run legmodel parity
"""

from __future__ import annotations

import argparse


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

    compare_cmd = sub.add_parser("compare", help="paired comparison of two variants")
    compare_cmd.add_argument("variants", nargs=2, metavar="VARIANT")

    sub.add_parser("parity", help="check baseline coefficients against mapoli")
    sub.add_parser("variants", help="list registered variants")

    args = parser.parse_args(argv)

    if args.command == "score":
        from . import score

        score.run(args.variants)
    elif args.command == "compare":
        from . import compare

        compare.run(args.variants[0], args.variants[1])
    elif args.command == "parity":
        from . import parity

        parity.run()
    elif args.command == "variants":
        from . import variants

        for name, spec in variants.all_variants().items():
            print(f"{name:<20} {spec.formula}")
    else:
        parser.error(f"unknown command {args.command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
