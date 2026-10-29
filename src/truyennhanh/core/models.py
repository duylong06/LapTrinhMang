"""Kiểu dữ liệu dùng chung giữa các module. Phụ trách: R1 · chốt ở T05.

Đây là hợp đồng: giao diện, dò tìm, gửi, nhận đều dùng các kiểu này.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from truyennhanh.protocol.constants import Reason


class Direction(str, Enum):
    """Chiều của một lượt truyền, nhìn từ máy này."""

    SEND = "send"
    RECEIVE = "receive"


class TransferState(str, Enum):
    """Trạng thái một lượt truyền.

    PENDING -> ACTIVE -> DONE, hoặc bất cứ lúc nào -> FAILED.
    """

    PENDING = "pending"   # đã tạo nhưng chưa truyền dữ liệu: đang tính mã băm, hoặc chờ người nhận đồng ý
    ACTIVE = "active"     # đang truyền dữ liệu
    DONE = "done"         # xong, mã băm khớp
    FAILED = "failed"     # kết thúc vì lỗi, bị từ chối hoặc bị hủy


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


@dataclass
class Transfer:
    """Một lượt truyền, nhìn từ máy này. Do service.list_transfers() trả về.

    Giao diện dựng danh sách lượt truyền từ các sự kiện, nhưng vẫn cần hàm này
    cho hai trường hợp: lúc mới mở cửa sổ (lấy những lượt đang chạy sẵn), và
    khi cần vẽ lại toàn bộ cho chắc.

    done_bytes : số byte đã truyền; chia cho size ra phần trăm
    saved_path : chỉ có ở chiều nhận, sau khi đã xác minh mã băm xong
    reason     : chỉ có khi state là FAILED
    """

    id: str
    direction: Direction
    peer_name: str
    file_name: str
    size: int
    done_bytes: int = 0
    state: TransferState = TransferState.PENDING
    reason: Reason | None = None
    saved_path: Path | None = None
