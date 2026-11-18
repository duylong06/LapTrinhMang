"""Lưu trữ phía nhận: file .part, đổi tên, trùng tên, dung lượng — docs/02 mục 6, docs/03 mục 4.5.

Phụ trách: R4 · Nhiệm vụ: T21 (tuần 2), T27, T28 (tuần 3), T37 (tuần 4)

    <download_dir>/
    ├── bao_cao.pdf                ← chỉ file đã xác minh SHA-256 mới nằm ở đây
    └── .truyennhanh/
        └── <sha256>.part          ← đang nhận; tên file chính là khóa truyền tiếp
"""
from __future__ import annotations

import os, re
import shutil
import threading
import time
from pathlib import Path

from truyennhanh.protocol.constants import (
    PART_DIR_NAME,
    PART_MAX_AGE_DAYS,
    PART_SUFFIX,
    SHA256_HEX_LENGTH,
)

FREE_SPACE_MARGIN_BYTES = 16 * 1024 * 1024
"""Chừa thêm 16 MiB ngoài phần cần cho file (T28).

Nhận file tới khi ổ đĩa còn đúng 0 byte sẽ làm hệ điều hành và các chương trình
khác hỏng việc, nên luôn để lại một khoảng thở.
"""

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

    Lấy kích thước .part làm vị trí tiếp tục là đúng vì dữ liệu được ghi tuần tự
    từ đầu tới cuối: mọi byte đang có đều là byte đã nhận đúng. Đuôi hỏng vì mất
    điện giữa lúc ghi sẽ bị bước so SHA-256 cuối cùng phát hiện.

    sha256 được part_path kiểm tra; sai định dạng thì ValueError bay ra ngoài,
    không âm thầm nhận lại từ đầu, vì đó là lỗi lập trình chứ không phải .part hỏng.
    """
    path = part_path(download_dir, sha256)
    try:
        have = path.stat().st_size
    except FileNotFoundError:
        return 0
    except OSError:
        # Không đọc nổi (quyền, ổ đĩa lỗi): coi như chưa có gì, nhận lại từ đầu.
        return 0

    if have > size:
        # Dài hơn cả file được khai thì chắc chắn hỏng — xóa để nhận lại.
        try:
            path.unlink()
        except OSError:
            pass
        return 0
    return have


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
    base = Path(os.path.realpath(directory))
    resolved_candidate = Path(os.path.realpath(candidate))

    base_norm = os.path.normcase(str(base))
    resolved_norm = os.path.normcase(str(resolved_candidate))

    if resolved_norm == base_norm or not resolved_norm.startswith(base_norm + os.sep):
        # Phòng trường hợp Windows trả về tên rút gọn 8.3 khi file đang bị lock (CI race condition)
        resolved_parent = Path(os.path.realpath(candidate.parent))
        fallback_candidate = resolved_parent / candidate.name
        fallback_norm = os.path.normcase(str(fallback_candidate))

        # Nếu thư mục cha nằm trong base, và file này không phải symlink trỏ ra ngoài
        if fallback_norm.startswith(base_norm + os.sep) and not candidate.is_symlink():
            return fallback_candidate

        raise ValueError(f"đường dẫn nằm ngoài thư mục nhận: {candidate}")

    return resolved_candidate


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
    """Dùng shutil.disk_usage. Chừa thêm một khoảng an toàn nhỏ.

    Khoảng an toàn cần vì ổ đĩa đầy sát nút làm hệ điều hành và các chương trình
    khác hỏng việc, và vì giữa lúc hỏi và lúc ghi xong còn có chương trình khác
    cũng đang ghi.

    Không hỏi được dung lượng thì trả về True: thà thử ghi rồi báo lỗi thật, còn
    hơn từ chối một file hoàn toàn có chỗ chứa.
    """
    try:
        free = shutil.disk_usage(Path(download_dir)).free
    except OSError:
        return True
    return free >= needed_bytes + FREE_SPACE_MARGIN_BYTES


def cleanup_old_parts(download_dir: Path, max_age_days: int = PART_MAX_AGE_DAYS) -> int:
    """Xóa các .part không được sửa quá max_age_days ngày. Trả về số file đã xóa.

    Chỉ đụng tới file .part trong .truyennhanh, không bao giờ đụng file thật
    trong thư mục nhận — người dùng có thể để đó một file cũ nhiều năm.

    Không tạo thư mục .truyennhanh nếu chưa có: dọn dẹp mà lại sinh ra rác mới
    thì vô lý.
    """
    folder = Path(download_dir) / PART_DIR_NAME
    if not folder.is_dir():
        return 0

    deadline = time.time() - max_age_days * 86400
    removed = 0
    for part in folder.glob(f"*{PART_SUFFIX}"):
        try:
            if part.stat().st_mtime < deadline:
                part.unlink()
                removed += 1
        except OSError:
            # Đang bị một lượt khác giữ, hoặc vừa bị xóa: bỏ qua, lần sau dọn tiếp.
            continue
    return removed


class FileLocks:
    """Bảo đảm không có hai lượt cùng sha256 ghi vào một .part (docs/03 mục 4.9 bước 8).

    Khóa theo mã băm chứ không theo tên file, vì .part được đặt tên theo mã băm:
    hai máy gửi cùng một file với hai tên khác nhau vẫn ghi vào đúng một .part.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._busy: set[str] = set()

    def acquire(self, sha256: str) -> bool:
        """Trả về False ngay nếu sha256 đang bận (KHÔNG chờ) — bên nhận trả REJECT busy."""
        with self._lock:
            if sha256 in self._busy:
                return False
            self._busy.add(sha256)
            return True

    def release(self, sha256: str) -> None:
        with self._lock:
            # discard chứ không remove: nhả một khóa chưa giữ không được ném lỗi,
            # vì khối finally của bên nhận gọi hàm này trên mọi đường thoát.
            self._busy.discard(sha256)
