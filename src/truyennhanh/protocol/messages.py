"""Tạo và kiểm tra các thông điệp JSON trong khung — docs/03 mục 4.3.

Phụ trách: R1 · Nhiệm vụ: T13 (tuần 2, xong trước thứ Tư)
Người dùng: R3, R4. Test viết sẵn bởi R6 ở T24: tests/test_messages.py.

Quy ước: JSON gọn (separators=(",", ":")), UTF-8, ensure_ascii=False.
Khi đọc: bỏ qua trường lạ; thiếu trường, sai kiểu, sai ràng buộc thì ném ProtocolError.

Module này là tầng trên của protocol/framing.py. framing cắt dòng byte thành
từng khung mà không quan tâm nội dung; module này hiểu nội dung bên trong khung.
Ranh giới đó cố ý: đổi cách đóng khung không phải sửa ở đây, và ngược lại.

Vì sao mọi hàm parse_* đều nhận transfer_id để đối chiếu: trên một kết nối chỉ
có đúng một lượt truyền (docs/03 mục 4), nên một thông điệp mang transfer_id lạ
là dấu hiệu sai giao thức hoặc có kẻ chen ngang. Bắt lỗi ngay tại đây thì bên
gửi và bên nhận không phải nhớ tự kiểm.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from truyennhanh.protocol.constants import PROTOCOL_VERSION, SHA256_HEX_LENGTH, Reason


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


_HEX_DIGITS = frozenset("0123456789abcdef")
"""Chỉ chữ thường. docs/03 mục 4.3 quy định sha256 là 64 ký tự hex CHỮ THƯỜNG.

