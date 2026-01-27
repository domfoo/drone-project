#!/usr/bin/env python3
"""
YOLOv8 Training and Edge TPU Export Script
Trains a YOLOv8 model for dumpsite detection and exports it for Coral Edge TPU deployment.
"""

import os
import yaml
import glob
import numpy as np
from pathlib import Path
from PIL import Image
import torch
from ultralytics import YOLO
from roboflow import Roboflow
import tensorflow as tf
import warnings

warnings.filterwarnings('ignore')

# =============================================================================
# Environment Info
# =============================================================================
print(f"Python version: {os.sys.version}")
print(f"TensorFlow version: {tf.__version__}")
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")

# =============================================================================
# Configuration
# =============================================================================
ROBOFLOW_API_KEY = '5hjb3rLQ4gG1SyRaOorf'
WORKSPACE = "drone-ihemm"
PROJECT = "dumpsite-detection-vynfo-usuq1"
VERSION = 2

EPOCHS = 100
BATCH_SIZE = 8
IMAGE_SIZE = 320  # Using 320x320 for Edge TPU compatibility
MODEL_NAME = 'yolov8n'
PATIENCE = 20
CONFIDENCE_THRESHOLD = 0.25

# =============================================================================
# Dataset Download
# =============================================================================
print("\n" + "="*50)
print("Downloading Dataset")
print("="*50)

                
rf = Roboflow(api_key=ROBOFLOW_API_KEY)
project = rf.workspace(WORKSPACE).project(PROJECT)
version = project.version(VERSION)
dataset = version.download("yolov8")

print(f"Dataset downloaded to: {dataset.location}")

# Display dataset information
with open(f"{dataset.location}/data.yaml", 'r') as f:
    data_config = yaml.safe_load(f)

print(f"\nDataset Statistics:")
print(f"  Number of classes: {data_config['nc']}")
print(f"  Classes: {data_config['names']}")

# Count images
train_images_count = len(glob.glob(os.path.join(dataset.location, 'train', 'images', '*')))
valid_images_count = len(glob.glob(os.path.join(dataset.location, 'valid', 'images', '*')))
test_images_count = len(glob.glob(os.path.join(dataset.location, 'test', 'images', '*'))) if os.path.exists(os.path.join(dataset.location, 'test')) else 0

print(f"\nDataset splits:")
print(f"  Training images: {train_images_count}")
print(f"  Validation images: {valid_images_count}")
print(f"  Test images: {test_images_count}")

# Check sample image dimensions
sample_images = glob.glob(os.path.join(dataset.location, 'train', 'images', '*'))[:5]
print("\nSample image dimensions:")
for img_path in sample_images:
    img = Image.open(img_path)
    print(f"  {os.path.basename(img_path)}: {img.size}")

# =============================================================================
# Update data.yaml with absolute paths
# =============================================================================
data_yaml_path = f"{dataset.location}/data.yaml"

with open(data_yaml_path, 'r') as f:
    data = yaml.safe_load(f)

num_classes = data['nc']
class_names = data['names']

data['path'] = dataset.location
data['train'] = 'train/images'
data['val'] = 'valid/images'
data['test'] = 'test/images' if os.path.exists(os.path.join(dataset.location, 'test')) else 'valid/images'

with open(data_yaml_path, 'w') as f:
    yaml.dump(data, f, default_flow_style=False)

print(f"\nUpdated data.yaml:")
print(f"  Path: {data['path']}")
print(f"  Train: {data['train']}")
print(f"  Val: {data['val']}")
print(f"  Test: {data['test']}")

# =============================================================================
# Training
# =============================================================================
print("\n" + "="*50)
print("Training Configuration")
print("="*50)
print(f"  Model: {MODEL_NAME}")
print(f"  Image size: {IMAGE_SIZE}x{IMAGE_SIZE}")
print(f"  Batch size: {BATCH_SIZE}")
print(f"  Epochs: {EPOCHS}")
print(f"  Early stopping patience: {PATIENCE}")
print(f"  Number of classes: {num_classes}")

model = YOLO(f'{MODEL_NAME}.pt')

print("\nStarting training...")
train_results = model.train(
    data=data_yaml_path,
    epochs=EPOCHS,
    imgsz=IMAGE_SIZE,
    batch=BATCH_SIZE,
    patience=PATIENCE,
    device=0 if torch.cuda.is_available() else 'cpu',
    project='yolo_coral_training',
    name=f'run_{IMAGE_SIZE}',
    exist_ok=True,
    pretrained=True,
    optimizer='Adam',
    lr0=0.001,
    lrf=0.01,
    momentum=0.937,
    weight_decay=0.0005,
    warmup_epochs=3,
    warmup_momentum=0.8,
    warmup_bias_lr=0.1,
    box=0.05,
    cls=0.5,
    dfl=1.5,
    close_mosaic=10,
    amp=True,
    seed=42,
    verbose=True,
    save=True,
    save_period=10
)

print("\nTraining completed!")
print(f"Results saved to: {train_results.save_dir}")

# =============================================================================
# Validation
# =============================================================================
print("\n" + "="*50)
print("Validation")
print("="*50)

best_model_path = os.path.join(train_results.save_dir, 'weights', 'best.pt')
best_model = YOLO(best_model_path)
print(f"Loaded best model from: {best_model_path}")

metrics = best_model.val(
    data=data_yaml_path,
    imgsz=IMAGE_SIZE,
    batch=BATCH_SIZE,
    conf=CONFIDENCE_THRESHOLD
)

