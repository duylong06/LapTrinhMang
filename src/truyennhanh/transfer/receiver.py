"""Bên nhận: máy chủ TCP nhận file — docs/03 mục 4.

Phụ trách: R4 · Nhiệm vụ: T20, T21 (tuần 2), T27, T28 (tuần 3), T37 (tuần 4)

Một luồng chấp nhận kết nối; MỖI kết nối được xử lý trên một luồng riêng, để một máy gửi
bị treo không chặn máy khác. Mỗi kết nối đi qua 5 trạng thái ở docs/03 mục 4.4:
chờ OFFER -> chờ quyết định -> nhận dữ liệu -> kiểm tra -> kết thúc.

Mọi thứ đến từ mạng là KHÔNG ĐÁNG TIN. Làm đủ 9 kiểm tra ở docs/03 mục 4.9.
Lỗi ở một kết nối không được làm sập máy chủ.

Đọc thêm: TCP/IP Sockets in C# mục 4.3 Threads, 4.6 Closing Connections.
"""
from __future__ import annotations

import errno
import hashlib
import logging
import os
import socket
import threading
import time
from contextlib import nullcontext
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from truyennhanh.config import Config, default_download_dir
from truyennhanh.core.events import (
    Emit,
    StatusMessage,
    TransferFinished,
    TransferProgress,
    TransferStarted,
)
from truyennhanh.core.models import Direction
from truyennhanh.protocol.constants import (
    DECISION_TIMEOUT_S,
    IDLE_TIMEOUT_S,
    PROGRESS_MAX_PER_SECOND,
    FrameType,
    Reason,
)
from truyennhanh.protocol.framing import ConnectionClosed, FrameError, read_frame, send_frame
from truyennhanh.protocol.messages import (
    Offer,
    ProtocolError,
    UnsupportedVersion,
    decode_json,
    make_accept,
    make_cancel,
    make_reject,
    make_result,
    parse_cancel,
    parse_done,
    parse_offer,
)
from truyennhanh.transfer.filenames import sanitize_filename
from truyennhanh.transfer.hashing import sha256_prefix
from truyennhanh.transfer.storage import (
    FileLocks,
    cleanup_old_parts,
    finalize,
    has_free_space,
    part_path,
    resume_offset,
)

_log = logging.getLogger(__name__)

LISTEN_BACKLOG = 16
"""Độ dài hàng chờ các kết nối chưa được accept(). Không phải giới hạn số kết nối đồng thời."""

ACCEPT_POLL_S = 0.1
"""Chu kỳ luồng chấp nhận tỉnh dậy để xem máy chủ có đang dừng không.

Không thể trông chờ việc đóng socket từ luồng khác sẽ đánh thức accept() đang chờ: trên Linux
và macOS nó có thể không đánh thức. Đặt hạn chờ ngắn rồi kiểm tra cờ dừng thì chạy đúng trên
mọi hệ điều hành; cái giá là stop() có thể mất tới ACCEPT_POLL_S giây.
"""

STOP_GRACE_S = 2.0
"""stop() chờ các kết nối tự kết thúc sau khi đã gửi CANCEL; hết hạn này thì đóng cưỡng bức."""

CLOSE_DRAIN_S = 2.0
CLOSE_DRAIN_MAX_BYTES = 1024 * 1024
"""Đóng nhẹ nhàng: sau khi gửi xong, đọc bỏ dữ liệu bên kia còn gửi tối đa chừng này giây/byte
trước khi close(). Xem _close_gracefully."""

DECISION_TOLERANCE_S = 0.5
"""Sai số khi đoán lý do ask_user trả về False (xem _decline_reason)."""

_REJECT_MESSAGES = {
    Reason.USER_DECLINED: "Người nhận đã từ chối.",
    Reason.TIMEOUT: "Người nhận không trả lời kịp.",
    Reason.BUSY: "Máy nhận đang nhận đúng file này ở một lượt khác.",
    Reason.INSUFFICIENT_SPACE: "Ổ đĩa của máy nhận không còn đủ chỗ trống.",
}


def _decline_reason(waited_s: float) -> Reason:
    """Lý do REJECT khi ask_user trả về False.

    ask_user chỉ trả về bool, không cho biết người dùng bấm Từ chối hay hết giờ. Lõi chờ đúng
    DECISION_TIMEOUT_S rồi mới trả về False khi hết giờ, nên chờ gần đủ chừng đó là hết giờ.
    Cách sạch hơn là cho ask_user trả về Reason: đề nghị R1 nếu muốn đổi.
    """
    if waited_s >= DECISION_TIMEOUT_S - DECISION_TOLERANCE_S:
        return Reason.TIMEOUT
    return Reason.USER_DECLINED


