"""Kiểm thử lưu trữ phía nhận (storage.py): ensure_inside (T22) và part_dir, part_path, unique_path, finalize (T21)."""
import os
import threading
from pathlib import Path

import pytest

from truyennhanh.protocol.constants import PART_DIR_NAME
from truyennhanh.transfer import storage
from truyennhanh.transfer.storage import ensure_inside, finalize, part_dir, part_path, unique_path

SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def _make_symlink_or_skip(link: Path, target: Path):
    try:
        link.symlink_to(target, target_is_directory=target.is_dir())
    except OSError:
        pytest.skip("không tạo được symlink (Windows cần Developer Mode hoặc quyền Administrator)")


def _make_part(download_dir: Path, content: bytes, sha: str = SHA) -> Path:
    """Tạo một file .part có nội dung cho trước, đúng chỗ storage quy định."""
    part = part_path(download_dir, sha)
    part.write_bytes(content)
    return part


# --------------------------------------------------------------------------- ensure_inside (T22)

def test_ensure_inside_returns_resolved_path_for_normal_name(tmp_path):
    out = ensure_inside(tmp_path, tmp_path / "a.txt")
    assert out == (tmp_path / "a.txt").resolve()


def test_ensure_inside_rejects_parent_traversal(tmp_path):
    with pytest.raises(ValueError):
        ensure_inside(tmp_path, tmp_path / ".." / "x")


def test_ensure_inside_rejects_the_download_dir_itself(tmp_path):
    """Ghi file 'lên' chính thư mục nhận là lỗi nặng, phải bị chặn."""
    with pytest.raises(ValueError):
        ensure_inside(tmp_path, tmp_path)


def test_ensure_inside_rejects_sibling_dir_with_same_prefix(tmp_path):
    """/nhan-evil không nằm trong /nhan dù chuỗi bắt đầu giống nhau (bẫy của startswith)."""
    nhan = tmp_path / "nhan"
    nhan.mkdir()
    (tmp_path / "nhan-evil").mkdir()
    with pytest.raises(ValueError):
        ensure_inside(nhan, nhan / ".." / "nhan-evil" / "x")


def test_ensure_inside_rejects_symlink_pointing_outside(tmp_path):
    nhan = tmp_path / "nhan"
    ngoai = tmp_path / "ngoai"
    nhan.mkdir()
    ngoai.mkdir()
    _make_symlink_or_skip(nhan / "x", ngoai)
    with pytest.raises(ValueError):
        ensure_inside(nhan, nhan / "x" / "file.txt")


def test_ensure_inside_accepts_download_dir_that_is_a_symlink(tmp_path):
    that = tmp_path / "that"
    that.mkdir()
    link = tmp_path / "link"
    _make_symlink_or_skip(link, that)
    assert ensure_inside(link, link / "a.txt") == (that / "a.txt").resolve()


# --------------------------------------------------------------------------- part_dir, part_path

def test_part_dir_is_created_inside_the_download_dir(tmp_path):
    folder = part_dir(tmp_path)
    assert folder.is_dir()
    assert folder.parent == tmp_path
    assert folder.name == PART_DIR_NAME


def test_part_dir_can_be_called_twice(tmp_path):
    assert part_dir(tmp_path) == part_dir(tmp_path)


def test_part_path_is_named_after_the_sha256(tmp_path):
    path = part_path(tmp_path, SHA)
    assert path.name == f"{SHA}.part"
    assert path.parent == (tmp_path / PART_DIR_NAME).resolve()


@pytest.mark.parametrize(
    "bad_sha",
    [
        "../../etc/passwd",
        SHA.upper(),
        SHA[:63],
        SHA + "0",
        SHA + "\n",
        "g" * 64,
        "../" + SHA[3:],
        "",
    ],
    ids=["path", "uppercase", "too-short", "too-long", "trailing-newline", "not-hex", "path-with-right-length", "empty"],
)
def test_part_path_rejects_anything_but_64_lowercase_hex(tmp_path, bad_sha):
    """sha256 do máy lạ khai rồi được dùng làm tên file: không được để lọt ký tự đường dẫn."""
    with pytest.raises(ValueError):
        part_path(tmp_path, bad_sha)


def test_part_path_rejects_part_dir_that_is_a_symlink_to_outside(tmp_path):
    nhan = tmp_path / "nhan"
    ngoai = tmp_path / "ngoai"
    nhan.mkdir()
    ngoai.mkdir()
    _make_symlink_or_skip(nhan / PART_DIR_NAME, ngoai)
    with pytest.raises(ValueError):
        part_path(nhan, SHA)


# --------------------------------------------------------------------------- unique_path (KT-10)

def test_unique_path_returns_the_name_itself_when_free(tmp_path):
    assert unique_path(tmp_path, "a.txt") == tmp_path / "a.txt"


def test_unique_path_adds_number_when_name_is_taken(tmp_path):
    (tmp_path / "a.txt").write_text("x")
    assert unique_path(tmp_path, "a.txt") == tmp_path / "a (1).txt"


def test_unique_path_skips_numbers_that_are_taken(tmp_path):
    """KT-10: a.txt và a (1).txt đã có thì ra a (2).txt."""
    (tmp_path / "a.txt").write_text("x")
    (tmp_path / "a (1).txt").write_text("x")
    assert unique_path(tmp_path, "a.txt") == tmp_path / "a (2).txt"


