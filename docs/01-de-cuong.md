# Đề cương đồ án

## 1. Thông tin chung

| | |
|---|---|
| **Tên đề tài** | Truyền Nhanh — Ứng dụng truyền file trong mạng LAN không cần Internet |
| **Tên tiếng Anh** | Truyen Nhanh — Peer-to-peer LAN File Transfer |
| **Môn học** | Lập trình mạng |
| **Số thành viên** | 6 |
| **Thời gian** | 26/10/2026 – 29/11/2026 (5 tuần) |
| **Ngôn ngữ** | Python 3.10+, chỉ dùng thư viện chuẩn |

## 2. Lý do chọn đề tài

**Bài toán có thật.** Sinh viên chuyển file cho nhau hằng ngày trong phòng học và phòng máy. Các cách hiện có đều có nhược điểm: Zalo và Messenger nén ảnh và giới hạn dung lượng; Google Drive buộc dữ liệu đi ra Internet rồi quay về, chậm khi mạng trường yếu; USB phải có sẵn và phải cầm sang tận nơi. Trong khi đó, hai máy trong cùng một mạng LAN có thể truyền trực tiếp cho nhau với tốc độ cao hơn nhiều so với đường Internet.

**Đúng trọng tâm môn học.** Đề tài không dựa vào dịch vụ hay API của bên thứ ba. Toàn bộ hệ thống là code của nhóm: hai máy tìm thấy nhau, bắt tay, trao đổi dữ liệu bằng một giao thức do nhóm tự định nghĩa. Đề tài chạm vào cả hai giao thức tầng giao vận — UDP cho việc dò tìm, TCP cho việc truyền dữ liệu — và buộc nhóm viết cả phía server lẫn phía client.

**Đo được bằng số.** Mọi quyết định thiết kế (kích thước khối, chọn TCP thay vì UDP, truyền tiếp) đều kiểm chứng được bằng thí nghiệm, cho phép báo cáo có kết luận dựa trên số liệu chứ không chỉ mô tả.

## 3. Mục tiêu

**Về kiến thức**, sau đồ án mỗi thành viên hiểu và giải thích được:

- Sự khác nhau giữa UDP và TCP, khi nào dùng cái nào, có số liệu đo để chứng minh
- Broadcast trong mạng LAN và giới hạn của nó
- Vì sao TCP là dòng byte và cách tự đóng khung thông điệp trên dòng byte đó
- Lập trình socket phía server (bind, listen, accept, đa luồng) và phía client (connect, send, recv)
- Thiết kế một giao thức tầng ứng dụng: định dạng thông điệp, trình tự trao đổi, xử lý lỗi, hết giờ
- Các thành phần độ trễ và thông lượng (Kurose Chương 1) thể hiện trên một hệ thống thật

**Về sản phẩm**: một ứng dụng chạy được trên Windows, có giao diện đồ họa và dòng lệnh, đủ ổn định để cả lớp dùng thử trong buổi demo.

## 4. Phạm vi

**Trong phạm vi**

- Dò tìm tự động các máy chạy ứng dụng trong cùng một mạng con (subnet)
- Thêm máy thủ công theo địa chỉ IP
- Gửi một file mỗi lượt; gửi nhiều file bằng cách xếp hàng nhiều lượt
- Kiểm tra toàn vẹn, truyền tiếp khi đứt, hủy lượt truyền
- Giao diện đồ họa (Tkinter) và giao diện dòng lệnh

**Ngoài phạm vi** (ghi rõ để không bị hỏi vì sao không làm)

- Ứng dụng điện thoại cài đặt riêng (Android, iOS)
- Truyền qua Internet hoặc giữa hai mạng khác nhau (xuyên NAT)
- Mã hóa đường truyền và xác thực danh tính máy gửi. Đây là **hạn chế đã biết**: người khác trong cùng mạng có thể nghe lén nội dung file và có thể giả mạo tên máy. Sẽ được trình bày trong mục Hạn chế của báo cáo kèm hướng giải quyết (TLS)
- Gửi nguyên cả thư mục, đồng bộ thư mục

## 5. Yêu cầu chức năng

| Mã | Yêu cầu | Ưu tiên |
|---|---|---|
| FR-01 | Tự phát hiện các máy đang chạy ứng dụng trong cùng mạng LAN, người dùng không cần nhập IP | Bắt buộc |
| FR-02 | Thêm máy thủ công bằng địa chỉ IP, dùng khi mạng chặn dò tìm | Bắt buộc |
| FR-03 | Gửi một file bất kỳ tới một máy đã chọn, kể cả file 0 byte và file lớn hơn 4 GB | Bắt buộc |
| FR-04 | Người nhận được hỏi và quyết định nhận hay từ chối trước khi bất kỳ byte nội dung nào được truyền | Bắt buộc |
| FR-05 | Hiển thị tiến độ, tốc độ và thời gian còn lại ở cả hai phía | Bắt buộc |
| FR-06 | Kiểm tra toàn vẹn bằng SHA-256; file chưa xác minh không bao giờ xuất hiện trong thư mục nhận | Bắt buộc |
| FR-07 | Truyền tiếp từ vị trí đã nhận khi kết nối bị đứt | Nâng cao |
| FR-08 | Hủy lượt truyền từ bất kỳ phía nào | Bắt buộc |
| FR-09 | Nhận từ nhiều máy và gửi tới nhiều máy cùng lúc | Nâng cao |
| FR-10 | Sử dụng được bằng cả giao diện đồ họa và dòng lệnh | Bắt buộc |
| FR-11 | Điện thoại gửi file lên máy tính qua trình duyệt web | Mở rộng |

