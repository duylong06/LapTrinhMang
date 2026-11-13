
"""Mã hóa và giải mã gói dò tìm UDP — docs/03 mục 3.2 và 3.4.
Phụ trách: R2 · Nhiệm vụ: T15 (tuần 2)
"""
from __future__ import annotations

import json
import unicodedata
import uuid
from dataclasses import dataclass

from truyennhanh.protocol.constants import (
    PROTOCOL_NAME,
    PROTOCOL_VERSION,
    MAX_DATAGRAM_BYTES,
    MAX_NAME_CHARS,
    DiscoveryType,
)


@dataclass(frozen=True)
class DiscoveryPacket:
    type: DiscoveryType
    id: str
    name: str
    tcp_port: int | None = None
    os: str | None = None


def _valid_uuid(value: str) -> bool:
    """Kiểm tra chuỗi có phải UUID hợp lệ không."""
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def _clean_name(name: str) -> str:
    """Bỏ ký tự điều khiển và giới hạn độ dài tên máy."""
    cleaned = "".join(
        char for char in name
        if not unicodedata.category(char).startswith("C")
    )
    return cleaned[:MAX_NAME_CHARS]


def encode_packet(packet: DiscoveryPacket) -> bytes:
    """Mã hóa gói thành JSON UTF-8, không vượt quá MAX_DATAGRAM_BYTES."""
    if not isinstance(packet.type, DiscoveryType):
        raise ValueError("type không hợp lệ")

    if not isinstance(packet.id, str) or not _valid_uuid(packet.id):
        raise ValueError("id phải là UUID hợp lệ")

    if not isinstance(packet.name, str):
        raise ValueError("name phải là chuỗi")

    if packet.type in (DiscoveryType.DISCOVER, DiscoveryType.ANNOUNCE):
        if type(packet.tcp_port) is not int or not 1 <= packet.tcp_port <= 65535:
            raise ValueError("tcp_port phải nằm trong khoảng 1–65535")
    elif packet.tcp_port is not None:
        if type(packet.tcp_port) is not int or not 1 <= packet.tcp_port <= 65535:
            raise ValueError("tcp_port không hợp lệ")

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
        raise ValueError("Gói UDP vượt quá giới hạn 1024 byte")

    return encoded


def decode_packet(
    data: bytes,
    self_id: str | None = None,
) -> DiscoveryPacket | None:
    """Giải mã gói UDP. Trả về None nếu gói không hợp lệ hoặc là gói của chính mình."""
    try:
        if not isinstance(data, bytes):
            return None

        if len(data) > MAX_DATAGRAM_BYTES:
            return None

        obj = json.loads(data.decode("utf-8"))

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

        packet_id = obj.get("id")
        if not isinstance(packet_id, str) or not _valid_uuid(packet_id):
            return None

        if self_id is not None:
            if not isinstance(self_id, str) or not _valid_uuid(self_id):
                return None
            if uuid.UUID(packet_id) == uuid.UUID(self_id):
                return None

        name = obj.get("name")
        if not isinstance(name, str):
            return None

        tcp_port = obj.get("tcp_port")

        if packet_type in (DiscoveryType.DISCOVER, DiscoveryType.ANNOUNCE):
            if type(tcp_port) is not int or not 1 <= tcp_port <= 65535:
                return None
        elif tcp_port is not None:
            if type(tcp_port) is not int or not 1 <= tcp_port <= 65535:
                return None

        os_name = obj.get("os")
        if os_name is not None and not isinstance(os_name, str):
            return None

        return DiscoveryPacket(
            type=packet_type,
            id=packet_id,
            name=_clean_name(name),
            tcp_port=tcp_port,
            os=os_name,
        )

    except Exception:
        # Gói UDP không hợp lệ phải được bỏ qua, không làm ứng dụng crash.
        return None
