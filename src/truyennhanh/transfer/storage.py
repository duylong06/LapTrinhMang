"""Lưu trữ phía nhận: file .part, đổi tên, trùng tên, dung lượng — docs/02 mục 6, docs/03 mục 4.5.

Phụ trách: R4 · Nhiệm vụ: T21 (tuần 2), T27, T28 (tuần 3), T37 (tuần 4)

    <download_dir>/
    ├── bao_cao.pdf                ← chỉ file đã xác minh SHA-256 mới nằm ở đây
    └── .truyennhanh/
        └── <sha256>.part          ← đang nhận; tên file chính là khóa truyền tiếp
"""
from __future__ import annotations

import os, re
from pathlib import Path

from truyennhanh.protocol.constants import (
    PART_DIR_NAME,
    PART_MAX_AGE_DAYS,
    PART_SUFFIX,
    SHA256_HEX_LENGTH,
)

_SHA256_PATTERN = re.compile(rf"[0-9a-f]{{{SHA256_HEX_LENGTH}}}")
"""Dùng với fullmatch, không dùng match + "$": "$" khớp được cả trước dấu xuống dòng cuối chuỗi."""

_MAX_UNIQUE_ATTEMPTS = 10_000
"""Số lần thử tên mới tối đa trong unique_path và finalize, để không quay vòng vô hạn."""


def _hide_on_windows(path: Path) -> None:
    """Đặt thuộc tính Ẩn cho thư mục trên Windows.

    Trên Linux và macOS, tên bắt đầu bằng dấu chấm đã là ẩn; Windows thì không. Chỉ là trang trí
    nên mọi lỗi đều bị nuốt: không được để nó làm hỏng việc nhận file.
    """
    if os.name != "nt":
        return
    try:
        import ctypes

        ctypes.windll.kernel32.SetFileAttributesW(str(path), 0x02)  # FILE_ATTRIBUTE_HIDDEN
    except Exception:
        pass


def part_dir(download_dir: Path) -> Path:
    """<download_dir>/.truyennhanh — tạo nếu chưa có. Phải nằm CÙNG ổ đĩa với download_dir.

    Nằm bên trong thư mục nhận nên chắc chắn cùng ổ, và os.replace khi đổi tên mới tức thời (atomic).
    """
    path = Path(download_dir) / PART_DIR_NAME
    created = not path.exists()
    path.mkdir(parents=True, exist_ok=True)
    if created:
        _hide_on_windows(path)
    return path


def part_path(download_dir: Path, sha256: str) -> Path:
    """<download_dir>/.truyennhanh/<sha256>.part, đã resolve và đã kiểm tra nằm trong thư mục nhận.

    sha256 do máy lạ khai và được dùng làm tên file, nên kiểm tra thật chặt trước khi ghép
    đường dẫn: chỉ 64 ký tự hex chữ thường, còn lại ném ValueError ("../../x" không lọt được).
    """
    if not isinstance(sha256, str) or _SHA256_PATTERN.fullmatch(sha256) is None:
        raise ValueError("sha256 phải là đúng 64 ký tự hex viết thường")
    return ensure_inside(download_dir, part_dir(download_dir) / f"{sha256}{PART_SUFFIX}")



def resume_offset(download_dir: Path, sha256: str, size: int) -> int:
    """Vị trí tiếp tục theo bảng ở docs/03 mục 4.5.

    Không có .part -> 0. Nhỏ hơn size -> kích thước .part. Bằng size -> size.
    Lớn hơn size -> xóa .part, trả về 0.
    """
    raise NotImplementedError("T27 · R4")


