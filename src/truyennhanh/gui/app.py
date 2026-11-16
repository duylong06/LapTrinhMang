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

import ipaddress
import os
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
import traceback
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
MAX_EVENTS_PER_TICK = 200   # mỗi lần poll xử lý tối đa chừng này sự kiện, để cửa sổ luôn kịp vẽ
BUSY_POLL_MS = 10           # còn sự kiện tồn đọng thì poll lại ngay sau 10 ms
STOP_TIMEOUT_S = 5          # đóng cửa sổ: chờ service.stop() tối đa chừng này giây rồi thoát hẳn


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


def format_eta(seconds: float) -> str:
    """12 -> '12 giây', 65 -> '1 phút 05 giây', 4000 -> '1 giờ 06 phút'."""
    total = max(int(seconds), 0)
    if total >= 3600:
        return f"{total // 3600} giờ {total % 3600 // 60:02d} phút"
    if total >= 60:
        return f"{total // 60} phút {total % 60:02d} giây"
    return f"{total} giây"


def parse_host_port(text: str) -> tuple[str, int | None]:
    """'192.168.1.20' hoặc '192.168.1.20:50506' -> (ip, cổng hoặc None).

    Sai thì ném ValueError kèm câu tiếng Việt để hiện thẳng cho người dùng; nhờ vậy lỗi
    gõ nhầm được báo ngay ở giao diện thay vì đợi lõi mạng từ chối.
    """
    value = text.strip()
    if not value:
        raise ValueError("Chưa nhập địa chỉ IP.")
    host, port_text = value, None
    if value.count(":") == 1:  # nhiều hơn một dấu ':' là IPv6, để ipaddress tự xử lý
        host, port_text = (part.strip() for part in value.split(":"))
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        raise ValueError(f"\"{host}\" không phải địa chỉ IP hợp lệ (ví dụ 192.168.1.20).") from None
    if ip.version != 4:
        raise ValueError("Hiện chỉ hỗ trợ địa chỉ IPv4.")
    if ip.is_unspecified or ip.is_multicast or str(ip) == "255.255.255.255":
        raise ValueError(f"{ip} không phải địa chỉ của một máy cụ thể.")
    port = None
    if port_text is not None:
        if not port_text.isdigit() or not 1 <= int(port_text) <= 65535:
            raise ValueError("Cổng phải là số từ 1 đến 65535.")
        port = int(port_text)
    return str(ip), port


def coalesce_progress(events: list) -> list:
    """Chỉ giữ sự kiện TransferProgress MỚI NHẤT của mỗi lượt trong một lô.

    Vẽ lại thanh tiến độ 50 lần chỉ để hiện kết quả của lần cuối là phí công và làm
    cửa sổ giật. Các loại sự kiện khác giữ nguyên thứ tự.
    """
    last: dict[str, int] = {}
    for i, event in enumerate(events):
        if isinstance(event, TransferProgress):
            last[event.transfer_id] = i
    return [e for i, e in enumerate(events)
            if not isinstance(e, TransferProgress) or last[e.transfer_id] == i]


def open_folder(path: Path) -> None:
    """Mở thư mục bằng trình quản lý file của hệ điều hành."""
    if sys.platform == "win32":
        os.startfile(path)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


