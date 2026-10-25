"""Tạo nhãn, 5 mốc tuần và toàn bộ issue nhiệm vụ trên GitHub — nhiệm vụ T01.

Hướng dẫn đầy đủ: docs/00-khoi-tao-repo.md (bước 6–9).

    python scripts/tao_issue_github.py                  # chạy thử: chỉ in ra, không đụng GitHub
    python scripts/tao_issue_github.py --xem T15        # xem trước nội dung một issue
    python scripts/tao_issue_github.py --chay-that      # tạo thật
    python scripts/tao_issue_github.py --tao-codeowners # ghi .github/CODEOWNERS

Cần GitHub CLI (`gh`) đã đăng nhập (`gh auth login`) khi chạy thật.
Chạy lại nhiều lần vẫn an toàn: nhãn được cập nhật, mốc và issue trùng tên được bỏ qua.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
NHIEM_VU = HERE / "nhiem_vu.json"
THANH_VIEN = HERE / "thanh_vien.json"
ALL_ROLES = ["R1", "R2", "R3", "R4", "R5", "R6"]


# --------------------------------------------------------------------------- đọc dữ liệu

def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        sys.exit(f"Không tìm thấy {path}. Chạy script từ thư mục gốc của repo.")
    except json.JSONDecodeError as e:
        sys.exit(f"{path.name} sai cú pháp JSON ở dòng {e.lineno}, cột {e.colno}: {e.msg}")


def load_members() -> tuple[dt.date, dict[str, dict]]:
    data = load_json(THANH_VIEN)
    try:
        start = dt.date.fromisoformat(data["ngay_bat_dau"])
    except (KeyError, ValueError):
        sys.exit('thanh_vien.json: "ngay_bat_dau" phải có dạng "YYYY-MM-DD", ví dụ "2026-10-26".')
    if start.weekday() != 0:
        print(f"Lưu ý: ngay_bat_dau {start:%d/%m/%Y} không phải Thứ Hai.")
    members = {}
    for m in data.get("thanh_vien", []):
        vai = m.get("vai")
        if vai not in ALL_ROLES or vai in members:
            sys.exit(f"thanh_vien.json: vai {vai!r} không hợp lệ hoặc bị lặp. Phải là R1 đến R6, mỗi vai một lần.")
        m["github"] = (m.get("github") or "").strip().lstrip("@")
        members[vai] = m
    return start, members


def week_range(start: dt.date, week: int) -> tuple[dt.date, dt.date]:
    a = start + dt.timedelta(days=7 * (week - 1))
    return a, a + dt.timedelta(days=6)


def milestone_title(week: int, info: dict) -> str:
    return f"Tuần {week} · {info['ten']}"


# --------------------------------------------------------------------------- dựng nội dung issue

def doc_link(ref: str, repo: str) -> str:
    """'docs/03-x.md (mục 3)' thành link GitHub; tên sách thì giữ nguyên."""
    head, _, rest = ref.partition(" ")
    if head.endswith(".md") and "/" in head or head == "README.md":
        url = f"https://github.com/{repo}/blob/main/{head}"
        return f"[{head}]({url})" + (f" {rest}" if rest else "")
    return ref


def issue_title(task: dict) -> str:
    return f"[{task['id']}] {task['ten']}"


def issue_labels(task: dict, data: dict) -> list[str]:
    if len(task["vai"]) == len(ALL_ROLES):
        roles = ["ca-nhom"]
    else:
        roles = [data["vai"][v]["nhan"] for v in task["vai"]]
    return roles + [task["loai"], task["uu_tien"]]


def issue_assignees(task: dict, members: dict) -> list[str]:
    return [members[v]["github"] for v in task["vai"] if v in members and members[v]["github"]]


def issue_body(task: dict, data: dict, start: dt.date, repo: str) -> str:
    tasks = {t["id"]: t for t in data["nhiem_vu"]}
    a, b = week_range(start, task["tuan"])
    if len(task["vai"]) == len(ALL_ROLES):
        who = "Cả nhóm"
    else:
        who = " + ".join(f"{v} · {data['vai'][v]['ten_vai']}" for v in task["vai"])
    lines = [
        f"> **{who}** · Tuần {task['tuan']} ({a:%d/%m} – {b:%d/%m}) · "
        f"{data['ten_uu_tien'][task['uu_tien']]} · {data['ten_loai'][task['loai']]}",
        "",
        task["mo_ta"],
        "",
        "### Hoàn thành khi",
        "",
        *[f"- [ ] {h}" for h in task["hoan_thanh"]],
        "",
        "### Phụ thuộc",
        "",
    ]
    if task["phu_thuoc"]:
        lines += [f"- **{p}** — {tasks[p]['ten']}" for p in task["phu_thuoc"]]
        lines += ["", "Tìm issue phụ thuộc bằng cách gõ mã của nó (ví dụ `T04`) vào ô tìm kiếm issue."]
    else:
        lines.append("Không có — bắt đầu được ngay.")
    if task["doc"]:
        lines += ["", "### Tài liệu", ""] + [f"- {doc_link(d, repo)}" for d in task["doc"]]
    lines += [
        "",
        "---",
        f"<sub>Tạo tự động từ `scripts/nhiem_vu.json`. Toàn bộ phân công: "
        f"[docs/04-phan-cong.md](https://github.com/{repo}/blob/main/docs/04-phan-cong.md). "
        f"Quy trình làm việc: [docs/06-quy-trinh-git.md](https://github.com/{repo}/blob/main/docs/06-quy-trinh-git.md).</sub>",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------- gọi gh

def gh(args: list[str], stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["gh", *args], input=stdin, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")


def gh_lines(args: list[str]) -> list[str]:
    r = gh(args)
    if r.returncode != 0:
        sys.exit(f"Lỗi khi chạy: gh {' '.join(args)}\n{r.stderr.strip()}")
    return [ln for ln in r.stdout.splitlines() if ln.strip()]


def resolve_repo(repo_arg: str | None) -> str:
    if repo_arg:
        return repo_arg
    r = gh(["repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"])
    if r.returncode != 0 or not r.stdout.strip():
        sys.exit("Không xác định được repo. Chạy script bên trong thư mục repo đã push lên GitHub, "
                 "hoặc thêm --repo TAI_KHOAN/truyen-nhanh.\n" + r.stderr.strip())
    return r.stdout.strip()


# --------------------------------------------------------------------------- các bước

def step_labels(data: dict, repo: str, real: bool) -> int:
    labels = [(r["nhan"], r["mau"], r["ten_vai"]) for r in data["vai"].values()]
    labels += [(x["ten"], x["mau"], x["mo_ta"]) for x in data["nhan_khac"]]
    print(f"\n== Nhãn ({len(labels)})")
    fails = 0
    for name, color, desc in labels:
        if not real:
            print(f"  [thử] {name:<16} #{color}  {desc}")
            continue
        r = gh(["label", "create", name, "-R", repo, "--color", color, "--description", desc, "--force"])
        ok = r.returncode == 0
        fails += not ok
        print(f"  {'OK ' if ok else 'LỖI'} {name}" + ("" if ok else f" — {r.stderr.strip()}"))
    return fails


def step_milestones(data: dict, start: dt.date, repo: str, real: bool) -> int:
    print("\n== Mốc tuần (5)")
    existing = set()
    if real:
        existing = set(gh_lines(["api", f"repos/{repo}/milestones?state=all",
                                 "--paginate", "--jq", ".[].title"]))
    fails = 0
    for w, info in data["tuan"].items():
        title = milestone_title(int(w), info)
        _, end = week_range(start, int(w))
        if title in existing:
            print(f"  bỏ qua  {title} (đã có)")
            continue
        if not real:
            print(f"  [thử] {title:<34} hạn {end:%d/%m/%Y}")
            continue
        # 16:59:59 UTC = 23:59:59 giờ Việt Nam, cùng một ngày ở cả hai múi giờ
        r = gh(["api", f"repos/{repo}/milestones", "-X", "POST",
                "-f", f"title={title}", "-f", f"description={info['moc']}",
                "-f", f"due_on={end.isoformat()}T16:59:59Z"])
        ok = r.returncode == 0
        fails += not ok
        print(f"  {'OK ' if ok else 'LỖI'} {title}" + ("" if ok else f" — {r.stderr.strip()}"))
    return fails


def step_issues(data: dict, members: dict, start: dt.date, repo: str,
                real: bool, pause: float) -> tuple[int, int]:
    tasks = data["nhiem_vu"]
    print(f"\n== Issue ({len(tasks)})")
    existing = set()
    if real:
        existing = set(gh_lines(["issue", "list", "-R", repo, "--state", "all",
                                 "--limit", "1000", "--json", "title", "--jq", ".[].title"]))
    created = fails = 0
    for t in tasks:
        title = issue_title(t)
        if title in existing:
            print(f"  bỏ qua  {title} (đã có)")
            continue
        labels = issue_labels(t, data)
        milestone = milestone_title(t["tuan"], data["tuan"][str(t["tuan"])])
        assignees = issue_assignees(t, members)
        if not real:
            who = ", ".join(assignees) if assignees else "(chưa điền github)"
            print(f"  [thử] {title}\n         nhãn: {', '.join(labels)} · mốc: {milestone} · giao: {who}")
            continue
        body = issue_body(t, data, start, repo)
        args = ["issue", "create", "-R", repo, "--title", title, "--body-file", "-", "--milestone", milestone]
        for lb in labels:
            args += ["--label", lb]
        r = gh(args + [x for a in assignees for x in ("--assignee", a)], stdin=body)
        if r.returncode != 0 and assignees:
            # Thường do có người chưa nhận lời mời vào repo. Tạo issue không giao,
            # rồi giao từng người một để một người lỗi không kéo theo cả nhóm.
            r = gh(args, stdin=body)
            if r.returncode == 0:
                url = r.stdout.strip()
                failed = [a for a in assignees
                          if gh(["issue", "edit", url, "-R", repo, "--add-assignee", a]).returncode != 0]
                if failed:
                    print(f"  CHÚ Ý  {title}: không giao được cho {', '.join(failed)} "
                          f"— họ đã nhận lời mời vào repo chưa?")
        if r.returncode == 0:
            created += 1
            print(f"  OK   {title}  {r.stdout.strip()}")
        else:
            fails += 1
            print(f"  LỖI  {title} — {r.stderr.strip()}")
        time.sleep(pause)   # tránh bị GitHub chặn vì tạo nội dung quá nhanh
    return created, fails


def write_codeowners(data: dict, members: dict) -> None:
    missing = [v for v in ALL_ROLES if not members.get(v, {}).get("github")]
    if missing:
        sys.exit(f"Chưa điền github cho: {', '.join(missing)} trong scripts/thanh_vien.json.")
    lines = [
        "# Sinh bởi: python scripts/tao_issue_github.py --tao-codeowners",
        "# Ai mở PR sửa file trong một thư mục thì GitHub tự mời chủ thư mục đó duyệt.",
        "# Dòng sau được ưu tiên hơn dòng trước.",
        "",
        f"*  @{members['R1']['github']}",
    ]
    for vai, info in data["vai"].items():
        for path in info["so_huu"]:
            lines.append(f"/{path}  @{members[vai]['github']}")
    out = ROOT / ".github" / "CODEOWNERS"
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Đã ghi {out.relative_to(ROOT)} ({len(lines) - 4} quy tắc). Commit file này qua một PR.")


# --------------------------------------------------------------------------- main

def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    ap = argparse.ArgumentParser(description="Tạo nhãn, mốc tuần và issue nhiệm vụ trên GitHub.")
    ap.add_argument("--chay-that", action="store_true", help="tạo thật trên GitHub (mặc định chỉ chạy thử)")
    ap.add_argument("--repo", help="TAI_KHOAN/TEN_REPO; mặc định là repo của thư mục hiện tại")
    ap.add_argument("--xem", metavar="Txx", help="in nội dung đầy đủ của một issue rồi thoát")
    ap.add_argument("--tao-codeowners", action="store_true", help="ghi .github/CODEOWNERS rồi thoát")
    ap.add_argument("--nghi", type=float, default=1.0, help="số giây nghỉ giữa hai issue (mặc định 1)")
    args = ap.parse_args(argv)

    data = load_json(NHIEM_VU)
    start, members = load_members()

    if args.tao_codeowners:
        write_codeowners(data, members)
        return 0

    if args.xem:
        task = next((t for t in data["nhiem_vu"] if t["id"].upper() == args.xem.upper()), None)
        if task is None:
            sys.exit(f"Không có nhiệm vụ {args.xem}.")
        print(issue_title(task))
        print("nhãn:", ", ".join(issue_labels(task, data)))
        print("mốc :", milestone_title(task["tuan"], data["tuan"][str(task["tuan"])]))
        print("giao:", ", ".join(issue_assignees(task, members)) or "(chưa điền github)")
        print("-" * 70)
        print(issue_body(task, data, start, args.repo or "TAI_KHOAN/truyen-nhanh"))
        return 0

    real = args.chay_that
    if real:
        if shutil.which("gh") is None:
            sys.exit("Chưa cài GitHub CLI. Xem docs/00-khoi-tao-repo.md bước 6.")
        if gh(["auth", "status"]).returncode != 0:
            sys.exit("GitHub CLI chưa đăng nhập. Chạy: gh auth login")
        repo = resolve_repo(args.repo)
    else:
        repo = args.repo or "TAI_KHOAN/truyen-nhanh"

    print(f"Repo: {repo} · Bắt đầu: {start:%d/%m/%Y} · Chế độ: {'TẠO THẬT' if real else 'CHẠY THỬ'}")
    missing = [v for v in ALL_ROLES if not members.get(v, {}).get("github")]
    if missing:
        print(f"Chưa điền github cho {', '.join(missing)}: issue của họ sẽ được tạo nhưng chưa giao.")

    fails = step_labels(data, repo, real)
    fails += step_milestones(data, start, repo, real)
    created, issue_fails = step_issues(data, members, start, repo, real, args.nghi)
    fails += issue_fails

    print()
    if not real:
        print("Đây là CHẠY THỬ, chưa có gì được tạo. Thấy ổn thì chạy lại với --chay-that")
        return 0
    print(f"Xong: tạo {created} issue, {fails} lỗi."
          + (" Chạy lại script để thử lại phần lỗi — phần đã tạo sẽ được bỏ qua." if fails else ""))
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
