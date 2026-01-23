#!/usr/bin/env python3
"""
YOLOv8 Coral Edge TPU detector - saves detection video from Pi Camera
Usage: python3 coral_yolo_detector.py --model model_edgetpu.tflite --labels labels.txt
"""

import cv2
import numpy as np
from pycoral.utils.edgetpu import make_interpreter
from picamera2 import Picamera2
import argparse
import time


def load_model(model_path, labels_path):
    interpreter = make_interpreter(model_path)
    interpreter.allocate_tensors()
    
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    input_size = input_details[0]['shape'][1]
    input_dtype = input_details[0]['dtype']
    
    with open(labels_path) as f:
        labels = [line.strip() for line in f]
    
    print(f"Model: {model_path}")
    print(f"Input: {input_size}x{input_size} ({input_dtype})")
    print(f"Classes: {labels}")
    
    return interpreter, input_details, output_details, input_size, input_dtype, labels


def detect(frame, interpreter, input_details, output_details, input_size, input_dtype, labels, threshold):
    h, w = frame.shape[:2]
    
    # Preprocess
    img = cv2.resize(frame, (input_size, input_size))
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    if input_dtype == np.float32:
        img = img.astype(np.float32) / 255.0
    elif input_dtype == np.int8:
        img = img.astype(np.int8)
    else:
        img = img.astype(np.uint8)
    
    img = np.expand_dims(img, axis=0)
    
    # Inference
    interpreter.set_tensor(input_details[0]['index'], img)
    interpreter.invoke()
    output = interpreter.get_tensor(output_details[0]['index'])
    
    # Postprocess - VECTORIZED
    if output.shape[1] < output.shape[2]:
        output = output[0].T
    else:
        output = output[0]
    
    # Get confidence
    if output.shape[1] > 5:
        confs = np.max(output[:, 4:], axis=1)
        class_ids = np.argmax(output[:, 4:], axis=1)
    else:
        confs = output[:, 4]
        class_ids = np.zeros(len(confs), dtype=int)
    
    # Filter
    mask = confs > threshold
    if not np.any(mask):
        return []
    
    boxes = output[mask, :4]
    confs = confs[mask]
    class_ids = class_ids[mask]
    
    # Scale to frame size
    x, y, bw, bh = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
    scale = np.array([w, h, w, h]) / input_size
    x1 = np.clip(((x - bw/2) * scale[0]).astype(int), 0, w)
    y1 = np.clip(((y - bh/2) * scale[1]).astype(int), 0, h)
    x2 = np.clip(((x + bw/2) * scale[2]).astype(int), 0, w)
    y2 = np.clip(((y + bh/2) * scale[3]).astype(int), 0, h)
    
    # Top detections only
    indices = np.argsort(confs)[::-1][:20]
    
    return [{'bbox': [x1[i], y1[i], x2[i], y2[i]], 
             'conf': float(confs[i]),
             'label': labels[class_ids[i]] if class_ids[i] < len(labels) else str(class_ids[i])}
            for i in indices]


def draw(frame, detections, fps):
    for det in detections:
        x1, y1, x2, y2 = det['bbox']
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(frame, f"{det['label']}: {det['conf']:.2f}", (x1, y1 - 5), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    return frame


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', required=True)
    parser.add_argument('--labels', required=True)
    parser.add_argument('--threshold', type=float, default=0.25)
    parser.add_argument('--output', default='output.mp4')
    parser.add_argument('--duration', type=int, default=0)
    args = parser.parse_args()
    
    interpreter, input_details, output_details, input_size, input_dtype, labels = \
        load_model(args.model, args.labels)
    
    # Camera at 640x480 for speed
    camera = Picamera2()
    camera.configure(camera.create_preview_configuration(main={"size": (640, 480), "format": "RGB888"}))
    camera.start()
    print("Camera started (640x480)")
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(args.output, fourcc, 20.0, (640, 480))
    print(f"Recording to: {args.output}")
    print("Press Ctrl+C to stop")
    
    fps_history = []
    start_time = time.time()
    frame_count = 0
    
    try:
        while True:
            if args.duration > 0 and (time.time() - start_time) > args.duration:
                break
            
            frame = cv2.cvtColor(camera.capture_array(), cv2.COLOR_RGB2BGR)
            
            t0 = time.perf_counter()
            detections = detect(frame, interpreter, input_details, output_details, 
                              input_size, input_dtype, labels, args.threshold)
            dt = time.perf_counter() - t0
            
            fps_history.append(1.0 / dt)
            if len(fps_history) > 30:
                fps_history.pop(0)
            fps = sum(fps_history) / len(fps_history)
            
            out.write(draw(frame, detections, fps))
            
            frame_count += 1
            if frame_count % 30 == 0:
                print(f"Frame {frame_count} | FPS: {fps:.1f} | Detections: {len(detections)}")
                
    except KeyboardInterrupt:
        print("\nStopping...")
    
    camera.stop()
    out.release()
    print(f"\nSaved {frame_count} frames ({time.time() - start_time:.1f}s) to {args.output}")


if __name__ == "__main__":
    main()
