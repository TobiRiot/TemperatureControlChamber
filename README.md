# Thermal Controller & SDI-12 Logging Dashboard

A comprehensive, Python-based GUI application built with `customtkinter` for managing hardware thermal profiles and concurrently logging/analyzing environmental data from SDI-12 sensors. 

This tool is designed for laboratory or field setups where a primary microcontroller (like an ESP32) drives a thermal chamber (heater/compressor), while a USB-to-SDI-12 adapter continuously polls external sensors (e.g., soil moisture, temperature sensors).

## Features

### 🌡️ Thermal Profile Management
* **Dynamic Profile Builder:** Create multi-step thermal profiles with specific target temperatures and hold/ramp durations.
* **Live Rate Calculation:** Automatically calculates and displays the ramp rate (°C/hr) for each step as you type.
* **Profile I/O:** Save and load thermal profiles as JSON files for repeatable testing.
* **Real-Time Telemetry Graphing:** Live tracking of actual temperature vs. setpoint, including an adjustable ±1°C tolerance band.
* **Hardware State Visualization:** Tracks heater and compressor ON/OFF states as square waves on a secondary axis.

### 📡 SDI-12 Data Logging
* **Concurrent Polling:** Runs in a dedicated background thread to prevent GUI freezing.
* **Compliant SDI-12 Handshakes:** Automatically handles `I!`, `M!`, and `M1!` commands, honoring sensor service request wait times.
* **Robust CSV Logging:** Dynamically aligns varying data lengths (up to 10 Moisture and 10 Temperature variables) into a clean, time-stamped CSV.

### 📊 Live Data Analysis
* **Time Series Visualization:** Live-updating plots of moisture and temperature data for individual sensors.
* **Statistical Correlation:** Generates Pearson correlation heatmaps between moisture and temperature readings.
* **Linear Regression:** Computes and graphs linear regression, $R^2$ values, and coefficients for sensor data relationships.
* **Batch Export:** One-click saving of all time series, correlation, and regression plots to a designated `Results` directory.

## Prerequisites

### Hardware
1. **Thermal Controller:** A microcontroller (e.g., ESP32, Arduino) programmed to accept `T:<target>,D:<duration>\n` commands over Serial and return `CurrentTemp,Setpoint,CompressorState,HeaterState` telemetry.
2. **SDI-12 Adapter:** A USB-to-SDI-12 serial adapter.
3. **Sensors:** Up to N SDI-12 compliant environmental sensors.

### Software
Ensure you have Python 3.8+ installed. Install the required dependencies using pip:

```bash
pip install customtkinter pyserial matplotlib pandas numpy seaborn
