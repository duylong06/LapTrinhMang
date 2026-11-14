
"""Dò tìm thiết bị bằng UDP broadcast — docs/03 mục 3.
Phụ trách: R2 · Nhiệm vụ: T15
"""
from __future__ import annotations

import platform
import socket
import threading

from truyennhanh.core.events import Emit, PeerFound, PeerLost
from truyennhanh.discovery.messages import DiscoveryPacket, encode_packet, decode_packet
from truyennhanh.discovery.peer_table import PeerTable
from truyennhanh.protocol.constants import (
    DISCOVERY_PORT,
    BROADCAST_ADDRESS,
    ANNOUNCE_INTERVAL_S,
    DiscoveryType,
)


class Discovery:
    """Quản lý dò tìm thiết bị trong mạng LAN bằng UDP."""

    def __init__(
        self,
        instance_id: str,
        device_name: str,
        tcp_port: int,
        peers: PeerTable,
        emit: Emit,
        port: int = DISCOVERY_PORT,
    ) -> None:
        self.instance_id = instance_id
        self.device_name = device_name
        self.tcp_port = tcp_port
        self._peers = peers
        self.emit = emit
        self.port = port
        self.os_name = platform.system()

        self._socket: socket.socket | None = None
        self._stop_event = threading.Event()
        self._listener_thread: threading.Thread | None = None
        self._timer_thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._running = False

    def _make_packet(self, packet_type: DiscoveryType) -> bytes:
        """Tạo gói tin theo giao thức."""
        packet = DiscoveryPacket(
            type=packet_type,
            id=self.instance_id,
            name=self.device_name,
            tcp_port=(
                self.tcp_port
                if packet_type in (
                    DiscoveryType.DISCOVER,
                    DiscoveryType.ANNOUNCE,
                )
                else None
            ),
            os=self.os_name,
        )
        return encode_packet(packet)

    def _send(
        self,
        packet_type: DiscoveryType,
        address: tuple[str, int],
    ) -> None:
        """Gửi một gói UDP đến địa chỉ chỉ định."""
        with self._lock:
            sock = self._socket

        if sock is None:
            return

        try:
            sock.sendto(self._make_packet(packet_type), address)
        except OSError:
            pass

    def start(self, tcp_port: int | None = None) -> None:
        """Mở socket, bật hai luồng nền và gửi DISCOVER."""
        if tcp_port is not None:
            self.set_tcp_port(tcp_port)

        with self._lock:
            if self._running:
                return

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                sock.bind(("0.0.0.0", self.port))
                sock.settimeout(0.5)
            except OSError:
                sock.close()
                raise

            self._socket = sock
            self._stop_event.clear()
            self._running = True

            self._listener_thread = threading.Thread(
                target=self._listen_loop,
                name="UDP-Discovery-Listener",
                daemon=True,
            )
            self._timer_thread = threading.Thread(
                target=self._timer_loop,
                name="UDP-Discovery-Timer",
                daemon=True,
            )

            self._listener_thread.start()
            self._timer_thread.start()

        self.discover_now()

    def stop(self) -> None:
        """Gửi BYE, dừng hai luồng và đóng socket. Gọi nhiều lần không lỗi."""
        with self._lock:
            if not self._running:
                return

        self._send(
            DiscoveryType.BYE,
            (BROADCAST_ADDRESS, self.port),
        )

        with self._lock:
            self._running = False
            self._stop_event.set()
            sock = self._socket
            self._socket = None

        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass

        current = threading.current_thread()
        for thread in (self._listener_thread, self._timer_thread):
            if thread is not None and thread is not current:
                thread.join(timeout=1.0)

    def discover_now(self) -> None:
        """Gửi DISCOVER ngay khi người dùng yêu cầu làm mới."""
        self._send(
            DiscoveryType.DISCOVER,
            (BROADCAST_ADDRESS, self.port),
        )

    def refresh(self) -> None:
        """Gửi DISCOVER ngay khi người dùng yêu cầu làm mới."""
        self.discover_now()

    def peers(self) -> list:
        """Trả về danh sách các thiết bị đang được phát hiện."""
        return self._peers.snapshot()

    def set_tcp_port(self, port: int) -> None:
        """Cập nhật cổng TCP được phát trong ANNOUNCE."""
        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError("tcp_port phải nằm trong khoảng 1–65535")

        with self._lock:
            self.tcp_port = port

    def _listen_loop(self) -> None:
        """Nhận và xử lý các gói UDP."""
        while not self._stop_event.is_set():
            with self._lock:
                sock = self._socket

            if sock is None:
                break

            try:
                data, address = sock.recvfrom(2048)
            except socket.timeout:
                continue
            except OSError:
                break

            packet = decode_packet(data, self.instance_id)
            if packet is None:
                continue

            if packet.type == DiscoveryType.BYE:
                peer = self._peers.remove(packet.id)
                if peer is not None:
                    self.emit(PeerLost(peer_id=packet.id))
                continue

            if packet.tcp_port is None:
                continue

            is_new = self._peers.upsert(
                peer_id=packet.id,
                name=packet.name,
                ip=address[0],
                tcp_port=packet.tcp_port,
                os=packet.os,
            )

            if is_new:
                peer = self._peers.get(packet.id)
                if peer is not None:
                    self.emit(PeerFound(peer=peer))

            if packet.type == DiscoveryType.DISCOVER:
                self._send(
                    DiscoveryType.ANNOUNCE,
                    (address[0], self.port),
                )

    def _timer_loop(self) -> None:
        """Định kỳ phát ANNOUNCE và loại bỏ máy đã hết hạn."""
        while not self._stop_event.wait(ANNOUNCE_INTERVAL_S):
            self._send(
                DiscoveryType.ANNOUNCE,
                (BROADCAST_ADDRESS, self.port),
            )

            expired_peers = self._peers.expire()
            for peer in expired_peers:
                self.emit(PeerLost(peer_id=peer.id))
