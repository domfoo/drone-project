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

# --- CONFIGURATION ---
BAUD_RATE = 460800  # 57600 or 230400

FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FPS = 30

SERVO_CHANNEL = 9  # Channel for Servo Control

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
    print("[ACTION] Servo Opening...")
    # Open the Servo
    vehicle.channels.overrides[str(SERVO_CHANNEL)] = 2000

    # Small loop to keep window responsive while waiting
    for _ in range(10):
        if use_camera:
            cv2.waitKey(1)
        time.sleep(0.1)

    # Close the Servo
    print("[ACTION] Servo Closing...")
    vehicle.channels.overrides[str(SERVO_CHANNEL)] = 1000


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

    # TODO: Switch Flight Mode on Remote to regain control
    print("[LOG] Drop complete. Switch Flight Mode on Remote to regain control")

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
    # TODO: replace this with inference result trigger instead of keypress
    if key == ord("d"):
        handle_detection(vehicle, use_camera)
        return True
    if key == ord("q"):
        return False
    return True


def run_inference(frame):
    """Placeholder for AI model inference. Return True when trash detected."""
    # TODO: integrate your model here (e.g., YOLO, TFLite, ONNX)
    return False


def handle_frame_and_inputs(frame, key, vehicle, use_camera=False):
    # TODO: Uncomment this when the inference model is ready
    # if run_inference(frame):
    #     handle_detection(vehicle, use_camera)
    #     return True

    # For testing, use keypress to trigger detection
    return process_keypress(key, vehicle, use_camera)


def arm_for_testing(vehicle):
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


def arm_and_takeoff(aTargetAltitude, vehicle):
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

    # vehicle.simple_takeoff(aTargetAltitude)

    while True:
        print(f" Altitude: {vehicle.location.global_relative_frame.alt}")
        if vehicle.location.global_relative_frame.alt >= aTargetAltitude * 0.95:
            print("Reached target altitude")
            break
        time.sleep(1)


def main(real=False, camera=False):
    vehicle = connect_to_drone()
    if vehicle is None:
        print("[ERROR] Failed to connect to Drone via Radio")
        sys.exit()

    # Setup the Video Stream for Goggle (only if camera is True)
    cap = None
    if camera:
        cap = setup_video_stream()
        if not cap.isOpened():
            print("[ERROR] Failed to open Video Stream")
            sys.exit()
        print("[LOG] Video Stream initialized")
    else:
        print("[LOG] Running without video stream")

    # Start the Mission - Arm & Takeoff & Go to GUIDED
    print("\n[LOG] Mission Started")

    # Use real arm_and_takeoff if real=True, else use arm_for_testing
    if real:
        print("[LOG] Using real arm_and_takeoff")
        arm_and_takeoff(10, vehicle)
    else:
        print("[LOG] Using arm_for_testing")
        arm_for_testing(vehicle)

    # Main loop: Detect Trash -> Drop Payload -> Back to GUIDED mode
    try:
        if camera:
            # Main loop with video stream
            while True:
                frame = read_frame(cap)
                if frame is None:
                    print("[ERROR] Camera disconnected")
                    break

                cv2.imshow("Drone Feed (Real)", frame)
                key = cv2.waitKey(1) & 0xFF

                if not handle_frame_and_inputs(frame, key, vehicle, use_camera=True):
                    break
        else:
            # Main loop without video stream
            print("[LOG] Running main loop without camera (press Ctrl+C to exit)")
            while True:
                time.sleep(1)
                # TODO: Add detection logic here that doesn't require camera frames

    except KeyboardInterrupt:
        print("[LOG] Script aborted by user")

    finally:
        if vehicle and vehicle.armed:
            vehicle.armed = False  # Disarm the vehicle before closing
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
        help="Use real arm_and_takeoff function (default: False, uses arm_for_testing)",
    )
    parser.add_argument(
        "--camera",
        action="store_true",
        default=False,
        help="Setup and use video stream (default: False, runs without camera)",
    )
    args = parser.parse_args()

    # Ensure Remote is in 'USB Serial (VCP)' mode.
    # Ensure Drone is powered on and connected to Remote.
    main(real=args.real, camera=args.camera)
