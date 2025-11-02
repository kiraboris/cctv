"""
Module for connecting to Tapo C211 WiFi camera via ONVIF and displaying video feed.
"""

import cv2
from onvif import ONVIFCamera
import threading
import time
import json
import os


class TapoCamera:
    """Class to handle Tapo C211 camera connection via ONVIF and video streaming."""
    
    def __init__(self, host, port, username, password):
        """
        Initialize the Tapo camera connection.
        
        Args:
            host (str): Camera IP address
            port (int): ONVIF port (usually 2020 for Tapo cameras)
            username (str): Camera username
            password (str): Camera password
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.camera = None
        self.media_service = None
        self.stream_uri = None
        self.cap = None
        self.running = False
        
    def connect(self):
        """Connect to the camera via ONVIF."""
        try:
            print(f"Connecting to camera at {self.host}:{self.port}...")
            self.camera = ONVIFCamera(self.host, self.port, self.username, self.password)
            
            # Create media service
            self.media_service = self.camera.create_media_service()
            
            # Get profiles
            profiles = self.media_service.GetProfiles()
            if not profiles:
                raise Exception("No profiles found on camera")
            
            # Use the first profile
            profile = profiles[0]
            print(f"Using profile: {profile.Name}")
            
            # Get stream URI
            stream_setup = self.camera.create_type('GetStreamUri')
            stream_setup.ProfileToken = profile.token
            stream_setup.StreamSetup = {
                'Stream': 'RTP-Unicast',
                'Transport': {'Protocol': 'RTSP'}
            }
            
            stream_uri_response = self.media_service.GetStreamUri(stream_setup)
            self.stream_uri = stream_uri_response.Uri
            
            # Add credentials to RTSP URI if not present
            if self.username and self.password:
                if '://' in self.stream_uri:
                    protocol = self.stream_uri.split('://')[0]
                    uri_part = self.stream_uri.split('://')[1]
                    self.stream_uri = f"{protocol}://{self.username}:{self.password}@{uri_part}"
            
            print(f"Stream URI obtained: {self.stream_uri[:50]}...")
            return True
            
        except Exception as e:
            print(f"Error connecting to camera: {e}")
            return False
    
    def get_stream_uri(self):
        """Get the RTSP stream URI."""
        return self.stream_uri
    
    def start_stream(self):
        """Start the video stream."""
        if not self.stream_uri:
            print("No stream URI available. Please connect first.")
            return False
        
        try:
            print("Opening video stream...")
            self.cap = cv2.VideoCapture(self.stream_uri)
            
            if not self.cap.isOpened():
                raise Exception("Failed to open video stream")
            
            self.running = True
            print("Video stream opened successfully!")
            return True
            
        except Exception as e:
            print(f"Error starting stream: {e}")
            return False
    
    def read_frame(self):
        """Read a single frame from the stream."""
        if not self.cap or not self.cap.isOpened():
            return None
        
        ret, frame = self.cap.read()
        if ret:
            return frame
        return None
    
    def stop_stream(self):
        """Stop the video stream."""
        self.running = False
        if self.cap:
            self.cap.release()
            self.cap = None
        print("Video stream stopped.")
    
    def display_feed(self, window_name="Tapo Camera Feed"):
        """
        Display the video feed in a window.
        
        Args:
            window_name (str): Name of the display window
        """
        if not self.running:
            if not self.start_stream():
                return
        
        print("Displaying video feed. Press 'q' to quit.")
        
        try:
            while self.running:
                frame = self.read_frame()
                
                if frame is None:
                    print("Failed to read frame. Retrying...")
                    time.sleep(0.1)
                    continue
                
                # Display the frame
                cv2.imshow(window_name, frame)
                
                # Break on 'q' key press
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
        except KeyboardInterrupt:
            print("\nInterrupted by user")
        finally:
            self.stop_stream()
            cv2.destroyAllWindows()
    
    def get_camera_info(self):
        """Get camera information."""
        if not self.camera:
            return None
        
        try:
            device_service = self.camera.create_devicemgmt_service()
            device_info = device_service.GetDeviceInformation()
            
            return {
                'Manufacturer': device_info.Manufacturer,
                'Model': device_info.Model,
                'FirmwareVersion': device_info.FirmwareVersion,
                'SerialNumber': device_info.SerialNumber,
                'HardwareId': device_info.HardwareId
            }
        except Exception as e:
            print(f"Error getting camera info: {e}")
            return None


def load_config(config_path="config.json"):
    """
    Load camera configuration from JSON file.
    
    Args:
        config_path (str): Path to the configuration file
        
    Returns:
        dict: Configuration dictionary with camera settings
    """
    default_config = {
        "camera": {
            "host": "192.168.1.100",
            "port": 2020,
            "username": "admin",
            "password": ""
        },
        "display": {
            "window_name": "Tapo Camera Feed"
        }
    }
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                # Merge with defaults to ensure all keys exist
                merged_config = default_config.copy()
                merged_config.update(config)
                return merged_config
        except json.JSONDecodeError as e:
            print(f"Error parsing config file: {e}")
            print("Using default configuration.")
            return default_config
        except Exception as e:
            print(f"Error reading config file: {e}")
            print("Using default configuration.")
            return default_config
    else:
        print(f"Config file '{config_path}' not found. Using default configuration.")
        # Create default config file
        try:
            with open(config_path, 'w') as f:
                json.dump(default_config, f, indent=2)
            print(f"Created default config file: {config_path}")
            print("Please update it with your camera details.")
        except Exception as e:
            print(f"Could not create config file: {e}")
        return default_config


def main():
    """Example usage of the Tapo camera module."""
    import sys
    
    # Load configuration from config.json
    config = load_config()
    cam_config = config.get("camera", {})
    display_config = config.get("display", {})
    
    # Get camera settings from config file
    CAMERA_IP = cam_config.get("host", "192.168.1.100")
    CAMERA_PORT = cam_config.get("port", 2020)
    CAMERA_USERNAME = cam_config.get("username", "admin")
    CAMERA_PASSWORD = cam_config.get("password", "")
    WINDOW_NAME = display_config.get("window_name", "Tapo Camera Feed")
    
    # Allow command line arguments to override config
    if len(sys.argv) > 1:
        CAMERA_IP = sys.argv[1]
    if len(sys.argv) > 2:
        CAMERA_PORT = int(sys.argv[2])
    if len(sys.argv) > 3:
        CAMERA_USERNAME = sys.argv[3]
    if len(sys.argv) > 4:
        CAMERA_PASSWORD = sys.argv[4]
    
    # Create camera instance
    camera = TapoCamera(CAMERA_IP, CAMERA_PORT, CAMERA_USERNAME, CAMERA_PASSWORD)
    
    # Connect to camera
    if not camera.connect():
        print("Failed to connect to camera. Exiting.")
        sys.exit(1)
    
    # Get and print camera info
    info = camera.get_camera_info()
    if info:
        print("\nCamera Information:")
        for key, value in info.items():
            print(f"  {key}: {value}")
        print()
    
    # Display video feed
    camera.display_feed(WINDOW_NAME)


if __name__ == "__main__":
    main()

