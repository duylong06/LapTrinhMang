"""Tính mã băm SHA-256 — docs/02 quyết định D5.

Phụ trách: R3 · Nhiệm vụ: T18 (tuần 2)
Người dùng: R3 (bên gửi, tính trước khi gửi OFFER), R4 (bên nhận, tính lại phần .part khi truyền tiếp).
"""
from __future__ import annotations

import hashlib
import os
import threading
from pathlib import Path
from typing import Callable

ProgressFn = Callable[[int, int], None]
"""progress(số byte đã băm, tổng số byte) — để giao diện hiện "Đang tính mã băm... 40%"."""

HASH_READ_SIZE = 1024 * 1024


def _check_cancel(cancel: threading.Event | None) -> None:
    if cancel is not None and cancel.is_set():
        raise InterruptedError("Đã hủy khi đang tính mã băm")


def _hash_stream(f, digest, limit: int | None, total: int,
                 progress: ProgressFn | None, cancel: threading.Event | None) -> int:
    """Băm từ vị trí hiện tại của f vào digest; dừng khi hết file hoặc đủ `limit` byte.

    Trả về số byte đã băm. Dùng readinto với một bộ đệm cấp phát một lần, nên file nhiều GB
    cũng chỉ tốn đúng HASH_READ_SIZE byte RAM.
    """
    buffer = bytearray(HASH_READ_SIZE)
    view = memoryview(buffer)
    done = 0
    while limit is None or done < limit:
        _check_cancel(cancel)
        want = HASH_READ_SIZE if limit is None else min(HASH_READ_SIZE, limit - done)
        n = f.readinto(view[:want])
        if not n:
            break
        digest.update(view[:n])
        done += n
        if progress is not None:
            progress(done, total)
    return done


def sha256_file(path: Path, progress: ProgressFn | None = None,
                cancel: threading.Event | None = None) -> str:
    """SHA-256 của cả file, chuỗi 64 ký tự hex chữ thường.

    Đọc theo khối HASH_READ_SIZE — KHÔNG được đọc cả file vào RAM (file có thể vài GB).
    cancel được đặt thì dừng giữa chừng và ném InterruptedError.
    File rỗng thì không gọi progress (tổng bằng 0, tránh chia cho 0 ở bên gọi).
    """
    path = Path(path)
    total = os.stat(path).st_size
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        _hash_stream(f, digest, None, total, progress, cancel)
    return digest.hexdigest()


def sha256_prefix(path: Path, length: int, cancel: threading.Event | None = None):
    """Băm `length` byte đầu của file, trả về ĐỐI TƯỢNG hashlib (chưa gọi hexdigest).

    Bên nhận dùng khi truyền tiếp: băm phần .part đã có, rồi .update() tiếp các khối mới
    (docs/03 mục 4.5).

    Ném ValueError nếu length âm hoặc file ngắn hơn length (khi đó .part không đáng tin,
    bên gọi nên xử lý như .part hỏng). cancel được đặt thì ném InterruptedError.
    """
    if length < 0:
        raise ValueError(f"length không được âm: {length}")
    digest = hashlib.sha256()
    with open(Path(path), "rb") as f:
        done = _hash_stream(f, digest, length, length, None, cancel)
    if done < length:
        raise ValueError(f"File chỉ có {done} byte, ít hơn {length} byte cần băm")
    return digest
