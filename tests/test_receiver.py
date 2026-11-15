"""Kiểm thử FileReceiverServer (T20). Tích hợp qua 127.0.0.1, dùng cổng 0 theo quy ước docs/08."""
import socket, threading, time, queue
from types import SimpleNamespace
from typing import cast

import pytest

from truyennhanh.config import Config
from truyennhanh.core.events import StatusMessage
from truyennhanh.protocol.constants import FrameType, Reason
from truyennhanh.protocol.framing import encode_frame, read_frame
from truyennhanh.protocol.messages import Offer, encode_json, parse_accept, parse_cancel, parse_reject
from truyennhanh.transfer import receiver as receiver_module
from truyennhanh.transfer.receiver import FileReceiverServer

def _make_server(download_dir, transfer_port: int = 0, server_class=FileReceiverServer, ask_user=None):
    """Máy chủ với cấu hình giả (transfer_port và download_dir) và danh sách thu sự kiện."""
    events = []
    config = cast(Config, SimpleNamespace(transfer_port=transfer_port, download_dir=download_dir))
    if ask_user is None:
        ask_user = lambda offer, name, offset: True  # noqa: E731
    server = server_class(config, events.append, ask_user)
    return server, events


@pytest.fixture
def server_factory(tmp_path):
    """Tạo máy chủ (thư mục nhận là tmp_path) và bảo đảm mọi máy chủ đều được stop() sau test, dù test fail."""
    created = []

    def make(transfer_port: int = 0, server_class=FileReceiverServer, ask_user=None):
        server, events = _make_server(tmp_path, transfer_port, server_class, ask_user)
        created.append(server)
        return server, events

    yield make
    for server in created:
        server.stop()

def _connection_threads():
    return [t for t in threading.enumerate() if t.name.startswith("receiver-conn")]


