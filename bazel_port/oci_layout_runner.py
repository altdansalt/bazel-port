#!/usr/bin/env python3
"""Run a command from an OCI image layout."""

from __future__ import annotations

import argparse
import gzip
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tarfile
import tempfile


def _read_blob(layout: pathlib.Path, digest: str) -> bytes:
    algorithm, value = digest.split(":", 1)
    if algorithm != "sha256":
        raise ValueError(f"unsupported digest algorithm: {algorithm}")
    return (layout / "blobs" / algorithm / value).read_bytes()


def _load_image(layout: pathlib.Path) -> tuple[dict, list[bytes]]:
    index = json.loads((layout / "index.json").read_text())
    manifest = json.loads(_read_blob(layout, index["manifests"][0]["digest"]))
    config = json.loads(_read_blob(layout, manifest["config"]["digest"]))
    layers = [_read_blob(layout, layer["digest"]) for layer in manifest["layers"]]
    return config, layers


def _extract_layer(layer: bytes, rootfs: pathlib.Path) -> None:
    with tarfile.open(fileobj=gzip.GzipFile(fileobj=BytesReader(layer)), mode="r|") as tar:
        for member in tar:
            if member.ischr() or member.isblk() or member.isfifo():
                continue
            tar.extract(member, rootfs)


def _find_runfile(path: str) -> pathlib.Path:
    candidate = pathlib.Path(path)
    if candidate.exists():
        return candidate

    manifest = os.environ.get("RUNFILES_MANIFEST_FILE")
    if manifest:
        for line in pathlib.Path(manifest).read_text().splitlines():
            logical, _, physical = line.partition(" ")
            if logical.endswith(path) and physical:
                return pathlib.Path(physical)

    runfile_roots: list[pathlib.Path] = []
    if os.environ.get("RUNFILES_DIR"):
        runfile_roots.append(pathlib.Path(os.environ["RUNFILES_DIR"]))
    for parent in pathlib.Path(__file__).resolve().parents:
        if parent.name.endswith(".runfiles") or (parent / "MANIFEST").exists():
            runfile_roots.append(parent)

    suffix = pathlib.PurePosixPath(path)
    for root in runfile_roots:
        matches = sorted(root.glob(f"**/{suffix}"))
        if matches:
            return matches[0]
    raise FileNotFoundError(path)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image-layout", required=True, help="OCI image layout directory")
    parser.add_argument(
        "--runtime",
        choices=["proot", "bwrap"],
        default="proot",
        help="rootfs runner to use (default: proot)",
    )
    parser.add_argument("--proot", default=None, help="PRoot binary; required for --runtime=proot")
    parser.add_argument(
        "--network",
        choices=["none", "host"],
        default="host",
        help="network mode for runtimes that support it (default: host)",
    )
    parser.add_argument(
        "--bind",
        action="append",
        default=[],
        metavar="RUNFILE_OR_PATH:GUEST_PATH",
        help="bind a host path or runfile into the rootfs; repeatable",
    )
    parser.add_argument(
        "--bind-parent",
        action="append",
        default=[],
        metavar="RUNFILE_OR_PATH:GUEST_PATH",
        help="bind the parent directory of a host path or runfile into the rootfs; repeatable",
    )
    parser.add_argument(
        "--workspace",
        default=None,
        help="guest path for a new writable temporary directory",
    )
    parser.add_argument("--clear-env", action="store_true", help="do not inherit the host environment")
    parser.add_argument(
        "--env",
        action="append",
        default=[],
        metavar="NAME=VALUE",
        help="set an environment variable for the command; repeatable",
    )
    parser.add_argument("--workdir", default=None, help="working directory inside the rootfs")
    parser.add_argument(
        "--export",
        action="append",
        default=[],
        metavar="GUEST_PATH:DEST_PATH",
        help="after a successful command, copy a guest path under --workspace to a host "
        "destination; repeatable",
    )
    parser.add_argument("command", nargs=argparse.REMAINDER, help="command override")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    layout = _find_runfile(args.image_layout)
    config, layers = _load_image(layout)

    image_config = config.get("config", {})
    command = args.command
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        command = image_config.get("Entrypoint", []) + image_config.get("Cmd", [])
    if not command:
        raise SystemExit("image has no command; pass one after --")

    with tempfile.TemporaryDirectory(prefix="bazel-port-rootfs-") as temp_dir:
        rootfs = pathlib.Path(temp_dir) / "rootfs"
        rootfs.mkdir()
        for layer in layers:
            _extract_layer(layer, rootfs)

        workspace = None
        if args.workspace:
            workspace = pathlib.Path(temp_dir) / "workspace"
            workspace.mkdir()

        binds = _resolve_binds(args)
        workdir = args.workdir or image_config.get("WorkingDir")
        env = {} if args.clear_env else os.environ.copy()
        for item in image_config.get("Env", []):
            key, _, value = item.partition("=")
            if key:
                env[key] = value
        for item in args.env:
            key, _, value = item.partition("=")
            if not key or not _:
                raise SystemExit(f"invalid --env value: {item!r}")
            env[key] = value

        if args.runtime == "proot":
            runtime_args = _proot_args(args, rootfs, temp_dir, workspace, binds, workdir)
        else:
            runtime_args = _bwrap_args(args, rootfs, workspace, binds, workdir)

        result = subprocess.run(runtime_args + command, env=env, check=False)
        if result.returncode == 0 and args.export:
            _export_paths(args, workspace)
        return result.returncode


