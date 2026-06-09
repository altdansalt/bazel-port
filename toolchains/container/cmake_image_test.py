#!/usr/bin/env python3

from __future__ import annotations

import gzip
import io
import json
import os
import pathlib
import subprocess
import tarfile
import tempfile
import unittest


def _find_image_layout() -> pathlib.Path:
    runfiles = pathlib.Path(os.environ["TEST_SRCDIR"])
    matches = sorted(runfiles.glob("**/toolchains/container/cmake_image/index.json"))
    if not matches:
        raise AssertionError("could not find cmake_image OCI layout in runfiles")
    return matches[0].parent


def _read_blob(layout: pathlib.Path, digest: str) -> bytes:
    algorithm, value = digest.split(":", 1)
    if algorithm != "sha256":
        raise AssertionError(f"unsupported digest algorithm: {algorithm}")
    return (layout / "blobs" / algorithm / value).read_bytes()


class CmakeImageTest(unittest.TestCase):
    def test_image_defaults_to_cmake_version(self) -> None:
        layout = _find_image_layout()
        index = json.loads((layout / "index.json").read_text())
        manifest = json.loads(_read_blob(layout, index["manifests"][0]["digest"]))
        config = json.loads(_read_blob(layout, manifest["config"]["digest"]))

        self.assertEqual(config["os"], "linux")
        self.assertEqual(config["architecture"], "amd64")
        self.assertEqual(config["config"]["Entrypoint"], ["/usr/bin/cmake"])
        self.assertEqual(config["config"]["Cmd"], ["--version"])

    def test_image_layer_contains_cmake_binary(self) -> None:
        layout = _find_image_layout()
        index = json.loads((layout / "index.json").read_text())
        manifest = json.loads(_read_blob(layout, index["manifests"][0]["digest"]))
        layer = _read_blob(layout, manifest["layers"][0]["digest"])

        with gzip.GzipFile(fileobj=io.BytesIO(layer)) as gz:
            with tarfile.open(fileobj=gz, mode="r|") as tar:
                for member in tar:
                    if member.name == "usr/bin/cmake":
                        self.assertTrue(member.isfile())
                        return

        self.fail("image layer does not contain usr/bin/cmake")

    def test_image_cmake_binary_runs_with_image_libraries(self) -> None:
        layout = _find_image_layout()
        index = json.loads((layout / "index.json").read_text())
        manifest = json.loads(_read_blob(layout, index["manifests"][0]["digest"]))
        layer = _read_blob(layout, manifest["layers"][0]["digest"])

        with tempfile.TemporaryDirectory() as temp_dir:
            rootfs = pathlib.Path(temp_dir) / "rootfs"
            rootfs.mkdir()
            with tarfile.open(fileobj=io.BytesIO(layer), mode="r:gz") as tar:
                for member in tar:
                    if member.ischr() or member.isblk() or member.isfifo():
                        continue
                    tar.extract(member, rootfs)

            loader = rootfs / "usr/lib/ld-linux-x86-64.so.2"
            cmake = rootfs / "usr/bin/cmake"
            lib_path = ":".join(
                [
                    str(rootfs / "usr/lib"),
                    str(rootfs / "lib"),
                    str(rootfs / "lib64"),
                ]
            )
            result = subprocess.run(
                [
                    str(loader),
                    "--library-path",
                    lib_path,
                    str(cmake),
                    "--version",
                ],
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        self.assertIn("cmake version", result.stdout.lower())


if __name__ == "__main__":
    unittest.main()