class MainWindow:
    """Bốn vùng: danh sách máy · chọn file và gửi · tiến trình · lịch sử đã nhận."""

    def __init__(self, root: tk.Tk, service) -> None:
        """service: TruyenNhanhService hoặc FakeService — hai lớp có cùng API."""
        self.root = root
        self.service = service

        root.title("Truyền Nhanh")
        root.geometry("640x660")
        root.minsize(600, 620)

        self.device_name_var = tk.StringVar(value="-")
        self.file_var = tk.StringVar(value="(chưa chọn file)")
        self.target_var = tk.StringVar(value="")
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_text_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="")
        self.download_dir_var = tk.StringVar(value="")
        self.detail_var = tk.StringVar(value="")        # "14,9 / 24 MB" cạnh dòng tiến trình
        self.peers_hint_var = tk.StringVar(value="")    # gợi ý khi danh sách máy còn trống
        self._history_paths: dict[str, Path | None] = {}  # dòng lịch sử -> đường dẫn file đã lưu

        self._peers: list[Peer] = []
        self._selected_path: Path | None = None
        self._active_id: str | None = None
        self._started: dict[str, TransferStarted] = {}
        self._closing = False

        self._build_header()
        self._build_peers_area()
        self._build_send_area()
        self._build_progress_area()
        self._build_status_bar()
        self._build_history_area()
        self._refresh_buttons()
        self._render_peers()
        root.bind("<Control-o>", lambda _e: self._on_choose_file())  # phím tắt: chọn file
        root.bind("<F5>", lambda _e: self._on_refresh())            # phím tắt: làm mới

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
        ttk.Label(box, textvariable=self.peers_hint_var,
                  foreground="gray").pack(anchor="w")

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

        top = ttk.Frame(box)
        top.pack(fill="x")
        ttk.Label(top, textvariable=self.target_var).pack(side="left")
        ttk.Label(top, textvariable=self.detail_var).pack(side="right")
        row = ttk.Frame(box)
        row.pack(fill="x", pady=4)
        self.progress_bar = ttk.Progressbar(row, variable=self.progress_var,
                                            maximum=100)
        self.progress_bar.pack(side="left", fill="x", expand=True)
        ttk.Label(row, textvariable=self.progress_text_var, width=38,
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
            box, columns=("file", "from", "size", "time"), show="headings", height=5)
        self.history_tree.heading("file", text="Tên file")
        self.history_tree.heading("from", text="Từ máy")
        self.history_tree.heading("size", text="Kích thước")
        self.history_tree.heading("time", text="Lúc")
        self.history_tree.column("file", width=230)
        self.history_tree.column("from", width=140)
        self.history_tree.column("size", width=80, anchor="e")
        self.history_tree.column("time", width=60, anchor="center")
        self.history_tree.bind("<Double-1>", self._on_history_open)  # bấm đúp: mở thư mục chứa file
        self.history_tree.pack(fill="both", expand=True)

        row = ttk.Frame(box)
        row.pack(fill="x", pady=(6, 0))
        ttk.Label(row, text="Lưu tại: ").pack(side="left")
        ttk.Label(row, textvariable=self.download_dir_var).pack(
            side="left", fill="x", expand=True)
        self.change_dir_button = ttk.Button(row, text="Đổi...",
                                            command=self._on_change_download_dir)
        self.change_dir_button.pack(side="right")
        self.open_dir_button = ttk.Button(row, text="Mở thư mục",
                                          command=self._on_open_download_dir)
        self.open_dir_button.pack(side="right", padx=(0, 6))

    # ---------- Trạng thái ban đầu ----------
    def _load_initial_state(self) -> None:
        """Lấy ảnh chụp hiện tại từ service (docs: list_peers / list_transfers)."""
        self.device_name_var.set(self.service.device_name)
        self.download_dir_var.set(str(self.service.get_download_dir()))
        self._peers = list(self.service.list_peers())
        self._render_peers()
        for t in reversed(self.service.list_transfers()):  # cũ -> mới
            if t.direction == Direction.RECEIVE and t.state == TransferState.DONE:
                self._add_history(t.file_name, t.peer_name, t.size, "", t.saved_path)
            elif t.state == TransferState.ACTIVE:
                self._active_id = t.id
                self._set_target(t.direction, t.peer_name)
                self._show_progress(t.done_bytes, t.size, 0.0)
        self._refresh_buttons()

    # ---------- Danh sách máy ----------
    def _selected_peer_id(self) -> str | None:
        sel = self.peer_list.curselection()
        return self._peers[sel[0]].id if sel else None

    def _render_peers(self) -> None:
        selected = self._selected_peer_id()
        self.peer_list.delete(0, "end")
        for i, peer in enumerate(self._peers):
            mark = "  (thêm tay)" if peer.manual else ""
            self.peer_list.insert("end", f"●  {peer.name:<18} {peer.ip}{mark}")
            if peer.id == selected:
                self.peer_list.selection_set(i)
        self.peers_hint_var.set(
            "" if self._peers else 'Chưa thấy máy nào. Bấm "Làm mới" hoặc thêm máy theo IP.')

    def _upsert_peer(self, peer: Peer) -> None:
        for i, old in enumerate(self._peers):
            if old.id == peer.id:
                self._peers[i] = peer
                return
        self._peers.append(peer)

    # ---------- Vùng tiến trình / lịch sử ----------
    def _set_target(self, direction: Direction, peer_name: str, note: str = "") -> None:
        verb = "Đang gửi tới" if direction == Direction.SEND else "Đang nhận từ"
        self.target_var.set(f"{verb} {peer_name}{note}")

    def _show_progress(self, done: int, total: int, bytes_per_second: float) -> None:
        percent = done * 100 / total if total else 0
        self.progress_var.set(percent)
        text = f"{percent:.0f}%   {format_speed(bytes_per_second)}"
        if bytes_per_second > 0:
            text += f"   còn {format_eta((total - done) / bytes_per_second)}"
        self.progress_text_var.set(text)
        self.detail_var.set(f"{format_size(done)} / {format_size(total)}" if total else "")

    def _reset_progress(self) -> None:
        self.progress_var.set(0)
        self.progress_text_var.set("")
        self.detail_var.set("")

    def _add_history(self, file_name: str, peer_name: str, size: int | None = None,
                     when: str | None = None, saved_path: Path | None = None) -> None:
        if when is None:
            when = datetime.now().strftime("%H:%M")
        size_text = format_size(size) if size else ""
        iid = self.history_tree.insert("", 0, values=(file_name, peer_name, size_text, when))
        self._history_paths[iid] = saved_path

    def _refresh_buttons(self) -> None:
        """Nút Hủy chỉ bấm được khi đang có một lượt hiện trên thanh tiến trình."""
        self.cancel_button.state(["!disabled"] if self._active_id else ["disabled"])

    def has_active_transfer(self) -> bool:
        return self._active_id is not None

    @property
    def is_closing(self) -> bool:
        return self._closing

    def begin_shutdown(self) -> None:
        """Đánh dấu đang đóng: từ đây không xử lý sự kiện nữa, để khỏi bật hộp thoại cho cửa sổ đã ẩn."""
        self._closing = True

    # ---------- Nút bấm (không chờ mạng — luật 2) ----------
    def _on_choose_file(self) -> None:
        """Chỉ mở hộp chọn file của hệ điều hành, không đụng tới mạng."""
        path = filedialog.askopenfilename(title="Chọn file để gửi")
        if path:
            self._selected_path = Path(path)
            try:
                size_text = f" ({format_size(self._selected_path.stat().st_size)})"
            except OSError:
                size_text = ""
            self.file_var.set(f"{self._selected_path.name}{size_text}")

    def _on_add_ip(self) -> None:
        initial = ""
        while True:  # gõ sai thì báo lỗi rồi hỏi lại, giữ nguyên chữ đã gõ để sửa
            text = simpledialog.askstring(
                "Thêm máy theo IP",
                "Nhập địa chỉ IP của máy kia (ví dụ 192.168.1.20,\n"
                "hoặc kèm cổng: 192.168.1.20:50506):",
                initialvalue=initial, parent=self.root)
            if not text:
                return
            try:
                ip, port = parse_host_port(text)
                break
            except ValueError as exc:
                messagebox.showwarning("Truyền Nhanh", str(exc), parent=self.root)
                initial = text
        try:
            peer = (self.service.add_manual_peer(ip) if port is None
                    else self.service.add_manual_peer(ip, port))
        except Exception as exc:  # lõi có thể từ chối vì lý do riêng
            messagebox.showerror("Truyền Nhanh", f"Không thêm được máy: {exc}",
                                 parent=self.root)
            return
        self._upsert_peer(peer)
        self._render_peers()

    def _on_refresh(self) -> None:
        if self.service is None:
            return
        self.service.refresh_peers()  # trả về ngay; máy tìm thấy báo bằng PeerFound

    def _open_folder_safely(self, folder: Path, create: bool = False) -> None:
        try:
            if create:
                folder.mkdir(parents=True, exist_ok=True)  # chưa nhận file nào thì thư mục có thể chưa có
            open_folder(folder)
        except OSError as exc:
            messagebox.showerror("Truyền Nhanh", f"Không mở được thư mục: {exc}",
                                 parent=self.root)

    def _on_open_download_dir(self) -> None:
        self._open_folder_safely(Path(self.service.get_download_dir()), create=True)

    def _on_history_open(self, _event=None) -> None:
        """Bấm đúp một dòng "Đã nhận" thì mở thư mục chứa file đó."""
        selection = self.history_tree.selection()
        if not selection:
            return
        saved = self._history_paths.get(selection[0])
        if saved is None:  # dòng nạp lúc mở cửa sổ có thể không biết đường dẫn
            self._on_open_download_dir()
        else:
            self._open_folder_safely(Path(saved).parent)

    def _on_change_download_dir(self) -> None:
        chosen = filedialog.askdirectory(
            title="Chọn thư mục nhận file",
            initialdir=self.download_dir_var.get() or None)
        if not chosen:
            return
        try:
            self.service.set_download_dir(chosen)
        except Exception as exc:
            messagebox.showerror("Truyền Nhanh", f"Không đổi được thư mục: {exc}",
                                 parent=self.root)
            return
        self.download_dir_var.set(str(self.service.get_download_dir()))

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
        if not self._selected_path.is_file():
            messagebox.showwarning(
                "Truyền Nhanh", "File này không còn tồn tại hoặc không phải file thường. "
                "Hãy chọn lại.", parent=self.root)
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
        self._refresh_buttons()

    def on_cancel_clicked(self) -> None:
        if self._active_id is not None:
            self.service.cancel(self._active_id)  # kết quả về qua TransferFinished

    # ---------- Sự kiện từ service (luật 3) ----------
    def poll_events(self) -> None:
        """Lấy sự kiện đang có trong service.events, xử lý, rồi hẹn gọi lại.

        Khác bản T23 ở ba điểm, đều để cửa sổ không bị đơ khi lõi thật bắn sự kiện dồn dập:
          - mỗi lần lấy tối đa MAX_EVENTS_PER_TICK sự kiện (còn thì poll lại sau BUSY_POLL_MS);
          - gộp các TransferProgress cùng một lượt, chỉ vẽ lại cái mới nhất;
          - một sự kiện gây lỗi không làm mất cả lô còn lại hay làm dừng vòng poll.
        """
        if self._closing:
            return
        batch: list = []
        try:
            while len(batch) < MAX_EVENTS_PER_TICK:
                try:
                    batch.append(self.service.events.get_nowait())
                except queue.Empty:
                    break
            for event in coalesce_progress(batch):
                try:
                    self.handle_event(event)
                except Exception:
                    traceback.print_exc()
        finally:
            backlog = len(batch) >= MAX_EVENTS_PER_TICK
            self.root.after(BUSY_POLL_MS if backlog else POLL_INTERVAL_MS, self.poll_events)

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
            note = ""
            if event.offset and event.size:
                note = f" (tiếp tục từ {event.offset * 100 // event.size}%)"
            self._set_target(event.direction, event.peer_name, note)
            self._show_progress(event.offset, event.size, 0.0)
            self._refresh_buttons()

        elif isinstance(event, TransferProgress):
            if event.transfer_id == self._active_id:
                self._show_progress(event.done_bytes, event.total_bytes,
                                    event.bytes_per_second)

        elif isinstance(event, TransferFinished):
            started = self._started.pop(event.transfer_id, None)
            if event.ok and event.direction == Direction.RECEIVE and started:
                self._add_history(started.file_name, started.peer_name, started.size,
                                  saved_path=event.saved_path)
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
                self._refresh_buttons()

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
        try:
            self.service.respond_to_offer(offer_event.transfer_id, accept)  # luật 4
        except Exception as exc:
            messagebox.showerror("Truyền Nhanh", f"Không trả lời được yêu cầu: {exc}",
                                 parent=self.root)


