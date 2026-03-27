# Flash LED Controller with Screen Flash Detection

This Python script controls a Govee LED light in response to brightness flashes detected on screen. When a flash is detected, the LED turns on in white and stays on for the duration of the flash, then turns off. Useful for immersive gaming or ambient lighting reactions.

## Features

- **Screen Flash Detection**: Uses `Pillow` to capture a screen region and monitor RGB brightness changes.
- **Govee LED Control**: Directly calls the official Govee HTTP API via `aiohttp` — no third-party wrapper.
- **Non-blocking capture**: Screen capture runs in a thread executor so the async event loop stays responsive.
- **Optimized Response Time**: Polls brightness every 0.05 seconds.

## Requirements

- **Python 3.10** or higher
- **Govee API Key**: Generate one from the [Govee Developer Portal](https://developer.govee.com/).

### Required Python Libraries

```bash
pip install numpy pillow aiohttp
```

## Configuration

### API Key

Set your Govee API key as an environment variable:

```bash
# Linux / macOS
export GOVEE_API_KEY="your_api_key"

# Windows
set GOVEE_API_KEY=your_api_key
```

### Device Name

Edit the `device_name_to_control` variable in `flash.py` to match your device's name as it appears in the Govee app:

```python
device_name_to_control = "Barre Led"
```

## Usage

```bash
python flash.py
```

The script will:
1. Connect to the Govee API and resolve the target device.
2. Monitor a screen region for brightness changes.
3. Turn the LED on (white) when a flash is detected.
4. Turn the LED off when the flash ends.

## Script Details

### Flash Detection (`detect_flash`)

```python
def detect_flash(threshold=200):
    bbox = (300, 300, 500, 500)
    img = ImageGrab.grab(bbox=bbox)
    img_array = np.array(img)
    brightness = np.mean(img_array[:, :, :3])
    return brightness > threshold
```

1. **Capture region**: A 200×200 px area at `(300, 300)` on the primary monitor. Adjust `bbox` to target any screen area.
2. **RGB brightness**: Averages the R, G, B channels (alpha excluded) for an accurate brightness value.
3. **Threshold**: Returns `True` if average brightness exceeds `200/255`. Adjust `threshold` to tune sensitivity.

### Govee LED Control (`control_device`)

Sends PUT requests directly to `https://developer-api.govee.com/v1/devices/control`:

- **Turn on**: sends a `turn: on` command, then a `color: {r:255, g:255, b:255}` command to set white.
- **Turn off**: sends a `turn: off` command.

HTTP errors are caught and printed without crashing the loop.
