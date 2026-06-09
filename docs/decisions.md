# Decision Log

Append-only record of non-obvious decisions: *what* was decided and *why*.
Newest entries go on top. Don't edit past entries — add a new one that
supersedes them. [STATUS.md](STATUS.md) says where we are; this says why.

## 2026-06-09 — Removed the `oci_runner` prototype and orphaned root runner

Deleted `//:oci_runner` (+ its test and sources) and the orphaned
`//:oci_layout_runner` root binary. **Why:** `oci_runner` shelled out to a host
OCI engine, which violates the dependency policy (no host container engine), so
it could never be part of a real port workflow; the root `oci_layout_runner`
binary was public but referenced nowhere and shipped without an image. The
functional image runners under `//toolchains/container` cover the real workflow.

## 2026-06-09 — Adopted continuously-edited docs over a single handoff

Replaced `docs/handoff.md` with a living `STATUS.md` plus this append-only
decision log, and moved port-specific state into port READMEs. **Why:** work
continues across many sessions, so there is no single handoff moment; mixing
slow-changing reference docs with per-session state in one file caused drift.

## (earlier) — `bubblewrap --unshare-net` for the no-network runner

`run_cmake_image_no_network` uses image-provided `bubblewrap` with
`--unshare-net` rather than `proot`. **Why:** it gives real network isolation
(verified by an outbound `wget` failing in the test) using a tool declared in
the Bazel-built image, not a host binary. `proot` is kept as a lighter runner
for the networked path. Caveat: bwrap needs unprivileged-namespace support from
the kernel/VM.

## (earlier) — llama.cpp HTTPS support disabled

The llama.cpp port builds without HTTPS support. **Why:** OpenSSL is not a
declared image dependency, so llama.cpp's build auto-disables HTTPS (it is not
forced off with a flag). Adding OpenSSL reproducibly is the alternative. This is
provisional — see the open question in STATUS.md next steps.

## (earlier) — llama.cpp pinned by raw commit

`@llama_cpp` is pinned to a raw commit archive rather than a release tag.
**Why:** it unblocked the first no-network CMake build. It should move to a
versioned release tag pinned by SHA-256 (tracked in STATUS.md next steps).
