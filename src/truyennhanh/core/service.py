"""Lõi ứng dụng: TruyenNhanhService — docs/02 mục 3 và 4.

Phụ trách: R1 · Nhiệm vụ: T05 (chốt API), T14 (bản đầu), T25 (ghép thật), T33 (đồng thời)

Lớp DUY NHẤT mà giao diện (gui, cli) được phép gọi. Hai luật:
  1. Mọi hàm trả về NGAY, không bao giờ chờ mạng. Việc mạng chạy ở luồng riêng.
  2. Kết quả và trạng thái báo ngược lên bằng sự kiện trong self.events.

gui/fake_service.py có cùng API này để R5 làm giao diện trước khi lõi xong.

Về trạng thái của file này (T14, tuần 2)
----------------------------------------
Lõi đã chạy được với **thành phần giả**: vòng đời luồng, hàng đợi sự kiện, sổ
sách lượt truyền và cơ chế chờ quyết định người dùng đều thật. Ba thành phần
mạng — dò tìm (R2), bên gửi (R3), bên nhận (R4) — được tiêm vào qua tham số
từ khóa của __init__. Chưa tiêm thì lõi vẫn khởi động và dừng bình thường,
chỉ là không thấy máy nào và không gửi được.

T25 chỉ việc đổi giá trị mặc định của ba tham số đó từ None sang lớp thật.
Không phải sửa gì khác trong file này.

Ba giao thức Discovery, Receiver, Sender ở dưới là **hợp đồng** cho R2, R3, R4:
lớp các bạn viết chỉ cần có đúng những hàm đó là cắm vào chạy được.
"""
from __future__ import annotations

import queue
import socket
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from truyennhanh.config import Config, default_download_dir
from truyennhanh.core.events import (
    Emit,
    Event,
    PeerFound,
    StatusMessage,
    TransferFinished,
)
from truyennhanh.core.models import Direction, Peer, Transfer, TransferState
from truyennhanh.protocol.constants import TRANSFER_PORT_DEFAULT, Reason

STOP_JOIN_TIMEOUT_S = 5.0
"""Thời gian tối đa chờ MỖI luồng tự kết thúc trong stop().

Có giới hạn chứ không join() vô hạn: một luồng kẹt không được phép giữ cả ứng
dụng lại khi người dùng bấm đóng cửa sổ. Luồng nào quá hạn thì bị bỏ lại, và
stop() phát StatusMessage nói rõ — thà chạy tiếp và báo còn hơn đơ im lặng.
"""


# --------------------------------------------------------------------------- Hợp đồng thành phần

class Discovery(Protocol):
    """Hợp đồng cho phần dò tìm của R2 (discovery/, nhiệm vụ T15, T16, T29)."""

    def start(self, tcp_port: int) -> None:
        """Mở socket UDP, phát DISCOVER, bắt đầu phát ANNOUNCE mỗi 2 giây.

        tcp_port là cổng bên nhận THỰC SỰ đang lắng nghe, để đưa vào gói ANNOUNCE.
        """

    def stop(self) -> None:
        """Phát BYE rồi đóng socket và dừng luồng. Phải trả về, không được treo."""

    def refresh(self) -> None:
        """Phát lại DISCOVER ngay, không chờ hết chu kỳ 2 giây."""

    def peers(self) -> list[Peer]:
        """Ảnh chụp bảng thiết bị hiện tại."""


class Receiver(Protocol):
    """Hợp đồng cho máy chủ nhận của R4 (transfer/receiver.py, nhiệm vụ T20, T21)."""

    def start(self) -> int:
        """Lắng nghe TCP và trả về cổng THỰC SỰ đang nghe.

        Trả về cổng thật chứ không phải cổng đã xin, vì config.transfer_port = 0
        nghĩa là để hệ điều hành chọn cổng trống. Dò tìm cần con số thật để phát đi.
        """

    def stop(self) -> None:
        """Đóng socket nghe và dừng các luồng nhận. Phải trả về, không được treo."""


class Sender(Protocol):
    """Hợp đồng cho bên gửi của R3 (transfer/sender.py, nhiệm vụ T18, T19, T26)."""

    def send(self, job: SendJob) -> None:
        """Chạy trọn một lượt gửi. Lõi gọi hàm này TRÊN MỘT LUỒNG RIÊNG.

        Được phép chặn (blocking) thoải mái. Báo tiến độ qua job.emit, và kiểm
        job.cancelled thường xuyên để dừng sớm khi người dùng bấm hủy.
        """


