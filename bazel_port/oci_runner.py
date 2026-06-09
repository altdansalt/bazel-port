#!/usr/bin/env python3
"""Diagnostic OCI runner prototype.

This target shells out to a host OCI engine, so it does not satisfy the
project's final reproducibility contract. Finished port workflows must declare
their tools and source repos as Bazel dependencies.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import shlex
import subprocess
import sys
import tempfile


DEFAULT_IMAGE = "ubuntu:24.04"


def _absolute_dir(path: str) -> pathlib.Path:
    resolved = pathlib.Path(path).expanduser().resolve()
    if not resolved.is_dir():
        raise argparse.ArgumentTypeError(f"{path!r} is not a directory")
    return resolved


def build_container_args(args: argparse.Namespace) -> list[str]:
    source_dir = pathlib.Path(args.source).resolve()
    work_dir = pathlib.Path(args.work_dir).resolve()
    cache_dir = pathlib.Path(args.cache_dir).resolve()

    container_args = [
        args.engine,
        "run",
        "--rm",
        "--init",
        "--volume",
        f"{source_dir}:/src:ro",
        "--volume",
        f"{work_dir}:/work",
        "--volume",
        f"{cache_dir}:/bazel-cache",
        "--workdir",
        "/work",
        "--env",
        "BAZEL_OUTPUT_USER_ROOT=/bazel-cache/output-user-root",
    ]

    if args.network == "none":
        container_args.extend(["--network", "none"])
    elif args.network != "default":
        container_args.extend(["--network", args.network])

    for env in args.env:
        container_args.extend(["--env", env])

    container_args.append(args.image)
    container_args.extend(["/bin/sh", "-lc", args.command])
    return container_args


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Diagnostic prototype: run a build/test command in an OCI "
            "container using a host OCI engine. This is not the final "
            "reproducible port interface."
        )
    )
    parser.add_argument(
        "--source",
        type=_absolute_dir,
        default=os.getcwd(),
        help="source tree to mount read-only at /src (default: current directory)",
    )
    parser.add_argument(
        "--image",
        default=DEFAULT_IMAGE,
        help=f"OCI image to run (default: {DEFAULT_IMAGE})",
    )
    parser.add_argument(
        "--engine",
        default=os.environ.get("OCI_ENGINE", "docker"),
        help="OCI engine executable (default: OCI_ENGINE or docker)",
    )
    parser.add_argument(
        "--work-dir",
        type=_absolute_dir,
        default=None,
        help="host directory mounted writable at /work (default: temporary directory)",
    )
    parser.add_argument(
        "--cache-dir",
        type=_absolute_dir,
        default=None,
        help="host directory mounted writable at /bazel-cache (default: temporary directory)",
    )
    parser.add_argument(
        "--network",
        default="default",
        help="container network mode: default, none, or an engine-specific mode",
    )
    parser.add_argument(
        "--env",
        action="append",
        default=[],
        metavar="NAME=VALUE",
        help="environment variable to pass into the container; repeatable",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the engine command instead of executing it",
    )
    parser.add_argument(
        "command",
        help="shell command to run in the container, for example: 'cp -a /src/. . && bazel test //...'",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    with tempfile.TemporaryDirectory(prefix="bazel-port-work-") as temp_work, tempfile.TemporaryDirectory(
        prefix="bazel-port-cache-"
    ) as temp_cache:
        if args.work_dir is None:
            args.work_dir = pathlib.Path(temp_work)
        if args.cache_dir is None:
            args.cache_dir = pathlib.Path(temp_cache)

        container_args = build_container_args(args)
        if args.dry_run:
            print(shlex.join(container_args))
            return 0

        return subprocess.run(container_args, check=False).returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
