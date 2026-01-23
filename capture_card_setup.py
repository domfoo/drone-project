#!/usr/bin/env python3
"""
USB Composite Capture Card Setup and Test

This script helps you configure and test your USB HD Audio/Video capture card
with the Caddx Ratel Pro analog camera.

Your capture card has:
- Yellow wire = Composite Video (CVBS) ← Connect the camera here
- White wire = Left Audio
- Red wire = Right Audio
- S-Video = Higher quality video (optional, if camera supports it)

Connection Options:
1. Direct (bench testing): Caddx Ratel Pro → Yellow wire → Capture Card
2. Via goggles (flight): Cobra X AV Out → Yellow wire → Capture Card
"""

import cv2
import numpy as np
import time
import sys
import platform
from typing import Optional, List, Dict


def get_system_info() -> Dict:
    """Get system and OpenCV info."""
    return {
        'os': platform.system(),
        'os_version': platform.version(),
        'python': sys.version,
        'opencv': cv2.__version__,
        'opencv_backends': [
            ('V4L2', cv2.CAP_V4L2),
            ('DSHOW', cv2.CAP_DSHOW),
            ('MSMF', cv2.CAP_MSMF),
            ('AVFOUNDATION', cv2.CAP_AVFOUNDATION),
            ('ANY', cv2.CAP_ANY),
        ]
    }


def scan_video_devices(max_devices: int = 10) -> List[Dict]:
    """
    Scan for all available video capture devices.
    
    Returns detailed info about each device found.
    """
    print("\n" + "="*60)
    print("SCANNING FOR VIDEO DEVICES")
    print("="*60)
    
    devices = []
    system = platform.system()
    
    # Choose backends based on OS
    if system == "Linux":
        backends = [(cv2.CAP_V4L2, "V4L2"), (cv2.CAP_ANY, "ANY")]
    elif system == "Windows":
        backends = [(cv2.CAP_DSHOW, "DirectShow"), (cv2.CAP_MSMF, "MSMF"), (cv2.CAP_ANY, "ANY")]
    else:
        backends = [(cv2.CAP_ANY, "ANY")]
    
    for i in range(max_devices):
        for backend_id, backend_name in backends:
            cap = cv2.VideoCapture(i, backend_id)
            if cap.isOpened():
                # Get device properties
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
                fourcc_str = "".join([chr((fourcc >> 8 * i) & 0xFF) for i in range(4)])
                
                device_info = {
                    'index': i,
                    'backend': backend_name,
                    'width': width,
                    'height': height,
                    'fps': fps,
                    'fourcc': fourcc_str,
                }
                
                # Check if this looks like an analog capture card
                is_analog = (width == 720 and height in [480, 576]) or \
                           (width == 640 and height == 480)
                device_info['likely_analog'] = is_analog
                
                devices.append(device_info)
                
                status = "← LIKELY YOUR CAPTURE CARD" if is_analog else ""
                print(f"\n  Device {i} ({backend_name}):")
                print(f"    Resolution: {width}x{height}")
                print(f"    FPS: {fps}")
                print(f"    FourCC: {fourcc_str}")
                if status:
                    print(f"    {status}")
                
                cap.release()
                break  # Found device with this backend, move to next index
    
    if not devices:
        print("\n  No video devices found!")
        print("\n  Troubleshooting:")
        print("  - Make sure the capture card is plugged in")
        print("  - On Linux, check: ls /dev/video*")
        print("  - On Linux, you may need: sudo usermod -a -G video $USER")
        print("  - On Windows, check Device Manager")
    
    return devices