@dataclass(frozen=True)
class SendJob:
    """Mọi thứ bên gửi cần cho một lượt, gói trong một đối tượng.

    cancelled : lõi bật cờ này khi người dùng bấm Hủy hoặc khi ứng dụng tắt.
                Bên gửi kiểm giữa các khối DATA và dừng sạch khi thấy nó bật.
    emit      : đẩy sự kiện lên giao diện. Bên gửi không bao giờ gọi thẳng giao diện.
    """

    transfer_id: str
    peer: Peer
    path: Path
    as_name: str | None
    chunk_size: int
    emit: Emit
    cancelled: threading.Event


class _Decision:
    """Chỗ hẹn giữa luồng nhận và người dùng — docs/02 mục 4, luật 4.

    Luồng nhận gặp OFFER thì phát OfferReceived rồi đứng chờ ở đây. Người dùng
    bấm nút, giao diện gọi respond_to_offer trên luồng chính, lõi ghi câu trả
    lời rồi mở khóa. Dùng threading.Event chứ không dùng vòng lặp hỏi liên tục:
    luồng chờ không tốn chút CPU nào.
    """

    def __init__(self) -> None:
        self._ready = threading.Event()
        self._accepted = False

    def answer(self, accepted: bool) -> None:
        self._accepted = accepted
        self._ready.set()

    def wait(self, timeout: float) -> bool | None:
        """True = đồng ý, False = từ chối, None = hết giờ chưa ai bấm."""
        if not self._ready.wait(timeout):
            return None
        return self._accepted


# --------------------------------------------------------------------------- Lõi

