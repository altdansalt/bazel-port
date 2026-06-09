# Dependency Policy

`bazel-port` workflows must be reproducible from Bazel declarations.

## Allowed host assumptions

- Bazel is available.
- Network access may be available for Bazel repository fetching, subject to the
  configured Bazel lockfile and repository rules.
- The execution platform may need to support specific kernel features required
  by declared sandbox/runtime tools. For example, the current network-disabled
  image runner uses `bubblewrap`, which requires unprivileged namespace support.

## Not allowed as workflow assumptions

- Preinstalled Docker or Podman
- Preinstalled CMake, Ninja, Make, compilers, or linkers
- Preinstalled language package managers or packages
- Manually cloned upstream source trees
- Package-manager commands such as `apt-get`, `brew`, or `pip install`

## Declaring inputs

- Bazel rulesets should be declared in `MODULE.bazel`.
- Source repositories should be pinned by commit, tag, archive digest, or another
  reproducible identifier.
- Toolchains should be declared through Bazel modules, repository rules, or
  checked-in definitions.
- OCI images, when used, should be pinned by digest and built or consumed by
  Bazel targets.

## Temporary diagnostics

Ad hoc scripts may be useful while learning an upstream project, but they should
not be the final interface for a port. The committed port interface should be
`bazel build`, `bazel test`, or `bazel run` targets.
