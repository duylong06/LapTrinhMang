# Kế hoạch kiểm thử

Người giữ: **R6**. Hoàn thiện ở nhiệm vụ T11 (tuần 1), cập nhật suốt dự án.

## 1. Các mức kiểm thử

| Mức | Kiểm tra gì | Chạy ở đâu | Khi nào |
|---|---|---|---|
| **Đơn vị** | Từng hàm riêng lẻ, không mở mạng thật: đóng khung, thông điệp, tên file, bảng thiết bị | `pytest`, CI | Mỗi PR |
| **Tích hợp** | Bên gửi và bên nhận thật nói chuyện qua `127.0.0.1` | `pytest`, CI | Mỗi PR, từ tuần 3 |
| **Hệ thống** | Ứng dụng hoàn chỉnh giữa hai máy thật | Thủ công | Cuối mỗi tuần, từ tuần 2 |
| **Phá hoại** | Rút mạng, tắt tiến trình giữa chừng | Thủ công, có kịch bản | Tuần 3–4 |
| **Bảo mật** | Dữ liệu xấu có chủ đích | Tự động và thủ công | Tuần 2–4 |
| **Khả dụng** | Người ngoài nhóm dùng được không | Thủ công | Tuần 4 |

## 2. Quy ước viết test

- File: `tests/test_<module>.py`, ví dụ `tests/test_framing.py`.
- Tên hàm test bằng tiếng Anh, mô tả **hành vi**: `test_recv_exact_joins_partial_reads`, không phải `test_1`.
- Mỗi test kiểm tra **một** ý. Docstring tiếng Việt nói ý đó là gì nếu tên chưa đủ rõ.
- Test đơn vị **không** mở socket thật và **không** `sleep` thật: dùng socket giả (đối tượng có hàm `recv` trả về dữ liệu định sẵn) và đồng hồ giả.
- Test tích hợp dùng cổng `0` để hệ điều hành chọn cổng trống, không đụng ứng dụng thật đang chạy trên 50506.
- Test chạy quá 10 giây thì đánh dấu `@pytest.mark.cham`.
- Test viết trước khi code xong (kiểu TDD, nhiệm vụ T24) thì đánh dấu `@pytest.mark.xfail(reason="chờ T13")` cho tới khi code xong, rồi bỏ dấu.

```bash
pytest                    # chạy hết
pytest tests/test_framing.py -v
pytest -m "not cham"      # bỏ qua test chậm
```

## 3. Danh sách ca kiểm thử

Mỗi ca có mã `KT-xx`, ánh xạ tới yêu cầu trong [docs/01](01-de-cuong.md).

### Đơn vị

| Mã | Ca kiểm thử | Kết quả mong đợi | Yêu cầu |
|---|---|---|---|
| KT-01 | `recv_exact` với socket giả trả về từng 1 byte | Ghép đủ n byte | FR-03 |
| KT-02 | `recv_exact` khi đối phương đóng giữa chừng | Ném `ConnectionClosed` | FR-07 |
| KT-03 | `encode_frame` với ACCEPT ở docs/03 mục 5 | Khớp từng byte ví dụ hex | FR-03 |
| KT-04 | `read_frame` gặp khung khai độ dài vượt giới hạn | Ném `FrameError` **mà không đọc** phần nội dung | NFR-05 |
| KT-05 | `validate_offer` với: thiếu trường, `size` âm, `size` là chuỗi, `sha256` 63 ký tự, `sha256` chữ hoa, JSON hỏng | Ném `ProtocolError` cho mọi ca | NFR-05 |
| KT-06 | `sanitize_filename` với mọi tên trong danh sách T09 | Tên an toàn, đúng ví dụ ở docs/03 mục 4.9 | NFR-05 |
| KT-07 | `sanitize_filename("báo cáo.pdf")` dạng dựng sẵn và dạng dấu rời | Cả hai ra cùng một chuỗi NFC | NFR-05 |
| KT-08 | `PeerTable` với đồng hồ giả: im lặng 6,9 giây và 7,1 giây | Còn ở 6,9; bị xóa ở 7,1 | NFR-01 |
| KT-09 | Gói dò tìm rác: không phải JSON, quá 1024 byte, sai `proto`, `id` của chính mình | Bị bỏ qua, không ném lỗi | FR-01 |
| KT-10 | `unique_path` khi `a.txt` và `a (1).txt` đã tồn tại | Trả về `a (2).txt` | FR-06 |
| KT-11 | `sha256_file` với file 0 byte và file 1 MB | Khớp `hashlib` tính trực tiếp | FR-06 |

### Tích hợp (qua 127.0.0.1)

| Mã | Ca kiểm thử | Kết quả mong đợi | Yêu cầu |
|---|---|---|---|
| KT-12 | Gửi bộ file mẫu (trừ file 1 GB) | Mọi file có SHA-256 khớp | FR-03, NFR-02 |
| KT-13 | Gửi file 0 byte | Nhận được file 0 byte, mã băm `e3b0c442...` | FR-03 |
| KT-14 | Bên nhận từ chối | Bên gửi nhận REJECT `user_declined`; không byte nào được ghi | FR-04 |
| KT-15 | Bên nhận không trả lời | REJECT `timeout` sau 60 giây (rút ngắn được khi test) | FR-04 |
| KT-16 | Bên gửi khai `sha256` sai | RESULT `hash_mismatch`; thư mục nhận không có file; `.part` bị xóa | FR-06 |
| KT-17 | Đóng kết nối ở giữa, gửi lại | ACCEPT `offset` bằng số byte đã nhận; file cuối cùng khớp | FR-07, NFR-03 |
| KT-18 | Hai lượt cùng `sha256` cùng lúc | Lượt sau nhận REJECT `busy` | FR-09 |
| KT-19 | Hủy từ bên gửi, rồi hủy từ bên nhận | Cả hai bên kết thúc với lý do `cancelled`; `.part` được giữ | FR-08 |

