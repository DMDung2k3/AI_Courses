from flask import Flask, Response, jsonify, request
from flask_socketio import SocketIO, emit
import cv2
import json
import threading
import time
from datetime import datetime
import base64
import numpy as np
import socket
import sys

app = Flask(__name__)
app.config['SECRET_KEY'] = 'face_detection_secret'

def find_free_port(start_port=8080):
    """Find a free port starting from start_port"""
    port = start_port
    while port < start_port + 100:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(('localhost', port))
            sock.close()
            return port
        except OSError:
            port += 1
        finally:
            sock.close()
    raise RuntimeError("No free ports found")

# Try to find a free port
try:
    PORT = find_free_port(8080)
    print(f"Using port: {PORT}")
except:
    PORT = 8080
    print(f"Using default port: {PORT}")

# Initialize SocketIO with error handling
try:
    socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)
except Exception as e:
    print(f"Error initializing SocketIO: {e}")
    socketio = SocketIO(app, cors_allowed_origins="*")

class FaceDetectionServer:
    def __init__(self):
        self.camera = None
        # Check if OpenCV cascade file exists
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        try:
            self.face_cascade = cv2.CascadeClassifier(cascade_path)
            if self.face_cascade.empty():
                print("Warning: Could not load face cascade classifier")
        except Exception as e:
            print(f"Error loading face cascade: {e}")
            self.face_cascade = None
            
        self.is_running = False
        self.last_detection = None
        self.detection_events = []
        
    def start_camera(self):
        """Khởi động camera"""
        try:
            # Try different camera indices
            for i in range(3):
                try:
                    self.camera = cv2.VideoCapture(i)
                    if self.camera.isOpened():
                        print(f"Camera {i} opened successfully")
                        break
                    else:
                        self.camera.release()
                except:
                    continue
            else:
                print("No camera found")
                return False
                
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.camera.set(cv2.CAP_PROP_FPS, 30)
            
            # Test if camera is working
            ret, frame = self.camera.read()
            if not ret:
                print("Cannot read from camera")
                self.camera.release()
                return False
                
            self.is_running = True
            print("Camera started successfully")
            return True
            
        except Exception as e:
            print(f"Lỗi khởi động camera: {e}")
            if self.camera:
                self.camera.release()
            return False
    
    def stop_camera(self):
        """Dừng camera"""
        self.is_running = False
        if self.camera:
            self.camera.release()
            print("Camera stopped")
            
    def detect_faces(self, frame):
        """Nhận diện khuôn mặt trong frame"""
        if self.face_cascade is None:
            return frame, []
            
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
            
            # Vẽ khung quanh khuôn mặt
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
            
            return frame, faces
        except Exception as e:
            print(f"Error in face detection: {e}")
            return frame, []
    
    def generate_frames(self):
        """Generator cho video stream"""
        while self.is_running and self.camera and self.camera.isOpened():
            try:
                success, frame = self.camera.read()
                if not success:
                    print("Failed to read frame")
                    break
                
                # Nhận diện khuôn mặt
                processed_frame, faces = self.detect_faces(frame)
                
                # Gửi event nếu có khuôn mặt được phát hiện
                if len(faces) > 0:
                    self.handle_face_detection(faces)
                
                # Encode frame thành JPEG
                ret, buffer = cv2.imencode('.jpg', processed_frame, 
                                         [cv2.IMWRITE_JPEG_QUALITY, 80])
                if ret:
                    frame_bytes = buffer.tobytes()
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                else:
                    print("Failed to encode frame")
                    
            except Exception as e:
                print(f"Error in frame generation: {e}")
                break
    
    def handle_face_detection(self, faces):
        """Xử lý event khi phát hiện khuôn mặt"""
        try:
            current_time = datetime.now().isoformat()
            
            event_data = {
                'timestamp': current_time,
                'faces_count': len(faces),
                'faces': [{'x': int(x), 'y': int(y), 'width': int(w), 'height': int(h)} 
                         for (x, y, w, h) in faces],
                'event_type': 'face_detected'
            }
            
            # Lưu event
            self.detection_events.append(event_data)
            
            # Giữ chỉ 100 events gần nhất
            if len(self.detection_events) > 100:
                self.detection_events = self.detection_events[-100:]
            
            self.last_detection = event_data
            
            # Gửi event qua WebSocket với error handling
            try:
                socketio.emit('face_detected', event_data)
            except Exception as e:
                print(f"Error emitting WebSocket event: {e}")
            
            print(f"Phát hiện {len(faces)} khuôn mặt lúc {current_time}")
            
        except Exception as e:
            print(f"Error handling face detection: {e}")

