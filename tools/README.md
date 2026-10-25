# Công cụ

Script hỗ trợ kiểm thử và đo đạc. Không nằm trong ứng dụng, không cần cài đặt.

| Script | Nhiệm vụ | Người viết | Dùng để |
|---|---|---|---|
| `tao_file_mau.py` | T12 | R6 | Tạo bộ file mẫu vào `du-lieu-thu/`: 0 B, 1 B, 1 MB, 100 MB, 1 GB, tên tiếng Việt có dấu, tên có khoảng trắng. Cùng seed ra cùng nội dung |
| `so_sanh_hash.py` | T12 | R6 | So SHA-256 hai thư mục, in file khớp, lệch, thiếu |
| `gui_rac.py` | T32 | R6 | Gửi dữ liệu xấu vào cổng TCP và UDP cho các ca bảo mật KT-29 → KT-32 |
| `thu_udp_thuan.py` | T36 | R3 | Thí nghiệm E5: gửi file bằng UDP thuần, đo gói mất và sai thứ tự |
| `ve_bieu_do.py` | T38 | R6 | Đọc CSV trong `ket-qua/`, vẽ biểu đồ vào `docs/hinh/`. Cần `pip install -e ".[do-dac]"` |

Thư mục `thu-nghiem/` chứa các script thử nghiệm nhanh ở tuần 1 (T06, T08) — viết nhanh để học, không cần đẹp, không phải qua duyệt kỹ.

`du-lieu-thu/` đã nằm trong `.gitignore`: **không bao giờ commit file thử nghiệm lớn**.
