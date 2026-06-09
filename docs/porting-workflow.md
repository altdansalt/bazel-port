# Porting Workflow

The first reproducibility target for each port is:

1. Build the upstream project.
2. Run its test suite.
3. Declare the upstream source repo and every required tool as Bazel
   dependencies.
4. Run the workflow with `bazel build`, `bazel test`, or `bazel run` only.

This creates a baseline before deeper Bazel porting starts. It also makes
failures easier to compare across agents and machines.

## Hard requirements

- Do not rely on host-installed Docker, Podman, CMake, Ninja, compilers,
  package managers, Python packages, or source checkouts.
- Do not download source repos from an ad hoc shell command.
- Do not run `apt-get`, `brew`, `pip install`, or similar package-manager
  commands as part of the port workflow.
- Pin source repositories and tool versions.
- Prefer Bazel Central Registry modules where available.
- Use repository rules or module extensions for source repos that are not Bazel
  modules.

## Port target shape

Each port should grow targets with names like:

- `//ports/<project>:build`: builds the pinned upstream project
- `//ports/<project>:test`: runs the upstream test suite or a documented
  representative subset
- `//ports/<project>:image`: builds an OCI image when container execution is
  useful
- `//ports/<project>:run`: runs the built artifact when there is a meaningful
  smoke-test command

## OCI usage

OCI images are useful for reproducibility, but this repo must build image
artifacts through Bazel-declared rules and inputs. A target that shells out to a
host container engine is acceptable only as a temporary diagnostic aid, not as a
completed port workflow.

For CMake-based projects such as llama.cpp, the expected direction is to declare
the source archive and CMake-oriented build rules in Bazel, then expose the
native build and test suite as Bazel targets.

## Notes for exe.dev

This repo should use documented exe.dev behavior only. The public documentation
entry point is <https://exe.dev/docs.md>. HTTPS proxy behavior is documented at
<https://exe.dev/docs/proxy.md>.