Nếu chấp nhận cả chữ hoa thì cùng một file sinh ra hai chuỗi khác nhau, và tên
file .part (đặt theo mã băm, mục 4.5) sẽ lệch nhau giữa hai lần truyền.
"""


def encode_json(obj: dict) -> bytes:
    """dict -> bytes JSON gọn, UTF-8.

    separators=(",", ":") bỏ hết khoảng trắng thừa. ensure_ascii=False giữ
    nguyên chữ tiếng Việt thay vì đổi thành \\uXXXX — gói tin ngắn hơn và đọc
    được bằng mắt khi bắt gói bằng Wireshark lúc làm báo cáo.
    """
    text = json.dumps(obj, separators=(",", ":"), ensure_ascii=False)
    return text.encode("utf-8")


def decode_json(payload: bytes) -> dict:
    """bytes -> dict. Không phải UTF-8 hợp lệ, không phải JSON, không phải object: ProtocolError.

    Gộp cả ba lỗi vào một loại ngoại lệ vì bên gọi xử lý giống hệt nhau: trả lời
    bad_request rồi đóng kết nối. Phân biệt chúng chỉ làm bên gọi dài ra vô ích.
    """
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as e:
        raise ProtocolError(f"Nội dung không phải UTF-8 hợp lệ: {e}") from e

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ProtocolError(f"Nội dung không phải JSON hợp lệ: {e}") from e

    if not isinstance(data, dict):
        raise ProtocolError(
            f"Thông điệp phải là một đối tượng JSON, nhận được {type(data).__name__}"
        )
    return data


# --------------------------------------------------------------------------- Lấy trường và kiểm tra

def _get(data: dict, key: str) -> Any:
    """Lấy một trường bắt buộc. Thiếu thì ProtocolError."""
    if key not in data:
        raise ProtocolError(f"Thiếu trường bắt buộc: {key}")
    return data[key]


def _get_str(data: dict, key: str) -> str:
    """Lấy một trường bắt buộc kiểu chuỗi."""
    value = _get(data, key)
    if not isinstance(value, str):
        raise ProtocolError(
            f"Trường {key} phải là chuỗi, nhận được {type(value).__name__}"
        )
    return value


def _get_int(data: dict, key: str) -> int:
    """Lấy một trường bắt buộc kiểu số nguyên.

    Loại bỏ bool một cách tường minh: trong Python bool là lớp con của int, nên
    isinstance(True, int) trả về True. Không chặn thì {"size": true} lọt qua và
    được hiểu thành size = 1.
    """
    value = _get(data, key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ProtocolError(
            f"Trường {key} phải là số nguyên, nhận được {type(value).__name__}"
        )
    return value


def _get_reason(data: dict, key: str = "reason") -> Reason:
    """Lấy một mã lý do bắt buộc và kiểm tra nó nằm trong bảng ở docs/03 mục 4.8."""
    value = _get_str(data, key)
    try:
        return Reason(value)
    except ValueError:
        raise ProtocolError(f"Mã lý do không tồn tại: {value!r}") from None


def _check_transfer_id(data: dict, expected: str) -> None:
    """Đối chiếu transfer_id của thông điệp với lượt truyền đang chạy (docs/03 mục 4.3)."""
    got = _get_str(data, "transfer_id")
    if got != expected:
        raise ProtocolError(
            f"transfer_id không khớp: thông điệp mang {got!r}, lượt truyền là {expected!r}"
        )


# --------------------------------------------------------------------------- Tạo thông điệp

def make_offer(offer: Offer) -> bytes:
    """Nội dung khung OFFER, có thêm trường v = PROTOCOL_VERSION.

    Thứ tự trường giữ đúng như ví dụ ở docs/03 mục 4.3, để kết quả khớp từng
    byte với ví dụ tính sẵn ở mục 5 (phần đầu khung 00 00 00 fd 01).
    """
    return encode_json({
        "v": PROTOCOL_VERSION,
        "transfer_id": offer.transfer_id,
        "sender_id": offer.sender_id,
        "sender_name": offer.sender_name,
        "name": offer.name,
        "size": offer.size,
        "sha256": offer.sha256,
    })


def make_accept(transfer_id: str, offset: int) -> bytes:
    """offset = 0 là nhận từ đầu; khác 0 là truyền tiếp (docs/03 mục 4.5)."""
    if offset < 0:
        raise ValueError(f"offset không được âm: {offset}")
    return encode_json({"transfer_id": transfer_id, "offset": offset})


def make_reject(transfer_id: str, reason: Reason, message: str | None = None) -> bytes:
    """message là câu giải thích cho người đọc, không bắt buộc nên bỏ hẳn khỏi JSON khi None.

    Bỏ hẳn chứ không ghi null: đặc tả nói trường này không bắt buộc, và bên đọc
    phải chịu được việc nó vắng mặt. Luôn ghi null sẽ che mất lỗi đó khi thử.
    """
    data: dict[str, Any] = {"transfer_id": transfer_id, "reason": reason.value}
    if message is not None:
        data["message"] = message
    return encode_json(data)


def make_done(transfer_id: str) -> bytes:
    """Bên gửi đã gửi xong mọi byte."""
    return encode_json({"transfer_id": transfer_id})


def make_result(transfer_id: str, ok: bool, reason: Reason | None = None) -> bytes:
    """ok=True thì reason phải là None (ghi null trong JSON).

    Hai chiều đều bắt buộc: thành công mà kèm lý do, hoặc thất bại mà không có
    lý do, đều là lỗi lập trình ở bên gọi. Chặn ngay lúc tạo thay vì để bên kia
    nhận một thông điệp vô nghĩa rồi mới báo bad_request.
    """
    if ok and reason is not None:
        raise ValueError(f"RESULT ok=True không được kèm lý do, nhận được {reason!r}")
    if not ok and reason is None:
        raise ValueError("RESULT ok=False phải kèm lý do")

    return encode_json({
        "transfer_id": transfer_id,
        "ok": ok,
        "reason": None if reason is None else reason.value,
    })


def make_cancel(transfer_id: str, reason: Reason) -> bytes:
    """Hủy lượt truyền. Gửi được từ cả hai phía, bất cứ lúc nào sau OFFER."""
    return encode_json({"transfer_id": transfer_id, "reason": reason.value})


# --------------------------------------------------------------------------- Đọc và kiểm tra

def parse_offer(payload: bytes) -> Offer:
    """Kiểm tra theo docs/03 mục 4.3 và 4.9 bước 3.

    - Đủ các trường, đúng kiểu (size phải là int, không phải bool hay chuỗi)
    - size >= 0
    - sha256 đúng 64 ký tự hex CHỮ THƯỜNG
    - v khác PROTOCOL_VERSION -> UnsupportedVersion

    Kiểm tra v trước tiên, vì hai lỗi này dẫn tới hai câu trả lời khác nhau:
    sai phiên bản thì REJECT unsupported_version, còn sai định dạng thì
    bad_request. Một OFFER của phiên bản 2 có thể có bộ trường hoàn toàn khác,
    nên đem luật của phiên bản 1 ra soi rồi báo bad_request là trả lời sai câu hỏi.

    Trường name KHÔNG được làm sạch ở đây. Làm sạch là việc của transfer/filenames.py
    (T22), vì nó phụ thuộc thư mục nhận và hệ điều hành — những thứ tầng giao
    thức không biết và không nên biết.
    """
    data = decode_json(payload)

    version = _get_int(data, "v")
    if version != PROTOCOL_VERSION:
        raise UnsupportedVersion(
            f"OFFER dùng phiên bản giao thức {version}, máy này chỉ hiểu {PROTOCOL_VERSION}"
        )

    size = _get_int(data, "size")
    if size < 0:
        raise ProtocolError(f"size không được âm: {size}")

    sha256 = _get_str(data, "sha256")
    if len(sha256) != SHA256_HEX_LENGTH:
        raise ProtocolError(
            f"sha256 phải dài đúng {SHA256_HEX_LENGTH} ký tự, nhận được {len(sha256)}"
        )
    if not all(c in _HEX_DIGITS for c in sha256):
        raise ProtocolError(
            "sha256 chỉ được chứa chữ số hex viết thường (0-9, a-f): " + repr(sha256)
        )

    return Offer(
        transfer_id=_get_str(data, "transfer_id"),
        sender_id=_get_str(data, "sender_id"),
        sender_name=_get_str(data, "sender_name"),
        name=_get_str(data, "name"),
        size=size,
        sha256=sha256,
    )


def parse_accept(payload: bytes, transfer_id: str, size: int) -> int:
    """Trả về offset. Kiểm tra transfer_id khớp và 0 <= offset <= size.

    offset == size là hợp lệ, không phải lỗi: bên nhận đã có đủ số byte từ lần
    truyền trước, bên gửi gửi thẳng DONE để hai bên so mã băm (docs/03 mục 4.5).
    """
    data = decode_json(payload)
    _check_transfer_id(data, transfer_id)

    offset = _get_int(data, "offset")
    if not 0 <= offset <= size:
        raise ProtocolError(
            f"offset {offset} nằm ngoài khoảng cho phép 0..{size}"
        )
    return offset


def parse_reject(payload: bytes, transfer_id: str) -> tuple[Reason, str | None]:
    """Trả về (lý do, câu giải thích nếu có)."""
    data = decode_json(payload)
    _check_transfer_id(data, transfer_id)

    reason = _get_reason(data)

    message = data.get("message")
    if message is not None and not isinstance(message, str):
        raise ProtocolError(
            f"Trường message phải là chuỗi, nhận được {type(message).__name__}"
        )
    return reason, message


def parse_done(payload: bytes, transfer_id: str) -> None:
    """Chỉ kiểm transfer_id. DONE không mang thêm thông tin nào khác."""
    _check_transfer_id(decode_json(payload), transfer_id)


def parse_result(payload: bytes, transfer_id: str) -> tuple[bool, Reason | None]:
    """Trả về (ok, lý do). ok=True thì lý do là None.

    Kiểm cả hai chiều giống make_result, vì một RESULT nói thất bại mà không nêu
    lý do thì bên gửi không có gì để hiện cho người dùng.
    """
    data = decode_json(payload)
    _check_transfer_id(data, transfer_id)

    ok = _get(data, "ok")
    if not isinstance(ok, bool):
        raise ProtocolError(
            f"Trường ok phải là true hoặc false, nhận được {type(ok).__name__}"
        )

    raw_reason = _get(data, "reason")
    if ok:
        if raw_reason is not None:
            raise ProtocolError(f"RESULT ok=true phải có reason là null, nhận được {raw_reason!r}")
        return True, None

    if raw_reason is None:
        raise ProtocolError("RESULT ok=false phải kèm mã lý do")
    return False, _get_reason(data)


def parse_cancel(payload: bytes, transfer_id: str) -> Reason:
    """Trả về lý do hủy."""
    data = decode_json(payload)
    _check_transfer_id(data, transfer_id)
    return _get_reason(data)
