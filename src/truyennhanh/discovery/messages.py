"""Mã hóa và giải mã gói dò tìm UDP — docs/03 mục 3.2 và 3.4.

Phụ trách: R2 · Nhiệm vụ: T15 (tuần 2)
"""
from __future__ import annotations

from dataclasses import dataclass

from truyennhanh.protocol.constants import DiscoveryType


@dataclass(frozen=True)
class DiscoveryPacket:
    """Một gói dò tìm đã giải mã. KHÔNG có trường IP: IP lấy từ recvfrom (quyết định D8).

    tcp_port là None với gói BYE.
    """

    type: DiscoveryType
    id: str
    name: str
    tcp_port: int | None = None
    os: str | None = None


def encode_packet(packet: DiscoveryPacket) -> bytes:
    """Thành JSON gọn, UTF-8, có proto và v. Kết quả không được vượt MAX_DATAGRAM_BYTES."""
    raise NotImplementedError("T15 · R2")


def decode_packet(data: bytes) -> DiscoveryPacket | None:
    """Giải mã một gói nhận được. Trả về None cho MỌI gói phải bỏ qua theo mục 3.4.

    Không bao giờ ném ngoại lệ: mạng LAN là môi trường dùng chung, ai cũng gửi được
    byte bất kỳ tới cổng 50505. Tên hiển thị phải được bỏ ký tự điều khiển và cắt
    còn MAX_NAME_CHARS ký tự.
    """
    raise NotImplementedError("T15 · R2")
