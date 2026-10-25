# Khởi tạo repo trên GitHub

Hướng dẫn cho **R1 (trưởng nhóm)**, làm một lần duy nhất ở đầu tuần 1 — nhiệm vụ **T01**. Mất khoảng 20–30 phút. Các lệnh viết cho PowerShell trên Windows; macOS và Linux gõ y hệt, trừ chỗ có ghi chú.

## 1. Tạo repo rỗng trên GitHub

Vào GitHub → **New repository**:

- **Repository name:** `LapTrinhMang`
- **Public** hay **Private:** xem lưu ý ở bước 5 trước khi chọn
- **Không** tích *Add a README*, *.gitignore* hay *license* — repo phải hoàn toàn rỗng, vì dự án đã có sẵn các file này

## 2. Đẩy khung dự án lên

Giải nén file zip, mở terminal **bên trong** thư mục `truyen-nhanh`:

```powershell
git init
git branch -M main
git add .
git commit -m "Khởi tạo khung dự án Truyền Nhanh"
git remote add origin https://github.com/<tai-khoan-cua-ban>/truyen-nhanh.git
git push -u origin main
```

Nếu Git báo chưa biết bạn là ai, chạy hai lệnh này một lần rồi commit lại:

```powershell
git config --global user.name "Nguyễn Duy Long"
git config --global user.email "email-dung-cho-github@example.com"
```

## 3. Kiểm tra CI

Mở tab **Actions** trên GitHub. Workflow **CI** phải chạy và hiện dấu tích xanh cho cả hai hệ điều hành (Ubuntu và Windows). CI làm ba việc: cài dự án, kiểm tra cú pháp toàn bộ code, chạy `pytest`.

Nếu đỏ: bấm vào để xem log. Lúc mới khởi tạo, nguyên nhân gần như luôn là đẩy thiếu file.

## 4. Mời thành viên

**Settings → Collaborators → Add people**, nhập tài khoản GitHub của 5 người còn lại. Mỗi người phải vào email bấm chấp nhận lời mời.

## 5. Bảo vệ nhánh `main`

Mục đích: không ai đẩy thẳng lên `main` được, mọi thay đổi phải qua Pull Request có người duyệt và CI xanh. Đây là thứ giữ cho code chung không bị một người lỡ tay làm hỏng.

> **Lưu ý quan trọng:** GitHub chỉ cho bật bảo vệ nhánh trên repo **private** khi tài khoản có gói trả phí. Với tài khoản miễn phí, chọn một trong ba cách:
>
> 1. **Đăng ký GitHub Education** (miễn phí cho sinh viên, có kèm GitHub Pro) — tốt nhất, nhưng xét duyệt có thể mất vài ngày.
> 2. **Để repo public** — bật bảo vệ được ngay. Phù hợp nếu thầy không cấm công khai mã nguồn.
> 3. **Không bật bảo vệ**, cả nhóm tự giữ quy tắc "không đẩy thẳng lên main". Kém an toàn nhất.

Khi bật được: **Settings → Branches → Add classic branch protection rule**

- **Branch name pattern:** `main`
- Tích **Require a pull request before merging** → **Require approvals: 1**
- Tích **Require status checks to pass before merging** → tìm và chọn hai mục `test (ubuntu-latest)` và `test (windows-latest)` (chỉ hiện sau khi CI đã chạy ít nhất một lần ở bước 3)
- Bấm **Create**

## 6. Cài GitHub CLI và đăng nhập

Script tạo issue dùng công cụ dòng lệnh `gh` của GitHub.

```powershell
winget install --id GitHub.cli        # Windows
# brew install gh                     # macOS
```

Mở **terminal mới** (để nhận PATH mới), rồi:

```powershell
gh auth login
```

Chọn *GitHub.com* → *HTTPS* → *Login with a web browser*, làm theo hướng dẫn. Kiểm tra bằng `gh auth status`.

## 7. Điền danh sách thành viên

Mở `scripts/thanh_vien.json`, điền tên và **tài khoản GitHub** của từng vai:

```json
{ "vai": "R2", "ten": "Trần Văn A", "github": "tranvana" }
```

- Ô `github` để trống thì issue vẫn được tạo, chỉ là chưa giao cho ai — có thể giao tay sau.
- Tài khoản phải **đã nhận lời mời** ở bước 4, nếu không GitHub từ chối giao việc (script sẽ tự tạo issue không giao và báo lại).
- Nếu nhóm bắt đầu muộn hơn 26/10, sửa `ngay_bat_dau` — hạn của 5 mốc tuần sẽ tự dời theo.

## 8. Tạo nhãn, mốc tuần và issue

Chạy thử trước — lệnh này **chỉ in ra** những gì sẽ làm, không đụng vào GitHub:

```powershell
python scripts/tao_issue_github.py
```

Đọc lướt, thấy ổn thì chạy thật:

```powershell
python scripts/tao_issue_github.py --chay-that
```

Script sẽ tạo:

- **Nhãn** cho 6 vai, loại việc (`tinh-nang`, `nghien-cuu`, `kiem-thu`...) và mức ưu tiên (`bat-buoc`, `nang-cao`, `mo-rong`)
- **5 mốc** (milestone) tương ứng 5 tuần, có hạn chót
- **47 issue** — mỗi nhiệm vụ một issue, có mô tả, tiêu chí hoàn thành, phụ thuộc, tài liệu liên quan, được giao đúng người và gắn đúng tuần

Script **chạy lại nhiều lần vẫn an toàn**: nhãn đã có thì cập nhật, mốc và issue đã có (trùng tên) thì bỏ qua. Lỡ dừng giữa chừng thì cứ chạy lại.

Mất khoảng 1–2 phút vì script cố ý nghỉ một chút giữa các issue để GitHub không chặn vì tạo quá nhanh.

## 9. Tự động gán người duyệt (tùy chọn, nên làm)

Sau khi đã điền đủ tài khoản GitHub ở bước 7:

```powershell
python scripts/tao_issue_github.py --tao-codeowners
```

Lệnh này ghi file `.github/CODEOWNERS`: ai mở PR sửa file của module nào, GitHub tự mời chủ module đó vào duyệt. Commit file này qua một PR như mọi thay đổi khác.

## 10. Hoàn tất

- Ghim issue **T02** (mở issue → **Pin issue**) để ai vào repo cũng thấy việc đầu tiên phải làm.
- Gửi link repo vào nhóm chat, nhắc mọi người làm T02 trước buổi họp Chủ nhật đầu tiên.
- (Tùy chọn) Tạo bảng Kanban: tab **Projects → New project → Board**, thêm các issue vào, nhóm theo **Milestone** để mỗi tuần là một cột nhìn tiến độ.
