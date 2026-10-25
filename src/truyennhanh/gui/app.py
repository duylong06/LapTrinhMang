"""Giao diện đồ họa Tkinter — docs/02 mục 4 (mô hình luồng). README mục "Người dùng thấy gì".

Phụ trách: R5 · Nhiệm vụ: T10 (khung tĩnh), T23 (với FakeService), T30 (nối thật), T40 (hoàn thiện)

BỐN LUẬT CỦA MÔ HÌNH LUỒNG — đọc docs/02 mục 4 trước khi viết dòng nào:
  1. Chỉ luồng chính được gọi Tkinter.
  2. Hàm xử lý nút bấm KHÔNG BAO GIỜ chờ mạng. Gọi service.send_file(...) là đủ — nó trả về ngay.
  3. Sự kiện lấy từ service.events bằng root.after(POLL_INTERVAL_MS, ...), dùng get_nowait()
     trong vòng lặp cho tới khi hàng đợi rỗng.
  4. Gặp OfferReceived thì hiện hộp thoại, rồi gọi service.respond_to_offer(...).

Đổi FakeService sang TruyenNhanhService chỉ được phép là sửa MỘT dòng trong run_app.
"""
from __future__ import annotations

import tkinter as tk

POLL_INTERVAL_MS = 100


class MainWindow:
    """Bốn vùng: danh sách máy · chọn file và gửi · tiến trình · lịch sử đã nhận."""

    def __init__(self, root: tk.Tk, service) -> None:
        """service: TruyenNhanhService hoặc FakeService — hai lớp có cùng API."""
        raise NotImplementedError("T10, T23 · R5")

    def poll_events(self) -> None:
        """Lấy hết sự kiện đang có trong service.events, xử lý, rồi hẹn gọi lại sau POLL_INTERVAL_MS."""
        raise NotImplementedError("T23 · R5")

    def handle_event(self, event) -> None:
        """Cập nhật giao diện theo từng loại sự kiện trong core/events.py."""
        raise NotImplementedError("T23 · R5")

    def on_send_clicked(self) -> None:
        raise NotImplementedError("T23 · R5")

    def on_cancel_clicked(self) -> None:
        raise NotImplementedError("T30 · R5")

    def ask_accept(self, offer_event) -> None:
        """Hộp thoại «<máy> muốn gửi <tên file> (<kích thước>). Nhận không?».
        Nếu resume_offset khác 0 thì ghi rõ "tiếp tục từ X%".
        """
        raise NotImplementedError("T23, T30 · R5")


def run_app(use_fake: bool = False) -> None:
    """Tạo service (thật hoặc giả), start(), mở cửa sổ, mainloop(); đóng cửa sổ thì service.stop()."""
    raise NotImplementedError("T23, T30 · R5")
