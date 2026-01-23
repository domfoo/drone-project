#!/usr/bin/env python3
"""
Video Capture Utilities for Drone FPV Systems

Handles video capture from various sources:
- Analog capture cards (AV input from Skyzone Cobra X)
- USB capture devices
- Video files for testing
- RTSP streams

Optimized for:
- Caddx Ratel Pro: NTSC (720x480) or PAL (720x576)
- Analog capture cards connected to Skyzone Cobra X AV output
"""

import cv2
import numpy as np
import time
import threading
from queue import Queue
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple, Generator
import platform


class VideoStandard(Enum):
    """Video standards for analog FPV systems."""
    NTSC = "ntsc"  # 720x480 @ 29.97fps
    PAL = "pal"    # 720x576 @ 25fps


@dataclass
class CaptureConfig:
    """Configuration for video capture."""
    # Resolution
    width: int = 720
    height: int = 480  # NTSC default, use 576 for PAL
    
    # Frame rate
    fps: int = 30
    
    # Video standard
    standard: VideoStandard = VideoStandard.NTSC
    
    # Buffer settings
    buffer_size: int = 2  # Small buffer for low latency
    
    # Backend preference
    backend: Optional[int] = None  # cv2.CAP_V4L2, cv2.CAP_DSHOW, etc.
    
    # Deinterlacing (analog video is typically interlaced)
    deinterlace: bool = True
    
    # Color correction for analog video
    color_correction: bool = True


class AnalogVideoCapture:
    """
    Video capture handler optimized for analog FPV systems.
    
    Handles the quirks of analog video capture:
    - Interlaced video deinterlacing
    - Color correction for analog artifacts
    - Low-latency buffering
    - Automatic reconnection
    """
    
    def __init__(
        self,
        source: int | str,
        config: Optional[CaptureConfig] = None
    ):
        """
        Initialize video capture.
        
        Args:
            source: Device index (int) or video file path (str)
            config: Capture configuration
        """
        self.source = source
        self.config = config or CaptureConfig()
        self.cap: Optional[cv2.VideoCapture] = None
        self.running = False
        self._frame_queue: Queue = Queue(maxsize=self.config.buffer_size)
        self._capture_thread: Optional[threading.Thread] = None
        
        # Performance metrics
        self._frame_count = 0
        self._start_time = 0
        self._fps_actual = 0
        
    def _get_backend(self) -> int:
        """Get the appropriate backend for the current platform."""
        if self.config.backend is not None:
            return self.config.backend
        
        system = platform.system()
        if system == "Linux":
            return cv2.CAP_V4L2
        elif system == "Windows":
            return cv2.CAP_DSHOW
        elif system == "Darwin":  # macOS
            return cv2.CAP_AVFOUNDATION
        else:
            return cv2.CAP_ANY
    
    def open(self) -> bool:
        """
        Open the video capture device.
        
        Returns:
            True if successful, False otherwise
        """
        backend = self._get_backend()
        
        if isinstance(self.source, int):
            self.cap = cv2.VideoCapture(self.source, backend)
        else:
            self.cap = cv2.VideoCapture(self.source)
        
        if not self.cap.isOpened():
            print(f"Error: Could not open video source: {self.source}")
            return False
        
        # Configure capture settings
        self._configure_capture()
        
        # Verify settings
        actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
        
        print(f"Video capture opened:")
        print(f"  Source: {self.source}")
        print(f"  Resolution: {actual_width}x{actual_height}")
        print(f"  FPS: {actual_fps}")
        print(f"  Backend: {backend}")
        
        return True
    
    def _configure_capture(self):
        """Configure capture device settings."""
        if self.cap is None:
            return
        
        # Set resolution
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.height)
        
        # Set frame rate
        self.cap.set(cv2.CAP_PROP_FPS, self.config.fps)
        
        # Minimize buffer for low latency
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        # For analog capture cards, try to set the video standard
        # Note: This may not work on all devices
        if self.config.standard == VideoStandard.NTSC:
            # NTSC standard code
            pass
        elif self.config.standard == VideoStandard.PAL:
            # PAL standard code
            pass
    
    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Read a single frame.
        
        Returns:
            Tuple of (success, frame)
        """
        if self.cap is None or not self.cap.isOpened():
            return False, None
        
        ret, frame = self.cap.read()
        
        if ret and frame is not None:
            # Apply processing
            frame = self._process_frame(frame)
            self._frame_count += 1
        
        return ret, frame
    
    def _process_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Process captured frame.
        
        Applies:
        - Deinterlacing
        - Color correction
        """
        # Deinterlace if enabled (simple bob deinterlacing)
        if self.config.deinterlace:
            frame = self._deinterlace(frame)
        
        # Color correction for analog video
        if self.config.color_correction:
            frame = self._correct_colors(frame)
        
        return frame
    
    def _deinterlace(self, frame: np.ndarray) -> np.ndarray:
        """
        Simple deinterlacing using bob method.
        
        For analog video which is typically interlaced.
        """
        # Simple bob deinterlace: interpolate between lines
        height = frame.shape[0]
        
        # Take every other line and resize back
        # This is a fast approximation - for better quality, use more
        # sophisticated methods like YADIF
        deinterlaced = cv2.resize(
            frame[::2],  # Take even lines
            (frame.shape[1], height),
            interpolation=cv2.INTER_LINEAR
        )
        
        return deinterlaced
    
    def _correct_colors(self, frame: np.ndarray) -> np.ndarray:
        """
        Apply color correction for analog video artifacts.
        
        Handles common analog issues like:
        - Color bleeding
        - Slight saturation issues
        """
        # Convert to LAB color space for better color correction
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        
        # Split channels
        l, a, b = cv2.split(lab)
        
        # Apply CLAHE to L channel for better contrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        
        # Merge and convert back
        lab = cv2.merge([l, a, b])
        corrected = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        
        return corrected
    
    def start_async(self):
        """Start asynchronous capture in a separate thread."""
        if self.running:
            return
        
        if not self.open():
            raise RuntimeError("Failed to open video capture")
        
        self.running = True
        self._start_time = time.time()
        self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._capture_thread.start()
        
        print("Async capture started")
    
    def _capture_loop(self):
        """Continuous capture loop for async mode."""
        while self.running:
            ret, frame = self.read()
            
            if ret and frame is not None:
                # Drop old frames if queue is full (keeps latency low)
                if self._frame_queue.full():
                    try:
                        self._frame_queue.get_nowait()
                    except:
                        pass
                
                self._frame_queue.put(frame)
            else:
                # Small sleep on failure to prevent busy loop
                time.sleep(0.001)
    
    def get_frame(self, timeout: float = 1.0) -> Optional[np.ndarray]:
        """
        Get the latest frame from async capture.
        
        Args:
            timeout: Maximum time to wait for a frame
            
        Returns:
            Frame if available, None otherwise
        """
        try:
            return self._frame_queue.get(timeout=timeout)
        except:
            return None
    
    def get_fps(self) -> float:
        """Get actual capture FPS."""
        if self._start_time == 0:
            return 0
        
        elapsed = time.time() - self._start_time
        if elapsed > 0:
            return self._frame_count / elapsed
        return 0
    
    def stop(self):
        """Stop capture and release resources."""
        self.running = False
        
        if self._capture_thread is not None:
            self._capture_thread.join(timeout=1.0)
            self._capture_thread = None
        
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        
        print("Capture stopped")
    
    def __enter__(self):
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