def unique_path(directory: Path, filename: str) -> Path:
    """Đường dẫn chưa tồn tại: "a.txt", rồi "a (1).txt", "a (2).txt"... (KT-10).
    
    Chỉ tìm tên, KHÔNG tạo file; việc chiếm tên là của finalize. Tên có nhiều đuôi tách ở dấu chấm
    cuối: "a.tar.gz" thành "a.tar (1).gz". Dùng lexists chứ không dùng exists: liên kết tượng trưng
    (symlink) hỏng vẫn tính là đã có, nếu không file sẽ bị ghi xuyên qua nó.
    """
    directory = Path(directory)
    candidate = directory / filename
    if not os.path.lexists(candidate):
        return candidate

    stem, ext = os.path.splitext(filename)
    for number in range(1, _MAX_UNIQUE_ATTEMPTS):
        candidate = directory / f"{stem} ({number}){ext}"
        if not os.path.lexists(candidate):
            return candidate
    raise FileExistsError(f"Không tìm được tên trống cho {filename!r} trong {directory}")



def ensure_inside(directory: Path, candidate: Path) -> Path:
    """Lớp phòng thủ cuối (docs/03 mục 4.9 bước 9)."""
    # Dùng realpath thay cho resolve(strict=True) để tránh lỗi lock file trên Windows
    # và tự động mở rộng các đường dẫn dạng 8.3 (VD: RUNNER~1 -> runneradmin)
    base = os.path.realpath(directory)
    resolved = os.path.realpath(candidate)

    # So sánh không phân biệt hoa thường (do Windows) và thêm dấu phân cách
    # để tránh lỗi thư mục "nhan" và "nhan-evil" bị coi là giống nhau.
    base_norm = os.path.normcase(base)
    resolved_norm = os.path.normcase(resolved)

    # Phải nằm trong base (khác base) và bắt đầu bằng base + dấu gạch chéo
    if resolved_norm == base_norm or not resolved_norm.startswith(base_norm + os.sep):
        raise ValueError(f"đường dẫn nằm ngoài thư mục nhận: {candidate}")

    return Path(resolved)


def finalize(part: Path, download_dir: Path, safe_name: str) -> Path:
    """Đổi .part thành file thật bằng os.replace (tức thời khi cùng ổ đĩa).

    Dùng unique_path và ensure_inside. Trả về đường dẫn cuối cùng.

    Chỉ gọi sau khi SHA-256 đã khớp. Ba việc chống mất dữ liệu:
    - fsync trước khi đổi tên, để mất điện không để lại file đã "xác minh" mà nội dung chưa xuống đĩa.
    - Chiếm tên bằng tạo file rỗng độc quyền (O_EXCL) rồi mới os.replace đè lên chỗ đã chiếm. Nếu chỉ
      dùng unique_path rồi os.replace thì hai lượt cùng tên kết thúc cùng lúc sẽ chọn trùng một tên
      và cái sau ghi đè mất cái trước, vì os.replace ghi đè không báo.
    - Lỗi giữa chừng thì dọn file rỗng đã chiếm, không để lại rác trong thư mục nhận.

    part_dir và tên file được kiểm tra bằng ensure_inside; sai thì ValueError và .part còn nguyên.
    """
    part = ensure_inside(download_dir, Path(part))

    with open(part, "r+b") as f:  # r+b chứ không phải rb: trên Windows fsync cần handle ghi được
        os.fsync(f.fileno())

    for _ in range(_MAX_UNIQUE_ATTEMPTS):
        target = ensure_inside(download_dir, unique_path(download_dir, safe_name))
        
        try:
            fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o666)
        except (FileExistsError, PermissionError):
            # FileExistsError: Luồng khác đã nhanh tay tạo file này trước.
            # PermissionError: Windows báo lỗi quyền truy cập khi 2 luồng tranh nhau tạo file.
            continue
            
        os.close(fd)
        
        try:
            os.replace(part, target)
        except PermissionError:
            # Windows: File rỗng vừa tạo có thể bị lock tạm thời bởi antivirus/luồng khác.
            # Dọn dẹp file rỗng và nhảy sang thử tên tiếp theo.
            try:
                os.unlink(target)
            except OSError:
                pass
            continue
        except OSError:
            # Các lỗi nghiêm trọng khác (VD: ổ đĩa đầy): Dọn rác và văng lỗi ra ngoài.
            try:
                os.unlink(target)
            except OSError:
                pass
            raise
            
        return target
        
    raise FileExistsError(f"Không chiếm được tên trống cho {safe_name!r} trong {download_dir}")



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
