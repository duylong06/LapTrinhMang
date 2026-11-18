"""Giao diện dòng lệnh — docs/02 mục 2.

Phụ trách: R2 · Nhiệm vụ: T17 (tuần 2), chuyển sang dùng lõi ở T25 (tuần 3)

Các lệnh đã được khai báo sẵn (đây là giao diện đã thống nhất, R6 viết test dựa vào nó);
phần xử lý của từng lệnh chưa được cài đặt.

    truyennhanh scan [--seconds 3]
    truyennhanh receive [--dir THƯ_MỤC] [--yes]
    truyennhanh send IP FILE [--port 50506] [--as-name TÊN]
    truyennhanh ui
"""
from __future__ import annotations

import argparse
import queue
import sys
import time
from pathlib import Path

from truyennhanh import __version__
from truyennhanh.config import Config
from truyennhanh.core.events import (
    OfferReceived,
    PeerFound,
    PeerLost,
    StatusMessage,
    TransferFinished,
    TransferProgress,
    TransferStarted,
)
from truyennhanh.protocol.constants import TRANSFER_PORT_DEFAULT

NHIP_CHO_S = 0.2
"""Chu kỳ lấy sự kiện ra khỏi hàng đợi. Đủ nhỏ để tiến độ chạy mượt trên màn hình."""


def build_parser() -> argparse.ArgumentParser:
    """Khai báo các lệnh và tham số."""
    p = argparse.ArgumentParser(
        prog="truyennhanh",
        description="Truyền Nhanh — gửi file trong mạng LAN không cần Internet.",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="command", metavar="LỆNH")

    s = sub.add_parser("scan", help="liệt kê các máy đang chạy Truyền Nhanh trong mạng")
    s.add_argument("--seconds", type=float, default=3.0, help="nghe trong bao nhiêu giây (mặc định 3)")

    r = sub.add_parser("receive", help="bật chế độ nhận file")
    r.add_argument("--dir", help="thư mục lưu file nhận được")
    r.add_argument("--yes", action="store_true", help="tự đồng ý mọi file, không hỏi")

    se = sub.add_parser("send", help="gửi một file tới máy có địa chỉ IP cho trước")
    se.add_argument("ip")
    se.add_argument("file")
    se.add_argument("--port", type=int, default=TRANSFER_PORT_DEFAULT)
    se.add_argument("--as-name", help="khai một tên file tùy ý trong OFFER — chỉ dùng để kiểm thử bảo mật (KT-28)")

    sub.add_parser("ui", help="mở giao diện đồ họa")
    return p


# --------------------------------------------------------------------------- Tiện ích hiển thị

def _goncao(n: int) -> str:
    """1536 -> '1,5 KB'. Dùng dấu phẩy thập phân cho đúng cách viết tiếng Việt."""
    for don_vi, nguong in (("GB", 1024**3), ("MB", 1024**2), ("KB", 1024)):
        if n >= nguong:
            return f"{n / nguong:.1f}".replace(".", ",") + f" {don_vi}"
    return f"{n} B"


_dang_ve = False
"""Có thanh tiến độ đang nằm trên dòng hiện tại hay không.

Không theo dõi thì _xoa_dong() in ra 78 dấu cách thừa trước mỗi dòng thông
báo, và khi hứng đầu ra vào file log thì cả file đầy khoảng trắng.
"""


def _ve_tien_do(xong: int, tong: int, toc_do: float) -> None:
    """Vẽ đè lên cùng một dòng bằng \\r, không cuộn màn hình."""
    global _dang_ve
    _dang_ve = True
    phan_tram = (xong / tong * 100) if tong else 100.0
    o_day = int(phan_tram / 4)
    thanh = "█" * o_day + "·" * (25 - o_day)
    sys.stdout.write(
        f"\r  [{thanh}] {phan_tram:5.1f}%  {_goncao(xong)}/{_goncao(tong)}  {_goncao(int(toc_do))}/s   "
    )
    sys.stdout.flush()


