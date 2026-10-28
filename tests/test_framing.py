"""Kiểm thử module đóng khung — docs/08 ca KT-01 đến KT-04, nhiệm vụ T04.

Nguyên tắc: không mở socket thật (quy ước ở tests/README.md). Thay vào đó dùng
SocketGia — một đối tượng chỉ có hai phương thức recv và sendall, nhưng cho
phép điều khiển chính xác thứ mà socket thật không điều khiển được: recv trả về
bao nhiêu byte mỗi lần. Đó chính là tình huống cần kiểm.

Mọi con số hex trong file này chép từ docs/03 mục 5. Nếu một ngày test đỏ ở
phần đó thì hoặc code sai, hoặc có người sửa đặc tả mà quên sửa code.
"""
import struct

import pytest

from truyennhanh.protocol.constants import (
    FRAME_HEADER_SIZE,
    MAX_CONTROL_PAYLOAD,
    MAX_DATA_PAYLOAD,
    FrameType,
)
from truyennhanh.protocol.framing import (
    ConnectionClosed,
    FrameError,
    encode_frame,
    max_payload_for,
    read_frame,
    recv_exact,
    send_frame,
)

# --------------------------------------------------------------------------- Đồ giả


class SocketGia:
    """Socket giả, chỉ đủ dùng cho framing: recv và sendall.

    Tham số:
        du_lieu   : dòng byte mà recv sẽ lần lượt trả về
        moi_lan   : mỗi lần recv trả về tối đa chừng này byte; None = trả hết
                    những gì được yêu cầu. Đặt 1 để mô phỏng mạng chậm, cắt vụn.
        dong_som  : sau khi đã trả hết du_lieu, recv trả về b"" (đối phương đóng)

    Thuộc tính kiểm tra được sau khi chạy:
        da_gui    : toàn bộ byte đã đi qua sendall
        so_lan_recv : đếm số lần recv được gọi
        da_doc    : số byte đã bị đọc ra khỏi dòng
    """

    def __init__(self, du_lieu: bytes = b"", moi_lan: int | None = None) -> None:
        self._du_lieu = bytes(du_lieu)
        self._vi_tri = 0
        self._moi_lan = moi_lan
        self.da_gui = bytearray()
        self.so_lan_recv = 0

    def recv(self, n: int) -> bytes:
        self.so_lan_recv += 1
        if self._moi_lan is not None:
            n = min(n, self._moi_lan)
        mau = self._du_lieu[self._vi_tri : self._vi_tri + n]
        self._vi_tri += len(mau)
        return mau

    def sendall(self, data: bytes) -> None:
        self.da_gui.extend(data)

    @property
    def da_doc(self) -> int:
        return self._vi_tri


# --------------------------------------------------------------------------- Ví dụ trong đặc tả

ACCEPT_JSON = (
    b'{"transfer_id":"0b8c5c5e-2f7d-4c5a-9e61-3a2d7c1f9b40","offset":0}'
)

KHUNG_ACCEPT_TRONG_DAC_TA = bytes.fromhex(
    "00 00 00 41 02 7b 22 74 72 61 6e 73 66 65 72 5f"
    "69 64 22 3a 22 30 62 38 63 35 63 35 65 2d 32 66"
    "37 64 2d 34 63 35 61 2d 39 65 36 31 2d 33 61 32"
    "64 37 63 31 66 39 62 34 30 22 2c 22 6f 66 66 73"
    "65 74 22 3a 30 7d".replace(" ", "")
)


def test_spec_example_bytes_are_self_consistent():
    """Bản thân ví dụ hex trong docs/03 mục 5 phải đúng: 70 byte, 5 byte đầu + 65 byte JSON."""
    assert len(KHUNG_ACCEPT_TRONG_DAC_TA) == 70
    assert KHUNG_ACCEPT_TRONG_DAC_TA[FRAME_HEADER_SIZE:] == ACCEPT_JSON
    assert len(ACCEPT_JSON) == 0x41 == 65


def test_encode_frame_matches_spec_hex_example():
    """KT-03 · docs/03 mục 5: encode_frame phải khớp từng byte ví dụ ACCEPT."""
    assert encode_frame(FrameType.ACCEPT, ACCEPT_JSON) == KHUNG_ACCEPT_TRONG_DAC_TA


