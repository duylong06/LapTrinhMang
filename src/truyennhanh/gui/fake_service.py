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
from pathlib import Path

from truyennhanh.core.events import Event
from truyennhanh.core.models import Peer
from truyennhanh.protocol.constants import TRANSFER_PORT_DEFAULT


class FakeService:
    events: "queue.Queue[Event]"

    def __init__(self, config=None) -> None:
        raise NotImplementedError("T23 · R5")

    def start(self) -> None:
        raise NotImplementedError("T23 · R5")

    def stop(self) -> None:
        raise NotImplementedError("T23 · R5")

    def list_peers(self) -> list[Peer]:
        raise NotImplementedError("T23 · R5")

    def add_manual_peer(self, ip: str, port: int = TRANSFER_PORT_DEFAULT) -> Peer:
        raise NotImplementedError("T23 · R5")

    def send_file(self, peer_id: str, path: str | Path) -> str:
        raise NotImplementedError("T23 · R5")

    def respond_to_offer(self, transfer_id: str, accept: bool) -> None:
        raise NotImplementedError("T23 · R5")

    def cancel(self, transfer_id: str) -> None:
        raise NotImplementedError("T23 · R5")

    def set_download_dir(self, path: str | Path) -> None:
        raise NotImplementedError("T23 · R5")
