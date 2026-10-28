"""Đóng khung và mở khung trên dòng byte TCP — docs/03 mục 4.1.

Phụ trách: R1 · Nhiệm vụ: T04 (tuần 1)
Người dùng: R3 (bên gửi), R4 (bên nhận). Đây là module chặn nhiều người nhất — làm trước tiên.

TCP chỉ là một dòng byte, không có ranh giới thông điệp. Một lần recv() có thể trả về
nửa khung, hoặc một khung rưỡi. Module này giải quyết đúng vấn đề đó:

    [ 4 byte độ dài nội dung, big-endian ][ 1 byte loại ][ nội dung ]

Vì sao ghi độ dài ở đầu thay vì dùng ký tự phân cách (quyết định D3 ở docs/02):
nội dung file là nhị phân, nên bất kỳ ký tự phân cách nào cũng có thể xuất hiện
giữa dữ liệu. Biết trước độ dài còn cho phép từ chối khung quá lớn **trước khi**
cấp phát bộ nhớ cho nó.

Module này cố tình KHÔNG biết gì về JSON hay ý nghĩa từng loại khung. Nó chỉ
làm đúng một việc: cắt dòng byte thành từng khung. Việc hiểu nội dung là của
protocol/messages.py (T13).

Về hết giờ: các hàm ở đây không tự đặt timeout. Bên gọi dùng sock.settimeout()
theo bảng ở docs/03 mục 4.7; khi hết giờ, socket.timeout được ném ra ngoài
nguyên vẹn để bên gọi xử lý.

Đọc thêm: TCP/IP Sockets in C#, mục 3.3 "Framing and Parsing".
"""
from __future__ import annotations

import socket
import struct

from truyennhanh.protocol.constants import (
    FRAME_HEADER_FORMAT,
    FRAME_HEADER_SIZE,
    MAX_CONTROL_PAYLOAD,
    MAX_DATA_PAYLOAD,
    FrameType,
)

MIN_DATA_PAYLOAD = 1
"""Khung DATA rỗng là vi phạm đặc tả (docs/03 mục 4.1: DATA dài 1 đến 16 MiB).

File rỗng vẫn gửi được: bên gửi không gửi khung DATA nào, chỉ gửi thẳng DONE.
"""


class FrameError(Exception):
    """Khung vi phạm đặc tả: độ dài vượt giới hạn, loại khung không tồn tại."""


class ConnectionClosed(Exception):
    """Đối phương đóng kết nối khi chưa đọc đủ số byte cần."""


def max_payload_for(frame_type: FrameType) -> int:
    """Độ dài nội dung lớn nhất cho phép của một loại khung.

    DATA: MAX_DATA_PAYLOAD. Mọi loại khác: MAX_CONTROL_PAYLOAD.
    """
    return MAX_DATA_PAYLOAD if frame_type is FrameType.DATA else MAX_CONTROL_PAYLOAD


def _check_payload_length(frame_type: FrameType, length: int) -> None:
    """Kiểm tra độ dài nội dung nằm trong khoảng cho phép của loại khung.

    Tách riêng ra vì cả encode_frame (lúc gửi) và read_frame (lúc nhận) đều phải
    kiểm cùng một luật. Để hai chỗ tự kiểm riêng thì sớm muộn chúng lệch nhau.
    """
    ceiling = max_payload_for(frame_type)
    floor = MIN_DATA_PAYLOAD if frame_type is FrameType.DATA else 0

    if length > ceiling:
        raise FrameError(
            f"Khung {frame_type.name} dài {length} byte, vượt giới hạn {ceiling} byte"
        )
    if length < floor:
        raise FrameError(f"Khung {frame_type.name} phải dài ít nhất {floor} byte")


def encode_frame(frame_type: FrameType, payload: bytes) -> bytes:
    """Ghép phần đầu 5 byte và nội dung thành một khung hoàn chỉnh.

    Ném FrameError nếu payload vượt giới hạn của loại khung.
    Kết quả khớp từng byte ví dụ ở docs/03 mục 5.

    Lưu ý: độ dài tính trên BYTE sau khi mã hóa UTF-8, không phải số ký tự.
    Chuỗi "báo" có 3 ký tự nhưng chiếm 4 byte.
    """
    payload = bytes(payload)
    _check_payload_length(frame_type, len(payload))
    header = struct.pack(FRAME_HEADER_FORMAT, len(payload), frame_type)
    return header + payload


def send_frame(sock: socket.socket, frame_type: FrameType, payload: bytes) -> None:
    """Gửi trọn một khung.

    Dùng sendall chứ không dùng send: send được phép chỉ gửi một phần và trả về
    số byte đã gửi, bỏ sót phần còn lại. sendall lặp cho tới khi hết.

    Gửi phần đầu và nội dung trong MỘT lần gọi sendall để chúng nằm cùng một
    gói TCP khi có thể — tránh hiệu ứng mỗi khung tốn hai lượt đi về.
    """
    sock.sendall(encode_frame(frame_type, payload))


def recv_exact(sock: socket.socket, n: int) -> bytes:
    """Đọc ĐÚNG n byte từ socket.

    recv(n) được phép trả về ít hơn n byte — đây là nguồn lỗi kinh điển khi lập
    trình TCP, vì trên mạng LAN nhanh nó gần như luôn trả về đủ, nên lỗi chỉ lộ
    ra khi file lớn hoặc mạng chậm. Vì vậy phải lặp cho tới khi đủ.

    recv trả về b"" nghĩa là đối phương đã đóng: ném ConnectionClosed.
    n == 0 thì trả về b"" ngay, không gọi recv (recv(0) trả về b"" và sẽ bị
    hiểu nhầm thành đã đóng kết nối).
    """
    if n < 0:
        raise ValueError(f"Số byte cần đọc không được âm: {n}")
    if n == 0:
        return b""

    parts: list[bytes] = []
    remaining = n
    while remaining > 0:
        chunk = sock.recv(remaining)
        if not chunk:
            raise ConnectionClosed(
                f"Đối phương đóng kết nối khi còn thiếu {remaining}/{n} byte"
            )
        parts.append(chunk)
        remaining -= len(chunk)

    return parts[0] if len(parts) == 1 else b"".join(parts)


def read_frame(sock: socket.socket) -> tuple[FrameType, bytes]:
    """Đọc một khung: 5 byte đầu, kiểm tra, rồi đúng chừng ấy byte nội dung.

    Thứ tự bắt buộc (docs/03 mục 4.1 và 4.9):
      1. recv_exact 5 byte, giải ra (độ dài, mã loại)
      2. Mã loại không có trong FrameType -> FrameError
      3. Độ dài vượt max_payload_for(loại) -> FrameError, KHÔNG đọc phần nội dung
      4. recv_exact(độ dài)

    Bước 3 phải đứng TRƯỚC bước 4, nếu không thì chỉ cần 5 byte khai độ dài
    4 GB là bên nhận cố cấp phát 4 GB bộ nhớ và chết — một kiểu tấn công từ
    chối dịch vụ rẻ tiền (docs/03 mục 4.9 điểm 1).
    """
    header = recv_exact(sock, FRAME_HEADER_SIZE)
    length, type_code = struct.unpack(FRAME_HEADER_FORMAT, header)

    try:
        frame_type = FrameType(type_code)
    except ValueError:
        raise FrameError(f"Loại khung không tồn tại: 0x{type_code:02x}") from None

    _check_payload_length(frame_type, length)

    return frame_type, recv_exact(sock, length)
