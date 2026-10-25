"""Lõi ứng dụng: TruyenNhanhService — docs/02 mục 3 và 4.

Phụ trách: R1 · Nhiệm vụ: T05 (chốt API), T14 (bản đầu), T25 (ghép thật), T33 (đồng thời)

Lớp DUY NHẤT mà giao diện (gui, cli) được phép gọi. Hai luật:
  1. Mọi hàm trả về NGAY, không bao giờ chờ mạng. Việc mạng chạy ở luồng riêng.
  2. Kết quả và trạng thái báo ngược lên bằng sự kiện trong self.events.

gui/fake_service.py có cùng API này để R5 làm giao diện trước khi lõi xong.
"""
from __future__ import annotations

import queue
from pathlib import Path

from truyennhanh.config import Config
from truyennhanh.core.events import Event
from truyennhanh.core.models import Peer
from truyennhanh.protocol.constants import TRANSFER_PORT_DEFAULT


class TruyenNhanhService:
    """Điều phối dò tìm, máy chủ nhận và các lượt gửi.

    Thuộc tính:
        events : queue.Queue[Event] — giao diện lấy sự kiện từ đây trên luồng chính.
    """

    events: "queue.Queue[Event]"

    def __init__(self, config: Config | None = None) -> None:
        """Tạo id lần chạy (uuid4), hàng đợi sự kiện; CHƯA mở socket nào."""
        raise NotImplementedError("T14 · R1")

    def start(self) -> None:
        """Bật máy chủ nhận (lấy cổng thật), rồi bật dò tìm với cổng đó."""
        raise NotImplementedError("T14, T25 · R1")

    def stop(self) -> None:
        """Gửi BYE, hủy các lượt đang chạy với lý do shutting_down, dừng mọi luồng, giữ .part."""
        raise NotImplementedError("T14, T33 · R1")

    def list_peers(self) -> list[Peer]:
        """Ảnh chụp danh sách máy đang thấy."""
        raise NotImplementedError("T25 · R1")

    def add_manual_peer(self, ip: str, port: int = TRANSFER_PORT_DEFAULT) -> Peer:
        """Thêm máy theo IP (FR-02). Máy thêm tay không bị hết hạn."""
        raise NotImplementedError("T25, T29 · R1, R2")

    def send_file(self, peer_id: str, path: str | Path) -> str:
        """Bắt đầu gửi một file. Tạo luồng gửi và trả về transfer_id NGAY."""
        raise NotImplementedError("T25 · R1")

    def respond_to_offer(self, transfer_id: str, accept: bool) -> None:
        """Người dùng đồng ý hoặc từ chối một OfferReceived. Mở khóa luồng nhận đang chờ."""
        raise NotImplementedError("T14, T25 · R1")

    def cancel(self, transfer_id: str) -> None:
        """Hủy một lượt, gửi hay nhận đều được. Kết quả về qua TransferFinished."""
        raise NotImplementedError("T25 · R1")

    def set_download_dir(self, path: str | Path) -> None:
        """Đổi thư mục nhận cho các lượt sau."""
        raise NotImplementedError("T25 · R1")
