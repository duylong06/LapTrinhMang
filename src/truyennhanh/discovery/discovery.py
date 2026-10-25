"""Dò tìm thiết bị bằng UDP broadcast — docs/03 mục 3.

Phụ trách: R2 · Nhiệm vụ: T06 (thử nghiệm), T15 (cài đặt), T29 (nhiều card mạng)

Một socket UDP duy nhất, bind ("0.0.0.0", DISCOVERY_PORT), bật SO_BROADCAST và SO_REUSEADDR.
Hai luồng nền:
  - Luồng nghe: recvfrom -> decode_packet -> cập nhật PeerTable -> emit PeerFound/PeerLost;
                gặp DISCOVER thì trả lời ANNOUNCE về đúng địa chỉ nguồn.
  - Luồng hẹn giờ: mỗi ANNOUNCE_INTERVAL_S phát ANNOUNCE, rồi gọi PeerTable.expire().

Đọc thêm: Kurose Chương 2 slide 101–104; TCP/IP Sockets in C# mục 2.4 và 4.5.
"""
from __future__ import annotations

from truyennhanh.core.events import Emit
from truyennhanh.discovery.peer_table import PeerTable
from truyennhanh.protocol.constants import DISCOVERY_PORT


class Discovery:
    """instance_id : id của lần chạy này — dùng để bỏ qua gói của chính mình.
    tcp_port       : cổng TCP thật mà máy chủ nhận đang lắng nghe (R4 cung cấp).
    """

    def __init__(self, instance_id: str, device_name: str, tcp_port: int,
                 peers: PeerTable, emit: Emit, port: int = DISCOVERY_PORT) -> None:
        raise NotImplementedError("T15 · R2")

    def start(self) -> None:
        """Mở socket, bật hai luồng nền, gửi một DISCOVER."""
        raise NotImplementedError("T15 · R2")

    def stop(self) -> None:
        """Gửi BYE, dừng hai luồng, đóng socket. Gọi nhiều lần không lỗi."""
        raise NotImplementedError("T15 · R2")

    def discover_now(self) -> None:
        """Gửi DISCOVER ngay (người dùng bấm làm mới)."""
        raise NotImplementedError("T15 · R2")

    def set_tcp_port(self, port: int) -> None:
        """Đổi cổng được phát trong ANNOUNCE (khi máy chủ nhận phải đổi cổng)."""
        raise NotImplementedError("T15 · R2")
