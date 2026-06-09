#!/usr/bin/env python3

from __future__ import annotations

import sys

from bazel_port import oci_layout_runner


def main() -> int:
    return oci_layout_runner.main(
        [
            "--image-layout",
            "toolchains/container/cmake_image",
            "--runtime",
            "bwrap",
            "--network",
            "none",
            "--bind-parent",
            "llama_cpp/CMakeLists.txt:/src",
            "--workspace",
            "/work",
            "--workdir",
            "/work",
            "--clear-env",
            "--env",
            "HOME=/work",
            "--env",
            "PATH=/usr/local/sbin:/usr/local/bin:/usr/bin:/usr/sbin:/sbin:/bin",
            "--env",
            "SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt",
            "--env",
            "CC=/usr/bin/gcc",
            "--env",
            "CXX=/usr/bin/g++",
            "--",
            "/bin/bash",
            "--noprofile",
            "--norc",
            "-c",
            "cmake -S /src -B /work/build -G 'Unix Makefiles' "
            "-DLLAMA_BUILD_TESTS=ON "
            "-DLLAMA_BUILD_UI=OFF "
            "-DGGML_CCACHE=OFF "
            "&& cmake --build /work/build --target llama-cli -- -j2",
        ]
    )


if __name__ == "__main__":
    sys.exit(main())
