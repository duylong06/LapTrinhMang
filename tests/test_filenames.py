"""Kiểm thử sanitize_filename (T22) theo 8 bước ở docs/03 mục 4.9 và danh sách ca nguy hiểm T09.

Bước 9 (đường dẫn nằm trong thư mục nhận) được kiểm thử ở tests/test_storage.py.
"""
import os
import unicodedata

import pytest

from src.truyennhanh.protocol.constants import FALLBACK_FILENAME, MAX_FILENAME_BYTES
from src.truyennhanh.transfer.filenames import sanitize_filename


def _byte_length(text: str) -> int:
    return len(text.encode("utf-8"))


# Bước 1: NFC
def test_sanitize_normalizes_nfd_to_nfc():
    """Dấu tiếng Việt viết rời (NFD) phải ra cùng một chuỗi với dạng dựng sẵn (NFC)."""
    nfc = unicodedata.normalize("NFC", "báo cáo.pdf")
    nfd = unicodedata.normalize("NFD", "báo cáo.pdf")
    assert nfc != nfd
    assert sanitize_filename(nfd) == nfc


# Bước 2: bỏ đường dẫn
@pytest.mark.parametrize(
    "raw, expected",
    [
        ("../../x", "x"),
        ("..\\..\\x", "x"),
        ("C:\\Windows\\x", "x"),
        ("/etc/passwd", "passwd"),
        ("../../Windows/system32/x.dll", "x.dll"),
        ("C:\\Users\\a\\bao_cao.pdf", "bao_cao.pdf"),
        (".ssh/authorized_keys", "authorized_keys"),
    ],
)
def test_sanitize_keeps_only_last_path_component(raw, expected):
    """Chỉ giữ phần sau dấu / hoặc \\ cuối cùng, dù máy gửi dùng kiểu đường dẫn nào."""
    assert sanitize_filename(raw) == expected


# Bước 3: ký tự điều khiển
@pytest.mark.parametrize(
    "raw",
    ["a\x00b.txt", "a\nb.txt", "a\rb.txt", "a\x1bb.txt", "a\x7fb.txt"],
    ids=["null", "newline", "carriage-return", "escape", "delete"],
)
def test_sanitize_drops_control_characters(raw):
    assert sanitize_filename(raw) == "ab.txt"


def test_sanitize_keeps_space_between_words():
    """Dấu cách (mã 32) không phải ký tự điều khiển, phải được giữ."""
    assert sanitize_filename("báo cáo.pdf") == "báo cáo.pdf"


# Bước 4: ký tự cấm
@pytest.mark.parametrize(
    "raw, expected",
    [
        ("a<b>c?.txt", "a_b_c_.txt"),
        ('a:b"c|d*e.txt', "a_b_c_d_e.txt"),
        ("file.txt:evil.exe", "file.txt_evil.exe"),
        ("file.txt::$DATA", "file.txt__$DATA"),
        ("C:file.txt", "C_file.txt"),
    ],
    ids=["angle-and-question", "colon-quote-pipe-star", "ntfs-stream", "ntfs-data-stream", "drive-letter"],
)
def test_sanitize_replaces_forbidden_characters_with_underscore(raw, expected):
    assert sanitize_filename(raw) == expected


# Bước 5: chấm và cách hai đầu
@pytest.mark.parametrize(
    "raw, expected",
    [
        ("  .hidden. ", "hidden"),
        (".bashrc", "bashrc"),
        ("báo cáo.pdf  ", "báo cáo.pdf"),
        ("a. . ", "a"),
        ("  báo cáo.pdf  ", "báo cáo.pdf"),
    ],
)
def test_sanitize_strips_dots_and_spaces_at_both_ends(raw, expected):
    assert sanitize_filename(raw) == expected


def test_sanitize_keeps_inner_dots():
    assert sanitize_filename("file.tar.gz") == "file.tar.gz"


def test_sanitize_does_not_use_internal_folder_name():
    """Tên trùng thư mục nội bộ .truyennhanh mất dấu chấm đầu nên không còn trùng."""
    assert sanitize_filename(".truyennhanh") == "truyennhanh"


# Bước 6: tên thiết bị Windows
@pytest.mark.parametrize(
    "raw, expected",
    [
        ("CON", "_CON"),
        ("nul.txt", "_nul.txt"),
        ("NUL.txt", "_NUL.txt"),
        ("COM1.log", "_COM1.log"),
        ("LPT9", "_LPT9"),
        ("AUX.", "_AUX"),
        ("CON.tar.gz", "_CON.tar.gz"),
    ],
)
def test_sanitize_prefixes_windows_reserved_device_names(raw, expected):
    """Windows tính theo phần trước dấu chấm đầu tiên, nên CON.tar.gz vẫn là thiết bị CON."""
    assert sanitize_filename(raw) == expected


def test_sanitize_keeps_names_that_only_look_reserved():
    assert sanitize_filename("CONSOLE.txt") == "CONSOLE.txt"


# Bước 7: tên rỗng
@pytest.mark.parametrize(
    "raw",
    ["", ".", "..", "...   ", "   ", "\x00\x01", "/", "C:\\Windows\\System32\\"],
    ids=["empty", "dot", "dotdot", "dots-and-spaces", "spaces", "control-only", "slash", "trailing-backslash"],
)
def test_sanitize_returns_fallback_when_nothing_is_left(raw):
    assert sanitize_filename(raw) == FALLBACK_FILENAME


def test_sanitize_drops_leading_dot_of_extension_only_name():
    """".mp4" mất dấu chấm đầu (bước 5) nên thành "mp4", không phải tên mặc định (đúng đặc tả)."""
    assert sanitize_filename(".mp4") == "mp4"


