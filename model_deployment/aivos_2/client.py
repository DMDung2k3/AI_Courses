import requests
import socketio
import time
import json
from datetime import datetime
import sys
import os

class FaceDetectionClient:
    def __init__(self, server_url="http://localhost:8080"):
        self.server_url = server_url
        self.sio = socketio.Client(reconnection=True, reconnection_attempts=5, reconnection_delay=2)
        self.connected = False
        self.setup_socket_events()
        
    def setup_socket_events(self):
        """Thiết lập các event handlers cho WebSocket"""
        
        @self.sio.event
        def connect():
            self.connected = True
            print("✅ Đã kết nối tới Face Detection Server")
            print(f"📡 Server: {self.server_url}")
            
        @self.sio.event
        def disconnect():
            self.connected = False
            print("❌ Mất kết nối tới Face Detection Server")
            
        @self.sio.event
        def face_detected(data):
            """Xử lý khi có khuôn mặt được phát hiện"""
            print(f"\n🎯 PHÁT HIỆN KHUÔN MẶT!")
            print(f"   ⏰ Thời gian: {data['timestamp']}")
            print(f"   👥 Số khuôn mặt: {data['faces_count']}")
            
            # Hiển thị vị trí các khuôn mặt
            for i, face in enumerate(data['faces'], 1):
                print(f"   👤 Khuôn mặt {i}: x={face['x']}, y={face['y']}, w={face['width']}, h={face['height']}")
            
            # Xử lý logic của bạn ở đây
            self.handle_face_detection_event(data)
            
        @self.sio.event
        def connect_error(data):
            print(f"❌ Lỗi kết nối WebSocket: {data}")
            
        @self.sio.event
        def reconnect():
            print("🔄 Đang thử kết nối lại...")
            
        @self.sio.event
        def reconnect_error(data):
            print(f"❌ Lỗi kết nối lại: {data}")
    
    def check_server_availability(self):
        """Kiểm tra xem server có đang chạy không"""
        try:
            response = requests.get(f"{self.server_url}/status", timeout=5)
            if response.status_code == 200:
                print("✅ Server đang hoạt động")
                return True
            else:
                print(f"⚠️ Server phản hồi với status code: {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            print("❌ Không thể kết nối tới server")
            print("💡 Hãy đảm bảo Face Detection Server đang chạy")
            return False
        except requests.exceptions.Timeout:
            print("⏱️ Timeout khi kết nối tới server")
            return False
        except Exception as e:
            print(f"❌ Lỗi không xác định: {e}")
            return False
    
    def find_server_port(self, base_port=8080, max_attempts=10):
        """Tìm port mà server đang chạy"""
        print(f"🔍 Đang tìm server port từ {base_port}...")
        
        for port in range(base_port, base_port + max_attempts):
            test_url = f"http://localhost:{port}"
            try:
                response = requests.get(f"{test_url}/status", timeout=2)
                if response.status_code == 200:
                    print(f"✅ Tìm thấy server tại port {port}")
                    self.server_url = test_url
                    return True
            except:
                continue
                
        print(f"❌ Không tìm thấy server trên các port {base_port}-{base_port + max_attempts - 1}")
        return False
    
    def connect_to_server(self):
        """Kết nối tới Face Detection Server"""
        # Kiểm tra server trước
        if not self.check_server_availability():
            # Thử tìm server trên các port khác
            if not self.find_server_port():
                return False
        
        try:
            print(f"🔗 Đang kết nối WebSocket tới {self.server_url}...")
            self.sio.connect(self.server_url, wait_timeout=10)
            return True
        except socketio.exceptions.ConnectionError as e:
            print(f"❌ Lỗi kết nối WebSocket: {e}")
            return False
        except Exception as e:
            print(f"❌ Lỗi không xác định khi kết nối: {e}")
            return False
    
    def disconnect_from_server(self):
        """Ngắt kết nối"""
        if self.connected:
            self.sio.disconnect()
            print("🔌 Đã ngắt kết nối")
    
    def start_detection(self):
        """Bắt đầu nhận diện khuôn mặt"""
        try:
            print("🚀 Đang bắt đầu nhận diện...")
            response = requests.post(f"{self.server_url}/start", timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ {result.get('message', 'Đã bắt đầu nhận diện')}")
                return result
            else:
                print(f"❌ Server trả về lỗi: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Lỗi: {error_data.get('message', 'Unknown error')}")
                except:
                    print(f"   Response: {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            print("⏱️ Timeout khi bắt đầu nhận diện")
            return None
        except Exception as e:
            print(f"❌ Lỗi start detection: {e}")
            return None
    
    def stop_detection(self):
        """Dừng nhận diện khuôn mặt"""
        try:
            print("⏹️ Đang dừng nhận diện...")
            response = requests.post(f"{self.server_url}/stop", timeout=5)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ {result.get('message', 'Đã dừng nhận diện')}")
                return result
            else:
                print(f"❌ Lỗi khi dừng: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Lỗi stop detection: {e}")
            return None
    
    def get_status(self):
        """Lấy trạng thái server"""
        try:
            response = requests.get(f"{self.server_url}/status", timeout=5)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Lỗi get status: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Lỗi get status: {e}")
            return None
    
    def get_events(self, limit=10):
        """Lấy danh sách events gần nhất"""
        try:
            response = requests.get(f"{self.server_url}/events?limit={limit}", timeout=5)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Lỗi get events: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Lỗi get events: {e}")
            return None
    
    def get_latest_detection(self):
        """Lấy detection mới nhất"""
        try:
            response = requests.get(f"{self.server_url}/latest_detection", timeout=5)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Lỗi get latest: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Lỗi get latest detection: {e}")
            return None
    
    def handle_face_detection_event(self, data):
        """Xử lý event khi phát hiện khuôn mặt - Customize logic ở đây"""
        
        # Tạo log entry
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'event': 'face_detected',
            'server_timestamp': data['timestamp'],
            'faces_count': data['faces_count'],
            'faces': data['faces']
        }
        
        # Lưu vào file log
        try:
            log_file = 'face_detection_log.json'
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
            print(f"   📝 Đã lưu log vào {log_file}")
        except Exception as e:
            print(f"   ❌ Lỗi lưu log: {e}")
        
        # Có thể thêm các xử lý khác ở đây:
        # - Gửi email/SMS thông báo
        # - Lưu vào database
        # - Gửi webhook
        # - Chụp ảnh từ camera khác
        # - Kích hoạt báo động
        
        print("   🔔 Đã xử lý event thành công")

def show_help():
    """Hiển thị hướng dẫn sử dụng"""
    print("\n📋 HƯỚNG DẪN SỬ DỤNG:")
    print("   start     - Bắt đầu nhận diện khuôn mặt")
    print("   stop      - Dừng nhận diện khuôn mặt")
    print("   status    - Kiểm tra trạng thái server")
    print("   events    - Xem 5 events gần nhất")
    print("   events 20 - Xem 20 events gần nhất")
    print("   latest    - Xem detection mới nhất")
    print("   reconnect - Kết nối lại WebSocket")
    print("   help      - Hiển thị hướng dẫn này")
    print("   quit/exit - Thoát chương trình")

def main():
    print("🎯 Face Detection Client")
    print("=" * 50)
    
    # Kiểm tra tham số dòng lệnh
    server_url = "http://localhost:8080"
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
        server_url = f"http://localhost:{port}"
        print(f"📡 Sử dụng server URL: {server_url}")
    
    # Khởi tạo client
    client = FaceDetectionClient(server_url)
    
    # Kết nối tới server
    print(f"\n🔗 Đang kết nối tới {server_url}...")
    if not client.connect_to_server():
        print("\n💡 TROUBLESHOOTING:")
        print("1. Đảm bảo Face Detection Server đang chạy")
        print("2. Kiểm tra port server (có thể không phải 8080)")
        print("3. Thử chạy: python client_example.py <port_number>")
        print("4. Kiểm tra Windows Firewall")
        print("5. Thử chạy server trước, sau đó chạy client")
        return
    
    show_help()
    
    # Auto-start detection
    print(f"\n🚀 Tự động bắt đầu nhận diện...")
    client.start_detection()
    
    try:
        while True:
            try:
                command_input = input(f"\n{'🟢' if client.connected else '🔴'} > ").strip()
                
                if not command_input:
                    continue
                    
                parts = command_input.split()
                command = parts[0].lower()
                
                if command in ['start', 's']:
                    client.start_detection()
                    
                elif command in ['stop', 'st']:
                    client.stop_detection()
                    
                elif command in ['status', 'stat']:
                    status = client.get_status()
                    if status:
                        print(f"\n📊 TRẠNG THÁI SERVER:")
                        print(f"   🏃 Running: {'✅ Có' if status.get('is_running', False) else '❌ Không'}")
                        print(f"   📊 Total events: {status.get('total_events', 0)}")
                        print(f"   📹 Camera: {'✅ OK' if status.get('camera_available', False) else '❌ Lỗi'}")
                        print(f"   🔗 WebSocket: {'✅ Kết nối' if client.connected else '❌ Mất kết nối'}")
                        
                        if status.get('last_detection'):
                            print(f"   🕐 Last detection: {status['last_detection']['timestamp']}")
                        else:
                            print(f"   🕐 Last detection: Chưa có")
                    
                elif command in ['events', 'e']:
                    limit = int(parts[1]) if len(parts) > 1 else 5
                    events = client.get_events(limit)
                    if events and events.get('events'):
                        print(f"\n📋 {len(events['events'])} EVENTS GÀN NHẤT:")
                        for i, event in enumerate(reversed(events['events']), 1):
                            print(f"   {i:2d}. {event['timestamp']}: {event['faces_count']} khuôn mặt")
                    else:
                        print("📭 Chưa có events nào")
                        
                elif command in ['latest', 'l']:
                    latest = client.get_latest_detection()
                    if latest and latest.get('detection'):
                        detection = latest['detection']
                        print(f"\n🔍 DETECTION MỚI NHẤT:")
                        print(f"   ⏰ Thời gian: {detection['timestamp']}")
                        print(f"   👥 Số khuôn mặt: {detection['faces_count']}")
                        for i, face in enumerate(detection['faces'], 1):
                            print(f"   👤 Face {i}: ({face['x']}, {face['y']}) - {face['width']}x{face['height']}")
                    else:
                        print("📭 Chưa có detection nào")
                        
                elif command in ['reconnect', 'r']:
                    print("🔄 Đang kết nối lại...")
                    client.disconnect_from_server()
                    time.sleep(1)
                    if client.connect_to_server():
                        print("✅ Kết nối lại thành công")
                    else:
                        print("❌ Không thể kết nối lại")
                        
                elif command in ['help', 'h', '?']:
                    show_help()
                    
                elif command in ['quit', 'exit', 'q']:
                    break
                    
                else:
                    print(f"❓ Command '{command}' không hợp lệ. Gõ 'help' để xem hướng dẫn.")
                    
            except KeyboardInterrupt:
                print("\n⚠️ Đã nhận Ctrl+C")
                break
            except EOFError:
                print("\n⚠️ EOF detected")
                break
            except Exception as e:
                print(f"❌ Lỗi xử lý command: {e}")
                
    finally:
        print(f"\n🛑 Đang dọn dẹp...")
        client.stop_detection()
        client.disconnect_from_server()
        print("👋 Đã thoát!")

if __name__ == "__main__":
    main()