# Phân công

## 1. Nguyên tắc chia việc

**Mỗi người sở hữu một mảnh code riêng.** Người sở hữu chịu trách nhiệm cho mảnh đó chạy đúng, có test, có tài liệu. Người khác muốn sửa file của bạn thì mở PR và bạn duyệt. Nhờ vậy sáu người làm song song mà hiếm khi sửa trùng một file.

**Các mảnh khớp với nhau nhờ hợp đồng, không nhờ hỏi miệng.** Có hai hợp đồng: [đặc tả giao thức](03-dac-ta-giao-thuc.md) giữa bên gửi và bên nhận, và [API của lõi](02-kien-truc.md) giữa giao diện và phần mạng. Cả hai được chốt trong tuần 1. Muốn đổi hợp đồng thì sửa tài liệu trước qua PR, rồi mới sửa code.

**Ai cũng viết code mạng.** Không có vai nào chỉ làm giao diện hay chỉ viết báo cáo: R5 phải xử lý đúng mô hình luồng khi nối giao diện với mạng, R6 viết test tích hợp mở socket thật và chạy thí nghiệm đo đạc. Ai cũng phải trả lời được câu hỏi của thầy về phần mình.

**Mỗi người viết phần báo cáo của mình.** R6 tổng hợp, nhưng không viết hộ.

## 2. Tổng quan sáu vai

| Vai | Phụ trách | Sở hữu | Dự phòng | Số việc riêng |
|---|---|---|---|---|
| **R1** | Trưởng nhóm · Giao thức & Lõi | `protocol/`<br>`core/`<br>`config.py`<br>`docs/03-dac-ta-giao-thuc.md` | R3 | 10 |
| **R2** | Dò tìm thiết bị (UDP) & Dòng lệnh | `discovery/`<br>`cli/` | R1 | 8 |
| **R3** | Bên gửi (TCP client) | `transfer/sender.py`<br>`transfer/hashing.py` | R4 | 7 |
| **R4** | Bên nhận (TCP server) | `transfer/receiver.py`<br>`transfer/storage.py`<br>`transfer/filenames.py` | R3 | 8 |
| **R5** | Giao diện (Tkinter) | `gui/` | R2 | 5 |
| **R6** | Kiểm thử · Đo đạc · Báo cáo | `tests/`<br>`tools/`<br>`ket-qua/`<br>`docs/bao-cao/` | R5 | 8 |

**Người dự phòng** là người nắm phần việc đó nhiều thứ hai, sẽ đỡ việc khi chủ module ốm, bận thi hoặc bị kẹt quá lâu. Người dự phòng nên đọc qua PR của chủ module mỗi tuần.

## 3. Ai làm gì, tuần nào

| Vai | Tuần 1<br>26/10 – 01/11 | Tuần 2<br>02/11 – 08/11 | Tuần 3<br>09/11 – 15/11 | Tuần 4<br>16/11 – 22/11 | Tuần 5<br>23/11 – 29/11 |
|---|---|---|---|---|---|
| **R1** | T01 T03 T04 T05 | T13 T14 | T25 | T33 T34 | T45 |
| **R2** | T06 T07 | T15 T16 T17 | T29 | T41 | T46 |
| **R3** | T08 | T18 T19 | T26 | T35 T36 | T47 |
| **R4** | T09 | T20 T21 T22 | T27 T28 | T37 | T47 |
| **R5** | T10 | T23 | T30 | T40 | T44 |
| **R6** | T11 T12 | T24 | T31 T32 | T38 T39 | T43 |
| **Cả nhóm** | T02 | — | — | — | T42 |

## 4. Ai duyệt PR của ai

Mỗi PR cần **1 người duyệt** trước khi hợp nhất. Người duyệt mặc định:

| PR của | Người duyệt | Lý do |
|---|---|---|
| R1 | R3 | R3 dùng trực tiếp phần đóng khung và thông điệp của R1 |
| R2 | R1 | Dò tìm phải khớp đặc tả mục 3, và nối vào lõi |
| R3 | **R4** | Bên gửi và bên nhận là hai đầu của cùng một giao thức |
| R4 | **R3** | Như trên |
| R5 | R2 | R2 cũng viết giao diện (dòng lệnh) trên cùng API lõi |
| R6 | Chủ của module đang được kiểm thử | Người viết code biết test có kiểm tra đúng ý không |

**Ngoại lệ bắt buộc:** PR nào sửa `src/truyennhanh/protocol/`, `src/truyennhanh/core/` hoặc `docs/03-dac-ta-giao-thuc.md` thì **R1 phải duyệt**, vì đó là hợp đồng chung.

Duyệt trong vòng **24 giờ**. Không kịp thì nhắn trong nhóm để người khác duyệt thay.

## 5. Đường găng

Đường găng là chuỗi việc phụ thuộc nhau dài nhất. **Bất kỳ việc nào trên chuỗi này trễ một ngày thì cả dự án trễ một ngày**, nên đây là những việc cần theo dõi sát nhất trong buổi họp:

1. **T01** Khởi tạo repo GitHub và bảng công việc — R1, tuần 1
2. **T02** Cả nhóm: làm quen môi trường và quy trình Git — Cả nhóm, tuần 1
3. **T03** Chốt đặc tả giao thức v1.0 — R1, tuần 1
4. **T04** Cài đặt module đóng khung (framing) kèm kiểm thử — R1, tuần 1
5. **T13** Cài đặt messages.py: tạo và kiểm tra thông điệp JSON — R1, tuần 2
6. **T18** Bên gửi: tính SHA-256, gửi OFFER, chờ quyết định — R3, tuần 2
7. **T19** Bên gửi: gửi DATA theo khối, DONE, nhận RESULT, báo tiến độ — R3, tuần 2
8. **T25** Ghép dò tìm, gửi, nhận vào service thật — R1, tuần 3
9. **T33** Nhiều lượt truyền đồng thời và rà soát luồng — R1, tuần 4
10. **T34** Đóng băng mã nguồn và phát hành bản ứng viên v1.0-rc — R1, tuần 4
11. **T44** Slide thuyết trình và video demo dự phòng — R5, tuần 5
12. **T45** Kịch bản demo, tổng duyệt và phát hành v1.0 — R1, tuần 5
13. **T47** Sửa lỗi phát hiện khi tổng duyệt — R3, R4, tuần 5

Ba điểm hội tụ cần chú ý: **T04** (đóng khung, cuối tuần 1) chặn cả bên gửi lẫn bên nhận; **T25** (ghép nối, giữa tuần 3) cần đủ việc của R2, R3, R4; **T34** (đóng băng mã nguồn, Chủ nhật tuần 4) chặn toàn bộ tuần 5.

## 6. Chi tiết từng vai

### R1 — Trưởng nhóm · Giao thức & Lõi

**Bạn làm gì.** Giữ đặc tả giao thức; viết lớp đóng khung và lớp thông điệp mà bên gửi, bên nhận dựa vào; viết lõi để ghép mọi thành phần lại thành một ứng dụng; duyệt các PR đụng tới hợp đồng chung; điều phối buổi họp và phát hành.

**Bạn sở hữu.** `src/truyennhanh/protocol/`, `src/truyennhanh/core/`, `src/truyennhanh/config.py`, `docs/03-dac-ta-giao-thuc.md`.

