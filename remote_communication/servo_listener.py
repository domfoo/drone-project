from pymavlink import mavutil
import RPi.GPIO as GPIO
import time
import sys

# --- CONFIGURATION ---
# Replace with the Pi's UART port connected to FC
# On Pi 3/4/Zero W, this is usually /dev/ttyS0 or /dev/ttyAMA0
CONNECTION_STRING = '/dev/ttyS0' 
BAUD_RATE = 921600
SERVO_PIN = 27

# --- GPIO SETUP ---
GPIO.setmode(GPIO.BCM)
GPIO.setup(SERVO_PIN, GPIO.OUT)
pwm = GPIO.PWM(SERVO_PIN, 50) # 50Hz frequency
pwm.start(0) # Start with 0 duty cycle (off)

def move_servo(pwm_value):
    """
    Maps MAVLink PWM (1000-2000) to Duty Cycle (approx 2-12).
    """
    # 1000us = 0 deg, 2000us = 180 deg (approx)
    # Duty Cycle = Pulse Width (ms) / Period (20ms) * 100
    duty = (pwm_value / 1000.0) / 20.0 * 100.0
    
    GPIO.output(SERVO_PIN, True)
    pwm.ChangeDutyCycle(duty)
    time.sleep(0.5) # Wait for servo to reach position
    
    # Turn off signal to prevent jitter/buzzing
    GPIO.output(SERVO_PIN, False)
    pwm.ChangeDutyCycle(0)

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
        if msg.command == 183:
            print("Hello Servo!")
            # servo_instance = int(msg.param1) # The "Servo Number"
            # pwm_value = int(msg.param2)      # The PWM value (1000-2000)

            # # Filter for our specific Servo ID (9)
            # if servo_instance == 9:
            #     print(f"[Pi] Command Received: Servo 9 -> {pwm_value}")
            #     move_servo(pwm_value)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n[Pi] Stopping...")
    finally:
        pwm.stop()
        GPIO.cleanup()