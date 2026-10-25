"""Hằng số giao thức Truyền Nhanh — bản code của docs/03-dac-ta-giao-thuc.md.

Phụ trách: R1. File này là HỢP ĐỒNG chung: mọi giá trị ở đây phải khớp đặc tả.
Muốn đổi giá trị nào thì sửa docs/03 trước, qua PR do R1 duyệt.
"""
from __future__ import annotations

from enum import Enum, IntEnum

PROTOCOL_NAME = "truyennhanh"
PROTOCOL_VERSION = 1

# --------------------------------------------------------------------------- Dò tìm (mục 3)
DISCOVERY_PORT = 50505
BROADCAST_ADDRESS = "255.255.255.255"
ANNOUNCE_INTERVAL_S = 2.0
PEER_TIMEOUT_S = 7.0
MAX_DATAGRAM_BYTES = 1024
MAX_NAME_CHARS = 64


class DiscoveryType(str, Enum):
    """Loại gói dò tìm (mục 3.3)."""

    DISCOVER = "DISCOVER"
    ANNOUNCE = "ANNOUNCE"
    BYE = "BYE"


# --------------------------------------------------------------------------- Khung TCP (mục 4.1)
TRANSFER_PORT_DEFAULT = 50506

FRAME_HEADER_FORMAT = ">IB"
"""Định dạng struct của phần đầu khung: 4 byte độ dài nội dung (không dấu, big-endian) + 1 byte loại."""

FRAME_HEADER_SIZE = 5
MAX_CONTROL_PAYLOAD = 64 * 1024          # mọi loại khung trừ DATA
MAX_DATA_PAYLOAD = 16 * 1024 * 1024      # khung DATA
DEFAULT_CHUNK_SIZE = 64 * 1024           # tạm thời — chốt lại bằng thí nghiệm E1 ở T35


class FrameType(IntEnum):
    """Loại khung (mục 4.2)."""

    OFFER = 0x01
    ACCEPT = 0x02
    REJECT = 0x03
    DATA = 0x04
    DONE = 0x05
    RESULT = 0x06
    CANCEL = 0x07


class Reason(str, Enum):
    """Mã lý do trong REJECT, CANCEL, RESULT (mục 4.8)."""

    USER_DECLINED = "user_declined"
    TIMEOUT = "timeout"
    BUSY = "busy"
    INSUFFICIENT_SPACE = "insufficient_space"
    UNSUPPORTED_VERSION = "unsupported_version"
    BAD_REQUEST = "bad_request"
    HASH_MISMATCH = "hash_mismatch"
    INCOMPLETE = "incomplete"
    CANCELLED = "cancelled"
    SHUTTING_DOWN = "shutting_down"


SHA256_HEX_LENGTH = 64

# --------------------------------------------------------------------------- Hết giờ (mục 4.7)
CONNECT_TIMEOUT_S = 5.0
DECISION_TIMEOUT_S = 60.0          # bên nhận chờ người dùng
ACCEPT_WAIT_TIMEOUT_S = 65.0       # bên gửi chờ ACCEPT/REJECT — phải lớn hơn DECISION_TIMEOUT_S
IDLE_TIMEOUT_S = 15.0
RESULT_WAIT_TIMEOUT_S = 60.0
RETRY_DELAYS_S = (1, 2, 4, 8, 16)

# --------------------------------------------------------------------------- Lưu trữ (mục 4.5, 4.9)
PART_DIR_NAME = ".truyennhanh"
PART_SUFFIX = ".part"
PART_MAX_AGE_DAYS = 7

MAX_FILENAME_BYTES = 200
FALLBACK_FILENAME = "file-nhan-duoc"
FORBIDDEN_FILENAME_CHARS = '<>:"/\\|?*'
WINDOWS_RESERVED_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{i}" for i in range(1, 10)}
    | {f"LPT{i}" for i in range(1, 10)}
)

# --------------------------------------------------------------------------- Giao diện
PROGRESS_MAX_PER_SECOND = 10       # TransferProgress tối đa 10 lần mỗi giây mỗi lượt
