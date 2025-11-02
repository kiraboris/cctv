# Tapo C211 ONVIF Camera Module

A Python module for connecting to Tapo C211 WiFi camera via ONVIF protocol and displaying the video feed.

## Installation

1. Create a virtual environment (recommended):

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

3. Configure your camera settings:

Copy `config.example.json` to `config.json` and update it with your camera's details:

```bash
cp config.example.json config.json
```

Edit `config.json` with your camera's IP address, port, username, and password:

```json
{
  "camera": {
    "host": "192.168.1.100",
    "port": 2020,
    "username": "admin",
    "password": "your_password"
  },
  "display": {
    "window_name": "Tapo Camera Feed"
  }
}
```

## Usage

### Basic Usage

```python
from tapo_camera import TapoCamera

# Initialize camera connection
camera = TapoCamera(
    host="192.168.1.100",  # Your camera's IP address
    port=2020,             # ONVIF port (usually 2020 for Tapo)
    username="admin",      # Your camera username
    password="your_password"  # Your camera password
)

# Connect to camera
camera.connect()

# Display video feed
camera.display_feed()
```

### Configuration File Usage (Recommended)

The easiest way is to configure your camera settings in `config.json`. The module will automatically load settings from this file:

```bash
python tapo_camera.py
```

### Command Line Usage

You can also override config file settings via command line arguments:

```bash
python tapo_camera.py [IP] [PORT] [USERNAME] [PASSWORD]
```

Example:
```bash
python tapo_camera.py 192.168.1.100 2020 admin mypassword
```

Command line arguments will override values from `config.json`.

### Programmatic Usage

```python
from tapo_camera import TapoCamera

camera = TapoCamera("192.168.1.100", 2020, "admin", "password")
camera.connect()

# Get camera information
info = camera.get_camera_info()
print(info)

# Get stream URI
stream_uri = camera.get_stream_uri()
print(f"Stream URI: {stream_uri}")

# Start streaming and display
camera.display_feed()

# When done, stop the stream
camera.stop_stream()
```

## Features

- Connect to Tapo C211 camera via ONVIF protocol
- Get camera information (manufacturer, model, firmware version, etc.)
- Obtain RTSP stream URI
- Display live video feed using OpenCV
- Easy to integrate into other projects

## Notes

- Make sure your camera and computer are on the same network
- Tapo cameras typically use port 2020 for ONVIF
- The default username is usually "admin"
- Press 'q' in the video window to quit
- The module uses ONVIF to get the RTSP stream URI and then connects directly via RTSP

## Troubleshooting

1. **Connection failed**: 
   - Verify the camera IP address
   - Ensure the camera is powered on and connected to the network
   - Check that the ONVIF service is enabled on the camera

2. **Stream won't open**:
   - Verify your username and password are correct
   - Try accessing the camera's web interface to ensure it's working
   - Check firewall settings

3. **No frames received**:
   - Some cameras may require additional setup
   - Try using the camera's web interface to verify the stream works