@pytest.mark.parametrize(
    ("frame_type", "payload_len", "header_hex"),
    [
        (FrameType.OFFER, 253, "000000fd01"),       # OFFER ở docs/03 mục 4.3
        (FrameType.DATA, 64 * 1024, "0001000004"),  # một khối DATA 64 KiB
        (FrameType.DONE, 54, "0000003605"),         # DONE
    ],
)
def test_frame_headers_match_spec_table(frame_type, payload_len, header_hex):
    """docs/03 mục 5, bảng "Phần đầu các khung khác"."""
    khung = encode_frame(frame_type, b"x" * payload_len)
    assert khung[:FRAME_HEADER_SIZE] == bytes.fromhex(header_hex)
    assert len(khung) == FRAME_HEADER_SIZE + payload_len


def test_payload_length_is_counted_in_bytes_not_characters():
    """docs/03 mục 5: chữ "báo" có 3 ký tự nhưng chiếm 4 byte UTF-8.

    Đây là lỗi dễ mắc nhất khi tính độ dài khung, và chỉ lộ ra với tên file
    tiếng Việt — tức là gần như mọi file trong đồ án này.
    """
    assert "báo".encode("utf-8") == bytes.fromhex("62c3a16f")

    payload = "báo cáo.pdf".encode("utf-8")
    assert len(payload) == 13 and len("báo cáo.pdf") == 11

    khung = encode_frame(FrameType.DONE, payload)
    (do_dai,) = struct.unpack(">I", khung[:4])
    assert do_dai == 13


# --------------------------------------------------------------------------- recv_exact


def test_recv_exact_joins_partial_reads():
    """KT-01 · recv trả về từng 1 byte một thì vẫn phải ghép đủ.

    Socket thật trên mạng LAN gần như luôn trả về đủ, nên lỗi "quên lặp recv"
    chỉ lộ ra khi file lớn hoặc mạng chậm — lúc demo trước thầy. Đồ giả ép
    tình huống đó xảy ra ngay trong CI.
    """
    sock = SocketGia(bytes(range(100)), moi_lan=1)

    assert recv_exact(sock, 100) == bytes(range(100))
    assert sock.so_lan_recv == 100


@pytest.mark.parametrize("moi_lan", [1, 3, 7, 64, None])
def test_recv_exact_works_for_any_chunking(moi_lan):
    """Kết quả không được phụ thuộc vào việc mạng cắt dòng byte ra sao."""
    du_lieu = bytes(range(256)) * 4
    sock = SocketGia(du_lieu, moi_lan=moi_lan)

    assert recv_exact(sock, len(du_lieu)) == du_lieu


def test_recv_exact_raises_connection_closed_when_peer_disconnects():
    """KT-02 · Đối phương đóng giữa chừng: recv trả về b"", phải ném ConnectionClosed.

    Không được trả về dữ liệu thiếu, vì bên gọi sẽ tưởng đã đọc đủ và giải mã
    một khung cụt.
    """
    sock = SocketGia(b"chi co 10", moi_lan=1)  # 9 byte, nhưng đòi 20

    with pytest.raises(ConnectionClosed) as loi:
        recv_exact(sock, 20)

    assert "11/20" in str(loi.value)  # còn thiếu 11 trên tổng 20


def test_recv_exact_returns_empty_without_calling_recv_for_zero_bytes():
    """n = 0 phải trả b"" ngay. Gọi recv(0) sẽ trả b"" và bị hiểu nhầm là đã đóng."""
    sock = SocketGia(b"abc")

    assert recv_exact(sock, 0) == b""
    assert sock.so_lan_recv == 0


def test_recv_exact_rejects_negative_length():
    with pytest.raises(ValueError):
        recv_exact(SocketGia(), -1)


# --------------------------------------------------------------------------- read_frame


def test_read_frame_reads_a_whole_frame():
    sock = SocketGia(encode_frame(FrameType.ACCEPT, ACCEPT_JSON))

    assert read_frame(sock) == (FrameType.ACCEPT, ACCEPT_JSON)


