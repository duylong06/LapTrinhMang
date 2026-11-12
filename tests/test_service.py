"""Kiểm thử lõi TruyenNhanhService với thành phần giả — nhiệm vụ T14.

Phần mạng thật (dò tìm, gửi, nhận) chưa có, nên ở đây tiêm vào các lớp giả
chỉ ghi lại xem lõi gọi chúng thế nào. Nhờ vậy kiểm được đúng phần việc của
lõi: vòng đời luồng, hàng đợi sự kiện, sổ sách lượt truyền và cơ chế chờ
quyết định người dùng.
"""
from __future__ import annotations

import threading

import pytest

from truyennhanh.config import Config
from truyennhanh.core import service as service_module
from truyennhanh.core.events import StatusMessage, TransferFinished
from truyennhanh.core.models import Direction, Peer, Transfer, TransferState
from truyennhanh.core.service import TruyenNhanhService
from truyennhanh.protocol.constants import Reason


# --------------------------------------------------------------------------- Thành phần giả

class FakeDiscovery:
    """Dò tìm giả: ghi lại lời gọi, trả về danh sách máy dựng sẵn."""

    def __init__(self, peers=None):
        self._peers = list(peers or [])
        self.started_with_port = None
        self.stopped = False
        self.refresh_count = 0

    def start(self, tcp_port):
        self.started_with_port = tcp_port

    def stop(self):
        self.stopped = True

    def refresh(self):
        self.refresh_count += 1

    def peers(self):
        return list(self._peers)


class FakeReceiver:
    """Máy chủ nhận giả. Trả về một cổng khác cổng xin, để kiểm lõi dùng cổng THẬT."""

    def __init__(self, real_port=54321):
        self.real_port = real_port
        self.started = False
        self.stopped = False

    def start(self):
        self.started = True
        return self.real_port

    def stop(self):
        self.stopped = True


class FakeSender:
    """Bên gửi giả: chạy xong ngay và tự báo kết thúc, như bên gửi thật phải làm."""

    def __init__(self, service):
        self.service = service
        self.jobs = []
        self.ran = threading.Event()

    def send(self, job):
        self.jobs.append(job)
        self.service._finish(job.transfer_id, ok=True)
        self.ran.set()


class StuckSender:
    """Bên gửi hỏng: chặn mãi và không thèm nhìn cờ hủy. Dùng để kiểm stop() không treo."""

    def __init__(self):
        self.entered = threading.Event()
        self.release = threading.Event()

    def send(self, job):
        self.entered.set()
        self.release.wait(30)


# --------------------------------------------------------------------------- Dụng cụ chung

PEER = Peer(id="peer-1", name="PC-PHONGMAY-07", ip="192.168.1.9", tcp_port=50506)


def lay_su_kien(svc):
    """Vét sạch hàng đợi thành một danh sách."""
    out = []
    while not svc.events.empty():
        out.append(svc.events.get_nowait())
    return out


@pytest.fixture
def tmp_config(tmp_path):
    """Config trỏ thư mục nhận vào tmp_path, để test không đụng Downloads thật."""
    return Config(device_name="MAY-TEST", download_dir=tmp_path, transfer_port=0)


# --------------------------------------------------------------------------- Vòng đời

def test_start_bat_ben_nhan_truoc_roi_moi_bat_do_tim(tmp_config):
    """Dò tìm phải nhận được cổng THẬT của bên nhận, nên bên nhận chạy trước."""
    discovery, receiver = FakeDiscovery(), FakeReceiver(real_port=54321)
    svc = TruyenNhanhService(tmp_config, discovery=discovery, receiver=receiver)

    svc.start()

    assert receiver.started
    assert discovery.started_with_port == 54321, "dò tìm phải lấy cổng thật, không lấy cổng đã xin"
    svc.stop()


def test_start_va_stop_goi_nhieu_lan_khong_sao(tmp_config):
    receiver = FakeReceiver()
    svc = TruyenNhanhService(tmp_config, receiver=receiver)

    svc.start()
    svc.start()
    svc.stop()
    svc.stop()

    assert receiver.started and receiver.stopped


