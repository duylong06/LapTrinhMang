"""Dịch vụ giả để làm giao diện trước khi có phần mạng — nhiệm vụ T23.

Phụ trách: R5

Có ĐÚNG CÙNG API với core/service.py (TruyenNhanhService), nhưng không mở socket nào.
Một luồng nền tự sinh sự kiện giả theo kịch bản, ví dụ:
  - 0,5 giây: PeerFound "PC-PHONGMAY-07"; 1 giây: PeerFound "LAPTOP-NGAN"
  - 3 giây  : OfferReceived "bai_tap_tuan_5.zip" từ LAPTOP-NGAN
  - send_file(): TransferStarted, rồi TransferProgress tăng dần, rồi TransferFinished
  - thỉnh thoảng một lượt thất bại, để giao diện xử lý cả nhánh lỗi

Khi lõi thật thay đổi API (T05), file này phải đổi theo.
"""
from __future__ import annotations

import queue
import threading
import time
from dataclasses import replace
from pathlib import Path

from truyennhanh.core.events import (
    Event,
    OfferReceived,
    PeerFound,
    StatusMessage,
    TransferFinished,
    TransferProgress,
    TransferStarted,
)
from truyennhanh.core.models import Direction, Peer, Transfer, TransferState
from truyennhanh.protocol.constants import TRANSFER_PORT_DEFAULT, Reason

FAKE_SPEED = 8.4 * 1024 * 1024  # byte/giây, khớp số liệu mẫu trong README
FAKE_MAX_SECONDS = 6            # file lớn thì tăng tốc để mỗi lượt giả không quá ~6 giây
FAKE_STEP = 0.2                 # 5 sự kiện tiến độ mỗi giây
FAIL_EVERY = 3                  # cứ lượt GỬI thứ 3, 6, 9... thì thất bại giữa chừng


def _any_reason() -> Reason:
    """Lấy một giá trị Reason bất kỳ cho các lượt thất bại giả.

    TODO: đổi sang Reason.<tên đúng> sau khi đọc protocol/constants.py
    (ví dụ lý do "bị từ chối", "bị hủy", "mất kết nối").
    """
    return next(iter(Reason))


