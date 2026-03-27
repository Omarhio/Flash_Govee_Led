import asyncio
from dataclasses import dataclass

import httpx
import numpy as np
from PIL import ImageGrab
from pydantic_settings import BaseSettings, SettingsConfigDict

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


def _headers() -> dict[str, str]:
    return {"Govee-API-Key": settings.govee_api_key, "Content-Type": "application/json"}


async def control_device(client: httpx.AsyncClient, device: GoveeDevice, turn_on: bool = True) -> None:
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
    except httpx.HTTPStatusError as e:
        print(f"Erreur HTTP {e.response.status_code} lors du {'allumage' if turn_on else 'extinction'}")
    except httpx.RequestError as e:
        print(f"Erreur réseau : {e}")


def detect_flash() -> bool:
    img = ImageGrab.grab(bbox=settings.capture_bbox)
    brightness = float(np.mean(np.array(img)[:, :, :3]))
    return brightness > settings.flash_threshold


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
        print(f"Erreur HTTP {e.response.status_code} lors de la récupération des appareils")
    except httpx.RequestError as e:
        print(f"Erreur réseau : {e}")
    return None


async def main() -> None:
    async with httpx.AsyncClient(timeout=10) as client:
        device = await get_device_info(client)

        if device is None:
            print(f"Appareil '{settings.device_name}' introuvable.")
            return

        print("Détection de flash en cours...")
        flash_on = False
        loop = asyncio.get_running_loop()

        while True:
            is_flash = await loop.run_in_executor(None, detect_flash)
            if is_flash:
                if not flash_on:
                    print("Flash détecté ! Allumage des lumières...")
                    await control_device(client, device, turn_on=True)
                    flash_on = True
            else:
                if flash_on:
                    print("Fin du flash. Extinction des lumières...")
                    await control_device(client, device, turn_on=False)
                    flash_on = False

            await asyncio.sleep(settings.poll_interval)


if __name__ == "__main__":
    asyncio.run(main())
