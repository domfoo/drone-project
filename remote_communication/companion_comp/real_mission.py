import cv2
import time
import sys
import argparse
import subprocess

# --- CONFIGURATION ---
RASPBERRY_PI_IP = '172.20.10.2'
UDP_PORT = 5005

FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FPS = 30
CAM_INDEX = 1  # Camera Index for Goggle/Receiver connected to Mac

def trigger_drone_action(command):
    """Sends a UDP command string to the Raspberry Pi bridge via Netcat."""
    try:
        # Use a 1-second timeout to prevent the script from hanging
        cmd = f'echo "{command}" | nc -u -w 1 {RASPBERRY_PI_IP} {UDP_PORT}'
        subprocess.run(cmd, shell=True, check=True)
        print(f"[NETCAT] Successfully triggered: {command}")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Netcat failed: {e}. Check RPi connection.")

def setup_video_stream():
    """Initializes the video feed from the local receiver."""
    cap = cv2.VideoCapture(CAM_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, FPS)
    return cap

def run_inference(frame):
    """
    Placeholder for AI model (YOLO/TFLite).
    Return True when target object is detected.
    """
    # TODO: Insert your model inference code here
    return False

def handle_detection():
    """
    Automated mission sequence upon AI detection:
    1. 'b': Engage BRAKE mode.
    2. 's': Trigger SERVO drop cycle.
    3. 'k': Switch back to AUTO mode to continue mission.
    """
    print("\n[AI LOG] Target detected! Starting Drop Sequence...")

    # 1. BRAKE
    trigger_drone_action('b')
    time.sleep(2) # Wait for the drone to stabilize in position

    # 2. TRIGGER SERVO
    # Note: The Pi script handles the open-wait-close cycle automatically
    trigger_drone_action('s')
    time.sleep(2) 
    
    # 3. CONTINUE PLAN (Switch to AUTO)
    print("[AI LOG] Resuming Mission Plan...")
    trigger_drone_action('k')
    
    # Debounce: Prevent immediate re-triggering
    time.sleep(5)

def process_keypress(key):
    """Handles manual overrides from the keyboard using updated keys."""
    if key == ord("a"):
        # ArduPilot typically requires a safe mode like STABILIZE to arm
        print("[MANUAL] Setting mode to STABILIZE and Arming...")
        trigger_drone_action('j')
        time.sleep(0.5)
        trigger_drone_action('a')
    elif key == ord("q"):
        print("[MANUAL] Disarming Drone...")
        trigger_drone_action('q')
    elif key == ord("s"):
        print("[MANUAL] Toggling Servo...")
        trigger_drone_action('s')
    elif key == ord("b"):
        print("[MANUAL] Engaging BRAKE...")
        trigger_drone_action('b')
    elif key == ord("j"):
        print("[MANUAL] Switching to STABILIZE...")
        trigger_drone_action('j')
    elif key == ord("k"):
        print("[MANUAL] Switching to AUTO (Continue Plan)...")
        trigger_drone_action('k')
    elif key == ord("l"):
        print("[MANUAL] Switching to RTL (Return To Launch)...")
        trigger_drone_action('l')
    elif key == ord("x"):
        print("[MANUAL] Shutting down Bridge and Hub...")
        trigger_drone_action('c') 
        return False
    return True

def main(run_ai=False):
    cap = setup_video_stream()
    if not cap or not cap.isOpened():
        print("[ERROR] Failed to open Video Stream")
        sys.exit()
    print("[LOG] Video Stream initialized")

    print("\n[LOG] Mission Hub Started")
    # Updated help text to match new keys
    print("CONTROLS: 'a'=Arm | 'q'=Disarm | 's'=Servo | 'b'=Brake | 'j'=Stab | 'k'=Auto | 'l'=RTL | 'x'=Exit")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[ERROR] Camera disconnected")
                break

            cv2.imshow("Drone AI Hub", frame)
            key = cv2.waitKey(1) & 0xFF

            if not process_keypress(key):
                break

            if run_ai:
                if run_inference(frame):
                    handle_detection()

    except Exception as e:
        print(f"[ERROR] Hub Exception: {e}")

    finally:
        # Final safety check: ensure disarmed on exit
        trigger_drone_action('q')
        if cap is not None:
            cap.release()
        cv2.destroyAllWindows()
        print("[LOG] Mission Hub Closed")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Drone AI Hub (Mac-Side)")
    parser.add_argument(
        "--real",
        action="store_true",
        help="Run AI inference and auto-trigger drop sequence",
    )
    args = parser.parse_args()
    main(run_ai=args.real)