## 6. Yêu cầu phi chức năng

Mỗi yêu cầu đều đo hoặc kiểm tra được, và được ánh xạ sang ca kiểm thử trong [docs/08](08-kiem-thu.md).

| Mã | Yêu cầu | Cách kiểm tra |
|---|---|---|
| NFR-01 | **Dò tìm:** máy mới xuất hiện ở máy khác trong vòng 3 giây; máy tắt bình thường biến mất ngay; máy tắt đột ngột biến mất trong vòng 7 giây | Thí nghiệm E6 |
| NFR-02 | **Toàn vẹn:** 100% file nhận thành công có SHA-256 khớp file gốc | Kiểm thử tích hợp với bộ file mẫu |
| NFR-03 | **Truyền tiếp:** sau khi nối lại, không gửi lại byte nào bên nhận đã ghi xuống đĩa | Thí nghiệm E4 |
| NFR-04 | **Phản hồi:** giao diện không đơ trong khi truyền — vẫn kéo được cửa sổ, bấm được nút | Kiểm thử thủ công với file 1 GB |
| NFR-05 | **An toàn:** không ghi file ra ngoài thư mục nhận với bất kỳ tên file nào; không nhận dữ liệu khi người nhận chưa đồng ý; khung tin vượt giới hạn bị từ chối mà không đọc | Bộ ca kiểm thử bảo mật |
| NFR-06 | **Hiệu năng:** gửi file 500 MB trong cùng phòng phải nhanh hơn cách tải lên rồi tải xuống Google Drive | Thí nghiệm E3 |
| NFR-07 | **Nền tảng:** chạy trên Windows 10/11 (bắt buộc), macOS và Linux (nên có); không cần Internet, không cần máy chủ trung gian | Chạy thử trên máy các thành viên |

## 7. Công nghệ

| Thành phần | Lựa chọn | Lý do |
|---|---|---|
| Ngôn ngữ | Python 3.10+ | Module `socket` ánh xạ một-một với các lệnh socket trong giáo trình; chạy đa nền tảng; dễ tiếp cận cho cả nhóm |
| Mạng | `socket` (thư viện chuẩn) | Làm việc trực tiếp ở mức socket, không qua thư viện mạng mức cao |
| Đồng thời | `threading`, `queue` | Mô hình luồng dễ hiểu, khớp với ví dụ socket chặn (blocking) trong giáo trình |
| Mã băm | `hashlib` (SHA-256) | Có sẵn, đủ mạnh để phát hiện mọi sai lệch |
| Giao diện | `tkinter` | Có sẵn trong Python, không cần cài thêm |
| Kiểm thử | `pytest` | Chuẩn de facto của Python |
| Quản lý mã nguồn | Git, GitHub, GitHub Actions | Phân công qua issue, duyệt qua Pull Request, CI tự chạy kiểm thử |

## 8. Sản phẩm bàn giao

1. Mã nguồn trên GitHub, bản phát hành `v1.0` kèm file zip
2. Báo cáo đồ án (theo [dàn ý](bao-cao/dan-y-bao-cao.md))
3. Đặc tả giao thức ([docs/03](03-dac-ta-giao-thuc.md))
4. Bộ số liệu đo đạc (CSV) và biểu đồ
5. Slide thuyết trình và video demo
6. Hướng dẫn cài đặt và sử dụng

## 9. Rủi ro và phương án

| Rủi ro | Khả năng | Hậu quả | Phương án |
|---|---|---|---|
| WiFi trường bật chế độ cách ly, các máy không thấy nhau | Cao | Demo trực tiếp thất bại | Kiểm tra ngay tuần 1 (T07). Dự phòng: phát WiFi từ điện thoại, mang router riêng, dùng dây mạng phòng máy, thêm máy theo IP, và video demo (T44) |
| Tường lửa Windows chặn gói broadcast và kết nối đến | Cao | Ứng dụng không thấy máy khác | Viết hướng dẫn mở tường lửa từ tuần 1 (T06); chuyển mạng sang chế độ Private |
| Máy có card mạng ảo (VirtualBox, VMware, VPN) phát broadcast nhầm card | Trung bình | Không thấy máy dù cùng mạng | Thêm máy theo IP (T29); ghi cách xử lý vào hướng dẫn |
| Một thành viên chậm tiến độ trên đường găng | Trung bình | Kéo trễ cả nhóm | Họp kiểm tra giữa tuần; mỗi vai có người dự phòng ([docs/04](04-phan-cong.md)); có danh sách việc được cắt ([docs/05](05-lo-trinh.md)) |
| Xung đột Git khi nhiều người sửa cùng file | Trung bình | Mất thời gian, mất code | Mỗi người sở hữu file riêng; PR nhỏ; cập nhật từ main hằng ngày |
| Giao diện đơ vì gọi hàm mạng trên luồng giao diện | Cao nếu không biết trước | Ứng dụng trông như bị treo | Mô hình luồng được quy định sẵn trong [docs/02](02-kien-truc.md) mục 4 |

## 10. Tiêu chí tự đánh giá

| Mức | Điều kiện |
|---|---|
| **Đạt** | Mọi yêu cầu Bắt buộc hoạt động; có báo cáo và demo |
| **Khá** | Thêm FR-07 truyền tiếp hoạt động và được chứng minh bằng thí nghiệm E4 |
| **Giỏi** | Thêm FR-09; đủ thí nghiệm E1–E6 có biểu đồ và phân tích nối với lý thuyết môn học |
| **Xuất sắc** | Thêm FR-11; báo cáo có phần so sánh với giải pháp có sẵn và chỉ ra hạn chế cùng hướng khắc phục |
