# Kế hoạch đo đạc

Số liệu là thứ biến báo cáo từ "nhóm em đã làm..." thành "nhóm em đã chứng minh...". Mỗi thí nghiệm dưới đây trả lời một câu hỏi cụ thể và nối với một phần lý thuyết của môn học.

Người chạy chính là **R6**; thí nghiệm E5 do **R3**. Tuần 4 cần nhiều máy nên cả nhóm hỗ trợ.

## 1. Quy tắc chung — áp dụng cho mọi thí nghiệm

**Ghi môi trường đo** vào đầu mỗi file CSV, dạng dòng chú thích `#`: máy gửi và máy nhận (CPU, RAM, ổ SSD hay HDD, hệ điều hành), loại kết nối (dây hay WiFi, băng tần 2,4 hay 5 GHz), khoảng cách tới router, ngày giờ đo. Không có thông tin này thì con số vô nghĩa — cùng một chương trình có thể chạy nhanh gấp mười lần chỉ vì đổi từ WiFi sang dây.

**Lặp lại ít nhất 5 lần** mỗi điểm đo. Báo cáo **trung bình** và **độ lệch chuẩn**. Bỏ lần chạy đầu tiên (ổ đĩa và bộ nhớ đệm hệ điều hành chưa "nóng") hoặc ghi rõ là không bỏ.

**Định nghĩa rõ đo từ đâu tới đâu.** Trong tài liệu này:
- **Thời gian truyền** = từ lúc bên gửi gửi khung DATA đầu tiên đến lúc nhận RESULT. Không tính thời gian tính mã băm và thời gian người dùng suy nghĩ.
- **Thời gian đầu cuối** = từ lúc bấm Gửi đến lúc file sẵn sàng ở máy nhận. Dùng cho E3, vì đó là thời gian người dùng thật cảm nhận.
- **Tốc độ** = kích thước file ÷ thời gian truyền, đơn vị **MB/s với 1 MB = 1 000 000 byte**. Khi so với tốc độ đường truyền thì đổi sang Mbps (nhân 8).

**Giữ mọi thứ khác không đổi** khi thay một biến: cùng hai máy, cùng vị trí, cùng file, cùng thời điểm trong ngày nếu được. Tắt các ứng dụng tải nặng (cập nhật Windows, đồng bộ OneDrive) trên cả hai máy.

**Mọi số liệu thô** lưu thành CSV trong `ket-qua/`, mọi biểu đồ lưu ở `docs/hinh/`. Biểu đồ phải có tên trục kèm đơn vị, thanh sai số (độ lệch chuẩn), và chú thích nguồn số liệu (tên file CSV). Không dùng biểu đồ 3D hay biểu đồ tròn.

## 2. Các thí nghiệm

### E1 — Kích thước khối ảnh hưởng tốc độ thế nào?

| | |
|---|---|
| **Nhiệm vụ** | T38 (R6), đầu tuần 4 — R3 cần kết quả cho T35 |
| **Biến thay đổi** | Kích thước khối DATA: 4 KB, 16 KB, 64 KB, 256 KB, 1 MB |
| **Giữ nguyên** | File 500 MB, hai máy, một mạng |
| **Đo** | Thời gian truyền → tốc độ |
| **File kết quả** | `ket-qua/e1-kich-thuoc-khoi.csv` |

**Dự đoán:** tốc độ tăng theo kích thước khối rồi chững lại. Khối nhỏ thì chậm, nhưng **không phải** vì 5 byte phần đầu khung: 5 byte trên khối 4 KB chỉ là 0,12%. Nguyên nhân thật là chi phí cố định cho **mỗi lần** gửi một khung — một vòng lặp Python, một lời gọi hệ thống `send`. Khối càng nhỏ thì số lần gọi càng nhiều. Khi khối đủ lớn, tốc độ chạm trần của đường truyền hoặc ổ đĩa và không tăng nữa.

**Nối với lý thuyết:** thời gian truyền một gói `d_trans = L/R` (Kurose Chương 1, slide 49) chỉ là một phần chi phí; phần xử lý ở hai đầu (`d_proc`) mới là thứ làm khối nhỏ chậm.

**Kết quả dùng để:** chọn `DEFAULT_CHUNK_SIZE` bằng số liệu thay vì đoán (T35).

### E2 — Môi trường mạng ảnh hưởng tốc độ thế nào?

| | |
|---|---|
| **Nhiệm vụ** | T39 (R6) |
| **Biến thay đổi** | Cùng một máy (localhost) · cáp mạng · WiFi 2,4 GHz · WiFi 5 GHz |
| **Giữ nguyên** | File 500 MB, khối mặc định |
| **File kết quả** | `ket-qua/e2-moi-truong.csv` |

**Dự đoán:** localhost nhanh nhất — đó là trần của phần mềm và ổ đĩa, không có mạng nào cản. Cáp nhanh hơn WiFi; WiFi 5 GHz nhanh hơn 2,4 GHz.

**Nối với lý thuyết:** thông lượng đầu cuối bằng thông lượng của **liên kết hẹp nhất** trên đường đi (Kurose Chương 1, slide 56–58). So con số đo được với tốc độ danh định của từng loại kết nối, và giải thích vì sao luôn thấp hơn.

