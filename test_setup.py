#!/usr/bin/env python3
"""
Network scanner and setup tool for Tapo C211 camera.
Automatically scans the network to find ONVIF cameras with confirmation prompts.
"""

import socket
import ipaddress
import json
import sys
import os
import getpass
from concurrent.futures import ThreadPoolExecutor, as_completed
from onvif import ONVIFCamera


def get_local_network():
    """Get the local network IP range."""
    try:
        # Connect to a remote address to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        
        # Get network address
        network = ipaddress.IPv4Network(f"{local_ip}/24", strict=False)
        return str(network.network_address), str(network.broadcast_address)
    except Exception as e:
        print(f"Error determining local network: {e}")
        return None, None


def check_port(ip, port, timeout=1):
    """Check if a port is open on the given IP."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0
    except:
        return False


def check_onvif_service(ip, port, username="admin", password=""):
    """Check if an ONVIF service is available at the given IP and port."""
    try:
        camera = ONVIFCamera(ip, port, username, password)
        device_service = camera.create_devicemgmt_service()
        device_info = device_service.GetDeviceInformation()
        return {
            'ip': ip,
            'port': port,
            'manufacturer': device_info.Manufacturer,
            'model': device_info.Model,
            'firmware': device_info.FirmwareVersion,
            'serial': device_info.SerialNumber,
            'hardware_id': device_info.HardwareId
        }
    except Exception as e:
        return None


def scan_network_for_cameras(network_start, network_end, ports=[2020, 80, 8080], username="admin", password=""):
    """Scan network for ONVIF cameras."""
    print("=" * 60)
    print("NETWORK SCAN FOR ONVIF CAMERAS")
    print("=" * 60)
    print()
    
    # Parse IP range
    try:
        start_ip = ipaddress.IPv4Address(network_start)
        end_ip = ipaddress.IPv4Address(network_end)
    except:
        print(f"Invalid IP range: {network_start} - {network_end}")
        return []
    
    # Generate IP list
    ip_list = []
    current = int(start_ip)
    end = int(end_ip)
    while current <= end:
        ip_list.append(str(ipaddress.IPv4Address(current)))
        current += 1
    
    print(f"Scanning {len(ip_list)} IP addresses on ports {ports}...")
    print("This may take a few minutes. Please wait...")
    print()
    
    found_cameras = []
    
    # First, scan for open ports
    print("Step 1: Scanning for open ports...")
    open_ports = []
    
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = []
        for ip in ip_list:
            for port in ports:
                futures.append(executor.submit(check_port, ip, port))
        
        completed = 0
        total = len(futures)
        for future in as_completed(futures):
            completed += 1
            if completed % 100 == 0:
                print(f"  Progress: {completed}/{total} ({completed*100//total}%)", end='\r')
        
        # Collect results (we'll re-scan for ports that are open)
        print(f"\n  Port scanning complete. Checking ONVIF services...")
    
    # Now check ONVIF services on detected ports
    print("\nStep 2: Checking ONVIF services on open ports...")
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for ip in ip_list:
            for port in ports:
                if check_port(ip, port, timeout=0.5):
                    futures.append(executor.submit(check_onvif_service, ip, port, username, password))
        
        completed = 0
        total = len(futures)
        for future in as_completed(futures):
            completed += 1
            result = future.result()
            if result:
                found_cameras.append(result)
                print(f"  ✓ Found camera at {result['ip']}:{result['port']}")
                print(f"    Model: {result['manufacturer']} {result['model']}")
            if completed % 10 == 0:
                print(f"  Progress: {completed}/{total} ONVIF checks completed", end='\r')
    
    print()
    return found_cameras


def manual_ip_scan():
    """Allow user to manually enter IP address to scan."""
    print("\n" + "=" * 60)
    print("MANUAL IP SCAN")
    print("=" * 60)
    print()
    
    ip = input("Enter camera IP address: ").strip()
    if not ip:
        return None
    
    # Validate IP
    try:
        ipaddress.IPv4Address(ip)
    except:
        print("Invalid IP address")
        return None
    
    ports = [2020, 80, 8080]
    print(f"\nScanning {ip} on ports {ports}...")
    
    for port in ports:
        if check_port(ip, port):
            print(f"  Port {port} is open, checking ONVIF service...")
            camera_info = check_onvif_service(ip, port)
            if camera_info:
                return camera_info
    
    print("No ONVIF service found at this IP address.")
    return None


def confirm_camera(camera_info):
    """Ask user to confirm if this is the correct camera."""
    print("\n" + "=" * 60)
    print("CAMERA FOUND")
    print("=" * 60)
    print()
    print(f"IP Address:     {camera_info['ip']}")
    print(f"Port:           {camera_info['port']}")
    print(f"Manufacturer:   {camera_info['manufacturer']}")
    print(f"Model:          {camera_info['model']}")
    print(f"Firmware:       {camera_info['firmware']}")
    print(f"Serial Number:  {camera_info.get('serial', 'N/A')}")
    print()
    
    response = input("Is this your Tapo C211 camera? (y/n): ").strip().lower()
    return response == 'y' or response == 'yes'


def update_config(camera_ip, camera_port, username, password):
    """Update config.json with camera settings."""
    config_path = "config.json"
    
    try:
        # Load existing config or create default
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
        else:
            config = {
                "camera": {},
                "display": {"window_name": "Tapo Camera Feed"}
            }
        
        # Update camera settings
        config["camera"]["host"] = camera_ip
        config["camera"]["port"] = camera_port
        config["camera"]["username"] = username
        config["camera"]["password"] = password
        
        # Save config
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"\n✓ Configuration saved to {config_path}")
        return True
    except Exception as e:
        print(f"\n✗ Error saving config: {e}")
        return False


def main():
    """Main function to run camera discovery."""
    import os
    
    print("=" * 60)
    print("TAPO C211 CAMERA DISCOVERY TOOL")
    print("=" * 60)
    print()
    
    # Get username and password first
    print("First, we need your camera credentials:")
    username = input("Camera username [admin]: ").strip() or "admin"
    password = getpass.getpass("Camera password: ")
    
    if not password:
        print("\n⚠ Warning: No password entered. Some cameras may require a password.")
        proceed = input("Continue anyway? (y/n): ").strip().lower()
        if proceed != 'y' and proceed != 'yes':
            print("Cancelled.")
            return
    
    print("\nChoose scanning method:")
    print("1. Automatic network scan (scans entire local network)")
    print("2. Manual IP address entry")
    print("3. Skip scanning, just show instructions")
    print()
    
    choice = input("Enter choice [1]: ").strip() or "1"
    
    found_camera = None
    
    if choice == "1":
        # Automatic network scan
        network_start, network_end = get_local_network()
        
        if not network_start:
            print("Could not determine local network. Using common default: 192.168.1.0/24")
            network_start = "192.168.1.0"
            network_end = "192.168.1.255"
        else:
            print(f"Detected network: {network_start} - {network_end}")
            confirm = input("Use this network range? (y/n): ").strip().lower()
            if confirm != 'y' and confirm != 'yes':
                network_start = input("Enter network start IP (e.g., 192.168.1.0): ").strip() or network_start
                network_end = input("Enter network end IP (e.g., 192.168.1.255): ").strip() or network_end
        
        found_cameras = scan_network_for_cameras(network_start, network_end, username=username, password=password)
        
        if not found_cameras:
            print("\n✗ No ONVIF cameras found on the network.")
            print("\nTrying manual scan...")
            found_camera = manual_ip_scan()
        else:
            print(f"\n✓ Found {len(found_cameras)} ONVIF camera(s):")
            print()
            for i, cam in enumerate(found_cameras, 1):
                print(f"{i}. {cam['manufacturer']} {cam['model']} at {cam['ip']}:{cam['port']}")
            
            if len(found_cameras) == 1:
                if confirm_camera(found_cameras[0]):
                    found_camera = found_cameras[0]
            else:
                selection = input(f"\nSelect camera (1-{len(found_cameras)}): ").strip()
                try:
                    idx = int(selection) - 1
                    if 0 <= idx < len(found_cameras):
                        if confirm_camera(found_cameras[idx]):
                            found_camera = found_cameras[idx]
                except:
                    print("Invalid selection")
    
    elif choice == "2":
        # Manual IP entry
        found_camera = manual_ip_scan()
    
    else:
        # Show instructions
        print("\n" + "=" * 60)
        print("MANUAL SETUP INSTRUCTIONS")
        print("=" * 60)
        print()
        print("To configure your camera manually:")
        print("1. Find your camera's IP address (router admin, Tapo app, etc.)")
        print("2. Edit config.json with your camera details")
        print("3. Or run: python tapo_camera.py <IP> <PORT> <USERNAME> <PASSWORD>")
        print()
        return
    
    # Process found camera
    if found_camera:
        if confirm_camera(found_camera):
            update = input("\nUpdate config.json with these settings? (y/n): ").strip().lower()
            if update == 'y' or update == 'yes':
                update_config(found_camera['ip'], found_camera['port'], username, password)
                print("\n✓ Setup complete! You can now run: python tapo_camera.py")
            else:
                print("\nConfiguration not saved. You can manually edit config.json")
        else:
            print("\nCamera not confirmed. Please try scanning again or set up manually.")
    else:
        print("\nNo camera found. Please check:")
        print("  - Camera is powered on and connected to WiFi")
        print("  - Camera and computer are on the same network")
        print("  - ONVIF is enabled on the camera")
        print("  - Camera credentials are correct")
        print("\nYou can also manually edit config.json with your camera details.")


if __name__ == "__main__":
    main()
