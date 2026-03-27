import asyncio
import os
import numpy as np
from PIL import ImageGrab
import aiohttp

api_key = os.environ.get('GOVEE_API_KEY', '')
device_name_to_control = "Barre Led"
api_url = "https://developer-api.govee.com/v1/devices"


async def control_device(session, device_id, model, turn_on=True):
    headers = {
        "Govee-API-Key": api_key,
        "Content-Type": "application/json",
    }
    command = {
        "device": device_id,
        "model": model,
        "cmd": {"name": "turn", "value": "on" if turn_on else "off"},
    }
    try:
        async with session.put(f"{api_url}/control", headers=headers, json=command) as resp:
            if not resp.ok:
                print(f"Erreur lors du {'allumage' if turn_on else 'extinction'} (HTTP {resp.status})")
                return
        if turn_on:
            white_command = {
                "device": device_id,
                "model": model,
                "cmd": {"name": "color", "value": {"r": 255, "g": 255, "b": 255}},
            }
            async with session.put(f"{api_url}/control", headers=headers, json=white_command) as resp:
                if not resp.ok:
                    print(f"Erreur lors du réglage de la couleur (HTTP {resp.status})")
    except aiohttp.ClientError as e:
        print(f"Erreur réseau : {e}")


def detect_flash(threshold=200):
    bbox = (300, 300, 500, 500)
    img = ImageGrab.grab(bbox=bbox)
    img_array = np.array(img)
    brightness = np.mean(img_array)
    return brightness > threshold


async def get_device_info(session):
    headers = {"Govee-API-Key": api_key}
    try:
        async with session.get(api_url, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                for device in data.get("data", {}).get("devices", []):
                    if device.get("deviceName") == device_name_to_control:
                        return device.get("device"), device.get("model")
    except aiohttp.ClientError as e:
        print(f"Erreur lors de la récupération des appareils : {e}")
    return None, None


async def main():
    async with aiohttp.ClientSession() as session:
        device_id, model = await get_device_info(session)

        if not device_id or not model:
            print(f"Appareil '{device_name_to_control}' introuvable.")
            return

        print("Détection de flash en cours...")
        flash_on = False

        while True:
            if detect_flash():
                if not flash_on:
                    print("Flash détecté ! Allumage des lumières...")
                    await control_device(session, device_id, model, turn_on=True)
                    flash_on = True
            else:
                if flash_on:
                    print("Fin du flash. Extinction des lumières...")
                    await control_device(session, device_id, model, turn_on=False)
                    flash_on = False

            await asyncio.sleep(0.05)


if __name__ == "__main__":
    asyncio.run(main())
