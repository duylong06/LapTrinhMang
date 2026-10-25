"""Bên gửi: gửi một file qua một kết nối TCP — docs/03 mục 4.4 và 4.5.

Phụ trách: R3 · Nhiệm vụ: T08 (thử nghiệm), T18, T19 (tuần 2), T26 (truyền tiếp, tuần 3), T35 (hủy)

Trình tự một lượt:
  1. sha256_file (phát StatusMessage "Đang tính mã băm...")
  2. Kết nối TCP, hết giờ CONNECT_TIMEOUT_S
  3. Gửi OFFER, chờ ACCEPT/REJECT tối đa ACCEPT_WAIT_TIMEOUT_S
  4. ACCEPT offset=k: kiểm tra 0 <= k <= size, nhảy tới byte k, phát TransferStarted
  5. Gửi DATA từng khối config.chunk_size; phát TransferProgress không quá 10 lần/giây
  6. Gửi DONE, chờ RESULT tối đa RESULT_WAIT_TIMEOUT_S, phát TransferFinished, đóng kết nối

Mất kết nối ở bước 5 (T26): chờ lần lượt RETRY_DELAYS_S, kết nối lại, gửi lại OFFER cùng
transfer_id. Hết 5 lần thì TransferFinished(ok=False).

Đọc thêm: Kurose Chương 2 slide 105–108; TCP/IP Sockets in C# mục 5.1, 5.2.
"""
from __future__ import annotations

from pathlib import Path

from truyennhanh.config import Config
from truyennhanh.core.events import Emit
from truyennhanh.core.models import Peer


class FileSender:
    """Một đối tượng cho một lượt gửi. Lõi tạo luồng và gọi run() trong luồng đó."""

    def __init__(self, transfer_id: str, sender_id: str, sender_name: str,
                 peer: Peer, path: Path, config: Config, emit: Emit) -> None:
        raise NotImplementedError("T18 · R3")

    def run(self) -> None:
        """Chạy trọn một lượt gửi, CHẶN cho tới khi xong. Không ném ngoại lệ ra ngoài:
        mọi kết cục — thành công, bị từ chối, lỗi, bị hủy — báo bằng đúng một TransferFinished.
        """
        raise NotImplementedError("T18, T19, T26 · R3")

    def cancel(self) -> None:
        """Gọi từ luồng khác. Gửi CANCEL cancelled nếu đang kết nối, rồi để run() kết thúc."""
        raise NotImplementedError("T35 · R3")
