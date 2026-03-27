import asyncio
import time

import numpy as np
from govee_local_api import GoveeController, GoveeDevice
from loguru import logger
from PIL import ImageGrab
from pydantic_settings import BaseSettings, SettingsConfigDict

# ── Configuration ──────────────────────────────────────────────────────────────

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    device_ip: str
    flash_threshold: float = 200.0
    capture_bbox: tuple[int, int, int, int] = (300, 300, 500, 500)
    poll_interval: float = 0.05
    discovery_timeout: float = 10.0

settings = Settings()

# ── Screen detection ───────────────────────────────────────────────────────────

def detect_flash() -> bool:
    img = ImageGrab.grab(bbox=settings.capture_bbox)
    brightness = float(np.mean(np.array(img)[:, :, :3]))
    return brightness > settings.flash_threshold

# ── Main loop ──────────────────────────────────────────────────────────────────

async def main() -> None:
    logger.info("Démarrage — connexion LAN à {}", settings.device_ip)

    loop = asyncio.get_running_loop()
    controller = GoveeController(
        loop=loop,
        listening_address="0.0.0.0",
        discovery_enabled=False,
    )
    await controller.start()
    controller.add_device_to_discovery_queue(settings.device_ip)

    deadline = loop.time() + settings.discovery_timeout
    while not controller.devices and loop.time() < deadline:
        await asyncio.sleep(0.5)

    if not controller.devices:
        logger.error(
            "Appareil introuvable à {} (timeout {}s) — vérifier IP et LAN Control",
            settings.device_ip,
            settings.discovery_timeout,
        )
        return

    device: GoveeDevice = controller.devices[0]
    logger.success("Appareil trouvé : {} ({})", device.sku, device.ip)

    await device.turn_on()
    await device.set_rgb_color(255, 255, 255)
    await device.turn_off()
    logger.info("Couleur initiale définie (blanc) — détection de flash en cours...")

    flash_on = False

    while True:
        is_flash = await loop.run_in_executor(None, detect_flash)

        if is_flash and not flash_on:
            logger.debug("Flash détecté (seuil={})", settings.flash_threshold)
            await device.turn_on()
            flash_on = True
        elif not is_flash and flash_on:
            logger.debug("Fin du flash")
            await device.turn_off()
            flash_on = False

        await asyncio.sleep(settings.poll_interval)


if __name__ == "__main__":
    asyncio.run(main())