def test_capture_card(device_index: int = 0, duration: float = 5.0) -> bool:
    """
    Test video capture from the specified device.
    
    Args:
        device_index: Video device index
        duration: How long to test in seconds
    """
    print(f"\n" + "="*60)
    print(f"TESTING CAPTURE CARD (Device {device_index})")
    print("="*60)
    
    # Try different backends
    system = platform.system()
    if system == "Linux":
        backend = cv2.CAP_V4L2
    elif system == "Windows":
        backend = cv2.CAP_DSHOW
    else:
        backend = cv2.CAP_ANY
    
    cap = cv2.VideoCapture(device_index, backend)
    
    if not cap.isOpened():
        print(f"\n  ✗ Could not open device {device_index}")
        return False
    
    # Try to set NTSC resolution (what Caddx Ratel Pro outputs)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 720)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Low latency
    
    # Get actual settings
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    print(f"\n  Device opened successfully!")
    print(f"  Resolution: {width}x{height}")
    print(f"  FPS: {fps}")
    
    # Determine video standard
    if height == 480:
        print(f"  Standard: NTSC (720x480)")
    elif height == 576:
        print(f"  Standard: PAL (720x576)")
    else:
        print(f"  Standard: Unknown ({width}x{height})")
    
    print(f"\n  Testing capture for {duration} seconds...")
    print("  Press 'q' to quit early, 's' to save a frame")
    print()
    
    frames_captured = 0
    frames_failed = 0
    start_time = time.time()
    latencies = []
    
    try:
        while time.time() - start_time < duration:
            frame_start = time.perf_counter()
            ret, frame = cap.read()
            frame_time = (time.perf_counter() - frame_start) * 1000
            
            if ret and frame is not None:
                frames_captured += 1
                latencies.append(frame_time)
                
                # Add info overlay
                info_frame = frame.copy()
                cv2.putText(info_frame, f"Frame: {frames_captured}", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(info_frame, f"Res: {width}x{height}", (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(info_frame, f"Latency: {frame_time:.1f}ms", (10, 90),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                # Check for video signal
                mean_brightness = np.mean(frame)
                if mean_brightness < 5:
                    cv2.putText(info_frame, "NO SIGNAL?", (width//2-80, height//2),
                               cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)
                
                cv2.imshow("Capture Card Test", info_frame)
                
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('s'):
                    filename = f"capture_test_{frames_captured}.jpg"
                    cv2.imwrite(filename, frame)
                    print(f"    Saved: {filename}")
            else:
                frames_failed += 1
    
    except KeyboardInterrupt:
        print("\n  Interrupted by user")
    
    finally:
        cap.release()
        cv2.destroyAllWindows()
    
    # Print results
    elapsed = time.time() - start_time
    actual_fps = frames_captured / elapsed if elapsed > 0 else 0
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    
    print(f"\n  Results:")
    print(f"  ─────────────────────────────")
    print(f"  Frames captured: {frames_captured}")
    print(f"  Frames failed: {frames_failed}")
    print(f"  Actual FPS: {actual_fps:.1f}")
    print(f"  Average latency: {avg_latency:.1f}ms")
    
    if frames_captured > 0:
        print(f"\n  ✓ Capture card is working!")
        
        # Check if settings are optimal for Caddx Ratel Pro
        if width == 720 and height == 480:
            print(f"  ✓ Resolution matches NTSC (Caddx Ratel Pro default)")
        elif width == 720 and height == 576:
            print(f"  ✓ Resolution matches PAL")
            print(f"    Note: Set your Caddx Ratel Pro to PAL in camera menu")
        else:
            print(f"  ⚠ Unexpected resolution - check camera settings")
        
        return True
    else:
        print(f"\n  ✗ No frames captured!")
        print(f"\n  Troubleshooting:")
        print(f"  - Check the yellow composite cable connection")
        print(f"  - Make sure the Caddx Ratel Pro is powered (4.5-27V)")
        print(f"  - Try the S-Video connection if available")
        return False


def check_signal_quality(device_index: int = 0) -> Dict:
    """
    Analyze the video signal quality.
    
    Checks for:
    - Signal presence
    - Noise levels
    - Color accuracy
    - Interlacing artifacts
    """
    print(f"\n" + "="*60)
    print(f"ANALYZING SIGNAL QUALITY")
    print("="*60)
    
    cap = cv2.VideoCapture(device_index)
    if not cap.isOpened():
        print(f"  ✗ Could not open device")
        return {}
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 720)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    # Capture several frames for analysis
    frames = []
    for _ in range(30):
        ret, frame = cap.read()
        if ret:
            frames.append(frame)
    
    cap.release()
    
    if not frames:
        print(f"  ✗ No frames captured")
        return {}
    
    # Analyze frames
    results = {}
    
    # Check for signal (not just black frames)
    mean_brightness = np.mean([np.mean(f) for f in frames])
    results['has_signal'] = mean_brightness > 10
    print(f"\n  Signal detected: {'Yes' if results['has_signal'] else 'No'}")
    print(f"  Mean brightness: {mean_brightness:.1f}")
    
    if not results['has_signal']:
        print(f"\n  ⚠ No video signal detected!")
        print(f"  - Check cable connections")
        print(f"  - Verify camera is powered")
        return results
    
    # Check noise level (variance between consecutive frames)
    if len(frames) >= 2:
        diffs = [np.mean(np.abs(frames[i].astype(float) - frames[i+1].astype(float))) 
                 for i in range(len(frames)-1)]
        noise_level = np.mean(diffs)
        results['noise_level'] = noise_level
        
        if noise_level < 5:
            quality = "Excellent (static image?)"
        elif noise_level < 15:
            quality = "Good"
        elif noise_level < 30:
            quality = "Fair (some noise)"
        else:
            quality = "Poor (high noise)"
        
        print(f"  Noise level: {noise_level:.1f} ({quality})")
    
    # Check for interlacing artifacts
    frame = frames[-1]
    # Simple interlacing check: compare adjacent lines
    odd_lines = frame[::2]
    even_lines = frame[1::2]
    if odd_lines.shape == even_lines.shape:
        line_diff = np.mean(np.abs(odd_lines.astype(float) - even_lines.astype(float)))
        results['interlacing_detected'] = line_diff > 20
        print(f"  Interlacing artifacts: {'Likely' if results['interlacing_detected'] else 'Minimal'}")
    
    # Color check
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    saturation = np.mean(hsv[:,:,1])
    results['saturation'] = saturation
    print(f"  Color saturation: {saturation:.1f}")
    
    print(f"\n  ✓ Signal quality analysis complete")
    
    return results


def generate_config(device_index: int = 0) -> str:
    """
    Generate optimal configuration for the detected setup.
    """
    print(f"\n" + "="*60)
    print(f"GENERATING CONFIGURATION")
    print("="*60)
    
    cap = cv2.VideoCapture(device_index)
    if not cap.isOpened():
        return ""
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 720)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    cap.release()
    
    # Determine video standard
    if height == 480 or height < 500:
        standard = "ntsc"
        height = 480
    else:
        standard = "pal"
        height = 576
    
    config = f"""
# Generated configuration for your capture card
# Device index: {device_index}
# Detected: {width}x{height} @ {fps}fps ({standard.upper()})

capture:
  device: {device_index}
  width: {width}
  height: {height}
  fps: {int(fps) if fps > 0 else 30}
  standard: "{standard}"
  deinterlace: true
  color_correction: true

# For config.yaml, update these values:
# capture:
#   input_width: {width}
#   input_height: {height}
#   device: {device_index}
"""
    
    print(config)
    
    # Save to file
    with open("capture_config.txt", "w") as f:
        f.write(config)
    print(f"\n  Configuration saved to: capture_config.txt")
    
    return config


def interactive_setup():
    """
    Interactive setup wizard for the capture card.
    """
    print("\n" + "="*60)
    print("CAPTURE CARD SETUP WIZARD")
    print("="*60)
    print("""
This wizard will help you set up your USB capture card with
the Caddx Ratel Pro camera.

Before starting, make sure:
1. The capture card is plugged into USB
2. The YELLOW composite cable is connected to your video source
3. The video source is powered on (camera or goggles AV out)
""")
    
    input("Press Enter to start scanning for devices...")
    
    # Step 1: Scan devices
    devices = scan_video_devices()
    
    if not devices:
        print("\nNo devices found. Please check your connections.")
        return
    
    # Find likely capture card
    analog_devices = [d for d in devices if d.get('likely_analog', False)]
    
    if analog_devices:
        suggested = analog_devices[0]['index']
        print(f"\n  Suggested device: {suggested} (looks like an analog capture card)")
    else:
        suggested = devices[0]['index']
        print(f"\n  Using first available device: {suggested}")
    
    # Step 2: Test the device
    print(f"\n" + "-"*40)
    response = input(f"Test device {suggested}? [Y/n]: ").strip().lower()
    
    if response != 'n':
        success = test_capture_card(suggested, duration=10.0)
        
        if not success:
            print("\nCapture test failed. Please check:")
            print("1. Is the yellow cable connected?")
            print("2. Is the Caddx Ratel Pro powered?")
            print("3. If using goggles, is the drone transmitting?")
            return
    
    # Step 3: Analyze signal
    print(f"\n" + "-"*40)
    response = input("Analyze signal quality? [Y/n]: ").strip().lower()
    
    if response != 'n':
        check_signal_quality(suggested)
    
    # Step 4: Generate config
    print(f"\n" + "-"*40)
    generate_config(suggested)
    
    print(f"\n" + "="*60)
    print("SETUP COMPLETE!")
    print("="*60)
    print(f"""
Your capture card is configured and ready!

Next steps:
1. Update config.yaml with the settings above
2. Train your model: python train.py --dataset YOUR_DATASET
3. Run inference: python inference.py --source {suggested} --weights best.pt

For real-time detection during flight:
- Connect Skyzone Cobra X AV Output → Yellow wire → Capture Card
- Run: python inference.py --source {suggested} --weights best.pt
""")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="USB Capture Card Setup and Test Tool"
    )
    
    parser.add_argument(
        '--scan', 
        action='store_true',
        help="Scan for available video devices"
    )
    parser.add_argument(
        '--test', 
        type=int, 
        metavar='DEVICE',
        help="Test capture from specified device index"
    )
    parser.add_argument(
        '--analyze',
        type=int,
        metavar='DEVICE',
        help="Analyze signal quality from specified device"
    )
    parser.add_argument(
        '--config',
        type=int,
        metavar='DEVICE',
        help="Generate configuration for specified device"
    )
    parser.add_argument(
        '--wizard',
        action='store_true',
        help="Run interactive setup wizard"
    )
    parser.add_argument(
        '--duration',
        type=float,
        default=10.0,
        help="Test duration in seconds (default: 10)"
    )
    
    args = parser.parse_args()
    
    # Print system info
    info = get_system_info()
    print(f"System: {info['os']}")
    print(f"OpenCV: {info['opencv']}")
    
    if args.scan:
        scan_video_devices()
    elif args.test is not None:
        test_capture_card(args.test, args.duration)
    elif args.analyze is not None:
        check_signal_quality(args.analyze)
    elif args.config is not None:
        generate_config(args.config)
    elif args.wizard:
        interactive_setup()
    else:
        # Default: run wizard
        interactive_setup()


if __name__ == "__main__":
    main()
