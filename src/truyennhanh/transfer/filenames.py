"""Làm sạch tên file nhận được — docs/03 mục 4.9.

Phụ trách: R4 · Nhiệm vụ: T09 (danh sách ca), T22 (cài đặt) · Test: tests/test_filenames.py (R6, T24)

YÊU CẦU BẢO MẬT, KHÔNG ĐƯỢC CẮT. Tên file do máy gửi tự khai. Không làm sạch thì một máy
bất kỳ trong mạng có thể khai tên "../../Windows/x.dll" và ghi file ra bất cứ đâu.
"""
from __future__ import annotations
import unicodedata, re, os
from truyennhanh.protocol.constants import (FORBIDDEN_FILENAME_CHARS, 
                                            WINDOWS_RESERVED_NAMES, 
                                            FALLBACK_FILENAME,
                                            MAX_FILENAME_BYTES)


#Tạo bảng để thay FORBIDDEN_NAME_CHARS bằng "_"
_FORBIDDEN_TABLE = str.maketrans(FORBIDDEN_FILENAME_CHARS, "_" * len(FORBIDDEN_FILENAME_CHARS))
_MAX_EXT_BYTE = 20
_SURROGATES = re.compile("[\ud800-\udfff]")

def _cut_bytes(text: str, limit: int) -> str:
    """Cắt chuỗi còn tối đa `limit` byte UTF-8, không bao giờ cắt đôi một ký tự."""
    return text.encode("utf-8")[:limit].decode("utf-8", "ignore")

def sanitize_filename(name: str) -> str:
    """Biến một tên bất kỳ thành tên an toàn, theo ĐÚNG THỨ TỰ 8 bước ở docs/03 mục 4.9:

      1. unicodedata.normalize("NFC", name)
      2. Chỉ giữ phần sau dấu / hoặc \\ cuối cùng
      3. Bỏ ký tự điều khiển (mã 0–31 và 127)
      4. Thay FORBIDDEN_FILENAME_CHARS bằng "_"
      5. Bỏ dấu chấm và khoảng trắng ở đầu, cuối
      6. Tên (bỏ đuôi) thuộc WINDOWS_RESERVED_NAMES, không phân biệt hoa thường -> thêm "_" vào đầu
      7. Rỗng -> FALLBACK_FILENAME
      8. Quá MAX_FILENAME_BYTES byte UTF-8 -> cắt phần tên, giữ đuôi, không cắt đôi một ký tự

    Bước 9 (đường dẫn phải nằm trong thư mục nhận) làm ở storage.ensure_inside.

    Ví dụ:
        "../../Windows/system32/x.dll" -> "x.dll"
        "C:\\Users\\a\\bao_cao.pdf"     -> "bao_cao.pdf"
        "  .hidden. "                  -> "hidden"
        "a<b>c?.txt"                   -> "a_b_c_.txt"
        "NUL.txt"                      -> "_NUL.txt"
        ".."                           -> "file-nhan-duoc"
    """
    # raise NotImplementedError("T22 · R4")

    if not isinstance(name, str):
      # validate_offer đã phải chặn trước (REJECT bad_request); đây chỉ là lưới an toàn.
      raise TypeError("tên file phải là chuỗi")

    # Surrogate đơn lẻ (JSON "\ud800") không mã hóa được sang UTF-8 -> thay trước mọi bước khác.
    name = _SURROGATES.sub("_", name)
    
    #1. chuyển hóa string về dạng NFC
    name = unicodedata.normalize("NFC", name)

    #2. phân tách tên địa chỉ bẳng cách bỏ dấu / và \\ và lấy phần cuối cùng
    name = re.split(r"[/\\]", name)[-1]

    #3. Bỏ ký tự điều khiển
    name = "".join(c for c in name if ord(c) > 31 and ord(c) != 127)

    #4. Thay FORBIDDEN_FILENAME_CHARS bằng "_"
    name = name.translate(_FORBIDDEN_TABLE)

    #5. Bỏ khoảng trắng và dấu . ở đầu và cuối
    name = name.strip(". ")

    #6. Tên (bỏ đuôi) thuộc WINDOWS_RESERVED_NAMES, không phân biệt hoa thường -> thêm "_" vào đầu
    if name.partition(".")[0].upper() in WINDOWS_RESERVED_NAMES:
        name = "_" + name

    #7. Nếu tên file là rỗng "" thì thay nó bằng FALLBACK_FILENAME ("file-nhan-duoc")
    if not name:
        return FALLBACK_FILENAME

    #8. Quá MAX_FILENAME_BYTES byte UTF-8 -> cắt phần tên, giữ đuôi, không cắt đôi một ký tự
    if len(name.encode("utf-8")) > MAX_FILENAME_BYTES:
        root, dot, ext = name.rpartition(".")
        ext = dot + ext if dot else ""
        if not root or len(ext.encode("utf-8")) > _MAX_EXT_BYTE:
            root, ext = name, "" # không có đuôi đáng tin: cắt cả chuỗi
        root = _cut_bytes(root, MAX_FILENAME_BYTES - len(ext.encode("utf-8")))
        root = root.rstrip(". ") # sau khi cắt có thể lộ dấu chấm/khoảng trắng cuối
        name = (root + ext) if root else FALLBACK_FILENAME + ext

    return name
