# Drone Project - AI-Powered Trash Detection

A real-time object detection system for drones using YOLOv8, developed as part of the **Drohnen mit Künstlicher Intelligenz** module (Master-Projekt - Studienfeld Intelligente Systeme, WS2526) at Frankfurt University of Applied Sciences.

## Team Members

- Nhat Khanh Hoang
- Dominik Bartsch
- Gajus

## Project Overview

This project implements a real-time trash detection system for drones using YOLOv8. The system processes video streams from drone cameras and communicates with the drone's flight controller via a Raspberry Pi bridge.

## Key Files

- **`inference.py`** - Main script for running the YOLOv8 model inference on video streams
- **`real_mission.py`** - Handles communication between the local computer and the drone through Raspberry Pi (UDP-based)
- **`yolov8n.pt`** - Pre-trained YOLOv8 model weights file

## Basic Usage

### Prerequisites

1. Ensure your computer and Raspberry Pi are connected to the same network
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Model

Run the inference script with the model weights:

```bash
python inference.py -w yolov8n.pt -s 1 --show
```

**Parameters:**
- `-w` / `--weights`: Path to the model weights file (e.g., `yolov8n.pt`)
- `-s` / `--source`: Video source (0 for webcam, 1 for capture card, or path to video file)
- `--show`: Display the detection results in real-time

### Additional Options

For more advanced usage, see the help menu:

```bash
python inference.py --help
```

## Requirements

See `requirements.txt` for the complete list of dependencies. Main requirements include:
- Ultralytics YOLOv8
- PyTorch
- OpenCV
- NumPy

## Architecture

The system consists of:
1. **Local Computer**: Runs YOLOv8 inference on video streams
2. **Raspberry Pi**: Acts as a bridge for UDP communication with the drone's flight controller
3. **Drone**: Receives commands based on detection results

## License

See `LICENSE` file for details.
