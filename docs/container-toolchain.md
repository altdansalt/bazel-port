# Container Toolchain

The first concrete project milestone is a Bazel-built OCI image that can run
`cmake --version`.

## Direction

Use `rules_apko` to build an OCI root filesystem from APK packages, without
starting from an existing container image. Use `rules_oci` for later image
composition and registry/image-layout operations.

The initial image config is:

- [toolchains/container/cmake-image.apko.yaml](../toolchains/container/cmake-image.apko.yaml)

It declares Wolfi APK repositories and packages for:

- `cmake`
- `ninja`
- `make`
- `gcc`
- `glibc`
- certificate and small POSIX utility support

## Targets

Current targets:

```sh
bazel run //toolchains/container:cmake_image_lock
bazel build //toolchains/container:cmake_image
bazel test //toolchains/container:cmake_image_test
```

`cmake_image_lock` regenerates the APK lockfile for the image config.
`cmake_image` builds the OCI image from the checked-in lockfile.
`cmake_image_test` verifies the OCI image metadata and confirms that the
image-provided CMake binary can start with the image-provided dynamic loader and
libraries.
`run_cmake_image_test` runs the image through the declared `proot` binary.
`run_cmake_image_bwrap_test` runs the image through image-provided `bubblewrap`
with networking disabled and verifies an outbound `wget` fails.

The image target produces an OCI image layout:

```sh
bazel-bin/toolchains/container/cmake_image/
```

Run the image default command:

```sh
bazel run //toolchains/container:run_cmake_image
```

Override the image command:

```sh
bazel run //toolchains/container:run_cmake_image -- /usr/bin/cmake --version
```

Run with network disabled through `bubblewrap`:

```sh
bazel run //toolchains/container:run_cmake_image_no_network
```

## Runtime Model

`run_cmake_image` uses a pinned `proot` binary downloaded by Bazel. This gives
us a practical user-space rootfs runner without Docker, Podman, or host CMake.

`run_cmake_image_no_network` uses `bubblewrap` from the Bazel-built image and
passes `--unshare-net`, so commands run without host network access on platforms
that permit unprivileged user/network namespaces.

This is a declared tool dependency, not a host binary dependency, but it is still
an execution-platform requirement: the Linux kernel and VM policy must allow the
namespace operations that `bubblewrap` uses. This works in the current exe.dev
VM.

Neither path is a complete OCI runtime implementation with cgroup semantics like
`runc`/`crun`. If later port workflows need stricter container semantics, add a
full OCI runtime target and keep these paths as lightweight smoke/build runners.