def _export_paths(args: argparse.Namespace, workspace: pathlib.Path | None) -> None:
    if not (workspace and args.workspace):
        raise SystemExit("--export requires --workspace")
    for spec in args.export:
        guest, separator, dest = spec.partition(":")
        if not separator or not guest or not dest:
            raise SystemExit(f"invalid --export value: {spec!r}")
        relative = os.path.relpath(guest, args.workspace)
        if relative == os.pardir or relative.startswith(os.pardir + os.sep):
            raise SystemExit(f"--export path must be under --workspace: {guest!r}")
        source = workspace if relative == os.curdir else workspace / relative
        if not source.exists():
            raise SystemExit(f"export source missing after command: {guest!r}")
        destination = pathlib.Path(dest)
        if source.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source, destination, dirs_exist_ok=True, symlinks=True)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)


def _resolve_bind(value: str, option: str) -> tuple[pathlib.Path, str]:
    host, separator, guest = value.partition(":")
    if not separator or not host or not guest:
        raise SystemExit(f"invalid {option} value: {value!r}")
    return _find_runfile(host), guest


def _resolve_binds(args: argparse.Namespace) -> list[tuple[pathlib.Path, str]]:
    binds = [_resolve_bind(bind, "--bind") for bind in args.bind]
    for bind in args.bind_parent:
        host, guest = _resolve_bind(bind, "--bind-parent")
        binds.append((host.parent, guest))
    return binds


def _proot_args(
    args: argparse.Namespace,
    rootfs: pathlib.Path,
    temp_dir: str,
    workspace: pathlib.Path | None,
    binds: list[tuple[pathlib.Path, str]],
    workdir: str | None,
) -> list[str]:
    if args.proot is None:
        raise SystemExit("--proot is required for --runtime=proot")
    runnable_proot = pathlib.Path(temp_dir) / "proot"
    shutil.copy2(_find_runfile(args.proot), runnable_proot)
    runnable_proot.chmod(0o755)

    proot_args = [
        str(runnable_proot),
        "-R",
        str(rootfs),
        "-b",
        "/dev",
        "-b",
        "/proc",
        "-b",
        "/sys",
    ]
    if workspace and args.workspace:
        proot_args.extend(["-b", f"{workspace}:{args.workspace}"])
    for host, guest in binds:
        proot_args.extend(["-b", f"{host}:{guest}"])
    if workdir:
        proot_args.extend(["-w", workdir])
    return proot_args


def _bwrap_args(
    args: argparse.Namespace,
    rootfs: pathlib.Path,
    workspace: pathlib.Path | None,
    binds: list[tuple[pathlib.Path, str]],
    workdir: str | None,
) -> list[str]:
    bwrap = rootfs / "usr/bin/bwrap"
    if not bwrap.exists():
        raise SystemExit("image does not contain /usr/bin/bwrap")

    bwrap_args = [
        str(bwrap),
        "--die-with-parent",
        "--unshare-pid",
        "--ro-bind",
        str(rootfs),
        "/",
        "--dev",
        "/dev",
        "--proc",
        "/proc",
        "--tmpfs",
        "/tmp",
    ]
    if args.network == "none":
        bwrap_args.append("--unshare-net")
    if workspace and args.workspace:
        _ensure_guest_path(rootfs, args.workspace, is_dir=True)
        bwrap_args.extend(["--bind", str(workspace), args.workspace])
    for host, guest in binds:
        _ensure_guest_path(rootfs, guest, is_dir=host.is_dir())
        bwrap_args.extend(["--ro-bind", str(host), guest])
    if workdir:
        _ensure_guest_path(rootfs, workdir, is_dir=True)
        bwrap_args.extend(["--chdir", workdir])
    return bwrap_args


def _ensure_guest_path(rootfs: pathlib.Path, guest: str, *, is_dir: bool) -> None:
    relative = guest.lstrip("/")
    if not relative:
        return
    path = rootfs / relative
    if is_dir:
        path.mkdir(parents=True, exist_ok=True)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(exist_ok=True)


class BytesReader:
    def __init__(self, data: bytes) -> None:
        self._data = memoryview(data)
        self._offset = 0

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            size = len(self._data) - self._offset
        start = self._offset
        end = min(start + size, len(self._data))
        self._offset = end
        return self._data[start:end].tobytes()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
