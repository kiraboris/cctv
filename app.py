#!/usr/bin/env python3
"""
Flask web server for streaming Tapo camera feed to Flutter app or browser.
Uses MJPEG streaming for maximum compatibility.
"""

from flask import Flask, Response, render_template_string
from tapo_camera import TapoCamera, load_config
import cv2
import threading
import time
import signal
import atexit
import socket

app = Flask(__name__)

# Global camera instance
camera = None
frame_lock = threading.Lock()


def initialize_camera():
    """Initialize camera connection."""
    global camera
    
    config = load_config()
    cam_config = config.get("camera", {})
    
    CAMERA_IP = cam_config.get("host", "192.168.1.100")
    CAMERA_PORT = cam_config.get("port", 2020)
    CAMERA_USERNAME = cam_config.get("username", "admin")
    CAMERA_PASSWORD = cam_config.get("password", "")
    
    camera = TapoCamera(CAMERA_IP, CAMERA_PORT, CAMERA_USERNAME, CAMERA_PASSWORD)
    
    if not camera.connect():
        print("Failed to connect to camera. Check your configuration.")
        return False
    
    if not camera.start_stream():
        print("Failed to start camera stream.")
        return False
    
    print("Camera initialized successfully!")
    return True


def generate_frames():
    """Generator function for MJPEG streaming."""
    global camera
    
    while True:
        if camera is None or not camera.running:
            time.sleep(0.1)
            continue
        
        frame = camera.read_frame()
        
        if frame is None:
            time.sleep(0.1)
            continue
        
        # Encode frame as JPEG
        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        
        if not ret:
            continue
        
        # MJPEG format: multipart HTTP response
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')


@app.route('/')
def index():
    """Main page with video stream."""
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Tapo Camera Feed</title>
        <meta charset="utf-8">
        <style>
            body {
                margin: 0;
                padding: 20px;
                background-color: #000;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                font-family: Arial, sans-serif;
            }
            .container {
                text-align: center;
                max-width: 100%;
            }
            h1 {
                color: #fff;
                margin-bottom: 20px;
            }
            img {
                max-width: 100%;
                height: auto;
                border: 2px solid #333;
                box-shadow: 0 4px 8px rgba(0,0,0,0.5);
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Tapo Camera Feed</h1>
            <img src="/video_feed" alt="Camera Feed">
        </div>
    </body>
    </html>
    """
    return render_template_string(html_template)


@app.route('/video_feed')
def video_feed():
    """MJPEG stream endpoint - compatible with Flutter and browsers."""
    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@app.route('/api/status')
def status():
    """API endpoint to check camera status."""
    global camera
    
    if camera is None:
        return {'status': 'not_initialized', 'camera': None}
    
    if not camera.running:
        return {'status': 'not_streaming', 'camera': 'connected'}
    
    info = camera.get_camera_info()
    return {
        'status': 'streaming',
        'camera': info,
        'stream_uri': camera.get_stream_uri() if camera else None
    }


def cleanup():
    """Cleanup resources on shutdown."""
    global camera
    if camera:
        camera.stop_stream()
        print("Camera stream stopped.")


# Register cleanup handlers
def signal_handler(signum, frame):
    """Handle shutdown signals."""
    cleanup()
    exit(0)


def get_local_ip():
    """Get the local IP address of this machine."""
    try:
        # Connect to a remote address (doesn't actually send data)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            # Fallback: get hostname and resolve
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            return ip
        except Exception:
            return None


def print_connection_info(host, port):
    """Print connection information for accessing the server."""
    print("\n" + "="*60)
    print("SERVER STARTED - Access from other devices:")
    print("="*60)
    
    if host == "0.0.0.0" or host == "":
        local_ip = get_local_ip()
        if local_ip:
            print(f"  On this computer:")
            print(f"    http://localhost:{port}/")
            print(f"\n  From other devices on your network:")
            print(f"    http://{local_ip}:{port}/")
            print(f"    http://{local_ip}:{port}/video_feed")
            print(f"    http://{local_ip}:{port}/api/status")
        else:
            print(f"  Could not determine local IP address")
            print(f"  Try accessing via: http://<your-ip>:{port}/")
    else:
        print(f"  Server URL: http://{host}:{port}/")
    
    print("="*60 + "\n")


# Register signal handlers for graceful shutdown
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
atexit.register(cleanup)

# Initialize camera when module is loaded (works with both Flask dev server and gunicorn)
if not initialize_camera():
    print("Warning: Failed to initialize camera. Status will show 'not_initialized'.")
    print("Check your configuration and camera connectivity.")


if __name__ == '__main__':
    try:
        # Get server config
        config = load_config()
        server_config = config.get("server", {})
        host = server_config.get("host", "0.0.0.0")
        port = server_config.get("port", 8080)
        debug = server_config.get("debug", False)
        
        print_connection_info(host, port)
        print("\nTo run with gunicorn, use:")
        print(f"  gunicorn -w 1 -b {host}:{port} --threads 2 --timeout 120 app:app")
        print("\nPress Ctrl+C to stop.\n")
        
        app.run(host=host, port=port, debug=debug, threaded=True)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        cleanup()

