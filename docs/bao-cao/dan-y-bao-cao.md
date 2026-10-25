# Dàn ý báo cáo

Mỗi người viết phần của mình (nhiệm vụ **T42**, hạn **thứ Tư tuần 5**), R6 tổng hợp và thống nhất văn phong (T43), R1 duyệt lần cuối.

Số trang chỉ là gợi ý. Viết đủ ý, có hình, có số liệu, quan trọng hơn viết dài.

| Chương | Người viết | Số trang |
|---|---|---|
| 1. Giới thiệu | R6 | 2 |
| 2. Cơ sở lý thuyết | R1 (2.1–2.3), R2 (2.4), R3 (2.5) | 5 |
| 3. Phân tích và thiết kế | R1 | 6 |
| 4. Cài đặt | R2, R3, R4, R5 — mỗi người một mục | 8 |
| 5. Kiểm thử | R6, R4 (mục an toàn) | 3 |
| 6. Đo đạc và đánh giá | R6, R3 (E5) | 5 |
| 7. Kết luận | R1 | 2 |
| Phụ lục | R2 (hướng dẫn), R1 (đóng góp) | — |

---

## Chương 1. Giới thiệu — R6

- 1.1 Bài toán: chuyển file trong cùng mạng và nhược điểm của các cách hiện có (Zalo, Google Drive, USB)
- 1.2 Mục tiêu đồ án — lấy từ [docs/01](../01-de-cuong.md) mục 3
- 1.3 Phạm vi và những gì nằm ngoài phạm vi
- 1.4 Bố cục báo cáo

## Chương 2. Cơ sở lý thuyết

- 2.1 Mô hình TCP/IP và vị trí của giao thức tầng ứng dụng — **R1**
- 2.2 Socket: bind, listen, accept, connect, send, recv — **R1**
- 2.3 Mô hình client–server và ngang hàng; Truyền Nhanh thuộc mô hình nào và vì sao là cả hai — **R1**, dựa vào [docs/02](../02-kien-truc.md) mục 1
- 2.4 UDP, broadcast, giới hạn của broadcast trong một mạng con — **R2**
- 2.5 TCP: dòng byte tin cậy, vì sao cần đóng khung thông điệp; so sánh với UDP — **R3**
- 2.6 Hàm băm SHA-256 và kiểm tra toàn vẹn — **R3**

## Chương 3. Phân tích và thiết kế — R1

- 3.1 Yêu cầu chức năng và phi chức năng — bảng FR, NFR từ docs/01
- 3.2 Kiến trúc tổng thể, các module và ai phụ trách — sơ đồ ở docs/02
- 3.3 Đặc tả giao thức: dò tìm, khung, các loại thông điệp, trình tự, truyền tiếp — tóm tắt [docs/03](../03-dac-ta-giao-thuc.md), kèm sơ đồ trình tự và một ví dụ hex
- 3.4 Mô hình luồng và lý do chọn đa luồng
- 3.5 Các quyết định thiết kế D1–D8 và đánh đổi của từng quyết định

## Chương 4. Cài đặt

Mỗi mục có cùng bốn phần: **cấu trúc code** (lớp, hàm chính); **đoạn code quan trọng nhất** kèm giải thích (ngắn, không dán cả file); **khó khăn gặp phải** và cách giải quyết; **ảnh chụp** chạy thật.

- 4.1 Dò tìm thiết bị — **R2**. Gợi ý khó khăn: tường lửa, nhiều card mạng, WiFi trường
- 4.2 Bên gửi và truyền tiếp — **R3**. Gợi ý: tự kết nối lại, chọn kích thước khối
- 4.3 Bên nhận và an toàn — **R4**. Gợi ý: đa luồng, quản lý `.part`, làm sạch tên file
- 4.4 Giao diện — **R5**. Gợi ý: vì sao giao diện đơ nếu làm sai, và cách hàng đợi sự kiện giải quyết
- 4.5 Giao diện dòng lệnh — **R2**

## Chương 5. Kiểm thử — R6

- 5.1 Chiến lược: các mức kiểm thử, CI tự chạy trên mỗi PR
- 5.2 Kết quả: bảng ca kiểm thử từ [docs/08](../08-kiem-thu.md) với cột đạt / không đạt
- 5.3 Kiểm thử an toàn: các ca tấn công đã thử và kết quả — **R4** viết phần phân tích
- 5.4 Lỗi đáng kể đã tìm thấy và đã sửa (dẫn link issue)

## Chương 6. Đo đạc và đánh giá

Mỗi thí nghiệm theo đúng thứ tự: **câu hỏi** → **cách đo** → **biểu đồ** → **giải thích nối với lý thuyết**. Xem [docs/07](../07-ke-hoach-do-dac.md).

- 6.1 Môi trường đo — **R6**
- 6.2 E1 Kích thước khối — **R6**
- 6.3 E2 Môi trường mạng — **R6**
- 6.4 E3 So với Zalo, Google Drive, USB — **R6**
- 6.5 E4 Truyền tiếp — **R6**
- 6.6 E5 UDP thuần — **R3**
- 6.7 E6 Dò tìm — **R6**
- 6.8 Đối chiếu với các yêu cầu phi chức năng: NFR nào đạt, NFR nào chưa, vì sao — **R6**

## Chương 7. Kết luận — R1

- 7.1 Đã làm được gì, đối chiếu mục tiêu ở chương 1
- 7.2 **Hạn chế** — nói thẳng, không né:
  - Chưa mã hóa đường truyền: người cùng mạng nghe lén được nội dung
  - Chưa xác thực máy gửi: ai cũng tự đặt được tên máy bất kỳ
  - Broadcast không qua được router, chỉ chạy trong một mạng con
  - Các lỗi còn mở khi đóng băng mã nguồn
- 7.3 Hướng phát triển: TLS cho đường truyền, ghép đôi bằng mã PIN, gửi thư mục, ứng dụng điện thoại
- 7.4 Bài học rút ra khi làm việc nhóm

## Phụ lục

- A. Hướng dẫn cài đặt và sử dụng — **R2**, từ `docs/huong-dan-su-dung.md`
- B. Bảng phân công và đóng góp — **R1**: mỗi thành viên, các nhiệm vụ đã làm, link PR, ước lượng phần trăm đóng góp được cả nhóm đồng ý
- C. Toàn văn đặc tả giao thức — docs/03

## Tài liệu tham khảo

Ít nhất gồm:

1. J. F. Kurose, K. W. Ross, *Computer Networking: A Top-Down Approach*, 8th ed., Pearson, 2020.
2. D. B. Makofske, M. J. Donahoo, K. L. Calvert, *TCP/IP Sockets in C#: Practical Guide for Programmers*, Morgan Kaufmann, 2004.
3. Tài liệu Python: `socket`, `threading`, `hashlib`, `tkinter` — docs.python.org
4. Slide môn Lập trình mạng, Chương 1: Tổng quan về lập trình mạng.
