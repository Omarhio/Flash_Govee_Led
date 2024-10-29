# Flash LED Controller with Screen Flash Detection

This Python script is designed to control a Govee LED light in response to a detected flash on the screen. When a flash occurs, the Govee LED light turns on in white and remains on for the duration of the flash, then turns off once the flash ends. This project can be used for immersive gaming experiences or for reacting to brightness changes on the screen.

## Features

- **Screen Flash Detection**: Uses the `mss` library to capture a specific screen area and monitor brightness changes.
- **Govee LED Control**: Automatically turns the LED on in white during the flash and turns it off afterward.
- **Optimized Response Time**: Checks brightness every 0.1 seconds for quick detection and response.

## Requirements

- **Python 3.6** or higher
- **Govee API Key**: To get your API key, create an account on the [Govee Developer Portal](https://developer.govee.com/) and generate your key.

### Required Python Libraries

Install the required libraries using the following commands:

```bash
pip install numpy mss govee-api-laggat