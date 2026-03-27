import asyncio
import json
import socket

import numpy as np
from loguru import logger
from PIL import ImageGrab
from pydantic_settings import BaseSettings, SettingsConfigDict

# ── Configuration ──────────────────────────────────────────────────────────────

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    device_ip: str
    flash_threshold: float = 200.0
    capture_bbox: tuple[int, int, int, int] = (300, 300, 500, 500)
    poll_interval: float = 0.05

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

# ── Screen sampling ────────────────────────────────────────────────────────────

def sample_screen() -> tuple[bool, tuple[int, int, int]]:
    img_array = np.array(ImageGrab.grab(bbox=settings.capture_bbox))[:, :, :3]
    r, g, b = (int(np.mean(img_array[:, :, i])) for i in range(3))
    brightness = (r + g + b) / 3
    return brightness > settings.flash_threshold, (r, g, b)

# ── Main loop ──────────────────────────────────────────────────────────────────

async def main() -> None:
    ip = settings.device_ip
    logger.info("Démarrage — connexion LAN à {}", ip)
    logger.success("Détection de flash en cours...")

    flash_on = False
    loop = asyncio.get_running_loop()

    while True:
        is_flash, (r, g, b) = await loop.run_in_executor(None, sample_screen)

        if is_flash:
            if not flash_on:
                logger.debug("Flash détecté — couleur ({}, {}, {})", r, g, b)
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
