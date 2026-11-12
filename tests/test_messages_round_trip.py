"""Kiểm thử phần còn lại của messages.py — nhiệm vụ T13.

tests/test_messages.py (R6 viết ở T24) đã soi kỹ parse_offer. File này lo nốt:
sáu cặp tạo–đọc còn lại, và các ràng buộc chung mà mọi thông điệp phải theo.
"""
from __future__ import annotations

import json

import pytest

from truyennhanh.protocol.constants import PROTOCOL_VERSION, Reason
from truyennhanh.protocol.messages import (
    Offer,
    ProtocolError,
    decode_json,
    encode_json,
    make_accept,
    make_cancel,
    make_done,
    make_offer,
    make_reject,
    make_result,
    parse_accept,
    parse_cancel,
    parse_done,
    parse_offer,
    parse_reject,
    parse_result,
)

TID = "0b8c5c5e-2f7d-4c5a-9e61-3a2d7c1f9b40"
SID = "5d2e8f10-7c3b-4a9e-b1d4-6f0a2c8e9b13"
SHA = "9f2c4d1e8b7a6f5e3d2c1b0a9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e"
KHAC = "11111111-2222-4333-8444-555555555555"


# --------------------------------------------------------------------------- JSON nền

def test_json_viet_gon_khong_co_khoang_trang_thua():
    """Khoảng trắng thừa làm khung dài ra vô ích — docs/03 mục 2."""
    payload = encode_json({"a": 1, "b": "x"})

    assert payload == b'{"a":1,"b":"x"}'


def test_tieng_viet_giu_nguyen_khong_doi_thanh_ma_u():
    """ensure_ascii=False: gói ngắn hơn và đọc được bằng mắt khi bắt gói."""
    payload = encode_json({"name": "báo cáo.pdf"})

    assert "báo cáo.pdf".encode("utf-8") in payload
    assert b"\\u" not in payload


def test_decode_json_tu_choi_json_khong_phai_doi_tuong():
    for payload in (b"[1,2,3]", b'"chuoi"', b"42", b"null"):
        with pytest.raises(ProtocolError):
            decode_json(payload)


def test_decode_json_tu_choi_byte_khong_phai_utf8():
    with pytest.raises(ProtocolError):
        decode_json(b"\xff\xfe khong phai utf-8")


# --------------------------------------------------------------------------- OFFER

def test_offer_tao_roi_doc_lai_duoc_nguyen_ven():
    goc = Offer(TID, SID, "LAPTOP-LONG", "báo cáo quý 3.pdf", 1048576, SHA)

    assert parse_offer(make_offer(goc)) == goc


def test_make_offer_tu_them_truong_phien_ban():
    data = json.loads(make_offer(Offer(TID, SID, "A", "a.txt", 0, SHA)))

    assert data["v"] == PROTOCOL_VERSION


def test_offer_file_rong_van_hop_le():
    """File 0 byte phải gửi được; mã băm của nó là một giá trị cố định đã biết."""
    rong = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    assert parse_offer(make_offer(Offer(TID, SID, "A", "trong.txt", 0, rong))).size == 0


# --------------------------------------------------------------------------- ACCEPT

def test_accept_tao_roi_doc_lai():
    assert parse_accept(make_accept(TID, 0), TID, size=1000) == 0
    assert parse_accept(make_accept(TID, 512), TID, size=1000) == 512


def test_accept_offset_bang_size_la_hop_le():
    """Bên nhận đã có đủ byte từ lần trước; bên gửi gửi thẳng DONE — docs/03 mục 4.5."""
    assert parse_accept(make_accept(TID, 1000), TID, size=1000) == 1000


def test_accept_offset_vuot_size_bi_tu_choi():
    with pytest.raises(ProtocolError):
        parse_accept(make_accept(TID, 1001), TID, size=1000)


def test_accept_offset_am_bi_chan_ngay_luc_tao():
    with pytest.raises(ValueError):
        make_accept(TID, -1)


# --------------------------------------------------------------------------- REJECT

