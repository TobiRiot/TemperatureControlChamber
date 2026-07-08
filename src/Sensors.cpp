#include "Sensors.h"

// --- Constructor ---
Sensors::Sensors(int pin1, int pin2, int pin3) {
  thermistorPins[0] = pin1;
  thermistorPins[1] = pin2;
  thermistorPins[2] = pin3;
  lastKnownTemp = 25.0; // Safe default

}

// --- Read Single Thermistor ---
float Sensors::readThermistor(int pin) {
  int rawADC = analogRead(pin);
  if (rawADC == 0 || rawADC >= 4095) return -999.0; 
  
  float resistance = SERIES_RESISTOR / (4095.0 / (float)rawADC - 1.0);
  float steinhart = resistance / NOMINAL_RESISTANCE;
  steinhart = log(steinhart) / B_COEFFICIENT;
  steinhart += 1.0 / (NOMINAL_TEMPERATURE + 273.15);
  return (1.0 / steinhart) - 273.15;
}

// --- Get Averaged Temperature ---
float Sensors::getAverageTemperature() {
  float sum = 0;
  int validReadings = 0;
  
  for (int i = 0; i < 3; i++) {
    float temp = readThermistor(thermistorPins[i]);
    if (temp > -50.0 && temp < 150.0) { // Basic sanity check
      sum += temp;
      validReadings++;
    }
  }
  
  if (validReadings > 0) {
    lastKnownTemp = sum / validReadings;
  }
  
  return lastKnownTemp;
}