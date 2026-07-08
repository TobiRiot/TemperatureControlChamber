import serial
import time

# --- CONFIGURATION ---
# Change this to match the port your ESP32 is plugged into.
SERIAL_PORT = 'COM10' 
BAUD_RATE = 115200

# --- LOGGING CONFIGURATION ---
# Generates a unique log file name using the current timestamp
LOG_FILENAME = f"telemetry_log_{time.strftime('%Y%m%d_%H%M%S')}.txt"

# --- MULTI-CYCLE PROFILE ---
# Define your sequence here. 
# Format: (target_temp_in_C, duration_in_minutes)
PROFILE = [
    (30.0, 10.0),   # Cycle 1: Ramp to 30.0°C over 10 minutes
    (40.0, 15.0),   # Cycle 2: Ramp to 40.0°C over 15 minutes
    (40.0, 30.0),   # Cycle 3: Hold at 40.0°C for 30 minutes
    (25.0, 20.0)    # Cycle 4: Cool down to 25.0°C over 20 minutes
]

def main():
    # Open log file
    log_file = open(LOG_FILENAME, 'w', encoding='utf-8')
    
    # Helper function to print to console AND write to the log file
    def print_and_log(text):
        print(text)
        log_file.write(text + "\n")
        log_file.flush() # Ensure data is written to disk immediately
        
    try:
        # 1. Open the serial connection
        print_and_log(f"Connecting to ESP32 on {SERIAL_PORT}...")
        esp32 = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(2) # Wait for ESP32 to reboot on connection
        
        # 2. State Tracking for Cycles
        current_step_index = 0
        step_start_time = time.time()
        current_duration_sec = 0

        # Helper function to send the current step to the ESP32
        def send_step(index):
            nonlocal step_start_time, current_duration_sec
            target, duration_mins = PROFILE[index]
            
            # Format: "T:target_temp,D:duration_in_minutes\n"
            command = f"T:{target},D:{duration_mins}\n"
            print_and_log(f"\n>> Sending Cycle {index + 1}/{len(PROFILE)}: {command.strip()}")
            esp32.write(command.encode('utf-8'))
            
            # Reset our Python-side timers
            step_start_time = time.time()
            current_duration_sec = duration_mins * 60.0

        # Kick off the very first step
        if PROFILE:
            send_step(current_step_index)
        
        # 3. Listen for Telemetry and Manage Cycles
        print_and_log("\nListening for live data (Press Ctrl+C to stop)...")
        header = "Current(°C) | Setpoint(°C) | Compressor | Heater"
        print_and_log(header)
        print_and_log("-" * len(header))
        
        while True:
            # --- Cycle Management Logic ---
            if current_step_index < len(PROFILE):
                elapsed_time = time.time() - step_start_time
                
                # If the current cycle's time is up, move to the next one
                if elapsed_time >= current_duration_sec:
                    current_step_index += 1
                    
                    if current_step_index < len(PROFILE):
                        send_step(current_step_index)
                    else:
                        print_and_log("\n>> Profile complete! The ESP32 will now hold the final temperature indefinitely.")

            # --- Telemetry Reading Logic ---
            if esp32.in_waiting > 0:
                line = esp32.readline().decode('utf-8').strip()
                
                if line.startswith("ACK:"):
                    print_and_log(f">> ESP32 Confirms: {line}")
                elif "," in line:
                    data = line.split(',')
                    if len(data) == 4:
                        curr_temp, setpoint = data[0], data[1]
                        comp_on = "ON" if data[2] == "1" else "OFF"
                        heat_on = "ON" if data[3] == "1" else "OFF"
                        print_and_log(f"{curr_temp:>10}  | {setpoint:>12} | {comp_on:>10} | {heat_on:>6}")
                else:
                    if line: 
                        print_and_log(f"Debug: {line}")
                        
            # Keep CPU usage low
            time.sleep(0.1)
            
    except serial.SerialException:
        print_and_log(f"\nError: Could not open {SERIAL_PORT}. Is the board plugged in and the Arduino/PIO Serial Monitor closed?")
    except KeyboardInterrupt:
        print_and_log("\nExiting script. The ESP32 will continue running its current ramp autonomously.")
    finally:
        if 'esp32' in locals() and esp32.is_open:
            esp32.close()
            
        # Ensure the log file is safely closed when exiting
        log_file.close()
        print(f"Log saved successfully to: {LOG_FILENAME}")

if __name__ == "__main__":
    main()