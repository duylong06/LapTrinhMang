
import json

import pytest

from truyennhanh.protocol.messages import (
    Offer,
    ProtocolError,
    UnsupportedVersion,
    parse_offer,
)

TRANSFER_ID = "0b8c5c5e-2f7d-4c5a-9e61-3a2d7c1f9b40"
SENDER_ID = "5d2e8f10-7c3b-4a9e-b1d4-6f0a2c8e9b13"
SHA256 = "a" * 64


def make_offer_data(**overrides):
    data = {
        "v": 1,
        "transfer_id": TRANSFER_ID,
        "sender_id": SENDER_ID,
        "sender_name": "LAPTOP-LONG",
        "name": "bao_cao.pdf",
        "size": 1024,
        "sha256": SHA256,
    }
    data.update(overrides)
    return json.dumps(data).encode("utf-8")


def test_parse_offer_valid():
    offer = parse_offer(make_offer_data())

    assert isinstance(offer, Offer)
    assert offer.transfer_id == TRANSFER_ID
    assert offer.sender_id == SENDER_ID
    assert offer.name == "bao_cao.pdf"
    assert offer.size == 1024
    assert offer.sha256 == SHA256


def test_parse_offer_ignores_unknown_fields():
    payload = make_offer_data(extra_field="unknown")

    offer = parse_offer(payload)

    assert offer.name == "bao_cao.pdf"


def test_parse_offer_missing_required_field():
    data = {
        "v": 1,
        "transfer_id": TRANSFER_ID,
        "sender_id": SENDER_ID,
        "sender_name": "LAPTOP-LONG",
        "name": "bao_cao.pdf",
        "size": 1024,
    }

    with pytest.raises(ProtocolError):
        parse_offer(json.dumps(data).encode("utf-8"))


def test_parse_offer_negative_size():
    with pytest.raises(ProtocolError):
        parse_offer(make_offer_data(size=-1))


def test_parse_offer_size_must_be_integer():
    with pytest.raises(ProtocolError):
        parse_offer(make_offer_data(size="1024"))


def test_parse_offer_sha256_must_have_64_characters():
    with pytest.raises(ProtocolError):
        parse_offer(make_offer_data(sha256="a" * 63))


def test_parse_offer_sha256_must_be_lowercase():
    with pytest.raises(ProtocolError):
        parse_offer(make_offer_data(sha256="A" * 64))


def test_parse_offer_invalid_json():
    with pytest.raises(ProtocolError):
        parse_offer(b"{invalid json")


def test_parse_offer_unsupported_version():
    with pytest.raises(UnsupportedVersion):
        parse_offer(make_offer_data(v=2))
