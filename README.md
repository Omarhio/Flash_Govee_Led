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
```
## Configuration

Govee API Key: Replace the api_key variable in the script with your Govee API Key.
Device Name: Modify the device_name_to_control variable to match your Govee LED device's name (e.g., "Barre Led" in this example).

### Usage

Run the script with:

```bash
python flash.py
```

The script performs the following actions:

- Monitors a specific screen area to detect brightness changes (flash).
- Turns on the Govee LED and changes its color to white when a flash is detected.
- Turns off the LED when the flash ends.

## Script Details

Flash Detection (detect_flash)  
The detect_flash function captures a specific screen area and analyzes brightness to detect a flash. Here’s how it works:

```python
def detect_flash(threshold=200):
    with mss.mss() as sct:
        monitor = {"top": 200, "left": 200, "width": 400, "height": 400}
        img = np.array(sct.grab(monitor))
        gray_img = np.mean(img, axis=2)
        brightness = np.mean(gray_img)
        return brightness > threshold
```

1. Capture Region: The screen area to analyze is defined by ```top```, ```left```, ```width```, and ```height```. You can adjust these values to target a specific area of your screen.
2. Convert to Grayscale: The captured image is converted to grayscale by averaging the RGB values for simplified analysis.
3. Average Brightness Calculation: The average brightness is calculated. If it exceeds the threshold (```threshold=200```), a flash is detected, and the function returns ```True```.

## Govee LED Control

The ```control_device``` function manages the Govee LED state:

- Turn On and Change Color: When ```turn_on=True```, the LED is turned on and changed to white.
- Turn Off: When no flash is detected, the LED is turned off.

#### Configuration Example

To control a Govee LED:

```api_key = 'your_govee_api_key'```  
```device_name_to_control = "Barre Led"```
