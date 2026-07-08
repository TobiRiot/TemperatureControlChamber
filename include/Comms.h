/*
  User Inputs

*/

#ifndef COMMS_H
#define COMMS_H

#include <Arduino.h>

class Comms {
  private:
    float parsedTarget;
    float parsedDuration;

  public:
    Comms();
    
    // Checks serial buffer and returns true if a valid command was received
    bool checkForCommands();
    
    // Getters for the parsed data
    float getTargetTemp();
    float getDurationMinutes();

    // Telemetry output
    void reportStatus(float currentTemp, float currentSetpoint, bool compOn, bool heatOn);
};

#endif