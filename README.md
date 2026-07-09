Dynamic Temperature Chamber Controller
This repository contains the firmware and control software for a dynamic temperature chamber. The system utilizes a microcontroller to manage physical hardware and a Python script to define and transmit multi-stage heating and cooling profiles.

Hardware Configuration
The microcontroller firmware is configured for a Seeed Studio XIAO ESP32-C3. Ensure your hardware is wired to the following pins:

Sensors (Thermistors): D0, D1, D2

Compressor Relay: D4

Heater Relay: D5
How to Program a Heat Cycle
The heat cycles are completely managed by the Python script (controller.py). You do not need to recompile the C++ firmware to change the temperature profile.

To program a new heat cycle, open controller.py and locate the PROFILE array.

The PROFILE Array
The profile is a list of sequential stages. Each stage is defined as a tuple containing two numbers: (target_temp_in_C, duration_in_minutes).

Example Configuration:

Python
PROFILE = [
    (30.0, 10.0),   # Cycle 1: Ramp to 30.0°C over 10 minutes
    (40.0, 15.0),   # Cycle 2: Ramp to 40.0°C over 15 minutes
    (40.0, 30.0),   # Cycle 3: Hold at 40.0°C for 30 minutes
    (25.0, 20.0)    # Cycle 4: Cool down to 25.0°C over 20 minutes
]
How the Controller Interprets the Profile:
Ramping: If the target temperature is different from the current temperature, the ESP32 will linearly interpolate (ramp) the setpoint over the specified duration.

Holding: To hold a specific temperature, create a cycle where the target temperature is the same as the previous cycle's target, and specify how long you want to hold it (e.g., Cycle 3 in the example above).

Completion: Once the final profile stage finishes, the ESP32 will hold the final temperature indefinitely.

Running the System
Flash the Firmware: Ensure main.cpp, Thermostat.cpp, Sensors.cpp, and Comms.cpp are flashed to your Seeed Studio XIAO ESP32-C3.

Configure Python COM Port: Open controller.py and modify the SERIAL_PORT variable (default is 'COM10') to match the port your ESP32 is connected to.

Execute the Script: Run the script using Python:

Bash
python controller.py
Observe Initialization: The Python script connects at a baud rate of 115200. It will format your programmed steps into strings like "T:target_temp,D:duration_in_minutes\n" and send them to the microcontroller. The ESP32 will respond with "ACK: New Profile Loaded" to confirm receipt.

Telemetry and Logging
Once the script is running, the ESP32 broadcasts telemetry data every 2 seconds (2000 ms).

Live Console Output: The Python script will print a live dashboard displaying the Current Temperature, Setpoint, Compressor State, and Heater State.

Data Logging: All telemetry is automatically saved to a uniquely timestamped log file in the same directory, formatted as telemetry_log_YYYYMMDD_HHMMSS.txt.

Safe Interruptions: If you need to stop logging or close the terminal, pressing Ctrl+C will cleanly exit the Python script and save the log file. The ESP32 will continue running its current temperature ramp autonomously.
