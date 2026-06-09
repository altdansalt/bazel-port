# Handoff

This document captures the current project state for the next agent or person
working on `bazel-port`.

## Current State

The repository can build, test, and run its current tooling with Bazel.

Important targets:

```sh
bazel test //...
bazel run //toolchains/container:run_cmake_image_no_network
bazel run //ports/llama_cpp:cmake_build
```

The current architecture:

- `rules_apko` builds an OCI image from Wolfi APK packages, with no base image.
- The image includes CMake, GCC, Make, Ninja, BusyBox, and Bubblewrap.
- `bazel_port/oci_layout_runner.py` unpacks an OCI layout and runs commands with
  either `proot` or `bubblewrap`.
- `//toolchains/container:run_cmake_image_no_network` uses image-provided
  `bubblewrap` with `--unshare-net`.
- `//ports/llama_cpp:cmake_build` builds upstream `llama-cli` from pinned source
  inside the Bazel-built image with networking disabled.

## Important Caveat

`bubblewrap` is a declared image/tool dependency, not a host binary dependency.
However, it still requires execution-platform support from the Linux kernel and
VM policy. In particular, the platform must permit the unprivileged namespace
operations used by `bubblewrap --unshare-net`.

This works in the current exe.dev VM.

## Current llama.cpp Pin

The current `@llama_cpp` source repository is pinned to commit:

```text
49f354219059fc22316ae3efa54e54ba37f77860
```

This should likely move to an upstream release tag such as `bNNNN`, pinned by
archive SHA-256.

## Known Caveats

- The llama.cpp pin is a raw commit archive, not a release tag.
- Git is not installed in the image, so upstream build metadata reports an
  unknown commit.
- OpenSSL is not installed in the image, so llama.cpp HTTPS support is disabled.
- `ctest` is not wired as a Bazel target yet.
- The checked-in llama.cpp target builds `llama-cli`, not the entire default
  upstream target graph.

## What Helped Clarify the Shape

Two constraints were decisive:

- Everything needed by the project must be declared in Bazel: source repos,
  tools, images, and runners. Do not rely on host Docker, host CMake, host
  source checkouts, or package-manager installs.
- The first useful milestone is not a native Bazel port of llama.cpp. It is a
  Bazel-built image that can run CMake, followed by a no-network CMake build of
  a pinned upstream target.

These constraints led to the current `rules_apko` plus `bubblewrap` design.

## Suggested Next Steps

1. Switch `@llama_cpp` from the current raw commit archive to a versioned
   upstream release tag, pinned by SHA-256.
2. Add `//ports/llama_cpp:cmake_test` for a curated no-network `ctest` subset.
3. Decide whether HTTPS support is intentionally disabled with
   `-DLLAMA_OPENSSL=OFF`, or add OpenSSL as a declared image dependency.
4. Declare any test models or assets as Bazel dependencies rather than allowing
   tests to download them.
5. Consider adding native Bazel BUILD files for selected llama.cpp libraries or
   tools after the CMake baseline is stable.
