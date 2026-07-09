# 🌡️ Dynamic Temperature Chamber Controller

![Hardware](https://img.shields.io/badge/Hardware-XIAO_ESP32--C3-blue?style=flat-square) <!-- -->
![Python](https://img.shields.io/badge/Script-Python_3.x-yellow?style=flat-square) <!-- -->

This repository contains the firmware and control software for a dynamic temperature chamber. The system utilizes a microcontroller to manage the physical hardware and a Python script to define and transmit multi-stage heating and cooling profiles.

---

## 🛠️ Hardware Configuration

The microcontroller firmware is explicitly configured for a **Seeed Studio XIAO ESP32-C3** <!-- -->. Ensure your hardware is wired to the following pins:

| Component | Pin | Description |
| :--- | :--- | :--- |
| **Sensors** | `D0`, `D1`, `D2` | Thermistor inputs for averaging temperature <!-- --> |
| **Compressor** | `D4` | Relay control for cooling <!-- --> |
| **Heater** | `D5` | Relay control for heating <!-- --> |

---

## 📈 How to Program a Heat Cycle

The heat cycles are completely managed by the Python script (`controller.py`) <!-- -->. You do not need to recompile the C++ firmware to change your temperature profiles.

To program a new heat cycle, open `controller.py` and modify the `PROFILE` list <!-- -->. 

### The `PROFILE` Array
The profile is a list of sequential stages. Each stage is defined as a tuple containing two numbers: `(target_temp_in_C, duration_in_minutes)` <!-- -->.

**Example Configuration:**
```python
PROFILE = [
    (30.0, 10.0),   # Cycle 1: Ramp to 30.0°C over 10 minutes
    (40.0, 15.0),   # Cycle 2: Ramp to 40.0°C over 15 minutes
    (40.0, 30.0),   # Cycle 3: Hold at 40.0°C for 30 minutes
    (25.0, 20.0)    # Cycle 4: Cool down to 25.0°C over 20 minutes
]
```

Profile Behavior:
Ramping: If the target temperature differs from the current temperature, the ESP32 will linearly interpolate the setpoint over the specified duration .

Holding: To hold a specific temperature, create a cycle where the target temperature matches the previous cycle's target, and specify the hold duration .

Completion: Once the final profile stage finishes, the ESP32 will hold the final temperature indefinitely .

## 🚀 Running the System
Flash the Firmware: Ensure the provided .cpp and .h files are flashed to your ESP32.

Configure COM Port: Open controller.py and modify the SERIAL_PORT variable (default is '`COM10`') to match your board's connection .

Execute: Run the script from your terminal:

`python controller.py`

## 📊 Telemetry and Logging
Once active, the ESP32 broadcasts telemetry data every 2 seconds .

Live Dashboard: The Python script prints a live console table displaying the Current Temperature, Setpoint, Compressor State, and Heater State .

Auto-Logging: All telemetry is automatically saved to a uniquely timestamped .txt file in the same directory .

Safe Interruptions: Pressing Ctrl+C will cleanly exit the script and save the log file. The ESP32 will safely continue running its current temperature ramp autonomously .
        
