# Flash LED Controller — Valorant Edition

Controls a Govee LED strip via the **local LAN API** (UDP) in response to flash effects detected on screen. Tuned for Valorant (Phoenix, Reyna, Skye, Breach flashes) but works with any game.

## Features

- **Smart flash detection** — three combined signals: brightness spike + spatial uniformity + color saturation. Ignores bright scenes (sky, white UI, lit environments).
- **Real-time color matching** — LED mirrors the screen color during the flash
- **Direct LAN UDP control** — no cloud, no API key, no rate limits
- **Typed configuration** — all settings managed via `.env` with `pydantic-settings`
- **Structured logging** — `loguru` with TRACE level for detector tuning

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

### 2. Find your device's local IP

Check your router's DHCP table or the Govee app under device info.

### 3. Configure `.env`

```bash
cp .env.example .env
```

Set your device IP and adjust `CAPTURE_BBOX` to your screen resolution:

```env
DEVICE_IP=192.168.1.xxx
CAPTURE_BBOX=[640,300,1280,780]   # center of a 1920x1080 screen
```

## Usage

```bash
python flash.py
```

## How the detector works

A flash is only declared when **all three signals** fire simultaneously:

| Signal | What it measures | Why it matters |
|--------|-----------------|----------------|
| **Brightness spike** | Current brightness vs rolling baseline | Ignores persistently bright scenes |
| **Spatial uniformity** | Std deviation of the captured frame | Flash = whole screen turns uniform; sky/UI don't |
| **Color saturation** | Max − min across R, G, B channels | Flash = white/pale; sky = blue, grass = green |

```
flash = spike_ok AND uniform_ok AND saturation_ok
```

### Visualized

```
Ciel clair    : spike ❌ (baseline also high)  →  no flash
Explosion     : spike ✅  uniformity ❌ (varied colors/shadows)  →  no flash
Valorant flash: spike ✅  uniformity ✅  saturation ✅  →  FLASH ✓
```

## Configuration reference

| Variable | Default | Description |
|----------|---------|-------------|
| `DEVICE_IP` | *(required)* | Local IP of the Govee LED strip |
| `CAPTURE_BBOX` | `[640,300,1280,780]` | Screen region `[left, top, right, bottom]` |
| `POLL_INTERVAL` | `0.05` | Seconds between checks |
| `BASELINE_WINDOW` | `20` | Frames in rolling baseline |
| `RELATIVE_SPIKE` | `0.30` | Minimum relative brightness spike (30% above baseline) |
| `MIN_SPIKE` | `25.0` | Minimum absolute brightness increase |
| `MAX_UNIFORMITY` | `50.0` | Max spatial std — lower = stricter uniformity required |
| `MAX_SATURATION` | `80.0` | Max RGB spread — lower = requires whiter flash |

## Tuning tips

Enable TRACE logs to see why a spike was ignored:
```python
logger.enable("__main__")
```

If too many **false positives** (triggers on bright scenes):
- Decrease `MAX_UNIFORMITY` (e.g. `35`)
- Decrease `MAX_SATURATION` (e.g. `50`)

If **missing flashes**:
- Increase `MAX_UNIFORMITY` (e.g. `70`)
- Increase `MAX_SATURATION` (e.g. `100`)
- Decrease `RELATIVE_SPIKE` (e.g. `0.20`)

## LAN protocol

Commands sent as UDP JSON to `device_ip:4003`:

| Action | Command |
|--------|---------|
| Turn on | `{"cmd": "turn", "data": {"value": 1}}` |
| Turn off | `{"cmd": "turn", "data": {"value": 0}}` |
| Set color | `{"cmd": "colorwc", "data": {"color": {"r": R, "g": G, "b": B}, "colorTemInKelvin": 0}}` |
