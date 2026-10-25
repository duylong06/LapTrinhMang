# Quy trình Git và GitHub

Viết cho cả người chưa từng dùng Pull Request. Làm đúng các bước dưới đây là đủ, không cần biết thêm gì về Git.

## 1. Ba quy tắc

1. **Không ai đẩy thẳng lên `main`.** `main` luôn phải chạy được. Mọi thay đổi đi qua Pull Request (PR).
2. **Một nhiệm vụ, một nhánh, một PR.** PR nhỏ thì duyệt nhanh, ít xung đột, dễ quay lại khi hỏng.
3. **Mọi thứ gắn với mã nhiệm vụ** `Txx`: tên nhánh, commit, tiêu đề PR.

## 2. Vòng đời một nhiệm vụ

```
Nhận issue ──► Tạo nhánh ──► Code + test ──► Commit ──► Push ──► Mở PR
                                                                   │
  Đóng issue ◄── Hợp nhất ◄── CI xanh + 1 người duyệt ◄────────────┘
  (tự động)    (Squash and merge)
```

### Bước 1 — Nhận việc

Mở issue của bạn trên GitHub, kéo trạng thái sang *đang làm* nếu nhóm dùng bảng Project, và đọc kỹ phần **Hoàn thành khi**. Đó là định nghĩa "xong" — PR sẽ được duyệt dựa trên danh sách đó.

### Bước 2 — Tạo nhánh từ `main` mới nhất

```bash
git switch main
git pull
git switch -c T15-phat-announce
```

Tên nhánh: `Txx-mo-ta-ngan`, chữ thường không dấu, nối bằng gạch ngang.

### Bước 3 — Code, chạy test, commit

```bash
pytest                       # luôn chạy trước khi commit
git add src/truyennhanh/discovery/discovery.py tests/test_discovery.py
git commit -m "[T15] Thêm vòng lặp phát ANNOUNCE mỗi 2 giây"
```

**Lời nhắn commit:** bắt đầu bằng `[Txx]`, rồi một câu tiếng Việt nói **đã làm gì**, viết như mệnh lệnh: "Thêm...", "Sửa...", "Bỏ...". Không viết "update", "fix bug", "abc".

Commit nhiều lần nhỏ trong lúc làm cũng được — khi hợp nhất, GitHub gộp hết thành một commit.

### Bước 4 — Đẩy lên và mở PR

```bash
git push -u origin T15-phat-announce
```

GitHub hiện nút **Compare & pull request**. Bấm vào, điền mẫu có sẵn:

- **Tiêu đề:** `[T15] Cài đặt dò tìm: DISCOVER, ANNOUNCE, BYE`
- Trong phần mô tả ghi **`Closes #<số issue>`** — PR được hợp nhất thì issue tự đóng
- Ghi **cách bạn đã kiểm tra**: lệnh gì, trên máy nào, thấy gì
- Chọn người duyệt theo bảng ở [docs/04](04-phan-cong.md) mục 4

### Bước 5 — Được duyệt và hợp nhất

- Người duyệt để lại bình luận. Sửa theo góp ý, commit, push lại lên **cùng nhánh** — PR tự cập nhật.
- Khi có **1 duyệt** và **CI xanh**, bấm **Squash and merge**, rồi **Delete branch**.

### Bước 6 — Dọn dẹp

```bash
git switch main
git pull
git branch -d T15-phat-announce
```

## 3. Giữ nhánh của mình cập nhật

Làm mỗi ngày, hoặc khi PR báo *This branch has conflicts*:

```bash
git switch main
git pull
git switch T15-phat-announce
git merge main
```

### Khi bị xung đột

Git báo `CONFLICT` và đánh dấu trong file:

```
<<<<<<< HEAD
dòng code của bạn
=======
dòng code từ main
>>>>>>> main
```

1. Mở file, giữ lại phần đúng (có khi là cả hai), **xóa ba dòng đánh dấu**.
2. Chạy `pytest`.
3. `git add <file>` rồi `git commit` (không cần lời nhắn, Git tự điền).

