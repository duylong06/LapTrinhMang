"""Tạo và kiểm tra các thông điệp JSON trong khung — docs/03 mục 4.3.

Phụ trách: R1 · Nhiệm vụ: T13 (tuần 2, xong trước thứ Tư)
Người dùng: R3, R4. Test viết sẵn bởi R6 ở T24: tests/test_messages.py.

Quy ước: JSON gọn (separators=(",", ":")), UTF-8, ensure_ascii=False.
Khi đọc: bỏ qua trường lạ; thiếu trường, sai kiểu, sai ràng buộc thì ném ProtocolError.
"""
from __future__ import annotations

from dataclasses import dataclass

from truyennhanh.protocol.constants import Reason


class ProtocolError(ValueError):
    """Thông điệp sai định dạng hoặc vi phạm đặc tả. Bên nhận trả lời bằng lý do bad_request."""


class UnsupportedVersion(ProtocolError):
    """OFFER có trường v khác PROTOCOL_VERSION. Bên nhận trả REJECT unsupported_version."""


@dataclass(frozen=True)
class Offer:
    """Nội dung một OFFER đã được kiểm tra hợp lệ. Tên file ở đây là tên GỐC, chưa làm sạch."""

    transfer_id: str
    sender_id: str
    sender_name: str
    name: str
    size: int
    sha256: str


def encode_json(obj: dict) -> bytes:
    """dict -> bytes JSON gọn, UTF-8."""
    raise NotImplementedError("T13 · R1")


def decode_json(payload: bytes) -> dict:
    """bytes -> dict. Không phải UTF-8 hợp lệ, không phải JSON, không phải object: ProtocolError."""
    raise NotImplementedError("T13 · R1")


# --------------------------------------------------------------------------- Tạo thông điệp

def make_offer(offer: Offer) -> bytes:
    """Nội dung khung OFFER, có thêm trường v = PROTOCOL_VERSION."""
    raise NotImplementedError("T13 · R1")


def make_accept(transfer_id: str, offset: int) -> bytes:
    raise NotImplementedError("T13 · R1")


def make_reject(transfer_id: str, reason: Reason, message: str | None = None) -> bytes:
    raise NotImplementedError("T13 · R1")


def make_done(transfer_id: str) -> bytes:
    raise NotImplementedError("T13 · R1")


def make_result(transfer_id: str, ok: bool, reason: Reason | None = None) -> bytes:
    """ok=True thì reason phải là None (ghi null trong JSON)."""
    raise NotImplementedError("T13 · R1")


def make_cancel(transfer_id: str, reason: Reason) -> bytes:
    raise NotImplementedError("T13 · R1")


# --------------------------------------------------------------------------- Đọc và kiểm tra

def parse_offer(payload: bytes) -> Offer:
    """Kiểm tra theo docs/03 mục 4.3 và 4.9 bước 3.

    - Đủ các trường, đúng kiểu (size phải là int, không phải bool hay chuỗi)
    - size >= 0
    - sha256 đúng 64 ký tự hex CHỮ THƯỜNG
    - v khác PROTOCOL_VERSION -> UnsupportedVersion
    """
    raise NotImplementedError("T13 · R1")


def parse_accept(payload: bytes, transfer_id: str, size: int) -> int:
    """Trả về offset. Kiểm tra transfer_id khớp và 0 <= offset <= size."""
    raise NotImplementedError("T13 · R1")


def parse_reject(payload: bytes, transfer_id: str) -> tuple[Reason, str | None]:
    """Trả về (lý do, câu giải thích nếu có)."""
    raise NotImplementedError("T13 · R1")


def parse_done(payload: bytes, transfer_id: str) -> None:
    raise NotImplementedError("T13 · R1")


def parse_result(payload: bytes, transfer_id: str) -> tuple[bool, Reason | None]:
    raise NotImplementedError("T13 · R1")


def parse_cancel(payload: bytes, transfer_id: str) -> Reason:
    raise NotImplementedError("T13 · R1")
