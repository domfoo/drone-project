import collections
import collections.abc

# Patch DroneKit for Python 3.10+ compatibility:
if not hasattr(collections, "MutableMapping"):
    collections.MutableMapping = collections.abc.MutableMapping

from dronekit import connect, VehicleMode, LocationGlobalRelative
import dronekit_sitl
import time
import cv2
import numpy as np

print("--- STARTING SIMULATION SETUP ---")

# 1. Start the Virtual Drone (SITL)
# This downloads a virtual Copter and runs it
sitl = dronekit_sitl.SITL()
sitl.download('copter', '3.3', verbose=True)
sitl_args = ['--model', 'quad', '--home=50.1109,8.6821,0,180'] # Offenbach/Frankfurt coordinates
sitl.launch(sitl_args, await_ready=True)

# Get the connection string (usually tcp:127.0.0.1:5760)
connection_string = sitl.connection_string()
print(f"Virtual Drone flying at: {connection_string}")

# 2. Connect Python to the Virtual Drone
print("Connecting to vehicle...")
vehicle = connect(connection_string, wait_ready=True)

# 3. Setup Virtual Servo Helper
def log_servo_status():
    # In SITL, we can check the servo output values (Channel 1 for our drop mechanism)
    # 1000 = Closed, 2000 = Open
    servo_pwm = vehicle.channels['1']
    print(f" [DEBUG] Servo Channel 1 PWM: {servo_pwm}")

# 4. Takeoff Function
def arm_and_takeoff(aTargetAltitude):
    print("Basic pre-arm checks")
    while not vehicle.is_armable:
        print(" Waiting for vehicle to initialise...")
        time.sleep(0.5)

    print("Arming motors")
    vehicle.mode = VehicleMode("GUIDED")
    vehicle.armed = True

    while not vehicle.armed:
        print(" Waiting for arming...")
        time.sleep(0.5)

    print("Taking off!")
    vehicle.simple_takeoff(aTargetAltitude)

    while True:
        print(f" Altitude: {vehicle.location.global_relative_frame.alt}")
        if vehicle.location.global_relative_frame.alt >= aTargetAltitude * 0.95:
            print("Reached target altitude")
            break
        time.sleep(1)

# --- SIMULATION START ---

# A. Fly the virtual drone
arm_and_takeoff(10) # Go to 10 meters height

# B. Start "Forward Flight" (simulate drone moving)
print("d5 m/s...")
# This sets a velocity of 5m/s North
msg = vehicle.message_factory.set_position_target_local_ned_encode(
    0, 0, 0,
    1, 0b0000111111000111, # Bitmask
    5, 0, 0, # x, y, z velocity (m/s)
    0, 0, 0, 0, 0, afz=0, yaw_rate=0, yaw=0)
vehicle.send_mavlink(msg)

# C. Fake Camera Loop
print("\n--- SYSTEM READY FOR DETECTION ---")
print("Press 'd' to simulate TRASH DETECTION")
print("Press 'q' to Quit")

# Create a black image to simulate a camera feed window
fake_cam_feed = np.zeros((400, 400, 3), dtype="uint8")
cv2.putText(fake_cam_feed, "Simulated Camera", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

try:
    while True:
        # Show fake camera window
        cv2.imshow("Virtual Drone View", fake_cam_feed)
        key = cv2.waitKey(100) & 0xFF

        # --- TEST LOGIC HERE ---
        if key == ord('d'):
            print("\n!!! OBJECT DETECTED !!!")
            
            # 1. STOP
            print("1. Sending BRAKE command...")
            vehicle.mode = VehicleMode("BRAKE")
            
            # 2. DROP TAG (Simulate Servo on Channel 1)
            print("2. Dropping Payload...")
            # Override Channel 1 to 2000 PWM (Open)
            vehicle.channels.overrides['1'] = 2000
            time.sleep(0.5) # Let servo move
            log_servo_status() # Verify it happened
            
            # Reset Servo
            vehicle.channels.overrides['1'] = 1000
            print("   Payload Dropped. Servo Reset.")
            log_servo_status()

        if key == ord('q'):
            print("Landing...")
            vehicle.mode = VehicleMode("LAND")
            break

except KeyboardInterrupt:
    pass

# Shutdown
vehicle.close()
sitl.stop()
cv2.destroyAllWindows()
print("Simulation Ended")