**Bạn cung cấp cho người khác.**
- Cho R3, R4: module đóng khung (cuối tuần 1) và module thông điệp (giữa tuần 2) — **đây là thứ chặn nhiều người nhất, ưu tiên số một**
- Cho R2, R5: API lõi và danh sách sự kiện đã chốt (cuối tuần 1)
- Cho cả nhóm: tag `spec-v1.0`, bản ghép nối chạy được (giữa tuần 3)

**Bạn cần từ người khác.** Thành phần dò tìm, gửi, nhận chạy được độc lập vào cuối tuần 2 để ghép ở tuần 3.

**Đọc trước.** docs/02 và 03 (bạn là người giải đáp cho cả nhóm); Kurose Chương 2, slide 99–108 (Socket programming); *TCP/IP Sockets in C#*, mục 3.3 *Framing and Parsing* và 4.3 *Threads*; [Python Socket Programming HOWTO](https://docs.python.org/3/howto/sockets.html).

**Việc đầu tiên.** T01 — khởi tạo repo theo [docs/00](00-khoi-tao-repo.md). Có thể bắt tay vào T04 song song với buổi chốt đặc tả T03, vì cấu trúc khung gần như không đổi.

**Nhiệm vụ của R1** (10 việc):

#### T01 · Khởi tạo repo GitHub và bảng công việc

**Tuần 1** (26/10 – 01/11) · Bắt buộc · Tổ chức · Người làm: R1 · Phụ thuộc: không

Đẩy khung dự án lên GitHub, mời 5 thành viên, bật bảo vệ nhánh main, chạy script tạo nhãn, mốc tuần và toàn bộ issue. Đây là việc đầu tiên, mọi việc khác chờ nó.

Hoàn thành khi:

- [ ] Repo có đủ khung, CI chạy xanh trên nhánh main
- [ ] Cả 5 thành viên đã nhận lời mời vào repo
- [ ] Nhánh main được bảo vệ: bắt buộc qua PR, 1 người duyệt, CI xanh
- [ ] Chạy xong scripts/tao_issue_github.py: đủ nhãn, 5 mốc tuần và toàn bộ issue

Tài liệu: [docs/00-khoi-tao-repo.md](00-khoi-tao-repo.md)

#### T03 · Chốt đặc tả giao thức v1.0

**Tuần 1** (26/10 – 01/11) · Bắt buộc · Tài liệu · Người làm: R1 · Phụ thuộc: T02

Tổ chức buổi đọc chung docs/03 (30–45 phút), gom mọi câu hỏi và đề xuất sửa, rồi đóng băng thành v1.0. Sau mốc này mọi thay đổi giao thức phải qua PR do R1 duyệt, vì bên gửi và bên nhận do hai người khác nhau viết, chỉ khớp nhau nhờ bản đặc tả.

Hoàn thành khi:

- [ ] R2, R3, R4, R5 đã đọc và đặt câu hỏi (bình luận trên issue này)
- [ ] Mọi câu hỏi được trả lời hoặc được sửa vào đặc tả
- [ ] Đổi trạng thái đặc tả thành v1.0 và gắn tag `spec-v1.0` trên main

Tài liệu: [docs/03-dac-ta-giao-thuc.md](03-dac-ta-giao-thuc.md)

#### T04 · Cài đặt module đóng khung (framing) kèm kiểm thử

**Tuần 1** (26/10 – 01/11) · Bắt buộc · Tính năng · Người làm: R1 · Phụ thuộc: T03

Viết encode_frame, send_frame, recv_exact, read_frame trong protocol/framing.py. Bên gửi và bên nhận đều dựa vào module này, nên phải xong trong tuần 1 để R3, R4 dùng ngay đầu tuần 2.

Hoàn thành khi:

- [ ] recv_exact đọc đủ n byte kể cả khi recv() trả về từng mẩu nhỏ; ném ConnectionClosed khi đối phương đóng giữa chừng
- [ ] read_frame từ chối khung vượt giới hạn mà không đọc phần payload
- [ ] Có kiểm thử: khung rỗng, khung lớn nhất cho phép, khung bị cắt đôi, loại khung lạ
- [ ] Ví dụ hex trong docs/03 mục 5 khớp với kết quả encode_frame thật

Tài liệu: [docs/03-dac-ta-giao-thuc.md](03-dac-ta-giao-thuc.md) · TCP/IP Sockets in C# — mục 3.3 Framing and Parsing

#### T05 · Chốt API lõi và danh sách sự kiện với R2–R5

**Tuần 1** (26/10 – 01/11) · Bắt buộc · Tính năng · Người làm: R1 · Phụ thuộc: T02

Rà soát core/service.py, core/events.py, core/models.py cùng những người sẽ dùng chúng. API này là hợp đồng giữa giao diện và phần mạng: chốt sớm thì R5 làm giao diện song song được.

Hoàn thành khi:

- [ ] R5 xác nhận API đủ để làm giao diện
- [ ] R2, R3, R4 xác nhận các sự kiện đủ để báo trạng thái và tiến độ
- [ ] Thay đổi (nếu có) đã được hợp nhất và docs/02 cập nhật theo

Tài liệu: [docs/02-kien-truc.md](02-kien-truc.md)

#### T13 · Cài đặt messages.py: tạo và kiểm tra thông điệp JSON

**Tuần 2** (02/11 – 08/11) · Bắt buộc · Tính năng · Người làm: R1 · Phụ thuộc: T04

Hàm tạo và hàm kiểm tra hợp lệ cho OFFER, ACCEPT, REJECT, DONE, RESULT, CANCEL theo docs/03 mục 4.3. Làm xong trước thứ Tư vì R3 và R4 cần dùng.

Hoàn thành khi:

- [ ] validate_offer từ chối: thiếu trường, size âm, sha256 không phải 64 ký tự hex thường, JSON hỏng
- [ ] Mọi thông điệp mã hóa JSON gọn (không khoảng trắng thừa), UTF-8
- [ ] Các test do R6 viết sẵn ở T24 chạy xanh

Tài liệu: [docs/03-dac-ta-giao-thuc.md](03-dac-ta-giao-thuc.md)

#### T14 · Phiên bản đầu của lõi (service) với hàng đợi sự kiện

**Tuần 2** (02/11 – 08/11) · Bắt buộc · Tính năng · Người làm: R1 · Phụ thuộc: T05

TruyenNhanhService khởi động và dừng các thành phần, giữ danh sách lượt truyền, đẩy sự kiện vào hàng đợi. Tuần này được phép dùng thành phần giả thay cho dò tìm, gửi, nhận.

Hoàn thành khi:

- [ ] start() và stop() không treo, dừng sạch mọi luồng
- [ ] Sự kiện đi qua queue.Queue, lõi không bao giờ gọi thẳng vào giao diện
- [ ] Có kiểm thử với thành phần giả

Tài liệu: [docs/02-kien-truc.md](02-kien-truc.md) (mục 4 Mô hình luồng)

#### T25 · Ghép dò tìm, gửi, nhận vào service thật

**Tuần 3** (09/11 – 15/11) · Bắt buộc · Tính năng · Người làm: R1 · Phụ thuộc: T14, T15, T16, T19, T21

Nối các thành phần của R2, R3, R4 vào TruyenNhanhService. Đây là điểm hội tụ của dự án: làm xong là có ứng dụng chạy thật.

Hoàn thành khi:

- [ ] Hai máy bật ứng dụng tự thấy nhau và gửi file cho nhau qua service
- [ ] Dòng lệnh (T17) chuyển sang dùng service
- [ ] Giao diện thay FakeService bằng service thật mà không phải sửa gì khác

Tài liệu: [docs/02-kien-truc.md](02-kien-truc.md)

