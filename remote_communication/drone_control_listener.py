import socket
from pymavlink import mavutil
import RPi.GPIO as GPIO
import time
import sys

# --- Network Configuration ---
UDP_IP = "0.0.0.0"      
UDP_PORT = 5005         

# --- GPIO Configuration (Servo) ---
SERVO_PIN = 18 
GPIO.setmode(GPIO.BCM)
GPIO.setup(SERVO_PIN, GPIO.OUT)
pwm_servo = GPIO.PWM(SERVO_PIN, 50)
pwm_servo.start(0)

# --- MAVLink Configuration ---
try:
    # Connect to the GOKU GN745 via UART4
    master = mavutil.mavlink_connection('/dev/serial0', baud=921600)
except Exception as e:
    print(f"Error connecting to Flight Controller: {e}")
    GPIO.cleanup()
    sys.exit(1)

# --- State & Logic Functions ---
def set_servo_angle(angle):
    """Direct GPIO control for the servo"""
    duty = 2.5 + (angle / 18.0)
    pwm_servo.ChangeDutyCycle(duty)
    time.sleep(0.5) 
    pwm_servo.ChangeDutyCycle(0)

def set_flight_mode(mode_name):
    """Changes the flight mode of the ArduPilot controller."""
    if mode_name not in master.mode_mapping():
        print(f"Unknown mode: {mode_name}")
        return
    
    mode_id = master.mode_mapping()[mode_name]
    master.mav.set_mode_send(
        master.target_system,
        mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
        mode_id
    )
    print(f"Sent command to switch to {mode_name} mode")

def send_arm_disarm(arm):
    """MAVLink command to Arm/Disarm motors"""
    master.mav.command_long_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
        0, 1 if arm else 0, 0, 0, 0, 0, 0, 0
    )

# --- Setup UDP Socket ---
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))
sock.setblocking(False) 

def main():
    print("Starting Command Listener...")    
    master.wait_heartbeat()
    # Initial mode set to STABILIZE
    set_flight_mode('STABILIZE')

    last_heartbeat = 0
    
    try:
        print(f"Bridge Active. Listening on UDP port {UDP_PORT}...")
        while True:
            # 1. Maintain MAVLink Heartbeat (Crucial: 1Hz)
            if time.time() - last_heartbeat > 1.0:
                master.mav.heartbeat_send(mavutil.mavlink.MAV_TYPE_GCS, mavutil.mavlink.MAV_AUTOPILOT_INVALID, 0, 0, 0)
                last_heartbeat = time.time()

            # 2. Check for Network Commands
            try:
                data, addr = sock.recvfrom(1024)
                command = data.decode().lower().strip()
                print(f"Received Cmd: {command}")
                
                if command == 'a':
                    print("Network Cmd: ARMING DRONE")
                    send_arm_disarm(True)
                elif command == 'q':
                    print("Network Cmd: DISARMING DRONE")
                    send_arm_disarm(False)
                elif command == 'b':
                    # BRAKE mode: Stops drone immediately (requires GPS)
                    print("Network Cmd: BRAKE")
                    set_flight_mode('BRAKE')
                elif command == 's':
                    # Drop sequence: Open -> Wait -> Close
                    print("Network Cmd: DROP PAYLOAD")
                    set_servo_angle(90) # Open
                    time.sleep(1.0)
                    set_servo_angle(0)  # Close
                elif command == 'j':
                    # New key for STABILIZE
                    print("Network Cmd: SWITCH TO STABILIZE")
                    set_flight_mode('STABILIZE')
                elif command == 'k':
                    # New key for AUTO
                    print("Network Cmd: SWITCH TO AUTO")
                    set_flight_mode('AUTO')
                elif command == 'l':
                    # New key for RTL
                    print("Network Cmd: SWITCH TO RTL")
                    set_flight_mode('RTL')
                elif command == 'c':
                    print("Network Cmd: SYSTEM EXIT")
                    send_arm_disarm(False)
                    break
                    
            except socket.error:
                pass

            time.sleep(0.05) 

    except KeyboardInterrupt:
        print("Shutting down bridge...")
    finally:
        send_arm_disarm(False)
        pwm_servo.stop()
        GPIO.cleanup()
        sock.close()

if __name__ == "__main__":
    main()