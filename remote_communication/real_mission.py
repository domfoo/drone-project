import collections
import collections.abc
import cv2
import time
import sys
import argparse

# Patch DroneKit for Python 3.10+ compatibility:
if not hasattr(collections, "MutableMapping"):
    collections.MutableMapping = collections.abc.MutableMapping

from dronekit import connect, VehicleMode
from pymavlink import mavutil

# --- CONFIGURATION ---
BAUD_RATE = 460800  # 57600 or 230400

FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FPS = 30

# SERVO CONFIG
PAYLOAD_SERVO_ID = 9     # ID used in MAVLink command (must match Pi script)
PWM_OPEN = 2000          # PWM value for Open
PWM_CLOSE = 1000         # PWM value for Close

# UPDATE THIS TO MATCH YOUR DEVICE
CONNECTION_STRING = "udp:0.0.0.0:14550"  # Connect through UDP
CAM_INDEX = 1  # Camera Index for Goggle


def message_callback(self, name, message):
    # The pre-arm check status is often sent as a STATUSTEXT message
    if name == "STATUSTEXT":
        # Print the error text to the console
        print(f" [APM MESSAGE]: {message.text}")


def connect_to_drone():
    print(f"[LOG] Connecting to Drone via Radio ({CONNECTION_STRING})")
    try:
        # ELRS is slower than a USB cable, so we need to increase the heartbeat timeout
        vehicle = connect(
            CONNECTION_STRING, baud=BAUD_RATE, wait_ready=False, heartbeat_timeout=30
        )
        print("[LOG] Connected to Drone")
        vehicle.add_message_listener("STATUSTEXT", message_callback)
        return vehicle
    except Exception as e:
        print(f"[ERROR] Connection Error: {e}")
        print("[ERROR] Check your COM port and ensure the Remote is connected")
        return None


def drop_payload(vehicle, use_camera=False):
    print("[ACTION] Sending Drop Command (Open)...")
    
    # Construct MAVLink command: MAV_CMD_DO_SET_SERVO (183)
    msg = vehicle.message_factory.command_long_encode(
        0, 0,    # target_system, target_component
        mavutil.mavlink.MAV_CMD_DO_SET_SERVO, 
        0,       # confirmation
        PAYLOAD_SERVO_ID,  # param1: Servo instance number
        PWM_OPEN,          # param2: PWM value
        0, 0, 0, 0, 0      # param3-7 (unused)
    )
    vehicle.send_mavlink(msg)

    # Wait for mechanism to open
    for _ in range(20): # 2 seconds
        if use_camera:
            cv2.waitKey(1)
        time.sleep(0.1)

    print("[ACTION] Sending Reset Command (Close)...")
    # Construct MAVLink command to Close
    msg = vehicle.message_factory.command_long_encode(
        0, 0,
        mavutil.mavlink.MAV_CMD_DO_SET_SERVO,
        0,
        PAYLOAD_SERVO_ID,
        PWM_CLOSE,
        0, 0, 0, 0, 0
    )
    vehicle.send_mavlink(msg)


def handle_detection(vehicle, use_camera=False):
    print("\n[LOG] Trash detected")

    # 1. INTERRUPT FLIGHT -> BRAKE
    # This overrides manual stick inputs and holds position (requires GPS lock!)
    print("[ACTION] Engaging Auto-Brake...")
    vehicle.mode = VehicleMode("BRAKE")

    # Wait 2 seconds for drone to stop (while keeping video alive)
    for _ in range(20):
        if use_camera:
            cv2.waitKey(1)
        time.sleep(0.1)

    # 2. DROP PAYLOAD
    drop_payload(vehicle, use_camera)

    print("[LOG] Drop complete. Switch Flight Mode on Remote to regain control")
    vehicle.mode = VehicleMode("GUIDED")

    # Debounce (Wait 3s before looking for trash again)
    for _ in range(30):
        if use_camera:
            cv2.waitKey(1)
        time.sleep(0.1)


def setup_video_stream():
    cap = cv2.VideoCapture(CAM_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, FPS)
    return cap


def read_frame(cap):
    ret, frame = cap.read()
    if not ret:
        print("[ERROR] Camera disconnected")
        return None
    return frame