#### T33 · Nhiều lượt truyền đồng thời và rà soát luồng

**Tuần 4** (16/11 – 22/11) · Bắt buộc · Tính năng · Người làm: R1 · Phụ thuộc: T25

Bảo đảm ứng dụng chịu được nhiều việc cùng lúc và tắt sạch khi đang truyền.

Hoàn thành khi:

- [ ] Gửi 2 file tới 2 máy cùng lúc, và nhận từ 2 máy cùng lúc — đều đúng
- [ ] Không còn dữ liệu dùng chung giữa các luồng mà thiếu khóa
- [ ] stop() khi đang truyền: dừng sạch, giữ .part để truyền tiếp sau

Tài liệu: [docs/02-kien-truc.md](02-kien-truc.md) (mục 4 Mô hình luồng)

#### T34 · Đóng băng mã nguồn và phát hành bản ứng viên v1.0-rc

**Tuần 4** (16/11 – 22/11) · Bắt buộc · Tổ chức · Người làm: R1 · Phụ thuộc: T33, T30

Từ Chủ nhật tuần 4 không thêm tính năng mới, chỉ sửa lỗi. Tuần 5 dành trọn cho báo cáo và demo.

Hoàn thành khi:

- [ ] Gắn tag `v1.0-rc` trên main vào Chủ nhật cuối tuần 4
- [ ] Từ đó chỉ hợp nhất PR có nhãn `loi`
- [ ] Danh sách lỗi còn mở được phân loại: sẽ sửa, hoặc chấp nhận và ghi vào mục Hạn chế của báo cáo

Tài liệu: [docs/05-lo-trinh.md](05-lo-trinh.md)

#### T45 · Kịch bản demo, tổng duyệt và phát hành v1.0

**Tuần 5** (23/11 – 29/11) · Bắt buộc · Tổ chức · Người làm: R1 · Phụ thuộc: T34, T44

Demo trực tiếp là lúc dễ hỏng nhất. Tổng duyệt trên đúng máy và đúng mạng sẽ dùng khi thuyết trình.

Hoàn thành khi:

- [ ] Kịch bản demo từng bước, ghi rõ ai thao tác máy nào
- [ ] Tổng duyệt 2 lần trên máy thật ở trường, đã xử lý tường lửa và mạng theo kết quả T07
- [ ] Gắn tag `v1.0`, tạo GitHub Release kèm file zip mã nguồn

Tài liệu: [docs/05-lo-trinh.md](05-lo-trinh.md) (mục Demo)

### R2 — Dò tìm thiết bị (UDP) & Dòng lệnh

**Bạn làm gì.** Phần giúp các máy tự thấy nhau mà không ai phải gõ địa chỉ IP, và công cụ dòng lệnh cả nhóm dùng để thử nghiệm trước khi có giao diện. Bạn cũng là người đụng vào tường lửa và mạng WiFi trường đầu tiên — kết quả của bạn ở tuần 1 quyết định nhóm demo bằng mạng nào.

**Bạn sở hữu.** `src/truyennhanh/discovery/`, `src/truyennhanh/cli/`, `docs/huong-dan-tuong-lua.md`, `docs/huong-dan-su-dung.md`.

**Bạn cung cấp cho người khác.**
- Cho cả nhóm: hướng dẫn mở tường lửa và kết luận về WiFi trường (tuần 1)
- Cho R1: lớp `Discovery` và `PeerTable` phát sự kiện `PeerFound`, `PeerLost` (tuần 2)
- Cho cả nhóm: lệnh `scan`, `send`, `receive` để thử nghiệm (cuối tuần 2)

**Bạn cần từ người khác.** Từ R4: cổng TCP mà máy chủ nhận thực sự đang lắng nghe, để phát trong ANNOUNCE. Từ R1: API lõi để dòng lệnh chuyển sang dùng ở tuần 3.

**Đọc trước.** docs/03 mục 3; Kurose Chương 2, slide 101–104 (Socket programming with UDP); *TCP/IP Sockets in C#*, mục 2.4 *UDP Sockets* và 4.5 *Multiple Recipients* (broadcast và multicast); *Hands-On Network Programming with C# and .NET Core*, chương *The Transport Layer – TCP and UDP*, phần UDP.

**Việc đầu tiên.** T06 — gửi được một gói broadcast giữa hai laptop thật.

**Nhiệm vụ của R2** (8 việc):

#### T06 · Thử nghiệm UDP broadcast giữa hai máy thật

**Tuần 1** (26/10 – 01/11) · Bắt buộc · Nghiên cứu · Người làm: R2 · Phụ thuộc: T02

Viết một script thử nhỏ (để trong tools/thu-nghiem/, không nằm trong src/) gửi và nhận một gói broadcast giữa hai laptop. Mục tiêu là đụng sớm vào tường lửa và cấu hình mạng.

Hoàn thành khi:

- [ ] Hai máy khác nhau nhận được gói broadcast của nhau
- [ ] Viết docs/huong-dan-tuong-lua.md: cho Python đi qua tường lửa Windows, chuyển mạng sang chế độ Private
- [ ] Ghi chú: chạy hai bản trên cùng một máy cần tùy chọn socket nào (SO_REUSEADDR, SO_BROADCAST), khác nhau giữa Windows và macOS ra sao

Tài liệu: Kurose Chương 2 — slide 101–104 (Socket programming with UDP) · TCP/IP Sockets in C# — mục 2.4 UDP Sockets, 4.5 Multiple Recipients

#### T07 · Kiểm tra WiFi trường có cho các máy nói chuyện với nhau không

**Tuần 1** (26/10 – 01/11) · Bắt buộc · Nghiên cứu · Người làm: R2 · Phụ thuộc: T06

Nhiều mạng WiFi công cộng bật chế độ cách ly: máy vào được Internet nhưng không thấy nhau. Nếu WiFi phòng học như vậy thì demo trực tiếp sẽ hỏng, nên phải biết ngay từ tuần 1.

Hoàn thành khi:

- [ ] Thử tại phòng học hoặc phòng máy: hai laptop ping được nhau, nhận được broadcast của nhau, kết nối TCP được qua cổng 50506
- [ ] Ghi kết quả vào issue này: được hay không được, thử ở phòng nào, mạng nào
- [ ] Nếu không được: đề xuất phương án demo (phát WiFi từ điện thoại, mang router riêng, hoặc dùng dây mạng phòng máy) và chốt với R1

Tài liệu: [docs/01-de-cuong.md](01-de-cuong.md) (mục Rủi ro)

#### T15 · Cài đặt dò tìm: DISCOVER, ANNOUNCE, BYE

**Tuần 2** (02/11 – 08/11) · Bắt buộc · Tính năng · Người làm: R2 · Phụ thuộc: T06, T03

Lớp Discovery dùng một socket UDP duy nhất: phát ANNOUNCE mỗi 2 giây, gửi DISCOVER lúc khởi động, trả lời DISCOVER, gửi BYE khi thoát.

Hoàn thành khi:

- [ ] Bỏ qua gói của chính mình, gói sai giao thức hoặc phiên bản, JSON hỏng — không bao giờ crash vì gói lạ
- [ ] IP của máy lấy từ địa chỉ nguồn của gói tin, không lấy từ nội dung JSON
- [ ] Máy mới xuất hiện ở máy kia trong vòng 3 giây

Tài liệu: [docs/03-dac-ta-giao-thuc.md](03-dac-ta-giao-thuc.md) (mục 3)

#### T16 · Bảng thiết bị có hết hạn