class TruyenNhanhService:
    """Điều phối dò tìm, máy chủ nhận và các lượt gửi.

    Thuộc tính:
        events : queue.Queue[Event] — giao diện lấy sự kiện từ đây trên luồng chính.
    """

    events: "queue.Queue[Event]"

    def __init__(
        self,
        config: Config | None = None,
        *,
        discovery: Discovery | None = None,
        receiver: Receiver | None = None,
        sender: Sender | None = None,
    ) -> None:
        """Tạo id lần chạy (uuid4), hàng đợi sự kiện; CHƯA mở socket nào.

        Ba tham số từ khóa là chỗ tiêm thành phần mạng. Để trống thì lõi chạy
        không mạng — dùng cho kiểm thử, và là trạng thái hiện tại của tuần 2.
        """
        self.config = config if config is not None else Config()
        self.events = queue.Queue()

        self._id = str(uuid.uuid4())
        self._device_name = self.config.device_name or socket.gethostname()
        self._download_dir = (
            Path(self.config.download_dir)
            if self.config.download_dir is not None
            else default_download_dir()
        )

        self._discovery = discovery
        self._receiver = receiver
        self._sender = sender

        # Một khóa duy nhất cho toàn bộ sổ sách. Nhiều luồng gửi, luồng nhận và
        # luồng chính cùng đọc ghi vào đây. Dùng RLock để một hàm đang giữ khóa
        # còn gọi được hàm khác cũng cần khóa mà không tự kẹt chính mình.
        self._lock = threading.RLock()

        self._transfers: dict[str, Transfer] = {}
        self._order: list[str] = []                      # mới nhất đứng đầu
        self._manual_peers: dict[str, Peer] = {}
        self._decisions: dict[str, _Decision] = {}
        self._cancel_flags: dict[str, threading.Event] = {}
        self._threads: list[threading.Thread] = []

        self._running = False
        self._transfer_port = self.config.transfer_port

    # ----------------------------------------------------------------- Vòng đời

    def start(self) -> None:
        """Bật máy chủ nhận (lấy cổng thật), rồi bật dò tìm với cổng đó.

        Đúng thứ tự này, không đảo được: gói ANNOUNCE phải mang cổng TCP thật,
        mà chỉ biết được sau khi bên nhận đã lắng nghe xong (config.transfer_port
        bằng 0 nghĩa là để hệ điều hành chọn).

        Gọi nhiều lần không sao: lần thứ hai trở đi không làm gì.
        """
        with self._lock:
            if self._running:
                return

            if self._receiver is not None:
                self._transfer_port = self._receiver.start()

            if self._discovery is not None:
                self._discovery.start(self._transfer_port)

            self._running = True

        self._emit(StatusMessage(
            f"Sẵn sàng với tên {self._device_name}, cổng nhận {self._transfer_port}"
        ))

    def stop(self) -> None:
        """Gửi BYE, hủy các lượt đang chạy với lý do shutting_down, dừng mọi luồng, giữ .part.

        Thứ tự ngược với start, và bật cờ hủy TRƯỚC khi dừng thành phần: các
        luồng gửi đang chạy cần thấy cờ để tự thoát, nếu không chúng vẫn ghi
        vào socket vừa bị đóng và ném lỗi loạn lên.

        Không bao giờ treo: mỗi luồng chỉ được chờ tối đa STOP_JOIN_TIMEOUT_S.
        Gọi nhiều lần không sao.
        """
        with self._lock:
            if not self._running:
                return
            self._running = False

            for flag in self._cancel_flags.values():
                flag.set()
            for decision in self._decisions.values():
                decision.answer(False)       # không ai kịp bấm thì coi như từ chối

            dang_chay = [
                t for t in self._transfers.values()
                if t.state in (TransferState.PENDING, TransferState.ACTIVE)
            ]
            threads = list(self._threads)

        for transfer in dang_chay:
            self._finish(transfer.id, ok=False, reason=Reason.SHUTTING_DOWN,
                         message="Ứng dụng đang tắt")

        if self._discovery is not None:
            self._discovery.stop()
        if self._receiver is not None:
            self._receiver.stop()

        con_song = []
        for t in threads:
            t.join(timeout=STOP_JOIN_TIMEOUT_S)
            if t.is_alive():
                con_song.append(t.name)

        with self._lock:
            self._threads = [t for t in self._threads if t.is_alive()]

        if con_song:
            self._emit(StatusMessage(
                "Đã tắt, nhưng các luồng sau chưa kết thúc: " + ", ".join(con_song)
            ))
        else:
            self._emit(StatusMessage("Đã tắt"))

    @property
    def device_name(self) -> str:
        """Tên máy này đang hiện với các máy khác. Giao diện hiện ở góc cửa sổ."""
        return self._device_name

    # ----------------------------------------------------------------- Máy trong mạng

    def list_peers(self) -> list[Peer]:
        """Ảnh chụp danh sách máy đang thấy.

        Gộp máy dò tìm được với máy người dùng tự thêm theo IP. Máy thêm tay
        đứng sau và không bao giờ hết hạn (docs/03 mục 3.3).
        """
        found = list(self._discovery.peers()) if self._discovery is not None else []
        seen = {p.id for p in found}
        with self._lock:
            them = [p for p in self._manual_peers.values() if p.id not in seen]
        return found + them

    def refresh_peers(self) -> None:
        """Gửi lại DISCOVER ngay, không chờ chu kỳ 2 giây.

        Dùng cho nút Làm mới trên giao diện và lệnh `truyennhanh scan`.
        Trả về ngay; máy tìm thấy báo về bằng sự kiện PeerFound.
        """
        if self._discovery is not None:
            self._discovery.refresh()

    def add_manual_peer(self, ip: str, port: int = TRANSFER_PORT_DEFAULT) -> Peer:
        """Thêm máy theo IP (FR-02). Máy thêm tay không bị hết hạn.

        Dùng cho mạng chặn broadcast — đúng tình huống WiFi trường (T07).
        id dạng "manual:<ip>" theo docs/03 mục 3.2, nên thêm lại cùng một IP
        sẽ cập nhật chứ không tạo thêm dòng trùng.
        """
        if not ip or not ip.strip():
            raise ValueError("Địa chỉ IP không được để trống")
        if not 1 <= port <= 65535:
            raise ValueError(f"Cổng phải nằm trong khoảng 1..65535, nhận được {port}")

        ip = ip.strip()
        peer = Peer(id=f"manual:{ip}", name=ip, ip=ip, tcp_port=port, manual=True)
        with self._lock:
            self._manual_peers[peer.id] = peer

        self._emit(PeerFound(peer))
        return peer

    # ----------------------------------------------------------------- Lượt truyền

    def list_transfers(self) -> list[Transfer]:
        """Các lượt truyền của lần chạy này, mới nhất trước.

        Giao diện chủ yếu dựng danh sách từ sự kiện; hàm này để lấy trạng thái
        ban đầu lúc mở cửa sổ và để vẽ lại khi cần.
        """
        with self._lock:
            return [self._transfers[i] for i in self._order if i in self._transfers]

    def send_file(self, peer_id: str, path: str | Path, as_name: str | None = None) -> str:
        """Bắt đầu gửi một file. Tạo luồng gửi và trả về transfer_id NGAY.

        as_name: khai một tên khác trong OFFER thay cho tên file thật. Chỉ dùng cho
        kiểm thử bảo mật KT-28 (lệnh `truyennhanh send --as-name ../../hack.txt`),
        giao diện không bao giờ truyền tham số này.

        Các lỗi thấy ngay (không có máy đó, không có file đó, chưa nối bên gửi)
        thì ném ngoại lệ tại chỗ. Lỗi xảy ra trong lúc truyền thì báo bằng sự
        kiện TransferFinished, vì lúc đó hàm này đã trả về từ lâu.
        """
        if self._sender is None:
            raise RuntimeError(
                "Chưa nối bên gửi vào lõi. Phần này do R3 làm ở T18 và T19, "
                "ghép vào lõi ở T25."
            )

        peer = next((p for p in self.list_peers() if p.id == peer_id), None)
        if peer is None:
            raise ValueError(f"Không có máy nào mang id {peer_id!r} trong danh sách")

        path = Path(path)
        if not path.is_file():
            raise ValueError(f"Không tìm thấy file: {path}")

        transfer_id = str(uuid.uuid4())
        cancelled = threading.Event()
        transfer = Transfer(
            id=transfer_id,
            direction=Direction.SEND,
            peer_name=peer.name,
            file_name=as_name or path.name,
            size=path.stat().st_size,
            state=TransferState.PENDING,
        )

        with self._lock:
            self._transfers[transfer_id] = transfer
            self._order.insert(0, transfer_id)
            self._cancel_flags[transfer_id] = cancelled

        job = SendJob(
            transfer_id=transfer_id,
            peer=peer,
            path=path,
            as_name=as_name,
            chunk_size=self.config.chunk_size,
            emit=self._emit,
            cancelled=cancelled,
        )
        self._spawn(f"gui-{transfer_id[:8]}", self._run_send, job)
        return transfer_id

    def respond_to_offer(self, transfer_id: str, accept: bool) -> None:
        """Người dùng đồng ý hoặc từ chối một OfferReceived. Mở khóa luồng nhận đang chờ.

        Bấm muộn quá 60 giây thì luồng nhận đã bỏ cuộc và xóa chỗ hẹn; khi đó
        hàm này lặng lẽ không làm gì. Ném lỗi ở đây sẽ làm hỏng hàm xử lý nút
        bấm của giao diện, mà người dùng thì không làm gì sai cả.
        """
        with self._lock:
            decision = self._decisions.get(transfer_id)
        if decision is not None:
            decision.answer(accept)

    def cancel(self, transfer_id: str) -> None:
        """Hủy một lượt, gửi hay nhận đều được. Kết quả về qua TransferFinished.

        Chỉ bật cờ rồi trả về ngay. Luồng đang chạy thấy cờ thì tự dừng sạch và
        tự phát TransferFinished — lõi không tự ý kết thúc hộ, vì chỉ luồng đó
        mới biết nó đang dở ở đâu.
        """
        with self._lock:
            flag = self._cancel_flags.get(transfer_id)
            decision = self._decisions.get(transfer_id)
        if flag is not None:
            flag.set()
        if decision is not None:
            decision.answer(False)

    # ----------------------------------------------------------------- Thư mục nhận

    def get_download_dir(self) -> Path:
        """Thư mục nhận hiện tại. Giao diện hiện lên và dùng cho nút Mở thư mục."""
        with self._lock:
            return self._download_dir

    def set_download_dir(self, path: str | Path) -> None:
        """Đổi thư mục nhận cho các lượt sau.

        Lượt đang chạy vẫn ghi vào thư mục cũ: file .part của nó nằm ở đó, đổi
        giữa chừng sẽ làm mất dấu phần đã nhận được.
        """
        path = Path(path).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        if not path.is_dir():
            raise ValueError(f"Không phải thư mục: {path}")
        with self._lock:
            self._download_dir = path
        self._emit(StatusMessage(f"Thư mục nhận: {path}"))

    # ----------------------------------------------------------------- Dùng nội bộ

    def _emit(self, event: Event) -> None:
        """Đẩy một sự kiện lên cho giao diện.

        Đây là lối ra DUY NHẤT từ các luồng mạng về giao diện (docs/02 mục 4,
        luật 3). queue.Queue tự lo việc nhiều luồng cùng ghi.
        """
        self.events.put(event)

    def _spawn(self, name: str, target, *args) -> threading.Thread:
        """Chạy một việc trên luồng nền và ghi sổ để stop() còn biết mà chờ.

        daemon=True để lỡ có luồng nào kẹt thì tiến trình vẫn thoát được; nhưng
        stop() vẫn join có hạn giờ, vì dựa vào daemon để thoát là cách thoát bẩn.
        """
        thread = threading.Thread(target=target, args=args, name=name, daemon=True)
        with self._lock:
            self._threads.append(thread)
        thread.start()
        return thread

    def _run_send(self, job: SendJob) -> None:
        """Vỏ bọc quanh bên gửi của R3, chạy trên luồng riêng.

        Bắt mọi ngoại lệ: một lượt gửi hỏng không được phép làm chết luồng rồi
        để lượt đó treo mãi ở trạng thái đang chạy trên giao diện.
        """
        try:
            self._sender.send(job)
        except Exception as e:                                # noqa: BLE001
            self._finish(
                job.transfer_id,
                ok=False,
                reason=Reason.CANCELLED if job.cancelled.is_set() else Reason.BAD_REQUEST,
                message=f"Lỗi khi gửi: {e}",
            )

    def _register_decision(self, transfer_id: str) -> _Decision:
        """Luồng nhận gọi trước khi phát OfferReceived, rồi chờ trên kết quả trả về."""
        decision = _Decision()
        with self._lock:
            self._decisions[transfer_id] = decision
        return decision

    def _forget_decision(self, transfer_id: str) -> None:
        """Luồng nhận gọi sau khi có câu trả lời hoặc hết giờ."""
        with self._lock:
            self._decisions.pop(transfer_id, None)

    def _track(self, transfer: Transfer) -> threading.Event:
        """Ghi một lượt vào sổ và trả về cờ hủy của nó. Dùng cho lượt NHẬN."""
        cancelled = threading.Event()
        with self._lock:
            self._transfers[transfer.id] = transfer
            self._order.insert(0, transfer.id)
            self._cancel_flags[transfer.id] = cancelled
        return cancelled

    def _update(self, transfer_id: str, **fields) -> None:
        """Cập nhật vài trường của một lượt trong sổ."""
        with self._lock:
            transfer = self._transfers.get(transfer_id)
            if transfer is None:
                return
            for key, value in fields.items():
                setattr(transfer, key, value)

    def _finish(
        self,
        transfer_id: str,
        *,
        ok: bool,
        reason: Reason | None = None,
        saved_path: Path | None = None,
        message: str | None = None,
    ) -> None:
        """Kết thúc một lượt: cập nhật sổ và phát TransferFinished đúng MỘT lần.

        Chống phát trùng: lượt đã ở trạng thái kết thúc rồi thì bỏ qua. Không có
        chốt này thì một lượt vừa bị hủy vừa gặp lỗi mạng sẽ phát hai sự kiện,
        và giao diện hiện hai dòng cho cùng một file.
        """
        with self._lock:
            transfer = self._transfers.get(transfer_id)
            if transfer is None or transfer.state in (TransferState.DONE, TransferState.FAILED):
                return

            transfer.state = TransferState.DONE if ok else TransferState.FAILED
            transfer.reason = reason
            transfer.saved_path = saved_path
            direction = transfer.direction
            self._cancel_flags.pop(transfer_id, None)
            self._decisions.pop(transfer_id, None)

        self._emit(TransferFinished(
            transfer_id=transfer_id,
            direction=direction,
            ok=ok,
            reason=reason,
            saved_path=saved_path,
            message=message,
        ))
