import io
import tarfile
from pathlib import Path

import pytest

from app.cli.private_uploads_archive import create_archive, restore_and_verify


def test_private_upload_archive_roundtrip(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    nested = source / "nested"
    nested.mkdir()
    (source / "front.jpg").write_bytes(b"synthetic front\x00\xff")
    (nested / "side.png").write_bytes(b"synthetic side\x01\xfe")
    archive_path = tmp_path / "private_uploads.tar.gz"
    with archive_path.open("wb") as output:
        create_archive(source, output)
    restored = tmp_path / "restore"
    restored.mkdir()
    assert restore_and_verify(archive_path, restored) == 2
    assert (restored / "front.jpg").read_bytes() == (source / "front.jpg").read_bytes()
    assert (restored / "nested" / "side.png").read_bytes() == (nested / "side.png").read_bytes()


def test_private_upload_restore_rejects_path_traversal(tmp_path: Path) -> None:
    archive_path = tmp_path / "unsafe.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        item = tarfile.TarInfo("../escape.txt")
        item.size = 4
        archive.addfile(item, io.BytesIO(b"nope"))
    restored = tmp_path / "restore"
    restored.mkdir()
    with pytest.raises(ValueError, match="unsafe"):
        restore_and_verify(archive_path, restored)
    assert not (tmp_path / "escape.txt").exists()
