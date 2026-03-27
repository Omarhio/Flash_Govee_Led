# Flash LED Controller with Screen Flash Detection

Controls a Govee LED strip via the **local LAN API** (UDP) in response to brightness flashes detected on screen. No cloud dependency, no rate limits, near-instant response.

## Features

- **Screen flash detection** — captures a screen region and monitors RGB brightness with `Pillow`
- **Direct LAN UDP control** — JSON packets sent directly to the device via stdlib `socket`, no third-party Govee library
- **Non-blocking** — screen capture and UDP calls run in a thread executor, keeping the async loop responsive
- **Typed configuration** — all settings managed via `.env` with `pydantic-settings`
- **Structured logging** — log levels via `loguru`

## Requirements

- **Python 3.11+**
- A Govee LED strip that supports LAN Control — check the [supported device list](https://app-h5.govee.com/user-manual/wlan-guide)

### Install dependencies

```bash
pip install numpy pillow pydantic-settings loguru
```

## Setup

### 1. Enable LAN Control on your device

In the **Govee Home app** → select your device → tap the settings icon → enable **"LAN Control"**.
Without this step, UDP packets will be ignored.

### 2. Find your device's local IP

Check your router's DHCP table, or look in the Govee app under device info.

### 3. Configure `.env`

```bash
cp .env.example .env
```

Edit `.env` and set your device IP:

```env
DEVICE_IP=192.168.1.xxx
```

## Usage

```bash
python flash.py
```

The script will:
1. Initialize the LED color to white via UDP
2. Monitor the configured screen region for brightness changes
3. Turn the LED on when a flash is detected
4. Turn it off when the flash ends

## Configuration reference

| Variable | Default | Description |
|----------|---------|-------------|
| `DEVICE_IP` | *(required)* | Local IP of the Govee LED strip |
| `FLASH_THRESHOLD` | `200.0` | Brightness threshold (0–255) to trigger a flash |
| `CAPTURE_BBOX` | `[300,300,500,500]` | Screen region to monitor `[left, top, right, bottom]` |
| `POLL_INTERVAL` | `0.05` | Seconds between each brightness check |

## How it works

### Flash detection

```python
def detect_flash() -> bool:
    img = ImageGrab.grab(bbox=settings.capture_bbox)
    brightness = float(np.mean(np.array(img)[:, :, :3]))
    return brightness > settings.flash_threshold
```

Captures a screen region, averages the RGB channels, and compares against the threshold.
Adjust `CAPTURE_BBOX` to target the area most likely to flash (e.g. center of screen).

### LAN control

Commands are plain JSON payloads sent over UDP to `device_ip:4003` — the Govee LAN API port:

| Action | Command |
|--------|---------|
| Turn on | `{"cmd": "turn", "data": {"value": 1}}` |
| Turn off | `{"cmd": "turn", "data": {"value": 0}}` |
| Set color | `{"cmd": "colorwc", "data": {"color": {"r": 255, "g": 255, "b": 255}, "colorTemInKelvin": 0}}` |

No API key, no cloud, no rate limits.
