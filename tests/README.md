# Kiểm thử tự động

Người giữ: **R6**. Kế hoạch đầy đủ ở [docs/08-kiem-thu.md](../docs/08-kiem-thu.md).

```bash
pytest                    # chạy hết
pytest tests/test_framing.py -v
pytest -m "not cham"      # bỏ qua test chậm
```

## Hiện có

| File | Kiểm tra |
|---|---|
| `test_khung_du_an.py` | Mọi module import được; hằng số khớp đặc tả docs/03. Không được xóa |

## Sẽ thêm

| File | Nhiệm vụ | Người viết | Ca kiểm thử |
|---|---|---|---|
| `test_framing.py` | T24 | R6 (viết trước), R1 làm cho xanh | KT-01 → KT-04 |
| `test_messages.py` | T24 | R6, R1 | KT-05 |
| `test_filenames.py` | T24 | R6, R4 | KT-06, KT-07 |
| `test_peer_table.py` | T16 | R2 | KT-08 |
| `test_discovery_messages.py` | T15 | R2 | KT-09 |
| `test_storage.py` | T21 | R4 | KT-10 |
| `test_hashing.py` | T18 | R3 | KT-11 |
| `test_tich_hop.py` | T31 | R6 | KT-12 → KT-19 |

## Quy ước

- Tên hàm test bằng tiếng Anh, mô tả hành vi: `test_recv_exact_joins_partial_reads`.
- Test đơn vị không mở socket thật, không `sleep` thật — dùng đối tượng giả.
- Test tích hợp dùng cổng `0` để hệ điều hành chọn cổng trống.
- Test viết trước khi code xong: `@pytest.mark.xfail(reason="chờ T13")`, bỏ dấu khi code xong.
- Test chạy quá 10 giây: `@pytest.mark.cham`.