def process_keypress(key, vehicle, use_camera=False):
    if key == ord("d"):
        handle_detection(vehicle, use_camera)
        return True
    if key == ord("q"):
        return False  # Return False to break the loop
    return True


def run_inference(frame):
    """Placeholder for AI model inference. Return True when trash detected."""
    # TODO: integrate your model here (e.g., YOLO, TFLite, ONNX)
    return False


def handle_frame_and_inputs(frame, key, vehicle, real=False):
    # Always allow manual key control (both real and test modes)
    if key != 0xFF:
        if not process_keypress(key, vehicle, use_camera=real):
            # Return False to signal main loop to stop (e.g., on 'q')
            return False

    # When real=True, also run AI inference so the system works autonomously
    if real:
        if run_inference(frame):
            handle_detection(vehicle, use_camera=True)

    # Continue mission loop by default
    return True


def arm_only(vehicle):
    """
    Checks for armability, attempts to arm the vehicle, and waits for confirmation.
    It performs NO takeoff or altitude checks.
    """
    print("[LOG] Arm Testing Started")
    # 2. Set mode to STABILIZE and arm the motors
    # ONLY USE STABILIZE HERE FOR TESTING !!!!
    vehicle.mode = VehicleMode("STABILIZE")
    vehicle.armed = True

    # 3. Wait for arming confirmation
    while not vehicle.armed:
        print("[LOG] Waiting for arming confirmation...")
        time.sleep(1)

    print("[SUCCESS] Motors ARMED.")
    print("--------------------------------")


def arm_and_auto(aTargetAltitude, vehicle):
    print("[LOG] Basic pre-arm checks")
    while not vehicle.is_armable:
        print("[LOG] Waiting for vehicle to initialise...")
        time.sleep(1)

    print("[LOG] Arming motors")
    vehicle.mode = VehicleMode("GUIDED")
    vehicle.armed = True

    while not vehicle.armed:
        print("[LOG] Waiting for arming...")
        time.sleep(1)

    vehicle.simple_takeoff(aTargetAltitude)

    while True:
        print(f" Altitude: {vehicle.location.global_relative_frame.alt}")
        if vehicle.location.global_relative_frame.alt >= aTargetAltitude * 0.95:
            print("Reached target altitude")
            break
        time.sleep(1)


def main(real=False):
    # 1. Connect to drone
    vehicle = connect_to_drone()
    if vehicle is None:
        print("[ERROR] Failed to connect to Drone via Radio")
        sys.exit()

    # 2. Setup the Video Stream for Goggle
    cap = None
    cap = setup_video_stream()
    if not cap.isOpened():
        print("[ERROR] Failed to open Video Stream")
        sys.exit()
    print("[LOG] Video Stream initialized")

    print("\n[LOG] Mission Started")

    # 3. Start mission: Use arm_and_auto if real=True, else use arm_only
    if real:
        print("[LOG] Using real arm_and_auto")
        arm_and_auto(10, vehicle)
    else:
        print("[LOG] Using arm_only")
        arm_only(vehicle)

    # 4. Main mission: GUIDED mode -> Detect Trash -> (optional) Back to position trash detected -> Drop Payload -> GUIDED mode
    try:
        while True:
            frame = read_frame(cap)
            if frame is None:
                print("[ERROR] Camera disconnected")
                break

            cv2.imshow("Drone Feed (Real)", frame)
            key = cv2.waitKey(1) & 0xFF

            if not handle_frame_and_inputs(frame, key, vehicle, real):
                break

    except Exception as e:
        print("[ERROR] Exception while running mission: ", e)

    finally:
        # Process before termination
        if vehicle and vehicle.armed:
            vehicle.armed = False
            print("[LOG] Motors Disarmed.")
        if vehicle:
            vehicle.close()
        if cap is not None:
            cap.release()
            cv2.destroyAllWindows()
        print("[LOG] Connection Closed")


if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Drone Mission Control Script")
    parser.add_argument(
        "--real",
        action="store_true",
        default=False,
        help="Use real arm_and_auto function (default: False, uses arm_only)",
    )
    args = parser.parse_args()

    # Ensure Remote is in 'USB Serial (VCP)' mode.
    # Ensure Drone is powered on and connected to Remote.
    main(real=args.real)
