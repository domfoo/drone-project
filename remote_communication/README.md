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

```bash
python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

python remote_communication/real_mission.py --real=true --camera=true
python remote_communication/real_mission.py --real=true --camera=true
```

## Servo Configuration

*TBD*