def test_stop_khong_treo_du_luong_gui_bi_ket(tmp_config, monkeypatch):
    """Một luồng kẹt không được phép giữ cả ứng dụng lại khi người dùng bấm đóng."""
    monkeypatch.setattr(service_module, "STOP_JOIN_TIMEOUT_S", 0.2)

    sender = StuckSender()
    svc = TruyenNhanhService(tmp_config, discovery=FakeDiscovery([PEER]), sender=sender)
    svc.start()

    file = svc.get_download_dir() / "a.txt"
    file.write_bytes(b"xin chao")
    svc.send_file(PEER.id, file)
    assert sender.entered.wait(2), "luồng gửi chưa kịp chạy"

    xong = threading.Event()
    threading.Thread(target=lambda: (svc.stop(), xong.set()), daemon=True).start()

    assert xong.wait(5), "stop() bị treo"
    assert any(
        isinstance(e, StatusMessage) and "chưa kết thúc" in e.text
        for e in lay_su_kien(svc)
    ), "stop() phải nói rõ luồng nào chưa chịu dừng"
    sender.release.set()


def test_stop_huy_luot_dang_chay_voi_ly_do_shutting_down(tmp_config):
    svc = TruyenNhanhService(tmp_config)
    svc.start()
    svc._track(Transfer(
        id="t-1", direction=Direction.RECEIVE, peer_name="X",
        file_name="a.bin", size=10, state=TransferState.ACTIVE,
    ))
    lay_su_kien(svc)

    svc.stop()

    ket_thuc = [e for e in lay_su_kien(svc) if isinstance(e, TransferFinished)]
    assert len(ket_thuc) == 1
    assert ket_thuc[0].ok is False
    assert ket_thuc[0].reason is Reason.SHUTTING_DOWN


# --------------------------------------------------------------------------- Sự kiện

def test_su_kien_di_qua_hang_doi(tmp_config):
    """docs/02 mục 4 luật 3: lõi không gọi thẳng giao diện, chỉ đẩy vào queue."""
    svc = TruyenNhanhService(tmp_config)

    svc.start()

    assert any(isinstance(e, StatusMessage) for e in lay_su_kien(svc))


def test_ket_thuc_mot_luot_chi_phat_dung_mot_su_kien(tmp_config):
    """Vừa bị hủy vừa gặp lỗi mạng cũng chỉ được hiện một dòng trên giao diện."""
    svc = TruyenNhanhService(tmp_config)
    svc._track(Transfer(
        id="t-2", direction=Direction.SEND, peer_name="X",
        file_name="a.bin", size=10, state=TransferState.ACTIVE,
    ))

    svc._finish("t-2", ok=False, reason=Reason.CANCELLED)
    svc._finish("t-2", ok=True)

    assert len([e for e in lay_su_kien(svc) if isinstance(e, TransferFinished)]) == 1


# --------------------------------------------------------------------------- Quyết định của người dùng

def test_respond_to_offer_mo_khoa_luong_nhan_dang_cho(tmp_config):
    """docs/02 mục 4 luật 4: luồng nhận chờ trên Event, giao diện mở khóa."""
    svc = TruyenNhanhService(tmp_config)
    decision = svc._register_decision("t-3")
    ket_qua = []

    threading.Thread(target=lambda: ket_qua.append(decision.wait(5)), daemon=True).start()
    svc.respond_to_offer("t-3", True)

    for _ in range(50):
        if ket_qua:
            break
        threading.Event().wait(0.02)
    assert ket_qua == [True]


def test_respond_to_offer_sau_khi_het_gio_thi_lang_le_bo_qua(tmp_config):
    """Người dùng bấm muộn không được làm hỏng hàm xử lý nút bấm."""
    svc = TruyenNhanhService(tmp_config)

    svc.respond_to_offer("khong-ton-tai", True)      # không được ném lỗi


def test_cancel_bat_co_huy_cua_luot_do(tmp_config):
    svc = TruyenNhanhService(tmp_config)
    co = svc._track(Transfer(
        id="t-4", direction=Direction.SEND, peer_name="X",
        file_name="a.bin", size=10,
    ))

    svc.cancel("t-4")

    assert co.is_set()


# --------------------------------------------------------------------------- Gửi file

def test_send_file_tra_ve_ngay_va_chay_tren_luong_rieng(tmp_config, tmp_path):
    svc = TruyenNhanhService(tmp_config, discovery=FakeDiscovery([PEER]))
    sender = FakeSender(svc)
    svc._sender = sender
    file = tmp_path / "bao_cao.pdf"
    file.write_bytes(b"x" * 100)

    transfer_id = svc.send_file(PEER.id, file)

    assert sender.ran.wait(2), "bên gửi chưa được gọi"
    assert sender.jobs[0].transfer_id == transfer_id
    assert sender.jobs[0].peer == PEER
    assert sender.jobs[0].cancelled.is_set() is False


