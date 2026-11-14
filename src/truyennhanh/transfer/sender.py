"""Bên gửi: gửi một file qua một kết nối TCP — docs/03 mục 4.4 và 4.5.

Phụ trách: R3 · Nhiệm vụ: T08 (thử nghiệm), T18, T19 (tuần 2), T26 (truyền tiếp, tuần 3), T35 (hủy)

Trình tự một lượt:
  1. sha256_file (phát StatusMessage "Đang tính mã băm...")
  2. Kết nối TCP, hết giờ CONNECT_TIMEOUT_S
  3. Gửi OFFER, chờ ACCEPT/REJECT tối đa ACCEPT_WAIT_TIMEOUT_S
  4. ACCEPT offset=k: kiểm tra 0 <= k <= size, nhảy tới byte k, phát TransferStarted
  5. Gửi DATA từng khối config.chunk_size; phát TransferProgress không quá 10 lần/giây
  6. Gửi DONE, chờ RESULT tối đa RESULT_WAIT_TIMEOUT_S, phát TransferFinished, đóng kết nối

Mất kết nối ở bước 5 (T26): chờ lần lượt RETRY_DELAYS_S, kết nối lại, gửi lại OFFER cùng
transfer_id. Hết 5 lần thì TransferFinished(ok=False).

Các quyết định thiết kế (để R1, R4 và báo cáo biết):
  * Mỗi socket chỉ có MỘT luồng ghi là luồng run(). cancel() chỉ bật cờ; run() thấy cờ (tối đa
    sau POLL_INTERVAL_S giây, hoặc ngay giữa hai khối DATA) thì tự gửi CANCEL. Nếu cancel() tự
    ghi lên socket từ luồng khác thì khung CANCEL có thể chen vào giữa một khung DATA đang gửi
    dở và làm hỏng đóng khung của cả kết nối.
  * Giữa hai khối DATA, bên gửi nhìn xem bên nhận có gửi CANCEL (hết chỗ, người dùng hủy...) không.
  * Chỉ thử kết nối lại khi đã từng nhận ACCEPT: kết nối lần đầu không được (máy kia tắt, sai IP)
    thì báo lỗi ngay thay vì bắt người dùng chờ 31 giây. Bộ đếm 5 lần được tính lại từ đầu nếu lần
    kết nối vừa rồi đã gửi thêm được ít nhất một khối DATA, để mỗi lần đứt mạng thật đều được đủ 5 lần
    mà một kết nối đứt liên tục không có tiến triển thì vẫn dừng sau 5 lần.
  * Bên gửi kiểm tra file không đổi (kích thước, thời điểm sửa) trước mỗi lần kết nối. File đổi giữa
    chừng thì mã băm đã khai trong OFFER sai và vị trí truyền tiếp vô nghĩa, nên báo lỗi thay vì gửi tiếp.
  * TransferProgress đếm byte đã giao cho TCP (sendall xong), không phải byte bên nhận đã ghi.

Đọc thêm: Kurose Chương 2 slide 105–108; TCP/IP Sockets in C# mục 5.1, 5.2.
"""
from __future__ import annotations

import os
import select
import socket
import threading
import time
from pathlib import Path

from truyennhanh.config import Config
from truyennhanh.core.events import (
    Emit,
    StatusMessage,
    TransferFinished,
    TransferProgress,
    TransferStarted,
)
from truyennhanh.core.models import Direction, Peer
from truyennhanh.protocol.constants import (
    ACCEPT_WAIT_TIMEOUT_S,
    CONNECT_TIMEOUT_S,
    IDLE_TIMEOUT_S,
    MAX_DATA_PAYLOAD,
    MAX_NAME_CHARS,
    PROGRESS_MAX_PER_SECOND,
    RESULT_WAIT_TIMEOUT_S,
    RETRY_DELAYS_S,
    FrameType,
    Reason,
)
from truyennhanh.protocol.framing import ConnectionClosed, FrameError, encode_frame, read_frame
from truyennhanh.protocol.messages import (
    Offer,
    ProtocolError,
    make_cancel,
    make_done,
    make_offer,
    parse_accept,
    parse_cancel,
    parse_reject,
    parse_result,
)
from truyennhanh.transfer.hashing import sha256_file