Không chắc nên giữ phần nào thì **hỏi người viết đoạn code kia** trước khi xóa. Đừng bao giờ xóa code của người khác chỉ để hết xung đột.

## 4. Duyệt PR của người khác

Người duyệt không chỉ bấm nút. Kiểm tra theo thứ tự:

1. **Đúng việc chưa?** Đối chiếu từng mục *Hoàn thành khi* trong issue.
2. **Đúng hợp đồng chưa?** Code giao thức khớp [docs/03](03-dac-ta-giao-thuc.md) đến từng byte; code dùng lõi khớp API ở [docs/02](02-kien-truc.md).
3. **Có test chưa?** Tính năng mới phải có test, sửa lỗi phải có test tái hiện lỗi đó.
4. **Đọc hiểu được không?** Tên rõ nghĩa, hàm public có docstring tiếng Việt, không có code chết hay đoạn `print` gỡ lỗi bỏ quên.
5. **Có tự tay chạy thử không?** Với phần mạng, kéo nhánh về chạy thử giữa hai máy nếu được.

Góp ý cụ thể và lịch sự: *"Chỗ này nếu `recv` trả về 0 byte thì vòng lặp chạy mãi — nên ném `ConnectionClosed`"* thay vì *"sai rồi"*.

- **Approve** — đạt, hợp nhất được
- **Request changes** — có lỗi phải sửa trước khi hợp nhất
- **Comment** — hỏi hoặc gợi ý, không chặn

## 5. Không bao giờ commit

| Thứ | Vì sao |
|---|---|
| File thử nghiệm lớn (`du-lieu-thu/`), file `.part` | Làm phình repo vĩnh viễn, kể cả khi xóa sau đó |
| Thư mục `.venv/`, `__pycache__/` | Mỗi máy tự sinh |
| Mật khẩu, token, file `.env` | Đã lên GitHub là coi như lộ |
| File cấu hình riêng của trình soạn thảo | Mỗi người dùng một trình khác nhau |

`.gitignore` đã chặn sẵn hầu hết những thứ này. Trước khi commit, chạy `git status` xem mình sắp commit gì.

## 6. Quy ước viết code

- Theo **PEP 8**. Thụt lề 4 dấu cách.
- **Tên hàm, biến, lớp bằng tiếng Anh**: `recv_exact`, `PeerTable`, `transfer_id`. Khớp với tên trong giáo trình và tài liệu Python.
- **Chú thích và docstring bằng tiếng Việt**: giải thích *vì sao*, không lặp lại code làm *gì*.
- Mỗi hàm và lớp public có **docstring** và **gợi ý kiểu** (type hint).
- Không bắt `except Exception: pass`. Bắt đúng loại lỗi và xử lý, hoặc để nó nổi lên.
- Mỗi socket mở ra phải được đóng: dùng `with socket.socket(...) as s:` hoặc `try/finally`.

## 7. Báo lỗi

Thấy lỗi ở module người khác: mở issue mới bằng mẫu **Báo lỗi**, ghi các bước tái hiện, gắn nhãn `loi` và nhãn vai của chủ module. Đừng tự sửa file của người khác — trừ khi đã hỏi và họ đồng ý.

## 8. Khi lỡ tay

| Tình huống | Lệnh |
|---|---|
| Sửa nhầm file, muốn bỏ thay đổi chưa commit | `git restore <file>` |
| Lỡ `git add` một file | `git restore --staged <file>` |
| Viết sai lời nhắn commit cuối (chưa push) | `git commit --amend` |
| Lỡ commit vào `main` trên máy (chưa push) | `git branch T15-ten-nhanh` rồi `git reset --hard origin/main`, sau đó `git switch T15-ten-nhanh` |
| Mọi thứ rối tung | Dừng lại, nhắn R1. Đừng chạy lệnh có chữ `--force` |
