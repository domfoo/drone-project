#!/usr/bin/env python3
"""
Real-time YOLOv8 Inference for Drone Trash Detection

Processes video stream from Skyzone Cobra X (via analog capture card)
and runs YOLOv8 detection in real-time.

Usage:
    # From capture card
    python inference.py --source 0 --weights best.pt
    
    # From video file
    python inference.py --source video.mp4 --weights best.pt
    
    # With custom settings
    python inference.py --source 0 --weights best.pt --conf 0.5 --imgsz 640
"""

import os
import sys
import argparse
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, List
from dataclasses import dataclass

import cv2
import numpy as np
import torch
import yaml

from ultralytics import YOLO
from capture_utils import (
    AnalogVideoCapture, 
    CaptureConfig, 
    VideoStandard,
    create_capture_for_fpv_setup
)

from threading import Thread
from remote_communication.mission_controller import handle_detection, process_keypress, trigger_drone_action

@dataclass
class DetectionResult:
    """Container for detection results."""
    boxes: np.ndarray  # [x1, y1, x2, y2]
    confidences: np.ndarray
    class_ids: np.ndarray
    class_names: List[str]


class TrashDetector:
    """
    Real-time trash detection using YOLOv8.
    
    Optimized for:
    - RTX 3080 Ti inference
    - Analog FPV video input (720x480 NTSC)
    - Low-latency detection
    """
    
    def __init__(
        self,
        weights_path: str,
        conf_threshold: float = 0.5,
        iou_threshold: float = 0.45,
        imgsz: int = 640,
        device: str = "0",
        half: bool = True
    ):
        """
        Initialize the trash detector.
        
        Args:
            weights_path: Path to YOLOv8 weights file
            conf_threshold: Confidence threshold for detections
            iou_threshold: IOU threshold for NMS
            imgsz: Model input size
            device: Device to run on ("0" for GPU, "cpu" for CPU)
            half: Use FP16 inference (faster on GPU)
        """
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.imgsz = imgsz
        self.device = device
        self.half = half
        
        # Performance tracking
        self.inference_times = []
        
        # Load model
        print(f"Loading model from: {weights_path}")
        self.model = YOLO(weights_path)
        
        # Warm up model
        self._warmup()
        
        print(f"Model loaded successfully")
        print(f"  Classes: {self.model.names}")
        print(f"  Device: {self.device}")
        print(f"  FP16: {self.half}")
    
    def _warmup(self, iterations: int = 3):
        """Warm up the model with dummy inference."""
        print("Warming up model...")
        dummy = np.zeros((self.imgsz, self.imgsz, 3), dtype=np.uint8)
        
        for _ in range(iterations):
            self.model.predict(
                dummy,
                conf=self.conf_threshold,
                iou=self.iou_threshold,
                device=self.device,
                half=self.half,
                verbose=False
            )
        
        print("Model warmed up")
    
    def detect(self, frame: np.ndarray) -> Tuple[DetectionResult, float]:
        """
        Run detection on a single frame.
        
        Args:
            frame: BGR image as numpy array
            
        Returns:
            Tuple of (DetectionResult, inference_time_ms)
        """
        start_time = time.perf_counter()
        
        # Run inference
        results = self.model.predict(
            frame,
            conf=self.conf_threshold,
            iou=self.iou_threshold,
            imgsz=self.imgsz,
            device=self.device,
            half=self.half,
            verbose=False
        )[0]
        
        inference_time = (time.perf_counter() - start_time) * 1000
        self.inference_times.append(inference_time)
        
        # Extract results
        boxes = results.boxes.xyxy.cpu().numpy() if len(results.boxes) > 0 else np.array([])
        confidences = results.boxes.conf.cpu().numpy() if len(results.boxes) > 0 else np.array([])
        class_ids = results.boxes.cls.cpu().numpy().astype(int) if len(results.boxes) > 0 else np.array([])
        class_names = [self.model.names[cid] for cid in class_ids]
        
        detection_result = DetectionResult(
            boxes=boxes,
            confidences=confidences,
            class_ids=class_ids,
            class_names=class_names
        )
        
        return detection_result, inference_time
    
    def draw_detections(
        self,
        frame: np.ndarray,
        detections: DetectionResult,
        inference_time: float,
        show_fps: bool = True
    ) -> np.ndarray:
        """
        Draw detection boxes and labels on frame.
        
        Args:
            frame: Original frame
            detections: Detection results
            inference_time: Time taken for inference (ms)
            show_fps: Whether to show FPS counter
            
        Returns:
            Annotated frame
        """
        annotated = frame.copy()
        
        # Color palette for classes
        colors = [
            (0, 255, 0),    # Green
            (255, 0, 0),    # Blue
            (0, 0, 255),    # Red
            (255, 255, 0),  # Cyan
            (255, 0, 255),  # Magenta
            (0, 255, 255),  # Yellow
        ]
        
        # Draw detections
        for i, (box, conf, class_name) in enumerate(zip(
            detections.boxes, 
            detections.confidences, 
            detections.class_names
        )):
            x1, y1, x2, y2 = map(int, box)
            color = colors[i % len(colors)]
            
            # Draw box
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            
            # Draw label background
            label = f"{class_name}: {conf:.2f}"
            (label_w, label_h), baseline = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
            )
            cv2.rectangle(
                annotated,
                (x1, y1 - label_h - 10),
                (x1 + label_w, y1),
                color,
                -1
            )
            
            # Draw label text
            cv2.putText(
                annotated,
                label,
                (x1, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1
            )
        
        # Draw FPS and info
        if show_fps:
            fps = 1000 / inference_time if inference_time > 0 else 0
            info_text = f"FPS: {fps:.1f} | Detections: {len(detections.boxes)}"
            
            cv2.putText(
                annotated,
                info_text,
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )
            
            # Draw inference time
            cv2.putText(
                annotated,
                f"Inference: {inference_time:.1f}ms",
                (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2
            )
        
        return annotated
    
    def get_average_inference_time(self) -> float:
        """Get average inference time in ms."""
        if not self.inference_times:
            return 0
        return sum(self.inference_times[-100:]) / len(self.inference_times[-100:])


class MissionController:
    # Bridges inference detections + keyboard control to the Raspberry Pi

    def __init__(self, enabled: bool, cooldown_s: float = 10.0):
        self.enabled = enabled
        self.cooldown_s = cooldown_s
        self._last_trigger_ts: float = 0.0
        self._in_progress = False

    def process_key(self, key: int) -> bool:
        # Returns False to stop the main loop
        if not self.enabled:
            return True
        if key == 255:  # no key pressed
            return True
        return process_keypress(key)

    def maybe_trigger_detection(self, detections: DetectionResult) -> None:
        if not self.enabled:
            return
        if self._in_progress:
            return
        if detections.boxes is None or len(detections.boxes) == 0:
            return

        now = time.time()
        if now - self._last_trigger_ts < self.cooldown_s:
            return

        print(f"[MISSION] Checking detection: {str(detections)}")

        # Only trigger if the detection is a trash can
        if detections.class_names[0] != "trash":
            return

        self._last_trigger_ts = now
        self._in_progress = True

        def _run() -> None:
            try:
                handle_detection()
            finally:
                self._in_progress = False

        Thread(target=_run, daemon=True).start()

    def disarm_on_exit(self) -> None:
        if not self.enabled:
            return
        try:
            trigger_drone_action("q")
        except Exception:
            # Best-effort only; avoid masking main shutdown.
            return


def run_inference(
    source: int | str,
    weights: str,
    conf: float = 0.5,
    iou: float = 0.45,
    imgsz: int = 640,
    device: str = "0",
    half: bool = True,
    show: bool = True,
    save: bool = False,
    save_dir: str = "runs/detect/inference",
    video_standard: str = "ntsc",
    mission: bool = True,
    mission_cooldown_s: float = 10.0,
):
    """
    Run real-time inference on video source.
    
    Args:
        source: Video source (device index or file path)
        weights: Path to model weights
        conf: Confidence threshold
        iou: IOU threshold
        imgsz: Model input size
        device: Device to use
        half: Use FP16 inference
        show: Show output window
        save: Save output video
        save_dir: Directory to save output
        video_standard: "ntsc" or "pal" for capture card
    """
    # Initialize detector
    detector = TrashDetector(
        weights_path=weights,
        conf_threshold=conf,
        iou_threshold=iou,
        imgsz=imgsz,
        device=device,
        half=half
    )
    
    # Initialize video capture
    if isinstance(source, int) or (isinstance(source, str) and source.isdigit()):
        # Capture device - use FPV-optimized capture
        source_idx = int(source) if isinstance(source, str) else source
        capture = create_capture_for_fpv_setup(source_idx, video_standard)
    else:
        # Video file
        capture = AnalogVideoCapture(source)
    
    if not capture.open():
        print(f"Error: Could not open video source: {source}")
        return
    
    # Setup video writer for saving
    video_writer = None
    if save:
        os.makedirs(save_dir, exist_ok=True)
        output_path = os.path.join(save_dir, f"detection.mp4")
        
        # Get frame dimensions
        ret, test_frame = capture.read()
        if ret:
            h, w = test_frame.shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            video_writer = cv2.VideoWriter(output_path, fourcc, 30, (w, h))
            print(f"Saving output to: {output_path}")
    
    print(f"\n{'='*60}")
    print("Starting real-time inference")
    print(f"{'='*60}")
    print(f"Source: {source}")
    print(f"Model: {weights}")
    print("CONTROLS:")
    print("  'p'=Screenshot | 'x'=Exit")
    print("  Mission keys: 'a'=Arm | 'q'=Disarm | 's'=Servo | 'b'=Brake | 'j'=Stab | 'k'=Auto | 'l'=RTL")
    print()
    
    frame_count = 0
    start_time = time.time()
    mission_controller = MissionController(enabled=mission, cooldown_s=mission_cooldown_s)
    
    try:
        while True:
            # Read frame
            ret, frame = capture.read()
            if not ret:
                if isinstance(source, str) and not source.isdigit():
                    print("End of video file")
                    break
                continue
            
            # Run detection
            detections, inference_time = detector.detect(frame)
            
            # Draw results
            annotated = detector.draw_detections(frame, detections, inference_time)
            
            # Save if enabled
            if video_writer is not None:
                video_writer.write(annotated)
            
            # Display
            if show:
                cv2.imshow("Drone Trash Detection", annotated)
                
                key = cv2.waitKey(1) & 0xFF
                if key == ord("p"):
                    # Save screenshot
                    screenshot_path = f"{save_dir}/screenshots/screenshot_{frame_count}.jpg"
                    cv2.imwrite(screenshot_path, annotated)
                    print(f"Screenshot saved: {screenshot_path}")
                elif not mission_controller.process_key(key):
                    break
            
            frame_count += 1
            
            # Print periodic stats
            if frame_count % 100 == 0:
                elapsed = time.time() - start_time
                fps = frame_count / elapsed
                avg_inference = detector.get_average_inference_time()
                print(f"Frames: {frame_count} | FPS: {fps:.1f} | Avg inference: {avg_inference:.1f}ms")

            # Auto-trigger mission when detections appear
            mission_controller.maybe_trigger_detection(detections)
    
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    
    finally:
        # Cleanup
        mission_controller.disarm_on_exit()
        capture.stop()
        if video_writer is not None:
            video_writer.release()
        cv2.destroyAllWindows()
        
        # Print final stats
        elapsed = time.time() - start_time
        print(f"\n{'='*60}")
        print("Inference Complete")
        print(f"{'='*60}")
        print(f"Total frames: {frame_count}")
        print(f"Total time: {elapsed:.1f}s")
        print(f"Average FPS: {frame_count/elapsed:.1f}")
        print(f"Average inference time: {detector.get_average_inference_time():.1f}ms")


def benchmark(weights: str, imgsz: int = 640, device: str = "0"):
    """
    Benchmark model performance.
    
    Tests inference speed at various resolutions and batch sizes.
    """
    print(f"\n{'='*60}")
    print("Running Benchmark")
    print(f"{'='*60}")
    
    model = YOLO(weights)
    
    # Test resolutions
    resolutions = [320, 480, 640, 720]
    
    print(f"\nModel: {weights}")
    print(f"Device: {device}")
    print(f"\n{'Resolution':<12} {'FP32 (ms)':<12} {'FP16 (ms)':<12} {'FPS (FP16)':<12}")
    print("-" * 48)
    
    for res in resolutions:
        # Create test image
        test_img = np.random.randint(0, 255, (res, res, 3), dtype=np.uint8)
        
        # FP32 inference
        times_fp32 = []
        for _ in range(20):
            start = time.perf_counter()
            model.predict(test_img, imgsz=res, device=device, half=False, verbose=False)
            times_fp32.append((time.perf_counter() - start) * 1000)
        avg_fp32 = sum(times_fp32[5:]) / len(times_fp32[5:])  # Skip warmup
        
        # FP16 inference
        times_fp16 = []
        for _ in range(20):
            start = time.perf_counter()
            model.predict(test_img, imgsz=res, device=device, half=True, verbose=False)
            times_fp16.append((time.perf_counter() - start) * 1000)
        avg_fp16 = sum(times_fp16[5:]) / len(times_fp16[5:])  # Skip warmup
        
        fps_fp16 = 1000 / avg_fp16
        
        print(f"{res}x{res:<6} {avg_fp32:<12.1f} {avg_fp16:<12.1f} {fps_fp16:<12.1f}")
    
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Real-time Drone Trash Detection with YOLOv8"
    )
    
    # Required arguments
    parser.add_argument(
        "--weights", "-w",
        type=str,
        required=True,
        help="Path to model weights"
    )
    
    # Source options
    parser.add_argument(
        "--source", "-s",
        type=str,
        default="0",
        help="Video source (device index or file path)"
    )
    
    # Model options
    parser.add_argument(
        "--conf",
        type=float,
        default=0.5,
        help="Confidence threshold (default: 0.5)"
    )
    parser.add_argument(
        "--iou",
        type=float,
        default=0.45,
        help="IOU threshold for NMS (default: 0.45)"
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        default=640,
        help="Model input size (default: 640)"
    )
    
    # Device options
    parser.add_argument(
        "--device",
        type=str,
        default="0",
        help="Device to use (0 for GPU, cpu for CPU)"
    )
    parser.add_argument(
        "--half",
        action="store_true",
        default=True,
        help="Use FP16 inference (default: True)"
    )
    parser.add_argument(
        "--no-half",
        action="store_true",
        help="Disable FP16 inference"
    )
    
    # Video options
    parser.add_argument(
        "--video-standard",
        type=str,
        choices=["ntsc", "pal"],
        default="ntsc",
        help="Video standard for capture card (default: ntsc)"
    )
    
    # Output options
    parser.add_argument(
        "--show",
        action="store_true",
        default=True,
        help="Show output window (default: True)"
    )
    parser.add_argument(
        "--no-show",
        action="store_true",
        help="Don't show output window"
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save output video"
    )
    parser.add_argument(
        "--save-dir",
        type=str,
        default="runs/detect/inference",
        help="Directory to save output"
    )
    
    # Benchmark mode
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Run benchmark instead of inference"
    )

    # Mission / Raspberry Pi bridge options
    parser.add_argument(
        "--no-mission",
        action="store_true",
        help="Disable Raspberry Pi mission bridge (default: enabled)"
    )
    parser.add_argument(
        "--mission-cooldown-s",
        type=float,
        default=5.0,
        help="Cooldown between auto-triggers in seconds (default: 5)"
    )
    
    args = parser.parse_args()
    
    # Handle boolean flags
    use_half = args.half and not args.no_half
    show_output = args.show and not args.no_show

    # Name save_dit based on start timestamp
    save_dir = args.save_dir or "runs/detect/inference_{}".format(datetime.now().strftime('%Y%m%d_%H%M%S'))
    
    if args.benchmark:
        benchmark(args.weights, args.imgsz, args.device)
    else:
        run_inference(
            source=args.source,
            weights=args.weights,
            conf=args.conf,
            iou=args.iou,
            imgsz=args.imgsz,
            device=args.device,
            half=use_half,
            show=show_output,
            save=args.save,
            save_dir=save_dir,
            video_standard=args.video_standard,
            mission=(not args.no_mission),
            mission_cooldown_s=args.mission_cooldown_s,
        )


if __name__ == "__main__":
    main()
