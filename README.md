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

For where the project is right now — what works, how to build/test/run, known
issues, and next steps — see [Status](docs/STATUS.md). For *why* the project is
in that state, see the [Decision log](docs/decisions.md).

## Repository checks

```sh
bazel test //...
```

## Documentation

State (changes often):

- [Status](docs/STATUS.md) — current capability, commands, known issues, roadmap
- [Decision log](docs/decisions.md) — append-only record of why

Reference (changes slowly):

- [Dependency policy](docs/dependency-policy.md)
- [Container toolchain](docs/container-toolchain.md)
- [Porting workflow](docs/porting-workflow.md)
- [llama.cpp port](ports/llama_cpp/README.md)
