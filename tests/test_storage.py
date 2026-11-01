import pytest

from src.truyennhanh.transfer.storage import ensure_inside


def test_ten_binh_thuong_nam_trong_thu_muc(tmp_path):
    out = ensure_inside(tmp_path, tmp_path / "a.txt")
    assert out == (tmp_path / "a.txt").resolve()


def test_thoat_bang_cham_cham_bi_chan(tmp_path):
    with pytest.raises(ValueError):
        ensure_inside(tmp_path, tmp_path / ".." / "x")


def test_chinh_thu_muc_nhan_bi_chan(tmp_path):
    with pytest.raises(ValueError):
        ensure_inside(tmp_path, tmp_path)


def test_thu_muc_anh_em_trung_tien_to_bi_chan(tmp_path):
    nhan = tmp_path / "nhan"
    evil = tmp_path / "nhan-evil"
    nhan.mkdir()
    evil.mkdir()
    with pytest.raises(ValueError):
        ensure_inside(nhan, nhan / ".." / "nhan-evil" / "x")


def test_symlink_tro_ra_ngoai_bi_chan(tmp_path):
    nhan = tmp_path / "nhan"
    ngoai = tmp_path / "ngoai"
    nhan.mkdir()
    ngoai.mkdir()
    try:
        (nhan / "x").symlink_to(ngoai, target_is_directory=True)
    except OSError:
        pytest.skip("không tạo được symlink (Windows cần Developer Mode hoặc quyền Administrator)")
    with pytest.raises(ValueError):
        ensure_inside(nhan, nhan / "x" / "file.txt")


def test_thu_muc_nhan_la_symlink_van_hoat_dong(tmp_path):
    that = tmp_path / "that"
    that.mkdir()
    link = tmp_path / "link"
    try:
        link.symlink_to(that, target_is_directory=True)
    except OSError:
        pytest.skip("không tạo được symlink")
    out = ensure_inside(link, link / "a.txt")
    assert out == (that / "a.txt").resolve()