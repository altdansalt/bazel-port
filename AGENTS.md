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

## Working across sessions

This repo is worked on continuously across many sessions, so docs are split by
how fast they change. Two principles keep them from drifting:

1. **Volatile status lives in exactly one place.** Current state, commands,
   known issues, and next steps belong in `docs/STATUS.md` (repo-wide) or a port
   README (port-specific). Reference docs describe *mechanisms and rules*, not
   *status* — link to STATUS.md rather than restating it.
2. **Record the why, not just the what.** When you make a non-obvious decision,
   add a dated entry to `docs/decisions.md` (append-only, newest on top).
   STATUS.md says where we are; the decision log says why.

Start a session by reading `docs/STATUS.md`. End one by updating it (and any
affected port README), and append to `docs/decisions.md` for decisions worth
remembering.