# Khởi tạo detector
detector = FaceDetectionServer()

# Routes
@app.route('/')
def index():
    """Trang chủ với demo"""
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Face Detection Server</title>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .controls {{ margin: 20px 0; }}
            button {{ padding: 10px 20px; margin: 5px; font-size: 16px; }}
            .status {{ background: #f0f0f0; padding: 10px; margin: 10px 0; border-radius: 5px; }}
            .events {{ max-height: 300px; overflow-y: auto; border: 1px solid #ccc; padding: 10px; }}
            #video-feed {{ border: 2px solid #333; margin: 10px 0; }}
        </style>
    </head>
    <body>
        <h1>🎯 Face Detection Server</h1>
        <div class="controls">
            <button onclick="startDetection()" id="startBtn">🚀 Bắt đầu</button>
            <button onclick="stopDetection()" id="stopBtn">⏹️ Dừng</button>
            <button onclick="checkStatus()">📊 Kiểm tra trạng thái</button>
        </div>
        <br>
        <img id="video-feed" src="/video_feed" width="640" height="480" 
             onerror="this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjQwIiBoZWlnaHQ9IjQ4MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZGRkIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxOCIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPkNhbWVyYSBjaOG7qWEga2jhu59pIMSR4buZbmc8L3RleHQ+PC9zdmc+'">
        
        <div class="status" id="status">Trạng thái: Chưa khởi động</div>
        
        <div class="events">
            <h3>📋 Events gần đây:</h3>
            <div id="event-list"></div>
        </div>
        
        <script>
            const socket = io();
            let connected = false;
            
            socket.on('connect', function() {{
                connected = true;
                console.log('Connected to server');
                document.getElementById('status').innerHTML = '🟢 Kết nối thành công';
            }});
            
            socket.on('disconnect', function() {{
                connected = false;
                console.log('Disconnected from server');
                document.getElementById('status').innerHTML = '🔴 Mất kết nối';
            }});
            
            socket.on('face_detected', function(data) {{
                document.getElementById('status').innerHTML = 
                    `🎯 Phát hiện ${{data.faces_count}} khuôn mặt lúc ${{data.timestamp}}`;
                
                const eventDiv = document.createElement('div');
                eventDiv.innerHTML = `⏰ ${{data.timestamp}}: ${{data.faces_count}} khuôn mặt`;
                eventDiv.style.padding = '5px';
                eventDiv.style.borderBottom = '1px solid #eee';
                document.getElementById('event-list').prepend(eventDiv);
                
                // Keep only last 10 events
                const events = document.getElementById('event-list').children;
                while (events.length > 10) {{
                    events[events.length - 1].remove();
                }}
            }});
            
            function startDetection() {{
                fetch('/start', {{method: 'POST'}})
                    .then(response => response.json())
                    .then(data => {{
                        console.log(data);
                        if (data.status === 'success') {{
                            document.getElementById('video-feed').src = '/video_feed?' + Date.now();
                            document.getElementById('status').innerHTML = '🟢 ' + data.message;
                        }} else {{
                            document.getElementById('status').innerHTML = '🔴 ' + data.message;
                        }}
                    }})
                    .catch(error => {{
                        console.error('Error:', error);
                        document.getElementById('status').innerHTML = '🔴 Lỗi kết nối';
                    }});
            }}
            
            function stopDetection() {{
                fetch('/stop', {{method: 'POST'}})
                    .then(response => response.json())
                    .then(data => {{
                        console.log(data);
                        document.getElementById('status').innerHTML = '🟡 ' + data.message;
                    }})
                    .catch(error => {{
                        console.error('Error:', error);
                    }});
            }}
            
            function checkStatus() {{
                fetch('/status')
                    .then(response => response.json())
                    .then(data => {{
                        const statusText = data.is_running ? '🟢 Đang chạy' : '🔴 Đã dừng';
                        document.getElementById('status').innerHTML = 
                            `${{statusText}} - Tổng events: ${{data.total_events}}`;
                    }});
            }}
            
            // Auto-refresh video feed every 30 seconds if running
            setInterval(() => {{
                if (connected) {{
                    checkStatus();
                }}
            }}, 30000);
        </script>
    </body>
    </html>
    '''

@app.route('/video_feed')
def video_feed():
    """Video stream endpoint"""
    if not detector.is_running:
        return "Camera chưa được khởi động. Vui lòng bấm 'Bắt đầu' trước.", 503
    
    try:
        return Response(detector.generate_frames(),
                       mimetype='multipart/x-mixed-replace; boundary=frame')
    except Exception as e:
        print(f"Error in video feed: {e}")
        return f"Lỗi video stream: {e}", 500

@app.route('/start', methods=['POST'])
def start_detection():
    """API để bắt đầu nhận diện"""
    try:
        if detector.start_camera():
            return jsonify({
                'status': 'success',
                'message': 'Đã bắt đầu nhận diện khuôn mặt',
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Không thể khởi động camera. Kiểm tra kết nối camera.'
            }), 500
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Lỗi: {str(e)}'
        }), 500

@app.route('/stop', methods=['POST'])
def stop_detection():
    """API để dừng nhận diện"""
    try:
        detector.stop_camera()
        return jsonify({
            'status': 'success',
            'message': 'Đã dừng nhận diện khuôn mặt',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Lỗi: {str(e)}'
        }), 500

@app.route('/status')
def get_status():
    """Lấy trạng thái hiện tại"""
    try:
        return jsonify({
            'is_running': detector.is_running,
            'last_detection': detector.last_detection,
            'total_events': len(detector.detection_events),
            'camera_available': detector.camera is not None and detector.camera.isOpened() if detector.camera else False
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'is_running': False,
            'total_events': 0
        }), 500

@app.route('/events')
def get_events():
    """Lấy danh sách events"""
    try:
        limit = request.args.get('limit', 10, type=int)
        return jsonify({
            'events': detector.detection_events[-limit:],
            'total': len(detector.detection_events)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/latest_detection')
def get_latest_detection():
    """Lấy detection mới nhất"""
    try:
        return jsonify({
            'detection': detector.last_detection,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# WebSocket events
@socketio.on('connect')
def handle_connect():
    print('Client connected')
    try:
        emit('connected', {'message': 'Connected to Face Detection Server'})
    except Exception as e:
        print(f"Error emitting connect event: {e}")

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on_error_default
def default_error_handler(e):
    print(f'WebSocket error: {e}')

if __name__ == '__main__':
    print("🎯 Face Detection Server đang khởi động...")
    print("📹 Endpoints:")
    print(f"   - Video stream: http://localhost:{PORT}/video_feed")
    print(f"   - Start detection: POST http://localhost:{PORT}/start")
    print(f"   - Stop detection: POST http://localhost:{PORT}/stop")
    print(f"   - Get status: GET http://localhost:{PORT}/status")
    print(f"   - Get events: GET http://localhost:{PORT}/events")
    print(f"   - Latest detection: GET http://localhost:{PORT}/latest_detection")
    print(f"   - WebSocket: ws://localhost:{PORT}")
    print(f"   - Demo page: http://localhost:{PORT}/")
    print(f"\n🚀 Server starting on port {PORT}...")
    
    try:
        # Try running with different configurations
        socketio.run(app, host='127.0.0.1', port=PORT, debug=False, allow_unsafe_werkzeug=True)
    except Exception as e:
        print(f"Error starting server: {e}")
        print("Trying alternative configuration...")
        try:
            socketio.run(app, host='localhost', port=PORT+1, debug=False)
        except Exception as e2:
            print(f"Failed to start server: {e2}")
            print("\n🔧 Troubleshooting tips:")
            print("1. Try running as administrator")
            print("2. Check if another process is using the port")
            print("3. Try disabling Windows Firewall temporarily")
            print("4. Check antivirus software")