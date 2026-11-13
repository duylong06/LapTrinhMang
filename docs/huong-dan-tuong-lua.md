# Hướng dẫn mở tường lửa và xử lý sự cố mạng

> **Khung — R2 viết ở nhiệm vụ T06 (tuần 1), bổ sung ở T29 (tuần 3).**

Ứng dụng cần hai cổng mở trên mỗi máy: **UDP 50505** để dò tìm, **TCP 50506** để nhận file. Tường lửa Windows mặc định chặn cả hai với chương trình mới.

## 1. Windows: cho Python đi qua tường lửa
Khi chạy chương trình Python lần đầu, Windows có thể hiển thị thông báo Windows Security Alert.

**Cách 1: Cho phép từ thông báo Windows**

1. Kiểm tra chương trình được yêu cầu cấp quyền là Python.
2. Chọn Allow access nếu đang sử dụng mạng riêng đáng tin cậy.
3. Chỉ cho phép trên Private networks.

**Cách 2: Cấp quyền thủ công**

1. Mở Windows Security.
2. Chọn Firewall & network protection.
3. Chọn Allow an app through firewall.
4. Chọn Change settings.
5. Tìm Python trong danh sách.
6. Đánh dấu quyền truy cập tại Private.
7. Nếu chưa có Python, chọn Allow another app để thêm chương trình.

**Lưu ý:** Không tắt toàn bộ Windows Firewall. Chỉ cấp quyền cần thiết cho chương trình.

## 2. Chuyển mạng sang chế độ Private
Windows phân biệt hai loại mạng:

- **Private:** Dành cho mạng riêng đáng tin cậy, chẳng hạn mạng gia đình.
- **Public:** Dành cho mạng công cộng, nơi cần hạn chế khả năng các thiết bị khác truy cập máy tính.

**Cách chuyển sang Private:**

1. Mở Settings.
2. Chọn Network & Internet.
3. Chọn Wi-Fi hoặc Ethernet đang kết nối.
4. Mở Properties.
5. Tại Network profile type, chọn Private nếu mạng đó đáng tin cậy.

Việc chuyển sang Private giúp áp dụng quy tắc tường lửa phù hợp hơn, nhưng không đảm bảo UDP Broadcast hoạt động nếu router hoặc mạng có chính sách cách ly thiết bị.

## 3. macOS và Linux
**Đối với macOS:**

- Mở System Settings.
- Chọn Network hoặc Privacy & Security, tùy phiên bản hệ điều hành.
- Kiểm tra mục Firewall trong phần Network.
- Nếu tường lửa chặn kết nối đến Python, kiểm tra và cho phép ứng dụng khi cần thiết.

**Đối với Linux:**

- Kiểm tra trạng thái tường lửa bằng lệnh `sudo ufw status`.
- Nếu sử dụng UFW, chỉ cấu hình cho phép UDP cổng 50505 và TCP cổng 50506 khi cần thiết cho ứng dụng.
- Không nên mở tất cả các cổng không cần thiết.

Cấu hình thực tế có thể khác nhau tùy phiên bản hệ điều hành và phần mềm tường lửa.
### Ghi chú về tùy chọn Socket khi kiểm thử UDP Broadcast

Trong chương trình UDP Broadcast, cần chú ý hai tùy chọn Socket:

- `SO_BROADCAST`: Bật ở socket gửi để cho phép gửi gói tin UDP đến địa chỉ Broadcast.
- `SO_REUSEADDR`: Hỗ trợ sử dụng lại địa chỉ socket trong những trường hợp hệ điều hành cho phép.

**Khi chạy hai chương trình trên cùng một máy và cùng sử dụng cổng UDP 50505:**

- Trên Windows, `SO_REUSEADDR` cho phép nhiều socket có thể bind cùng địa chỉ và cổng trong một số trường hợp, nhưng cách phân phối gói tin giữa các socket có thể không xác định.
- Trên macOS, khi nhiều socket cần bind cùng một cổng UDP, có thể cần `SO_REUSEPORT` cùng với `SO_REUSEADDR`, tùy cấu hình.
- `SO_BROADCAST` được sử dụng ở socket gửi, không thay thế cho tùy chọn bind cổng ở socket nhận.
- Cần kiểm tra kết quả thực tế trên từng hệ điều hành, không mặc định Windows và macOS có cách xử lý giống nhau.

## 4. Không thấy máy kia: kiểm tra theo thứ tự
Khi hai máy không tìm thấy nhau, thực hiện kiểm tra theo thứ tự:

1. Kiểm tra hai máy đã kết nối mạng và có địa chỉ IP hay chưa.
2. Trên Windows, sử dụng `ipconfig`; trên macOS/Linux, sử dụng `ifconfig` hoặc `ip addr` để kiểm tra địa chỉ IP.
3. Kiểm tra hai máy có cùng mạng con hay không.
4. Kiểm tra tường lửa có chặn UDP cổng 50505 hoặc TCP cổng 50506 không.
5. Kiểm tra router có bật tính năng AP Isolation hoặc Client Isolation hay không.
6. Kiểm tra chương trình đã chạy đúng chế độ gửi và nhận chưa.

Lưu ý: Ping không thành công chưa đủ để kết luận hai máy không thể giao tiếp vì ICMP có thể bị chặn riêng.

## 5. Máy có card mạng ảo (VirtualBox, VMware, VPN)

Máy tính có thể có nhiều card mạng như Wi-Fi, Ethernet, VirtualBox, VMware hoặc VPN.

Khi đó, chương trình có thể sử dụng nhầm giao diện mạng.

Cách kiểm tra:

1. Xem danh sách card mạng bằng `ipconfig` hoặc `ip addr`.
2. Xác định card mạng đang kết nối Internet hoặc mạng LAN cần sử dụng.
3. Kiểm tra địa chỉ IP và cấu hình broadcast của card mạng đó.
4. Kiểm tra cấu hình VPN hoặc card mạng ảo nếu chương trình không tìm thấy thiết bị khác.

Nên ưu tiên kiểm tra trên card mạng thực tế đang sử dụng.<img width="1558" height="768" alt="image" src="https://github.com/user-attachments/assets/f5c70147-e4a1-4a96-876d-f27bc9b6cf11" />


## 6. Kết quả kiểm tra WiFi trường
### 6.1. Thông tin thử nghiệm

- Thời gian: 07/11/2026.
- Số thiết bị: 2 máy tính.
- IP máy thứ nhất: `10.67.92.75`.
- IP máy thứ hai: `10.177.112.90`.

### 6.2. Kết quả thử nghiệm

Qua kết quả nhóm ghi nhận, hai máy tính không thể kết nối như mong muốn và xuất hiện lỗi `WinError 10060`.

Hai địa chỉ IP thuộc các mạng con khác nhau, do đó cần xem xét cấu hình mạng và chính sách kết nối của hệ thống Wi-Fi trường.

### 6.3. Phương án thay thế

Trong trường hợp mạng Wi-Fi trường không đáp ứng yêu cầu giao tiếp giữa các thiết bị, nhóm đề xuất sử dụng:

- Mobile Hotspot (điểm phát sóng điện thoại).
- Router Wi-Fi riêng.
- Mạng LAN có dây.

### 6.4. Kết luận

Kết quả thử nghiệm cho thấy việc giao tiếp giữa hai máy trong môi trường mạng đã kiểm tra chưa thành công. Nhóm cần sử dụng mạng thay thế để tiếp tục kiểm thử chức năng dò tìm thiết bị của ứng dụng Truyền Nhanh.