def _wait_until(predicate, timeout: float = 3.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


# --------------------------------------------------------------------------- Bước 1: cổng

def test_start_returns_a_real_port_when_config_port_is_zero(server_factory):
    server, _ = server_factory(0)
    port = server.start()
    assert port > 0
    assert server.port == port


def test_start_accepts_tcp_connection_on_the_reported_port(server_factory):
    server, _ = server_factory(0)
    port = server.start()
    with socket.create_connection(("127.0.0.1", port), timeout=2):
        pass  # kết nối được nghĩa là socket đang listen thật


def test_start_falls_back_to_os_chosen_port_when_requested_port_is_busy(server_factory):
    """Cổng bị ứng dụng khác chiếm thì lấy cổng khác, không ném lỗi, và báo cổng thật."""
    blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        blocker.bind(("0.0.0.0", 0))
        blocker.listen(1)
        busy_port = blocker.getsockname()[1]

        server, events = server_factory(busy_port)
        port = server.start()

        assert port != busy_port
        assert port > 0
        assert server.port == port
    finally:
        blocker.close()


def test_start_tells_the_user_when_it_falls_back(server_factory):
    blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        blocker.bind(("0.0.0.0", 0))
        blocker.listen(1)
        server, events = server_factory(blocker.getsockname()[1])
        server.start()
        assert any(isinstance(e, StatusMessage) for e in events)
    finally:
        blocker.close()


def test_port_before_start_raises(server_factory):
    server, _ = server_factory(0)
    with pytest.raises(RuntimeError):
        _ = server.port


def test_start_twice_raises(server_factory):
    server, _ = server_factory(0)
    server.start()
    with pytest.raises(RuntimeError):
        server.start()


def test_stop_releases_the_port(server_factory):
    server, _ = server_factory(0)
    port = server.start()
    server.stop()
    with pytest.raises(OSError):
        socket.create_connection(("127.0.0.1", port), timeout=1)


# --------------------------------------------------------------------------- Bước 2: luồng

class _GateServer(FileReceiverServer):
    """Mỗi kết nối báo đã bắt đầu rồi đứng chờ cổng mở: dùng để chứng minh các kết nối độc lập."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.started = threading.Semaphore(0)
        self.gate = threading.Event()

    def _handle_connection(self, conn, addr):
        self.started.release()
        self.gate.wait(5)


class _FailFirstServer(FileReceiverServer):
    """Kết nối đầu tiên ném lỗi; từ kết nối thứ hai trở đi chạy bình thường."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.first_failed = threading.Event()
        self.later_handled = threading.Event()
        self._calls = 0

    def _handle_connection(self, conn, addr):
        self._calls += 1
        if self._calls == 1:
            self.first_failed.set()
            raise RuntimeError("lỗi giả để thử")
        self.later_handled.set()


class _ReadServer(FileReceiverServer):
    """Mỗi kết nối đứng chờ recv() mãi: giống một bên gửi im lặng."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reading = threading.Event()

    def _handle_connection(self, conn, addr):
        self.reading.set()
        try:
            conn.recv(1)
        except OSError:
            pass


def test_a_stuck_connection_does_not_block_other_connections(server_factory):
    """Kết nối thứ nhất kẹt mãi; kết nối thứ hai vẫn phải được xử lý ngay."""
    server, _ = server_factory(0, _GateServer)
    port = server.start()
    clients = []
    try:
        for _ in range(2):
            clients.append(socket.create_connection(("127.0.0.1", port), timeout=2))
            assert server.started.acquire(timeout=2)
    finally:
        server.gate.set()
        for client in clients:
            client.close()


def test_exception_in_one_connection_does_not_stop_the_server(server_factory):
    server, _ = server_factory(0, _FailFirstServer)
    port = server.start()
    with socket.create_connection(("127.0.0.1", port), timeout=2):
        assert server.first_failed.wait(2)
    with socket.create_connection(("127.0.0.1", port), timeout=2):
        assert server.later_handled.wait(2)


def test_stop_ends_the_accept_thread(server_factory):
    server, _ = server_factory(0)
    server.start()
    assert any(t.name == "receiver-accept" for t in threading.enumerate())
    server.stop()
    assert not any(t.name == "receiver-accept" for t in threading.enumerate())


def test_stop_unblocks_connection_threads_and_closes_clients(server_factory):
    server, _ = server_factory(0, _ReadServer)
    port = server.start()
    with socket.create_connection(("127.0.0.1", port), timeout=2) as client:
        assert server.reading.wait(2)
        server.stop()
        client.settimeout(3)
        try:
            data = client.recv(1)
        except ConnectionError:
            data = b""
        assert data == b""
    assert _wait_until(lambda: not _connection_threads())


def test_stop_twice_does_not_raise(server_factory):
    server, _ = server_factory(0)
    server.start()
    server.stop()
    server.stop()


def test_stop_before_start_does_not_raise(server_factory):
    server, _ = server_factory(0)
    server.stop()


def test_server_can_start_again_after_stop(server_factory):
    server, _ = server_factory(0)
    server.start()
    server.stop()
    port = server.start()
    with socket.create_connection(("127.0.0.1", port), timeout=2):
        pass
# --------------------------------------------------------------------------- Bước 3: đọc OFFER

SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def _offer_fields(**changes) -> dict:
    """Các trường của một OFFER hợp lệ; truyền tham số để ghi đè."""
    fields = {"v": 1, "transfer_id": "t-1", "sender_id": "s-1", "sender_name": "May A",
              "name": "bao_cao.pdf", "size": 10, "sha256": SHA}
    fields.update(changes)
    return fields


def _valid_offer() -> Offer:
    return Offer(transfer_id="t-1", sender_id="s-1", sender_name="May A",
                 name="bao_cao.pdf", size=10, sha256=SHA)


def _offer_frame(fields: dict) -> bytes:
    return encode_frame(FrameType.OFFER, encode_json(fields))


class _OfferCapture(FileReceiverServer):
    """Thu lại các OFFER hợp lệ mà bước 3 chuyển sang bước sau."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.offers = queue.Queue()

    def _on_offer(self, conn, addr, offer):
        self.offers.put(offer)


def _connect(port: int) -> socket.socket:
    return socket.create_connection(("127.0.0.1", port), timeout=3)


def _recv_or_eof(client: socket.socket) -> bytes:
    """Đọc 1 byte; kết nối bị đóng (kể cả bị reset) thì trả về b""."""
    try:
        return client.recv(1)
    except ConnectionError:
        return b""


def _read_reject(client: socket.socket, transfer_id: str):
    frame_type, payload = read_frame(client)
    assert frame_type is FrameType.REJECT
    return parse_reject(payload, transfer_id)


def test_valid_offer_is_handed_to_the_next_stage(server_factory):
    server, _ = server_factory(0, _OfferCapture)
    port = server.start()
    with _connect(port) as client:
        client.sendall(_offer_frame(_offer_fields()))
        assert server.offers.get(timeout=2) == _valid_offer()


def test_silent_connection_is_closed_after_idle_timeout(server_factory, monkeypatch):
    monkeypatch.setattr(receiver_module, "IDLE_TIMEOUT_S", 0.3)
    server, _ = server_factory(0, _OfferCapture)
    port = server.start()
    with _connect(port) as client:
        started = time.monotonic()
        assert _recv_or_eof(client) == b""
        assert time.monotonic() - started < 3
    assert server.offers.empty()


def test_half_sent_header_is_closed_after_idle_timeout(server_factory, monkeypatch):
    monkeypatch.setattr(receiver_module, "IDLE_TIMEOUT_S", 0.3)
    server, _ = server_factory(0, _OfferCapture)
    port = server.start()
    with _connect(port) as client:
        client.sendall(b"\x00\x00")  # mới 2 trong 5 byte của phần đầu khung
        assert _recv_or_eof(client) == b""
    assert server.offers.empty()


def test_silent_connection_does_not_block_a_valid_offer(server_factory):
    """Một máy kết nối rồi im lặng không được chặn máy khác (KT-30)."""
    server, _ = server_factory(0, _OfferCapture)
    port = server.start()
    with _connect(port) as silent, _connect(port) as sender:
        sender.sendall(_offer_frame(_offer_fields()))
        assert server.offers.get(timeout=2) == _valid_offer()


def test_client_closing_mid_frame_does_not_break_the_server(server_factory):
    server, _ = server_factory(0, _OfferCapture)
    port = server.start()
    with _connect(port) as client:
        client.sendall(b"\x00\x00\x00")
    with _connect(port) as sender:
        sender.sendall(_offer_frame(_offer_fields()))
        assert server.offers.get(timeout=2) == _valid_offer()


def test_data_frame_before_offer_closes_the_connection(server_factory):
    """KT-32: khung đầu tiên không phải OFFER thì đóng, không chuyển đi đâu."""
    server, _ = server_factory(0, _OfferCapture)
    port = server.start()
    with _connect(port) as client:
        client.sendall(encode_frame(FrameType.DATA, b"abc"))
        assert _recv_or_eof(client) == b""
    assert server.offers.empty()


@pytest.mark.parametrize(
    "garbage",
    [bytes.fromhex("ffffffff01"), b"GET / HTTP/1.1\r\nHost: x\r\n\r\n", bytes.fromhex("0000000009")],
    ids=["huge-length", "http-request", "unknown-frame-type"],
)
def test_garbage_bytes_close_the_connection_at_once(server_factory, garbage):
    """KT-29, KT-31: đóng ngay, không chờ hết hạn 15 giây, không trả lời."""
    server, _ = server_factory(0, _OfferCapture)
    port = server.start()
    with _connect(port) as client:
        client.sendall(garbage)
        started = time.monotonic()
        assert _recv_or_eof(client) == b""
        assert time.monotonic() - started < 2
    assert server.offers.empty()


@pytest.mark.parametrize(
    "fields",
    [
        _offer_fields(sha256=SHA.upper()),
        _offer_fields(sha256=SHA[:63]),
        _offer_fields(size=-1),
        _offer_fields(size=True),
        _offer_fields(size="10"),
        {k: v for k, v in _offer_fields().items() if k != "name"},
    ],
    ids=["sha256-uppercase", "sha256-too-short", "negative-size", "bool-size", "string-size", "missing-name"],
)
def test_invalid_offer_is_rejected_with_bad_request(server_factory, fields):
    server, _ = server_factory(0, _OfferCapture)
    port = server.start()
    with _connect(port) as client:
        client.sendall(_offer_frame(fields))
        reason, _ = _read_reject(client, "t-1")
        assert reason is Reason.BAD_REQUEST
        assert _recv_or_eof(client) == b""
    assert server.offers.empty()


def test_offer_of_another_protocol_version_is_rejected_as_unsupported(server_factory):
    server, _ = server_factory(0, _OfferCapture)
    port = server.start()
    with _connect(port) as client:
        client.sendall(_offer_frame(_offer_fields(v=2)))
        reason, _ = _read_reject(client, "t-1")
        assert reason is Reason.UNSUPPORTED_VERSION
    assert server.offers.empty()


@pytest.mark.parametrize(
    "payload",
    [b"khong phai json", b"[]", b"[" * 60_000, b"\xff\xfe"],
    ids=["not-json", "not-an-object", "deeply-nested", "not-utf8"],
)
def test_unparseable_offer_is_rejected_without_crashing(server_factory, payload):
    """Không đọc được transfer_id thì REJECT mang transfer_id rỗng; máy chủ không ném lỗi."""
    server, _ = server_factory(0, _OfferCapture)
    port = server.start()
    with _connect(port) as client:
        client.sendall(encode_frame(FrameType.OFFER, payload))
        reason, _ = _read_reject(client, "")
        assert reason is Reason.BAD_REQUEST
    assert server.offers.empty()


def test_server_keeps_working_after_a_bad_offer(server_factory):
    server, _ = server_factory(0, _OfferCapture)
    port = server.start()
    with _connect(port) as bad:
        bad.sendall(encode_frame(FrameType.OFFER, b"khong phai json"))
        _read_reject(bad, "")
    with _connect(port) as good:
        good.sendall(_offer_frame(_offer_fields()))
        assert server.offers.get(timeout=2) == _valid_offer()



# --------------------------------------------------------------------------- Bước 4: hỏi người dùng

def _read_accept(client: socket.socket, transfer_id: str = "t-1", size: int = 10) -> int:
    frame_type, payload = read_frame(client)
    assert frame_type is FrameType.ACCEPT
    return parse_accept(payload, transfer_id, size)


def test_accepted_offer_gets_accept_with_offset_zero(server_factory):
    server, _ = server_factory(0, ask_user=lambda offer, name, offset: True)
    port = server.start()
    with _connect(port) as client:
        client.sendall(_offer_frame(_offer_fields()))
        assert _read_accept(client) == 0


def test_declined_offer_gets_reject_user_declined(server_factory):
    server, _ = server_factory(0, ask_user=lambda offer, name, offset: False)
    port = server.start()
    with _connect(port) as client:
        client.sendall(_offer_frame(_offer_fields()))
        reason, message = _read_reject(client, "t-1")
        assert reason is Reason.USER_DECLINED
        assert message
        assert _recv_or_eof(client) == b""


def test_ask_user_receives_the_offer_the_sanitized_name_and_the_resume_offset(server_factory):
    calls = []

    def ask_user(offer, name, offset):
        calls.append((offer, name, offset))
        return True

    server, _ = server_factory(0, ask_user=ask_user)
    port = server.start()
    with _connect(port) as client:
        client.sendall(_offer_frame(_offer_fields(name="../../Windows/x.dll")))
        _read_accept(client)
    offer, name, offset = calls[0]
    assert offer.name == "../../Windows/x.dll"  # OFFER giữ nguyên tên gốc
    assert name == "x.dll"                       # ask_user nhận tên đã làm sạch
    assert offset == 0


def test_ask_user_timing_out_gets_reject_timeout(server_factory, monkeypatch):
    monkeypatch.setattr(receiver_module, "DECISION_TIMEOUT_S", 0.6)

    def slow_user(offer, name, offset):
        time.sleep(0.65)  # giống lõi: chờ đủ hạn rồi trả về False
        return False

    server, _ = server_factory(0, ask_user=slow_user)
    port = server.start()
    with _connect(port) as client:
        client.sendall(_offer_frame(_offer_fields()))
        reason, _ = _read_reject(client, "t-1")
        assert reason is Reason.TIMEOUT


@pytest.mark.parametrize(
    "waited, expected",
    [(0.0, Reason.USER_DECLINED), (5.0, Reason.USER_DECLINED), (59.0, Reason.USER_DECLINED),
     (59.6, Reason.TIMEOUT), (60.0, Reason.TIMEOUT), (75.0, Reason.TIMEOUT)],
)
def test_decline_reason_depends_on_how_long_the_user_took(waited, expected):
    assert receiver_module._decline_reason(waited) is expected


def test_slow_user_decision_does_not_block_other_connections(server_factory):
    """Máy thứ nhất đang chờ người dùng quyết định; máy thứ hai vẫn được trả lời ngay."""
    gate = threading.Event()

    def ask_user(offer, name, offset):
        if name == "cham.txt":
            gate.wait(5)
        return True

    server, _ = server_factory(0, ask_user=ask_user)
    port = server.start()
    try:
        with _connect(port) as slow, _connect(port) as fast:
            slow.sendall(_offer_frame(_offer_fields(transfer_id="t-slow", name="cham.txt")))
            fast.sendall(_offer_frame(_offer_fields(transfer_id="t-fast", name="nhanh.txt")))
            assert _read_accept(fast, "t-fast") == 0   # máy sau được trả lời trước
            gate.set()
            assert _read_accept(slow, "t-slow") == 0
    finally:
        gate.set()


def test_ask_user_raising_closes_that_connection_and_server_keeps_working(server_factory):
    calls = []

    def ask_user(offer, name, offset):
        calls.append(name)
        if len(calls) == 1:
            raise RuntimeError("lỗi giả trong lõi")
        return True

    server, _ = server_factory(0, ask_user=ask_user)
    port = server.start()
    with _connect(port) as first:
        first.sendall(_offer_frame(_offer_fields()))
        assert _recv_or_eof(first) == b""
    with _connect(port) as second:
        second.sendall(_offer_frame(_offer_fields()))
        assert _read_accept(second) == 0

# --------------------------------------------------------------------------- Bước 5: hủy, tắt máy, đóng nhẹ nhàng

def _blocking_user(answer: bool = True):
    """ask_user đứng chờ cổng mở, giống người dùng đang suy nghĩ.

    Trả về (ask_user, entered, gate): entered.acquire() đợi tới khi có lượt vào hỏi; gate.set() cho trả lời.
    """
    entered = threading.Semaphore(0)
    gate = threading.Event()

    def ask_user(offer, name, offset):
        entered.release()
        gate.wait(5)
        return answer

    return ask_user, entered, gate


def _read_cancel(client: socket.socket, transfer_id: str = "t-1") -> Reason:
    frame_type, payload = read_frame(client)
    assert frame_type is FrameType.CANCEL
    return parse_cancel(payload, transfer_id)


def test_stop_sends_cancel_shutting_down_to_running_transfers(server_factory, monkeypatch):
    monkeypatch.setattr(receiver_module, "STOP_GRACE_S", 0.3)
    ask_user, entered, gate = _blocking_user()
    server, _ = server_factory(0, ask_user=ask_user)
    port = server.start()
    try:
        with _connect(port) as client:
            client.sendall(_offer_frame(_offer_fields()))
            assert entered.acquire(timeout=2)
            started = time.monotonic()
            server.stop()
            assert time.monotonic() - started < 2  # ask_user kẹt cũng không giữ stop() quá hạn chờ
            assert _read_cancel(client) is Reason.SHUTTING_DOWN
            assert _recv_or_eof(client) == b""
    finally:
        gate.set()


def test_stop_leaves_no_connection_thread_behind(server_factory):
    server, _ = server_factory(0)
    port = server.start()
    with _connect(port) as client:
        client.sendall(_offer_frame(_offer_fields()))
        assert _read_accept(client) == 0  # luồng kết nối còn đang đợi bên gửi đóng
        server.stop()
        assert not _connection_threads()


def test_cancel_sends_cancel_cancelled_and_no_accept_follows(server_factory):
    ask_user, entered, gate = _blocking_user(answer=True)
    server, _ = server_factory(0, ask_user=ask_user)
    port = server.start()
    try:
        with _connect(port) as client:
            client.sendall(_offer_frame(_offer_fields()))
            assert entered.acquire(timeout=2)
            server.cancel("t-1")
            assert _read_cancel(client) is Reason.CANCELLED
            gate.set()  # người dùng bấm Đồng ý quá muộn: lượt đã bị hủy
            assert _recv_or_eof(client) == b""  # không có ACCEPT nào theo sau
    finally:
        gate.set()


def test_cancel_only_affects_the_matching_transfer(server_factory):
    ask_user, entered, gate = _blocking_user(answer=True)
    server, _ = server_factory(0, ask_user=ask_user)
    port = server.start()
    try:
        with _connect(port) as a, _connect(port) as b:
            a.sendall(_offer_frame(_offer_fields(transfer_id="t-a")))
            b.sendall(_offer_frame(_offer_fields(transfer_id="t-b")))
            assert entered.acquire(timeout=2)
            assert entered.acquire(timeout=2)
            server.cancel("t-a")
            gate.set()
            assert _read_cancel(a, "t-a") is Reason.CANCELLED
            assert _read_accept(b, "t-b") == 0
    finally:
        gate.set()


def test_cancel_of_unknown_transfer_does_nothing(server_factory):
    server, _ = server_factory(0)
    server.start()
    server.cancel("khong-co-luot-nao")  # không ném lỗi


def test_reject_is_delivered_even_when_the_sender_keeps_sending(server_factory):
    """Đóng nhẹ nhàng: bên gửi còn gửi dữ liệu thừa thì REJECT vẫn tới nơi, không bị RST xóa mất."""
    server, _ = server_factory(0, _OfferCapture)
    port = server.start()
    with _connect(port) as client:
        client.sendall(encode_frame(FrameType.OFFER, b"khong phai json") + b"x" * 200_000)
        reason, _ = _read_reject(client, "")
        assert reason is Reason.BAD_REQUEST