**Tuần 2** (02/11 – 08/11) · Bắt buộc · Tính năng · Người làm: R2 · Phụ thuộc: T05

PeerTable thêm, cập nhật, xóa máy; máy im lặng quá 7 giây thì tự biến mất; phát sự kiện PeerFound và PeerLost cho lõi.

Hoàn thành khi:

- [ ] Có kiểm thử dùng đồng hồ giả (truyền hàm thời gian vào), không dùng sleep thật
- [ ] An toàn khi nhiều luồng cùng đọc ghi (có khóa)
- [ ] Máy thêm thủ công không bị hết hạn

Tài liệu: [docs/03-dac-ta-giao-thuc.md](03-dac-ta-giao-thuc.md) (mục 3.3)

#### T17 · Giao diện dòng lệnh tối thiểu: scan, send, receive

**Tuần 2** (02/11 – 08/11) · Bắt buộc · Tính năng · Người làm: R2 · Phụ thuộc: T19, T21

`truyennhanh scan`, `truyennhanh receive`, `truyennhanh send <ip> <file>`. Đây là công cụ để cả nhóm thử nghiệm trước khi có giao diện đồ họa, và là bằng chứng đạt mốc M2.

Hoàn thành khi:

- [ ] send gửi thẳng theo IP, không cần dò tìm
- [ ] receive in tiến độ và hỏi y/n khi có file đến (có cờ --yes để tự nhận)
- [ ] send có tùy chọn --as-name để khai một tên file tùy ý — dùng cho kiểm thử bảo mật và đoạn demo an toàn
- [ ] Cùng R3, R4 demo mốc M2 trong buổi họp Chủ nhật

Tài liệu: [README.md](../README.md) (mục Bắt đầu)

#### T29 · Thêm máy theo IP và xử lý máy nhiều card mạng

**Tuần 3** (09/11 – 15/11) · Bắt buộc · Tính năng · Người làm: R2 · Phụ thuộc: T15

Phương án dự phòng khi mạng chặn broadcast: người dùng gõ IP máy kia. Đồng thời kiểm tra trên máy có VirtualBox, VMware hoặc VPN, nơi gói broadcast dễ đi nhầm card mạng.

Hoàn thành khi:

- [ ] add_manual_peer(ip) hoạt động, máy thêm thủ công hiện trong danh sách
- [ ] Thử trên máy có card mạng ảo; ghi hiện tượng và cách xử lý vào docs/huong-dan-tuong-lua.md
- [ ] Kết quả T07 được phản ánh: nếu WiFi trường chặn broadcast thì phương án thủ công đã sẵn sàng

Tài liệu: [docs/03-dac-ta-giao-thuc.md](03-dac-ta-giao-thuc.md) (mục 3.4)

#### T41 · (Mở rộng) Trang web cho điện thoại gửi file lên máy tính

**Tuần 4** (16/11 – 22/11) · Mở rộng · Tính năng · Người làm: R2 · Phụ thuộc: T25

Chỉ làm nếu mốc M3 đạt đúng hạn. Ứng dụng mở một máy chủ HTTP nhỏ; điện thoại cùng WiFi mở trình duyệt, chọn file và tải lên. Không cần viết app điện thoại.

Hoàn thành khi:

- [ ] Điện thoại cùng mạng tải được file lên máy tính qua trình duyệt
- [ ] File đi qua cùng bước làm sạch tên và lưu trữ như bên nhận TCP
- [ ] Địa chỉ trang hiện trên giao diện để gõ vào điện thoại

Tài liệu: Kurose Chương 2 — phần HTTP

#### T46 · Hướng dẫn cài đặt và sử dụng

**Tuần 5** (23/11 – 29/11) · Bắt buộc · Tài liệu · Người làm: R2 · Phụ thuộc: T34

Tài liệu cho người dùng cuối, cũng là phụ lục của báo cáo.

Hoàn thành khi:

- [ ] docs/huong-dan-su-dung.md: cài đặt, chạy, gửi, nhận, xử lý lỗi thường gặp (tường lửa, không thấy máy)
- [ ] Một người ngoài nhóm làm theo được từ đầu đến cuối mà không cần hỏi

Tài liệu: [docs/huong-dan-tuong-lua.md](huong-dan-tuong-lua.md)

### R3 — Bên gửi (TCP client)

**Bạn làm gì.** Phía chủ động của mỗi lượt truyền: mở kết nối tới máy nhận, đề nghị gửi, đẩy dữ liệu đi theo từng khối, và tự kết nối lại khi rớt mạng mà không gửi lại phần đã tới nơi. Bạn cũng làm thí nghiệm chứng minh vì sao không dùng UDP để truyền file.

**Bạn sở hữu.** `src/truyennhanh/transfer/sender.py`, `src/truyennhanh/transfer/hashing.py`, `tools/thu_udp_thuan.py`.

**Bạn cung cấp cho người khác.**
- Cho R1: lớp `FileSender` chạy trên một luồng riêng, báo tiến độ qua hàm `emit`
- Cho R6 và báo cáo: số liệu thí nghiệm E5 (UDP thuần)

**Bạn cần từ người khác.** Từ R1: module đóng khung (cuối tuần 1) và module thông điệp (giữa tuần 2). Từ R4: bên nhận để thử cặp.

**Đọc trước.** docs/03 mục 4 — đọc **toàn bộ**, đây là việc của bạn; Kurose Chương 2, slide 105–108 (Socket programming with TCP); Kurose Chương 3, slide 24–35 (UDP) cho thí nghiệm E5; *TCP/IP Sockets in C#*, mục 5.1 *Buffering and TCP* và 5.2 *Buffer Deadlock*.

**Việc đầu tiên.** T08 — cùng R4 gửi một file qua TCP thô.

**R3 và R4 là một cặp.** Hai bạn viết hai đầu của cùng một giao thức. Thử code với nhau thường xuyên, duyệt PR của nhau, và khi thấy đặc tả mơ hồ thì cùng hỏi R1 trước khi mỗi người tự hiểu một kiểu.

**Nhiệm vụ của R3** (7 việc):

#### T08 · Thử nghiệm gửi một file qua TCP thô (làm cặp với R4)

**Tuần 1** (26/10 – 01/11) · Bắt buộc · Nghiên cứu · Người làm: R3 · Phụ thuộc: T02

R3 viết phía gửi, R4 viết phía nhận, chưa cần giao thức: mở kết nối, đổ toàn bộ file, đóng. Mục tiêu là tự thấy vì sao TCP cần đóng khung trước khi đọc đặc tả.

Hoàn thành khi:

- [ ] Gửi được file 100 MB giữa hai máy, SHA-256 hai đầu khớp
- [ ] Ghi lại quan sát: mỗi lần recv() trả về bao nhiêu byte, khác nhau thế nào giữa localhost và WiFi
- [ ] Trả lời trong issue: nếu muốn gửi kèm tên file thì bên nhận biết tên file kết thúc ở đâu?

Tài liệu: Kurose Chương 2 — slide 105–108 (Socket programming with TCP) · TCP/IP Sockets in C# — mục 2.3 TCP Sockets, 5.1 Buffering and TCP

#### T18 · Bên gửi: tính SHA-256, gửi OFFER, chờ quyết định

**Tuần 2** (02/11 – 08/11) · Bắt buộc · Tính năng · Người làm: R3 · Phụ thuộc: T04, T13

Tính mã băm toàn file trước khi gửi (mã băm là định danh của file, cần cho cả kiểm tra toàn vẹn và truyền tiếp), gửi OFFER và chờ bên nhận đồng ý hay từ chối.