def _xoa_dong() -> None:
    """Xóa thanh tiến độ nếu đang có, để dòng chữ tiếp theo không đè lên nó."""
    global _dang_ve
    if not _dang_ve:
        return
    _dang_ve = False
    sys.stdout.write("\r" + " " * 78 + "\r")
    sys.stdout.flush()


def _tao_service(download_dir: str | None = None, transfer_port: int | None = None):
    """Dựng lõi thật. Nhập muộn để `--help` không phải nạp cả tầng mạng."""
    from truyennhanh.core.service import create_service

    return create_service(Config(
        download_dir=Path(download_dir).expanduser() if download_dir else None,
        transfer_port=TRANSFER_PORT_DEFAULT if transfer_port is None else transfer_port,
    ))


# --------------------------------------------------------------------------- Các lệnh

def cmd_scan(args: argparse.Namespace) -> int:
    # Cổng 0: chỉ đi dò tìm, không chiếm cổng nhận của bản đang chạy thật trên máy.
    service = _tao_service(transfer_port=0)
    service.start()
    print(f"Đang nghe {args.seconds:g} giây trên cổng dò tìm…\n")

    het_gio = time.monotonic() + args.seconds
    try:
        while time.monotonic() < het_gio:
            try:
                su_kien = service.events.get(timeout=NHIP_CHO_S)
            except queue.Empty:
                continue
            if isinstance(su_kien, PeerFound):
                may = su_kien.peer
                print(f"  + {may.name:<24} {may.ip}:{may.tcp_port}")
            elif isinstance(su_kien, PeerLost):
                print(f"  - máy {su_kien.peer_id[:8]}… đã rời mạng")
    except KeyboardInterrupt:
        pass

    danh_sach = service.list_peers()
    service.stop()

    if not danh_sach:
        print("Không thấy máy nào.\n")
        print("Thử: cả hai máy cùng mạng WiFi, đã mở tường lửa cho UDP 50505")
        print("(xem docs/huong-dan-tuong-lua.md), hoặc dùng `send` thẳng theo IP.")
        return 1

    print(f"\nThấy {len(danh_sach)} máy:\n")
    print(f"  {'TÊN MÁY':<24} {'ĐỊA CHỈ':<22} HỆ ĐIỀU HÀNH")
    for may in danh_sach:
        print(f"  {may.name:<24} {may.ip + ':' + str(may.tcp_port):<22} {may.os or '—'}")
    return 0


def cmd_receive(args: argparse.Namespace) -> int:
    service = _tao_service(download_dir=args.dir)
    service.start()

    thu_muc = service.get_download_dir()
    print(f"Đang nhận trên cổng {service._transfer_port}, lưu vào {thu_muc}")
    print("Nhấn Ctrl+C để dừng.\n")
    if args.yes:
        print("(chế độ --yes: tự đồng ý mọi file)\n")

    ma_thoat = 0
    try:
        while True:
            try:
                su_kien = service.events.get(timeout=NHIP_CHO_S)
            except queue.Empty:
                continue

            if isinstance(su_kien, OfferReceived):
                _xoa_dong()
                tiep = f", truyền tiếp từ {_goncao(su_kien.resume_offset)}" if su_kien.resume_offset else ""
                print(f"\n{su_kien.sender_name} muốn gửi '{su_kien.file_name}' "
                      f"({_goncao(su_kien.size)}{tiep})")
                if args.yes:
                    dong_y = True
                    print("  -> tự đồng ý")
                else:
                    try:
                        tra_loi = input("  Nhận file này? [y/N] ").strip().lower()
                    except EOFError:
                        tra_loi = ""
                    dong_y = tra_loi in ("y", "yes", "c", "có")
                service.respond_to_offer(su_kien.transfer_id, dong_y)
                if not dong_y:
                    print("  -> đã từ chối")

            elif isinstance(su_kien, TransferStarted):
                print(f"  Bắt đầu nhận '{su_kien.file_name}'")

            elif isinstance(su_kien, TransferProgress):
                _ve_tien_do(su_kien.done_bytes, su_kien.total_bytes, su_kien.bytes_per_second)

            elif isinstance(su_kien, TransferFinished):
                _xoa_dong()
                if su_kien.ok:
                    print(f"  Xong. Đã lưu: {su_kien.saved_path}\n")
                else:
                    ly_do = su_kien.reason.value if su_kien.reason else "không rõ"
                    print(f"  Thất bại ({ly_do}): {su_kien.message or ''}\n")
                    ma_thoat = 1

            elif isinstance(su_kien, StatusMessage):
                _xoa_dong()
                print(f"  {su_kien.text}")

    except KeyboardInterrupt:
        _xoa_dong()
        print("\nĐang dừng…")
    finally:
        service.stop()
    return ma_thoat