def create_capture_for_fpv_setup(
    device: int = 0,
    standard: str = "ntsc"
) -> AnalogVideoCapture:
    """
    Create a capture instance optimized for the Caddx Ratel Pro + Skyzone Cobra X setup.
    
    Args:
        device: Video device index
        standard: Video standard ("ntsc" or "pal")
        
    Returns:
        Configured AnalogVideoCapture instance
    """
    if standard.lower() == "ntsc":
        config = CaptureConfig(
            width=720,
            height=480,
            fps=30,
            standard=VideoStandard.NTSC,
            deinterlace=True,
            color_correction=True
        )
    else:  # PAL
        config = CaptureConfig(
            width=720,
            height=576,
            fps=25,
            standard=VideoStandard.PAL,
            deinterlace=True,
            color_correction=True
        )
    
    return AnalogVideoCapture(device, config)


def list_capture_devices():
    """List available video capture devices."""
    print("Scanning for video capture devices...")
    
    available = []
    for i in range(10):  # Check first 10 indices
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            backend = cap.getBackendName()
            
            print(f"  Device {i}: {width}x{height} @ {fps}fps ({backend})")
            available.append(i)
            cap.release()
    
    if not available:
        print("  No devices found")
    
    return available


# Frame generator for easy iteration
def frame_generator(
    source: int | str,
    config: Optional[CaptureConfig] = None
) -> Generator[np.ndarray, None, None]:
    """
    Generator that yields frames from video source.
    
    Usage:
        for frame in frame_generator(0):
            # process frame
    """
    capture = AnalogVideoCapture(source, config)
    
    try:
        if not capture.open():
            return
        
        while True:
            ret, frame = capture.read()
            if not ret:
                break
            yield frame
    finally:
        capture.stop()


if __name__ == "__main__":
    # Test capture
    print("Video Capture Test")
    print("=" * 40)
    
    # List devices
    devices = list_capture_devices()
    
    if devices:
        print(f"\nTesting device {devices[0]}...")
        
        capture = create_capture_for_fpv_setup(devices[0], "ntsc")
        
        with capture:
            frame_count = 0
            start = time.time()
            
            while frame_count < 100:
                ret, frame = capture.read()
                if ret:
                    frame_count += 1
                    
                    # Display frame
                    cv2.imshow("Capture Test", frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
            
            elapsed = time.time() - start
            print(f"\nCaptured {frame_count} frames in {elapsed:.2f}s")
            print(f"Average FPS: {frame_count/elapsed:.1f}")
        
        cv2.destroyAllWindows()
