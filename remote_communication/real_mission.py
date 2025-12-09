import collections
import collections.abc
import cv2
import time
import sys

# Patch DroneKit for Python 3.10+ compatibility:
if not hasattr(collections, "MutableMapping"):
    collections.MutableMapping = collections.abc.MutableMapping

from dronekit import connect, VehicleMode

# --- CONFIGURATION ---
# Fixed Configuration
BAUD_RATE = 115200  # Standard for USB Serial (VCP)

# Variable Configuration: UPDATE THIS TO MATCH YOUR DEVICE
COM_PORT = "COM3"  # USB Port for Remote Controller
CAM_INDEX = 1  # Camera Index for Goggle
SERVO_CHANNEL = 1  # Channel for Servo Control


def drop_payload(vehicle):
    print("[ACTION] Servo Opening...")
    # Open the Servo
    vehicle.channels.overrides[SERVO_CHANNEL] = 2000
    time.sleep(1.0)
    # Close the Servo
    print("[ACTION] Servo Closing...")
    vehicle.channels.overrides[SERVO_CHANNEL] = 1000


def handle_detection(vehicle):
    print("\n[LOG] Trash detected")

    # 1. INTERRUPT FLIGHT -> BRAKE
    # This overrides your manual stick inputs and holds position (requires GPS lock!)
    print("[ACTION] Engaging Auto-Brake...")
    vehicle.mode = VehicleMode("BRAKE")

    # Wait a moment for drone to settle
    time.sleep(1.5)

    # 2. DROP PAYLOAD
    drop_payload(vehicle)

    print("[LOG] Switch back to GUIDED or other stable mode to regain control.")

    # Debounce to prevent double-dropping
    time.sleep(3)


def connect_to_drone():
    print(f"[LOG] Connecting to Drone via Radio ({COM_PORT})")
    try:
        print("[LOG] Connected to Drone")
        return connect(COM_PORT, baud=BAUD_RATE, wait_ready=False)
    except Exception as e:
        print(f"[ERROR] Connection Error: {e}")
        print("[ERROR] Check your COM port and ensure the Remote is connected")
        return None


def setup_video_stream():
    cap = cv2.VideoCapture(CAM_INDEX)
    return cap


def read_frame(cap):
    ret, frame = cap.read()
    if not ret:
        print("[ERROR] Camera disconnected")
        return None
    return frame


def process_keypress(key, vehicle):
    # TODO: replace this with inference result trigger instead of keypress
    if key == ord("d"):
        handle_detection(vehicle)
        return True
    if key == ord("q"):
        return False
    return True


def main():
    vehicle = connect_to_drone()
    if vehicle is None:
        print("[ERROR] Failed to connect to Drone via Radio")
        sys.exit()

    # Setup the Video Stream for Goggle
    cap = setup_video_stream()
    if cap is None:
        print("[ERROR] Failed to setup Video Stream")
        sys.exit()

    # TODO: Start the Mission
    print("\n[LOG] Mission Started")

    # Main loop: Detect Trash -> Drop Payload -> Back to GUIDED mode
    try:
        while True:
            frame = read_frame(cap)
            if frame is None:
                print("[ERROR] Camera disconnected")
                break

            cv2.imshow("Drone Feed (Real)", frame)
            key = cv2.waitKey(1) & 0xFF

            if not process_keypress(key, vehicle):
                break

    except KeyboardInterrupt:
        print("[LOG] Script aborted by user")

    finally:
        vehicle.close()
        cap.release()
        cv2.destroyAllWindows()
        print("[LOG] Connection Closed")


if __name__ == "__main__":
    # Ensure Remote is in 'USB Serial (VCP)' mode.
    # Ensure Drone is powered on and connected to Remote.
    main()
