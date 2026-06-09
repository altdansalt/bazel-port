# Design note: remote caching & remote build execution (RBE)

**Status: open question — no decision made yet.** This captures the goal, what
was learned, and the paths in front of us so the choice can be made
deliberately. When a path is chosen, record it in [decisions.md](decisions.md)
and update [STATUS.md](STATUS.md).

## Goal

Make the in-image CMake build (and the eventual `cmake_test`) work well with:

- **Remote caching** — a hermetic action whose result is shared via a CAS /
  action cache, so a build done once (on any machine) is reused everywhere.
- **Remote build execution (RBE)** — the action runs on a remote worker, not
  just the local machine.

These are different capabilities (see "Caching ≠ execution" below) and the easy
win — remote caching — is worth most of the value.

## Why this isn't automatic: the two jobs bubblewrap does

Today `//ports/llama_cpp:cmake_build` runs through
`bazel_port/oci_layout_runner.py`, which uses image-provided `bubblewrap`.
Bubblewrap is doing two separable jobs:

1. **Supply the image filesystem as `/`** so the build uses the image's
   `cmake`/`gcc`/`glibc`/dynamic-loader instead of host tools. **Bazel cannot do
   this** — Bazel roots an action at the execroot, not at an arbitrary OCI
   rootfs. Only a runtime (bwrap/proot/runc) or making the image the *execution
   platform* can put the image at `/`.
2. **Isolation: no network + read-only inputs.** **Bazel provides this natively**
   — read-only inputs are the linux-sandbox default, and network can be blocked
   with `--sandbox_default_allow_network=false` or the `block-network` tag; RBE
   workers also stage inputs read-only and run without network. So bubblewrap is
   *not* needed for isolation, only for job 1.

## What we learned (2026-06-09 experiments)

- bubblewrap **does** nest inside Bazel's `linux-sandbox` in the current VM (a
  scratch `bwrap --unshare-net` genrule and the existing
  `run_cmake_image_bwrap_test` both pass sandboxed). So the namespace nesting we
  feared is not itself the blocker here.
- **But the real `cmake_build` fails under `linux-sandbox`:**
  `CMake Error: The source directory "/src" does not appear to contain
  CMakeLists.txt`. Root cause: the runner **bind-mounts execroot paths** into
  bwrap. Under local execution that works because the source dir is a symlink
  that dereferences to real files; under the sandbox, Bazel stages inputs as
  per-file symlinks into the output base, and bwrap's mount namespace doesn't
  include those targets, so they dangle and `/src` looks empty.
- This is a **hermeticity bug**, and it is the real blocker — more than
  namespaces. The "bind execroot symlinks into a container" model is
  fundamentally not sandbox-/RBE-clean.
- Because of this, the action is currently tagged `{no-sandbox, local}`. Those
  tags also **disable remote caching and remote execution**, so as committed the
  target is opted out of both.

## Caching ≠ execution (caching is the easy 80%)

A hermetic action that is *not* tagged `local`/`no-cache` is shared via the
remote cache while still executing locally — "build once anywhere, reuse
everywhere." This needs only: (a) fix the input-materialization bug so the
action is hermetic under sandboxing, and (b) drop the `local`/`no-sandbox` tags.
Remote *execution* is the harder, separate step.

## Paths

### Option A — make the apko image the *execution platform* (RBE-native)

- Push the image to a registry (`rules_oci` push), pin by digest.
- Define a `platform` with
  `exec_properties = {"container-image": "docker://repo@sha256:…"}`.
- The build becomes an **ordinary action**: `cmake -S … -B … && cmake --build`,
  `inputs = source`, `outputs = declare_directory("build")`. **No bubblewrap.**
  The RBE worker starts the action already inside the image, so `cmake`/`gcc`
  are at `/usr/bin`, and the worker + Bazel provide read-only inputs and
  no-network for free.
- This is the well-trodden RBE pattern (rules_foreign_cc + RBE, Google's own
  builds). Locally reproduce it with the Docker sandbox
  (`--experimental_docker_image`) or by having the toolchain present.
- **Pros:** the sane, standard route to real RBE; deletes bubblewrap from the
  build; isolation becomes Bazel's job. **Cons:** real rearchitecture — registry
  push + platform config, and a local-dev story for providing the toolchain.

### Option B — keep bubblewrap, make it sandbox-correct

- Fix the runner to **materialize real input files into the rootfs** (copy /
  dereference source into the tempdir's `/src`, read the image from declared
  inputs) instead of bind-mounting execroot symlinks. Then drop
  `local`/`no-sandbox`.
- **Pros:** earns reliable remote *caching* with minimal rearchitecture; keeps
  the current design. **Cons:** remote *execution* still depends on the RBE
  worker permitting unprivileged nested namespaces, which many managed /
  gVisor-based RBE services forbid — so this is largely a dead end for portable
  RBE.

## Caveat that shapes `cmake_test`: CMake build trees don't relocate

CMake bakes absolute paths into the build tree, and each RBE action gets its own
exec root, so a tree built by one action won't have valid paths for a *separate*
`ctest` action. Implications:

- The RBE-clean shape is a **single action that configures + builds + runs
  ctest**, cached as a unit. Remote caching of that combined action already
  delivers "don't rebuild every time I run the tests."
- Splitting into separate `cmake_build` + `cmake_test` targets mainly helps
  *local* iteration, not RBE. If we keep the split, the build tree is only
  safely reusable within the same environment/path it was produced in.
- Alternative: make the build relocatable (relocatable RPATH, no absolute
  paths), which is more fragile.

## What to decide

1. Is RBE (remote *execution*) a real destination, or is remote *caching*
   enough for now?
2. If RBE: commit to Option A (image-as-platform) and the registry/platform
   plumbing it needs.
3. For tests: combined build+test action (RBE-friendly) vs. split
   `cmake_build` + `cmake_test` (better local iteration, weaker on RBE).