def test_read_frame_handles_a_frame_split_in_half():
    """Khung bị cắt đôi — tiêu chí T04.

    Mô phỏng bằng cách bắt recv trả về từng 1 byte: phần đầu khung bị cắt làm 5
    mẩu, nội dung bị cắt làm 65 mẩu. Nếu read_frame đọc đúng thì vẫn ra nguyên khung.
    """
    sock = SocketGia(encode_frame(FrameType.ACCEPT, ACCEPT_JSON), moi_lan=1)

    assert read_frame(sock) == (FrameType.ACCEPT, ACCEPT_JSON)
    assert sock.so_lan_recv == 70


def test_read_frame_reads_frames_back_to_back():
    """Nhiều khung nối nhau trong cùng một dòng byte phải tách đúng chỗ.

    Đây là lý do tồn tại của việc đóng khung: TCP không giữ ranh giới thông điệp.
    """
    dong_byte = (
        encode_frame(FrameType.OFFER, b'{"v":1}')
        + encode_frame(FrameType.DATA, b"\x00\xff" * 10)
        + encode_frame(FrameType.DONE, b"")
    )
    sock = SocketGia(dong_byte, moi_lan=3)

    assert read_frame(sock) == (FrameType.OFFER, b'{"v":1}')
    assert read_frame(sock) == (FrameType.DATA, b"\x00\xff" * 10)
    assert read_frame(sock) == (FrameType.DONE, b"")


def test_read_frame_raises_connection_closed_on_truncated_header():
    """Kết nối đứt khi mới nhận được 3 trong 5 byte đầu."""
    sock = SocketGia(encode_frame(FrameType.DONE, b"")[:3])

    with pytest.raises(ConnectionClosed):
        read_frame(sock)


def test_read_frame_rejects_unknown_frame_type():
    """Loại khung lạ — tiêu chí T04 và docs/03 mục 4.2.

    Mã 0x09 chưa được định nghĩa. Bên nhận phải báo lỗi chứ không được đoán.
    """
    sock = SocketGia(struct.pack(">IB", 0, 0x09))

    with pytest.raises(FrameError) as loi:
        read_frame(sock)

    assert "0x09" in str(loi.value)


# --------------------------------------------------------------------------- Giới hạn độ dài


def test_read_frame_rejects_oversized_length_without_reading_payload():
    """KT-04 · Khung khai độ dài 4 GB: phải ném FrameError mà KHÔNG đọc nội dung.

    Đây là ca kiểm thử quan trọng nhất của module. Kẻ xấu chỉ cần gửi 5 byte
    khai độ dài 4 GB; nếu read_frame đọc trước rồi mới kiểm tra thì bên nhận
    cố cấp phát 4 GB bộ nhớ và chết (docs/03 mục 4.9 điểm 1).

    Cách kiểm chứng: dòng byte CHỈ chứa 5 byte đầu, không có nội dung. Nếu code
    sai thứ tự, nó sẽ chờ đọc nội dung và ném ConnectionClosed thay vì FrameError.
    Đồng thời kiểm luôn số byte đã bị đọc đúng bằng 5.
    """
    sock = SocketGia(struct.pack(">IB", 4_000_000_000, FrameType.DATA))

    with pytest.raises(FrameError) as loi:
        read_frame(sock)

    assert sock.da_doc == FRAME_HEADER_SIZE
    assert "4000000000" in str(loi.value).replace(" ", "")


def test_read_frame_rejects_control_frame_over_64_kib():
    """Khung điều khiển chỉ được tới 64 KiB, kể cả khi dưới giới hạn của DATA."""
    sock = SocketGia(struct.pack(">IB", MAX_CONTROL_PAYLOAD + 1, FrameType.OFFER))

    with pytest.raises(FrameError):
        read_frame(sock)

    assert sock.da_doc == FRAME_HEADER_SIZE


def test_read_frame_accepts_control_frame_exactly_at_the_limit():
    """Đúng 64 KiB vẫn hợp lệ — ranh giới phải là "vượt quá" chứ không phải "bằng"."""
    payload = b"k" * MAX_CONTROL_PAYLOAD
    sock = SocketGia(encode_frame(FrameType.REJECT, payload))

    loai, nhan_duoc = read_frame(sock)

    assert loai is FrameType.REJECT
    assert nhan_duoc == payload


