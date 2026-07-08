#ifndef THERMOSTAT_H
#define THERMOSTAT_H

#include <Arduino.h>

class Thermostat {
  private:
    // --- Hardware Pins ---
    int relayCompressor;
    int relayHeatLamp;

    // --- Internal State (Locked down) ---
    float currentSetpoint;
    float startSetpoint;
    float targetSetpoint;
    unsigned long transitionStartTime;
    unsigned long transitionDurationMs;
    
    unsigned long lastCompressorOffTime;
    unsigned long lastCompressorOnTime;
    bool isCompressorOn;
    bool isHeaterOn;

    // --- Constants ---
    const float DEADBAND = 1.0; 
    const unsigned long COMPRESSOR_MINIMUM_OFF_MS = 300000;
    const unsigned long COMPRESSOR_MINIMUM_ON_MS = 300000; 


    // --- Private Internal Functions ---
    void turnOnCompressor();
    void turnOffCompressor();
    void turnOnHeater();
    void turnOffHeater();

  public:
    // --- Constructor (Runs when you create the object) ---
    Thermostat(int compressorPin, int heaterPin);

    // --- Public Methods (Main.cpp can use these) ---
    void startNewTemperatureRamp(float currentTemp, float newTarget, float minutes);
    void updateThermostatLogic(float currentTemp);

    // --- Getters ---
    float getCurrentSetpoint();
    bool getCompressorState();
    bool getHeaterState();
};

#endif