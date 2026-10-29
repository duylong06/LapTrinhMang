#!/usr/bin/env python3
"""Tạo bộ file mẫu kiểm thử với nội dung tái lập được theo seed.

Mặc định, file được tạo trong <thu_muc_du_an>/du-lieu-thu/.
Dung lượng dùng quy ước nhị phân: 1 MB = 1024**2 byte, 1 GB = 1024**3 byte.
Yêu cầu Python 3.9+.
"""
from __future__ import annotations

import argparse
import hashlib
import random
import sys
from pathlib import Path

CHUNK_SIZE = 1024 * 1024  # Ghi từng khối 1 MiB để không nạp file lớn vào RAM.
DEFAULT_OUT_DIR = Path(__file__).resolve().parents[1] / "du-lieu-thu"

# 0 B, 1 B, 1 MB, 100 MB, 1 GB.
STANDARD_FILES: tuple[tuple[str, int], ...] = (
    ("du_lieu_0B.bin", 0),
    ("du_lieu_1B.bin", 1),
    ("du_lieu_1MB.bin", 1 * 1024**2),
    ("du_lieu_100MB.bin", 100 * 1024**2),
    ("du_lieu_1GB.bin", 1 * 1024**3),
)
# Hai file tên đặc biệt dùng để kiểm tra đường dẫn/tên file Unicode và khoảng trắng.
SPECIAL_FILES: tuple[tuple[str, int], ...] = (
    ("báo cáo tiếng Việt.txt", 32 * 1024),
    ("file có khoảng trắng.txt", 32 * 1024),
)


def make_rng(seed: int, filename: str) -> random.Random:
    """Tạo bộ sinh riêng cho mỗi file, với seed ổn định không phụ thuộc hash() của Python."""
    seed_material = f"{seed}:{filename}".encode("utf-8")
    stable_seed = int.from_bytes(hashlib.sha256(seed_material).digest()[:8], "big")
    return random.Random(stable_seed)


def write_deterministic_file(path: Path, size_bytes: int, seed: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rng = make_rng(seed, path.name)
    remaining = size_bytes
    with path.open("wb") as f:
        while remaining:
            amount = min(CHUNK_SIZE, remaining)
            f.write(rng.randbytes(amount))
            remaining -= amount


def format_size(n: int) -> str:
    if n == 0:
        return "0 B"
    if n < 1024:
        return f"{n} B"
    if n % 1024**3 == 0:
        return f"{n // 1024**3} GB"
    if n % 1024**2 == 0:
        return f"{n // 1024**2} MB"
    return f"{n} B"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Tạo file mẫu kiểm thử với nội dung tái lập theo seed."
    )
    parser.add_argument(
        "--seed", type=int, default=2026,
        help="Seed số nguyên; cùng seed + cùng tên file sẽ tạo cùng nội dung (mặc định: 2026).",
    )
    parser.add_argument(
        "--output", type=Path, default=DEFAULT_OUT_DIR,
        help=f"Thư mục đầu ra (mặc định: {DEFAULT_OUT_DIR}).",
    )
    parser.add_argument(
        "--skip-large-files", action="store_true",
        help="Bỏ qua file 100 MB và 1 GB để kiểm tra nhanh; không dùng cho bộ dữ liệu bàn giao đầy đủ.",
    )
    args = parser.parse_args()

    output_dir = args.output.expanduser().resolve()
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        files = list(STANDARD_FILES) + list(SPECIAL_FILES)
        if args.skip_large_files:
            files = [item for item in files if item[1] < 100 * 1024**2]
            print("CHẾ ĐỘ THỬ NHANH: đang bỏ qua file 100 MB và 1 GB.")

        total = sum(size for _, size in files)
        print(f"Thư mục đầu ra: {output_dir}")
        print(f"Seed: {args.seed}")
        print(f"Tổng dung lượng dự kiến: {total:,} byte")
        for filename, size in files:
            target = output_dir / filename
            write_deterministic_file(target, size, args.seed)
            print(f"[OK] {filename} — {format_size(size)}")
        print(f"Hoàn tất: đã tạo/ghi đè {len(files)} file trong {output_dir}")
        return 0
    except OSError as exc:
        print(f"LỖI I/O: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
