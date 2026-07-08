/*
  Dynamic Temperature Controller
  Microcontroller: Seeed Studio XIAO ESP32-C3
  Input: Serial commands from Python (Format: "T:target_temp,D:duration_in_minutes\n")
*/

#include <Arduino.h>
#include "Thermostat.h"
#include "Sensors.h"
#include "Comms.h"

// --- Create the Class Objects ---
Thermostat myThermostat(D4, D5);       // Compressor on D4, Heater on D5
Sensors    mySensors(D0, D1, D2);      // Thermistors on D0, D1, D2
Comms      myComms;                    // Serial interface

// --- Timing & State Variables ---
unsigned long lastTelemetryTime = 0;
const unsigned long TELEMETRY_INTERVAL = 2000; // Update every 2 seconds

float currentTemp = 25.0;
bool systemActive = false; // NEW: Flag to keep the system idling on boot

void setup() {
  Serial.begin(115200);
  while (!Serial) { delay(10); }

  // Set the pin modes for the relays
  pinMode(D4, OUTPUT);
  pinMode(D5, OUTPUT);
  
  // NEW: Explicitly force relays OFF to ensure safe idle state
  digitalWrite(D4, LOW); 
  digitalWrite(D5, LOW);
  
  // Get an initial baseline temperature to start the system safely
  currentTemp = mySensors.getAverageTemperature();
}

void loop() {
  // 1. READ SENSORS
  currentTemp = mySensors.getAverageTemperature();

  // 2. CHECK FOR PYTHON COMMANDS
  if (myComms.checkForCommands()) {
    
    // NEW: The system has received a command and will now exit idle mode
    systemActive = true; 
    
    // Extract the newly parsed data and feed it to the thermostat
    float newTarget = myComms.getTargetTemp();
    float newDuration = myComms.getDurationMinutes();
    
    myThermostat.startNewTemperatureRamp(currentTemp, newTarget, newDuration);
  }

  // 3. RUN THERMOSTAT LOGIC
  if (systemActive) {
    myThermostat.updateThermostatLogic(currentTemp);
  }

  // 4. SEND TELEMETRY DATA
  // Note: Telemetry will still broadcast while idling so Python knows current temp
  if (millis() - lastTelemetryTime >= TELEMETRY_INTERVAL) {
    myComms.reportStatus(
      currentTemp, 
      myThermostat.getCurrentSetpoint(), 
      myThermostat.getCompressorState(), 
      myThermostat.getHeaterState()
    );
    lastTelemetryTime = millis();
  }
}