# Bước 8: tên quá dài
def test_sanitize_cuts_long_ascii_name_to_limit():
    assert sanitize_filename("A" * 300) == "A" * MAX_FILENAME_BYTES


def test_sanitize_keeps_extension_when_cutting():
    assert sanitize_filename("A" * 296 + ".pdf") == "A" * 196 + ".pdf"


def test_sanitize_does_not_cut_multibyte_character_in_half():
    out = sanitize_filename("á" * 300)
    assert out == "á" * 100
    assert _byte_length(out) == MAX_FILENAME_BYTES


def test_sanitize_drops_character_that_does_not_fit_at_cut_point():
    """199 byte "a" + "á" (2 byte) = 201 byte: chữ á không còn chỗ nên bị bỏ cả ký tự."""
    assert sanitize_filename("a" * 199 + "á") == "a" * 199


def test_sanitize_leaves_name_of_exactly_limit_unchanged():
    name = "A" * MAX_FILENAME_BYTES
    assert sanitize_filename(name) == name


def test_sanitize_leaves_no_trailing_space_before_extension_after_cut():
    """Cắt đúng chỗ có dấu cách thì phần tên không được kết thúc bằng dấu cách."""
    out = sanitize_filename("a" * 195 + " " + "b" * 10 + ".txt")
    stem, ext = os.path.splitext(out)
    assert ext == ".txt"
    assert stem == stem.rstrip(". ")


def test_sanitize_handles_extension_longer_than_limit():
    out = sanitize_filename("a." + "x" * 300)
    assert 0 < _byte_length(out) <= MAX_FILENAME_BYTES


def test_sanitize_does_not_start_with_dot_after_cut():
    out = sanitize_filename("a." + "x" * 199)
    assert not out.startswith(".")
    assert _byte_length(out) <= MAX_FILENAME_BYTES


def test_sanitize_handles_huge_name():
    """Tên 60.000 ký tự (vừa lọt khung 64 KiB) vẫn ra kết quả hợp lệ."""
    out = sanitize_filename("x" * 60_000)
    assert _byte_length(out) <= MAX_FILENAME_BYTES


# Tính chất mọi kết quả phải có
HOSTILE_NAMES = [
    "../../x", "..\\..\\x", "C:\\Windows\\x", "/etc/passwd", "C:\\Windows\\System32\\", "/",
    "CON", "nul.txt", "COM1.log", "LPT9", "AUX.", "CON.tar.gz",
    "", ".", "..", "...   ", "   ",
    "A" * 300, "A" * 296 + ".pdf", "á" * 300, "a." + "x" * 300, "x" * 60_000,
    "a<b>c?.txt", 'a:b"c|d*e.txt', "file.txt:evil.exe", "file.txt::$DATA", "C:file.txt",
    "a\x00b.txt", "a\nb.txt", "a\x1bb.txt", "a\x7fb.txt",
    ".hidden.", ".bashrc", ".ssh/authorized_keys", "  báo cáo.pdf  ", ".truyennhanh",
]


@pytest.mark.parametrize(
    "raw",
    HOSTILE_NAMES,
    ids=[f"case-{i}" for i in range(len(HOSTILE_NAMES))]
)
def test_sanitize_never_returns_empty_name(raw):
    assert sanitize_filename(raw)


@pytest.mark.parametrize("raw", HOSTILE_NAMES, ids=[f"case-{i}" for i in range(len(HOSTILE_NAMES))])
def test_sanitize_result_has_no_forbidden_characters(raw):
    assert not any(c in sanitize_filename(raw) for c in '<>:"/\\|?*')


@pytest.mark.parametrize("raw", HOSTILE_NAMES, ids=[f"case-{i}" for i in range(len(HOSTILE_NAMES))])
def test_sanitize_result_has_no_control_characters(raw):
    assert not any(ord(c) < 32 or ord(c) == 127 for c in sanitize_filename(raw))


@pytest.mark.parametrize("raw", HOSTILE_NAMES, ids=[f"case-{i}" for i in range(len(HOSTILE_NAMES))])
def test_sanitize_result_does_not_start_or_end_with_dot_or_space(raw):
    out = sanitize_filename(raw)
    assert out == out.strip(". ")


@pytest.mark.parametrize("raw", HOSTILE_NAMES, ids=[f"case-{i}" for i in range(len(HOSTILE_NAMES))])
def test_sanitize_result_fits_in_byte_limit(raw):
    assert _byte_length(sanitize_filename(raw)) <= MAX_FILENAME_BYTES


@pytest.mark.parametrize("raw", HOSTILE_NAMES, ids=[f"case-{i}" for i in range(len(HOSTILE_NAMES))])
def test_sanitize_is_idempotent(raw):
    """Tên đã sạch đưa qua hàm lần nữa phải không đổi."""
    once = sanitize_filename(raw)
    assert sanitize_filename(once) == once


# Đầu vào không phải tên thường
@pytest.mark.parametrize("bad", [None, 123, ["a"], b"a"], ids=["none", "int", "list", "bytes"])
def test_sanitize_rejects_non_string_input(bad):
    """validate_offer phải chặn trước; đây là lưới an toàn nếu nó sót."""
    with pytest.raises(TypeError):
        sanitize_filename(bad)

def test_sanitize_survives_lone_surrogate():
    """Tên JSON "\\ud800.txt" không được làm hàm crash; kết quả hợp lệ và không chứa surrogate."""
    out = sanitize_filename("\ud800" * 300 + ".txt")
    out.encode("utf-8")  # phải mã hóa được
    assert out