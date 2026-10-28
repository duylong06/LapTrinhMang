#!/usr/bin/env python3
"""So sánh hai thư mục theo đường dẫn tương đối và SHA-256 của từng file."""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

CHUNK_SIZE = 1024 * 1024


def list_files(root: Path) -> dict[str, Path]:
    """Liệt kê file thường bên trong root; khóa là đường dẫn tương đối dạng POSIX."""
    result: dict[str, Path] = {}
    for path in root.rglob("*"):
        # Không theo symbolic link để tránh vô tình đọc ngoài thư mục được chỉ định.
        if path.is_file() and not path.is_symlink():
            rel = path.relative_to(root).as_posix()
            result[rel] = path
    return result


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="So sánh file giữa hai thư mục bằng đường dẫn tương đối, dung lượng và SHA-256."
    )
    parser.add_argument("source", type=Path, help="Thư mục nguồn/original.")
    parser.add_argument("destination", type=Path, help="Thư mục đích/đã nhận.")
    args = parser.parse_args()

    source = args.source.expanduser().resolve()
    destination = args.destination.expanduser().resolve()
    for label, root in (("Nguồn", source), ("Đích", destination)):
        if not root.exists():
            print(f"LỖI: thư mục {label} không tồn tại: {root}", file=sys.stderr)
            return 2
        if not root.is_dir():
            print(f"LỖI: đường dẫn {label} không phải thư mục: {root}", file=sys.stderr)
            return 2

    try:
        source_files = list_files(source)
        destination_files = list_files(destination)
        source_names = set(source_files)
        destination_names = set(destination_files)
        only_source = sorted(source_names - destination_names)
        only_destination = sorted(destination_names - source_names)
        common = sorted(source_names & destination_names)

        matched = 0
        mismatched = 0
        errors = 0

        for rel in only_source:
            print(f"[THIẾU Ở ĐÍCH] {rel}")
        for rel in only_destination:
            print(f"[THỪA Ở ĐÍCH] {rel}")

        for rel in common:
            src = source_files[rel]
            dst = destination_files[rel]
            try:
                source_size = src.stat().st_size
                destination_size = dst.stat().st_size
                if source_size != destination_size:
                    mismatched += 1
                    print(
                        f"[LỆCH] {rel} — dung lượng nguồn={source_size:,} B, "
                        f"đích={destination_size:,} B"
                    )
                    continue
                source_hash = sha256_file(src)
                destination_hash = sha256_file(dst)
                if source_hash == destination_hash:
                    matched += 1
                    print(f"[KHỚP] {rel} — SHA-256: {source_hash}")
                else:
                    mismatched += 1
                    print(f"[LỆCH] {rel} — SHA-256 không giống nhau")
                    print(f"        nguồn: {source_hash}")
                    print(f"        đích:  {destination_hash}")
            except OSError as exc:
                errors += 1
                print(f"[LỖI ĐỌC] {rel} — {exc}")

        print("\n========== TỔNG KẾT ==========")
        print(f"File khớp:       {matched}")
        print(f"File lệch:       {mismatched}")
        print(f"Thiếu ở đích:    {len(only_source)}")
        print(f"Thừa ở đích:     {len(only_destination)}")
        print(f"Lỗi khi đọc:     {errors}")

        ok = mismatched == 0 and not only_source and not only_destination and errors == 0
        if ok:
            print("KẾT LUẬN: ĐẠT — hai thư mục có cùng tập file và nội dung.")
            return 0
        print("KẾT LUẬN: KHÔNG ĐẠT — hai thư mục khác nhau hoặc có lỗi đọc.")
        return 1
    except OSError as exc:
        print(f"LỖI I/O: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
