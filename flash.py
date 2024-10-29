import asyncio
import numpy as np
import mss
from govee_api_laggat import Govee, GoveeError

api_key = 'your_govee_api_key'
device_name_to_control = "Your LED Device Name"

async def control_device(govee, device, turn_on=True):
    try:
        if turn_on:
            # Allumer la lumière et changer la couleur en blanc
            success, err = await govee.turn_on(device.device)
            if success:
                await govee.set_color(device.device, (255, 255, 255))  # Blanc
                action = 'allumé et changé en blanc'
            else:
                action = 'allumé'
        else:
            success, err = await govee.turn_off(device.device)
            action = 'éteint'

        if success:
            print(f"L'appareil {device.device_name} ({device.device}) a été {action}.")
        else:
            print(f"Impossible de {action} l'appareil {device.device_name} ({device.device}): {err}")

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
        gray_img = np.mean(img, axis=2)
        brightness = np.mean(gray_img)
        return brightness > threshold

async def main():
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

            await asyncio.sleep(0.1)  # Réduire la pause pour une détection plus rapide (0.1 seconde)

        await govee.close()
        
    except GoveeError as e:
        print(f"Erreur Govee : {e}")

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
