
"""Bảng các máy đang thấy, có hết hạn — docs/03 mục 3.3.

Phụ trách: R2 · Nhiệm vụ: T16 (tuần 2), T29 (máy thêm tay, tuần 3)
"""

from __future__ import annotations

import copy
import time
import threading
from typing import Callable

from truyennhanh.core.models import Peer
from truyennhanh.protocol.constants import PEER_TIMEOUT_S


class PeerTable:
    """Khóa của mỗi máy là Peer.id, không phải IP."""

    def __init__(
        self,
        timeout_s: float = PEER_TIMEOUT_S,
        clock: Callable[[], float] = time.monotonic
    ) -> None:
        self._timeout_s = timeout_s
        self._clock = clock
        self._peers: dict[str, Peer] = {}
        self._lock = threading.Lock()

    def upsert(
        self,
        peer_id: str,
        name: str,
        ip: str,
        tcp_port: int,
        os: str | None = None
    ) -> bool:
        """Thêm hoặc cập nhật máy. True nếu là máy mới."""
        with self._lock:
            is_new = peer_id not in self._peers

            if is_new:
                self._peers[peer_id] = Peer(
                    id=peer_id,
                    name=name,
                    ip=ip,
                    tcp_port=tcp_port,
                    last_seen=self._clock(),
                    manual=False,
                    os=os
                )
            else:
                peer = self._peers[peer_id]
                peer.name = name
                peer.ip = ip
                peer.tcp_port = tcp_port
                peer.last_seen = self._clock()
                peer.os = os

            return is_new

    def add_manual(self, ip: str, tcp_port: int) -> Peer:
        """Thêm máy thủ công theo IP, không bao giờ hết hạn."""
        peer_id = f"manual:{ip}"

        with self._lock:
            if peer_id in self._peers:
                peer = self._peers[peer_id]
                peer.tcp_port = tcp_port
                return copy.deepcopy(peer)

            peer = Peer(
                id=peer_id,
                name=ip,
                ip=ip,
                tcp_port=tcp_port,
                last_seen=self._clock(),
                manual=True
            )
            self._peers[peer_id] = peer
            return copy.deepcopy(peer)

    def remove(self, peer_id: str) -> Peer | None:
        """Xóa máy theo ID."""
        with self._lock:
            return self._peers.pop(peer_id, None)

    def expire(self) -> list[Peer]:
        """Xóa các máy không phải manual đã quá thời gian hết hạn."""
        with self._lock:
            now = self._clock()
            expired = [
                peer_id
                for peer_id, peer in self._peers.items()
                if not peer.manual
                and now - peer.last_seen > self._timeout_s
            ]

            removed = [
                self._peers.pop(peer_id)
                for peer_id in expired
            ]

            return removed

    def get(self, peer_id: str) -> Peer | None:
        """Lấy máy theo ID."""
        with self._lock:
            peer = self._peers.get(peer_id)
            return copy.deepcopy(peer) if peer is not None else None

    def snapshot(self) -> list[Peer]:
        """Trả về bản sao danh sách, sắp xếp theo tên."""
        with self._lock:
            peers = copy.deepcopy(list(self._peers.values()))
            return sorted(peers, key=lambda peer: (peer.name.casefold(), peer.id))
