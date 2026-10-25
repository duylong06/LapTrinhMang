"""Bên nhận: máy chủ TCP nhận file — docs/03 mục 4.

Phụ trách: R4 · Nhiệm vụ: T20, T21 (tuần 2), T27, T28 (tuần 3), T37 (tuần 4)

Một luồng chấp nhận kết nối; MỖI kết nối được xử lý trên một luồng riêng, để một máy gửi
bị treo không chặn máy khác. Mỗi kết nối đi qua 5 trạng thái ở docs/03 mục 4.4:
chờ OFFER -> chờ quyết định -> nhận dữ liệu -> kiểm tra -> kết thúc.

Mọi thứ đến từ mạng là KHÔNG ĐÁNG TIN. Làm đủ 9 kiểm tra ở docs/03 mục 4.9.
Lỗi ở một kết nối không được làm sập máy chủ.

Đọc thêm: TCP/IP Sockets in C# mục 4.3 Threads, 4.6 Closing Connections.
"""
from __future__ import annotations

from typing import Callable

from truyennhanh.config import Config
from truyennhanh.core.events import Emit
from truyennhanh.protocol.messages import Offer

AskUser = Callable[[Offer, str, int], bool]
"""ask_user(offer, tên_đã_làm_sạch, resume_offset) -> True nếu người dùng đồng ý.

Do lõi cung cấp. Hàm này CHẶN tối đa DECISION_TIMEOUT_S (lõi phát OfferReceived rồi chờ
trên một threading.Event); hết giờ thì trả về False và bên nhận gửi REJECT timeout.
"""


class FileReceiverServer:
    """Lắng nghe config.transfer_port; cổng bận thì để hệ điều hành chọn (bind cổng 0)."""

    def __init__(self, config: Config, emit: Emit, ask_user: AskUser) -> None:
        raise NotImplementedError("T20 · R4")

    @property
    def port(self) -> int:
        """Cổng TCP thật đang lắng nghe — R2 phát giá trị này trong ANNOUNCE."""
        raise NotImplementedError("T20 · R4")

    def start(self) -> int:
        """Mở socket lắng nghe, bật luồng chấp nhận. Trả về cổng thật."""
        raise NotImplementedError("T20 · R4")

    def stop(self) -> None:
        """Ngừng nhận kết nối mới; gửi CANCEL shutting_down cho các lượt đang chạy; giữ .part."""
        raise NotImplementedError("T20 · R4")

    def cancel(self, transfer_id: str) -> None:
        """Hủy một lượt đang nhận: gửi CANCEL cancelled, đóng kết nối, giữ .part."""
        raise NotImplementedError("T20 · R4")
