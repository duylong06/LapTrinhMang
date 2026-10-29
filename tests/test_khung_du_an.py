"""Kiểm tra khung dự án và hợp đồng giao thức.

Các test này không kiểm tra phần cài đặt (chưa có), mà kiểm tra hai điều:
  1. Mọi module import được — ai lỡ làm hỏng cú pháp hay vòng import sẽ bị CI chặn.
  2. Hằng số trong protocol/constants.py khớp đặc tả docs/03 — hợp đồng không bị sửa lén.
"""
import importlib
import struct

import pytest

MODULES = [
    "truyennhanh",
    "truyennhanh.config",
    "truyennhanh.protocol.constants",
    "truyennhanh.protocol.framing",
    "truyennhanh.protocol.messages",
    "truyennhanh.core.models",
    "truyennhanh.core.events",
    "truyennhanh.core.service",
    "truyennhanh.discovery.messages",
    "truyennhanh.discovery.peer_table",
    "truyennhanh.discovery.discovery",
    "truyennhanh.transfer.hashing",
    "truyennhanh.transfer.sender",
    "truyennhanh.transfer.receiver",
    "truyennhanh.transfer.storage",
    "truyennhanh.transfer.filenames",
    "truyennhanh.cli.main",
    "truyennhanh.gui.fake_service",
]


@pytest.mark.parametrize("name", MODULES)
def test_module_imports(name):
    importlib.import_module(name)


def test_gui_module_imports():
    pytest.importorskip("tkinter")
    importlib.import_module("truyennhanh.gui.app")


def test_frame_header_matches_spec_example():
    """docs/03 mục 5: khung ACCEPT có nội dung 65 byte bắt đầu bằng 00 00 00 41 02."""
    from truyennhanh.protocol.constants import FRAME_HEADER_FORMAT, FRAME_HEADER_SIZE, FrameType

    assert struct.calcsize(FRAME_HEADER_FORMAT) == FRAME_HEADER_SIZE == 5
    assert struct.pack(FRAME_HEADER_FORMAT, 65, FrameType.ACCEPT) == bytes.fromhex("0000004102")
    assert struct.pack(FRAME_HEADER_FORMAT, 65536, FrameType.DATA) == bytes.fromhex("0001000004")


def test_frame_type_codes_match_spec():
    """docs/03 mục 4.2."""
    from truyennhanh.protocol.constants import FrameType

    assert {t.name: t.value for t in FrameType} == {
        "OFFER": 1, "ACCEPT": 2, "REJECT": 3, "DATA": 4, "DONE": 5, "RESULT": 6, "CANCEL": 7,
    }


def test_reason_codes_match_spec():
    """docs/03 mục 4.8."""
    from truyennhanh.protocol.constants import Reason

    assert {r.value for r in Reason} == {
        "user_declined", "timeout", "busy", "insufficient_space", "unsupported_version",
        "bad_request", "hash_mismatch", "incomplete", "cancelled", "shutting_down",
    }


def test_limits_and_timeouts_are_consistent():
    """docs/03 mục 4.1 và 4.7."""
    from truyennhanh.protocol import constants as c

    assert c.MAX_CONTROL_PAYLOAD == 64 * 1024
    assert c.MAX_DATA_PAYLOAD == 16 * 1024 * 1024
    assert 0 < c.DEFAULT_CHUNK_SIZE <= c.MAX_DATA_PAYLOAD
    assert c.ACCEPT_WAIT_TIMEOUT_S > c.DECISION_TIMEOUT_S
    assert c.PEER_TIMEOUT_S > 3 * c.ANNOUNCE_INTERVAL_S
    assert c.RETRY_DELAYS_S == (1, 2, 4, 8, 16)


def test_ports_match_spec():
    from truyennhanh.protocol.constants import DISCOVERY_PORT, TRANSFER_PORT_DEFAULT

    assert (DISCOVERY_PORT, TRANSFER_PORT_DEFAULT) == (50505, 50506)


def test_fake_service_matches_real_api():
    """FakeService (R5) phải có đúng cùng API với TruyenNhanhService (R1) — docs/02 mục 3.

    Đổi API lõi mà quên đổi FakeService thì giao diện làm trên đồ giả sẽ hỏng khi nối thật.
    """
    import inspect

    from truyennhanh.core.service import TruyenNhanhService
    from truyennhanh.gui.fake_service import FakeService

    def public_api(cls):
        api = {
            name: list(inspect.signature(fn).parameters)
            for name, fn in inspect.getmembers(cls, inspect.isfunction)
            if not name.startswith("_")
        }
        # property không phải function nên getmembers(isfunction) bỏ qua — phải so riêng,
        # nếu không thiếu một property vẫn lọt qua test.
        api.update({
            name: "property"
            for name, obj in vars(cls).items()
            if isinstance(obj, property) and not name.startswith("_")
        })
        return api

    assert public_api(FakeService) == public_api(TruyenNhanhService)
    assert "events" in TruyenNhanhService.__annotations__
    assert "events" in FakeService.__annotations__


def test_cli_without_command_prints_help(capsys):
    from truyennhanh.cli.main import main

    assert main([]) == 0
    assert "scan" in capsys.readouterr().out


def test_cli_unimplemented_command_reports_task(capsys):
    from truyennhanh.cli.main import main

    assert main(["scan"]) == 2
    assert "T17" in capsys.readouterr().out
