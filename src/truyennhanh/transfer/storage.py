"""Lưu trữ phía nhận: file .part, đổi tên, trùng tên, dung lượng — docs/02 mục 6, docs/03 mục 4.5.

Phụ trách: R4 · Nhiệm vụ: T21 (tuần 2), T27, T28 (tuần 3), T37 (tuần 4)

    <download_dir>/
    ├── bao_cao.pdf                ← chỉ file đã xác minh SHA-256 mới nằm ở đây
    └── .truyennhanh/
        └── <sha256>.part          ← đang nhận; tên file chính là khóa truyền tiếp
"""
from __future__ import annotations

from pathlib import Path

from truyennhanh.protocol.constants import PART_MAX_AGE_DAYS


def part_dir(download_dir: Path) -> Path:
    """<download_dir>/.truyennhanh — tạo nếu chưa có. Phải nằm CÙNG ổ đĩa với download_dir."""
    raise NotImplementedError("T21 · R4")


def part_path(download_dir: Path, sha256: str) -> Path:
    raise NotImplementedError("T21 · R4")


def resume_offset(download_dir: Path, sha256: str, size: int) -> int:
    """Vị trí tiếp tục theo bảng ở docs/03 mục 4.5.

    Không có .part -> 0. Nhỏ hơn size -> kích thước .part. Bằng size -> size.
    Lớn hơn size -> xóa .part, trả về 0.
    """
    raise NotImplementedError("T27 · R4")


def unique_path(directory: Path, filename: str) -> Path:
    """Đường dẫn chưa tồn tại: "a.txt", rồi "a (1).txt", "a (2).txt"... (KT-10)."""
    raise NotImplementedError("T21 · R4")


def ensure_inside(directory: Path, candidate: Path) -> Path:
    """Lớp phòng thủ cuối (docs/03 mục 4.9 bước 9).

    Trả về candidate đã resolve nếu nó nằm TRONG directory đã resolve; ngược lại ném ValueError.
    """
    raise NotImplementedError("T22 · R4")


def finalize(part: Path, download_dir: Path, safe_name: str) -> Path:
    """Đổi .part thành file thật bằng os.replace (tức thời khi cùng ổ đĩa).

    Dùng unique_path và ensure_inside. Trả về đường dẫn cuối cùng.
    """
    raise NotImplementedError("T21 · R4")


def has_free_space(download_dir: Path, needed_bytes: int) -> bool:
    """Dùng shutil.disk_usage. Chừa thêm một khoảng an toàn nhỏ."""
    raise NotImplementedError("T28 · R4")


def cleanup_old_parts(download_dir: Path, max_age_days: int = PART_MAX_AGE_DAYS) -> int:
    """Xóa các .part không được sửa quá max_age_days ngày. Trả về số file đã xóa."""
    raise NotImplementedError("T37 · R4")


class FileLocks:
    """Bảo đảm không có hai lượt cùng sha256 ghi vào một .part (docs/03 mục 4.9 bước 8)."""

    def __init__(self) -> None:
        raise NotImplementedError("T28 · R4")

    def acquire(self, sha256: str) -> bool:
        """Trả về False ngay nếu sha256 đang bận (KHÔNG chờ) — bên nhận trả REJECT busy."""
        raise NotImplementedError("T28 · R4")

    def release(self, sha256: str) -> None:
        raise NotImplementedError("T28 · R4")