print("\nValidation Metrics:")
print(f"  mAP@0.5: {metrics.box.map50:.3f}")
print(f"  mAP@0.5:0.95: {metrics.box.map:.3f}")
print(f"  Precision: {metrics.box.mp:.3f}")
print(f"  Recall: {metrics.box.mr:.3f}")

if hasattr(metrics.box, 'ap_class_index'):
    print("\nPer-class mAP@0.5:")
    for idx in metrics.box.ap_class_index:
        class_name = class_names[idx]
        map50 = metrics.box.ap50[idx]
        print(f"  {class_name}: {map50:.3f}")

# =============================================================================
# Sample Inference
# =============================================================================
print("\n" + "="*50)
print("Sample Inference")
print("="*50)

test_images_dir = os.path.join(dataset.location, 'test', 'images')
if not os.path.exists(test_images_dir):
    test_images_dir = os.path.join(dataset.location, 'valid', 'images')

test_images = glob.glob(os.path.join(test_images_dir, '*'))[:3]

print("Running inference on sample images...")
for img_path in test_images:
    pred_results = best_model.predict(
        source=img_path,
        imgsz=IMAGE_SIZE,
        conf=CONFIDENCE_THRESHOLD,
        save=True,
        project='test_predictions',
        name='sample',
        exist_ok=True
    )

    for r in pred_results:
        if len(r.boxes) > 0:
            print(f"\n{os.path.basename(img_path)}:")
            for box in r.boxes:
                class_id = int(box.cls)
                confidence = float(box.conf)
                class_name = class_names[class_id]
                print(f"  - {class_name}: {confidence:.2%}")
        else:
            print(f"{os.path.basename(img_path)}: No detections")

print("\nPredictions saved to: test_predictions/")

# =============================================================================
# Export to Edge TPU
# =============================================================================
print("\n" + "="*50)
print("Exporting for Edge TPU")
print("="*50)

print(f"Exporting model with format='edgetpu' at {IMAGE_SIZE}x{IMAGE_SIZE}...")

# Export directly to Edge TPU format - this handles TFLite conversion and
# Edge TPU compilation in one step
best_model.export(
    format='edgetpu',
    imgsz=IMAGE_SIZE,
    data=data_yaml_path
)

# Find the exported Edge TPU model
edgetpu_model_path = None
search_paths = [
    os.path.join(train_results.save_dir, 'weights', 'best_full_integer_quant_edgetpu.tflite'),
    os.path.join(train_results.save_dir, 'weights', 'best_int8_edgetpu.tflite'),
    os.path.join(train_results.save_dir, 'weights', 'best_edgetpu.tflite'),
]

for path in search_paths:
    if os.path.exists(path):
        edgetpu_model_path = path
        break

# If not found in expected locations, search recursively
if not edgetpu_model_path:
    edgetpu_files = glob.glob(os.path.join(train_results.save_dir, '**', '*_edgetpu.tflite'), recursive=True)
    if edgetpu_files:
        edgetpu_model_path = edgetpu_files[0]

if edgetpu_model_path:
    model_size = os.path.getsize(edgetpu_model_path) / (1024 * 1024)
    print(f"\nEdge TPU model exported: {edgetpu_model_path}")
    print(f"Model size: {model_size:.2f} MB")

    # Copy to a convenient location
    os.makedirs('edge_tpu_models', exist_ok=True)
    import shutil
    dest_path = os.path.join('edge_tpu_models', os.path.basename(edgetpu_model_path))
    shutil.copy2(edgetpu_model_path, dest_path)
    print(f"Copied to: {dest_path}")
else:
    print("\nWarning: Edge TPU model not found at expected locations")
    print("Searching for any exported files...")
    tflite_files = glob.glob(os.path.join(train_results.save_dir, '**', '*.tflite'), recursive=True)
    if tflite_files:
        print("Found TFLite files:")
        for f in tflite_files:
            size = os.path.getsize(f) / (1024 * 1024)
            print(f"  {f} ({size:.2f} MB)")

# =============================================================================
# Create labels.txt
# =============================================================================
print("\n" + "="*50)
print("Creating Deployment Files")
print("="*50)

labels_path = 'labels.txt'
with open(labels_path, 'w') as f:
    for name in class_names:
        f.write(f"{name}\n")

print(f"Labels file created: {labels_path}")
print("Classes:")
for i, name in enumerate(class_names):
    print(f"  {i}: {name}")

# Also save to edge_tpu_models directory
os.makedirs('edge_tpu_models', exist_ok=True)
with open('edge_tpu_models/labels.txt', 'w') as f:
    for name in class_names:
        f.write(f"{name}\n")

# =============================================================================
# Summary
# =============================================================================
print("\n" + "="*50)
print("Training Complete - Summary")
print("="*50)
print(f"Training results: {train_results.save_dir}")
print(f"Best PyTorch model: {best_model_path}")
print(f"Edge TPU model: {edgetpu_model_path or 'See above for available files'}")
print(f"Labels file: {labels_path}")
print(f"\nModel trained at {IMAGE_SIZE}x{IMAGE_SIZE} for optimal Edge TPU performance")
print("\nFor Raspberry Pi deployment, copy to your Pi:")
print("  1. The *_edgetpu.tflite model from edge_tpu_models/")
print("  2. labels.txt (also in edge_tpu_models/)")
print("  3. coral_yolo_detector.py")
print("  4. Run install_raspberry_pi.sh to set up dependencies")
