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
bazel run //ports/llama_cpp:cmake_build
```

This target:

- uses the pinned `@llama_cpp` source archive declared in `MODULE.bazel`
- runs inside `//toolchains/container:cmake_image`
- uses the image-provided `bubblewrap` runtime with network disabled
- binds source at `/src`
- creates a writable `/work`
- configures CMake out-of-source into `/work/build`
- disables the embedded UI download path with `LLAMA_BUILD_UI=OFF`
- builds the upstream `llama-cli` target

The build uses `bubblewrap --unshare-net`, so it depends on the execution
platform permitting unprivileged namespace operations. The `bubblewrap` binary is
provided by the Bazel-built image; the kernel/VM capability is the remaining
platform assumption.

An earlier exploratory run also completed the upstream default CMake build. The
checked-in target is narrower so it is faster and avoids the upstream UI asset
download path.
