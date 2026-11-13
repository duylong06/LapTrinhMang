
"""Mã hóa và giải mã gói dò tìm UDP — docs/03 mục 3.2 và 3.4.

Phụ trách: R2 · Nhiệm vụ: T15 (tuần 2)
"""
from __future__ import annotations

import json
import unicodedata
import uuid
from dataclasses import dataclass

from truyennhanh.protocol.constants import (
    DiscoveryType,
    MAX_DATAGRAM_BYTES,
    MAX_NAME_CHARS,
    PROTOCOL_NAME,
    PROTOCOL_VERSION,
)


@dataclass(frozen=True)
class DiscoveryPacket:
    """Một gói dò tìm đã giải mã. KHÔNG có trường IP: IP lấy từ recvfrom (quyết định D8).

    tcp_port là None với gói BYE.
    """

    type: DiscoveryType
    id: str
    name: str
    tcp_port: int | None = None
    os: str | None = None


def _valid_uuid4(value: str) -> bool:
    """Kiểm tra chuỗi UUID phiên bản 4."""
    try:
        return str(uuid.UUID(value)) == value.lower() and uuid.UUID(value).version == 4
    except (ValueError, AttributeError, TypeError):
        return False


def _clean_name(name: str) -> str:
    """Loại bỏ ký tự điều khiển và giới hạn độ dài tên."""
    cleaned = "".join(
        char for char in name
        if unicodedata.category(char) != "Cc"
    )
    return cleaned[:MAX_NAME_CHARS]


def encode_packet(packet: DiscoveryPacket) -> bytes:
    """Thành JSON gọn, UTF-8, có proto và v. Kết quả không được vượt MAX_DATAGRAM_BYTES."""
    if not isinstance(packet, DiscoveryPacket):
        raise TypeError("packet phải là DiscoveryPacket")

    if not isinstance(packet.type, DiscoveryType):
        raise ValueError("type không hợp lệ")

    if not _valid_uuid4(packet.id):
        raise ValueError("id phải là UUID phiên bản 4")

    if not isinstance(packet.name, str):
        raise ValueError("name phải là chuỗi")

    if packet.type in (DiscoveryType.DISCOVER, DiscoveryType.ANNOUNCE):
        if type(packet.tcp_port) is not int or not 1 <= packet.tcp_port <= 65535:
            raise ValueError("tcp_port phải nằm trong khoảng 1–65535")
    elif packet.tcp_port is not None:
        raise ValueError("Gói BYE không được có tcp_port")

    if packet.os is not None and not isinstance(packet.os, str):
        raise ValueError("os phải là chuỗi hoặc None")

    data = {
        "proto": PROTOCOL_NAME,
        "v": PROTOCOL_VERSION,
        "type": packet.type.value,
        "id": packet.id,
        "name": _clean_name(packet.name),
    }

    if packet.tcp_port is not None:
        data["tcp_port"] = packet.tcp_port

    if packet.os is not None:
        data["os"] = packet.os

    encoded = json.dumps(
        data,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")

    if len(encoded) > MAX_DATAGRAM_BYTES:
        raise ValueError("Gói UDP vượt quá MAX_DATAGRAM_BYTES")

    return encoded


def decode_packet(data: bytes) -> DiscoveryPacket | None:
    """Giải mã một gói nhận được. Trả về None cho MỌI gói phải bỏ qua theo mục 3.4.

    Không bao giờ ném ngoại lệ: mạng LAN là môi trường dùng chung, ai cũng gửi được
    byte bất kỳ tới cổng 50505. Tên hiển thị phải được bỏ ký tự điều khiển và cắt
    còn MAX_NAME_CHARS ký tự.
    """
    try:
        if not isinstance(data, bytes):
            return None

        if len(data) > MAX_DATAGRAM_BYTES:
            return None

        text = data.decode("utf-8")
        obj = json.loads(text)

        if not isinstance(obj, dict):
            return None

        if obj.get("proto") != PROTOCOL_NAME:
            return None

        if type(obj.get("v")) is not int or obj["v"] != PROTOCOL_VERSION:
            return None

        try:
            packet_type = DiscoveryType(obj.get("type"))
        except (ValueError, TypeError):
            return None

        peer_id = obj.get("id")
        name = obj.get("name")

        if not isinstance(peer_id, str) or not _valid_uuid4(peer_id):
            return None

        if not isinstance(name, str):
            return None

        tcp_port = None

        if packet_type in (DiscoveryType.DISCOVER, DiscoveryType.ANNOUNCE):
            tcp_port = obj.get("tcp_port")
            if type(tcp_port) is not int or not 1 <= tcp_port <= 65535:
                return None

        os_name = obj.get("os")
        if os_name is not None and not isinstance(os_name, str):
            return None

        return DiscoveryPacket(
            type=packet_type,
            id=peer_id,
            name=_clean_name(name),
            tcp_port=tcp_port,
            os=os_name,
        )

    except Exception:
        return None
