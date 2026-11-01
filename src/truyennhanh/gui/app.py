"""Giao diện đồ họa Tkinter — docs/02 mục 4 (mô hình luồng). README mục "Người dùng thấy gì".

Phụ trách: R5 · Nhiệm vụ: T10 (khung tĩnh), T23 (với FakeService), T30 (nối thật), T40 (hoàn thiện).

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
from tkinter import filedialog, ttk

POLL_INTERVAL_MS = 100


class MainWindow:
    """Bốn vùng: danh sách máy · chọn file và gửi · tiến trình · lịch sử đã nhận."""

    def __init__(self, root: tk.Tk, service) -> None:
        """service: TruyenNhanhService hoặc FakeService — hai lớp có cùng API.""" 
        self.root = root
        self.service = service  

        root.title("Truyền Nhanh")
        root.geometry("620x560")
        root.minsize(560, 520)
 
        self.device_name_var = tk.StringVar(value="LAPTOP-LONG")   
        self.file_var = tk.StringVar(value="(chưa chọn file)")
        self.target_var = tk.StringVar(value="")
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_text_var = tk.StringVar(value="")

        self._build_header()
        self._build_peers_area()
        self._build_send_area()
        self._build_progress_area()
        self._build_history_area()
        self._fill_sample_data()
 
    def _build_header(self) -> None:
        bar = ttk.Frame(self.root, padding=(12, 8))
        bar.pack(fill="x")
        ttk.Label(bar, text="Truyền Nhanh",
                  font=("Segoe UI", 14, "bold")).pack(side="left")
        ttk.Label(bar, textvariable=self.device_name_var).pack(side="right")
        ttk.Label(bar, text="Tên máy: ").pack(side="right")
        ttk.Separator(self.root).pack(fill="x")

    def _build_peers_area(self) -> None:
        box = ttk.LabelFrame(self.root, text="Máy trong mạng", padding=8)
        box.pack(fill="x", padx=12, pady=(10, 4))

        self.peer_list = tk.Listbox(box, height=5, activestyle="none",
                                    exportselection=False)
        self.peer_list.pack(fill="x")
 
        self.add_ip_button = ttk.Button(box, text="+ Thêm máy theo IP")
        self.add_ip_button.pack(anchor="w", pady=(6, 0))

    def _build_send_area(self) -> None:
        box = ttk.LabelFrame(self.root, text="Gửi file", padding=8)
        box.pack(fill="x", padx=12, pady=4)

        self.choose_button = ttk.Button(box, text="Chọn file...",
                                        command=self._on_choose_file)
        self.choose_button.pack(side="left")
        ttk.Label(box, textvariable=self.file_var).pack(
            side="left", padx=10, fill="x", expand=True)
        self.send_button = ttk.Button(box, text="Gửi",
                                      command=self.on_send_clicked)
        self.send_button.pack(side="right")

    def _build_progress_area(self) -> None:
        box = ttk.LabelFrame(self.root, text="Tiến trình", padding=8)
        box.pack(fill="x", padx=12, pady=4)

        ttk.Label(box, textvariable=self.target_var).pack(anchor="w")
        row = ttk.Frame(box)
        row.pack(fill="x", pady=4)
        self.progress_bar = ttk.Progressbar(row, variable=self.progress_var,
                                            maximum=100)
        self.progress_bar.pack(side="left", fill="x", expand=True)
        ttk.Label(row, textvariable=self.progress_text_var, width=30,
                  anchor="e").pack(side="left", padx=(8, 0))
        self.cancel_button = ttk.Button(box, text="Hủy",
                                        command=self.on_cancel_clicked)
        self.cancel_button.pack(anchor="e")

    def _build_history_area(self) -> None:
        box = ttk.LabelFrame(self.root, text="Đã nhận", padding=8)
        box.pack(fill="both", expand=True, padx=12, pady=(4, 12))

        self.history_tree = ttk.Treeview(
            box, columns=("file", "from", "time"), show="headings", height=5)
        self.history_tree.heading("file", text="Tên file")
        self.history_tree.heading("from", text="Từ máy")
        self.history_tree.heading("time", text="Lúc")
        self.history_tree.column("file", width=260)
        self.history_tree.column("from", width=160)
        self.history_tree.column("time", width=70, anchor="center")
        self.history_tree.pack(fill="both", expand=True)

    def _fill_sample_data(self) -> None:
        """DỮ LIỆU MẪU của T10 để xem bố cục. Xóa hàm này khi làm T23."""
        self.peer_list.insert("end", "●  PC-PHONGMAY-07     192.168.1.35")
        self.peer_list.insert("end", "●  LAPTOP-NGAN        192.168.1.12")
        self.file_var.set("bao_cao_cuoi_ky.pdf")
        self.target_var.set("Đang gửi tới PC-PHONGMAY-07")
        self.progress_var.set(62)
        self.progress_text_var.set("62%   8,4 MB/s   còn 12 giây")
        self.history_tree.insert("", "end",
                                 values=("bai_tap_tuan_5.zip", "LAPTOP-NGAN", "14:32"))

    def _on_choose_file(self) -> None:
        """Chỉ mở hộp chọn file của hệ điều hành, không đụng tới mạng."""
        path = filedialog.askopenfilename(title="Chọn file để gửi")
        if path:
            self.file_var.set(path.replace("\\", "/").split("/")[-1])
 
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
        """Hộp thoại «<máy>» muốn gửi <tên file> (<kích thước>). Nhận không?».
        Nếu resume_offset khác 0 thì ghi rõ "tiếp tục từ X%".
        """
        raise NotImplementedError("T23, T30 · R5")


def run_app(use_fake: bool = False) -> None:
    """Tạo service (thật hoặc giả), start(), mở cửa sổ, mainloop(); đóng cửa sổ thì service.stop()."""
    raise NotImplementedError("T23, T30 · R5")