Hoàn thành khi:

- [ ] Tính SHA-256 theo khối, không đọc cả file vào RAM (thử với file 1 GB)
- [ ] Chờ ACCEPT hoặc REJECT tối đa 60 giây, hết giờ thì báo lỗi timeout
- [ ] Báo trạng thái "đang tính mã băm" cho file lớn để giao diện không im lặng

Tài liệu: [docs/03-dac-ta-giao-thuc.md](03-dac-ta-giao-thuc.md) (mục 4.4)

#### T19 · Bên gửi: gửi DATA theo khối, DONE, nhận RESULT, báo tiến độ

**Tuần 2** (02/11 – 08/11) · Bắt buộc · Tính năng · Người làm: R3 · Phụ thuộc: T18

Gửi nội dung file thành các khung DATA bắt đầu từ offset bên nhận yêu cầu, kết thúc bằng DONE và chờ RESULT.

Hoàn thành khi:

- [ ] Gửi bắt đầu đúng từ offset trong ACCEPT
- [ ] Báo TransferProgress không quá 10 lần mỗi giây, để không làm ngập giao diện
- [ ] Gửi thành công toàn bộ bộ file mẫu qua localhost, SHA-256 khớp

Tài liệu: [docs/03-dac-ta-giao-thuc.md](03-dac-ta-giao-thuc.md) (mục 4.4)

#### T26 · Truyền tiếp phía gửi và tự kết nối lại

**Tuần 3** (09/11 – 15/11) · Nâng cao · Tính năng · Người làm: R3 · Phụ thuộc: T19

Khi mất kết nối giữa chừng, bên gửi tự thử lại và tiếp tục từ chỗ bên nhận đã có, thay vì gửi lại từ đầu. Đây là tính năng làm nên điểm cao của đồ án.

Hoàn thành khi:

- [ ] Nhận ACCEPT với offset = k thì gửi từ byte k; offset bằng size thì gửi DONE ngay
- [ ] Mất kết nối: thử lại sau 1, 2, 4, 8, 16 giây; hết 5 lần thì báo lỗi
- [ ] Không gửi lại byte nào bên nhận đã ghi xuống đĩa

Tài liệu: [docs/03-dac-ta-giao-thuc.md](03-dac-ta-giao-thuc.md) (mục 4.5)

#### T35 · Hủy lượt gửi và chọn kích thước khối mặc định

**Tuần 4** (16/11 – 22/11) · Bắt buộc · Tính năng · Người làm: R3 · Phụ thuộc: T26, T38

Cho phép hủy từ cả hai phía, và chọn kích thước khối mặc định bằng số liệu đo thật chứ không đoán.

Hoàn thành khi:

- [ ] CANCEL hoạt động từ cả hai phía, giao diện hai bên cập nhật đúng
- [ ] Đặt DEFAULT_CHUNK_SIZE theo kết quả thí nghiệm E1 (T38), ghi lý do vào docs/03

Tài liệu: [docs/07-ke-hoach-do-dac.md](07-ke-hoach-do-dac.md) (E1)

#### T36 · Thí nghiệm E5: gửi file bằng UDP thuần

**Tuần 4** (16/11 – 22/11) · Nâng cao · Nghiên cứu · Người làm: R3 · Phụ thuộc: T08

Viết công cụ bắn file qua UDP không có cơ chế tin cậy, đo tỷ lệ gói mất và đến sai thứ tự. Đây là lý lẽ bằng số cho việc chọn TCP để truyền file.

Hoàn thành khi:

- [ ] tools/thu_udp_thuan.py chạy được giữa hai máy
- [ ] Bảng kết quả: tốc độ bắn so với % gói mất, % sai thứ tự, file có khớp SHA-256 không
- [ ] Một đoạn phân tích nối với Kurose Chương 3: UDP không bảo đảm tin cậy

Tài liệu: [docs/07-ke-hoach-do-dac.md](07-ke-hoach-do-dac.md) (E5) · Kurose Chương 3 — slide 24–35 (UDP)

#### T47 · Sửa lỗi phát hiện khi tổng duyệt

**Tuần 5** (23/11 – 29/11) · Bắt buộc · Sửa lỗi · Người làm: R3, R4 · Phụ thuộc: T45

Lỗi lộ ra trong buổi tổng duyệt thường nằm ở phần truyền nhận, nên R3 và R4 trực sửa.

Hoàn thành khi:

- [ ] Mọi lỗi làm hỏng demo được sửa trước Thứ Bảy tuần 5
- [ ] Lỗi nhỏ còn lại được ghi vào mục Hạn chế của báo cáo

Tài liệu: [docs/08-kiem-thu.md](08-kiem-thu.md)

### R4 — Bên nhận (TCP server)

**Bạn làm gì.** Phía bị động: máy chủ lắng nghe, nhận file, xác minh, lưu trữ — và **bảo vệ máy của người dùng** khỏi dữ liệu xấu. Bên nhận ghi xuống đĩa những gì một máy lạ gửi tới, nên đây là phần nhạy cảm nhất về an toàn. Đọc kỹ docs/03 mục 4.9.

**Bạn sở hữu.** `src/truyennhanh/transfer/receiver.py`, `src/truyennhanh/transfer/storage.py`, `src/truyennhanh/transfer/filenames.py`.

**Bạn cung cấp cho người khác.**
- Cho R1: lớp `FileReceiverServer`
- Cho R2: cổng TCP thật đang lắng nghe
- Cho R6: danh sách ca nguy hiểm (T09), làm đầu vào cho kiểm thử bảo mật

**Bạn cần từ người khác.** Từ R1: module đóng khung, module thông điệp, và cơ chế hỏi người dùng qua lõi (`respond_to_offer`).

**Đọc trước.** docs/03 mục 4, đặc biệt 4.5 (truyền tiếp) và 4.9 (kiểm tra bắt buộc); *TCP/IP Sockets in C#*, mục 4.3 *Threads* và 4.6 *Closing Connections*; tài liệu Python về `os.replace`, `shutil.disk_usage`, `pathlib.Path.resolve`.

**Việc đầu tiên.** T08 cùng R3, rồi T09.

**Nhiệm vụ của R4** (8 việc):

#### T09 · Liệt kê các ca nguy hiểm phía bên nhận

**Tuần 1** (26/10 – 01/11) · Bắt buộc · Nghiên cứu · Người làm: R4 · Phụ thuộc: T03

Bên nhận ghi xuống đĩa những file do máy lạ gửi tới, đây là phần dễ bị tấn công nhất của hệ thống. Lập danh sách ca biên trước khi code. Trong tuần 1, R4 cũng cùng R3 làm T08.

Hoàn thành khi:

- [ ] Danh sách tên file độc hại: `../../x`, `C:\Windows\x`, `/etc/passwd`, `CON`, `NUL.txt`, tên rỗng, tên 300 ký tự, ký tự `<>:"|?*`, ký tự điều khiển
- [ ] Các tình huống: trùng tên, hết dung lượng, hai máy gửi cùng một file một lúc, file 0 byte, kết nối rồi im lặng, gửi byte rác
- [ ] Mỗi ca có cách xử lý mong đợi, được đưa vào docs/08 (phối hợp R6)

Tài liệu: [docs/03-dac-ta-giao-thuc.md](03-dac-ta-giao-thuc.md) (mục 4.9) · [docs/08-kiem-thu.md](08-kiem-thu.md)