def test_data_frame_may_be_as_large_as_16_mib():
    """Khung lớn nhất cho phép — tiêu chí T04."""
    payload = b"\xa5" * MAX_DATA_PAYLOAD
    sock = SocketGia(encode_frame(FrameType.DATA, payload))

    loai, nhan_duoc = read_frame(sock)

    assert loai is FrameType.DATA
    assert len(nhan_duoc) == MAX_DATA_PAYLOAD


def test_encode_frame_rejects_oversized_payload():
    """Lỗi phải bị bắt ngay từ phía gửi, không để đẩy khung hỏng lên mạng."""
    with pytest.raises(FrameError):
        encode_frame(FrameType.CANCEL, b"x" * (MAX_CONTROL_PAYLOAD + 1))

    with pytest.raises(FrameError):
        encode_frame(FrameType.DATA, b"x" * (MAX_DATA_PAYLOAD + 1))


def test_max_payload_for_distinguishes_data_from_control_frames():
    assert max_payload_for(FrameType.DATA) == MAX_DATA_PAYLOAD == 16 * 1024 * 1024
    for loai in FrameType:
        if loai is not FrameType.DATA:
            assert max_payload_for(loai) == MAX_CONTROL_PAYLOAD == 64 * 1024


# --------------------------------------------------------------------------- Khung rỗng


@pytest.mark.parametrize(
    "loai", [t for t in FrameType if t is not FrameType.DATA]
)
def test_control_frames_may_be_empty(loai):
    """Khung rỗng — tiêu chí T04. Nội dung 0 byte là hợp lệ với mọi khung trừ DATA."""
    sock = SocketGia(encode_frame(loai, b""))

    assert read_frame(sock) == (loai, b"")


def test_empty_data_frame_is_rejected():
    """docs/03 mục 4.1: DATA dài 1 đến 16 MiB, nên khung DATA rỗng là vi phạm.

    File rỗng vẫn gửi được: bên gửi không gửi khung DATA nào, chỉ gửi thẳng DONE.
    """
    with pytest.raises(FrameError):
        encode_frame(FrameType.DATA, b"")

    sock = SocketGia(struct.pack(">IB", 0, FrameType.DATA))
    with pytest.raises(FrameError):
        read_frame(sock)


# --------------------------------------------------------------------------- send_frame


def test_send_frame_writes_the_encoded_frame():
    sock = SocketGia()

    send_frame(sock, FrameType.ACCEPT, ACCEPT_JSON)

    assert bytes(sock.da_gui) == KHUNG_ACCEPT_TRONG_DAC_TA


def test_send_frame_uses_a_single_sendall_call():
    """Phần đầu và nội dung phải đi trong MỘT lần gọi, không tách làm hai.

    Tách làm hai thì mỗi khung tốn thêm một lượt đi về trên mạng, và khi gửi
    hàng nghìn khung DATA thì chi phí đó cộng dồn thấy rõ trong thí nghiệm E1.
    """
    so_lan = 0

    class DemSendall(SocketGia):
        def sendall(self, data):
            nonlocal so_lan
            so_lan += 1
            super().sendall(data)

    send_frame(DemSendall(), FrameType.DONE, b'{"transfer_id":"x"}')

    assert so_lan == 1


def test_send_then_read_round_trip():
    """Gửi rồi đọc lại phải ra đúng thứ đã gửi, với mọi loại khung."""
    sock = SocketGia()
    goi = [
        (FrameType.OFFER, b'{"v":1,"name":"b\xc3\xa1o c\xc3\xa1o.pdf"}'),
        (FrameType.ACCEPT, ACCEPT_JSON),
        (FrameType.DATA, bytes(range(256))),
        (FrameType.DONE, b""),
        (FrameType.RESULT, b'{"ok":true}'),
    ]
    for loai, noi_dung in goi:
        send_frame(sock, loai, noi_dung)

    doc_lai = SocketGia(bytes(sock.da_gui), moi_lan=5)

    assert [read_frame(doc_lai) for _ in goi] == goi
