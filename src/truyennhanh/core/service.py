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
from truyennhanh.core.models import Peer, Transfer
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

    @property
    def device_name(self) -> str:
        """Tên máy này đang hiện với các máy khác. Giao diện hiện ở góc cửa sổ."""
        raise NotImplementedError("T14 · R1")

    def list_peers(self) -> list[Peer]:
        """Ảnh chụp danh sách máy đang thấy."""
        raise NotImplementedError("T25 · R1")

    def refresh_peers(self) -> None:
        """Gửi lại DISCOVER ngay, không chờ chu kỳ 2 giây.

        Dùng cho nút Làm mới trên giao diện và lệnh `truyennhanh scan`.
        Trả về ngay; máy tìm thấy báo về bằng sự kiện PeerFound.
        """
        raise NotImplementedError("T25 · R1")

    def add_manual_peer(self, ip: str, port: int = TRANSFER_PORT_DEFAULT) -> Peer:
        """Thêm máy theo IP (FR-02). Máy thêm tay không bị hết hạn."""
        raise NotImplementedError("T25, T29 · R1, R2")

    def list_transfers(self) -> list[Transfer]:
        """Các lượt truyền của lần chạy này, mới nhất trước.

        Giao diện chủ yếu dựng danh sách từ sự kiện; hàm này để lấy trạng thái
        ban đầu lúc mở cửa sổ và để vẽ lại khi cần.
        """
        raise NotImplementedError("T25 · R1")

    def send_file(self, peer_id: str, path: str | Path, as_name: str | None = None) -> str:
        """Bắt đầu gửi một file. Tạo luồng gửi và trả về transfer_id NGAY.

        as_name: khai một tên khác trong OFFER thay cho tên file thật. Chỉ dùng cho
        kiểm thử bảo mật KT-28 (lệnh `truyennhanh send --as-name ../../hack.txt`),
        giao diện không bao giờ truyền tham số này.
        """
        raise NotImplementedError("T25 · R1")

    def respond_to_offer(self, transfer_id: str, accept: bool) -> None:
        """Người dùng đồng ý hoặc từ chối một OfferReceived. Mở khóa luồng nhận đang chờ."""
        raise NotImplementedError("T14, T25 · R1")

    def cancel(self, transfer_id: str) -> None:
        """Hủy một lượt, gửi hay nhận đều được. Kết quả về qua TransferFinished."""
        raise NotImplementedError("T25 · R1")

    def get_download_dir(self) -> Path:
        """Thư mục nhận hiện tại. Giao diện hiện lên và dùng cho nút Mở thư mục."""
        raise NotImplementedError("T14 · R1")

    def set_download_dir(self, path: str | Path) -> None:
        """Đổi thư mục nhận cho các lượt sau."""
        raise NotImplementedError("T25 · R1")
