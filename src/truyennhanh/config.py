"""Cấu hình người dùng đổi được. Phụ trách: R1.

Giá trị giao thức không đổi được (cổng dò tìm, giới hạn khung...) nằm ở protocol/constants.py.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from truyennhanh.protocol.constants import DEFAULT_CHUNK_SIZE, DISCOVERY_PORT, TRANSFER_PORT_DEFAULT


@dataclass
class Config:
    """device_name=None: dùng tên máy (socket.gethostname()).
    download_dir=None : dùng default_download_dir().
    transfer_port=0   : để hệ điều hành chọn cổng trống (dùng trong test tích hợp).
    """

    device_name: str | None = None
    download_dir: Path | None = None
    discovery_port: int = DISCOVERY_PORT
    transfer_port: int = TRANSFER_PORT_DEFAULT
    chunk_size: int = DEFAULT_CHUNK_SIZE


def default_download_dir() -> Path:
    """<thư mục người dùng>/Downloads/TruyenNhanh — tạo nếu chưa có."""
    raise NotImplementedError("T14 · R1")
