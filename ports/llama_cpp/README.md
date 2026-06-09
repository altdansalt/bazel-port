# llama.cpp Port

The llama.cpp port must be driven entirely by Bazel.

## Target contract

Expected user-facing targets:

- `//ports/llama_cpp:build`
- `//ports/llama_cpp:test`
- `//ports/llama_cpp:image`, if container packaging is needed
- `//ports/llama_cpp:run`, if a meaningful model-free smoke run exists

## Dependency contract

The port should declare:

- the pinned llama.cpp source repository
- the C/C++ toolchain
- CMake/Ninja or replacement build tooling, if using the upstream CMake build as
  the baseline
- any OCI base image by digest, if an image target is added

No step should require a manually cloned llama.cpp checkout, host CMake, host
Docker, or package-manager installs.

## Initial baseline

The first useful baseline is a CPU-only CMake build inside the Bazel-built
container image. In native upstream terms this corresponds to configuring CMake
out-of-source, building selected targets, and later running `ctest`, but those
steps must be represented by Bazel targets rather than shell prerequisites.

Current build target:

```sh
bazel build //ports/llama_cpp:cmake_build
# output: bazel-bin/ports/llama_cpp/build/  (the CMake build tree)
```

This is a `cmake_build` rule (see [bazel_port/cmake.bzl](../../bazel_port/cmake.bzl))
whose declared output is the CMake build tree, so Bazel caches it and re-running
is a no-op until an input changes. The target:

- uses the pinned `@llama_cpp` source archive declared in `MODULE.bazel`
- runs inside `//toolchains/container:cmake_image`
- uses the image-provided `bubblewrap` runtime with network disabled
- binds source at `/src`
- creates a writable `/work`
- configures CMake out-of-source into `/work/build`
- disables the embedded UI download path with `LLAMA_BUILD_UI=OFF`
- builds the upstream `llama-cli` target
- exports `/work/build` to the declared output directory

The build uses `bubblewrap --unshare-net`, so it depends on the execution
platform permitting unprivileged namespace operations, and the build action runs
unsandboxed (`no-sandbox`/`local`) so bubblewrap's namespaces don't nest inside
Bazel's sandbox. The `bubblewrap` binary is provided by the Bazel-built image;
the kernel/VM capability is the remaining platform assumption.

The build tree embeds absolute guest paths (`/src`, `/work/build`); a future
`cmake_test` must re-mount the captured tree at the same `/work/build` so
`ctest` runs without reconfiguring.

An earlier exploratory run also completed the upstream default CMake build. The
checked-in target is narrower so it is faster and avoids the upstream UI asset
download path.

## Current pin

`@llama_cpp` is pinned to commit:

```text
49f354219059fc22316ae3efa54e54ba37f77860
```

## Known issues & caveats

- The pin is a raw commit archive, not a release tag (should move to a `bNNNN`
  tag pinned by SHA-256). See [decisions.md](../../docs/decisions.md).
- Git is not installed in the image, so upstream build metadata reports an
  unknown commit.
- OpenSSL is not installed in the image, so HTTPS support is disabled.
- `ctest` is not wired as a Bazel target yet (CMake is configured with
  `-DLLAMA_BUILD_TESTS=ON`, but no Bazel `cmake_test` target exists).
- This target builds `llama-cli` only, not the full upstream target graph.