def test_reject_tao_roi_doc_lai_co_kem_loi_nhan():
    payload = make_reject(TID, Reason.USER_DECLINED, "Người nhận bấm Từ chối")

    assert parse_reject(payload, TID) == (Reason.USER_DECLINED, "Người nhận bấm Từ chối")


def test_reject_khong_co_loi_nhan_thi_bo_han_truong_do():
    """Đặc tả nói message không bắt buộc, nên bên đọc phải chịu được việc nó vắng."""
    payload = make_reject(TID, Reason.BUSY)

    assert "message" not in json.loads(payload)
    assert parse_reject(payload, TID) == (Reason.BUSY, None)


def test_reject_voi_ma_ly_do_khong_co_trong_bang():
    payload = encode_json({"transfer_id": TID, "reason": "ly_do_bia_ra"})

    with pytest.raises(ProtocolError):
        parse_reject(payload, TID)


# --------------------------------------------------------------------------- DONE

def test_done_tao_roi_doc_lai():
    assert parse_done(make_done(TID), TID) is None


# --------------------------------------------------------------------------- RESULT

def test_result_thanh_cong():
    assert parse_result(make_result(TID, ok=True), TID) == (True, None)


def test_result_that_bai_kem_ly_do():
    payload = make_result(TID, ok=False, reason=Reason.HASH_MISMATCH)

    assert parse_result(payload, TID) == (False, Reason.HASH_MISMATCH)


def test_result_thanh_cong_ma_kem_ly_do_la_loi_lap_trinh():
    with pytest.raises(ValueError):
        make_result(TID, ok=True, reason=Reason.TIMEOUT)


def test_result_that_bai_ma_thieu_ly_do_la_loi_lap_trinh():
    with pytest.raises(ValueError):
        make_result(TID, ok=False)


def test_result_nhan_duoc_that_bai_ma_thieu_ly_do_thi_tu_choi():
    """Bên kia gửi sai thì cũng phải bắt, vì bên gửi không có gì để hiện cho người dùng."""
    payload = encode_json({"transfer_id": TID, "ok": False, "reason": None})

    with pytest.raises(ProtocolError):
        parse_result(payload, TID)


def test_result_truong_ok_phai_la_true_hoac_false():
    payload = encode_json({"transfer_id": TID, "ok": 1, "reason": None})

    with pytest.raises(ProtocolError):
        parse_result(payload, TID)


# --------------------------------------------------------------------------- CANCEL

def test_cancel_tao_roi_doc_lai():
    assert parse_cancel(make_cancel(TID, Reason.CANCELLED), TID) is Reason.CANCELLED


# --------------------------------------------------------------------------- Luật chung

@pytest.mark.parametrize("ham, payload", [
    (lambda p: parse_accept(p, KHAC, 1000), make_accept(TID, 0)),
    (lambda p: parse_reject(p, KHAC), make_reject(TID, Reason.BUSY)),
    (lambda p: parse_done(p, KHAC), make_done(TID)),
    (lambda p: parse_result(p, KHAC), make_result(TID, ok=True)),
    (lambda p: parse_cancel(p, KHAC), make_cancel(TID, Reason.TIMEOUT)),
])
def test_moi_thong_diep_deu_phai_mang_dung_transfer_id(ham, payload):
    """docs/03 mục 4.3: sai transfer_id thì CANCEL bad_request."""
    with pytest.raises(ProtocolError):
        ham(payload)


@pytest.mark.parametrize("ham", [
    lambda p: parse_accept(p, TID, 1000),
    lambda p: parse_reject(p, TID),
    lambda p: parse_done(p, TID),
    lambda p: parse_result(p, TID),
    lambda p: parse_cancel(p, TID),
    parse_offer,
])
def test_khong_ham_doc_nao_chet_vi_json_hong(ham):
    """Mọi thứ đến từ mạng đều không đáng tin — docs/03 mục 4.9."""
    for rac in (b"", b"{", b"{khong phai json", b"[]", b"\xff\xff"):
        with pytest.raises(ProtocolError):
            ham(rac)
