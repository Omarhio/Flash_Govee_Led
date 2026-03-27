import asyncio
import os
import numpy as np
import mss
from govee_api_laggat import Govee, GoveeError

api_key = os.environ.get('GOVEE_API_KEY', '')
device_name_to_control = "Your LED Device Name"

async def control_device(govee, device, turn_on=True):
    try:
        if turn_on:
            success, err = await govee.turn_on(device.device)
            if not success:
                print(f"Impossible d'allumer {device.device_name} ({device.device}): {err}")
                return
            await govee.set_color(device.device, (255, 255, 255))
            print(f"L'appareil {device.device_name} ({device.device}) a été allumé et changé en blanc.")
        else:
            success, err = await govee.turn_off(device.device)
            if success:
                print(f"L'appareil {device.device_name} ({device.device}) a été éteint.")
            else:
                print(f"Impossible d'éteindre {device.device_name} ({device.device}): {err}")

    except GoveeError as e:
        print(f"Erreur lors du contrôle de l'appareil {device.device_name}: {e}")

async def control_barre_led(govee, turn_on):
    devices, err = await govee.get_devices()
    if err:
        print(f"Erreur lors de la récupération des appareils : {err}")
        return
    
    for device in devices:
        if device.device_name == device_name_to_control:
            await control_device(govee, device, turn_on)

def detect_flash(threshold=200):
    with mss.mss() as sct:
        monitor = {"top": 200, "left": 200, "width": 400, "height": 400}
        img = np.array(sct.grab(monitor))
        gray_img = np.mean(img[:, :, :3], axis=2)
        brightness = np.mean(gray_img)
        return brightness > threshold

async def main():
    govee = None
    try:
        govee = await Govee.create(api_key)

        print("En attente de la détection d'un flash...")
        flash_on = False

        while True:
            if detect_flash():
                if not flash_on:
                    print("Flash détecté ! Allumage des lumières et changement de couleur en blanc...")
                    await control_barre_led(govee, turn_on=True)
                    flash_on = True
            else:
                if flash_on:
                    print("Fin du flash. Extinction des lumières...")
                    await control_barre_led(govee, turn_on=False)
                    flash_on = False

            await asyncio.sleep(0.1)

    except GoveeError as e:
        print(f"Erreur Govee : {e}")
    finally:
        if govee:
            await govee.close()

asyncio.run(main())
