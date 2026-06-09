#!/usr/bin/env python3

from __future__ import annotations

import unittest

from bazel_port import oci_layout_runner


class RunCmakeImageBwrapTest(unittest.TestCase):
    def test_runs_cmake_version_without_network(self) -> None:
        exit_code = oci_layout_runner.main(
            [
                "--image-layout",
                "toolchains/container/cmake_image",
                "--runtime",
                "bwrap",
                "--network",
                "none",
                "--",
                "/usr/bin/cmake",
                "--version",
            ]
        )

        self.assertEqual(exit_code, 0)

    def test_network_is_disabled(self) -> None:
        exit_code = oci_layout_runner.main(
            [
                "--image-layout",
                "toolchains/container/cmake_image",
                "--runtime",
                "bwrap",
                "--network",
                "none",
                "--",
                "/bin/busybox",
                "wget",
                "-q",
                "-O",
                "-",
                "https://example.com",
            ]
        )

        self.assertNotEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
