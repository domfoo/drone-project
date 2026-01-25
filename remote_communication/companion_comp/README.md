# REMOTE COMMUNICATION USING COMPANION COMPUTER (RASPBERRY PI)

## 1. System Architecture
The system uses a decoupled architecture to ensure the Raspberry Pi's CPU remains free for hardware tasks while the MacBook handles heavy AI processing

* **Local Computer:** Runs the AI detection model (`inference.py`) and transmits commands via UDP using Netcat (nc). The `MissionController` class bridges inference detections + keyboard control to the Raspberry Pi
* **Raspberry Pi:** Receives network packets via `drone_control_listener.py`, maintains a MAVLink heartbeat with the FC, bridges signals from Local Computer to Flight Controller and controls the servo via GPIO
* **Flight Controller:** Executes signals for flight modes (Brake, Auto, RTL) and motor arming

## 2. First-Time Setup

### MacBook Configuration

* Dependencies: Install OpenCV and ensure nc is available in your terminal

### Raspberry Pi Configuration

* Bridge Script: Save `drone_control_listener.py` to `/home/tpu/`
* Auto-Run Setup: Create a systemd service at `/etc/systemd/system/drone_bridge.service` to run the script on boot
* Hardware Link: Connect Pi UART (/dev/serial0) to the FC UART and GPIO 18 to the servo signal wire

## 3. Operational Workflow (Every Flight)

### Step 1: Power & Network

1. Connect the Local Computer & Raspberry Pi to the same network (same subnet)
```
WIFI NAME: drohn3 
PASSWORD: geheim123
```
2. Get the local IP address of the Raspberry Pi (e.g. 172.20.10.2)
3. Verify the connection by pinging the Pi from Local Computer: `ping 172.20.10.2`

### Step 2: Goggle & Video Link

1. Connect your Goggles to the Local Computer via USB
2. Ensure the camera feed is visible (verify `CAM_INDEX` in mission_controller.py)

### Step 3: Launch Mission Control

1. On the Mac, navigate to your workspace and run:
```bash
# Run inference with mission control enabled (default)
python3 inference.py --weights yolov8n.pt --source 0

# Disable mission control if you only want inference
python3 inference.py --weights yolov8n.pt --source 0 --no-mission

# Adjust mission cooldown (default: 5 seconds)
python3 inference.py --weights yolov8n.pt --source 0 --mission-cooldown-s 10.0
```

**Note:** The communication bridge is now integrated into `inference.py` through the `MissionController` class, which bridges inference detections + keyboard control to the Raspberry Pi. The `mission_controller.py` file provides helper functions (`handle_detection`, `process_keypress`, `trigger_drone_action`) that are imported and used by `inference.py`.
## 4. Usage & Controls

### Manual Keyboard Hotkeys
| Key | Action/Flight Mode        | Result/Description                                      |
|-----|--------------------------|---------------------------------------------------------|
| a   | Arm (STABILIZE)          | Switches to STABILIZE mode and arms motors              |
| q   | Disarm                   | Immediately stops motors (Use with caution!)            |
| b   | Brake                    | Halts the drone in its current 3D position              |
| s   | Open Servo               | Manually triggers the drop mechanism                    |
| x   | Exit                     | Shuts down the mission hub and bridge                   |
| j   | Stabilize MODE           | Switches to manual flight with self-leveling            |
| k   | Auto MODE                | Resumes the programmed mission plan                     |
| l   | RTL MODE                 | Return to Launch point and Land                         |

### Autonomous Detection Sequence

When the `MissionController` detects a "trash" object in the inference results, it automatically executes:
1. Brake (b): Drone stops moving
2. Drop (s): Pi cycles the servo (Open $\rightarrow$ 1s $\rightarrow$ Close)
3. Resume (k): Drone switches back to AUTO to continue the mission

The `MissionController` class in `inference.py` handles:
- Processing keyboard input for manual control
- Monitoring detection results from the YOLOv8 model
- Automatically triggering the drop sequence when trash is detected
- Managing cooldown periods to prevent repeated triggers
- Disarming the drone on exit for safety

## 5. Troubleshooting

* **Script Updates:** If you update `drone_control_listener.py`, run `sudo systemctl restart drone_bridge.service` on the Pi
* **Mission Control Not Working:** Ensure `--no-mission` flag is not set. Check that `mission_controller.py` is in the same directory as `inference.py` (it provides the helper functions)
* **Network Connection:** If you cannot send nc command to Raspberry Pi, make sure Local Computer & Raspberry Pi are on the same subnet (usually 172.20.10.x). In case they are not in the same subnet, try to manually setup the TCP/IP with following steps:

    1. Manually Setup TCP/IP

        | Name        | Value                                      |
        |---------------------------|---------------------------------------------------------|
        | IP address                | 172.20.10.15 (same subnet with Pi)                      |
        | Subnet mask               | 255.255.255.0 (netmask from `ifconfig en0 \| grep netmask`)                      |
        | Router                | 172.20.10.255 (broadcast from `ifconfig en0 \| grep netmask`)                      |

    2. Add to DNS Server: `172.20.10.1` & `8.8.8.8`

## 6. Code Structure

* **`inference.py`**: Main script that runs YOLOv8 inference and integrates mission control via `MissionController` class
* **`mission_controller.py`**: Provides helper functions (`handle_detection`, `process_keypress`, `trigger_drone_action`) used by `inference.py`
* **`drone_control_listener.py`**: Raspberry Pi script that listens for UDP commands and bridges them to the Flight Controller
* **`commander.py`**: Standalone test script for sending commands to the Raspberry Pi

## 7. Remaining Work

* Update mission for demo
* Figure autonomous flying 💀