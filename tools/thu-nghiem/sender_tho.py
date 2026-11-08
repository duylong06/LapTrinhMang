import socket
import os

def send_file_raw(filepath, server_ip, server_port=50506):
    file_size = os.path.getsize(filepath)
    print(f"Chuẩn bị gửi file {filepath} ({file_size} byte)")
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        print(f"Đang kết nối tới {server_ip}:{server_port}...")
        s.connect((server_ip, server_port))
        print("Đã kết nối! Bắt đầu đổ dữ liệu...")
        
        with open(filepath, 'rb') as f:
            # Đọc và gửi từng khối 64KB
            while chunk := f.read(65536):
                s.sendall(chunk)
                
        print("Đã gửi xong toàn bộ file và đóng kết nối.")

if __name__ == "__main__":
    # Thay bằng file 100MB được tạo từ tools/tao_file_mau.py của R6
    send_file_raw(r"C:\Users\VoMenh\LapTrinhMang\du-lieu-thu\du_lieu_100MB.bin", "127.0.0.1")