def cmd_send(args: argparse.Namespace) -> int:
    duong_dan = Path(args.file).expanduser()
    if not duong_dan.is_file():
        print(f"Không thấy file: {duong_dan}", file=sys.stderr)
        return 2

    # Cổng 0: lệnh send không cần lắng nghe, đừng tranh cổng 50506 với bản đang nhận.
    service = _tao_service(transfer_port=0)
    service.start()

    try:
        may = service.add_manual_peer(args.ip, args.port)
        print(f"Gửi '{duong_dan.name}' ({_goncao(duong_dan.stat().st_size)}) "
              f"tới {args.ip}:{args.port}")
        if args.as_name:
            print(f"  (khai tên trong OFFER là '{args.as_name}' — chế độ kiểm thử bảo mật)")
        transfer_id = service.send_file(may.id, duong_dan, as_name=args.as_name)
    except Exception as loi:        # noqa: BLE001 — lỗi thấy ngay, in cho người dùng
        print(f"Không gửi được: {loi}", file=sys.stderr)
        service.stop()
        return 2

    ma_thoat = 1
    try:
        while True:
            try:
                su_kien = service.events.get(timeout=NHIP_CHO_S)
            except queue.Empty:
                continue

            if isinstance(su_kien, TransferProgress) and su_kien.transfer_id == transfer_id:
                _ve_tien_do(su_kien.done_bytes, su_kien.total_bytes, su_kien.bytes_per_second)

            elif isinstance(su_kien, StatusMessage) and su_kien.transfer_id == transfer_id:
                _xoa_dong()
                print(f"  {su_kien.text}")

            elif isinstance(su_kien, TransferFinished) and su_kien.transfer_id == transfer_id:
                _xoa_dong()
                if su_kien.ok:
                    print("  Gửi xong, mã băm khớp.")
                    ma_thoat = 0
                else:
                    ly_do = su_kien.reason.value if su_kien.reason else "không rõ"
                    print(f"  Thất bại ({ly_do}): {su_kien.message or ''}", file=sys.stderr)
                break
    except KeyboardInterrupt:
        _xoa_dong()
        print("\nĐã hủy.")
        service.cancel(transfer_id)
    finally:
        service.stop()
    return ma_thoat


def cmd_ui(args: argparse.Namespace) -> int:
    try:
        from truyennhanh.gui.app import run_app
    except ImportError as loi:
        print(f"Không mở được giao diện: {loi}", file=sys.stderr)
        print("Trên Linux có thể cần cài gói python3-tk.", file=sys.stderr)
        return 2
    run_app()
    return 0


COMMANDS = {"scan": cmd_scan, "receive": cmd_receive, "send": cmd_send, "ui": cmd_ui}


def main(argv: list[str] | None = None) -> int:
    """Điểm vào của `python -m truyennhanh` và lệnh `truyennhanh`. Trả về mã thoát."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    try:
        return COMMANDS[args.command](args)
    except NotImplementedError as e:
        print(f"Lệnh '{args.command}' chưa được cài đặt — nhiệm vụ {e}.")
        return 2
