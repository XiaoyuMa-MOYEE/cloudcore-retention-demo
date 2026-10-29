"""Command-line entry point for local pre-API preparation."""

import argparse
import sys
from pathlib import Path

from .config import load_config
from .pipeline import run_live, run_pre_api


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and prepare CloudCore records locally up to the API boundary.")
    parser.add_argument("--config", default="config.yaml", help="Path to YAML configuration (default: config.yaml)")
    parser.add_argument("--input", help="Override configured input CSV")
    parser.add_argument("--dry-run", action="store_true", help="Prepare local request payloads only; never call an API")
    parser.add_argument("--live", action="store_true", help="Call the configured external provider")
    parser.add_argument("--synthetic-data", action="store_true", help="Assert that this input contains synthetic test data")
    parser.add_argument("--api-smoke", action="store_true", help="With --live, send only the first valid record")
    args = parser.parse_args()

    if args.api_smoke and not args.live:
        parser.error("--api-smoke requires --live.")
    if args.synthetic_data and not args.live:
        parser.error("--synthetic-data is meaningful only with --live.")
    if args.live and args.dry_run:
        parser.error("Choose either --live or --dry-run.")
    if args.live:
        try:
            from dotenv import load_dotenv
        except ImportError:
            print("Configuration error: python-dotenv is not installed. Install local dependencies with pip install -r requirements-local.txt.", file=sys.stderr)
            return 2
        load_dotenv(dotenv_path=Path.cwd() / ".env", override=False, encoding="utf-8-sig")

    try:
        config = load_config(args.config)
        if args.live:
            ok, summary = run_live(config, args.input, synthetic_data=args.synthetic_data,
                                   smoke_test=args.api_smoke)
        else:
            ok, summary = run_pre_api(config, args.input)
    except ValueError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    print(summary)
    if args.dry_run:
        print("Dry-run mode: prepared data remains local; no third-party API call was made.")
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
