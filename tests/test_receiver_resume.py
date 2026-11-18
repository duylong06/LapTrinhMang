"""Truyền tiếp qua bên nhận thật — docs/03 mục 4.5 (T27).

Tách khỏi tests/test_receiver.py (của R4, kiểm T20/T21) để hai phần không
giẫm lên nhau khi sửa.

Bài quan trọng nhất ở đây là test_truyen_tiep_bam_ca_phan_da_co: khi nối lại,
bên nhận phải nạp phần đã nằm trong .part vào bộ băm trước khi băm tiếp. Bắt
đầu bằng một bộ băm rỗng thì mã băm cuối luôn lệch, bên nhận báo hash_mismatch
và xóa mất phần đã nhận — đúng thứ mà truyền tiếp sinh ra để tránh.
"""
from __future__ import annotations

import hashlib
import queue
import socket
import uuid

import pytest

from truyennhanh.config import Config
from truyennhanh.core.events import TransferFinished
from truyennhanh.protocol.constants import FrameType, Reason
from truyennhanh.protocol.framing import read_frame, send_frame
from truyennhanh.protocol.messages import (
    Offer,
    make_done,
    make_offer,
    parse_accept,
    parse_reject,
    parse_result,
)
from truyennhanh.transfer.receiver import FileReceiverServer
from truyennhanh.transfer.storage import part_path

TIMEOUT_S = 5.0


class May:
    """Bên nhận đang chạy, kèm thư mục lưu và sổ ghi các lần hỏi người dùng."""

    def __init__(self, thu_muc, tra_loi=True):
        self.thu_muc = thu_muc
        self.su_kien: queue.Queue = queue.Queue()
        self.da_hoi: list[tuple] = []
        self.server = FileReceiverServer(
            Config(download_dir=thu_muc, transfer_port=0),
            self.su_kien.put,
            self._hoi,
        )
        self._tra_loi = tra_loi
        self.cong = self.server.start()

    def _hoi(self, offer, ten_sach, offset):
        self.da_hoi.append((ten_sach, offset))
        return self._tra_loi

    def noi(self) -> socket.socket:
        s = socket.create_connection(("127.0.0.1", self.cong), timeout=TIMEOUT_S)
        s.settimeout(TIMEOUT_S)
        return s

    def cho_ket_thuc(self, timeout=TIMEOUT_S):
        """Chờ TransferFinished — cũng là lúc bên nhận đã nhả khóa mã băm."""
        try:
            while True:
                su_kien = self.su_kien.get(timeout=timeout)
                if isinstance(su_kien, TransferFinished):
                    return su_kien
        except queue.Empty:
            raise AssertionError("không thấy TransferFinished sau khi kết nối đứt")

    def dong(self):
        self.server.stop()


@pytest.fixture
def may(tmp_path):
    m = May(tmp_path / "nhan")
    yield m
    m.dong()


def tao_offer(noi_dung: bytes, ten="a.txt", sender_id=None) -> Offer:
    return Offer(
        transfer_id=str(uuid.uuid4()),
        sender_id=sender_id or str(uuid.uuid4()),
        sender_name="MAY-GUI",
        name=ten,
        size=len(noi_dung),
        sha256=hashlib.sha256(noi_dung).hexdigest(),
    )


def gui_roi_dut(may: May, offer: Offer, noi_dung: bytes, den_byte: int) -> int:
    """Gửi tới byte thứ den_byte rồi đóng kết nối đột ngột, như khi rớt mạng.

    Gửi tiếp từ đúng offset mà bên nhận trả về, không gửi lại từ đầu: gửi thừa
    thì bên nhận huỷ với lý do bad_request (docs/03 mục 4.9 bước 6).
    """
    s = may.noi()
    send_frame(s, FrameType.OFFER, make_offer(offer))
    _, payload = read_frame(s)
    offset = parse_accept(payload, offer.transfer_id, offer.size)
    send_frame(s, FrameType.DATA, noi_dung[offset:den_byte])
    s.close()
    may.cho_ket_thuc()
    return offset