AskUser = Callable[[Offer, str, int], bool]
"""ask_user(offer, tên_đã_làm_sạch, resume_offset) -> True nếu người dùng đồng ý.

Do lõi cung cấp. Hàm này CHẶN tối đa DECISION_TIMEOUT_S (lõi phát OfferReceived rồi chờ
trên một threading.Event); hết giờ thì trả về False và bên nhận gửi REJECT timeout.
"""


@dataclass
class _Session:
    """Một lượt truyền đang chạy trên một kết nối, tính từ lúc có OFFER hợp lệ."""

    transfer_id: str
    send_lock: threading.Lock = field(default_factory=threading.Lock)
    """Hai luồng cùng sendall() lên một socket thì các byte có thể đan xen nhau.
    Luồng của kết nối và luồng gọi cancel()/stop() đều có thể gửi, nên phải khóa."""
    cancel_reason: Reason | None = None
    """Khác None nghĩa là lượt này đã bị hủy từ phía mình (cancel() hoặc stop())."""


class FileReceiverServer:
    """Lắng nghe config.transfer_port; cổng bận thì để hệ điều hành chọn (bind cổng 0)."""

    def __init__(
        self,
        config: Config,
        emit: Emit,
        ask_user: AskUser,
        *,
        get_download_dir: Callable[[], Path] | None = None,
    ) -> None:
        """get_download_dir: hàm trả về thư mục nhận hiện tại, được gọi MỖI lượt nhận.

        Lõi nên truyền service.get_download_dir vào đây: service.set_download_dir() chỉ đổi thư mục
        trong lõi chứ không sửa config.download_dir. Không truyền thì dùng config.download_dir,
        và default_download_dir() nếu config để None.
        """
        self._config = config
        self._emit = emit
        self._ask_user = ask_user
        self._get_download_dir = get_download_dir

        # --- BỔ SUNG CÁC THUỘC TÍNH SAU ĐỂ PYLANCE NHẬN DIỆN ---
        self._server_socket: socket.socket | None = None
        self._accept_thread: threading.Thread | None = None
        self._port: int = 0
        
        # Các thành phần quản lý luồng và trạng thái
        self._stopping = threading.Event()
        self._lock = threading.Lock()
        self._sessions: dict[socket.socket, _Session] = {}
        self._connections: set[socket.socket] = set()
        self._threads: set[threading.Thread] = set()

        # T28 bước 8 mục 4.9: không cho hai lượt cùng sha256 ghi vào một .part.
        # Khóa theo mã băm vì .part được đặt tên theo mã băm, nên hai máy gửi
        # cùng một file với hai tên khác nhau vẫn đụng đúng một file.
        self._locks = FileLocks()

        # T27, docs/03 mục 4.5: (sender_id, sha256) mà người dùng đã đồng ý trong
        # lần chạy này. Nối lại để truyền tiếp thì tự đồng ý, không hỏi lại.
        #
        # Không chỉ để đỡ phiền: mục 4.7 ghi rõ bên gửi chỉ chờ ACCEPT 65 giây,
        # mà băm lại phần đã có cộng thời gian người dùng suy nghĩ lần hai thì
        # rất dễ vượt mốc đó và lượt truyền hỏng hẳn.
        self._auto_accept: set[tuple[str, str]] = set()

    @property
    def port(self) -> int:
        """Cổng thực tế máy chủ đang lắng nghe. Ném RuntimeError nếu chưa start()."""
        if self._server_socket is None:
            raise RuntimeError("Máy chủ chưa start()")
        return self._port
    
    @property
    def _download_dir(self) -> Path:
        if self._get_download_dir is not None:
            return Path(self._get_download_dir())
        configured = self._config.download_dir
        return Path(configured) if configured is not None else default_download_dir()

    @staticmethod
    def _bind(port: int) -> socket.socket:
        """Tạo socket TCP và bind vào mọi card mạng ở cổng đã cho. Lỗi thì đóng socket rồi ném tiếp.

        Không đặt SO_REUSEADDR trên Windows: ở đó nó cho hai tiến trình cùng bind một cổng,
        nên ứng dụng thứ hai không bao giờ thấy "cổng bận". Trên Linux/macOS nó chỉ giúp bind
        lại ngay sau khi vừa tắt ứng dụng, không có hại.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            if os.name != "nt":
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("0.0.0.0", port))
        except OSError:
            sock.close()
            raise
        return sock

    def start(self) -> int:
        """Mở socket lắng nghe, bật luồng chấp nhận. Trả về cổng thật."""
        if self._server_socket is not None:
            raise RuntimeError("Máy chủ đã start() rồi")

        wanted = self._config.transfer_port
        try:
            sock = self._bind(wanted)
        except OSError:
            if wanted == 0:  # đã xin hệ điều hành chọn cổng mà vẫn lỗi thì không còn đường lùi
                raise
            sock = self._bind(0)
            self._emit(StatusMessage(
                f"Cổng {wanted} đang bận, dùng cổng {sock.getsockname()[1]} thay thế."
            ))

        sock.listen(LISTEN_BACKLOG)
        sock.settimeout(ACCEPT_POLL_S)  # xem ACCEPT_POLL_S; socket nhận về từ accept() vẫn ở chế độ chặn
        self._server_socket = sock
        self._port = sock.getsockname()[1]

        self._stopping.clear()  # cho phép start() lại sau stop()
        self._accept_thread = threading.Thread(
            target=self._accept_loop, args=(sock,), name="receiver-accept", daemon=True
        )
        self._accept_thread.start()

        # T37: dọn .part bỏ quên từ những lần chạy trước. Làm sau khi đã lắng
        # nghe xong để một thư mục nhận chậm không làm trễ việc mở cổng, và
        # nuốt mọi lỗi vì dọn dẹp thất bại không phải lý do để không nhận file.
        try:
            removed = cleanup_old_parts(self._download_dir)
            if removed:
                self._emit(StatusMessage(f"Đã dọn {removed} file .part quá hạn."))
        except OSError:
            _log.warning("Không dọn được .part cũ", exc_info=True)

        return self._port

    def stop(self) -> None:
        """Ngừng nhận kết nối mới; gửi CANCEL shutting_down cho các lượt đang chạy; giữ .part.

        Thứ tự: ngừng nhận kết nối mới -> CANCEL từng lượt đang chạy (bên gửi đóng kết nối theo
        docs/03 mục 4.6) -> chờ tối đa STOP_GRACE_S cho các luồng tự kết thúc -> đóng cưỡng bức
        phần còn sót. Gọi hai lần hoặc gọi khi chưa start() đều không lỗi.
        """
        self._stopping.set()

        # Đặt về None trước khi đóng; gọi hai lần hoặc gọi khi chưa start() đều không lỗi.
        sock, self._server_socket = self._server_socket, None
        thread, self._accept_thread = self._accept_thread, None
        if thread is not None:
            thread.join(timeout=ACCEPT_POLL_S * 4)
        if sock is not None:
            sock.close()

        with self._lock:
            sessions = list(self._sessions.items())
            connections = list(self._connections)
            threads = list(self._threads)

        for conn, session in sessions:
            self._cancel_session(conn, session, Reason.SHUTTING_DOWN)

        # Kết nối chưa có OFFER thì chưa có gì để hủy: đóng luôn.
        in_session = {conn for conn, _ in sessions}
        for conn in connections:
            if conn not in in_session:
                self._close_quietly(conn)

        deadline = time.monotonic() + STOP_GRACE_S
        for t in threads:
            t.join(timeout=max(0.0, deadline - time.monotonic()))

        with self._lock:
            leftovers = list(self._connections)
        for conn in leftovers:
            self._close_quietly(conn)

        for t in threads:
            if t.is_alive():
                t.join(timeout=1.0)

    def cancel(self, transfer_id: str) -> None:
        """Hủy một lượt đang nhận: gửi CANCEL cancelled, đóng kết nối, giữ .part.

        transfer_id không còn (lượt đã xong hoặc đã bị hủy) là chuyện bình thường khi người dùng
        bấm Hủy đúng lúc lượt kết thúc, nên không ném lỗi.
        """
        with self._lock:
            targets = [(conn, s) for conn, s in self._sessions.items() if s.transfer_id == transfer_id]
        if not targets:
            _log.info("cancel(): không có lượt nào đang chạy với transfer_id này")
        for conn, session in targets:
            self._cancel_session(conn, session, Reason.CANCELLED)

    # ------------------------------------------------------------------ luồng chấp nhận

    def _accept_loop(self, server_sock: socket.socket) -> None:
        """Chỉ nhận kết nối và giao cho luồng riêng. Không làm việc nặng ở đây, vì một kết nối
        chậm mà chiếm luồng này thì mọi máy khác không vào được."""
        while not self._stopping.is_set():
            try:
                conn, addr = server_sock.accept()
            except socket.timeout:
                continue  # hết chu kỳ chờ: quay lại kiểm tra cờ dừng
            except OSError:
                if self._stopping.is_set():
                    return
                time.sleep(0.1)  # lỗi tạm (ví dụ hết file handle): đừng quay vòng ăn hết CPU
                continue

            thread = threading.Thread(
                target=self._serve_connection,
                args=(conn, addr),
                name=f"receiver-conn-{addr[0]}:{addr[1]}",
                daemon=True,
            )
            with self._lock:
                self._threads.add(thread)
            thread.start()

    # ------------------------------------------------------------------ luồng của từng kết nối

    def _serve_connection(self, conn: socket.socket, addr: tuple) -> None:
        """Vỏ bọc an toàn quanh một kết nối: ghi nhận, chạy, bắt mọi lỗi, luôn đóng."""
        try:
            with self._lock:
                if self._stopping.is_set():  # stop() chạy xen vào giữa accept() và đây
                    self._close_quietly(conn)
                    return
                self._connections.add(conn)
            try:
                self._handle_connection(conn, addr)
            except Exception:  # lỗi ở một kết nối không được làm sập máy chủ
                _log.exception("Lỗi khi xử lý kết nối từ %s:%s", addr[0], addr[1])
            finally:
                self._close_gracefully(conn)
                with self._lock:
                    self._connections.discard(conn)
        finally:
            with self._lock:
                self._threads.discard(threading.current_thread())

    def _handle_connection(self, conn: socket.socket, addr: tuple) -> None:
        """Xử lý một kết nối từ đầu đến cuối (docs/03 mục 4.4)."""
        # Hạn chờ áp dụng cho TỪNG lần recv(): im lặng quá IDLE_TIMEOUT_S thì read_frame ném socket.timeout.
        conn.settimeout(IDLE_TIMEOUT_S)

        offer = self._read_offer(conn, addr)
        if offer is None:
            return

        session = _Session(offer.transfer_id)
        with self._lock:
            self._sessions[conn] = session
        try:
            if self._stopping.is_set():  # stop() đã chụp danh sách lượt trước khi lượt này được ghi nhận
                self._cancel_session(conn, session, Reason.SHUTTING_DOWN)
                return
            self._on_offer(conn, addr, offer)
        finally:
            with self._lock:
                self._sessions.pop(conn, None)

    def _read_offer(self, conn: socket.socket, addr: tuple) -> Offer | None:
        """Chờ khung đầu tiên, phải là OFFER hợp lệ. Trả về None nếu kết nối phải bị bỏ.

        Không tin gì từ mạng (docs/03 mục 4.9):
        - im lặng, đóng giữa chừng, khung khổng lồ hoặc loại lạ: đóng, không trả lời
        - khung đầu không phải OFFER: đóng, không trả lời
        - OFFER sai: REJECT bad_request (hoặc unsupported_version nếu chỉ sai phiên bản) rồi đóng
        Không ghi nội dung nhận được vào log, để kẻ gửi không chèn được dòng giả vào log.
        """
        try:
            frame_type, payload = read_frame(conn)
        except socket.timeout:  # phải đứng trước OSError, vì timeout cũng là một OSError
            _log.info("%s:%s im lặng quá %s giây, đóng kết nối", addr[0], addr[1], IDLE_TIMEOUT_S)
            return None
        except (ConnectionClosed, FrameError, OSError) as exc:
            _log.info("%s:%s bị bỏ ở khung đầu tiên (%s)", addr[0], addr[1], type(exc).__name__)
            return None

        if frame_type is not FrameType.OFFER:
            _log.info("%s:%s gửi %s trước OFFER, đóng kết nối", addr[0], addr[1], frame_type.name)
            return None

        try:
            return parse_offer(payload)
        except UnsupportedVersion:  # phải đứng trước ProtocolError, vì nó là lớp con
            self._reject(conn, payload, Reason.UNSUPPORTED_VERSION,
                         "Hai máy dùng phiên bản giao thức khác nhau.")
        except (ProtocolError, RecursionError):  # RecursionError: JSON lồng nhau quá sâu
            self._reject(conn, payload, Reason.BAD_REQUEST, "Yêu cầu gửi file không hợp lệ.")
        return None

    def _on_offer(self, conn: socket.socket, addr: tuple, offer: Offer) -> None:
        """Một OFFER hợp lệ đã tới: hỏi người dùng, rồi ACCEPT hoặc REJECT (docs/03 mục 4.4, trạng thái 2).

        Hàm này chạy trên luồng riêng của kết nối nên ask_user được phép chặn tới 60 giây
        mà không ảnh hưởng máy khác.
        """
        safe_name = sanitize_filename(offer.name)

        # T28 bước 8: giữ khóa TRƯỚC khi đọc .part. Đọc trước rồi mới khóa thì
        # hai lượt cùng mã băm có thể cùng đọc ra một offset rồi cùng ghi đè nhau.
        if not self._locks.acquire(offer.sha256):
            self._reject_with(conn, addr, offer, Reason.BUSY)
            return

        try:
            offset = self._resume_offset(offer)

            # T28 bước 7: chỉ cần chỗ cho phần CÒN LẠI, phần đã nằm trong .part
            # thì đã chiếm chỗ rồi.
            if not has_free_space(self._download_dir, offer.size - offset):
                self._reject_with(conn, addr, offer, Reason.INSUFFICIENT_SPACE)
                return

            # T27 mục 4.5: đúng file này từ đúng máy này, người dùng đã đồng ý
            # rồi thì không hỏi lại. Mọi trường hợp khác PHẢI hỏi.
            dau_moi = (offer.sender_id, offer.sha256)
            with self._lock:
                tu_dong = dau_moi in self._auto_accept

            if tu_dong:
                accepted, waited = True, 0.0
            else:
                started = time.monotonic()
                accepted = self._ask_user(offer, safe_name, offset)
                waited = time.monotonic() - started

            with self._lock:
                session = self._sessions.get(conn)
            if session is not None and session.cancel_reason is not None:
                return  # đã bị hủy trong lúc chờ người dùng: bên gửi đã nhận CANCEL, không ACCEPT nữa

            if not accepted:
                reason = _decline_reason(waited)
                self._send_quietly(conn, addr, FrameType.REJECT,
                                   make_reject(offer.transfer_id, reason, _REJECT_MESSAGES[reason]))
                return

            if not self._send_quietly(conn, addr, FrameType.ACCEPT, make_accept(offer.transfer_id, offset)):
                self._emit(TransferFinished(offer.transfer_id, Direction.RECEIVE, False, Reason.TIMEOUT, None,
                                            "Máy gửi đã ngắt kết nối trước khi nhận được câu trả lời."))
                return

            # Ghi nhớ SAU khi đã ACCEPT: người dùng đồng ý mà kết nối đứt ngay
            # thì lần nối lại tiếp theo mới được tự đồng ý.
            with self._lock:
                self._auto_accept.add(dau_moi)

            outcome = self._receive_file(conn, addr, offer, safe_name, offset)

            # Chỉ quên dấu mốc khi lượt đã khép lại HẲN: nhận xong, hoặc mã băm
            # lệch nên .part đã bị xóa. Mọi kết thúc còn giữ .part (mất kết nối,
            # thiếu byte, bị huỷ) đều có thể truyền tiếp, nên giữ dấu mốc lại —
            # quên ở đây thì lần nối lại sẽ hỏi người dùng lần nữa, đúng thứ mà
            # mục 4.5 bảo nên tránh.
            if outcome.ok or outcome.reason is Reason.HASH_MISMATCH:
                with self._lock:
                    self._auto_accept.discard(dau_moi)
        finally:
            # Nhả trên MỌI đường thoát, kể cả khi kết nối đứt giữa chừng: không
            # nhả thì mã băm đó bị khóa vĩnh viễn và lần truyền tiếp sau sẽ nhận
            # REJECT busy mãi mãi.
            self._locks.release(offer.sha256)

    def _reject_with(self, conn: socket.socket, addr: tuple, offer: Offer, reason: Reason) -> None:
        """REJECT một OFFER hợp lệ nhưng không phục vụ được lúc này (bận, hết chỗ)."""
        self._send_quietly(conn, addr, FrameType.REJECT,
                           make_reject(offer.transfer_id, reason, _REJECT_MESSAGES[reason]))

    # ------------------------------------------------------------------ nhận dữ liệu (T21)

    def _receive_file(self, conn: socket.socket, addr: tuple, offer: Offer, safe_name: str, offset: int) -> "_Outcome":
        """Trạng thái 3 và 4 của docs/03 mục 4.4: nhận DATA vào .part, nhận DONE, kiểm tra, trả RESULT.

        Phát TransferStarted rồi đúng MỘT TransferFinished, dù kết thúc kiểu nào: nếu không, giao diện
        sẽ treo ở "đang nhận" mãi.
        """
        self._emit(TransferStarted(
            transfer_id=offer.transfer_id,
            direction=Direction.RECEIVE,
            peer_name=_display_name(offer.sender_name),
            file_name=safe_name,
            size=offer.size,
            offset=offset,
        ))
        try:
            outcome = self._receive_data(conn, addr, offer, safe_name, offset)
        except Exception:  # lỗi bất ngờ: vẫn phải báo kết thúc
            _log.exception("Lỗi bất ngờ khi nhận file từ %s:%s", addr[0], addr[1])
            self._send_quietly(conn, addr, FrameType.CANCEL, make_cancel(offer.transfer_id, Reason.CANCELLED))
            outcome = _Outcome(False, Reason.CANCELLED, None,
                               "Có lỗi khi nhận file. File dở dang (nếu có) được giữ lại.")
        self._emit(TransferFinished(
            transfer_id=offer.transfer_id,
            direction=Direction.RECEIVE,
            ok=outcome.ok,
            reason=outcome.reason,
            saved_path=outcome.saved_path,
            message=outcome.message,
        ))
        return outcome

    def _receive_data(self, conn: socket.socket, addr: tuple, offer: Offer, safe_name: str, offset: int) -> _Outcome:
        download_dir = self._download_dir  # đọc mỗi lượt: người dùng có thể đổi thư mục nhận
        part = part_path(download_dir, offer.sha256)
        # T27 (docs/03 mục 4.5): truyền tiếp thì phải nạp phần đã có trong .part
        # vào bộ băm trước, rồi mới .update() tiếp các khối mới. Bắt đầu bằng một
        # bộ băm rỗng khi offset khác 0 thì mã băm cuối chắc chắn lệch, bước kiểm
        # tra sẽ báo hash_mismatch và xóa mất .part đang dở.
        if offset > 0:
            try:
                hasher = sha256_prefix(part, offset)
            except (OSError, ValueError):
                # Không băm lại được thì .part không đáng tin: bỏ, nhận lại từ đầu.
                _log.warning("Không băm lại được .part của %s, nhận lại từ đầu",
                             offer.sha256[:12])
                _remove_quietly(part)
                offset = 0
                hasher = hashlib.sha256()
        else:
            hasher = hashlib.sha256()

        state = _Receiving(offer, offset, offer.size - offset, hasher, time.monotonic())

        try:
            out = open(part, "wb" if offset == 0 else "ab")
        except OSError as exc:
            return self._cancel_with(conn, addr, offer, _disk_reason(exc),
                                     "Không ghi được file tạm trong thư mục nhận.")
        with out:  # phải đóng trước khi đổi tên hoặc xóa
            failure = self._pump_data(conn, addr, out, state)
        if failure is not None:
            return failure
        return self._verify_and_save(conn, addr, state, safe_name, download_dir, part)

    def _pump_data(self, conn: socket.socket, addr: tuple, out, state: _Receiving) -> _Outcome | None:
        """Đọc khung cho tới khi có DONE. Trả về None nếu DONE đã tới, ngược lại trả về kết quả thất bại.

        .part luôn được giữ lại trừ khi sai mã băm (xóa ở _verify_and_save), để còn truyền tiếp.
        """
        offer = state.offer
        while True:
            cancelled = self._cancelled_outcome(conn)
            if cancelled is not None:
                return cancelled
            try:
                frame_type, payload = read_frame(conn)
            except socket.timeout:  # phải đứng trước OSError, vì timeout cũng là một OSError
                return _Outcome(False, Reason.TIMEOUT, None, _MSG_IDLE)
            except FrameError:
                return self._cancel_with(conn, addr, offer, Reason.BAD_REQUEST, _MSG_BAD_DATA)
            except (ConnectionClosed, OSError):
                return self._cancelled_outcome(conn) or _Outcome(False, Reason.TIMEOUT, None, _MSG_LOST)

            if frame_type is FrameType.DATA:
                # Kiểm tra TRƯỚC khi ghi, để .part không bao giờ lớn hơn size đã khai (docs/03 mục 4.9).
                if state.received + len(payload) > state.expected:
                    return self._cancel_with(conn, addr, offer, Reason.BAD_REQUEST,
                                             "Máy gửi gửi nhiều dữ liệu hơn kích thước đã khai.")
                try:
                    out.write(payload)
                    out.flush()  # đẩy xuống file ngay: .part luôn phản ánh đúng số byte đã nhận, để còn truyền tiếp
                except OSError as exc:
                    return self._cancel_with(conn, addr, offer, _disk_reason(exc),
                                             "Không ghi được dữ liệu xuống đĩa (ổ đĩa đầy?). File dở dang được giữ lại.")
                state.hasher.update(payload)
                state.received += len(payload)
                self._emit_progress(state)
            elif frame_type is FrameType.DONE:
                try:
                    parse_done(payload, offer.transfer_id)
                except ProtocolError:
                    return self._cancel_with(conn, addr, offer, Reason.BAD_REQUEST, _MSG_BAD_DATA)
                return None
            elif frame_type is FrameType.CANCEL:
                try:
                    reason = parse_cancel(payload, offer.transfer_id)
                except ProtocolError:
                    reason = Reason.CANCELLED
                return _Outcome(False, reason, None, "Máy gửi đã hủy. File dở dang được giữ lại.")
            else:  # OFFER, ACCEPT, REJECT, RESULT không có chỗ ở đây
                return self._cancel_with(conn, addr, offer, Reason.BAD_REQUEST, _MSG_BAD_DATA)

    def _verify_and_save(self, conn: socket.socket, addr: tuple, state: _Receiving, safe_name: str,
                         download_dir: Path, part: Path) -> _Outcome:
        """Trạng thái 4: đủ byte, đúng mã băm thì đổi tên thành file thật; sai thì xóa .part."""
        offer = state.offer
        if state.received < state.expected:
            self._send_result(conn, addr, offer, Reason.INCOMPLETE)
            return _Outcome(False, Reason.INCOMPLETE, None,
                            "Máy gửi báo xong nhưng chưa đủ dữ liệu. File dở dang được giữ lại.")
        if state.hasher.hexdigest() != offer.sha256:
            _remove_quietly(part)
            self._send_result(conn, addr, offer, Reason.HASH_MISMATCH)
            return _Outcome(False, Reason.HASH_MISMATCH, None,
                            "File nhận về bị sai lệch (mã băm không khớp). Đã xóa file tạm, hãy gửi lại.")
        try:
            saved = finalize(part, download_dir, safe_name)
        except (OSError, ValueError) as exc:
            _log.warning("Không đổi tên được .part thành file thật (%s)", type(exc).__name__)
            reason = _disk_reason(exc)
            self._send_result(conn, addr, offer, reason)
            return _Outcome(False, reason, None, "Không lưu được file vào thư mục nhận. File tạm được giữ lại.")
        self._send_result(conn, addr, offer, None)
        return _Outcome(True, None, saved, f"Đã nhận xong {saved.name}")

    def _send_result(self, conn: socket.socket, addr: tuple, offer: Offer, reason: Reason | None) -> None:
        """RESULT ok=True nếu reason là None; ngược lại ok=False kèm reason."""
        self._send_quietly(conn, addr, FrameType.RESULT,
                           make_result(offer.transfer_id, reason is None, reason))

    def _cancel_with(self, conn: socket.socket, addr: tuple, offer: Offer, reason: Reason, message: str) -> _Outcome:
        """Gửi CANCEL cho bên gửi và trả về kết quả thất bại tương ứng. .part được giữ lại."""
        self._send_quietly(conn, addr, FrameType.CANCEL, make_cancel(offer.transfer_id, reason))
        return _Outcome(False, reason, None, message)

    def _cancelled_outcome(self, conn: socket.socket) -> _Outcome | None:
        """Lượt đã bị hủy từ phía mình (cancel() hoặc stop()) thì trả về kết quả; CANCEL đã được gửi rồi."""
        with self._lock:
            session = self._sessions.get(conn)
        if session is None or session.cancel_reason is None:
            return None
        if session.cancel_reason is Reason.SHUTTING_DOWN:
            message = "Ứng dụng đang tắt. File dở dang được giữ lại để truyền tiếp."
        else:
            message = "Đã hủy. File dở dang được giữ lại để truyền tiếp."
        return _Outcome(False, session.cancel_reason, None, message)

    def _emit_progress(self, state: _Receiving) -> None:
        """Phát TransferProgress, tối đa PROGRESS_MAX_PER_SECOND lần mỗi giây (docs/02, events.py)."""
        now = time.monotonic()
        if now - state.last_progress < 1.0 / PROGRESS_MAX_PER_SECOND:
            return
        state.last_progress = now
        elapsed = now - state.started
        speed = state.received / elapsed if elapsed > 0 else 0.0
        self._emit(TransferProgress(
            transfer_id=state.offer.transfer_id,
            done_bytes=state.offset + state.received,
            total_bytes=state.offer.size,
            bytes_per_second=speed,
        ))

    def _resume_offset(self, offer: Offer) -> int:
        """Vị trí bắt đầu nhận, theo bảng ở docs/03 mục 4.5 (T27).

        Một .part hỏng không được làm hỏng cả lượt nhận: đọc không nổi thì nhận
        lại từ đầu, vì nhận thừa vẫn ra file đúng, còn nhận thiếu thì không.
        """
        try:
            return resume_offset(self._download_dir, offer.sha256, offer.size)
        except (OSError, ValueError):
            _log.warning("Không đọc được .part của %s, nhận lại từ đầu", offer.sha256[:12])
            return 0

    # ------------------------------------------------------------------ gửi, hủy, đóng

    @staticmethod
    def _reject(conn: socket.socket, payload: bytes, reason: Reason, message: str) -> None:
        """Gửi REJECT cho một OFFER hỏng (chưa có lượt truyền nên chưa cần khóa), nuốt lỗi."""
        try:
            send_frame(conn, FrameType.REJECT,
                       make_reject(_best_effort_transfer_id(payload), reason, message))
        except OSError:
            pass

    def _send_quietly(self, conn: socket.socket, addr: tuple, frame_type: FrameType, payload: bytes) -> bool:
        """Gửi một khung của luồng kết nối; bên gửi đã bỏ đi thì ghi log và trả về False."""
        with self._lock:
            session = self._sessions.get(conn)
        guard = session.send_lock if session is not None else nullcontext()
        try:
            with guard:
                send_frame(conn, frame_type, payload)
            return True
        except OSError as exc:
            _log.info("%s:%s không gửi được %s (%s)", addr[0], addr[1], frame_type.name, type(exc).__name__)
            return False

    def _cancel_session(self, conn: socket.socket, session: _Session, reason: Reason) -> None:
        """Gửi CANCEL cho bên gửi rồi ngừng ghi (FIN đi sau CANCEL). Chỉ làm một lần cho mỗi lượt.

        Không đóng hẳn ở đây: docs/03 mục 4.6 cho bên nhận CANCEL cũng đóng, và luồng của kết nối
        sẽ đóng nhẹ nhàng khi nó kết thúc. Đóng ngay thì dữ liệu bên gửi còn đang gửi tới sẽ làm
        hệ điều hành gửi RST, có thể xóa mất CANCEL trước khi bên gửi kịp đọc.
        """
        with self._lock:
            if session.cancel_reason is not None:
                return
            session.cancel_reason = reason
        try:
            with session.send_lock:
                send_frame(conn, FrameType.CANCEL, make_cancel(session.transfer_id, reason))
        except OSError:
            pass  # bên gửi đã đi mất
        try:
            conn.shutdown(socket.SHUT_WR)
        except OSError:
            pass

    @staticmethod
    def _close_gracefully(conn: socket.socket) -> None:
        """Đóng kiểu "lingering" (TCP/IP Sockets in C#, mục 4.6).

        close() ngay khi còn dữ liệu chưa đọc thì hệ điều hành gửi RST, và RST có thể xóa mất
        REJECT/CANCEL/RESULT bên gửi chưa kịp đọc. Vì vậy: shutdown(SHUT_WR) để FIN đi sau dữ
        liệu đã gửi, đọc bỏ phần bên kia còn gửi (có giới hạn thời gian và dung lượng), rồi mới close().
        """
        try:
            conn.shutdown(socket.SHUT_WR)
            deadline = time.monotonic() + CLOSE_DRAIN_S
            drained = 0
            while drained < CLOSE_DRAIN_MAX_BYTES:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                conn.settimeout(remaining)
                data = conn.recv(4096)
                if not data:  # bên kia đã đóng
                    break
                drained += len(data)
        except OSError:
            pass  # bên kia đã ngắt, hết giờ, hoặc stop() đã đóng giúp
        finally:
            try:
                conn.close()
            except OSError:
                pass

    @staticmethod
    def _close_quietly(conn: socket.socket) -> None:
        """Đóng cưỡng bức, nuốt lỗi. shutdown() trước để đánh thức luồng đang chờ recv() trên nó
        (đóng suông từ luồng khác không đảm bảo đánh thức trên mọi hệ điều hành)."""
        try:
            conn.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass  # đã đóng hoặc đối phương đã ngắt
        try:
            conn.close()
        except OSError:
            pass


def _best_effort_transfer_id(payload: bytes) -> str:
    """transfer_id lấy từ OFFER hỏng, chỉ để REJECT có gì mà gửi lại; không lấy được thì trả "".

    Chỉ chấp nhận chuỗi ngắn: không phản hồi lại nguyên văn một chuỗi dài do kẻ lạ chọn.
    """
    try:
        value = decode_json(payload).get("transfer_id")
    except Exception:  # JSON hỏng, quá sâu (RecursionError)... đằng nào cũng đang xử lý một OFFER hỏng
        return ""
    return value if isinstance(value, str) and len(value) <= 64 else ""



_MSG_IDLE = "Máy gửi im lặng quá 15 giây. File dở dang được giữ lại để truyền tiếp."
_MSG_LOST = "Mất kết nối với máy gửi. File dở dang được giữ lại để truyền tiếp."
_MSG_BAD_DATA = "Máy gửi gửi dữ liệu sai quy định. File dở dang được giữ lại."

_DISK_FULL_ERRNOS = {e for e in (getattr(errno, "ENOSPC", None), getattr(errno, "EDQUOT", None)) if e is not None}


@dataclass
class _Outcome:
    """Kết quả cuối của một lượt nhận, để phát TransferFinished đúng một lần."""

    ok: bool
    reason: Reason | None = None
    saved_path: Path | None = None
    message: str | None = None


@dataclass
class _Receiving:
    """Số liệu của một lượt nhận đang chạy."""

    offer: Offer
    offset: int
    expected: int  # số byte DATA còn phải nhận = size - offset
    hasher: "hashlib._Hash"
    started: float
    received: int = 0
    last_progress: float = 0.0


def _display_name(name: str) -> str:
    """Tên máy gửi để HIỆN: bỏ ký tự không in được (điều khiển, đảo chiều chữ), cắt 64 ký tự."""
    cleaned = "".join(c for c in name if c.isprintable())[:64].strip()
    return cleaned or "(không rõ tên)"


def _remove_quietly(path: Path) -> None:
    try:
        path.unlink()
    except OSError:
        pass


def _disk_reason(exc: Exception) -> Reason:
    """Lý do gửi cho bên gửi khi lỗi nằm ở đĩa phía mình. Bảng lý do ở docs/03 mục 4.8 không có mã
    "lỗi đĩa", nên ổ đầy dùng insufficient_space, lỗi tên dùng bad_request, còn lại dùng cancelled."""
    if isinstance(exc, ValueError):
        return Reason.BAD_REQUEST
    if isinstance(exc, OSError) and exc.errno in _DISK_FULL_ERRNOS:
        return Reason.INSUFFICIENT_SPACE
    return Reason.CANCELLED