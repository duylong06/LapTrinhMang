"""Kiểm thử truyền tiếp, dung lượng, khóa và dọn .part — T27, T28, T37.

Phần T21 (part_dir, part_path, unique_path, finalize, ensure_inside) đã có bài
riêng ở tests/test_storage.py; file này chỉ kiểm những hàm thêm ở tuần 3 và 4.

Không chờ thật: chỗ nào cần "file cũ bảy ngày" thì đặt lại thời gian sửa file
bằng os.utime, nên cả file chạy xong trong chớp mắt.
"""
from __future__ import annotations

import os
import threading
import time

import pytest

from truyennhanh.transfer.storage import (
    FREE_SPACE_MARGIN_BYTES,
    FileLocks,
    cleanup_old_parts,
    has_free_space,
    part_path,
    resume_offset,
)

SHA = "a" * 64
SHA_KHAC = "b" * 64


@pytest.fixture
def thu_muc(tmp_path):
    d = tmp_path / "nhan"
    d.mkdir()
    return d


def _tao_part(thu_muc, so_byte: int, sha: str = SHA):
    p = part_path(thu_muc, sha)
    p.write_bytes(b"x" * so_byte)
    return p


def _lam_cho_cu(duong_dan, so_ngay: float) -> None:
    """Đặt lại thời gian sửa file, thay cho việc chờ thật nhiều ngày."""
    moc = time.time() - so_ngay * 86400
    os.utime(duong_dan, (moc, moc))


# --------------------------------------------------------------------- T27: bảng ở mục 4.5

def test_khong_co_part_thi_bat_dau_tu_0(thu_muc):
    assert resume_offset(thu_muc, SHA, 1000) == 0


def test_part_ngan_hon_thi_tiep_tu_cho_do(thu_muc):
    _tao_part(thu_muc, 400)
    assert resume_offset(thu_muc, SHA, 1000) == 400


def test_part_dung_bang_size_thi_tra_ve_size(thu_muc):
    """Bên gửi sẽ gửi DONE ngay, bên nhận kiểm mã băm như bình thường."""
    _tao_part(thu_muc, 1000)
    assert resume_offset(thu_muc, SHA, 1000) == 1000


def test_part_dai_hon_size_thi_coi_la_hong_va_xoa(thu_muc):
    p = _tao_part(thu_muc, 1500)
    assert resume_offset(thu_muc, SHA, 1000) == 0
    assert not p.exists(), ".part hỏng phải bị xóa để nhận lại từ đầu"


def test_part_rong_tra_ve_0(thu_muc):
    _tao_part(thu_muc, 0)
    assert resume_offset(thu_muc, SHA, 1000) == 0


def test_moi_ma_bam_co_part_rieng(thu_muc):
    _tao_part(thu_muc, 300, SHA)
    _tao_part(thu_muc, 700, SHA_KHAC)
    assert resume_offset(thu_muc, SHA, 1000) == 300
    assert resume_offset(thu_muc, SHA_KHAC, 1000) == 700


@pytest.mark.parametrize("sha_xau", ["../../etc/passwd", SHA.upper(), SHA[:63], "g" * 64, ""])
def test_sha256_doc_hai_bi_chan(thu_muc, sha_xau):
    """sha256 do máy lạ khai và dùng làm tên file: không được để lọt ký tự đường dẫn."""
    with pytest.raises(ValueError):
        resume_offset(thu_muc, sha_xau, 1000)


# --------------------------------------------------------------------- T28: dung lượng

def test_con_cho_cho_file_nho(thu_muc):
    assert has_free_space(thu_muc, 1024) is True


def test_het_cho_cho_file_khong_tuong(thu_muc):
    assert has_free_space(thu_muc, 10**18) is False


def test_co_chua_khoang_an_toan(thu_muc, monkeypatch):
    """Vừa khít chỗ trống vẫn phải từ chối: ổ đĩa đầy sát nút làm cả máy hỏng việc."""
    class _GiaLapODia:
        free = 100 * 1024 * 1024

    monkeypatch.setattr("truyennhanh.transfer.storage.shutil.disk_usage",
                        lambda _p: _GiaLapODia())
    vua_khit = _GiaLapODia.free - FREE_SPACE_MARGIN_BYTES
    assert has_free_space(thu_muc, vua_khit) is True
    assert has_free_space(thu_muc, vua_khit + 1) is False