def test_send_file_khi_chua_noi_ben_gui_thi_bao_ngay(tmp_config, tmp_path):
    svc = TruyenNhanhService(tmp_config, discovery=FakeDiscovery([PEER]))
    file = tmp_path / "a.txt"
    file.write_bytes(b"a")

    with pytest.raises(RuntimeError, match="R3"):
        svc.send_file(PEER.id, file)


def test_send_file_voi_may_khong_co_trong_danh_sach(tmp_config, tmp_path):
    svc = TruyenNhanhService(tmp_config, discovery=FakeDiscovery([]))
    svc._sender = FakeSender(svc)
    file = tmp_path / "a.txt"
    file.write_bytes(b"a")

    with pytest.raises(ValueError, match="khong-co|không có"):
        svc.send_file("khong-co", file)


def test_send_file_voi_file_khong_ton_tai(tmp_config, tmp_path):
    svc = TruyenNhanhService(tmp_config, discovery=FakeDiscovery([PEER]))
    svc._sender = FakeSender(svc)

    with pytest.raises(ValueError):
        svc.send_file(PEER.id, tmp_path / "khong-co-file-nay.txt")


def test_list_transfers_moi_nhat_dung_dau(tmp_config, tmp_path):
    svc = TruyenNhanhService(tmp_config, discovery=FakeDiscovery([PEER]))
    svc._sender = FakeSender(svc)
    for ten in ("mot.txt", "hai.txt", "ba.txt"):
        f = tmp_path / ten
        f.write_bytes(b"a")
        svc.send_file(PEER.id, f)

    assert [t.file_name for t in svc.list_transfers()] == ["ba.txt", "hai.txt", "mot.txt"]


# --------------------------------------------------------------------------- Máy trong mạng

def test_them_may_theo_ip_va_gop_vao_danh_sach(tmp_config):
    """Dùng khi mạng chặn broadcast — đúng tình huống WiFi trường (T07)."""
    svc = TruyenNhanhService(tmp_config, discovery=FakeDiscovery([PEER]))

    them = svc.add_manual_peer("10.67.92.75")

    assert them.manual is True
    assert them.id == "manual:10.67.92.75"
    assert {p.id for p in svc.list_peers()} == {PEER.id, "manual:10.67.92.75"}


def test_them_lai_cung_mot_ip_thi_cap_nhat_chu_khong_tao_dong_trung(tmp_config):
    svc = TruyenNhanhService(tmp_config)

    svc.add_manual_peer("10.0.0.5", port=50506)
    svc.add_manual_peer("10.0.0.5", port=60000)

    peers = svc.list_peers()
    assert len(peers) == 1
    assert peers[0].tcp_port == 60000


@pytest.mark.parametrize("ip, port", [("", 50506), ("   ", 50506), ("10.0.0.5", 0), ("10.0.0.5", 70000)])
def test_them_may_voi_tham_so_sai(tmp_config, ip, port):
    svc = TruyenNhanhService(tmp_config)

    with pytest.raises(ValueError):
        svc.add_manual_peer(ip, port)


def test_refresh_peers_goi_xuong_do_tim(tmp_config):
    discovery = FakeDiscovery()
    svc = TruyenNhanhService(tmp_config, discovery=discovery)

    svc.refresh_peers()

    assert discovery.refresh_count == 1


def test_khong_co_do_tim_thi_danh_sach_rong_chu_khong_vo(tmp_config):
    svc = TruyenNhanhService(tmp_config)

    assert svc.list_peers() == []
    svc.refresh_peers()


# --------------------------------------------------------------------------- Thư mục nhận

def test_doi_thu_muc_nhan(tmp_config, tmp_path):
    svc = TruyenNhanhService(tmp_config)
    moi = tmp_path / "cho-moi"

    svc.set_download_dir(moi)

    assert svc.get_download_dir() == moi
    assert moi.is_dir(), "thư mục chưa có thì phải tự tạo"


def test_ten_may_lay_tu_config(tmp_config):
    assert TruyenNhanhService(tmp_config).device_name == "MAY-TEST"