#### T20 · Bên nhận: máy chủ TCP, nhận OFFER, hỏi chấp nhận

**Tuần 2** (02/11 – 08/11) · Bắt buộc · Tính năng · Người làm: R4 · Phụ thuộc: T04, T13

Máy chủ lắng nghe cổng TCP, mỗi kết nối xử lý trên một luồng riêng, đọc OFFER, hỏi người dùng qua lõi và trả lời ACCEPT hoặc REJECT.

Hoàn thành khi:

- [ ] Mỗi kết nối chạy trên luồng riêng: một máy gửi bị treo không chặn máy khác
- [ ] Nếu cổng 50506 đang bận thì để hệ điều hành chọn cổng, và báo cổng thật cho R2 phát trong ANNOUNCE
- [ ] Kết nối rồi im lặng quá 15 giây thì bị đóng

Tài liệu: [docs/03-dac-ta-giao-thuc.md](03-dac-ta-giao-thuc.md) (mục 4) · TCP/IP Sockets in C# — mục 4.3 Threads

#### T21 · Bên nhận: ghi .part, kiểm tra SHA-256, đổi tên, trả RESULT

**Tuần 2** (02/11 – 08/11) · Bắt buộc · Tính năng · Người làm: R4 · Phụ thuộc: T20

Ghi dữ liệu vào file tạm .part, khi nhận DONE thì kiểm tra mã băm, đúng thì đổi thành file thật trong thư mục nhận, sai thì xóa.

Hoàn thành khi:

- [ ] File chưa được xác minh không bao giờ xuất hiện trong thư mục nhận (chỉ nằm ở .truyennhanh/*.part)
- [ ] Trùng tên thì đặt "ten (1).ext", "ten (2).ext"
- [ ] Sai mã băm thì xóa .part và trả RESULT ok=false, reason=hash_mismatch

Tài liệu: [docs/02-kien-truc.md](02-kien-truc.md) (mục 6 Lưu trữ)

#### T22 · Làm sạch tên file, chống ghi ra ngoài thư mục nhận

**Tuần 2** (02/11 – 08/11) · Bắt buộc · Tính năng · Người làm: R4 · Phụ thuộc: T09

Tên file do máy gửi tự khai, không được tin. Hàm sanitize_filename biến mọi tên thành một tên an toàn nằm gọn trong thư mục nhận. Đây là yêu cầu bảo mật, không được cắt.

Hoàn thành khi:

- [ ] Mọi ca trong danh sách của T09 cho ra tên an toàn
- [ ] Các test do R6 viết ở T24 chạy xanh
- [ ] Tên tiếng Việt có dấu hợp lệ được giữ nguyên

Tài liệu: [docs/03-dac-ta-giao-thuc.md](03-dac-ta-giao-thuc.md) (mục 4.9)

#### T27 · Truyền tiếp phía nhận

**Tuần 3** (09/11 – 15/11) · Nâng cao · Tính năng · Người làm: R4 · Phụ thuộc: T21

Khi OFFER đến với mã băm trùng một file .part đang dở, trả ACCEPT với offset bằng kích thước phần đã nhận.

Hoàn thành khi:

- [ ] OFFER có sha256 trùng .part sẵn có → ACCEPT offset = kích thước .part
- [ ] .part lớn hơn size → xóa và nhận lại từ 0
- [ ] Mất kết nối thì giữ nguyên .part, không xóa

Tài liệu: [docs/03-dac-ta-giao-thuc.md](03-dac-ta-giao-thuc.md) (mục 4.5)

#### T28 · Khóa theo file và kiểm tra dung lượng trống

**Tuần 3** (09/11 – 15/11) · Bắt buộc · Tính năng · Người làm: R4 · Phụ thuộc: T21

Ngăn hai lượt cùng ghi vào một file .part, và từ chối sớm khi ổ đĩa không đủ chỗ.

Hoàn thành khi:

- [ ] Hai lượt có cùng sha256 đến cùng lúc → lượt sau nhận REJECT busy
- [ ] Không đủ dung lượng → REJECT insufficient_space trước khi nhận byte nào
- [ ] Có kiểm thử cho cả hai ca

Tài liệu: [docs/03-dac-ta-giao-thuc.md](03-dac-ta-giao-thuc.md) (mục 4.8)

#### T37 · Dọn .part cũ, xử lý hết dung lượng giữa chừng, sửa lỗi

**Tuần 4** (16/11 – 22/11) · Bắt buộc · Tính năng · Người làm: R4 · Phụ thuộc: T27, T32

Những tình huống chỉ lộ ra khi dùng thật lâu: rác .part tích tụ, ổ đầy giữa lúc nhận.

Hoàn thành khi:

- [ ] .part không được đụng tới quá 7 ngày bị xóa khi ứng dụng khởi động
- [ ] Hết dung lượng giữa chừng: dừng, báo lỗi rõ ràng, giữ .part
- [ ] Đóng hết các issue `loi` được giao cho R4 từ T32

Tài liệu: [docs/02-kien-truc.md](02-kien-truc.md) (mục 6 Lưu trữ)

#### T47 · Sửa lỗi phát hiện khi tổng duyệt

**Tuần 5** (23/11 – 29/11) · Bắt buộc · Sửa lỗi · Người làm: R3, R4 · Phụ thuộc: T45

Lỗi lộ ra trong buổi tổng duyệt thường nằm ở phần truyền nhận, nên R3 và R4 trực sửa.

Hoàn thành khi:

- [ ] Mọi lỗi làm hỏng demo được sửa trước Thứ Bảy tuần 5
- [ ] Lỗi nhỏ còn lại được ghi vào mục Hạn chế của báo cáo

Tài liệu: [docs/08-kiem-thu.md](08-kiem-thu.md)

### R5 — Giao diện (Tkinter)

**Bạn làm gì.** Thứ người dùng và thầy nhìn thấy. Bạn làm giao diện trên một dịch vụ giả ngay từ tuần 1 — không phải chờ ai — rồi nối vào phần mạng thật ở tuần 3. Phần khó nhất của bạn là **mô hình luồng**: giao diện phải mượt trong lúc mạng đang chạy. Cuối dự án bạn làm slide và video demo.

**Bạn sở hữu.** `src/truyennhanh/gui/`, slide thuyết trình, video demo.

**Bạn cung cấp cho người khác.** Giao diện để demo; slide và video (tuần 5).

**Bạn cần từ người khác.** Từ R1: API lõi đã chốt (cuối tuần 1) và lõi thật chạy được (giữa tuần 3).

**Đọc trước.** docs/02 mục 3 và 4 — **bắt buộc**, mô hình luồng là chỗ dễ sai nhất; tài liệu Python về `tkinter` và `queue`; *TCP/IP Sockets in C#*, mục 4.3 *Threads* (cùng một vấn đề luồng, ở ngôn ngữ khác).

**Việc đầu tiên.** T10 — phác thảo và dựng cửa sổ tĩnh.

**Cái bẫy cần biết trước.** Nếu gọi hàm gửi file ngay trong hàm xử lý nút bấm, cửa sổ sẽ đơ cứng suốt thời gian truyền: không kéo được, thanh tiến trình không nhích. Đây là lỗi rất phổ biến — ví dụ Feed-Parser trong tài liệu tham khảo của môn gọi `XDocument.Load(url)` ngay trong hàm xử lý nút bấm, nên mạng chậm là cửa sổ đứng yên. Làm đúng chỗ này và giải thích được trong báo cáo là một điểm cộng.

**Nhiệm vụ của R5** (5 việc):

#### T10 · Phác thảo giao diện và dựng cửa sổ tĩnh

**Tuần 1** (26/10 – 01/11) · Bắt buộc · Tính năng · Người làm: R5 · Phụ thuộc: T02

Vẽ phác thảo bốn vùng (danh sách máy, chọn file và gửi, tiến trình, lịch sử) và hộp thoại "Nhận file?". Dựng khung Tkinter hiển thị dữ liệu giả, chưa nối mạng.

Hoàn thành khi:

- [ ] Ảnh phác thảo lưu ở docs/hinh/
- [ ] Cửa sổ Tkinter mở được, đủ bốn vùng, co giãn được khi kéo cửa sổ
- [ ] Cả nhóm góp ý trên issue, R1 duyệt bố cục

Tài liệu: [README.md](../README.md) (mục Người dùng thấy gì)

#### T23 · Giao diện chạy với dịch vụ giả (FakeService)

**Tuần 2** (02/11 – 08/11) · Bắt buộc · Tính năng · Người làm: R5 · Phụ thuộc: T10, T05

FakeService có cùng API với service thật nhưng tự sinh sự kiện giả: máy xuất hiện, có file đến, tiến độ chạy. Làm giao diện hoàn chỉnh trên đó, không cần đợi phần mạng.

Hoàn thành khi:

- [ ] Danh sách máy cập nhật theo sự kiện; thanh tiến trình chạy mượt; hộp thoại nhận file hoạt động
- [ ] Giao diện đọc sự kiện bằng after() và queue, không gọi Tkinter từ luồng khác
- [ ] Đổi FakeService sang service thật chỉ cần sửa một dòng

Tài liệu: [docs/02-kien-truc.md](02-kien-truc.md) (mục 4 Mô hình luồng)

#### T30 · Nối giao diện với service thật, không đơ cửa sổ

**Tuần 3** (09/11 – 15/11) · Bắt buộc · Tính năng · Người làm: R5 · Phụ thuộc: T23, T25

Thay FakeService bằng service thật. Cái bẫy lớn nhất: gọi hàm mạng ngay trong sự kiện bấm nút sẽ làm cửa sổ đơ cứng suốt thời gian truyền.

Hoàn thành khi:

- [ ] Gửi file 1 GB: cửa sổ vẫn kéo được, bấm được trong suốt thời gian truyền
- [ ] Có nút Hủy; hộp thoại "Nhận file từ X?" hiện cả phần trăm sẽ tiếp tục nếu là truyền tiếp
- [ ] Lỗi hiển thị bằng câu tiếng Việt dễ hiểu, không bao giờ hiện traceback

Tài liệu: [docs/02-kien-truc.md](02-kien-truc.md) (mục 4 Mô hình luồng)

#### T40 · Hoàn thiện giao diện

**Tuần 4** (16/11 – 22/11) · Bắt buộc · Tính năng · Người làm: R5 · Phụ thuộc: T30, T29

Những thứ biến bản chạy được thành bản dùng được.

Hoàn thành khi:

- [ ] Chọn thư mục lưu; nút mở thư mục chứa file vừa nhận
- [ ] Hiện tốc độ và thời gian còn lại
- [ ] Gửi nhiều file liên tiếp bằng hàng đợi
- [ ] Ô thêm máy theo IP ngay trên giao diện

Tài liệu: [README.md](../README.md) (mục Người dùng thấy gì)

#### T44 · Slide thuyết trình và video demo dự phòng

**Tuần 5** (23/11 – 29/11) · Bắt buộc · Tài liệu · Người làm: R5 · Phụ thuộc: T34

Video là bảo hiểm: nếu WiFi phòng thuyết trình trục trặc, nhóm vẫn có demo để chiếu.

Hoàn thành khi:

- [ ] 15–20 slide: vấn đề → giải pháp → giao thức → kiến trúc → kết quả đo → demo → hạn chế
- [ ] Video 2–3 phút: gửi file giữa hai máy, kể cả cảnh rút mạng rồi truyền tiếp

Tài liệu: [docs/05-lo-trinh.md](05-lo-trinh.md) (mục Demo)

### R6 — Kiểm thử · Đo đạc · Báo cáo

**Bạn làm gì.** Người chứng minh hệ thống chạy **đúng** (bằng test tự động) và chạy **nhanh đến đâu** (bằng số liệu đo). Bạn viết test trước khi code xong để người cài đặt biết đích phải tới, dựng test tích hợp chạy trong CI, chạy các thí nghiệm, và tổng hợp báo cáo cuối kỳ.

**Bạn sở hữu.** `tests/`, `tools/` (trừ `thu_udp_thuan.py` của R3), `ket-qua/`, `docs/07-ke-hoach-do-dac.md`, `docs/08-kiem-thu.md`, `docs/bao-cao/`.

**Bạn cung cấp cho người khác.**
- Bộ file mẫu và công cụ so mã băm (tuần 1) — cả nhóm dùng suốt dự án
- Test viết trước cho đóng khung, thông điệp, tên file (đầu tuần 2)
- Test tích hợp chạy trong CI (tuần 3)
- Số liệu và biểu đồ (tuần 4), báo cáo hoàn chỉnh (tuần 5)

**Bạn cần từ người khác.** Từ R4: danh sách ca nguy hiểm (T09). Từ cả nhóm: mượn máy và có mặt để đo ở tuần 4.

**Đọc trước.** docs/07 và 08; Kurose Chương 1, slide 47–58 (độ trễ, mất gói, thông lượng) — nền tảng lý thuyết để phân tích số liệu; *Hands-On Network Programming with C# and .NET Core*, chương *Network Analysis and Packet Inspection* (Wireshark).

**Việc đầu tiên.** T11 và T12.

**Nhiệm vụ của R6** (8 việc):

#### T11 · Viết kế hoạch kiểm thử chi tiết

**Tuần 1** (26/10 – 01/11) · Bắt buộc · Tài liệu · Người làm: R6 · Phụ thuộc: T03

Hoàn thiện docs/08: danh sách ca kiểm thử có mã số, ai chạy, chạy lúc nào, kết quả mong đợi. Kế hoạch có trước thì người viết code biết mình sẽ bị kiểm tra những gì.

Hoàn thành khi:

- [ ] Mỗi yêu cầu chức năng FR trong docs/01 có ít nhất một ca kiểm thử
- [ ] Có nhóm ca bảo mật (lấy từ T09) và nhóm ca phá hoại (rút mạng, tắt tiến trình)
- [ ] Có bảng theo dõi kết quả: đạt/không đạt, ngày chạy, người chạy

Tài liệu: [docs/08-kiem-thu.md](08-kiem-thu.md)

#### T12 · Công cụ tạo bộ file mẫu và so sánh mã băm

**Tuần 1** (26/10 – 01/11) · Bắt buộc · Tính năng · Người làm: R6 · Phụ thuộc: T02

Viết tools/tao_file_mau.py tạo bộ file dùng cho kiểm thử và đo đạc, và tools/so_sanh_hash.py so hai thư mục. Cả nhóm sẽ dùng hai công cụ này suốt dự án.

Hoàn thành khi:

- [ ] Tạo được: 0 B, 1 B, 1 MB, 100 MB, 1 GB, tên tiếng Việt có dấu, tên có khoảng trắng
- [ ] Nội dung ngẫu nhiên nhưng tái lập được: cùng seed ra cùng file
- [ ] so_sanh_hash.py in rõ file nào khớp, file nào lệch, file nào thiếu
- [ ] File sinh ra nằm trong thư mục du-lieu-thu/ (đã có trong .gitignore)

Tài liệu: [tools/README.md](../tools/README.md)

#### T24 · Viết kiểm thử trước cho framing, messages, tên file

**Tuần 2** (02/11 – 08/11) · Bắt buộc · Kiểm thử · Người làm: R6 · Phụ thuộc: T03, T09

Viết test từ đặc tả trước khi phần cài đặt xong (kiểu TDD): tests/test_framing.py, test_messages.py, test_filenames.py. Người cài đặt chỉ cần làm cho test xanh.

Hoàn thành khi:

- [ ] Ba file test có mặt trên main đầu tuần 2 (được phép đỏ lúc đầu, đánh dấu xfail)
- [ ] Có ca dữ liệu rác: byte ngẫu nhiên, độ dài khung khổng lồ, JSON hỏng
- [ ] Cuối tuần 2 cả ba file chạy xanh trong CI

Tài liệu: [docs/08-kiem-thu.md](08-kiem-thu.md)

#### T31 · Kiểm thử tích hợp tự động qua localhost

**Tuần 3** (09/11 – 15/11) · Bắt buộc · Kiểm thử · Người làm: R6 · Phụ thuộc: T12, T25

Một test pytest bật bên nhận và bên gửi trên 127.0.0.1, gửi bộ file mẫu và so mã băm. Chạy trong CI để mọi PR làm hỏng việc truyền file bị phát hiện ngay.

Hoàn thành khi:

- [ ] Gửi toàn bộ bộ file mẫu (trừ file 1 GB) qua 127.0.0.1, SHA-256 khớp
- [ ] Chạy trong CI dưới 2 phút
- [ ] Dùng cổng ngẫu nhiên để không đụng ứng dụng thật đang chạy

Tài liệu: [docs/08-kiem-thu.md](08-kiem-thu.md)

#### T32 · Kiểm thử phá hoại: ngắt kết nối giữa chừng

**Tuần 3** (09/11 – 15/11) · Nâng cao · Kiểm thử · Người làm: R6 · Phụ thuộc: T26, T27

Chứng minh truyền tiếp hoạt động thật, và bên nhận không sập trước dữ liệu xấu.

Hoàn thành khi:

- [ ] Tắt WiFi hoặc tắt tiến trình nhận ở 25%, 50%, 75% rồi bật lại: file hoàn tất, SHA-256 khớp
- [ ] Ghi số byte bị gửi lại thực tế (mong đợi: không byte đã ghi nào bị gửi lại)
- [ ] Ca "kết nối rồi im lặng" và "gửi byte rác": bên nhận không sập, các lượt khác vẫn chạy
- [ ] Lỗi tìm thấy được mở thành issue có nhãn `loi` và giao đúng người

Tài liệu: [docs/08-kiem-thu.md](08-kiem-thu.md)

#### T38 · Thí nghiệm E1: kích thước khối và tốc độ (làm đầu tuần)

**Tuần 4** (16/11 – 22/11) · Bắt buộc · Kiểm thử · Người làm: R6 · Phụ thuộc: T25

Đo tốc độ truyền với các kích thước khối khác nhau. Cần xong trước thứ Tư vì R3 dùng kết quả cho T35.

Hoàn thành khi:

- [ ] Đo 4 KB, 16 KB, 64 KB, 256 KB, 1 MB; mỗi mức 5 lần; file 500 MB; cùng hai máy, cùng vị trí
- [ ] CSV lưu ở ket-qua/, biểu đồ ở docs/hinh/
- [ ] Một đoạn giải thích hình dạng đồ thị

Tài liệu: [docs/07-ke-hoach-do-dac.md](07-ke-hoach-do-dac.md) (E1)

#### T39 · Thí nghiệm E2–E4 và E6: môi trường mạng, so với Zalo/Drive/USB, truyền tiếp, dò tìm

**Tuần 4** (16/11 – 22/11) · Bắt buộc · Kiểm thử · Người làm: R6 · Phụ thuộc: T32, T38

Phần số liệu chính của báo cáo. Cần nhiều máy nên cả nhóm hỗ trợ chạy.

Hoàn thành khi:

- [ ] E2: localhost, dây mạng, WiFi 2,4 GHz, WiFi 5 GHz
- [ ] E3: cùng file 500 MB gửi bằng Truyền Nhanh, Zalo, Google Drive, USB — thời gian và file có bị nén không
- [ ] E4: cắt ở 25/50/75% — số byte tiết kiệm và thời gian khôi phục
- [ ] E6: thời gian máy xuất hiện và biến mất trong danh sách
- [ ] Mỗi thí nghiệm có CSV và biểu đồ

Tài liệu: [docs/07-ke-hoach-do-dac.md](07-ke-hoach-do-dac.md)

#### T43 · Tổng hợp báo cáo hoàn chỉnh

**Tuần 5** (23/11 – 29/11) · Bắt buộc · Tài liệu · Người làm: R6 · Phụ thuộc: T42, T38, T39

Ghép các phần thành một báo cáo thống nhất, đưa số liệu đo vào, và lập bảng đóng góp.

Hoàn thành khi:

- [ ] Đủ các chương theo dàn ý, thống nhất văn phong, hình có chú thích, có tài liệu tham khảo
- [ ] Bảng đóng góp từng thành viên, có dẫn link PR
- [ ] R1 duyệt xong trước Thứ Bảy tuần 5

Tài liệu: [docs/bao-cao/dan-y-bao-cao.md](bao-cao/dan-y-bao-cao.md)

## 7. Việc của cả nhóm

#### T02 · Cả nhóm: làm quen môi trường và quy trình Git

**Tuần 1** (26/10 – 01/11) · Bắt buộc · Tổ chức · Người làm: Cả nhóm · Phụ thuộc: T01

Mỗi người cài môi trường, đọc tài liệu nền và mở một PR nhỏ đầu tiên để quen cách nhóm làm việc trước khi đụng vào code thật.

Hoàn thành khi:

- [ ] Mỗi người: cài Python ≥ 3.10 và Git, clone repo, chạy được `pip install -e ".[dev]"` và `pytest`
- [ ] Mỗi người: đọc README, docs/01, docs/02, docs/03 và docs/06
- [ ] Mỗi người mở 1 PR điền tên và tài khoản GitHub của mình vào bảng thành viên trong README, được duyệt và hợp nhất
- [ ] Đã xong: R1 · R2 · R3 · R4 · R5 · R6 (đánh dấu từng người ở bình luận)

Tài liệu: [README.md](../README.md) · [docs/06-quy-trinh-git.md](06-quy-trinh-git.md)

#### T42 · Cả nhóm: viết phần báo cáo của module mình

**Tuần 5** (23/11 – 29/11) · Bắt buộc · Tài liệu · Người làm: Cả nhóm · Phụ thuộc: T34

Mỗi người viết phần mình phụ trách theo dàn ý. Hạn thứ Tư để R6 kịp tổng hợp.

Hoàn thành khi:

- [ ] Mỗi người nộp phần của mình theo docs/bao-cao/dan-y-bao-cao.md, hạn thứ Tư tuần 5
- [ ] Mỗi phần có: thiết kế, quyết định quan trọng và lý do, khó khăn gặp phải và cách giải quyết
- [ ] Đã xong: R1 · R2 · R3 · R4 · R5 · R6 (đánh dấu từng người ở bình luận)

Tài liệu: [docs/bao-cao/dan-y-bao-cao.md](bao-cao/dan-y-bao-cao.md)
