# Lộ trình 5 tuần

## Nhịp làm việc

| Khi nào | Làm gì | Bao lâu |
|---|---|---|
| **Chủ nhật 20:00** | Họp online cả nhóm: mỗi người demo ngắn việc đã xong, kiểm tra mốc của tuần, xem trước việc tuần sau, gỡ vướng | 30 phút |
| **Thứ Tư** | Mỗi người nhắn 3 dòng vào nhóm chat: *đã làm gì — sẽ làm gì — đang vướng gì* | 2 phút |
| **Mỗi ngày** | Cập nhật nhánh của mình từ `main`; duyệt PR được giao trong vòng 24 giờ | |
| **Bất cứ lúc nào** | Vướng một việc quá **một ngày** thì gắn nhãn `can-ho-tro` vào issue và nhắn nhóm ngay. Không im lặng chịu đựng | |

Mỗi buổi họp Chủ nhật bắt đầu bằng một câu hỏi: **mốc của tuần này đạt chưa?** Chưa đạt thì cả buổi họp dành để tìm cách đạt, trước khi bàn sang việc tuần sau.

## Tổng quan

| Tuần | Thời gian | Chủ đề | Mốc phải đạt cuối tuần |
|---|---|---|---|
| **1** | 26/10 – 01/11 | Nền móng | M1 — Đặc tả giao thức v1.0 đã chốt; module đóng khung chạy có kiểm thử; mỗi người đã có PR đầu tiên được hợp nhất. |
| **2** | 02/11 – 08/11 | Từng mảnh chạy riêng | M2 — Gửi được một file giữa hai máy bằng dòng lệnh, SHA-256 hai đầu khớp; giao diện chạy với dữ liệu giả. |
| **3** | 09/11 – 15/11 | Ghép nối & truyền tiếp | M3 — Bản đủ tính năng: giao diện chạy thật trên hai máy, tự thấy nhau, truyền tiếp được khi mất kết nối. |
| **4** | 16/11 – 22/11 | Cứng cáp & đo đạc | M4 — Tag v1.0-rc (đóng băng mã nguồn); đủ số liệu cho các thí nghiệm E1–E4. |
| **5** | 23/11 – 29/11 | Báo cáo & demo | M5 — Nộp: báo cáo, slide, video, bản phát hành v1.0; đã tổng duyệt hai lần. |

---

## Tuần 1 — Nền móng (26/10 – 01/11)

**Mục tiêu.** Cả nhóm hiểu đề tài, môi trường sẵn sàng, giao thức được chốt, biết sớm mạng WiFi trường có dùng được để demo hay không.

| Mã | Việc | Ai | Ưu tiên | Phụ thuộc |
|---|---|---|---|---|
| T01 | Khởi tạo repo GitHub và bảng công việc | R1 | Bắt buộc | — |
| T02 | Cả nhóm: làm quen môi trường và quy trình Git | Cả nhóm | Bắt buộc | T01 |
| T03 | Chốt đặc tả giao thức v1.0 | R1 | Bắt buộc | T02 |
| T04 | Cài đặt module đóng khung (framing) kèm kiểm thử | R1 | Bắt buộc | T03 |
| T05 | Chốt API lõi và danh sách sự kiện với R2–R5 | R1 | Bắt buộc | T02 |
| T06 | Thử nghiệm UDP broadcast giữa hai máy thật | R2 | Bắt buộc | T02 |
| T07 | Kiểm tra WiFi trường có cho các máy nói chuyện với nhau không | R2 | Bắt buộc | T06 |
| T08 | Thử nghiệm gửi một file qua TCP thô (làm cặp với R4) | R3 | Bắt buộc | T02 |
| T09 | Liệt kê các ca nguy hiểm phía bên nhận | R4 | Bắt buộc | T03 |
| T10 | Phác thảo giao diện và dựng cửa sổ tĩnh | R5 | Bắt buộc | T02 |
| T11 | Viết kế hoạch kiểm thử chi tiết | R6 | Bắt buộc | T03 |
| T12 | Công cụ tạo bộ file mẫu và so sánh mã băm | R6 | Bắt buộc | T02 |

**Mốc cuối tuần.** M1 — Đặc tả giao thức v1.0 đã chốt; module đóng khung chạy có kiểm thử; mỗi người đã có PR đầu tiên được hợp nhất.

## Tuần 2 — Từng mảnh chạy riêng (02/11 – 08/11)

**Mục tiêu.** Mỗi module chạy được độc lập. Cuối tuần gửi được một file thật giữa hai máy.

