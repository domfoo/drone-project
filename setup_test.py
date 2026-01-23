#!/usr/bin/env python3
"""
Hardware Setup and Testing Script

Tests your hardware setup for the drone trash detection system:
1. GPU detection and capabilities
2. Video capture devices
3. Model loading and inference speed

Run this first to verify your setup works correctly.
"""

import sys
import time
from pathlib import Path

def check_python_version():
    """Check Python version."""
    print("Checking Python version...")
    version = sys.version_info
    print(f"  Python {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("  ⚠ Warning: Python 3.8+ recommended")
        return False
    print("  ✓ Python version OK")
    return True


def check_cuda():
    """Check CUDA availability and GPU info."""
    print("\nChecking CUDA and GPU...")
    
    try:
        import torch
        print(f"  CUDA Version: {torch.__version__}")
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1e9
            cuda_version = torch.version.cuda
            
            print(f"  ✓ CUDA Available")
            print(f"  CUDA Version: {cuda_version}")
            print(f"  GPU: {gpu_name}")
            print(f"  GPU Memory: {gpu_memory:.1f} GB")
            
            # Check for RTX 3080 Ti
            if "3080" in gpu_name:
                print("  ✓ RTX 3080 Ti detected - optimal for this project!")
            
            # Test GPU computation
            print("\n  Testing GPU computation...")
            x = torch.randn(1000, 1000, device='cuda')
            y = torch.matmul(x, x)
            torch.cuda.synchronize()
            print("  ✓ GPU computation test passed")
            
            return True
        else:
            print("  ⚠ CUDA not available - will use CPU (slower)")
            return False
            
    except ImportError:
        print("  ✗ PyTorch not installed")
        return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def check_packages():
    """Check required packages."""
    print("\nChecking required packages...")
    
    packages = {
        'torch': 'PyTorch',
        'ultralytics': 'Ultralytics (YOLOv8)',
        'cv2': 'OpenCV',
        'numpy': 'NumPy',
        'roboflow': 'Roboflow',
        'yaml': 'PyYAML',
    }
    
    all_ok = True
    for module, name in packages.items():
        try:
            __import__(module)
            print(f"  ✓ {name}")
        except ImportError:
            print(f"  ✗ {name} - not installed")
            all_ok = False
    
    return all_ok


def check_video_capture():
    """Check video capture devices."""
    print("\nChecking video capture devices...")
    
    try:
        import cv2
        
        found_devices = []
        for i in range(5):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                backend = cap.getBackendName()
                
                print(f"  ✓ Device {i}: {width}x{height} @ {fps}fps ({backend})")
                found_devices.append({
                    'index': i,
                    'width': width,
                    'height': height,
                    'fps': fps,
                    'backend': backend
                })
                cap.release()
        
        if not found_devices:
            print("  ⚠ No video capture devices found")
            print("    - Check if your capture card is connected")
            print("    - On Linux, check /dev/video* devices")
            return False
        
        return True
        
    except ImportError:
        print("  ✗ OpenCV not installed")
        return False


def test_capture_card(device_index: int = 0):
    """
    Test video capture from analog capture card.
    
    Expected setup:
    - Skyzone Cobra X AV output → Analog capture card → USB → Laptop
    - Resolution should be 720x480 (NTSC) or 720x576 (PAL)
    """
    print(f"\nTesting capture card (device {device_index})...")
    
    try:
        import cv2
        import numpy as np
        
        # Try to open with V4L2 backend (Linux) or default
        backends = [cv2.CAP_V4L2, cv2.CAP_ANY]
        cap = None
        
        for backend in backends:
            cap = cv2.VideoCapture(device_index, backend)
            if cap.isOpened():
                break
        
        if not cap or not cap.isOpened():
            print(f"  ✗ Could not open device {device_index}")
            return False
        
        # Set expected resolution for analog video
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 720)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # Read test frames
        print("  Reading test frames...")
        frames_read = 0
        start_time = time.time()
        
        for _ in range(30):  # Read 30 frames
            ret, frame = cap.read()
            if ret:
                frames_read += 1
        
        elapsed = time.time() - start_time
        
        if frames_read > 0:
            actual_fps = frames_read / elapsed
            height, width = frame.shape[:2]
            
            print(f"  ✓ Capture working!")
            print(f"    Resolution: {width}x{height}")
            print(f"    Actual FPS: {actual_fps:.1f}")
            
            # Check if resolution matches expected analog video
            if width == 720 and height in [480, 576]:
                print(f"    ✓ Resolution matches analog video standard")
            else:
                print(f"    ⚠ Unexpected resolution - check capture settings")
            
            cap.release()
            return True
        else:
            print("  ✗ No frames captured")
            cap.release()
            return False
            
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_model_inference():
    """Test YOLOv8 model loading and inference."""
    print("\nTesting YOLOv8 inference...")
    
    try:
        from ultralytics import YOLO
        import numpy as np
        import torch
        
        # Load a small pretrained model for testing
        print("  Loading YOLOv8n model...")
        model = YOLO('yolov8n.pt')
        
        # Create test image
        test_img = np.random.randint(0, 255, (480, 720, 3), dtype=np.uint8)
        
        # Test inference
        print("  Running test inference...")
        device = '0' if torch.cuda.is_available() else 'cpu'
        
        # Warmup
        for _ in range(3):
            model.predict(test_img, device=device, verbose=False)
        
        # Benchmark
        times = []
        for _ in range(10):
            start = time.perf_counter()
            results = model.predict(test_img, device=device, verbose=False)
            times.append((time.perf_counter() - start) * 1000)
        
        avg_time = sum(times) / len(times)
        fps = 1000 / avg_time
        
        print(f"  ✓ Inference working!")
        print(f"    Device: {device}")
        print(f"    Average inference time: {avg_time:.1f}ms")
        print(f"    Estimated FPS: {fps:.1f}")
        
        if torch.cuda.is_available():
            # Test FP16
            print("\n  Testing FP16 inference...")
            times_fp16 = []
            for _ in range(10):
                start = time.perf_counter()
                model.predict(test_img, device=device, half=True, verbose=False)
                times_fp16.append((time.perf_counter() - start) * 1000)
            
            avg_time_fp16 = sum(times_fp16) / len(times_fp16)
            fps_fp16 = 1000 / avg_time_fp16
            speedup = avg_time / avg_time_fp16
            
            print(f"  ✓ FP16 inference working!")
            print(f"    Average inference time: {avg_time_fp16:.1f}ms")
            print(f"    Estimated FPS: {fps_fp16:.1f}")
            print(f"    Speedup vs FP32: {speedup:.2f}x")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def print_setup_guide():
    """Print hardware setup guide."""
    print("\n" + "="*60)
    print("HARDWARE SETUP GUIDE")
    print("="*60)
    print("""
Your FPV Setup:
--------------
1. Caddx Ratel Pro 1500TVL (on drone)
   - Analog camera, outputs CVBS video
   - Set to NTSC (720x480) or PAL (720x576)
   - 16:9 aspect ratio recommended
   - Transmits to 5.8GHz video transmitter

2. Skyzone Cobra X V4 (goggles)
   - Receives 5.8GHz analog video
   - Has AV OUTPUT (for sending to capture card)
   - HDMI port is INPUT only!
   
3. Getting Video to Laptop:
   - Use the AV OUTPUT from Cobra X goggles
   - Connect to an analog capture card:
     * EasyCap USB capture device (~$10-20)
     * Elgato Video Capture (~$100)
     * Any composite video to USB adapter
   - Expected resolution: 720x480 (NTSC) or 720x576 (PAL)

4. Alternative Setup (for simultaneous goggle use):
   - Add a dedicated 5.8GHz receiver module
   - Connect directly to capture card
   - This allows flying and capturing simultaneously

Connection Diagram:
------------------
Drone Camera → 5.8GHz TX → Air → 5.8GHz RX (Goggles)
                                      ↓
                              AV Output
                                      ↓
                           Analog Capture Card
                                      ↓
                              USB to Laptop
                                      ↓
                           YOLOv8 Inference
""")


def main():
    print("="*60)
    print("DRONE TRASH DETECTION - HARDWARE SETUP TEST")
    print("="*60)
    
    results = {}
    
    # Run all checks
    results['python'] = check_python_version()
    results['packages'] = check_packages()
    results['cuda'] = check_cuda()
    results['capture'] = check_video_capture()
    results['model'] = test_model_inference()
    
    # If capture card found, test it
    if results['capture']:
        results['capture_test'] = test_capture_card(0)
    
    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    all_passed = True
    for test, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {test}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n✓ All tests passed! Your system is ready.")
        print("\nNext steps:")
        print("1. Download your Roboflow dataset")
        print("2. Run: python train.py --api-key YOUR_API_KEY")
        print("3. Run: python inference.py --source 0 --weights best.pt")
    else:
        print("\n⚠ Some tests failed. Please review the issues above.")
        print_setup_guide()
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