class FakeService:
    events: "queue.Queue[Event]"

    def __init__(self, config=None) -> None:
        self.events = queue.Queue()
        self._lock = threading.Lock()
        self._stop_flag = threading.Event()
        self._peers: dict[str, Peer] = {}
        self._transfers: dict[str, Transfer] = {}
        self._cancel_flags: dict[str, threading.Event] = {}
        self._download_dir = Path.home() / "TruyenNhanh"
        self._counter = 0
        self._send_count = 0

    # ---------- vòng đời ----------
    def start(self) -> None:
        self._stop_flag.clear()
        threading.Thread(target=self._scenario, daemon=True).start()

    def stop(self) -> None:
        self._stop_flag.set()
        with self._lock:
            for flag in self._cancel_flags.values():
                flag.set()

    # ---------- API giống TruyenNhanhService ----------
    @property
    def device_name(self) -> str:
        return "LAPTOP-LONG"

    def list_peers(self) -> list[Peer]:
        with self._lock:
            return list(self._peers.values())

    def refresh_peers(self) -> None:
        self.events.put(StatusMessage(text="Đang tìm máy trong mạng..."))

    def add_manual_peer(self, ip: str, port: int = TRANSFER_PORT_DEFAULT) -> Peer:
        peer = Peer(id=f"manual:{ip}", name=ip, ip=ip, tcp_port=port,
                    last_seen=time.monotonic(), manual=True)
        self._add_peer(peer)
        return peer

    def list_transfers(self) -> list[Transfer]:
        """Mới nhất trước, trả về bản sao để luồng nền không sửa dưới chân giao diện."""
        with self._lock:
            return [replace(t) for t in reversed(list(self._transfers.values()))]

    def send_file(self, peer_id: str, path: str | Path, as_name: str | None = None) -> str:
        path = Path(path)
        with self._lock:
            peer = self._peers.get(peer_id)
            self._send_count += 1
            fail = self._send_count % FAIL_EVERY == 0
        try:
            size = max(path.stat().st_size, 1)
        except OSError:
            size = 8 * 1024 * 1024  # file không đọc được: giả vờ 8 MB
        transfer = Transfer(
            id=self._new_id(), direction=Direction.SEND,
            peer_name=peer.name if peer else peer_id,
            file_name=as_name or path.name, size=size)
        self._register(transfer)
        threading.Thread(target=self._simulate, args=(transfer.id, fail), daemon=True).start()
        return transfer.id

    def respond_to_offer(self, transfer_id: str, accept: bool) -> None:
        if accept:
            threading.Thread(target=self._simulate, args=(transfer_id, False), daemon=True).start()
        else:
            self._finish(transfer_id, ok=False, reason=_any_reason(),
                         message="Bạn đã từ chối nhận file.")

    def cancel(self, transfer_id: str) -> None:
        with self._lock:
            flag = self._cancel_flags.get(transfer_id)
        if flag:
            flag.set()

    def get_download_dir(self) -> Path:
        return self._download_dir

    def set_download_dir(self, path: str | Path) -> None:
        self._download_dir = Path(path)

    # ---------- kịch bản nền ----------
    def _scenario(self) -> None:
        if not self._sleep(0.5):
            return
        self._add_peer(Peer(id="fake-pc-phongmay-07", name="PC-PHONGMAY-07",
                            ip="192.168.1.35", tcp_port=TRANSFER_PORT_DEFAULT,
                            last_seen=time.monotonic()))
        if not self._sleep(0.5):
            return
        self._add_peer(Peer(id="fake-laptop-ngan", name="LAPTOP-NGAN",
                            ip="192.168.1.12", tcp_port=TRANSFER_PORT_DEFAULT,
                            last_seen=time.monotonic()))
        if not self._sleep(2.0):
            return
        offer = Transfer(id=self._new_id(), direction=Direction.RECEIVE,
                         peer_name="LAPTOP-NGAN", file_name="bai_tap_tuan_5.zip",
                         size=5_400_000)
        self._register(offer)
        self.events.put(OfferReceived(
            transfer_id=offer.id, sender_id="fake-laptop-ngan", sender_name=offer.peer_name,
            file_name=offer.file_name, size=offer.size, resume_offset=0))

    def _simulate(self, transfer_id: str, fail: bool) -> None:
        """Giả lập một lượt truyền (gửi hoặc nhận) chạy trên luồng nền."""
        with self._lock:
            t = self._transfers[transfer_id]
            cancel = self._cancel_flags[transfer_id]
        if not self._sleep(0.3):
            return
        with self._lock:
            t.state = TransferState.ACTIVE
        self.events.put(TransferStarted(
            transfer_id=t.id, direction=t.direction, peer_name=t.peer_name,
            file_name=t.file_name, size=t.size, offset=0))

        speed = max(FAKE_SPEED, t.size / FAKE_MAX_SECONDS)
        done = 0
        while done < t.size:
            if self._stop_flag.wait(FAKE_STEP):
                return
            if cancel.is_set():
                self._finish(t.id, ok=False, reason=_any_reason(),
                             message="Đã hủy lượt truyền.")
                return
            done = min(t.size, done + int(speed * FAKE_STEP))
            with self._lock:
                t.done_bytes = done
            self.events.put(TransferProgress(
                transfer_id=t.id, done_bytes=done, total_bytes=t.size,
                bytes_per_second=speed))
            if fail and done >= t.size // 2:
                self._finish(t.id, ok=False, reason=_any_reason(),
                             message="Mất kết nối giữa chừng (lỗi giả để thử giao diện).")
                return

        saved = self._download_dir / t.file_name if t.direction == Direction.RECEIVE else None
        self._finish(t.id, ok=True, saved_path=saved)

    # ---------- tiện ích nội bộ ----------
    def _sleep(self, seconds: float) -> bool:
        """Ngủ có thể bị đánh thức khi stop(); trả về False nếu service đã dừng."""
        return not self._stop_flag.wait(seconds)

    def _new_id(self) -> str:
        with self._lock:
            self._counter += 1
            return f"fake-t{self._counter}"

    def _register(self, transfer: Transfer) -> None:
        with self._lock:
            self._transfers[transfer.id] = transfer
            self._cancel_flags[transfer.id] = threading.Event()

    def _add_peer(self, peer: Peer) -> None:
        with self._lock:
            self._peers[peer.id] = peer
        self.events.put(PeerFound(peer=peer))

    def _finish(self, transfer_id: str, ok: bool, reason: Reason | None = None,
                saved_path: Path | None = None, message: str | None = None) -> None:
        with self._lock:
            t = self._transfers.get(transfer_id)
            if t is None:
                return
            t.state = TransferState.DONE if ok else TransferState.FAILED
            t.reason = None if ok else reason
            t.saved_path = saved_path
        self.events.put(TransferFinished(
            transfer_id=transfer_id, direction=t.direction, ok=ok,
            reason=None if ok else reason, saved_path=saved_path, message=message))