#!/usr/bin/env python3

from __future__ import annotations

import argparse
import pathlib
import unittest

from bazel_port.oci_runner import build_container_args


class OciRunnerTest(unittest.TestCase):
    def test_builds_read_only_source_mount_and_writable_build_dirs(self) -> None:
        args = argparse.Namespace(
            source=pathlib.Path("/repo"),
            work_dir=pathlib.Path("/tmp/work"),
            cache_dir=pathlib.Path("/tmp/cache"),
            engine="docker",
            image="example:test",
            network="none",
            env=["CI=1"],
            command="cp -a /src/. . && bazel test //...",
        )

        command = build_container_args(args)

        self.assertEqual(command[0:3], ["docker", "run", "--rm"])
        self.assertIn("/repo:/src:ro", command)
        self.assertIn("/tmp/work:/work", command)
        self.assertIn("/tmp/cache:/bazel-cache", command)
        self.assertIn("BAZEL_OUTPUT_USER_ROOT=/bazel-cache/output-user-root", command)
        self.assertIn("--network", command)
        self.assertIn("none", command)
        self.assertEqual(command[-4:], ["example:test", "/bin/sh", "-lc", "cp -a /src/. . && bazel test //..."])


if __name__ == "__main__":
    unittest.main()