def test_khong_hoi_duoc_dung_luong_thi_cho_di_tiep(thu_muc, monkeypatch):
    def _no(_p):
        raise OSError("ổ đĩa không trả lời")

    monkeypatch.setattr("truyennhanh.transfer.storage.shutil.disk_usage", _no)
    assert has_free_space(thu_muc, 1024) is True


# --------------------------------------------------------------------- T28: FileLocks

def test_khoa_lan_dau_thanh_cong():
    assert FileLocks().acquire(SHA) is True


def test_khoa_lan_hai_bi_tu_choi_va_tra_ve_ngay():
    khoa = FileLocks()
    khoa.acquire(SHA)
    bat_dau = time.monotonic()
    assert khoa.acquire(SHA) is False
    # Phải trả về NGAY, không chờ: bên nhận cần gửi REJECT busy lập tức.
    assert time.monotonic() - bat_dau < 0.1


def test_hai_ma_bam_khac_nhau_khong_vuong_nhau():
    khoa = FileLocks()
    assert khoa.acquire(SHA) is True
    assert khoa.acquire(SHA_KHAC) is True


def test_nha_roi_lay_lai_duoc():
    khoa = FileLocks()
    khoa.acquire(SHA)
    khoa.release(SHA)
    assert khoa.acquire(SHA) is True


def test_nha_khoa_chua_giu_khong_nem_loi():
    """Khối finally của bên nhận gọi release() trên mọi đường thoát."""
    FileLocks().release(SHA)
    FileLocks().release(SHA)


def test_chi_mot_luong_gianh_duoc_khoa():
    khoa = FileLocks()
    so_luong = 20
    vach = threading.Barrier(so_luong)
    thang = []

    def thu():
        vach.wait()
        if khoa.acquire(SHA):
            thang.append(threading.current_thread().name)

    luong = [threading.Thread(target=thu) for _ in range(so_luong)]
    for t in luong:
        t.start()
    for t in luong:
        t.join(timeout=5)

    assert len(thang) == 1, "đúng một luồng được giữ khóa, số còn lại phải trượt"


# --------------------------------------------------------------------- T37: dọn .part cũ

def test_xoa_part_qua_han(thu_muc):
    p = _tao_part(thu_muc, 10)
    _lam_cho_cu(p, 10)
    assert cleanup_old_parts(thu_muc, max_age_days=7) == 1
    assert not p.exists()


def test_giu_part_con_moi(thu_muc):
    p = _tao_part(thu_muc, 10)
    assert cleanup_old_parts(thu_muc, max_age_days=7) == 0
    assert p.exists()


def test_dung_moc_mac_dinh_bay_ngay(thu_muc):
    cu = _tao_part(thu_muc, 10, SHA)
    moi = _tao_part(thu_muc, 10, SHA_KHAC)
    _lam_cho_cu(cu, 8)
    _lam_cho_cu(moi, 6)
    assert cleanup_old_parts(thu_muc) == 1
    assert not cu.exists()
    assert moi.exists()


def test_khong_co_thu_muc_part_thi_tra_ve_0(thu_muc):
    assert cleanup_old_parts(thu_muc) == 0


def test_khong_tu_tao_thu_muc_part(thu_muc):
    """Dọn dẹp mà lại sinh ra thư mục mới thì vô lý."""
    cleanup_old_parts(thu_muc)
    assert list(thu_muc.iterdir()) == []


def test_khong_dung_den_file_that_trong_thu_muc_nhan(thu_muc):
    that = thu_muc / "quan trong.pdf"
    that.write_text("đừng xóa tôi", encoding="utf-8")
    _lam_cho_cu(that, 99)
    cleanup_old_parts(thu_muc, max_age_days=1)
    assert that.exists()


def test_khong_dung_den_file_khac_duoi_trong_thu_muc_part(thu_muc):
    khac = part_path(thu_muc, SHA).parent / "ghi-chu.txt"
    khac.write_text("x")
    _lam_cho_cu(khac, 99)
    cleanup_old_parts(thu_muc, max_age_days=1)
    assert khac.exists()
