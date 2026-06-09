"""Run a CMake build inside a Bazel-built OCI image and capture the build tree.

This turns the in-image CMake build into a cacheable `bazel build` target: the
CMake build directory is declared as an output, so Bazel reuses it until an
input changes (source archive, image, runner, or command), and downstream
targets such as a `ctest` runner can consume it without rebuilding.

The build still runs through `//bazel_port:oci_layout_runner` with the
image-provided `bubblewrap` and networking disabled. The action runs
unsandboxed (`no-sandbox`/`local`) because bubblewrap's namespaces cannot nest
inside Bazel's linux-sandbox; this matches how `bazel run` already invoked it.
"""

# Environment for the in-image build. These are image-specific (paths and
# toolchain locations inside the apko image), not port-specific.
_STANDARD_ENV = [
    "HOME=/work",
    "PATH=/usr/local/sbin:/usr/local/bin:/usr/bin:/usr/sbin:/sbin:/bin",
    "SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt",
    "CC=/usr/bin/gcc",
    "CXX=/usr/bin/g++",
]

def _shallowest(files, basename):
    """Return the matching file with the fewest path segments (the top-level one)."""
    found = None
    for f in files:
        if f.basename == basename:
            if found == None or len(f.path.split("/")) < len(found.path.split("/")):
                found = f
    return found

def _cmake_build_impl(ctx):
    srcs = ctx.files.srcs
    image_files = ctx.files.image

    cmake_lists = _shallowest(srcs, "CMakeLists.txt")
    if cmake_lists == None:
        fail("no CMakeLists.txt found in srcs for %s" % ctx.label)

    image_dir = None
    for f in image_files:
        if f.is_directory:
            image_dir = f
            break
    if image_dir == None:
        fail("image %s does not provide an OCI layout directory" % ctx.attr.image.label)

    build_dir = ctx.actions.declare_directory(ctx.attr.out_dir)

    # Single bash -c script: configure out-of-source, then build the targets.
    configure = ["cmake", "-S", "/src", "-B", "/work/build", "-G", "'Unix Makefiles'"]
    for entry in ctx.attr.cache_entries:
        configure.append("-D" + entry)
    build = ["cmake", "--build", "/work/build"]
    for target in ctx.attr.build_targets:
        build += ["--target", target]
    build += ["--", "-j%d" % ctx.attr.jobs]
    script = " ".join(configure) + " && " + " ".join(build)

    args = ctx.actions.args()
    args.add("--image-layout", image_dir.path)
    args.add("--runtime", "bwrap")
    args.add("--network", "none")
    args.add("--bind-parent", cmake_lists.path + ":/src")
    args.add("--workspace", "/work")
    args.add("--workdir", "/work")
    args.add("--clear-env")
    for entry in _STANDARD_ENV:
        args.add("--env", entry)
    args.add("--export", "/work/build:" + build_dir.path)
    args.add("--")
    args.add_all(["/bin/bash", "--noprofile", "--norc", "-c", script])

    ctx.actions.run(
        executable = ctx.executable._runner,
        arguments = [args],
        inputs = depset(srcs + image_files),
        outputs = [build_dir],
        mnemonic = "CMakeImageBuild",
        progress_message = "Building %s with CMake in image" % ctx.label,
        # bubblewrap needs its own namespaces, which can't nest in the sandbox.
        execution_requirements = {"no-sandbox": "1", "local": "1"},
    )
    return [DefaultInfo(files = depset([build_dir]))]

cmake_build = rule(
    implementation = _cmake_build_impl,
    doc = "Configure and build a CMake project inside an OCI image; the output is the build tree.",
    attrs = {
        "srcs": attr.label_list(
            mandatory = True,
            allow_files = True,
            doc = "Source files of the CMake project, e.g. an upstream `all_srcs` filegroup.",
        ),
        "image": attr.label(
            mandatory = True,
            allow_files = True,
            doc = "OCI image layout target providing cmake, a compiler, and bubblewrap.",
        ),
        "build_targets": attr.string_list(
            default = ["all"],
            doc = "Values passed to `cmake --build --target`.",
        ),
        "cache_entries": attr.string_list(
            default = [],
            doc = "CMake `-D` cache entries, e.g. \"LLAMA_BUILD_TESTS=ON\".",
        ),
        "jobs": attr.int(default = 2, doc = "Parallel build jobs (`-j`)."),
        "out_dir": attr.string(
            default = "build",
            doc = "Name of the declared output directory holding the CMake build tree.",
        ),
        "_runner": attr.label(
            default = "//bazel_port:oci_layout_runner",
            executable = True,
            cfg = "exec",
        ),
    },
)
