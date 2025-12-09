import collections
import collections.abc
import cv2
import time
import sys

# Patch DroneKit for Python 3.10+ compatibility:
if not hasattr(collections, "MutableMapping"):
    collections.MutableMapping = collections.abc.MutableMapping

from dronekit import connect, VehicleMode

# --- CONFIGURATION: UPDATE THIS TO MATCH YOUR DEVICE ---
COM_PORT = "COM3"  # USB Port for Remote Controller
BAUD_RATE = 115200  # Fixed: Standard for USB Serial (VCP)

CAM_INDEX = 1  # Camera Index for Goggle
SERVO_CHANNEL = 1  # Channel for Servo Control


def drop_payload(vehicle):
    print("   [ACTION] Dropping Payload...")
    # Open the Servo
    vehicle.channels.overrides[SERVO_CHANNEL] = 2000
    time.sleep(1.0)
    # Close the Servo
    vehicle.channels.overrides[SERVO_CHANNEL] = 1000
    print("   [ACTION] Servo Reset.")


def handle_detection(vehicle):
    print("\n!!! TRASH DETECTED !!!")

    # 1. INTERRUPT FLIGHT -> BRAKE
    # This overrides your manual stick inputs and holds position (requires GPS lock!)
    print("1. Engaging Auto-Brake...")
    vehicle.mode = VehicleMode("BRAKE")

    # Optional: Wait a moment for drone to settle
    time.sleep(1.5)

    # 2. DROP TAG
    drop_payload(vehicle)

    print("Sequence Complete. Switch to LOITER or STABILIZE to regain control.")

    # Simple debounce to prevent double-dropping
    time.sleep(3)


def main():
    print(f"--- CONNECTING TO DRONE VIA RADIO ({COM_PORT}) ---")
    print("1. Ensure Remote is in 'USB Serial (VCP)' mode.")
    print("2. Ensure Drone is powered on and bound to Remote.")

    try:
        # We use wait_ready=False because ELRS bandwidth is low and full param download takes time
        vehicle = connect(COM_PORT, baud=BAUD_RATE, wait_ready=False)
        print(">>> LINK ESTABLISHED! <<<")
    except Exception as e:
        print(f"Connection Error: {e}")
        print("Check your COM port and ensure the Remote is connected.")
        sys.exit()

    # Setup the Video Stream for Goggle
    cap = cv2.VideoCapture(CAM_INDEX)

    print("\n--- SYSTEM ARMED AND WATCHING ---")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Error: Camera disconnected.")
                break

            cv2.imshow("Drone Feed (Real)", frame)
            key = cv2.waitKey(1) & 0xFF

            # --- REPLACE THIS WITH YOUR AI MODEL LATER ---
            # For now, we still use 'd' to test the full loop in the real world
            if key == ord("d"):
                handle_detection(vehicle)

            if key == ord("q"):
                break

    except KeyboardInterrupt:
        print("Script aborted by user.")

    finally:
        vehicle.close()
        cap.release()
        cv2.destroyAllWindows()
        print("Connection Closed.")


if __name__ == "__main__":
    main()
