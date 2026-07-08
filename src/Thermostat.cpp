#include "Thermostat.h"

// --- Constructor ---
// This replaces the old "init" function. It sets up the default state.
Thermostat::Thermostat(int compressorPin, int heaterPin) {
  relayCompressor = compressorPin;
  relayHeatLamp = heaterPin;
  
  currentSetpoint = 25.0;
  startSetpoint = 25.0;
  targetSetpoint = 25.0;
  transitionStartTime = 0;
  transitionDurationMs = 0;
  
  lastCompressorOffTime = 0 - COMPRESSOR_MINIMUM_OFF_MS;
  lastCompressorOnTime = 0;
  isCompressorOn = false;
  isHeaterOn = false;

}

// --- Setup a new ramp ---
void Thermostat::startNewTemperatureRamp(float currentTemp, float newTarget, float minutes) {
  startSetpoint = currentTemp; 
  targetSetpoint = newTarget;
  transitionStartTime = millis();
  transitionDurationMs = (unsigned long)(minutes * 60000.0);
}

// --- Internal Relay Wrappers ---
void Thermostat::turnOnCompressor() {
  if (!isCompressorOn) { 
    digitalWrite(relayCompressor, HIGH); 
    isCompressorOn = true;
    lastCompressorOnTime = millis();
    }
}
void Thermostat::turnOffCompressor() {
  if (isCompressorOn) { 
    digitalWrite(relayCompressor, LOW); 
    isCompressorOn = false; 
    lastCompressorOffTime = millis(); 
  }
}
void Thermostat::turnOnHeater() {
  if (!isHeaterOn) { digitalWrite(relayHeatLamp, HIGH); isHeaterOn = true; }
}
void Thermostat::turnOffHeater() {
  if (isHeaterOn) { digitalWrite(relayHeatLamp, LOW); isHeaterOn = false; }
}

// --- Main Logic ---
void Thermostat::updateThermostatLogic(float currentTemp) {
  // 1. Update interpolation
  if (transitionDurationMs > 0) {
    unsigned long elapsed = millis() - transitionStartTime;
    if (elapsed >= transitionDurationMs) {
      currentSetpoint = targetSetpoint;
    } else {
      float progress = (float)elapsed / (float)transitionDurationMs;
      currentSetpoint = startSetpoint + ((targetSetpoint - startSetpoint) * progress);
    }
  }

  // 2. Bang-Bang Control
  if (currentTemp > currentSetpoint + DEADBAND) {
    turnOffHeater();
    if (millis() - lastCompressorOffTime >= COMPRESSOR_MINIMUM_OFF_MS) {
      turnOnCompressor();
    }
  }
  else if (currentTemp < currentSetpoint - DEADBAND) {
    if (millis() - lastCompressorOnTime >= COMPRESSOR_MINIMUM_ON_MS) {
      turnOffCompressor();
    }
    turnOnHeater();
  }
  else if (currentTemp > currentSetpoint - (DEADBAND/2.0) && currentTemp < currentSetpoint + (DEADBAND/2.0)){
    if (millis() - lastCompressorOnTime >= COMPRESSOR_MINIMUM_ON_MS) {
      turnOffCompressor();
    }
     turnOffHeater();
  }
}

// --- Getters ---
float Thermostat::getCurrentSetpoint() { return currentSetpoint; }
bool Thermostat::getCompressorState() { return isCompressorOn; }
bool Thermostat::getHeaterState() { return isHeaterOn; }