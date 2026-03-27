import asyncio
from dataclasses import dataclass

import httpx
import numpy as np
from loguru import logger
from PIL import ImageGrab
from pydantic_settings import BaseSettings, SettingsConfigDict
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

# ── Configuration ──────────────────────────────────────────────────────────────

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    govee_api_key: str
    device_name: str = "Barre Led"
    flash_threshold: float = 200.0
    capture_bbox: tuple[int, int, int, int] = (300, 300, 500, 500)
    poll_interval: float = 0.05

settings = Settings()

# ── Constants ──────────────────────────────────────────────────────────────────

GOVEE_API_URL = "https://developer-api.govee.com/v1/devices"
WHITE = {"r": 255, "g": 255, "b": 255}

# ── Data models ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class GoveeDevice:
    device_id: str
    model: str
    name: str

# ── HTTP helpers ───────────────────────────────────────────────────────────────

def _headers() -> dict[str, str]:
    return {"Govee-API-Key": settings.govee_api_key, "Content-Type": "application/json"}


_http_retry = retry(
    retry=retry_if_exception_type(httpx.RequestError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    reraise=True,
)

# ── Govee API ──────────────────────────────────────────────────────────────────

@_http_retry
async def control_device(client: httpx.AsyncClient, device: GoveeDevice, turn_on: bool = True) -> None:
    action = "allumage" if turn_on else "extinction"
    command = {
        "device": device.device_id,
        "model": device.model,
        "cmd": {"name": "turn", "value": "on" if turn_on else "off"},
    }
    try:
        resp = await client.put(f"{GOVEE_API_URL}/control", headers=_headers(), json=command)
        resp.raise_for_status()
        if turn_on:
            white_command = {
                "device": device.device_id,
                "model": device.model,
                "cmd": {"name": "color", "value": WHITE},
            }
            resp = await client.put(f"{GOVEE_API_URL}/control", headers=_headers(), json=white_command)
            resp.raise_for_status()
        logger.info("LED {} — {}", action, device.name)
    except httpx.HTTPStatusError as e:
        logger.error("Erreur HTTP {} lors du {} ({})", e.response.status_code, action, device.name)
    except httpx.RequestError as e:
        logger.error("Erreur réseau lors du {} : {}", action, e)


@_http_retry
async def get_device_info(client: httpx.AsyncClient) -> GoveeDevice | None:
    try:
        resp = await client.get(GOVEE_API_URL, headers=_headers())
        resp.raise_for_status()
        for device in resp.json().get("data", {}).get("devices", []):
            if device.get("deviceName") == settings.device_name:
                return GoveeDevice(
                    device_id=device["device"],
                    model=device["model"],
                    name=device["deviceName"],
                )
    except httpx.HTTPStatusError as e:
        logger.error("Erreur HTTP {} lors de la récupération des appareils", e.response.status_code)
    except httpx.RequestError as e:
        logger.error("Erreur réseau : {}", e)
    return None

# ── Screen detection ───────────────────────────────────────────────────────────

def detect_flash() -> bool:
    img = ImageGrab.grab(bbox=settings.capture_bbox)
    brightness = float(np.mean(np.array(img)[:, :, :3]))
    return brightness > settings.flash_threshold

# ── Main loop ──────────────────────────────────────────────────────────────────

async def main() -> None:
    logger.info("Démarrage — résolution de l'appareil '{}'", settings.device_name)

    async with httpx.AsyncClient(timeout=10) as client:
        device = await get_device_info(client)

        if device is None:
            logger.error("Appareil '{}' introuvable.", settings.device_name)
            return

        logger.success("Appareil trouvé : {} ({})", device.name, device.device_id)
        logger.info("Détection de flash en cours...")

        flash_on = False
        loop = asyncio.get_running_loop()

        while True:
            is_flash = await loop.run_in_executor(None, detect_flash)
            if is_flash and not flash_on:
                logger.debug("Flash détecté (seuil={})", settings.flash_threshold)
                await control_device(client, device, turn_on=True)
                flash_on = True
            elif not is_flash and flash_on:
                logger.debug("Fin du flash")
                await control_device(client, device, turn_on=False)
                flash_on = False

            await asyncio.sleep(settings.poll_interval)


if __name__ == "__main__":
    asyncio.run(main())
