# Remote Communication between Computer and Drone via Telemetry

## One-time Setup (hopefully) - AI Generated, not tested yet

### 1. Servo Wiring and Flight Controller Mapping
Configure the LED signal for Servo controlling purpose. This can be updated based on real hardware configuration by Gajus.

**1.1. Physical Connections:**

| Component     | Wire Color        | Connects To (GN745 Pad) | Notes                                       |
|-------------- |------------------|-------------------------|---------------------------------------------|
| Micro Servo   | Signal (Orange/White) | LED                    | This pad is repurposed for PWM output.      |
| Micro Servo   | Positive (Red)        | 5V                     | Use a dedicated 5V pad for reliable power.  |
| Micro Servo   | Ground (Brown/Black)  | GND                    |                                             |
    
**1.2. ArduCopter Parameter Configuration:** Connect the Drone to QGroundControl and update the following parameters. This tells ArduPilot to use the LED pad as a Servo signal and maps it to Auxiliary Channel 9.

| Parameter          | Value          | Description                                                                                         |
|--------------------|---------------|-----------------------------------------------------------------------------------------------------|
| SERVO5_FUNCTION    | 38 (RCIN9)    | Maps physical PWM output (often Servo 5 in firmware) to Channel 9 of the remote/MAVLink input.      |
| SERVO5_MIN         | 1000          | Minimum PWM value (Servo Closed/Hold).                                                              |
| SERVO5_MAX         | 2000          | Maximum PWM value (Servo Open/Drop).                                                                |
| SERVO5_TRIM        | 1000          | Neutral position (Servo Closed/Hold).                                                               |
| RC_OPTIONS         | 3 (or higher) | Ensures that ArduPilot accepts RC input and telemetry data, crucial for MAVLink tunneling.          |

### 2. Communication Bridge Configuration (MAVLink over ELRS)

We use Radiomaster connected to Computer to communicate with the Drone.

**2.1. ExpressLRS (ELRS) Firmware Settings:** Access the ELRS Lua script on your Radiomaster controller to ensure data integrity

* Packet Rate: Set to 333Hz Full Res or 100Hz Full Res (Higher frequency provides more opportunity to transmit telemetry/MAVLink data)

* Telemetry Ratio: Set to 1:2 or Standard (This ensures a robust bidirectional data link required for MAVLink commands)

**2.2. EdgeTX/OpenTX Radio Settings:** This configures the radio to act as a serial connection for your PC

* USB Connection Mode: When plugging the remote into the PC, select "USB Serial (VCP)" or "Serial"/"Debug"

* Verify Port: Check your PC's Device Manager for the newly created COM Port (e.g., COM3), **this is the COM_PORT value you must use in your Python script**

**2.3 ArduCopter MAVLink Link Settings:** The ELRS receiver is connected to a UART (e.g., UART2) on the FC. This parameter tells ArduCopter to read the control and telemetry data from that port

* Set `SERIALx_PROTOCOL` to	`23 (RCIN)`	to tells the specified UART to listen for RC input (CRSF/ELRS) and MAVLink telemetry simultaneously

* Replace `x` with SERIAL that Remote Controller connects to (maybe 4, I do not remember)

## Run the script

### Prerequisites

* Python version 3.10.14

* Install required packages as below (or simply from `requirements.txt`, see [Run the script](#run-the-script))
```
pip install dronekit-sitl
pip install dronekit
pip install opencv-python
```

* Others
    * Ensure Remote is in 'USB Serial (VCP)' mode
    * Ensure Drone is powered on and connected to Remote
    * Configuration Constants in `real_mission.py` is correctly setup

### Run the script
```
python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

python remote_communication/real_mission.py
```




