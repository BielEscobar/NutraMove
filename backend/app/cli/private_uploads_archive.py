"""Stream a private-upload archive and verify a restore into an empty directory.

Only local files are handled. No database, settings, or network access is needed.
"""

import argparse
import hashlib
import os
import sys
import tarfile
from pathlib import Path, PurePosixPath
from typing import BinaryIO


def create_archive(source: Path, output: BinaryIO) -> None:
    root = source.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Private upload source must be a directory.")
    with tarfile.open(fileobj=output, mode="w|gz") as archive:
        for path in sorted(root.rglob("*")):
            if path.is_symlink() or not (path.is_file() or path.is_dir()):
                raise ValueError("Private upload source contains an unsupported entry.")
            archive.add(path, arcname=path.relative_to(root).as_posix(), recursive=False)


def restore_and_verify(archive_path: Path, destination: Path) -> int:
    root = destination.resolve(strict=True)
    if not root.is_dir() or any(root.iterdir()):
        raise ValueError("Restore destination must be an empty directory.")
    files: dict[Path, str] = {}
    directories: list[tuple[Path, int]] = []
    seen: set[str] = set()
    with tarfile.open(archive_path, mode="r:gz") as archive:
        for member in archive:
            logical_name = member.name.removesuffix("/") if member.isdir() else member.name
            name = PurePosixPath(logical_name)
            if (
                not logical_name
                or logical_name.startswith("/")
                or "\\" in logical_name
                or any(part in {"", ".", ".."} for part in logical_name.split("/"))
                or logical_name in seen
                or not (member.isdir() or member.isfile())
            ):
                raise ValueError("Backup archive contains an unsafe entry.")
            seen.add(logical_name)
            target = root.joinpath(*name.parts).resolve()
            if not target.is_relative_to(root):
                raise ValueError("Backup archive contains an unsafe path.")
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                directories.append((target, member.mode & 0o777))
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            source = archive.extractfile(member)
            if source is None:
                raise ValueError("Backup archive contains an unreadable file.")
            expected = hashlib.sha256()
            with source, target.open("xb") as output:
                while chunk := source.read(1024 * 1024):
                    expected.update(chunk)
                    output.write(chunk)
            os.chmod(target, member.mode & 0o777)
            files[target] = expected.hexdigest()
    for path, mode in sorted(directories, key=lambda item: len(item[0].parts), reverse=True):
        os.chmod(path, mode)
    for path, expected_hash in files.items():
        actual = hashlib.sha256()
        with path.open("rb") as restored:
            while chunk := restored.read(1024 * 1024):
                actual.update(chunk)
        if actual.hexdigest() != expected_hash:
            raise ValueError("Restored upload differs from archive.")
    if len(list(root.rglob("*"))) != len(seen):
        raise ValueError("Restored upload structure differs from archive.")
    return len(files)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=("create", "verify"))
    parser.add_argument("path", type=Path)
    parser.add_argument("destination", nargs="?", type=Path)
    args = parser.parse_args()
    try:
        if args.operation == "create":
            if args.destination is not None:
                parser.error("create accepts only the source directory")
            create_archive(args.path, sys.stdout.buffer)
        else:
            if args.destination is None:
                parser.error("verify requires an empty destination directory")
            count = restore_and_verify(args.path, args.destination)
            print(f"Private uploads restore verified: files={count}")
    except (OSError, ValueError, tarfile.TarError) as exc:
        print(f"Private uploads archive failed: {type(exc).__name__}", file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
