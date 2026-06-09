# Agent Notes

This repository is developed in an exe.dev VM.

Use only documented exe.dev features. The documentation entry point is
<https://exe.dev/docs.md>; HTTPS proxy behavior is documented at
<https://exe.dev/docs/proxy.md>.

The software in this repository must be buildable, testable, and runnable with
Bazel.

Required tools and source repositories must be declared as Bazel dependencies.
Do not rely on host-installed Docker, Podman, CMake, compilers, package
managers, Python packages, or manually cloned source trees for project
workflows.

When adding porting logic, document the workflow and assumptions in this repo so
future agents can reproduce the same steps.