| Mã | Việc | Ai | Ưu tiên | Phụ thuộc |
|---|---|---|---|---|
| T13 | Cài đặt messages.py: tạo và kiểm tra thông điệp JSON | R1 | Bắt buộc | T04 |
| T14 | Phiên bản đầu của lõi (service) với hàng đợi sự kiện | R1 | Bắt buộc | T05 |
| T15 | Cài đặt dò tìm: DISCOVER, ANNOUNCE, BYE | R2 | Bắt buộc | T06, T03 |
| T16 | Bảng thiết bị có hết hạn | R2 | Bắt buộc | T05 |
| T17 | Giao diện dòng lệnh tối thiểu: scan, send, receive | R2 | Bắt buộc | T19, T21 |
| T18 | Bên gửi: tính SHA-256, gửi OFFER, chờ quyết định | R3 | Bắt buộc | T04, T13 |
| T19 | Bên gửi: gửi DATA theo khối, DONE, nhận RESULT, báo tiến độ | R3 | Bắt buộc | T18 |
| T20 | Bên nhận: máy chủ TCP, nhận OFFER, hỏi chấp nhận | R4 | Bắt buộc | T04, T13 |
| T21 | Bên nhận: ghi .part, kiểm tra SHA-256, đổi tên, trả RESULT | R4 | Bắt buộc | T20 |
| T22 | Làm sạch tên file, chống ghi ra ngoài thư mục nhận | R4 | Bắt buộc | T09 |
| T23 | Giao diện chạy với dịch vụ giả (FakeService) | R5 | Bắt buộc | T10, T05 |
| T24 | Viết kiểm thử trước cho framing, messages, tên file | R6 | Bắt buộc | T03, T09 |

**Mốc cuối tuần.** M2 — Gửi được một file giữa hai máy bằng dòng lệnh, SHA-256 hai đầu khớp; giao diện chạy với dữ liệu giả.

## Tuần 3 — Ghép nối & truyền tiếp (09/11 – 15/11)

**Mục tiêu.** Ghép các mảnh thành ứng dụng hoàn chỉnh và làm tính năng truyền tiếp khi đứt mạng.

| Mã | Việc | Ai | Ưu tiên | Phụ thuộc |
|---|---|---|---|---|
| T25 | Ghép dò tìm, gửi, nhận vào service thật | R1 | Bắt buộc | T14, T15, T16, T19, T21 |
| T26 | Truyền tiếp phía gửi và tự kết nối lại | R3 | Nâng cao | T19 |
| T27 | Truyền tiếp phía nhận | R4 | Nâng cao | T21 |
| T28 | Khóa theo file và kiểm tra dung lượng trống | R4 | Bắt buộc | T21 |
| T29 | Thêm máy theo IP và xử lý máy nhiều card mạng | R2 | Bắt buộc | T15 |
| T30 | Nối giao diện với service thật, không đơ cửa sổ | R5 | Bắt buộc | T23, T25 |
| T31 | Kiểm thử tích hợp tự động qua localhost | R6 | Bắt buộc | T12, T25 |
| T32 | Kiểm thử phá hoại: ngắt kết nối giữa chừng | R6 | Nâng cao | T26, T27 |

**Mốc cuối tuần.** M3 — Bản đủ tính năng: giao diện chạy thật trên hai máy, tự thấy nhau, truyền tiếp được khi mất kết nối.

## Tuần 4 — Cứng cáp & đo đạc (16/11 – 22/11)

**Mục tiêu.** Xử lý trường hợp biên, sửa lỗi, đo đạc lấy số liệu. Chủ nhật đóng băng mã nguồn.

| Mã | Việc | Ai | Ưu tiên | Phụ thuộc |
|---|---|---|---|---|
| T33 | Nhiều lượt truyền đồng thời và rà soát luồng | R1 | Bắt buộc | T25 |
| T34 | Đóng băng mã nguồn và phát hành bản ứng viên v1.0-rc | R1 | Bắt buộc | T33, T30 |
| T35 | Hủy lượt gửi và chọn kích thước khối mặc định | R3 | Bắt buộc | T26, T38 |
| T36 | Thí nghiệm E5: gửi file bằng UDP thuần | R3 | Nâng cao | T08 |
| T37 | Dọn .part cũ, xử lý hết dung lượng giữa chừng, sửa lỗi | R4 | Bắt buộc | T27, T32 |
| T38 | Thí nghiệm E1: kích thước khối và tốc độ (làm đầu tuần) | R6 | Bắt buộc | T25 |
| T39 | Thí nghiệm E2–E4 và E6: môi trường mạng, so với Zalo/Drive/USB, truyền tiếp, dò tìm | R6 | Bắt buộc | T32, T38 |
| T40 | Hoàn thiện giao diện | R5 | Bắt buộc | T30, T29 |
| T41 | (Mở rộng) Trang web cho điện thoại gửi file lên máy tính | R2 | Mở rộng | T25 |

**Mốc cuối tuần.** M4 — Tag v1.0-rc (đóng băng mã nguồn); đủ số liệu cho các thí nghiệm E1–E4.

