#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["PyYAML>=6.0"]
# ///
"""Unified command-line interface for the AICC skill collection."""

from __future__ import annotations

import argparse

from core.paths import ensure_orchestrator_imports

ensure_orchestrator_imports()

from commands import COMMAND_MODULES  # noqa: E402 - bootstrap sibling helper modules first


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aicc", description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for module in COMMAND_MODULES:
        module.register(subparsers)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
