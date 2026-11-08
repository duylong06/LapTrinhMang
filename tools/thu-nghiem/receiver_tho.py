import socket

def receive_file_raw(save_path, listen_port=50506):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('0.0.0.0', listen_port))
        s.listen(1)
        print(f"Đang lắng nghe TCP trên cổng {listen_port}...")
        
        conn, addr = s.accept()
        with conn:
            print(f"Chấp nhận kết nối từ {addr}")
            
            with open(save_path, 'wb') as f:
                while True:
                    data = conn.recv(65536)
                    if not data:
                        break # Đối phương đã đóng kết nối
                    print(f"Hàm recv() vừa trả về {len(data)} byte")
                    f.write(data)
                    
            print(f"Đã nhận và lưu file tại {save_path}.")

if __name__ == "__main__":
    receive_file_raw("du-lieu-thu/100MB_nhan.bin")