### E3 — Truyền Nhanh so với cách mọi người đang dùng

| | |
|---|---|
| **Nhiệm vụ** | T39 (R6) |
| **So sánh** | Truyền Nhanh · Zalo · Google Drive (tải lên rồi tải xuống) · USB |
| **Giữ nguyên** | Cùng một file 500 MB, cùng hai máy, cùng phòng |
| **Đo** | Thời gian đầu cuối; kích thước file nhận được; SHA-256 có khớp không |
| **File kết quả** | `ket-qua/e3-so-sanh.csv` |

Với Zalo, thử thêm một ảnh chụp từ điện thoại và ghi kích thước trước và sau khi gửi: ảnh bị nén nghĩa là SHA-256 không khớp. Nếu Zalo từ chối file 500 MB vì quá giới hạn dung lượng, ghi lại giới hạn đó — bản thân điều đó đã là một kết quả.

**Nối với lý thuyết:** đường đi qua Google Drive đi ra Internet rồi quay về, nên bị giới hạn bởi đường truyền Internet của trường — liên kết hẹp nhất ở E2 giờ nằm ngoài mạng LAN.

**Thí nghiệm này là căn cứ cho NFR-06.**

### E4 — Truyền tiếp tiết kiệm được bao nhiêu?

| | |
|---|---|
| **Nhiệm vụ** | T39 (R6), dùng kịch bản của T32 |
| **Biến thay đổi** | Điểm cắt kết nối: 25%, 50%, 75% |
| **Đo** | Số byte đã nhận trước khi cắt; số byte bị gửi lại; thời gian từ lúc có mạng lại đến lúc dữ liệu chảy tiếp; SHA-256 cuối cùng |
| **So với** | Trường hợp giả định không có truyền tiếp (phải gửi lại từ đầu) |
| **File kết quả** | `ket-qua/e4-truyen-tiep.csv` |

Cắt kết nối bằng cách tắt WiFi máy nhận, **không** bằng cách tắt ứng dụng (tắt ứng dụng là một kịch bản khác, ghi riêng nếu có thời gian).

**Dự đoán:** số byte gửi lại bằng 0 (NFR-03). Thời gian khôi phục bằng khoảng chờ thử lại cộng một lần bắt tay TCP cộng thời gian tính lại mã băm phần đã có.

### E5 — Vì sao không truyền file bằng UDP?

| | |
|---|---|
| **Nhiệm vụ** | T36 (R3) |
| **Cách làm** | Công cụ `tools/thu_udp_thuan.py` cắt file thành gói UDP có đánh số thứ tự, bắn đi **không** có xác nhận hay gửi lại; bên nhận ghi lại gói nào tới, theo thứ tự nào |
| **Biến thay đổi** | Tốc độ bắn: 100, 1 000, 10 000 gói/giây, và không giới hạn |
| **Đo** | % gói mất; % gói tới sai thứ tự; file ghép lại có khớp SHA-256 không |
| **File kết quả** | `ket-qua/e5-udp-thuan.csv` |

**Dự đoán:** bắn chậm thì trong LAN có thể không mất gói nào; bắn càng nhanh thì càng mất nhiều, vì bộ đệm ở máy nhận hoặc ở router đầy và gói tới sau bị bỏ. Chỉ cần mất **một** gói là file hỏng.

**Nối với lý thuyết:** UDP không bảo đảm gói tới nơi, không bảo đảm thứ tự (Kurose Chương 3, slide 24–35); gói bị mất khi bộ đệm hàng đợi đầy (Kurose Chương 1, slide 32 và 55). Đây là lý lẽ bằng số cho quyết định D2 ở [docs/02](02-kien-truc.md).

### E6 — Dò tìm nhanh đến đâu?

| | |
|---|---|
| **Nhiệm vụ** | T39 (R6) |
| **Đo** | Thời gian từ lúc bật ứng dụng ở máy A đến lúc A hiện trong danh sách máy B; từ lúc tắt bình thường đến lúc biến mất; từ lúc tắt đột ngột (rút WiFi) đến lúc biến mất |
| **File kết quả** | `ket-qua/e6-do-tim.csv` |

**Dự đoán:** xuất hiện gần như tức thì nhờ DISCOVER và ANNOUNCE trả lời ngay; tắt bình thường biến mất tức thì nhờ BYE; tắt đột ngột biến mất sau khoảng 5–7 giây.

**Căn cứ cho NFR-01.**

## 3. Định dạng file CSV

Dòng đầu là chú thích môi trường, rồi một dòng tiêu đề, mỗi lần đo một dòng. Ví dụ cho E1:

```csv
# may_gui=Laptop Long (i5-1135G7, SSD, Windows 11); may_nhan=PC phòng máy 07 (i3-10100, HDD, Windows 10)
# ket_noi=WiFi 5 GHz, cách router 3 m; ngay=2026-11-17 14:00
lan,kich_thuoc_khoi_byte,kich_thuoc_file_byte,thoi_gian_s,toc_do_MBps,ghi_chu
1,4096,500000000,98.41,5.08,
2,4096,500000000,97.12,5.15,
```

Các thí nghiệm khác dùng cùng cấu trúc, đổi các cột cho phù hợp với biến được đo. Công cụ vẽ biểu đồ đặt ở `tools/`.
