
import socket
import sys

PORT = 37020
BUFFER_SIZE = 2048


def listen():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", PORT))
        print(f"Đang chờ UDP trên cổng {PORT}...")

        while True:
            data, address = sock.recvfrom(BUFFER_SIZE)
            message = data.decode("utf-8", errors="replace")
            print(f"Nhận từ {address[0]}: {message}")


def send():
    message = input("Nhập thông điệp: ").encode("utf-8")

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(message, ("255.255.255.255", PORT))

    print("Đã gửi broadcast.")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("listen", "send"):
        print("Cách dùng:")
        print("  python udp_broadcast.py listen")
        print("  python udp_broadcast.py send")
        sys.exit(1)

    listen() if sys.argv[1] == "listen" else send()
