import subprocess
import time

# --- Configuration ---
RASPBERRY_PI_IP = '172.20.10.2'
UDP_PORT = 5005

def trigger_drone_action(command):
    """Executes the working netcat command via system shell."""
    try:
        # This mimics: echo "command" | nc -u RASPBERRY_PI_IP UDP_PORT
        # We use a 1-second timeout so the script doesn't hang.
        cmd = f'echo "{command}" | nc -u -w 1 {RASPBERRY_PI_IP} {UDP_PORT}'
        
        # subprocess.run executes the string in the system shell.
        subprocess.run(cmd, shell=True, check=True)
        print(f"Successfully triggered '{command}' via Netcat")
        
    except subprocess.CalledProcessError as e:
        print(f"Error executing Netcat: {e}")

if __name__ == "__main__":
    # Test the trigger
    trigger_drone_action('a')
    time.sleep(1)
    trigger_drone_action('s')
    time.sleep(10)
    trigger_drone_action('q')