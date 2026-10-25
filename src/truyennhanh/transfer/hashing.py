"""Tính mã băm SHA-256 — docs/02 quyết định D5.

Phụ trách: R3 · Nhiệm vụ: T18 (tuần 2)
Người dùng: R3 (bên gửi, tính trước khi gửi OFFER), R4 (bên nhận, tính lại phần .part khi truyền tiếp).
"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Callable

ProgressFn = Callable[[int, int], None]
"""progress(số byte đã băm, tổng số byte) — để giao diện hiện "Đang tính mã băm... 40%"."""

HASH_READ_SIZE = 1024 * 1024


def sha256_file(path: Path, progress: ProgressFn | None = None,
                cancel: threading.Event | None = None) -> str:
    """SHA-256 của cả file, chuỗi 64 ký tự hex chữ thường.

    Đọc theo khối HASH_READ_SIZE — KHÔNG được đọc cả file vào RAM (file có thể vài GB).
    cancel được đặt thì dừng giữa chừng và ném InterruptedError.
    """
    raise NotImplementedError("T18 · R3")


def sha256_prefix(path: Path, length: int, cancel: threading.Event | None = None):
    """Băm `length` byte đầu của file, trả về ĐỐI TƯỢNG hashlib (chưa gọi hexdigest).

    Bên nhận dùng khi truyền tiếp: băm phần .part đã có, rồi .update() tiếp các khối mới
    (docs/03 mục 4.5).
    """
    raise NotImplementedError("T18 · R3")
