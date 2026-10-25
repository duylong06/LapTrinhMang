"""Sự kiện lõi phát ra cho giao diện — docs/02 mục 3. Phụ trách: R1 · chốt ở T05.

Các thành phần mạng (dò tìm, gửi, nhận) không biết giao diện tồn tại. Chúng gọi hàm
emit(sự_kiện) được truyền vào; lõi đẩy sự kiện vào service.events (queue.Queue);
giao diện lấy ra mỗi 100 ms trên luồng chính (docs/02 mục 4).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Union

from truyennhanh.core.models import Direction, Peer
from truyennhanh.protocol.constants import Reason


@dataclass(frozen=True)
class PeerFound:
    """Một máy mới xuất hiện trong danh sách."""

    peer: Peer


@dataclass(frozen=True)
class PeerLost:
    """Một máy biến mất: gửi BYE, hoặc im lặng quá PEER_TIMEOUT_S."""

    peer_id: str


@dataclass(frozen=True)
class OfferReceived:
    """Có máy muốn gửi file tới. Giao diện PHẢI gọi service.respond_to_offer(transfer_id, ...).

    file_name     : tên ĐÃ làm sạch, đúng tên sẽ được lưu
    resume_offset : khác 0 nghĩa là truyền tiếp từ byte này — hiển thị phần trăm cho người dùng
    """

    transfer_id: str
    sender_id: str
    sender_name: str
    file_name: str
    size: int
    resume_offset: int


@dataclass(frozen=True)
class TransferStarted:
    """Một lượt bắt đầu truyền dữ liệu (sau ACCEPT)."""

    transfer_id: str
    direction: Direction
    peer_name: str
    file_name: str
    size: int
    offset: int


@dataclass(frozen=True)
class TransferProgress:
    """Tiến độ. Tối đa PROGRESS_MAX_PER_SECOND lần mỗi giây mỗi lượt."""

    transfer_id: str
    done_bytes: int
    total_bytes: int
    bytes_per_second: float


@dataclass(frozen=True)
class TransferFinished:
    """Một lượt kết thúc, vì bất kỳ lý do gì. Mỗi lượt phát đúng một lần.

    ok=True     : thành công; saved_path là nơi lưu (chỉ có ở bên nhận)
    ok=False    : reason cho biết vì sao; message là câu tiếng Việt để hiện cho người dùng
    """

    transfer_id: str
    direction: Direction
    ok: bool
    reason: Reason | None = None
    saved_path: Path | None = None
    message: str | None = None


@dataclass(frozen=True)
class StatusMessage:
    """Thông báo trạng thái chung, ví dụ "Đang tính mã băm...". transfer_id có thể là None."""

    text: str
    transfer_id: str | None = None


Event = Union[PeerFound, PeerLost, OfferReceived, TransferStarted,
              TransferProgress, TransferFinished, StatusMessage]

Emit = Callable[[Event], None]
"""Kiểu của hàm emit mà lõi truyền vào cho các thành phần mạng."""
