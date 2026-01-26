---
layout: default
title: AI Application
---

# AI Application

## Overview
WasteWing uses an AI system designed to detect illegal dumpsites from the drone's camera perspective.
The AI component is based on a YOLOv8 object detection model.

## Dataset
The model was trained using the Dumpsite Detection Dataset [1].

### Dataset Characteristics:
- Aerial images of waste and dumpsites
- Annotated bounding boxes for dumpsite regions
- Designed for object detection tasks
- Includes variation in scale, terrain, and lighting conditions


## Training
The model can be trained using the `yolo` command line application from ultralytics like so:

```bash
yolo detect train model=yolov8n.pt data=data.yaml epochs=100 name=yolov8n_waste
```

## Inference
1. Drone camera captures live frames
2. Frames are sent to a local computer with the YOLOv8 model
3. YOLOv8 model performs inference
4. Dumpsite detections are returned with:
   - Bounding box coordinates
   - Confidence score
5. Results are processed and appropriate drone action commands are passed back to the drone

A processed frame might look like this:
![](/assets/val_batch2_pred.jpg)


## Deployment
- Runs on edge hardware onboard the drone
- Supports real-time detection during flight
- Can operate offline once deployed

## Limitations
- Detection accuracy depends on altitude and image clarity
- Performance may degrade in extreme weather or low visibility

## Dataset Reference

[1] Dumpsite Detection Dataset.  
Work. *Roboflow Universe*, 2025.  
Available at: https://universe.roboflow.com/work-0sor9/dumpsite-detection-vynfo  
(Accessed: 2026-01-26)
