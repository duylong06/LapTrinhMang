"""Làm sạch tên file nhận được — docs/03 mục 4.9.

Phụ trách: R4 · Nhiệm vụ: T09 (danh sách ca), T22 (cài đặt) · Test: tests/test_filenames.py (R6, T24)

YÊU CẦU BẢO MẬT, KHÔNG ĐƯỢC CẮT. Tên file do máy gửi tự khai. Không làm sạch thì một máy
bất kỳ trong mạng có thể khai tên "../../Windows/x.dll" và ghi file ra bất cứ đâu.
"""
from __future__ import annotations


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
    raise NotImplementedError("T22 · R4")