## Tuần 5 — Báo cáo & demo (23/11 – 29/11)

**Mục tiêu.** Viết báo cáo, làm slide, quay video dự phòng, tổng duyệt demo, phát hành v1.0.

| Mã | Việc | Ai | Ưu tiên | Phụ thuộc |
|---|---|---|---|---|
| T42 | Cả nhóm: viết phần báo cáo của module mình | Cả nhóm | Bắt buộc | T34 |
| T43 | Tổng hợp báo cáo hoàn chỉnh | R6 | Bắt buộc | T42, T38, T39 |
| T44 | Slide thuyết trình và video demo dự phòng | R5 | Bắt buộc | T34 |
| T45 | Kịch bản demo, tổng duyệt và phát hành v1.0 | R1 | Bắt buộc | T34, T44 |
| T46 | Hướng dẫn cài đặt và sử dụng | R2 | Bắt buộc | T34 |
| T47 | Sửa lỗi phát hiện khi tổng duyệt | R3, R4 | Bắt buộc | T45 |

**Mốc cuối tuần.** M5 — Nộp: báo cáo, slide, video, bản phát hành v1.0; đã tổng duyệt hai lần.

---

## Khi bị trễ: cắt theo thứ tự này

Năm tuần là ngắn. Nếu đến buổi họp Chủ nhật tuần 3 mà mốc M3 chưa đạt, **cắt việc theo đúng thứ tự dưới đây** thay vì thức đêm làm tất cả rồi không việc nào xong:

1. **T41** — trang web cho điện thoại (vốn là mở rộng)
2. **T40** — phần hàng đợi gửi nhiều file trong giao diện
3. **T37** — dọn file `.part` cũ
4. **T36** — thí nghiệm UDP thuần: thay bằng phân tích lý thuyết trong báo cáo
5. **T33** — nhiều lượt cùng lúc: giới hạn mỗi lúc một lượt, ghi vào mục Hạn chế

**Không bao giờ cắt:**

- **T22** làm sạch tên file — thiếu nó, ai trong mạng cũng ghi được file vào bất kỳ đâu trên máy bạn
- **Kiểm tra SHA-256** — thiếu nó, ứng dụng không chứng minh được file nhận đúng
- **T26, T27** truyền tiếp — tính năng làm nên điểm cao và là phần ấn tượng nhất khi demo
- **T30** giao diện không đơ — một ứng dụng đơ trong lúc demo bị đánh giá là hỏng, dù phần mạng chạy đúng

## Demo

### Kịch bản gợi ý (khoảng 6 phút)

1. **Vấn đề** (30 giây) — chiếu cảnh gửi ảnh qua Zalo bị nén, hoặc thời gian tải lên rồi tải xuống Google Drive.
2. **Tự tìm thấy nhau** (1 phút) — bật ứng dụng trên hai máy, máy kia hiện lên trong danh sách. Mở Wireshark lọc `udp.port == 50505` cho thầy thấy gói ANNOUNCE bằng JSON mà nhóm tự thiết kế.
3. **Gửi file** (1 phút) — gửi file 500 MB: hộp thoại xác nhận ở máy nhận, thanh tiến trình, tốc độ, SHA-256 khớp.
4. **Rớt mạng** (1 phút) — gửi lại một file lớn, rút WiFi ở khoảng 50%, cắm lại: ứng dụng tiếp tục đúng chỗ cũ. Đây là đoạn ấn tượng nhất, nên tập kỹ.
5. **An toàn** (30 giây) — dùng dòng lệnh gửi một file tên `../../hack.txt`: máy nhận lưu thành `hack.txt` nằm gọn trong thư mục nhận.
6. **Số liệu** (1 phút) — hai biểu đồ: tốc độ theo kích thước khối, và so sánh với Zalo, Google Drive, USB.
7. **Hạn chế** (30 giây) — nói thẳng: chưa mã hóa đường truyền, và cách sẽ khắc phục (TLS).

### Phương án dự phòng

Demo trực tiếp là lúc dễ hỏng nhất. Chuẩn bị đủ ba lớp:

1. **Mạng riêng** — một điện thoại phát WiFi hoặc một router mang theo, đã thử trước với đúng hai máy demo. Dùng nếu WiFi phòng thuyết trình chặn các máy nhìn thấy nhau (đã kiểm tra ở T07).
2. **Thêm máy theo IP** — nếu dò tìm không chạy, gõ IP máy kia và tiếp tục.
3. **Video** (T44) — nếu mọi thứ đều hỏng, chiếu video và trả lời câu hỏi bình thường.

Tổng duyệt **hai lần** trên đúng hai máy sẽ dùng khi thuyết trình, ở trường, trước ngày nộp (T45).