def test_unique_path_handles_name_without_extension(tmp_path):
    (tmp_path / "Makefile").write_text("x")
    assert unique_path(tmp_path, "Makefile") == tmp_path / "Makefile (1)"


def test_unique_path_splits_extension_at_the_last_dot(tmp_path):
    (tmp_path / "a.tar.gz").write_text("x")
    assert unique_path(tmp_path, "a.tar.gz") == tmp_path / "a.tar (1).gz"


def test_unique_path_does_not_create_anything(tmp_path):
    unique_path(tmp_path, "a.txt")
    assert list(tmp_path.iterdir()) == []


def test_unique_path_treats_a_dangling_symlink_as_taken(tmp_path):
    """Symlink hỏng: Path.exists() báo False nhưng ghi vào nó vẫn ghi xuyên ra chỗ nó trỏ tới."""
    _make_symlink_or_skip(tmp_path / "a.txt", tmp_path / "khong-ton-tai")
    assert unique_path(tmp_path, "a.txt") == tmp_path / "a (1).txt"


# --------------------------------------------------------------------------- finalize

def test_finalize_moves_the_part_file_to_the_download_dir(tmp_path):
    part = _make_part(tmp_path, b"noi dung")
    saved = finalize(part, tmp_path, "bao_cao.pdf")
    assert saved == (tmp_path / "bao_cao.pdf").resolve()
    assert saved.read_bytes() == b"noi dung"
    assert not part.exists()


def test_finalize_leaves_only_the_final_file_in_the_download_dir(tmp_path):
    finalize(_make_part(tmp_path, b"x"), tmp_path, "a.txt")
    assert sorted(p.name for p in tmp_path.iterdir()) == [PART_DIR_NAME, "a.txt"]
    assert list((tmp_path / PART_DIR_NAME).iterdir()) == []


def test_finalize_numbers_a_name_that_is_already_taken(tmp_path):
    (tmp_path / "a.txt").write_bytes(b"cu")
    saved = finalize(_make_part(tmp_path, b"moi"), tmp_path, "a.txt")
    assert saved.name == "a (1).txt"
    assert (tmp_path / "a.txt").read_bytes() == b"cu"  # file có sẵn không bị đè
    assert saved.read_bytes() == b"moi"


def test_finalize_numbers_consecutive_duplicates(tmp_path):
    names = []
    for i in range(3):
        sha = f"{i:064x}"
        names.append(finalize(_make_part(tmp_path, b"x", sha), tmp_path, "a.txt").name)
    assert names == ["a.txt", "a (1).txt", "a (2).txt"]


def test_finalize_never_overwrites_when_many_threads_use_the_same_name(tmp_path):
    """Nhiều lượt cùng tên kết thúc cùng lúc: mỗi lượt phải được một tên riêng, không file nào bị đè."""
    count = 12
    parts = [_make_part(tmp_path, f"noi dung {i}".encode(), f"{i:064x}") for i in range(count)]
    barrier = threading.Barrier(count)
    results = []
    errors = []

    def run(part):
        barrier.wait()
        try:
            results.append(finalize(part, tmp_path, "trung.txt"))
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=run, args=(p,)) for p in parts]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    assert len(set(results)) == count
    contents = sorted(p.read_bytes() for p in results)
    assert contents == sorted(f"noi dung {i}".encode() for i in range(count))


def test_finalize_does_not_follow_a_symlink_with_the_target_name(tmp_path):
    nhan = tmp_path / "nhan"
    nhan.mkdir()
    ngoai = tmp_path / "ngoai.txt"
    ngoai.write_bytes(b"cua nguoi khac")
    _make_symlink_or_skip(nhan / "a.txt", ngoai)
    saved = finalize(_make_part(nhan, b"moi"), nhan, "a.txt")
    assert saved.name == "a (1).txt"
    assert ngoai.read_bytes() == b"cua nguoi khac"


def test_finalize_rejects_a_name_that_escapes_the_download_dir(tmp_path):
    nhan = tmp_path / "nhan"
    nhan.mkdir()
    part = _make_part(nhan, b"x")
    with pytest.raises(ValueError):
        finalize(part, nhan, "../thoat-ra.txt")
    assert part.exists()  # .part còn nguyên để truyền tiếp
    assert not (tmp_path / "thoat-ra.txt").exists()


def test_finalize_of_a_missing_part_leaves_no_file_behind(tmp_path):
    missing = part_path(tmp_path, SHA)
    with pytest.raises(FileNotFoundError):
        finalize(missing, tmp_path, "a.txt")
    assert sorted(p.name for p in tmp_path.iterdir()) == [PART_DIR_NAME]


def test_finalize_cleans_up_the_reserved_name_when_replace_fails(tmp_path, monkeypatch):
    part = _make_part(tmp_path, b"x")

    def broken_replace(src, dst):
        raise OSError("ổ đĩa lỗi giả")

    monkeypatch.setattr(storage.os, "replace", broken_replace)
    with pytest.raises(OSError):
        finalize(part, tmp_path, "a.txt")
    assert not (tmp_path / "a.txt").exists()  # file rỗng đã chiếm tên phải được dọn
    assert part.exists()