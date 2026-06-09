#!/usr/bin/env python3

from __future__ import annotations

import unittest

from bazel_port import oci_layout_runner


class RunCmakeImageTest(unittest.TestCase):
    def test_runs_cmake_version_from_oci_image(self) -> None:
        exit_code = oci_layout_runner.main(
            [
                "--image-layout",
                "toolchains/container/cmake_image",
                "--proot",
                "file/proot",
                "--",
                "/usr/bin/cmake",
                "--version",
            ]
        )

        self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