POLL_INTERVAL_S = 0.25
"""Chu kỳ nhìn cờ hủy khi đang chờ bên nhận (chờ ACCEPT, chờ RESULT, socket đầy)."""

HASH_STATUS_MIN_BYTES = 8 * 1024 * 1024
"""File nhỏ hơn mức này tính mã băm trong chớp mắt, không cần báo trạng thái."""

HASH_STATUS_INTERVAL_S = 0.5

_REASON_TEXT = {
    Reason.USER_DECLINED: "Người nhận đã từ chối.",
    Reason.TIMEOUT: "Hết thời gian chờ.",
    Reason.BUSY: "Máy nhận đang nhận đúng file này ở một lượt khác.",
    Reason.INSUFFICIENT_SPACE: "Máy nhận không đủ dung lượng.",
    Reason.UNSUPPORTED_VERSION: "Máy nhận dùng phiên bản giao thức khác.",
    Reason.BAD_REQUEST: "Máy nhận báo yêu cầu không hợp lệ.",
    Reason.HASH_MISMATCH: "File nhận được có SHA-256 không khớp; máy nhận đã xóa phần đã nhận.",
    Reason.INCOMPLETE: "Máy nhận báo chưa nhận đủ dữ liệu.",
    Reason.CANCELLED: "Lượt gửi đã bị hủy.",
    Reason.SHUTTING_DOWN: "Máy nhận đang tắt ứng dụng.",
}


def _reason_text(reason: Reason, extra: str | None = None) -> str:
    text = _REASON_TEXT.get(reason, f"Lý do: {reason.value}.")
    return f"{text} ({extra})" if extra else text


class _Stop(Exception):
    """Lượt gửi kết thúc thất bại (hoặc bị hủy). Không thử lại."""

    def __init__(self, reason: Reason, message: str) -> None:
        super().__init__(message)
        self.reason = reason
        self.message = message


class _ConnectionLost(Exception):
    """Kết nối đứt hoặc im lặng quá lâu. Được phép thử lại nếu đã từng nhận ACCEPT."""