def run_app(use_fake: bool = False) -> None:
    """Tạo service (thật hoặc giả), start(), mở cửa sổ, mainloop(); đóng cửa sổ thì service.stop()."""
    root = tk.Tk()
    root.withdraw()  # chưa hiện cửa sổ trống nếu service không khởi động được
    try:
        service = FakeService() if use_fake else TruyenNhanhService()  # <- MỘT dòng duy nhất
        service.start()
    except Exception as exc:  # ví dụ: cổng bị chiếm do đang chạy một bản khác
        messagebox.showerror(
            "Truyền Nhanh", f"Không khởi động được lõi mạng:\n{exc}", parent=root)
        root.destroy()
        return

    window = MainWindow(root, service)
    root.deiconify()

    def on_close() -> None:
        if window.is_closing:  # bấm đóng lần hai khi đang dọn dẹp
            return
        if window.has_active_transfer() and not messagebox.askyesno(
                "Truyền Nhanh", "Đang truyền file. Thoát sẽ hủy lượt này. Thoát không?",
                parent=root):
            return
        window.begin_shutdown()
        root.withdraw()  # cửa sổ biến mất ngay, người dùng không thấy nó đơ

        def stop_service() -> None:
            # service.stop() gửi BYE, dừng luồng; có thể mất vài giây nên chạy ngoài luồng chính.
            # Nó không gọi Tkinter nên không vi phạm luật 1.
            try:
                service.stop()
            except Exception:
                traceback.print_exc()

        stopper = threading.Thread(target=stop_service, daemon=True)
        stopper.start()
        deadline = time.monotonic() + STOP_TIMEOUT_S

        def wait_then_destroy() -> None:
            if stopper.is_alive() and time.monotonic() < deadline:
                root.after(50, wait_then_destroy)
            else:
                root.destroy()

        wait_then_destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()