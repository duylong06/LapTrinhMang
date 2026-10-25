"""Kiểu dữ liệu dùng chung giữa các module. Phụ trách: R1 · chốt ở T05.

Đây là hợp đồng: giao diện, dò tìm, gửi, nhận đều dùng các kiểu này.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Direction(str, Enum):
    """Chiều của một lượt truyền, nhìn từ máy này."""

    SEND = "send"
    RECEIVE = "receive"


@dataclass
class Peer:
    """Một máy khác trong mạng.

    id   : id của lần chạy ứng dụng bên đó (docs/03 mục 3.2); máy thêm tay theo IP có id dạng "manual:<ip>"
    ip   : lấy từ địa chỉ nguồn của gói tin, không lấy từ nội dung gói (quyết định D8)
    last_seen : thời điểm nghe thấy gần nhất, theo time.monotonic()
    manual    : True nếu thêm tay theo IP — không bao giờ hết hạn
    """

    id: str
    name: str
    ip: str
    tcp_port: int
    last_seen: float = 0.0
    manual: bool = False
    os: str | None = None
