from pymavlink import mavutil
import RPi.GPIO as GPIO
import time
import sys

# --- CONFIGURATION ---
# Replace with the Pi's UART port connected to FC
# On Pi 3/4/Zero W, this is usually /dev/ttyS0 or /dev/ttyAMA0
CONNECTION_STRING = '/dev/ttyS0' 
BAUD_RATE = 921600
SERVO_PIN = 18  # BCM pin (verified working setup)

# MAVLink MAV_CMD_DO_SET_SERVO configuration
TARGET_SERVO_INSTANCE = 9  # must match param1 sent by the mission script

# Physical servo angles (degrees)
ANGLE_CLOSED = 0
ANGLE_OPEN = 90

# --- GPIO SETUP ---
print("Setting up GPIO...")
GPIO.setmode(GPIO.BCM)
GPIO.setup(SERVO_PIN, GPIO.OUT)
pwm = GPIO.PWM(SERVO_PIN, 50)  # 50Hz frequency (standard servos)
pwm.start(0)  # Start with 0 duty cycle (off)

def _clamp(value, min_value, max_value):
    return max(min_value, min(value, max_value))


def set_angle(angle):
    angle = _clamp(angle, 0, 180)
    print(f"[Pi] Moving to {angle} degrees")

    # Mapping angle to duty cycle (approx for most servos)
    # 0 deg = ~2.5% duty, 180 deg = ~12.5% duty
    duty = 2.5 + (angle / 18.0)

    # Just update the PWM. Do NOT use GPIO.output here.
    pwm.ChangeDutyCycle(duty)
    time.sleep(0.5)  # Wait for it to move
    print("[Pi] moved to duty:", duty)

    # Set duty to 0 to stop sending pulses (stops jitter)
    pwm.ChangeDutyCycle(0)
    time.sleep(0.5)


def pwm_to_angle(pwm_value):
    """
    Convert MAVLink PWM value (typically 1000-2000) into an angle for this servo.

    This maps:
    - 1000 -> ANGLE_CLOSED
    - 2000 -> ANGLE_OPEN
    with linear interpolation between.
    """
    pwm_value = int(pwm_value)
    pwm_value = _clamp(pwm_value, 1000, 2000)
    t = (pwm_value - 1000) / 1000.0
    angle = ANGLE_CLOSED + t * (ANGLE_OPEN - ANGLE_CLOSED)
    return int(round(angle))

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
        if msg.command != 183:
            continue

        servo_instance = int(msg.param1)  # the "Servo Number"
        pwm_value = int(msg.param2)       # PWM value (1000-2000)

        # Filter for our specific Servo ID
        if servo_instance != TARGET_SERVO_INSTANCE:
            continue

        angle = pwm_to_angle(pwm_value)
        print(f"[Pi] Command Received: Servo {servo_instance} -> {pwm_value} (angle {angle})")
        set_angle(angle)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n[Pi] Stopping...")
    finally:
        pwm.stop()
        GPIO.cleanup()