def test_truyen_tiep_bam_ca_phan_da_co(may):
    """Nối lại giữa chừng thì file cuối phải đúng và mã băm phải khớp."""
    noi_dung = bytes(range(256)) * 400          # 102 400 byte, nội dung không lặp đơn điệu
    offer = tao_offer(noi_dung)

    gui_roi_dut(may, offer, noi_dung, 40_000)
    assert part_path(may.thu_muc, offer.sha256).stat().st_size == 40_000

    with may.noi() as s:
        send_frame(s, FrameType.OFFER, make_offer(offer))
        _, payload = read_frame(s)
        offset = parse_accept(payload, offer.transfer_id, offer.size)
        assert offset == 40_000, "phải tiếp từ đúng chỗ đứt"

        send_frame(s, FrameType.DATA, noi_dung[offset:])
        send_frame(s, FrameType.DONE, make_done(offer.transfer_id))
        _, payload = read_frame(s)
        ok, ly_do = parse_result(payload, offer.transfer_id)

    assert ok is True, f"mã băm phải khớp, nhưng nhận được {ly_do}"
    assert (may.thu_muc / "a.txt").read_bytes() == noi_dung


def test_truyen_tiep_nhieu_lan_lien_tiep(may):
    """Rớt mạng ba lần vẫn phải ra đúng file."""
    noi_dung = bytes(range(256)) * 200
    offer = tao_offer(noi_dung)

    for den in (20_000, 35_000, 48_000):
        gui_roi_dut(may, offer, noi_dung, den)
        assert part_path(may.thu_muc, offer.sha256).stat().st_size == den

    with may.noi() as s:
        send_frame(s, FrameType.OFFER, make_offer(offer))
        _, payload = read_frame(s)
        offset = parse_accept(payload, offer.transfer_id, offer.size)
        send_frame(s, FrameType.DATA, noi_dung[offset:])
        send_frame(s, FrameType.DONE, make_done(offer.transfer_id))
        _, payload = read_frame(s)
        ok, _ = parse_result(payload, offer.transfer_id)

    assert ok is True
    assert (may.thu_muc / "a.txt").read_bytes() == noi_dung


def test_khong_hoi_lai_nguoi_dung_khi_noi_lai(may):
    """docs/03 mục 4.5: cùng sender_id và cùng sha256 thì tự đồng ý."""
    noi_dung = b"z" * 30_000
    offer = tao_offer(noi_dung, sender_id="may-gui-co-dinh")

    gui_roi_dut(may, offer, noi_dung, 10_000)
    so_lan_hoi = len(may.da_hoi)

    with may.noi() as s:
        send_frame(s, FrameType.OFFER, make_offer(offer))
        read_frame(s)
    assert len(may.da_hoi) == so_lan_hoi, "nối lại cùng file từ cùng máy thì không được hỏi lại"


def test_part_hong_dai_hon_size_thi_nhan_lai_tu_dau(may):
    noi_dung = b"w" * 5_000
    offer = tao_offer(noi_dung)
    part_path(may.thu_muc, offer.sha256).write_bytes(b"?" * 9_000)

    with may.noi() as s:
        send_frame(s, FrameType.OFFER, make_offer(offer))
        _, payload = read_frame(s)
        assert parse_accept(payload, offer.transfer_id, offer.size) == 0

        send_frame(s, FrameType.DATA, noi_dung)
        send_frame(s, FrameType.DONE, make_done(offer.transfer_id))
        _, payload = read_frame(s)
        ok, _ = parse_result(payload, offer.transfer_id)

    assert ok is True
    assert (may.thu_muc / "a.txt").read_bytes() == noi_dung


def test_hai_luot_cung_ma_bam_thi_luot_sau_bi_busy(may):
    """T28 bước 8 mục 4.9."""
    noi_dung = b"x" * 5_000
    o1 = tao_offer(noi_dung)
    o2 = tao_offer(noi_dung)            # cùng nội dung -> cùng sha256

    with may.noi() as a, may.noi() as b:
        send_frame(a, FrameType.OFFER, make_offer(o1))
        read_frame(a)                                    # a giữ khóa
        send_frame(b, FrameType.OFFER, make_offer(o2))
        loai, payload = read_frame(b)
        ly_do, _ = parse_reject(payload, o2.transfer_id)

    assert loai is FrameType.REJECT
    assert ly_do is Reason.BUSY


def test_nha_khoa_sau_khi_dut_de_con_truyen_tiep(may):
    """Không nhả khóa thì mã băm đó bị kẹt và mọi lần nối lại đều nhận busy."""
    noi_dung = b"k" * 8_000
    offer = tao_offer(noi_dung)

    gui_roi_dut(may, offer, noi_dung, 3_000)

    with may.noi() as s:
        send_frame(s, FrameType.OFFER, make_offer(offer))
        loai, payload = read_frame(s)
    assert loai is FrameType.ACCEPT, "khóa phải được nhả khi kết nối đứt"
