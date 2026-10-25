"""Đóng khung và mở khung trên dòng byte TCP — docs/03 mục 4.1.

Phụ trách: R1 · Nhiệm vụ: T04 (tuần 1)
Người dùng: R3 (bên gửi), R4 (bên nhận). Đây là module chặn nhiều người nhất — làm trước tiên.

TCP chỉ là một dòng byte, không có ranh giới thông điệp. Một lần recv() có thể trả về
nửa khung, hoặc một khung rưỡi. Module này giải quyết đúng vấn đề đó:

    [ 4 byte độ dài nội dung, big-endian ][ 1 byte loại ][ nội dung ]

Đọc thêm: TCP/IP Sockets in C#, mục 3.3 "Framing and Parsing".
"""
from __future__ import annotations

import socket

from truyennhanh.protocol.constants import FrameType


class FrameError(Exception):
    """Khung vi phạm đặc tả: độ dài vượt giới hạn, loại khung không tồn tại."""


class ConnectionClosed(Exception):
    """Đối phương đóng kết nối khi chưa đọc đủ số byte cần."""


def max_payload_for(frame_type: FrameType) -> int:
    """Độ dài nội dung lớn nhất cho phép của một loại khung.

    DATA: MAX_DATA_PAYLOAD. Mọi loại khác: MAX_CONTROL_PAYLOAD.
    """
    raise NotImplementedError("T04 · R1")


def encode_frame(frame_type: FrameType, payload: bytes) -> bytes:
    """Ghép phần đầu 5 byte và nội dung thành một khung hoàn chỉnh.

    Dùng struct.pack với FRAME_HEADER_FORMAT. Ném FrameError nếu payload vượt giới hạn
    của loại khung. Kết quả phải khớp từng byte ví dụ ở docs/03 mục 5.
    """
    raise NotImplementedError("T04 · R1")


def send_frame(sock: socket.socket, frame_type: FrameType, payload: bytes) -> None:
    """Gửi trọn một khung. Dùng sendall, không dùng send (send có thể chỉ gửi một phần)."""
    raise NotImplementedError("T04 · R1")


def recv_exact(sock: socket.socket, n: int) -> bytes:
    """Đọc ĐÚNG n byte từ socket.

    recv(n) được phép trả về ít hơn n byte, nên phải lặp cho tới khi đủ.
    recv trả về b"" nghĩa là đối phương đã đóng: ném ConnectionClosed.
    n == 0 thì trả về b"" ngay.
    """
    raise NotImplementedError("T04 · R1")


def read_frame(sock: socket.socket) -> tuple[FrameType, bytes]:
    """Đọc một khung: 5 byte đầu, kiểm tra, rồi đúng chừng ấy byte nội dung.

    Thứ tự bắt buộc (docs/03 mục 4.1 và 4.9):
      1. recv_exact 5 byte, giải ra (độ dài, mã loại)
      2. Mã loại không có trong FrameType -> FrameError
      3. Độ dài vượt max_payload_for(loại) -> FrameError, KHÔNG đọc phần nội dung
      4. recv_exact(độ dài)
    """
    raise NotImplementedError("T04 · R1")