class FileSender:
    """Một đối tượng cho một lượt gửi. Lõi tạo luồng và gọi run() trong luồng đó.

    as_name     : tên khai trong OFFER thay cho tên file thật (chỉ để kiểm thử bảo mật KT-28)
    cancel_event: cờ hủy dùng chung với lõi (SendJob.cancelled); không truyền thì tự tạo
    """

    def __init__(self, transfer_id: str, sender_id: str, sender_name: str,
                 peer: Peer, path: Path, config: Config, emit: Emit, *,
                 as_name: str | None = None,
                 cancel_event: threading.Event | None = None) -> None:
        self.transfer_id = transfer_id
        self._sender_id = sender_id
        self._sender_name = sender_name[:MAX_NAME_CHARS]
        self._peer = peer
        self._path = Path(path)
        self._emit = emit
        self._offer_name = as_name if as_name is not None else self._path.name
        self._chunk_size = max(1, min(int(config.chunk_size), MAX_DATA_PAYLOAD))
        self._cancel = cancel_event if cancel_event is not None else threading.Event()

        self._finished = False
        self._size = 0
        self._mtime_ns = 0
        self._sha256 = ""
        self._accepted_once = False
        self._made_progress = False
        self._last_progress_at = float("-inf")

    # ----------------------------------------------------------------- Giao diện công khai

    def run(self) -> None:
        """Chạy trọn một lượt gửi, CHẶN cho tới khi xong. Không ném ngoại lệ ra ngoài:
        mọi kết cục — thành công, bị từ chối, lỗi, bị hủy — báo bằng đúng một TransferFinished.
        """
        try:
            self._run()
            self._finish(True)
        except _Stop as stop:
            self._finish(False, stop.reason, stop.message)
        except Exception as e:                                # noqa: BLE001
            self._finish(False, Reason.BAD_REQUEST, f"Lỗi khi gửi: {e}")

    def cancel(self) -> None:
        """Gọi từ luồng khác. Bật cờ hủy; run() sẽ gửi CANCEL cancelled rồi kết thúc.

        Không ghi trực tiếp lên socket ở đây — xem ghi chú đầu file.
        """
        self._cancel.set()

    # ----------------------------------------------------------------- Luồng chính của một lượt

    def _run(self) -> None:
        self._prepare()

        failures = 0
        while True:
            self._raise_if_cancelled()
            self._check_file_unchanged()
            self._made_progress = False
            try:
                self._attempt()
                return
            except _ConnectionLost as lost:
                self._raise_if_cancelled()
                if not self._accepted_once:
                    raise _Stop(
                        Reason.TIMEOUT,
                        f"Không kết nối được tới {self._peer.name} ({lost}).",
                    ) from None
                if self._made_progress:
                    failures = 0
                if failures >= len(RETRY_DELAYS_S):
                    raise _Stop(
                        Reason.TIMEOUT,
                        f"Mất kết nối với {self._peer.name} và đã thử lại {len(RETRY_DELAYS_S)} lần "
                        f"không được ({lost}).",
                    ) from None
                delay = RETRY_DELAYS_S[failures]
                failures += 1
                self._status(
                    f"Mất kết nối, thử lại sau {delay} giây "
                    f"(lần {failures}/{len(RETRY_DELAYS_S)})..."
                )
                if self._cancel.wait(delay):
                    raise _Stop(Reason.CANCELLED, "Bạn đã hủy lượt gửi.") from None

    def _prepare(self) -> None:
        """Kiểm tra file và tính SHA-256 một lần cho cả lượt (kể cả các lần kết nối lại)."""
        try:
            st = os.stat(self._path)
        except OSError as e:
            raise _Stop(Reason.BAD_REQUEST, f"Không đọc được file: {e}") from None
        if not self._path.is_file():
            raise _Stop(Reason.BAD_REQUEST, f"Không phải file: {self._path}")

        self._size = st.st_size
        self._mtime_ns = st.st_mtime_ns

        last_status = [float("-inf")]

        def on_progress(done: int, total: int) -> None:
            now = time.monotonic()
            if now - last_status[0] >= HASH_STATUS_INTERVAL_S:
                last_status[0] = now
                self._status(f"Đang tính mã băm... {done * 100 // total}%")

        if self._size >= HASH_STATUS_MIN_BYTES:
            self._status("Đang tính mã băm...")
        try:
            self._sha256 = sha256_file(
                self._path,
                progress=on_progress if self._size >= HASH_STATUS_MIN_BYTES else None,
                cancel=self._cancel,
            )
        except InterruptedError:
            raise _Stop(Reason.CANCELLED, "Bạn đã hủy lượt gửi.") from None
        except OSError as e:
            raise _Stop(Reason.BAD_REQUEST, f"Không đọc được file: {e}") from None
        self._check_file_unchanged()

    def _check_file_unchanged(self) -> None:
        try:
            st = os.stat(self._path)
        except OSError as e:
            raise _Stop(Reason.BAD_REQUEST, f"Không đọc được file: {e}") from None
        if st.st_size != self._size or st.st_mtime_ns != self._mtime_ns:
            raise _Stop(
                Reason.BAD_REQUEST,
                "File đã bị thay đổi trong lúc gửi nên không thể gửi tiếp. Hãy gửi lại từ đầu.",
            )

    def _attempt(self) -> None:
        """Một lần kết nối: OFFER -> ACCEPT -> DATA -> DONE -> RESULT."""
        sock = self._connect()
        try:
            self._converse(sock)
        except _ConnectionLost:
            self._look_for_cancel(sock)
            raise
        finally:
            try:
                sock.close()
            except OSError:
                pass

    def _connect(self) -> socket.socket:
        try:
            sock = socket.create_connection(
                (self._peer.ip, self._peer.tcp_port), timeout=CONNECT_TIMEOUT_S
            )
        except OSError as e:
            raise _ConnectionLost(f"{self._peer.ip}:{self._peer.tcp_port}: {e}") from None
        try:
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except OSError:
            pass
        return sock

    def _converse(self, sock: socket.socket) -> None:
        # --- OFFER -> ACCEPT / REJECT
        offer = Offer(
            transfer_id=self.transfer_id,
            sender_id=self._sender_id,
            sender_name=self._sender_name,
            name=self._offer_name,
            size=self._size,
            sha256=self._sha256,
        )
        self._send_all(sock, encode_frame(FrameType.OFFER, make_offer(offer)))

        frame_type, payload = self._read_reply(sock, ACCEPT_WAIT_TIMEOUT_S)
        if frame_type is FrameType.REJECT:
            reason, message = self._parse(sock, lambda: parse_reject(payload, self.transfer_id))
            raise _Stop(reason, _reason_text(reason, message))
        if frame_type is FrameType.CANCEL:
            self._stop_for_cancel(sock, payload)
        if frame_type is not FrameType.ACCEPT:
            self._protocol_violation(sock, f"Bên nhận trả lời OFFER bằng khung {frame_type.name}")

        offset = self._parse(sock, lambda: parse_accept(payload, self.transfer_id, self._size))
        self._accepted_once = True
        self._emit(TransferStarted(
            transfer_id=self.transfer_id,
            direction=Direction.SEND,
            peer_name=self._peer.name,
            file_name=self._offer_name,
            size=self._size,
            offset=offset,
        ))

        # --- DATA
        self._send_data(sock, offset)

        # --- DONE -> RESULT
        self._send_all(sock, encode_frame(FrameType.DONE, make_done(self.transfer_id)))
        frame_type, payload = self._read_reply(sock, RESULT_WAIT_TIMEOUT_S)
        if frame_type is FrameType.CANCEL:
            self._stop_for_cancel(sock, payload)
        if frame_type is not FrameType.RESULT:
            self._protocol_violation(sock, f"Bên nhận trả lời DONE bằng khung {frame_type.name}")

        ok, reason = self._parse(sock, lambda: parse_result(payload, self.transfer_id))
        if not ok:
            raise _Stop(reason, _reason_text(reason))

    def _send_data(self, sock: socket.socket, offset: int) -> None:
        pos = offset
        sent_this_attempt = 0
        started_at = time.monotonic()
        try:
            f = open(self._path, "rb")
        except OSError as e:
            self._abort(sock, Reason.BAD_REQUEST, f"Không đọc được file: {e}")
        with f:
            try:
                f.seek(offset)
            except OSError as e:
                self._abort(sock, Reason.BAD_REQUEST, f"Không đọc được file: {e}")
            while pos < self._size:
                self._raise_if_cancelled(sock)
                self._poll_incoming(sock)

                try:
                    data = f.read(min(self._chunk_size, self._size - pos))
                except OSError as e:
                    self._abort(sock, Reason.BAD_REQUEST, f"Không đọc được file: {e}")
                if not data:
                    self._abort(sock, Reason.BAD_REQUEST,
                                "File bị cắt ngắn trong lúc gửi nên không thể gửi tiếp.")

                self._send_all(sock, encode_frame(FrameType.DATA, data))
                pos += len(data)
                sent_this_attempt += len(data)
                self._made_progress = True
                self._report_progress(pos, sent_this_attempt, started_at)

    # ----------------------------------------------------------------- Sự kiện

    def _status(self, text: str) -> None:
        self._emit(StatusMessage(text, self.transfer_id))

    def _report_progress(self, done: int, sent_now: int, started_at: float) -> None:
        now = time.monotonic()
        if now - self._last_progress_at < 1.0 / PROGRESS_MAX_PER_SECOND:
            return
        self._last_progress_at = now
        elapsed = now - started_at
        speed = sent_now / elapsed if elapsed > 0 else 0.0
        self._emit(TransferProgress(self.transfer_id, done, self._size, speed))

    def _finish(self, ok: bool, reason: Reason | None = None, message: str | None = None) -> None:
        """Phát TransferFinished đúng một lần cho mỗi lượt."""
        if self._finished:
            return
        self._finished = True
        self._emit(TransferFinished(
            transfer_id=self.transfer_id,
            direction=Direction.SEND,
            ok=ok,
            reason=reason,
            message=message,
        ))

    # ----------------------------------------------------------------- Đọc và ghi socket

    def _raise_if_cancelled(self, sock: socket.socket | None = None) -> None:
        if not self._cancel.is_set():
            return
        if sock is not None:
            self._best_effort_cancel(sock, Reason.CANCELLED)
        raise _Stop(Reason.CANCELLED, "Bạn đã hủy lượt gửi.")

    def _best_effort_cancel(self, sock: socket.socket, reason: Reason) -> None:
        """Báo cho bên nhận biết mình dừng. Không được làm hỏng việc kết thúc nếu gửi không nổi."""
        try:
            sock.settimeout(1.0)
            sock.sendall(encode_frame(FrameType.CANCEL, make_cancel(self.transfer_id, reason)))
        except OSError:
            pass

    def _abort(self, sock: socket.socket, reason: Reason, message: str) -> None:
        self._best_effort_cancel(sock, reason)
        raise _Stop(reason, message)

    def _send_all(self, sock: socket.socket, data: bytes) -> None:
        """Gửi hết `data`, nhưng thức dậy mỗi POLL_INTERVAL_S để nhìn cờ hủy.

        sendall thường sẽ chặn tới 15 giây nếu bên nhận ngừng đọc (bộ đệm TCP đầy — TCP/IP Sockets
        mục 5.2), và trong lúc đó nút Hủy không có tác dụng. Vòng lặp này sửa chuyện đó.
        """
        view = memoryview(data)
        sock.settimeout(POLL_INTERVAL_S)
        last_progress = time.monotonic()
        while view:
            try:
                n = sock.send(view)
            except socket.timeout:
                # Đang dở một khung (đã ghi một phần) thì không chen CANCEL vào được: chỉ dừng và đóng.
                self._raise_if_cancelled(sock if len(view) == len(data) else None)
                if time.monotonic() - last_progress > IDLE_TIMEOUT_S:
                    raise _ConnectionLost(
                        f"bên nhận không đọc dữ liệu suốt {IDLE_TIMEOUT_S:g} giây"
                    ) from None
                continue
            except OSError as e:
                raise _ConnectionLost(str(e)) from None
            if n == 0:
                raise _ConnectionLost("socket không gửi được byte nào")
            view = view[n:]
            last_progress = time.monotonic()

    def _read_reply(self, sock: socket.socket, timeout_s: float) -> tuple[FrameType, bytes]:
        """Chờ một khung từ bên nhận tối đa timeout_s, vẫn nhìn cờ hủy mỗi POLL_INTERVAL_S.

        Chờ bằng select rồi mới read_frame, thay vì đặt timeout ngắn lên recv: recv hết giờ giữa
        chừng một khung sẽ làm mất những byte đã đọc và hỏng đóng khung.
        """
        deadline = time.monotonic() + timeout_s
        while True:
            self._raise_if_cancelled(sock)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                self._best_effort_cancel(sock, Reason.TIMEOUT)
                raise _Stop(
                    Reason.TIMEOUT,
                    f"{self._peer.name} không trả lời sau {timeout_s:g} giây.",
                )
            try:
                readable, _, _ = select.select([sock], [], [], min(POLL_INTERVAL_S, remaining))
            except (OSError, ValueError) as e:
                raise _ConnectionLost(str(e)) from None
            if readable:
                return self._read_frame(sock)

    def _read_frame(self, sock: socket.socket) -> tuple[FrameType, bytes]:
        sock.settimeout(IDLE_TIMEOUT_S)
        try:
            return read_frame(sock)
        except FrameError as e:
            self._protocol_violation(sock, str(e))
        except (ConnectionClosed, OSError) as e:
            raise _ConnectionLost(str(e)) from None
        raise AssertionError("không tới được đây")           # pragma: no cover

    def _poll_incoming(self, sock: socket.socket) -> None:
        """Giữa hai khối DATA: bên nhận có gửi gì không? Chỉ CANCEL là hợp lệ lúc này."""
        try:
            readable, _, _ = select.select([sock], [], [], 0)
        except (OSError, ValueError) as e:
            raise _ConnectionLost(str(e)) from None
        if not readable:
            return
        frame_type, payload = self._read_frame(sock)
        if frame_type is FrameType.CANCEL:
            self._stop_for_cancel(sock, payload)
        self._protocol_violation(sock, f"Bên nhận gửi khung {frame_type.name} khi đang nhận DATA")

    def _look_for_cancel(self, sock: socket.socket) -> None:
        """Kết nối vừa đứt giữa chừng. Bên nhận có kịp để lại một CANCEL (hết chỗ, đang tắt...) không?

        Có thì đó là lý do thật, và thử lại vô ích. Cố gắng hết sức, không có thì thôi.
        """
        try:
            readable, _, _ = select.select([sock], [], [], 0.2)
            if not readable:
                return
            sock.settimeout(1.0)
            frame_type, payload = read_frame(sock)
        except (OSError, ConnectionClosed, FrameError, ValueError):
            return
        if frame_type is FrameType.CANCEL:
            try:
                reason = parse_cancel(payload, self.transfer_id)
            except ProtocolError:
                return
            raise _Stop(reason, _reason_text(reason)) from None

    # ----------------------------------------------------------------- Xử lý khung lạ

    def _parse(self, sock: socket.socket, parse):
        """Chạy một hàm parse_*; thông điệp sai định dạng là vi phạm giao thức của bên nhận."""
        try:
            return parse()
        except ProtocolError as e:
            self._protocol_violation(sock, str(e))

    def _protocol_violation(self, sock: socket.socket, detail: str) -> None:
        """docs/03 mục 4.2, 4.3: khung hay thông điệp sai -> CANCEL bad_request rồi đóng."""
        self._abort(sock, Reason.BAD_REQUEST, f"Máy nhận vi phạm giao thức: {detail}")

    def _stop_for_cancel(self, sock: socket.socket, payload: bytes) -> None:
        reason = self._parse(sock, lambda: parse_cancel(payload, self.transfer_id))
        raise _Stop(reason, _reason_text(reason))


