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
    capture_bbox: tuple[int, int, int, int] = (300, 300, 500, 500)
    poll_interval: float = 0.05

    # Flash detector
    baseline_window: int = 20       # frames used to compute ambient baseline (~1s at 50ms)
    relative_spike: float = 0.25    # brightness must be 25% above baseline to trigger
    min_spike: float = 20.0         # minimum absolute brightness increase (0–255)

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
    Detects flashes by comparing current brightness against a rolling ambient
    baseline. Triggers only when brightness spikes significantly above recent
    context, so a persistently bright scene (sky, white UI) is ignored.
    """
    window: int
    relative_spike: float
    min_spike: float
    _history: deque = field(init=False)

    def __post_init__(self) -> None:
        self._history = deque(maxlen=self.window)

    def update(self, brightness: float) -> bool:
        is_flash = False
        if len(self._history) >= max(3, self.window // 4):
            baseline = float(np.mean(self._history))
            spike = brightness - baseline
            is_flash = spike >= max(baseline * self.relative_spike, self.min_spike)
        self._history.append(brightness)
        return is_flash

# ── Screen sampling ────────────────────────────────────────────────────────────

def sample_screen() -> tuple[float, tuple[int, int, int]]:
    img_array = np.array(ImageGrab.grab(bbox=settings.capture_bbox))[:, :, :3]
    r, g, b = (int(np.mean(img_array[:, :, i])) for i in range(3))
    brightness = (r + g + b) / 3
    return brightness, (r, g, b)

# ── Main loop ──────────────────────────────────────────────────────────────────

async def main() -> None:
    ip = settings.device_ip
    logger.info("Démarrage — connexion LAN à {}", ip)
    logger.info(
        "Détecteur : baseline={}f  spike_relatif={:.0%}  spike_min={}",
        settings.baseline_window,
        settings.relative_spike,
        settings.min_spike,
    )

    detector = FlashDetector(
        window=settings.baseline_window,
        relative_spike=settings.relative_spike,
        min_spike=settings.min_spike,
    )

    flash_on = False
    loop = asyncio.get_running_loop()

    while True:
        brightness, (r, g, b) = await loop.run_in_executor(None, sample_screen)
        is_flash = detector.update(brightness)

        if is_flash:
            if not flash_on:
                logger.debug("Flash détecté — brightness={:.1f}  couleur=({},{},{})", brightness, r, g, b)
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
