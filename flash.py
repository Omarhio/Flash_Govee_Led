import asyncio
import json
import socket
from collections import deque
from dataclasses import dataclass, field

import numpy as np
from loguru import logger
from PIL import ImageGrab
from pydantic_settings import BaseSettings, SettingsConfigDict

# ── Configuration ──────────────────────────────────────────────────────────────

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    device_ip: str
    capture_bbox: tuple[int, int, int, int] = (640, 300, 1280, 780)
    poll_interval: float = 0.05

    # Flash detector — brightness spike
    baseline_window: int = 20       # frames in rolling ambient baseline (~1s at 50ms)
    relative_spike: float = 0.30    # brightness must be 30% above baseline
    min_spike: float = 25.0         # minimum absolute brightness increase (0–255)

    # Flash detector — Valorant-specific filters
    max_uniformity: float = 50.0    # max spatial std of the frame (flash = uniform = low std)
    max_saturation: float = 80.0    # max RGB channel spread (flash = white/pale = low spread)

settings = Settings()

# ── Govee LAN API ──────────────────────────────────────────────────────────────

GOVEE_COMMAND_PORT = 4003


def _send_udp(ip: str, command: dict) -> None:
    message = json.dumps({"msg": command}).encode()
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.sendto(message, (ip, GOVEE_COMMAND_PORT))


def turn_on(ip: str) -> None:
    _send_udp(ip, {"cmd": "turn", "data": {"value": 1}})


def turn_off(ip: str) -> None:
    _send_udp(ip, {"cmd": "turn", "data": {"value": 0}})


def set_color(ip: str, r: int, g: int, b: int) -> None:
    _send_udp(ip, {"cmd": "colorwc", "data": {"color": {"r": r, "g": g, "b": b}, "colorTemInKelvin": 0}})

# ── Flash detector ─────────────────────────────────────────────────────────────

@dataclass
class FlashDetector:
    """
    Detects flashes by combining three independent signals:

    1. Brightness spike   — current brightness significantly above rolling baseline
                           (handles scene-adaptive detection, ignores persistent brightness)
    2. Spatial uniformity — the captured frame is nearly uniform (low std)
                           (a flash blankets the whole area; a sky or UI element does not)
    3. Color saturation   — RGB channels are close to each other (low spread)
                           (flashes are white/pale; sky is blue, foliage is green, etc.)

    All three must be true simultaneously to declare a flash.
    """
    window: int
    relative_spike: float
    min_spike: float
    max_uniformity: float
    max_saturation: float
    _history: deque = field(init=False)

    def __post_init__(self) -> None:
        self._history = deque(maxlen=self.window)

    def update(self, brightness: float, uniformity: float, saturation: float) -> bool:
        is_flash = False
        if len(self._history) >= max(3, self.window // 4):
            baseline = float(np.mean(self._history))
            spike = brightness - baseline

            spike_ok      = spike >= max(baseline * self.relative_spike, self.min_spike)
            uniform_ok    = uniformity <= self.max_uniformity
            saturated_ok  = saturation <= self.max_saturation

            is_flash = spike_ok and uniform_ok and saturated_ok

            if spike_ok and not is_flash:
                logger.trace(
                    "Spike ignoré — uniformity={:.1f}/{} saturation={:.1f}/{}",
                    uniformity, self.max_uniformity,
                    saturation, self.max_saturation,
                )

        self._history.append(brightness)
        return is_flash

# ── Screen sampling ────────────────────────────────────────────────────────────

def sample_screen() -> tuple[float, float, float, tuple[int, int, int]]:
    img_array = np.array(ImageGrab.grab(bbox=settings.capture_bbox))[:, :, :3]
    r = int(np.mean(img_array[:, :, 0]))
    g = int(np.mean(img_array[:, :, 1]))
    b = int(np.mean(img_array[:, :, 2]))
    brightness  = (r + g + b) / 3
    uniformity  = float(np.std(img_array))
    saturation  = float(max(r, g, b) - min(r, g, b))
    return brightness, uniformity, saturation, (r, g, b)

# ── Main loop ──────────────────────────────────────────────────────────────────

async def main() -> None:
    ip = settings.device_ip
    logger.info("Démarrage — connexion LAN à {}", ip)
    logger.info(
        "Détecteur : baseline={}f  spike={:.0%}+{}  uniformity≤{}  saturation≤{}",
        settings.baseline_window,
        settings.relative_spike,
        settings.min_spike,
        settings.max_uniformity,
        settings.max_saturation,
    )

    detector = FlashDetector(
        window=settings.baseline_window,
        relative_spike=settings.relative_spike,
        min_spike=settings.min_spike,
        max_uniformity=settings.max_uniformity,
        max_saturation=settings.max_saturation,
    )

    flash_on = False
    loop = asyncio.get_running_loop()

    while True:
        brightness, uniformity, saturation, (r, g, b) = await loop.run_in_executor(
            None, sample_screen
        )
        is_flash = detector.update(brightness, uniformity, saturation)

        if is_flash:
            if not flash_on:
                logger.debug(
                    "Flash — brightness={:.1f}  uniformity={:.1f}  saturation={:.1f}  rgb=({},{},{})",
                    brightness, uniformity, saturation, r, g, b,
                )
                await loop.run_in_executor(None, turn_on, ip)
                flash_on = True
            await loop.run_in_executor(None, set_color, ip, r, g, b)
        elif flash_on:
            logger.debug("Fin du flash")
            await loop.run_in_executor(None, turn_off, ip)
            flash_on = False

        await asyncio.sleep(settings.poll_interval)


if __name__ == "__main__":
    asyncio.run(main())
