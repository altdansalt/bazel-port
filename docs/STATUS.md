# Status

Living snapshot of where `bazel-port` is right now. This file is meant to be
**overwritten freely** — it should always describe HEAD, not a point in time.

- For *why* the project is in this state, see [decisions.md](decisions.md).
- For port-specific state, see that port's README (e.g.
  [ports/llama_cpp/README.md](../ports/llama_cpp/README.md)).

## What works now

The repository can build, test, and run its current tooling entirely through
Bazel. The current capability is a Bazel-built OCI image (no base image) that
runs a CMake build with networking disabled:

- `rules_apko` builds an OCI image from Wolfi APK packages.
- The image includes CMake, GCC, Make, Ninja, BusyBox, and Bubblewrap.
- `bazel_port/oci_layout_runner.py` unpacks an OCI layout and runs commands with
  either `proot` or `bubblewrap`.
- A pinned upstream `llama-cli` builds inside that image with networking off.

## Build / test / run

These are the canonical commands (single source of truth):

```sh
bazel test //...                                            # repository checks
bazel run //toolchains/container:run_cmake_image_no_network # cmake in no-network image
bazel build //ports/llama_cpp:cmake_build                   # build upstream llama-cli; output at
                                                            #   bazel-bin/ports/llama_cpp/build/
```

`//ports/llama_cpp:cmake_build` is a `bazel build` target whose declared output
is the CMake build tree. Bazel caches it keyed on its inputs (source archive,
image, runner, command), so re-running is a no-op until an input changes — no
more cold rebuilds.

## Known issues & caveats (repo-wide)

- `bubblewrap --unshare-net` is a declared image/tool dependency, but it still
  requires execution-platform support: the Linux kernel and VM policy must
  permit the unprivileged namespace operations it uses. This works in the
  current exe.dev VM.
- Neither `proot` nor `bubblewrap` is a complete OCI runtime (no cgroup
  semantics like `runc`/`crun`). They are lightweight smoke/build runners.

For port-specific caveats, see the port READMEs.

## Goals / roadmap

Provide reproducible Bazel targets for popular upstream projects so that each
port can be fetched, built, tested, and optionally containerized with only
`bazel build`/`test`/`run`. Near-term focus is hardening the CMake-in-image
baseline and growing the llama.cpp port toward a native Bazel build.

A concrete driver: be able to **compare the upstream CMake test suite against
the eventual native Bazel tests**. That requires running `ctest` repeatedly
without paying for a full CMake build each time — so the CMake build must be a
cacheable artifact (a `bazel build` output), and the test target must consume
that artifact rather than rebuild. The path being taken:

1. Teach `oci_layout_runner.py` to `--export` a guest path after the command.
2. Wrap the in-image CMake build in a `cmake_build` Bazel rule that declares the
   build tree as an output (so `bazel build` caches it). ← implemented
3. (next) Add `cmake_test` that binds the cached build tree back in at
   `/work/build` and runs `ctest` — no reconfigure, no rebuild.

## Next steps

- [ ] Switch `@llama_cpp` from a raw commit archive to a versioned upstream
      release tag, pinned by SHA-256.
- [ ] Add `//ports/llama_cpp:cmake_test` that consumes the cached `cmake_build`
      tree (binds it at `/work/build`) and runs a curated no-network `ctest`
      subset — no reconfigure/rebuild.
- [ ] Decide whether HTTPS support stays disabled (OpenSSL is absent from the
      image) or add OpenSSL as a declared image dependency.
- [ ] Declare any test models or assets as Bazel dependencies rather than
      letting tests download them.
- [ ] Consider native Bazel BUILD files for selected llama.cpp libraries or
      tools once the CMake baseline is stable.
