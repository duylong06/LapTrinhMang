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

import queue
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from truyennhanh.core.events import (
    OfferReceived,
    PeerFound,
    PeerLost,
    StatusMessage,
    TransferFinished,
    TransferProgress,
    TransferStarted,
)
from truyennhanh.core.models import Direction, Peer, TransferState
from truyennhanh.core.service import TruyenNhanhService
from truyennhanh.gui.fake_service import FakeService

POLL_INTERVAL_MS = 100


def format_size(n: int) -> str:
    """1536 -> '1,5 KB'. Dùng dấu phẩy thập phân như trong README."""
    size = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            text = f"{size:.0f}" if unit == "B" else f"{size:.1f}".replace(".", ",")
            return f"{text} {unit}"
        size /= 1024
    return f"{n} B"


def format_speed(bytes_per_second: float) -> str:
    if bytes_per_second >= 1024 * 1024:
        return f"{bytes_per_second / (1024 * 1024):.1f}".replace(".", ",") + " MB/s"
    return f"{bytes_per_second / 1024:.0f} KB/s"


class MainWindow:
    """Bốn vùng: danh sách máy · chọn file và gửi · tiến trình · lịch sử đã nhận."""

    def __init__(self, root: tk.Tk, service) -> None:
        """service: TruyenNhanhService hoặc FakeService — hai lớp có cùng API."""
        self.root = root
        self.service = service

        root.title("Truyền Nhanh")
        root.geometry("620x560")
        root.minsize(560, 520)

        self.device_name_var = tk.StringVar(value="-")
        self.file_var = tk.StringVar(value="(chưa chọn file)")
        self.target_var = tk.StringVar(value="")
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_text_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="")

        self._peers: list[Peer] = []
        self._selected_path: Path | None = None
        self._active_id: str | None = None
        self._started: dict[str, TransferStarted] = {}

        self._build_header()
        self._build_peers_area()
        self._build_send_area()
        self._build_progress_area()
        self._build_status_bar()
        self._build_history_area()

        # service=None: chỉ xem bố cục tĩnh (không có dữ liệu, không poll)
        if service is not None:
            self._load_initial_state()
            self.root.after(POLL_INTERVAL_MS, self.poll_events)

    # ---------- Dựng bố cục ----------
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

        row = ttk.Frame(box)
        row.pack(fill="x", pady=(6, 0))
        self.add_ip_button = ttk.Button(row, text="+ Thêm máy theo IP",
                                        command=self._on_add_ip)
        self.add_ip_button.pack(side="left")
        self.refresh_button = ttk.Button(row, text="Làm mới",
                                         command=self._on_refresh)
        self.refresh_button.pack(side="left", padx=(8, 0))

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

    def _build_status_bar(self) -> None:
        ttk.Label(self.root, textvariable=self.status_var,
                  anchor="w").pack(fill="x", padx=12, pady=(2, 0))

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

    # ---------- Trạng thái ban đầu ----------
    def _load_initial_state(self) -> None:
        """Lấy ảnh chụp hiện tại từ service (docs: list_peers / list_transfers)."""
        self.device_name_var.set(self.service.device_name)
        self._peers = list(self.service.list_peers())
        self._render_peers()
        for t in reversed(self.service.list_transfers()):  # cũ -> mới
            if t.direction == Direction.RECEIVE and t.state == TransferState.DONE:
                self._add_history(t.file_name, t.peer_name, "")
            elif t.state == TransferState.ACTIVE:
                self._active_id = t.id
                self._set_target(t.direction, t.peer_name)
                self._show_progress(t.done_bytes, t.size, 0.0)

    # ---------- Danh sách máy ----------
    def _selected_peer_id(self) -> str | None:
        sel = self.peer_list.curselection()
        return self._peers[sel[0]].id if sel else None

    def _render_peers(self) -> None:
        selected = self._selected_peer_id()
        self.peer_list.delete(0, "end")
        for i, peer in enumerate(self._peers):
            self.peer_list.insert("end", f"●  {peer.name:<18} {peer.ip}")
            if peer.id == selected:
                self.peer_list.selection_set(i)

    def _upsert_peer(self, peer: Peer) -> None:
        for i, old in enumerate(self._peers):
            if old.id == peer.id:
                self._peers[i] = peer
                return
        self._peers.append(peer)

    # ---------- Vùng tiến trình / lịch sử ----------
    def _set_target(self, direction: Direction, peer_name: str) -> None:
        verb = "Đang gửi tới" if direction == Direction.SEND else "Đang nhận từ"
        self.target_var.set(f"{verb} {peer_name}")

    def _show_progress(self, done: int, total: int, bytes_per_second: float) -> None:
        percent = done * 100 / total if total else 0
        self.progress_var.set(percent)
        text = f"{percent:.0f}%   {format_speed(bytes_per_second)}"
        if bytes_per_second > 0:
            text += f"   còn {int((total - done) / bytes_per_second)} giây"
        self.progress_text_var.set(text)

    def _reset_progress(self) -> None:
        self.progress_var.set(0)
        self.progress_text_var.set("")

    def _add_history(self, file_name: str, peer_name: str, when: str | None = None) -> None:
        if when is None:
            when = datetime.now().strftime("%H:%M")
        self.history_tree.insert("", 0, values=(file_name, peer_name, when))

    # ---------- Nút bấm (không chờ mạng — luật 2) ----------
    def _on_choose_file(self) -> None:
        """Chỉ mở hộp chọn file của hệ điều hành, không đụng tới mạng."""
        path = filedialog.askopenfilename(title="Chọn file để gửi")
        if path:
            self._selected_path = Path(path)
            self.file_var.set(self._selected_path.name)

    def _on_add_ip(self) -> None:
        ip = simpledialog.askstring(
            "Thêm máy theo IP", "Nhập địa chỉ IP (ví dụ 192.168.1.20):",
            parent=self.root)
        if not ip:
            return
        try:
            peer = self.service.add_manual_peer(ip.strip())
        except Exception as exc:  # lỗi định dạng IP... do lõi quyết định
            messagebox.showerror("Truyền Nhanh", f"Không thêm được máy: {exc}",
                                 parent=self.root)
            return
        self._upsert_peer(peer)
        self._render_peers()

    def _on_refresh(self) -> None:
        self.service.refresh_peers()  # trả về ngay; máy tìm thấy báo bằng PeerFound

    def on_send_clicked(self) -> None:
        peer_id = self._selected_peer_id()
        if peer_id is None:
            messagebox.showinfo("Truyền Nhanh", "Hãy chọn một máy trong danh sách.",
                                parent=self.root)
            return
        if self._selected_path is None:
            messagebox.showinfo("Truyền Nhanh", "Hãy chọn file cần gửi.",
                                parent=self.root)
            return
        try:
            transfer_id = self.service.send_file(peer_id, self._selected_path)
        except Exception as exc:
            messagebox.showerror("Truyền Nhanh", f"Không gửi được: {exc}",
                                 parent=self.root)
            return
        self._active_id = transfer_id
        self._reset_progress()
        self.target_var.set("Đang chờ bên nhận đồng ý...")

    def on_cancel_clicked(self) -> None:
        if self._active_id is not None:
            self.service.cancel(self._active_id)  # kết quả về qua TransferFinished

    # ---------- Sự kiện từ service (luật 3) ----------
    def poll_events(self) -> None:
        """Lấy hết sự kiện đang có trong service.events, xử lý, rồi hẹn gọi lại sau POLL_INTERVAL_MS."""
        try:
            while True:
                try:
                    event = self.service.events.get_nowait()
                except queue.Empty:
                    break
                self.handle_event(event)
        finally:
            self.root.after(POLL_INTERVAL_MS, self.poll_events)

    def handle_event(self, event) -> None:
        """Cập nhật giao diện theo từng loại sự kiện trong core/events.py."""
        if isinstance(event, PeerFound):
            self._upsert_peer(event.peer)
            self._render_peers()

        elif isinstance(event, PeerLost):
            self._peers = [p for p in self._peers if p.id != event.peer_id]
            self._render_peers()

        elif isinstance(event, OfferReceived):
            self.ask_accept(event)

        elif isinstance(event, TransferStarted):
            self._started[event.transfer_id] = event
            self._active_id = event.transfer_id
            self._set_target(event.direction, event.peer_name)
            self._show_progress(event.offset, event.size, 0.0)

        elif isinstance(event, TransferProgress):
            if event.transfer_id == self._active_id:
                self._show_progress(event.done_bytes, event.total_bytes,
                                    event.bytes_per_second)

        elif isinstance(event, TransferFinished):
            started = self._started.pop(event.transfer_id, None)
            if event.ok and event.direction == Direction.RECEIVE and started:
                self._add_history(started.file_name, started.peer_name)
            if event.transfer_id == self._active_id:
                self._active_id = None
                if event.ok:
                    done = "Đã gửi xong" if event.direction == Direction.SEND else "Đã nhận xong"
                    self.target_var.set(f"{done}: {started.file_name}" if started else done)
                    self.progress_var.set(100)
                    self.progress_text_var.set("100%")
                else:
                    self.target_var.set(event.message or "Truyền file thất bại.")
                    self._reset_progress()

        elif isinstance(event, StatusMessage):
            self.status_var.set(event.text)

    def ask_accept(self, offer_event) -> None:
        """Hộp thoại «<máy>» muốn gửi <tên file> (<kích thước>). Nhận không?».
        Nếu resume_offset khác 0 thì ghi rõ "tiếp tục từ X%".
        """
        text = (f"{offer_event.sender_name} muốn gửi {offer_event.file_name} "
                f"({format_size(offer_event.size)}). Nhận không?")
        if offer_event.resume_offset and offer_event.size:
            percent = offer_event.resume_offset * 100 // offer_event.size
            text += f"\nTiếp tục từ {percent}%."
        accept = messagebox.askyesno("Có file gửi đến", text, parent=self.root)
        self.service.respond_to_offer(offer_event.transfer_id, accept)  # luật 4


def run_app(use_fake: bool = False) -> None:
    """Tạo service (thật hoặc giả), start(), mở cửa sổ, mainloop(); đóng cửa sổ thì service.stop()."""
    service = FakeService() if use_fake else TruyenNhanhService()  # <- MỘT dòng duy nhất
    service.start()
    root = tk.Tk()
    MainWindow(root, service)

    def on_close() -> None:
        service.stop()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()