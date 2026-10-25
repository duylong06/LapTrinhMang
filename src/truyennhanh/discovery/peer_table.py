"""Bảng các máy đang thấy, có hết hạn — docs/03 mục 3.3.

Phụ trách: R2 · Nhiệm vụ: T16 (tuần 2), T29 (máy thêm tay, tuần 3)

Bảng được đọc và ghi từ nhiều luồng (luồng nghe UDP, luồng hẹn giờ, luồng giao diện),
nên mọi thao tác phải giữ một threading.Lock.

Nhận hàm clock qua tham số để kiểm thử dùng đồng hồ giả, không phải sleep thật (KT-08).
"""
from __future__ import annotations

import time
from typing import Callable

from truyennhanh.core.models import Peer
from truyennhanh.protocol.constants import PEER_TIMEOUT_S


class PeerTable:
    """Khóa của mỗi máy là Peer.id, không phải IP."""

    def __init__(self, timeout_s: float = PEER_TIMEOUT_S,
                 clock: Callable[[], float] = time.monotonic) -> None:
        raise NotImplementedError("T16 · R2")

    def upsert(self, peer_id: str, name: str, ip: str, tcp_port: int,
               os: str | None = None) -> bool:
        """Thêm hoặc cập nhật máy, ghi last_seen = clock(). Trả về True nếu là máy mới."""
        raise NotImplementedError("T16 · R2")

    def add_manual(self, ip: str, tcp_port: int) -> Peer:
        """Thêm máy theo IP, manual=True, id = "manual:<ip>". Không bao giờ hết hạn."""
        raise NotImplementedError("T29 · R2")

    def remove(self, peer_id: str) -> Peer | None:
        """Xóa ngay (khi nhận BYE). Trả về máy vừa xóa, hoặc None nếu không có."""
        raise NotImplementedError("T16 · R2")

    def expire(self) -> list[Peer]:
        """Xóa và trả về các máy không phải manual có clock() - last_seen > timeout_s."""
        raise NotImplementedError("T16 · R2")

    def get(self, peer_id: str) -> Peer | None:
        raise NotImplementedError("T16 · R2")

    def snapshot(self) -> list[Peer]:
        """Bản sao danh sách, sắp theo tên. Người gọi sửa bản sao không ảnh hưởng bảng."""
        raise NotImplementedError("T16 · R2")
