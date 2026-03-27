# Flash LED Controller with Screen Flash Detection

Controls a Govee LED strip via the **local LAN API** (UDP) in response to brightness flashes detected on screen. No cloud dependency, no rate limits, near-instant response.

## Features

- **Screen flash detection** — captures a screen region and monitors RGB brightness with `Pillow`
- **LAN UDP control** — direct communication with the device on your local network via `govee-local-api`
- **Non-blocking capture** — screen capture runs in a thread executor, keeping the async loop responsive
- **Typed configuration** — all settings managed via `.env` with `pydantic-settings`
- **Structured logging** — log levels via `loguru`

## Requirements

- **Python 3.11+**
- A Govee LED strip that supports the LAN API — check the [supported device list](https://app-h5.govee.com/user-manual/wlan-guide)

### Install dependencies

```bash
pip install numpy pillow govee-local-api pydantic-settings loguru
```

## Setup

### 1. Enable LAN Control on your device

In the **Govee Home app** → select your device → tap the settings icon → enable **"LAN Control"**.
Without this step, the script cannot discover the device.

### 2. Find your device's local IP

Check your router's DHCP table, or look in the Govee app under device info.

### 3. Configure `.env`

```bash
cp .env.example .env
```

Edit `.env`:

```env
DEVICE_IP=192.168.1.xxx
```

All other settings are optional (defaults shown in `.env.example`).

## Usage

```bash
python flash.py
```

The script will:
1. Connect to the device at `DEVICE_IP` via LAN UDP
2. Set the initial color to white
3. Turn the LED on (white) when a flash is detected
4. Turn it off when the flash ends

## Configuration reference

| Variable | Default | Description |
|----------|---------|-------------|
| `DEVICE_IP` | *(required)* | Local IP of the Govee LED strip |
| `FLASH_THRESHOLD` | `200.0` | Brightness threshold (0–255) to trigger a flash |
| `CAPTURE_BBOX` | `[300,300,500,500]` | Screen region to monitor `[left, top, right, bottom]` |
| `POLL_INTERVAL` | `0.05` | Seconds between each brightness check |
| `DISCOVERY_TIMEOUT` | `10.0` | Seconds to wait for device to respond on startup |

## Script details

### Flash detection

```python
def detect_flash() -> bool:
    img = ImageGrab.grab(bbox=settings.capture_bbox)
    brightness = float(np.mean(np.array(img)[:, :, :3]))
    return brightness > settings.flash_threshold
```

Captures a screen region, averages the RGB channels, and compares against the threshold.
Adjust `CAPTURE_BBOX` to target the area most likely to flash (e.g. center of screen).

### LAN communication

Uses `govee-local-api` which sends UDP packets directly to the device on ports 4001–4003.
No API key, no cloud, no rate limits.
