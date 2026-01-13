# Remote Communication between Computer and Drone via Telemetry

## Communication Bridge Configuration (MAVLink over ELRS)

We use Radiomaster connected to Computer to communicate with the Drone.

*Reference: https://www.expresslrs.org/software/mavlink*

#### Prerequisites:
* Transmitter/Receiver firmware: 3.6.2
* TX Backpack firmware: 1.5.4
* FC Firmware: Ardupilot

**1. ArduCopter Drone MAVLink Settings:** Setup Drone Parameters to accept Mavlink protocol

| Parameter        | Value               | Description                                                                                          |
|------------------|---------------------|------------------------------------------------------------------------------------------------------|
| SERIALx_PROTOCOL | 2 (Mavlink2)        | Tells the specified SERIAL to listen for MAVLink telemetry.                                          |
| SERIALx_BAUD     | 460                 | Fixed Baud Rate for Mavlink according to the documentation.                                          |
| RSSI_TYPE        | 5 (TelemetryRadioR) |                                                                                                      |

*Replace `x` with SERIAL that Remote Controller connects to (to be honest, I do not remember which number in our real drone 😭)*

**2. Remote Controller ExpressLRS (ELRS) Firmware Settings:** Update the ELRS Lua script on your Radiomaster controller.

**For TX Settings:** Update these settings in ExpressLRS menu:

| Setting         | Value(s)       | Description                                                                                        |
|-----------------|----------------|----------------------------------------------------------------------------------------------------|
| Packet Rate     | 333Hz Full Res | High frequency to download parameters from drone to computer.                                      |
| Telemetry Ratio | 1:2            | Ensures a robust bidirectional data link required for MAVLink commands.                            |
| Link Mode       | MavLink        | Use MavLink communication mode                                                                     |

**For RX Settings:**
Make sure Link Mode for RX is also set to `MavLink` in `Other Devices` menu

**3. Setup connection between Computer and Remote Controller:** Connect Computer to Remote Controller using UDP.

1. Turn on WIFI on Remote Controller: `ExpressLRS` -> `Backpack` -> `Telemetry` -> `WiFi`. After a while (~30s), a new WIFI connection `ExpressLRS TX Backpack 000000` should be created.
2. Connect Computer to created WIFI:
```
Name: ExpressLRS TX Backpack 000000
Password: expresslrs
```
3. Test connection: Open `http://elrs_txbp.local/` (or `http://10.0.0.1`) in a browser. If the page loads, then you are good 👍🏼.

**4. Control the Drone from Computer:** You can control the drone using Mission Planner (QGroundControl) or a Python Script. For QGroundControl, refer to [this instruction](https://www.expresslrs.org/software/mavlink/#qgroundcontrol-setup-udp). In this project, we will focus on using Python Script for customizable missions & AI feature.

## Running the Script

#### Prerequisites

* Drone & Remote Controller powered on
* Telemetry connected between Drone & Remote Controller
* Ensure Configuration in `real_mission.py` correctly setup
* Python version 3.10.14
* Install required packages as below (or simply from `requirements.txt`, see [Run the script](#run-the-script)):

```bash
pip install dronekit
pip install opencv-python

pip install dronekit-sitl   # For simulation only
```

#### Run the script

* Connect to RC WIFI `ExpressLRS TX Backpack 000000 / expresslrs`
* Check connection `http://10.0.0.1`
* Run the script to connect

```bash
python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

python remote_communication/real_mission.py --real=true --camera=true
python remote_communication/real_mission.py --real=true --camera=true
```

## Servo Configuration

### Step-by-step guide

Step 1: Hardware Wiring
1. Flight Controller (FC) $\leftrightarrow$ Raspberry Pi:
    * UART 4 accroding to specifications
2. Raspberry Pi $\leftrightarrow$ Servo:
    * Yellow: 13 (GPIO 27)
    * Red: 4
    * Brown (Ground): 14

Step 2: FC Configuration on QGroundControl
| Parameter         | Value | Description                              |
|-------------------|-------|------------------------------------------|
| SERIAL4_PROTOCOL  | 2     | Sets protocol to MAVLink 2. **SERIAL4 due to UART4**.              |
| SERIAL4_BAUD      | 921 (Old: 460)   | Sets speed to 921600 baud (fast link for Pi). Make sure BAUD config on Pi also matched. |

Step 3: Raspberry Pi Setup to listen for command from FC to trigger servo
1. SSH into your Raspberry Pi
2. Install dependencies `pip install pymavlink RPi.GPIO`
3. Create a listener file `payload_listener.py`

```python
from pymavlink import mavutil
import RPi.GPIO as GPIO
import time
import sys

# --- CONFIGURATION ---
# Replace with the Pi's UART port connected to FC
# On Pi 3/4/Zero W, this is usually /dev/ttyS0 or /dev/ttyAMA0
CONNECTION_STRING = '/dev/ttyS0' 
BAUD_RATE = 921600
SERVO_PIN = 18

# --- GPIO SETUP ---
GPIO.setmode(GPIO.BCM)
GPIO.setup(SERVO_PIN, GPIO.OUT)
pwm = GPIO.PWM(SERVO_PIN, 50) # 50Hz frequency
pwm.start(0) # Start with 0 duty cycle (off)

def move_servo(pwm_value):
    """
    Maps MAVLink PWM (1000-2000) to Duty Cycle (approx 2-12).
    """
    # 1000us = 0 deg, 2000us = 180 deg (approx)
    # Duty Cycle = Pulse Width (ms) / Period (20ms) * 100
    duty = (pwm_value / 1000.0) / 20.0 * 100.0
    
    GPIO.output(SERVO_PIN, True)
    pwm.ChangeDutyCycle(duty)
    time.sleep(0.5) # Wait for servo to reach position
    
    # Turn off signal to prevent jitter/buzzing
    GPIO.output(SERVO_PIN, False)
    pwm.ChangeDutyCycle(0)

def main():
    print(f"[Pi] Connecting to FC on {CONNECTION_STRING}...")
    
    # Establish MAVLink Connection
    try:
        master = mavutil.mavlink_connection(CONNECTION_STRING, baud=BAUD_RATE)
    except Exception as e:
        print(f"[ERROR] Could not connect to UART: {e}")
        sys.exit(1)

    print("[Pi] Waiting for Heartbeat...")
    master.wait_heartbeat()
    print("[Pi] Connected! Listening for Servo Commands...")

    while True:
        # Listen for COMMAND_LONG messages (blocking wait)
        msg = master.recv_match(type='COMMAND_LONG', blocking=True)
        
        # Check for MAV_CMD_DO_SET_SERVO (ID 183)
        if msg.command == 183:
            servo_instance = int(msg.param1) # The "Servo Number"
            pwm_value = int(msg.param2)      # The PWM value (1000-2000)

            # Filter for our specific Servo ID (9)
            if servo_instance == 9:
                print(f"[Pi] Command Received: Servo 9 -> {pwm_value}")
                move_servo(pwm_value)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n[Pi] Stopping...")
    finally:
        pwm.stop()
        GPIO.cleanup()
```


NOTE:
* For `servo_listener.py` to test the listener from FC to RasberryPi and print `hello`. Enable serial in raspberry pi configs, try to run file again. After starting successfully, try to send command from the computer.
* For servo, currently cannot make the servo work. Ask other teams how they setup the servo with rasberry pi