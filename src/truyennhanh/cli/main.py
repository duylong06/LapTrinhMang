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

from truyennhanh import __version__
from truyennhanh.protocol.constants import TRANSFER_PORT_DEFAULT


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


def cmd_scan(args: argparse.Namespace) -> int:
    raise NotImplementedError("T17 · R2")


def cmd_receive(args: argparse.Namespace) -> int:
    raise NotImplementedError("T17 · R2")


def cmd_send(args: argparse.Namespace) -> int:
    raise NotImplementedError("T17 · R2")


def cmd_ui(args: argparse.Namespace) -> int:
    raise NotImplementedError("T23, T30 · R5")


COMMANDS = {"scan": cmd_scan, "receive": cmd_receive, "send": cmd_send, "ui": cmd_ui}


def main(argv: list[str] | None = None) -> int:
    """Điểm vào của `python -m truyennhanh` và lệnh `truyennhanh`. Trả về mã thoát."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        print("\nDự án đang ở giai đoạn khung: các lệnh đã khai báo nhưng chưa được cài đặt.")
        print("Xem docs/04-phan-cong.md để biết ai làm phần nào.")
        return 0
    try:
        return COMMANDS[args.command](args)
    except NotImplementedError as e:
        print(f"Lệnh '{args.command}' chưa được cài đặt — nhiệm vụ {e}.")
        return 2