### Hệ thống (hai máy thật)

| Mã | Ca kiểm thử | Kết quả mong đợi | Yêu cầu |
|---|---|---|---|
| KT-20 | Bật ứng dụng trên hai máy | Thấy nhau trong 3 giây | FR-01, NFR-01 |
| KT-21 | Tắt bình thường; rút WiFi đột ngột | Biến mất ngay; biến mất trong 7 giây | NFR-01 |
| KT-22 | Chặn UDP 50505 bằng tường lửa, thêm máy theo IP | Vẫn gửi được file | FR-02 |
| KT-23 | Gửi file 1 GB qua WiFi, trong lúc đó kéo cửa sổ và bấm các nút | Cửa sổ không đơ | FR-05, NFR-04 |
| KT-24 | Rút WiFi ở 25%, 50%, 75% rồi cắm lại | Tự truyền tiếp, file khớp | FR-07, NFR-03 |
| KT-25 | Một máy nhận từ hai máy cùng lúc | Cả hai file khớp | FR-09 |
| KT-26 | Gửi file lớn hơn 4 GB | File khớp | FR-03 |
| KT-27 | Chạy trên Windows 10, Windows 11 và ít nhất một máy macOS hoặc Linux | Gửi nhận chéo được giữa các hệ điều hành | NFR-07 |

### Bảo mật

| Mã | Ca kiểm thử | Kết quả mong đợi | Yêu cầu |
|---|---|---|---|
| KT-28 | `truyennhanh send <ip> a.txt --as-name ../../hack.txt` | Lưu thành `hack.txt` bên trong thư mục nhận | NFR-05 |
| KT-29 | Kết nối và gửi 5 byte `ff ff ff ff 01` | Bên nhận đóng kết nối ngay, bộ nhớ không tăng vọt | NFR-05 |
| KT-30 | Kết nối rồi im lặng | Bị đóng sau 15 giây; lượt khác vẫn chạy bình thường | NFR-05 |
| KT-31 | Gửi 1 MB byte ngẫu nhiên vào cổng TCP 50506 và cổng UDP 50505 | Không sập; ứng dụng vẫn hoạt động | NFR-05 |
| KT-32 | Gửi khung DATA trước OFFER | Đóng kết nối, không ghi gì xuống đĩa | NFR-05 |

Công cụ cho KT-29 đến KT-32: R6 viết `tools/gui_rac.py`. Ca KT-29 làm tay được ngay bằng một dòng:

```bash
python -c "import socket; s = socket.create_connection(('127.0.0.1', 50506)); s.sendall(bytes.fromhex('ffffffff01')); print(s.recv(10))"
```

### Khả dụng

| Mã | Ca kiểm thử | Kết quả mong đợi | Yêu cầu |
|---|---|---|---|
| KT-33 | Một người ngoài nhóm gửi file lần đầu, không ai hướng dẫn | Làm được trong 2 phút | FR-10 |
| KT-34 | Gây ra mọi lỗi đã biết (tường lửa chặn, máy nhận tắt, ổ đầy, từ chối) | Mọi thông báo là câu tiếng Việt dễ hiểu, không có traceback | FR-05 |

## 4. Các ca nguy hiểm phía bên nhận

R4 lập danh sách đầy đủ ở nhiệm vụ T09 và bổ sung vào đây. Khởi điểm:

| Tình huống | Xử lý mong đợi |
|---|---|
| Tên file `../../x`, `C:\Windows\x`, `/etc/passwd` | Chỉ giữ tên cuối: `x`, `x`, `passwd` |
| Tên `CON`, `nul.txt`, `COM1.log` | Thêm `_` vào đầu |
| Tên rỗng, `..`, chỉ có dấu chấm và khoảng trắng | `file-nhan-duoc` |
| Tên 300 ký tự | Cắt còn 200 byte, giữ đuôi |
| Tên chứa `<>:"\|?*` hoặc ký tự điều khiển | Thay bằng `_` hoặc bỏ |
| Trùng tên file đã có | `ten (1).ext` |
| Ổ đĩa không đủ chỗ | REJECT `insufficient_space` trước khi nhận |
| Ổ đầy giữa chừng | Dừng, báo lỗi, giữ `.part` |
| Hai máy gửi cùng một file cùng lúc | Lượt sau REJECT `busy` |
| Kết nối rồi im lặng | Đóng sau 15 giây |
| Byte rác, khung khổng lồ, loại khung lạ | Đóng kết nối đó, không ảnh hưởng kết nối khác |

## 5. Theo dõi kết quả

Mỗi lần chạy kiểm thử thủ công (hệ thống, phá hoại, bảo mật, khả dụng), thêm một dòng. Ca không đạt thì mở issue nhãn `loi`, giao cho chủ module, ghi số issue vào cột Ghi chú.

| Ngày | Mã | Người chạy | Máy, mạng | Kết quả | Ghi chú |
|---|---|---|---|---|---|
| | | | | | |
