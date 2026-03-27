import asyncio
import numpy as np
from PIL import ImageGrab
import aiohttp
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


async def control_device(session, device_id, model, turn_on=True):
    headers = {
        "Govee-API-Key": settings.govee_api_key,
        "Content-Type": "application/json",
    }
    command = {
        "device": device_id,
        "model": model,
        "cmd": {"name": "turn", "value": "on" if turn_on else "off"},
    }
    try:
        async with session.put(f"{GOVEE_API_URL}/control", headers=headers, json=command) as resp:
            if not resp.ok:
                print(f"Erreur lors du {'allumage' if turn_on else 'extinction'} (HTTP {resp.status})")
                return
        if turn_on:
            white_command = {
                "device": device_id,
                "model": model,
                "cmd": {"name": "color", "value": WHITE},
            }
            async with session.put(f"{GOVEE_API_URL}/control", headers=headers, json=white_command) as resp:
                if not resp.ok:
                    print(f"Erreur lors du réglage de la couleur (HTTP {resp.status})")
    except aiohttp.ClientError as e:
        print(f"Erreur réseau : {e}")


def detect_flash():
    img = ImageGrab.grab(bbox=settings.capture_bbox)
    brightness = np.mean(np.array(img)[:, :, :3])
    return brightness > settings.flash_threshold


async def get_device_info(session):
    headers = {"Govee-API-Key": settings.govee_api_key}
    try:
        async with session.get(GOVEE_API_URL, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                for device in data.get("data", {}).get("devices", []):
                    if device.get("deviceName") == settings.device_name:
                        return device.get("device"), device.get("model")
    except aiohttp.ClientError as e:
        print(f"Erreur lors de la récupération des appareils : {e}")
    return None, None


async def main():
    async with aiohttp.ClientSession() as session:
        device_id, model = await get_device_info(session)

        if not device_id or not model:
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
                    await control_device(session, device_id, model, turn_on=True)
                    flash_on = True
            else:
                if flash_on:
                    print("Fin du flash. Extinction des lumières...")
                    await control_device(session, device_id, model, turn_on=False)
                    flash_on = False

            await asyncio.sleep(settings.poll_interval)


if __name__ == "__main__":
    asyncio.run(main())
