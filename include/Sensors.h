/*
  Sensor management

*/


#ifndef SENSORS_H
#define SENSORS_H

#include <Arduino.h>

class Sensors {
  private:
    int thermistorPins[3];
    float lastKnownTemp;

    // Constants for B3950 Thermistor
    const float SERIES_RESISTOR = 10000.0; 
    const float NOMINAL_RESISTANCE = 10000.0; 
    const float NOMINAL_TEMPERATURE = 25.0; 
    const float B_COEFFICIENT = 3950.0; 

    // Internal helper function
    float readThermistor(int pin);

  public:
    // Constructor takes the 3 pins you are using
    Sensors(int pin1, int pin2, int pin3);

    // Public method to get the final averaged reading
    float getAverageTemperature();
};

#endif