#include "Comms.h"

// --- Constructor ---
Comms::Comms() {
  parsedTarget = 25.0;
  parsedDuration = 0.0;

}

// --- Listen for Python Strings ---
bool Comms::checkForCommands() {
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    
    int tIndex = cmd.indexOf("T:");
    int dIndex = cmd.indexOf(",D:");
    
    // If string format matches "T:xx.x,D:yyyy"
    if (tIndex != -1 && dIndex != -1) {
      parsedTarget = cmd.substring(tIndex + 2, dIndex).toFloat();
      parsedDuration = cmd.substring(dIndex + 3).toFloat();
      
      Serial.println("ACK: New Profile Loaded");
      return true; // Inform main.cpp that new data is ready
    }
  }
  return false; // No valid command received
}

// --- Getters ---
float Comms::getTargetTemp() { return parsedTarget; }
float Comms::getDurationMinutes() { return parsedDuration; }

// --- Send Status to Python ---
void Comms::reportStatus(float currentTemp, float currentSetpoint, bool compOn, bool heatOn) {
  Serial.print(currentTemp); Serial.print(",");
  Serial.print(currentSetpoint); Serial.print(",");
  Serial.print(compOn); Serial.print(",");
  Serial.println(heatOn);
}