class TcpSender:
    """Cầu nối giữa hợp đồng Sender của lõi (core.service.Sender) và FileSender.

    Lõi gọi send(job) trên luồng riêng; hàm này dựng một FileSender cho job đó và chạy tới khi xong.
    Cờ job.cancelled của lõi được dùng chung làm cờ hủy của FileSender, nên service.cancel()
    có tác dụng ngay mà lõi không cần gọi FileSender.cancel().

    R1 ghép vào lõi ở T25:  TruyenNhanhService(config, sender=TcpSender(service_id, device_name))
    Lưu ý cho R1: FileSender báo kết quả bằng TransferFinished qua job.emit, nên nếu sổ lượt truyền
    của lõi cần được cập nhật thì lõi phải bọc job.emit (hoặc bắt TransferFinished) để gọi _finish.
    """

    def __init__(self, sender_id: str, sender_name: str) -> None:
        self._sender_id = sender_id
        self._sender_name = sender_name

    def send(self, job) -> None:
        FileSender(
            transfer_id=job.transfer_id,
            sender_id=self._sender_id,
            sender_name=self._sender_name,
            peer=job.peer,
            path=job.path,
            config=Config(chunk_size=job.chunk_size),
            emit=job.emit,
            as_name=job.as_name,
            cancel_event=job.cancelled,
        ).run()
