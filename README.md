# bazel-port

`bazel-port` collects tooling and documentation for adding Bazel build and test
support to popular open source projects.

The project is itself built, tested, and run with Bazel. Required tools and
source repositories must be declared as Bazel dependencies; workflows must not
assume tools such as Docker, CMake, compilers, package managers, or source
checkouts already exist in the host environment.

## Reproducibility contract

Every port should provide Bazel targets for:

- fetching the upstream source at a pinned version
- building the upstream project
- running the upstream test suite
- optionally packaging or running the result in an OCI image

The host contract is intentionally small:

- `bazel build ...`
- `bazel test ...`
- `bazel run ...`

If a workflow needs an upstream repo, CMake, Ninja, Python packages, OCI image
layers, or other tools, those inputs belong in Bazel dependency declarations.

## Current direction

The current milestone is a Bazel-built OCI image, with no base image, that can
run `cmake --version` through a Bazel-declared user-space rootfs runner. See
[Container toolchain](docs/container-toolchain.md).

`//:oci_runner` is retained only as an early diagnostic prototype. It shells out
to a host OCI engine, so it is not part of the final workflow.

## Repository checks

```sh
bazel test //...
```

## Documentation

- [Dependency policy](docs/dependency-policy.md)
- [Container toolchain](docs/container-toolchain.md)
- [Handoff](docs/handoff.md)
- [Porting workflow](docs/porting-workflow.md)
