#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Stage an install and compile a minimal external consumer."""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import sys
import tempfile


def find_single_path(root: pathlib.Path, pattern: str) -> pathlib.Path:
    matches = sorted(path for path in root.rglob("*")
                     if path.as_posix().endswith("/" + pattern))
    if len(matches) != 1:
        print(
            f"FAIL: expected exactly one match for {pattern!r} under {root}, "
            f"found {len(matches)}",
            file=sys.stderr,
        )
        for match in matches:
            print(f"  {match}", file=sys.stderr)
        raise SystemExit(1)
    return matches[0]


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: run_install_smoke.py <source_root> <build_root>",
              file=sys.stderr)
        return 2

    source_root = pathlib.Path(sys.argv[1]).resolve()
    build_root = pathlib.Path(sys.argv[2]).resolve()
    compiler = os.environ.get("CC", "cc")

    meson = shutil.which("meson")
    if meson is None:
        print("FAIL: meson not found in PATH", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory(prefix="arena-install-smoke-") as temp_dir:
        temp_path = pathlib.Path(temp_dir)
        destdir = temp_path / "destdir"
        exe_path = temp_path / "install_smoke_consumer"
        consumer = source_root / "tests" / "install_smoke_consumer.c"

        subprocess.run(
            [meson, "install", "-C", str(build_root), "--destdir",
             str(destdir)],
            check=True,
        )

        header = find_single_path(destdir, "arena/arena.h")
        include_root = header.parent.parent
        lib_path = find_single_path(destdir, "libarena.a")

        if not (header.parent / "arena_cfg.h").is_file():
            print("FAIL: arena_cfg.h not installed under arena/",
                  file=sys.stderr)
            return 1

        # Subdirectory path, root forwarding header, and the pkg-config
        # include path (which points into arena/).
        variants = (
            ("subdir", include_root, []),
            ("root-forwarder", include_root, ["-DSMOKE_ROOT_INCLUDE"]),
            ("pkg-config", header.parent, ["-DSMOKE_ROOT_INCLUDE"]),
        )
        for label, include_dir, defines in variants:
            subprocess.run(
                [
                    compiler,
                    "-std=c11",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    *defines,
                    str(consumer),
                    "-I",
                    str(include_dir),
                    str(lib_path),
                    "-o",
                    str(exe_path),
                ],
                check=True,
            )
            subprocess.run([str(exe_path)], check=True)
            print(f"PASS: arena_install_smoke ({label})")

    print("PASS: arena_install_smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
